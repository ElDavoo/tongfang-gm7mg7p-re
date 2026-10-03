#!/usr/bin/env python3
"""Compare two decompiled Control Center trees, and refuse when it would lie.

Issue #83 asks for the 2021 Control Center's `BatteryProtection2` behaviour and
its mode-to-register writes compared against the current 3.1.39.0. The
comparison is a text scan -- `ec_callsites.py`'s, over `ECSpec.cs`'s inlined
constants -- and on the two older committed trees that scan returns **nothing
at all**:

    $ python3 ec_callsites.py ../decompiled/v3.1.6.0/   --summary
    addr,addr_kind,reads,writes,writers          <- no rows
    $ python3 ec_callsites.py ../decompiled/v3.9.18.0/ --summary
    addr,addr_kind,reads,writes,writers          <- no rows

That is not a finding about those versions. It is what an anti-tamper casualty
looks like to a text scanner: the method bodies on disk are ciphertext, so there
is no `EcCtrl.Write` text to find. Print a diff between those two trees and the
reader takes "the older version wrote no register" away from it, which is
`docs/findings.md` §4c exactly -- a scan that found nothing written up as
nothing there. So **this tool refuses** when either input carries a decompiler
marker, names the count and the files, and exits non-zero.

The refusal is the deliverable for the Control Center half of #83 until someone
runs `dotnet_dump.py` (Windows, a live process) over a 2021-era build and
commits the decrypted tree. `../decompiled/v3.1.6.0/README.md` carries that
procedure; it is a human step and nothing here claims a result from it.

**A marker is a body the decompiler could not read.** `DECOMPILER_MARKERS` is
imported from `t1wr_callers.py` rather than restated, so "what counts as a
casualty" has one answer in this repository and not two that can drift. The
count is taken over the whole tree and reported per file, because the
consequence is not uniform: a marker in a localisation resource class costs
nothing, and a marker in `BatteryProtection2.cs` costs the whole comparison. The
refusal does not grade that -- it refuses on any, because "this tree is
partly unreadable" is not a state in which a zero means anything.

**What a clean diff reports**, for two trees that are both fully decompiled:
- the per-address read/write counts, with each address that differs shown with
  both sides' numbers rather than only the ones that went missing;
- the `BatteryProtection2` method set on each side, so a method that exists and
  is never called in one version shows up as a name rather than as silence.

A `0` in the output means "no direct reference found by this scan in this tree".
Indirect addressing is invisible to it, exactly as it is to `scan_refs.py`.

Usage:
    cc_version_diff.py ../decompiled/v3.1.6.0 ../decompiled/v3.1.39.0/GCUService
    cc_version_diff.py OLD NEW --addr 0x07A6
    cc_version_diff.py --self-test
"""
import argparse
import csv
import io
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import ec_callsites  # noqa: E402  (needs the sys.path entry above)
from t1wr_callers import DECOMPILER_MARKERS  # noqa: E402

# The class issue #83 names. Matched by name because it is the unit the
# question is asked in, and a class that moved namespace between versions is
# still the class.
CHARGE_CLASS = "BatteryProtection2"

CAVEAT = (
    "Counts are direct EcCtrl.Read/Write sites with a literal address, from a\n"
    "text scan of the decompiled tree. A site whose address is computed is\n"
    "listed as 'computed', and an access made through a pointer is invisible to\n"
    "this scan entirely. A zero means 'not found by this method', never\n"
    "'the version does not touch it' -- the same caveat ec_callsites.py and\n"
    "ec/tools/scan_refs.py carry.\n"
)

METHOD = re.compile(
    r"^\s*(?:(?:public|private|internal|protected|static|async|override|virtual|"
    r"unsafe|extern|new|sealed)\s+)+[\w<>\[\],\.\s?]+?\s+(?P<name>[\w\.]+)\s*\(")


