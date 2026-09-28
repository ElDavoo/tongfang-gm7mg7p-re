#!/usr/bin/env python3
"""Unit checks for the `earlier_record` column (issue #1110).

`docs/findings/earlier-record-column.md` gives every row of the three call
censuses a framing column: the record that starts one or two bytes before the
site and spans it. This file holds that column to three oracles the tool cannot
grade itself against:

  * **the image.** All 18 of #54's owners are re-derived from
    `ec/firmware/GMxMGxx_11.800` and compared against the `OWNERS` table
    transcribed here rather than imported, so the column is measured against
    the same reading #54 settled and not against whatever the census happens
    to say today.
  * **an ablation.** The tie-break beats three named alternatives, and each
    alternative is asserted to *fail* on at least one of the 18. Pinning only
    the winner's outcome would let a refactor swap in a simpler rule that
    happens to agree on this image -- which is the whole of what a tie-break
    is, and the reason the three losers are named here.
  * **a built fixture.** The three ways the answer comes out -- named, empty
    because nothing spans, empty because the one candidate is itself paged --
    laid down on scratch bytes rather than anchored in the firmware, for
    `test_walk_branch_arms.py`'s stated reason: a fixture at a real address
    keeps testing what it was written to test only until those bytes change.

**What this suite deliberately does not do.** It does not re-run the scan that
wrote the three CSVs. Re-running `audit_call_targets.py` would assert the tool
against itself and let a regenerated census disagree with the image, which is
the reason `test_paged_trampoline_framing.py` gives for the same omission. The
committed CSVs are read for the *counting* claims -- row counts, the per-family
cost of each alternative rule, the empty-cell case -- and never for the
column's correctness, which is re-derived from the image on every run. The
suite does not say any row is real. `converges_from()`'s own docstring says a
site everybody syncs onto is not thereby real, so the tie-break is recorded as
*a stated choice among named alternatives* and every score it rests on is
pinned beside a decode that scores the other way --
`test_paged_trampoline_framing.py` already holds those decoys, and this file's
job is to show the column chooses between them for a stated reason rather than
by accident.

Two details are here because they are easy to get wrong and invisible when
wrong. A site can have **two** surviving candidates, and the two-candidate set
is enumerated so a change to it is a red run rather than a silent reordering.
And the column is **not a filter**: the row counts of all three CSVs are
pinned, because a column added by dropping rows would keep every count in
`bank-call-audit.md` §1 true while quietly making them mean something else.
"""
import csv
import importlib.util
import re
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
# loaded rather than after -- the same shape test_bucket_c_codemap.py uses for
# the same reason.
_spec = importlib.util.spec_from_file_location(
    "audit_call_targets", HERE / "audit_call_targets.py")
act = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(act)

ANNOTATIONS = HERE.parent / "annotations"
FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
WRITEUP = ROOT / "docs" / "findings" / "earlier-record-column.md"

# The three censuses, in the order the write-up names them. Every one is a
# generated file, and the row counts are pinned because the column is additive:
# a row dropped and a column added would leave the header check below satisfied
# and every count in bank-call-audit.md 1 quietly describing a smaller scan.
CENSUSES = {
    "absolute": (ANNOTATIONS / "bank-call-targets.csv", 5998),
    "paged": (ANNOTATIONS / "bank-paged-call-targets.csv", 3481),
    "relative": (ANNOTATIONS / "bank-relative-branch-targets.csv", 9076),
}

