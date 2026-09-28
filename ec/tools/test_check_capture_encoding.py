#!/usr/bin/env python3
"""Offline checks for check_capture_encoding.py: one case per problem branch.

The tool's whole product is its exit code. `report()` returns the problems it
found and `main()` turns that into the status, so the failure mode that
matters is the one where `problems` comes back empty every time: the tables
still print, the `ok:` line still prints, and the corpus the `utf-8` decision
rests on looks re-derivable while nothing re-derives it. #748 said this tool
is not a check that cannot fail, and said it having driven `report()` by
hand. A sentence in a merge body is not a case, and this is the case.

So the three problems `report()` can append are held separately -- a BOM, a
capture the declared reader refuses, and two reads that disagree -- each over
a tree built here, each asserted to be named by the path it was found at. The
clean half is held too, and it is the half that does the work: three cases
that a tool reporting every file would also pass are not evidence of a
checker, and a temp tree with a good capture beside a broken one is what says
this one is sharp.

**The fixtures are built in a temp directory and must never be committed.**
`ec/tools/testdata/` and `evidence/ec-watch/` are the two `ROOTS` the committed
run walks, so a BOM'd or latin-1 capture checked in beside the real ones
would turn the committed-corpus case red by construction, and a broken capture
in the tree is precisely the thing only a temp tree is allowed to hold.

No count of the corpus is asserted anywhere. A figure of the tree is a value
every merge that adds a capture has to edit; what is asserted instead are the
relations the `utf-8` decision rests on -- every committed capture decodes,
none carries a BOM, and every capture carrying a high byte comes out of the
declared reader agreeing with the locale-default one.

Offline throughout, and calibrated: these cases read committed files and
files they wrote themselves. No EC, no laptop, no Windows box was reached, and
nothing here is evidence about register behaviour.
"""
import contextlib
import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "check_capture_encoding.py")
spec = importlib.util.spec_from_file_location("check_capture_encoding", TOOL)
cce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cce)

# A capture in the committed `ts,addr,old,new` shape, and the three broken
# ones. Built as bytes because the bytes are what is under test: `bytes([...])`
# says which byte is on disk, where an escape buried in a longer literal is
# something a reader has to count, and the third fixture has to be a valid
# utf-8 string rather than a byte string to be the fixture it is.
CLEAN = b"ts,addr,old,new\n2026-01-01T12:00:00.000+01:00,0x0400,1,2\n"
BOM = bytes([0xEF, 0xBB, 0xBF]) + CLEAN
# 0xE9 is a utf-8 lead byte and never a utf-8 byte on its own, so nothing
# decodes this file and the declared reader refuses it outright.
LONE_E9 = (b"ts,addr,old,new\n2026-01-01T12:00:00.000+01:00,0x0400,1,"
           + bytes([0xE9]) + b"\n")
# The one that separates the third branch from the second: it *does* decode,
# so the declared reader takes it, and it is only the locale-default read that
# cannot. The label is the tool's own PROBE, because that is the character the
# whole check is about.
HIGH = "ts,addr,old,new\n2026-01-01T12:00:00.000+01:00,0x0400,1,§3 block 2\n".encode()

# The closing of the writer section, asserted absent and present by the
# argument a caller passed rather than by the module constant.
WRITER_ROWS = "landed:"

# A row of the per-file table, anchored on the `yes`/`NO` the walk ends every
# row with. The summary line and the writer rows cannot match it: the summary
# opens with a number and a comma, and a writer row carries a class name where
# the marks column is.
ROW = re.compile(
    r"^(?P<path>\S+)\s+(?P<bytes>\d+)\s+(?P<bom>yes|-)\s+(?P<hi>yes|-)\s+"
    r"(?:(?P<marks>\d+)\s+(?P<changes>\d+)|--\s+--)\s+(?P<agrees>yes|NO)\s*$")

SUMMARY = re.compile(r"^(?P<n>\d+) capture\(s\), (?P<high>\d+) with a high byte, "
                     r"(?P<bom>\d+) with a BOM;")

# The self-report the write-up leans on: on a utf-8 runner the two reads are
# the same read, and the tool says so rather than letting the trivially-`yes`
# `agrees` column pass for evidence.
NOTE = "note: this runner's default is already"

# The environment that stops the two reads being the same read, for the child
# that has to reach the third branch without patching anything. Asserted on
# its own terms in `TheDisagreementBranch` rather than assumed to take effect.
C_LOCALE = dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0",
                PYTHONCOERCECLOCALE="0")

# What the tool prints when a locale-default read and a declared read could
# not both succeed. The counts beside it are deliberately not matched: when the
# locale read is the one that raised, `walk_captures()` has set both to `None`
# and the message renders as `(None against None)`, which is a wart worth its
# own issue and a string worth freezing in neither.
DISAGREE = ": the declared read and the locale-default read disagree"


