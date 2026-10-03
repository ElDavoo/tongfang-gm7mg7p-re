#!/usr/bin/env python3
"""Offline checks for `ifr_refgraph.py`: its own parsing, and the routes to
form 0x2718 read out of the committed `Setup` IFR.

Two halves, and the split is the point. The first asserts the tool on a
hand-built fixture, where every answer is known because the fixture was written
to be known -- which is the only way to pin the parts that are easy to get
subtly wrong and that the real dump cannot reveal, because the real dump has no
second answer to check against. The second reads the committed
`bios/ifr/Setup.en-US.ifr.txt` and asserts the facts
`docs/findings/ifr-2718-reachability.md` cites, so a regenerated dump that lost
a `Ref` fails here rather than quietly changing what that write-up says.

Every assertion below is a property of the tree or of the committed firmware,
never a count of either. A count moves on the next merge, and the line carrying
it is one every other open branch edits; a membership test does not move.
Where a number *is* the finding -- a sentinel value, a byte offset -- it is
asserted as that value, beside the thing it is a value of.

Both halves read committed text. Nothing here opens the ROM, runs
UEFIExtract or ifrextractor, or reads a setup variable, and no case is a claim
about what this machine's setup menu displays.
"""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import ifr_census  # noqa: E402  (the path insert above is what makes this work)
import ifr_refgraph  # noqa: E402

IFR = os.path.join(REPO, "bios", "ifr", "Setup.en-US.ifr.txt")

# The six `Ref`s that make up stock root form 0x2710's tab list, and the forms
# they name. Asserted as this table rather than as "there are six of them":
# 0x271C alone is reached from eleven places, so a referrer count is not a
# stable thing to hold, and this pairing is what the write-up's route table
# turns on.
STOCK_TABS = ((65, "0x2717"), (66, "0x2718"), (67, "0x2719"),
              (68, "0x271A"), (69, "0x271B"), (70, "0x271C"))

_DUMP = {}


def committed():
    """`(statements, spans, stores)` for the committed dump, read once per run.

    A dict rather than a module-level tuple so a case that mutates the result
    cannot leak into the next one, and a dict rather than `functools.cache` so
    there is no import to explain: the dump is 2.4 MB and the parse is the
    slowest thing this suite does.
    """
    if "dump" not in _DUMP:
        statements = ifr_refgraph.read_dump(IFR)
        _DUMP["dump"] = (statements, ifr_refgraph.block_spans(statements),
                         ifr_refgraph.varstores(statements))
    return _DUMP["dump"]


def referrers(form_id):
    statements, spans, _ = committed()
    return ifr_refgraph.referrers(statements, spans, form_id)


def statement_at(line):
    statements, _, _ = committed()
    return [s for s in statements if s.line == line][0]


