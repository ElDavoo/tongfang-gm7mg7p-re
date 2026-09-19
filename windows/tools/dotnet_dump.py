#!/usr/bin/env python3
r"""Dump a running .NET module after its anti-tamper has decrypted it, and rebuild
it as a file a decompiler can read.

`windows/antitamper/README.md` describes the protection on `GCUService.exe`: at
module load, `<Module>.cctor` calls a routine that `VirtualProtect`s the image
and decrypts the method bodies in place, before any of them run. On disk those
bodies are ciphertext; in the running service they are plaintext IL. This tool
is that README's "approach 2", without a debugger: the service is already
running, so its decrypted image is simply read out of its address space.

How the file is rebuilt, and why that way:

  * The on-disk file is the template. Its headers, section table and metadata
    are kept byte-for-byte; only each section's *raw data* is replaced with
    what the running process holds at that section's virtual address. So
    anything an anti-dump pass may have scribbled over in the in-memory headers
    cannot leak into the output, and file offsets stay exactly where the
    metadata's RVA->offset mapping expects them.
  * Bytes the loader itself rewrites at load time (the import address table,
    base-relocation sites) are put back from the disk copy, and so are the CLI
    header and the metadata blob: anti-tamper encrypts method *bodies* only, so
    those never legitimately change at run time, while an anti-dump pass
    deliberately wipes parts of them in memory (on GCUService 3.1.39.0: 9 bytes
    of the COR20 header, 27 of the metadata root -- the `BSJB` signature and
    stream names). The dump therefore differs from the shipped file *only*
    where the running module differs for another reason. `--report` lists
    those regions, which is the evidence that the difference is the decrypted
    bodies and not something incidental.

Nothing is written to the target process. It is opened with
PROCESS_QUERY_INFORMATION | PROCESS_VM_READ only; SeDebugPrivilege is enabled on
this tool's own token because the vendor service runs as LocalSystem. Must be
run elevated.

Usage:
  dotnet_dump.py --name GCUService.exe --out GCUService.dumped.exe --report
  dotnet_dump.py --pid 8056 --module GCUService.exe --out dump.exe

Check the result with `dotnet_bodies.py` (method-body header census, disk vs
dump) before decompiling it.
"""
import argparse
import ctypes
import os
import sys
from ctypes import wintypes

import pefile

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
LIST_MODULES_ALL = 0x03
TH32CS_SNAPPROCESS = 0x00000002

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_adv = ctypes.WinDLL("advapi32", use_last_error=True)
_psapi = ctypes.WinDLL("psapi", use_last_error=True)


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD),
                ("Privileges", LUID_AND_ATTRIBUTES * 1)]


class MODULEINFO(ctypes.Structure):
    _fields_ = [("lpBaseOfDll", ctypes.c_void_p),
                ("SizeOfImage", wintypes.DWORD),
                ("EntryPoint", ctypes.c_void_p)]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260)]


_k32.OpenProcess.restype = wintypes.HANDLE
_k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
_k32.ReadProcessMemory.restype = wintypes.BOOL
_k32.GetCurrentProcess.restype = wintypes.HANDLE
_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
_k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
_k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
_adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                  ctypes.POINTER(wintypes.HANDLE)]
_adv.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                                       ctypes.POINTER(LUID)]
_adv.AdjustTokenPrivileges.argtypes = [wintypes.HANDLE, wintypes.BOOL,
                                       ctypes.POINTER(TOKEN_PRIVILEGES), wintypes.DWORD,
                                       ctypes.c_void_p, ctypes.c_void_p]
_psapi.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE),
                                        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                        wintypes.DWORD]
_psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
                                        wintypes.LPWSTR, wintypes.DWORD]
_psapi.GetModuleInformation.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
                                        ctypes.POINTER(MODULEINFO), wintypes.DWORD]


def fail(msg):
    raise SystemExit(f"error: {msg} (win32 error {ctypes.get_last_error()})")


