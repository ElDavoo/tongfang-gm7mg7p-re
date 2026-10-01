#!/usr/bin/env python3
"""Offline checks for cross_decoder_blindness.py.

The tool's `--self-test` holds the five known answers issue #350 named, the
`insns`=0 identity, and its oracle against the committed listings. What is here
is the rest: that the classification is a **partition** rather than a set of
buckets that happens to add up, that the sidecar on disk is a fresh derivation
rather than something a hand edited, and `--check` driven in both directions --
a doctored cell fails, a doctored row fails, a **missing** file fails rather
than being created.

**No case here asserts a count of the tree.** The four class counts move every
time the export or the sample does, and a test that pinned them would be a
value every merge has to edit -- the `CLAUDE.md` rule, and the reason the
counts are held as a *relationship* (`census()` sums to the vacuous row count)
and read out of the committed sidecar rather than typed in. The one figure that
cannot be derived, `KNOWN_ANSWERS`, is five named functions with their classes
spelled out, which is a claim about those functions rather than about the
sample.

**The fixtures are hand-made bytes where they can be.** The branch order in
`classify_body()` is exercised against a five-byte image rather than against a
committed address, so a re-export cannot quietly turn a case into a test of
something else. What *has* to be measured on the tree is the other half: the
walk's agreement with the committed listings, and the sidecar's reproducibility,
and those are the cases that read the image.
"""
import csv
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).parent
# cross_decoder_blindness imports disasm8051 and build_ec_decompile by bare
# module name, so the tool directory has to be on the path before it is loaded
# rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'cross_decoder_blindness', HERE / 'cross_decoder_blindness.py')
blind = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blind)

import build_ec_decompile as bld

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')

_IMAGE = None
_ROWS = None


def image() -> bytes:
    global _IMAGE
    if _IMAGE is None:
        with open(FIRMWARE, "rb") as f:
            _IMAGE = f.read()
    return _IMAGE


def rows():
    """The sidecar's derivation over the committed tree, memoised."""
    global _ROWS
    if _ROWS is None:
        _ROWS = blind.blind_rows(image())
    return _ROWS


def parent() -> list:
    return bld.read_index(blind.CROSS_DECODER)


def fixture_image() -> bytes:
    """A five-byte image at bank0 0x1000, hand-transcribed.

    `bank0` addresses below `COMMON_END` map to themselves, so a `bytearray`
    this short is addressable and no case depends on what the firmware happens
    to hold there. `90 09 88 22` is `mov DPTR,#0x0988; ret`; `22 00` at 0x1004
    is `ret` followed by a pad byte.
    """
    img = bytearray(0x1006)
    img[0x1000:0x1004] = bytes([0x90, 0x09, 0x88, 0x22])
    img[0x1004:0x1006] = bytes([0x22, 0x00])
    return bytes(img)


NAMES_0988 = "void f(void)\n{\n  DAT_EXTMEM_0988 = 1;\n}\n"
NAMES_07D0 = "void f(void)\n{\n  DAT_EXTMEM_07d0 = 1;\n}\n"
SILENT = "void f(void)\n{\n  bVar1 = 1;\n}\n"


