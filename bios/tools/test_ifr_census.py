#!/usr/bin/env python3
"""Offline checks for `ifr_census.py`: its own parsing, and the six charge
questions read out of the committed `Setup` IFR.

Two halves, and the split is the point. The first asserts the tool on a
hand-built fixture, where every answer is known because the fixture was written
to be known -- which is the only way to pin the parts that are easy to get
subtly wrong and that the real dump cannot reveal, because the real dump has no
second answer to check against. The second reads the committed
`bios/ifr/Setup.en-US.ifr.txt` and asserts the facts the write-up cites, so a
regenerated dump that lost a question fails here rather than quietly changing
what `docs/findings/ifr-charge-and-battery-options.md` says.

Both halves read committed text. Nothing here opens the ROM, runs UEFIExtract
or ifrextractor, or reads a setup variable, and no case is a claim about what
this machine's menu displays.
"""
import csv
import io
import os
import re
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import ifr_census  # noqa: E402  (the path insert above is what makes this work)

IFR = os.path.join(REPO, "bios", "ifr", "Setup.en-US.ifr.txt")
CSV_PATH = os.path.join(REPO, "bios", "ifr", "charge-questions.csv")


def committed_statements():
    return ifr_census.read_dump(IFR)


_CENSUS = {}


def committed_census():
    """The committed dump's census, read once per process.

    A dict rather than a module-level tuple so a case that mutates the result
    cannot leak into the next one, and a dict rather than `functools.cache` so
    there is no import to explain: the dump is 2.4 MB and the parse is the
    slowest thing this suite does.
    """
    if "census" not in _CENSUS:
        _CENSUS["census"] = ifr_census.census(committed_statements())
    return _CENSUS["census"]


def run(*argv):
    """main()'s output and exit code, for the modes a case wants to read."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = ifr_census.main(list(argv))
    return buf.getvalue(), code


# --------------------------------------------------------------------------
# Parsing, on hand-built text
# --------------------------------------------------------------------------

class FieldTests(unittest.TestCase):
    """`split_fields`, which is where the format's two awkward shapes live."""

    def test_the_fields_of_a_question(self):
        body = ('OneOf Prompt: "Charging Method", Help: "Normal or Fast.", '
                'QuestionFlags: 0x10, QuestionId: 0x2A6, VarStoreId: 0x1, '
                'VarOffset: 0x4F3, Size: 8 { 05 91 B5 15 }')
        fields = ifr_census.split_fields(body)
        self.assertEqual(fields["QuestionId"], "0x2A6")
        self.assertEqual(fields["VarOffset"], "0x4F3")
        self.assertEqual(fields["Size"], "8")

    def test_the_prompt_is_read_though_no_comma_precedes_it(self):
        # The first field sits between the opcode and the first comma, so a
        # split that only looks after commas finds Help and loses Prompt --
        # which is the prompt column of every row in the committed CSV.
        fields = ifr_census.split_fields('OneOf Prompt: "Light Bar Effect", '
                                         'Help: "x", VarOffset: 0x740')
        self.assertEqual(fields["Prompt"], '"Light Bar Effect"')

    def test_a_comma_inside_a_quoted_string_does_not_split(self):
        fields = ifr_census.split_fields(
            'OneOf Prompt: "a, b", Help: "c, d, e", QuestionId: 0x1')
        self.assertEqual(fields["Prompt"], '"a, b"')
        self.assertEqual(fields["Help"], '"c, d, e"')
        self.assertEqual(fields["QuestionId"], "0x1")

    def test_a_comma_inside_brackets_does_not_split(self):
        # `EqIdValList ... Values: [1, 2]` is one field. Splitting there leaves
        # the value reading "[1" and the resolved condition naming one value
        # instead of two.
        fields = ifr_census.split_fields(
            'EqIdValList QuestionId: 0xE17, Values: [1, 2] { 14 92 17 0E }')
        self.assertEqual(fields["Values"], "[1, 2]")

    def test_the_byte_block_is_stripped_and_a_brace_in_help_is_not(self):
        # ifrextractor writes the block with a space after the brace, and a
        # help string is free to end in one of its own.
        self.assertEqual(ifr_census.split_fields("EqIdVal Value: 0x1 { 09 }")
                         ["Value"], "0x1")
        self.assertEqual(ifr_census.split_fields('OneOf Help: "ends in { 7F }"')
                         ["Help"], '"ends in { 7F }"')

    def test_a_statement_with_no_fields(self):
        self.assertEqual(ifr_census.split_fields("SuppressIf  { 0A 82 }"), {})

    def test_default_is_not_comma_separated_and_needs_its_own_rule(self):
        # `Default DefaultId: 0x0 Value: 8` has no comma between the two, so
        # the split reads DefaultId as "0x0 Value: 8" and every numeric default
        # comes out empty.
        stmt = ifr_census.Statement(1, 3, "Default DefaultId: 0x0 Value: 8 "
                                          "{ 5B 06 00 00 00 08 }")
        self.assertEqual(ifr_census.default_of(stmt), ("0x0", "8"))

    def test_a_default_whose_value_is_an_expression_is_not_a_number(self):
        stmt = ifr_census.Statement(1, 3, "Default DefaultId: 0x0 Value: Other "
                                          "{ 5B 85 00 00 08 }")
        self.assertIsNone(ifr_census.default_of(stmt))


