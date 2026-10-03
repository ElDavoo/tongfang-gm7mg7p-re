#!/usr/bin/env python3
"""Offline checks over the converter and over the one real log it reads.

This is the suite that reads `evidence/`, which
`test_grade_0751_isolation.py` deliberately does not: every case there is over
a constructed capture in `testdata/`, because the grader's own refusals are
arguments about files and a real one would put the answer in the fixture. Here
the question is the other way round -- does the committed 2026-09-23 log convert
into something the committed grader reads -- and that cannot be asked of a
synthetic log, because a synthetic log would agree with this converter by
construction.

No hardware, no Windows, and no EC: both tools are stdlib-only, and every case
here reads committed files.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name, path):
    """One module from one path, under `name`.

    The same `importlib` shape `test_grade_0751_isolation.py` uses, and for
    the same reason: the converter reads the grader by path rather than
    importing it, and a suite that wanted the same object from both would be
    asserting on a second copy of a module rather than on the one the tool
    loads.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


convert = _load('probe_log_to_capture', HERE / 'probe_log_to_capture.py')
grade = _load('grade', HERE / 'grade_0751_isolation.py')

# The two committed files this is about: the probe console log from the issue
# #99 run, and the capture committed here that converts it. The log is dated;
# the capture carries the obviously-placeholder date this repository's testdata
# requires of anything in that directory, so a reconstructed timestamp can
# never be read as an observed one.
LOG = str(REPO / 'evidence' / 'ec-watch' / '2026-09-23-0751-isolation.txt')
DERIVED = str(HERE / 'testdata' / '0751-isolation-probe-log'
              / '2026-01-01-0751-isolation-from-probe-log.csv')
ANCHOR = '2026-01-01T12:00:00'

# The two older captures issue #124 asks about: they predate the MARK row, so
# `main` refuses them, and the question is whether that reads as a message or as
# a crash.
MARKLESS = (str(REPO / 'evidence' / 'ec-watch'
                / '2026-09-23-power-mode-cycle-0700-07ff.csv'),
            str(REPO / 'evidence' / 'ec-watch'
                / '2026-09-18-profile-switch-0700-07ff.csv'))


