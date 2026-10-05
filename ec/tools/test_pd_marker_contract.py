#!/usr/bin/env python3
"""Stands in for #857's "done looks like": that each `ec/tools/` module's
`PD_MARKER` contract is recorded, and that `scan_refs.py` holds the one the
issue asked it to.

What this suite is for, and what it is not:

* **It is not a count of the census.** No case asserts how many rows, modules or
  contracts the table holds -- a tool landing in this directory moves all three,
  and a suite that went red on that would be a merge conflict wearing a
  unittest's clothes. What is asserted is a *property*: every module that reads
  the marker has a row, every `note-stdout` row's note really does reach stdout,
  and the one module this change altered is altered in the way the issue asked.
* **The properties are recomputed, not read back.** The stream check re-reads
  the module's own source text rather than asking `check_pd_marker_contract.py`
  what it thought; a census tool that classified a site wrongly would otherwise
  agree with itself. Only the two cases that are about the committed artifact
  (the CSV reproduces byte for byte, `scan_refs.py`'s row says `refuse`) read
  the tool's output, because reproducing it *is* what they are checking.
* **The regression is a scratch copy, never the committed image.** The marker is
  clobbered in a temporary file and the tool is run against that. Nothing here
  reads the hardware, writes to the repository, or implies that either happened.

The regression itself is `docs/findings/pd-marker-caller-contracts.md` §3: on an
image whose `ITE8850-PD` marker is gone, the tool used to find seven sites for
`0x0001`, count them in neither split column, and print `ABSENT` -- the word
`docs/findings.md` §4 records having to be retracted twice, reached by a
different route. The case below pins the fixed behaviour: non-zero exit, nothing
on stdout, and no `ABSENT` anywhere.
"""
import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
CSV = os.path.join(HERE, os.pardir, "annotations",
                   "pd-marker-caller-contracts.csv")
TOOL = os.path.join(HERE, "check_pd_marker_contract.py")
SCAN_REFS = os.path.join(HERE, "scan_refs.py")

sys.path.insert(0, HERE)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


census = load("pdmarker_census", TOOL)


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def reads_marker(path) -> bool:
    """Whether this module *uses* `PD_MARKER` rather than naming it in prose.

    A docstring spelling `PD_MARKER` is not a read of it, and docstrings in
    this directory do so constantly -- `check_image_map.py`'s banner names the
    marker and never touches it. Only a statement is looked at, so a module
    whose every mention is in a string does not become a row's obligation.
    """
    try:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Return, ast.If,
                             ast.Expr, ast.AugAssign)):
            if census.MARKER in census.names(node):
                return True
    return False


def guard_prints(path, function) -> list:
    """`(call, file argument)` for every `print` in the guard over the marker.

    Scoped to that one branch on purpose. A module can print several unrelated
    things in the same function -- `check_image_map.py` reports refused bands on
    stderr long after the marker note -- and a window over the whole function
    would say a module routes *something* to stderr and call that a contract it
    does not have. What is checked is the guard's own note, which is the claim
    the `note-stdout` row makes.

    Found by structure rather than by offset: the statement in `function` that
    reads `PD_MARKER`, and then the `if` in the same statement list whose test
    reads a name that statement bound. **No line number is used here either**
    -- the census commits none (see `COLUMNS` in the tool), and finding the
    guard at `site + 1` would put the same hazard in this file, where an
    unrelated merge growing the module would turn this case red for a branch
    that never touched the census. A shape this walk cannot find fails with
    that as the reason, which is the outcome worth having.
    """
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    host = next((n for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == function), None)
    if host is None:
        return []
    out = []
    for block in census.blocks(host.body):
        for i, st in enumerate(block):
            if not isinstance(st, (ast.Assign, ast.AnnAssign)):
                continue
            if census.MARKER not in census.names(st):
                continue
            bound = census.assigns(st)
            for guard in block[i + 1:]:
                if not isinstance(guard, ast.If):
                    continue
                if not census.names(guard.test) & bound:
                    continue
                for node in ast.walk(guard):
                    if not (isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Name)
                            and node.func.id == "print"):
                        continue
                    target = ""
                    for kw in node.keywords:
                        if kw.arg == "file":
                            target = ast.unparse(kw.value)
                    out.append((node, target))
                return out
    return out


