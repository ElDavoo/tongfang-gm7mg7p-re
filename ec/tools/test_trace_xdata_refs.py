#!/usr/bin/env python3
"""The bounds contract of `trace_xdata_refs.walk()`, on its own.

`test_walk_budget_census.py` holds the *terminator* half of this loop: one
hand-built fixture per guard, each asserting which guard fired, because a
wrong token is a census row that names the wrong reason. This file is the
other half -- which *instructions come back* -- and the two are not duplicates
of each other. A walk that decodes the wrong window for the right reason
passes this file and fails that one; a walk that names the right reason for a
window it decoded wrongly passes that one and fails this.

Why the same loop twice. `docs/findings/opcode-len-bounds-census.md` row 9
records that the `i + 2 >= len(d)` test is the one that holds the index in,
and that over the committed sweep it fires **0** times -- 94109 bytes is the
smallest `len(d) - i` any committed walk reaches -- which reads as dead code
to exactly the reader the restated comment was written for. The census could
not settle that either way, and the issue that asked for a case had measured
the tree before this one's neighbour landed, so its "pinned by nothing" was
true when written and is not now: two cases in
`test_walk_budget_census.py` hold the guard, they do it as `IndexError`s
escaping a case rather than as assertions that name it, and the sweep the
census points at cannot see them. Deleting either guard turns *this* suite
red too, and which of its cases go red says which guard went. The
guard-deleting runs are in
`docs/findings/walk-bounds-guard-pinned.md`.

No hardware, no firmware image and no Ghidra. Every case builds its own
`common`-region buffer, where the file offset equals the runtime address,
which is what lets the offsets in a case be the addresses in the fixture.
"""
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# trace_xdata_refs imports disasm8051 by bare module name, the way
# register_ref_table.py does, so the tool directory has to be on the path
# before it is loaded rather than after.
sys.path.insert(0, str(HERE))
import trace_xdata_refs as T          # noqa: E402

# One instruction in none of the guards' way, laid down any number of times:
# `0x00` is the opcode table's 1-byte `nop`, not a flow opcode and not
# `mov dptr`. A 3-byte stand-in would not do -- `disasm8051.py` gives `0x75`
# a length of 3, so a fixture counting two bytes per filler would stop in the
# filler and every case below would be about `0x75` instead.
NOP = bytes([0x00])
SITE = bytes([0x90, 0x07, 0xD0])      # mov dptr,#0x07D0 -- what a site is
RELOAD = bytes([0x90, 0x07, 0xD1])    # mov dptr,#0x07D1 -- the other guard
READ = bytes([0xE0])                  # movx a,@dptr

# walk()'s own default, named so a case says which budget it meant instead of
# relying on the signature's.
BUDGET = 8

# #805's derived vector, from docs/findings/opcode-len-bounds-census.md's
# "The issue's vector does not reproduce; here is one that does". Over-asked
# by two: four 1-byte instructions, three decoded.
VEC = b"\x00\x00\x00\x00"


def fixture(*insns: bytes, size: int = 0x40) -> bytes:
    """A flat `common`-region image with `insns` laid down from offset 0.

    The same helper `test_walk_budget_census.py` and `test_walk_branch_arms.py`
    each carry a copy of, and for the same reason: a case that pointed at the
    firmware would keep testing the same bytes only until the bytes around
    some address in the image changed.
    """
    img = bytearray(b"\x00" * size)
    at = 0
    for insn in insns:
        img[at:at + len(insn)] = insn
        at += len(insn)
    return bytes(img)


def why(img, start=0, max_insns=BUDGET):
    return T.walk_why(img, start, max_insns)[1]


