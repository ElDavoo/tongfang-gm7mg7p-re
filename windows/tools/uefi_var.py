#!/usr/bin/env python3
r"""Read (never write) UEFI variables from Windows, and decode the vendor's own.

The vendor service keeps a block of settings shared with the BIOS in one UEFI
variable. `windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/NvramVariable.cs`
reaches it through `UEFI_Firmware.dll`'s `ReadUefi`/`WriteUefi`, and that DLL's
only UEFI calls are `Get`/`SetFirmwareEnvironmentVariableW` on

    name  UniWillVariable
    GUID  {9f33f85c-13ca-4fd1-9c4a-96217722c593}

(both UTF-16 strings in the DLL itself). `NVRAM_STRUCT.cs` in the same tree
gives the field layout, which `decode_uniwill()` below follows field by field.
It includes `BatteryLimitation`, `ChargeMaximumLimit` and `ChargeMinimumLimit`,
the three names `BatteryProtection2`'s charge-limit properties write.

This tool only ever calls GetFirmwareEnvironmentVariableExW and, for `list`,
NtEnumerateSystemEnvironmentValuesEx. It enables SeSystemEnvironmentPrivilege on
its own token, which both need. Must be run elevated.

Usage:
  uefi_var.py uniwill                       # read + decode UniWillVariable
  uefi_var.py read <Name> <{GUID}>          # hex-dump any variable
  uefi_var.py list [--grep TEXT]            # every variable name + GUID + size
  uefi_var.py uniwill --save out.bin        # also keep the raw bytes
"""
import argparse
import ctypes
import struct
import sys
import uuid
from ctypes import wintypes

UNIWILL_NAME = "UniWillVariable"
UNIWILL_GUID = "{9f33f85c-13ca-4fd1-9c4a-96217722c593}"

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_adv = ctypes.WinDLL("advapi32", use_last_error=True)
_nt = ctypes.WinDLL("ntdll")

_k32.GetFirmwareEnvironmentVariableExW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD)]
_k32.GetFirmwareEnvironmentVariableExW.restype = wintypes.DWORD
_k32.GetCurrentProcess.restype = wintypes.HANDLE
_nt.NtEnumerateSystemEnvironmentValuesEx.argtypes = [
    wintypes.ULONG, ctypes.c_void_p, ctypes.POINTER(wintypes.ULONG)]
_nt.NtEnumerateSystemEnvironmentValuesEx.restype = wintypes.LONG


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD), ("Luid", LUID),
                ("Attributes", wintypes.DWORD)]


_adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                  ctypes.POINTER(wintypes.HANDLE)]
_adv.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                                       ctypes.POINTER(LUID)]
_adv.AdjustTokenPrivileges.argtypes = [wintypes.HANDLE, wintypes.BOOL,
                                       ctypes.POINTER(TOKEN_PRIVILEGES),
                                       wintypes.DWORD, ctypes.c_void_p,
                                       ctypes.c_void_p]


def enable_privilege(name="SeSystemEnvironmentPrivilege"):
    tok = wintypes.HANDLE()
    if not _adv.OpenProcessToken(_k32.GetCurrentProcess(), 0x0020 | 0x0008,
                                 ctypes.byref(tok)):
        raise SystemExit("error: OpenProcessToken failed")
    luid = LUID()
    if not _adv.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
        raise SystemExit(f"error: LookupPrivilegeValue({name}) failed")
    tp = TOKEN_PRIVILEGES(1, luid, 0x2)
    _adv.AdjustTokenPrivileges(tok, False, ctypes.byref(tp), 0, None, None)
    if ctypes.get_last_error():
        raise SystemExit(f"error: could not enable {name}; run elevated")


ATTRS = {0x1: "NV", 0x2: "BS", 0x4: "RT", 0x8: "HW_ERR", 0x10: "AUTH_WRITE",
         0x20: "TIME_AUTH_WRITE", 0x40: "APPEND"}


def read_var(name, guid):
    buf = ctypes.create_string_buffer(0x10000)
    attr = wintypes.DWORD()
    n = _k32.GetFirmwareEnvironmentVariableExW(name, guid, buf, len(buf),
                                               ctypes.byref(attr))
    if n == 0:
        err = ctypes.get_last_error()
        raise SystemExit(f"error: {name} {guid}: win32 error {err}"
                         + (" (variable not found)" if err == 203 else ""))
    flags = "|".join(v for k, v in ATTRS.items() if attr.value & k)
    return buf.raw[:n], flags


def list_vars():
    size = wintypes.ULONG(0)
    _nt.NtEnumerateSystemEnvironmentValuesEx(1, None, ctypes.byref(size))
    buf = ctypes.create_string_buffer(size.value or 0x100000)
    st = _nt.NtEnumerateSystemEnvironmentValuesEx(1, buf, ctypes.byref(size))
    if st < 0:
        raise SystemExit(f"error: NtEnumerateSystemEnvironmentValuesEx 0x{st & 0xFFFFFFFF:08X}")
    raw, off, out = buf.raw, 0, []
    while True:
        nxt = struct.unpack_from("<I", raw, off)[0]
        guid = uuid.UUID(bytes_le=raw[off + 4:off + 20])
        name_bytes = raw[off + 20:off + nxt] if nxt else raw[off + 20:]
        name = name_bytes.decode("utf-16le").split("\0", 1)[0]
        out.append((name, "{" + str(guid) + "}"))
        if not nxt:
            break
        off += nxt
    return out


