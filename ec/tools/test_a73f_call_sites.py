#!/usr/bin/env python3
"""Cases for `a73f_call_sites.py`.

The tool makes two claims that are easy to get quietly wrong: that the
population it reports is every transfer into the target rather than the
`lcall` subset a raw opcode scan would find, and that the `r7` column is a
backward byte-pattern scan rather than a decoded walk. The committed-image
cases pin both against `ec/firmware/GMxMGxx_11.800`; the fixture cases cover
the scan's edges, which that image does not contain -- a `7f` that is a DPTR
operand byte, a site nothing branches to -- and a rule nothing reaches is a
rule nothing tests.

The window has to reach past 44, or `0xC5A5` and `0xC603` come back empty and
the published payload set is short the values the image holds. Widening it
alone is not enough either: the same window then reaches `0xC827`, a
`mov r7,#0x12` belonging to an unrelated dispatch, and would publish `0x12`
for `0xC848`. The branch check is what separates those two cases, so both
sides of it are asserted here.
"""

import csv
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import a73f_call_sites as a73f  # noqa: E402


def image():
    with open(FIRMWARE, "rb") as handle:
        return handle.read()


class ThePopulation(unittest.TestCase):
    """What the tool enumerates, which is the census and not `12 a7 3f`."""

    def setUp(self):
        self.data = image()
        self.census = a73f.read_census(a73f.targets_csv_path())

    def test_it_reads_the_committed_census(self):
        self.assertTrue(self.census)
        for row in self.census:
            self.assertEqual(row["target"].lower(), "0xa73f", row["runtime"])

    def test_every_site_decodes_to_the_transfer_the_row_claims(self):
        # A `file_offset` that drifts off the instruction boundary would
        # still be a row; the tool's population is only the population if the
        # bytes at each offset really are the transfer named.
        opcode = {"lcall": b"\x12", "ljmp": b"\x02"}
        for row in self.census:
            site = int(row["file_offset"], 16)
            want = opcode[row["opcode"]] + b"\xa7\x3f"
            self.assertEqual(self.data[site:site + 3], want, row["runtime"])

    def test_it_finds_the_tail_jumps_a_raw_lcall_scan_misses(self):
        # The reason the tool reads the census rather than scanning for the
        # `lcall` encoding: `02 a7 3f` transfers into the target too, and an
        # opcode-specific scan cannot see them. Losing that population is
        # silent -- every remaining row is still a real site -- so it is
        # asserted rather than left to a reader noticing the number is
        # smaller than expected.
        tails = [r for r in self.census if r["opcode"] == "ljmp"]
        self.assertTrue(tails, "no ljmp into the target in the census")
        for row in tails:
            site = int(row["file_offset"], 16)
            self.assertEqual(self.data[site:site + 3], b"\x02\xa7\x3f")

    def test_a_target_with_no_transfers_yields_no_rows(self):
        # The target filter lives in `read_census`, so it is exercised there
        # and against a census of our own rather than by handing `rows_for` a
        # row it was never asked to filter.
        text = ("region,runtime,opcode,file_offset,target\n"
                "bank0,0x0000,lcall,0x00000,0x9999\n")
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write(text)
            path = fh.name
        try:
            self.assertEqual(a73f.read_census(path), [])
        finally:
            os.unlink(path)


