#!/usr/bin/env python3
"""Triage a native x86-64 PE (the vendor .sys/.dll under vendor/) without
needing a disassembler, Windows, or anything from pip.

Method: parse the PE headers, import/export directories and section table
straight out of the file, then byte-scan the executable sections for the
two things that would distinguish a direct-EC driver from an ACPI
passthrough shim -- x86 port-I/O opcodes (IN/OUT), and the EC register
addresses the Windows service uses (ECSpec.cs's 0x07B9/0x07D0 pair) as
raw immediates.

A byte scan does not know code from data, and x86 is a variable-length
encoding, so a bare opcode-byte match is a *candidate*, not a finding:
0xEC is `in al,dx` but it is also the third byte of `sub $0x460,%rsp`.
--portio therefore takes an optional --listing produced by disasm.sh and
adjudicates each candidate against real instruction boundaries. Even then,
the answer is bounded by the method: a byte/listing scan cannot follow
port access performed through an imported HAL routine (READ_PORT_UCHAR
and friends), through a computed or indirect call, or through code that
is generated or decrypted at run time. Zero confirmed hits means "not
found by this method", never "absent" -- the same caveat
ec/tools/scan_refs.py carries.

Usage:
    python3 pe_triage.py ACPIDriver.sys                 # headers+imports+exports
    python3 pe_triage.py ACPIDriver.sys --portio        # IN/OUT candidates
    python3 pe_triage.py ACPIDriver.sys --portio --listing l.asm   # adjudicated
    python3 pe_triage.py ACPIDriver.sys --immediates    # EC address constants
    python3 pe_triage.py ACPIDriver.sys --ioctls        # CTL_CODE constants
    python3 pe_triage.py ACPIDriver.sys --strings       # ASCII + UTF-16LE
    python3 pe_triage.py ACPIDriver.sys --self-check    # the counts the docs quote
"""
import argparse
import re
import struct
import sys

# x86 port I/O, the whole opcode set. The one-byte forms take the port in
# DX; the imm8 forms encode it directly, which is what a driver poking the
# EC's 0x62/0x66 command/data pair or the SuperIO 0x2E/0x4E index pair
# would most likely look like.
PORTIO_OPCODES = {
    0xE4: "in  al, imm8",
    0xE5: "in  eax, imm8",
    0xE6: "out imm8, al",
    0xE7: "out imm8, eax",
    0xEC: "in  al, dx",
    0xED: "in  eax, dx",
    0xEE: "out dx, al",
    0xEF: "out dx, eax",
}

# The charge-limit register pair from windows/decompiled/v3.1.6.0/ECSpec.cs.
# Only 16-bit-and-wider values are worth scanning for: a one-byte constant
# like the EC's 0x62/0x66 data/command ports matches thousands of random
# bytes, so its "hits" would carry no information. Whether those ports are
# touched is what --portio answers.
IMMEDIATES = {
    0x07B9: "ADDR_BATTERY_CHARGE_LIMIT_UP (ECSpec.cs)",
    0x07D0: "ADDR_BATTERY_CHARGE_LIMIT_DOWN (ECSpec.cs)",
}

# CTL_CODE(DeviceType, Function, Method, Access) as the Windows DDK
# defines it. Needed to turn a bare immediate compared against
# Parameters.DeviceIoControl.IoControlCode back into something readable.
METHODS = ("BUFFERED", "IN_DIRECT", "OUT_DIRECT", "NEITHER")
ACCESSES = ("ANY_ACCESS", "READ_ACCESS", "WRITE_ACCESS", "READ_WRITE_ACCESS")


