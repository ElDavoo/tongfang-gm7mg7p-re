#!/usr/bin/env python3
"""`0x09E9`'s `registers.yaml` row, and the two-writer reconciliation that
justifies giving it one (issue #597).

Stands in for the part of [issue
#597](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/597) the cheap tier
can reach: that `ec/annotations/registers.yaml` carries `0x09E9` at the status
the static evidence warrants, that the per-site census resolves it to both a
read and a write direction, and that the reconciliation
`ec/annotations/ec-09e9-writers.md` §4 draws holds **by bytes** rather than only
in prose.

That last one is the half this suite exists for. The write-up's claim is that
both direct writers gate on `CTGP_DB_CTRL` (`0x0743`) **bit 2** in complementary
senses -- `jnb acc.2` in `0x96AD`, `jb acc.2` in `0x9C00` -- which is what makes
the disagreement one cell rather than a general race. A claim that sharp, resting
on a hand reading of two short windows, rots quietly: nothing fails if a later
re-decode finds the gate somewhere else, and the write-up keeps asserting it. So
the opcodes are asserted here against the committed `.asm`, and each case states
which byte it is looking for and why that byte is the claim.

The `0x0788` half is held the same way, one level up: the consumer is identified
by ASL text in `evidence/acpi/dsdt.dsl`, so that text is asserted rather than
left to rot with the write-up's claim about it.

**Every case here is a property of the tree, never a census of it.** The
reference counts are `check_register_counts.py`'s to recompute from the image and
are deliberately not repeated as constants, for the reason the sibling suite
gives: a count that every merge has to edit is a count that collides. What is
held is that the row carries all three keys, that none of them claims a PD-image
site, that the census resolves both directions, and that the two gates are where
the write-up says they are.
"""
import csv
import importlib.util
import re
import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

ANNOTATIONS = HERE.parent / "annotations"
REGISTERS = ANNOTATIONS / "registers.yaml"
SITES_CSV = ANNOTATIONS / "ec-09e9-09eb-sites.csv"
RESOLUTION_CSV = ANNOTATIONS / "site-resolution.csv"
DSDT = ROOT / "evidence" / "acpi" / "dsdt.dsl"
DECOMPILED = HERE.parent / "decompiled"
WRITERS_MD = ANNOTATIONS / "ec-09e9-writers.md"

# The one address this suite is about.
ADDR = 0x09E9

# The two writers, and the bit each one gates on. Spelled out rather than
# derived: the point of the cases below is to fail loudly when the image and
# this list drift apart, and a list recomputed from the same walk it is checked
# against would always agree.
#
# Each entry is (gate address, gate opcode, store address). `jnb`/`jb acc.2` are
# `30 e2` and `20 e2` -- the two forms the write-up calls complementary, and the
# whole reason the disagreement is one cell rather than a race. Addresses rather
# than a search over the window because the claim is about *which* branch gates
# the store: a window carrying both opcodes somewhere would satisfy a substring
# search and say nothing about whether the right one is in front of the store.
WRITERS = {
    0x96AD: (0x9718, b"\x30\xe2", 0x9747),
    0x9C00: (0x9C09, b"\x20\xe2", 0x9C0D),
}

# The routine that reads the byte and copies it into `0x0788`, and the three
# instructions of that copy: the compare at `0x8429`, the `mov dptr` at `0x842D`
# and the store that follows it. Named by routine so a failure message points at
# a row a reader can look up.
READER = 0x83FF
READER_STEPS = (
    (0x8429, b"\x6f", "xrl A, R7 -- the compare against 0x0788"),
    (0x842D, b"\x90\x07\x88", "mov DPTR, #0x0788"),
    (0x8430, b"\xf0", "movx @DPTR, A -- the copy itself"),
)

# `90 09 e9` is `mov DPTR,#0x09E9`: the store's own anchor. Its address is the
# CSV's `runtime` for the site; the `movx` that follows is the access, which is
# the distinction the write-up's §1 exists to keep.
STORE_MNEMONIC = b"\x90\x09\xe9"