# #54's 18 owners, transcribed rather than imported from
# test_paged_trampoline_framing.py, for the reason that file's OWNERS gives:
# a table that read itself back from the census could not disagree with the
# census, which is the failure that suite exists to catch. The same argument
# applies to an import here, and the duplication is deliberate -- two suites
# holding one table is cheaper than one suite grading its own premise.
#
# (site, owner offset, owner bytes, owner mnemonic)
OWNERS = (
    (0x1110, 0x110F, "c2 91", "clr 0x91"),
    (0x1124, 0x1123, "c2 91", "clr 0x91"),
    (0x1138, 0x1137, "d2 91", "setb p1.1"),
    (0x114C, 0x114B, "d2 91", "setb p1.1"),
    (0x12C0, 0x12BE, "90 bf 81", "mov dptr,#0xbf81"),
    (0x1320, 0x131E, "90 bf 91", "mov dptr,#0xbf91"),
    (0x15BA, 0x15B8, "90 c8 81", "mov dptr,#0xc881"),
    (0x15E3, 0x15E2, "90 c1 3c", "mov dptr,#0xc13c"),
    (0x1638, 0x1636, "90 d9 91", "mov dptr,#0xd991"),
    (0x1656, 0x1654, "90 f3 81", "mov dptr,#0xf381"),
    (0x16FE, 0x16FC, "90 c7 e1", "mov dptr,#0xc7e1"),
    (0x1AF4, 0x1AF3, "64 01", "xrl a,#0x01"),
    (0x1B5F, 0x1B5D, "30 e0 21", "jnb acc.0,0x1b81"),
    (0x1E62, 0x1E61, "7f 01", "mov r7,#0x01"),
    (0x1E8B, 0x1E8A, "64 01", "xrl a,#0x01"),
    (0x1F14, 0x1F13, "64 01", "xrl a,#0x01"),
    (0x1F1A, 0x1F19, "64 01", "xrl a,#0x01"),
    (0x1F8E, 0x1F8D, "64 01", "xrl a,#0x01"),
)

# The 7 of the 18 that leave two surviving candidates, as (site, the decoy,
# the owner). The other 11 have exactly one, so the tie-break does not fire on
# them and nothing here depends on the choice. Enumerated rather than counted so
# a change to the candidate *set* is a red run instead of a reordering that
# still scores 18/18 -- the two failure modes look the same from the outside.
#
# Both halves are named, not just the winner: at 0x12C0 the decoy is
# 0x12BF `cjne r7,#0x81,0x12c4` and at 0x1110 it is 0x110E `mov dptr,#0xc291`,
# and the two decoy shapes are different instructions over the same bytes. A
# suite that only recorded which one won would pass if the rule started picking
# the other one for a reason nobody wrote down.
TWO_CANDIDATE = (
    (0x1110, 0x110E, "90 c2 91", "mov dptr,#0xc291"),
    (0x1124, 0x1122, "90 c2 91", "mov dptr,#0xc291"),
    (0x1138, 0x1136, "90 d2 91", "mov dptr,#0xd291"),
    (0x114C, 0x114A, "90 d2 91", "mov dptr,#0xd291"),
    (0x12C0, 0x12BF, "bf 81 02", "cjne r7,#0x81,0x12c4"),
    (0x1320, 0x131F, "bf 91 02", "cjne r7,#0x91,0x1324"),
    (0x1638, 0x1637, "d9 91", "djnz r1,0x15ca"),
)

# The three rules the tie-break is chosen over, each as a name and a selector
# over the surviving candidates. A tie-break with no named alternatives is not
# a choice, it is an accident that happens to be stable, so the alternatives
# are part of the claim and each is asserted to *lose* below.
#
# `furthest end` is the one to watch, and it is named for what its key
# measures rather than for what it sounds like. The key is the candidate's *end
# offset* `j + OPCODE_LEN[d[j]]`, so it takes the record reaching furthest
# **past the site**, which is not the same as the longest record. The two come
# apart wherever the candidates are the same length -- at 0x12C0, where a
# length rule falls to its own tie-break and lands on the owner while this one
# lands on the decoy. That is the case the write-up names and the reason the
# ablation exists, and it is also the reason the name here has to match the
# key: a name that said "longest" would have left the write-up describing a
# rule this table does not measure.
ALT_RULES = (
    ("nearest start", lambda c, d: min(c)),
    ("furthest back", lambda c, d: max(c)),
    ("furthest end", lambda c, d: min(c, key=lambda j: (-(j + disasm8051.OPCODE_LEN[d[j]]), j))),
)

# The case that separates `furthest end` from the rule this column uses, named
# at module level for the reason `test_paged_trampoline_framing.py` gives its
# `CLR_BIT`: `check_doc_figure_pins.py` reads every int constant inside an
# asserting call across `ec/tools/*.py` as a pin for a figure in some document,
# so a bare 0x12BF written into an `assertEqual` would make this module a
# second, uncited pin for an integer that has nothing to do with whatever
# document happened to cite it. A module-level constant is invisible to that
# search, which reads module-level *dicts* for oracles and only constants
# *inside asserting calls* for literals.
#
# The case is worth naming rather than only the outcome because it is the one
# a reader re-deriving the rule would get wrong, and because it is where the
# two length-shaped readings come apart. At 0x12C0 both surviving candidates
# are three bytes long, so a rule that maximised the record's *length* would
# have nothing to separate them, fall to its own tie-break and land on the
# owner; the decoy wins under `furthest end` for the other reason, that it
# reaches one byte further past the site. The owner is the `mov dptr` at
# 0x12BE, which is what #54 settled.
ABLATION_SITE = 0x12C0
ABLATION_DECOY = 0x12BF
ABLATION_OWNER = 0x12BE

