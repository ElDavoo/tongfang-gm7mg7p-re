#!/usr/bin/env python3
"""Cases for `nested_frame_census.py`.

The tool's own `--self-test` carries the readings and the refusals, and this
drives it. What is here is the half a self-test cannot be: the tool's *shapes*
held directly, so a census that had quietly stopped being a partition, or a
`bucket_of()` that answered a third name, or a note that had started failing
`--check`, is caught by a named case rather than by a count moving.

**No count of the tree is asserted anywhere in this file.** The figure the tool
reports has already moved once between the hand count §8 carried and the
measurement, and a suite that pinned it would have gone red on a merge that
added a row and told the implement stage to fix a correct tool. What is asserted
is the claim and the relation: these named rows nest in these containers, the
two buckets partition the edges, the two readings of "contained" are both
reported and differ, and every refusal still refuses.

Everything here reads committed files. No Ghidra, no hardware, no Windows, no
network; the fixture tree is built in a `tempfile` from the real firmware with a
handful of bytes replaced, which is what `second_copy_census.py`'s fixtures do
and for the reason its docstring gives.
"""
import collections
import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import nested_frame_census as census  # noqa: E402
from second_copy_census import norm_addr, read_csv  # noqa: E402


def committed():
    """The census over the committed tree, read once per class that needs it."""
    return census.census(read_csv(census.INDEX_CSV), read_csv(census.ANNOTATIONS))


class TheSelfTest(unittest.TestCase):
    """The tool's own self-test, which is where the readings live."""

    def test_it_passes(self):
        # Its transcript goes to a buffer rather than to this suite's own
        # output: the readings are two dozen lines, and a reader running the
        # suite would otherwise have to find this suite's own result underneath
        # them. The exit code is the whole of the assertion.
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = census.self_test()
        self.assertEqual(rc, 0, buf.getvalue()[-2000:])


class TheVocabularies(unittest.TestCase):
    """Closed, and the closure is what makes the splits partitions."""

    def test_there_are_three_verdicts_and_two_buckets(self):
        self.assertEqual(census.VERDICTS,
                         ("nested", "after-a-function", "unframed"))
        self.assertEqual(census.BUCKETS,
                         ("same-address", "listing-opens-below-address"))

    def test_a_bucket_is_named_for_what_was_measured(self):
        # Neither name is a conclusion about whether the container frames the
        # bytes. `listing-opens-below-address` in particular says the listing
        # reaches back past its entry point, not that the container fails to
        # hold what it is reported as holding.
        for name in census.BUCKETS:
            self.assertNotIn("not", name)
            self.assertNotIn("wrong", name)
            self.assertNotIn("bad", name)

    def test_a_listing_that_opens_above_its_own_address_is_not_a_bucket(self):
        # The third shape. `edges_of()` cannot produce it -- a span covering an
        # address cannot start above that address -- so it is `bucket_of()` that
        # is held here, as the function `failures()` guards through. A census
        # that filed it under one of the two would make the split a list.
        self.assertIsNone(census.bucket_of(0x1000, (0x1100, 0x1200)))
        self.assertEqual(census.bucket_of(0x1000, (0x1000, 0x1200)),
                         "same-address")
        self.assertEqual(census.bucket_of(0x1000, (0x0F00, 0x1200)),
                         "listing-opens-below-address")


