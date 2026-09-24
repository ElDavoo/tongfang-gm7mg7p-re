#!/usr/bin/env python3
"""Offline checks for check_site_census.py: committed files only.

The tool joins two vocabularies that were previously only reconciled in prose,
so its failure mode is silence rather than a crash. Loosen the set comparison
that holds them and it starts reporting agreement on a disagreement, still
exits 0, and the only thing that notices is a reader who has already been
misled. So what is pinned here is every way the two vocabularies are *allowed*
to differ -- one case per row of the table in the tool's docstring, each
asserting the checker rejects the disagreement -- plus the cases a loosened
test would let through: a sweep direction nobody recognised, a `read+write`
window that a substring test would have read as a read, a count that drifted
while every citation still resolves.

The fixtures are small enough to write inline, which keeps each case readable
as the disagreement it is about rather than as a diff against a stored file.
They are not the real 0x0860 sites; the last class is, and it is what says the
committed sweep, the committed correspondence and the committed census
currently agree.
"""
import contextlib
import csv
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
# check_site_census imports xdata_register_map by bare module name, the way
# check_register_counts.py imports this one, so the tool directory has to be
# on the path before either is loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_site_census', HERE / 'check_site_census.py')
csc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(csc)
import trace_xdata_refs as tref  # noqa: E402

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')

# The fifteen addresses xdata-086x-dispatch.md §1 sweeps, which is the run
# whose --csv output is the committed sites table --check compares against.
PAGE_ADDRESSES = ("0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A "
                  "0x086B 0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07").split()

# One mapped site in both vocabularies, the smallest fixture that still runs
# every clause: a sweep cell, a mapping row, the two lines the row cites, and
# the census's own classification of them. `read x1` against `read x2` is not
# a disagreement -- the sweep records one row per `MOV DPTR` and the second
# comparison re-reads A without reloading DPTR -- so the base fixture is
# already the many-to-one shape the real 0x0D091 row has.
SITES = {
    '0x0D091': {'addr': '0x0860', 'region': 'bank0', 'access': 'read x1',
                'window': 'movx a,@dptr ; jnz +0x03'},
}
ROWS = [{
    'region': 'bank0', 'file_offset': '0x0D091', 'census_state': 'mapped',
    'census_bucket': 'read', 'census_count': '2',
    'census_refs': 'bank0/D091.c:43,47',
}]
OCCURRENCES = {('bank0/D091.c', 43): ['read'], ('bank0/D091.c', 47): ['read']}
EXPECTED = ({'read': 2, 'write': 0, 'read+write': 0, 'passed-to-call': 0,
             'address-taken': 0}, 2)

# The same totals for a fixture whose only site is a blind one, where the map
# has no bucket to sum.
BLIND = {'read': 0, 'write': 0, 'read+write': 0, 'passed-to-call': 0,
         'address-taken': 0}


def checked(sites=None, rows=None, occurrences=None, expected=None):
    """(problems, agreed, unchecked) for the fixtures with the named parts
    replaced. `None` means "the base version", spelled that way rather than
    with `or` so that an empty dict is a fixture and not a default."""
    return csc.check(SITES if sites is None else sites,
                     ROWS if rows is None else rows,
                     OCCURRENCES if occurrences is None else occurrences,
                     EXPECTED if expected is None else expected, False)


def row(**overrides) -> list:
    """The base mapping row with fields replaced, as the one-row list a
    `rows=` override needs."""
    out = dict(ROWS[0])
    out.update(overrides)
    return [out]


def saying(*needles, **overrides) -> list:
    """Problems containing every needle, out of the fixture the keywords
    replace. The needle is the assertion: a case that passes because *some*
    problem was reported would go green on a checker that had stopped
    comparing the thing the case is about."""
    return [p for p in checked(**overrides)[0] if all(n in p for n in needles)]


