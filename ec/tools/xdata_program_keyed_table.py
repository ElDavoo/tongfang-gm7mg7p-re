#!/usr/bin/env python3
"""§2's split table keyed per program, with the union key beside it, and the
partition re-keyed with them (issue #714).

`ec/annotations/xdata-register-map.md` §2 works its split table and its
three-way partition on the union `spelled_as` column, so every row of that
table is a statement about one *address number* and the main-EC rows of it mix
in what the PD image does with the same number. The CSV already carries the
answer — `spellings_by_program` (column 21) holds each program's own half, and
columns 22–33 split every reference count the same way — so this is a
**presentation** change: the same committed rows, keyed a second way.

The two keyings are both printed, per program first. They are not in
competition and neither is the correction of the other: one address number two
images both reach is **two rows** under the per-program key and **one row**
under the union key, so the per-program total is larger by exactly the number
of `both` rows. That identity is what `--check` asserts, which is why this file
holds no total of its own — see the note on `--check` below.

**The reference column follows the key, and that is the substantive half.**
Under the union key a `both` row carries one `refs` cell holding the sum over
both programs, so the union table's references double-count the 49 shared
addresses across the two address spaces. Under the per-program key each row is
one program's own `refs_main_ec` or `refs_pd`, and there is no row to
double-count. §2's published partition quoted `refs` (6,416 for the named
main-EC addresses, a figure that is neither the main EC's 6,337 nor the census
total); the figures here are `refs_main_ec` on both keyings, so the two
readings of the partition are comparable and both sum to the main EC's own
14,838.

**`0x04A3` is the one address whose partition bucket moves**, and `--moved`
prints every address that does rather than asserting there is one. It moves
because the main EC reaches it as a bare `pair-literal` and only the PD image
spells it `DAT_EXTMEM_xxxx`: the union label folds the PD half in, so the union
counts it as `DAT_EXTMEM` and the per-program key counts it in the
pair-literal-only term. `docs/findings/xdata-spelled-as-union.md` has the whole
reconciliation; this prints the move.

**Nothing here re-derives the census.** The input is one committed CSV, and
every figure below is read out of it. No image is opened, no Ghidra run, no network, no laptop, EC or
Windows machine is involved, and nothing is written anywhere: there is no
`--out-`, and no code path in this file opens a file for writing.

Usage:
    python3 xdata_program_keyed_table.py            # both keyings, as markdown
    python3 xdata_program_keyed_table.py --moved    # addresses whose bucket moves
    python3 xdata_program_keyed_table.py --check    # the relations hold
    python3 xdata_program_keyed_table.py --self-test
"""
import argparse
import collections
import csv
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
COMMITTED = HERE.parent / "annotations" / "xdata-registers.csv"

# The two programs the census splits into, in the order every table prints
# them. Held as a list rather than read off the rows being split, so a fourth
# program would land in the report's undeclared bucket instead of silently
# widening every total to include it -- the same reason
# `xdata_guard_off_row_join.py` holds `PROGRAMS`.
PROGRAMS = ("main-ec", "pd")

# The three terms of §2's partition, in the order the page prints them. A
# fourth bucket is not silently folded into one of these: `bucket()` returns
# `None` for a spelling that is none of the three and `--check` fails on it.
TERMS = ("named", "DAT_EXTMEM", "pair-only")

# Which column carries each program's references. The union key has one `refs`
# cell per row whatever the program; the per-program key has one cell per
# program, which is the whole reason the two tables' reference columns differ.
REFS_COLUMN = {"main-ec": "refs_main_ec", "pd": "refs_pd"}


def read_rows(path):
    """The register rows of a census CSV, read **by name**.

    `csv.DictReader` and never a field index, because this file exists to make
    a claim about columns 21 and 22–33 and a column that moves would turn the
    claim into a different claim that still passed. The positional
    `awk -F,` readers in `xdata-census-totals.md` and
    `xdata-export-ownership-page-census.md` depend on those columns being
    appended, which is why they are read by name here.
    """
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def halves(cell):
    """{program: that program's own spelling} for one `spellings_by_program`.

    The column's own contract is `main-ec=<spelling>` on a main-EC row, `pd=…`
    on a pd one and `main-ec=…;pd=…` on a `both` one. A clause naming a program
    this report does not declare is kept rather than dropped: `undeclared`
    below is what makes a fourth program visible rather than absent.
    """
    out = {}
    for clause in (cell or "").split(";"):
        if not clause:
            continue
        program, _, spelling = clause.partition("=")
        out[program] = spelling
    return out


