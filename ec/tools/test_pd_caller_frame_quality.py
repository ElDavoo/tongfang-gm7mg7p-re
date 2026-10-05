#!/usr/bin/env python3
"""Offline checks for the caller frame-length criterion and its CSV column.

Stands in for the three properties `--self-test` does not hold, all of which are
about the *committed artefacts* rather than about the code's own internal
consistency:

  * `frame_insns` in `ec/annotations/pd-index-callers.csv` is
    `len(frame_of(d, caller_file_offset))`, recomputed here from the image for
    every row. A hand-set column would otherwise satisfy `pd_index_geometry.py
    --self-test`, which byte-compares the file against what the tool writes.
  * No row carrying literal loads is ever filed `frame too short to say`, in the
    committed table or for any frame length. This is the calibration rule as a
    test: a short frame is a reason to weaken a negative claim, never a reason
    to drop a positive one.
  * The threshold separates the committed `0x7421`/`0xC9DD` row from the four
    rows with real frames -- in both directions, so a threshold that moved high
    enough to catch every row would fail here as well as one that moved low.

**Every case reads a committed file. None of them is a behaviour.** No EC was
opened, no register was read back, and no frame was watched change on hardware.
A `frame_insns` of 1 is a fact about bytes in `ec/firmware/GMxMGxx_11.800`, not
an observation of what that caller does at run time.

**Expectations are recomputed, not read back from the tool.** The frame-length
cases below walk the image themselves with `disasm8051.OPCODE_LEN` rather than
calling `pd_index_geometry.frame_of()`. A suite that asserted the column against
the very function that wrote it would pass on any consistent misreading, and the
one thing this column carries is a length: `frame_of()` returning a list of the
wrong instructions still returns a list of the right length. The phantom case
then checks the *identity* of the one instruction it finds, which is a claim
about bytes rather than about a count.

The whole-image distribution `docs/findings/pd-caller-frame-quality.md` carries
is deliberately not asserted here. It is a figure over the committed firmware,
stated once in the write-up beside the command that prints it; a second copy in
a test assertion is a value every later change to `caller_rows()` would have to
be reflected in. `pd_caller_frame_quality.py --self-test` holds the relations
that figure's shape depends on, and this file holds the committed rows.

The suite is **not** wired into `.github/scripts/agent-gates.sh`: that file
lives under `.github/`, which this branch's push token cannot write, so the
registration is a human's change. Until it is made the runner finds it by name
and CI does not run it, and nothing here implies otherwise.
"""

import csv
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import pd_caller_frame_quality as F  # noqa: E402
import pd_index_geometry as P  # noqa: E402
from disasm8051 import OPCODE_LEN  # noqa: E402

FIRMWARE = ROOT / 'ec' / 'firmware' / 'GMxMGxx_11.800'
CALLERS_CSV = ROOT / 'ec' / 'annotations' / 'pd-index-callers.csv'

IMAGE = FIRMWARE.read_bytes()
with CALLERS_CSV.open(encoding='utf-8') as fh:
    ROWS = list(csv.DictReader(fh))

# The row pd-index-geometry.md 4.1 attributes to a phantom, and the four rows
# with frames the same page reasons from. Named here rather than counted: the
# phantom is the one row the criterion exists for, and the four are what it has
# to leave alone.
PHANTOM = ("0x7421", "0xC9DD")
REAL_FRAMES = (("0x7421", "0x7CD1"), ("0x9DEC", "0xB452"),
               ("0xB5D3", "0xB838"), ("0xE9F5", "0x66E4"))


def frame_len_recomputed(image: bytes, file_offset: int) -> int:
    """`len(frame_of(d, off))`, derived here instead of called.

    The walk is `frame_of()`'s own idiom -- the longest backward linear walk
    landing exactly on `off`, choosing by length alone -- written out so a bug
    in `frame_of()` cannot satisfy the assertions about its own output. `OPCODE_LEN`
    is the image-independent decode table `frame_of()` itself uses, so what is
    under test is the walk, not the table.
    """
    best = 0
    for back in range(P.FRAME_BACK, 0, -1):
        start = file_offset - back
        if start < 0:
            continue
        i, count = start, 0
        while i < file_offset:
            i += OPCODE_LEN[image[i]]
            count += 1
        if i == file_offset:
            best = max(best, count)
    return best


