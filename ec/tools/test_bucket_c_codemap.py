#!/usr/bin/env python3
"""Offline checks for bucket_c_codemap.py: no hardware, no capture, no Ghidra,
and for the parts that would need a live read nothing but the committed
firmware.

The tool's own `--self-test` holds the refusals that need the image.
`--check` is the reproducibility half and is driven from here too, in both
directions, because a `--check` that has quietly stopped failing looks exactly
like a `--check` that is working. What is here and not there is everything a
fixture can answer: one hand-built byte fixture per terminator class, the
closed vocabulary over `disasm8051.FLOW_OPCODES`, and the two invariants that
hold *because* the classification is a separate file.

**The terminator fixtures are built, not read out of the image.** The same
arrangement `test_walk_branch_arms.py` states at its own head: a fixture
anchored at an address in the committed image keeps testing what it was
written to test only until the bytes there change, and these are about the
*rules*, not about this dump. Every case therefore lays its own bytes down in
a `common`-region buffer, and the `common` region is walked in a buffer whose
file offset equals its runtime address -- so a 0x40-byte fixture is its own
address space and the addresses in a case are the offsets in the fixture.

Each terminator case asserts the reason that fired **and** the reasons that
did not. A walk that swapped the `ret` guard for the `reti` guard, or reported
`mid-instruction` where `ret` is the truth, passes a positive-only assertion and
fails one that names its neighbours. That is the whole reason the negative half
is written out rather than implied by the positive half passing.

**The oracle is transcribed into this docstring, not read from the tool.**
From `ec/annotations/bank-call-audit.md` §5, as that file states them:

    * 140 bucket-C sites, upper bound, and 83 of them anchored;
    * 102 distinct targets across those sites;
    * exactly 1 of those 102 is also an address some BL51 trampoline names.

Those four figures were written down by an enumeration this tool does not
perform and must not be able to grade itself against. A tool that computed its
own expectation would pass whenever its arithmetic drifted with the thing it
measures; these are literals, and a change to the census that moved any of
them is a change `audit_call_targets.py` has to explain in its own write-up
first. The same arrangement `test_data_regions.py` describes.

**What is deliberately not here.** No case asserts that a site *means*
anything. `reached-by-walk` is a statement about where a byte falls relative to
an instruction boundary one particular walk decoded, and nothing in this suite
says any byte is or is not a call -- the module docstring's §4c sentence is the
statement of that, and the tool's own report carries it before any verdict.
`bank-call-targets.csv` and `registers.yaml` are asserted to be *untouched*,
which is a fact about two files rather than a reading of the firmware.
"""
import contextlib
import csv
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
# bucket_c_codemap imports disasm8051 and trace_xdata_refs by bare module name,
# the way register_ref_table.py does, so the tool directory has to be on the
# path before it is loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'bucket_c_codemap', HERE / 'bucket_c_codemap.py')
bcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bcc)

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')
COMMITTED_CSV = HERE.parent / 'annotations' / 'bucket-c-codemap.csv'
TOOL = str(HERE / 'bucket_c_codemap.py')

# The oracle, transcribed from ec/annotations/bank-call-audit.md 5. See the
# module docstring for why these are literals and not something read back.
ORACLE_SITES = 140
ORACLE_ANCHORED = 83
ORACLE_TARGETS = 102
ORACLE_TRAMPOLINE_NAMED = 1

# The descent bounds the fixtures run at, named so a case can move one without
# repeating the other. The budget is deliberately larger than any fixture needs
# except the one about the budget, which passes its own.
DEPTH = 8
INSNS = 64


def fixture(*insns, size=0x40, at=0):
    """A flat `common`-region buffer with `insns` laid down from offset `at`."""
    img = bytearray(b"\x00" * size)
    for insn in insns:
        img[at:at + len(insn)] = insn
        at += len(insn)
    return bytes(img)


def codemap(img, seeds, erased=frozenset(), budget=INSNS):
    """A Codemap over a hand-built buffer, built the way build() builds one.

    The image argument is the buffer itself, and the seeds are given rather
    than discovered -- a fixture has no vector table, no trampoline block and no
    census behind it, and a case that wanted those would be a case about the
    image rather than about the rule.
    """
    reached, descents = bcc.walk(img, list(seeds), max_insns=budget,
                                 max_depth=DEPTH)
    covered = bcc.covered_index(img, descents)
    return bcc.Codemap(img, reached, descents, covered, set(erased))


