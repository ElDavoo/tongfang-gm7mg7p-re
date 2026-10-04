#!/usr/bin/env python3
"""`pd_pop_order_oracle.py` held to the image and to the committed prose, and
the falsifiable case that keeps it from passing vacuously.

`pd_pop_order_oracle.py --self-test` holds the byte shapes the census rests on.
This suite exists because a `--self-test` is a thing a person runs and this is a
thing `tools/run-tests.sh` collects, and because two of its four cases assert
against files the tool itself never reads -- so a tool that drifted from the
prose it claims to reproduce would fail here and not there.

The cases split by what each would catch, and the split is the point:

  1. **The `0x8038` table reproduces committed prose.** The eight arms and the
     `00 00` terminator and the `0x8274` default are what
     `ec/annotations/bank-call-audit.md` section 9 and
     `ec/annotations/ghidra-functions.csv` already name, from a hand decode. The
     tool re-derives them; this asserts them as literals transcribed from that
     prose, so the tool and the prose *can* disagree. It is a claim, not a
     census, which is why it is spelled out here rather than compared to
     another tool's output.
  2. **The census agrees with the committed spans.** Every site's entry count
     and well-formedness against `ec/annotations/index-table-spans.csv`. The
     tool imports `decode_index_table`, so this is close to tautological -- and
     that is why it is here rather than nowhere: it is the assertion that the
     import is the one that was intended and that the byte-order layer has not
     quietly re-walked anything behind it.
  3. **The two readings are computed differently.** Case 3 is the one that makes
     the other two mean anything. It asserts that exchanging the two bytes of an
     entry changes what the tool reports about it -- the arms, their resolution,
     the fall-through clause and the locality proxy all move. Without it, cases
     1 and 2 pass on a tool that reads one order and prints it twice.
  4. **`--self-test`'s byte-shape pins hold**, by importing the module and
     calling the function, the way `test_check_findings_frozen.py` holds its
     checker. It is the one case here that duplicates a self-test, and it earns
     that: the pins are what the whole argument rests on, and a suite is where
     a pin belongs.

**No case asserts a count of the tree**, per CLAUDE.md: no 201, no 15, no
per-table entry count as a literal. Cases 2 and 3 compute what they compare; the
only literals are the eight arms of case 1, which are a claim committed prose
already makes. A figure that moves on every re-export would be a value every
merge has to edit.

Nothing here opens a device, reads a register, or needs Windows or hardware:
every input is a committed file.
"""
import csv
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pd_pop_order_oracle as O
from decode_index_table import SITE_0X8038

FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
SPANS = HERE.parent / "annotations" / "index-table-spans.csv"

# The `0x8038` table as bank-call-audit.md section 9 records it and as
# ghidra-functions.csv names it: eight three-byte entries, a `00 00` terminator
# and a default of 0x8274. Transcribed here as (case, target) because those are
# the two things the prose states; the entry offsets follow from the stride and
# are asserted against the image separately below. This is a hand decode of one
# table, and it is the oracle case 1 exists for.
ARMS_0X8038 = ((0x00, 0x8054), (0x01, 0x8094), (0x02, 0x80D7), (0x03, 0x811A),
               (0x04, 0x815D), (0x05, 0x819D), (0x06, 0x81DF), (0x07, 0x8231))
TERMINATOR_0X8038 = b"\x00\x00"
DEFAULT_0X8038 = 0x8274

# A read-only handle on the committed image, shared by every case that needs it.
D = FIRMWARE.read_bytes()
ROWS = O.census(D)


def committed_spans() -> list:
    """The rows of `index-table-spans.csv`, read once and closed."""
    with SPANS.open(newline="") as handle:
        return list(csv.DictReader(handle))


SPANS_ROWS = committed_spans()


def table_0x8038():
    return O.decode_table(D, SITE_0X8038 + 3)


