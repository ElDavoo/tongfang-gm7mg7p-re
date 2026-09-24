#!/usr/bin/env python3
"""Group the annotated functions into subsystems, from what already exists.

`ghidra-functions.csv` has one row per function and no notion of a subsystem.
That is the gap issue #135 names: a reader has to reassemble the high-level
picture by hand, every time. This adds the layer mechanically -- seeds from
the `type` column and the vector table that are already typed, then
call-graph clustering for the remainder -- and writes it to
`<component>/annotations/function-groups.csv`, one row per annotated
function:

    scope,addr,group,group_basis,comment,evidence

`group_basis` is closed: `type` (the existing `type` column already names a
family), `vector` (the 0x0000 interrupt table), `module` (the BIOS, where the
module IS the grouping), `callgraph` (a connected component of the call
graph), `shared`, and `ungrouped`.

**A `callgraph` group is a connected component, not a subsystem.** Union-find
over `lcall`/`ljmp` edges answers "are these mutually reachable", and on this
firmware the largest component holds 323 of the 1,804 rows. That is a real
structural fact and a poor subsystem boundary, so the group is named
`callgraph_<scope>_<addr>`, its size is in the row's comment, and --report
names any component of 50 or more rather than letting it read as a mechanism.
The seeds -- the ones read off the `type` column, the vector table and the
BIOS modules -- are the part of this layer that says what a group is *for*.

**The scope in that name is the component's dominant scope, and --check holds
it there.** A component can span scopes -- the common area is reachable from
any bank -- so the token says which one the component mostly is. Naming it
after the first member instead described whichever row the union-find emitted
first, and four of the nineteen names were wrong that way: a 323-row component
of mostly bank1 rows read `callgraph_bank0_1803`, and a 145-row component of
mostly `pd` rows read `callgraph_common_0EF3`, which hands a reader 144 rows of
the separate ITE8850-PD program under the token `common` -- the exact
conflation the `pd` grade rule in grade_name_basis.py exists to prevent.

**The banking caveat is inherited verbatim from audit_call_targets.py, and
this is the part that must not be softened.** Nothing in an `lcall` names a
bank: bank0->bank1 and bank0->bank0 are the same three bytes, and both banks
are mapped at base 0x8000. So this tool **never joins bank0 to bank1**. A
cross-region edge is counted, bucketed and reported, and never used to merge
two clusters: the rule is structural, so the union never sees a cross-region
edge and there is no cluster to reject afterwards. Per CLAUDE.md a zero here
means *not found by this method* and never "absent", so every run prints the
A/B/C edge populations, the cross-region count and the ungrouped remainder,
and `--check` refuses a `callgraph` group that spans two banks. The rule is
scoped to `callgraph` on purpose: a `type`-seeded group can hold a bank0 row
and a bank1 row, and that is two functions happening to share a role rather
than a merge, which is what a role-based grouping means.

**What a group is not.** A group is a structural claim about call structure:
these routines work together. It is not a claim about what the EC does with
them on a live machine, and no grouping here establishes a mechanism. No
hardware is reachable from a GitHub-hosted runner, so nothing in this file
should be read as a behavioural result.

**What call-graph clustering cannot do, and it is the first thing to say.**
Three blind spots, none of them closed here: the graph is built from the
committed `.asm` listings' `lcall`/`ljmp` operands, so a computed target
(`sjmp @a+dptr`) and a bank-select trampoline's DPTR-carried target are both
invisible to it; Ghidra's function boundaries on this firmware are a
hypothesis (ec/annotations/bank-call-audit.md §1), so an edge can be an
artifact of where a boundary was drawn; and the paged `ajmp`/`acall` forms
stay inside the caller's own region and are not edges at all. A cluster count
is not a topology. Read the report.

Usage:
    python3 ec/tools/group_functions.py --report
    python3 ec/tools/group_functions.py --apply
    python3 ec/tools/group_functions.py --check
    python3 ec/tools/group_functions.py --self-test
"""
import argparse
import collections
import csv
import itertools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from audit_call_targets import OTHER_BANK, bucket_of  # noqa: E402,F401

EC_CSV = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")
EC_GROUPS = os.path.join(REPO, "ec", "annotations", "function-groups.csv")
BIOS_CSV = os.path.join(REPO, "bios", "annotations", "ghidra-functions.csv")
BIOS_GROUPS = os.path.join(REPO, "bios", "annotations", "function-groups.csv")

# The closed vocabulary, and the order --report prints in. `ungrouped` is a
# result, not a failure: it is what a row the method did not reach is, and
# having it in the list is what makes saying so cost nothing -- the same
# argument `unresolved` makes in the `type` vocabulary.
GROUP_BASES = ("type", "vector", "module", "callgraph", "shared", "ungrouped")

