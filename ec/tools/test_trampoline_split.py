#!/usr/bin/env python3
"""Offline checks for the bank-select trampoline cut: the shape rule that
finds the trampolines, and what the cut does to the grouping.

`group_functions.py --self-test` holds the cases that need the clustering
machinery -- the two banks kept apart across a trampoline, the accounting for
the edges the cut removes. This file holds the two it cannot reach cleanly:
the shape rule itself, over listings written here rather than read from the
export, and the mode's *contract* -- which modes exist, which is the default,
and what each one claims in a row's comment.

**Why the shape rule needs its own file.** `group_functions.py` reads every
annotated row's listing once per run, and the committed EC listings are real
decompiled output: a fixture written under `ec/decompiled/` would be
indistinguishable from it. So the listings are written to a temporary
directory here, exactly as `test_group_functions.py` does for its own.

**Why the pin is pinned here rather than in a census.** `mov DPTR,#imm16`
followed by `ljmp <anything>` is the shape; `ljmp <a BL51 stub>` is the rule.
Accepting any target widens the population by whatever else in the export
happens to have that body, so the gap between the two answers is the cost of
not pinning -- and a gap nobody asserts is a gap that changes silently. The
assertions below are on fixtures, so they hold a property rather than a count:
the committed tree's figures move with every annotation tranche and a test that
quoted them would be a value every merge has to edit. `bl51_trampolines.py` is
the command that prints today's.
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
# group_functions imports the shape rule from bl51_trampolines and the listing
# regex with it, so both have to be importable by path before it loads. Same
# reasoning as test_group_functions.py: running the tool from this directory is
# what puts these names on sys.path anyway.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'group_functions', HERE / 'group_functions.py')
gf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gf)

import bl51_trampolines as bt  # noqa: E402  (needs the sys.path entry above)

# The four stubs `subsystems.md` §4 enumerates. Used as a fixture's own stub
# set where the point is the rule and not the committed file, so that a case
# here does not move when an annotation tranche lands.
STUBS = {'1100', '1114', '1128', '113C'}

# A body that matches the shape, split over two lines the way the committed
# export writes it. The address column is what `read_listing` parses and the
# byte column is lower-case throughout, because `LISTING` only matches
# lower-case hex there -- a fixture with upper-case bytes parses as a listing
# with no instructions in it, and every case below then passes for a reason
# that has nothing to do with the rule.
MOV_DNTR = "9000     90 88 f0 mov      DPTR, #0x88f0"
JMP_1100 = "9003     02 11 00 ljmp     0x1100"
JMP_110C = "9003     02 11 0c ljmp     0x110c"
RET = "9006     22 - -   ret"


def listing(directory, name, *lines):
    """One fixture `.asm`, returned as a repo-relative path."""
    path = os.path.join(directory, name)
    with open(path, 'w') as f:
        f.write("; fixture -- not a real listing\n")
        for line in lines:
            f.write(line + "\n")
    return path


class ShapeRule(unittest.TestCase):
    """`is_trampoline()`: the body, not the name and not the `type` column.

    Every case is a listing whose failure would be silent. The 30
    `type=bank-switch` rows and the 7 `type=dispatch` ones are already seeded
    into groups by that column, which is precisely why a rule keyed on it
    would fix nothing: a seed labels a row and leaves its edges in the graph.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_a_two_instruction_body_is_a_trampoline(self):
        path = listing(self.tmp.name, 'yes.asm', MOV_DNTR, JMP_1100)
        self.assertEqual(bt.is_trampoline(path, STUBS), '1100')

    def test_a_body_with_a_ret_is_not(self):
        # The rule is the WHOLE body. A third instruction makes it something
        # else, and a rule that only looked at the first two would cut an edge
        # for a function this shape does not describe.
        path = listing(self.tmp.name, 'ret.asm', MOV_DNTR, JMP_1100, RET)
        self.assertIsNone(bt.is_trampoline(path, STUBS))

    def test_a_single_instruction_is_not(self):
        path = listing(self.tmp.name, 'one.asm', MOV_DNTR)
        self.assertIsNone(bt.is_trampoline(path, STUBS))

    def test_a_mov_of_something_other_than_dptr_is_not(self):
        # `mov SP,#0x07` and an `ljmp` is still a tail jump, but the address
        # the stub acts on is not in it.
        path = listing(self.tmp.name, 'sp.asm',
                       "9000     90 07 81 mov      SP, #0x8107", JMP_1100)
        self.assertIsNone(bt.is_trampoline(path, STUBS))

    def test_a_dptr_load_followed_by_something_other_than_an_ljmp_is_not(self):
        path = listing(self.tmp.name, 'sjmp.asm',
                       MOV_DNTR, "9003     80 90 sjmp     @a+dptr")
        self.assertIsNone(bt.is_trampoline(path, STUBS))

    def test_a_call_rather_than_a_tail_jump_is_not(self):
        # `lcall` back to the caller is the same shape of code with a
        # different meaning, and cutting its edge would remove a real call.
        path = listing(self.tmp.name, 'call.asm',
                       MOV_DNTR, "9003     12 00 80 lcall    0x8000")
        self.assertIsNone(bt.is_trampoline(path, STUBS))

    def test_the_shape_alone_matches_a_jump_to_a_non_stub(self):
        # `stubs=None` asks the unpinned question: the shape with any `ljmp`
        # target. This is what §4's "290 across the export" counts, and the
        # rule is the pinned version of it.
        path = listing(self.tmp.name, 'elsewhere.asm', MOV_DNTR, JMP_110C)
        self.assertEqual(bt.is_trampoline(path, None), '110C')

    def test_the_pin_is_what_separates_the_two_populations(self):
        # **The gap, held on fixtures rather than on the tree.** The same
        # listing answers under both questions, and it is the pin alone that
        # makes them differ. Loosening `is_trampoline()` to accept any target
        # would widen every downstream count by however many such listings the
        # export has, with nothing failing and `bl51_trampolines.py` still
        # printing a number.
        elsewhere = listing(self.tmp.name, 'elsewhere.asm', MOV_DNTR, JMP_110C)
        stub = listing(self.tmp.name, 'stub.asm', MOV_DNTR, JMP_1100)
        self.assertIsNone(bt.is_trampoline(elsewhere, STUBS))
        self.assertIsNotNone(bt.is_trampoline(elsewhere, None))
        self.assertEqual(bt.is_trampoline(stub, STUBS),
                         bt.is_trampoline(stub, None),
                         "a listing that jumps to a stub is in both "
                         "populations; the gap is entirely the non-stubs")

    def test_a_path_that_is_not_a_listing_reads_as_no_instructions(self):
        # An annotation row whose evidence resolves to nothing is a gap in the
        # annotations. It is not a malformed export, and the shape rule has
        # nothing to say about it either way.
        self.assertEqual(bt.read_listing(None), [])
        self.assertEqual(bt.read_listing(os.path.join(self.tmp.name, 'no')),
                         [])
        self.assertIsNone(bt.is_trampoline(
            os.path.join(self.tmp.name, 'no'), STUBS))

    def test_comments_and_blank_lines_are_not_instructions(self):
        # The committed listings carry a five-line header; counting it would
        # make every real trampoline a non-trampoline.
        path = listing(self.tmp.name, 'header.asm', MOV_DNTR, JMP_1100)
        self.assertEqual(len(bt.read_listing(path)), 2)


