#!/usr/bin/env python3
"""Offline checks for walk_budget_census.py and for walk_why(), the function
whose terminator the census reports.

Five terminator tokens, five guards, one function: a wrong token is a census
row that names the wrong reason, and the reason is the whole content of the
column. So the token cases are built as byte fixtures rather than read off the
firmware, one per guard, each asserting the *direction* -- which guard is
named, and which is not, since a test that only checked the token would pass
on a guard that had swapped two of them.

What is pinned here and not by the tool:

- that `walk()` still returns a bare list, and `classify()` still gives back
  the `access` cell every committed table holds. The census itself refuses a
  run that cannot reproduce those cells, so this is the same invariant stated
  where a failure names a function rather than a census.
- that the vocabulary is closed. A sixth terminator would reach the committed
  census and `--check` would go green on it, so the refusal is tested.
- that the class A/B verdict reports rather than guesses when the evidence is
  not in the window, which the committed data never exercises.
- that the six re-cut tables did not move an `access` or a `window` cell, and
  that the four tables the census measures as clean still are. That is the
  fifteen-address `0x086x` sweep the census's own command 1 runs, against the
  table #800 owns.

Nothing here needs hardware, Windows or a capture. The firmware read is a
committed file.
"""
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
# walk_budget_census imports trace_xdata_refs by bare module name, the way
# register_ref_table.py does, so the tool directory has to be on the path
# before it is loaded rather than after.
sys.path.insert(0, str(HERE))
import trace_xdata_refs as T          # noqa: E402
import walk_budget_census as W        # noqa: E402

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')
ANNOT = HERE.parent / 'annotations'

# One instruction that is in none of the five guards' way. 0x00 is the
# opcode-table's 1-byte `nop`: not a flow opcode, not `mov dptr`, and short
# enough that a fixture can lay any number of them down. A three-byte stand-in
# would not do -- `disasm8051.py` gives 0x75 (`mov 0x55,#0x22`) a length of 3,
# so a fixture that assumed two bytes per filler would stop in the filler.
NOP = bytes([0x00])
SITE = bytes([0x90, 0x07, 0xD0])      # mov dptr,#0x07D0
RELOAD = bytes([0x90, 0x07, 0xD1])    # mov dptr,#0x07D1
RET = bytes([0x22])                   # ret -- a flow opcode
READ = bytes([0xE0])                  # movx a,@dptr
WRITE = bytes([0xF0])                 # movx @dptr,a
DPL_FROM_A = bytes([0xF5, 0x82])      # mov 0x82,a -- the form walk()'s guard cannot see
DPL_FROM_R7 = bytes([0x8F, 0x82])     # mov 0x82,r7
DPH_FROM_A = bytes([0xF5, 0x83])      # mov 0x83,a


def fixture(*insns: bytes, size: int = 0x40) -> bytes:
    """A flat `common`-region image with `insns` laid down from offset 0.

    The same helper `test_walk_branch_arms.py` uses, and for the same reason:
    a case that pointed at the firmware would keep testing the same bytes only
    until the bytes around some address in the image changed.
    """
    img = bytearray(b"\x00" * size)
    at = 0
    for insn in insns:
        img[at:at + len(insn)] = insn
        at += len(insn)
    return bytes(img)


def firmware():
    """The image, read once and kept.

    `Path.read_bytes()` rather than `open(...).read()`, and cached rather than
    re-read per case: the census re-walks 1288 rows several times over, and a
    suite that left a handle open per case would print a ResourceWarning per
    case -- noise of the kind a reader learns to stop looking at.
    """
    if not firmware._cached:
        firmware._cached = Path(FIRMWARE).read_bytes()
    return firmware._cached


firmware._cached = None


def rows_of(name):
    """A committed CSV as a list of dicts, header included as row 0's key set."""
    with open(ANNOT / name, newline="") as f:
        return list(csv.DictReader(f))


def text_of(name):
    """A committed file's bytes as text, newlines untranslated.

    Read this way and not with `read_text()`, because these files carry the
    csv module's own CRLF terminator and universal-newline translation would
    hand back different bytes from the ones `--check` compares.
    """
    with open(ANNOT / name, newline="") as f:
        return f.read()


def why(img, start=0, max_insns=8):
    return T.walk_why(img, start, max_insns)[1]


