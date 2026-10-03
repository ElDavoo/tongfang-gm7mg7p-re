#!/usr/bin/env python3
"""Holds the five facts `docs/findings/d8a0-init-routine.md` rests on.

That write-up reads `bank0,0xD8A0`, the routine one byte on from the `ret`
stub the reset vector's `common,0x158E` trampoline names. Nothing in the
repository pinned any of it: the routine has no listing, no index row and no
`ghidra-functions.csv` row, so every claim in the write-up is a claim about
the committed image and the committed decoder, and all of them would rot
silently if the decode, the frame evidence or the call graph moved.

Each case below is that kind of claim, re-derived by running the committed
tool that produced it. **No count of the tree is asserted** -- the write-up's
own figures are over the committed firmware, which no merge can move, and the
suite names an address or a byte where it can rather than counting rows,
suites or write-ups.

**What it does not hold, on purpose.** `check_register_counts.py` already
re-derives the three `static_refs` fields of every `registers.yaml` entry
against the image, and `check_status_vocabulary.py` already refuses a
`present-untested` address with no resolving EC-side site. This suite starts
one level up and holds the two facts those tools take as given: that the four
`0x20xx` addresses named in the write-up have exactly one direct site each and
that site is inside this routine, and that `common,0x1504` -- the trampoline
that reaches it -- has exactly one caller.

It does not assert that `ec/decompiled/bank0/D8A0.asm` is absent. That
absence is a deferral, not a property: the write-up carries the row-by-row
table for the pinned-toolchain run that lands the listing, and a test that
failed when it landed would have to be deleted rather than fixed.

Read-only and offline: the committed image and the committed tools. No
Ghidra, no network, no hardware, and no claim about behaviour on a machine.
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
EC = HERE.parent
FIRMWARE = EC / "firmware" / "GMxMGxx_11.800"

# The routine's byte range, as the decode establishes it: 0xD8A0 through the
# three-byte tail jump at 0xD924. The four XDATA sites below are checked to
# fall inside it, which is the claim that makes them this routine's.
ROUTINE_START = 0xD8A0
ROUTINE_END = 0xD927  # exclusive: 0xD927 is the next entry, not a continuation

# The four bytes of the 0x20xx page this routine alone touches, and where the
# decode puts each site. `0x201C` is the issue's own; the other three are in
# the routine's last block, which the issue's 40-instruction window stopped
# short of.
QUARTET = {0x2012: 0xD90E, 0x2014: 0xD915, 0x2015: 0xD91B, 0x201C: 0xD8CC}


def run(*args):
    """Run a committed tool and return its stdout, or fail the test."""
    proc = subprocess.run([sys.executable, *map(str, args)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"{args[0]} exited {proc.returncode}: "
                             f"{proc.stderr.strip()[:400]}")
    return proc.stdout


def decode(n, at="0x0D8A0"):
    """The committed decoder's listing of the routine, `n` instructions long."""
    return run(HERE / "disasm8051.py", FIRMWARE,
               "--at", at, "--runtime", at, "-n", str(n)).splitlines()


def image():
    return FIRMWARE.read_bytes()