class StubSet(unittest.TestCase):
    """`stub_addresses()`: derived from the annotations, and refused when
    partial."""

    @staticmethod
    def stub_row(name, addr):
        return {'scope': 'common', 'addr': addr, 'name': name, 'type': 'gate',
                'evidence': ''}

    def all_four(self):
        return [self.stub_row('bl51_bank_select_%d' % n, addr)
                for n, addr in enumerate(('1100', '1114', '1128', '113C'))]

    def test_the_committed_annotations_resolve_to_the_four_named_stubs(self):
        # The one case that reads the real file, and it asserts the SET rather
        # than a count: the addresses are what `subsystems.md` §4 enumerates,
        # and a stub renamed at that address would have to be a rename of a
        # real function rather than of this tool's expectation.
        self.assertEqual(bt.stub_addresses(gf.read_csv(gf.EC_CSV)),
                         {'1100', '1114', '1128', '113C'})

    def test_the_wrapper_row_is_not_a_stub(self):
        # `ghidra-functions.csv` carries `bl51_bank_select_0_tail_110a_wrapper`
        # at `common` `0x1048`. It shares the prefix and is a wrapper AROUND a
        # stub. A substring or prefix match sweeps it in, makes the set five,
        # and every address below 0x1100 that the wrapper jumps to becomes a
        # "stub" -- which is why the name match is a whole-name one.
        rows = self.all_four() + [self.stub_row(
            'bl51_bank_select_0_tail_110a_wrapper', '1048')]
        self.assertEqual(bt.stub_addresses(rows), STUBS)

    def test_a_partial_set_is_refused(self):
        # The assertion is "all four or none", and this is the half that is
        # load-bearing: one, two or three stubs means the pattern has stopped
        # meaning the stubs, and every shape answer below it would still be
        # produced quietly.
        for keep in (1, 2, 3):
            with self.assertRaises(AssertionError):
                bt.stub_addresses(self.all_four()[:keep])

    def test_an_empty_set_is_left_alone(self):
        # Not an escape: `group_functions.cluster()` runs this over the BIOS
        # rows too, and the BIOS has no BL51 stubs because it is not this
        # firmware. The split mode is inert there, and measured so.
        self.assertEqual(bt.stub_addresses([]), set())
        self.assertEqual(bt.stub_addresses(gf.read_csv(gf.BIOS_CSV)), set())