class ReproducesCommittedProse(unittest.TestCase):
    """Case 1: the table `bank-call-audit.md` section 9 read entry by entry."""

    def test_the_eight_arms_and_their_cases_are_the_committed_ones(self):
        tbl = table_0x8038()
        self.assertIsNotNone(tbl, f"no table after the `lcall` at "
                                  f"0x{SITE_0X8038:05X}")
        got = tuple((e["case"], e["target"]) for e in tbl["entries"])
        self.assertEqual(got, ARMS_0X8038)

    def test_the_terminator_and_the_default_are_the_committed_ones(self):
        tbl = table_0x8038()
        self.assertEqual(D[tbl["terminator_offset"]:tbl["terminator_offset"] + 2],
                         TERMINATOR_0X8038)
        self.assertEqual(tbl["default"], DEFAULT_0X8038)

    def test_the_entry_offsets_follow_from_the_three_byte_stride(self):
        # Section 9's block is `8054 00 | 8094 01 | ...`, so entry n sits at the
        # table base plus 3n. Asserted against the base rather than as literals,
        # because a table that moved would move the offsets with it and the
        # eight arms above would still be right.
        tbl = table_0x8038()
        for n, entry in enumerate(tbl["entries"]):
            self.assertEqual(entry["file_offset"], tbl["file_offset"] + 3 * n)

    def test_the_first_entry_is_what_the_annotation_row_says(self):
        # ghidra-functions.csv's `0x8038` row names "80 54 is entry 0's address
        # 0x8054" and calls the layout big-endian address then case value. If the
        # tool's decode disagreed with that the eight arms above could still pass
        # on a table that had been re-strided, so the row's own claim is checked
        # here against the image the row cites.
        tbl = table_0x8038()
        self.assertEqual(D[tbl["file_offset"]:tbl["file_offset"] + 2],
                         b"\x80\x54")


class AgreesWithCommittedSpans(unittest.TestCase):
    """Case 2: the census and `index-table-spans.csv` describe the same sites."""

    def test_every_site_is_one_the_committed_span_table_carries(self):
        self.assertEqual([f"0x{s['file_offset']:05X}" for _, s, _, _ in ROWS],
                         [r["site"] for r in SPANS_ROWS])

    def test_each_sites_entry_count_and_span_match_the_committed_row(self):
        by_site = {r["site"]: r for r in SPANS_ROWS}
        for _, site, tbl, bad in ROWS:
            row = by_site[f"0x{site['file_offset']:05X}"]
            with self.subTest(site=row["site"]):
                self.assertIsNotNone(tbl)
                self.assertEqual(str(len(tbl["entries"])), row["entries"])
                self.assertEqual(f"0x{tbl['file_offset']:05X}",
                                 row["table_file_offset"])
                self.assertEqual(f"0x{tbl['end']:05X}", row["table_end"])
                self.assertEqual("yes" if not bad else "no", row["well_formed"])

    def test_the_census_reports_no_site_the_committed_table_does_not(self):
        # The other direction, because a census that dropped a row would still
        # agree on the rows it kept. A committed `well_formed=no` would be a
        # finding about `decode_index_table`, and this case is where it would
        # show -- the tool reports it rather than reconciling it away.
        by_site = {f"0x{s['file_offset']:05X}": (t, b) for _, s, t, b in ROWS}
        for row in SPANS_ROWS:
            with self.subTest(site=row["site"]):
                tbl, bad = by_site[row["site"]]
                self.assertEqual(row["well_formed"],
                                 "no" if (tbl is None or bad) else "yes")


