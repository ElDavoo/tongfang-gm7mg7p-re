#!/usr/bin/env python3
"""Offline checks for `ecrw.py`'s own arithmetic; no EC, no driver, no IOCTL.

This is the one suite here that exercises the *real* `ecrw.py` rather than a
stand-in for it, and it can: `ecrw.py` reaches kernel32 through
`ctypes.WinDLL`, which does not exist on Linux, so putting a fake `ecrw` in
front of it -- which is what `ecrw_fake.py` is for, and what every other suite
in this directory does -- would test the fake. Instead a fake kernel32 goes in
front of it, which is the only boundary the module has.

The fake has to stand in at construction rather than at import:
`ecrw.py` binds kernel32 on the first `Ec()` (`_kernel32`), so a fake put in
front of the module alone would leave every `Ec()` here reaching for a
`WinDLL` that is not there. `load_modules` primes the resolver inside its
patch window and the cache carries the rest.

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
from unittest.mock import patch

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

    def ec_addresses(self):
        """Every EC byte each recorded read touched, both IOCTLs.

        `offsets()` answers for `MMRD` alone, and reads a four-byte buffer's
        physical address; a byte read carries its 16-bit offset in the first
        two. What the fan-tach cases want is the union over both, because a
        page byte that reached the wire is what they are about however it got
        there -- and an `MMRD` touches four addresses, not one, so counting
        offsets would under-report a block read by three quarters.
        """
        out = []
        for code, buf in self.calls:
            if code == FAKE_IOCTL_ECRR:
                out.append(int.from_bytes(buf[:2], "little"))
            else:
                first = int.from_bytes(buf[:4], "little") - FAKE_EC_BASE
                out.extend(range(first, first + 4))
        return out

    def codes(self):
        return [code for code, _ in self.calls]


def load_modules():
    """Import the real `ecrw.py`, and the probe that imports it, on a fake.

    `ctypes.wintypes` imports cleanly on Linux, so `WinDLL` is the only name
    that has to be standing in -- and `ecrw.py` binds it on the first `Ec()`
    rather than at import, so the window has to stay open across that call and
    not merely across the module body.

    Which is what the priming `_kernel32()` here does: inside the window it
    builds the fake and caches it on the module, so every later `Ec()` in this
    suite reuses it after `ctypes.WinDLL` has gone back to not existing. That
    is safe because `tools/run-tests.sh` gives each suite file its own
    interpreter, and a cache that outlived it would be this suite deciding the
    binding for whatever ran next -- the same accident
    `docs/findings.md` §16 is about, one object narrower. It also asserts
    something the rest of the suite cannot: that the resolver caches, which is
    what lets the patch window be this narrow.

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
        if ecrw._kernel32() is not k32:
            raise AssertionError("the resolver did not cache the fake kernel32")
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

    def test_the_resolver_declared_the_signatures_it_loaded(self):
        # The `argtypes`/`restype` block moved off module scope into
        # `_kernel32` when the bind went lazy, so the fake handle is where that
        # move can go wrong: load the DLL, forget the signatures, and every
        # call passes whatever ctypes defaults to -- an int where a pointer is
        # expected, truncated silently, with no exception anywhere. Read off
        # the fake rather than asserted as literals, because what is checked is
        # that the resolver *wrote* them, not what the right values are.
        k32 = ecrw._k32
        self.assertIsNotNone(k32, "the resolver did not cache a handle")
        for name in ("CreateFileW", "DeviceIoControl", "CloseHandle"):
            self.assertIsNotNone(getattr(k32, name).argtypes, name)
            self.assertIsNotNone(getattr(k32, name).restype, name)
        # And it declared them on the object it handed back rather than on a
        # second load: one bind, one set of signatures.
        self.assertIs(ecrw._kernel32(), k32)

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
    def dump(self, *argv, gap="0"):
        # `--gap-ms 0` unless a case says otherwise, so the case that is about
        # a flag is not also the case that pays milliseconds per read. The
        # default is 6 ms for a reason no case here can check; `DumpPacingTests`
        # is where the value itself is held.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(ecrw.main(["dump", *argv, "--gap-ms", gap]), 0)
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

    # 8. The unaligned escape, `read_dword_unaligned` and the `mmrd` command.
    #    Issue #147 words its check as one MMRD at 0xFE410000 + 0x0751, where
    #    0x0751 % 4 == 1, and the block path cannot put that question. These
    #    hold what the escape does, and -- the half that matters -- what it
    #    cannot reach: an escape that leaked into a sweep would issue unaligned
    #    four-byte reads over the fan-tach page, which is the access #94 is
    #    about, so the watch sets are swept here against the real
    #    decomposition rather than argued for in a docstring.
    def test_the_escape_marshals_the_physical_address_as_read_dword_does(self):
        self.ec.read_dword_unaligned(0x0751)
        # One address, one IOCTL, and nothing else: this is the whole reason
        # it is a command rather than a mode. A sweep that could reach it
        # would issue as many as it liked.
        self.assertEqual(K32.codes(), [FAKE_IOCTL_MMRD])
        (buf,) = [b for _, b in K32.calls]
        # Byte for byte what read_dword(0x0750) puts on the wire, one byte
        # along in the address: the ASL hands an MMRD operand to MMRW
        # unchanged (dsdt.dsl:50481), so the tool still adds EC_BASE itself.
        self.assertEqual(buf[:4], (FAKE_EC_BASE + 0x0751).to_bytes(4, "little"))
        self.assertEqual(int.from_bytes(buf[:4], "little"), 0xFE410751)
        self.assertNotEqual(int.from_bytes(buf[:4], "little"),
                            int.from_bytes((FAKE_EC_BASE + 0x0750)
                                           .to_bytes(4, "little"), "little"))
        # And the same zeroed tail the byte path and the aligned dword send,
        # not a second address.
        self.assertEqual(buf[4:], b"\x00" * 4)

    def test_the_escape_returns_the_four_bytes_from_its_own_start(self):
        self.assertEqual(self.ec.read_dword_unaligned(0x0751),
                         K32.ram[0x0751:0x0755])
        # "The same four the aligned block at 0x0750 returns" is read here as
        # the *overlap*, not as byte equality: the two reads are a one-byte
        # shift, so against this fixture they share three positions and differ
        # at the two ends, and an equality assertion would fail an
        # implementation that is correct. Held against the real read_dword
        # rather than against the fixture directly, so it is the two methods
        # that are pinned to each other.
        aligned = self.ec.read_dword(0x0750)
        unaligned = self.ec.read_dword_unaligned(0x0751)
        self.assertEqual(unaligned[:3], aligned[1:])
        # The ends differ here because the fake's RAM is a 0x00..0xFF ramp and
        # 0x0750 != 0x0754. That is what makes the overlap above a check: a
        # fixture that could not tell the two reads apart would satisfy it
        # whatever the escape did.
        self.assertNotEqual(unaligned[3], aligned[0])
        # The limit of the same claim: on RAM that does not move under either
        # read, an unaligned dword and the aligned dword covering it return
        # the same four bytes. Which of the four is the lowest address is a
        # reading of the marshalling, not something this can settle -- the
        # fake answers in the order the bytes are indexed by offset, which is
        # the very assumption under test.
        K32.ram = bytes(0x10000)
        self.assertEqual(self.ec.read_dword_unaligned(0x0751),
                         self.ec.read_dword(0x0750))

    def test_the_aligned_paths_still_refuse_the_unaligned_start(self):
        # The escape existing is not the escape being on. The escape is
        # called first, and read_dword then still refuses the address the
        # escape exists to reach -- so the refusal is a property of the
        # method, not of whether the other one has been used. K32.calls is
        # empty at the end, so it is a bound and not a failed IOCTL.
        # (test_a_dword_start_off_the_block_grid_is_refused holds the same
        # refusal on its own; this is that case again with the escape run
        # first, which is the adjacency that is new.)
        self.ec.read_dword_unaligned(0x0751)
        K32.calls = []
        for addr in (0x0751, 0x0751 % 4):
            with self.assertRaises(ValueError):
                self.ec.read_dword(addr)
        self.assertEqual(K32.calls, [])

    def test_the_escape_is_the_only_unaligned_mmrd_any_block_path_issues(self):
        # The escape, called, and then the three real watch sets swept. If
        # `readmany` or `read_dword` could reach the unaligned path, one of
        # these offsets would be odd -- and an odd offset is a four-byte
        # access whose last byte is somewhere else, which over the fan-tach
        # page is the #94 access the default sets are built to avoid.
        self.ec.read_dword_unaligned(0x0751)
        self.assertEqual(K32.offsets(), [0x0751])
        for addrs in (probe.watch_set(), probe.watch_set(level_block=True),
                      probe.watch_set(watch_page=True)):
            K32.calls = []
            got = self.read_runs(addrs)
            offsets = K32.offsets()
            self.assertTrue(offsets)
            self.assertEqual([hex(o) for o in offsets if o % 4], [],
                             "an unaligned MMRD reached a block sweep")
            self.assertEqual(got, {a: K32.ram[a] for a in addrs})
        # And readmany's own cover of an unaligned range is unchanged by the
        # escape: same keys, and still two aligned blocks rather than one
        # unaligned read. (test_an_unaligned_start_is_covered_and_the_lead_
        # dropped holds the same pair on its own; this is that case again
        # after the escape has run, which is the adjacency that matters.)
        K32.calls = []
        self.assertEqual(sorted(self.ec.readmany(0x0751, 4)),
                         list(range(0x0751, 0x0755)))
        self.assertEqual(K32.offsets(), [0x0750, 0x0754])

    def test_the_escape_loosens_alignment_and_not_the_window(self):
        # 0xFFFD is the last unaligned start that still ends inside the
        # mapped region, and it is accepted; 0xFFFE would end at 0x10001, one
        # byte into 0xFE420000, which is not EC RAM. So the window bound is
        # the one read_dword holds, moved by the single byte the looser
        # alignment makes room for. Asserted as an offset the wire carried and
        # not as the four bytes back: the fake's RAM ends at 0xFFFF, so its own
        # answer there is three real bytes and a padding zero, which is the
        # fixture's edge rather than anything read_dword_unaligned did.
        self.assertEqual(len(self.ec.read_dword_unaligned(0xFFFD)), 4)
        self.assertEqual(K32.offsets(), [0xFFFD])
        K32.calls = []
        for addr in (0xFFFE, 0x10000, -1):
            with self.assertRaises(ValueError):
                self.ec.read_dword_unaligned(addr)
        self.assertEqual(K32.calls, [])

    def test_the_mmrd_command_prints_the_physical_address_and_four_bare_bytes(self):
        # The command line is a separate thing from the method: argparse
        # accepts a string, `EC_BASE` is added here rather than by the
        # operator, and the line printed is where the byte-order question
        # would otherwise get settled by assumption. The whole output is
        # asserted, so a per-byte EC-offset label added later -- the shape that
        # would make this a confirmation of the reading rather than a
        # measurement of it -- fails here.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(ecrw.main(["mmrd", "0x0751"]), 0)
        self.assertEqual(K32.codes(), [FAKE_IOCTL_MMRD])
        self.assertEqual(K32.offsets(), [0x0751])
        # 0x0751, 0x0752, 0x0753 and 0x0754 out of the fake's ramp, and the
        # physical address 0xFE410000 + 0x0751 as the label.
        self.assertEqual(out.getvalue(), "0xFE410751: 51 52 53 54\n")


