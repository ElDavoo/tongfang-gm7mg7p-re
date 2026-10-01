#!/usr/bin/env python3
"""The AP_OEM bit-7 chain: one setter, a 253-byte scan, and the correction of
a committed annotation that read the loop as three iterations (issue #114).

`docs/findings/0741-bit7-oc-recovery.md` is the write-up. What it claims is
that bit 7 of XDATA 0x0741 -- the request BIOS 1.09's `OemOcDxe` reads as
"overclocking failed, recover" -- is set by exactly one instruction, at
bank0 0xCFEE, and that the instruction runs when a two-bit accumulator at
0x0816 reads 3, which happens when the bytes 0x14 and 0x32 have both been seen
in the 253-byte XDATA region 0x0B00-0x0BFC.

**Every assertion here is made against the image bytes, not against a re-run
of the scan that produced the finding.** That distinction is the whole reason
this file exists rather than a diff of the committed CSV against itself: a
table regenerated from the same walk it is checked against would agree with a
stale transcription indefinitely. The one case that does re-run a tool is
`TheTableIsReproducible`, and it re-runs it against the *committed CSV file*,
so a tool whose output changed fails rather than confirming its own output.

Four of these cases are the load-bearing ones and each is a claim that could
be wrong in a specific, nameable way:

  - **The setter's eight bytes.** `90 07 41 e0 44 80 f0 22` at 0xCFEE. If
    these were not the bytes, nothing else in the file mattered.
  - **The back-edge `b4 fd e1`.** This is what refutes "three iterations" from
    the image rather than from prose. It is asserted as bytes, so the
    correction stands on the firmware and not on this repository agreeing with
    itself about the firmware.
  - **`0xD078`'s twelve bytes.** The claim that the scan reads
    `XDATA[0x0B00 + R5]` is arithmetic, and arithmetic in a decompile is a
    reading; the byte column settles it.
  - **The 253 figure's two halves.** 0xFD as the loop's stop value gives 0x00
    through 0xFC, and the two bank1 scanners' `cjne DPL,#0xfd` bounds give the
    same span from the other direction. A figure that only one routine
    supplies would be one routine's reading.

**The negative is held as a claim about the tools, not about the machine.**
`test_no_writer_is_found_and_the_saying_is_calibrated` runs
`find_indirect_xdata.py` over page 0x0B and asserts that *no* anchored
`movx @Ri` site there resolves -- and that the write-up says "not found by
this method" rather than "absent", because the region is provably read as a
marker buffer and something must write it. A suite that only asserted the
zero would be satisfied by a firmware with no writer at all.

Nothing here reads hardware, needs Windows or needs Ghidra: the firmware is the
committed `ec/firmware/GMxMGxx_11.800` and everything else is committed text.
"""
import csv
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
# trace_xdata_refs imports disasm8051 by bare module name, the way
# test_trace_xdata_refs.py does and for the same reason.
sys.path.insert(0, str(HERE))

import verify_gap_text as G          # noqa: E402
import yaml                         # noqa: E402

FIRMWARE = REPO / 'ec' / 'firmware' / 'GMxMGxx_11.800'
ANNOTATIONS = REPO / 'ec' / 'annotations'
FUNCTIONS = ANNOTATIONS / 'ghidra-functions.csv'
SITES_CSV = ANNOTATIONS / 'ap-oem-0741-bit7-sites.csv'
TASK_TABLE = ANNOTATIONS / 'task-call-table.csv'
WRITEUP = REPO / 'docs' / 'findings' / '0741-bit7-oc-recovery.md'
REGISTERS = ANNOTATIONS / 'registers.yaml'
FIND_INDIRECT = HERE / 'find_indirect_xdata.py'
TRACE = HERE / 'trace_xdata_refs.py'

# Address == image offset for every program, which is what make_bank_image.py
# arranges and why nothing here does address arithmetic of its own. Loaded once
# rather than per test, for the reason test_xdata_07fd_07ff_triple.py gives.
IMAGES = G.load_images()

