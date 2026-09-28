#!/usr/bin/env python3
"""Census the `pd` listings that carry no `ghidra-functions.csv` row, and what
the clustering does and does not do with them once they do.

`docs/findings/pd-common-address-attribution.md` closed by naming the
unannotated `pd` population as the thing that would turn issue #471's "latent
today" into a live figure change. That is the population this tool derives, so
the number the batch was sized by comes out of a committed tool rather than out
of somebody's arithmetic -- `merge_annotation_shards.py`'s `--census` mode says
why the repository wants it that way, and this is the same argument applied to a
different batch.

**The population is a set difference over matched addresses, not a subtraction.**
It is `ec/decompiled/pd/*.asm` minus the `pd` rows of the annotation CSV, keyed
on the address each filename already spells. Subtracting two totals would be the
same number on the current tree and would go wrong the first time a row named
an address with no listing behind it or a listing arrived with no row, which is
exactly the pair of ways a census of this kind is wrong quietly. Both are
reported separately rather than allowed to cancel.

**A `pd` listing with no row is *not found by this method*, never absent.** The
listing is a Ghidra function boundary, and it exists -- that is why the `.asm`
and the `.c` are committed. What is missing is a human reading of it. Every
figure below is a statement about `ghidra-functions.csv`, and none of them is a
statement about the PD program.

**The edge accounting is read with `group_functions`'s own reader, imported
rather than reimplemented.** `listing_calls()` is what the clustering walks, so
a second parse here would be a second, slightly different answer to "which edges
does the tool see" -- and the whole claim of the census is about what the
clustering does. Importing it is what makes "39 edges" and the clustering's
edge set the same 39 by construction rather than by agreement.

**`norm_addr` is the other import, and it is the one that could go wrong
quietly.** Two exist under that name: `citation_callers`' strips the `0x` and
zero-fills to four digits, `group_functions`' strips the prefix and does not.
On an address of four digits or more the two are the same function -- `0x06EA`
reads `06EA` under either, not `6EA` -- so the choice is not load-bearing for
any row as this CSV spells them today. They part company below four digits:
`0x1` is `0001` under the first and `1` under the second, and a row spelled
that way matches its listing under one and matches no listing at all under the
other, which reports a population too large by however many rows are spelled
short. The listing filename is the key and it is the four-digit spelling, so
this is `citation_callers`' either way; the `--self-test` asserts both the
agreement and the divergence so the choice is pinned rather than assumed.

**And the second half of the report is the null.** Issue #471's fix only shows
where a bank caller and a `pd` caller reach the same `common` row, and
`reached_only_by_bank` is a subset test over the banks. Seeding a `pd` row moves
neither: a `pd` caller whose target has a `pd` row takes the same-scope join, and
one whose target has not would take the proxy branch -- so the question is
whether any of these addresses carries a `common` row, and `common_rows()` is
reported per address for that reason. A figure that does not move is a result,
and the tool prints the reason next to the figure rather than leaving the reader
to guess which of the two halves of the mechanism was not exercised.

**What this is not.** Nothing here is a behavioural claim and no live test ran:
every input is a committed file, and no hardware is reachable from a
GitHub-hosted runner. A listing being unreached by the committed `lcall`/`ljmp`
operands says the graph does not reach it, not that the EC does not -- computed
targets (`sjmp @a+dptr`), a DPTR-carried bank-select target and the paged
`ajmp`/`acall` forms are all invisible to that reader, which is the first thing
`group_functions.py`'s own docstring lists among its blind spots.

**The edge count is exactly as complete as the `evidence` column, and that is
reported rather than assumed.** 67 of the committed rows cite a document and no
`.asm`, and `asm_path()` returns `None` for each, so the clustering walks none
of their edges and neither does this. That is a pre-existing property of
`ghidra-functions.csv` rather than anything this tool introduces, and it is left
alone here: repairing 67 rows' citations is a change to a shared file for
reasons unrelated to the `pd` population, and doing it in the same commit would
make the edge figure below mean two different things. It is reported, it wants
its own issue, and until it is repaired "39 edges" means *39 edges out of the
rows whose evidence names a listing*.

Usage:
    python3 pd_unannotated_census.py
    python3 pd_unannotated_census.py --self-test
"""
import argparse
import collections
import csv
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