# `type` values that already name a family, mapped to the group they imply.
# The two hand-written charge-target rows and the two `ec-io` rows are here
# because the issue names them; the rest is the mechanical mapping from a
# typed column to a group, which is what makes the first pass real rather
# than a list of names restated.
TYPE_GROUPS = {
    "charge-target": "charge-target-update",
    "ec-io": "ec-io-helpers",
    "bank-switch": "bank-switch-trampolines",
    "delay": "delay-loops",
    "dispatch": "dispatch-tables",
    "math": "arithmetic",
}

# The 0x0000 interrupt table, matched on the name rather than on
# `seed_basis`. Only 3 index rows carry `seed_basis=vector`, because the seed
# set was built from the call census and the rest of the table reached the
# export by annotation; the 8 handlers are all there, named for the
# interrupt each one is. The match is `*_vector_forwarder_*` plus the reset
# vector, so a function that merely forwards is not swept in with them.
VECTOR = re.compile(r"^(?:reset|int\d|timer\d|serial\d)_vector_")

# The banked regions, and the base both are mapped at. 0x8000 is where
# audit_call_targets.py draws its bucket A/B/C line, and the reason a target
# at or above it does not name a bank.
BANK_BASE = 0x8000
BANKS = ("bank0", "bank1")

# `<addr> <bytes> <mnemonic> <operands>`; the same shape
# grade_name_basis.py reads, kept local so this tool has no import cycle.
LISTING = re.compile(r"^\s*([0-9A-Fa-f]{4,8})\s+"
                     r"((?:[0-9a-f]{2}|-)(?:\s+(?:[0-9a-f]{2}|-)){1,5})\s+"
                     r"(\S+)\s*(.*?)\s*$")

# The 3-byte absolute forms. These are the ones that CAN name an address in
# another bank, which is why they are the ones worth bucketing.
ABSOLUTE = frozenset(("lcall", "ljmp"))

# `callgraph_<scope>_<addr>`, the name a clustered component is given. Parsed
# by `--check` so a name that no longer describes its own rows is caught there
# rather than read as fact by the next person to open the file.
CALLGRAPH_NAME = re.compile(r"^callgraph_([a-z0-9]+)_([0-9A-F]{4,8})$",
                            re.I)


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def norm_addr(addr):
    return (addr or "").upper().replace("0X", "")


def region_of(scope):
    """Which region a scope belongs to, for the banking rule.

    `common` is the 0x0000-0x7FFF area both banks carry; `pd` is the
    separate ITE8850-PD program with its own vectors and its own XDATA map.
    Neither is a bank, and neither is joined to one."""
    return scope if scope in BANKS else "common"


def listing_calls(path):
    """{caller-relative address: [target addresses]} from a committed `.asm`.

    Only the 3-byte absolute forms. `ajmp`/`acall` are paged and stay inside
    the caller's own region, so they are not a banking question and joining
    on them would manufacture cross-region edges that cannot exist."""
    edges = collections.defaultdict(list)
    if not path or not os.path.isfile(path):
        return edges
    with open(path, errors="replace") as text:
        for line in text:
            if line.lstrip().startswith(";") or not line.strip():
                continue
            m = LISTING.match(line)
            if not m:
                continue
            addr, mnemonic, operands = (int(m.group(1), 16),
                                        m.group(3).lower(), m.group(4))
            if mnemonic not in ABSOLUTE:
                continue
            target = re.search(r"0x([0-9a-fA-F]{4})", operands)
            if target:
                edges[addr].append(int(target.group(1), 16))
    return edges


def asm_path(row, repo=REPO):
    """The row's committed `.asm`, the `.asm` first per the evidence
    convention (the machine code is ground truth, the `.c` is a reading)."""
    for path in (row.get("evidence") or "").split(";"):
        path = path.strip()
        if path.endswith(".asm"):
            full = os.path.join(repo, path)
            if os.path.isfile(full):
                return full
    return None


def bucket_populations(rows, repo=REPO):
    """The A/B/C populations over the edges this tool actually reads, counted
    by `audit_call_targets.bucket_of` rather than by a second implementation
    of the rule.

    Printed on every run because the alternative is worse: a clustering tool
    that reports only how many groups it found reads as though it had found
    the structure. These three numbers say how much of the graph the
    assumption decides -- bucket B is the population an `lcall` cannot
    resolve, and it is the largest of the three here."""
    out = collections.Counter()
    for row in rows:
        scope = row["scope"]
        for target in itertools.chain.from_iterable(
                listing_calls(asm_path(row, repo)).values()):
            out[bucket_of(region_of(scope), target)] += 1
    return out


