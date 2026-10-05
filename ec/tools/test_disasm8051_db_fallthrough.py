#!/usr/bin/env python3
"""What reaches `disasm8051.mnemonic()`'s `db` fall-through, and what it names.

`disasm8051.py --self-test` holds the hand-transcribed windows, the branch
sites and the bit-form sites. It does not hold the wider mnemonic table, because
those names were decided against a different oracle: the committed Ghidra
listings, which carry Ghidra's own mnemonic on every row and have never seen
this file. This suite is where that table is held instead, and the write-up is
`../../docs/findings/mnemonic-db-fallthrough-coverage.md`.

The oracle discipline is what separates the cases. **What reaches `db`** is
derived by calling `mnemonic()` and `opcode_coverage.MCS51_LEN` over the whole
map and comparing, so it fails if either table drifts and states no figure of
its own -- a count here would be a value every landing rename has to edit, which
is the mistake `CLAUDE.md`'s no-totals rule exists to stop. **What each named
value is called** is read live out of the committed `.asm` rows rather than
transcribed, for the reason `BIT_SITES` and `TEXTBOOK_BIT_SITES` both record: an
expectation derived from the tool under test agrees with it whatever it were.
**What the bytes `citation_gap_scan.UNASSIGNED` holds are** is paired against
the real instruction either side of each, in the `TEXTBOOK_BIT_SITES` shape, so a
decoder keying on the wrong operand cannot pass. **What the remaining `db` is**
is the negative of the negative, since a decoder that stopped printing `db`
anywhere would satisfy every case above vacuously. **What did not change** is
`OPCODE_LEN`, asserted for the values this work names, because a length change
would be a framing claim and this work makes none.

No firmware image and no subprocess, so this runs in the cheap tier. The
listings are read from disk, which is the whole point -- the oracle has to be a
file nobody on this branch wrote.
"""
import csv
import importlib.util
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load("disasm8051")
C = _load("opcode_coverage")

DECOMPILED = REPO / "ec" / "decompiled"
LISTING_INDEX = DECOMPILED / "listing-index.csv"

# The byte column is three fixed-width slots of two hex digits, `-` for the
# slots an instruction does not fill, then the mnemonic. The padding is not
# cosmetic: `da` is the one mnemonic that is also two hex digits, so a run of
# hex pairs would be ambiguous exactly where this table is most delicate -- the
# reason `0xD4` is in the set this suite checks.
LINE_RE = re.compile(r"^([0-9A-Fa-f]+)\s+(.*)$")
BYTE_SLOT = re.compile(r"^(?:[0-9A-Fa-f]{2}|-)$")

# The byte values issue #1153 gave `mnemonic()` a case for, and the only place
# in this repository that enumeration belongs outside the write-up's own table.
# It is a *scope*, not a total: the cases that would go stale as it grows are
# the ones built by complement above, and this set only has to say which values
# this issue's length claim covers. Adding to it means a new value was named and
# the write-up's table has a row for it.
NAMED_HERE = (0x06, 0x07, 0x16, 0x17, 0x26, 0x27, 0x36, 0x37, 0x46, 0x47,
              0x56, 0x57, 0x66, 0x67, 0x72, 0x76, 0x77, 0x82, 0x86, 0x87,
              0x96, 0x97, 0xA6, 0xA7, 0xB6, 0xB7, 0xD4, 0xF4)