class TerminatorTokenTests(unittest.TestCase):
    """One case per guard, each naming the guard that fired and the one that
    did not. A test asserting only "the token is one of the five" would pass
    on a loop that got two of them the wrong way round, which is the change
    this work is about."""

    def test_a_flow_opcode_names_flow_opcode(self):
        img = fixture(SITE, NOP, RET, NOP, NOP)
        self.assertEqual(why(img), T.FLOW_END)

    def test_a_dptr_reload_names_the_reload_and_not_the_budget(self):
        # Eight instructions is more than the four below, so a guard that
        # reported the budget here would still have one to fall back on.
        img = fixture(SITE, NOP, NOP, RELOAD, NOP, NOP, NOP, NOP)
        self.assertEqual(why(img), T.RELOAD_END)

    def test_a_reload_is_not_mistaken_for_a_flow_opcode(self):
        # `mov dptr,#imm16` is 0x90 and is not in FLOW_OPCODES, so a guard
        # order that tested for the flow case by "not a plain instruction"
        # would name this one flow. It is a reload.
        self.assertNotIn(T.MOV_DPTR, T.FLOW_OPCODES)
        img = fixture(SITE, RELOAD)
        self.assertEqual(why(img), T.RELOAD_END)

    def test_the_end_of_the_buffer_names_the_buffer(self):
        # The `i + 2 >= len(d)` disjunct: the walk runs out of bytes it can
        # read two ahead of. #805's restatement is that this disjunct and not
        # the instruction-length test is what holds the index, and a window
        # that runs off the end is a different event from one whose next
        # instruction does not fit.
        img = fixture(SITE, *(NOP,) * 5, size=9)
        self.assertEqual(why(img), T.BUFFER_END)

    def test_an_instruction_that_does_not_fit_names_itself(self):
        # `i + n > len(d)`. Reachable only on a walk's *first* instruction, and
        # that is a fact about the guard order rather than an accident: the
        # instruction-length test needs `i + n > len(d)` while the disjunct
        # below it has already guaranteed `i + 2 < len(d)`, and the longest
        # opcode in disasm8051.py is three bytes, so no integer `len(d)` is
        # both `> i + 2` and `<= i + 3`. The case below is a start two bytes
        # from the end, which is the only shape that reaches it.
        self.assertEqual(max(T.OPCODE_LEN), 3)
        img = fixture(bytes([0x90, 0x07]), size=2)
        insns, token = T.walk_why(img, 0)
        self.assertEqual(insns, [])
        self.assertEqual(token, T.SHORT_END)

    def test_the_three_byte_opcode_alone_does_not_reach_that_guard(self):
        # The other side of the case above: with the third byte present the
        # very same instruction is accepted and the walk moves on to the next
        # guard, so the length test is about the length and not about the
        # opcode. A one-byte filler either side of it would have made the case
        # pass for the wrong reason.
        self.assertEqual(why(fixture(bytes([0x90, 0x07, 0xD0]), size=3)),
                         T.BUFFER_END)
        self.assertNotEqual(why(fixture(bytes([0x90, 0x07]), size=2)),
                            T.BUFFER_END)

    def test_a_run_longer_than_the_budget_names_the_budget_with_that_budget(self):
        # Nine non-terminating instructions at the default budget of 8, so
        # every other guard is a candidate and none of them fires.
        img = fixture(SITE, *(NOP,) * 9)
        self.assertEqual(why(img), T.budget_end(8))
        # The token carries the budget, which is what makes a row's cell say
        # which 8 produced it rather than just that something ran out.
        self.assertEqual(why(img, max_insns=9), T.budget_end(9))
        self.assertNotEqual(why(img, max_insns=9), why(img))

    def test_a_budget_of_one_is_exhausted_by_a_window_that_would_run_on(self):
        # The floor: one instruction, and the site is the first one, so the
        # budget is gone before any guard can fire. A default `why` of `None`
        # would put a bare cell in the census here.
        img = fixture(SITE, NOP, NOP, NOP, NOP, NOP, NOP, NOP, NOP, NOP)
        self.assertEqual(why(img, max_insns=1), T.budget_end(1))

    def test_a_budget_of_zero_decodes_nothing_and_still_says_why(self):
        img = fixture(SITE, NOP, NOP, NOP, NOP, NOP, NOP, NOP, NOP, NOP)
        insns, token = T.walk_why(img, 0, 0)
        self.assertEqual(insns, [])
        self.assertEqual(token, T.budget_end(0))


