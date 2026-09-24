#!/usr/bin/env python3
"""Hold every `main-ec-NNN` citation in the prose to the committed census.

Two rules over one walk of the committed markdown under `ec/`, `docs/` and
`evidence/`, both keyed on the same two CSVs, and independent of each other.

**Membership.** A cluster id in a sentence is a pointer: a reader who follows
it into `ec/annotations/xdata-clusters.csv` has to land on the membership the
sentence describes. Issue #253 is four sentences where the pointer drifted —
the ids moved when issue #4.3's census regeneration landed (#133 / #238), and
prose written against the old numbering kept the old ids. The ids are numbered
by size, then references, then lowest address (`xdata_register_map.py:1027`),
which makes them stable across regenerations *of one tool version* and says
nothing about staying put across a change to the tool's own classifier. So a
unit that names one or more clusters and one or more XDATA addresses has to
attribute each address to a member of one of the clusters it names: the
cluster its own wording pairs the address with, and where it pairs it with
none, one of the clusters the unit names.

**Counts.** `xdata-register-map.md` §5 is a hand-typed copy of twelve rows of
that CSV, and nothing held its numbers: four of the twelve rows disagreed with
the census beside them before issue #272. A *census row* — a markdown table row
whose first cell is one `main-ec-NNN` id — has its size, reference count,
address range and named count held to the same CSV. It is a second gate rather
than an extension of the membership one and inherits none of its conditions:
a §5 row carries a range and a title but never the word "member", so the
membership rule skips every one of them, and this rule reads cells the
membership rule never sees.

**What the membership rule does not check, which is as much of the point:**

  * *Denials.* A unit that says an address is **not** in a cluster is skipped
    rather than checked, so "X is not in main-ec-003" is never verified and a
    denial that has itself gone stale is not caught.
  * *Proximity.* A unit that mentions a cluster word without claiming
    membership ("the `0x06E6`/`0x0860` gate block" in a `main-ec-002` table row,
    where `0x06E6` is a byte the shared function reads and not a member) is
    skipped. Requiring the membership cue is what keeps §5's *ranges* out of
    the membership results; its *numbers* are the count rule's.
  * *A split written as a list.* An address is held to the cluster its own
    words put it with — "`0x06C6` in `main-ec-121` and `0x06CD` in
    `main-ec-198`" — but only where a preposition joins the two tokens and no
    clause boundary falls between them. The same claim with the ids first and
    the addresses in a trailing list ("the two cut into `main-ec-121` and
    `main-ec-198` (`0x06C6`, `0x06CD`)") pairs nothing and is satisfied by
    either id; the two in it can be exchanged without this noticing. So a
    unit naming two clusters is caught when its own wording says which is
    which, and only in the weaker sense of "a wrong id at all" where it does
    not.
  * *Anything outside the three roots*, and any address the census does not
    know, so a code address that collides with an XDATA one is not examined.

**And what the count rule does not check.** A cell is read as a count only if
it is a bare decimal integer — thousands commas allowed, so `1,136` is 1136 —
or, in the "named inside" column, one of `none`, an em dash or a hyphen, which
there say zero. Everything else in a census row is left alone, which is most
of why the rule can sit in the tree without flagging the corpus:

  * *A listing.* `` `0x0403` `` in §5's "named inside" column is the one
    address `main-ec-004` names, written out because a single name is worth
    the space, and a listing is not a count of one.
  * *A span.* `` `0x030E`-`0x1809` `` is two addresses of a range. The count
    rule reads it as the row's range and holds it against `addr_range`, but it
    is never read as a number of anything, in any column.
  * *Free text.* `**43 addresses, 4,965 refs**` in
    `xdata-06c2-06db-timers.md:491` is a deliberate contrast between the
    committed cluster and the shape a code guard would produce, and the prose
    under it says that shape carries no id. Reading counts out of free text
    would flag those two figures permanently and for no reason.
  * *A dash in a size or reference column.* The same corpus writes `—` there
    for "this figure does not apply to this row", which is not a claim of
    zero, so the two columns do not get the named cell's three spellings.
  * *A row naming more than one cluster id.* Which row's figures would apply
    is ambiguous, so a row that names two is not read as a census row at all.
  * *A row whose cluster id is not in its first cell.* The
    `gpu-tgp-07c4-07d7-door.md` cross-reference table puts `main-ec-001` in a
    cross-reference column beside `dsdt.dsl:52204` source line numbers, which
    are not counts of anything this census knows.

Every one of those is "not found by this method", never "absent" — the same
caveat `ec/annotations/registers.yaml` carries for a static scan. Passing this
means the checked sentences and the checked counts agree with the committed
CSVs; it does not mean the prose is right about the firmware, and where the
count rule cannot read a cell it says nothing about that figure.

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

# The preposition that turns two tokens into one claim. Both orders occur in
# the corpus -- "`0x06C6` in `main-ec-121`", and "`main-ec-011` is the
# 10-address, 91-reference cluster of `0x0875 0x089C ...`" -- so a pair is
# read whichever way round the two tokens sit.
MEMBERSHIP_PREP = re.compile(r"\b(?:in|into|within|of|inside|to)\b", re.IGNORECASE)

# A span crossing one of these is not one claim, so nothing is paired across
# it. The brackets are the conservative half: a preposition on one side of a
# parenthetical is not a claim about a token on the other side of it, which is
# what "cut into `main-ec-121` and `main-ec-198` (`0x06C6`, `0x06CD`)" would
# otherwise invite. A unit is one joined line by `units()`, so there is no
# newline to break on.
CLAUSE_BREAK = re.compile(r"[;:.()]")

# A sentence ends at a terminator followed by something that starts a new one.
# The trailing set matters in a corpus written as wrapped prose inside list
# items and tables: without the `-` and `|` here, one list item's sentence runs
# on into the next item's and drags its addresses along with it.
TERMINATOR = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*_|-])")

# The shapes a census row's cells can be read in. A count is a bare decimal
# integer -- thousands commas the way this corpus writes them, so `1,136` and
# `4,965` both read and `1,,,2` does not -- or one of the three ways the
# corpus says zero. Everything else in a table cell is left unread, and the
# docstring names the committed prose each of those shapes is.
BARE_NUMBER = re.compile(r"[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+")
ZERO = re.compile(r"none|—|-", re.IGNORECASE)
# A range, which is what anchors the named count. §5 writes it
# `` `0x030E`-`0x1809` ``, one backtick per address, so it is only recognisable
# as a span once `clean` has taken the backticks out.
SPAN = re.compile(r"0x[0-9A-Fa-f]{4}-0x[0-9A-Fa-f]{4}")
MARKUP = re.compile(r"[`*]")


def clean(cell):
    """The cell's own text, without the markdown wrapped around it.

    A §5 cell is bolded or backticked or both, and the id cell is both at
    once (`**`main-ec-003`**` in `xdata-06c2-06db-timers.md`). The backticks
    go throughout rather than off the ends, because a range is written
    `` `0x030E`-`0x1809` `` and it is only the range once they are gone.
    """
    return MARKUP.sub("", cell).strip()


def number(cell):
    """The cell read as a plain number, or None if it is not one.

    Deliberately narrow: a bare decimal integer, thousands commas the way this
    corpus writes them. A listing, a span and a run of free text are all `None`
    here, and every one of those shapes is real committed prose -- see the
    docstring. An em dash is `None` too, and that is the point: in a size or
    reference column a dash means the figure does not apply to that row, which
    is not the same claim as zero.
    """
    text = clean(cell)
    if BARE_NUMBER.fullmatch(text):
        return int(text.replace(",", ""))
    return None


def named(cell):
    """The cell read as a count of named addresses, or None if it is not one.

    `number`, plus the three ways this corpus says zero -- `none`, an em dash,
    a hyphen -- which in the "named inside" column do mean zero and so are
    checked against the census's own count. This is the one cell where a
    non-number is still a count claim, and it is what makes a row reading
    `none` where the census names every member visible rather than merely
    wrong. It is the reason the two readers are separate: the same dash means
    "zero" here and "not applicable" in the two columns beside it.
    """
    stated = number(cell)
    if stated is not None:
        return stated
    if ZERO.fullmatch(clean(cell)):
        return 0
    return None


def cells(unit):
    """(the cells of a markdown table row) or () if the unit is not one."""
    if not (unit.startswith("|") and unit.endswith("|")):
        return ()
    return [c.strip() for c in unit[1:-1].split("|")]


def plural(n, noun):
    """`1 named address`, `43 named addresses` — a one is a real case here."""
    head, _, word = noun.rpartition(" ")
    if n != 1:
        word += "es" if word.endswith(("s", "x", "z", "ch", "sh")) else "s"
    return f"{n} {head} {word}" if head else f"{n} {word}"


def census():
    """(membership per cluster id, the addresses the census knows, its counts).

    Membership and the counted columns both come from the clusters CSV, which
    is keyed by program, so a `main-ec-NNN` id is unambiguous on its own. The
    registers CSV is read only for its address column: an address that is not
    in the census is a code address in a sentence full of them, not a cluster
    member claim.
    """
    with open(CLUSTERS, newline="") as f:
        rows = list(csv.DictReader(f))
    members = {r["cluster_id"]: set(r["addrs"].split()) for r in rows}
    counts = {r["cluster_id"]: {"size": int(r["size"]),
                               "refs": int(r["refs"]),
                               "named": len(r["named_addrs"].split()),
                               "addr_range": r["addr_range"]}
              for r in rows}
    with open(REGISTERS, newline="") as f:
        known = {r["addr"] for r in csv.DictReader(f)}
    return members, known, counts


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


def pairings(unit, addresses):
    """{address: cluster id} for the address/id pairs the unit's wording makes.

    A unit saying "`0x06C6` in `main-ec-121` and `0x06CD` in `main-ec-198`" is
    claiming the split between two clusters, and reading it as "in either" is
    how `xdata-06c2-06db-timers.md`'s stale `main-ec-118` got past #253. An
    address pairs with an id where a preposition joins the two tokens and
    nothing else does: no second address, no second id, no clause boundary in
    between. Where several ids qualify for one address the nearest wins, and
    where none does the address is left to the any-of rule.
    """
    addr_spans = [m.span() for m in ADDRESS.finditer(unit)]
    id_spans = [m.span() for m in CLUSTER_ID.finditer(unit)]
    all_spans = addr_spans + id_spans
    pairs = {}
    for match in ADDRESS.finditer(unit):
        address = "0x" + match.group(1).upper()
        if address not in addresses:
            continue
        nearest = None
        for span in id_spans:
            lo, hi = sorted((match.span(), span))
            between = unit[lo[1]:hi[0]]
            if not MEMBERSHIP_PREP.search(between) or CLAUSE_BREAK.search(between):
                continue
            if any(lo[1] < s[0] < hi[0] for s in all_spans):
                continue
            if nearest is None or hi[0] - lo[1] < nearest[0]:
                nearest = (hi[0] - lo[1], unit[span[0]:span[1]])
        if nearest:
            pairs[address] = nearest[1]
    return pairs


def census_row(path, lineno, unit, counts):
    """(problems) for a census row's hand-typed counts.

    Independent of the membership rule and run before it, because a §5 row
    never reaches the membership rule: it has an address range and a title,
    and not one of its cells says "member". So a row is read here, and only a
    row is: the first cell has to be one cluster id the census knows.
    """
    row = cells(unit)
    if len(row) < 3:
        return []
    head = clean(row[0])
    ids = CLUSTER_ID.findall(head)
    # `findall` rather than a `fullmatch`, so a cell naming two clusters is
    # not a census row: whose figures would they be?
    if len(ids) != 1 or head != ids[0]:
        return []
    facts = counts.get(ids[0])
    if facts is None:
        return []

    problems = []
    # Both counts quote the cell as the table writes it rather than as the
    # number parsed out of it, so a reader can find the figure in the row
    # without converting it first. A census problem has no paired id: the
    # `kind` says which rule raised it, and only a membership one names a
    # cluster for the unit's own wording to have paired the address with.
    for cell, column, noun in ((row[1], "size", "address"),
                               (row[2], "refs", "reference")):
        stated = number(cell)
        if stated is not None and stated != facts[column]:
            problems.append((path, lineno, ids,
                             f"{plural(facts[column], noun)} in the census, "
                             f"{clean(cell)} in the row", "census count", None))
    # The range anchors the named count, so the cell after it is where the
    # count goes. The range itself is held to the row's own `addr_range` --
    # nearly free once the cell has been parsed to find that neighbour -- and
    # a second span is not treated as another anchor, which is what keeps a
    # span in the named column from being read as a range.
    for i, cell in enumerate(row[2:], start=2):
        stated = clean(cell)
        if not SPAN.fullmatch(stated):
            continue
        if stated.upper() != facts["addr_range"].upper():
            problems.append((path, lineno, ids,
                             f"range `{facts['addr_range']}` in the census, "
                             f"`{stated}` in the row", "census range", None))
        if i + 1 < len(row):
            stated = named(row[i + 1])
            if stated is not None and stated != facts["named"]:
                problems.append((path, lineno, ids,
                                 f"{plural(facts['named'], 'named address')} "
                                 f"in the census, {clean(row[i + 1])} in the row",
                                 "census count", None))
        break
    return problems


def check(path, members, counts, known, verbose):
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
        problems += census_row(path, lineno, unit, counts)
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
        # Ordered after the two skips above: a denial is not a claim, and a
        # pairing rule reached first would read "a size-1 cluster of its own"
        # as an attribution. The fallback is per address, not per unit, so a
        # unit that pairs one byte still has its other addresses checked.
        pairs = pairings(unit, addresses) if len(ids) > 1 else {}
        for address in addresses:
            expected = [pairs[address]] if address in pairs else ids
            if not any(address in members.get(cid, ()) for cid in expected):
                at = line_of_address(unit, address)
                problems.append((path, at or lineno, ids, address, "membership",
                                 pairs.get(address)))
    return problems, len(text.split("\n"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="report every unit skipped, and why")
    args = ap.parse_args()

    members, known, counts = census()
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
        found, lines = check(path, members, counts, known, args.verbose)
        problems += found
        read += lines

    for path, lineno, ids, what, kind, paired in problems:
        where = f"{os.path.relpath(path, REPO)}:{lineno}"
        named = ", ".join(f"`{cid}`" for cid in ids)
        if kind == "membership":
            if paired:
                claim = f"not in `{paired}`, the cluster this line pairs it with"
            else:
                claim = f"not a member of any cluster this line names ({named})"
            print(f"{where}: {what} is {claim}; it is a member of "
                  f"{cluster_of(what, members)}", file=sys.stderr)
        else:
            print(f"{where}: {kind} disagrees for {named}: {what}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} citation(s) disagree with "
              f"{os.path.relpath(CLUSTERS, REPO)}", file=sys.stderr)
        return 1
    print(f"{len(paths)} files / {read} lines: every checked `main-ec-NNN` "
          "citation and hand-typed count agrees with the committed census")
    return 0


def cluster_of(address, members):
    """The id the census does give this address, for the error message."""
    for cid in sorted(members):
        if address in members[cid]:
            return f"`{cid}`"
    return "no main-ec cluster (a pd-image cluster, or none)"


if __name__ == "__main__":
    sys.exit(main())
