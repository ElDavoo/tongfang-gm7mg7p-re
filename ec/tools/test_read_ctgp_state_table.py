#!/usr/bin/env python3
"""Offline checks for read_ctgp_state_table.py: committed files only.

The reader stands in for `check_capture_claims.py` on the one capture whose
addresses are its table's *columns* rather than its rows, so its failure mode is
the same and quieter: a rule that reads the header as a comment, or normalises
an address differently from the checker, and the reader then refuses every claim
or holds a claim it should not -- either way the run still exits 0 and the
figure it prints is the only evidence anything was read.

So what is pinned here is the line between what this shape can answer and what
it cannot. The column parse, the presence rule, the polarity (which is the
checker's, imported rather than rewritten), and the two refusals -- an address
the table has no column for, and a count. **Both refusals matter more than the
hold**, because the hold is what a reader expects to see and the refusals are
what a reader has to be told.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).parent
# The tool imports its walker and its polarity from check_capture_claims, and
# that imports check_cluster_citations; loading by path with the tool directory
# on sys.path is what running it does, and every sibling suite does this.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'read_ctgp_state_table', HERE / 'read_ctgp_state_table.py')
rcst = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcst)

CAPTURE = 'evidence/ec-watch/2026-09-23-ctgp-live.txt'
FULL = os.path.join(rcst.REPO, CAPTURE)


def claims(text, capture=CAPTURE, suffix='.md'):
    """(refusals, claims held) the reader reports for one piece of prose."""
    with tempfile.NamedTemporaryFile('w', suffix=suffix, delete=False) as f:
        f.write(text)
        path = f.name
    try:
        refusals, _, held = rcst.check(path, capture, False)
    finally:
        os.unlink(path)
    return refusals, held


def refusals_for(text, capture=CAPTURE):
    """The refusal strings, for the compact cases."""
    found, _held = claims(text, capture)
    return [r[3] for r in found]


class TheHeaderIsTheColumns(unittest.TestCase):
    """Where the addresses come from, which is the whole of the reader."""

    def setUp(self):
        self.cols, self.header = rcst.columns(FULL)

    def test_the_committed_table_has_four_address_columns(self):
        # The shape that sends this file to its own reader: four registers, and
        # the value column is not one of them.
        self.assertEqual(self.cols, ['0x0743', '0x0744', '0x0745', '0x0746'])
        self.assertIn('enforced.power.limit', self.header)
        self.assertNotIn('enforced.power.limit', self.cols)

    def test_the_comment_block_is_not_the_header(self):
        # The file's own `#` block names its watch set -- "`0x0743-0x0746`
        # read-modify-restore" -- so a reader that took the first line the `#`
        # filter left, or the first line at all, would find the same four
        # addresses *by accident* and pass every case below while reading the
        # wrong line. Asserted on the line, not on the addresses: the addresses
        # being right is not evidence about which line was read.
        self.assertTrue(self.header.startswith('state'))
        self.assertNotIn('read-modify-restore', self.header)

    def test_the_blank_line_after_the_comment_block_is_not_the_header(self):
        # The other half of the same trap, and the one that bit first: the
        # comment block is followed by an empty line, so "the first surviving
        # line" is not the header either.
        raw = rcst.capture_lines(FULL)
        self.assertEqual(raw[0].strip(), "", "the fixture changed shape")
        self.assertTrue(self.header.startswith('state'))

    def test_address_case_does_not_silently_match_nothing(self):
        # `0X0743` in prose and `0x0743` in the header are one address. An
        # upper() applied before the comparison makes every column look absent,
        # and the reader then refuses every claim in the tree and exits 0 --
        # a checker that passes by reading nothing.
        self.assertTrue(rcst.has_column(FULL, '0X0743'))
        self.assertFalse(rcst.has_column(FULL, '0x0799'))

    def test_an_unwatched_address_is_not_a_column(self):
        # The distinction the reader exists to keep: not-watched is not
        # did-not-move. `0x07C4` is the address
        # `docs/hardware-tests/ctgp-dben-07c4-bit3.md` names when it says the
        # capture watched the power limit "not `0x07C4`".
        self.assertFalse(rcst.has_column(FULL, '0x07C4'))


class AClaimIsHeldWhenTheTableHasItsColumn(unittest.TestCase):
    """The affirmative rule, and the shape of the prose that exercises it."""

    # `registers.yaml`'s own cTGP note, from the `- name: CTGP_DB_CTRL / OFFSET`
    # entry, abridged to the two sentences that matter and **keeping the first
    # of them**. That is not padding: "setting ... raised" and "records a live
    # test" carry no word in the checker's `MOVEMENT` vocabulary, so a fixture
    # built from the claim sentence alone is skipped as "no movement claim" and
    # the reader reads nothing. In the committed note the unit is a movement
    # claim because the sentence before it says the vendor *writes* those
    # registers per power mode -- which is why the fixture opens the way it
    # does rather than at the interesting half.
    CTGP_NOTE = ('The vendor writes them per power mode on AC: 0x0743=0x03, '
                 '0x0744=0x0A, 0x0745=0xFF, 0x0746=5. 2026-09-23 (issue #8), '
                 'confirmed live against nvidia-smi on the RTX 3070 Laptop '
                 '(' + CAPTURE + '): with the dGPU default_limit 115 W and max '
                 '140 W, setting 0x0743 bit 2 (cTGP enable) with 0x0744=0x0A '
                 'raised the *enforced* power limit 120 -> 130 W within ~1 s, '
                 'and clearing it restored 120.\n')

    def test_the_committed_ctgp_note_is_held(self):
        # The claim the entry's whole live evidence rests on. All four
        # registers are columns, so all four are held.
        refusals, held = claims(self.CTGP_NOTE)
        self.assertEqual(refusals, [])
        self.assertEqual(held, 4)

    def test_the_dmi_note_that_cites_it_is_held(self):
        # `docs/findings/dmi-descriptor-evidence.md`'s unit, the sibling of the
        # one above: two addresses, both columns. Its movement word is
        # "records", which is in `MOVEMENT` -- so this one needs no preceding
        # clause, and the pair is what shows the fixture's dependence on the
        # movement guard rather than on the addresses.
        text = ('The issue wrote it up as untested, and registers.yaml\'s '
                '0x0743 entry records a live test against nvidia-smi on '
                '2026-09-23 (' + CAPTURE + ') in which setting 0x0743 bit 2 '
                'with 0x0744 raised the *enforced* power limit from 120 W to '
                '130 W and clearing it restored 120.\n')
        refusals, held = claims(text)
        self.assertEqual(refusals, [])
        self.assertEqual(held, 2)

    def test_one_address_named_twice_is_one_claim(self):
        # A unit naming a byte in two clauses is one claim about a register.
        # Counting it twice would make the run's figure a count of sentences.
        text = ('0x0743 moved in ' + CAPTURE + ' and 0x0743 was read back.\n')
        _refusals, held = claims(text)
        self.assertEqual(held, 1)

    def test_the_presence_rule_is_load_bearing_rather_than_asserted_to_be(self):
        # The suite's drop-it-in-turn form. `has_column()` patched to answer
        # `True` for everything holds every address in the corpus, which is
        # what a reader that never compared anything would print; patched to
        # answer `False` for everything holds none. The hold is the rule doing
        # work, not the figure being stable.
        text = '`0x0743` moved in ' + CAPTURE + ', and `0x0799` moved.\n'
        self.assertEqual(claims(text)[1], 1)
        with mock.patch.object(rcst, 'has_column', lambda _p, _a: True):
            self.assertEqual(claims(text)[1], 2)
        with mock.patch.object(rcst, "has_column", lambda _p, _a: False):
            self.assertEqual(claims(text)[1], 0)

    def test_a_unit_naming_no_capture_yields_no_claim(self):
        # `if capture not in unit: continue` -- the guard that keeps this
        # reader off the other 400-odd files, and the one a widened search
        # would remove.
        self.assertEqual(claims('0x0743 moved in some other capture.\n'),
                         ([], 0))


class ARefusalIsNotADisagreement(unittest.TestCase):
    """The two answers this shape can give for a claim it cannot hold.

    Both of these were the design's whole risk: a reader that reports "the
    capture says nothing about it" as a disagreement has invented a defect in
    prose that agrees with the capture, and a reader that answers `0` has
    asserted a fact about the firmware it has no evidence for. The first is a
    false red; the second is a false green that reads as a check.
    """

    def test_an_address_the_table_never_watched_is_refused_not_reported(self):
        text = '`0x0799` moved in ' + CAPTURE + '.\n'
        refusals, held = claims(text)
        self.assertEqual(held, 0, "nothing was held, so nothing may fail")
        self.assertEqual(len(refusals), 1)
        self.assertIn('0x0799', refusals[0][3])
        self.assertIn('not read by this method', refusals[0][3])

    def test_a_denial_about_an_unwatched_address_is_refused_too(self):
        # `ctgp-dben-07c4-bit3.md`'s sentence, and the reason polarity is not
        # in this reader: "it watched the dGPU's *enforced power limit*, not
        # `0x07C4`" is a *denial*, and the table having no `0x07C4` column
        # agrees with it. Inverting the presence check would change no verdict
        # -- an address with no column is unread either way -- so the polarity
        # walk is left out rather than imported for the one sentence it would
        # describe wrongly. What is pinned is that the sentence is not reported
        # as a disagreement and not held either.
        text = ('The two existing captures are not runs of this. '
                '`evidence/ec-watch/2026-09-23-ctgp-live.txt` is issue #8\'s '
                'live write of `0x0743` measured against nvidia-smi; it drove '
                'bit 2 (cTGP enable), not bit 1, and it watched the dGPU\'s '
                '*enforced power limit*, not `0x07C4`.\n')
        refusals, held = claims(text)
        self.assertEqual(held, 1, "0x0743 is a column and is held")
        self.assertEqual(len(refusals), 1)
        self.assertIn('0x07C4', refusals[0][3])
        self.assertIn('not read by this method', refusals[0][3])

    def test_the_refusal_wording_covers_both_polarities(self):
        # What the refusal says is the sentence that survives dropping the
        # polarity walk. It says the byte's *movement* is unread, not that the
        # capture denies it -- a claim about what a reader may conclude, which
        # is true whichever way the prose reads the address.
        text = '`0x07C4` never moved in ' + CAPTURE + '.\n'
        refusals, _held = claims(text)
        self.assertIn('whether the byte moved is not read by this method',
                      refusals[0][3])

    def test_a_count_is_refused_rather_than_answered_zero(self):
        # The absence that is easiest to get wrong, because answering it costs
        # nothing to the tool: the table has no per-address row set, so a count
        # compared against it yields 0 for every address, and every count claim
        # naming this capture would be reported as a disagreement against a
        # capture that never made a count. `check_capture_claims.py` applies
        # `COUNT` to everything in its index; this file must not be in it.
        text = '`0x0743` moved 3 times in ' + CAPTURE + '.\n'
        refusals, held = claims(text)
        self.assertEqual(len(refusals), 1, "the count itself is refused")
        self.assertIn('3 times', refusals[0][2], "the refusal names what it refuses")
        self.assertIn('not read by this method', refusals[0][3])
        # The presence half is still read, exactly as the checker reads both
        # halves of a mixed-polarity sentence. What is refused is the count,
        # not the sentence.
        self.assertEqual(held, 1, "0x0743 is a column, so the attribution holds")

    def test_a_count_is_refused_even_where_the_address_is_a_column(self):
        # The sharpness for the case above, and the one that separates "no count
        # here" from "no count *for that address*": `0x0743` is watched in all
        # five rows and the table still cannot say it moved three times, since a
        # row is a state and not a change. A reader that read counts as
        # "distinct values in the column" would answer 2 here and be asserting
        # that the person chose two interventions.
        text = '`0x0743` moved 2 times in ' + CAPTURE + '.\n'
        refusals, _held = claims(text)
        self.assertEqual(len(refusals), 1)
        self.assertIn('no per-address change count', refusals[0][3])

    def test_a_unit_with_no_count_produces_no_count_refusal(self):
        # So the refusal is not a line printed on every run: it fires on the
        # count and on nothing else.
        text = '`0x0799` moved in ' + CAPTURE + '.\n'
        refusals, _held = claims(text)
        self.assertEqual(len(refusals), 1)
        self.assertNotIn('per-address change count', refusals[0][3])

    def test_the_refusal_says_which_address_it_is_about(self):
        # A refusal naming no subject is a refusal the reader has to go and
        # find the subject of, and a refusal a reader cannot attribute is a
        # refusal they cannot act on.
        text = '`0x0799` and `0x079A` moved in ' + CAPTURE + '.\n'
        refusals, _held = claims(text)
        self.assertEqual([r[2] for r in refusals], ['0x0799', '0x079A'])

    def test_no_run_over_the_committed_prose_exits_non_zero(self):
        # The exit is the reader's last line of defence, and it is asserted
        # here rather than assumed: a design that reported "the capture says
        # nothing" as a defect would be red on the committed tree, over
        # `ctgp-dben-07c4-bit3.md`, which is correct prose.
        err = io.StringIO()
        argv = sys.argv
        sys.argv = ['read_ctgp_state_table.py', '--check']
        try:
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(err):
                rc = rcst.main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0, err.getvalue())


class TheCommittedTree(unittest.TestCase):
    """The real thing: the cTGP prose agrees with the table it names.

    `registers.yaml`'s `CTGP_DB_CTRL / OFFSET` entry is `confirmed-working` on
    the strength of one file, and this is what makes that entry's live claim
    something a run checks rather than something a re-reading checks. It is the
    assertion the issue asks for at the end: the entry is held to the capture,
    or it carries a stated reason it is not.
    """

    def test_the_ctgp_entry_is_held_to_its_capture(self):
        # Membership, not a figure: the entry is named because a claim in it was
        # held, and equality is not an invariant -- the next document added to
        # the tree adds a claim. Asserted as "this file yields held claims and
        # no refusals for an address it does not watch", which is a property of
        # the prose rather than a count of it.
        full = os.path.join(rcst.REPO, 'ec/annotations/registers.yaml')
        refusals, _lines, held = rcst.check(full, CAPTURE, False)
        self.assertGreater(held, 0,
                           "the entry that `confirmed-working` rests on "
                           "yields no held claim")
        self.assertEqual(refusals, [])

    def test_the_committed_table_still_parses(self):
        # A reader whose subject stopped parsing would refuse every claim and
        # exit 0, so the parse is asserted directly rather than through a
        # figure that would look the same either way.
        cols, header = rcst.columns(FULL)
        self.assertEqual(cols, ['0x0743', '0x0744', '0x0745', '0x0746'])
        self.assertTrue(header)

    def test_the_held_figure_is_printed_and_is_not_zero(self):
        # A run that read nothing and a run that held everything both print a
        # green line; the figure is what tells them apart, so a zero here is a
        # reader that has stopped reading rather than a tree with no claims.
        out, err = io.StringIO(), io.StringIO()
        argv = sys.argv
        sys.argv = ['read_ctgp_state_table.py', '--check']
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = rcst.main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0, err.getvalue())
        self.assertIn('state-table claim(s) held', out.getvalue())
        held = int(out.getvalue().split(' lines / ')[1].split(' ')[0])
        self.assertGreater(held, 0)
        # And the refusal half is printed on the same run rather than only
        # under --verbose: a refusal nothing prints is a refusal with no teeth,
        # and this reader's contribution over the checker skipping the file is
        # the reader being able to see it.
        self.assertIn('not read by this method', err.getvalue())


if __name__ == '__main__':
    unittest.main()