#!/usr/bin/env python3
r"""List every EC register access in a decompiled vendor service tree.

`GCUService` reaches the EC only through `MyECIO.MyEcCtrl.Read/Write(name, addr,
...)` (-> `AcpiCtrl` -> `\\.\ACPIDriver` IOCTL -> ACPI `ECRR`/`ECRW`, see
`windows/native/`). `ECSpec` constants are C# `const`, so the compiler inlined
them: every call site carries its EC address as a literal, which is what makes
a plain-text scan of the decompiled tree complete for literal addresses. Sites
whose address is computed (`(ushort)(3840 + i)`, a table walk) are listed with
their base and flagged `computed`, since the scan cannot know the index range.

Output is one CSV row per call site, so "which vendor method writes 0x07A6" and
"what does `SetHealthProtectionLow` touch" are both a grep away, and the table
can be regenerated from the committed tree rather than trusted.

Usage:
  ec_callsites.py windows/decompiled/v3.1.39.0/GCUService > sites.csv
  ec_callsites.py TREE --addr 0x07A6          # only this address
  ec_callsites.py TREE --summary              # per-address read/write counts
"""
import argparse
import csv
import os
import re
import sys

CALL = re.compile(
    r"\b(?P<recv>EcCtrl|MyEcCtrl\.Instance|AcpiModel|EcModel)\s*\.\s*"
    r"(?P<op>Read|Write)\s*\(")
METHOD = re.compile(
    r"^\s*(?:(?:public|private|internal|protected|static|async|override|virtual|"
    r"unsafe|extern|new|sealed)\s+)+[\w<>\[\],\.\s?]+?\s+(?P<name>[\w<>\.]+)\s*\("
    r"[^;]*$")
CLASS = re.compile(r"^\s*(?:[\w]+\s+)*(?:class|struct)\s+(?P<name>\w+)")
NAMESPACE = re.compile(r"^\s*namespace\s+(?P<name>[\w\.]+)")


def split_args(s):
    """Split a C# argument list at top-level commas; stop at the closing paren."""
    depth, cur, out = 0, [], []
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                out.append("".join(cur).strip())
                return out
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    return None  # unterminated on this line


def parse_addr(expr):
    e = expr.replace(" ", "")
    m = re.fullmatch(r"(?:\(ushort\))?(\d+)", e)
    if m:
        return int(m.group(1)), "literal"
    m = re.fullmatch(r"(?:\(ushort\))?0x([0-9A-Fa-f]+)", e)
    if m:
        return int(m.group(1), 16), "literal"
    m = re.search(r"\((?:ushort\))?\(?(\d+)\+", e)
    if m:
        return int(m.group(1)), "computed"
    return None, "unresolved"


def scan(root):
    for dirpath, _, files in os.walk(root):
        for fn in sorted(files):
            if not fn.endswith(".cs"):
                continue
            path = os.path.join(dirpath, fn)
            ns = cls = meth = ""
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                lines = fh.readlines()
            for i, line in enumerate(lines, 1):
                if m := NAMESPACE.match(line):
                    ns = m.group("name")
                if m := CLASS.match(line):
                    cls = m.group("name")
                if m := METHOD.match(line):
                    meth = m.group("name")
                for c in CALL.finditer(line):
                    rest = line[c.end():]
                    j = i
                    args = split_args(rest)
                    while args is None and j < len(lines):  # call spans lines
                        rest += lines[j]
                        j += 1
                        args = split_args(rest)
                    if not args or len(args) < 2:
                        continue
                    addr, kind = parse_addr(args[1])
                    yield {
                        "file": os.path.relpath(path, root).replace(os.sep, "/"),
                        "line": i,
                        "type": f"{ns}.{cls}".strip("."),
                        "method": meth,
                        "op": c.group("op").lower(),
                        "addr": f"0x{addr:04X}" if addr is not None else "",
                        "addr_kind": kind,
                        "addr_expr": args[1],
                        "value_expr": args[2] if len(args) > 2 else "",
                    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tree")
    ap.add_argument("--addr", help="only sites at this EC address (hex or decimal)")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args(argv)

    rows = list(scan(args.tree))
    if args.addr:
        want = int(args.addr, 0)
        rows = [r for r in rows if r["addr"] and int(r["addr"], 16) == want]

    if args.summary:
        agg = {}
        for r in rows:
            k = r["addr"] or r["addr_expr"]
            a = agg.setdefault(k, {"read": 0, "write": 0, "kind": r["addr_kind"],
                                   "writers": set()})
            a[r["op"]] += 1
            if r["op"] == "write":
                a["writers"].add(f"{r['type'].split('.')[-1]}.{r['method']}")
        w = csv.writer(sys.stdout, lineterminator="\n")
        w.writerow(["addr", "addr_kind", "reads", "writes", "writers"])
        for k in sorted(agg):
            a = agg[k]
            w.writerow([k, a["kind"], a["read"], a["write"],
                        "; ".join(sorted(a["writers"]))])
        return 0

    w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()) if rows else
                       ["file"], lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    print(f"# {len(rows)} sites", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