def listing_first_tokens():
    """{opcode: {ghidra's first token, ...}} over the committed listings.

    Read from `listing-index.csv` rather than by globbing `*.asm`, the same rule
    `opcode_coverage.read_listings()` documents: the index is the committed
    inventory, so a listing on disk the index does not name is a listing no other
    check counts. Only the *first* token is taken, because that is the
    instruction name; everything after it is operand spelling, and this module
    renders operands its own way (`bit_name()`, lowercase registers, `@r0` where
    Ghidra writes `@R0`) in every case the corpus can check.
    """
    seen = {}
    with LISTING_INDEX.open(newline="") as fh:
        for row in csv.DictReader(fh):
            rel = row["out_file"]
            if not rel or rel.startswith("("):
                continue
            path = DECOMPILED / rel
            if not path.is_file():
                continue
            with path.open(errors="replace") as asm:
                for line in asm:
                    if line.startswith(";") or not line.strip():
                        continue
                    m = LINE_RE.match(line.rstrip("\n"))
                    if not m:
                        continue
                    _addr, rest = m.groups()
                    slots = rest.split()
                    # The first slot is the opcode only if it is a byte; a row
                    # whose slots are all `-` has nothing to take a length from,
                    # which is `parse_listing()`'s rule too.
                    if not slots or not BYTE_SLOT.match(slots[0]):
                        continue
                    text = " ".join(slots[3:]).strip()
                    if not text:
                        continue
                    seen.setdefault(int(slots[0], 16), set()).add(
                        text.split()[0].lower())
    return seen


class DbFallThrough(unittest.TestCase):
    """The reachable set, held as a relation between two tables rather than as
    a list typed here, so it fails if either drifts."""

    def test_db_is_reachable_for_exactly_what_the_manual_leaves_unassigned(self):
        # The claim, as a relation: a byte value prints as `db` if and only if
        # `MCS51_LEN` leaves it with no length. Both sides are read from the
        # tables themselves, so neither this suite nor the decoder's docstring
        # carries a figure that a landing rename would make stale -- and a value
        # the manual assigns is caught whichever table is wrong.
        ours = {op for op in range(256)
                if D.mnemonic(bytes([op]) + bytes(8), 0).startswith("db ")}
        manual = {op for op in range(256) if C.MCS51_LEN[op] == 0}
        self.assertEqual(ours, manual)
        # And the pair is not trivially empty on both sides: an empty relation
        # would satisfy the equality above while asserting nothing at all.
        self.assertTrue(manual,
                        "the manual leaves at least one byte value unassigned, "
                        "so the relation is not vacuously true")

    def test_the_one_remaining_db_is_not_named_by_the_listings(self):
        # Why `db` stays reachable rather than being a dead branch: the manual
        # assigns its byte value no instruction, and no committed listing places
        # it at an instruction start either, so there is nothing to transcribe a
        # spelling from. That is *not found by this method*, not "absent" --
        # `OPCODE_LEN` still gives it a length, so a walk that lands on one is a
        # byte this firmware uses as something other than an opcode.
        db_ops = {op for op in range(256)
                  if D.mnemonic(bytes([op]) + bytes(8), 0).startswith("db ")}
        tokens = listing_first_tokens()
        for op in sorted(db_ops):
            with self.subTest(op=f"0x{op:02x}"):
                self.assertNotIn(op, tokens)
                self.assertEqual(C.MCS51_LEN[op], 0)
                self.assertEqual(D.mnemonic(bytes([op, 0x00]), 0),
                                 f"db   0x{op:02x}")


