#!/usr/bin/env python3
"""Offline checks for `ecrw.py`'s own arithmetic; no EC, no driver, no IOCTL.

This is the one suite here that exercises the *real* `ecrw.py` rather than a
stand-in for it, and it can: `ecrw.py` binds kernel32 through
`ctypes.WinDLL` at import time (ecrw.py:69), and there is no `WinDLL` on
Linux, so putting a fake `ecrw` in front of it -- which is what
`ecrw_fake.py` is for, and what every other suite in this directory does --
would test the fake. Instead a fake kernel32 goes in front of it, which is the
only boundary the module has.

What that buys: `read_dword` and `readmany` run for real, over a fake EC RAM
the fake answers out of, so a block that asked for the wrong address, the
wrong width or in the wrong order returns the wrong bytes instead of passing.
The IOCTL codes, the little-endian marshalling and the aligned-block
arithmetic are all asserted against the bytes that would have gone on the wire.

`read()` is in here too, and it is here to be pinned rather than admired: the
per-byte path is the default everywhere in this directory, so the 52 IOCTLs
the block path exists to avoid must not have come at the cost of it.
"""
import contextlib
import ctypes
import importlib.util
import io
from pathlib import Path
import sys
import unittest

# The codes the fake answers, written out rather than read off the module,
# because the module is not importable until the fake kernel32 is in place.
# test_the_ioctl_codes_are_the_ones_the_analysis_file_names is what holds the
# two together.
FAKE_IOCTL_ECRR = 0x9C40A488
FAKE_IOCTL_MMRD = 0x9C40A494
FAKE_EC_BASE = 0xFE410000


class FakeProc:
    """One kernel32 export, callable.

    `ecrw.py` assigns `.argtypes` and `.restype` onto each of these while it
    imports, so the attributes have to exist and be writable; the call is the
    fake's own.
    """

    def __init__(self, fn):
        self._fn = fn
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self._fn(*args)


class FakeKernel32:
    """64 KB of EC RAM, and the two read IOCTLs answered out of it.

    The RAM is a repeating 0x00..0xFF pattern, so every offset in the window
    reads differently from its neighbours and a block that shifted by one would
    return a different answer rather than the same one. `MMRD` answers with
    `ram[off:off+4]` and `ECRR` with `ram[off]` -- the whole of the fake's
    model, and the whole of what a read means here.

    Every `DeviceIoControl` is recorded as `(code, in-bytes)`, so a test can
    assert the wire shape and not only the value that came back.
    """

    def __init__(self):
        self.ram = bytes(range(256)) * 256
        self.calls = []
        self.CreateFileW = FakeProc(lambda *args: 0x1234)
        self.CloseHandle = FakeProc(lambda *args: True)
        self.DeviceIoControl = FakeProc(self._ioctl)

    def _ioctl(self, handle, code, inbuf, inlen, outbuf, outlen, returned,
               overlapped):
        self.calls.append((code, bytes(inbuf)[:inlen]))
        data = bytes(inbuf)
        if code == FAKE_IOCTL_ECRR:
            off = int.from_bytes(data[:2], "little")
            outbuf[0] = self.ram[off]
            returned._obj.value = 4
        elif code == FAKE_IOCTL_MMRD:
            off = int.from_bytes(data[:4], "little") - FAKE_EC_BASE
            # Byte for byte, lowest address first: the copy-back the handler
            # does is four byte stores in order, so anything else is a different
            # access and the fake says so.
            for i, byte in enumerate(self.ram[off:off + 4]):
                outbuf[i] = byte
            returned._obj.value = 4
        else:
            raise AssertionError(f"unexpected IOCTL 0x{code:08X}")
        return True

    def offsets(self):
        """The EC offset of every recorded read, in order."""
        return [int.from_bytes(buf[:4], "little") - FAKE_EC_BASE
                for code, buf in self.calls if code == FAKE_IOCTL_MMRD]

    def codes(self):
        return [code for code, _ in self.calls]


