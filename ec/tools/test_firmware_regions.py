#!/usr/bin/env python3
"""Checks for `firmware_regions.py`, over the committed image and a fixture.

The tool's `--self-test` pins the known answers and its own refusals. What it
cannot reach is a shape the committed image happens not to contain, and this
file is where those live: an image whose blocks take each verdict, whose
trailing block is partial, and whose image marker sits at an offset the
committed dump does not use.

**The fixture is the interesting half and the reason these two cannot be
merged.** A census tool that had quietly degraded into "every non-erased block
is code" would print the committed image's table correctly and pass every
assertion about it, because on that image the degradation is invisible: all
three non-erased blocks look alike. `testdata/firmware-regions/` supplies the
block that separates them -- one with the `ITE8850-PD` marker at `+0x1234`
rather than `+0x40`, which a search pinned to one offset cannot find, and
without it that block reads `not classified by this method` and the tool is
caught.

Nothing here was observed on hardware; the fixture is hand-written and the
committed image is a committed file.
"""
import contextlib
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import firmware_regions as fr

FIXTURE = os.path.join(HERE, "testdata", "firmware-regions",
                       "census-example-image.bin")


def run(*args):
    out = subprocess.run([sys.executable, os.path.join(HERE,
                                                       "firmware_regions.py")]
                         + list(args),
                         capture_output=True, text=True, cwd=HERE)
    return out.returncode, out.stdout, out.stderr


class CommittedImage(unittest.TestCase):
    """The properties of `ec/firmware/GMxMGxx_11.800` the write-up cites."""

    def setUp(self):
        with open(fr.FIRMWARE, "rb") as f:
            self.d = f.read()
        self.blocks = fr.census(self.d)
        self.by_base = {b["base"]: b for b in self.blocks}

    def test_the_erased_blocks_are_the_three_the_layout_names(self):
        erased = [b["base"] for b in self.blocks if b["verdict"] == fr.ERASED]
        self.assertEqual(erased, [0x18000, 0x30000, 0x38000])

    def test_the_0x28000_block_carries_pd_strings_and_is_not_marked(self):
        blk = self.by_base[0x28000]
        texts = {t for _off, t in blk["strings"]}
        self.assertIn("SRC Negotiate done", texts)
        self.assertIn("PR Swap", texts)
        self.assertIsNone(blk["marker"])
        # The architecture is *not* established, and the head byte is the
        # evidence for why a byte census cannot establish it: 0x01 is AJMP
        # here, where the three identified images open 0x02.
        self.assertEqual(blk["head"], 0x01)
        self.assertEqual(blk["head_shape"], "AJMP")

    def test_the_0x28000_block_is_distinct_from_the_0x20000_one(self):
        a, b = self.by_base[0x20000], self.by_base[0x28000]
        self.assertEqual(a["marker"], "ITE8850-PD")
        self.assertNotEqual(a["head"], b["head"])
        self.assertGreater(len(b["strings"]), len(a["strings"]))

    def test_no_block_is_ever_labelled_code(self):
        # The single invariant CLAUDE.md's calibration rule turns on for this
        # tool: a byte census separates erased from non-erased and nothing
        # more, so `code` must not be reachable as a verdict.
        for blk in self.blocks:
            self.assertIn(blk["verdict"],
                          (fr.ERASED, fr.NON_ERASED, fr.UNCLASSIFIED))
        self.assertNotEqual(fr.UNCLASSIFIED, "code")

    def test_bank_two_slot_is_measured_erased_and_bank_three_slot_is_not(self):
        stubs = fr.find_stubs(self.d)
        slots = fr.bank_slots(stubs)
        self.assertEqual(slots[2]["file_offset"], 0x18000)
        self.assertEqual(self.by_base[0x18000]["verdict"], fr.ERASED)
        self.assertEqual(slots[3]["file_offset"], 0x20000)
        self.assertNotEqual(self.by_base[0x20000]["verdict"], fr.ERASED)


