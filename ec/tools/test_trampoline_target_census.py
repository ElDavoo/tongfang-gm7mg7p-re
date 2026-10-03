#!/usr/bin/env python3
"""Offline checks for trampoline_target_census.py: no hardware, no capture, no
Ghidra, and nothing but the committed firmware and the committed listings.

**What is asserted here is a relationship or a cited fact, never a count of the
tree.** CLAUDE.md's rule and `test_bucket_c_codemap.py`'s are the same rule
arrived at twice: "there are 535 listings" is a value every merge has to edit,
so this suite asserts "one row per entry `trampolines()` finds inside the
block" and lets the figure move without the suite moving with it. The places a
number *is* the finding are named addresses -- the two the reset-vector
write-up already read and the four `bank-call-audit.md` section 4 names as its
`0xFF` regression -- and those are transcribed here for the same reason they
are named there.

**The committed table is checked against the image, not against a re-run of the
scan that wrote it.** A regenerated table that disagreed with itself would pass
a test comparing `csv_text()` with `csv_text()`, and a re-derived block that
drifted with the firmware would take the census's framing with it. So the
assertions read the image: `target_byte` is the byte at the file offset the
row's own `selects_bank` and `target` name, and `target_class` is
`audit_call_targets.byte_class()` recomputed at that offset.

**The two committed tables that overlap are cross-checked against each other,
not against a literal.** `census_forwarder_targets.py` (issue #465) censused
the same entries against the committed `.asm` files and reached the same
covered/not-covered split from a different source. Asserting agreement between
them catches a drift in either; asserting one against a number written in this
file would only say that file had not changed.

**The 16-byte rule is pinned on a fixture and on the image.** The fixture is
built rather than read out of the image, for the reason
`test_walk_branch_arms.py` gives at its own head: a fixture anchored at an
address in the committed dump keeps testing what it was written to test only
until those bytes change, and the rule is not about this dump. The four
section 4 addresses are the real-image regression, and they are the four the
audit itself names rather than four of this suite's choosing.

**What is deliberately not here.** No case asserts that any target is or is not
code, that any trampoline is called, or that any register behaves in any way.
`target_class` is section 4's own scoring heuristic and this file says so where
it asserts the class; `listing` is coverage by a committed export and is never
"absent"; nothing here is a behavioural claim and nothing was observed on
hardware.
"""
import contextlib
import csv
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    "trampoline_target_census", HERE / "trampoline_target_census.py")
ttc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ttc)

import audit_call_targets as act
import trace_xdata_refs as txr
from find_banks import find_stubs

FIRMWARE = str(HERE.parent / "firmware" / "GMxMGxx_11.800")
COMMITTED_CSV = HERE.parent / "annotations" / "trampoline-target-census.csv"
FORWARDER_CSV = HERE.parent / "annotations" / "forwarder-targets.csv"
CALL_TARGETS_CSV = HERE.parent / "annotations" / "bank-call-targets.csv"
TOOL = str(HERE / "trampoline_target_census.py")

# `bank-call-audit.md` section 4's four addresses. It names them as the
# bucket-B targets that begin with a lone `0xFF` and continue into ordinary
# code -- the four a one-byte test reported as calls into erased flash. They are
# the rule's real-image regression and they are transcribed rather than found,
# so a run that had quietly changed one would be caught.
SECTION_4_LONE_FF = (0xBAD4, 0xBAF4, 0xBB90, 0xBD54)

# The two the reset-vector write-up read, with what it read. Issue #559, in
# `docs/findings/reset-vector-dptr-targets.md`: `common,158E` carries
# `mov DPTR,#0xD89F` and the byte there is a single `ret`; `common,1594`
# carries `mov DPTR,#0xD96C` and the byte there is `mov DPTR,#0x0100`. Neither
# has a committed listing, which is that write-up's own "The export is deferred"
# and is asserted here as the empty cell it produces -- a claim about the
# export, not about the bytes.
RESET_VECTOR_TARGETS = (0x158E, 0xD89F, 0x22), (0x1594, 0xD96C, 0x90)


def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, strict=True))


def derived_block_entries():
    """{entry: (bank, target)} for the entries the census is scoped to.

    `audit_call_targets.trampolines()` is called here rather than a count being
    written out, so a firmware dump or a framing correction that moved the block
    does not redden this suite for a reason nobody re-derived. The filter is the
    census's own scope -- the two addresses it names, read off the tool rather
    than restated -- so a change to one without the other is caught.
    """
    d = Path(FIRMWARE).read_bytes()
    return {e: (b, t)
            for e, (b, t) in act.trampolines(d, act.bank_switch_stubs(d)).items()
            if ttc.BLOCK_LO <= e <= ttc.BLOCK_HI}


