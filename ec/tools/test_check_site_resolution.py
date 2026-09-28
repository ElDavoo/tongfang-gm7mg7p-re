#!/usr/bin/env python3
"""Offline checks for check_site_resolution.py: no hardware, no Ghidra, and
for everything that would need a live read nothing but the committed firmware.

The oracle is split in two on purpose. The ten addresses issue #1105 names --
the `present-untested` addresses whose EC-side sites are all DPTR handoffs or
`none` cells at depth 0 -- are asserted **from the committed image** with
expected verdicts transcribed by hand from the exported listings, so the
answers do not come from the code under test. Every one of those transcriptions
cites a file a reader can open: `bank1/8886.asm` and `bank1/888C.asm` are the
pair accessors, `bank0/B939.asm` is the one-instruction store, and
`bank1/E769.asm` is the R1:R2 handoff. Everything else builds its own span
fixtures, so a case keeps testing what it was written to test if the index or
the census moves.

What the fixtures are for is the part the image cannot show: that the
half-open containment is right at its edges, that a gap reads `not exported`
rather than a name, that the PD image is filtered out rather than classified,
and that a population which matched nothing fails instead of printing an empty
table and exiting 0. A bug in any of those produces a confident wrong answer
rather than a crash, which is the failure mode worth pinning.
"""
import contextlib
import csv
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# check_site_resolution imports its siblings by bare module name, the way
# register_ref_table.py does, so the tool directory has to be on the path
# before they are loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_site_resolution', HERE / 'check_site_resolution.py')
csr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(csr)

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')
COMMITTED = HERE.parent / 'annotations' / 'site-resolution.csv'


def read_image():
    return csr.load_image(FIRMWARE)


def census():
    """(image, pd_verified, functions, rows) for the whole population."""
    d, pd = read_image()
    if d is None:
        raise AssertionError('the committed image did not load')
    functions = csr.load_functions()
    regs = csr.load_registers(csr.DEFAULT_YAML)
    return d, pd, functions, list(csr.ec_side_rows(d, regs, pd, functions))


def committed_rows():
    with open(COMMITTED, newline='') as f:
        return list(csv.DictReader(f))


# The ten addresses, each with the verdict its own exported listing gives, and
# the file that verdict was read off. Transcribed by hand from those .asm
# files, not from a run of the tool under test:
#
#   0x8886 bank1/8886.asm  `movx a,@dptr` x2           -> read
#   0x888C bank1/888C.asm  `movx @dptr,a` x2           -> write
#   0x8892 bank1/8892.asm  `movx a,@dptr` x2           -> read
#   0x889E bank1/889E.asm  `movx @dptr,a` x2           -> write
#   0xB939 bank0/B939.asm  `movx @dptr,a`              -> write
#   0xE769 bank1/E769.asm  `mov dptr,#0x420` ; mov r2,0x83 ; mov r1,0x82 ; ret
#                        -- the address is copied into R1:R2 and returned, and
#                           no movx appears in the window
TEN = {
    '0x0402': [('read', '0xB43B'), ('write', '0xDB0B'), ('write', '0xDEF1')],
    '0x0408': [('write', '0xDB0B'), ('write', '0xDEF1')],
    '0x040A': [('read', '0xAE2B'), ('write', '0xB50E'), ('read', '0xB50E')],
    '0x040C': [('read', '0xAE92'), ('write', '0xB50E')],
    '0x040E': [('write', '0xB50E'), ('read', '0xB50E')],
    '0x0410': [('write', '0xB50E')],
    '0x0420': [('unresolved-none', '0xE769')],
    '0x043A': [('read', '0xB56C'), ('read', '0xB56C'), ('read', '0xB56C')],
    '0x0733': [('write', '0x94D0')],
    '0x0735': [('write', '0x94D0'), ('write', '0x94D0')],
}


