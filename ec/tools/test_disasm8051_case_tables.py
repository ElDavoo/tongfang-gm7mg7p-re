#!/usr/bin/env python3
"""The `0x7151` case-table framing contract of `disasm8051`, on its own.

`test_disasm8051_inline_args.py` holds the sibling contract for the PD image's
`0x104D` block: a fixed width, so `inline_arg_len()` can express it. The main
EC's `switch_case_dispatch` at `0x7151` is a different shape again -- 3-byte
entries until a `00 00` head, then a 2-byte default -- so it cannot be a second
row in that table and gets its own function, its own file, and these cases.
`../../docs/findings/7151-case-tables-in-the-walk.md` is where the rule is
established; this is where the decoder's half of it is pinned.

The cases split by what they would catch. The first pair is the claim and its
teeth: a table is skipped as one indivisible item, and a `00 00` *ends* the
skip so the walk resumes on the byte after the default rather than on the
default itself -- resuming on the default is the defect, because the default
is a code address the reader dispatches to. The bounds cases hold at the two
edges a scan creates and a fixed width does not have: a table the buffer does
not hold whole, and one whose terminator never arrives, which must decline
rather than run to the end of the buffer. The last two are the safety
arguments -- a table entry that matched on the opcode alone would re-frame
every `lcall` in the image, and the population this changes is the one carrying
a load-bearing negative, so what the corrected walk removes is pinned by
identity (these offsets are inside a table span) rather than by a count.
"""
import csv
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load('disasm8051')
F = _load('find_indirect_xdata')
T = _load('trace_xdata_refs')

FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
SPANS_CSV = HERE.parent / "annotations" / "index-table-spans.csv"

# The table's own entry and the reader's own extent rule, read from the module
# rather than spelled here: a test that hard-coded the address it is testing
# the table for would keep passing after the table was pointed somewhere else.
TARGET, WIDTH = next(iter(D.CASE_TABLE_CALLS.items()))

# A `lcall` to the named target, the committed `0x0F254` table's seven 3-byte
# entries, the `00 00` terminator, the 2-byte default, and the instruction
# after it -- the bytes transcribed out of `ec/firmware/GMxMGxx_11.800` at file
# offsets `0x0F257`-`0x0F272`, grouped as the reader groups them in
# `ec/decompiled/common/7151.c`. The real table rather than a shaped stand-in
# because `0x0F254` is the site whose four decoded-as-instruction rows this
# removes, and a fixture invented for it would be asserting against itself.
# The targets are left as the two-byte values the reader consumes without
# interpreting them, so these cases assert the *framing* and nothing about what
# the entries point at.
ENTRIES = bytes([0xF2, 0x70, 0x00, 0xF2, 0xF8, 0x01, 0xF3, 0x8E, 0x03,
                 0xF3, 0xBE, 0x04, 0xF3, 0xE1, 0x06, 0xF3, 0xFD, 0x07,
                 0xF4, 0x14, 0x08])
TERMINATOR = b"\x00\x00"
DEFAULT = b"\xf4\x2b"
RESUME = b"\x90\x0e\x00"
CALL = bytes([0x12, TARGET >> 8, TARGET & 0xFF])
SHAPE = CALL + ENTRIES + TERMINATOR + DEFAULT + RESUME
TABLE_LEN = len(ENTRIES) + len(TERMINATOR) + len(DEFAULT)
# The 0xF2/0xF3 lead bytes are the `movx @Ri` opcodes the old walk reported as
# four sites in this span, so the same four offsets are named here as data and
# asserted not to decode as instructions anywhere in the suite.
MOVX_BYTES = (0xF2, 0xF3)

# A table of `n` entries whose bytes spell nothing, for the cases that need a
# length the seven-entry fixture does not have. Neither the target pair nor the
# case byte is `00`, so no entry head can be mistaken for the terminator and
# the scan runs to the one this file puts there.
def entries_of(n: int) -> bytes:
    return b"".join(bytes([0x12, 0x34, 0x56 + i % 10]) for i in range(n))


