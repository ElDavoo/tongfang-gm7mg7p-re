#!/usr/bin/env python3
"""Generate ec/ghidra/xdata-symbols.csv: one Ghidra EXTMEM symbol per XDATA
address in ec/annotations/registers.yaml, for step 3 of ec/ghidra/README.md
("Name XDATA from ../annotations/registers.yaml before decompiling").

This is a generator, not an editor. It reads registers.yaml and never writes
it: a register's `status:` changes when a human has evidence for it
(CLAUDE.md), and a renamed symbol must never be able to imply that happened.

Output columns: addr,name,from_register,register_status,derivation,programs
Header-only, no comment lines -- ec/README.md (the bank0-8038 paragraph) is
the house rule that a later consumer reads these with csv.DictReader.

`programs` is always `bank0;bank1`, never `pd`. The ITE8850-PD image at file
0x20000 is a separate 8051 program with its own XDATA map (ec/README.md;
ec/annotations/lightbar-bat-flow.md 2), so a `MOV DPTR,#0x07E2` inside it is
not a reference to the EC register at 0x07E2. An address in registers.yaml
is an EC address; naming it for the two images that share the EC's banks
claims nothing about the PD one.

Derivation rules, applied in this order per entry:

  1. scalar-name  -- the entry has a single `addr`; the name is the entry
     name with any trailing `(...)` stripped (`OEM_4 (CHARGING_PROFILE_MASK)`
     -> `OEM_4`).
  2. name-split   -- the entry has several addrs and its name splits 1:1
     across them on `" / "` once the parens are stripped, e.g.
     `LIGHTBAR_AC_CTRL / RED / GREEN / BLUE` over four addrs yields four
     names. Each is emitted as the whole split re-joined, the tail prefixed
     to the base: `LIGHTBAR_AC_CTRL`, `LIGHTBAR_AC_CTRL_RED`,
     `..._GREEN`, `..._BLUE`. A bare `RED` would be a valid identifier and
     is a legal emission under the uniqueness rule below, but it is a poor
     one in a disassembly -- a decompilation full of `RED`/`GREEN`/`BLUE`
     with no register in sight says nothing, so the prefix earns its keep
     in readability even though it is not strictly required.
  3. override     -- the address is listed in ec/ghidra/xdata-overrides.csv
     (columns addr,name,reason), the hand-maintained escape hatch. Reason
     cites where the name comes from.

Anything none of the three can name is not silently dropped: the tool exits
non-zero and lists every such address, pointing at the overrides file. That
list is the human's to-do, not a bug to paper over.

**Multi-byte registers are named by address order, `<BASE>_0`, `<BASE>_1`,
... -- never `_LO`/`_HI`, `_HIGH`/`_LOW`, or `_BYTE1`/`_BYTE0`.**
ec/annotations/charge-target-derating.md reads the 16-bit stores as
big-endian, but that is a hand reading of one routine, not a decoded
property of the stores, and a wrong endianness suffix baked into a symbol
is an overclaim in the least defensible place -- the name will outlive the
note that corrects it. `_0`/`_1` also keeps the name honest about
registers.yaml: the YAML records the addresses, not a byte order.

What this does *not* say: whether a register exists, is written, or acts.
`status:` is copied verbatim from registers.yaml so the reader sees what
the entry said; a `static_refs: 0` / `status: absent` row here means "not
found by this method", never "absent" (docs/findings.md 4c, and the
0x07B9 retraction in registers.yaml itself). The generator's `--check` mode
asserts the mechanical invariants only -- counts, uniqueness, identifier
shape, no `pd` -- and not any of that.

Usage:
    python3 ec/tools/gen_xdata_symbols.py                 # write the CSV
    python3 ec/tools/gen_xdata_symbols.py --check         # diff vs committed
    python3 ec/tools/gen_xdata_symbols.py --self-test ec/annotations/registers.yaml
"""
import argparse
import csv
import io
import os
import re
import sys

import yaml

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
EC_DIR = os.path.dirname(TOOL_DIR)
DEFAULT_REGISTERS = os.path.join(EC_DIR, "annotations", "registers.yaml")
OVERRIDES = os.path.join(EC_DIR, "ghidra", "xdata-overrides.csv")
OUT_CSV = os.path.join(EC_DIR, "ghidra", "xdata-symbols.csv")

COLUMNS = ["addr", "name", "from_register", "register_status", "derivation",
           "programs"]

# Only the EC firmware proper: common area plus the two CODE banks that have
# callers in this build (ec/README.md's bank table). Never "pd".
PROGRAMS = "bank0;bank1"

C_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# The name ec/ghidra/README.md already prescribes for 0x07A6, so the
# self-test oracle pins the whole pipeline to a name a reader already has in
# front of them. It is an override row, not a scalar-name one: registers.yaml
# calls the entry `OEM_4 (CHARGING_PROFILE_MASK)` and rule 1 alone would
# emit a bare `OEM_4`, dropping what the byte is for.
ORACLE_ADDR = 0x07A6
ORACLE_NAME = "OEM_4_CHARGING_PROFILE"