class TheR7Scan(unittest.TestCase):
    """`r7` is a byte-pattern scan with a gap, and its edges are its own."""

    @staticmethod
    def buffer(pairs, site):
        """A buffer carrying `(offset, bytes)` pairs, read at `site`."""
        buf = bytearray(b"\x00" * 64)
        for at, raw in pairs:
            buf[at:at + len(raw)] = raw
        return bytes(buf)

    def test_the_adjacent_pair_is_found_at_gap_two(self):
        buf = self.buffer([(42, b"\x7f\x5a")], 44)
        self.assertEqual(a73f.nearest_mov_r7(buf, 44), (0x5A, 2, 42))

    def test_the_nearest_pair_wins_over_an_older_one(self):
        buf = self.buffer([(20, b"\x7f\x11"), (42, b"\x7f\x5a")], 44)
        self.assertEqual(a73f.nearest_mov_r7(buf, 44), (0x5A, 2, 42))

    def test_a_7f_that_is_an_operand_byte_is_still_reported(self):
        # The scan does not decode, so a `7f` that is the low byte of a
        # `mov dptr,#imm16` is indistinguishable from the opcode. The gap
        # column is what a reader has to weigh it with, which is why an
        # operand-byte hit is a reported value rather than a refusal.
        buf = self.buffer([(10, b"\x90\x7f")], 44)
        self.assertEqual(a73f.nearest_mov_r7(buf, 44, window=32)[0], None)
        # Reported value is whatever follows the `7f`, which here is the zero
        # behind the pair rather than an immediate at all -- the scan pairs
        # bytes and does not know the difference.
        self.assertEqual(a73f.nearest_mov_r7(buf, 44, window=40), (0x00, 33, 11))

    def test_no_pair_in_range_reads_as_not_found(self):
        # "Not found by this scan", never a value: the distinction is the
        # whole reason the cell is empty rather than zero.
        value, gap, at = a73f.nearest_mov_r7(bytes(64), 44)
        self.assertIsNone(value)
        self.assertIsNone(gap)
        self.assertIsNone(at)

    def test_a_pair_beyond_the_window_is_not_read(self):
        buf = self.buffer([(20, b"\x7f\x11")], 44)
        self.assertIsNone(a73f.nearest_mov_r7(buf, 44, window=8)[0])
        self.assertEqual(a73f.nearest_mov_r7(buf, 44, window=32)[0], 0x11)

    def test_the_window_is_not_widened_to_reach_a_buffer_edge(self):
        # A negative index would silently wrap to the far end of the buffer
        # in Python, so the last byte is made a `7f` that an unguarded read
        # would find. The guard is what stops the scan reporting it.
        buf = bytearray(b"\x00" * 64)
        buf[63] = 0x7F
        self.assertIsNone(a73f.nearest_mov_r7(bytes(buf), 1, window=32)[0])


class TheBranchCorroboration(unittest.TestCase):
    """A far `7f nn` is published only if a forward branch delivers it.

    This is the check that makes the window safe to widen: the image holds a
    `mov r7,#0x12` at `0xC827` in a run of `7f nn` / `lcall 0x2990` pairs
    that tail-jumps away at `0xC829`, and nothing connects it to the site at
    `0xC848`.
    """

    def test_it_finds_the_branch_that_reaches_a_site(self):
        data = image()
        # `0xC5A5` is reached by the `sjmp` at `0xC57B`, which follows the
        # `mov R7,#0xB1` at `0xC579`.
        self.assertEqual(a73f.branch_into(data, 0xC5A5, 0xC579), 0xC57B)
        self.assertEqual(a73f.branch_into(data, 0xC603, 0xC5D7), 0xC5D9)

    def test_no_branch_into_a_site_reads_as_absent(self):
        self.assertIsNone(a73f.branch_into(image(), 0xC848, 0xC800))

    def test_a_pair_nothing_branches_to_the_site_is_not_published(self):
        # The regression the widened window would otherwise introduce: this
        # is exactly the `0xC848` shape, and the answer has to stay empty.
        buf = bytearray(b"\x00" * 64)
        buf[10:12] = b"\x7f\x12"
        buf[44:47] = b"\x12\xa7\x3f"
        row = [{"region": "bank0", "runtime": "0x002C", "opcode": "lcall",
                "file_offset": "0x0002C"}]
        got = a73f.rows_for(bytes(buf), row, window=64)[0]
        self.assertEqual(got["r7"], "")
        self.assertEqual(got["r7_gap"], "")
        self.assertEqual(got["r7_branch"], "")

    def test_a_pair_a_branch_does_reach_the_site_is_published(self):
        buf = bytearray(b"\x00" * 64)
        buf[10:12] = b"\x7f\x12"
        buf[12:14] = b"\x80\x1e"          # `sjmp` to 0x002C
        buf[44:47] = b"\x12\xa7\x3f"
        row = [{"region": "bank0", "runtime": "0x002C", "opcode": "lcall",
                "file_offset": "0x0002C"}]
        got = a73f.rows_for(bytes(buf), row, window=64)[0]
        self.assertEqual(got["r7"], "0x12")
        self.assertEqual(got["r7_branch"], "0x000C")

    def test_a_branch_from_before_the_pair_is_not_corroboration(self):
        # The load has to come first, or the branch delivers some other
        # value. `sjmp` at `0x08` targets the site but precedes the pair.
        buf = bytearray(b"\x00" * 64)
        buf[8:10] = b"\x80\x22"           # `sjmp` to 0x002C
        buf[10:12] = b"\x7f\x12"
        buf[44:47] = b"\x12\xa7\x3f"
        row = [{"region": "bank0", "runtime": "0x002C", "opcode": "lcall",
                "file_offset": "0x0002C"}]
        self.assertEqual(a73f.branch_into(bytes(buf), 44, 10), None)
        self.assertEqual(a73f.rows_for(bytes(buf), row, window=64)[0]["r7"],
                         "")


