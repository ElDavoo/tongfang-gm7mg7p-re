#!/usr/bin/env python3
"""Unit checks for the call-target seed framing adjudication (issue #1280).

`docs/findings/call-target-seed-frames.md` publishes the population of seeds
`build_ec_decompile.py` mints inside a longer instruction, and
`call_target_seed_frames.py` derives it. This file holds that derivation to
three oracles the tool cannot grade itself against:

  * **the image.** The four sites the write-up reads by hand -- `0x1706`,
    `0x0064`, `0x0512` and the `0x012F` counter-example -- are re-derived from
    `ec/firmware/GMxMGxx_11.800` and compared against the table transcribed
    here rather than imported, so the verdicts are measured against a reading
    somebody wrote down rather than against whatever the CSV happens to hold.
  * **an ablation.** The threshold is chosen over three named alternatives, and
    each is asserted to *lose* on at least one seed of the committed population.
    Pinning only the winner's outcome would let a refactor swap in a simpler
    rule that agrees on this image, which is the whole of what a threshold is.
  * **a built fixture.** The two ways a verdict comes out, laid down on scratch
    bytes rather than anchored in the firmware, for `test_walk_branch_arms.py`'s
    stated reason: a fixture at a real address keeps testing what it was written
    to test only until those bytes change.

**What this suite deliberately does not do.** It does not re-run the census scan
that wrote `bank-call-targets.csv`. Re-running `audit_call_targets.py` would
assert the tool against itself and let a regenerated census disagree with the
image, which is the reason `test_paged_trampoline_framing.py` gives for the same
omission. The committed CSVs are read for the *shape* claims and never for the
verdicts' correctness, which are re-derived from the image on every run.

**No census row count is pinned here.** `test_earlier_record_column.py` already
pins all three, and the absolute one again in `build_ec_decompile.py`'s own
`--self-test`; a fourth copy in a suite that writes none of them would be a
figure nothing here can move. What this suite holds instead is the *relation*
that a filter would break -- that the attribution still emits every seed, and
that bucket C is still seeded by nothing.
"""
import csv
import importlib.util
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import call_target_seed_frames as ctsf

# The census, read by predicate rather than by count. `build_ec_decompile` is
# loaded by path because it is a 5,000-line script whose module-level work none
# of these cases need; importing it whole would make the suite slow for no
# assertion.
_spec = importlib.util.spec_from_file_location(
    "build_ec_decompile", HERE / "build_ec_decompile.py")
bedc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bedc)

ANNOTATIONS = HERE.parent / "annotations"
WRITEUP = ROOT / "docs" / "findings" / "call-target-seed-frames.md"
IMAGE = (HERE.parent / "firmware" / "GMxMGxx_11.800").read_bytes()

# The three censuses, by file, and no row counts beside them. The row counts of
# all three are pinned in `test_earlier_record_column.py` and the absolute one in
# `build_ec_decompile.py`'s own `--self-test`, and a fourth copy in a suite that
# does not write any of them would be a figure nothing here can move. What this
# suite needs from the census is the *shape* of bucket C and the fact that the
# attribution still emits every seed -- both read below as predicates, so they go
# red when the rule changes rather than when a census is regenerated.
CENSUSES = {
    "absolute": ANNOTATIONS / "bank-call-targets.csv",
    "paged": ANNOTATIONS / "bank-paged-call-targets.csv",
    "relative": ANNOTATIONS / "bank-relative-branch-targets.csv",
}

# The four sites the write-up reads by hand, transcribed rather than imported
# from the CSV, for the reason `test_earlier_record_column.py` gives its `OWNERS`
# table: a table that read itself back from the file under test could not
# disagree with it, which is the failure this suite exists to catch. Two suites
# holding one table is cheaper than one suite grading its own premise.
#
# (target, spanning record offset, spanning record bytes, spanning mnemonic,
#  walk lands, walk steps over, want verdict)
SITES = (
    (0x1706, 0x1705, "02 11 00", "ljmp 0x1100", 2, 22, "mid-instruction"),
    (0x0064, 0x0063, "02 11 86", "ljmp 0x1186", 1, 23, "mid-instruction"),
    (0x0512, 0x0511, "b4 01 03", "cjne a,#0x01,0x0517", 0, 24, "mid-instruction"),
    (0x012F, 0x012E, "b0 90", "anl c,/p1.0", 23, 1, "entry-under-walk"),
)