class TenAddressTests(unittest.TestCase):
    """The population issue #1105 asks about, out of the committed image."""

    @classmethod
    def setUpClass(cls):
        cls.rows = census()[3]

    def verdicts_for(self, addr):
        return [(r[6], r[7].split(' ')[0]) for r in self.rows
                if f'0x{r[0]:04X}' == addr]

    def test_each_of_the_ten_matches_its_transcribed_verdicts(self):
        for addr, expected in sorted(TEN.items()):
            with self.subTest(addr=addr):
                self.assertEqual(self.verdicts_for(addr), expected)

    def test_the_transcribed_population_is_exactly_ten_addresses(self):
        # The issue's own table, checked against the census. Its population is
        # "every EC-side site is a DPTR handoff or a `none` cell", which at
        # depth 1 is exactly: no row of the address carries a *direct*
        # direction, because a direct site class is the same label at both
        # depths. Per address, not per row -- 0x043F has an unresolved site
        # *and* a direct write, so it is not in this population. If a new
        # address joined, the table above would silently stop covering it.
        classes = {}
        for row in self.rows:
            classes.setdefault(f'0x{row[0]:04X}', set()).add(row[5])
        self.assertEqual(
            sorted(TEN),
            sorted(a for a, seen in classes.items()
                   if not seen.intersection(csr.RESOLVED)))

    def test_every_handoff_site_names_a_callee_and_its_function(self):
        for row in self.rows:
            if row[5].startswith('handed'):
                with self.subTest(addr=f'0x{row[0]:04X}', off=row[2]):
                    self.assertIsNotNone(row[8], 'a handoff row with no callee')
                    self.assertTrue(row[9], 'a handoff row with no callee name')

    def test_the_five_callees_are_the_exported_accessors(self):
        # The join on the *callee* side is a second join, and this is what it
        # has to reach. Restricted to the ten: the wider population reaches
        # other callees, and 0x0420 has none at all because its handoff is
        # across a `ret` in R1:R2 rather than an lcall.
        seen = {}
        for row in self.rows:
            if row[8] is not None and f'0x{row[0]:04X}' in TEN:
                seen.setdefault(f'0x{row[8]:04X}', row[9])
        self.assertEqual(seen, {
            '0x8886': '0x8886 read_xdata_pair_to_r1r2',
            '0x888C': '0x888C write_r1r2_to_xdata_pair',
            '0x8892': '0x8892 read_xdata_pair_to_r3r4',
            '0x889E': '0x889E write_r3r4_to_xdata_pair',
            '0xB939': '0xB939 store_a_to_dptr_b939',
        })

    def test_0420_is_the_r1r2_handoff_and_never_a_read_or_a_store(self):
        rows = [r for r in self.rows if r[0] == 0x0420]
        self.assertEqual(len(rows), 1, '0x0420 has one EC-side site')
        off, region, runtime, depth1, res, func = (rows[0][2], rows[0][3],
                                                   rows[0][4], rows[0][5],
                                                   rows[0][6], rows[0][7])
        self.assertEqual((region, f'0x{runtime:04X}'), ('bank1', '0xE779'))
        self.assertEqual(res, 'unresolved-none')
        self.assertNotIn('read', depth1)
        self.assertNotIn('write', depth1)
        self.assertIsNone(rows[0][8], 'the R1:R2 handoff is not an lcall')
        self.assertEqual(func,
                         '0xE769 clamp_r2r1_to_0420_above_3c0b')

    def test_the_0733_and_0735_sites_are_the_named_copy_routine(self):
        for addr in ('0x0733', '0x0735'):
            for row in self.rows:
                if f'0x{row[0]:04X}' == addr:
                    with self.subTest(addr=addr, off=row[2]):
                        self.assertEqual(
                            row[7], '0x94D0 copy_code_table_into_0730_07a7')
                        self.assertEqual(row[6], 'write')
                        self.assertEqual(row[9], '0xB939 store_a_to_dptr_b939')


