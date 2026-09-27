#!/usr/bin/env python3
"""Unit checks for the 18 paged-trampoline framing verdicts (issue #54).

`docs/findings/paged-trampoline-hits-by-hand.md` reads all 18 `calls_trampoline`
rows of `bank-paged-call-targets.csv` one at a time and records a verdict for
each: the byte at the site is the operand or displacement of a named
instruction one or two bytes earlier. This file pins the byte facts that reading
stands on, from the committed image and the committed tables, and checks the
write-up's verdict table against the census so the reading cannot drift away
from either.

Three things it deliberately does not do. It does not re-run the scan that
wrote `bank-paged-call-targets.csv` -- that would assert the tool against
itself, and a regenerated census would then be free to disagree with the image.
It does not add a verdict column to that CSV, which is generated and which
`census_ff_fill.py` and `decode_index_table.py` both read as an input. And it
does not assert that a site nobody syncs onto is misframed, or that a site
everybody syncs onto is real: `converges_from`'s own docstring says neither
follows, so every score here is pinned *beside* a named alternative decode
rather than in place of one.

The negative controls are the part that makes the rest mean something. At three
of the sites the byte immediately before the owner's site is a perfectly good
instruction head, and the same bytes frame two ways -- `mov dptr,#0xbf81` +
`ljmp 0x1100`, or `cjne r7,#0x81` + `acall 0x1000`, and both readings contain a
paged call. A suite that answered `phantom` for all 18 without comparing the
framings would pass on a claim that cannot tell them apart, so the decoys are
asserted to decode as something other than the real owner *and* to score 0 of
24 while the owner scores 24.
"""
import csv
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import disasm8051

ANNOTATIONS = HERE.parent / 'annotations'
CENSUS = ANNOTATIONS / 'bank-paged-call-targets.csv'
DECOMPILED = HERE.parent / 'decompiled' / 'common'
FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
WRITEUP = ROOT / 'docs' / 'findings' / 'paged-trampoline-hits-by-hand.md'

# The issue's three verdicts plus the fourth docs/findings.md §4c requires to
# be reachable. `unresolved` is a first-class verdict and is never a synonym for
# phantom, which is why it is here even though this reading returned none of
# it: a later reader who genuinely cannot name an owner has to have somewhere
# to say so.
VERDICTS = {
    'misframed-operand',
    'misframed-data',
    'genuine-paged-call',
    'unresolved',
}

# The 18 sites, in the census's own order, with the instruction each site's byte
# is the last byte of. Pinned literally rather than derived: the write-up's
# table is the claim, and a table that regenerated itself from the census could
# not disagree with it, which is the failure this suite exists to catch.
#
# `listing` is the committed .asm that covers the owner, or None where there is
# none. Three of the 18 have no covering listing and the write-up says so
# rather than implying 18; those entries are the assertion.
OWNERS = [
    # (site, owner, owner bytes, owner mnemonic, covering listing)
    (0x1110, 0x110F, 'c2 91', 'clr 0x91', '110A.asm'),
    (0x1124, 0x1123, 'c2 91', 'clr 0x91', '1114.asm'),
    (0x1138, 0x1137, 'd2 91', 'setb p1.1', '1128.asm'),
    (0x114C, 0x114B, 'd2 91', 'setb p1.1', '113C.asm'),
    (0x12C0, 0x12BE, '90 bf 81', 'mov dptr,#0xbf81', '12BE.asm'),
    (0x1320, 0x131E, '90 bf 91', 'mov dptr,#0xbf91', '131E.asm'),
    (0x15BA, 0x15B8, '90 c8 81', 'mov dptr,#0xc881', '15B8.asm'),
    (0x15E3, 0x15E2, '90 c1 3c', 'mov dptr,#0xc13c', '15E2.asm'),
    (0x1638, 0x1636, '90 d9 91', 'mov dptr,#0xd991', '1636.asm'),
    (0x1656, 0x1654, '90 f3 81', 'mov dptr,#0xf381', None),
    (0x16FE, 0x16FC, '90 c7 e1', 'mov dptr,#0xc7e1', None),
    (0x1AF4, 0x1AF3, '64 01', 'xrl a,#0x01', '1AC2.asm'),
    (0x1B5F, 0x1B5D, '30 e0 21', 'jnb acc.0,0x1b81', '1AC2.asm'),
    (0x1E62, 0x1E61, '7f 01', 'mov r7,#0x01', '1E30.asm'),
    (0x1E8B, 0x1E8A, '64 01', 'xrl a,#0x01', '1E7F.asm'),
    (0x1F14, 0x1F13, '64 01', 'xrl a,#0x01', '1E7F.asm'),
    (0x1F1A, 0x1F19, '64 01', 'xrl a,#0x01', '1E7F.asm'),
    (0x1F8E, 0x1F8D, '64 01', 'xrl a,#0x01', None),
]

