#!/usr/bin/env python3
"""Offline checks for the 0x0436 read-only probe; no EC, no battery, no root.

Stands in for: `linux/battery-trace/remain-capacity-probe`, the Linux arm of
docs/hardware-tests/remain-capacity-0436.md. Its sibling `probe-6005.py` has a
dry run that opens no HID node; this one opens no `/dev/mem`, needs no root,
writes no capture, and takes its `power_supply` and EC answers from fixtures, so
the tool's own parsing, guarding and formatting run unmodified between them.
The tool's rules are what is under test -- nothing about what `0x0436` is. No
register has been read and no run on the laptop has happened.
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / 'remain-capacity-probe'
REPO = HERE.parent.parent

# The header the probe writes, as its own constant spells it. Read out of the
# script rather than repeated, so a column rename shows up here as a red run
# instead of as a header that quietly grew a field.
HEADER = re.search(r'^HEADER="([^"]+)"', PROBE.read_text(), re.M).group(1)

# A power_supply tree with the readings the probe cats. `charge_now` is the
# only one with an interesting value: "unknown" is what several drivers publish,
# and the probe guards it before it reaches arithmetic.
BAT0 = {'charge_now': '50000000', 'status': 'Discharging', 'capacity': '50',
        'current_now': '1000000', 'voltage_now': '12000000'}


def make_sysfs(root, **overrides):
    """The `power_supply` directory a `--sysfs-dir` names, BAT0 and AC0 under it.

    `charge_now` is overridable, which is the one reading with an interesting
    value: `unknown` is what several drivers publish.
    """
    values = dict(BAT0, **overrides)
    bat = root / 'BAT0'
    ac = root / 'AC0'
    bat.mkdir(parents=True)
    ac.mkdir()
    for name, text in values.items():
        (bat / name).write_text(text + '\n')
    (ac / 'online').write_text('0\n')
    return root


def make_reader(root, body):
    """An `--ec-reader` command: a python file printing `0xNNNN=0xNN` lines.

    Written to disk rather than shelled inline so the command the probe runs is
    the same shape `ec/tools/ecmem.py` has -- `--ec-reader CMD read <addrs...>`
    -- and the case's answers stay readable in the case.
    """
    path = root / 'fake_ecmem.py'
    path.write_text('#!/usr/bin/env python3\nimport sys\n' + body)
    return f'python3 {path}'


# One distinguishable byte pair per u16, so each column can be traced back to
# the address that was asked for it. design 0x1234, full 0x5678, current 0x9abc,
# ec_u16 0xdef0 -- no two of them alike, and none equal to another column's.
PAIR_BYTES = {0x402: 0x34, 0x403: 0x12, 0x404: 0x78, 0x405: 0x56,
              0x434: 0xbc, 0x435: 0x9a, 0x436: 0xf0, 0x437: 0xde}

# A data row is a `date -Is` timestamp in column 0, which is the only thing on
# stdout the probe writes with a comma-separated field count. Everything else
# it prints -- the header comment, the phase markers, the report -- does not
# start with a date, so this picks the rows without depending on their number.
ROW = re.compile(r'^\d{4}-\d\d-\d\dT')


class ProbeRun:
    """One probe invocation over a throwaway fixture tree."""

    def __init__(self, root, sysfs=None, reader=None, out=None, env=None):
        self.root = root
        self.sysfs = sysfs or make_sysfs(root / 'sys')
        self.reader = reader if reader is not None else make_reader(
            root, self.pairs_body(PAIR_BYTES))
        self.out = out
        self.env = env

    @staticmethod
    def pairs_body(values, rotate=0, extra_lines=(), step=0):
        """A reader printing `values` in argument order, optionally perturbed.

        `rotate` shifts the printed order by that many addresses, `extra_lines`
        emits lines that are not answers at all, and `step` changes the EC pair
        by that much on every call after the first so a series can be seen to
        fall between samples.
        """
        return (
            f'VALUES = {values!r}\n'
            f'ROTATE = {rotate!r}\n'
            f'EXTRA = {list(extra_lines)!r}\n'
            f'STEP = {step!r}\n'
            'state = 0\n'
            'if STEP:\n'
            "    marker = __file__ + '.n'\n"
            '    try:\n'
            "        state = int(open(marker).read())\n"
            '    except OSError:\n'
            '        state = 0\n'
            "    open(marker, 'w').write(str(state + 1))\n"
            'asked = [int(a, 0) for a in sys.argv[2:]]\n'
            'values = dict(VALUES)\n'
            'if state and STEP:\n'
            '    values[0x436] = (values[0x436] - STEP) & 0xff\n'
            'for line in EXTRA:\n'
            '    print(line)\n'
            'for a in asked[ROTATE:] + asked[:ROTATE]:\n'
            "    print(f'{a:#06x}={values[a]:#04x}')\n")

    def argv(self):
        args = ['bash', str(PROBE), '--dry-run', '--sysfs-dir', str(self.sysfs),
                '--ec-reader', self.reader]
        if self.out is not None:
            args.append(self.out)
        return args

    def run(self):
        env = dict(os.environ, **(self.env or {}))
        return subprocess.run(self.argv(), capture_output=True, text=True,
                              cwd=str(REPO), env=env)


class ColumnMappingTests(unittest.TestCase):
    """Issue #216: the address->column mapping is the tool's, not luck's."""

    def run_probe(self, **kwargs):
        """One dry run over a throwaway tree, for the cases with nothing to keep."""
        with tempfile.TemporaryDirectory() as tmp:
            return ProbeRun(Path(tmp), **kwargs).run()

    def test_each_column_carries_the_bytes_of_the_address_it_names(self):
        proc = self.run_probe()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = [line.split(',') for line in proc.stdout.splitlines() if ROW.match(line)]
        self.assertTrue(rows, f'no data row in the dry run:\n{proc.stdout}')
        row = rows[0]
        col = HEADER.split(',').index
        self.assertEqual(row[col('ec_0402_design')], str(0x1234))
        self.assertEqual(row[col('ec_0404_full')], str(0x5678))
        self.assertEqual(row[col('ec_0434_ma')], str(0x9abc))
        self.assertEqual(row[col('ec_u16')], str(0xdef0))
        # The hex column is the two EC bytes in the order they sit in memory,
        # low byte first, which is the order u16() and the firmware's own pair
        # helpers read them; ec_u16 beside it is the same pair as a number. The
        # two spellings differ by design and both belong to 0x0436/0x0437.
        self.assertEqual(row[col('ec_0436_0437')], '0xf0de')

    def test_a_rotated_read_is_refused_and_not_rotated(self):
        # The count is still eight, so the guard that fires can only be the key
        # check: this is the case the issue describes, where every column would
        # otherwise be committed one address out under a correct header.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'rotated.csv'
            run = ProbeRun(root, out=str(out),
                           reader=make_reader(root, ProbeRun.pairs_body(
                               PAIR_BYTES, rotate=1)))
            proc = run.run()
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('0x0402', proc.stderr)
            self.assertIn('0x0403', proc.stderr)
            self.assertFalse(out.exists())

    def test_a_diagnostic_line_among_the_values_is_refused(self):
        # An extra line makes the answer the wrong *length*, so the count guard
        # is what fires here rather than the key check. Both refuse; this case
        # exists so the "ecmem printed something extra" reading is covered
        # whichever guard catches it.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'stray.csv'
            run = ProbeRun(root, out=str(out),
                           reader=make_reader(root, ProbeRun.pairs_body(
                               PAIR_BYTES, extra_lines=['ecmem.py: note: window mapped r/o'])))
            proc = run.run()
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('got 9 of 8', proc.stderr)
            self.assertFalse(out.exists())

    def test_a_short_read_still_trips_the_count_guard_first(self):
        # The count guard predates this change and its message says more about
        # a missing line than the key check could, so it stays in front.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = ('VALUES = %r\n'
                    'for a in [int(x, 0) for x in sys.argv[2:]][:-1]:\n'
                    "    print(f'{a:#06x}={VALUES[a]:#04x}')\n" % (PAIR_BYTES,))
            proc = ProbeRun(root, reader=make_reader(root, body)).run()
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('got 7 of 8', proc.stderr)


