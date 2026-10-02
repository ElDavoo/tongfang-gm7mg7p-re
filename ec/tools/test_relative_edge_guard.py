#!/usr/bin/env python3
"""Unit checks for the rel8 site walk's region-edge guard (issue #1093).

`docs/findings/trampoline-relative-branch-sites.md`'s §"What this means for
#48" is the one place in this tree that argues a byte scan's negative is
exhaustive rather than sampled, and it names its own exception:
`relative_sites()`'s guard `i + OPCODE_LEN[op] <= hi` declines a relative form
whose instruction would not fit whole inside the region, which leaves the last
two bytes of each audited region untested. This file holds that exception
honest:

  * **the rule, on scratch bytes.** `declined_sites()` is the guard's other
    branch, and the property is that the two partition the same predicate --
    every relative-shaped byte in a region is a site in one or declined in the
    other, never neither and never both. Built rather than anchored in the
    firmware, for `test_walk_branch_arms.py`'s stated reason: a fixture at a
    real address keeps testing what it was written to test only until those
    bytes change.
  * **the window, both ways, which is where the issue's own description is
    wrong.** The six addresses are the last two bytes of the three audited
    regions read as one symmetric window, and they are not symmetric: `hi - 1`
    is declined by *any* relative form and `hi - 2` only by a 3-byte one,
    because a 2-byte form at `hi - 2` satisfies `i + 2 == hi`. A 2-byte form
    planted at `hi - 2` is an ordinary site. The case that fails if anyone
    implements the window as the pair the issue describes is here for that.
  * **the check, run and seen to fail.** `--self-test`'s new line walks the
    window and fails if any of it opens a relative branch. It is driven here in
    both directions over the committed image and over one-byte copies of it,
    because a check nobody has watched go red is a comment and a restatement
    of its predicate is not the same as running it.
  * **the image, against a transcription.** The six addresses and the byte each
    holds are stated in a module-level table below and read back out of
    `ec/firmware/GMxMGxx_11.800`, so the suite measures the image rather than
    agreeing with the tool about it.

**What this suite deliberately does not do.** It does not re-run the scan that
wrote `bank-relative-branch-targets.csv` to decide whether that census is
correct -- `test_earlier_record_column.py` gives the reason, and it is the same
one here: re-running `audit_call_targets.py` asserts the tool against itself.
It does run the tool's own writer, because there the claim is narrower and
different -- that this change regenerated nothing, which is a comparison
between the committed file and today's output and not a verdict on either.

**No count of the tree is asserted as a bare literal.** The site total the
issue quotes is read out of the tool's own walk and compared to a module-level
constant, so the two documents quoting it cannot drift apart; a figure written
into an `assertEqual` would also be a figure-pin candidate
`check_doc_figure_pins.py` would credit to whichever document happened to cite
that number, which is the reason `test_earlier_record_column.py` keeps
`ABLATION_SITE` at module level. The six addresses are a transcribed table and
not a census: they are fixed by `REGIONS` and by the guard, and no merge moves
them.
"""
import importlib.util
import io
import contextlib
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import disasm8051

# audit_call_targets imports disasm8051, find_banks and trace_xdata_refs by
# bare module name, so the tool directory has to be on the path before it is
# loaded rather than after -- the shape test_earlier_record_column.py uses for
# the same reason.
_spec = importlib.util.spec_from_file_location(
    "audit_call_targets", HERE / "audit_call_targets.py")
act = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(act)

FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
ANNOTATIONS = HERE.parent / "annotations"
CENSUS = ANNOTATIONS / "bank-relative-branch-targets.csv"
WRITEUP = ROOT / "docs" / "findings" / "region-edge-declined-sites.md"

# What each of the six bytes is *not*: a relative opcode. Named so the image
# cases say what the write-up says rather than only that two things agree.
RELATIVE_SHAPED = frozenset(disasm8051.REL_OPCODES)