# The eight bytes at 0xCFEE: `mov DPTR,#0x0741` / `movx A,@DPTR` /
# `orl A,#0x80` / `movx @DPTR,A` / `ret`. Spelled as bytes rather than as a
# mnemonic string because the byte column is the claim -- `0x0741` is 07 41
# and a transcription that transposed them would still read as "the setter".
SETTER = bytes((0x90, 0x07, 0x41, 0xE0, 0x44, 0x80, 0xF0, 0x22))

# `cjne A,#0xfd,-0x1f` -- the back-edge at 0xCFE4 that jumps back to 0xCFC8.
# 0xFD is the signed-char -3 the decompile prints as `cVar1 != -3`, and the
# correction is that it is 253 and not three.
BACK_EDGE = bytes((0xB4, 0xFD, 0xE1))

# `0xD078` in full: DPTR = 0x0B00 + R5, then `movx A,@DPTR`, then `ret`.
# Twelve bytes with no branch among them, so the routine's whole address
# arithmetic is here and nowhere else.
READER = bytes((0x74, 0x00, 0x2D, 0xF5, 0x82, 0xE4,
                0x34, 0x0B, 0xF5, 0x83, 0xE0, 0x22))


def bank(name):
    return IMAGES[name]


def rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def annotation(scope, addr):
    """The one ghidra-functions.csv row, or a failure naming both keys.

    Keyed on (scope, addr) rather than on addr alone because the two CODE
    banks are numbered in the same address space and `0xCFC6` could name a row
    in each; a lookup that ignored the scope would silently read the wrong one.
    """
    for row in rows(FUNCTIONS):
        if row['scope'] == scope and row['addr'].lower() == addr.lower():
            return row
    raise AssertionError('no ghidra-functions.csv row for %s %s' % (scope, addr))


class TheSetter(unittest.TestCase):
    """One instruction sets bit 7, and it is the one the write-up names."""

    def test_the_setter_bytes_are_where_the_writeup_says(self):
        self.assertEqual(bank('bank0')[0xCFEE:0xCFEE + len(SETTER)], SETTER)

    def test_the_setter_is_the_tail_of_the_annotated_routine(self):
        # `ret` closes both, so the eight bytes end exactly where the routine
        # ends. If the routine grew or the setter moved into it, the two
        # offsets would no longer agree and the write-up's "at the tail of"
        # would have become "somewhere inside".
        listing = bank('bank0')[0xCFC6:0xCFF6]
        self.assertEqual(listing[-len(SETTER):], SETTER)
        self.assertEqual(listing[-1], 0x22)

    def test_it_is_the_only_site_of_the_35_whose_window_sets_bit_7(self):
        # Read from the committed table's `window` column, which is the
        # per-site decode the write-up's "35 sites" sentence rests on. The
        # assertion is over the table rather than over a fresh walk so that a
        # scan whose rules changed shows up as a diff to be adjudicated, not
        # as a silent redefinition of what the table means.
        setters = [r['runtime'] for r in rows(SITES_CSV)
                   if 'a,#0x80' in r['window'] or 'acc.7' in r['window']]
        self.assertEqual(setters, ['0xCFEE'],
                         'bit 7 is set at more than the one site the write-up '
                         'names, or at none')

    def test_the_table_has_a_row_for_every_site(self):
        self.assertEqual(len(rows(SITES_CSV)), 35)


