#!/usr/bin/env python3
"""Offline checks for group_functions.py: a fixture graph with a known
cross-bank edge, and the committed group files.

The tool's whole claim is a refusal. It reads `lcall`/`ljmp` operands out of
the committed listings, and the reason it cannot join bank0 to bank1 is that
nothing in those three bytes names a bank -- bank0->bank1 and bank0->bank0 are
the same encoding. A clustering tool that quietly merged across a bank would
produce a smaller, tidier, wrong answer, and nothing in its own output would
say so: the failure mode is a plausible number, not a crash.

So the case that matters is the one where a same-region call and a
cross-region call are *byte-identical* and differ only in which bank the
target happens to exist in. Everything else here supports that.

The fixtures are written inline rather than committed, because the `.asm`
shape being tested is a hypothetical one -- a listing that really is three
identical bytes at 0x8000 in both banks would be a committed export, and
building one by hand under `ec/` would be indistinguishable from real
decompiled output. The parsers exercised are the real ones.
"""
import contextlib
import csv
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
# group_functions imports bucket_of/OTHER_BANK from audit_call_targets, the
# way check_register_counts imports trace_xdata_refs; loading it by path is
# no different from running it, and the directory is the same sys.path entry.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'group_functions', HERE / 'group_functions.py')
gf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gf)

# The three bytes both cases share: `12 81 00` is `lcall 0x8100`, and there
# is no encoding of it that says which bank 0x8100 is in.
LCALL_8100 = "8000     12 81 00 lcall    0x8100"
# A callee body. Every fixture function that is not the caller gets one, so
# the graph under test has exactly the edges the case is about.
RET = "8100     22 - -   ret"
# A call into the common area, which IS unambiguous -- below the bank base
# there is one copy both banks share.
LCALL_0530 = "8000     12 05 30 lcall    0x0530"
# A paged `ajmp`, which cannot leave the caller's own region and so is not a
# banking question; the tool must not treat it as an edge.
AJMP = "8000     01 30 - -   ajmp     0x8030"


def listing(directory, name, *lines):
    """One fixture `.asm`, returned as a repo-relative path."""
    path = os.path.join(directory, name)
    with open(path, 'w') as f:
        f.write("; fixture -- not a real listing\n")
        for line in lines:
            f.write(line + "\n")
    return os.path.relpath(path, gf.REPO)


def row(scope, addr, name, path, type="logic"):
    return {"scope": scope, "addr": addr, "name": name, "type": type,
            "comment": "", "evidence": path, "basis": "hand-decoded",
            "name_basis": "code-shape"}