def run(tool, *argv):
    """`tool.main(argv)` with both streams captured, as (rc, out, err).

    Driven through `main` rather than through the tool's internals because what
    each refusal is is a command-line property: a converter that raised instead
    of returning 1, or a grader that printed a traceback, passes every case
    written against the functions below.
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = tool.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def convert_to(path, out, anchor=ANCHOR, gap=None):
    """`convert.main` over `path`, and the file it wrote.

    `(rc, stdout, stderr, bytes)`. The bytes rather than the text, because the
    committed capture is compared exactly: a header line or a terminator that
    moved would leave the text identical under a reader and different on disk.
    """
    argv = [path, '--anchor', anchor, '--out', out]
    if gap is not None:
        argv += ['--block-gap', str(gap)]
    rc, stdout, stderr = run(convert, *argv)
    written = Path(out).read_bytes() if Path(out).exists() else b''
    return rc, stdout, stderr, written


# The one convertible log, as the pieces the refusal cases break. Written out
# rather than cut out of the committed file so each case names the line it broke
# and nothing else moves with it; the committed log is read whole, over its real
# content, in `CommittedLogTests`.
GOOD_HEADER = ("# a probe run\n"
               "# 2026-01-01T12:00:01Z, Control Center running\n")
GOOD_BLOCK = ("=== write 0x0751=0xA0 (hold 20s) ===\n"
              "0x0751 currently 0x10; writing 0xA0, holding 20s\n"
              "    + 0.0s  0x0751: 0x10 -> 0xA0\n"
              "restored 0x0751 -> 0x10\n"
              "SUMMARY: addresses that moved while only 0x0751 was written:\n"
              "  0x0751: 0x10 -> ... (last 0xA0)\n")


class CommittedLogTests(unittest.TestCase):
    """The committed log, converted, and the committed grader's report on it."""

    def test_the_conversion_is_the_committed_capture_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, err, written = convert_to(LOG, str(Path(tmp) / 'out.csv'))
        self.assertEqual(rc, 0, err)
        # Byte for byte, not a line count and not a row count: this file is the
        # converter's entire output and it is small, so a parser change that
        # moves anything in it -- a timestamp, the header's own wording, an
        # order -- is a diff on a committed file rather than a sentence nobody
        # reads twice. `--anchor` is the committed fixture's own, which is the
        # point of requiring it: the fixture names the choice it was made with.
        self.assertEqual(written, Path(DERIVED).read_bytes())

    def test_the_committed_grader_reads_it_and_exits_zero(self):
        rc, out, err = run(grade, DERIVED)
        self.assertEqual(rc, 0, err)
        # A figure the claim needs, not a count of the repository: one window
        # per mark is what the six marks of three blocks produce, and it is the
        # first thing to go wrong if a mark is dropped or two are folded.
        self.assertIn('=== 6 window(s), one per mark ===', out)
        self.assertIn("None of the §4.1-§4.3 bytes moved in any window", out)

    def test_every_block_is_intact_and_named_by_its_value(self):
        rc, out, _ = run(grade, DERIVED)
        self.assertEqual(rc, 0)
        verdicts = [line for line in out.splitlines()
                    if 'intact -- last mark' in line]
        # One line per block, and each naming the value its `write` mark
        # carried -- which is the whole of what `intact` is: the block's last
        # mark is its restore, so the capture can show the byte put back. Three
        # lines and three values rather than "3 blocks": a converter that lost
        # a block would print two and still match a count written here.
        self.assertEqual(len(verdicts), 3)
        self.assertTrue(all("last mark 'restored 0x0751=0x10' is the restore"
                            in line for line in verdicts))
        for value in ('0xA0', '0x00', '0x10'):
            self.assertIn(f"value under test {value}; roles write, restore", out)

    def test_the_six_marks_are_the_logs_own_in_the_logs_own_order(self):
        marks, _ = grade.read_capture(DERIVED)
        self.assertEqual([m.label for m in marks], [
            'wrote 0x0751=0xA0', 'restored 0x0751=0x10',
            'wrote 0x0751=0x00', 'restored 0x0751=0x10',
            'wrote 0x0751=0x10', 'restored 0x0751=0x10'])
        # The third block's mark is `wrote`, not `no-op wrote`. The log calls
        # that write a no-op in its own closing note and `===` line, and
        # relabelling it would be inventing §3's control-arm form: `parse_mark`
        # reads the two as different roles on purpose, and a control arm that
        # was never recorded is not one this tool may write on its behalf.
        self.assertEqual(grade.parse_mark(marks[4].label), ('write', 0x10))

    def test_the_third_block_records_no_change_row(self):
        # The log's third `SUMMARY:` names no address, and this pins the other
        # half of that: it converted to no change row either, so the grader's
        # zeros over that block are zeros over a block with nothing in it
        # rather than over one whose rows went missing in the conversion.
        marks, changes = grade.read_capture(DERIVED)
        windows = grade.build_windows(marks, changes)
        blocks, _ = grade.assign_blocks(windows)
        by_value = {b.value: b for b in blocks}
        self.assertEqual([c.addr for c in changes], [0x0751, 0x0751])
        self.assertEqual(sum(len(w.changes) for w in by_value[0x10].windows), 0)
        self.assertEqual(sum(len(w.changes) for w in by_value[0xA0].windows), 1)

    def test_the_three_readers_agree_on_the_marks_it_carries(self):
        # The anti-drift guard the grader's own suite runs over every committed
        # fixture under `testdata/`; this file is now one of them, and this is
        # the case stated over it directly so a failure here names this capture
        # rather than whichever subTest the walk reached first.
        self.assertEqual(
            [(ts, label) for _, ts, label, _ in
             grade.existing_mark_provenance(DERIVED)],
            grade.existing_mark_labels(DERIVED))
        # And the strict reader holds no mark `read_capture` did not take.
        strict = [ts for ts, _ in grade.existing_mark_labels(DERIVED)]
        self.assertEqual([m.ts.isoformat() for m in grade.read_capture(DERIVED)[0]],
                         strict)

    def test_the_header_carries_the_four_caveats_and_no_early_exit_row(self):
        lines = Path(DERIVED).read_text(encoding="utf-8").splitlines()
        for title, _ in convert.CAVEATS:
            self.assertTrue(
                any(line.startswith(f"# caveat: {title}.") for line in lines),
                title)
        # The property, not the spelling: `read_early_exits` keeps exactly the
        # rows the other readers drop, and it recognises one by this phrase
        # alone. A header carrying one would charge every block's windows and
        # withhold all of them over a file that records no crash -- and the log
        # this file derives from transcribes its own notes, so the phrase could
        # arrive here from the input rather than only from a reformatting.
        self.assertEqual([line for line in lines
                          if line.startswith(grade.EARLY_EXIT_TAG)], [])

    def test_the_header_names_the_choices_and_the_sources_own_stamp(self):
        text = Path(DERIVED).read_text(encoding="utf-8")
        # A reconstructed timestamp beside the observed one is the difference
        # between a derived capture and a capture, and it is only legible if
        # both are written down.
        self.assertIn("2026-09-23T16:31:01Z", text)
        self.assertIn("--anchor, a choice, not an observation", text)
        self.assertIn(f"anchor this file was given: {ANCHOR}", text)
        self.assertIn("--block-gap, a choice", text)
        # And the log's own notes came across: the closing one is what says the
        # PWM rows were omitted, which is what the third caveat is about.
        self.assertIn("changes omitted above", text)


