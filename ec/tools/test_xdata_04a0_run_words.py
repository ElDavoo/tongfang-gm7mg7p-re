#!/usr/bin/env python3
"""The byte facts behind `docs/findings/xdata-04a0-04ae-04be-words.md` (#732).

The write-up enters `0x04AE`/`0x04AF` and `0x04BE`/`0x04BF` as two 16-bit
up-counters whose zeroing rides the `0x0490` gate bits, and `0x04A0`/`0x04A1`
as two separate bytes with a corrected provenance. This suite pins the bytes
that reading stands on, and it is written so that the provenance claim in
particular **cannot pass on the wrong answer**: the case that matters reads
`B6C9.asm` and `888C.asm` and composes them, rather than checking the DPTR
literals at the call site -- literals that are the same whichever pair of bytes
moves, which is how the withdrawn mirror claim survived a suite that was green
over it.

**Every case is static and none of them is a behaviour.** No register was read,
written or read back and no site was seen run. Every byte assertion below is
made twice where it can be: once against the listing's own hex column and once
against the image at the runtime address that listing names, so a listing that
drifted from the firmware fails rather than agreeing with itself. A `write`
asserted here is an instruction, not evidence the EC acted on the byte, and
"no committed routine has been read setting `0x04A1` non-zero" is a statement
about this method, never "is always zero".

**The suite is not wired into `.github/scripts/agent-gates.sh`.** That file
lives under `.github/`, which this branch's push token cannot write, so the
registration is a human's one-line change. Until it is made this suite is run by
hand and nothing here should be read as implying CI runs it. The same situation
`ec/annotations/xdata-inc-dptr-only.md` §1 records for
`test_inc_dptr_sites.py`.

Committed files and the committed firmware only: no Ghidra, no network, no
hardware.
"""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import yaml  # noqa: E402

from trace_xdata_refs import offset_for_runtime  # noqa: E402
from disasm8051 import relative_target  # noqa: E402

DECOMPILED = HERE.parent / "decompiled"
ANNOTATIONS = HERE.parent / "annotations"
FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"

# The four entries this issue adds. Held by name rather than by a figure of the
# table: `registers.yaml` is the source of truth and the cases below read it.
NEW_ENTRIES = ("XDATA_04A0", "XDATA_04A1",
               "XDATA_04AE_COUNTER_A (16-bit up-counter, gate 0x0490 bit 1)",
               "XDATA_04BE_COUNTER_B (16-bit up-counter, gate 0x0490 bit 5)")

# `0xB6C9` reads four bytes into R3, R4, R1, R2 and `0x888C` stores R1 then R2,
# so the register each lands in is the whole of the provenance question. The
# order is asserted by parsing the listing rather than cited from it, so a
# listing that reordered the loads fails instead of agreeing with a comment.
B6C9_LOAD_ORDER = ("R3", "R4", "R1", "R2")


def listing(bank, addr):
    """Text of one committed .asm listing."""
    return (DECOMPILED / bank / f"{addr:04X}.asm").read_text()


def image_bytes():
    with open(FIRMWARE, "rb") as f:
        return f.read()


def at_runtime(bank, addr, length, data=None):
    """`length` bytes at `addr` as the bank sees them, read off the image.

    `offset_for_runtime` is trace_xdata_refs' own inverse of the runtime map,
    so this cannot drift from the tool that counted the sites.
    """
    if data is None:
        data = image_bytes()
    off = offset_for_runtime(addr, bank)
    if off is None:
        raise AssertionError(f"0x{addr:04X} is not reachable from {bank}")
    return data[off:off + length]


# A listing row is `<ADDR><gap><byte><gap><byte><gap><byte><gap><mnemonic>
# <operands>`, with the byte column "-" padded to three. The byte fields are
# matched positionally rather than by a run of hex-or-dash, because a run also
# swallows the padding and hands the mnemonic's first column to the operand
# slot.
ROW = re.compile(r"^([0-9A-F]{4})\s+([0-9a-f]{2}|-)\s([0-9a-f]{2}|-)"
                 r"\s([0-9a-f]{2}|-)\s+(\S+)\s+(.*?)\s*$")


def rows(text):
    """[(address, bytes, mnemonic, operands)] for every instruction of a listing.

    Keyed by the address column rather than by line number, which is the
    durable form: a listing can grow above a row without moving it.
    """
    out = []
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            out.append((int(m.group(1), 16),
                        " ".join(b for b in m.group(2, 3, 4) if b != "-"),
                        m.group(5), m.group(6).strip()))
    return out


def hex_runs(text):
    """{address: "aa bb"} for every instruction row, `-` padding dropped."""
    return {addr: byts for addr, byts, _, _ in rows(text) if byts}


def run_at(text, addr, nbytes):
    """The next `nbytes` of the listing's bytes, starting at `addr`.

    Walked instruction by instruction rather than by address, because an
    instruction's address is not its previous one's address plus its length:
    8051 is variable-width, so `range(addr, addr + n)` walks off the listing.
    """
    out = []
    for a, byts, _, _ in sorted(rows(text)):
        if a < addr:
            continue
        if len(" ".join(out).split()) >= nbytes:
            break
        out.extend(byts.split())
    return " ".join(out[:nbytes])


