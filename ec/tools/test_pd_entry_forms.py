#!/usr/bin/env python3
"""Unit checks for the `pd` 0xE2E4 entry sweep (issue #340).

`docs/findings/pd-e2e4-entry-forms.md` reads the entry set of
`poll_d78a_for_indices_0_and_1` as one address -- the `lcall 0xE2E4` at 0xDA78
-- and the two other byte-scan candidates that spell a transfer into the body
as readings the committed bytes already account for another way. This file
pins the byte and structure facts that reading stands on.

**What it deliberately does not do.** It does not re-run the sweep that wrote
`../annotations/pd-entry-forms.csv` and then assert the tool against itself --
that would let a regenerated census pass on a stale pair. Every assertion here
is recomputed from the committed firmware, the committed `.asm` listings and the
committed annotation tables, and the generated CSV is read by predicate and
compared against those. And it does not duplicate `pd_entry_forms.py
--self-test`, which pins the same figures from inside the tool: the two are
read together, this one from outside the tool so a change to the tool that
moves a number fails here even when the tool's own oracle was updated with it.
"""
import csv
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import disasm8051
import pd_entry_forms as sweep

FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
DECOMPILED = HERE.parent / 'decompiled'
ANNOTATIONS = ROOT / 'ec' / 'annotations'
FORMS_CSV = ANNOTATIONS / 'pd-entry-forms.csv'
VARIABLES_CSV = ANNOTATIONS / 'ghidra-variables.csv'
INDEX_CSV = HERE.parent / 'decompiled' / 'listing-index.csv'

# The 15 instructions `pd/E2E4.asm` carries, first to last. Transcribed from the
# listing, and the listing is re-read rather than trusted: `body_listing()`
# below asserts that the bytes here are the bytes at 0xE2E4 in the image, so a
# listing that drifted fails rather than agreeing with the constant beside it.
BODY_FIRST, BODY_LAST = 0xE2E4, 0xE322
LISTED_BYTES = bytes.fromhex(
    "e4 fa af 02 12 d7 8a ef 60 2d 75 f0 60 ea 90 04 24 12 10 bc"
    "0a ea b4 01 c6 7f 01 22")
# The 35 bytes of the span that the committed listing does not carry. Kept as a
# whole rather than sampled, because the two things the write-up says about it
# -- that it holds a second `mov R7`, and that it ends `ret` -- are both
# statements about the block as a block.
UNLISTED = (0xE2F8, 0xE31B)
UNLISTED_BYTES = bytes.fromhex(
    "ea 12 b1 68 e0 fe a3 e0 ff 64 01 4e 60 15 ef f4 70 03 ee 64 01"
    "60 0c ef f4 70 03 ee 64 02 60 03 7f 00 22")

# Read once, the way `test_bank1_e582_framing.py` gives for `verify_gap_text`:
# a per-test read of a 256 KiB image is not a cost worth paying 40 times, and
# the suite's own assertions compare what they read against the committed
# tables, so a wrong read fails rather than agreeing with itself.
IMAGE = FIRMWARE.read_bytes()
PD = IMAGE[sweep.PD_BASE:sweep.PD_BASE + sweep.PD_LEN]
STARTS, LISTINGS = sweep.read_listings()


def listing_instructions(addr):
    """(hex bytes, mnemonic text) for every instruction line of one committed
    listing, in address order.

    Read here rather than through a shared parser, for the reason
    `test_bank1_e582_framing.py` gives: a reader that mis-parsed the column
    cannot pass quietly, because the byte assertions below compare what comes
    back against the image."""
    out = []
    for line in (DECOMPILED / 'pd' / f'{addr:04X}.asm').read_text(
            errors="replace").splitlines():
        if line.startswith(";") or not line.strip():
            continue
        cols = line.split()
        raw = tuple(int(b, 16) for b in cols[1:4] if b != "-")
        out.append((bytes(raw), " ".join(cols[4:])))
    return out


def index_row(addr):
    with open(INDEX_CSV) as f:
        return {r['addr']: r for r in csv.DictReader(f)
                if r['program'] == 'pd'}.get(f'{addr:04X}')