def check_tree(path: str) -> None:
    """Refuse a tree that is not there or holds no `.cs` file at all.

    Without this, a mistyped path is the exact failure this tool exists to
    prevent: `marker_census()` finds no markers in a directory that does not
    exist, `summary()` and `charge_methods()` both come back empty, and the
    run prints a clean exit-0 diff reporting every address and every method as
    one-sided -- the reader is handed "the older version wrote no register" by
    a typo. That is not a hypothetical here: issue #83's own workflow step is
    to *create* `windows/decompiled/v<version>/`, so a path that does not exist
    yet is the expected state before the first recovery, not a mistake.
    """
    if not os.path.isdir(path):
        raise SystemExit(
            f"cc_version_diff.py: {path} is not a directory.\n"
            f"  A tree that is not there scans as empty, and an empty tree "
            f"produces a diff\n  in which everything looks one-sided. Check "
            f"the path, or decrypt the tree first\n  (windows/tools/"
            f"dotnet_dump.py, on a Windows machine).")
    for _dirpath, _dirnames, filenames in os.walk(path):
        if any(f.endswith(".cs") for f in filenames):
            return
    raise SystemExit(
        f"cc_version_diff.py: {path} holds no .cs files.\n"
        f"  That is what an unextracted installer or a directory of binaries "
        f"looks like, and\n  it scans the same as a tree whose bodies are all "
        f"ciphertext: empty, and\n  therefore every register and every method "
        f"one-sided. Point at a decompiled tree.")


def marker_census(root: str):
    """(total, {relative .cs path: count}) over every file under `root`.

    Imported vocabulary, own walk: `t1wr_callers.py` has the same loop for its
    readability census, but it is a script whose `main` reads a fixed list of
    binaries, and importing its walk would couple this tool's half to the other
    half of that one. The markers themselves are not duplicated.
    """
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            if not name.endswith(".cs"):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            count = sum(text.count(m) for m in DECOMPILER_MARKERS)
            if count:
                files[os.path.relpath(path, root).replace(os.sep, "/")] = count
    return sum(files.values()), files


def summary(tree: str):
    """{addr: {"kind":…, "reads": n, "writes": n, "writers": [...]}}.

    `ec_callsites.py`'s own aggregation, taken through its `main()` so the two
    tools cannot drift on what a row means -- the summary format is the part
    other work reads, and re-deriving it here would be a second answer to the
    same question.
    """
    out = io.StringIO()
    with redirect_stdout(out):
        ec_callsites.main([tree, "--summary"])
    rows = {}
    for row in csv.DictReader(io.StringIO(out.getvalue())):
        rows[row["addr"]] = {
            "kind": row["addr_kind"],
            "reads": int(row["reads"]),
            "writes": int(row["writes"]),
            "writers": [w for w in row["writers"].split("; ") if w],
        }
    return rows


def charge_methods(tree: str):
    """{method name: True} for the charge class, over every file under `tree`.

    The class is found by name in the file's own `class`/`namespace` lines
    rather than by path, because 3.1.39.0 nests it under a per-namespace
    directory and 3.1.6.0 does not. Set-valued and untyped on purpose: the
    question is whether a method *exists* in a version, and a signature that
    changed between releases is not the finding.
    """
    found = {}
    for dirpath, dirnames, filenames in os.walk(tree):
        dirnames.sort()
        for name in sorted(filenames):
            if not name.endswith(".cs"):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8-sig", errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            if not any(re.search(rf"\b(?:class|struct)\s+{CHARGE_CLASS}\b", ln)
                       for ln in lines):
                continue
            for line in lines:
                if m := METHOD.match(line):
                    found[m.group("name").split(".")[-1]] = True
    return found