class OlderCapturesTests(unittest.TestCase):
    """The two pre-MARK captures issue #124 names."""

    def test_each_is_refused_with_a_message_and_not_a_crash(self):
        for path in MARKLESS:
            with self.subTest(capture=Path(path).name):
                rc, _, err = run(grade, path)
                self.assertEqual(rc, 1)
                self.assertIn('no MARK rows', err)

    def test_each_still_reads_as_capture_rows(self):
        # What the refusal is about: these files are captures, and they carry
        # change rows. `read_capture` takes them and finds no MARK among them,
        # which is why the message is about marks and not about the file being
        # unreadable -- a reader that had failed on the file would say so
        # instead, and the two are different verdicts.
        for path in MARKLESS:
            with self.subTest(capture=Path(path).name):
                marks, changes = grade.read_capture(path)
                self.assertEqual(len(marks), 0)
                self.assertGreater(len(changes), 0)


class LegacyLogThroughTheGraderTests(unittest.TestCase):
    """What `main` does with the log it cannot read."""

    def test_it_names_the_file_and_the_short_row_and_does_not_raise(self):
        rc, _, err = run(grade, LOG)
        self.assertEqual(rc, 1)
        self.assertIn(LOG, err)
        self.assertIn("short row", err)
        self.assertIn("'=== write 0x0751=0xA0 (hold 20s) ==='", err)
        # And the sentence says what to do with a file of that shape, which is
        # what makes this a refusal rather than an unexplained exit.
        self.assertIn('probe_log_to_capture.py', err)

    def test_a_bom_is_refused_by_the_readers_own_sentence(self):
        # The other file-level refusal, over a constructed file: `main` prints
        # the exception's text, so the warning the operator already reads from
        # `existing_mark_findings` and the error the grading raises are one
        # string rather than two that have to agree.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bom.csv'
            path.write_bytes(grade.BOM_BYTES + b"ts,addr,old,new\n")
            rc, _, err = run(grade, str(path))
        self.assertEqual(rc, 1)
        self.assertIn(grade.bom_refusal(str(path)), err)


