#!/usr/bin/env python3
"""The bank0 `0xC118` thunk is a listing in the tree, and the two programs'
`0xC118` are not the same bytes.

`bank0 0xC118` is the address bank1's `trampoline_to_c118` reaches, through
the common-area bank-select stub, so it is a bank-0 address read in bank 0
(ec/annotations/bank-call-audit.md section 2). It carries no listing of its own
before issue #337's seed, and the six `ghidra-variables.csv` rows that branch on
the R7 it leaves each said so -- they rested on a reading of the image. This
suite holds the three claims that seed was for:

- **The listing is the image.** `bank0/C118.asm`'s instruction bytes are the
  firmware's own bytes at that address, read through `verify_reassembly`'s
  reader and its bank images rather than through a decoder written here, so a
  listing that disagreed with the firmware would fail here rather than
  somewhere downstream.
- **The bank contrast, which is the claim that never goes stale.** bank0
  `0x0C118` opens `12 c0 e7`; bank1's own `0x14118` is `f3 4d f0 22`, byte 1 of
  the `anl A,#0xf3` at `0x14117` in a different program. Both were read as one
  address and produced a reading that a listing now contradicts; this is the
  assertion that retires that confusion, and it is measured from the image on
  both sides rather than from either listing's text.
- **The six caller rows cite the listing.** Each of the six names
  `ec/decompiled/bank0/C118.asm` in its `evidence` cell, which is what moved
  those rows from a reading of the image to a statement about a committed
  listing.

What this suite deliberately does not assert: anything about `0xC10C`, the
sibling thunk twelve bytes earlier and issue #255's. A case holding "`0xC10C`
is not exported" would be a value #255 has to edit on landing, and the four
thunks in that run are recorded as a gap in
`docs/findings/bank0-c118-3202-bit0-thunk.md` instead.

No hardware, no Windows, no Ghidra: the firmware and the committed listings are
both on disk, which is the same reason the rest of the `ec/tools` suites need
nothing else.
"""
import csv
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import verify_gap_text as G          # noqa: E402  (needs the path set first)
import verify_reassembly as V         # noqa: E402  (needs the path set first)

FIRMWARE = REPO / "ec" / "firmware" / "GMxMGxx_11.800"
ANNOT = REPO / "ec" / "annotations"
DECOMPILED = REPO / "ec" / "decompiled"

LISTING = DECOMPILED / "bank0" / "C118.asm"

# The six `ghidra-variables.csv` rows whose comments branch on the R7 this
# address leaves. Four are keyed `r7_from_a_callee` and two `r7_from_19a8`,
# because one identifier per row covers both callees those listings call; the
# set is the six *addresses*, not the two keys -- `0x90B8` is the row that
# shows why, since its single key `r7_from_1984` covers three callees at once
# and 0xC118 is one of them.
CALLER_ROWS = ("0x90B8", "0x9199", "0x9CC0", "0xA064", "0xA4CF", "0xC614")

LISTING_CITED = "ec/decompiled/bank0/C118.asm"

# The four instruction bytes each bank's image holds at this address's file
# offset, read below rather than written here: what this suite pins is that
# the two disagree and that bank0's agree with the listing.
BANK0_BYTES = bytes.fromhex("12 c0 e7".replace(" ", ""))
BANK1_BYTES = bytes.fromhex("f34df022")


# Loaded once at import rather than per case, for the reason
# `test_citation_gap_scan.py` gives and for the same reader: these are 192 KiB
# of the committed firmware, and `load_images` leaves its handles unclosed,
# which unittest's warning filters turn into a ResourceWarning from inside a
# test and not from an import. Both are shared files this suite does not own,
# so the suite arranges its own call rather than changing them.
_IMAGES = G.load_images()


class ListingIsTheImage(unittest.TestCase):
    """The listing's bytes are the firmware's bytes at the address it names."""

    def test_listing_starts_at_C118(self):
        insns = V.parse_listing(LISTING)
        self.assertTrue(insns, "bank0/C118.asm parsed to no instructions")
        self.assertEqual(insns[0][0], 0xC118)

    def test_listing_bytes_are_the_bank0_image_at_C118(self):
        insns = V.parse_listing(LISTING)
        text = b"".join(bytes.fromhex(b) for _a, b, _m, _o in insns)
        image = _IMAGES["bank0"]
        self.assertEqual(text, image[0xC118:0xC118 + len(text)])

    def test_the_whole_run_ends_where_the_next_listing_begins(self):
        # 0xC124 is the next bank0 listing, and it is 12 bytes after this one
        # starts: the thunk is exactly the twelve bytes before it, which is
        # what makes the four thunks in this run a run rather than a
        # coincidence of neighbouring addresses.
        insns = V.parse_listing(LISTING)
        last = insns[-1][0] + len(bytes.fromhex(insns[-1][1]))
        self.assertEqual(last, 0xC124)

    def test_the_call_target_is_the_annotated_callee(self):
        # The one instruction this suite reads as load-bearing: the thunk's
        # whole content is that it hands `test_3202_bit0`'s answer back in R7,
        # so a listing that stopped calling 0xC0E7 would no longer be the
        # routine the six caller rows describe.
        insns = V.parse_listing(LISTING)
        self.assertEqual(insns[0][2], "lcall")
        self.assertEqual(insns[0][3], "0xc0e7")

    def test_the_callee_is_the_row_the_annotation_names(self):
        # ...and that callee is a real listing of its own, so the chain the
        # annotation asserts is anchored at both ends.
        with (ANNOT / "ghidra-functions.csv").open() as f:
            names = {r["addr"]: r["name"] for r in csv.DictReader(f)}
        self.assertEqual(names.get("0xC0E7"), "test_3202_bit0")