class DumpPacingTests(unittest.TestCase):
    """`dump` leaves out the fan-tach page and sleeps between its reads.

    Same question as `test_ec_watch.py`'s, and asked the same way -- over the
    IOCTLs the fake kernel32 recorded rather than over what the dump printed.
    A hexdump that happened to look right would not show a read that was
    issued and then discarded from the output, and the whole of #94 is about
    a read that was issued.

    A sibling of `EcrwTests` rather than a subclass of it: the fixture it
    needs is the module-level `K32` and its own `setUp`, and inheriting would
    run every case above a second time under a second name.

    Nothing here is evidence about this machine's fans. HydroControl reports
    the stall on a sibling board and names the 6 ms; this pins that `dump`'s
    defaults match those reports, not that they are right here.
    """

    # HydroControl's figure for the OEM software and uniwill-laptop, and this
    # repository's default. Not measured on this machine.
    DEFAULT_MS = 6

    def setUp(self):
        # The recorded calls are this test's, as above.
        K32.calls = []
        K32.ram = bytes(range(256)) * 256

    def run_dump(self, *argv):
        """`(rc, stdout, stderr)` for one `dump` against the fake kernel32.

        Both streams, and not through the `dump()` helper above: what these
        cases read is mostly the notice, and that is on stderr so the hexdump
        on stdout stays pipeable.
        """
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ecrw.main(["dump", *argv])
        return rc, out.getvalue(), err.getvalue()

    def run_paced(self, *argv):
        """As `run_dump`, with `time.sleep` recorded rather than taken."""
        sleeps = []
        clock = type("FakeTime", (), {"sleep": lambda _, s: sleeps.append(s)})()
        with patch.object(ecrw, "time", clock):
            return self.run_dump(*argv), sleeps

    def test_a_full_range_dump_reads_no_fan_tach_byte(self):
        K32.calls = []
        rc, _, _ = self.run_dump("0x0000", "0x0800", "--gap-ms", "0")
        self.assertEqual(rc, 0)
        # The wire, not the output: these are the bytes that went to the
        # driver, and the fan-tach page is not among them.
        self.assertEqual(set(K32.ec_addresses()) & FAN_TACH, set())
        # ...and the rest of the range really was read, so this is not passing
        # because the dump did nothing.
        self.assertTrue(set(K32.ec_addresses()))

    def test_the_block_path_reads_no_fan_tach_byte_either(self):
        K32.calls = []
        rc, _, _ = self.run_dump("0x0000", "0x0800", "--block", "--gap-ms", "0")
        self.assertEqual(rc, 0)
        self.assertTrue(K32.codes())
        # `MMRD` covers four bytes, so a block read across the page would be
        # a wider access to it rather than a narrower one (#94). `offsets()`
        # is the block start of each one, and those are 4-aligned, so the
        # page's own blocks are the ones that must be missing.
        self.assertEqual(set(K32.offsets()) & FAN_TACH, set())
        self.assertEqual(set(K32.ec_addresses()) & FAN_TACH, set())
        # Both halves of the range really were read, split around the page.
        self.assertEqual(min(K32.offsets()), 0x0000)
        self.assertEqual(max(K32.offsets()), 0x07FC)

    def test_the_flag_reads_the_page_and_says_so(self):
        K32.calls = []
        rc, _, err = self.run_dump("0x0460", "0x10", "--include-fan-tach",
                                   "--gap-ms", "0")
        self.assertEqual(rc, 0)
        self.assertEqual(set(K32.ec_addresses()), FAN_TACH)
        # Said where the operator is looking: a page read on purpose and one
        # read by accident are the same IOCTLs.
        self.assertIn("0x0460-0x046F", err)
        self.assertIn("#94", err)

    def test_the_exclusion_is_marked_in_the_hexdump_and_named_on_stderr(self):
        rc, out, err = self.run_dump("0x0450", "0x30", "--gap-ms", "0")
        self.assertEqual(rc, 0)
        self.assertIn("not reading 16 byte(s)", err)
        self.assertIn("0x0460-0x046F", err)
        # '--' is an address that was not read. A zero there would read as a
        # byte the EC returned, which is the failure the marking exists to
        # make impossible.
        page_row = [ln for ln in out.splitlines() if ln.startswith("0460:")]
        self.assertEqual(len(page_row), 1)
        self.assertEqual(page_row[0], "0460: " + "-- " * 15 + "--")
        # The rows either side are whole, so the marking did not shift them.
        for start in ("0450", "0470"):
            row = [ln for ln in out.splitlines() if ln.startswith(f"{start}:")]
            self.assertEqual(len(row), 1)
            self.assertNotIn("--", row[0])

    def test_a_dump_entirely_inside_the_page_says_it_read_nothing(self):
        K32.calls = []
        rc, out, err = self.run_dump("0x0460", "0x10", "--gap-ms", "0")
        # A dump that read nothing and printed nothing is indistinguishable
        # from a dump that read nothing and moved nothing, which is the reading
        # #94 is about. So it says so, and issues no IOCTL to say it with.
        self.assertNotEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertEqual(K32.calls, [])
        self.assertIn("nothing read", err)
        self.assertIn("0x0460-0x046F", err)
        self.assertIn("--include-fan-tach", err)

    def test_a_dump_entirely_inside_the_page_runs_with_the_flag(self):
        rc, out, _ = self.run_dump("0x0460", "0x10", "--include-fan-tach",
                                   "--gap-ms", "0")
        self.assertEqual(rc, 0)
        self.assertIn("0460: 60 61 62 63 64 65 66 67 68 69 6a 6b 6c 6d 6e 6f",
                      out)

    def test_a_range_off_the_page_is_untouched(self):
        K32.calls = []
        rc, out, err = self.run_dump("0x0750", "0x20", "--gap-ms", "0")
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")
        self.assertNotIn("--", out)
        self.assertEqual(K32.codes(), [FAKE_IOCTL_ECRR] * 32)

    def test_the_default_gap_reaches_the_sleep(self):
        (rc, _, _), sleeps = self.run_paced("0x0750", "0x10")
        self.assertEqual(rc, 0)
        # The value is this file's, not the module's read back: a default that
        # had changed would have to change here first to still pass.
        self.assertEqual(sleeps, [self.DEFAULT_MS / 1000] * 16)

    def test_the_gap_flag_is_what_the_operator_asked_for(self):
        (_, _, _), sleeps = self.run_paced("0x0750", "0x10", "--gap-ms", "2.5")
        self.assertEqual(sleeps, [0.0025] * 16)

    def test_the_gap_is_paid_per_read_call_on_the_block_path_too(self):
        (_, _, _), sleeps = self.run_paced("0x0000", "0x0800", "--block")
        # Two calls into the driver, so two gaps -- for the same range the
        # byte path would have read 2032 times. A `readmany` issues one
        # IOCTL per four bytes without coming back here, so the gap is per
        # call and --block is not the paced path. Leaving it unpaced would
        # have left the identical hazard reachable through the back door of
        # this tool.
        self.assertEqual(sleeps, [self.DEFAULT_MS / 1000] * 2)

    def test_how_many_ioctls_a_block_sweep_of_the_default_range_buries(
            self):
        K32.calls = []
        rc, _, _ = self.run_dump("0x0000", "0x0800", "--block", "--gap-ms", "0")
        self.assertEqual(rc, 0)
        # The number `docs/findings/ec-read-pacing-fan-page.md` quotes for why
        # `--block` is not the paced path, asserted rather than left to the
        # prose: `readmany` issues one `MMRD` per four bytes, so the two runs
        # the exclusion leaves -- 0x460 and 0x390 bytes -- are 280 + 228 = 508
        # IOCTLs under two gaps. A docstring or a write-up that understated
        # this is what put "four IOCTLs" there in the first place, and the
        # direction of the error matters: it is what an operator reading that
        # section would conclude about an unpaced sweep.
        self.assertEqual(len(K32.calls), (0x460 + 0x390) // 4)
        # All `MMRD`, so the count is the block path's and not the byte one's:
        # the same range per byte would be 2032 `ECRR` under 2032 gaps.
        self.assertEqual(set(K32.codes()), {FAKE_IOCTL_MMRD})


if __name__ == "__main__":
    unittest.main()
