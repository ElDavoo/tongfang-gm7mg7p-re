#!/usr/bin/env python3
"""Offline checks for check_citation_lines.py: committed files only.

The tool's failure mode is silence, and silence here is a specific one: a
citation that names the wrong line of a generated CSV produces no error at all
in the prose, no wrong count, and nothing for a reader to notice. The page
reads exactly as well with `:662` as with `:817`. So what is pinned here is one
case per way a citation can be wrong -- each asserting the checker *rejects* it,
with the needle being the assertion, since a case that passed on any problem at
all would go green on a checker that had stopped comparing the thing it is
about -- plus the cases a loosened test would let through: a rule that located
nothing and reported nothing, a correction paragraph checked because it looks
like prose, and a skip that is not announced anywhere.

The last class is the one that matters most and is the reason the committed-tree
case runs `main()` with argv rather than calling a rule: the run has to print
how many citations it checked *and* how many it skipped, or "checked nothing"
reads from the exit code exactly like "found nothing".

The fixtures are small enough to write inline, which keeps each case readable as
the error it is about rather than as a diff against a stored file. They are not
the real `0x0860` sites, but they are the real *shapes* -- the `:49`
shorthand, the merged `0x25CE4`/`0x25CFC` row, the two correction paragraphs
above `HAND_CHECKED["0x0860"]` -- and the last class is the real thing, which is
what says the committed prose and the committed census currently agree.
"""
import contextlib
import csv
import importlib.util
import io
import os
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).parent
# check_citation_lines imports check_cluster_citations by bare module name, the
# way check_capture_claims imports the same one, so the tool directory has to be
# on the path before either is loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_citation_lines', HERE / 'check_citation_lines.py')
ccl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccl)


# The base fixture: a site table and the correspondence it is read against, in
# the shapes the committed ones have. `read x2` against `read x1` is not a
# disagreement -- the sweep records one row per `MOV DPTR` and the second
# comparison re-reads A without reloading DPTR -- so the base is already the
# many-to-one shape the real `0x0D091` row has, and the two `—` rows are the
# two places a site carries no citation at all rather than a zero.
TABLE = '\n'.join([
    '| site | sweep `access` | `census` | C occurrence(s) | why |',
    '|---|---|---|---|---|',
    '| `0x0D091` | `read x1` | `read x2` | `D091.c:45`, `:49` | two early-outs |',
    '| `0x0D0EF` | `read x1` | `read x6` | `D091.c:71,72` | the `0x48` chain |',
    '| `0x0D117` | `read x1` | `read x6` | `D091.c:75,76,77` | the `0x4C` chain |',
    '| `0x0D144` | `read x1` | `passed-to-call x1` | `D091.c:84` | one instruction, two vocabularies |',
    '| `0x0D281` | `write x1` | `write x1` | `D281.c:19` | `XDATA_0860 = 0xff` |',
    '| `0x0D28A` | `write x1` | `write x1` | `D289.c:18` | `XDATA_0860 = 0` |',
    '| `0x0D31C` | `no movx found in the decoded window` | `no census occurrence` | — | reloads DPTR and returns |',
    '| `0x25CE4`, `0x25CFC` | `read x1` | `other program` | — | the PD image |',
    '',
    'A paragraph after the table, so the body ends rather than running on to',
    'the end of the file the way a scan that ignored the blank line would.',
])
SITES = [
    {'file_offset': '0x0D091', 'census_state': 'mapped',
     'census_refs': 'bank0/D091.c:45,49'},
    {'file_offset': '0x0D0EF', 'census_state': 'mapped',
     'census_refs': 'bank0/D091.c:71,72'},
    {'file_offset': '0x0D117', 'census_state': 'mapped',
     'census_refs': 'bank0/D091.c:75,76,77'},
    {'file_offset': '0x0D144', 'census_state': 'mapped',
     'census_refs': 'bank0/D091.c:84'},
    {'file_offset': '0x0D281', 'census_state': 'mapped',
     'census_refs': 'bank0/D281.c:19'},
    {'file_offset': '0x0D28A', 'census_state': 'mapped',
     'census_refs': 'bank0/D289.c:18'},
    {'file_offset': '0x0D31C', 'census_state': 'no-occurrence',
     'census_refs': 'none'},
    {'file_offset': '0x25CE4', 'census_state': 'other-program',
     'census_refs': 'none'},
    {'file_offset': '0x25CFC', 'census_state': 'other-program',
     'census_refs': 'none'},
]

