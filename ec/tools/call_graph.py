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

**The width rule does not stop a 4-digit data address, so a frame gates the
citation.** The same token is a function entry and an XDATA byte -- 0x07D0 is
`FUN_CODE_07d0` here and `DBD1` in `registers.yaml` -- so `citations()` asks
`citation_frames.classify()` whether a code frame governs the mention. The test
is a bounded window, not the sentence and not the comment, because a data veto
over the whole sentence would reject a genuine list: seven `bank1` comments
write "then calls to 0x110A, 0x158E, 0x0F75, 0x1594 and 0x00CF", and "to" is
a data marker. A code frame is necessary, a data frame is a veto, and what
neither settles is returned as `undecided`: the rejected and undecided
populations are reported, never dropped, because a guard that silently
discards what it rejects cannot be told apart from one that rejects too much.
A `pd` comment additionally cannot cite an EC row at all -- the two programs
have separate address spaces (`citation_frames.program_reason`) -- which is
decidable from program identity and not from prose. See
docs/findings/citation-code-vs-data.md.

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
import contextlib
import csv
import glob
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import citation_frames

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
    """`(kept, rejected, undecided)` for the anonymous callees comments name.

    `kept` maps a callee key to its citing comments, and is a count of
    *comments*, not of mentions: a comment naming the same callee twice is one
    comment, because the work list is "which comments have to stop writing a
    bare address", and one comment rewritten settles one dependency however
    many times it says so. A pair is kept when no mention carries a data frame
    or a program veto and at least one carries a code frame, so a comment that
    calls an address once and stores to it once is one *rejection*, not one
    call citation: a data frame vetoes the pair whatever a code frame says.

    `rejected` and `undecided` are the guard's own audit trail, per
    `citation_frames.Candidate`. They are returned rather than dropped for the
    reason `audit_call_targets.py` reports both framings for the same one: a
    guard that silently discards what it rejects cannot be told apart from a
    guard that rejects too much. The program-identity veto outranks the frame
    verdict because it is not a reading of the prose at all -- a `pd` comment
    and a `common` row are different programs, whatever the sentence says.
    """
    with open(rows, newline="") as f:
        ann = list(csv.DictReader(f, strict=True))
    verdicts = collections.defaultdict(set)
    data_reasons = collections.defaultdict(list)
    program_reasons = collections.defaultdict(list)
    citer_name = {}
    for r in ann:
        comment = r.get("comment") or ""
        scope, addr = r["scope"], norm_addr(r["addr"])
        if not comment:
            continue
        citer_name[(scope, addr)] = r["name"]
        for m in HEXREF.finditer(comment):
            digits = m.group("d")
            # Canonical width, and only then. See the module docstring: this
            # is what keeps "subtracts 0x64 (100)" off the 0x0064 row.
            if digits.upper() != "%04X" % int(digits, 16):
                continue
            row = index.resolve(scope, digits.upper())
            if row is None or not row["name"].startswith("FUN_"):
                continue
            key = (row["program"], row["_addr"])
            pair = (key, (scope, addr))
            frame = citation_frames.classify(comment, m)
            verdicts[pair].add(frame.verdict)
            if frame.verdict == citation_frames.DATA:
                if frame.reason not in data_reasons[pair]:
                    data_reasons[pair].append(frame.reason)
            program = citation_frames.program_reason(scope, row["program"])
            if program and program not in program_reasons[pair]:
                program_reasons[pair].append(program)
    kept = collections.defaultdict(list)
    rejected, undecided = [], []
    for pair, seen in verdicts.items():
        key, citer = pair
        # Both reasons are kept when both fire. The program veto decides on
        # its own, so recording only the frame reading would hide the pairs
        # the prose gets wrong: three of the 45 cross-program rejections read
        # as a code frame, and those three are what the veto is for. The count
        # is derived and printed by `report()`, because the figure written in
        # the prose drifted once already: "four" was how many of the 45 carry
        # no data reason at all, not how many read as a code frame.
        reasons = program_reasons[pair] + data_reasons[pair]
        if reasons:
            rejected.append(citation_frames.Candidate(key, citer,
                                                       tuple(reasons),
                                                       tuple(sorted(seen))))
        elif citation_frames.CODE in seen:
            kept[key].append((citer[0], citer[1], citer_name[citer]))
        else:
            undecided.append(citation_frames.Candidate(key, citer, (),
                                                        tuple(sorted(seen))))
    return kept, rejected, undecided


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
    """The lines describing a *row-level* difference between the committed
    table `have` and the recomputed `want`.

    Empty when every row parses equal, which is **not** the same as identical:
    the byte comparison is the pass condition and it lives in `check_table()`.
    This function renders a difference and never decides one.

    A function rather than an inline block in `main()` so `self_test()` can
    drive the *same* comparison the gate runs per commit. Asserting against a
    re-implementation of the diff would prove that the re-implementation
    works, which is not the question: the question is whether `--check` still
    rejects a table that has drifted, and a check that has quietly started
    accepting everything looks exactly like a check that is working.
    """
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


