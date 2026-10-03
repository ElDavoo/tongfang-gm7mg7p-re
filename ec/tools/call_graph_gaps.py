#!/usr/bin/env python3
"""Give the two populations `call_graph.py`'s census reduces to an integer their
identity back: one `cause` per unresolved transfer target, one `entry` per
anonymous row no transfer reaches.

`scan()` keeps unresolved targets in a `Counter` and `report()` prints
`sum(unresolved.values())` beside the number of keys. The eighty keys are
emitted nowhere, so a single sentence in `ec/annotations/call-graph.md` was
carrying a per-target cause for all of them -- "those are branches into
straight-line code" -- on no measurement at all. That sentence is not false of
the rows it fits; it is false as a statement about all eighty. Four
populations sit inside them, and which one a target is in decides what a reader
should do about it.

So this is a classifier, not another census: it writes two committed CSVs, one
per population, and `--check` recomputes both and fails on any byte difference.
The classification is then something a reader can re-derive rather than a
sentence they have to believe.

**It imports the rule rather than re-implementing it.** `call_graph.Index` and
`call_graph.parse_listing` are what `scan()` resolves a transfer with and what
it reads the listing grammar with, and `citation_callers.iter_instructions` is
what reads a listing's last instruction. Three predicates here would be three
more places for "what counts as unresolved" to be decided, and the whole value
of this tool is that it is describing `scan()`'s population rather than a
near-neighbour of it. The suite asserts the totals agree with `scan()`'s own
`Counter` in one process for the same reason.

**`cause` is a closed vocabulary of four values, decided in this order.** Each
rule is a predicate over committed files, and the precedence is not
preference -- rule 1 is `Index.resolve()`'s own reason for declining, so a
target in that class is reported under the cause its resolver already gives it.

  1. `multi-scope` -- the address carries two or more `index.csv` rows and no
     reaching site's own scope is among them. `Index.resolve()` declines here,
     and `scan()` counts the site; this names the decline.
  2. `xdata-or-data` -- no index row at the address, and
     `registers.yaml` records it.
  3. `interior-entry` -- no index row, and the address lies strictly inside
     `[addr, addr+size)` of some *other* row, off the `size` column the index
     already carries. Strictly inside, because a row's own address is rule 1's
     subject and not an interior entry.
  4. `no-index-row` -- none of the above.

**Two of those four are weak negatives and are labelled as weak everywhere they
are named.** `xdata-or-data` is a lookup in `registers.yaml`, which carries a
few hundred XDATA addresses and not one code address: it finds a small
minority of the targets, and a target it does not name is **not found by this
method**, never "not XDATA" and never "code". `no-index-row` is what is left
once the three place a target, and it is **explicitly unclassified** -- it means
this method placed the target nowhere, which is not a statement about the
firmware. Neither value is ever a basis for saying a target has no function,
and the artifact says so in its own header comment as well.

**The host row is reported whether or not the cause that won used it.** An
address `xdata-or-data` also found lying inside a routine keeps that routine in
`host_*`, because rule 2 outranks rule 3 and a reader who cannot see the host
would read the precedence as the host not existing. For a `pd` transfer the
host is often a `common` row: the two programs have separate address spaces
(`citation_frames.program_reason`, and
`docs/findings/pd-common-address-spaces.md`), so the host is **not** looked up
under the reaching site's own scope. Narrowing the search to the reaching
program would drop a dozen real cross-program hosts and report those targets as
unplaced, which is the quiet direction.

**The paged-form signal is a column, not a fifth cause.** An `ajmp`/`acall` puts
the page in the opcode and only the low byte in the operand, so `0x5A43`,
`0x5A44` and `0x5A46` are three distinct entry points into one body. That is a
property of the *forms* that reach a target, not of why it failed to resolve, so
it is `forms` and the vocabulary stays four.

**`entry` is three values, and the third one is the reason it is not two.** The
question the unreached population turns on is whether an anonymous row is the
continuation of a neighbouring one. The rule answers it positionally -- the row
immediately after some index row's last instruction -- and then has to say
whether control *actually* falls through there. A returns-only test is the
obvious reading and it is wrong on most of the population: an `ljmp` is three
bytes of unconditional jump, and an address one past it is jumped over. So the
second question is asked against `NO_FALLTHROUGH` rather than against the
returns:

  * `fall-through` -- adjacent, and the predecessor's last instruction is not
    one control can be taken away from the next address by, so **control does
    continue into it**;
  * `adjacent-no-fallthrough` -- adjacent, and the predecessor's last
    instruction is one `NO_FALLTHROUGH` covers, so **this method credits it no
    fall-through**: the adjacency is a boundary, and `NO_FALLTHROUGH`'s own
    comment says which members are a boundary and which are a branch this tool
    does not trace;
  * `not-adjacent` -- neither, i.e. nothing this method read places it.

Two values would have had to call the second class a fall-through, which is the
overclaim `CLAUDE.md` puts above every other rule; and `not-adjacent` is not
"reached by a function pointer", which is a claim about the firmware this tool
does not make.

**No column is hand-maintained.** There is no `note` cell, which is the only
reason a prose note cannot escape `--check`; where a row's answer is argued
elsewhere, the artifact carries the re-derivable half and the argument lives in
`docs/findings/unresolved-transfer-causes.md`.

Usage:
    python3 ec/tools/call_graph_gaps.py            # report, write both tables
    python3 ec/tools/call_graph_gaps.py --check     # recompute, diff, fail
    python3 ec/tools/call_graph_gaps.py --self-test  # known answers, on a fixture
"""
import argparse
import collections
import contextlib
import csv
import glob
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_ec_decompile
import call_graph
import citation_callers

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
DECOMPILED = call_graph.DECOMPILED
ANNOTATIONS = os.path.join(REPO, "ec", "annotations")
UNRESOLVED = os.path.join(ANNOTATIONS, "call-graph-unresolved.csv")
UNREACHED = os.path.join(ANNOTATIONS, "call-graph-unreached.csv")

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "testdata", "call-graph-gaps")

