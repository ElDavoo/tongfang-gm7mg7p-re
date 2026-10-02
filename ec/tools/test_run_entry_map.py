#!/usr/bin/env python3
"""Unit checks for the `run=0x8518` entry map (issue #1185).

`docs/findings/scheduler-run-8518-entries.md` decodes the block the charge
target's caller chain lands in: which of its slots a far-call stub names, what
each slot does on a pass, and which of the XDATA it writes the host can
actually see. This file holds the byte facts that reading stands on.

**The image, not a re-run of the tool's own scan.** Every case here reads
`ec/firmware/GMxMGxx_11.800` or a committed CSV. A regenerated table that
disagreed would then fail instead of passing on a stale pair -- the
`test_bank1_e582_framing.py` arrangement, and the reason the tool's `--csv` mode
is not what these cases compare against.

**The stub-to-segment map is computed, not asserted.** `test_each_stub_names_its
_own_segments_head` reads the stub immediates out of the committed
`task-call-table.csv` and the segment heads out of the run's own opcodes, and
asserts the two sets are equal. It does not assert "seven stubs" and it does not
assert a list of indices: a changed stride, a changed stub immediate or a
changed opcode moves one of the two sides and the failure names it, where a
literal would have kept passing. The census -- how many stubs there are -- is
deliberately not what any case holds, per CLAUDE.md's rule that a test asserts
the claim rather than a count of the tree.

**The reachability premise is pinned here as well as in the tool.** A
tail-jumped slot's target returning to the entry's caller rather than resuming
the block is the one premise the whole map rests on, and it is a property of the
`0x1100` bank-select trampoline's bytes. `TheMarkerPremise` checks the stack
shape directly: the stub pushes DPL and DPH last and ends in `ret`, so its own
`ret` consumes the pointer and the marker is what the far routine pops. The
marker's *low* byte is a runtime value -- direct 0x08's value at entry -- so
the claim is held against the **window** its constant high byte forces, and
`test_the_window_is_disjoint_from_the_run` is what makes the reachability
column mean something. A tool that published a reachability table off an
unsettled premise would print `reach unsettled`; these cases make sure it has a
reason to.

**The host-window classification is checked against the imported constant**, not
a copy of it. `ec_timer_capture.HOST_WINDOW` is imported, so a change to the
window moves the verdicts with it. And the suite asserts that at least one
named slot's write set falls wholly outside it -- that is the finding a future
capture run most needs warned about, and a test that only ever checked the
classification would pass just as well if every slot turned out visible.
"""
import csv
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import run_entry_map
from ec_timer_capture import HOST_WINDOW
from trace_xdata_refs import offset_for_runtime

FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
TASK_TABLE = HERE.parent / 'annotations' / 'task-call-table.csv'
FUNCTIONS = HERE.parent / 'annotations' / 'ghidra-functions.csv'
WRITEUP = ROOT / 'docs' / 'findings' / 'scheduler-run-8518-entries.md'

IMAGE = FIRMWARE.read_bytes()

# The stub's own extent, and the marker's high byte as the bytes spell it. Both
# are transcribed by hand from the image rather than read out of a decode this
# suite then checks against itself, which is `walk_branch_arms.SELF_TEST_SITES`'s
# arrangement for the same reason.
SELECT_STUB = 0x1100
SELECT_STUB_LENGTH = 20
SELECT_STUB_BYTES = bytes.fromhex('c0087411c0e0c082c08375080ac290c291c29222')
MARKER_HIGH = 0x11
MARKER_WINDOW = (0x1100, 0x11FF)

# The two absolute-transfer opcodes, and the run's stride. `task_call_table.py`
# is the authority on both -- it is what produced the committed rows -- and the
# cases below re-derive from the image rather than importing its predicate, so
# that a change in either place shows up as a disagreement instead of being
# agreed with by construction.
LCALL, LJMP = 0x12, 0x02
STRIDE = 3


def at(addr, n=1, region='bank0'):
    """The n bytes at a runtime address, as a hex string."""
    off = offset_for_runtime(addr, region)
    return IMAGE[off:off + n].hex(' ')