def check_table(have, want):
    """`(exit_code, lines)`: what `--check` returns, and the lines it prints
    on the way there. Byte equality is the pass condition, and it is the only
    one.

    It has to be the bytes rather than the parsed rows. A table whose rows
    read the same while its bytes do not is a table this tool did not write --
    CRLF line endings from a `core.autocrlf` checkout, a trailing blank line,
    reordered columns, redundant quoting -- and `.gitattributes` marks the
    decompiled `.c` trees `-text` for exactly that hazard but does not cover
    `ec/annotations/*.csv`, so the CRLF case is reachable rather than
    hypothetical. Gating the verdict on the rows would call such a table clean
    with the gate green, which is the exact quiet drift this check exists to
    close.

    `lines` is never empty when the code is 1, so a failure always says
    something: where every row parses equal, the line names the byte
    difference instead of leaving the reader with no output and an exit code
    to interpret.
    """
    if have == want:
        return 0, []
    lines = diff_table(have, want)
    if not lines:
        lines = ["  bytes differ and every row parses equal: line endings, a "
                 "trailing blank line, column order or quoting differ from "
                 "what this tool writes"]
    return 1, lines


def report(index, rows, edges, unresolved, orphan_callers, total,
           cited_rows, rejected, undecided):
    """Print the census, every figure twice-framed where a second framing
    exists, and the method's stated limits. These are the numbers
    ec/annotations/call-graph.md quotes, so a reader can re-derive them with
    this tool rather than trusting the prose."""
    anon_rows = [r for r in index.rows if r["name"].startswith("FUN_")]
    anon_edges = [r for r in rows if r["name"].startswith("FUN_")]
    cited = [r for r in anon_edges if r["cited_by"]]
    unreached = len(anon_rows) - len(anon_edges)
    c_callees = decompiled_callees()
    # Two different counts, and the gap between them is the point of the
    # block below. `cited_by` sums over the rows this table carries, so a
    # citation of a callee no transfer reaches is in neither; the frame gate
    # counts (callee, comment) pairs, which is the whole population the
    # matcher sees. 0x1C00 is the worked example: no lcall reaches it, so it
    # has no row to be right or wrong in, and its comments split across the
    # rejected and undecided buckets rather than falling out of the census
    # altogether.
    table_keys = {(r["scope"], r["addr"]) for r in rows}
    kept = sum(len(v) for v in cited_rows.values())
    unranked = sum(1 for c in rejected + undecided
                   if c.callee not in table_keys)
    unranked += sum(len(v) for k, v in cited_rows.items()
                    if k not in table_keys)
    candidates = kept + len(rejected) + len(undecided)
    # The three numbers the 0x1C00 sentence is made of, counted rather than
    # written out. All three were literals once and the sentence below was the
    # only one of them the census did not produce, so it drifted into claiming
    # "every one" in a data frame where the same run reports 18 rejected and 1
    # undecided. A limit sentence that contradicts the block above it is worse
    # than no limit sentence, so the counts come from the same lists the block
    # prints.
    c1c00 = ("common", "1C00")
    c1c00_rejected = sum(1 for c in rejected if c.callee == c1c00)
    c1c00_undecided = sum(1 for c in undecided if c.callee == c1c00)
    c1c00_named = (c1c00_rejected + c1c00_undecided
                   + len(cited_rows.get(c1c00, ())))
    # The program-identity sentence's number, counted rather than written out,
    # for the reason the three above are. It cannot be read off `reasons`: a
    # `cross-program` pair that also lists a data marker may still have had a
    # mention the frame test called `code`, so the frame verdict has to travel
    # with the candidate. Stated as a literal this figure drifted into the
    # neighbouring statistic -- "four of the 45" is how many of them carry no
    # data reason at all, not how many read as a code frame.
    cross_program = [c for c in rejected
                     if "cross-program" in c.reasons]
    cross_program_code = [c for c in cross_program
                          if citation_frames.CODE in c.verdicts]
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
    print("  frame gate (citation_frames.py), the same comments:")
    print("  %-52s %6d" % ("  candidate (callee, comment) pairs", candidates))
    print("  %-52s %6d" % ("  kept: a code frame governs the mention", kept))
    print("  %-52s %6d" % ("  rejected: a data frame, or another program",
                           len(rejected)))
    print("  %-52s %6d" % ("  undecided: no frame inside the window",
                           len(undecided)))
    print("  %-52s %6d" % ("  of those, naming a callee no transfer reaches",
                           unranked))
    print("  %-52s %6d" % ("  cross-program rejections", len(cross_program)))
    print("  %-52s %6d" % ("    of those, a mention reads as a code frame",
                           len(cross_program_code)))
    for reason, n in citation_frames.reason_counts(rejected).most_common(5):
        print("  %-52s %6d" % ("    rejected on " + reason, n))
    print("  rejected set, largest callee first (citation_frames.rejected_rows"
          " renders all):")
    for line in citation_frames.rejected_rows(rejected, limit=10):
        print(line)
    print("  undecided set, largest callee first; every one has a recorded"
          " reading in")
    print("  docs/findings/citation-undecided-verdicts.md, and the tool still"
          " reports the")
    print("  pair here -- a recorded reading does not reclassify it:")
    for line in citation_frames.rejected_rows(undecided, limit=10):
        print(line)
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
    print("  limit: %d citation candidates name a callee this table carries "
          "no row" % unranked)
    print("  for, because no transfer reaches it, so the gate can count them "
          "but the")
    print("  table cannot rank them. 0x1C00 is the worked example: %d "
          "comments name it, %d" % (c1c00_named, c1c00_rejected))
    print("  in a data frame and %d unsettled. Not ranked is not absent."
          % c1c00_undecided)


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
    modelled on the real cases -- a paged-form-only callee, an `ljmp`-only
    callee, a call from a bank listing into the common area, and a comment
    whose code and data addresses are the same four hex digits.
    """
    index = load_index(os.path.join(FIXTURE, "index.csv"))
    edges, unresolved, orphans, total = scan(
        index, os.path.join(FIXTURE, "decompiled"))
    cited, rejected, undecided = citations(
        index, os.path.join(FIXTURE, "ghidra-functions.csv"))
    rows = build(index, edges, cited)
    by_key = {(r["scope"], r["addr"]): r for r in rows}
    rejected_keys = {(c.callee, c.citer) for c in rejected}
    undecided_keys = {(c.callee, c.citer) for c in undecided}
    ok = True

    def check(label, cond):
        nonlocal ok
        print("  %s  %s" % ("ok  " if cond else "FAIL", label))
        if not cond:
            ok = False

    print("call_graph.py --self-test (fixture: ec/tools/testdata/call-graph)")
    check("every transfer site in the fixture resolves (%d)" % total,
          total == 15 and not unresolved)
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
    check("the rendered table against itself passes, which is --check's "
          "passing case",
          check_table(rendered, rendered) == (0, []))
    crlf = rendered.replace("\n", "\r\n")
    crlf_rc, crlf_lines = check_table(crlf, rendered)
    check("a CRLF table is rejected on its bytes although every row parses "
          "equal -- the row diff alone finds nothing there, which is why "
          "the pass condition is the comparison -- and the report is not "
          "empty",
          crlf_rc == 1 and crlf_lines
          and diff_table(crlf, rendered) == [])
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
    # The frame gate. Each of these is a number that shrinks when the guard is
    # wrong in one direction, which is the failure the guard exists to stop.
    check("a code callee and a colliding XDATA byte in one sentence: 0x018C "
          "credits 0x07D0 and credits 0x0A5A nothing, though both are "
          "reachable anonymous rows in this same fixture",
          ("common", "07D0") in cited
          and ("common", "0A5A") not in cited
          and by_key[("common", "0A5A")]["inbound"] == 1
          and by_key[("common", "0A5A")]["cited_by"] == 0)
    check("the XDATA 0x0A56-0x0A5A run credits neither end, and the rejection "
          "is reported with the pattern that made it rather than dropped",
          (("common", "0A5A"), ("common", "018C")) in rejected_keys
          and any("data-marker" in r
                  for c in rejected
                  if (c.callee, c.citer) == (("common", "0A5A"),
                                            ("common", "018C"))
                  for r in c.reasons))
    check("a data-marked word inside a code list does not veto it: 0x0070's "
          "'calls to 0x110A, 0x158E, 0x0F75, 0x1594 and 0x00CF' credits all "
          "four anonymous addresses, and the named 0x00CF is not a candidate "
          "at all",
          all(("common", a) in cited and
              by_key[("common", a)]["cited_by"] == 1
              for a in ("110A", "158E", "0F75", "1594"))
          and ("common", "00CF") not in cited)
    check("0x07D0 lands on the count its own listings support: two comments "
          "say 'calls 0x07D0' and two listings carry the lcall, so cited_by "
          "and inbound agree at 2",
          by_key[("common", "07D0")]["cited_by"] == 2
          and by_key[("common", "07D0")]["inbound"] == 2)
    check("a pd comment cannot cite an EC row whatever the prose says: the "
          "0x07D0 in 0x10BC's comment is this program's own byte",
          (("common", "07D0"), ("pd", "10BC")) in rejected_keys
          and any("cross-program" in c.reasons
                  for c in rejected
                  if (c.callee, c.citer) == (("common", "07D0"),
                                            ("pd", "10BC")))
          and by_key[("common", "07D0")]["citing"]
          == "common:018C common:029B")
    check("a mention with no frame in the window is undecided, not credited "
          "and not counted as rejected: 0x029B's 'the shared helper here is "
          "0x5A43'",
          (("common", "5A43"), ("common", "029B")) in undecided_keys
          and by_key[("common", "5A43")]["cited_by"] == 0)
    # The program-identity sentence's figure is derived from these verdicts,
    # so they are pinned here. The fixture's single cross-program rejection is
    # the mixed case: its mentions read code, data and undecided, and the
    # program veto is the only thing rejecting it. Lose the population and the
    # report's count falls to 0 while the prose keeps claiming otherwise,
    # which is the drift this field exists to prevent.
    check("a rejected candidate carries the frame verdicts its mentions drew, "
          "so the code-frame count is derived rather than written out: the "
          "fixture's one pd citation reads as a code frame",
          all(c.verdicts for c in rejected + undecided)
          and sum(1 for c in rejected
                  if "cross-program" in c.reasons
                  and citation_frames.CODE in c.verdicts) == 1)
    check("kept, rejected and undecided partition the candidate pairs, so no "
          "comment is both credited and reported against",
          len(cited) and rejected and undecided
          and not ({(k, c) for k, v in cited.items() for c in
                    ((s, a) for s, a, _ in v)} & rejected_keys)
          and not ({(k, c) for k, v in cited.items() for c in
                    ((s, a) for s, a, _ in v)} & undecided_keys))
    # The `sjmp` case, and the reason it is one. TRANSFERS scans the four
    # absolute forms and the comment lexicon is a different set, so a target
    # reached only by a PC-relative branch is a citation the graph cannot
    # rank. Both halves are asserted, because a guard that credited it
    # *and* a graph that gave it an edge would agree on the number while
    # disagreeing about what produced it.
    check("an `sjmp` in the comment lexicon credits a target whose only "
          "transfer is a PC-relative branch TRANSFERS does not scan: 0x0D40 "
          "is cited and still has no inbound edge",
          ("common", "0D40") in cited
          and ("common", "0D40") not in by_key)
    # The undecided block. This population is the one a human is handed, and
    # it is rendered the way the rejected one is; an undecided candidate
    # carries no reason, so each line falls back to the frame verdicts its
    # mentions drew rather than ending in a bare `--`.
    report_out = io.StringIO()
    with contextlib.redirect_stdout(report_out):
        report(index, rows, edges, unresolved, orphans, total,
               cited, rejected, undecided)
    report_lines = report_out.getvalue().splitlines()
    block_at = next((i for i, line in enumerate(report_lines)
                     if line.startswith("  undecided set,")), None)
    block = report_lines[block_at:] if block_at is not None else []
    rendered = [line for line in block if line.startswith("  common,5A43 ")]
    check("the undecided population is rendered, and a line carries the "
          "frame verdicts rather than a bare `--`: 0x5A43 cited by 0x029B",
          block_at is not None
          and len(rendered) == 1 and rendered[0].endswith("-- undecided"))
    check("the rendered undecided block names every undecided candidate, "
          "limit included: the fixture's is one",
          len([line for line in block
               if line.startswith("  ") and " cited by " in line]) == len(undecided))
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
    cited, rejected, undecided = citations(index)
    rows = build(index, edges, cited)
    text = render(rows)

    if args.check:
        if not os.path.exists(CALLEES):
            print("missing %s -- run call_graph.py to write it"
                  % os.path.relpath(CALLEES, REPO), file=sys.stderr)
            return 1
        with open(CALLEES, newline="") as f:
            have = f.read()
        rc, lines = check_table(have, text)
        if rc == 0:
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
    report(index, rows, edges, unresolved, orphans, total,
           cited, rejected, undecided)
    print()
    print("wrote %s (%d rows)"
          % (os.path.relpath(CALLEES, REPO), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
