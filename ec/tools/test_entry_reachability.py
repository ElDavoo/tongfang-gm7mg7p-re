#!/usr/bin/env python3
"""Unit checks for per-program transfer reachability (issue #336).

`docs/findings/bank1-c1e7-reachability.md` answers a question the forwarder
census does not: `census_forwarder_targets.py` says *which bank* a forwarder's
`imm16` is read in, and nothing in the tree said *which program's own transfers
reach the address it names*. `entry_reachability.py` is that measurement, and
this file holds it to things it cannot be graded against by the tool that made
it.

**What it grades against, and why each is a different kind of thing.**

  * **the image.** The bytes of the `jnb` run that falls into `bank1 0xC1E7`,
    and the two banks' bytes at `0xC1E7`, are read from
    `ec/firmware/GMxMGxx_11.800` and compared against constants transcribed
    here. The two banks holding *different* bytes at one address is the whole
    reason the bank argument is load-bearing, so it is pinned as byte strings
    rather than as a rule that could be reimplemented wrongly.
  * **the committed listings.** The claim that the fall-through run is covered
    by no `bank1` listing is re-derived by walking the `.asm` files, not by
    asking the tool's own coverage map, so a coverage map that stopped covering
    what it claims to cannot agree with itself.
  * **a negative control that is the defect itself.** The positive controls
    assert the scan finds the `lcall` sites the annotations already record. The
    control asserts the converse for bank 1, and it is per *program*: a tool
    that scanned the whole image once, or that resolved the bank from the
    forwarder rather than from the caller's own window, would hand bank 1
    bank 0's site and go red here. Losing the program key is the mistake this
    issue is about, so losing it has to fail the suite.

**What it deliberately does not do.** It does not re-run the scan and then grade
the tool against that same run. And it asserts no count of the tree: the
annotated-entry population moves whenever a listing lands, so a figure of it
would be a value every merge had to edit. What is asserted instead is the
property -- the addresses, the banks, the bytes, and the corrections staying
where they landed.

**And the correction is checked where it landed.** `docs/findings.md` §4a wants
the withdrawn reading visible beside its replacement, so both are asserted
present in the row that carries them.
"""
import csv
import glob
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir, os.pardir))
sys.path.insert(0, HERE)

import entry_reachability as reach  # noqa: E402
from audit_call_targets import region_bounds, relative_sites  # noqa: E402
from build_ec_decompile import FIRMWARE, file_offset  # noqa: E402
from disasm8051 import OPCODE_LEN  # noqa: E402

FUNCTIONS_CSV = os.path.join(ROOT, "ec", "annotations", "ghidra-functions.csv")
VARIABLES_CSV = os.path.join(ROOT, "ec", "annotations", "ghidra-variables.csv")
ANNOTATIONS = os.path.join(ROOT, "ec", "annotations")
WRITEUP = os.path.join(ROOT, "docs", "findings",
                       "bank1-c1e7-reachability.md")
BANK1_LISTINGS = os.path.join(ROOT, "ec", "decompiled", "bank1")

with open(FIRMWARE, "rb") as _handle:
    IMAGE = _handle.read()


def annotation_row(path, scope, addr):
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["scope"] == scope and int(row["addr"], 16) == addr:
                return row
    raise AssertionError("no %s row at 0x%04X in %s"
                         % (scope, addr, os.path.basename(path)))


def bytes_at(program, addr, length):
    off = file_offset(program, addr)
    return IMAGE[off:off + length]


def resolve_jnb(image, at):
    """Where the 3-byte `jnb` at `at` goes, from the image's own bytes.

    Read here rather than transcribed so the assertion is about the firmware
    and not about a constant this file happens to hold: the displacement is
    the instruction's *last* byte, and reading the second of a 3-byte form
    instead lands somewhere else without complaint.
    """
    displacement = image[file_offset("bank1", at + 2)]
    return at + 3 + displacement


def listing_starts(program):
    """Every instruction start the committed `.asm` files of `program` carry."""
    starts = set()
    for path in glob.glob(os.path.join(ROOT, "ec", "decompiled", program,
                                       "*.asm")):
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                head = line.split()
                if head and len(head[0]) == 4:
                    try:
                        starts.add(int(head[0], 16))
                    except ValueError:
                        pass
    return starts


def read_writeup():
    with open(WRITEUP, encoding="utf-8") as handle:
        return handle.read()


def squeezed(text):
    """`text` with its runs of whitespace collapsed, for phrase assertions."""
    return " ".join(text.split())