class FrameInsnsColumn(unittest.TestCase):
    """The column is a measurement of the image, so it is measured again."""

    def test_every_row_matches_a_walk_of_the_image(self):
        for row in ROWS:
            with self.subTest(site=row['site'], caller=row['caller_runtime']):
                self.assertEqual(int(row['frame_insns']),
                                 frame_len_recomputed(IMAGE,
                                                      int(row['caller_file_offset'],
                                                          16)))

    def test_header_carries_the_column(self):
        """`write_callers_csv` emits it, so a regenerated file cannot drop it.

        The CSV's own header rather than the writer's tuple, so a column removed
        from the committed file is caught here as well as one never added.
        """
        self.assertIn('frame_insns', ROWS[0].keys())
        with CALLERS_CSV.open(encoding='utf-8') as fh:
            header = fh.readline().strip().split(',')
        self.assertEqual(header.index('frame_insns'),
                         header.index('frame_over') + 1)

    def test_status_follows_the_column(self):
        """A literal-free row's status is a function of its frame length alone.

        Those are the rows this change is about: with no literals the whole
        literal branch falls away and what is left is the threshold, so the
        CSV's own `literals` cell is enough to recompute the status here without
        re-running the site's term decode. The literal-bearing rows are covered
        by the case below, which asserts the weaker property that still holds
        for them -- that they took the literal branch at all.
        """
        for row in ROWS:
            if row['literals']:
                continue
            with self.subTest(site=row['site'], caller=row['caller_runtime']):
                want = P.CALLER_SHORT_FRAME \
                    if int(row['frame_insns']) < P.MIN_FRAME_INSNS \
                    else P.UNRESOLVED_CALLER
                self.assertEqual(row['status'], want)

    def test_a_row_with_literals_took_the_literal_branch(self):
        """A literal-bearing row's status is one the frame length cannot pick.

        The three literal-branch values are the whole set, so a status outside it
        means the row was graded on its frame rather than on its loads -- the
        failure mode the branch order exists to prevent.
        """
        literal_branch = {P.CALLER_INDEX_LOAD, P.CALLER_NO_INDEX,
                          P.CALLER_UNRESOLVED_INDEX}
        seen = 0
        for row in ROWS:
            if not row['literals']:
                continue
            seen += 1
            with self.subTest(site=row['site'], caller=row['caller_runtime']):
                self.assertIn(row['status'], literal_branch)
        self.assertTrue(seen, "the committed table has no literal-bearing row, "
                              "so this case would pass vacuously")


class ShortFrameNeverLosesALiteral(unittest.TestCase):
    """The calibration rule, as an assertion rather than as a comment."""

    def test_committed_table_has_no_short_row_with_literals(self):
        """Checked against a table that *has* short rows, so it cannot pass empty.

        A committed CSV with nothing filed short would satisfy the loop below
        trivially, so the guard comes first rather than after it: the property is
        only worth anything if there is a row to check it on.
        """
        short = [row for row in ROWS if row['status'] == P.CALLER_SHORT_FRAME]
        self.assertTrue(short, "the committed table files no row short, so this "
                               "case would pass vacuously")
        for row in short:
            with self.subTest(site=row['site'], caller=row['caller_runtime']):
                self.assertEqual(row['literals'], '')

    def test_caller_status_keeps_the_literal_branch_first(self):
        """No frame length below the threshold takes a literal-bearing row out of
        its branch.

        Swept rather than spot-checked: the property is that *no* short frame
        loses the literal branch, so one hand-built case would understate it.
        """
        literals = {'R7': 4, 'R3': 1}
        for insns in range(0, P.MIN_FRAME_INSNS):
            with self.subTest(frame_insns=insns):
                self.assertNotEqual(
                    P.caller_status(literals, {'R7', 'R6'}, insns),
                    P.CALLER_SHORT_FRAME)
                self.assertEqual(
                    P.caller_status(literals, {'R7', 'R6'}, insns),
                    P.CALLER_INDEX_LOAD)

    def test_short_frame_says_nothing_about_the_index(self):
        """The value must not read as a claim about the index either way.

        Checked by name: the strings below are the ones that do assert
        something about an index, and the new value is none of them, so a
        reword that reintroduced such a claim fails here.
        """
        about_an_index = (P.CALLER_INDEX_LOAD, P.CALLER_NO_INDEX,
                          P.CALLER_UNRESOLVED_INDEX)
        self.assertNotIn(P.CALLER_SHORT_FRAME, about_an_index)
        self.assertNotIn(P.UNRESOLVED_CALLER, about_an_index)


