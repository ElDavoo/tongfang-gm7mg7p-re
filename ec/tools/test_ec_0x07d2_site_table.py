#!/usr/bin/env python3
"""The claims `ec/annotations/ec-0x07d2-sites.md` is written on, held against
the committed firmware and against each other (issue #226).

Every case here asserts a property of a committed file or of the firmware image
in `ec/firmware/GMxMGxx_11.800`, or an agreement between two committed
artefacts. None of them is a count of this repository's own text: the write-up
has no hand-kept total in it for exactly the reason CLAUDE.md gives, so there
is nothing here that a later merge has to edit a number out of. Where the
write-up *does* name an address -- the nine `inc dptr` walks, the one `no movx`
row, the three bit-operation sites -- the address is a property of the image
and is pinned here so a regeneration that moved one fails this suite rather
than leaving the prose quietly describing a different site.

**The image split is the load-bearing assertion, so it is the first one.**
`scan_refs.py` reports a bare `refs=47` for `0x07D2`, and a bare total adds the
EC firmware's XDATA map to the PD image's without saying so. Every row of the
table is `pd-image` and every row's `addr` is `0x07D2`; if either moved, the
register entry would be describing a different program than the table does, and
a PD-image decode cannot move an EC-side `status:` at all.

**The bit-operation verdict is asserted against the raw `window` text, not a
summary of it.** §6 of the write-up says `0x8B70` sets bit 3 of `0x07D2` and
that `0x8B81` sets bit 1 of `0x07D3` *after* the `inc dptr`, so the field
straddles a byte boundary. That second half is the whole finding, and it is the
half a summary would drop. So each case checks that the `orl` sits on the side
of the `inc dptr` the write-up names, read off the committed CSV rather than
re-derived, and `trace_xdata_refs.walk_why()`'s decode of the firmware is checked
against the same three addresses in `BitOperations` so the CSV cannot be the only
witness. (`disasm8051.py` is what the write-up quotes for these addresses and
agrees with both; it is not what this suite re-runs, because its own
`--self-test` is already driven by `test_pd_image_census.py` under
`tools/run-tests.sh`.)

**The two verdict sentences are compared as strings.** `ec-0x07d2-sites.md` §4.3
and `docs/findings/pd-07d2-index-or-word-half.md` both carry the answer to
"index or word half", and they are two files that will not otherwise be read
together. Asserting they are the same string is what stops the short one
drifting from the long one; it is a claim about two committed files, so it
costs nothing to keep true and is the only place the answer is written twice.
"""
import csv
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
EC = HERE.parent
REPO = EC.parent
sys.path.insert(0, str(HERE))

import trace_xdata_refs as tref  # noqa: E402

ANNOT = EC / "annotations"
SITES_CSV = ANNOT / "ec-0x07d2-sites.csv"
SITES_MD = ANNOT / "ec-0x07d2-sites.md"
FINDINGS_MD = REPO / "docs" / "findings" / "pd-07d2-index-or-word-half.md"
REGISTERS = ANNOT / "registers.yaml"
FIRMWARE = str(EC / "firmware" / "GMxMGxx_11.800")

ADDR = "0x07D2"

# The nine sites that walk past their own byte through `inc dptr`. Pinned
# because §4.2 of the write-up names each one and says what it reaches; a
# regeneration that moved one would leave the table describing a walk the
# image does not contain. One of them, F628, is the 24-bit store and the one
# `access_cell_corrections.py` carries.
WALK_SITES = ("0x8B70", "0x8B81", "0x8BAD", "0xA5DD", "0xA61C", "0xA660",
              "0xC755", "0xC780", "0xF628")

# The one row the walk scores `no movx`, and §5 of the write-up says why that
# is the walk stopping at a branch rather than the site being inert.
NO_MOVX_SITE = "0x6757"