class CommittedTableTests(unittest.TestCase):
    """The committed CSV is the product of the command, not a hand-kept file."""

    def test_check_reproduces_the_committed_csv_byte_for_byte(self):
        done = run([sys.executable, TOOL, "--check"])
        self.assertEqual(done.returncode, 0,
                         "check_pd_marker_contract.py --check did not reproduce "
                         f"{os.path.relpath(CSV, REPO)}:\n{done.stderr}")

    def test_every_contract_in_the_table_is_one_the_tool_defines(self):
        # A token in the table the tool cannot produce would mean the file was
        # hand-edited, which --check catches by byte diff but not by meaning.
        with open(CSV, newline="") as f:
            text = f.read()
        for contract in census.CONTRACTS:
            self.assertIn(f",{contract},", text)
        for row in census.census():
            self.assertIn(row["contract"], census.CONTRACTS)


class CoverageTests(unittest.TestCase):
    """A module that reads the marker is not a module with no contract."""

    def test_every_module_reading_the_marker_has_at_least_one_row(self):
        listed = {r["module"] for r in census.census()}
        # Found by a scan of this directory, never by a list: a new tool that
        # reads PD_MARKER has to show up here without an edit to this suite.
        for name in sorted(os.listdir(HERE)):
            if not name.endswith(".py") or name.startswith("test_"):
                continue
            if not reads_marker(os.path.join(HERE, name)):
                continue
            self.assertIn(name, listed,
                          f"{name} reads PD_MARKER but has no census row, so "
                          "its contract is unrecorded. A row saying 'not found "
                          "by this method' is the alternative; silence is not.")

    def test_no_row_points_at_a_module_that_is_no_longer_there(self):
        for row in census.census():
            self.assertTrue(
                os.path.exists(os.path.join(HERE, row["module"])),
                f"the table names {row['module']}, which is not in this "
                "directory any more -- regenerate it with --csv")

    def test_only_a_refusal_names_how_it_ends(self):
        # `exit` is how the run stops, so it belongs to the one contract that
        # stops it. A row with an exit and no refusal, or a refusal with no
        # exit, is a table that was edited rather than generated.
        for row in census.census():
            if row["contract"] == census.REFUSE:
                self.assertNotEqual(row["exit"], "",
                                    f"{row['module']}'s {row['function']}() "
                                    "refuses but does not say how")
            else:
                self.assertEqual(row["exit"], "",
                                 f"{row['module']}'s {row['function']}() is "
                                 f"{row['contract']} yet names an exit")


class StreamTests(unittest.TestCase):
    """`note-stdout` means the note reaches stdout, checked without the tool.

    Re-derived from the module's own parse rather than asked of
    `check_pd_marker_contract.py`: a classifier that filed a stderr note in
    this column would otherwise be graded by itself. The rule is the one a
    reader cares about -- a `print` with no `file=` goes to stdout, and that is
    the whole difference between the two note contracts -- so the check is
    exactly that, and no more.
    """

    def test_every_note_stdout_row_prints_without_routing_to_stderr(self):
        rows = [r for r in census.census()
                if r["contract"] == census.NOTE_STDOUT]
        self.assertTrue(rows, "no site is recorded as noting on stdout, so "
                              "this case is not checking anything")
        for row in rows:
            printed = guard_prints(os.path.join(HERE, row["module"]),
                                    row["function"])
            self.assertTrue(printed,
                            f"{row['module']}'s {row['function']}() is filed "
                            "as note-stdout but no guard over the marker "
                            "comparison in it prints anything")
            for call, target in printed:
                self.assertNotIn("stderr", target,
                                 f"{row['module']}'s {row['function']}() is "
                                 "filed as note-stdout but the print at line "
                                 f"{call.lineno} routes the note to stderr")