# The byte encodings the fixtures below are written in, as mnemonic -> bytes.
# Written out rather than built from disasm8051 so a change to that module's
# table cannot quietly make a fixture encode into something else and keep
# passing -- which is the same reason walk_branch_arms.SELF_TEST_SITES is
# literal bytes rather than mnemonic strings.
RET = bytes([0x22])
RETI = bytes([0x32])
NOP = bytes([0x00])
LJMP = bytes([0x02, 0x00, 0x20])        # ljmp 0x0020
SJMP = bytes([0x80, 0x10])              # sjmp +16
AJMP = bytes([0x01, 0x20])              # ajmp, page-relative
JMP_ADPTR = bytes([0x73])               # jmp @a+dptr
MOV_DPTR = bytes([0x90, 0x00, 0x45])    # mov dptr,#0x0045
JNZ = bytes([0x70, 0x20])               # jnz +32
MOV_R7_A = bytes([0xFF])                # mov r7,a -- also the erased-flash byte


class TerminatorReasonTests(unittest.TestCase):
    """One fixture per terminator class, each naming the reasons it is not.

    Every case below asks `Codemap.reason_for()` for a site the fixture places
    just past a terminator, and asserts the reason that fired and the three or
    four reasons a swapped guard would produce instead. Without the negative
    half, a classifier that answered `ret` to everything would pass the first
    case, the third and the fifth.
    """

    def assert_reason(self, img, seeds, site, want, not_want, erased=()):
        got, _ = codemap(img, seeds, erased).reason_for(site)
        self.assertEqual(got, want, f"0x{site:04X} in this fixture")
        for other in not_want:
            self.assertNotEqual(
                got, other,
                f"0x{site:04X} reported {got!r}, which is the answer the "
                f"{other!r} guard produces -- the guards are interchangeable "
                f"if this passes")

    def test_a_ret_ends_the_function(self):
        img = fixture(RET, at=0x00)
        self.assert_reason(img, [(0x00, "test")], 0x01, "ret",
                           ("reti", "tail-jump", "mid-instruction",
                            "instruction-budget"))

    def test_a_reti_is_not_a_ret(self):
        # The pair matters: 0x22 and 0x32 are both one-byte and both end an
        # arm, so a decoder that keyed on "ends the block" rather than on the
        # opcode would give these the same answer and pass either alone.
        img = fixture(RETI, at=0x00)
        self.assert_reason(img, [(0x00, "test")], 0x01, "reti",
                           ("ret", "tail-jump", "mid-instruction"))

    def test_a_tail_jump_hands_the_block_over(self):
        img = fixture(LJMP, at=0x00)
        # 0x01 and 0x02 are the ljmp's operand bytes, so the walk decoded over
        # them; 0x03 is the first byte the walk did not touch.
        self.assert_reason(img, [(0x00, "test")], 0x03, "tail-jump",
                           ("ret", "mid-instruction", "reached"))

    def test_an_sjmp_is_a_tail_jump_and_not_a_branch_arm(self):
        # `sjmp` is a transfer rather than a split, so the walk does not follow
        # a fall-through -- the two bytes past it are as unvisited as they would
        # be after an `ljmp`, and reporting them as a gap would be the bug
        # `walk_branch_arms.REL_BRANCHES` was written to avoid.
        img = fixture(SJMP, at=0x00)
        self.assert_reason(img, [(0x00, "test")], 0x02, "tail-jump",
                           ("ret", "mid-instruction", "reached"))

    def test_an_ajmp_is_a_tail_jump_too(self):
        img = fixture(AJMP, at=0x00)
        self.assert_reason(img, [(0x00, "test")], 0x02, "tail-jump",
                           ("ret", "mid-instruction", "reached"))

    def test_a_computed_jump_is_unknown_and_not_a_negative(self):
        # `jmp @a+dptr` is the reason the `unknown` verdict exists. No byte scan
        # and no forward walk can follow it, so a site past it is a question
        # this method could not answer -- and saying `not-reached` would claim
        # the opposite.
        img = fixture(JMP_ADPTR, at=0x00)
        cm = codemap(img, [(0x00, "test")])
        reason, _ = cm.reason_for(0x01)
        self.assertEqual(reason, "indirect-jump")
        self.assertEqual(bcc.verdict_for(reason), bcc.UNKNOWN)

    def test_a_site_inside_a_decoded_operand_is_mid_instruction(self):
        # The strongest negative this tool has, and the one the census's
        # over-count actually needs: the `0x12`/`0x02` the byte scan found is an
        # operand byte of a `mov dptr,#imm16`, not the first byte of an
        # instruction.
        img = fixture(MOV_DPTR, at=0x00)
        for site in (0x01, 0x02):
            self.assert_reason(img, [(0x00, "test")], site, "mid-instruction",
                               ("reached", "ret", "tail-jump"))
        # And the opcode byte itself is reached, so the two are told apart.
        self.assert_reason(img, [(0x00, "test")], 0x00, "reached",
                           ("mid-instruction", "ret"))

    def test_a_conditional_branch_decodes_both_arms(self):
        # The fall-through of a PC-relative branch is decoded in the same block,
        # so a site inside it is reached rather than being reported as a gap the
        # walk failed to close. This is the case the (removed) `gap-after-block`
        # reason would have been about, and it is why that reason is not in the
        # vocabulary: the nearest decoded instruction below a gap is never a
        # branch.
        img = fixture(JNZ, at=0x00)
        self.assert_reason(img, [(0x00, "test")], 0x02, "reached",
                           ("mid-instruction", "ret", "tail-jump"))

    def test_the_budget_is_reported_as_a_budget_and_not_as_an_image_end(self):
        # A run of one-byte `nop`s with a budget too small to finish it. The
        # reason has to be the budget, because "ran out of instructions" and
        # "ran out of image" are different claims about the same routine
        # (docs/findings/count-bounded-walk-invariant.md), and the site past the
        # cut is `unknown` rather than a negative.
        img = fixture(NOP, size=0x40, at=0x00)
        reached, descents = bcc.walk(img, [(0x00, "test")], max_insns=4,
                                     max_depth=DEPTH)
        cm = bcc.Codemap(img, reached, descents,
                         bcc.covered_index(img, descents), frozenset())
        reason, _ = cm.reason_for(0x20)
        self.assertEqual(reason, "instruction-budget")
        self.assertEqual(bcc.verdict_for(reason), bcc.UNKNOWN)

    def test_the_end_of_the_buffer_is_reported_as_the_end_of_the_buffer(self):
        # 0x3F is the last byte of a 0x40 buffer, so the `nop` there decodes and
        # the walk lands exactly on len(d). The byte after it does not exist.
        # The budget has to be larger than the buffer holds, or it fires first --
        # `descend()` checks the budget before the index -- and that ordering is
        # the whole reason the two claims are separate rows.
        img = fixture(NOP, size=0x40, at=0x00)
        cm = codemap(img, [(0x00, "test")], budget=0x100)
        reason, _ = cm.reason_for(0x40)
        self.assertEqual(reason, "end-of-image")
        self.assertEqual(bcc.verdict_for(reason), bcc.UNKNOWN)
        # And the same fixture under a budget of one instruction is a budget
        # stop, not an image end.
        tight = codemap(img, [(0x00, "test")], budget=1)
        self.assertEqual(tight.reason_for(0x40)[0], "instruction-budget")

    def test_a_site_below_every_seed_has_no_seed_nearby(self):
        # Walked from 0x10, so 0x04 has nothing below it. This is the one
        # reason that is a fact about the seed set rather than about the bytes,
        # which is why it is its own cell and not a variant of `ret`.
        img = fixture(RET, at=0x10)
        self.assert_reason(img, [(0x10, "test")], 0x04, "no-seed-nearby",
                           ("ret", "reached", "mid-instruction"))

    def test_an_erased_run_is_labelled_and_the_site_is_still_classified(self):
        # A run of 0xFF with a `ret` at 0x20 to end it. `0xFF` is `mov r7,a`,
        # one byte, so the walk decodes straight through the run and would
        # answer `reached` for every byte of it -- which is the reason the
        # erased label is checked before the walk's own verdict.
        #
        # Two assertions, and the second is the one that matters: a label that
        # overrode the walk would be a filter, and `data_regions.py` refuses
        # filtering rather than suppressing a labelled site for that reason.
        img = fixture(MOV_R7_A * 0x20, RET, size=0x40)
        erased = set(range(0x00, 0x30))
        # Past the `ret`, inside the run: erased.
        self.assert_reason(img, [(0x00, "test")], 0x24, "erased-run",
                           ("reached", "ret", "mid-instruction"),
                           erased=erased)
        # Inside the run, and decoded: the walk's own answer stands.
        reason, _ = codemap(img, [(0x00, "test")], erased).reason_for(0x08)
        self.assertEqual(reason, "reached")