def listed_starts():
    """Every instruction start the committed export puts in the span, in
    address order. The listing is not contiguous, which is the whole of §"the
    span is not contiguous" below, so this is a set of addresses rather than a
    slice."""
    return [a for a in STARTS if BODY_FIRST <= a <= BODY_LAST]


def listed_bytes():
    """The span's instruction bytes, read back from the image at each start.

    Concatenated rather than sliced, because slicing is the misreading this
    suite exists to rule out: the bytes at the listed addresses are not
    28 consecutive bytes, and a test that compared a slice would be asserting
    the thing the write-up says is wrong."""
    out = bytearray()
    for a in listed_starts():
        out += PD[a:a + disasm8051.OPCODE_LEN[PD[a]]]
    return bytes(out)


def norm_addr(addr):
    """`addr` as an int, from either spelling the annotation CSVs use.

    `ghidra-functions.csv` carries `DA44` on some rows and `0x0EA2` on others,
    and `ghidra-variables.csv` the second form throughout, so a comparison done
    on the string would silently miss every bare-address row rather than fail.
    """
    return int(addr, 16)


def forms_rows():
    with open(FORMS_CSV, newline="") as f:
        return list(csv.DictReader(f))


def variables_rows():
    with open(VARIABLES_CSV, newline="") as f:
        return list(csv.DictReader(f))


def function_rows():
    with open(ANNOTATIONS / 'ghidra-functions.csv', newline="") as f:
        return list(csv.DictReader(f))


class TheBody(unittest.TestCase):
    """The span is 63 bytes and the index says 28, and both are pinned. The
    discrepancy is asserted rather than fixed: `listing-index.csv` regenerates,
    and a hand edit would be undone and would be a merge hazard besides."""

    def test_the_fifteen_instructions_are_the_listing_and_the_image(self):
        insns = listing_instructions(BODY_FIRST)
        self.assertEqual(len(insns), 15)
        self.assertEqual(b"".join(raw for raw, _ in insns), LISTED_BYTES)
        # The same 28 bytes, re-read out of the image at the listed addresses.
        # A contiguous slice at [0xE2E4:0xE300) is *not* them -- that is the
        # misreading, and asserting the slice would assert the error.
        self.assertEqual(listed_bytes(), LISTED_BYTES)
        self.assertNotEqual(PD[BODY_FIRST:BODY_FIRST + len(LISTED_BYTES)],
                            LISTED_BYTES)
        self.assertEqual([t.split()[0] for _r, t in insns],
                         ["clr", "mov", "mov", "lcall", "mov", "jz", "mov",
                          "mov", "mov", "lcall", "inc", "mov", "cjne", "mov",
                          "ret"])

    def test_the_listing_is_not_contiguous_across_the_span(self):
        # The load-bearing fact behind the whole `size` argument. The listing
        # holds 28 instruction bytes spread over a 63-byte span, so
        # `[addr, addr + size)` stops at 0xE2FF and never reaches the
        # `inc R2` / `cjne` / `mov R7,#0x1` / `ret` at 0xE31B-0xE322 -- the
        # return the caller's test is on.
        self.assertEqual(listed_starts(),
                         [0xE2E4, 0xE2E5, 0xE2E6, 0xE2E8, 0xE2EB,
                          0xE2EC, 0xE2EE, 0xE2F1, 0xE2F2, 0xE2F5,
                          0xE31B, 0xE31C, 0xE31D, 0xE320, 0xE322])
        self.assertEqual(BODY_LAST - BODY_FIRST + 1, 63)
        self.assertEqual(len(LISTED_BYTES), 28)
        self.assertEqual(int(index_row(BODY_FIRST)['size']), 28)
        self.assertEqual(PD[BODY_LAST], 0x22)
        self.assertEqual(PD[0xE322:0xE323], b"\x22")

    def test_the_span_carries_a_second_ret_and_a_second_mov_r7(self):
        # Not part of the entry sweep and deliberately asserted anyway, because
        # it is the reason the sweep's "63 bytes" matters and the reason the
        # `pd,0xDA44` row's "no other exit" clause is narrowed. The committed
        # export does not carry these bytes, so nothing here claims they are
        # inside the function -- only that they are inside the span, and that
        # they are not a repetition of the tail at 0xE31B-0xE322.
        lo, hi = UNLISTED
        block = PD[lo:hi]
        self.assertEqual(block, UNLISTED_BYTES)
        self.assertEqual(len(block), 35)
        self.assertEqual(block[-1], 0x22)
        self.assertEqual(block[-3:-1], b"\x7f\x00")     # mov R7,#0x00
        # Pinned to its address, not merely present: the write-up's claim is
        # positional, and a 0xFF that moved inside the block would satisfy
        # assertIn() and leave the claim untested.
        self.assertEqual(block[0xE300 - lo:0xE301 - lo], b"\xff")  # mov R7,A
        # ... and none of it is in a committed listing, which is the whole of
        # what is being claimed about it.
        for a in range(lo, hi):
            self.assertIsNone(sweep.owner_of(a, STARTS, LISTINGS)[0])
        self.assertEqual(disasm8051.converges_from(PD, lo), (20, 4))

    def test_the_only_mov_r7_on_a_listed_path_to_the_ret_is_the_one_at_e320(self):
        # The load-bearing fact behind "returns R7 = 1 on every path" -- over
        # the *listed* stream, which is the qualifier the write-up and the
        # annotation row both now carry. Two encodings load R7 and both are
        # counted: 0x7F is `mov Rn,#imm` with Rn in the low nibble, and 0xAF is
        # `mov Rn,direct`, which is how the loop loads its index (0x02 is R2).
        loads = []
        for a in listed_starts():
            raw = PD[a:a + disasm8051.OPCODE_LEN[PD[a]]]
            if raw[0] in (0x7F, 0xAF) and raw[0] & 0x07 == 0x07:
                loads.append((a, raw[0], raw[1]))
        self.assertEqual(loads, [(0xE2E6, 0xAF, 0x02), (0xE320, 0x7F, 0x01)])
        # The second is the last instruction before the `ret`, so it is the
        # one that decides the return value on every path the export carries.
        self.assertEqual(PD[0xE31F:0xE323], b"\xc6\x7f\x01\x22")
        self.assertEqual(0xE320 + 2, BODY_LAST)


