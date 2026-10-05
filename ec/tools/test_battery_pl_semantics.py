#!/usr/bin/env python3
"""Unit checks for the battery PL default block and the zero semantics.

`docs/findings/battery-pl-default-and-zero-semantics.md` answers issue #1228
section 1 -- name the battery PL default bytes -- and reads the EC side of the
zero the vendor writes on battery. `docs/hardware-tests/battery-pl-limit-effect.md`
is the run that would settle what a *non-zero* limit does; it has not been run.
This file pins the facts both documents stand on, so that a later edit to the
firmware, to `ECSpec.cs` or to the annotations cannot quietly change what they
claim.

**Every case here reads a committed file. None of them is a behaviour.** No
register was read, written or read back, and no byte was watched move on
hardware. The suite asserts claims, never counts: a census of the tree's own
size is a value every merge has to edit, which is what `CLAUDE.md`'s no-totals
rule is about. It asserts that `ECSpec.cs` still defines the battery group at
1959 and still defines no `ADDR_TURBO_PL*`, that the disassembly the write-up
quotes still carries the presence-test guards it quotes, and that the
host-window census still says what the write-up says it says -- each of which
stays true as the tree grows, and each of which fails loudly if the underlying
fact changes.

The disassembly cases read `ec/decompiled/bank0/*.asm` rather than the firmware,
because those files are generated from the firmware and the write-up quotes
them as the authority. That indirection is the point: a re-export that changed
those bytes would have to change the committed `.asm` first.

The suite is **not** wired into `.github/scripts/agent-gates.sh`: that file
lives under `.github/`, which this branch's push token cannot write, so the
registration is a human's change. Until it is made, the suite is run by hand
and nothing here implies CI runs it.
"""
import csv
import io
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

ECSPEC = ROOT / 'windows' / 'decompiled' / 'v3.1.6.0' / 'ECSpec.cs'
FINDING = ROOT / 'docs' / 'findings' / 'battery-pl-default-and-zero-semantics.md'
PROCEDURE = ROOT / 'docs' / 'hardware-tests' / 'battery-pl-limit-effect.md'
FAN0751 = ROOT / 'ec' / 'annotations' / 'manual-fan-ctrl-0751.md'
CENSUS = (ROOT / 'evidence' / 'ec-watch'
          / '2026-09-24-host-window-page-census.txt')
FIRMWARE = ROOT / 'ec' / 'firmware' / 'GMxMGxx_11.800'
CAPTURE_TOOL = ROOT / 'ec' / 'tools' / 'ec_timer_capture.py'
OVERRIDES = ROOT / 'ec' / 'decompiled' / 'bank0' / '96AD.asm'
LEVELS = ROOT / 'ec' / 'decompiled' / 'bank0' / '9D9B.asm'

# The three PL registers the write-up is about, and the register that decides
# which of the override sites run at all. Named rather than ranged so that a
# site list drifting does not silently keep passing.
PL1, PL2, PL4, AP_OEM = 0x0783, 0x0784, 0x0785, 0x0741

# How the generated disassembly spells a `mov DPTR` operand: `#0x741`, three
# digits, no padding. Both routine checks key on this one spelling, because a
# routine that stopped reading AP_OEM is a change in the disassembly and not a
# change in how this suite searches for it.
AP_OEM_OPERAND = f'#0x{AP_OEM:x}'

# The EC's own page of level-block destinations, which the write-up says the
# host cannot read. Its page base is what makes that true. `0x0867` is adjacent
# rather than PL-fed -- it is written from `0x0872`/`0x087A`/`0x088A` -- and is
# here because the write-up names it as part of the same dark block.
LEVEL_PAGE = 0x0800
DARK_DESTINATIONS = (0x08C0, 0x08C1, 0x08C3, 0x08C4, 0x08C5, 0x08C6,
                     0x0866, 0x0867)

# Wide enough to reach the store past the test in either form: the `subb` site
# at 0x96B4 is eight instruction lines to its `movx @DPTR, A`, the `jz` site at
# 0x9DC8 six. A window short of the store would pass on a branch that jumped
# somewhere harmless, which is the misreading these cases exist to catch.
WINDOW = 8


