#!/usr/bin/env python3
"""Offline checks for the `pd` "no ret" fall-through classification (issue #646).

`docs/findings/pd-no-ret-fallthrough-boundaries.md` retypes `pd,34EF` from
`unresolved` to `forwarder` on the reading that its three bytes fall straight
into `pd,34F2` and that the pair is two entries over one shared tail rather
than one routine cut in half by the export. This file pins the byte facts that
reading stands on.

**What it deliberately does not do.** It does not re-run
`pd_no_ret_fallthrough.py --self-test` and assert the tool against itself --
that would let a regenerated census pass on a stale pair. Every assertion here
is recomputed from the committed firmware, the committed `.asm` listings and
the committed annotation tables, and the generated CSV is read by predicate and
compared against those. It does not duplicate the tool's own oracle either: the
two are read together, this one from outside, so a change to the tool that
moves a byte fails here even when the tool's own check was updated with it.

**And it holds claims, not censuses.** A test that asserts how many rows the
family has is a value every merge has to edit, and this repository has been
burned by that four times. What is asserted here is each *byte* claim and each
*relationship*, and the population lives in one place -- the committed CSV,
which `--check` reproduces and which this suite reads by predicate. The tool's
`--self-test` is run for its exit code, so whatever it asserts is asserted
here transitively too, which is why it asserts byte facts, membership and
shape rather than either arm's size. `docs/findings/no-append-logs.md` is the
write-up; the same rule is in `CLAUDE.md`.
"""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import disasm8051
import pd_no_ret_fallthrough as sweep

FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
DECOMPILED = HERE.parent / 'decompiled'
ANNOTATIONS = ROOT / 'ec' / 'annotations'
INDEX_CSV = DECOMPILED / 'listing-index.csv'
CENSUS_CSV = ANNOTATIONS / 'pd-no-ret-fallthrough.csv'
FUNCTIONS_CSV = ANNOTATIONS / 'ghidra-functions.csv'

# The pair's three addresses, named because the claims are positional. Every
# one of them is re-read from the image below rather than trusted from here.
HEAD, SUCC, TAIL = 0x34EF, 0x34F2, 0x10BC
# The two `lcall 0x34EF` sites, the one `lcall 0x34F2` site, and the `ret` the
# pair's tail ends in. The return addresses the write-up names are these three
# plus two.
CALL_HEAD = (0x67E0, 0xCB40)
CALL_SUCC = (0x6782,)
RET_AT = 0x10C7

# The bytes, transcribed from the listings and re-read out of the image at each
# listed address. Kept whole rather than sampled: the claim is that `pd,34EF`
# is exactly three bytes and that `pd,34F2` begins immediately after, so a
# sample would not test the adjacency.
HEAD_BYTES = bytes.fromhex("90 04 24")            # mov DPTR,#0x0424
SUCC_BYTES = bytes.fromhex("75 f0 60 02 10 bc")   # mov B,#0x60 / ljmp 0x10bc
TAIL_LAST = 0x22                                   # ret

# Read once, the way `test_pd_entry_forms.py` gives: a per-test read of a
# 256 KiB image is not a cost worth paying repeatedly, and the assertions below
# compare what they read against the committed tables, so a wrong read fails
# rather than agreeing with itself.
IMAGE = FIRMWARE.read_bytes()
PD = IMAGE[sweep.PD_BASE:sweep.PD_BASE + sweep.PD_LEN]
STARTS, LISTINGS, TAILS = sweep.read_listings()
INDEX = sweep.load_index()
ANN = sweep.load_annotations()