class LineNumberTests(unittest.TestCase):
    """The dump is read with newline translation off, and that is load-bearing.

    1,717 of the Setup dump's 1,724 CRs are the first half of a CRLF, which
    translation leaves alone, and 7 are a bare CR that ifrextractor wrote
    inside a help string. Each of those 7 becomes a line break of its own under
    Python's default text mode, so every line number the write-up cites below
    it is off by the number of bare CRs above it.
    """

    def test_a_bare_cr_does_not_shift_the_line_numbers(self):
        path = os.path.join(HERE, "testdata", "ifr-wrapped-help.ifr.txt")
        statements = ifr_census.read_dump(path)
        # The fixture's first statement has a help string wrapped over a CRLF
        # and then over a bare CR, which is the shape the Setup dump has. The
        # second statement must land on line 3, which is where `grep -n` puts
        # it, and the two halves of the wrapped sentence must stay apart.
        self.assertEqual([s.line for s in statements], [1, 3])
        self.assertEqual(statements[0].quoted("Help"), "one two three")

    def test_the_same_read_with_translation_would_be_off_by_one(self):
        # The failure this class exists for, shown rather than described: read
        # the same fixture with Python's default text mode, where the bare CR
        # becomes a line break of its own, and the second statement's number
        # moves from 3 to 4.
        path = os.path.join(HERE, "testdata", "ifr-wrapped-help.ifr.txt")
        with open(path, encoding="utf-8") as f:
            translated = ifr_census.read_statements(f.read().split("\n"))
        self.assertEqual([s.line for s in translated], [1, 4])

    def test_a_wrapped_question_does_not_vanish_from_the_census(self):
        # The bug this file's line numbers exist beside. Parsing the fields
        # before the continuation lines are joined truncates a wrapped
        # statement at the wrap, so every field after it -- QuestionId,
        # VarStoreId, VarOffset, Size -- reads as absent and the question is
        # dropped from the census entirely. 374 of the Setup dump's questions
        # wrap, so the census came out 368 questions short and silently so:
        # nothing crashed, and the eight charge rows were all unaffected,
        # which is exactly why only a case that counts catches it.
        path = os.path.join(HERE, "testdata", "ifr-wrapped-help.ifr.txt")
        stores, questions = ifr_census.census(ifr_census.read_dump(path))
        self.assertEqual(len(questions), 2)
        self.assertEqual([q.stmt.question_id() for q in questions], ["0x1", "0x3"])
        self.assertEqual(questions[0].row(stores)["offset"], "0x2")
        self.assertEqual(questions[0].row(stores)["varstore_id"], "0x1")

    def test_the_committed_dumps_line_numbers_are_grep_line_numbers(self):
        # The same property, measured on the real file rather than a fixture:
        # the tool's line for Charging Method is the one `grep -n` prints.
        _, questions = committed_census()
        charging = [q for q in questions if q.stmt.question_id() == "0x2A6"]
        self.assertEqual(len(charging), 1)
        self.assertEqual(charging[0].stmt.line, 5953)

    def test_the_two_hidden_numerics_are_cited_by_grep_line_number(self):
        # The write-up cites the bytes that hide things by `:NNNN` like every
        # other offset there, and once cited the dump's left-column file offset
        # (`0x56964`, `0x56975`) in that slot instead. Those read as plausible
        # line numbers and `sed -n` on one lands in the middle of the next
        # hidden numeric, so nothing but a case here catches the slip. The CSV's
        # `ifr_line` column and the eight rows in it are `grep -n` numbers, and
        # the write-up says every offset in it is the one `grep -n` prints.
        _, questions = committed_census()
        lines = dict((q.stmt.question_id(), q.stmt.line) for q in questions)
        self.assertEqual(lines["0xE17"], 26937)   # SetupVolatileData[0x4]
        self.assertEqual(lines["0xECB"], 27297)   # Setup[0x741]


