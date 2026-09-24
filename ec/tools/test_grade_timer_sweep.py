#!/usr/bin/env python3
"""Offline checks for grade_timer_sweep.py. No EC is opened and no real
capture is read: the captures below are constructed in a temporary directory,
carry the `2026-01-01` placeholder date `testdata/README.md` reserves for
constructed input, and say so in their first line.

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


def write_capture(path, interval, addrs, baseline, rows, end):
    with open(path, 'w') as f:
        f.write(HEADER)
        f.write(f"# interval {interval}s  seconds {end}  {len(addrs)} addresses: "
                + " ".join(f"{a:#06x}" for a in addrs) + "\n")
        f.write(f"# baseline {ts(0)}: "
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


def run(*paths):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = gts.main(list(paths))
    return rc, out.getvalue()


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

    def test_unresolved_step_warns(self):
        p = self.dir / 'slow.csv'
        rows = reload_cycle(0.05, 0.1, 3.0)
        write_capture(p, 0.05, [gts.RELOAD], {gts.RELOAD: 9}, rows, 3.1)
        rc, out = run(str(p))
        self.assertIn("WARNING: median step is under 3 sample intervals", out)


if __name__ == '__main__':
    unittest.main()
