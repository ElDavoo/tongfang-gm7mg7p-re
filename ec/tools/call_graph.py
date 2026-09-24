#!/usr/bin/env python3
"""Build the EC call graph from the committed listings, and rank the
anonymous callees a named function's comment already depends on.

Issue #134 asks for a second pass over the *edges* rather than the leaves: a
named function whose comment has to say "calls 0x0EE8" is not explaining
itself until 0x0EE8 has a name. The work list is therefore not the anonymous
functions but the anonymous functions a comment already cites, and this tool
is what turns "the anonymous ones" into a ranked address list.

**Parse the `.asm` listings, not the `.c` files.** The `.c` export names its
callees (`FUN_CODE_05e8()`), so a name-based inbound count is zeroed by the
exact operation that creates it: annotate 0x05E8 and the two evidence frames
disagree about whether anything reaches it. The `.asm` listings in the same
tree spell the target as an address (`lcall 0x05e8`), which survives a rename.
A future agent re-deriving this graph will reach for `grep FUN_` first; that is
the mistake this paragraph exists to stop.

Two parsing traps, both of which fail *quietly* to undercount:

  1. The listings' byte columns are whitespace-separated but not fixed-width,
     and a 2-byte instruction pads the two absent slots with a bare `-`. A
     `[0-9a-f-]{2}`-style column regex matches nothing on those lines and drops
     every `ajmp`/`acall` site. Split on whitespace runs and read tokens by
     position; see `parse_listing()`.
  2. `lcall`, `ljmp`, `ajmp` and `acall` all reach a function. Matching only
     `lcall` misses tail-calls and dispatch: 0x5A43, third-most-called, is
     reached by 11 `ajmp` and zero `lcall`; 0x00CF by a single `ljmp`. A
     `lcall`-only scan reports all three as unreachable.

**Two framings of the same population, and never one.** The report's numbers
come from two independent readings that disagree and are both kept:

  * *anchored* -- transfer instructions decoded out of the committed `.asm`
    listings, resolved to an exported function. Lower bound: it cannot see a
    call the decompiler synthesises and a branch into straight-line code.
  * *decompiled* -- distinct `FUN_*` callees the `.c` files name. Larger,
    because the decompiler emits calls the listing does not carry directly.
    (Its blind spot is the mirror image: it is blind to a callee renamed in
    both frames at once, and to a paged form it renders inline.)

The `.asm`-derived count is what the ranking and `call-graph-callees.csv` are
built on, because only it survives the annotation pass that consumes the work
list. The gap between the two framings is a stated limit, not a discrepancy to
reconcile away; follow audit_call_targets.py, which reports both for the same
reason.

**Ordering is citation-first, and that is a correction to the issue.** Issue
#134 says the natural ordering is by inbound reference count. Inbound is right
about the top of the list and wrong about the function the issue is written
around: 0x0EE8 has 2 direct `lcall` sites (0x0EA2 and 0x0ECC) and ranks about
210th of 891 on the decompile-derived inbound count, but it is first on
*citations* -- exactly one named function's comment names it. Inbound count is
the ranking within a citation band. See ec/annotations/call-graph.md.

A citation is a named function's comment writing a callee's address in the
canonical `0x` + 4-uppercase-hex-digit form, which is how every function
address in the export is written. The width is the point, not a detail: a
comment's `0x64` is overwhelmingly a *data* value ("subtracts 0x64 (100) from
XDATA 0x0465"), and matching it numerically would credit 43 citations to the
1-byte function at 0x0064 that the comment never mentions. A comment writing a
short form (`0x5E8` for 0x05E8) is **not found by this method**; it is not
evidence the address is uncited.

**`also_in`, never a guessed bank.** A `common` function is exported once, so
which bank executed a given common call site is not in the listing: a
`common/0EA2.asm` and a `bank0/0EA2.asm` reading of the same bytes are
indistinguishable here. Such a target is reported with `also_in` as the index
records it and is never attributed to one bank.

**What this cannot do.** A transfer target with no row in the index is a branch
into straight-line code (Ghidra's function boundaries on this firmware cut
through it), not evidence of a missing function; those sites are counted and
reported as `unresolved` rather than dropped or guessed. A target that
resolves to more than one scope row is likewise left unresolved rather than
assigned to the caller's bank. 339 of the 814 `FUN_*` rows in the index have
no direct transfer reaching them at all -- reached by function pointer, by a
table, or not reached -- and that is a limit of this method, not a claim that
they are unreachable. Disassembly of the listing, not reachability, is what
their own annotation rows rest on.

Both counts move as rows are annotated, and the report prints the live pair;
the numbers here are the ones the committed tree gives, so re-run rather than
trust them if a tranche has landed since.

Usage:
    python3 ec/tools/call_graph.py                 # report, write the table
    python3 ec/tools/call_graph.py --check         # recompute, diff, fail
    python3 ec/tools/call_graph.py --self-test     # known answers, on a fixture
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
DECOMPILED = os.path.join(REPO, "ec", "decompiled")
INDEX = os.path.join(DECOMPILED, "index.csv")
ANNOTATIONS = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")
CALLEES = os.path.join(REPO, "ec", "annotations", "call-graph-callees.csv")

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "call-graph")

# All four reach a function. lcall/ljmp are the 3-byte absolute forms; ajmp/
# acall are the 2-byte paged forms, which is exactly why a fixed-width column
# regex drops them (see the module docstring).
TRANSFERS = ("lcall", "ljmp", "ajmp", "acall")

# A `0x`-prefixed hex run, not itself inside a longer hex run. The 1-4 digit
# bound is what makes `0x8E` in "0x8E/0x8F are TCON" a candidate at all; the
# canonical-width test in `citations()` is what rejects it.
HEXREF = re.compile(r"(?<![0-9A-Fa-f])0[xX](?P<d>[0-9A-Fa-f]{1,4})"
                    r"(?![0-9A-Fa-f])")

# The listing's own address column.
ADDRCOL = re.compile(r"[0-9A-Fa-f]{4}")

COLUMNS = ["scope", "addr", "name", "annotated", "also_in", "inbound",
           "lcall", "ljmp", "ajmp", "acall", "callers", "named_callers",
           "cited_by", "citing"]


def norm_addr(text):
    """`05E8`, `0x05e8`, `0X5E8` -> `05E8`. One spelling everywhere, because
    every comparison below is a string comparison and the listings are
    inconsistent about the prefix."""
    return text.strip().lstrip("0x").lstrip("0X").upper().zfill(4)


def parse_listing(path):
    """Yield `(site_addr, form, target_addr)` for every transfer in one `.asm`.

    The line is `<addr> <b0> <b1> <b2> <mnemonic> <operand>`, whitespace
    separated, where a 2-byte instruction's absent slots are the single
    character `-`. The byte region is a fixed 9 columns wide, so the mnemonic
    is always token 4 -- but a fixed-width *regex* over the columns is what
    fails here, because the `-` pads are one character, not two.
    """
    with open(path, errors="replace") as f:
        for line in f:
            if line.startswith(";"):
                continue
            parts = line.split()
            if len(parts) < 6 or not ADDRCOL.fullmatch(parts[0]):
                continue
            form = parts[4]
            if form not in TRANSFERS:
                continue
            operand = parts[5]
            if not operand.lower().startswith("0x"):
                continue
            try:
                target = norm_addr(operand[2:])
            except ValueError:
                continue
            if not ADDRCOL.fullmatch(target):
                continue
            yield norm_addr(parts[0]), form, target


class Index:
    """The committed function census, and the one rule that resolves a
    transfer target to a function.

    Resolution is two-step and never a guess. A `common` function is exported
    once because both bank programs carry it identically, so a `bank0` listing
    calling 0x05E8 reaches the `common` row: a `bank0`-scoped row there would
    be a scope rename, not a second function. Where an address carries rows in
    two bank scopes the caller's own scope wins, because a bank program can
    only reach its own copy; where nothing decides it, the target is left
    unresolved and counted.
    """

    def __init__(self, rows):
        self.rows = rows
        self.by_scope_addr = {}
        self.by_addr = collections.defaultdict(list)
        for r in rows:
            addr = norm_addr(r["addr"])
            r["_addr"] = addr
            self.by_scope_addr[(r["program"], addr)] = r
            self.by_addr[addr].append(r)

    def resolve(self, scope, addr):
        row = self.by_scope_addr.get((scope, addr))
        if row is not None:
            return row
        rows = self.by_addr.get(addr, ())
        if len(rows) == 1:
            return rows[0]
        return None


def load_index(path=INDEX):
    with open(path, newline="") as f:
        return Index(list(csv.DictReader(f, strict=True)))


def scan(index, decompiled=DECOMPILED):
    """Walk every committed listing and resolve every transfer.

    Returns `(edges, unresolved, orphan_callers, sites)`. `edges` maps a
    callee row to its inbound sites, each tagged with the *calling function*
    -- the listing's own stem, which is the function's entry address, so a
    function that calls the same callee from three places is one caller and
    not three. Keying on the instruction address instead would make every
    site its own caller and report a call count no reader could act on.

    `unresolved` counts transfer *targets* that resolved to no index row, and
    `orphan_callers` listings whose own stem is no index row. Both are counts
    of what this method did not place, reported rather than dropped.
    """
    edges = collections.defaultdict(list)
    unresolved = collections.Counter()
    orphan_callers = 0
    total = 0
    for path in sorted(glob.glob(os.path.join(decompiled, "*", "*.asm"))):
        scope = os.path.basename(os.path.dirname(path))
        caller = norm_addr(os.path.basename(path)[:-4])
        if (scope, caller) not in index.by_scope_addr:
            orphan_callers += 1
        for _site, form, target in parse_listing(path):
            total += 1
            row = index.resolve(scope, target)
            if row is None:
                unresolved[target] += 1
                continue
            edges[(row["program"], target)].append((scope, caller, form))
    return edges, unresolved, orphan_callers, total


def citations(index, rows=ANNOTATIONS):
    """`(callee_key, citing_key)` for every anonymous callee a named comment
    names, plus the count of comments, not of mentions.

    A comment naming the same callee twice is one comment, because the work
    list is "which comments have to stop writing a bare address", and one
    comment rewritten settles one dependency however many times it says so.
    """
    with open(rows, newline="") as f:
        ann = list(csv.DictReader(f, strict=True))
    out = collections.defaultdict(list)
    for r in ann:
        comment = r.get("comment") or ""
        scope, addr = r["scope"], norm_addr(r["addr"])
        if not comment:
            continue
        seen = set()
        for m in HEXREF.finditer(comment):
            digits = m.group("d")
            # Canonical width, and only then. See the module docstring: this
            # is what keeps "subtracts 0x64 (100)" off the 0x0064 row.
            if digits.upper() != "%04X" % int(digits, 16):
                continue
            row = index.resolve(scope, digits.upper())
            if row is None:
                continue
            key = (row["program"], row["_addr"])
            if not row["name"].startswith("FUN_") or key in seen:
                continue
            seen.add(key)
            out[key].append((scope, addr, r["name"]))
    return out


def is_named(index, key):
    """True when `(scope, addr)` is an index row that is no longer `FUN_*`.
    A row the index does not carry is not named and not anonymous either: it
    is unplaced, and counting it as named would credit a callee with callers
    this scan never established."""
    row = index.by_scope_addr.get(key)
    return row is not None and not row["name"].startswith("FUN_")


def build(index, edges, cited):
    """One row per callee in the graph, ordered the issue's work list is
    read in: most-cited first, inbound count breaking a citation band, then
    scope and address so the order is total and reproducible.

    Named callees are kept, not dropped. Annotating a tranche row renames it
    in `index.csv` and in the `.c` files, and a table that lists only
    anonymous callees would then lose the row that the annotation just
    completed -- so `--check` would fail on the very pull request that
    consumes it. A named row keeps its inbound count and loses only its
    citation count, and its `annotated=yes` is how a reader sees the tranche
    is done rather than how a row silently disappears.
    """
    rows = []
    for key, sites in edges.items():
        row = index.by_scope_addr[key]
        forms = collections.Counter(form for _, _, form in sites)
        callers = {(scope, caller) for scope, caller, _ in sites}
        citing = cited.get(key, [])
        rows.append({
            "scope": key[0],
            "addr": key[1],
            "name": row["name"],
            "annotated": "yes" if row.get("annotated") == "yes" else "no",
            "also_in": row.get("also_in", ""),
            "inbound": len(sites),
            "lcall": forms["lcall"],
            "ljmp": forms["ljmp"],
            "ajmp": forms["ajmp"],
            "acall": forms["acall"],
            "callers": len(callers),
            "named_callers": sum(1 for c in callers if is_named(index, c)),
            "cited_by": len(citing),
            "citing": " ".join(f"{s}:{a}" for s, a, _ in sorted(citing)),
        })
    rows.sort(key=lambda r: (-r["cited_by"], -r["inbound"], r["scope"],
                             r["addr"]))
    return rows


def render(rows):
    buf = []
    w = csv.DictWriter(_Sink(buf), fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return "".join(buf)


class _Sink:
    """csv needs a file-like; a list of lines is the committed byte-for-byte
    comparison `--check` wants, and a temp file is not worth it for 1,841
    rows."""

    def __init__(self, sink):
        self._sink = sink

    def write(self, text):
        self._sink.append(text)


def diff_table(have, want):
    """The lines `--check` prints when the committed table `have` differs
    from the recomputed `want`; empty when they are byte-identical.

    A function rather than an inline block in `main()` so `self_test()` can
    drive the *same* comparison the gate runs per commit. Asserting against a
    re-implementation of the diff would prove that the re-implementation
    works, which is not the question: the question is whether `--check` still
    rejects a table that has drifted, and a check that has quietly started
    accepting everything looks exactly like a check that is working.
    """
    if have == want:
        return []
    have_rows = list(csv.DictReader(have.splitlines()))
    want_rows = list(csv.DictReader(want.splitlines()))
    lines = []
    shown = 0
    for a, b in zip(have_rows, want_rows):
        if a != b:
            lines.append("  %s/%s:" % (a["scope"], a["addr"]))
            for k in COLUMNS:
                if a.get(k) != b.get(k):
                    lines.append("    %-14s committed %r, recomputed %r"
                                 % (k, a.get(k), b.get(k)))
            shown += 1
            if shown >= 20:
                lines.append("  ... more")
                break
    if len(have_rows) != len(want_rows):
        lines.append("  row count: committed %d, recomputed %d"
                     % (len(have_rows), len(want_rows)))
    return lines


def report(index, rows, edges, unresolved, orphan_callers, total):
    """Print the census, every figure twice-framed where a second framing
    exists, and the method's stated limits. These are the numbers
    ec/annotations/call-graph.md quotes, so a reader can re-derive them with
    this tool rather than trusting the prose."""
    anon_rows = [r for r in index.rows if r["name"].startswith("FUN_")]
    anon_edges = [r for r in rows if r["name"].startswith("FUN_")]
    cited = [r for r in anon_edges if r["cited_by"]]
    unreached = len(anon_rows) - len(anon_edges)
    c_callees = decompiled_callees()
    print("call_graph.py -- EC call graph, from ec/decompiled/*/*.asm")
    print()
    print("  %-52s %6s" % ("function rows in index.csv", len(index.rows)))
    print("  %-52s %6d" % ("  of those, still FUN_*", len(anon_rows)))
    print("  %-52s %6d" % ("transfer instructions found (all four forms)",
                           total))
    print("  %-52s %6d" % ("  resolving to an index row",
                           total - sum(unresolved.values())))
    print("  %-52s %6d" % ("distinct targets reaching a row", len(edges)))
    print("  %-52s %6d" % ("  sites whose target is no index row",
                           sum(unresolved.values())))
    print("  %-52s %6d" % ("  listings with no index row of their own",
                           orphan_callers))
    print()
    print("  %-52s %6d" % ("  targets still anonymous", len(anon_edges)))
    print("  %-52s %6d" % ("  inbound sites to those",
                           sum(r["inbound"] for r in anon_edges)))
    print("  %-52s %6d" % ("  anonymous rows no transfer reaches", unreached))
    print()
    print("  second framing, from the .c export:")
    print("  %-52s %6d" % ("  distinct FUN_* callees named in .c files",
                           c_callees))
    print()
    print("  citation framing, from annotations/ghidra-functions.csv:")
    print("  %-52s %6d" % ("  anonymous callees a comment names", len(cited)))
    print("  %-52s %6d" % ("  comments that name one",
                           sum(r["cited_by"] for r in cited)))
    print()
    print("  ranked  scope    addr    in  named  cited  name")
    for rank, r in zip(range(1, 13), cited[:12]):
        print("  %6d  %-7s %-6s %3d %6d %6d  %s"
              % (rank, r["scope"], r["addr"], r["inbound"],
                 r["named_callers"], r["cited_by"], r["name"]))
    print()
    print("  limit: %d anonymous rows have no direct transfer reaching them "
          "by this" % unreached)
    print("  method -- function pointer, dispatch table, or not reached. Not "
          "found by this")
    print("  method is not absent. The ranking is a work order, not evidence "
          "of what any")
    print("  function does.")


def decompiled_callees(decompiled=DECOMPILED):
    """Distinct `FUN_*` callees the `.c` files name. The second framing; see
    the module docstring. Read from the `.c` on purpose -- this count is the
    one that a rename would move, which is why it is reported and not ranked
    on."""
    found = set()
    for path in glob.glob(os.path.join(decompiled, "*", "*.c")):
        with open(path, errors="replace") as f:
            for m in re.finditer(r"\bFUN_[A-Za-z0-9_]*", f.read()):
                found.add(m.group(0))
    return len(found)


def self_test() -> int:
    """Known answers against ec/tools/testdata/call-graph/.

    The fixture is small enough to read, and every assertion in it exists
    because the corresponding failure is quiet: a graph that cannot see 0x5A43
    looks exactly like a graph with a smaller number in it. The fixture is
    modelled on the three real cases -- a paged-form-only callee, an
    `ljmp`-only callee, and a call from a bank listing into the common area.
    """
    index = load_index(os.path.join(FIXTURE, "index.csv"))
    edges, unresolved, orphans, total = scan(
        index, os.path.join(FIXTURE, "decompiled"))
    cited = citations(index, os.path.join(FIXTURE, "ghidra-functions.csv"))
    rows = build(index, edges, cited)
    by_key = {(r["scope"], r["addr"]): r for r in rows}
    ok = True

    def check(label, cond):
        nonlocal ok
        print("  %s  %s" % ("ok  " if cond else "FAIL", label))
        if not cond:
            ok = False

    print("call_graph.py --self-test (fixture: ec/tools/testdata/call-graph)")
    check("every transfer site in the fixture resolves (%d)" % total,
          total == 8 and not unresolved)
    check("the 2-byte ajmp is seen: 0x5A43 inbound=3 via ajmp only, "
          "lcall=0",
          by_key[("common", "5A43")]["inbound"] == 3
          and by_key[("common", "5A43")]["ajmp"] == 3
          and by_key[("common", "5A43")]["lcall"] == 0)
    check("an ljmp-only callee is seen: 0x00CF inbound=1 via ljmp",
          by_key[("common", "00CF")]["inbound"] == 1
          and by_key[("common", "00CF")]["ljmp"] == 1)
    check("a 3-byte lcall callee is seen: 0x05E8 inbound=2",
          by_key[("common", "05E8")]["inbound"] == 2
          and by_key[("common", "05E8")]["lcall"] == 2)
    check("a bank0 call into the common area resolves to the common row, "
          "with also_in and not a guessed bank",
          ("common", "05E8") in by_key
          and by_key[("common", "05E8")]["also_in"] == "bank1")
    check("a comment naming an address the listings do not carry is refused, "
          "not invented: 0xBEEF gets no citation",
          not any(k[1] == "BEEF" for k in cited))
    check("an index row no transfer reaches gets no inbound edge, and that "
          "is a limit of the scan rather than an absent function: 0xDEAD",
          ("common", "DEAD") not in by_key)
    check("a short-form data value is not a citation: the 0x64 in 0xEA2's "
          "comment credits neither 0x0064 nor anything else",
          ("common", "0064") not in cited
          and ("common", "0064") in index.by_scope_addr)
    check("a canonical citation is counted once per comment, not once per "
          "mention: 0x0EE8 cited_by == 1 though written twice",
          by_key[("common", "0EE8")]["cited_by"] == 1)
    check("the citing list names the citing row",
          by_key[("common", "0EE8")]["citing"] == "bank0:0EA2")
    check("ordering is citation-first, so 0x0EE8 (2 inbound, 1 cited) sorts "
          "above 0x5A43 (3 inbound, 0 cited)",
          [r["addr"] for r in rows].index("0EE8")
          < [r["addr"] for r in rows].index("5A43"))
    check("a named callee keeps its row and its inbound count, which is what "
          "keeps --check passing on the pull request that names it: 0x00CF",
          ("common", "00CF") in by_key
          and by_key[("common", "00CF")]["inbound"] == 1
          and by_key[("common", "00CF")]["annotated"] == "yes"
          and by_key[("common", "00CF")]["name"] == "table_walker_00cf")
    check("callers and named_callers differ because 0x5A43 is reached by two "
          "anonymous callers and one named",
          by_key[("common", "5A43")]["callers"] == 3
          and by_key[("common", "5A43")]["named_callers"] == 1)
    check("every emitted row carries a non-empty scope and a 4-digit addr",
          all(r["scope"] and ADDRCOL.fullmatch(r["addr"]) for r in rows))
    rendered = render(rows)
    check("the rendered table is a csv.DictReader fixed point, which is what "
          "--check relies on",
          render(list(csv.DictReader(rendered.splitlines()))) == rendered)
    check("the rendered table against itself is no diff, which is --check's "
          "passing case",
          diff_table(rendered, rendered) == [])
    edited = [dict(r) for r in rows]
    edited[0]["inbound"] = str(int(edited[0]["inbound"]) + 1)
    edited_lines = diff_table(render(edited), rendered)
    check("a table with one cell altered is rejected, naming that row and "
          "that column: %s/%s inbound"
          % (rows[0]["scope"], rows[0]["addr"]),
          any(line == "  %s/%s:" % (rows[0]["scope"], rows[0]["addr"])
              for line in edited_lines)
          and any("inbound" in line and "recomputed" in line
                  for line in edited_lines))
    check("a table with its last row dropped is rejected on the row count, "
          "a drift no cell-by-cell comparison can see",
          diff_table(render(rows[:-1]), rendered)
          == ["  row count: committed %d, recomputed %d"
              % (len(rows) - 1, len(rows))])
    check("no fixture listing is an orphan, so callers == named_callers is "
          "only false where a real anonymous caller makes it false",
          orphans == 0)
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="recompute the table and fail on any diff")
    mode.add_argument("--self-test", action="store_true",
                      help="known answers against the committed fixture")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    index = load_index()
    edges, unresolved, orphans, total = scan(index)
    rows = build(index, edges, citations(index))
    text = render(rows)

    if args.check:
        if not os.path.exists(CALLEES):
            print("missing %s -- run call_graph.py to write it"
                  % os.path.relpath(CALLEES, REPO), file=sys.stderr)
            return 1
        with open(CALLEES, newline="") as f:
            have = f.read()
        lines = diff_table(have, text)
        if not lines:
            print("call-graph-callees.csv: %d rows, no diff"
                  % len(rows))
            return 0
        for line in lines:
            print(line)
        print("call-graph-callees.csv differs from the committed listings; "
              "re-run without --check", file=sys.stderr)
        return 1

    with open(CALLEES, "w", newline="") as f:
        f.write(text)
    report(index, rows, edges, unresolved, orphans, total)
    print()
    print("wrote %s (%d rows)"
          % (os.path.relpath(CALLEES, REPO), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