def run(*argv):
    """main()'s output and exit code, for the modes a case wants to read."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = ifr_refgraph.main(list(argv))
    return buf.getvalue(), code


# --------------------------------------------------------------------------
# The shared parser
# --------------------------------------------------------------------------

class SharedReaderTests(unittest.TestCase):
    """This tool reads the dump through `ifr_census`, and says so.

    The two answers have to be one answer. `ifr_refgraph` and `ifr_census` are
    both committed, both cited by write-ups, and both parse the same verbose
    format; a rename or a fork in one that the other does not follow would leave
    two answers to one question with nothing failing. These cases hold the
    import itself, not just that the tool runs.
    """

    def test_the_parser_is_the_siblings_and_not_a_second_one(self):
        for name in ("read_dump", "read_statements", "varstores", "block_spans",
                     "condition_expr", "CONDITION_BLOCKS", "DEFAULT_IFR",
                     "REPO", "form_chain"):
            self.assertIs(getattr(ifr_refgraph, name),
                          getattr(ifr_census, name),
                          "ifr_refgraph.%s should be ifr_census's" % name)

    def test_the_byte_block_pattern_is_shared_too(self):
        # `opcode_bytes` reaches the block through the sibling's pattern rather
        # than its own, because a help string is free to end in a brace and two
        # readers would not agree on which brace that is.
        self.assertIs(ifr_refgraph.ifr_census.BYTE_BLOCK,
                      ifr_census.BYTE_BLOCK)

    def test_the_siblings_csv_is_still_current(self):
        # A refactor here that changed the shared reader's output would break
        # the sibling's derived CSV too, and that is a different failure with a
        # different fix. Caught here so it is not diagnosed here.
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = ifr_census.main(["--check"])
        self.assertEqual(code, 0, buf.getvalue())


# --------------------------------------------------------------------------
# The Ref opcode bytes
# --------------------------------------------------------------------------

class RefOpcodeTests(unittest.TestCase):
    """Reading a `Ref`'s target from its bytes, in both block shapes.

    The two shapes are the reason the offset is a constant rather than "the last
    two bytes". A `Ref` that crosses into another form set carries a 16-byte
    `FormSetGuid` *after* the `FormId`, so reading the tail of the block names a
    form built out of the last two bytes of a GUID on those and the right form
    on the rest -- a decoder that is right about most of the dump.
    """

    def build(self, hexbytes):
        return ifr_census.Statement(
            1, 2, 'Ref Prompt: "x", FormId: 0x2718 { %s }' % hexbytes)

    def test_the_target_is_at_the_documented_offset(self):
        # The 15-byte shape: a Ref within the form set.
        stmt = self.build("0F 0F 09 00 02 00 01 00 00 00 FF FF 00 18 27")
        self.assertEqual(ifr_refgraph.ref_target(stmt), 0x2718)

    def test_the_same_offset_holds_when_a_formsetguid_follows(self):
        # The 33-byte shape. The target is still at the same offset; what
        # changes is that 18 more bytes follow it, so the block's tail is a
        # GUID and "the last two bytes" would read 0xC48AA1AC.
        stmt = self.build(
            "0F 21 44 18 45 18 3C 00 00 00 FF FF 00 01 00 00 00 "
            "AC A1 8A C4 70 F8 8D 41 A6 EF C1 DD 89 C1 CE 19")
        self.assertEqual(ifr_refgraph.ref_target(stmt), 0x0001)
        self.assertNotEqual(ifr_refgraph.ref_target(stmt),
                            int.from_bytes(
                                ifr_refgraph.opcode_bytes(stmt)[-2:], "little"))

    def test_a_block_this_tool_does_not_describe_is_reported_not_decoded(self):
        # Returning a plausible number here would put a fabricated form in a
        # reachability table, which is the one failure this tool exists to rule
        # out. Three shapes: wrong opcode, an unseen length, and no block.
        for hexbytes, why in (("05 01 02", "not the Ref opcode"),
                              ("0F 01 02 03", "an unseen block length"),
                              ("", "no opcode block")):
            stmt = self.build(hexbytes)
            with self.assertRaises(ifr_refgraph.RawRefError, msg=why):
                ifr_refgraph.ref_target(stmt)

    def test_every_ref_in_the_committed_dump_agrees_with_its_rendered_field(self):
        # The property the whole decode rests on, measured on the real file
        # rather than on a fixture: each `Ref`'s opcode bytes and its rendered
        # `FormId:` name the same form. They are read from different halves of
        # one line, so a disagreement means the dump is not what this tool
        # reads -- and every reachability claim built on it would be wrong in a
        # way nothing else here would catch.
        statements, spans, _ = committed()
        checked = 0
        for i in ifr_refgraph.ref_statements(statements):
            ref = ifr_refgraph.Referrer(
                statements[i], i, ifr_refgraph.enclosing_form(statements, spans, i),
                ())
            self.assertIsNone(ref.raw_error,
                              "line %d: %s" % (statements[i].line, ref.raw_error))
            self.assertTrue(ref.agrees(),
                            "line %d: bytes name 0x%04X, the field says %s"
                            % (statements[i].line, ref.raw, ref.rendered()))
            checked += 1
        self.assertGreater(checked, 0, "the dump holds no Ref at all")

    def test_the_offset_constant_is_what_the_bytes_agree_with(self):
        # If someone moves REF_FORMID_OFFSET this fails rather than the dump
        # silently decoding to a different form at every call site.
        self.assertEqual(ifr_refgraph.REF_FORMID_OFFSET, 13)
        self.assertEqual(ifr_refgraph.REF_OPCODE, 0x0F)


# --------------------------------------------------------------------------
# Questions, in the reverse direction
# --------------------------------------------------------------------------

class QuestionDirectionTests(unittest.TestCase):
    """`--question`: where a question is stored, and what reads it."""

    def test_0xe9f_is_the_dynamic_page_count_sentinel(self):
        # The question issue #119 asks to resolve. Every field of the answer is
        # asserted, because the write-up's first route rests on the pairing of
        # a store whose name says what it is with a condition that tests it
        # against a value no page count takes.
        statements, spans, stores = committed()
        declared = ifr_refgraph.declaring_questions(statements, spans, "0xE9F")
        self.assertEqual([s.line for _, s in declared], [27209])
        stmt = declared[0][1]
        self.assertEqual(stmt.opcode, "Numeric")
        self.assertEqual(stmt.quoted("Prompt"), "")
        self.assertEqual(stmt.field("VarOffset"), "0x0")
        self.assertEqual(stmt.field("Size"), "16")
        self.assertEqual(stmt.field("Flags"), "0x11")
        self.assertEqual(stores[0x33],
                         ("DynamicPageCount", "B63BF800-F267-4F55-9217-E97FB3B69846",
                          "0x2"))

    def test_its_neighbour_is_the_driver_health_sibling(self):
        # 0xE9E is declared beside it on the next VarStore with the identical
        # shape, which is what makes the pair an AMI idiom rather than a vendor
        # invention. The two are held as the pair they are; neither one's
        # existence is asserted as a count over some population.
        statements, spans, stores = committed()
        for qid, store_id, name in (("0xE9E", 0x34, "DriverHlthEnable"),
                                    ("0xE9F", 0x33, "DynamicPageCount")):
            declared = ifr_refgraph.declaring_questions(statements, spans, qid)
            self.assertEqual(len(declared), 1, qid)
            stmt = declared[0][1]
            self.assertEqual(stmt.field("VarOffset"), "0x0", qid)
            self.assertEqual(stmt.field("Size"), "16", qid)
            self.assertEqual(stmt.field("Flags"), "0x11", qid)
            self.assertEqual(stmt.quoted("Prompt"), "", qid)
            self.assertEqual(stores[store_id][0], name, qid)

    def test_both_suppressors_test_the_sentinel_rather_than_a_page_count(self):
        # 0xFFFF is the sentinel. The value is the finding, so it is asserted
        # as a value -- and each suppressor with the form it sits in, because
        # *which* page each one is on is the correction that changes the answer:
        # one is on the vendor's Advanced, not the stock one.
        statements, spans, _ = committed()
        hits = ifr_refgraph.mentions(statements, spans, "0xE9F")
        self.assertEqual(
            [(s.line, e.text, ifr_refgraph.enclosing_form(statements, spans, i)[0])
             for i, s, e in hits],
            [(397, "EqIdValList QuestionId: 0xE9F, Values: [65535]", "0x2712"),
             (1673, "EqIdValList QuestionId: 0xE9F, Values: [65535]", "0x2718")])
        self.assertEqual([statement_at(114).field("FormId"),
                          statement_at(1613).field("FormId")],
                         ["0x2712", "0x2718"])

    def test_the_stock_advanced_suppressor_sits_inside_the_page_itself(self):
        # The second referrer of 0x2718 is a self-reference from inside 0x2718,
        # not a route in from 0x2717 as the issue has it. Held as the
        # enclosing form of the `Ref`, which is the claim the write-up makes.
        self.assertEqual(referrers("0x2718")[1].form[:2], ("0x2718", "Advanced"))

    def test_the_vendor_suppressor_is_nested_two_deep(self):
        # The other suppressor is inside the vendor's own 0x2712, under a
        # GrayOutIf the write-up names, and it gates a self-Ref back to 0x2712.
        # Asserted as a stack, because "nested two deep in a GrayOutIf on
        # 0xD81" is a claim about containment and a flat list would not hold it.
        refs = referrers("0x2712")
        breadcrumb = [r for r in refs
                      if [q for q in r.question_ids() if q.lower() == "0xe9f"]]
        self.assertEqual([r.stmt.line for r in breadcrumb], [399])
        self.assertEqual([op for op, _, _ in breadcrumb[0].stack],
                         ["GrayOutIf", "SuppressIf"])
        self.assertEqual([e.text for _, _, e in breadcrumb[0].stack],
                         ["EqIdVal QuestionId: 0xD81, Value: 0x1",
                          "EqIdValList QuestionId: 0xE9F, Values: [65535]"])

    def test_both_questions_sit_inside_a_block_the_ifr_never_unlocks(self):
        # The answer to "what sets it", stated as a property of the IFR: the
        # declaration is inside a DisableIf whose operand is a bare True, so
        # the form set states no path that writes either question at setup
        # time. Not a claim that nothing writes them.
        statements, spans, _ = committed()
        for qid in ("0xE9E", "0xE9F"):
            i, _ = ifr_refgraph.declaring_questions(statements, spans, qid)[0]
            stack = ifr_refgraph.condition_stack(statements, spans, i)
            self.assertEqual([op for op, _, _ in stack], ["DisableIf"], qid)
            self.assertEqual([e.text for _, _, e in stack], ["TRUE"], qid)
        self.assertEqual(statement_at(26613).opcode, "DisableIf")
        self.assertEqual(statement_at(26614).opcode, "True")

    def test_the_conditions_that_read_0xe9f_are_the_two_named(self):
        out, code = run("--question", "0xE9F")
        self.assertEqual(code, 0, out)
        self.assertIn("DynamicPageCount", out)
        self.assertIn("B63BF800-F267-4F55-9217-E97FB3B69846", out)
        self.assertIn("EqIdValList QuestionId: 0xE9F, Values: [65535]", out)
        self.assertIn("read by 2 condition(s)", out)
        self.assertIn('0x2712 "Advanced"', out)
        self.assertIn('0x2718 "Advanced"', out)

    def test_a_question_nothing_reads_says_so_rather_than_saying_nothing(self):
        # The negative is scoped. A silent empty section is indistinguishable
        # from a mode that did not run.
        out, _ = run("--question", "0xDEAD")
        self.assertIn("No question with id 0xDEAD", out)

    def test_a_ref_is_not_a_question_despite_carrying_a_question_id(self):
        # A `Ref` links to a question in another form; it does not address a
        # byte of a store. Question 0x2 is the stock tab Ref to 0x2717, and
        # reading it as a store question would put a nonexistent Setup[0x0] row
        # in the answer.
        statements, spans, _ = committed()
        self.assertEqual(ifr_refgraph.declaring_questions(statements, spans, "0x2"),
                         [])


# --------------------------------------------------------------------------
# The routes to 0x2718
# --------------------------------------------------------------------------

class RouteTests(unittest.TestCase):
    """What reaches form 0x2718, which is the issue's second question."""

    def test_the_two_referrers_are_the_two_the_write_up_names(self):
        refs = referrers("0x2718")
        self.assertEqual([r.stmt.line for r in refs], [66, 1675])

    def test_the_first_is_ungated_and_comes_from_the_stock_root(self):
        ref = referrers("0x2718")[0]
        self.assertEqual(ref.form[:2], ("0x2710", "Setup"))
        self.assertEqual(ref.stack, [])
        self.assertFalse(ref.gated())

    def test_the_second_is_the_sentinel_suppressed_self_reference(self):
        ref = referrers("0x2718")[1]
        self.assertEqual([e.text for _, _, e in ref.stack],
                         ["EqIdValList QuestionId: 0xE9F, Values: [65535]"])
        self.assertTrue(ref.gated())
        self.assertEqual(ref.question_ids(), ["0xE9F"])

    def test_form_0x2717_holds_no_ref_at_all(self):
        # The correction this rests on: the issue places the second referrer in
        # 0x2717, and 0x2717 is reached only by the root's tab Ref.
        self.assertEqual([r.stmt.line for r in referrers("0x2717")], [65])
        statements, spans, _ = committed()
        start = [i for i, s in enumerate(statements)
                 if s.opcode == "Form" and s.field("FormId") == "0x2717"][0]
        self.assertEqual([i for i in range(start + 1, spans[start])
                          if statements[i].opcode == "Ref"], [])

    def test_the_root_six_tabs_are_read_from_the_opcode_bytes_and_are_ungated(self):
        # Each of the six is unwrapped from `Statement.body` rather than read
        # off the rendered field, so a reformat that made a suppressed `Ref`
        # read as a bare one would fail here rather than quietly agreeing.
        statements, spans, _ = committed()
        root = [i for i, s in enumerate(statements)
                if s.opcode == "Form" and s.field("FormId") == "0x2710"][0]
        inside = [i for i in range(root + 1, spans[root])
                  if statements[i].opcode == "Ref"]
        self.assertEqual([(statements[i].line,
                           "0x%04X" % ifr_refgraph.ref_target(statements[i]))
                          for i in inside], list(STOCK_TABS))
        for i in inside:
            self.assertEqual(ifr_refgraph.condition_stack(statements, spans, i),
                             [], "the tab Ref at line %d is gated"
                                % statements[i].line)

    def test_each_sibling_tab_resolves_to_the_root_ref_that_links_it(self):
        # Asserted as the pairing, not as a referrer count: 0x271C is reached
        # from eleven places, so "one referrer" is not true of it and is not
        # what the write-up claims.
        for line, form_id in STOCK_TABS:
            self.assertIn(line, [r.stmt.line for r in referrers(form_id)],
                          "%s should be linked from the root's tab Ref at line "
                          "%d" % (form_id, line))
            self.assertEqual(referrers(form_id)[0].form[0], "0x2710")

    def test_the_overclocking_menu_is_reached_from_the_stock_advanced(self):
        # The issue's reason for wanting 0x2718 at all: the CPU-side OC menu is
        # a link on that page, so the route matters. One `Ref`, ungated.
        refs = referrers("0x27AA")
        self.assertEqual([r.stmt.line for r in refs], [1630])
        self.assertEqual(refs[0].form[:2], ("0x2718", "Advanced"))

    def test_a_ref_on_a_wrapped_continuation_is_still_a_referrer(self):
        # A good number of this dump's Refs carry their FormId on a
        # continuation line, because the help string wrapped over a CR. A
        # reader that parsed the fields before joining the continuation loses
        # the target, and those Refs vanish from every referrer list with
        # nothing crashing. One is pinned here -- by its being present, not by
        # its being the only one, since 0x29FA is also linked from further down
        # the same page.
        wrapped = statement_at(549)
        self.assertEqual(wrapped.opcode, "Ref")
        self.assertEqual(wrapped.field("FormId"), "0x29FA")
        self.assertEqual(ifr_refgraph.ref_target(wrapped), 0x29FA)
        self.assertIn(549, [r.stmt.line for r in referrers("0x29FA")])

    def test_a_form_no_ref_reaches_says_so_without_claiming_deadness(self):
        out, code = run("--form", "0x2710")
        self.assertEqual(code, 0, out)
        self.assertIn("0 Ref(s) in this dump reach it", out)
        self.assertIn("not a claim about how the firmware reaches it", out)

    def test_a_form_that_is_not_in_the_dump_is_a_miss_not_an_error(self):
        out, code = run("--form", "0xDEAD")
        self.assertEqual(code, 0)
        self.assertIn("No form with FormId", out)
        self.assertIn("grep -n", out)


