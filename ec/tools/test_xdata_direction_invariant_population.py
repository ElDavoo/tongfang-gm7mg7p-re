#!/usr/bin/env python3
"""The direction invariant's population is measured, not restated (issue #1385).

Issue #1385 found `DIRECTION_INVARIANT["write_like"]` and `["write_like_addrs"]
interpolated into the corpus-wide direction invariant's pass line and compared
by nothing, so the line stated a population as a measurement that would read
identically if both figures were wrong. The remedy the issue offered was #849's
second one — derive the census side and assert it — and the calibration clause
was that a derived figure other than the pinned one would itself be a finding.

**What this suite holds is the derivation, not a figure.** The two counts move
with every seeded routine and every named register, so nothing here asserts
5,677 or 1,008; a suite that did would be the next `fb8be6ee` had to unpick.
What is asserted is the shape of the claim: that the check *reads* the derived
quantity in its predicate rather than only interpolating it into its message,
and that a census figure perturbed by one moves the line. The figures
themselves are the write-up's, beside the command that prints them.

**Why a perturbation and not an equality.** Both failure modes this guards
against are silent: a figure interpolated into a message reads as measured
whether or not anything computed it, and a `got` slot that interpolated the
constant it was checked against would be the same defect one level down. An
equality against the current tree cannot tell those from a working check,
because both pass. Moving a figure and requiring the line to go red is the only
thing here that fails when the binding is gone — which is why the harness is a
scratch copy rather than a value.

**The scratch copy resolves every path unchanged.** `EC_DIR` and `DECOMPILED`
are derived from `__file__`, so a copy *inside* `ec/tools/` reads the same tree
the committed file does and the committed file is never mutated. The copy is
removed in a `finally` whatever the assertion does.
"""
import ast
import csv
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
TOOL = HERE / "xdata_register_map.py"
# The scratch copy is a sibling of the tool rather than a temp file, and its
# name is not in `.gitignore` -- so a run killed between writing and cleaning
# up would leave something the next commit could pick up. Removing it on the
# way out of every path, including an exception, is the whole reason it is
# written where it is.
SCRATCH = HERE / "_scratch_population_probe.py"
sys.path.insert(0, str(HERE))


def drop_scratch():
    """Remove the scratch copy if a previous run left one behind."""
    SCRATCH.unlink(missing_ok=True)

WRITE_LIKE = "the two passes account for the same write-like population"
WIDTH = "the two address counts differ by exactly"


def run_self_test(path):
    """(exit code, [lines]) for `path --self-test`."""
    done = subprocess.run([sys.executable, str(path), "--self-test"],
                          capture_output=True, text=True)
    return done.returncode, done.stdout.splitlines() + done.stderr.splitlines()


def line_for(lines, needle):
    """The single self-test line whose text carries `needle`."""
    hits = [ln for ln in lines if needle in ln]
    return hits[0] if hits else None


def read_plus_write_column():
    """The committed `read+write` column, summed over the registers CSV.

    Read rather than typed, so a census that grows does not turn this into a
    figure this suite owns.
    """
    with open(HERE.parent / "annotations" / "xdata-registers.csv",
              newline="") as handle:
        return sum(int(row["read+write"])
                   for row in csv.DictReader(handle))


def write_direction_pair_sites():
    """Write-direction pair sites, measured by the sweep the tool runs.

    Read rather than typed: a routine seeded or an accessor annotated moves
    this, and a figure written into this suite would be one more thing a
    census pass edits.
    """
    sys.path.insert(0, str(HERE))
    import xdata_register_map as xrm
    funcs, by_file = xrm.load_index()
    pattern = xrm.occurrence_re(xrm.load_symbols())
    accessors = xrm.load_pair_accessors()
    sites = 0
    for out_file in sorted(by_file):
        text = xrm.strip_comments(
            (HERE.parent / "decompiled" / out_file).read_text())
        sites += sum(1 for _, d in xrm.pair_sites(text, accessors, pattern)
                     if d == "write")
    return sites