def clears_bits(mask):
    """The bit numbers `ANL A,#mask` clears -- the list a note must print."""
    return [b for b in range(8) if not (mask >> b) & 1]


# Which routine a quoted run belongs to, when it starts below the function's
# own address. `0xB841` and `0xB8E1` open with a countdown; the run the write-up
# quotes is the zeroing block further in, and reading it from the function's
# listing is what keeps the two from being confused.
RUN_OWNER = {0xB860: 0xB841, 0xB900: 0xB8E1, 0xC044: 0xC032, 0xB2E5: 0xB2D5}


def owner_of(addr):
    return RUN_OWNER.get(addr, addr)


# A unit word may appear only in a sentence carrying the refusal. Two
# subtractions, both of them false positives this tree's own notes would trip:
# `ms` lands inside "arms" and "systems", and a bare "second" is an ordinal in
# "the second of the two up-counters". What is left is a claim about time.
UNIT = re.compile(r"\b(seconds?|minutes?|msec|hz)\b", re.I)
UNIT_EXCEPT = re.compile(r"\bthe second of\b|\bsecond (?:up-)?counter", re.I)


def asserts_a_unit(sentence):
    """True when `sentence` uses a time unit as a claim rather than an ordinal."""
    scrubbed = UNIT_EXCEPT.sub(" ", sentence)
    return bool(UNIT.search(scrubbed))


def entry_named(name):
    regs = yaml.safe_load((ANNOTATIONS / "registers.yaml").read_text())["registers"]
    for r in regs:
        if str(r.get("name", "")) == name:
            return r
    raise AssertionError(f"registers.yaml has no entry named {name!r}")


class TheProvenanceComposition(unittest.TestCase):
    """Why `0xB2D5` gives `0x04A0` the `0x0526` byte and not the `0x0524` one.

    This is the case the rejected suite lacked. It reads the two helpers and
    composes them, and it asserts the negatives that make the mirror reading
    unpassable: that `0x888C` does not store `R3`/`R4`, and that the bytes
    reaching `R1`/`R2` are the second and third of the four, not the first two.
    """

    @classmethod
    def setUpClass(cls):
        cls.b6c9_text = listing("bank1", 0xB6C9)

    def test_b6c9_loads_four_bytes_into_r3_r4_r1_r2_with_three_inc_dptr(self):
        # Parsed out of the listing rather than cited: which register each of
        # the four `movx A,@DPTR` reads lands in is the whole claim, so a test
        # that asserted four addresses would pass on the wrong order.
        loaded = [ops.split(",")[0].strip()
                  for _, _, mnem, ops in rows(self.b6c9_text)
                  if mnem == "mov" and ops.split(",")[0].strip()
                  in ("R1", "R2", "R3", "R4")]
        self.assertEqual(loaded, list(B6C9_LOAD_ORDER),
                         "0xB6C9 loads four bytes into R3, R4, R1, R2 in that "
                         "order, and the order is what makes the provenance "
                         "settle; a different order would change which bytes "
                         "0x888C stores")
        # Three inc DPTR between four loads: the byte count the claim rests on.
        self.assertEqual(sum(1 for _, _, mnem, ops in rows(self.b6c9_text)
                             if mnem == "inc" and "DPTR" in ops), 3)

    def test_888c_stores_r1_then_r2_and_not_r3_or_r4(self):
        text = listing("bank1", 0x888C)
        # Each store is preceded by the `mov A,Rn` that sources it, across an
        # `inc DPTR`. Held as the (source, store) pairs so a store gaining a
        # different register fails rather than the count staying at two.
        pairs = []
        pending = None
        for _, _, mnem, ops in rows(text):
            if mnem == "mov" and ops.startswith("A, R"):
                pending = ops.split(",")[1].strip()
            elif mnem == "movx" and ops.startswith("@DPTR"):
                pairs.append(pending)
                pending = None
            else:
                pending = None
        self.assertEqual(pairs, ["R1", "R2"],
                         "0x888C stores R1 then R2; storing R3/R4 instead is "
                         "the mirror reading this case exists to fail")
        self.assertNotIn("R3", text)
        self.assertNotIn("R4", text)

    def test_0524_lands_in_r3_r4_and_therefore_not_in_the_pair_store(self):
        # The composition, stated as the address arithmetic it is. `0xB2D5`
        # hands `0xB6C9` DPTR=0x0524, so the four bytes it reads are 0x0524
        # through 0x0527 in ascending order, and the two `0x888C` stores take
        # the third and fourth.
        seed = 0x0524
        loaded = [seed + i for i in range(4)]
        stored = loaded[2:]
        self.assertEqual(loaded, [0x0524, 0x0525, 0x0526, 0x0527])
        self.assertEqual(stored, [0x0526, 0x0527])
        self.assertNotIn(seed, stored,
                         "0x0524 is in R3/R4 and 0x888C stores R1/R2, so the "
                         "byte arriving at 0x04A0 is 0x0526's, one hop "
                         "downstream -- this is the mirror claim's negation")

    def test_the_call_site_literals_alone_do_not_settle_it(self):
        # Why this suite composes instead of reading literals: the four
        # operands at the call site are identical under either provenance, so
        # asserting only them would pass on the wrong answer.
        ops = listing("bank1", 0xB2D5)
        self.assertIn("B2E5     90 05 24 mov      DPTR, #0x524", ops)
        self.assertIn("B2E8     12 b6 c9 lcall    0xb6c9", ops)
        self.assertIn("B2EB     40 06 -  jc       0xb2f3", ops)
        self.assertIn("B2ED     90 04 a0 mov      DPTR, #0x4a0", ops)
        self.assertIn("B2F0     12 88 8c lcall    0x888c", ops)
        # Same literals, both provenances: nothing here names a byte, which is
        # the whole reason `TheProvenanceComposition` exists.


