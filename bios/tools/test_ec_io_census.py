#!/usr/bin/env python3
"""Offline checks for `ec_io_census.py`: the resolvers, on hand-built
listings, and the committed table against the listings it was derived from.

Two halves, and the split is the point. The first asserts the resolvers where
every answer is known because the fixture was written to be known -- which is
the only way to pin the parts that are easy to get subtly wrong, because the
real listings have no second answer to check a reading against. The second
reads the committed `bios/ghidra/listings/` and asserts the facts
`docs/findings/bios-ec-io-census.md` cites, so a listing that changed shape
fails here rather than quietly changing what that file says.

The committed half asserts properties and named rows, never a row count. A
count is a value every landing edit has to touch, which is what CLAUDE.md's
"No totals of the repository's own text" is about; the claims here are "every
command byte in the tree reaches a row", "the pair the write-up names is
present" and "the pair the write-up says is absent is absent".

Both halves read committed text. Nothing here opens the ROM, runs Ghidra or
UEFIExtract, or reads a register, and no case is a claim about what this
machine's firmware does at run time.
"""
import collections
import csv
import io
import os
import re
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import ec_io_census  # noqa: E402  (the path insert above is what makes this work)

LISTINGS = os.path.join(REPO, "bios", "ghidra", "listings")
CSV_PATH = os.path.join(REPO, "bios", "annotations", "ec-io-writes.csv")


def fixture(name):
    """One hand-built listing from the tool's own fixture, by function name."""
    for module, addr, fname, body in ec_io_census.FIXTURE:
        if fname == name:
            return ec_io_census.parse_listing_text(
                os.path.join("fixture", fname),
                "; %s @ %s   %s   [named]\n%s" % (module, addr, fname, body))
    raise KeyError(name)


