#!/usr/bin/env python3
"""Offline checks for grade_pd_index_block.py. No EC is opened and no capture
from this repository is read: every capture below is constructed in a temporary
directory and carries the `2026-01-01` placeholder date
`testdata/README.md` reserves for constructed input, and says so in its first
line.

What this stands in for is the turn the run's result takes. A capture is a list
of change rows; what a later reader needs from it is a table saying which bytes
moved, how much they took, and how that lines up with the operator's actions --
and, for the two addresses `pd-xdata-overlap.md` §7 names, which of the two
readings the capture can support. Both of those are places a grader can be
quietly wrong in the direction of overclaiming, so the cases below are the ones
that would make it overclaim:

  * a byte that held still reads as *not reached on the paths watched, over this
    span*, never as absent and never as zero -- the live-capture spelling of
    the rule CLAUDE.md keeps for a static scan's zero hits;
  * an address outside the host window is reported as **not sampled**, not
    graded, because a constant `0xFF` there is a fact about the host;
  * a byte whose record spans the fan page `0x0460`-`0x046F` carries the
    reachable figure even though the byte itself sits inside what can be read,
    because the claim being corrected is about the record -- "inside the
    window" and "readable by a capture" are different questions, and only the
    second one is the one an `--addrs` argument can act on;
  * a byte quiet in the idle capture and moved in the active one is reported as
    differing -- that asymmetry is the whole comparison, and a diff that
    dropped the quiet-in-idle case would drop the signal it exists to find;
  * a `0x04A6` that never moves is reported as *consistent with* separate maps
    and not as evidence of them, while one that moves is reported as the
    overlap reading. The two directions are not interchangeable and the grader
    is the place that has to know which one it is printing.

The refusals are tested in both directions as well: the same file under two
spellings, and a `--mark-relative` request over a capture with no MARK rows,
which has nothing to be relative to and would otherwise grade as though no
action had happened.
"""

import contextlib
import datetime
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

spec = importlib.util.spec_from_file_location(
    'grade_pd_index_block', HERE / 'grade_pd_index_block.py')
gpb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gpb)

spec_reach = importlib.util.spec_from_file_location(
    'pd_index_block_readability_for_grader', HERE / 'pd_index_block_readability.py')
reach = importlib.util.module_from_spec(spec_reach)
spec_reach.loader.exec_module(reach)

# The capture tool itself, for the two facts a grader cannot derive from a
# constructed capture: which addresses its guard refuses, and so which bytes no
# capture can hold. Imported by name so it is the same module object the
# readability tool imported its fan page from.
import ec_timer_capture as CAPTURE

HEADER = "# CONSTRUCTED INPUT, NOT A CAPTURE. Written by test_grade_pd_index_block.py\n"

# The `0x60` family's slot-0 and slot-1 records, and an address in none of
# them. `0x04A6`/`0x04A7` are the two `pd-xdata-overlap.md` §7 names, and
# `0x08E7` is a `0x5E` base -- outside the host window, so the one address in
# the fixtures that must never be graded.
SLOT0, SLOT1 = 0x0400, 0x0660
PROBE_A, PROBE_B = 0x04A6, 0x04A7
OUT_OF_WINDOW = 0x08E7

# A byte of the slot-0 record that spans the fan page `0x0460`-`0x046F`: the
# case where "inside the window" and "readable by a capture" come apart. It sits
# before the hole and well inside what *can* be read, which is the point -- the
# note it must carry is about the record, not about this byte.
FAN_CROSSING = 0x0450


def reach_slot0_base():
    """The `0x60` base whose slot-0 record spans the fan page.

    Read off the committed base list rather than written here, so a re-run that
    moves the bases leaves the fixture asserting about whichever record is now
    the cut one instead of about a record that no longer is.
    """
    for base in dict(reach.load_strides())["0x60"]:
        if base <= CAPTURE.FAN_PAGE.start < base + reach.RECORD_STRIDE:
            return base
    raise AssertionError("no 0x60 slot-0 record spans the fan page")