class BytesAgainstTheImage(unittest.TestCase):
    """Each claim's bytes, checked against the listing and against the image."""

    # (address, hex) for the rows the write-up's transcripts quote. Each is a
    # run of consecutive instructions, so the address is where the quote
    # starts -- for `0xB2D5` that is `0xB2E5`, the pair store, not the
    # function head.
    BANK1_BYTES = {
        0xB6C9: "e0 fb a3 e0 fc a3 e0 f9 a3 e0 fa",
        0x888C: "e9 f0 a3 ea f0 22",
        0xB2E5: "90 05 24 12 b6 c9 40 06 90 04 a0 12 88 8c",
        0xB860: "90 04 90 e0 54 f9 f0 12 b8 8c 12 b9 37 79 00 7a 00 90 04 ae 12 88 8c",
        0xB900: "90 04 90 e0 54 9f f0 12 b9 1b 12 b9 62 79 00 7a 00 90 04 be 12 88 8c",
        0xBFD9: "79 00 7a 00 90 04 ae 12 88 8c 90 04 be 12 88 8c 22",
        0xC044: "90 05 7b e0 fe 90 04 72 e0 54 20 60 07 7d 08 90 05 7c e0 fe",
        0xD0C4: "90 05 24 e0 90 05 26 f0 90 04 a0 f0 e4 90 05 25 f0 90 05 27 f0 90 04 a1 f0",
    }

    def test_every_quoted_run_equals_the_listing_and_the_image(self):
        data = image_bytes()
        for addr, want in self.BANK1_BYTES.items():
            nbytes = len(want.split())
            text = listing("bank1", owner_of(addr))
            self.assertEqual(run_at(text, addr, nbytes), want,
                             f"0x{addr:04X}: the listing's own bytes moved")
            self.assertEqual(at_runtime("bank1", addr, nbytes, data).hex(" "),
                             want,
                             f"0x{addr:04X}: the image disagrees with the "
                             "listing at the runtime address")

    def test_the_quoted_runs_are_each_inside_the_routine_they_are_cited_to(self):
        # A run keyed by an address in a *different* routine would make the
        # case above agree with the image while the write-up's transcript
        # quoted a listing that does not say that, so each address is held to
        # the routine whose listing it is read from.
        for addr in self.BANK1_BYTES:
            addrs = [a for a, _, _, _ in rows(listing("bank1", owner_of(addr)))]
            self.assertIn(addr, addrs,
                          f"0x{addr:04X} is not in 0x{owner_of(addr):04X}, the "
                          "listing the table reads it from")

    def test_bank0_gate_byte_is_read_and_bit_1_branches_to_b158(self):
        data = image_bytes()
        ops = listing("bank0", 0xB12C)
        self.assertIn("B141     90 04 90 mov      DPTR, #0x490", ops)
        self.assertIn("B145     20 e1 10 jb       0xe1, 0xb158", ops)
        self.assertEqual(at_runtime("bank0", 0xB141, 7, data).hex(" "),
                         "90 04 90 e0 20 e1 10")

    def test_the_masks_beside_the_zeroing_are_0xf9_and_0x9f(self):
        # The two `ANL A,#mask` instructions the write-up's transcripts quote,
        # pinned against the image at their own addresses. Issue #732's text
        # said `0xB841` clears "bits 0, 1, 2 and 6", which is what `0xb8` would
        # clear, and the `B841` annotation row carried it -- so the mask is
        # asserted here and the bit list is derived from it in
        # `TheZeroingAndTheGate`, rather than either being taken on trust.
        data = image_bytes()
        self.assertEqual(at_runtime("bank1", 0xB864, 2, data).hex(" "), "54 f9")
        self.assertEqual(at_runtime("bank1", 0xB904, 2, data).hex(" "), "54 9f")
        self.assertIn("B864     54 f9 -  anl      A, #0xf9",
                      listing("bank1", 0xB841))
        self.assertIn("B904     54 9f -  anl      A, #0x9f",
                      listing("bank1", 0xB8E1))