class OverAskTests(unittest.TestCase):
    """A walk asked for more instructions than its buffer holds stops and
    yields what fitted, rather than reading past the end.

    The contract `test_disasm8051.py` pins for `decode()` and this loop
    inherited: the count is a request, not a promise. The difference is which
    of the two `len(d)` tests gets there, and this file asserts the *result*
    where that file asserts the guard's position.
    """

    def test_the_over_ask_yields_what_fitted(self):
        # Offsets and `raw`, not the mnemonic text. The mnemonic table is
        # disasm8051.py's subject and test_disasm8051.py's; a case here that
        # asserted `0x00` renders as "nop" would go red for a change to that
        # table, which is not a bounds defect, and would stop being evidence
        # for one the moment the wording moved.
        insns = T.walk(VEC, 0)
        self.assertEqual([(at, raw) for at, raw, _ in insns],
                         [(0, b"\x00"), (1, b"\x00")])
        # Two, not three and not four: the walk stops on the first iteration
        # that cannot read two bytes ahead, and the request was for eight.
        self.assertLess(len(insns), BUDGET)
        # Every triple is in range, which is the property stated in a form
        # that holds whatever the instruction lengths are.
        for at, raw, text in insns:
            self.assertLessEqual(at + len(raw), len(VEC))
            self.assertIsInstance(text, str)

    def test_the_same_walk_says_the_buffer_ended_it(self):
        # Its own case, and not folded into the one above, because this is the
        # assertion that makes that one a statement about the guard: "it
        # stopped" is otherwise equally true of the budget and of a flow
        # opcode, and the case above cannot tell those apart from a stop at
        # the buffer's end. The budget is left at walk()'s own default so it
        # is not a candidate answer here -- a walk that ran out of budget
        # returns the budget token whatever it decoded on the way there.
        insns, token = T.walk_why(VEC, 0, BUDGET)
        self.assertEqual(token, T.BUFFER_END)
        self.assertNotEqual(token, T.budget_end(BUDGET))
        # The same walk as the case above, so the two cannot disagree about
        # what was decoded while agreeing about why it stopped.
        self.assertEqual([(at, raw) for at, raw, _ in insns],
                         [(0, b"\x00"), (1, b"\x00")])


class BothGuardsTests(unittest.TestCase):
    """Each of `walk_why()`'s two post-`i += n` guards, and what the other
    one does instead. One going cannot be argued away by the other holding."""

    def test_a_dptr_reload_ends_the_walk_and_its_absence_runs_on_to_the_budget(self):
        # The negative half is the load-bearing half. Asserting only that a
        # reload ends a walk would pass on a loop that ended it for some other
        # reason, so the same eight-instruction fixture is walked twice: with
        # the reload at the fourth instruction and with three filler bytes
        # there instead. The second run is 0x40 bytes long, so the bounds
        # guard cannot be what stops it -- what stops it is `max_insns`, and
        # the budget token is the proof that the reload really was the
        # difference between the two.
        with_reload = fixture(SITE, NOP, NOP, RELOAD, NOP, NOP, NOP, NOP)
        self.assertEqual(why(with_reload), T.RELOAD_END)
        without = fixture(SITE, NOP, NOP, NOP, NOP, NOP, NOP, NOP)
        self.assertEqual(why(without), T.budget_end(BUDGET))
        self.assertNotEqual(why(with_reload), why(without))
        # And the reload is what differs, by offset and by bytes: the first
        # walk stops after three instructions, the second after eight.
        self.assertEqual(len(T.walk(with_reload, 0)), 3)
        self.assertEqual(len(T.walk(without, 0)), BUDGET)

    def test_the_loop_is_bounded_by_max_insns_and_not_by_len_d(self):
        # The restatement's claim, asserted rather than asserted-about: the
        # loop's own bound is the caller's number, so the same six bytes run
        # to the budget in one buffer and to the buffer's end in another, and
        # nothing about the instruction stream decides which. The first half
        # overlaps the other suite's
        # `TerminatorTokenTests.test_a_run_longer_than_the_budget_names_the_budget_with_that_budget`
        # and is kept because the second half is the property -- it is the
        # half that would go if `max_insns` were ever replaced by `len(d)`.
        long_enough = fixture(SITE, NOP, NOP, NOP)
        self.assertEqual(why(long_enough), T.budget_end(BUDGET))
        # The same bytes in a 7-byte buffer: three fit, and after the third
        # `i` is 5 and there is no room to read two more. `size` is 7 rather
        # than something tighter because the helper lays `insns` down into a
        # `bytearray` and a slice assignment past the end *appends* -- a size
        # under the bytes written grows the image rather than shortening it,
        # and this fixture would then be the `long_enough` one under another
        # name.
        short = fixture(SITE, NOP, NOP, NOP, size=7)
        self.assertEqual(why(short), T.BUFFER_END)
        self.assertLess(len(T.walk(short, 0)), len(T.walk(long_enough, 0)))
        # The default the function documents is the one both halves assume.
        self.assertEqual(T.walk.__defaults__[0], BUDGET)