# The bit operations of §6: site, the `orl` immediate, and the byte the write-up
# says the bit belongs to. `BIT_BYTE` is the claim under test -- 0x8B81 and
# 0x8BAD operate on 0x07D3, not 0x07D2, which is what makes the field straddle
# a byte boundary. Which of them actually *stores* is a separate claim, held by
# `STORES`: 0x8BAD's `orl` reaches only R5, so the field-boundary finding rests
# on the other two and is not a three-instruction span.
BIT_SITES = (("0x8B70", "#0x08", "0x07D2"),
             ("0x8B81", "#0x02", "0x07D3"),
             ("0x8BAD", "#0x01", "0x07D3"))

# The bit sites that store their bit back into the byte, as §6 now states it.
# 0x8BAD is deliberately absent: its `orl a,#0x01` goes into A and on into R5 and
# the pair goes to `0xDC29`, which writes 0xFFFE/0xFFFF, so its committed access
# cell carries no `write` at all. Asserted from the CSV and re-derived from the
# firmware, because a §6 that read it as a third bit set is exactly the drift
# this pins.
STORES = ("0x8B70", "0x8B81")

# The bit site that does not store, and the access cell §4.2 quotes for it.
NO_STORE_SITE = "0x8BAD"

VERDICT = (
    "On the PD side `0x07D2` is both: all nine of its `inc dptr` walks put it "
    "in the low position of a 16-bit — or, at `0xF628`, 24-bit — window with "
    "`0x07D3`, while four sites multiply it into an address on its own, so "
    "the address is a word's low byte in some routines and a standalone "
    "index in others, and no single reading of it holds everywhere."
)


def sites():
    with open(SITES_CSV, newline="") as f:
        return list(csv.DictReader(f))


def normalise(addr):
    """A runtime cell and a hand-written address as one spelling.

    The CSV pads runtime cells to four or five digits (`0x08B70` is written
    `0x8B70`, `0x2F628` appears only in `file_offset`), and every address in
    this suite is written the short way. Comparing the two without this is how
    a test passes by never matching the row it names.
    """
    s = addr.upper().replace("0X", "").lstrip("0")
    return s or "0"


def texts(insns):
    """`walk_why()`'s rows as their rendered instruction text.

    Each row is a `(offset, raw bytes, text)` triple, so joining the rows
    themselves renders the bytes rather than the disassembly. The renderer
    column-aligns its mnemonics (`orl  a,#0x08`) where the committed CSV's
    `window` cell does not, so each row is squeezed to single spaces before it
    is compared with a cell this suite reads.
    """
    return [" ".join(row[2].split()) for row in insns]


def prose(path):
    """A write-up as one whitespace-normalised line, block quotes unmarked.

    The verdict is a block quote in `ec-0x07d2-sites.md` and an ordinary
    paragraph in the findings file -- the same sentence, presented the way each
    page presents its own answer. Comparing the raw markdown would make this
    suite a test of which character starts a line.
    """
    lines = []
    for line in path.read_text().splitlines():
        lines.append(line[2:] if line.startswith("> ") else line)
    return " ".join(" ".join(lines).split())


class TheImageSplit(unittest.TestCase):
    """§1's claim, asserted on the table rather than on a summary of it."""

    def test_every_row_is_this_address_in_the_pd_image(self):
        for row in sites():
            with self.subTest(file_offset=row["file_offset"]):
                self.assertEqual(row["addr"], ADDR)
                self.assertEqual(row["region"], "pd-image")

    def test_no_two_rows_are_the_same_site(self):
        # §2's "distinct sites, not one function called repeatedly". Over
        # `runtime`, not over `file_offset`: two `MOV DPTR` bytes cannot share
        # a file offset, but the same runtime appearing twice would mean the
        # generator emitted one site twice, which is the failure the claim is
        # actually about.
        runtimes = [normalise(r["runtime"]) for r in sites()]
        self.assertEqual(len(runtimes), len(set(runtimes)))
        offsets = [r["file_offset"] for r in sites()]
        self.assertEqual(len(offsets), len(set(offsets)))