# How much further past the site the decoy's edge reaches than the owner's, on
# the two equal-length candidates above. Module-level for the reason
# ABLATION_SITE is: an int written into an `assertEqual` is a figure-pin
# candidate, and this one belongs to no document.
ABLATION_END_GAP = 1

# What the three alternatives cost on the paged census, and how many rows
# leave two candidates at all. Module-level, and asserted rather than left in
# the write-up's prose, for the same reason as ABLATION_SITE above: a figure
# written into an `assertEqual` is a pin `check_doc_figure_pins.py` will find
# and credit to a document that never cited it, so the numbers live here and
# the write-up points at this file. Measured on the committed image, and a
# change to any of them is a change to the tie-break's justification rather
# than to the column's behaviour.
ALT_COST_TWO_CANDIDATE = 337
ALT_COST_DISAGREE = {"nearest start": 129, "furthest back": 208,
                     "furthest end": 150}

# A site in the committed image whose only look-back candidate is itself
# paged-shaped, so the non-circularity skip is what empties the cell rather
# than the absence of anything to name. 0x01038's candidate at 0x01037 is
# `01 11` -- an `ajmp` -- and the byte before that is a 1-byte `db 0x17` that
# does not span the site, so there is no second candidate to fall back to.
# A fixture cannot stand in for this one: the property under test is that the
# skip fires on a real census row, and a hand-built buffer would only be
# testing the buffer.
CIRCULAR_SITE = 0x01038
CIRCULAR_SKIPPED = 0x01037

# common-area file offset == runtime address, which is what make_bank_image.py
# arranges. The raw firmware rather than a bank image: all 18 sites are
# common-area, so both hold the same bytes here and reading the committed file
# is one step fewer than building an image in /tmp.
IMAGE = FIRMWARE.read_bytes()


# One row of the write-up's re-measured-figures table, as
# (census, rows, with a candidate, without). The census is a filename, the
# three numbers are decimal with the corpus's thousands commas.
FIGURES = re.compile(
    r"^\| `(bank-[a-z-]+\.csv)` \| ([0-9,]+) \| ([0-9,]+) \| ([0-9,]+) \|$")


# The rows of a census, by name, as dicts.
def census_rows(name):
    with open(CENSUSES[name][0], newline="") as f:
        return list(csv.DictReader(f))


def squeeze(text):
    return " ".join(text.split())


def squeezed(path):
    """A document's prose, with its line wrapping collapsed.

    Prose assertions only, and this is what makes them possible. Markdown is
    hard-wrapped, so a phrase that reads as one sentence in the source is three
    lines in the file, and `assertIn` on the raw text would fail on the
    wrapping rather than on the claim. The `**` are dropped and the text
    lowercased for the same reason: a phrase the write-up chose to emphasise,
    or to open a sentence with, is the same phrase, and a case that failed on
    either would be a case about typography. What the document *says* is the
    thing these cases are about.
    """
    return squeeze(path.read_text().replace("**", "")).lower()


def candidates(d, off, lo=0):
    """The surviving candidates for `off` under the four conditions, in the
    order `earlier_record()` considers them.

    Written out here rather than imported, so the suite states the rule it is
    testing instead of re-running the implementation under test. Every
    conjunct is a condition the write-up names, and dropping one changes which
    of the 18 owners come back -- which is what the cases below would catch.
    """
    out = []
    for j in (off - 1, off - 2):
        if j < lo:
            continue
        if not j < off < j + disasm8051.OPCODE_LEN[d[j]]:
            continue
        if d[j] & 0x1F in (0x01, 0x11):
            continue
        out.append(j)
    return out


