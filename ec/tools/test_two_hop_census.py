#!/usr/bin/env python3
"""Offline checks for the two hops `register_ref_table.py` took to reach a
direction, and for the census that records which cells took them: no hardware,
and for the parts that would need a live read nothing but the committed
firmware.

The oracle is split in two on purpose, the way `test_walk_flow_follow.py` and
`test_callee_depth.py` split theirs. Everything asserted about the committed
image is asserted **against the image**, with the expected verdicts and
windows transcribed by hand from `r2 -a 8051` transcripts -- `0x34A5` and the
`0x10C8` family are already transcribed in `ec-0x07d0-sites.md` 3 and
`lightbar-bat-flow.md` 3.5, and the rest are reproduced in
`../../docs/findings/two-hop-dptr-handoff.md` -- so the answers do not come
from the code under test. Everything the image cannot show is a byte fixture
in the `common` region, whose file offset equals its runtime address, so a
case keeps testing what it was written to test if the bytes around some address
in the image change.

The fixtures are for the load-bearing part. The committed image's `other->flow`
population settles at its first callee for every cell that settles at all, and
its longest handoff chain is two links, so **neither** new column's *negative*
shape is exercised by the image: no flow cell's callee writes or reads+writes,
and no flow row takes two hops. A `FLOW_CALLEE_CLASSES` that resolved writes
into `->read`, or a second-pass `classes_for()` that dropped a label, would
pass every image-derived case here and be wrong. That is why the write /
r+w / two-hop / unreachable cases are built rather than read.
"""
import collections
import contextlib
import csv
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
# register_ref_table imports trace_xdata_refs and walk_flow_follow by bare
# module name, so the tool directory has to be on the path before they load.
sys.path.insert(0, str(HERE))

import register_ref_table as rrt           # noqa: E402  (needs the path above)
import trace_xdata_refs as txr             # noqa: E402  (needs the path above)
import two_hop_census as thc               # noqa: E402  (needs the path above)
import walk_flow_follow as wff             # noqa: E402  (needs the path above)

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')
CENSUS = HERE.parent / 'annotations' / 'two-hop-dptr-handoffs.csv'

# --------------------------------------------------------------------------
# Opcodes, as bytes. Module-level rather than inline in an asserting call:
# check_doc_figure_pins.py reads every int inside an assertEqual /
# assertIn argument as a candidate claim about a counted figure in some
# document, and an opcode or a fixture address is not one. test_callee_depth.py
# writes the same rule next to its own fixtures.
MOV_DPTR = 0x90        # the site form: mov dptr, #imm16
MOVX_A_DPTR = 0xE0     # movx a,@dptr -- the read every read verdict rests on
MOVX_DPTR_A = 0xF0     # movx @dptr,a -- the store
LCALL = 0x12           # the handoff form
SJMP = 0x80            # the unconditional branch a `flow` row can be reached by
RET = 0x22             # what stops walk() at a routine's end

READS = "handed to lcall/ljmp -> callee reads"
SECOND_READS = "handed to lcall/ljmp -> second callee reads"
HANDOFF = rrt.HANDOFF
NONE = rrt.NONE


def _labels(*classes):
    return [label for label, _ in classes]