norm_addr = citation_callers.norm_addr

# The header comment written above each committed table. CSV has no comment
# syntax, so it is a leading `#` line the reader sees and `csv.DictReader` never
# does -- which is why the recalibration caveat is here rather than only in the
# docstring: this file is what someone opens when they want to know what a value
# means, and "not found by this method" is the difference between a tool and an
# accusation.
HEADER_NOTE = [
    "# %(file)s -- generated by ec/tools/call_graph_gaps.py; do not edit by"
    " hand.",
    "# Re-derive with `python3 ec/tools/call_graph_gaps.py`, and gate a change",
    "# with `python3 ec/tools/call_graph_gaps.py --check`.",
    "#",
    "# `%(cause)s` is a WEAK NEGATIVE and is not a claim about the firmware: it",
    "# means this method did not place the row, not that the row has no",
    "# function and not that it is unreachable. `host_*` names the index row",
    "# the reading rests on where there is one, and is empty where there is",
    "# not. The argument for each row is in",
    "# docs/findings/unresolved-transfer-causes.md.",
]

UNRESOLVED_COLUMNS = ["target", "sites", "callers", "forms", "cause",
                      "host_scope", "host_addr", "host_name", "listings"]
UNREACHED_COLUMNS = ["scope", "addr", "name", "size", "entry",
                     "pred_scope", "pred_addr", "pred_name", "pred_named",
                     "listing"]

CAUSES = ("multi-scope", "xdata-or-data", "interior-entry", "no-index-row")
ENTRIES = ("fall-through", "adjacent-no-fallthrough", "not-adjacent")

# The one value in each table's vocabulary that means "this method placed it
# nowhere". Named per table because the header comment above each is written
# from it, and a caveat that named a value the table does not carry would be a
# second thing to keep in step.
WEAK_NEGATIVE = {
    "call-graph-unresolved.csv": "no-index-row",
    "call-graph-unreached.csv": "not-adjacent",
}

# The mnemonics after which this tool credits the next address with **no**
# fall-through. A returns-only rule is the obvious version of this predicate
# and it is wrong on most of the population: an `ljmp` is three bytes of
# unconditional jump, and the row one past it is jumped *over*, not fallen
# into. The set is read off the mnemonic rather than the byte column because
# this tool reads listings; the mnemonics it carries are the ones below.
#
# Two halves, and they are not the same claim about the bytes:
#
#   * `ret`/`reti` and the unconditional transfers -- `ljmp`, `ajmp`, `sjmp` and
#     the indirect `jmp @A+DPTR` -- are boundaries: control provably does not
#     continue into what follows.
#   * the conditional branches continue into what follows *when the branch is
#     not taken*. This tool reads listings rather than tracing, so it credits
#     nothing past one. That is the conservative direction and it is a
#     statement about what was measured, not about where the branch goes.
#
# `lcall`/`acall` are deliberately **out**, and that is the one decision here
# easy to get wrong the other way: a call returns to the instruction after it,
# so a row one past a call really is fallen into.
NO_FALLTHROUGH = frozenset((
    # boundaries: control provably does not continue into the next address
    "ret", "reti", "ljmp", "ajmp", "sjmp", "jmp",
    # conditional branches: credited nothing past, by the reading above
    "jb", "jbc", "jc", "jnb", "jnz", "jz", "jnc", "cjne", "djnz",
))