def slots():
    """The run's `Slot` list with segments and stub attributions filled in."""
    out, stubs = run_entry_map.read_run(TASK_TABLE)
    run_entry_map.segments(out)
    idx = run_entry_map.index_of(out)
    for target, stub_addr in stubs.items():
        if target in idx:
            out[idx[target]].stub = stub_addr
    return out, stubs


class TheRunItself(unittest.TestCase):
    """The block is a stride-3 run of 3-byte absolute transfers, and the
    committed table says so."""

    def test_every_row_re_decodes_from_the_image(self):
        # The CSV's opcode and immediate against the bytes, per row. A table
        # that had drifted from the image fails here rather than being read as
        # the authority further down.
        rows, _stubs = slots()
        self.assertTrue(rows, 'no run rows in the committed table')
        for slot in rows:
            with self.subTest(index=slot.index):
                raw = IMAGE[offset_for_runtime(slot.address, 'bank0'):][:3]
                self.assertIn(raw[0], (LCALL, LJMP))
                self.assertEqual('lcall' if raw[0] == LCALL else 'ljmp',
                                 slot.opcode)
                self.assertEqual((raw[1] << 8) | raw[2], slot.target)

    def test_the_stride_is_three_throughout(self):
        # Arithmetic on the committed addresses rather than a literal count, so
        # a lost slot moves the spacing and is named.
        rows, _stubs = slots()
        for a, b in zip(rows, rows[1:]):
            with self.subTest(after=f"0x{a.address:04X}"):
                self.assertEqual(b.address - a.address, STRIDE)

    def test_the_indices_are_contiguous_from_zero(self):
        # A run whose index column skipped a value would make "index 11" mean
        # two different slots in two files, so the column is checked as a
        # property of the rows rather than trusted.
        rows, _stubs = slots()
        self.assertEqual([s.index for s in rows], list(range(len(rows))))

    def test_the_run_ends_where_the_next_routine_starts(self):
        # 0x855A is `mov dptr,#0x085F`, not a transfer: the run's last slot ends
        # where a different routine begins. Pinned so a widened stride cannot
        # quietly absorb the next routine into the run.
        rows, _stubs = slots()
        last = rows[-1]
        self.assertEqual(last.opcode, 'ljmp')
        self.assertEqual(last.address + STRIDE, 0x855A)
        self.assertEqual(at(0x855A, 3), '90 08 5f')


class TheSegmentShape(unittest.TestCase):
    """A segment is a maximal lcall run ending at an ljmp. The claim under
    test is that the stub immediates name the segment *heads*."""

    def test_each_stub_names_its_own_segments_head(self):
        # **Computed, not asserted.** Both sides are derived independently --
        # the heads from the run's opcodes, the stub targets from the committed
        # stub table -- and the claim is that they are equal. Neither the
        # number of stubs nor the list of indices appears here.
        rows, stubs = slots()
        idx = run_entry_map.index_of(rows)
        named = sorted(idx[t] for t in stubs if t in idx)
        heads = run_entry_map.head_indices(rows)
        self.assertEqual(named, heads)

    def test_the_comparison_is_not_vacuous(self):
        # If every slot were its own head the equality above would hold for any
        # stub table at all, so the head set is shown to be a proper subset.
        rows, _stubs = slots()
        self.assertLess(len(run_entry_map.head_indices(rows)), len(rows))

    def test_every_segment_ends_at_an_ljmp(self):
        # The shape that makes a head a head. Checked over the decoded opcodes
        # so a table that kept the addresses but lost the opcodes fails here.
        rows, _stubs = slots()
        for i, slot in enumerate(rows):
            if not slot.head:
                continue
            segment = [slot]
            for other in rows[i + 1:]:
                if other.head:
                    break
                segment.append(other)
            with self.subTest(head=slot.index):
                self.assertTrue(segment[-1].tail_jump,
                                'segment does not end at an ljmp')
                for inner in segment[:-1]:
                    self.assertFalse(inner.tail_jump,
                                     'an ljmp is only ever a segment\'s last slot')

    def test_a_head_is_the_first_entry_or_follows_an_ljmp(self):
        rows, _stubs = slots()
        for i, slot in enumerate(rows):
            if slot.head and i:
                with self.subTest(index=slot.index):
                    self.assertTrue(rows[i - 1].tail_jump)

    def test_a_stub_immediate_is_never_in_the_middle_of_a_segment(self):
        # The negative half of the same claim, and the one that would catch a
        # stub pointing into a segment's body: such a slot would be entered
        # with no `lcall` return of its own, so the segment structure would not
        # describe the path actually taken.
        rows, stubs = slots()
        heads = set(run_entry_map.head_indices(rows))
        for target in stubs:
            for slot in rows:
                if slot.target == target and slot.index not in heads:
                    self.fail(f"stub 0x{stubs[target]:04X} names run index "
                              f"{slot.index}, which is not a segment head")