class TheCondition(unittest.TestCase):
    """`0x0816 == 3` after a 253-byte scan for 0x14 and 0x32."""

    def test_the_reader_computes_0x0b00_plus_r5(self):
        self.assertEqual(bank('bank0')[0xD078:0xD078 + len(READER)], READER)

    def test_the_loop_back_edge_pins_253_iterations(self):
        self.assertEqual(bank('bank0')[0xCFE4:0xCFE4 + 3], BACK_EDGE)
        # And the arithmetic, stated rather than left implicit: the counter
        # starts at 0 (`e4 fd` at 0xCFC6) and stops when it *reaches* 0xFD, so
        # the body runs for 0x00 through 0xFC.
        self.assertEqual(bank('bank0')[0xCFC6:0xCFC8], bytes((0xE4, 0xFD)))
        self.assertEqual(0xFD, 253)

    def test_the_scan_spans_0x0b00_to_0x0bfc(self):
        # 0x0B00 + 0xFC, off the back-edge's stop value. Asserted because the
        # 253 and the region are the same fact stated twice, and a change to
        # one that left the other would be the correction going stale.
        self.assertEqual(0x0B00 + 0xFC, 0x0BFC)

    def test_the_two_bank1_scanners_bound_the_same_span(self):
        # The independent check on the 253. Both scanners are already
        # annotated as walking to `DPL == 0xFD`, and both really do. Each is
        # `mov dptr,#0x0b00` / `movx a,@dptr` / `cjne a,#0x1c` /
        # `sjmp` / `inc dptr` / `mov a,dpl` / `cjne a,#0xfd`, sixteen bytes
        # with the marker compare at offset 4 and the bound at offset 13. If
        # either bounded the walk differently, the agreement that makes §4 of
        # the write-up checkable would be gone.
        for addr in (0xA43B, 0xAAA2):
            window = bank('bank1')[addr:addr + 16]
            self.assertEqual(window[0:3], bytes((0x90, 0x0B, 0x00)),
                             '0x%04X no longer starts at 0x0B00' % addr)
            self.assertEqual(window[4:6], bytes((0xB4, 0x1C)),
                             '0x%04X no longer compares against 0x1C' % addr)
            self.assertEqual(window[13:15], bytes((0xB4, 0xFD)),
                             '0x%04X no longer compares against 0xFD' % addr)

    def test_both_marker_bytes_are_compared_in_the_loop(self):
        # `cjne A,#0x14` at 0xCFCB and `cjne A,#0x32` at 0xCFD8, and the two
        # lcalls that feed them both at 0xD078 with R5 unadvanced between them
        # -- which is what makes one byte unable to satisfy both.
        body = bank('bank0')[0xCFC8:0xCFE2]
        self.assertEqual(body.count(bytes((0x12, 0xD0, 0x78))), 2)
        self.assertEqual(bank('bank0')[0xCFCB:0xCFCB + 3],
                         bytes((0xB4, 0x14, 0x07)))
        self.assertEqual(bank('bank0')[0xCFD8:0xCFD8 + 3],
                         bytes((0xB4, 0x32, 0x07)))

    def test_the_guard_is_an_equality_against_three(self):
        # `cjne A,#0x3,+7` at 0xCFEB, whose equal case is the setter. An
        # inequality against 3, or a comparison against a different constant,
        # would be a different condition than the write-up's.
        self.assertEqual(bank('bank0')[0xCFEB:0xCFEE], bytes((0xB4, 0x03, 0x07)))


