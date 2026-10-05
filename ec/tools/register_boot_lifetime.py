#!/usr/bin/env python3
"""What the EC's reset path leaves at every XDATA address `registers.yaml` names.

**The question this answers, and why no column in the tree answers it.**
Whether a mapped byte is firmware-initialised or residue. `registers.yaml`
records a register's reference count, its access direction and its `status:`;
`boot-xdata_sites.csv` records what the reset path's walk did to an address --
but nothing joins them, so "does the EC wipe this register on every reset" is a
question a driver author has to answer by hand, per register, from a per-address
table that is not keyed by register. A register the reset path clears cannot
carry a value across a suspend/resume; a register it does not touch is a
deliberate exception. That is a property of the byte, and this is its table.

**The walk is `boot_xdata_sites.py`'s, not this file's.** Imported, executed
once, and its `verdict()` called per address; the five verdict tokens are
delegated verbatim rather than re-spelled, so a token added there reaches here
without an edit here. Nothing in this file models an 8051 instruction.

**`not-reached` is the token that does the work, and it comes free.** The walk
has a verdict for an address it never held in DPTR, and that verdict is what
this tool's rows would otherwise be missing. The addresses that get it are the
interesting ones: they are outside every range the boot path clears, so nothing
in the reset path writes them and a value read there afterwards is whatever the
previous session left. Reporting them as *absent from the table* instead would be
indistinguishable from *not yet surveyed*, and a reader could not tell which.

**The join is on the address, and it is a join, not a copy.** One row per
`registers.yaml` address. Two `registers.yaml` entries naming the same address
would be a silent collapse; `check_joins()` refuses rather than emitting one
row for two claims. The symbol spelling is `gen_xdata_symbols.py`'s -- it is the
module that owns the rule, and a second naming rule here is a second answer to
its question -- so this table's `symbol` column is by construction the string
`ec/ghidra/xdata-symbols.csv` carries for the same address.

**The walk is not the only writer, and this table does not claim it is.**
`not-reached` is scoped to *this walk*, exactly as `boot_xdata_sites.py` scopes
it: it does not exclude an indirect or DPTR-handed store from a routine the walk
never entered. `../annotations/xdata-0440-readers.md` §7.5 names that population
and nothing here searches it. A register that reads `not-reached` is therefore
"nothing in the executed reset path stores it", never "nothing does".

**Nothing here was observed on hardware.** Every verdict is a static execution
of committed bytes in `ec/firmware/GMxMGxx_11.800`. No EC was powered and no
register was read back. Whether anything re-clears these addresses later, and
whether the `0x07FD`-`0x07FF` carve-out is load-bearing or incidental, are open
and need the physical machine.

`--csv` writes `../annotations/register-boot-lifetime.csv` and `--check` diffs
against it byte for byte, the way `trace_xdata_refs.check_table()` does (with
`newline=""`, because the committed tables carry the csv module's own CRLF
terminator). `--self-test` holds the properties rather than a census: every
`registers.yaml` address resolves to exactly one verdict, the three carve-out
addresses read `spared` where their neighbours read `cleared`, and an address
outside every walked range reads `not-reached` rather than being dropped.

**Not in `.github/scripts/agent-gates.sh`, and cannot be from an agent branch.**
The plan-stage push token has no `workflow` scope, so a branch touching that
script fails at the end rather than the start. `../docs/findings/` carries the
reason at greater length; `--check` and `--self-test` are runnable from the repo
root with no arguments but this file's path.

Usage:
    python3 register_boot_lifetime.py                 # write the CSV
    python3 register_boot_lifetime.py --check
    python3 register_boot_lifetime.py --self-test
    python3 register_boot_lifetime.py --report
"""
import argparse
import collections
import csv
import io
import os
import sys

import yaml

from boot_xdata_sites import (DEFAULT_FIRMWARE, VERDICTS, boot_stubs,
                              boot_value, verdict, walk_boot)
from gen_xdata_symbols import (OVERRIDES, as_addrs, build_rows, load_overrides)
from trace_xdata_refs import check_table

HERE = os.path.dirname(os.path.abspath(__file__))
EC_DIR = os.path.join(HERE, os.pardir)
ANNOT = os.path.join(EC_DIR, "annotations")
REGISTERS = os.path.join(ANNOT, "registers.yaml")
LIFETIME_CSV = os.path.join(ANNOT, "register-boot-lifetime.csv")