class DryRunTests(unittest.TestCase):
    """The mode has to stay a mode: no file, no EC, no root."""

    def test_the_dry_run_writes_nothing_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / 'never-written.csv'
            proc = ProbeRun(root, out=str(out)).run()
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(out.exists(), 'the dry run opened its output path')

    def test_the_dry_run_writes_nothing_under_evidence(self):
        before = sorted(p.name for p in (REPO / 'evidence' / 'ec-watch').glob('*'))
        with tempfile.TemporaryDirectory() as tmp:
            proc = ProbeRun(Path(tmp), out='dry-run-should-not-exist.csv').run()
            self.assertEqual(proc.returncode, 0, proc.stderr)
        after = sorted(p.name for p in (REPO / 'evidence' / 'ec-watch').glob('*'))
        self.assertEqual(after, before,
                         'a dry run added a file under evidence/ec-watch/')

    def test_a_bare_output_name_resolves_under_evidence_ec_watch(self):
        # docs/hardware-tests/remain-capacity-0436.md §4 gives a bare name and
        # §7 promises the capture lands under evidence/ec-watch/ with no rename
        # step. The script cd's to the repository root, so a bare name has to
        # be resolved rather than taken literally -- see the dated correction
        # beside §7's paragraph in that document.
        with tempfile.TemporaryDirectory() as tmp:
            proc = ProbeRun(Path(tmp), out='2026-01-01-0436-capacity.csv').run()
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn(f'would write {REPO}/evidence/ec-watch/'
                          '2026-01-01-0436-capacity.csv', proc.stdout)

    def test_an_absolute_output_name_is_printed_as_given(self):
        # The path is normalised once, where the argument is resolved against
        # the repository root, so the two print sites name it directly. Printing
        # "$REPO/$OUT" instead composes the root onto an argument that already
        # carries one, and reports a path that does not exist -- which is the
        # one thing this line is for.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'absolute.csv'
            proc = ProbeRun(Path(tmp) / 'r', out=str(out)).run()
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn(f'would write {out}\n', proc.stdout)
            self.assertNotIn(f'{REPO}/{out}', proc.stdout)

    def test_a_fixture_flag_is_refused_outside_a_dry_run(self):
        # A real run must read this machine's sysfs and this EC. A flag that
        # could quietly point it somewhere else is not left in the tool.
        for flag in (['--sysfs-dir', '/tmp'], ['--ec-reader', 'true']):
            with tempfile.TemporaryDirectory() as tmp:
                proc = subprocess.run(
                    ['bash', str(PROBE), *flag, 'out.csv'],
                    capture_output=True, text=True, cwd=str(REPO))
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn('dry-run only', proc.stderr)

    def test_header_and_row_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = ProbeRun(Path(tmp)).run()
            self.assertEqual(proc.returncode, 0, proc.stderr)
            lines = proc.stdout.splitlines()
            # The resolved path is named before the capture's own first line,
            # because opening $OUT truncates whatever a previous run left there.
            self.assertIn('would write', lines[0])
            self.assertTrue(lines[1].startswith('# '))
            self.assertEqual(lines[2], HEADER)
            width = len(HEADER.split(','))
            rows = [line.split(',') for line in lines[3:] if ROW.match(line)]
            self.assertTrue(rows)
            for row in rows:
                self.assertEqual(len(row), width, row)
            for phase in ('baseline', 'discharge', 'recovery'):
                self.assertIn(f'# phase {phase} begins', lines)

    def test_rerunning_replaces_the_capture_rather_than_extending_it(self):
        # Asserted against the script's own text and labelled as such. The
        # header is opened with `>` and rows go through `tee -a`, so a second
        # run rewrites the file instead of appending to the one before it --
        # the opposite of `ec_validate.py --csv`, which §7 of the procedure
        # states. No offline run can show this at the file level: the write
        # needs a real run as root against a real machine.
        source = PROBE.read_text()
        self.assertIn('capture_header > "$OUT"', source)
        self.assertIn('tee -a "$OUT"', source)
        self.assertNotIn('tee -a "$OUT" > /dev/null', source)