# The two positions in the edge window, each with a relative form planted at it,
# as (name, offset from `hi`, opcode, OPCODE_LEN). The offsets are negative
# because that is the direction the guard is read from -- `hi` is the region's
# end and the last two bytes sit below it -- and the tool itself takes absolute
# `lo`/`hi`, so every use here adds them back. Module level for the reason
# `test_earlier_record_column.py` gives its ABLATION_SITE: a bare 0x10 written
# into an `assertEqual` is a figure-pin candidate, and a constant is invisible
# to that search.
#
# `0x40` is `jc` and `0x10` is `jbc`; the two differ in length, which is the
# whole of the asymmetry below, so the lengths are asserted rather than assumed
# and swapping the two would make the `hi - 2` case stop being a 3-byte case
# while every other assertion here still passed on a fixture that no longer
# tested it.
TWO_BYTE = ("hi - 1", -1, 0x40, 2)
THREE_BYTE = ("hi - 2", -2, 0x10, 3)

# Where the scratch fixtures put their region end. A small number rather than
# the size of the image, so the offsets in a failure message are readable and
# so a `hi` past the `common` region's runtime bound cannot turn a case about
# the guard into a `TypeError` out of `runtime_addr()`; see `scratch_region`.
SCRATCH_HI = 0x100

# The six offsets the rel8 site walk declines at a region edge on the committed
# image, as (region, file offset, the byte that offset holds), transcribed here
# rather than imported from the tool or read out of the image at import: a table
# that read itself back from the buffer could not disagree with the buffer, and
# the disagreement is the thing this suite exists to catch.
# `trampoline-relative-branch-sites.md` and `rel8-displacement-bound.md` both
# name these addresses in prose; neither is imported either.
EDGE_BYTES = (
    ("common", 0x07FFE, 0xFF),
    ("common", 0x07FFF, 0xFF),
    ("bank0", 0x0FFFE, 0xFF),
    ("bank0", 0x0FFFF, 0xFF),
    ("bank1", 0x17FFE, 0xFF),
    ("bank1", 0x17FFF, 0xFF),
)

# The population the exhaustive negative in
# `trampoline-relative-branch-sites.md` is stated over, as the write-up gives
# it, so the case that reads the tool's own walk back compares against the
# document rather than against itself.
SITES_IN_THE_AUDITED_REGIONS = 9076

# The `--self-test` line this change adds, matched on the half of it that is
# the claim rather than the half that is the count. The count is a figure and
# `SITES_IN_THE_AUDITED_REGIONS` holds it; this is a name, so a rename of the line is
# a red run here instead of a document pointing at a check that is no longer
# there under the name it quotes.
EDGE_LINE = "offsets the rel8 site walk declines at a region edge"

# The raw firmware rather than a bank image, as test_earlier_record_column.py
# gives for the same three regions: the walk is over file offsets and all six
# addresses are in audited regions, so reading the committed file is one step
# fewer than building an image in /tmp.
IMAGE = FIRMWARE.read_bytes()


def edge_window(d, lo, hi):
    """[(offset, byte)] for the window relative_sites()'s guard leaves untested.

    Written out here rather than imported, for the reason the `candidates()`
    helper in `test_earlier_record_column.py` is: the suite has to state the
    rule it is testing rather than re-run the implementation under test. The
    width comes from `act.REL_EDGE_WINDOW` because *that* is the claim -- the
    window is two bytes wide, not three and not one -- while the two positions
    inside it are named in the tuples above, so the asymmetry the window is not
    stays visible in the source.
    """
    return [(i, d[i]) for i in range(hi - act.REL_EDGE_WINDOW, hi)
            if lo <= i < hi]


def with_relative_opcode(d, at, opcode):
    """A copy of `d` with `opcode` at `at`, the way a hypothetical dump does.

    One byte into a copy of the image and nothing else, which is the same
    device `trampoline-relative-branch-sites.md` uses to redden its own line.
    A check whose failure case exists only in prose is a comment.
    """
    buf = bytearray(d)
    buf[at] = opcode
    return bytes(buf)