class TheTableIsData(unittest.TestCase):
    """The bytes after the call are one item, and the walk resumes past the
    default rather than on it."""

    def test_a_table_is_skipped_and_yielded_as_data(self):
        got = list(D.decode(SHAPE, 0, 2, 0x0F254))
        self.assertEqual(got[0], (0, CALL, f"lcall 0x{TARGET:04x}"))
        self.assertEqual(got[1][0], 3, "the table starts at the byte after the call")
        self.assertEqual(got[1][1], SHAPE[3:3 + TABLE_LEN],
                         "the yielded block is the table and its default")
        self.assertEqual(got[1][2], f"case table: {TABLE_LEN} bytes")
        # Offset 3 + 25, not 3 + 23: the two default bytes past the terminator
        # are inside the block. A walk resuming on the default would decode a
        # code address as an instruction, which is the defect this table
        # exists to prevent.
        self.assertEqual(got[2], (3 + TABLE_LEN, RESUME, "mov  dptr,#0x0e00"))
        self.assertEqual(TABLE_LEN, 7 * WIDTH + D.CASE_TABLE_TAIL)

    def test_the_terminator_ends_the_scan_rather_than_the_buffer(self):
        # The rule is a terminator, not a width, so the answer moves with the
        # entry count. One entry and seven are the same code with six more `3`s,
        # and a decoder that had a width baked in would return the same length
        # for both -- which is what makes it a scan.
        for n in (1, 4, 7):
            shape = CALL + entries_of(n) + TERMINATOR + DEFAULT + RESUME
            self.assertEqual(D.case_table_len(shape, 0), 3 * n + D.CASE_TABLE_TAIL,
                             f"{n} entries")

    def test_the_table_does_not_consume_a_unit_of_count(self):
        # `count` counts instructions and the table is not one, same as the
        # inline-argument block. A table that ate a unit would silently hand a
        # caller one instruction fewer than it asked for at every such call.
        got = list(D.decode(SHAPE, 0, 2, 0x0F254))
        self.assertEqual([t for _i, _r, t in got],
                         [f"lcall 0x{TARGET:04x}", f"case table: {TABLE_LEN} bytes",
                          "mov  dptr,#0x0e00"])

    def test_a_walk_that_anchors_inside_the_table_decodes_normally(self):
        # The special case keys on the *call*, not on the bytes, as its sibling
        # does: an anchor inside a table is an anchor inside data, and a caller
        # who points the decoder there is asking what is at that offset. The
        # table is not rediscovered from the middle of itself.
        got = [t for _i, _r, t in D.decode(ENTRIES, 0, 4, 0x0F257)]
        self.assertNotIn(f"case table: {TABLE_LEN} bytes", got)

    def test_the_movx_bytes_in_the_table_are_not_sites(self):
        # The claim behind the population change, at the one site the issue
        # named. This table's lead bytes spell `movx @r0,a`/`movx @r1,a` at six
        # offsets, four of which the committed `indirect-xdata-sites.csv` used
        # to report as sites. They are table data, so a walk anchored on the
        # `lcall` must not reach any of them. Pinned on the four offsets rather
        # than on a population, which moves with every re-derivation.
        for off in (3, 6, 9, 12, 15, 18):
            self.assertIn(SHAPE[off], MOVX_BYTES)
        starts = F.anchored_starts(SHAPE, 0, len(SHAPE))
        for off in (3, 6, 9, 12, 15, 18):
            self.assertNotIn(off, starts,
                             f"offset 0x{0x0F257 + off - 3:05X} is inside the "
                             "table and must not be an anchored start")

    def test_stop_at_flow_still_stops_at_the_call(self):
        # The flag exists so a window can end at a branch, and this call is one.
        # Yielding the table first would make `stop_at_flow` mean something it
        # does not.
        got = list(D.decode(SHAPE, 0, 40, 0x0F254, stop_at_flow=True))
        self.assertEqual([t for _i, _r, t in got], [f"lcall 0x{TARGET:04x}"])


