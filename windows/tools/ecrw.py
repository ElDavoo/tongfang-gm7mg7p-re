#!/usr/bin/env python3
r"""Read/write EC RAM from Windows through the vendor's own ACPIDriver IOCTLs.

This is the Windows counterpart of `ec/tools/ecmem.py`. Where that tool maps
physical `0xFE410000` itself via `/dev/mem`, this one asks the vendor's kernel
driver to do it, over exactly the interface `ACPIDriverDll.dll`'s `ReadEC` /
`WriteEC` use (`windows/native/ACPIDriver.sys.analysis.md`,
`windows/native/ACPIDriverDll.dll.analysis.md`):

    CreateFileW(r"\\.\ACPIDriver", GENERIC_READ|GENERIC_WRITE, ...)
    DeviceIoControl(h, 0x9C40A488, buf, ...)   # ECRR -> ACPI ECRR(addr)
    DeviceIoControl(h, 0x9C40A48C, buf, ...)   # ECRW -> ACPI ECRW(addr, val)
    DeviceIoControl(h, 0x9C40A494, buf, ...)   # MMRD -> ACPI MMRD(phys)

    buf[0..1] = 16-bit EC address, little-endian
    buf[4]    = byte value (ECRW only)
    buf[0]    = byte value on return (ECRR)

`--block` reads four bytes per IOCTL instead of one, through `MMRD`, the
driver's 32-bit case of the same `MMRW` the byte path already uses. It is off
by default and nothing in this repository has ever run it. What is static and
committed is that the handler marshals all four bytes and copies four bytes
back (`windows/native/ACPIDriver.sys.analysis.md`); what is not established is
that the BIOS returns what four single reads would return for the same four
addresses, that a read straddling a boundary behaves, or that the path is any
faster. The comparison that would answer the first of those is written down in
`manual_fan_ctrl_probe.py`'s docstring, for a human with the machine.

The DSDT's `ECRR` is `MMRW(0xFE410000 + Arg0, 0, 0, 0)` (`evidence/acpi/dsdt.dsl`
:50497), so a read here and a read through `ec/tools/ecmem.py` on Linux are the
same physical byte, reached two different ways.

No driver is installed by this tool. It requires the vendor stack's driver to be
already present and started; on the machine this was developed against that is
`UWACPIDriver.sys` (Control Center Service 3.1.39.0), which creates the same
`\DosDevices\ACPIDriver` symlink the 3.1.6.0-era `ACPIDriver.sys` does and
carries the same 21 IOCTL codes. Must be run elevated.

Usage:
  ecrw.py read  0x7b9 0x7d0 ...
  ecrw.py dump  0x0700 0x100          # start, length
  ecrw.py dump  0x0700 0x100 --block  # 4 bytes per IOCTL, same output
  ecrw.py write 0x7b9=60 0x7d0=55     # requires --i-mean-it

Addresses and values accept 0x-prefixed hex or decimal.
"""
import argparse
import ctypes
import sys
from ctypes import wintypes

DEVICE = r"\\.\ACPIDriver"
IOCTL_ECRR = 0x9C40A488
IOCTL_ECRW = 0x9C40A48C
IOCTL_MMRD = 0x9C40A494
# The window ECRR's ASL adds to its argument, and the DSDT maps in full
# (`OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)`,
# evidence/acpi/dsdt.dsl:52193). ECRR(addr) is `MMRW(0xFE410000 + addr, ...)`
# (:50497); MMRD takes a full physical address instead and hands it to MMRW
# unchanged (:50420, :50481), so the block path has to add this itself.
EC_BASE = 0xFE410000
EC_SIZE = 0x10000

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ_WRITE = 0x00000003
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)

_k32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
    wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
]
_k32.CreateFileW.restype = wintypes.HANDLE

_k32.DeviceIoControl.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
    wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
    wintypes.LPVOID,
]
_k32.DeviceIoControl.restype = wintypes.BOOL