class RoutineShape(unittest.TestCase):
    """`0xD8A0` is a 60-instruction routine whose exit is a tail jump."""

    def test_decodes_to_a_tail_jump_and_no_ret(self):
        # 60 instructions, not 61: the 61st is the first instruction of the
        # next entry, which is why the window is pinned at 60 rather than at
        # whatever length happens to look like a function.
        listing = decode(60)
        self.assertEqual(len(listing), 60,
                         "the routine is 60 instructions; a different count "
                         "means the decode moved")
        self.assertEqual(listing[-1].split()[0], "0xd924",
                         "the last instruction of the 60 is the tail jump")
        self.assertIn("ljmp 0xeada", listing[-1],
                      "the exit is ljmp 0xEADA, not a call")
        rets = [ln for ln in listing if re.search(r"\bret\b", ln)]
        self.assertEqual(rets, [],
                         "no ret in the routine: it exits by tail jump, so "
                         "the issue's 'decode to its ret' has no object")

    def test_spans_87_bytes_up_to_the_next_entry(self):
        self.assertEqual(ROUTINE_END - ROUTINE_START, 0x87,
                         "0x87 bytes, 0xD8A0..0xD926")

    def test_is_an_instruction_start_by_frame_evidence(self):
        out = run(HERE / "disasm8051.py", FIRMWARE,
                  "--at", "0x0D8A0", "--converge").strip()
        self.assertEqual(out, "0x0D8A0: 24 of 24 preceding anchors decode "
                              "onto it, 0 step over it",
                         "24/24 with 0 stepping over rules out an operand "
                         "byte mistaken for an entry")


class FourBytesOfThePageWithNoRegisterRow(unittest.TestCase):
    """Each of the four has exactly one direct site, and it is in this routine."""

    def _sites_in_image(self, addr):
        pat = bytes((0x90, addr >> 8, addr & 0xFF))
        return [i for i in range(len(image()) - 2) if image()[i:i + 3] == pat]

    def test_each_has_exactly_one_direct_site(self):
        for addr, expected in sorted(QUARTET.items()):
            with self.subTest(addr=f"0x{addr:04X}"):
                sites = self._sites_in_image(addr)
                self.assertEqual(len(sites), 1,
                                 f"0x{addr:04X} has one direct MOV DPTR site "
                                 f"in the image, not {len(sites)}")
                self.assertEqual(sites[0], expected,
                                 f"0x{addr:04X}'s sole site is at "
                                 f"0x{expected:04X}")

    def test_every_site_is_inside_the_routine(self):
        # This is the finding, and it is what a per-address count alone would
        # not say: the routine is the sole direct accessor of all four.
        for addr, site in sorted(QUARTET.items()):
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertTrue(ROUTINE_START <= site < ROUTINE_END,
                                f"0x{addr:04X}'s site 0x{site:04X} is inside "
                                f"the routine's 0xD8A0-0xD926")

    def test_the_ec_side_count_is_one_for_each(self):
        # `scan_refs.py` splits the count per image; the PD image at file
        # 0x20000 has its own XDATA map, so an EC-side count of 1 is the
        # claim the register rows' warrant rests on.
        for addr in sorted(QUARTET):
            with self.subTest(addr=f"0x{addr:04X}"):
                out = run(HERE / "scan_refs.py", FIRMWARE, f"0x{addr:04X}")
                line = next(ln for ln in out.splitlines()
                            if ln.startswith(f"0x{addr:04X}  "))
                self.assertRegex(line, r"\brefs=1\s+ec=1\s+pd=0\b",
                                 f"0x{addr:04X}: one EC-side site, no PD "
                                 f"site; got {line!r}")