def enable_privilege(name):
    tok = wintypes.HANDLE()
    if not _adv.OpenProcessToken(_k32.GetCurrentProcess(),
                                 TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                 ctypes.byref(tok)):
        fail("OpenProcessToken")
    luid = LUID()
    if not _adv.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
        fail(f"LookupPrivilegeValue({name})")
    tp = TOKEN_PRIVILEGES(1, (LUID_AND_ATTRIBUTES * 1)(
        LUID_AND_ATTRIBUTES(luid, SE_PRIVILEGE_ENABLED)))
    _adv.AdjustTokenPrivileges(tok, False, ctypes.byref(tp), 0, None, None)
    err = ctypes.get_last_error()
    _k32.CloseHandle(tok)
    if err:  # ERROR_NOT_ALL_ASSIGNED = 1300: not elevated
        raise SystemExit(f"error: could not enable {name} (error {err}); run elevated")


def find_pid(exe_name):
    snap = _k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(pe)
    pids = []
    ok = _k32.Process32FirstW(snap, ctypes.byref(pe))
    while ok:
        if pe.szExeFile.lower() == exe_name.lower():
            pids.append(pe.th32ProcessID)
        ok = _k32.Process32NextW(snap, ctypes.byref(pe))
    _k32.CloseHandle(snap)
    if len(pids) != 1:
        raise SystemExit(f"error: expected one {exe_name} process, found {pids}")
    return pids[0]