def listing_instructions(addr):
    """(hex bytes, mnemonic text) for every instruction line of one committed
    listing, in address order.

    Read here rather than through the tool's parser, for the reason
    `test_pd_entry_forms.py` gives: a reader that mis-parsed the column cannot
    pass quietly, because the byte assertions below compare what comes back
    against the image."""
    out = []
    for line in (DECOMPILED / 'pd' / f'{addr:04X}.asm').read_text(
            errors="replace").splitlines():
        if line.startswith(";") or not line.strip():
            continue
        cols = line.split()
        raw = tuple(int(b, 16) for b in cols[1:4] if b != "-")
        out.append((bytes(raw), " ".join(cols[4:])))
    return out


def index_row(listing_file):
    with open(INDEX_CSV, newline="") as f:
        return {r['out_file']: r for r in csv.DictReader(f)
                if r['program'] == 'pd'}.get(f'pd/{listing_file:04X}.asm')


def census_rows():
    with open(CENSUS_CSV, newline="") as f:
        return list(csv.DictReader(f))


def census_row(addr):
    return next(r for r in census_rows() if int(r['addr'], 16) == addr)


def function_row(scope, addr):
    with open(FUNCTIONS_CSV, newline="") as f:
        return {(r['scope'], sweep.norm_addr(r['addr'])): r
                for r in csv.DictReader(f)}.get((scope, addr))


def annotation_for(listing_addr):
    """The annotation row a census row at `listing_addr` was read from.

    The census is keyed on a listing's *first instruction*, and four committed
    pd listings have a first instruction that is not the address their index
    row names -- `pd/0B85.asm` begins at 0x0B51 and is indexed at 0x0B85,
    `pd/4D6F.asm` at 0x4A12, and two more. The tool falls back to the index
    address for exactly those rows, and this does the same rather than
    reporting an empty comment for a listing that has one: a lookup that
    silently missed would make the `clause` column's own assertion vacuous on
    those four rows.

    The hop is head -> the listing's own file -> the index row's `addr` ->
    the annotation row, which is three steps and not one, and the reason a
    reader who joins the census to the annotations on address alone gets four
    empty comments and a `clause` column that disagrees with the tool on
    exactly those rows."""
    row = ANN.get(listing_addr)
    if row is not None:
        return row
    listing_file = TAILS[listing_addr][0][2]
    index_row = INDEX.get(listing_file)
    return ANN.get(sweep.norm_addr(index_row['addr'])) if index_row else None