class TheZeroingAndTheGate(unittest.TestCase):
    """The mask and the pair store in one run, and `0xBFD9`'s independence."""

    def test_b841_clears_0490_then_zeroes_the_04ae_word(self):
        ops = listing("bank1", 0xB841)
        self.assertIn("B864     54 f9 -  anl      A, #0xf9", ops)
        self.assertIn("B871     90 04 ae mov      DPTR, #0x4ae", ops)
        self.assertIn("B874     12 88 8c lcall    0x888c", ops)
        # 0xf9 is 0b11111001, so the mask clears bits 1 and 2 -- and bit 1 is
        # the gate `0xB12C` branches on. Held as the mask and the derived bit
        # list rather than as prose, so a note that prints the wrong bits fails
        # here: the plan and the `B841` annotation both say "bits 0, 1, 2 and
        # 6", which is what an `and`-with-`0x06` would clear, not `0xf9`.
        self.assertEqual(clears_bits(0xF9), [1, 2])
        self.assertIn(1, clears_bits(0xF9))

    def test_b8e1_clears_0490_then_zeroes_the_04be_word(self):
        ops = listing("bank1", 0xB8E1)
        self.assertIn("B904     54 9f -  anl      A, #0x9f", ops)
        self.assertIn("B911     90 04 be mov      DPTR, #0x4be", ops)
        self.assertIn("B914     12 88 8c lcall    0x888c", ops)
        self.assertEqual(clears_bits(0x9F), [5, 6])

    def test_bfd9_is_two_stores_and_a_ret_reading_no_0490(self):
        ops = listing("bank1", 0xBFD9)
        self.assertIn("BFE9     22 - -   ret", ops)
        self.assertNotIn("0x490", ops,
                         "0xBFD9 reads no 0x0490 byte, which is what makes its "
                         "zeroing independent of the two arming routines")


class TheIncrements(unittest.TestCase):
    """The two words are up-counters, so the issue's premise is false."""

    def test_bfbb_increments_04ae_and_carries_into_04af(self):
        ops = listing("bank1", 0xBFBB)
        for line in ("C01B     90 04 ae mov      DPTR, #0x4ae",
                     "C01E     e0 - -   movx     A, @DPTR",
                     "C021     24 01 -  add      A, #0x1",
                     "C025     7a 01 -  mov      R2, #0x1",
                     "C027     f0 - -   movx     @DPTR, A",
                     "C029     90 04 af mov      DPTR, #0x4af",
                     "C02D     2a - -   add      A, R2"):
            self.assertIn(line, ops)

    def test_c0a8_increments_04be_and_carries_into_04bf(self):
        ops = listing("bank1", 0xC0A8)
        for line in ("C0D9     90 04 be mov      DPTR, #0x4be",
                     "C0DC     e0 - -   movx     A, @DPTR",
                     "C0DF     24 01 -  add      A, #0x1",
                     "C0E3     7a 01 -  mov      R2, #0x1",
                     "C0E5     f0 - -   movx     @DPTR, A",
                     "C0E7     90 04 bf mov      DPTR, #0x4bf",
                     "C0EB     2a - -   add      A, R2"):
            self.assertIn(line, ops)

    def test_the_increment_is_reached_once_the_byte_in_front_reaches_0x3c(self):
        self.assertIn("BFF0     b4 3c 04 cjne     A, #0x3c, 0xbff7",
                      listing("bank1", 0xBFBB))
        self.assertIn("C0AE     b4 3c 04 cjne     A, #0x3c, 0xc0b5",
                      listing("bank1", 0xC0A8))

    def test_the_cjnes_not_equal_arm_lands_on_the_jnc_not_the_increment(self):
        """The `0x3C` is the gate, and that needs the pair read together.

        `CJNE` writes the carry itself -- set when `A` is unsigned-less than the
        immediate -- so the `JNC` that follows tests the comparison, not the
        `ADD` before it. That makes the not-equal arm land on the `JNC`, and
        both the equal arm and the `JNC`'s own arm reach the increment while
        only `A < 0x3C` returns without incrementing. Reading the two
        instructions as one `if`, or crediting the `ADD`'s carry, inverts the
        claim; the targets are pinned so that reading fails here.
        """
        for stem, cjne_at, jnc_at, zero_at, into_at, ret_at in (
                ("BFBB", 0xBFF0, 0xBFF7, 0xBFF3, 0xBFFB, 0xBFFA),
                ("C0A8", 0xC0AE, 0xC0B5, 0xC0B1, 0xC0B9, 0xC0B8)):
            ops = {addr: (mn, o) for addr, _, mn, o
                   in rows(listing("bank1", int(stem, 16)))}
            with self.subTest(routine=stem):
                self.assertEqual(ops[cjne_at], ("cjne", "A, #0x3c, 0x%x"
                                                % (cjne_at + 3 + 4)))
                # The not-equal arm is the `jnc`, so the comparison decides.
                self.assertEqual(ops[jnc_at], ("jnc", "0x%x" % zero_at))
                # ...and that arm reaches the same store the equal arm falls
                # into, which is the one the increment is entered past.
                self.assertEqual(ops[zero_at][0], "clr")
                self.assertEqual(ops[zero_at + 1], ("movx", "@DPTR, A"))
                self.assertEqual(ops[zero_at + 2][1], f"0x{into_at:x}")
                # The other arm stores and returns: no increment. The `jnc` is two bytes,
                # so the store is at `jnc_at + 2` and the `ret` after it.
                self.assertEqual(ops[jnc_at + 2], ("movx", "@DPTR, A"))
                self.assertEqual(ops[ret_at][0], "ret")

    def test_the_jnc_carries_the_cjnes_comparison_not_the_adds(self):
        """Computed from the encodings, so the semantics cannot drift.

        `CJNE` at `0xBFF0` targets `0xBFF7`, the `JNC`, not `0xBFF3`. Both
        targets of a `CJNE` landing on the increment path is what would make
        `0x3C` incidental; the displacement says otherwise, and the `JNC` is
        reached only when `A != 0x3C`, i.e. only when the comparison has just
        written the carry.
        """
        for stem, cjne_at, disp, want in (("BFBB", 0xBFF0, 0x04, 0xBFF7),
                                          ("C0A8", 0xC0AE, 0x04, 0xC0B5)):
            with self.subTest(routine=stem):
                got = relative_target(0xB4, disp, cjne_at)
                self.assertEqual(got, want,
                                 f"{stem}: CJNE's not-equal arm must land on "
                                 f"the JNC, not on the increment path")