# The `HAND_CHECKED` comment, in the committed shape: one live paragraph, a
# `#`-only separator, then the two dated corrections that quote the wrong line
# numbers verbatim. `bank0/D091.c's` names the file without claiming a line, and
# the `(lines 45, 49, 71, 72, 75, 76 and 77)` list that follows is bound to it
# -- the two ways this comment cites the same file, and the reason
# `parse_citations` is a single left-to-right alternation.
MAP = '\n'.join([
    'HAND_CHECKED = {',
    '    # 17 references: 14 `==` inside bank0/D091.c\'s dispatch test (lines 45, 49,',
    '    # 71, 72, 75, 76 and 77 -- the later ones are multi-line boolean chains),',
    '    # the dispatch argument itself at bank0/D091.c:84, a `= 0xff` at',
    '    # bank0/D281.c:19 and a `= 0` at bank0/D289.c:18. Two stores in two',
    '    # functions.',
    '    #',
    '    # CORRECTION (2026-09-24, issue #281): the line numbers above were 30, 34,',
    '    # 56, 57, 60, 61 and 62, with the dispatch argument at :69.',
    '    #',
    '    # CORRECTION (2026-09-25, issue #752): the line numbers above were 43, 47, 69,',
    '    # 70, 73, 74 and 75, with the dispatch argument at :81, `= 0xff` at',
    '    # bank0/D281.c:18 and `= 0` at bank0/D289.c:17.',
    '    "0x0860": {"read": 14, "write": 2, "read+write": 0, "passed-to-call": 1,',
    '               "address-taken": 0, "writers": 2},',
    '    # A second entry, whose comment is not this one and must not be read as it.',
    '    # It cites bank0/F11C.c:99, which the CSV does not hold for 0x0860.',
    '    "0x0440": {"read": 181, "write": 0},',
    '}',
])

# A generated CSV small enough to read, with one row per declared subject so a
# nudge of one line is a real move and not a coincidence. `0x0860` at line 2 and
# `0x0800` at line 3 are the two Rule 3 resolves in these cases.
REGISTERS = '\n'.join([
    'addr,program,spelled_as',
    '0x0860,main-ec,symbol',
    '0x0800,main-ec,DAT_EXTMEM',
    '0x06E6,main-ec,DAT_EXTMEM',
])
CLUSTERS = '\n'.join([
    'cluster_id,program,n',
    'main-ec-086,main-ec,3',
    'main-ec-104,main-ec,3',
    'main-ec-100,main-ec,3',
])
PAGE = 'page.md'
SCOPE = ((PAGE, 'xdata-registers.csv', '0x0860', 'addr'),)
CSV_TEXT = {'xdata-registers.csv': REGISTERS, 'xdata-clusters.csv': CLUSTERS}


def pointers(text, scope=SCOPE):
    """Rule 3's (problems, checked, skipped) over an inline page."""
    return ccl.check_row_pointers(PAGE, text, list(scope), CSV_TEXT, False)


def site_problems(text=TABLE, rows=None):
    """Rule 1's (problems, checked, skipped) over an inline table."""
    return ccl.check_site_table(PAGE, text, SITES if rows is None else rows,
                                False)


def hand_problems(text=MAP, rows=None):
    """Rule 2's (problems, checked, skipped) over an inline module."""
    return ccl.check_hand_checked('xdata_register_map.py', text,
                                 SITES if rows is None else rows, False)