def unresolved_sites(index, decompiled=DECOMPILED):
    """`{target: [(scope, caller, site_addr, form)]}` for every transfer target
    `index.resolve()` declines.

    A second walk rather than a change to `scan()`, which is deliberately left
    alone: it keeps `call-graph-callees.csv` byte-identical and keeps the census
    `call-graph.md` quotes untouched, and this needs per-site detail that
    `scan()`'s `Counter` does not carry. The set of targets is `scan()`'s, by
    construction -- both ask `resolve()` the same question -- and the suite
    asserts the agreement in one process rather than trusting it.
    """
    sites = collections.defaultdict(list)
    for path in sorted(glob.glob(os.path.join(decompiled, "*", "*.asm"))):
        scope = os.path.basename(os.path.dirname(path))
        caller = norm_addr(os.path.basename(path)[:-4])
        for site, form, target in call_graph.parse_listing(path):
            if index.resolve(scope, target) is None:
                sites[target].append((scope, caller, site, form))
    return sites


def spans(index):
    """`[(start, size, row)]` for every index row carrying a usable size.

    The `size` column is the index's own, which is what makes an interior entry
    computable rather than a guess: no second span table is built here and none
    can drift from the index.
    """
    out = []
    for r in index.rows:
        try:
            size = int(r["size"])
        except (TypeError, ValueError):
            continue
        if size > 0:
            out.append((int(r["_addr"], 16), size, r))
    return out


def hosts(addr, spans_):
    """Every index row whose `[start, start+size)` strictly contains `addr`.

    Strictly, so a row's own address is not its own interior. Sorted so the
    artifact is a function of the tree rather than of `index.csv`'s row order,
    which a re-export is free to change.
    """
    value = int(addr, 16)
    found = [(start, r) for start, size, r in spans_
             if start < value < start + size]
    return [r for _, r in sorted(found, key=lambda p: (p[0], p[1]["program"]))]


def all_causes(addr, site_scopes, at_addr, contained, xdata):
    """Every cause that fires for one unresolved target, in precedence order.

    The whole of the classification, in one place and in one pass, because a
    second copy of these four predicates is a second answer to the same
    question: `classify()` below takes this list's head rather than
    re-deciding, so the artifact's value and the overlap the tool prints cannot
    disagree.

    Each rule is a predicate over what is already in hand -- the rows at the
    address, the scopes its reaching sites are in, the rows that contain it, and
    the `registers.yaml` set -- so no rule can be talking about a different
    target than the others.

    The overlap count is what makes the precedence visible: a precedence that
    quietly decides a target is a rule no reader can see, so the tool prints how
    many it decided.
    """
    fired = []
    if len(at_addr) >= 2 and not ({r["program"] for r in at_addr} & site_scopes):
        fired.append("multi-scope")
    if not at_addr and int(addr, 16) in xdata:
        fired.append("xdata-or-data")
    if not at_addr and contained:
        fired.append("interior-entry")
    if not fired:
        # The residual, and named for what it is: this method placed the target
        # nowhere. A fourth rule that fired would be a claim about the firmware
        # the three above do not support.
        fired.append("no-index-row")
    return fired


def classify(addr, site_scopes, at_addr, contained, xdata):
    """The `cause` for one unresolved target: the head of `all_causes()`.

    A function rather than an inline `all_causes(...)[0]` because the suite
    asserts the artifact's value is this list's first element, and an assertion
    against an inline index would only be checking that `[0]` returns index 0.
    """
    return all_causes(addr, site_scopes, at_addr, contained, xdata)[0]