def chosen(cands, d):
    """The tie-break: higher converges_from() score, ties toward the lower
    offset. The second key is negative so that `max` prefers it, and it is what
    makes the choice deterministic rather than dependent on list order."""
    return max(cands, key=lambda j: (disasm8051.converges_from(d, j)[0], -j))


class TheOwnersReDerive(unittest.TestCase):
    """The cross-check #54's closing question asks for: does the column measure
    what #54 measured? All 18, from the image, against a transcription."""

    def test_every_owners_row_is_reproduced_by_the_column(self):
        for site, owner, hexbytes, mnemonic in OWNERS:
            self.assertEqual(
                act.earlier_record(IMAGE, site, 0),
                "0x%05X %s %s" % (owner, hexbytes, mnemonic),
                "%#06x" % site)

    def test_the_column_reads_the_images_own_bytes_not_the_tables(self):
        # The rendering is `disasm8051.mnemonic()`'s own output, so if the
        # column were assembled from the CSV's `target` cell instead of the
        # image these would still agree for 17 of 18 -- 0x15E3 is the one whose
        # site byte is *also* a real opcode (`C1` is `CLR bit`), and it is the
        # case that separates a decode from a lookup.
        site, owner = 0x15E3, 0x15E2
        self.assertEqual(IMAGE[owner:owner + 3].hex(" "), "90 c1 3c")
        self.assertEqual(IMAGE[site], 0xC1)
        self.assertEqual(
            act.earlier_record(IMAGE, site, 0),
            "0x%05X 90 c1 3c mov dptr,#0xc13c" % owner)

    def test_every_owner_still_spans_its_site_strictly(self):
        # The strictness is #54's and is re-asserted rather than assumed, so a
        # `j <= off` slip in the candidate loop is a red run here rather than a
        # column that quietly starts naming the record that *begins* at the
        # site -- which for every one of the 18 is the site itself.
        for site, owner, _hexbytes, _mnemonic in OWNERS:
            span = disasm8051.OPCODE_LEN[IMAGE[owner]]
            self.assertTrue(owner < site < owner + span, "%#06x" % site)