class ScanRefsTests(unittest.TestCase):
    """`scan_refs.py` holds the contract the issue asked it to hold."""

    def test_the_census_records_scan_refs_as_a_refusal(self):
        rows = [r for r in census.census() if r["module"] == "scan_refs.py"]
        self.assertEqual([r["contract"] for r in rows], [census.REFUSE],
                         "scan_refs.py's site moved; the census and this "
                         "case are two readings of the same source")

    def test_the_committed_table_says_so_too(self):
        with open(CSV, newline="") as f:
            self.assertIn("scan_refs.py,main,", f.read())
        done = run([sys.executable, TOOL, "--csv", "--module", "scan_refs.py"])
        self.assertIn(f",{census.REFUSE},", done.stdout)

    def test_the_committed_image_still_reports_the_count_the_gate_greps(self):
        # The cheap gate's smoke test, kept here so a refusal that was too broad
        # -- one that also fired on the good image -- fails in this suite with
        # the reason attached rather than as a bare gate line.
        done = run([sys.executable, SCAN_REFS, FIRMWARE, "0x043E"])
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("refs=15", done.stdout)
        self.assertIn("referenced", done.stdout)


class RegressionTests(unittest.TestCase):
    """The measurement the write-up reproduces, on a scratch copy.

    Nothing here touches the committed firmware: the ten bytes at the marker's
    offset are replaced in a temporary file, the tool is run against that, and
    the file goes away with the `TemporaryDirectory`.
    """

    def setUp(self):
        from trace_xdata_refs import PD_MARKER
        self.off, self.magic = PD_MARKER
        with open(FIRMWARE, "rb") as f:
            self.data = f.read()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.clobbered = os.path.join(self.tmp.name, "clobbered.bin")
        broken = bytearray(self.data)
        broken[self.off:self.off + len(self.magic)] = b"ITE8850-XX"
        with open(self.clobbered, "wb") as f:
            f.write(bytes(broken))

    def test_the_marker_really_is_what_a_python_slice_compares(self):
        # The fixture is the measurement: if this stopped holding, every case
        # below would be passing on an image whose marker never moved.
        self.assertEqual(self.data[self.off:self.off + len(self.magic)],
                         self.magic)
        with open(self.clobbered, "rb") as f:
            moved = f.read()
        self.assertNotEqual(moved[self.off:self.off + len(self.magic)],
                            self.magic)

    def test_a_lost_marker_exits_non_zero_and_prints_nothing(self):
        done = run([sys.executable, SCAN_REFS, self.clobbered, "0x0001"])
        self.assertEqual(done.returncode, 1,
                         f"a lost marker must stop the run:\n{done.stdout}")
        self.assertEqual(done.stdout, "",
                         "the note must not reach stdout: a caller redirecting "
                         f"the table to a file would get this\n{done.stdout}")
        self.assertIn("note:", done.stderr)

    def test_a_lost_marker_never_reaches_an_absent_verdict(self):
        # The regression proper. The sites are still found -- 0x0001's live in
        # the PD image -- and the count is still printed, so only the exit code
        # and the refusal stand between a reader and the word `ABSENT`.
        done = run([sys.executable, SCAN_REFS, self.clobbered, "0x0001"])
        self.assertNotIn("ABSENT", done.stdout)
        self.assertNotIn("ABSENT", done.stderr)

    def test_the_same_address_reads_as_pd_only_on_the_good_image(self):
        good = run([sys.executable, SCAN_REFS, FIRMWARE, "0x0001"])
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("referenced in the PD image ONLY", good.stdout)
        # The count that made the fallthrough visible: found, then denied.
        self.assertRegex(good.stdout, r"refs=\d+\s+ec=0\s+pd=[1-9]")


if __name__ == "__main__":
    unittest.main()