def ts(sec):
    """An ISO timestamp `sec` seconds into 2026-01-01 UTC.

    Millisecond resolution, which is what `ec_timer_capture.py`'s `now()`
    writes, so a row this suite builds is one the real tool could have written.
    """
    base = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    whole = int(sec)
    ms = round((sec - whole) * 1000)
    if ms == 1000:
        whole, ms = whole + 1, 0
    stamp = base + datetime.timedelta(seconds=whole, milliseconds=ms)
    return stamp.isoformat(timespec="milliseconds")


def write_capture(path, addrs, baseline, rows, marks=(), interval=0.01,
                  end=60.0, baseline_at=0.0):
    """A capture in the format `ec_timer_capture.py` writes.

    `marks` are `(second, label)` pairs. They go in as five-field rows with an
    empty fifth column, which is `ec_watch.Marker`'s provenance column and is
    not optional here: a four-field mark row reads as *not recorded* where an
    empty one reads as *held no flag*
    (`docs/findings/0751-mark-provenance-column.md`).
    """
    with open(path, 'w', encoding='utf-8') as f:
        f.write(HEADER)
        f.write(f"# interval {interval}s  seconds {end}  {len(addrs)} addresses: "
                + " ".join(f"{a:#06x}" for a in addrs) + "\n")
        f.write(f"# baseline {ts(baseline_at)}: "
                + " ".join(f"0x{a:04X}=0x{baseline[a]:02X}" for a in addrs) + "\n")
        f.write("ts,addr,old,new,provenance\n")
        for t, label in marks:
            f.write(f"{ts(t)},MARK,,{label},\n")
        for t, a, o, n in sorted(rows):
            f.write(f"{ts(t)},0x{a:04X},0x{o:02X},0x{n:02X}\n")
        f.write(f"# ended {ts(end)}  constructed\n")
    return str(path)


class Fixture:
    """A temporary directory holding the captures one test needs.

    Takes each capture either as a mapping or wrapped in a one-tuple, so a test
    with a single capture can write `Fixture(spec)` and a test with two can
    write `Fixture(spec_a, spec_b)` without a comma-counting trap.
    """

    def __init__(self, *captures):
        self._dir = tempfile.TemporaryDirectory()
        self.paths = []
        for name, capture in zip(("a.csv", "b.csv", "c.csv"), captures):
            spec_ = capture if isinstance(capture, dict) else capture[0]
            self.paths.append(write_capture(
                os.path.join(self._dir.name, name), **spec_))

    def __enter__(self):
        return self.paths

    def __exit__(self, *exc):
        self._dir.cleanup()
        return False


def grade(paths, **flags):
    """Run the grader's `grade()` over `paths` and return what it printed."""
    buf = io.StringIO()
    gpb.grade(paths, **flags, out=buf)
    return buf.getvalue()


def separation_line(text, addr):
    """The line about `addr` inside the map-separation section.

    Scoped to that section because the per-address table prints a line about
    the same address, and reading the wrong one would let the separation
    wording be tested against a line that never claims it.
    """
    body = text.split("map separation", 1)[1]
    body = body.split("\n\n", 1)[0]
    for line in body.splitlines():
        if line.strip().startswith(f"0x{addr:04X}"):
            return line
    raise AssertionError(f"no separation line for 0x{addr:04X} in:\n{text}")