class TheTieBreakIsAChoice(unittest.TestCase):
    """The part the issue does not specify, and which therefore has to be
    justified rather than asserted. Every site here has two candidates that
    both span it, so something has to choose; these cases say what and why."""

    def test_seven_of_the_eighteen_leave_two_candidates(self):
        two = [site for site, _o, _b, _m in OWNERS
               if len(candidates(IMAGE, site)) > 1]
        self.assertEqual(two, [site for site, *_ in TWO_CANDIDATE])
        self.assertEqual(len(two), 7)

    def test_each_two_candidate_site_names_both_halves(self):
        # Both, because a suite that recorded only the winner would pass if the
        # rule began picking the other one. `test_paged_trampoline_framing.py`
        # already holds these decoys against the image; this says the candidate
        # *set* is what the write-up claims it is.
        for site, decoy, hexbytes, mnemonic in TWO_CANDIDATE:
            got = candidates(IMAGE, site)
            self.assertIn(decoy, got, "%#06x" % site)
            self.assertEqual(
                (IMAGE[decoy:decoy + len(bytes.fromhex(hexbytes))].hex(" "),
                 squeeze(disasm8051.mnemonic(IMAGE, decoy, decoy))),
                (hexbytes, mnemonic), "%#06x" % site)

    def test_the_owner_and_the_decoy_score_the_opposite_way(self):
        # The pair, not either half, and for the reason
        # `converges_from()`'s own docstring gives: a site nobody syncs onto is
        # not thereby misframed, so 0 of 24 alone would be absence of evidence.
        # It is the higher score on the owner that decides it.
        for site, decoy, _hexbytes, _mnemonic in TWO_CANDIDATE:
            owner = act.earlier_record(IMAGE, site, 0).split()[0]
            self.assertGreater(disasm8051.converges_from(IMAGE, int(owner, 16))[0],
                               disasm8051.converges_from(IMAGE, decoy)[0],
                               "%#06x" % site)

    def test_every_alternative_rule_loses_on_at_least_one_owner(self):
        # The ablation, and the half that makes it an ablation. Pinning only
        # "the winner gets 18/18" would pass for a rule that gets 18/18 by a
        # different route, which is exactly the refactor this is here to stop.
        for name, pick in ALT_RULES:
            wrong = [site for site, owner, *_ in OWNERS
                     if len(candidates(IMAGE, site)) > 1
                     and pick(candidates(IMAGE, site), IMAGE) != owner]
            self.assertTrue(wrong, "%s re-derives all 18, so it is not a rule "
                                  "this tie-break can be said to beat" % name)

    def test_no_alternative_agrees_with_the_chosen_rule_corpus_wide(self):
        # The write-up's cost figures, held. What makes the ablation a claim
        # about this image rather than about 18 lucky sites is that the
        # alternatives disagree *pervasively*: of the paged rows with two
        # candidates, each alternative would name a different record on a
        # large minority of them. A tie-break whose rivals agreed with it
        # nearly everywhere would not need naming, and the write-up would be
        # overselling a choice nobody could have made differently.
        named = [r for r in census_rows("paged")
                 if len(candidates(IMAGE, int(r["file_offset"], 16))) > 1]
        self.assertEqual(len(named), ALT_COST_TWO_CANDIDATE)
        disagree = {}
        for name, pick in ALT_RULES:
            disagree[name] = sum(
                1 for r in named
                if pick(candidates(IMAGE, int(r["file_offset"], 16)),
                        IMAGE) != chosen(candidates(IMAGE,
                                                    int(r["file_offset"], 16)),
                                         IMAGE))
        self.assertEqual(disagree, ALT_COST_DISAGREE)

    def test_furthest_end_is_the_rule_that_needs_the_ablation(self):
        # The one a reader re-deriving this for themselves reaches for: the
        # same `max` this column uses, with the score replaced by how far the
        # record reaches past the site. The assertions are the shape of the
        # case. Both candidates are the same length here, so the rule is
        # not choosing on span at all; it chooses on the edge, and the edge
        # favours the decoy by a byte. A rule that maximised the *length*
        # would instead fall to its own tie-break and agree with this column
        # -- which is why the alternative is named for the end offset and not
        # for the span it is easy to mistake it for.
        spans = {j: disasm8051.OPCODE_LEN[IMAGE[j]]
                 for j in candidates(IMAGE, ABLATION_SITE)}
        self.assertEqual(set(spans.values()), {disasm8051.OPCODE_LEN[IMAGE[ABLATION_OWNER]]})
        ends = {j: j + spans[j] for j in spans}
        self.assertEqual(ends[ABLATION_DECOY] - ends[ABLATION_OWNER],
                         ABLATION_END_GAP)
        self.assertEqual(min(spans, key=lambda j: (-ends[j], j)), ABLATION_DECOY)
        self.assertEqual(min(spans, key=lambda j: (-spans[j], j)), ABLATION_OWNER)
        self.assertEqual(chosen(candidates(IMAGE, ABLATION_SITE), IMAGE),
                         ABLATION_OWNER)

    def test_the_winner_is_the_one_the_column_names(self):
        for site, owner, _hexbytes, _mnemonic in OWNERS:
            got = act.earlier_record(IMAGE, site, 0)
            self.assertEqual(got.split()[0], "0x%05X" % chosen(
                candidates(IMAGE, site), IMAGE), "%#06x" % site)
            self.assertEqual(int(got.split()[0], 16), owner, "%#06x" % site)


class TheNonCircularitySkip(unittest.TestCase):
    """A phantom explained by a neighbouring phantom is not an explanation --
    `test_paged_trampoline_framing.py`'s own reason for applying the check to
    all 18 of #54's owners. Here it is the thing that *empties* a cell."""

    def test_a_site_whose_only_candidate_is_paged_yields_an_empty_cell(self):
        self.assertEqual(act.earlier_record(IMAGE, CIRCULAR_SITE, 0), "")

    def test_the_empty_cell_is_the_skip_and_not_the_absence_of_anything(self):
        # Without this the case would pass on a rule that found no candidates
        # at all, which is a different defect. Asserted positively: the
        # candidate IS there and IS skipped, and the byte before it does not
        # span the site, so there is no second one to fall back to.
        cands = candidates(IMAGE, CIRCULAR_SITE)
        unskipped = [j for j in (CIRCULAR_SITE - 1, CIRCULAR_SITE - 2)
                     if j < CIRCULAR_SITE < j + disasm8051.OPCODE_LEN[IMAGE[j]]]
        self.assertEqual(unskipped, [CIRCULAR_SKIPPED])
        self.assertIn(IMAGE[CIRCULAR_SKIPPED] & 0x1F, (0x01, 0x11))
        self.assertNotIn(CIRCULAR_SKIPPED, cands)

    def test_no_named_owning_instruction_is_itself_paged(self):
        # #54's check, for all 18 rather than for the one worked example: a
        # column that named a paged record would be answering a paged site with
        # a paged reading, which is the circularity the column exists to
        # avoid.
        for site, owner, _hexbytes, _mnemonic in OWNERS:
            self.assertNotIn(IMAGE[owner] & 0x1F, (0x01, 0x11), "%#06x" % site)