class VocabularyTests(unittest.TestCase):
    """The terminator vocabulary is closed, over `disasm8051.FLOW_OPCODES`.

    Closed over that table rather than over a range written here, because the
    range is the mistake `walk_branch_arms.REL_BRANCHES` documents: the 8051
    puts `clr c`/`setb c` inside `0xB4`-`0xDF`, and reading that span as "the
    PC-relative branches" resolves a target out of the following byte.
    """

    def test_every_flow_opcode_is_dispositioned_into_a_known_shape(self):
        seen = {bcc.flow_disposition(op) for op in bcc.FLOW_OPCODES}
        self.assertEqual(seen - set(bcc.DISPOSITIONS), set(),
                         f"unrecognised dispositions: {seen - set(bcc.DISPOSITIONS)}")
        self.assertEqual(len(bcc.FLOW_OPCODES), 50)

    def test_the_three_dispositions_account_for_every_opcode(self):
        counts = {d: 0 for d in bcc.DISPOSITIONS}
        for op in bcc.FLOW_OPCODES:
            counts[bcc.flow_disposition(op)] += 1
        self.assertEqual(counts["call"], 9)
        self.assertEqual(counts["follow"], 28)
        self.assertEqual(sum(counts.values()), len(bcc.FLOW_OPCODES))

    def test_a_non_flow_opcode_is_refused(self):
        for op in (0x00, 0x90, 0xE0, 0xFF):
            with self.assertRaises(SystemExit):
                bcc.flow_disposition(op)

    def test_every_reason_maps_to_one_of_the_three_verdicts(self):
        for reason in bcc.WALK_REASONS:
            self.assertIn(bcc.verdict_for(reason), bcc.VERDICTS)

    def test_a_fourth_verdict_is_refused_rather_than_rendered(self):
        for reason in ("probably-code", "", "reached ", "Reached", "not-reached",
                       "REACHED", None, 0):
            with self.assertRaises(SystemExit):
                bcc.verdict_for(reason)

    def test_only_the_reached_reason_makes_a_site_reached(self):
        reached = [r for r in bcc.WALK_REASONS
                   if bcc.verdict_for(r) == bcc.REACHED]
        self.assertEqual(reached, ["reached"])

    def test_every_unknown_reason_is_a_reason_the_walk_could_not_see_past(self):
        # A `ret`, a tail jump and a loop are all the walk *deciding*; the
        # unknown set is exactly the five-plus it could not see past. Keeping
        # the two apart is what makes `not-reached` a negative worth stating.
        for reason in ("ret", "reti", "tail-jump", "loop", "no-control-flow",
                       "mid-instruction", "no-seed-nearby", "erased-run"):
            self.assertNotIn(reason, bcc.UNKNOWN_REASONS)
        self.assertTrue(bcc.UNKNOWN_REASONS <= bcc.WALK_REASONS)