class Classifier(unittest.TestCase):
    """`classify_body()`'s branch order, on hand-made bytes."""

    def test_a_body_naming_nothing_is_no_xdata_named_even_with_a_literal_beside_it(self):
        self.assertEqual(
            blind.classify_body(SILENT, fixture_image(), "bank0", 0x1000, 4),
            blind.NO_XDATA_NAMED)

    def test_a_flow_opcode_at_the_entry_outranks_everything_else(self):
        # Both halves: against a body that names an address the extent does not
        # hold, and against one that names nothing. The order is the reason
        # `insns`=0 can mean `entry-is-branch` exactly.
        self.assertEqual(
            blind.classify_body(NAMES_07D0, fixture_image(), "bank0", 0x1004, 2),
            blind.ENTRY_IS_BRANCH)
        self.assertEqual(
            blind.classify_body(SILENT, fixture_image(), "bank0", 0x1004, 2),
            blind.ENTRY_IS_BRANCH)

    def test_a_literal_the_extent_holds_is_named_past_first_branch(self):
        self.assertEqual(
            blind.classify_body(NAMES_0988, fixture_image(), "bank0", 0x1000, 4),
            blind.NAMED_PAST_FIRST_BRANCH)

    def test_a_literal_the_extent_does_not_hold_is_no_literal_named(self):
        self.assertEqual(
            blind.classify_body(NAMES_07D0, fixture_image(), "bank0", 0x1000, 4),
            blind.NO_LITERAL_NAMED)

    def test_a_zero_size_listing_holds_nothing(self):
        # The second reading `insns`=0 would otherwise have, and the one the
        # self-test's zero-size assertion rules out over the committed report.
        self.assertEqual(
            blind.classify_body(NAMES_0988, fixture_image(), "bank0", 0x1000, 0),
            blind.NO_LITERAL_NAMED)

    def test_no_exported_c_is_unclassified_rather_than_guessed(self):
        self.assertEqual(blind.classify_body(None, fixture_image(), "bank0",
                                             0x1000, 4), "")

    def test_a_missing_export_and_an_out_file_of_none_read_the_same(self):
        for out_file in ("", None, "(no-instructions)", "bank0/DOES-NOT-EXIST.c"):
            with self.subTest(out_file=out_file):
                self.assertIsNone(blind.c_body(out_file,
                                               blind.strip_header_comment))
                self.assertEqual(
                    blind.classify(image(), "bank0", 0x1000, 4, out_file), "")

    def test_the_vocabulary_is_closed_and_held_by_name(self):
        # Not by length: a fourth reading of `vacuous` added as a synonym for
        # one of these would keep the counts right and let `--check` go green.
        self.assertEqual(set(blind.BLIND_CLASSES),
                         {blind.NO_XDATA_NAMED, blind.ENTRY_IS_BRANCH,
                          blind.NAMED_PAST_FIRST_BRANCH, blind.NO_LITERAL_NAMED})
        self.assertEqual(set(blind.CLASS_REASONS), set(blind.BLIND_CLASSES))
        for cls in blind.BLIND_CLASSES:
            with self.subTest(cls=cls):
                self.assertIsInstance(blind.CLASS_REASONS[cls], str)
                self.assertTrue(blind.CLASS_REASONS[cls].strip())


class Walk(unittest.TestCase):
    """The window-relative walk, against the committed listings.

    `extent_literals()` reads the firmware through `disasm8051`'s own tables,
    so nothing in the tool can contradict it -- the committed `.asm` is the
    record of the same bytes, and these are the cases that put the two side by
    side.
    """

    def test_the_committed_listing_is_read_as_the_exporter_wrote_it(self):
        self.assertEqual([m for m, _ in blind.asm_instructions("bank0", 0x9C24)][:2],
                         ["clr", "lcall"])
        self.assertEqual(blind.asm_dptr_operands("bank0", 0x9C24),
                         {"0x490", "0x8ad", "0x8bf"})

    def test_the_walk_agrees_with_the_committed_listing(self):
        listing = {(r["program"], r["addr"]): r
                   for r in bld.read_index(blind.LISTING_INDEX)}
        for program, addr in (("bank0", 0x9C24), ("bank0", 0x8FDB),
                              ("bank0", 0xACB4), ("bank0", 0x031C)):
            with self.subTest(program=program, addr="%04X" % addr):
                self.assertEqual(
                    blind.extent_literals(image(), program, addr,
                                          int(listing[(program, "%04X" % addr)]["size"])),
                    {"%04X" % int(a, 16)
                     for a in blind.asm_dptr_operands(program, addr)})

    def test_the_walk_is_over_the_listing_extent_and_not_the_window(self):
        # `CROSS_DECODER_WINDOW` is a bound on instruction *count* and the
        # listing's `size` is in bytes, so the two are not interchangeable; the
        # point of the case is that a function larger than the window's reach
        # still yields its later literals.
        listing = {(r["program"], r["addr"]): r
                   for r in bld.read_index(blind.LISTING_INDEX)}
        size = int(listing[("bank0", "ACB4")]["size"])
        with self.subTest(size=size, window=bld.CROSS_DECODER_WINDOW):
            self.assertGreater(size, bld.CROSS_DECODER_WINDOW)
            self.assertGreater(len(blind.extent_literals(image(), "bank0",
                                                         0xACB4, size)), 1)

    def test_a_listing_that_is_not_there_comes_back_empty(self):
        # Not a raise and not a guess: the oracle that invents a reading on a
        # shape it does not recognise is an oracle that agrees.
        self.assertEqual(blind.asm_instructions("bank0", 0xFFFF), [])
        self.assertEqual(blind.asm_dptr_operands("bank0", 0xFFFF), set())
        self.assertTrue(blind.asm_instructions("bank0", 0x031C))


