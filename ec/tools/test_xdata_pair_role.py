#!/usr/bin/env python3
"""The `pair_role` column is the split `inc_dptr_sites.py` derives, held against
that derivation rather than against a figure (issue #734).

`xdata_register_map.py --self-test` already pins the column's own contract on
the committed CSV: it sits last, its cells are the declared vocabulary, and the
two roles partition what the pair pass reaches. All of that reads *the file*.
This suite asks the one question the file cannot answer about itself -- whether
those cells are still what the tool that motivated the column would say today
-- by re-running `inc_dptr_sites.pair_pass()` over the committed tree and
comparing cell for cell. A column generated from the same walk could agree by
accident once and then drift; this is what makes it unable to.

**The population is measured, not typed.** `PAIR_ROWS` is read out of
`xdata_register_map`, the module that pins it, rather than copied here; the
seed and `inc DPTR`-half sets are counted rather than asserted at a figure.
The numbers that are findings live in `docs/findings/xdata-pair-role-column.md`
beside the command that prints them.

**Both roles are compared, not one.** An address can be a seed in one call and
another call's `+1`, in which case the cell is `seed+inc-dptr` and the address
belongs in both sets. The comparison is therefore over the *role set* each side
has for each address, which is what catches a writer that keeps one role and
drops the other -- and the disjointness of the two sets is asserted separately
rather than assumed by it, so an overlap fails here as itself instead of
silently shrinking both populations.

**Why this is not `test_xdata_register_map.py`.** That file's module docstring
scopes it to the refusal contract of the tool's two census flags, its four
classes are all about refusals and scratch-write runs, and the check above
needs a cross-tool import it has no precedent for. CLAUDE.md's "new work goes
in new files" applied to a test rather than to a tool. The census-side half of
the same claim is in the tool's own `--self-test`, which CI already gates.

**What is not re-tested here.** `inc_dptr_sites.py`'s own refusals and its
"writes stdout and nothing else" tripwire are `test_inc_dptr_sites.py`'s, and
that suite owns them; duplicating the classes would make two files that fail
together for one reason. What this suite does carry is the one regression that
belongs to *this* change: `scan()` grew a `pair_roles` set that `absorb()`
folds across scopes, and `inc_dptr_sites.py` reaches both through its own
`census_by_addr()`, so a broken `absorb()` would take the sibling tool down
too. That is why `TheSiblingTool` runs `--check` rather than trusting that
nothing else uses these two functions.
"""
import csv
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).parent
EC = HERE.parent
# inc_dptr_sites imports xdata_register_map and trace_xdata_refs by bare module
# name, so the tool directory has to be on the path before it is loaded.
sys.path.insert(0, str(HERE))
import inc_dptr_sites as ids  # noqa: E402
import xdata_register_map as xrm  # noqa: E402

REGISTERS_CSV = xrm.OUT_REGISTERS


def pair_pass() -> dict:
    """`inc_dptr_sites.pair_pass()` over the committed tree, once per call.

    The function under test rather than `ids.build()`, because `build()` also
    reads the firmware and `registers.yaml` and this suite's claim is about the
    decompiled walk alone.
    """
    _funcs, by_file = xrm.load_index()
    return ids.pair_pass(xrm.load_pair_accessors(), by_file, xrm.load_symbols())


def roles_of(entry: dict) -> set:
    """The roles `inc_dptr_sites` gives an address, as a set.

    `reached_as_seed` and `directions` are the tool's own record of the two
    halves, and neither implies the other -- `pair_pass()`'s docstring is the
    argument -- so this is the derivation the census's cell is compared against.
    """
    roles = set()
    if entry["reached_as_seed"]:
        roles.add(xrm.PAIR_SEED)
    if entry["directions"]:
        roles.add(xrm.PAIR_INC)
    return roles