class CutParsingTests(unittest.TestCase):
    """`descend()` formats an address into a cut's end string; read it back.

    The parse is the quiet one. A cut that is not recognised does not crash and
    does not look wrong: it becomes an unclassified end, the site becomes
    `unknown`, and the count in the report moves by a few. So it is pinned on
    the exact strings `descend()` builds, and on the near misses that a looser
    split would accept.
    """

    def test_the_three_cuts_carry_their_address(self):
        self.assertEqual(bcc.split_cut("instruction budget at 0x1A2B"),
                         ("instruction budget", 0x1A2B))
        self.assertEqual(bcc.split_cut("depth limit at 0x0000"),
                         ("depth limit", 0x0000))
        self.assertEqual(
            bcc.split_cut("index past the end of the image at 0x7FFF"),
            ("index past the end of the image", 0x7FFF))

    def test_a_plain_terminator_carries_no_address(self):
        for end in ("ret", "reti", "tail jump to a callee",
                    "indirect jump -- target not resolvable from the bytes",
                    "loop back to 0x1A2B"):
            self.assertEqual(bcc.split_cut(end), (end, None))

    def test_a_cut_whose_address_is_not_four_hex_digits_is_not_a_cut(self):
        # `descend()` always formats four, so anything else is a string this
        # tool has not seen and must not read an address out of.
        for end in ("instruction budget at 0x1A2", "instruction budget at 0x1A2BC",
                    "instruction budget at 0xZZZZ", "instruction budget at "):
            self.assertEqual(bcc.split_cut(end), (end, None))

    def test_an_end_with_an_address_that_is_not_a_cut_is_left_alone(self):
        # The loop ends contain an address too, and they are terminators rather
        # than cuts. Reading one as a cut would report `loop` as a place the
        # walk gave up, which is the opposite of what `walk_branch_arms.CUTS`
        # says about it.
        head, addr = bcc.split_cut("loop back to 0x0042")
        self.assertEqual(head, "loop back to 0x0042")
        self.assertIsNone(addr)