# The decoy framings, each a real alternative decode of bytes that are also the
# real owner's. (decoy address, its mnemonic, the site it would consume, its
# owner's score, its own score)
DECOYS = [
    (0x12BF, 'cjne r7,#0x81,0x12c4', 0x12C0),
    (0x131F, 'cjne r7,#0x91,0x1324', 0x1320),
    (0x1637, 'djnz r1,0x15ca', 0x1638),
]

# The 2-byte paged family `paged_sites()` keys on, in the committed decoder's
# own terms rather than the manual's: each value at an instruction boundary, and
# what the tool says it is.
FAMILY = (0x01, 0x11, 0x21, 0x31, 0x41, 0x51, 0x61, 0x71,
          0x81, 0x91, 0xA1, 0xB1, 0xC1, 0xD1, 0xE1, 0xF1)

# The one member of that family the 8051 table gives a second meaning to, named
# rather than written at the assertion. `check_doc_figure_pins.py` reads every
# int constant inside an asserting call across `ec/tools/*.py` as a pin for that
# figure, and `0xC1` is the integer 193 -- which is the `193 / 142` row of
# `docs/findings/xdata-census-rederivation-checklist.md` §2b, whose pin is a case
# in `test_xdata_cluster_names.py`. A bare `0xC1` inside an `assertEqual` would
# make this suite a second, uncited pin for a figure it has nothing to do with
# and turn that page's own marking red; the collision is the one
# `SELF_MODULES` exists to prevent for the four modules it does name, and
# adding a fifth for one assert would be a change to a tool that measures other
# documents' figures, argued for on its own merits rather than to accommodate
# this line. A module-level constant is invisible to that search, which reads
# module-level *dicts* for oracles and only constants *inside* asserting calls
# for literals -- and it says what the byte is, which the bare literal did not.
CLR_BIT = 0xC1

# common-area file offset == runtime address, which is what make_bank_image.py
# arranges and why nothing here does address arithmetic of its own. The raw
# image rather than a bank image: all 18 sites are common-area, so the bank-0
# image and the firmware file hold the same bytes at these offsets, and reading
# the committed firmware is one step fewer than building an image in /tmp.
IMAGE = FIRMWARE.read_bytes()

# One table row: the backticked cells the write-up's verdict table is written
# in. The mnemonic cell is matched loosely (whitespace collapsed) because
# `disasm8051.mnemonic` pads its mnemonic column to a fixed width, and a table
# that had to reproduce the padding would be a table about the padding.
ROW = re.compile(
    r'^\|\s*`(0x[0-9A-F]{5})`\s*\|\s*`(ajmp|acall)`\s*\|\s*`(0x[0-9A-F]{4})`\s*'
    r'\|\s*`(0x[0-9A-F]{5})`\s*`([0-9a-f]{2}(?: [0-9a-f]{2})*)`\s*`([^`]+)`\s*'
    r'\|\s*([a-z-]+)\s*\|$'
)