def census_roles() -> dict:
    """{addr int: the roles the committed CSV's cell gives it}."""
    out = {}
    with open(REGISTERS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            out[int(row["addr"], 0)] = set(row["pair_role"].split("+")) \
                - {""}
    return out


class TheColumnMatchesTheTool(unittest.TestCase):
    """Every committed cell is what `pair_pass()` says that address's role is.

    One fresh walk for the whole class: it reads the whole decompiled tree, and
    the tool is deterministic over committed inputs, which is the property the
    committed-file cases below rest on.
    """

    @classmethod
    def setUpClass(cls):
        cls.resolved = pair_pass()
        cls.census = census_roles()

    def test_every_address_agrees_cell_for_cell(self):
        # A partition over the pair-reached population in both directions, not
        # two set equalities: an address the tool reaches that the CSV leaves
        # empty, a CSV row carrying a role the tool does not reach, and an
        # address both reach with different roles are three different failures
        # and each is named. Naming the addresses is the point -- a count alone
        # would say the files disagree without saying where.
        tool = {a: roles_of(e) for a, e in self.resolved.items()}
        labelled = {a for a, r in self.census.items() if r}
        only_census = sorted(labelled - set(tool))
        only_tool = sorted(set(tool) - labelled)
        disagree = sorted(a for a in set(tool) & labelled
                          if tool[a] != self.census[a])
        shown = ", ".join(f"0x{a:04X}" for a in (only_census + only_tool
                                                 + disagree)[:8]) or "none"
        self.assertEqual(
            (only_census, only_tool, disagree), ([], [], []),
            f"{shown}: the committed `pair_role` column disagrees with "
            f"`inc_dptr_sites.pair_pass()` -- {len(only_census)} labelled in "
            f"the CSV and not reached by the walk, {len(only_tool)} reached "
            f"by it and left empty in the CSV, and {len(disagree)} in both "
            f"with different roles")

    def test_the_empty_cell_is_the_answer_and_not_an_omission(self):
        # Every row with no role is an address no pair call reaches. Asserted
        # over the whole CSV rather than over the pair rows alone, because the
        # claim is about the column being written everywhere: a column absent
        # from the rows it does not cover could not be told from one whose
        # cells are all empty.
        with open(REGISTERS_CSV, newline="") as f:
            rows = list(csv.DictReader(f))
        blank = {int(r["addr"], 0) for r in rows if not r["pair_role"]}
        self.assertTrue(len(rows) > len(blank),
                        "no row has an empty `pair_role`, so the column is "
                        "not being written on the rows no pair call reaches "
                        "and 'empty' cannot be told from 'not written'")
        self.assertEqual(sorted(blank & set(self.resolved)), [])


class TheSplit(unittest.TestCase):
    """The two halves are disjoint, and together they are the whole population.

    Carried here as `test_inc_dptr_sites.py` carries it, against the *column*
    rather than against `inc_dptr_sites`'s own map: the claim the issue makes
    is that the census can now be read this way, and that claim needs the two
    sides measured against each other rather than each against its own memory.
    """

    @classmethod
    def setUpClass(cls):
        cls.resolved = pair_pass()
        cls.census = census_roles()

    def test_the_two_halves_are_disjoint(self):
        seed = {a for a, r in self.census.items() if xrm.PAIR_SEED in r}
        inc = {a for a, r in self.census.items() if xrm.PAIR_INC in r}
        both = sorted(seed & inc)
        self.assertEqual(both, [],
                         f"{[f'0x{a:04X}' for a in both]} are a seed in one "
                         "call and an `inc DPTR` half in another, so a cell "
                         "reading `seed+inc-dptr` is a true statement about "
                         "one address and neither half's count is what it "
                         "claims to be -- the column says so rather than "
                         "quietly dropping a role, which is what the join in "
                         "`pair_role_of()` is for")
        self.assertTrue(seed, "no census row reads `seed` at all")

    def test_the_halves_close_on_pair_rows(self):
        # `PAIR_ROWS` is read out of the module that pins it, so this and the
        # tool's own `TheSplit` are the same measurement rather than two that
        # happen to agree. Asserted as the union rather than as
        # `seed + inc == 2 * inc`, so a population that closed by sharing an
        # address fails on the disjointness case above and not on a
        # coincidence of arithmetic.
        census_rows = {a for a, r in self.census.items() if r}
        self.assertEqual(len(census_rows), xrm.PAIR_ROWS,
                         f"{len(census_rows)} census rows carry a role and "
                         f"`xdata_register_map.PAIR_ROWS` is {xrm.PAIR_ROWS}; "
                         "the column and the population the pair pass reaches "
                         "have come apart")
        self.assertEqual(census_rows, set(self.resolved))

    def test_each_half_is_what_the_tool_calls_that_half(self):
        # Disjointness says the two sets do not touch; this says each one is
        # the *right* one. The census's `seed` rows are the addresses
        # `pair_pass()` reached as an `addr` and not as an `inc DPTR` half,
        # and its `inc-dptr` rows are the ones that are.
        tool_seed = {a for a, e in self.resolved.items()
                     if e["reached_as_seed"] and not e["directions"]}
        tool_inc = {a for a, e in self.resolved.items() if e["directions"]}
        census_seed = {a for a, r in self.census.items()
                       if r == {xrm.PAIR_SEED}}
        census_inc = {a for a, r in self.census.items()
                      if r == {xrm.PAIR_INC}}
        self.assertEqual(census_seed, tool_seed,
                         "the census's `seed` rows are not the addresses "
                         "`pair_pass()` reached only as an `addr`")
        self.assertEqual(census_inc, tool_inc,
                         "the census's `inc-dptr` rows are not the addresses "
                         "`pair_pass()` reached as an `inc DPTR` half")


class TheSiblingTool(unittest.TestCase):
    """The two committed artifacts about this population still agree.

    `xdata-inc-dptr-only.csv` is the 107 `inc-dptr` rows of the census, written
    by a different tool on a different run; the two are separate files about one
    population, and this is what stops them being edited apart.
    """

    @classmethod
    def setUpClass(cls):
        cls.census = census_roles()
        with open(ids.SITES_CSV, newline="") as f:
            cls.rows = list(csv.DictReader(f))

    def test_the_sites_table_is_the_columns_inc_dptr_ends_at(self):
        self.assertEqual(len(self.rows), len({a for a, r in self.census.items()
                                              if r == {xrm.PAIR_INC}}),
                         "the committed sites table and the census's "
                         "`inc-dptr` rows are different sizes")

    def test_the_sites_table_is_exactly_the_inc_dptr_rows(self):
        table = {int(r["addr"], 0) for r in self.rows}
        census = {a for a, r in self.census.items() if r == {xrm.PAIR_INC}}
        self.assertEqual(table, census,
                         f"only in the table: "
                         f"{[f'0x{a:04X}' for a in sorted(table - census)][:8]}"
                         f"; only in the census: "
                         f"{[f'0x{a:04X}' for a in sorted(census - table)][:8]}")

    def test_every_row_is_the_seed_the_tool_says_it_is(self):
        # The table's own `seed` cell points back at the low half. Reading it
        # against `pair_pass()` is the check that the two files are describing
        # the same pair rather than merely the same address number.
        resolved = pair_pass()
        wrong = [r["addr"] for r in self.rows
                 if resolved[int(r["addr"], 0)]["seed"]
                 != int(r["seed"], 0)]
        self.assertEqual(wrong, [],
                         f"{wrong[:8]}: the table's `seed` cell is not the "
                         "seed `pair_pass()` records for that address")

    def test_the_sibling_tool_still_reproduces_its_own_table(self):
        # `scan()` grew `pair_roles` and `absorb()` folds it across scopes,
        # and `inc_dptr_sites.census_by_addr()` reaches both through
        # `scan()`, so a regression in either would take this tool's
        # generation down as well as its own. The tripwire and the refusal
        # cases around it are `test_inc_dptr_sites.py`'s.
        proc = subprocess.run(
            [sys.executable, str(HERE / "inc_dptr_sites.py"),
             str(EC / "firmware" / "GMxMGxx_11.800"), "--check"],
            cwd=HERE, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