class UnclassifiedEndTests(unittest.TestCase):
    """An end this tool does not recognise is its own cell, and it is zero here.

    `descend()` records notes as well as terminators -- "DPTR built at run time
    (a store to DPL/DPH)" is one, and the walk continues past it -- so a
    classifier that folded every end string into a real terminator would report
    a store through DPTR as the reason a function ended. The cell keeps those
    visible, and pinning it at zero says this image has no end string this tool
    has not accounted for.
    """

    def test_a_note_is_unclassified_rather_than_a_terminator(self):
        note = "DPTR built at run time (a store to DPL/DPH)"
        self.assertEqual(bcc.token_for_ends([note]), [(None, bcc.UNCLASSIFIED)])
        self.assertEqual(bcc.verdict_for(bcc.UNCLASSIFIED), bcc.UNKNOWN)

    def test_the_terminal_is_the_last_terminator_not_the_last_string(self):
        # The order `descend()` records them in: a store through DPTR partway
        # through a block, then the `ret` that ends it. The answer is `ret`.
        self.assertEqual(
            bcc.terminal_token(["DPTR built at run time (a store to DPL/DPH)",
                                "ret"]), "ret")
        # And with only a note there is no terminator to name.
        self.assertEqual(
            bcc.terminal_token(["DPTR built at run time (a store to DPL/DPH)"]),
            bcc.UNCLASSIFIED)