# The four readers are group_functions' own, imported for the reason the module
# docstring gives: the census is about what the clustering sees, so a second
# parser would be answering a different question.
from citation_callers import iter_instructions, norm_addr  # noqa: E402
from group_functions import (asm_path, listing_calls,  # noqa: E402
                             read_csv, EC_CSV)

PD_DIR = os.path.join(REPO, "ec", "decompiled", "pd")

# Which program this census is about. Named rather than inferred from the
# directory listing, so pointing the tool at another program is an edit that
# gets read rather than an accident of which directories exist.
PROGRAM = "pd"


def listing_addresses(directory=PD_DIR):
    """Every committed listing under `directory`, as a sorted address list.

    `.asm` only, and the `.c` is deliberately not counted: the annotation CSV
    cites both and the two are one function, so counting both would double the
    population and then have to be divided back out. `missing_c_files()` is
    what checks the pair, separately.
    """
    return sorted(norm_addr(name[:-4])
                  for name in os.listdir(directory) if name.endswith(".asm"))


def missing_c_files(addresses=None, directory=PD_DIR):
    """Listings with no `.c` beside them.

    A separate report rather than a factor of two, because the claim "one
    listing is one function" rests on the pair holding and a census that
    assumed it would not notice if it stopped holding.
    """
    addresses = listing_addresses(directory) if addresses is None else addresses
    return [a for a in addresses
            if not os.path.isfile(os.path.join(directory, a + ".c"))]


def rows_by_scope(rows, scope):
    """{norm_addr: row} for one scope of the annotation CSV."""
    return {norm_addr(r["addr"]): r for r in rows if r["scope"] == scope}


def annotated_addresses(rows, scope=PROGRAM):
    return set(rows_by_scope(rows, scope))


def edges_from_annotated_rows(rows, targets, repo=REPO):
    """({target: [(caller scope, caller addr, site addr)]}, unreadable rows).

    One walk of every annotated row's own committed `.asm`, keeping only edges
    whose target is in `targets`. This is the accounting the issue is about: how
    many of the unannotated listings the graph already has an edge pointing at,
    and where those edges come from. A caller scope is recorded rather than
    folded into a total, because *which* region an edge starts in is what decides
    whether seeding the target can move a figure at all -- see the module
    docstring.

    **A row whose `evidence` names no `.asm` that exists contributes no edges,
    and the second return value is the count of those rows.** `asm_path()`
    returns `None` rather than raising, so a stale path would otherwise make
    this census quietly smaller without saying so. It is the same reason
    `census()` reports orphans instead of netting them out: a figure that is
    low for a reason nobody printed reads as a finding.
    """
    wanted = set(targets)
    inbound = collections.defaultdict(list)
    unreadable = 0
    for row in rows:
        path = asm_path(row, repo)
        if not path:
            unreadable += 1
            continue
        for site, called in listing_calls(path).items():
            for target in called:
                if target in wanted:
                    inbound[target].append((row["scope"],
                                            norm_addr(row["addr"]), site))
    return inbound, unreadable


