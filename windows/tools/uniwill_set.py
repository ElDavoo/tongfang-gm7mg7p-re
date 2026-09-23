#!/usr/bin/env python3
r"""Change one field of UniWillVariable, with a backup, a readback and a restore.

`uefi_var.py` stays read-only; this is the one tool here that writes a UEFI
variable, and it only writes `UniWillVariable`
{9f33f85c-13ca-4fd1-9c4a-96217722c593}, the block the vendor service itself
rewrites through `UEFI_Firmware.dll`'s `WriteUefi` (NV+BS+RT, so the OS can
write it). Field names and offsets come from `uefi_var.NVRAM_FIELDS`, i.e. the
decrypted `NVRAM_STRUCT.cs`.

What it does, in order:
  1. reads the variable and its attributes,
  2. saves the raw bytes to --backup (refuses to overwrite an existing file),
  3. changes the one field, keeping every other byte and the attributes,
  4. writes it with SetFirmwareEnvironmentVariableExW,
  5. reads it back and checks the whole buffer matches what it wrote.

The vendor service caches the whole struct when it starts and writes the whole
cached copy back whenever it sets any field (NvramVariable.SetFwBufferTesting),
so a change made here can be reverted by the service before the next boot if
anything in Control Center is touched in between. Reboot soon after writing.

Must be run elevated.

Usage:
  uniwill_set.py set MemoryOverClockSwitch 1 --backup before.bin
  uniwill_set.py restore before.bin
"""
import argparse
import ctypes
import os
import struct
import sys
from ctypes import wintypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uefi_var  # noqa: E402

_k32 = uefi_var._k32
_k32.SetFirmwareEnvironmentVariableExW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD,
    wintypes.DWORD]
_k32.SetFirmwareEnvironmentVariableExW.restype = wintypes.BOOL

NAME, GUID = uefi_var.UNIWILL_NAME, uefi_var.UNIWILL_GUID


def read_raw():
    buf = ctypes.create_string_buffer(0x1000)
    attr = wintypes.DWORD()
    n = _k32.GetFirmwareEnvironmentVariableExW(NAME, GUID, buf, len(buf),
                                               ctypes.byref(attr))
    if n == 0:
        raise SystemExit(f"error: read {NAME}: win32 error {ctypes.get_last_error()}")
    return buf.raw[:n], attr.value


def write_raw(data, attr):
    buf = ctypes.create_string_buffer(bytes(data), len(data))
    if not _k32.SetFirmwareEnvironmentVariableExW(NAME, GUID, buf, len(data), attr):
        raise SystemExit(f"error: write {NAME}: win32 error {ctypes.get_last_error()}")
    back, back_attr = read_raw()
    if back != bytes(data) or back_attr != attr:
        raise SystemExit("error: readback does not match what was written")


def field(name):
    rows, size = uefi_var.layout(packed=False)
    for fname, fmt, off, fsize in rows:
        if fname == name and not fmt.endswith("s"):
            return fmt, off, fsize, size
    raise SystemExit(f"error: no scalar field {name!r} in NVRAM_STRUCT")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("set")
    p.add_argument("field")
    p.add_argument("value", type=lambda s: int(s, 0))
    p.add_argument("--backup", required=True)
    p = sub.add_parser("restore")
    p.add_argument("backup")
    args = ap.parse_args(argv)

    uefi_var.enable_privilege()
    raw, attr = read_raw()
    flags = "|".join(v for k, v in uefi_var.ATTRS.items() if attr & k)
    print(f"{NAME}: {len(raw)} bytes, attributes {flags}")

    if args.cmd == "restore":
        old = open(args.backup, "rb").read()
        if len(old) != len(raw):
            raise SystemExit(f"error: backup is {len(old)} bytes, variable is {len(raw)}")
        write_raw(old, attr)
        print(f"restored {args.backup}; readback matches")
        return 0

    fmt, off, fsize, struct_size = field(args.field)
    if len(raw) != struct_size:
        raise SystemExit(f"error: variable is {len(raw)} bytes, NVRAM_STRUCT is "
                         f"{struct_size}; layout not trusted, not writing")
    if os.path.exists(args.backup):
        raise SystemExit(f"error: {args.backup} exists; not overwriting a backup")
    with open(args.backup, "wb") as f:
        f.write(raw)
    old = struct.unpack_from("<" + fmt, raw, off)[0]
    new = bytearray(raw)
    struct.pack_into("<" + fmt, new, off, args.value)
    print(f"0x{off:02X} {args.field}: 0x{old:0{fsize * 2}X} -> "
          f"0x{args.value:0{fsize * 2}X} (backup: {args.backup})")
    if old == args.value:
        print("already set; nothing written")
        return 0
    write_raw(new, attr)
    print("written; readback matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