# The CSV's columns. `symbol` is `gen_xdata_symbols`' own spelling, so a reader
# can paste it into a decompilation; `from_register` is `registers.yaml`'s entry
# name verbatim, parens and all, because the two differ (`OEM_4` is emitted as
# `OEM_4_CHARGING_PROFILE`) and collapsing them loses which string the name is
# derived from. `boot_verdict` and `boot_value` are the walk's own two columns,
# delegated rather than re-spelled: `boot_value` is `none` for a byte the walk
# did not write at all, which is not the same statement as a zero it stored.
CSV_COLUMNS = ["addr", "symbol", "from_register", "boot_verdict", "boot_value"]


class Refusal(Exception):
    """A join this tool declines to print, carrying the reason it names.

    The same shape as `boot_xdata_sites.Refusal` and for the same reason: every
    way this fails is a table that looks complete and is not. A register
    address dropped for want of a symbol, or two entries collapsed into one row,
    both read as an answer.
    """


def load_registers(path: str = REGISTERS) -> list:
    """The `registers.yaml` entries, as committed.

    A file that cannot be read as that shape is a refusal rather than an
    `IndexError`: the caller is about to print a table keyed by these entries,
    and an empty list would produce a table with no rows that reads as "no
    register is affected".
    """
    try:
        with open(path) as handle:
            doc = yaml.safe_load(handle)
    except OSError as exc:
        raise Refusal(f"{path} cannot be read: {exc.strerror}")
    except yaml.YAMLError as exc:
        # A parser error is the same failure as a missing key and gets the same
        # treatment: the file is not the register map, so the join has no left
        # side. Letting it through as a traceback would say less and stop the
        # caller from printing anything about it.
        raise Refusal(f"{path} is not readable as YAML: {exc}")
    if not isinstance(doc, dict) or not isinstance(doc.get("registers"), list):
        raise Refusal(f"{path} has no top-level `registers` list, so the join "
                      "has no left-hand side; the table would be empty and "
                      "read as 'no register is affected'")
    return doc["registers"]


def register_addresses(entries: list) -> list:
    """(address, entry name) for every address in `entries`, in file order.

    `status:` is read out of the entry by whoever grades it and is deliberately
    not carried here: lifetime is not a status, and a column that put the two
    side by side would invite reading one as a grade on the other.

    `as_addrs()` normalises the scalar-or-list `addr:` field and rejects a
    non-integer, so this file does not repeat that rule. An entry with no
    `addr:` is a refusal rather than a skip: it is a register row whose address
    the join cannot place, and dropping it would leave a table that looks like a
    complete answer over the registers that *do* have addresses.
    """
    out = []
    for entry in entries:
        if "addr" not in entry:
            raise Refusal(
                f"entry {entry.get('name', '?')!r} has no `addr:`; the join "
                "cannot place it, and dropping it would leave a table that "
                "looks complete")
        name = str(entry.get("name", ""))
        for addr in as_addrs(entry):
            if not 0 <= addr <= 0xFFFF:
                raise Refusal(
                    f"entry {name!r} carries address 0x{addr:X}, which is "
                    "outside the 16-bit XDATA space this tool joins over")
            out.append((addr, name))
    return out


def symbols(entries: list, overrides_path: str = OVERRIDES) -> dict:
    """{address: the Ghidra symbol spelling}, from `gen_xdata_symbols.build_rows`.

    Delegated rather than re-derived: the scalar-name / name-split / override
    rules belong to that module, and a second naming rule here would be a second
    answer to the question `ec/ghidra/xdata-symbols.csv` already answers.

    **An address that module could not name is a refusal, not a blank cell.**
    `build_rows()` reports those separately and its own `--check` fails on them;
    carrying on here would put a register in the table with no symbol, which
    reads as "this register has no name" rather than "the join stopped".
    """
    rows, unresolved = build_rows(entries, load_overrides(overrides_path))
    if unresolved:
        listed = ", ".join(f"0x{addr:04X}" for addr in sorted(unresolved))
        raise Refusal(
            f"gen_xdata_symbols could not name {len(unresolved)} address(es) "
            f"({listed}); the table is refused rather than written with a blank "
            f"symbol. Name them in {overrides_path} and re-run")
    return {int(row["addr"], 16): row for row in rows}


def check_joins(joined: list) -> None:
    """Refuse a join whose rows do not partition the register addresses.

    Two entries naming one address would emit two rows for it, and one row can
    carry only one `from_register` -- so a reader could not tell which entry's
    claim the row is making, and two rows for one byte reads as a table with a
    duplicate rather than as an ambiguity. Every address appearing exactly once
    is a property of the join rather than a count of it, which is why it is a
    refusal here and not a figure in the prose.
    """
    seen = collections.Counter(addr for addr, _name in joined)
    duplicated = sorted(addr for addr, count in seen.items() if count > 1)
    if duplicated:
        listed = ", ".join(f"0x{addr:04X}" for addr in duplicated)
        raise Refusal(
            f"{len(duplicated)} address(es) ({listed}) are named by more than "
            "one registers.yaml entry; one row per address cannot say which "
            "entry's claim it carries, so the join is refused rather than "
            "picking one")


