#!/usr/bin/env python3
"""The basis a `(program, addr)` records, which is not the basis its address
alone records (issue #393).

`index.csv`'s `seed_basis` column answers "where did this function's entry
point come from", and the exporter reads that out of the seed-basis CSV the
driver writes. Both halves of that answer are per program: `seed_rows()` builds
the EC's seed set as three separate lists and seeds the common area into **both**
bank programs by design, so one address can carry a row in more than one
program and those rows can disagree -- `bank0 0x2BD5` is an `annotation` row
and `bank1 0x2BD5` is a `call-target` row, because the two banks really do
disagree about that address.

`readBasis()` used to key the map on the address and drop `f[0]`, the program.
A shared address then recorded whichever program's row the CSV wrote last,
which is a property of the row order rather than of the program being exported.
Both copies carried it -- `ExportDecompile.readBasis()` and
`TongFang.readBasis()`, the one `ExportListing` calls -- so the `.c` and the
`.asm` agreed with each other and both could be wrong. The write-up is
`../../docs/findings/seed-basis-program-key.md`.

**This module is the derivation that decides what a row *should* record**, kept
in its own file so `build_ec_decompile.py --check` and a test suite call one
implementation of it rather than two readings of it, and so neither needs
Ghidra. It reads the committed firmware and two committed CSVs and writes
nothing.

**The `common` fold is resolved here, not in the caller.** `join_index()`
de-duplicates a common-area function both banks carry identically by renaming
bank0's row to `common` and deleting bank1's, so a `common` row *is* bank0's
row under another name. Resolving it to bank0 is therefore the reading that
matches what the export did, and a caller that invented its own mapping would
be asserting against a row the pipeline never wrote.

**Two assertions, both properties rather than totals.** That every committed row
records its own program's basis, and that the seed set holds no duplicate
`(program, addr)` -- which is the shadowing a program-keyed map can actually
suffer, and the one the version of this the issue proposed cannot catch (the
common area is seeded into both banks at every common-area seed, so "no other
program has a row at this address" is false by construction and would fail on
the committed tree). The disagreement set is printed rather than asserted, so a
reader can see the exposure without a figure going stale in a document.

**What a green run is not.** It says the committed index agrees with the
derivation, not that either is right about the firmware: a basis names how an
entry point was found, and the byte-scan `call-target` it names is an upper
bound (`ec/annotations/bank-call-audit.md` §1). No hardware was read and no
register observed.

Usage:
    python3 ec/tools/seed_basis_projection.py           # the per-address table
    python3 ec/tools/seed_basis_projection.py --print   # the exposure, counted
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)

# What an index row records when its own program was never seeded at its
# address: the exporter's own fallback, spelled once so a reader comparing this
# against `ExportDecompile.java` is comparing against one definition of it.
AUTO = "auto"

# `common` is an export grouping rather than a Ghidra program: `join_index()`
# renames a folded bank0 row to `common` after the fact and deletes bank1's.
# Named rather than inlined at each use because the resolution is the whole
# reason this module can hold a `common` row to the same assertion as the rest.
COMMON_SOURCE = "bank0"


def exporter():
    """`build_ec_decompile`'s seed derivation, imported on first use.

    Deferred rather than module-level because `build_ec_decompile.py --check`
    imports *this* module, and an import in both directions is a cycle. Same
    shape as `second_copy_census.exporter_rules()`, and for the same reason:
    both are pure and read nothing but the committed files, so the second
    module object a deferred import creates while the exporter runs as
    `__main__` answers identically.
    """
    import build_ec_decompile
    return build_ec_decompile


def read_index(path):
    """Rows of a committed CSV, read strictly, or [] when it is not there."""
    if not os.path.isfile(path):
        return []
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, strict=True))


def seed_pairs(rows):
    """`(program, addr) -> basis` over the exporter's seed rows, and the
    duplicates.

    The pairs are the map's keys, so a key written twice is the one collision a
    program-keyed lookup cannot report: the second row would be dropped, and
    which of the two is the better reading is not a question a dict answers.
    `seed_rows()` de-duplicates before it returns -- keeping the strongest,
    because it sorts each program's seeds by evidence strength first -- so the
    first row is the one this keeps and the second list is empty on the
    committed inputs. It stays a check rather than a reading.
    """
    basis, seen, dupes = {}, set(), []
    for program, addr, why in rows:
        key = (program, addr)
        if key in seen:
            dupes.append(key)
            continue
        seen.add(key)
        basis[key] = why
    return basis, dupes


def derived_seeds(census=None):
    """`((program, addr) -> basis)` and the duplicate keys, off the committed
    firmware and the two committed CSVs the seed set is built from.

    `census` is the validated `bank-call-targets.csv` read, handed in rather than
    read again. `call_target_rows()` validates the whole file and refuses to
    continue on an unsound one, which is a whole-file check; a caller that
    already holds the rows -- `--check` does, having read and validated them for
    its own structural pass -- should not pay for that a second time. It is a
    parameter rather than the only way in so this module's CLI stays one command.
    """
    bld = exporter()
    with open(bld.FIRMWARE, "rb") as handle:
        firmware = handle.read()
    rows, _b0, _b1, _pd = bld.seed_rows(firmware, firmware[0x20000:0x30000],
                                        bld.call_target_rows() if census is None
                                        else census)
    return seed_pairs(rows)


def index_program(program):
    """The Ghidra program an index row's `seed_basis` was recorded for.

    Everything but `common` is its own program. `common` resolves to bank0 for
    the reason in the module docstring: it is bank0's row under a name the
    de-duplication pass gave it, and bank1's copy of the row was deleted with
    its files.
    """
    return COMMON_SOURCE if program == "common" else program


def expected_basis(row_program, addr, basis):
    """The basis a row of `row_program` at `addr` should record, `auto` when
    that program was never seeded there."""
    return basis.get((index_program(row_program), addr), AUTO)


def row_mismatches(index_rows, basis):
    """Every committed row whose `seed_basis` is not its own program's.

    `(program, addr, name, recorded, derived)` per fault. An empty list is a
    pass. This is the comparative property the address-only key could not hold:
    two programs disagreeing at one address, each reading the other's answer.
    """
    out = []
    for row in index_rows:
        want = expected_basis(row["program"], int(row["addr"], 16), basis)
        if want != row.get("seed_basis"):
            out.append((row["program"], row["addr"], row.get("name", ""),
                        row.get("seed_basis"), want))
    return out


def seed_duplicate_problems(dupes):
    """The seed set's duplicate `(program, addr)` keys, as messages."""
    return ["seed set: %s %04X is seeded twice; only one row can be recorded "
            "and a program-keyed map cannot say which of the two is the better "
            "reading" % (program, addr) for program, addr in dupes]