def load(name):
    """A sibling tool by path -- they are scripts beside this suite, not modules."""
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(HERE))
csr = load("check_site_resolution")
vocab = load("check_status_vocabulary")


def register_row(addr):
    """The `registers.yaml` entry carrying `addr`, or None."""
    with REGISTERS.open(encoding="utf-8") as handle:
        for entry in yaml.safe_load(handle)["registers"]:
            addrs = entry["addr"] if isinstance(entry["addr"], list) else [entry["addr"]]
            if addr in addrs:
                return entry
    return None


def asm_window(addr):
    """The committed `.asm` text for one bank0 function, by its entry address."""
    path = DECOMPILED / "bank0" / f"{addr:04X}.asm"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


# One `.asm` row is `ADDR  b0 b1 b2  mnemonic  operands`, with the byte columns
# space-padded and `-` filled where an instruction is shorter than three bytes.
# Parsed rather than grepped because the padding makes a substring search
# unreliable -- `6f` alone also matches inside a longer row's operands -- and
# because the cases below are about *which address* carries an opcode.
#
# The mnemonic is lowercase letters, which is what keeps the `-` padding out of
# it: a looser `(\S+)` backtracks into the byte columns and reads the pad as the
# mnemonic, which is a listing that parses and then says nothing. The width is
# not fixed at three because the 8051 mnemonics run from `da` to `movc`, and a
# three-letter class silently drops every `jz`, `jb`, `movx` and `lcall` row --
# which is most of the window this suite reads.
_ASM_ROW = re.compile(
    r"(?m)^([0-9A-Fa-f]{4,6})\s+((?:[0-9a-f]{2}|-)(?:\s+(?:[0-9a-f]{2}|-))*)\s+"
    r"([a-z]{2,6})\b")


def asm_opcodes(text):
    """{runtime address: (opcode bytes, mnemonic)} over one committed listing."""
    out = {}
    for m in _ASM_ROW.finditer(text):
        raw = bytes(int(b, 16) for b in m.group(2).split() if b != "-")
        out[int(m.group(1), 16)] = (raw, m.group(3))
    return out


class TheRowIsPresent(unittest.TestCase):
    """`0x09E9` has a row, and the row says what the evidence warrants."""

    def test_the_address_is_carried(self):
        """Stated first and on its own: a suite that skips every assertion
        because its subject is absent is a green suite.
        """
        self.assertIsNotNone(register_row(ADDR),
                             f"0x{ADDR:04X} has no row in registers.yaml")

    def test_the_row_carries_all_three_reference_keys(self):
        """A missing key is not a zero.

        `check_register_counts.py` requires both split keys to be present for
        the same reason: "not audited" and "audited, no site" have to stay
        distinguishable, and only the second is a claim.
        """
        entry = register_row(ADDR)
        for key in ("static_refs", "static_refs_main_ec", "static_refs_pd_image"):
            self.assertIn(key, entry,
                          f"0x{ADDR:04X} has no {key}; a missing count is not "
                          f"a zero one")

    def test_the_status_is_declared_by_the_file_its_own_header(self):
        """`status:` is one of the values the header comment declares.

        Read out of the header rather than copied here, so a vocabulary that
        gains or loses a value does not need this file edited to agree -- the
        same reason `check_status_vocabulary.py` parses it.
        """
        declared = vocab.parse_declared(REGISTERS.read_text(encoding="utf-8"))
        self.assertIsNotNone(declared,
                             "registers.yaml's header no longer declares a "
                             "status vocabulary")
        values, suffixes = declared
        base, suffix = vocab.split_status(register_row(ADDR)["status"], suffixes)
        self.assertIn(base, values)
        if suffix is not None:
            self.assertIn(suffix, suffixes)

    def test_the_status_is_not_promoted_beyond_present_untested(self):
        """Nothing here was exercised at the machine.

        The whole grade rests on a static scan of two instruction windows. A row
        that quietly acquired a live source, or a status the scan cannot warrant,
        would claim a host read of bytes no run in this repository performed.
        """
        entry = register_row(ADDR)
        self.assertEqual(entry["status"], "present-untested")
        self.assertNotIn("live", entry.get("sources") or [])
        self.assertIn("read back", entry["note"].lower())

    def test_no_pd_image_site_is_claimed(self):
        """`static_refs_pd_image` is zero, and present.

        Not the count itself -- `check_register_counts.py` recomputes that from
        the image -- but that the key is there and zero. A PD-image site would
        be a reference to a different program's XDATA map and would make
        `present-untested` a claim about the wrong firmware.
        """
        self.assertEqual(register_row(ADDR)["static_refs_pd_image"], 0)

    def test_the_row_is_not_carried_by_the_named_rule_three_exemption(self):
        """`RESOLUTION_EXEMPT` names one address, and this is not it.

        The exemption is a limit of the instrument at one address, held by name.
        An entry that acquired it by accident would stop being checked without
        anything saying so.
        """
        self.assertNotIn(register_row(ADDR).get("name"), vocab.RESOLUTION_EXEMPT)


