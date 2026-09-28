# !/usr/bin/env python3
"""Offline checks for check_fixture_pointer_cells.py: committed files only.

The tool derives one thing -- which of a fixture's pointer cells carry no value
-- and holds the fixture README's sentence about them to the answer. Its failure
mode is therefore silence in two directions at once. A rule that stops
*classifying* leaves every empty cell `undocumented` and reddens the committed
tree, which is loud. A rule that stops *firing* on the class it exists for -- a
cell emptied on a `call-target` row with no sentence beside it -- is accepted
silently, and the sentence in the README is what goes stale. So each rule that
makes the tool strict gets a case saying so, and each rule that makes it accept
a cell gets one too, because a checker that has quietly started accepting
everything looks exactly like a checker that is working.

**Three invariants, and where each is held.** Every address the README names is
an empty pointer cell, and the six it names by name are among them
(`TheCommittedTree`); the derived set is exactly those addresses plus the
transfer-seeded residue, disjointly, which is what closes the issue's own
failure (`TheCommittedTree`); and a run that reached nothing is told apart from
a run that found nothing (`TheReachedSomethingRule`, which every class below
holds itself to, and which the two scratch trees either side of each other in
`TheTalliesAreNotAFloor` exist to keep from being a floor).

The fixtures are written inline into a scratch fixture directory under a
temporary root, which keeps each case readable as the CSVs and the README
beside it rather than as a diff against a stored pair, and the CSVs are written
as the text they are so a case reads as the CSV it is about. The real committed
fixture is the last class, and it is what says the CSVs and the README currently
agree.

**Nothing here reads a capture, an EC, or a laptop.** Every path is a
hand-written string in a `tempfile`, and the committed class reads three
committed files with `open()`.
"""
import contextlib
import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# The tool imports nothing of its own, so this is only about finding it; the
# directory is the same sys.path entry its siblings load through.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_fixture_pointer_cells', HERE / 'check_fixture_pointer_cells.py')
cfpc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cfpc)

# The two committed headers, verbatim. A scratch case that used a header of its
# own invention would pass for a rule keyed on a column name this file happens
# to use, and the whole pointer-column and `seed_basis` argument is that neither
# name is keyed on -- so the scratch cases carry the real shapes.
INDEX_HEADER = ("program,addr,name,size,seed_basis,common,annotated,type,basis,"
                "evidence,also_in,out_file\n")
GHIDRA_HEADER = "scope,addr,name,signature,type,comment,evidence,basis\n"

# One row of each CSV whose `evidence` cell carries a value, which is what makes
# an `evidence` column readable at all: the rule qualifies a column on a cell
# that names a path, so a CSV whose every `evidence` cell is empty has no
# pointer column and its empties are invisible. The committed fixture's five
# populated cells are its own version of this and the only reason its other 22
# are read. Every scratch CSV below carries one of these, and the degenerate
# case is pinned on its own in `ThePointerColumnRule`.
POPULATED = ("bank0,0EA2,delay_calls_0ee8,42,annotation,yes,yes,delay,"
             "hand-decoded,ec/decompiled/bank0/0EA2.asm,,bank0/0EA2.c\n")
POPULATED_GHIDRA = ('common,018C,chan_arm_1709,,unresolved,"One arm of a '
                    'three-function family.",ec/decompiled/common/018C.asm,'
                    'hand-decoded\n')

# The scratch corpus, in the committed fixture's own column layout, small enough
# to read in one go: five addresses and all three kinds, and one tie for the
# precedence. `0x0071` is an `annotation` row named by the paragraph, `0x0D40`
# is a `call-target` row named by it as well -- the tie, since both clauses read
# it -- `0x0EA3` is the row no other CSV corroborates, and `0x05E8` is the
# transfer-seeded residue the derivation has to account for and the paragraph
# does not name. The `comment` cell is a whole sentence ending in a period,
# which is the shape `names_a_file()` needs the whitespace clause to refuse.
SCRATCH_INDEX = INDEX_HEADER + (
    POPULATED + "common,0071,dispatch_setup,7,annotation,yes,yes,unresolved,"
    "hand-decoded,,bank1,common/0071.c\n"
    "common,0D40,FUN_CODE_0d40,3,call-target,yes,no,,,,bank1,common/0D40.c\n"
    "common,05E8,FUN_CODE_05e8,6,call-target,yes,no,,,,bank1,common/05E8.c\n")
SCRATCH_GHIDRA = GHIDRA_HEADER + (
    'common,018C,chan_arm_1709,,unresolved,"One arm of a three-function '
    'family.",ec/decompiled/common/018C.asm,hand-decoded\n'
    'bank0,0EA3,mentions_absent_target,,unresolved,"Calls 0xBEEF, which is '
    'named here to pin that a comment naming an address the listings do not '
    'carry produces no citation.",,hand-decoded\n')