class TheBytes(unittest.TestCase):
    """The image, pinned as byte strings rather than as a re-derivation."""

    def test_the_two_banks_hold_different_code_at_0xc1e7(self):
        # The bank argument is load-bearing only because this holds. If both
        # banks held the same bytes, a reading in either would be equally right
        # and the correction would have nothing to correct.
        self.assertEqual(bytes_at("bank0", 0xC1E7, 13),
                         bytes.fromhex("90 16 64 e0 30 e0 03 7f 01 22 7f 00 22"))
        self.assertEqual(bytes_at("bank1", 0xC1E7, 7),
                         bytes.fromhex("90 04 95 e0 54 c4 60"))

    def test_bank0s_0xc1e7_is_the_reader_that_writes_r7(self):
        # `mov R7,#0x01` / `mov R7,#0x00` at 0xC1EE and 0xC1F1. This is the
        # routine the bank-0 reading names, and the two R7 immediates are the
        # whole of what makes it one -- so they are asserted as bytes and not as
        # a decoded mnemonic.
        window = bytes_at("bank0", 0xC1E7, 13)
        self.assertIn(b"\x7f\x01", window)
        self.assertIn(b"\x7f\x00", window)

    def test_the_fallthrough_run_into_bank1_0xc1e7(self):
        # Three `jnb bit,rel` (0x30) at 0xC1DE, 0xC1E1 and 0xC1E4, whose last one
        # runs off its end into the entry. Asserted from the image rather than
        # from the tool's walk, so a walk that stopped decoding would fail here
        # rather than quietly agreeing with itself.
        self.assertEqual(bytes_at("bank1", 0xC1DA, 13),
                         bytes.fromhex("90 04 90 e0 30 e4 4e 30 e6 4b 30 e2 55"))
        self.assertEqual([bytes_at("bank1", a, 1)[0] for a in (0xC1DE, 0xC1E1, 0xC1E4)],
                         [0x30, 0x30, 0x30])

    def test_the_run_branches_out_of_the_band_and_falls_into_the_entry(self):
        # What makes the last `jnb` a fall-through rather than a jump into the
        # entry: all three branches leave 0xC1E7-0xC21A, so the next
        # instruction after the last one *is* the entry. The property is what
        # is asserted here, not the addresses -- the displacements are read
        # off the image and resolved, so a listing that changed, or a resolver
        # that stopped decoding 3-byte `jnb`, moves the result and fails.
        band = range(0xC1E7, 0xC21A)
        targets = [resolve_jnb(IMAGE, a) for a in (0xC1DE, 0xC1E1, 0xC1E4)]
        for at, target in zip((0xC1DE, 0xC1E1, 0xC1E4), targets):
            self.assertNotIn(target, band,
                             "0x%04X branches to 0x%04X, inside the entry's own "
                             "band, so the run does not fall into it" % (at, target))
        # And the load-bearing negative: the entry is not a branch target at
        # all, which is what makes the way in a fall-through.
        self.assertNotIn(0xC1E7, targets)
        # The last instruction runs off its end exactly onto the entry -- the
        # displacement plays no part in that, only the instruction's own
        # length, which the opcode table supplies rather than this file.
        # Should the run end anywhere else, the way in is not this one.
        self.assertEqual(0xC1E4 + OPCODE_LEN[IMAGE[file_offset("bank1", 0xC1E4)]],
                         0xC1E7)

    def test_the_branch_targets_agree_with_the_repo_resolver(self):
        # The targets above are computed from the displacement bytes here, so
        # they are only the write-up's claim if the repository's own
        # `relative_sites()` resolves the same three instructions the same
        # way. Cross-checked rather than assumed: its offsets are file offsets,
        # and reading the displacement of a 3-byte form as its second byte
        # lands somewhere else silently.
        resolved = {o: t for o, _op, t in relative_sites(
            IMAGE, *region_bounds("bank1"))}
        for at in (0xC1DE, 0xC1E1, 0xC1E4):
            self.assertEqual(resolved.get(file_offset("bank1", at)),
                             resolve_jnb(IMAGE, at),
                             "relative_sites() and the image displacement "
                             "disagree at 0x%04X" % at)

    def test_the_writeup_reads_jnb_the_way_jnb_reads(self):
        # `jnb` jumps when the bit is *clear*, so control reaches the entry when
        # all three bits are set. The opposite sentence is the natural mistake
        # and reads correctly at a glance, so it is held here explicitly: the
        # write-up has to say "set", and must not have the inverted claim
        # anywhere in it.
        text = squeezed(read_writeup())
        self.assertIn("all three bits are **set**", text)
        self.assertNotIn("none of three bits", text)

    def test_bank0s_0xc201_and_0xc209_are_standalone_entries(self):
        # The correction's second half: in bank 0 these are eight-byte
        # read-modify-writes on 0x1604, not addresses inside a larger body.
        self.assertEqual(bytes_at("bank0", 0xC201, 8),
                         bytes.fromhex("90 16 04 e0 44 02 f0 22"))
        self.assertEqual(bytes_at("bank0", 0xC209, 8),
                         bytes.fromhex("90 16 04 e0 54 fd f0 22"))


