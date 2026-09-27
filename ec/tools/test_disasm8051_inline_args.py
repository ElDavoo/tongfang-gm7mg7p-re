#!/usr/bin/env python3
"""The inline-argument framing contract of `disasm8051`, on its own.

`test_disasm8051.py` holds the bounds contract of `decode()`, and
`disasm8051.py --self-test` holds the opcode and mnemonic tables against the r2
hand transcriptions. Neither asks what happens when a call carries its arguments
inline in the code stream, which is a different contract again: that the four
bytes after `lcall 0x104D` are read as *data*, that a walk steps over them, and
-- the part with teeth -- that no committed main-EC listing can be re-framed by
the special case at all. `../../docs/findings/pd-inline-arg-trampoline.md` is
where the convention is established; this is where the decoder's half of it is
pinned.

The four cases below split by what they would catch. The first is the claim;
the second is the bounds contract holding at the new edge the special case
creates, because a decoder that skips four bytes it has not got is worse than
one that skips none; the third is the one that would go quietly wrong, since
`0x104D` is now a name in a table and a table entry that matched on the opcode
alone would re-frame every `lcall` in the image; and the fourth is the safety
argument itself.

That fourth case is the one to keep an eye on. `INLINE_ARG_CALLS` is keyed on
the call's *target*, with no knowledge of which program is being walked, because
`converges_from()` is handed a bare file offset and no region information and
still has to know. The EC image's zero is what makes that sound, and a zero is
the one kind of number that goes stale silently: a different dump, or a PD image
that grows, could put the idiom in the main EC and re-frame every committed
listing that the decompile pipeline exports, with no test failing and
`--self-test` still green. So the zero is asserted here against the committed
image, and it is asserted by *this file* rather than by the census tool that
measures it, so that losing the tool does not lose the guard.
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
spec = importlib.util.spec_from_file_location(
    'trace_xdata_refs', HERE / 'trace_xdata_refs.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
# The table's own entry, read from the table rather than spelled here: a test
# that hard-codes the address it is testing the table for would keep passing
# after the table was pointed somewhere else.
TARGET, N = next(iter(D.INLINE_ARG_CALLS.items()))

# A `lcall` to the named target, four argument bytes, and the instruction that
# follows them -- the shape at PD runtime 0x3AA8, where the four bytes are
# `00 00 00 01` and the resume point holds `90 07 d0` (`mov dptr,#0x07d0`).
CALL = bytes([0x12, TARGET >> 8, TARGET & 0xFF])
ARGS = b"\x00\x00\x00\x01"
RESUME = b"\x90\x07\xd0"
SHAPE = CALL + ARGS + RESUME


class InlineArgumentBlock(unittest.TestCase):
    """The four bytes are data, they are stepped over, and the walk resumes
    where the helper's tail call lands."""

    def test_the_argument_block_is_yielded_as_data_not_decoded(self):
        got = list(D.decode(SHAPE, 0, 3, 0x3AA8))
        self.assertEqual(got[0], (0, CALL, f"lcall 0x{TARGET:04x}"))
        self.assertEqual(got[1], (3, ARGS, "inline args: 00 00 00 01"))
        # Offset 7, not 6: the block is four bytes wide and the walk resumes
        # after it. A decoder resuming at 6 would decode the resume
        # instruction's own low operand byte as an opcode, which is the defect
        # this table exists to prevent.
        self.assertEqual(got[2], (7, RESUME, "mov  dptr,#0x07d0"))

    def test_the_block_does_not_consume_a_unit_of_count(self):
        # `count` counts instructions and the block is not one, so asking for
        # two instructions still yields two instructions, with the block
        # between them. A block that ate a unit would silently hand a caller
        # one instruction fewer than it asked for at every such call.
        got = list(D.decode(SHAPE, 0, 2, 0x3AA8))
        self.assertEqual([t for _i, _r, t in got],
                         [f"lcall 0x{TARGET:04x}", "inline args: 00 00 00 01",
                          "mov  dptr,#0x07d0"])
        self.assertEqual([i for i, _r, _t in got], [0, 3, 7])

    def test_a_walk_that_enters_mid_argument_block_decodes_normally(self):
        # The special case keys on the *call*, not on the bytes. An anchor
        # inside the block is an anchor inside data, and a caller who points
        # the decoder there is asking what is at that offset -- not asking for
        # the argument block to be found again. So those bytes decode as
        # whatever they decode as, which for `00 00 00 01` is three `nop`s and
        # an `ajmp`, and the resume instruction is not reachable from here.
        got = [t for _i, _r, t in D.decode(ARGS + RESUME, 0, 4, 0x3AAB)]
        self.assertEqual(got[:3], ["nop", "nop", "nop"])
        self.assertNotIn("inline args: 00 00 00 01", got)

    def test_stop_at_flow_still_stops_at_the_call(self):
        # The flag exists so a window can end at a branch, and this call is one.
        # Yielding the block first would make `stop_at_flow` mean something it
        # does not.
        got = list(D.decode(SHAPE, 0, 40, 0x3AA8, stop_at_flow=True))
        self.assertEqual([t for _i, _r, t in got], [f"lcall 0x{TARGET:04x}"])