class TrampolineListings(unittest.TestCase):
    """`trampoline_listings()`: keyed the way `cluster()` walks."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_it_is_keyed_by_scope_and_address(self):
        # `cluster()` holds one row at a time and has already resolved that
        # row's listing, so the lookup it does is a membership test on this
        # key -- not a path comparison, which two rows could share.
        #
        # The four stub rows are here because `stub_addresses()` refuses a
        # partial set, and a fixture with none would resolve to an empty stub
        # set -- which is the BIOS case, inert, and asserts nothing about the
        # keying.
        path = listing(self.tmp.name, 't.asm', MOV_DNTR, JMP_1100)
        rows = [
            {'scope': 'bank0', 'addr': '9000', 'name': 't',
             'type': 'forwarder', 'evidence': os.path.relpath(path, gf.REPO)},
            {'scope': 'bank1', 'addr': '9000', 'name': 'u',
             'type': 'forwarder', 'evidence': os.path.relpath(path, gf.REPO)},
            # Same listing, but this row's body is not a trampoline, so it must
            # not inherit the key merely because the file is shared.
            {'scope': 'bank0', 'addr': '9100', 'name': 'v', 'type': 'logic',
             'evidence': os.path.relpath(
                 listing(self.tmp.name, 'plain.asm', RET), gf.REPO)},
        ] + [{'scope': 'common', 'addr': addr,
              'name': 'bl51_bank_select_%d' % n, 'type': 'gate',
              'evidence': ''}
             for n, addr in enumerate(('1100', '1114', '1128', '113C'))]
        found = bt.trampoline_listings(rows, gf.REPO)
        self.assertEqual(sorted(found), [('bank0', '9000'), ('bank1', '9000')])

    def test_a_row_whose_evidence_does_not_resolve_is_left_out(self):
        # Not found by this method, never absent: the same wording
        # `group_functions.py` uses for the same situation, and the same
        # reason it is the right one.
        rows = [{'scope': 'bank0', 'addr': '9000', 'name': 't',
                 'type': 'forwarder',
                 'evidence': 'ec/decompiled/bank0/no-such.asm'}]
        self.assertEqual(bt.trampoline_listings(rows, gf.REPO), {})

    def test_the_committed_annotations_resolve_to_a_population(self):
        # The one case that reads the real tree, and it asserts the two sides
        # of the pin rather than a figure: the pinned set is a subset of the
        # unpinned one, and both are non-empty. `bl51_trampolines.py` prints
        # the counts, because a count asserted here is a number every
        # annotation tranche has to edit.
        rows = gf.read_csv(gf.EC_CSV)
        pinned = set(bt.trampoline_listings(rows, gf.REPO))
        unpinned = {key for row in rows
                    for key in ((row['scope'], bt.norm_addr(row['addr'])),)
                    if bt.is_trampoline(bt.asm_path(row, gf.REPO), None)}
        self.assertTrue(pinned)
        self.assertTrue(pinned <= unpinned)


class SplitModeContract(unittest.TestCase):
    """`--split`: which modes exist, which is the default, and what each one
    says in a row's comment."""

    def test_trampoline_is_the_default(self):
        # `agent-gates.sh` runs `--check && --self-test` with no arguments, so
        # a mode that had to be named at every call site would either need a
        # gate edit or leave the committed file and the gate disagreeing. This
        # is the assertion that the default is the committed mode.
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument('--split', choices=sorted(gf.SPLIT_MODES),
                        default=gf.DEFAULT_SPLIT)
        self.assertEqual(ap.parse_args([]).split, 'trampoline')
        self.assertEqual(gf.DEFAULT_SPLIT, 'trampoline')

    def test_the_vocabulary_is_closed_and_small(self):
        # Every mode has to carry the clause it puts in a `callgraph` comment.
        # A mode added without one would write a row claiming nothing about
        # the graph it was computed on, which is the whole failure the clause
        # exists to prevent.
        self.assertEqual(sorted(gf.SPLIT_MODES), ['none', 'trampoline'])
        for mode, clause in gf.SPLIT_MODES.items():
            self.assertTrue(clause.endswith('.'), mode)
            self.assertGreater(len(clause), 40, mode)

    def test_the_modes_claim_different_graphs(self):
        # Neither clause may be usable as the other's: a row written under one
        # mode and read under the other is the reader who is misled, and the
        # two sentences have to be about different graphs for that to fail
        # loudly rather than quietly.
        cut, uncut = gf.SPLIT_MODES['trampoline'], gf.SPLIT_MODES['none']
        self.assertIn('bank-select trampoline boundary', cut)
        self.assertIn('property of the graph the union walked', cut)
        self.assertIn('No edge is cut', uncut)
        self.assertNotIn('bank-select trampoline boundary', uncut)
        self.assertNotIn('union walked', uncut)

    def test_a_mode_outside_the_list_is_refused_rather_than_read_as_no_cut(self):
        with self.assertRaises(ValueError):
            gf.cluster([], repo=gf.REPO, split='trampolines')

    def test_apply_refuses_the_mode_the_committed_file_was_not_written_in(self):
        # Driven against a scratch pair rather than the committed CSVs, so a
        # refusal that regressed to writing first would damage a temporary
        # file rather than the tree. That is the only safe way to test the
        # ordering of a refusal against a write.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        groups = os.path.join(tmp.name, 'groups.csv')
        with open(groups, 'w', newline='') as f:
            writer = csv.DictWriter(
                f, fieldnames=['scope', 'addr', 'group', 'group_basis',
                               'comment', 'evidence'], lineterminator='\n')
            writer.writeheader()
            writer.writerow({'scope': 'bank0', 'addr': '8000',
                             'group': 'sentinel', 'group_basis': 'ungrouped',
                             'comment': '', 'evidence': ''})
        with open(groups, 'rb') as f:
            before = f.read()
        saved = gf.COMMITTED_SOURCES
        gf.COMMITTED_SOURCES = ((os.path.join(tmp.name, 'ann.csv'), groups,
                                 False),)
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                rc = gf.main(['--apply', '--split=none'])
        finally:
            gf.COMMITTED_SOURCES = saved
        self.assertEqual(rc, 2)
        with open(groups, 'rb') as f:
            self.assertEqual(f.read(), before,
                             'the refusal has to happen before the write, or '
                             'the message is the only thing saying the file '
                             'changed')
        self.assertIn('group_basis=callgraph', err.getvalue())


