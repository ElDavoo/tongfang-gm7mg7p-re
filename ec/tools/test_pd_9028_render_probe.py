#!/usr/bin/env python3
"""Cases for `pd_9028_render_probe.py`.

The tool's own `--self-test` carries the readings, and this drives it, so the
guard it checks is exercised by `tools/run-tests.sh` rather than only by a
human typing the flag. The Ghidra half (`--run`) needs the toolchain and is
still not in the runner; what is here needs neither Ghidra nor a project, so
the half that can be checked in CI is checked in CI.

What is added on top of the self-test is the same split
`test_c_asm_counterpart.py` makes: the self-test proves the CSV surgery works
on a fixture, and the cases below hold the properties the experiment rests on
against the *committed* files. The load-bearing one is that no arm can name a
committed annotation CSV as its output — the property that makes this a
counterfactual rather than an edit. A tool that dropped a correct hand-decoded
annotation to stabilise a number is what `xdata-register-map.md` §7.1's policy
already rejected, and `drop_row`'s own docstring calls the refusal "the guard
that matters most".

**No count of the tree is asserted anywhere in this file.** The arms are two
named rows and a baseline; asserting how many rows either CSV holds would be a
figure every merge touching an annotation has to edit, and it would prove
nothing about the probe. What is asserted is the claim and the relation: the
named keys resolve to exactly one committed row each, the arms differ from the
baseline in the one row they name, and the committed CSVs are byte-identical
after the arms have run.

Everything here reads committed files and writes under a temporary directory.
No Ghidra, no hardware, no Windows, no network.
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import pd_9028_render_probe as tool                                      # noqa: E402


def digest(path):
    """`path`'s bytes, so "this was not written" is checked and not assumed."""
    with open(path, "rb") as f:
        return f.read()


class TheSelfTest(unittest.TestCase):
    """The tool's own self-test, which is where the readings live."""

    def test_it_passes(self):
        # Its transcript goes to a buffer rather than to this suite's own
        # output: it is a dozen lines, and a reader running the suite would
        # otherwise have to find this suite's own result underneath them. The
        # exit code is the whole of the assertion.
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = tool.self_test()
        self.assertEqual(rc, 0, buf.getvalue()[-2000:])


class TheArmsNameOneRowEach(unittest.TestCase):
    """An arm that drops nothing still renders, and looks like the baseline.

    So the keys are held against the committed CSVs: each has to match exactly
    one row, or the experiment answers a question nobody asked.
    """

    def test_each_arm_key_matches_exactly_one_committed_row(self):
        for arm in ("drop-variable", "drop-function"):
            layer, key = tool.ARMS[arm]
            path = (tool.FUNCTIONS if layer == "functions"
                    else tool.VARIABLES)
            columns = (("scope", "addr") if layer == "functions"
                       else ("scope", "addr", "key"))
            header, rows = tool.read_csv(path)
            idx = [header.index(c) for c in columns]
            hits = [r for r in rows if tuple(r[i] for i in idx) == key]
            self.assertEqual(
                len(hits), 1,
                "the %s arm's key %r matches %d committed row(s) in %s, so the "
                "arm does not drop the one row it claims"
                % (arm, key, len(hits), os.path.relpath(path, tool.REPO)))

    def test_the_baseline_drops_nothing(self):
        # The baseline is the re-export the old account did not have, and it is
        # the only arm that can tell a row's effect from the export's own. An
        # arm that dropped something would stop being that.
        self.assertIsNone(tool.ARMS["baseline"])
        self.assertEqual(set(tool.ARMS),
                         {"baseline", "drop-variable", "drop-function"})


class TheCommittedCsvsAreNotTheOutput(unittest.TestCase):
    """The guard, held against the committed files rather than a fixture.

    `drop_row` refuses to write its output over its own input, and this is the
    level above it: the arm's output path is built under the scratch directory,
    and the layer an arm does not target is passed to Ghidra as the committed
    path — read-only. So no arm can name a committed CSV as its destination,
    which is what makes this a counterfactual instead of an edit.
    """

    def arms_over_committed_csvs(self, work):
        """Each arm's CSV pair, and the committed bytes taken around them."""
        before = {p: digest(p) for p in (tool.FUNCTIONS, tool.VARIABLES)}
        pairs = {arm: tool.arm_csvs(arm, work) for arm in tool.ARMS
                 if tool.ARMS[arm] is not None}
        return pairs, before, {p: digest(p) for p in (tool.FUNCTIONS,
                                                      tool.VARIABLES)}

    def test_no_arm_writes_a_committed_annotation_csv(self):
        # The layer an arm does *not* target is deliberately handed over as the
        # committed path -- read-only -- so the arm differs from the baseline in
        # exactly one row. What must never happen is the layer the arm targets
        # being written in place, so the assertion is on the file `drop_row`
        # produced, not on the pair.
        committed = {os.path.abspath(tool.FUNCTIONS),
                     os.path.abspath(tool.VARIABLES)}
        with tempfile.TemporaryDirectory() as tmp:
            pairs, _before, _after = self.arms_over_committed_csvs(tmp)
            for arm, (funcs, variables, dropped) in pairs.items():
                scratch = [p for p in (funcs, variables)
                           if os.path.abspath(p) not in committed]
                self.assertEqual(
                    len(scratch), 1,
                    "the %s arm has %d scratch CSVs, so it either wrote a "
                    "committed one or copied a layer it does not target"
                    % (arm, len(scratch)))
                # One row dropped, into a real file with content -- an arm whose
                # output is empty would make Ghidra's run fail rather than
                # silently annotate nothing.
                self.assertTrue(os.path.isfile(scratch[0]), scratch[0])
                self.assertEqual(dropped, 1,
                                 "the %s arm dropped %d row(s), not the one it "
                                 "names" % (arm, dropped))

    def test_an_arm_touches_only_the_layer_it_names(self):
        # The other layer is handed over as the committed path, so the arm
        # differs from the baseline in exactly the row it names and in nothing
        # else. Were this to copy both layers, a difference in the render would
        # not be attributable.
        with tempfile.TemporaryDirectory() as tmp:
            pairs, _before, _after = self.arms_over_committed_csvs(tmp)
            funcs, variables, _n = pairs["drop-variable"]
            self.assertEqual(funcs, tool.FUNCTIONS)
            self.assertNotEqual(variables, tool.VARIABLES)
            funcs, variables, _n = pairs["drop-function"]
            self.assertNotEqual(funcs, tool.FUNCTIONS)
            self.assertEqual(variables, tool.VARIABLES)

    def test_the_committed_csvs_are_byte_identical_afterwards(self):
        with tempfile.TemporaryDirectory() as tmp:
            _pairs, before, after = self.arms_over_committed_csvs(tmp)
            self.assertEqual(before, after,
                             "building an arm's scratch copy changed a committed "
                             "annotation CSV")


class TheWatchedFileIsTheOneUnderTest(unittest.TestCase):
    """What every arm is diffed against has to exist and be the named file.

    Otherwise all three arms would agree with each other and with a tree that
    has no `pd/7B14.c` in it, and the probe would report a fixed point it never
    measured.
    """

    def test_the_committed_watch_is_non_empty_and_annotated(self):
        text = tool.committed_watch()
        self.assertTrue(text.strip(), "the committed pd/7B14.c is empty")
        self.assertIn("stage_07c9_index_then_dispatch_on_flag_bits", text,
                      "the committed pd/7B14.c is not the annotated file the "
                      "arm table is read against")


if __name__ == "__main__":
    unittest.main()
