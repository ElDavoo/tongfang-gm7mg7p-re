#!/usr/bin/env python3
"""Unit checks for the common 0x5A5A edge adjudication (issue #703).

`docs/findings/common-5a5a-edge-framing.md` reads the census's `lcall 0x5A5A`
at 0x0049 as three bytes inside one 26-byte record ending in the EC identity
string, and reads 0x5A5A as offset 7 inside a 15-byte group the image holds ten
times. This file pins the byte facts that reading stands on, from the committed
image and the committed tables.

Three things it deliberately does not do. It does not re-run the scan that
wrote `bank-call-targets.csv`: that would assert the tool against itself, and a
regenerated census would then be free to disagree with the image. It does not
duplicate `test_bank1_e582_framing.py`, which is the same argument on the
0x9F03 census row. And it does not bank the frame scores. They read *for* a
real call at both disputed addresses, so the controls that make the column
useless are pinned beside them -- offsets inside the very runs under
adjudication that score the same, and one offset in each of two unrelated data
islands that scores the same. A suite holding only the two high scores would be
checking the one column the write-up declines to rest on.

Every census assertion reads the committed CSV by predicate and compares it to
the image recomputed here, so a regeneration that changed either fails loudly
instead of passing on a stale pair.
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
import verify_gap_text as G

ANNOTATIONS = HERE.parent / 'annotations'
DECOMPILED = HERE.parent / 'decompiled'
FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
CENSUS = ANNOTATIONS / 'bank-call-targets.csv'
CALL_GRAPH = ANNOTATIONS / 'call-graph-callees.csv'
INDEX = DECOMPILED / 'index.csv'

# The whole committed image, for the claims the write-up makes about "the
# image" rather than about one region: the `a5` run, the `12 5a 5a` occurrence
# and the group copies are each stated over all of it. `read_bytes()` closes its
# own handle, so unlike `load_images()`'s `open()` it puts no ResourceWarning on
# unittest's warning filters.
IMAGE = FIRMWARE.read_bytes()

# The common area, which make_bank_image.py copies verbatim from the firmware
# file's own 0x0000-0x7FFF onto the front of every bank image -- so a
# common-area address *is* a file offset here, which is why the census's
# `file_offset` and `runtime` are the same number for these rows. Address ==
# image offset for that reason, and `TheCallerEnd.test_the_common_area_is_the
# _files_own_first_half` holds the equality rather than assuming it. Loaded
# once, for the reason test_bank1_e582_framing.py gives: the reader leaves an
# unclosed file and unittest's warning filters would put the ResourceWarning on
# a shared tool this suite is not here to fix.
COMMON = G.load_images()['bank0']

# The 15-byte group 0x5A5A is read as sitting inside, and where the image holds
# it. The offsets are spelled out rather than counted so that a copy which
# moved names itself in the failure instead of turning into a bare length.
GROUP = bytes.fromhex('3c 3c 46 5a 60 64 6e 8c aa c8 c8 c8 c8 c8 c8')
GROUP_COPIES = (0x5813, 0x58D3, 0x5993, 0x59C3, 0x5A53,
                0x5A83, 0x5B13, 0x5B43, 0x5BD3, 0x5C03)

# The 26 bytes at 0x0046 that decide the caller end, as one record: ten of
# prefix, then the identity string and its NUL.
RECORD = bytes.fromhex('a4 95 85 12 5a 5a aa 7b 55 55'
                       '49 54 45 20 45 43 2d 56 31 34 2e 36 20 20 20 00')


def occurrences(pattern, blob=IMAGE):
    """Every offset in `blob` holding `pattern`, ascending."""
    return tuple(i for i in range(len(blob) - len(pattern) + 1)
                 if blob[i:i + len(pattern)] == pattern)


def byte_runs(value, minimum, blob=IMAGE):
    """[(offset, length)] for every run of `value` at least `minimum` long."""
    pattern = re.escape(bytes([value])) + ('{%d,}' % minimum).encode()
    return tuple((m.start(), m.end() - m.start())
                 for m in re.finditer(pattern, blob))


def ljmp_run(start):
    """([(addr, target)] for the `02 hi lo` entries from `start`, end offset).

    The stop offset is returned rather than left implicit because "the table
    ends here" is half of what the caller-end bracket rests on: it is the
    reason there is a padding run between the two tables instead of one run.
    """
    entries = []
    at = start
    while COMMON[at] == 0x02:
        entries.append((at, (COMMON[at + 1] << 8) | COMMON[at + 2]))
        at += 3
    return entries, at


def census_rows(runtime, target):
    with open(CENSUS) as f:
        return [r for r in csv.DictReader(f)
                if r['runtime'] == runtime and r['target'] == target]


def call_graph_rows(scope, addr):
    with open(CALL_GRAPH) as f:
        return [r for r in csv.DictReader(f)
                if r['scope'] == scope and r['addr'] == addr]


def index_rows(program, addr):
    with open(INDEX) as f:
        return [r for r in csv.DictReader(f)
                if r['program'] == program and r['addr'] == addr]


class TheCallerEnd(unittest.TestCase):
    """0x0046-0x005F is one 26-byte record, and the `lcall` the census booked is
    bytes 3-5 of its ten-byte prefix. The record ends in a NUL-terminated ASCII
    version string, which is what the whole reading turns on: a transfer-shaped
    triple in the middle of a string record is a coincidence of framing, not a
    call, and the string is a positive reading of the same bytes rather than an
    absence claim."""

    def test_the_common_area_is_the_files_own_first_half(self):
        # What lets a common-area address be used as a file offset throughout,
        # and what ties the 64 KiB image the frame scores are computed against
        # to the 256 KiB file the whole-image counts come from. If the graft
        # ever stopped being verbatim, every other assertion here would still
        # pass while answering a different question, so it is held directly.
        self.assertEqual(COMMON[:0x8000], IMAGE[:0x8000])

    def test_the_twenty_six_bytes(self):
        self.assertEqual(COMMON[0x0046:0x0060], RECORD)
        self.assertEqual(len(RECORD), 26)

    def test_the_tail_is_a_nul_terminated_identity_string(self):
        # `ITE EC-V14.6` is what docs/hardware-identity.md already records, and
        # what ec/README.md and ec/annotations/lightbar-bat-flow.md both record
        # at file 0x50. What this adds is the other end of it: that the run
        # reaches the NUL, so the bytes the census read as a call are inside
        # the record that ends in the string rather than inside the string.
        self.assertEqual(COMMON[0x0050:0x0060], b'ITE EC-V14.6   \x00')
        self.assertEqual(COMMON[0x005F], 0x00)

    def test_the_booked_call_is_three_bytes_into_the_prefix(self):
        # `12 5a 5a` at 0x0049, out of a ten-byte prefix that is not a save, a
        # restore, or a sequence of instructions that reaches the end of
        # anything. Asserted against the address the census recorded rather
        # than against a decode, so the case is about the bytes' position in
        # the record and not about the opcode table.
        self.assertEqual(COMMON[0x0046:0x0050], RECORD[:10])
        self.assertEqual(COMMON[0x0049:0x004C], b'\x12\x5a\x5a')
        self.assertEqual(0x0049 - 0x0046, 3)
        self.assertEqual((COMMON[0x004A] << 8) | COMMON[0x004B], 0x5A5A)

    def test_the_three_byte_signature_occurs_once_in_the_image(self):
        # One run, and it is inside the record. If the same triple were common
        # in the image the uniqueness argument would have nothing to stand on.
        self.assertEqual(occurrences(b'\x12\x5a\x5a'), (0x0049,))


class TheBracket(unittest.TestCase):
    """The record is bracketed by two `02 hi lo` runs with a padding run
    between them. This is the shape `ec/annotations/data-regions.yaml` records
    for a jump table, and it is what makes the record a record: bytes in the
    middle of a data island are not an entry point, and the census's own
    listing header says as much when it calls the 0x0046 boundary a
    hypothesis."""

    def test_the_a5_padding_is_the_only_such_run_in_the_image(self):
        # Six `a5` bytes and nowhere else in 256 KiB, so the gap between the
        # two tables is one recognisable run rather than a guess about where
        # the first table stopped.
        self.assertEqual(byte_runs(0xa5, 4), ((0x0040, 6),))
        self.assertEqual(COMMON[0x0040:0x0046], b'\xa5' * 6)

    def test_the_two_ljmp_runs_bracket_the_record(self):
        before, before_end = ljmp_run(0x0035)
        after, after_end = ljmp_run(0x0060)
        self.assertEqual(before, [(0x0035, 0x116E), (0x0038, 0x1174),
                                  (0x003B, 0x117A)])
        self.assertEqual([t for _a, t in after],
                         [0x1180, 0x1186, 0x1192, 0x1198, 0x119E])
        # Both runs point into one narrow ascending band -- 0x116E to 0x119E, in
        # steps that are multiples of 6 (not all of them 6: 0x1186 to 0x1192 is
        # 12). Two runs of `02` bytes aiming at the same block is what makes
        # them one family of table rather than `02` bytes that happen to align.
        for targets in ([t for _a, t in before], [t for _a, t in after]):
            steps = [t2 - t1 for t1, t2 in zip(targets, targets[1:])]
            self.assertTrue(all(step > 0 for step in steps), targets)
            self.assertTrue(all(step % 6 == 0 for step in steps), targets)
        self.assertEqual(min(before[0][1], after[0][1]), 0x116E)
        self.assertEqual(max(before[-1][1], after[-1][1]), 0x119E)
        # ... and each stops two or one bytes short of the padding and of the
        # second run, on a `22` that is not `02`.
        self.assertEqual(before_end, 0x003E)
        self.assertEqual(COMMON[0x003E:0x0040], b'\x22\x22')
        self.assertEqual(after_end, 0x006F)
        self.assertEqual(COMMON[0x006F], 0x22)
        self.assertEqual(before_end + 2, 0x0040)   # the `a5` run
        self.assertEqual(after_end - 0x0060, 15)   # five entries, then the stop

    def test_what_follows_the_second_run_is_code_and_not_a_table(self):
        # The positive half of the bracket: the table stops and something that
        # reads as a routine starts, so the run at 0x0060 is bounded on both
        # sides rather than merely followed by other bytes.
        self.assertEqual(COMMON[0x0070:0x0078],
                         bytes.fromhex('75 81 c0 90 10 01 74 3f'))
        decoded = [t.split() for _o, _r, t in
                   disasm8051.decode(COMMON, 0x0070, count=4, addr=0x0070)]
        self.assertEqual(decoded[0], ['mov', '0x81,#0xc0'])
        self.assertEqual(decoded[1], ['mov', 'dptr,#0x1001'])
        self.assertEqual(decoded[3], ['movx', '@dptr,a'])


class TheCalleeEnd(unittest.TestCase):
    """0x5A5A is offset 7 inside a 15-byte group the image holds at ten
    offsets, not the start of anything. The group copies are the load-bearing
    half: a `8c aa` followed by six `c8` occurs once in a data run and reads as
    `mov direct,R4` plus six exchanges; the same fifteen bytes occur ten times,
    none of them at 0x5A5A."""

    def test_the_group_copy_offsets(self):
        self.assertEqual(occurrences(GROUP), GROUP_COPIES)

    def test_5a5a_is_seven_bytes_into_one_of_them(self):
        # Arithmetic rather than narration, so "not a record boundary" is
        # checked instead of asserted. The one copy the callee sits in starts
        # at 0x5A53, and 0x5A5A is the eighth byte of it -- the `8c` the
        # annotation reads as `mov 0xaa, R4`.
        self.assertEqual(COMMON[0x5A53:0x5A62], GROUP)
        self.assertIn(0x5A5A - (0x5A5A - 0x5A53), GROUP_COPIES)
        self.assertEqual(0x5A5A - 0x5A53, 0x7)
        self.assertNotIn(0x5A5A, GROUP_COPIES)

    def test_the_reti_the_5a55_row_reads_is_inside_the_run(self):
        # `reti` is 0x32, and the annotation reads a `reti` at 0x5A62. The
        # bytes are a 0x32 -- but the run does not stop there: 0x5A63 is
        # another 0x32 and the eight after it ascend. A return the bytes do
        # not mark is the strongest part of the case against code here.
        self.assertEqual(COMMON[0x5A62], 0x32)
        self.assertEqual(COMMON[0x5A63], 0x32)
        self.assertEqual(COMMON[0x5A64:0x5A6C],
                         bytes.fromhex('34 36 38 3a 3c 40 42 44'))
        ascending = COMMON[0x5A62:0x5A6C]
        self.assertEqual(list(ascending), sorted(ascending))


class TheFrameScoresDoNotDiscriminate(unittest.TestCase):
    """`converges_from` scores both disputed addresses *for* a real call, and
    that is why this reading cannot rest on the column. Every score asserted
    here is matched by an offset this file has already shown to be table
    bytes: neighbours inside the two disputed runs, and one offset in each of
    two unrelated islands. The write-up's claim is that the column does not
    separate the two cases; this is that claim as a test rather than a
    sentence."""

    def test_the_disputed_pair(self):
        self.assertEqual(disasm8051.converges_from(COMMON, 0x0049), (23, 1))
        self.assertEqual(disasm8051.converges_from(COMMON, 0x5A5A), (24, 0))

    def test_neighbours_inside_the_two_runs_score_the_same(self):
        # The tightest form of the control, because these are the same bytes
        # the reading is about. Inside the caller record, 0x0046/0x0047/0x0051
        # and the ASCII at 0x005B-0x005C score 24 of 24, and 0x004E, 0x0053,
        # 0x0056, 0x0057 and 0x005A score 23 of 24. Inside the callee group,
        # 0x5A53, 0x5A55, the five `c8` at 0x5A5D-0x5A61 and the `32` at
        # 0x5A62 all score 24 of 24; the sixth `c8`, at 0x5A5C, scores 23 of
        # 24, and is held too so the `c8` run cannot be read as uniform.
        # Every one of those bytes has been shown above to be part of a record
        # or a table, so a high score at 0x5A5A is not evidence of code there.
        for addr in (0x0046, 0x0047, 0x0051, 0x005B, 0x005C):
            self.assertEqual(disasm8051.converges_from(COMMON, addr), (24, 0),
                             'caller record, 0x%04X' % addr)
        for addr in (0x004E, 0x0053, 0x0056, 0x0057, 0x005A):
            self.assertEqual(disasm8051.converges_from(COMMON, addr), (23, 1),
                             'caller record, 0x%04X' % addr)
        for addr in (0x5A53, 0x5A55, 0x5A5D, 0x5A5E, 0x5A5F,
                     0x5A60, 0x5A61, 0x5A62):
            self.assertEqual(disasm8051.converges_from(COMMON, addr), (24, 0),
                             'callee group, 0x%04X' % addr)
        self.assertEqual(disasm8051.converges_from(COMMON, 0x5A5C), (23, 1))

    def test_two_unrelated_islands_score_the_same_too(self):
        # The same two scores, from two data islands neither of which is under
        # adjudication. 0x0060 is the first byte of the second `ljmp` run --
        # a table entry, at 23 of 24. 0x631F is inside a run of small-value
        # records and scores 24 of 24, the same as 0x5A5A. It is *not* a record
        # start there, so the `02 00 46` the census read as `ljmp 0x0046` spans
        # a record boundary. Asserted because "not at a record start" is what
        # makes the control honest, and because the same shape is the one row
        # this change deliberately leaves un-adjudicated.
        self.assertEqual(disasm8051.converges_from(COMMON, 0x0060), (23, 1))
        self.assertEqual(COMMON[0x0060], 0x02)
        self.assertEqual(disasm8051.converges_from(COMMON, 0x631F), (24, 0))
        self.assertEqual(COMMON[0x631F:0x6322], b'\x02\x00\x46')
        self.assertEqual(occurrences(b'\x02\x00\x46'), (0x631F,))

    def test_the_0x631f_control_is_interior_under_either_framing(self):
        # Which record 0x631F lands inside is the part the write-up declines to
        # settle, so nothing here picks a stride. What the control needs is the
        # framing-independent half: the site is not a record start on the
        # stride-6 grid the write-up treats as better evidenced, nor on the
        # stride-3 grid the same bytes also support -- whichever of that grid's
        # two candidate anchors is taken, since 0x62D6 and 0x631D are not in the
        # same mod-3 class.
        self.assertNotEqual((0x631F - 0x62D6) % 6, 0)   # stride-6 grid
        self.assertNotEqual((0x631F - 0x62D6) % 3, 0)   # stride-3, anchored at 0x62D6
        self.assertNotEqual((0x631F - 0x631D) % 3, 0)   # stride-3, anchored at 0x631D
        # The bytes each grid would cut around the site, held without saying
        # which framing is right: the 6-byte record covering it, and the two
        # stride-3 triples that a grid anchored at 0x631D would start there.
        self.assertEqual(COMMON[0x631E:0x6324], bytes.fromhex('19 02 00 46 19 19'))
        self.assertEqual(COMMON[0x631D:0x6320], bytes.fromhex('14 19 02'))
        self.assertEqual(COMMON[0x6320:0x6323], bytes.fromhex('00 46 19'))
        # The anchor the better-evidenced framing rests on: three 6-byte
        # records repeat byte for byte 0x24 later, so 0x62D6 is where this run
        # starts rather than an arbitrary pick. Deliberately not asserted as
        # fixing the stride -- 0x24 divides by 3 as well, which is why the
        # stride-3 grid stays available and why only the anchor is claimed.
        for first, second, value in ((0x62D6, 0x62FA, '0f 04 00 46 14 14'),
                                     (0x62DC, 0x6300, '19 03 00 64 14 14'),
                                     (0x62E2, 0x6306, '19 02 00 0f 0a 0a')):
            self.assertEqual(COMMON[first:first + 6], bytes.fromhex(value))
            self.assertEqual(COMMON[second:second + 6], bytes.fromhex(value))
            self.assertEqual(second - first, 0x24)


class TheGeneratedTablesStayGenerated(unittest.TestCase):
    """The verdict is a census false positive, recorded in prose. Both tables
    are regenerated by their own tools and must stay byte-identical, which is
    what `call_graph.py --check` reports and what these cases hold: the rows are
    present and read as phantoms, not removed."""

    def test_the_census_row_still_reads_lcall_5a5a(self):
        rows = census_rows('0x0049', '0x5A5A')
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['region'], 'common')
        self.assertEqual(row['opcode'], 'lcall')
        self.assertEqual(row['bucket'], 'A')
        self.assertEqual(int(row['file_offset'], 16), 0x0049)
        self.assertEqual(int(row['target'], 16), 0x5A5A)
        self.assertEqual((int(row['frame_onto']), int(row['frame_over'])),
                         disasm8051.converges_from(COMMON, 0x0049))

    def test_the_census_records_a_competing_record_over_the_same_two_bytes(self):
        # `earlier_record` is the tool's own non-circularity check: the record
        # starting one byte earlier that spans the site. It shares 0x0049 and
        # 0x004A with the booked `lcall` and the tool renders it `mov 0x5a,
        # 0x12`. The same two bytes read two ways, one byte apart, by the tool
        # that booked the row -- which is the sharpest statement available that
        # the site is framing-sensitive. The column is a candidate generator
        # and not an adjudicator, so this is corroboration and not the verdict.
        rows = census_rows('0x0049', '0x5A5A')
        fields = rows[0]['earlier_record'].split()
        self.assertEqual(fields[:4], ['0x00048', '85', '12', '5a'])
        self.assertEqual(' '.join(fields[4:]), 'mov 0x5a,0x12')
        self.assertEqual(int(fields[0], 16), 0x0048)
        self.assertEqual(COMMON[0x0048:0x004B], bytes.fromhex('85 12 5a'))
        # The two records overlap rather than merely sit next to each other.
        self.assertEqual(COMMON[0x0049:0x004B], b'\x12\x5a')

    def test_the_call_graph_row_is_deliberately_untouched(self):
        rows = call_graph_rows('common', '5A5A')
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['name'], 'FUN_CODE_5a5a')
        self.assertEqual(row['annotated'], 'no')
        self.assertEqual(int(row['inbound']), 1)
        self.assertEqual(int(row['lcall']), 1)
        self.assertEqual(int(row['cited_by']), 1)
        self.assertEqual(row['citing'], 'common:5A55')

    def test_the_two_seed_rows_are_deliberately_untouched(self):
        # Retiring either seed needs `--mode rebuild-project`, which two
        # branches cannot both do, so both rows are left as they are and the
        # adjudication is this file plus the write-up beside it.
        for addr in ('0046', '5A5A'):
            rows = index_rows('common', addr)
            self.assertEqual(len(rows), 1, addr)
            self.assertEqual(rows[0]['name'], 'FUN_CODE_' + addr.lower())
            self.assertEqual(rows[0]['seed_basis'], 'call-target')
            self.assertEqual(rows[0]['annotated'], 'no')


if __name__ == '__main__':
    unittest.main()