class PerAddressTests(unittest.TestCase):
    """The table itself: what moved, what held, and how that is worded."""

    def test_a_moved_byte_reports_its_change_count_and_its_values(self):
        rows = [(5.0, SLOT0, 0x10, 0x11), (6.0, SLOT0, 0x11, 0x12)]
        with Fixture(dict(addrs=[SLOT0], baseline={SLOT0: 0x10}, rows=rows)) \
                as (path,):
            text = grade([path])
        self.assertIn("2", text)
        # Baseline, both intermediates and the last value are all distinct
        # values the byte took; the count is of those, not of the rows.
        self.assertIn("0x10 -> 0x12", text)

    def test_a_quiet_byte_reads_as_not_reached_and_not_as_absent(self):
        # The calibration rule in its live-capture spelling. Every wording that
        # would make a zero into an absence is the thing under test.
        with Fixture(dict(addrs=[SLOT0], baseline={SLOT0: 0x10}, rows=[])) \
                as (path,):
            text = grade([path])
        self.assertIn("not reached on the paths watched, over this span", text)
        for forbidden in ("absent", "unused", "zero", "never written"):
            self.assertNotIn(forbidden, text.lower().replace("over this span", ""),
                             f"{forbidden!r} reads as absence")

    def test_an_out_of_window_address_is_reported_as_not_sampled(self):
        # A constant `0xFF` there is a fact about the host, so grading it would
        # put a number in the table that no observation supports.
        with Fixture(dict(addrs=[OUT_OF_WINDOW],
                           baseline={OUT_OF_WINDOW: 0xFF},
                           rows=[(5.0, OUT_OF_WINDOW, 0xFF, 0xFF)])) as (path,):
            text = grade([path])
        self.assertIn("not sampled", text)
        self.assertIn("0xFF whatever the EC holds", text)

    def test_a_record_out_of_the_window_says_how_much_of_it_is_reachable(self):
        # Slot 1 of the `0x60` family starts inside the window and runs out of
        # it, so a line about one of its bytes has to carry the reachable
        # figure rather than implying the record was covered.
        self.assertEqual(gpb.slots_of(SLOT1)[1], 1)
        with Fixture(dict(addrs=[SLOT1], baseline={SLOT1: 0x00}, rows=[])) \
                as (path,):
            text = grade([path])
        self.assertIn("reachable", text)
        self.assertIn(str(reach.RECORD_STRIDE), text)

    def test_a_record_spanning_the_fan_page_says_so_on_every_line(self):
        # The claim a window-only reach count makes wrongly: the slot-0 record
        # at `0x0400` spans `0x0460`-`0x046F`, which `ec_timer_capture.py`
        # refuses, so it is not wholly sampled -- and a byte sitting well
        # inside what *can* be read still belongs to a record that was not
        # covered. The note is therefore on this line, not only on one past a
        # boundary.
        with Fixture(dict(addrs=[FAN_CROSSING], baseline={FAN_CROSSING: 0x00},
                          rows=[])) as (path,):
            text = grade([path])
        self.assertIn("reachable", text)
        self.assertEqual(gpb.slots_of(FAN_CROSSING),
                         ("0x60", 0, reach_slot0_base()))
        self.assertLess(reach.reachable_bytes(reach_slot0_base(), 0),
                        reach.RECORD_STRIDE)

    def test_the_fan_page_is_refused_here_too(self):
        # A capture cannot hold one of these bytes -- the capture tool refuses
        # them before it reads anything -- so the grader has nothing to grade
        # for it, and a line that reported a value would be reporting one no
        # tool in this tree could have read.
        self.assertIsNotNone(CAPTURE.check_addrs([CAPTURE.FAN_PAGE.start]))
        for addr in CAPTURE.FAN_PAGE:
            self.assertEqual(gpb.slots_of(addr), (None, None, None),
                             f"0x{addr:04X} placed in a record")

    def test_every_watched_address_gets_a_line_moved_or_not(self):
        with Fixture(dict(addrs=[SLOT0, PROBE_A, PROBE_B],
                           baseline={SLOT0: 0x00, PROBE_A: 0x07, PROBE_B: 0x00},
                           rows=[(5.0, SLOT0, 0x00, 0x01)])) as (path,):
            text = grade([path])
        for addr in (SLOT0, PROBE_A, PROBE_B):
            self.assertIn(f"0x{addr:04X}", text)