def saying(check, *needles, **kwargs) -> list:
    """Problems containing every needle. The needle is the assertion: a case
    that passes because *some* problem was reported would go green on a checker
    that had stopped comparing the thing the case is about."""
    return [p for p in check(**kwargs)[0] if all(n in p for n in needles)]


def in_table(before, after) -> str:
    """TABLE with one cell of the occurrence column replaced.

    String surgery rather than a template with a slot, because what each case is
    about is a *cell* -- `D091.c:45` becoming `D091.c:44` is the nudge, and the
    case has to read as that edit rather than as a diff against a stored file.
    """
    self_ = TABLE.replace(before, after, 1)
    assert self_ != TABLE, f"the fixture does not contain {before!r}"
    return self_


class Rule1SiteTable(unittest.TestCase):
    """The site table against the correspondence CSV, per site."""

    def test_the_base_fixture_agrees(self):
        self.assertEqual(site_problems(), ([], 9, 0))

    def test_a_site_line_nudged_by_one_is_rejected(self):
        # The D091.c case exactly: a `D091.c` header rewrite moved the line and
        # the table kept the old number. Every other row is still right, so this
        # is the only thing in the tree that could notice.
        self.assertTrue(saying(site_problems, 'site 0x0D091 cites',
                               'D091.c:44, D091.c:49',
                               text=in_table('`D091.c:45`, `:49`',
                                             '`D091.c:44`, `:49`')))

    def test_a_citation_that_resolves_onto_the_wrong_site_is_rejected(self):
        # Both lines are real and the census knows them; they belong to
        # `0x0D091`, and a table that hangs them off `0x0D0EF` is asserting a
        # correspondence no CSV row records. The same clause as the nudge above
        # catches this one, and that is worth pinning: the set comparison is the
        # check, and a "does every cited line exist" test would pass here.
        self.assertTrue(saying(site_problems, 'site 0x0D0EF cites',
                               text=in_table('`D091.c:71,72`', '`D091.c:45,49`')))

    def test_the_shorthand_binds_to_the_file_it_follows(self):
        # `:49` is a continuation of `D091.c`, not a citation of a file named
        # nowhere. Read as a bare number it would be dropped, and the row would
        # pass with one of its two lines missing.
        self.assertEqual(ccl.parse_citations('`D091.c:45`, `:49`'),
                         {('D091.c', 45), ('D091.c', 49)})

    def test_the_shorthand_expanded_to_the_wrong_number_is_rejected(self):
        self.assertTrue(saying(site_problems, 'site 0x0D091 cites', 'D091.c:50',
                               text=in_table('`D091.c:45`, `:49`',
                                             '`D091.c:45`, `:50`')))

    def test_a_bare_list_binds_to_the_file_named_ahead_of_it(self):
        # `bank0/D091.c's` names the file and claims no line, which is the shape
        # the `HAND_CHECKED` comment writes its seven `==` lines in.
        self.assertEqual(
            ccl.parse_citations("inside bank0/D091.c's test (lines 45, 49, 71 and 72)"),
            {('D091.c', 45), ('D091.c', 49), ('D091.c', 71), ('D091.c', 72)})

    def test_a_shorthand_with_no_file_ahead_of_it_is_not_a_citation(self):
        # There is nothing for the number to be a line *of*, and guessing one is
        # the move this tool exists to refuse.
        self.assertEqual(ccl.parse_citations('`:49` on its own'), set())

    def test_the_merged_pd_row_is_two_sites_and_one_row(self):
        # `0x25CE4` and `0x25CFC` are one table row and two CSV rows, and the
        # bank/prefix spelling differs from the prose's. A locator that read one
        # offset per row would drop `0x25CFC`, and the join would then report it
        # as a site the table never mentions.
        column, body = ccl.site_table(TABLE)
        self.assertEqual(column, 3)
        self.assertEqual([r[1][0] for r in body][-1], '0x25CE4, 0x25CFC')

    def test_a_site_in_the_table_with_no_csv_row_is_rejected(self):
        self.assertTrue(saying(site_problems, 'is in the table but',
                               'has no row for it',
                               text=TABLE.replace('`0x0D144`', '`0x0D999`', 1)))

    def test_a_csv_row_with_no_table_row_is_rejected(self):
        rows = SITES + [{'file_offset': '0x0D200', 'census_state': 'mapped',
                         'census_refs': 'bank0/D091.c:90'}]
        self.assertTrue(saying(site_problems, 'with no row in the table', rows=rows))

    def test_the_join_fails_before_anything_is_compared(self):
        # A half-joined pair produces only the join failure -- in both
        # directions, since renaming one site orphans two rows -- so a report
        # never mixes "disagrees" with "no row" and sends the reader after the
        # wrong one. The `D281.c` nudge below is in the fixture to be *not*
        # reported: a content disagreement while the two files describe
        # different site sets means nothing.
        text = in_table('`0x0D144`', '`0x0D999`').replace(
            '`D281.c:19`', '`D281.c:18`', 1)
        problems, checked, _ = site_problems(text=text)
        self.assertEqual(checked, 0)
        self.assertTrue(any('is in the table but' in p for p in problems))
        self.assertTrue(any('with no row in the table' in p for p in problems))
        self.assertFalse(any('D281.c' in p for p in problems))

    def test_a_dash_cell_over_a_row_that_cites_something_is_rejected(self):
        # `—` means the census has no occurrence here. Over a CSV row that does
        # carry citations it is a row that dropped them, and a blank reads as
        # agreement -- the failure this whole class of tool exists to remove.
        rows = [dict(r) for r in SITES]
        for row in rows:
            if row['file_offset'] == '0x0D31C':
                row['census_refs'] = 'bank0/D091.c:45'
        self.assertTrue(saying(site_problems, 'site 0x0D31C cites nothing',
                               'D091.c:45', rows=rows))

    def test_a_cell_naming_no_line_at_all_is_rejected(self):
        # Neither agreeing nor disagreeing: there is nothing to compare, and a
        # rule that read it as an empty set would report the site as a match.
        text = in_table('`D281.c:19`', 'two early-outs')
        self.assertTrue(saying(site_problems, 'holds no `.c:line` to check',
                               text=text))

    def test_a_table_whose_header_lost_the_column_is_reported_not_located(self):
        # The vacuous-pass shape. A renamed column must not read as a table with
        # nothing in it to disagree about, which is the one result this rule
        # must never produce by accident.
        text = TABLE.replace('C occurrence(s)', 'occurrences')
        problems, checked, _ = site_problems(text=text)
        self.assertEqual(checked, 0)
        self.assertTrue(any('was not located' in p for p in problems))

    def test_the_body_ends_with_the_table(self):
        # This file carries six tables and the rows of the next one are not
        # sites. A scan that ran on to the end of the file would report every
        # unrelated `0x0NNN` in it as a site with no CSV row.
        text = TABLE + '\n' + '\n'.join([
            '| site | loads DPTR | the store that follows |',
            '|---|---|---|',
            '| bank0 `0xD281` | `0x0860` | `0xFF` at `0xD286` |',
        ])
        self.assertEqual(site_problems(text=text), ([], 9, 0))


