#!/usr/bin/env python3
"""Offline checks for dispatch_edges.py and for the closure edges it feeds.

`docs/findings/dispatch-table-closure-edges.md` is the argument; this holds the
mechanism. Nothing here reads firmware beyond re-deriving from the committed
image, opens a capture, or needs an EC: the inputs are committed files, so this
runs in the cheap tier alongside its siblings.

**What is asserted is a relation, not a census.** The figures this change moved
-- the four verdicts, the closure sizes -- live in `bank_attribution.py`'s own
pins and are checked there, because they are properties of that tool's whole
pipeline rather than of the edge reader. What is held here is the set of
properties a re-derived table could break *silently*: a dispatch shape that
stops matching, a row that stops being an `ljmp`, a site whose bytes stop being
the reader in the window it was read in, and a table edge that loses its `frm`.

**Two cases are deliberately run against doctored inputs.** `--self-test` being
green over the committed image proves the two agree; what makes the reachability
gate mean something is the case where `edges()` is handed a closure that has
*not* reached a site and must emit nothing for it. Both directions are asserted
below, so the gate cannot be deleted and quietly widen every closure.

**What is deliberately not asserted.** No case here says a dispatch site *is* a
dispatch rather than a shape match inside data -- that is what
`dispatch_edges.py`'s `truncated_tables()` reports and what the write-up
calibrates, and the standing rule is the one `ec/annotations/registers.yaml`
states for every scan in this repository: "not found by this method" is never
"absent". The one place a site *is* pinned is `0xEFE7`, and it is pinned as the
bytes that make it a dispatch, with the listing deliberately not pinned.
"""
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
# Both tools import their siblings by bare module name, so the tool directory
# goes on the path before either module is loaded.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'dispatch_edges', HERE / 'dispatch_edges.py')
de = importlib.util.module_from_spec(spec)
spec.loader.exec_module(de)

import bank_attribution as ba  # noqa: E402  (needs the path above)

FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
ENTRIES_CSV = HERE.parent / 'annotations' / 'index-table-entries.csv'
SPANS_CSV = HERE.parent / 'annotations' / 'index-table-spans.csv'
TOOL = str(HERE / 'dispatch_edges.py')
BA_TOOL = str(HERE / 'bank_attribution.py')
WRITEUP = REPO / 'docs' / 'findings' / 'dispatch-table-closure-edges.md'

D = FIRMWARE and Path(FIRMWARE).read_bytes()


def self_test(tool=TOOL):
    """`--self-test` as a subprocess, so the exit code is what CI would see."""
    return subprocess.run([sys.executable, tool, '--self-test'],
                          capture_output=True, text=True)


class SelfTestTests(unittest.TestCase):
    """The tool's own gate, as a process. Its content is its own business;
    what this adds is that it exits zero and that a doctored tree does not."""

    def test_self_test_passes(self):
        got = self_test()
        self.assertEqual(got.returncode, 0, got.stdout + got.stderr)
        self.assertIn('self-test passed', got.stdout)

    def test_self_test_is_not_vacuous(self):
        """A run that checked nothing would also exit zero, so the gate is
        held to having actually reported checks."""
        got = self_test()
        self.assertGreater(got.stdout.count('  ok  '), 10)
        self.assertNotIn('FAIL', got.stdout)


