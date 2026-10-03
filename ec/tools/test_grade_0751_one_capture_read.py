#!/usr/bin/env python3
"""`main`'s one read of a capture, and what a truncated early-exit row does (#767).

Its own file rather than cases in `test_grade_0751_isolation.py`, which is
several times this length and whose every append has been a merge conflict:
this is a suite about one question -- how many times `main` opens each
capture, and what the one read it takes is refused for -- and it stands in
for nothing that suite already holds. The open-count idiom it reuses is
`ExistingMarkLabelTests.count_opens` and `snapshot_then_append`, borrowed
rather than copied, so the two suites cannot drift on how the count is
taken.

Every fixture here is a `tempfile` file this checkout wrote or a committed
capture under `ec/tools/testdata/`. No EC is opened, no register is read
back, no capture is taken on the machine, and no §3 run is re-applied: the
probes are writes to a temporary file, and a "watcher" here is an append
made by the test itself at the instant the read returns.
"""
import builtins
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'grade', HERE / 'grade_0751_isolation.py')
grade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grade)

REPO = HERE.parent.parent
# The two programs that unpack `read_capture`'s two-tuple. The grader's own
# `main` stopped calling it (#767) and the reader kept its contract for these,
# which is why the case below greps their call sites rather than trusting that
# nothing moved.
DOOR = REPO / 'ec' / 'tools' / 'grade_gpu_door.py'
PROBE = REPO / 'windows' / 'tools' / 'manual_fan_ctrl_probe.py'


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = grade.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def snapshot_then_append(path, row):
    """A stand-in for a watcher landing a row at the instant `main` reads.

    Borrowed from `ExistingMarkLabelTests` rather than written again, and
    patched over `capture_snapshot` because that is the one read this change
    leaves in `main`. The append is *after* the delegate on purpose: it is
    what a second read would have picked up and the first had not, which is
    the whole of the two-moments defect.
    """
    real = grade.capture_snapshot

    def read_then_append(p):
        rows, failure, has_bom = real(p)
        with open(p, 'a', newline='') as f:
            f.write(row + '\n')
        return rows, failure, has_bom
    return read_then_append


def count_opens(path, call):
    """What `call` returned, and how many times it `open()`ed `path`.

    The count rather than the effect, and the reason is that the two reads
    this change removed differ from one read only when an append lands
    between them -- a test that waited for that would pass on a quiet
    filesystem. Counting is true every run.
    """
    opened = []
    real = builtins.open

    def counting(name, *args, **kwargs):
        if str(name) == str(path):
            opened.append(str(name))
        return real(name, *args, **kwargs)
    with patch.object(builtins, 'open', counting):
        return call(), len(opened)


class OneOpenPerCaptureTests(unittest.TestCase):
    # One of each row kind, so a reader that drops the wrong one is caught by
    # the census line's own counts rather than by a row list compared here.
    # The mark labels are §6's own forms, so the run gets as far as a window
    # report and the case is about the read rather than about placement.
    ROWS = [
        '# 0751 isolation, 0xA0 block',
        'ts,addr,old,new',
        '',
        '2026-01-01T12:00:05.000+01:00,0x0701,0x00,0x11',
        '2026-01-01T12:00:00.000+01:00,MARK,,no-op wrote 0x0751=0xA0',
        '2026-01-01T12:00:30.000+01:00,MARK,,restored 0x0751=0xA0',
    ]
    CRASH = (f"{grade.EARLY_EXIT_TAG} 2026-01-01T12:00:10.000+01:00,"
             "manual_fan_ctrl_probe: RuntimeError: observation failed mid-run")

    def capture(self, rows, tmp, name='capture.csv'):
        path = Path(tmp) / name
        path.write_text(''.join(row + '\n' for row in rows), encoding='utf-8')
        return str(path)

    def test_the_capture_is_opened_once_in_main(self):
        # The issue's first "Done" bullet, as a count. Measured on this tree
        # before the change: two -- `read_capture` and then
        # `read_early_exits`, each opening the path once, a few lines apart in
        # `main`'s read loop. The result is asserted beside the count so a
        # `main` that returned the right marks without opening the file
        # cannot pass this by returning something constant.
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(self.ROWS, tmp)
            (rc, out, _), opens = count_opens(path, lambda: run(path))
        self.assertEqual(opens, 1)
        self.assertEqual(rc, 0, out)
        # What the one read produced, so the count is not the only assertion:
        # the `#` and the blank are dropped, the header is not a data row, and
        # the change row is a change.
        self.assertIn('2 mark(s), 1 change row(s)', out)

    def test_the_census_line_is_one_moment(self):
        # The issue's item (1) made to land. A watcher appends a well-formed
        # early-exit row at the instant `main` reads: the census line has to
        # describe the file as it was at that read, and a second unpatched run
        # has to see the row. Both directions, so a `main` that never opened
        # the file cannot pass this by printing a constant.
        with tempfile.TemporaryDirectory() as tmp:
            path = self.capture(self.ROWS, tmp)
            with patch.object(grade, 'capture_snapshot',
                              snapshot_then_append(path, self.CRASH)):
                rc, patched, _ = run(path)
            rc2, second, _ = run(path)
        # The row landed *after* the read both times, so the first line is
        # the same and the second is the one that has it -- which is the
        # whole claim: one moment, described by both halves of the line.
        self.assertIn('2 mark(s), 1 change row(s)', patched)
        self.assertNotIn('early-exit row(s)', patched)
        self.assertIn('2 mark(s), 1 change row(s), 1 early-exit row(s)', second)
        self.assertEqual(rc2, 1)