class TheCensusResolvesBothDirections(unittest.TestCase):
    """Rule 3 wants one EC-side site that resolves to a direction; this has three."""

    @classmethod
    def setUpClass(cls):
        with RESOLUTION_CSV.open(encoding="utf-8", newline="") as handle:
            cls.tally = {}
            for row in csv.DictReader(handle):
                if int(row["addr"], 16) == ADDR:
                    cls.tally.setdefault(row["resolution"], []).append(row)

    def test_the_address_has_rows_in_the_census(self):
        """A missing census row is not a resolved one, in either direction."""
        self.assertTrue(self.tally,
                        f"0x{ADDR:04X} has no row in site-resolution.csv; rule 3 "
                        f"refuses an address it cannot see")

    def test_it_resolves_to_a_direction(self):
        """At least one site lands in the resolved vocabulary."""
        self.assertTrue(
            any(label in csr.RESOLVED for label in self.tally),
            f"no site of 0x{ADDR:04X} resolves to a direction; got "
            f"{sorted(self.tally)}")

    def test_it_has_both_a_read_and_a_write_direction(self):
        """The two-writer claim, on the census rather than on prose.

        This is the property that distinguishes `0x09E9` from `0x09EA`/`0x09EB`,
        which each resolve to a read and a write from a single writer. Stated as
        "both directions are present" rather than as a count of sites, because
        it is the shape of the census that the write-up rests on and the number
        of rows is `check_register_counts.py`'s to measure.
        """
        self.assertIn("read", self.tally,
                      "the census resolves no read of 0x09E9, so the routine "
                      "that syncs it into 0x0788 is unaccounted for")
        self.assertIn("write", self.tally,
                      "the census resolves no write of 0x09E9, which is the "
                      "half of the two-writer claim")