def scratch_region(off, opcode):
    """A zero-filled buffer with `opcode` planted `off` bytes below its `hi`.

    Returns (buffer, hi, at), with the plant inside the region at exactly the
    position `off` names -- so `off = -1` puts it at the last byte in `[lo, hi)`
    and `off = -2` at the second-to-last, which is the whole of the asymmetry
    these fixtures exist for. Deriving `hi` from `off` rather than writing it
    out per case is what keeps them honest: a case naming its own `hi` would be
    free to plant outside the region it claims to test and pass on a region
    with nothing in it, which is the failure an earlier draft of this file had.

    `SCRATCH_HI` is far below the `common` region's end rather than at the end
    of the image, because both generators go through `runtime_addr()`: an
    offset at or above `0x8000` maps to no runtime address and
    `relative_target()` raises on the `None`. A fixture parked at the top of
    the image would be testing that raise instead of the guard.
    """
    hi = SCRATCH_HI
    at = hi + off
    return with_relative_opcode(b"\x00" * hi, at, opcode), hi, at


def run_self_test(d):
    """`--self-test` over `d`, as (exit status, the lines it printed)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        status = act.self_test(d)
    return status, buf.getvalue().splitlines()


def edge_line_of(lines):
    """The new check's line out of a `--self-test` transcript, or ""."""
    return next((line for line in lines if EDGE_LINE in line), "")


class TheTwoBranchesPartitionThePredicate(unittest.TestCase):
    """What `declined_sites()` is for: naming the offsets the site walk skips,
    as the other branch of the same test rather than as a second scan."""

    def test_the_fixture_opcodes_are_the_lengths_they_are_claimed_to_be(self):
        for _name, _off, opcode, length in (TWO_BYTE, THREE_BYTE):
            with self.subTest(opcode="%#04x" % opcode):
                self.assertIn(opcode, RELATIVE_SHAPED)
                self.assertEqual(disasm8051.OPCODE_LEN[opcode], length)

    def test_a_planted_form_is_declined_and_no_longer_a_site(self):
        # The direction the two disagree on, and the whole of what the sibling
        # function is for: a form the guard refuses is one the scan does not
        # report. Both directions, because a `declined_sites()` that returned
        # every site and a `relative_sites()` that returned none would satisfy
        # either half alone.
        for name, off, opcode, _length in (TWO_BYTE, THREE_BYTE):
            buf, hi, at = scratch_region(off, opcode)
            with self.subTest(planted=name):
                self.assertEqual([i for i, *_ in act.declined_sites(buf, 0, hi)],
                                 [at])
                self.assertEqual([i for i, *_ in act.relative_sites(buf, 0, hi)],
                                 [])

    def test_the_two_are_disjoint_and_their_union_is_every_relative_byte(self):
        # The property, over a region dense enough to exercise it rather than
        # one form at a time. Every relative-shaped byte in [lo, hi) is yielded
        # by exactly one of the pair: an offset in both would be counted twice
        # and a byte in neither would be dropped without a trace, which is the
        # defect #1093 is about. The buffer is every one of the 256 byte values
        # in turn, so the population is the whole opcode table rather than the
        # two fixtures above, and its last two bytes are planted with a 3-byte
        # and a 2-byte form so the declined half is not satisfied by being
        # empty -- which is the failure a buffer of `range(256)` would have,
        # since its top two bytes are `fe ff` and neither opens a branch.
        lo, hi = 0, 256
        buf = bytearray(range(256))
        buf[hi + THREE_BYTE[1]] = THREE_BYTE[2]
        buf[hi + TWO_BYTE[1]] = TWO_BYTE[2]
        sites = {i for i, *_ in act.relative_sites(bytes(buf), lo, hi)}
        declined = {i for i, *_ in act.declined_sites(bytes(buf), lo, hi)}
        shaped = {i for i in range(lo, hi) if buf[i] in RELATIVE_SHAPED}
        self.assertFalse(sites & declined, "an offset is both a site and declined")
        self.assertEqual(sites | declined, shaped)
        self.assertTrue(declined, "no offset was declined, so the partition is "
                                   "satisfied by an empty half")
        self.assertEqual(declined, {hi + THREE_BYTE[1], hi + TWO_BYTE[1]})

    def test_the_partition_holds_on_the_committed_image_too(self):
        # The same relation, over the bytes the verdict was measured on, with
        # the two halves asserted apart rather than inferred from a count: a
        # walk that quietly stopped reading the last two bytes would still
        # report the total.
        for name in act.AUDITED:
            lo, hi = act.region_bounds(name)
            with self.subTest(region=name):
                sites = {i for i, *_ in act.relative_sites(IMAGE, lo, hi)}
                declined = {i for i, *_ in act.declined_sites(IMAGE, lo, hi)}
                shaped = {i for i in range(lo, hi) if IMAGE[i] in RELATIVE_SHAPED}
                self.assertFalse(sites & declined)
                self.assertEqual(sites | declined, shaped)