class HeaderComment(unittest.TestCase):
    """Which block comment is removed, and that it does not matter which."""

    def test_a_ghidra_warning_is_not_the_annotation_comment(self):
        warned = ("/* WARNING: Do nothing block with infinite loop */\n"
                  "/* a type: line that is not the exporter's field */\n"
                  + NAMES_0988)
        self.assertEqual(blind.names_an_address(blind.strip_header_comment(warned)),
                         {"0988"})

    def test_the_annotations_own_addresses_are_not_the_bodys(self):
        annotated = ("/* Names 0x07D0 in prose.\n   type: state\n"
                     "   evidence: ec/decompiled/bank0/9006.c */\n" + NAMES_0988)
        self.assertEqual(blind.names_an_address(blind.strip_header_comment(annotated)),
                         {"0988"})

    def test_a_c_with_no_annotation_comment_keeps_its_body(self):
        self.assertEqual(blind.names_an_address(blind.strip_header_comment(SILENT)),
                         set())

    def test_the_census_is_the_same_under_either_stripping_rule(self):
        # The rule in the docstring is a choice, and this is what makes it one:
        # the four counts do not depend on which of the two is used. Asserted
        # rather than described, because a rule whose result had quietly become
        # load-bearing would still read the same in the docstring.
        self.assertEqual(blind.census(rows()),
                         blind.census(blind.blind_rows(
                             image(), blind.strip_every_comment)))


class Partition(unittest.TestCase):
    """The classification is a partition of the vacuous rows, and nothing else."""

    def test_the_committed_tree_partitions(self):
        self.assertEqual(blind.partition_problems(rows(), parent()), [])

    def test_the_four_counts_sum_to_the_vacuous_row_count(self):
        # A relationship rather than a census: this holds at any sample size,
        # and it is the property that makes the four numbers one measurement.
        vacuous = sum(1 for r in parent() if r["outcome"] == "vacuous")
        self.assertGreater(vacuous, 0)
        self.assertEqual(sum(blind.census(rows()).values()), vacuous)

    def test_a_row_falling_in_no_class_is_reported_rather_than_dropped(self):
        broken = [dict(r) for r in rows()]
        victim = next(i for i, r in enumerate(broken)
                      if r["blind"] == blind.NAMED_PAST_FIRST_BRANCH)
        broken[victim]["blind"] = ""
        problems = blind.partition_problems(broken, parent())
        self.assertEqual(len(problems), 1)
        self.assertIn("vacuous and carries no `blind` class", problems[0])

    def test_a_class_on_a_row_that_is_not_vacuous_is_reported(self):
        broken = [dict(r) for r in rows()]
        victim = next(i for i, r in enumerate(broken) if r["outcome"] == "agree")
        broken[victim]["blind"] = blind.ENTRY_IS_BRANCH
        problems = blind.partition_problems(broken, parent())
        self.assertEqual(len(problems), 1)
        self.assertIn("only a vacuous row is in scope", problems[0])

    def test_a_class_outside_the_closed_vocabulary_is_reported(self):
        broken = [dict(r) for r in rows()]
        victim = next(i for i, r in enumerate(broken) if r["blind"])
        broken[victim]["blind"] = "no-literal-named-ish"
        problems = blind.partition_problems(broken, parent())
        self.assertEqual(len(problems), 1)
        self.assertIn("closed vocabulary", problems[0])

    def test_a_vacuous_row_with_no_sidecar_row_at_all_is_reported(self):
        short = [r for r in rows() if r["blind"] != blind.ENTRY_IS_BRANCH]
        problems = blind.partition_problems(short, parent())
        self.assertTrue(problems)
        self.assertTrue(all("has no row in the sidecar" in p for p in problems))


