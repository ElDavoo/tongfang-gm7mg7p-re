#!/usr/bin/env python3
"""Offline checks for check_probe_csv_encoding.py: one case per problem branch.

The tool's product is its exit code. `report()` returns the problems it found
and `main()` turns that into the status, so the failure mode that matters is
the one where `problems` comes back empty every time: the tables still print,
the `ok:` line still prints, and every site looks declared while nothing is
checking. A sentence in a write-up is not a case, and this is the case.

So each problem is held separately over a tree built here and each asserted to
be named by the path it was found at:

  * the corpus half's three -- a BOM, a capture the declared reader refuses,
    and two reads that disagree;
  * the declaration half's four -- a call matching no anchor at all, a call
    that matched but carries no `encoding=`, a call that declares some *other*
    codec (the failure `0751-capture-encoding.md` §3 argued against, which a
    keyword-name-only check would pass), and a site whose file could not be
    read at all, which is a hole in the coverage rather than a pass.

The disagreement branch is unreachable on a utf-8 interpreter by construction,
because there the declared read and the locale-default read are the same read.
It is reached the same way the sibling reaches its own: with the locale handed
in, and by a child process under a C locale, which reaches it with nothing
patched. Both are held here, and the environment is asserted first and on its
own terms so a failure names the environment rather than the branch.

**The fixtures are built in a temp directory and must never be committed.**
`evidence/battery-traces/` and `evidence/ec-watch/` are the two `ROOTS` the
committed run walks, so a BOM'd or latin-1 capture checked in beside the real
ones would turn the committed-corpus case red by construction, and a broken
capture in the tree is precisely the thing only a temp tree is allowed to
hold. The declaration fixtures are copies of the real tools with one keyword
removed, for the same reason: the committed copy is the evidence.

No count of the corpus is asserted anywhere. A figure of the tree is a value
every merge that adds a capture has to edit; what is asserted instead are the
relations the `utf-8` decision rests on -- every committed capture decodes,
none carries a BOM, and every capture carrying a high byte comes out of the
declared reader agreeing with the locale-default one.

Offline throughout, and calibrated: these cases read committed files and files
they wrote themselves. No EC, no laptop and no Windows box was reached, and
nothing here is evidence about register behaviour or about what a stock
Windows interpreter would write.
"""
import ast
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
TOOL = os.path.join(HERE, "check_probe_csv_encoding.py")
REPO = os.path.join(HERE, os.pardir, os.pardir)
spec = importlib.util.spec_from_file_location("check_probe_csv_encoding", TOOL)
cpe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cpe)

# A capture in the `ts,phase,...` shape `battery_trace.py` writes, and the
# three broken versions of it. Built as bytes because the bytes are what is
# under test: `bytes([...])` says which byte is on disk, where an escape
# buried in a longer literal is something a reader has to count, and the third
# fixture has to be a valid utf-8 string rather than a byte string to be the
# fixture it is.
CLEAN = b"ts,phase,ac,charging\n2026-01-01T12:00:00+01:00,baseline,1,1\n"
BOM = bytes([0xEF, 0xBB, 0xBF]) + CLEAN
# 0xE9 is a utf-8 lead byte and never a utf-8 byte on its own, so nothing
# decodes this file and the declared reader refuses it outright.
LONE_E9 = (b"ts,phase,ac,charging\n2026-01-01T12:00:00+01:00,base"
           + bytes([0xE9]) + b"line,1,1\n")
# The one that separates the third branch from the second: it *does* decode,
# so the declared reader takes it, and it is only the locale-default read that
# cannot. The label is a `§` phase, which is the character this whole question
# is about -- `args.phase` is operator-supplied and lands in column 1.
HIGH = ("ts,phase,ac,charging\n"
        "2026-01-01T12:00:00+01:00,§3,1,1\n").encode()

# A row of the per-file table, anchored on the two columns the walk ends every
# row with. The summary line and the declaration rows cannot match it: the
# summary opens with a number and a comma, and a declaration row's third
# column is `writer`/`reader` where the shape column is.
ROW = re.compile(
    r"^(?P<path>\S+)\s+(?P<shape>\S+)\s+(?P<bytes>\d+)\s+(?P<bom>yes|-)\s+"
    r"(?P<hi>yes|-)\s+(?P<decodes>yes|NO)\s+(?P<agrees>yes|NO)\s*$")