class SeparationTests(unittest.TestCase):
    """The one-sided question, in both of its directions.

    This is the section most able to overclaim: one of its two outputs is a
    *negative* that looks like evidence and is not. The tests hold each
    direction separately rather than checking that both words appear, and read
    the separation section rather than the per-address table's line about the
    same address.
    """

    def test_a_quiet_probe_is_consistent_with_separate_maps_and_proves_nothing(self):
        with Fixture(dict(addrs=[PROBE_A, SLOT0], baseline={PROBE_A: 0x07,
                                                            SLOT0: 0x00},
                          rows=[(5.0, SLOT0, 0x00, 0x01)],
                          marks=[(10.0, "plug")])) as (path,):
            line = separation_line(grade([path]), PROBE_A)
        self.assertIn("CONSISTENT WITH", line)
        self.assertIn("does not establish", line)
        # The direction that would turn the negative into a positive.
        self.assertNotIn("OVERLAP", line)

    def test_a_moving_probe_is_reported_as_the_overlap_reading(self):
        with Fixture(dict(addrs=[PROBE_A], baseline={PROBE_A: 0x07},
                          rows=[(12.0, PROBE_A, 0x07, 0x08)],
                          marks=[(10.0, "plug")])) as (path,):
            line = separation_line(grade([path]), PROBE_A)
        self.assertIn("OVERLAP", line)
        self.assertNotIn("CONSISTENT WITH", line)

    def test_an_unobserved_probe_says_neither_direction_is_available(self):
        # Not a quiet byte and not a moving one: an address this host does not
        # map, which reads `0xFF` throughout and would otherwise print the
        # quiet-probe sentence for a byte nobody observed. Both named probes
        # are inside this machine's window, so the guard is reached directly --
        # what it exists for is a host whose window is not this one.
        self.assertIn("neither direction is available",
                      gpb.separation_verdict(0x04A6, {0xFF}, 0, sampled=False))

    def test_the_unobserved_verdict_is_not_the_quiet_one(self):
        # The negative that makes the guard worth having: an unmapped probe
        # reading `0xFF` has one distinct value, exactly like a held byte, so
        # the two must not produce the same text.
        quiet = gpb.separation_verdict(0x04A6, {0xFF}, 0, sampled=True)
        unmapped = gpb.separation_verdict(0x04A6, {0xFF}, 0, sampled=False)
        self.assertNotEqual(quiet, unmapped)
        self.assertNotIn("separate map", unmapped)

    def test_a_probe_with_no_stated_value_is_neither_direction(self):
        # Watched in the header, but with no change row and no `# baseline`
        # level: there is nothing to read a movement or a stillness from.
        # Falling through to the moved branch would print "took 0 distinct
        # values" beside the overlap wording, which is a positive claim built
        # out of no evidence at all.
        nothing = gpb.separation_verdict(0x04A6, set(), 0, sampled=True)
        self.assertIn("no value is stated", nothing)
        self.assertNotIn("OVERLAP", nothing)
        self.assertNotIn("CONSISTENT WITH", nothing)

    def test_a_probe_absent_from_the_watched_list_says_so(self):
        with Fixture(dict(addrs=[SLOT0], baseline={SLOT0: 0x00},
                          rows=[(5.0, SLOT0, 0, 1)])) as (path,):
            line = separation_line(grade([path]), PROBE_A)
        self.assertIn("not in the watched list", line)