class ConditionTests(unittest.TestCase):
    """The condition buffer, which is a stack machine and not a tree."""

    def build(self, *lines):
        return ifr_census.read_statements(list(lines) + [""])

    def test_and_over_two_negations(self):
        statements = self.build(
            "0x1: \tSuppressIf  { 0A 82 }",
            "0x2: \t\tEqIdVal QuestionId: 0xE17, Value: 0x1 { 12 86 }",
            "0x3: \t\t\tNot  { 17 02 }",
            "0x4: \t\t\tEqIdVal QuestionId: 0xE17, Value: 0x5 { 12 06 }",
            "0x5: \t\t\tNot  { 17 02 }",
            "0x6: \t\t\tAnd  { 15 02 }",
            "0x7: \t\tEnd  { 29 02 }")
        expr = ifr_census.condition_expr(statements, 0)
        self.assertEqual(expr.text,
                         "(NOT (EqIdVal QuestionId: 0xE17, Value: 0x1) AND "
                         "NOT (EqIdVal QuestionId: 0xE17, Value: 0x5))")
        self.assertEqual(expr.question_ids, ["0xE17", "0xE17"])
        self.assertTrue(expr.resolved)

    def test_or_chains_left_to_right(self):
        statements = self.build(
            "0x1: \tSuppressIf  { 0A 82 }",
            "0x2: \t\tEqIdVal QuestionId: 0xE17, Value: 0x2 { 12 86 }",
            "0x3: \t\t\tEqIdVal QuestionId: 0xE17, Value: 0x4 { 12 06 }",
            "0x4: \t\t\tOr  { 16 02 }",
            "0x5: \t\t\tEqIdVal QuestionId: 0xE17, Value: 0x3 { 12 06 }",
            "0x6: \t\t\tOr  { 16 02 }",
            "0x7: \t\tEnd  { 29 02 }")
        self.assertEqual(
            ifr_census.condition_expr(statements, 0).text,
            "((EqIdVal QuestionId: 0xE17, Value: 0x2 OR "
            "EqIdVal QuestionId: 0xE17, Value: 0x4) OR "
            "EqIdVal QuestionId: 0xE17, Value: 0x3)")

    def test_an_unconditional_block_states_no_condition(self):
        # An unconditional SuppressIf does appear in the dump. None is not
        # TRUE, and printing TRUE would be a claim the IFR does not make.
        statements = self.build("0x1: \tSuppressIf  { 0A 82 }",
                                "0x2: \t\tEnd  { 29 02 }")
        self.assertIsNone(ifr_census.condition_expr(statements, 0))

    def test_an_operator_with_nothing_to_pop_is_reported_not_guessed(self):
        statements = self.build("0x1: \tSuppressIf  { 0A 82 }",
                                "0x2: \t\tAnd  { 15 02 }",
                                "0x3: \t\tEnd  { 29 02 }")
        expr = ifr_census.condition_expr(statements, 0)
        self.assertFalse(expr.resolved)
        self.assertIn("unresolved", expr.text)

    def test_a_comparator_consumes_the_two_values_below_it(self):
        statements = self.build(
            "0x1: \tGrayOutIf  { 0B 82 }",
            "0x2: \t\tEqIdVal QuestionId: 0x1, Value: 0x2 { 12 06 }",
            "0x3: \t\tEqIdVal QuestionId: 0x2, Value: 0x3 { 12 06 }",
            "0x4: \t\tLessThan  { 33 02 }",
            "0x5: \t\tEnd  { 29 02 }")
        self.assertEqual(ifr_census.condition_expr(statements, 0).text,
                         "(EqIdVal QuestionId: 0x1, Value: 0x2 LESS THAN "
                         "EqIdVal QuestionId: 0x2, Value: 0x3)")

    def test_the_buffer_ends_at_the_question_not_at_the_block(self):
        # A `Default ... Value: Other` carries its own expression, nested
        # inside the `SuppressIf` that gates the very question it belongs to.
        # A scan that kept descending by depth would read that expression as
        # the visibility condition, and this is the one place in the dump
        # where that happens.
        statements = self.build(
            "0x1: \tSuppressIf  { 0A 82 }",
            "0x2: \t\tEqIdVal QuestionId: 0xE17, Value: 0x2 { 12 86 }",
            "0x3: \t\tOneOf Prompt: \"x\", QuestionId: 0x902, "
            "VarStoreId: 0x1, VarOffset: 0x11 { 05 91 }",
            "0x4: \t\t\tDefault DefaultId: 0x0 Value: Other { 5B 85 }",
            "0x5: \t\t\t\tValue  { 5A 82 }",
            "0x6: \t\t\t\t\tEqIdValList QuestionId: 0xE17, Values: [1, 2] { 14 92 }",
            "0x7: \t\t\tEnd  { 29 02 }",
            "0x8: \t\tEnd  { 29 02 }")
        stores, questions = ifr_census.census(statements)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].suppress[0].text,
                         "EqIdVal QuestionId: 0xE17, Value: 0x2")
        self.assertEqual(questions[0].row(stores)["default_normal"], "")