class TheAttributionIsNotBfbb(unittest.TestCase):
    """`0x3C` as a multiplier and every `0x0494` access are `0xC032`'s bytes.

    Asserted as a negative, so making the attribution the other way -- back to
    `0xBFBB.c`, which is what the decompile reads like -- fails here.
    """

    def test_bfbb_has_no_multiplier_and_no_0494_site(self):
        ops = listing("bank1", 0xBFBB)
        self.assertNotIn("0x494", ops,
                         "0xBFBB has no 0x0494 site; the .c shows three because "
                         "its first instruction is `lcall 0xc032`")
        self.assertNotIn("mov      B, #0x3c", ops,
                         "the `* 0x3C` multiplier is 0xC032's, not 0xBFBB's")

    def test_c032_holds_both_multipliers_and_all_three_0494_accesses(self):
        ops = listing("bank1", 0xC032)
        self.assertEqual(ops.count("mov      B, #0x3c"), 2)
        for line in ("C059     75 f0 3c mov      B, #0x3c",
                     "C07E     75 f0 3c mov      B, #0x3c",
                     "C08A     90 04 94 mov      DPTR, #0x494",
                     "C090     90 04 94 mov      DPTR, #0x494",
                     "C09F     90 04 94 mov      DPTR, #0x494"):
            self.assertIn(line, ops)

    def test_bfbb_ends_before_c032_and_calls_it(self):
        # The reason the decompile reads the other way, asserted so the
        # explanation in the write-up stays true: 0xBFBB's first instruction is
        # the call, so the decompiler follows it into the callee's body.
        self.assertIn("BFBB     12 c0 32 lcall    0xc032", listing("bank1", 0xBFBB))
        self.assertEqual(max(hex_runs(listing("bank1", 0xBFBB))), 0xC031)


class FourA1IsNeverSetNonZero(unittest.TestCase):
    """The composition behind "no committed routine has been read setting it".

    Held as a composition over the three routines rather than as a citation, so
    the claim fails if any one of them gains a store.
    """

    def test_the_only_direct_store_of_04a1_has_a_cleared(self):
        ops = listing("bank1", 0xD0C4)
        self.assertIn("D0D0     e4 - -   clr      A", ops)
        self.assertIn("D0D9     90 04 a1 mov      DPTR, #0x4a1", ops)
        self.assertIn("D0DC     f0 - -   movx     @DPTR, A", ops)

    def test_0527s_only_committed_writer_stores_zero(self):
        # Searched rather than cited: no other committed decompile names
        # `DAT_EXTMEM_0527`, so the claim is held by the search.
        hits = sorted(p.name for p in (DECOMPILED / "bank1").glob("*.c")
                      if "DAT_EXTMEM_0527" in p.read_text())
        self.assertEqual(hits, ["D0C4.c"],
                         "0x0527 has exactly one committed writer; a second "
                         "one would need re-reading before this claim holds")
        ops = listing("bank1", 0xD0C4)
        self.assertIn("D0D5     90 05 27 mov      DPTR, #0x527", ops)
        self.assertIn("D0D8     f0 - -   movx     @DPTR, A", ops)

    def test_the_helper_route_delivers_0527_not_0524(self):
        # Inherited from the composition above rather than restated: the only
        # non-direct route into 0x04A1 is 0xB2D5's pair store, and
        # `TheProvenanceComposition` is what fixes which bytes it carries.
        self.assertIn("B2ED     90 04 a0 mov      DPTR, #0x4a0",
                      listing("bank1", 0xB2D5))


