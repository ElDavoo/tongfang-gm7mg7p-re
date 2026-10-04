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

Every block path here reads at 4-aligned offsets and nothing else can: a range
is covered by the aligned blocks enclosing it, and `read_dword` refuses
anything else. The one exception is the `mmrd` subcommand and the
`read_dword_unaligned` behind it, which exists to put issue #147's question —
one `MMRD` at `0xFE410000 + 0x0751`, an unaligned operand — so that it can be
asked. It issues exactly one IOCTL and is reachable from no sweep, by name
rather than by flag. That too has never been run, and the four bytes it brings
back are printed as they arrived rather than labelled with the EC offsets they
are read as, because which of the four is the lowest address is a reading of
the marshalling (`windows/native/ACPIDriver.sys.analysis.md`) and labelling
them here would settle it by assumption. `docs/findings/mmrd-unaligned-escape.md`
is the write-up; it settles nothing either.

The DSDT's `ECRR` is `MMRW(0xFE410000 + Arg0, 0, 0, 0)` (`evidence/acpi/dsdt.dsl`
:50497), so a read here and a read through `ec/tools/ecmem.py` on Linux are the
same physical byte, reached two different ways.

**`dump` leaves out the fan-tach page and paces its reads.** Reading
`0x0460-0x046F` through `ECRR` stalled the fans on a sibling Uniwill board, and
the OEM software and `uniwill-laptop` both sleep about 6 ms after every EC
access (HydroControl DESIGN.md §4.2, `docs/related-projects.md`);
`--include-fan-tach` reads the page anyway, and `--gap-ms` sets the gap. This
machine has never been observed to stall, so that is another board's figure
rather than a finding here, and no interval in this repository is validated --
but an unpaced `dump 0x0000 0x0800` reads those sixteen bytes as part of a
2048-address burst with no gap in it, which is the shape of access that report
is about, and `dump` had no way to say otherwise. A range this long is also
slow: at the default gap it takes seconds rather than the moment an unpaced one
took, which is what the cost is for. `read` and `write` are unchanged, and
`mmrd` is one IOCTL by name.

No driver is installed by this tool. It requires the vendor stack's driver to be
already present and started; on the machine this was developed against that is
`UWACPIDriver.sys` (Control Center Service 3.1.39.0), which creates the same
`\DosDevices\ACPIDriver` symlink the 3.1.6.0-era `ACPIDriver.sys` does and
carries the same 21 IOCTL codes. Must be run elevated.

**Importing this module opens nothing and binds nothing.** `kernel32` is loaded
on the first `Ec()`, not at import, because `ctypes.WinDLL` exists only on
Windows: a module-scope bind made this file -- and every tool that does `from
ecrw import ...` -- loadable only there. Off Windows `Ec()` raises `EcError`
naming the platform, which `main` turns into a message and exit 1.
`windows/tools/test_import_off_windows.py` holds both halves. The `try` around
the `wintypes` import below is belt-and-braces rather than the load-bearing
half: `ctypes.wintypes` imports cleanly on Linux, and the guard exists so a
future interpreter without it fails at the point of use rather than as an
`ImportError` from the top of the file.

Usage:
  ecrw.py read  0x7b9 0x7d0 ...
  ecrw.py dump  0x0700 0x100          # start, length
  ecrw.py dump  0x0700 0x100 --block  # 4 bytes per IOCTL, same output
  ecrw.py dump  0x0460 0x10 --include-fan-tach   # the page dump leaves out
  ecrw.py write 0x7b9=60 0x7d0=55     # requires --i-mean-it
  ecrw.py mmrd  0x0751                # one MMRD at an unaligned offset

