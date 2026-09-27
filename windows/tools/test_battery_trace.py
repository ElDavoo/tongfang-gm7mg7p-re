#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

battery_trace.py imports ecrw, which binds kernel32 at import time and so only
loads on Windows, and shells out to powershell for its WMI line. The fakes
below stand in for both: windows/tools/ecrw_fake.py is installed by assignment,
so this suite is not a party to the setdefault ordering accident
docs/findings.md §16 records, and only subprocess.run is replaced so the tool's
own wmi() -- the six-token parse and the dict(zip(keys, ...)) the row is built
from -- runs under test too.

What is worth having a suite for is narrow. The tool has none, and its
function-local `cols` is the thing two committed captures and every reader of
them depend on. The pieces that are load-bearing:

  * the column set, twice over -- once against the tool writing it and once
    against the two committed captures that carry it, so a rename in the tool
    and a watch byte that moved are separate failures;
  * a row carrying both current sources, which is the property
    docs/findings.md §4a's retraction was about and the tool's own docstring
    gives as the reason it logs two;
  * the fh.tell() == 0 branch, which decides whether a header is written and
    has never run against a pre-existing file in any committed run.

The other half of the suite is a census: every file in evidence/battery-traces/
is named, classified, and checked to be on the column set its class claims. A
file that arrived with a shape nobody classified fails instead of being skipped,
which is the difference between a check and a loop that quietly reads two of
eight.

Nothing here is hardware evidence. No EC is opened, no register is read back,
and every fixture value is either a byte taken from a committed row or a token
from a canned WMI line. The append-to-a-mismatched-header case asserts today's
behaviour and says in a comment that the gap is unfixed; it is a record of a
defect, not a handling of one.