class DiffTests(unittest.TestCase):
    """Idle against active, and the byte the comparison exists to find."""

    def test_a_byte_quiet_idle_and_moved_active_is_reported_as_differing(self):
        # The case a naive `last value or absent` comparison drops, and the one
        # the whole idle/active arm is run to find: with no change rows in the
        # idle capture there is no "last value" to read, so a diff that looked
        # for one would report nothing where the signal is.
        idle = dict(addrs=[PROBE_A], baseline={PROBE_A: 0x07}, rows=[])
        active = dict(addrs=[PROBE_A], baseline={PROBE_A: 0x07},
                      rows=[(12.0, PROBE_A, 0x07, 0x08)])
        with Fixture(idle, active) as (a, b):
            text = grade([a], active=b)
        self.assertIn("<- differs", text)
        self.assertIn("1 of 1 sampled", text)

    def test_the_diff_excludes_addresses_outside_the_window(self):
        idle = dict(addrs=[OUT_OF_WINDOW], baseline={OUT_OF_WINDOW: 0xFF}, rows=[])
        active = dict(addrs=[OUT_OF_WINDOW], baseline={OUT_OF_WINDOW: 0xFF},
                      rows=[(12.0, OUT_OF_WINDOW, 0xFF, 0x01)])
        with Fixture(idle, active) as (a, b):
            text = grade([a], active=b)
        # An invented difference there would be a fact about the host wearing
        # the clothes of a PD finding.
        self.assertIn("outside the host window and are not compared", text)
        self.assertIn("0 of 0 sampled", text)

    def test_an_address_only_one_capture_watched_is_not_compared(self):
        idle = dict(addrs=[SLOT0], baseline={SLOT0: 0x00}, rows=[])
        active = dict(addrs=[PROBE_A], baseline={PROBE_A: 0x00},
                      rows=[(12.0, PROBE_A, 0, 1)])
        with Fixture(idle, active) as (a, b):
            text = grade([a], active=b)
        self.assertIn("appear in one capture and not the other", text)


class RefusalTests(unittest.TestCase):
    """The refusals, each reached through `main()` so the exit code is the
    thing under test rather than the helper behind it."""

    def _run(self, argv):
        """`main()`'s exit code and stderr.

        stdout is captured and dropped as well: `main()` prints the whole
        report there, and letting it reach the runner's output would put a
        page of constructed-capture table into the middle of the suite's.
        """
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            rc = gpb.main(argv)
        return rc, err.getvalue()

    def test_the_same_file_twice_is_refused_under_two_spellings(self):
        spec_ = dict(addrs=[SLOT0], baseline={SLOT0: 0x00},
                     rows=[(5.0, SLOT0, 0x00, 0x01)])
        with Fixture(spec_) as (path,):
            rc, err = self._run([path, os.path.join(os.path.dirname(path), ".",
                                                    os.path.basename(path))])
        self.assertEqual(rc, 1)
        self.assertIn("are both", err)
        self.assertIn("nothing", err)

    def test_a_repeat_is_refused_before_any_file_is_read(self):
        # The cost the refusal names. A file that does not exist, given twice,
        # must still be refused as a repeat rather than raising: the point is
        # that the answer costs nothing, and a traceback from opening it would
        # be a different answer.
        rc, err = self._run(["/nonexistent/a.csv", "/nonexistent/a.csv"])
        self.assertEqual(rc, 1)
        self.assertIn("is given twice", err)

    def test_mark_relative_over_a_capture_with_no_marks_is_refused(self):
        # Nothing to be relative to, and grading anyway would read as "nothing
        # moved around the action" rather than "nothing was timed against it".
        with Fixture(dict(addrs=[SLOT0], baseline={SLOT0: 0x00},
                           rows=[(5.0, SLOT0, 0, 1)])) as (path,):
            rc, err = self._run([path, "--mark-relative"])
        self.assertEqual(rc, 1)
        self.assertIn("no MARK rows", err)

    def test_mark_relative_passes_over_a_capture_that_has_one(self):
        with Fixture(dict(addrs=[SLOT0], baseline={SLOT0: 0x00},
                           rows=[(12.0, SLOT0, 0, 1)],
                           marks=[(10.0, "operator: plugged in")])) as (path,):
            rc, _ = self._run([path, "--mark-relative"])
        self.assertEqual(rc, 0)

    def test_an_active_capture_that_is_also_a_given_one_is_refused(self):
        # A capture compared with itself differs nowhere, so the section would
        # report a result that is a property of the comparison.
        with Fixture(dict(addrs=[SLOT0], baseline={SLOT0: 0x00},
                           rows=[(5.0, SLOT0, 0, 1)])) as (path,):
            rc, err = self._run([path, "--active", path])
        self.assertEqual(rc, 1)
        self.assertIn("with itself", err)

    def test_the_active_refusal_catches_a_second_spelling_of_the_same_file(self):
        with Fixture(dict(addrs=[SLOT0], baseline={SLOT0: 0x00},
                           rows=[(5.0, SLOT0, 0, 1)])) as (path,):
            rc, err = self._run([path, "--active",
                                 os.path.join(os.path.dirname(path), ".",
                                              os.path.basename(path))])
        self.assertEqual(rc, 1)
        self.assertIn("with itself", err)