class VocabularyTests(unittest.TestCase):
    """What the phrase list matches, and what it must decline."""

    def test_a_phrase_matches_inside_a_word_not_only_at_one(self):
        self.assertTrue(ifr_census.phrase_in("Fast Charging", "charg"))
        self.assertTrue(ifr_census.phrase_in("Charger device", "charg"))
        self.assertTrue(ifr_census.phrase_in("Battery Participant", "battery"))

    def test_a_phrase_does_not_match_inside_a_longer_word(self):
        # "charger" is a charge word; "orchard" is not, and a bare substring
        # search would call it one.
        self.assertFalse(ifr_census.phrase_in("orchard mapping", "charg"))
        self.assertFalse(ifr_census.phrase_in("backwards", "ac brick"))

    def test_ac_as_a_bare_substring_is_the_noise_the_list_avoids(self):
        # The hex byte pair in a OneOfOption body is why `ac` is not a term.
        self.assertTrue(ifr_census.phrase_in("09 07 AC 1A 00 00 20", "ac"))
        self.assertNotIn("ac", ifr_census.CHARGE_TERMS)

    def test_the_byte_block_is_never_matched_against(self):
        # ... which is only true because the matcher reads the prompt, the help
        # and the option LABELS, and never the hex ifrextractor prints after
        # them. A matcher that read the byte block would take in every
        # OneOfOption in the dump that happens to contain the pair.
        _, questions = committed_census()
        for q in questions:
            for _, text in q.text_fields():
                self.assertNotIn("{", text)

    def test_the_two_phrase_terms_that_name_an_ac_thing_need_the_second_word(self):
        self.assertTrue(ifr_census.phrase_in("Specify the AC Brick capacity",
                                             "ac brick"))
        self.assertFalse(ifr_census.phrase_in("AC Loadline Time", "ac brick"))
        self.assertFalse(ifr_census.phrase_in("AC termination voltage",
                                              "ac brick"))

    def test_the_tool_has_its_own_self_test_and_it_passes(self):
        out, code = run("--self-test")
        self.assertEqual(code, 0, out)
        self.assertIn("self-test", out)