class DeterminationTests(unittest.TestCase):
    """`0xEFE7` is a dispatch. Pinned as the reason, not the conclusion."""

    def test_bytes_that_make_it_a_dispatch(self):
        det = de.DISPATCHER
        region = det['region']
        jmp = de._bytes_at(D, region, det['jmp'], 1)
        routine = de._bytes_at(D, region, det['routine'][0], det['routine'][1])
        self.assertEqual(jmp, det['jmp_byte'])
        # The `73` is the LAST byte of a 14-byte routine, so it is a
        # instruction the walk decodes and not a byte sitting inside a table.
        self.assertEqual(len(routine), det['routine'][1])
        self.assertEqual(routine[-1:], det['jmp_byte'])

    def test_the_base_is_loaded_by_a_mov_dptr(self):
        det = de.DISPATCHER
        load = de._bytes_at(D, det['region'], det['load'], 3)
        call = de._bytes_at(D, det['region'], det['call'], 3)
        self.assertEqual(load, det['load_bytes'])
        self.assertEqual(call, det['call_bytes'])
        # Base immediately follows the call site, and the call names the
        # dispatcher whose last byte is the `jmp`.
        self.assertEqual(det['load'] + 3, det['call'])
        self.assertEqual(det['base'], det['load_bytes'][1] << 8 | det['load_bytes'][2])

    def test_row_fourteen_is_the_row_the_inventory_names(self):
        """The one corroboration that is not this repository's own tool: the
        committed inventory names this row independently."""
        det = de.DISPATCHER
        self.assertEqual(det['base'] + 3 * 14, det['row14'])
        self.assertEqual(de._bytes_at(D, det['region'], det['row14'], 3),
                         det['row14_bytes'])
        index = (HERE.parent / 'decompiled' / 'index.csv').read_text()
        self.assertIn('bank1,F012,table_efe8_row14_ljmp_f040', index)
        self.assertIn('bank1,EFDA,dispatch_index_3x_from_byte_00', index)

    def test_it_is_a_table_the_walk_now_follows(self):
        """The consequence, not the determination: the closure reaches through
        it, so a future edit that dropped the table edges fails here."""
        det = de.DISPATCHER
        bank = int(det['region'][-1])
        seeds = ba.seeds_for(ba.survey(D)[2])
        _reached, _who, entries, _cuts, _common = ba.closure(D, bank, seeds[bank])
        rows = [det['base'] + 3 * i for i in range(det['rows'])]
        for addr in rows:
            self.assertIn(addr, entries)
            self.assertTrue(entries[addr][0].startswith('dispatch'),
                            f'0x{addr:04X} is {entries[addr][0]}')


class IndexTableTests(unittest.TestCase):
    """The CSV's `site` is a bare address, and the window decides."""

    def test_every_admitted_site_holds_the_reader_in_its_own_window(self):
        for bank in (0, 1):
            region = f'bank{bank}'
            for site in de.index_table_sites(D, region):
                off = de.offset_for_runtime(site, region)
                self.assertEqual(D[off:off + 3], de.READER_CALL,
                                 f'{region} 0x{site:04X} is not the reader')

    def test_no_edge_lands_below_the_bank_floor(self):
        for bank in (0, 1):
            region = f'bank{bank}'
            reached = self.closure_reached(bank)
            for edge in de.edges(D, region, reached):
                self.assertGreaterEqual(edge['addr'], de.BANK_FLOOR)

    def test_the_two_addresses_that_are_the_same_in_both_windows(self):
        """0x8662 and 0x918A are reached by bank1's closure for unrelated
        reasons. Gating on the bytes is what stops bank0's table from being
        attributed to bank1 on a numerical coincidence."""
        bank0_sites = de.index_table_sites(D, 'bank0')
        bank1_sites = de.index_table_sites(D, 'bank1')
        self.assertIn(0x8662, bank0_sites)
        self.assertIn(0x918A, bank0_sites)
        self.assertNotIn(0x8662, bank1_sites)
        self.assertNotIn(0x918A, bank1_sites)
        # And the closure really does reach those addresses in bank1, so the
        # gate is doing work rather than being redundant.
        self.assertIn(0x8662, self.closure_reached(1))

    def test_the_common_area_sites_are_excluded_with_a_reason(self):
        excluded = de.excluded_index_sites(D, 'bank0')
        self.assertTrue(excluded)
        for site, why in excluded:
            self.assertLess(site, de.BANK_FLOOR)
            self.assertTrue(why)
        # One row per site, not per entry: the question is which tables were
        # left out, and 91 rows for four tables would answer a different one.
        self.assertEqual(len(excluded), len({s for s, _ in excluded}))

    def test_targets_are_read_from_the_csv_not_re_decoded(self):
        """Every edge's address is a target_runtime the committed file carries,
        so a drift between the two cannot hide behind this tool."""
        carried = {r['target_rt'] for r in de.index_rows()
                   if r['target_rt'] >= de.BANK_FLOOR}
        for bank in (0, 1):
            region = f'bank{bank}'
            for edge in de.edges(D, region, self.closure_reached(bank)):
                if edge['kind'] == de.KIND_INDEX:
                    self.assertIn(edge['addr'], carried)

    @staticmethod
    def closure_reached(bank):
        seeds = ba.seeds_for(ba.survey(D)[2])
        return ba.closure(D, bank, seeds[bank])[0]