class TheWindowIsNotSymmetric(unittest.TestCase):
    """The correction to the issue's own description, and the cases that fail
    if the window is implemented as the pair the issue reads it as."""

    def test_a_two_byte_form_at_hi_minus_two_is_a_site_and_not_declined(self):
        # `i + 2 == hi`, so the whole instruction is inside the region and the
        # guard admits it. The issue's six-address figure reads the last two
        # bytes of each region as one window, and an implementation that took
        # `declined_sites()`'s population for that window would be reporting
        # this as dropped. Asserted positively, including that the
        # displacement is the last byte *inside* the region rather than the
        # first byte of the next one, because that is what makes it a site.
        # The `--self-test` line's own treatment of the same bytes is a
        # separate case, under TheCheckRunsAndCanBeSeenToFail.
        buf, hi, at = scratch_region(THREE_BYTE[1], TWO_BYTE[2])
        self.assertEqual([i for i, *_ in act.declined_sites(buf, 0, hi)], [])
        self.assertEqual([i for i, *_ in act.relative_sites(buf, 0, hi)], [at])
        self.assertEqual(at + disasm8051.OPCODE_LEN[TWO_BYTE[2]], hi)
        self.assertTrue(at + disasm8051.OPCODE_LEN[TWO_BYTE[2]] - 1 < hi)

    def test_a_two_byte_form_at_hi_minus_one_is_declined(self):
        # The other half, and the one the issue's wording is right about:
        # `i + 2 > hi` for every form, so a 2-byte form at `hi - 1` is refused
        # exactly as a 3-byte one is.
        buf, hi, at = scratch_region(TWO_BYTE[1], TWO_BYTE[2])
        self.assertEqual([i for i, *_ in act.declined_sites(buf, 0, hi)], [at])
        self.assertEqual([i for i, *_ in act.relative_sites(buf, 0, hi)], [])

    def test_a_three_byte_form_at_hi_minus_two_is_declined(self):
        # And the case that makes `hi - 2` a window at all rather than a
        # coincidence of the byte values on this image.
        buf, hi, at = scratch_region(THREE_BYTE[1], THREE_BYTE[2])
        self.assertEqual([i for i, *_ in act.declined_sites(buf, 0, hi)], [at])
        self.assertEqual([i for i, *_ in act.relative_sites(buf, 0, hi)], [])

    def test_the_window_is_two_bytes_wide_and_its_two_positions_are_named(self):
        # The width is a claim, not an accident of how many addresses the issue
        # happened to list, and the two positions inside it are the two the
        # fixtures above plant at. A guard widened to three bytes would leave
        # `hi - 3` untested as well and every other case here would still pass.
        self.assertEqual(act.REL_EDGE_WINDOW, len({TWO_BYTE[1], THREE_BYTE[1]}))
        self.assertEqual({TWO_BYTE[1], THREE_BYTE[1]},
                         set(range(-act.REL_EDGE_WINDOW, 0)))