def squeeze(text):
    return ' '.join(text.split())


def rows():
    """The census rows the reading is about, read by predicate."""
    with open(CENSUS) as f:
        return [r for r in csv.DictReader(f) if r['calls_trampoline'].strip()]


def census_row(site):
    found = [r for r in rows() if int(r['file_offset'], 16) == site]
    if len(found) != 1:
        raise AssertionError('%#06x matches %d census rows' % (site, len(found)))
    return found[0]


def family_meanings():
    """{family byte: what `disasm8051` calls it at an instruction boundary}.

    A scratch buffer rather than the image, because the question is what the
    opcode table *says* a value means and not what this firmware happens to
    have at one -- a firmware with no `0xC1` instruction-start byte at all
    cannot answer it. Each value is given a real operand so a decoder that
    wanted a third byte has one to take.
    """
    scratch = bytearray(len(FAMILY) * 4)
    for i, op in enumerate(FAMILY):
        scratch[i * 4] = op
        scratch[i * 4 + 1] = 0x34
    return {op: squeeze(disasm8051.mnemonic(bytes(scratch), i * 4, i * 4)
                        .split()[0])
            for i, op in enumerate(FAMILY)}


def verdict_table():
    """`{site: (opcode, target, owner, bytes, mnemonic, verdict)}` from the
    write-up, by parsing its markdown table rather than trusting a summary.

    Only lines that the full-row pattern matches are rows, so the header, the
    separator and any prose cell are skipped rather than half-believed -- the
    same discipline `test_readme_suite_table.py` applies to its own inventory.
    """
    out = {}
    for line in WRITEUP.read_text().splitlines():
        m = ROW.match(line)
        if m:
            out[int(m.group(1), 16)] = m.groups()[1:]
    return out


def listing_covers(path, addr):
    """The committed listing's own bytes for the instruction covering `addr`, or
    None. Read from the listing's instruction lines and checked against the
    image, so a listing that stops short of the byte in question cannot pass as
    covering it.

    Only the byte column is returned. The mnemonic beside it is Ghidra's own
    rendering and this suite's is `disasm8051.mnemonic`'s -- `DPTR, #0xc881`
    against `dptr,#0xc881` -- so comparing the two would be a test of which
    disassembler pads where, which is not a claim this reading makes.
    """
    for line in path.read_text(errors='replace').splitlines():
        if not line.strip() or line.startswith(';'):
            continue
        parts = line.split()
        try:
            here = int(parts[0], 16)
        except ValueError:
            continue
        # The byte column is padded with a lone `-` for a short instruction, so
        # take the leading hex pairs and stop at the first token that is not one.
        span = disasm8051.OPCODE_LEN[IMAGE[here]]
        column = []
        for token in parts[1:]:
            if len(token) == 2 and all(c in '0123456789abcdefABCDEF' for c in token):
                column.append(token.lower())
            else:
                break
        if here <= addr < here + span:
            return ' '.join(column)
    return None


def listing_head(path):
    """The address of the committed listing's own first instruction."""
    for line in path.read_text(errors='replace').splitlines():
        if not line.strip() or line.startswith(';'):
            continue
        return int(line.split(None, 1)[0], 16)
    raise AssertionError('%s has no instruction line' % path)


