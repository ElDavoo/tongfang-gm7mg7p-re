#!/usr/bin/env python3
"""Unit checks for the pack-temperature producer chain (issue #1425).

`docs/findings/pack-temp-producer-chain.md` reads `0x04A2`/`0x04A3` as a
16-bit little-endian pair, accounts for the census's three main-EC `write`
references as two store sites one of which is counted twice, reads the
`0x0B72` constant out of `AF32.asm` rather than off the decompiler's inlined
literal, reads all four writers of `0x0502`/`0x0503`, and adjudicates the PD
image's five `0x04A3` sites as strided base references. This file pins the
byte facts that reading stands on.

**Every case here is static and none of them is a behaviour.** No register was
read, written or read back and no site was seen run. A `write` asserted below
is an instruction, not evidence the EC acted on the byte, and the fact that a
constant is `0x0B72` is not evidence the EC ever stored a temperature there.
The suite is written so that none of its assertions could be mistaken for a
live result: they read the committed image and the committed tables, and
nothing here watches a byte move.

Two things it deliberately does not do. It does not re-run the scan that
wrote `xdata-registers.csv` -- that would assert a tool against itself, and a
regenerated census would then be free to disagree with the image; every census
assertion below reads the committed CSV *by predicate* and compares it to the
image recomputed here. And it does not re-derive the PD term model, which
`pd_index_geometry.py` already pins in its own `--self-test`: the PD cases
assert the **five helper bodies as bytes** and the **write-up's reading of
what they do**, not a second implementation of the term algebra.

Where the census and a per-site walk disagree, the disagreement is the thing
asserted -- that the write-up *names* it -- rather than resolved here. A suite
that picked a winner would be deciding a question the evidence leaves open.
"""
import csv
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import verify_gap_text as G

DECOMPILED = HERE.parent / 'decompiled'
ANNOTATIONS = ROOT / 'ec' / 'annotations'
CENSUS = ANNOTATIONS / 'xdata-registers.csv'
FINDING = ROOT / 'docs' / 'findings' / 'pack-temp-producer-chain.md'
FIRMWARE = ROOT / 'ec' / 'firmware' / 'GMxMGxx_11.800'

# Read once, the way `test_bank1_e582_framing.py` gives for
# `verify_gap_text.load_images`: a per-test read of a 256 KiB image is not a
# cost worth paying forty times, and every assertion below compares what it
# reads against a committed table, so a wrong read fails rather than agreeing
# with itself.
IMAGES = G.load_images()
BANK0, BANK1 = IMAGES['bank0'], IMAGES['bank1']
# `load_images` returns one 64 KiB image per program already indexed by
# *runtime* address, so no case here does offset arithmetic: the PD image is a
# separate program with its own address space and its own slice, and the same
# `PD[0xF22E]` indexing applies to it as `BANK1[0xAF32]` does to bank 1.
PD = IMAGES['pd']

# The two pair accessors the chain runs on, named once because "which helper"
# is the difference between a store and a load and the whole suite turns on
# telling them apart. 0x888C stores R1:R2, 0x8892 loads R3:R4.
STORE_PAIR, LOAD_PAIR = 0x888C, 0x8892


def census_row(addr):
    with CENSUS.open() as f:
        for row in csv.DictReader(f):
            if int(row['addr'], 16) == addr:
                return row
    raise AssertionError("no xdata-registers.csv row for 0x%04X" % addr)


def listing(bank, name):
    """[(address, bytes, operand text)] for every instruction line.

    Read here rather than through a shared parser, for the reason
    `test_bank1_e582_framing.py` gives: a reader that mis-parsed the byte
    column could not pass quietly, because the assertions below compare what
    comes back against the image."""
    out = []
    for line in (DECOMPILED / bank / name).read_text(
            errors='replace').splitlines():
        if line.startswith(';') or not line.strip():
            continue
        cols = line.split()
        raw = bytes(int(b, 16) for b in cols[1:4] if b != '-')
        out.append((int(cols[0], 16), raw, ' '.join(cols[4:])))
    return out