class TheEntrySet(unittest.TestCase):
    """One entry found by this method, on the body's first byte; two candidates
    strictly inside, and the pair retires them by different halves. Set
    membership and a landing-site check, not a bare count, so a new annotation
    adding a listing cannot make this pass by accident."""

    def test_the_only_committed_entry_lands_on_the_first_byte(self):
        row = next(r for r in forms_rows() if r['site'] == '0xDA78')
        self.assertEqual((row['form'], row['target']), ('lcall', '0xE2E4'))
        self.assertEqual(row['population'], 'listing')
        self.assertEqual(row['status'], 'start')
        self.assertEqual(row['landing'], 'first-byte')
        self.assertEqual(row['origin'], 'outside')
        self.assertEqual(row['target_shape'], 'instruction-start')
        self.assertEqual(row['site_listing'], 'pd/DA44.asm')
        # The framing pair recomputed from the image, not read from the CSV.
        onto, over = disasm8051.converges_from(PD, 0xDA78)
        self.assertEqual((int(row['frame_onto']), int(row['frame_over'])),
                         (onto, over))
        # ... and the instruction is really there, at an instruction start in a
        # committed listing, spelling the transfer the row records.
        self.assertEqual(PD[0xDA78:0xDA7B], b"\x12\xe2\xe4")
        self.assertEqual(bytes(LISTINGS[0xDA78][0]), b"\x12\xe2\xe4")
        self.assertIn("lcall", LISTINGS[0xDA78][1])

    def test_exactly_one_candidate_from_a_committed_listing_reaches_the_body(self):
        outside = [r for r in forms_rows() if r['origin'] == 'outside']
        self.assertEqual(len(outside), 3)
        listed = [r for r in outside if r['population'] == 'listing']
        self.assertEqual([r['site'] for r in listed], ['0xDA78'])
        self.assertEqual(sorted(r['site'] for r in outside),
                         ['0x0BBA', '0xDA78', '0xE68B'])

    def test_the_0bba_candidate_is_the_cjne_displacement_pd_0bab_already_carries(self):
        # The strong form: not "the scan is unsupported" but "the byte it
        # consumed is the displacement of an instruction a committed listing
        # exports independently of this sweep", which is what
        # `bank1-e582-entry-framing.md` calls a displaced reading.
        row = next(r for r in forms_rows() if r['site'] == '0x0BBA')
        self.assertEqual((row['form'], row['target']), ('ljmp', '0xE322'))
        self.assertEqual(row['status'], 'cjne')
        self.assertEqual(row['site_listing'], 'pd/0BAB.asm')
        self.assertEqual(PD[0x0BB8:0x0BBB], b"\xbb\xfe\x02")
        self.assertEqual(bytes(LISTINGS[0x0BB8][0]), b"\xbb\xfe\x02")
        self.assertEqual(disasm8051.mnemonic(PD, 0x0BB8, 0x0BB8),
                         "cjne r3,#0xfe,0x0bbd")
        self.assertEqual(sweep.owner_of(0x0BBA, STARTS, LISTINGS),
                         (0x0BB8, 2))
        self.assertEqual(int(row['frame_onto']), 1)

    def test_the_e68b_candidate_targets_the_middle_of_a_listed_instruction(self):
        # The other half. 0xE68B is in no committed listing at all, so its
        # target is what retires it: 0xE2EF is the second byte of the
        # three-byte `mov B,#0x60` at 0xE2EE, not an instruction start.
        row = next(r for r in forms_rows() if r['site'] == '0xE68B')
        self.assertEqual((row['form'], row['target']), ('ajmp', '0xE2EF'))
        self.assertEqual(row['status'], 'gap')
        self.assertEqual(row['site_listing'], '')
        self.assertEqual(row['target_shape'], 'mid-instruction')
        self.assertEqual(PD[0xE2EE:0xE2F1], b"\x75\xf0\x60")
        self.assertEqual(sweep.owner_of(0xE2EF, STARTS, LISTINGS),
                         (0xE2EE, 1))
        self.assertEqual(sweep.owner_of(0xE68B, STARTS, LISTINGS),
                         (None, None))
        self.assertEqual(disasm8051.converges_from(PD, 0xE68B), (0, 24))

    def test_nothing_reaches_the_body_from_a_table(self):
        # The index-table half, and the scope filter with it. A `common` row at
        # 0xE2E4 would be a different image's byte; eligibility is measured
        # from the file offset the row names rather than from which tool wrote
        # it, which is why the count of discarded rows is asserted as well.
        eligible, discarded, found = sweep.table_rows(PD)
        self.assertEqual((eligible, found), (28, []))
        self.assertEqual(discarded, 231)
        self.assertEqual(eligible + discarded, 259)
        for name in ('index-table-entries.csv', 'index-table-spans.csv'):
            with open(ANNOTATIONS / name, newline="") as f:
                for row in csv.DictReader(f):
                    off = row.get('table_file_offset') or row.get(
                        'entry_file_offset')
                    self.assertFalse(sweep.PD_BASE <= int(off, 16)
                                     < sweep.PD_BASE + sweep.PD_LEN,
                                     f"{name} {off} is inside the pd extent")


