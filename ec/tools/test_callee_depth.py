#!/usr/bin/env python3
"""Offline checks for `register_ref_table.py --callee-depth N`: no hardware,
and for the parts that would need a live read nothing but the committed
firmware.

The oracle is split in two on purpose. Everything asserted about the committed
image is asserted **against the image**, with the expected verdicts
transcribed by hand from the `r2 -a 8051` transcripts
`../annotations/lightbar-bat-flow.md` 3.5 already commits, so the answers do
not come from the code under test. Everything the image cannot show -- the
cycle, and the cap -- builds its own byte fixtures in the `common` region,
whose file offset equals its runtime address, so a case keeps testing what it
was written to test if the bytes around some address in the image change.

What the fixtures are for is the load-bearing part: the committed image's
longest handoff chain is two links, so depths 2, 3, 4 and 8 produce
byte-identical rows and *neither guard in this feature is ever exercised by
it*. A depth-N recursion with no cycle check passes every image-derived case
here and then hangs on the first loop a future image contains; a cap that
never fires is untested in the only sense that matters. That is why the last
two cases are built rather than read, per `test_walk_flow_follow.py`'s stated
reason: a fixture anchored at an address keeps testing what it was written to
test only until the bytes there change.
"""
import collections
import contextlib
import csv
import io
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).parent
# register_ref_table imports trace_xdata_refs and walk_flow_follow by bare
# module name, so the tool directory has to be on the path before they load.
sys.path.insert(0, str(HERE))

import register_ref_table as rrt           # noqa: E402  (needs the path above)
import trace_xdata_refs as txr             # noqa: E402

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')

# The two sites the issue names, and the four the run moves with them. The
# file offsets are the sites; the runtime addresses and the chains are
# transcribed from lightbar-bat-flow.md 3.5's `r2` listing of each callee,
# not from the tool.
NAMED = {
    0x07E2: (0x204F9, 0xB1F2, 0x10C8, "handed to lcall/ljmp -> callee reads"),
    0x07E5: (0x2662D, 0x383A, 0x0FCB, "handed to lcall/ljmp -> callee reads"),
}
# The three more the run moves that the issue does not name. Same shape: the
# chain's first link is the callee depth 1 already reported, the second is
# what depth 2 reaches and depth 1 could not.
ALSO_MOVING = {
    0x089E: (0x0B6E8, (0xBADE, 0x70E4), "handed to lcall/ljmp -> callee reads+writes"),
    0x0811: (0x2B5F9, (0x9A48, 0x10C8), "handed to lcall/ljmp -> callee reads"),
    0x07D6: (0x2951B, (0xB2F7, 0x10C8), "handed to lcall/ljmp -> callee reads"),
}

# `lightbar-bat-flow.md` 3.5's own `r2 -a 8051 -c 's <addr>; pd N'` heads.
READ3_R3R2R1 = ("movx a,@dptr ; mov r3,a ; inc dptr ; movx a,@dptr ; mov r2,a"
                " ; inc dptr ; movx a,@dptr ; mov r1,a")
READ3_R0R1R2 = ("movx a,@dptr ; mov r0,a ; inc dptr ; movx a,@dptr ; mov r1,a"
                " ; inc dptr ; movx a,@dptr ; mov r2,a")
# 0x70E4, the second link of 0x089E's chain: reads, writes, and reads again
# off the same DPTR, which is what makes that cell r+w rather than read.
RW_70E4 = ("xch a,0xf0 ; mov r0,a ; inc dptr ; movx a,@dptr ; add a,r0"
           " ; movx @dptr,a ; xch a,0xf0 ; mov r0,a")

# ec-0x07d0-sites.md 3, hand-decoded: of 0x07D0's 79 handoffs, 72 resolve to a
# callee that loads and 7 to one that stores. Recorded here as the split the
# tool has to keep producing, because a depth-N change that moved it would be
# a change to the walk rather than to the depth.
D7D0_SPLIT = (72, 7)


def fixture(insns_at, size: int = 0x60) -> bytes:
    """A flat `common`-region image with `insns_at` = {offset: bytes}."""
    img = bytearray(b"\x00" * size)
    for off, raw in insns_at.items():
        img[off:off + len(raw)] = raw
    return bytes(img)