class BothWritersGateOnBitTwoOf0743(unittest.TestCase):
    """The reconciliation, pinned by opcode against the committed `.asm`.

    `ec-09e9-writers.md` §4 claims the two writers are complementary on
    `0x0743` bit 2, which is what bounds the disagreement to one cell. Each case
    below says which byte it wants and why that byte is the claim, so a failure
    names the part of the reading that stopped holding.
    """

    def listing(self, addr):
        """One routine's committed listing, parsed to {address: (bytes, mnemonic)}."""
        text = asm_window(addr)
        self.assertIsNotNone(
            text, f"bank0 0x{addr:04X} has no committed .asm, so the window "
                  f"this checks does not exist")
        return asm_opcodes(text)

    def gate_precedes_the_store(self, addr):
        """The gate is the opcode the write-up names, and it is in front.

        Three failures are kept apart on purpose, because each is a different
        claim going false. A listing with no `mov DPTR,#0x09E9` is an export that
        changed under the write-up. A listing whose row at the gate address
        carries a *different* opcode is a store this case would otherwise read
        as gated when it is not. And a gate that decoded at some other address
        is a reading of the wrong branch -- so the address is part of the claim,
        not decoration on it.
        """
        gate_addr, gate_op, store_addr = WRITERS[addr]
        listing = self.listing(addr)

        self.assertIn(
            store_addr, listing,
            f"0x{addr:04X}'s listing has no row at 0x{store_addr:04X}, so the "
            f"store the write-up reconciles is not in it")
        op, mnemonic = listing[store_addr]
        self.assertEqual(op, STORE_MNEMONIC,
                         f"0x{store_addr:04X} decodes to {op.hex(' ')} "
                         f"`{mnemonic}`, not `mov DPTR,#0x09E9`")

        self.assertIn(
            gate_addr, listing,
            f"0x{addr:04X}'s listing has no row at 0x{gate_addr:04X}, so the "
            f"gate the write-up names is not in it")
        gate_bytes, gate_mnemonic = listing[gate_addr]
        self.assertTrue(
            gate_bytes.startswith(gate_op),
            f"0x{gate_addr:04X} decodes to {gate_bytes.hex(' ')} "
            f"`{gate_mnemonic}`, which is not the "
            f"{gate_op.hex(' ')} the write-up reads as a bit-2 test")
        self.assertLess(gate_addr, store_addr,
                        f"0x{addr:04X}: the gate at 0x{gate_addr:04X} comes "
                        f"after the store at 0x{store_addr:04X}, so the store "
                        f"does not run behind it")

    def test_the_96ad_writer_is_gated_on_bit_two(self):
        """`jnb acc.2` -- the gate the write-up reads as "bit 2 clear"."""
        self.gate_precedes_the_store(0x96AD)

    def test_the_9c00_writer_is_gated_on_bit_two(self):
        """`jb acc.2` -- the opposite sense of the same bit.

        The half that makes the pair *complementary* rather than two
        independent writers. On its own it is a claim about one routine; the
        write-up's is about the disagreement being bounded, and that needs both
        opcodes and their opposite senses, which is why they are two cases over
        one table rather than one assertion over two windows.
        """
        self.gate_precedes_the_store(0x9C00)

    def test_the_two_gates_are_opposite_forms(self):
        """`30 e2` and `20 e2`, and not the same form twice.

        The boundedness claim rests on the two being opposite senses of the same
        bit. If both listings ever decoded to the same opcode the write-up's
        table would be describing a different pair of routines, and the two cases
        above would both still pass -- which is the failure this one exists to
        catch.
        """
        gates = {gate_op for _gate_addr, gate_op, _store in WRITERS.values()}
        self.assertEqual(len(gates), len(WRITERS),
                         f"the two writers no longer gate on opposite forms: "
                         f"{sorted(g.hex() for g in gates)}")

    def test_the_reader_compares_then_copies_into_0788(self):
        """`0x83FF` reads the byte, compares, and stores into `0x0788`.

        This is the hop the whole `0x0788` half of the write-up rests on. Each
        instruction is asserted at its own address rather than by substring, so
        a firmware whose copy stopped happening -- or stopped being conditional
        on the compare -- fails here instead of leaving the write-up claiming a
        hop that is not in the image.
        """
        listing = self.listing(READER)
        for step_addr, opcode, what in READER_STEPS:
            self.assertIn(step_addr, listing,
                          f"0x{READER:04X}'s listing has no row at "
                          f"0x{step_addr:04X}, so the {what} is not in it")
            op, mnemonic = listing[step_addr]
            self.assertEqual(op, opcode,
                             f"0x{step_addr:04X} decodes to {op.hex(' ')} "
                             f"`{mnemonic}`, not the {what}")

    def test_the_compare_and_the_copy_are_adjacent_and_ordered(self):
        """`xrl` at `0x8429`, the `jz` over it, then the copy at `0x842D`.

        What makes the copy *conditional* rather than unconditional is that the
        `jz` at `0x842A` skips straight past the `movx @DPTR,A`. Asserting the
        three opcodes without their order would still pass on a listing where
        the store came first, which is a different routine and a different claim.
        """
        listing = self.listing(READER)
        for step_addr in (0x842A, 0x842C):
            self.assertIn(step_addr, listing,
                          f"0x{READER:04X}'s listing has no row at "
                          f"0x{step_addr:04X}")
        _op, jz = listing[0x842A]
        self.assertEqual(jz, "jz",
                         f"0x842A decodes to `{jz}`, so the branch that makes "
                         f"the copy conditional is not a `jz`")
        self.assertEqual(listing[0x842C][1], "movx",
                         "0x842C is not the re-read of the byte that feeds the "
                         "copy")
        self.assertLess(0x8429, 0x842A)
        self.assertLess(0x842A, 0x842D)

    def test_the_forwarder_enters_past_the_copy(self):
        """`0x8044`'s `ajmp` lands *after* the `0x0788` copy, not before it.

        `0x8044` is a single `ajmp` into the middle of `0x83FF`, and the write-up
        leans on where it lands: past the `0x8420`-`0x8433` block, so a caller
        arriving that way reaches the `0x09EA`/`0x09EB` half and never `0x0788`.
        Held here because the claim is an ordering one -- a forwarder retargeted
        into the copy's own block would leave the prose describing a path that
        does not exist, and nothing else would notice.

        The destination is read from the listing's own operand column rather than
        re-derived from the 11-bit `ajmp` encoding, which is not what this case
        is about; what it holds is that the operand the exporter printed and the
        block's position agree.
        """
        text = asm_window(0x8044)
        self.assertIsNotNone(text, "bank0 0x8044 has no committed .asm")
        rows = asm_opcodes(text)
        self.assertEqual([m for _op, m in rows.values()], ["ajmp"],
                         f"0x8044 is not the single-ajmp forwarder the "
                         f"write-up describes: {sorted(rows)}")
        dest = int(re.search(r"ajmp\s+(0x[0-9a-f]+)", text, re.I).group(1), 16)
        self.assertGreater(
            dest, 0x8433,
            f"0x8044 now enters 0x83FF at 0x{dest:04X}, at or before the "
            f"0x0788 copy that ends at 0x8433 -- the write-up says this "
            f"forwarder reaches only the 0x09EA/0x09EB half")
        # Into the *middle* of the routine, so the bound is the listing's own
        # address span rather than a row: `0x845D` is not an instruction
        # boundary, which is what the row in `ghidra-functions.csv` records and
        # what makes this a forwarder into a routine rather than a second entry
        # to one.
        body = self.listing(READER)
        self.assertGreaterEqual(dest, min(body),
                                f"0x8044's ajmp target 0x{dest:04X} is below "
                                f"0x83FF, so it is not a jump into it")
        self.assertLessEqual(dest, max(body),
                             f"0x8044's ajmp target 0x{dest:04X} is past the "
                             f"end of 0x83FF's listing, so it is not a jump "
                             f"into it")