class Identity(unittest.TestCase):
    """`insns`=0 is `entry-is-branch`, read from the firmware in both
    directions."""

    def test_the_zero_window_rows_and_the_flow_entry_rows_are_the_same_set(self):
        vacuous = [r for r in parent() if r["outcome"] == "vacuous"]
        zero = {(r["program"], r["addr"]) for r in vacuous if r["insns"] == "0"}
        flow = {(r["program"], r["addr"]) for r in vacuous
                if blind.entry_is_branch(image(), r["program"], int(r["addr"], 16))}
        self.assertTrue(zero)
        self.assertEqual(zero, flow)

    def test_and_the_sidecar_classifies_exactly_that_set_as_entry_is_branch(self):
        by_class = {(r["program"], r["addr"]) for r in rows()
                    if r["blind"] == blind.ENTRY_IS_BRANCH}
        vacuous = {(r["program"], r["addr"]) for r in parent()
                   if r["outcome"] == "vacuous" and r["insns"] == "0"}
        self.assertEqual(by_class, vacuous)

    def test_no_vacuous_zero_window_row_is_a_zero_size_listing(self):
        # The one alternative reading of `insns`=0, named rather than assumed
        # away: a listing of size zero decodes nothing whatever its entry byte.
        listing = {(r["program"], r["addr"]): r
                   for r in bld.read_index(blind.LISTING_INDEX)}
        for r in parent():
            if r["outcome"] != "vacuous" or r["insns"] != "0":
                continue
            with self.subTest(program=r["program"], addr=r["addr"]):
                self.assertGreater(
                    int(listing[(r["program"], r["addr"])]["size"]), 0)

    def test_the_flow_opcode_set_is_the_comparison_own(self):
        # `entry_is_branch()` reads `disasm8051.FLOW_OPCODES`; this asserts it
        # is the set the comparison stops on and not a list written here.
        self.assertIs(blind.disasm8051.FLOW_OPCODES, bld.disasm8051.FLOW_OPCODES)
        self.assertIn(0x12, blind.disasm8051.FLOW_OPCODES)   # lcall
        self.assertIn(0x22, blind.disasm8051.FLOW_OPCODES)   # ret
        self.assertNotIn(0x90, blind.disasm8051.FLOW_OPCODES)  # mov dptr,#imm


class KnownAnswers(unittest.TestCase):
    """The five functions issue #350 named, at what each reads on this tree.

    `bank0 0xACB4` is pinned at `named-past-first-branch` rather than at the
    issue's `no-literal-named`. That is not a typo and not a softening: the
    issue's example turns on the C naming neither 0x07C5 nor 0x075E, which is
    a claim about two addresses, and this classifier asks whether the function
    loads an address its C names -- which `ACB4` does, ten of them. Pinned at
    the measurement, with the difference written up in
    `docs/findings/cross-decoder-blind-population.md`.
    """

    def test_each_named_function_reads_what_the_table_says(self):
        by_key = {(r["program"], r["addr"]): r for r in rows()}
        for program, addr, name, want in blind.KNOWN_ANSWERS:
            with self.subTest(program=program, addr=addr):
                row = by_key[(program, addr)]
                self.assertEqual(row["name"], name)
                self.assertEqual(row["outcome"], "vacuous")
                self.assertEqual(row["blind"], want)

    def test_all_five_are_vacuous_rows_the_parent_also_records(self):
        vacuous = {(r["program"], r["addr"]) for r in parent()
                   if r["outcome"] == "vacuous"}
        for program, addr, _name, _want in blind.KNOWN_ANSWERS:
            with self.subTest(program=program, addr=addr):
                self.assertIn((program, addr), vacuous)

    def test_the_two_classes_the_issue_named_are_both_represented(self):
        # A guard against the table quietly losing its diversity: if a future
        # change collapsed the classifier, `KNOWN_ANSWERS` would keep passing
        # on one class while the census stopped saying anything.
        self.assertEqual({want for _, _, _, want in blind.KNOWN_ANSWERS},
                         {blind.ENTRY_IS_BRANCH, blind.NAMED_PAST_FIRST_BRANCH,
                          blind.NO_LITERAL_NAMED})

    def test_the_documented_disagreement_is_still_the_measurement(self):
        # `ACB4` is the row the issue and this table disagree about, so the
        # disagreement is a fact to be held rather than a sentence to be
        # re-read: its extent really does hold literals, and really more than
        # its C names.
        listing = {(r["program"], r["addr"]): r
                   for r in bld.read_index(blind.LISTING_INDEX)}
        size = int(listing[("bank0", "ACB4")]["size"])
        literals = blind.extent_literals(image(), "bank0", 0xACB4, size)
        named = blind.names_an_address(blind.c_body(
            "bank0/ACB4.c", blind.strip_header_comment))
        with self.subTest(literals=len(literals), named=len(named)):
            self.assertTrue(literals)
            self.assertTrue(named & literals)
            self.assertGreater(literals, named & literals)