class TheTwoBanksDisagree(unittest.TestCase):
    """The claim that retires the #262/#255 confusion, measured from the image.

    Both sides are read out of the firmware rather than out of either listing,
    because the failure this exists to catch was reading one address out of the
    wrong program -- so a case that took its expected bytes from a listing would
    inherit the very mistake it is meant to catch.
    """

    def setUp(self):
        self.image = FIRMWARE.read_bytes()

    def test_bank0_C118_opens_with_an_lcall(self):
        self.assertEqual(self.image[0x0C118:0x0C118 + 3], BANK0_BYTES)

    def test_bank1_C118_is_different_bytes(self):
        self.assertEqual(self.image[0x14118:0x14118 + 4], BANK1_BYTES)

    def test_the_two_are_not_equal(self):
        # The assertion proper. The two rows above would each pass against a
        # firmware where the banks agreed, if the expectation moved with them;
        # this one cannot.
        self.assertNotEqual(self.image[0x0C118:0x0C118 + 4],
                            self.image[0x14118:0x14118 + 4])

    def test_bank1_those_bytes_are_an_operand_of_the_instruction_before(self):
        # Why the bank-1 reading went wrong rather than merely differing: the
        # byte at bank1 0x14118 is byte 1 of the `anl A,#0xf3` that starts at
        # 0x14117, so a decode anchored there lands mid-instruction. This is
        # the shape of the withdrawn reading the CORRECTION blocks in the six
        # caller rows record, asserted so the two stay describable.
        self.assertEqual(self.image[0x14117:0x14117 + 2], b"\x54\xf3")


class CallerRowsCiteTheListing(unittest.TestCase):
    """The six rows rest on a listing rather than on a reading of the image."""

    def setUp(self):
        with (ANNOT / "ghidra-variables.csv").open() as f:
            self.rows = {r["addr"]: r for r in csv.DictReader(f)}

    def test_all_six_rows_are_present(self):
        # Named as the set they are, so a row that lost its address fails here
        # rather than silently dropping out of the check below.
        for addr in CALLER_ROWS:
            self.assertIn(addr, self.rows)

    def test_each_cites_the_listing(self):
        for addr in CALLER_ROWS:
            evidence = [p.strip() for p in self.rows[addr]["evidence"].split(";")]
            self.assertIn(LISTING_CITED, evidence,
                          "%s does not cite %s" % (addr, LISTING_CITED))

    def test_each_keeps_its_correction(self):
        # The 2026-09-24 blocks under #255 stay visible beside the citation
        # that supersedes the reading, per CLAUDE.md's calibration rule. A
        # check that only asserted the corrected text would pass on a silent
        # deletion of the wrong version, which is the failure the rule exists
        # to prevent.
        for addr in CALLER_ROWS:
            self.assertIn("CORRECTION 2026-09-24, issue #255",
                          self.rows[addr]["comment"],
                          "%s lost its CORRECTION block" % addr)


class TheAnnotationRowResolves(unittest.TestCase):
    """The seed row and the two files it cites are all where they are said to be."""

    def setUp(self):
        with (ANNOT / "ghidra-functions.csv").open() as f:
            self.row = next((r for r in csv.DictReader(f)
                             if r["scope"] == "bank0"
                             and r["addr"] == "0xC118"), None)

    def test_the_row_exists(self):
        self.assertIsNotNone(self.row)

    def test_its_evidence_files_are_on_disk(self):
        for path in self.row["evidence"].split(";"):
            self.assertTrue((REPO / path.strip()).is_file(), path)

    def test_its_name_takes_no_reserved_prefix(self):
        # `TongFang.isPlaceholderName()` treats a `thunk_` name as Ghidra's own
        # and the index then reports the row `annotated=no`, which is how the
        # first attempt at this name read: a hand-decoded row filed among the
        # machine's. The check that exists for that is
        # `grade_name_basis.reserved_prefix_problems`; this is the same
        # property held at the row that motivated it.
        import grade_name_basis as G
        self.assertEqual(G.reserved_prefix_problems([self.row]), [])

    def test_the_listing_carries_that_name(self):
        head = LISTING.read_text().splitlines()[0]
        self.assertIn(self.row["name"], head)


if __name__ == "__main__":
    unittest.main()