class TheTwoReadingsDiffer(unittest.TestCase):
    """Case 3: the falsifiable case.

    Every assertion here is about a *difference* between the two columns, so a
    tool that computed one order and printed it twice fails all of them, and
    cases 1 and 2 -- which only ever compare against committed files -- go on
    passing. That is the arrangement the case exists to catch.
    """

    def test_swapping_an_entry_changes_everything_derived_from_its_address(self):
        for _, _, tbl, _ in ROWS:
            if tbl is None:
                continue
            with self.subTest(site=f"0x{tbl['file_offset']:05X}"):
                direct = O.arms_of(tbl, O.READINGS[0])
                swapped = O.arms_of(tbl, O.READINGS[1])
                self.assertEqual(len(direct), len(swapped))
                self.assertNotEqual(direct, swapped)
                self.assertEqual(swapped,
                                 [O.byte_swapped(a) for a in direct])

    def test_the_census_reports_a_different_verdict_under_each_reading(self):
        good = {r: sum(1 for _, _, tbl, _ in ROWS if tbl is not None
                       and not O.well_formed_under(D, tbl, r))
                for r in O.READINGS}
        self.assertEqual(good[O.READINGS[0]], len(ROWS),
                         "every table is well-formed under the reading "
                         "bank-call-audit.md section 9 records")
        self.assertLess(good[O.READINGS[1]], len(ROWS),
                        "and not every table survives the swap -- if this "
                        "fails, the second column is the first one again")

    def test_the_fall_through_clause_is_what_separates_the_banked_tables(self):
        # The module docstring's claim, held: on a banked caller most byte-
        # swapped addresses still land in the caller's own 0x8000-0xFFFF window,
        # so `malformed()`'s resolution clause barely moves and the fall-through
        # clause is what fails. If the resolution clause started separating the
        # banked tables on its own, this file's explanation of the output would
        # be stale and the comment with it.
        banked = [(s, t) for _, s, t, _ in ROWS if t is not None
                  and s["region"].startswith("bank")]
        self.assertTrue(banked, "no banked table in the census; the region rule "
                                "the columns depend on has moved")
        for site, tbl in banked:
            with self.subTest(site=f"0x{site['file_offset']:05X}"):
                self.assertEqual(O.unresolved(tbl, O.READINGS[0]), 0)
                self.assertEqual(O.unresolved(tbl, O.READINGS[1]), 0)
                self.assertEqual(O.well_formed_under(D, tbl, O.READINGS[0]), [])
                self.assertNotEqual(O.well_formed_under(D, tbl, O.READINGS[1]),
                                    [])

    def test_the_locality_proxy_moves_and_is_still_only_a_proxy(self):
        # The proxy has to separate, or the census's third column says nothing.
        # It does not separate on every table and this file does not pretend it
        # does: `0x041EE`'s fourteen arms all sit one page above their own base,
        # so both readings score it 0-of-14 and the column is silent there. The
        # assertion is therefore that the swap never *raises* the rate and does
        # lower it on most tables -- which is what makes the column a proxy in
        # both directions, since a column that separates everywhere would be
        # being read as a test.
        dropped = 0
        for _, _, tbl, _ in ROWS:
            if tbl is None:
                continue
            direct = O.local_arms(tbl, O.READINGS[0])
            swapped = O.local_arms(tbl, O.READINGS[1])
            self.assertLessEqual(swapped[0], direct[0])
            self.assertEqual(direct[1], swapped[1],
                             "the denominators are the same arms either way")
            dropped += swapped[0] < direct[0]
        self.assertGreater(dropped, len(ROWS) // 2,
                           "the locality rate barely moves under the swap, so "
                           "the column is not measuring the order")
        tbl = table_0x8038()
        direct = O.local_arms(tbl, O.READINGS[0])
        self.assertLess(direct[0], direct[1],
                        "the direct reading is not every arm in its own page, "
                        "so quoting it as one would be the overclaim the module "
                        "docstring names")


class SelfTestPins(unittest.TestCase):
    """Case 4: `--self-test`'s byte shapes, called rather than shelled out to."""

    def test_the_byte_shape_pins_hold_against_the_committed_image(self):
        # Captured, because `self_test()` is a report rather than a predicate and
        # its "ok" lines would otherwise land in the middle of this suite's own
        # output -- where they read as tests that passed when they are
        # assertions *about* the pins. The exit code is the claim; the text is
        # attached to the failure so a red run says which pin went.
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = O.self_test(D)
        self.assertEqual(rc, 0, buf.getvalue())

    def test_the_pins_are_byte_patterns_and_not_addresses(self):
        # A pin spelled as an address would move silently with the reader; a pin
        # spelled as bytes and applied at the reader the search *finds* does not.
        for rel, raw, what in O.READER_ENTRY_BYTE:
            with self.subTest(what=what):
                self.assertEqual(len(raw) >= 2, True)
                self.assertEqual(D[O.readers(D)[0][0]["file_offset"] + rel:
                                   O.readers(D)[0][0]["file_offset"] + rel
                                   + len(raw)], raw)
        rel, raw, head = O.READER_STRIDE
        base = O.readers(D)[0][0]["file_offset"]
        self.assertEqual(D[base + rel:base + rel + len(raw)], raw)

    def test_the_swap_is_the_whole_of_the_difference(self):
        # `byte_swapped()` is what both columns differ by, so an address it does
        # not return to is a bug in the primitive every other case rests on.
        for addr in (0x0000, 0x0001, 0x00FF, 0x8038, 0x8054, 0xFFFF, 0x1234):
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(O.byte_swapped(O.byte_swapped(addr)), addr)
                self.assertEqual(O.byte_swapped(addr),
                                 ((addr & 0xFF) << 8) | (addr >> 8))


if __name__ == "__main__":
    unittest.main()