class ResolutionWarrantTests(unittest.TestCase):
    """Rule 3's population: what a site is worth once it has been found."""

    @classmethod
    def setUpClass(cls):
        cls.rows = census()[3]

    def resolutions_by_addr(self):
        out = {}
        for row in self.rows:
            out.setdefault(f'0x{row[0]:04X}', []).append(row[6])
        return out

    def test_only_0420_rests_entirely_on_unresolved_sites(self):
        # The number rule 3 is refused over, measured rather than asserted:
        # one address out of the whole `present-untested` population, and it
        # is the one the write-up names.
        unresolved = {a for a, rs in self.resolutions_by_addr().items()
                      if not any(r in csr.RESOLVED for r in rs)}
        self.assertEqual(unresolved, {'0x0420'})

    def test_the_population_is_not_vacuous(self):
        # A population function that matched nothing would satisfy the case
        # above by finding no violators at all.
        self.assertGreater(len(self.resolutions_by_addr()), 100)
        self.assertGreater(len(self.rows), len(self.resolutions_by_addr()))

    def test_the_two_unresolved_shapes_stay_apart(self):
        # A handoff is positive evidence the address is passed somewhere; a
        # `none` cell is not evidence of anything. Collapsing them would let
        # the first launder the second.
        unresolved = [r for r in self.rows if r[6].startswith('unresolved')]
        self.assertTrue(unresolved)
        for row in unresolved:
            with self.subTest(addr=f'0x{row[0]:04X}', off=row[2]):
                self.assertIn(row[6], (csr.UNRESOLVED_HANDOFF,
                                       csr.UNRESOLVED_NONE))
        self.assertTrue(any(r[6] == csr.UNRESOLVED_NONE for r in unresolved))
        self.assertTrue(any(r[6] == csr.UNRESOLVED_HANDOFF
                            for r in unresolved))

    def test_a_handoff_that_resolves_is_a_warrant_and_a_none_cell_is_not(self):
        # The two sides of the rule, from the committed image rather than from
        # a fixture: 0x043A's three handoffs all resolve to reads, and
        # 0x0420's single site resolves to nothing.
        for row in self.rows:
            if row[0] == 0x043A:
                self.assertEqual(row[6], 'read')
        self.assertEqual(
            [r[6] for r in self.rows if r[0] == 0x0420],
            [csr.UNRESOLVED_NONE])

    def test_the_mode_pl_defaults_block_is_write_only(self):
        # Settles the question the plan left open, and it settles it against
        # the note's own sentence: every EC-side site of the twelve-byte
        # block is a store, so the D-state byte is written and not read.
        block = ('0x0730', '0x0731', '0x0732', '0x0733',
                 '0x0734', '0x0735', '0x0736', '0x0737',
                 '0x07A7', '0x07A8', '0x07A9', '0x07AA')
        seen = {a: rs for a, rs in self.resolutions_by_addr().items()
                if a in block}
        self.assertEqual(sorted(seen), sorted(block))
        for addr, res in sorted(seen.items()):
            with self.subTest(addr=addr):
                self.assertEqual(set(res), {'write'})


