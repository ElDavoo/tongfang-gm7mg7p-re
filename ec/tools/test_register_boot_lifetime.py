#!/usr/bin/env python3
"""`register_boot_lifetime.py`'s join, on inputs it can be wrong about.

**What this file stands in for.** The tool's own `--self-test` runs the join
against the committed `registers.yaml` and `ec/firmware/GMxMGxx_11.800`: every
address resolves, the three carve-out bytes read `spared` beside neighbours that
read `cleared`, and the refusals fire. That is the measurement the write-up
rests on.

This file is the half `--self-test` cannot be. Every join case here is a
**hand-built `registers.yaml`** written to a temporary directory, so the join is
tested where the committed file could only test it by agreeing with itself: a
tool whose `not-reached` handling were wrong would still produce a table over
the committed registers, because most of them fall inside the boot path's
cleared ranges. `JoinFixtureCases` puts an address outside every one of them in
and reads what comes out.

The two cases that do read the committed tree assert the tree, not the tool's
arithmetic: the `0x07FD`-`0x07FF` rows in `register-boot-lifetime.csv` say
`spared` where the byte below and above say `cleared`, and the two vectors'
reason for that is read out of `../docs/findings/reset-vector-dptr-targets.md`'s
subject rather than out of a number this suite derived.

**Refusals are half the file.** A join that quietly drops an address it cannot
name, or collapses two entries onto one address, emits a table that looks
complete -- which is the failure `--check` cannot see, because the table it
compares against was produced by the same code.

No hardware, no network, no Ghidra. The two cases that need the firmware read
the committed image; everything else builds its own bytes.
"""
import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# register_boot_lifetime imports boot_xdata_sites, gen_xdata_symbols and
# trace_xdata_refs by bare module name, so the tool directory has to be on the
# path before the tool is loaded rather than after.
sys.path.insert(0, str(HERE))
import boot_xdata_sites as B          # noqa: E402
import register_boot_lifetime as R    # noqa: E402

TOOL = HERE / "register_boot_lifetime.py"
LIFETIME_CSV = HERE.parent / "annotations" / "register-boot-lifetime.csv"


def registers_yaml(*entries):
    """A `registers.yaml` body from `(name, addr, status)` triples, as text.

    Written by hand rather than through `yaml.safe_dump` so a fixture that
    stops parsing fails as a fixture rather than as a dump-format change.
    """
    lines = ["registers:"]
    for name, addr, status in entries:
        lines.append(f"  - name: {name}")
        lines.append(f"    addr: 0x{addr:04X}")
        lines.append(f"    status: {status}")
    return "\n".join(lines) + "\n"


