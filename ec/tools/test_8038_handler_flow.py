#!/usr/bin/env python3
"""Unit checks for the bank0 0x8038 handler control-flow walk (issue #60).

`ec/annotations/bank0-8038-handler-flow.md` walks the eight handlers the
`0x8038` inline switch table dispatches to, the shared epilogue at 0x821F and
the default at 0x8274, following branches rather than decoding each window
linearly the way `bank-call-audit.md` §9 had to. This file pins the byte facts
that walk stands on.

Most of the assertions are on **raw bytes** rather than on a disassembler's
rendering of them, and that is a choice rather than a shortcut. The document
quotes `r2 -a 8051`; this suite compares what the image actually holds, so a
change to either tool's spelling cannot make a claim pass or fail. It also
sidesteps a real disagreement the document records: at `bank1,0xDAF3` the two
bytes `a8 01` are `mov r0, r1` to r2, `mov r0,0x01` to `disasm8051`, and
`mov r0,@r0` on the base instruction set. Pinning the byte is the only way to
assert anything there that is not a choice between three readings.

Two other things it deliberately does not do.

It does not re-run `walk_branch_arms.py`. That would assert the tool against
itself, and a regenerated `bank0-8038-handler-arms.csv` would then be free to
disagree with the image. Where this suite reads that CSV at all, it compares it
to the image recomputed here, so a regeneration that changed either fails
loudly instead of passing on a stale pair.

And it writes no `test_*.py:<line>` citation, and names no other test file by
line. `census_test_line_pins.py` counts those spellings in markdown across the
tree and its reconciled population figures move when one is added, which is a
shared-file diff this change has no reason to cause. Files are named by path
and tests by name instead.
"""
import csv
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import verify_gap_text as G

ANNOTATIONS = HERE.parent / 'annotations'
DECOMPILED = HERE.parent / 'decompiled'
ARMS = ANNOTATIONS / 'bank0-8038-handler-arms.csv'
CENSUS = ANNOTATIONS / 'xdata-registers.csv'
CALL_TARGETS = ANNOTATIONS / 'bank-call-targets.csv'
REL_CENSUS = ANNOTATIONS / 'bank-relative-branch-targets.csv'
DISPATCH = ANNOTATIONS / 'bank0-8038-dispatch-table.csv'
FLOW_DOC = ANNOTATIONS / 'bank0-8038-handler-flow.md'
AUDIT_DOC = ANNOTATIONS / 'bank-call-audit.md'

# Address == image offset for every program, which is what make_bank_image.py
# arranges and why nothing here does address arithmetic of its own. Loaded once
# rather than per test, for the reason test_bank1_e582_framing.py gives.
IMAGES = G.load_images()
BANK0 = IMAGES['bank0']
BANK1 = IMAGES['bank1']

JB = 0x20          # jb  acc.7, rel8
JNB = 0x30         # jnb acc.7, rel8
LCALL = 0x12
LJMP = 0x02
SJMP = 0x80
RET = 0x22
ORL_A_IMM = 0x44   # `orl a,#imm8`
JZ = 0x60


def be16(image, addr):
    return (image[addr] << 8) | image[addr + 1]


def hexat(image, addr, length):
    """The bytes at `addr` as the hex string a transcript would quote, so a
    failure prints something a reader can look up rather than a repr."""
    return image[addr:addr + length].hex()


def rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def census():
    return {int(r['addr'], 16): r for r in rows(CENSUS) if r['addr']}


def annotations():
    return {(r['scope'], r['addr']): r
            for r in rows(ANNOTATIONS / 'ghidra-functions.csv')}


def call_targets():
    # Keyed on (region, runtime) because the two banks are numbered in the
    # same address space -- `0xAA28` names a row in each -- and on the
    # integer rather than the string because the `runtime` column is spelled
    # `0x0AA28`. Both are quirks of how the census is written out, not
    # something a caller should have to know.
    return {(r['region'], int(r['runtime'], 16)): r
            for r in rows(CALL_TARGETS)}


# The census rows whose recorded `02` is an operand byte rather than an
# `ljmp` opcode -- the phantom row of §8's table. The value is the real
# opcode in front of the site together with that instruction's length,
# which is what says where the opcode sits: a `jb`/`jnb` spends two bytes on
# operands, so its opcode is at `site - 2` where the two-byte opcodes are at
# `site - 1`. All twenty target 0x8000-0x8038, which is the range §8's
# twenty-two is counted over; 0xAA28 and 0xAA67 are the three-byte form.
PHANTOM_SITES = {
    0x89D1: (2, 0x40), 0x8C79: (2, 0x40), 0x90E8: (2, 0xA2),
    0x9141: (2, 0xA2), 0x914F: (2, 0x60), 0x9AE2: (2, 0x50),
    0x9DF8: (2, 0x50), 0x9EE1: (2, 0x50), 0x9FE8: (2, 0x50),
    0xAA28: (3, 0x30), 0xAA67: (3, 0x20), 0xAA77: (3, 0x30),
    0xABFD: (2, 0x10), 0xAC14: (2, 0x70), 0xC68C: (2, 0x70),
    0xC6C9: (2, 0x70), 0xC756: (2, 0x10), 0xC969: (2, 0x60),
    0xD779: (2, 0x71), 0xD850: (2, 0xFC),
}


# The eight cases, and the columns of bank-call-audit.md §9's per-case table
# that this walk re-derives. `case` and `target` are what the dispatch table
# says; the rest is §9's row, restated here so a change to either the document
# or the table has to be made in two places rather than one.
CASES = (
    # case, target, gate, slot,   pair,   flag, exit acc, first helper, gate helper
    (0x00, 0x8054, 0x1904, 0x08D0, 0x0600, 0x01, 0x81, 0xB9DF, 0xBE7E),
    (0x01, 0x8094, 0x1906, 0x08D2, 0x0602, 0x02, 0x82, 0xBDAE, 0xBB9A),
    (0x02, 0x80D7, 0x1909, 0x08D4, 0x0604, 0x04, 0x83, 0xBDBA, 0xBE88),
    (0x03, 0x811A, 0x190C, 0x08D6, 0x0606, 0x08, 0x84, 0xBDC6, 0xBE92),
    (0x04, 0x815D, 0x1904, 0x08D8, 0x0608, 0x10, 0x85, 0xB9DF, 0xBE7E),
    (0x05, 0x819D, 0x1906, 0x08DA, 0x060A, 0x20, 0x86, 0xBDAE, 0xBB9A),
    (0x06, 0x81DF, 0x1909, 0x08DC, 0x060C, 0x40, 0x87, 0xBDBA, 0xBE88),
    (0x07, 0x8231, 0x190C, 0x08DE, 0x060E, 0x80, 0x80, 0xBDC6, 0xBE92),
)

# Cases 0x00-0x06 branch *into* the body with `jb`, so their fall-through is
# the one-instruction jump to the default; case 0x07 uses `jnb` and the same
# edge is the *taken* one. The walk's CSV `arm` column therefore says `taken`
# for what is semantically the clear arm on 0x07, and this is what that
# inversion is checked against.
BRANCH_OPCODE = {case: (JNB if case == 0x07 else JB) for case, *_ in CASES}