class WalkContractTests(unittest.TestCase):
    """`walk()` is a nine-call-site API that eleven other modules import
    around, and the whole point of the change was that none of them could
    tell. So its two contracts are pinned rather than assumed."""

    def test_walk_returns_a_bare_list_of_triples(self):
        img = fixture(SITE, NOP, READ, RET)
        out = T.walk(img, 0)
        self.assertIsInstance(out, list)
        # site, filler, the read, and the `ret` that ends the window.
        self.assertEqual(len(out), 4)
        for entry in out:
            self.assertIsInstance(entry, tuple)
            self.assertEqual(len(entry), 3)
            at, raw, text = entry
            self.assertIsInstance(at, int)
            self.assertIsInstance(raw, bytes)
            self.assertIsInstance(text, str)

    def test_walk_is_walk_why_discard_the_reason(self):
        img = fixture(SITE, NOP, RELOAD, NOP, NOP, NOP, NOP, NOP)
        for budget in (1, 2, 3, 8, 64):
            self.assertEqual(T.walk(img, 0, budget),
                             T.walk_why(img, 0, budget)[0])

    def test_walk_keeps_the_name_docstring_and_signature(self):
        # The eleven modules that import from trace_xdata_refs name `walk`
        # with a positional budget, so the parameter has to stay third and
        # under its own name.
        import inspect
        sig = inspect.signature(T.walk)
        self.assertEqual(list(sig.parameters), ["d", "start", "max_insns"])
        self.assertEqual(sig.parameters["max_insns"].default, 8)
        self.assertIn("control-flow", T.walk.__doc__)
        self.assertIn("terminator", T.walk_why.__doc__)

    def test_classify_is_byte_identical_on_every_committed_window(self):
        # The load-bearing regression, stated at the function rather than
        # through the census. Every committed table's `access` cell is
        # classify(walk(d, file_offset)), so a walk that changed shape would
        # move one of them.
        d = firmware()
        checked = 0
        for name in W.TABLES:
            for row in rows_of(name):
                    off = int(row["file_offset"], 16)
                    self.assertEqual(T.classify(T.walk(d, off)), row["access"],
                                     f"{name} row {row['file_offset']}")
                    checked += 1
        self.assertEqual(checked, 1288,
                         "the population moved; W.TABLES and the committed "
                         "tables are supposed to agree")

    def test_no_committed_access_cell_is_re_derived_differently(self):
        # The census's own loud check, exercised through census_table() so
        # that path is not untested just because the tool refuses it.
        d = firmware()
        _table, _tallies, _moving, _classes, mismatched, unknown = \
            W.census_table(d, W.BUDGET, W.EXTEND)
        self.assertEqual(mismatched, [])
        self.assertEqual(unknown, [])


class VocabularyTests(unittest.TestCase):
    """The vocabulary is closed, and a token outside it is a refusal rather
    than a cell. This is `load_census_map()`'s rule applied to the terminator
    column: a default here is a cell that reads as an answer."""

    def test_the_five_tokens_are_the_five_the_census_snippet_prints(self):
        # Lifted out of docs/findings/opcode-len-bounds-census.md's
        # reproducing snippet, which had to re-implement the loop to count
        # them. The two `ended[...]` keys that name a guard in that snippet's
        # own words are the two whose names were shortened here, so the
        # shortening is pinned rather than asserted.
        self.assertEqual(T.TERMINATORS,
                         ("flow opcode", "DPTR reloaded", "end of buffer",
                          "instruction does not fit"))
        self.assertEqual(T.budget_end(8), "max_insns (8) exhausted")

    def test_a_terminator_outside_the_vocabulary_is_not_a_terminator(self):
        self.assertTrue(all(T.is_terminator(t) for t in T.TERMINATORS))
        self.assertTrue(T.is_terminator("max_insns (16) exhausted"))
        self.assertFalse(T.is_terminator("ran out of instructions"))
        self.assertFalse(T.is_terminator("max_insns exhausted"))
        self.assertFalse(T.is_terminator(""))
        self.assertFalse(T.is_terminator(None))

    def test_an_unknown_terminator_stops_the_census(self):
        # A `walk_why()` that grew a sixth way to stop would put a token in
        # the census and into `--check` that nothing can classify. The census
        # refuses rather than rendering it, so this drives the refusal
        # through the same collection the tool uses.
        #
        # Patched on `W`, not on `T`: the census imported walk_why by name at
        # import time, so rebinding the attribute on the defining module would
        # leave the census calling the original and this case would pass
        # vacuously.
        real = W.walk_why
        try:
            W.walk_why = lambda d, start, max_insns=8: (
                real(d, start, max_insns)[0], "budget spent")
            _t, _ta, _m, _c, _mm, unknown = W.census_table(
                firmware(), W.BUDGET, W.EXTEND)
            self.assertTrue(unknown)
            self.assertIn("budget spent", {u[2] for u in unknown})
        finally:
            W.walk_why = real

    def test_the_census_is_green_again_once_the_token_is_a_known_one(self):
        # The other side of the case above, so a census that refused
        # everything would not pass it: the same collection with the real
        # function has nothing to report.
        _t, _ta, _m, _c, _mm, unknown = W.census_table(
            firmware(), W.BUDGET, W.EXTEND)
        self.assertEqual(unknown, [])