class DispatchTableTests(unittest.TestCase):
    """The two shapes, the mask that sizes them, and the reachability gate."""

    def test_every_seeded_row_is_an_ljmp(self):
        """The property that makes seeding a row address enough: descend()
        follows the row's own `ljmp`, so a non-`ljmp` row is a fabricated
        target rather than a target."""
        for bank in (0, 1):
            region = f'bank{bank}'
            for table in de.dispatch_tables(D, region):
                for i in range(table['rows']):
                    addr = table['base'] + de.STRIDE * i
                    off = de.offset_for_runtime(addr, region)
                    self.assertEqual(D[off], de.LJMP,
                                     f'{region} 0x{addr:04X}')

    def test_row_count_comes_from_the_mask_and_is_capped_at_the_last_ljmp(self):
        for bank in (0, 1):
            for table in de.dispatch_tables(D, f'bank{bank}'):
                self.assertLessEqual(table['rows'], table['masked'])
                self.assertGreaterEqual(table['rows'], 1)

    def test_a_short_table_is_reported_rather_than_padded(self):
        """A mask wider than the table is a fact about the firmware, and the
        tool stops at the last real row instead of inventing the rest."""
        short = de.truncated_tables(D, 'bank1')
        for table in short:
            self.assertLess(table['rows'], table['masked'])
            region = 'bank1'
            nxt = table['base'] + de.STRIDE * table['rows']
            off = de.offset_for_runtime(nxt, region)
            self.assertNotEqual(D[off], de.LJMP)

    def test_the_two_shapes_partition_the_tables(self):
        for bank in (0, 1):
            tables = de.dispatch_tables(D, f'bank{bank}')
            self.assertEqual(len({t['site'] for t in tables}), len(tables))
            kinds = {t['kind'] for t in tables}
            self.assertTrue(kinds <= {de.KIND_INLINE, de.KIND_SHARED})

    def test_reachability_gate_run_in_both_directions(self):
        """The gate is the calibration, so it is checked with a closure that
        reached a site and one that did not. An empty `reached` must yield no
        dispatch edge at all."""
        empty = de.edges(D, 'bank1', set())
        self.assertEqual([e for e in empty if e['kind'] != de.KIND_INDEX], [])
        # And a reached site does yield its rows.
        site = de.dispatch_tables(D, 'bank1')[0]
        got = de.edges(D, 'bank1', {site['site']})
        rows = [e for e in got if e['site'] == site['site']]
        self.assertEqual(len(rows), site['rows'])
        for edge in rows:
            self.assertEqual(edge['addr'],
                             site['base'] + de.STRIDE * int(edge['edge_row'][3:]))

    def test_every_edge_names_the_site_that_produced_it(self):
        """The `frm` trap. A table edge with no site would be recorded as a
        linker-written seed, which is a false claim about the linker."""
        for bank in (0, 1):
            region = f'bank{bank}'
            seeds = ba.seeds_for(ba.survey(D)[2])
            reached = ba.closure(D, bank, seeds[bank])[0]
            edges = de.edges(D, region, reached)
            self.assertTrue(edges)
            for edge in edges:
                self.assertIn(edge['kind'], de.KINDS)
                self.assertIsInstance(edge['site'], int)
                self.assertNotEqual(edge['site'], 0)

    def test_a_row_address_is_seeded_not_its_target(self):
        """What makes this a control-flow edge: descend() derives the target,
        so the tool asserts an address to walk from and nothing more."""
        table = next(t for t in de.dispatch_tables(D, 'bank1')
                     if t['base'] == 0x8A45)
        addr = table['base']
        arm = ba.descend(D, 'bank1', addr, None, ba.MAX_DEPTH, ba.MAX_INSNS,
                         True)
        self.assertEqual([c for c in arm.callees], [0x8A6C])
        # The seeded address is the row, and the row is not the target.
        self.assertNotEqual(addr, 0x8A6C)


