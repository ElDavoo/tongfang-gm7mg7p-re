#!/usr/bin/env python3
"""Offline checks for export_ownership.py: committed files only.

The tool decides which `.c` files are copies of one another, and its failure
mode is not a crash but a plausible wrong answer -- a class that merges two
routines that share a `return`, or splits a routine that was exported 42 ways
into a dozen classes that all still have to be read. The second is the exact
defect the pass exists to remove, so what is pinned here is every way the
containment rule is *allowed* to fire and not fire, one case per named rule,
each asserting the direction that a loosened rule would get backwards.

The refusals carry as much weight as the fixtures. `--check` and `--self-test`
are the two modes a reader trusts to describe the committed CSV, and a
refusal that quietly stopped refusing would let either of them answer for a
derivation nobody committed -- which is indistinguishable, from the output,
from the check working.
"""
import contextlib
import csv
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'export_ownership', HERE / 'export_ownership.py')
eo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eo)


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = eo.main(list(argv))
        except SystemExit as e:
            rc = e.code
    return rc, out.getvalue(), err.getvalue()


def fixture(stmts, names, program="bank0", addrs=None):
    """Inline index.csv-shaped rows and the body sets they describe.

    Each case reads as the shape it is about rather than as a diff against a
    stored file, and the address list is explicit where the case turns on which
    of two files wins the ownership tie-break.
    """
    addrs = addrs or [f"{0x8000 + 4 * i:04X}" for i in range(len(names))]
    rows = [{"out_file": f"{program}/{addrs[i]}.c", "program": program,
             "addr": addrs[i], "name": name, "order": i,
             "key": (program, int(addrs[i], 16))}
            for i, (name, st) in enumerate(zip(names, stmts))]
    bodies = {r["out_file"]: eo.body_of(st) for r, st in zip(rows, stmts)}
    return rows, bodies