class TheCheckRunsAndCanBeSeenToFail(unittest.TestCase):
    """`--self-test`'s new line, driven in both directions over the committed
    image. `trampoline-relative-branch-sites.md` plants a byte to redden its
    own guard for exactly this reason, and the point is that it is the tool's
    own `check()` that goes red rather than a restatement of its predicate."""

    def test_the_committed_image_passes_and_the_line_names_the_six(self):
        status, lines = run_self_test(IMAGE)
        self.assertEqual(status, 0)
        line = edge_line_of(lines)
        self.assertTrue(line, "the new line is not in the transcript")
        self.assertTrue(line.startswith("  ok "), line)
        for region, off, byte in EDGE_BYTES:
            with self.subTest(offset="%#06x" % off):
                self.assertIn("0x%05X=0x%02x" % (off, byte), line)

    def test_a_relative_opcode_at_hi_minus_one_turns_it_red(self):
        # One byte, in a copy, in each of the three audited regions. Every one
        # of them, because a check that only walked `common` would be green
        # over a bank with a form at its top edge -- and the banks are two
        # thirds of the population the verdict is stated over.
        for name in act.AUDITED:
            lo, hi = act.region_bounds(name)
            at = hi + TWO_BYTE[1]
            with self.subTest(region=name):
                self.assertEqual(run_self_test(IMAGE)[0], 0)
                status, lines = run_self_test(
                    with_relative_opcode(IMAGE, at, TWO_BYTE[2]))
                self.assertEqual(status, 1)
                line = edge_line_of(lines)
                self.assertTrue(line.startswith("  FAIL "), line)
                self.assertIn("0x%05X" % at, line)

    def test_a_three_byte_form_at_hi_minus_two_turns_it_red(self):
        # The position the issue's wording covers and the `hi - 1` case does
        # not: a 2-byte form there is an ordinary site and leaves the line
        # green, so the line's sensitivity to *this* address is a separate
        # claim from its sensitivity to the other one, and is asserted apart.
        for name in act.AUDITED:
            lo, hi = act.region_bounds(name)
            with self.subTest(region=name):
                self.assertEqual(run_self_test(IMAGE)[0], 0)
                status, lines = run_self_test(
                    with_relative_opcode(IMAGE, hi + THREE_BYTE[1],
                                         THREE_BYTE[2]))
                self.assertEqual(status, 1)
                self.assertTrue(edge_line_of(lines).startswith("  FAIL "))

    def test_a_two_byte_form_at_hi_minus_two_reddens_and_says_it_is_admitted(self):
        # The direction the correction cuts, and the one the output has to get
        # right: the line reports the *window* claim rather than the guard's,
        # so it reddens on a 2-byte form at `hi - 2` even though the guard
        # admits it and nothing is dropped there. That is deliberate -- the
        # sentence `trampoline-relative-branch-sites.md` is inherited on is
        # stated over the window, not over the guard -- so the failure clause
        # has to name the distinction. A reader who meets this line on a byte
        # the guard admits must be told that, not left to work it out from the
        # exit code.
        for name in act.AUDITED:
            lo, hi = act.region_bounds(name)
            at = hi + THREE_BYTE[1]
            with self.subTest(region=name):
                status, lines = run_self_test(
                    with_relative_opcode(IMAGE, at, TWO_BYTE[2]))
                self.assertEqual(status, 1)
                line = edge_line_of(lines)
                self.assertTrue(line.startswith("  FAIL "), line)
                self.assertIn("0x%05X" % at, line)
                self.assertIn("the guard admits", line)

    def test_a_form_the_guard_refuses_is_not_reported_as_admitted(self):
        # The other half of the same distinction, and the one that stops the
        # clause above being satisfied by a message that always says it: at
        # `hi - 1` a 2-byte form really is refused, and at `hi - 2` a 3-byte one
        # is, so neither may carry the "nothing is dropped there" wording. This
        # is the asymmetry the issue's six-address figure misses, asserted
        # through the tool's own output.
        for name in act.AUDITED:
            lo, hi = act.region_bounds(name)
            for label, off, opcode, admitted in (
                    ("2-byte at hi - 1", TWO_BYTE[1], TWO_BYTE[2], False),
                    ("3-byte at hi - 2", THREE_BYTE[1], THREE_BYTE[2], False)):
                at = hi + off
                status, lines = run_self_test(
                    with_relative_opcode(IMAGE, at, opcode))
                line = edge_line_of(lines)
                with self.subTest(region=name, planted=label):
                    self.assertEqual(status, 1)
                    self.assertIn("0x%05X" % at, line)
                    self.assertEqual("the guard admits" in line, admitted)

    def test_every_other_check_of_the_self_test_is_unmoved_by_the_plant(self):
        # Otherwise the cases above would be satisfied by a line that had
        # stopped distinguishing anything: if planting a byte turned the whole
        # transcript red, "the new line is red" would prove nothing about which
        # line saw it. Every other check must be identical, and the plant has
        # to be one that does move the new line.
        #
        # The trailing summary line is excluded because it is *supposed* to
        # move -- it reports the count the new check has just changed -- and
        # is held separately below, where it is the claim rather than noise.
        def checks(lines):
            return [l for l in lines
                    if EDGE_LINE not in l and not l.startswith("self-test ")]

        base = checks(run_self_test(IMAGE)[1])
        for name in act.AUDITED:
            lo, hi = act.region_bounds(name)
            for label, off, opcode, _length in (TWO_BYTE, THREE_BYTE):
                at = hi + off
                status, lines = run_self_test(
                    with_relative_opcode(IMAGE, at, opcode))
                with self.subTest(region=name, planted=label):
                    self.assertEqual(status, 1)
                    self.assertTrue(edge_line_of(lines).startswith("  FAIL "))
                    self.assertEqual(checks(lines), base)

    def test_the_summary_line_and_the_exit_status_agree(self):
        # The pair, in both directions, so the line that counts the failures is
        # held to the code that counts them. A summary that said "passed" while
        # returning 1 would leave the transcript above asserting a run that
        # never happened, and the base comparison in the case beside this one
        # would be comparing against it.
        status, lines = run_self_test(IMAGE)
        self.assertEqual(status, 0)
        self.assertIn("self-test passed", lines)
        for name in act.AUDITED:
            lo, hi = act.region_bounds(name)
            status, lines = run_self_test(
                with_relative_opcode(IMAGE, hi + TWO_BYTE[1], TWO_BYTE[2]))
            with self.subTest(region=name):
                self.assertEqual(status, 1)
                self.assertIn("self-test FAILED", lines)