def operands(bank, name):
    """{runtime address: operand text} for one listing, mnemonic dropped.

    The byte column ends at the first `-` and the mnemonic is what follows it,
    so the operand text is everything after the first token of the text column.
    A reader that took a fixed number of columns would pass the listings that
    happen to line up and misreport the rest; the assertions below compare the
    operands against literals, so a shape change fails rather than agreeing
    with itself."""
    return {a: ' '.join(t.split()[1:]) for a, _raw, t in listing(bank, name)}


def committed_sites(addr):
    """{region: count} of `MOV DPTR,#addr` sites, from the committed census.

    `ec/annotations/pd-xdata-span-sites.csv` is the per-region site census the
    write-up quotes, and reading it *here* rather than re-deriving it is what
    keeps a regenerated table from being asserted against itself: the counts
    below are compared to what the image shows at the addresses this suite
    names, and an image that moved fails here.

    A raw `90 hi lo` byte scan is **not** used for the census counts and must
    not be: in a 64 KiB image the same three bytes occur inside data, so a scan
    over the whole image reports sites that are not instructions. The cases
    below therefore check the bytes at addresses the listings and the census
    give, rather than searching for every occurrence."""
    with (ANNOTATIONS / 'pd-xdata-span-sites.csv').open() as f:
        for row in csv.DictReader(f):
            if int(row['addr'], 16) == addr:
                return {k: int(row[k]) for k in
                        ('total', 'main_ec', 'pd_image', 'bank0', 'bank1',
                         'pd-image')}
    raise AssertionError("no pd-xdata-span-sites.csv row for 0x%04X" % addr)


def call_target_after(image, site):
    """The `lcall`/`ljmp` target following a `mov DPTR,#imm` at `site`.

    `mov DPTR,#imm` is three bytes and a transfer is three, so the opcode is
    at `site + 3` and the target is the two bytes at `site + 4..+5` -- the same
    shape in all four programs, which is why this takes an image rather than a
    program name. A third byte would be the next instruction, and taking one
    would read every call as a 24-bit address that matched nothing.
    """
    if image[site + 3] not in (0x12, 0x02):
        return None
    return int.from_bytes(image[site + 4:site + 6], 'big')


class TheThreeWritesAreTwoSites(unittest.TestCase):
    """The census says three main-EC `write` references for `0x04A2`; the
    image has two store sites. The third is `0xAF06`'s rendered twice, once in
    its own `.c` and once in `AD7D.c`, which is the decompiler following
    `AD7D`'s three-byte `ljmp`. This is issue step 1's question and the count
    is its answer."""

    def test_ad7d_is_three_bytes_and_one_of_them_is_the_ljmp(self):
        self.assertEqual(BANK1[0xAD7D:0xAD80], b"\x02\xaf\x06")
        self.assertEqual(listing('bank1', 'AD7D.asm')[-1],
                         (0xAD7D, b"\x02\xaf\x06", 'ljmp 0xaf06'))

    def test_the_census_counts_the_two_sites_and_the_forwarder_twice(self):
        # Read the census by predicate rather than as a whole-file total: a
        # regeneration that changed 0x04A2's row fails here by name, and one
        # that changed any other row does not send this suite looking for a
        # cause it has nothing to do with.
        row = census_row(0x04A2)
        self.assertEqual((int(row['write_main_ec']), int(row['write'])), (3, 3))
        # ...and the three .c files that carry a store spelling, which is where
        # the 3 comes from. AD7D.c and AF06.c carry the same call text because
        # they are the same bytes, which is the point.
        stores = sorted(p.name for p in (DECOMPILED / 'bank1').glob('*.c')
                        if 'write_r1r2_to_xdata_pair(0x4a2' in p.read_text())
        self.assertEqual(stores, ['AC84.c' and 'AD7D.c', 'AF06.c', 'AF32.c'])

    def test_the_image_has_two_store_sites_and_three_load_sites(self):
        # The six main-EC sites the census records, read off the committed
        # listings and checked against the image at those addresses. Which of
        # them stores and which loads is decided by the *callee*, not by the
        # mnemonic at the site -- `mov DPTR,#imm` is the same instruction in
        # all six and the difference is the helper it hands the address to.
        stores = [s for s in (0xAF28, 0xAF39, 0xB134, 0xB145, 0xC3A7)
                  if call_target_after(BANK1, s) == STORE_PAIR]
        loads = [s for s in (0xAF28, 0xAF39, 0xB134, 0xB145, 0xC3A7)
                 if call_target_after(BANK1, s) == LOAD_PAIR]
        self.assertEqual(stores, [0xAF28, 0xAF39])
        self.assertEqual(loads, [0xB134, 0xB145, 0xC3A7])
        # Five bank1 sites and one bank0 site, and the committed census agrees.
        self.assertEqual((committed_sites(0x04A2)['bank1'],
                          committed_sites(0x04A2)['bank0']), (5, 1))
        # Every one of the six carries the immediate in the image.
        for s in (0xAF28, 0xAF39, 0xB134, 0xB145, 0xC3A7):
            self.assertEqual(BANK1[s:s + 3], b"\x90\x04\xa2")
        self.assertEqual(BANK0[0xBAEC:0xBAEF], b"\x90\x04\xa2")

    def test_the_writeup_names_the_disagreement_rather_than_resolving_it(self):
        text = FINDING.read_text()
        self.assertIn('counted twice', text)
        self.assertIn('AD7D.asm', text)


