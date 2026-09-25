#!/usr/bin/env python3
"""The bounds contract of `disasm8051.decode()`, on its own.

`disasm8051.py --self-test` holds the r2 hand transcriptions, which are the
oracle for the opcode and mnemonic tables: if one of those changes, those
windows disagree with the listing. None of them asks for more instructions than
their buffer holds, so the contract at the end of the buffer has no home there
-- and for a while it had no home anywhere, being asserted only inside another
tool's suite (`citation_gap_scan.py --self-test` and
`test_citation_gap_scan.py`), where it was pinned *as a defect* and where its
failure mode was a second walk rather than this one.

`count` is a request, not a promise: the walk stops at the end of the buffer
and at an instruction that does not fit, and returns rather than raising. The
end-of-buffer check runs before the index it guards; the neighbouring
does-not-fit check is older and separate, and both are pinned here, because a
later "simplification" that folds them into one is the edit that would quietly
change what a truncated instruction does.

No hardware, no firmware bytes and no Ghidra: the cases are hand-built windows,
so a case keeps testing what it was written for if the bytes at some address in
the image change. The windows are `common`-region shapes, where the file offset
equals the runtime address, which is what lets the runtime addresses below be
the offsets in the fixture.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'disasm8051', HERE / 'disasm8051.py')
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

# A one-byte `ret` is the shape a gap window ends on routinely -- `bank0,B5D2`
# is a bare one -- and a 3-byte `lcall` is the shape that does not fit when the
# window stops short of its last byte.
RET_1 = b"\x22"
LCALL_3 = b"\x12\xe5\xd6"


class EndOfBuffer(unittest.TestCase):
    """`i` is checked against the end of the buffer before it indexes it, so a
    caller that over-asks gets the instructions that fitted and a stop."""

    def test_asking_for_more_than_the_buffer_holds_yields_what_fitted(self):
        # The regression this file exists for. One `ret`, asked for four: the
        # walk decodes it, advances `i` to 1, and used to evaluate
        # `OPCODE_LEN[d[1]]` before its own bounds check -- an IndexError from
        # the index rather than the clean stop the guard was written to give.
        self.assertEqual(list(D.decode(RET_1, 0, 4, 0xB5D2)),
                         [(0, RET_1, "ret")])

    def test_asking_for_exactly_what_is_there_still_yields_it(self):
        # The neighbouring case, and the one a fix that clamped `count` rather
        # than guarding `i` would break: a request the buffer satisfies in full
        # is not truncated by the guard.
        self.assertEqual([t for _i, _r, t in D.decode(LCALL_3, 0, 1, 0xE580)],
                         ["lcall 0xe5d6"])

    def test_a_walk_that_reaches_the_end_under_stop_at_flow_stops(self):
        # `stop_at_flow` returns on the branch; the end of the buffer is the
        # other exit, and it is the one a `--cross-decoder` window over the last
        # function in a region takes. `ret` is a flow opcode, so this also
        # pins that the two exits are not confused for one.
        got = list(D.decode(RET_1, 0, 40, 0xB5D2, stop_at_flow=True))
        self.assertEqual([t for _i, _r, t in got], ["ret"])

    def test_an_empty_buffer_decodes_to_nothing(self):
        self.assertEqual(list(D.decode(b"", 0, 8, 0xB5CC)), [])

    def test_a_start_past_the_end_decodes_to_nothing(self):
        # `start == len(d)` is the boundary the guard sits on. A caller that
        # computed an offset one past a region is a question about that
        # caller's arithmetic, not something to answer with a traceback.
        self.assertEqual(list(D.decode(RET_1, len(RET_1), 8, 0xB5D3)), [])


class TruncatedInstruction(unittest.TestCase):
    """The older, neighbouring guard: an instruction whose bytes are not all
    there is not decoded, and is not read past the end to find them."""

    def test_an_instruction_that_does_not_fit_yields_nothing(self):
        # Two bytes are not enough for a 3-byte `lcall`. This already worked
        # before the end-of-buffer guard was hoisted, and it is pinned here for
        # that reason: the two checks guard different things, and the first
        # must not have been satisfied by moving the second.
        self.assertEqual(list(D.decode(LCALL_3[:2], 0, 4, 0xE580)), [])

    def test_what_fits_is_kept_and_the_walk_stops_at_the_instruction_that_does_not(self):
        # The mixed shape: a `ret` followed by the two bytes of a `lcall` that
        # does not fit. The `ret` is decoded and the `lcall` is not -- which is
        # the difference between a window whose tail is short and a window that
        # failed to start.
        got = list(D.decode(RET_1 + LCALL_3[:2], 0, 4, 0xB5D2))
        self.assertEqual([(i, text) for i, _r, text in got], [(0, "ret")])


if __name__ == '__main__':
    unittest.main()