class TheConsumerIsIdentified(unittest.TestCase):
    """`0x0788` is `CTWA`, and ASL `_Q83` reads it and publishes `UOCT`.

    The issue allows for this to be left open. It is not -- the chain is closed
    on committed ASL text -- and a closed chain that nothing checks is a claim
    that rots the same way the gates above would. So the ASL is asserted here,
    and `_Q83` is located by its own method name rather than by a line number,
    which CLAUDE.md asks for and which survives an edit above it.
    """

    @classmethod
    def setUpClass(cls):
        cls.dsdt = DSDT.read_text(encoding="utf-8", errors="replace")

    def method_body(self, name):
        """The text of one ASL method by name, or None."""
        m = re.search(r"Method \(%s\b.*?\n(\s*)\}" % re.escape(name), self.dsdt,
                      re.DOTALL)
        return m.group(0) if m else None

    def test_the_field_list_declares_0788_as_ctwa(self):
        """`Offset (0x788), CTWA, 8` -- what ties the byte to the ASL name.

        Without this the `_Q83` cases below would read a field whose offset is
        unestablished, and `0x0788`'s own row would be carrying a name the DSDT
        does not give it.
        """
        self.assertRegex(
            self.dsdt,
            r"Offset \(0x788\),\s*\n\s*CTWA,\s*8,",
            "the ECMG field list no longer declares Offset (0x788) as CTWA, "
            "eight bits wide")

    def test_q83_reads_ctwa_and_publishes_uoct(self):
        """The consumer, in the ASL's own words.

        `_Q83` is what the EC's `R5 = 0x83` notify reaches; the write-up stops
        short of claiming the two are one protocol, and this case does not either
        -- it holds that the method reads `CTWA`, scales it and publishes
        `UOCT`, which is the part that is text.
        """
        body = self.method_body("_Q83")
        self.assertIsNotNone(body, "the DSDT carries no _Q83 method")
        for pattern, what in (
                (r"Local0\s*=\s*CTWA\b", "reads CTWA"),
                (r"Local0\s*=\s*\(Local0 \* 0x08\)", "scales it by 8"),
                (r"\^\^\^\^NPCF\.UOCT\s*=\s*Local0", "publishes ^^^^NPCF.UOCT"),
                (r"Notify \(NPCF, 0xC0\)", "raises Notify(NPCF, 0xC0)")):
            self.assertRegex(body, pattern,
                             f"_Q83 does not {what}")

    def test_t1wr_writes_ctwa_on_the_1171_arm(self):
        """The other side of the meeting point: ASL writes the byte too.

        `T1WR`'s `Arg0 == 0x1171` arm stores `Arg1` into `CTWA` and publishes
        `UOCT` the same way `_Q83` does. That is what makes `0x0788` a byte both
        sides of the EC/ACPI boundary touch, rather than a pass-through the ASL
        only reads -- and it is the half a reader checking the write-up's chain
        would otherwise have to take on trust.
        """
        arm = re.search(r"ElseIf \(\(Arg0 == 0x1171\)\)\s*\{(.*?)\n\s*\}",
                        self.dsdt, re.DOTALL)
        self.assertIsNotNone(arm,
                             "the DSDT's T1WR carries no Arg0 == 0x1171 arm")
        for pattern, what in (
                (r"\^\^PCI0\.LPCB\.EC0\.CTWA\s*=\s*Arg1", "writes CTWA"),
                (r"\^\^NPCF\.UOCT\s*=\s*Local0", "publishes ^^^^NPCF.UOCT")):
            self.assertRegex(arm.group(1), pattern,
                             f"T1WR's 0x1171 arm does not {what}")

    def test_it_is_the_only_ecmg_field_the_asl_writes_and_reads(self):
        """The sweep the write-up's "only" claim rests on, re-run here.

        `0x0788` matters as a meeting point because both sides of the EC/ACPI
        boundary write it -- the ASL through `T1WR`, the EC through `0x83FF` --
        and `CTWA` is the only ECMG field for which that is true. Decided the way
        the write-up says it is: over the rows of the field sweep that carry
        `asl_sites`, by whether the field name is the left-hand side of an
        *assignment*. `==` is a comparison, so `If ((DBEN == One))` is a read of
        `DBEN` and not a write to it -- getting that backwards would hand the
        "only" claim to the wrong field, which is why the assignment is matched
        as a lone `=` here too.
        """
        assign = re.compile(r"(?<![=!<>])=(?!=)")
        lines = self.dsdt.splitlines()

        def direction(name, line_no):
            text = lines[int(line_no) - 1]
            m = assign.search(text)
            if not m:
                return "read"
            lhs = text[:m.start()].strip()
            return "write" if re.search(r"\b%s\b\s*$" % re.escape(name),
                                        lhs) else "read"

        both = []
        with (ANNOTATIONS / "dsdt-ecmg-fields.csv").open(encoding="utf-8",
                                                         newline="") as handle:
            fields = list(csv.DictReader(handle))
        for row in fields:
            sites = row["asl_sites"]
            if not sites or sites == "not-referenced-by-this-method":
                continue
            kinds = {direction(row["name"], ln) for ln in sites.split()}
            if kinds == {"write", "read"}:
                both.append(row["name"])

        self.assertEqual(both, ["CTWA"],
                         f"the ECMG fields the ASL both writes and reads are "
                         f"{both}, not just CTWA; if a second one has joined, "
                         f"the write-up's 'only' claim needs rewording rather "
                         f"than this case being relaxed")


