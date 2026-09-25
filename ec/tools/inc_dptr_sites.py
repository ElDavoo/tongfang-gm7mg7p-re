#!/usr/bin/env python3
"""The 107 bytes the pair-accessor pass reaches only as an `inc DPTR` half,
accounted for all 107, and whether each has a `MOV DPTR` site of its own.

`xdata_register_map.py`'s pair pass (`ec/annotations/xdata-register-map.md`
§4.7) resolves 437 accessor call sites into 214 distinct addresses, and
`scan()` folds each call into one `pair-literal` row per *pair* -- it adds
`addr` and `addr + 1` under the same spelling
(`xdata_register_map.py:2241-2249`), so the census CSV cannot say which of the
214 is the seed and which is the byte the accessor's `inc DPTR` walks onto. That
distinction lives only inside `pair_sites()`, which is why the question §4.7
left open ("73 of the 107 have no `MOV DPTR,#addr` encoding") is not a query
against a committed artifact and this tool exists to answer it.

**The population is a set difference, and both halves are derived here.** `S` is
every `addr` a call site passes and `S1` every `addr + 1`. The addresses that
are *only* the `inc DPTR` half are `S1 - S`: one that is somebody's seed *and*
somebody's `+1` is reached by two encodings, which is a different population
and is not what §4.7 counted. The summary prints how many addresses the two
halves share, so the arithmetic the 107 rests on is a measurement on every run
rather than a claim about a tree that has since moved -- on the committed tree
they are disjoint and 107 + 107 == `PAIR_ROWS` == 214, and both numbers are
re-derived here instead of read out of the ORACLE block.

**Two methods, never added together.** `mov_dptr_main_ec` and
`mov_dptr_pd_image` are `trace_xdata_refs.sites_for` over the image -- the
`MOV DPTR,#addr` byte scan §6 of `ec/annotations/xdata-0400-045f.md` is written
against. The `census_*` columns are `xdata_register_map.py`'s per-`.c` census of
the decompiled C. `region_of` does the image split rather than a hand-written
offset range, which is what keeps bank1's window at file `0x10000` and not
`0x08000`: §4.7's recipe warns that reading the bank boundary at `0x08000`
misses six of the addresses below, and a tool that spelled the range out itself
would be one edit away from making that mistake again.

**What the columns are and are not.** `direction` and `accessor` are the
callee's, because the direction is the accessor's own body -- `pair_accessor()`
reads the two `movx @DPTR` an `inc DPTR` apart out of the committed `.asm` --
and the caller's argument says nothing about it. `census_*` counts references
in decompiled text, which is a lower bound on the machine code and, over
overlapping exports, an upper bound on it; `ec/annotations/xdata-register-map.md`
§4.7 works that through for `0x0402` and nothing here re-derives it. Every
bucket in `xrm.BUCKETS` gets a column, so no bucket can be dropped without the
schema changing: on this population `census_read_write` is non-zero for `0x0389`
and `0x0393`, the other two are zero everywhere, and `census_refs` is the sum
of the five on all 107 rows.

**A zero here is "not found by this method".** `mov_dptr_main_ec == 0` is what
`trace_xdata_refs.py` found by a byte scan, and `docs/findings.md` §4c is this
repository's retracted case of reading such a zero as absence.
`ec/annotations/xdata-inc-dptr-only.md` is the write-up: it states the
admission rule, lists all 107, and declines to enter the 73 -- on the grounds
that `registers.yaml` is not the census, which is a statement about what the two
files are *for* and not about what either of them found.

This tool reads committed files and writes nothing but stdout. `registers.yaml`
is opened read-only, for the `entered` column, and
`../tools/test_inc_dptr_sites.py` pins that with a tripwire over `open` in any
write mode.

Usage:
    python3 inc_dptr_sites.py ../firmware/GMxMGxx_11.800
    python3 inc_dptr_sites.py ../firmware/GMxMGxx_11.800 --csv > ../annotations/xdata-inc-dptr-only.csv
    python3 inc_dptr_sites.py ../firmware/GMxMGxx_11.800 --check
"""
import argparse
import collections
import csv
import io
import os
import sys

from trace_xdata_refs import (PD_MARKER, check_table, region_of, repo_path,
                              sites_for)
from xdata_register_map import (BUCKETS, DECOMPILED, MAIN_PROGRAMS,
                                absorb, blank_entry, load_index, load_names,
                                load_pair_accessors, load_symbols,
                                occurrence_re, pair_sites, scan, strip_comments)