class ImageTwoHopTests(unittest.TestCase):
    """The two shapes, asserted against the committed image with verdicts
    transcribed from `r2 -a 8051` rather than from this repository's tools."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        off, magic = txr.PD_MARKER
        cls.pd = cls.d[off:off + len(magic)] == magic
        import yaml
        with open(rrt.DEFAULT_YAML) as f:
            cls.regs = yaml.safe_load(f)["registers"]

    def rows(self, addr, depth, follow_flow=False):
        return list(rrt.site_rows(self.d, addr, self.pd, depth, follow_flow))

    # -- shape 1: a handoff the follow reached, then one call ----------------

    def test_the_flow_columns_resolve_the_cell_the_issue_named(self):
        # `docs/findings/walk-flow-follow.md` 2 recorded the 0x4B40 cell as
        # direction-unresolved because the resolver never saw it. The row now
        # carries a direction AND both hop names -- `flow_via` for the branch
        # and `callee` for the call -- which is the issue's "Done when".
        rows = [r for r in self.rows(0x07D0, 1, True) if r[0] == 0x24B40]
        self.assertEqual(len(rows), 1)
        o, _region, rt, label, callee, window, win2, via, _chain, _stop = rows[0]
        self.assertEqual(rt, 0x4B40)
        self.assertEqual(via, "fall-through past jnz +0x12 at 0x4B43")
        self.assertEqual(callee, 0x34A5)
        # r2 -a 8051 -c 's 0x4b40; pd 3' against the flat PD image, and
        # `s 0x34a5; pd 1` for the callee: `e0  movx a, @dptr`.
        self.assertEqual(window, "movx a,@dptr")
        self.assertEqual(label, rrt.FLOW_CALLEE_CLASSES[0][0])
        # The `window` column is still the site's own, not the callee's: the
        # committed --follow-flow tables carry that spelling.
        self.assertEqual(win2, "jnz +0x12")

    def test_every_flow_row_is_read_and_says_so_in_its_own_column(self):
        # The census of shape 1, checked against the image rather than against
        # the census file: each cell named by the committed table must still be
        # a read, at the address that file records.
        with open(CENSUS, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r["mode"] == "flow"]
        self.assertTrue(rows, "no flow rows in the committed census")
        want = rrt.FLOW_CALLEE_CLASSES[0][0]
        for r in rows:
            addr, off = int(r["addr"], 16), int(r["file_offset"], 16)
            row = [x for x in self.rows(addr, 1, True) if x[0] == off]
            self.assertEqual(len(row), 1, f"{r['addr']} at {r['file_offset']}")
            self.assertEqual(row[0][3], want, f"{r['addr']} at {r['file_offset']}")
            self.assertEqual(row[0][7], r["via"], "the branch is not the one recorded")
            self.assertEqual(f"0x{row[0][4]:04X}", r["callee"])

    def test_a_flow_row_names_both_hops_and_neither_column_is_the_strong_one(self):
        # The whole point of the columns: the claim is branch-then-call, which
        # is weaker than either one-hop column, so it shares neither.
        strong = {l for l, _ in rrt.CLASSES} | {l for l, _ in rrt.HANDOFF_CLASSES}
        for label, _short in rrt.FLOW_CALLEE_CLASSES[:4]:
            self.assertNotIn(label, strong)
        weak = [s for _, s in rrt.FLOW_CALLEE_CLASSES]
        self.assertEqual(weak[:4],
                         ["other->flow->read", "other->flow->write",
                          "other->flow->r+w", "other->flow->unresolved"])

    def test_the_follow_alone_column_is_unchanged_next_to_the_new_ones(self):
        # `--follow-flow` without `--callee-depth` still prints `other->flow`,
        # because at that bound there is no callee budget to resolve with.
        rows = [r for r in self.rows(0x07D0, 0, True) if r[0] == 0x24B40]
        self.assertEqual(rows[0][3], rrt.FLOW_CLASSES[3][0])
        self.assertIsNone(rows[0][4])

    # -- shape 2: a callee that forwards DPTR on again ------------------------

    def test_the_depth2_rows_carry_the_second_callee_and_the_weaker_label(self):
        # The two LIGHTBAR_BAT_* cells `static-refs-audit.md` 5.2 named, plus
        # the three that moved with them. The label is the depth-2 one: a cell
        # only the second hop settled is a weaker claim and cannot print in the
        # one-hop column.
        want = {
            (0x07E2, 0x204F9): (0xB1F2, 0x10C8, SECOND_READS),
            (0x07E5, 0x2662D): (0x383A, 0x0FCB, SECOND_READS),
            (0x089E, 0x0B6E8): (0xBADE, 0x70E4,
                                "handed to lcall/ljmp -> second callee reads+writes"),
            (0x0811, 0x2B5F9): (0x9A48, 0x10C8, SECOND_READS),
            (0x07D6, 0x2951B): (0xB2F7, 0x10C8, SECOND_READS),
        }
        for (addr, off), (first, second, label) in want.items():
            row = [r for r in self.rows(addr, 2) if r[0] == off]
            self.assertEqual(len(row), 1, f"0x{addr:04X} at 0x{off:05X}")
            self.assertEqual(row[0][8], (first, second), f"0x{addr:04X}")
            self.assertEqual(row[0][3], label, f"0x{addr:04X} at 0x{off:05X}")

    def test_a_depth1_row_of_the_same_cell_is_still_unresolved(self):
        # The split is not a rename of an existing column: at depth 1 this cell
        # resolves to nothing, and at depth 2 it lands in the *weaker* column
        # rather than in the one-hop `handoff->read` beside it.
        one = [r for r in self.rows(0x07E2, 1) if r[0] == 0x204F9]
        self.assertEqual(one[0][3], HANDOFF)
        two = [r for r in self.rows(0x07E2, 2) if r[0] == 0x204F9]
        self.assertEqual(two[0][3], rrt.HANDOFF_DEPTH2_CLASSES[3][0])
        self.assertNotIn(two[0][3], [l for l, _ in rrt.HANDOFF_CLASSES])

    def test_a_cell_that_settles_at_its_first_callee_keeps_the_depth1_column(self):
        # The other half of the split, on a cell the image does contain: a
        # one-link resolution must not drift into the depth-2 column at depth 2,
        # or every cell would print as two hops.
        off = 0x23AD5
        one = [r for r in self.rows(0x07D0, 1) if r[0] == off]
        two = [r for r in self.rows(0x07D0, 2) if r[0] == off]
        self.assertEqual(len(one), 1)
        self.assertEqual(len(two), 1)
        self.assertEqual(len(one[0][8]), 1)
        self.assertEqual(one[0][3], rrt.HANDOFF_CLASSES[0][0])
        # Same cell, same column, at the deeper bound: the split keys on the
        # chain and not on the depth asked for.
        self.assertEqual(two[0][3], rrt.HANDOFF_CLASSES[0][0])

    def test_the_0x10c8_forwarders_stay_unresolved_at_depth_1(self):
        # `0x04A6`'s four PD handoffs reach `0x10BC`, which adds to DPTR without
        # dereferencing it. The cap has to keep them in the unresolved bucket
        # rather than promote them on a second hop that cannot settle them.
        for off in txr.sites_for(self.d, 0x04A6):
            row = [r for r in self.rows(0x04A6, 2) if r[0] == off]
            if row[0][3] != HANDOFF:
                continue
            self.assertNotIn("->read", row[0][3])
            self.assertNotIn("->write", row[0][3])


class ByteIdentityTests(unittest.TestCase):
    """Depth 0, depth 1 and `--follow-flow` alone are unchanged -- structurally,
    not by a digest of the whole output, because a digest is a value every
    registers.yaml addition has to edit. The rows are rebuilt the way
    `test_walk_flow_follow.py::rows_the_pre_flag_way` rebuilds them, over the
    whole of registers.yaml as it stands."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        off, magic = txr.PD_MARKER
        cls.pd = cls.d[off:off + len(magic)] == magic
        import yaml
        with open(rrt.DEFAULT_YAML) as f:
            cls.regs = yaml.safe_load(f)["registers"]
        # One build per mode, shared by every case below. Each is a full walk
        # of every site of every address, and rebuilding the same table once
        # per assertion would cost more than the assertions are worth.
        cls.tables = {}
        for depth, follow in ((0, False), (1, False), (2, False),
                              (1, True), (2, True)):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rrt.write_csv(cls.d, cls.regs, cls.pd, depth, follow)
            cls.tables[(depth, follow)] = buf.getvalue()

    def table(self, depth, follow_flow):
        """The whole `--csv` output of one mode, as a string.

        Driven through write_csv() rather than a subprocess so a failure names
        the assertion instead of an exit code, and so the header can be read
        without re-parsing a table this size.
        """
        return self.tables[(depth, follow_flow)]

    def test_depth_0_and_1_csv_headers_are_unchanged(self):
        # The columns, not the values: `callee2` belongs to the composition --
        # two hops *and* a branch -- so no mode that the committed tables use
        # may have gained it.
        self.assertNotIn("callee2", self.table(0, False).splitlines()[0])
        self.assertNotIn("callee2", self.table(1, False).splitlines()[0])
        self.assertNotIn("callee2", self.table(1, True).splitlines()[0])
        # depth 1's header is exactly the committed one, columns included.
        self.assertEqual(self.table(1, False).splitlines()[0].split(","),
                         ["addr", "register", "file_offset", "region",
                          "runtime", "class", "window", "callee",
                          "callee_window"])
        self.assertEqual(self.table(0, False).splitlines()[0].split(","),
                         ["addr", "register", "file_offset", "region",
                          "runtime", "class", "window"])

    def test_depth_2_alone_adds_chain_and_stop_but_not_callee2(self):
        header = self.table(2, False).splitlines()[0]
        self.assertIn("chain,stop", header)
        # `callee2` is for the composition -- two hops *and* a branch -- so it
        # appears only when both flags are given.
        self.assertNotIn("callee2", header)

    def test_the_composition_adds_callee2(self):
        header = self.table(2, True).splitlines()[0]
        self.assertIn("callee2", header)
        self.assertIn("flow_via", header)

    def test_the_first_seven_columns_are_the_same_table_at_every_depth(self):
        # A reader's `cut -d, -f6` keeps working, which is what keeps the new
        # columns additive rather than a reshuffle.
        first = self.table(0, False).splitlines()[0].split(",")[:7]
        for depth, follow in ((1, False), (2, False), (1, True), (2, True)):
            self.assertEqual(self.table(depth, follow).splitlines()[0]
                             .split(",")[:7], first)

    def test_depth_2_alone_is_the_committed_table_plus_chain_and_stop(self):
        # What `--callee-depth 2` prints, column for column, so a change to the
        # header names itself here rather than in a transcript nobody diffs.
        header = self.table(2, False).splitlines()[0].split(",")
        self.assertEqual(header[:9], self.table(1, False)
                         .splitlines()[0].split(","))
        self.assertEqual(header[9:], ["chain", "stop"])


