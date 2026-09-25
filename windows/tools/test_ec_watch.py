#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

ec_watch.py imports ecrw, which binds kernel32 at import time and so only
loads on Windows -- ecrw_fake.py stands in for the whole module, and the
FakeEc below scripts the sweep byte by byte on top of it.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import ecrw_fake

ADDRS = [0x0700, 0x0701, 0x0702, 0x0703]

# Sweep 0 is the baseline ec_watch takes before its loop; 1 and 2 each move a
# different byte, and the mark is forced to land between them.
SWEEPS = [
    {0x0700: 0x00, 0x0701: 0x00, 0x0702: 0x00, 0x0703: 0x00},
    {0x0700: 0x00, 0x0701: 0x11, 0x0702: 0x00, 0x0703: 0x00},
    {0x0700: 0x00, 0x0701: 0x11, 0x0702: 0x22, 0x0703: 0x00},
]


class FakeEc:
    """Returns SWEEPS[n] for sweep n, and stops the run after the last one.

    The two events pin the interleaving: without them "did the MARK row land
    between the two change rows" would be a race against the sweep timer, and
    the test would pass on a build where marks never reach the CSV at all.

    `readmany` is the --block path's, and it is a whole sweep rather than four
    bytes: ADDRS is one aligned block, so a real readmany of it is exactly one
    IOCTL and this stands in for that. `blocks` is the recording that makes
    "one IOCTL per sweep" checkable rather than asserted.
    """

    def __init__(self):
        self.at_last_sweep = threading.Event()
        self.marked = threading.Event()
        self.blocks = []
        self._reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read(self, addr):
        sweep, offset = divmod(self._reads, len(ADDRS))
        if sweep == len(SWEEPS) - 1 and offset == 0:
            self.at_last_sweep.set()
            self.marked.wait(5)
        if sweep >= len(SWEEPS):
            raise KeyboardInterrupt
        self._reads += 1
        # The .get is for the --block cases' ranges, which are not ADDRS: an
        # address the script does not name reads as 0x00 rather than raising,
        # so a case can put its range on the fan-tach page and still run.
        return SWEEPS[sweep].get(addr, 0x00)

    def readmany(self, start, length):
        self.blocks.append((start, length))
        return {addr: self.read(addr) for addr in range(start, start + length)}


class FakeStdin:
    """The lines the marker thread reads, in order, once the last sweep starts.

    The read after the list is exhausted is the proof the last mark is fully
    committed -- Marker only asks for another line after writing the previous
    one -- so that is where the sweep loop is released.

    A bare string is the one-mark case, so the callers that stamp a single
    label do not have to wrap it. A list is what a re-prompt needs: a blank
    line the marker refuses comes back here as the *next* line rather than as
    the end of the stream, because the thread is still reading.
    """

    def __init__(self, ec, lines):
        self._ec = ec
        self._lines = [lines] if isinstance(lines, str) else list(lines)
        self._next = 0

    def readline(self):
        self._ec.at_last_sweep.wait(5)
        if self._next < len(self._lines):
            line = self._lines[self._next]
            self._next += 1
            return line
        self._ec.marked.set()
        return ""


ecrw_fake.install()

spec = importlib.util.spec_from_file_location(
    'ec_watch', Path(__file__).with_name('ec_watch.py'))
ec_watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ec_watch)

# The grader --label-vocab 0751 loads, loaded the same way here so the cases
# below can ask it rather than spell its answer out a second time.
grader_path = Path(__file__).resolve().parents[2] / 'ec/tools' \
    / 'grade_0751_isolation.py'
grader_spec = importlib.util.spec_from_file_location('grade_0751_isolation',
                                                     grader_path)
grader = importlib.util.module_from_spec(grader_spec)
grader_spec.loader.exec_module(grader)