class ReportFigures(unittest.TestCase):
    """What `--report` shows about the cut, keyed off a fixture so the figures
    are the ones the fixture produces."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def rows_and_stats(self, split):
        """Two bank0 rows that reach a common helper, plus a bank1 pair that
        reaches it through a trampoline. Small enough to state exactly and
        large enough that the cut changes the component count."""
        def asm(name, *lines):
            return os.path.relpath(listing(self.tmp.name, name, *lines),
                                   gf.REPO)

        def row(scope, addr, name, path, type='logic'):
            return {'scope': scope, 'addr': addr, 'name': name, 'type': type,
                    'evidence': path}

        rows = [row('bank0', '8000', 'a', asm('a.asm', "8000     12 81 00 lcall    0x8100", RET)),
                row('bank0', '8100', 'b', asm('b.asm', RET)),
                row('bank0', '8200', 'c', asm('c.asm', "8200     12 83 00 lcall    0x8300", RET)),
                row('bank0', '8300', 'd', asm('d.asm', RET)),
                row('bank1', '8000', 'e', asm('e.asm', "8000     12 81 00 lcall    0x8100", RET)),
                row('bank1', '8100', 'f', asm('f.asm', RET)),
                # A bank0 trampoline into a common row: two more rows joined to
                # bank0's component only while its tail jump survives.
                row('bank0', '8400', 't', asm('t.asm', "8400     90 07 81 mov      DPTR, #0x8107",
                                              "8403     02 11 00 ljmp     0x1100"), 'forwarder'),
                row('common', '1100', 'bl51_bank_select_0', asm('s0.asm', RET), 'gate'),
                ]
        rows += [{'scope': 'common', 'addr': addr,
                  'name': 'bl51_bank_select_%d' % n, 'type': 'gate',
                  'evidence': asm('s%s.asm' % addr, RET)}
                 for n, addr in enumerate(('1114', '1128', '113C'))]
        grouped, stats = gf.group_rows(rows, repo=gf.REPO, min_size=2,
                                       split=split)
        return rows, grouped, stats

    def test_the_cut_reports_its_own_population_and_the_banking_rule_does_not(self):
        # The trampoline's tail jump targets a `common` stub, so it WOULD have
        # been a proxy edge. With the cut it is not proxied and it is not the
        # banking rule's either: it is counted on its own line, and the proxy
        # total is the difference. A report that let the proxy line absorb it
        # would be attributing this tool's own edit to the rule that exists to
        # refuse a join.
        rows, grouped, stats = self.rows_and_stats('trampoline')
        self.assertEqual(stats.trampoline_edges, 1)
        self.assertEqual(stats.proxy_edges, 0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gf.report(grouped, stats, rows, repo=gf.REPO, split='trampoline')
        printed = out.getvalue()
        self.assertIn('by the split mode and not by the banking rule: 1',
                      printed)
        self.assertIn('bank->common edges cut by the per-bank proxy rule: 0',
                      printed)

    def test_the_uncut_mode_reports_no_trampoline_population(self):
        # The paired case: with the cut off the same edge is the proxy rule's,
        # so the two populations swap and neither total is silently constant.
        rows, grouped, stats = self.rows_and_stats('none')
        self.assertEqual(stats.trampoline_edges, 0)
        self.assertEqual(stats.proxy_edges, 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gf.report(grouped, stats, rows, repo=gf.REPO, split='none')
        printed = out.getvalue()
        self.assertNotIn('bank-select trampoline boundary, by the split mode',
                         printed)
        self.assertIn('bank->common edges cut by the per-bank proxy rule: 1',
                      printed)
        self.assertIn('No edge is cut', printed)

    def test_the_split_mode_line_says_it_is_inert_when_nothing_matched(self):
        # Measured, not assumed: the BIOS has no BL51 stubs because it is not
        # this firmware, and a report that claimed a cut there would be
        # claiming an edit that did not happen.
        rows = [{'scope': 'common', 'addr': '0000', 'name': 'x',
                 'type': 'logic', 'evidence': ''}]
        grouped, stats = gf.group_rows(rows, repo=gf.REPO)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gf.report(grouped, stats, rows, repo=gf.REPO)
        self.assertIn('Inert on this component: no listing matched the shape',
                      out.getvalue())

    def test_component_sizes_exclude_components_below_the_minimum(self):
        # `group_rows()` never assigns one, so a table counting them would
        # report a population no reader can find in the file.
        rows, _grouped, _stats = self.rows_and_stats('trampoline')
        sizes = gf.component_sizes(rows, repo=gf.REPO, min_size=2)
        self.assertTrue(all(s >= 2 for s in sizes), sizes)
        self.assertTrue(sizes)
        self.assertEqual(sizes, sorted(sizes, reverse=True))


class CommittedFiles(unittest.TestCase):
    """The committed group files, under the default mode the gate runs."""

    def test_the_committed_group_files_pass_their_own_check(self):
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            rc = gf.check()
        self.assertEqual(rc, 0, err.getvalue() + out.getvalue())

    def test_every_committed_callgraph_row_names_the_cut(self):
        # The calibration requirement, held over the whole file rather than on
        # one fixture: "one of N mutually reachable functions" is false of the
        # firmware and true only of the graph the cut produced, so a row that
        # kept the old sentence is a row describing a graph this repository
        # edited, without saying so.
        with open(gf.EC_GROUPS, newline='') as f:
            rows = [r for r in csv.DictReader(f, strict=True)
                    if r['group_basis'] == 'callgraph']
        self.assertTrue(rows)
        for row in rows:
            self.assertIn('cut at the BL51 bank-select trampoline boundary',
                          row['comment'], row)

    def test_the_regenerated_file_still_passes_the_two_whole_file_rules(self):
        # Both run over the regenerated file, whose component NAMES differ
        # from the ones the split replaced -- which is the point. Checked
        # against names the file already agrees with, the dominant-scope token
        # check would be doing nothing.
        with open(gf.EC_GROUPS, newline='') as f:
            rows = list(csv.DictReader(f, strict=True))
        self.assertEqual(gf.cross_bank_groups(rows), [])
        self.assertEqual(gf.misnamed_callgraph_groups(rows), [])

    def test_the_bios_file_is_inert_under_the_cut(self):
        # Measured rather than assumed. `--apply` rewrote it byte for byte,
        # and this says why: 0 `callgraph` rows and 0 listings matching the
        # shape, so the mode has nothing to act on there.
        with open(gf.BIOS_GROUPS, newline='') as f:
            rows = list(csv.DictReader(f, strict=True))
        self.assertEqual([r for r in rows if r['group_basis'] == 'callgraph'], [])
        with open(gf.BIOS_CSV, newline='') as f:
            ann = list(csv.DictReader(f, strict=True))
        self.assertEqual(bt.trampoline_listings(ann, gf.REPO), {})


class MarkdownOnlyEvidence(unittest.TestCase):
    """Every row in ghidra-functions.csv whose `evidence` names only `.md`
    files must either contribute edges to the call graph or be documented
    as a table cell."""

    def test_every_markdown_only_evidence_row_has_an_index_entry(self):
        # All such rows have listings on disk at (scope, addr) in
        # ec/decompiled/index.csv. The fallback resolver now uses them.
        index = {}
        index_path = os.path.join(gf.REPO, "ec", "decompiled", "index.csv")
        with open(index_path, newline='') as f:
            for row in csv.DictReader(f, strict=True):
                addr = (row.get("addr") or "").upper().replace("0X", "")
                index[(row["program"], addr)] = row.get("out_file") or ""

        with open(gf.EC_CSV, newline='') as f:
            ann_rows = list(csv.DictReader(f, strict=True))

        markdown_only = []
        for row in ann_rows:
            evidence = row.get("evidence") or ""
            has_asm = any(p.strip().endswith(".asm")
                         for p in evidence.split(";"))
            has_md = any(p.strip().endswith(".md")
                        for p in evidence.split(";"))
            if has_md and not has_asm:
                addr = (row.get("addr") or "").upper().replace("0X", "")
                key = (row.get("scope") or "", addr)
                markdown_only.append((key, row))

        # Assert all are in the index.
        for (scope, addr), row in markdown_only:
            key = (scope, addr)
            self.assertIn(key, index,
                         msg="row %s %s %s not in index" % (scope, addr,
                                                             row.get("name")))

    def test_markdown_only_evidence_rows_resolve_via_fallback(self):
        # The fallback resolver `asm_path()` must find all markdown-only rows.
        with open(gf.EC_CSV, newline='') as f:
            ann_rows = list(csv.DictReader(f, strict=True))

        markdown_only = []
        for row in ann_rows:
            evidence = row.get("evidence") or ""
            has_asm = any(p.strip().endswith(".asm")
                         for p in evidence.split(";"))
            has_md = any(p.strip().endswith(".md")
                        for p in evidence.split(";"))
            if has_md and not has_asm:
                markdown_only.append(row)

        # Every such row must resolve to a listing via the fallback.
        resolved_count = 0
        for row in markdown_only:
            path = bt.asm_path(row, gf.REPO)
            if path:
                resolved_count += 1
                self.assertTrue(os.path.isfile(path),
                               msg="resolved path %s does not exist for %s" %
                               (path, row.get("name")))

        # Assert that a non-trivial number resolve.
        self.assertGreater(resolved_count, 50,
                          "fewer than 50 rows resolved; the fallback may be "
                          "broken")


if __name__ == '__main__':
    unittest.main()