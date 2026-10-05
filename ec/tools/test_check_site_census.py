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
currently agree -- for every address of the page, since the correspondence is
one file per address and `--all` is what covers them.

**A third outcome has to be asserted as an outcome, not as a non-failure.**
`census-blind` and `window-cut` are neither agreement nor errors, so a case that
only asserted `problems == []` would go green on a checker that had started
counting them as agreement -- which is the exact failure the whole suite
exists to catch, one level up. The cases below therefore assert the counters
as well as the empty problem list.
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
    """(problems, agreed, unchecked, blind, cut, callee_dptr, sites) for the
    fixtures with the named parts replaced. `None` means "the base version",
    spelled that way rather than with `or` so that an empty dict is a fixture
    and not a default. The tail four are what the summary line reports beyond
    agreement, and the cases below that assert an outcome are asserting one of
    them."""
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
        self.assertEqual(checked(), ([], 1, 0, 0, 0, 0, 1))

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
        self.assertEqual(checked(sites, rows, occurrences, expected),
                         ([], 1, 0, 0, 0, 0, 1))

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
        self.assertEqual(checked(sites, rows, {}, (BLIND, 0)),
                         ([], 1, 0, 0, 0, 0, 1))

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
        self.assertEqual(checked(sites, rows, occurrences, expected),
                         ([], 3, 0, 0, 0, 0, 3))


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
        # A handoff names no direction, so it cannot corroborate one.
        # `address-taken` is the single exception and has its own cases in
        # `AddressTakenIsItsOwnVocabularyRow` -- it is a pointer, not a
        # direction, so it is not a read or a write the sweep contradicted.
        # Everything else here is a bucket invented for a site that named none.
        sites = {'0x09E03': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'DPTR handed to lcall 0xbd34 -- direction unresolved here',
                             'window': 'lcall 0xbd34'}}
        rows = row(file_offset='0x09E03', census_count='1',
                   census_refs='bank0/D091.c:43')
        self.assertTrue(saying('a handoff names no direction', sites=sites, rows=rows))

    def test_a_handoff_site_that_says_no_occurrence_agrees(self):
        sites = {'0x09E03': {'addr': '0x0860', 'region': 'bank0',
                             'access': 'DPTR handed to lcall 0xbd34 -- direction unresolved here',
                             'window': 'lcall 0xbd34'}}
        rows = [{'region': 'bank0', 'file_offset': '0x09E03',
                 'census_state': 'no-occurrence', 'census_bucket': 'none',
                 'census_count': '0', 'census_refs': 'none'}]
        self.assertEqual(checked(sites, rows, {}, (BLIND, 0)),
                         ([], 1, 0, 0, 0, 0, 1))

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