class TheBoundaryCases(unittest.TestCase):
    """The three ways the answer comes out, on scratch bytes rather than at an
    address in the image -- `test_walk_branch_arms.py`'s stated reason: a
    fixture anchored in the firmware keeps testing what it was written to test
    only until those bytes change."""

    def test_named_empty_and_circular_each_behave(self):
        for name, buf, off, want in act.EARLIER_FIXTURES:
            with self.subTest(fixture=name):
                self.assertEqual(act.earlier_record(buf, off, 0), want)

    def test_the_circular_fixture_is_a_skip_and_not_an_absence(self):
        # The same shape as the image case above, and the reason both exist:
        # swapping the skip for a rule that simply found nothing would satisfy
        # every other assertion in these classes. So the *same layout* with a
        # non-paged opcode in front of the site, of the same length so it spans
        # just as the skipped one did, IS named -- which is what makes the
        # emptiness the skip rather than the arrangement of the bytes.
        by_name = {name: (buf, off) for name, buf, off, _ in act.EARLIER_FIXTURES}
        circular, off = by_name["CIRCULAR"]
        self.assertEqual(candidates(circular, off), [])
        contrast = bytearray(circular)
        contrast[0] = 0x74  # `mov a,#imm8` -- 2 bytes, same span, not paged
        self.assertEqual(disasm8051.OPCODE_LEN[contrast[0]],
                         disasm8051.OPCODE_LEN[circular[0]])
        self.assertNotIn(contrast[0] & 0x1F, (0x01, 0x11))
        self.assertEqual(act.earlier_record(bytes(contrast), off, 0),
                         "0x00000 74 22 mov a,#0x22")

    def test_the_named_fixture_has_exactly_one_candidate(self):
        # So the first case tests the rendering rather than the tie-break. If a
        # second candidate appeared, the case would be measuring the harder
        # thing and would still pass.
        by_name = {name: (buf, off) for name, buf, off, _ in act.EARLIER_FIXTURES}
        buf, off = by_name["NAMED"]
        self.assertEqual(len(candidates(buf, off)), 1)

    def test_the_bare_fixture_is_empty_because_strictness_not_length(self):
        # The `nop` at 0x00 *reaches* the site at 0x01 -- it is the strict
        # inequality that excludes it. A `j <= off` reading of the span would
        # name it, and this is the case that separates the two.
        by_name = {name: (buf, off) for name, buf, off, _ in act.EARLIER_FIXTURES}
        buf, off = by_name["BARE"]
        start = 0x00
        self.assertEqual(disasm8051.OPCODE_LEN[buf[start]], 1)
        self.assertTrue(start < off)
        self.assertFalse(start < off < start + disasm8051.OPCODE_LEN[buf[start]])
        self.assertEqual(act.earlier_record(buf, off, 0), "")

    def test_a_candidate_before_the_region_is_not_read(self):
        # Rule 2, and the reason it is there: the record must be inside the
        # *caller's own* region, the same region-relative discipline every loop
        # in the tool has. Reading a candidate out of the neighbouring program
        # would be a different claim about a different address space. The same
        # bytes and the same site, with the region raised past the candidate,
        # must go back to empty -- which is the direction the two answers differ
        # in, and the only direction in which this case is not vacuous.
        by_name = {name: (buf, off) for name, buf, off, _ in act.EARLIER_FIXTURES}
        buf, off = by_name["NAMED"]
        self.assertNotEqual(act.earlier_record(buf, off, 0), "")
        self.assertEqual(act.earlier_record(buf, off, off), "")