# The three thresholds the majority rule is chosen over, as a name and a
# predicate over the walk's pair. A threshold with no named alternatives is not a
# choice, it is an accident that happens to be stable, so the alternatives are
# part of the claim and each is asserted to *lose* below.
#
# The tie is decided the same way `verdict_for()` decides it -- a tie is not
# landed -- rather than by folding `>=` into one of the alternatives and leaving
# the reader to work out which side of the line it fell. `bank1 0xF018` is the
# one tie in the population and it is what "no anchor steps over" loses on.
ALT_THRESHOLDS = (
    ("any anchor lands", lambda onto, over: onto > 0),
    ("no anchor steps over", lambda onto, over: onto >= over and onto > 0),
    ("a fixed count", lambda onto, over: onto > ctsf.BACK // 2),
)

# The seed each alternative is asserted to lose on, as (program, target). Named
# at module level for the reason `test_earlier_record_column.py` gives its
# `ABLATION_SITE`: `check_doc_figure_pins.py` reads every int constant inside an
# asserting call across `ec/tools/*.py` as a pin for a figure in some document,
# so a bare address written into an `assertEqual` would make this module a
# second, uncited pin for a value no document has claimed. These are addresses,
# not figures, and the rule they hold is the one the module docstring states.
ALT_LOSES_ON = {
    "any anchor lands": ("bank0", "0x1706"),
    "no anchor steps over": ("bank1", "0xF018"),
    "a fixed count": ("bank1", "0x8007"),
}

# The one seed in the population where the anchors tie, and where `0xF018` is
# therefore the case the tie-break direction is decided on. Named rather than
# found by a scan so a change to the population cannot quietly move the tie to
# an address nothing here has read.
TIE_SEED = ("bank1", "0xF018")

def census_rows(name):
    with open(CENSUSES[name], newline="") as f:
        return list(csv.DictReader(f))


def committed_frames():
    return ctsf.read_csv(ctsf.FRAMES)


def frames_by_key():
    return {(r["program"], r["target"]): r for r in committed_frames()}


def squeezed(path):
    """A document's prose, with its line wrapping collapsed.

    Prose assertions only, and this is what makes them possible. Markdown is
    hard-wrapped, so a phrase that reads as one sentence in the source is three
    lines in the file, and `assertIn` on the raw text would fail on the wrapping
    rather than on the claim."""
    return " ".join(path.read_text().replace("**", "").lower().split())


class TheWorkedSitesReDerive(unittest.TestCase):
    """The four sites the write-up reads by hand, re-derived from the image.

    Transcribed rather than read back out of the published CSV, so these cases
    measure the derivation against a reading somebody wrote down rather than
    against the file the derivation wrote."""

    def test_each_site_is_covered_by_the_record_the_write_up_names(self):
        earlier = ctsf.audit_module().earlier_record
        for target, start, hexbytes, mnemonic, _o, _v, _want in SITES:
            with self.subTest(target="%#06x" % target):
                self.assertEqual(
                    earlier(IMAGE, target, ctsf.REGION_FLOOR["common"]),
                    "0x%05X %s %s" % (start, hexbytes, mnemonic))

    def test_each_covering_record_really_spans_its_site(self):
        # The strictness is #54's, re-asserted here so a `j <= off` slip is a red
        # run rather than a predicate that quietly starts naming the record that
        # *begins* at the site -- which for every one of these is the site itself.
        import disasm8051
        for target, start, _hexbytes, _mnemonic, _o, _v, _want in SITES:
            with self.subTest(target="%#06x" % target):
                span = disasm8051.OPCODE_LEN[IMAGE[start]]
                self.assertTrue(start < target < start + span)
                self.assertEqual(IMAGE[start:start + span].hex(" "),
                                 dict((t, b) for t, _s, b, _m, _o, _v, _w
                                      in SITES)[target])

    def test_each_site_gets_the_verdict_the_write_up_states(self):
        for target, _start, _b, _m, onto, over, want in SITES:
            with self.subTest(target="%#06x" % target):
                got = (ctsf.windowed_walk(IMAGE, target, ctsf.BACK))
                self.assertEqual(got, (onto, over))
                self.assertEqual(ctsf.verdict_for(onto, over, True), want)

    def test_the_comitted_csv_holds_the_same_verdicts(self):
        by_key = frames_by_key()
        for target, _start, _b, _m, _o, _v, want in SITES:
            with self.subTest(target="%#06x" % target):
                # Both bank programs seed a common-area target, so both rows
                # exist and both must carry the verdict -- a rule that filed one
                # program's seed differently from the other's would be reading
                # something other than the bytes.
                for program in ("bank0", "bank1"):
                    row = by_key.get((program, "0x%04X" % target))
                    self.assertIsNotNone(row, "%s %s" % (program, target))
                    self.assertEqual(row["verdict"], want)

    def test_the_walk_landed_on_012f_and_not_on_the_others(self):
        # The distinction the whole rule turns on, asserted as the counts rather
        # than as a verdict: three of the four sites are stepped over by most
        # anchors and one is landed on by nearly all of them, and a rule that
        # treated those two shapes alike would pass every verdict assertion above
        # while adjudicating none of them.
        landed = {target: onto for target, _s, _b, _m, onto, _o, _w in SITES
                  if onto > ctsf.BACK - onto}
        self.assertEqual(landed, {0x012F: 23})


class TheCounterCase(unittest.TestCase):
    """`0x012F`: the case that makes the rule honest.

    A seed that trips the predicate and is a real entry anyway. Every assertion
    above would pass for a rule that filed every predicate trip as
    `mid-instruction`; this class is what stops that."""

    def test_the_site_trips_the_predicate(self):
        # Asserted positively, with the bytes, rather than as "not empty": the
        # whole case is that 0x012E pairs as `b0 90` and the pairing is what
        # makes a real routine look mid-instruction.
        earlier = ctsf.audit_module().earlier_record
        record = earlier(IMAGE, 0x012F, ctsf.REGION_FLOOR["common"])
        self.assertTrue(record, "the counter-case no longer trips the predicate")
        self.assertEqual(IMAGE[0x012E:0x0130].hex(" "), "b0 90")

    def test_the_rule_keeps_it(self):
        onto, over = ctsf.windowed_walk(IMAGE, 0x012F, ctsf.BACK)
        self.assertEqual(ctsf.verdict_for(onto, over, True), "entry-under-walk")

    def test_it_is_still_seeded_and_still_labelled(self):
        # The listing survives today because seed_rows() sorts `annotation`
        # ahead of `call-target`. This asserts the seed is still emitted *and*
        # still carries its label, so a change that quietly started filtering the
        # labelled seeds is a red run here rather than a shorter index.csv that
        # nobody notices.
        census = bedc.call_target_rows()
        seeds = {addr for addr, _basis in bedc.call_target_seeds("bank0", census)[0]}
        self.assertIn(0x012F, seeds)
        self.assertEqual(bedc.seed_basis_labels().get(("bank0", "0x012F")),
                         "entry-under-walk")


class TheThresholdIsAChoice(unittest.TestCase):
    """The part nothing specifies, and which therefore has to be justified rather
    than asserted. `converges_from()`'s own docstring says a site everybody syncs
    onto is not thereby real, so the threshold picks a better-evidenced reading
    and never adjudicates the seed."""

    def reclassify(self, onto, over, has_listing, lands):
        """What this suite says the verdict would be under an alternative.

        Written out rather than imported, so the ablation states the rule it is
        testing instead of re-running `verdict_for()` -- which is the
        implementation under test, and asserting an alternative against it would
        compare two spellings of one function."""
        if lands(onto, over):
            return "entry-under-walk"
        if has_listing:
            return "mid-instruction"
        return "unread"

    def has_listing(self, row):
        _by_program, by_addr = ctsf.index_rows()
        return row["target"].lstrip("0x").zfill(4) in by_addr

    def test_every_named_alternative_loses_on_the_seed_it_is_named_for(self):
        by_key = frames_by_key()
        for name, lands in ALT_THRESHOLDS:
            program, target = ALT_LOSES_ON[name]
            with self.subTest(rule=name):
                self.assertIn((program, target), by_key,
                              "%s is named for a seed the population does not "
                              "adjudicate, so the ablation would prove nothing"
                              % name)
                row = by_key[(program, target)]
                got = self.reclassify(int(row["onto"]), int(row["over"]),
                                      self.has_listing(row), lands)
                self.assertNotEqual(got, row["verdict"],
                                    "%s does not lose on %s %s: it re-derives "
                                    "%r, which is the verdict already published"
                                    % (name, program, target, got))

    def test_each_alternative_disagrees_with_the_rule_somewhere_in_the_population(self):
        # The ablation, and the half that makes it one: pinning only "the winner
        # gets every row" would pass for a rule that gets them all by a different
        # route, which is exactly the refactor this is here to stop.
        for name, lands in ALT_THRESHOLDS:
            with self.subTest(rule=name):
                wrong = 0
                for row in committed_frames():
                    got = self.reclassify(int(row["onto"]), int(row["over"]),
                                          self.has_listing(row), lands)
                    if got != row["verdict"]:
                        wrong += 1
                self.assertGreater(wrong, 0,
                                   "%s re-derives the whole population, so it "
                                   "is not a rule this threshold can be said to "
                                   "beat" % name)

    def test_the_tie_goes_the_way_the_rule_says_and_not_the_way_a_tie_looks(self):
        # `0xF018` is the population's only tie, and it is what decides the
        # direction of the inequality. Asserted as its own case because a rule
        # reading `>=` instead of `>` agrees with this one on every other seed
        # in the population -- so without this case the tie-break direction is
        # unheld, and it is exactly the sort of `>=` a refactor reaches for.
        row = frames_by_key()[TIE_SEED]
        onto, over = int(row["onto"]), int(row["over"])
        self.assertEqual((onto, over), (onto, onto))
        self.assertEqual(ctsf.verdict_for(onto, over, True), "mid-instruction",
                         "a tie is not 'landed', so this seed is not an entry "
                         "under the walk")
        self.assertEqual(row["verdict"], "mid-instruction")


class TheRegionFloorAndTheWindow(unittest.TestCase):
    """Two edges the walk has, where a slip is invisible in the output.

    A window running past a region's floor reads a neighbouring address space, and
    a window padded with zeros decodes `nop` where this firmware has a real byte.
    Both produce a plausible-looking pair and neither is caught by a verdict."""

    def test_no_published_row_was_walked_past_its_own_regions_floor(self):
        for key, row in frames_by_key().items():
            with self.subTest(seed=key):
                total = int(row["onto"]) + int(row["over"])
                floor = ctsf.REGION_FLOOR[row["region"]]
                target = int(row["target"], 16)
                off = ctsf.offset_for_runtime(target, row["region"])
                self.assertLessEqual(total, min(ctsf.BACK, off - floor))
                self.assertGreater(total, 0)

    def test_every_published_row_counts_a_whole_number_of_anchors(self):
        # A row whose counts do not add up to the window it was given is a walk
        # handed a truncated buffer, and the pair it reports then reads as
        # unanimity rather than as the handful of anchors it saw.
        for key, row in frames_by_key().items():
            with self.subTest(seed=key):
                onto, over = int(row["onto"]), int(row["over"])
                self.assertGreater(onto + over, 0)
                self.assertLessEqual(onto + over, ctsf.BACK)

    def test_the_window_agrees_with_a_whole_image_walk(self):
        # The strong form of the window question, and it is the one worth
        # holding: `converges_from()` run over the whole image is the reading
        # every other count in this repository takes, so a windowed walk that
        # disagreed with it would put this tool's numbers in a different unit
        # from `counter_sweep_entry.py`'s and `audit_call_targets.py`'s.
        import disasm8051
        for row in committed_frames():
            with self.subTest(seed=(row["program"], row["target"])):
                target = int(row["target"], 16)
                off = ctsf.offset_for_runtime(target, row["region"])
                floor = ctsf.REGION_FLOOR[row["region"]]
                back = min(ctsf.BACK, off - floor)
                self.assertEqual(ctsf.windowed_walk(IMAGE, off, back),
                                 disasm8051.converges_from(IMAGE, off, back),
                                 "the windowed walk and a whole-image walk "
                                 "disagree, so this population's onto/over "
                                 "columns are not the same measure as the rest "
                                 "of the tree's")

    def test_a_bank_window_seed_is_walked_against_its_own_banks_bytes(self):
        # The two bank programs' images differ above 0x8000, so a window that
        # read the common area's copy would frame both identically and the
        # per-program verdict would be a function of the address alone. The
        # common area is the same bytes in both, which is why the four worked
        # sites cannot catch this and a bank-window seed can.
        rows = [r for r in committed_frames() if r["region"] != "common"]
        self.assertTrue(rows, "no bank-window seed, so the per-program walk is "
                              "not being exercised")
        differing = 0
        for row in rows:
            off = ctsf.offset_for_runtime(int(row["target"], 16), row["region"])
            other = 0x10000 if row["region"] == "bank0" else 0x08000
            if IMAGE[off:off + ctsf.OPCODE_SLACK] != IMAGE[other:other + ctsf.OPCODE_SLACK]:
                differing += 1
        self.assertGreater(differing, 0,
                           "no bank-window seed sits where the two banks' bytes "
                           "differ, so reading the wrong bank would go unnoticed")


class TheIndexLookup(unittest.TestCase):
    """Which index row stands for a seed's listing, and why the obvious answer is
    wrong for a minority of seeds.

    `join_index()` folds a common-area function into one `common` row only where
    both bank programs agree on its address, name and size, and keeps both
    bank-scoped rows where they disagree. A lookup on the folded name alone finds
    no listing at `bank0 0x031C` or `bank0 0x703A` and files seeds that do have
    one as `unread`, which is how this case's addresses were found."""

    # Common-area addresses the export kept under a bank-scoped row. Named rather
    # than found by a scan, so that if a future re-export folds them the case says
    # so instead of quietly finding nothing and passing.
    KEPT_UNDER_A_BANK = (("bank0", "0x031C"), ("bank0", "0x703A"))

    def test_a_common_area_seed_finds_its_listing_under_either_spelling(self):
        by_program, by_addr = ctsf.index_rows()
        for program, target in self.KEPT_UNDER_A_BANK:
            with self.subTest(seed=(program, target)):
                addr = target.lstrip("0x").zfill(4)
                self.assertIn(addr, by_addr,
                              "no committed listing covers this address at all, "
                              "so the case is not being exercised")
                # The row is filed under a bank, not under the folded name -- and
                # that is the whole reason the lookup cannot key on `common`.
                self.assertNotIn(("common", addr), by_program,
                                 "this address is folded after all, so the "
                                 "reason the lookup is by address has gone")
                self.assertTrue(by_addr[addr])

    def test_no_verdict_rests_on_another_programs_row(self):
        # `ec/decompiled/index.csv` also carries the PD image, whose addresses
        # are the same numbers in a different address space. `pd 0x1229` is the
        # *only* index row at that address, so an unscoped by-address lookup found
        # it and reported a main-EC seed with no listing of its own as
        # `mid-instruction` -- another program's bytes standing in for this
        # one's. `listing_at()` is the exclusion and this is what holds it.
        #
        # The case that matters is the address with *only* a foreign row: a `pd`
        # row beside a main-EC one is harmless, since the main-EC row is what the
        # lookup returns either way.
        _by_program, by_addr = ctsf.index_rows()
        foreign_only = []
        for row in committed_frames():
            target = int(row["target"], 16)
            rows = by_addr.get("%04X" % target, [])
            if rows and not [r for r in rows
                             if r["program"] in ctsf.MAIN_EC_PROGRAMS]:
                foreign_only.append(row)
        for row in foreign_only:
            with self.subTest(seed=(row["program"], row["target"])):
                self.assertIsNone(ctsf.listing_at(by_addr, int(row["target"], 16)),
                                  "a foreign program's row is standing in for a "
                                  "main-EC listing")
        # And the case is real rather than vacuous: the address that motivated the
        # exclusion is in the published population and has only a `pd` row.
        self.assertIn(("bank0", "0x1229"), frames_by_key())
        self.assertIsNone(ctsf.listing_at(by_addr, 0x1229))
        self.assertEqual(
            [r["program"] for r in by_addr["1229"]], ["pd"])

    def test_the_verdict_agrees_with_the_frame_table_named_without_a_row_published(self):
        # `named-without-a-row.md` §5 publishes four addresses as
        # `mid-instruction`, read by its own walk, and this rule classes all four
        # the same way from a population it derives independently. Neither
        # reading consulted the other, so the agreement is corroboration rather
        # than a restatement -- and it is the check that would have caught the
        # lookup above, since three of the four kept their bank-scoped rows.
        read_by_hand = (("bank0", "0x031C"), ("bank1", "0x031C"),
                        ("bank1", "0x703A"), ("bank0", "0x0512"))
        by_key = frames_by_key()
        for program, target in read_by_hand:
            with self.subTest(seed=(program, target)):
                row = by_key.get((program, target))
                self.assertIsNotNone(row,
                                     "%s %s is in the published frame table and "
                                     "not in the affected population, so the "
                                     "agreement is no longer being exercised"
                                     % (program, target))
                self.assertEqual(row["verdict"], "mid-instruction")
                self.assertEqual((int(row["onto"]), int(row["over"])),
                                 (0, ctsf.BACK),
                                 "the published table says all 24 anchors step "
                                 "over this address")


    def test_every_index_address_is_the_width_the_lookup_formats(self):
        # `listing_at()` formats a target as four hex digits and looks it up in a
        # dict `index_rows()` keyed on the address as the file spells it. If the
        # file ever spelled one differently the lookup would return None for an
        # address that has a listing, and every such seed would silently become
        # `unread` -- a smaller verdict count and nothing to show for it.
        _by_program, by_addr = ctsf.index_rows()
        self.assertTrue(by_addr)
        widths = {len(addr) for addr in by_addr}
        self.assertEqual(widths, {len("%04X" % 0)},
                         "the index spells an address some other way than the "
                         "lookup formats it, so the two cannot meet")
        # And the lookup finds a listing at every address the export has a
        # *main-EC* row for. Not at every address in the dict: an address held
        # only by a `pd` row is a different program's function, and a seed with
        # no listing of its own is exactly what `unread` is for.
        for addr, rows in by_addr.items():
            with self.subTest(addr=addr):
                has_main = any(r["program"] in ctsf.MAIN_EC_PROGRAMS
                               for r in rows)
                self.assertEqual(bool(ctsf.listing_at(by_addr, int(addr, 16))),
                                 has_main)


class NothingDownstreamMoved(unittest.TestCase):
    """The issue's done condition: a report, not a filter. The census keeps every
    row, the seed set keeps every seed, and the export is untouched."""

    def test_each_census_still_carries_a_target_and_a_region(self):
        # The shape, not the size. The row counts of all three are pinned in
        # `test_earlier_record_column.py`, and pinning a fourth copy here would
        # assert a figure this suite cannot move; what a filter in this change
        # would break is the *attribution*, which the two cases below read off
        # the census directly.
        for name in CENSUSES:
            with self.subTest(census=name):
                rows = census_rows(name)
                self.assertTrue(rows)
                for column in ("region", "target"):
                    self.assertIn(column, rows[0])
                    self.assertTrue(all(row[column] for row in rows))

    def test_the_bucket_c_rows_are_still_named_by_nobody(self):
        # #48's population, by predicate rather than by count. The predicate is
        # `call_target_seeds()`'s own, re-derived here from the census: a target
        # at or above 0x8000 that a *common-area* row names and no bank row does
        # is seeded by nothing. The second half of that predicate is the whole
        # subtlety -- most of those targets are ALSO named by a bank row, which
        # seeds them normally, so a bucket read as "common-area row with a high
        # target" would call a seeded seed unattributed and this would be a
        # failure about the bucket rather than about this change.
        rows = census_rows("absolute")
        high_common = {int(r["target"], 16) for r in rows
                       if r["region"] == "common"
                       and int(r["target"], 16) >= 0x8000}
        bank_named = {int(r["target"], 16) for r in rows
                      if r["region"] != "common"}
        unseeded = high_common - bank_named
        self.assertTrue(unseeded,
                        "no bucket-C rows, so the separation is not being "
                        "exercised")
        seeds, unattributed = ctsf.population()
        self.assertEqual(unattributed, len(high_common))
        self.assertFalse(unseeded & {t for _p, t in seeds},
                         "a bucket-C target reached the seeded population")
        # The complementary half, so the count above is not a coincidence: every
        # target the bucket does seed is one a bank row named.
        self.assertEqual(high_common & {t for _p, t in seeds}, high_common
                         & bank_named)

    def test_the_seed_set_is_not_shorter_than_the_population(self):
        # A filter would show up here first and most cheaply: the population the
        # tool derives must still contain every target the attribution seeds.
        census = bedc.call_target_rows()
        for bank in ("bank0", "bank1"):
            emitted = {addr for addr, _b in
                       bedc.call_target_seeds(bank, census)[0]}
            derived = {t for p, t in ctsf.population()[0] if p == bank}
            self.assertTrue(emitted <= derived,
                            "%s: %d seed(s) the attribution emits are not in the "
                            "derived population" % (bank, len(emitted - derived)))

    def test_the_export_is_untouched(self):
        # Every committed .c and .asm still carries the exporter's do-not-edit
        # header. This change reads the export and writes none of it, and a
        # `--mode rebuild-project` here would collide with every other branch on
        # the 7 MB EC database -- so the cheap, mechanical form of "untouched" is
        # that every generated file still says so.
        decompiled = HERE.parent / "decompiled"
        for name in ("index.csv", "listing-index.csv"):
            self.assertTrue((decompiled / name).is_file(), name)
        sample = sorted(decompiled.glob("*/0*.asm"))[:20]
        self.assertTrue(sample, "no committed listing to sample")
        for path in sample:
            with self.subTest(listing=path.name):
                self.assertIn("do not edit", path.read_text().splitlines()[1])

    def test_no_published_row_is_a_seed_the_predicate_does_not_fire_on(self):
        # The other half of "only the affected seeds are published": a row for a
        # seed nothing objects to would put a verdict in the file that no reading
        # supports.
        earlier = ctsf.audit_module().earlier_record
        for row in committed_frames():
            with self.subTest(seed=(row["program"], row["target"])):
                target = int(row["target"], 16)
                self.assertTrue(
                    earlier(IMAGE, ctsf.offset_for_runtime(target, row["region"]),
                            ctsf.REGION_FLOOR[row["region"]]))

    def test_every_published_row_is_address_deduped_by_program_not_globally(self):
        # A common-area target is one address and two seeds. Collapsing them
        # would halve the population; not keying on the program would merge two
        # different seeds into one row. Both are the same mistake in opposite
        # directions, so both directions are asserted.
        rows = committed_frames()
        keys = [(r["program"], r["target"]) for r in rows]
        self.assertEqual(len(set(keys)), len(keys))
        common = [r for r in rows if r["region"] == "common"]
        by_target = {}
        for row in common:
            by_target.setdefault(row["target"], []).append(row["program"])
        paired = {t: p for t, p in by_target.items() if sorted(p) == ["bank0", "bank1"]}
        self.assertTrue(paired,
                        "no common-area seed appears in both bank programs, so "
                        "the per-program key is not being exercised")


class TheRatchetIsLive(unittest.TestCase):
    """A check that has never been seen to reject is not known to reject.

    Every case here builds a disagreement between a committed file and a
    derivation and asserts the check names the seed, because a bare "the
    populations differ" would be a failure a reader has to reproduce before they
    can act on it."""

    def derived(self):
        return ctsf.frames(IMAGE)

    def test_a_file_that_agrees_with_the_derivation_passes(self):
        rows, _unattributed, _total = self.derived()
        self.assertEqual(ctsf.frame_problems(rows, rows), [])

    def test_a_reverted_verdict_is_reported_and_names_the_seed(self):
        rows, _u, _t = self.derived()
        target = next(r for r in rows if r["verdict"] == "mid-instruction")
        committed = [dict(r) for r in rows]
        committed[rows.index(target)] = dict(target, verdict="entry-under-walk")
        got = ctsf.frame_problems(committed, rows)
        self.assertEqual(len(got), 1, str(got))
        self.assertIn(target["target"], got[0])
        self.assertIn(target["program"], got[0])
        self.assertIn("--write", got[0])

    def test_a_new_mid_instruction_seed_is_reported_and_names_the_covering_record(self):
        rows, _u, _t = self.derived()
        invented = list(rows) + [{"program": "bank0", "target": "0xFFF0",
                                  "region": "common", "verdict": "unread",
                                  "covering_record": "0x0FFEE 74 22 mov a,#0x22",
                                  "onto": "0", "over": "4"}]
        got = ctsf.frame_problems(rows, invented)
        self.assertEqual(len(got), 1, str(got))
        self.assertIn("0xFFF0", got[0])
        self.assertIn("0x0FFEE", got[0])

    def test_a_row_the_derivation_no_longer_produces_is_reported(self):
        rows, _u, _t = self.derived()
        dropped = [dict(r) for r in rows[:-1]]
        got = ctsf.frame_problems(rows, dropped)
        self.assertEqual(len(got), 1, str(got))
        self.assertIn(rows[-1]["target"], got[0])
        self.assertIn(rows[-1]["covering_record"], got[0],
                      "the report should name the record that used to span it, "
                      "or a reader cannot tell which rule changed")

    def test_a_changed_walk_count_is_reported_even_though_the_verdict_is_not(self):
        # The walk's pair is the evidence every verdict rests on, so a row whose
        # counts moved but whose class did not is still a changed reading.
        rows, _u, _t = self.derived()
        committed = [dict(r) for r in rows]
        committed[0] = dict(committed[0], onto=str(int(committed[0]["onto"]) + 1))
        got = ctsf.frame_problems(committed, rows)
        self.assertEqual(len(got), 1, str(got))
        self.assertIn("onto", got[0])

    def test_a_missing_file_and_a_wrong_header_are_each_reported_once(self):
        # Once, rather than as one difference per row: a file this tool did not
        # write has no rows to compare, and reporting hundreds of differences
        # that all mean "you are looking at the wrong file" is how a ratchet
        # gets ignored.
        import tempfile
        with tempfile.TemporaryDirectory() as work:
            absent = os.path.join(work, "absent.csv")
            self.assertEqual(len(ctsf.file_problems(absent)), 1)
            wrong = os.path.join(work, "wrong.csv")
            with open(wrong, "w", newline="") as f:
                f.write("program,target\nbank0,0x0002\n")
            got = ctsf.file_problems(wrong)
            self.assertEqual(len(got), 1, str(got))
            self.assertIn("header", got[0])

    def test_the_committed_file_is_this_tools_own_and_derives_agree_with_it(self):
        # The end-to-end claim: the file on disk is the file this run derives.
        # Every other case here tests one direction of the ratchet against a
        # hand-built disagreement, and this is the one that says the shipped
        # state is green.
        self.assertEqual(ctsf.file_problems(), [])
        rows, _unattributed, _total = self.derived()
        self.assertEqual(ctsf.frame_problems(committed_frames(), rows), [])


class WhatThisDoesNotClaim(unittest.TestCase):
    """Pinned because both are cheap to make by accident in prose, and because the
    write-up is where a reader would look for them."""

    def test_no_register_status_is_named_by_this_change(self):
        registers = (ANNOTATIONS / "registers.yaml").read_text()
        for token in ("call-target-seed-frames", "call_target_seed_frames"):
            self.assertNotIn(token, registers)

    def test_no_annotation_row_names_an_address_the_rule_never_looked_at(self):
        # The write-up claims this change adds no `ghidra-functions.csv` row. The
        # row that backs an entry is the whole of what makes it evidence-backed,
        # and adding one here would settle a framing question by fiat. What is
        # held is the shape rather than the size: every row still resolves an
        # address and carries the evidence the annotation layer requires.
        with open(ANNOTATIONS / "ghidra-functions.csv", newline="") as f:
            annotations = list(csv.DictReader(f))
        self.assertTrue(annotations)
        for row in annotations:
            self.assertTrue(int(row["addr"], 16) >= 0, row.get("addr"))
        self.assertTrue(any(row["evidence"].strip() for row in annotations),
                        "no annotation row carries an evidence citation, so the "
                        "export's own content guard is not being exercised")

    def test_the_writeup_corrects_the_issue_figure_in_place(self):
        # The issue's third figure does not reproduce and is not carried forward.
        # A retraction stays visible beside its replacement, per the calibration
        # rule, so both the wrong figure and the refusal to reconcile it are
        # asserted rather than only the replacement.
        text = squeezed(WRITEUP)
        self.assertIn("155", text)
        self.assertIn("does not reproduce", text)
        self.assertIn("does not state which one it used", text)

    def test_the_writeup_leaves_the_rebuild_and_the_later_sites_open(self):
        text = squeezed(WRITEUP)
        for phrase in ("--mode rebuild-project",
                       "rebuild has not been run",
                       "not call-target seeds"):
            self.assertIn(phrase, text)

    def test_the_writeup_makes_no_behavioural_claim(self):
        text = squeezed(WRITEUP)
        for phrase in ("nothing here was observed on hardware or in windows",
                       "no register",
                       "about framing only"):
            self.assertIn(phrase, text)

    def test_the_writeup_names_the_threshold_and_its_alternatives(self):
        # The word that keeps this from being a verdict, and the same discipline
        # `test_earlier_record_column.py` holds for the tie-break it chose: a
        # write-up presenting one threshold as the answer rather than as a choice
        # among named alternatives would be overclaiming the whole population.
        text = squeezed(WRITEUP)
        for phrase in ("any anchor lands", "no anchor steps over",
                       "a fixed count", "not thereby real"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()