class Agreement(unittest.TestCase):
    """The pairs the two vocabularies are allowed to spell the same way."""

    def test_read_against_read_passes(self):
        self.assertEqual(checked(), ([], 1, 0))

    def test_a_call_tail_agrees_with_passed_to_call(self):
        # The one instruction the two methods read differently: the sweep
        # reports the `movx` it decoded, the census reports the call the value
        # went into. The table's third row, and the only one that is an
        # exception rather than a plain set comparison.
        sites = {'0x0D144': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'read x1',
                             'window': 'movx a,@dptr ; lcall 0x7151'}}
        rows = [{'region': 'bank0', 'file_offset': '0x0D144',
                 'census_state': 'mapped', 'census_bucket': 'passed-to-call',
                 'census_count': '1', 'census_refs': 'bank0/D091.c:81'}]
        occurrences = {('bank0/D091.c', 81): ['passed-to-call']}
        expected = (dict(BLIND, **{'passed-to-call': 1}), 1)
        self.assertEqual(checked(sites, rows, occurrences, expected), ([], 1, 0))

    def test_no_movx_against_no_occurrence_agrees(self):
        # 0x0D31C: the sweep decoded a window with no `movx` in it, and the
        # decompile (`return *param_1 & 0x7c;`) names no address. Both methods
        # see nothing, which is agreement about a method, not about the byte.
        sites = {'0x0D31C': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'no movx found in the decoded window',
                             'window': 'ret'}}
        rows = [{'region': 'bank0', 'file_offset': '0x0D31C',
                 'census_state': 'no-occurrence', 'census_bucket': 'none',
                 'census_count': '0', 'census_refs': 'none'}]
        self.assertEqual(checked(sites, rows, {}, (BLIND, 0)), ([], 1, 0))

    def test_the_many_to_one_collapse_is_a_count_not_a_conflict(self):
        # Three `read x1` rows carrying 2, 6 and 6 occurrences, which is the
        # real 0x0860 shape down to the per-line split. If the check compared
        # the two counts per site this would go red on the committed data on
        # day one, and a check that has never been green is a check nobody
        # trusts.
        shapes = (('0x0D091', [(43, 1), (47, 1)]),
                  ('0x0D0EF', [(69, 3), (70, 3)]),
                  ('0x0D117', [(73, 2), (74, 1), (75, 3)]))
        sites, rows, occurrences = {}, [], {}
        for offset, lines in shapes:
            sites[offset] = {'addr': '0x0860', 'region': 'bank0',
                             'access': 'read x1',
                             'window': 'movx a,@dptr ; xrl a,#0x08 ; jz +0x18'}
            rows.append({'region': 'bank0', 'file_offset': offset,
                         'census_state': 'mapped', 'census_bucket': 'read',
                         'census_count': str(sum(n for _, n in lines)),
                         'census_refs': 'bank0/D091.c:'
                                        + ','.join(str(ln) for ln, _ in lines)})
            for line, times in lines:
                occurrences[('bank0/D091.c', line)] = ['read'] * times
        expected = (dict(BLIND, read=14), 14)
        self.assertEqual(checked(sites, rows, occurrences, expected), ([], 3, 0))