class ThresholdSeparatesThePhantom(unittest.TestCase):
    """The threshold is a line between two kinds of row, and both sides move."""

    def _insns(self, key):
        for row in ROWS:
            if (row['site'], row['caller_runtime']) == key:
                return int(row['frame_insns'])
        self.fail(f"{key} is not a row of {CALLERS_CSV.name}")

    def test_phantom_is_below_and_real_frames_above(self):
        phantom = self._insns(PHANTOM)
        for key in REAL_FRAMES:
            with self.subTest(site=key[0], caller=key[1]):
                self.assertGreater(self._insns(key), P.MIN_FRAME_INSNS)
        self.assertLess(phantom, P.MIN_FRAME_INSNS)

    def test_the_phantom_frame_is_one_nop_inside_a_previous_instruction(self):
        """The whole frame lies inside the previous instruction's encoding.

        `pd-index-geometry.md` 4.1 shows the `0x12` at file `0x2C9DD` is the low
        operand byte of `mov dptr,#0x0012` at `0x2C9DB`. That is a claim about
        *which* byte the frame consists of, so it is checked here as the identity
        of the one instruction -- the byte values below are read straight out of
        `IMAGE`, not out of the walk. The length itself is
        `FrameInsnsColumn`'s case; this one is what a length alone cannot say.
        """
        off = int(next(row['caller_file_offset'] for row in ROWS
                       if (row['site'], row['caller_runtime']) == PHANTOM), 16)
        frame = P.frame_of(IMAGE, off)
        self.assertEqual(len(frame), self._insns(PHANTOM))
        self.assertEqual([(o, r[0]) for o, r in frame], [(off - 1, 0x00)])
        # `0x00` is `nop`; the instruction the frame's one byte really belongs
        # to is the `mov dptr,#0x0012` starting two bytes earlier, so the frame
        # is one byte of its middle operand plus the `nop` it is read as. The
        # `74 20` after it is the `mov a,#0x20` 4.1's listing continues with.
        self.assertEqual(IMAGE[off - 2:off + 3],
                         bytes((0x90, 0x00, 0x12, 0x74, 0x20)))


class BucketsFollowTheThreshold(unittest.TestCase):
    """The measurement tool's own labelling, without its census.

    The distribution over the whole image is the write-up's figure and is not
    pinned here; what is pinned is that a bucket label means the same thing the
    criterion does, because a report that bucketed by something else would be
    arguing for a threshold it does not measure.
    """

    def test_every_short_bucket_is_below_the_threshold(self):
        for label in F.buckets()[:-1]:
            with self.subTest(bucket=label):
                self.assertLess(int(label), P.MIN_FRAME_INSNS)

    def test_the_wide_bucket_starts_at_the_threshold(self):
        wide = F.buckets()[-1]
        self.assertEqual(wide, f">={P.MIN_FRAME_INSNS}")
        self.assertEqual(F.bucket_of(P.MIN_FRAME_INSNS), wide)
        self.assertNotEqual(F.bucket_of(P.MIN_FRAME_INSNS - 1), wide)

    def test_committed_rows_land_in_a_bucket(self):
        for row in ROWS:
            with self.subTest(site=row['site'], caller=row['caller_runtime']):
                self.assertIn(F.bucket_of(int(row['frame_insns'])), F.buckets())


if __name__ == '__main__':
    unittest.main()