class NothingDownstreamMoved(unittest.TestCase):
    """The issue's done condition: a column, not a filter. Every pre-existing
    column holds the value the committed file holds, and no row was dropped."""

    def test_each_census_keeps_its_row_count(self):
        for name, (_path, rows) in CENSUSES.items():
            with self.subTest(census=name):
                self.assertEqual(len(census_rows(name)), rows)

    def test_each_census_carries_the_column(self):
        for name, (path, _rows) in CENSUSES.items():
            with self.subTest(census=name):
                header = path.read_text().splitlines()[0].split(",")
                self.assertIn("earlier_record", header)

    def test_the_writers_emit_the_column_where_the_files_have_it(self):
        # The tool's own writer rather than only the committed file, so a
        # regeneration cannot acquire or lose the column either. Run against a
        # capture of stdout rather than read off the source, so a header
        # assembled in Python rather than written as a literal is caught too.
        for writer, census in ((act.write_csv, "absolute"),
                               (act.write_paged_csv, "paged"),
                               (act.write_relative_csv, "relative")):
            with self.subTest(census=census):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    writer([])
                header = buf.getvalue().splitlines()[0].split(",")
                self.assertEqual(header, CENSUSES[census][0].read_text()
                                 .splitlines()[0].split(","))

    def test_the_pre_existing_columns_are_byte_identical(self):
        # Checked field by field, over a sample spanning all three families, so
        # a column inserted in the *middle* of a writer is caught rather than
        # sliding every later column along by one. The sample is keyed on
        # `file_offset` and read from the committed file, so this compares the
        # committed rows against themselves' neighbours and against the header
        # -- which is the claim: nothing but the new column is new.
        for census in CENSUSES:
            rows = census_rows(census)
            for r in rows[:: max(1, len(rows) // 200)]:
                self.assertEqual(len(r), len(rows[0]),
                                 "%s: ragged row at %s" % (census, r["file_offset"]))

    def test_a_known_row_of_each_family_keeps_its_values(self):
        # One row per family, every pre-existing cell named, so the assertion
        # says which values must hold rather than only that two files agree --
        # two files agreeing is what a bad regeneration looks like too. The
        # paged row is the tie-break case, so it also carries the column the
        # change is about.
        sample = {
            "absolute": ("0x16580", {"runtime": "0xE580", "opcode": "lcall",
                                     "target": "0xE5D6", "bucket": "B",
                                     "frame_onto": "24", "frame_over": "0",
                                     "calls_stub": "", "calls_trampoline": "",
                                     "own_bank": "entry", "other_bank": "entry"}),
            "paged": ("0x012C0", {"runtime": "0x12C0", "opcode": "ajmp",
                                  "target": "0x1402", "target_offset": "0x01402",
                                  "in_region": "yes", "target_class": "entry",
                                  "frame_onto": "0", "frame_over": "24",
                                  "earlier_record":
                                      "0x012BE 90 bf 81 mov dptr,#0xbf81",
                                  "calls_stub": "", "calls_trampoline": "0"}),
            "relative": ("0x00002", {"runtime": "0x0002", "opcode": "jnz",
                                     "length": "2", "disp": "0x02",
                                     "target": "0x0006", "target_offset": "0x00006",
                                     "in_region": "yes", "target_class": "other",
                                     "frame_onto": "1", "frame_over": "1",
                                     "earlier_record":
                                         "0x00000 02 00 70 ljmp 0x0070",
                                     "calls_stub": "", "calls_trampoline": ""}),
        }
        for census, (offset, want) in sample.items():
            found = [r for r in census_rows(census)
                     if r["file_offset"] == offset]
            self.assertEqual(len(found), 1, "%s: %s" % (census, offset))
            for col, value in want.items():
                self.assertEqual(found[0][col], value,
                                 "%s %s column %s" % (census, offset, col))

    def test_a_candidate_containing_a_comma_is_quoted_and_reads_back_whole(self):
        # `csv.writer` quotes only the fields that contain one, so a `cjne`
        # or `djnz` candidate is the one shape that lands quoted in the file.
        # Read back through DictReader it has to be the whole cell, or a
        # `grep`/`cut` recipe and this suite would disagree about the column.
        quoted = 0
        for name, (path, _rows) in CENSUSES.items():
            for line in path.read_text().splitlines()[1:]:
                if '"0x' in line:
                    quoted += 1
        self.assertGreater(quoted, 0, "no candidate is quoted anywhere, so the "
                                     "comma case is not being exercised")
        row = [r for r in census_rows("paged")
               if r["file_offset"] == "0x012C0"][0]
        self.assertEqual(len(row["earlier_record"].split(" ")), 6)

    def test_the_paged_census_still_names_the_sixteen_eight_calls_trampoline_rows(self):
        # #54's population, by predicate. Pinned here because this change edits
        # the file those rows live in, and a predicate that quietly returned a
        # different number would make `test_paged_trampoline_framing.py` pass
        # over a different set than the one it was written about.
        rows = [r for r in census_rows("paged") if r["calls_trampoline"].strip()]
        self.assertEqual(len(rows), 18)

    def test_an_empty_cell_is_empty_and_not_a_placeholder(self):
        # The column's contract, in one case: an empty cell means this rule
        # found no candidate, and it is written as the empty string rather than
        # as a `-` or a `none` a reader could mistake for a value. A placeholder
        # here would also stop `csv.DictReader` giving a falsy field, which is
        # the check every downstream reader makes.
        empty = [r for r in census_rows("paged") if not r["earlier_record"]]
        self.assertTrue(empty, "every paged row is named, so the empty case is "
                              "not being exercised at all")
        for r in empty:
            self.assertEqual(r["earlier_record"], "")
            self.assertNotIn(r["earlier_record"], ("-", "none", "None", "n/a"))


class WhatThisDoesNotClaim(unittest.TestCase):
    """Pinned because both are cheap to make by accident in prose, and because
    the write-up is where a reader would look for them."""

    def test_no_register_status_is_named_by_this_change(self):
        registers = (ANNOTATIONS / "registers.yaml").read_text()
        for token in ("earlier_record", "earlier-record"):
            self.assertNotIn(token, registers)

    def test_the_writeup_states_the_blind_spots_and_the_column_not_filter(self):
        text = squeezed(WRITEUP)
        for phrase in ("a column, not a filter",
                       "fires wherever any byte precedes a paged-shaped byte",
                       "cannot see data",
                       "a name is not a verdict"):
            self.assertIn(phrase, text)

    def test_the_writeup_reports_the_tiebreak_as_a_choice_among_alternatives(self):
        # The word that keeps this from being a verdict. `converges_from()`'s
        # own docstring says a site everybody syncs onto is not thereby real,
        # and a write-up that presented 18/18 as a result rather than as a
        # choice among named alternatives would be overclaiming by 18 rows.
        text = squeezed(WRITEUP)
        for phrase in ("stated choice among named alternatives",
                       "not thereby real", "nearest start", "furthest end",
                       "furthest back"):
            self.assertIn(phrase, text)

    def test_the_writeup_makes_no_behavioural_claim(self):
        text = WRITEUP.read_text()
        self.assertIn("No register `status:`, no row added to or removed from",
                      text)

    def test_the_writeups_figure_table_matches_the_committed_censuses(self):
        # The table is the write-up's re-measurement, and a re-measurement is
        # the one figure a reader cannot check without running the tool. Held
        # here so it goes red when a census moves rather than becoming a
        # sentence that was true once. Read back out of the markdown table
        # rather than matched as prose, so a reworded sentence is not a
        # failure and a changed number is.
        counts = {}
        for line in WRITEUP.read_text().splitlines():
            m = FIGURES.match(line)
            if m:
                counts[m.group(1)] = (int(m.group(2).replace(",", "")),
                                      int(m.group(3).replace(",", "")),
                                      int(m.group(4).replace(",", "")))
        # The table keys on the file's own name, so the census is looked up by
        # that rather than by this module's short alias for it -- two spellings
        # for one file is a mapping somebody has to keep right, and a write-up
        # that renamed a column would otherwise fail on a missing dict key
        # rather than on a figure that moved.
        by_name = {path.name: (name, path) for name, (path, _n) in CENSUSES.items()}
        self.assertEqual(sorted(counts), sorted(by_name))
        for filename, (rows, with_candidate, without) in counts.items():
            name = by_name[filename][0]
            actual = census_rows(name)
            self.assertEqual(rows, len(actual), filename)
            self.assertEqual(with_candidate,
                             sum(1 for r in actual if r["earlier_record"]),
                             filename)
            self.assertEqual(without, rows - with_candidate, filename)


if __name__ == "__main__":
    unittest.main()