def bucket(spelling):
    """Which of the three partition terms one spelling falls in, or None.

    `symbol` wins over `DAT_EXTMEM` because a union label can carry both --
    `symbol+DAT_EXTMEM` on the eleven `both` rows -- and §2's own partition
    counts those eleven in the named term and not again in the `DAT_EXTMEM`
    one. Within a program the two token spellings are disjoint, which
    `xdata_register_map.py`'s own self-test asserts, so this is a choice only
    a union label forces.

    `None` rather than a fourth bucket, so a spelling the partition does not
    cover is reported by `--check` instead of quietly inflating a term.
    """
    if "symbol" in spelling:
        return "named"
    if "DAT_EXTMEM" in spelling:
        return "DAT_EXTMEM"
    if spelling:
        return "pair-only"
    return None


def undeclared_programs(rows):
    """Every program named in `spellings_by_program` that is not in PROGRAMS."""
    seen = collections.Counter()
    for row in rows:
        for program in halves(row.get("spellings_by_program")):
            if program not in PROGRAMS:
                seen[program] += 1
    return seen


def per_program_split(rows):
    """({(program, spelling): rows}, {same: refs}) keyed on each half's own.

    One CSV row contributes **one entry per program** it carries, so a `both`
    row is counted in both address spaces. That is what makes the per-program
    total exceed the row count, and it is the identity `--check` asserts
    rather than a total this file holds.
    """
    counts, refs = collections.Counter(), collections.Counter()
    for row in rows:
        for program, spelling in halves(row.get("spellings_by_program")).items():
            counts[(program, spelling)] += 1
            refs[(program, spelling)] += int(row.get(REFS_COLUMN.get(program, ""), 0) or 0)
    return counts, refs


def union_split(rows):
    """({(program, spelled_as): rows}, {same: refs}) on the CSV's own key.

    `program` and `spelled_as` are the two columns `xdata_register_map.py`
    writes, so this is the key a reader comparing the page against the file has
    in front of them, and `refs` is the single cell the CSV carries per row.
    """
    counts, refs = collections.Counter(), collections.Counter()
    for row in rows:
        key = (row.get("program", ""), row.get("spelled_as", ""))
        counts[key] += 1
        refs[key] += int(row.get("refs", 0) or 0)
    return counts, refs


def partition(rows, per_program):
    """({term: (rows, refs)}, unplaced rows) for the main EC, on one key.

    The main EC is `main-ec` rows plus the main-EC half of every `both` row,
    which is the 1,218 §2's partition is a partition of. Under the per-program
    key a row contributes only if it *carries* a main-EC half; under the union
    key a `both` row contributes through its `program` column, so a row whose
    halves disagree about which spelling the main EC used is counted by the
    program column rather than by `spellings_by_program`.

    References are `refs_main_ec` on **both** keyings, deliberately, so the two
    readings are comparable and each sums to the main EC's own 14,838. §2's
    published 6,416 is the `refs` column, which on a `both` row is a sum over
    both programs: neither a main-EC figure nor a census total, and the write-up
    says so rather than leaving the reader to find it.
    """
    terms = {t: [0, 0] for t in TERMS}
    unplaced = 0
    for row in rows:
        if per_program:
            spelling = halves(row.get("spellings_by_program")).get("main-ec")
            if spelling is None:
                continue
        else:
            if row.get("program") not in ("main-ec", "both"):
                continue
            spelling = row.get("spelled_as", "")
        term = bucket(spelling)
        if term is None:
            unplaced += 1
            continue
        terms[term][0] += 1
        terms[term][1] += int(row.get("refs_main_ec", 0) or 0)
    return ({t: tuple(v) for t, v in terms.items()}, unplaced)