class TheNamedRows(unittest.TestCase):
    """The claims the write-up and §8's correction rest on, per address.

    Relations and addresses, not a population: the tool's figure is whatever
    `--check` prints on the tree a reader runs it on.
    """

    @classmethod
    def setUpClass(cls):
        cls.records = committed()
        cls.by_key = {(r["program"], r["addr"]): r for r in cls.records}
        cls.nested, cls.edges = census.population(cls.records)

    def containers_of(self, key):
        return [census.where_text(e) for e in self.by_key[key]["edges"]]

    def test_the_bank0_0x90xx_rows_nest_in_0x8fdb(self):
        for addr in ("9000", "9006", "9007", "900D", "9015", "9016", "9018",
                     "901C", "902A"):
            self.assertEqual(
                self.containers_of(("bank0", addr)),
                ["bank0 8FDB `state_0817_fallthrough`, listed 0x8FDB-0x903F"],
                addr)

    def test_the_bank1_0xe3xx_rows_nest_in_0xe2d3(self):
        for addr in ("E322", "E332"):
            self.assertEqual(
                self.containers_of(("bank1", addr)),
                ["bank1 E2D3 `dispatch_036c_low3_then_seed_1c00_block`, "
                 "listed 0xE2D3-0xE3B3"], addr)

    def test_bank1_0xe322_is_not_a_row_the_csv_claims(self):
        # The issue lists it among the annotation rows this repository
        # committed deliberately. It is `seed_basis=auto` and no
        # `ghidra-functions.csv` row stands behind it -- which is the
        # difference between "nested" and "nested and somebody decided this is
        # a function", and the whole of the drop-or-keep question.
        r = self.by_key[("bank1", "E322")]
        self.assertEqual(r["seed_basis"], "auto")
        self.assertFalse(r["backed"])
        self.assertTrue(self.by_key[("bank1", "E332")]["backed"])

    def test_pd_0x9c4d_is_after_a_function_and_not_nested(self):
        # The reading §8 item 2 got wrong, held against the files rather than
        # against the sentence: `pd 0x9C45` is listed 0x9C45-0x9C4C, so the
        # frame at 0x9C4D begins the byte immediately after that listing ends
        # and is inside nothing.
        r, before = self.by_key[("pd", "9C4D")], self.by_key[("pd", "9C45")]
        self.assertEqual(r["verdict"], "after-a-function")
        self.assertEqual(r["edges"], [])
        self.assertEqual("%04X-%04X" % before["span"], "9C45-9C4C")

    def test_bank0_0xf002_is_reported_like_any_other_row(self):
        # #577, read and not relitigated: the container here, holding two
        # annotation rows of its own.
        for addr in ("EFDC", "EFF0"):
            self.assertEqual(
                [e["container_addr"] for e in self.by_key[("bank0", addr)]["edges"]],
                ["F002"], addr)

    def test_every_nested_row_is_nested_and_every_edge_names_a_container(self):
        self.assertTrue(self.nested)
        for r in self.nested:
            self.assertEqual(r["verdict"], "nested")
            self.assertTrue(r["edges"])
            for e in r["edges"]:
                self.assertEqual(e["container"]["program"], r["program"])
                self.assertNotEqual(e["container_addr"], e["addr"])
                self.assertIn(e["bucket"], census.BUCKETS)


class TheTwoReadings(unittest.TestCase):
    """"Contained" is ambiguous here, and both readings are reported."""

    @classmethod
    def setUpClass(cls):
        cls.records = committed()
        cls.by_key = {(r["program"], r["addr"]): r for r in cls.records}
        cls.nested, cls.edges = census.population(cls.records)
        cls.strict = {(e["program"], e["addr"])
                      for e in cls.edges if e["span_contained"]}
        cls.address = {(e["program"], e["addr"]) for e in cls.edges}

    def test_the_strict_reading_is_a_subset_of_the_address_reading(self):
        self.assertTrue(self.strict)
        self.assertLessEqual(self.strict, self.address)

    def test_they_differ_and_the_difference_is_reported(self):
        # If they were equal the report's second figure would be decoration, and
        # a reader told the population was "contained" would have no way to know
        # which reading the number came from.
        self.assertNotEqual(self.strict, self.address)
        text = census.report(self.records, [], census.notes(self.records))
        self.assertIn("span-inside-a-listing", text)
        self.assertIn("address-inside-a-listing", text)
        for key in self.address - self.strict:
            self.assertIn("%s %s" % key, text)

    def test_a_span_is_read_from_the_listing_and_not_the_size_column(self):
        # `index.csv` records 21 for this row and the listing runs 0x8054-0x806B,
        # so a tool that used `size` would get a different span and a different
        # answer about what 0x805B sits inside.
        row = [r for r in read_csv(census.INDEX_CSV)
               if r["program"] == "bank0" and norm_addr(r["addr"]) == "8054"][0]
        self.assertEqual(int(row["size"]), 21)
        self.assertEqual("%04X-%04X" % self.by_key[("bank0", "8054")]["span"],
                         "8054-806B")

    def test_the_report_example_span_is_the_listing_it_names(self):
        # The report prints `0x60ED-0x65A8` as `common 0x65A6` in its bucket
        # gloss. That pair is written into the tool as a literal, so this is what
        # turns a tree that moves into a red case and not a stale example.
        self.assertEqual("%04X-%04X" % self.by_key[("common", "65A6")]["span"],
                         "60ED-65A8")