class BlockAtTheEndOfTheBuffer(unittest.TestCase):
    """The bounds contract, at the new edge the special case creates.

    `test_disasm8051.py` pins the same contract for a buffer that simply runs
    out. This is the case that only exists because of `INLINE_ARG_CALLS`: a
    decoder that skipped four bytes it has not got would read past the end, so
    a truncated block has to score as no block at all."""

    def test_a_call_whose_four_bytes_are_the_last_four_still_resumes(self):
        # Exactly the bytes there are: no instruction follows the block, and the
        # walk must end there rather than decoding the block as instructions or
        # reading off the end.
        got = list(D.decode(CALL + ARGS, 0, 4, 0x3AA8))
        self.assertEqual([(i, t) for i, _r, t in got],
                         [(0, f"lcall 0x{TARGET:04x}"),
                          (3, "inline args: 00 00 00 01")])

    def test_a_block_the_buffer_does_not_hold_whole_is_no_block(self):
        # Three of the four. `inline_arg_len()` returns 0, so the walk carries
        # on decoding from the instruction after the call and stops at the end
        # of the buffer -- which is the bounds contract, not a crash and not a
        # fabricated four-byte argument. The three `nop`s are what those three
        # bytes happen to decode as once the special case declines them.
        self.assertEqual(D.inline_arg_len(CALL + ARGS[:3], 0), 0)
        got = list(D.decode(CALL + ARGS[:3], 0, 8, 0x3AA8))
        self.assertEqual([t for _i, _r, t in got],
                         [f"lcall 0x{TARGET:04x}", "nop", "nop", "nop"])

    def test_the_call_alone_at_the_end_of_the_buffer_still_decodes(self):
        # The neighbouring case, and the one the previous case's rule could have
        # broken: a `lcall` with nothing after it is still a `lcall`.
        self.assertEqual([t for _i, _r, t in D.decode(CALL, 0, 4, 0x3AA8)],
                         [f"lcall 0x{TARGET:04x}"])


class OtherCalls(unittest.TestCase):
    """`0x104D` is a name in a table, and a table entry that matched on the
    opcode alone would re-frame every `lcall` in the image."""

    def test_an_lcall_to_another_target_is_unaffected(self):
        other = b"\x12\xe5\xd6" + ARGS + RESUME
        got = [t for _i, _r, t in D.decode(other, 0, 3, 0xE580)]
        self.assertEqual(got[0], "lcall 0xe5d6")
        self.assertNotIn("inline args:", got[1])
        # `00 00 00 01` decoded linearly, which is the mis-framing this table
        # exists to prevent -- and is correct here, because the call it follows
        # is not the named one. Pinned as the `nop` it decodes to rather than
        # as an absence, so a decoder that skipped the block anyway would fail
        # on the value rather than on a `assertNotIn` it could satisfy by
        # yielding nothing.
        self.assertEqual(got[1], "nop")

    def test_the_table_holds_exactly_the_one_call_this_file_knows(self):
        # A second entry is a new claim about a new address, and this file's
        # cases say nothing about it. Failing here says so rather than letting
        # the suite go green over a convention nobody has written down.
        self.assertEqual(len(D.INLINE_ARG_CALLS), 1)

    def test_trace_xdata_refs_walk_stops_on_the_call_and_never_crosses_it(self):
        # `walk_why()` consults `inline_arg_len()` for the same reason
        # `converges_from()` does, and for the same reason it cannot currently
        # fire: the call is a flow opcode, so the walk returns at it. Pinned
        # because the guard is a latent one, and a change that relaxed the flow
        # stop would otherwise re-frame every row behind such a call with the
        # `access` cell still reading as an answer.
        window = b"\x90\x07\xd0" + CALL + ARGS + RESUME
        insns, why = T.walk_why(window, 0)
        self.assertEqual(why, T.FLOW_END)
        self.assertEqual([i for i, _r, _t in insns], [0, 3])


class ScopeAcrossPrograms(unittest.TestCase):
    """The safety argument for keying on the call rather than an address range.

    `INLINE_ARG_CALLS` has no idea which program it is walking -- `converges_from`
    is handed a bare file offset -- so the guard is that the idiom does not occur
    in the main EC image at all, and the guard fails loudly if that stops being
    true."""

    def test_the_idiom_occurs_nowhere_in_the_main_ec_image(self):
        d = FIRMWARE.read_bytes()
        pat = bytes([0x12, TARGET >> 8, TARGET & 0xFF])
        ec = [off for off in range(0, len(d) - len(pat) + 1)
              if d[off:off + len(pat)] == pat
              and T.region_of(off, True)[0] in ("common", "bank0", "bank1")]
        self.assertEqual(ec, [],
                         f"`lcall 0x{TARGET:04x}` now appears at {len(ec)} "
                         "file offset(s) in the main EC image, so the "
                         "special case is not inert there and every committed "
                         "main-EC listing may need regenerating")

    def test_it_occurs_in_the_pd_image_so_the_table_is_not_vacuous(self):
        # The other half: a table entry nothing calls is a table entry nothing
        # tests, and the count is here so the zero above cannot be satisfied by
        # a wrong target address.
        d = FIRMWARE.read_bytes()
        off, magic = T.PD_MARKER
        self.assertEqual(d[off:off + len(magic)], magic,
                         "the pd marker moved; this file's region split is now "
                         "reading somebody else's bytes")
        pat = bytes([0x12, TARGET >> 8, TARGET & 0xFF])
        self.assertGreater(
            sum(1 for o in range(0, len(d) - len(pat) + 1)
                if d[o:o + len(pat)] == pat
                and T.region_of(o, True)[0] == "pd-image"),
            0)


if __name__ == '__main__':
    unittest.main()
