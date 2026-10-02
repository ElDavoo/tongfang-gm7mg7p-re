#!/usr/bin/env python3
"""Offline checks for cross_decoder_disagreement.py.

The tool's `--self-test` holds the known answers issue #510 named, the identity
between its recomputed `missing` and the parent's committed cell, and the
classifier's own fixtures. What is here is the rest: that the classification is
a **partition** rather than a set of buckets that happens to add up, that the
sidecar on disk is a fresh derivation rather than something a hand edited, that
`--check` is driven in both directions, and -- the strongest single case here --
**that no row moved `agree` -> `disagree`**. That last one is a property over
the whole tree rather than a sentence in a docstring, and it is the direction
issue #510 is about: widening a matcher can only ever grow the set of addresses
it accepts, so a row reaching `disagree` on the spelling route is not a
decompiler doing better and is not a row count either.

**No case here asserts a count of the tree.** The five cause counts move every
time the export or the sample does, and a test that pinned them would be a
value every merge has to edit -- the `CLAUDE.md` rule, and the reason the counts
are held as a *relationship* (`census()` sums to the `disagree` row count) and
read out of the committed sidecar rather than typed in. The one figure that
cannot be derived, `KNOWN_ANSWERS`, is nine named functions with their causes
spelled out, which is a claim about those functions rather than about the
sample.

**The fixtures are hand-made text where they can be.** The branch order in
`classify_body()` is exercised against five one-line bodies rather than against
committed addresses, so a re-export cannot quietly turn a case into a test of
something else. What *has* to be measured on the tree is the other half: the
sidecar's agreement with the parent's own cells, and its reproducibility, and
those are the cases that read the image.
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
# cross_decoder_disagreement imports build_ec_decompile by bare module name, so
# the tool directory has to be on the path before it is loaded rather than
# after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'cross_decoder_disagreement', HERE / 'cross_decoder_disagreement.py')
dis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dis)

import build_ec_decompile as bld

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')

_IMAGE = None
_ROWS = None

# A two-name symbol table, so a fixture that wants a register name does not have
# to read the committed CSV -- and so a fixture can be wrong about which name
# carries which address without that being a statement about the tree.
NAMES_075C = {"MAIN_FAN_R_DUTY": {0x075C}, "GPU_DYNAMIC_BOOST_STATUS": {0x07C4}}


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
        _ROWS = dis.disagreement_rows(image())
    return _ROWS


def parent() -> list:
    return bld.read_index(dis.CROSS_DECODER)


def classify(body, missing):
    return dis.classify_body(body, missing, NAMES_075C)


class Classifier(unittest.TestCase):
    """`classify_body()`'s branch order, on hand-made text.

    Each negative is the positive with exactly one thing wrong, so a failure
    names the rule that stopped rejecting rather than the class that stopped
    matching.
    """

    # A body that names an address in the comparison's own vocabulary, so the
    # last two causes can be told apart from "names nothing at all".
    SAYS_AN_ADDRESS = "  DAT_EXTMEM_0a52 = 1;\n  %s\n"

    def test_a_name_from_the_symbol_table_names_the_address(self):
        self.assertEqual(classify("  MAIN_FAN_R_DUTY = *param_1;\n", ["075C"]),
                         dis.NAMED_BY_REGISTER_SYMBOL)

    def test_a_register_name_carrying_a_different_address_does_not(self):
        body = self.SAYS_AN_ADDRESS % "MAIN_FAN_R_DUTY = 2;"
        self.assertEqual(classify(body, ["07C4"]), dis.NAMES_OTHER_ADDRESSES)

    def test_a_code_space_symbol_names_a_code_address(self):
        self.assertEqual(classify("  pbVar6 = &DAT_CODE_6f39;\n", ["6F39"]),
                         dis.NAMED_BY_CODE_SYMBOL)

    def test_the_export_calls_a_function_entry_in_that_space_too(self):
        # `bank0 0xBADB`'s whole body is `be16_add(0,FUN_CODE_08ce,1);`, and a
        # class that only knew the `DAT_CODE_` spelling would call that a
        # different shape from `common 0x00CF`'s `&DAT_CODE_6f39`. It is not:
        # the address is not in XDATA either way.
        self.assertEqual(classify("  be16_add(0,FUN_CODE_08ce,1);\n", ["08CE"]),
                         dis.NAMED_BY_CODE_SYMBOL)

    def test_and_a_code_space_symbol_does_not_name_an_xdata_address(self):
        body = self.SAYS_AN_ADDRESS % "pbVar6 = &DAT_CODE_6f39;"
        self.assertEqual(classify(body, ["075C"]), dis.NAMES_OTHER_ADDRESSES)

    def test_a_decimal_literal_of_that_value_names_the_address(self):
        self.assertEqual(classify("  read_xdata_pair_to_r1r2(900);\n", ["0384"]),
                         dis.NAMED_BY_DECIMAL_LITERAL)

    def test_and_one_of_a_different_value_does_not(self):
        body = self.SAYS_AN_ADDRESS % "read_xdata_pair_to_r1r2(901);"
        self.assertEqual(classify(body, ["0384"]), dis.NAMES_OTHER_ADDRESSES)

    def test_a_hex_literal_is_not_also_read_as_a_decimal(self):
        # It is the route `names_an_address()` already had, so a body that
        # spells the address this way would not be a `disagree` row at all; the
        # case is here because a decimal regex that also matched `3f8` would
        # hand this body to the wrong cause.
        self.assertEqual(classify("  read_xdata_pair_to_r1r2(0x384);\n", ["0384"]),
                         dis.NAMES_OTHER_ADDRESSES)

    def test_a_character_constant_is_not_the_address_zero(self):
        # `'\0'` is a character. Read as a decimal it would make the address
        # 0x0000 nameable by any body that zeroes a variable, which is most of
        # them.
        self.assertEqual(classify("  cVar = '\\0';\n", ["0000"]),
                         dis.NAMES_NOTHING)

    def test_a_body_naming_some_other_address_is_names_other_addresses(self):
        self.assertEqual(classify("  return DAT_EXTMEM_0a52;\n", ["0A51"]),
                         dis.NAMES_OTHER_ADDRESSES)

    def test_a_body_naming_nothing_at_all_is_names_nothing(self):
        self.assertEqual(classify("  return *param_1;\n", ["0408"]),
                         dis.NAMES_NOTHING)

    def test_a_row_split_between_two_causes_falls_through(self):
        # A class that fired when *one* address matched would describe half of
        # such a row and none of the other half.
        self.assertEqual(
            classify("  store_be16_a(MAIN_FAN_R_DUTY,0xa48,"
                     "read_xdata_pair_to_r1r2);\n", ["075C", "0384"]),
            dis.NAMES_OTHER_ADDRESSES)

    def test_an_unclassifiable_row_is_left_unclassified_rather_than_guessed(self):
        self.assertEqual(classify(None, ["075C"]), "")
        self.assertEqual(classify("  MAIN_FAN_R_DUTY = *param_1;\n", []), "")

    def test_a_missing_export_and_an_out_file_of_none_read_the_same(self):
        for out_file in ("", None, "(no-instructions)", "bank0/DOES-NOT-EXIST.c"):
            with self.subTest(out_file=out_file):
                self.assertIsNone(dis.c_body(out_file, dis.strip_every_comment))
                self.assertEqual(
                    dis.classify_row("bank0", 0xB158, out_file, ["075C"],
                                     NAMES_075C, dis.strip_every_comment), "")

    def test_the_vocabulary_is_closed_and_held_by_name(self):
        # Not by length: a sixth reading of `disagree` added as a synonym for
        # one of these would keep the counts right and let `--check` go green.
        self.assertEqual(set(dis.CAUSES),
                         {dis.NAMED_BY_REGISTER_SYMBOL, dis.NAMED_BY_CODE_SYMBOL,
                          dis.NAMED_BY_DECIMAL_LITERAL, dis.NAMES_OTHER_ADDRESSES,
                          dis.NAMES_NOTHING})
        self.assertEqual(set(dis.CAUSE_REASONS), set(dis.CAUSES))
        for cause in dis.CAUSES:
            with self.subTest(cause=cause):
                self.assertIsInstance(dis.CAUSE_REASONS[cause], str)
                self.assertTrue(dis.CAUSE_REASONS[cause].strip())


class SymbolTable(unittest.TestCase):
    """The name table the first cause is read out of."""

    def test_it_is_the_committed_one_and_not_a_list_written_here(self):
        table = dis.register_symbol_names()
        self.assertTrue(table)
        self.assertEqual(table, dis.register_symbol_names())

    def test_a_name_given_to_two_addresses_answers_for_both_and_neither_else(self):
        # A set rather than a scalar, because `register_symbol_named()` asks
        # whether *this* address is among them; a name shared by two bytes must
        # not name a third by accident.
        table = {"TWO": {0x0100, 0x0200}}
        self.assertTrue(dis.register_symbol_named("  TWO = 1;\n", 0x0100, table))
        self.assertTrue(dis.register_symbol_named("  TWO = 1;\n", 0x0200, table))
        self.assertFalse(dis.register_symbol_named("  TWO = 1;\n", 0x0300, table))

    def test_a_name_matched_inside_a_longer_identifier_is_not_a_match(self):
        self.assertFalse(dis.register_symbol_named("  TWO_x = 1;\n", 0x0100,
                                                   {"TWO": {0x0100}}))


class CodeSpace(unittest.TestCase):
    """The code-space spelling, read off the C rather than off the vocabulary."""

    def test_both_spellings_and_neither_a_lookalike(self):
        for text in ("  &DAT_CODE_632d", "  FUN_CODE_632d"):
            with self.subTest(text=text):
                self.assertTrue(dis.code_symbol_named(text, 0x632D))
        self.assertFalse(dis.code_symbol_named("  DAT_CODE_632d0", 0x632D))
        self.assertFalse(dis.code_symbol_named("  XCODE_632d", 0x632D))


class Partition(unittest.TestCase):
    """The classification is a partition of the disagree rows, and nothing else."""

    def test_the_committed_tree_partitions(self):
        self.assertEqual(dis.partition_problems(rows(), parent()), [])

    def test_the_five_counts_sum_to_the_disagree_row_count(self):
        # A relationship rather than a census: this holds at any sample size,
        # and it is the property that makes the five numbers one measurement.
        disagree = sum(1 for r in parent() if r["outcome"] == "disagree")
        self.assertGreater(disagree, 0)
        self.assertEqual(sum(dis.census(rows()).values()), disagree)

    def test_a_row_falling_in_no_cause_is_reported_rather_than_dropped(self):
        broken = [dict(r) for r in rows()]
        victim = next(i for i, r in enumerate(broken)
                      if r["cause"] == dis.NAMES_OTHER_ADDRESSES)
        broken[victim]["cause"] = ""
        problems = dis.partition_problems(broken, parent())
        self.assertEqual(len(problems), 1)
        self.assertIn("disagree and carries no `cause`", problems[0])

    def test_a_cause_on_a_row_that_is_not_disagree_is_reported(self):
        broken = [dict(r) for r in rows()]
        victim = next(i for i, r in enumerate(broken) if r["outcome"] == "agree")
        broken[victim]["cause"] = dis.NAMES_NOTHING
        problems = dis.partition_problems(broken, parent())
        self.assertEqual(len(problems), 1)
        self.assertIn("only a disagree row is in scope", problems[0])

    def test_a_cause_outside_the_closed_vocabulary_is_reported(self):
        broken = [dict(r) for r in rows()]
        victim = next(i for i, r in enumerate(broken) if r["cause"])
        broken[victim]["cause"] = "named-by-something-else"
        problems = dis.partition_problems(broken, parent())
        self.assertEqual(len(problems), 1)
        self.assertIn("closed vocabulary", problems[0])

    def test_a_disagree_row_with_no_sidecar_row_at_all_is_reported(self):
        short = [r for r in rows() if r["cause"] != dis.NAMED_BY_REGISTER_SYMBOL]
        problems = dis.partition_problems(short, parent())
        self.assertTrue(problems)
        self.assertTrue(all("has no row in the sidecar" in p for p in problems))


class KnownAnswers(unittest.TestCase):
    """The functions this tool is pinned on, at what each reads on this tree.

    `bank0 0xB158` is the row §14i's byte-pair fold and issue #510 named, and
    it is pinned at `named-by-register-symbol` rather than at a fold of its own.
    That is not a softening and not a typo: the class is about where the
    address is spelled, and 0x0438/0x0439 reach the C as `BAT_VOLTAGE_MV_0` and
    `BAT_VOLTAGE_MV_1` inside one `store_be16_a` argument list. A cause called
    "the fold" would need a judgement about which of a function's reads is a
    fold, which is the guess `CROSS_DECODER_OUTCOMES` refuses.
    """

    def test_each_named_function_reads_what_the_table_says(self):
        by_key = {(r["program"], r["addr"]): r for r in rows()}
        for program, addr, name, want in dis.KNOWN_ANSWERS:
            with self.subTest(program=program, addr=addr):
                row = by_key[(program, addr)]
                self.assertEqual(row["name"], name)
                self.assertEqual(row["outcome"], "disagree")
                self.assertEqual(row["cause"], want)

    def test_all_nine_are_disagree_rows_the_parent_also_records(self):
        disagree = {(r["program"], r["addr"]) for r in parent()
                    if r["outcome"] == "disagree"}
        for program, addr, _name, _want in dis.KNOWN_ANSWERS:
            with self.subTest(program=program, addr=addr):
                self.assertIn((program, addr), disagree)

    def test_every_cause_is_represented_and_none_twice_for_nothing(self):
        # A guard against the table quietly losing its diversity: if a future
        # change collapsed the classifier, `KNOWN_ANSWERS` would keep passing
        # on one cause while the census stopped saying anything.
        self.assertEqual({want for _, _, _, want in dis.KNOWN_ANSWERS},
                         set(dis.CAUSES))

    def test_the_issue_row_is_agree_now_and_carries_no_cause(self):
        # `pd 0xF4CD` is the done-when: the same listing, the same address, an
        # `agree` verdict for a reason about the spelling, and therefore nothing
        # for a `disagree` sidecar to classify.
        by_key = {(r["program"], r["addr"]): r for r in rows()}
        row = by_key[("pd", "F4CD")]
        self.assertEqual(row["outcome"], "agree")
        self.assertEqual(row["cause"], "")
        committed = {(r["program"], r["addr"]): r
                     for r in bld.read_index(bld.CROSS_DECODER)}
        self.assertEqual(committed[("pd", "F4CD")]["in_c"], "07D6")
        self.assertEqual(committed[("pd", "F4CD")]["missing"], "")

    def test_the_documented_fold_is_still_the_measurement(self):
        # `B158` reads `named-by-register-symbol`, so the case has to assert the
        # thing that makes that right: the two addresses really are named, by
        # names the symbol table really carries, and really are not readable by
        # the comparison's own matcher.
        body = dis.c_body("bank0/B158.c", dis.strip_every_comment)
        table = dis.register_symbol_names()
        for addr in (0x0438, 0x0439):
            with self.subTest(addr="%04X" % addr):
                self.assertTrue(dis.register_symbol_named(body, addr, table))
                self.assertNotIn("%04X" % addr, bld.names_an_address(body))
        self.assertIn("store_be16_a", body)


class HeaderComment(unittest.TestCase):
    """Which comment is removed, and that the census does not depend on it."""

    def test_an_address_named_only_in_the_annotation_is_not_the_bodys(self):
        annotated = ("/* DPTR is loaded from 0x07D6 before the call.\n"
                     "   type: forwarder\n"
                     "   evidence: ec/decompiled/pd/F4CD.c */\n"
                     "void f(void)\n{\n  DAT_EXTMEM_09c7 = 1;\n}\n")
        self.assertEqual(bld.names_an_address(annotated), {"09C7"})

    def test_a_ghidra_warning_is_not_the_annotation_comment(self):
        warned = ("/* WARNING: Do nothing block with infinite loop */\n"
                  "void f(void)\n{\n  DAT_EXTMEM_09c7 = 1;\n}\n")
        self.assertEqual(bld.names_an_address(warned), {"09C7"})

    def test_a_c_with_no_annotation_comment_keeps_its_body(self):
        plain = "void f(void)\n{\n  DAT_EXTMEM_09c7 = 1;\n}\n"
        self.assertEqual(bld.names_an_address(plain), {"09C7"})

    def test_the_census_is_the_same_under_either_stripping_rule(self):
        # The rule in the docstring is a choice, and this is what makes it one:
        # the counts do not depend on which of the two strippers decides the
        # missing set. Asserted rather than described, because a rule whose
        # result had quietly become load-bearing would still read the same in
        # the docstring.
        self.assertEqual(dis.census(rows()),
                         dis.census(dis.disagreement_rows(
                             image(), dis.strip_every_comment)))

    def test_the_whole_file_would_agree_where_the_body_disagrees(self):
        # The negative half of the same rule, on the tree rather than on a
        # fixture: matching the file rather than the code is what would turn an
        # annotation's summary of a function into a decode of it, and the two
        # readings disagree about the whole disagree bucket rather than one row.
        whole = bld.cross_decoder_summary(bld.cross_decoder_results(image(),
                                                                    lambda t: t))
        body = bld.cross_decoder_summary(bld.cross_decoder_results(image()))
        self.assertLess(whole["disagree"], body["disagree"])
        self.assertGreater(whole["agree"], body["agree"])


class Direction(unittest.TestCase):
    """No sampled row moved `agree` -> `disagree`.

    The property issue #510 asks for, over the whole sample rather than over a
    row, and expressed as a relation between the committed report and this run
    so it survives every future export. A widening can only grow the set of
    addresses the matcher accepts, so `missing` can only shrink; the one way a
    row reaches `disagree` on the spelling route is for the matcher to have
    narrowed, which is a change a `--check` diff will catch and a reader should
    not have to.
    """

    def test_no_sampled_row_regressed(self):
        committed = {(r["program"], r["addr"]): r
                     for r in bld.read_index(bld.CROSS_DECODER)}
        current = {(r["program"], r["addr"]): r
                   for r in bld.cross_decoder_results(image())}
        regressed = sorted(k for k in set(committed) & set(current)
                           if committed[k]["outcome"] == "agree"
                           and current[k]["outcome"] == "disagree")
        self.assertEqual(regressed, [])

    def test_the_matcher_only_grows(self):
        # The mechanism behind the property above, on the tree rather than on
        # the report: for every sampled row, the set of addresses the body
        # names is a superset of what `_EXTMEM` alone read out of the same text.
        listing = {(r["program"], r["addr"]): r
                   for r in bld.read_index(bld.LISTING_INDEX)}
        narrowed = []
        for row, _kind in bld.cross_decoder_sample():
            listed = listing[(row["program"], row["addr"])]
            out_file = listed["out_file"]
            if not out_file or out_file.startswith("("):
                continue
            path = os.path.join(bld.OUTDIR, out_file.replace(".asm", ".c"))
            if not os.path.isfile(path):
                continue
            with open(path, errors="replace") as f:
                body = bld.strip_header_comment(f.read())
            narrow = {m.group(1).upper() for m in bld._EXTMEM.finditer(body)}
            if not narrow <= bld.names_an_address(body):
                narrowed.append((row["program"], row["addr"]))
        self.assertEqual(narrowed[:3], [])

    def test_the_diagnostic_names_the_direction_rather_than_saying_look(self):
        agreed = {"program": "bank0", "addr": "B1F0", "outcome": "agree"}
        split = {"program": "bank0", "addr": "B1F0", "outcome": "disagree"}
        note = bld.direction_note(agreed, split, "outcome")
        self.assertIn("one direction a widening cannot produce", note)
        self.assertNotIn("the export or the comparison moved", note)
        # And the other columns keep the general clause: an `insns` that moved
        # is not the decompiler regressing and not the matcher narrowing.
        self.assertEqual(bld.direction_note(agreed, split, "insns"),
                         "the export or the comparison moved")


class Ratchet(unittest.TestCase):
    """`--check` driven in both directions, and the sidecar's reproducibility."""

    def _sidecar(self):
        return bld.read_index(dis.DISAGREEMENT)

    def test_the_committed_sidecar_is_a_fresh_derivation(self):
        with open(dis.DISAGREEMENT, newline="") as f:
            header = next(csv.reader(f))
        with open(dis.DISAGREEMENT) as f:
            on_disk = f.read()
        self.assertEqual(header, dis.CAUSE_COLUMNS)
        self.assertEqual(dis.render(rows()), on_disk)

    def test_it_carries_the_parent_keys_and_only_the_disagree_rows_are_caused(self):
        self.assertEqual([(r["program"], r["addr"]) for r in self._sidecar()],
                         [(r["program"], r["addr"]) for r in parent()])
        self.assertEqual(dis.partition_problems(self._sidecar(), parent()), [])

    def test_it_carries_no_missing_column(self):
        # `missing` is recomputed by `classify_row()` precisely so that it is
        # not the column; a copy of it beside the cause would be a second answer
        # to the same question.
        self.assertNotIn("missing", dis.CAUSE_COLUMNS)

    def test_a_doctored_cell_is_caught(self):
        doctored = [dict(r) for r in self._sidecar()]
        # A row that is not already `names-nothing`, so the edit is an edit: a
        # victim picked without that condition would pass silently on the rows
        # it happened to pick.
        victim = next(i for i, r in enumerate(doctored)
                      if r["cause"] and r["cause"] != dis.NAMES_NOTHING)
        doctored[victim]["cause"] = dis.NAMES_NOTHING
        compared, problems = dis.disagreement_problems(doctored, rows())
        self.assertEqual(len(problems), 1)
        self.assertIn("cause", problems[0])
        self.assertIn("regenerate", problems[0])
        self.assertGreater(compared, 0)

    def test_a_doctored_name_is_caught_too(self):
        # The ratchet compares every column, not just the cause, so a renamed
        # function in the parent cannot pass unnoticed here.
        doctored = [dict(r) for r in self._sidecar()]
        doctored[0]["name"] = "renamed"
        _compared, problems = dis.disagreement_problems(doctored, rows())
        self.assertEqual(len(problems), 1)
        self.assertIn("name", problems[0])

    def test_a_row_the_sample_no_longer_has_is_caught(self):
        # A phantom committed row the current sample does not carry, so the
        # parent of these three is named: a report that has outlasted the
        # export it describes.
        extra = self._sidecar() + [dict(self._sidecar()[0], addr="FFFF")]
        _compared, problems = dis.disagreement_problems(extra, rows())
        self.assertEqual(len(problems), 1)
        self.assertIn("not in the sample", problems[0])

    def test_a_row_the_sample_gained_is_caught(self):
        # The other direction: a committed row missing from the sidecar, which
        # is the one a sidecar holding only the classified rows could not see.
        short = self._sidecar()[1:]
        _compared, problems = dis.disagreement_problems(short, rows())
        self.assertEqual(len(problems), 1)
        self.assertIn("in the sample and not in the sidecar", problems[0])

    def test_an_identical_copy_has_no_problems(self):
        # The known-good case, first on purpose in `--check`'s own run: a guard
        # exercised only on doctored input cannot tell "clean" from "never ran".
        compared, problems = dis.disagreement_problems(self._sidecar(), rows())
        self.assertEqual(problems, [])
        self.assertEqual(compared, len(rows()))