def build_rows_for_registers(entries: list, machine, overrides_path: str = OVERRIDES):
    """The joined rows, one per `registers.yaml` address, in file order."""
    names = symbols(entries, overrides_path)
    joined = register_addresses(entries)
    check_joins(joined)
    stored = machine.stored()
    rows = []
    for addr, name in joined:
        row = names.get(addr)
        if row is None:
            # `build_rows()` resolves every address it reports and `symbols()`
            # refuses on the ones it does not, so this is unreachable rather
            # than handled -- said here so a future change to that refusal
            # surfaces as a `KeyError` naming the address rather than a row
            # with an empty symbol.
            raise Refusal(
                f"0x{addr:04X} has no symbol from gen_xdata_symbols; the join "
                "stopped rather than print a row with no name in it")
        rows.append({
            "addr": f"0x{addr:04X}",
            "symbol": row["name"],
            "from_register": name,
            "boot_verdict": verdict(addr, machine, stored),
            "boot_value": boot_value(addr, machine, stored),
        })
    return rows


def render(rows: list) -> str:
    """The `--csv` table as a string, so `--check` diffs the same bytes.

    CRLF is the csv module's own terminator and the one the committed tables
    carry; writing it explicitly rather than leaving it to the platform is what
    makes a regenerated file diff clean on any checkout.
    """
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def runs(addresses) -> list:
    """A sorted address set as inclusive (lo, hi) runs.

    The verdict split is the table's whole point and a per-address list is
    not readable; the runs are the form both are readable in. Formatting, not a
    measurement, so it is deliberately not `boot_xdata_sites._ranges` -- that
    one answers for XDATA bytes the walk touched and this one answers for
    registers, and sharing the name would suggest the population is shared.
    """
    out = []
    for addr in sorted(addresses):
        if out and addr == out[-1][1] + 1:
            out[-1][1] = addr
        else:
            out.append([addr, addr])
    return [(lo, hi) for lo, hi in out]


def report(rows: list, machine) -> str:
    """The `--report` block: the verdict split, as address runs.

    The split is printed rather than the rows because the rows are the table and
    the split is what a reader asks for first -- "how many registers does the
    reset path leave alone", which `--csv` answers in a form nobody reads by
    hand. The run lines carry their own extent so neither answer needs the
    other.
    """
    by_verdict = collections.defaultdict(list)
    for row in rows:
        by_verdict[row["boot_verdict"]].append(int(row["addr"], 16))
    lines = [f"register boot lifetime over {len(rows)} registers.yaml "
             f"address(es), from the walk in boot_xdata_sites.py:"]
    for token in VERDICTS:
        addresses = by_verdict.get(token)
        if not addresses:
            continue
        lines.append(f"  {token} ({len(addresses)}):")
        for lo, hi in runs(addresses):
            extent = (f"0x{lo:04X}" if lo == hi
                      else f"0x{lo:04X}-0x{hi:04X}")
            lines.append(f"    {extent}")
    lines.append("")
    lines.append("  a verdict is about the reset path's executed walk and this")
    lines.append("  walk only. `not-reached` does not exclude an indirect or")
    lines.append("  DPTR-handed store from a routine the walk never entered --")
    lines.append("  xdata-0440-readers.md §7.5 names that population, and")
    lines.append("  nothing here searches it.")
    return "\n".join(lines)


