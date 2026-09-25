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
A/B/C edge populations, the cross-region count, the proxy count and the
ungrouped remainder split by reason, and `--check` refuses a `callgraph` group
that spans two banks. The rule is scoped to `callgraph` on purpose: a
`type`-seeded group can hold a bank0 row and a bank1 row, and that is two
functions happening to share a role rather than a merge, which is what a
role-based grouping means.

**The rule needed a node as well as an edge, so a bank caller's endpoint for a
common target is a per-bank proxy, not the common row.** A `common`-scoped row
is one function both bank images carry, so a bank0 caller and a bank1 caller
that both reach it were two halves of ONE node, and that node joined the two
banks however sound each edge is. The endpoint is a `PROXY_SCOPE` proxy now,
which keeps the relation the edge really does carry -- the bank0 functions
sharing this helper stay connected -- and drops the one it does not.

That makes the proxy the larger of the two discard populations on the committed
tree, 196 bank->common edges against 27 bank<->bank, so `--report` prints it
beside the cross-region count rather than letting the 27 stand as the rule's
whole accounting. It also bounds what a group is: a path between two members of
a `callgraph` group can run through a proxy that is not a member, so "mutually
reachable" is a property of the graph the union walked, not of a set of rows.

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

**And a non-bank caller scope on that proxy line is an annotation gap, not a
second kind of region.** This paragraph used to read that a `pd` caller's edge
to a `common`-scoped address "is a question about two separate programs" that
`region_of` has no word for. That was a conclusion about the *images* wearing
the clothes of a conclusion about the *rule*, and it was wrong: the proxy
branch is reached whenever the target has no row in the **caller's own** scope,
so for a `pd` caller it means "no `pd` row at that address" and nothing more.
The ITE8850-PD image does have its own address space -- `region_of` and the
`pd` grade rule both guard that -- but the branch never asks it. On the
committed tree the last such edge was `pd 0xCB2A` -> 0x11C2, and it was a
missing `ghidra-functions.csv` row: the `pd` listing at 0x11C2 is a two-key
return-address table dispatcher and the `common` row at the same address is a
bank-select trampoline, so annotating the `pd` one removed the edge rather
than reclassifying it. A `pd` listing with no row is **not found by this
method**, never absent from the PD program, and annotating the remaining
unlisted `pd` addresses is ordinary annotation work rather than a
classification problem. `--report` keeps the break-out for the case that comes
back, and names it as a gap so it cannot read as a banking result; see
`docs/findings/pd-common-address-spaces.md`.

Usage:
    python3 ec/tools/group_functions.py --report
    python3 ec/tools/group_functions.py --apply
    python3 ec/tools/group_functions.py --check
    python3 ec/tools/group_functions.py --self-test
