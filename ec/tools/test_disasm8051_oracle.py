#!/usr/bin/env python3
"""The two transcriptions `--self-test` is checked against, re-read from the
committed markdown rather than trusted from a literal table.

`disasm8051.py` holds `SELF_TEST` and `REL_SITES` as tuples typed into it and
cites two annotation files in a comment as where those rows were transcribed
from. That is provenance, not a check, and for as long as it was only that,
correcting either `.md` left the literals holding the old text, `--self-test`
stayed green, and the failure line named a file the run had never opened.
`disasm8051_oracle.py` is the read-back; these cases hold it to what it claims.

**The mutations are the reason this file exists.** A parser that finds nothing
reconciles perfectly -- an empty parse equals an empty window span, and a
missing address is not a disagreement if nothing is looking for it -- so the
cases that matter are the ones that change a committed `.md` and require a
named failure. Each of the three ways a listing can be wrong gets its own:
an operand re-transcribed, a row added, a row removed. Everything else here is
the parse agreeing with the committed files, which is what keeps a green run
from meaning only that the parser is still broken.

Nothing here reads firmware except the two cases that run the mode whole, and
those read the committed image the way the gate does. No capture, no EC, no
register read back, nothing deferred to a human at the machine.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'disasm8051', HERE / 'disasm8051.py')
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)
import disasm8051_oracle as O                       # noqa: E402

CHARGE_PROFILE = (HERE.parent / 'annotations'
                  / O.CHARGE_PROFILE_FLOW).read_text()
BANK_CALL_AUDIT = (HERE.parent / 'annotations' / O.BANK_CALL_AUDIT).read_text()
FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')

# The eleven and seven texts SELF_TEST carries, written out here rather than
# read off it. Reading the table into the expected value is a tautology: the
# table is one of the two things under test, and a case that asserts it agrees
# with itself holds nothing. These two lists are the transcription, in the
# decoder's own spelling.
WINDOW_0B12C = [
    (0xB12C, 'mov  dptr,#0x078e'),
    (0xB12F, 'movx a,@dptr'),
    (0xB130, 'orl  a,#0x08'),
    (0xB132, 'movx @dptr,a'),
    (0xB133, 'mov  dptr,#0x0741'),
    (0xB136, 'movx a,@dptr'),
    (0xB137, 'jb   acc.0,0xb141'),
    (0xB13A, 'mov  dptr,#0x07a6'),
    (0xB13D, 'movx a,@dptr'),
    (0xB13E, 'anl  a,#0xcf'),
    (0xB140, 'movx @dptr,a'),
]
WINDOW_0B2E2 = [
    (0xB2E2, 'mov  dptr,#0x07a6'),
    (0xB2E5, 'movx a,@dptr'),
    (0xB2E6, 'anl  a,#0x30'),
    (0xB2E8, 'mov  r7,a'),
    (0xB2E9, 'cjne r7,#0x20,0xb2f0'),
    (0xB2EC, 'mov  r3,#0xc8'),
    (0xB2EE, 'sjmp 0xb35e'),
]
# The 0xB330 block, which the table has never carried. Named rather than
# skipped: the mode prints it, so a case has to say what it is printing.
BLOCK_0XB330 = [
    (0xB330, 'mov  dptr,#0x07a6'),
    (0xB333, 'movx a,@dptr'),
    (0xB334, 'anl  a,#0x30'),
    (0xB336, 'mov  r7,a'),
    (0xB337, 'cjne r7,#0x10,0xb33e'),
    (0xB33A, 'mov  r3,#0x64'),
]


@contextlib.contextmanager
def scratch(charge_profile=CHARGE_PROFILE, bank_call_audit=BANK_CALL_AUDIT):
    """A directory holding the two annotations, mutated, for one run."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / O.CHARGE_PROFILE_FLOW).write_text(charge_profile)
        (d / O.BANK_CALL_AUDIT).write_text(bank_call_audit)
        yield str(d)