def unresolved_rows(index, sites, xdata):
    """One row per unresolved target, ordered by address.

    `host_*` is filled from whichever rows exist -- the rows *at* the address
    when it has any, otherwise the rows containing it -- and not from the host
    of the winning cause. That is deliberate: rule 2 outranks rule 3, and a
    `xdata-or-data` target that also sits inside a routine would otherwise lose
    the only pointer to it that a reader has.
    """
    spans_ = spans(index)
    rows = []
    for addr in sorted(sites):
        at_addr = list(index.by_addr.get(addr, ()))
        contained = hosts(addr, spans_)
        row_hosts = at_addr or contained
        scope_scopes = {s[0] for s in sites[addr]}
        forms = sorted({form for _, _, _, form in sites[addr]})
        rows.append({
            "target": addr,
            "sites": len(sites[addr]),
            "callers": len({(s, c) for s, c, _, _ in sites[addr]}),
            "forms": " ".join(forms),
            "cause": classify(addr, scope_scopes, at_addr, contained, xdata),
            "host_scope": " ".join(r["program"] for r in row_hosts),
            "host_addr": " ".join(r["addr"] for r in row_hosts),
            "host_name": " ".join(r["name"] for r in row_hosts),
            "listings": " ".join(sorted("%s/%s@%s" % (s, c, site)
                                        for s, c, site, _ in sites[addr])),
        })
    return rows


def unreached_rows(index, edges, decompiled=DECOMPILED):
    """One row per anonymous index row no transfer reaches, with how it is
    entered if this method can say.

    The population is exactly `report()`'s: `len(anon_rows)` less the anonymous
    rows the table carries an inbound edge for. That is a different set from
    "anonymous rows the table carries no row for" -- a cited row the scan cannot
    reach is in the table now and is still a row no transfer reaches -- so the
    two are counted separately and this tool uses the one it is about.

    `edges`' keys *are* the reached set, so the subtraction below is the same
    one `scan()` reported rather than a second reachability rule.
    """
    anon = [r for r in index.rows if r["name"].startswith("FUN_")]
    keys = {(r["program"], r["_addr"]) for r in anon} - set(edges)
    # The predecessor map, built once over every index row rather than per
    # unreached row: the question "which row's last instruction lands here" is
    # asked of the whole index, and a row nobody transfers to is exactly the row
    # most likely to be somebody's continuation.
    pred = {}
    for r in index.rows:
        path = os.path.join(decompiled, r["program"], r["addr"] + ".asm")
        if not os.path.exists(path):
            continue
        last = None
        for parts in citation_callers.iter_instructions(path):
            last = parts
        if last is None:
            continue
        # The instruction's own length is the count of byte tokens it carries:
        # the listings pad a short instruction's absent slots with a bare `-`,
        # which is the same trap `call_graph.parse_listing()` documents and why
        # the length is counted rather than read off a column width.
        length = sum(1 for t in last[1:4] if t != "-")
        nxt = "%04X" % ((int(last[0], 16) + length) & 0xFFFF)
        pred.setdefault((r["program"], nxt), []).append(
            (r, last[4] in NO_FALLTHROUGH))
    rows = []
    for scope, addr in sorted(keys):
        row = index.by_scope_addr[(scope, addr)]
        found = pred.get((scope, addr), [])
        if not found:
            entry, chosen = "not-adjacent", None
        else:
            # Deterministic when two rows end on the same address: the one the
            # index sorts first, so the artifact does not depend on `index.csv`
            # row order.
            r, no_fallthrough = sorted(found, key=lambda p: (p[0]["_addr"],
                                                              p[0]["program"]))[0]
            entry = ("adjacent-no-fallthrough" if no_fallthrough
                     else "fall-through")
            chosen = r
        rows.append({
            "scope": scope,
            "addr": addr,
            "name": row["name"],
            "size": row["size"],
            "entry": entry,
            "pred_scope": chosen["program"] if chosen else "",
            "pred_addr": chosen["addr"] if chosen else "",
            "pred_name": chosen["name"] if chosen else "",
            "pred_named": ("yes" if chosen and not
                           chosen["name"].startswith("FUN_") else
                           ("no" if chosen else "")),
            "listing": "%s/%s.asm" % (scope, addr),
        })
    return rows