class PE:
    """Just enough PE64 to answer the questions above."""

    def __init__(self, data: bytes):
        self.data = data
        if data[:2] != b"MZ":
            raise ValueError("not a PE: no MZ signature")
        pe_off = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_off:pe_off + 4] != b"PE\0\0":
            raise ValueError("not a PE: no PE signature")

        coff = pe_off + 4
        (self.machine, self.nsections, self.timestamp, _symtab, _nsyms,
         opt_size, self.characteristics) = struct.unpack_from("<HHIIIHH", data, coff)

        opt = coff + 20
        self.magic = struct.unpack_from("<H", data, opt)[0]
        if self.magic != 0x20B:
            raise ValueError(f"not PE32+ (optional header magic 0x{self.magic:04X})")
        self.entry_rva = struct.unpack_from("<I", data, opt + 16)[0]
        self.image_base = struct.unpack_from("<Q", data, opt + 24)[0]
        self.subsystem = struct.unpack_from("<H", data, opt + 68)[0]
        ndirs = struct.unpack_from("<I", data, opt + 108)[0]
        self.dirs = [struct.unpack_from("<II", data, opt + 112 + 8 * i)
                     for i in range(ndirs)]

        sec = opt + opt_size
        self.sections = []
        for i in range(self.nsections):
            off = sec + 40 * i
            name = data[off:off + 8].rstrip(b"\0").decode("ascii", "replace")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
            flags = struct.unpack_from("<I", data, off + 36)[0]
            self.sections.append({
                "name": name, "vsize": vsize, "vaddr": vaddr,
                "rawsize": rawsize, "rawptr": rawptr, "flags": flags,
                "exec": bool(flags & 0x20000000),
            })

    def rva_to_off(self, rva: int):
        for s in self.sections:
            if s["vaddr"] <= rva < s["vaddr"] + max(s["vsize"], s["rawsize"]):
                off = rva - s["vaddr"] + s["rawptr"]
                return off if off < len(self.data) else None
        return None

    def off_to_rva(self, off: int):
        for s in self.sections:
            if s["rawptr"] <= off < s["rawptr"] + s["rawsize"]:
                return off - s["rawptr"] + s["vaddr"]
        return None

    def section_at_off(self, off: int):
        for s in self.sections:
            if s["rawptr"] <= off < s["rawptr"] + s["rawsize"]:
                return s["name"]
        return "?"

    def cstr(self, rva: int) -> str:
        off = self.rva_to_off(rva)
        if off is None:
            return "<bad rva>"
        end = self.data.index(b"\0", off)
        return self.data[off:end].decode("ascii", "replace")

    def imports(self):
        """[(dll, [symbol, ...], iat_rva_of_first_slot)], in directory order."""
        rva, size = self.dirs[1] if len(self.dirs) > 1 else (0, 0)
        if not rva or not size:
            return []
        base = self.rva_to_off(rva)
        out = []
        i = 0
        while True:
            off = base + 20 * i
            oft, _ts, _fc, name_rva, iat = struct.unpack_from("<IIIII", self.data, off)
            if not (oft or name_rva or iat):
                break
            syms = []
            thunks = self.rva_to_off(oft or iat)
            j = 0
            while True:
                entry = struct.unpack_from("<Q", self.data, thunks + 8 * j)[0]
                if not entry:
                    break
                if entry & (1 << 63):
                    syms.append(f"#ordinal {entry & 0xFFFF}")
                else:
                    syms.append(self.cstr((entry & 0x7FFFFFFF) + 2))
                j += 1
            out.append((self.cstr(name_rva), syms, iat))
            i += 1
        return out

    def iat_map(self):
        """{VA of IAT slot: 'dll!symbol'} -- what `call *0x...(%rip)` targets."""
        out = {}
        for dll, syms, iat in self.imports():
            for k, sym in enumerate(syms):
                out[self.image_base + iat + 8 * k] = f"{dll}!{sym}"
        return out

    def import_data_ranges(self):
        """[(start_rva, end_rva)] covered by the import directory's own data.

        The linker puts .idata in an executable section in this driver, so
        a linear disassembler decodes the hint/name table as instructions.
        Knowing which RVAs are import data is what separates a real IN/OUT
        from an import hint that happens to be 0x02EC.
        """
        rva, size = self.dirs[1] if len(self.dirs) > 1 else (0, 0)
        if not rva or not size:
            return []
        ranges = [(rva, rva + size)]
        base = self.rva_to_off(rva)
        i = 0
        while True:
            oft, _ts, _fc, name_rva, iat = struct.unpack_from(
                "<IIIII", self.data, base + 20 * i)
            if not (oft or name_rva or iat):
                break
            ranges.append((name_rva, name_rva + len(self.cstr(name_rva)) + 1))
            for table in (oft, iat):
                if not table:
                    continue
                thunks = self.rva_to_off(table)
                j = 0
                while True:
                    entry = struct.unpack_from("<Q", self.data, thunks + 8 * j)[0]
                    if not entry:
                        break
                    if not entry & (1 << 63):
                        hint = entry & 0x7FFFFFFF
                        ranges.append(
                            (hint, hint + 2 + len(self.cstr(hint + 2)) + 1))
                    j += 1
                ranges.append((table, table + 8 * (j + 1)))
            i += 1
        return ranges

    def function_ranges(self):
        """[(begin_rva, end_rva)] from .pdata's RUNTIME_FUNCTION table.

        x86-64 PEs must describe every non-leaf function here for stack
        unwinding, which makes it a far better code/data oracle than
        "is it in an executable section" -- MSVC parks jump tables and
        offset arrays inside .text, and a linear disassembler happily
        decodes those as instructions. Leaf functions that touch no
        non-volatile state may legitimately be absent, so "outside every
        range" means "not in a function this table describes", not
        "definitely data".
        """
        rva, size = self.dirs[3] if len(self.dirs) > 3 else (0, 0)
        if not rva or not size:
            return []
        off = self.rva_to_off(rva)
        out = []
        for i in range(size // 12):
            begin, end, _unwind = struct.unpack_from("<III", self.data, off + 12 * i)
            if begin or end:
                out.append((begin, end))
        return sorted(out)

    def exports(self):
        """[(ordinal, name, rva)] sorted by ordinal."""
        rva, size = self.dirs[0] if self.dirs else (0, 0)
        if not rva or not size:
            return []
        off = self.rva_to_off(rva)
        ordinal_base, naddr, nnames = struct.unpack_from("<III", self.data, off + 16)
        addr_rva, name_rva, ord_rva = struct.unpack_from("<III", self.data, off + 28)
        addrs = self.rva_to_off(addr_rva)
        funcs = [struct.unpack_from("<I", self.data, addrs + 4 * i)[0]
                 for i in range(naddr)]
        named = {}
        if nnames:
            names = self.rva_to_off(name_rva)
            ords = self.rva_to_off(ord_rva)
            for i in range(nnames):
                n = struct.unpack_from("<I", self.data, names + 4 * i)[0]
                o = struct.unpack_from("<H", self.data, ords + 2 * i)[0]
                named[o] = self.cstr(n)
        return sorted((ordinal_base + i, named.get(i, ""), f)
                      for i, f in enumerate(funcs) if f)


def scan_portio(pe: PE):
    """[(rva, opcode, mnemonic, section, context_bytes)] over exec sections."""
    hits = []
    for s in pe.sections:
        if not s["exec"]:
            continue
        blob = pe.data[s["rawptr"]:s["rawptr"] + s["rawsize"]]
        for i, b in enumerate(blob):
            if b in PORTIO_OPCODES:
                ctx = blob[max(0, i - 8):i + 8]
                hits.append((s["vaddr"] + i, b, PORTIO_OPCODES[b], s["name"], ctx))
    return hits


def parse_listing(path: str):
    """{VA: mnemonic} for every instruction start in an objdump listing."""
    starts = {}
    pattern = re.compile(r"^\s*([0-9a-f]+):\t[0-9a-f ]+\t\s*(\S+)")
    with open(path) as f:
        for line in f:
            m = pattern.match(line)
            if m:
                starts[int(m.group(1), 16)] = m.group(2)
    return starts


def in_jump_table(pe: PE, rva: int) -> bool:
    """Do this RVA and its 4-byte neighbours all read as code pointers?

    MSVC emits switch jump tables as arrays of image-relative 4-byte RVAs
    parked inside the function body, usually right after a `ret`. .pdata
    still covers them, so the only thing that separates such a table from
    real code is that the 4-byte read here and at an adjacent slot both
    land in an executable section -- which arbitrary instruction bytes
    essentially never do. A heuristic, so its verdicts belong in a
    write-up as "adjudicated as a jump-table entry", not as proof.
    """
    code = [(s["vaddr"], s["vaddr"] + s["vsize"]) for s in pe.sections if s["exec"]]

    def is_code_pointer(at: int) -> bool:
        off = pe.rva_to_off(at)
        if off is None or off + 4 > len(pe.data):
            return False
        target = struct.unpack_from("<I", pe.data, off)[0]
        return any(start <= target < end for start, end in code)

    return is_code_pointer(rva) and (is_code_pointer(rva - 4)
                                     or is_code_pointer(rva + 4))


def adjudicate_portio(pe: PE, listing: dict):
    """[(rva, mnemonic_or_None, verdict)] -- candidate vs instruction boundary."""
    idata = pe.import_data_ranges()
    functions = pe.function_ranges()
    out = []
    for rva, _op, _mnem, _sec, _ctx in scan_portio(pe):
        va = pe.image_base + rva
        if va not in listing:
            out.append((rva, None, "not an instruction start (data, or "
                                   "inside a longer instruction)"))
        elif any(start <= rva < end for start, end in idata):
            out.append((rva, listing[va], "import-directory data, not code"))
        elif in_jump_table(pe, rva):
            out.append((rva, listing[va], "jump-table entry embedded in .text"))
        elif not any(start <= rva < end for start, end in functions):
            out.append((rva, listing[va], "outside every .pdata function range"))
        elif listing[va] in ("in", "out", "insb", "insl", "outsb", "outsl", "outsw"):
            out.append((rva, listing[va], "PORT I/O INSTRUCTION"))
        else:
            out.append((rva, listing[va], "decodes as a different instruction"))
    return out


def scan_imm32_operands(pe: PE, listing=None):
    """[(rva, value)] for every 32-bit immediate operand in executable code.

    Looking for a bare 4-byte value anywhere in a 2 MB .text returns
    hundreds of coincidental matches, so only the encodings a constant is
    actually loaded or compared in are accepted: `mov r32, imm32` (B8+r),
    `cmp eax, imm32` (3D), `cmp r32, imm32` (81 /7, register-direct) and
    `mov dword ptr [..], imm32` (C7 /0). That still over-matches, because
    the scan does not know where instructions begin -- pass `listing` (see
    parse_listing) to keep only the matches a real disassembler agrees
    start an instruction.
    """
    hits = []
    for s in pe.sections:
        if not s["exec"]:
            continue
        blob = pe.data[s["rawptr"]:s["rawptr"] + s["rawsize"]]
        for i in range(len(blob) - 6):
            op = blob[i]
            if op == 0x3D or 0xB8 <= op <= 0xBF:
                imm_at = i + 1
            elif op in (0x81, 0xC7) and 0xC0 <= blob[i + 1] <= 0xFF:
                reg = (blob[i + 1] >> 3) & 7
                if (op == 0x81 and reg != 7) or (op == 0xC7 and reg != 0):
                    continue
                imm_at = i + 2
            else:
                continue
            if imm_at + 4 > len(blob):
                continue
            rva = s["vaddr"] + i
            if listing is not None and pe.image_base + rva not in listing:
                continue
            hits.append((rva, struct.unpack_from("<I", blob, imm_at)[0]))
    return hits


def scan_immediates(pe: PE, listing=None):
    """{value: [rva, ...]} for the IMMEDIATES of interest, as operands."""
    found = {}
    for rva, value in scan_imm32_operands(pe, listing):
        if value in IMMEDIATES:
            found.setdefault(value, []).append(rva)
    return found


def decode_ctl_code(code: int):
    """(DeviceType, Function, Method, Access) or None if implausible."""
    if not 0 < code < (1 << 32):
        return None
    device = (code >> 16) & 0xFFFF
    access = (code >> 14) & 0x3
    function = (code >> 2) & 0xFFF
    method = code & 0x3
    # Vendor drivers use FILE_DEVICE_UNKNOWN (0x22) or a private type
    # >= 0x8000; a function code below 0x800 is Microsoft-reserved.
    # 0xFFFF is excluded because it is not a device type anyone ships, and
    # accepting it turns every small negative constant into a fake IOCTL.
    if device == 0xFFFF or (device != 0x22 and device < 0x8000):
        return None
    if not 0x800 <= function <= 0xFFF:
        return None
    return device, function, METHODS[method], ACCESSES[access]


def scan_ioctls(pe: PE, listing=None):
    """[(rva, code, decoded)] for CTL_CODE-shaped immediate operands."""
    return [(rva, code, decode_ctl_code(code))
            for rva, code in scan_imm32_operands(pe, listing)
            if decode_ctl_code(code)]


def scan_strings(pe: PE, minlen: int = 6):
    """[(rva, encoding, text)] -- ASCII and UTF-16LE, file order."""
    out = []
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, pe.data):
        out.append((pe.off_to_rva(m.start()), "ascii",
                    m.group().decode("ascii")))
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){%d,}" % minlen, pe.data):
        out.append((pe.off_to_rva(m.start()), "utf-16le",
                    m.group().decode("utf-16-le")))
    return [(rva, enc, text) for rva, enc, text in out if rva is not None]