def run_mode(charge_profile=CHARGE_PROFILE, bank_call_audit=BANK_CALL_AUDIT):
    """`self_test()` whole, over a scratch copy of the annotations.

    Returns `(exit code, printed lines)`. The mode's own printing is the thing
    under test in several of the cases below, so it is captured rather than
    discarded -- but a case that fails on the run's noise teaches nothing, so
    `quiet=True` is for the cases that only want the verdict.
    """
    with scratch(charge_profile, bank_call_audit) as ann:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = D.self_test(FIRMWARE, ann)
        return rc, buf.getvalue().splitlines()


class ChargeProfileParse(unittest.TestCase):
    """`charge-profile-flow.md`, in the decoder's own listing dialect."""

    def test_the_two_windows_parse_to_their_transcribed_texts(self):
        rows = O.parse_windows(CHARGE_PROFILE)
        for lo, hi, expected in ((0xB12C, 0xB140, WINDOW_0B12C),
                                 (0xB2E2, 0xB2EE, WINDOW_0B2E2)):
            self.assertEqual([r for r in rows if lo <= r[0] <= hi], expected)

    def test_the_elisions_are_dropped_rather_than_matched(self):
        # 0xb141 closes the first window and 0xb2f0 sits one past the second,
        # and the bare `...` between the two blocks has no address at all.
        # Dropping them is what lets a window's span be compared without either
        # span having to cover an elision; matching them would fail on a file
        # that is right.
        rows = O.parse_windows(CHARGE_PROFILE)
        self.assertNotIn(0xB141, [a for a, _t in rows])
        self.assertNotIn(0xB2F0, [a for a, _t in rows])
        self.assertEqual(len(rows), 24)

    def test_a_trailing_comment_is_not_part_of_the_instruction(self):
        # Every line of both windows except the last carries one, and SELF_TEST
        # holds the text without it -- so a parser that kept the `;` tail would
        # disagree with the table on every row at once.
        rows = dict(O.parse_windows(CHARGE_PROFILE))
        self.assertEqual(rows[0xB137], 'jb   acc.0,0xb141')
        self.assertIn('; if ENABLE_MANUAL_CTRL set, skip reset', CHARGE_PROFILE)

    def test_the_third_block_parses_and_is_reported_as_untranscribed(self):
        # 24 rows is 18 transcribed plus these 6. The mode prints a line about
        # them, and a case that did not say what it prints would let that line
        # drift into a claim the mode does not support.
        rows = O.parse_windows(CHARGE_PROFILE)
        self.assertEqual([r for r in rows
                          if 0xB330 <= r[0] <= 0xB33A], BLOCK_0XB330)
        lo, hi, n = O.untranscribed(rows, D.SELF_TEST)
        self.assertEqual((lo, hi, n), (0xB330, 0xB33A, 6))