# A README that carries a table as well, because the documented-paragraph rule
# skips tables and a fixture README that is nothing but a paragraph would make
# that skip look like it did nothing. The table quotes an address, so a rule
# that read tables as well would name an address twice.
README_WITH_TABLE = (
    "# scratch fixture\n"
    "\n"
    "| file / row | what it pins |\n"
    "|---|---|\n"
    "| `0x1234` | a row the table quotes, which is not a claim about a cell |\n"
    "\n"
    "The frame guard has its own cases, and none of them is about this.\n"
    "\n")


class RunsTheTool:
    """One run of the tool, over a fixture that is not the committed one.

    Split out of `TheReachedSomethingRule` for the same reason it is there in
    `test_check_testdata_index.py`: a refusal whose `Result` fields are right
    and whose *printed* line is wrong is only visible through a run, and
    `TheCommittedTree` runs the tool too while inheriting no scratch fixture. It
    is a base rather than a method on `ScratchFixture` for the same reason.
    """

    def run_tool(self, fixture):
        """(exit code, stdout, stderr) for one run of the tool over `fixture`.

        `main()` reads the committed `FIXTURE` as a module global and has no
        flag pointing it anywhere else, so a scratch tree is reached by patching
        it. `REPO` is the second of the same two: `repo_relative()` reports
        against it, so a run over a `tempfile` with only `FIXTURE` patched would
        print a chain of `..` out of an unrelated root. Both go back in the same
        `finally` that already restored `sys.argv`, for the reason `tools/` §16
        records for the suites that used to leave a fake installed.
        """
        out, err = io.StringIO(), io.StringIO()
        argv, was = sys.argv, (cfpc.FIXTURE, cfpc.REPO)
        sys.argv = ['check_fixture_pointer_cells.py', '--check']
        cfpc.FIXTURE, cfpc.REPO = fixture, os.path.dirname(fixture)
        try:
            with contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err):
                rc = cfpc.main()
        finally:
            sys.argv = argv
            cfpc.FIXTURE, cfpc.REPO = was
        return rc, out.getvalue(), err.getvalue()

    def tallies(self, out):
        """{label: number} for every figure the run printed.

        The parse is part of what is held, not a convenience: the claim being
        pinned is the docstring's, that the tallies print whether or not they
        found anything. Labels are unique across the printed lines for the
        reason `test_check_testdata_index.py` gives for the same parse -- a
        label reused across two lines would let one line's number answer for the
        other's, and `address(es)` is the empty set's here while `named
        address(es)` is the README's.
        """
        counts = {}
        for line in out.splitlines():
            for piece in re.split(r'[:,]', line):
                number, _, label = piece.strip().partition(' ')
                if number.isdigit() and label:
                    counts[label] = int(number)
        return counts


