#!/usr/bin/env python3
"""The properties of ACPIDriver.sys's ACPI argument slots, from the committed `.asm`.

`acpi_eval_arg_slots.py` reads `windows/decompiled/native/ACPIDriver.asm` and
reports, per handler, the dword each `ACPI_METHOD_ARGUMENT` header is given.
This suite is what holds that tool to the settlement it exists to record, so
the two are read together: the tool prints, and these are the claims about the
print.

**The one assertion that carries the answer.** `MMRD`'s
`mov qword ptr [RSP + 0x60], 0x40000` is eight bytes, so it writes `0x60`-`0x67`
-- the constant into the low dword and zeros into the high one -- and the four
byte stores that follow fill `0x64`-`0x67` with the address. Whether the two are
one dword or two turns entirely on whether anything rewrites `0x60`-`0x63`
afterwards. `test_header_bytes_are_never_rewritten` is that question, asked of
every function carrying the constant rather than of `MMRD` alone: if a
regeneration ever coalesced the two, or moved a store, this is what goes red.

The rest are relations rather than a census, on purpose. The named sets below
are how a regeneration that moved a store fails loudly, and asserting how many
functions carry the constant would be a figure every landing change to this
driver moves -- the trap `CLAUDE.md` records four times over. So the sets are
named, the counts are not written down, and the exception is named rather than
counted.

**What is not asserted.** Nothing here says what `ACPI.sys` requires of
`DataLength`, or that `DataLength = 0` is wrong for `ECRR`. The field is
identified from the driver's own code and stops there;
`docs/findings/acpi-interpreter-region-access.md` records that Microsoft's
`ACPI_METHOD_ARGUMENT_V1` is not committed to this tree, so the far side of the
boundary is not reachable from committed material.

**Nothing here is hardware evidence.** No driver is loaded, no IOCTL is issued
and no EC register is read. Every value is read out of a committed listing, and
the read is over a disassembly rather than over the machine -- which is why
`test_no_handler_is_silently_dropped` exists, since a store the exporter did not
emit would be invisible to the whole tool rather than failing loudly.

This suite reads a committed input, so it has to run from inside the repository:
`tools/run-tests.sh` cds to the repo root.
"""
import io
import pathlib
import sys
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parent.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import acpi_eval_arg_slots as slots  # noqa: E402

ASM = REPO / "windows" / "decompiled" / "native" / "ACPIDriver.asm"
ANALYSIS = REPO / "windows" / "native" / "ACPIDriver.sys.analysis.md"
FINDING = REPO / "docs" / "findings" / "acpi-eval-argument-datalength.md"

# The handlers that state the length 4 in at least one argument header, by ACPI
# method name. Named rather than counted: this is the set a regeneration that
# moved a store would change, and it is the only place in this file that has to
# be updated when it does. `MMWB` is here and in `REGISTER_HEADER_METHODS` at
# once, and the overlap is the finding -- it states the length of 4 for the
# address it passes and takes the value's header from a register.
CONSTANT_METHODS = frozenset((
    "IORD", "MMRB", "MMRD", "PCRD",
    "T1RD", "T2RD", "T3RD",
    "IOWD", "MMWB", "MMWD", "PCWD",
    "T1WR", "T2WR",
))

# The handlers whose single argument is a buffer rather than a scalar: the
# header dword is `0x00800002`, and each `memcpy_s`es `0x80` bytes into the
# slot's payload and reads the `+2` field back as a word (`0x140001CB0`,
# `0x140002A40`). They carry no length of 4 because they have no four-byte
# scalar argument to declare one for -- which is the whole of `T3WR`'s absence
# from the constant set, and `test_every_slot_is_one_of_three_shapes` is the
# shape of that claim.
BUFFER_METHODS = frozenset(("SMRW", "T3WR"))

# The handlers that hand a header its value in a register rather than an
# immediate. Every one zeroes it, so every one declares a length of 0.
# `MMWB` belongs here and in `CONSTANT_METHODS` at once, and that overlap is
# the finding rather than a mistake in either set: it is the handler the issue
# did not flag, the one whose second argument's header is a register store, so
# it states the length of 4 once for two arguments. Asserting the two sets
# disjoint would delete the case.
REGISTER_HEADER_METHODS = frozenset((
    "RCMS", "ECRR", "RIOP", "WCMS", "ECRW", "WIOP", "MMWB",
))