REGISTERS_YAML = os.path.join(DECOMPILED, os.pardir, "annotations",
                              "registers.yaml")
SITES_CSV = os.path.join(DECOMPILED, os.pardir, "annotations",
                         "xdata-inc-dptr-only.csv")
# The regions the `MOV DPTR` count is made over, as `region_of` spells them.
# Named rather than computed so a reader can see that the main EC is `common`
# plus both banks and that the pd image is counted separately from both: a
# shared address number in the pd image is another program's byte, not a second
# site for this one.
MAIN_EC_REGIONS = ("common", "bank0", "bank1")
PD_REGION = "pd-image"
# The three populations the 107 split into, and the two the first of them
# splits into again. Named because the page's whole claim is that the split is
# complete, and a population with no name reads as an omission rather than as a
# decision.
NO_SITE_ANY_IMAGE = "no MOV DPTR site in any image"
PD_IMAGE_ONLY = "pd-image sites only, none in the main EC"
MOV_DPTR_ENTERED = "main-EC MOV DPTR site, entered in registers.yaml"
MOV_DPTR_NOT_ENTERED = "main-EC MOV DPTR site, not entered"
# §4.7's 73 is the first two together and *not* the first one alone: the cut is
# by main-EC site, because a `MOV DPTR` in the pd image is another program's
# byte and says nothing about what the EC does with that address number. The
# two are named separately and then summed, because "found nowhere" and "found
# in a different program" are different reasons to decline, and a table that
# reported only their total would be one edit away from merging them.
DECLINED = (NO_SITE_ANY_IMAGE, PD_IMAGE_ONLY)
POPULATIONS = DECLINED + (MOV_DPTR_ENTERED, MOV_DPTR_NOT_ENTERED)

COLUMNS = (["addr", "seed", "direction", "accessor", "census_refs"]
           + [f"census_{b.replace('-', '_').replace('+', '_')}" for b in BUCKETS]
           + ["mov_dptr_main_ec", "mov_dptr_pd_image", "entered"])


def entered_addrs(path: str = REGISTERS_YAML) -> set:
    """Every address `registers.yaml` names, read-only.

    A row's `addr` is a list for a 16-bit pair and a scalar otherwise, and
    `status:` is deliberately not read: this asks only which numbers the file
    names, which is what the 34-that-have-a-`MOV DPTR`-site split is a question
    about. A byte the census reaches and this file cannot name is one of the
    follow-up's 27, not a statement about whether the byte exists.
    """
    import yaml
    with open(path) as f:
        doc = yaml.safe_load(f)
    out = set()
    for entry in doc["registers"]:
        addr = entry["addr"]
        out.update(addr if isinstance(addr, list) else [addr])
    return out


def blank_half() -> dict:
    """One address's running row. `seed` is None until a call names it, which
    is how the CSV's `seed` cell is a derivation rather than arithmetic."""
    return {"reached_as_seed": False, "seed": None, "directions": set(),
            "accessors": set(), "programs": set()}


