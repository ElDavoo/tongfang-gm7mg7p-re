#!/usr/bin/env python3
"""Does `export_ownership.py --self-test` name every pin its own check holds?

**The defect this stands in for.** Issue #1386: `check()` lines compared
against `OWNERSHIP_ORACLE` and `SHARE_ORACLE` and interpolated none of them, so
a `--self-test` line going red carried the measured figure in both slots and the
pinned figure nowhere. `ok  56 containment classes, 146 non-owner rows` was the
worst of them -- both numbers measured, neither pinned, and the pair the
census doc quotes as the tool's derivation. It is the shape issue #1363 fixed
in `xdata_register_map.py`, which is what makes this checkable rather than a
matter of taste: a reader turning a red line to a failing argument needs the
pinned figure and the measured one both on it, and a line holding only the
measured one cannot be turned into that argument at all.

**Why a perturbation and not a read of the source.** A pin in the message is the
property; a pin in the source is a substring that could match the key's *name*
rather than its value, which is the failure a substring sweep makes and the
reason `check_pin_message_names.py` tests the subscript expression. So each case
writes a **textually perturbed copy** of the committed source -- one dict
figure changed, not an in-memory mutation of an imported module -- and runs the
real `--self-test` over the real tree. The proof is the FAIL line a human would
see, not a claim that the source mentions something.

**The scratch copy, and why the paths are repointed.** `export_ownership.py`
derives `DECOMPILED`, `INDEX_CSV` and `OWNERSHIP_CSV` from `__file__` at import,
so a copy on its own would derive over nothing. The copy is loaded by path and
the three are then set to the committed tree, which is the real derivation over
the real `.c` files: a synthetic fixture would make every pin FAIL at once and
so could not say which check read which pin. The cost is one full derivation
per pin, and `tools/run-tests.sh`'s output is where the suite's cost shows up.

**The property is the shape, and the shape is split.** Each FAIL line is cut at
the `"(got "` every message now carries, and the pinned figure has to be on one
side of that cut and the measured on the other. Asserting a substring anywhere
on the line would pass on the pre-fix text for half these pins -- `56` and `146`
are both *on* that line, as measured figures -- which is why the split is the
assertion and not a membership test. `ThePreFixLine` is the control: it holds
the pre-#1386 label and runs it, so the harness cannot pass by construction.

**The pins are read from the module, never written here.** `PINS` names the
`(table, key)` pairs and nothing else; each case loads the committed tool and
takes the figure from its own oracle, so a re-pin does not make a suite fail for
a reason that has nothing to do with the message. That is why no figure appears
in this file at all -- a figure written here would be a second copy of the pin,
which is the same mistake this suite exists to catch.

**Offline, and not evidence about the EC.** Everything here reads committed
files: the tool's own source, `ec/decompiled/index.csv`, and the `.c` bodies it
derives from. No EC is opened, no register is read back, no laptop is reached.
The property is about a message a Python tool prints.
"""
import ast
import contextlib
import importlib.util
import io
import os
import re
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "export_ownership.py")
EC_DIR = os.path.dirname(HERE)

# The `(table, key)` pairs a `check()` in `export_ownership.py` compares against
# without naming, read off `check_pin_message_names.py`'s own sweep over the
# pre-fix source and fixed there by #1386. The list is of *pairs* and the
# figures are read from the module at run time; see the docstring for why.
#
# `largest_class` and `largest_class_owner` are absent because the sweep never
# reported them: their checks already named both, and `largest_class` is the one
# key read by two checks with only one of them unnamed.
PINS = (
    ("OWNERSHIP_ORACLE", "rows"),
    ("OWNERSHIP_ORACLE", "classes"),
    ("OWNERSHIP_ORACLE", "shared_rows"),
    ("OWNERSHIP_ORACLE", "bridged"),
    ("OWNERSHIP_ORACLE", "bridged_no_floor"),
    ("OWNERSHIP_ORACLE", "classes_no_floor"),
    ("OWNERSHIP_ORACLE", "flood_no_floor"),
    ("OWNERSHIP_ORACLE", "tiny_bodies"),
    ("SHARE_ORACLE", "classes"),
    ("SHARE_ORACLE", "shared_rows"),
    ("SHARE_ORACLE", "newly_read"),
)