def lcall(target: int) -> bytes:
    return bytes([0x12, target >> 8, target & 0xFF])


def mov_dptr(addr: int) -> bytes:
    return bytes([0x90, addr >> 8, addr & 0xFF])


def movx_read() -> bytes:
    return bytes([0xE0, 0x22])                 # movx a,@dptr ; ret


class ImageDepthTests(unittest.TestCase):
    """The whole-file claims, read off the committed image.

    `all_rows` walks every site of every address in registers.yaml once and
    then resolves each handoff at every depth asked for, because the site's
    own walk is the expensive half and it does not depend on the depth. The
    tests that need the buckets to add up still go through `site_rows()`
    itself at one depth, so the fast path here is not the only thing that
    would notice a dropped site.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        off, magic = txr.PD_MARKER
        cls.pd = cls.d[off:off + len(magic)] == magic
        import yaml
        with open(rrt.DEFAULT_YAML) as f:
            cls.regs = yaml.safe_load(f)["registers"]
        cls.addrs = list(rrt.addresses(cls.regs))

    def all_rows(self, depths):
        """{(addr, file_offset): {depth: (label, chain, stop)}}."""
        out = collections.defaultdict(dict)
        for _, addr in self.addrs:
            for o in txr.sites_for(self.d, addr):
                insns = txr.walk(self.d, o)
                if rrt.bucket(txr.classify(insns)) != rrt.HANDOFF:
                    continue
                for depth in depths:
                    label, _callee, _win, chain, stop = rrt.resolve_handoff(
                        self.d, o, insns, self.pd, depth)
                    out[(addr, o)][depth] = (label, tuple(chain), stop)
        return out

    def test_depth_0_and_1_are_byte_identical_to_what_was_committed(self):
        # The guard rail: at depth 0 the class set is the committed one and
        # every site's row is what the file produced before the flag existed.
        # A regression here would not be a weaker claim, it would be a
        # document that no longer reproduces.
        self.assertIs(rrt.classes_for(0), rrt.CLASSES)
        for addr in (0x043E, 0x0768, 0x07D0, 0x04A6, 0x07E2, 0x07E5, 0x089E):
            rows = list(rrt.site_rows(self.d, addr, self.pd, 0))
            want = []
            for o in txr.sites_for(self.d, addr):
                insns = txr.walk(self.d, o)
                want.append((o, txr.region_of(o, self.pd)[0],
                             txr.runtime_addr(o, self.pd),
                             rrt.bucket(txr.classify(insns)), None, None,
                             " ; ".join(" ".join(mn.split())
                                        for _, _, mn in insns[1:]), None,
                             None, None))
            self.assertEqual(rows, want, f"0x{addr:04X}")

    def test_depth_1_changes_the_handoff_buckets_and_nothing_else(self):
        # What "depth 1 is unchanged" has to mean, since a depth-1 row does
        # carry a chain and a stop reason: the walk ran and stopped, it just
        # never left depth 1. So a depth-1 row must equal its depth-0 row
        # everywhere except the three fields the resolution exists to fill,
        # and a depth-1 chain is never longer than one link. A recursion that
        # ran a second level at depth 1 would move a label and fail here
        # before it could quietly rewrite a committed transcript.
        for addr in (0x04A6, 0x07D0, 0x07E2, 0x07E5, 0x089E, 0x0811):
            zero = list(rrt.site_rows(self.d, addr, self.pd, 0))
            one = list(rrt.site_rows(self.d, addr, self.pd, 1))
            self.assertEqual(len(zero), len(one), f"0x{addr:04X}")
            for a, b in zip(zero, one):
                # Where it is, and what it did at the site, are the depth-0
                # facts and cannot move.
                self.assertEqual(a[:3], b[:3], f"0x{addr:04X}")
                self.assertEqual(a[6:8], b[6:8], f"0x{addr:04X}")
                if a[3] != rrt.HANDOFF:
                    self.assertEqual(a, b, f"0x{addr:04X}")
                if b[8] is not None:
                    self.assertLessEqual(len(b[8]), 1, f"0x{addr:04X}")

    def test_the_csv_gains_its_two_columns_only_above_depth_1(self):
        # The gate is on the header, because a column added at depth 1 would
        # put an empty cell in every committed transcript's reproduction.
        headers = {}
        for depth in (0, 1, 2, 3):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rrt.write_csv(self.d, [{"name": "n", "addr": 0x07E2}],
                              self.pd, depth)
            headers[depth] = out.getvalue().splitlines()[0]
        self.assertNotIn("chain", headers[0])
        self.assertNotIn("chain", headers[1])
        self.assertIn("chain,stop", headers[2])
        self.assertIn("chain,stop", headers[3])
        # The first seven columns are the same table at every depth, so a
        # reader's `cut -d, -f6` keeps working.
        for depth in (1, 2, 3):
            self.assertEqual(headers[depth].split(",")[:7],
                             headers[0].split(",")[:7])

    def test_the_two_named_sites_resolve_at_depth_2_with_the_chains(self):
        # The claim the issue asks for, asserted from the committed image
        # against chains transcribed from lightbar-bat-flow.md 3.5's `r2`
        # listing rather than from the tool's own output.
        for addr, (off, first, second, label) in NAMED.items():
            row = [r for r in rrt.site_rows(self.d, addr, self.pd, 2)
                   if r[0] == off]
            self.assertEqual(len(row), 1, f"0x{addr:04X} at 0x{off:05X}")
            _o, _region, _rt, got, _cal, _win, _win2, _via, chain, stop = row[0]
            self.assertEqual(got, label, f"0x{addr:04X} at 0x{off:05X}")
            self.assertEqual(chain, (first, second), f"0x{addr:04X}")
            self.assertEqual(stop, "", f"0x{addr:04X}")

    def test_the_named_sites_transcripts_are_the_committed_ones(self):
        # The direction is only as good as the window behind it, so the
        # window the depth-2 row carries is pinned against the `r2` heads
        # lightbar-bat-flow.md 3.5 already transcribed. 0x07E2's chain ends
        # at 0x10C8 and 0x07E5's at 0x0FCB, which load into different
        # register groups -- so a chain that swapped the two links would
        # still read `callee reads` and would be caught here.
        want = {0x07E2: (0x204F9, READ3_R3R2R1), 0x07E5: (0x2662D, READ3_R0R1R2)}
        for addr, (off, window) in want.items():
            got = [(w, c) for o, _r, _rt, _lab, _cal, w, _w2, _v, c, _s
                   in rrt.site_rows(self.d, addr, self.pd, 2) if o == off]
            self.assertEqual(got, [(window, (NAMED[addr][1], NAMED[addr][2]))])

    def test_exactly_the_five_named_cells_move_between_depth_1_and_2(self):
        # The census: which rows a depth-2 run changes. Stated as a claim
        # about the image ("these five, and no other"), not as a count, so a
        # future image that moves a sixth fails by naming it.
        rows = self.all_rows((1, 2))
        moved = {k for k, v in rows.items() if v[1][0] != v[2][0]}
        want = {(addr, off) for addr, (off, _a, _b, _l) in NAMED.items()}
        want |= {(addr, off) for addr, (off, _c, _l) in ALSO_MOVING.items()}
        self.assertEqual(moved, want)
        for key in moved - want:
            self.fail(f"0x{key[0]:04X} at 0x{key[1]:05X} moved and is not named")

    def test_the_three_unnamed_cells_resolve_to_what_their_chains_show(self):
        for addr, (off, chain, label) in ALSO_MOVING.items():
            row = [r for r in rrt.site_rows(self.d, addr, self.pd, 2)
                   if r[0] == off]
            self.assertEqual(len(row), 1, f"0x{addr:04X} at 0x{off:05X}")
            self.assertEqual(row[0][3], label)
            self.assertEqual(row[0][8], chain)
            self.assertEqual(row[0][9], "")
            # 0x70E4 is the one that is not a plain 3-byte load: it reads,
            # adds and writes the same DPTR, so its cell has to be r+w.
            if addr == 0x089E:
                self.assertEqual(row[0][5], RW_70E4)

    def test_both_cross_checks_hold_at_every_depth(self):
        # 0x07D0's 79 handoffs split 72 load / 7 store (ec-0x07d0-sites.md 3),
        # and 0x04A6's four PD handoffs stay unresolved because the DPTR +=
        # A x B family at 0x10BC never dereferences DPTR (pd-xdata-overlap.md
        # 3). A depth-N change that "resolves" those four has a bug, not a
        # result. `all_rows` sweeps every address in registers.yaml, so a
        # chain that appeared or vanished anywhere else would move the counts
        # below; the site-count reconciliation that would catch a *dropped*
        # site is the next case, because a sweep that only records handoffs
        # cannot see one.
        for depth in (2, 3, 4, 8):
            rows = self.all_rows((depth,))
            d7d0 = collections.Counter(
                v[depth][0] for k, v in rows.items() if k[0] == 0x07D0)
            self.assertEqual(
                (d7d0["handed to lcall/ljmp -> callee reads"],
                 d7d0["handed to lcall/ljmp -> callee writes"]),
                D7D0_SPLIT, f"0x07D0 at depth {depth}")
            pd_handoffs = [(k, v[depth]) for k, v in rows.items()
                           if k[0] == 0x04A6
                           and txr.region_of(k[1], self.pd)[0] == "pd-image"]
            self.assertEqual(len(pd_handoffs), 4, f"0x04A6 at depth {depth}")
            for key, (label, _chain, stop) in pd_handoffs:
                self.assertEqual(label, rrt.HANDOFF, f"0x{key[1]:05X}")
                # The reason the chain ends where it does, so a row that
                # stayed unresolved is unresolved for this method's stated
                # reason and not some other one.
                self.assertIn("no direction at 0x10BC", stop, f"0x{key[1]:05X}")

    def test_the_buckets_still_reconcile_at_depth_2(self):
        # reconcile() is the property that makes the table trustworthy: the
        # buckets sum to the site count and main + PD to the file-wide total,
        # for every address, at the new depth as at the old one. This drives
        # the same writer main() does and asserts its return value, so a run
        # that merely *did not print* a problem cannot pass it.
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            problems = rrt.write_markdown(self.d, self.regs, self.pd, 2)
        self.assertEqual(problems, 0, err.getvalue())

    def test_depth_is_a_fixed_point_at_two_on_this_image(self):
        # The measurement that bounds the feature: no chain is longer than
        # two links, so 2, 3, 4 and 8 agree everywhere. That is a fact about
        # this image and not evidence the cap is unnecessary -- the cap is
        # what the fixtures below exist for, and nothing here would notice if
        # it stopped working.
        rows = self.all_rows((2, 3, 4, 8))
        self.assertTrue(rows)
        for (addr, off), per_depth in rows.items():
            for depth in (3, 4, 8):
                self.assertEqual(per_depth[2], per_depth[depth],
                                 f"0x{addr:04X} at 0x{off:05X} at depth {depth}")
        longest = max(len(v[2][1]) for v in rows.values())
        self.assertEqual(longest, 2, "the longest chain this run reaches")


class GuardTests(unittest.TestCase):
    """The two paths the committed image never reaches, built as fixtures."""

    def resolve(self, img, site, depth):
        insns = txr.walk(img, site)
        self.assertEqual(rrt.bucket(txr.classify(insns)), rrt.HANDOFF,
                         "the fixture's own site is not a handoff site")
        return rrt.resolve_handoff(img, site, insns, True, depth)

    def test_a_cycle_terminates_with_the_cycle_reason(self):
        # Two routines that hand DPTR to each other. Without the guard this
        # recurses until the interpreter gives up, and the suite would hang
        # rather than fail -- which is why the case is here and not implied
        # by the image cases above.
        img = fixture({
            0x00: mov_dptr(0x0751) + lcall(0x0010),   # the site
            0x10: lcall(0x0020),
            0x20: lcall(0x0010),
        })
        label, callee, _win, chain, stop = self.resolve(img, 0x00, 8)
        self.assertEqual(label, rrt.HANDOFF)
        # The chain names the routines actually entered, so it does not repeat
        # the one the loop closed on; `callee` and the window are what name
        # where it closed, and `stop` is what says that is why.
        self.assertEqual(chain, (0x0010, 0x0020))
        self.assertEqual(callee, 0x0010, "names where the loop closed")
        self.assertEqual(stop, rrt.STOP_CYCLE)
        self.assertIn("0x0010", _win)

    def test_the_cap_terminates_with_the_depth_that_was_asked_for(self):
        # A chain of ten forwarders ending in a routine that reads, so every
        # depth this case asks about runs out of budget before the end and
        # one more reaches it. Ten rather than three because the load-bearing
        # half of this is the depth in the reason: a run asked for 8 has to
        # say `cap 8`, and a three-link fixture would have resolved at 8 and
        # tested nothing about it.
        at = [0x10 * (i + 1) for i in range(10)]
        end = at[-1] + 0x10
        links = dict(zip(at, at[1:] + [end]))
        img = fixture({0x00: mov_dptr(0x0751) + lcall(0x0010),
                       end: movx_read(),
                       **{a: lcall(t) for a, t in links.items()}},
                      size=0x110)
        for depth in (1, 2, 3, 8):
            label, _callee, _win, chain, stop = self.resolve(img, 0x00, depth)
            self.assertEqual(label, rrt.HANDOFF, f"depth {depth}")
            self.assertEqual(chain, tuple(at)[:depth])
            self.assertEqual(stop, rrt.STOP_CAP.format(depth=depth),
                             f"a run asked for {depth} must not name another")
        # And the same fixture one level past the end resolves, so the cases
        # above are the cap and not a chain that never resolves. The chain is
        # the ten forwarders plus the reader, so it takes depth 11 to reach
        # the reader: one level is spent entering each routine in it.
        label, callee, _win, chain, stop = self.resolve(img, 0x00, 11)
        self.assertEqual(label, "handed to lcall/ljmp -> callee reads")
        self.assertEqual(callee, end)
        self.assertEqual(chain, tuple(at) + (end,))
        self.assertEqual(stop, "")

    def test_a_callee_that_never_dereferences_dptr_is_not_the_cap(self):
        # The distinction the `stop` column exists for: a chain that ends on
        # a routine which does not touch DPTR is an answer, and a chain that
        # ran out of budget is a question this tool was not asked far enough.
        # Both read `handoff->unresolved` in the class column.
        img = fixture({
            0x00: mov_dptr(0x0751) + lcall(0x0010),
            0x10: lcall(0x0020),
            0x20: bytes([0xA4, 0x22]),               # mul ab ; ret
        })
        _label, _callee, _win, _chain, stop = self.resolve(img, 0x00, 8)
        self.assertNotEqual(stop, rrt.STOP_CAP)
        self.assertTrue(stop.startswith("no direction at 0x0020:"), stop)

    def test_the_four_reasons_are_distinct_and_none_is_the_class_label(self):
        # A `stop` that could be confused with `HANDOFF` would leave a reader
        # unable to tell a reason from a bucket, and a reader who cannot is
        # back to the bare `unresolved` the column was added to break up.
        reasons = [rrt.STOP_NO_TARGET, rrt.STOP_UNREACHABLE, rrt.STOP_CYCLE,
                   rrt.STOP_CAP.format(depth=2)]
        self.assertEqual(len(set(reasons)), len(reasons))
        for reason in reasons:
            self.assertNotIn(rrt.HANDOFF, reason)
            self.assertTrue(reason)

    def test_a_negative_depth_is_refused_by_name(self):
        # Not `choices`, which cannot express "any non-negative N", and not a
        # silent 0: a negative depth is a request to walk a chain backwards.
        out = subprocess.run(
            [sys.executable, str(HERE / 'register_ref_table.py'), FIRMWARE,
             "--callee-depth", "-1"],
            capture_output=True, text=True, cwd=str(HERE))
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("--callee-depth -1 is not a depth", out.stderr)

    def test_reconcile_still_fails_at_depth_2_on_each_of_its_three_ways(self):
        # The third is the one the new columns could have introduced: a class
        # the bucket set does not know would still be counted into the sum
        # and would still partition the sites, and would read as a clean run
        # if reconcile() only checked arithmetic.
        classes = rrt.classes_for(2)
        # The unresolved bucket keeps the depth-0 HANDOFF label by design --
        # it is the same verdict reached further in -- so what has to hold is
        # that depth 2's class set is depth 1's, unchanged, which is what
        # makes a depth-N cross-check a like-for-like comparison.
        self.assertEqual(classes, rrt.classes_for(1))
        # Each of the three ways reconcile() can fail, one call each: a
        # bucket that does not sum to the site count, a main + PD that does
        # not sum to the file-wide total, and a class no column is named for.
        # The second is the one worth building by hand rather than reaching
        # for, because it is the only one whose arithmetic can be right while
        # its two halves disagree.
        cases = (
            ("dropped site", 4, 0, 4, collections.Counter({"read": 3})),
            ("main + PD do not add up", 4, 1, 2,
             collections.Counter({"read": 2, "write": 2})),
            ("unbucketed class", 4, 0, 4,
             collections.Counter({"read": 3, "handed to lcall/ljmp -> "
                                            "callee sideways": 1})),
        )
        for why, total, main, pd, hist in cases:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                problems = rrt.reconcile("n", 0x07E2, total, main, pd, hist,
                                         classes)
            self.assertEqual(problems, 1, f"{why}: {err.getvalue()}")
            self.assertTrue(err.getvalue().strip(), f"{why} said nothing")


class BudgetTests(unittest.TestCase):
    """The 0x0FCB window, pinned as a fact about the budget rather than as a
    verdict about the routine."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()

    def off(self, runtime: int) -> int:
        return txr.offset_for_runtime(runtime, "pd-image")

    def test_the_0x0FCB_window_is_truncated_by_the_budget(self):
        # lightbar-bat-flow.md 3.5 reports 0x0FCB as a 3-byte load into
        # R0:R1:R2. That is the *direction* right and the count is the walk's:
        # at the budget walk() uses, the eighth instruction is the third
        # MOVX and the window ends with `max_insns (8) exhausted`; the ninth
        # is `inc dptr` and at a budget of 12 the same routine is four reads.
        # pd-0x38-consumers.md reads it as four MOVX reads into R0-R3, and
        # both are right about a budget the other did not use. Asserting the
        # budget here is what stops a future change to walk_budget_census.py
        # from quietly rewriting the number out of that write-up.
        at8 = txr.walk(self.d, self.off(0x0FCB))
        _insns, why = txr.walk_why(self.d, self.off(0x0FCB))
        self.assertEqual(why, "max_insns (8) exhausted")
        self.assertEqual(txr.classify(at8, skip=0), "read x3, walks 3 consecutive bytes (inc dptr)")
        at12 = txr.walk(self.d, self.off(0x0FCB), max_insns=12)
        self.assertEqual(txr.classify(at12, skip=0), "read x4, walks 4 consecutive bytes (inc dptr)")
        # And the tool's own row carries the budget-limited one, not the
        # larger budget's, because resolve_handoff walks at the default.
        _l, _c, win, _chain, _stop = rrt.resolve_handoff(
            self.d, 0x2662D, txr.walk(self.d, 0x2662D), True, 2)
        self.assertEqual(win, READ3_R0R1R2)

    def test_the_ljmp_tails_of_b1f2_and_383a_stay_untraced(self):
        # walk() stops at the first control-flow instruction, so each of the
        # two forwarders decodes as exactly one `lcall` and its `mov a,#1 ;
        # ljmp 0x0C46` / `clr c ; ljmp 0x0F0E` tail is never in any window at
        # any depth. Following it is walk_flow_follow.py's job. Asserted so
        # a future relaxation of the flow stop cannot make the depth-2 claim
        # quietly stronger than the write-up says it is.
        for runtime, tail in ((0xB1F2, "0x0C46"), (0x383A, "0x0F0E")):
            insns, why = txr.walk_why(self.d, self.off(runtime))
            self.assertEqual(why, "flow opcode", f"0x{runtime:04X}")
            self.assertEqual(len(insns), 1, f"0x{runtime:04X}")
            self.assertEqual(insns[0][2], f"lcall 0x{0x10C8 if runtime == 0xB1F2 else 0x0FCB:04x}")


if __name__ == "__main__":
    unittest.main()