class AgainstTheRegisterEntry(unittest.TestCase):
    """The table and `registers.yaml` have to agree, or the count the rest of
    the tree cites is describing something the table does not hold."""

    def test_row_count_equals_the_recorded_pd_image_count(self):
        import yaml
        with open(REGISTERS) as f:
            registers = yaml.safe_load(f)["registers"]
        # `addr: 0x07D2` is a YAML integer, so the entry is keyed on the
        # number the register map already uses everywhere rather than on the
        # string this suite's other comparisons are written in. Getting that
        # wrong is a StopIteration, not a failure, so it is worth the comment.
        entry = next(e for e in registers
                     if isinstance(e.get("addr"), int)
                     and e["addr"] == int(ADDR, 16))
        self.assertEqual(len(sites()), entry["static_refs_pd_image"])
        self.assertEqual(entry["static_refs"], entry["static_refs_pd_image"])
        # 0 in the EC column is what keeps this a PD-image finding and what
        # forbids `present-untested` on this entry, so it is asserted rather
        # than left to check_status_vocabulary.py's rule 2 alone.
        self.assertEqual(entry["static_refs_main_ec"], 0)


class TheWalks(unittest.TestCase):
    """§4.2, the nine sites that reach `0x07D3`."""

    def test_every_named_walk_exists_and_walks(self):
        by_runtime = {normalise(r["runtime"]): r for r in sites()}
        for addr in WALK_SITES:
            with self.subTest(runtime=addr):
                row = by_runtime.get(normalise(addr))
                self.assertIsNotNone(row, f"{addr} is not a row of the table")
                self.assertIn("inc dptr", row["access"])

    def test_the_three_byte_walk_is_the_corrected_one(self):
        # F628 is the row `access_cell_corrections.py` carries: the committed
        # cell says three writes because the budget-8 window stopped at the
        # second `inc dptr`. `test_walk_budget_census.py` holds the correction
        # re-derivable; this holds that the table carries the corrected cell,
        # so the two cannot disagree about which string is the committed one.
        row = next(r for r in sites() if normalise(r["runtime"]) == "F628")
        self.assertIn("write x3", row["access"])


class TheNoMovxRow(unittest.TestCase):
    """§5: the one `no movx` row, and that it is a misframed window rather
    than an inert site."""

    def test_the_row_exists_and_is_scored_no_movx(self):
        rows = [r for r in sites() if normalise(r["runtime"])
                == normalise(NO_MOVX_SITE)]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["access"].startswith("no movx"))
        self.assertEqual(rows[0]["terminator"], "flow opcode")

    def test_the_window_stopped_at_a_branch_not_at_the_end_of_the_code(self):
        # The claim is that the walk stopped, so it has to be a branch: if the
        # byte after the site were not a flow opcode the `no movx` cell would
        # mean something else, and §5's whole reading of it would be wrong.
        with open(FIRMWARE, "rb") as f:
            d = f.read()
        row = next(r for r in sites()
                   if normalise(r["runtime"]) == normalise(NO_MOVX_SITE))
        insns, why = tref.walk_why(d, int(row["file_offset"], 16))
        self.assertEqual(why, "flow opcode")
        self.assertEqual(texts(insns)[1], "cjne a,#0x02,+0x08")