def run(*argv):
    """main()'s output and exit code, for the modes a case wants to read."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = ec_io_census.main(list(argv))
    return buf.getvalue(), code


_CENSUS = {}


def committed():
    """The committed listings' census, read once per process.

    A dict rather than a module-level tuple so a case that mutates the result
    cannot leak into the next one, and a dict rather than `functools.cache` so
    there is no import to explain.
    """
    if "rows" not in _CENSUS:
        _CENSUS["rows"] = ec_io_census.rows(
            ec_io_census.read_listings(LISTINGS))
    return _CENSUS["rows"]


def listing(module, addr, name, *insns):
    """A hand-built listing, in the shape the committed ones are printed in.

    Two things the exporter does and a hand-typed body easily does not: the
    byte column is padded to eleven slots with `-`, and the address is upper
    case. Both are matched rather than tolerated, so a fixture that spells
    either of them differently parses to fewer instructions than it looks
    like it has -- which is how this file's first drafts of these bodies lost
    a line each without failing loudly.
    """
    lines = ["; %s @ %s   %s   [named]" % (module, addr.upper(), name)]
    for at, raw, mn, ops in insns:
        cells = raw.split() + ["-"] * (11 - len(raw.split()))
        lines.append("%s %s       %-7s %s"
                     % (at.upper(), " ".join(cells), mn, ops))
    return ec_io_census.parse_listing_text(
        os.path.join("fixture", name), "\n".join(lines) + "\n")


# --------------------------------------------------------------------------
# Reading a listing
# --------------------------------------------------------------------------

class ParseTests(unittest.TestCase):
    """The header and instruction regexes, against the shape each is for."""

    def test_the_byte_column_padded_with_dashes(self):
        # Past the instruction's own length the listing pads with `-`, which
        # is why the mnemonic is found by matching the column rather than by
        # counting spaces -- a fixed-width split reads most `mov`s wrong.
        parsed = listing(
            "Mod", "00000000", "f",
            ("00000000", "48 89 5c 24 08", "mov", "qword ptr [RSP + 0x8], RBX"),
            ("00000005", "41 b0 07", "mov", "R8B, 0x7"),
            ("00000008", "c3", "ret", ""))
        self.assertEqual([i["mn"] for i in parsed.insns], ["mov", "mov", "ret"])
        self.assertEqual(parsed.insns[1]["ops"], "R8B, 0x7")
        self.assertEqual(parsed.module, "Mod")
        self.assertEqual(parsed.addr, "00000000")

    def test_an_unnamed_function_keeps_its_generated_name(self):
        parsed = listing(
            "Setup", "0001BA3C", "FUN_0001ba3c",
            ("0001BA3C", "48 89 5c 24 08", "mov", "qword ptr [RSP + 0x8], RBX"))
        self.assertEqual(parsed.name, "FUN_0001ba3c")

    def test_a_file_that_is_not_a_listing_reads_as_nothing(self):
        self.assertIsNone(ec_io_census.parse_listing_text(
            "x", "not a listing at all\n"))


# --------------------------------------------------------------------------
# Which register an operand names
# --------------------------------------------------------------------------

class RegisterTests(unittest.TestCase):
    """`reg_family`, on the widths and the byte aliases it has to fold."""

    def test_the_widths_of_one_register_are_one_register(self):
        for name in ("R8", "R8D", "R8W", "R8B", "r8b"):
            self.assertEqual(ec_io_census.reg_family(name), "R8", name)

    def test_a_byte_alias_belongs_to_its_full_register(self):
        self.assertEqual(ec_io_census.reg_family("DIL"), "RDI")
        self.assertEqual(ec_io_census.reg_family("BL"), "RBX")
        self.assertEqual(ec_io_census.reg_family("R15B"), "R15")

    def test_a_memory_operand_is_not_a_register(self):
        self.assertIsNone(ec_io_census.reg_family("byte ptr [RBP + 0x810]"))
        self.assertIsNone(ec_io_census.reg_family("[ESP + 0x8]"))


# --------------------------------------------------------------------------
# Reading a value byte
# --------------------------------------------------------------------------

class ValueTests(unittest.TestCase):
    """`trace` and `te_value`, on windows built to have a known answer."""

    def window_of(self, *insns):
        """The instruction list of a listing built from `(addr, bytes, mn, ops)`."""
        return listing("M", "00000000", "f", *insns).insns

    def test_an_immediate_is_read_where_it_is_set(self):
        insns = self.window_of(
            ("00000000", "41 b0 41", "mov", "R8B, 0x41"),
            ("00000003", "e8 00 00 00 00", "call", "0x000000f0"))
        self.assertEqual(ec_io_census.trace(insns, 0, 1, "R8B"),
                         ("imm", "0x41"))

    def test_the_port_byte_may_be_set_before_or_after_the_value_byte(self):
        # Both orders occur in the tree, so neither may be assumed.
        for pair in ((("00000000", "b2 a3", "mov", "DL, 0xa3"),
                      ("00000002", "41 b0 41", "mov", "R8B, 0x41")),
                     (("00000000", "41 b0 41", "mov", "R8B, 0x41"),
                      ("00000003", "b2 a3", "mov", "DL, 0xa3"))):
            insns = self.window_of(*(pair + (
                ("00000005", "e8 00 00 00 00", "call", "0x000000f0"),)))
            self.assertEqual(ec_io_census.trace(insns, 0, 2, "R8B"),
                             ("imm", "0x41"))

    def test_xor_with_itself_is_zero(self):
        insns = self.window_of(
            ("00000000", "45 33 c0", "xor", "R8D, R8D"),
            ("00000003", "b2 a5", "mov", "DL, 0xa5"),
            ("00000005", "e8 00 00 00 00", "call", "0x000000f0"))
        self.assertEqual(ec_io_census.trace(insns, 0, 2, "R8B"),
                         ("imm", "0x00"))

    def test_an_entry_alias_is_the_callers_byte(self):
        # `mov DIL, R8B` at the top of the function is what makes the later
        # `mov R8B, DIL` the caller's argument rather than an unreadable one.
        insns = self.window_of(
            ("00000000", "41 8a f8", "mov", "DIL, R8B"),
            ("00000003", "e8 00 00 00 00", "call", "0x000000f0"),
            ("00000008", "44 8a c7", "mov", "R8B, DIL"),
            ("0000000b", "e8 00 00 00 00", "call", "0x000000f0"))
        self.assertEqual(ec_io_census.trace(insns, 2, 3, "R8B"),
                         ("caller", "R8B"))

    def test_a_push_is_a_spill_and_does_not_count_as_a_write(self):
        # The register keeps the value it had, so an alias after `push RDI` is
        # still the only write to RDI in the entry block.
        insns = self.window_of(
            ("00000000", "57", "push", "RDI"),
            ("00000001", "41 8a f8", "mov", "DIL, R8B"),
            ("00000004", "e8 00 00 00 00", "call", "0x000000f0"),
            ("00000009", "44 8a c7", "mov", "R8B, DIL"),
            ("0000000c", "e8 00 00 00 00", "call", "0x000000f0"),
            ("00000011", "5f", "pop", "RDI"))
        self.assertEqual(ec_io_census.trace(insns, 3, 4, "R8B"),
                         ("caller", "R8B"))

    def test_two_writes_in_one_window_are_not_one_byte(self):
        # `Setup 0x1A5C` sets DL three ways and passes whichever it reached,
        # so the answer is the register, not the last literal before the call.
        insns = self.window_of(
            ("00000000", "b2 10", "mov", "DL, 0x10"),
            ("00000002", "b2 a0", "mov", "DL, 0xa0"),
            ("00000004", "44 8a ca", "mov", "R9B, DL"),
            ("00000007", "e8 00 00 00 00", "call", "0x000000f0"))
        # The chase ends on DL, not on R9B: DL is the register whose value is
        # the uncertain one, and naming it is what lets a reader go and look.
        self.assertEqual(ec_io_census.trace(insns, 0, 4, "R9B"),
                         ("unresolved", "DL"))

    def test_a_status_guard_between_two_calls_is_not_a_choice(self):
        # `test RAX, RAX` / `js` is in nearly every window in this tree and
        # writes nothing, so a rule keyed on branches would lose the byte.
        insns = self.window_of(
            ("00000000", "41 b0 41", "mov", "R8B, 0x41"),
            ("00000003", "e8 00 00 00 00", "call", "0x000000f0"),
            ("00000008", "48 85 c0", "test", "RAX, RAX"),
            ("0000000b", "78 7d", "js", "0x0000008a"),
            ("0000000d", "b2 a5", "mov", "DL, 0xa5"),
            ("0000000f", "e8 00 00 00 00", "call", "0x000000f0"))
        self.assertEqual(ec_io_census.trace(insns, 2, 5, "R8B"),
                         ("imm", "0x41"))

    def test_a_comparison_of_the_read_register_is_not_a_second_write(self):
        # `OemApControlDxe 0x438` guards the value it then passes:
        # `mov R9B, AL` at 0x4A8, `cmp R9B, 0xff` at 0x4C2, and the call at
        # 0x4D4. The `cmp` sets flags and leaves R9B alone, so the window has
        # one write and the answer is the chase from AL; counted as a second
        # write it disagrees with the first and the byte comes back unreadable.
        insns = self.window_of(
            ("0000049f", "a0 06 00 43 ff 00 00 00 00", "mov",
             "AL, [0xff430006]"),
            ("000004a8", "44 8a c8", "mov", "R9B, AL"),
            ("000004c2", "41 80 f9 ff", "cmp", "R9B, 0xff"),
            ("000004c6", "74 27", "jz", "0x000004ef"),
            ("000004d1", "41 b0 6c", "mov", "R8B, 0x6c"),
            ("000004d4", "e8 3b 05 00 00", "call", "0x00000a14"))
        # The chase ends on AL, which came out of memory one line up.
        self.assertEqual(ec_io_census.trace(insns, 1, 5, "R9B"),
                         ("unresolved", "AL"))

    def test_a_test_of_the_read_register_is_not_a_write_either(self):
        # The other flag-setting form, on the same family, for the same reason.
        insns = self.window_of(
            ("00000000", "e8 00 00 00 00", "call", "0x000000f0"),
            ("00000005", "41 b0 41", "mov", "R8B, 0x41"),
            ("00000008", "45 84 c0", "test", "R8B, R8B"),
            ("0000000b", "74 05", "jz", "0x0000001b"),
            ("0000000d", "e8 00 00 00 00", "call", "0x000000f0"))
        self.assertEqual(ec_io_census.trace(insns, 1, 4, "R8B"),
                         ("imm", "0x41"))

    def test_a_value_read_out_of_memory_is_the_register_that_is_unknown(self):
        insns = self.window_of(
            ("00000000", "a0 34 00 43 ff 00 00 00 00", "mov",
             "AL, [0xff430034]"),
            ("00000007", "8a d8", "mov", "BL, AL"),
            ("00000009", "44 8a c3", "mov", "R8B, BL"),
            ("0000000c", "e8 00 00 00 00", "call", "0x000000f0"))
        # The chase ends on AL, the register whose value came out of memory --
        # not on R8B, which only forwards it, and not on the operand itself.
        self.assertEqual(ec_io_census.trace(insns, 0, 3, "R8B"),
                         ("unresolved", "AL"))


# --------------------------------------------------------------------------
# The two ABIs
# --------------------------------------------------------------------------

class AbiTests(unittest.TestCase):
    """Which of the two forms a listing is read with."""

    def test_the_x64_modules_are_not_te(self):
        listing = ec_io_census.parse_listing_text(
            "x", "; OemOcDxe @ 00000F38   EcWriteCommandData   [named]\n")
        self.assertFalse(ec_io_census.is_te(listing))

    def test_the_two_te_modules_are_te(self):
        for module in ("OemOcPei", "OemHooksPei"):
            listing = ec_io_census.parse_listing_text(
                "x", "; %s @ 00000000   f   [named]\n" % module)
            self.assertTrue(ec_io_census.is_te(listing), module)

    def test_a_te_byte_is_read_off_the_stack_the_call_finds(self):
        listing = fixture("te_write")
        sites = dict((port, at) for at, port in ec_io_census.port_sites(listing))
        self.assertEqual(
            ec_io_census.te_value(listing, sites["0xa3"]), ("imm", "0x07"))
        self.assertEqual(
            ec_io_census.te_value(listing, sites["0xa2"]), ("imm", "0xa6"))

    def test_a_pop_pairing_a_push_leaves_the_byte_beneath_it(self):
        # `OemOcPei 0xFFF827F3` pushes 0x7, pushes 0x62 and pops that straight
        # back into EBX, so the command carries the one underneath.
        parsed = listing(
            "OemOcPei", "FFF827F3", "f",
            ("FFF827F3", "6a 07", "push", "0x7"),
            ("FFF827F5", "6a 62", "push", "0x62"),
            ("FFF827F7", "5b", "pop", "EBX"),
            ("FFF827F8", "b2 a3", "mov", "DL, 0xa3"),
            ("FFF827FA", "b1 62", "mov", "CL, 0x62"),
            ("FFF827FC", "e8 00 00 00 00", "call", "0xfff8277f"))
        site = ec_io_census.port_sites(parsed)[0][0]
        self.assertEqual(ec_io_census.te_value(parsed, site),
                         ("imm", "0x07"))


# --------------------------------------------------------------------------
# Grouping command bytes into an access
# --------------------------------------------------------------------------

class SequenceTests(unittest.TestCase):
    """`access_sequences`, on the two shapes the tree uses."""

    def test_a_read_is_base_index_then_0xa4(self):
        seq = ec_io_census.access_sequences(fixture("imm_write"))
        self.assertEqual(len(seq), 1)
        self.assertEqual(seq[0]["base"][1], "0xa3")
        self.assertEqual(seq[0]["index"][1], "0xa2")
        self.assertEqual(seq[0]["end"][1], "0xa5")

    def test_two_runs_in_one_function_are_two_rows(self):
        # `OemOcDxe 0x4F8` reads 0x0741 and then writes it, in one function.
        parsed = listing(
            "OemOcDxe", "000004F8", "two",
            ("000004F8", "41 b0 07", "mov", "R8B, 0x7"),
            ("000004FB", "b2 a3", "mov", "DL, 0xa3"),
            ("000004FD", "e8 00 00 00 00", "call", "0x00000f38"),
            ("00000502", "41 b0 41", "mov", "R8B, 0x41"),
            ("00000505", "b2 a2", "mov", "DL, 0xa2"),
            ("00000507", "e8 00 00 00 00", "call", "0x00000f38"),
            ("0000050c", "b2 a4", "mov", "DL, 0xa4"),
            ("0000050e", "e8 00 00 00 00", "call", "0x00000dd4"),
            ("00000513", "41 b0 07", "mov", "R8B, 0x7"),
            ("00000516", "b2 a3", "mov", "DL, 0xa3"),
            ("00000518", "e8 00 00 00 00", "call", "0x00000f38"),
            ("0000051d", "41 b0 41", "mov", "R8B, 0x41"),
            ("00000520", "b2 a2", "mov", "DL, 0xa2"),
            ("00000522", "e8 00 00 00 00", "call", "0x00000f38"),
            ("00000527", "41 b0 5a", "mov", "R8B, 0x5a"),
            ("0000052a", "b2 a5", "mov", "DL, 0xa5"),
            ("0000052c", "e8 00 00 00 00", "call", "0x00000f38"))
        seqs = ec_io_census.access_sequences(parsed)
        self.assertEqual(len(seqs), 2)
        self.assertEqual([s["end"][1] for s in seqs], ["0xa4", "0xa5"])

    def test_every_command_byte_reaches_exactly_one_run(self):
        # The property the write-up's "no silent drops" rests on: a shape this
        # tool does not understand has to show up as a row, not as a silence.
        listings = ec_io_census.read_listings(LISTINGS)
        for listing in listings:
            sites = ec_io_census.port_sites(listing)
            if not sites:
                continue
            claimed = sum(
                1 + (1 if s["index"] else 0) + (1 if s["end"] else 0)
                for s in ec_io_census.access_sequences(listing))
            self.assertEqual(claimed, len(sites),
                             "%s %s: %d command byte(s), %d claimed"
                             % (listing.module, listing.name, len(sites),
                                claimed))


# --------------------------------------------------------------------------
# A 0xA6 that is not an index byte
# --------------------------------------------------------------------------

class OperandTests(unittest.TestCase):
    """The false positive the census has to decline.

    `Setup 0xD400` carries the byte pair `a6 00` inside a displacement,
    `test word ptr [RBX + 0xa6], AX`. A scan for the byte finds it, and it is
    a memory offset rather than a command byte.
    """

    def test_a_memory_operand_carrying_0xa6_is_not_a_command_byte(self):
        parsed = listing(
            "Setup", "0000D400", "mem_operand",
            ("0000D400", "66 85 83 a6 00 00 00", "test",
             "word ptr [RBX + 0xa6], AX"),
            ("0000D407", "c3", "ret", ""))
        self.assertEqual(ec_io_census.port_sites(parsed), [])
        self.assertEqual(ec_io_census.access_sequences(parsed), [])

    def test_only_a_mov_to_dl_starts_a_run(self):
        # The command byte is a literal in DL, so `mov DL, 0xa2` and nothing
        # else is what a site looks like.
        parsed = listing(
            "M", "00000000", "f",
            ("00000000", "b2 a2", "mov", "DL, 0xa2"),
            ("00000002", "44 0f b6 c0", "movzx", "R8D, R8B"),
            ("00000006", "e8 00 00 00 00", "call", "0x000000f0"))
        self.assertEqual([p for _, p in ec_io_census.port_sites(parsed)],
                         ["0xa2"])


# --------------------------------------------------------------------------
# The committed table
# --------------------------------------------------------------------------

class CommittedTests(unittest.TestCase):
    """The census over the committed listings, and the CSV over both."""

    def test_the_committed_csv_is_what_the_tool_derives(self):
        out, code = run("--check")
        self.assertEqual(code, 0, out)

    def test_write_and_check_are_refused_together(self):
        # A run that both re-blessed the file and compared against it would
        # exit green on anything.
        with self.assertRaises(SystemExit):
            run("--write", "--check")

    def test_every_command_byte_in_the_tree_reaches_a_row(self):
        table = committed()
        claimed = collections.Counter()
        for row in table:
            claimed[(row["module"], row["func_addr"])] += 1
        for listing in ec_io_census.read_listings(LISTINGS):
            seqs = ec_io_census.access_sequences(listing)
            if not seqs:
                continue
            key = (listing.module, "0x" + listing.addr)
            self.assertGreaterEqual(claimed[key], len(seqs),
                                    "%s %s has a run with no row"
                                    % (listing.module, listing.name))

    def test_the_csv_carries_a_row_for_every_row_the_tool_builds(self):
        table = committed()
        with open(CSV_PATH, newline="") as f:
            on_disk = list(csv.DictReader(f))
        self.assertEqual([ec_io_census.clean(r) for r in table], on_disk)

    def test_the_pair_the_write_up_cites_is_present(self):
        # `Setup 0x7C50` `update_ec_82_from_setup_byte_7cd` rewrites EC RAM
        # 0x82 through 0x1BA3C, which selects 0x07 and is passed 0x82. If the
        # resolver stopped finding the caller, this row would go and the
        # write-up's worked example with it.
        rows = [r for r in committed()
                if r["module"] == "Setup" and r["index"] == "0x82"]
        self.assertTrue(rows, "the (0x07, 0x82) writes are gone")
        self.assertTrue(all(r["base"] == "0x07" for r in rows),
                        [r["base"] for r in rows])
        self.assertTrue([r for r in rows
                         if r["caller"] == "Setup@0x00007CFB"],
                        "the call from update_ec_82_from_setup_byte_7cd")

    def test_the_pair_the_write_up_says_is_absent_is_absent(self):
        # 0x07A6 is the address the corrected section 6 is about, and the
        # census's verdict. A future listing that reaches it would make that
        # negative wrong in the loudest way available, so it is held here.
        self.assertEqual([r for r in committed()
                          if r["base"] == "0x07" and r["index"] == "0xa6"], [])

    def test_the_base_is_not_always_0x07(self):
        # "indexed by 0xA6 means nothing without its base", and 0x04 is a base
        # the modules select. Held as "the two bases the write-up names are
        # both present" rather than as the whole set: a new module selecting a
        # third base is a change to the table, not a reason to fail here.
        bases = {r["base"] for r in committed() if r["base"]}
        self.assertLessEqual({"0x04", "0x07"}, bases)

    def test_a_base_the_modules_actually_select_is_among_them(self):
        # The modules §4 of the write-up names as carrying base 0x04, in
        # either the literal form or the argument form.
        four = {r["module"] for r in committed() if r["base"] == "0x04"}
        for module in ("OemSWBoardIDDxe", "Setup", "OemHooks",
                       "OemTurboModeDxe", "OemPowerModeDxe", "OemServiceDxe",
                       "OemGlobalNvsDxe"):
            self.assertIn(module, four)

    def test_a_read_and_a_write_are_told_apart(self):
        # 0xA4 terminates a read and 0xA5 a write; a table that lost the
        # distinction would answer "does the BIOS write 0x07A6" wrongly.
        directions = {r["direction"] for r in committed()}
        self.assertEqual(directions, {"read", "write"})
        self.assertTrue([r for r in committed()
                         if r["direction"] == "write" and r["data"]],
                        "no write in the tree carries a readable data byte")
        self.assertFalse([r for r in committed()
                          if r["direction"] == "read" and r["data"]],
                         "a read has no data byte")

    def test_an_unresolved_row_names_the_column_and_the_register(self):
        # The negative's boundary lives in this column, so a bare "unresolved"
        # would throw away the one thing a reader needs to follow it up.
        for row in committed():
            if row["resolved"] != "yes":
                self.assertTrue(row["resolved"].startswith("no:"), row)
                field, _, name = row["resolved"][3:].partition(":")
                self.assertIn(field, ("base", "index", "data"), row)
                self.assertTrue(name, row)
                self.assertEqual(row[field], "", row)

    def test_a_caller_supplied_byte_is_not_filled_in_from_a_register_name(self):
        # A row that put `R8` in the `index` column would read as though the
        # table had settled the address, which is exactly what it has not.
        for row in committed():
            for field in ("base", "index", "data"):
                self.assertNotIn(row[field], ("R8", "R8B", "DL", "R9B"),
                                 "%s in %s" % (row[field], field))

    def test_the_both_abis_are_covered(self):
        # A census handling only the x64 form leaves the PEI modules out, and
        # the hole is invisible in the output rather than in the count.
        abis = {r["abi"] for r in committed()}
        self.assertEqual(abis, {"x64", "te32"})
        self.assertTrue([r for r in committed() if r["abi"] == "te32"
                         and r["index"]],
                        "no TE access resolved an index")

    def test_every_row_is_cited_to_a_listing_that_exists(self):
        for row in committed():
            self.assertTrue(os.path.isfile(os.path.join(REPO, row["evidence"])),
                            row["evidence"])


# --------------------------------------------------------------------------
# The modes a reader runs
# --------------------------------------------------------------------------

class ModeTests(unittest.TestCase):
    """`--addr` and `--unresolved`, on the committed tree."""

    def test_addr_takes_the_address_or_the_pair(self):
        for spec in ("0x0741", "0741", "0x07:41", "7:41"):
            out, code = run("--addr", spec)
            self.assertEqual(code, 0, spec)
            self.assertIn("index=0x41", out, spec)

    def test_addr_refuses_a_shape_it_cannot_read(self):
        with self.assertRaises(SystemExit):
            run("--addr", "not-an-address")

    def test_addr_on_a_pair_the_tree_does_not_use_says_so(self):
        out, code = run("--addr", "0x07A6")
        self.assertEqual(code, 0)
        self.assertIn("0 access(es)", out)

    def test_unresolved_prints_only_what_could_not_be_read(self):
        out, code = run("--unresolved")
        self.assertEqual(code, 0)
        self.assertNotIn("yes\n", out.split("access(es)")[0])
        # A count of the tree's own rows, but read across two files: what the
        # tool prints against what the committed CSV holds.
        unread = sum(1 for r in committed() if r["resolved"] != "yes")
        self.assertTrue(unread)
        printed = re.search(r"(\d+) access\(es\); (\d+) with a byte", out)
        self.assertIsNotNone(printed, out)
        self.assertEqual((int(printed.group(1)), int(printed.group(2))),
                         (unread, unread))

    def test_the_module_filter_prints_that_module(self):
        out, code = run("--module", "OemOcPei")
        self.assertEqual(code, 0)
        self.assertIn("OemOcPei", out)
        self.assertNotIn("OemOcDxe ", out)

    def test_the_self_test_is_the_mode_the_gate_would_run(self):
        out, code = run("--self-test")
        self.assertEqual(code, 0, out)
        self.assertIn("self-test", out)


if __name__ == "__main__":
    unittest.main()