def refusal(left: str, right: str):
    """The message and the reason, or None when both trees are fully readable.

    Returns a tuple rather than printing, so `--self-test` can assert on the
    refusal instead of on its exit status alone -- a refusal that fires for the
    wrong reason is still a refusal, and only the text says which.
    """
    census = {}
    for label, root in (("old", left), ("new", right)):
        if root:
            census[label] = marker_census(root)
    damaged = {label: (total, files) for label, (total, files) in census.items()
               if total}
    if not damaged:
        return None

    lines = ["refusing to diff: the input trees carry decompiler markers"]
    lines.append("")
    lines.append("  These are method bodies ILSpy could not turn back into C#. On")
    lines.append("  the committed older trees the bodies are ciphertext (see")
    lines.append("  ../antitamper/README.md), so a text scan of one finds no EC")
    lines.append("  call sites at all. Diffing against that and reporting")
    lines.append("  \"this version wrote no register\" would be a statement about")
    lines.append("  the scanner, not about the version.")
    lines.append("")
    for label in ("old", "new"):
        total, files = damaged.get(label, (0, {}))
        root = left if label == "old" else right
        lines.append(f"  {label}: {root} -- {total} marker(s) in "
                     f"{len(files)} file(s)")
        for path, count in sorted(files.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"      {path:<60} {count}")
        if not total:
            lines.append("      (clean)")
    lines.append("")
    lines.append("  Decrypting the bodies needs windows/tools/dotnet_dump.py on a")
    lines.append("  Windows machine with that version installed -- a live process,")
    lines.append("  not a file. Nothing offline can answer this until then, and a")
    lines.append("  zero from a tree with markers in it is not an answer.")
    return "\n".join(lines), damaged


def diff(left: str, right: str, want_addr=None):
    """(text, exit status). The status is non-zero only for a refusal."""
    check_tree(left)
    check_tree(right)
    refusal_text = refusal(left, right)
    if refusal_text:
        return refusal_text[0], 2

    old_rows, new_rows = summary(left), summary(right)
    addrs = sorted(set(old_rows) | set(new_rows))
    if want_addr is not None:
        # Compared numerically, because the rows are zero-padded hex
        # ("0x07A6") and a caller reading the address off a capture or a
        # `0x%s` format string will not have padded it the same way.
        want_int = int(want_addr, 16)
        addrs = [a for a in addrs if _addr_int(a) == want_int]

    out = [f"old: {left}", f"new: {right}", "", CAVEAT]
    differing = 0
    out.append("EC register accesses, by address")
    out.append(f"{'addr':<8} {'kind':<9} {'old r/w':>10} {'new r/w':>10}"
               "  writers (new)")
    for addr in addrs:
        o, n = old_rows.get(addr), new_rows.get(addr)
        if want_addr is None and o == n:
            continue
        differing += 1
        out.append(f"{addr:<8} {(n or o)['kind']:<9} "
                   f"{_rw(o):>10} {_rw(n):>10}  {'; '.join((n or o)['writers'])}")
    if want_addr is None:
        out.append("")
        out.append(f"  {len(addrs)} address(es) in either tree, {differing} "
                   f"differing. An address in neither column of a diff row is")
        out.append("  'not found by this scan in that tree', not 'not touched'.")

    old_m, new_m = charge_methods(left), charge_methods(right)
    out += ["", f"{CHARGE_CLASS} methods"]
    if not old_m and not new_m:
        out.append("  (neither tree declares a class by that name -- a refactor "
                   "renamed it,")
        out.append("   or this is not the charge class. An empty method set is "
                   "not 'the version")
        out.append("   has no charge methods'.)")
    for name in sorted(set(old_m) | set(new_m)):
        mark = "  " if name in old_m and name in new_m else " *"
        out.append(f"  {mark} {name}")
    out += ["", "  * in one tree only. A method listed here exists in that "
                "version's source;",
            "    whether anything calls it is a separate question "
            "(docs/findings.md §4k)."]
    return "\n".join(out), 0


def _addr_int(addr: str):
    """The numeric value of a summary row's key, or None for an unresolved one.

    A row whose address the scan could not resolve is keyed by the expression
    that defeated it, so it has no number to compare against and simply drops
    out of an address-filtered run rather than being forced into one.
    """
    try:
        return int(addr, 16)
    except ValueError:
        return None


def _line_for(text: str, name: str):
    """The output line listing `name`, or None -- so a test can assert on the
    line rather than on a substring that a differently-indented one would
    still satisfy."""
    for line in text.splitlines():
        if line.strip().lstrip("* ") == name:
            return line
    return None


def _rw(row):
    return "-" if row is None else f"{row['reads']}/{row['writes']}"