def index_problems(index_rows, basis, label="index.csv"):
    """`index_rows`' own mismatches, as messages.

    One entry point so `--check` and the test suite ask the same question the
    same way; the label names the committed file in the message, because the two
    indexes are two files and a message that named neither would send a reader
    to the wrong one.
    """
    return ["%s: %s %s (%s) records seed_basis=%s but its own program's seed "
            "is %s" % (label, program, addr, name, recorded, want)
            for program, addr, name, recorded, want in row_mismatches(index_rows, basis)]


def committed_basis(index_rows=None, listing_rows=None, census=None):
    """The derivation beside both committed indexes' mismatches and the seed
    set's duplicate keys -- everything `--check` asks, in one call."""
    bld = exporter()
    basis, dupes = derived_seeds(census=census)
    if index_rows is None:
        index_rows = read_index(bld.INDEX)
    if listing_rows is None:
        listing_rows = read_index(bld.LISTING_INDEX)
    problems = (index_problems(index_rows, basis, "index.csv")
                + index_problems(listing_rows, basis, "listing-index.csv")
                + seed_duplicate_problems(dupes))
    return basis, dupes, problems


def exposure_line(basis, faults):
    """The one line `--check` prints, whether or not it passed.

    The failure arm counts the rows that disagree and stops there; the green arm
    says what was checked and then names the exposure, so a reader of a passing
    run sees the addresses that *could* have moved rather than only the fact
    that none did. Both are printed by a command and asserted by neither.
    """
    if faults:
        return ("%d committed row(s) do not record their own program's basis"
                % len(faults))
    shared = shared_addresses(basis)
    disagreeing = sum(1 for v in shared.values() if len(set(v.values())) > 1)
    return ("every committed row records its own program's basis, and the seed "
            "set holds no duplicate (program, addr); %d of the %d addresses "
            "seeded into more than one program carry different bases there"
            % (disagreeing, len(shared)))