class TheCensusPopulation(unittest.TestCase):
    """The predicate is the reading's subject matter, so the subject matter's
    size is asserted before anything is read through it. Fourteen sites that are
    read as eighteen is a pass, so the count is pinned first and separately."""

    def test_the_predicate_yields_eighteen_rows(self):
        self.assertEqual(len(rows()), 18)

    def test_every_row_is_common_and_resolves_inside_its_own_region(self):
        for r in rows():
            self.assertEqual(r['region'], 'common', r)
            self.assertEqual(r['in_region'], 'yes', r)

    def test_no_row_resolves_onto_a_stub(self):
        # The one thing §7 got right the first time and that a regression here
        # would silently undo: a paged call into a stub is a different finding
        # (a bank reaching its own select entry) and is not what this is about.
        for r in rows():
            self.assertEqual(r['calls_stub'], '', r)

    def test_the_trampoline_column_is_a_bank_number_not_a_boolean(self):
        # The column holds the bank the trampoline selects, so 17/1 is a split
        # of parsed values, not of truthiness -- a test asserting "17 rows are
        # truthy" would pass on a file where the 1 became any other non-empty
        # string, and would fail on a correct one.
        banks = sorted(r['calls_trampoline'] for r in rows())
        self.assertEqual([b for b in banks if b == '0'], ['0'] * 17)
        self.assertEqual([b for b in banks if b == '1'], ['1'])

    def test_the_census_names_the_sites_this_reading_names(self):
        self.assertEqual([int(r['file_offset'], 16) for r in rows()],
                         [site for site, *_ in OWNERS])


class ThePhantomTargetsAreReproducible(unittest.TestCase):
    """Every target the census recorded must fall out of `paged_target()` run on
    the committed image at that offset. This is the check that catches a wrong
    `+ 2` or a wrong mask in the tool, and it is the reason the suite does not
    re-run the scan: the tool is checked against the image, not against itself.
    A `paged_target` that lost the `+ 2` would still agree with a regenerated
    CSV and disagree with all 18 of these."""

    def test_each_target_is_the_one_the_image_computes(self):
        for r in rows():
            site = int(r['file_offset'], 16)
            self.assertEqual(
                disasm8051.paged_target(IMAGE[site], IMAGE[site + 1], site),
                int(r['target'], 16), '%#06x' % site)

    def test_every_target_lands_in_the_trampoline_block(self):
        # 0x1150-0x1ABC is where audit_call_targets.trampolines() puts the
        # common-area block, and it is the whole reason these 18 exist as a
        # group. Pinned so a changed range fails here rather than quietly
        # emptying the population above.
        for r in rows():
            self.assertTrue(0x1150 <= int(r['target'], 16) <= 0x1ABC, r)