def load_modules():
    """Import the real `ecrw.py`, and the probe that imports it, on a fake.

    `ctypes.wintypes` imports cleanly on Linux, so `WinDLL` is the only name
    that has to be standing in -- and it has to be standing in before the
    module body runs, because the binding is at import time.

    `manual_fan_ctrl_probe.py` is loaded in the same window, because it does
    `from ecrw import Ec` and this suite wants the watch set off the file the
    tool actually reads rather than a copy of it. That import is the reason
    `ecrw` has to be in `sys.modules` at all while this runs; whatever was
    under the name before goes back afterwards, because a suite that leaves a
    real `ecrw` behind it is deciding the import order for the other suites in
    this directory, which is the accident `docs/findings.md` §16 is about.
    """
    k32 = FakeKernel32()
    borrowed = sys.modules.get("ecrw", None)
    had_win_dll = hasattr(ctypes, "WinDLL")
    ctypes.WinDLL = lambda name, **kw: k32
    try:
        ecrw = _load("ecrw", "ecrw.py")
        sys.modules["ecrw"] = ecrw
        probe = _load("manual_fan_ctrl_probe", "manual_fan_ctrl_probe.py")
    finally:
        if not had_win_dll:
            del ctypes.WinDLL
        if borrowed is None:
            del sys.modules["ecrw"]
        else:
            sys.modules["ecrw"] = borrowed
    return ecrw, k32, probe


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ecrw, K32, probe = load_modules()

FAN_TACH = set(range(0x0460, 0x0470))