class ThePairOnItsBytes(unittest.TestCase):
    """`pd,34EF` is three bytes, `pd,34F2` is six and starts immediately after,
    and `pd,10BC` ends in `ret`. Together those are the whole of the fall-
    through: the first two say control leaves 0x34EF by running on, the third
    says it comes back to the caller."""

    def test_head_listing_is_exactly_the_three_bytes(self):
        insns = listing_instructions(HEAD)
        self.assertEqual(len(insns), 1)
        self.assertEqual(insns[0][0], HEAD_BYTES)
        # The same bytes, re-read out of the image rather than from the
        # listing, so a listing that drifted from the firmware fails here
        # instead of agreeing with the constant beside it.
        self.assertEqual(PD[HEAD:HEAD + len(HEAD_BYTES)], HEAD_BYTES)
        self.assertEqual(disasm8051.mnemonic(PD, HEAD, HEAD),
                         "mov  dptr,#0x0424")

    def test_successor_listing_is_six_bytes_and_starts_at_the_next_address(self):
        insns = listing_instructions(SUCC)
        self.assertEqual([raw for raw, _t in insns], [b"\x75\xf0\x60",
                                                      b"\x02\x10\xbc"])
        self.assertEqual(PD[SUCC:SUCC + 6], SUCC_BYTES)
        self.assertEqual([t.split()[0] for _r, t in insns], ["mov", "ljmp"])
        self.assertEqual(disasm8051.mnemonic(PD, SUCC, SUCC),
                         "mov  0xf0,#0x60")
        # The adjacency is the load-bearing half. A non-adjacent successor
        # would make "control falls straight into it" a claim about a gap.
        self.assertEqual(SUCC, HEAD + len(HEAD_BYTES))

    def test_the_span_is_nine_bytes_and_neither_listing_says_so(self):
        # The issue's "the routine at 0x34EF is therefore complete at 6 bytes"
        # conflates the two listings' sizes with the span's. Held here because
        # a reader who has only one of the three numbers cannot tell which
        # mistake is being made.
        self.assertEqual(int(index_row(HEAD)['size']), 3)
        self.assertEqual(int(index_row(SUCC)['size']), 6)
        self.assertEqual(SUCC + 6 - HEAD, 9)
        self.assertNotEqual(9, int(index_row(SUCC)['size']))

    def test_the_tail_ends_in_ret_so_control_returns_to_the_caller(self):
        insns = listing_instructions(TAIL)
        self.assertEqual(insns[-1][0], bytes([TAIL_LAST]))
        self.assertEqual(PD[RET_AT], TAIL_LAST)
        self.assertEqual(insns[-1][1].split()[0], "ret")
        # The return address is the byte after the `lcall`, so the two sites
        # give 0x67E3 and 0xCB43 -- the second is what the companion issue
        # reads, and it is the address a fall-through reading must reach.
        self.assertEqual([site + 3 for site in CALL_HEAD], [0x67E3, 0xCB43])

    def test_the_last_two_instructions_of_the_pair_add_sixty_times_a(self):
        # `pd,10BC` is mul AB / add A,DPL / mov DPL,A / mov A,B / addc A,DPH /
        # mov DPH,A / ret, so with B = 0x60 the incoming DPTR becomes
        # DPTR + 0x60 * A. The effect the corrected comment records.
        body = [t.split()[0] for _r, t in listing_instructions(TAIL)]
        self.assertEqual(body, ["mul", "add", "mov", "mov", "addc", "mov",
                                "ret"])
        self.assertEqual(listing_instructions(SUCC)[0][0], b"\x75\xf0\x60")


class TheTwoEntries(unittest.TestCase):
    """0x34EF is `lcall`ed twice and 0x34F2 once, and that is what makes the
    pair two entries over a shared tail rather than one routine in two
    listings. Without the 0x6782 site the fall-through reading would be the
    whole story and the row would be a merge candidate instead."""

    def test_lcall_34ef_sites(self):
        sites = sweep.listing_sites(PD, LISTINGS)
        self.assertIn(HEAD, sites, "a committed listing decodes a transfer to "
                                   "0x34EF")
        for site in CALL_HEAD:
            self.assertEqual(PD[site], 0x12)
            self.assertEqual((PD[site + 1] << 8) | PD[site + 2], HEAD)
            self.assertIn(site, sites[HEAD])

    def test_34f2_is_lcalled_in_its_own_right(self):
        # The claim that changes the answer, so it is held on its own: one
        # `lcall 0x34F2`, at 0x6782, in the same listing as the `lcall 0x34EF`
        # at 0x67E0. If this site were not there, 0x34F2 would be reachable
        # only by falling in from 0x34EF and the two rows would be a merge
        # candidate on the evidence rather than two entries.
        self.assertEqual(len(CALL_SUCC), 1)
        site = CALL_SUCC[0]
        self.assertEqual(PD[site], 0x12)
        self.assertEqual((PD[site + 1] << 8) | PD[site + 2], SUCC)
        self.assertIn(site, sweep.listing_sites(PD, LISTINGS)[SUCC])

    def test_both_sites_are_committed_instruction_starts(self):
        # Not a byte pattern: an address no committed listing decodes is a
        # candidate, and the write-up's "in its own right" is only as strong
        # as the strength of this site. `pd_entry_forms.py`'s standing rule.
        for site in CALL_HEAD + CALL_SUCC:
            self.assertIn(site, LISTINGS, f"0x{site:04X} is a committed "
                                          f"instruction start")

    def test_the_pair_shares_one_listing_file_with_the_0x67e0_site(self):
        self.assertEqual(LISTINGS[CALL_HEAD[0]][2], LISTINGS[CALL_SUCC[0]][2])