class OracleTests(unittest.TestCase):
    """The four figures bank-call-audit.md 5 states, against the live image.

    The literals are in the module docstring. These are the cases that stop the
    tool agreeing with a census that has drifted: they read the image, so a
    change to `audit_call_targets.py` that moved a count is a red run here
    rather than a new number in this tool's own report.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        cls.rows, cls.seeds, cls.reached, cls.descents, cls.codemap, \
            cls.known, _, _ = bcc.build(cls.d)

    def test_the_census_has_not_moved(self):
        self.assertEqual(len(self.rows), ORACLE_SITES)
        self.assertEqual(sum(1 for r in self.rows if r["anchored"]),
                         ORACLE_ANCHORED)
        self.assertEqual(len({r["target"] for r in self.rows}), ORACLE_TARGETS)

    def test_one_target_is_also_a_trampoline_entry(self):
        shared = {r["target"] for r in self.rows} & self.known
        self.assertEqual(len(shared), ORACLE_TRAMPOLINE_NAMED)

    def test_every_seed_is_inside_the_common_area(self):
        lo, hi = bcc.region_bounds("common")
        for addr, basis in self.seeds:
            self.assertTrue(lo <= addr < hi, f"seed 0x{addr:04X} ({basis})")

    def test_no_unclassified_end_survives_on_this_image(self):
        # The count is the point, not the token: it says this image contains no
        # `descend()` end string this tool has not accounted for, so the
        # `unclassified-end` cell in the committed table is not hiding one.
        counts = {r: 0 for r in bcc.WALK_REASONS}
        for off in (r["file_offset"] for r in self.rows):
            counts[self.codemap.reason_for(off)[0]] += 1
        self.assertEqual(counts[bcc.UNCLASSIFIED], 0)

    def test_every_row_gets_a_reason_from_the_closed_vocabulary(self):
        for row in self.rows:
            reason, _ = self.codemap.reason_for(row["file_offset"])
            self.assertIn(reason, bcc.WALK_REASONS,
                          f"0x{row['file_offset']:05X} -> {reason!r}")


class CommittedTableTests(unittest.TestCase):
    """`--check` in both directions, and the two invariants about scope.

    `--check` regenerates the table from the image and diffs. A doctored CSV
    has to fail, and a missing one has to fail rather than being created: a
    `--check` that wrote the file it is checking is not a check, it is the
    thing that decides what the file says.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()

    def test_the_committed_table_is_what_this_run_derives(self):
        self.assertEqual(bcc.csv_text(self.d), COMMITTED_CSV.read_text())

    def assert_check_fails(self, doctored_text, what):
        """`check_csv` against a doctored copy, with its diff kept out of the
        suite's own output. The diff is the tool working; printing it on every
        run of this suite would put a page of expected noise in front of the
        one real failure, which is how a red run stops being read."""
        with tempfile.TemporaryDirectory() as tmp:
            doctored = Path(tmp) / 'bucket-c-codemap.csv'
            doctored.write_text(doctored_text)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), \
                    contextlib.redirect_stderr(buf):
                rc = bcc.check_csv(self.d, str(doctored))
            self.assertEqual(rc, 1, f"a {what} committed table passed --check")
            self.assertIn("not what this run derives", buf.getvalue())

    def test_a_doctored_verdict_cell_fails(self):
        # `walk_reason` and `walk_verdict` are the two columns whose pair has
        # to stay consistent, so a doctor that changes only one is the exact
        # drift `--check` exists to catch.
        self.assert_check_fails(
            COMMITTED_CSV.read_text().replace(
                ",not-reached,mid-instruction,",
                ",reached-by-walk,mid-instruction,", 1),
            "verdict-doctored")

    def test_a_doctored_membership_column_fails(self):
        self.assert_check_fails(
            COMMITTED_CSV.read_text().replace(",not listed,", ",invented,", 1),
            "membership-doctored")

    def test_a_truncated_csv_fails(self):
        # The other direction: a table that lost rows is a red run too, and a
        # check that only noticed *changed* cells would not notice this.
        text = COMMITTED_CSV.read_text()
        self.assert_check_fails("\n".join(text.splitlines()[:-1]) + "\n",
                                "truncated")

    def test_a_missing_csv_fails_rather_than_being_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / 'bucket-c-codemap.csv'
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                rc = bcc.check_csv(self.d, str(absent))
            self.assertEqual(rc, 1)
            self.assertIn("never", buf.getvalue())
            self.assertFalse(absent.exists(),
                             "--check created the file it was asked to check")

    def test_the_table_has_one_row_per_bucket_c_site(self):
        text = bcc.csv_text(self.d)
        lines = text.rstrip("\n").split("\n")
        self.assertEqual(lines[0], ",".join(bcc.CSV_HEAD))
        self.assertEqual(len(lines) - 1, ORACLE_SITES)

    def test_the_shared_columns_join_on_the_census(self):
        # Columns 1-7 are `bank-call-targets.csv`'s own, in its own spelling, so
        # a row keyed on `file_offset` from either file has to carry the same
        # bytes there. A drift between the two is a red run, not a stale row.
        # `region` is the one census column not carried across: every bucket-C
        # row is `common` by construction, so repeating it would be a column
        # that cannot disagree with itself.
        shared = ("runtime", "opcode", "target", "bucket", "frame_onto",
                  "frame_over")
        census = {}
        with open(HERE.parent / 'annotations' / 'bank-call-targets.csv') as fh:
            header = fh.readline().rstrip("\n").split(",")
            for line in fh:
                cells = line.rstrip("\n").split(",")
                census[cells[0]] = dict(zip(header, cells))
        for line in bcc.csv_text(self.d).rstrip("\n").split("\n")[1:]:
            row = dict(zip(bcc.CSV_HEAD, next(csv.reader([line]))))
            theirs = census.get(row["file_offset"])
            self.assertIsNotNone(theirs, f"{row['file_offset']} is not in the census")
            self.assertEqual(theirs["region"], "common",
                             f"{row['file_offset']} is not a common-area site")
            for col in shared:
                self.assertEqual(row[col], theirs[col],
                                 f"{row['file_offset']} column {col}")