class CrossBankEdge(unittest.TestCase):
    """The refusal, on a graph where the two cases are the same three bytes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # One listing per FUNCTION, because a row's `.asm` is its own body
        # and every `lcall` in it is an edge out of that function. Sharing
        # the caller's listing with the callee would hand the callee the
        # caller's edge, which is not a case the tool can be asked about.
        self.caller = listing(self.tmp.name, 'caller.asm', LCALL_8100, RET)
        self.callee = listing(self.tmp.name, 'callee.asm', RET)
        self.other = listing(self.tmp.name, 'other_bank.asm', RET)
        self.same = self.cross = self.caller

    def test_a_call_into_the_other_bank_is_not_joined(self):
        # bank0 0x8000 calls 0x8100; 0x8100 exists in BOTH banks. The
        # same-bank reading is the right default and the cross-bank one is
        # unknowable, so the two must not end up in one group.
        rows = [row('bank0', '8000', 'caller', self.caller),
                row('bank0', '8100', 'callee', self.callee),
                row('bank1', '8100', 'other_bank_callee', self.other)]
        grouped, _ = gf.group_rows(rows, repo=gf.REPO, min_size=2)
        self.assertNotEqual(grouped[('bank0', '8100')][0],
                            grouped[('bank1', '8100')][0],
                            "bank0 0x8100 and bank1 0x8100 must not share a "
                            "group; the lcall does not name a bank")

    def test_the_ambiguous_edge_is_counted_not_hidden(self):
        # If the count only lived in the branch that refuses to join, an
        # address present in both banks would report zero for an edge the
        # assumption genuinely decides.
        rows = [row('bank0', '8000', 'caller', self.caller),
                row('bank0', '8100', 'callee', self.callee),
                row('bank1', '8100', 'other_bank_callee', self.other)]
        _grouped, stats = gf.group_rows(rows, repo=gf.REPO, min_size=2)
        self.assertEqual(stats.cross_region, 1)

    def test_a_same_region_edge_still_clusters(self):
        # The refusal must not be a refusal to cluster at all. With no bank1
        # row to tempt it, the two bank0 functions are one cluster.
        rows = [row('bank0', '8000', 'caller', self.caller),
                row('bank0', '8100', 'callee', self.callee)]
        grouped, _ = gf.group_rows(rows, repo=gf.REPO, min_size=2)
        self.assertEqual(grouped[('bank0', '8000')][0],
                         grouped[('bank0', '8100')][0])
        self.assertEqual(grouped[('bank0', '8000')][1], 'callgraph')

    def test_a_common_area_target_is_joined(self):
        # Below 0x8000 there is one copy, so this edge is not a banking
        # question and dropping it would make the graph sparser than the
        # evidence supports.
        common = listing(self.tmp.name, 'common.asm', LCALL_0530)
        rows = [row('bank0', '8000', 'caller', common),
                row('common', '0530', 'handler', common),
                row('bank1', '0530', 'also_common', common)]
        grouped, _ = gf.group_rows(rows, repo=gf.REPO, min_size=2)
        self.assertEqual(grouped[('bank0', '8000')][0],
                         grouped[('common', '0530')][0])

    def test_a_paged_ajmp_is_not_an_edge(self):
        # `ajmp` is 2 bytes and paged: the target is inside the caller's own
        # page and cannot leave the region, so treating it as an edge would
        # manufacture a cross-region link that cannot exist.
        paged = listing(self.tmp.name, 'paged.asm', AJMP)
        rows = [row('bank0', '8000', 'caller', paged),
                row('bank1', '8030', 'elsewhere', paged)]
        grouped, stats = gf.group_rows(rows, repo=gf.REPO, min_size=2)
        self.assertEqual(stats.cross_region, 0)
        self.assertEqual(grouped[('bank1', '8030')][0], 'ungrouped')


class Seeds(unittest.TestCase):
    """The seeds, which are the part of the grouping that is not a guess."""

    def test_a_vector_row_is_seeded_from_the_table(self):
        rows = [row('common', '0000', 'reset_vector_forwarder_to_0070',
                    '', type='entry'),
                row('common', '000B', 'timer0_vector_forwarder_to_0530',
                    '', type='forwarder')]
        grouped, _ = gf.group_rows(rows, repo=gf.REPO)
        for key in (('common', '0000'), ('common', '000B')):
            self.assertEqual(grouped[key][1], 'vector')
            self.assertEqual(grouped[key][0], 'interrupt-vectors')

    def test_a_plain_forwarder_is_not_swept_in_with_the_vectors(self):
        # The vector match is on the name, so a forwarder that merely forwards
        # has to stay out of the group.
        rows = [row('common', '0100', 'forward_to_0530', '', type='forwarder')]
        grouped, _ = gf.group_rows(rows, repo=gf.REPO)
        self.assertNotEqual(grouped[('common', '0100')][0], 'interrupt-vectors')

    def test_a_bank_switch_row_is_seeded_from_its_type(self):
        rows = [row('bank0', '163C', 'load_dptr_88f0_tail_jump_1114', '',
                    type='bank-switch')]
        grouped, _ = gf.group_rows(rows, repo=gf.REPO)
        self.assertEqual(grouped[('bank0', '163C')][0], 'bank-switch-trampolines')
        self.assertEqual(grouped[('bank0', '163C')][1], 'type')

    def test_a_row_with_no_seed_and_no_cluster_is_ungrouped(self):
        # A plausible label is the thing to avoid here: `ungrouped` exists so
        # that saying the method did not reach the row costs nothing.
        rows = [row('bank0', '163C', 'mystery', '', type='reader')]
        grouped, _ = gf.group_rows(rows, repo=gf.REPO)
        self.assertEqual(grouped[('bank0', '163C')][0], 'ungrouped')

    def test_a_cluster_below_the_minimum_size_is_not_a_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = listing(tmp, 'one.asm', LCALL_0530)
            rows = [row('bank0', '8000', 'caller', path),
                    row('common', '0530', 'handler', path)]
            grouped, _ = gf.group_rows(rows, repo=gf.REPO, min_size=4)
            self.assertEqual(grouped[('bank0', '8000')][0], 'ungrouped')

    def test_a_seed_outranks_a_cluster(self):
        # A seed is read off something already established; a cluster is a
        # guess at structure. Where both apply, the established one wins.
        with tempfile.TemporaryDirectory() as tmp:
            path = listing(tmp, 'bs.asm', LCALL_0530)
            rows = [row('common', '0000', 'reset_vector_forwarder_to_0070', path,
                        type='entry'),
                    row('common', '0530', 'handler', path, type='bank-switch')]
            grouped, _ = gf.group_rows(rows, repo=gf.REPO, min_size=2)
            self.assertEqual(grouped[('common', '0000')][1], 'vector')


class GroupFileCheck(unittest.TestCase):
    """The --check refusals, and the committed files they run over."""

    def grow(self, **kw):
        base = {"scope": "bank0", "addr": "8000", "group": "g",
                "group_basis": "callgraph", "comment": "", "evidence": ""}
        base.update(kw)
        return base

    def test_every_basis_in_the_vocabulary_is_accepted(self):
        for basis in gf.GROUP_BASES:
            self.assertEqual(gf.check_group_row(self.grow(group_basis=basis), {}),
                             [], basis)

    def test_an_off_list_basis_is_refused(self):
        self.assertTrue(gf.check_group_row(self.grow(group_basis="vibes"), {}))

    def test_an_empty_group_is_refused(self):
        self.assertTrue(gf.check_group_row(self.grow(group="  "), {}))

    def test_a_group_spanning_two_banks_is_refused(self):
        rows = [self.grow(scope='bank0', addr='8000', group='merged'),
                self.grow(scope='bank1', addr='8100', group='merged')]
        self.assertEqual(gf.cross_bank_groups(rows), ['merged'])

    def test_a_group_inside_one_bank_is_accepted(self):
        rows = [self.grow(scope='bank0', addr='8000', group='one'),
                self.grow(scope='bank0', addr='8100', group='one')]
        self.assertEqual(gf.cross_bank_groups(rows), [])

    def test_a_common_row_does_not_make_a_group_cross_bank(self):
        # `common` is the 0x0000-0x7FFF area both banks carry. It is not a
        # bank, so a type-seeded group legitimately spans it and bank0.
        rows = [self.grow(scope='common', addr='0530', group='timers',
                          group_basis='type'),
                self.grow(scope='bank0', addr='8100', group='timers',
                          group_basis='type')]
        self.assertEqual(gf.cross_bank_groups(rows), [])

    def test_ungrouped_spanning_banks_is_not_a_cross_bank_claim(self):
        rows = [self.grow(scope='bank0', addr='8000', group='ungrouped',
                          group_basis='ungrouped'),
                self.grow(scope='bank1', addr='8100', group='ungrouped',
                          group_basis='ungrouped')]
        self.assertEqual(gf.cross_bank_groups(rows), [])

    def test_a_type_seeded_group_spanning_two_banks_is_not_a_merge(self):
        # Two functions that share a role are not connected by anything, so
        # a `math` row in each bank is the vocabulary working, not the merge
        # the caveat forbids. Refusing it would refuse the seeded grouping the
        # whole layer is built on.
        rows = [self.grow(scope='bank0', addr='8000', group='arithmetic',
                          group_basis='type'),
                self.grow(scope='bank1', addr='8100', group='arithmetic',
                          group_basis='type')]
        self.assertEqual(gf.cross_bank_groups(rows), [])


class CommittedFiles(unittest.TestCase):
    """The last case is the real thing: the two committed group files.

    It is what says the tree currently agrees with the tool, and it is the
    only case that would notice a re-export moving a function between
    groups."""

    def test_the_committed_group_files_pass_their_own_check(self):
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            rc = gf.check()
        self.assertEqual(rc, 0, err.getvalue() + out.getvalue())
        self.assertIn('every annotated function has a group',
                      out.getvalue())

    def test_every_committed_group_row_names_a_group_and_a_basis(self):
        for path in (gf.EC_GROUPS, gf.BIOS_GROUPS):
            if not os.path.isfile(path):
                self.skipTest('%s not generated yet' % os.path.basename(path))
            with open(path, newline='') as f:
                rows = list(csv.DictReader(f, strict=True))
            self.assertGreater(len(rows), 0, path)
            for row in rows:
                self.assertTrue(row['group'].strip(), row)
                self.assertIn(row['group_basis'], gf.GROUP_BASES, row)


if __name__ == '__main__':
    unittest.main()