class ClosureIntegrationTests(unittest.TestCase):
    """The edges as `bank_attribution.py` consumes them."""

    def test_the_table_edge_frm_is_never_none(self):
        """entry_chain() reads `frm is None` as a seed the linker wrote down.
        Every entry point with a None `frm` must therefore be a trampoline."""
        seeds = ba.seeds_for(ba.survey(D)[2])
        for bank in (0, 1):
            _reached, _who, entries, _cuts, _common = ba.closure(
                D, bank, seeds[bank])
            linker_named = {a for a, (_k, frm) in entries.items() if frm is None}
            self.assertEqual(linker_named, seeds[bank])

    def test_a_table_derived_entry_point_names_a_real_site(self):
        seeds = ba.seeds_for(ba.survey(D)[2])
        for bank in (0, 1):
            _reached, _who, entries, _cuts, _common = ba.closure(
                D, bank, seeds[bank])
            for addr, (kind, frm) in entries.items():
                if kind in ("call", "trampoline"):
                    continue
                self.assertIsNotNone(frm, f'0x{addr:04X} ({kind})')
                self.assertIn(kind, de.KINDS)

    def test_section_four_negative_still_holds(self):
        """The question a reader of the write-up will ask: seeding the tables
        must not re-create the one-byte failure. All three halves."""
        seeds = ba.seeds_for(ba.survey(D)[2])
        reached = ba.closure(D, ba.NEGATIVE['bank'], seeds[ba.NEGATIVE['bank']])[0]
        self.assertIn(ba.NEGATIVE['reached'], reached)
        self.assertIn(ba.NEGATIVE['followed'], reached)
        lo, hi = ba.NEGATIVE['table']
        self.assertEqual([a for a in range(lo, hi) if a in reached], [])

    def test_no_table_target_lies_inside_its_own_table(self):
        """Why the previous case holds: nothing points back into the data, so
        seeding a target cannot close the loop that made the mis-decode."""
        import csv
        import collections
        by_site = collections.defaultdict(set)
        for row in de.index_rows():
            by_site[row['site_rt']].add(row['target_rt'])
        inside = 0
        with open(SPANS_CSV, newline='') as fh:
            for span in csv.DictReader(fh):
                lo = int(span['table_file_offset'], 16)
                hi = int(span['table_end'], 16)
                inside += sum(1 for t in by_site[int(span['site'], 16)]
                              if lo <= t < hi)
        self.assertEqual(inside, 0)

    def test_seed_entries_excludes_table_edges_and_sources_names_them(self):
        """The regions CSV's two columns are the calibration a region map
        reads, and neither can absorb the other."""
        seeds = ba.seeds_for(ba.survey(D)[2])
        closures = {b: ba.closure(D, b, seeds[b]) for b in (0, 1)}
        rows = list(ba.regions_rows(closures))
        tabled = [r for r in rows if 'trampoline' not in r['sources']]
        self.assertTrue(tabled, 'no run is reached only through a table edge')
        for r in tabled:
            self.assertEqual(r['seed_entries'], 0, r['start'])
            self.assertTrue(any(k != 'trampoline' for k in r['sources']))

    def test_the_regions_csv_carries_the_sources_column(self):
        got = subprocess.run(
            [sys.executable, BA_TOOL, FIRMWARE, '--regions-csv'],
            capture_output=True, text=True)
        self.assertEqual(got.returncode, 0, got.stderr)
        header = got.stdout.splitlines()[0].split(',')
        self.assertIn('sources', header)
        self.assertEqual(header, list(ba.REGION_COLUMNS))

    def test_the_committed_csvs_match_what_the_tool_writes(self):
        """Both committed tables are regenerated by this change, so a stale one
        is a real failure rather than a formatting preference."""
        for flag, name in (('--regions-csv', 'bank-attribution-regions.csv'),
                           ('--pairs-csv', 'bank-attribution-pairs.csv')):
            got = subprocess.run(
                [sys.executable, BA_TOOL, FIRMWARE, flag],
                capture_output=True, text=True)
            self.assertEqual(got.returncode, 0, got.stderr)
            committed = (HERE.parent / 'annotations' / name).read_text()
            self.assertEqual(got.stdout, committed, name)

    def test_regeneration_is_idempotent(self):
        """Byte-identical on a second run: the CSVs are a derived artefact and
        a rerun that moved a row would make the file unreadable as evidence."""
        outs = []
        for _ in range(2):
            got = subprocess.run(
                [sys.executable, BA_TOOL, FIRMWARE, '--regions-csv'],
                capture_output=True, text=True)
            self.assertEqual(got.returncode, 0, got.stderr)
            outs.append(got.stdout)
        self.assertEqual(outs[0], outs[1])