def _fmt_addr(addr):
    return "%04X" % addr


def shared_addresses(basis):
    """`addr -> {program: basis}` for every address seeded into more than one
    program, largest fan-out first then by address."""
    by_addr = {}
    for (program, addr), why in basis.items():
        by_addr.setdefault(addr, {})[program] = why
    shared = {a: v for a, v in by_addr.items() if len(v) > 1}
    return dict(sorted(shared.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def print_exposure(basis, index_rows, listing_rows):
    """The per-address table, printed.

    Every address the seed set carries in more than one program, with each
    program's own basis beside it, so a reader can see which of them disagree
    and which do not -- the distinction the whole of this is about, and the one
    a count cannot carry. The shared-but-agreeing addresses are printed too and
    are the larger half of the answer: they are what a program-keyed map changes
    nothing about, and a census that reported only the disagreeing ones would
    read as though every shared address were at risk.
    """
    shared = shared_addresses(basis)
    print("  addresses the seed set carries in more than one program: %d"
          % len(shared))
    for addr, programs in shared.items():
        verdict = "disagree" if len(set(programs.values())) > 1 else "agree"
        print("    %s  %-9s %s"
              % (_fmt_addr(addr), verdict,
                 "  ".join("%s=%s" % (p, programs[p]) for p in sorted(programs))))
    # The rows that move, which is the set the committed index has to change: a
    # row whose own program is seeded at that address on a different basis, or
    # not seeded there at all while another program is.
    print("  committed rows whose recorded basis is not their own program's:")
    for rows, label in ((index_rows, "index.csv"),
                        (listing_rows, "listing-index.csv")):
        faults = row_mismatches(rows, basis)
        print("    %s: %d" % (label, len(faults)))
        for program, addr, name, was, now in faults:
            print("      %-6s %s  %-12s -> %-12s %s"
                  % (program, addr, was, now, name))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", dest="summary", action="store_true",
                    help="the exposure counted, rather than the per-address "
                         "table")
    args = ap.parse_args(argv)
    bld = exporter()
    basis, dupes = derived_seeds()
    index_rows = read_index(bld.INDEX)
    listing_rows = read_index(bld.LISTING_INDEX)
    faults = (row_mismatches(index_rows, basis)
              + row_mismatches(listing_rows, basis)
              + seed_duplicate_problems(dupes))
    print("seed_basis_projection.py")
    if args.summary:
        shared = shared_addresses(basis)
        disagreeing = sum(1 for v in shared.values() if len(set(v.values())) > 1)
        print("  seed rows: %d over %d program(s)"
              % (len(basis), len({p for p, _ in basis})))
        print("  addresses in more than one program: %d, of which %d disagree "
              "on the basis" % (len(shared), disagreeing))
        print("  duplicate (program, addr) keys in the seed set: %d" % len(dupes))
        print("  committed rows disagreeing with their own program: %d "
              "(index.csv) and %d (listing-index.csv)"
              % (len(row_mismatches(index_rows, basis)),
                 len(row_mismatches(listing_rows, basis))))
    else:
        print_exposure(basis, index_rows, listing_rows)
    print("  all checks passed" if not faults
          else "  %d disagreement(s) above" % len(faults))
    return 0 if not faults else 1


if __name__ == "__main__":
    sys.exit(main())