class Fixture(unittest.TestCase):
    """The shapes the committed image does not contain."""

    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, "rb") as f:
            cls.d = f.read()
        cls.blocks = fr.census(cls.d)
        cls.by_base = {b["base"]: b for b in cls.blocks}

    def test_every_verdict_is_reachable_on_one_image(self):
        verdicts = {b["verdict"] for b in self.blocks}
        self.assertEqual(verdicts,
                         {fr.ERASED, fr.NON_ERASED, fr.UNCLASSIFIED})

    def test_the_marker_is_found_away_from_the_offset_the_committed_dump_uses(self):
        # The committed `ITE8850-PD` sits at +0x40; this one is at +0x1234. A
        # search pinned to +0x40 misses it, and the block then reads
        # unclassified -- which is the failure this fixture exists to catch.
        blk = self.by_base[0x08000]
        self.assertEqual(blk["marker"], "ITE8850-PD")
        self.assertEqual(blk["marker_at"], 0x09234)
        self.assertEqual(blk["verdict"], fr.NON_ERASED)

    def test_an_all_zero_block_is_not_erased(self):
        # `erased` means *every* byte is 0xFF. A block of 0x00 is a different
        # thing and is reported as not classified rather than as erased, which
        # is what stops a fixture that pads its tail from looking like a
        # measurement.
        tail = self.blocks[-1]
        self.assertEqual(tail["ff"], 0)
        self.assertEqual(tail["verdict"], fr.UNCLASSIFIED)

    def test_a_partial_trailing_block_is_walked_at_its_real_extent(self):
        tail = self.blocks[-1]
        self.assertNotEqual(len(self.d) % fr.BLOCK, 0)
        self.assertEqual(tail["end"] - tail["base"], len(self.d) % fr.BLOCK)

    def test_the_strings_mode_names_the_block_it_was_asked_about(self):
        rc, out, _err = run("--image", FIXTURE, "--strings", "0x18000")
        self.assertEqual(rc, 0)
        self.assertIn("UsbPdVer:01.00", out)
        self.assertIn("PR Swap", out)

    def test_the_strings_mode_says_so_when_a_block_has_none(self):
        rc, out, _err = run("--image", FIXTURE, "--strings", "0x10000")
        self.assertEqual(rc, 0)
        self.assertIn("None", out)


class CommandLine(unittest.TestCase):
    """`--check` is a gate on the tool's own classifier, not on the firmware."""

    def test_check_passes_on_the_committed_image_and_on_the_fixture(self):
        self.assertEqual(run("--check")[0], 0)
        self.assertEqual(run("--image", FIXTURE, "--check")[0], 0)

    def test_check_fails_when_a_block_gets_no_verdict(self):
        # The only thing --check is for: a verdict outside the three the
        # classifier can produce is a bug in the classifier, and it has to be
        # visible without a human reading the table. It is unreachable through
        # the committed path, which is exactly why it is injected here rather
        # than left to a fixture -- a fixture can only reach a branch the
        # classifier actually takes.
        original_block, original_census = fr.census_block, fr.census

        def poisoned(base, block, marker):
            out = original_block(base, block, marker)
            out["verdict"] = "code"
            return out

        def poisoned_census(d, block=fr.BLOCK, marker_bytes=fr.PD_MARKER[1]):
            return [poisoned(base, d[base:base + block], marker_bytes)
                    for base in range(0, len(d), block)]

        argv = sys.argv
        try:
            fr.census_block, fr.census = poisoned, poisoned_census
            sys.argv = ["firmware_regions.py", "--image", FIXTURE, "--check"]
            # The report itself is not what is under test here, and printing it
            # would bury the assertion's own output.
            with open(os.devnull, "w") as devnull, \
                    contextlib.redirect_stdout(devnull):
                rc = fr.main()
        finally:
            fr.census_block, fr.census = original_block, original_census
            sys.argv = argv
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()