class ScratchFixture(RunsTheTool):
    """A throwaway fixture directory: its CSVs and the README beside them.

    `table()`, `corpus()`, `claims()` and `readme()` build the two things a
    reader of the real fixture has -- CSVs with the headers this file's rules
    read by name, and a paragraph naming the addresses the CSVs leave empty.
    They are written together and the second is supplied with the first on
    purpose: a case whose README names an address its CSVs do not carry is red
    for a reason that has nothing to do with the rule under test, which is the
    same trap the two directions of the tool's own claim set.

    It inherits `RunsTheTool` rather than declaring a runner, because every case
    that builds a tree wants to run the tool over it and the two are one thing
    here; `TheCommittedTree` gets the runner from `TheReachedSomethingRule`
    instead, which is why the runner is a base of its own.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.fixture = os.path.join(self.root, "call-graph")
        os.mkdir(self.fixture)
        self.written = False

    def table(self, name, text):
        """Write one CSV into the scratch fixture, header included."""
        with open(os.path.join(self.fixture, name), "w", encoding="utf-8") as f:
            f.write(text)
        self.written = True
        return os.path.join(self.fixture, name)

    def corpus(self, index=SCRATCH_INDEX, ghidra=SCRATCH_GHIDRA,
               claims=('0x0071', '0x0D40', '0x0EA3')):
        """The standard corpus, or the two CSVs and the claim a case supplies.

        The defaults are the shape above. A case passes its own text for either
        CSV, and the addresses its CSVs leave empty for `claims`, so the README
        and the files are written in the same call and cannot drift apart by
        accident.

        Whichever CSVs it is *not* given are removed first, so the call is the
        whole of the tree rather than an addition to it. A case that replaced
        one CSV and left the other would have the other one's rows read as
        unexplained empties, and would be red for a reason that has nothing to
        do with the rule under test.
        """
        for name in os.listdir(self.fixture):
            if name.endswith(".csv"):
                os.unlink(os.path.join(self.fixture, name))
        if index is not None:
            self.table('index.csv', index)
        if ghidra is not None:
            self.table('ghidra-functions.csv', ghidra)
        self.claims(*claims)

    def claims(self, *addresses):
        """Write a README whose empty-cell paragraph names exactly these.

        The paragraph is the shape the committed fixture writes: the word, then
        the backticked addresses, each spelled the way the README spells one
        (`0x0D20`, not `0D20`) because the `0x` is part of what the tool reads.
        No numeral in it, so a case that names one address and a case that names
        three read the same and the sentence is never what carries a count.
        """
        named = ", ".join(f"`{address}`" for address in addresses)
        self.readme("A cell whose path the real tree does not have turns the "
                    f"check red, so the addresses below have their cell "
                    f"**empty**: {named}.\n")

    def readme(self, *paragraphs):
        """Write the scratch README, with the table above the paragraphs."""
        with open(os.path.join(self.fixture, 'README.md'), "w",
                  encoding="utf-8") as f:
            f.write(README_WITH_TABLE + "\n".join(paragraphs))

    def readme_text(self):
        """The scratch README as it stands, for a case that reads the claim."""
        with open(os.path.join(self.fixture, 'README.md'),
                  encoding="utf-8") as f:
            return f.read()

    def result(self):
        """A `Result` for the scratch fixture as it stands."""
        self.assertTrue(self.written,
                        "no CSV was written, so there is nothing to "
                        "derive from")
        return cfpc.check(self.fixture)

    def green(self):
        """Assert a run over the scratch fixture is green, and hand it back.

        The failure is the whole of the stderr, because a case that is refused
        should say why in the reader's terms rather than only that something was
        refused.
        """
        rc, out, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 0, err)
        return self.result()

    def red(self):
        """Assert a run over the scratch fixture is red, and hand it back."""
        rc, out, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 1, out)
        return self.result()


class TheReachedSomethingRule(RunsTheTool):
    """The one rule about a run's tallies, over whatever fixture it is handed.

    `check_fixture_pointer_cells.py`'s docstring says the tallies print whether
    or not they found anything, and gives the degenerate case as the reason: a
    pointer column emptied in every cell no longer qualifies as one, so the run
    reads nothing and reads it correctly. That is this. The fixture is a
    parameter rather than `cfpc.FIXTURE` so the rule is a property of a run and
    can be pointed at a scratch tree beside the committed one; the two are held
    to the same method, so neither half can be edited alone.
    """

    def assert_the_run_reached_something(self, fixture):
        """Assert a run over `fixture` read something, and that it read it.

        Each of the six tallies non-zero, read out of what the run *printed*
        rather than off a `Result`, because the claim being pinned is the
        docstring's. Each is named in its message so a case that is refused
        knows which clause said so.
        """
        rc, out, err = self.run_tool(fixture)
        self.assertEqual(rc, 0, err)
        counts = self.tallies(out)
        for name, label in (('CSVs', 'fixture CSV(s)'),
                            ('pointer columns', 'pointer column(s)'),
                            ('pointer cells', 'pointer cell(s)'),
                            ('empty cells', 'empty cell(s)'),
                            ('addresses', 'address(es)'),
                            ('named addresses', 'named address(es)')):
            self.assertGreater(
                counts.get(label, 0), 0,
                f"the run reached no {name}: a run that checked nothing and a "
                "run that found nothing look the same from the exit code alone")


class TheCommittedTree(TheReachedSomethingRule, unittest.TestCase):
    """The real thing: the fixture's CSVs and its README currently agree.

    This goes red on any future edit that drifts them apart -- a cell filled in
    that the README calls empty, an address the README names that no CSV row
    carries, an empty cell with nothing beside it explaining why. It does not go
    red on the tree being a different size, which is what
    `TheTalliesAreNotAFloor` is about, and it does not go red on a `call-target`
    row gaining another empty cell, which is the class the tool is built to
    accept.
    """

    def readme_text(self):
        with open(os.path.join(cfpc.FIXTURE, 'README.md'),
                  encoding='utf-8') as f:
            return f.read()

    def test_the_run_reaches_something(self):
        self.assert_the_run_reached_something(cfpc.FIXTURE)

    def test_every_address_the_readme_names_has_an_empty_cell(self):
        # The invariant, in the direction that matters: every address the
        # paragraph names is a pointer cell carrying no value. This is the #780
        # fix that was declined -- repointing `bank0,0EA3` at the real
        # `bank0/0EA2.asm` fills a cell rather than emptying one, and no other
        # rule here would notice, so the case below spells the six out and a
        # later edit that fills one in lands on it.
        named = cfpc.documented(self.readme_text())
        result = cfpc.check(cfpc.FIXTURE)
        empty = {entry.value for entry in result.entries}
        for address in named:
            self.assertIn(address, empty,
                          f"the README names 0x{address:04X} for a cell "
                          f"carrying no value and no pointer cell in the CSVs "
                          f"is empty for it")
        self.assertEqual(result.noempty, [])

    def test_the_six_addresses_the_readme_decided_on_are_all_derived(self):
        # The six are a record of a decision rather than a class anything
        # derives, and this is the claim rather than a census: it says each of
        # them is still named in the README *and* still empty in the CSVs, so
        # deleting one from the sentence is red and filling one in is red. The
        # list is six addresses and no figure, and it moves only when somebody
        # edits the sentence it is holding.
        named = cfpc.documented(self.readme_text())
        empty = {entry.value for entry in cfpc.check(cfpc.FIXTURE).entries}
        for address in ('0x0D20', '0x0D40', '0x0EA3', '0x0071', '0xF6A0',
                        '0x10E0'):
            value = cfpc.as_address(address)
            self.assertIn(value, named,
                          f"the README no longer names {address} in its "
                          f"empty-cell paragraph")
            self.assertIn(value, empty,
                          f"{address} is still named but its cell is not empty")

    def test_the_derived_set_is_the_named_addresses_and_the_residue(self):
        # The disjoint covering, and the whole of the issue: every empty cell is
        # either an address the README accounts for or a row a transfer scan
        # seeded, and the two never overlap. Red the moment a cell is emptied on
        # a row the transfer scan did not seed with no sentence beside it, and
        # red the moment an address falls in both classes. Asserting a count of
        # the tree instead would be the census `CLAUDE.md` warns about, and it
        # would move on every fixture edit.
        named = set(cfpc.documented(self.readme_text()))
        result = cfpc.check(cfpc.FIXTURE)
        derived = {entry.value for entry in result.entries}
        seeded = {entry.value for entry in result.entries
                  if entry.kind == cfpc.TRANSFER_SEEDED}
        self.assertEqual(derived, named | seeded)
        self.assertEqual(named & seeded, set(),
                         "an address the README names and a transfer scan "
                         "seeded is in both classes, so the covering is not "
                         "the disjoint one the tool's precedence is built for")

    def test_every_entry_carries_one_of_the_three_kinds(self):
        # `undocumented` is the residue and it fails, so the kinds a run reaches
        # are read here rather than taken from the exit code: a fourth rule
        # added to `kind_of()` would print a word this suite has never been
        # asked about, and the report would look the same.
        result = cfpc.check(cfpc.FIXTURE)
        self.assertTrue(
            all(entry.kind in (cfpc.DOCUMENTED, cfpc.SYNTHETIC,
                               cfpc.TRANSFER_SEEDED)
                for entry in result.entries),
            "the classification left something outside the three kinds the "
            "docstring documents")

    def test_the_synthetic_row_is_its_own_kind_and_not_a_documented_one(self):
        # `0x0EA3` is in the README's six and is still `synthetic`: the address
        # is carried by one CSV and that CSV records no `seed_basis`, which is a
        # fact about the columns and outranks the prose. The other five are
        # `documented`. If the precedence were dropped and the prose read first,
        # the six would collapse into one list, which is the distinction #780's
        # write-up exists to preserve.
        kinds = {entry.value: entry.kind
                 for entry in cfpc.check(cfpc.FIXTURE).entries}
        self.assertEqual(kinds.get(cfpc.as_address('0x0EA3')), cfpc.SYNTHETIC)
        for address in ('0x0D20', '0x0D40', '0x0071', '0xF6A0', '0x10E0'):
            self.assertEqual(kinds.get(cfpc.as_address(address)),
                             cfpc.DOCUMENTED,
                             f"{address} is named in the README and should be "
                             f"classified from the prose")

    def test_every_empty_cell_is_in_the_evidence_column(self):
        # The README's own correction says which column each entry came from,
        # and the honest answer is that one column contributes all of them: the
        # sibling `out_file` column has no cell carrying no value at all. Read
        # from the tool rather than quoted, so the sentence and the derivation
        # cannot drift apart.
        result = cfpc.check(cfpc.FIXTURE)
        self.assertEqual({entry.column for entry in result.entries},
                         {'evidence'})

    def test_the_evidence_column_is_read_and_its_siblings_are_not(self):
        # Which columns the structural rule lands on, for the committed tree:
        # the `evidence` of both CSVs, and neither `comment` (a sentence per
        # cell) nor `also_in` (a program name). Stated as what is and is not
        # read rather than as a count, so a fixture that gains a fourth pointer
        # column later does not redden a case that was never about the size of
        # the fixture.
        for name, read, unread in (('index.csv', 'evidence', 'also_in'),
                                   ('ghidra-functions.csv', 'evidence',
                                    'comment')):
            header, rows = cfpc.read_table(os.path.join(cfpc.FIXTURE, name))
            columns = {column for _, column
                       in cfpc.pointer_columns(header, rows)}
            self.assertIn(read, columns)
            self.assertNotIn(unread, columns)


class ThePointerColumnRule(ScratchFixture, unittest.TestCase):
    """Which columns the tool reads, decided by what they hold.

    The clause is structural rather than an exemption list, and the case at the
    bottom is the one that matters: a fixture directory this file has never
    seen, with its own CSVs and its own README, read with no edit here.
    """

    def setUp(self):
        super().setUp()
        self.corpus()

    def test_a_column_holding_a_path_is_read(self):
        header, rows = cfpc.read_table(os.path.join(self.fixture, 'index.csv'))
        self.assertEqual([column for _, column
                          in cfpc.pointer_columns(header, rows)],
                         ['evidence', 'out_file'])

    def test_a_column_holding_program_names_is_not_a_pointer_column(self):
        # `also_in` is `bank0`/`bank1`: no extension, so no path. Reading it
        # would make every one of those cells an empty pointer cell, and the
        # report would name a column that holds nothing to be empty.
        header, rows = cfpc.read_table(os.path.join(self.fixture, 'index.csv'))
        self.assertNotIn('also_in',
                         {column for _, column
                          in cfpc.pointer_columns(header, rows)})

    def test_a_column_with_no_path_in_it_anywhere_is_not_read(self):
        # The declared limit, pinned from the side that is usually wrong. A CSV
        # whose only pointer column is empty in every cell has no path-shaped
        # cell left, so the column does not qualify and its cells are invisible:
        # the run reaches nothing and says so, and the README's claim has
        # nothing behind it, so it is red rather than green. That is the whole
        # of what stands between this rule and a silently empty run.
        self.corpus(index=INDEX_HEADER + "common,0071,dispatch_setup,7,"
                    "call-target,yes,no,,,,bank1,\n",
                    ghidra=None, claims=())
        rc, out, err = self.run_tool(self.fixture)
        self.assertIn('0 pointer column(s), 0 pointer cell(s)', out)
        self.assertEqual(rc, 1)
        self.assertIn('no claim here to hold the derivation to', err)

    def test_a_sentence_is_not_a_path_even_when_it_ends_in_one(self):
        # The clause this file adds to `names_a_file()`, and the reason it is
        # needed: `ghidra-functions.csv`'s `comment` cells are sentences, and
        # `splitext` on a sentence ending in a period reads a file whose
        # extension is `.`. Without the whitespace test the whole comment column
        # qualifies and every comment becomes a pointer cell.
        self.corpus(index=None, ghidra=SCRATCH_GHIDRA, claims=('0x0EA3',))
        result = self.result()
        self.assertEqual(result.columns, 1)
        self.assertEqual([entry.column for entry in result.entries],
                         ['evidence'])

    def test_a_semicolon_joined_cell_qualifies_through_either_half(self):
        # The one multi-pointer cell in the committed tree is `;`-joined and has
        # spaces in it, so the test is over a cell's tokens rather than over the
        # cell. A cell read whole has whitespace and the clause above refuses
        # it.
        self.corpus(index=INDEX_HEADER +
                    "bank0,0EA2,delay_calls_0ee8,42,annotation,yes,yes,delay,"
                    "hand-decoded,ec/decompiled/bank0/0EA2.asm; "
                    "ec/decompiled/bank0/0EA2.c,,bank0/0EA2.c\n",
                    ghidra=None, claims=())
        self.assertEqual([column for _, column
                          in cfpc.pointer_columns(*cfpc.read_table(
                              os.path.join(self.fixture, 'index.csv')))],
                         ['evidence', 'out_file'])

    def test_a_fixture_directory_this_file_has_never_seen_is_read(self):
        # The structural argument, tested the way `test_check_testdata_index.py`
        # tests its self-indexed clause: a directory name absent from the
        # committed tree, a CSV nothing above it names, a header of four columns
        # rather than twelve, and a README this file has never parsed.
        os.rename(self.fixture, os.path.join(self.root, "next-fixture"))
        self.fixture = os.path.join(self.root, "next-fixture")
        self.corpus(index="scope,addr,evidence,basis\n"
                    "common,0EA2,ec/decompiled/bank0/0EA2.asm,hand-decoded\n"
                    "common,0071,,hand-decoded\n",
                    ghidra=None, claims=('0x0071',))
        rc, out, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 0, err)
        self.assertIn('1 empty cell(s), 1 address(es)', out)


class TheVerdicts(ScratchFixture, unittest.TestCase):
    """What a cell carrying a value is told, and what that verdict is not.

    Existence is deliberately not among the questions -- the module docstring
    gives the measured reason -- so the case that matters is the one holding
    `unresolved` to a token whose shape no path rule reads, and holding it to
    *not* failing the run.
    """

    def setUp(self):
        super().setUp()
        self.corpus()

    def test_a_cell_carrying_a_path_is_resolved(self):
        self.corpus(index=INDEX_HEADER + POPULATED +
                    "common,0071,dispatch_setup,7,annotation,yes,yes,"
                    "unresolved,hand-decoded,ec/decompiled/common/0071.asm,,"
                    "common/0071.c\n"
                    "common,0D40,FUN_CODE_0d40,3,call-target,yes,no,,,,"
                    "bank1,common/0D40.c\n",
                    ghidra=None, claims=('0x0D40',))
        result = self.green()
        self.assertEqual(result.unresolved, [])
        self.assertEqual([entry.row for entry in result.entries],
                         ['common,0D40'])

    def test_a_token_that_is_not_shaped_like_a_path_is_unresolved_not_red(self):
        # An address range in a pointer cell, the shape
        # `check_testdata_index.py`'s `names_a_file()` docstring names as the
        # one that must not be joined onto a directory. "Not resolved by this
        # method", never "the file is absent" -- the line
        # `ec/annotations/registers.yaml` carries and this tool repeats. A run
        # that failed here would be a check that false-positives, which is the
        # condition #746 set on the whole direction.
        self.corpus(index=INDEX_HEADER + POPULATED +
                    "common,0071,dispatch_setup,7,annotation,yes,yes,"
                    "unresolved,hand-decoded,0x0700-0x07FF,,common/0071.c\n"
                    "common,0D40,FUN_CODE_0d40,3,call-target,yes,no,,,,"
                    "bank1,common/0D40.c\n",
                    ghidra=None, claims=('0x0D40',))
        result = self.green()
        self.assertEqual(len(result.unresolved), 1)
        self.assertEqual(result.unresolved[0][1], 'evidence')
        self.assertIn('0x0700-0x07FF', result.unresolved[0][3])

    def test_a_cell_carrying_no_value_is_empty_and_not_a_finding(self):
        # `empty` is what this tool exists to report, and on its own it is not
        # an error: every row carrying one below has a reason -- two are named
        # by the paragraph, one is the uncorroborated row, one is the transfer-
        # seeded residue.
        result = self.green()
        self.assertEqual({entry.kind for entry in result.entries},
                         {cfpc.DOCUMENTED, cfpc.SYNTHETIC,
                          cfpc.TRANSFER_SEEDED})

    def test_a_row_that_stops_short_is_read_as_an_empty_cell(self):
        # A short row is a real shape -- a trailing column dropped from the last
        # line of a hand-edited file -- and reading it as an empty cell is the
        # honest answer for a column being reported on, rather than an index
        # error half way through a run. This row's `evidence` carries a value,
        # so the one cell it is short of is `out_file`'s and the report is about
        # that one column.
        self.corpus(index=INDEX_HEADER + POPULATED +
                    "common,0071,dispatch_setup,7,call-target,yes,no,"
                    "ec/decompiled/common/0071.asm,hand-decoded,bank1\n",
                    ghidra=None, claims=('0x0071',))
        self.assertEqual([(entry.row, entry.column, entry.kind)
                          for entry in self.green().entries],
                         [('common,0071', 'out_file', cfpc.DOCUMENTED)])

    def test_a_row_that_stops_short_in_the_pointer_column(self):
        # The same shape several columns earlier, where what is missing is the
        # cell this tool exists to report. `csv.reader` gives a short row and
        # reading past it is the mistake; the cell is reported, not skipped.
        self.corpus(index=INDEX_HEADER + POPULATED +
                    "common,0071,dispatch_setup,7,call-target,yes,no,,,,\n",
                    ghidra=None, claims=('0x0071',))
        self.assertEqual({(entry.row, entry.column)
                          for entry in self.green().entries},
                         {('common,0071', 'evidence'),
                          ('common,0071', 'out_file')})

    def test_a_row_with_no_address_column_is_reported_by_its_scope(self):
        # A CSV the tool cannot key to an address. The empty cell is not quietly
        # dropped: the row's own cells name it, and the classification says the
        # CSV has no `seed_basis` column rather than guessing at a reason.
        self.corpus(index=None,
                    ghidra="scope,name,evidence,basis\n"
                           "common,chan_arm_1709,ec/decompiled/common/018C.asm,"
                           "hand-decoded\n"
                           "common,chan_arm_1708,,hand-decoded\n",
                    claims=())
        rc, out, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 1)
        self.assertIn('no `seed_basis` column', err)
        self.assertIn('common', err)


class TheKindRule(ScratchFixture, unittest.TestCase):
    """The three kinds, in precedence order, and the residue that fails.

    One case per rule and one per edge the docstring names, because a kind is
    the part of an entry a reader cannot check from the report: it is derived,
    and a derivation that stopped would print the same word without the same
    work behind it.
    """

    def setUp(self):
        super().setUp()
        self.corpus()

    def kinds(self):
        return {entry.addr: entry.kind for entry in self.result().entries}

    def test_a_call_target_row_with_no_listing_is_transfer_seeded(self):
        self.assertEqual(self.kinds().get('05E8'), cfpc.TRANSFER_SEEDED)

    def test_a_row_no_other_csv_carries_is_synthetic(self):
        # The `ghidra-functions.csv` shape: no `seed_basis` column, and no row
        # at the same address in the other CSV, so nothing in the fixture
        # records where the row came from.
        self.assertEqual(self.kinds().get('0EA3'), cfpc.SYNTHETIC)

    def test_an_address_the_readme_names_is_documented(self):
        self.assertEqual(self.kinds().get('0071'), cfpc.DOCUMENTED)

    def test_documented_outranks_transfer_seeded(self):
        # Both clauses read the same row: `common,0D40` is in the paragraph
        # *and* is a `call-target` row, and the prose wins. The precedence is
        # what keeps the six from being reclassified by a later edit to a
        # `seed_basis` cell, and the committed tree's `0x0D40` and `0xF6A0` are
        # this same tie.
        header, rows = cfpc.read_table(os.path.join(self.fixture, 'index.csv'))
        self.assertEqual(cfpc.seed_basis(header, rows[2]), 'call-target')
        self.assertEqual(self.kinds().get('0D40'), cfpc.DOCUMENTED)

    def test_synthetic_outranks_documented(self):
        # `0x0EA3` is in the paragraph and is synthetic: the two clauses
        # disagree about it and the column set outranks the sentence. This is
        # the one place the committed tree exercises the ordering -- `0x0071`,
        # `0xF6A0`, `0x10E0` and `0x0D20` are all carried by both CSVs, so no
        # clause but `documented` can fire on them.
        self.assertIn(cfpc.as_address('0x0EA3'),
                      cfpc.documented(self.readme_text()))
        self.assertEqual(self.kinds().get('0EA3'), cfpc.SYNTHETIC)

    def test_a_row_the_transfer_scan_did_not_seed_is_undocumented_and_red(self):
        # The issue's own failure, one cell: emptied on an `annotation` row,
        # with no sentence beside it. The run is red and the message names the
        # row and the `seed_basis` it read, so a reader is told which edit to
        # make rather than only that one is owed.
        self.corpus(index=INDEX_HEADER + POPULATED +
                    "common,0071,dispatch_setup,7,annotation,yes,yes,"
                    "unresolved,hand-decoded,,bank1,common/0071.c\n"
                    "common,018C,chan_arm_1709,4,annotation,yes,yes,unresolved,"
                    "hand-decoded,,,common/018C.c\n",
                    ghidra=None, claims=('0x0071',))
        rc, out, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 1)
        self.assertIn('common,018C', err)
        self.assertIn('carries no value', err)
        self.assertIn('`seed_basis=annotation`', err)
        self.assertIn('1 disagreement(s)', err)


class TheClaimIsHeldBothWays(TheReachedSomethingRule, ScratchFixture,
                             unittest.TestCase):
    """The README's sentence, against the CSVs, from both sides.

    These are the two ways the prose can be left behind and the one way it is
    not: a cell filled in, an address deleted from the sentence, and a cell
    emptied on a row the tool has a rule for -- which is green and needs nothing
    added, and that green is the one that matters, because it is what a later
    issue's edit looks like when it is the edit the tool was built to allow.
    """

    def setUp(self):
        super().setUp()
        self.corpus()

    def test_the_fixture_as_built_is_green(self):
        self.assert_the_run_reached_something(self.fixture)

    def test_filling_in_a_named_cell_is_red(self):
        # The #780 fix that was declined, in the shape a future edit would take
        # it: the cell stops being empty and the sentence is left behind. No
        # other rule here would notice, because a filled-in cell is a `resolved`
        # one.
        self.corpus(index=SCRATCH_INDEX.replace(
            "annotation,yes,yes,unresolved,hand-decoded,,bank1,common/0071.c",
            "annotation,yes,yes,unresolved,hand-decoded,"
            "ec/decompiled/common/0071.asm,,common/0071.c"))
        rc, out, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 1)
        self.assertIn('0x0071', err)
        self.assertIn('no pointer cell in the CSVs is empty for it', err)

    def test_deleting_an_address_from_the_sentence_is_red(self):
        # The other direction: the address is still empty in the CSV and nothing
        # accounts for why, so it is the `undocumented` residue. The message
        # names the row, which is the edit a reader has to make. `0x0071` is an
        # `annotation` row, as the committed fixture's is, so the residue is
        # what it would be there.
        self.claims('0x0D40', '0x0EA3')
        rc, out, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 1)
        self.assertIn('common,0071', err)
        self.assertIn('carries no value', err)

    def test_emptying_a_call_target_cell_is_green_and_needs_no_sentence(self):
        # The class the tool accepts, and the edit a later issue would make:
        # `0x05E8` is a `call-target` row whose `evidence` cell starts out
        # carrying a value, and emptying it needs nothing added to the README.
        # Both runs are asserted because the one that matters is the second: a
        # rule that reddened the residue would make every future fixture edit a
        # failure, which is the trade `docs/agent-pipeline.md` records.
        self.corpus(index=SCRATCH_INDEX.replace(
            "common,05E8,FUN_CODE_05e8,6,call-target,yes,no,,,,bank1,"
            "common/05E8.c",
            "common,05E8,FUN_CODE_05e8,6,call-target,yes,no,,,"
            "ec/decompiled/common/05E8.asm,bank1,common/05E8.c"))
        rc, out, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 0, err)
        self.assertNotIn('05E8',
                         [entry.addr for entry in self.result().entries])
        self.corpus()
        rc, out, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 0, err)
        result = self.result()
        self.assertEqual({entry.kind for entry in result.entries
                          if entry.addr == '05E8'}, {cfpc.TRANSFER_SEEDED})

    def test_a_readme_naming_no_empty_cell_is_red(self):
        # Nothing to hold the derivation to. A green run here would be a check
        # that checked nothing, which is the same thing the tallies guard
        # against and the one case where the two would otherwise agree.
        self.corpus(claims=())
        self.readme("Nothing in this fixture is emptied.\n")
        rc, out, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 1)
        self.assertIn('no claim here to hold the derivation to', err)

    def test_a_paragraph_about_the_cells_that_names_none_is_not_a_claim(self):
        # A correction carries the word and no backticked address, so it is not
        # a second claim: the two together name what the first one does. This is
        # the clause that stops a correction *about* the sentence from becoming
        # a second sentence to hold, and it is the reason the committed
        # fixture's correction does not repeat the six addresses.
        self.corpus(claims=('0x0071', '0x0D40'))
        self.readme("A cell whose path the real tree does not have turns the "
                    "check red, so the addresses below have their cell "
                    "**empty**: `0x0071`, `0x0D40`.\n",
                    "*(**Correction, 2026-09-27, issue #1006.** The cells "
                    "carrying no value are more numerous than the ones the "
                    "paragraph names, and those are a record of a decision "
                    "rather than a derived class. The measurement is in "
                    "`docs/findings/fixture-empty-pointer-cells.md`.)*\n")
        named = cfpc.documented(self.readme_text())
        self.assertEqual(sorted(named),
                         sorted(cfpc.as_address(a)
                                for a in ('0x0071', '0x0D40')))


class TheTalliesAreNotAFloor(TheReachedSomethingRule, ScratchFixture,
                             unittest.TestCase):
    """`TheReachedSomethingRule`, pointed at scratch trees, from both sides.

    The rule exists because the tool's own degenerate case is invisible from the
    exit code: a pointer column emptied in every cell stops qualifying as one,
    and a run over a fixture that has only that reads nothing. A floor on any
    tally would catch it and would also make every fixture edit a failure, which
    is the trade `docs/agent-pipeline.md` records about gates and the reason
    non-emptiness is the assertion instead.

    Two trees either side of each other, so the assertion cannot be reading a
    minimum, and a run over each that reached something, so it cannot be reading
    nothing. Every case calls the method the committed case calls: a floor
    reinstated in the helper fails here, and a clause dropped here fails on the
    committed tree being the wrong size to notice.
    """

    def one_cell(self):
        self.corpus(index=INDEX_HEADER + POPULATED +
                    "common,0071,dispatch_setup,7,call-target,yes,no,,,,"
                    "bank1,common/0071.c\n",
                    ghidra=None, claims=('0x0071',))

    def three_cells(self):
        self.corpus()

    def test_a_tree_with_one_empty_cell_is_green_and_reaches_something(self):
        self.one_cell()
        self.assert_the_run_reached_something(self.fixture)

    def test_a_tree_with_three_empty_cells_is_green_and_reaches_something(self):
        self.three_cells()
        self.assert_the_run_reached_something(self.fixture)

    def test_the_two_trees_report_different_figures_and_both_pass(self):
        # The point of the pair in one case: the tallies are a census of what a
        # run read, not a threshold it is held to. A rule that insisted on a
        # number would have to pick one of these two and be wrong on the other,
        # which is the lock `CLAUDE.md` describes for a total written in prose.
        self.one_cell()
        rc, small, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 0, err)
        self.three_cells()
        rc, large, err = self.run_tool(self.fixture)
        self.assertEqual(rc, 0, err)
        self.assertLess(self.tallies(small)['empty cell(s)'],
                        self.tallies(large)['empty cell(s)'])


if __name__ == '__main__':
    unittest.main()