def census(rows=None, directory=PD_DIR, scope=PROGRAM, repo=REPO):
    """The whole population, as a list of dicts in address order.

    Each carries what a decision about the row needs and nothing that is only
    interesting once: the address, the listing path, how many instructions it
    holds (which is what sizes the reading), the `seed_basis` the export
    recorded for it, whether a `common` row sits at the same address, and the
    inbound edges grouped by caller scope.

    `repo` is the root the rows' `evidence` paths resolve against, threaded
    rather than taken from the module so a fixture tree can be read through the
    same function the committed tree is. `asm_path()` already takes it.
    """
    rows = read_csv(EC_CSV) if rows is None else rows
    addresses = listing_addresses(directory)
    annotated = annotated_addresses(rows, scope)
    # Numerically, not as strings. The listing key is a four-digit filename and
    # the CSV address is normalized text; comparing the two as strings reads a
    # shared address as unshared and reports the overlap as zero, which is a
    # figure that looks like a result and is the opposite of one.
    common = {int(a, 16) for a in rows_by_scope(rows, "common")}

    unannotated = [a for a in addresses if a not in annotated]
    # Reported, not subtracted: a row naming an address with no listing is a
    # claim about a function the export no longer holds, and the difference is
    # the tool's business rather than the census's.
    orphans = sorted(annotated - set(addresses))
    inbound, unreadable = edges_from_annotated_rows(
        rows, [int(a, 16) for a in unannotated], repo)

    out = []
    for addr in unannotated:
        edges = inbound.get(int(addr, 16), [])
        out.append({
            "addr": addr,
            "path": os.path.join(directory, addr + ".asm"),
            "insns": instruction_count(os.path.join(directory, addr + ".asm")),
            "seed_basis": seed_basis(addr, scope, directory),
            "shared_with_common": int(addr, 16) in common,
            "inbound": edges,
            "callers": sorted({scope_ for scope_, _, _ in edges}),
        })
    return out, orphans, unreadable


def instruction_count(path):
    """How many instruction lines a listing holds.

    `iter_instructions` rather than a line count, so a header comment is not
    an instruction. A listing it reads none from is zero, which is a fact about
    the listing and not a failure of the read.
    """
    return sum(1 for _ in iter_instructions(path))


def seed_basis(addr, scope=PROGRAM, directory=PD_DIR):
    """The `seed_basis` the export recorded, read from `index.csv`.

    `vector` and `annotation` are the two the PD program uses for entries that
    no call census found, and they are worth seeing beside the address: a
    listing the export seeded as a vector slot is a table entry by construction,
    where an `auto` seed is a function boundary Ghidra proposed. Missing index
    reads as an empty cell rather than raising, so a fixture tree without one
    is a tree with nothing to say here.
    """
    path = os.path.join(os.path.dirname(directory), "index.csv")
    if not os.path.isfile(path):
        return ""
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("program") == scope and norm_addr(row["addr"]) == addr:
                return row.get("seed_basis", "")
    return ""


def report(census_rows, orphans, unreadable=0, scope=PROGRAM, out=sys.stdout):
    """Print the population and the edge accounting. Returns a verdict flag.

    The summary lines are the ones the write-up quotes, and the table beneath
    them is what they are a summary *of* -- a count with nothing behind it is
    the shape of claim this repository distrusts.
    """
    total = len(census_rows)
    reached = [r for r in census_rows if r["inbound"]]
    bare = [r for r in census_rows if not r["inbound"]]
    edges = sum(len(r["inbound"]) for r in census_rows)
    caller_scopes = collections.Counter(s for r in census_rows
                                        for s in r["callers"])
    shared = [r for r in census_rows if r["shared_with_common"]]

    print("ec/decompiled/%s listings with no ghidra-functions.csv row: %d"
          % (scope, total))
    print("  reached by an lcall/ljmp from an annotated row: %d "
          "(%d edge(s), callers %s)"
          % (len(reached), edges,
             ", ".join("%s=%d" % kv for kv in sorted(caller_scopes.items()))
             or "none"))
    print("  no annotated row reaches them:                  %d"
          % len(bare))
    print("  also carrying a `common` row:                   %d (%s)"
          % (len(shared), ", ".join(r["addr"] for r in shared) or "none"))
    print("  annotated rows naming an address with no listing: %d"
          % len(orphans))
    print("  annotated rows whose evidence names no .asm:    %d%s"
          % (unreadable,
             "  (cluster() skips these too, so the edge count is the"
             " clustering's, not a second reading of it)"
             if unreadable else ""))
    orphans_c = missing_c_files()
    if not orphans_c:
        print("  every listing has a .c beside it:               yes")
    else:
        print("  listings with no .c beside them:                 %d (%s)"
              % (len(orphans_c), ", ".join(orphans_c)))

    print("\n  addr  insns  seed        in  callers  also-common  name")
    for row in census_rows:
        print("  %s  %5d  %-11s %2d  %-8s  %-11s  %s"
              % (row["addr"], row["insns"], row["seed_basis"] or "-",
                 len(row["inbound"]),
                 ",".join(row["callers"]) or "-",
                 "yes" if row["shared_with_common"] else "no",
                 os.path.basename(row["path"])))

    print("\nA `common` row beside a `pd` listing is two functions in two "
          "programs, so seeding the\n`pd` side takes the same-scope join and "
          "the `common` row keeps its own reach.\nThat is why "
          "`reached_only_by_bank` cannot move: it is a subset test over\nthe "
          "banks, and a `pd` caller is not one. Run "
          "`group_functions.py --report` for the figures\nthis census is "
          "about, and `docs/findings/pd-unannotated-listings.md` for the\n"
          "measurement and what it does and does not establish.")
    return True