def strip_parens(name: str) -> str:
    """Entry name with any trailing `(...)` removed, whitespace trimmed."""
    return re.sub(r"\s*\(.*\)\s*$", "", name).strip()


def as_addrs(entry) -> list:
    """`addr` is scalar or list; normalise to a list of ints."""
    addrs = entry["addr"]
    if not isinstance(addrs, list):
        addrs = [addrs]
    out = []
    for a in addrs:
        if not isinstance(a, int):
            raise ValueError(f"non-integer addr {a!r} in entry "
                             f"{entry.get('name', '?')!r}")
        out.append(a)
    return out


def load_overrides(path: str) -> dict:
    """addr -> (name, reason) from the hand-maintained escape hatch."""
    overrides = {}
    if not os.path.exists(path):
        return overrides
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            addr = int(row["addr"], 0)
            if addr in overrides:
                raise ValueError(f"0x{addr:04X} listed twice in {path}")
            overrides[addr] = (row["name"], row["reason"])
    return overrides


def name_entry(entry, overrides: dict) -> tuple:
    """(addr -> (name, derivation), {addr: why-not}) for one entry.

    Rules are tried in the order scalar-name, name-split, override; a name
    is taken from whichever rule first produces one for that address."""
    addrs = as_addrs(entry)
    raw_name = str(entry.get("name", ""))
    base = strip_parens(raw_name)
    names = {}
    unresolved = {}

    if len(addrs) == 1:
        # Rule 1: scalar-name.
        addr = addrs[0]
        if addr in overrides:
            names[addr] = (overrides[addr][0], "override")
        elif C_IDENT.match(base):
            names[addr] = (base, "scalar-name")
        else:
            unresolved[addr] = "entry name is not a usable C identifier"
    else:
        # Rule 2: name-split, a 1:1 split on " / ". Rebuilt as base + "_" +
        # each tail, so a colour/limit tail is not emitted on its own.
        parts = [p.strip() for p in base.split(" / ")]
        parts = [re.sub(r"\s*\(.*\)\s*$", "", p).strip() for p in parts]
        if len(parts) == len(addrs) and all(C_IDENT.match(p) for p in parts):
            head = parts[0]
            for addr, part in zip(addrs, parts):
                if addr in overrides:
                    names[addr] = (overrides[addr][0], "override")
                elif part == head:
                    names[addr] = (part, "name-split")
                else:
                    names[addr] = (f"{head}_{part}", "name-split")
        else:
            for addr in addrs:
                if addr in overrides:
                    names[addr] = (overrides[addr][0], "override")
                else:
                    unresolved[addr] = (f"entry has {len(addrs)} addrs but its "
                                        f"name splits {len(parts)} ways on "
                                        f"' / '")
    return names, unresolved


def build_rows(regs, overrides: dict) -> tuple:
    """(rows, unresolved) -- one row per address in registers.yaml order.

    Rows carry `from_register` and `register_status` verbatim so a reader
    can see the source entry, parens and all."""
    rows = []
    unresolved = {}
    for entry in regs:
        status = str(entry.get("status", ""))
        raw_name = str(entry.get("name", ""))
        names, bad = name_entry(entry, overrides)
        unresolved.update(bad)
        for addr in as_addrs(entry):
            if addr in names:
                name, derivation = names[addr]
            else:
                continue  # recorded in unresolved
            rows.append({
                "addr": f"0x{addr:04X}",
                "name": name,
                "from_register": raw_name,
                "register_status": status,
                "derivation": derivation,
                "programs": PROGRAMS,
            })
    return rows, unresolved


def check_invariants(rows) -> int:
    """Mechanical invariants -- return a problem count, 0 if all hold.

    None of this says a name is *right*, only that the set is well formed:
    one row per address, addresses and names unique, names usable C
    identifiers, and the PD image never named as a program."""
    problems = 0
    addrs = [r["addr"] for r in rows]
    names = [r["name"] for r in rows]
    dup_addrs = {a for a in addrs if addrs.count(a) > 1}
    dup_names = {n for n in names if names.count(n) > 1}
    for a in sorted(dup_addrs):
        print(f"0x{int(a, 0):04X}: appears in {addrs.count(a)} rows", file=sys.stderr)
        problems += 1
    for n in sorted(dup_names):
        print(f"symbol {n}: emitted more than once", file=sys.stderr)
        problems += 1
    for r in rows:
        if not C_IDENT.match(r["name"]):
            print(f"0x{int(r['addr'], 0):04X}: {r['name']!r} is not a valid "
                  "C identifier", file=sys.stderr)
            problems += 1
        programs = r["programs"].split(";")
        if "pd" in programs:
            print(f"0x{int(r['addr'], 0):04X}: names the PD image, which has "
                  "its own XDATA map", file=sys.stderr)
            problems += 1
    return problems