class SummaryTests(unittest.TestCase):
    """The closing report, including the two paths that used to be wrong."""

    def test_charge_now_unknown_publishes_no_charge_mwh(self):
        # A driver publishing `unknown` for the whole run left the summary
        # reading a key sample() had deliberately never written, which under
        # `set -u` killed the run after a complete capture was on disk. Zero is
        # not substituted for it either: `printf '%8d'` on an empty operand
        # prints a plausible 0 -> 0 for a series no sample ever published.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sysfs = make_sysfs(root / 'sys', charge_now='unknown')
            proc = ProbeRun(root, sysfs=sysfs).run()
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('not published this phase', proc.stdout)
            self.assertNotIn('-> 0', proc.stdout)
            self.assertNotIn('0 -> 0', proc.stdout)
            # The EC columns are unaffected by sysfs publishing nothing.
            self.assertIn('ec_u16', proc.stdout)
            self.assertNotIn('moved down with charge_mwh', proc.stdout)

    def test_a_partly_published_charge_mwh_is_not_called_included(self):
        # The verdict says "charge_mwh included" only where charge_now was
        # published in every phase. A phase that published none is not a phase
        # charge_now sat flat through, so it is named instead of being folded
        # into the not-a-discharge verdict, which would be a claim about a
        # series the capture does not have.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sysfs = make_sysfs(root / 'sys')
            run = ProbeRun(root, sysfs=sysfs)
            # Wrap the fixture reader so charge_now is blanked from the second
            # sample onward: baseline has a charge_mwh and the later phases do
            # not. Wrapping rather than replacing keeps the EC answers the same.
            flicker = root / 'flicker.sh'
            flicker.write_text(
                '#!/usr/bin/env bash\n'
                f'n=$(cat {root}/n 2>/dev/null || echo 0); echo $((n+1)) > {root}/n\n'
                'if [ "$n" -lt 1 ]; then echo 50000000 > '
                f'{sysfs}/BAT0/charge_now; else echo unknown > {sysfs}/BAT0/charge_now; fi\n'
                f'exec {run.reader} "$@"\n')
            flicker.chmod(0o755)
            run.reader = str(flicker)
            run.env = {'BASELINE': '2', 'DISCHARGE': '2', 'RECOVERY': '2',
                       'STEP': '0'}
            proc = run.run()
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('charge_mwh was not published in: discharge recovery',
                          proc.stdout)
            self.assertNotIn('nothing at all, charge_mwh included', proc.stdout)
            self.assertIn('charge_mwh was published only in: baseline',
                          proc.stdout)
            self.assertIn('not the not-a-discharge verdict either', proc.stdout)
            # This branch is reached with an empty fell-list -- that is the
            # condition that got here -- so nothing it prints may name one. It
            # used to close with "What fell in those phases is above", pointing
            # a reader at a table of +0 deltas as though it held a fall: the
            # same defect this change exists to remove, reintroduced inside the
            # block it rewrites. The other three lines here were asserted and
            # passed straight over it.
            self.assertIn('in the phases that published one, and the rest '
                          'cannot be compared', proc.stdout)
            self.assertNotRegex(proc.stdout, r'what fell')

    def test_a_flat_run_is_reported_as_not_a_discharge(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = ProbeRun(Path(tmp)).run()
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('is not a discharge', proc.stdout)
            # The early `exit 0` that ends this branch is what holds each of
            # these two absences, and neither the exit status nor the verdict
            # line above distinguishes it from falling through. Deleted, a run
            # on which nothing fell prints the fell-list heading and then
            # "(charge_mwh fell; no other series did)" -- asserting the
            # opposite of what happened -- and goes on to report the
            # full-capacity bound, which this branch deliberately never
            # reaches. Both absences go red with that one line removed.
            self.assertNotIn('(charge_mwh fell; no other series did)',
                             proc.stdout)
            self.assertNotIn('ec_0436_0437 <= ec_0404_full', proc.stdout)

    def test_a_falling_ec_u16_with_a_flat_charge_mwh_does_not_claim_the_pair_fell(self):
        # The heading used to read "moved down with charge_mwh:" whenever any
        # series fell, so an ec_u16 that fell while the pack did not was listed
        # under a claim about charge_mwh -- which is what the procedure's §8
        # grades on ("the pair did not fall with the pack"). Two samples a phase
        # because a phase of one can never show a series falling.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sysfs = make_sysfs(root / 'sys')
            reader = make_reader(root, ProbeRun.pairs_body(PAIR_BYTES, step=0x40))
            proc = ProbeRun(root, sysfs=sysfs, reader=reader,
                            env={'BASELINE': '2', 'DISCHARGE': '2',
                                 'RECOVERY': '2', 'STEP': '0'}).run()
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('ec_u16', proc.stdout)
            self.assertNotIn('moved down with charge_mwh:', proc.stdout)
            self.assertIn('charge_mwh did not fall', proc.stdout)


if __name__ == '__main__':
    unittest.main()