def run(*argv):
    """(exit code, the whole report) for one in-process `main()` call."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = cce.main(list(argv))
    return rc, out.getvalue()


def problems_in(text):
    """The messages `main()` printed under its own `N problem(s):` heading."""
    _, heading, block = text.partition(" problem(s):\n")
    if not heading:
        return []
    return [line[2:] for line in block.splitlines() if line.startswith("  ")]


def rows_in(text):
    """The per-file rows of a report, as dicts.

    An empty parse raises, because an empty parse is indistinguishable from a
    run that walked nothing: the table would print its header and no rows
    under it, and every case built on the count would read that as a clean
    corpus. Same reason the sibling's `docstring_surface()` raises.
    """
    rows = [m.groupdict() for m in (ROW.match(l) for l in text.splitlines()) if m]
    if not rows:
        raise AssertionError("the per-file table parsed as no rows")
    return rows


def summary_in(text):
    """The one `N capture(s), H with a high byte, B with a BOM` line."""
    found = [m.groupdict() for m in
             (SUMMARY.match(l) for l in text.splitlines()) if m]
    if len(found) != 1:
        raise AssertionError(f"expected one summary line, found {len(found)}")
    return {k: int(v) for k, v in found[0].items()}


def on_utf8_runner():
    """Whether this interpreter's default read *is* the declared one."""
    return cce._preferred_encoding().lower().replace("_", "-") == cce.DECLARED


def child(argv, env=None):
    """One run of the tool as a process, for the status a consumer sees."""
    return subprocess.run([sys.executable, TOOL] + list(argv),
                          capture_output=True, text=True, env=env)