class TheAddressSpaces(unittest.TestCase):
    """The rule the whole sweep rests on, asserted rather than cited: the PD
    image is a separate program with its own address space, and 0xE2E4 means
    two different bytes depending on which one is meant."""

    def test_only_the_pd_listing_covers_the_span(self):
        covering = {LISTINGS[sweep.owner_of(a, STARTS, LISTINGS)[0]][2]
                    for a in range(BODY_FIRST, BODY_LAST + 1)
                    if sweep.owner_of(a, STARTS, LISTINGS)[0] is not None}
        self.assertEqual(covering, {'pd/E2E4.asm'})

    def test_the_same_numbers_in_bank0_and_bank1_are_not_pd_entries(self):
        # bank0 0xE256 and bank1 0xE2D3 are the nearest listings on each side
        # of the span. They cover the same *numbers* as the body and are a
        # different image's bytes; the point of the assertion is that nothing
        # in this sweep read one of them.
        for scope, addr in (('bank0', 0xE256), ('bank1', 0xE2D3)):
            self.assertTrue((DECOMPILED / scope / f'{addr:04X}.asm').is_file())
        self.assertEqual({LISTINGS[a][2] for a in listed_starts()},
                         {'pd/E2E4.asm'})
        # The nearest pd listing above the span starts one byte past its last.
        self.assertEqual(min(a for a in STARTS if a > BODY_LAST), 0xE323)

    def test_a_runtime_address_sliced_out_of_the_dump_reads_the_wrong_program(self):
        self.assertNotEqual(IMAGE[BODY_FIRST:BODY_LAST + 1],
                            PD[BODY_FIRST:BODY_LAST + 1])
        self.assertEqual(sweep.offset_for_runtime(BODY_FIRST, sweep.PD_REGION),
                         sweep.PD_BASE + BODY_FIRST)
        self.assertNotEqual(sweep.PD_BASE, sweep.PD_MARKER[0])
        # The listing is named for the runtime address, so keying by file
        # offset finds no file for any candidate and reports every one of them
        # unframed -- the misreading `--self-test` asserts in the tool.
        self.assertTrue((DECOMPILED / 'pd' / f'{BODY_FIRST:04X}.asm').is_file())
        self.assertFalse((DECOMPILED / 'pd'
                          / f'{sweep.PD_BASE + BODY_FIRST:04X}.asm').exists())


