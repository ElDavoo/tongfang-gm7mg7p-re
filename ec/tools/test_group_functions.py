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
# A call into a common-area address that carries a row in BOTH programs. The
# bytes say nothing about which row the caller meant -- that is the whole
# point of `TwoProgramsOneAddress` below.
LCALL_06A0 = "8000     12 06 a0 lcall    0x06A0"
LCALL_06B0 = "8000     12 06 b0 lcall    0x06B0"


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


class TwoProgramsOneAddress(unittest.TestCase):
    """One address, two functions, because there are two programs.

    `ec/decompiled/pd/0C7A.asm` and `ec/decompiled/common/0C7A.asm` are
    different functions: the ITE8850-PD image is a separate program with its
    own address space, which is the same program-versus-address conflation
    `grade_name_basis.py` and the dominant-scope naming rule exist to prevent.
    Here it is the bookkeeping rather than the grouping: an edge that joined
    the `pd` row at a shared address says nothing about the `common` row
    beside it, because that row is not an endpoint of the edge.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_a_pd_join_at_a_shared_address_is_not_a_reach_of_the_common_row(self):
        # A bank0 caller and a `pd` caller both reach 0x06A0, which carries a
        # `common` row and a `pd` row.
        #
        # The bank0 caller is what makes this discriminate, and that is worth
        # writing down rather than rediscovering: a `pd`-ONLY reach is
        # invisible either way, because `reached_only_by_bank` is a subset test
        # that already discards any non-bank scope. An assertion shaped "a `pd`
        # caller does not put the row in reached_only_by_bank" therefore passes
        # against the very bug it is written for. The reach is a set, and the
        # bank reach on the same row is what separates the two behaviours:
        # ['bank0', 'pd'] is not a subset of the banks, ['bank0'] is.
        b0_caller = listing(self.tmp.name, 'shared_b0.asm', LCALL_06A0, RET)
        pd_caller = listing(self.tmp.name, 'shared_pd.asm', LCALL_06A0, RET)
        # A callee body with no calls of its own. Handing either callee the
        # caller's listing would give that row the caller's edge, which is
        # exactly the conflation under test.
        common_row = listing(self.tmp.name, 'shared_common.asm', RET)
        pd_row = listing(self.tmp.name, 'shared_pd_row.asm', RET)
        rows = [row('bank0', '8000', 'b0_caller', b0_caller),
                row('pd', '8100', 'pd_caller', pd_caller),
                row('common', '06A0', 'common_row', common_row),
                row('pd', '06A0', 'pd_row', pd_row)]
        _grouped, stats = gf.group_rows(rows, repo=gf.REPO, min_size=2)
        self.assertEqual(stats.reached_only_by_bank, {'06A0'},
                         "the bank0 caller's edge targets the common row and "
                         "the pd caller's joins the pd row, so the common row's "
                         "callers are exactly the banks")

    def test_the_two_rows_at_a_shared_address_stay_apart(self):
        # Grouping them together would assert one function that both programs
        # call, which is the stronger and wrong claim the whole point avoids.
        caller = listing(self.tmp.name, 'shared_pd.asm', LCALL_06A0, RET)
        common_row = listing(self.tmp.name, 'shared_common.asm', RET)
        pd_row = listing(self.tmp.name, 'shared_pd_row.asm', RET)
        rows = [row('pd', '8100', 'pd_caller', caller),
                row('common', '06A0', 'common_row', common_row),
                row('pd', '06A0', 'pd_row', pd_row)]
        grouped, _ = gf.group_rows(rows, repo=gf.REPO, min_size=2)
        self.assertNotEqual(grouped[('common', '06A0')][0],
                            grouped[('pd', '06A0')][0],
                            "one address is not one function across two "
                            "programs")

    def test_a_pd_edge_to_a_common_row_with_no_pd_row_beside_it_counts(self):
        # The committed `common 11C2` case, which the attribution above must
        # not cost: no `pd` row at that address, so the `pd` caller's endpoint
        # IS the common row. The bank0 caller is here because a `pd`-only
        # reach is not observable through `reached_only_by_bank` at all -- with
        # a bank reach beside it, dropping the `pd` reach would show up as the
        # row wrongly counted as found-then-cut.
        b0_caller = listing(self.tmp.name, 'boundary_b0.asm', LCALL_06B0, RET)
        pd_caller = listing(self.tmp.name, 'boundary_pd.asm', LCALL_06B0, RET)
        common_row = listing(self.tmp.name, 'boundary_common.asm', RET)
        rows = [row('bank0', '8000', 'b0_caller', b0_caller),
                row('pd', '8100', 'pd_caller', pd_caller),
                row('common', '06B0', 'common_row', common_row)]
        _grouped, stats = gf.group_rows(rows, repo=gf.REPO, min_size=2)
        self.assertEqual(stats.reached_only_by_bank, set(),
                         "a pd caller is outside the banks, so the row is not "
                         "a found-then-cut row however the join was taken")
        # ... and it is counted rather than hidden inside bank->common, which
        # is all the banking rule can honestly do with an edge between two
        # programs.
        self.assertEqual(dict(stats.proxy_by_caller), {'bank0': 1, 'pd': 1})
        self.assertEqual(dict(stats.proxy_by_target), {'06B0': 2})


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

    def test_every_basis_is_produced_by_a_fixture_or_declared_unreachable(self):
        # The vocabulary end of the issue, and the relation is both ways: a
        # closed list is only closed if every value in it can be produced, and
        # one that cannot is a name rather than a vocabulary. `shared` was
        # exactly that -- in `GROUP_BASES`, emitted by nothing, and exempted by
        # a `cross_bank_groups` branch that skips every non-`callgraph` row.
        #
        # Each basis is read off a fixture that makes `group_rows()` return it
        # rather than written down beside it, so the two sets cannot drift into
        # agreeing with each other the way a hand-kept list does.
        def emitted(rows, **kw):
            grouped, _ = gf.group_rows(rows, repo=gf.REPO, **kw)
            return {v[1] for v in grouped.values()}

        with tempfile.TemporaryDirectory() as tmp:
            # A same-region call, and one listing per function, because that is
            # the shape that clusters: a bank0 -> common edge is cut by the
            # per-bank proxy rule and lands on `ungrouped` instead, which would
            # make this fixture's `callgraph` a claim about the wrong rule.
            caller = listing(tmp, 'closure_caller.asm', LCALL_8100, RET)
            callee = listing(tmp, 'closure_callee.asm', RET)
            produced = (
                emitted([row('common', '0000', 'reset_vector_forwarder_to_0070',
                             '', type='entry')])                        # vector
                | emitted([row('bank0', '163C', 'switch', '',
                               type='bank-switch')])                     # type
                | emitted([row('bank0', '163C', 'mystery', '',
                               type='reader')])                          # ungrouped
                | emitted([row('bank0', '8000', 'caller', caller),
                           row('bank0', '8100', 'callee', callee)],
                          min_size=2)                                   # callgraph
                | emitted([row('Setup', '260', 'entry', '',
                               type='module-entry')], is_bios=True))    # module
        # Where a basis with no rule behind it goes: out of the closed list,
        # into this map with the reason it cannot be produced. It is empty,
        # and that is the point -- `shared` belonged here, and a closed list
        # with nowhere to say so is what the issue is about.
        declared_unreachable = {}
        self.assertEqual(
            set(gf.GROUP_BASES) - produced, set(declared_unreachable),
            "a basis in the closed list that no rule emits and no fixture "
            "produces")
        for basis, why in declared_unreachable.items():
            self.assertTrue(why.strip(),
                            '%s is declared unreachable with no reason' % basis)
        self.assertEqual(
            produced - set(gf.GROUP_BASES), set(),
            "a rule emits a basis the closed list does not name, so --check "
            "would refuse the rows the rule itself wrote")


class CommittedDrift(unittest.TestCase):
    """`--check`'s drift half against the committed files.

    The two directions have to be true at once on the same tree, and neither
    one implies the other: the committed cells have to agree with a fresh run
    of the rule, and a single poisoned cell has to be *named* rather than
    counted. A comparison that is quiet because it is comparing a value with
    itself passes the first and fails nothing else, which is the shape of the
    bug this half of the check exists to stop.
    """

    def maps(self, is_bios=False):
        """The committed and computed maps for one component, keyed the way
        `check()` keys them. Freshly built per test, because the poisoning
        below edits the committed map in place."""
        return gf.drift_for(
            gf.read_csv(gf.BIOS_CSV if is_bios else gf.EC_CSV),
            gf.read_csv(gf.BIOS_GROUPS if is_bios else gf.EC_GROUPS),
            gf.REPO, is_bios)

    def a_callgraph_row(self, committed):
        """The first committed `callgraph` key and its cells.

        A `callgraph` row because its `group` is a name a reader takes
        seriously -- `callgraph_<scope>_<addr>` is checked by
        `misnamed_callgraph_groups`, so a wrong one here is the edit most worth
        being caught."""
        for key in sorted(committed):
            if committed[key][1] == 'callgraph':
                return key, committed[key]
        self.fail('no callgraph row in %s' % gf.EC_GROUPS)

    def test_the_committed_cells_agree_with_a_fresh_run(self):
        for is_bios, path in ((False, gf.EC_GROUPS), (True, gf.BIOS_GROUPS)):
            committed, computed = self.maps(is_bios)
            self.assertEqual(
                gf.drift_problems(committed, computed,
                                  os.path.relpath(path, gf.REPO)),
                [], path)

    def test_a_hand_edited_group_cell_is_named(self):
        # The issue's demonstration. `arithmetic` is a real group name, so the
        # edit is the plausible kind: it breaks no vocabulary rule, trips no
        # naming rule, and `--apply` would revert it without saying so.
        committed, computed = self.maps()
        key, cells = self.a_callgraph_row(committed)
        committed[key] = ('arithmetic',) + cells[1:]
        problems = gf.drift_problems(committed, computed,
                                     os.path.relpath(gf.EC_GROUPS, gf.REPO))
        self.assertEqual(len(problems), 1, problems)
        self.assertIn('%s %s' % (key[0], key[1]), problems[0])
        self.assertIn(cells[2], problems[0], 'the refusal names the function')
        self.assertIn('committed group arithmetic/', problems[0])
        self.assertIn('the rule gives %s/%s' % (cells[0], cells[1]),
                      problems[0])

    def test_a_hand_edited_basis_cell_is_named(self):
        # `type` is in the closed list, so the vocabulary check accepts it and
        # only the recompute can say the rule did not write it.
        committed, computed = self.maps()
        key, cells = self.a_callgraph_row(committed)
        committed[key] = cells[:1] + ('type',) + cells[2:]
        problems = gf.drift_problems(committed, computed,
                                     os.path.relpath(gf.EC_GROUPS, gf.REPO))
        self.assertEqual(len(problems), 1, problems)
        self.assertIn('committed group_basis %s/type' % cells[0], problems[0])

    def test_a_committed_row_the_rule_does_not_produce_is_named(self):
        # The other direction, and the one that is not a cell comparison: a
        # group row whose function the annotation file no longer carries.
        # Nothing else in `check()` looks for it -- the "no group for annotated"
        # rule asks the other way round -- so it is the drift half's to name.
        committed, computed = self.maps()
        key, cells = self.a_callgraph_row(committed)
        del computed[key]
        problems = gf.drift_problems(committed, computed,
                                     os.path.relpath(gf.EC_GROUPS, gf.REPO))
        self.assertEqual(len(problems), 1, problems)
        self.assertIn('%s %s' % (key[0], key[1]), problems[0])


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
        self.assertIn('every committed group and group_basis agrees with a '
                      'fresh run of the rule', out.getvalue())

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