_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_k32.CloseHandle.restype = wintypes.BOOL


class EcError(RuntimeError):
    pass


class Ec:
    """One open handle to the vendor driver, reused across calls.

    The vendor's own DLL reopens the device for every single byte; nothing in
    the driver requires that (`IRP_MJ_CREATE`/`CLOSE` just return success), and
    holding the handle makes a 256-byte dump roughly an order of magnitude
    cheaper. Both shapes were exercised against the same registers and returned
    the same values.
    """

    def __init__(self):
        h = _k32.CreateFileW(DEVICE, GENERIC_READ | GENERIC_WRITE,
                             FILE_SHARE_READ_WRITE, None, OPEN_EXISTING, 0, None)
        if h == INVALID_HANDLE_VALUE or h is None:
            err = ctypes.get_last_error()
            raise EcError(
                f"opening {DEVICE} failed (error {err}). "
                "Run elevated, and check the vendor driver is loaded: "
                "`Get-CimInstance Win32_SystemDriver | ? Name -match 'ACPIDriver'`"
            )
        self._h = h

    def close(self):
        if self._h is not None:
            _k32.CloseHandle(self._h)
            self._h = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _ioctl(self, code, buf):
        returned = wintypes.DWORD(0)
        ok = _k32.DeviceIoControl(self._h, code, buf, len(buf), buf, len(buf),
                                  ctypes.byref(returned), None)
        if not ok:
            raise EcError(f"DeviceIoControl(0x{code:08X}) failed, "
                          f"error {ctypes.get_last_error()}")
        return returned.value

    def read(self, addr):
        if not 0 <= addr <= 0xFFFF:
            raise ValueError(f"EC address 0x{addr:X} out of the 16-bit range")
        buf = ctypes.create_string_buffer(8)
        buf[0] = addr & 0xFF
        buf[1] = (addr >> 8) & 0xFF
        self._ioctl(IOCTL_ECRR, buf)
        return buf.raw[0]

    def read_dword(self, addr):
        """One MMRD: four EC bytes at a 4-aligned offset, one IOCTL.

        `addr` is an EC offset; what goes on the wire is a physical address,
        because the handler marshals a full 32-bit one and the ASL adds nothing
        to it. `EC_BASE` is added here for that reason. The four bytes come
        back in ascending address order -- the copy-back is four byte stores out
        of the ACPI output buffer, in order, not one dword store.

        Nothing in this repository has issued one; see this module's docstring
        for what that does and does not make this method.
        """
        if not 0 <= addr <= 0xFFFC or addr % 4:
            # The bound is the block start, not the last byte: a dword starting
            # at 0xFFFC ends at 0xFFFF, and one starting at 0xFFFE would run
            # off the mapped window into 0xFE420000.
            raise ValueError(f"EC address 0x{addr:X} is not a 4-aligned dword "
                             "start in 0x0000-0xFFFC")
        buf = ctypes.create_string_buffer(8)
        for i in range(4):
            buf[i] = (EC_BASE + addr) >> (8 * i) & 0xFF
        self._ioctl(IOCTL_MMRD, buf)
        return buf.raw[:4]

    def readmany(self, start, length):
        """`length` bytes from EC offset `start`, as {addr: byte}.

        Four bytes per IOCTL, keyed by exactly the addresses asked for -- the
        same key set the per-byte path produces, which is what lets a caller
        swap one for the other. A range is covered by the aligned blocks that
        enclose it, so an unaligned `start` (or a `length` that does not end on
        a block boundary) is read past on both sides and the overshoot is
        dropped here. Those bytes are read, not skipped: an unaligned range
        touches bytes the caller did not name.
        """
        if length < 0:
            raise ValueError(f"length {length} is not a length")
        if length == 0:
            return {}
        if not 0 <= start <= 0xFFFF or start + length > EC_SIZE:
            raise ValueError(f"EC range 0x{start:X}+0x{length:X} leaves the "
                             "64 KB window (0x0000-0xFFFF)")
        out = {}
        # The last byte wanted is at most 0xFFFF, so the last block it falls in
        # starts at 0xFFFC at the very most: alignment is what keeps a block
        # from crossing the end of the window, and read_dword's own bound is
        # the backstop under that.
        first = start & ~3
        last = (start + length - 1) & ~3
        for block in range(first, last + 1, 4):
            for i, byte in enumerate(self.read_dword(block)):
                out[block + i] = byte
        return {a: out[a] for a in range(start, start + length)}

    def write(self, addr, val):
        if not 0 <= addr <= 0xFFFF:
            raise ValueError(f"EC address 0x{addr:X} out of the 16-bit range")
        if not 0 <= val <= 0xFF:
            raise ValueError(f"value 0x{val:X} is not a byte")
        buf = ctypes.create_string_buffer(8)
        buf[0] = addr & 0xFF
        buf[1] = (addr >> 8) & 0xFF
        buf[4] = val
        self._ioctl(IOCTL_ECRW, buf)


