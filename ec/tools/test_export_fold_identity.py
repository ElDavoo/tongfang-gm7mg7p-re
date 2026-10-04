#!/usr/bin/env python3
"""What stands in for `export_fold_identity.py` deciding a fold, and what does not.

The tool asks whether any mechanical criterion can tell a `re-export` from a
`fragment` -- the two readings `xdata-export-ownership-verdicts.csv` records --
because a fold decided by a text heuristic deletes a routine from the census
and only a project rebuild fixes the boundary underneath it
(`annotations/xdata-06c2-06db-timers.md` 8 item 7). The answer is that these
two probes do not separate the two, which is a negative result and the only
kind of result this suite will accept silently.

**The assertion that matters is the negative one.** `TheProbesDoNotSeparate`
holds that neither probe fires on one class and not the other. That is a
property of the measurements, not a figure: it goes red the day a probe set
*does* discriminate, and the message says the boundary became mechanically
settleable. A suite that only checked the positive controls would let a probe
set that separated the classes pass in silence, which is the opposite of what
this work is for.

**Every other case here is a control on the measurement's own edges.** A probe
that fires on everything separates nothing, so a case that would separate has to
be built and shown to be detected; a row outside the audited programs has to
read `not-audited` rather than `no`, because a scan that never ran over a
program is not a scan that found nothing there; and a row with no recorded
verdict has to come back `unmeasured` rather than agreeing with either class.
Those three are the ways this report could be over-read, and each is caught
against a constructed population rather than against the tree.

**Nothing here asserts a figure of the committed tree.** The one case that
touches the committed inputs checks that the population is *derived* -- that
every ledger verdict names a row the committed map contains -- and not how many
rows there are, because a census is a value every merge has to edit and this
suite is meant to keep passing as the map moves. The measurements themselves
print: `python3 ec/tools/export_fold_identity.py`.
"""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    "export_fold_identity", HERE / "export_fold_identity.py")
efi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(efi)


def row(out_file, owner="bank0/8000.c", shared="yes"):
    """One map row in the shape the population predicate reads."""
    program, addr = out_file.split("/")[0], out_file.split("/")[1][:-2]
    return {"out_file": out_file, "program": program, "addr": addr,
            "owner_out_file": owner, "owner_addr": "8000",
            "owner_name": "owner_name", "shared": shared,
            "body_lines": "4", "containment": "1.00",
            "owner_body_lines": "22", "member_share": "0.18"}


def verdict(out_file, value="fragment", owner="bank0/8000.c"):
    return {"out_file": out_file, "owner_out_file": owner, "verdict": value,
            "basis": "a reason a reader can check"}


def assessed(out_file, named="yes", start="yes", value="fragment",
             owner="bank0/8000.c", program=None, addr=None):
    """One assessment record, without running a probe to produce it."""
    return {"out_file": out_file, "program": program or out_file.split("/")[0],
            "addr": addr or out_file.split("/")[1][:-2],
            "owner_out_file": owner, "named_by_transfer": named,
            "instruction_start": start, "verdict": value}


class PopulationTests(unittest.TestCase):
    """Which rows the report is about, and where that population comes from."""

    def test_the_population_is_the_non_owner_rows_of_the_map(self):
        rows = [row("bank0/8000.c", shared="no"), row("bank0/8004.c"),
                row("bank0/8008.c"), row("bank1/9004.c", owner="bank1/9000.c")]
        self.assertEqual(
            [r["out_file"] for r in efi.non_owner_rows(rows)],
            ["bank0/8004.c", "bank0/8008.c", "bank1/9004.c"])

    def test_an_owner_row_is_not_a_fold_anybody_has_to_decide(self):
        # A row that owns itself is not a fold at all, so a verdict recorded
        # against one is a stale ledger row rather than a probe result.
        self.assertEqual(efi.non_owner_rows([row("bank0/8000.c",
                                                shared="no")]), [])

    def test_a_verdict_the_ledger_does_not_record_reads_unmeasured(self):
        # The image is the committed one rather than a stub: probe A reads
        # bytes, and a zero-length buffer is a scan that raised rather than a
        # scan that found nothing.
        import entry_reachability
        rows = [row("bank0/8004.c"), row("bank0/8008.c")]
        verdicts = [verdict("bank0/8004.c")]
        out = efi.assess(rows, verdicts, entry_reachability.read_image(),
                         index={})
        self.assertEqual([r["verdict"] for r in out],
                         ["fragment", efi.UNMEASURED])

    def test_unmeasured_is_outside_the_ledger_vocabulary(self):
        # The ledger's tokens are closed so that a typo cannot become "we
        # looked and could not tell". This tool's word for a fold nobody has read
        # has to stay outside that vocabulary for the same reason, or a row
        # could carry it and read as decided.
        import export_ownership_verdicts as eov
        self.assertNotIn(efi.UNMEASURED, eov.VERDICTS)