class TheClearSites(unittest.TestCase):
    """Three sites clear bit 7 and two of them take the latch with them."""

    def test_both_clears_mask_off_bit_7_and_zero_the_latch(self):
        # `anl a,#0x7f` then `mov dptr,#0x0816`. At 0xAD4E the store itself
        # is a `lcall 0xbc3f`, which writes the caller's A through whatever
        # DPTR it was handed (store_a_then_clear_0824_bit7_and_0768_bit2), so
        # the pair asserted here is "clear the flag, then hand the latch to a
        # store of zero" rather than two inline movx writes.
        for addr in (0xCF78, 0xAD46):
            window = bank('bank0')[addr:addr + 12]
            self.assertEqual(window[0:3], bytes((0x90, 0x07, 0x41)))
            self.assertIn(bytes((0x54, 0x7F)), window[:8],
                          '0x%04X no longer clears bit 7 where the reading says'
                          % addr)
            self.assertIn(bytes((0x90, 0x08, 0x16)), window[:12],
                          '0x%04X no longer zeroes 0x0816 in the same breath'
                          % addr)

    def test_the_cf78_clear_is_the_0x81_arm_of_the_0x06e6_dispatcher(self):
        # The dispatcher's own arm table: `add A,#0x7e` / `dec A` / `dec A` /
        # `add A,#0x3` maps 0x82, 0x83, 0x84 and 0x81 onto the four tail
        # jumps, and 0x81 is the one that falls through into the clear. Held
        # as the byte column so "the 0x81 arm" is a reading of the arithmetic
        # rather than an assertion about it.
        self.assertEqual(bank('bank0')[0xCF6A:0xCF6C], bytes((0x24, 0x7E)))
        self.assertEqual(bank('bank0')[0xCF84:0xCF87], bytes((0x02, 0xCD, 0xE4)))
        self.assertEqual(bank('bank0')[0xCF87:0xCF8A], bytes((0x02, 0xCE, 0x9E)))
        self.assertEqual(bank('bank0')[0xCF8A:0xCF8D], bytes((0x02, 0xCE, 0xE9)))
        self.assertEqual(bank('bank0')[0xCF8D:0xCF90], bytes((0x02, 0xCE, 0x37)))

    def test_the_latch_has_five_bank0_sites_and_the_rest_are_the_pd_image(self):
        # `0x0816` is read as a latch rather than a scratch byte, and that is
        # a claim about *where* its sites are. The PD half is named rather
        # than summed: it is a different program's XDATA map, and a total that
        # added the two would be the file-wide count `trace_xdata_refs.py`
        # splits for exactly this reason.
        regions = {}
        # The 0x0816 census is not the 0x0741 table, so it is taken from the
        # tool the write-up cites for it rather than from SITES_CSV.
        out = subprocess.run(
            [sys.executable, str(TRACE), str(FIRMWARE), '0x0816',
             '--csv', '--terminator-column'],
            capture_output=True, text=True, check=True).stdout
        for row in csv.DictReader(io.StringIO(out)):
            regions.setdefault(row['region'], []).append(int(row['runtime'], 16))
        self.assertEqual(sorted(regions['bank0']),
                         [0xAD4E, 0xCF80, 0xCFCE, 0xCFDB, 0xCFE7])
        self.assertNotIn('common', regions)
        self.assertTrue(regions['pd-image'], 'the PD half went missing')


class TheCallPath(unittest.TestCase):
    """`0xCFC6` has no `lcall` caller and one `ljmp`, from the task run."""

    def test_no_lcall_reaches_cfc6_from_either_bank_or_the_pd_image(self):
        for name in ('bank0', 'bank1', 'pd'):
            self.assertNotIn(bytes((0x12, 0xCF, 0xC6)), bank(name),
                             '%s has an lcall 0xCFC6 the write-up denies' % name)

    def test_the_single_jump_is_the_tail_of_the_task_run_at_0x851b(self):
        self.assertEqual(bank('bank0')[0x8521:0x8524], bytes((0x02, 0xCF, 0xC6)))
        self.assertEqual(bank('bank0')[0x851B:0x851E], bytes((0x12, 0xA7, 0xC8)))

    def test_the_task_table_still_names_the_far_call_stub(self):
        # `ec/annotations/task-call-table.csv` is what makes the run reachable
        # at all, since nothing branches to it. Keyed on the target rather
        # than the row number: a row index moves when any annotation merges.
        hits = [r for r in rows(TASK_TABLE) if r['target'].upper() == '0X851B']
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['opcode'], 'ljmp')
        self.assertEqual(hits[0]['address'].upper(), '0X1564')