class TheSixAddressesOnTheImage(unittest.TestCase):
    """What `trampoline-relative-branch-sites.md`'s exhaustive negative rests
    on, read out of the image against a transcription rather than against the
    tool."""

    def test_each_edge_offset_is_in_the_region_the_table_names(self):
        for region, off, _byte in EDGE_BYTES:
            lo, hi = act.region_bounds(region)
            with self.subTest(offset="%#06x" % off):
                self.assertTrue(lo <= off < hi, "%s does not hold %#06x"
                                % (region, off))

    def test_each_edge_offset_is_inside_the_window_of_its_region(self):
        # What makes the six the last two bytes rather than six addresses
        # somebody picked: each one is the `hi - 2` or the `hi - 1` of a region
        # the tool walks, and both are taken from the tool's own constant, so a
        # guard widened to three bytes fails here rather than leaving a stale
        # table agreeing with a narrower walk.
        for region, off, _byte in EDGE_BYTES:
            hi = act.region_bounds(region)[1]
            with self.subTest(offset="%#06x" % off):
                self.assertIn(off, range(hi - act.REL_EDGE_WINDOW, hi))

    def test_each_edge_offset_holds_the_byte_the_table_transcribes(self):
        for _region, off, byte in EDGE_BYTES:
            with self.subTest(offset="%#06x" % off):
                self.assertEqual(IMAGE[off], byte)

    def test_no_edge_offset_opens_a_relative_branch(self):
        # The claim itself, and stated over the transcribed addresses rather
        # than over a walk of the tool's own: this is the negative the
        # `trampoline-relative-branch-sites.md` sentence is inherited on, so it
        # is the one a reader has to be able to re-derive by hand from six
        # bytes and a table.
        for _region, off, _byte in EDGE_BYTES:
            with self.subTest(offset="%#06x" % off):
                self.assertNotIn(IMAGE[off], RELATIVE_SHAPED)

    def test_the_window_the_tool_reports_is_exactly_these_six(self):
        # The two cases above are the transcription; this is the tool reading
        # the same image, and the two agreeing is what makes the table an oracle
        # rather than a copy. In `AUDITED` order so the comparison is a list and
        # not a set -- the same six in another order is the same result, but a
        # reader comparing the two by eye wants them in one.
        reported = []
        for name in act.AUDITED:
            lo, hi = act.region_bounds(name)
            reported += ["0x%05X=0x%02x" % pair
                         for pair in edge_window(IMAGE, lo, hi)]
        self.assertEqual(reported, ["0x%05X=0x%02x" % (off, byte)
                                    for _r, off, byte in EDGE_BYTES])

    def test_the_table_covers_every_audited_region_and_both_its_offsets(self):
        # So a table that quietly lost a region -- or one of the two offsets
        # within it -- is a red run rather than a shorter list that still
        # agrees with whatever the tool printed. Which regions are walked is
        # the tool's own `AUDITED`; the width is its constant.
        self.assertEqual({region for region, _o, _b in EDGE_BYTES},
                         set(act.AUDITED))
        for region in act.AUDITED:
            lo, hi = act.region_bounds(region)
            offsets = [off for r, off, _b in EDGE_BYTES if r == region]
            with self.subTest(region=region):
                self.assertEqual(offsets, list(range(hi - act.REL_EDGE_WINDOW,
                                                     hi)))


