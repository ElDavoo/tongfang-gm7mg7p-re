#!/usr/bin/env python3
r"""`NVRAM_STRUCT`'s field table and offsets, importable on any platform.

No I/O and no `ctypes.WinDLL` here. That used to be the whole reason this table
is repeated rather than imported -- `windows/tools/uefi_var.py` built its
`kernel32`/`advapi32`/`ntdll` handles with three module-scope
`ctypes.WinDLL` calls, so a Linux tool that reached for it failed at import.
`uefi_var.py` now binds those three on first use
(`windows/tools/test_import_off_windows.py` holds that it imports anywhere), so
the reason this duplication cites is gone and folding the two back together is
the open follow-up. Until then the copy stays, and what holds it is the check
below rather than the impossibility of importing the original.

The cost is paid off here instead, in `test_uniwill_var.py`, which `ast`-reads
both copies and the decompiled `NVRAM_STRUCT.cs` and holds all three to the
same field-for-field table. So this module is not free-floating: a field
renamed, reordered, retyped or resized on either side is a red run rather than
a silent divergence, and the check runs on every commit rather than being
trusted once at review.

**C# default alignment.** The struct declares no `Pack`, so the CLR aligns
each field to its own size and the offsets below are computed that way. That is
the reading `evidence/uefi/2026-09-19-UniWillVariable.txt` records for a live
180-byte dump, and the field names match the dump line for line, which is the
evidence that it is the right one. `layout(packed=True)` is carried alongside
only to show the alternative's shape: 178 bytes, not 180.

Which matters where, and it is worth being exact about, because §8's field is
the one that does not move. `MemoryOverClockSwitch` is at **0x33 under both**,
because every field before it is a byte or an 8-byte array and neither forces
padding. The first offset-sensitive field is `ACpuFreqValue`: the single-byte
`ACpuOverClockSupport` at 0x42 leaves three bytes of pad before the following
`uint`, so it sits at 0x44 aligned and 0x43 packed, and the 17 fields from it
onward shift with it -- `ACpuFreqValue` itself and the 16 after it. Any tool
that wants to write a field past 0x42 has to decide that question first; one
that wants 0x33 does not, which is why the tool refuses a body whose length is
not `NVRAM_STRUCT_SIZE` rather than guessing.
"""
import struct

UNIWILL_NAME = "UniWillVariable"
# The braced, dashed spelling the vendor service uses (Win32 wants it that way).
UNIWILL_GUID = "{9f33f85c-13ca-4fd1-9c4a-96217722c593}"
# The same GUID reduced to 32 bare hex digits. This is the *normalised* form
# `is_var_dent` compares against, not a filename spelling: efivarfs builds the
# dentry with the dashes still in place, so the entry on a real machine is
# `UniWillVariable-9f33f85c-13ca-4fd1-9c4a-96217722c593` -- the same string
# `docs/findings.md` §8 and issue #118 give, which is correct as written.
# `guid_dent_name` builds that; the tool never hardcodes either spelling.
UNIWILL_GUID_HEX = UNIWILL_GUID.strip("{}").replace("-", "")

EFIVARS_DIR = "/sys/firmware/efi/efivars"

# The 4-byte little-endian attribute word efivarfs puts in front of the data,
# same map as `windows/tools/uefi_var.py`'s `ATTRS`. EFI_VARIABLE_* per the
# UEFI spec; `HW_ERR` is `EFI_VARIABLE_RUNTIME_ERROR` under its other name.
ATTRS = {0x1: "NV", 0x2: "BS", 0x4: "RT", 0x8: "HW_ERR", 0x10: "AUTH_WRITE",
         0x20: "TIME_AUTH_WRITE", 0x40: "APPEND"}

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


def guid_dent_name(name=UNIWILL_NAME, guid=UNIWILL_GUID):
    """The efivarfs filename for a UEFI variable: `Name-<dashed guid>`.

    efivarfs keeps the GUID's dashes in the dentry name and drops only the
    braces, so on a real system this is
    `UniWillVariable-9f33f85c-13ca-4fd1-9c4a-96217722c593` -- the spelling
    `docs/findings.md` §8 already gives. The braces are the only thing Win32
    needs that a filename cannot carry, and they are what this strips.
    """
    return f"{name}-{guid.strip('{}')}"


def guid_dent_name_hex(name=UNIWILL_NAME, guid=UNIWILL_GUID):
    r"""The separator-free spelling, which the matcher tolerates.

    efivarfs writes the dashed form above; that is what a real mount holds,
    checked by `ls /sys/firmware/efi/efivars | grep -c -- '-[0-9a-f]\{32\}$'`
    coming back 0 on every mount checked, including a GitHub-hosted CI runner
    rather than the laptop. This spelling is here for the other case `--var`
    opens: a directory the operator assembled by hand or a test fixture, which
    nothing stops from naming the entry either way. It is a spelling to
    tolerate, not a second claim about the kernel.
    """
    return f"{name}-{guid.strip('{}').replace('-', '')}"


def is_var_dent(dent, name=UNIWILL_NAME, guid=UNIWILL_GUID):
    """Whether a `efivars/` directory entry name is this variable's.

    Name equality plus the trailing GUID compared with separators stripped, so
    the dashed dentry efivarfs actually writes and the 32-bare-digit form are
    both this variable's. Stripping is the reason for the `--var`-independent
    glob in `find_entry`: the tool never has to be told which spelling the
    directory holds.

    Both halves are load-bearing. A name that matched without the GUID would
    collide with nothing today and with something the day the vendor ships a
    second variable, and the tool must never be one wrong `--var` away from
    writing the wrong block.
    """
    prefix = name + "-"
    if not dent.startswith(prefix):
        return False
    return dent[len(prefix):].strip("{}").replace("-", "") == \
        guid.strip("{}").replace("-", "")


def layout(packed):
    """-> ([(name, fmt, offset, size)], total) for the struct as laid out.

    `packed` follows the C# side: with no `Pack` declared, each scalar is
    aligned to its own size. Arrays are exempt either way, since a `byte[]`
    marshalled `ByValArray` has alignment 1.
    """
    off, rows = 0, []
    for name, fmt in NVRAM_FIELDS:
        size = struct.calcsize("<" + fmt)
        align = 1 if packed or fmt.endswith("s") else size
        off = (off + align - 1) // align * align
        rows.append((name, fmt, off, size))
        off += size
    return rows, off


NVRAM_STRUCT_SIZE = layout(packed=False)[1]


def field(name):
    """-> (fmt, offset, size) for a *scalar* field, or None.

    None covers both "no such field" and "that field is an array": neither can
    be written by the one-field path, and the caller refuses both the same way,
    so the caller does not need to tell them apart to refuse them.
    """
    for fname, fmt, off, size in layout(packed=False)[0]:
        if fname == name and not fmt.endswith("s"):
            return fmt, off, size
    return None


def is_array(name):
    """Whether `name` is one of the struct's `byte[]` fields."""
    return any(fname == name and fmt.endswith("s")
               for fname, fmt in NVRAM_FIELDS)


def attr_flags(attr):
    """An attribute word as `NV|BS|RT`, in `ATTRS` order."""
    return "|".join(v for k, v in ATTRS.items() if attr & k)