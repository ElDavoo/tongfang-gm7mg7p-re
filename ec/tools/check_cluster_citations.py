#!/usr/bin/env python3
"""Check every `main-ec-NNN` cluster citation in the prose against the census.

A cluster id in a sentence is a pointer: a reader who follows it into
`ec/annotations/xdata-clusters.csv` has to land on the membership the sentence
describes. Issue #253 is four sentences where the pointer drifted — the ids
moved when issue #4.3's census regeneration landed (#133 / #238), and prose
written against the old numbering kept the old ids. The ids are numbered by
size, then references, then lowest address (`xdata_register_map.py:1027`),
which makes them stable across regenerations *of one tool version* and says
nothing about staying put across a change to the tool's own classifier.

So this walks the committed markdown under `ec/`, `docs/` and `evidence/`,
finds every unit that names one or more `main-ec-NNN` clusters and one or more
XDATA addresses, and holds it to the census: an address attributed to a
cluster has to be a member of one of the clusters that unit names.

**What this does not check, which is as much of the point:**

  * *Denials.* A unit that says an address is **not** in a cluster is skipped
    rather than checked, so "X is not in main-ec-003" is never verified and a
    denial that has itself gone stale is not caught.
  * *Proximity.* A unit that mentions a cluster word without claiming
    membership ("the `0x06E6`/`0x0860` gate block" in a `main-ec-002` table row,
    where `0x06E6` is a byte the shared function reads and not a member) is
    skipped. Requiring the membership cue is what keeps the census summary
    table in `xdata-register-map.md` §5 out of the results.
  * *Which* of several named clusters an address belongs to. A unit naming
    two clusters is satisfied if the address is in either. The cases where the
    split between them is the claim — "`0x06C6` in A and `0x06CD` in B" — are
    caught only in the weaker sense that a wrong id is caught at all.
  * *Anything outside the three roots*, and any address the census does not
    know, so a code address that collides with an XDATA one is not examined.

Every one of those is "not found by this method", never "absent" — the same
caveat `ec/annotations/registers.yaml` carries for a static scan. Passing this
means the checked sentences agree with the committed CSVs; it does not mean the
prose is right about the firmware.

Usage:
    python3 ec/tools/check_cluster_citations.py [--verbose]
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
ROOTS = ("ec", "docs", "evidence")

CLUSTERS = os.path.join(EC, "annotations", "xdata-clusters.csv")
REGISTERS = os.path.join(EC, "annotations", "xdata-registers.csv")

CLUSTER_ID = re.compile(r"main-ec-\d{3}")
ADDRESS = re.compile(r"0x([0-9A-Fa-f]{4})\b")

# A unit only makes a membership claim if it says membership somewhere. The
# word "cluster" alone is not enough -- `xdata-register-map.md` §5's rows carry
# cluster ids and address ranges with no claim that the ranges are the rows'
# members -- but "member" is, and so is "clustering", which is how the
# sentences that drifted in #253 phrase it.
MEMBERSHIP = re.compile(r"\b(?:clustering|clusters?|members?)\b", re.IGNORECASE)

# Phrases that take an address *out* of the cluster the unit names. These units
# are skipped, not checked: see the docstring.
DISCLAIM = re.compile(
    r"\b(?:not|isn't|aren't|never|no longer)\s+(?:in|among|part of|a member|member of)\b"
    r"|\b(?:on|of) its own\b"
    r"|\bsingleton\b",
    re.IGNORECASE,
)

# A sentence ends at a terminator followed by something that starts a new one.
# The trailing set matters in a corpus written as wrapped prose inside list
# items and tables: without the `-` and `|` here, one list item's sentence runs
# on into the next item's and drags its addresses along with it.
TERMINATOR = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*_|-])")


def census():
    """(membership per cluster id, the set of addresses the census knows).

    Membership comes from the clusters CSV, which is keyed by program, so a
    `main-ec-NNN` id is unambiguous on its own. The registers CSV is read only
    for its address column: an address that is not in the census is a code
    address in a sentence full of them, not a cluster member claim.
    """
    with open(CLUSTERS, newline="") as f:
        members = {r["cluster_id"]: set(r["addrs"].split()) for r in csv.DictReader(f)}
    with open(REGISTERS, newline="") as f:
        known = {r["addr"] for r in csv.DictReader(f)}
    return members, known


def units(text):
    """(line number, unit) for each attribution-sized piece of prose.

    A table row is its own unit: the columns of a census table mean different
    things, and letting a row run into the next would make the unit's addresses
    mean nothing in particular. Everything else is joined per paragraph and cut
    into sentences, because this corpus wraps sentences across lines and a
    line-based scan misses an attribution that straddles a wrap -- which is
    exactly how the `manual-fan-ctrl-0751.md` one hides.
    """
    lines = text.split("\n")

    def sentences(buf):
        joined = " ".join(t for _, t in buf)

        def line_at(offset):
            walked = 0
            for lineno, t in buf:
                if offset < walked + len(t) + 1:
                    return lineno
                walked += len(t) + 1
            return buf[-1][0]

        start = 0
        for end in [m.end() for m in TERMINATOR.finditer(joined)] + [len(joined)]:
            chunk = joined[start:end].strip()
            if chunk:
                yield line_at(start), chunk
            start = end

    buf = []
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if buf:
                yield from sentences(buf)
                buf = []
            yield lineno, stripped
        elif not stripped:
            if buf:
                yield from sentences(buf)
                buf = []
        else:
            buf.append((lineno, stripped))
    if buf:
        yield from sentences(buf)


def line_of_address(unit, address):
    """The line a unit's address token is on, for the report.

    Not the line the unit starts on: in a wrapped sentence the cluster id and
    the address it is wrong about are often not on the same line, and a report
    that points at the wrong line is worse than none.
    """
    for lineno, sentence in units(unit):
        if address in sentence.upper():
            return lineno
    return 0


def check(path, members, known, verbose):
    """(problems, lines read) for one file."""
    problems = []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if "main-ec-" not in text:
        return problems, len(text.split("\n"))
    for lineno, unit in units(text):
        ids = sorted(set(CLUSTER_ID.findall(unit)))
        if not ids:
            continue
        addresses = sorted({"0x" + a.upper() for a in ADDRESS.findall(unit)
                            if "0x" + a.upper() in known})
        if not addresses:
            continue
        if DISCLAIM.search(unit):
            if verbose:
                print(f"  skip (disclaims membership) {path}:{lineno}", file=sys.stderr)
            continue
        if not MEMBERSHIP.search(unit):
            if verbose:
                print(f"  skip (no membership claim) {path}:{lineno}", file=sys.stderr)
            continue
        for address in addresses:
            if not any(address in members.get(cid, ()) for cid in ids):
                at = line_of_address(unit, address)
                problems.append((path, at or lineno, ids, address))
    return problems, len(text.split("\n"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="report every unit skipped, and why")
    args = ap.parse_args()

    members, known = census()
    paths = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, root)):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            paths += [os.path.join(dirpath, f) for f in sorted(filenames)
                      if f.endswith(".md")]
    paths.sort()

    problems = []
    read = 0
    for path in paths:
        found, lines = check(path, members, known, args.verbose)
        problems += found
        read += lines

    for path, lineno, ids, address in problems:
        where = f"{os.path.relpath(path, REPO)}:{lineno}"
        named = ", ".join(f"`{cid}`" for cid in ids)
        print(f"{where}: {address} is not a member of any cluster this line "
              f"names ({named}); it is a member of "
              f"{cluster_of(address, members)}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} citation(s) disagree with "
              f"{os.path.relpath(CLUSTERS, REPO)}", file=sys.stderr)
        return 1
    print(f"{len(paths)} files / {read} lines: every checked `main-ec-NNN` "
          "citation resolves to the membership it names in the committed census")
    return 0


def cluster_of(address, members):
    """The id the census does give this address, for the error message."""
    for cid in sorted(members):
        if address in members[cid]:
            return f"`{cid}`"
    return "no main-ec cluster (a pd-image cluster, or none)"


if __name__ == "__main__":
    sys.exit(main())