def print_headers(pe: PE) -> None:
    print(f"machine       0x{pe.machine:04X} (x86-64)" if pe.machine == 0x8664
          else f"machine       0x{pe.machine:04X}")
    print(f"image base    0x{pe.image_base:016X}")
    print(f"entry point   RVA 0x{pe.entry_rva:08X} "
          f"(VA 0x{pe.image_base + pe.entry_rva:X})")
    print(f"subsystem     {pe.subsystem} "
          f"({'native/driver' if pe.subsystem == 1 else 'windows'})")
    print(f"sections      {pe.nsections}")
    for s in pe.sections:
        print(f"  {s['name']:<8} RVA 0x{s['vaddr']:06X}  vsize 0x{s['vsize']:06X}  "
              f"raw 0x{s['rawptr']:06X}/0x{s['rawsize']:06X}  "
              f"flags 0x{s['flags']:08X}{'  EXEC' if s['exec'] else ''}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pefile", help="native PE, e.g. vendor/.../ACPIDriver.sys")
    ap.add_argument("--portio", action="store_true", help="scan for IN/OUT opcodes")
    ap.add_argument("--immediates", action="store_true", help="scan for EC addresses")
    ap.add_argument("--ioctls", action="store_true", help="scan for CTL_CODE constants")
    ap.add_argument("--strings", action="store_true", help="dump ASCII and UTF-16LE strings")
    ap.add_argument("--iat", action="store_true", help="dump IAT slot VA -> dll!symbol")
    ap.add_argument("--min-len", type=int, default=6, help="--strings minimum length")
    ap.add_argument("--listing", help="disasm.sh listing; restricts the code "
                                      "scans to real instruction boundaries")
    ap.add_argument("--self-check", action="store_true",
                    help="print the counts the analysis docs quote")
    args = ap.parse_args()

    with open(args.pefile, "rb") as f:
        pe = PE(f.read())
    listing = parse_listing(args.listing) if args.listing else None

    if args.self_check:
        imports = pe.imports()
        ioctls = sorted({code for _, code, _ in scan_ioctls(pe, listing)})
        immediates = scan_immediates(pe, listing)
        print(f"file              {args.pefile}")
        print(f"sections          {pe.nsections}")
        print(f"import-dlls       {len(imports)}")
        print(f"import-symbols    {sum(len(s) for _, s, _ in imports)}")
        print(f"exports           {len(pe.exports())}")
        print(f"portio-candidates {len(scan_portio(pe))}")
        if listing is not None:
            verdicts = adjudicate_portio(pe, listing)
            real = [v for _, _, v in verdicts if v == "PORT I/O INSTRUCTION"]
            print(f"portio-confirmed  {len(real)}")
        print(f"ioctl-constants   {len(ioctls)}")
        for code in ioctls:
            print(f"  0x{code:08X}")
        for value in sorted(IMMEDIATES):
            n = len(immediates.get(value, ()))
            print(f"imm 0x{value:04X}        {n} operand(s)  {IMMEDIATES[value]}")
        return

    if args.portio:
        if listing is not None:
            verdicts = adjudicate_portio(pe, listing)
            for rva, mnem, verdict in verdicts:
                print(f"RVA 0x{rva:06X}  {mnem or '-':<10} {verdict}")
            real = sum(1 for _, _, v in verdicts if v == "PORT I/O INSTRUCTION")
            decoded = sum(1 for m in listing.values() if m in ("in", "out"))
            print(f"{len(verdicts)} candidate byte(s), {real} of them real "
                  f"port-I/O instructions")
            print(f"{decoded} IN/OUT instruction(s) in the listing overall")
            return
        for rva, op, mnem, sec, ctx in scan_portio(pe):
            print(f"RVA 0x{rva:06X}  {sec:<8} opcode 0x{op:02X}  {mnem:<14} "
                  f"ctx {ctx.hex()}")
        print(f"{len(scan_portio(pe))} candidate byte(s) in executable sections "
              f"-- screening only; re-run with --listing to adjudicate")
        return

    if args.immediates:
        found = scan_immediates(pe, listing)
        for value in sorted(IMMEDIATES):
            rvas = found.get(value)
            if not rvas:
                print(f"0x{value:04X}  not found by this scan  {IMMEDIATES[value]}")
                continue
            print(f"0x{value:04X}  {IMMEDIATES[value]}")
            for rva in rvas:
                print(f"    RVA 0x{rva:06X}")
        return

    if args.ioctls:
        for rva, code, (device, function, method, access) in scan_ioctls(pe, listing):
            print(f"RVA 0x{rva:06X}  0x{code:08X}  "
                  f"device 0x{device:04X} function 0x{function:03X} "
                  f"{method} {access}")
        return

    if args.strings:
        for rva, enc, text in scan_strings(pe, args.min_len):
            print(f"RVA 0x{rva:06X}  {enc:<8} {text}")
        return

    if args.iat:
        for va, sym in sorted(pe.iat_map().items()):
            print(f"0x{va:016X}  {sym}")
        return

    print_headers(pe)
    print("\nimports:")
    for dll, syms, iat in pe.imports():
        print(f"  {dll}  ({len(syms)} symbols, IAT at RVA 0x{iat:06X})")
        for s in syms:
            print(f"    {s}")
    exports = pe.exports()
    print(f"\nexports: {len(exports)}")
    for ordinal, name, rva in exports:
        print(f"  #{ordinal:<5} RVA 0x{rva:06X}  {name}")


if __name__ == "__main__":
    sys.exit(main())