class SectionEightParse(unittest.TestCase):
    """`bank-call-audit.md` §8, r2's `pd` output quoted verbatim."""

    def test_the_four_branch_sites_parse_to_their_bytes_and_texts(self):
        listings = O.parse_section(BANK_CALL_AUDIT)
        for addr, raw, text in ((0xB2EE, b'\x80\x6e', 'sjmp 0xb35e'),
                                (0xB137, b'\x20\xe0\x07', 'jb acc.0, 0xb141'),
                                (0xF1B0, b'\xdf\xe6', 'djnz r7, 0xf198'),
                                (0xFE24, b'\x30\xe1\xe8', 'jnb acc.1, 0xfe0f')):
            self.assertEqual(listings.get(addr), [(raw, text)])

    def test_the_escape_block_listings_parse_too(self):
        # The point of this one is that the parse is address-scoped rather
        # than "the first four lines that look like listings". §8 quotes a
        # second `r2` session over the four byte-scan escapes, and a parse that
        # stopped at the first fence would hold the four branch sites and none
        # of these, which is a parser that would pass a section whose second
        # half had rotted.
        listings = O.parse_section(BANK_CALL_AUDIT)
        self.assertEqual(listings[0x8020], [(b'\x90\x19\x02', 'mov dptr, #0x1902')])
        self.assertEqual(listings[0x805B], [(b'\x02\x82\x74', 'ljmp 0x8274')])
        self.assertEqual(listings[0x805E], [(b'\x12\xb9\xdf', 'lcall 0xb9df')])

    def test_a_shell_prompt_is_not_mistaken_for_a_listing(self):
        # A `$ r2 ... 's 0xb136; pd 2'` line carries a seek offset of its own,
        # and bank-0 runtime addresses run to 0xFFFF, so a prompt's offset is
        # indistinguishable from a listing's by range -- parsing one would put
        # a *seek* into a table of *listings* and it would be the seek of the
        # very site the line above it lists. What separates them is the shape
        # of the line, so that is what the case reads: there are prompts here
        # to be misparsed, and none of them came through.
        prompts = [l for l in O._section_body(BANK_CALL_AUDIT).splitlines()
                   if l.startswith('$')]
        self.assertTrue(prompts, 'no prompt lines in §8, so this holds nothing')
        for _addr, entries in O.parse_section(BANK_CALL_AUDIT).items():
            for _raw, text in entries:
                self.assertNotIn('r2 -a 8051', text)
                self.assertNotIn('; pd ', text)


class CommittedTree(unittest.TestCase):
    """The reconciliation, against the two files as committed."""

    def test_both_windows_agree_with_no_problem_named(self):
        checked, problems = O.reconcile_windows(
            O.parse_windows(CHARGE_PROFILE), D.SELF_TEST)
        self.assertEqual(problems, [])
        self.assertEqual(checked, 18)

    def test_all_four_sites_agree_with_no_problem_named(self):
        checked, problems = O.reconcile_sites(
            O.parse_section(BANK_CALL_AUDIT), D.REL_SITES)
        self.assertEqual(problems, [])
        self.assertEqual(checked, 4)

    def test_the_table_and_the_files_still_hold_the_same_rows(self):
        # The other direction, and the one that catches a table edited to match
        # a file edited to match it. SELF_TEST and REL_SITES are transcribed by
        # hand from `r2`; the write-up above carries the same rows, and this
        # is what stops the two copies of the transcription from drifting into
        # two oracles.
        self.assertEqual([(s, expected) for s, expected in D.SELF_TEST],
                         [(0xB12C, WINDOW_0B12C), (0xB2E2, WINDOW_0B2E2)])

    def test_the_mode_exits_zero_on_the_committed_tree(self):
        rc, _lines = run_mode()
        self.assertEqual(rc, 0)