class Rule2HandChecked(unittest.TestCase):
    """The `HAND_CHECKED` comment against the same CSV, as an unordered union."""

    def test_the_base_fixture_agrees(self):
        problems, checked, skipped = hand_problems()
        self.assertEqual(problems, [])
        # 10 is the union over the six mapped sites: eight `D091.c` lines (the
        # seven `==` tests and the dispatch argument) and the two stores.
        self.assertEqual(checked, 10)
        # Both dated corrections above the entry are passed over, and the count
        # says so rather than the run being quiet about it. It is 2 and not
        # 17 because the tally is of citations the parser recognised, and the
        # #281 correction names seven bare line numbers with no file ahead of
        # them -- a number with no file to be a line *of* is not something this
        # tool can count, and inventing a file for it is the move it refuses.
        # The #752 correction names two `.c` lines and both are counted.
        self.assertEqual(skipped, 2)

    def test_a_citation_that_does_not_resolve_is_rejected(self):
        text = MAP.replace('bank0/D281.c:19', 'bank0/D281.c:18')
        self.assertTrue(saying(hand_problems, 'HAND_CHECKED', text=text))

    def test_a_citation_that_is_dropped_entirely_is_rejected(self):
        text = MAP.replace("""the dispatch argument itself at bank0/D091.c:84, a `= 0xff` at
    # bank0/D281.c:19 and a `= 0` at bank0/D289.c:18. Two stores in two
    # functions.""", 'Two stores in two functions.')
        self.assertTrue(saying(hand_problems, 'comment cites', text=text))

    def test_a_regrouping_across_sites_does_not_red_this_rule(self):
        # The deliberate asymmetry, and the reason both rules exist: Rule 2 is
        # insensitive to how the lines group into sites, so a CSV that moved
        # `D091.c:84` onto another site leaves this one alone.
        # Two existing sites trade their citations, so the CSV still holds the
        # same ten lines and only says something different about which site
        # each belongs to.
        rows = [dict(r) for r in SITES]
        for row in rows:
            if row['file_offset'] == '0x0D117':
                row['census_refs'] = 'bank0/D091.c:84'
            elif row['file_offset'] == '0x0D144':
                row['census_refs'] = 'bank0/D091.c:75,76,77'
        self.assertEqual(hand_problems(rows=rows)[0], [])
        # ...and Rule 1 is what catches it, on both rows.
        problems = saying(site_problems, 'site 0x0D117 cites', rows=rows)
        self.assertTrue(problems)
        self.assertTrue(saying(site_problems, 'site 0x0D144 cites', rows=rows))

    def test_only_this_entrys_comment_is_read(self):
        # The entry below carries a citation the CSV does not hold for
        # `0x0860`, and a walk that ran past this entry's closing line would
        # take it as part of the same comment.
        self.assertNotIn('F11C.c', ' '.join(ccl.hand_checked_comment(MAP)))

    def test_a_module_with_no_such_entry_is_reported_as_checked_nothing(self):
        # A rule that located nothing has to say so. Returning no problems for a
        # comment that is not there would be the silent pass this tool is about.
        problems, checked, _ = hand_problems(text='HAND_CHECKED = {\n}\n')
        self.assertEqual(checked, 0)
        self.assertTrue(any('checked nothing' in p for p in problems))