class RejectsDisagreement(unittest.TestCase):
    """One case per way the two vocabularies can part company."""

    def test_read_against_write_is_rejected(self):
        self.assertTrue(saying('the two methods disagree',
                               rows=row(census_bucket='write')))

    def test_write_against_read_is_rejected(self):
        sites = {'0x0D281': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'write x1',
                             'window': 'mov a,#0xff ; movx @dptr,a ; sjmp +0x05'}}
        rows = [{'region': 'bank0', 'file_offset': '0x0D281',
                 'census_state': 'mapped', 'census_bucket': 'read',
                 'census_count': '2', 'census_refs': 'bank0/D091.c:43,47'}]
        self.assertTrue(saying('the two methods disagree', sites=sites, rows=rows))

    def test_a_read_plus_write_window_is_not_a_read(self):
        # `read x1, write x1` contains the substring "read x". A site the
        # sweep calls both is not a read, so it cannot be made to agree with a
        # `read` bucket by testing for one word.
        sites = {'0x0D2A0': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'read x1, write x1',
                             'window': 'movx a,@dptr ; inc a ; movx @dptr,a'}}
        self.assertTrue(saying('the two methods disagree', sites=sites,
                               rows=row(file_offset='0x0D2A0')))

    def test_passed_to_call_needs_a_call_in_the_window(self):
        # The agreeing pair above with the `lcall` gone: a read the census
        # calls an argument, and nothing in the window to pass it to.
        self.assertTrue(saying('the two methods disagree',
                               rows=row(census_bucket='passed-to-call')))

    def test_passed_to_call_against_a_write_site_is_rejected(self):
        sites = {'0x0D144': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'write x1', 'window': 'movx @dptr,a'}}
        rows = row(file_offset='0x0D144', census_bucket='passed-to-call',
                   census_count='2')
        self.assertTrue(saying('the two methods disagree', sites=sites, rows=rows))

    def test_a_handoff_site_claiming_a_bucket_is_rejected(self):
        # The decompile names no address where DPTR went to a call, so an
        # occurrence cannot exist and a bucket for one is invented.
        sites = {'0x09E03': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'DPTR handed to lcall 0xbd34 -- direction unresolved here',
                             'window': 'lcall 0xbd34'}}
        rows = row(file_offset='0x09E03', census_count='1',
                   census_refs='bank0/D091.c:43')
        self.assertTrue(saying('a handoff names no address', sites=sites, rows=rows))

    def test_a_handoff_site_that_says_no_occurrence_agrees(self):
        sites = {'0x09E03': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'DPTR handed to lcall 0xbd34 -- direction unresolved here',
                             'window': 'lcall 0xbd34'}}
        rows = [{'region': 'bank0', 'file_offset': '0x09E03',
                 'census_state': 'no-occurrence', 'census_bucket': 'none',
                 'census_count': '0', 'census_refs': 'none'}]
        self.assertEqual(checked(sites, rows, {}, (BLIND, 0)), ([], 1, 0))

    def test_no_occurrence_against_a_read_site_is_rejected(self):
        # The census saw nothing where the sweep decoded a `movx`. One of the
        # two rows is wrong, or the decompiler folded the address away, which
        # is a state this table does not have -- and a loud failure is what it
        # should be until somebody adds one.
        rows = [{'region': 'bank0', 'file_offset': '0x0D091',
                 'census_state': 'no-occurrence', 'census_bucket': 'none',
                 'census_count': '0', 'census_refs': 'none'}]
        self.assertTrue(saying('the two methods disagree', rows=rows,
                               occurrences={}))

    def test_a_code_pointer_is_not_a_register(self):
        # `movc a,@a+dptr` is a CODE pointer, and the census reads the
        # decompile where a table lookup is not an occurrence. Reading it as a
        # read would let a table agree with itself.
        sites = {'0x0D14B': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'movc a,@a+dptr x1 -- CODE pointer, not an XDATA access',
                             'window': 'movc a,@a+dptr'}}
        self.assertTrue(saying('the two methods disagree', sites=sites,
                               rows=row(file_offset='0x0D14B')))

    def test_an_unrecognised_access_is_not_silence(self):
        # A sweep cell in a shape this tool does not know must be rejected,
        # never default to a direction and agree with something. The way this
        # tool learns a new shape is by being red here first.
        sites = {'0x0D091': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'something the walk did not say',
                             'window': 'movx a,@dptr'}}
        self.assertTrue(saying('the two methods disagree', sites=sites))