"""
import argparse
import collections
import contextlib
import csv
import io
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

# The scope token a bank caller's endpoint in the common area is filed under.
# Not a scope any row carries, and not in `region_of`'s vocabulary: it names a
# per-bank stand-in for one common-area function, so that a bank0 caller and a
# bank1 caller of the same helper stay in their own bank's component. See
# `cluster()`, which is the only thing that builds one.
PROXY_SCOPE = "%s#common"

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

# What the banking rule discarded, as one value the report and `group_rows()`
# can both ask about. Two populations, because the rule cuts edges two ways and
# reporting one of them as if it were the whole cost is what made 27 look like
# the accounting for a rule that cuts 196 as well.
#
#   `cross_region` -- bucket-B edges whose target also exists in the other
#     bank, i.e. the ones the same-bank assumption decides and this tool
#     cannot.
#   `proxy_edges` / `proxy_by_caller` -- edges a caller had to a `common` row,
#     replaced by a per-bank proxy. Broken out by caller scope because a
#     non-bank scope here is an ANNOTATION GAP rather than a banking result --
#     the branch is reached when the target has no row in the caller's own
#     scope, which for `pd` means no `pd` row, not a different program -- and
#     by target address because the edge total is not the row total: the edges
#     spread over every `common` row they land on, found-then-cut or not.
#   `reached_only_by_bank` -- annotated `common` rows whose caller scopes are
#     a non-empty subset of the banks, i.e. the rows this method DID find and
#     then cut. Non-empty matters: a row no caller reaches at all is not
#     "reached only by bank callers", it is unreached.
ClusterStats = collections.namedtuple(
    "ClusterStats",
    "cross_region proxy_edges proxy_by_caller proxy_by_target "
    "reached_only_by_bank")


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
    region are counted and reported, never merged, and the calling scope is
    recorded against an annotated `common` target on whichever branch ended
    there, so the report can say which rows the method found and the rule then
    cut.

    "Never sees a cross-region edge" is about the union, and an edge to a
    common-area function is where that promise was being broken without
    `--check` noticing: a `common`-scoped row is one function both images
    carry, so a bank0 caller and a bank1 caller that both reach it were two
    halves of one node, and that node joined the two banks. With the EC's
    common area 43 annotated there was nothing dense enough to bridge them
    and the committed groups happened to pass; issue #134's 33 more made the
    bridge and `cross_bank_groups` refused the result. The endpoint is a
    per-bank proxy node now (`PROXY_SCOPE`), which is still a node the union
    never joins across regions -- it is how the invariant was made true
    rather than lucky."""
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
    real = set()
    for row in rows:
        key = (row["scope"], norm_addr(row["addr"]))
        find(key)
        real.add(key)
        by_addr[row["scope"]][norm_addr(row["addr"])] = row

    cross_region = 0
    # Which caller scopes reach each annotated `common` address, how many bank
    # callers' edges were replaced by a proxy, and which rows those edges
    # landed on. Collected in the same walk as the union rather than by a
    # second pass over the listings: a second read is a second chance to
    # measure a different population from the one the clustering used, and
    # these figures are reported beside it.
    #
    # The per-target counts are what keep the two apart. `proxy_edges` is a
    # population of EDGES and `reached_only_by_bank` one of ROWS, and on the
    # committed tree the edges spread over more rows than the report line for
    # `reached_only_by_bank` names -- so quoting the edge count for a row
    # population is the same partial accounting this report exists to stop,
    # one level down.
    reach = collections.defaultdict(set)
    proxy_by_caller = collections.Counter()
    proxy_by_target = collections.Counter()
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
                taddr = "%04X" % target
                # Recorded on the branches whose edge really does end at the
                # `common` row, not before the join decision. An address
                # carrying a `common` row and a row of the caller's own scope
                # is two different functions -- `pd/0C7A.asm` is not
                # `common/0C7A.asm`, and the separate ITE8850-PD image has its
                # own address space -- and a same-scope join took the other
                # program's row as its endpoint, so recording the caller
                # scope against the `common` row there was attributing an edge
                # to a row the edge never touched.
                #
                # The `common` case is why the reach is recorded at all on this
                # branch: both ends are `common`, so the edge is joined
                # directly rather than proxied, but it still says the row was
                # reached from outside the banks, which is what keeps it out
                # of `reached_only_by_bank`. The guard is load-bearing, not
                # cosmetic -- dropping it loses the 30 common->common edges on
                # the committed tree, takes `reached_only_by_bank` from 26 to
                # 35, and fails --self-test.
                if taddr in by_addr.get(scope, {}):
                    union(caller, (scope, taddr))
                    if scope == "common":
                        reach[taddr].add(scope)
                elif taddr in by_addr.get("common", {}):
                    # A common-area row is one function that both bank images
                    # carry, so a bank0 caller and a bank1 caller that both
                    # reach it are two halves of ONE node -- and joining them
                    # to it is how bank0 and bank1 end up in one component,
                    # which is the join this tool exists to refuse. The
                    # annotation says `common`, which is exactly as
                    # unattributable as having no row at all: nothing here
                    # records which bank ran the call. So a bank caller's
                    # endpoint is a PROXY, one per bank, which keeps the
                    # relation this edge really does carry (the bank0
                    # functions that share this helper are connected) and
                    # drops the one it does not (that they are connected to
                    # the bank1 ones through it).
                    #
                    # A `common`-scoped caller never reaches this branch: its
                    # own scope is "common", so the line above unions it to
                    # the real common row, which is right -- both banks
                    # carrying a function is not the same function being
                    # called by both.
                    union(caller, (PROXY_SCOPE % scope, taddr))
                    # The proxy replaces the common row as this edge's
                    # endpoint, but the common row is the row this address
                    # means, so the caller's scope is recorded against it:
                    # this is the population `reached_only_by_bank` is the
                    # other half of.
                    reach[taddr].add(scope)
                    proxy_by_caller[scope] += 1
                    proxy_by_target[taddr] += 1
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
        # The proxy endpoints above are not rows. They hold a component
        # together and are dropped from it, so a group's members, its name
        # and its reported size all stay counts of annotated functions.
        if key not in real:
            continue
        clusters[find(key)].append(key)
    # A non-empty subset of the banks: at least one bank caller, and nobody
    # outside them. The `scopes and` is the difference between "the method
    # found this and the rule cut it" and "no caller was found for it at all",
    # which is a different row in a different column of the report.
    stats = ClusterStats(
        cross_region=cross_region,
        proxy_edges=sum(proxy_by_caller.values()),
        proxy_by_caller=proxy_by_caller,
        proxy_by_target=proxy_by_target,
        reached_only_by_bank={taddr for taddr, scopes in reach.items()
                              if scopes and scopes <= set(BANKS)})
    return clusters, stats


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
    the same rule that put `unresolved` in the `type` vocabulary.

    `ungrouped` is a result, not a failure, and it is not one reason. A row no
    caller reaches was not found by this method; a `common` row reached only by
    bank callers WAS found, and the per-bank proxy rule is what cut the edges.
    The two get different comments, because on the second row `ungrouped` says
    nothing about the method and everything about the rule -- and a comment
    reading "not found by this method" there is a claim the tool's own edge
    list contradicts."""
    seeds = seed_groups(rows)
    if is_bios:
        for row in rows:
            seeds.setdefault((row["scope"], norm_addr(row["addr"])),
                             (row["scope"], "module",
                              "The module is the grouping: the export is "
                              "per-module and the module name is the real "
                              "structural layer the BIOS has."))
    clusters, stats = cluster(rows, repo, min_size)
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
        elif key[0] == "common" and key[1] in stats.reached_only_by_bank:
            out[key] = ("ungrouped", "ungrouped",
                        "No typed seed and no connected component at or above "
                        "the minimum size. This row WAS found: its callers are "
                        "all bank rows, and the per-bank proxy rule cut every "
                        "edge to it rather than join the banks through a "
                        "common-area node. The reason is the rule, not the "
                        "method.",
                        row.get("evidence", ""))
        else:
            out[key] = ("ungrouped", "ungrouped",
                        "No typed seed and no connected component at or above "
                        "the minimum size. Not found by this method.",
                        row.get("evidence", ""))
    return out, stats


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
    """Pin the no-cross-bank rule, the seeds, the vocabulary, and what the
    report says about the edges the rule discarded.

    The fixture is a graph with a KNOWN cross-bank edge, because the whole
    claim of this tool is that it refuses to join across one.

    The refusal is not the only thing pinned. The proxy fixtures below also pin
    the figures a reader sees, because a `--report` that quietly stopped
    printing the proxy population would leave the tool correct and its
    accounting wrong again, which is the shape of the bug this pass exists to
    fix."""
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
    grouped, stats = group_rows(rows, repo=REPO, min_size=2)
    g00 = grouped[("bank0", "8000")][0]
    g10 = grouped[("bank1", "8100")][0]
    check("a bucket-B edge into the other bank is not joined",
          g00 != g10,
          "(bank0 0x8000 and bank1 0x8100 must not share a group: the same "
          "three bytes name a same-bank call)")
    check("the cross-region edge is counted",
          stats.cross_region == 1, "(got %r)" % (stats.cross_region,))

    # The same two bank0 rows, with no bank1 row to tempt it, DO cluster.
    two = [r for r in rows if r["scope"] == "bank0"]
    grouped2, _ = group_rows(two, repo=REPO, min_size=2)
    check("a same-region edge still clusters",
          grouped2[("bank0", "8000")][0] == grouped2[("bank0", "8100")][0])

    # The same caveat one level down, and the case `cross_bank_groups`
    # actually refused once issue #134 annotated 33 more of the common area:
    # a bank0 caller and a bank1 caller that BOTH reach one annotated
    # `common` function. That function is one function both images carry, so
    # a single node for it is how the two banks' graphs became one component.
    # Two callers a side, so each bank's component clears min_size=2 and the
    # assertion is about the grouping rather than about falling through to
    # `ungrouped`.
    def bridge_row(scope, addr, name, fname):
        return {"scope": scope, "addr": addr, "name": name, "type": "logic",
                "evidence": os.path.relpath(
                    asm(fname, ["%s     12 05 e8 lcall    0x05E8" % addr, RET]),
                    REPO)}

    bridge = [
        bridge_row("bank0", "8000", "b0_caller_a", "bridge_b0a.asm"),
        bridge_row("bank0", "8100", "b0_caller_b", "bridge_b0b.asm"),
        bridge_row("bank1", "8000", "b1_caller_a", "bridge_b1a.asm"),
        bridge_row("bank1", "8100", "b1_caller_b", "bridge_b1b.asm"),
        {"scope": "common", "addr": "05E8", "name": "critical_section_enter",
         "type": "gate", "evidence": os.path.relpath(
             asm("bridge_common.asm", [RET]), REPO)},
    ]
    grouped3, stats3 = group_rows(bridge, repo=REPO, min_size=2)
    check("one annotated common function reached from both banks is not a "
          "bridge between them",
          grouped3[("bank0", "8000")][0] != grouped3[("bank1", "8000")][0],
          "(both banks' 0x8000 call 0x05E8; nothing in either listing says "
          "which image ran it, so the two must not share a group)")
    # ... and the relation the edge really does carry survives: the callers
    # that share a common helper, within one bank, are connected through the
    # proxy rather than the edge being dropped.
    check("two bank0 callers of the same common helper still cluster",
          grouped3[("bank0", "8000")][0] == grouped3[("bank0", "8100")][0],
          "(the per-bank proxy is a node, not a dropped edge)")
    check("two bank1 callers of the same common helper still cluster",
          grouped3[("bank1", "8000")][0] == grouped3[("bank1", "8100")][0])
    # The proxy is not a row, so it cannot reach a group file and inflate a
    # group's size or name.
    check("the proxy endpoint is not itself a grouped row",
          set(grouped3) == {("bank0", "8000"), ("bank0", "8100"),
                            ("bank1", "8000"), ("bank1", "8100"),
                            ("common", "05E8")},
          "(got %r)" % (sorted(grouped3),))

    # ... and the rule's COST is counted, separately from the cross-region
    # count, because on the committed tree it is the larger of the two and a
    # report offering only the 27 would read as though the rule's whole
    # accounting were 27. Four callers reach 0x05E8 and every one of those
    # edges became a proxy; none of them is a bucket-B edge, so the two
    # populations do not overlap and the cross-region count stays 0 here.
    check("the proxy edges are counted as their own population",
          stats3.proxy_edges == 4,
          "(got %r; four callers reach 0x05E8, so four edges were proxied)"
          % (stats3.proxy_edges,))
    check("the proxy count is broken down by caller scope",
          dict(stats3.proxy_by_caller) == {"bank0": 2, "bank1": 2},
          "(got %r)" % (dict(stats3.proxy_by_caller),))
    # ... and by the target each edge landed on, because the edge total and the
    # row populations below are not the same number and the report has to be
    # able to say so. Four edges, one target row: on the committed tree the
    # same shape is 196 edges over 36 rows, and a reader given only the 196
    # for a row population would read the edge total as the row count.
    check("the proxy count is broken down by target row",
          dict(stats3.proxy_by_target) == {"05E8": 4},
          "(got %r; the four proxied edges all target 0x05E8, so the edge "
          "total and the target count are 4 and 1 respectively)"
          % (dict(stats3.proxy_by_target),))
    check("a proxied common target is not also a cross-region edge",
          stats3.cross_region == 0,
          "(got %r; 0x05E8 is below the bank base, so no bank call here is a "
          "bucket-B edge)" % (stats3.cross_region,))
    check("a common row only bank callers reach is reported as found-then-cut",
          stats3.reached_only_by_bank == {"05E8"},
          "(got %r; a `common` row reached by both banks and nobody else is "
          "exactly the population the generic 'not found by this method' "
          "comment gets wrong)" % (sorted(stats3.reached_only_by_bank),))
    # The row's own comment carries the reason, because a CSV row is read
    # without the report beside it. The basis stays `ungrouped` -- it asserts
    # no membership, which is what `cross_bank_groups` relies on -- so the
    # reason lives here and not in a new basis.
    check("the found-then-cut row keeps the ungrouped basis",
          grouped3[("common", "05E8")][1] == "ungrouped")
    check("the found-then-cut row's comment names the rule, not the method",
          "per-bank proxy rule" in grouped3[("common", "05E8")][2]
          and "Not found by this method" not in grouped3[("common", "05E8")][2],
          "(got %r)" % (grouped3[("common", "05E8")][2],))
    # The 26-figure definition, pinned on the half of it that is easy to get
    # wrong: one `common` caller is enough to take a row OUT of the population.
    # That edge is joined directly rather than proxied (both ends are `common`,
    # so no bank is implicated), but it still says the row is reached from
    # outside the banks, and calling it "reached only by bank callers" would
    # be a claim about its callers the edge list contradicts.
    mixed = list(bridge) + [
        {"scope": "common", "addr": "0100", "name": "c_caller", "type": "logic",
         "evidence": os.path.relpath(
             asm("bridge_common_caller.asm",
                 ["0100     12 05 e8 lcall    0x05E8", RET]), REPO)}]
    grouped4, stats4 = group_rows(mixed, repo=REPO, min_size=2)
    check("a common row a common caller also reaches is not found-then-cut",
          stats4.reached_only_by_bank == set(),
          "(got %r; the 26 counts rows whose callers are a subset of the "
          "banks, and a `common` caller is outside them)" % (
              sorted(stats4.reached_only_by_bank),))
    check("adding a common caller proxies no more edges",
          stats4.proxy_edges == 4,
          "(got %r; a common->common edge is joined directly, so it is not "
          "this population)" % (stats4.proxy_edges,))
    # The same four edges, now attributed to a row population they do not
    # belong to. This is the half of the split that a report giving only the
    # edge total gets wrong: the 196 is a population of edges and it reaches
    # rows the method found AND rows a non-bank caller also reaches, so it is
    # not the accounting for either of them.
    check("a proxied edge is still attributed to its target row",
          dict(stats4.proxy_by_target) == {"05E8": 4},
          "(got %r; the common->common edge is joined directly, so the target "
          "count is unchanged)" % (dict(stats4.proxy_by_target),))

    # A `common` row and a `pd` row at the SAME address, reached by a bank0
    # caller and by a `pd` caller. `ec/decompiled/pd/0C7A.asm`
    # (`mul_r7_r5_r4_into_r6r7`) is a different function from
    # `ec/decompiled/common/0C7A.asm` (`clear_low_nibble_of_1304`) -- the
    # ITE8850-PD image is a separate program with its own address space -- so a
    # same-scope `pd` join takes the `pd` row as its endpoint and the `common`
    # row at that address is not an endpoint of that edge at all.
    #
    # The bank0 caller is what makes this discriminate, and it is worth saying
    # why, because the obvious version of the fixture does not. A `pd`-ONLY
    # reach is invisible either way: `reached_only_by_bank` is a subset test
    # that already discards any non-bank scope, so asserting "a pd caller does
    # not put the row in reached_only_by_bank" passes against the bug it is
    # written for. The reach is a SET, so what separates the two behaviours is
    # a bank reach on the same row:
    #     ['bank0', 'pd']  (the bug) -> not a subset of the banks -> not here
    #     ['bank0']        (the fix) -> a subset of the banks     -> here
    shared = [
        # No bank0 row at 0x06A0, so this caller's endpoint really is the
        # `common` row, and the edge is proxied.
        {"scope": "bank0", "addr": "8000", "name": "b0_shared_caller",
         "type": "logic", "evidence": os.path.relpath(
             asm("shared_b0.asm", ["8000     12 06 a0 lcall    0x06A0", RET]),
             REPO)},
        # A `pd` row at 0x06A0, so this caller's endpoint is the `pd` row.
        {"scope": "pd", "addr": "8100", "name": "pd_shared_caller",
         "type": "logic", "evidence": os.path.relpath(
             asm("shared_pd.asm", ["8100     12 06 a0 lcall    0x06A0", RET]),
             REPO)},
        {"scope": "common", "addr": "06A0", "name": "shared_common_row",
         "type": "logic", "evidence": os.path.relpath(
             asm("shared_common.asm", [RET]), REPO)},
        {"scope": "pd", "addr": "06A0", "name": "shared_pd_row",
         "type": "logic", "evidence": os.path.relpath(
             asm("shared_pd_row.asm", [RET]), REPO)},
    ]
    grouped5, stats5 = group_rows(shared, repo=REPO, min_size=2)
    check("a pd->pd join at an address that also carries a common row is not "
          "a reach of the common row",
          stats5.reached_only_by_bank == {"06A0"},
          "(got %r; the bank0 caller's edge targets the common row and the pd "
          "caller's joins the pd row, so the common row's callers are exactly "
          "the banks)" % (sorted(stats5.reached_only_by_bank),))
    check("the pd caller's edge at a shared address is joined, not proxied",
          dict(stats5.proxy_by_target) == {"06A0": 1}
          and dict(stats5.proxy_by_caller) == {"bank0": 1},
          "(got %r by target, %r by caller; a same-scope join is a join, so "
          "only the bank0 edge is the rule's to cut)"
          % (dict(stats5.proxy_by_target), dict(stats5.proxy_by_caller)))
    check("the common row and the pd row at a shared address stay distinct",
          grouped5[("common", "06A0")][0] != grouped5[("pd", "06A0")][0],
          "(one address is not one function across two programs)")

    # The `pd` edge that DOES reach the proxy branch: no `pd` row at the
    # target, so the `pd` caller's endpoint is the `common` row and the reach
    # is real. The bank0 caller is here for the same reason as above -- a
    # `pd`-only reach is not observable through `reached_only_by_bank` at all,
    # so this pins the attribution the way the surface can: with a bank reach
    # beside it, the row must fall OUT of the population, and a `pd` reach that
    # is dropped rather than recorded wrongly is the failure this catches.
    #
    # This is the shape the committed `pd 0xCB2A` -> 0x11C2 edge had, and it is
    # kept as a fixture after that row was annotated. The rule does not change
    # and the edge is not a special case: the target simply has no row in the
    # caller's own program, which is an annotation gap. The one thing that
    # changed is the reading -- the branch is not a program boundary the banking
    # rule cannot describe, and nothing about the two images' address spaces
    # makes it one.
    boundary = [
        {"scope": "bank0", "addr": "8000", "name": "b0_boundary_caller",
         "type": "logic", "evidence": os.path.relpath(
             asm("boundary_b0.asm", ["8000     12 06 b0 lcall    0x06B0", RET]),
             REPO)},
        {"scope": "pd", "addr": "8100", "name": "pd_boundary_caller",
         "type": "logic", "evidence": os.path.relpath(
             asm("boundary_pd.asm", ["8100     12 06 b0 lcall    0x06B0", RET]),
             REPO)},
        {"scope": "common", "addr": "06B0", "name": "boundary_common_row",
         "type": "logic", "evidence": os.path.relpath(
             asm("boundary_common.asm", [RET]), REPO)},
    ]
    _grouped6, stats6 = group_rows(boundary, repo=REPO, min_size=2)
    check("a pd caller's edge to a common row with no pd row beside it is "
          "still a reach of that row",
          stats6.reached_only_by_bank == set(),
          "(got %r; the pd caller is outside the banks, so the row is not a "
          "found-then-cut row however the join was taken)"
          % (sorted(stats6.reached_only_by_bank),))
    check("both edges to an unlisted-in-the-caller's-program target are counted "
          "by the proxy rule",
          dict(stats6.proxy_by_caller) == {"bank0": 1, "pd": 1}
          and dict(stats6.proxy_by_target) == {"06B0": 2},
          "(got %r by caller, %r by target; the pd edge is an annotation gap "
          "and is counted rather than hidden, and neither scope is a bank)"
          % (dict(stats6.proxy_by_caller), dict(stats6.proxy_by_target)))

    # The two halves of the reading, as a pair, because each one alone is a
    # fixture that passes for the wrong reason. The committed `pd 0xCB2A` ->
    # 0x11C2 edge was the second shape, and annotating `pd 0x11C2` took it off
    # the report; the first shape is what the other six `pd` edges to an
    # annotated `common` address already did. What makes this a pair is that the
    # only difference between them is whether the target carries a row in the
    # CALLER'S OWN SCOPE, and the branch does not look at anything else -- not
    # at which image the caller is in, and not at whether the two images happen
    # to overlap at that address.
    joined_pd = [
        {"scope": "pd", "addr": "8100", "name": "pd_joined_caller",
         "type": "logic", "evidence": os.path.relpath(
             asm("gap_pd_joined.asm", ["8100     12 06 c0 lcall    0x06C0", RET]),
             REPO)},
        # A `pd` row at the target and NO `common` row beside it, so the
        # same-scope join is the only branch available and the proxy rule is
        # never reached.
        {"scope": "pd", "addr": "06C0", "name": "pd_joined_target",
         "type": "logic", "evidence": os.path.relpath(
             asm("gap_pd_joined_target.asm", [RET]), REPO)},
    ]
    grouped7, stats7 = group_rows(joined_pd, repo=REPO, min_size=2)
    check("a pd caller whose target has a pd row proxies nothing",
          stats7.proxy_edges == 0
          and dict(stats7.proxy_by_caller) == {}
          and dict(stats7.proxy_by_target) == {},
          "(got %r edge(s), %r by caller; the edge joins the pd row, so the "
          "banking rule is not what handles it)"
          % (stats7.proxy_edges, dict(stats7.proxy_by_caller)))
    check("a pd caller whose target has a pd row joins it directly",
          grouped7[("pd", "8100")][0] == grouped7[("pd", "06C0")][0],
          "(the two must share a component; the proxy node is what a gap would "
          "have inserted between them)")

    # ... and the gap shape: same caller, a target with a `common` row and no
    # `pd` row. No bank caller here, which is the half that makes the printed
    # wording unambiguous -- with a bank edge in the same population the reader
    # cannot tell which scope the annotation-gap sentence is about.
    gap_pd = [
        {"scope": "pd", "addr": "8100", "name": "pd_gap_caller",
         "type": "logic", "evidence": os.path.relpath(
             asm("gap_pd.asm", ["8100     12 06 d0 lcall    0x06D0", RET]),
             REPO)},
        {"scope": "common", "addr": "06D0", "name": "gap_common_target",
         "type": "logic", "evidence": os.path.relpath(
             asm("gap_common.asm", [RET]), REPO)},
    ]
    grouped8, stats8 = group_rows(gap_pd, repo=REPO, min_size=2)
    check("a pd caller whose target has only a common row proxies one edge",
          stats8.proxy_edges == 1
          and dict(stats8.proxy_by_caller) == {"pd": 1}
          and dict(stats8.proxy_by_target) == {"06D0": 1},
          "(got %r edge(s), %r by caller; the target has no row in the "
          "caller's own program, so the edge ends at the proxy)"
          % (stats8.proxy_edges, dict(stats8.proxy_by_caller)))
    # The report half. A `pd=1` inside the `bank->common` parenthetical is what
    # let a banking label absorb an annotation gap, so the wording is asserted
    # rather than left to the next reader: the scope is named as a NON-BANK
    # caller scope, and the line below says what that is.
    out_gap = io.StringIO()
    with contextlib.redirect_stdout(out_gap):
        report(grouped8, stats8, gap_pd, repo=REPO)
    printed_gap = out_gap.getvalue()
    for label, needle in (
            ("the proxy total is unchanged by the split",
             "cut by the per-bank proxy rule: 1"),
            ("a non-bank caller scope is not printed as a bank term",
             "1 non-bank caller scope(s) (pd=1)"),
            ("the non-bank scope is named as an annotation gap",
             "that is an annotation gap rather than a banking result"),
            ("the gap is stated as a missing row in the caller's own program",
             "the target has no row in the caller's own program"),
            ("the gap is stated as not-found rather than absent",
             "never absent from the PD program"),
    ):
        check("the report prints %s for a non-bank caller scope" % label,
              needle in printed_gap,
              "(looked for %r in:\n%s)" % (needle, printed_gap))
    check("a non-bank caller scope is not printed inside the bank terms",
          "pd=1" not in printed_gap.split("non-bank caller scope(s)")[0]
          .split("per-bank proxy rule:")[1],
          "(the bank parenthetical must carry bank scopes only, or a gap reads "
          "as a banking result)")

    # What a reader can SEE. The refusal fixtures above all pass on a report
    # that says nothing about any of this, which is exactly how 27 came to
    # stand for the whole cost of the rule: the tool was right and its
    # accounting was not. So the printed figures are asserted, not just the
    # numbers behind them.
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        report(grouped3, stats3, bridge, repo=REPO)
    printed = out.getvalue()
    for label, needle in (
            ("the cross-region population",
             "cross-region edges counted, not joined: 0"),
            ("the proxy population", "cut by the per-bank proxy rule: 4"),
            ("the proxy per-caller breakdown", "bank0=2, bank1=2"),
            ("the distinct rows the proxied edges reach",
             "Those 4 edges reach 1 distinct common target(s)"),
            ("the proxied edges split by the row population they land on",
             "4 land on rows reached only by bank callers, 0 on rows a "
             "non-bank caller also reaches"),
            ("the found-then-cut rows", "reached only by bank callers: 1"),
            ("the split ungrouped line",
             "ungrouped: 1 (0 not found by this method + 1 found then cut"),
            ("the proxied edges reaching the found-then-cut rows",
             "reached by 4 of the 4 proxied edges"),
    ):
        check("the report prints %s" % label, needle in printed,
              "(looked for %r in:\n%s)" % (needle, printed))
    # The same report for the `common`-caller fixture, where the four edges
    # reach a row no bank caller reaches alone. Without this half, a report
    # that attributed every proxied edge to the found-then-cut rows would
    # still pass the assertions above.
    out4 = io.StringIO()
    with contextlib.redirect_stdout(out4):
        report(grouped4, stats4, mixed, repo=REPO)
    printed4 = out4.getvalue()
    for label, needle in (
            ("the distinct rows the proxied edges reach",
             "Those 4 edges reach 1 distinct common target(s)"),
            ("the proxied edges attributed to a non-bank-reached row",
             "0 land on rows reached only by bank callers, 4 on rows a "
             "non-bank caller also reaches"),
    ):
        check("the report prints %s when a non-bank caller also reaches it"
              % label, needle in printed4,
              "(looked for %r in:\n%s)" % (needle, printed4))

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
    # The other half of the split, and the reason it is asserted separately:
    # giving `ungrouped` a second reason must not quietly take the first one
    # away from the rows that still are "not found by this method".
    check("a row the method did not reach keeps the generic reason",
          "Not found by this method" in small[0][("bank0", "163C")][2]
          and "proxy rule" not in small[0][("bank0", "163C")][2],
          "(got %r)" % (small[0][("bank0", "163C")][2],))

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


def report(grouped, stats, rows, repo=REPO, is_bios=False):
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
              "job. A path between two members can run through a per-bank "
              "proxy node that is not a member itself."
              % (len(big), ", ".join("%s=%d" % (g, n) for g, n in big[:3])))
    print("    call-edge buckets (audit_call_targets.py's): "
          + " ".join("%s=%d" % (b, buckets[b]) for b in "ABC" if buckets[b]))
    # The two discard populations, printed together because one of them is
    # seven times the other and the banking rule cut both. A report that
    # printed only the cross-region count would read as though that were the
    # rule's whole accounting, which is the claim this line exists to stop.
    #
    # The proxy line then says which ROWS its edges landed on. Without that,
    # the only number a reader can attach to a row population is the edge
    # total, which on the committed tree is the whole 195 for a reason the
    # total does not describe: the edges spread over every `common` row they
    # reach, so the 16 found-then-cut `ungrouped` rows and the 9 rows a
    # non-bank caller also reaches are both inside it.
    cut_targets = stats.reached_only_by_bank
    cut_edges = sum(n for target, n in stats.proxy_by_target.items()
                    if target in cut_targets)
    # The per-caller breakdown, split on the one distinction that changes what
    # the number means. A bank scope is the rule doing its job; a non-bank
    # scope is the same rule standing in for a row the caller's own program does
    # not have, which on this tree is an annotation gap. They are printed as
    # separate terms rather than as one `pd=1` inside a `bank->common`
    # parenthetical, because a `bank->common` label absorbs a `pd=N` silently:
    # the reader sees a banking figure and a caller scope they cannot reconcile
    # with it. The count is still the whole population either way, so the terms
    # sum to the headline and the breakdown is not a second, smaller number.
    bank_callers = {s: n for s, n in stats.proxy_by_caller.items()
                    if s in BANKS}
    other_callers = {s: n for s, n in stats.proxy_by_caller.items()
                     if s not in BANKS}
    terms = ["%s=%d" % (s, n) for s, n in sorted(bank_callers.items())]
    if other_callers:
        terms.append("%d non-bank caller scope(s) (%s)"
                     % (sum(other_callers.values()),
                        ", ".join("%s=%d" % (s, n)
                                  for s, n in sorted(other_callers.items()))))
    print("    cross-region edges counted, not joined: %d" % stats.cross_region)
    print("    bank->common edges cut by the per-bank proxy rule: %d (%s). A "
          "bank caller's endpoint for a common target is that bank's proxy, "
          "not the common row, so the two banks are not joined through it. "
          "Those %d edges reach %d distinct common target(s): %d land on rows "
          "reached only by bank callers, %d on rows a non-bank caller also "
          "reaches."
          % (stats.proxy_edges, ", ".join(terms) or "none",
             stats.proxy_edges, len(stats.proxy_by_target), cut_edges,
             stats.proxy_edges - cut_edges))
    if other_callers:
        # Named as a gap rather than left for the reader to work out, because
        # the alternative is the reading this line used to invite: that a
        # non-bank caller scope is a second kind of region the banking rule
        # cannot describe. The branch does not ask that question. It is asked
        # when the target has no row in the caller's own scope, and a `pd`
        # listing with no row is not found by this method -- never absent from
        # the PD program, and never a claim about which bank ran anything.
        print("    %d of the %d proxied edges have a non-bank caller scope, and "
              "that is an annotation gap rather than a banking result: the "
              "target has no row in the caller's own program, so the row the "
              "edge lands on is another image's function. Annotating the "
              "listing joins the edge directly and drops it out of this line. A "
              "listing with no row is not found by this method, never absent "
              "from the PD program; see "
              "docs/findings/pd-common-address-spaces.md."
              % (sum(other_callers.values()), stats.proxy_edges))
    if stats.reached_only_by_bank:
        print("    annotated common rows reached only by bank callers: %d. The "
              "method found these and its own banking rule then cut the edges, "
              "which is a different reason from not being found."
              % len(stats.reached_only_by_bank))
    ungrouped = counts.get("ungrouped", 0)
    # Split by the reason the row carries, so the two populations sum to the
    # headline rather than one of them being an unexplained remainder. These
    # rows also carry their share of the proxy edges, so the headline can be
    # read against the edge total above: the 16 are a subset of what those
    # edges reach, not the whole of it.
    ungrouped_cut = {key[1] for key, value in grouped.items()
                     if value[0] == "ungrouped" and key[0] == "common"
                     and key[1] in stats.reached_only_by_bank}
    cut = len(ungrouped_cut)
    ungrouped_cut_edges = sum(stats.proxy_by_target.get(target, 0)
                              for target in ungrouped_cut)
    print("    ungrouped: %d (%d not found by this method + %d found then cut "
          "by the proxy rule, reached by %d of the %d proxied edges, never "
          "'absent')"
          % (ungrouped, ungrouped - cut, cut, ungrouped_cut_edges,
             stats.proxy_edges))


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
        grouped, stats = group_rows(rows, REPO, is_bios)
        if args.apply:
            write_groups(groups_path, rows, grouped)
        print("%s -- %s" % (os.path.relpath(groups_path, REPO),
                            "wrote" if args.apply else "proposed"))
        report(grouped, stats, rows, REPO, is_bios)
    return 0


if __name__ == "__main__":
    sys.exit(main())