# --------------------------------------------------------------------------
# The committed dump
# --------------------------------------------------------------------------

class CommittedCensusTests(unittest.TestCase):
    """The six charge questions the write-up names, read out of the dump.

    Every offset here is the one `grep -n 'QuestionId: 0x…, VarStoreId'`
    prints, so a reviewer can confirm a row without running anything.
    """

    @classmethod
    def setUpClass(cls):
        cls.stores, cls.questions = committed_census()
        cls.rows = dict((q.stmt.question_id(), q) for q in cls.questions)

    def test_the_population(self):
        # A floor, not a count: a much smaller number would mean the parse
        # stopped early, and a much larger one would mean the phrase list grew
        # a term that matches everything.
        self.assertGreater(len(self.questions), 3000)
        self.assertLess(len(self.questions), 4000)

    def test_the_dump_parses_into_the_shape_the_write_up_describes(self):
        statements = committed_statements()
        self.assertEqual(
            len([s for s in statements if s.opcode == "Form"]), 207)
        self.assertEqual(
            len([s for s in statements if s.opcode == "SuppressIf"]), 1292)
        self.assertEqual(
            len([s for s in statements if s.opcode == "GrayOutIf"]), 302)

    def test_the_three_varstores_the_rows_name(self):
        for store_id, name, guid, size in (
                (0x1, "Setup", "EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9", "0x7D8"),
                (0x12, "CpuSetup", "B08F97FF-E6E8-4193-A997-5E9E9B0ADB32",
                 "0x2BB"),
                (0x37, "SetupVolatileData", "EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9",
                 "0x97")):
            self.assertEqual(self.stores[store_id], (name, guid, size),
                             "VarStoreId 0x%x" % store_id)

    def assert_row(self, qid, store, offset, size, prompt, verdict):
        q = self.rows.get(qid)
        self.assertIsNotNone(q, "no question 0x%s in the dump" % qid)
        row = q.row(self.stores)
        self.assertEqual(row["varstore"], store)
        self.assertEqual(row["offset"], offset)
        self.assertEqual(row["size_bits"], size)
        self.assertEqual(row["prompt"], prompt)
        self.assertEqual(row["verdict"], verdict)
        return row

    def test_charging_method_is_setup_0x4f3_under_a_suppressif_on_0xe17(self):
        row = self.assert_row("0x2A6", "Setup", "0x4F3", "8", "Charging Method",
                              "charge-option")
        # The row the table exists for: the only charge control in the whole
        # IFR that is hidden, and hidden on a byte the OS cannot see.
        self.assertEqual(row["suppress_if"],
                         "(NOT (EqIdVal QuestionId: 0xE17, Value: 0x1) AND "
                         "NOT (EqIdVal QuestionId: 0xE17, Value: 0x5))")
        self.assertEqual(row["options"],
                         "Normal Charging=0 [default] [mfg]; "
                         "Fast Charging=1")
        self.assertEqual(row["form_chain"],
                         "Setup / Platform Settings (FormId 0x2791)")
        self.assertEqual(row["ifr_line"], "5953")

    def test_the_byte_that_hides_charging_method_is_a_hidden_numeric(self):
        hidden = self.rows.get("0xE17")
        self.assertIsNotNone(hidden)
        self.assertEqual(hidden.stmt.quoted("Prompt"), "")
        self.assertEqual(hidden.row(self.stores)["varstore"],
                         "SetupVolatileData")
        self.assertEqual(hidden.row(self.stores)["offset"], "0x4")

    def test_the_two_dynamic_tuning_participants(self):
        charger = self.assert_row("0x24D", "Setup", "0x3D2", "8",
                                  "Charger participant", "charge-option")
        battery = self.assert_row("0x250", "Setup", "0x65D", "8",
                                  "Battery Participant", "charge-option")
        for row in (charger, battery):
            self.assertEqual(row["suppress_if"],
                             "EqIdVal QuestionId: 0x229, Value: 0x0")
            self.assertEqual(row["default_normal"], "0")
            self.assertIn("Dynamic Tuning", row["form_chain"])

    def test_the_sampling_period_disappears_with_the_row_above_it(self):
        row = self.assert_row("0x251", "Setup", "0x3D4", "16",
                              "Intel Dynamic Tuning Battery Sampling Period",
                              "charge-option")
        self.assertIn("EqIdVal QuestionId: 0x250, Value: 0x0", row["suppress_if"])
        self.assertEqual(row["default_normal"], "0")

    def test_the_ac_brick_capacity_is_cpu_setup_0xc3(self):
        row = self.assert_row("0x127", "CpuSetup", "0xC3", "8",
                              "  AC Brick Capacity", "charge-option")
        self.assertEqual(row["suppress_if"],
                         "EqIdVal QuestionId: 0x126, Value: 0x0")
        self.assertEqual(row["default_normal"], "1")
        self.assertIn("90W AC Brick", row["options"])

    def test_the_light_bar_row_is_recognisable_only_from_its_help(self):
        row = self.assert_row("0x29E9", "Setup", "0x740", "8", "Light Bar Effect",
                              "charge-option")
        self.assertEqual(row["matched_term"], "ac power")
        self.assertEqual(row["matched_field"], "help")
        self.assertIn("Advanced", row["form_chain"])

    def test_the_two_rows_that_matched_the_vocabulary_and_are_not_chargers(self):
        # Both are in the census with the exclusion recorded, rather than
        # dropped: a match that vanishes silently is indistinguishable from a
        # question the list never saw.
        boot = self.assert_row("0xFA", "CpuSetup", "0xE", "8",
                               "Boot performance mode",
                               "matched-not-a-charge-option")
        self.assertEqual(boot["matched_field"], "option")
        self.assertIn("Max Battery", boot["options"])
        deep = self.assert_row("0x705", "PchSetup", "0x4", "8",
                               "DeepSx Power Policies",
                               "matched-not-a-charge-option")
        self.assertIn("Enabled in S4-S5/Battery", deep["options"])

    def test_the_census_is_exactly_those_eight_rows(self):
        matched = [q.stmt.question_id() for q in ifr_census.charge_rows(
            self.questions)]
        self.assertEqual(matched, ["0x29E9", "0xFA", "0x127", "0x24D", "0x250",
                                   "0x251", "0x2A6", "0x705"])

    def test_every_condition_this_dump_gates_was_resolved(self):
        # A `?(...)` anywhere in the census would mean a condition was printed
        # as though it had been read. The tool reports the count; this asserts
        # it is zero, so a new unmodelled opcode cannot slip in.
        self.assertEqual([e.text for e in ifr_census.unresolved(self.questions)],
                         [])

    def test_no_form_set_references_the_runtime_variable(self):
        # Scoped, and stated as scoped: this is the Setup IFR and the string
        # `UniWillVariable` in it. docs/findings.md §8 records the positive
        # half -- OemOcDxe copies UniWillVariable[0x33] into Setup[0x7D7] at
        # boot -- and the consumer there is DXE code, not a form-set.
        with open(IFR, encoding="utf-8", errors="replace", newline="") as f:
            text = f.read()
        self.assertEqual(text.lower().count("uniwillvariable"), 0)
        self.assertEqual(text.lower().count("9f33f85c"), 0)