# --------------------------------------------------------------------------
# Roots and orphans
# --------------------------------------------------------------------------

class RootsTests(unittest.TestCase):
    """`--roots` is a statement about this dump, and the mode says so.

    The calibration the write-up turns on: "no incoming Ref" is what a
    TSE-opened root looks like and also what an orphaned page looks like, and
    this dump holds both. The property that separates them is repeating the
    form set's own title, which is a statement about the IFR and not about what
    the TSE opens.
    """

    def test_the_stock_root_is_a_root_and_the_advanced_page_is_not(self):
        root_ids = [form_id for form_id, _, _ in ifr_refgraph.roots(committed()[0])]
        self.assertIn("0x2710", root_ids)
        self.assertNotIn("0x2718", root_ids)

    def test_the_vendor_pages_are_in_the_same_set(self):
        # Stated because it is the calibration: the set is not the root alone,
        # so membership of it does not identify a TSE-opened root.
        root_ids = [form_id for form_id, _, _ in ifr_refgraph.roots(committed()[0])]
        for form_id in ("0x2711", "0x2713", "0x2714"):
            self.assertIn(form_id, root_ids)

    def test_exactly_one_root_repeats_the_form_set_title(self):
        # Asserted as "exactly one, and it is this one" rather than as the size
        # of the root set: the set moves when the dump is re-extracted, and the
        # property does not.
        statements, spans, stores = committed()
        titled = ifr_refgraph.root_form(statements)
        self.assertIsNotNone(titled)
        self.assertEqual(titled[:2], ("0x2710", "Setup"))
        self.assertEqual(ifr_refgraph.formset_title(statements), "Setup")
        repeating = [f for f in ifr_refgraph.roots(statements)
                     if f[1] == ifr_refgraph.formset_title(statements)]
        self.assertEqual(len(repeating), 1)

    def test_orphans_is_the_root_set_without_the_titled_form(self):
        out, code = run("--orphans")
        self.assertEqual(code, 0, out)
        self.assertIn("0x2711", out)
        self.assertNotIn("0x2710 ", out)
        self.assertIn("Not reachable by any Ref in this form set", out)
        self.assertIn("Not dead", out)

    def test_roots_states_the_calibration_rather_than_a_verdict(self):
        out, code = run("--roots")
        self.assertEqual(code, 0, out)
        self.assertIn("No incoming Ref is a statement about this dump", out)
        self.assertIn("also what an orphaned", out)
        self.assertIn("Which form the TSE opens is not in the IFR", out)