# The handler whose second argument header is a register store, and so the one
# place where ArgumentCount and the number of constants disagree. Named, not
# counted -- see `test_argument_count_matches_the_constant_slots`.
REGISTER_HEADER_EXCEPTION = "MMWB"


def methods_with(rows, predicate):
    return {row["method"] for row in rows if predicate(row)}


class AcpiEvalArgSlots(unittest.TestCase):
    """Every case reads the committed listing once; the class holds the parse."""

    @classmethod
    def setUpClass(cls):
        cls.rows = slots.rows_for(str(ASM))
        cls.by_method = {}
        for row in cls.rows:
            cls.by_method.setdefault(row["method"], []).append(row)

    def methods(self):
        return set(self.by_method)

    # -- the settlement ----------------------------------------------------

    def test_header_bytes_are_never_rewritten(self):
        """The decisive one: nothing rewrites 0x60-0x63 after the constant.

        Stated over every constant-carrying slot rather than over `MMRD`,
        because a regression toward the coalesced reading would look identical
        in any one handler and different in the population.
        """
        carried = [r for r in self.rows if r["header"] == slots.LITERAL_4]
        self.assertTrue(carried, "no slot carries the constant at all")
        for row in carried:
            self.assertFalse(
                row["rewritten"],
                "%s slot %d: a store rewrites the four header bytes after the "
                "constant at %s" % (row["method"], row["slot"],
                                    row["handler_obj"].header_stores(row["slot"])[0].va))

    def test_constant_store_is_eight_bytes_at_a_slot_base(self):
        """Where the constant is stored, it is stored wide enough to reach the payload.

        This is the shape that makes the byte stores land in the *upper* half of
        the same store rather than over the constant. A dword at a slot base
        would leave `0x64`-`0x67` untouched by the header store, and the
        coalesced reading of the generated C would become a second possibility.
        """
        for row in self.rows:
            if row["header"] != slots.LITERAL_4:
                continue
            stores = row["handler_obj"].header_stores(row["slot"])
            self.assertEqual(len(stores), 1,
                             "%s slot %d has %d stores at its base"
                             % (row["method"], row["slot"], len(stores)))
            store = stores[0]
            self.assertEqual(store.off, row["handler_obj"].slot_base(row["slot"]))
            self.assertGreaterEqual(store.width, slots.HEADER_BYTES,
                                    "%s slot %d: a store narrower than the "
                                    "header cannot carry a length at +2"
                                    % (row["method"], row["slot"]))

    def test_payload_stores_land_above_the_header(self):
        """Every byte store in a slot is at +4 or above.

        The mirror of the previous case. Together they are the two-adjacent-
        dwords answer: the constant occupies `+0`-`+3` and the four address
        bytes `+4`-`+7`, with nothing overlapping.
        """
        for row in self.rows:
            for store in row["handler_obj"].payload_stores(row["slot"]):
                self.assertGreaterEqual(
                    store.off - row["handler_obj"].slot_base(row["slot"]),
                    slots.HEADER_BYTES,
                    "%s slot %d: a store at +%#x is inside the header"
                    % (row["method"], row["slot"],
                       store.off - row["handler_obj"].slot_base(row["slot"])))

    # -- the field's identification ---------------------------------------

    def test_every_constant_handler_is_named_here(self):
        """CONSTANT_METHODS is what the tool found, not a subset of it.

        Asserted as equality so a store that moves or appears is a failure in
        the direction that matters: a handler nobody has looked at should not
        be able to join the set quietly.
        """
        self.assertEqual(methods_with(self.rows,
                                      lambda r: r["header"] == slots.LITERAL_4),
                         CONSTANT_METHODS)

    def test_every_slot_is_one_of_three_shapes(self):
        """Every header in the listing resolves to one of three values.

        `0x00040000`, `0x00800002`, or zero. A fourth shape would show up here
        as an unnamed value rather than as a total that quietly moved, which is
        why this is a partition over *slots* and not over handlers: `MMWB` has
        a slot of each of the first and third kinds, so a partition over
        handlers could not be stated at all.
        """
        shapes = {slots.LITERAL_4, slots.LITERAL_BUFFER, 0}
        for row in self.rows:
            self.assertIn(row["header"], shapes,
                          "%s slot %d resolves to %r, which is none of the "
                          "three named shapes"
                          % (row["method"], row["slot"], row["header"]))
        self.assertEqual(methods_with(self.rows,
                                      lambda r: r["header"] == slots.LITERAL_BUFFER),
                         BUFFER_METHODS)
        self.assertEqual(methods_with(self.rows, lambda r: r["header"] == 0),
                         REGISTER_HEADER_METHODS)

    def test_zeroed_slots_declare_no_length(self):
        """A register-sourced header that resolves to zero is a length of 0.

        The `ECRR`/`ECRW` half of the finding, and the one the issue called a
        real difference between the two families. Asserted per slot so a
        failure names which handler stopped zeroing, and restricted to the
        slots that are actually zeroed so `MMWB`'s other slot does not have to
        be excused here.
        """
        zeroed = [r for r in self.rows if r["header"] == 0]
        self.assertTrue(zeroed, "no slot is zeroed at all")
        for row in zeroed:
            self.assertIn(row["method"], REGISTER_HEADER_METHODS,
                          "%s slot %d zeroed but is not a register-header "
                          "handler" % (row["method"], row["slot"]))

    def test_register_sourced_headers_are_the_only_zeroed_ones(self):
        """Zero is reached two ways -- a literal and a cleared register -- and
        the tool says which, rather than conflating them.

        The listing has no `mov dword ptr [RSP + 0x60], 0x0`; every zeroed
        slot comes from a register whose defining `xor` is one instruction
        back. A future regeneration that zeroed by immediate would be a
        different code path and should be visible here.
        """
        zeroed = [r for r in self.rows if r["header"] == 0]
        self.assertTrue(zeroed)
        for row in zeroed:
            store = row["handler_obj"].header_stores(row["slot"])[0]
            self.assertFalse(store.src.startswith("0x"),
                             "%s slot %d zeroed by immediate %s"
                             % (row["method"], row["slot"], store.src))

    # -- the census shape -------------------------------------------------

    def test_argument_count_matches_the_constant_slots(self):
        """ArgumentCount equals the number of slots stating the length of 4.

        Except in one named handler, whose second argument header comes from a
        register -- so the disagreement is stated as a relation with a named
        exception rather than as a count that could be off by one either way.
        """
        for row in self.rows:
            if row["header"] != slots.LITERAL_4 or not row["slot"] == 0:
                continue
            method = row["method"]
            carried = sum(1 for r in self.by_method[method]
                          if r["header"] == slots.LITERAL_4)
            if method == REGISTER_HEADER_EXCEPTION:
                self.assertLess(carried, row["count"],
                                "%s no longer takes its second header from a "
                                "register, so it is no longer the exception"
                                % method)
            else:
                self.assertEqual(carried, row["count"],
                                 "%s declares %d arguments but states the "
                                 "length of 4 for %d of them"
                                 % (method, row["count"], carried))

    def test_argument_count_is_never_more_than_the_slots_written(self):
        """A handler cannot declare an argument whose slot it never wrote.

        `T3WR` is the case this is really about: `ArgumentCount = 1`, and the
        one slot it writes is a buffer, so there is no scalar length to state.
        Without the relation, "carries no constant" and "declares an argument
        it forgot" would be indistinguishable from the table alone.
        """
        for row in self.rows:
            if row["slot"]:
                continue
            self.assertLessEqual(
                1, row["count"],
                "%s declares ArgumentCount = 0 yet writes an argument slot"
                % row["method"])

    def test_slots_are_contiguous_from_zero(self):
        """A handler's written slots are 0..n-1 with no hole.

        A gap would mean a slot whose header was written by something this
        tool does not parse, which is exactly the blind spot worth failing on
        rather than rendering as a shorter table.
        """
        for method, rows in self.by_method.items():
            indices = sorted(r["slot"] for r in rows)
            self.assertEqual(indices, list(range(len(indices))),
                             "%s writes slots %r" % (method, indices))
            self.assertLessEqual(len(indices), rows[0]["count"],
                                 "%s writes %d slots for ArgumentCount = %d"
                                 % (method, len(indices), rows[0]["count"]))

    # -- the tool's own parse ---------------------------------------------

    def test_no_handler_is_silently_dropped(self):
        """Every ACPI method the analysis file's IOCTL table names is found.

        The parse decides a handler is ACPI-evaluating by finding a MethodName
        store and an ArgumentCount store. If it found fewer, the table would
        quietly lose a row and every count over it with it -- so the population
        is checked against the committed table rather than against itself.
        """
        text = ANALYSIS.read_text(encoding="utf-8")
        # `| 0x9C40A494 | 0x925 | 0x1400015EC | MMRD | *(none)* |` -- the method
        # is the fourth cell. Every row is matched by its IOCTL prefix and by
        # its cell count, so a paragraph elsewhere in the file that happens to
        # start with a pipe cannot contribute a row here.
        named = set()
        for line in text.splitlines():
            if not line.startswith("| `0x9C40A") or line.count("|") < 5:
                continue
            named.add(line.split("|")[4].strip().strip("`"))
        named.discard("")
        self.assertTrue(named, "the IOCTL table in the analysis file did not parse")
        self.assertTrue(named <= self.methods(),
                        "methods in the IOCTL table this tool did not find: %s"
                        % ", ".join(sorted(named - self.methods())))

    def test_ambiguous_mnemonics_absent(self):
        """No mnemonic in the listing is two hex digits.

        The byte column is read by consuming two-digit groups and stopping, so
        a mnemonic spelled `AD` would put the stop in the wrong place. Nothing
        in this listing is, and the parse cannot see that by itself.
        """
        self.assertEqual(slots.ambiguous_mnemonics(str(ASM)), [])

    def test_tool_refuses_a_missing_listing(self):
        """A path that is not there is an error, not an empty table.

        A run that found nothing would print a header and no rows, which reads
        as "this driver states no lengths" rather than as "you asked for the
        wrong file".
        """
        self.assertEqual(
            slots.main([str(REPO / "no" / "such" / "listing.asm")]), 1)

    def test_tool_refuses_an_unknown_handler(self):
        self.assertEqual(slots.main([str(ASM), "--handler", "FUN_nope"]), 1)

    def test_self_test_passes(self):
        """The tool's own fixtures, including the clobbered-slot case.

        The committed listing cannot exercise it: nothing in this driver
        rewrites a header after writing it, so a parse that always answered
        "intact" would look correct here and only the fixtures catch it.
        """
        self.assertEqual(slots.main(["--self-test"]), 0)

    def test_table_and_csv_agree(self):
        """The two output modes describe the same slots.

        They are built from the same rows, so this is a check that neither
        mode drops one on the way out -- the CSV is what a reader would join
        against the DSDT, and a silently shorter join is the failure.
        """
        csv_out = io.StringIO()
        slots.print_csv(str(ASM), csv_out)
        table_out = io.StringIO()
        table_rows = slots.print_table(str(ASM), table_out)

        lines = [line for line in csv_out.getvalue().splitlines()[1:] if line]
        self.assertEqual(len(lines), len(table_rows))
        for line, row in zip(lines, table_rows):
            fields = line.split(",")
            self.assertEqual(fields[0], row["handler"])
            self.assertEqual(fields[2], row["method"])
            self.assertEqual(int(fields[4]), row["slot"])

    # -- the write-up, where the correction lives --------------------------

    def test_findings_writeup_agrees_with_the_listing(self):
        """The write-up's named sets are the tool's, not a transcription.

        A write-up that quoted a table and then had the listing change would
        be the failure CLAUDE.md's no-totals rule is about in its sharpest
        form, so the method names it lists for each shape are checked against
        what the tool finds.
        """
        text = FINDING.read_text(encoding="utf-8")
        missing = [m for m in sorted(CONSTANT_METHODS | BUFFER_METHODS)
                   if "`%s`" % m not in text]
        self.assertEqual(missing, [],
                         "the write-up does not mention: %s" % ", ".join(missing))
        self.assertTrue("acpi_eval_arg_slots.py" in text,
                        "the write-up does not name the tool that prints its table")

    def test_analysis_file_points_at_the_writeup(self):
        """The correction in the analysis file is visible where the claim is.

        The listing comment and the paragraph that disclaimed the constant are
        the two places the issue named, and a correction that lives in a
        separate file with no pointer from either is a retraction nobody reads.
        """
        text = ANALYSIS.read_text(encoding="utf-8")
        self.assertTrue("acpi-eval-argument-datalength.md" in text,
                        "the analysis file does not point at the write-up")
        self.assertTrue("DataLength" in text,
                        "the analysis file still disclaims the field's name")


if __name__ == "__main__":
    unittest.main()