class Mutations(unittest.TestCase):
    """A changed `.md` is a named failure, which is the whole point of the
    read-back. Each case is one way a listing can stop matching its table."""

    def assert_fails(self, lines, needle):
        bad = [l for l in lines if l.startswith('  !')]
        self.assertTrue(bad, f'no failure reported; the run printed:\n'
                             + '\n'.join(lines))
        self.assertTrue(any(needle in l for l in bad),
                        f'no failure names {needle!r}; reported:\n'
                        + '\n'.join(bad))

    def test_an_operand_re_transcribed_is_named_by_address(self):
        rc, lines = run_mode(
            charge_profile=CHARGE_PROFILE.replace(
                '0xb130   orl  a,#0x08', '0xb130   orl  a,#0x09'))
        self.assertEqual(rc, 1)
        self.assert_fails(lines, '0xB130 is `orl  a,#0x09`')

    def test_a_row_added_inside_a_window_is_a_duplicate_not_a_shift(self):
        # A row inserted *and* the original left, so the address is listed
        # twice. A parser that paired the two lists up in order would report
        # this as a cascade of text disagreements one address to the right,
        # none of which is the address that changed.
        rc, lines = run_mode(
            charge_profile=CHARGE_PROFILE.replace(
                '0xb12f   movx a,@dptr', '0xb12f   movx a,@dptr\n0xb130   nop'))
        self.assertEqual(rc, 1)
        self.assert_fails(lines, 'lists 0xB130 twice inside 0xB12C..0xB140')

    def test_a_row_removed_from_a_window_is_named_as_absent(self):
        # The shape the positional comparison gets exactly wrong: every
        # surviving row still pairs with a row that agrees, so an ordered zip
        # reports nothing at all here.
        rc, lines = run_mode(
            charge_profile=CHARGE_PROFILE.replace(
                '0xb133   mov  dptr,#0x0741   ; AP_OEM\n', ''))
        self.assertEqual(rc, 1)
        self.assert_fails(lines, '0xB133 is `mov  dptr,#0x0741` in SELF_TEST '
                                 'and is not listed')

    def test_an_elision_written_over_a_real_row_is_a_removal(self):
        # The same absence wearing the other spelling, and worth its own case
        # because `...` is dropped by the parse -- so nothing downstream ever
        # sees the row to notice that it is gone.
        rc, lines = run_mode(
            charge_profile=CHARGE_PROFILE.replace(
                '0xb2ee   sjmp 0xb35e', '0xb2ee   ...'))
        self.assertEqual(rc, 1)
        self.assert_fails(lines, '0xB2EE')

    def test_a_section_8_listing_line_deleted_is_its_own_failure(self):
        # Not a skip. A skipped row would leave a REL_SITES entry that nothing
        # has ever checked reading exactly like one that was checked.
        rc, lines = run_mode(
            bank_call_audit=BANK_CALL_AUDIT.replace(
                '┌─< 0x0000b137      20e007', '┌─< 0x0000b1f7     20e007'))
        self.assertEqual(rc, 1)
        self.assert_fails(lines, 'REL_SITES 0xB137 is no longer listed')

    def test_a_section_8_byte_column_edited_is_caught_on_bytes(self):
        rc, lines = run_mode(
            bank_call_audit=BANK_CALL_AUDIT.replace(
                '0x0000f1b0      dfe6', '0x0000f1b0      dfe7'))
        self.assertEqual(rc, 1)
        self.assert_fails(lines, '0xF1B0 is `df e7`')

    def test_a_section_8_target_edited_is_caught_on_the_target(self):
        # The wrong target this one names is the one the file's own prose calls
        # the load-bearing case: reading 0xFE24's displacement from the second
        # byte would give 0xFE08.
        rc, lines = run_mode(
            bank_call_audit=BANK_CALL_AUDIT.replace(
                'jnb acc.1, 0xfe0f', 'jnb acc.1, 0xfe08'))
        self.assertEqual(rc, 1)
        self.assert_fails(lines, '0xFE24 is `30 e1 e8` -> 0xFE08')

    def test_the_two_dialects_are_never_reconciled_on_their_text(self):
        # The reason the branch sites compare on bytes and target. §8 writes
        # `jb acc.0, 0xb141` where charge-profile-flow.md writes
        # `jb   acc.0,0xb141`, so a text comparison would need a normaliser for
        # both spacings -- and that normaliser would be the fragile part of a
        # check whose whole job is to notice drift.
        listings = O.parse_section(BANK_CALL_AUDIT)
        self.assertEqual(listings[0xB137], [(b'\x20\xe0\x07', 'jb acc.0, 0xb141')])
        self.assertEqual(dict(O.parse_windows(CHARGE_PROFILE))[0xB137],
                         'jb   acc.0,0xb141')