def self_test(repo: str) -> int:
    """The refusal, the diff, and an oracle the tool did not write for itself.

    Both halves: a check that has quietly stopped rejecting anything looks
    exactly like a check that is working, and a diff that fires on every input
    would satisfy the first half alone.
    """
    bad = 0
    print("cc_version_diff.py --self-test")

    def expect(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}"
              + (f"  {detail}" if detail and not ok else ""))

    old_tree = f"{repo}/windows/decompiled/v3.1.6.0"
    new_tree = f"{repo}/windows/decompiled/v3.1.39.0/GCUService"

    # --- the refusal, on the committed trees, which is what a user gets -----
    text, status = diff(old_tree, new_tree)
    expect("the 3.1.6.0 tree is refused against the decrypted 3.1.39.0 tree",
           status != 0)
    expect("the refusal names the marker count", "27 marker(s)" in text,
           text.splitlines()[0] if text else "")
    expect("the refusal names the file the markers are in",
           "BatteryProtection2.cs" in text)
    expect("the refusal says the scan cannot answer, not that the version "
           "wrote nothing", "not an answer" in text)
    expect("a refused run prints no per-address table",
           "EC register accesses" not in text)

    # The census the refusal rests on, against `t1wr_callers.py`'s own count
    # for the same file. Two tools, one number.
    total, files = marker_census(old_tree)
    expect("the 3.1.6.0 tree's whole-tree marker count is 27",
           total == 27 and files.get("BatteryProtection2.cs") == 27,
           f"{total} in {files}")

    # The same tool on the same tree the other way round must refuse too: a
    # refusal that only fires for the left-hand argument is not a refusal.
    _, flipped = diff(new_tree, old_tree)
    expect("the refusal does not depend on which tree is the old one",
           flipped != 0)

    # --- an absent or unextracted tree ------------------------------------
    # The failure mode this guards is not hypothetical: issue #83's own next
    # step is to *create* `windows/decompiled/v<version>/`, so "that path does
    # not exist yet" is the expected state before the first recovery, and
    # without this the run reports every register and every method as one-sided
    # and exits zero.
    def refuses_tree(path):
        try:
            check_tree(path)
        except SystemExit:
            return True
        return False

    def _refuses(fn, *a):
        """Whether `fn` raises SystemExit -- the whole run, not just the check.

        The distinction matters: `check_tree()` firing while `diff()` never
        calls it would leave the bug in place, so the run itself is the thing
        asserted.
        """
        try:
            fn(*a)
        except SystemExit:
            return True
        return False

    expect("a tree that does not exist is refused rather than scanned as empty",
           refuses_tree(f"{repo}/windows/decompiled/v9.9.9.9"))
    expect("a path that is a file rather than a directory is refused the "
           "same way",
           refuses_tree(f"{repo}/windows/decompiled/v3.1.6.0/BatteryProtection2.cs"))
    expect("a directory holding no .cs file is refused the same way",
           refuses_tree(f"{repo}/vendor/control-center-3.9.18.0/ACPIDriver"))
    expect("a real tree is not refused",
           not refuses_tree(f"{repo}/windows/decompiled/v3.1.6.0"))
    expect("a missing tree is refused by the whole run, not only by the "
           "pre-flight",
           _refuses(diff, f"{repo}/windows/decompiled/v9.9.9.9", new_tree))

    # --- and it must not fire on a clean pair ------------------------------
    scratch = tempfile.TemporaryDirectory(prefix="cc_version_diff_")
    clean_a = _clean_tree(scratch.name, "A")
    clean_b = _clean_tree(scratch.name, "B")
    expect("two marker-free trees are not refused",
           refusal(clean_a, clean_b) is None)
    text, status = diff(clean_a, clean_b)
    expect("a clean pair produces a diff rather than a refusal",
           status == 0 and "EC register accesses" in text)

    # --- the diff actually distinguishes the two trees ---------------------
    text, _ = diff(clean_a, clean_b)
    expect("an address only one tree writes is shown as a difference",
           "0x07B9" in text)
    expect("an address both trees touch the same way is not listed",
           "0x07A6" not in text)
    expect("a method only one tree declares is marked",
           "  * SetBatteryChargingLimit_Up" in text)
    shared = _line_for(text, "SetHealthProtectionHigh")
    expect("a method both trees declare is listed without the one-sided mark",
           shared is not None and "*" not in shared, repr(shared))
    only_new = _line_for(text, "SetBatteryChargingLimit_Up")
    expect("the one-sided mark is a '*' on the method's own line",
           only_new is not None and "*" in only_new, repr(only_new))

    # --- the self-graded half is the point ---------------------------------
    expect("a tree whose markers were counted as zero still diffs, so the "
           "refusal is reading the census and not the file names",
           "BatteryProtection2.cs" not in text)

    print("data: the two synthetic trees differ by one write to 0x07B9 and")
    print("      one method, so a diff that reports neither is not diffing")
    scratch.cleanup()
    return 1 if bad else 0


