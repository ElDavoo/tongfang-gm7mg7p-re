#!/usr/bin/env python3
"""Join the `0x086x` opcode sweep and the C-level census, site by site.

`ec/annotations/xdata-086x-dispatch.md` quotes two direction vocabularies for
the same address and had no way to say whether they contradict each other: the
opcode sweep behind §8, which counts a `MOV DPTR,#addr` and the `movx` after
it, and the decompiled-C census behind §3, which counts occurrences of the
address in the decompiled text. Different denominators, so the totals are
never comparable -- but the *direction* at one site is comparable, and a
hand-typed table is exactly the kind of prose no tool can see (#272).

So the correspondence is committed as data,
`ec/annotations/xdata-0860-census-sites.csv`, and this holds it to the other
two. It reads the sweep's `access` cell out of
`xdata-086x-dispatch-sites.csv`, the bucket out of the mapping, and the
occurrences out of the census itself -- `xdata_register_map.py`'s
`load_index`, `load_symbols`, `occurrence_re`, `strip_comments` and
`classify`, never a re-grep, so the line numbers it checks are the reader's
line numbers and the buckets are the census's own. It fails loudly on a
mapped site whose two directions disagree, on a bucket claimed where the
census is structurally blind, on a citation that no longer resolves or no
longer classifies the way the map says, on an occurrence no site accounts for
or two sites account for between them, on per-bucket totals that miss the
committed `xdata-registers.csv` row, and on a site that is in one of the two
files and not the other.

**The vocabulary, which is the whole content of the check.** The two methods
are not in conflict on `0x0860`; they are in two languages:

| sweep classification | census bucket | verdict |
|---|----------------|---------|
| `read xN` | `read xM` | agree, for any `M >= 1` |
| `write xN` | `write xM` | agree |
| `read xN`, window ending in a call | `passed-to-call xM` | agree -- one instruction, two vocabularies |
| `DPTR handed to <call>` | a bucket | **error** -- the decompile names no address, so no occurrence can exist |
| `no movx found in the decoded window`, or a handoff | `no-occurrence` | agree -- nothing for either method to see |
| any | `other-program` | out of scope -- reported as unchecked, never as agreeing |

The counts are deliberately not compared per site. The sweep records one row
per `MOV DPTR`, and the `0x48`/`0x4C` chains re-read A without reloading
DPTR, so six C-level comparisons land on one sweep row: `2 + 6 + 6 = 14` reads
behind three `read x1` rows. The totals are compared instead, per bucket,
against the generated `xdata-registers.csv` row.

**What this does not check, which is as much of the point:**

  * *The 14 addresses other than `0x0860`.* They carry `not recorded` in the
    sweep's `census` column and have no row in the mapping at all. That is
    "not done by this method", never "there is nothing there" -- a blank cell
    would read as agreement, which is the failure this tool exists to remove.
  * *The two PD-image sites.* `other-program`: the two programs have separate
    XDATA maps and the census's `0x0860` row is `main-ec`, so a direction for
    those bytes is a category error, not a missing measurement. The census is
    still scanned for occurrences, so a PD occurrence appearing one day would
    be reported as unaccounted rather than quietly ignored.
  * *The prose.* This reads three CSVs and the decompile; it cannot see a
    sentence in `xdata-086x-dispatch.md`, and the page's own §9 says so. The
    same gap `check_cluster_citations.py` concedes. **Corrected 2026-09-25
    (issue #801): that is still true of this tool and no longer true of the
    tree.** `check_citation_lines.py` reads the page's site table, its
    `xdata-registers.csv:NNN` cells and the `HAND_CHECKED["0x0860"]` comment,
    and holds them to the two CSVs this tool already joins -- so the *line
    numbers the prose repeats* are now checked, for the two units named in its
    `ROW_SCOPE`. What remains true is the first half: this tool still cannot
    read a sentence, and a claim the prose makes about a direction is not
    checked by anything. `docs/findings/prose-line-citations-held.md` says which
    of the prose's cells are covered and which are held by nothing.
  * *The sweep's blind spot.* A byte reached through a computed DPTR, a
    register-indirect access or a table lookup has no site here, and a site
    the decompiler folded a `MOV DPTR` out of -- `0x0D31C` -- looks identical
    to one the firmware never touches. `no census occurrence` is not evidence
    that the site is unused.

Usage:
    python3 check_site_census.py [--verbose]
"""
import argparse
import collections
import csv
import os
import sys