# The instruction that leaves each bit-7-set arm, and what it is. This is the
# walk's main result over §9's linear decode: cases 0x00-0x04 leave with a
# 3-byte `ljmp`, case 0x05 with a 2-byte PC-relative `sjmp`, case 0x06 with no
# transfer at all, and case 0x07 by falling through `0xBCB1` into the default.
# A `None` opcode means the case leaves by falling through, and `follows` is
# the address that comes next in the byte order -- which for 0x06 and 0x07 is
# the point, since nothing in the image names either edge.
# `mov a,#0x81 + case` first, then whatever leaves. The two are adjacent in
# five cases and not in the other three, which is why they are both here
# rather than one being derived from the other.
EXIT = {
    # case: (mov a, exit insn, exit opcode, its target, what follows it)
    0x00: (0x808F, 0x8091, LJMP, 0x821F, 0x8094),
    0x01: (0x80D2, 0x80D4, LJMP, 0x821F, 0x80D7),
    0x02: (0x8115, 0x8117, LJMP, 0x821F, 0x811A),
    0x03: (0x8158, 0x815A, LJMP, 0x821F, 0x815D),
    0x04: (0x8198, 0x819A, LJMP, 0x821F, 0x819D),
    0x05: (0x81DB, 0x81DD, SJMP, 0x821F, 0x81E0),
    0x06: (0x821D, None, None, 0x821F, 0x821F),
    0x07: (0x826C, 0x8271, LCALL, 0xBCB1, 0x8274),
}

# The source word each case's `r6:r7` is loaded from, which is what the
# document's §6.2 prints. Four distinct words across eight cases, paired the
# way the gate bytes are -- and case 0x00/0x04's is the one that is NOT
# gate+1, which is the row a pattern-match would get wrong.
SOURCE_WORD = {0x00: 0x1918, 0x01: 0x1907, 0x02: 0x190A, 0x03: 0x190D,
               0x04: 0x1918, 0x05: 0x1907, 0x06: 0x190A, 0x07: 0x190D}

# The `lcall 0xB965` site in each case, and the accumulator low byte it is
# called with -- eight sites, one per case, in case order.
B965_CALLS = {0x8074: 0x0601, 0x80B7: 0x0603, 0x80FA: 0x0605,
              0x813D: 0x0607, 0x817D: 0x0609, 0x81C0: 0x060B,
              0x8202: 0x060D, 0x8251: 0x060F}

# The four gate helpers: each writes 0x9F to one gate and leaves DPTR on the
# next in the ring. The value, not the address, is what §6.3 rests on.
GATE_RING = ((0xBE7E, 0x1904, 0x1906),
             (0xBB9A, 0x1906, 0x1909),
             (0xBE88, 0x1909, 0x190C),
             (0xBE92, 0x190C, 0x1904))


def target_of(case):
    return dict((c, t) for c, t, *_ in CASES)[case]


def arm_row(case):
    """The bit-7-set arm's CSV row, with `window` lower-cased.

    Which row that is depends on the branch spelling: for 0x00-0x06 it is the
    `taken` row, for 0x07 the `fall-through` one, because `jnb` sends the
    clear case the other way. The lower-casing is because the writer renders
    an instruction's own address in upper-case hex and its operands in lower,
    so `0x821F lcall 0xbb08` and `ljmp 0x821f` are the two spellings of one
    reach and neither is the right one to assert on unnormalised."""
    want = 'fall-through' if case == 0x07 else 'taken'
    target = target_of(case)
    for r in rows(ARMS):
        if (r['kind'] == 'arm' and r['arm'] == want
                and int(r['site_runtime'], 16) == target):
            found = dict(r)
            found['window'] = found['window'].lower()
            return found
    raise AssertionError("no %s arm row for case 0x%02X" % (want, case))


class TheDispatchSite(unittest.TestCase):
    """The selector read and the computed dispatch the eight handlers are
    reached through. Neither is visible to any byte scan, which is the whole
    reason the document's §8 ends where it does."""

    def test_the_selector_is_08e0_and_the_call_is_7151(self):
        # 0x8030's `ret` is one byte, so 0x8031 is a separate entry rather
        # than a fall-through: load 0x08E0, read it, call the reader that pops
        # the return address into DPTR and dispatches through the table the
        # call leaves behind.
        self.assertEqual(hexat(BANK0, 0x8030, 8),
                         "22"            # ret
                         "9008e0"        # mov dptr,#0x08E0
                         "e0"            # movx a,@dptr
                         "127151")       # lcall 0x7151

    def test_the_dispatch_is_a_computed_jump_with_no_displacement(self):
        # `e4 73` is `clr a ; jmp @a+dptr` and the `73` is the whole
        # instruction. A branch target neither tool can produce is the fact
        # §2 and §8 both rest on: no edge out of 0x716B is resolvable from
        # its own bytes.
        self.assertEqual(hexat(BANK0, 0x716A, 2), "e473")

    def test_and_the_table_follows_that_call(self):
        # Eight three-byte entries, a `00 00` terminator and a `0x8274`
        # default, immediately after the `lcall 0x7151` at 0x8035.
        self.assertEqual(hexat(BANK0, 0x8038, 28),
                         "805400" "809401" "80d702" "811a03"
                         "815d04" "819d05" "81df06" "823107"
                         "0000" "8274")


class TheHandlerSkeleton(unittest.TestCase):
    """Every case opens the same three instructions and splits on bit 7 of the
    byte it just read. That is the one thing §9's linear decode and this walk
    agree on, so it is pinned once and read per case below."""

    def test_each_case_loads_its_gate_reads_it_and_tests_bit_7(self):
        for case, target, gate, _s, _p, _f, _a, _h, _h2 in CASES:
            with self.subTest(case="0x%02X" % case):
                self.assertEqual(hexat(BANK0, target, 5),
                                 "90%04x" % gate + "e0" + "%02x" % BRANCH_OPCODE[case])
                # `jb`/`jnb acc.7` encodes the bit as 0xE0 + 7, not 0x07.
                self.assertEqual(BANK0[target + 5], 0xE7)

    def test_the_branch_displacement_reaches_the_body_or_the_default(self):
        for case, target, *_ in CASES:
            with self.subTest(case="0x%02X" % case):
                # The branch is at target+4 and is three bytes, so the
                # fall-through is target+7 and the taken arm is seven further.
                # For 0x00-0x06 that is the body; for 0x07 the displacement
                # carries it all the way to the default instead.
                want = 0x8274 if case == 0x07 else target + 10
                self.assertEqual(target + 7 + BANK0[target + 6], want)

    def test_the_clear_arm_is_a_three_byte_ljmp_to_the_default(self):
        # Seven of eight, and §3 of the document's claim that a linear window
        # decode could not have shown it: one instruction, and the only thing
        # between a gate byte and the default.
        for case, target, *_ in CASES:
            if case == 0x07:
                continue
            with self.subTest(case="0x%02X" % case):
                self.assertEqual(hexat(BANK0, target + 7, 3), "028274")