def render(rows, columns, note):
    """The committed bytes for one table.

    A leading `#` comment block over a `csv.DictWriter`, on the reasoning that
    the calibration caveat belongs in the file a reader opens. `DictReader`
    treats those lines as a header row, so `read_rows()` drops them; the
    pass condition is the byte comparison either way.
    """
    buf = []
    # One value per table: the file's own name, and the vocabulary member that
    # table's caveat is about. `no-index-row` and `not-adjacent` are the two
    # weak negatives, one per table, and naming the wrong one in a header would
    # be a second thing to keep in step.
    name = columns_file(columns)
    for line in note:
        buf.append(line % {"file": name,
                           "cause": WEAK_NEGATIVE[name]} + "\n")
    w = csv.DictWriter(call_graph._Sink(buf), fieldnames=columns,
                       lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return "".join(buf)


def columns_file(columns):
    """Which committed file a column set belongs to, for the header note."""
    return ("call-graph-unresolved.csv" if columns is UNRESOLVED_COLUMNS
            else "call-graph-unreached.csv")


def read_rows(text):
    """The rows of a committed table, past the `#` header comment.

    `csv.DictReader` on the whole file would read the comment as the header and
    silently produce one column called `# call-graph-unresolved.csv ...`, which
    is a parse that succeeds and answers nothing.
    """
    lines = [ln for ln in text.splitlines(True) if not ln.startswith("#")]
    return list(csv.DictReader(lines))


def diff_table(have, want, columns):
    """Lines describing a row-level difference, or `[]`.

    Empty when every row parses equal, which is **not** the same as identical:
    the byte comparison is the pass condition and it lives in `check_table()`.
    This renders a difference and never decides one, for the reason
    `call_graph.diff_table()` gives -- the suite drives the shipped function
    rather than a re-implementation, so what is asserted is what the gate runs.
    """
    have_rows = read_rows(have)
    want_rows = read_rows(want)
    key = columns[0]
    lines = []
    shown = 0
    for a, b in zip(have_rows, want_rows):
        if a != b:
            lines.append("  %s:" % a.get(key))
            for k in columns:
                if a.get(k) != b.get(k):
                    lines.append("    %-12s committed %r, recomputed %r"
                                 % (k, a.get(k), b.get(k)))
            shown += 1
            if shown >= 20:
                lines.append("  ... more")
                break
    if len(have_rows) != len(want_rows):
        lines.append("  row count: committed %d, recomputed %d"
                     % (len(have_rows), len(want_rows)))
    return lines


def check_table(have, want, columns):
    """`(exit_code, lines)`: what `--check` returns.

    Byte equality is the pass condition and it is the only one, for
    `call_graph.check_table()`'s reason: `.gitattributes` marks the decompiled
    `.c` trees `-text` for the CRLF hazard and does not cover
    `ec/annotations/*.csv`, so a table whose rows parse equal while its bytes do
    not is reachable rather than hypothetical, and calling it clean would be
    the exact quiet drift the check exists to close.
    """
    if have == want:
        return 0, []
    lines = diff_table(have, want, columns)
    if not lines:
        lines = ["  bytes differ and every row parses equal: line endings, a "
                 "trailing blank line, column order or quoting differ from "
                 "what this tool writes"]
    return 1, lines


def distinct_listings(sites):
    """The number of `(scope, listing)` pairs reaching any unresolved target.

    A **union**, over the whole site map, and not the sum of the per-target
    `callers` column: that column counts distinct callers *per target*, so a
    listing that reaches two unresolved targets is one listing and the sum
    counts it twice. Summing a per-target count and printing it under the word
    *distinct* is the same mistake one level down as reporting a per-target
    cause as a per-population one, and `ReportPrintingTests` holds the printed
    figure to this union rather than to the column.
    """
    return len({(scope, caller)
                for reaching in sites.values()
                for scope, caller, _site, _form in reaching})


def report(sites, unresolved, unreached, overlap, xdata):
    """Print both populations, every figure split by cause, and the limits.

    The numbers here are the ones `ec/annotations/call-graph.md` quotes, so a
    reader re-derives them with this tool instead of trusting prose. The
    calibration lines are printed rather than left to the docstring because a
    report read once in a terminal is where a weak negative gets promoted into
    a finding.
    """
    by_cause = collections.Counter(r["cause"] for r in unresolved)
    sites_by_cause = collections.Counter()
    for r in unresolved:
        sites_by_cause[r["cause"]] += int(r["sites"])
    by_entry = collections.Counter(r["entry"] for r in unreached)
    paged = [r for r in unresolved
             if r["forms"] and all(f in ("ajmp", "acall")
                                   for f in r["forms"].split())]
    print("call_graph_gaps.py -- why call_graph.py's unresolved and unreached "
          "rows are unresolved and unreached")
    print()
    print("  unresolved transfer targets                 %6d" % len(unresolved))
    print("  sites reaching them                         %6d"
          % sum(int(r["sites"]) for r in unresolved))
    print("  distinct caller listings reaching them      %6d"
          % distinct_listings(sites))
    for cause in CAUSES:
        print("    %-42s %6d targets, %6d sites"
              % (cause, by_cause[cause], sites_by_cause[cause]))
    print("  %-44s %6d" % ("of which every reaching site is ajmp/acall",
                           len(paged)))
    print("  %-44s %6d" % ("targets the precedence decided over one cause",
                           overlap))
    print()
    print("  registers.yaml addresses consulted         %6d" % len(xdata))
    print("  limits. `xdata-or-data` is a lookup in a file that carries XDATA")
    print("  addresses and no code addresses, so a target it does not name is")
    print("  not found by this method -- not 'not XDATA', and not 'code'.")
    print("  `no-index-row` is what is left once the other three have had their")
    print("  turn: this method placed the target nowhere. Neither value is a")
    print("  claim that a target has no function.")
    print()
    print("  anonymous rows no transfer reaches           %6d" % len(unreached))
    for entry in ENTRIES:
        print("    %-42s %6d" % (entry, by_entry[entry]))
    print("    %-42s %6d" % ("of those, from a named predecessor",
                              sum(1 for r in unreached
                                  if r["pred_named"] == "yes")))
    print("  limit. `not-adjacent` is not 'reached by a function pointer': it is")
    print("  this method reading no transfer and no continuation for the row.")
    print("  `adjacent-no-fallthrough` is a row whose predecessor ends in a")
    print("  return or a transfer control cannot be fallen past, or in a")
    print("  conditional branch this tool does not trace -- so it is counted, not")
    print("  credited with an entry.")
    print()
    print("  every non-obvious target, by address, so the classification is read")
    print("  at its rows rather than only counted:")
    for row in unresolved:
        if row["cause"] != "no-index-row":
            print("  %-6s %-14s %3d site(s)  %-22s host %s/%s %s"
                  % (row["target"], row["cause"], int(row["sites"]),
                     row["forms"], row["host_scope"], row["host_addr"],
                     row["host_name"]))
    print()
    print("  wrote %s and %s" % (os.path.relpath(UNRESOLVED, REPO),
                                 os.path.relpath(UNREACHED, REPO)))


def self_test() -> int:
    """Known answers against `ec/tools/testdata/call-graph-gaps/`.

    The fixture carries one instance of each cause, one target two rules would
    claim, and one unreached row of each `entry` value. Every assertion is about
    a shape at an address the committed tree does not use, so the property
    outlives whatever the real census does next -- a fixture that asserted the
    real numbers would redden on the next tranche rather than telling anyone the
    classifier broke.

    It also runs the two rejections `--check` exists for, because a check that
    has quietly started accepting everything is indistinguishable from one that
    is working.
    """
    index = call_graph.load_index(os.path.join(FIXTURE, "index.csv"))
    xdata = build_ec_decompile.registered_addresses(
        os.path.join(FIXTURE, "registers.yaml"))
    decompiled = os.path.join(FIXTURE, "decompiled")
    sites = unresolved_sites(index, decompiled)
    edges, _unresolved, _orphans, _total, _listings = call_graph.scan(
        index, decompiled)
    rows = unresolved_rows(index, sites, xdata)
    unreached = unreached_rows(index, edges, decompiled)
    spans_ = spans(index)
    by_addr = {r["target"]: r for r in rows}
    unreached_by_key = {(r["scope"], r["addr"]): r for r in unreached}
    ok = True

    def check(label, cond):
        nonlocal ok
        print("  %s  %s" % ("ok  " if cond else "FAIL", label))
        if not cond:
            ok = False

    print("call_graph_gaps.py --self-test "
          "(fixture: ec/tools/testdata/call-graph-gaps)")
    check("the fixture's sites are the ones scan() counted: %d targets over %d"
          " sites" % (len(sites), sum(len(v) for v in sites.values())),
          set(sites) == set(_unresolved)
          and sum(len(v) for v in sites.values())
          == sum(_unresolved.values()))
    check("every cause in the vocabulary is exercised, and nothing outside it: "
          "the fixture carries %d targets over %d sites"
          % (len(rows), sum(int(r["sites"]) for r in rows)),
          {r["cause"] for r in rows} == set(CAUSES)
          and not ({r["cause"] for r in rows} - set(CAUSES)))
    # Each cause, pinned at the address that carries it rather than by a count,
    # so a fixture row that gets renamed later does not redden the run, and the
    # addresses are the fixture's own -- never the committed tree's, because an
    # assertion against a real address would redden the day a tranche moves it.
    check("multi-scope is the address two index rows carry and no reaching "
          "site's scope decides: D100 is a bank0 and a bank1 row and the site "
          "is common, so resolve() declines and both hosts are named",
          by_addr["D100"]["cause"] == "multi-scope"
          and by_addr["D100"]["host_addr"] == "D100 D100"
          and by_addr["D100"]["host_scope"] == "bank0 bank1"
          and index.resolve("common", "D100") is None)
    check("xdata-or-data is a registers.yaml hit and nothing more: D012 is in "
          "this fixture's registers.yaml and carries no index row",
          by_addr["D012"]["cause"] == "xdata-or-data"
          and "D012" not in index.by_addr)
    check("interior-entry is strictly inside another row's size span: D01E sits "
          "inside common/D010's [D010, D025) and has no index row of its own",
          by_addr["D01E"]["cause"] == "interior-entry"
          and by_addr["D01E"]["host_addr"] == "D010"
          and "D01E" not in index.by_addr
          and index.by_scope_addr[("common", "D010")]["size"] == "21")
    check("no-index-row is what is left, and it is a target this method placed "
          "nowhere rather than a row with no function: D0F1 has no host and no "
          "registers.yaml entry",
          by_addr["D0F1"]["cause"] == "no-index-row"
          and by_addr["D0F1"]["host_addr"] == ""
          and "D0F1" not in index.by_addr
          and int("D0F1", 16) not in xdata)
    check("a target two rules would claim is reported under the higher one and "
          "keeps its host: D012 is both xdata-or-data and interior-entry, and "
          "the host survives the precedence",
          all_causes("D012", {"common"}, [], hosts("D012", spans_), xdata)
          == ["xdata-or-data", "interior-entry"]
          and by_addr["D012"]["cause"] == "xdata-or-data"
          and by_addr["D012"]["host_addr"] == "D010")
    check("the paged-form signal is a column, not a fifth cause: D012 is "
          "reached by a 2-byte ajmp and is still xdata-or-data",
          by_addr["D012"]["forms"] == "ajmp"
          and len(CAUSES) == 4)
    check("the listings column names the listing and the instruction, so a row "
          "reads back to the site that produced it",
          by_addr["D012"]["listings"] == "common/D080@D080")
    check("the entry column splits the unreached population, and every value "
          "in it is in the vocabulary",
          {r["entry"] for r in unreached} == set(ENTRIES)
          and not ({r["entry"] for r in unreached} - set(ENTRIES)))
    check("a row one past a `ret` is adjacent but not entered by falling "
          "through: D040 sits after common/D03F's `ret`, and reading it as a "
          "fall-through would credit an entry the bytes do not make",
          unreached_by_key[("common", "D040")]["entry"]
          == "adjacent-no-fallthrough"
          and unreached_by_key[("common", "D040")]["pred_addr"] == "D03F")
    check("and the same holds past a `ljmp`, which is the case a returns-only "
          "predicate cannot see: D06D sits after common/D06A's 3-byte `ljmp`, "
          "so it is jumped over rather than fallen into",
          unreached_by_key[("common", "D06D")]["entry"]
          == "adjacent-no-fallthrough"
          and unreached_by_key[("common", "D06D")]["pred_addr"] == "D06A")
    check("and past a conditional branch, which is the deliberate half of the "
          "rule: D07D sits after common/D07A's `cjne`, and a branch taken "
          "nothing, not taken the next address -- this tool reads listings "
          "rather than tracing, so it credits no fall-through either way",
          unreached_by_key[("common", "D07D")]["entry"]
          == "adjacent-no-fallthrough"
          and unreached_by_key[("common", "D07D")]["pred_addr"] == "D07A")
    check("a row one past an instruction that hands control to the next address "
          "is a fall-through, and the predecessor is named in the row: D031 "
          "after common/D030's `nop`",
          unreached_by_key[("common", "D031")]["entry"] == "fall-through"
          and unreached_by_key[("common", "D031")]["pred_addr"] == "D030"
          and unreached_by_key[("common", "D031")]["pred_name"]
          == "host_named_d030"
          and unreached_by_key[("common", "D031")]["pred_named"] == "yes")
    check("a row nothing places is not-adjacent, with no predecessor invented: "
          "D050",
          unreached_by_key[("common", "D050")]["entry"] == "not-adjacent"
          and unreached_by_key[("common", "D050")]["pred_addr"] == ""
          and unreached_by_key[("common", "D050")]["pred_named"] == "")
    anon_keys = {(r["program"], r["_addr"]) for r in index.rows
                 if r["name"].startswith("FUN_")}
    check("the unreached population is exactly report()'s -- every anonymous "
          "index row no transfer reaches, and no row a transfer does reach",
          set(unreached_by_key) == anon_keys - set(edges))
    rendered = render(rows, UNRESOLVED_COLUMNS, HEADER_NOTE)
    # The fixed point is checked on the whole file, header comment included:
    # reading the committed bytes back with `read_rows()` and writing them again
    # must reproduce the file byte for byte, or a round trip through this tool's
    # own parser is lossy and `--check` would reject a correct regeneration.
    check("the rendered table is a csv.DictReader fixed point, header comment "
          "included, which is what --check relies on",
          render(read_rows_text(rendered), UNRESOLVED_COLUMNS, HEADER_NOTE)
          == rendered)
    check("the header comment is what `read_rows()` skips and a reader sees, "
          "and naming the file's own weak negative rather than a fixed string",
          rendered.startswith("# call-graph-unresolved.csv")
          and "`no-index-row` is a WEAK NEGATIVE" in rendered
          and len(read_rows(rendered)) == len(rows))
    check("the rendered table against itself passes, which is --check's passing "
          "case",
          check_table(rendered, rendered, UNRESOLVED_COLUMNS) == (0, []))
    edited = [dict(r) for r in rows]
    edited[0]["cause"] = "edited-by-the-self-test"
    edited_lines = diff_table(render(edited, UNRESOLVED_COLUMNS, HEADER_NOTE),
                              rendered, UNRESOLVED_COLUMNS)
    check("a table with one cell altered is rejected, naming that row and that "
          "column: %s" % rows[0]["target"],
          any(line == "  %s:" % rows[0]["target"] for line in edited_lines)
          and any("cause" in line and "recomputed" in line
                  for line in edited_lines))
    dropped = render(rows[:-1], UNRESOLVED_COLUMNS, HEADER_NOTE)
    check("a table with its last row dropped is rejected on the row count, a "
          "drift no cell-by-cell comparison can see",
          diff_table(dropped, rendered, UNRESOLVED_COLUMNS)
          == ["  row count: committed %d, recomputed %d"
              % (len(rows) - 1, len(rows))])
    crlf = rendered.replace("\n", "\r\n")
    rc, lines = check_table(crlf, rendered, UNRESOLVED_COLUMNS)
    check("a CRLF table is rejected on its bytes although every row parses "
          "equal -- the row diff alone finds nothing there, which is why the "
          "pass condition is the comparison -- and the report is not empty",
          rc == 1 and lines
          and diff_table(crlf, rendered, UNRESOLVED_COLUMNS) == [])
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def read_rows_text(text):
    """`read_rows()` as a round-tripping render input, for the fixed-point check.

    The rendered rows are parsed and handed back to `render()`, which is what
    makes "the file this tool writes reads back to the file this tool writes"
    a checkable statement rather than an assumption about `csv`.
    """
    rows = read_rows(text)
    return [{k: row[k] for k in UNRESOLVED_COLUMNS} for row in rows]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="recompute both tables and fail on any diff")
    mode.add_argument("--self-test", action="store_true",
                      help="known answers against the committed fixture")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    index = call_graph.load_index()
    edges, _unresolved, _orphans, _total, _listings = call_graph.scan(index)
    xdata = build_ec_decompile.registered_addresses()
    sites = unresolved_sites(index)
    rows = unresolved_rows(index, sites, xdata)
    unreached = unreached_rows(index, edges)
    overlap = sum(1 for addr in sites
                  if len(all_causes(addr, {s[0] for s in sites[addr]},
                                    list(index.by_addr.get(addr, ())),
                                    hosts(addr, spans(index)), xdata)) > 1)

    tables = [(UNRESOLVED, rows, UNRESOLVED_COLUMNS),
              (UNREACHED, unreached, UNREACHED_COLUMNS)]
    texts = [(path, render(rs, cols, HEADER_NOTE), cols)
             for path, rs, cols in tables]

    if args.check:
        failed = False
        for path, want, cols in texts:
            name = os.path.relpath(path, REPO)
            if not os.path.exists(path):
                print("missing %s -- run call_graph_gaps.py to write it" % name,
                      file=sys.stderr)
                failed = True
                continue
            with open(path, newline="") as f:
                have = f.read()
            rc, lines = check_table(have, want, cols)
            if rc == 0:
                print("%s: %d rows, no diff" % (name, len(read_rows(want))))
                continue
            failed = True
            for line in lines:
                print(line)
            print("%s differs from the committed listings; re-run without "
                  "--check" % name, file=sys.stderr)
        return 1 if failed else 0

    for path, text, _cols in texts:
        with open(path, "w", newline="") as f:
            f.write(text)
    report(sites, rows, unreached, overlap, xdata)
    return 0


if __name__ == "__main__":
    sys.exit(main())