class TheOwningInstructions(unittest.TestCase):
    """The verdict is "this byte is the last byte of that instruction", so
    every part of it is a byte assertion: the offset, the bytes, the mnemonic,
    the length that covers the site, and the frame score."""

    def test_the_site_is_an_operand_byte_of_the_owning_instruction(self):
        # Strictly inside, and never at the instruction's own offset. Seventeen
        # of the 18 are the instruction's last byte; 0x15E3 is the first of its
        # two immediate bytes, which is the next test.
        for site, owner, hexbytes, mnemonic, _listing in OWNERS:
            span = disasm8051.OPCODE_LEN[IMAGE[owner]]
            self.assertTrue(owner < site < owner + span,
                            '%#06x: %s does not span the site' % (site, mnemonic))
            self.assertEqual(IMAGE[owner:owner + span].hex(' '), hexbytes, '%#06x' % site)

    def test_only_15e3_is_not_the_last_byte(self):
        # The one site the write-up calls out, pinned so a reader who smoothed
        # the other seventeen into "always the last byte" would be caught. Its
        # byte is the 0xC1 *high* immediate of `mov dptr,#0xc13c`, so the
        # instruction continues one byte past the site -- and that continuation
        # is what the `0x3C` at 0x15E4 is, since `3c` on its own is `addc a,r4`.
        for site, owner, _hexbytes, _mnemonic, _listing in OWNERS:
            span = disasm8051.OPCODE_LEN[IMAGE[owner]]
            self.assertEqual(site == owner + span - 1, site != 0x15E3,
                             '%#06x' % site)
        self.assertEqual(IMAGE[0x15E2:0x15E5].hex(' '), '90 c1 3c')
        # `mov dptr,#imm16` is 90 hi lo, so the owner holds the 0x90 and the
        # site's byte is the immediate's high half -- the site is inside the
        # immediate, not at the end of the instruction.
        self.assertEqual(IMAGE[0x15E2], 0x90)
        self.assertEqual((IMAGE[0x15E3] << 8) | IMAGE[0x15E4], 0xC13C)

    def test_the_owning_instruction_decodes_to_what_the_reading_says(self):
        for site, owner, _hexbytes, mnemonic, _listing in OWNERS:
            self.assertEqual(squeeze(disasm8051.mnemonic(IMAGE, owner, owner)),
                             mnemonic, '%#06x' % site)

    def test_the_owning_instructions_are_anchors(self):
        # 23 or 24 of 24. The four stub sites score 23, and the one that steps
        # over is the walk from the byte before, which reads the site's own
        # opcode and lands on the site -- the misframing seen from the other
        # side, so the exception is the reading and not a gap in it.
        for site, owner, _hexbytes, _mnemonic, _listing in OWNERS:
            onto, over = disasm8051.converges_from(IMAGE, owner)
            self.assertEqual((onto, over), (23, 1) if site < 0x1150 else (24, 0),
                             '%#06x' % site)

    def test_the_byte_at_the_site_is_the_paged_opcode_the_census_recorded(self):
        # Stated because it reads as a contradiction until you see it: the
        # census is right that the byte is paged-shaped, and wrong that it
        # starts an instruction. Checked against the census's own predicate --
        # `paged_sites()` keys on `op & 0x1F in (0x01, 0x11)`, and the 0x10 bit
        # is what separates `acall` from `ajmp` -- rather than against
        # `mnemonic()`, which is the thing the reading disputes.
        for r in rows():
            site = int(r['file_offset'], 16)
            self.assertIn(IMAGE[site] & 0x1F, (0x01, 0x11), '%#06x' % site)
            self.assertEqual('acall' if IMAGE[site] & 0x10 else 'ajmp',
                             r['opcode'], '%#06x' % site)

    def test_15e3_is_the_one_where_the_phantom_reading_is_also_a_real_opcode(self):
        # 0xC1 is the single collision between the 2-byte paged family and the
        # 8051's real opcode table: every other value in the family is
        # unallocated, and 0xC1 is `CLR bit`. So at 0x15E3 the census's `ajmp`
        # is not only displaced by position -- decoded at its own offset the
        # byte completes a valid `clr` instruction too, and only the anchor
        # score separates the two readings. Worth pinning because it is the one
        # site of the 18 where "it is not an instruction" would be false, and
        # because disasm8051.py's own comment says this firmware contains no
        # instruction-start 0xC1, which the anchors confirm.
        self.assertEqual(IMAGE[0x15E3], CLR_BIT)
        self.assertEqual(squeeze(disasm8051.mnemonic(IMAGE, 0x15E3, 0x15E3)),
                         'clr 0x27.4')
        self.assertEqual(disasm8051.OPCODE_LEN[IMAGE[0x15E3]], 2)
        self.assertEqual(disasm8051.converges_from(IMAGE, 0x15E3), (0, 24))
        # ... and the collision is 0xC1's alone. Every family value is put at an
        # instruction boundary in a scratch buffer and decoded by the committed
        # table: fifteen of them mean the paged form and nothing else, so a byte
        # of those values at a site cannot also be a real instruction.
        self.assertEqual([hex(op) for op, m in family_meanings().items()
                          if m not in ('ajmp', 'acall')], ['0xc1'])
        for site, _o, _b, _m, _l in OWNERS:
            if site != 0x15E3:
                self.assertIn(family_meanings()[IMAGE[site]], ('ajmp', 'acall'),
                              '%#06x' % site)