class TheAnnotationRow(unittest.TestCase):
    """`pd,34EF` is a `forwarder` whose comment records the fall-through, and
    its name is unchanged. The name is held because the write-up leaves the
    rename alone deliberately: a name change ripples through five generated
    CSVs, and the name is not false."""

    def test_type_and_comment(self):
        row = function_row('pd', HEAD)
        self.assertIsNotNone(row)
        self.assertEqual(row['type'], 'forwarder')
        self.assertEqual(row['name'], 'set_dptr_0424')
        comment = row['comment']
        for clause in ('0x34F2', '0x60'):
            self.assertIn(clause, comment)

    def test_the_clause_the_correction_replaces_is_gone_but_the_claim_is_not(self):
        # The old comment said "not decoded here"; the new one must not, and
        # must instead say where control goes. Asserted as presence and
        # absence separately because a comment that kept both would read as
        # undecided while satisfying either test alone.
        comment = function_row('pd', HEAD)['comment']
        self.assertNotIn("not decoded here", comment)
        self.assertIn("no ret", comment)

    def test_the_successor_row_is_untouched(self):
        # `pd,34F2` was already annotated on exactly this reading, so this
        # change has nothing to say about it. Held so a merge that took both
        # rows fails here.
        self.assertEqual(function_row('pd', SUCC)['name'],
                         'add_60a_to_dptr_34f2')
        self.assertEqual(function_row('pd', SUCC)['type'], 'math')

    def test_the_3632_precedent_is_untouched(self):
        # `pd,3632`'s comment calls the pair "one routine split by the
        # function boundary". The byte scan's `lcall 0x3635` at 0x44A1 is a
        # candidate no committed listing decodes, so whether that makes the
        # comment a half-statement is not settled here and this change does not
        # edit the row. It is held as it stands so a merge that quietly took it
        # fails.
        self.assertEqual(function_row('pd', 0x3632)['name'],
                         'set_dptr_042f_then_fall_through')
        self.assertIn("split by the function boundary",
                      function_row('pd', 0x3632)['comment'])


class TheCensusIsReadByPredicate(unittest.TestCase):
    """The generated CSV is compared by predicate against the bytes, never by
    count: a row that has silently changed its verdict is a defect, and a
    total is a value every merge has to edit."""

    def test_34ef_is_in_the_family_with_the_shared_tail_verdict(self):
        row = census_row(HEAD)
        self.assertEqual(row['in_byte_arm'], 'yes')
        self.assertEqual(row['verdict'], 'shared-tail')
        self.assertEqual(int(row['addr'], 16), HEAD)
        self.assertEqual(int(row['successor'], 16), SUCC)
        self.assertEqual(int(row['size']), 3)
        self.assertEqual(int(row['succ_size']), 6)
        self.assertEqual(row['clause'], 'yes')

    def test_the_sites_the_verdict_rests_on_are_in_the_row(self):
        row = census_row(HEAD)
        self.assertEqual([int(s, 16) for s in row['self_sites'].split(';')],
                         list(CALL_HEAD))
        self.assertEqual([int(s, 16) for s in row['succ_sites'].split(';')],
                         list(CALL_SUCC))

    def test_every_verdict_is_one_of_the_three_the_tool_defines(self):
        # The vocabulary is the tool's, and a value invented in a follow-up
        # would make the CSV unreadable against this one.
        for row in census_rows():
            if row['verdict']:
                self.assertIn(row['verdict'], sweep.VERDICTS)

    def test_a_row_outside_the_family_carries_no_verdict(self):
        # A verdict on a row the byte arm did not admit would be a claim the
        # tool did not measure.
        for row in census_rows():
            if row['in_byte_arm'] == 'no':
                self.assertEqual(row['verdict'], '')

    def test_the_clause_column_is_the_clause_arm_and_nothing_else(self):
        # Re-derived from the comment rather than from the tool, because a
        # column that is "whatever the tool said" cannot catch the tool being
        # wrong about it.
        for row in census_rows():
            comment = (annotation_for(int(row['addr'], 16)) or {}).get(
                'comment', '')
            self.assertEqual(row['clause'],
                             'yes' if sweep.CLAUSE_RE.search(comment) else 'no')

    def test_the_pair_row_survives_a_regenerated_index(self):
        # Every family's successor, size and first instruction re-derived from
        # the image rather than from the CSV, so a regenerated listing-index
        # that moved one fails here instead of being held.
        for row in census_rows():
            if row['in_byte_arm'] != 'yes':
                continue
            a, s = int(row['addr'], 16), int(row['successor'], 16)
            self.assertEqual(int(row['size']), s - a)
            self.assertEqual(row['succ_first'],
                             disasm8051.mnemonic(PD, s, s))


