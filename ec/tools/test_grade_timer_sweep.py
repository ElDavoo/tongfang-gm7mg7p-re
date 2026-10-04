#!/usr/bin/env python3
"""Offline checks for grade_timer_sweep.py. No EC is opened: the captures
below are constructed in a temporary directory, carry the `2026-01-01`
placeholder date `testdata/README.md` reserves for constructed input, and say
so in their first line. The exception is `CommittedPairAgainstTheSuite`, which
holds the one committed instance of the merged-run path the grader has: it
reads the sweep procedure's own §4a and §4b captures from `evidence/`, and
`merged-capture-against-committed-pair.md` is the write-up for what it finds.

The first test is the one that keeps the grader honest about the code. PRE and
POST are hand-typed lists; this re-reads them from the committed EC image, so
a list that drifts from the bytes at bank1 0x8001-0x8189 fails here rather
than grading a capture against the wrong prediction.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('gts', HERE / 'grade_timer_sweep.py')
gts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gts)

FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
# bank1 runtime 0x8001-0x8189 sits at file 0x10001 ("CODE bank 1 at file
# 0x10000", the header of every ec/decompiled/bank1/*.c).
SWEEP = (0x10001, 0x1018A)
RET_AT = 0x10074

HEADER = "# CONSTRUCTED INPUT, NOT A CAPTURE. Written by test_grade_timer_sweep.py.\n"


def ts(sec):
    whole = int(sec)
    ms = round((sec - whole) * 1000)
    if ms == 1000:
        whole, ms = whole + 1, 0
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    return f"2026-01-01T{h:02d}:{m:02d}:{s:02d}.{ms:03d}+00:00"


def write_capture(path, interval, addrs, baseline, rows, end, baseline_at=0):
    """`baseline_at` is the second on the `# baseline` line, and it exists so a
    second file can state its levels at its own t0 rather than at the first
    file's. A level a byte really held at the start of its own capture is not
    the same claim as a level it held at the start of someone else's."""
    with open(path, 'w') as f:
        f.write(HEADER)
        f.write(f"# interval {interval}s  seconds {end}  {len(addrs)} addresses: "
                + " ".join(f"{a:#06x}" for a in addrs) + "\n")
        f.write(f"# baseline {ts(baseline_at)}: "
                + " ".join(f"0x{a:04X}=0x{baseline[a]:02X}" for a in addrs) + "\n")
        f.write("ts,addr,old,new\n")
        for t, a, o, n in sorted(rows):
            f.write(f"{ts(t)},0x{a:04X},0x{o:02X},0x{n:02X}\n")
        f.write(f"# ended {ts(end)}  constructed\n")


def countdown(addr, start, t0, step, stop):
    """Rows for a byte decrementing from start by one every `step` s to 0."""
    rows, v, t = [], start, t0
    while v > 0 and t <= stop:
        rows.append((t, addr, v, v - 1))
        v, t = v - 1, t + step
    return rows


def reload_cycle(t0, step, stop, start=9):
    rows, v, t = [], start, t0
    while t <= stop:
        n = 9 if v == 0 else v - 1
        rows.append((t, gts.RELOAD, v, n))
        v, t = n, t + step
    return rows


def one_capture_contradicting_itself(dirpath, address=0x0635, levels=(0x14, 0x04),
                                    intervals=(0.01,)):
    """One file stating one of its own header figures twice, and its path.

    The second shape `merged_capture_refusal` refuses: no second file, the
    file disagreeing with itself. `write_capture` cannot build it, because
    `ec_timer_capture.py` cannot produce it -- its levels come out of a dict
    keyed by address (`:314`), so the committed writer says each address once
    and states each `# interval` line once (`:278` takes `--interval` per
    invocation). Which is the point of writing this out longhand. The refusal
    is not hypothetical because a second file happens to exist; it is
    hypothetical because a capture gets hand-edited or written by something
    else, and `load()` collects a repeated entry in one header exactly as it
    collects two files that disagree -- `intervals` and `levels` are appended
    per entry, and nothing downstream knows which file an entry came from
    beyond the path it is filed under.

    Two figures, two shapes: `levels` longer than one contradicts the file's
    `# baseline`, `intervals` longer than one contradicts its `# interval`, and
    both reach the same sentence.
    """
    path = dirpath / 'dup.csv'
    with open(path, 'w') as f:
        f.write(HEADER)
        for interval in intervals:
            f.write(f"# interval {interval}s  seconds 1.1  1 addresses: "
                    f"{address:#06x}\n")
        f.write(f"# baseline {ts(0)}: "
                + " ".join(f"0x{address:04X}=0x{v:02X}" for v in levels) + "\n")
        f.write("ts,addr,old,new\n")
        f.write(f"{ts(0.05)},0x{address:04X},0x{levels[0]:02X},0x13\n")
        f.write(f"{ts(0.15)},0x{address:04X},0x13,0x12\n")
        f.write(f"# ended {ts(1.1)}  constructed\n")
    return str(path)