def read(path):
    return path.read_text(encoding='utf-8')


def instruction(path, addr):
    """The one disassembly line at `addr`, or None if the file has none.

    Addressed by value rather than by line number so that regenerating the
    `.asm` -- which this repository does whenever the firmware is re-anchored
    -- cannot turn the case into a failure about a line that merely moved.
    """
    for line in read(path).splitlines():
        if line[:4].lower() == format(addr, '04x'):
            return line
    return None


def asm_window(path, addr, count):
    """`count` instruction lines from `addr`, or [] if `addr` is not there."""
    lines = read(path).splitlines()
    for i, line in enumerate(lines):
        if line[:4].lower() == format(addr, '04x'):
            return lines[i:i + count]
    return []


def ecspec_constants():
    """Every `public const ushort NAME = value;` in ECSpec.cs, as a dict."""
    body = read(ECSPEC)
    return dict(re.findall(r'public const ushort (\w+) = (\d+);', body))


def pl_read_sites():
    """Every direct read site of the PL registers, from the tool itself.

    Run against the committed firmware rather than transcribed, because the
    write-up's claim is about *every* site that method finds and a list typed
    into a test would quietly stop covering a site a later re-export added.
    Deriving it here means a new site fails the presence-test case below
    rather than passing unseen.
    """
    proc = subprocess.run(
        [sys.executable, str(HERE / 'trace_xdata_refs.py'), str(FIRMWARE),
         '0x0783', '0x0784', '0x0785', '--csv'],
        capture_output=True, text=True, check=True)
    rows = csv.DictReader(io.StringIO(proc.stdout))
    return [r for r in rows if r['access'].startswith('read')]


class BatteryDefaultBlockIsNamed(unittest.TestCase):
    """The `0x07A7`-`0x07AA` group, and the fourth group that is not there."""

    def test_the_battery_group_is_the_last_of_the_three(self):
        # 1959 is 0x07A7, so the group the write-up calls the battery block is
        # the third of the three ECSpec defines. Asserted as the arithmetic
        # rather than as the hex literal, because the write-up's whole claim is
        # that this identity holds.
        constants = ecspec_constants()
        self.assertEqual(constants['ADDR_BATTERYSAVER_PL1_DEFAULT_VALUE'], '1959')
        self.assertEqual(int(constants['ADDR_BATTERYSAVER_PL1_DEFAULT_VALUE']),
                         0x07A7)
        self.assertEqual(constants['ADDR_BATTERYSAVER_PL4_DEFAULT_VALUE'], '1961')

    def test_the_three_groups_are_contiguous_and_ordered(self):
        # The write-up leans on there being exactly three groups and on their
        # order -- the last is the battery one. A fourth inserted after
        # BATTERYSAVER would make "the last block" a different sentence.
        constants = ecspec_constants()
        starts = sorted(int(v) for n, v in constants.items()
                        if n.endswith('_PL1_DEFAULT_VALUE'))
        self.assertEqual(starts, [1840, 1844, 1959])
        for name in ('ADDR_GAMING', 'ADDR_OFFICE', 'ADDR_BATTERYSAVER'):
            self.assertIn(f'{name}_PL1_DEFAULT_VALUE', constants)

    def test_no_turbo_pl_default_group_exists(self):
        # The negative the write-up rests on, phrased so it holds as names are
        # added: no constant carries a TURBO name AND a PL default suffix.
        # "Turbo" as a bare TCC byte is fine and is not what this rejects.
        turbo = [n for n in ecspec_constants()
                 if 'TURBO' in n and 'PL' in n and 'DEFAULT_VALUE' in n]
        self.assertEqual(turbo, [])

    def test_the_only_turbo_constant_is_a_tcc_byte(self):
        constants = ecspec_constants()
        turbo = sorted(n for n in constants if 'TURBO' in n)
        self.assertEqual(turbo, ['ADDR_TURBO_TCC_OFFSET_DEFAULT_VALUE'])