class Vacuity(unittest.TestCase):
    """A parse that finds nothing has to fail. These are the three shapes it
    can find nothing in, and each is a different silent pass if left alone."""

    def test_a_window_covering_no_parsed_row_is_refused(self):
        # The whole span elided rather than one row of it: `0xb2e2` is the
        # window's first row, so removing it does not empty the span and would
        # be reported as an ordinary absence.
        emptied = '\n'.join(l for l in CHARGE_PROFILE.splitlines()
                            if not l.startswith('0xb2e'))
        _checked, problems = O.reconcile_windows(
            O.parse_windows(emptied), D.SELF_TEST)
        self.assertTrue(problems)
        self.assertIn('0xB2E2..0xB2EE covers', problems[0])

    def test_a_file_with_no_fence_is_refused_rather_than_read_as_empty(self):
        with self.assertRaises(ValueError):
            O.parse_windows('# Charge-profile control flow\n\nNo listing.\n')

    def test_a_missing_section_is_refused_rather_than_read_as_empty(self):
        # The same argument for §8, and the reason the heading is looked for
        # rather than the whole file being scanned: a `## Eight.` or a renumber
        # would otherwise leave the parser scanning a file that still parses and
        # finding the four sites in whichever section had them.
        with self.assertRaises(ValueError):
            O.parse_section(BANK_CALL_AUDIT.replace(
                '## 8. The PC-relative', '## Eight. The PC-relative'))

    def test_a_missing_file_is_a_reported_problem_rather_than_a_traceback(self):
        # A prepared gate that crashes on a renamed annotation file looks, on
        # the first run after the rename, like a broken tool.
        with tempfile.TemporaryDirectory() as tmp:
            n, problems, _loose = O.reconcile(tmp, D.SELF_TEST, D.REL_SITES)
        self.assertTrue(problems)
        self.assertIn('could not be read', problems[0])
        self.assertEqual(n, 0)

    def test_one_unreadable_file_does_not_take_the_other_verdict_down(self):
        # The partial answer, and the reason `reconcile()` is one call returning
        # one list: a run whose charge-profile-flow.md has gone still checked
        # the four branch sites, and saying so is more use than a total that
        # means nothing.
        with scratch() as ann:
            n, problems, _loose = O.reconcile(ann, D.SELF_TEST, D.REL_SITES)
            self.assertEqual(problems, [])
            self.assertEqual(n, 22)
            (Path(ann) / O.CHARGE_PROFILE_FLOW).unlink()
            n, problems, _loose = O.reconcile(ann, D.SELF_TEST, D.REL_SITES)
        self.assertEqual(n, 4)
        self.assertTrue(problems)


