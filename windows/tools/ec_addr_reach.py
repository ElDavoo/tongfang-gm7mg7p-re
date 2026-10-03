#!/usr/bin/env python3
r"""Which EC address bands the vendor service actually reaches, and how far.

`windows/decompiled/v3.1.39.0/ec-callsites.csv` is a census of the service's EC
call sites, and `windows/vendor-ec-map.md` presents it as one. It is one, and
this tool is what makes its *reach* a separate question from its contents: the
addresses it resolves fall in three high-byte bands and nothing else, so a
question of the form "does the service write `0x086B`" is answered by the shape
of the histogram rather than by reading 868 rows.

The question this exists for is `docs/hardware-tests/level-block-0860-086e.md`
§5's, which declines it: whether the vendor service writes any `0x08xx` byte.
The census cannot answer it on its own for three reasons, and each is closed
here rather than left in the negative:

* **The parameterised path.** `SingleZone.ReadECRAM`/`WriteECRAM` take the
  address as a parameter, so the census can only list their two helper bodies
  -- with no address, as `unresolved`. The callers are ordinary literal call
  sites and are resolved here, per address, which is the one thing a computed
  `0x08xx` write would have to appear in to be found.
* **The name table.** `ECSpec` is C# `const`, so a constant that named an
  `0x08xx` byte would be inlined into its call site and would already be in the
  census. The constant table is censused separately anyway, as an independent
  line of evidence that needs no call-site parser to be right.
* **The trees that are not the service.** `v3.1.6.0` and `v3.9.18.0` are
  partial and anti-tamper-damaged (`windows/antitamper/README.md`), so a zero
  there is a far weaker statement than a zero on the decrypted tree. The two
  are reported separately and never pooled.

**The reach is a measurement and the answer is a negative, so both are stated
as what they are.** A band with no sites means "not found by this method", never
"the service does not write there" -- the same caveat
`ec/annotations/registers.yaml` and `ec/tools/scan_refs.py` carry. A computed
site reports its base and marks the index range unproven, because
`ec_callsites.py` cannot bound `i` in `(ushort)(3840 + i)` and neither can this.

Usage:
  ec_addr_reach.py                       # the reach, per tree, and the answer
  ec_addr_reach.py --band 0x08           # every site in one high-byte band
  ec_addr_reach.py --addr 0x086B         # every site at one address
  ec_addr_reach.py --self-check          # assert the figures the write-up quotes
"""
import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ec_callsites  # noqa: E402  (needs the sys.path entry above)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The three committed managed trees, and what each one is. The label is the
# answer as much as the path is: a zero on a partial tree is not the same claim
# as a zero on the decrypted service, and pooling them would average the two
# into a statement neither supports. `t1wr_callers.py` carries the same split.
TREES = [
    ("v3.1.39.0 (the decrypted service)",
     "windows/decompiled/v3.1.39.0/GCUService"),
    ("v3.1.6.0 (partial, anti-tamper)",
     "windows/decompiled/v3.1.6.0"),
    ("v3.9.18.0 (partial, anti-tamper)",
     "windows/decompiled/v3.9.18.0"),
]

# The band this repository's `0x086x` question lives in. Named here so the
# answer and the negative are one comparison, and so a `--band 0x08` run and
# the write-up's sentence are the same claim rather than two that can drift.
LEVEL_BLOCK = (0x0800, 0x08FF)

# Helpers that take the EC address as a parameter and that `ec_callsites.py`
# cannot see, so they are searched for rather than derived from the census.
#
# `WMIEC.WMIReadECRAM`/`WMIWriteECRAM` reach the EC over WMI -- a
# `ManagementObject` `GetSetULong` invocation, not `EcCtrl` -- so no call site
# of theirs is a row in the census at all, and neither is their definition.
# They are `public static`, so unlike the `SingleZone` pair their callers are
# not confined to one file and the sweep for them is tree-wide. Neither has a
# caller anywhere in the committed tree: a dead door rather than a blind spot,
# and which of the four is which is why they are listed here individually.
#
# The `SingleZone` pair is deliberately *not* in this list. It is derived, from
# the census's own `unresolved` rows -- see `parameterised_helpers()` -- because
# a name-based sweep cannot tell it from an unrelated private helper that
# shares the spelling.
WMI_HELPERS = [
    ("MyControlCenter", "WMIEC", "WMIReadECRAM"),
    ("MyControlCenter", "WMIEC", "WMIWriteECRAM"),
    ("MyRGBKeyboard", "WMIEC", "WMIReadECRAM"),
    ("MyRGBKeyboard", "WMIEC", "WMIWriteECRAM"),
]