class TheBucketIsOnTheEdge(unittest.TestCase):
    """"The container" is not always a single row, and the report says so."""

    @classmethod
    def setUpClass(cls):
        cls.records = committed()
        cls.nested, cls.edges = census.population(cls.records)

    def test_a_row_can_hold_more_than_one_container(self):
        many = [r for r in self.nested if len(r["edges"]) > 1]
        self.assertTrue(many)
        for r in many:
            self.assertGreater(len({e["container_addr"] for e in r["edges"]}), 1)

    def test_and_the_two_containers_of_such_a_row_differ_in_bucket(self):
        # This is what makes the split a partition of the edges and not of the
        # rows: a row-level bucket would have to pick one and be wrong about the
        # other.
        for r in self.nested:
            if len(r["edges"]) > 1:
                self.assertGreater(len({e["bucket"] for e in r["edges"]}), 1,
                                   r["addr"])

    def test_the_buckets_account_for_every_edge(self):
        counts = collections.Counter(e["bucket"] for e in self.edges)
        self.assertEqual(set(counts), set(census.BUCKETS))
        self.assertEqual(sum(counts.values()), len(self.edges))


class TheVerdicts(unittest.TestCase):
    """Three verdicts, and `unframed` is the one a nested row cannot hold."""

    @classmethod
    def setUpClass(cls):
        cls.records = committed()

    def test_every_row_read_gets_exactly_one_verdict(self):
        # A row with no listing is the one shape outside the three, and it is
        # named rather than folded into a verdict: a row this method did not
        # read has no framing to adjudicate.
        for r in self.records:
            if r["span"] is None:
                self.assertEqual(r["verdict"], census.UNREAD, r["addr"])
            else:
                self.assertIn(r["verdict"], census.VERDICTS, r["addr"])
        read = [r for r in self.records if r["span"] is not None]
        self.assertTrue(read)
        self.assertEqual({r["verdict"] for r in read}, set(census.VERDICTS))

    def test_unframed_has_no_instance_among_the_nested_rows(self):
        nested = [r for r in self.records if r["verdict"] == "nested"]
        self.assertTrue(nested)
        self.assertFalse([r for r in nested if r["verdict"] == "unframed"])

    def test_the_switch_entry_second_copy_census_calls_unframed_is_too(self):
        # `bank1 0x9AD2` is that tool's one `unframed`, and it is a member of
        # this set -- which is what lets the write-up say where the class's
        # instances are rather than only that it has none among the nested rows.
        got = {(r["program"], r["addr"]): r["verdict"] for r in self.records}
        self.assertEqual(got[("bank1", "9AD2")], "unframed")


class TheRefusals(unittest.TestCase):
    """Every refusal, on fixtures rather than on the committed tree.

    A refusal tested against the committed rows stops being a refusal the day
    the tree grows a row that needs it, which is the reason
    `second_copy_census.py` states and the reason these are built here.
    """

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        (self.decompiled, self.image, self.rows, self.anns) = \
            census._fixture_tree(scratch.name)
        self.records = census.census(self.rows, self.anns, self.image,
                                     self.decompiled)
        self.nested, self.edges = census.population(self.records)
        self.by_key = {(r["program"], r["addr"]): r for r in self.records}

    def test_a_row_alone_in_its_program_is_not_nested(self):
        # `unframed` rather than `after-a-function`: it is the only row in
        # `bank0` in this fixture, so nothing in that program ends the byte
        # before it either. Either way the claim under test is that nothing
        # holds it, and a `common` listing at the same address number does not
        # change that.
        r = self.by_key[("bank0", "0400")]
        self.assertNotEqual(r["verdict"], "nested")
        self.assertEqual(r["verdict"], "unframed")
        self.assertEqual(r["edges"], [])

    def test_a_container_in_the_other_program_does_not_nest(self):
        # Spans are per-program. `second_copy_census.target_row()` falls back
        # from a bank to `common`; this walk must not, and the two living in the
        # same module is exactly why.
        self.assertTrue(all(e["container"]["program"] == e["program"]
                            for e in self.edges))

    def test_mutual_nesting_yields_both_edges_and_neither_contains_the_other(self):
        a, b = self.by_key[("common", "0300")], self.by_key[("common", "0310")]
        self.assertEqual([e["container_addr"] for e in a["edges"]], ["0310"])
        self.assertEqual([e["container_addr"] for e in b["edges"]], ["0300"])
        self.assertFalse(any(e["span_contained"] for e in a["edges"] + b["edges"]))

    def test_a_listing_opening_below_its_own_address_is_the_other_bucket(self):
        # The reason the two buckets exist. `listing_bytes()` in the census this
        # imports already declines such a listing, and the bucket is what that
        # guard is measuring.
        below = self.by_key[("common", "0208")]["edges"]
        at = self.by_key[("common", "0110")]["edges"]
        self.assertEqual([e["bucket"] for e in below],
                         ["listing-opens-below-address"])
        self.assertEqual([e["bucket"] for e in at], ["same-address"])

    def test_a_row_with_no_listing_is_reported_rather_than_skipped(self):
        r = self.by_key[("common", "0600")]
        self.assertEqual(r["verdict"], census.UNREAD)
        self.assertIsNone(r["span"])
        self.assertTrue([p for p in census.notes(self.records) if "0600" in p])
        # ... and it is not a failure itself, or `--check` would be red on a tree
        # the export itself records this way. (The fixture includes other stale
        # entries for testing the extended guard, so we only check that 0600
        # is not reported as a failure.)
        failures_for_0600 = [p for p in census.failures(self.records, self.edges)
                             if "0600" in p]
        self.assertEqual(failures_for_0600, [])

    def test_a_frame_one_byte_past_a_listing_is_after_a_function(self):
        self.assertEqual(self.by_key[("common", "0501")]["verdict"],
                         "after-a-function")

    def test_a_listing_that_disagrees_with_the_firmware_fails(self):
        with open(os.path.join(self.decompiled, "common", "0110.asm"),
                  "w") as f:
            f.write("; fixture\n0110     90 34 12 mov  dptr,#0x1234\n")
        again = census.census(self.rows, self.anns, self.image, self.decompiled)
        found = census.failures(*census.population(again))
        self.assertTrue([p for p in found if "the export is stale" in p], found)
        # Named, so a person reading a red run knows which row to re-export.
        self.assertTrue([p for p in found if "0110" in p], found)

    def test_a_listing_whose_later_instructions_drift_is_caught(self):
        # The new fixture: a listing whose first instruction matches but a
        # later instruction differs. The extended guard walks the full listing
        # and catches this, where the old guard that only checked opening bytes
        # would have missed it.
        found = census.failures(self.records, self.edges)
        stale_messages = [p for p in found if "0700" in p and "stale" in p]
        self.assertTrue(stale_messages,
                        "the 0x0700 fixture should be caught as stale")

    def test_a_listing_opening_below_its_row_and_stale_there_is_caught(self):
        # The new fixture: a listing that opens at 0x07F0 but is assigned to
        # row 0x0800. The listing's opening byte is corrupted in the firmware.
        # The extended guard checks at the listing's actual opening point and
        # catches this.
        found = census.failures(self.records, self.edges)
        stale_messages = [p for p in found if "0800" in p and "stale" in p]
        self.assertTrue(stale_messages,
                        "the 0x0800 fixture should be caught as stale")


