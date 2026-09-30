#!/usr/bin/env python3
"""The claims in `docs/findings/perturb-arm-colliding-marks.md`, against the
capture it is about.

One committed CSV, three committed graders, and no constructed fixture: the
instance is a file a human took at the machine, so a hand-built capture would
be testing a shape rather than the instance. Nothing here opens an EC, and
nothing writes -- the one subprocess runs `grade_gpu_door.py` over a committed
file and reads what it prints.

**Every assertion is on the instance or the shape, never on a census.** The
population (how many captures in the tree carry a colliding pair), the mark
count and the row count move with every capture a human takes and commits, so
a test that pinned any of them would be a value every landing capture has to
edit -- `ec/tools/check_pin_table_by_cited_file.py`'s lesson. What is stable is
the *file*: it is committed, so which pair it holds, which addresses moved in
it, and what its header says are all facts about this tree. That split is the
reason the write-up quotes its counts from the tool's output and the tests
quote the instance from the file.

The graders are imported rather than re-implemented for the same reason
`scan_mark_collisions.py` imports them: a second copy of "what is a collision"
could disagree with the refusal it is describing, and then the suite would be
green over a shape the door grader does not refuse.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import re
import subprocess
import sys
import unittest

HERE = Path(__file__).parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "ec" / "tools"))

import grade_0751_isolation as fan
import grade_gpu_door as door
import grade_timer_sweep as sweep

spec = importlib.util.spec_from_file_location(
    'scan_collisions', HERE / 'scan_mark_collisions.py')
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

# The one capture in the tree carrying a colliding pair, and the one the two
# documents under test draw their Fn-arm sentence from. Its four actions are
# §4a's of `docs/hardware-tests/xdata-06c2-06db-sweep.md`; its six marks are
# the instance.
CAPTURE = REPO / "evidence" / "ec-watch" / "2026-09-24-06c2-06db-perturb-linux.csv"

# The pair, by label. Both labels, because a test that named only the instant
# would pass on any pair at that instant -- and the labels are the half that
# tells a reader which press this was (`0xb0` is the scan code `uniwill_laptop`
# delivers as `KEY_F14`).
SCAN_LABEL = "auto: event7 scan 0xb0"
KEY_LABEL = "auto: event7 key 184 pressed"

# The instant they share, as the parser hands it back. Spelled with the
# microseconds `fromisoformat` produces, because that is what the grader prints
# and what a reader comparing two outputs is comparing.
INSTANT = "2026-09-24T21:21:11.447000+02:00"

# The fan-mode byte the Fn arm's negative is about.
FAN_MODE = 0x0751


def marks_of(path=CAPTURE):
    marks, _ = fan.read_capture(str(path))
    return sorted(marks, key=lambda w: w.ts)


def changes_of(path=CAPTURE):
    _, changes = fan.read_capture(str(path))
    return changes


class InstanceTests(unittest.TestCase):
    """The pair is in the committed file, and it is the pair the issue names."""

    def test_the_capture_holds_exactly_one_colliding_pair(self):
        pairs = door.collided_marks(marks_of())
        self.assertEqual(len(pairs), 1,
                         "the write-up claims the file holds one colliding "
                         "pair and no more")
        a, b = pairs[0]
        # The labels, in the order the two MARK rows are written: the MSC_SCAN
        # arrives before the EV_KEY, so `0xb0` is the first of the two.
        self.assertEqual(a.label, SCAN_LABEL)
        self.assertEqual(b.label, KEY_LABEL)
        # And the instant, which is the whole claim -- equality and nothing
        # else, on the parsed datetime rather than the string.
        self.assertEqual(a.ts.isoformat(), INSTANT)
        self.assertEqual(b.ts.isoformat(), INSTANT)

    def test_the_refusal_fires_on_the_committed_capture(self):
        """The instance is a real one, not a reading of the tool that found it.

        Run as a subprocess rather than through `door.main`, because the claim
        is about the *program* exiting 1: a direct call proves the function
        agrees with itself, and the operator meets the process.
        """
        proc = subprocess.run(
            [sys.executable, str(HERE / "grade_gpu_door.py"), str(CAPTURE)],
            capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 1)
        # Both labels and the instant they share, so the failure names the pair
        # rather than reporting only that one exists.
        self.assertIn(f"marks {SCAN_LABEL!r} and {KEY_LABEL!r} are both "
                      f"{INSTANT}", proc.stderr)
        # Refused before any window is built, so there is no report over a
        # zero-length window to be half-right.
        self.assertNotIn("window(s), one per mark", proc.stdout)


class WholeCaptureTests(unittest.TestCase):
    """'0x0751 held 0x10' read over every interval the capture has.

    The Fn arm's negative is stated without an interval, and the collision is
    what makes the interval ambiguous: under one mark per action the window is
    `[t, t)`, and a negative over no time is true by construction. What makes
    the sentence sound anyway is that this byte has no change row anywhere in
    the file -- so the negative does not depend on where a boundary was drawn,
    and that is a property of the capture rather than of a reading of it.
    """

    def test_the_fan_mode_byte_has_no_change_row_anywhere(self):
        hits = [c for c in changes_of() if c.addr == FAN_MODE]
        self.assertEqual(hits, [],
                         "a change row for 0x0751 would make the whole-capture "
                         "reading false and the two documents' wording wrong")

    def test_the_baseline_line_carries_the_value_the_documents_cite(self):
        """Read through the timer grader's own parse, not off a comment.

        `grade_timer_sweep.load` is what grades the sweep, so the `0x0751=0x10`
        here is that grader's reading of the header rather than a regex written
        a second time. And the address is in the watched set, so the baseline
        is a value for a byte this capture was watching -- which is what makes
        "held" a claim about a watched byte at all.
        """
        watched, baseline, _, _, _ = sweep.load([str(CAPTURE)])
        self.assertIn(FAN_MODE, watched)
        self.assertEqual(baseline[FAN_MODE], 0x10)

    def test_absence_is_reported_as_absence_of_rows_not_as_inertness(self):
        """The tool's own line for the byte says what the zero means.

        A count of zero in a change-row capture is "no transition recorded",
        never "absent" or "inert": the file records transitions, not values, so
        a byte that moved and came back between two of the watcher's sweeps
        reads as quiet. `docs/findings.md` §4c retracted a claim built on a
        zero-reference scan, and the write-up under test keeps that distinction
        in front of the figure rather than after it.

        The forbidden words are checked on the per-address *verdicts* and not on
        the whole output, because the banner's whole job is to name them: a
        rule that reddened on a document saying "never `inert`" is a rule that
        gets deleted, which is why `check_no_append_logs.py` strips inline code
        spans before it looks. What must not happen is a verdict reading like
        one of them.
        """
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            scan.report_capture(str(CAPTURE))
        text = " ".join(out.getvalue().split())
        self.assertIn(f"0x{FAN_MODE:04X} baseline 0x10 0 change row(s) "
                      "no change row in the whole capture", text)
        # The banner that forbids the three words is present, and the verdicts
        # -- the lines that open with an address -- are checked without it.
        self.assertIn("never 'absent' and never 'inert'", text)
        verdicts = [ln for ln in out.getvalue().splitlines()
                    if re.match(r'\s+0x[0-9A-F]{4}\s+baseline', ln)]
        self.assertTrue(verdicts, "the per-address census is what this reads")
        for line in verdicts:
            for word in ('inert', 'unreferenced', 'unused', 'absent'):
                self.assertNotIn(word, line,
                                 f"a verdict states a zero as something other "
                                 f"than a row count: {line.strip()}")


class WindowTests(unittest.TestCase):
    """The other reading: the interval the door grader would have graded."""

    def setUp(self):
        self.marks = marks_of()
        self.changes = changes_of()
        b = door.collided_marks(self.marks)[0][1]
        end = self.marks[self.marks.index(b) + 1]
        self.end = end
        self.inside = sorted((c for c in self.changes if b.ts < c.ts < end.ts),
                             key=lambda c: c.ts)

    def test_the_window_is_the_52_second_run_to_the_next_mark(self):
        # The interval itself, as a fact about the file rather than as a count:
        # the next mark is the lid, and the pair-to-lid distance is the one
        # §4a's pacing produces.
        self.assertEqual(self.end.label, "auto: lid LID1 open -> closed")
        gap = (self.end.ts - self.marks[3].ts).total_seconds()
        self.assertAlmostEqual(gap, 52.272, places=3)

    def test_every_row_in_that_window_is_the_sweep_counter(self):
        """Asserted as *every*, not as a count of the rows.

        The write-up quotes 525; this says what the 525 are, which is the
        claim. A count would go red the moment a human committed a capture of
        a different length, and would be the wrong thing to hold.
        """
        self.assertTrue(self.inside, "the window is not empty, so the "
                        "'only the sweep moved' sentence needs rows")
        self.assertEqual({c.addr for c in self.inside}, {0x06D6})


class TimerGraderTests(unittest.TestCase):
    """`grade_timer_sweep.py` is untouched by the collision, and says so.

    The two colliding labels are read by that grader's `load()` and neither
    contains `"resumed"`, so `RESUMES` and `GAPS` come back empty and every
    figure the perturbation arm drew from the sweep -- the 1000 ms decrement
    interval, the 10.00x post-return ratio -- is computed off `rows`, which
    the collision does not touch. Stated here so a later reader who finds the
    pair in the file does not go looking for a broken grader.
    """

    def setUp(self):
        self.rc, out, _ = run_timer(str(CAPTURE))
        self.out = " ".join(out.split())

    def test_the_sweep_reads_no_resume_and_finds_no_gap(self):
        self.assertEqual(self.rc, 0)
        self.assertEqual(sweep.RESUMES, [])
        self.assertEqual(sweep.GAPS, [])

    def test_the_sweep_figures_come_out_unchanged(self):
        # The two the write-up names, as the ratio the grader prints it: 10.00
        # is the code's prediction measured, and it is the figure a reader
        # would check if they suspected the collision had disturbed the run.
        self.assertIn("step interval (= one pass of 0x8001): median 100.0 ms",
                      self.out)
        self.assertIn("period / step = 10.00", self.out)


def run_timer(path):
    """(rc, stdout, stderr) from `grade_timer_sweep.main`, captured."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = sweep.main([path])
    return rc, out.getvalue(), err.getvalue()