class ZeroIsAPresenceTest(unittest.TestCase):
    """The idiom: skip the store when the PL reads zero."""

    def test_the_subb_form_tests_against_zero_and_branches_over_the_store(self):
        # The `subb`-against-zero form the write-up quotes at 0x96B4. The
        # branch must land between the test and the store, or a zero would be
        # stored rather than skipped.
        window = asm_window(OVERRIDES, 0x96B4, WINDOW)
        joined = ' '.join(window)
        self.assertIn('subb     A, #0x0', joined)
        self.assertIn('jc', joined)
        self.assertLess(joined.index('subb'), joined.index('jc'))
        self.assertLess(joined.index('jc'), joined.index('movx     @DPTR, A'))

    def test_the_jz_form_tests_against_zero_and_branches_over_the_store(self):
        # The `jz` form at 0x9DC8, in the other routine. Same shape.
        window = asm_window(LEVELS, 0x9DC8, WINDOW)
        joined = ' '.join(window)
        self.assertIn('jz', joined)
        self.assertLess(joined.index('jz'), joined.index('movx     @DPTR, A'))

    def test_every_pl_read_the_write_up_quotes_carries_the_test(self):
        # The whole claim is "every direct read site found by this method is a
        # presence test", so the case runs over every site the tool reports
        # rather than over a transcribed list -- a site added by a later
        # re-export has to fail here, not pass unseen. The window string the
        # tool prints is the decoded form; the presence test is the `jz`/`jc`
        # in it.
        sites = pl_read_sites()
        self.assertTrue(sites, 'the tool reported no PL read sites at all')
        for site in sites:
            with self.subTest(site=site['runtime']):
                self.assertRegex(site['window'], r'j(z|c) ')

    def test_the_write_up_quotes_sites_that_are_all_still_reads(self):
        # The addresses the write-up and the 0751 correction both name, checked
        # against the tool's own output, so a site that stopped being a read
        # (or stopped existing) fails on the fact rather than on the prose
        # having drifted from it silently.
        quoted = (0x96B4, 0x96C2, 0x96D0, 0x97D8, 0x97E3, 0x97EE,
                  0x98C4, 0x98CF, 0x98DA, 0x9DC8, 0x9EB1, 0x9FC3)
        found = {int(s['runtime'], 16) for s in pl_read_sites()}
        for addr in quoted:
            with self.subTest(site=f'{addr:04x}'):
                self.assertIn(addr, found)

    def test_the_two_quoted_shapes_are_read_from_the_generated_disassembly(self):
        # The write-up's two code blocks are quotes, so the suites that check
        # them read the generated `.asm` rather than a copy in a fixture. Both
        # quoted addresses have to be in the file the write-up attributes them
        # to, or the quote has lost its source.
        for path, addr in ((OVERRIDES, 0x96B4), (LEVELS, 0x9DC8)):
            with self.subTest(site=f'{path.name}@{addr:04x}'):
                self.assertIsNotNone(instruction(path, addr))
                self.assertIn('generated by', read(path).splitlines()[1])

    def test_the_level_block_routine_never_reads_ap_oem(self):
        # The correction in the write-up's second half: the presence-test
        # idiom is not, by itself, gated on AP_OEM. If this routine ever grows
        # a 0x0741 read, the write-up's "unguarded" sentence is wrong and this
        # fails on the fact rather than on the prose.
        self.assertNotIn(AP_OEM_OPERAND, read(LEVELS))

    def test_the_override_routine_does_gate_on_ap_oem(self):
        # ...and the other routine does, at each of its guarded blocks. The
        # write-up's contrast between the two routines is only meaningful with
        # both halves of it.
        self.assertIn(AP_OEM_OPERAND, read(OVERRIDES))