class JoinFixtureCases(unittest.TestCase):
    """The join on hand-built register maps, against a hand-built walk.

    The walk is a `Machine` this file fills rather than one the tool executes:
    these cases are about how a verdict becomes a row, and running the real
    8051 walk behind every one of them would make a three-entry fixture depend
    on 262 KiB of firmware to test a join.
    """

    def machine(self, stored=None, walked=()):
        """A Machine whose store set is `stored` and whose walked set is `walked`.

        `walked` is separate because `spared` is walked-minus-stored, and a
        fixture that could only produce `spared` by storing-then-unstoring would
        not be testing the skip window the carve-out is.
        """
        machine = B.Machine(b"")
        machine.xdata = dict(stored or {})
        machine.writes = list((addr, value)
                              for addr, value in (stored or {}).items())
        machine.walked = set(walked)
        return machine

    def join(self, body, machine, **kwargs):
        """Write `body` to a temp registers.yaml and return the joined rows."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registers.yaml")
            with open(path, "w") as handle:
                handle.write(body)
            entries = R.load_registers(path)
            return R.build_rows_for_registers(entries, machine, **kwargs)

    def test_a_stored_zero_reads_cleared_with_its_value(self):
        rows = self.join(registers_yaml(("CHARGING", 0x0400, "present-untested")),
                         self.machine({0x0400: 0}))
        self.assertEqual([(r["addr"], r["boot_verdict"], r["boot_value"])
                          for r in rows],
                         [("0x0400", "cleared", "0x00")])

    def test_a_stored_nonzero_reads_written_not_cleared(self):
        # The distinction the whole table exists for: "the reset path zeroes
        # this" and "the reset path writes this" are different facts about a
        # byte, and a register reading `cleared` when the vector writes 0x3F to
        # it would be the overclaim this column is the check against.
        rows = self.join(registers_yaml(("WARM", 0x1001, "present-untested")),
                         self.machine({0x1001: 0x3F}))
        self.assertEqual([(r["boot_verdict"], r["boot_value"]) for r in rows],
                         [("written", "0x3f")])

    def test_a_walked_but_unstored_byte_reads_spared_with_no_value(self):
        # `boot_value` is `none` rather than `0x00`: the walk advanced past the
        # byte and stored nothing, which is not the same statement as a zero it
        # put there.
        rows = self.join(registers_yaml(("CARVE", 0x07FD, "present-untested")),
                         self.machine({0x07FC: 0}, walked={0x07FD, 0x07FE}))
        self.assertEqual([(r["boot_verdict"], r["boot_value"]) for r in rows],
                         [("spared", "none")])

    def test_an_address_outside_every_range_reads_not_reached_and_is_still_a_row(self):
        # The half that a fixture over the committed registers cannot reach: most
        # committed addresses fall inside a cleared range, so nothing there
        # would fail if `not-reached` rows were dropped instead of emitted.
        # Before this change the row would simply be missing, and a missing row
        # is indistinguishable from a register nobody surveyed.
        rows = self.join(registers_yaml(("FAR", 0x3202, "unknown-not-absent")),
                         self.machine({0x0400: 0}, walked={0x0400}))
        self.assertEqual([(r["addr"], r["boot_verdict"], r["boot_value"])
                          for r in rows],
                         [("0x3202", "not-reached", "none")])

    def test_every_address_gets_exactly_one_row_in_registers_yaml_order(self):
        rows = self.join(registers_yaml(("A", 0x0400, "present-untested"),
                                        ("B", 0x1663, "unknown-not-absent"),
                                        ("C", 0x07FD, "present-untested")),
                         self.machine({0x0400: 0, 0x07FC: 0},
                                      walked={0x07FC, 0x07FD}))
        self.assertEqual([r["addr"] for r in rows],
                         ["0x0400", "0x1663", "0x07FD"])

    def test_the_symbol_column_is_the_one_xdata_symbols_carries(self):
        # Delegation, held: this table's `symbol` is a C identifier the reader
        # can paste into a decompilation, and it has to be the same string
        # `ec/ghidra/xdata-symbols.csv` already carries or a driver author has
        # two names for one byte. Asserted against the generated file rather
        # than against this module's own naming.
        with open(HERE.parent / "ghidra" / "xdata-symbols.csv",
                  newline="") as handle:
            committed = {row["addr"]: row["name"]
                         for row in csv.DictReader(handle)}
        rows = self.join(registers_yaml(
            ("OEM_4 (CHARGING_PROFILE_MASK)", 0x07A6, "present-untested")),
            self.machine({0x07A6: 0}))
        self.assertEqual(rows[0]["symbol"], committed["0x07A6"])
        # ...and the two differ on purpose: the symbol is the C identifier a
        # decompilation carries, the entry is what `registers.yaml` says.
        self.assertEqual(rows[0]["from_register"],
                         "OEM_4 (CHARGING_PROFILE_MASK)")

    def test_the_from_register_column_is_the_entry_name_verbatim(self):
        # `gen_xdata_symbols` strips the trailing `(...)` and rewrites a
        # split name; `from_register` is what the entry said, so the two can be
        # reconciled when they disagree.
        rows = self.join(registers_yaml(
            ("AP_OEM (ENABLE_MANUAL_CTRL)", 0x0741, "present-untested")),
            self.machine({0x0741: 0}))
        self.assertEqual(rows[0]["from_register"], "AP_OEM (ENABLE_MANUAL_CTRL)")

    def test_render_round_trips_the_rows_it_is_given(self):
        # `--check` compares the rendered bytes, so a renderer that dropped or
        # reordered a column would still pass its own round trip and fail every
        # reader. This is the shape the committed table has.
        rows = self.join(registers_yaml(("A", 0x0400, "present-untested")),
                         self.machine({0x0400: 0}))
        import io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=R.CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        self.assertEqual(buf.getvalue().splitlines()[0],
                         ",".join(R.CSV_COLUMNS))
        self.assertEqual(R.render(rows), buf.getvalue())


class RefusalCases(unittest.TestCase):
    """The joins this tool declines, each with the reason it names.

    Every case below would produce a table that reads as complete with its
    guard removed, which is the only thing these guards are for.
    """

    def refuses(self, thunk, needle):
        with self.assertRaises(R.Refusal) as caught:
            thunk()
        self.assertIn(needle, str(caught.exception))

    def test_two_entries_naming_one_address_are_refused(self):
        joined = [(0x0043, "FIRST"), (0x0043, "SECOND")]
        self.refuses(lambda: R.check_joins(joined),
                     "named by more than one")

    def test_the_refusal_names_the_duplicated_addresses(self):
        # A refusal that only said "something is wrong" would leave the reader
        # to diff the register map themselves, which is the work the refusal is
        # there to save.
        joined = [(0x0043, "FIRST"), (0x0043, "SECOND")]
        self.refuses(lambda: R.check_joins(joined), "0x0043")

    def test_an_entry_with_no_address_is_refused(self):
        self.refuses(lambda: R.register_addresses([{"name": "no address"}]),
                     "no `addr:`")

    def test_an_address_outside_the_xdata_space_is_refused(self):
        self.refuses(lambda: R.register_addresses(
            [{"name": "far", "addr": 0x1FFFF}]), "outside the 16-bit")

    def test_a_file_that_is_not_the_register_map_is_refused(self):
        # A YAML parse error rather than a missing key: the same failure, and
        # it has to be a refusal too or the caller prints nothing at all.
        self.refuses(lambda: R.load_registers(str(HERE / "gen_xdata_symbols.py")),
                     "not readable as YAML")

    def test_a_file_with_no_registers_list_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "registers.yaml")
            with open(path, "w") as handle:
                handle.write("something_else: 1\n")
            self.refuses(lambda: R.load_registers(path), "no top-level")

    def test_a_missing_file_is_refused(self):
        self.refuses(lambda: R.load_registers("/nonexistent/registers.yaml"),
                     "cannot be read")


class CommittedTableCases(unittest.TestCase):
    """The committed table, read against the tree that produced it."""

    @classmethod
    def setUpClass(cls):
        with open(LIFETIME_CSV, newline="") as handle:
            cls.rows = list(csv.DictReader(handle))

    def test_every_row_carries_a_verdict_the_walk_defines(self):
        self.assertEqual(sorted({r["boot_verdict"] for r in self.rows}
                                - set(B.VERDICTS)), [])

    def test_the_carve_out_reads_spared_where_its_neighbours_read_cleared(self):
        # The finding the write-up's headline rests on, read off the table:
        # `0x07FD`-`0x07FF` are the three bytes the reset path steps over, and
        # `0x07FC` and `0x0800` on either side are stores like any other. If
        # this ever reads otherwise, the walk changed -- or the walk stopped
        # walking the skip window -- and both are worth a look.
        by_addr = {r["addr"]: r["boot_verdict"] for r in self.rows}
        for addr in ("0x07FD", "0x07FE", "0x07FF"):
            self.assertEqual(by_addr.get(addr), "spared", addr)
        # The nearest registers on either side of the window, which are what
        # makes the carve-out read as a window rather than as a page: every
        # other named byte in that neighbourhood is a store like any other.
        for addr in ("0x07F6", "0x0803"):
            self.assertEqual(by_addr.get(addr), "cleared", addr)

    def test_a_spared_or_not_reached_row_carries_no_value(self):
        # The spelling rule `boot_xdata_sites` states: `none` is a byte the walk
        # did not write at all. A `0x00` here would put a value in the table
        # that no instruction stored.
        for row in self.rows:
            if row["boot_verdict"] in ("spared", "not-reached"):
                self.assertEqual(row["boot_value"], "none", row["addr"])

    def test_a_cleared_row_carries_a_zero(self):
        for row in self.rows:
            if row["boot_verdict"] == "cleared":
                self.assertEqual(row["boot_value"], "0x00", row["addr"])

    def test_the_table_names_every_address_registers_yaml_names(self):
        # A relation between the two files, not a count of either: a register
        # added to `registers.yaml` must appear here, and one dropped from it
        # must not, or the table is answering a question about a smaller map.
        # Read out of the YAML rather than out of the tool's own flattening, so
        # a bug in that flattening shows up here as a disagreement rather than
        # as agreement.
        import yaml
        with open(R.REGISTERS) as handle:
            entries = yaml.safe_load(handle)["registers"]
        wanted = set()
        for entry in entries:
            addr = entry["addr"]
            wanted.update(addr if isinstance(addr, list) else [addr])
        self.assertEqual({r["addr"] for r in self.rows},
                         {f"0x{a:04X}" for a in wanted})

    def test_check_reproduces_the_committed_table_byte_for_byte(self):
        out = subprocess.run([sys.executable, str(TOOL), "--check"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("byte for byte", out.stdout)

    def test_the_report_names_the_verdicts_it_printed(self):
        out = subprocess.run([sys.executable, str(TOOL), "--report"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        for token in ("cleared", "spared", "not-reached"):
            self.assertIn(token, out.stdout)


class CommandLineCases(unittest.TestCase):
    """`main()`'s exit status, which is the only thing a caller can branch on."""

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args],
                              capture_output=True, text=True)

    def test_self_test_exits_zero(self):
        out = self.run_tool("--self-test")
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_report_and_check_are_exclusive(self):
        out = self.run_tool("--report", "--check")
        self.assertEqual(out.returncode, 2)
        self.assertIn("different questions", out.stderr)

    def test_a_missing_firmware_image_is_a_named_failure_not_a_traceback(self):
        out = self.run_tool("--firmware", "/nonexistent/image.bin", "--report")
        self.assertEqual(out.returncode, 1)
        self.assertIn("note:", out.stderr)
        self.assertNotIn("Traceback", out.stderr)


if __name__ == '__main__':
    unittest.main()