# The cut every message carries after #1386, and the one the assertion is on.
GOT = "(got "


def committed_source():
    with open(TOOL, encoding="utf-8") as f:
        return f.read()


def load(source):
    """The tool as `source` says it is, with its derived paths on the real tree.

    The temporary directory closes before the module is used, which is safe and
    worth saying: `exec_module` compiles the source into the module object at
    import and nothing here reads `__file__` afterwards -- the three paths are
    the only things `__file__` was for, and they are set explicitly below.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "export_ownership.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(source)
        spec = importlib.util.spec_from_file_location("export_ownership", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    module.DECOMPILED = os.path.join(EC_DIR, "decompiled")
    module.INDEX_CSV = os.path.join(EC_DIR, "decompiled", "index.csv")
    module.OWNERSHIP_CSV = os.path.join(EC_DIR, "annotations",
                                        "xdata-export-ownership.csv")
    return module


def self_test(source):
    """(rc, stdout) from a scratch copy's own `--self-test`, in process."""
    module = load(source)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = module.main(["--self-test"])
    return rc, out.getvalue()


def fail_lines(stdout):
    """The check lines that went red, and not the `FAILURES ABOVE` trailer."""
    return [line for line in stdout.splitlines() if line.startswith("  FAIL  ")]


def figure_in(text, figure):
    """True when `figure` appears in `text` as a whole number.

    The boundaries are the point: these pins are single- and double-digit and
    `flood_no_floor`'s measured 562 sits next to `bridged_no_floor`'s 14 in the
    same `got` clause, so a bare `in` would credit a match inside another
    figure.
    """
    return re.search(r"(?<![\d.])" + re.escape(str(figure)) + r"(?![\d.])",
                     text) is not None


class ThePerturbation(unittest.TestCase):
    """One figure moved in the source; the FAIL line has to name both."""

    def test_each_unnamed_pin_is_named_expected_and_measured(self):
        committed = committed_source()
        for table, key in PINS:
            with self.subTest(pin=f"{table}[{key!r}]"):
                pinned = getattr(load(committed), table)[key]
                # The fragment is spelled with the figure the module already
                # holds, so a re-pin moves the perturbation with it and a
                # mismatch is a genuine disagreement rather than a stale
                # literal. The uniqueness check is the guard: a fragment that
                # matched nothing would perturb nothing and the case would pass
                # for the wrong reason, and one that matched twice would move a
                # figure this case did not mean to touch.
                fragment = f'"{key}": {pinned}'
                self.assertEqual(committed.count(fragment), 1,
                                 f"{fragment!r} is not unique in the source")
                moved = pinned + 1
                perturbed = committed.replace(fragment, f'"{key}": {moved}', 1)
                self.assertNotEqual(perturbed, committed,
                                    "the perturbation did not apply")

                rc, out = self_test(perturbed)
                self.assertEqual(rc, 1, out)
                fails = fail_lines(out)
                self.assertEqual(len(fails), 1,
                                 f"one pin moved, so one check may fail: {fails}")

                expected, cut, measured = fails[0].partition(GOT)
                self.assertTrue(cut,
                                f"no {GOT!r} clause, so the line cannot say which "
                                f"figure is pinned: {fails[0]!r}")
                self.assertTrue(measured, f"nothing after the cut: {fails[0]!r}")
                self.assertTrue(figure_in(expected, moved),
                                f"{table}[{key!r}] moved to {moved}, and the "
                                f"expected slot does not name it: {fails[0]!r}")
                self.assertTrue(figure_in(measured, pinned),
                                f"{table}[{key!r}] is pinned at {pinned}, and the "
                                f"measured slot does not carry it: {fails[0]!r}")