class SummaryCrossCheckTests(unittest.TestCase):
    """The one check this format supports, run as a refusal."""

    def _converted(self, tmp, edited):
        path = Path(tmp) / 'log.txt'
        path.write_text(edited, encoding="utf-8")
        return convert_to(str(path), str(Path(tmp) / 'out.csv'))

    def test_a_summary_that_disagrees_with_its_own_rows_is_refused(self):
        source = Path(LOG).read_text(encoding="utf-8")
        # One digit, in the first block's summary only: the rows still say
        # `0x10 -> 0xA0` and the claim beside them now says it started at
        # `0x11`. Both halves of the file are unchanged in every other respect,
        # so what refuses it is the cross-check and nothing else.
        edited = source.replace('  0x0751: 0x10 -> ... (last 0xA0)',
                                '  0x0751: 0x11 -> ... (last 0xA0)')
        self.assertNotEqual(edited, source)
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, err, written = self._converted(tmp, edited)
            self.assertEqual(rc, 1)
            self.assertIn('block 1', err)
            self.assertIn('0x0751', err)
            self.assertEqual(written, b'')

    def test_a_summary_naming_an_address_the_rows_do_not_is_refused(self):
        source = Path(LOG).read_text(encoding="utf-8")
        edited = source.replace('  0x0751: 0x10 -> ... (last 0xA0)',
                                '  0x0751: 0x10 -> ... (last 0xA0)\n'
                                '  0x075B: 0x70 -> ... (last 0x71)')
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, err, written = self._converted(tmp, edited)
        self.assertEqual(rc, 1)
        self.assertIn('0x075B', err)
        self.assertEqual(written, b'')

    def test_the_committed_log_passes_its_own_cross_check(self):
        # The other direction, and the one that would catch a cross-check
        # tightened into something the real file cannot satisfy: the committed
        # log converts, so its summaries and its rows already agree.
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, err, _ = convert_to(LOG, str(Path(tmp) / 'out.csv'))
        self.assertEqual(rc, 0, err)