class ProbeWindowTests(unittest.TestCase):
    """The two edges where a probe's answer would not be about the member."""

    def test_a_program_the_reachability_scan_does_not_audit_is_not_a_no(self):
        # `entry_reachability.AUDITED` is three programs and the map has a
        # fourth. Reporting a `pd` row as `no` would say the scan covered it
        # and found nothing naming it, which is a claim about bytes from a scan
        # that never ran over them.
        import entry_reachability
        self.assertNotIn("pd", entry_reachability.AUDITED)
        out = efi.probe_named(b"", row("pd/3750.c", owner="pd/9784.c"))
        self.assertEqual(out, efi.NOT_AUDITED)
        self.assertNotEqual(out, "no")

    def test_an_audited_program_gets_a_real_answer(self):
        # The control for the case above: the same probe on a program the scan
        # does cover returns yes or no, so `not-audited` is a property of the
        # window rather than of the probe.
        import entry_reachability
        out = efi.probe_named(entry_reachability.read_image(),
                              row("bank0/8004.c"))
        self.assertIn(out, ("yes", "no"))
        self.assertNotEqual(out, efi.NOT_AUDITED)

    def test_probe_b_reads_the_listings_and_nothing_else(self):
        # B is a set membership over the committed `.asm` files, so an index
        # the caller hands in is the whole of its input -- which is what lets a
        # case below state a listing tree that does not exist on disk.
        index = {"bank0": {0x8004}}
        self.assertEqual(efi.probe_instruction_start(index, row("bank0/8004.c")),
                         "yes")
        self.assertEqual(efi.probe_instruction_start(index, row("bank0/8008.c")),
                         "no")

    def test_probe_b_does_not_answer_for_a_program_it_has_no_listings_for(self):
        # A missing program is `no` here rather than a third value, because
        # `PROGRAMS` is a closed list this tool reads a directory for; a program
        # absent from it is not a row the report can carry at all.
        self.assertEqual(efi.probe_instruction_start({}, row("bank0/8004.c")),
                         "no")

    def test_b_fires_wherever_the_member_has_its_own_committed_listing(self):
        # Probe B is close to a constant on this tree, and the write-up says so
        # rather than leaving a reader to infer it from the cross-tab. The
        # relation is the honest form: the exporter writes one listing per
        # export, so a member's address is an instruction start exactly when the
        # committed listing index gives that address a listing rather than the
        # placeholder it writes for an export the decompiler emitted no
        # instructions for. Held as a relation in both directions, because the
        # count of rows it leaves over is what a future seed moves and is not
        # what makes the probe mean something.
        import csv
        import entry_reachability
        import export_ownership_verdicts as eov
        with open(HERE.parent / "decompiled" / "listing-index.csv",
                  newline="") as f:
            listing = list(csv.DictReader(f))
        # `build_ec_decompile.py` records such a row with this `out_file`
        # rather than as no row at all, so the boundary is read from the index
        # rather than from the directory scan the probe itself reads.
        no_instructions = {(r["program"], r["addr"]) for r in listing
                           if r["out_file"] == efi.NO_INSTRUCTIONS}
        self.assertTrue(no_instructions,
                        "the committed listing index no longer records a "
                        "zero-instruction export, so the boundary this case "
                        "holds no longer exists to be tested at")
        assessed = efi.assess(eov.load_map(), eov.load_verdicts(),
                              entry_reachability.read_image())
        unlisted = {r["out_file"] for r in assessed
                    if r["instruction_start"] == "no"}
        expected = {r["out_file"] for r in assessed
                    if (r["program"], r["addr"]) in no_instructions}
        self.assertEqual(unlisted, expected,
                         "probe B fires on a row unless the committed listing "
                         "index says the export has no instructions of its own")
        self.assertTrue(unlisted,
                        "probe B fired on every non-owner row, so this no "
                        "longer says where its boundary is")