class ThePreFixLine(unittest.TestCase):
    """The control, so the case above cannot pass by construction.

    The label is transcribed from the committed source before #1386 rather than
    paraphrased -- a paraphrase that happened to name a figure would be a
    control passing for the wrong reason -- and the replacement is asserted to
    have applied, which is what makes it a transcription that is checked rather
    than one that is trusted.
    """

    PRE_FIX_LABEL = (
        '    check(f"{len(real)} containment classes, {len(shared)} non-owner '
        'rows",\n'
    )

    def test_the_pre_fix_line_names_the_pinned_figure_in_neither_slot(self):
        source = committed_source()
        classes = load(source).OWNERSHIP_ORACLE["classes"]
        shared = load(source).OWNERSHIP_ORACLE["shared_rows"]

        fixed_label = (
            '    check(f"{OWNERSHIP_ORACLE[\'classes\']} containment classes, "\n'
            '          f"{OWNERSHIP_ORACLE[\'shared_rows\']} non-owner rows "\n'
            '          f"(got {len(real)}/{len(shared)})",\n'
        )
        self.assertIn(fixed_label, source, "the fixed label no longer matches")
        # A pin is moved as well as the message restored: the pre-fix label on
        # its own still passes, because the tree agrees with the pin, and the
        # defect this stands in for is only visible on the line a moved pin
        # produces. That is the whole point -- a reader cannot diagnose the move
        # from the text either way round, but only one of the two is a FAIL.
        moved = source.replace(f'"classes": {classes}',
                               f'"classes": {classes + 1}', 1)
        pre_fix = moved.replace(fixed_label, self.PRE_FIX_LABEL, 1)
        self.assertNotEqual(pre_fix, moved, "the control did not apply")

        rc, out = self_test(pre_fix)
        self.assertEqual(rc, 1, out)
        fails = fail_lines(out)
        self.assertEqual(len(fails), 1, fails)
        line = fails[0]
        expected, cut, measured = line.partition(GOT)
        # Both figures are *on* this line and neither is named: which is exactly
        # why the case above splits at the cut rather than searching the whole
        # line, where both would match as measured figures. The moved pin is on
        # no line at all.
        self.assertEqual(cut, "", f"the pre-fix line has a got clause: {line!r}")
        self.assertEqual(measured, "")
        self.assertTrue(figure_in(expected, classes))
        self.assertTrue(figure_in(expected, shared))
        self.assertFalse(figure_in(line, classes + 1),
                         f"the moved pin is named after all: {line!r}")


class TheScope(unittest.TestCase):
    """The two directions a fixed list of pins can go stale in."""

    def test_the_committed_tree_is_green(self):
        # Without this the other cases would pass on a tool whose checks were
        # failing for some other reason, and the FAIL line a perturbation
        # produced would be one of several.
        rc, out = self_test(committed_source())
        self.assertEqual(rc, 0, out)

    def test_every_pin_listed_is_read_by_a_check(self):
        # The other direction: a pin whose check stopped comparing against it
        # is a case that would go on passing. Read off the parse rather than
        # asserted as a count, so adding a check does not make this fail.
        #
        # The walk is spelled out here rather than borrowed from
        # `check_pin_message_names.py`: this suite is a second reading of the
        # same property, and a second reading that followed the tool would
        # agree with it by construction.
        source = committed_source()
        tree = ast.parse(source)
        read = set()
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "check" and len(node.args) >= 2):
                continue
            for sub in ast.walk(node.args[1]):
                if (isinstance(sub, ast.Subscript)
                        and isinstance(sub.value, ast.Name)
                        and isinstance(sub.slice, ast.Constant)):
                    read.add((sub.value.id, sub.slice.value))
        for pin in PINS:
            self.assertIn(pin, read,
                          f"{pin} is listed here but no check() predicate "
                          f"compares against it any more")


if __name__ == "__main__":
    unittest.main()