from xdata_register_map import (BUCKETS, DECOMPILED, classify, load_index,
                                load_symbols, occurrence_re, strip_comments)

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
SITES_CSV = os.path.join(EC, "annotations", "xdata-086x-dispatch-sites.csv")
MAPPING_CSV = os.path.join(EC, "annotations", "xdata-0860-census-sites.csv")
REGISTERS_CSV = os.path.join(EC, "annotations", "xdata-registers.csv")

# The one address the mapping covers. It is also the address the page's §3
# counts and §8 tabulates, and the only one with a per-site correspondence
# recorded -- see the docstring's first "does not check" bullet.
ADDRESS = "0x0860"

# What a non-mapped row carries, per state, so "the census cannot see this
# site" is one shape and "a different program's byte" is another. `na` is not
# a measured zero: the register row for the address is `main-ec`, so no count
# is established for a PD site at all.
BLIND = {"no-occurrence": "0", "other-program": "na"}

# trace_xdata_refs.classify()'s own spellings, read back off the committed
# `access` cell rather than re-run: the sweep's half of the join is the
# committed table, because that is the thing a reader is being shown.
HANDOFF = "DPTR handed to "
NO_MOVX = "no movx found in the decoded window"
CODE_POINTER = "CODE pointer"

# The call and tail-call forms a window can end in. `movx a,@dptr ; lcall
# 0x7151` is the single instruction the two vocabularies disagree about, and
# the row above is the only place they are allowed to.
CALL_TAIL = ("lcall", "acall", "ljmp", "ajmp")


def repo_path(path: str) -> str:
    return os.path.relpath(path, REPO)


def sweep_direction(access: str):
    """The direction one `access` cell claims, or None if it claims none of
    the ones the table above can compare. `read+write` is its own answer
    rather than two, so a site the sweep calls both is not silently read as
    a read and made to agree with a `read` bucket."""
    if access.startswith(HANDOFF):
        return "handoff"
    if access == NO_MOVX:
        return "no-movx"
    if CODE_POINTER in access:
        return "code-pointer"
    reads, writes = "read x" in access, "write x" in access
    if reads and writes:
        return "read+write"
    if reads:
        return "read"
    if writes:
        return "write"
    return None


def ends_in_call(window: str) -> bool:
    """True when a window's last instruction is a call, i.e. the value the
    sweep read is on its way into a subroutine. The window is the `;`-joined
    mnemonic text of the committed `window` cell."""
    tail = window.rsplit(" ; ", 1)[-1].strip()
    return bool(tail) and tail.split(" ")[0] in CALL_TAIL


def verdict(sweep: str, state: str, bucket: str, call_tail: bool) -> str:
    """"agree", "error" or "unchecked" for one site, per the table above.

    Order matters: the two structural cases are decided before the bucket is
    looked at, because a bucket the census cannot support is an error whatever
    the sweep says."""
    if state == "other-program":
        return "unchecked"
    if state == "no-occurrence":
        # Nothing to compare and nothing claimed. A window the sweep found no
        # `movx` in and a handoff the decompile names no address for are the
        # same shape -- the 0x0D31C one and its counterpart -- and both agree.
        # The caller's bucket check is what rejects a bucket claimed here.
        return "agree" if sweep in ("no-movx", "handoff") else "error"
    if sweep == "handoff":
        # Mapped, so a bucket is claimed, and DPTR went to a call that named no
        # address in the decompile. An occurrence cannot exist there.
        return "error"
    if sweep == "no-movx" or sweep in (None, "code-pointer"):
        return "error"
    if bucket == "passed-to-call":
        return "agree" if sweep == "read" and call_tail else "error"
    return "agree" if sweep == bucket else "error"


def read_csv(path: str):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def sweep_sites(path: str = SITES_CSV, addr: str = ADDRESS) -> dict:
    """file_offset -> row, for one address's sites in the committed sweep.

    Keyed on `file_offset` rather than `runtime`: a bank window maps the same
    file offset to a different runtime address per bank, and the mapping is
    about bytes."""
    return {r["file_offset"]: r for r in read_csv(path) if r["addr"] == addr}


def parse_refs(text: str) -> list:
    """[(out_file, line), ...] for a `bank0/D091.c:43,47` cell. Line numbers
    are the reader's, because strip_comments() keeps every newline."""
    where, _, lines = text.partition(":")
    return [(where, int(n)) for n in lines.split(",")]