class CommandLine(unittest.TestCase):
    """The tool as a command, including the refusals."""

    def _run(self, *args, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = dis.main(list(args))
        return rc, out.getvalue(), err.getvalue()

    def test_check_passes_on_the_committed_sidecar(self):
        rc, out, _err = self._run("--check")
        self.assertEqual(rc, 0)
        self.assertIn("every cell agreeing with", out)

    def test_check_fails_when_the_sidecar_is_missing_and_does_not_create_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            absent = os.path.join(tmp, "cross-decoder-disagreement.csv")
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
            with open(path) as written, open(dis.DISAGREEMENT) as committed:
                self.assertEqual(written.read(), committed.read())

    def test_the_plain_run_prints_the_census_and_every_cause_is_explained(self):
        rc, out, _err = self._run()
        self.assertEqual(rc, 0)
        for cause in dis.CAUSES:
            with self.subTest(cause=cause):
                self.assertIn(cause, out)
                self.assertIn(dis.CAUSE_REASONS[cause], out)
        self.assertRegex(out, r"the \d+ disagree row\(s\) are .* of \d+ "
                              r"sampled function\(s\)")

    def test_the_render_is_byte_identical_run_to_run(self):
        # What the ratchet rests on. A sidecar whose bytes moved between two
        # runs of the same inputs would make `--check` a coin flip.
        self.assertEqual(dis.render(rows()), dis.render(rows()))


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
            bld.cross_decoder_summary(bld.read_index(dis.CROSS_DECODER)))
        recomputed = bld.denominator_line(
            bld.cross_decoder_summary(bld.cross_decoder_results(image())))
        self.assertEqual(committed, recomputed)

    def test_nothing_was_added_to_the_comparison_own_vocabulary(self):
        self.assertEqual(bld.CROSS_DECODER_OUTCOMES,
                         ("agree", "disagree", "vacuous", "no-export"))
        self.assertNotIn("cause", bld.CROSS_DECODER_OUTCOMES)
        self.assertEqual(bld.CROSS_DECODER_COLUMNS,
                         ["program", "addr", "name", "sample", "insns", "linear",
                          "in_c", "missing", "outcome"])

    def test_the_parents_report_is_unchanged_by_this_tool(self):
        # The sidecar is derived; the parent is not written by anything here.
        self.assertEqual(dis.CROSS_DECODER,
                         os.path.join(HERE.parent, 'ghidra', 'cross-decoder.csv'))

    def test_a_full_run_writes_the_sidecar_and_nothing_else(self):
        # A cause is a fact about how a C spells an address, and none of it is a
        # claim about the EC -- so the annotation layer has to come out of a
        # full `--report` exactly as it went in, byte for byte. Measured over
        # the whole directory rather than over the two files this tool reads, so
        # a future write to a third one is caught too.
        def snapshot(root):
            return {str(p.relative_to(root)): p.stat().st_mtime_ns
                    for p in sorted(root.rglob('*')) if p.is_file()}

        before = snapshot(HERE.parent / 'annotations')
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = dis.main(["--report", "--sidecar",
                               os.path.join(tmp, "sidecar.csv")])
            self.assertEqual(rc, 0)
        self.assertEqual(snapshot(HERE.parent / 'annotations'), before)
        # And the export it reads is untouched for the same reason.
        self.assertIn(dis.XDATA,
                      [str(p) for p in (HERE.parent / 'ghidra').iterdir()])


if __name__ == "__main__":
    unittest.main()