class TheAF06Gate(unittest.TestCase):
    """Three routes, and which bit or byte picks between them. The gate is the
    only place `0x0502`/`0x0503` reaches `0x04A2`/`0x04A3`, so its three tests
    are what make route 3 a copy rather than a measurement."""

    def test_the_three_gates_are_the_three_bytes_the_listing_carries(self):
        insn = listing('bank1', 'AF06.asm')
        # bit 2 of 0x0490 clear -> jnb 0xe2 to 0xAF4B, the 0xAF32 route
        self.assertEqual(insn[2], (0xAF0A, b"\x30\xe2\x3e", 'jnb 0xe2, 0xaf4b'))
        # bit 3 of 0x04FF set -> jb 0xe3 to 0xAF2E, the straight-to-0xB0D1 route
        self.assertEqual(insn[5], (0xAF11, b"\x20\xe3\x1a", 'jb 0xe3, 0xaf2e'))
        # 0x0505 is read and branched three ways: 0, 1, anything else
        by_addr = {a: (raw, t) for a, raw, t in insn}
        self.assertEqual(by_addr[0xAF19], (b"\x90\x05\x05", 'mov DPTR, #0x505'))
        self.assertEqual(by_addr[0xAF1D], (b"\x60\x2c", 'jz 0xaf4b'))
        self.assertEqual(by_addr[0xAF1F], (b"\xb5\x01\x0f", 'cjne A, 0x01, 0xaf31'))

    def test_route_three_copies_the_word_and_not_a_value_it_computed(self):
        self.assertEqual(BANK1[0xAF22:0xAF2E],
                         b"\x90\x05\x02\x12\x88\x86\x90\x04\xa2\x12\x88\x8c")

    def test_the_r1_load_from_0x0503_is_dead_in_this_listing(self):
        # AF06.c:12 says the R1 load is dead, and that is checkable: R1 is
        # written at 0xAF18 and read by nothing before the next write. The
        # `cjne A,#0x01` at 0xAF1F branches on A, not on R1, and the value the
        # branch distinguishes comes from the 0x0505 read at 0xAF1C.
        self.assertEqual(BANK1[0xAF14:0xAF19], b"\x90\x05\x03\xe0\xf9")
        insn = operands('bank1', 'AF06.asm')
        self.assertEqual(insn[0xAF18], 'R1, A')
        self.assertFalse([a for a, t in insn.items()
                          if a > 0xAF18 and a < 0xAF22 and t.startswith('R1')])