class TheMarkerPremise(unittest.TestCase):
    """Why a tail-jumped slot leaves the block: the `0x1100` trampoline's
    stack shape, read from its own bytes."""

    def test_the_stub_bytes(self):
        self.assertEqual(IMAGE[SELECT_STUB:SELECT_STUB + SELECT_STUB_LENGTH],
                         SELECT_STUB_BYTES)

    def test_the_stub_pushes_dpl_and_dph_last_and_ends_in_ret(self):
        # The order is the claim. The stub's own `ret` pops the top two stack
        # bytes into PC, so DPL and DPH being the last two pushes is what makes
        # it jump to the far address -- and therefore what leaves the marker on
        # the stack for the far routine's own `ret` to pop.
        insns = run_entry_map.decode_select_stub(IMAGE, SELECT_STUB)
        self.assertTrue(insns)
        self.assertEqual(insns[-1][1], b'\x22', 'the stub does not end in ret')
        pushes = [raw for _off, raw, _t in insns if raw[0] == 0xC0]
        self.assertGreaterEqual(len(pushes), 3)
        self.assertEqual(pushes[-2][1], 0x82, 'second-to-last push is not DPL')
        self.assertEqual(pushes[-1][1], 0x83, 'last push is not DPH')

    def test_the_stub_does_not_run_into_the_next_one(self):
        # The four stubs are 20 bytes apart with no gap, so decoding past this
        # one would read the next stub's body and a predicate like "ends in
        # ret" would be reading the wrong stub.
        insns = run_entry_map.decode_select_stub(IMAGE, SELECT_STUB)
        for off, _raw, _t in insns:
            self.assertLess(off, SELECT_STUB + SELECT_STUB_LENGTH)

    def test_the_markers_high_byte_is_the_stubs_own_constant(self):
        # `mov a,#0x11` is the byte a later ret pops into PCH. Asserted against
        # the bytes rather than against the tool's own reading of them, so a
        # decoder that rendered the same bytes consistently wrongly would fail
        # here rather than agree with itself.
        self.assertEqual(at(SELECT_STUB + 2, 2, 'common'), '74 11')

    def test_the_window_is_derived_from_that_byte(self):
        window, _evidence = run_entry_map.marker_landing(IMAGE)
        self.assertEqual(window, MARKER_WINDOW)
        self.assertEqual(window[0] >> 8, MARKER_HIGH)

    def test_the_window_is_disjoint_from_the_run(self):
        # The reachability claim, held as a property: no address a far routine
        # can return to is one of the run's own slots. True whatever the
        # marker's low byte is, which is the point -- the low byte is a runtime
        # value and the claim must not rest on which of the four it took.
        rows, _stubs = slots()
        window, _evidence = run_entry_map.marker_landing(IMAGE)
        low, high = window
        for slot in rows:
            with self.subTest(index=slot.index):
                self.assertFalse(low <= slot.address <= high)

    def test_the_low_byte_is_a_runtime_value_not_a_constant(self):
        # Pinned as what it is, so a future reader does not read the window as
        # a single address. The four bank-select stubs each write their own
        # value into direct 0x08, and the landing is 0x11 <that value>.
        for base, value in ((0x1100, 0x0A), (0x1114, 0x1E),
                            (0x1128, 0x32), (0x113C, 0x46)):
            with self.subTest(stub=f"0x{base:04X}"):
                self.assertEqual(at(base + 10, 3, 'common'),
                                 f"75 08 {value:02x}")
                low, high = MARKER_WINDOW
                self.assertTrue(low <= (MARKER_HIGH << 8) | value <= high)

    def test_reach_is_unsettled_rather_than_assumed(self):
        # The refusal the tool publishes when the premise cannot be settled.
        # Driven with a stub that has the wrong shape, so the path that produces
        # `reach unsettled` is exercised rather than assumed to work.
        self.assertFalse(run_entry_map.reach_settled(
            IMAGE, None, [s.address for s in slots()[0]])[0])
        # And the overlap direction, which is the other way the premise can
        # fail: a window that *did* contain a slot of the run.
        rows, _stubs = slots()
        self.assertFalse(run_entry_map.reach_settled(
            IMAGE, (rows[0].address, rows[-1].address),
            [s.address for s in rows])[0])