class TruncatedEarlyExitRowTests(unittest.TestCase):
    # The defect behind the issue's item (2), which that item under-describes.
    # A capture whose last line is an early-exit row cut short is a *static*
    # file: a watcher killed mid-`flush` leaves exactly that on disk, and so
    # does a row an operator edited. No race is needed and none is staged
    # here.
    ROWS = [
        'ts,addr,old,new',
        '2026-01-01T12:00:00.000+01:00,MARK,,no-op wrote 0x0751=0xA0',
        '2026-01-01T12:00:01.000+01:00,0x0751,aa,bb',
        '2026-01-01T12:00:30.000+01:00,MARK,,restored 0x0751=0xA0',
    ]
    # Three truncations, and they are not one case. `parse_ts` is
    # `datetime.fromisoformat`, which accepts a bare `YYYY-MM-DDThh:mm:ss`
    # and returns a *naive* datetime, so a stamp cut before its offset still
    # parses -- and arrives at `charge_early_exits` as a `ts` while every
    # window's carries the offset the writer's `now()` put there. The
    # comparison `w.ts <= e.ts` then raised `TypeError: can't compare
    # offset-naive and offset-aware datetimes` straight out of `main`,
    # killing the run with a traceback over a file the operator did nothing
    # wrong to. The third is a stamp cut so far that `parse_ts` refuses it,
    # which was already handled and is the case the issue describes.
    CUTS = [
        ('cut before the offset', f'{grade.EARLY_EXIT_TAG} 2026-01-01T12:00:10'),
        ('cut inside the milliseconds', f'{grade.EARLY_EXIT_TAG} 2026-01-01T12:00:10.4'),
        ('cut so parse_ts refuses it', f'{grade.EARLY_EXIT_TAG} 2026-01-01T12:00:10.'),
    ]

    def _run_with(self, trailing):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'capture.csv'
            path.write_text(''.join(row + '\n' for row in self.ROWS),
                            encoding='utf-8')
            with open(path, 'a', encoding='utf-8') as f:
                f.write(trailing + '\n')
            return run(str(path))

    def test_a_truncated_trailing_early_exit_row_is_refused_by_name(self):
        for label, trailing in self.CUTS:
            with self.subTest(label):
                rc, out, err = self._run_with(trailing)
                # Named, not crashed. A crash-absence assertion is the one
                # shape that would pass for the wrong reason, so the sentence
                # itself is asserted below.
                self.assertEqual(rc, 1, err)
                self.assertNotIn('Traceback', err)
                # The row is still counted on the census line, because it is
                # in the file: a truncated row is not a row that was not
                # there.
                self.assertIn('1 early-exit row(s)', out)
                flat = ' '.join(out.split())
                # And it is named, not placed. Which sentence it gets is the
                # difference between the three truncations, and each says
                # what the reader could not do with the row rather than
                # asserting only that it did not raise.
                self.assertIn('NOT PLACED --', flat)
                if trailing.endswith('10.'):
                    # The stamp `parse_ts` refuses outright: no timestamp at
                    # all, which was the case the issue named.
                    self.assertIn('carries no timestamp this can read', flat)
                else:
                    # The stamp that still parses and carries no offset. The
                    # mismatch is named, because the row is well-formed on its
                    # own and it is only against these marks that it cannot
                    # be placed -- which is what the operator has to be told.
                    self.assertIn('carries no UTC offset', flat)
                    self.assertIn('cannot be compared', flat)
                    self.assertIn('no window for it to have cut short', flat)
                # No block is withheld over a row that was never placed, so
                # the run is refused for the row and the blocks still read.
                self.assertIn('restored 0x0751=0xA0', flat)