class TheReaderCensusIsComplete(unittest.TestCase):
    """The write-up's reader table is the whole set, not a selection.

    The set comes from the **listings**, and that is the point. A decompile
    credits a routine with whatever control flow the decompiler followed into
    it, so three committed `.c` files name `0x04A0`/`0x04A1` with no such byte
    anywhere in their own listing: `0xAD80` is a one-instruction forwarder,
    `0xB98D` and `0xD17E` each render a block belonging to a neighbour. Reading
    the census off `DAT_EXTMEM_04a*` tokens counted all three as readers of
    their own.

    The comparison is equality in **both** directions. Intersecting the
    write-up's rows with the derived set would let a spurious row pass, which
    is the one error this derivation actually makes, so a routine the listings
    do not support fails here just as a missing one does.
    """

    WRITUP = ROOT / "docs" / "findings" / "xdata-04a0-04ae-04be-words.md"

    # Decompiles that name the byte without owning it, each with the reason
    # the write-up gives for dropping it. Held here so the census cannot be
    # "fixed" by silently dropping one of them instead.
    ARTEFACTS = {
        "AD80": "one instruction, `sjmp 0xad8b`",
        "B98D": "renders `0xBA43`–`0xBAAF`, which is `BA43`'s",
        "D17E": "reaches `0xD166` in `D0C4` by `sjmp 0xd14c`",
    }

    @classmethod
    def setUpClass(cls):
        # From the listings: a routine is a reader when its own bytes carry a
        # DPTR literal for the byte. `B2D5` needs no special case here -- it
        # stores through the pair store, but it loads `0x04A0` itself first.
        cls.readers = sorted(
            p.stem for p in (DECOMPILED / "bank1").glob("*.asm")
            if re.search(r"mov\s+DPTR,\s+#0x4a[01]\b", p.read_text()))
        text = cls.WRITUP.read_text()
        # The table's own rows, not every `bank1 0x…` in the prose: the
        # artefacts are named in prose deliberately and are not rows.
        cls.named = sorted(set(re.findall(
            r"^\| `bank1 0x([0-9A-F]{4})`", text, re.M)))

    def test_the_census_is_measured_from_the_listings_not_the_decompiles(self):
        # If the write-up and the tree ever stop agreeing, the tree decides --
        # asserted here so a reader can tell which of the two is stale.
        self.assertEqual(self.readers,
                         ["AD8B", "B224", "B2A0", "B2D5", "BA43", "C11C",
                          "C778", "D0C4"])

    def test_the_table_and_the_listings_agree_in_both_directions(self):
        # Not an intersection: a row the listings do not support is the error
        # this derivation makes, and intersecting would hide exactly that.
        self.assertEqual(set(self.named), set(self.readers),
                         "the write-up's reader table and the routines whose "
                         "own listings carry the byte must be the same set")

    def test_no_artefact_is_admitted_as_a_reader_of_its_own(self):
        # Each holds no such byte, so a table listing one fails the case
        # above; held per routine so a fourth artefact fails on its own.
        for stem in self.ARTEFACTS:
            with self.subTest(artefact=stem):
                listing_text = listing("bank1", int(stem, 16))
                self.assertIsNone(
                    re.search(r"mov\s+DPTR,\s+#0x4a[01]\b", listing_text),
                    f"{stem}.asm carries a 0x04A0/0x04A1 DPTR literal, so it is "
                    f"a reader in its own right and not an artefact")

    def test_the_artefacts_are_named_in_the_writeup_with_a_reason(self):
        # Dropped with a reason rather than silently, so a reader who meets
        # one of these `.c` files knows why it is not a row.
        text = self.WRITUP.read_text()
        for stem in self.ARTEFACTS:
            with self.subTest(artefact=stem):
                self.assertIn(f"`bank1 0x{stem}`", text)

    def test_b2d5_reaches_04a0_only_through_the_pair_store(self):
        # Why its decompile carries no `DAT_EXTMEM_04a0` token while its
        # listing does carry the byte: the store is rendered as a call. Held so
        # the census cannot be "fixed" by dropping the one routine that writes
        # the byte through a helper.
        text = (DECOMPILED / "bank1" / "B2D5.c").read_text()
        self.assertNotIn("DAT_EXTMEM_04a0", text)
        self.assertIn("write_r1r2_to_xdata_pair(0x4a0)", text)
        self.assertIn("B2ED     90 04 a0 mov      DPTR, #0x4a0",
                      listing("bank1", 0xB2D5))

    def test_the_bit_tests_are_in_the_04a1_routines_that_own_the_byte(self):
        # `0x04A1`'s bit-6 and `& 0x90` tests, held against the listings that
        # carry the byte rather than against decompiles that name it.
        for stem, sites in (("BA43", ("BA5F", "BA90")),
                            ("C11C", ("C14A", "C1B2"))):
            text = listing("bank1", int(stem, 16))
            for site in sites:
                with self.subTest(routine=stem, site=site):
                    self.assertIn(f"{site}     90 04 a1 mov      DPTR, #0x4a1",
                                  text)

    def test_04a0s_bit_5_test_is_in_the_routines_that_own_the_byte(self):
        for stem, site in (("AD8B", "ADA5"), ("B224", "B234"), ("B2A0", "B2A5")):
            with self.subTest(routine=stem):
                self.assertIn(f"{site}     90 04 a0 mov      DPTR, #0x4a0",
                              listing("bank1", int(stem, 16)))
        # The bit itself: `0xe5` is bit 5 of the byte just loaded at `0xADBD`.
        ops = {addr: (mn, o) for addr, _, mn, o
               in rows(listing("bank1", 0xAD8B))}
        self.assertEqual(ops[0xADBD], ("jb", "0xe5, 0xade1"))