def census_occurrences(addr: str = ADDRESS) -> dict:
    """{(out_file, line): [bucket, ...]} for every C-level occurrence of
    `addr` in the decompiled tree, one entry per occurrence so a line holding
    three comparisons counts three. The census is reused rather than re-grepped
    so the buckets are the ones `xdata-registers.csv` was generated from."""
    funcs, by_file = load_index()
    symbols = load_symbols()
    pattern = occurrence_re(symbols)
    by_name = {name: value for value, name in symbols.items()}
    func_names = {row["name"] for row in funcs.values()}
    out = collections.defaultdict(list)
    for out_file in by_file:
        with open(os.path.join(DECOMPILED, out_file)) as f:
            text = strip_comments(f.read())
        for m in pattern.finditer(text):
            value = (int(m.group(1), 16) if m.group(1) is not None
                     else by_name[m.group(2)])
            if value == int(addr, 16):
                line = text.count("\n", 0, m.start()) + 1
                out[(out_file, line)].append(
                    classify(text, m.start(), m.end(), m.group(0), func_names))
    return dict(out)


def register_buckets(path: str = REGISTERS_CSV,
                     addr: str = ADDRESS) -> tuple:
    """({bucket: count}, refs) for one address, read out of the generated
    census rather than re-derived. This is the point of reading it: the
    mapping's per-bucket sums are hand-typed, and this is the number they have
    to equal, so a hand-typed number that drifts fails instead of reading as
    agreement."""
    for row in read_csv(path):
        if row["addr"] == addr:
            return ({b: int(row[b]) for b in BUCKETS}, int(row["refs"]))
    raise KeyError(f"{repo_path(path)} has no row for {addr}")