class TheCommittedReading(unittest.TestCase):
    """What the run over the committed image actually reports."""

    def setUp(self):
        self.rows = a73f.rows_for(image(),
                                  a73f.read_census(a73f.targets_csv_path()))

    def test_a_reading_further_back_than_the_adjacent_pair_is_corroborated(self):
        # Recorded because it is the property that lets the window be wide:
        # the gap column is not a weaker claim on its own, it is one that
        # carries a branch. If a future edit moves a site's load, the branch
        # check is what stops the reading silently following it.
        for row in self.rows:
            if row["r7"] and row["r7_gap"] != "2":
                self.assertTrue(row["r7_branch"],
                                f"{row['runtime']} has no branch")
                at = int(row["r7_at"], 16)
                self.assertLess(at, int(row["r7_branch"], 16))

    def test_the_window_reaches_the_loads_the_issue_named(self):
        # `C55F.asm` and `C5BD.asm` both load R7 and branch to their site's
        # transfer. A window narrower than 44 drops both, and the payload set
        # the write-up publishes is then short those two values.
        self.assertGreater(a73f.WINDOW, 44)
        got = {r["runtime"]: r for r in self.rows}
        self.assertEqual(got["0xC5A5"]["r7"], "0xB1")
        self.assertEqual(got["0xC603"]["r7"], "0xB2")

    def test_an_unresolved_site_leaves_the_r7_cells_empty(self):
        unresolved = [r for r in self.rows if not r["r7"]]
        self.assertTrue(unresolved, "every site resolved; the empty case is gone")
        for row in unresolved:
            self.assertEqual(row["r7_gap"], "")
            self.assertEqual(row["r7_at"], "")
            self.assertEqual(row["r7_branch"], "")

    def test_the_table_is_reproducible(self):
        again = a73f.rows_for(image(),
                              a73f.read_census(a73f.targets_csv_path()))
        self.assertEqual(a73f.csv_table(self.rows), a73f.csv_table(again))

    def test_the_csv_carries_every_site_and_only_its_own_columns(self):
        parsed = list(csv.DictReader(io.StringIO(a73f.csv_table(self.rows))))
        self.assertEqual(len(parsed), len(self.rows))
        self.assertEqual(list(parsed[0]), list(a73f.COLUMNS))


class TheSelfTest(unittest.TestCase):
    def test_it_passes_on_the_committed_image(self):
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = a73f.self_test(image(), a73f.read_census(a73f.targets_csv_path()))
        self.assertEqual(rc, 0, buf.getvalue())


if __name__ == "__main__":
    unittest.main()