class ReportsBlindRatherThanAgreeing(unittest.TestCase):
    """`census-blind`: the sweep decoded an access the C-level reader does not
    name. It is a third outcome and the case is that it is neither of the other
    two -- asserting the count is asserting it is not agreement and not failure,
    which is the only property that makes it safe to have."""

    BLIND_SITE = {'addr': '0x1F01', 'region': 'bank0', 'access': 'write x1',
                  'window': 'mov a,#0x20 ; movx @dptr,a'}
    BLIND_ROW = {'region': 'bank0', 'file_offset': '0x0D6B5',
                 'census_state': 'census-blind', 'census_bucket': 'none',
                 'census_count': '0', 'census_refs': 'none'}

    def test_a_decoded_access_the_decompile_does_not_name_is_blind(self):
        problems, agreed, unchecked, blind, cut, _, seen = checked(
            {'0x0D6B5': self.BLIND_SITE}, [self.BLIND_ROW], {}, (BLIND, 0))
        self.assertEqual((problems, agreed, unchecked, cut), ([], 0, 0, 0))
        self.assertEqual(blind, 1)

    def test_blind_is_not_an_error(self):
        # The shape this state exists for. Reporting it as a failure would be a
        # claim about the decompiler; the tool has no evidence for one.
        self.assertFalse(checked({'0x0D6B5': self.BLIND_SITE}, [self.BLIND_ROW],
                                 {}, (BLIND, 0))[0])

    def test_blind_is_not_agreement_either(self):
        # The other half. Counting it as agreement is the claim that a site
        # where only one method saw something has been corroborated.
        self.assertEqual(checked({'0x0D6B5': self.BLIND_SITE}, [self.BLIND_ROW],
                                 {}, (BLIND, 0))[1], 0)

    def test_a_site_with_no_decoded_access_cannot_be_blind(self):
        # `census-blind` asserts the sweep decoded something. On a window with
        # no `movx` it would be a claim about a site neither method saw, and
        # the state that says that is `no-occurrence`.
        sites = {'0x0D31C': {'addr': '0x1F01', 'region': 'bank0',
                             'access': 'no movx found in the decoded window',
                             'window': 'ret'}}
        rows = [dict(self.BLIND_ROW, file_offset='0x0D31C')]
        self.assertTrue(saying('the two methods disagree', sites=sites, rows=rows,
                               occurrences={}))

    def test_a_handoff_cannot_be_blind(self):
        # A handoff is `DPTR handed to <call>`: the sweep named no direction
        # either, so there is no decoded access for `census-blind` to be about.
        sites = {'0x09E03': {'addr': '0x1F01', 'region': 'bank0',
                             'access': 'DPTR handed to lcall 0xbd34 -- '
                                       'direction unresolved here',
                             'window': 'lcall 0xbd34'}}
        rows = [dict(self.BLIND_ROW, file_offset='0x09E03')]
        self.assertTrue(saying('a handoff names no direction', sites=sites,
                               rows=rows, occurrences={}))

    def test_blind_cannot_claim_a_bucket_or_a_citation(self):
        # The blind states' own bucket/count/refs discipline, which is what
        # stops `census-blind` from becoming a bucket with no occurrence behind
        # it wearing a different name.
        for field, value, needle in (
                ('census_bucket', 'write', 'structurally blind'),
                ('census_count', '1', 'structurally blind'),
                ('census_refs', 'bank0/D091.c:43', 'no occurrence')):
            with self.subTest(field=field):
                rows = [dict(self.BLIND_ROW, **{field: value})]
                self.assertTrue(saying(needle, sites={'0x0D6B5': self.BLIND_SITE},
                                       rows=rows, occurrences={}))

    def test_verbose_names_the_blind_site(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            csc.check({'0x0D6B5': self.BLIND_SITE}, [self.BLIND_ROW], {},
                      (BLIND, 0), True)
        self.assertIn('blind 0x0D6B5', err.getvalue())


class WindowCutRatherThanDisagreeing(unittest.TestCase):
    """A second row at one site, admitted only where the sweep's window stopped
    at a *conditional* branch before the access. The `0x086B` clamp shape, and
    the tails that are not conditional branches are cases below."""

    CLAMP_SITE = {'addr': '0x086B', 'region': 'bank0', 'access': 'read x1',
                  'window': 'movx a,@dptr ; setb c ; subb a,#0x23 ; jc +0x03'}
    READ_ROW = {'region': 'bank0', 'file_offset': '0x09E41',
                'census_state': 'mapped', 'census_bucket': 'read',
                'census_count': '2', 'census_refs': 'bank0/9D9B.c:80'}
    WRITE_ROW = {'region': 'bank0', 'file_offset': '0x09E41',
                 'census_state': 'mapped', 'census_bucket': 'write',
                 'census_count': '1', 'census_refs': 'bank0/9D9B.c:81'}
    OCC = {('bank0/9D9B.c', 80): ['read', 'read'],
           ('bank0/9D9B.c', 81): ['write']}
    EXPECTED = (dict(BLIND, read=2, write=1), 3)

    def test_a_store_behind_the_branch_is_window_cut_not_a_disagreement(self):
        problems, agreed, unchecked, blind, cut, _, seen = checked(
            {'0x09E41': self.CLAMP_SITE}, [self.READ_ROW, self.WRITE_ROW],
            self.OCC, self.EXPECTED)
        self.assertEqual(problems, [])
        self.assertEqual((agreed, cut, seen), (1, 1, 1))

    def test_the_same_store_at_a_window_that_did_not_stop_is_rejected(self):
        # The narrowness, and the half that matters: without the branch the
        # second row is a plain bucket the sweep contradicted, which is the
        # error `check()` was written to raise.
        sites = {'0x09E41': dict(self.CLAMP_SITE,
                                  window='movx a,@dptr ; mov r7,a')}
        self.assertTrue(saying('the two methods disagree', sites=sites,
                               rows=[self.READ_ROW, self.WRITE_ROW],
                               occurrences=self.OCC, expected=self.EXPECTED))

    def test_a_ret_terminated_window_admits_no_extra_row(self):
        # The other half of the narrowness, and the one a wider tuple lost: a
        # window ending at an *unconditional* terminator stopped because the
        # straight-line run ended, with no fall-through arm for an access to
        # hide in. This is the real `0x0865` `0x0BBF7` window and the real
        # construction -- the same site, a `read` row the sweep agrees with and
        # a second `write` row the sweep contradicts -- and it has to be the
        # plain disagreement.
        sites = {'0x0BBF7': {'addr': '0x0865', 'region': 'bank0',
                             'access': 'read x1',
                             'window': 'movx a,@dptr ; clr c ; subb a,r7 ; ret'}}
        rows = [{'region': 'bank0', 'file_offset': '0x0BBF7',
                 'census_state': 'mapped', 'census_bucket': 'read',
                 'census_count': '1', 'census_refs': 'bank0/BBF2.c:19'},
                {'region': 'bank0', 'file_offset': '0x0BBF7',
                 'census_state': 'mapped', 'census_bucket': 'write',
                 'census_count': '1', 'census_refs': 'bank0/BBF2.c:20'}]
        occ = {('bank0/BBF2.c', 19): ['read'], ('bank0/BBF2.c', 20): ['write']}
        self.assertTrue(saying('the two methods disagree', sites=sites,
                               rows=rows, occurrences=occ,
                               expected=(dict(BLIND, read=1, write=1), 2)))

    def test_every_unconditional_tail_the_sweep_commits_is_rejected(self):
        # The same construction at each unconditional terminator the page's own
        # windows end in, so the tuple cannot be widened by a future sweep
        # without a test failing. Read from the committed table rather than
        # listed, so a tail that appears one day is covered the day it appears.
        wanted = {"ret", "reti", "sjmp", "ljmp", "jmp @a+dptr"}
        seen = set()
        for row in csc.read_csv(csc.SITES_CSV):
            tail = row["window"].rsplit(" ; ", 1)[-1].strip()
            if tail not in wanted:
                continue
            seen.add(tail)
            sites = {row['file_offset']: dict(row, window=f'movx a,@dptr ; {tail}')}
            rows = [{'region': row['region'], 'file_offset': row['file_offset'],
                     'census_state': 'mapped', 'census_bucket': 'read',
                     'census_count': '1', 'census_refs': 'bank0/BBF2.c:19'},
                    {'region': row['region'], 'file_offset': row['file_offset'],
                     'census_state': 'mapped', 'census_bucket': 'write',
                     'census_count': '1', 'census_refs': 'bank0/BBF2.c:20'}]
            occ = {('bank0/BBF2.c', 19): ['read'],
                   ('bank0/BBF2.c', 20): ['write']}
            self.assertTrue(
                saying('the two methods disagree', sites=sites, rows=rows,
                       occurrences=occ,
                       expected=(dict(BLIND, read=1, write=1), 2)),
                f"{row['addr']} {row['file_offset']}: {tail!r}")
        self.assertTrue(seen, "no committed window ends at an unconditional "
                              "tail; this case has stopped testing anything")

    def test_a_site_with_no_row_the_sweep_agrees_with_is_rejected(self):
        # `second_row` means "this site also has a row the sweep's direction
        # names", so a site whose *only* row contradicts the sweep is an error
        # even with a branch in its window. Dropping the read row is what makes
        # this the case -- it is the one a check keyed on row order would let
        # through, since the write row is then first and last.
        problems = checked({'0x09E41': self.CLAMP_SITE}, [self.WRITE_ROW],
                           {('bank0/9D9B.c', 81): ['write']},
                           (dict(BLIND, write=1), 1))[0]
        self.assertTrue(any('the two methods disagree' in p for p in problems))

    def test_the_allowance_needs_a_row_the_sweep_does_agree_with(self):
        # The same site with the read row present is the `0x086B` clamp shape
        # and passes, so the two cases together are what pins the condition on
        # the sibling row rather than on the window alone.
        self.assertEqual(
            checked({'0x09E41': self.CLAMP_SITE},
                    [dict(self.WRITE_ROW, census_count='1'),
                     self.READ_ROW], self.OCC,
                    (dict(BLIND, read=2, write=1), 3))[0], [])

    def test_a_window_cut_row_still_has_its_citation_checked(self):
        # The clause a third outcome must not lose. A `window-cut` row carrying
        # a line the census has no occurrence for is a stale citation, and it
        # has to fail exactly as a `mapped` row's would.
        rows = [self.READ_ROW, dict(self.WRITE_ROW,
                                    census_refs='bank0/9D9B.c:30')]
        # The fixture's address is the default one, so that is what the
        # message names; what is under test is that it is named at all.
        self.assertTrue(saying('where the census has no',
                               sites={'0x09E41': self.CLAMP_SITE}, rows=rows,
                               occurrences=self.OCC, expected=self.EXPECTED))

    def test_a_window_cut_row_still_counts_its_occurrence_once(self):
        # Same reason, the other direction: dropping the write row leaves
        # `9D9B.c:81` unaccounted for even though the site still passes on its
        # own, so the per-occurrence join is what catches it.
        self.assertTrue(saying('no mapped row accounts for',
                               sites={'0x09E41': self.CLAMP_SITE},
                               rows=[self.READ_ROW], occurrences=self.OCC,
                               expected=self.EXPECTED))


class AddressTakenIsItsOwnVocabularyRow(unittest.TestCase):
    """`address-taken` names no direction, so it can only be admitted against a
    sweep cell that names no direction either."""

    TAKEN_SITE = {'addr': '0x0866', 'region': 'bank0', 'access': 'read x1',
                  'window': 'movx a,@dptr'}
    TAKEN_ROW = {'region': 'bank0', 'file_offset': '0x09DFB',
                 'census_state': 'mapped', 'census_bucket': 'address-taken',
                 'census_count': '1', 'census_refs': 'bank0/9D9B.c:62'}
    OCC = {('bank0/9D9B.c', 62): ['address-taken']}
    EXPECTED = (dict(BLIND, **{'address-taken': 1}), 1)

    def test_address_taken_against_a_bare_movx_read_agrees(self):
        # `movx a,@dptr` on its own is the encoding of an address being taken,
        # which is what `&XDATA_0866` in the decompile is. One instruction, two
        # vocabularies, and neither claims a direction.
        problems, agreed = checked({'0x09DFB': self.TAKEN_SITE},
                                   [self.TAKEN_ROW], self.OCC,
                                   self.EXPECTED)[:2]
        self.assertEqual((problems, agreed), ([], 1))

    def test_address_taken_against_a_handoff_agrees(self):
        # The other half of the row: `mov DPTR,#0x086B ; lcall 0xbd34` is
        # `pbVar4 = &XDATA_086B` in the decompile, and the handoff names no
        # direction to contradict.
        sites = {'0x09DFB': {'addr': '0x0866', 'region': 'bank0',
                             'access': 'DPTR handed to lcall 0xbd34 -- '
                                       'direction unresolved here',
                             'window': 'lcall 0xbd34'}}
        self.assertEqual(checked(sites, [self.TAKEN_ROW], self.OCC,
                                 self.EXPECTED)[:2], ([], 1))

    def test_address_taken_against_a_window_with_more_in_it_is_rejected(self):
        # The narrowness. `movx a,@dptr ; mov r7,a` is the sweep reporting what
        # it did with the byte, and `address-taken` against it is a
        # disagreement rather than a second reading of one instruction.
        sites = {'0x09DFB': dict(self.TAKEN_SITE,
                                  window='movx a,@dptr ; mov r7,a')}
        self.assertTrue(saying('the two methods disagree', sites=sites,
                               rows=[self.TAKEN_ROW], occurrences=self.OCC,
                               expected=self.EXPECTED))

    def test_address_taken_against_a_write_is_rejected(self):
        sites = {'0x09DFB': dict(self.TAKEN_SITE, access='write x1')}
        self.assertTrue(saying('the two methods disagree', sites=sites,
                               rows=[self.TAKEN_ROW], occurrences=self.OCC,
                               expected=self.EXPECTED))

    def test_is_bare_read_is_exact(self):
        # The predicate is what makes the row narrow, so its edge is the
        # interesting part: whitespace is stripped and nothing else is.
        self.assertTrue(csc.is_bare_read('  movx a,@dptr  '))
        self.assertFalse(csc.is_bare_read('movx a,@dptr ; mov r7,a'))
        self.assertFalse(csc.is_bare_read('movx @dptr,a'))


class FlowTailMatchesTheDecoder(unittest.TestCase):
    """`FLOW_TAIL` and `BRANCH_TAIL` are written out by hand, so they are pinned
    against the table that decides when a window ends. One opcode in that set
    renders as `clr` rather than as a tail mnemonic and is excluded here for the
    reason `FLOW_TAIL`'s own comment gives; this is where that exclusion is
    checked rather than asserted in prose.

    The two tuples answer different questions and the difference is load-bearing
    -- `ends_in_branch()` admits a `window-cut` row only on `BRANCH_TAIL`, so a
    tuple that drifts wide again is a weaker check than the tool's docstring
    says it is. Pinning the narrowing here is what stops that."""

    # `0xC1` renders as `clr <bit>`, which is not a tail form. **`0xB6`/`0xB7`
    # were in this set until issue #1153 named them**: they are `CJNE @Ri,#data,rel`
    # and `mnemonic()` used to print `db` for both, so they were excluded for
    # want of a mnemonic. Naming them adds nothing to the rendered set --
    # `cjne` is already contributed by `0xB4`/`0xB5`/`0xB8`-`0xBF`, which are in
    # `FLOW_OPCODES` -- so dropping them here leaves `FLOW_TAIL` exactly as it
    # was, and `test_the_tuple_is_the_flow_opcode_table_minus_the_unrenderable`
    # is what proves it rather than this comment asserting it.
    UNRENDERABLE = {0xC1}

    def rendered(self) -> set:
        import disasm8051
        out = set()
        for op in disasm8051.FLOW_OPCODES - self.UNRENDERABLE:
            n = disasm8051.OPCODE_LEN[op]
            out.add(disasm8051.mnemonic(
                bytes([op] + [0] * (n - 1)), 0).split()[0])
        return out

    def test_the_tuple_is_the_flow_opcode_table_minus_the_unrenderable(self):
        self.assertEqual(set(csc.FLOW_TAIL), self.rendered())

    def test_the_branch_tuple_is_the_conditional_subset_and_nothing_more(self):
        # What separates the two: a conditional branch has an arm the walk
        # cannot reach, and an unconditional terminator does not. So this is
        # exactly the derived set minus the forms that fall through to nothing
        # and minus the call forms `CALL_TAIL` already carries.
        excluded = csc.CALL_TAIL + ("jmp", "ljmp", "sjmp", "ret", "reti")
        self.assertEqual(set(csc.BRANCH_TAIL),
                         self.rendered() - set(excluded))

    def test_no_unconditional_terminator_is_in_the_branch_tuple(self):
        # The case the narrowing exists for, stated directly rather than
        # derived: none of these has a fall-through arm, so nothing can hide
        # behind one and the `window-cut` allowance must not apply to them.
        for tail in ("ret", "reti", "sjmp", "ljmp", "jmp @a+dptr", "lcall",
                     "acall", "ajmp"):
            self.assertNotIn(tail.split(" ")[0], csc.BRANCH_TAIL, tail)

    def test_the_unrenderable_opcodes_really_do_not_render_as_a_mnemonic(self):
        # The exclusion is only sound because this one does not render as a
        # tail mnemonic. If the table grows one, this fails and the exclusion
        # has to be re-examined rather than left in place. `db` stays in the
        # accepted pair: it is the render for any byte value the manual assigns
        # no instruction, and a future opcode joining this set would arrive as
        # one.
        import disasm8051
        for op in sorted(self.UNRENDERABLE & disasm8051.FLOW_OPCODES):
            n = disasm8051.OPCODE_LEN[op]
            name = disasm8051.mnemonic(bytes([op] + [0] * (n - 1)), 0).split()[0]
            self.assertIn(name, ("db", "clr"))

    def test_ends_in_branch_agrees_with_the_table_for_every_committed_window(self):
        # The predicate reads the committed `window` cell, so the only way it
        # can be wrong about the tree is if a tail mnemonic is in neither list.
        # Read over every window the page's sweep commits.
        for row in csc.read_csv(csc.SITES_CSV):
            tail = row["window"].rsplit(" ; ", 1)[-1].strip()
            self.assertEqual(bool(tail) and tail.split(" ")[0] in csc.BRANCH_TAIL,
                             csc.ends_in_branch(row["window"]),
                             f"{row['addr']} {row['file_offset']}: {tail!r}")


class ReportsUncheckedRatherThanAgreeing(unittest.TestCase):
    """The `other-program` token, which is the whole calibration of the column."""

    PD_SITE = {'addr': '0x0860', 'region': 'pd-image', 'access': 'read x1',
               'window': 'movx a,@dptr'}
    PD_ROW = {'region': 'pd-image', 'file_offset': '0x25CE4',
              'census_state': 'other-program', 'census_bucket': 'none',
              'census_count': 'na', 'census_refs': 'none'}

    def test_other_program_is_unchecked_not_agreeing(self):
        self.assertEqual(checked({'0x25CE4': self.PD_SITE}, [self.PD_ROW], {},
                                 (BLIND, 0)), ([], 0, 1, 0, 0, 0, 1))

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
            _, agreed, unchecked, blind, cut, _, _ = csc.check(
                {'0x25CE4': self.PD_SITE}, [self.PD_ROW], {}, (BLIND, 0), True)
        self.assertEqual((agreed, unchecked, blind, cut), (0, 1, 0, 0))
        self.assertIn('unchecked 0x25CE4', err.getvalue())


class CalleeSetDPtrIsNotAgreement(unittest.TestCase):
    """Issue #799: both methods missing the same byte is not corroboration.

    `0x0D191` and `0x0D249` are stores whose DPTR `0xD319` loaded. The sweep
    has no `MOV DPTR,#0x0860` at either and the decompiled C charges them to
    `0x0864` and to nothing, so before this state existed the pair had nowhere
    to go and the checker's only options were `agree` or `error`. What is
    pinned here is that the third option is its own outcome, that it is never
    counted as agreement, and that either method being wrong about it still
    fails.
    """

    SITE = {'addr': '0x0860', 'region': 'bank0',
            'access': 'write x1, DPTR from 0xD319',
            'window': 'movx @dptr,a ; ljmp 0xd28e'}
    ROW = {'region': 'bank0', 'file_offset': '0x0D191',
           'census_state': 'dptr-from-callee', 'census_bucket': 'none',
           'census_count': '0', 'census_refs': 'none'}

    def test_the_pair_is_accepted_and_reported_on_its_own(self):
        problems, agreed, unchecked, blind, cut, callee, _ = checked(
            sites={'0x0D191': self.SITE}, rows=[self.ROW], occurrences={},
            expected=(BLIND, 0))
        self.assertEqual(problems, [])
        self.assertEqual((agreed, callee, unchecked), (0, 1, 0))
        self.assertEqual((blind, cut), (0, 0))

    def test_it_is_never_counted_as_agreement(self):
        # The regression the issue is about: a checker that returned `agree`
        # here would report two independent-looking methods on a site neither
        # of them can see.
        _, agreed, _, _, _, callee, _ = checked(
            sites={'0x0D191': self.SITE}, rows=[self.ROW], occurrences={},
            expected=(BLIND, 0))
        self.assertEqual(agreed, 0)
        self.assertEqual(callee, 1)

    def test_the_sweep_cell_alone_is_an_error(self):
        # The sweep found the site through a callee and the map does not say
        # so, which would leave the site out of the per-bucket totals too.
        sites = dict(SITES, **{'0x0D191': self.SITE})
        rows = ROWS + [dict(self.ROW, census_state='mapped',
                            census_bucket='read', census_count='1',
                            census_refs='bank0/D091.c:43')]
        occurrences = {('bank0/D091.c', 43): ['read'] * 2,
                       ('bank0/D091.c', 47): ['read']}
        self.assertTrue(saying('only set of pairs', sites=sites, rows=rows,
                               occurrences=occurrences,
                               expected=(dict(BLIND, read=3), 3)))

    def test_the_map_state_alone_is_an_error(self):
        # The map says the site was found through a callee; the sweep's own
        # cell says it was not, and one of the two is stale.
        sites = dict(SITES, **{'0x0D0EF': {'addr': '0x0860', 'region': 'bank0',
                                           'access': 'read x1',
                                           'window': 'movx a,@dptr'}})
        rows = ROWS + [dict(self.ROW, file_offset='0x0D0EF')]
        self.assertTrue(saying('only set of pairs', sites=sites, rows=rows,
                               occurrences=OCCURRENCES))

    def test_a_plain_write_cell_does_not_satisfy_the_callee_state(self):
        # `write x1` and `write x1, DPTR from 0xD319` both contain "write x1",
        # so a checker that read the direction by substring would call this
        # site an ordinary mapped write and make the two agree.
        rows = [dict(self.ROW, file_offset='0x0D091')]
        sites = {'0x0D091': dict(SITES['0x0D091'], access='write x1')}
        self.assertTrue(saying('only set of pairs', sites=sites, rows=rows,
                               occurrences=OCCURRENCES))

    def test_it_contributes_to_no_bucket_total(self):
        # The census sees no occurrence there, so folding the site's zero into
        # a bucket would be the tool asserting a measured zero it does not
        # have. The totals it checks are the base fixture's, unchanged.
        self.assertEqual(checked(sites={'0x0D091': SITES['0x0D091']},
                                 rows=[self.ROW], occurrences={},
                                 expected=(BLIND, 0))[0],
                         [p for p in checked(rows=[self.ROW], occurrences={},
                                             expected=(BLIND, 0))[0]])

    def test_a_bucket_claimed_on_this_state_is_rejected(self):
        rows = [dict(self.ROW, census_bucket='write')]
        self.assertTrue(saying('structurally blind', sites={'0x0D191': self.SITE},
                               rows=rows, occurrences={}))

    def test_verbose_names_the_callee_site(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            csc.check({'0x0D191': self.SITE}, [self.ROW], {}, (BLIND, 0), True)
        self.assertIn('callee-dptr 0x0D191', err.getvalue())

    def test_the_dp_from_spelling_is_one_string_with_the_tool(self):
        # Two hand-kept copies of one spelling is a table and a checker
        # agreeing by accident waiting to happen, which is the whole failure
        # this state exists to name.
        self.assertEqual(csc.DPTR_FROM, tref.DPTR_FROM)


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
        self.assertTrue(saying('no mapped row accounts for',
                               occurrences=occurrences))

    def test_two_sites_citing_one_occurrence_are_rejected(self):
        sites = {ref: dict(row) for ref, row in SITES.items()}
        sites['0x0D094'] = dict(SITES['0x0D091'])
        rows = ROWS + [dict(ROWS[0], file_offset='0x0D094')]
        self.assertTrue(saying('mapped rows cite this occurrence',
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
        # Two rows for one offset *in one bucket* is the duplicate. Two rows
        # for one offset in different buckets is the documented shape -- a
        # window that stopped at a branch before the second access -- so the
        # clause names the bucket rather than the offset.
        self.assertTrue(saying('two rows for bucket', 'read',
                               rows=ROWS + [dict(ROWS[0])]))

    def test_the_join_fails_before_anything_is_compared(self):
        # A half-joined pair produces only the join failure, so a report never
        # mixes "disagrees" with "no row" and sends the reader after the wrong
        # one.
        sites = {ref: dict(row) for ref, row in SITES.items()}
        sites['0x0D0EF'] = self.OTHER
        problems, agreed, unchecked, blind, cut, _, seen = checked(
            sites=sites, rows=row(census_bucket='write'))
        self.assertEqual((agreed, unchecked, blind, cut, seen), (0, 0, 0, 0, 0))
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
        # The commas in `bank0/D091.c:45,49` are the CSV's own quoting: read
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

    def test_a_site_with_two_rows_renders_both_cells(self):
        # The 0x086B clamp shape reaching the column: one site, a read the
        # sweep decoded and a write behind the branch it stopped at. Rendering
        # only the first would put a direction in front of the reader that the
        # mapping does not support.
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'map.csv'
            path.write_text('region,file_offset,census_state,census_bucket,'
                            'census_count,census_refs\n'
                            'bank0,0x09E41,mapped,read,2,bank0/9D9B.c:80\n'
                            'bank0,0x09E41,mapped,write,1,bank0/9D9B.c:81\n')
            cells = tref.load_census_map(str(path))
        self.assertEqual(cells['0x09E41'], 'read x2 + write x1')

    def test_census_blind_renders_its_own_token(self):
        # It has to be a different cell from `no census occurrence`: the first
        # is what both methods agree is not there, the second is where the
        # sweep decoded an access and the decompile names nothing. Asserted on
        # the cell being distinct rather than on its wording, which is prose.
        self.assertNotEqual(tref.CENSUS_TOKENS['census-blind'],
                            tref.CENSUS_TOKENS['no-occurrence'])


class TheCensusColumnIsHeldToTheMapping(unittest.TestCase):
    """`check_cells()`: the sweep's own `census` column, against the row it
    restates. Without it the column is a hand-typed copy nothing derives."""

    SITES = {'0x0D091': {'census': 'read x2'}}

    def test_a_cell_that_matches_passes(self):
        self.assertEqual(csc.check_cells(self.SITES, {'0x0D091': 'read x2'}), [])

    def test_a_cell_that_drifted_is_rejected(self):
        problems = csc.check_cells(self.SITES, {'0x0D091': 'read x6'})
        self.assertEqual(len(problems), 1)
        self.assertIn('0x0D091', problems[0])

    def test_a_cell_reading_not_recorded_over_a_real_row_is_rejected(self):
        # The failure this clause exists for. `not recorded` reads as
        # "agreement pending" to anyone who does not know what it means, and a
        # mapping row behind it says the join was recorded.
        self.assertTrue(csc.check_cells(self.SITES,
                                        {'0x0D091': 'other program'}))

    def test_a_site_the_mapping_says_nothing_about_is_rejected(self):
        problems = csc.check_cells(self.SITES, {})
        self.assertEqual(len(problems), 1)
        self.assertIn('nothing', problems[0])


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

    def test_every_address_of_the_page_joins(self):
        # `--all` is what makes "no `not recorded` cell is left that a reader
        # could mistake for agreement" a check rather than a promise, so the
        # run that covers the page is itself under test -- including that it
        # prints one line per address and a page total over them.
        out = self.run_main(csc, ['check_site_census.py', '--all'])
        addresses = csc.page_addresses()
        self.assertEqual(len(addresses), len(PAGE_ADDRESSES))
        for addr in addresses:
            self.assertIn(f"{addr}: ", out)
        self.assertIn('page: ', out)

    def test_one_address_can_be_checked_on_its_own(self):
        # The switch that made the fourteen files reachable at all. A file that
        # nothing can name is a file nothing checks.
        out = self.run_main(csc, ['check_site_census.py', '--address', '0x1F01'])
        self.assertIn('0x1F01: ', out)
        self.assertNotIn('0x0860: ', out)

    def test_the_committed_sites_table_reproduces_from_the_sweep(self):
        out = self.run_main(tref, ['trace_xdata_refs.py', FIRMWARE,
                                   *PAGE_ADDRESSES, '--csv', '--census-column',
                                   '--check'])
        self.assertIn('reproduces it byte for byte', out)


if __name__ == '__main__':
    unittest.main()
