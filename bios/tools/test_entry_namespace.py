#!/usr/bin/env python3
"""`isPlaceholderName()` has one definition, and no BIOS row sits in the
namespace it reserves.

Stands in for the reconciliation of issue #626, which deleted
`ExportDecompile.java`'s private copy of `isPlaceholderName()` and renamed the
two `bios/annotations/ghidra-functions.csv` rows that took the bare name
`entry`. Each assertion below is a claim rather than a census: none of them is a
number that a rename, a new annotation or the BIOS re-export has to go and edit.

**Why the first one is here at all, when `build_ec_decompile.py --self-test`
already holds the predicate.** That hold reads *one* Java file, and its regex
requires the literal `public static`. It compared `TongFang.java` against the
Python transcription and was structurally unable to notice a second definition
existed — so while `ExportDecompile.java` carried a `private static` twin, the
self-test stayed green, both docstrings claimed one definition, and two
committed CSVs disagreed about which rows were annotated. The issue's "a change
to either copy is a red test" was wrong of the drifted copy, and this is what
closes the hole.

**The refusals are what make it worth anything.** A scanner that cannot open the
scripts directory finds no definitions, and "no second copy" is exactly what a
green run is supposed to say — so an unreadable tree and a clean one would be
indistinguishable. Every file that cannot be read is reported beside the
definitions rather than folded into them, and each refusal is driven on a
fixture below.

Reads committed text. Nothing here runs Ghidra, so the BIOS half of #626 — the
re-export that would move `annotated` in `bios/ghidra/index.csv` — is outside
what this file can speak to, and it does not claim to.
"""

import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "ec", "tools"))

import grade_name_basis  # noqa: E402  (the path insert above is what makes this work)

SCRIPTS = os.path.join(REPO, "ghidra", "scripts")
BIOS_ANNOTATIONS = os.path.join(REPO, "bios", "annotations", "ghidra-functions.csv")

# A *definition*, matched on the method's own signature line and not on the
# name alone: a call site or a `{@link}` mentions `isPlaceholderName` too, and
# counting those would make this a count of mentions. The modifiers are
# captured rather than required, because "is the one definition `public`" is an
# assertion below and not a premise of the scan.
DEFINITION = re.compile(
    r"^[ \t]*(?P<mods>(?:(?:public|private|protected|static|final)[ \t]+)+)"
    r"boolean[ \t]+isPlaceholderName[ \t]*\(",
    re.M)
# The Java call whose presence is the drift: the drifted copy tested the
# `entry` PREFIX where the canonical tests the exact word. Scanned as a literal
# rather than as a parsed call, so a second copy cannot slip past by being
# spelled across lines -- and a comment naming the old form to explain the
# change goes red here too, which is a reword rather than a hole.
DRIFTED_TEST = 'startsWith("entry")'