class Invocation(unittest.TestCase):
    """How the mode finds its two files, which is the other half of the claim.

    The prepared gate calls `python3 ec/tools/disasm8051.py --self-test` from
    the repository root, and `main()` derives the firmware path from `__file__`
    for the same reason the annotations have to be: a gate's cwd is not
    something the mode gets to choose.
    """

    def test_the_mode_runs_with_the_cwd_removed(self):
        here = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = D.self_test(FIRMWARE)
            finally:
                os.chdir(here)
        self.assertEqual(rc, 0)
        self.assertIn('and reconciled', buf.getvalue())

    def test_the_prepared_gates_invocation_exits_zero_from_the_repo_root(self):
        # The arm in docs/ci/agent-gates-disasm8051-self-test.patch, verbatim,
        # and the only invocation that a human running `git apply` on that patch
        # will get. A lazy import resolved off the cwd rather than off
        # `__file__` would pass every in-process case above and fail here.
        proc = subprocess.run(
            [sys.executable, 'ec/tools/disasm8051.py', '--self-test'],
            cwd=REPO, capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('self-test passed:', proc.stdout)

    def test_the_oracle_is_not_imported_at_module_scope(self):
        # Eleven tools under ec/tools/ import disasm8051 for its opcode tables
        # and none of them wants a markdown parser. The import is inside
        # self_test() for that reason, and a case reading the module's own
        # header is what keeps a later tidy-up from hoisting it back to the
        # top.
        with open(HERE / 'disasm8051.py') as f:
            source = f.read()
        top = source.split('def self_test(', 1)[0]
        self.assertNotIn('disasm8051_oracle', top)


class TranscriptContract(unittest.TestCase):
    """The lines this branch did not change, asserted as strings.

    Five committed transcripts quote `--self-test`'s tail verbatim --
    `disasm8051-self-test-gate.md`, `ec-07d6-07d7-sites.md`,
    `ec-09e9-09eb-sites.md` and the `tail -6` at `bank-call-audit.md` -- so the
    new block is printed at the head of the run and the summary line gains no
    clause. Without a case, that is a promise a later edit breaks and a reader
    discovers by noticing four transcripts have gone stale.

    The four `REL_SITES` lines and the summary are pinned literally. The
    fourteen `BIT_SITES`, `TEXTBOOK_BIT_SITES` and page-rule lines are counted
    and their ends pinned instead, because those are generated from tables this
    suite holds elsewhere: pinning them here would pin `BIT_SITES` twice and
    make a legitimate addition to it a failure of this file.
    """

    SUMMARY = ('self-test passed: both charge-profile-flow.md windows decode '
               'identically, all 4 relative-branch sites resolve as '
               'hand-decoded, and all 11 bit-form sites decode as transcribed')
    TAIL = [
        '  ok  file 0x0B2EE (runtime 0xB2EE) is `80 6e` targeting 0xB35E '
        '(got `80 6e` -> 0xB35E)',
        '  ok  file 0x0B137 (runtime 0xB137) is `20 e0 07` targeting 0xB141 '
        '(got `20 e0 07` -> 0xB141)',
        '  ok  file 0x0F1B0 (runtime 0xF1B0) is `df e6` targeting 0xF198 '
        '(got `df e6` -> 0xF198)',
        '  ok  file 0x0FE24 (runtime 0xFE24) is `30 e1 e8` targeting 0xFE0F '
        '(got `30 e1 e8` -> 0xFE0F)',
    ]

    def setUp(self):
        self.lines = run_mode()[1]

    def test_the_summary_line_is_byte_identical(self):
        self.assertEqual(self.lines[-1], self.SUMMARY)

    def test_the_four_branch_site_lines_are_byte_identical(self):
        found = [l for l in self.lines if l.startswith('  ok  file 0x0B2EE')
                 or l.startswith('  ok  file 0x0B137')
                 or l.startswith('  ok  file 0x0F1B0')
                 or l.startswith('  ok  file 0x0FE24')]
        self.assertEqual(found, self.TAIL)

    def test_the_new_block_is_printed_before_the_window_loop(self):
        # The property that keeps the tail from moving: everything the read-back
        # prints lands above the first `    0x` row, which is where the run
        # already had its first line before this branch.
        first_row = next(i for i, l in enumerate(self.lines)
                         if l.startswith('    0x'))
        self.assertTrue(all(l.startswith(('  !', '  --', '  ok')) or not l.strip()
                            for l in self.lines[:first_row]))
        self.assertEqual(self.lines[first_row],
                         '    0xb12c  mov  dptr,#0x078e        expected '
                         '0xb12c  mov  dptr,#0x078e')

    def test_the_fourteen_generated_lines_and_the_page_edge_survive(self):
        # BIT_SITES' 11, TEXTBOOK_BIT_SITES' 2 and the page-rule edge, in the
        # order and with the markers the run had before this branch. The block
        # runs from the blank line after the last `REL_SITES` row to the blank
        # line before the summary.
        last_rel = self.lines.index(self.TAIL[-1])
        generated = self.lines[last_rel + 2:-2]
        self.assertEqual(len(generated), len(D.BIT_SITES) +
                         len(D.TEXTBOOK_BIT_SITES) + 1)
        self.assertTrue(all(l.startswith('  ok ') for l in generated))
        self.assertEqual(generated[-1], '  ok  `01 ff` at 0x07FE targets '
                                       '0x08FF, the *following* page '
                                       '(expected 0x08FF)')


if __name__ == '__main__':
    unittest.main()