def self_test(image: bytes, registers_path: str = REGISTERS) -> int:
    """Known answers against the committed image, then the refusals.

    The answers are properties of the join and of two carve-out addresses read
    off `../docs/findings/reset-vector-dptr-targets.md`, which reached its three
    spared bytes by executing the same instructions. No figure of the tree is
    asserted: a census would be a value every landing register moves.
    """
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f"  {label}: got {got!r}, want {want!r}")

    entries = load_registers(registers_path)
    machine = walk_boot(image, stubs=boot_stubs())
    rows = build_rows_for_registers(entries, machine)
    stored = machine.stored()
    walked = machine.walked_set()

    # Every address resolves, exactly once, and to a token the walk itself
    # defines. A row with a verdict from outside `VERDICTS` would be a spelling
    # this file invented, which is the one thing the delegation rules out.
    check("every row's verdict is a boot_xdata_sites token",
          sorted({r["boot_verdict"] for r in rows}
                 - set(VERDICTS)), [])
    check("the join partitions the register addresses",
          len({r["addr"] for r in rows}), len(rows))
    check("every registers.yaml address got a row",
          len(rows), len(register_addresses(entries)))

    # The carve-out. `reset-vector-dptr-targets.md`'s three spared bytes, against
    # the walks that reached them: `0x0F75` and `0xD96C` each step over them and
    # store every neighbour. If the spared set moved, these three would read
    # `cleared` and this is where it would surface.
    for addr in (0x07FD, 0x07FE, 0x07FF):
        check(f"verdict 0x{addr:04X}", verdict(addr, machine, stored), "spared")
    check("their in-range neighbours are cleared",
          [verdict(a, machine, stored) for a in (0x07FC, 0x0800)],
          ["cleared", "cleared"])

    # The walk's own tokens on the vector's own stores, which is what makes
    # `cleared` and `written` different words: `0x1001` is written a known value
    # by the vector's body, `0x0004` is written a value nothing here
    # established. Both are `registers.yaml`-shaped questions asked of the
    # walk rather than of the table, because neither address is a register.
    check("verdict 0x1001", verdict(0x1001, machine, stored), "written")
    check("verdict 0x0004", verdict(0x0004, machine, stored), "written-unknown")

    # An address outside every walked range is `not-reached`, and -- the half
    # that matters -- the table still carries a row for it. This is a fixture
    # rather than a figure: `0x3202` is named by a `registers.yaml` entry today,
    # and naming a new register near it must not turn the token's own test into
    # a census of the register map.
    outside = 0x3202
    check(f"verdict 0x{outside:04X} (outside every walked range)",
          verdict(outside, machine, stored), "not-reached")
    check("...and the walk reached no part of it",
          outside in stored or outside in walked, False)
    check("a `not-reached` row carries boot_value `none`",
          sorted({r["boot_value"] for r in rows
                  if r["boot_verdict"] == "not-reached"}), ["none"])
    check("every table row is in the delegated vocabulary",
          sorted({r["boot_verdict"] for r in rows} - set(VERDICTS)), [])

    # The refusals. Each is an input that would yield a table looking complete
    # with its guard removed.
    def refuses(label, thunk):
        try:
            thunk()
        except Refusal:
            return
        failures.append(f"  {label}: the join completed instead of refusing")

    refuses("two entries naming one address",
            lambda: check_joins([(0x0043, "a"), (0x0043, "b")]))
    refuses("an entry with no addr",
            lambda: register_addresses([{"name": "no address here"}]))
    refuses("an address outside the XDATA space",
            lambda: register_addresses([{"name": "far", "addr": 0x1FFFF}]))
    refuses("a file that is not the register map",
            lambda: load_registers(os.path.join(HERE, "gen_xdata_symbols.py")))

    if failures:
        print("self-test FAILED:", file=sys.stderr)
        for line in failures:
            print(line, file=sys.stderr)
        return 1
    print("register_boot_lifetime self-test: all assertions passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registers", default=REGISTERS,
                    help="registers.yaml to read (default: %(default)s)")
    ap.add_argument("--firmware", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: %(default)s)")
    ap.add_argument("--overrides", default=OVERRIDES,
                    help="gen_xdata_symbols overrides (default: %(default)s)")
    ap.add_argument("--out", default=LIFETIME_CSV,
                    help="CSV to write (default: %(default)s)")
    ap.add_argument("--report", action="store_true",
                    help="print the verdict split as address runs instead of "
                         "writing the CSV")
    ap.add_argument("--check", nargs="?", const=LIFETIME_CSV, metavar="PATH",
                    help="diff this run against a committed table and exit "
                         "non-zero on any difference (default: "
                         "register-boot-lifetime.csv)")
    ap.add_argument("--self-test", action="store_true",
                    help="known answers against the committed image and "
                         "registers.yaml, then the refusals")
    args = ap.parse_args(argv)

    if args.check is not None and args.report:
        ap.error("--report and --check answer different questions; pick one")

    try:
        with open(args.firmware, "rb") as handle:
            image = handle.read()
        if args.self_test:
            return self_test(image, args.registers)

        machine = walk_boot(image, stubs=boot_stubs())
        rows = build_rows_for_registers(load_registers(args.registers),
                                        machine, args.overrides)
        text = render(rows)

        if args.report:
            print(report(rows, machine))
            return 0
        if args.check is not None:
            return check_table(text, args.check)

        with open(args.out, "w", newline="") as handle:
            handle.write(text)
        print(f"wrote {args.out}: {len(rows)} registers, one row each")
        return 0
    except Refusal as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"note: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())