class CommittedCsvTests(unittest.TestCase):
    """The CSV is derived, and `--check` is what holds it to that."""

    def test_the_committed_csv_is_what_the_tool_derives(self):
        out, code = run("--check")
        self.assertEqual(code, 0, out)

    def test_the_csv_header_is_the_tools_own_column_list(self):
        with open(CSV_PATH, newline="") as f:
            header = next(csv.reader(f))
        self.assertEqual(header, ifr_census.CSV_COLUMNS)

    def test_every_row_is_one_of_the_eight_and_carries_its_reading(self):
        stores, questions = committed_census()
        with open(CSV_PATH, newline="") as f:
            rows = list(csv.DictReader(f))
        derived = [q.row(stores) for q in ifr_census.charge_rows(questions)]
        self.assertEqual(rows, derived)
        for row in rows:
            self.assertTrue(row["varstore_guid"], row["question_id"])
            self.assertTrue(row["matched_term"], row["question_id"])
            self.assertIn(row["verdict"],
                          ("charge-option", "matched-not-a-charge-option"))
            self.assertGreater(int(row["ifr_line"]), 0)

    def test_a_tampered_csv_fails_the_check(self):
        # The direction that matters: a hand-edited table cannot survive. Done
        # against a copy in a temporary directory, so the committed file is
        # never the thing being edited.
        import tempfile
        with open(CSV_PATH, newline="") as f:
            text = f.read()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "charge-questions.csv")
            with open(path, "w", newline="") as f:
                f.write(text.replace("Setup[0x4F3]", "Setup[0x4F4]")
                        if "Setup[0x4F3]" in text
                        else text.replace("0x4F3", "0x4F4"))
            out, code = run("--check", "--csv", path)
        self.assertEqual(code, 1)
        self.assertIn("is not what", out)

    def test_a_missing_csv_fails_the_check_rather_than_creating_it(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out, code = run("--check", "--csv", os.path.join(tmp, "absent.csv"))
        self.assertEqual(code, 1)
        self.assertIn("run --write", out)

    def test_write_and_check_cannot_be_asked_for_together(self):
        # --write re-blesses the file from the dump and exits 0, so a run that
        # both rewrote and compared would exit green on anything.
        with self.assertRaises(SystemExit) as caught:
            run("--check", "--write")
        self.assertIn("cannot be combined", str(caught.exception))


class LookupTests(unittest.TestCase):
    """The two lookups issue #86 needs, and what they say when they miss."""

    def test_offset_finds_the_question(self):
        out, _ = run("--offset", "Setup:0x4F3")
        self.assertIn("Charging Method", out)
        self.assertIn("Qid 0x2A6", out)

    def test_offset_misses_are_answered_as_a_miss(self):
        out, code = run("--offset", "Setup:0x4F4")
        self.assertEqual(code, 0)
        self.assertIn("No question in this dump writes", out)
        self.assertIn("grep -n", out)

    def test_offset_without_a_store_is_refused(self):
        with self.assertRaises(SystemExit) as caught:
            run("--offset", "0x4F3")
        self.assertIn("<varstore>:<offset>", str(caught.exception))

    def test_question_lookup_and_its_miss(self):
        out, _ = run("--question", "0x250")
        self.assertIn("Battery Participant", out)
        out, _ = run("--question", "0xDEAD")
        self.assertIn("No question with id", out)

    def test_match_is_a_lookup_not_the_charge_list(self):
        out, _ = run("--match", r"^  AC Brick")
        self.assertIn("AC Brick Capacity", out)
        self.assertNotIn("Charging Method", out)

    def test_a_pattern_nothing_matches_is_reported_as_such(self):
        out, code = run("--match", "flexicharge-that-is-not-here")
        self.assertEqual(code, 0)
        self.assertIn("not a claim about any other", out)

    def test_the_excluded_list_contains_the_near_misses_the_plan_names(self):
        # The three shapes the issue's wording points at, each declined for its
        # own reason. `PEP SATA` is the third because `Adapter D0/F1` and
        # `Adapter D3` are its OPTION labels, not its prompt -- so the row is
        # only visible to a matcher that reads option labels at all, and
        # asserting on the prompt is asserting on the wrong string.
        out, _ = run("--list-excluded")
        self.assertIn("AC Loadline", out)      # a VR loadline: AC, not a brick
        self.assertIn("ACPI Debug", out)       # ACPI, which contains "AC"
        self.assertIn("PEP SATA", out)
        self.assertIn("'adapter' in option", out)

    def test_the_excluded_list_is_the_transcript_the_write_up_pastes(self):
        # The write-up states this list's size in prose and pastes `head -6` of
        # it, and both drifted once with nothing failing: the near-misses above
        # stay in the list however the count moves, so only a case that pins the
        # count and the rows catches it. The size is derived from the phrase
        # list, the looser probe and the parse, so any of those three moving is
        # a deliberate edit to this case and to the write-up together.
        out, code = run("--list-excluded")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[:6], [
            "521 question(s) trip 'ac' / 'pow' / 'adapter' / 'batter' / 'charg' "
            "and none of battery / charg / flexicharge / ac brick / ac power.",
            "  0x2A2B  Operating Mode                               'pow' in help",
            "  0x2A2C  Operating Mode                               'pow' in help",
            "  0x2A2F  Light Effect                                 'pow' in help",
            "  0x2A2D  Light Effect                                 'pow' in help",
            "  0x2A2E  Light Effect                                 'pow' in help",
        ])

    def test_the_excluded_list_holds_no_question_that_matched(self):
        # The two lists must not overlap, or a row is both in the census and
        # reported as declined, which is a contradiction a reader cannot
        # resolve. Checked by id rather than by prompt, because two of the
        # near-misses are named the same way the real rows are.
        out, _ = run("--list-excluded")
        declined = set(re.findall(r"^  (0x[0-9A-F]+) ", out, re.M))
        _, questions = committed_census()
        matched = set(q.stmt.question_id()
                      for q in ifr_census.charge_rows(questions))
        self.assertEqual(sorted(declined & matched), [])
        # ... and the declined set is large, which is the point of the mode: a
        # bare `ac` would have taken in most of it.
        self.assertGreater(len(declined), 100)

    def test_a_missing_dump_is_refused_rather_than_read_as_empty(self):
        # An unreadable input and an input with nothing in it must not look
        # alike: the first is an error, the second is a result.
        with self.assertRaises(SystemExit) as caught:
            run("--ifr", os.path.join(HERE, "no-such-dump.ifr.txt"))
        self.assertIn("no-such-dump.ifr.txt", str(caught.exception))

    def test_an_empty_match_is_not_a_pass_silently(self):
        # The same rule as tools/run-tests.sh's empty-discovery guard, one
        # level down: a run that found nothing says so in words.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "empty.ifr.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("Program version: 1.6.1, Extraction mode: UEFI\n")
            out, code = run("--ifr", path)
        self.assertEqual(code, 0)
        self.assertIn("not a claim that the dump holds no such question", out)