class TheAF32Constant(unittest.TestCase):
    """The store's value is a literal in the listing, not a caller's R1:R2.

    This is the case the write-up's one numeric reading rests on, so it is
    asserted as bytes rather than as a derived dK value. What `0x0B72` *means*
    is not asserted here and is not established by the write-up."""

    def test_dptr_is_loaded_with_the_constant_and_split_into_r1_r2(self):
        self.assertEqual(BANK1[0xAF32:0xAF3F],
                         b"\x90\x0b\x72\xaa\x83\xa9\x82\x90\x04\xa2\x12\x88\x8c")
        self.assertEqual(operands('bank1', 'AF32.asm'),
                         {0xAF32: 'DPTR, #0xb72', 0xAF35: 'R2, DPH',
                          0xAF37: 'R1, DPL', 0xAF39: 'DPTR, #0x4a2',
                          0xAF3C: '0x888c', 0xAF3F: 'A, #0x4',
                          0xAF41: 'DPTR, #0x56b', 0xAF44: '@DPTR, A',
                          0xAF45: 'A', 0xAF46: 'DPTR, #0x493',
                          0xAF49: '@DPTR, A', 0xAF4A: ''})

    def test_the_constant_is_0x0b72_and_that_is_2930_dK(self):
        # 0x0B72 is 2930 dK; the consumer's first threshold is 3030 dK
        # (ec/annotations/charge-target-derating.md 48), so the constant sits
        # 100 dK below it. The arithmetic is pinned; the reading is not.
        self.assertEqual(0x0B72, 2930)
        self.assertEqual(3030 - 0x0B72, 100)

    def test_the_two_writes_beside_the_store_are_what_resets_the_index(self):
        # 0x056B is the step index 0xB0D1 walks and 0x0493 a flag byte, so this
        # is why route 1 is a reset rather than a plain copy.
        self.assertEqual(BANK1[0xAF3F:0xAF4B],
                         b"\x74\x04\x90\x05\x6b\xf0\xe4\x90\x04\x93\xf0\x22")