SUMMARY = re.compile(r"^(?P<n>\d+) capture\(s\), (?P<high>\d+) with a high byte, "
                     r"(?P<bom>\d+) with a BOM;")

# The self-report the write-up leans on: on a utf-8 runner the two reads are
# the same read, and the tool says so rather than letting the trivially-`yes`
# `agrees` column pass for evidence.
NOTE = "note: this runner's default is already"

# The environment that stops the two reads being the same read, for the child
# that has to reach the third branch without patching anything.
C_LOCALE = dict(os.environ, LC_ALL="C", LANG="C", PYTHONUTF8="0",
                PYTHONCOERCECLOCALE="0")

# The two halves' headings, so a case can say which half it means rather than
# matching on a phrase that appears in both.
CORPUS_HEADING = "== the committed corpus, read two ways =="
DECLARATION_HEADING = "== every probe site that touches a capture =="

# The two spellings the declaration half has to be made to lose, one per role.
# They differ because the writers pass `encoding=` beside `newline=` and the
# readers pass it alone, so a single pattern would strip the writers and miss
# every reader -- which would leave the reader case red for the wrong reason.
WRITER_STRIP = (', newline="", encoding="utf-8"', ', newline=""')
READER_STRIP = ('read_text(encoding="utf-8")', 'read_text()')

# The suites the table draws its readers from, and the module-level names each
# one holds a capture path in. A `read_text()` whose receiver is built from one
# of these is reading a capture and belongs in `DECLARATIONS`; one whose
# receiver is anything else is reading a source file and deliberately does not.
#
# Named by the constant rather than by its value so the classification survives
# the path being moved, and named as a set rather than a count so that a suite
# gaining a capture reader -- or a fourth source read -- is a line edited here
# rather than a figure retyped in prose. `test_a_source_read_is_not_in_the_table`
# holds the split; `test_every_capture_reader_is_in_the_table` holds that
# nothing reading a capture has been left out of it.
CAPTURE_HOLDERS = {
    "windows/tools/test_battery_trace.py": ("TRACES",),
    "windows/tools/test_charge_target_test.py": (),
    "windows/tools/test_ctgp_dben_probe.py": (),
}
SUITES = tuple(CAPTURE_HOLDERS)


def read_text_receivers(path):
    """`{receiver rendering: [declared codec or None]}` for a suite's reads.

    Every `read_text()` in the file, keyed by what it is called on rather than
    by where it is, because the question this exists to answer -- is this
    reading a capture or a source file -- is a property of the receiver. A
    receiver naming a module-level capture path (`TRACES / name`) is a
    capture; anything else is a source file.
    """
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    found = {}
    for call in ast.walk(tree):
        if not (isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "read_text"):
            continue
        keywords = {k.arg: ast.unparse(k.value).strip("'\"")
                    for k in call.keywords if isinstance(k, ast.keyword)}
        found.setdefault(ast.unparse(call.func), []).append(
            keywords.get("encoding"))
    return found