def bucket_moves(rows):
    """[(addr, union bucket, per-program bucket)] for addresses that change.

    An address the main EC does not touch cannot move, so only rows with a
    main-EC half are compared -- and the comparison is between the union label
    and the main-EC half, which is the comparison §2's two partitions actually
    disagree about. The eleven `symbol+DAT_EXTMEM` rows do **not** appear: both
    labels bucket as `named`, so relabelling a row is not moving an address
    between terms, and a report that listed them would be reporting a rename as
    a move.
    """
    moves = []
    for row in rows:
        main = halves(row.get("spellings_by_program")).get("main-ec")
        if main is None:
            continue
        union_label = row.get("spelled_as", "")
        was, now = bucket(union_label), bucket(main)
        if was is not None and was != now:
            moves.append((row.get("addr", ""), was, now, union_label, main))
    return sorted(moves)


def markdown_table(counts, refs, keys, stream):
    """One `| program | spelling | rows | references |` block, total row last."""
    print("| program | spelling | distinct | references |", file=stream)
    print("|---|---|---:|---:|", file=stream)
    total_rows = total_refs = 0
    for key in sorted(keys):
        rows, ref = counts[key], refs[key]
        total_rows += rows
        total_refs += ref
        print(f"| {key[0]} | `{key[1]}` | {rows:,} | {ref:,} |", file=stream)
    print(f"| **total** | | **{total_rows:,}** | **{total_refs:,}** |", file=stream)
    return total_rows, total_refs


def provenance(path, rows, stream):
    """The line naming the input, so "re-runnable" also means reproducible.

    Path, row count and SHA-256 together, because a figure a reader re-derives
    is only the same figure if it came off the same bytes: the path says which
    file, the row count says what was read, and the digest is what settles the
    third question when a second branch has edited the CSV.
    """
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    print(f"<!-- source: {path} -- {len(rows)} rows -- sha256 {digest} -->",
          file=stream)


def partition_table(part, unplaced, stream):
    """§2's three-way partition for one keying, on the main-EC basis."""
    print("| term | distinct | main-EC references |", file=stream)
    print("|---|---:|---:|", file=stream)
    for term in TERMS:
        rows, ref = part[term]
        print(f"| {term} | {rows:,} | {ref:,} |", file=stream)
    print(f"| **total** | **{sum(part[t][0] for t in TERMS):,}** | "
          f"**{sum(part[t][1] for t in TERMS):,}** |", file=stream)
    if unplaced:
        print(f"| **{unplaced} row(s) in no term** | | |", file=stream)