class EcrwTests(unittest.TestCase):
    def setUp(self):
        # One Ec per test on a re-primed fake, so the recorded calls are this
        # test's and nothing else sees.
        K32.calls = []
        K32.ram = bytes(range(256)) * 256
        self.ec = ecrw.Ec()

    def read_runs(self, addrs):
        """What a block sweep of `addrs` costs, against the real code."""
        out = {}
        for start, length in ecrw.block_runs(addrs):
            out.update(self.ec.readmany(start, length))
        return out

    # 1. The wire shape. This IOCTL is supposed to be a 32-bit read of a full
    #    physical address, and the only way to hold it to that is to look at
    #    what went into the buffer.
    def test_the_mmrd_ioctl_carries_the_physical_address_little_endian(self):
        self.ec.read_dword(0x0750)
        self.assertEqual(K32.codes(), [FAKE_IOCTL_MMRD])
        (buf,) = [b for _, b in K32.calls]
        self.assertEqual(buf[:4], (FAKE_EC_BASE + 0x0750).to_bytes(4, "little"))
        # The offset goes out as a physical address, not as the 16-bit EC
        # offset the byte path sends: MMRD's ASL hands Arg0 straight to MMRW
        # (dsdt.dsl:50481) where ECRR adds 0xFE410000 itself (:50497).
        self.assertEqual(int.from_bytes(buf[:4], "little"), 0xFE410750)
        # And the rest of the buffer is the zeroed tail the byte path also
        # sends, not a second address.
        self.assertEqual(buf[4:], b"\x00" * 4)

    def test_a_dword_returns_the_four_bytes_at_that_offset(self):
        self.assertEqual(self.ec.read_dword(0x0750),
                         K32.ram[0x0750:0x0754])
        self.assertEqual(self.ec.read_dword(0x0460), K32.ram[0x0460:0x0464])

    def test_the_ioctl_codes_are_the_ones_the_analysis_file_names(self):
        # Pinned here rather than read off the module in the fake, so this is a
        # check against windows/native/ACPIDriver.sys.analysis.md's table and
        # not a tautology.
        self.assertEqual(ecrw.IOCTL_ECRR, FAKE_IOCTL_ECRR)
        self.assertEqual(ecrw.IOCTL_MMRD, FAKE_IOCTL_MMRD)
        self.assertEqual(ecrw.EC_BASE, FAKE_EC_BASE)
        self.assertEqual(ecrw.EC_SIZE, 0x10000)

    # 2. Decomposition. A range is covered by the aligned blocks enclosing it,
    #    and the keys that come back are the range and not the blocks.
    def test_an_aligned_range_decomposes_into_its_own_blocks(self):
        got = self.ec.readmany(0x0750, 8)
        self.assertEqual(K32.offsets(), [0x0750, 0x0754])
        self.assertEqual(sorted(got), list(range(0x0750, 0x0758)))
        self.assertEqual(got, {a: K32.ram[a] for a in range(0x0750, 0x0758)})

    def test_the_watch_set_costs_56_ioctls_not_52(self):
        # The regression guard for the arithmetic in issue #147. 206/4 = 52 is
        # the count if the watch set were contiguous, and it is not: WATCH
        # scatters 14 addresses over 0x0743-0x07C6 onto 8 blocks, so the
        # sweep is 8 + 24 + 24 = 56. 224 bytes are read for 206 addresses --
        # fewer IOCTLs is not fewer bytes, and a docstring that quotes one
        # without the other would be quoting half of it.
        got = self.read_runs(probe.ALL)
        self.assertEqual(len(probe.ALL), 206)
        self.assertEqual(K32.codes(), [FAKE_IOCTL_MMRD] * 56)
        self.assertEqual(len(K32.offsets()) * 4, 224)
        self.assertEqual(got, {a: K32.ram[a] for a in probe.ALL})

    def test_the_three_watch_set_runs_cost_8_24_and_24(self):
        counts = [sum(1 for _ in range(start & ~3,
                                        ((start + length - 1) & ~3) + 1, 4))
                  for start, length in ecrw.block_runs(probe.ALL)]
        self.assertEqual(counts, [24, 2, 1, 2, 2, 1, 24])
        self.assertEqual(sum(counts), 56)

    def test_block_runs_groups_a_scattered_set_and_dedups_it(self):
        self.assertEqual(ecrw.block_runs([0x07C5, 0x0751, 0x0750, 0x0751]),
                         [(0x0750, 2), (0x07C5, 1)])
        self.assertEqual(ecrw.block_runs([]), [])

    # 3. The window's end. 0xFFFE would be the last two bytes of the window, and
    #    a dword read there runs into 0xFE420000, which is not EC RAM.
    def test_no_block_read_past_the_end_of_the_window(self):
        self.ec.readmany(0xFFF8, 8)
        self.assertEqual(K32.offsets(), [0xFFF8, 0xFFFC])
        self.ec.readmany(0xFFFC, 4)
        self.assertEqual(K32.offsets()[-1], 0xFFFC)
        for off in K32.offsets():
            self.assertLessEqual(off + 4, ecrw.EC_SIZE)

    def test_a_dword_start_off_the_block_grid_is_refused(self):
        for addr in (0xFFFE, 0x0751, 0x10000, -4):
            with self.assertRaises(ValueError):
                self.ec.read_dword(addr)
        self.assertEqual(K32.calls, [])

    def test_a_range_off_the_end_of_the_window_is_refused(self):
        with self.assertRaises(ValueError):
            self.ec.readmany(0xFFF0, 0x20)
        with self.assertRaises(ValueError):
            self.ec.readmany(0x10000, 4)
        self.assertEqual(K32.calls, [])

    def test_an_empty_range_reads_nothing(self):
        self.assertEqual(self.ec.readmany(0x0750, 0), {})
        self.assertEqual(K32.calls, [])

    # 4. An unaligned start. `0x0751` is the byte the whole fan-mode question
    #    hangs off, and it is one byte into its block.
    def test_an_unaligned_start_is_covered_and_the_lead_dropped(self):
        got = self.ec.readmany(0x0751, 4)
        # Two blocks, because 0x0751-0x0754 straddles them: the enclosing-block
        # cover of the range, not a 4-byte read the alignment cannot do.
        self.assertEqual(K32.offsets(), [0x0750, 0x0754])
        self.assertEqual(sorted(got), list(range(0x0751, 0x0755)))
        self.assertEqual(got, {a: K32.ram[a] for a in range(0x0751, 0x0755)})
        # 0x0750 was read and is not returned: a caller swapping readmany for
        # a per-byte loop must not have to know that the keys overshot.
        self.assertNotIn(0x0750, got)

    def test_a_single_unaligned_byte_costs_one_block(self):
        self.assertEqual(self.ec.readmany(0x0751, 1), {0x0751: K32.ram[0x0751]})
        self.assertEqual(K32.offsets(), [0x0750])

    def test_a_range_ending_mid_block_drops_the_tail(self):
        got = self.ec.readmany(0x0750, 6)
        self.assertEqual(K32.offsets(), [0x0750, 0x0754])
        self.assertEqual(sorted(got), list(range(0x0750, 0x0756)))

    # 5. The default path, pinned. Same buffer, same IOCTL, same byte back --
    #    the block path is an opt-in addition, not a rewrite.
    def test_the_per_byte_read_is_unchanged(self):
        self.assertEqual(self.ec.read(0x0751), K32.ram[0x0751])
        self.assertEqual(K32.codes(), [FAKE_IOCTL_ECRR])
        (buf,) = [b for _, b in K32.calls]
        # The 16-bit EC offset, little-endian, in a buffer whose tail is
        # zeroed: byte for byte what ecrw.py has always sent.
        self.assertEqual(buf, bytes([0x51, 0x07, 0, 0, 0, 0, 0, 0]))
        self.assertNotEqual(buf[:4], (FAKE_EC_BASE + 0x0751).to_bytes(4, "little"))

    def test_read_outside_the_window_is_refused_before_the_ioctl(self):
        for addr in (0x10000, -1):
            with self.assertRaises(ValueError):
                self.ec.read(addr)
        self.assertEqual(K32.calls, [])

    def test_the_two_paths_agree_byte_for_byte_where_they_overlap(self):
        # The property the whole comparison is after, on the one machine this
        # suite cannot reach: given bytes that do not change under either path,
        # the two agree. It is worth having against a fixture precisely because
        # it is not the hardware result.
        K32.ram = bytes(0x10000)
        per_byte = {a: self.ec.read(a) for a in range(0x0750, 0x0760)}
        K32.calls = []
        block = self.ec.readmany(0x0750, 0x10)
        self.assertEqual(block, per_byte)

    # 6. The `dump --block` flag itself. "Same output" is what the usage line
    #    and the flag's help both claim, so it is checked rather than left to
    #    the reader of readmany's docstring.
    def dump(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(ecrw.main(["dump", *argv]), 0)
        return out.getvalue()

    def test_the_block_flag_changes_the_call_count_and_not_the_output(self):
        K32.calls = []
        plain = self.dump("0x0750", "0x20")
        self.assertEqual(K32.codes(), [FAKE_IOCTL_ECRR] * 32)
        K32.calls = []
        blocked = self.dump("0x0750", "0x20", "--block")
        self.assertEqual(K32.codes(), [FAKE_IOCTL_MMRD] * 8)
        self.assertEqual(blocked, plain)

    def test_a_dump_of_an_unaligned_range_prints_the_same_either_way(self):
        # The rows are 16 bytes and the blocks are 4, so an unaligned start and
        # a length that does not end on a boundary is the case where the two
        # paths could print different bytes: readmany covers the enclosing
        # blocks and drops the overshoot, and this holds the printing to the
        # range that was asked for.
        K32.calls = []
        plain = self.dump("0x0751", "0x0a")
        K32.calls = []
        blocked = self.dump("0x0751", "0x0a", "--block")
        self.assertEqual(blocked, plain)
        self.assertIn("0751: 51 52 53 54 55 56 57 58 59 5a", plain)

    # 7. The watch set's own safety rule, checked against the real
    #    decomposition rather than against a fake's report of it. #94 is why
    #    every watch set here stops before 0x0460, and a block path that
    #    straddles the page is a wider access to it, not a safer one.
    def test_no_block_of_the_watch_set_touches_the_fan_tach_page(self):
        covered = set()
        for start, length in ecrw.block_runs(probe.watch_set(True)):
            first = start & ~3
            last = (start + length - 1) & ~3
            covered.update(range(first, last + 4))
        self.assertEqual(covered & FAN_TACH, set())
        # ...and every set the tool can be asked for is checked in its own
        # right, rather than the union of them: a set that grows later -- the
        # page arm is one already -- has to fail here too rather than be
        # covered by a sibling's clearance.
        for addrs in (probe.watch_set(), probe.watch_set(level_block=True),
                      probe.watch_set(watch_page=True),
                      probe.watch_set(level_block=True, watch_page=True)):
            covered = set()
            for start, length in ecrw.block_runs(addrs):
                covered.update(range(start & ~3,
                                     ((start + length - 1) & ~3) + 4))
            self.assertEqual(covered & FAN_TACH, set())

    # The page arm against the real IOCTLs, which is the only way to see that
    # 112 is what the wire carries and not what the set's address count
    # divided by four suggests. Both of its ranges are 4-aligned, so this is
    # the one watch set with no padding: 448 addresses, 448 bytes read.
    def test_the_page_arm_costs_112_ioctls_and_reads_448_bytes(self):
        addrs = probe.watch_set(watch_page=True)
        self.assertEqual(len(addrs), 448)
        self.assertEqual(ecrw.block_runs(addrs),
                         [(0x0400, 0x60), (0x0700, 0x100), (0x0F00, 0x60)])
        self.assertEqual(K32.codes(), [])  # nothing read yet
        got = self.read_runs(addrs)
        self.assertEqual(K32.codes(), [FAKE_IOCTL_MMRD] * 112)
        self.assertEqual(len(K32.offsets()) * 4, 448)
        self.assertEqual(got, {a: K32.ram[a] for a in addrs})
        # No MMRD outside the three ranges, so the access is the width the
        # default set already issues and only the count moves.
        self.assertEqual(sorted({run[0] for run in ecrw.block_runs(addrs)}),
                         [0x0400, 0x0700, 0x0F00])
        self.assertTrue(all(any(start <= o < start + length
                                for start, length in ecrw.block_runs(addrs))
                            for o in K32.offsets()))


if __name__ == "__main__":
    unittest.main()