def definitions(paths):
    """`(file, mods, line)` for every definition found, and the files refused.

    Two returns rather than one because the refusal is not a special case of a
    definition: a script directory this cannot list has no definitions *as far
    as this run knows*, which is a different answer from "there is one", and
    conflating them is how a green run would come to mean nothing.
    """
    found, refused = [], []
    for path in paths:
        try:
            with open(path, errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            refused.append("%s (%s)" % (os.path.basename(path), exc.strerror))
            continue
        for match in DEFINITION.finditer(text):
            found.append((os.path.basename(path),
                          match.group("mods").split(),
                          text[:match.start()].count("\n") + 1))
    return found, refused


def java_scripts(scripts_dir=SCRIPTS):
    """The `.java` paths under `scripts_dir`, or None when it cannot be listed.

    None and not [] for the same reason `definitions` reports refusals: an empty
    list would assert that the exporters have no sources at all, which is a
    different and much larger claim than the one this file makes.
    """
    try:
        names = sorted(os.listdir(scripts_dir))
    except OSError:
        return None
    return [os.path.join(scripts_dir, n) for n in names if n.endswith(".java")]


class OneDefinition(unittest.TestCase):
    """The predicate is defined once, publicly, in the file that documents it."""

    def test_the_committed_tree_defines_it_once_and_publicly(self):
        paths = java_scripts()
        self.assertIsNotNone(paths, "%s cannot be listed" % SCRIPTS)
        found, refused = definitions(paths)
        self.assertEqual(refused, [], "script(s) not readable: %s" % refused)
        self.assertEqual(
            [(f, mods) for f, mods, _ in found],
            [("TongFang.java", ["public", "static"])],
            "expected one public static definition in TongFang.java and no "
            "other; found %s" % [(f, l) for f, _, l in found])

    def test_a_second_definition_is_reported_with_where_it_is(self):
        # The regression this file exists for. A `private static` twin is the
        # shape #602 shipped, and it is the shape a reader skimming the
        # canonical file would not see.
        found, _ = definitions(self.fixture({
            "TongFang.java": "    public static boolean isPlaceholderName(String n) {\n"
                             "        return n.startsWith(\"FUN_\");\n    }\n",
            "ExportDecompile.java":
                "    private static boolean isPlaceholderName(String n) {\n"
                "        return n.startsWith(\"entry\");\n    }\n",
        }))
        self.assertEqual([(f, mods, line) for f, mods, line in found],
                         [("TongFang.java", ["public", "static"], 1),
                          ("ExportDecompile.java", ["private", "static"], 1)])

    def test_a_call_site_is_not_a_definition(self):
        # The reason the scan is on a signature line. Both exporters call the
        # predicate, and counting a call would make the tree look drifted the
        # moment either of them was fixed.
        found, _ = definitions(self.fixture({
            "TongFang.java": "    public static boolean isPlaceholderName(String n) {\n"
                             "        return n.startsWith(\"FUN_\");\n    }\n",
            "ExportListing.java": "    String a = TongFang.isPlaceholderName(name);\n",
        }))
        self.assertEqual([f for f, _, _ in found], ["TongFang.java"])

    def test_a_script_it_cannot_read_is_reported_not_counted_as_clean(self):
        paths = self.fixture({
            "TongFang.java": "    public static boolean isPlaceholderName(String n) {\n"
                             "        return n.startsWith(\"FUN_\");\n    }\n",
        })
        found, refused = definitions(paths + [os.path.join(HERE, "no_such_script.java")])
        self.assertEqual([f for f, _, _ in found], ["TongFang.java"])
        self.assertEqual(len(refused), 1, "a file that cannot be read is a refusal")
        self.assertIn("no_such_script.java", refused[0])

    def fixture(self, sources):
        """`sources` written to a scratch directory, and the paths to them.

        Fixtures rather than the committed scripts for the same reason the
        refusal cases need them: a scan that only ever sees a clean tree cannot
        be shown to catch a dirty one.
        """
        scratch = tempfile.mkdtemp(prefix="entry_namespace")
        self.addCleanup(shutil.rmtree, scratch, True)
        return [self.write(os.path.join(scratch, n), body)
                for n, body in sources.items()]

    def write(self, path, body):
        with open(path, "w") as handle:
            handle.write(body)
        return path


class DriftedFormIsGone(unittest.TestCase):
    """The prefix form is not in the exporters, in any file."""

    def test_no_script_tests_the_entry_prefix(self):
        paths = java_scripts()
        self.assertIsNotNone(paths, "%s cannot be listed" % SCRIPTS)
        hits, refused = [], []
        for path in paths:
            try:
                with open(path, errors="replace") as handle:
                    text = handle.read()
            except OSError as exc:
                refused.append(os.path.basename(path))
                continue
            if DRIFTED_TEST in text:
                hits.append(os.path.basename(path))
        self.assertEqual(refused, [], "script(s) not readable: %s" % refused)
        self.assertEqual(hits, [],
                         "%s tests the `entry` prefix where the canonical "
                         "tests the word; every exporter must share one "
                         "definition" % hits)


class BiosNamespaceIsClean(unittest.TestCase):
    """No BIOS annotation row takes a name Ghidra could have produced itself."""

    def test_no_committed_bios_row_is_in_the_reserved_namespace(self):
        rows = grade_name_basis.read_csv(BIOS_ANNOTATIONS)
        self.assertEqual(grade_name_basis.reserved_prefix_problems(rows), [],
                         "a renamed row is the fix; see "
                         "docs/findings/entry-namespace-two-copies.md")

    def test_the_scan_still_answers_on_a_row_that_would_fail(self):
        # The property is asserted, not the emptiness, so the check above is
        # not a tautology over an empty scan. This is the shape #626 removed:
        # the row resolves, the comment is honest, and the predicate matches the
        # name anyway -- which is why the scan, not a reader, is what holds it.
        row = {"scope": "Setup", "addr": "0x000004B0", "name": "entry"}
        problems = grade_name_basis.reserved_prefix_problems([row])
        self.assertEqual(len(problems), 1)
        self.assertIn("Setup", problems[0])
        self.assertEqual(
            grade_name_basis.reserved_prefix_problems(
                [dict(row, name="module_entry_call_two_helpers_with_both_arguments")]),
            [])


if __name__ == "__main__":
    sys.exit(unittest.main())