class MarkCsvTests(unittest.TestCase):
    def run_watch(self, *extra):
        ec = FakeEc()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            text = io.StringIO()
            with patch.object(ec_watch, 'Ec', lambda: ec), \
                 patch.object(ec_watch.sys, 'stdin', FakeStdin(ec, 'wrote 0x0751=0xA0')), \
                 contextlib.redirect_stdout(text):
                rc = ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                    '--interval', '0', '--csv', str(out),
                                    *extra])
            return rc, out.read_text().splitlines(), text.getvalue()

    def test_mark_lands_in_the_csv_between_the_change_rows(self):
        rc, rows, _ = self.run_watch('--mark')
        self.assertEqual(rc, 0)
        self.assertEqual(rows[0], 'ts,addr,old,new')
        self.assertEqual([r.split(',', 1)[1] for r in rows[1:]],
                         ['0x0701,0x00,0x11',
                          'MARK,,wrote 0x0751=0xA0',
                          '0x0702,0x00,0x22'])

    def test_mark_row_parses_as_the_grader_expects(self):
        _, rows, _ = self.run_watch('--mark')
        mark = [r for r in rows if ',MARK,' in r][0]
        ts, addr, old, label = mark.split(',')
        self.assertEqual((addr, old, label), ('MARK', '', 'wrote 0x0751=0xA0'))
        # The grader keys every window off this timestamp.
        self.assertTrue(ts.startswith('20'))

    def test_without_mark_the_csv_holds_changes_only(self):
        ec = FakeEc()
        ec.marked.set()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            with patch.object(ec_watch, 'Ec', lambda: ec), \
                 contextlib.redirect_stdout(io.StringIO()):
                ec_watch.main(['--start', '0x0700', '--len', '0x4',
                               '--interval', '0', '--csv', str(out)])
            rows = out.read_text().splitlines()
        self.assertEqual([r.split(',', 1)[1] for r in rows[1:]],
                         ['0x0701,0x00,0x11', '0x0702,0x00,0x22'])


def marks_summary(text):
    """The lines under the run's own `marks:` count, one per mark it took.

    The block ends at the blank line the next section's leading newline
    prints, which is what keeps the indented `quiet` and `busy` rows that
    follow it out of the count.
    """
    out = []
    for line in text.split('\nmarks:\n', 1)[1].splitlines():
        if not line:
            break
        out.append(line)
    return out


class BlankMarkTests(unittest.TestCase):
    """A blank press is not a mark, and the tool says so rather than naming it.

    The prompt used to substitute `mark N` for an empty label, which wrote a
    `ts,MARK,,mark N` row that `grade_0751_isolation.py`'s `parse_mark` cannot
    read -- and one unreadable mark is fatal for the whole run rather than for
    one block, because block attribution rests entirely on the labels
    (`unplaceable_marks`). The substitution also read as a deliberate mark
    rather than as a missing one, which is the half nobody could see at the
    console. Pinned here so the shape cannot return as a `strip() or` default.
    """

    def run_watch(self, lines):
        ec = FakeEc()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            text = io.StringIO()
            with patch.object(ec_watch, 'Ec', lambda: ec), \
                 patch.object(ec_watch.sys, 'stdin', FakeStdin(ec, lines)), \
                 contextlib.redirect_stdout(text):
                rc = ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                    '--interval', '0', '--csv', str(out),
                                    '--mark'])
            return rc, out.read_text().splitlines(), text.getvalue()

    def test_a_blank_press_writes_no_row_and_leaves_the_real_mark_alone(self):
        rc, rows, _ = self.run_watch(['\n', 'wrote 0x0751=0xA0\n'])
        self.assertEqual(rc, 0)
        self.assertEqual([r.split(',', 1)[1] for r in rows[1:]],
                         ['0x0701,0x00,0x11',
                          'MARK,,wrote 0x0751=0xA0',
                          '0x0702,0x00,0x22'])
        # The whole capture rather than the row counted above: the shape the
        # grader refuses is a substituted mark anywhere in the file, and the
        # grade is a property of the file rather than of where the mark fell.
        self.assertNotIn(',MARK,,mark', '\n'.join(rows))

    def test_the_console_says_the_press_was_not_recorded(self):
        _, _, text = self.run_watch(['\n', 'wrote 0x0751=0xA0\n'])
        # 'nothing recorded' rather than 'blank line': the banner says a blank
        # line records nothing, and that sentence is not the notice.
        notices = [ln for ln in text.splitlines() if 'nothing recorded' in ln]
        self.assertEqual(len(notices), 1)
        # Not framed as a mark: a notice that reads like one is the same
        # confusion the refusal exists to remove.
        self.assertNotIn('MARK:', notices[0])
        # And the run's own count agrees with the file -- the one mark, and no
        # substitute standing in for the press.
        summary = marks_summary(text)
        self.assertEqual(len(summary), 1)
        self.assertIn('wrote 0x0751=0xA0', summary[0])
        self.assertNotIn('mark ', summary[0])

    def test_a_whitespace_only_press_is_the_same_as_an_empty_one(self):
        rc, rows, _ = self.run_watch(['   \n', 'wrote 0x0751=0xA0\n'])
        self.assertEqual(rc, 0)
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r],
                         ['wrote 0x0751=0xA0'])

    def test_a_padded_real_label_is_still_taken_and_stripped(self):
        # The other half of the guard: refuse the blank press, not the
        # whitespace. A label typed with a stray leading space is a label.
        rc, rows, text = self.run_watch(['  wrote 0x0751=0xA0  \n'])
        self.assertEqual(rc, 0)
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r],
                         ['wrote 0x0751=0xA0'])
        self.assertNotIn('nothing recorded', text)

    def test_a_rejected_press_does_not_take_a_mark_number(self):
        _, rows, text = self.run_watch(['\n', 'wrote 0x0751=0xA0\n', '\n'])
        # Each notice names the number the press would have taken, and `_n`
        # counts marks recorded: the first blank would have been mark 1 and
        # was not, so the typed mark took 1 and the second blank would have
        # been mark 2. Without the counter held back the first notice would
        # have read "mark 2" and the capture would hold a `mark 2` row.
        self.assertEqual(text.count('nothing recorded, no mark 1 taken'), 1)
        self.assertEqual(text.count('nothing recorded, no mark 2 taken'), 1)
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r],
                         ['wrote 0x0751=0xA0'])