class ColumnArithmeticTests(unittest.TestCase):
    """One column in, N out, in place -- and the columns after the one replaced
    do not move, which is what makes the new columns additive."""

    def test_one_column_in_and_n_out_in_place(self):
        self.assertEqual(len(rrt.classes_for(0)), len(rrt.CLASSES))
        # depth 1: HANDOFF (1) -> HANDOFF_CLASSES
        self.assertEqual(len(rrt.classes_for(1)),
                         len(rrt.CLASSES) - 1 + len(rrt.HANDOFF_CLASSES))
        # depth 2: the same one-in, and HANDOFF_DEPTH2_CLASSES carries both the
        # depth-1 labels and the weaker ones beside them.
        self.assertEqual(len(rrt.classes_for(2)),
                         len(rrt.CLASSES) - 1 + len(rrt.HANDOFF_DEPTH2_CLASSES))
        # --follow-flow alone: NONE (1) -> FLOW_CLASSES
        self.assertEqual(len(rrt.classes_for(0, True)),
                         len(rrt.CLASSES) - 1 + len(rrt.FLOW_CLASSES))
        # Both flags: the same NONE replacement, then a second pass over its
        # product replacing the inner `other->flow` (1) ->
        # FLOW_CALLEE_CLASSES. One column in, N out, twice over.
        self.assertEqual(len(rrt.classes_for(1, True)),
                         len(rrt.CLASSES) - 1 + len(rrt.FLOW_CLASSES)
                         - 1 + len(rrt.FLOW_CALLEE_CLASSES)
                         - 1 + len(rrt.HANDOFF_CLASSES))

    def test_no_column_is_named_twice_in_any_mode(self):
        # reconcile() keys its unbucketed check on the label set, and the
        # markdown is a group-by over the same tuple, so a duplicate would
        # print the same header twice and count one bucket into two cells.
        for depth in (0, 1, 2, 3):
            for follow in (False, True):
                labels = _labels(*rrt.classes_for(depth, follow))
                self.assertEqual(len(labels), len(set(labels)),
                                 f"depth={depth} follow={follow}")

    def test_the_untouched_tuples_keep_their_names_members_and_order(self):
        # test_walk_flow_follow.py indexes FLOW_CLASSES[0] and [3], and both
        # tuples are what the committed tables' column order is built from.
        self.assertEqual(rrt.FLOW_CLASSES[0][1], "read->flow")
        self.assertEqual(rrt.FLOW_CLASSES[3][1], "other->flow")
        self.assertEqual(_labels(*rrt.FLOW_CLASSES)[:3],
                         ["read reached only by following a branch",
                          "write reached only by following a branch",
                          "read+write reached only by following a branch"])
        self.assertEqual([s for _, s in rrt.HANDOFF_CLASSES],
                         ["handoff->read", "handoff->write", "handoff->r+w",
                          "handoff->unresolved"])
        self.assertEqual(_labels(*rrt.CLASSES),
                         ["read", "write", "read+write", "movc (CODE pointer)",
                          "jmp @a+dptr", HANDOFF, NONE])

    def test_flow_bucket_is_not_modified_by_the_new_columns(self):
        # The sibling suite asserts these directly; they are the reason the
        # re-bucketing happens in site_rows() rather than in flow_bucket().
        self.assertEqual(rrt.flow_bucket("DPTR handed to lcall 0x1 -- "
                                         "direction unresolved here"),
                         rrt.FLOW_CLASSES[3][0])
        self.assertNotEqual(rrt.flow_bucket("DPTR handed to lcall 0x1"),
                            HANDOFF)
        self.assertEqual(rrt.flow_bucket("read x1"), rrt.FLOW_CLASSES[0][0])

    def test_the_new_columns_are_weaker_than_the_one_beside_them(self):
        # Asserted as the property, not as a count: every label the two-hop
        # columns introduce is one no one-hop table already uses, so nothing
        # downstream can average the two or read one as the other. The
        # depth-1 labels are deliberately *not* new -- HANDOFF_DEPTH2_CLASSES
        # reuses them for the cells that settled at the first callee, which is
        # what keeps a depth-2 run comparable with a depth-1 one.
        strong = {l for l, _ in rrt.CLASSES} | {l for l, _ in rrt.HANDOFF_CLASSES}
        introduced = ([l for l, _ in rrt.FLOW_CALLEE_CLASSES]
                      + [l for l, _ in rrt.HANDOFF_DEPTH2_CLASSES[3:6]])
        self.assertTrue(introduced, "no new labels to check")
        for label in introduced:
            self.assertNotIn(label, strong, label)
        self.assertEqual(rrt.HANDOFF_DEPTH2_CLASSES[:3],
                         rrt.HANDOFF_CLASSES[:3])