class NothingDownstreamMoved(unittest.TestCase):
    """The issue's done condition: a reported fact, not a different scan. The
    census is byte-identical, the site total is the one every other write-up
    quotes, and the new sibling adds no site and drops none."""

    def test_the_site_total_is_the_one_the_verdict_was_measured_on(self):
        # Read out of the tool's own walk and compared to what
        # `trampoline-relative-branch-sites.md` states, so the two documents
        # that quote it cannot drift apart.
        total = sum(sum(1 for _ in act.relative_sites(IMAGE,
                                                      *act.region_bounds(n)))
                    for n in act.AUDITED)
        self.assertEqual(total, SITES_IN_THE_AUDITED_REGIONS)

    def test_no_offset_is_declined_in_any_audited_region(self):
        # The other half of the same claim, and the one that is new: a declined
        # offset has no row, so a site appearing here would be one nothing
        # downstream could have seen. Zero on this image, and it is the state
        # the write-up's *why the CSV column was declined* section is about.
        for name in act.AUDITED:
            lo, hi = act.region_bounds(name)
            with self.subTest(region=name):
                self.assertEqual(list(act.declined_sites(IMAGE, lo, hi)), [])

    def test_every_site_keeps_its_displacement_inside_its_own_region(self):
        # The invariant the guard exists to hold, asserted directly over the
        # image rather than inferred from the count above. A guard loosened far
        # enough to admit a cross-region displacement would keep the total
        # right for a moment -- the read would still succeed, it would just be
        # reading the next region -- and only this fails.
        for name in act.AUDITED:
            lo, hi = act.region_bounds(name)
            for off, op, _target in act.relative_sites(IMAGE, lo, hi):
                with self.subTest(offset="%#06x" % off):
                    self.assertTrue(
                        lo <= off + disasm8051.OPCODE_LEN[op] - 1 < hi)

    def test_the_relative_census_is_byte_identical_to_the_tools_own_output(self):
        # Run the writer rather than compare a line count: a regenerated census
        # that had gained or lost a column would keep its rows and fail here,
        # and one that had reordered a column would fail here too. This is the
        # only place the scan is re-run, and what it is asked is the narrow
        # question -- did this change regenerate anything -- rather than
        # whether the census is right, which is a different suite's business.
        #
        # Compared as bytes, because `csv.writer` emits `\r\n` and reading the
        # committed file as text would normalise them away: the comparison is
        # "did anything move", and a newline that the reader silently rewrote
        # is a byte the comparison would not have looked at.
        buf = io.BytesIO()
        with contextlib.redirect_stdout(io.TextIOWrapper(buf, encoding="utf-8",
                                                         newline="")) as out:
            act.write_relative_csv(act.relative_survey(IMAGE)[0])
            out.flush()
        self.assertEqual(buf.getvalue(), CENSUS.read_bytes())

    def test_the_header_the_writer_emits_is_still_the_committed_one(self):
        # Separately from the byte comparison, so a failure says which of the
        # two it is. A header assembled from a list rather than written as a
        # literal would match the file today and would have changed the shape
        # of the writer without changing a byte of its output.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            act.write_relative_csv([])
        self.assertEqual(buf.getvalue().splitlines()[0],
                         CENSUS.read_text().splitlines()[0].rstrip())