class TrampolineAndItsOneCaller(unittest.TestCase):
    """`common,0x1504` reaches the routine, and exactly one site calls it."""

    def test_listing_is_the_six_byte_bank_switch_trampoline(self):
        text = (EC / "decompiled" / "common" / "1504.asm").read_text()
        body = [ln for ln in text.splitlines() if re.match(r"^150[47] ", ln)]
        self.assertEqual(len(body), 2, "the listing is two instructions")
        self.assertIn("90 d8 a0", body[0], "DPTR carries 0xD8A0")
        self.assertIn("02 11 00", body[1], "tail-jumps the bank-0 stub 0x1100")
        self.assertNotIn("22", text.split("1504")[-1].split("\n")[0],
                         "no ret: the trailing return in the .c is the "
                         "decompiler reading the tail jump")

    def test_index_records_it_as_six_bytes(self):
        row = next(ln for ln in
                   (EC / "decompiled" / "index.csv").read_text().splitlines()
                   if ln.startswith("common,1504,"))
        self.assertEqual(row.split(",")[3], "6",
                         "index.csv records the six-byte trampoline")

    def test_exactly_one_lcall_names_it(self):
        data = image()
        for op, name, expected in ((b"\x12", "lcall", [0x026C]),
                                   (b"\x02", "ljmp", [])):
            with self.subTest(operand=name):
                pat = op + bytes((0x15, 0x04))
                sites = [i for i in range(len(data) - 2)
                         if data[i:i + 3] == pat]
                self.assertEqual(
                    sites, expected,
                    f"the sole lcall naming 0x1504 is at common 0x026C, and "
                    f"no {name} names it")

    def test_the_caller_site_is_the_committed_listing_line(self):
        listing = (EC / "decompiled" / "common" / "0213.asm").read_text()
        self.assertRegex(listing, r"(?m)^026C\s+12 15 04 lcall",
                         "ec/decompiled/common/0213.asm carries the "
                         "`lcall 0x1504` at 0x026C")

    def test_no_branch_operand_names_the_routine_itself(self):
        # The uniqueness claim behind the write-up: 0xD8A0 is reachable only
        # through its DPTR-carrying trampoline, never as a branch operand.
        for op, name in ((b"\x12", "lcall"), (b"\x02", "ljmp")):
            with self.subTest(operand=name):
                pat = op + bytes((0xD8, 0xA0))
                data = image()
                self.assertEqual([i for i in range(len(data) - 2)
                                  if data[i:i + 3] == pat], [],
                                 f"no {name} operand names 0xD8A0")


class RegisterRows(unittest.TestCase):
    """The four rows record what the write-up claims for them."""

    ROWS = ("XDATA_2012", "XDATA_2014", "XDATA_2015", "XDATA_201C")

    def _entries(self):
        import yaml
        return {e["name"]: e for e in
                yaml.safe_load((EC / "annotations" / "registers.yaml")
                               .read_text())["registers"]}

    def test_each_row_is_present_untested_with_the_three_counts(self):
        entries = self._entries()
        for name in self.ROWS:
            with self.subTest(register=name):
                entry = entries[name]
                self.assertEqual(entry["status"], "present-untested",
                                 f"{name} is present-untested: the ceiling, "
                                 "since nothing was run on hardware")
                self.assertEqual(entry["static_refs"], 1)
                self.assertEqual(entry["static_refs_main_ec"], 1)
                self.assertEqual(entry["static_refs_pd_image"], 0)

    def test_each_row_is_registered_as_not_reaching_the_decompiled_tree(self):
        # xdata_register_map.py refuses a named address that no NOT_IN_TREE
        # reason explains, so this is what keeps the four from reading as a
        # coverage gap nobody owns.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "xdata_register_map", HERE / "xdata_register_map.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in self.ROWS:
            with self.subTest(register=name):
                addr = self._entries()[name]["addr"]
                self.assertIn(addr, mod.NOT_IN_TREE,
                              f"0x{addr:04X} has a NOT_IN_TREE reason")
                # Every reason cites the site offset that re-derives it,
                # which is the handle the house idiom uses -- 0x0EAF names
                # "bank0 0xF36D", 0x07C1 defers to 0x07C0 and names its own
                # pd site. The shared comment above the four names 0xD8A0.
                self.assertIn(
                    "0x" + f"{QUARTET[addr]:04X}", mod.NOT_IN_TREE[addr],
                    "the reason cites its own site offset, so a reader can "
                    "re-derive which routine the census cannot reach")
        for addr, forbidden in mod.NOT_IN_TREE.items():
            with self.subTest(addr=f"0x{addr:04X}"):
                low = mod.NOT_IN_TREE[addr].lower()
                for word in mod.NOT_IN_TREE_FORBIDDEN:
                    self.assertNotIn(word, low,
                                     f"0x{addr:04X}'s reason must not say "
                                     f"{word!r}: a reason is about the scan")


if __name__ == "__main__":
    unittest.main()