class Perturbation(unittest.TestCase):
    """A census figure moved by one must move the line that names it."""

    def setUp(self):
        drop_scratch()
        self.addCleanup(drop_scratch)

    def perturbed(self, old, new):
        """Run --self-test against a copy with `old` rewritten to `new`.

        The copy lives in `ec/tools/` so the paths `__file__` derives are the
        committed ones, and it is removed whatever happens next.
        """
        text = TOOL.read_text()
        self.assertIn(old, text, f"probe target {old!r} is not in the tool")
        drop_scratch()
        SCRATCH.write_text(text.replace(old, new, 1))
        try:
            code, lines = run_self_test(SCRATCH)
        finally:
            drop_scratch()
        return code, lines

    def test_committed_run_is_green(self):
        """The unperturbed case, so a red line below is the perturbation's."""
        code, lines = run_self_test(TOOL)
        self.assertEqual(code, 0, "\n".join(lines))
        self.assertIsNotNone(line_for(lines, WRITE_LIKE))
        self.assertIsNotNone(line_for(lines, WIDTH))

    def test_perturbing_the_census_side_moves_the_population_line(self):
        """Drop one census write, and the identity must notice.

        `+ e["buckets"]["read+write"]` is the census's half of the expected
        value, so removing it moves `expected` while the measured side stands
        still. A check whose `got` slot restated the constant would not see it.
        """
        code, lines = self.perturbed(
            'e["buckets"]["write"] + e["buckets"]["read+write"]', 'e["buckets"]["write"]')
        line = line_for(lines, WRITE_LIKE)
        self.assertIsNotNone(line, "the population line vanished:\n" + "\n".join(lines))
        self.assertIn("FAIL", line)
        self.assertEqual(code, 1)
        # Both sides named, expected first: the moved figure has to be the one
        # in the expected slot for this to be a comparison rather than a
        # recomputation agreeing with itself. The size of the gap is read off
        # the committed `read+write` column rather than written here, since
        # that column moves with every routine the census seeds.
        self.assertRegex(line, r"expected \d+, got \d+")
        expected = int(re.search(r"expected (\d+)", line).group(1))
        got = int(re.search(r"got (\d+)", line).group(1))
        self.assertEqual(got - expected, read_plus_write_column(),
                         "the gap is the `read+write` column this "
                         "perturbation removed from the expected side")

    def test_perturbing_the_measured_side_moves_the_population_line(self):
        """Halve what the sweep credits the walk, and the line must go red.

        A pair site names two bytes and `scan()` counts both, so the sweep
        credits two references per site. Crediting one is exactly the mistake
        the factor of two exists to catch, and it moves `got` while the census
        side stands still -- the disagreement between two code paths reading
        the same text, which is what the identity is for.
        """
        code, lines = self.perturbed("pair_refs[direction] += 2",
                                     "pair_refs[direction] += 1")
        line = line_for(lines, WRITE_LIKE)
        self.assertIsNotNone(line, "the population line vanished:\n" + "\n".join(lines))
        self.assertIn("FAIL", line)
        self.assertEqual(code, 1)
        expected = int(re.search(r"expected (\d+)", line).group(1))
        got = int(re.search(r"got (\d+)", line).group(1))
        # The shortfall is the write-direction sites, each of which the
        # perturbation stopped crediting a second time; that count is measured
        # off the committed census rather than written here.
        self.assertEqual(expected - got, write_direction_pair_sites(),
                         "the shortfall is the write-direction pair sites the "
                         "perturbation stopped crediting twice")


class TheWidthIsNotShaped(unittest.TestCase):
    """`len(shaped)` is one address wider than the write-like set, by cause.

    The tempting reading of "how many addresses carry a store" is `len(shaped)`,
    and it is wrong here: `shaped` accepts `*`-dereference stores that
    `store_target()` excludes for cause. The two differ by the dereference
    addresses, so a re-deriver who divides the gap has a site to look at rather
    than an off-by-one to shrug at.
    """

    def test_the_two_widths_differ_and_the_difference_is_the_deref_sites(self):
        import xdata_register_map as xrm
        funcs, by_file = xrm.load_index()
        symbols = xrm.load_symbols()
        func_names = {r["name"] for r in funcs.values()}
        shaped, census_side, _off, _sur, _eq, _eqw = xrm.direction_invariant(
            by_file, symbols, func_names)
        write_like = census_side["write_like_addrs"]
        self.assertNotEqual(len(shaped), len(write_like),
                            "the two sets are equal, so this suite's premise "
                            "no longer describes the tree and the difference "
                            "needs re-deriving")
        self.assertEqual(set(shaped) - write_like,
                         census_side["deref_addrs"] - write_like)


class TheBindingIsRead(unittest.TestCase):
    """The predicate reads the derived quantity; the message alone would not do.

    `check_doc_figure_pins.py` reads a figure's being written down and reports
    it unheld; the mirror of that is a figure that *is* written down and read
    only by the string that prints it. The two directions of the mistake are
    both silent, so this resolves the call the way the sibling checker resolves
    a subscript, and asserts the reading rather than any line number.
    """

    def source_tree(self):
        return ast.parse(TOOL.read_text(), filename=str(TOOL))

    def check_calls(self, tree):
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and getattr(node.func, "id", None) == "check"):
                yield node

    def test_the_population_check_reads_what_it_prints(self):
        """The line naming the write-like population derives it in scope."""
        tree = self.source_tree()
        targets = [c for c in self.check_calls(tree)
                   if WRITE_LIKE in ast.unparse(c.args[0])]
        self.assertEqual(len(targets), 1,
                         "expected exactly one check naming the population, "
                         f"found {len(targets)}")
        # The predicate is what has to move; the message is what misled.
        self.assertIn("write_like", ast.unparse(targets[0].args[1]))

    def test_no_module_level_figure_is_held_for_the_population(self):
        """The counts are derived per run, so no constant reintroduces them.

        This is the shape issue #1385's own remedy implies and `fb8be6ee`
        completed: a module-level dict whose keys are these two figures would
        be the hand-kept total the census stopped carrying, and the pass line
        would be interpolating it again.
        """
        held = set()
        for node in ast.walk(self.source_tree()):
            if not (isinstance(node, ast.Assign)
                    and isinstance(node.value, ast.Dict)):
                continue
            held.update(t.id for t in node.targets
                        if isinstance(t, ast.Name))
        self.assertNotIn("DIRECTION_INVARIANT", held,
                         "the census-side figures are derived again; a constant "
                         "holding them is what this issue removed")


if __name__ == "__main__":
    drop_scratch()
    unittest.main()