class TheOutsideScan(unittest.TestCase):
    """No `lcall`/`ljmp` anywhere in the image names a slot of the block, so
    nothing enters the middle of a segment. A zero, and it is a zero *by this
    method*."""

    def test_the_scan_finds_nothing(self):
        rows, _stubs = slots()
        hits = run_entry_map.transfer_hits(IMAGE, {s.address for s in rows})
        self.assertEqual(hits, {})

    def test_the_scan_would_find_a_hit_if_one_existed(self):
        # The negative control, and the reason green means anything here: a
        # predicate that matches nothing matches nothing. Pointed at an address
        # the block itself transfers to, which the same scan must find.
        rows, _stubs = slots()
        found = run_entry_map.transfer_hits(IMAGE, {rows[0].target})
        self.assertTrue(found, 'the scan finds nothing even where a hit exists')

    def test_both_opcodes_are_covered(self):
        # `lcall` and `ljmp` are two different opcodes and the block uses both.
        # A scan that dropped one would still report zero for any address the
        # other opcode did not name, so each is checked against a known hit.
        rows, _stubs = slots()
        lcall_target = next(s.target for s in rows if s.opcode == 'lcall')
        ljmp_target = next(s.target for s in rows if s.opcode == 'ljmp')
        self.assertTrue(run_entry_map.transfer_hits(IMAGE, {lcall_target}))
        self.assertTrue(run_entry_map.transfer_hits(IMAGE, {ljmp_target}))


class TheHostWindow(unittest.TestCase):
    """Which of the block's writes the host can see, checked against the
    imported constant rather than a copy of it."""

    def test_the_window_is_the_imported_one(self):
        # Not a restatement of the value -- an assertion that the tool reads
        # the same constant this module does, so a change to either is a change
        # to both.
        self.assertIs(run_entry_map.HOST_WINDOW, HOST_WINDOW)

    def test_the_pages_outside_the_window_read_as_ff(self):
        # The measured half of the claim, cited from the committed census
        # rather than asserted from memory: the pages the block writes in that
        # the host cannot map are the ones that came back 0/256.
        census = ROOT / 'evidence' / 'ec-watch' / \
            '2026-09-24-host-window-page-census.txt'
        text = census.read_text()
        invisible = set()
        for line in text.splitlines():
            m = re.match(r'^0x([0-9a-f]{4})\s+0/256$', line.strip())
            if m:
                invisible.add(int(m.group(1), 16))
        self.assertTrue(invisible, 'no 0/256 page found in the committed census')
        for page in sorted(invisible):
            with self.subTest(page=f"0x{page:04X}"):
                self.assertFalse(run_entry_map.host_visible(page))

    def test_the_classification_is_a_property_of_the_address(self):
        for addr, want in ((0x0000, True), (0x07FF, True), (0x0800, False),
                           (0x0BFF, False), (0x0C00, True), (0x0FFF, True),
                           (0x1000, False), (0x1300, False)):
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(run_entry_map.host_visible(addr), want)

    def test_some_named_slot_writes_nowhere_the_host_can_see(self):
        # **The finding a future capture run most needs warned about**, and the
        # case that makes the classification above worth having: at least one
        # slot the CSV names a routine for has a write set wholly outside the
        # window, so a capture watching it sees nothing and must not read that
        # as a stalled counter.
        rows, _stubs = slots()
        names = run_entry_map.committed_names(FUNCTIONS)
        invisible = []
        for slot in rows:
            if run_entry_map.name_for(names, 'bank0', slot.target) \
                    == run_entry_map.NO_NAME:
                continue
            arm = run_entry_map.descend(IMAGE, 'bank0', slot.target, None,
                                        run_entry_map.MAX_DEPTH,
                                        run_entry_map.MAX_INSNS, True)
            writes = [a for a in arm.writes()]
            if writes and not any(run_entry_map.host_visible(a) for a in writes):
                invisible.append((slot.index, writes))
        self.assertTrue(
            invisible,
            'no named slot writes wholly outside the host window, so the '
            'invisible-page warning this write-up leads with has no instance')

    def test_a_slot_that_writes_nothing_is_not_reported_as_writing(self):
        # The refusal, checked rather than described: an empty write set says
        # "no arm found by this method", never that the EC does not write.
        # `no_claim` reads `slot.arm`, so the arm is attached to the slot rather
        # than held beside it -- otherwise every row takes the "nothing decoded"
        # branch and the case would pass without testing the refusal at all.
        rows, _stubs = slots()
        for slot in rows:
            slot.arm = run_entry_map.descend(IMAGE, 'bank0', slot.target, None,
                                             run_entry_map.MAX_DEPTH,
                                             run_entry_map.MAX_INSNS, True)
            claim = run_entry_map.no_claim(slot, [])
            with self.subTest(index=slot.index):
                if slot.arm.writes():
                    self.assertEqual(claim, '')
                else:
                    self.assertIn('no arm found by this method', claim)
                    self.assertNotIn('the EC does not', claim)