class TheWriterSets(unittest.TestCase):
    """`0x04A0`'s three routes, and the subset relation that sinks the mirror."""

    def test_0526s_writers_are_a_strict_subset_of_0524s(self):
        def writers(sym):
            """Routines whose own listing loads the byte's DPTR.

            From the listings, not from `DAT_EXTMEM_…=` in the decompiles, for
            the reason TheReaderCensusIsComplete gives: a decompile credits a
            routine with whatever control flow the decompiler followed into
            it. `D17E.c` writes `DAT_EXTMEM_0526` and `D17E.asm` holds no
            `0x0526` byte at all -- the store is `D0C4`'s at `0xD165` -- so
            reading tokens here would name a fourth neighbour as a writer.
            """
            # The listings print the literal as the address's digits, not
            # zero-padded to four (`#0x524`, not `#0x0524`).
            lit = sym.lstrip("0") or "0"
            pat = re.compile(rf"mov\s+DPTR,\s+#0x{lit}\b")
            return sorted(p.stem for p in (DECOMPILED / "bank1").glob("*.asm")
                          if pat.search(p.read_text()))

        w524, w526 = writers("0524"), writers("0526")
        # A listing that loads the byte is not necessarily a *writer*, so this
        # asserts the relation the argument rests on rather than a figure: the
        # ones that clear `0x0524` without touching `0x0526` are what make it
        # strict.
        self.assertTrue(set(w526) < set(w524),
                        f"0x0526's routines {w526} must be a strict subset of "
                        f"0x0524's {w524}; that is what stops 0x04A0 from "
                        "tracking 0x0524 across all three of its own routes")
        self.assertNotIn("D17E", w526,
                         "D17E.asm carries no 0x0526 byte; its decompile's "
                         "store is D0C4's")

    def test_c778_clears_04a0_in_the_same_run_as_0524_and_0526(self):
        ops = listing("bank1", 0xC778)
        self.assertIn("C788     e4 - -   clr      A", ops)
        for line in ("C78D     90 04 a0 mov      DPTR, #0x4a0",
                     "C790     f0 - -   movx     @DPTR, A",
                     "C791     90 05 24 mov      DPTR, #0x524",
                     "C794     f0 - -   movx     @DPTR, A",
                     "C795     90 05 26 mov      DPTR, #0x526",
                     "C798     f0 - -   movx     @DPTR, A"):
            self.assertIn(line, ops)

    def test_d0c4_gives_04a0_the_0524_value_and_later_the_literal_0x20(self):
        ops = listing("bank1", 0xD0C4)
        for line in ("D0C4     90 05 24 mov      DPTR, #0x524",
                     "D0C7     e0 - -   movx     A, @DPTR",
                     "D0C8     90 05 26 mov      DPTR, #0x526",
                     "D0CB     f0 - -   movx     @DPTR, A",
                     "D0CC     90 04 a0 mov      DPTR, #0x4a0",
                     "D0CF     f0 - -   movx     @DPTR, A"):
            self.assertIn(line, ops)
        # The second route: one literal into four stores.
        self.assertIn("D15C     74 20 -  mov      A, #0x20", ops)
        for line in ("D15E     90 05 24 mov      DPTR, #0x524",
                     "D162     90 05 26 mov      DPTR, #0x526",
                     "D166     90 04 a0 mov      DPTR, #0x4a0",
                     "D16A     90 04 92 mov      DPTR, #0x492"):
            self.assertIn(line, ops)


