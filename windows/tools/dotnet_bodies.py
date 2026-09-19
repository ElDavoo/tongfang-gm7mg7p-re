#!/usr/bin/env python3
r"""Census of .NET method-body headers in one or more assembly files.

For every MethodDef with a non-zero RVA, parse the ECMA-335 II.25.4 body header
at that RVA and classify it:

  tiny     -- low 2 bits 0b10; code size in the top 6 bits
  fat      -- low 2 bits 0b11, header size field 3 (dwords), code fits the section,
              LocalVarSigTok 0 or a StandAloneSig (0x11) token
  invalid  -- anything else: this is what an encrypted body looks like on disk
              (ILSpy's "Invalid MethodBodyBlock: Invalid method header")

Run it on the shipped file and on a `dotnet_dump.py` dump side by side. A dump
that really holds decrypted bodies turns the shipped file's `invalid` column into
`tiny`/`fat`; a dump that doesn't leaves it where it was. `--type` narrows the
per-method listing to one class (e.g. BatteryProtection2) so the claim can be
checked for exactly the methods an issue cares about.

Usage:
  dotnet_bodies.py GCUService.exe GCUService.dumped.exe
  dotnet_bodies.py --type BatteryProtection2 GCUService.exe GCUService.dumped.exe
"""
import argparse
import struct
import sys

import dnfile


def classify(pe, rva):
    try:
        off = pe.get_offset_from_rva(rva)
    except Exception:
        return "invalid", "rva outside any section"
    data = pe.__data__
    if off >= len(data):
        return "invalid", "offset past end of file"
    b0 = data[off]
    if b0 & 3 == 2:
        return "tiny", f"code {b0 >> 2}"
    if b0 & 3 == 3 and off + 12 <= len(data):
        flags_size, max_stack, code_size, local_tok = struct.unpack_from(
            "<HHII", data, off)
        hdr_dwords = flags_size >> 12
        sec = pe.get_section_by_rva(rva)
        end = rva + 12 + code_size
        in_section = sec is not None and end <= sec.VirtualAddress + max(
            sec.Misc_VirtualSize, sec.SizeOfRawData)
        tok_ok = local_tok == 0 or (local_tok >> 24) == 0x11
        if hdr_dwords == 3 and in_section and tok_ok and code_size < 0x100000:
            return "fat", f"code {code_size} stack {max_stack}"
        return "invalid", (f"fat-looking but hdr={hdr_dwords} code={code_size} "
                           f"tok=0x{local_tok:08X}")
    return "invalid", f"header byte 0x{b0:02X}"


def methods(path):
    pe = dnfile.dnPE(path)
    md = pe.net.mdtables
    types = md.TypeDef.rows if md.TypeDef else []
    meths = md.MethodDef.rows if md.MethodDef else []
    # owner of each method: TypeDef.MethodList runs
    owner = [None] * len(meths)
    starts = []
    for t in types:
        ml = t.MethodList
        idx = ml[0].row_index if isinstance(ml, list) and ml else getattr(
            ml, "row_index", None)
        starts.append(idx)
    for ti, t in enumerate(types):
        s = starts[ti]
        if not s:
            continue
        e = next((starts[j] for j in range(ti + 1, len(types)) if starts[j]),
                 len(meths) + 1)
        for mi in range(s, e):
            if 1 <= mi <= len(meths):
                owner[mi - 1] = f"{t.TypeNamespace}.{t.TypeName}".lstrip(".")
    for i, m in enumerate(meths):
        yield pe, owner[i], str(m.Name), m.Rva


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--type", help="list each method of types whose name contains this")
    args = ap.parse_args(argv)

    per_file = {}
    for path in args.files:
        counts = {"tiny": 0, "fat": 0, "invalid": 0, "abstract/extern": 0}
        detail = {}
        for pe, own, name, rva in methods(path):
            if not rva:
                counts["abstract/extern"] += 1
                kind, why = "abstract/extern", ""
            else:
                kind, why = classify(pe, rva)
                counts[kind] += 1
            detail[(own, name, rva)] = (kind, why)
        per_file[path] = detail
        print(f"{path}")
        print("   " + "  ".join(f"{k} {v}" for k, v in counts.items()))

    if args.type:
        keys = [k for k in per_file[args.files[0]]
                if k[0] and args.type.lower() in k[0].lower()]
        print(f"\nmethods of types matching '{args.type}' ({len(keys)}):")
        for k in keys:
            cells = [per_file[f].get(k, ("missing", ""))[0] for f in args.files]
            print(f"  {k[0]}::{k[1]}  RVA 0x{k[2]:X}  " + "  ->  ".join(cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())