def check(rows, stream=sys.stdout):
    """The relations, asserted against each other.

    **No total of the census is written here**, and that is the whole design.
    `1,375`, `850` and `7,534` are values a landing change moves, and a check
    that held one would be a number every branch has to remember to bump --
    which is the defect `CLAUDE.md` names. What is asserted instead is that the
    two keyings *relate* the way the prose says they do, so a drift shows up as
    a relation failing rather than as a stale numeral.

    Returns True when every relation held.
    """
    counts, refs = per_program_split(rows)
    u_counts, u_refs = union_split(rows)
    per_part, per_unplaced = partition(rows, True)
    union_part, union_unplaced = partition(rows, False)
    per_total_rows = sum(counts.values())
    per_total_refs = sum(refs.values())
    union_total_rows = sum(u_counts.values())
    union_total_refs = sum(u_refs.values())
    per_main_rows = sum(n for (p, _), n in counts.items() if p == "main-ec")
    per_pd_rows = sum(n for (p, _), n in counts.items() if p == "pd")
    per_main_refs = sum(r for (p, _), r in refs.items() if p == "main-ec")
    per_pd_refs = sum(r for (p, _), r in refs.items() if p == "pd")
    both_rows = sum(1 for r in rows if r.get("program") == "both")
    disagree = sum(1 for r in rows
                   if r.get("program") == "both"
                   and len(set(halves(r.get("spellings_by_program")).values())) > 1)
    undeclared = undeclared_programs(rows)
    ok = True

    def check_relation(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}", file=stream)
        if not cond:
            ok = False

    print("xdata_program_keyed_table.py --check", file=stream)
    check_relation("the CSV's rows read by name, and every row carries a "
                   "spellings_by_program clause",
                   all(r.get("spellings_by_program") for r in rows))
    check_relation("no program outside the declared split is named in the "
                   "column", not undeclared)
    if undeclared:
        print("        undeclared: "
              + ", ".join(f"{p} {n}" for p, n in sorted(undeclared.items())),
              file=stream)
    check_relation("the per-program total exceeds the union total by exactly "
                   "the number of `both` rows",
                   per_total_rows - union_total_rows == both_rows)
    check_relation("the per-program total is the two programs' own addresses, "
                   "added",
                   per_total_rows == per_main_rows + per_pd_rows)
    check_relation("the per-program references are the two programs' own "
                   "references, added",
                   per_total_refs == per_main_refs + per_pd_refs)
    check_relation("references do not move under the re-key: the per-program "
                   "reference total is the CSV's `refs` total",
                   per_total_refs == union_total_refs)
    check_relation("the main EC's per-program address count equals the main "
                   "EC's under the union key",
                   per_main_rows == sum(per_part[t][0] for t in TERMS))
    check_relation("the union key's `both` rows are the rows the per-program "
                   "key counts twice",
                   per_total_rows == union_total_rows + both_rows)
    check_relation("fewer `both` rows disagree between halves than there are "
                   "`both` rows, and the disagreement is a subset",
                   disagree <= both_rows)
    for label, part, unplaced in (("per-program", per_part, per_unplaced),
                                  ("union", union_part, union_unplaced)):
        check_relation(f"the {label} partition places every main-EC row",
                       unplaced == 0)
        check_relation(f"the {label} partition's three terms sum to the main "
                       f"EC's distinct address count",
                       sum(part[t][0] for t in TERMS) == per_main_rows)
        check_relation(f"the {label} partition's three reference terms sum to "
                       f"the main EC's reference count",
                       sum(part[t][1] for t in TERMS) == per_main_refs)
    check_relation("the per-program and union partitions differ in the "
                   "pair-literal term by exactly the addresses whose bucket "
                   "moves",
                   per_part["pair-only"][0] - union_part["pair-only"][0]
                   == len(bucket_moves(rows)))
    return ok


# --------------------------------------------------------------------------
# --self-test. Known-answer over fixtures written here rather than read from
# the tree, so each derivation is exercised on a shape the committed census
# does not happen to have: a `both` row whose halves disagree, an address that
# moves bucket, an undeclared fourth program, a spelling in no partition term.
# --------------------------------------------------------------------------

FIXTURE_HEADER = ("addr,program,spelled_as,refs,spellings_by_program,"
                  "refs_main_ec,refs_pd\n")

FIXTURE_ROWS = [
    # A `both` row whose halves agree: one row, two program-addresses, and the
    # union label's `refs` is the sum of the two per-program cells.
    ("0x0001,both,DAT_EXTMEM,7,main-ec=DAT_EXTMEM;pd=DAT_EXTMEM,6,1"),
    # The row that moves bucket: the main EC reaches it as a bare pair literal
    # and only the PD image spells it DAT_EXTMEM, so the union label counts it
    # as DAT_EXTMEM and the per-program key does not.
    ("0x04A3,both,DAT_EXTMEM+pair-literal,8,main-ec=pair-literal;pd=DAT_EXTMEM,7,1"),
    # A `both` row whose halves are mixed inside the main EC.
    ("0x0834,both,DAT_EXTMEM+pair-literal,66,"
     "main-ec=DAT_EXTMEM+pair-literal;pd=DAT_EXTMEM,48,18"),
    # A `both` row named in the EC and spelled DAT_EXTMEM by the PD image: a
    # union label carrying both tokens, which buckets as `named` either way.
    ("0x07D3,both,symbol+DAT_EXTMEM,5,main-ec=symbol;pd=DAT_EXTMEM,4,1"),
    # A main-EC-only row carrying a token spelling alongside the pair literal.
    ("0x0002,main-ec,symbol+pair-literal,3,main-ec=symbol+pair-literal,3,0"),
    # A pd-only row.
    ("0x0003,pd,DAT_EXTMEM,4,pd=DAT_EXTMEM,0,4"),
]