def pair_pass(accessors: dict, by_file, symbols) -> dict:
    """{addr: the row this tool needs} for every address a pair call reaches,
    **both halves** -- the `addr` a call is passed and the `addr + 1` its own
    `inc DPTR` walks onto.

    Two passes over the same text, and the second is the narrower one on
    purpose. The first calls `pair_sites()` once per file with the whole
    accessor table, so `xdata_register_map.py` stays the single authority on
    which calls resolve and in which direction -- this file never re-reads a
    call argument. The second runs over the files the first flagged only, and
    calls the same function once per accessor with a one-entry table:
    `pair_sites()` builds its name alternation from the keys it is given, so a
    one-entry table resolves exactly that accessor and nothing else. That is
    how the per-address accessor name is obtained without a second
    implementation of the argument parse, and the second pass's findings are
    checked against the first's, so a divergence is a failure here rather than
    a second answer somewhere.

    The seed half is recorded as a role rather than as a row of its own,
    because an address can be a seed in one call and an `inc DPTR` half in
    another; `reached_as_seed` is what `inc_only()` subtracts, and its count is
    what makes the two halves' disjointness a measurement instead of an
    assumption (see the module docstring).
    """
    pattern = occurrence_re(symbols)
    resolved = {}
    flagged = set()
    for out_file, row in by_file.items():
        with open(os.path.join(DECOMPILED, out_file)) as f:
            text = strip_comments(f.read())
        hit = False
        for addr, direction in pair_sites(text, accessors, pattern):
            resolved.setdefault(addr, blank_half())["reached_as_seed"] = True
            entry = resolved.setdefault(addr + 1, blank_half())
            entry["directions"].add(direction)
            entry["programs"].add(row["program"])
            # `addr + 1` fixes `addr`, so two call sites can only disagree
            # about the seed if `pair_sites()` itself is inconsistent; the check
            # is here because the CSV prints this cell and a reader would take
            # it for the derivation it claims to be.
            if entry["seed"] is not None and entry["seed"] != addr:
                raise SystemExit(
                    f"error: {out_file} reaches 0x{addr + 1:04X} from both "
                    f"0x{entry['seed']:04X} and 0x{addr:04X}")
            entry["seed"] = addr
            hit = True
        if hit:
            flagged.add(out_file)
    for out_file, row in by_file.items():
        if out_file not in flagged:
            continue
        with open(os.path.join(DECOMPILED, out_file)) as f:
            text = strip_comments(f.read())
        for name, direction in accessors.items():
            for addr, got in pair_sites(text, {name: direction}, pattern):
                entry = resolved.get(addr + 1)
                if entry is None or not entry["directions"]:
                    raise SystemExit(
                        f"error: {out_file} resolves {name}({addr:#06x}) in the "
                        "per-accessor pass but not in the full-table pass; the "
                        "two disagree about which calls are pair sites, so "
                        "neither table is trustworthy")
                if got not in entry["directions"] or row["program"] not in entry["programs"]:
                    raise SystemExit(
                        f"error: {out_file} resolves {name}({addr:#06x}) as "
                        f"{got!r} from {row['program']}, but the full-table pass "
                        f"recorded {sorted(entry['programs'])} with "
                        f"{sorted(entry['directions'])}")
                entry["accessors"].add(name)
    return resolved


def inc_only(resolved: dict) -> dict:
    """`resolved` minus every address that is some call's own `addr`.

    The subtraction is what `scan()` cannot do for the census CSV: an address
    that is both an `addr` and some other call's `addr + 1` is reached by two
    encodings, so it is not "only ever the `inc DPTR` half" and §4.7's 107 does
    not contain it. Writing the set difference out rather than relying on the
    two halves being disjoint is what makes the 107 a measurement instead of a
    restatement -- and on this tree the difference removes nothing, because no
    address is both, so `S1 - S` is all of `S1` and the summary prints that
    rather than the reader having to assume it.
    """
    return {a: e for a, e in resolved.items() if not e["reached_as_seed"]}


def census_by_addr(by_file, names, symbols, accessors, wanted) -> dict:
    """{addr: the census entry} for `wanted`, over the whole tree.

    Read through `xdata_register_map.py` rather than re-counted, so these cells
    are the same references `xdata-registers.csv` carries and the two can be
    compared cell for cell. The three main-EC programs are absorbed into one
    entry per address the way `merge_group()` does it, which is why a `pd`
    reference would not silently join a main-EC row: the merge is over
    `MAIN_PROGRAMS` and the pd census is a separate dict this never reads.
    """
    census, _calls, _raw = scan(by_file, names, set(names), symbols,
                                accessors=accessors)
    merged = {}
    for program in MAIN_PROGRAMS:
        for addr, entry in census[program].items():
            if addr not in wanted:
                continue
            merged.setdefault(addr, blank_entry())
            absorb(merged[addr], entry)
    return merged