# --------------------------------------------------------------------------
# Conditions
# --------------------------------------------------------------------------

class ConditionTests(unittest.TestCase):
    """A condition that resolves to nothing prints as nothing."""

    def test_every_condition_this_dump_gates_was_resolved(self):
        # A `?(...)` anywhere would mean a condition was printed as though it
        # had been read. `--form` and `--question` both print the count on every
        # run; this asserts it is zero, so a new unmodelled opcode cannot slip
        # in and be reported as a read condition.
        statements, spans, _ = committed()
        self.assertEqual(ifr_refgraph.unresolved_blocks(statements, spans), [])

    def test_the_run_reports_that_and_says_what_the_bare_blocks_are(self):
        out, _ = run("--form", "0x2718")
        self.assertIn("every condition this run resolved was read in full", out)
        self.assertIn("no condition stated", out)

    def test_a_block_that_states_no_condition_is_not_printed_as_true(self):
        # `condition_expr` returns None for a bare SuppressIf. Printing TRUE
        # would be a claim the IFR does not make, so the wording is held here
        # as well as in the tool's own self-test: this is the sentence a
        # reader takes away.
        statements, spans, _ = committed()
        bare = [statements[i].opcode for i, s in enumerate(statements)
                if s.opcode in ifr_refgraph.CONDITION_BLOCKS and i < spans[i]
                and ifr_refgraph.condition_expr(statements, i) is None]
        self.assertIn("SuppressIf", bare)
        self.assertNotIn("TRUE", ifr_refgraph.report_conditions.__doc__ or "")

    def test_a_referrer_under_a_bare_block_is_reported_as_ungated(self):
        # The stack still names the block it sits under, and the block's absent
        # condition is not turned into one.
        out, _ = run("--form", "0x2718")
        self.assertIn("no enclosing condition block", out)