class ContainmentJoinTests(unittest.TestCase):
    """The join this file exists for, on spans built for the case."""

    def setUp(self):
        self.spans = {
            'bank1': sorted({0xB000: (0xB010, 'outer_routine'),
                             0xB100: (0xB110, 'inner_routine')}.items()),
            'common': sorted({0x0500: (0x0510, 'common_routine')}.items()),
        }

    def test_a_site_inside_a_known_export_names_it(self):
        self.assertEqual(csr.containing(self.spans, 'bank1', 0xB004),
                         '0xB000 outer_routine')

    def test_the_entry_byte_is_inside_and_the_last_byte_is_not(self):
        # The half-open range is what "the function that holds this site"
        # means, and both edges are where an off-by-one would land.
        self.assertEqual(csr.containing(self.spans, 'bank1', 0xB000),
                         '0xB000 outer_routine')
        self.assertEqual(csr.containing(self.spans, 'bank1', 0xB010),
                         csr.NOT_EXPORTED)

    def test_a_site_in_a_gap_reads_not_exported(self):
        # Not "no function contains it": the index is a census of *named,
        # exported* functions, so a gap is a gap in the exports.
        self.assertEqual(csr.containing(self.spans, 'bank1', 0xB080),
                         csr.NOT_EXPORTED)

    def test_a_site_in_a_program_with_no_rows_reads_not_exported(self):
        self.assertEqual(csr.containing(self.spans, 'bank0', 0x8000),
                         csr.NOT_EXPORTED)

    def test_a_callee_is_looked_for_in_the_callers_bank_then_in_common(self):
        self.assertEqual(csr.callee_function(self.spans, 'bank1', 0xB004),
                         '0xB000 outer_routine')
        self.assertEqual(csr.callee_function(self.spans, 'bank1', 0x0504),
                         '0x0500 common_routine')
        self.assertEqual(csr.callee_function(self.spans, 'bank1', 0x7000),
                         csr.NOT_EXPORTED)

    def test_the_pd_image_region_maps_onto_the_pd_program(self):
        # The one name translation the join needs, and it is load-bearing:
        # without it every PD-image site would read `not exported` for the
        # wrong reason and the error would look like a census result.
        self.assertEqual(csr.PROGRAM_FOR_REGION['pd-image'], 'pd')
        with open(csr.INDEX_CSV, newline='') as f:
            programs = {r['program'] for r in csv.DictReader(f)}
        for region, program in csr.PROGRAM_FOR_REGION.items():
            with self.subTest(region=region):
                self.assertIn(program, programs)

    def test_a_row_with_no_size_is_skipped_rather_than_guessed_at(self):
        # A zero-length span would swallow nothing and hide the row's real
        # extent, so the load has to drop it rather than keep an empty one.
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / 'index.csv'
            index.write_text(
                'program,addr,name,size\n'
                'bank1,B000,sized_routine,16\n'
                'bank1,B100,unsized_routine,\n'
                'bank1,B200,zero_sized_routine,0\n')
            functions = csr.load_functions(str(index))
        self.assertEqual(csr.containing(functions, 'bank1', 0xB004),
                         '0xB000 sized_routine')
        self.assertEqual(csr.containing(functions, 'bank1', 0xB104),
                         csr.NOT_EXPORTED)
        self.assertEqual(csr.containing(functions, 'bank1', 0xB204),
                         csr.NOT_EXPORTED)

    def test_the_committed_index_is_loaded_for_every_program(self):
        functions = csr.load_functions()
        for program in ('common', 'bank0', 'bank1', 'pd'):
            with self.subTest(program=program):
                self.assertTrue(functions.get(program))


class PopulationTests(unittest.TestCase):
    """Which addresses the census covers, and which sites it drops."""

    @classmethod
    def setUpClass(cls):
        cls.d, cls.pd, cls.functions, cls.rows = census()

    def test_no_pd_image_site_is_classified(self):
        # The census is the EC-side population. A PD site reaching the
        # `resolution` column would be a direction for another program's
        # byte, which is a category error rather than a measurement.
        for row in self.rows:
            with self.subTest(addr=f'0x{row[0]:04X}', off=row[2]):
                self.assertNotEqual(row[3], 'pd-image')

    def test_every_row_is_present_untested(self):
        names = {r['name'] for r in csr.load_registers(csr.DEFAULT_YAML)
                 if r.get('status', '').startswith(csr.COUNT_WARRANTED)}
        for row in self.rows:
            with self.subTest(addr=f'0x{row[0]:04X}'):
                self.assertIn(row[1], names)

    def test_the_site_count_agrees_with_the_direct_scan(self):
        # The reconciliation `register_ref_table.py` does for its own table,
        # in the one direction this file could quietly break: a site dropped
        # by the PD filter would leave every tally short without failing.
        import collections
        import yaml
        import trace_xdata_refs as txr
        want = collections.Counter()
        for entry in csr.load_registers(csr.DEFAULT_YAML):
            status = entry.get('status', '')
            if not status.startswith(csr.COUNT_WARRANTED):
                continue
            addrs = entry['addr'] if isinstance(entry['addr'], list) \
                else [entry['addr']]
            for addr in addrs:
                want[addr] = sum(
                    1 for o in txr.sites_for(self.d, addr)
                    if txr.region_of(o, self.pd)[0] != 'pd-image')
        got = collections.Counter(r[0] for r in self.rows)
        self.assertEqual(dict(got), {a: c for a, c in want.items() if c})
        self.assertEqual(sum(got.values()), sum(want.values()))

    def test_a_suffixed_present_untested_is_still_censused(self):
        # `present-untested-DO-NOT-WRITE-BLIND` is the same value with a
        # warning on it; the suffix must not take the address out of the
        # census, or the value underneath it would stop being checked.
        self.assertEqual(
            len(csr.population([{'name': 'S', 'addr': 0x043E,
                                 'status': 'present-untested'
                                          '-DO-NOT-WRITE-BLIND'}])),
            1)