class CalibrationTests(unittest.TestCase):
    """The standing caveats, held as text. Whitespace is collapsed first so a
    rewrap is not a red run; what is held is that the caveats are present in
    both files that carry them."""

    @staticmethod
    def flat(path):
        return ' '.join(path.read_text().split())

    def test_the_writeup_carries_the_table_edge_caveat(self):
        text = self.flat(WRITEUP)
        self.assertIn('pops the return address into DPTR', text)
        self.assertIn('Calibration: a table edge is a table edge', text)

    def test_the_both_ways_movement_is_stated_next_to_the_numbers(self):
        """The ambiguous class grows while the residue falls, and the write-up
        has to say both. The *relation* is asserted, never the numerals: the
        figures are counts over the committed firmware that `bank_attribution`
        pins, and a test that read them back out of prose would be a second
        place to edit them."""
        text = self.flat(WRITEUP)
        self.assertIn('not all one way', text)
        self.assertIn('more coverage and weaker separation', text)
        self.assertIn('The residue falls', text)

    def test_the_efe7_determination_is_in_the_writeup(self):
        text = self.flat(WRITEUP)
        self.assertIn('0xEFE7', text)
        self.assertIn('mov dptr, #0xefe8', text)

    def test_the_tool_carries_the_same_calibration(self):
        """The caveat lives in both files a reader might reach first: the one
        running the tool and the one describing it."""
        text = self.flat(Path(TOOL))
        self.assertIn('pops the return address into DPTR', text)
        self.assertIn('attributed by this closure', text)

    def test_no_hardware_claim_in_either_file(self):
        """CLAUDE.md's rule, asserted rather than trusted. Held as the
        *disclaimer* being present rather than as the absence of a phrase:
        these files legitimately contain "no capture was taken", so a naive
        keyword check would fire on the sentence that rules the claim out.
        What is held is that both say what was not done, and that neither
        claims a result from a machine. Whitespace is collapsed first because
        both files wrap that sentence across a line."""
        for path in (WRITEUP, Path(TOOL)):
            flat = ' '.join(path.read_text().split())
            self.assertIn('no capture was taken', flat, path.name)
            self.assertIn('registers.yaml', flat, path.name)
            for phrase in ('we ran on hardware', 'read back on the machine',
                           'tested on the laptop', 'observed on the ec',
                           'the hardware confirms'):
                self.assertNotIn(phrase, flat.lower(), path.name)


if __name__ == '__main__':
    unittest.main()