def _clean_tree(scratch: str, tag: str) -> str:
    """A two-file decompiled tree under `tempfile`, with no markers in it.

    Built in a scratch directory rather than committed as a fixture: the two
    trees differ by a few lines, and `ec/tools/testdata/` carries a hand-written
    index (`check_testdata_index.py`) that a pair of twenty-line `.cs` files do
    not need a row in.

    The addresses are decimal literals rather than `ECSpec` const names because
    that is what ILSpy emits -- `ECSpec.cs`'s constants are C# `const`, so the
    compiler inlined them, which is the whole reason a text scan of the
    decompiled tree is complete for literal addresses (`ec_callsites.py`'s
    header). A fixture written with the symbolic name would resolve to no
    address at all and would test nothing.
    """
    root = os.path.join(scratch, f"v{tag}")
    os.makedirs(os.path.join(root, "GCUService.MySystem"))
    # 1958 is 0x07A6, the mode register §4h names; 1977 is 0x07B9, the
    # charge-limit register `SetBatteryChargingLimit_Up` writes.
    body = ("using MyECIO;\n\nnamespace GCUService.MySystem;\n\n"
            "internal class BatteryProtection2\n{\n"
            "\t\tprivate MyEcCtrl EcCtrl = MyEcCtrl.Instance;\n")
    body += ("\t\tpublic void SetHealthProtectionHigh()\n\t\t{\n"
             "\t\t\tEcCtrl.Write(GetType().Name, 1958, data);\n\t\t}\n"
             "\t\tpublic void SetHealthProtectionLow()\n\t\t{\n"
             "\t\t\tEcCtrl.Write(GetType().Name, 1958, data);\n\t\t}\n")
    if tag == "B":
        body += ("\t\tprivate void SetBatteryChargingLimit_Up(byte limit)\n"
                 "\t\t{\n"
                 "\t\t\tEcCtrl.Write(GetType().Name, 1977, limit);\n\t\t}\n")
    body += "}\n"
    path = os.path.join(root, "GCUService.MySystem", "BatteryProtection2.cs")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    with open(os.path.join(root, "ECSpec.cs"), "w", encoding="utf-8") as fh:
        fh.write("namespace GCUService.MyECIO\n{\n\tinternal class ECSpec\n"
                 "\t{\n\t\tpublic const ushort ADDR_BATTERY_PROTECTION = 1958;\n"
                 "\t}\n}\n")
    return root


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", nargs="?", help="the older decompiled tree")
    ap.add_argument("new", nargs="?", help="the newer decompiled tree")
    ap.add_argument("--addr", help="only this EC address (hex or decimal)")
    ap.add_argument("--self-test", action="store_true",
                    help="the refusal, the diff, and two synthetic trees")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test(os.path.abspath(
            os.path.join(HERE, os.pardir, os.pardir)))
    if not args.old or not args.new:
        ap.error("give two decompiled trees, or --self-test")

    want = args.addr
    if want is not None and not want.lower().startswith("0x"):
        want = hex(int(want))
    text, status = diff(args.old, args.new, want_addr=want)
    print(text)
    return status


if __name__ == "__main__":
    sys.exit(main())