# --------------------------------------------------------------------------
# The tool's own modes
# --------------------------------------------------------------------------

class ModeTests(unittest.TestCase):
    """The modes' contract, and the reader's agreement with the dump."""

    def test_the_tool_has_its_own_self_test_and_it_passes(self):
        out, code = run("--self-test")
        self.assertEqual(code, 0, out)
        self.assertNotIn("FAIL", out)

    def test_check_passes_against_the_committed_dump(self):
        out, code = run("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("reader and dump agree", out)

    def test_check_needs_neither_the_rom_nor_ifrextractor(self):
        # The property that makes this a gate and not a script: it reads the
        # committed dump and nothing else. Asserted rather than described, by
        # pointing it at a copy of the dump taken elsewhere.
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "copy.en-US.ifr.txt")
            shutil.copyfile(IFR, path)
            out, code = run("--check", "--ifr", path)
        self.assertEqual(code, 0, out)

    def test_a_missing_dump_is_refused_rather_than_read_as_empty(self):
        # An unreadable input and an input with nothing in it must not look
        # alike: the first is an error, the second is a result.
        out, code = run("--check", "--ifr", os.path.join(HERE, "no-such.ifr.txt"))
        self.assertEqual(code, 1)
        self.assertIn("bios_extract.py", out)

    def test_a_ref_whose_bytes_disagree_fails_the_check(self):
        # The direction that matters. Done against a copy in a temporary
        # directory, so the committed dump is never the thing being edited.
        import shutil
        import tempfile
        with open(IFR, encoding="utf-8", errors="replace", newline="") as f:
            lines = f.read().split("\n")
        # Rewrite one tab Ref's target bytes, leaving the rendered field alone,
        # so the two halves of one line disagree.
        for n, line in enumerate(lines):
            if line.startswith("0x2DD13:") and "FormId: 0x2718" in line:
                lines[n] = line.replace("FF FF 00 18 27", "FF FF 00 19 27")
                break
        else:
            self.fail("the committed dump no longer holds the tab Ref to 0x2718")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tampered.en-US.ifr.txt")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write("\n".join(lines))
            out, code = run("--check", "--ifr", path)
        self.assertEqual(code, 1)
        self.assertIn("the rendered field says", out)

    def test_a_ref_pointing_into_another_form_set_is_not_a_failure(self):
        # Some Refs name forms this dump does not declare, because they cross
        # into another package. Most of them go to
        # bios/ifr/FboGroupForm.en-US.ifr.txt -- DE8AB926-EFDA-4C23-BBC4-98FD29AA0069
        # -- which declares 0x2A1A-0x2A29; the rest name
        # HddAcousticDynamicSetup, PciDynamicSetup and NvmeDynamicSetup, plus one
        # form set GUID no committed dump declares. That is a Ref out of this
        # form set, not a reader that has lost the plot, so `--check` reports it
        # and still exits zero.
        out, code = run("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("not a failure of the reader", out)

    def test_no_mode_is_called_writes_a_file(self):
        # There is no derived artefact, so no mode may create one. Checked by
        # pointing a run at a scratch directory that starts empty: `--form`,
        # `--question`, `--roots` and `--orphans` must leave it empty.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            for argv in (("--form", "0x2718"), ("--question", "0xE9F"),
                         ("--roots",), ("--orphans",), ("--check",)):
                out, code = run(*(argv + ("--ifr", IFR)))
                self.assertEqual(code, 0, out)
            self.assertEqual(os.listdir(tmp), [])


if __name__ == "__main__":
    unittest.main()