class NoteShape(unittest.TestCase):
    """Calibration made mechanical: what the four notes may and may not say."""

    # A unit word may appear only in a sentence carrying the refusal. Matched on
    # word boundaries: `ms` as a substring also lands inside "arms" and
    # "systems", which is how a note about arming a counter would trip this.

    @classmethod
    def setUpClass(cls):
        cls.notes = {name: entry_named(name) for name in NEW_ENTRIES}

    def test_every_new_entry_is_present_untested_and_cites_its_functions(self):
        for name, entry in self.notes.items():
            self.assertEqual(entry["status"], "present-untested", name)
            self.assertIn("static-scan", entry["sources"], name)
            self.assertIn("xdata-refs", entry["sources"], name)
            # The functions the note rests on, named rather than line-pinned.
            self.assertNotRegex(entry["note"], r"\.asm:\d",
                                f"{name}: cite by name and address, not "
                                "file:NNN")
            self.assertNotRegex(entry["note"], r"\.c:\d",
                                f"{name}: cite by name and address, not "
                                "file:NNN")

    def test_no_note_asserts_a_unit(self):
        # Split on sentence-final punctuation, and skip the refusal sentence by
        # content rather than by position: the two counter notes carry one
        # sentence naming the unit words in order to refuse them.
        for name, entry in self.notes.items():
            for sentence in re.split(r"(?<=[.;])\s+|\n\n", entry["note"]):
                if asserts_a_unit(sentence):
                    self.assertIn(
                        "no unit is claimed", sentence,
                        f"{name}: a unit word may appear only in the sentence "
                        f"that refuses one, not here: {sentence!r}")

    def test_the_counter_notes_say_nothing_was_observed_live(self):
        for name in ("XDATA_04AE_COUNTER_A (16-bit up-counter, gate 0x0490 bit 1)",
                     "XDATA_04BE_COUNTER_B (16-bit up-counter, gate 0x0490 bit 5)"):
            note = self.notes[name]["note"].lower()
            self.assertIn("observed live", note,
                          f"{name}: the note must say nothing was observed")
            self.assertIn("driver", note,
                          f"{name}: the note must say a register the EC arms "
                          "and zeroes is not thereby one to write")

    def test_the_04a1_note_is_not_read_not_always_zero(self):
        note = self.notes["XDATA_04A1"]["note"]
        self.assertIn("has been read setting this non-zero", note)
        # The limit of the claim has to be in the note, not only here.
        self.assertIn("not found by this method", note)
        # "is always zero" may appear only as the thing being refused. Held as
        # a per-sentence check because the refusal is what the note should say,
        # so banning the phrase outright would ban the calibration too.
        for sentence in re.split(r"(?<=[.;])\s+|\n\n", note):
            if "always zero" in sentence.lower():
                self.assertRegex(
                    sentence.lower(), r"\bnot\b",
                    f"XDATA_04A1: 'always zero' may appear only in a sentence "
                    f"that refuses it, not here: {sentence!r}")

    def test_no_note_carries_the_withdrawn_mirror_claim(self):
        # Mentioning the reading to withdraw it is required; asserting it is
        # not. So the property is per-sentence: any sentence naming the mirror
        # has to carry the withdrawal beside it.
        for name, entry in self.notes.items():
            self.assertNotIn("MIRROR_OF_0524", str(entry["name"]), name)
            for sentence in re.split(r"(?<=[.;])\s+|\n\n", entry["note"]):
                if re.search(r"mirror", sentence, re.I):
                    self.assertRegex(
                        sentence.lower(),
                        r"withdrawn|cannot distinguish|not a mirror",
                        f"{name}: a note may name the mirror reading only to "
                        f"withdraw it, and this sentence does not: "
                        f"{sentence!r}")

    def test_the_pd_split_is_recorded_rather_than_summed(self):
        # The claim this case holds is the *split*, not the totals:
        # `0x04A1`'s PD-image sites are a different program's bytes and are
        # carried in their own column rather than added to the main-EC one. A
        # figure here would be a value every firmware change moves, and
        # `check_register_counts.py` already re-derives the counts from the
        # image; what no tool re-derives is that the two columns are recorded
        # separately, so that is what is asserted.
        entry = self.notes["XDATA_04A1"]
        self.assertIn("static_refs_pd_image", entry)
        self.assertIn("static_refs_main_ec", entry)
        self.assertIn("static_refs_pd_image", entry["note"])
        self.assertRegex(entry["note"], r"separate program with its own XDATA map")
        for name, e in self.notes.items():
            self.assertNotEqual(e.get("static_refs_main_ec"),
                                e.get("static_refs_pd_image"), name)


class TheWithdrawalStaysVisible(unittest.TestCase):
    """The wrong argument is beside its correction, not edited away."""

    WRITUP = ROOT / "docs" / "findings" / "xdata-04a0-04ae-04be-words.md"

    def test_the_mirror_argument_and_its_correction_are_both_present(self):
        text = self.WRITUP.read_text()
        self.assertIn("XDATA_04A0_MIRROR_OF_0524", text,
                      "the withdrawn entry name stays visible")
        self.assertRegex(text, r"Withdrawn, \d{4}-\d{2}-\d{2} \(issue #732\)")
        self.assertIn("The argument is withdrawn", text)

    def test_the_attribution_correction_names_bfbb_and_c032(self):
        text = self.WRITUP.read_text()
        self.assertIn("`0xC032`'s, not `0xBFBB`'s", text)
        self.assertIn("lcall 0xc032", text)


if __name__ == "__main__":
    unittest.main()