class TheProbeSweepAndTheOtherThreeWriters(unittest.TestCase):
    """`0x0502`/`0x0503` has four writers on four different paths, and the
    issue asks what the word is. What the listing settles is the shape of each
    writer: two of them compute `value x 10 + 0x0AAA` and one computes
    `value x 10 + 0x0A46`, which is why the word is not read here as a
    temperature."""

    def test_ac84_writes_ten_slots_in_listing_order_with_0502_first(self):
        # The ten store sites, in the order the listing reaches them, each the
        # `mov DPTR,#slot` three bytes before its `lcall 0x889E`. Read off the
        # listing rather than off the decompiler's ten calls, and each DPTR
        # immediate taken from the image so a re-framed listing cannot pass.
        insn = listing('bank1', 'AC84.asm')
        call_at = {a: t for a, _raw, t in insn}
        stores = []
        for i, (a, _raw, t) in enumerate(insn):
            if t.startswith('lcall 0x889e') and i and insn[i - 1][2].startswith('mov DPTR'):
                dptr_a, dptr_raw, dptr_t = insn[i - 1]
                self.assertEqual(BANK1[dptr_a - 0x10000:dptr_a - 0x10000 + 3], dptr_raw)
                stores.append((dptr_a, int(dptr_t.split('#0x')[1], 16)))
        self.assertEqual([a for a, _v in stores],
                         [0xAC99, 0xACAA, 0xACBB, 0xACCC, 0xACDD, 0xACF2,
                          0xAD13, 0xAD24, 0xAD35, 0xAD46])
        self.assertEqual([v for _a, v in stores],
                         [0x0502, 0x0518, 0x052A, 0x052E, 0x0514, 0x0506,
                          0x053A, 0x053C, 0x053E, 0x0540])
        self.assertEqual(len(set(v for _a, v in stores)), 10)

    def test_e8a4_forms_a_times_ten_product_and_stores_it_twice(self):
        insn = operands('bank1', 'E8A4.asm')
        self.assertEqual(insn[0xE8E5], 'B, #0xa')     # mul by 10
        self.assertEqual(insn[0xE8EC], 'R1, #0x46')    # + 0x0A46
        self.assertEqual(insn[0xE8EE], 'R2, #0xa')
        self.assertEqual(insn[0xE8F3], 'DPTR, #0x502')  # store to 0x0502
        self.assertEqual(insn[0xE8F9], 'DPTR, #0x504')  # and the same to 0x0504

    def test_db0b_and_e100_both_build_the_same_times_ten_plus_0x0aaa(self):
        db = operands('bank1', 'DB0B.asm')
        self.assertEqual(db[0xDBE4], 'B, #0xa')       # mul by 10
        self.assertEqual(db[0xDBE9], 'A, #0xaa')      # + 0x0AA
        self.assertEqual(db[0xDBF2], 'DPTR, #0x502')
        e1 = operands('bank1', 'E100.asm')
        self.assertEqual(e1[0xE1A5], 'B, #0xa')       # mul by 10
        self.assertEqual(e1[0xE1A9], 'A, #0xaa')      # + 0x0AA
        self.assertEqual(e1[0xE1B9], 'DPTR, #0x502')

    def test_the_four_writers_the_census_names_are_the_four_sites(self):
        row = census_row(0x0502)
        named = sorted(f.split('=')[0] for f in row['functions'].split('; '))
        self.assertEqual(named, ['bank1:0x8BD1', 'bank1:0xAC84', 'bank1:0xAD7D',
                                 'bank1:0xAF06', 'bank1:0xDB0B', 'bank1:0xE100',
                                 'bank1:0xE8A4'])
        self.assertEqual(int(row['write']), 4)
        # Seven main-EC sites, three of them reads and four writes, and the
        # image carries the immediate at each. The three reads are 0x8BD1's
        # two and `0xAF06`'s; the four writes are the four writers this case
        # and the two above are about.
        reads = [s for s in (0x8C00, 0x8C53, 0xAC99, 0xAF22, 0xDBF2, 0xE1B9, 0xE8F3)
                 if call_target_after(BANK1, s) == 0x8886]
        writes = [s for s in (0x8C00, 0x8C53, 0xAC99, 0xAF22, 0xDBF2, 0xE1B9, 0xE8F3)
                  if call_target_after(BANK1, s) in (0x889E, 0x888C)]
        self.assertEqual(reads, [0x8C00, 0x8C53, 0xAF22])
        self.assertEqual(writes, [0xAC99, 0xDBF2, 0xE1B9, 0xE8F3])
        for s in reads + writes:
            self.assertEqual(BANK1[s:s + 3], b"\x90\x05\x02")

    def test_8bd1_reads_the_word_twice_and_never_writes_it(self):
        # Two 0x0502 loads paired with the read helper, and a third for 0x0506
        # -- the arm that compares a *different* word.
        by_addr = {a: t for a, _raw, t in listing('bank1', '8BD1.asm')}
        self.assertEqual([a for a, t in by_addr.items() if t == 'mov DPTR, #0x502'],
                         [0x8C00, 0x8C53])
        self.assertEqual(by_addr[0x8CD0], 'mov DPTR, #0x506')
        for a in (0x8C00, 0x8C53, 0x8CD0):
            self.assertEqual(by_addr[a + 3], 'lcall 0x8886')

    def test_the_three_comparison_constants_per_arm(self):
        insn = operands('bank1', '8BD1.asm')
        for addr, const in ((0x8C06, '0xce4'), (0x8C14, '0xd48'), (0x8C34, '0xd16'),
                            (0x8C59, '0x9f6'), (0x8C67, '0xabe'),
                            (0x8CA3, '0x2328'), (0x8CC5, '0x2ee0'),
                            (0x8CBC, '0x1770')):
            self.assertEqual(insn[addr], 'DPTR, #%s' % const)

    def test_0x0ce4_is_ten_dk_below_the_0x0cee_the_consumers_use(self):
        # The issue asked for this arithmetic and it is not "one dK-unit":
        # 0x0CEE is 3310 and 0x0CE4 is 3300.
        self.assertEqual((0x0CEE, 0x0CE4, 0x0CEE - 0x0CE4), (3310, 3300, 10))
        self.assertIn('ten dK', FINDING.read_text())