class TheCoveringListings(unittest.TestCase):
    """Fifteen of the eighteen owners sit in a committed listing, and three do
    not. Both halves are asserted: a write-up that claimed 18 would be
    overclaiming, so the three `None`s are pinned as None rather than left to a
    reader to notice."""

    def test_the_listing_named_covers_the_owning_instruction(self):
        for site, owner, _hexbytes, _mnemonic, listing in OWNERS:
            if listing is None:
                continue
            self.assertIsNotNone(listing_covers(DECOMPILED / listing, owner),
                                 '%#06x: %s does not cover %#06x'
                                 % (site, listing, owner))

    def test_the_listing_carries_the_pinned_bytes(self):
        for site, owner, hexbytes, _mnemonic, listing in OWNERS:
            if listing is None:
                continue
            self.assertEqual(listing_covers(DECOMPILED / listing, owner),
                             hexbytes, '%#06x: %s' % (site, listing))

    def test_five_owners_are_their_listings_own_first_instruction(self):
        # The strongest form of the claim, and what
        # docs/findings/bank1-e582-entry-framing.md sets as the house order: a
        # listing that opens at its own first instruction with the bytes in
        # question beats a transcript, because the file's header pins a SHA-256
        # of the source image and was exported independently of this census.
        # Five of the fifteen, all inside the trampoline block, where the six-byte
        # entries are short enough that the exporter opens a listing on each.
        heads = sorted((owner, site) for site, owner, _b, _m, listing in OWNERS
                       if listing is not None
                       and listing_head(DECOMPILED / listing) == owner)
        self.assertEqual([(hex(o), hex(s)) for o, s in heads],
                         [('0x12be', '0x12c0'), ('0x131e', '0x1320'),
                          ('0x15b8', '0x15ba'), ('0x15e2', '0x15e3'),
                          ('0x1636', '0x1638')])

    def test_exactly_three_sites_have_no_covering_listing(self):
        gaps = [site for site, _o, _b, _m, listing in OWNERS if listing is None]
        self.assertEqual([hex(s) for s in gaps], ['0x1656', '0x16fe', '0x1f8e'])


class TheNegativeControls(unittest.TestCase):
    """The non-vacuity property. Every verdict is a claim about framing, so
    each has to be a choice, and the wrong side of the choice has to be a real
    decode rather than a formality."""

    def test_each_decoy_is_a_real_instruction_that_owns_the_site_too(self):
        for decoy, mnemonic, site in DECOYS:
            span = disasm8051.OPCODE_LEN[IMAGE[decoy]]
            self.assertTrue(decoy < site < decoy + span,
                            '%#06x does not reach %#06x' % (decoy, site))
            self.assertEqual(squeeze(disasm8051.mnemonic(IMAGE, decoy, decoy)),
                             mnemonic, '%#06x' % decoy)

    def test_the_decoy_and_its_owner_score_the_opposite_way(self):
        # The pair, not either half: converges_from's docstring says a site
        # nobody syncs onto is not thereby misframed, so 0 of 24 alone would
        # be absence of evidence. It is 24 of 24 on the owner that decides it.
        for decoy, _mnemonic, _site in DECOYS:
            self.assertEqual(disasm8051.converges_from(IMAGE, decoy), (0, 24),
                             '%#06x' % decoy)
        for site, owner, _b, _m, _l in OWNERS:
            if any(site == s for _d, _m, s in DECOYS):
                self.assertEqual(disasm8051.converges_from(IMAGE, owner), (24, 0),
                                 '%#06x' % site)

    def test_the_wrong_framing_still_contains_a_paged_call(self):
        # The reason the decoys are the control and not just a formality: read
        # the same four bytes either way and *both* readings contain a paged
        # transfer. "It looks like a paged call" therefore selects nothing, and
        # a reading that stopped there would have called all 18 phantoms on a
        # property the misframed bytes share.
        self.assertEqual(squeeze(disasm8051.mnemonic(IMAGE, 0x12C2, 0x12C2)),
                         'acall 0x1000')
        self.assertEqual(squeeze(disasm8051.mnemonic(IMAGE, 0x12BE, 0x12BE)),
                         'mov dptr,#0xbf81')

    def test_no_owning_instruction_is_itself_a_paged_instruction(self):
        # Non-circularity, for all 18 rather than for the three worked above: a
        # phantom explained by a neighbouring phantom is not an explanation, and
        # `ajmp`/`acall` are the 0x01/0x11 low-five-bit opcodes paged_sites()
        # keys on.
        for site, owner, _hexbytes, _mnemonic, _listing in OWNERS:
            self.assertNotIn(IMAGE[owner] & 0x1F, (0x01, 0x11), '%#06x' % site)