def block_runs(addrs):
    """`addrs` as the contiguous (start, length) runs `readmany` takes.

    A watch set is scattered -- the fan-ctrl probe's 206 addresses are 7 runs
    -- and a run's blocks are exactly the blocks its own addresses fall in, so
    grouping by run reads the same bytes a distinct-block count would and saves
    the caller from deduping blocks across the gaps. Ascending: the order the
    per-byte path reads in is the sorted order, and a sweep that reads
    backwards is a different access pattern for no reason.
    """
    runs = []
    for a in sorted(set(addrs)):
        if runs and a == runs[-1][0] + runs[-1][1]:
            runs[-1][1] += 1
        else:
            runs.append([a, 1])
    return [tuple(run) for run in runs]


def _int(s):
    return int(s, 16) if s.lower().startswith("0x") else int(s, 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_read = sub.add_parser("read", help="read one or more addresses")
    p_read.add_argument("addrs", nargs="+")

    p_dump = sub.add_parser("dump", help="hex-dump a range")
    p_dump.add_argument("start")
    p_dump.add_argument("length")
    p_dump.add_argument("--block", action="store_true",
                        help="read 4 bytes per IOCTL (MMRD) instead of 1 "
                             "(ECRR); same output, a path that has never been "
                             "run against the driver -- see this tool's help")

    p_write = sub.add_parser("write", help="write addr=value pairs")
    p_write.add_argument("pairs", nargs="+")
    p_write.add_argument("--i-mean-it", action="store_true",
                         help="required: writes go to live EC RAM")

    args = ap.parse_args(argv)

    try:
        with Ec() as ec:
            if args.cmd == "read":
                for a in args.addrs:
                    addr = _int(a)
                    print(f"0x{addr:04X} = 0x{ec.read(addr):02X}")
            elif args.cmd == "dump":
                start, length = _int(args.start), _int(args.length)
                for base in range(start, start + length, 16):
                    n = min(16, start + length - base)
                    if args.block:
                        # One IOCTL per four bytes over the row rather than
                        # one per byte. readmany's keys come out in ascending
                        # order, which is the order the row prints in.
                        row = list(ec.readmany(base, n).values())
                    else:
                        row = [ec.read(base + i) for i in range(n)]
                    print(f"{base:04X}: " + " ".join(f"{b:02x}" for b in row))
            elif args.cmd == "write":
                if not args.i_mean_it:
                    print("refusing to write without --i-mean-it", file=sys.stderr)
                    return 2
                for pair in args.pairs:
                    a, _, v = pair.partition("=")
                    addr, val = _int(a), _int(v)
                    before = ec.read(addr)
                    ec.write(addr, val)
                    after = ec.read(addr)
                    print(f"0x{addr:04X}: was 0x{before:02X} "
                          f"wrote 0x{val:02X} readback 0x{after:02X}")
    except EcError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