class TempTree(unittest.TestCase):
    """A capture tree of this case's own, cleaned up with it."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name

    def write(self, name, raw):
        """One capture, by bytes, and the path it landed at."""
        path = os.path.join(self.root, name)
        with open(path, "wb") as f:
            f.write(raw)
        return path


class TheCommittedCorpus(unittest.TestCase):
    """The real tree, and the relations the `utf-8` declaration rests on.

    §1 of the write-up and §6 both quote a run of this: every committed
    capture decodes, none carries a BOM, and the ones carrying high bytes come
    out of the declared reader as they came out of the old one. Those are
    asserted as relations between the table and itself, never as a count --
    the next capture a human commits moves every figure here and none of them
    is a defect.
    """

    @classmethod
    def setUpClass(cls):
        cls.rc, cls.text = run()
        cls.rows = rows_in(cls.text)
        cls.summary = summary_in(cls.text)

    def test_the_committed_corpus_yields_no_problems(self):
        self.assertEqual(self.rc, 0, problems_in(self.text))
        self.assertEqual(problems_in(self.text), [])
        self.assertIn("ok: every committed capture", self.text)

    def test_the_table_decomposes_the_summary(self):
        # The three figures the summary prints, each taken apart of the rows it
        # counted. A walk that found nothing cannot agree with a summary that
        # says it found something, and one that found a file no summary counted
        # is a table that has drifted from the run that wrote it.
        derived = {
            "n": len(self.rows),
            "high": sum(r["hi"] == "yes" for r in self.rows),
            "bom": sum(r["bom"] == "yes" for r in self.rows),
        }
        self.assertEqual(self.summary, derived)

    def test_no_committed_capture_carries_a_bom(self):
        # This zero is asserted, unlike every other figure here, because it is
        # stable by construction: a committed capture carrying one makes the
        # tool exit 1, so it cannot arrive without the tree going red
        # elsewhere first. §1's table and §3's argument both rest on it.
        self.assertEqual([r["path"] for r in self.rows if r["bom"] == "yes"], [])

    def test_every_high_byte_capture_agrees_between_the_two_reads(self):
        # The load-bearing result, stated as a relation so that a corpus which
        # grew an ASCII-only capture cannot turn it red. A row with a high byte
        # that came out of the declared reader disagreeing with the old one is
        # exactly the file the declaration was not allowed to change.
        disagreeing = [r["path"] for r in self.rows
                       if r["hi"] == "yes" and r["agrees"] != "yes"]
        self.assertEqual(disagreeing, [])

    def test_the_corpus_does_carry_high_byte_captures(self):
        # Otherwise the case above is satisfied by a corpus with nothing in it,
        # which is the "checker that passes by checking nothing" failure the
        # sibling suite's docstring opens on.
        self.assertGreater(sum(r["hi"] == "yes" for r in self.rows), 0)

    def test_a_committed_capture_is_named_by_its_repo_relative_path(self):
        # The other half of what `_shown()` is for: `--root` gets the path it
        # was given, and a run over the committed corpora gets what it has
        # always gotten. An absolute path here is a changed default run, and
        # the default run is what the write-up tells a reader to reproduce.
        for row in self.rows:
            self.assertFalse(os.path.isabs(row["path"]), row["path"])
            self.assertNotIn(os.pardir, row["path"].split(os.sep), row["path"])
        self.assertTrue(any(r["path"].startswith("ec/tools/testdata/")
                            for r in self.rows), self.rows[0]["path"])
        self.assertTrue(any(r["path"].startswith("evidence/ec-watch/")
                            for r in self.rows), "one of the two ROOTS is missing")

    def test_a_utf8_runner_says_the_two_reads_are_the_same_read(self):
        # The write-up's own caveat -- that the agreement column is weak
        # evidence on a utf-8 box -- is a line the tool prints, and a line
        # nobody reads is a caveat that does not travel. Which direction this
        # is asserted in is a fact about the machine, not a skip: the case
        # holds the note as a function of the thing it reports, and the other
        # direction is held in `TheDisagreementBranch`.
        if on_utf8_runner():
            self.assertIn(NOTE, self.text)
        else:
            self.assertNotIn(NOTE, self.text)


class TheFailPath(TempTree):
    """Each corpus problem, named by the path it was found at."""

    def assert_only(self, expected):
        """One problem, and it is `expected`, with exit 1."""
        rc, text = run("--root", self.root)
        self.assertEqual(problems_in(text), [expected])
        self.assertEqual(rc, 1, text)
        self.assertIn("1 problem(s):", text)

    def test_a_bom_is_reported_by_path(self):
        path = self.write("bom.csv", BOM)
        self.assert_only(f"{path} carries a BOM; the format is utf-8 with no BOM")

    def test_a_capture_no_utf8_reader_takes_is_reported_by_path(self):
        path = self.write("latin1.csv", LONE_E9)
        self.assert_only(
            f"{path} is not utf-8-decodable, so the declared reader refuses "
            f"it; a capture is defined to be utf-8")

    def test_two_broken_captures_give_one_problem_each(self):
        # The issue's first item, and the sharpness of the two above: a tool
        # that reported every file in the tree would satisfy either one of them
        # on its own. A good capture sits in this tree too, and the count is
        # one per *broken* file -- so a run that named the clean one is red
        # here and green nowhere.
        bom = self.write("bom.csv", BOM)
        latin1 = self.write("latin1.csv", LONE_E9)
        self.write("clean.csv", CLEAN)
        high = self.write("high.csv", HIGH)
        rc, text = run("--root", self.root)
        found = problems_in(text)
        self.assertEqual(rc, 1)
        self.assertEqual(len(found), 2, found)
        self.assertTrue(any(p.startswith(bom) for p in found), found)
        self.assertTrue(any(p.startswith(latin1) for p in found), found)
        for quiet in (os.path.join(self.root, "clean.csv"), high):
            self.assertFalse(any(quiet in p for p in found), found)
        self.assertIn("2 problem(s):", text)

    def test_the_problem_names_the_path_the_run_was_pointed_at(self):
        # `_shown()` rather than an unconditional `relpath`: a temp tree has a
        # perfectly good name, and `../../../../../tmp/...` is a report nobody
        # can paste into an editor. The sibling suite holds the same clause
        # for the checker it sits beside.
        path = self.write("bom.csv", BOM)
        rc, text = run("--root", self.root)
        problem, = problems_in(text)
        self.assertTrue(problem.startswith(path + " "), problem)
        self.assertNotIn(os.pardir, problem.split(" ")[0].split(os.sep))

    def test_the_process_status_is_1(self):
        # What a consumer observes. In-process, `main()` returns a number
        # nothing then turns into a status, and the sibling's stated reason
        # for running its checker as a subprocess is the same one. `--quiet`
        # because the report's own table prints a `§`, which a non-utf-8 child
        # could not write to a pipe -- the problems it is here for do not
        # carry one.
        self.write("bom.csv", BOM)
        done = child(["--root", self.root, "--quiet"])
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("carries a BOM", done.stdout)
        self.assertIn("1 problem(s):", done.stdout)


class TheDisagreementBranch(TempTree):
    """The third problem, which a utf-8 runner cannot reach on its own.

    On a utf-8 machine the declared read and the locale-default read are the
    same read, so nothing can disagree -- the tool says so in its own output
    and the branch is unreachable by construction here. It is reachable two
    ways below: with the locale handed in, which is what actually exercises
    the branch, and by a child process under a C locale, which reaches it
    without anything patched.

    The `(None against None)` beside the disagreement is not asserted. When
    the locale read is the one that raised, `walk_captures()` has set both
    counts to `None` and the message renders those; freezing that string would
    lock in a cosmetic wart. Whether the locale-default comparison is worth
    keeping at all is its own question, and this is not the place to answer it.
    """

    def test_a_decodable_capture_the_locale_cannot_read_is_reported(self):
        path = self.write("high.csv", HIGH)
        out = io.StringIO()
        with mock.patch.object(cce, "_preferred_encoding", lambda: "ascii"):
            with contextlib.redirect_stdout(out):
                problems = cce.report(list(cce.walk_captures([self.root])),
                                      cce.WRITERS)
        self.assertEqual([p for p in problems if p.startswith(path)],
                         [f"{path}{DISAGREE} (None against None), so the "
                          f"declaration changed what this file grades as"])

    def test_the_same_capture_under_the_real_locale_is_silent(self):
        # The control, and the reason this is a branch about the codec rather
        # than about the fixture: the same bytes, the same run, no patch, and
        # no problem. Without it a case that reported a disagreement for any
        # capture carrying a high byte would also be green.
        self.write("high.csv", HIGH)
        rc, text = run("--root", self.root)
        self.assertEqual(problems_in(text), [])
        self.assertEqual(rc, 0, text)

    def test_a_runner_whose_locale_differs_prints_no_note(self):
        # The other direction of the self-report, and the one that makes the
        # note a claim rather than a decoration: a runner whose default is not
        # the declared codec has two genuinely different reads, and the caveat
        # about the agreement column being weak evidence does not apply to it.
        self.write("clean.csv", CLEAN)
        out = io.StringIO()
        with mock.patch.object(cce, "_preferred_encoding", lambda: "ascii"):
            with contextlib.redirect_stdout(out):
                cce.report(list(cce.walk_captures([self.root])), ())
        self.assertNotIn(NOTE, out.getvalue())

    def test_a_c_locale_child_reaches_the_same_branch(self):
        # Nothing patched, so this is the branch reached by the tool as it is
        # actually run. The environment is asserted first and on its own terms,
        # so a failure here names the environment rather than the branch: if
        # that `env` ever stops taking effect on some interpreter, this is the
        # case to drop and the in-process twin above is what holds the branch
        # regardless.
        probe = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util, sys\n"
             "s = importlib.util.spec_from_file_location('c', sys.argv[1])\n"
             "m = importlib.util.module_from_spec(s)\n"
             "s.loader.exec_module(m)\n"
             "print(m._preferred_encoding())\n", TOOL],
            capture_output=True, text=True, env=C_LOCALE)
        self.assertEqual(probe.returncode, 0, probe.stderr)
        self.assertNotEqual(probe.stdout.strip().lower().replace("_", "-"),
                            cce.DECLARED,
                            f"the C locale did not take effect: the child's "
                            f"default read is {probe.stdout.strip()!r}")
        path = self.write("high.csv", HIGH)
        done = child(["--root", self.root, "--quiet"], env=C_LOCALE)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn(f"{path}{DISAGREE}", done.stdout)


class TheWriterArgument(TempTree):
    """`report()` reads the writers it is handed, rather than the constant.

    `report(captures, writers)` takes both corpora as arguments and then
    iterated the module-level `WRITERS`, so the argument was dead: no caller
    could see any effect from passing it, and a case asserting only that the
    writer half ran would have been green against a `report()` that ignored
    what it was given. The first case here is red on the tree before that line
    reads the argument, which is what makes the fix evidence rather than a
    claim about it.

    The second case is the sharpness the first needs: an empty list and a
    one-element slice of the same table have to come out different, so "no
    writer rows" cannot also be what a `report()` printing no writer rows at
    all would give.
    """

    def setUp(self):
        super().setUp()
        self.write("clean.csv", CLEAN)

    def report_with(self, writers):
        """(problems, the report) for one `report()` over this case's tree."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            problems = cce.report(list(cce.walk_captures([self.root])), writers)
        return problems, out.getvalue()

    def test_no_writer_rows_for_an_empty_writer_list(self):
        problems, text = self.report_with(())
        self.assertEqual(problems, [])
        self.assertNotIn(WRITER_ROWS, text)
        # The corpus half still ran, which is what says the two arguments are
        # read independently: a `report()` that took an empty `writers` and
        # quietly skipped the rest of itself would satisfy the two lines above.
        self.assertIn("1 capture(s)", text)

    def test_the_writer_rows_are_the_ones_the_argument_names(self):
        one = cce.WRITERS[:1]
        problems, text = self.report_with(one)
        self.assertEqual(problems, [])
        self.assertEqual(text.count(WRITER_ROWS), 1, text)
        # By path and not by class name: two of the five writers are a
        # `CsvSink`, so the class name is not what distinguishes a row the
        # argument asked for from one it did not.
        self.assertIn(one[0][0], text)
        for path, _cls in cce.WRITERS[1:]:
            self.assertNotIn(path, text)


if __name__ == "__main__":
    unittest.main()