class WhatIsNotATable(unittest.TestCase):
    """The two edges a scan creates that a fixed width does not have.

    `test_disasm8051_inline_args.py`'s `BlockAtTheEndOfTheBuffer` holds the
    equivalent contract for the `0x104D` block. Here the table's length is not
    known until the scan finishes, so there are two ways to fail to finish: the
    buffer ends first, and the terminator never arrives."""

    def test_a_table_the_buffer_does_not_hold_whole_is_no_table(self):
        # The four entries with no terminator after them.
        # `case_table_len()` returns 0, so the walk carries on decoding from
        # the instruction after the call and stops at the end of the buffer --
        # the bounds contract, not a fabricated 16-byte table and not a read
        # past the end. Pinned as "no table item was yielded" and as "the walk
        # reached the last byte", which is the two halves of that.
        shape = CALL + ENTRIES
        self.assertEqual(D.case_table_len(shape, 0), 0)
        got = list(D.decode(shape, 0, 20, 0x0F254))
        self.assertNotIn([t for _i, _r, t in got
                          if t.startswith("case table:")], [True])
        self.assertEqual(got[0][0], 0)
        self.assertEqual(got[-1][0] + len(got[-1][1]), len(shape),
                         "the walk must stop at the end of the buffer")

    def test_a_terminator_the_buffer_ends_inside_the_default_is_no_table(self):
        # The near-miss the tail of the scan creates: the `00 00` is there and
        # the default's second byte is not. The block cannot be stepped over
        # whole, so it is not a table -- the same rule, one byte earlier.
        self.assertEqual(D.case_table_len(CALL + ENTRIES + TERMINATOR + DEFAULT[:1], 0), 0)

    def test_a_terminator_that_never_arrives_is_no_table(self):
        # The cap is what bounds the scan, and declining is what it does when
        # the cap is reached: a `lcall` byte pair inside data would otherwise
        # run to the end of the buffer. A `00 00` past the cap is not read, so
        # it cannot rescue the call.
        shape = CALL + entries_of(D.MAX_CASE_ENTRIES + 1) + TERMINATOR + DEFAULT
        self.assertEqual(D.case_table_len(shape, 0), 0)
        # ... and the same shape inside the cap is a table, so the previous case
        # is the cap and not "entries this shape are never a table".
        n = D.MAX_CASE_ENTRIES - 1
        shape = CALL + entries_of(n) + TERMINATOR + DEFAULT
        self.assertEqual(D.case_table_len(shape, 0),
                         3 * n + D.CASE_TABLE_TAIL)

    def test_the_call_alone_at_the_end_of_the_buffer_still_decodes(self):
        self.assertEqual([t for _i, _r, t in D.decode(CALL, 0, 4, 0x0F254)],
                         [f"lcall 0x{TARGET:04x}"])


class OtherCalls(unittest.TestCase):
    """`0x7151` is a name in a table, and a table entry that matched on the
    opcode alone would re-frame every `lcall` in the image."""

    def test_an_lcall_to_another_target_is_unaffected(self):
        other = b"\x12\xe5\xd6" + ENTRIES + TERMINATOR + DEFAULT + RESUME
        got = [t for _i, _r, t in D.decode(other, 0, 3, 0xE580)]
        self.assertEqual(got[0], "lcall 0xe5d6")
        # `f2 70` decoded linearly, which is the mis-framing this table exists
        # to prevent -- and is correct here, because the call it follows is not
        # the named one. Pinned as the `movx @r0,a` those bytes spell rather
        # than as an absence, so a decoder that skipped the table anyway would
        # fail on the value.
        self.assertEqual(got[1], "movx @r0,a")

    def test_the_two_tables_name_disjoint_targets(self):
        # Both mechanisms fire on a `lcall` and both add to the same step, so
        # one call claimed by two entries would be skipped twice over. The
        # claim is disjointness, not a count: a future second row in either
        # table is a new claim about a new address, which is its own test's
        # business.
        self.assertEqual(set(D.CASE_TABLE_CALLS) & set(D.INLINE_ARG_CALLS), set())

    def test_walk_why_stops_on_the_call_and_never_crosses_it(self):
        # `walk_why()` consults `case_table_len()` for the same reason
        # `converges_from()` does, and for the same reason it cannot currently
        # fire: the call is a flow opcode, so the walk returns at it. Pinned
        # because the guard is a latent one, and a change that relaxed the flow
        # stop would otherwise re-frame every row behind such a call with the
        # `access` cell still reading as an answer.
        window = b"\x90\x0e\x00" + SHAPE
        insns, why = T.walk_why(window, 0)
        self.assertEqual(why, T.FLOW_END)
        self.assertEqual([i for i, _r, _t in insns], [0, 3])