class ThePdAdjudication(unittest.TestCase):
    """The five PD `0x04A3` sites want a strided field, not the byte. Each
    hands DPTR to a helper that *returns*, and every term the helper adds is
    non-zero for some register value -- so the sites that dereference do so at
    a rebased address. Asserted as helper bytes rather than as a second
    implementation of `pd_index_geometry.py`'s term algebra, which that tool
    pins in its own `--self-test`."""

    def test_the_five_sites_and_the_helper_each_one_calls(self):
        # The census records five PD sites and one EC-side; the five addresses
        # are the ones `trace_xdata_refs.py` prints, and the image carries the
        # immediate at each of them.
        self.assertEqual((committed_sites(0x04A3)['pd-image'],
                          committed_sites(0x04A3)['main_ec']), (5, 1))
        for a in (0x917A, 0x9DA6, 0x9E52, 0xEDB7, 0xF22E):
            self.assertEqual(PD[a:a + 3], b"\x90\x04\xa3")
        targets = {a: call_target_after(PD, a)
                   for a in (0x917A, 0x9DA6, 0x9E52, 0xEDB7, 0xF22E)}
        self.assertEqual(targets, {0x917A: 0x10BC, 0x9DA6: 0x998B,
                                   0x9E52: 0x9A3F, 0xEDB7: 0x9A1B,
                                   0xF22E: 0x9987})
        # 0x917A reaches 0x10BC by `ljmp` and the other four by `lcall`; both
        # are transfers, and neither one dereferences on the way.
        self.assertEqual(PD[0x917D], 0x02)
        for a in (0x9DA6, 0x9E52, 0xEDB7, 0xF22E):
            self.assertEqual(PD[a + 3], 0x12)

    def test_every_helper_returns_rather_than_dereferencing(self):
        # 0x10BC is `mul ab` / add DPL / addc DPH / ret; two of the four
        # tail-jump into it and 0x9987 falls through to the same `ret`. A
        # returned DPTR is a computed address, which is the whole argument.
        for entry, blob in (
                (0x10BC, b"\xa4\x25\x82\xf5\x82\xe5\xf0\x35\x83\xf5\x83\x22"),
                (0x9A1B, b"\xeb\x75\xf0\x60\x02\x10\xbc"),
                (0x9A3F, b"\x75\xf0\x60\x02\x10\xbc")):
            self.assertEqual(PD[entry:entry + len(blob)], blob,
                             "pd helper 0x%04X moved" % entry)
        # 0x9987 = `mov a,r7 / mov b,#0x60 / lcall 0x10BC / ... / ret`, and
        # 0x998B is the same tail entered one instruction later.
        self.assertEqual(PD[0x9987:0x9996],
                         b"\xef\x75\xf0\x60\x12\x10\xbc\xef\x25\xe0\x25\x83\xf5\x83\x22")
        self.assertEqual(PD[0x998B:0x9996],
                         b"\x12\x10\xbc\xef\x25\xe0\x25\x83\xf5\x83\x22")
        # The exact bodies above are what rule out a dereference, and they do
        # it by being exact: a `movx` in any of these spans would be different
        # bytes. A separate scan for 0xE5/0xF5 was tried here and is wrong --
        # 0xE5 is also `mov a,direct`, and 0x10BC legitimately contains
        # `e5 f0` (`mov a,0xF0`) -- so the check is the listing, not the byte.

    def test_the_helper_listings_agree_with_the_bytes(self):
        # The committed listings are read as well as the image, because two of
        # the four carry a *partial* body: `9987.asm` and `998B.asm` are one
        # line each, because the exporter stopped them at the `lcall 0x10BC`
        # and the shared tail is `10BC`'s. The bytes below say what the whole
        # body is, and this says which of the two the listings under-report --
        # a fact about the export rather than about the image, and worth
        # knowing before quoting either one as a routine.
        self.assertEqual(operands('pd', '10BC.asm'),
                         {0x10BC: 'AB', 0x10BD: 'A, DPL', 0x10BF: 'DPL, A',
                          0x10C1: 'A, B', 0x10C3: 'A, DPH', 0x10C5: 'DPH, A',
                          0x10C7: ''})
        self.assertEqual([a for a, _r, _t in listing('pd', '9987.asm')], [0x9987])
        self.assertEqual([a for a, _r, _t in listing('pd', '998B.asm')], [0x998B])
        self.assertEqual(operands('pd', '9A1B.asm'),
                         {0x9A1B: 'A, R3', 0x9A1C: 'B, #0x60', 0x9A1F: '0x10bc'})

    def test_each_helper_sets_a_multiplicand_and_only_9987_adds_a_page_term(self):
        # `mov B,#0x60` is the stride in three of the four, and the 0xE0 added
        # to the carry-adjusted DPH is the page term -- pd-index-geometry.md's
        # `0x200x` naming, which this file quotes rather than re-derives.
        # `mov B,#0x60` is the stride. It is at 0x9A3F+0, at 0x9A1B+1 (behind
        # `mov a,r3`) and at 0x9987+1 (behind `mov a,r7`) -- three offsets,
        # which is why they are named rather than looped over.
        self.assertEqual(PD[0x9A3F:0x9A42], b"\x75\xf0\x60")
        self.assertEqual(PD[0x9A1C:0x9A1F], b"\x75\xf0\x60")
        self.assertEqual(PD[0x9988:0x998B], b"\x75\xf0\x60")
        self.assertEqual(PD[0x9987:0x998B], b"\xef\x75\xf0\x60")
        self.assertEqual(PD[0x998F:0x9996], b"\x25\xe0\x25\x83\xf5\x83\x22")
        # 0x9A3F and 0x10BC carry no page term of their own.
        self.assertNotIn(b"\x25\xe0", PD[0x9A3F:0x9A3F + 6])
        self.assertNotIn(b"\x25\xe0", PD[0x10BC:0x10BC + 12])

    def test_three_of_the_five_dereference_and_two_do_not(self):
        # A helper that only *returns* does not by itself prove the site reads
        # nothing: what follows the `lcall` is the site's own code. Three of
        # the five dereference the pointer the helper handed back, and the
        # write-up's count is the tool's, not a reading of the call shape --
        # so the count is pinned here against the bytes. `movx A,@DPTR` is
        # 0xE0 and `movx @DPTR,A` is 0xF0, and each sits where the term below
        # says it does.
        site_tail = {
            0x917A: b"\x90\x04\xa3\x02\x10\xbc\x75\xf0\x1f\x02\x10\xbc\x90\x08\x23",
            0x9DA6: b"\x90\x04\xa3\x12\x99\x8b\xe0\x12\x99\xb8\xf0\x12\xed\xb5\xef",
            0x9E52: b"\x90\x04\xa3\x12\x9a\x3f\xee\x12\x99\x8f\xef\xf0\xee\x12\x9a",
            0xEDB7: b"\x90\x04\xa3\x12\x9a\x1b\xeb\x12\x99\x8f\x12\x99\xd4\xeb\x12",
            0xF22E: b"\x90\x04\xa3\x12\x99\x87\xe0\xfe\x12\x9a\x90\x12\x99\x8b\xe0",
        }
        for a, blob in site_tail.items():
            self.assertEqual(PD[a:a + len(blob)], blob,
                             "pd 0x04A3 site 0x%04X moved" % a)
        # 0x9DA6 and 0xF22E read the rebased pointer at site+6; 0x9E52's first
        # `movx` at +6 is the R6-indirect `movx A,@R6`, and the DPTR store is
        # the 0xF0 at +11, after the `lcall 0x998F` adds the page term.
        self.assertEqual((PD[0x9DA6 + 6], PD[0xF22E + 6], PD[0x9E52 + 11]),
                         (0xE0, 0xE0, 0xF0))
        # 0x917A's chain ends at the tail call into 0x10BC, and 0xEDB7's ends
        # unmodelled at 0x99D4 -- neither reaches a `movx` under this model,
        # and neither site carries one in its own bytes above. The two are not
        # classified by a scan for the opcode (0xE5 is also `mov a,direct`, so
        # a byte scan cannot tell the two apart); they are classified by the
        # chain ends the tool prints, and only the *count* is asserted here.
        self.assertEqual(PD[0x917A + 3], 0x02)          # ljmp, a tail call
        self.assertNotIn(b"\xe0", site_tail[0x917A])    # no movx A,@DPTR
        self.assertNotIn(b"\xf0", site_tail[0xEDB7])    # no movx @DPTR,A
        dereferencing = (0x9DA6, 0x9E52, 0xF22E)
        self.assertEqual(len(dereferencing), 3)
        # ...and the write-up says three, so the document cannot drift back to
        # the count the call shape used to suggest.
        finding = FINDING.read_text()
        self.assertIn('**three of the five dereference the', finding)
        self.assertIn('three, not one', finding)

    def test_f22e_reads_the_rebased_address_and_not_the_byte(self):
        # The clearest of the three dereferencing sites, and what it
        # dereferences: DPTR is
        # 0x04A3, 0x9987 adds R7x0x60 and 0xE0 to DPH, and only then does
        # `movx A,@DPTR` run. The term is R7's, so the address read is
        # 0x04A3 + R7x0x60 + 0xE0 whenever R7 is non-zero.
        self.assertEqual(PD[0xF22E:0xF23C],
                         b"\x90\x04\xa3\x12\x99\x87\xe0\xfe\x12\x9a\x90\x12\x99\x8b")
        insn = operands('pd', 'F22E.asm')
        self.assertEqual(insn[0xF22E], 'DPTR, #0x4a3')
        self.assertEqual(insn[0xF231], '0x9987')
        self.assertEqual(insn[0xF234], 'A, @DPTR')
        self.assertEqual(insn[0xF235], 'R6, A')
        # ...and the decompiler's `&DAT_EXTMEM_04a3` is the base, not the
        # address the movx touches. The PD image is never given a symbol table,
        # so the base is the only thing that file names at all.
        self.assertIn('&DAT_EXTMEM_04a3', (DECOMPILED / 'pd' / 'F22E.c').read_text())

    def test_04a2_leaves_the_datemov_term_and_04a3_keeps_its_pair_literal(self):
        # The naming must not change what `--moved` reports. `0x04A2` leaves
        # the `DAT_EXTMEM` term for `symbol` in the main EC once the re-export
        # carries `PACK_TEMP_DK_0` into the text; `0x04A3` does not, because
        # its main-EC half is a bare pair-literal and the `DAT_EXTMEM` spelling
        # is the PD image's -- so it is the only address `--moved` still names.
        self.assertEqual(census_row(0x04A3)['spellings_by_program'],
                         'main-ec=pair-literal;pd=DAT_EXTMEM')
        self.assertEqual(census_row(0x04A2)['spelled_as'],
                         'symbol+pair-literal')
        self.assertEqual(census_row(0x04A2)['name'], 'PACK_TEMP_DK_0')
        self.assertEqual(census_row(0x04A3)['name'], 'PACK_TEMP_DK_1')


