#!/usr/bin/env python3
"""Unit checks for the bank1 0xE582 framing reading (issue #680).

`docs/findings/bank1-e582-entry-framing.md` reads `bank-call-targets.csv`'s
`ljmp 0xE582` at 0x9F03 as the displacement byte of the `sjmp` above it, and
0xE580 as the real transfer. This file pins the byte facts that reading stands
on, from the committed image and the committed tables.

Two things it deliberately does not do. It does not re-run the scan that wrote
`bank-call-targets.csv` -- that would assert the tool against itself, and a
regenerated census would then be free to disagree with the image. And it does
not duplicate `test_citation_gap_scan.py`, which already pins the 0xE580 window
and its five bytes; what is left is the 0x9F03 half, where the argument is a
*displaced* alternative decode rather than a bare anchor score.

Every census assertion reads the committed CSV by predicate and compares it to
the image recomputed here, so a regeneration that changed either fails loudly
instead of passing on a stale pair.
"""
import csv
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import disasm8051
import verify_gap_text as G

DECOMPILED = HERE.parent / 'decompiled'
ANNOTATIONS = ROOT / 'ec' / 'annotations'
CENSUS = ANNOTATIONS / 'bank-call-targets.csv'
FUNCTIONS = ANNOTATIONS / 'ghidra-functions.csv'


def first_instruction(path):
    """(address, byte-column, mnemonic, operands) for a listing's first line.

    Read here rather than through `verify_reassembly.parse_listing`, which
    leaves its file handle open and puts a ResourceWarning on every call under
    unittest. That is a shared tool's business and not this suite's, and a new
    suite that added to the noise rather than avoiding it would be a merge
    hazard on a file other agents are touching. A reader that mis-parsed the
    column cannot pass quietly either: the caller compares what comes back
    against the image, so a shape change fails rather than agreeing with itself.
    """
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith(";") or not line.strip():
            continue
        addr, rest = line.split(None, 1)
        # The byte column ends at the first `-`, the mnemonic is what follows.
        # Taking a run of hex pairs instead would be ambiguous the moment the
        # mnemonic is itself two hex digits, which is why the column is padded.
        head, _, tail = rest.partition(" - ")
        return int(addr, 16), head.split(), tail.split(None, 1)
    raise AssertionError("%s has no instruction line" % path)


# Address == image offset for every program, which is what make_bank_image.py
# arranges and why nothing here does address arithmetic of its own. Loaded once
# rather than per test, for the reason test_citation_gap_scan.py gives: the
# reader leaves an unclosed file and unittest's warning filters would put the
# ResourceWarning on a shared tool this suite is not here to fix.
BANK1 = G.load_images()['bank1']


def annotations():
    with open(FUNCTIONS) as f:
        return {(r['scope'], r['addr']): r for r in csv.DictReader(f)}


def census_row(runtime, target):
    with open(CENSUS) as f:
        return [r for r in csv.DictReader(f)
                if r['runtime'] == runtime and r['target'] == target]


def walk(start, count):
    return list(disasm8051.decode(BANK1, start, count=count, addr=start))


class TheSaveRestorePair(unittest.TestCase):
    """0xE580 is a transfer and 0xE582 is its third byte. The `POP` is what
    makes that a reading rather than a coincidence of framing: a save/restore
    pair bracketing a transfer is not something a misframed read manufactures,
    and it says the stream was framed correctly at the 0xE57E anchor the walk
    starts from."""

    def test_the_eight_bytes_around_the_cut(self):
        # The listing at 0xE57E is a single `c0 07`, so it ends at 0xE580 and
        # the lcall is in no listing at all. Read as push / lcall / pop, the
        # save and the restore carry the same operand 0x07, and the transfer
        # completes by reading *through* 0xE582 -- the byte the bank1,0xE582
        # row opens its own listing with.
        self.assertEqual(BANK1[0xE57E:0xE586],
                         b"\xc0\x07\x12\xe5\xd6\xd0\x07\xef")
        self.assertEqual([t.split() for _o, _r, t in walk(0xE57E, 4)],
                         [["push", "0x07"], ["lcall", "0xe5d6"],
                          ["pop", "0x07"], ["mov", "a,r7"]])

    def test_e580_is_an_anchor_and_e582_is_stepped_over(self):
        # 24 of 24 onto one and 0 of 24 onto the other, a byte apart, reading
        # the two ways the whole reading turns on. On its own the 0/24 would be
        # absence of evidence -- converges_from's docstring says a site nobody
        # syncs onto is not thereby misframed -- so this pins the pair rather
        # than either half.
        self.assertEqual(disasm8051.converges_from(BANK1, 0xE580), (24, 0))
        self.assertEqual(disasm8051.converges_from(BANK1, 0xE582), (0, 24))