class Rule3RowPointers(unittest.TestCase):
    """Every `<generated CSV>:NNN` against the row for its declared address."""

    def test_a_pointer_at_the_declared_row_passes(self):
        text = 'The `refs: 17` is `xdata-registers.csv:2` today.\n'
        self.assertEqual(pointers(text), ([], 1, 0))

    def test_a_pointer_one_line_above_the_row_is_rejected(self):
        text = 'The `refs: 17` is `xdata-registers.csv:1` today.\n'
        self.assertTrue(saying(pointers, 'which is the header row', text=text))

    def test_a_pointer_one_line_below_the_row_is_rejected(self):
        # The nudge in the direction the corpus actually moves: a row inserted
        # above `0x0860` pushes it down and leaves every figure on the page
        # still correct.
        text = 'The `refs: 17` is `xdata-registers.csv:3` today.\n'
        problems = saying(pointers, 'which is the 0x0800 row',
                          'not the 0x0860 row at 2', text=text)
        self.assertTrue(problems)

    def test_a_pointer_past_the_end_of_the_file_is_rejected(self):
        text = 'See `xdata-registers.csv:9999`.\n'
        self.assertTrue(saying(pointers, 'past the end of the file', text=text))

    def test_a_full_path_pointer_is_the_same_citation(self):
        # The corpus writes both spellings and they are one citation, so the
        # scope list keys on the basename rather than on the whole path.
        text = 'The row is `ec/annotations/xdata-registers.csv:2`.\n'
        self.assertEqual(pointers(text), ([], 1, 0))

    def test_either_declared_row_satisfies_a_file_that_cites_two(self):
        scope = (SCOPE[0], (PAGE, 'xdata-registers.csv', '0x0800', 'addr'))
        for line in (2, 3):
            text = f'See `xdata-registers.csv:{line}`.\n'
            self.assertEqual(pointers(text, scope=scope), ([], 1, 0))

    def test_a_pointer_neither_declared_row_holds_names_both(self):
        scope = (SCOPE[0], (PAGE, 'xdata-registers.csv', '0x0800', 'addr'))
        text = 'See `xdata-registers.csv:4`.\n'
        self.assertTrue(saying(pointers, 'the 0x0860 row at 2',
                               'the 0x0800 row at 3', text=text, scope=scope))

    def test_a_declared_subject_with_no_row_is_reported(self):
        # A scope list that has itself gone stale. Raising nothing here would
        # leave the rule comparing against an empty expectation, which every
        # citation then fails against for the wrong reason.
        scope = (SCOPE[0], (PAGE, 'xdata-registers.csv', '0x0999', 'addr'))
        self.assertTrue(saying(pointers, 'the scope list names',
                               "'0x0999' has no addr row", text='See it.\n',
                               scope=scope))

    def test_a_pointer_to_a_csv_with_no_declared_subject_is_reported(self):
        text = 'It is in `xdata-clusters.csv:2`.\n'
        self.assertTrue(saying(pointers, 'declares no subject', text=text))

    def test_a_blockquoted_supersession_is_skipped(self):
        # The dispatch page's corrections are blockquotes, and they quote the
        # old figures on purpose. Checked, the tool would be red on its own
        # corrected tree, which is the surest way to get a check switched off.
        text = ('> **CORRECTION (2026-09-25, issue #801)** to the\n'
                '> `xdata-registers.csv:662` cell, which named a line that moved.\n')
        self.assertEqual(pointers(text), ([], 0, 1))

    def test_a_correction_paragraph_is_skipped(self):
        # The same sentence in the Python comment's language: no `>`, and the
        # marker is a `#` that a sentence splitter has already thrown away.
        text = ('# CORRECTION (2026-09-24, issue #281): the row is at\n'
                '# xdata-registers.csv:662, not :659.\n')
        self.assertEqual(pointers(text), ([], 0, 1))

    def test_a_live_paragraph_naming_the_word_correction_is_still_checked(self):
        # Only a paragraph that *opens* with the announcement is superseded. A
        # sentence that mentions a correction in passing is still a claim, and
        # reading it as quoted would be a skip with no shape behind it.
        text = ('The correction above left the row at\n'
                '`xdata-registers.csv:4`, which is the 0x06E6 row.\n')
        self.assertTrue(saying(pointers, 'which is the 0x06E6 row', text=text))

    def test_verbose_names_what_was_passed_over_and_why(self):
        err = io.StringIO()
        text = '> quoted `xdata-registers.csv:662`.\n'
        with contextlib.redirect_stderr(err):
            ccl.check_row_pointers(PAGE, text, list(SCOPE), CSV_TEXT, True)
        self.assertIn('skip (quoted material)', err.getvalue())
        self.assertIn('xdata-registers.csv:662', err.getvalue())

    def test_a_wrapped_sentence_is_reported_on_the_line_the_citation_is_on(self):
        # Not the line the sentence starts on. A report that points a reader at
        # the wrong line is worse than one that points at none.
        text = ('The census counts C-level occurrences of the address in the\n'
                'decompiled text, which is the `refs: 17` of\n'
                '`xdata-registers.csv:662`. The 14/2/0/1 below is the bucketing.\n')
        self.assertTrue(saying(pointers, 'page.md:3: cites', text=text))