class ThePerProgramKey(unittest.TestCase):
    """The defect itself: which program a transfer is read in."""

    def test_bank1_names_0xc1e7_nowhere_and_bank0_names_it_once(self):
        bank0 = reach.sites_naming(IMAGE, "bank0", 0xC1E7)
        bank1 = reach.sites_naming(IMAGE, "bank1", 0xC1E7)
        self.assertEqual([a for _f, a in bank0], [0xD9E7])
        self.assertEqual(bank1, [])

    def test_a_tool_that_ignored_the_program_would_be_caught(self):
        # The mutation this suite exists to catch: pool every program's sites
        # and answer the same for each. `bank1,0xC1E7` would then inherit bank
        # 0's call site, so the assertion above would fail. Held as a property
        # rather than as a comment, because a suite that only says so in prose
        # stops saying so the moment the code is edited.
        pooled = []
        for program in reach.AUDITED:
            pooled.extend(reach.sites_naming(IMAGE, program, 0xC1E7))
        self.assertTrue(pooled)
        self.assertEqual(reach.sites_naming(IMAGE, "bank1", 0xC1E7), [])
        self.assertNotEqual(pooled, reach.sites_naming(IMAGE, "bank1", 0xC1E7))

    def test_the_common_area_is_a_separate_answer(self):
        # Below 0x8000 the three programs share bytes, so a target there has to
        # be asked of the common window rather than inferred from either bank.
        self.assertEqual(reach.sites_naming(IMAGE, "common", 0xC1E7), [])

    def test_the_positive_control_the_zero_depends_on(self):
        # A scan that found nothing anywhere would satisfy every assertion
        # above. These are the call sites the annotations already record, so a
        # zero elsewhere is about the address rather than about the scan.
        self.assertEqual([a for _f, a in reach.sites_naming(IMAGE, "bank0", 0xC0E7)],
                         [0xC118, 0xCBB5])


class TheFallThrough(unittest.TestCase):
    """A way in that is not a call, reported as its own thing."""

    def test_bank1_0xc1e7_is_reached_only_by_fallthrough(self):
        found = reach.fallthrough_in(IMAGE, "bank1", 0xC1E7)
        self.assertIsNotNone(found)
        self.assertEqual(found[1], 0xC1E7)

    def test_the_walk_reads_the_window_it_was_asked_about(self):
        # `file_offset('bank1', ...)` is not bank 0's offset shifted: reading
        # bank 1 through bank 0's window decodes a different instruction and
        # this would find no fall-through at all.
        self.assertNotEqual(bytes_at("bank1", 0xC1E4, 3),
                            bytes_at("bank0", 0xC1E4, 3))

    def test_common_never_claims_a_bank_address(self):
        # The common program holds 0x0000-0x7FFF and nothing above it, so a
        # fall-through reported for `common` at a bank address would be bank 0's
        # instruction wearing the common area's name.
        self.assertIsNone(reach.fallthrough_in(IMAGE, "common", 0xC1E7))

    def test_no_fallthrough_is_reported_where_there_is_none(self):
        self.assertIsNone(reach.fallthrough_in(IMAGE, "bank1", 0xCC64))


class TheCoverageClaim(unittest.TestCase):
    """The run that falls into the entry is covered by no committed listing."""

    def test_no_bank1_listing_covers_the_run(self):
        starts = listing_starts("bank1")
        uncovered = [a for a in range(0xC1DA, 0xC1E7) if a not in starts]
        self.assertEqual(uncovered, list(range(0xC1DA, 0xC1E7)))
        self.assertIn(0xC1E7, starts)

    def test_the_entry_next_to_the_run_is_exported(self):
        # So the gap is a gap in the listing rather than an absence of code:
        # the entry the run falls into is there, and only the run is not.
        self.assertIn("latch_0498_bit1_or_bit3",
                      annotation_row(FUNCTIONS_CSV, "bank1", 0xC1E7)["name"])