class ContainmentRuleTests(unittest.TestCase):
    """The rule, one case per clause of the docstring."""

    def test_overlapping_pair_folds_into_the_larger_body(self):
        rows, bodies = fixture(["a; b; c; d; e;", "b; c;"], ["big", "small"])
        own = eo.ownership(rows, bodies, floor=1)
        self.assertEqual(own["bank0/8000.c"]["owner_out_file"], "bank0/8000.c")
        self.assertEqual(own["bank0/8004.c"]["owner_out_file"], "bank0/8000.c")
        self.assertEqual(own["bank0/8004.c"]["shared"], "yes")

    def test_genuinely_distinct_pair_does_not_fold(self):
        rows, bodies = fixture(["a; b; c;", "x; y; z;"], ["p", "q"])
        own = eo.ownership(rows, bodies)
        self.assertEqual([own[k]["shared"] for k in own], ["no", "no"])

    def test_containment_has_a_direction(self):
        # The one case a rule written as a symmetric set comparison gets
        # backwards. Folded the other way, the big body follows the fragment and
        # the whole routine leaves the census.
        rows, bodies = fixture(["a; b; c; d; e;", "b;"], ["big", "frag"])
        own = eo.ownership(rows, bodies, floor=1)
        self.assertEqual(own["bank0/8000.c"]["owner_out_file"], "bank0/8000.c")
        self.assertEqual(own["bank0/8004.c"]["owner_out_file"], "bank0/8000.c")

    def test_floor_keeps_a_short_body_out_of_comparison(self):
        rows, bodies = fixture(["a; b; c; d; e;", "b;"], ["big", "frag"])
        own = eo.ownership(rows, bodies)
        self.assertEqual(own["bank0/8004.c"]["owner_out_file"], "bank0/8004.c")
        self.assertEqual(own["bank0/8000.c"]["owner_out_file"], "bank0/8000.c")

    def test_empty_body_folds_into_nothing(self):
        # "No statements" is not evidence of overlap. Folding it into whatever
        # is nearby would drop a real export's references from the census.
        rows, bodies = fixture(["a; b; c; d; e;", ""], ["big", "empty"])
        own = eo.ownership(rows, bodies)
        self.assertEqual(own["bank0/8004.c"]["owner_out_file"], "bank0/8004.c")
        self.assertEqual(own["bank0/8004.c"]["body_lines"], 0)

    def test_cross_program_pair_never_folds(self):
        rows, bodies = fixture(["a; b; c; d; e;"], ["big"], program="bank0")
        rows2, bodies2 = fixture(["b; c;"], ["small"], program="bank1",
                                 addrs=["8004"])
        own = eo.ownership(rows + rows2, {**bodies, **bodies2}, floor=1)
        self.assertEqual(own["bank1/8004.c"]["owner_out_file"], "bank1/8004.c")

    def test_equal_bodies_are_each_their_own_owner_under_strict_containment(self):
        rows, bodies = fixture(["a; b; c;", "a; b; c;"], ["one", "two"],
                               addrs=["8004", "8000"])
        own = eo.ownership(rows, bodies)
        self.assertEqual(own["bank0/8000.c"]["shared"], "no")
        self.assertEqual(own["bank0/8004.c"]["shared"], "no")

    def test_fold_equal_collapses_to_the_lowest_address(self):
        rows, bodies = fixture(["a; b; c;", "a; b; c;"], ["one", "two"],
                               addrs=["8004", "8000"])
        own = eo.ownership(rows, bodies, fold_equal=True)
        self.assertEqual(own["bank0/8004.c"]["owner_out_file"], "bank0/8000.c")
        self.assertEqual(own["bank0/8004.c"]["shared"], "yes")
        self.assertEqual(own["bank0/8000.c"]["shared"], "no")

    def test_largest_body_owns_the_class_not_the_lowest_address(self):
        # The tie-break is only reached at equal size. A rule that picked the
        # lowest address unconditionally would hand this class to the fragment,
        # which sits at the lower address here on purpose.
        rows, bodies = fixture(["a; b;", "a; b; c; d; e;"], ["small", "big"],
                               addrs=["8000", "8004"])
        own = eo.ownership(rows, bodies, floor=1)
        self.assertEqual(own["bank0/8000.c"]["owner_out_file"], "bank0/8004.c")

    def test_containment_score_is_directed_not_jaccard(self):
        # Jaccard would score the fragment-in-big case 2/5 and refuse to fold
        # it, which is the whole 42-file class. The measure is how much of the
        # *smaller* body is accounted for, not how much the pair has in common.
        big, small = eo.body_of("a; b; c; d; e;"), eo.body_of("b; c;")
        self.assertAlmostEqual(eo.containment(small, big), 1.0)
        self.assertLess(len(small & big) / len(small | big), 0.9)

    def test_a_chained_member_is_visible_in_its_own_containment_score(self):
        # Thresholded containment does not compose, so a component can hold a
        # member the owner barely resembles. The score is the member's own
        # rather than the class's, so that is visible in the CSV instead of
        # hidden by the grouping. Bodies here need ten statements before 0.90
        # can absorb even one, which is why a three-line chain cannot show it.
        def stmts(*idx):
            return "; ".join(f"s{i}" for i in idx) + ";"

        # A is inside B, B is 0.90 inside C, and A is only 0.80 inside C: the
        # two missing statements are A's, so A reaches the owner through B.
        a = stmts(*range(10))                              # s0..s9
        b = stmts(*range(10), *(10 + i for i in range(10)))  # a, plus t0..t9
        c = stmts(*range(8), *(10 + i for i in range(10)), 20, 21, 22)
        rows, bodies = fixture([a, b, c], ["a", "b", "c"])
        self.assertGreaterEqual(eo.containment(eo.body_of(a), eo.body_of(b)),
                                eo.THRESHOLD)
        self.assertGreaterEqual(eo.containment(eo.body_of(b), eo.body_of(c)),
                                eo.THRESHOLD)
        self.assertLess(eo.containment(eo.body_of(a), eo.body_of(c)),
                        eo.THRESHOLD)
        recs = eo.ownership(rows, bodies, floor=1)
        self.assertEqual(recs["bank0/8000.c"]["owner_out_file"], "bank0/8008.c")
        self.assertLess(float(recs["bank0/8000.c"]["containment"]), eo.THRESHOLD)


class RefusalTests(unittest.TestCase):
    """A check that has quietly stopped rejecting looks like a check that works."""

    def test_check_refuses_a_threshold_it_was_not_committed_at(self):
        for mode in ("--check", "--self-test"):
            with self.subTest(mode=mode):
                rc, _, err = run(mode, "--threshold", "0.5")
                self.assertNotEqual(rc, 0)
                self.assertIn("--threshold", err)

    def test_check_refuses_fold_equal(self):
        for mode in ("--check", "--self-test"):
            with self.subTest(mode=mode):
                rc, _, err = run(mode, "--fold-equal")
                self.assertNotEqual(rc, 0)
                self.assertIn("--fold-equal", err)

    def test_the_refusal_says_where_to_look_instead(self):
        _, _, err = run("--check", "--fold-equal")
        self.assertIn("--map", err)
        self.assertIn(str(eo.OWNERSHIP_CSV), err)

    def test_the_committed_threshold_is_still_accepted(self):
        # The refusal is on the *value*, not on the flag: passing the committed
        # threshold explicitly is the same derivation and has to stay legal, or
        # the gate cannot pin the derivation it means to pin.
        with tempfile.TemporaryDirectory() as d:
            rc, _, err = run("--threshold", str(eo.THRESHOLD), "--map",
                             "--out", str(Path(d) / "ownership.csv"))
        self.assertEqual(rc, 0, err)