class TheAnnotationSaysSo(unittest.TestCase):
    """The drift guard between the machine-readable layer and the prose.

    A comment edit that reverted to "three iterations" would leave the image
    assertions above all passing -- the bytes are the bytes whatever the CSV
    says -- and the correction silently undone. This class is what holds the
    two together, in the shape `test_de3c_store_target.py` uses to keep a
    retraction visible.
    """

    def test_the_cfc6_comment_no_longer_claims_three_iterations(self):
        comment = annotation('bank0', '0xCFC6')['comment']
        self.assertNotIn('Runs three iterations', comment)
        self.assertIn('253', comment)

    def test_the_cfc6_comment_carries_the_scanned_address(self):
        comment = annotation('bank0', '0xCFC6')['comment']
        self.assertIn('0x0B00', comment)

    def test_the_superseded_sentence_stays_visible_beside_the_correction(self):
        # CLAUDE.md's calibration rule: a retraction leaves the wrong version
        # readable with the correction next to it. A comment that simply
        # stopped saying "three" would have hidden that this repository once
        # got it wrong, which is the part a reader needs.
        comment = annotation('bank0', '0xCFC6')['comment']
        self.assertIn('previously annotated as three iterations', comment)

    def test_the_row_still_cites_the_writeup_and_an_evidence_path(self):
        row = annotation('bank0', '0xCFC6')
        self.assertIn('docs/findings/0741-bit7-oc-recovery.md', row['evidence'])
        for path in row['evidence'].split('; '):
            self.assertTrue((REPO / path).is_file(),
                            'evidence path does not exist: %s' % path)

    def test_the_registers_note_names_the_traced_condition(self):
        with open(REGISTERS) as f:
            note = next(e['note'] for e in yaml.safe_load(f)['registers']
                        if e.get('addr') == 0x0741)
        self.assertIn('0xCFEE', note)
        self.assertNotIn('is not traced', note)
        # The status is for bit 0 only, and that is not this change's to move.
        self.assertIn('bit 0 only', note)


class TheLimitsAreStated(unittest.TestCase):
    """The calibration is a claim about this file too.

    A negative that reads "there is no writer" would be stronger than any
    method in the tree supports, and the region is provably read as a marker
    buffer by three routines. So the wording is held, and the zero the tools
    actually return is held beside it.
    """

    TEXT = None

    @classmethod
    def setUpClass(cls):
        cls.TEXT = WRITEUP.read_text()

    def test_the_writeup_says_the_writing_is_not_found_not_absent(self):
        self.assertIn('not found by this method', self.TEXT)
        self.assertNotIn('there is no writer', self.TEXT)

    def test_the_writeup_states_that_nothing_was_measured_on_hardware(self):
        # The CLAUDE.md rule for an issue whose work turns out to need the
        # hardware: preparation, not results.
        self.assertIn('Nothing here is a live test', self.TEXT)

    def test_no_writer_is_found_and_the_saying_is_calibrated(self):
        # The tool's own report, run here rather than quoted: no anchored
        # `movx @Ri` site on page 0x0B resolves to an address, and every one of
        # them is unresolved for the same reason. That is what "no writer is
        # found by this method" is made of, and running it is what stops the
        # sentence from outliving the result it describes.
        #
        # The non-zero exit is the claim, not an accident: `--page` returns
        # non-zero when the page is reached by nothing resolvable at all, so
        # that a scripted caller can use it. Asserting exit 0 here would
        # assert the opposite of what the write-up says.
        buf = io.StringIO()
        with redirect_stderr(buf):
            proc = subprocess.run(
                [sys.executable, str(FIND_INDIRECT), str(FIRMWARE),
                 '--page', '0x0B'],
                capture_output=True, text=True)
        report = proc.stdout
        self.assertEqual(proc.returncode, 1,
                         'page 0x0B is now reached by a resolvable site, so '
                         'the write-up\'s calibrated negative no longer holds')
        self.assertIn('0 resolve to a full XDATA address', report)
        self.assertIn('no P2 write in the window', report)
        self.assertIn('reaches page 0x0B by this method nowhere', report)

    def test_the_out_of_scope_host_handler_is_reported_as_not_found(self):
        self.assertIn('0xA2', self.TEXT)
        self.assertIn('not found', self.TEXT)


class TheTableIsReproducible(unittest.TestCase):
    """The committed CSV is what the write-up's commands produce.

    The one case that re-runs a tool, and it is here rather than in the cases
    above precisely because it compares against a *file*. Every other case
    reads the image, so none of them can pass by agreeing with a stale
    transcription; this one can, and that is why it is scoped to the table and
    to nothing else.
    """

    def test_the_reproduction_command_reproduces_the_committed_table(self):
        proc = subprocess.run(
            [sys.executable, str(TRACE), str(FIRMWARE), '0x0741',
             '--csv', '--terminator-column'],
            capture_output=True, text=True, check=True)
        self.assertEqual(proc.stdout, SITES_CSV.read_text())


if __name__ == '__main__':
    unittest.main()