class SlotIndexTests(unittest.TestCase):
    """Which record an address is in, and the scope that decides it."""

    def test_an_address_in_a_paged_record_is_placed_in_it(self):
        self.assertEqual(gpb.slots_of(0x04A6), ("0x60", 0, 0x0400))
        self.assertEqual(gpb.slots_of(0x0660)[1], 1)

    def test_an_address_in_no_record_is_unplaced_rather_than_nearest(self):
        # `0x08E7` is a `0x5E` base. It is also within a `0x260` stride of the
        # `0x0400` base's third index, so an index built from the stride alone
        # would place it in a record -- inventing one, and printing an
        # unobservable address as a byte of a record. `pd-index-geometry.md`
        # 7.4 puts the `0x5E` family outside the `0x260` geometry entirely, and
        # the host does not map the page it is on.
        self.assertEqual(gpb.slots_of(OUT_OF_WINDOW), (None, None, None))
        self.assertTrue(gpb.unmapped(OUT_OF_WINDOW))

    def test_no_placed_byte_is_outside_the_window(self):
        # The relation that catches the same defect from the other side: every
        # byte the index places must be one this host can actually read. Built
        # from the reachable length per slot, which is the only way it holds
        # for slot 1, where a record starts inside the window and runs out of
        # it partway.
        for addr, placed in gpb.slot_index().items():
            self.assertFalse(gpb.unmapped(addr), f"0x{addr:04X} -> {placed}")

    def test_a_byte_past_a_truncated_record_is_not_in_it(self):
        # The specific boundary. Slot 1 of the `0x0400` record starts at
        # `0x0660` and the window ends at `0x07FF`, so `0x0800` is inside the
        # record by arithmetic and outside the window by a page.
        self.assertEqual(gpb.slots_of(SLOT1)[1], 1)
        self.assertEqual(gpb.slots_of(0x0800), (None, None, None))
        self.assertTrue(gpb.unmapped(0x0800))

    def test_no_byte_is_placed_in_two_records(self):
        index = gpb.slot_index()
        placed = list(index.values())
        self.assertEqual(len(placed), len(index),
                         "a byte was placed in two records")


class KnownAnswerTests(unittest.TestCase):
    """The tool run the way an operator runs it, on a capture built to be
    readable by eye -- so a change to its output shows up as a diff here."""

    def test_a_full_report_prints_every_section_it_promises(self):
        rows = [(12.0, SLOT0, 0x10, 0x11), (20.0, SLOT0, 0x11, 0x12)]
        with Fixture((dict(addrs=[SLOT0, PROBE_A, PROBE_B, OUT_OF_WINDOW],
                           baseline={SLOT0: 0x10, PROBE_A: 0x07,
                                     PROBE_B: 0x00, OUT_OF_WINDOW: 0xFF},
                           rows=rows, marks=[(10.0, "operator: plugged in")]),)
                ) as (path,):
            text = grade([path], mark_relative=True)
        for section in ("per-address", "last change relative to the preceding mark",
                        "map separation", "Nothing above is a register status"):
            self.assertIn(section, text)


if __name__ == '__main__':
    unittest.main()