class TheProbesDoNotSeparate(unittest.TestCase):
    """The finding, asserted as a property so a future probe set trips it."""

    # Two rows of each verdict, and the assessments a probe set that separates
    # nothing produces: every probe fires on every row of both classes.
    def setUp(self):
        self.flat = [
            assessed("bank0/8004.c", named="yes", start="yes",
                     value="re-export"),
            assessed("bank0/8008.c", named="yes", start="yes",
                     value="re-export"),
            assessed("bank1/9004.c", owner="bank1/9000.c", named="yes",
                     start="yes", value="fragment"),
            assessed("bank1/9008.c", owner="bank1/9000.c", named="yes",
                     start="yes", value="fragment"),
        ]
        self.counts = efi.crosstab(self.flat)

    def test_a_probe_that_fires_on_everything_separates_nothing(self):
        for probe in efi.PROBES:
            self.assertFalse(
                efi.separates(self.counts, ("re-export", "fragment"), probe),
                "%s fires on every row of both verdicts, which is the "
                "measurement this tool reports -- not a discriminator"
                % probe)

    def test_the_negative_holds_for_the_committed_tree_too(self):
        # The constructed cases above show the predicate can tell a
        # discriminator from a non-discriminator. This one is the finding on the
        # committed inputs: the real ledger, the real map, the real image. It
        # asserts the property and not a count, so it stays true as the map
        # moves; if a future probe set discriminates, this is what goes red.
        import entry_reachability
        import export_ownership_verdicts as eov
        assessed = efi.assess(eov.load_map(), eov.load_verdicts(),
                              entry_reachability.read_image())
        counts = efi.crosstab(assessed)
        judged = sorted({r["verdict"] for r in assessed
                         if r["verdict"] != efi.UNMEASURED})
        self.assertGreaterEqual(len(judged), 2,
                                "the ledger no longer holds two verdicts to "
                                "compare, so there is nothing for this to say")
        for probe in efi.PROBES:
            self.assertFalse(
                efi.separates(counts, judged, probe),
                "%s now separates %s on the committed tree, so the boundary "
                "has become mechanically settleable and the write-up's "
                "negative result is wrong" % (probe, ", ".join(judged)))

    def test_a_probe_that_would_separate_is_detected(self):
        # The control for the negative above: fire on every re-export and on no
        # fragment, and `separates` says so. Without this, a `separates` that
        # always returned False would pass the negative case while measuring
        # nothing.
        built = [
            assessed("bank0/8004.c", named="yes", start="yes",
                     value="re-export"),
            assessed("bank1/9004.c", owner="bank1/9000.c", named="no",
                     start="no", value="fragment"),
        ]
        counts = efi.crosstab(built)
        for probe in efi.PROBES:
            self.assertTrue(
                efi.separates(counts, ("re-export", "fragment"), probe),
                "%s fires on the re-export and not on the fragment, which is "
                "the shape separates() exists to recognise" % probe)

    def test_one_verdict_alone_separates_nothing(self):
        # With only one verdict present there is no second class to tell it
        # from, and returning True would report a discriminator out of a
        # population that cannot hold one.
        counts = efi.crosstab([assessed("bank0/8004.c", value="re-export")])
        for probe in efi.PROBES:
            self.assertFalse(
                efi.separates(counts, ("re-export",), probe),
                "one verdict is not a separation, however the probe reads it")