# Held apart from the six above because it is the one shape that makes the
# reference reconciliation *fail*, and that failure is the behaviour being
# tested: a program this report does not declare has no reference column, so
# its row's references cannot be attributed and every total over the file
# would be short by exactly them. Keeping it in the same fixture would have had
# to weaken the positive invariant below to accommodate it.
UNDECLARED_ROW = "0x0004,both,DAT_EXTMEM,9,main-ec=DAT_EXTMEM;ps2=DAT_EXTMEM,8,1"


def fixture_rows(extra=()):
    """Fixture lines as a list of dicts, in the column order the header names."""
    out = []
    for line in list(FIXTURE_ROWS) + list(extra):
        fields = dict(zip(FIXTURE_HEADER.strip().split(","), line.split(",")))
        out.append(fields)
    return out


def self_test(stream=sys.stdout) -> bool:
    """Known-answer run over the fixtures above. No census, no firmware."""
    rows = fixture_rows()
    ok = True

    def check(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}", file=stream)
        if not cond:
            ok = False

    counts, refs = per_program_split(rows)
    per_part, per_unplaced = partition(rows, True)
    union_part, union_unplaced = partition(rows, False)
    moves = bucket_moves(rows)
    third = fixture_rows([UNDECLARED_ROW])
    third_counts, third_refs = per_program_split(third)

    print("xdata_program_keyed_table.py --self-test", file=stream)
    check("the per-program total is the union total plus the `both` rows",
          sum(counts.values()) == len(rows) + sum(
              1 for r in rows if r["program"] == "both"))
    check("references do not move under the re-key: the fixture's 93 `refs` "
          "are 93 under the per-program key too",
          sum(refs.values()) == sum(int(r["refs"]) for r in rows) == 93)
    check("`halves()` reads both halves of a `both` clause and one of a "
          "single-program one",
          halves("main-ec=pair-literal;pd=DAT_EXTMEM")
          == {"main-ec": "pair-literal", "pd": "DAT_EXTMEM"}
          and halves("pd=DAT_EXTMEM") == {"pd": "DAT_EXTMEM"})
    check("a union label carrying both tokens buckets as `named`, not as "
          "either token's own term",
          bucket("symbol+DAT_EXTMEM") == "named")
    check("`bucket()` returns None for a spelling in no term rather than "
          "folding it into one",
          bucket("") is None)
    check("the per-program partition places every row (no unplaced)",
          per_unplaced == 0 and union_unplaced == 0)
    check("both partitions place the five main-EC rows, and the two keyings "
          "differ only in which term `0x04A3` is counted in",
          sum(per_part[t][0] for t in TERMS) == 5
          and sum(union_part[t][0] for t in TERMS) == 5
          and per_part["pair-only"][0] == 1 and union_part["pair-only"][0] == 0
          and per_part["DAT_EXTMEM"][0] == 2 and union_part["DAT_EXTMEM"][0] == 3)
    check("`0x04A3` is the only row whose bucket moves, and it moves from "
          "`DAT_EXTMEM` to `pair-only`",
          [(m[0], m[1], m[2]) for m in moves]
          == [("0x04A3", "DAT_EXTMEM", "pair-only")])
    check("a relabelled row is not a moved address: the `symbol+DAT_EXTMEM` "
          "row buckets the same both ways",
          not [m for m in moves if m[0] == "0x07D3"])
    check("the per-program split counts a `both` row in both address spaces: "
          "five fixture rows carry a `pd=DAT_EXTMEM` clause, and one main-EC "
          "row is a bare `pair-literal`",
          counts[("pd", "DAT_EXTMEM")] == 5
          and counts[("main-ec", "pair-literal")] == 1)
    check("the per-program references come from the per-program columns, so a "
          "`both` row contributes each program's own count and not the row's "
          "summed 66",
          refs[("main-ec", "DAT_EXTMEM+pair-literal")] == 48
          and refs[("pd", "DAT_EXTMEM")] == 25)
    check("an undeclared program is reported rather than dropped",
          undeclared_programs(third) == {"ps2": 1}
          and undeclared_programs(rows) == {})
    check("an undeclared program makes the reference reconciliation fail "
          "rather than passing on a total that is short by its row: the "
          "clause is counted in a bucket of its own and its one reference is "
          "attributable to nobody",
          third_counts[("ps2", "DAT_EXTMEM")] == 1
          and sum(third_refs.values())
          == sum(int(r["refs"]) for r in third) - 1)
    return ok