class ReportsUncheckedRatherThanAgreeing(unittest.TestCase):
    """The `other-program` token, which is the whole calibration of the column."""

    PD_SITE = {'addr': '0x0860', 'region': 'pd-image', 'access': 'read x1',
               'window': 'movx a,@dptr'}
    PD_ROW = {'region': 'pd-image', 'file_offset': '0x25CE4',
              'census_state': 'other-program', 'census_bucket': 'none',
              'census_count': 'na', 'census_refs': 'none'}

    def test_other_program_is_unchecked_not_agreeing(self):
        self.assertEqual(checked({'0x25CE4': self.PD_SITE}, [self.PD_ROW], {},
                                 (BLIND, 0)), ([], 0, 1))

    def test_other_program_cannot_claim_a_measured_zero(self):
        # The census's 0x0860 row is `main-ec`, so a PD site has no count at
        # all -- `na`. A `0` there would be a measured zero, which is a claim
        # about the PD program that nothing on this page supports.
        rows = [dict(self.PD_ROW, census_count='0')]
        self.assertTrue(saying('structurally blind', sites={'0x25CE4': self.PD_SITE},
                               rows=rows, occurrences={}))

    def test_verbose_names_the_unchecked_site(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            _, agreed, unchecked = csc.check({'0x25CE4': self.PD_SITE},
                                             [self.PD_ROW], {}, (BLIND, 0), True)
        self.assertEqual((agreed, unchecked), (0, 1))
        self.assertIn('unchecked 0x25CE4', err.getvalue())


class RejectsAnUnsupportedClaim(unittest.TestCase):
    """A bucket where the census cannot support one is an error, not a gap."""

    BLIND_SITE = {'addr': '0x0860', 'region': 'bank0',
                  'access': 'no movx found in the decoded window', 'window': 'ret'}

    def test_no_occurrence_carrying_a_bucket_is_rejected(self):
        rows = [{'region': 'bank0', 'file_offset': '0x0D31C',
                 'census_state': 'no-occurrence', 'census_bucket': 'read',
                 'census_count': '2', 'census_refs': 'bank0/D091.c:43,47'}]
        self.assertTrue(saying('structurally blind', sites={'0x0D31C': self.BLIND_SITE},
                               rows=rows))

    def test_no_occurrence_carrying_a_citation_is_rejected(self):
        rows = [{'region': 'bank0', 'file_offset': '0x0D31C',
                 'census_state': 'no-occurrence', 'census_bucket': 'none',
                 'census_count': '0', 'census_refs': 'bank0/D091.c:43'}]
        self.assertTrue(saying('no occurrence', 'behind it',
                               sites={'0x0D31C': self.BLIND_SITE}, rows=rows))

    def test_a_mapped_site_with_a_zero_count_is_rejected(self):
        # The shape that would otherwise make a site's bucket agree with
        # nothing: a bucket with no occurrence behind it. "Not visible to the
        # census" is `no-occurrence`, which is a different row.
        self.assertTrue(saying('a mapped site carries census_count 0',
                               rows=row(census_count='0')))

    def test_a_mapped_site_without_a_citation_is_rejected(self):
        self.assertTrue(saying('names no line', rows=row(census_refs='none')))

    def test_a_bucket_outside_the_census_vocabulary_is_rejected(self):
        self.assertTrue(saying('is not one of the census',
                               rows=row(census_bucket='stored')))

    def test_a_count_that_is_not_a_number_is_rejected(self):
        self.assertTrue(saying('is not a number', rows=row(census_count='two')))

    def test_an_unknown_state_is_rejected(self):
        self.assertTrue(saying('census_state', rows=row(census_state='unchecked')))


class RejectsStaleCitations(unittest.TestCase):
    """The assertion that catches a decompile moving out from under the map."""

    def test_a_citation_that_no_longer_resolves_is_rejected(self):
        # The D091.c case: its correction header grew, the line numbers in the
        # comment moved, and a citation to the old ones now points at lines
        # with no occurrence on them.
        self.assertTrue(saying('where the census has no 0x0860 occurrence',
                               rows=row(census_refs='bank0/D091.c:30,34')))

    def test_a_citation_that_classifies_differently_is_rejected(self):
        # A line that still holds an occurrence, but of another bucket. The
        # site's own direction agrees with the map, so this is the only clause
        # that can catch it: the line moved onto a different occurrence.
        occurrences = {('bank0/D091.c', 43): ['read'],
                       ('bank0/D091.c', 47): ['write']}
        self.assertTrue(saying('which the census classifies', 'the map claims read',
                               occurrences=occurrences))

    def test_a_count_that_does_not_match_its_cited_lines_is_rejected(self):
        self.assertTrue(saying('census_count says 3', rows=row(census_count='3')))

    def test_an_unparseable_citation_is_rejected(self):
        self.assertTrue(saying('does not parse', rows=row(census_refs='bank0/D091.c')))

    def test_an_occurrence_no_site_accounts_for_is_rejected(self):
        occurrences = {ref: list(buckets) for ref, buckets in OCCURRENCES.items()}
        occurrences[('bank0/D091.c', 81)] = ['read']
        self.assertTrue(saying('no mapped site accounts for', occurrences=occurrences))

    def test_two_sites_citing_one_occurrence_are_rejected(self):
        sites = {ref: dict(row) for ref, row in SITES.items()}
        sites['0x0D094'] = dict(SITES['0x0D091'])
        rows = ROWS + [dict(ROWS[0], file_offset='0x0D094')]
        self.assertTrue(saying('mapped sites cite this occurrence',
                               sites=sites, rows=rows))


class RejectsAnUnjoinedPair(unittest.TestCase):
    """A site in one file and not the other, in both directions."""

    OTHER = {'addr': '0x0860', 'region': 'bank0', 'access': 'read x1',
             'window': 'movx a,@dptr'}

    def test_a_sweep_site_with_no_mapping_row_is_rejected(self):
        sites = {ref: dict(row) for ref, row in SITES.items()}
        sites['0x0D0EF'] = self.OTHER
        self.assertTrue(saying('with no row in', sites=sites))

    def test_a_mapping_row_for_a_site_the_sweep_lacks_is_rejected(self):
        self.assertTrue(saying('but the sweep has no',
                               rows=ROWS + [dict(ROWS[0], file_offset='0x0D0EF')]))

    def test_a_region_disagreement_is_rejected(self):
        # The same file offset cannot be a different image's byte; the key is
        # an offset precisely because the bank map is not one to one.
        self.assertTrue(saying('mapped as', rows=row(region='pd-image')))

    def test_a_duplicated_offset_is_rejected(self):
        self.assertTrue(saying('two rows in', rows=ROWS + [dict(ROWS[0])]))

    def test_the_join_fails_before_anything_is_compared(self):
        # A half-joined pair produces only the join failure, so a report never
        # mixes "disagrees" with "no row" and sends the reader after the wrong
        # one.
        sites = {ref: dict(row) for ref, row in SITES.items()}
        sites['0x0D0EF'] = self.OTHER
        problems, agreed, unchecked = checked(sites=sites,
                                              rows=row(census_bucket='write'))
        self.assertEqual((agreed, unchecked), (0, 0))
        self.assertTrue(all('no row in' in p for p in problems))


class RejectsATotalsDrift(unittest.TestCase):
    """The hand-typed numbers, against the generated row."""

    def test_per_bucket_totals_are_compared_with_the_register_row(self):
        # Every citation still resolves and every bucket still classifies the
        # way the map says; only the total disagrees with the generated census,
        # which is exactly the hand-typed number drifting. Nothing else here
        # would notice.
        occurrences = {('bank0/D091.c', 43): ['read'] * 2,
                       ('bank0/D091.c', 47): ['read']}
        self.assertTrue(saying('the map sums read to 3',
                               rows=row(census_count='3'),
                               occurrences=occurrences))

    def test_the_refs_total_is_compared_too(self):
        expected = (dict(BLIND, read=2), 3)
        self.assertTrue(saying('refs 3', expected=expected))


class CsvReading(unittest.TestCase):
    """The two committed CSVs, so a change to the tool's idea of the columns is
    caught here rather than as a mystery empty cell in a table."""

    def test_the_census_map_renders_a_bucket_with_its_count(self):
        cells = tref.load_census_map()
        self.assertEqual(cells['0x0D091'], 'read x2')
        self.assertEqual(cells['0x0D144'], 'passed-to-call x1')
        self.assertEqual(cells['0x0D31C'], 'no census occurrence')
        self.assertEqual(cells['0x25CE4'], 'other program')

    def test_a_committed_row_citing_several_lines_is_one_row(self):
        # The commas in `bank0/D091.c:44,48` are the CSV's own quoting: read
        # unquoted, the field shifts and the citation loses its second line --
        # which is how this file was written wrong once already.
        #
        # The line numbers are read out of the committed file rather than
        # written here, because they are a pin into a generated `.c` and every
        # plate-comment edit moves them: issue #135's `name_basis:` line
        # shifted this cell by one and the assertion below caught it, which is
        # the check working. A hardcoded copy would go stale silently the
        # moment the next annotation landed. What is being tested is the
        # quoting and the parse, not the addresses.
        with open(csc.MAPPING_CSV, newline="") as f:
            first = list(csv.DictReader(f))[0]
        self.assertEqual(len(csc.parse_refs(first['census_refs'])), 2)
        where, first_line = csc.parse_refs(first['census_refs'])[0]
        self.assertEqual(first['census_refs'],
                         '%s:%d,%d' % (where, first_line,
                                       csc.parse_refs(first['census_refs'])[1][1]))
        self.assertEqual(csc.parse_refs(first['census_refs']),
                         [(where, first_line),
                          (where, csc.parse_refs(first['census_refs'])[1][1])])

    def test_an_unknown_state_is_an_error_not_a_default_cell(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'map.csv'
            path.write_text('region,file_offset,census_state,census_bucket,'
                            'census_count,census_refs\n'
                            'bank0,0x0D091,probably,read,2,bank0/D091.c:43\n')
            with self.assertRaises(ValueError) as caught:
                tref.load_census_map(str(path))
        self.assertIn('probably', str(caught.exception))


class CheckMode(unittest.TestCase):
    """`--check`, whose whole job is to be red when the table drifts."""

    def checked_table(self, generated: str, path: str) -> tuple:
        """(exit code, stdout, stderr), both streams captured so a passing
        case does not print the tool's own confirmation into the suite's."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = tref.check_table(generated, path)
        return rc, out.getvalue(), err.getvalue()

    def test_a_table_that_reproduces_exits_zero(self):
        with open(csc.SITES_CSV, newline="") as f:
            committed = f.read()
        rc, out, err = self.checked_table(committed, csc.SITES_CSV)
        self.assertEqual(rc, 0, err)
        self.assertIn('reproduces it byte for byte', out)

    def test_one_changed_cell_exits_non_zero(self):
        with open(csc.SITES_CSV, newline="") as f:
            committed = f.read()
        rc, _, err = self.checked_table(committed.replace('read x2', 'read x9', 1),
                                        csc.SITES_CSV)
        self.assertEqual(rc, 1)
        self.assertIn('-0x0860,0x0D091', err)
        self.assertIn('+0x0860,0x0D091', err)

    def test_a_missing_table_exits_non_zero_rather_than_passing(self):
        rc, _, err = self.checked_table('addr\n', str(HERE / 'no-such-table.csv'))
        self.assertEqual(rc, 1)
        self.assertIn('no-such-table.csv', err)


class TheCommittedTree(unittest.TestCase):
    """The real thing: the committed sweep, correspondence and census agree,
    and the sweep's own table still reproduces from the command that names it.

    This is the assertion that would have caught the two vocabularies drifting
    apart in prose. It is also the one that goes red on any future edit that
    parts them, which is the point of having the correspondence as data.
    """

    def run_main(self, module, argv) -> int:
        """module.main() with `argv` in place, stdout and stderr captured, the
        way a reader would run it -- the return code and the line it prints
        are the tool's whole output surface."""
        err, out, saved = io.StringIO(), io.StringIO(), sys.argv
        sys.argv = argv
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = module.main()
        finally:
            sys.argv = saved
        self.assertEqual(rc, 0, err.getvalue())
        return out.getvalue()

    def test_the_committed_join_holds(self):
        out = self.run_main(csc, ['check_site_census.py'])
        self.assertIn('site(s) agree across both methods', out)
        self.assertIn('unchecked (other program)', out)
        self.assertIn('refs 17', out)

    def test_the_committed_sites_table_reproduces_from_the_sweep(self):
        out = self.run_main(tref, ['trace_xdata_refs.py', FIRMWARE,
                                   *PAGE_ADDRESSES, '--csv', '--census-column',
                                   '--check'])
        self.assertIn('reproduces it byte for byte', out)


if __name__ == '__main__':
    unittest.main()