class TheCorrection(unittest.TestCase):
    """§4a: the withdrawn reading stays visible beside its replacement."""

    def test_the_c1e7_row_quotes_what_it_corrects(self):
        row = annotation_row(FUNCTIONS_CSV, "bank1", 0xC1E7)
        self.assertIn("no instruction in the body writes R7", row["comment"])
        self.assertIn("Two further BL51 forwarders land inside the body",
                      row["comment"])
        self.assertIn("CORRECTION", row["comment"])

    def test_the_c1e7_row_carries_the_bank0_readings(self):
        row = annotation_row(FUNCTIONS_CSV, "bank1", 0xC1E7)
        for name in ("test_1664_bit0", "set_1604_bit1", "clear_1604_bit1"):
            self.assertIn(name, row["comment"])

    def test_the_c1e7_row_cites_the_listings_it_now_reasons_from(self):
        row = annotation_row(FUNCTIONS_CSV, "bank1", 0xC1E7)
        for name in ("ec/decompiled/bank0/C1E7.asm",
                     "ec/decompiled/bank0/C201.asm",
                     "ec/decompiled/bank0/C209.asm"):
            self.assertIn(name, row["evidence"])
            self.assertTrue(os.path.isfile(os.path.join(ROOT, name)),
                            "%s is cited but not in the tree" % name)

    def test_the_row_states_its_own_limit(self):
        # Reachability is not liveness, and the row that now rests on a
        # reachability claim has to say so where a reader meets the claim.
        row = annotation_row(FUNCTIONS_CSV, "bank1", 0xC1E7)
        self.assertIn("not about whether the code runs", row["comment"])
        self.assertIn("observed on hardware", row["comment"])

    def test_the_row_does_not_upgrade_a_zero_into_unreachability(self):
        # CLAUDE.md's rule, held where the zero is written down: a static scan
        # that finds no reference means "not found by this method". The row has
        # to say so and to name what the scan does not cover. The disclaimer
        # words themselves are not the test -- the row has to be able to say
        # "unreachable" to deny it -- so this asserts the denial is present and
        # attached, not that the word is absent.
        row = annotation_row(FUNCTIONS_CSV, "bank1", 0xC1E7)
        self.assertIn("not found by this method rather than unreachable",
                      row["comment"])
        self.assertIn("indirect transfer", row["comment"])
        self.assertIn("not about whether the code runs", row["comment"])
        for word in ("dead code", "never called", "is unreachable"):
            self.assertNotIn(word, row["comment"].lower())

    def test_the_variables_row_it_cites_agrees(self):
        # The correction rests on bank 0's 0xC1E7 writing R7, and
        # `ghidra-variables.csv` already records that. Asserted so the two
        # cannot drift: one citing the other is only worth anything while both
        # are right.
        row = annotation_row(VARIABLES_CSV, "bank1", 0xA389)
        self.assertIn("test_1664_bit0", row["comment"])


class TheCalibration(unittest.TestCase):
    """The rule CLAUDE.md puts above every other."""

    def test_the_tool_reads_the_image_and_no_annotation_file(self):
        # What decides whether a `status:` in registers.yaml could move on any
        # of this is which files the tool opens, so the assertion is over the
        # module's *own* path constants, read out of the module rather than
        # listed here. The previous version tested three names this suite
        # happened to know about: a fourth path constant, or a new input
        # opened inline, went unseen while the test stayed green -- which is
        # the shape of check this file exists to distrust. A constant that is
        # not a path (a family table, an opcode table) is not this file's
        # business and is skipped.
        paths = {v for k, v in vars(reach).items()
                 if isinstance(v, str) and k.isupper()}
        self.assertTrue(paths, "no path constants found in the module at all, "
                               "so this would pass without testing anything")
        for path in sorted(paths):
            self.assertTrue(os.path.isabs(path),
                            "%s is named as a path constant but is not one"
                            % path)
            self.assertFalse(
                os.path.realpath(path).startswith(
                    os.path.realpath(ANNOTATIONS) + os.sep),
                "%s is under ec/annotations/, and the tool's inputs are the "
                "firmware image alone" % path)

    def test_the_tool_opens_only_the_image_over_a_whole_run(self):
        # The same claim against the reads themselves rather than the names:
        # `open` is watched while the tool does its work and every path it
        # reaches for is recorded. A new input anywhere in the call graph puts
        # a second path in that list and fails here.
        opened = []
        real_open = reach.builtins.open

        def watch(path, *a, **kw):
            if isinstance(path, (str, bytes, os.PathLike)):
                opened.append(os.path.realpath(os.fsdecode(path)))
            return real_open(path, *a, **kw)

        reach.builtins.open = watch
        try:
            data = reach.read_image()
            reach.report(data, [0xC1E7])
        finally:
            reach.builtins.open = real_open
        self.assertEqual(opened, [os.path.realpath(FIRMWARE)])

    def test_the_writeup_leads_with_the_bank_argument(self):
        self.assertIn("0xC1E7", squeezed(read_writeup()))
        self.assertIn("bank1", squeezed(read_writeup()))

    def test_the_writeup_states_the_limit_and_claims_no_behaviour(self):
        text = squeezed(read_writeup())
        for phrase in ("not reached by this method", "observed on hardware",
                       "entry_reachability.py"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()