# A `const ushort` in an `ECSpec` table. The type matters and is why this is
# not a bare number scan: the same file carries `const uint` fan-mode codes and
# a `[Flags]` enum whose members are byte masks, and neither is an EC address.
ECSPEC_CONST = re.compile(
    r"^\s*(?:public|private|internal|protected)?\s*(?:static\s+)?const\s+ushort\s+"
    r"(?P<name>\w+)\s*=\s*(?P<val>0[xX][0-9A-Fa-f]+|\d+)\s*;")

# The `ECSpec` file of each tree, relative to that tree's root, which sits at a
# different depth in each.
ECSPEC = {
    "windows/decompiled/v3.1.39.0/GCUService": "Define/ECSpec.cs",
    "windows/decompiled/v3.1.6.0": "ECSpec.cs",
    "windows/decompiled/v3.9.18.0": "Define/ECSpec.cs",
}

# A call to a parameterised helper. `\b` on the name keeps `ReadECRAM` from
# matching a longer identifier, and the receiver is deliberately absent: the
# same method is called bare inside its own class and qualified from outside
# one, and a search that only understood the qualified spelling would miss half
# the tree.
HELPER_CALL = re.compile(r"\b(?P<name>ReadECRAM|WriteECRAM|WMIReadECRAM|"
                         r"WMIWriteECRAM)\s*\(")


def bands(rows):
    """{high byte: number of resolved sites} over rows carrying an `addr`.

    Keyed on the high byte rather than grouped into named bands, so a band
    nobody expected shows up in the histogram instead of being folded into a
    bucket a reader has to know about in advance.
    """
    out = collections.Counter()
    for r in rows:
        if r["addr"]:
            out[int(r["addr"], 16) >> 8] += 1
    return out


def span(rows):
    """(lowest, highest) resolved address, or None when nothing resolved."""
    addrs = [int(r["addr"], 16) for r in rows if r["addr"]]
    return (min(addrs), max(addrs)) if addrs else None


def computed_bases(rows):
    """{base: number of computed sites}, the fan-table walks.

    A computed site reports its base and nothing else. `ec_callsites.py` cannot
    bound the index in `(ushort)(3840 + i)` and this does not either, so the
    base is the *start* of a range rather than the range: a walk from a `0x0Fxx`
    base with an unbounded index is not an `0x08xx` site, and it is also not a
    proof that none exists.
    """
    out = collections.Counter()
    for r in rows:
        if r["addr_kind"] == "computed" and r["addr"]:
            out[r["addr"]] += 1
    return out


def parameterised_helpers(rows):
    """The helpers whose EC address is a parameter, and where to look for them.

    Derived from the census's `unresolved` rows wherever the census can supply
    them: a helper that does `EcCtrl.Write(className, Addr, ...)` is by
    definition a helper the census could not resolve, so "the addresses the
    census could not resolve" and "the helpers that take an address" are one
    set rather than two lists to keep in step. Deriving it also gets the
    scoping right, which a list of method names does not: `SingleZone` has a
    `private void WriteECRAM(ushort, ulong, string)` and
    `MyRgbLightBarDefault` has a `private static void WriteECRAM(int, uint,
    uint, uint, uint, uint)`, and a name-based sweep over the tree collects
    the second class's four call sites as though they were EC addresses. They
    are lightbar levels. A `private` method's callers are confined to the file
    it is declared in, so scoping the sweep to that file is complete rather
    than a narrowing.

    The WMI helpers in `WMI_HELPERS` are the ones the census cannot supply --
    they are not in it at all -- so they are appended tree-wide.
    """
    found = {}
    for r in rows:
        if r["addr_kind"] != "unresolved":
            continue
        found[(r["type"], r["method"], r["file"])] = {
            "helper": r["method"],
            "file": r["file"],
            "type": r["type"],
            "op": r["op"],
        }
    for ns, cls, name in WMI_HELPERS:
        found[(f"{ns}.{cls}", name, None)] = {
            "helper": name, "file": None, "type": f"{ns}.{cls}", "op": "any"}
    return list(found.values())