def find_module(hproc, module_name):
    needed = wintypes.DWORD()
    mods = (wintypes.HMODULE * 1024)()
    if not _psapi.EnumProcessModulesEx(hproc, mods, ctypes.sizeof(mods),
                                       ctypes.byref(needed), LIST_MODULES_ALL):
        fail("EnumProcessModulesEx")
    buf = ctypes.create_unicode_buffer(1024)
    for i in range(needed.value // ctypes.sizeof(wintypes.HMODULE)):
        _psapi.GetModuleFileNameExW(hproc, mods[i], buf, 1024)
        if os.path.basename(buf.value).lower() == module_name.lower():
            mi = MODULEINFO()
            if not _psapi.GetModuleInformation(hproc, mods[i], ctypes.byref(mi),
                                               ctypes.sizeof(mi)):
                fail("GetModuleInformation")
            return buf.value, mi.lpBaseOfDll, mi.SizeOfImage
    raise SystemExit(f"error: module {module_name} not loaded in the target")


def read_image(hproc, base, size, page=0x1000):
    """Read [base, base+size) page by page; unreadable pages come back as None."""
    out = bytearray(size)
    unreadable = []
    got = ctypes.c_size_t()
    chunk = ctypes.create_string_buffer(page)
    for off in range(0, size, page):
        n = min(page, size - off)
        if _k32.ReadProcessMemory(hproc, ctypes.c_void_p(base + off), chunk, n,
                                  ctypes.byref(got)) and got.value == n:
            out[off:off + n] = chunk.raw[:n]
        else:
            unreadable.append(off)
    return bytes(out), unreadable


def restore_ranges(pe):
    """RVA ranges taken from the disk copy rather than from memory, with why.

    Two kinds. The loader legitimately rewrites the IAT and base-relocation
    sites. And the CLI header plus the whole metadata blob never change at run
    time under anti-tamper (it encrypts method *bodies* only) -- but an
    anti-dump pass deliberately wipes parts of them in memory (the COR20 header,
    the `BSJB` signature, the stream names), so the in-memory copy is the one
    that is wrong there.
    """
    ranges = []
    dd = pe.OPTIONAL_HEADER.DATA_DIRECTORY
    iat = dd[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IAT"]]
    if iat.VirtualAddress and iat.Size:
        ranges.append((iat.VirtualAddress, iat.VirtualAddress + iat.Size, "IAT"))
    width = 8 if pe.OPTIONAL_HEADER.Magic == 0x20B else 4
    for block in getattr(pe, "DIRECTORY_ENTRY_BASERELOC", []):
        for e in block.entries:
            if e.type != 0:  # IMAGE_REL_BASED_ABSOLUTE is padding
                ranges.append((e.rva, e.rva + width, "reloc"))
    cli = dd[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_COM_DESCRIPTOR"]]
    if cli.VirtualAddress and cli.Size:
        ranges.append((cli.VirtualAddress, cli.VirtualAddress + cli.Size,
                       "CLI header"))
        hdr = pe.get_data(cli.VirtualAddress, 16)
        md_rva, md_size = int.from_bytes(hdr[8:12], "little"), int.from_bytes(
            hdr[12:16], "little")
        if md_rva and md_size:
            ranges.append((md_rva, md_rva + md_size, "metadata"))
    return ranges


def diff_runs(a, b, base_rva):
    """Contiguous runs where a != b, as (rva_start, rva_end)."""
    runs, start = [], None
    for i in range(len(a)):
        if a[i] != b[i]:
            if start is None:
                start = i
        elif start is not None:
            runs.append((base_rva + start, base_rva + i))
            start = None
    if start is not None:
        runs.append((base_rva + start, base_rva + len(a)))
    return runs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    who = ap.add_mutually_exclusive_group(required=True)
    who.add_argument("--pid", type=int)
    who.add_argument("--name", help="process image name, e.g. GCUService.exe")
    ap.add_argument("--module", help="module to dump (default: the process image)")
    ap.add_argument("--disk", help="on-disk copy to use as the template "
                                   "(default: the path the module was loaded from)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", action="store_true",
                    help="list every region where the running image differs from disk")
    args = ap.parse_args(argv)

    enable_privilege("SeDebugPrivilege")
    pid = args.pid or find_pid(args.name)
    module = args.module or args.name
    if not module:
        raise SystemExit("error: --module is required with --pid")

    hproc = _k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not hproc:
        fail(f"OpenProcess({pid})")
    try:
        path, base, size = find_module(hproc, module)
        mem, unreadable = read_image(hproc, base, size)
    finally:
        _k32.CloseHandle(hproc)

    disk_path = args.disk or path
    disk = open(disk_path, "rb").read()
    pe = pefile.PE(data=disk)
    print(f"pid {pid}  {path}")
    print(f"mapped at 0x{base:X}, SizeOfImage 0x{size:X} "
          f"(file says 0x{pe.OPTIONAL_HEADER.SizeOfImage:X})")
    if size != pe.OPTIONAL_HEADER.SizeOfImage:
        raise SystemExit("error: in-memory size differs from the template; "
                         "is --disk the same build as the running module?")
    if unreadable:
        print(f"warning: {len(unreadable)} unreadable pages, left as on disk: "
              + ", ".join(f"0x{o:X}" for o in unreadable[:8]))

    restore = restore_ranges(pe)
    restored = {}          # reason -> bytes that differed in memory and were put back
    out = bytearray(disk)
    total_changed = 0
    for s in pe.sections:
        name = s.Name.rstrip(b"\0").decode(errors="replace")
        va, raw, rawsz = s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData
        n = min(rawsz, max(s.Misc_VirtualSize, 0) or rawsz, size - va)
        m = bytearray(mem[va:va + n])
        for off in unreadable:  # keep disk bytes where memory was unreadable
            lo, hi = max(off, va), min(off + 0x1000, va + n)
            if lo < hi:
                m[lo - va:hi - va] = disk[raw + lo - va:raw + hi - va]
        for lo, hi, why in restore:
            lo, hi = max(lo, va), min(hi, va + n)
            if lo < hi:
                d = disk[raw + lo - va:raw + hi - va]
                restored[why] = restored.get(why, 0) + sum(
                    1 for x, y in zip(m[lo - va:hi - va], d) if x != y)
                m[lo - va:hi - va] = d
        runs = diff_runs(disk[raw:raw + n], m, va)
        changed = sum(hi - lo for lo, hi in runs)
        total_changed += changed
        print(f"section {name:8s} RVA 0x{va:06X} raw 0x{raw:06X} len 0x{n:06X}: "
              f"{changed} bytes differ from disk in {len(runs)} run(s)")
        if args.report:
            for lo, hi in runs[:40]:
                print(f"    RVA 0x{lo:06X}-0x{hi:06X} ({hi - lo} bytes)")
            if len(runs) > 40:
                print(f"    ... {len(runs) - 40} more runs")
        out[raw:raw + n] = m

    for why, n in restored.items():
        print(f"restored from disk: {why}: {n} bytes differed in memory")
    with open(args.out, "wb") as fh:
        fh.write(out)
    print(f"wrote {args.out}: {len(out)} bytes, {total_changed} bytes differ from "
          f"{disk_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