class ThePerCaseWalk(unittest.TestCase):
    """The walk's per-case result: the block each arm reaches, the `lcall`s
    inside it, and the instruction that leaves the case."""

    def test_each_case_has_exactly_one_lcall_0xb965(self):
        for case, *_ in CASES:
            with self.subTest(case="0x%02X" % case):
                self.assertEqual(arm_row(case)['window'].count("lcall 0xb965"), 1)

    def test_the_b965_call_sites_and_the_pair_they_are_given(self):
        found = set()
        for case, target, *_ in CASES:
            hits = [pc for pc in range(target + 7, target + 0x60)
                    if hexat(BANK0, pc, 3) == "12b965"]
            self.assertEqual(len(hits), 1, "case 0x%02X" % case)
            found.add(hits[0])
        self.assertEqual(found, set(B965_CALLS))
        # Three bytes earlier is the `mov dptr` naming the pair's low byte,
        # so the average of §5.1 is over the pair and not one byte of it.
        for site, pair in B965_CALLS.items():
            with self.subTest(site="0x%04X" % site):
                self.assertEqual(BANK0[site - 3], 0x90)
                self.assertEqual(be16(BANK0, site - 2), pair)

    def test_the_first_helper_names_the_source_word(self):
        for case, _t, _g, _s, _p, _f, _a, helper, _h2 in CASES:
            with self.subTest(case="0x%02X" % case):
                self.assertEqual(BANK0[helper], 0x90)
                self.assertEqual(be16(BANK0, helper + 1), SOURCE_WORD[case])

    def test_each_case_stores_r6_then_r7_into_its_slot(self):
        # `mov dptr,#<slot> ; mov a,r6 ; movx @dptr,a ; inc dptr ;
        #  mov a,r7 ; movx @dptr,a` -- r6 low, r7 high, and the increment is
        # what puts r7 at slot+1.
        for case, _t, _g, slot, _p, _f, _a, _h, _h2 in CASES:
            with self.subTest(case="0x%02X" % case):
                want = "90%04x" % slot + "ee" "f0" "a3" "ef" "f0"
                hits = [off for off in range(0x8000, 0x8400)
                        if hexat(BANK0, off, 8) == want]
                self.assertEqual(len(hits), 1, "case 0x%02X" % case)
                self.assertEqual(be16(BANK0, hits[0] + 1), slot)

    def test_each_case_ors_its_own_flag_bit_into_0610(self):
        for case, _t, _g, _s, _p, flag, _a, _h, _h2 in CASES:
            with self.subTest(case="0x%02X" % case):
                want = "900610" "e0" "44" + "%02x" % flag
                hits = [off for off in range(0x8000, 0x8300)
                        if hexat(BANK0, off, 6) == want]
                self.assertEqual(len(hits), 1, "case 0x%02X" % case)
                self.assertEqual(BANK0[hits[0] + 4], ORL_A_IMM)

    def test_each_case_calls_its_own_gate_helper(self):
        for case, target, _g, _s, _p, _f, _a, _h, gate_helper in CASES:
            with self.subTest(case="0x%02X" % case):
                self.assertEqual(arm_row(case)['window'].count("lcall 0x%x"
                                                               % gate_helper), 1)
                exit_pc = EXIT[case][1]
                if exit_pc is not None:
                    self.assertLess(exit_pc - target, 0x60)

    def test_the_exit_accumulator_is_81_plus_case_except_case_07(self):
        # §9 says `a` holds 0x81 + case. That is right for 0x00-0x06 and wrong
        # for 0x07, whose immediate at 0x826C is 0x80. The correction sits
        # beside §9's table; this is what holds it there.
        for case, _t, _g, _s, _p, _f, acc, _h, _h2 in CASES:
            with self.subTest(case="0x%02X" % case):
                at = EXIT[case][0]
                self.assertEqual(BANK0[at], 0x74)      # `mov a,#imm`
                self.assertEqual(BANK0[at + 1], acc)
        self.assertEqual(0x80 + 0x07, 0x87)
        self.assertNotEqual(0x81 + 0x07,
                            dict((c, a) for c, _t, _g, _s, _p, _f, a, _h, _h2
                                 in CASES)[0x07])

    def test_the_exit_transfer_of_each_case(self):
        for case, _t, _g, _s, _p, _f, _a, _h, _h2 in CASES:
            with self.subTest(case="0x%02X" % case):
                pc, op, target, follows = EXIT[case][1:]
                if pc is None:
                    # Case 0x06 leaves by falling through, and the address
                    # after its last instruction IS the epilogue's first.
                    # `mov a,#0x87` is two bytes and `lcall` is three, so the
                    # arithmetic is the whole claim.
                    self.assertEqual(EXIT[case][0] + 2, follows)
                    self.assertEqual(hexat(BANK0, follows, 3), "12bb08")
                    continue
                self.assertEqual(BANK0[pc], op)
                if op == SJMP:
                    # 2-byte PC-relative. The displacement is the whole reason
                    # this edge is invisible to an absolute-address scan.
                    self.assertEqual(pc + 2 + BANK0[pc + 1], target)
                else:
                    self.assertEqual(be16(BANK0, pc + 1), target)
                if case == 0x07:
                    # `lcall 0xBCB1` and then the next address is the default.
                    self.assertEqual(follows, 0x8274)

    def test_cases_05_and_07_reach_past_their_own_window(self):
        # The specific thing the issue asked the walk to look for. §9's
        # windows are target-to-next-target; a body reaching past one is what
        # would have made its table need revisiting. Two of eight do, and
        # neither changes an attribution.
        for case, (lo, hi) in {0x05: (0x819D, 0x81DF),
                               0x07: (0x8231, 0x8274)}.items():
            with self.subTest(case="0x%02X" % case):
                if case == 0x05:
                    # The `sjmp` target 0x821F is past 0x81DE, and still
                    # inside case 0x06's window, so it is one block further on
                    # rather than off the end of the region.
                    self.assertEqual(EXIT[case][3], 0x821F)
                    self.assertGreater(0x821F, hi - 1)   # past 0x81DE
                    self.assertLess(0x821F, 0x8230)      # inside 0x06's
                else:
                    # Case 0x07's block runs past its window into 0x8274.
                    self.assertEqual(EXIT[case][4], hi)
                    self.assertGreaterEqual(0x8274, hi)

    def test_cases_05_and_07_are_the_two_block_handler_arms(self):
        # §3's per-case arithmetic, asserted per case rather than as a range
        # over all eight -- a range holds nothing when two of the eight are
        # two blocks. Case 0x05's `sjmp` lands in the epilogue and case 0x07's
        # run past its window into the default, so each is two blocks; case
        # 0x06's epilogue is inside its own single block instead, so it
        # reaches 0x821F and still has one.
        expected = {0x00: [26], 0x01: [27], 0x02: [27], 0x03: [27],
                    0x04: [26], 0x05: [27, 9], 0x06: [35], 0x07: [35, 9]}
        # All eight, so a ninth case cannot join them unmeasured.
        self.assertEqual(sorted(expected), sorted(c for c, *_ in CASES))
        for case in sorted(expected):
            with self.subTest(case="0x%02X" % case):
                # One block is no separator and two is one, so the per-block
                # sizes come from splitting on it rather than from a count.
                blocks = arm_row(case)['window'].split(" | ")
                self.assertEqual(
                    [len([i for i in b.split(';') if i.strip()])
                     for b in blocks], expected[case])
                self.assertEqual(int(arm_row(case)['insns']),
                                 sum(expected[case]))
        self.assertIn("0x821f lcall 0xbb08", arm_row(0x05)['window'].lower())

    def test_the_relative_census_carries_the_sjmp_case_05_leaves_by(self):
        # §3's claim is that the PC-relative census *does* resolve the edge a
        # linear window read cannot follow, so the row has to be there -- with
        # the framing that says 0x821F is an instruction start, and the `sjmp`
        # as its opcode rather than a byte inside a longer instruction.
        sites = [r for r in rows(REL_CENSUS)
                 if r['region'] == 'bank0' and int(r['runtime'], 16) == 0x81DD]
        self.assertEqual(len(sites), 1)
        row = sites[0]
        self.assertEqual(hexat(BANK0, 0x81DD, 2), "8040")
        self.assertEqual(row['opcode'], 'sjmp')
        self.assertEqual(int(row['target'], 16), 0x821F)
        self.assertEqual(row['target_class'], 'entry')
        self.assertEqual((int(row['frame_onto']), int(row['frame_over'])),
                         (21, 3))
        # And the eight cases hold no other `sjmp` between them, which is the
        # other half of §3's sentence.
        others = {r['site_runtime'] for r in rows(ARMS)
                  if r['kind'] == 'arm' and 'sjmp' in r['window'].lower()
                  and r['site_runtime'] != '0x82D8'}
        self.assertEqual(others, {'0x819D'})

    def test_case_06_contains_the_epilogue_in_its_own_block(self):
        window = arm_row(0x06)['window']
        self.assertNotIn(" | ", window)
        self.assertIn("0x821f lcall 0xbb08", window.lower())
        self.assertIn("0x822e ljmp 0x8274", window.lower())

    def test_the_other_six_only_name_the_epilogue_as_a_jump_target(self):
        # They leave with `ljmp 0x821f`, so the address is in their window --
        # but not the epilogue's first instruction, which is what would mean
        # the walk had stepped into it.
        for case in (0x00, 0x01, 0x02, 0x03, 0x04):
            with self.subTest(case="0x%02X" % case):
                window = arm_row(case)['window']
                self.assertIn("ljmp 0x821f", window.lower())
                self.assertNotIn("0x821f lcall 0xbb08", window.lower())