class AgainstTheCommittedSpans(unittest.TestCase):
    """The rule's evidence: the 15 committed tables, extent for extent.

    `../annotations/index-table-spans.csv` is produced by `decode_index_table.py`
    by a route that never calls `case_table_len()` -- it finds the reader from
    its opcode prologue, counts entries off the same `00 00` rule, and checks
    each table for well-formedness. So when the two agree row for row, the
    agreement is corroboration rather than a restatement, and a drift in either
    fails here instead of passing silently to the next reader."""

    def test_the_scan_reproduces_every_committed_extent(self):
        d = FIRMWARE.read_bytes()
        rows = list(csv.DictReader(SPANS_CSV.open()))
        self.assertTrue(rows, f"{SPANS_CSV} has no rows to check against")
        for r in rows:
            site = int(r["site"], 16)
            n = D.case_table_len(d, site)
            entries = (n - D.CASE_TABLE_TAIL) // WIDTH if n else None
            self.assertEqual(
                (n, entries, site + 3 + n if n else None),
                (3 * int(r["entries"]) + D.CASE_TABLE_TAIL, int(r["entries"]),
                 int(r["table_end"], 16)),
                f"the scan and {SPANS_CSV.name} disagree about the table at "
                f"{r['site']}")

    def test_every_committed_span_lies_inside_a_call_the_scan_recognises(self):
        # The other direction, and the one a "the table is skipped" test cannot
        # make: the walk must actually *stop* on the committed spans, not merely
        # measure them. Asserted per region over `anchored_starts()` rather than
        # as a count, so a landing population moving does not fail this.
        d = FIRMWARE.read_bytes()
        spans = [(int(r["table_file_offset"], 16), int(r["table_end"], 16))
                 for r in csv.DictReader(SPANS_CSV.open())
                 if r["well_formed"] == "yes"]
        for region, lo, hi, base, _how in T.REGIONS:
            if base is None:
                continue
            starts = F.anchored_starts(d, lo, hi)
            for lo_t, hi_t in spans:
                inside = [i for i in starts if lo_t <= i < hi_t]
                self.assertEqual(inside, [],
                                 f"region {region}: {len(inside)} anchored "
                                 f"start(s) inside the committed table span "
                                 f"0x{lo_t:05X}-0x{hi_t:05X}, first at "
                                 f"{[hex(i) for i in inside[:3]]}")

    def test_the_real_site_the_issue_named_is_one_of_them(self):
        # `0x0F254` is the site the issue's four bank-0 rows came from, so it is
        # the one whose removal is a claim about this repository's own table
        # rather than about a shape. The fixture above is these bytes, so
        # asserting that the image holds them says the hand-transcription and
        # the scan agree on the same span.
        d = FIRMWARE.read_bytes()
        site = 0x0F254
        self.assertEqual(d[site:site + 3], CALL)
        n = D.case_table_len(d, site)
        self.assertEqual(n, TABLE_LEN)
        self.assertEqual(d[site + 3:site + 3 + TABLE_LEN],
                         SHAPE[3:3 + TABLE_LEN])
        end = site + 3 + n
        self.assertEqual(d[end:end + 3], RESUME,
                         "the walk must resume on the instruction after the "
                         "default, not on the default")
        starts = F.anchored_starts(d, site, end + 3)
        self.assertIn(site, starts, "the call itself is an anchored start")
        self.assertIn(end, starts, "and so is the instruction it resumes on")


if __name__ == '__main__':
    unittest.main()