class WhatCheckFailsOn(unittest.TestCase):
    """Failures and notes are different kinds, and the exit code reads the first."""

    @classmethod
    def setUpClass(cls):
        cls.records = committed()
        cls.nested, cls.edges = census.population(cls.records)

    def test_the_committed_tree_is_green(self):
        self.assertEqual(census.failures(self.records, self.edges), [])

    def test_what_the_method_could_not_read_is_reported_and_not_empty(self):
        # Asserted as a relation, not a figure: there is a shape here this
        # method declines, and it is not a count of the tree that would have to
        # be edited on every merge.
        told = census.notes(self.records)
        self.assertTrue(told)
        self.assertTrue(any("no committed listing" in p for p in told))
        self.assertTrue(any("opens below its" in p or "opens below its own"
                            in p for p in told))
        for p in told:
            self.assertNotIn(p, census.failures(self.records, self.edges))


class TheReport(unittest.TestCase):
    """The lines the write-up quotes, held as a shape rather than as figures."""

    @classmethod
    def setUpClass(cls):
        cls.records = committed()
        cls.text = census.report(cls.records, [], census.notes(cls.records))

    def test_it_states_the_predicate_before_the_figure(self):
        head = self.text.split("## the two readings")[0]
        self.assertIn("predicate", head)
        self.assertIn("SAME program", head)

    def test_it_carries_both_readings_under_those_names(self):
        for phrase in ("address-inside-a-listing", "span-inside-a-listing",
                       "listing-opens-below-address", "same-address",
                       "after-a-function", "unframed"):
            self.assertIn(phrase, self.text, phrase)

    def test_it_names_the_command_that_produces_it(self):
        # A figure in a document with no command beside it is a transcription;
        # the whole point of this tool is that the write-up quotes output rather
        # than carrying a number.
        for command in ("nested_frame_census.py --check",
                        "nested_frame_census.py --self-test"):
            self.assertIn(command, self.text, command)

    def test_a_failure_is_rendered_rather_than_swallowed(self):
        text = census.report(self.records, ["a failure"], [])
        self.assertIn("FAIL  a failure", text)
        self.assertIn("## reported, not failed", text)


if __name__ == "__main__":
    unittest.main()