def helper_callers(root, helpers):
    """Every call to a parameterised helper, with its first argument.

    Returns [{helper, type, file, line, addr, addr_kind, addr_expr}] where
    `addr` is empty for a first argument that is not a literal. Those rows are
    kept rather than dropped: a caller whose address is a variable is exactly
    the shape that would hide a computed `0x08xx` write, so a sweep that
    quietly skipped them would report a clean result over the population it
    could not resolve.

    The search is over `.cs` text, so an anti-tamper casualty is a method body
    that is empty rather than one whose call is missing -- a caller the
    encryption erased is not in the file and is not counted either way. That is
    the `windows/antitamper/README.md` boundary, and it is a boundary on the
    reach rather than a fact about the addresses.
    """
    wanted = {}
    for h in helpers:
        wanted.setdefault(h["helper"], []).append(h)
    out = []
    for dirpath, _, files in os.walk(root):
        for fn in sorted(files):
            if not fn.endswith(".cs"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                lines = fh.readlines()
            for i, line in enumerate(lines, 1):
                for m in HELPER_CALL.finditer(line):
                    for h in wanted.get(m.group("name"), ()):
                        # A file-scoped helper is `private`, so no file other
                        # than the one declaring it can hold one of its
                        # callers, and the same-named method in a sibling
                        # class is a different method entirely.
                        if h["file"] is not None and h["file"] != rel:
                            continue
                        if _is_definition(line, m.start()):
                            continue
                        rest = line[m.end():]
                        j = i
                        args = ec_callsites.split_args(rest)
                        while args is None and j < len(lines):  # spans lines
                            rest += lines[j]
                            j += 1
                            args = ec_callsites.split_args(rest)
                        if not args:
                            continue
                        addr, kind = ec_callsites.parse_addr(args[0])
                        out.append({
                            "helper": m.group("name"),
                            "type": h["type"],
                            "file": rel,
                            "line": i,
                            "addr": f"0x{addr:04X}" if addr is not None else "",
                            "addr_kind": kind,
                            "addr_expr": args[0],
                        })
    return out


def _is_definition(line, at):
    """True when the match is the declaration, not a call to it.

    ILSpy writes a definition as `private void ReadECRAM(ushort Addr, ...)` and
    a call as `ReadECRAM(1900, ref num)`, so the access modifier ahead of the
    name is the discriminator. Counting a definition as a caller would add one
    unresolved row per helper to the very population the derivation is about.
    """
    return bool(re.search(r"\b(private|public|internal|protected)\s+.*$",
                          line[:at]))


def ecspec_constants(root):
    """{name: value} for every `const ushort` in the tree's `ECSpec`."""
    rel = ECSPEC.get(root)
    if rel is None:
        return None
    path = os.path.join(REPO, root, rel)
    if not os.path.exists(path):
        return None
    out = {}
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            if m := ECSPEC_CONST.match(line):
                out[m.group("name")] = int(m.group("val"), 0)
    return out


def tree_reach(root):
    """Everything the reach statement for one tree is made of."""
    abs_ = os.path.join(REPO, root)
    rows = list(ec_callsites.scan(abs_))
    helpers = parameterised_helpers(rows)
    callers = helper_callers(abs_, helpers)
    return {
        "root": root,
        "sites": rows,
        "bands": bands(rows),
        "span": span(rows),
        "kinds": collections.Counter(r["addr_kind"] for r in rows),
        "unresolved": [r for r in rows if r["addr_kind"] == "unresolved"],
        "computed": computed_bases(rows),
        "helpers": helpers,
        "callers": callers,
        "callers_resolved": [c for c in callers if c["addr"]],
        "ecspec": ecspec_constants(root),
    }


def in_band(addr, band):
    return band[0] <= addr <= band[1]


def report(t, band=LEVEL_BLOCK):
    """The reach of one tree, and the answer for `band`, as prose."""
    out = sys.stdout.write
    label = dict((path, name) for name, path in TREES)[t["root"]]
    out(f"\n== {label} ==\n")
    out(f"  {t['root']}\n")

    if not t["sites"]:
        out("  no EC call site found in this tree at all -- that is a tree this\n"
            "  method could not search, not a service that writes nothing.\n")
        out(f"\n  no answer for 0x{band[0]:04X}-0x{band[1]:04X} here: the\n"
            f"  question was never put to this tree.\n")
        if t["ecspec"]:
            named = sorted(n for n, v in t["ecspec"].items()
                           if in_band(v, band))
            out(f"  ECSpec `const ushort`: {len(t['ecspec'])} names, "
                f"0x{min(t['ecspec'].values()):04X}-"
                f"0x{max(t['ecspec'].values()):04X}; "
                f"{len(named)} name an address in the band.\n")
        return
    if t["span"] is None:
        out("  call sites found, none with a resolvable address.\n")
    else:
        lo, hi = t["span"]
        hist = " ".join(f"0x{b:02X}xx {n}" for b, n in sorted(t["bands"].items()))
        out(f"  {len(t['sites'])} sites; "
            + " ".join(f"{k} {t['kinds'][k]}" for k in sorted(t["kinds"]))
            + "\n")
        out(f"  span 0x{lo:04X}-0x{hi:04X}; bands: {hist}\n")
        empty = [f"0x{b:02X}xx" for b in range(lo >> 8, (hi >> 8) + 1)
                 if b not in t["bands"]]
        if empty:
            out(f"  high bytes in that span with no site: {', '.join(empty)}\n")

    if t["computed"]:
        bases = sorted(t["computed"])
        out(f"  {sum(t['computed'].values())} computed sites, base(s) "
            f"{', '.join(bases)};\n"
            f"  the index is unbounded, so a base is not a range and an empty\n"
            f"  band above says nothing about one.\n")

    hit = [r for r in t["sites"]
           if r["addr"] and in_band(int(r["addr"], 16), band)]
    out(f"\n  answer for 0x{band[0]:04X}-0x{band[1]:04X}: {len(hit)} site(s) "
        f"in the census, {len(t['callers_resolved'])} parameterised caller(s) "
        f"resolved.\n")
    for r in hit:
        out(f"    census  {r['file']}:{r['line']} {r['type']}.{r['method']} "
            f"{r['op']} {r['addr']}\n")

    if t["helpers"]:
        out("  parameterised helpers, and every caller this sweep resolved:\n")
        for h in t["helpers"]:
            calls = [c for c in t["callers"]
                     if c["helper"] == h["helper"] and c["type"] == h["type"]]
            scope = h["file"] or "tree-wide (public static)"
            out(f"    {h['type']}.{h['helper']}  -- {len(calls)} caller(s), "
                f"scoped to {scope}\n")
            for c in calls:
                got = c["addr"] or f"<{c['addr_kind']}: {c['addr_expr']}>"
                out(f"      {got:>18}  {c['file']}:{c['line']}\n")

    if t["ecspec"] is None:
        out("  ECSpec.cs: not found in this tree.\n")
    else:
        consts = t["ecspec"]
        named = sorted((n, v) for n, v in consts.items() if in_band(v, band))
        out(f"  ECSpec `const ushort`: {len(consts)} names, "
            f"0x{min(consts.values()):04X}-0x{max(consts.values()):04X}; "
            f"{len(named)} name an address in the band"
            + (" (" + ", ".join(f"{n} = 0x{v:04X}" for n, v in named) + ")"
               if named else "") + ".\n")

    if t["unresolved"]:
        out("  helper bodies the census cannot resolve, and where their "
            "callers are:\n")
        for r in t["unresolved"]:
            out(f"    {r['file']}:{r['line']} {r['type']}.{r['method']} "
                f"{r['op']} addr = {r['addr_expr']}\n")


def boundaries():
    """What the answer above does not cover, printed on every run."""
    out = sys.stdout.write
    out("\n== boundaries: what a zero above does not mean ==\n")
    out("  'No site in this band' is 'not found by this method'. It is not\n"
        "  'the service does not write there'.\n"
        "\n"
        "  * The two partial trees. v3.1.6.0 and v3.9.18.0 are anti-tamper\n"
        "    casualties (windows/antitamper/README.md): a method body that did\n"
        "    not decompile is a body that was not searched, and it is not a body\n"
        "    that does not write. A zero on the decrypted service and a zero on\n"
        "    those two are different claims and are reported as different.\n"
        "  * A binary immediate. This is a text scan of decompiled C#. A\n"
        "    numeric immediate in native code is invisible to it, which is the\n"
        "    blind spot t1wr_callers.py's own header names for a string scan.\n"
        "    Nothing here searches windows/decompiled/native or vendor/.\n"
        "  * The EC firmware. Whether the EC itself reads or writes a byte in\n"
        "    the band is a question about the firmware image, asked of\n"
        "    ec/tools/scan_refs.py and not of this. A zero here is about the\n"
        "    Windows service alone.\n"
        "  * The unbounded computed index. A `(ushort)(base + i)` site is\n"
        "    reported as its base with the index range unproven.\n")


# The figures `docs/findings/ec-addr-reach-086x.md` quotes, asserted against
# the committed tree. A property, not a census of the repository: what is held
# is which high bytes resolve and that the level block's addresses resolve to
# nothing. A count of the tree would be a value every legitimate re-export has
# to edit, which is the trade CLAUDE.md records several times over.
EXPECTED = {
    "windows/decompiled/v3.1.39.0/GCUService": {
        # The three high bytes the census resolves to, and the span it covers.
        # 0x08 -- the level block -- is absent, and with it 0x05 and 0x06.
        "bands": {0x04, 0x07, 0x0F},
        "span": (0x0408, 0x0FE0),
        "unresolved": {"ReadECRAM", "WriteECRAM"},
    },
    "windows/decompiled/v3.1.6.0": {"bands": set(), "span": None,
                                     "unresolved": set()},
    "windows/decompiled/v3.9.18.0": {"bands": set(), "span": None,
                                     "unresolved": set()},
}

# The addresses `docs/hardware-tests/level-block-0860-086e.md` watches, as the
# decimal a C# `const ushort` would carry.
LEVEL_ADDRESSES = [0x085F, 0x0860, 0x086B, 0x086C, 0x086E]


def self_check(reach):
    """The claims the write-up makes, asserted against the committed tree."""
    drift = []
    for t in reach:
        want = EXPECTED[t["root"]]
        got = set(t["bands"])
        if got != want["bands"]:
            drift.append(f"{t['root']}: high bytes "
                         f"{sorted(hex(b) for b in got)}, expected "
                         f"{sorted(hex(b) for b in want['bands'])}")
        if t["span"] != want["span"]:
            drift.append(f"{t['root']}: span {t['span']}, expected "
                         f"{want['span']}")
        got_unres = {r["method"] for r in t["unresolved"]}
        if got_unres != want["unresolved"]:
            drift.append(f"{t['root']}: unresolved helper bodies "
                         f"{sorted(got_unres)}, expected "
                         f"{sorted(want['unresolved'])}")

    full = next(t for t in reach
                if t["root"] == "windows/decompiled/v3.1.39.0/GCUService")

    # The negative itself, and it is the whole point: none of the level block's
    # addresses resolves anywhere in the census or in the resolved callers.
    resolved = {int(r["addr"], 16) for r in full["sites"] if r["addr"]}
    resolved |= {int(c["addr"], 16) for c in full["callers_resolved"]}
    for a in LEVEL_ADDRESSES:
        if a in resolved:
            drift.append(f"0x{a:04X} resolves in the census; the write-up's "
                         f"negative no longer holds")

    # ...and the parameterised path really is swept, rather than read off the
    # two unresolved rows the census already had. A tool that resolved nothing
    # and a tool that resolved everything outside the band look the same from
    # outside unless the caller set is non-empty and lands elsewhere.
    if not full["callers_resolved"]:
        drift.append(f"{full['root']}: no parameterised caller resolved, so "
                     f"the negative is untested")
    for c in full["callers_resolved"]:
        if in_band(int(c["addr"], 16), LEVEL_BLOCK):
            drift.append(f"a parameterised caller resolves into the band: "
                         f"{c['file']}:{c['line']} -> {c['addr']}")

    # The look-alike the scoping excludes: `MyRgbLightBarDefault.WriteECRAM`
    # takes lightbar levels, not an address, and a name-based sweep would read
    # its four call sites as parameterised EC addresses. If one of them ever
    # grows an EC address as its first argument the scoping has to change, and
    # the census is where that would show up first.
    for c in full["callers"]:
        if "LightBar" in c["file"]:
            drift.append(f"{c['file']}:{c['line']} reached the parameterised "
                         f"caller sweep; the helper set is name-scoped again")

    # The `ECSpec` line of evidence, held so a future dump that does name an
    # address in the band turns this red instead of passing vacuously.
    for t in reach:
        if t["ecspec"] is None:
            drift.append(f"{t['root']}: ECSpec.cs not found, so the constant "
                         f"census did not run")
            continue
        named = sorted(n for n, v in t["ecspec"].items() if in_band(v, LEVEL_BLOCK))
        if named:
            drift.append(f"{t['root']}: ECSpec names {named} in the band")

    # The dead door, held as a fact rather than a count: `WMIEC`'s helpers have
    # no caller anywhere in the tree. If one is ever called, the write-up's "a
    # dead door, not a blind spot" sentence is wrong and this says so.
    live = sorted({c["type"] for c in full["callers"] if c["helper"].startswith("WMI")})
    if live:
        drift.append(f"WMIEC parameterised helpers now have callers: {live}")

    if drift:
        print("ec_addr_reach: the reach has drifted from the committed tree",
              file=sys.stderr)
        for d in drift:
            print("  " + d, file=sys.stderr)
        print("\nIf a committed input genuinely changed, re-run the reach, "
              "re-bake EXPECTED here, and write the new figure up in a file "
              "under docs/findings/ -- docs/findings.md is frozen.",
              file=sys.stderr)
        return 1
    print("ec_addr_reach: the reach matches the committed tree -- the level "
          f"block's {len(LEVEL_ADDRESSES)} addresses resolve nowhere in the "
          "census or in the resolved callers, the high bytes that do resolve "
          "are "
          + "/".join(f"0x{b:02X}" for b in sorted(EXPECTED[full["root"]]["bands"]))
          + ", and no `const ushort` in any tree's ECSpec names one")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", help="only this tree root (default: all three)")
    ap.add_argument("--addr", help="only sites at this EC address (hex or decimal)")
    ap.add_argument("--band", help="only this high-byte band, e.g. 0x08")
    ap.add_argument("--self-check", action="store_true",
                    help="assert the figures the findings write-up quotes")
    args = ap.parse_args(argv)

    band = LEVEL_BLOCK
    if args.band:
        b = int(args.band, 0)
        band = (b << 8, (b << 8) + 0xFF)

    roots = [p for _name, p in TREES if not args.tree or args.tree == p]
    if not roots:
        print(f"ec_addr_reach: no tree matches {args.tree!r}; the committed "
              f"roots are {', '.join(p for _n, p in TREES)}", file=sys.stderr)
        return 2
    reach = [tree_reach(root) for root in roots]

    if args.self_check:
        return self_check(reach)

    if args.addr:
        want = int(args.addr, 0)
        n = 0
        for t in reach:
            for r in t["sites"]:
                if r["addr"] and int(r["addr"], 16) == want:
                    print(f"{t['root']}  {r['file']}:{r['line']} "
                          f"{r['type']}.{r['method']} {r['op']} {r['addr']}")
                    n += 1
            for c in t["callers_resolved"]:
                if int(c["addr"], 16) == want:
                    print(f"{t['root']}  {c['file']}:{c['line']} {c['type']}."
                          f"{c['helper']}(...) {c['addr']}")
                    n += 1
        print(f"# {n} site(s) at 0x{want:04X}", file=sys.stderr)
        return 0

    for t in reach:
        report(t, band)
    boundaries()
    return 0


if __name__ == "__main__":
    sys.exit(main())