class TheCommittedTree(unittest.TestCase):
    """The real thing: the committed prose and the committed census agree.

    This is the assertion that would have caught four of the cells this branch
    corrects, and it is the one that goes red on the next `D091.c` header
    rewrite -- which is the whole point of having the check rather than the five
    edits.
    """

    def run_main(self, argv) -> tuple:
        """(exit code, stdout, stderr) with `argv` in place and both streams
        captured, the way a reader would run it -- the return code and the lines
        it prints are the tool's whole output surface."""
        err, out, saved = io.StringIO(), io.StringIO(), sys.argv
        sys.argv = argv
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = ccl.main()
        finally:
            sys.argv = saved
        return rc, out.getvalue(), err.getvalue()

    def test_the_committed_citations_hold(self):
        rc, out, err = self.run_main(['check_citation_lines.py'])
        self.assertEqual(rc, 0, err)
        self.assertIn('resolve to the row they name', out)

    def test_the_run_says_how_many_it_checked_and_how_many_it_skipped(self):
        # Without this a rule that stopped looking and a tree with nothing to
        # look at print the same thing, and "checked nothing" would read from
        # the exit code exactly like "found nothing".
        _, out, _ = self.run_main(['check_citation_lines.py'])
        match = re.search(r'(\d+) citation\(s\) resolve.*?, (\d+) skipped',
                          out)
        self.assertIsNotNone(match, out)
        self.assertGreater(int(match.group(1)), 0)
        # Non-zero on the real tree too: `xdata_register_map.py` carries two
        # dated corrections above the entry and the dispatch page three
        # blockquotes, so the skip is exercised by the committed files and not
        # only by a fixture. A rule that reported zero skips on a tree full of
        # them would be skipping for a reason nobody wrote down.
        self.assertGreater(int(match.group(2)), 0)

    def test_the_scope_list_names_subjects_that_exist(self):
        # The scope list is a set of constants in the tool, and nothing else
        # holds them. A subject that has been renamed or renumbered would leave
        # every citation in its file failing against an expectation of nothing.
        for _, name, declared, column in ccl.ROW_SCOPE:
            with self.subTest(declared=declared):
                self.assertIsInstance(ccl.csv_line_of(
                    ccl.read(os.path.join(ccl.ANNOTATIONS, name)),
                    column, declared), int)

    def test_the_committed_registers_csv_is_the_one_the_tool_reads(self):
        # The figures in the page's own sentences, re-read rather than trusted:
        # the checker holding a pointer is worthless if the row it resolves
        # against is not the row the census generated.
        with open(ccl.REGISTERS_CSV, newline="") as f:
            row = next(r for r in csv.DictReader(f) if r['addr'] == '0x0860')
        self.assertEqual((row['refs'], row['read'], row['write'],
                          row['read+write'], row['passed-to-call']),
                         ('17', '14', '2', '0', '1'))

    def test_the_committed_site_correspondence_is_the_one_the_tool_reads(self):
        # The two `.c` line numbers the tool holds the prose to, read out of the
        # committed CSV rather than written here, for the reason
        # `test_check_site_census.py` gives its own version of this case: these
        # are pins into a decompile, and a hardcoded copy would go stale
        # silently the next time an annotation landed. What is under test is
        # that the tool and this suite read the same file, not the addresses.
        with open(ccl.SITES_CSV, newline="") as f:
            rows = {r['file_offset']: r['census_refs']
                    for r in csv.DictReader(f)}
        self.assertEqual(rows['0x0D281'], 'bank0/D281.c:19')
        self.assertEqual(rows['0x0D28A'], 'bank0/D289.c:18')


if __name__ == '__main__':
    unittest.main()