class TheWordSlot(unittest.TestCase):
    """What the 0x08D0-0x08DE slots hold, and the 16-bit word `r6:r7` is
    loaded with before they get it."""

    def test_r6_is_the_low_byte_of_the_word_it_loads(self):
        # 0xB9DF's tail loads r6 from 0x0A56 and r7 from 0x0A57, and the
        # staging routines put the source word's low byte in 0x0A56. r6 is
        # the low half of the pair: 0xB965's `clr c ; rrc a` pair shifts it
        # first and lets r7 consume its carry. So the slot store of §6.2 is a
        # straight copy of the value, laid down low byte at the lower
        # address.
        self.assertEqual(hexat(BANK0, 0xB9DF, 21),
                         "901918"     # mov dptr,#0x1918
                         "e0"         # movx a,@dptr
                         "900a57"     # mov dptr,#0x0A57
                         "f0"         # movx @dptr,a
                         "901919"     # mov dptr,#0x1919
                         "e0"         # movx a,@dptr
                         "900a56"     # mov dptr,#0x0A56
                         "f0"         # movx @dptr,a
                         "e0"         # movx a,@dptr
                         "fe"         # mov r6,a
                         "a3"         # inc dptr
                         "e0"         # movx a,@dptr
                         "ff")        # mov r7,a

    def test_the_three_entry_points_are_three_bytes_into_one_loader(self):
        # 0xB9EA and 0xB9EE are not function boundaries, which is why §6.1 of
        # the document calls them entries and not routines.
        self.assertEqual(hexat(BANK0, 0xB9DF, 3), "901918")
        self.assertEqual(BANK0[0xB9EA], 0xE0)      # movx a,@dptr
        self.assertEqual(BANK0[0xB9EE], 0xF0)      # movx @dptr,a
        for entry in (0xB9DF, 0xB9EA, 0xB9EE):
            with self.subTest(entry="0x%04X" % entry):
                self.assertEqual(BANK0[0xB9F4], RET)   # one shared `ret`

    def test_each_staging_routine_leaves_dptr_on_the_second_byte(self):
        # 0xBDAE stores 0x1907 at 0x0A57 and leaves DPTR on 0x1908; that is
        # what makes the `lcall 0xB9EA` after it read the other half. The two
        # names are address order only -- 0x1907 is the word's high byte and
        # 0x1908 its low one, so DPTR is left on the low byte.
        for entry, first, second in ((0xBDAE, 0x1907, 0x1908),
                                     (0xBDBA, 0x190A, 0x190B),
                                     (0xBDC6, 0x190D, 0x190E),
                                     (0xB9DF, 0x1918, 0x1919)):
            with self.subTest(entry="0x%04X" % entry):
                self.assertEqual(hexat(BANK0, entry, 11),
                                 "90%04x" % first + "e0" "900a57" "f0"
                                 "90%04x" % second)

    def test_four_source_words_across_eight_cases(self):
        self.assertEqual(len(set(SOURCE_WORD.values())), 4)
        counts = {}
        for word in SOURCE_WORD.values():
            counts[word] = counts.get(word, 0) + 1
        self.assertEqual(sorted(counts.values()), [2, 2, 2, 2])
        # ... and the pairings are the gate pairings.
        by_gate = {}
        for case, _t, gate, *_ in CASES:
            by_gate.setdefault(gate, set()).add(SOURCE_WORD[case])
        self.assertEqual(len(by_gate), 4)
        for gate, words in by_gate.items():
            self.assertEqual(len(words), 1, "gate 0x%04X reads two words" % gate)

    def test_the_byte_pair_is_gate_adjacent_and_the_word_is_not_always(self):
        for case, _t, gate, _s, pair, *_ in CASES:
            with self.subTest(case="0x%02X" % case):
                self.assertEqual(pair, (case * 2) + 0x0600)
                self.assertNotEqual(gate, pair)
                # Six of eight read gate+1; the two that do not are the pair
                # using 0xB9DF, which is the row a pattern-match gets wrong.
                self.assertEqual(SOURCE_WORD[case] == gate + 1,
                                 case not in (0x00, 0x04))

    def test_the_byte_pair_round_trip_through_0a58_0a59(self):
        # Case 0x00's shape: the pair's high byte to 0x0A59, its low byte read
        # by 0xB965, the returned low byte back to the pair, and 0x0A59 to
        # the pair's high byte. Asserted as the six instructions they are,
        # because it is why §5.1 can say the pair is halved in place.
        self.assertEqual(hexat(BANK0, 0x8069, 8), "900600" "e0" "900a59" "f0")
        self.assertEqual(hexat(BANK0, 0x8077, 12),
                         "900601" "f0" "900a59" "e0" "900600" "f0")