class CommittedTreeTests(unittest.TestCase):
    """The committed artifacts, re-derived rather than restated."""

    @classmethod
    def setUpClass(cls):
        cls.rows = eo.load_rows()
        cls.bodies = eo.load_bodies(cls.rows)
        cls.recs = eo.derive()
        cls.by_file = {r["out_file"]: r for r in cls.recs}

    def test_one_row_per_index_csv_row(self):
        self.assertEqual(len(self.recs), len(self.rows))
        self.assertEqual(len(self.by_file), len(self.rows))

    def test_every_owner_is_itself_a_row(self):
        owners = {r["owner_out_file"] for r in self.recs}
        self.assertTrue(owners <= set(self.by_file),
                        f"owner not in the map: {owners - set(self.by_file)}")

    def test_an_owner_is_never_a_non_owner(self):
        # A class has exactly one owner. Two would mean a row is skipped for a
        # file that is itself skipped, and its references would be lost.
        owners = {r["out_file"] for r in self.recs if r["shared"] == "no"}
        non_owners = {r["out_file"] for r in self.recs if r["shared"] == "yes"}
        self.assertFalse(owners & non_owners)

    def test_shared_flag_agrees_with_the_owner_column(self):
        for r in self.recs:
            self.assertEqual(r["shared"] == "no",
                             r["out_file"] == r["owner_out_file"], r)

    def test_the_42_file_class_is_owned_by_the_run_start(self):
        # The one figure the issue's own wording turns on, and the one whose
        # owner has to be bank1/8001.c: every `bank1:0x8001` citation in the
        # tree is only true if the run is attributed to the address that starts
        # it.
        members = [r for r in self.recs
                   if r["owner_out_file"] == "bank1/8001.c"]
        self.assertEqual(len(members), eo.OWNERSHIP_ORACLE["largest_class"])
        for r in members:
            self.assertEqual(r["program"], "bank1")

    def test_owners_never_cross_a_program(self):
        for r in self.recs:
            self.assertEqual(r["program"],
                             self.by_file[r["owner_out_file"]]["program"], r)

    def test_containment_scores_are_in_range(self):
        for r in self.recs:
            score = float(r["containment"])
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
            if r["shared"] == "no":
                self.assertEqual(score, 1.0, r)

    def test_the_body_floor_is_what_keeps_the_pass_a_detector(self):
        # Without it the one-statement fragments chain whole programs together.
        # This is the measurement that makes MIN_BODY_STMTS a decision rather
        # than a guess, and it is taken at THRESHOLD so it measures the same
        # question the docstring and xdata-export-ownership.md 3 answer.
        flood = max(len(m) for m in eo.classes_of(self.rows, self.bodies,
                                                 eo.THRESHOLD, False, 1).values())
        real = eo.OWNERSHIP_ORACLE["largest_class"]
        self.assertEqual(flood, eo.OWNERSHIP_ORACLE["flood_no_floor"])
        self.assertGreater(flood, 500)
        self.assertLessEqual(real, 42)

    def test_committed_csv_is_a_fresh_derivation(self):
        on_disk = eo.read_committed()
        self.assertIsNotNone(on_disk, f"{eo.OWNERSHIP_CSV} is missing")
        self.assertEqual(eo.diff(on_disk, self.recs), 0)

    def test_committed_csv_header_is_the_documented_one(self):
        with open(eo.OWNERSHIP_CSV, newline="") as f:
            self.assertEqual(next(csv.reader(f)), eo.COLUMNS)

    def test_map_round_trips_through_a_scratch_path(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "ownership.csv")
            rc, _, err = run("--map", "--fold-equal", "--out", path)
            self.assertEqual(rc, 0, err)
            with open(path, newline="") as f:
                written = list(csv.DictReader(f))
        self.assertEqual(len(written), len(self.rows))
        self.assertEqual(eo.diff(written, eo.derive(fold_equal=True)), 0)


if __name__ == "__main__":
    unittest.main()