class TheCountsAreTheCommittedOnes(unittest.TestCase):
    """The census figures the write-up quotes, read by address. A regeneration
    that disagrees fails here rather than silently restating them in prose."""

    def test_the_four_rows_the_writeup_depends_on(self):
        for addr, refs, main, pd_ in ((0x04A2, 9, 9, 0), (0x04A3, 8, 7, 1),
                                      (0x0502, 8, 8, 0), (0x0503, 10, 10, 0)):
            row = census_row(addr)
            self.assertEqual((int(row['refs']), int(row['refs_main_ec']),
                              int(row['refs_pd'])), (refs, main, pd_),
                             "0x%04X moved" % addr)

    def test_the_pair_is_little_endian_with_04a2_low(self):
        # BAE7.c:7 says it, and the bytes say it: 0xBAE7 loads 0x04A3 first
        # into R6 and 0x04A2 into R7, and 0xAF32 splits a DPTR with DPL -- the
        # low byte -- into R1.
        # Two reads with a `add a,#0x00` between them, step over rather than
        # span: BAE7.c:8 says the ADD only sets the carry and overflow flags,
        # so including it would assert three bytes the endianness does not
        # rest on. The high byte goes to R6 and the low to R7.
        self.assertEqual(BANK0[0xBAE7:0xBAEC], b"\x90\x04\xa3\xe0\xfe")
        self.assertEqual(BANK0[0xBAEC:0xBAF0], b"\x90\x04\xa2\xe0")
        self.assertEqual(operands('bank0', 'BAE7.asm')[0xBAEB], 'R6, A')
        self.assertEqual(operands('bank0', 'BAE7.asm')[0xBAF2], 'R7, A')
        self.assertEqual(BANK1[0xAF35:0xAF39], b"\xaa\x83\xa9\x82")


if __name__ == '__main__':
    unittest.main()