def check(sites: dict, rows: list, occurrences: dict, expected: tuple,
          verbose=False) -> list:
    """(problems, agreed, unchecked) over the three committed inputs.

    Every clause is a disagreement between a hand-typed correspondence and
    something derived -- the sweep's own `access` cell, the census's own
    classification of the cited lines, and the census's own totals. Passing
    means those three agree; it does not mean either method is right about the
    firmware."""
    buckets, refs_total = expected
    problems = []
    agreed = unchecked = 0

    # The join in both directions, before anything is compared: a site in one
    # file and not the other is a visible mismatch rather than a silent one.
    mapped = {}
    for row in rows:
        offset = row["file_offset"]
        if offset not in sites:
            problems.append(f"{offset}: in {repo_path(MAPPING_CSV)} but the "
                            f"sweep has no {ADDRESS} site there")
            continue
        if row["region"] != sites[offset]["region"]:
            problems.append(f"{offset}: mapped as {row['region']!r}, the sweep "
                            f"says {sites[offset]['region']!r}")
        if offset in mapped:
            problems.append(f"{offset}: two rows in "
                            f"{repo_path(MAPPING_CSV)}")
            continue
        mapped[offset] = row
    for offset in sites:
        if offset not in mapped:
            problems.append(f"{offset}: a {ADDRESS} site in "
                            f"{repo_path(SITES_CSV)} with no row in "
                            f"{repo_path(MAPPING_CSV)}")
    if problems:
        # Nothing below can mean anything until both files describe the same
        # set of sites, and a report that mixes "disagrees" with "no row" is
        # harder to read than the first real failure.
        return problems, 0, 0

    accounted = collections.Counter()
    totals = collections.Counter()
    for offset, row in mapped.items():
        state, bucket = row["census_state"], row["census_bucket"]
        site = sites[offset]
        where = f"{offset} ({state})"
        sweep = sweep_direction(site["access"])

        if state == "mapped":
            if bucket not in BUCKETS:
                problems.append(f"{where}: census_bucket {bucket!r} is not one "
                                f"of the census's {', '.join(BUCKETS)}")
                continue
            try:
                count = int(row["census_count"])
            except ValueError:
                problems.append(f"{where}: census_count {row['census_count']!r} "
                                "is not a number")
                continue
            if count < 1:
                problems.append(f"{where}: a mapped site carries "
                                f"census_count {count}; a site the census "
                                "cannot see is state 'no-occurrence', not a "
                                "mapped row with a zero")
                continue
            if row["census_refs"] == "none":
                problems.append(f"{where}: mapped, but census_refs names no "
                                "line -- a mapped site without a citation is "
                                "unverifiable, not corroborated")
                continue
            totals[bucket] += count
        else:
            if state not in BLIND:
                problems.append(f"{where}: census_state {state!r} is not one of "
                                f"'mapped', {', '.join(repr(s) for s in BLIND)}")
                continue
            if bucket != "none" or row["census_count"] != BLIND[state]:
                problems.append(f"{where}: the census is structurally blind "
                                "here, so census_bucket/census_count must be "
                                f"'none'/'{BLIND[state]}' and are "
                                f"{bucket!r}/{row['census_count']!r}")
                continue
            if row["census_refs"] != "none":
                problems.append(f"{where}: census_refs names "
                                f"{row['census_refs']!r} on a site the census "
                                "is blind to -- a claim with no occurrence "
                                "behind it")
                continue

        how = verdict(sweep, state, bucket, ends_in_call(site["window"]))
        if how == "unchecked":
            unchecked += 1
            if verbose:
                print(f"  unchecked {where}: sweep says "
                      f"{site['access']!r}, out of scope here", file=sys.stderr)
            continue
        if how == "error":
            problems.append(f"{where}: the sweep says {site['access']!r} and "
                            f"the map says bucket {bucket!r}; "
                            + ("a handoff names no address in the decompile, "
                               "so no occurrence can exist there"
                               if sweep == "handoff" else
                               "the two methods disagree, and the table in "
                               "this tool's docstring is the only set of pairs "
                               "allowed to agree"))
            continue
        agreed += 1

        if state != "mapped":
            continue
        # The citation itself: does it still resolve, and does the census's
        # own classify() still put it in the bucket the map claims?
        seen = 0
        try:
            refs = parse_refs(row["census_refs"])
        except ValueError as e:
            problems.append(f"{where}: census_refs {row['census_refs']!r} does "
                            f"not parse as 'file.c:line[,line...]' ({e})")
            continue
        for ref in refs:
            accounted[ref] += 1
            if ref not in occurrences:
                problems.append(f"{where}: census_refs cites {ref[0]}:{ref[1]}, "
                                f"where the census has no {ADDRESS} occurrence "
                                "-- the line moved, or the reference was dropped")
                continue
            seen += len(occurrences[ref])
            found = set(occurrences[ref])
            if found != {bucket}:
                problems.append(f"{where}: census_refs cites {ref[0]}:{ref[1]}, "
                                f"which the census classifies "
                                f"{', '.join(sorted(found))} and the map claims "
                                f"{bucket}")
        if seen != int(row["census_count"]):
            problems.append(f"{where}: census_count says {row['census_count']} "
                            f"and the cited lines hold {seen}")

    for ref, times in sorted(accounted.items()):
        if times > 1:
            problems.append(f"{ref[0]}:{ref[1]}: {times} mapped sites cite this "
                            "occurrence; the correspondence splits one "
                            "occurrence between sites")
    for ref in sorted(set(occurrences) - set(accounted)):
        problems.append(f"{ref[0]}:{ref[1]}: a {ADDRESS} occurrence no mapped "
                        "site accounts for")

    for bucket in BUCKETS:
        if totals.get(bucket, 0) != buckets[bucket]:
            problems.append(f"per-bucket totals: the map sums {bucket} to "
                            f"{totals.get(bucket, 0)} where "
                            f"{repo_path(REGISTERS_CSV)} says {buckets[bucket]}")
    if sum(totals.values()) != refs_total:
        problems.append(f"per-bucket totals: the map sums {sum(totals.values())} "
                        f"where {repo_path(REGISTERS_CSV)} says refs {refs_total}")
    return problems, agreed, unchecked


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="name the sites reported as unchecked, not only the ones that fail")
    args = ap.parse_args()

    sites = sweep_sites()
    rows = read_csv(MAPPING_CSV)
    occurrences = census_occurrences()
    expected = register_buckets()
    problems, agreed, unchecked = check(sites, rows, occurrences, expected,
                                        args.verbose)

    for problem in problems:
        print(f"check_site_census.py: {problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} disagreement(s) between "
              f"{repo_path(SITES_CSV)}, {repo_path(MAPPING_CSV)} and the census",
              file=sys.stderr)
        return 1
    counts = " ".join(f"{b} {expected[0][b]}" for b in BUCKETS)
    print(f"{ADDRESS}: {agreed} site(s) agree across both methods, {unchecked} "
          f"unchecked (other program), {sum(expected[0].values())} occurrence(s) "
          f"accounted for once each -- {counts}, refs {expected[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