class TheCommittedNames(unittest.TestCase):
    """The name column, and the five targets that have none."""

    def test_a_name_is_found_for_a_target_that_has_one(self):
        # Looked up by the parsed address, because the CSV spells the same
        # address several ways -- `0x1978` and `1978` are both in this file --
        # and a text key would miss rows silently. The miss prints `no committed
        # name`, which reads as a fact about the firmware rather than as a
        # lookup that never matched.
        names = run_entry_map.committed_names(FUNCTIONS)
        self.assertEqual(run_entry_map.name_for(names, 'bank0', 0xB065),
                         'ten_count_gate_then_set_1300_and_200f')

    def test_the_key_is_the_parsed_address_not_the_cell_text(self):
        # **The negative control for the case above**, and the reason it is
        # here: every target of this run happens to be spelled in the file
        # *without* a `0x` prefix, so a text-keyed lookup would agree with a
        # parsed one on all of them and the case above would pass with the bug
        # present. This points the same lookup at a row the file spells the
        # other way, so the two keyings are told apart.
        with open(FUNCTIONS, newline='') as handle:
            prefixed = [row for row in csv.DictReader(handle)
                        if row['addr'].lower().startswith('0x')]
        self.assertTrue(prefixed,
                        'no 0x-prefixed addr cell in the file, so this case '
                        'cannot tell the two keyings apart')
        row = prefixed[0]
        names = run_entry_map.committed_names(FUNCTIONS)
        addr = int(row['addr'], 16)
        self.assertNotEqual(row['addr'], format(addr, '04X'),
                            'this row is not spelled differently after all')
        self.assertEqual(run_entry_map.name_for(names, row['scope'], addr),
                         row['name'])

    def test_the_unnamed_targets_say_so_rather_than_going_blank(self):
        # A blank cell would read as "nothing to record"; the explicit token
        # says the lookup ran and the row is absent.
        names = run_entry_map.committed_names(FUNCTIONS)
        rows, _stubs = slots()
        unnamed = [s.target for s in rows
                   if run_entry_map.name_for(names, 'bank0', s.target)
                   == run_entry_map.NO_NAME]
        self.assertTrue(unnamed, 'every slot is named; the write-up says otherwise')
        for target in unnamed:
            with self.subTest(target=f"0x{target:04X}"):
                self.assertNotEqual(target, 0)
                # And each has a committed decompile, which is what lets the
                # write-up characterise it without a Ghidra run.
                for ext in ('asm', 'c'):
                    listing = HERE.parent / 'decompiled' / 'bank0' / \
                        f'{target:04X}.{ext}'
                    self.assertTrue(listing.exists(), f'missing {listing}')