class TheToolIsHeldToTheTree(unittest.TestCase):
    """`--check` is the tool's own contract with the committed CSV, and it is
    run as a subprocess so its exit code is observed rather than inferred."""

    def test_check_reproduces_the_committed_csv(self):
        r = subprocess.run(
            [sys.executable, str(HERE / 'pd_no_ret_fallthrough.py'), '--check'],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_self_test_passes(self):
        r = subprocess.run(
            [sys.executable, str(HERE / 'pd_no_ret_fallthrough.py'),
             '--self-test'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_a_dump_that_is_not_the_pd_image_is_refused(self):
        # `not found by this method` has to be able to say so. A file with the
        # marker missing must exit 1 with the offset named, rather than
        # decoding a page of arithmetic about the wrong program. The fixture
        # lives in a temp directory, not beside the committed vendor inputs,
        # so an interrupted run cannot leave a stray file in `ec/firmware/`.
        with open(FIRMWARE, 'rb') as f:
            whole = f.read()
        with tempfile.TemporaryDirectory() as tmp:
            scratch = Path(tmp) / 'not-the-pd-image.bin'
            scratch.write_bytes(whole[:sweep.PD_MARKER[0]]
                                + b"\x00" * len(whole[sweep.PD_MARKER[0]:]))
            r = subprocess.run(
                [sys.executable, str(HERE / 'pd_no_ret_fallthrough.py'),
                 str(scratch)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"0x{sweep.PD_MARKER[0]:05X}", r.stderr)

    def test_the_base_is_the_region_offset_and_not_the_marker(self):
        # The silent one: `PD_MARKER` is 0x40 bytes *inside* the image, so
        # using it as the base reads 0x40 bytes early in every one of the
        # 64 KiB -- which still decodes, at the wrong address. Held on the
        # offsets, and on the slice it would have produced.
        self.assertEqual(sweep.PD_BASE, 0x20000)
        self.assertNotEqual(sweep.PD_BASE, sweep.PD_MARKER[0])
        self.assertEqual(sweep.offset_for_runtime(HEAD, sweep.PD_REGION),
                         sweep.PD_BASE + HEAD)
        off = HEAD + sweep.PD_MARKER[0] - sweep.PD_BASE
        self.assertNotEqual(IMAGE[off:off + 3], HEAD_BYTES)


class TestWritesNothing(unittest.TestCase):
    """`pd_no_ret_fallthrough.py` writes only under `--csv`, and to stdout. A
    read-only default is what lets the tool be cited from a write-up without
    the write-up having to promise the reader's tree is clean afterwards."""

    def test_a_read_only_run_leaves_the_tree_alone(self):
        before = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True).stdout
        for flag in ([], ["--self-test"], ["--check"]):
            subprocess.run(
                [sys.executable, str(HERE / 'pd_no_ret_fallthrough.py')] + flag,
                capture_output=True, text=True)
        after = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True).stdout
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