def csv_table(d: bytes, population: dict, pd_verified: bool, census: dict,
              entered: set) -> str:
    """The `--csv` table, as a string rather than a write.

    `population` is `inc_only()`'s output, not `pair_pass()`'s: the table is the
    107 the issue asked for and not the 214 the pair pass reaches, because the
    seed half is already covered by `static_refs_main_ec` in `registers.yaml`
    and by the census's own rows. A string rather than a write because
    `--check` diffs the same bytes this prints, and because the tool's contract
    is that it writes nothing but stdout.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for addr in sorted(population):
        entry = population[addr]
        count = census.get(addr)
        buckets = count["buckets"] if count else collections.Counter()
        offsets = sites_for(d, addr)
        w.writerow([f"0x{addr:04X}", f"0x{entry['seed']:04X}",
                    "+".join(sorted(entry["directions"])),
                    ";".join(sorted(entry["accessors"])),
                    count["refs"] if count else 0]
                   + [buckets[b] for b in BUCKETS]
                   + [sum(1 for o in offsets
                          if region_of(o, pd_verified)[0] in MAIN_EC_REGIONS),
                      sum(1 for o in offsets
                          if region_of(o, pd_verified)[0] == PD_REGION),
                      "yes" if addr in entered else "no"])
    return buf.getvalue()


def population_of(row: dict) -> str:
    """Which of the four populations a table row is in.

    Read off the row rather than recomputed from the tree, so the summary this
    tool prints and the table it prints cannot disagree about the split. The
    cut is by `mov_dptr_main_ec` alone: a `MOV DPTR` in the pd image is
    another program's byte at the same address number, and counting it as a
    site for the main EC's byte is the mistake `trace_xdata_refs.py`'s own
    docstring opens with.
    """
    if int(row["mov_dptr_main_ec"]):
        return (MOV_DPTR_ENTERED if row["entered"] == "yes"
                else MOV_DPTR_NOT_ENTERED)
    return (PD_IMAGE_ONLY if int(row["mov_dptr_pd_image"])
            else NO_SITE_ANY_IMAGE)


def read_rows(generated: str) -> list:
    """The table's rows, through the csv module and not by splitting on commas.

    The `accessor` cell joins with `;` and the two direction words with `+`,
    which keeps a reader's `cut -d,` working, but a reader that did not know
    that should not be able to corrupt the summary it is printed beside.
    """
    return list(csv.DictReader(io.StringIO(generated)))


def build(d: bytes, pd_verified: bool) -> tuple:
    """(the resolved both-halves map, the `--csv` table). The one read of the
    tree, so the summary and the table cannot be built from different runs."""
    funcs, by_file = load_index()
    symbols = load_symbols()
    accessors = load_pair_accessors()
    resolved = pair_pass(accessors, by_file, symbols)
    only = inc_only(resolved)
    census = census_by_addr(by_file, load_names(funcs), symbols, accessors, only)
    return resolved, csv_table(d, only, pd_verified, census, entered_addrs())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-address table as CSV on stdout instead "
                         "of the summary")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="diff this run against the committed table and exit "
                         f"non-zero on any difference (default: {repo_path(SITES_CSV)})")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        # stderr, so `--csv` redirected to a file stays a clean CSV, and a
        # non-zero exit: without the marker the pd region is unidentified, so
        # `mov_dptr_pd_image` would read 0 for every row and look like a
        # measurement. This is the check `trace_xdata_refs.py` makes and it is
        # the same one, because it is the same claim.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- the "
              "pd region is unidentified, so `mov_dptr_pd_image` would read 0 "
              "for every row\n", file=sys.stderr)
        return 1

    resolved, generated = build(d, pd_verified)

    if args.check is not None:
        return check_table(generated, args.check)
    if args.csv:
        sys.stdout.write(generated)
        return 0

    rows = read_rows(generated)
    counts = collections.Counter(population_of(r) for r in rows)
    both = len(resolved)
    shared = sorted(a for a, e in resolved.items()
                    if e["reached_as_seed"] and e["directions"])
    declined = sum(counts[name] for name in DECLINED)
    print(f"{both} addresses are reached by a pair accessor, {len(rows)} of them "
          f"only as the `inc DPTR` half of the pair --\nand all {len(rows)} are "
          "accounted for:\n")
    for name in POPULATIONS:
        print(f"  {counts[name]:>4}  {name}")
    print(f"  {declined:>4}  = the {declined} with no main-EC `MOV DPTR` site, "
          "which is §4.7's 73")
    if shared:
        print(f"\n{len(shared)} address(es) are a seed in one call and an `inc "
              f"DPTR` half in another, so they are in the {both} and in neither "
              f"of the figures above: {', '.join(f'0x{a:04X}' for a in shared)}")
    else:
        print(f"\nThe two halves are disjoint: no address is a seed in one call "
              f"and an `inc DPTR` half in another, so {both} is the whole of "
              "what the\npair pass reaches and none of it is counted twice.")
    only = [r for r in rows if population_of(r) in DECLINED]
    print(f"\nThe {declined} run {only[0]['addr']} to {only[-1]['addr']}. "
          "`ec/annotations/xdata-inc-dptr-only.md`\nis the write-up; `--csv` is "
          "the whole table, one row each:\n")
    for r in only:
        print(f"  {r['addr']}  seed {r['seed']}  {r['direction']:<11} "
              f"census {r['census_refs']:>2} refs "
              f"({r['census_read']} read, {r['census_write']} write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