class TheDestinationPageIsDark(unittest.TestCase):
    """Why the procedure grades on behaviour and not on a byte."""

    def test_the_census_says_the_level_page_holds_nothing(self):
        # The write-up's claim that the copy landing cannot be watched is a
        # claim about this census row. Read the number out of it rather than
        # restating it, so a re-census that changed the answer fails here.
        rows = dict((line.split()[0], line.split()[1])
                    for line in read(CENSUS).splitlines()
                    if line.startswith('0x'))
        self.assertIn(format(LEVEL_PAGE, '#06x'), rows)
        non_ff, total = rows[format(LEVEL_PAGE, '#06x')].split('/')
        self.assertEqual(non_ff, '0')
        self.assertEqual(int(total), 256)

    def test_every_destination_the_write_up_names_is_on_that_page(self):
        # The blindness is not a property of one address; it is a property of
        # the page all of them share. If one moved off the page the write-up's
        # "none of them is host-visible" would need narrowing.
        for addr in DARK_DESTINATIONS:
            with self.subTest(destination=f'{addr:#06x}'):
                self.assertEqual(addr & 0xFF00, LEVEL_PAGE)

    def test_the_capture_tool_refuses_the_page(self):
        # The refusal is what keeps a run from watching `0xFF` and calling it
        # "the EC left it alone". Asserted against the tool's own window
        # constant, so widening HOST_WINDOW without re-deriving the census
        # fails here.
        source = read(CAPTURE_TOOL)
        window = re.search(r'HOST_WINDOW = \((.*?)\)', source, re.S)
        self.assertIsNotNone(window)
        for lo, hi in re.findall(r'0x([0-9A-Fa-f]{4}), 0x([0-9A-Fa-f]{4})',
                                 window.group(1)):
            self.assertFalse(int(lo, 16) <= 0x08C0 <= int(hi, 16))


class TheDocumentsSayWhatTheSuiteChecks(unittest.TestCase):
    """The write-up and the procedure still name what this suite pins."""

    def test_the_finding_carries_a_title(self):
        # `gen_findings_index.py --check` requires one, and the runner reads it.
        self.assertTrue(read(FINDING).startswith('# '))

    def test_the_finding_states_the_battery_block(self):
        body = read(FINDING)
        self.assertIn('ADDR_BATTERYSAVER', body)
        self.assertIn('0x07A7', body)
        self.assertIn('1959', body)

    def test_the_finding_states_the_no_turbo_group_negative(self):
        # A negative asserted without its method is the failure `CLAUDE.md`
        # names, so the write-up has to carry the method with the claim.
        self.assertIn('ADDR_TURBO_PL*_DEFAULT_VALUE', read(FINDING))

    def test_the_finding_and_the_procedure_both_cite_the_census(self):
        census = CENSUS.name
        for doc in (FINDING, PROCEDURE):
            with self.subTest(document=doc.name):
                self.assertIn(census, read(doc))

    def test_the_procedure_names_the_addresses_it_watches(self):
        # A procedure that watches addresses other than the ones it writes
        # would be a different procedure. Every address in the write-up's
        # argument has to be in the capture command.
        procedure = read(PROCEDURE)
        captures = re.findall(r'--addrs ([0-9a-fx,]+)', procedure)
        self.assertTrue(captures, 'no capture command in the procedure')
        for addr in (PL1, PL2, PL4, AP_OEM, 0x075B, 0x075C, 0x043E, 0x044F,
                     0x07A7, 0x07AA):
            with self.subTest(addr=f'{addr:#06x}'):
                self.assertIn(f'{addr:#06x}', procedure)
        self.assertEqual(len(set(captures)), 1,
                         'the arms watch different address sets')

    def test_the_procedure_declares_itself_unrun(self):
        # The claim the whole repository's calibration rule turns on. A
        # procedure that implied a live run would be a false statement in the
        # tree, not a stale one.
        procedure = read(PROCEDURE)
        self.assertIn('**Status: not run.**', procedure)

    def test_the_annotation_section_corrected_is_still_there(self):
        # The write-up corrects the site list in place in
        # `manual-fan-ctrl-0751.md` section 5. If that section were renumbered
        # or removed, the correction would be pointing at nothing.
        self.assertIn('## 5. The per-mode default blocks', read(FAN0751))

    def test_the_finding_points_at_the_procedure_and_the_other_way_round(self):
        self.assertIn('battery-pl-limit-effect.md', read(FINDING))
        self.assertIn('battery-pl-default-and-zero-semantics.md',
                      read(PROCEDURE))


if __name__ == '__main__':
    unittest.main()