class ReadCaptureContractTests(unittest.TestCase):
    # The issue's third "Done" bullet. `main` stopped calling `read_capture`
    # (#767) and the reader kept its signature and its two-tuple, because two
    # other programs unpack it. Both halves matter: the first is what stops a
    # well-meant signature change here, the second is what would let a rename
    # in either consumer pass unnoticed until that tool ran.
    FIXTURE = str(HERE / 'testdata' / '0751-isolation-example-quiet.csv')

    def test_read_capture_still_returns_the_two_tuple_the_other_tools_unpack(self):
        marks, changes = grade.read_capture(self.FIXTURE)
        # The two-tuple itself, unpacked the way both consumers unpack it: a
        # two-item return whose halves are the readers' own row types, so a
        # reader that returned a list of pairs or added a third item would
        # fail here rather than at the consumer.
        self.assertIsInstance(marks, list)
        self.assertIsInstance(changes, list)
        self.assertTrue(marks)
        self.assertTrue(all(isinstance(m, grade.Window) for m in marks))
        self.assertTrue(all(isinstance(c, grade.Change) for c in changes))
        # And the consumers still name it, by grep rather than by import: the
        # point is that a rename in either file reddens here, and importing
        # them would exercise their module bodies instead.
        for path in (DOOR, PROBE):
            with self.subTest(path.name):
                text = path.read_text(encoding='utf-8')
                self.assertIn('read_capture', text)
                self.assertRegex(
                    text,
                    r'\w+,\s*\w+\s*=\s*(?:fan\.|grader\.)?read_capture\(')

    def test_early_exits_of_is_read_early_exits_over_one_row_list(self):
        # The sibling `early_exits_of` holds `read_early_exits`' body, so the
        # two have to agree on every row shape rather than by a reader's
        # eye. Compared over a capture carrying a placed row, a row with no
        # readable stamp and a row with the reason in a second field -- the
        # three shapes the writer produces.
        rows = [
            'ts,addr,old,new',
            '2026-01-01T12:00:00.000+01:00,MARK,,no-op wrote 0x0751=0xA0',
            f'{grade.EARLY_EXIT_TAG} 2026-01-01T12:00:10.000+01:00,'
            'manual_fan_ctrl_probe: RuntimeError: observation failed mid-run',
            f'{grade.EARLY_EXIT_TAG} 2026-01-01T12:00:11,cut short',
            f'{grade.EARLY_EXIT_TAG} not a timestamp at all',
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'capture.csv'
            path.write_text(''.join(row + '\n' for row in rows),
                            encoding='utf-8')
            over_path = grade.read_early_exits(str(path))
            over_rows = grade.early_exits_of(grade.capture_rows(str(path)),
                                             str(path))
        self.assertEqual([(e.ts, e.reason) for e in over_path],
                         [(e.ts, e.reason) for e in over_rows])
        # Three rows, and the shapes are actually different -- so this is not
        # one shape compared with itself.
        self.assertEqual([e.ts is None for e in over_path],
                         [False, False, True])


class MainRefusalOrderTests(unittest.TestCase):
    # `main` no longer calls `read_capture`, so it raises the two refusals
    # itself, off the one buffer `capture_snapshot` read. They have to be the
    # same two, in the same order, with the same sentences -- the anti-drift
    # contract `bom_refusal` exists for, now with a third reader.
    #
    # **A BOM plus an undecodable byte is still named by the mark**, which is
    # the order `read_capture` and `existing_mark_findings` already agreed on,
    # and the case below is what holds the third reader to it rather than
    # leaving the agreement to two of the three.
    #
    # **A short row plus an undecodable byte is the one that changed.**
    # `read_capture` streams the text layer, so its wrapper decodes 8 KiB at a
    # time and which of the two faults it names depended on which chunk each
    # landed in: measured on this tree before the change, a short row
    # immediately above an undecodable byte raised the `UnicodeDecodeError`,
    # and the same two rows 400 KB apart raised the short-row `ValueError`
    # instead. `main` decides the decode first, on the whole buffer, at every
    # size. That is the improvement -- deterministic rather than a function of
    # how large the file is -- and it is pinned rather than described, because
    # a size-dependence that came back would be invisible on any single small
    # fixture.
    SHORT_ROW = b'2026-01-01T12:00:01.000+01:00,0x0751\n'
    BAD_BYTE = b'2026-01-01T12:00:02.000+01:00,0x0751,aa,\xe9\n'
    HEAD = (b'ts,addr,old,new\n'
            b'2026-01-01T12:00:00.000+01:00,MARK,,no-op wrote 0x0751=0xA0\n')

    def _two_fault(self, tmp, gap_rows):
        """A short row and an undecodable byte, `gap_rows` apart."""
        path = Path(tmp) / 'two-fault.csv'
        with open(path, 'wb') as f:
            f.write(self.HEAD)
            f.write(self.SHORT_ROW)
            f.write(b''.join(b'# ' + b'x' * 40 + b'\n' for _ in range(gap_rows)))
            f.write(self.BAD_BYTE)
        return str(path)

    def test_a_two_fault_file_is_refused_the_same_way_at_every_size(self):
        seen = {}
        for label, gap in (('adjacent', 0), ('400 KB apart', 9000)):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._two_fault(tmp, gap)
                rc, out, err = run(path)
            seen[label] = rc
            # The run is refused, and refused by the decode rather than by
            # the row -- the whole buffer is decoded before any row is
            # looked at, so the answer does not depend on where the faults
            # fell in it. The `position` in the exception does move with the
            # file's size, because the byte is at a different offset, so what
            # is compared is which refusal named the file and not its text.
            self.assertEqual(rc, 1, out)
            self.assertIn("'utf-8' codec can't decode", err)
            self.assertNotIn('short row', err)
        self.assertEqual(seen['adjacent'], seen['400 KB apart'])
        # The recorded half: `read_capture` is what the other two consumers
        # still call, and its answer to the same bytes is still
        # size-dependent. Asserted so the write-up's before-and-after is
        # checkable rather than remembered.
        verdicts = {}
        for label, gap in (('adjacent', 0), ('400 KB apart', 9000)):
            with tempfile.TemporaryDirectory() as tmp:
                path = self._two_fault(tmp, gap)
                try:
                    grade.read_capture(path)
                    verdicts[label] = 'no raise'
                except (ValueError, UnicodeDecodeError) as e:
                    verdicts[label] = type(e).__name__
        self.assertNotEqual(verdicts['adjacent'], verdicts['400 KB apart'])

    def test_a_bom_and_an_undecodable_byte_are_still_refused_the_same_way(self):
        # The mark first, on both the ways out: `bom_refusal` is one sentence
        # and the mark is decidable from three bytes without a decode, so a
        # file carrying both faults is named by the mark whether it is small
        # enough to be one chunk or not.
        cases = {
            'marked, decodes': grade.BOM_BYTES + b'ts,addr,old,new\n',
            'marked, undecodable': (grade.BOM_BYTES
                                    + b'ts,addr,old,new\n'
                                    + b'2026-01-01T12:00:01.000+01:00,'
                                      b'0x0751,aa,\xe9\n'),
        }
        for label, payload in cases.items():
            with self.subTest(label):
                with tempfile.TemporaryDirectory() as tmp:
                    path = self._written(tmp, 'bom.csv', payload)
                    rc, out, err = run(path)
                    # The very sentence `read_capture` raises and
                    # `existing_mark_findings` reports, so all three agree.
                    _, refused, _ = grade.existing_mark_findings(path)
                self.assertEqual(rc, 1)
                self.assertIn(grade.bom_refusal(path), err)
                self.assertIn(grade.bom_refusal(path), refused[0][1])
                # And nothing was graded over it.
                self.assertNotIn('=== mark census', out)

    def test_an_undecodable_byte_alone_is_still_the_bare_decode_error(self):
        # The other side of the order: a file with no mark and a byte the
        # codec cannot read is still refused by the decode, and still by the
        # `UnicodeDecodeError` itself rather than by a sentence of this tool's
        # own -- the grading raises what the format's codec raises, and the
        # notice is the one that wraps it.
        with tempfile.TemporaryDirectory() as tmp:
            path = self._written(
                tmp, 'latin1.csv',
                b'ts,addr,old,new\n'
                b'2026-01-01T12:00:00.000+01:00,MARK,,caf\xe9\n')
            rc, out, err = run(path)
        self.assertEqual(rc, 1)
        self.assertIn("codec can't decode byte 0xe9", err)
        self.assertNotIn('byte-order mark', err.lower())
        self.assertNotIn('=== mark census', out)

    def _written(self, tmp, name, payload):
        path = Path(tmp) / name
        path.write_bytes(payload)
        return str(path)


if __name__ == '__main__':
    unittest.main()