class CommittedCsvTests(unittest.TestCase):
    """The committed table, and the CLI that holds it."""

    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, str(HERE / 'check_site_resolution.py'), *args],
            capture_output=True, text=True, check=False)

    def test_check_passes_byte_for_byte_against_the_committed_csv(self):
        proc = self.run_tool('--check')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('match a fresh census', proc.stdout)

    def test_check_fails_on_a_doctored_committed_csv(self):
        # A check that has never been seen to refuse is not evidence of
        # anything, and this one is a byte comparison, so the refusal has to
        # be shown as well as the pass. The doctored copy is built in a
        # temporary directory and handed over with `--committed`, because a
        # check that could only be exercised by editing the committed file is
        # a check nobody runs twice.
        with open(COMMITTED, newline='') as f:
            original = f.read()
        doctored = original.replace('unresolved-none', 'unresolved-handoff', 1)
        self.assertNotEqual(doctored, original, 'the fixture changed nothing')
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / 'site-resolution.csv'
            stub.write_text(doctored)
            proc = self.run_tool('--check', '--committed', str(stub))
        self.assertEqual(proc.returncode, 1)
        self.assertIn('differs', proc.stderr)
        # And the committed file itself is untouched by having refused.
        with open(COMMITTED, newline='') as f:
            self.assertEqual(f.read(), original)

    def test_the_committed_csv_has_the_header_and_the_ten(self):
        with open(COMMITTED, newline='') as f:
            reader = csv.DictReader(f)
            self.assertEqual(tuple(reader.fieldnames), csr.COLUMNS)
            addrs = {r['addr'] for r in reader}
        for addr in TEN:
            self.assertIn(addr, addrs)

    def test_a_buffer_that_is_not_this_dump_is_refused(self):
        # Every region would be `unknown` and the table would read as a claim
        # about the real image.
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / 'not-the-dump.bin'
            stub.write_bytes(bytes(0x30000))
            proc = self.run_tool(str(stub))
        self.assertEqual(proc.returncode, 1)
        self.assertIn('ITE8850-PD', proc.stderr)

    def test_self_test_passes(self):
        proc = self.run_tool('--self-test')
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn('self-test passed', proc.stdout)

    def test_the_default_output_carries_the_calibration_caveat(self):
        # A site this tool calls unresolved is still "not found by this
        # method", and the sentence that says so has to be on the run that
        # prints the cell rather than only in the docstring.
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('not found by this method', proc.stdout)
        self.assertIn('0x07B9', proc.stdout)
        self.assertIn('Nothing is measured on', proc.stdout)

    def test_the_summary_carries_the_calibration_caveat_too(self):
        proc = self.run_tool('--summary')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('not found by this method', proc.stdout)

    def test_the_summary_names_the_one_address_with_no_resolution(self):
        proc = self.run_tool('--summary')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [ln for ln in proc.stdout.splitlines()
                 if 'NO RESOLUTION' in ln]
        self.assertEqual(lines, ['0x0420  NO RESOLUTION unresolved-none 1'])


if __name__ == '__main__':
    unittest.main()