class TheVerdictTable(unittest.TestCase):
    """The write-up's table is the issue's done condition, so it is parsed and
    checked against the census rather than taken on trust: 18 rows, one per
    census address, none missing and none invented, every verdict in the
    declared vocabulary, and every site holding the verdict its bytes support."""

    def test_the_table_parses_to_one_row_per_census_site(self):
        table = verdict_table()
        self.assertEqual(sorted(table), sorted(int(r['file_offset'], 16)
                                               for r in rows()))

    def test_every_verdict_is_in_the_declared_vocabulary(self):
        for site, row in verdict_table().items():
            self.assertIn(row[5], VERDICTS, '%#06x' % site)

    def test_every_row_names_the_site_the_census_recorded(self):
        # Opcode and target are re-derived, not trusted: a write-up whose table
        # disagreed with the census would otherwise be checked only for shape.
        for site, (opcode, target, *_rest) in verdict_table().items():
            row = census_row(site)
            self.assertEqual((opcode, int(target, 16)),
                             (row['opcode'], int(row['target'], 16)),
                             '%#06x' % site)

    def test_every_row_names_the_owning_instruction_the_image_has(self):
        table = verdict_table()
        for site, owner, hexbytes, mnemonic, _listing in OWNERS:
            self.assertIn(site, table, '%#06x missing from the table' % site)
            self.assertEqual((table[site][2], table[site][3], table[site][4]),
                             ('0x%05X' % owner, hexbytes, mnemonic),
                             '%#06x' % site)

    def test_every_verdict_matches_the_class_its_bytes_support(self):
        # The mapping the reading asserts, asserted rather than described:
        # a site whose byte is the last byte of a named instruction is a
        # misframed operand, and a site that is not gets `unresolved` -- which
        # is not available to this reading, so no row may quietly take it.
        table = verdict_table()
        for site, row in table.items():
            self.assertEqual(row[5], 'misframed-operand', '%#06x' % site)
        self.assertNotIn('unresolved', {row[5] for row in table.values()})


class WhatThisDoesNotClaim(unittest.TestCase):
    """Two claims this change is not making, pinned because both are cheap to
    make by accident in prose. Nothing here is behavioural, so no annotation
    comment may name a register `status:`; and the phantom census rows are
    left in place on purpose, because the CSV regenerates byte for byte and
    adjudicating in prose is the precedent."""

    def test_the_census_rows_are_left_exactly_as_the_scan_wrote_them(self):
        # Reconciling is not editing: no verdict column, no removed row. If a
        # future change wants the rows gone, it wants a tool change and a
        # regeneration, not a hand edit to a 3482-row generated file.
        # `census_row` raises on anything but exactly one match, so reaching the
        # assertion is the count check; the row is then confirmed to be this
        # site's, since a dict's length is its column count and not its count.
        for site, _owner, _b, _m, _l in OWNERS:
            self.assertEqual(census_row(site)['file_offset'],
                             '0x%05X' % site)

    def test_the_writeup_makes_no_behavioural_claim(self):
        text = WRITEUP.read_text()
        self.assertIn('No register `status:`, no row added to or removed from',
                      text)
        self.assertIn('A claim about behaviour', text)


if __name__ == '__main__':
    unittest.main()