class Ratchet(unittest.TestCase):
    """`--check` driven in both directions, and the sidecar's reproducibility."""

    def _sidecar(self):
        return bld.read_index(blind.BLINDNESS)

    def test_the_committed_sidecar_is_a_fresh_derivation(self):
        with open(blind.BLINDNESS, newline="") as f:
            header = next(csv.reader(f))
        with open(blind.BLINDNESS) as f:
            on_disk = f.read()
        self.assertEqual(header, blind.BLIND_COLUMNS)
        self.assertEqual(blind.render(rows()), on_disk)

    def test_it_carries_the_parent_keys_and_only_the_vacuous_rows_are_classed(self):
        self.assertEqual([(r["program"], r["addr"]) for r in self._sidecar()],
                         [(r["program"], r["addr"]) for r in parent()])
        self.assertEqual(blind.partition_problems(self._sidecar(), parent()), [])

    def test_it_carries_no_insns_column(self):
        # `insns`=0 is `entry-is-branch` only because the class is recomputed
        # from the firmware; a copy of the column beside it would be a second
        # answer to the same question.
        self.assertNotIn("insns", blind.BLIND_COLUMNS)

    def test_a_doctored_cell_is_caught(self):
        doctored = [dict(r) for r in self._sidecar()]
        victim = next(i for i, r in enumerate(doctored) if r["blind"])
        doctored[victim]["blind"] = blind.NO_XDATA_NAMED
        compared, problems = blind.blindness_problems(doctored, rows())
        self.assertEqual(len(problems), 1)
        self.assertIn("blind", problems[0])
        self.assertIn("regenerate", problems[0])
        self.assertGreater(compared, 0)

    def test_a_doctored_name_is_caught_too(self):
        # The ratchet compares every column, not just the class, so a renamed
        # function in the parent cannot pass unnoticed here.
        doctored = [dict(r) for r in self._sidecar()]
        doctored[0]["name"] = "renamed"
        _compared, problems = blind.blindness_problems(doctored, rows())
        self.assertEqual(len(problems), 1)
        self.assertIn("name", problems[0])

    def test_a_row_the_sample_no_longer_has_is_caught(self):
        # A phantom committed row the current sample does not carry, so the
        # parent of these three is named: a report that has outlasted the export
        # it describes.
        extra = self._sidecar() + [dict(self._sidecar()[0], addr="FFFF")]
        _compared, problems = blind.blindness_problems(extra, rows())
        self.assertEqual(len(problems), 1)
        self.assertIn("not in the sample", problems[0])

    def test_a_row_the_sample_gained_is_caught(self):
        # The other direction: a committed row missing from the sidecar, which
        # is the one a sidecar holding only the classified rows could not see.
        short = self._sidecar()[1:]
        _compared, problems = blind.blindness_problems(short, rows())
        self.assertEqual(len(problems), 1)
        self.assertIn("in the sample and not in the sidecar", problems[0])

    def test_an_identical_copy_has_no_problems(self):
        # The known-good case, first on purpose in `--check`'s own run: a
        # guard exercised only on doctored input cannot tell "clean" from
        # "never ran".
        compared, problems = blind.blindness_problems(self._sidecar(), rows())
        self.assertEqual(problems, [])
        self.assertEqual(compared, len(rows()))