def report(path, stream=sys.stdout):
    """Print both keyings and both partitions, each under its provenance."""
    rows = read_rows(path)
    provenance(path, rows, stream)

    counts, refs = per_program_split(rows)
    print("\n## Per program: each row's own `spellings_by_program` clause\n",
          file=stream)
    print("One address number two images both reach is **two rows** here and "
          "**one row** in the table below; the per-program references are "
          "`refs_main_ec` and `refs_pd`, so no row here double-counts a "
          "`both` address across the two spaces.\n", file=stream)
    print(f"- program-addresses: **{sum(counts.values()):,}** "
          f"({sum(n for (p, _), n in counts.items() if p == 'main-ec'):,} main "
          f"EC + {sum(n for (p, _), n in counts.items() if p == 'pd'):,} pd)",
          file=stream)
    print(f"- references: **{sum(refs.values()):,}** "
          f"({sum(r for (p, _), r in refs.items() if p == 'main-ec'):,} main "
          f"EC + {sum(r for (p, _), r in refs.items() if p == 'pd'):,} pd)\n",
          file=stream)
    per_rows, per_refs = markdown_table(counts, refs, sorted(counts), stream)

    u_counts, u_refs = union_split(rows)
    print("\n## Union key: the CSV's own `program` + `spelled_as` columns\n",
          file=stream)
    print("The key `xdata_register_map.py` writes, kept so a reader comparing "
          "this page against the CSV has the table that reads it directly. "
          "`refs` is one cell per row, so on a `both` row it is the sum over "
          "both programs.\n", file=stream)
    print(f"- rows: **{sum(u_counts.values()):,}** — this is the figure the "
          f"H1 above and the rest of the map carry, because the CSV has this "
          f"many rows", file=stream)
    print(f"- references: **{sum(u_refs.values()):,}**\n", file=stream)
    union_rows, union_refs = markdown_table(u_counts, u_refs, sorted(u_counts),
                                            stream)

    print(f"\n## The partition of the main EC, per program "
          f"({per_rows:,} addresses is the union key's {union_rows:,} plus "
          f"{per_rows - union_rows:,} `both` rows)\n", file=stream)
    per_part, per_unplaced = partition(rows, True)
    partition_table(per_part, per_unplaced, stream)

    print("\n## The same partition on the union key\n", file=stream)
    union_part, union_unplaced = partition(rows, False)
    partition_table(union_part, union_unplaced, stream)
    print("\nBoth partitions quote `refs_main_ec`, so each sums to the main "
          "EC's own references and the two are comparable. `docs/findings/"
          "xdata-register-map-per-program-keying.md` is the write-up.",
          file=stream)

    moves = bucket_moves(rows)
    print(f"\n## Addresses whose partition bucket moves: {len(moves)}\n",
          file=stream)
    print("| address | union key | per program | union label | main-EC half |",
          file=stream)
    print("|---|---|---|---|---|", file=stream)
    for addr, was, now, label, main in moves:
        print(f"| `{addr}` | {was} | {now} | `{label}` | `{main}` |",
              file=stream)
    return per_rows, per_refs, union_rows, union_refs


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true",
                       help="assert the relations between the two keyings; "
                            "no census is run")
    modes.add_argument("--self-test", action="store_true",
                       help="known-answer run over fixtures written in this "
                            "file; no census, no image, no Ghidra")
    modes.add_argument("--moved", action="store_true",
                       help="print only the addresses whose partition bucket "
                            "moves between the two keyings")
    ap.add_argument("--registers", default=str(COMMITTED),
                    help=f"per-address census CSV to read (default: {COMMITTED})")
    args = ap.parse_args()

    if args.self_test:
        return 0 if self_test() else 1
    if args.check:
        return 0 if check(read_rows(args.registers)) else 1
    if args.moved:
        for addr, was, now, label, main in bucket_moves(read_rows(args.registers)):
            print(f"{addr}\t{was} -> {now}\t{label}\t{main}")
        return 0
    report(args.registers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