class CrossTabTests(unittest.TestCase):
    """What the table counts, and what it refuses to count."""

    def test_a_row_with_no_verdict_is_out_of_the_cross_tab(self):
        # The gap is the coverage statement, so it must not leak into the
        # fired-counts: a probe firing on a fold nobody has read says nothing
        # about that fold, and counting it would answer a question nobody asked.
        rows = [assessed("bank0/8004.c", value="fragment"),
                assessed("bank0/8008.c", value="fragment"),
                assessed("bank0/800C.c", value=efi.UNMEASURED)]
        counts = efi.crosstab(rows)
        self.assertEqual(counts[("fragment", "named_by_transfer", "yes")], 2)
        self.assertNotIn((efi.UNMEASURED, "named_by_transfer", "yes"), counts)

    def test_a_probe_with_no_answer_is_its_own_cell_not_a_no(self):
        # `not-audited` counted as `no` would put a program the scan never
        # covered into the same column as one it covered and found nothing in,
        # which is the distinction the whole three-value shape exists for.
        rows = [assessed("bank0/8004.c", named=efi.NOT_AUDITED,
                         value="fragment")]
        counts = efi.crosstab(rows)
        self.assertEqual(counts[("fragment", "named_by_transfer",
                                 efi.NOT_AUDITED)], 1)
        self.assertNotIn(("fragment", "named_by_transfer", "no"), counts)

    def test_the_report_names_the_gap_and_the_unmeasured_word(self):
        # A reader who sees only the fired counts would take the table for
        # coverage; the gap and the word that means "nobody has read this" are
        # what stop that, so they are asserted rather than left to taste. The
        # gap is matched on the words and not on the wrapped line they sit in,
        # because a reflow of the report is not a change of what it claims.
        rows = [assessed("bank0/8004.c", value="fragment"),
                assessed("bank0/800C.c", value=efi.UNMEASURED)]
        flat = " ".join(efi.report(rows).split())
        self.assertIn(efi.UNMEASURED, flat)
        self.assertIn(efi.NOT_AUDITED, flat)
        self.assertIn("carry no verdict", flat)

    def test_the_report_prints_every_probe_value_not_just_the_fires(self):
        rows = [assessed("bank0/8004.c", named="yes", value="fragment"),
                assessed("bank0/8008.c", named=efi.NOT_AUDITED,
                         value="fragment")]
        text = efi.report(rows)
        for probe in efi.PROBES:
            self.assertIn(probe, text)
        self.assertIn("yes=1", text)
        self.assertIn("%s=1" % efi.NOT_AUDITED, text)

    def test_the_conclusion_follows_the_table_it_sits_under(self):
        # The conclusion is derived from `separates` over the cross-tab the
        # report prints above it, so a population that does discriminate says
        # so. Asserted on both directions because a literal typed in beside
        # the table reads the same either way, which is the defect: on the
        # committed tree the sentence is true, and it would have kept being
        # printed under a table that said the opposite.
        separating = [assessed("bank0/8004.c", named="yes", start="yes",
                               value="re-export"),
                      assessed("bank0/8008.c", named="no", start="no",
                               value="fragment")]
        flat = " ".join(efi.report(separating).split())
        self.assertNotIn("Neither probe separates", flat)
        for probe in efi.PROBES:
            self.assertIn(probe, flat)

        together = [assessed("bank0/8004.c", value="re-export"),
                    assessed("bank0/8008.c", value="fragment")]
        self.assertIn("Neither probe separates",
                      " ".join(efi.report(together).split()))


class CommittedTreeTests(unittest.TestCase):
    """The one place this suite reads the tree, and only for a relation."""

    def test_the_population_is_derived_and_covers_every_recorded_verdict(self):
        # Not a count: the population comes out of the committed map and the
        # ledger has to describe all of it. A map that grows a non-owner row
        # makes this suite check the new row rather than fail on its arrival.
        import export_ownership_verdicts as eov
        records = eov.load_map()
        verdicts = eov.load_verdicts()
        population = {r["out_file"] for r in efi.non_owner_rows(records)}
        self.assertTrue(population)
        for v in verdicts:
            self.assertIn(v["out_file"], population,
                          "the ledger carries a verdict for a row the "
                          "committed map does not have as a non-owner, so the "
                          "probe report is not about the same population the "
                          "ledger is")

    def test_every_verdict_the_ledger_records_is_one_of_its_own_tokens(self):
        # The tool must not invent a fourth reading. A probe result beside a
        # verdict belongs in a column, not in the verdict.
        import export_ownership_verdicts as eov
        for v in eov.load_verdicts():
            self.assertIn(v["verdict"], eov.VERDICTS)


if __name__ == "__main__":
    unittest.main()