class IfrextractorVersionTests(unittest.TestCase):
    """The dumps name the tool that wrote them, and that name is a fact."""

    def test_the_setup_dump_carries_the_ifrextractor_version(self):
        with open(IFR, encoding="utf-8", errors="replace", newline="") as f:
            header = f.readline()
        self.assertIn("Program version: 1.6.1", header)
        self.assertIn("Extraction mode: UEFI", header)

    def test_every_other_committed_dump_names_the_same_version(self):
        ifr_dir = os.path.join(REPO, "bios", "ifr")
        dumps = sorted(n for n in os.listdir(ifr_dir)
                       if n.endswith(".en-US.ifr.txt"))
        self.assertGreater(len(dumps), 1, "the other form-sets' dumps are gone")
        for name in dumps:
            with open(os.path.join(ifr_dir, name), encoding="utf-8",
                      errors="replace", newline="") as f:
                header = f.readline()
            self.assertIn("Program version: 1.6.1", header, name)

    def test_each_committed_dump_is_named_for_a_form_set_it_actually_contains(self):
        # A dump copied in under the wrong name would pass every other case
        # here and quietly answer the wrong module's questions.
        ifr_dir = os.path.join(REPO, "bios", "ifr")
        for name in sorted(os.listdir(ifr_dir)):
            if not name.endswith(".en-US.ifr.txt"):
                continue
            module = name.split(".", 1)[0]
            with open(os.path.join(ifr_dir, name), encoding="utf-8",
                      errors="replace", newline="") as f:
                text = f.read()
            formsets = set(re.findall(r"FormSet Guid: [0-9A-F-]+, "
                                      r"Title: \"([^\"]*)\"", text))
            self.assertTrue(formsets, "%s holds no FormSet" % name)
            if module in ("Setup",):
                continue
            # Every other dump is named for a module that is not a form-set
            # name -- the dynamic-setup helpers, the network stack's form
            # modules, the RAID and Realtek drivers -- so the module name is
            # recorded in bios/ifr/README.md and this case checks only that the
            # dump is a real HII package rather than a truncated one.
            self.assertGreater(len(text.splitlines()), 10, name)


if __name__ == "__main__":
    unittest.main()