class Refusal(Exception):
    """What `load_label_vocab` refused with, for the cases that call it
    directly rather than through `main`'s parser."""


class RefusingParser:
    """The one method `load_label_vocab` calls on the `ap` it is handed.

    `main` hands it argparse's own, whose `error` exits the process; the
    lookup cases below are about the message and the file it names, so this
    raises it and they read it back.
    """

    def error(self, message):
        raise Refusal(message)


class RefusedLabelTests(unittest.TestCase):
    """--label-vocab 0751: a label the grader cannot place is refused here.

    A *described* mark whose description is wrong is the other half of what
    the blank press above is: there, the operator typed nothing; here they
    typed something the 0751 grader cannot read, which `unplaceable_marks`
    treats as fatal for the whole run rather than for one block (#502). The
    prompt already had a refusal of this shape, so this is a second argument
    to the same one -- at the point where the correction is nearly free,
    rather than at the grading after a day's hardware time.

    The promise is bounded and these cases hold it to that: the label is
    refused when the grader's own `parse_mark` returns no role for it, and
    nothing more. A label that parses but names the wrong value is recorded,
    because a per-line prompt cannot know which values the run means to write
    or what its actions should be; the three-console comparison is what catches
    that one.
    """

    VOCAB = ('--label-vocab', '0751')

    # A form the committed grader has not got, so an assertion that saw this
    # string says which file the lookup loaded rather than only that some
    # grader loaded. The stub refuses every label, so the notice quotes its own
    # forms whatever the operator typed.
    STAGED_FORM = 'staged by a test'

    def run_watch(self, lines, *extra):
        ec = FakeEc()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            text = io.StringIO()
            with patch.object(ec_watch, 'Ec', lambda: ec), \
                 patch.object(ec_watch.sys, 'stdin', FakeStdin(ec, lines)), \
                 contextlib.redirect_stdout(text):
                rc = ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                    '--interval', '0', '--csv', str(out),
                                    '--mark', *self.VOCAB, *extra])
            return rc, out.read_text().splitlines(), text.getvalue()

    def write_stub(self, path):
        """A file shaped like the grader, from `load_label_vocab`'s point of view.

        A stub rather than a copy of the committed grader, because the case is
        about which file the lookup reaches and not about what a grader says;
        the committed one's own behaviour is asserted above, against the
        committed one.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def parse_mark(label):\n"
                        "    return (None, None)\n"
                        f"REQUIRED_LABEL_FORMS = ({self.STAGED_FORM!r},)\n")

    def staged_tool(self, root):
        """Where `ec_watch.py` would sit in a tree shaped like a checkout.

        The two built-in candidates are derived from that one path, so a
        shallower stand-in sends the committed copy's name somewhere above the
        temporary directory rather than under it. The directory is created;
        no grader goes in it unless the case is about one being there.
        """
        tools = root / 'windows/tools'
        tools.mkdir(parents=True)
        return tools / 'ec_watch.py'

    def shallow_tool(self):
        """`ec_watch.py` two levels below a root, the depth it is staged at.

        A bare tools directory copied onto a Windows box sits where
        `C:\\tools\\ec_watch.py` does: too shallow to have a checkout two
        parents up, so `parents[2]` is off the drive and the lookup has to
        offer the beside-the-tool copy alone rather than raise IndexError.
        The path is never created -- what is under test is that the lookup
        survives the depth, and a real directory two levels below a root is
        not something a test can stage portably (and this tool is
        Windows-facing). The candidates it derives are compared after
        `resolve()`, the way `grader_candidates` reads `__file__`.
        """
        return Path('/tools/ec_watch.py')

    def test_a_refused_label_writes_no_row_and_leaves_the_real_mark_alone(self):
        # The recognised leading word with no readable value behind it: what a
        # mistyped `=`, or a value that never got typed, leaves, and the shape
        # `parse_mark` returns (None, None) for. Asserted against the grader
        # rather than assumed, so the fixture cannot drift from the rule.
        self.assertIsNone(grader.parse_mark('wrote 0x0751=')[0])
        rc, rows, _ = self.run_watch(['wrote 0x0751=\n',
                                      'wrote 0x0751=0xA0\n'])
        self.assertEqual(rc, 0)
        self.assertEqual([r.split(',', 1)[1] for r in rows[1:]],
                         ['0x0701,0x00,0x11',
                          'MARK,,wrote 0x0751=0xA0',
                          '0x0702,0x00,0x22'])
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r],
                         ['wrote 0x0751=0xA0'])

    def test_the_notice_has_the_blank_press_shape(self):
        _, rows, text = self.run_watch(['wrote 0x0751=\n',
                                        'wrote 0x0751=0xA0\n'])
        notices = [ln for ln in text.splitlines() if 'nothing recorded' in ln]
        self.assertEqual(len(notices), 1)
        self.assertIn('nothing recorded, no mark 1 taken', notices[0])
        # Not framed as a mark, for the reason BlankMarkTests gives: a notice
        # that reads like one is the same confusion the refusal exists to
        # remove.
        self.assertNotIn('MARK:', notices[0])
        # The three forms are the grader's own, so the operator fixes the
        # label from this end and from `unplaceable_marks`'s message alike.
        for form in grader.REQUIRED_LABEL_FORMS:
            self.assertIn(form, notices[0])
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r],
                         ['wrote 0x0751=0xA0'])

    def test_a_refused_label_does_not_take_a_mark_number(self):
        _, rows, text = self.run_watch(['wrote 0x0751=\n',
                                        'wrote 0x0751=0xA0\n',
                                        'wrote 0751=0xA0\n'])
        # The second refusal drops the `0x` off the address, and is unreadable
        # for the same reason as the first. A dropped hex *digit* is not: the
        # value regex takes one or two of them, so `0x0751=0xA` parses as a
        # value of its own. That is the boundary the check does not cover, and
        # the case §3's three-console comparison exists for.
        # The counting rule is the blank press's, unchanged: each notice names
        # the number that press would have taken, so the typed mark took 1 and
        # the second refusal would have been 2. This is the case that fails if
        # the refusal is written after `_n += 1` -- the first notice would then
        # read "mark 2", and the number at the console would no longer be the
        # one the next accepted mark carries.
        self.assertEqual(text.count('nothing recorded, no mark 1 taken'), 1)
        self.assertEqual(text.count('nothing recorded, no mark 2 taken'), 1)
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r],
                         ['wrote 0x0751=0xA0'])
        self.assertEqual(len(marks_summary(text)), 1)

    def test_the_check_is_opt_in(self):
        # `gpu_block_watch.py:59,166` imports this same Marker, constructs it
        # with no vocabulary, and stamps its own free-form labels, so an
        # unplaceable one is theirs to record. Pinned so the blanket check
        # cannot come back unnoticed under it.
        ec = FakeEc()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            text = io.StringIO()
            with patch.object(ec_watch, 'Ec', lambda: ec), \
                 patch.object(ec_watch.sys, 'stdin',
                              FakeStdin(ec, 'wrote 0x0751=\n')), \
                 contextlib.redirect_stdout(text):
                rc = ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                    '--interval', '0', '--csv', str(out),
                                    '--mark'])
            rows = out.read_text().splitlines()
        self.assertEqual(rc, 0)
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r],
                         ['wrote 0x0751='])
        self.assertNotIn('nothing recorded', text.getvalue())

    def test_a_vocabulary_without_mark_is_refused_before_anything_opens(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as caught:
                    ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                   '--interval', '0', '--csv', str(out),
                                   *self.VOCAB])
            # The CSV is named on the command line and was never created, so
            # the refusal is above the file rather than after it -- and no EC
            # was opened either, which is the other half of "at startup".
            self.assertNotEqual(caught.exception.code, 0)
            self.assertFalse(out.exists())
        self.assertIn('--label-vocab needs --mark', err.getvalue())

    def test_an_unknown_vocabulary_is_refused_by_choices(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as caught:
                ec_watch.main(['--mark', '--label-vocab', '0752'])
        self.assertNotEqual(caught.exception.code, 0)
        self.assertIn('0752', err.getvalue())

    def test_a_grader_in_neither_place_is_refused_before_anything_opens(self):
        # The case that decides whether §3's three commands start at all: a
        # directory of tools staged onto a Windows box, with no grader in it
        # and no checkout above it. The refusal has to name every place it
        # looked, because the two ways out of it -- a copy beside the tool, or
        # a checkout -- are not something an operator can be expected to guess
        # from a path they have no way to create.
        with tempfile.TemporaryDirectory() as tmp:
            tool = self.staged_tool(Path(tmp))
            out = Path(tmp) / 'capture.csv'
            err = io.StringIO()
            with patch.object(ec_watch, '__file__', str(tool)), \
                 contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as caught:
                    ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                   '--interval', '0', '--csv', str(out),
                                   '--mark', *self.VOCAB])
            message = err.getvalue()
            self.assertNotEqual(caught.exception.code, 0)
            self.assertFalse(out.exists())
            # Both built-in candidates, named whether or not either exists --
            # this is the sentence the operator reads at the machine.
            for candidate in (Path(tmp) / 'ec/tools/grade_0751_isolation.py',
                              tool.with_name('grade_0751_isolation.py')):
                self.assertIn(str(candidate), message)
                self.assertFalse(candidate.is_file())
        self.assertIn('beside ec_watch.py', message)
        self.assertIn('checkout', message)

    def test_a_grader_beside_the_tool_is_found(self):
        # The staged-directory case, and the reason the lookup is a list rather
        # than one path: `ec_watch.py` and the grader in the same directory,
        # with no grader at the committed copy's place above them.
        with tempfile.TemporaryDirectory() as tmp:
            tool = self.staged_tool(Path(tmp))
            self.write_stub(tool.with_name('grade_0751_isolation.py'))
            with patch.object(ec_watch, '__file__', str(tool)):
                rc, rows, text = self.run_watch(['wrote 0x0751=0xA0\n'])
        self.assertEqual(rc, 0)
        notices = [ln for ln in text.splitlines() if 'nothing recorded' in ln]
        self.assertEqual(len(notices), 1)
        # The staged file's own form, which the committed grader does not have:
        # this is what says the lookup loaded the file beside the tool.
        self.assertIn(self.STAGED_FORM, notices[0])
        # And the check it brought is in force -- the stub refuses everything,
        # so a mark that would have been taken under the committed grader's
        # rule is not taken here.
        self.assertEqual([r.split(',')[3] for r in rows if ',MARK,' in r], [])

    def test_the_grader_flag_is_the_only_place_looked(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = self.staged_tool(Path(tmp))
            staged = tool.with_name('elsewhere.py')
            self.write_stub(staged)
            # Neither built-in candidate exists in this tree, so the flag is
            # the only thing that can answer.
            with patch.object(ec_watch, '__file__', str(tool)):
                _, forms = ec_watch.load_label_vocab(RefusingParser(), '0751',
                                                     str(staged))
        self.assertEqual(list(forms), [self.STAGED_FORM])

    def test_a_grader_that_is_present_and_broken_is_refused_not_skipped(self):
        # The candidate order is only safe if a file that is there and broken
        # stops the search. A staged copy quietly standing in for a committed
        # grader broken since the checkout was made is a capture graded
        # against a rule the tree does not hold, and the operator finds out at
        # the grading rather than at the watcher.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            broken = root / 'ec/tools/grade_0751_isolation.py'
            broken.parent.mkdir(parents=True)
            broken.write_text("REQUIRED_LABEL_FORMS = (\n")     # SyntaxError
            tool = self.staged_tool(root)
            self.write_stub(tool.with_name('grade_0751_isolation.py'))
            with patch.object(ec_watch, '__file__', str(tool)):
                with self.assertRaises(Refusal) as caught:
                    ec_watch.load_label_vocab(RefusingParser(), '0751')
        self.assertIn(str(broken), str(caught.exception))
        # And the loadable candidate behind it never got a say: this refused
        # rather than returning the staged form.
        self.assertNotIn(self.STAGED_FORM, str(caught.exception))

    def test_the_grader_flag_does_not_fall_back_to_the_checkout(self):
        # The flag is the only candidate by design, and this is the case that
        # says so. The committed grader is right there and loads -- every other
        # case in this class is graded by it -- and a run that named a
        # different file is not allowed to end up using it instead, whether
        # the file it named is broken or is not there. Either way an operator
        # who named a grader and got a different one was never told.
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / 'grader.py'
            broken.write_text("REQUIRED_LABEL_FORMS = (\n")     # SyntaxError
            absent = Path(tmp) / 'not-staged.py'
            for named in (broken, absent):
                with self.subTest(named=named):
                    with self.assertRaises(Refusal) as caught:
                        ec_watch.load_label_vocab(RefusingParser(), '0751',
                                                 str(named))
                    self.assertIn(str(named), str(caught.exception))

    def test_a_tool_two_levels_down_offers_the_grader_beside_it_and_no_checkout(self):
        # Candidate 3 is the feature, and at the depths a staged tools
        # directory actually meets it was unreachable: `grader_candidates`
        # indexed `parents[2]` and raised before the beside-the-tool copy --
        # the one candidate those runs have -- was ever offered. A path that
        # cannot be named is not a place a checkout can be, so at this depth
        # the beside-the-tool copy is offered alone, and that it is offered is
        # what `test_a_grader_beside_the_tool_is_found` then loads.
        with patch.object(ec_watch, '__file__', str(self.shallow_tool())):
            candidates = ec_watch.grader_candidates()
        self.assertEqual(
            candidates,
            [self.shallow_tool().resolve()
             .with_name('grade_0751_isolation.py')])

    def test_a_tool_two_levels_down_with_nothing_beside_it_is_refused_by_name(self):
        # No IndexError, and a refusal that names the one place it looked
        # rather than a traceback. Through main(), so the whole startup path
        # is what refuses.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            err = io.StringIO()
            with patch.object(ec_watch, '__file__', str(self.shallow_tool())), \
                 contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as caught:
                    ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                   '--interval', '0', '--csv', str(out),
                                   '--mark', *self.VOCAB])
            message = err.getvalue()
        self.assertNotEqual(caught.exception.code, 0)
        # The beside-the-tool copy is the only place looked at that depth, and
        # it is named whether or not it is there -- here it is not.
        beside = self.shallow_tool().resolve() \
            .with_name('grade_0751_isolation.py')
        self.assertIn(str(beside), message)

    def test_a_grader_that_is_there_and_will_not_load_is_refused_by_name(self):
        # A `--grader` path to a file importlib has no loader for (.txt and
        # friends) is there but unusable, and `module_from_spec(None)` is an
        # AttributeError traceback that names nothing an operator can act on.
        # New surface, because `--grader` is this PR's own flag and takes a
        # path the operator typed. The refusal has to be the documented one:
        # that path, by name.
        with tempfile.TemporaryDirectory() as tmp:
            notes = Path(tmp) / 'notes.txt'
            notes.write_text('these are not a grader\n')
            with self.assertRaises(Refusal) as caught:
                ec_watch.load_label_vocab(RefusingParser(), '0751', str(notes))
        message = str(caught.exception)
        self.assertIn(str(notes), message)
        self.assertIn('will not load', message)

    def test_a_grader_that_raises_at_load_is_refused_by_name(self):
        # The same refusal for a module that is importable but blows up while
        # it runs. The caught set is any load failure, so a RuntimeError at
        # module level is reported against the path rather than raised.
        with tempfile.TemporaryDirectory() as tmp:
            boom = Path(tmp) / 'boom.py'
            boom.write_text("raise RuntimeError('boom')\n")
            with self.assertRaises(Refusal) as caught:
                ec_watch.load_label_vocab(RefusingParser(), '0751', str(boom))
        message = str(caught.exception)
        self.assertIn(str(boom), message)
        self.assertIn('will not load', message)

    def test_the_grader_flag_needs_a_vocabulary(self):
        # It is a modifier of --label-vocab, so a grader path beside a run that
        # reads no vocabulary changes nothing while reading as a setting.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as caught:
                    ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                   '--interval', '0', '--csv', str(out),
                                   '--mark', '--grader', 'grader.py'])
            self.assertNotEqual(caught.exception.code, 0)
            self.assertFalse(out.exists())
        self.assertIn('--grader needs --label-vocab', err.getvalue())


class BlockPathTests(unittest.TestCase):
    """--block: opt-in, off the per-byte path, and loud about the fan-tach page.

    Every case here runs the real `ec_watch.main` against the FakeEc above, so
    what is under test is which method the tool calls, not a reimplementation
    of the decision.
    """

    def run_watch(self, *argv):
        ec = FakeEc()
        ec.marked.set()
        out = io.StringIO()
        with patch.object(ec_watch, 'Ec', lambda: ec), \
             contextlib.redirect_stdout(out):
            rc = ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                '--interval', '0', *argv])
        return rc, ec, out.getvalue()

    def test_the_flag_is_opt_in(self):
        # The default has to be the per-byte path: this is what says the block
        # path is an addition rather than a replacement, and it is the run the
        # committed captures were taken with.
        _, ec, out = self.run_watch()
        self.assertEqual(ec.blocks, [])
        self.assertNotIn("--block:", out)

    def test_block_sweeps_through_readmany(self):
        rc, ec, _ = self.run_watch('--block')
        self.assertEqual(rc, 0)
        # The whole four-byte range in one call. The first is the baseline and
        # the last is the sweep the fake cuts the run off in, so the run's
        # length stays the fake's business and not this case's.
        self.assertEqual(set(ec.blocks), {(0x0700, 0x4)})
        self.assertEqual(ec.blocks[0], (0x0700, 0x4))

    def test_the_banner_says_which_path_and_that_it_is_unverified(self):
        _, ec, out = self.run_watch('--block')
        # The operator is being asked to trust a path that has never met the
        # driver, so the banner has to say that where it is read rather than
        # leaving it to a help page nobody opens.
        self.assertIn("4 bytes per IOCTL (MMRD) instead of 1 (ECRR)", out)
        self.assertIn("never been run against the driver", out)
        self.assertIn("not a safety improvement", out)
        # And the sweep behind it is still the one IOCTL for four bytes.
        self.assertEqual(set(ec.blocks), {(0x0700, 0x4)})

    def test_a_block_sweep_reports_the_same_changes(self):
        _, ec, out = self.run_watch('--block')
        self.assertIn("0x0701: 0x00 -> 0x11", out)
        self.assertIn("0x0702: 0x00 -> 0x22", out)

    def test_the_fan_tach_warning_names_the_issue_and_the_page(self):
        # 0x0460-0x046F stalled the fans on a sibling board through ECRR
        # (#94). A 4-byte read that covers the page is a different access
        # shape, not a smaller one, so the warning has to say so rather than
        # let "fewer IOCTLs" read as "safer".
        ec = FakeEc()
        ec.marked.set()
        out = io.StringIO()
        with patch.object(ec_watch, 'Ec', lambda: ec), \
             contextlib.redirect_stdout(out):
            ec_watch.main(['--start', '0x0460', '--len', '0x4',
                           '--interval', '0', '--block'])
        text = out.getvalue()
        self.assertIn("0x0460-0x046F", text)
        self.assertIn("#94", text)
        self.assertIn("not a safer one", text)
        # No refusal: the run happened, and the warning did not stop it.
        self.assertEqual(set(ec.blocks), {(0x0460, 0x4)})

    def test_a_range_off_the_page_is_not_warned_about(self):
        _, ec, out = self.run_watch('--block')
        self.assertNotIn("#94", out)
        self.assertNotIn("0x0460-0x046F", out)

    def test_the_default_range_contains_the_page_so_the_warning_is_the_point(self):
        # 0x0000-0x07FF is this tool's default, and 0x0460-0x046F is inside it.
        # Pinned because the warning is otherwise easy to "fix" by narrowing a
        # default nobody asked to narrow.
        self.assertTrue(set(range(0x0000, 0x0800)) & set(ec_watch.FAN_TACH))


if __name__ == '__main__':
    unittest.main()
