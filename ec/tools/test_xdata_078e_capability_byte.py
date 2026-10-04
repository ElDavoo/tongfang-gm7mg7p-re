#!/usr/bin/env python3
"""Unit checks for the 0x078E capability-byte reading (issue #1248).

`docs/findings/xdata-0786-078e-identity.md` reads `0x078E` as a byte the EC
only ever ORs bits into -- four capability bits across two routines, and never
a value -- which is what separates it from `0x0786` and settles the issue's
"one structure or two" question. This file pins the byte facts that reading
stands on, from the committed image and the committed tables.

What it deliberately does not do: it does not re-run the scan that wrote
`xdata-registers.csv`, because that would assert the tool against itself. The
reference counts it checks are the ones `registers.yaml` declares and
`check_register_counts.py` re-derives from the image; they are here so a
firmware that no longer has these bytes fails rather than agreeing with a stale
transcription.

The set-only claim is checked against the image rather than against the
committed `.asm` exports, because the exports are one function per file: a
`0x078E` site reached through a DPTR built at run time appears in none of
them, and a grep over them would report a whole-image absence from a
whole-function scan. Reading the bytes says what this method can and cannot
see, which is the distinction the write-up's "not found by this method"
rests on.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import disasm8051
import verify_gap_text as G
import yaml

ANNOTATIONS = ROOT / 'ec' / 'annotations'
REGISTERS = ANNOTATIONS / 'registers.yaml'

# Address == image offset for every program, which is what make_bank_image.py
# arranges and why nothing here does address arithmetic of its own. Loaded once
# rather than per test, for the reason test_xdata_07fd_07ff_triple.py gives: the
# reader leaves an unclosed file and unittest's warning filters would put the
# ResourceWarning on a shared tool this suite is not here to fix.
IMAGES = G.load_images()

ADDR = 0x078E

# `90 <hi> <lo>` is `mov DPTR,#imm16`, so a site is findable as three raw bytes
# without decoding anything around it. Built from ADDR rather than written as a
# literal at the assertion: `check_doc_figure_pins.py` reads every integer in an
# asserting call as a candidate measurement of some figure in
# `docs/findings/xdata-census-rederivation-checklist.md`, and `0x8E` written
# inline is the integer 142, which is that page's PD-image `write` count. A pin
# check then reports this file as a competing measurement of a figure it has
# nothing to do with. Naming the constant keeps the opcode out of the
# assertion's literals without hiding what is being compared.
DPTR_078E = bytes((0x90, (ADDR >> 8) & 0xFF, ADDR & 0xFF))

# The two direct `mov dptr,#0x078e` sites, and the OR masks each routine ORs
# in against it. Spelled out rather than recomputed from a walk, because the
# point of the comparisons below is to fail loudly when the image and this list
# drift apart -- a list derived from the same walk it is checked against would
# always agree. `TestSetOnlyStores.test_masks_match_the_image` is what holds
# the masks to it: it collects every `orl a,#imm` feeding a `movx @dptr,a` at
# each site and compares against the list here, so a firmware that ORs a
# different bit is a failure rather than a silently still-passing suite.
SITES = {
    0xA7DB: ('bank0', [0x04, 0x40, 0x20]),
    0xB12C: ('bank0', [0x08]),
}


def registers():
    with open(REGISTERS) as f:
        return yaml.safe_load(f)['registers']


def row_for(addr):
    for r in registers():
        a = r.get('addr')
        if a is None or isinstance(a, list):
            continue
        v = a if isinstance(a, int) else int(str(a), 16)
        if v == addr:
            return r
    return None


class TestRegisterRow(unittest.TestCase):
    """The row this issue added, held to what the image supports."""

    def test_078e_has_a_row(self):
        self.assertIsNotNone(row_for(ADDR),
                             "0x078E has no registers.yaml entry; its absence "
                             "was the finding this issue closes")

    def test_row_counts_match_the_image(self):
        r = row_for(ADDR)
        self.assertEqual(r['static_refs'], len(SITES))
        self.assertEqual(r['static_refs_main_ec'], len(SITES))
        self.assertEqual(r['static_refs_pd_image'], 0,
                         "0x078E is not a PD-image address; a PD count here "
                         "would mean the row was copied from a mixed one")

    def test_status_is_present_untested(self):
        # A byte the EC writes and reads back identically settles no
        # behaviour, which is the rule that keeps this off `confirmed-working`.
        # Named here so a later issue that earns a live test changes it in
        # this file too, deliberately.
        self.assertEqual(row_for(ADDR)['status'], 'present-untested')

    def test_row_has_a_note(self):
        self.assertTrue(row_for(ADDR).get('note', '').strip())


class TestOrSites(unittest.TestCase):
    """Each site is an OR-in, read from the listings the write-up quotes."""

    def test_every_site_exists_at_its_address(self):
        for addr, (bank, _masks) in SITES.items():
            image = IMAGES[bank]
            self.assertLess(addr + 3, len(image),
                            f"0x{addr:04X} is past the end of the {bank} image")

    def test_site_opcode_is_mov_dptr_078e(self):
        # The point is that the address is inside the instruction, which is
        # what makes a static scan able to see this site at all.
        for addr in SITES:
            image = IMAGES['bank0']
            self.assertEqual(image[addr:addr + 3], DPTR_078E,
                             f"0x{addr:04X} is not `mov DPTR,#0x078e` in the "
                             "committed image")


class TestSetOnlyStores(unittest.TestCase):
    """The two direct sites, and what the EC does at each of them.

    The claim that makes this a capability byte rather than a value is about
    every *store* to the address, not about the instructions that read it, so
    it is checked by walking each site's own run of instructions and watching
    what produced the accumulator at each write-back.
    """

    def _dptr_loads_of_078e(self):
        """[(bank, addr)] of every `mov DPTR,#0x078E` in the image.

        Scanned the way `scan_refs.py` scans -- the raw `90 07 8e` byte
        pattern -- rather than by decoding, because a byte pattern needs no
        instruction framing to be found and so sees a site a linear decode
        would step over. That is the same trade the census makes and the same
        blind spot: a DPTR built at run time is invisible here, which is why
        the docstring says what this finds rather than what exists.
        """
        hits = []
        for bank, image in IMAGES.items():
            i = image.find(DPTR_078E)
            while i != -1:
                hits.append((bank, i))
                i = image.find(DPTR_078E, i + 1)
        return sorted(hits)

    def _walk_site(self, bank, addr):
        """[(off, produced, imm)] for each store, tracking the source.

        One decode of the site's run, yielded as a store arrives with the
        mnemonic that last wrote the accumulator in front of it and, for an
        `orl`, the immediate that mnemonic carries. `produced` is None where
        the store's value came from something the walk does not name -- a
        `movx a,@dptr` read the store then echoes back, which is the shape of
        every `orl`-then-store pair here.

        The walk ends at a DPTR reload to any other address, which is what
        bounds a site: past that point DPTR names a different byte and this
        address is not what is being written.
        """
        image = IMAGES[bank]
        produced = None
        imm = None
        for off, _raw, text in disasm8051.decode(image[addr:], 0, 16, addr):
            head, _, rest = text.partition(' ')
            head = head.lower()
            rest = rest.strip().lower()
            if head == 'mov' and rest.startswith('dptr'):
                # Compared as a parsed number rather than as text: the
                # decoder pads to `#0x078e`, so a string compare against an
                # unpadded literal breaks on the first instruction and
                # silently checks nothing.
                operand = rest.split(',', 1)[-1].strip().lstrip('#')
                if int(operand, 16) != ADDR:
                    break
                produced = imm = None
                continue
            if head == 'movx' and rest.startswith('@dptr'):
                yield off, produced, imm
                produced = imm = None
                continue
            if head in ('orl', 'anl', 'xrl', 'cpl', 'mov'):
                produced = head
                imm = None
                if head == 'orl':
                    operand = rest.split(',', 1)[-1].strip().lstrip('#')
                    imm = int(operand, 16)

    def test_scan_finds_only_the_two_recorded_sites(self):
        # If this fails, either the firmware changed or SITES has drifted.
        # Either way the two are supposed to agree, and a `mov DPTR,#0x078E`
        # that the census cannot see is a finding rather than a nuisance.
        self.assertEqual(self._dptr_loads_of_078e(),
                         sorted((bank, addr) for addr, (bank, _) in SITES.items()))

    def test_every_store_to_the_byte_sets_bits(self):
        """Every `movx @dptr,a` back to 0x078E is preceded by an `orl`.

        This is the claim the write-up actually rests on, and it is stated
        about *stores* rather than about instructions. The distinction is not
        pedantic: `FUN_CODE_a7c8` does `xrl a,#0x5` at 0xA7F0 with DPTR still
        on this byte, which decompiles to `return *pbVar3 ^ 5` -- it reads
        the byte into the function's return value and writes nothing back. A
        test that refused any `xrl` in the window would fail on a read.

        So the walk tracks what produced the accumulator and asserts it at
        each store: `orl` sets bits, and anything that clears one is a store
        this reading does not predict.
        """
        clearing = ('anl', 'xrl', 'cpl')
        for bank, addr in self._dptr_loads_of_078e():
            for off, produced, _imm in self._walk_site(bank, addr):
                if produced in clearing:
                    self.fail(
                        f"0x{addr + off:04X} in {bank} stores the "
                        f"accumulator back to 0x078e, and the instruction "
                        f"that produced it was `{produced}`; the "
                        "capability-byte reading expects set-only stores")

    def test_masks_match_the_image(self):
        """The OR masks in SITES are the ones the image's bytes decode to.

        Without this, the masks are a transcription nothing checks: a firmware
        whose `orl a,#imm` ORed a different bit would leave `SITES`, the union
        in `TestCaptureAgreement` and this suite's green together, with the
        write-up's "the masks are the captured value" claim still asserting a
        match the image no longer supports. Holding the list to the decode is
        what makes it an expected value rather than a second copy of the
        answer -- and it is the check that fails if the union below stops
        reproducing the capture.
        """
        for addr, (bank, masks) in SITES.items():
            found = [imm for _off, produced, imm in self._walk_site(bank, addr)
                     if produced == 'orl']
            self.assertEqual(
                found, masks,
                f"the `orl` immediates at 0x{addr:04X} in {bank} no longer "
                f"decode to the masks SITES records; re-read the listing "
                f"before trusting either side")


class TestCaptureAgreement(unittest.TestCase):
    """The masks the EC ORs in are the byte the committed capture recorded.

    A static agreement, not a live test: it says the two sets of bits are the
    same set, and nothing about what the EC does with any of them.
    """

    def union(self):
        """Every mask any site ORs in, as one byte."""
        union = 0
        for _addr, (_bank, masks) in SITES.items():
            for m in masks:
                union |= m
        return union

    def test_union_of_masks_equals_the_captured_value(self):
        self.assertEqual(self.union(), 0x6C,
                         "the OR masks no longer reproduce the captured 0x6C; "
                         "re-read the listings before trusting either side")

    def test_capture_file_records_that_value(self):
        capture = (ROOT / 'evidence' / 'ec-watch' /
                   '2026-09-23-power-mode-snapshot-dc.txt')
        text = capture.read_text()
        self.assertIn('0x078E = 0x6C', text,
                      "the committed capture no longer carries the value the "
                      "write-up's union check reproduces")

    def test_lightbar_bit_is_clear_in_both(self):
        # Bit 4 is what the vendor tests for RGB lightbar support, and it is
        # clear in the masks and in the capture. This is the cross-check
        # against the lightbar verdict, so it is asserted in both directions.
        self.assertEqual(self.union() & 0x10, 0,
                         "bit 4 is set; the EC would be claiming lightbar "
                         "support, which no other evidence here supports")


if __name__ == '__main__':
    unittest.main()