class CorpusTests(unittest.TestCase):
    """The corpus walk finds the instance among the committed captures.

    Not a count of them: `marked_captures` is a population that grows with
    every capture a human takes, so what is held is that the walk reaches the
    file the instance is in and that the walk's own prefilter does not hide
    it. A scan that quietly missed every capture would be green on an empty
    result, and that is the failure worth a test.
    """

    def test_the_walk_finds_the_capture_and_the_pair_in_it(self):
        found = {scan.repo_path(p) for p in scan.marked_captures()}
        self.assertIn(scan.repo_path(str(CAPTURE)), found)
        # And the pair is reachable through the walk's own reader and the
        # grader's own comparison, not only through a hand-passed path.
        marks, _ = scan.load_capture(str(CAPTURE))
        pairs = door.collided_marks(marks)
        self.assertEqual([(a.label, b.label) for a, b in pairs],
                         [(SCAN_LABEL, KEY_LABEL)])

    def test_a_capture_that_refuses_is_named_rather_than_dropped(self):
        """A read failure is a fact about a file, not a reason to skip it.

        The corpus form carries an unreadable file's reason into the
        population block, because dropping it silently would make the
        population smaller than the tree without saying so -- and a capture the
        strict reader cannot open is exactly the one a reader should be told
        about.
        """
        # The other direction, so the case above is not vacuous. `load_capture`
        # hands back `(marks, changes)` on a read and `(None, reason)` on a
        # refusal, so the first slot is what tells the two apart.
        marks, _ = scan.load_capture(str(CAPTURE))
        self.assertIsNotNone(marks)
        self.assertTrue(marks)
        # A file that is not a capture at all: the annotation tables under
        # `ec/annotations/` are what the `,MARK,` prefilter exists to skip, and
        # one handed to the reader is refused on its first row.
        a_table = next((REPO / "ec" / "annotations").glob("*.csv"))
        marks, why = scan.load_capture(str(a_table))
        self.assertIsNone(marks)
        self.assertTrue(why, "a refusal carries its reason, not a bare None")


if __name__ == '__main__':
    unittest.main()