class VerdictTests(unittest.TestCase):
    """Class A, class B, and the two cells that refuse to pick a side. The
    A/B fixtures are hand-built, so a case keeps testing what it was written
    to test if the bytes around some address in the image change."""

    def test_a_direct_dpl_store_before_the_extra_movx_is_class_a(self):
        extra = [(10, DPL_FROM_A, "mov 0x82,a"), (12, READ, "movx a,@dptr")]
        token = W.verdict_for(extra, T.FLOW_END, 8, 64, moved=True)
        self.assertTrue(token.startswith("A: "), token)
        self.assertIn("0x82", token)
        self.assertIn("DPL", token)

    def test_the_mov_0x82_rn_form_is_class_a_too(self):
        # `mov 0x82,r7` is 0x8F 0x82, the other of the two opcodes. A test
        # that only covered 0xF5 would pass on a guard reading `raw[0] == 0xF5`.
        extra = [(10, DPL_FROM_R7, "mov 0x82,r7"), (12, READ, "movx a,@dptr")]
        self.assertTrue(W.verdict_for(extra, T.FLOW_END, 8, 64, moved=True)
                        .startswith("A: "))

    def test_a_dph_store_is_class_a_and_says_dph(self):
        extra = [(10, DPH_FROM_A, "mov 0x83,a"), (12, WRITE, "movx @dptr,a")]
        token = W.verdict_for(extra, T.FLOW_END, 8, 64, moved=True)
        self.assertTrue(token.startswith("A: "), token)
        self.assertIn("DPH", token)
        self.assertIn("write", token)

    def test_no_store_before_the_extra_movx_is_class_b(self):
        extra = [(10, NOP, "mov b,#0x55"), (12, READ, "movx a,@dptr")]
        token = W.verdict_for(extra, T.FLOW_END, 8, 64, moved=True)
        self.assertTrue(token.startswith("B: "), token)

    def test_a_store_after_the_extra_movx_is_not_the_cause_of_it(self):
        # The store has to be *in front of* the movx. One behind it explains
        # the next access, not this one, and a test that scanned the whole
        # extension would put this row in class A.
        extra = [(10, READ, "movx a,@dptr"), (11, DPL_FROM_A, "mov 0x82,a")]
        self.assertTrue(W.verdict_for(extra, T.FLOW_END, 8, 64, moved=True)
                        .startswith("B: "))

    def test_an_extension_budget_that_is_itself_exhausted_is_undecided(self):
        # The reachable refusal: a --extend too small to reach the movx. It
        # must not fall into class B, because "the window was too short to see
        # a store" and "there is no store here" are different findings.
        token = W.verdict_for([(10, DPL_FROM_A, "mov 0x82,a")],
                              T.budget_end(9), 8, 9, moved=True)
        self.assertTrue(token.startswith("undecided"), token)
        self.assertIn("--extend", token)

    def test_no_movx_in_the_hidden_instructions_is_undecided_not_class_b(self):
        # The cell can move on the `inc dptr` span count with no new `movx` in
        # the hidden region, and naming a class there would be a guess about
        # an access this census cannot point at.
        token = W.verdict_for([(10, NOP, "mov b,#0x55")], T.FLOW_END, 8, 64,
                              moved=True)
        self.assertTrue(token.startswith("undecided"), token)

    def test_a_row_whose_cell_does_not_move_says_so_and_names_no_class(self):
        # A diagnosis on a row that keeps its cell is a finding about
        # nothing, and the one thing it must not be is a class.
        extra = [(10, DPL_FROM_A, "mov 0x82,a"), (12, READ, "movx a,@dptr")]
        token = W.verdict_for(extra, T.FLOW_END, 8, 64, moved=False)
        self.assertTrue(token.startswith("unchanged"), token)
        for cls in ("A:", "B:", "undecided"):
            self.assertNotIn(cls, token)

    def test_is_direct_dp_store_is_two_bytes_of_the_right_opcodes(self):
        self.assertTrue(W.is_direct_dp_store(DPL_FROM_A))
        self.assertTrue(W.is_direct_dp_store(DPL_FROM_R7))
        self.assertTrue(W.is_direct_dp_store(DPH_FROM_A))
        self.assertFalse(W.is_direct_dp_store(NOP))
        self.assertFalse(W.is_direct_dp_store(SITE))
        self.assertFalse(W.is_direct_dp_store(READ))
        # A longer instruction whose second byte is 0x82 is not one of these,
        # which is why OPCODE_LEN is not asked here: the length is checked.
        self.assertFalse(W.is_direct_dp_store(bytes([0x90, 0x82, 0x00])))