def run(*argv):
    """(exit code, the whole report) for one in-process `main()` call."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = cpe.main(list(argv))
    return rc, out.getvalue()


def problems_in(text):
    """The messages `main()` printed under its own `N problem(s):` heading."""
    _, heading, block = text.partition(" problem(s):\n")
    if not heading:
        return []
    return [line[2:] for line in block.splitlines() if line.startswith("  ")]


def rows_in(text):
    """The per-file rows of the corpus half, as dicts.

    An empty parse raises, because an empty parse is indistinguishable from a
    run that walked nothing: the table would print its header and no rows under
    it. Same reason the sibling's `rows_in()` raises.
    """
    head = text.index(CORPUS_HEADING)
    tail = text.index(DECLARATION_HEADING)
    rows = [m.groupdict() for m in
            (ROW.match(l) for l in text[head:tail].splitlines()) if m]
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
    return cpe._preferred_encoding().lower().replace("_", "-") == cpe.DECLARED


def child(*argv, env=None):
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

    def test_every_committed_capture_decodes_as_the_declared_codec(self):
        # The strong claim on a utf-8 runner, where the two reads are the same
        # read and `agrees` is trivially yes for everything.
        refused = [r["path"] for r in self.rows if r["decodes"] != "yes"]
        self.assertEqual(refused, [])

    def test_no_committed_capture_carries_a_bom(self):
        # This zero is asserted, unlike every other figure here, because it is
        # stable by construction: a committed capture carrying one makes the
        # tool exit 1, so it cannot arrive without the tree going red
        # elsewhere first. §1's table and §3's argument both rest on it.
        self.assertEqual([r["path"] for r in self.rows if r["bom"] == "yes"], [])

    def test_every_high_byte_capture_agrees_between_the_two_reads(self):
        # Stated as a relation so that a corpus which grew an ASCII-only
        # capture cannot turn it red. A row with a high byte that came out of
        # the declared reader disagreeing with the old one is exactly the file
        # the declaration was not allowed to change.
        disagreeing = [r["path"] for r in self.rows
                       if r["hi"] == "yes" and r["agrees"] != "yes"]
        self.assertEqual(disagreeing, [])

    def test_the_walk_found_rows_in_both_roots(self):
        # The non-vacuity guard for this corpus, and it is deliberately not
        # the sibling's. That suite can assert its corpus carries high-byte
        # captures; this one cannot, because on this tree it does not: every
        # committed capture in both roots is pure ASCII. So the case above is
        # satisfied vacuously *by the corpus itself* and the branch it guards
        # is held by the fixtures in `TheFailPath` and by the C-locale child in
        # `TheDisagreementBranch` -- not by anything committed. What is
        # asserted here is the narrower thing that would still be false for a
        # checker walking nothing: both roots contributed, and every row has
        # the shape the header claims.
        for root in ("evidence/battery-traces/", "evidence/ec-watch/"):
            self.assertTrue(any(r["path"].startswith(root) for r in self.rows),
                            f"{root} contributed nothing")
        self.assertTrue(all(r["shape"] != "?" for r in self.rows),
                        [r["path"] for r in self.rows if r["shape"] == "?"])

    def test_a_committed_capture_is_named_by_its_repo_relative_path(self):
        # The other half of what `_shown()` is for: `--root` gets the path it
        # was given, and a run over the committed corpora gets what it has
        # always gotten. An absolute path here is a changed default run, and
        # the default run is what the write-up tells a reader to reproduce.
        for row in self.rows:
            self.assertFalse(os.path.isabs(row["path"]), row["path"])
            self.assertNotIn(os.pardir, row["path"].split(os.sep), row["path"])
        for root in ("evidence/battery-traces/", "evidence/ec-watch/"):
            self.assertTrue(any(r["path"].startswith(root) for r in self.rows),
                            f"{root} is not in the walk")

    def test_the_shape_is_read_off_the_header_and_not_the_filename(self):
        # `2026-09-21-0522-follow.csv` says nothing about what is in the file.
        # The two shapes this check exists over are both present, which is what
        # makes the walk a population rather than one directory's contents; and
        # the `#`-annotated capture, whose header is on row 1, still gets its
        # shape rather than the annotation's first field.
        shapes = {r["path"]: r["shape"] for r in self.rows}
        self.assertIn("phase", shapes.values())
        self.assertIn("addr", shapes.values())
        annotated = shapes.get("evidence/battery-traces/2026-09-17-limit-pair.csv")
        self.assertEqual(annotated, "phase", shapes)

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
        # The sharpness of the two above: a tool that reported every file in
        # the tree would satisfy either one of them on its own. A good capture
        # sits in this tree too, and the count is one per *broken* file -- so a
        # run that named the clean one is red here and green nowhere.
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
        _, text = run("--root", self.root)
        problem, = problems_in(text)
        self.assertTrue(problem.startswith(path + " "), problem)
        self.assertNotIn(os.pardir, problem.split(" ")[0].split(os.sep))

    def test_the_process_status_is_1(self):
        # What a consumer observes. In-process, `main()` returns a number
        # nothing then turns into a status, and the sibling's stated reason for
        # running its checker as a subprocess is the same one.
        self.write("bom.csv", BOM)
        done = child("--root", self.root, "--quiet")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("carries a BOM", done.stdout)
        self.assertIn("1 problem(s):", done.stdout)

    def test_a_clean_tree_is_silent_and_exits_zero(self):
        # The clean half, which is the half that does the work: three cases a
        # tool reporting every file would also pass are not evidence of a
        # checker.
        self.write("clean.csv", CLEAN)
        self.write("high.csv", HIGH)
        rc, text = run("--root", self.root)
        self.assertEqual(problems_in(text), [])
        self.assertEqual(rc, 0, text)
        self.assertIn("ok: every committed capture", text)


class TheDisagreementBranch(TempTree):
    """The third corpus problem, which a utf-8 runner cannot reach on its own.

    On a utf-8 machine the declared read and the locale-default read are the
    same read, so nothing can disagree -- the tool says so in its own output
    and the branch is unreachable by construction here. It is reachable two
    ways below: with the locale handed in, which is what actually exercises the
    branch, and by a child process under a C locale, which reaches it without
    anything patched.
    """

    def test_a_decodable_capture_the_locale_cannot_read_is_reported(self):
        path = self.write("high.csv", HIGH)
        out = io.StringIO()
        with mock.patch.object(cpe, "_preferred_encoding", lambda: "ascii"):
            with contextlib.redirect_stdout(out):
                problems = cpe.report(list(cpe.walk_captures([self.root])))
        matched = [p for p in problems if p.startswith(path)]
        self.assertEqual(len(matched), 1, problems)
        self.assertIn("the declared read and the locale-default read disagree",
                      matched[0])

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
        with mock.patch.object(cpe, "_preferred_encoding", lambda: "ascii"):
            with contextlib.redirect_stdout(out):
                cpe.report(list(cpe.walk_captures([self.root])))
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
                            cpe.DECLARED,
                            f"the C locale did not take effect: the child's "
                            f"default read is {probe.stdout.strip()!r}")
        path = self.write("high.csv", HIGH)
        done = child("--root", self.root, "--quiet", env=C_LOCALE)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn(path, done.stdout)
        self.assertIn("the declared read and the locale-default read disagree",
                      done.stdout)


class TheDeclarationHalf(unittest.TestCase):
    """Every way the site table can stop describing the tree, held separately.

    The corpus half's branches are all about bytes; these three are about the
    table that says where to look for them, and they are the ones that make the
    `ok:` line mean something. A table whose anchor no longer matches anything,
    a call that matched but declares no codec, and a call that declares a
    different one are three different failures and the last is the one a
    keyword-name check would wave through.
    """

    def copy_tool(self, rel, edit):
        """A copy of a committed source file in a temp tree, and its root.

        `edit` is one (find, replace) pair. The declaration cases remove one
        keyword and nothing else, so the copy is still the file the checker is
        being pointed at -- a copy mangled past recognition would turn the
        branch red for the wrong reason, and the assertion on `find` is what
        says the fixture has stopped describing the tree before that happens.
        """
        find, replace = edit
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        target = os.path.join(tmp.name, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(os.path.join(REPO, rel), encoding="utf-8") as f:
            source = f.read()
        self.assertIn(find, source,
                      f"{rel} no longer contains {find!r}; the fixture for this "
                      f"case has stopped describing the tree")
        with open(target, "w", encoding="utf-8") as f:
            f.write(source.replace(find, replace))
        return tmp.name

    def site(self, rel, anchor, role):
        """One row of the table, so a case names the site it is about."""
        return [(rel, anchor, role)]

    def test_every_site_in_the_table_declares_the_declared_codec(self):
        # The positive claim, over the committed tree and the table as
        # committed. Red on `main` before the declarations this issue added,
        # which is what makes it evidence about the change rather than about
        # the tree it was written against.
        rows, problems = cpe.check_declarations()
        self.assertEqual(problems, [])
        self.assertTrue(rows, "the table matched nothing")
        self.assertEqual([r for r in rows if r[3] != cpe.DECLARED], [])

    def test_a_writer_without_the_keyword_is_named(self):
        rel = "windows/tools/battery_trace.py"
        root = self.copy_tool(rel, WRITER_STRIP)
        rows, problems = cpe.check_declarations(
            self.site(rel, "open(args.csv", "writer"), root)
        # `_shown()` gives a temp tree the path it was given rather than a
        # `../../../../../tmp` chain, so the site is named by its tail and the
        # rest of the row is compared whole.
        self.assertEqual([r[1:] for r in rows],
                         [("open(args.csv", "writer", None)], rows)
        self.assertTrue(all(r[0].endswith(rel) for r in rows), rows)
        # One problem per site found, as a relation rather than a tally: a
        # count of how many `open()` calls the tool has is a value every merge
        # adding one has to edit, and the claim here is that nothing found goes
        # unreported.
        self.assertEqual(len(problems), len(rows), problems)
        self.assertIn("declares no encoding=", problems[0])
        # The direction matters: a writer is the half where an undeclared codec
        # decides what lands on disk, and the message has to say so rather than
        # describing the read a reader would do.
        self.assertIn("the bytes it puts on disk", problems[0])

    def test_a_reader_without_the_keyword_is_named(self):
        rel = "windows/tools/test_battery_trace.py"
        root = self.copy_tool(rel, READER_STRIP)
        rows, problems = cpe.check_declarations(
            self.site(rel, "(TRACES / name).read_text", "reader"), root)
        # Every site the anchor finds is reported, and none of them carries the
        # keyword any more. The anchor names a function used by more than one
        # call site, and the non-vacuity assertion is what stops this passing
        # because the fixture matched nothing -- a count of those sites would
        # redden every time someone adds a caller.
        self.assertTrue(rows, "the anchor matched nothing in the copy")
        self.assertTrue(all(r[1:] == ("(TRACES / name).read_text", "reader",
                                      None) for r in rows), rows)
        self.assertTrue(all(r[0].endswith(rel) for r in rows), rows)
        self.assertEqual(len(problems), len(rows), problems)
        self.assertTrue(all("declares no encoding=" in p for p in problems),
                        problems)
        self.assertTrue(all("the bytes it reads" in p for p in problems),
                        problems)

    def test_a_site_declaring_another_codec_is_named(self):
        # The branch a keyword-name check cannot reach: the site carries an
        # `encoding=` and is still wrong, which is exactly what
        # 0751-capture-encoding.md §3 is about. `utf-8-sig` is the real
        # alternative rather than an invented one -- it is the codec that adds
        # the BOM this format is defined without.
        rel = "windows/tools/charge_target_test.py"
        root = self.copy_tool(rel, WRITER_STRIP)
        path = os.path.join(root, rel)
        with open(path, encoding="utf-8") as f:
            source = f.read().replace(
                '"a", newline=""', '"a", newline="", encoding="utf-8-sig"')
        with open(path, "w", encoding="utf-8") as f:
            f.write(source)
        rows, problems = cpe.check_declarations(
            self.site(rel, "open(args.csv", "writer"), root)
        self.assertEqual([r[1:] for r in rows],
                         [("open(args.csv", "writer", "utf-8-sig")], rows)
        self.assertTrue(all(r[0].endswith(rel) for r in rows), rows)
        self.assertEqual(len(problems), len(rows), problems)
        self.assertIn("'utf-8-sig'", problems[0])
        self.assertIn("rather than utf-8", problems[0])

    def test_an_anchor_matching_nothing_is_reported(self):
        # The silent one. A table entry whose anchor no longer matches any call
        # would otherwise read as a site that is fine, which is the whole
        # failure mode this suite exists for -- a checker that has quietly
        # stopped looking is indistinguishable from one that has passed.
        rows, problems = cpe.check_declarations(
            self.site("windows/tools/battery_trace.py",
                      "open(args.nonexistent_flag", "writer"))
        self.assertEqual(rows, [])
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("no call matching", problems[0])
        self.assertIn("not looking at the writer it names", problems[0])

    def test_an_enclosing_call_is_not_mistaken_for_the_site(self):
        # The anchor matches `p.read_text(...)` and must not also match the
        # `.splitlines()` wrapped around it, whose rendering *starts* with it,
        # or the `csv.reader(...)` around that, whose rendering contains it.
        # Held on a snippet rather than on a real file so the claim is about
        # the predicate and not about how many readers any one suite happens
        # to have -- a count of those is a value every merge adding a case
        # would have to edit.
        snippet = (
            "import csv\n"
            "p.read_text(encoding='utf-8')\n"
            "p.read_text(encoding='utf-8').splitlines()\n"
            "list(csv.reader(p.read_text(encoding='utf-8').splitlines()))\n"
        )
        tree = ast.parse(snippet)
        calls = [c for c in ast.walk(tree)
                 if isinstance(c, ast.Call)
                 and ast.unparse(c).startswith("p.read_text")]
        rendered = [ast.unparse(c) for c in calls]
        # Every one of them renders starting with the anchor, so the anchor
        # alone finds the two `.splitlines()` wrappers as well as the reads.
        self.assertTrue(any(r.endswith(".splitlines()") for r in rendered),
                        rendered)
        direct = [ast.unparse(c) for c in calls if cpe._direct_call(c)]
        self.assertTrue(direct, rendered)
        self.assertTrue(all(r == "p.read_text(encoding='utf-8')"
                            for r in direct), direct)

    def test_the_anchor_finds_the_reader_and_not_its_wrappers_in_a_real_file(self):
        # The same property against the file it is there for, held as a
        # relation rather than a count: every site the battery-trace table
        # names carries the codec. A run that reported the `.splitlines()`
        # wrappers too would read *their* keywords, which carry none, and this
        # is where that would show.
        found = cpe.keywords_at(
            os.path.join(REPO, "windows/tools/test_battery_trace.py"),
            "path.read_text")
        self.assertTrue(found)
        self.assertEqual([k for k in found if "encoding" not in k], [])

    def test_a_missing_file_is_reported_rather_than_skipped(self):
        # An unreadable or unparseable site is a hole in the coverage, not a
        # row to leave out: reported as its own problem so a red run says what
        # it stopped checking.
        rows, problems = cpe.check_declarations(
            self.site("windows/tools/does_not_exist.py", "open(args.csv",
                      "writer"))
        self.assertEqual(rows, [])
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("unchecked rather than held", problems[0])


class TheSuiteSplit(unittest.TestCase):
    """Which of the suites' reads the table covers, held rather than tallied.

    `probe-csv-encoding.md` §3 and this tool's own `DECLARATIONS` comment both
    say that the `read_text()` calls reading *source* are deliberately out of
    the site table. Written as a count, that claim is stale the next time a
    suite reads another committed file -- and it was, within this very change,
    which added a source read to each suite. So the property is held here
    instead: every read whose receiver names a capture is in the table, and no
    read whose receiver names a source file is.

    The classification is by receiver, which is the only thing that decides it:
    a `read_text()` on `TRACES / name` is reading a capture whoever calls it
    and however it is spelled on the line.
    """

    def reads(self, rel):
        return read_text_receivers(os.path.join(REPO, rel))

    def is_capture(self, rel, receiver):
        """Whether a rendered receiver names a capture rather than a source file.

        A receiver is a capture read when it is built from one of the
        suite's capture-path constants. The temp-file readers (`path`,
        `trace`) are captures too -- a run's own `--csv` output, read back to
        check it -- so those names are recognised as well. Everything else is
        a source file: a tool's own text, a shell script, `registers.yaml`, the
        DSDT, the annotations CSV, the procedure document.
        """
        holders = CAPTURE_HOLDERS[rel]
        root = ast.parse(receiver.replace(".read_text", ""), mode="eval").body
        if isinstance(root, ast.BinOp) and isinstance(root.left, ast.Name):
            root = root.left
        if isinstance(root, ast.Name):
            return root.id in holders or root.id in ("path", "trace")
        return False

    def test_every_capture_reader_is_in_the_table(self):
        # The load-bearing direction. A capture read nobody listed is a
        # capture this check does not hold, which is the failure the
        # declaration half exists to prevent -- and it is what a hand-kept
        # count cannot notice, since a count says how many were listed rather
        # than whether the right ones were.
        in_table = {(rel, anchor) for rel, anchor, _ in cpe.DECLARATIONS}
        missing = []
        for rel in SUITES:
            for receiver, codecs in self.reads(rel).items():
                if not self.is_capture(rel, receiver):
                    continue
                if not any(r == rel and receiver.startswith(a)
                           for r, a in in_table):
                    missing.append(f"{rel}: {receiver} reads a capture and is "
                                   f"not in the declaration table")
        self.assertEqual(missing, [])

    def test_every_capture_reader_declares_the_declared_codec(self):
        # Stated over the receivers rather than over the table, so it is the
        # tree that is asserted and not the table's opinion of the tree: a
        # table entry that stopped matching would leave this green, which is
        # why the case above exists alongside it.
        undeclared = []
        for rel in SUITES:
            for receiver, codecs in self.reads(rel).items():
                if self.is_capture(rel, receiver):
                    undeclared += [f"{rel}: {receiver} declares {c!r}"
                                   for c in codecs if c != cpe.DECLARED]
        self.assertEqual(undeclared, [])

    def test_a_source_read_is_not_in_the_table(self):
        # The other direction, and the one the exclusion sentence in the
        # tool and in §3 rests on: a read whose receiver names a source file is
        # a different population and is not this table's to hold. If one of
        # them ever is listed, the table has stopped being the claim it says
        # it is -- and this goes red rather than quietly broadening.
        listed = [(rel, anchor) for rel, anchor, _ in cpe.DECLARATIONS]
        wrong = [f"{rel}: {receiver}" for rel in SUITES
                 for receiver in self.reads(rel)
                 if not self.is_capture(rel, receiver)
                 and any(r == rel and receiver.startswith(a)
                         for r, a in listed)]
        self.assertEqual(wrong, [])

    def test_the_suites_actually_hold_reads_of_both_kinds(self):
        # The non-vacuity guard, without a count. Both directions above are
        # satisfied by an empty read: `is_capture` classifying nothing, or
        # classifying everything the same way. What is asserted is that the
        # split has both halves in it -- there is a capture reader and there is
        # a source reader -- so a change to the classifier that collapsed the
        # distinction is red here rather than green everywhere.
        for rel in SUITES:
            reads = self.reads(rel)
            with self.subTest(suite=rel):
                self.assertTrue(reads, f"{rel} has no read_text() to classify")
                kinds = {self.is_capture(rel, r) for r in reads}
                self.assertEqual(kinds, {True, False},
                                 f"{rel}: every read is the same kind, so the "
                                 f"split is not being exercised")


class TheProcessExit(unittest.TestCase):
    """What a consumer observes, for the half that can fail on any runner."""

    def test_a_tree_with_a_clean_corpus_and_a_broken_site_exits_1(self):
        # The composition the two halves exist in: the corpus reading clean is
        # not the whole product, so a declaration that fails has to fail the
        # run even when nothing about the bytes on disk has changed.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        shutil_root = os.path.join(tmp.name, "corpus")
        os.makedirs(shutil_root)
        with open(os.path.join(shutil_root, "clean.csv"), "wb") as f:
            f.write(CLEAN)
        site_root = tempfile.TemporaryDirectory()
        self.addCleanup(site_root.cleanup)
        target = os.path.join(site_root.name, "windows", "tools")
        os.makedirs(target)
        with open(os.path.join(REPO, "windows/tools/battery_trace.py"),
                  encoding="utf-8") as f:
            source = f.read().replace(*WRITER_STRIP)
        with open(os.path.join(target, "battery_trace.py"), "w",
                  encoding="utf-8") as f:
            f.write(source)
        done = child("--root", shutil_root, "--quiet",
                     "--declarations-root", site_root.name)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("declares no encoding=", done.stdout)

    def test_quiet_prints_the_problems_and_not_the_tables(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with open(os.path.join(tmp.name, "bom.csv"), "wb") as f:
            f.write(BOM)
        done = child("--root", tmp.name, "--quiet")
        self.assertNotIn(CORPUS_HEADING, done.stdout)
        self.assertNotIn(DECLARATION_HEADING, done.stdout)
        self.assertIn("carries a BOM", done.stdout)


if __name__ == "__main__":
    unittest.main()