class TheDisplacementByte(unittest.TestCase):
    """0x9F03 is the displacement of the `sjmp` at 0x9F02, and the `e5 82` the
    census read as its target address is the committed bank1/9F04.asm head.
    This is the part that makes the reading a displacement-byte argument rather
    than an unsupported site: the misframed read is displaced by a positive
    alternative that explains the same bytes two ways."""

    def test_the_six_bytes_at_9f00(self):
        # `ret`, then -- past the end of the one-instruction 9F00 listing --
        # `mov a,r7`, `80 02`, and the two bytes the census consumed.
        self.assertEqual(BANK1[0x9F00:0x9F06],
                         b"\x22\xef\x80\x02\xe5\x82")

    def test_9f02_is_the_sjmp_and_9f03_its_displacement(self):
        self.assertEqual(disasm8051.converges_from(BANK1, 0x9F02), (24, 0))
        self.assertEqual(disasm8051.converges_from(BANK1, 0x9F03), (0, 24))
        # The walk from 0x9F01 reproduces the census's stream -- `ef`, then
        # `80 02` -- and arrives at 0x9F04, which is where the displacement
        # byte lands. A three-instruction walk, because the `e5 82` pair is
        # where the two readings meet and is checked against the committed
        # listing in the next test rather than only against the image.
        insns = walk(0x9F01, 3)
        self.assertEqual([o for o, _r, _t in insns], [0x9F01, 0x9F02, 0x9F04])
        self.assertEqual(insns[1][2].split(), ["sjmp", "0x9f06"])

    def test_the_bytes_read_as_a_target_are_a_committed_first_instruction(self):
        # The strong form of the claim. Not "the census is unsupported" but
        # "the two bytes it consumed are the machine code of MOV A, DPL, in a
        # listing committed independently of this census" -- so the row is
        # reconstructible as a misframe rather than merely unbacked.
        addr, hexbytes, (mnemonic, operands) = first_instruction(
            DECOMPILED / 'bank1' / '9F04.asm')
        self.assertEqual(addr, 0x9F04)
        self.assertEqual([b.lower() for b in hexbytes], ["e5", "82"])
        self.assertEqual(BANK1[0x9F04:0x9F06].hex(), "".join(hexbytes))
        self.assertEqual((mnemonic, operands), ("mov", "A, DPL"))
        # ... and that listing's first instruction is where the linear decode
        # from 0x9F01 arrives, so the two readings meet rather than merely
        # coexist. `bank1/9F00.asm` is the listing the census walks past, and it
        # is a bare `ret`, which is why the walk starts one byte later at all.
        self.assertEqual(first_instruction(DECOMPILED / 'bank1' / '9F00.asm')[:2],
                         (0x9F00, ['22']))
        self.assertEqual(walk(0x9F01, 3)[2][0], addr)

    def test_the_phantom_row_is_left_in_place_on_purpose(self):
        # Present and unedited, because bank-call-targets.csv is
        # `audit_call_targets.py --csv` output and regenerates byte for byte --
        # bank-call-audit.md 9 is the precedent, adjudicating in prose. What is
        # pinned is that the row reads as a phantom, not that it was removed.
        rows = census_row('0x9F03', '0xE582')
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual((row['opcode'], row['bucket']), ('ljmp', 'B'))
        self.assertEqual((int(row['frame_onto']), int(row['frame_over'])),
                         disasm8051.converges_from(BANK1, 0x9F03))
        # The row's target is the pair the image holds at 0x9F04 -- the census
        # read the displacement's landing address out of a real instruction.
        self.assertEqual(int(row['target'], 16),
                         (BANK1[0x9F04] << 8) | BANK1[0x9F05])

    def test_the_lcall_row_still_reads_the_other_way(self):
        rows = census_row('0xE580', '0xE5D6')
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual((row['opcode'], row['bucket']), ('lcall', 'B'))
        self.assertEqual((int(row['frame_onto']), int(row['frame_over'])),
                         disasm8051.converges_from(BANK1, 0xE580))


class TheInPlaceCorrection(unittest.TestCase):
    """Both rows carry the correction *and* still carry the clause it replaces.
    Presence checks rather than exact-prose checks, so the house rule survives
    an edit that rewords either half: CLAUDE.md asks for the superseded wording
    left visible, and a test that matched it exactly would fail the next reader
    who tightened the prose."""

    def test_e57e_row(self):
        c = annotations()[('bank1', '0xE57E')]['comment']
        self.assertIn('CORRECTION (2026-09-25, issue #680)', c)
        self.assertIn('is not settled by this file pair', c)
        self.assertIn('docs/findings/bank1-e582-entry-framing.md', c)

    def test_e582_row(self):
        c = annotations()[('bank1', '0xE582')]['comment']
        self.assertIn('CORRECTION (2026-09-25, issue #680)', c)
        self.assertIn('contested rather than established', c)
        self.assertIn('docs/findings/bank1-e582-entry-framing.md', c)

    def test_the_correction_seeds_no_entry_and_moves_no_status(self):
        # Two claims this change is not making, pinned because both are cheap to
        # make by accident in prose. 0xE580 gets no function entry: it is the
        # lcall inside the 0xE57E forwarder, so seeding one there would split a
        # register-preserving forwarder in half. And no comment may name a
        # register `status:`, because nothing here is a behavioural claim.
        rows = annotations()
        self.assertNotIn(('bank1', '0xE580'), rows)
        self.assertIn('No function entry belongs at 0xE580 either',
                      rows[('bank1', '0xE57E')]['comment'])
        for addr in ('0xE57E', '0xE582'):
            self.assertNotIn('status:', rows[('bank1', addr)]['comment'])


if __name__ == '__main__':
    unittest.main()