class BitOperations(unittest.TestCase):
    """§6: bit 3 of `0x07D2` and bit 1 of `0x07D3`, which is the field that
    straddles the byte boundary and is *not* the DSDT's unnamed field. Only
    `0x8B70` and `0x8B81` store; `0x8BAD` ORs into `R5` and hands the pair to
    `0xDC29`, which is why the span is two instructions and not three."""

    def test_the_committed_windows_carry_the_claimed_ors(self):
        by_runtime = {normalise(r["runtime"]): r for r in sites()}
        for addr, orl, byte in BIT_SITES:
            with self.subTest(runtime=addr):
                window = by_runtime[normalise(addr)]["window"]
                self.assertIn(f"orl a,{orl}", window)

    def test_two_of_the_three_operate_on_the_byte_after_the_inc_dptr(self):
        # The half of the verdict a summary would lose. 0x8B70's `orl` is the
        # first instruction of its window and therefore lands on 0x07D2; the
        # other two have it after `inc dptr` and therefore land on 0x07D3.
        by_runtime = {normalise(r["runtime"]): r for r in sites()}
        for addr, orl, byte in BIT_SITES:
            with self.subTest(runtime=addr):
                window = by_runtime[normalise(addr)]["window"].split(" ; ")
                i = next(n for n, insn in enumerate(window)
                         if insn.startswith(f"orl a,{orl}"))
                dptr_inc = next((n for n, insn in enumerate(window)
                                 if insn == "inc dptr"), None)
                on_07d2 = dptr_inc is None or i < dptr_inc
                self.assertEqual(on_07d2, byte == "0x07D2",
                                 f"{addr}: the orl sits on the wrong side of "
                                 "the inc dptr for the byte the write-up "
                                 "claims")

    def test_the_image_agrees_with_the_csv(self):
        # So the CSV is not the only witness for the claim above: the decode
        # is re-run against the firmware, which is where the addresses mean
        # anything.
        with open(FIRMWARE, "rb") as f:
            d = f.read()
        by_runtime = {normalise(r["runtime"]): r for r in sites()}
        for addr, orl, byte in BIT_SITES:
            with self.subTest(runtime=addr):
                row = by_runtime[normalise(addr)]
                insns, _ = tref.walk_why(d, int(row["file_offset"], 16))
                joined = " ; ".join(texts(insns))
                self.assertIn(f"orl a,{orl}", joined)

    def test_only_two_of_the_three_store_the_bit_back(self):
        # §6's second claim, and the one a summary collapses into the first:
        # that the straddling field is *written* by 0x8B70 and 0x8B81. Read off
        # the committed access cells, where a stored bit shows up as a `write`.
        by_runtime = {normalise(r["runtime"]): r for r in sites()}
        for addr in STORES:
            with self.subTest(runtime=addr):
                self.assertIn("write", by_runtime[normalise(addr)]["access"])
        row = by_runtime[normalise(NO_STORE_SITE)]
        self.assertNotIn("write", row["access"])

    def test_the_non_storing_site_really_has_no_store_instruction(self):
        # The same claim re-derived from the firmware, so the CSV is not the
        # only witness for it: 0x8BAD's window must reach no `movx @dptr` at
        # all. Its `orl a,#0x01` goes into A, then into R5, and the R4/R5 pair
        # goes to 0xDC29 -- which writes 0xFFFE/0xFFFF, not these two bytes.
        with open(FIRMWARE, "rb") as f:
            d = f.read()
        row = next(r for r in sites()
                   if normalise(r["runtime"]) == normalise(NO_STORE_SITE))
        insns, _ = tref.walk_why(d, int(row["file_offset"], 16))
        self.assertNotIn("movx @dptr,a", texts(insns))
        self.assertIn("mov r5,a", texts(insns))


class TheVerdictIsOneSentence(unittest.TestCase):
    """§4.3 of the write-up and the findings file carry the same answer, and
    the answer is the only thing written in two places."""

    def test_both_files_carry_the_verdict_verbatim(self):
        wanted = " ".join(VERDICT.split())
        for path in (SITES_MD, FINDINGS_MD):
            with self.subTest(path=path.name):
                self.assertIn(
                    wanted, prose(path),
                    f"{path.name} does not carry the shared verdict verbatim")

    def test_neither_file_states_only_one_of_the_two_readings(self):
        # A verdict that lost half its claim would still contain the sentence
        # if the sentence were edited, so this does not help -- it is here to
        # fail loudly if either file is rewritten around a different answer
        # while the other keeps the old one.
        for path in (SITES_MD, FINDINGS_MD):
            with self.subTest(path=path.name):
                text = prose(path)
                self.assertIn("standalone index", text)
                self.assertIn("word's low byte", text)


if __name__ == "__main__":
    unittest.main()