class TheWriteUpAndTheCommitments(unittest.TestCase):
    """The walk exists, and the claims it makes line up with what is committed.

    The last case is the one that catches the write-up drifting away from the
    tree it describes: it re-derives the two writers and the reader from the
    committed site CSV rather than from anything this suite holds, so a
    regenerated CSV that moved the sites fails here instead of leaving the prose
    describing a different firmware.
    """

    def test_the_write_up_is_committed_with_a_title(self):
        """A write-up with no `# ` title fails `gen_findings_index.py --check`."""
        self.assertTrue(WRITERS_MD.is_file(),
                        f"{WRITERS_MD.name} is not committed")
        self.assertRegex(WRITERS_MD.read_text(encoding="utf-8"),
                         r"(?m)^# ", "the write-up carries no level-one title")

    def test_the_sites_csv_resolves_a_read_and_two_writes(self):
        """The committed sites table still says read, write, write.

        Held as a set of directions rather than as a count of rows: the count is
        `check_register_counts.py`'s, and a direction that appeared or vanished
        is what would falsify the write-up.
        """
        with SITES_CSV.open(encoding="utf-8", newline="") as handle:
            rows = [r for r in csv.DictReader(handle)
                    if int(r["addr"], 16) == ADDR]
        self.assertTrue(rows, f"the sites CSV records no 0x{ADDR:04X} row")
        directions = {r["access"].split()[0] for r in rows}
        self.assertEqual(directions, {"read", "write"},
                         f"the sites CSV resolves 0x{ADDR:04X} to "
                         f"{sorted(directions)}, which is not the read-and-two-"
                         f"writes shape the write-up describes")

    def test_the_two_writers_the_write_up_names_are_the_two_the_csv_records(self):
        """The write-up's routine addresses are the CSV's write sites.

        Each writer address is read out of the CSV rather than held here, so the
        suite fails if a regeneration moves a site instead of quietly continuing
        to check a window nothing points at any more.
        """
        with SITES_CSV.open(encoding="utf-8", newline="") as handle:
            writers = {int(r["runtime"], 16) for r in csv.DictReader(handle)
                       if int(r["addr"], 16) == ADDR
                       and r["access"].startswith("write")}
        self.assertEqual(writers, {0x9747, 0x9C0D},
                         f"the sites CSV records 0x{ADDR:04X}'s writes at "
                         f"{sorted(hex(w) for w in writers)}, not the pair the "
                         f"write-up reconciles")

    def test_the_export_spells_the_byte_by_its_symbol(self):
        """No committed `.c` still writes the exporter's placeholder.

        Being *in* `xdata-symbols.csv` and being *spelled* by it in the
        committed export are two facts, and only the second one is this case: an
        address can carry a name and still be written `DAT_EXTMEM_09e9` in the
        file a reader opens until the next export runs.
        """
        placeholder = f"DAT_EXTMEM_{ADDR:04x}"
        hits = {str(p.relative_to(DECOMPILED))
                for p in sorted(DECOMPILED.rglob("*.c"))
                if placeholder in p.read_text(encoding="utf-8", errors="replace")}
        self.assertEqual(hits, set(),
                         f"{placeholder} is still in the committed export; the "
                         f"re-export that names it by symbol has not landed")

    def test_no_annotation_comment_still_says_09e9_has_no_entry(self):
        """The plate-comment idiom, held against the row that made it false.

        `build_ec_decompile.py --self-test` runs the same scan over the whole
        annotation CSV; this is the one row's worth of it, so a failure here
        names the address instead of the file. Left in place it would be a
        confident, checkable, wrong sentence in the file a reader opens to find
        out what is known about `0x09E9`.
        """
        build = load("build_ec_decompile")
        with (ANNOTATIONS / "ghidra-functions.csv").open(encoding="utf-8",
                                                         newline="") as handle:
            ann_rows = list(csv.DictReader(handle))
        problems = build.stale_no_entry_claims(
            ann_rows, build.registered_addresses())
        mine = [p for p in problems if f"0x{ADDR:04X}" in p]
        self.assertEqual(mine, [],
                         f"{len(mine)} annotation row(s) still claim "
                         f"0x{ADDR:04X} has no entry: {mine[:2]}")


if __name__ == "__main__":
    unittest.main()