PLATE = ("; pd @ %s   %s\n"
         "; Ghidra disassembly, generated by build_ec_decompile.py -- do not "
         "edit.\n"
         "; This is the machine code.\n\n")


def write_listing(directory, addr, name, lines):
    """Write a minimal `.asm` and its `.c` into a fixture tree.

    The plate is two comment lines and a blank, because the reader skips `;`
    lines and reads the rest by column -- a fixture that omitted it would be
    testing a listing shape nothing in the repository has.
    """
    os.makedirs(directory, exist_ok=True)
    body = "".join("%-6s %-9s %-8s %s\n" % tuple(ln) for ln in lines)
    with open(os.path.join(directory, addr + ".asm"), "w") as f:
        f.write(PLATE % (addr, name) + body)
    with open(os.path.join(directory, addr + ".c"), "w") as f:
        f.write("/* %s */\n" % name)


def self_test(fh=sys.stdout):
    """The derivations, on a fixture tree whose answer is known.

    A census that reports a population cannot be checked by asserting the
    population -- that is a value every merge has to edit, and
    `ec/tools/test_check_pin_table_by_cited_file.py` has been that bug four
    times. What is checkable is the *derivation*, and it is checkable only by
    running `census()` itself: an earlier version of this asserted a set of
    expressions re-derived beside the real ones, and passed while `census()`
    compared an `int` against a set of address strings and reported every
    shared `common`/`pd` address as unshared. A self-test that re-derives the
    answer beside the code certifies the derivation, not the tool.

    So the fixture is a directory of listings, a set of annotation rows, and
    the one function that turns them into the report. Every case below is a
    shape the committed tree actually has.
    """
    checks = []

    def check(name, got, want):
        checks.append(name)
        if got != want:
            print("FAIL %s: got %r, want %r" % (name, got, want), file=fh)
            return 1
        return 0

    rc = 0

    # norm_addr is the key the whole population is matched on, and the CSV
    # spells an address with or without its 0x and in either case. The two
    # norm_addr in this repository agree at four digits and part company below
    # it, so the two cases below are the pair that pins which one this is: the
    # first passes under either implementation, the second does not.
    rc += check("norm_addr lower-cases, strips 0x and zero-fills",
                norm_addr("0x0ea2"), "0EA2")
    rc += check("norm_addr zero-fills a sub-four-digit address, which is what "
                "group_functions' would not do",
                norm_addr("0x1"), "0001")
    rc += check("norm_addr leaves a bare address alone",
                norm_addr("3497"), "3497")

    with tempfile.TemporaryDirectory() as tmp:
        # Laid out as a repository, because `asm_path()` resolves a row's
        # `evidence` against a repo root -- so the fixture has to have one, and
        # a tree that only looks like the right shape would test the shape.
        listing_dir = os.path.join(tmp, "ec", "decompiled", "pd")
        # 06EA carries a row, so it must not appear in the population. 0012 has
        # a `common` row at the same address and no `pd` one -- the conflation
        # this whole census is scoped around, and the case the re-derived
        # self-test missed. 1000 is reached by a `lcall` out of 06EA's listing,
        # so it must be reported as an edge with a caller scope. 2000 is
        # reached by nothing.
        write_listing(listing_dir, "0012", "FUN_CODE_0012",
                      [("0012", "ff - -", "mov", "R7, A")])
        write_listing(listing_dir, "06EA", "FUN_CODE_06ea",
                      [("06ea", "12 10 00", "lcall", "0x1000")])
        write_listing(listing_dir, "1000", "FUN_CODE_1000",
                      [("1000", "22 - -", "ret", "")])
        write_listing(listing_dir, "2000", "FUN_CODE_2000",
                      [("2000", "22 - -", "ret", "")])

        def ev(addr):
            return "ec/decompiled/%s/%s.asm; ec/decompiled/%s/%s.c" % (
                PROGRAM, addr, PROGRAM, addr)

        rows = [
            {"scope": PROGRAM, "addr": "0x06ea", "evidence": ev("06EA")},
            {"scope": "common", "addr": "0x0012", "evidence": ev("0012")},
            # A pd row at 0x3000 with no listing behind it: the reverse
            # difference, which a census that subtracted two totals would have
            # cancelled out. Its evidence resolves to nothing, so it is also
            # the row whose edges cannot be counted -- reported, not dropped.
            {"scope": PROGRAM, "addr": "0x3000", "evidence": ev("3000")},
        ]
        census_rows, orphans, unreadable = census(rows=rows,
                                                  directory=listing_dir,
                                                  repo=tmp)

        got = {r["addr"]: r for r in census_rows}

        # A `common` row does not annotate the `pd` listing at the same
        # address. Same address, separate program.
        rc += check("a common row does not annotate the pd side",
                    sorted(got), ["0012", "1000", "2000"])

        # The shared-address flag, which is the null result's whole mechanism.
        # Read from `census()`'s own output rather than recomputed.
        rc += check("a common row beside a pd listing is flagged",
                    got["0012"]["shared_with_common"], True)
        rc += check("an address with no common row is not flagged",
                    got["2000"]["shared_with_common"], False)

        # The edge, and the caller scope on it: which region an edge starts in
        # is what decides whether seeding the target can move a figure.
        rc += check("an lcall from an annotated row is one inbound edge",
                    len(got["1000"]["inbound"]), 1)
        rc += check("the caller's own scope is recorded",
                    got["1000"]["callers"], [PROGRAM])
        rc += check("a listing no annotated row reaches has no edge",
                    got["2000"]["inbound"], [])

        # Both halves of the difference are reported, not netted, and a row
        # whose evidence resolves to nothing is counted rather than quietly
        # contributing no edges.
        rc += check("a row with no listing is reported as an orphan",
                    orphans, ["3000"])
        rc += check("a row whose evidence resolves to nothing is counted",
                    unreadable, 1)

        # The instruction count is a read of the listing, not of its header.
        rc += check("instruction count ignores the plate",
                    got["2000"]["insns"], 1)
        rc += check("every fixture listing has a .c beside it",
                    missing_c_files(directory=listing_dir), [])

        # A `.c` missing from the pair is a fact about the tree, reported.
        os.remove(os.path.join(listing_dir, "2000.c"))
        rc += check("a listing with no .c is reported, not hidden",
                    missing_c_files(directory=listing_dir), ["2000"])

    if rc:
        print("%d of %d assertions FAILED" % (rc, len(checks)), file=fh)
        return 1
    print("all %d assertions passed" % len(checks), file=fh)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Census the pd listings with no annotation row.")
    parser.add_argument("--self-test", action="store_true",
                        help="check this tool's own derivations and exit")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    census_rows, orphans, unreadable = census()
    return 0 if report(census_rows, orphans, unreadable) else 1


if __name__ == "__main__":
    sys.exit(main())