def two_captures(dirpath, intervals, levels, baseline_at=(0, 0)):
    """Two captures of the same sweep either side of a suspend, and their paths.

    The pair every merged-run case here builds, so the only thing that varies
    between them is the field under test: what each `# interval` line states
    and what each `# baseline` line states. A file's rows start at the level
    its own header gives 0x06D6, because a level a byte held at the start of
    its own capture is the claim the header is making; `baseline_at` is per
    file, so the second file's levels can sit at its own t0 rather than the
    first file's.
    """
    paths = []
    for i, interval in enumerate(intervals):
        t0, stop = 0.05 + 20 * i, 5.0 + 20 * i
        rows = reload_cycle(t0, 0.1, stop, start=levels[i][gts.RELOAD])
        rows += countdown(0x0635, 20, t0 + 0.02, 0.1, stop)
        path = dirpath / f'part{i}.csv'
        write_capture(path, interval, [0x0635, gts.RELOAD], levels[i], rows,
                      stop, baseline_at[i])
        paths.append(str(path))
    return paths


def run(*paths):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = gts.main(list(paths))
    return rc, out.getvalue()


def run_quietly(*paths):
    """`run` plus stderr, which is where the refusal lands and nothing else.

    Beside `run` rather than in place of it: every graded run prints its whole
    report to stdout, so no call site has to be changed to learn about a run
    that printed nothing there.
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = gts.main(list(paths))
    return rc, out.getvalue(), err.getvalue()


class TheListsAreTheCode(unittest.TestCase):
    def test_counts_reconcile_to_thirty_nine(self):
        self.assertEqual(len(gts.PRE), 13)
        self.assertEqual(len(gts.POST), 25)
        self.assertEqual(len(set(gts.PRE) | set(gts.POST) | {gts.RELOAD}), 39)

    @unittest.skipUnless(FIRMWARE.exists(), "firmware image not present")
    def test_pre_and_post_are_the_image_in_code_order(self):
        img = FIRMWARE.read_bytes()
        # The countdown shape: mov DPTR,#imm / movx A,@DPTR / jz rel / dec A /
        # movx @DPTR,A. 0x0440's gate reads share the first three and then
        # branch, so the dec/store pair is what separates a countdown.
        found = []
        i = SWEEP[0]
        while i < SWEEP[1]:
            if (img[i] == 0x90 and img[i + 3] == 0xE0 and img[i + 4] == 0x60
                    and img[i + 6] == 0x14 and img[i + 7] == 0xF0):
                found.append((i, (img[i + 1] << 8) | img[i + 2]))
            i += 1
        self.assertEqual(img[RET_AT], 0x22, "the early ret at 0x8074")
        before = [a for off, a in found if off < RET_AT]
        after = [a for off, a in found if off > RET_AT]
        # 0x063A has a sign-bit test between its load and its jz, so it is
        # matched separately rather than by the shape above.
        self.assertIn(0x063A, gts.PRE)
        at = img.index(bytes([0x90, 0x06, 0x3A]), *SWEEP)
        where = {a: off for off, a in found}
        self.assertTrue(where[0x0639] < at < where[0x0890] < RET_AT)
        self.assertEqual([a for a in gts.PRE if a != 0x063A],
                         [a for a in before if a != gts.RELOAD])
        self.assertEqual(before[-1], gts.RELOAD)
        self.assertEqual(gts.POST, after)


class Grading(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_capture_gives_period_ten_and_ratio_ten(self):
        p = self.dir / 'clean.csv'
        rows = reload_cycle(0.05, 0.1, 5.0)
        rows += countdown(0x0635, 20, 0.02, 0.1, 5.0)     # PRE, every pass
        rows += countdown(0x06C2, 4, 0.9, 1.0, 5.0)       # POST, one in ten
        addrs = [0x0635, gts.RELOAD, 0x06C2, 0x06D9]
        write_capture(p, 0.01, addrs,
                      {0x0635: 20, gts.RELOAD: 9, 0x06C2: 4, 0x06D9: 3}, rows, 5.0)
        rc, out = run(str(p))
        self.assertEqual(rc, 0)
        self.assertIn("every change is a -1 step or the 0 -> 9 reload: yes", out)
        self.assertIn("period / step = 10.00", out)
        self.assertIn("= 10.00 (the early return predicts 10)", out)
        self.assertRegex(out, r"0x06D9  held at 0x03 over 5\.0s -- not reached")
        self.assertIn("0x0890  not sampled", out)

    def test_flat_capture_is_a_result_not_an_absence(self):
        p = self.dir / 'flat.csv'
        addrs = [gts.RELOAD, 0x06C2]
        write_capture(p, 0.2, addrs, {gts.RELOAD: 4, 0x06C2: 0}, [], 60.0)
        rc, out = run(str(p))
        self.assertEqual(rc, 0)
        self.assertIn("did not move over 60.0s; held at 0x04", out)
        self.assertIn("aliasing", out)
        self.assertIn("rate ratio\n  not measurable", out)
        self.assertIsNone(re.search(r"\babsent\b", out))

    def test_another_writer_is_flagged(self):
        p = self.dir / 'other.csv'
        rows = reload_cycle(0.05, 0.1, 1.0)
        rows.append((1.02, gts.RELOAD, 0x08, 0x09))       # not 0 -> 9
        write_capture(p, 0.01, [gts.RELOAD], {gts.RELOAD: 9}, rows, 1.1)
        rc, out = run(str(p))
        self.assertEqual(rc, 0)
        self.assertIn("NO -- another writer, or a missed sample", out)
        self.assertIn("up 1", out)

    def test_suspend_gap_is_excluded_and_counted_mod_ten(self):
        # Awake at 100 ms, then 12.3 s with no samples, then awake again, with
        # 0x06D6 having moved one step (mod 10) across the gap, and the resume
        # mark stamped 50 ms after the first sample, as a poller stamps it.
        p = self.dir / 'suspend.csv'
        rows = reload_cycle(0.05, 0.1, 5.0)
        last = rows[-1][3]
        after = 9 if last == 0 else last - 1
        rows.append((17.3, gts.RELOAD, last, after))
        rows += reload_cycle(17.31, 0.1, 22.0, start=after)
        write_capture(p, 0.01, [gts.RELOAD], {gts.RELOAD: 9}, rows, 22.1)
        with open(p) as f:
            body = f.read().replace(
                "# ended", f"{ts(17.35)},MARK,,\"auto: resumed, ~7.2 s suspended\"\n# ended")
        with open(p, 'w') as f:
            f.write(body)
        rc, out = run(str(p))
        self.assertEqual(rc, 0)
        self.assertIn("so the gap held 1 (mod 10) passes", out)
        self.assertIn("a different residue", out)
        # The 12.3 s gap, and the 10 ms from the first post-gap sample to the
        # next real step, are both out of the step figures.
        self.assertIn("min 100.0, max 100.0", out)

    def test_unresolved_step_warns(self):
        p = self.dir / 'slow.csv'
        rows = reload_cycle(0.05, 0.1, 3.0)
        write_capture(p, 0.05, [gts.RELOAD], {gts.RELOAD: 9}, rows, 3.1)
        rc, out = run(str(p))
        self.assertIn("WARNING: median step is under 3 sample intervals", out)

    def test_a_capture_given_twice_is_refused(self):
        # This is the shape the door grader takes too, and the two do not fail
        # alike, which is why each refusal says what a repeat costs *it*.
        # Here `load()` merges the rows of every file it is given, so a file
        # listed twice puts two rows at one timestamp: every interval between
        # two of 0x06D6's own steps becomes 0, the median step prints as
        # 0.0 ms under the "not resolved" warning, and `period / step` then
        # divides by it. That is a ZeroDivisionError and a traceback, after a
        # report has already been half printed -- not a wrong number, and not a
        # refusal.
        p = self.dir / 'clean.csv'
        rows = reload_cycle(0.05, 0.1, 5.0)
        rows += countdown(0x0635, 20, 0.02, 0.1, 5.0)     # PRE, every pass
        rows += countdown(0x06C2, 4, 0.9, 1.0, 5.0)       # POST, one in ten
        write_capture(p, 0.01, [0x0635, gts.RELOAD, 0x06C2, 0x06D9],
                      {0x0635: 20, gts.RELOAD: 9, 0x06C2: 4, 0x06D9: 3}, rows,
                      5.0)

        rc, out, err = run_quietly(str(p), str(p))
        self.assertEqual(rc, 1)
        self.assertIn(f'{str(p)!r} is given twice', err)
        self.assertIn('A capture given twice is one capture and not two', err)
        # Refused before `grade()`, so there is no half-printed report and the
        # two lines that make the damage legible are both absent.
        for absent in ('the step is not resolved', 'period / step',
                       'step interval'):
            self.assertNotIn(absent, out)

        # The message is about the period, not about windows: this grader has
        # none, and a reader who took it for the door grader's would be sent
        # looking for a window count that was never going to move.
        self.assertIn('period / step', err)
        self.assertNotIn('window', err)

        # And the same capture once is the graded run it would have been: the
        # refusal is pinned to the duplicate, not to this invocation.
        rc, out = run(str(p))
        self.assertEqual(rc, 0)
        self.assertIn('period / step = 10.00', out)

    def test_two_distinct_captures_are_still_one_run(self):
        # What the refusal is *not*: `capture.csv [capture2.csv ...]` is this
        # tool's documented usage, and `load()` merges the files, so two
        # captures of the same sweep taken either side of a suspend are a
        # legitimate command line. Refusing it would be a contract change
        # rather than a fix, and the test is what holds the difference.
        first, second = self.dir / 'first.csv', self.dir / 'second.csv'
        for path, (t0, stop) in ((first, (0.05, 5.0)), (second, (20.0, 25.0))):
            rows = reload_cycle(t0, 0.1, stop)
            rows += countdown(0x0635, 20, t0 + 0.02, 0.1, stop)
            write_capture(path, 0.01, [0x0635, gts.RELOAD],
                          {0x0635: 20, gts.RELOAD: 9}, rows, stop)
        rc, out = run(str(first), str(second))
        self.assertEqual(rc, 0)
        # Merged, not graded twice: one span covering both, and the step
        # resolved to the sweep's own 100 ms rather than collapsed by the gap.
        self.assertIn('span 25.000s', out)
        self.assertIn('median 100.0 ms', out)
        self.assertIn('period / step = 10.00', out)

    def test_an_interval_disagreement_is_refused(self):
        # `load()` took the sample interval from whichever file was named
        # last, so this pair graded a median step taken over both files
        # against one of their two `--interval` values, and said so with a
        # number. Nothing forces two captures to agree on it: the writer
        # takes `--interval` per invocation, and the 0x8001 sweep procedure
        # runs it at 0.01, 0.0005 and 0.002 across its arms.
        agreed = {0x0635: 20, gts.RELOAD: 9}
        first, second = two_captures(self.dir, [0.01, 0.05], [agreed, agreed])
        rc, out, err = run_quietly(first, second)
        self.assertEqual(rc, 1)
        # Both values, in both files, so the operator can see which is which
        # without re-running anything.
        for named in ("0.01s in", "0.05s in", str(self.dir / 'part0.csv'),
                      str(self.dir / 'part1.csv')):
            self.assertIn(named, err)
        # The merge half of the interval clause: two files, so the sentence may
        # count them. The one-file case below cannot, and says "this run's
        # rows" instead.
        self.assertIn('over all 2 files', err)
        # Refused before `grade()`, so there is no half-printed report.
        for absent in ('span ', 'step interval', 'period / step'):
            self.assertNotIn(absent, out)

        # The control: the same two files, the same level, the same rows, with
        # the intervals equal. So the refusal is pinned to the disagreement and
        # not to naming two captures.
        first, second = two_captures(self.dir, [0.01, 0.01], [agreed, agreed])
        rc, out = run(first, second)
        self.assertEqual(rc, 0)
        self.assertIn('period / step = 10.00', out)

    def test_a_baseline_level_disagreement_is_refused(self):
        # The same defect one level down. The first file's `# baseline` was
        # kept and the second's dropped without a word, so a byte would have
        # been reported as held at the level a *first* capture read it at, over
        # a span the second capture's rows sit inside -- and 0x06C5 in §4b of
        # the sweep procedure is a byte that moved across exactly such a
        # boundary.
        first_level = {0x0635: 20, gts.RELOAD: 9}
        second_level = {0x0635: 20, gts.RELOAD: 4}
        first, second = two_captures(self.dir, [0.01, 0.01],
                                     [first_level, second_level],
                                     baseline_at=(0, 20))
        rc, out, err = run_quietly(first, second)
        self.assertEqual(rc, 1)
        self.assertIn('0x06D6', err)
        self.assertIn('0x09', err)
        self.assertIn('0x04', err)
        self.assertIn(str(self.dir / 'part0.csv'), err)
        self.assertIn(str(self.dir / 'part1.csv'), err)
        # 0x0635 is watched by both files and both give it the same level, so
        # it is not a disagreement and does not belong in the sentence.
        self.assertNotIn('0x0635', err)
        for absent in ('span ', 'step interval', 'period / step'):
            self.assertNotIn(absent, out)
        # The merge half of the clause, pinned here so the one-file case below
        # cannot quietly take it over: this is two files disagreeing, so the
        # sentence is allowed to talk about the other file's rows.
        self.assertIn('over a span that includes the other file', err)
        # And it does not claim nothing was read -- `load()` has opened and
        # parsed both files by the time it can know they disagree.
        self.assertNotIn('nothing was read', err)
        self.assertIn('so no run was built', err)

        # The control again, and the one the other refusal's case also needs:
        # agreeing levels over the same two files grade, and 0x0635 -- which
        # both files gave the same level for -- is not named in the refusal.
        first, second = two_captures(self.dir, [0.01, 0.01],
                                     [first_level, first_level],
                                     baseline_at=(0, 20))
        rc, out, err = run_quietly(first, second)
        self.assertEqual(rc, 0)
        self.assertEqual(err, '')
        self.assertIn('period / step = 10.00', out)

    def test_a_single_capture_contradicting_itself_is_refused(self):
        # The other shape `merged_capture_refusal` reaches. One file, no
        # second file to disagree with, and the sentence said "1 captures
        # disagree about a figure a merged run can only take from one file ...
        # over a span that includes the other file ... Grade them one at a
        # time" -- a merge asserted where none happened, and an operator sent
        # looking for a file that is not there. So each of those four clauses
        # says what is true of one capture instead, and this pins that it does.
        p = one_capture_contradicting_itself(self.dir)
        rc, out, err = run_quietly(p)
        self.assertEqual(rc, 1)
        self.assertEqual(out, '')
        # Both values, in the one file that states both, so the operator can
        # see which is which without re-running anything.
        for named in ('0x14', '0x04', '0x0635', p):
            self.assertIn(named, err)
        self.assertIn('1 capture contradicts itself', err)
        self.assertIn('so no run was built', err)
        self.assertIn('over the whole of that capture', err)
        self.assertIn('Grade it on its own', err)
        # The four the shape cannot support, each asserted as absent rather
        # than left unread: a merge that did not happen, the ungrammatical
        # "1 captures", the merge's own span and closer, and the repeat
        # refusal's true-on-that-path claim that nothing was read.
        for absent in ('the other file', '1 captures', 'over all 1 files',
                       'Grade them', 'nothing was read', 'merged run'):
            self.assertNotIn(absent, err)
        # Still one ordered sentence, not one per conflict, and still refused
        # before `grade()`.
        self.assertEqual(err.strip().count('\n'), 0)

        # The control: the same file with one value for that address grades.
        # So what is refused is the contradiction and not the file.
        single = one_capture_contradicting_itself(self.dir, levels=(0x14,))
        rc, out, err = run_quietly(single)
        self.assertEqual(rc, 0)
        self.assertEqual(err, '')
        self.assertIn('0x0635  0x14 -> 0x12', out)
        # One capture, so neither clause the merge added may appear.
        self.assertNotIn('union', out)
        self.assertNotIn('stated by', out)

        # And the same file shape saying the *interval* twice rather than the
        # level, which reaches the other half of the sentence. "over all 1
        # files" was the merge's clause with the count left in it, and the
        # count is the only thing that was wrong.
        clash = one_capture_contradicting_itself(self.dir, levels=(0x14,),
                                                 intervals=(0.01, 0.05))
        rc, out, err = run_quietly(clash)
        self.assertEqual(rc, 1)
        self.assertEqual(out, '')
        for named in ('0.01s', '0.05s', clash, 'over this run\'s rows'):
            self.assertIn(named, err)
        for absent in ('over all 1 files', '1 captures', 'Grade them',
                       'the other file', 'nothing was read'):
            self.assertNotIn(absent, err)

    def test_one_refusal_names_every_disagreement_in_a_stated_order(self):
        # A refusal per disagreement discovered serially would cost the
        # operator a run each, and the order between them would be whatever
        # the loop happened to reach first. So all three are in one sentence,
        # intervals first and levels by ascending address -- which is the order
        # `merged_capture_refusal` states in its docstring, pinned here rather
        # than left to be discovered by running the thing.
        first_level = {0x0635: 20, gts.RELOAD: 9}
        second_level = {0x0635: 12, gts.RELOAD: 4}
        first, second = two_captures(self.dir, [0.01, 0.05],
                                     [first_level, second_level],
                                     baseline_at=(0, 20))
        rc, out, err = run_quietly(first, second)
        self.assertEqual(rc, 1)
        self.assertEqual(err.strip().count('\n'), 0,
                         'every disagreement belongs in the one sentence')
        clauses = ['0.01s', '0.05s', '0x0635', '0x06D6']
        for named in clauses:
            self.assertIn(named, err)
        where = [err.index(named) for named in clauses]
        self.assertEqual(where, sorted(where),
                         'intervals first, then levels by ascending address')
        self.assertEqual(out, '')

    def test_an_accepted_merged_run_says_where_its_figures_came_from(self):
        # What the two refusals leave, and the reason they can leave it: the
        # span is a union and says so, the sample interval says how many of
        # the files state it, and the numbers underneath are the merged run's.
        # The two files here are 0.05-5.0s and 20.05-25.0s with each one's
        # `# baseline` at its own t0, as `ec_timer_capture.py` stamps it, so
        # neither window contains the other and 15s of the merged span is a
        # hole neither file watched: `which none of them covers` is true of
        # them. `baseline_at` matters here and not in the two refusal cases --
        # a pair whose second file also claims a baseline at the first file's
        # t0 has a window that does cover the union, and gets the other half.
        agreed = {0x0635: 20, gts.RELOAD: 9}
        first, second = two_captures(self.dir, [0.01, 0.01], [agreed, agreed],
                                     baseline_at=(0, 20))
        rc, out = run(first, second)
        self.assertEqual(rc, 0)
        self.assertIn('span 25.000s (the union of the 2 captures given, which '
                      'none of them covers)', out)
        self.assertIn('stated by 2 of 2 files', out)
        self.assertIn('span 25.000s', out)
        self.assertIn('median 100.0 ms', out)
        self.assertIn('period / step = 10.00', out)

    def test_the_interval_clause_counts_files_and_not_interval_lines(self):
        # The count and the denominator were two different units. `INTERVALS`
        # holds one entry per `# interval` **line** and the clause divided it by
        # `len(paths)`, which counts files, so a file stating its interval
        # twice at the same value printed `stated by 3 of 2 files` -- a run
        # built by `cat`ing two captures of one sweep together, grading, and
        # reporting a numerator above its own denominator. In the one sentence
        # whose whole job is saying where a figure came from, and the
        # self-contradiction the issue exists to close. The count is of files.
        #
        # The repeat has to be at the *same* value: that is graded rather than
        # refused, because `merged_capture_refusal` groups the entries by
        # value and a duplicate of one value collapses to one key, so only a
        # genuine conflict reaches its `len(said) > 1` test. `ec_timer_capture`
        # cannot write this file -- it states each `# interval` line once, from
        # `--interval` per invocation -- which is why it is written longhand.
        agreed = {0x0635: 20, gts.RELOAD: 9}
        dup = one_capture_contradicting_itself(self.dir, levels=(0x14,),
                                               intervals=(0.01, 0.01))
        # One real capture beside it, agreeing on both figures -- 0x14 is 20,
        # so the level `countdown` starts 0x0635 at, and the intervals match.
        second = two_captures(self.dir, [0.01], [agreed])[0]
        rc, out = run(dup, second)
        self.assertEqual(rc, 0)
        # Both files state it, three lines say so, two files were given.
        self.assertIn('stated by 2 of 2 files', out)
        self.assertNotIn('stated by 3 of 2 files', out)
        # Still an accepted merge: the refusal groups by value, so a repeat of
        # one value is not a disagreement. Pinned because the count above could
        # have been fixed by refusing the repeat instead, and refusing it is
        # the shape the other case in this file already covers.
        self.assertIn('the union of the 2 captures given', out)

        # The other direction, and the write-up's "a file with no `# interval`
        # line contributes no interval": one file stating the interval twice
        # beside one that states it not at all. Counted by lines this reads 2
        # of 2, which credits the silent file with an interval it never wrote;
        # counted by files it is the 1 of 2 the write-up quotes. So the two
        # halves pin both ends of the range -- a numerator above the
        # denominator, and one inside it that names the wrong file.
        silent = Path(two_captures(self.dir, [0.01, 0.01],
                                   [agreed, agreed], baseline_at=(0, 20))[1])
        # `ec_timer_capture.py` always writes the line, so this capture is
        # hand-stripped into a shape no committed writer produces -- which is
        # what the write-up says of it, and why the reader has to be the one
        # that reads it. `addresses:` rides on the same line, so this file
        # states no watched list either and contributes its rows alone.
        silent.write_text(''.join(
            l for l in silent.read_text().splitlines(keepends=True)
            if not l.startswith('# interval')))
        rc, out = run(dup, str(silent))
        self.assertEqual(rc, 0)
        self.assertIn('stated by 1 of 2 files', out)
        self.assertNotIn('stated by 2 of 2 files', out)

        # The control: the same file shape with its two lines at *different*
        # values. That is the one case here that is refused rather than
        # counted, and the refusal names all three values across both files --
        # so the count above is not what decides this pair, and a fix that had
        # taught the clause to count lines would still have to leave this
        # alone. Merged, so the shape is the merge's: the one-file clause is
        # covered by `test_a_single_capture_contradicting_itself_is_refused`.
        clash = one_capture_contradicting_itself(self.dir, levels=(0x14,),
                                                 intervals=(0.01, 0.05))
        rc, out, err = run_quietly(clash, second)
        self.assertEqual(rc, 1)
        self.assertEqual(out, '')
        for named in ('0.01s', '0.05s', clash, second):
            self.assertIn(named, err)
        self.assertNotIn('stated by', err)

    def test_a_merged_run_says_which_none_covers_only_when_none_does(self):
        # The clause is a claim about the captures, and a merge of two nested
        # windows falsifies it: `first`/`last` are min/max'd across files, so
        # a 0-30s file merged with a 10-20s one of the same sweep gives a
        # 30s span that the 0-30s file covers on its own. Printed
        # unconditionally -- which is how this read -- that run asserted the
        # opposite of what its own construction shows. So the half is printed
        # only when no single file's window is the merged pair, and the union
        # half is printed either way.
        rows = reload_cycle(0.05, 0.1, 30.0)
        rows += countdown(0x0635, 20, 0.07, 0.1, 30.0)
        levels = {0x0635: 20, gts.RELOAD: 9}
        outer, inner = self.dir / 'outer.csv', self.dir / 'inner.csv'
        write_capture(outer, 0.01, [0x0635, gts.RELOAD], levels, rows, 30.0)
        # The same sweep's rows between 10s and 20s, with this file's
        # `# baseline` at its own start the way `ec_timer_capture.py` stamps
        # it, so its window is 10-20s and lies wholly inside the first's
        # 0-30s. Both state the same interval and the same levels, so this is
        # an accepted merge and not a refusal.
        write_capture(inner, 0.01, [0x0635, gts.RELOAD], levels,
                      [r for r in rows if 10.0 <= r[0] <= 20.0], 20.0,
                      baseline_at=10.0)
        rc, out = run(str(outer), str(inner))
        self.assertEqual(rc, 0)
        # Still graded as the one union it is, and still says it is a union.
        self.assertIn('span 30.000s (the union of the 2 captures given), ',
                      out)
        # And it does not claim a coverage the outer file contradicts.
        self.assertNotIn('which none of them covers', out)
        self.assertIn('stated by 2 of 2 files', out)
        self.assertIn('period / step = 10.00', out)

    def test_a_single_capture_report_is_byte_identical(self):
        # The gate on both new clauses. One capture has no other file for
        # either to point at, so the header has to be exactly what it was --
        # asserted as a whole line rather than in pieces, because a clause
        # that crept in one fragment at a time would satisfy any of them.
        p = self.dir / 'one.csv'
        write_capture(p, 0.01, [gts.RELOAD], {gts.RELOAD: 9},
                      reload_cycle(0.05, 0.1, 1.0), 1.1)
        rc, out = run(str(p))
        self.assertEqual(rc, 0)
        self.assertIn('span 1.100s, 10 change rows, sample interval 0.01s, '
                      '1 addresses watched', out)
        self.assertNotIn('union', out)
        self.assertNotIn('stated by', out)


class CommittedPairAgainstTheSuite(unittest.TestCase):
    """The merged-run path against the sweep procedure's own two captures.

    Every other case here builds its pair, because the merged path had no
    committed instance to build from. These two are committed and real: §4a
    and §4b of `docs/hardware-tests/xdata-06c2-06db-sweep.md`, the
    perturbation and suspend arms. **They are not two captures of one sweep**,
    which is what that path is for -- they are two runs about fifteen minutes
    apart with four operator actions between them. So this pair is a merge of
    the wrong thing, and the refusal it draws is the correct answer rather
    than a defect; what it holds is that the refusal behaves as designed on a
    real pair. `merged-capture-against-committed-pair.md` is the write-up.

    Reading committed captures is still reading files, so this is no more a
    live test than the rest of the suite: nothing is opened but a CSV.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def pair(self):
        """The two committed captures, resolved from the repository root."""
        watch = HERE.parent.parent / 'evidence' / 'ec-watch'
        return (watch / '2026-09-24-06c2-06db-suspend-linux.csv',
                watch / '2026-09-24-06c2-06db-perturb-linux.csv')

    def test_the_committed_pair_is_refused_on_one_address(self):
        suspend, perturb = self.pair()
        rc, out, err = run_quietly(str(suspend), str(perturb))
        # Refused before `grade()`, so no half-printed report sits behind it.
        self.assertEqual(rc, 1)
        self.assertEqual(out, '')
        # The one disagreement, with both values in the file each came from,
        # so an operator can see which is which without re-running anything.
        for named in ('0x06D6', '0x04', '0x03', str(suspend), str(perturb)):
            self.assertIn(named, err)
        self.assertIn('so no run was built', err)
        # The discriminating assertion. Both captures state `# interval
        # 0.01s`, so the level clause is the only one that can fire, and a
        # run whose refusal named the interval instead would be a different
        # defect from the one this pair shows.
        self.assertNotIn('sample interval is', err)
        # And every other address agrees, which is why the sentence names one
        # address and not thirty-five. Read the levels rather than pinning a
        # list, so a future capture that moves a second address names itself
        # here instead of passing on a stale set.
        here, there = self.baselines(suspend), self.baselines(perturb)
        self.assertEqual(here['0x06D6'], '0x04')
        self.assertEqual(there['0x06D6'], '0x03')
        self.assertEqual({a: v for a, v in here.items() if a != '0x06D6'},
                         {a: v for a, v in there.items() if a != '0x06D6'})
        for addr in here:
            if addr != '0x06D6':
                self.assertNotIn(addr, err)

    def test_the_same_pair_grades_once_its_one_disagreement_is_removed(self):
        # The control, and what pins the refusal to the disagreement rather
        # than to being handed two captures. The two files are copied into
        # this case's temporary directory and `0x06D6`'s `# baseline` level
        # is made the same in both. The committed files are not modified, and
        # the copies are derived input rather than anything
        # `testdata/README.md` indexes.
        suspend, perturb = self.pair()
        agreed_level = self.baselines(suspend)['0x06D6']
        other_level = self.baselines(perturb)['0x06D6']
        self.assertNotEqual(agreed_level, other_level,
                            'the control needs a disagreement to remove, so a '
                            'pair that already agrees is not measuring this')
        agreed = []
        for source, level in ((suspend, agreed_level), (perturb, other_level)):
            body = source.read_text().replace(f'0x06D6={level}',
                                              f'0x06D6={agreed_level}')
            copy = self.dir / source.name
            copy.write_text(body)
            # The patch is one token on the one `# baseline` line and reaches
            # nothing else, so this grades the committed pair's own rows and
            # geometry rather than a capture built to pass. Checked rather
            # than assumed, because a `replace` that hit a row too would still
            # grade.
            before, after = source.read_text().splitlines(), body.splitlines()
            self.assertEqual(len(before), len(after))
            touched = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
            self.assertEqual(len(touched), 0 if level == agreed_level else 1)
            for i in touched:
                self.assertTrue(before[i].startswith('# baseline '))
            agreed.append(str(copy))
        rc, out, err = run_quietly(*agreed)
        self.assertEqual(rc, 0, err)
        self.assertEqual(err, '')
        # Both labels `grader-merged-capture-sources.md` added, so the merge
        # this pair would be is labelled rather than refused.
        self.assertIn('the union of the 2 captures given', out)
        self.assertIn('stated by 2 of 2 files', out)

    @staticmethod
    def baselines(capture):
        """`{address: level}` from one capture's `# baseline` line."""
        for line in capture.read_text().splitlines():
            if line.startswith('# baseline '):
                return dict(pair.split('=') for pair in
                            line.split(': ', 1)[1].split())
        raise AssertionError(f"{capture.name} states no `# baseline` line")


if __name__ == '__main__':
    unittest.main()
