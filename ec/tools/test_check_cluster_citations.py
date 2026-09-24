#!/usr/bin/env python3
"""Offline checks for check_cluster_citations.py: committed files only.

The tool is a pointer-checker, so its failure mode is silence rather than a
crash. Loosen a regex and it stops catching drift while still exiting 0, and
the only thing that notices is a reader who has already been misled. So what
is pinned here is the line between what the tool claims and what it skips:
each rule that makes it conservative gets a case saying so, because a skip
that is not deliberate is the bug.

The fixtures are small enough to write inline, which keeps each case readable
as the sentence it is about rather than as a diff against a stored file. The
census they check against is not the real one; the last case is, and it is
what says the tree's prose currently agrees with the CSVs beside it.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    'check_cluster_citations', HERE / 'check_cluster_citations.py')
ccc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccc)

# A census small enough to reason about by hand: two clusters that share no
# address, which is the property the real main-ec-002 and main-ec-003 also have
# and the reason a wrong id cannot be caught by "close enough".
MEMBERS = {
    'main-ec-002': {'0x044C', '0x0860', '0x086E'},
    'main-ec-003': {'0x0460', '0x08A8'},
}
KNOWN = {'0x044C', '0x0860', '0x086E', '0x0460', '0x08A8', '0x06C6', '0x09CE'}


def cited(text, members=None):
    """(count, first address) the tool reports for one piece of prose."""
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
        f.write(text)
        path = f.name
    try:
        problems, _ = ccc.check(path, members or MEMBERS, KNOWN, False)
    finally:
        os.unlink(path)
    return len(problems), problems[0][3] if problems else None


class ReportsRealDrift(unittest.TestCase):
    """The four shapes issue #253 found, and the two numbers they turn on."""

    def test_wrong_id_with_one_address(self):
        n, addr = cited('The `0x0860` run is in cluster `main-ec-003`.\n')
        self.assertEqual((n, addr), (1, '0x0860'))

    def test_right_id_is_silent(self):
        self.assertEqual(cited('The `0x0860` run is in cluster `main-ec-002`.\n'), (0, None))

    def test_address_in_either_named_cluster_passes(self):
        # The weaker sense the docstring promises: a unit naming two clusters
        # is satisfied if the address is in one of them.
        text = ('the clustering put `0x0860` in `main-ec-002` and `0x08A8` in '
                '`main-ec-003`\n')
        self.assertEqual(cited(text), (0, None))

    def test_address_in_neither_named_cluster_fails(self):
        text = 'the clustering put `0x06C6` in `main-ec-002` and `main-ec-003`\n'
        n, addr = cited(text)
        self.assertEqual((n, addr), (1, '0x06C6'))

    def test_wrapped_attribution_is_still_seen(self):
        # The manual-fan-ctrl-0751.md case: the address and the id it is wrong
        # about are on different lines, and a line-based scan misses it.
        text = ('The one reader found for `0x0860` (bank1 `0xA987`) was not\n'
                'decoded, and the members of the `main-ec-003` cluster are unnamed.\n')
        n, addr = cited(text)
        self.assertEqual((n, addr), (1, '0x0860'))

    def test_reported_line_is_the_address_line_not_the_unit_start(self):
        text = ('A sentence that opens here and names no address, and goes on.\n'
                'It mentions `0x0860` and the `main-ec-003` cluster in one breath.\n')
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
            f.write(text)
            path = f.name
        try:
            problems, _ = ccc.check(path, MEMBERS, KNOWN, False)
        finally:
            os.unlink(path)
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0][1], 2)


class SkipsDeliberately(unittest.TestCase):
    """Every rule that makes the tool conservative, as a case saying so."""

    def test_denial_is_skipped(self):
        text = '`0x08A8` and `0x06C6` are not in `main-ec-002`, and both reload.\n'
        self.assertEqual(cited(text), (0, None))

    def test_singleton_wording_is_skipped(self):
        # "is a size-1 cluster on its own" denies membership in the cluster the
        # same sentence names, and does it without a negation word.
        text = ('nine of the ten are in `main-ec-002`, and the tenth, `0x06C6`, '
                'is a cluster on its own\n')
        self.assertEqual(cited(text), (0, None))

    def test_mention_without_a_membership_claim_is_skipped(self):
        # The xdata-register-map.md §5 row shape: a cluster id, its address
        # range, and a title naming a byte the shared function reads.
        text = ('| `main-ec-003` | 43 | 4,965 | `0x0460`-`0x09CE` | none | the '
                '`0x06C6`/`0x0860` gate block |\n')
        self.assertEqual(cited(text), (0, None))

    def test_code_address_is_not_an_xdata_address(self):
        # bank0:0x9D9B is code. It is not in the census, so it is not a
        # cluster member claim, however much it looks like one.
        text = 'The `0x9D9B` routine in cluster `main-ec-003` is where it happens.\n'
        self.assertEqual(cited(text), (0, None))

    def test_adjacent_list_items_do_not_bleed(self):
        # Without a sentence boundary at a list marker, the first item's
        # cluster id reaches into the next item's addresses.
        text = ('The census is wrong for this block.\n'
                '- A note about `main-ec-003`, with no address.\n'
                '- The `0x08A8` listing is separate.\n')
        self.assertEqual(cited(text), (0, None))

    def test_table_rows_are_separate_units(self):
        text = ('| `main-ec-003` | 43 | 4,965 | `0x0460` | none | the block |\n'
                '| `main-ec-002` | 44 | 248 | `0x044C` | 4 | the gate block |\n')
        self.assertEqual(cited(text), (0, None))


class CensusParsing(unittest.TestCase):
    """The CSV read, so a change to the tool's idea of the columns is caught."""

    def test_members_and_known_addresses(self):
        header = 'cluster_id,program,size,refs,addrs\n'
        with tempfile.TemporaryDirectory() as d:
            clusters = os.path.join(d, 'clusters.csv')
            registers = os.path.join(d, 'registers.csv')
            with open(clusters, 'w') as f:
                f.write(header)
                f.write('main-ec-002,main-ec,2,10,0x0860 0x086E\n')
            with open(registers, 'w') as f:
                f.write('addr,program,cluster_id\n')
                f.write('0x0860,main-ec,main-ec-002\n')
                f.write('0x086E,main-ec,main-ec-002\n')
            old = (ccc.CLUSTERS, ccc.REGISTERS)
            ccc.CLUSTERS, ccc.REGISTERS = clusters, registers
            try:
                members, known = ccc.census()
            finally:
                ccc.CLUSTERS, ccc.REGISTERS = old
        self.assertEqual(members, {'main-ec-002': {'0x0860', '0x086E'}})
        self.assertEqual(known, {'0x0860', '0x086E'})


class TheCommittedTree(unittest.TestCase):
    """The real thing: the prose and the CSVs beside it currently agree.

    This is the assertion that would have caught issue #253. It is also the
    one that goes red on any future edit that drifts an id, which is the
    point of having the tool in the tree at all.
    """

    def test_committed_prose_matches_committed_census(self):
        err = io.StringIO()
        out = io.StringIO()
        argv = sys.argv
        sys.argv = ['check_cluster_citations.py']
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = ccc.main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0, err.getvalue())
        self.assertIn('every checked', out.getvalue())


if __name__ == '__main__':
    unittest.main()