class TheSharedHelpers(unittest.TestCase):
    """0xB965 and the 0x1901 family, plus the four gate helpers. The
    document's §5 and §6.3 rest on these and on nothing else."""

    def test_b965_is_a_16_bit_sum_shifted_right_by_one(self):
        # Read the caller's DPTR byte into 0x0A58, add the 16-bit pair
        # 0x0A58/0x0A59 into r6:r7 low byte first, then `clr c ; rrc a` twice
        # -- r6 first, with r7 consuming its carry, so r6 is the low byte of
        # the sum and it is a plain >>1 with the carry out of r7, the top,
        # discarded -- write it back and return the new low byte in `a`.
        self.assertEqual(hexat(BANK0, 0xB965, 30),
                         "e0"                 # movx a,@dptr
                         "900a58" "f0"        # 0x0A58 = the caller's byte
                         "a3" "e0"            # 0x0A59, added into r7
                         "2f" "ff"            # add a,r7 ; mov r7,a
                         "900a58" "e0"        # 0x0A58, added into r6
                         "3e"                 # addc a,r6
                         "c3" "13"            # clr c ; rrc a
                         "fe"                 # mov r6,a
                         "ef" "13" "ff"       # mov a,r7 ; rrc a ; mov r7,a
                         "ee" "f0" "a3" "ef" "f0"    # r6, r7 back to 0x0A58/9
                         "900a58" "e0" "22")  # return 0x0A58 in `a`

    def test_ba3d_clears_and_bb08_sets_bit_0_of_1901(self):
        # Both open with the same `movx @dptr,a`, which is how 0xBA3D comes
        # to perform the handler's 0x0610 write. Asserted as a pair because
        # the pair is the claim: one bit, cleared on the way in and set on the
        # way out.
        self.assertEqual(hexat(BANK0, 0xBA3D, 9), "f0" "901901" "e0" "54fe" "f0" "22")
        self.assertEqual(hexat(BANK0, 0xBB08, 9), "f0" "901901" "e0" "4401" "f0" "22")
        self.assertEqual(0xFE & 0x01, 0x00)

    def test_the_ba3e_entry_skips_only_the_store(self):
        self.assertEqual(BANK0[0xBA3D], 0xF0)
        self.assertEqual(hexat(BANK0, 0xBA3E, 3), "901901")

    def test_bafd_is_bb08_with_the_1900_half_in_front(self):
        # 0x1900 |= 0x03, then the same 0x1901 |= 0x01, one routine. The
        # default's `lcall 0xBAFD` and the epilogue's `lcall 0xBB08` are two
        # entries into one stretch of bytes, and §7 of the document reads the
        # default's writes off that.
        self.assertEqual(hexat(BANK0, 0xBAFD, 20),
                         "f0"                       # movx @dptr,a
                         "901900" "e0" "4402" "f0"  # 0x1900 |= 0x02
                         "e0" "4401" "f0"           # 0x1900 |= 0x01
                         "901901" "e0" "4401" "f0" "22")   # 0x1901 |= 0x01

    def test_the_four_gate_helpers_write_9f_and_rotate(self):
        # 0x9F has bit 7 set, so every arming site in the walk sets the bit
        # the handlers test. That is why the document says the issue's
        # "whoever sets bit 7 decides whether a channel runs" has no answer
        # in that form; pinned so the claim cannot rot into a different one.
        for entry, gate, nxt in GATE_RING:
            with self.subTest(entry="0x%04X" % entry):
                self.assertEqual(hexat(BANK0, entry, 9),
                                 "90%04x" % gate + "749f" "f0" "90%04x" % nxt)
        self.assertEqual(0x9F & 0x80, 0x80)

    def test_the_ring_is_closed(self):
        gates = [g for _e, g, _n in GATE_RING]
        nxt = [n for _e, _g, n in GATE_RING]
        self.assertEqual(nxt, gates[1:] + gates[:1])
        self.assertEqual(sorted(gates), [0x1904, 0x1906, 0x1909, 0x190C])

    def test_every_named_helper_opens_and_terminates_where_the_document_says(self):
        # The entry instruction's bytes and the `ret` that ends the stretch.
        # Every helper named in the document has one of its own: the four gate
        # entries of test_the_four_gate_helpers_write_9f_and_rotate are three
        # `ret`-terminated entries the project exports separately, over a byte
        # stream that runs on, and 0xBB9A ends the 0xBB99-0xBBA3 stretch. The
        # `ret` is not shared with the instruction after it, so it is asserted
        # rather than skipped.
        expected = {
            0xB965: ("e0", 0xB982),
            0xB9DF: ("901918", 0xB9F4),
            0xB9EA: ("e0", 0xB9F4),
            0xB9EE: ("f0", 0xB9F4),
            0xBDAE: ("901907", 0xBDB9),
            0xBDBA: ("90190a", 0xBDC5),
            0xBDC6: ("90190d", 0xBDD1),
            0xBA3D: ("f0", 0xBA45),
            0xBA3E: ("901901", 0xBA45),
            0xBB08: ("f0", 0xBB10),
            0xBCB1: ("9008e1", 0xBCBC),
            0xBAFD: ("f0", 0xBB10),
            0xBB99: ("f0", 0xBBA3),
            0xBE7E: ("901904", 0xBE87),
            0xBE88: ("901909", 0xBE91),
            0xBE92: ("90190c", 0xBE9B),
            0xBB9A: ("901906", 0xBBA3),
        }
        for addr, (first, terminator) in sorted(expected.items()):
            with self.subTest(helper="0x%04X" % addr):
                self.assertEqual(hexat(BANK0, addr, len(first) // 2), first)
                self.assertEqual(BANK0[terminator], RET,
                                 "0x%04X's terminator moved" % addr)

    def test_and_case_07_has_no_committed_listing(self):
        # §4.8 of the document decodes 0x8231 from the image because the
        # committed project exports no function there. Pinned so that stays a
        # checked fact, and so a future rebuild that adds one shows up here.
        self.assertFalse((DECOMPILED / 'bank0' / '8231.asm').exists())
        self.assertTrue((DECOMPILED / 'bank0' / '821F.asm').exists())


class TheEpilogueAndDefault(unittest.TestCase):
    """0x821F and 0x8274, including the arming sequence the document's §7 and
    the issue's lead both rest on."""

    def test_the_epilogue(self):
        self.assertEqual(hexat(BANK0, 0x821F, 18),
                         "12bb08"                   # lcall 0xBB08
                         "9008e1" "7406" "f0"       # 0x08E1 = 6
                         "9008e0" "e0" "04" "f0"    # 0x08E0 += 1
                         "028274")                  # ljmp 0x8274

    def test_the_default_decrements_and_returns_while_nonzero(self):
        # The `jz` displacement resolves to the zero arm, not merely to "some
        # branch": 0x8278 + 2 + 0x04.
        self.assertEqual(hexat(BANK0, 0x8274, 10),
                         "9008e1" "e0" "6004" "e0" "14" "f0" "22")
        self.assertEqual(BANK0[0x8278], JZ)
        self.assertEqual(0x8278 + 2 + BANK0[0x8279], 0x827E)

    def test_the_default_zero_arm_arms_1904_and_resets_the_rest(self):
        # 0x80 to 0x1904, 0x9F to 0x1906 and 0x1909 through 0xBB99, whatever
        # `a` held to 0x190C through 0xBAFD, then 0xBCB1 and `ret`.
        self.assertEqual(hexat(BANK0, 0x827E, 22),
                         "12ba3e"                       # lcall 0xBA3E
                         "901904" "7480" "12bb99"       # 0x1904 = 0x80
                         "f0"                           # 0x1909 = 0x9F
                         "90190c" "12bafd"              # 0x190C, 0x1900/0x1901
                         "12bcb1" "22")
        # `0xBB99` is the store-then-rotate entry, so the 0x1906 write is
        # inside it and the 0x1909 write is the one back in the default.
        self.assertEqual(BANK0[0xBB99], 0xF0)
        self.assertEqual(hexat(BANK0, 0xBB9A, 5), "901906" "749f")

    def test_the_arming_values_both_have_bit_7_set(self):
        # 0x80 and 0x9F both have bit 7 set, and no edge in the eighteen arms
        # clears it. The document says so and stops there; this is the fact
        # its "not determined" rests on.
        self.assertEqual(0x80 & 0x80, 0x80)
        self.assertEqual(0x9F & 0x80, 0x80)

    def test_bcb1_writes_06_to_08e1_and_zero_to_08e0(self):
        self.assertEqual(hexat(BANK0, 0xBCB1, 12),
                         "9008e1" "7406" "f0"   # 0x08E1 = 6
                         "e4" "9008e0" "f0"     # 0x08E0 = 0
                         "22")

    def test_case_07_falls_through_bcb1_into_the_default(self):
        self.assertEqual(hexat(BANK0, 0x8271, 3), "12bcb1")
        self.assertEqual(0x8271 + 3, 0x8274)

    def test_82ff_ors_bit_7_into_1904(self):
        # The one site in the walk that ORs a gate bit rather than writing a
        # whole byte, and the reason a follow-up should start in 0x8294.
        self.assertEqual(hexat(BANK0, 0x82FF, 7), "901904" "e0" "4480" "f0")
        self.assertEqual(BANK0[0x8303], ORL_A_IMM)

    def test_8294_is_the_committed_listing_that_block_belongs_to(self):
        # The walk reaches 0x8397 from 0x82D8, and the committed listing that
        # runs that far is 8294.asm. The bytes are what this asserts; the
        # listing is only where the document says to look.
        listing = DECOMPILED / 'bank0' / '8294.asm'
        self.assertTrue(listing.exists())
        head = listing.read_text(errors="replace").splitlines()[0]
        self.assertIn("bank0 @ 8294", head)
        self.assertIn("8397", listing.read_text(errors="replace"))


class WhoReachesTheDispatcher(unittest.TestCase):
    """§8's bounded answer: nothing in the committed call census reaches
    bank0's 0x8031, and the rows that look like callers are phantoms or land
    mid-instruction. `bank1,0x1A98` is the one committed annotation about it;
    the rows naming the number without being about it are not callers."""

    def test_a_ret_sits_between_the_initialiser_and_the_dispatch(self):
        self.assertEqual(hexat(BANK0, 0x802E, 3), "a3" "f0" "22")

    def test_0x802c_is_mid_instruction_not_a_jump_target(self):
        # 0x802B is `lcall 0xBCB6` and 0x802C is its second byte. The census
        # row `bank0 0x0AA51 ljmp 0x802C` is real as an `ljmp` and wrong as a
        # destination -- §9's "displaced by a positive alternative" argument,
        # retried on a row §9 did not look at.
        self.assertEqual(hexat(BANK0, 0x802B, 3), "12bcb6")
        self.assertEqual(BANK0[0x802C], 0xBC)
        self.assertEqual(BANK0[0xAA51], LJMP)
        self.assertEqual(be16(BANK0, 0xAA52), 0x802C)

    def test_the_two_census_rows_this_section_retires_are_branch_displacements(self):
        # 0xAA28 and 0xAA67 are the rows that look most like the survivors:
        # the census recorded `02 80 1d` and `02 80 16`, an `ljmp` to 0x801D
        # and 0x8016, both inside the straight-line initialiser before the
        # `ret` that makes 0x8031 a separate entry. The three-byte
        # instruction in front of each site is the whole of the difference:
        # the `0x02` the census read as an `ljmp` opcode is a `jb`/`jnb`
        # displacement, and the `80` behind it is the *next* instruction --
        # an `sjmp` that goes somewhere else entirely. This is the shape the
        # document's own worked example at 0x9AE0 has.
        for branch, site, target, sjmp_target in (
                (JNB, 0xAA28, 0x801D, 0xAA48),
                (JB, 0xAA67, 0x8016, 0xAA80)):
            with self.subTest(site="0x%04X" % site):
                # `acc.0` encodes as 0xE0; the displacement is the site byte.
                self.assertEqual(hexat(BANK0, site - 2, 3), "%02xe002" % branch)
                self.assertEqual(BANK0[site], 0x02)
                # What the census read as the rest of an `ljmp` is in fact
                # the `sjmp` that follows the branch, so the two spellings
                # of those bytes and the branch's real destination differ.
                self.assertEqual(be16(BANK0, site + 1), target)
                self.assertEqual(BANK0[site + 1], SJMP)
                self.assertEqual(site + 3 + BANK0[site + 2], sjmp_target)
                self.assertNotIn(sjmp_target, (target, 0x8031))
                self.assertLess(target, 0x8030)
        # The census's own framing score says the same thing, and the
        # document quotes it: `frame_onto` counts the 24 decodings that put
        # an instruction start at the site.
        for site, onto in ((0xAA28, '3'), (0xAA67, '1'),
                           (0xD902, '24'), (0xAA19, '0')):
            with self.subTest(site="0x%04X" % site):
                self.assertEqual(
                    call_targets()[('bank0', site)]['frame_onto'], onto)

    def test_the_d902_call_names_the_initialiser_head(self):
        self.assertEqual(hexat(BANK0, 0xD902, 3), "128000")
        self.assertEqual(BANK0[0x8000], 0xE4)      # `clr a`, the head

    def test_no_lcall_byte_site_in_either_bank_names_8031(self):
        for name, image in (('bank0', BANK0), ('bank1', BANK1)):
            for off in range(0x8000, len(image) - 2):
                if image[off] == LCALL:
                    self.assertNotEqual(be16(image, off + 1), 0x8031,
                                        "%s:0x%04X lcalls 0x8031"
                                        % (name, off))

    def test_the_trampoline_is_the_one_committed_naming_of_8031(self):
        row = annotations()[('bank1', '1A98')]
        self.assertEqual(row['name'], 'trampoline_bank0_8031')
        self.assertIn('0x8031', row['comment'])
        self.assertEqual(hexat(BANK1, 0x1A98, 6), "908031" "021100")

    def test_the_other_census_rows_into_the_block_are_phantoms(self):
        # §9's argument applied to the whole set, and the shape is slightly
        # different from the one §9 found at 0xAA19: here the recorded `02` is
        # the OPERAND byte of a shorter instruction -- a bit test, a
        # PC-relative branch, an `acall`, a `jbc`, `mov c,bit` -- and the
        # `80` that follows belongs to the instruction AFTER it. The census
        # read the operand as an `ljmp` opcode either way. The length in
        # PHANTOM_SITES is what says which of the two framings applies: a
        # `jb`/`jnb` spends two bytes on operands, so its opcode is two back
        # from the site where the two-byte opcodes are one back.
        for site, (length, opcode) in sorted(PHANTOM_SITES.items()):
            with self.subTest(site="0x%04X" % site):
                self.assertEqual(BANK0[site - (length - 1)], opcode)
                if length == 3:
                    self.assertEqual(BANK0[site - 1], 0xE0)  # `acc.0`
                self.assertEqual(BANK0[site], 0x02)   # read as an `ljmp` opcode
                self.assertEqual(BANK0[site + 1], SJMP)   # the next instruction
        # The same shape, at two sites whose recorded targets are past the
        # initialiser this document is about, so they are out of §8's scope
        # and out of its count.
        for site, opcode in ((0xAB15, 0x70), (0xD768, 0xE3)):
            with self.subTest(site="0x%04X" % site):
                self.assertNotIn(site, PHANTOM_SITES)
                self.assertEqual(BANK0[site - 1], opcode)
                self.assertEqual(BANK0[site], 0x02)
                self.assertEqual(BANK0[site + 1], SJMP)

    def test_the_table_accounts_for_every_census_row_into_the_block(self):
        # §8's twenty-two is not a figure anyone keeps by hand: it is
        # every `bank0` row in the census whose target is 0x8000-0x8038,
        # less §9's retired 0xAA19, sorted into one real call, one `ljmp`
        # with a mid-instruction destination, and twenty phantoms. If a row
        # is added or dropped upstream, the document's sentence has to move
        # with it and this says so first.
        into = [r for r in rows(CALL_TARGETS)
                if r['region'] == 'bank0'
                and 0x8000 <= int(r['target'], 16) <= 0x8038]
        survivors = (0xD902, 0xAA51)        # the table's two real edges
        retired = (0xAA19,)                # §9's, argued out there
        phantoms = [r for r in into
                    if int(r['runtime'], 16) not in survivors + retired]
        self.assertEqual(len(into), 23)
        self.assertEqual(len(phantoms), 20)
        self.assertEqual({int(r['runtime'], 16) for r in phantoms},
                         set(PHANTOM_SITES))
        # The retired row is the same phantom shape, one instruction further
        # in -- which is why §9 could retire it and this counts it out.
        self.assertEqual(
            int(call_targets()[('bank0', 0xAA19)]['target'], 16), 0x8038)


class TheOtherReadersAndWriters(unittest.TestCase):
    """§9's census cross-check. The document says the census is a census of
    the decompiled C and that case 0x07 is invisible to it; both halves are
    asserted, the second against the file and the first against the image."""

    def test_the_census_has_no_row_for_0x08de(self):
        self.assertNotIn(0x08DE, census())
        # ... while the image has the site, at case 0x07's slot store.
        self.assertEqual(hexat(BANK0, 0x823E, 3), "9008de")
        # 0x08DF is the second half of that same two-byte store, so the
        # census misses it for the same reason -- which is why §9 says the
        # census covers thirty of the thirty-two rather than all of them.
        self.assertNotIn(0x08DF, census())
        self.assertEqual(hexat(BANK0, 0x8243, 3), "a3" "ef" "f0")

    def test_the_two_missing_rows_are_the_only_two_of_the_thirty_two(self):
        # §9 opens by naming exactly which addresses the census lacks, so the
        # set is pinned here rather than a count: the 32 the block touches,
        # minus the two named in the document, are all present.
        named = {0x0600 + i for i in range(16)} | {0x08D0 + i for i in range(16)}
        self.assertEqual(named - set(census()), {0x08DE, 0x08DF})

    def test_the_census_has_no_writer_for_0x060e_and_the_image_has_two_sites(self):
        self.assertEqual(census()[0x060E]['writers'], '0')
        # Case 0x07 reads it at 0x8249 and writes it back at 0x825F, both
        # through the 0xB965 round trip of §5.1.
        self.assertEqual(hexat(BANK0, 0x8246, 4), "90060e" "e0")
        self.assertEqual(hexat(BANK0, 0x825C, 4), "90060e" "f0")

    def test_the_census_counts_two_writers_for_08d0_where_the_image_has_one_site(self):
        # The two are the Ghidra entries 0x8048 and 0x8054 that §3 of the
        # document shows are one linear block -- and 0x8048 is a mid-stream
        # `[unresolved]` entry, so one of the census's two "writers" is not a
        # function the project identified at all. A fact about the listing
        # boundaries, and asserting it keeps the §3 claim falsifiable if a
        # rebuild ever merges them.
        #
        # Compared against this row's own `functions` cell rather than
        # against the names existing somewhere in the annotations: `0x806C` is
        # a real `bank0` entry and a writer of `0x0600`, so a check that only
        # asked whether the two names exist would pass while the row named the
        # wrong pair.
        self.assertEqual(census()[0x08D0]['writers'], '2')
        self.assertEqual(hexat(BANK0, 0x8061, 5), "9008d0" "ee" "f0")
        self.assertEqual(
            census()[0x08D0]['functions'],
            "bank0:0x8048=unresolved_midstream_bytes [unresolved]; "
            "bank0:0x8054=index_case_00 [writer]")
        # 0x806C is the third entry on 0x0600's row, and that is where the
        # name belongs.
        self.assertEqual(
            census()[0x0600]['functions'],
            "bank0:0x8048=unresolved_midstream_bytes [unresolved]; "
            "bank0:0x8054=index_case_00 [writer]; "
            "bank0:0x806C=store_byte_through_0a59_into_0600 [writer]")

    def test_the_three_bank1_consumers_of_the_accumulators(self):
        # 0x8886 is the same 16-bit loader in all three, which is what ties
        # the two bank1 sites to bank1,0xB728 at all.
        self.assertEqual(hexat(BANK1, 0xB728, 22),
                         "900610" "e0" "10e501" "22" "f0"
                         "90060a" "128886" "7c03" "7be8" "128863")
        for site in (0xD979, 0xDAED):
            with self.subTest(site="0x%04X" % site):
                self.assertEqual(hexat(BANK1, site, 6), "90060e" "128886")
        # 0xD979 masks the high byte of the word -- `0x8886` puts the low one
        # in r1 -- with 0x03, and what it does with the result is the thing
        # the document declines to say: the `mov dptr,#0x0378` after it is a
        # constant, and nothing between here and the next read of r2 uses it.
        self.assertEqual(hexat(BANK1, 0xD97F, 6), "530203" "900378")
        self._assert_the_listing_does_not_read_r2_before_d9c1()
        # 0xDAED hands the word to 0xA5A7 with two constants. The two
        # bytes at 0xDAF3/0xDAF5 are the ones the three disassemblers in this
        # tree read three ways, so they are asserted as bytes and the document
        # says nothing about which registers hold the word afterwards.
        self.assertEqual(hexat(BANK1, 0xDAF3, 11), "a801" "a902" "7b17" "7a75" "12a5a7")

    def _assert_the_listing_does_not_read_r2_before_d9c1(self):
        # The document's §9 claim that the masked byte is unused in what it
        # decodes is a claim about the committed listing, so it is checked
        # against it: no `R2` operand and no direct `0x02` operand between
        # the two addresses. A rebuild that decodes one in between would say
        # something the document does not.
        listing = (DECOMPILED / 'bank1' / 'D946.asm').read_text(
            errors="replace").splitlines()
        lo = next(i for i, l in enumerate(listing) if l.startswith('D97F'))
        hi = next(i for i, l in enumerate(listing) if l.startswith('D9C1'))
        for line in listing[lo + 1:hi]:
            self.assertNotIn('R2', line, "r2 is read before 0xD9C1: %s" % line)
            self.assertNotIn('0x02', line, "direct 0x02 appears: %s" % line)
        self.assertIn('R2', listing[hi])

    def test_0x8886_is_the_16_bit_loader_all_three_share(self):
        # r1 from the byte at DPTR and r2 from the next one up: low byte
        # first, which is what makes 0xB728's comparison against 0x03E8 a
        # 16-bit comparison and not two byte comparisons.
        self.assertEqual(hexat(BANK1, 0x8886, 6), "e0" "f9" "a3" "e0" "fa" "22")
        self.assertEqual(hexat(BANK1, 0xB737, 4), "7c03" "7be8")

    def test_the_dispatch_table_still_says_what_this_walk_confirms(self):
        # The document's headline is that §9's per-case table stands. Reading
        # the committed table and comparing it to the image is what makes that
        # a checked claim rather than a sentence.
        table = {r['index']: r for r in rows(DISPATCH)}
        for case, target, gate, slot, pair, _f, _a, _h, _h2 in CASES:
            with self.subTest(case="0x%02X" % case):
                row = table['0x%02X' % case]
                self.assertEqual(int(row['target_runtime'], 16), target)
                self.assertEqual(be16(BANK0, target + 1), gate)
                notes = row['notes'].split()
                for addr in (slot, pair, pair + 1, 0x0610, 0x0A59, gate):
                    self.assertIn('0x%04X' % addr, notes)
        self.assertEqual(int(table['default']['target_runtime'], 16), 0x8274)


class TheCommittedArmsTable(unittest.TestCase):
    """The CSV is the machine-readable half of the document. It is compared to
    the image here rather than to `walk_branch_arms.py`, so a regeneration that
    changed either side fails instead of agreeing with itself."""

    def test_every_arm_row_is_complete_and_covers_nine_sites(self):
        seen = set()
        for r in rows(ARMS):
            if r['kind'] != 'arm':
                continue
            target = int(r['site_runtime'], 16)
            seen.add((target, r['arm']))
            self.assertEqual(r['status'], 'complete',
                             "an arm of 0x%04X is cut: %s"
                             % (target, r['ends']))
            case = next((c for c, t, *_ in CASES if t == target), None)
            # 0x82D8 is the one non-handler site, and it is the same `jnb`.
            self.assertEqual(BANK0[target + 4],
                             BRANCH_OPCODE[case] if case is not None else JNB,
                             "0x%04X no longer branches on bit 7" % target)
        self.assertEqual(len(seen), 18)
        for case, target, *_ in CASES:
            self.assertIn((target, 'taken'), seen)
            self.assertIn((target, 'fall-through'), seen)
        # The other two belong to 0x82D8, which is not a handler. Their sizes
        # are pinned here because §7.1 of the document points at these two
        # rows instead of restating them -- so a regeneration that changed a
        # size has to fail rather than leave the prose quietly wrong. These
        # are pins, not a re-derivation: the block count is the ` | ` count
        # the writer emits, so seven blocks is six separators.
        by_arm = {r['arm']: r for r in rows(ARMS)
                  if r['kind'] == 'arm' and int(r['site_runtime'], 16) == 0x82D8}
        self.assertEqual(sorted(by_arm), ['fall-through', 'taken'])
        for arm, insns in (('taken', 137), ('fall-through', 154)):
            with self.subTest(arm=arm):
                self.assertEqual(by_arm[arm]['insns'], str(insns))
                self.assertEqual(by_arm[arm]['window'].count(' | ') + 1, 7)
        # They are an order of magnitude past every handler arm, which is what
        # "the largest thing the walk turned up" is being read against.
        for case, _t, *_ in CASES:
            with self.subTest(case="0x%02X" % case):
                self.assertLess(int(arm_row(case)['insns']), 100)

    def test_each_clear_arm_reaches_only_the_default(self):
        for case, target, *_ in CASES:
            if case == 0x07:
                continue
            with self.subTest(case="0x%02X" % case):
                row = [r for r in rows(ARMS)
                       if r['kind'] == 'arm'
                       and int(r['site_runtime'], 16) == target
                       and r['arm'] == 'fall-through'][0]
                self.assertEqual(int(row['arm_start'], 16), target + 7)
                self.assertEqual(row['callees'], '0x8274')
                self.assertEqual(row['xdata'], '')
                self.assertEqual(row['insns'], '1')
                self.assertEqual(row['window'],
                                 '0x%04X ljmp 0x8274' % (target + 7))

    def test_the_taken_arms_reach_their_own_slots_and_pairs(self):
        for case, target, gate, slot, pair, *_ in CASES:
            with self.subTest(case="0x%02X" % case):
                row = arm_row(case)
                for addr in (0x0610, slot, pair, pair + 1, 0x0A59):
                    self.assertIn('0x%04X' % addr, row['xdata'])
                # The slot's low byte is written by the `inc dptr` after it,
                # which is what leaves the pointer unknown, so the walk
                # credits the two-byte write to the slot alone. Asserted
                # because "the slot is 0x08D0/0x08D1" and "the scan names
                # 0x08D0" are different claims and only the first is a
                # reading of the handler.
                self.assertIn('0x%04X' % slot, row['xdata'])
                self.assertNotIn('0x%04X' % (slot + 1), row['xdata'])
                # The gate is read and never written by the arm; the re-arm is
                # inside a callee, which is why it is absent from this column.
                self.assertNotIn('0x%04X' % gate, row['xdata'])

    def test_the_callee_rows_name_the_helpers_the_document_lists(self):
        names = {r['callee'] for r in rows(ARMS) if r['kind'] == 'callee'}
        for addr in (0xB965, 0xBA3D, 0xBB08, 0xBCB1, 0xB9DF, 0xB9EA,
                     0xBDAE, 0xBDBA, 0xBDC6, 0xBB9A, 0xBE7E, 0xBE88, 0xBE92):
            with self.subTest(callee="0x%04X" % addr):
                self.assertIn('0x%04X' % addr, names)


class TheCorrectionDiscipline(unittest.TestCase):
    """The correction beside §9's table has to keep the thing that makes it
    readable: §9's original values, visible, with the walk's answer next to
    them. A later change that quietly overwrote them would leave a correction
    with nothing to correct, and this is what catches that."""

    SECTION9_ROWS = (
        ('0x00', '0x8054', '0x1904', '0x08D0', '0x0600`/`0x0601', '0x01'),
        ('0x01', '0x8094', '0x1906', '0x08D2', '0x0602`/`0x0603', '0x02'),
        ('0x02', '0x80D7', '0x1909', '0x08D4', '0x0604`/`0x0605', '0x04'),
        ('0x03', '0x811A', '0x190C', '0x08D6', '0x0606`/`0x0607', '0x08'),
        ('0x04', '0x815D', '0x1904', '0x08D8', '0x0608`/`0x0609', '0x10'),
        ('0x05', '0x819D', '0x1906', '0x08DA', '0x060A`/`0x060B', '0x20'),
        ('0x06', '0x81DF', '0x1909', '0x08DC', '0x060C`/`0x060D', '0x40'),
        ('0x07', '0x8231', '0x190C', '0x08DE', '0x060E`/`0x060F', '0x80'),
    )

    def section9(self):
        text = AUDIT_DOC.read_text()
        body = text[text.index('## 9. The `0x8038` table'):]
        return body[:body.index('## 10.')]

    def test_section_9_still_carries_the_values_this_corrects(self):
        section = self.section9()
        for row in self.SECTION9_ROWS:
            with self.subTest(case=row[0]):
                cells = ' | '.join('`%s`' % c for c in row)
                self.assertIn('| ' + cells + ' |', section,
                              "§9's row for case %s is gone" % row[0])
        # ... and the linear-decode caveat this walk answers, still standing.
        self.assertIn('not a control-flow trace', section)
        self.assertIn('separate piece of work', section)

    def test_the_correction_sits_beside_the_table_and_names_this_change(self):
        section = self.section9()
        self.assertIn('bank0-8038-handler-flow.md', section)
        self.assertIn('#60', section)
        # Beside the table, not over it: after the last per-case row.
        self.assertLess(section.index('| `0x07` | `0x8231`'),
                        section.index('bank0-8038-handler-flow.md'))
        # And it names the value it corrects, in §9's own spelling, so a
        # reader can see which sentence changed its mind.
        self.assertIn('0x81 + case', section)

    def test_the_document_carries_the_same_correction(self):
        doc = FLOW_DOC.read_text()
        self.assertIn('0x826C', doc)
        self.assertIn('`mov a,#0x80`, not `0x88`', doc)
        self.assertIn('The per-case table stands', doc)

    def test_the_document_makes_no_behavioural_claim(self):
        # The calibration rule, as five phrasings this document must not use.
        doc = FLOW_DOC.read_text()
        for phrase in ('the EC does', 'the handlers run', 'is unused',
                       'there are none', 'has no effect'):
            self.assertNotIn(phrase, doc,
                             "'%s' is a claim this document must not make"
                             % phrase)
        self.assertIn('not found by this method', doc)

    def test_nothing_here_moved_a_register_status(self):
        for path in (FLOW_DOC, AUDIT_DOC):
            text = path.read_text()
            self.assertNotIn('status: confirmed', text)
            self.assertNotIn('status: present-untested', text)


if __name__ == '__main__':
    unittest.main()