class TheWriteup(unittest.TestCase):
    """The write-up's table is parsed back and compared against the tool, so
    prose and tool cannot drift."""

    ROW = re.compile(r'^\|\s*`?0x([0-9A-Fa-f]{4})`?\s*\|\s*`?(lcall|ljmp)`?\s*\|'
                     r'\s*`?0x([0-9A-Fa-f]{4})`?\s*\|\s*(\d+)\s*\|')

    def table_rows(self):
        text = WRITEUP.read_text()
        found = []
        for line in text.splitlines():
            m = self.ROW.match(line.strip())
            if m:
                found.append((int(m.group(1), 16), m.group(2),
                              int(m.group(3), 16), int(m.group(4))))
        return found

    def test_the_writeup_exists_and_has_a_table(self):
        self.assertTrue(WRITEUP.exists(), f'{WRITEUP} is missing')
        self.assertTrue(self.table_rows(),
                        'no slot rows parsed out of the write-up table')

    def test_every_slot_appears_exactly_once(self):
        rows, _stubs = slots()
        parsed = self.table_rows()
        self.assertEqual([a for a, _op, _t, _s in parsed],
                         [s.address for s in rows])

    def test_the_opcode_and_target_agree_with_the_bytes(self):
        rows, _stubs = slots()
        for (addr, op, target, _segment), slot in zip(self.table_rows(), rows):
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(op, slot.opcode)
                self.assertEqual(target, slot.target)

    def test_the_segment_column_agrees_with_the_derived_segments(self):
        # The segment number in the prose is the tool's own, compared rather
        # than copied, so a run that changed shape moves this too.
        rows, _stubs = slots()
        for (_addr, _op, _target, segment), slot in zip(self.table_rows(), rows):
            with self.subTest(addr=f"0x{slot.address:04X}"):
                self.assertEqual(segment, slot.segment)

    def test_the_writeup_keeps_the_absence_claims_calibrated(self):
        # A write-up that had drifted into asserting absence would pass every
        # case above, so the two phrases that make it an absence claim are held
        # to the wording the calibration rule requires.
        text = WRITEUP.read_text()
        self.assertIn('not found by this method', text)
        self.assertNotIn('the EC does not write', text)
        # And it says the host-window split is a preparation, not a result.
        self.assertIn('HOST_WINDOW', text)


class TheInvariants(unittest.TestCase):
    """The claims about the tool itself that a reader relies on."""

    def test_task_call_table_csv_is_not_written(self):
        # The tool reads the CSV and never writes it; `task_call_table.py` owns
        # it and holds it to the image. Checked as a source-level property
        # rather than by watching the filesystem, because the failure being
        # guarded against is a future mode added to this tool, and a mode that
        # truncated the file would be caught by the next case only after the
        # damage.
        source = (HERE / 'run_entry_map.py').read_text()
        for token in ('open(TASK_TABLE, "w"', "open(TASK_TABLE, 'w'",
                      'TASK_TABLE, "w"', "TASK_TABLE, 'w'",
                      'TASK_TABLE, "a"', "TASK_TABLE, 'a'"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_the_tool_self_test_exits_zero(self):
        # The tool's own --self-test is part of what this change ships, so a
        # regression there is a regression here rather than something a
        # maintainer has to remember to run.
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(HERE / 'run_entry_map.py'), '--self-test',
             str(FIRMWARE)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_task_call_table_still_agrees_with_the_image(self):
        # Nothing this change does may have moved the CSV the tool reads.
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(HERE / 'task_call_table.py'), str(FIRMWARE),
             '--check'], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_the_committed_table_still_names_this_run(self):
        # The tool reads the run out of the CSV rather than re-scanning for it,
        # so a table regenerated under a different base would leave the tool
        # with no run at all -- silently, if the lookup were a default.
        with open(TASK_TABLE, newline='') as handle:
            runs = {row['run'] for row in csv.DictReader(handle)
                    if row['table'] == 'bank0-transfer-run'}
        self.assertIn(run_entry_map.RUN, runs)


if __name__ == '__main__':
    unittest.main()