class ScopeTests(unittest.TestCase):
    """The two files this change must not have moved.

    `bank-call-targets.csv` is another issue's output and `registers.yaml` is
    the source of truth for register status. Neither is touched here, and these
    are the cases that say so in a way a later branch cannot undo by accident.
    """

    def test_the_census_carries_no_walk_verdict_column(self):
        # The classification lives in its own file, not as a column on a census
        # someone else owns. A `walk_verdict` header cell would be the shape of
        # that mistake even if every row were right.
        with open(HERE.parent / 'annotations' / 'bank-call-targets.csv') as fh:
            header = fh.readline().strip()
        for column in ("walk_verdict", "walk_reason", "containing_function",
                       "in_data_region", "in_ghidra_function"):
            self.assertNotIn(column, header)

    def test_audit_call_targets_writes_no_walk_column(self):
        # The tool's own writer, not just the committed file: regenerating the
        # census must not acquire the column either. Run against a capture of
        # its stdout rather than reading its source, so a header added in
        # Python rather than in a literal is caught too.
        import audit_call_targets
        rows = [{"region": "common", "file_offset": 0, "runtime": 0,
                 "opcode": "ljmp", "target": 0x70, "bucket": "A",
                 "frame_onto": 0, "frame_over": 0, "calls_stub": None,
                 "calls_trampoline": None, "own_bank": "", "other_bank": ""}]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            audit_call_targets.write_csv(rows)
        header = buf.getvalue().split("\n")[0]
        self.assertEqual(header.split(",")[:6],
                         ["file_offset", "region", "runtime", "opcode",
                          "target", "bucket"])
        for column in ("walk_verdict", "walk_reason", "containing_function"):
            self.assertNotIn(column, header)

    def test_no_register_status_names_this_tool(self):
        # Nothing here is about a register, so no `status:` can have moved on
        # the strength of a Python walk over a `bytes` object.
        registers = (HERE.parent / 'annotations' / 'registers.yaml').read_text()
        for token in ("bucket_c_codemap", "bucket-c-codemap", "codemap"):
            self.assertNotIn(token, registers)

    def test_the_data_regions_yaml_is_read_and_not_rewritten(self):
        # `data_regions.py --check` re-derives every span from the image, so it
        # is the mode that would go red if this tool had written the file. Run
        # rather than asserted here: the assertion is that the mode still exits
        # 0, which is a fact about a command and not about this tool.
        result = subprocess.run(
            [sys.executable, str(HERE / 'data_regions.py'), "--check"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class RefusalTests(unittest.TestCase):
    """The refusals, from the other side of `SystemExit`.

    The tool's `--self-test` runs these against the image; these run them
    without one, so a refusal that only fires when the image loads would not be
    covered there.
    """

    def setUp(self):
        self.d = Path(FIRMWARE).read_bytes()

    def test_a_seed_outside_the_common_area_is_skipped(self):
        reached, _ = bcc.walk(self.d, [(0x1100, "stub"), (0x8000, "trampoline"),
                                       (0x9000, "trampoline"), (0xFFFF, "trampoline")])
        self.assertIn(0x1100, reached)
        for outside in (0x8000, 0x9000, 0xFFFF):
            self.assertNotIn(outside, reached)

    def test_a_budget_that_cannot_be_honoured_is_refused(self):
        for budget in (0, -1, -1000):
            with self.assertRaises(SystemExit) as caught:
                bcc.walk(self.d, [(0x1100, "stub")], max_insns=budget)
            self.assertIn("cannot be honoured", str(caught.exception))

    def test_check_and_self_test_are_refused_together(self):
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--check", "--self-test"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--check and --self-test", result.stderr)

    def test_csv_and_spans_are_refused_together(self):
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--csv", "--spans"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--csv and --spans", result.stderr)

    def test_an_image_without_the_pd_marker_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "not-the-ec.bin"
            other.write_bytes(b"\x00" * 0x20040)
            result = subprocess.run(
                [sys.executable, TOOL, str(other), "--csv"],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ITE8850-PD", result.stderr)

    def test_the_self_test_exits_zero_on_the_committed_image(self):
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--self-test"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("self-test passed", result.stdout)

    def test_check_exits_zero_on_the_committed_image(self):
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--check"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