class NamedAgainstTheListings(unittest.TestCase):
    """Every newly named value, checked against the file it was decided from.

    The oracle is read from disk at run time rather than transcribed into this
    file. A transcribed expectation is a copy of what the author believed when
    they wrote it, and it would keep passing after the listing it came from was
    re-cut; a read one cannot. The write-up carries the per-value citations.
    """

    def test_each_named_value_agrees_with_every_ghidra_token_for_it(self):
        # Built from the complement of the two cases above rather than from a
        # list of the values this change added: what is wanted is the property
        # "named values agree with the corpus", and naming the set here would
        # make a later rename need this file edited.
        tokens = listing_first_tokens()
        db_ops = {op for op in range(256)
                  if D.mnemonic(bytes([op]) + bytes(8), 0).startswith("db ")}
        checked = 0
        for op in sorted(set(tokens) - db_ops):
            ours = D.mnemonic(bytes([op, 0x34, 0x56, 0x78]), 0, 0).split()[0]
            with self.subTest(op=f"0x{op:02x}"):
                self.assertEqual(tokens[op], {ours.lower()})
            checked += 1
        # The corpus must actually have been read, or every subTest above passed
        # vacuously over an empty dict.
        self.assertTrue(checked, "no listing rows parsed")

    def test_opcode_len_is_unchanged_for_every_value_this_issue_names(self):
        # The whole reason this is a naming job and not a framing one: every
        # value below was already sized correctly, and a length change would
        # re-frame every window containing one. This issue makes no framing
        # claim, so the table is held against the manual's -- and only over the
        # values the write-up enumerates, because sweeping all 256 would fail on
        # `0xA8`-`0xAF`, where `MCS51_LEN` is itself the wrong transcription and
        # `opcode_coverage.py --divergence` reports that divergence deliberately.
        # That belongs to the tool that owns it, not to a suite about mnemonics.
        for op in NAMED_HERE:
            with self.subTest(op=f"0x{op:02x}"):
                self.assertEqual(D.OPCODE_LEN[op], C.MCS51_LEN[op])
                # ...and it is actually named, so this case is not satisfied by
                # a value the table already declined.
                self.assertFalse(
                    D.mnemonic(bytes([op, 0x34, 0x56, 0x78]), 0, 0)
                    .startswith("db "))


class TheFourUnassignedBytes(unittest.TestCase):
    """`0x06`/`0x07`/`0x16`/`0x17`, which two other tools grade windows against.

    `citation_gap_scan.UNASSIGNED` and `bank_map_score.UNASSIGNED` both hold
    these four and both used to describe them as the byte values the MCS-51 map
    assigns to no instruction. That was wrong -- the map assigns all four -- and
    issue #1153 named them here. Neither set was changed, because both drive a
    published verdict and a ranking; what is held below is that the decoder and
    the map now agree on all four, and that they agree with the *right* one.
    """

    def setUp(self):
        self.scan = _load("citation_gap_scan")

    def test_the_set_is_the_citation_scanners_and_they_are_all_named(self):
        # Read from the scanner rather than written here, so the set and this
        # suite cannot drift into each other being right.
        self.assertEqual(set(self.scan.UNASSIGNED), {0x06, 0x07, 0x16, 0x17})
        for b in sorted(self.scan.UNASSIGNED):
            with self.subTest(op=f"0x{b:02x}"):
                self.assertFalse(
                    D.mnemonic(bytes([b, 0x00]), 0).startswith("db "))

    def test_each_is_paired_against_the_instruction_either_side_of_it(self):
        # The pairing is the assertion. `0x06`/`0x07` sit between `INC direct`
        # and `INC Rn`, and `0x16`/`0x17` between `DEC direct` and `DEC R0`; a
        # decoder keying on the operand byte rather than the opcode would print
        # the neighbour's text here and pass a first-token-only check. Same shape
        # as `TEXTBOOK_BIT_SITES`'s `0xC1`/`0xC2`.
        for op, want in ((0x05, "inc  0x20"), (0x06, "inc  @r0"),
                         (0x07, "inc  @r1"), (0x08, "inc  r0"),
                         (0x15, "dec  0x20"), (0x16, "dec  @r0"),
                         (0x17, "dec  @r1"), (0x18, "dec  r0")):
            with self.subTest(op=f"0x{op:02x}"):
                self.assertEqual(D.mnemonic(bytes([op, 0x20]), 0, 0), want)

    def test_the_criterion_reads_the_byte_and_not_the_text(self):
        # Why naming them moved no verdict: `verdict_of()` is driven by the flag
        # the walk sets from `window[i] in UNASSIGNED`, so the decoder's spelling
        # is never consulted. Same flag, real mnemonic, same answer -- which is
        # what makes leaving the set alone safe rather than merely convenient.
        self.assertEqual(
            self.scan.verdict_of([(0x3AF0, b"\x17", "db   0x17", True)]),
            "not-code")
        self.assertEqual(
            self.scan.verdict_of([(0x3AF0, b"\x17", D.mnemonic(b"\x17", 0), True)]),
            "not-code")


if __name__ == "__main__":
    unittest.main()