def stub_banks():
    """The banks `find_stubs()` reports, which need not all be mapped.

    `REGIONS` maps fewer banks than the image has stubs for, and the refusal
    `bank_region()` makes is about that gap rather than about the census, so it
    is asked on the stubs' own answer.
    """
    return [bank for _addr, bank in find_stubs(Path(FIRMWARE).read_bytes())]


class CommittedTableTests(unittest.TestCase):
    """The committed CSV, read against the image rather than against the tool."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        cls.rows = read_csv(COMMITTED_CSV)
        cls.by_offset = {int(r["file_offset"], 16): r for r in cls.rows}
        cls.stubs = {addr: bank for addr, bank in find_stubs(cls.d)}
        cls.runs = {b: act.erased_runs(cls.d, *act.region_bounds("bank%d" % b))
                    for b in {int(r["selects_bank"]) for r in cls.rows}}

    def target_offset(self, row):
        """The file offset the row's own cells say its target byte was read at.

        Derived from `selects_bank` and `target` rather than from a column, so
        the test re-derives the arithmetic the census performed instead of
        comparing one column with a copy of itself. The window assertion is part
        of the answer, not a guard around it: an offset outside the bank the row
        names is the withdrawn `bank1,19A8` count, and the failure says so.
        """
        lo, hi = act.region_bounds("bank" + row["selects_bank"])
        off = lo + int(row["target"], 16) - 0x8000
        self.assertTrue(lo <= off < hi,
                        f"{row['file_offset']}: 0x{off:05X} is outside the "
                        f"bank-{row['selects_bank']} window the row names")
        return off

    # --- the population, as a relationship --------------------------------

    def test_one_row_per_block_entry_in_both_directions(self):
        want = derived_block_entries()
        self.assertEqual(
            set(self.by_offset), set(want),
            "the committed rows are not the entries `trampolines()` finds inside "
            f"the block; only in the CSV: {sorted(set(self.by_offset) - set(want))}; "
            f"only in the image: {sorted(set(want) - set(self.by_offset))}")
        self.assertEqual(len(self.rows), len(self.by_offset),
                         "two rows carry one file_offset")

    def test_no_row_outside_the_block(self):
        for off in self.by_offset:
            self.assertTrue(ttc.BLOCK_LO <= off <= ttc.BLOCK_HI,
                            f"0x{off:04X} is outside the block this census is "
                            "scoped to")

    def test_the_header_is_the_census_shape_plus_five_columns(self):
        census = read_csv(CALL_TARGETS_CSV)
        self.assertEqual(list(census[0])[:13], ttc.CSV_HEAD[:13],
                         "the first thirteen columns are `bank-call-targets.csv`"
                         "'s own, in its order, so the two tables read as one "
                         "family")
        self.assertEqual(ttc.CSV_HEAD[13:],
                         ["selects_bank", "stub", "target_class", "target_byte",
                          "listing"])

    def test_the_framing_is_a_constant_not_a_count(self):
        # The block's extent and stride are properties of the census's scope,
        # not figures to be re-derived here: they are the two constants this
        # write-up and `bank-call-audit.md` section 3 both cite.
        self.assertEqual((ttc.BLOCK_LO, ttc.BLOCK_HI), (0x1150, 0x1ABC))
        self.assertEqual(act.TRAMP_STRIDE, ttc.TRAMP_STRIDE,
                         "the stride is the one `audit_call_targets.py` "
                         "already publishes")
        self.assertEqual((min(self.by_offset), max(self.by_offset)),
                         (ttc.BLOCK_LO, ttc.BLOCK_HI),
                         "the committed rows start and end on the bounds the "
                         "census names, rather than inside them")
        self.assertEqual(max(self.by_offset) - min(self.by_offset),
                         (len(self.by_offset) - 1) * ttc.TRAMP_STRIDE,
                         "the rows are one unbroken stride with no gap, which is "
                         "what makes the two bounds a description of the block "
                         "rather than two addresses somewhere inside it")

    def test_every_entry_is_the_six_byte_shape(self):
        for off in sorted(self.by_offset):
            six = self.d[off:off + ttc.TRAMP_STRIDE]
            self.assertEqual(six[:1], bytes([ttc.MOV_DPTR]),
                             f"0x{off:04X} does not open with `mov dptr,#imm16`: "
                             f"{six.hex(' ')}")
            self.assertIn(six[3], ttc.TAIL_OPCODES,
                          f"0x{off:04X} has no tail instruction: {six.hex(' ')}")
            self.assertIn((six[4] << 8) | six[5], self.stubs,
                          f"0x{off:04X} tail-jumps to an address that is not a "
                          "stub `find_stubs()` found")

    # --- the ordering, which is the method --------------------------------

    def test_the_bank_is_the_stub_s_and_not_the_row_s_region(self):
        for off, row in sorted(self.by_offset.items()):
            self.assertEqual(int(row["stub"], 16),
                             (self.d[off + 4] << 8) | self.d[off + 5],
                             f"0x{off:04X}: `stub` is not the entry's own tail "
                             "operand")
            self.assertEqual(int(row["selects_bank"]),
                             self.stubs[int(row["stub"], 16)],
                             f"0x{off:04X}: `selects_bank` is not the bank that "
                             "stub selects")
            # Every entry is common-area code, so there is no other bank the
            # byte could have been read in. That is what makes `selects_bank`
            # the only answer rather than one of two.
            self.assertEqual(row["region"], "common")
            self.assertLess(off, 0x8000)

    def test_target_byte_is_the_image_at_the_row_s_own_offset(self):
        for off, row in sorted(self.by_offset.items()):
            off_t = self.target_offset(row)
            self.assertEqual(self.d[off_t], int(row["target_byte"], 16),
                             f"0x{off:04X}: `target_byte` is not the byte at "
                             f"file 0x{off_t:05X}, which is where the row's own "
                             "`selects_bank` and `target` say it was read")

    def test_target_class_is_recomputed_from_the_image(self):
        for off, row in sorted(self.by_offset.items()):
            bank = int(row["selects_bank"])
            want = act.byte_class(self.d, self.target_offset(row), self.runs[bank])
            self.assertEqual(row["target_class"], want,
                             f"0x{off:04X}: `target_class` disagrees with "
                             f"`byte_class()` at the row's own offset "
                             f"(got {row['target_class']!r}, expected {want!r})")
            self.assertIn(row["target_class"], ttc.CLASSES)

    def test_the_census_columns_join_with_bank_call_targets(self):
        # The row's tail `ljmp` is a real row of the census, three bytes above
        # the entry, and joining on it is what makes "this table is a sibling of
        # that one" a checkable claim rather than a shape comment.
        census = {int(r["file_offset"], 16): r for r in read_csv(CALL_TARGETS_CSV)}
        for off, row in sorted(self.by_offset.items()):
            tail = census.get(off + 3)
            self.assertIsNotNone(tail, f"0x{off:04X}: the census has no row for "
                                       "the tail instruction at +3")
            self.assertEqual(tail["opcode"], row["opcode"])
            self.assertEqual(tail["region"], row["region"])
            self.assertEqual(int(tail["target"], 16), int(row["stub"], 16),
                             f"0x{off:04X}: the census's branch operand and "
                             "`stub` are not the same address")
            self.assertEqual(int(tail["calls_stub"]), int(row["selects_bank"]),
                             f"0x{off:04X}: the census's `calls_stub` and "
                             "`selects_bank` disagree")

    def test_the_four_columns_with_no_answer_are_empty(self):
        # `bucket`, `calls_trampoline`, `own_bank` and `other_bank` answer
        # absolute-form questions a DPTR immediate does not raise; a value in
        # any of them would be a claim the row has no way to support.
        for off, row in sorted(self.by_offset.items()):
            for col in ("bucket", "calls_trampoline", "own_bank", "other_bank"):
                self.assertEqual(row[col], "",
                                 f"0x{off:04X}: `{col}` carries a value on a row "
                                 "that has no answer for it")

    # --- the named addresses, which are the finding ------------------------

    def test_the_two_targets_the_reset_vector_read_reproduce(self):
        for entry, target, byte in RESET_VECTOR_TARGETS:
            row = self.by_offset.get(entry)
            self.assertIsNotNone(row,
                                 f"no committed row for the entry at 0x{entry:04X}")
            self.assertEqual(int(row["target"], 16), target,
                             f"0x{entry:04X}: `target` disagrees with "
                             "reset-vector-dptr-targets.md")
            self.assertEqual(int(row["target_byte"], 16), byte,
                             f"0x{entry:04X}: `target_byte` disagrees with the "
                             "byte that write-up read")
            # Both rows are common-area and both route through the bank-0 stub,
            # which is the write-up's own claim and the one #255's correction
            # is about.
            self.assertEqual(row["region"], "common")
            self.assertEqual(int(row["selects_bank"]), 0)
            self.assertEqual(row["listing"], "",
                             f"0x{entry:04X}: the census reports a covering "
                             "listing, and reset-vector-dptr-targets.md records "
                             "the export covering it as deferred")

    # --- the 16-byte rule, on a fixture and on the image -------------------

    def test_the_run_rule_boundary_on_a_fixture(self):
        lo, hi = act.region_bounds("bank0")
        for runlen, want in ((ttc.RUN_LENGTH_EDGE, "other"),
                             (ttc.RUN_LENGTH_EDGE + 1, "erased")):
            buf = bytearray(self.d)
            buf[lo:lo + runlen] = b"\xFF" * runlen
            buf[lo + runlen] = 0x22
            got = act.byte_class(bytes(buf), lo,
                                 act.erased_runs(bytes(buf), lo, hi))
            self.assertEqual(got, want,
                             f"a run of {runlen} 0xFF bytes read `{got}`, "
                             f"expected `{want}`")

    def test_section_4_s_four_lone_ff_targets_read_other_not_erased(self):
        lo, hi = act.region_bounds("bank0")
        runs = act.erased_runs(self.d, lo, hi)
        for target in SECTION_4_LONE_FF:
            self.assertEqual(self.d[target], 0xFF,
                             f"0x{target:04X} no longer opens with 0xFF, so the "
                             "audit's own regression has moved")
            self.assertEqual(act.byte_class(self.d, target, runs), "other",
                             f"0x{target:04X}: bank 0 reads this target as "
                             "erased, which is the reading the 16-byte rule "
                             "exists to prevent")

    # --- coverage ----------------------------------------------------------

    def test_listing_coverage_is_the_span_lookup_and_nothing_else(self):
        spans = ttc.listing_spans()
        for off, row in sorted(self.by_offset.items()):
            want = ttc.covering_listings(spans, int(row["selects_bank"]),
                                         int(row["target"], 16))
            self.assertEqual(row["listing"], "; ".join(want),
                             f"0x{off:04X}: `listing` disagrees with the spans "
                             "`listing-index.csv` holds in the bank this row's "
                             "own stub selects")
        # The issue asks for the number of targets nothing covers and says to
        # stop there. It is printed on every run rather than written as a
        # literal here, because a literal would be a value every landing
        # listing has to edit -- and there is nothing to assert about it here
        # beyond the partition the loop above already checks row by row.
        uncovered = sum(1 for r in self.rows if not r["listing"])
        print(f"\n  {uncovered} of {len(self.rows)} committed targets are not "
              "covered by a listing in the bank their stub selects")

    def test_a_covering_listing_is_in_the_row_s_own_bank(self):
        # The `bank1,19A8` failure as a property of the table: a listing that
        # covers the address in the other bank must not be what fills this row's
        # cell. Checked against the spans rather than by counting rows, so it
        # holds however the coverage splits.
        spans = ttc.listing_spans()
        for off, row in sorted(self.by_offset.items()):
            if not row["listing"]:
                continue
            program = "bank" + row["selects_bank"]
            target = int(row["target"], 16)
            own = [out for prog, also, lo, hi, out in spans
                   if lo <= target < hi
                   and (prog == program
                        or (prog == "common" and program in also.split(";")))]
            self.assertTrue(set(row["listing"].split("; ")) <= set(own),
                            f"0x{off:04X}: the filled `listing` cell names a "
                            "span that is not in the bank this row's own stub "
                            f"selects -- own bank has {own or 'none'}")

    def test_the_agreeing_census_and_this_table_split_coverage_the_same_way(self):
        # Two committed tables, one population, two derivations: this one from
        # `listing-index.csv` spans, `census_forwarder_targets.py`'s from the
        # committed `.asm` instruction starts. Asserting they agree is what
        # makes either a check on the other.
        other = {int(r["forwarder"], 16): r for r in read_csv(FORWARDER_CSV)}
        self.assertEqual(set(self.by_offset), set(other),
                         "the two committed tables are not the same entries; one "
                         "of them has moved")
        for off, row in sorted(self.by_offset.items()):
            self.assertEqual(int(other[off]["target"], 16), int(row["target"], 16),
                             f"0x{off:04X}: the two tables name different targets")
            self.assertEqual(int(other[off]["bank"]), int(row["selects_bank"]),
                             f"0x{off:04X}: the two tables disagree on the bank "
                             "the stub selects")
            self.assertEqual(bool(row["listing"]),
                             other[off]["class"] in ("entry", "operand"),
                             f"0x{off:04X}: this table reports "
                             f"{'covered' if row['listing'] else 'not covered'} "
                             f"and forwarder-targets.csv reports "
                             f"{other[off]['class']!r}")


class ToolModeTests(unittest.TestCase):
    """`--check` in both directions, and the mode refusals.

    A `--check` that has quietly stopped failing looks exactly like a `--check`
    that is working, so the doctored and the absent table are both driven here
    rather than trusted.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()

    def assert_check_fails(self, doctored_text, what):
        with tempfile.TemporaryDirectory() as tmp:
            doctored = Path(tmp) / "trampoline-target-census.csv"
            doctored.write_text(doctored_text)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), \
                    contextlib.redirect_stderr(buf):
                rc = ttc.check_csv(self.d, str(doctored))
            self.assertEqual(rc, 1, f"a {what} committed table passed --check")
            self.assertIn("not what this run derives", buf.getvalue())

    def test_the_committed_table_is_what_this_run_derives(self):
        self.assertEqual(ttc.csv_text(self.d), COMMITTED_CSV.read_text())

    def test_a_doctored_bank_fails(self):
        # `selects_bank` is the column the whole method turns on: a row that
        # names the wrong bank would be read in the wrong window, which is the
        # withdrawn `bank1,19A8` count wearing a table.
        self.assert_check_fails(
            COMMITTED_CSV.read_text().replace(",0,0x1100,", ",1,0x1100,", 1),
            "bank-doctored")

    def test_a_doctored_target_byte_fails(self):
        self.assert_check_fails(
            COMMITTED_CSV.read_text().replace(",0x22,", ",0x90,", 1),
            "byte-doctored")

    def test_a_doctored_class_fails(self):
        self.assert_check_fails(
            COMMITTED_CSV.read_text().replace(",other,", ",entry,", 1),
            "class-doctored")

    def test_a_truncated_csv_fails(self):
        # The other direction: a table that lost rows is a red run too, and a
        # check that only noticed *changed* cells would not notice this.
        text = COMMITTED_CSV.read_text()
        self.assert_check_fails("\n".join(text.splitlines()[:-1]) + "\n",
                                "truncated")

    def test_a_missing_csv_fails_rather_than_being_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / "trampoline-target-census.csv"
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                rc = ttc.check_csv(self.d, str(absent))
            self.assertEqual(rc, 1)
            self.assertIn("never", buf.getvalue())
            self.assertFalse(absent.exists(),
                             "--check created the file it was asked to check")

    def test_write_and_check_are_refused_together(self):
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--check", "--write"],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not allowed with", result.stderr)

    def test_check_and_self_test_are_refused_together(self):
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--check", "--self-test"],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not allowed with", result.stderr)

    def test_an_image_that_is_not_the_recorded_one_is_refused(self):
        # The tool looks for the PD marker the recorded figures were taken
        # from. A run against some other image would otherwise answer with
        # figures about it and nothing in the output would say so.
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "not-the-ec.bin"
            other.write_bytes(b"\x00" * 0x20040)
            result = subprocess.run(
                [sys.executable, TOOL, str(other), "--csv"],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("not the image", result.stderr)

    def test_a_refused_target_is_not_read_from_a_neighbouring_bank(self):
        # `target_file_offset()` returns None rather than an offset, and
        # `census()` turns that into a refusal. Asserted through the function
        # because the committed image holds no target that trips it -- and a
        # guard that only ever runs against conforming input is not a guard.
        for bank in (0, 1):
            self.assertIsNone(ttc.target_file_offset(bank, 0x7FFF))
            self.assertIsNone(ttc.target_file_offset(bank, 0x10000))
            self.assertIsNotNone(ttc.target_file_offset(bank, 0x8000))
            self.assertIsNotNone(ttc.target_file_offset(bank, 0xFFFF))

    def test_a_bank_the_region_table_does_not_map_is_refused(self):
        mapped = {int(n[4:]) for n, _, _, _, _ in txr.REGIONS
                  if n.startswith("bank")}
        named = {int(r["selects_bank"]) for r in read_csv(COMMITTED_CSV)}
        unmapped = sorted((set(stub_banks()) | named) - mapped)
        self.assertTrue(unmapped, "every bank either the stubs or the table "
                                  "names is mapped, so this case has nothing to "
                                  "refuse and is not testing the refusal")
        for bank in unmapped:
            with self.assertRaises(SystemExit, msg=f"bank {bank}"):
                ttc.bank_region(bank)


if __name__ == "__main__":
    unittest.main()