#!/usr/bin/env python3
"""Offline checks for export_ownership_verdicts.py: committed files only.

The tool's whole job is to keep a judgement attached to every row of a
population, and its failure mode is not a crash but a ledger that reads as
complete. A verdict that was never made, a verdict recorded against an owner
that has since changed, a token that is not in the closed vocabulary: each of
those leaves the CSV looking like a record of a review that did not happen.
So what is pinned here is the two directions separately -- a member with no
verdict and a verdict for a member the population no longer holds are
different mistakes and want different fixes -- plus the refusals that make the
first of them impossible to pass by accident.

The population is built from a scratch map rather than read from the committed
one, so each case reads as the shape it is about and the committed tree is not
what decides whether the assertions hold.
"""
import contextlib
import csv
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    'export_ownership_verdicts', HERE / 'export_ownership_verdicts.py')
eov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eov)


def run(*argv):
    """Run the tool the way a shell would, and report what the shell would see.

    `SystemExit("msg")` prints `msg` on stderr and exits 1; catching it and
    returning only `code` would drop the message and leave a refusal looking
    like a silent failure, which is the opposite of what these cases are for.
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = eov.main(list(argv))
        except SystemExit as e:
            if isinstance(e.code, str):
                print(e.code, file=sys.stderr)
                rc = 1
            else:
                rc = e.code
    return rc, out.getvalue(), err.getvalue()


def row(out_file, owner, lines, owner_lines, containment="1.00",
        shared="yes"):
    """One map row in the shape the population predicate reads."""
    return {"out_file": out_file, "program": out_file.split("/")[0],
            "addr": out_file.split("/")[1].split(".")[0], "body_lines": lines,
            "owner_out_file": owner, "owner_addr": "0000",
            "owner_name": "owner_name", "shared": shared,
            "containment": containment, "owner_body_lines": owner_lines,
            "member_share": f"{lines / owner_lines:.2f}"}


def write(path, records):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    return str(path)


class PopulationTests(unittest.TestCase):
    """Which rows the ledger has to cover, derived rather than listed."""

    def setUp(self):
        self.rows = [
            row("bank0/8000.c", "bank0/8000.c", 22, 22, shared="no"),
            # Twice the size and an exact score: in the population.
            row("bank0/8004.c", "bank0/8000.c", 4, 22),
            # Twice the size but only thresholded: not on trial at the exact
            # score the population names.
            row("bank0/8008.c", "bank0/8000.c", 4, 22, containment="0.90"),
            # An exact score against an owner barely twice its size: below the
            # multiple, so not on trial.
            row("bank0/800C.c", "bank0/8000.c", 6, 10),
            # Its own owner: a non-owner row is the population's subject and an
            # owner row is not in it whatever its sizes say.
            row("bank1/9000.c", "bank1/9000.c", 40, 40, shared="no"),
        ]

    def test_the_population_is_both_clauses(self):
        self.assertEqual([r["out_file"] for r in eov.population(self.rows)],
                         ["bank0/8004.c"])

    def test_the_population_ignores_a_row_the_map_does_not_mark_shared(self):
        # A row that owns itself has a share of 1.00 against an owner that may
        # be much larger, and putting it on trial would ask for a verdict on a
        # fold that is not happening.
        rows = self.rows + [row("bank1/9004.c", "bank1/9000.c", 3, 40,
                                shared="no")]
        self.assertNotIn("bank1/9004.c",
                         [r["out_file"] for r in eov.population(rows)])


class DisagreementTests(unittest.TestCase):
    """The two directions, and the refusals that keep them honest."""

    # Two rows on trial, and one non-owner the population's exact-score clause
    # leaves out so the stale direction has something to fire on.
    MAP = [row("bank0/8000.c", "bank0/8000.c", 22, 22, shared="no"),
           row("bank0/8004.c", "bank0/8000.c", 4, 22),
           row("bank0/8008.c", "bank0/8000.c", 3, 22),
           row("bank0/800C.c", "bank0/8000.c", 4, 22, containment="0.90")]

    def ledger(self, *rows):
        return list(rows)

    def ok(self, out_file, verdict="fragment"):
        return {"out_file": out_file, "owner_out_file": "bank0/8000.c",
                "verdict": verdict, "basis": "ec/decompiled/bank0/8000.c"}

    def test_a_complete_ledger_disagrees_with_nothing(self):
        verdicts = self.ledger(self.ok("bank0/8004.c"),
                               self.ok("bank0/8008.c"))
        self.assertEqual(eov.disagree(self.MAP, verdicts), [])

    def test_a_member_with_no_verdict_fails(self):
        verdicts = self.ledger(self.ok("bank0/8008.c", "undecided"))
        bad = eov.disagree(self.MAP, verdicts)
        self.assertEqual([k for k, _ in bad], ["no-verdict"])
        self.assertIn("bank0/8004.c", bad[0][1])

    def test_a_verdict_for_a_row_outside_the_population_fails_apart(self):
        # The other direction, and it must not be reported as the first: a
        # reader sent to look for a missing member when the ledger is the stale
        # one is reading the wrong file.
        verdicts = self.ledger(self.ok("bank0/8004.c"),
                               self.ok("bank0/8008.c"),
                               self.ok("bank0/800C.c"))
        bad = eov.disagree(self.MAP, verdicts)
        self.assertEqual([k for k, _ in bad], ["not-in-population"])
        self.assertIn("not in the population", bad[0][1])

    def test_a_verdict_naming_a_file_the_map_has_is_also_stale(self):
        verdicts = self.ledger(self.ok("bank0/8004.c"),
                               self.ok("bank0/8008.c"),
                               self.ok("bank9/9999.c"))
        kinds = [k for k, _ in eov.disagree(self.MAP, verdicts)]
        self.assertEqual(kinds, ["not-in-map"])

    def test_an_unknown_verdict_token_is_refused_not_defaulted(self):
        # Treating it as `undecided` would turn a typo into a claim that
        # somebody looked at the two files and could not tell.
        verdicts = self.ledger(self.ok("bank0/8004.c", "probably-fine"),
                               self.ok("bank0/8008.c"))
        self.assertEqual([k for k, _ in eov.disagree(self.MAP, verdicts)],
                         ["unknown-verdict"])

    def test_a_verdict_against_a_different_owner_is_a_disagreement(self):
        # A class that has re-formed says nothing about the verdict recorded
        # for the old one, so the row has to be read again rather than
        # inherited.
        verdicts = self.ledger(self.ok("bank0/8004.c"),
                               self.ok("bank0/8008.c"))
        verdicts[0]["owner_out_file"] = "bank0/8100.c"
        self.assertEqual([k for k, _ in eov.disagree(self.MAP, verdicts)],
                         ["owner-moved"])

    def test_a_verdict_with_no_basis_is_a_disagreement(self):
        verdicts = self.ledger(self.ok("bank0/8004.c"),
                               self.ok("bank0/8008.c"))
        verdicts[0]["basis"] = "   "
        self.assertEqual([k for k, _ in eov.disagree(self.MAP, verdicts)],
                         ["no-basis"])

    def test_two_rows_for_one_member_is_a_disagreement(self):
        # Which verdict counts would otherwise be whichever row comes last,
        # and the order of a CSV means nothing -- so the file could carry both
        # readings and still check clean.
        verdicts = self.ledger(self.ok("bank0/8004.c"),
                               self.ok("bank0/8008.c"),
                               self.ok("bank0/8004.c", "re-export"))
        kinds = [k for k, _ in eov.disagree(self.MAP, verdicts)]
        self.assertEqual(kinds, ["duplicate-verdict"])

    def test_undecided_rows_are_counted_rather_than_dropped(self):
        # A population of undecided rows has not been worked through, and a
        # tally that omits them is a tally that reads as a clean sweep.
        verdicts = self.ledger(self.ok("bank0/8004.c", "undecided"),
                               self.ok("bank0/8008.c"))
        counts = eov.tally(verdicts)
        self.assertEqual(counts["undecided"], 1)
        self.assertEqual(sum(counts.values()), len(verdicts))
        self.assertEqual(set(counts) | set(eov.VERDICTS), set(eov.VERDICTS))


class MalformedLedgerTests(unittest.TestCase):
    """A row that reads back wrong has to be refused, not silently shortened."""

    def test_a_comma_inside_a_value_is_refused(self):
        # `csv.DictReader` puts the extra fields under a spare key rather than
        # raising, so the row keeps a member and a verdict and loses the end of
        # its citation -- and every check downstream still passes.
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "v.csv"
            path.write_text("out_file,owner_out_file,verdict,basis\n"
                            "bank0/8004.c,bank0/8000.c,fragment,"
                            "a basis, with an unquoted comma\n")
            with self.assertRaises(SystemExit) as caught:
                eov.load_verdicts(str(path))
        self.assertIn("quoting", str(caught.exception))

    def test_a_header_this_tool_does_not_own_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "v.csv"
            path.write_text("out_file,owner,verdict,basis\n")
            with self.assertRaises(SystemExit) as caught:
                eov.load_verdicts(str(path))
        self.assertIn("header", str(caught.exception))


class CommittedTreeTests(unittest.TestCase):
    """The committed map and the committed ledger, held to each other."""

    @classmethod
    def setUpClass(cls):
        cls.records = eov.load_map()
        cls.verdicts = eov.load_verdicts()

    def test_the_ledger_and_the_population_agree_in_both_directions(self):
        self.assertEqual(eov.disagree(self.records, self.verdicts), [])

    def test_every_member_of_the_population_carries_a_verdict(self):
        # The claim, not the census. Asserting the set match rather than a
        # number is what lets a tree that grows a row redden here for the real
        # reason instead of for a hard-coded figure that has stopped agreeing
        # with the map.
        population = {r["out_file"] for r in eov.population(self.records)}
        self.assertTrue(population)
        self.assertEqual({v["out_file"] for v in self.verdicts}, population)

    def test_every_verdict_is_in_the_vocabulary_and_has_a_basis(self):
        for v in self.verdicts:
            self.assertIn(v["verdict"], eov.VERDICTS, v)
            self.assertTrue(v["basis"].strip(), v)

    def test_the_ledger_says_the_negative_out_loud(self):
        # The whole point of the ledger: the rows whose fold the map asserts
        # and the text does not support are recorded as such rather than left
        # for a reader to infer from a containment score. Counted, not fixed,
        # so a tree that resolves one of them does not redden for the wrong
        # reason -- but not vacuous either, or the negative would be a claim
        # with nothing behind it.
        self.assertGreater(eov.tally(self.verdicts)["fragment"], 0)

    def test_check_mode_passes_on_the_committed_tree(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out, err = run("--check",
                               "--map", write(Path(d) / "m.csv", self.records),
                               "--verdicts",
                               write(Path(d) / "v.csv", self.verdicts))
        self.assertEqual(rc, 0, err)
        self.assertIn("fragment", out)

    def test_the_table_covers_the_whole_population(self):
        rc, out, err = run("--table")
        self.assertEqual(rc, 0, err)
        body = [ln for ln in out.splitlines() if ln.startswith("| `")]
        self.assertEqual(len(body), len(eov.population(self.records)))
        for r in eov.population(self.records):
            self.assertIn(f"`{r['out_file']}`", out)

    def test_the_table_refuses_to_render_a_ledger_that_does_not_cover_it(self):
        # A table of a population the ledger does not answer for reads as a
        # complete record, which is exactly the thing this work exists to stop.
        with tempfile.TemporaryDirectory() as d:
            rc, _, err = run("--table",
                             "--verdicts", write(Path(d) / "v.csv",
                                                 self.short_ledger()))
        self.assertNotEqual(rc, 0)
        self.assertIn("refusing to render", err)

    def short_ledger(self):
        return [v for v in self.verdicts
                if v["out_file"] != "common/3BDD.c"]


if __name__ == "__main__":
    unittest.main()