class ReadSitesTests(unittest.TestCase):
    """The population the census reads, and its refusal to read nothing."""

    def test_a_table_without_the_columns_is_refused(self):
        # A silently empty census reports zero truncated rows and reads as a
        # clean sweep, so a table that is not a site table is an error.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "not-a-site-table.csv")
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["a", "b"])
                w.writerow(["1", "2"])
            with self.assertRaises(ValueError) as cm:
                W.read_sites(path)
            self.assertIn("addr/file_offset", str(cm.exception))

    def test_a_missing_file_is_an_error_not_an_empty_population(self):
        with self.assertRaises(OSError):
            W.read_sites(str(ANNOT / "no-such-table.csv"))


class CommittedCensusTests(unittest.TestCase):
    """`--check` against the committed census, and what it refuses."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(HERE / 'walk_budget_census.py'), FIRMWARE,
             *args], capture_output=True, text=True)

    def test_check_passes_on_the_committed_census(self):
        out = self._run('--check')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("reproduces it byte for byte", out.stdout)
        self.assertIn("walk-budget-census.csv", out.stdout)

    def test_check_fails_on_a_doctored_census(self):
        rows = rows_of('walk-budget-census.csv')
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
        doctored = buf.getvalue().replace("max_insns (8) exhausted",
                                          "flow opcode", 1)
        self.assertNotEqual(doctored, buf.getvalue(),
                            "the doctoring did not take")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "doctored.csv")
            with open(path, "w", newline="") as f:
                f.write(doctored)
            out = self._run('--check', path)
            self.assertEqual(out.returncode, 1)
            self.assertIn("differs from what this run produced", out.stderr)

    def test_check_refuses_a_budget_the_committed_census_does_not_record(self):
        # A default budget here would be a --check that goes green against
        # rows it never looked at, so the run is refused and says why.
        out = self._run('--budget', '16', '--check')
        self.assertEqual(out.returncode, 1)
        self.assertIn("records a budget of 8", out.stderr)
        self.assertIn("used 16", out.stderr)

    def test_the_recorded_budget_is_walk_own_default(self):
        self.assertEqual(W.BUDGET, T.walk.__defaults__[0])
        self.assertEqual(W.load_recorded_budgets(str(ANNOT / 'walk-budget-census.csv')),
                         {W.BUDGET})

    def test_a_budget_below_the_extension_is_refused(self):
        out = self._run('--budget', '64', '--extend', '64')
        self.assertEqual(out.returncode, 1)
        self.assertIn("not larger than", out.stderr)

    def test_a_zero_budget_is_refused(self):
        out = self._run('--budget', '0')
        self.assertEqual(out.returncode, 1)
        self.assertIn("at least 1", out.stderr)

    def test_the_committed_census_holds_the_45_and_the_13(self):
        rows = rows_of('walk-budget-census.csv')
        self.assertEqual(len(rows), 45)
        self.assertEqual(sum(1 for r in rows if r["moves"] == "yes"), 13)
        self.assertEqual(sum(1 for r in rows
                             if r["verdict"].startswith("A: ")), 10)
        self.assertEqual(sum(1 for r in rows
                             if r["verdict"].startswith("B: ")), 3)
        # Every row is a row of a committed table, at the budget that table
        # was cut with, and no row's committed cell differs from the re-derived
        # one -- the census's own loud check, as a fact about the data.
        for r in rows:
            self.assertIn(r["table"], W.TABLES)
            self.assertEqual(r["access_at_budget"],
                             self._committed_access(r["table"], r["file_offset"]))
            self.assertEqual(r["terminator_at_budget"], T.budget_end(W.BUDGET))

    def test_the_four_issue_addresses_are_three_class_b_and_one_class_a(self):
        # The four rows issue #846 named, each at the committed and larger
        # values it quotes. It said four of the 45 move their `access` cell;
        # the measurement is thirteen, and these four are a correct subset.
        want = {
            ("ec-0x07d0-sites.csv", "0x2C2FA"): ("write x1", "read x1, write x1", "A"),
            ("ec-0x07d0-sites.csv", "0x2E8D4"): ("write x1", "read x1, write x1", "B"),
            ("ec-0x07d1-sites.csv", "0x28B8B"): ("read x1", "read x2", "A"),
            ("xdata-0400-045f-sites.csv", "0x0DD4A"): ("read x2, write x1", "read x2, write x2", "B"),
        }
        rows = {(r["table"], r["file_offset"]): r
                for r in rows_of('walk-budget-census.csv')}
        for key, (at8, at64, cls) in want.items():
            self.assertIn(key, rows, f"{key} is not in the committed census")
            row = rows[key]
            self.assertEqual(row["access_at_budget"], at8, key)
            self.assertEqual(row["access_at_extend"], at64, key)
            self.assertTrue(row["verdict"].startswith(f"{cls}: "),
                            f"{key} is not class {cls}: {row['verdict']}")

    def _committed_access(self, table, offset):
        with open(ANNOT / table, newline="") as f:
            for row in csv.DictReader(f):
                if row["file_offset"] == offset:
                    return row["access"]
        self.fail(f"{table} has no row at {offset}")


class ReCutTests(unittest.TestCase):
    """The re-cut: the six tables carry a `terminator` column, the four the
    census measures as clean do not, and no `access` or `window` cell moved in
    any of them.

    The `window` cell at `xdata-0400-045f-sites.csv` `0x11F16` *did* change,
    and it is pinned here rather than left to be noticed in the diff. It reads
    `mov c,acc.0` where it read `db 0xa2`, and that is `disasm8051.py`'s
    current rule for opcode `0xA2` applied to a table that was not regenerated
    when the rule landed. It reproduces on clean `origin/main` and has nothing
    to do with the terminator column."""

    # The six pages whose generating command gained --terminator-column.
    RECUT = ("ec-07c4-07d5-sites.csv", "ec-07d6-07d7-sites.csv",
             "ec-0x07d0-sites.csv", "ec-0x07d1-sites.csv",
             "manual-fan-ctrl-0751-sites.csv", "xdata-0400-045f-sites.csv")
    # The four the census measures as zero, left alone. #800 owns the 0x086x
    # one's `census` column and its --check staying green is the regression
    # test that the default output still has no column in it.
    UNCUT = ("ec-09e9-09eb-sites.csv", "xdata-086x-dispatch-sites.csv",
             "xdata-1c3x-consumers-sites.csv")

    def test_every_recut_table_has_a_terminator_column_and_a_valid_token(self):
        for name in self.RECUT:
            reader = rows_of(name)
            with open(ANNOT / name, newline="") as f:
                header = next(csv.reader(f))
            self.assertEqual(header[-1], "terminator", name)
            for row in reader:
                    self.assertTrue(T.is_terminator(row["terminator"]),
                                    f"{name} row {row['file_offset']}: "
                                    f"{row['terminator']!r}")

    def test_the_uncut_tables_did_not_gain_one(self):
        for name in self.UNCUT:
            with open(ANNOT / name, newline="") as f:
                self.assertNotIn("terminator", next(csv.reader(f)), name)

    def test_the_arms_table_is_not_one_of_them(self):
        # It has a `window` column and is not in W.TABLES: a different
        # producer, keyed on site_runtime, ending on a flow opcode by
        # construction. Folding it in would count another tool's guarantee
        # as this one's measurement.
        arms = rows_of('manual-fan-ctrl-0751-arms.csv')
        self.assertNotIn('manual-fan-ctrl-0751-arms.csv', W.TABLES)
        self.assertTrue(arms)
        self.assertNotIn("file_offset", arms[0])

    def test_the_only_window_cell_that_moved_is_the_preexisting_drift(self):
        # Stated as a count over the committed `git` HEAD's version of each
        # table, so a future re-cut that moves a second cell fails here rather
        # than in a reviewer's eye. Skipped when the tables are not committed
        # (a scratch tree), never skipped to make this pass.
        moved = []
        for name in self.RECUT:
            before = self._committed_at_head(name)
            if before is None:
                continue
            after = rows_of(name)
            old = list(csv.DictReader(io.StringIO(before)))
            self.assertEqual(len(old), len(after), f"{name} row count moved")
            for a, b in zip(old, after):
                for col in a:
                    if a[col] != b[col]:
                        moved.append((name, a["file_offset"], col, a[col], b[col]))
        self.assertEqual(
            moved,
            [("xdata-0400-045f-sites.csv", "0x11F16", "window",
              "movx a,@dptr ; db 0xa2", "movx a,@dptr ; mov c,acc.0")],
            "a second cell moved, or the known drift changed; the load-bearing "
            "claim of this re-cut is that no `access` cell and no other "
            "`window` cell changed")

    def test_no_access_cell_moved_in_any_of_the_six(self):
        # The census's own check, run over the tables rather than over the
        # census: every committed `access` cell is what walk_budget_census
        # re-derives from the image at walk()'s own budget.
        self.assertEqual(W.census_table(firmware(),
                                        W.BUDGET, W.EXTEND)[4], [])

    def _committed_at_head(self, name):
        text = subprocess.run(["git", "show", f"HEAD:ec/annotations/{name}"],
                              cwd=str(REPO), capture_output=True, text=True)
        return text.stdout if text.returncode == 0 else None


class FifteenAddressSweepTests(unittest.TestCase):
    """The regression test that matters.

    `docs/findings/opcode-len-bounds-census.md`'s command 1 diffs a
    114-site sweep against `xdata-086x-dispatch-sites.csv` -- #800's table,
    which this work deliberately did not re-cut. It is what makes "no `access`
    or `window` cell changed in the six tables" a measurement rather than an
    assertion: if `walk_why()` had changed what `walk()` returns, or the
    default `csv_table()` output had gained a column, this is what goes red.
    """

    ADDRESSES = ("0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A "
                 "0x086B 0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07").split()

    def test_the_sweep_reproduces_the_086x_table_byte_for_byte(self):
        out = subprocess.run(
            [sys.executable, str(HERE / 'trace_xdata_refs.py'), FIRMWARE,
             *self.ADDRESSES, '--csv', '--census-column', '--check'],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("reproduces it byte for byte", out.stdout)

    def test_the_sweep_terminators_are_the_75_39_and_0_the_census_committed(self):
        # #805's own tally for this table, which the census of terminators
        # reproduces: 75 DPTR reloads, 39 flow opcodes, no exhausted budget
        # over its 114 rows.
        rows = rows_of('xdata-086x-dispatch-sites.csv')
        self.assertEqual(len(rows), 114)
        d = firmware()
        tokens = {}
        for row in rows:
            token = T.walk_why(d, int(row["file_offset"], 16))[1]
            tokens[token] = tokens.get(token, 0) + 1
        self.assertEqual(tokens, {T.RELOAD_END: 75, T.FLOW_END: 39})

    def test_the_terminator_column_is_opt_in(self):
        # The sweep above is what keeps the default output free of a column,
        # so this asserts the two shapes side by side rather than trusting
        # the absence of a failure.
        d = firmware()
        plain, unmapped = T.csv_table(d, ["0x0860"], True, None)
        wide, _ = T.csv_table(d, ["0x0860"], True, None, terminator=True)
        plain_header = next(csv.reader(io.StringIO(plain)))
        wide_header = next(csv.reader(io.StringIO(wide)))
        self.assertNotIn("terminator", plain_header)
        self.assertEqual(wide_header[-1], "terminator")
        self.assertEqual(plain_header, wide_header[:-1])
        self.assertEqual(len(plain.splitlines()), len(wide.splitlines()))
        self.assertEqual(unmapped, {})
        # Every row's terminator is a token, and the cells before it are the
        # bytes the plain run produced. The header is stepped over: it is the
        # one row that is *meant* to differ, and a zip that included it would
        # report a mismatch that is the feature rather than a defect.
        for plain_row, wide_row in zip(list(csv.reader(io.StringIO(plain)))[1:],
                                       list(csv.reader(io.StringIO(wide)))[1:]):
            self.assertEqual(plain_row, wide_row[:-1])
            self.assertTrue(T.is_terminator(wide_row[-1]))


class CheckNoteTests(unittest.TestCase):
    """A red `--check` that names its own cause.

    Six committed tables carry a `terminator` column and a bare run has none,
    so the diff against one of them is one line of `-` per row and nothing
    about why. The note is the difference between a reader knowing and a
    reader working it out.

    **None of the six can be `--check`ed green, and that is pre-existing.**
    `--check` implies the `census` column -- `main()` loads the census map
    whenever a check is asked for, so the 0x086x table's own column is there
    by default -- so a run against any other table is one column out whichever
    flags it carries. That is exactly why the six pages produce their tables by
    `>` redirect and the census's `Reproducing it` block `diff`s them by hand;
    the cases below are about which note fires, not about going green.
    """

    def _run(self, *addrs, path, flag=None):
        """`--check` against `path`, with `--csv` and the optional column flag.

        `path` is a keyword because it is the value of `--check`'s optional
        argument: passed positionally it would land in `addrs` and be decoded
        as a hex address, which is a run that fails for a reason that has
        nothing to do with what the case is about.
        """
        argv = [sys.executable, str(HERE / 'trace_xdata_refs.py'), FIRMWARE,
                *addrs, '--csv']
        if flag:
            argv.append(flag)
        argv += ['--check', path]
        return subprocess.run(argv, capture_output=True, text=True)

    def test_checking_a_recut_table_without_the_flag_says_so(self):
        out = self._run('0x07D0', path=str(ANNOT / 'ec-0x07d0-sites.csv'))
        self.assertEqual(out.returncode, 1)
        self.assertIn("has a `terminator` column", out.stderr)
        self.assertIn("--terminator-column", out.stderr)
        self.assertIn("this run did not pass it", out.stderr)

    def test_the_note_does_not_fire_when_the_flag_was_passed(self):
        # The run is still red -- `--check` brought its own `census` column --
        # but not for the reason the note is about, and a note here would name
        # the wrong cause.
        out = self._run('0x07D0', path=str(ANNOT / 'ec-0x07d0-sites.csv'),
                        flag='--terminator-column')
        self.assertEqual(out.returncode, 1)
        self.assertNotIn("has a `terminator` column", out.stderr)
        self.assertIn("census", out.stderr)

    def test_a_table_without_the_column_gets_no_note_in_either_direction(self):
        # All fifteen addresses, because one does not reproduce this table:
        # the file carries 105 rows the single-address sweep never reaches.
        # That is the census's own recorded note and it is why command 1 is
        # the fifteen-address form.
        path = str(ANNOT / 'xdata-086x-dispatch-sites.csv')
        out = self._run(*FifteenAddressSweepTests.ADDRESSES, path=path)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("reproduces it byte for byte", out.stdout)
        self.assertNotIn("terminator column", out.stderr)
        # And the other direction: a run that has the column and the table
        # does not. The extra cells are the diff, and a note would repeat it.
        out = self._run(*FifteenAddressSweepTests.ADDRESSES, flag='--terminator-column',
                        path=path)
        self.assertEqual(out.returncode, 1)
        self.assertNotIn("has a `terminator` column", out.stderr)

    def test_the_note_works_against_a_table_this_run_reproduces(self):
        # The strongest form: a copy of a re-cut table with one row's
        # terminator cell doctored, so the only difference is that cell. The
        # note still fires, because it is about the column being absent from
        # the run, not about the diff being large.
        text = text_of('ec-0x07d0-sites.csv')
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "doctored.csv")
            with open(path, "w", newline="") as f:
                f.write(text)
            out = self._run('0x07D0', path=path)
            self.assertEqual(out.returncode, 1)
            self.assertIn("has a `terminator` column", out.stderr)

    def test_an_unreadable_check_path_is_left_to_check_table(self):
        # committed_columns() returns None rather than reporting, so the file
        # is reported once, by the function that owns the read.
        self.assertIsNone(T.committed_columns(str(ANNOT / 'no-such.csv')))
        self.assertIsNone(T.committed_columns(str(ANNOT)))
        out = self._run('0x0860', path=str(ANNOT / 'no-such.csv'))
        self.assertEqual(out.returncode, 1)
        self.assertIn("note:", out.stderr)
        self.assertNotIn("has a `terminator` column", out.stderr)


class DecodedPathTests(unittest.TestCase):
    """The non-`--csv` decode prints the terminator, so the reason is visible
    without a table at all."""

    def test_the_decode_says_which_guard_ended_the_window(self):
        out = subprocess.run(
            [sys.executable, str(HERE / 'trace_xdata_refs.py'), FIRMWARE,
             '0x07D0'], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("window ended: max_insns (8) exhausted", out.stdout)
        self.assertIn("window ended: flow opcode", out.stdout)
        self.assertIn("window ended: DPTR reloaded", out.stdout)

    def test_the_flags_need_the_csv_table(self):
        for flag in ("--terminator-column", "--census-column", "--check"):
            out = subprocess.run(
                [sys.executable, str(HERE / 'trace_xdata_refs.py'), FIRMWARE,
                 '0x07D0', flag], capture_output=True, text=True)
            self.assertEqual(out.returncode, 2, flag)
            self.assertIn("they need --csv", out.stderr, flag)


if __name__ == '__main__':
    unittest.main()