class WhatThisDoesNotClaim(unittest.TestCase):
    """Pinned because these are cheap to make by accident in prose, and this is
    the file a reader would open to check them."""

    def test_no_register_status_is_named_by_this_change(self):
        registers = (ANNOTATIONS / "registers.yaml").read_text()
        for token in ("declined_sites", "region-edge", "REL_EDGE_WINDOW"):
            with self.subTest(token=token):
                self.assertNotIn(token, registers)

    def test_the_writeup_states_the_blind_spots(self):
        # Prose assertions, and the write-up is where a reader looks for them.
        # A finding that says only what it measured is the failure mode
        # CLAUDE.md's calibration rule exists to catch.
        text = " ".join(WRITEUP.read_text().replace("**", "").split()).lower()
        for phrase in ("this image",
                       "no live test",
                       "not a claim about any other dump"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_the_writeup_quotes_the_verdict_it_corrects(self):
        # The issue's six-address figure is wrong about the window's symmetry,
        # and the write-up says so *beside* the sentence it corrects, the way
        # `docs/findings.md` 4a-4d does, rather than restating the number as
        # though it had been right. A write-up that quietly dropped the wrong
        # claim would be indistinguishable from one that never had it.
        text = " ".join(WRITEUP.read_text().replace("**", "").split()).lower()
        for phrase in ("six addresses", "not symmetric", "all six hold"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_the_writeup_names_the_column_it_declined_and_its_trigger(self):
        # The narrowing, recorded where a reader who wanted the `declined`
        # column would look for it. A write-up that said only "not done" would
        # leave the next agent to re-derive the whole argument.
        text = " ".join(WRITEUP.read_text().replace("**", "").split()).lower()
        for phrase in ("bank-relative-branch-targets.csv",
                       "what would reverse"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_the_writeup_makes_no_claim_about_the_audit_counts(self):
        # The issue's own limit, held: nothing here moves a count in
        # `bank-call-audit.md` or a `status:` in `registers.yaml`, and a
        # write-up that grew a section renumbering those would be overclaiming
        # a change that did not happen.
        text = WRITEUP.read_text()
        self.assertIn("No `registers.yaml` `status:` moved", text)


if __name__ == "__main__":
    unittest.main()