class PartitionTests(unittest.TestCase):
    """The new buckets are in classes_for(), so reconcile() still passes over
    the whole file, and still fails loudly on a class nothing is named for."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        off, magic = txr.PD_MARKER
        cls.pd = cls.d[off:off + len(magic)] == magic
        import yaml
        with open(rrt.DEFAULT_YAML) as f:
            cls.regs = yaml.safe_load(f)["registers"]

    def test_reconcile_returns_zero_in_every_mode(self):
        for depth, follow in ((0, False), (1, False), (2, False),
                              (1, True), (2, True)):
            classes = rrt.classes_for(depth, follow)
            problems = 0
            for name, addr in rrt.addresses(self.regs):
                rows = list(rrt.site_rows(self.d, addr, self.pd, depth, follow))
                total, main, pd, hist = rrt.row_for(self.d, addr, self.pd, rows)
                with contextlib.redirect_stderr(io.StringIO()):
                    problems += rrt.reconcile(name, addr, total, main, pd,
                                              hist, classes)
            self.assertEqual(problems, 0, f"depth={depth} follow={follow}")

    def test_every_row_carries_exactly_one_column(self):
        # The partition the markdown is a group-by over: no site may land
        # outside the tuple, or reconcile() above would already have said so,
        # and none may land in two.
        for depth, follow in ((1, True), (2, True), (2, False)):
            labels = set(_labels(*rrt.classes_for(depth, follow)))
            for name, addr in rrt.addresses(self.regs):
                for r in rrt.site_rows(self.d, addr, self.pd, depth, follow):
                    self.assertIn(r[3], labels, f"0x{addr:04X} at 0x{r[0]:05X}")

    def test_reconcile_still_fails_loudly_on_an_unbucketed_class(self):
        # The check the issue says must keep passing, on the class set the new
        # columns produce -- asserted directly with the message captured, the
        # way test_walk_flow_follow.py does it.
        classes = rrt.classes_for(2, True)
        hist = collections.Counter({"read": 3, "callee sideways": 1})
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            problems = rrt.reconcile("X", 0x1234, 4, 4, 0, hist, classes)
        self.assertEqual(problems, 1)
        self.assertIn("unbucketed class(es)", err.getvalue())
        self.assertIn("callee sideways", err.getvalue())


# ---------------------------------------------------------------------------
# Fixtures. The `common` region, where file offset == runtime address, so a
# case keeps testing what it was written to test if the image's bytes move.
# Every routine ends in `ret`, which is what stops walk() there: a window that
# runs into the zero fill would decode 0x00 as a two-byte opcode and read off
# the end of the buffer. test_callee_depth.py builds its fixtures the same way.
# ---------------------------------------------------------------------------

SITE = 0x0030          # mov dptr,#imm16 ; lcall CALLEE
CALLEE = 0x0040        # the routine the handoff names
SECOND = 0x0050        # the routine a forwarder names
SIZE = 0x0060
# The register these fixtures are tabulated under. `sites_for()` finds a site
# by matching the `mov dptr` *operand* against the address, so the immediate
# has to be this value or there is no row to classify.
SITE_ADDR = 0x0999


def at(*bodies) -> bytes:
    """A flat `common`-region image from (offset, raw) pairs."""
    img = bytearray(SIZE)
    for off, raw in bodies:
        img[off:off + len(raw)] = raw
    return bytes(img)


def lcall_to(target: int) -> bytes:
    """`lcall <target>`. The operand is little-endian -- call_target() reads it
    back swapped -- so a target is packed high byte first."""
    return bytes([LCALL, target >> 8, target & 0xFF])


def mov_dptr(addr: int) -> bytes:
    """`mov dptr,#addr`. Big-endian here, the operand order sites_for() reads."""
    return bytes([MOV_DPTR, addr >> 8, addr & 0xFF])


def site(target: int) -> tuple:
    """`mov dptr,#SITE_ADDR` then `lcall target`: the depth-0 HANDOFF shape."""
    return (SITE, mov_dptr(SITE_ADDR) + lcall_to(target))


class FixtureShapeTests(unittest.TestCase):
    """The shapes the committed image does not contain: a callee that writes,
    one that reads and writes, one that hands DPTR on a second time, one that
    is not reachable, a `movc` past a branch with no callee at all, and a
    first callee with no call in it -- which must take no second hop."""

    def resolve(self, img: bytes, depth=1):
        return rrt.resolve_handoff(img, SITE, txr.walk(img, SITE), True, depth)

    def test_a_callee_that_writes_is_write_not_read(self):
        img = at(site(CALLEE), (CALLEE, bytes([MOVX_DPTR_A, RET])))
        label, callee, _w, _c, _s = self.resolve(img)
        self.assertEqual(label, rrt.HANDOFF_CLASSES[1][0])
        self.assertEqual(callee, CALLEE)

    def test_a_callee_that_reads_and_writes_is_rw(self):
        img = at(site(CALLEE),
                 (CALLEE, bytes([MOVX_A_DPTR, MOVX_DPTR_A, RET])))
        label, _callee, _w, _c, _s = self.resolve(img)
        self.assertEqual(label, rrt.HANDOFF_CLASSES[2][0])

    def test_a_callee_with_no_call_in_it_takes_no_second_hop(self):
        # A first callee that decoded to no movx has no call to follow, which
        # is a different shrug from one that had a call that did not settle --
        # so the chain stops at one link rather than growing.
        img = at(site(CALLEE), (CALLEE, bytes([0xD8, 0x82, RET])))
        label, callee, _window, chain, stop = self.resolve(img)
        self.assertEqual(label, HANDOFF)
        self.assertEqual(callee, CALLEE)
        self.assertEqual(len(chain), 1)
        self.assertIn("no direction at", stop)
        self.assertNotIn("callee-depth", stop)

    def test_a_forwarder_at_depth_1_is_unresolved_and_at_depth_2_is_read(self):
        # The shape the two `LIGHTBAR_BAT_*` cells have in the image, built
        # here because the image's own forwarders all settle at their second
        # callee and so never exercise the negative arm at depth 1.
        img = at(site(CALLEE),
                 (CALLEE, bytes([MOV_DPTR, 0x99, 0x99]) + lcall_to(SECOND) + bytes([RET])),
                 (SECOND, bytes([MOVX_A_DPTR, 0xA3, MOVX_A_DPTR, RET])))
        one = self.resolve(img, depth=1)
        self.assertEqual(one[0], HANDOFF)
        # STOP_CAP is the template; the row carries it formatted, naming the
        # depth that was asked for rather than the budget left over.
        self.assertEqual(one[4], rrt.STOP_CAP.format(depth=1))
        two = self.resolve(img, depth=2)
        self.assertEqual(two[0], READS)
        self.assertEqual(two[3], (CALLEE, SECOND))

    def test_depth2_bucket_moves_only_a_two_link_resolution(self):
        # The split is the weaker column for a two-hop chain and nothing else:
        # a one-link resolution and the unresolved bucket both pass through
        # unchanged, or the depth-1 columns would move.
        self.assertEqual(rrt.depth2_bucket(READS, (CALLEE,)), READS)
        self.assertEqual(rrt.depth2_bucket(READS, (CALLEE, SECOND)),
                         rrt.HANDOFF_DEPTH2_CLASSES[3][0])
        self.assertEqual(rrt.depth2_bucket(HANDOFF, (CALLEE,)), HANDOFF)
        self.assertEqual(rrt.depth2_bucket(READS, None), READS)
        self.assertEqual(rrt.depth2_bucket(READS, ()), READS)

    def test_an_unreachable_callee_is_unresolved_not_a_direction(self):
        # A target outside the mapped regions: the resolver has to name the
        # reason rather than return a direction it cannot support.
        img = at(site(0xFFF0))
        label, _callee, window, _c, stop = self.resolve(img, depth=2)
        self.assertEqual(label, HANDOFF)
        self.assertIn("not reachable", window + stop)

    def test_a_movc_past_a_branch_has_no_callee_and_keeps_the_old_label(self):
        # The residue the `other->flow` column survives for: the follow found a
        # `movc`, which is a verdict and not a handoff, so there is no callee
        # to resolve and the cell must not gain a `->callee` column.
        img = at((SITE, mov_dptr(SITE_ADDR)),
                 (SITE + 3, bytes([SJMP, 0x02])),      # skip two bytes
                 (SITE + 7, bytes([0x93, RET])))       # movc a,@a+dptr ; ret
        f = wff.follow_site(img, SITE_ADDR, SITE, True)
        self.assertEqual(rrt.bucket(f.linear), NONE)
        self.assertEqual(rrt.flow_bucket(f.followed), rrt.FLOW_CLASSES[3][0])
        rows = list(rrt.site_rows(img, SITE_ADDR, True, 1, True))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], rrt.FLOW_CLASSES[3][0])
        self.assertIsNone(rows[0][4], "a movc has no callee to resolve")


class CLITests(unittest.TestCase):
    """The census reproduces its committed file, and refuses what it cannot
    regenerate rather than going green on rows it never compared."""

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(HERE / "two_hop_census.py"),
                               *args], capture_output=True, text=True)

    def test_check_reproduces_the_committed_census_byte_for_byte(self):
        r = self.run_tool("--check")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("reproduces it byte for byte", r.stdout)

    def test_check_regenerates_every_recorded_mode_whatever_mode_says(self):
        # The bug this pins: `--check --mode flow` once diffed a single-mode
        # regeneration against the whole file and reported the depth2 rows as
        # drift, so `--check` looked broken for both of its modes. --mode
        # narrows what is printed and nothing else.
        for mode in sorted(thc.MODES):
            r = self.run_tool("--check", "--mode", mode)
            self.assertEqual(r.returncode, 0, f"--mode {mode}: {r.stderr}")
            self.assertIn("reproduces it byte for byte", r.stdout)

    def test_a_mode_the_file_records_that_this_tool_lacks_is_refused(self):
        # The one thing --check does refuse. Such rows cannot be regenerated
        # at all, so dropping them would look like a clean run.
        self.assertEqual(sorted(thc.MODES), ["depth2", "flow"])
        recorded = thc.load_recorded_modes(str(CENSUS))
        self.assertEqual(recorded, set(thc.MODES),
                         "the committed census holds a mode the tool lacks")

    def test_a_file_that_is_not_one_of_its_tables_is_refused(self):
        other = HERE.parent / "annotations" / "site-resolution.csv"
        with self.assertRaises(ValueError) as cm:
            thc.load_recorded_modes(str(other))
        self.assertIn("no 'mode' column", str(cm.exception))

    def test_a_file_that_is_not_one_of_its_tables_is_refused(self):
        other = HERE.parent / "annotations" / "site-resolution.csv"
        with self.assertRaises(ValueError) as cm:
            thc.load_recorded_modes(str(other))
        self.assertIn("no 'mode' column", str(cm.exception))

    def test_a_doctored_copy_is_red_through_the_diff_path(self):
        # The committed file is never edited to prove this: the copy is
        # doctored, so a --check that went green would be going green on a
        # census it never compared.
        text = CENSUS.read_text()
        doctored = text.replace("0x34A5", "0xFFFF")
        self.assertNotEqual(text, doctored, "the doctored copy is unchanged")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doctored.csv"
            path.write_text(doctored)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = thc.check_table(text, str(path))
        self.assertEqual(rc, 1)
        self.assertIn("differs", err.getvalue())

    def test_a_buffer_without_the_pd_marker_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.bin"
            path.write_bytes(bytes(0x30000))
            r = self.run_tool(str(path))
        self.assertEqual(r.returncode, 1)
        self.assertIn("marker", r.stderr)

    def test_the_human_output_carries_the_calibration_sentence(self):
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("not found by this method", r.stdout)
        self.assertIn("never 'absent'", r.stdout)
        self.assertIn("0x07B9", r.stdout)
        self.assertIn("Nothing here is measured on hardware", r.stdout)

    def test_both_modes_are_reachable_and_each_is_held_at_its_own_bound(self):
        for mode in thc.MODES:
            _classes, depth, follow_flow = thc.MODES[mode]
            self.assertGreaterEqual(depth, 1)
            self.assertIsInstance(follow_flow, bool)
        self.assertEqual(sorted(thc.MODES), ["depth2", "flow"])

    def test_the_committed_census_records_both_modes(self):
        with open(CENSUS, newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual({r["mode"] for r in rows}, set(thc.MODES))
        self.assertEqual(list(rows[0]), list(thc.COLUMNS))


class TokenTests(unittest.TestCase):
    """`END_HANDOFF` is what `continuation()` prints, and it used to promise a
    resolution `--callee-depth 1` does not perform on its own."""

    def test_the_token_names_both_resolutions(self):
        self.assertIn("--callee-depth 1", wff.END_HANDOFF)
        self.assertIn("--follow-flow", wff.END_HANDOFF)
        # The promise it must not make any more: that depth 1 alone reaches a
        # handoff the follow had to be used to find.
        self.assertNotIn("--callee-depth 1 resolves those", wff.END_HANDOFF)

    def test_follow_carries_the_final_segment_for_the_resolver(self):
        # `res.blocks` holds runtime addresses and rendered text, so a caller
        # cannot get the file offset resolve_handoff() needs from it. This is
        # the attribute that carries it, and it is the last segment, which is
        # where the verdict came from.
        img = at((SITE, mov_dptr(SITE_ADDR)),
                 (SITE + 3, bytes([SJMP, 0x03])),
                 (SITE + 8, bytes([MOVX_A_DPTR, RET])))
        f = wff.follow_site(img, SITE_ADDR, SITE, True)
        self.assertEqual(f.final[0][0], SITE + 8)
        self.assertEqual(f.anchor[0][0], SITE)
        self.assertNotEqual(f.final, f.anchor, "the follow moved the verdict")

    def test_final_equals_anchor_when_the_site_resolves_where_it_sits(self):
        img = at((SITE, mov_dptr(SITE_ADDR) + bytes([MOVX_A_DPTR])))
        f = wff.follow_site(img, SITE_ADDR, SITE, True)
        self.assertEqual(f.final, f.anchor)
        self.assertEqual(f.via_cell, wff.VIA_SITE)


if __name__ == "__main__":
    unittest.main()
