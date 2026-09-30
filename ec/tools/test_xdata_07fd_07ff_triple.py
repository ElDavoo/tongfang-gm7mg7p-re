#!/usr/bin/env python3
"""Unit checks for the 0x07FD-0x07FF witness-triple reading (issue #573).

`docs/findings/xdata-07fd-07ff-witness-triple.md` reads the three bytes the
boot clear at 0xD96C steps over as a handshake whose third byte discriminates
between two outcomes. This file pins the byte facts that reading stands on,
from the committed image and the committed tables.

Two things it deliberately does not do. It does not re-run the scan that wrote
`xdata-registers.csv` -- that would assert the tool against itself, and a
regenerated census would then be free to disagree with the image. And it does
not pin anything `disasm8051.py`'s own `--self-test` already covers, which is
the oracle for the decoder's opcode and length tables; that self-test is
re-run by the gate and is cited by the write-up rather than duplicated here.

Every image assertion is made against `ec/firmware/GMxMGxx_11.800` through the
same helpers the reading was derived with, so a firmware that no longer has
these bytes fails rather than agreeing with a stale transcription.
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
DECOMPILED = HERE.parent / 'decompiled'

# Address == image offset for every program, which is what make_bank_image.py
# arranges and why nothing here does address arithmetic of its own. Loaded once
# rather than per test, for the reason test_bank1_e582_framing.py gives: the
# reader leaves an unclosed file and unittest's warning filters would put the
# ResourceWarning on a shared tool this suite is not here to fix.
IMAGES = G.load_images()

# The three addresses of the block, and the runtime address each of their `mov
# dptr,#addr` sites is expected at. Runtime, not the raw file offset
# `trace_xdata_refs.py` prints in its `file` column: the images loaded below
# are the flat per-bank ones, where address == image offset, so a bank1 site
# the trace reports at file 0x126AD is at 0xA6AD here. The offsets are spelled
# out rather than recomputed from a scan, because the point of the set
# comparison below is to fail loudly when the image and this list drift apart
# -- a list derived from the same walk it is checked against would always
# agree.
EC_SITES = {
    0x07FD: [(0xCD54, 'bank0'), (0xD68F, 'bank0'), (0xD862, 'bank0'),
             (0x8630, 'bank1'), (0x9517, 'bank1'), (0x9526, 'bank1'),
             (0xA6AD, 'bank1')],
    0x07FE: [(0xCD48, 'bank0'), (0xD683, 'bank0'), (0xD856, 'bank0'),
             (0x8624, 'bank1'), (0x9500, 'bank1'), (0x950F, 'bank1'),
             (0xA69F, 'bank1')],
    0x07FF: [(0xCD4E, 'bank0'), (0xD689, 'bank0'), (0xD85C, 'bank0'),
             (0x862A, 'bank1'), (0x9507, 'bank1'), (0x9513, 'bank1'),
             (0xA6A6, 'bank1')],
}

# The PD-image sites for the same addresses, which `scan_refs.py`'s split is
# what keeps out of the EC-side count. A `mov dptr,#0x07fe` in the ITE8850-PD
# image is a different program's XDATA (docs/findings.md 3a), so these are
# named only to pin that the split is real and not an artefact of the EC count
# happening to be lower. Runtime addresses, as above. These are *literal*
# sites, which is why 0x07FD has an empty list while the census's `refs_pd`
# for it is 1 -- see `test_the_extra_sites_are_pd_image_only`.
PD_SITES = {
    0x07FD: [],
    0x07FE: [0x680E, 0x6831],
    0x07FF: [0x6808],
}


def image_for(region):
    return IMAGES['pd' if region == 'pd-image' else region]


def walk(region, start, count):
    return list(disasm8051.decode(IMAGES[region], start, count=count, addr=start))


def sites_for(image, addr):
    """Every file offset in `image` holding `90 <hi> <lo>`, as a set.

    The raw byte pattern rather than `trace_xdata_refs.sites_for()`, which
    applies the same walk-window rules `scan_refs.py` counts under. The reading
    is about which addresses the EC names at all, and the window rules decide
    how a site is *labelled* rather than whether it exists -- importing the
    classifier here would assert one tool against another for no gain.
    """
    needle = bytes((0x90, addr >> 8, addr & 0xFF))
    return {i for i in range(len(image) - 2) if image[i:i + 3] == needle}


def registers():
    with open(REGISTERS) as f:
        return {e['name']: e for e in yaml.safe_load(f)['registers']}


class TheSiteSet(unittest.TestCase):
    """Seven EC-side `mov dptr` sites per byte, and the PD-image split.

    The count is the claim the issue's own instruction rests on -- that the
    writer/reader set has to come from the image rather than from
    `xdata-registers.csv`, whose `refs` column of 8/10/10 is a file-wide total
    that silently adds the PD image in. Asserted as a set rather than a count
    so a site that appeared or moved is a failure rather than silent drift,
    and so a regenerated census that disagreed could not pass on a stale pair.

    That `refs` column is a different count from the image's 7/9/8 rather than
    a padded one; `test_the_extra_sites_are_pd_image_only` says which is which.
    """

    def test_every_ec_side_site_is_where_the_reading_says(self):
        # Per region, not per address: the flat bank images each cover the
        # whole 64 KiB, so bank0's 0xCD54 has to be absent from bank1's image
        # rather than merely unmatched. One list against one image would let a
        # bank0 site satisfy a bank1 expectation.
        for addr, expected in EC_SITES.items():
            for region in {r for _o, r in expected}:
                offsets = {o for o, r in expected if r == region}
                self.assertEqual(
                    sites_for(IMAGES[region], addr), offsets,
                    "0x%04X %s sites differ from the reading" % (addr, region))

    def test_all_three_bytes_have_seven_ec_side_sites(self):
        for addr, expected in EC_SITES.items():
            self.assertEqual(len(expected), 7,
                             "0x%04X is not the 7 the write-up states" % addr)

    def test_the_extra_sites_are_pd_image_only(self):
        # 0x07FD has none, 0x07FE has two and 0x07FF has one. These are the PD
        # half of `scan_refs.py`'s own 7/9/8 -- its `refs` is already EC + PD,
        # so they are *inside* that figure and are not the difference between
        # it and the census's 8/10/10. The two are not two views of one number:
        # the census's `refs_pd` reads 1/3/3 because it also counts reference
        # forms a literal `90 xx xx` byte scan cannot see (`&DAT_EXTMEM_xxxx`
        # address-taken at ec/decompiled/pd/6673.c:85, and DPTR handed to a
        # call), which is why 0x07FD has a PD reference and no `90 07 fd` byte
        # in the PD image at all. So: 7/9/8 is literal MOV DPTR sites, already
        # including 0/2/1 PD ones; 8/10/10 is 7 EC plus those non-literal forms.
        for addr, expected in PD_SITES.items():
            self.assertEqual(sites_for(IMAGES['pd'], addr), set(expected))
        self.assertEqual([len(PD_SITES[a]) for a in (0x07FD, 0x07FE, 0x07FF)],
                         [0, 2, 1])

    def test_the_control_address_reproduces_its_committed_count(self):
        # 0x08EB is what licenses the method's recall on this image rather
        # than assuming it: 21 EC-side sites, exactly the static_refs_main_ec
        # its registers.yaml row already carries. Without this the seven above
        # are seven this scan found, which is a weaker claim.
        self.assertEqual(len(sites_for(IMAGES['bank0'], 0x08EB))
                         + len(sites_for(IMAGES['bank1'], 0x08EB)), 21)
        self.assertEqual(registers()['XDATA_08EB']['static_refs_main_ec'], 21)


class TheThirdByteIsADiscriminator(unittest.TestCase):
    """`0xD862` and `0x8633` hold `74 00` where `0xCD57` and `0xD692` hold
    `74 5a`.

    This is the finding. Three bytes are written together, two of them always
    the same `0x55`/`0xAA` pair, and the third is `0x5A` at two sites and
    `0x00` at two others -- so it is a discriminator rather than a third copy
    of the same value, and the block has two arms. It is invisible from the
    census's three named sites, two of which are the `0x5A` writers.
    """

    def test_the_two_zero_writers_store_zero(self):
        for region, at in (('bank0', 0xD862), ('bank1', 0x8630)):
            self.assertEqual(IMAGES[region][at:at + 3].hex(), '9007fd')
            self.assertEqual(IMAGES[region][at + 3:at + 5].hex(), '7400',
                             "the 0x00 store at 0x%X moved" % at)

    def test_the_two_witness_writers_store_5a(self):
        for region, at in (('bank0', 0xCD54), ('bank0', 0xD68F)):
            self.assertEqual(IMAGES[region][at:at + 3].hex(), '9007fd')
            self.assertEqual(IMAGES[region][at + 3:at + 5].hex(), '745a',
                             "the 0x5A store at 0x%X moved" % at)

    def test_the_pair_is_the_same_55_aa_at_every_writer(self):
        # All four writers, and the reason the third byte is the interesting
        # one: the first two do not vary. The stride is the 6-byte shape
        # `mov dptr,#imm16 / mov a,#imm8 / movx @dptr,a` twice, so the second
        # pair sits at +6 and +9 rather than adjacent.
        for region, base in (('bank0', 0xCD48), ('bank0', 0xD683),
                             ('bank0', 0xD856), ('bank1', 0x8624)):
            self.assertEqual(IMAGES[region][base:base + 3].hex(), '9007fe')
            self.assertEqual(IMAGES[region][base + 3:base + 5].hex(), '7455')
            self.assertEqual(IMAGES[region][base + 5:base + 6].hex(), 'f0')
            self.assertEqual(IMAGES[region][base + 6:base + 9].hex(), '9007ff')
            self.assertEqual(IMAGES[region][base + 9:base + 11].hex(), '74aa')


class TheConsumerBranchesOnTheThirdByte(unittest.TestCase):
    """`0x94FA` tests the pair, clears it, and branches on `0x07FD` between
    `ljmp 0x95B7` and a three-byte clear.

    The reading's other half. If the third byte were a third copy of the same
    value there would be nothing to branch on, and the block would be a
    latch rather than a handshake.
    """

    def test_the_two_bytes_are_tested_and_cleared(self):
        insns = [t.split() for _o, _r, t in walk('bank1', 0x9500, 6)]
        self.assertEqual(insns, [
            ["mov", "dptr,#0x07fe"], ["movx", "a,@dptr"],
            ["cjne", "a,#0x55,0x9532"], ["mov", "dptr,#0x07ff"],
            ["movx", "a,@dptr"], ["cjne", "a,#0xaa,0x9532"]])

    def test_the_5a_arm_and_the_other_arm(self):
        # `9517`/`951b` load and test the third byte; `951e` is the 0x5A arm and
        # the fall-through clears 0x0045, 0x07FD and XDATA_1F07.
        insns = [t.split() for _o, _r, t in walk('bank1', 0x9517, 6)]
        self.assertEqual(insns, [
            ["mov", "dptr,#0x07fd"], ["movx", "a,@dptr"],
            ["cjne", "a,#0x5a,0x9521"], ["ljmp", "0x95b7"],
            ["mov", "dptr,#0x0045"], ["clr", "a"]])
        tail = [t.split() for _o, _r, t in walk('bank1', 0x9526, 4)]
        self.assertEqual(tail, [
            ["mov", "dptr,#0x07fd"], ["mov", "a,#0x00"], ["movx", "@dptr,a"],
            ["mov", "dptr,#0x1f07"]])


class TheResetVectorClaim(unittest.TestCase):
    """`A6B3 02 00 00` is `ljmp 0x0000`, and `common,0x0000` is the
    `ljmp 0x0070` reset forwarder.

    Asserted as bytes and against the committed listing rather than as prose,
    because "it jumps the reset vector" is the sentence a reader is most likely
    to over-read: it says what the instruction is, and nothing about whether
    the path runs.
    """

    def test_a6b3_is_ljmp_0000(self):
        self.assertEqual(IMAGES['bank1'][0xA6AD:0xA6B3].hex(), '9007fd745af0')
        self.assertEqual([t.split() for _o, _r, t in walk('bank1', 0xA6AD, 3)],
                         [["mov", "dptr,#0x07fd"], ["mov", "a,#0x5a"],
                          ["movx", "@dptr,a"]])
        self.assertEqual(IMAGES['bank1'][0xA6B3:0xA6B6].hex(), '020000')

    def test_common_0000_is_the_reset_forwarder(self):
        # The common area is 0x0000-0x7FFF of either bank image -- verified
        # identical below rather than assumed -- so this is the reset vector
        # the jump lands on and not a bank address that happens to be zero.
        self.assertEqual(IMAGES['bank0'][:0x8000], IMAGES['bank1'][:0x8000])
        self.assertEqual(IMAGES['bank0'][0x0000:0x0003].hex(), '020070')
        head = (DECOMPILED / 'common' / '0000.asm').read_text()
        self.assertIn('ljmp     0x0070', head)
        self.assertIn('reset_vector_forwarder_to_0070', head)

    def test_a69f_is_reached_through_the_far_call_table(self):
        # Index 341 of the 0x1150 table, which is what makes this a path in the
        # image at all. Read out of the committed CSV rather than re-derived.
        rows = [l.split(',') for l in
                (ANNOTATIONS / 'task-call-table.csv').read_text().splitlines()[1:]]
        hit = [r for r in rows if r[0] == 'far-call-stub' and r[1] == '0x1150'
               and r[2] == '341']
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0][3:7], ['0x194E', 'ljmp', '0xA69F', '0x1114'])


class BothWritersSpin(unittest.TestCase):
    """`CD5A 80 fe` and `D6C7 80 fe`.

    The second one is the correction to the issue's premise, which reads
    `0xD673` as carrying on rather than hanging. The test is what stops that
    being re-asserted, and it matters that the second spin is *past* the end of
    `0xD673`'s own committed `.asm` -- so that entry's listing cannot be the
    evidence for it. Scoped to the entry on purpose: the sibling `D6C0.asm`
    *does* carry `D6C7 80 fe`, so the claim is about the listing anchored at the
    entry point, not about committed disassemblies in general.
    """

    def test_both_spins_are_sjmp_to_self(self):
        for region, at in (('bank0', 0xCD5A), ('bank0', 0xD6C7)):
            self.assertEqual(IMAGES[region][at:at + 2].hex(), '80fe')
            self.assertEqual([t.split() for _o, _r, t in walk(region, at, 1)],
                             [["sjmp", "0x%04x" % at]])

    def test_the_d673_spin_is_past_the_end_of_its_listing(self):
        # listing-index.csv gives D673 a size of 77, covering 0xD673-0xD6BF, so
        # the spin is eight bytes beyond what that entry's own .asm contains.
        # If this ever fails the two sources agree and the reading's reason for
        # quoting the image rather than this listing has gone with it. The
        # sibling listings are not in tension with it: D6C0.asm carries the same
        # spin, which is what makes this a fact about the entry anchor rather
        # than about committed disassemblies.
        import csv
        with open(HERE.parent / 'decompiled' / 'listing-index.csv') as f:
            row = [r for r in csv.DictReader(f)
                   if r['program'] == 'bank0' and r['addr'] == 'D673'][0]
        end = int(row['addr'], 16) + int(row['size'])
        self.assertLess(end, 0xD6C7)
        listing = (DECOMPILED / 'bank0' / 'D673.asm').read_text()
        self.assertNotIn('D6C7', listing)

    def test_d673_writes_the_5a_through_the_lcall_and_then_spins(self):
        # The lcall target's own re-pointing is what the issue gets wrong: the
        # 0x03 lands at 0x1F09, not the 0x1F06 the issue names.
        self.assertEqual([t.split() for _o, _r, t in walk('bank0', 0xD68F, 3)],
                         [["mov", "dptr,#0x07fd"], ["mov", "a,#0x5a"],
                          ["lcall", "0xd6ea"]])
        self.assertEqual([t.split() for _o, _r, t in walk('bank0', 0xD6EA, 4)],
                         [["movx", "@dptr,a"], ["clr", "a"],
                          ["mov", "dptr,#0x1f06"], ["movx", "@dptr,a"]])
        self.assertEqual([t.split() for _o, _r, t in walk('bank0', 0xD6F0, 1)],
                         [["mov", "dptr,#0x1f09"]])
        self.assertEqual([t.split() for _o, _r, t in walk('bank0', 0xD697, 2)],
                         [["mov", "a,#0x03"], ["movx", "@dptr,a"]])


class TheBootClearSparesExactlyTheseThree(unittest.TestCase):
    """`0xD96C`'s range clear steps over `0x07FD`-`0x07FF` because the
    `setb c` at `0xD982` makes the upper bound read `0x0800`.

    The premise the whole reading rests on, so it is pinned here rather than
    left to #559's file. This is the fact that makes preservation *consistent
    with* the bytes and not established by them.
    """

    def test_the_setb_c_is_what_lifts_the_upper_bound(self):
        insns = [t.split() for _o, _r, t in walk('bank0', 0xD982, 1)]
        self.assertEqual(insns, [["setb", "c"]])
        # With the carry clear the bound is r7=0xfd, r6=0x07; `setb c` turns the
        # first `subb` into a borrow, so the pair tested is 0xff/0x07 = 0x0800.
        after = [t.split() for _o, _r, t in walk('bank0', 0xD983, 3)]
        self.assertEqual(after, [["mov", "a,r7"], ["subb", "a,#0xff"],
                                 ["mov", "a,r6"]])

    def test_the_clear_starts_at_0100_and_steps_one_byte_at_a_time(self):
        self.assertEqual([t.split() for _o, _r, t in walk('bank0', 0xD96C, 2)],
                         [["mov", "dptr,#0x0100"], ["mov", "r7,0x82"]])
        self.assertEqual(IMAGES['bank0'][0xD98D:0xD98E].hex(), 'a3')


class TheThreeRegisterRows(unittest.TestCase):
    """The rows are `present-untested` with 7 EC-side sites each, and no
    status is upgraded to a behavioural value.

    Read back from the committed YAML rather than from this file's own
    constants, so a status changed elsewhere fails here too. `present-untested`
    is the value whose whole warrant is a reference count, which is what seven
    EC-side sites and no live run amount to; a range clear that steps over a
    byte is not evidence the EC reads it, and readback-accepted is not evidence
    the EC acts on it.
    """

    def test_the_rows_carry_the_counts_the_image_gives(self):
        regs = registers()
        for name, refs, pd in (('XDATA_07FD', 7, 0), ('XDATA_07FE', 9, 2),
                               ('XDATA_07FF', 8, 1)):
            row = regs[name]
            self.assertEqual(row['status'], 'present-untested')
            self.assertEqual(row['static_refs'], refs)
            self.assertEqual(row['static_refs_main_ec'], 7)
            self.assertEqual(row['static_refs_pd_image'], pd)
            self.assertIn('static-scan', row['sources'])

    def test_no_status_is_upgraded_to_a_behavioural_value(self):
        # The vocabulary check in check_status_vocabulary.py is what enforces
        # this across the file; this is the narrow statement that these three
        # in particular carry no live warrant, and it is what a future PR
        # adding one would have to delete deliberately.
        live = ('confirmed-working', 'confirmed-working-partially',
                'confirmed-inert', 'confirmed-not-this-mechanism')
        for name in ('XDATA_07FD', 'XDATA_07FE', 'XDATA_07FF'):
            self.assertNotIn(registers()[name]['status'], live)

    def test_every_site_resolves_to_a_direction(self):
        # Rule 3 of check_status_vocabulary.py reads the committed census, and
        # the census is generated from the same image. This asserts the block
        # is not resting on an unresolvable site, which is the one thing that
        # would make `present-untested` the wrong grade for a mechanical
        # reason rather than an evidentiary one.
        import csv
        with open(ANNOTATIONS / 'site-resolution.csv') as f:
            rows = [r for r in csv.DictReader(f)
                    if r['addr'] in ('0x07FD', '0x07FE', '0x07FF')]
        self.assertEqual(len(rows), 21)
        self.assertEqual({r['resolution'] for r in rows},
                         {'read', 'write'})


class FramingAtTheUnexportedEntries(unittest.TestCase):
    """`0xD856`, `0x8624` and `0xA69F` read 24 of 24 on `--converge`.

    Two of the three (`0x8624`, `0xA69F`) are in no exported listing at all, and
    the third (`0xD856`) is covered only by a listing anchored at `0xD757`, so
    none of the three has a listing that starts where its framing is claimed
    and the anchor is the only thing standing between the reading and a
    misframe. `--converge` is evidence about framing and not proof of it, per
    the tool's own docstring -- which is why this is paired with the byte
    assertions above rather than standing in for them.
    """

    def test_each_entry_is_framed_the_same_way(self):
        for region, at in (('bank0', 0xD856), ('bank1', 0x8624),
                           ('bank1', 0xA69F)):
            self.assertEqual(disasm8051.converges_from(IMAGES[region], at),
                             (24, 0),
                             "framing at 0x%X in %s changed" % (at, region))

    def test_the_two_spins_are_framed_too(self):
        # 0xD6C7 and 0xD6C9 a `mov` apart, both reading 24/24 with 0 stepping
        # over: the spin is a real instruction boundary and not the tail of a
        # decode that ran off the end of the listing.
        for at in (0xD6C7, 0xD6C9):
            self.assertEqual(
                disasm8051.converges_from(IMAGES['bank0'], at), (24, 0))


class TheMisattributedCensusTags(unittest.TestCase):
    """`main-ec-086` tags `0xD5D4` and `0xD74F` as `[writer]` and neither
    writes the triple.

    Recorded rather than fixed: the CSVs are generated and correcting the tags
    is its own change. The test holds the *correction*, so that a regenerated
    census that put the tags back would be a deliberate act against something
    written down rather than a quiet reappearance.
    """

    def test_neither_attributed_address_writes_the_triple(self):
        # 0xD5D4 writes 0x33 to 0x1501; 0xD74F writes 0x33 to 0x1511.
        self.assertEqual([t.split() for _o, _r, t in walk('bank0', 0xD5D4, 2)],
                         [["mov", "dptr,#0x1501"], ["mov", "a,#0x33"]])
        self.assertEqual([t.split() for _o, _r, t in walk('bank0', 0xD74F, 3)],
                         [["mov", "a,#0x33"], ["mov", "dptr,#0x1511"],
                          ["movx", "@dptr,a"]])

    def test_the_real_sites_are_where_the_census_looked_away(self):
        # The two sites at those addresses' neighbours, placed by the byte
        # pattern rather than by any function boundary.
        for at in (0xD683, 0xCD48):
            self.assertEqual(IMAGES['bank0'][at:at + 3].hex(), '9007fe')


if __name__ == '__main__':
    unittest.main()