Addresses and values accept 0x-prefixed hex or decimal.
"""
import argparse
import ctypes
import sys
import time
try:
    from ctypes import wintypes
except ImportError:  # pragma: no cover - only on a Python without the module
    wintypes = None

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

# The fan-tach bytes, which `dump` does not read unless --include-fan-tach is
# given: ECRR reads of that page stalled the fans on a sibling board (#94,
# docs/related-projects.md). The same range as `ec_watch.py`'s, and a local
# constant rather than an import because `windows/tools/` is deployed as a
# directory: `ecrw_fake.py` publishes three names and this one is not one of
# them, so importing it would make this module unloadable under every offline
# suite that installs the fixture.
FAN_TACH = range(0x0460, 0x0470)


class EcError(RuntimeError):
    pass


_k32 = None


def _kernel32():
    """kernel32, loaded and declared on first use.

    `ctypes.WinDLL` exists only on Windows, so binding it at import time made
    this module loadable only there -- and every tool importing it with it, on
    a runner that has no Windows. Binding on first call instead keeps the
    pure-Python surface (`DEVICE`, the `IOCTL_*` codes, `EC_BASE`, `EcError`)
    importable anywhere, which is what
    `windows/tools/test_import_off_windows.py` holds. The signatures travel
    with the load rather than staying at module scope because they are
    assignments onto the handle that does not exist yet.

    Cached, so one process binds it once: every `Ec` reuses the same handle
    object, and the `argtypes`/`restype` writes happen once rather than per
    construction.

    Off Windows the failure is `EcError` naming the platform, rather than the
    `AttributeError` a user got from the module-scope bind -- and it lands in
    `main`'s own `except EcError`, so the CLI prints it and exits 1.
    """
    global _k32
    if _k32 is not None:
        return _k32
    if wintypes is None:
        raise EcError("ctypes.wintypes is unavailable on this interpreter, so "
                      "the Win32 signatures this module needs cannot be built")
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except AttributeError:
        raise EcError(
            "ctypes.WinDLL does not exist on this platform -- this tool reads "
            f"EC RAM through the vendor driver on {DEVICE} and is Windows-only. "
            "On Linux, `ec/tools/ecmem.py` reads the same bytes through "
            "/dev/mem") from None

    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    k32.CreateFileW.restype = wintypes.HANDLE

    k32.DeviceIoControl.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    k32.DeviceIoControl.restype = wintypes.BOOL

    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL

    _k32 = k32
    return _k32


class Ec:
    """One open handle to the vendor driver, reused across calls.

    The vendor's own DLL reopens the device for every single byte; nothing in
    the driver requires that (`IRP_MJ_CREATE`/`CLOSE` just return success), and
    holding the handle makes a 256-byte dump roughly an order of magnitude
    cheaper. Both shapes were exercised against the same registers and returned
    the same values.
    """

    def __init__(self):
        self._k32 = _kernel32()
        h = self._k32.CreateFileW(DEVICE, GENERIC_READ | GENERIC_WRITE,
                                  FILE_SHARE_READ_WRITE, None, OPEN_EXISTING,
                                  0, None)
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
            self._k32.CloseHandle(self._h)
            self._h = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _ioctl(self, code, buf):
        returned = wintypes.DWORD(0)
        ok = self._k32.DeviceIoControl(self._h, code, buf, len(buf), buf,
                                       len(buf), ctypes.byref(returned), None)
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

    def read_dword_unaligned(self, addr):
        """One MMRD at an unaligned EC offset, one IOCTL. The escape, and
        the only path in this module that can issue one.

        Issue #147 words its check as one `MMRD` at `0xFE410000 + 0x0751`,
        where `0x0751 % 4 == 1`. `read_dword` refuses that and `readmany`
        covers the enclosing block instead, so without this method the
        question is unaskable from here; `manual_fan_ctrl_probe.py`'s docstring
        is where the comparison a human takes is written down.

        A separate name rather than a keyword on `read_dword`, on purpose.
        `readmany` calls `read_dword` at every block, so a flag that permitted
        an unaligned start would put one within reach of every sweep in this
        repository, and a distinct name makes the aligned path incapable of it
        by construction rather than by discipline.

        The marshalling is `read_dword`'s, unchanged: the same 8-byte buffer,
        the same little-endian `EC_BASE + addr` -- the ASL adds nothing to a
        `MMRD` operand (evidence/acpi/dsdt.dsl:50481-50483) -- and the same
        `buf.raw[:4]` back. Only the bound differs. This loosens alignment and
        nothing else: `addr + 3` must still be inside the window, so the last
        unaligned start accepted is `0xFFFD` and `0xFFFE` raises the same
        `ValueError`, before any IOCTL, that `read_dword` raises.

        The four bytes come back in the order the copy-back put them there --
        four byte stores out of the ACPI output buffer, in order, not one
        dword store. Which of them is the lowest address is a reading of that
        marshalling and not a measured one
        (`../native/ACPIDriver.sys.analysis.md`); nothing here labels them
        with an EC offset for exactly that reason.

        Nothing in this repository has issued one of these either. The DSDT
        has no alignment test on `MMRW` -- not found by the grep in
        `docs/findings/mmrd-unaligned-escape.md` -- and neither the ACPI
        specification nor `ACPI.sys` is in this tree, so whether the BIOS
        answers an unaligned operand at all is a question for a human at the
        machine.
        """
        if not 0 <= addr <= 0xFFFD:
            # The same window read_dword holds, one byte further along: a dword
            # starting at 0xFFFD ends at 0xFFFF, and one starting at 0xFFFE
            # would run off the mapped region into 0xFE420000. The unaligned
            # start is what is being allowed here, not the wider access.
            raise ValueError(f"EC address 0x{addr:X} is not a dword start in "
                             "0x0000-0xFFFD")
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
    p_dump.add_argument("--include-fan-tach", action="store_true",
                        help="read the fan-tach bytes 0x0460-0x046F, which are "
                             "not read at all otherwise and print as '--': "
                             "ECRR reads of that page stalled the fans on a "
                             "sibling board (#94) and this machine has never "
                             "been seen to. --block does not make it safer")
    p_dump.add_argument("--gap-ms", type=float, default=6,
                        help="milliseconds to sleep after every read (default "
                             "6). The figure HydroControl reports for the OEM "
                             "software and uniwill-laptop after reading a "
                             "sibling board whose fans stalled on unpaced ECRR "
                             "traffic; not measured on this machine, and no "
                             "interval here is validated. 0 is unpaced")

    p_write = sub.add_parser("write", help="write addr=value pairs")
    p_write.add_argument("pairs", nargs="+")
    p_write.add_argument("--i-mean-it", action="store_true",
                         help="required: writes go to live EC RAM")

    p_mmrd = sub.add_parser(
        "mmrd", help="one MMRD (4 bytes) at an unaligned EC offset")
    p_mmrd.add_argument(
        "addr",
        help="EC offset, not a physical address: EC_BASE is added here, as "
             "it is for every other command. May be unaligned -- that is "
             "the point, and no sweep can reach this. The four bytes print "
             "in the order the copy-back produced them and are deliberately "
             "not labelled with EC offsets: which of them is the lowest "
             "address is a reading of the marshalling "
             "(../native/ACPIDriver.sys.analysis.md) and not a measured one. "
             "Nothing here has been run against the driver")

    args = ap.parse_args(argv)

    try:
        with Ec() as ec:
            if args.cmd == "read":
                for a in args.addrs:
                    addr = _int(a)
                    print(f"0x{addr:04X} = 0x{ec.read(addr):02X}")
            elif args.cmd == "dump":
                start, length = _int(args.start), _int(args.length)
                wanted = list(range(start, start + length))
                addrs = wanted if args.include_fan_tach else [
                    a for a in wanted if a not in FAN_TACH]
                dropped = len(wanted) - len(addrs)
                if not addrs:
                    # Said rather than printed as an empty dump: a range that
                    # reads nothing and prints nothing is indistinguishable
                    # from a range that read nothing and moved nothing, which
                    # is the reading #94 is about.
                    #
                    # `dropped` is non-zero exactly when the exclusion emptied
                    # the set, so it says which of the two explanations is the
                    # true one. A `--len 0` never held a page byte, and naming
                    # the page for it diagnoses a range that did not touch it.
                    if dropped:
                        print(f"nothing read: 0x{start:04X}+0x{length:04X} is "
                              "inside the fan-tach bytes "
                              f"0x{FAN_TACH.start:04X}-"
                              f"0x{FAN_TACH.stop - 1:04X} "
                              "and they are left out by default (#94). Move "
                              "the range off the page, or pass "
                              "--include-fan-tach to read it anyway.",
                              file=sys.stderr)
                    else:
                        print(f"nothing read: 0x{start:04X}+0x{length:04X} is "
                              "an empty range -- it names no address to read, "
                              "so there is nothing to read. Give --len a "
                              "length.", file=sys.stderr)
                    return 1
                got = {}
                if args.block:
                    # One IOCTL per four bytes over a run rather than one per
                    # byte. Reading runs rather than rows is also what keeps
                    # the exclusion exact on this path: readmany covers a range
                    # with the aligned blocks enclosing it, and a run that ends
                    # at 0x045F or starts at 0x0470 cannot reach into a page
                    # that starts on a block boundary and is a whole number of
                    # blocks long. A range that both straddles and excludes
                    # would otherwise be read past by the row that covers it.
                    for run_start, run_length in block_runs(addrs):
                        got.update(ec.readmany(run_start, run_length))
                        time.sleep(args.gap_ms / 1000)
                else:
                    for a in addrs:
                        got[a] = ec.read(a)
                        time.sleep(args.gap_ms / 1000)
                if dropped:
                    print(f"not reading {dropped} byte(s) of "
                          f"0x{start:04X}+0x{length:04X}: the fan-tach page "
                          f"0x{FAN_TACH.start:04X}-0x{FAN_TACH.stop - 1:04X} "
                          "is left out by default (#94, and --block does not "
                          "make it safer). '--' below is an address that was "
                          "not read, not a zero.", file=sys.stderr)
                elif (args.include_fan_tach and start < FAN_TACH.stop
                        and start + length > FAN_TACH.start):
                    print("--include-fan-tach: this dump is reading the "
                          "fan-tach bytes "
                          f"0x{FAN_TACH.start:04X}-0x{FAN_TACH.stop - 1:04X}, "
                          "whose ECRR reads stalled the fans on a sibling "
                          "board (#94, docs/related-projects.md). This machine "
                          "has never been seen to; the flag is the choice "
                          "being made.", file=sys.stderr)
                for base in range(start, start + length, 16):
                    n = min(16, start + length - base)
                    # Every row of the range prints, including one that is
                    # wholly inside the page: the row is how the operator
                    # finds where that page sits in what they asked for, and a
                    # gap in the middle of a hexdump is not distinguishable
                    # from a gap in the middle of the range.
                    row = [got.get(base + i) for i in range(n)]
                    print(f"{base:04X}: " + " ".join(
                        "--" if b is None else f"{b:02x}" for b in row))
            elif args.cmd == "mmrd":
                addr = _int(args.addr)
                four = ec.read_dword_unaligned(addr)
                # The physical address is what went on the wire, so it is the
                # label; the four bytes print in the order the copy-back
                # produced them and carry no EC offset of their own. Naming
                # buf[0] as the byte at `addr` is the reading under test, and
                # having the tool print it would make this output a
                # confirmation of the assumption rather than a measurement of
                # it -- so the comparison a human takes is the one against the
                # aligned `dump --block` line, not against these four bytes.
                print(f"0x{EC_BASE + addr:08X}: "
                      + " ".join(f"{b:02x}" for b in four))
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