# NVRAM_STRUCT.cs, in declaration order. C#'s default sequential layout aligns
# each field to its own size, so offsets are computed that way; the struct
# declares no Pack. Arrays are (name, "8s") etc.
NVRAM_FIELDS = [
    ("OemBoardSsid", "I"), ("SupportByte", "H"), ("ProjectID", "B"),
    ("KeyboardType", "B"), ("CustomerList", "B"), ("RGBLightbarMode", "B"),
    ("RGBLightbarMode_R", "B"), ("RGBLightbarMode_G", "B"),
    ("RGBLightbarMode_B", "B"), ("ColorCalibrationSupport", "B"),
    ("TDRdata", "B"), ("RGBKeyboard1A", "8s"), ("RGBKeyboard08", "8s"),
    ("SmartLightbar1A", "8s"), ("SmartLightbar08", "8s"), ("PowerMode", "B"),
    ("BatteryLimitation", "B"), ("ChargeMaximumLimit", "B"),
    ("ChargeMinimumLimit", "B"), ("MemoryOverClockSwitch", "B"),
    ("ICpuCoreVoltageValue", "H"), ("ICpuCoreVoltageMaximum", "H"),
    ("ICpuCoreVoltageMinimum", "H"), ("ICpuCoreVoltageOffsetValue", "H"),
    ("ICpuCoreVoltageOffsetMaximum", "H"), ("ICpuCoreVoltageOffsetMinimum", "H"),
    ("ICpuTauValue", "H"), ("ACpuOverClockSupport", "B"), ("ACpuFreqValue", "I"),
    ("ACpuFreqValueMaximum", "I"), ("ACpuFreqValueMinimum", "I"),
    ("ACpuVoltageValue", "I"), ("ACpuVoltageValueMaximum", "I"),
    ("ACpuVoltageValueMinimum", "I"), ("OverClockRecoveryFlag", "B"),
    ("ApExistFlag", "B"), ("ACRecoverySupport", "B"), ("ACRecoveryStatus", "B"),
    ("MemoryOverClockSupport", "B"), ("ApUseFlag", "B"), ("OemDisplayMode", "B"),
    ("ICpuCoreVoltageOffsetNegativeValue", "H"),
    ("ICpuCoreVoltageOffsetRangeType", "B"), ("FnKeyStatus", "B"),
    ("Reserved", "76s"),
]


def layout(packed):
    off, rows = 0, []
    for name, fmt in NVRAM_FIELDS:
        size = struct.calcsize("<" + fmt)
        align = 1 if packed or fmt.endswith("s") else size
        off = (off + align - 1) // align * align
        rows.append((name, fmt, off, size))
        off += size
    return rows, off


def decode_uniwill(raw):
    natural, nat_size = layout(packed=False)
    packed, pk_size = layout(packed=True)
    print(f"variable is {len(raw)} bytes; NVRAM_STRUCT is {nat_size} with C# "
          f"default alignment, {pk_size} packed")
    for (name, fmt, off, size), (_, _, poff, _) in zip(natural, packed):
        def val(o):
            if o + size > len(raw):
                return "(past end)"
            v = struct.unpack_from("<" + fmt, raw, o)[0]
            return v.hex(" ") if isinstance(v, bytes) else f"0x{v:0{size * 2}X} ({v})"
        note = "" if off == poff else f"   [packed @0x{poff:02X}: {val(poff)}]"
        print(f"  0x{off:02X} {name:36s} {val(off)}{note}")


def hexdump(raw):
    for i in range(0, len(raw), 16):
        row = raw[i:i + 16]
        print(f"  {i:04X}: {row.hex(' '):47s}  "
              + "".join(chr(b) if 32 <= b < 127 else "." for b in row))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("uniwill")
    p.add_argument("--save")
    p = sub.add_parser("read")
    p.add_argument("name")
    p.add_argument("guid")
    p.add_argument("--save")
    p = sub.add_parser("list")
    p.add_argument("--grep")
    args = ap.parse_args(argv)

    enable_privilege()
    if args.cmd == "list":
        rows = list_vars()
        for name, guid in sorted(rows, key=lambda r: (r[1], r[0])):
            if args.grep and args.grep.lower() not in (name + guid).lower():
                continue
            print(f"{guid}  {name}")
        print(f"({len(rows)} variables)")
        return 0
    name, guid = ((UNIWILL_NAME, UNIWILL_GUID) if args.cmd == "uniwill"
                  else (args.name, args.guid))
    raw, flags = read_var(name, guid)
    print(f"{name} {guid}: {len(raw)} bytes, attributes {flags}")
    hexdump(raw)
    if args.cmd == "uniwill":
        decode_uniwill(raw)
    if args.save:
        open(args.save, "wb").write(raw)
    return 0


if __name__ == "__main__":
    sys.exit(main())