class TheAnnotationRow(unittest.TestCase):
    """The `pd,0xDA44` row carries the sweep's answer *and* still carries the
    clause it amends, and it moves no register status. Presence checks rather
    than exact-prose ones, for the reason `test_bank1_e582_framing.py` gives:
    CLAUDE.md asks for the superseded wording left visible, and a test that
    matched it exactly would fail the next reader who tightened the prose."""

    def comment(self):
        rows = [r for r in variables_rows()
                if r['scope'] == 'pd' and norm_addr(r['addr']) == 0xDA44]
        self.assertEqual(len(rows), 1)
        return rows[0]['comment']

    def test_it_carries_the_answer_and_the_superseded_clause(self):
        c = self.comment()
        self.assertIn("0xDA78", c)
        self.assertIn("0xE322", c)
        self.assertIn("one transfer reaches the body", c)
        self.assertIn("0x0BBA", c)
        self.assertIn("0xE68B", c)
        self.assertIn("docs/findings/pd-e2e4-entry-forms.md", c)
        # The clause the amendment narrows, still visible.
        self.assertIn("0xE2E4 has no other exit", c)

    def test_the_narrowed_clause_names_the_bytes_it_rests_on(self):
        # The narrowing is the point of the amendment: the export carries one
        # exit, and the 63-byte span carries a second `ret` that the export does
        # not. A row that said only the first would be the overclaim.
        c = self.comment()
        self.assertIn("0xE2F8", c)
        self.assertIn("0xE31A", c)
        self.assertIn("no committed listing covers", c)

    def test_the_amendment_moves_no_register_status_and_seeds_no_entry(self):
        # Two claims this change is not making, pinned because both are cheap to
        # make by accident in prose. Nothing here is a behavioural claim, and
        # seeding an entry inside the body would split a routine for no reason.
        self.assertNotIn("status:", self.comment())
        pd_funcs = {norm_addr(r['addr']) for r in function_rows()
                    if r['scope'] == 'pd'}
        # 0xE2E4 keeps its own row -- the routine has an entry and always did.
        # What this change must not add is a second one inside the body, which
        # would split a routine in half for no reason.
        self.assertIn(BODY_FIRST, pd_funcs)
        for addr in range(BODY_FIRST + 1, BODY_LAST + 1):
            self.assertNotIn(addr, pd_funcs)


class TheToolAgreesWithTheTree(unittest.TestCase):
    """`--check` and `--self-test` are the tool's own halves, run here so a
    change that moves a number fails on the committed tree rather than on
    whoever next remembers to run them."""

    def test_check_reproduces_the_committed_csv(self):
        out = subprocess.run(
            [sys.executable, str(HERE / 'pd_entry_forms.py'), '--check'],
            capture_output=True, text=True, check=False)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn('reproduces it byte for byte', out.stdout)

    def test_self_test_passes(self):
        out = subprocess.run(
            [sys.executable, str(HERE / 'pd_entry_forms.py'), '--self-test'],
            capture_output=True, text=True, check=False)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn('self-test passed', out.stdout)


if __name__ == '__main__':
    unittest.main()