def seed_groups(rows):
    """{(scope, addr): (group, group_basis, comment)} from what is already
    typed, before any clustering.

    Three seeds, in precedence order:

      * `vector` -- a row in the 0x0000 interrupt table. Its basis is the
        table, not the name: the names say `int0_vector_forwarder_to_052f`
        because that is what the bytes are, and a name that says which
        interrupt it is has already been read against the architecture.
      * `type` -- a `type` that names a mechanism rather than a role.
        `bank-switch` is the issue's own worked example.
      * `module` -- BIOS only, filled in by the caller. The module IS the
        grouping there, and it is the better starting point the issue says
        the BIOS has.
    """
    seeds = {}
    for row in rows:
        key = (row["scope"], norm_addr(row["addr"]))
        name = (row.get("name") or "")
        row_type = (row.get("type") or "").strip()
        if VECTOR.match(name):
            seeds[key] = ("interrupt-vectors", "vector",
                          "Row of the 0x0000 interrupt table; the name says "
                          "which interrupt it is, which is a read against the "
                          "8051 vector layout rather than a guess.")
        elif row_type in TYPE_GROUPS:
            basis = "the `type` column already names this family"
            seeds[key] = (TYPE_GROUPS[row_type], "type", basis)
    return seeds


def cluster(rows, repo=REPO, min_size=4):
    """The call-graph clusters, as `{(scope, addr): (group, comment)}`.

    Union-find over the caller->callee edges the committed listings give,
    **within a region only**. The no-cross-bank rule is structural rather
    than a filter applied afterwards: the union simply never sees a
    cross-region edge, so there is no cluster to reject and the invariant
    cannot be violated by a bug in a later pass. The edges that cross a
    region are counted and reported, never merged."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # A node per annotated row, keyed (scope, addr), so a cluster is a set of
    # annotated functions and an edge to something unannotated is simply not
    # there to join on.
    by_addr = collections.defaultdict(dict)
    for row in rows:
        key = (row["scope"], norm_addr(row["addr"]))
        find(key)
        by_addr[row["scope"]][norm_addr(row["addr"])] = row

    cross_region = 0
    for row in rows:
        scope = row["scope"]
        caller = (scope, norm_addr(row["addr"]))
        # A row's `.asm` is the WHOLE function body, so every `lcall` in it
        # is an edge out of that function -- not only the one at its entry
        # address. Reading just the entry is how 2,851 committed edges
        # become 206 and the graph looks far sparser than the export is.
        for target in itertools.chain.from_iterable(
                listing_calls(asm_path(row, repo)).values()):
            # Below the bank base is the common area, which both banks share:
            # a call there from either bank is an edge WITHIN that bank's own
            # graph, keyed to the common row.
            if target < BANK_BASE:
                if (scope, "%04X" % target) in by_addr.get(scope, {}):
                    union(caller, (scope, "%04X" % target))
                elif any(("%04X" % target) in by_addr.get(s, {})
                         for s in BANKS + ("common",)):
                    # A common-area row is its own scope, and both banks
                    # carry it. Join through the scope the annotation says.
                    for s in ("common", scope):
                        if ("%04X" % target) in by_addr.get(s, {}):
                            union(caller, (s, "%04X" % target))
                            break
                continue
            # At or above the bank base. The target is in the caller's own
            # bank by assumption -- the assumption audit_call_targets.py
            # cannot prove -- so the edge stays inside the region.
            #
            # The cross-region count is a SEPARATE question from the join, and
            # has to be asked separately: an address can exist in both banks
            # (they are the same length and much of them is alike), in which
            # case the same-bank branch below is taken and a count that lived
            # in its `else` would report zero for an edge that is genuinely
            # ambiguous. What is counted here is every bucket-B edge whose
            # target also exists in the other bank, because that is the
            # population the assumption decides and this tool cannot.
            taddr = "%04X" % target
            other = OTHER_BANK.get(scope)
            if other and taddr in by_addr.get(other, {}):
                cross_region += 1
            if taddr in by_addr.get(scope, {}):
                union(caller, (scope, taddr))
    clusters = collections.defaultdict(list)
    for key in list(parent):
        clusters[find(key)].append(key)
    return clusters, cross_region


def component_name(members):
    """`callgraph_<scope>_<addr>` for one component, and the (scope, addr)
    pair the name asserts.

    The scope token is the component's **dominant** scope, not its first
    member's. A component can hold rows from more than one scope -- the
    common area is reachable from any bank, and a bank0 caller can reach a
    common row -- and taking the first member meant the token described
    whichever row the union-find happened to emit first rather than the
    component. Four of the nineteen names on the committed file were wrong
    that way, and the worst was `callgraph_common_0EF3`: 144 of its 145 rows
    are `pd`, the separate ITE8850-PD program, which this repository spends
    three separate guards keeping distinct from the EC's common area, and the
    name handed a reader 144 rows of that separate program under the token
    `common`.

    "Dominant" is the scope holding the most members, ties broken by scope
    name so the choice does not depend on iteration order. The address is
    the lowest in that scope, which keeps the name stable across re-runs and
    is a real member address a reader can look up.
    """
    counts = collections.Counter(scope for scope, _addr in members)
    scope = min(counts, key=lambda s: (-counts[s], s))
    return ("callgraph_%s_%s" % (scope, min(a for s, a in members if s == scope)),
            (scope, min(a for s, a in members if s == scope)))


def misnamed_callgraph_groups(grows):
    """`callgraph` names whose scope token contradicts the rows carrying them.

    The whole-file form of the naming rule, in the same shape as
    `cross_bank_groups`: the name is a property of the group, so it is
    checked over the group column rather than per row. A name is right when
    its token is the dominant scope among the rows that carry it, which is
    what `component_name` writes and what a hand-edit can quietly stop being.
    Without this the four misnames on the committed file sat there through
    every other gate, which is the same silent failure `cross_bank_groups`
    exists to catch.
    """
    scopes = collections.defaultdict(collections.Counter)
    for row in grows:
        if (row.get("group_basis") or "").strip() != "callgraph":
            continue
        scopes[(row.get("group") or "").strip()][
            (row.get("scope") or "").strip()] += 1
    out = []
    for name, counts in sorted(scopes.items()):
        m = CALLGRAPH_NAME.match(name)
        if not m:
            out.append((name, "is not a callgraph_<scope>_<addr> name, so a "
                       "reader cannot tell what it identifies"))
            continue
        dominant = min(counts, key=lambda s: (-counts[s], s))
        if m.group(1).lower() != dominant:
            out.append((name, "says scope %r but %d of its %d rows are %s; the "
                       "scope token is the component's dominant scope, so a "
                       "reader who trusts it is told the wrong region"
                       % (m.group(1), counts[dominant], sum(counts.values()),
                          dominant)))
    return out


def group_rows(rows, repo=REPO, is_bios=False, min_size=4):
    """{key: (group, group_basis, comment, evidence)} for every row.

    Precedence: an existing seed wins over a cluster, because a seed is read
    off something already established (`type`, the vector table, the module)
    and a cluster is a guess at structure. A row in a cluster too small to be
    a subsystem stays `ungrouped` rather than getting a plausible label --
    the same rule that put `unresolved` in the `type` vocabulary."""
    seeds = seed_groups(rows)
    if is_bios:
        for row in rows:
            seeds.setdefault((row["scope"], norm_addr(row["addr"])),
                             (row["scope"], "module",
                              "The module is the grouping: the export is "
                              "per-module and the module name is the real "
                              "structural layer the BIOS has."))
    clusters, cross = cluster(rows, repo, min_size)
    out = {}
    assigned = collections.defaultdict(list)
    for members in clusters.values():
        if len(members) < min_size:
            continue
        # The size goes in the comment, and the report flags a large one,
        # because union-find over a call graph produces CONNECTED
        # COMPONENTS and a connected component is not a subsystem. A 300-member
        # blob says these 300 functions are mutually reachable; it does not
        # say they do one job, and reading it as though it did is the
        # overclaim this repository's rules are about. The name is prefixed
        # `callgraph_` precisely so it cannot be mistaken for a mechanism.
        #
        # The scope in the name is the component's dominant scope, not its
        # first member's -- see `component_name` for why that distinction is
        # load-bearing rather than cosmetic.
        name, _seed = component_name(members)
        for key in members:
            assigned[key].append(name)
    sizes = {name: sum(1 for v in assigned.values() if name in v)
             for name in {n for v in assigned.values() for n in v}}
    for row in rows:
        key = (row["scope"], norm_addr(row["addr"]))
        if key in seeds:
            group, basis, comment = seeds[key]
            out[key] = (group, basis, comment, row.get("evidence", ""))
        elif key in assigned:
            group = sorted(assigned[key])[0]
            out[key] = (group, "callgraph",
                        "One of %d mutually reachable functions in the "
                        "lcall/ljmp graph of the committed listings, within "
                        "one region only; a cross-region edge is never joined "
                        "(see audit_call_targets.py). A connected component is "
                        "not a subsystem: this says the call graph connects "
                        "them, not that they do one job."
                        % sizes[group],
                        row.get("evidence", ""))
        else:
            out[key] = ("ungrouped", "ungrouped",
                        "No typed seed and no connected component at or above "
                        "the minimum size. Not found by this method.",
                        row.get("evidence", ""))
    return out, cross


def write_groups(path, rows, grouped):
    fields = ["scope", "addr", "group", "group_basis", "comment", "evidence"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            key = (row["scope"], norm_addr(row["addr"]))
            group, basis, comment, evidence = grouped[key]
            writer.writerow({
                "scope": row["scope"], "addr": row["addr"], "group": group,
                "group_basis": basis, "comment": comment,
                "evidence": evidence,
            })


def check_group_row(row, banks_by_addr, repo=REPO):
    """One row's refusals.

    `banks_by_addr` maps a normalised address to the set of regions that
    address appears in across the whole file. The no-cross-bank rule is
    about a *group*, not a row: the thing that must not happen is one group
    name collecting functions out of two banks. That is a whole-file
    property, so it is checked in `check()` over the group column; what this
    function refuses per row is the vocabulary, an empty group, and an
    `evidence` citation that resolves to nothing on disk.

    The address-level view is still useful and is asserted by --self-test:
    a bank0 0x8100 and a bank1 0x8100 are two functions, and the graph must
    keep them apart even though the number is the same."""
    out = []
    basis = (row.get("group_basis") or "").strip()
    if basis not in GROUP_BASES:
        out.append("group_basis %r is outside the closed list (%s)"
                   % (basis, ", ".join(GROUP_BASES)))
    if not (row.get("group") or "").strip():
        out.append("has an empty group")
    # The group layer copies `evidence` from the annotation row, so this is
    # the same citation a reader would trace the group back through -- and it
    # is the one place in this file where the trace can be followed, which is
    # what makes it worth holding to the same on-disk guard
    # build_ec_decompile.py applies to the EC annotation CSV. Split on `;`
    # like that guard does, and the separator is load-bearing: a cell written
    # `a.asm, a.c` is one path here, and it is one path that is not on disk.
    # That is exactly how fifteen `OemOcDxe` rows read before this check
    # existed, and it passed every other gate because nothing asked whether
    # the path resolved.
    for path in (p.strip() for p in (row.get("evidence") or "").split(";")):
        if path and not os.path.exists(os.path.join(repo, path)):
            out.append("the evidence %s does not exist on disk" % path)
    return out


def cross_bank_groups(grows):
    """Group names that collect rows out of more than one bank *by clustering*.

    The whole-file form of the caveat, and it is deliberately scoped to the
    bases where a span is a MERGE rather than a coincidence:

      * `callgraph` -- the only basis that asserts the two functions are
        connected. One component spanning bank0 and bank1 is exactly the join
        the caveat forbids, because the edge that made them one component
        could have been a same-bank call.
      * `ungrouped` -- asserts no membership at all; the method did not reach
        the row.
      * `shared` -- the explicit way this file says a name is common to both
        banks on purpose.

    `type` and `vector` are exempt, and the reason is that they are not
    merges. A `type=math` row in bank0 and a `type=math` row in bank1 are two
    different functions that happen to do the same kind of work, which is
    what a role-based grouping means; nothing connected them. Refusing those
    would be refusing the vocabulary the issue asks for. A `vector` group is
    the 0x0000 table, which both banks carry identically by construction."""
    regions = collections.defaultdict(set)
    for row in grows:
        if (row.get("group_basis") or "").strip() != "callgraph":
            continue
        regions[(row.get("group") or "").strip()].add(
            region_of(row.get("scope", "").strip()))
    return sorted(name for name, regs in regions.items()
                  if len(regs & set(BANKS)) > 1)


def self_test():
    """Pin the no-cross-bank rule, the seeds, and the vocabulary.

    The fixture is a graph with a KNOWN cross-bank edge, because the whole
    claim of this tool is that it refuses to join across one."""
    failures = []

    def check(label, cond, detail=""):
        if not cond:
            failures.append("%s %s" % (label, detail))

    scratch = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                           "group_functions_selftest")
    os.makedirs(scratch, exist_ok=True)

    def asm(name, lines):
        path = os.path.join(scratch, name)
        with open(path, "w") as f:
            f.write("; fixture\n")
            for line in lines:
                f.write(line + "\n")
        return path

    # A bank0 function that calls 0x8100, and a 0x8100 that exists in BOTH
    # banks. The three bytes are identical to a same-bank call, which is the
    # whole caveat; the fixture is the smallest case that could be joined
    # wrongly.
    #
    # One listing per function, because a row's `.asm` is its own body and
    # every `lcall` in it is an edge out of that function. Handing the caller
    # and the callee the same listing would give the callee the caller's edge
    # too, which is not a case the tool can be asked about.
    RET = "22 - - -   ret"
    caller_asm = asm("caller.asm", ["8000     12 81 00 lcall    0x8100", RET])
    callee_asm = asm("callee.asm", [RET])
    other_asm = asm("other_bank.asm", [RET])
    same = cross = caller_asm
    rows = [
        {"scope": "bank0", "addr": "8000", "name": "caller", "type": "logic",
         "evidence": os.path.relpath(caller_asm, REPO)},
        {"scope": "bank0", "addr": "8100", "name": "callee", "type": "logic",
         "evidence": os.path.relpath(callee_asm, REPO)},
        {"scope": "bank1", "addr": "8100", "name": "other_bank_callee",
         "type": "logic", "evidence": os.path.relpath(other_asm, REPO)},
    ]
    grouped, cross_edges = group_rows(rows, repo=REPO, min_size=2)
    g00 = grouped[("bank0", "8000")][0]
    g10 = grouped[("bank1", "8100")][0]
    check("a bucket-B edge into the other bank is not joined",
          g00 != g10,
          "(bank0 0x8000 and bank1 0x8100 must not share a group: the same "
          "three bytes name a same-bank call)")
    check("the cross-region edge is counted",
          cross_edges == 1, "(got %r)" % (cross_edges,))

    # The same two bank0 rows, with no bank1 row to tempt it, DO cluster.
    two = [r for r in rows if r["scope"] == "bank0"]
    grouped2, _ = group_rows(two, repo=REPO, min_size=2)
    check("a same-region edge still clusters",
          grouped2[("bank0", "8000")][0] == grouped2[("bank0", "8100")][0])

    # Seeds.
    seeded = group_rows([{"scope": "common", "addr": "0000",
                          "name": "reset_vector_forwarder_to_0070",
                          "type": "entry", "evidence": ""}], repo=REPO)
    check("a vector row is seeded from the table",
          seeded[0][("common", "0000")][1] == "vector")
    bs = group_rows([{"scope": "bank0", "addr": "163C",
                      "name": "load_dptr_88f0_tail_jump_1114",
                      "type": "bank-switch", "evidence": ""}], repo=REPO)
    check("a bank-switch row is seeded from its type",
          bs[0][("bank0", "163C")][0] == "bank-switch-trampolines")
    small = group_rows([{"scope": "bank0", "addr": "163C", "name": "x",
                         "type": "reader", "evidence": ""}], repo=REPO)
    check("a row with no seed and no cluster is ungrouped, not guessed",
          small[0][("bank0", "163C")][0] == "ungrouped")

    # The vocabulary, and the check's own refusals.
    check("check accepts every basis in the vocabulary", all(
        not check_group_row({"scope": "bank0", "addr": "0", "group": "g",
                             "group_basis": b}, {})
        for b in GROUP_BASES))
    check("check refuses an off-list basis", bool(check_group_row(
        {"scope": "bank0", "addr": "0", "group": "g",
         "group_basis": "vibes"}, {})))
    check("check refuses an empty group", bool(check_group_row(
        {"scope": "bank0", "addr": "0", "group": "  ", "group_basis": "type"},
        {})))
    # The evidence guard, on both halves of the shape that made it necessary:
    # a path that is not on disk, and the comma-and-space separator that
    # silently turns two real paths into one that is neither.
    check("check accepts an evidence path that is on disk", not check_group_row(
        {"scope": "bank0", "addr": "0", "group": "g", "group_basis": "type",
         "evidence": "ec/annotations/README.md; ec/annotations/registers.yaml"},
        {}))
    check("check refuses an evidence path that is not on disk", bool(
        check_group_row(
            {"scope": "bank0", "addr": "0", "group": "g", "group_basis": "type",
             "evidence": "ec/annotations/no-such-file.asm"}, {})),
        "(a citation that resolves to nothing is not a citation)")
    check("check refuses a comma-separated evidence cell as one dead path",
          bool(check_group_row(
              {"scope": "OemOcDxe", "addr": "0x3D0", "group": "OemOcDxe",
               "group_basis": "module",
               "evidence": "bios/decompiled/OemOcDxe.annotated.c, "
                           "bios/decompiled/OemOcDxe.c"}, {})),
          "('; ' is the separator; a ', ' cell is one path and it is not on "
          "disk -- this is the shape fifteen BIOS rows carried past every "
          "other gate)")
    check("an empty evidence cell is not this check's business", not check_group_row(
        {"scope": "bank0", "addr": "0", "group": "g", "group_basis": "type",
         "evidence": ""}, {}),
        "(the annotation CSV owns the non-empty rule; this one asks only "
        "whether a path that IS named resolves)")
    # The whole-file form: one group name collecting both banks.
    spanning = [{"scope": "bank0", "addr": "8000", "group": "merged",
                 "group_basis": "callgraph"},
                {"scope": "bank1", "addr": "8100", "group": "merged",
                 "group_basis": "callgraph"}]
    check("check refuses a group spanning two banks",
          cross_bank_groups(spanning) == ["merged"])
    check("a group inside one bank is fine",
          not cross_bank_groups(spanning[:1]))
    check("a common row does not make a group cross-bank",
          not cross_bank_groups([
              {"scope": "common", "addr": "0530", "group": "timers",
               "group_basis": "type"},
              {"scope": "bank0", "addr": "8100", "group": "timers",
               "group_basis": "type"}]),
          "(common is not a bank; only bank0 and bank1 are)")
    check("an ungrouped name spanning banks is not a cross-bank claim",
          not cross_bank_groups([
              {"scope": "bank0", "addr": "8000", "group": "ungrouped",
               "group_basis": "ungrouped"},
              {"scope": "bank1", "addr": "8100", "group": "ungrouped",
               "group_basis": "ungrouped"}]),
          "(ungrouped asserts no membership)")
    check("a type-seeded group spanning two banks is not a merge",
          not cross_bank_groups([
              {"scope": "bank0", "addr": "8000", "group": "arithmetic",
               "group_basis": "type"},
              {"scope": "bank1", "addr": "8100", "group": "arithmetic",
               "group_basis": "type"}]),
          "(two functions that share a role are not connected by anything)")

    # The naming rule: a callgraph name's scope token is the component's
    # DOMINANT scope. The fixture is the shape the committed file got wrong --
    # a component that is mostly the separate PD program, reachable from the
    # common area, so its first member is a `common` row.
    mixed = [("common", "0EF3")] + [("pd", "%04X" % (0x180 + 4 * i)) for i in range(6)]
    name, seed = component_name(mixed)
    check("the scope token is the dominant scope, not the first member's",
          name == "callgraph_pd_0180" and seed == ("pd", "0180"),
          "(a `common` first member must not name a mostly-`pd` component "
          "`common`; got %r)" % (name,))
    check("the same component named from either end agrees",
          component_name(list(reversed(mixed)))[0] == name,
          "(a name that depends on iteration order is not stable)")
    check("a component of one scope names that scope",
          component_name([("bank1", "9A00"), ("bank1", "8100")])[0]
          == "callgraph_bank1_8100")
    check("check accepts a callgraph name that matches its rows",
          not misnamed_callgraph_groups([
              {"scope": "pd", "addr": "0180", "group": "callgraph_pd_0180",
               "group_basis": "callgraph"},
              {"scope": "pd", "addr": "0184", "group": "callgraph_pd_0180",
               "group_basis": "callgraph"},
              {"scope": "common", "addr": "0EF3",
               "group": "callgraph_pd_0180", "group_basis": "callgraph"}]),
          "(the common row is a minority member and does not name the group)")
    check("check refuses a callgraph name that misstates its scope",
          [n for n, _ in misnamed_callgraph_groups([
              {"scope": "common", "addr": "0EF3", "group": "callgraph_common_0EF3",
               "group_basis": "callgraph"},
              {"scope": "pd", "addr": "0180", "group": "callgraph_common_0EF3",
               "group_basis": "callgraph"},
              {"scope": "pd", "addr": "0184", "group": "callgraph_common_0EF3",
               "group_basis": "callgraph"}])] == ["callgraph_common_0EF3"],
          "(two of three rows are pd; the name says common)")
    check("check refuses a callgraph name that is not in the scheme",
          [n for n, _ in misnamed_callgraph_groups([
              {"scope": "bank0", "addr": "8100", "group": "blob",
               "group_basis": "callgraph"},
              {"scope": "bank0", "addr": "8104", "group": "blob",
               "group_basis": "callgraph"}])] == ["blob"],
          "(an unprefixed name cannot be mistaken for a connected component, "
          "which is what the `callgraph_` prefix is for)")
    check("a non-callgraph name is not this check's business",
          not misnamed_callgraph_groups([
              {"scope": "bank0", "addr": "8000", "group": "arithmetic",
               "group_basis": "type"},
              {"scope": "bank1", "addr": "8100", "group": "arithmetic",
               "group_basis": "type"}]),
          "(a type-seeded name is not a callgraph name to begin with)")

    if failures:
        for f in failures:
            print("  FAIL  %s" % f)
        print("  FAILURES ABOVE")
        return 1
    print("  self-test passed")
    return 0


def bases_of(grouped):
    """{group: the group_basis its rows carry}.

    A group name is not unique to a basis in principle -- `Setup` is a
    module and could one day be something else -- so the report asks the rows
    rather than assuming. A name whose rows disagree is a file to look at,
    not one to summarise."""
    out = {}
    for group, basis, _comment, _evidence in grouped.values():
        out.setdefault(group, basis)
    return out


def report(grouped, cross, rows, repo=REPO, is_bios=False):
    counts = collections.Counter(v[0] for v in grouped.values())
    bases = collections.Counter(v[1] for v in grouped.values())
    buckets = bucket_populations(rows, repo)
    print("  %d function(s), %d group(s)" % (len(rows), len(counts)))
    for group, n in counts.most_common(20):
        print("    %-34s %4d  (%s)" % (group, n, next(
            v[1] for v in grouped.values() if v[0] == group)))
    if len(counts) > 20:
        print("    ... and %d more group(s)" % (len(counts) - 20))
    print("    basis: " + " ".join("%s=%d" % (b, bases[b])
                                   for b in GROUP_BASES if bases[b]))
    # A call-graph group is a CONNECTED COMPONENT, and a large one is the
    # shape that reads as a subsystem and is not one. Naming the largest, and
    # saying what it is, is the difference between a report a reader can
    # calibrate and a table of tidy-looking numbers.
    big = [(g, n) for g, n in counts.most_common()
           if n >= 50 and bases_of(grouped).get(g) == "callgraph"]
    if big:
        print("    note  %d call-graph group(s) of 50+ function(s): %s. These "
              "are connected components, not subsystems -- the graph says "
              "these functions are mutually reachable, not that they do one "
              "job." % (len(big), ", ".join("%s=%d" % (g, n) for g, n in big[:3])))
    print("    call-edge buckets (audit_call_targets.py's): "
          + " ".join("%s=%d" % (b, buckets[b]) for b in "ABC" if buckets[b]))
    print("    cross-region edges counted, not joined: %d" % cross)
    print("    ungrouped: %d (not found by this method, never 'absent')"
          % counts.get("ungrouped", 0))


def check(repo=REPO):
    """Refuse a group file that breaks the vocabulary, leaves a function
    ungrouped, or names one address in two banks."""
    problems = []
    for annotations, groups_path, is_bios in (
            (EC_CSV, EC_GROUPS, False), (BIOS_CSV, BIOS_GROUPS, True)):
        rows = read_csv(annotations)
        if not os.path.isfile(groups_path):
            problems.append("no %s; run --apply" % os.path.relpath(groups_path, repo))
            continue
        grows = read_csv(groups_path)
        for name, why in misnamed_callgraph_groups(grows):
            problems.append("%s: group %r %s" % (
                os.path.relpath(groups_path, repo), name, why))
        for name in cross_bank_groups(grows):
            problems.append("%s: group %r collects rows out of more than one "
                            "bank. An lcall does not name a bank -- bank0->bank1 "
                            "and bank0->bank0 are the same three bytes -- so a "
                            "group spanning both is a merge this method cannot "
                            "support (see audit_call_targets.py)."
                            % (os.path.relpath(groups_path, repo), name))
        seen = set()
        for grow in grows:
            for problem in check_group_row(grow, {}, repo):
                problems.append("%s %s: %s" % (os.path.relpath(groups_path, repo),
                                               grow["addr"], problem))
            key = (grow["scope"].strip(), norm_addr(grow["addr"]))
            if key in seen:
                problems.append("%s: duplicate %s %s"
                                % (os.path.relpath(groups_path, repo),
                                   grow["scope"], grow["addr"]))
            seen.add(key)
        annotated = {(r["scope"].strip(), norm_addr(r["addr"])) for r in rows}
        for key in sorted(annotated - seen):
            problems.append("%s: no group for annotated %s %s"
                            % (os.path.relpath(groups_path, repo), key[0], key[1]))
    for problem in problems[:20]:
        print("  FAIL  %s" % problem)
    if len(problems) > 20:
        print("  FAIL  ... and %d more" % (len(problems) - 20))
    if problems:
        print("  FAILURES ABOVE")
        return 1
    print("  every annotated function has a group, every group_basis is in "
          "the closed list, every evidence path is on disk, and no group row "
          "spans two banks")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--report", action="store_true",
                    help="print the proposed grouping over both components; "
                         "no file is written")
    ap.add_argument("--apply", action="store_true",
                    help="write both function-groups.csv files")
    ap.add_argument("--check", action="store_true",
                    help="refuse a group file that breaks the vocabulary, "
                         "leaves a function ungrouped, or names one address "
                         "in two banks")
    ap.add_argument("--self-test", action="store_true",
                    help="pin the no-cross-bank rule on a fixture graph with "
                         "a known cross-region edge")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.check:
        return check()
    for annotations, groups_path, is_bios in (
            (EC_CSV, EC_GROUPS, False), (BIOS_CSV, BIOS_GROUPS, True)):
        rows = read_csv(annotations)
        grouped, cross = group_rows(rows, REPO, is_bios)
        if args.apply:
            write_groups(groups_path, rows, grouped)
        print("%s -- %s" % (os.path.relpath(groups_path, REPO),
                            "wrote" if args.apply else "proposed"))
        report(grouped, cross, rows, REPO, is_bios)
    return 0


if __name__ == "__main__":
    sys.exit(main())