class CommandLine(unittest.TestCase):
    """The tool as a command, including the refusals."""

    def _run(self, *args, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = blind.main(list(args))
        return rc, out.getvalue(), err.getvalue()

    def test_check_passes_on_the_committed_sidecar(self):
        rc, out, _err = self._run("--check")
        self.assertEqual(rc, 0)
        self.assertIn("every cell agreeing with", out)

    def test_check_fails_when_the_sidecar_is_missing_and_does_not_create_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            absent = os.path.join(tmp, "cross-decoder-blindness.csv")
            rc, _out, err = self._run("--check", "--sidecar", absent)
            self.assertEqual(rc, 1)
            self.assertIn("has stopped checking it", err)
            self.assertFalse(os.path.exists(absent))

    def test_check_refuses_to_be_given_both_modes(self):
        with self.assertRaises(SystemExit):
            self._run("--check", "--report")

    def test_report_writes_the_sidecar_and_check_then_agrees_with_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sidecar.csv")
            rc, out, _err = self._run("--report", "--sidecar", path)
            self.assertEqual(rc, 0)
            self.assertIn("wrote", out)
            with open(path) as written, open(blind.BLINDNESS) as committed:
                self.assertEqual(written.read(), committed.read())

    def test_the_plain_run_prints_the_census_and_every_class_is_explained(self):
        rc, out, _err = self._run()
        self.assertEqual(rc, 0)
        for cls in blind.BLIND_CLASSES:
            with self.subTest(cls=cls):
                self.assertIn(cls, out)
                self.assertIn(blind.CLASS_REASONS[cls], out)
        self.assertRegex(out, r"the \d+ vacuous row\(s\) are .* of \d+ "
                              r"sampled function\(s\)")

    def test_the_render_is_byte_identical_run_to_run(self):
        # What the ratchet rests on. A sidecar whose bytes moved between two
        # runs of the same inputs would make `--check` a coin flip.
        self.assertEqual(blind.render(rows()), blind.render(rows()))


class NoRegression(unittest.TestCase):
    """Adding this moved nothing the comparison already reports.

    The deliverable is a sidecar over the parent's own rows, so the claim is
    that `build_ec_decompile.py` still means what it meant: its self-test
    passes, and the denominator line recomputed from the tree is the one the
    committed report already encodes. Not asserted as a literal, which would be
    a count of the tree every merge has to edit.
    """

    def test_build_ec_decompiles_self_test_still_passes(self):
        with tempfile.TemporaryDirectory() as work:
            proc = subprocess.run(
                [sys.executable, str(HERE / 'build_ec_decompile.py'),
                 '--work', work, '--self-test'],
                capture_output=True, text=True, cwd=str(HERE.parent.parent))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("all assertions passed", proc.stdout)

    def test_the_denominator_line_still_describes_the_committed_report(self):
        committed = bld.denominator_line(
            bld.cross_decoder_summary(bld.read_index(blind.CROSS_DECODER)))
        recomputed = bld.denominator_line(
            bld.cross_decoder_summary(bld.cross_decoder_results(image())))
        self.assertEqual(committed, recomputed)

    def test_nothing_was_added_to_the_comparison_own_vocabulary(self):
        self.assertEqual(bld.CROSS_DECODER_OUTCOMES,
                         ("agree", "disagree", "vacuous", "no-export"))
        self.assertNotIn("blind", bld.CROSS_DECODER_OUTCOMES)
        self.assertEqual(bld.CROSS_DECODER_COLUMNS,
                         ["program", "addr", "name", "sample", "insns", "linear",
                          "in_c", "missing", "outcome"])

    def test_the_parents_report_is_unchanged_by_this_tool(self):
        # The sidecar is derived; the parent is not written by anything here.
        self.assertEqual(bld.CROSS_DECODER,
                         os.path.join(HERE.parent, 'ghidra', 'cross-decoder.csv'))


if __name__ == "__main__":
    unittest.main()