def render(rows) -> str:
    """The CSV text, with \\n line endings and no trailing blank lines."""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def report_unresolved(unresolved: dict, overrides_path: str) -> None:
    print(f"{len(unresolved)} address(es) could not be named by rules "
          "scalar-name / name-split / override:", file=sys.stderr)
    for addr in sorted(unresolved):
        print(f"  0x{addr:04X}: {unresolved[addr]}", file=sys.stderr)
    print(f"name them by hand in {overrides_path} (addr,name,reason); the "
          "reason cites where the name comes from", file=sys.stderr)


def self_test(registers_path: str) -> int:
    """Known-answer run against a committed registers.yaml.

    Every assertion is re-derivable from that file plus the two CSVs
    beside this tool -- no image, no network, no Ghidra."""
    with open(registers_path) as f:
        regs = yaml.safe_load(f)["registers"]
    overrides = load_overrides(OVERRIDES)
    rows, unresolved = build_rows(regs, overrides)
    n_addrs = sum(len(as_addrs(e)) for e in regs)
    names = {r["addr"]: r["name"] for r in rows}
    ok = True

    def check(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
        if not cond:
            ok = False

    print("gen_xdata_symbols.py --self-test")
    check("every address in registers.yaml is named (nothing unresolved)",
          not unresolved)
    check(f"symbol count == total address count in registers.yaml "
          f"({len(rows)} == {n_addrs})", len(rows) == n_addrs)
    check("every address appears in exactly one row",
          len({r["addr"] for r in rows}) == len(rows))
    check("every symbol name is a valid, unique C identifier",
          all(C_IDENT.match(r["name"]) for r in rows) and
          len({r["name"] for r in rows}) == len(rows))
    check(f"no row names the PD image (programs == {PROGRAMS!r})",
          all(r["programs"] == PROGRAMS for r in rows))
    check(f"oracle: 0x{ORACLE_ADDR:04X} is named {ORACLE_NAME} "
          "(ec/ghidra/README.md)",
          names.get(f"0x{ORACLE_ADDR:04X}") == ORACLE_NAME)
    check("multi-byte registers are named by address order, no endianness "
          "suffix (_LO/_HI/_HIGH/_LOW/_BYTE0/_BYTE1)",
          not any(re.search(r"_(LO|HI|HIGH|LOW|BYTE0|BYTE1)$", r["name"])
                  for r in rows))
    check("derivation is one of scalar-name / name-split / override",
          {r["derivation"] for r in rows} <= {"scalar-name", "name-split",
                                              "override"})
    check("from_register and register_status are carried through verbatim",
          all(r["from_register"] and r["register_status"] for r in rows))
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help=f"regenerate in memory and diff against {OUT_CSV} "
                         "(plus the mechanical invariants); no network, no Ghidra")
    ap.add_argument("--self-test", metavar="REGISTERS",
                    help="known-answer run against the given registers.yaml")
    ap.add_argument("--registers", default=DEFAULT_REGISTERS,
                    help="registers.yaml to read (default: the one beside this tool)")
    ap.add_argument("--out", default=OUT_CSV,
                    help=f"CSV to write (default: {OUT_CSV})")
    ap.add_argument("--overrides", default=OVERRIDES,
                    help=f"hand-maintained overrides (default: {OVERRIDES})")
    args = ap.parse_args()

    if args.self_test:
        if args.check:
            print("--self-test and --check are exclusive", file=sys.stderr)
            return 1
        return self_test(args.self_test)

    with open(args.registers) as f:
        regs = yaml.safe_load(f)["registers"]
    overrides = load_overrides(args.overrides)
    rows, unresolved = build_rows(regs, overrides)
    n_addrs = sum(len(as_addrs(e)) for e in regs)

    if unresolved:
        report_unresolved(unresolved, args.overrides)
        return 1

    problems = check_invariants(rows)
    if len(rows) != n_addrs:
        print(f"{len(rows)} rows for {n_addrs} addresses in {args.registers} "
              "-- row count must equal address count", file=sys.stderr)
        problems += 1
    if problems:
        return 1

    text = render(rows)
    if args.check:
        try:
            with open(args.out, newline="") as f:
                on_disk = f.read()
        except FileNotFoundError:
            print(f"{args.out} does not exist -- run without --check to write it",
                  file=sys.stderr)
            return 1
        if on_disk != text:
            print(f"{args.out} differs from a fresh generation "
                  f"({len(on_disk.splitlines())} on disk vs "
                  f"{len(text.splitlines())} generated) -- run without --check "
                  "to rewrite", file=sys.stderr)
            for i, (a, b) in enumerate(zip(on_disk.splitlines(),
                                           text.splitlines())):
                if a != b:
                    print(f"  line {i+1}: on disk {a!r} != generated {b!r}",
                          file=sys.stderr)
            return 1
        print(f"{args.out}: {len(rows)} symbols match a fresh generation "
              f"from {args.registers}")
        return 0

    with open(args.out, "w", newline="") as f:
        f.write(text)
    print(f"wrote {args.out}: {len(rows)} symbols for {n_addrs} addresses in "
          f"{args.registers} (programs {PROGRAMS}, no PD)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