class RefusalTests(unittest.TestCase):
    """The refusals, over a log written for each.

    Each is the committed log's own shape with one thing wrong with it, so a
    refusal that fires is the one under test and not a neighbour of it. Every
    case asserts two things: a non-zero exit with the reason on stderr, and no
    file written -- a half-converted capture on disk is a file the grader would
    open and report on as though it were a run.
    """

    def _refused(self, text, *expected):
        with tempfile.TemporaryDirectory() as tmp:
            rc, stdout, err, written = self._converted(tmp, text)
            self.assertEqual(rc, 1, f"not refused; stdout was {stdout!r}")
            self.assertEqual(written, b'')
            for phrase in expected:
                self.assertIn(phrase, err)
            return err

    def _converted(self, tmp, text):
        path = Path(tmp) / 'log.txt'
        path.write_text(text, encoding="utf-8")
        return convert_to(str(path), str(Path(tmp) / 'out.csv'))

    def test_a_log_with_no_run_timestamp_in_its_header(self):
        self._refused(GOOD_BLOCK, 'no run timestamp in the header')

    def test_a_block_with_no_restore_line(self):
        text = GOOD_HEADER + GOOD_BLOCK.replace('restored 0x0751 -> 0x10\n', '')
        self._refused(text, "no 'restored ...' line")

    def test_a_line_it_does_not_recognise(self):
        text = GOOD_HEADER + GOOD_BLOCK + "and then something else entirely\n"
        self._refused(text, 'is not a line this reads')

    def test_an_offset_that_is_not_a_number_of_seconds(self):
        text = GOOD_HEADER + GOOD_BLOCK.replace(
            '    + 0.0s  0x0751', '    + abc s  0x0751')
        self._refused(text, "'abc' is not a number of seconds")

    def test_an_offset_that_goes_backwards_inside_a_block(self):
        # A second change row, later in address order and earlier in time: the
        # two rows are each well formed and only their offsets disagree, so
        # nothing but the ordering check can catch it.
        text = (GOOD_HEADER
                + GOOD_BLOCK.replace(
                    '    + 0.0s  0x0751: 0x10 -> 0xA0',
                    '    + 5.0s  0x0751: 0x10 -> 0xA0\n'
                    '    + 1.0s  0x075B: 0x70 -> 0x71')
                + "  0x075B: 0x70 -> ... (last 0x71)\n")
        err = self._refused(text, 'comes before the + 5s row above it')
        self.assertIn('+ 1s', err)

    def test_a_write_address_the_grader_cannot_place(self):
        # The `===` line names `0x0750`, so the label this would open the block
        # with is one `parse_mark` reads as no action at all. The refusal is the
        # grader's own predicate, taken over the label rather than re-spelled
        # here -- a converter that rewrote the address into `0x0751` would
        # convert a log about a different byte into a capture about this one.
        # Written out rather than substituted: the `SUMMARY:` line names
        # `0x0751` in its own text whatever the block's address is, so a blanket
        # replace would refuse this on the wrong line and for the wrong reason.
        elsewhere = ("=== write 0x0750=0xA0 (hold 20s) ===\n"
                     "0x0750 currently 0x10; writing 0xA0, holding 20s\n"
                     "    + 0.0s  0x0750: 0x10 -> 0xA0\n"
                     "restored 0x0750 -> 0x10\n"
                     + convert.SUMMARY_HEAD + "\n"
                     "  0x0750: 0x10 -> ... (last 0xA0)\n")
        self._refused(GOOD_HEADER + elsewhere,
                      "would open or close with 'wrote 0x0750=0xA0'")

    def test_a_block_with_no_summary_to_check_its_rows_against(self):
        text = GOOD_HEADER + GOOD_BLOCK.replace(
            'SUMMARY: addresses that moved while only 0x0751 was written:\n'
            '  0x0751: 0x10 -> ... (last 0xA0)\n', '')
        self._refused(text, convert.SUMMARY_HEAD, 'cannot be checked')

    def test_an_anchor_and_a_gap_that_fold_two_marks_into_one_window(self):
        # The refusal the two choices exist to make checkable: a gap narrower
        # than the source's own 20 s hold puts the next block's write at or
        # after this block's restore, and `coalesce_marks` would file them as
        # one action -- a day the block walk would then report as having run.
        text = GOOD_HEADER + GOOD_BLOCK + "\n" + GOOD_BLOCK
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'log.txt'
            path.write_text(text, encoding="utf-8")
            rc, stdout, err, written = convert_to(str(path),
                                                  str(Path(tmp) / 'out.csv'),
                                                  gap=22)
        self.assertEqual(rc, 1, f"not refused; stdout was {stdout!r}")
        self.assertEqual(written, b'')
        self.assertIn('MARK_MERGE_SECONDS', err)
        self.assertIn('--block-gap', err)

    def test_a_hold_that_is_not_a_number_of_seconds(self):
        # The same shape the offset has and the block's own line does not: the
        # regex takes digits and dots, and `1.2.3` is neither a hold nor
        # anything else. Without `seconds` this is a `ValueError` out of the
        # parse -- a traceback over a log the operator is holding.
        text = GOOD_HEADER + GOOD_BLOCK.replace('(hold 20s)', '(hold 1.2.3s)')
        self._refused(text, "'1.2.3' is not a number of seconds")

    def test_a_path_that_is_not_there(self):
        # The input error an operator makes most, and the one a traceback over
        # is least acceptable for.
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, err, written = convert_to(
                str(Path(tmp) / 'absent.txt'), str(Path(tmp) / 'out.csv'))
        self.assertEqual(rc, 1)
        self.assertIn('cannot be read', err)
        self.assertEqual(written, b'')

    def test_an_anchor_this_cannot_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, err, _ = convert_to(LOG, str(Path(tmp) / 'out.csv'),
                                       anchor='2026-01-01 noon')
        self.assertEqual(rc, 1)
        self.assertIn('--anchor', err)


class SelfTestModeTests(unittest.TestCase):
    """`--self-test`, driven through its `run` seam rather than launched.

    A case that ran the mode for real would have the mode run this suite, which
    contains the case, which runs the mode. What a reader at the box runs is
    `python3 ec/tools/probe_log_to_capture.py --self-test`, and this file is
    not that.
    """

    def test_it_returns_the_subprocess_exit_code_and_says_it_passed(self):
        class Ok:
            returncode, stdout = 0, "Ran 7 tests in 0.001s\n\nOK\n"

        class Failed:
            returncode, stdout = 1, "FAILED (failures=1)\n"

        class Empty:
            # A discovery that matched nothing exits 0 and prints OK, which
            # from the outside is indistinguishable from a suite that passed.
            returncode, stdout = 0, "Ran 0 tests in 0.000s\n\nOK\n"

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(convert.self_test(run=lambda cmd, **kw: Ok()), 0)
            self.assertEqual(convert.self_test(run=lambda cmd, **kw: Failed()), 1)
            self.assertEqual(convert.self_test(run=lambda cmd, **kw: Empty()), 1)
        self.assertIn('passed', out.getvalue())
        self.assertIn('no test ran, which is not a pass', out.getvalue())


if __name__ == "__main__":
    unittest.main()