This suite reads committed inputs, evidence/battery-traces/ in particular, so
it has to run from inside the repository. tools/run-tests.sh cds to the repo
root, and a copy of this file outside the tree will not find them.
"""
import contextlib
import csv
import importlib.util
import io
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).parent
REPO = TOOLS.parent.parent
TRACES = REPO / "evidence" / "battery-traces"

# A run that samples exactly once. --seconds 0 will not do: the tool's break is
# `if args.seconds and time.time() - t0 >= args.seconds` (battery_trace.py:101),
# so a zero is falsy and the loop never ends. The charge-target suite can pass 0
# because that tool tests the comparison without the guard. Clock's step and this
# budget are the same 0.1, so the first pass's check is already true.
#
# The phase label is the one the committed row below carries, so a row this
# suite builds can be compared with it field for field.
BASE = ('--seconds', '0.1', '--phase', 'biosdefaults_nohdmi_stationary')

# battery_trace.py builds this list inside main(), so it cannot be imported and
# checked against itself. The copy here is the assertion, and it fails on a
# rename in the tool -- which is the point: these are the columns the committed
# captures and anything reading them depend on.
COLS = ["ts", "phase", "ac", "charging", "capacity", "remaining_mwh",
        "wmi_rate_mw", "ec_current_ma", "ec_voltage_mv",
        "ec_07a6", "ec_07b9", "ec_07d0", "ec_07d1", "ec_07cc"]

# The eight committed captures, classified. Named rather than globbed because a
# glob over the directory would collect whatever lands in it, and the point of
# the census is that a file nobody has classified is a failure rather than
# something quietly passed over.
#
# CURRENT is the two this tool's column set was written for. LEGACY is the
# three on a different tool's shapes: the 2026-09-09 captures predate the phase
# column and the ec_* readings, and 2026-09-17-limit-pair.csv carries a `#`
# annotation as its first line, so its header is on row 1. Two of the three are
# still written by a script in the tree -- LEGACY_WRITER below, which is the
# correction that keeps this a list of provenance rather than of stale files.
# CHARGE_TARGET is the charge-target tool's, checked against its own pinned set
# by test_charge_target_test.py.
CURRENT = ("2026-09-18-windows-stationary.csv",
           "2026-09-19-windows-bios-defaults.csv")
LEGACY = ("2026-09-09-profiles.csv",
          "2026-09-09-threshold80.csv",
          "2026-09-17-limit-pair.csv")
CHARGE_TARGET_GLOB = "2026-09-21-0522-*.csv"
LIMIT_PAIR = "2026-09-17-limit-pair.csv"
BIOS_DEFAULTS = "2026-09-19-windows-bios-defaults.csv"

# The committed header of each legacy capture a script in this tree still
# writes, byte for byte, and the line it sits on. `linux/battery-trace/
# battery-trace` emits 2026-09-09-threshold80.csv's ten columns and nothing has
# replaced it; `limit-pair-test` emits 2026-09-17-limit-pair.csv's eleven and,
# run with no argument, writes them into evidence/battery-traces/ itself. The
# column set moved from a Python tool to a shell script; it did not leave the
# repository, which is the reason these are not "superseded designs nobody
# produces". 2026-09-09-profiles.csv is the one with no writer here at all.
LEGACY_WRITER = {
    "2026-09-09-threshold80.csv": ("linux/battery-trace/battery-trace", 0),
    "2026-09-17-limit-pair.csv": ("linux/battery-trace/limit-pair-test", 1),
}

# The fixture's bytes and its WMI tokens are the first data row of
# evidence/battery-traces/2026-09-19-windows-bios-defaults.csv, so a row this
# suite builds reproduces a committed measurement instead of a number written
# here. The map is keyed by byte address because 0x0434 and 0x0438 are read as
# little-endian pairs, and a big-endian u16 has to be able to fail on the value.
REGS = {
    0x0434: 0xA4, 0x0435: 0x06,   # 1700 mA
    0x0438: 0x52, 0x0439: 0x40,   # 16466 mV
    0x07A6: 0x28,                 # 0x29 in the stationary capture, 0x28 here
    0x07B9: 0x00, 0x07D0: 0x00, 0x07D1: 0x00, 0x07CC: 0x00,
}

# The six tokens WMI_QUERY formats, in the order wmi() zips them onto its keys.
# AC in, charging, so discharging is 0 -- that column the current tool does not
# log at all, which is one of the drifts the census below records.
WMI_TOKENS = "1 1 0 19152 27992 63"

# The ACPI rate the committed row records, kept as a name because it is the
# second current source and the case below asserts it is the *other* one.
RATE_MW = 27992


def rows_of(name):
    return list(csv.reader((TRACES / name).read_text().splitlines()))


def header_line(name, row=0):
    """One line of a capture verbatim, which is the bytes rather than a re-parse.

    A csv.reader cell list is the parsed shape; this is the text, and the
    writer below is a shell script whose header is one `echo` of the same
    string. Comparing the two is therefore a byte-identity claim, not a
    question of how either side is quoted.
    """
    return (TRACES / name).read_text().splitlines()[row]


class FakeEc:
    """A byte map, so the tool's own u16 is the one under test.

    Every read goes through the map rather than a scripted table, because the
    two u16 readings and the five WATCH bytes are read by the same code path as
    the value the CSV row is built from -- there is nothing here to script and
    nothing written. The context manager is here rather than incidental, since
    the tool opens the device with `with Ec() as ec:`, and __exit__ returns
    None so a failure partway through still propagates.
    """

    def __init__(self):
        self.regs = dict(REGS)
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read(self, addr):
        self.reads += 1
        return self.regs.get(addr, 0x00)


class FakeWmi:
    """The canned WMI line, one call per loop pass.

    Not scripted per call index the way the charge-target suite's is: nothing
    here has a boundary to inject a failure at, and a fake that can raise is a
    fixture shape this suite would never exercise. The count is kept so a run
    that sampled more than once is visible rather than inferred from the row
    count.
    """

    def __init__(self):
        self.calls = 0

    def run(self, argv, **kw):
        self.calls += 1
        return types.SimpleNamespace(stdout=WMI_TOKENS)


class Clock:
    """A counter for time.time, so --seconds 0.1 buys exactly one loop pass.

    The tool takes t0 at the first call and the seconds check at the second, so
    a step equal to the budget breaks after one iteration. `slept` records what
    the run asked to sleep for, which is how "one pass and no interval" is
    asserted rather than counted out.
    """

    def __init__(self, step=0.1):
        self.t = 0.0
        self.step = step
        self.slept = []

    def time(self):
        self.t += self.step
        return self.t

    def sleep(self, s):
        self.slept.append(s)


# The tool's own `from ecrw import Ec, EcError` has to resolve, and the directory
# is the import root whether or not the runner was started from here.
sys.path.insert(0, str(TOOLS))

# The shared offline stand-in for `ecrw` (windows/tools/ecrw_fake.py), installed
# by assignment rather than setdefault so nothing here can inherit a sibling's
# shape whichever of the two ran first. It supplies the names the tool binds at
# import; the class with the bytes is patched over the tool's `Ec` below.
import ecrw_fake  # noqa: E402  (needs the sys.path entry above)
ecrw_fake.install()

spec = importlib.util.spec_from_file_location(
    'battery_trace', TOOLS / 'battery_trace.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class BatteryTraceTests(unittest.TestCase):
    def run_tool(self, argv, ec=None, clock=None, wmi=None):
        ec = ec if ec is not None else FakeEc()
        clock = clock if clock is not None else Clock()
        wmi = wmi if wmi is not None else FakeWmi()
        out, err = io.StringIO(), io.StringIO()
        with patch.object(tool, 'Ec', lambda: ec), \
             patch.object(tool, 'subprocess',
                          types.SimpleNamespace(run=wmi.run)), \
             patch.object(tool.time, 'time', clock.time), \
             patch.object(tool.time, 'sleep', clock.sleep), \
             contextlib.redirect_stdout(out), \
             contextlib.redirect_stderr(err):
            rc = tool.main(list(argv))
        return rc, ec, clock, wmi, out.getvalue(), err.getvalue()

    # 1. What the tool writes to a fresh file. A rename of any column in `cols`
    #    lands here first, and the committed-file check below is the one that
    #    says which captures stopped matching.
    def test_the_header_on_a_fresh_file_is_the_pinned_column_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, _, clock, wmi, _, _ = self.run_tool(BASE + ('--csv', str(path)))
            rows = list(csv.reader(path.read_text().splitlines()))
            self.assertEqual(rc, 0)
            self.assertEqual(rows[0], COLS)
            self.assertEqual(len(rows), 2)          # header, and the one sample
            self.assertEqual(len(rows[1]), len(COLS))
            # Breaks on the seconds check before the interval is ever slept,
            # which is the "exactly one pass" being true rather than assumed.
            self.assertEqual(clock.slept, [])
            self.assertEqual(wmi.calls, 1)

    # 2. The same set against the two committed captures that carry it. Read
    #    off the files rather than off the tool, so a tool that still agrees
    #    with itself while the evidence has moved fails here.
    def test_the_two_committed_captures_are_on_that_column_set(self):
        # A loop over a glob that matched nothing would pass vacuously, which
        # is the one thing it must not do.
        self.assertTrue(CURRENT, "no committed capture named to check the "
                                 "column set of")
        for name in CURRENT:
            with self.subTest(trace=name):
                self.assertEqual(rows_of(name)[0], COLS)

    # 3. The census: every file in the directory is in exactly one class, and
    #    the classes are the whole directory. A file that fits none of them
    #    fails; one claimed twice fails; a named file that is not on disk
    #    fails, which is the direction that would otherwise let a class quietly
    #    shrink while still looking complete.
    def test_every_committed_capture_is_classified_exactly_once(self):
        committed = {p.name for p in TRACES.iterdir()}
        groups = {'CURRENT': set(CURRENT),
                  'LEGACY': set(LEGACY),
                  'CHARGE_TARGET': {p.name for p in
                                    TRACES.glob(CHARGE_TARGET_GLOB)}}
        for label, group in groups.items():
            with self.subTest(group=label):
                # A glob that stopped matching, or a class reduced to nothing,
                # must not be able to make the union below look complete.
                self.assertTrue(group, f"{label} classifies no file")
                self.assertFalse(
                    group - committed,
                    f"{label} names a file not in evidence/battery-traces/: "
                    f"{sorted(group - committed)}")
        for a, b in (('CURRENT', 'LEGACY'),
                     ('CURRENT', 'CHARGE_TARGET'),
                     ('LEGACY', 'CHARGE_TARGET')):
            with self.subTest(pair=f'{a}/{b}'):
                self.assertFalse(
                    groups[a] & groups[b],
                    f"{sorted(groups[a] & groups[b])} is claimed by both "
                    f"{a} and {b}")
        self.assertEqual(
            groups['CURRENT'] | groups['LEGACY'] | groups['CHARGE_TARGET'],
            committed,
            "evidence/battery-traces/ holds a file no class above names. Add it "
            "to one, and say which column set it is on -- do not let a glob "
            "past it.")

    # 4. The classification is a claim about the files and not about their
    #    names: none this tool did not write may be on its column set.
    def test_no_capture_this_tool_did_not_write_is_on_its_column_set(self):
        for name in LEGACY:
            with self.subTest(trace=name):
                self.assertNotEqual(rows_of(name)[0], COLS)
        for name in sorted(p.name for p in TRACES.glob(CHARGE_TARGET_GLOB)):
            with self.subTest(trace=name):
                # The charge-target tool's header, held by its own suite; here
                # only that it is not this tool's.
                self.assertNotEqual(rows_of(name)[0], COLS)

    # 5. The two legacy captures a script in the tree still writes, held to
    #    that writer's own text rather than to a date. `in` and not a line
    #    number, so the claim is that the header the capture carries is
    #    byte-identical to one the writer emits -- which is what makes LEGACY a
    #    list of provenance -- and it survives the script being edited above or
    #    below that line.
    def test_the_legacy_captures_the_shell_tools_still_write_keep_their_headers(self):
        for name, (script, row) in sorted(LEGACY_WRITER.items()):
            with self.subTest(trace=name):
                source = (REPO / script).read_text()
                self.assertIn(
                    header_line(name, row), source,
                    f"{script} no longer emits {name}'s header. If it was "
                    f"superseded, move the capture out of LEGACY and say what "
                    f"writes its shape now; a capture whose writer has drifted "
                    f"is a capture whose columns nothing is holding.")
        # And the census above is live rather than archival: run with no
        # argument, limit-pair-test writes a dated capture into this very
        # directory, and a human doing that today produces a file the census
        # rejects until it is classified. The default path is read as text --
        # no script here is run, and nothing is written to.
        self.assertIn("evidence/battery-traces/",
                      (REPO / "linux" / "battery-trace" /
                       "limit-pair-test").read_text())

    # 6. 2026-09-17-limit-pair.csv, recorded rather than passed over. Its first
    #    line is an annotation, so row 0 is not a header -- which is the
    #    assumption test_charge_target_test.py's
    #    test_the_committed_0522_traces_share_that_header encodes for the three
    #    files it reads, and why that case could never have covered it.
    def test_the_limit_pair_capture_is_recorded_not_skipped(self):
        lines = (TRACES / LIMIT_PAIR).read_text().splitlines()
        rows = list(csv.reader(lines))
        self.assertTrue(
            lines[0].startswith("#"),
            f"{LIMIT_PAIR} no longer opens with a # annotation; if it was "
            f"regenerated on a current column set, reclassify it rather than "
            f"leaving a claim here that no longer holds")
        # The exact expression the sibling case uses over its own three files,
        # run here to show what it would return for this one.
        self.assertNotEqual(next(csv.reader(lines)), COLS)
        # The header is on row 1 and is a header: a data row's first field is a
        # timestamp, and a shape no current code emits, so it is held as what
        # it is rather than compared to a column set this tool still writes.
        self.assertEqual(rows[1][0], "ts")
        self.assertEqual(len(rows[1]), len(rows[2]))
        self.assertNotEqual(rows[1], COLS)

    # 7. The watch columns, against the committed evidence rather than the tool
    #    against itself: WATCH is the tool's constant, and the two captures
    #    this tool wrote end on the same five columns. A byte added or renamed
    #    moves both, and the files then mismatch.
    def test_the_watch_columns_cover_the_watch_set_in_order(self):
        watch_cols = [f"ec_{a:04x}" for a in tool.WATCH]
        self.assertTrue(COLS[-len(watch_cols):] == watch_cols,
                        f"{COLS[-len(watch_cols):]} is not {watch_cols}")
        # Those five are the only hex-shaped columns in the set, which is what
        # keeps the two fixed ec_* readings out of the watch tail by assertion
        # rather than by their position.
        self.assertEqual([c for c in COLS if re.fullmatch(r"ec_[0-9a-f]{4}", c)],
                         watch_cols)
        for name in CURRENT:
            with self.subTest(trace=name):
                self.assertEqual(rows_of(name)[0][-len(watch_cols):],
                                 watch_cols)

    # 8. The two-source discipline, at the row level. The tool exists to log
    #    both readings side by side because the ACPI one is cached and
    #    periodically reads zero, and a cache artefact written up as an
    #    enforced charge limit is what docs/findings.md §4a retracted. The
    #    assertion is per source, never an agreement between them: what makes
    #    the property real is that the two come from two reads, and a row that
    #    satisfied it with one value would be the failure.
    def test_a_sample_row_carries_both_current_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, _, _, _, _, _ = self.run_tool(BASE + ('--csv', str(path)))
            rows = list(csv.reader(path.read_text().splitlines()))
            self.assertEqual(rc, 0)
            row = dict(zip(rows[0], rows[1]))
            # The EC reading, worked out from the two bytes here rather than by
            # calling the tool's own u16, so a u16 that read big-endian fails on
            # the value instead of agreeing with itself. 1700 mA is what
            # 2026-09-19-windows-bios-defaults.csv's first row recorded.
            self.assertEqual(int(row['ec_current_ma']),
                             REGS[0x0434] | (REGS[0x0435] << 8))
            self.assertEqual(int(row['ec_current_ma']), 1700)
            # The ACPI reading, the rate token the faked WMI line carried, from
            # a different read entirely.
            self.assertEqual(int(row['wmi_rate_mw']), RATE_MW)
            # Different numbers, and the two have not collapsed into one
            # column. The inequality is a property of the fixture rather than
            # of the tool -- it is here so a row carrying one value in both
            # columns cannot pass as a satisfied two-source discipline.
            self.assertNotEqual(int(row['wmi_rate_mw']),
                                int(row['ec_current_ma']))
            # And the whole row past the timestamp is the committed row's,
            # reproduced from a byte map and a canned WMI line.
            self.assertEqual(rows[1][1:], rows_of(BIOS_DEFAULTS)[1][1:])

    # 9. fh.tell() == 0 decides whether a header is written, so a second run
    #    into the same file must not add one.
    def test_appending_does_not_repeat_the_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, _, _, _, _, _ = self.run_tool(BASE + ('--csv', str(path)))
            rc2, _, _, _, _, err = self.run_tool(BASE + ('--csv', str(path)))
            rows = list(csv.reader(path.read_text().splitlines()))
            self.assertEqual((rc, rc2), (0, 0))
            self.assertEqual(err, "")
            self.assertEqual(rows[0], COLS)
            self.assertEqual(rows.count(COLS), 1)
            self.assertEqual(len(rows), 3)          # header, and two samples

    # 10. The gap, pinned as today's behaviour and not as a handling of it.
    #    main() tests only whether the file is empty and never compares an
    #    existing header with cols, so appending to a file whose columns are
    #    something else interleaves this tool's rows into it, silently, with
    #    exit 0. 2026-09-17-limit-pair.csv is the committed file that would be
    #    corrupted, and what is asserted is the damage. Nothing here guards
    #    against it, and the fix -- refusing the append on a mismatched header
    #    -- is a behaviour change to a tool no committed run exercises, so it
    #    belongs to its own issue rather than to this suite.
    #
    #    Closing the gap therefore turns this case red. That is the record
    #    turning over, not a defect in the fix: rewrite it to assert the
    #    refusal, do not delete it, or the next change re-opens the gap in
    #    silence.
    def test_appending_to_a_foreign_header_interleaves_it_anyway(self):
        lines = (TRACES / LIMIT_PAIR).read_text().splitlines()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            # A copy of the file's first two lines. The committed evidence is
            # read, never written to.
            path.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
            rc, _, _, _, _, err = self.run_tool(BASE + ('--csv', str(path)))
            rows = list(csv.reader(path.read_text().splitlines()))
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            # The annotation and the header it annotated are untouched ...
            self.assertEqual(rows[0], next(csv.reader(lines[:1])))
            self.assertEqual(rows[1], next(csv.reader(lines[1:2])))
            # ... and the row appended after them is this tool's, on a
            # different column set. Column 4 is `status` in the header the
            # file was written with and `charging` in this row, so a reader
            # that indexed by that header reads the wrong field out of every
            # row the append added.
            self.assertNotEqual(rows[1], rows[2])
            self.assertEqual(rows[1][3], "status")
            self.assertEqual(rows[2][3], "1")
            self.assertEqual(rows[2][1:], rows_of(BIOS_DEFAULTS)[1][1:])


if __name__ == '__main__':
    unittest.main()