class CallSiteTests(unittest.TestCase):
    """`walk_why()`'s two callers, over a fixture image rather than the
    committed one.

    The issue this file answers wanted the function reachable from somewhere
    other than another suite's sweep of the real image. The fixture is a
    `mov dptr,#0x07D0` site, a read, and filler, cut off by the bounds guard
    at 7 bytes -- so both call sites are driven by a window that only the
    guard being pinned here can produce, and a `walk()`-only call site could
    not render either answer.
    """

    # 0: the site. 3: the read. 4: filler. 5, 6: the two bytes the walk cannot
    # read ahead of, and the buffer ends inside the third instruction, so the
    # bounds guard is the terminator rather than the budget. The budget is not
    # a candidate answer at this size and is not close to being one: the same
    # bytes in a 12-byte buffer still end at the buffer (8 instructions), and
    # only at 13 does the budget win.
    IMAGE = fixture(SITE, READ, NOP, size=7)

    def test_the_csv_table_renders_the_window_and_the_terminator(self):
        # `pd_verified=False` because a 7-byte buffer is not this dump's PD
        # image, and passing the flag rather than leaving it to the caller is
        # what keeps the region column reading "common" as a fact about where
        # offset 0 sits rather than as a claim about the firmware.
        table, unmapped = T.csv_table(self.IMAGE, ["0x07D0"], False, None)
        self.assertEqual(unmapped, {})
        rows = list(csv.DictReader(io.StringIO(table)))
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["file_offset"], "0x00000")
        self.assertEqual(row["region"], "common")
        self.assertEqual(row["runtime"], "0x0000")
        # The window is the decoded instructions after the site's own `mov
        # dptr`, and the assertion is against what `walk_why()` returns rather
        # than against a spelling: the mnemonic text belongs to the opcode
        # table, and the cell's claim is that it is this walk's output.
        insns, token = T.walk_why(self.IMAGE, 0)
        self.assertEqual(
            row["window"],
            " ; ".join(" ".join(mn.split()) for _, _, mn in insns[1:]))
        self.assertEqual(row["access"], T.classify(insns))
        self.assertEqual(len(insns), 3)
        # The same run with the column, which is the cell only a `walk_why()`
        # caller can fill: `walk()` discards the reason by construction, so a
        # table that carried it could not have come from a `walk()` call site.
        wide, _ = T.csv_table(self.IMAGE, ["0x07D0"], False, None,
                              terminator=True)
        wide_row = next(csv.DictReader(io.StringIO(wide)))
        self.assertEqual(wide_row["terminator"], token)
        self.assertEqual(wide_row["terminator"], T.BUFFER_END)

    def test_main_prints_the_window_and_the_reason_that_ended_it(self):
        # The non-CSV path, as a subprocess because that is how a reader runs
        # it and how `main()`'s exit status reaches anything at all. The
        # fixture goes to a temporary file because `main()`'s first argument is
        # a path, and a hand-built buffer is the only way to reach a window
        # this short without editing the firmware.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fixture.bin")
            with open(path, "wb") as f:
                f.write(self.IMAGE)
            out = subprocess.run(
                [sys.executable, str(HERE / 'trace_xdata_refs.py'), path,
                 "0x07D0"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("0x07D0: 1 direct MOV DPTR site(s)", out.stdout)
        # The reason, on the line `main()` prints it, and not merely some
        # reason: `end of buffer` is what separates this run from a decode
        # that stopped on a real terminator.
        self.assertIn(f"window ended: {T.BUFFER_END}", out.stdout)
        # And the note that says what this run is not. A 7-byte buffer has no
        # PD marker in it, `main()` says so on stderr rather than assuming,
        # and the line is what keeps `common` in the stdout above from reading
        # as a measurement of this dump.
        self.assertIn("no 'ITE8850-PD' marker", out.stderr)


if __name__ == '__main__':
    unittest.main()
