#!/usr/bin/env python3
"""What `trace_xdata_refs.py` tells a reader *before* they run a diff.

`test_trace_xdata_refs.py` is scoped to which instructions come back from
`walk()`, and its own docstring says so; this is the other half of the tool,
the one that writes advice rather than cells. They are kept apart on purpose:
a class about the usage surface does not belong under "the bounds contract of
`walk()`, on its own", and folding it in would mean rewriting that docstring to
say so -- a contested hunk in a file several issues have touched, bought for
nothing.

**Why the advice surface needs holding at all.** Issue #1020 reported that
`Usage:` never named `--terminator-column`, and that the `--csv` table it
produces is then one cell short of a committed table -- with nothing on stderr
saying why, and exit 0. A usage block is the only surface a reader reaches
before running anything, so an omission there is the whole finding: it is the
one place the omission costs anything, and it is not the docstring (which names
the flag at its third point) or `--help` (which names it in the argument's own
help string). Every case below is about the `Usage:` block specifically, and
`UsageBlockTests.test_the_check_is_over_the_usage_block_and_not_the_docstring`
is the case that says so.

**The defect is load-bearing in the tool's own commands.** Six committed tables
carry a `terminator` column; a bare `--csv` run has none, so a diff against one
is a line of "-" per row and nothing about why. `--check` has said so since
`--terminator-column` landed, but only on the `--check` path, where the reader
hands the tool the file to diff against. The `| diff -` command a reader
actually writes has no such hand-off, and
`docs/findings/csv-column-usage-advice.md` is the write-up.

**No hardware, no Ghidra, no network.** The firmware is the committed 256 KiB
image and the tables are the committed `*.csv` files; six subprocesses over it
is under a second. Nothing here reads the physical machine, and nothing in
this suite is evidence about the EC.
"""
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).parent
# trace_xdata_refs imports disasm8051 by bare module name, the way
# test_trace_xdata_refs.py does and for the same reason.
sys.path.insert(0, str(HERE))
import trace_xdata_refs as T          # noqa: E402

REPO = HERE.parent.parent
TOOL = HERE / "trace_xdata_refs.py"
# The two spellings of the same committed image: the `Usage:` block's are
# relative to the tool's own directory, because that is the directory a reader
# standing in `ec/tools` is in when they copy one.
FW_TOOLS = "../firmware/GMxMGxx_11.800"
FW_ROOT = "ec/firmware/GMxMGxx_11.800"

# The two fragments of the advice surface, kept apart because conflating them
# is the mistake this suite exists to prevent. `NEW_NOTE` is this change's
# stderr line and `OLD_NOTE` is the `--check` one that predates it; a case
# asserting the first is absent under `--check` has to be able to name the
# second, or "absent" would pass on a tool that printed neither.
NEW_NOTE = "carries a `terminator` column and covers"
OLD_NOTE = "has a `terminator` column, so it was re-cut"

# `argparse`'s own layout: an indented line whose first non-space character is
# a dash is an option line, and everything before the two-space gutter is that
# option's spec. `--check [PATH]` therefore yields `--check` and not the
# metavar. The help option is spelled two ways on one line, which is why the
# spec is tokenised rather than cut at the first space.
OPTION_LINE = re.compile(r"^\s+-{1,2}\S")
OPTION_TOKEN = re.compile(r"--?[A-Za-z0-9][A-Za-z0-9-]*")
# A redirect target, so `> sites.csv` in a `Usage:` line can be pointed at a
# temporary directory instead of writing into the checkout. Applied to the
# whole line rather than to one known spelling, so a `Usage:` line added later
# that redirects somewhere else is rewritten too.
REDIRECT = re.compile(r">\s*([^\s|]+)")


def usage_lines(doc: str = None):
    """The `Usage:` block's command lines, stripped and non-empty.

    **The slice, and not the whole docstring.** `Usage:` is the last section of
    the module docstring, so the block is everything from that heading on; the
    four points above it are prose about what the tool computes and are not
    copy-pasteable commands. An assertion over the whole docstring would pass
    on a `Usage:` block that names nothing at all, because `--terminator-column`
    is already written out in point 3 -- which is exactly the state issue
    #1020 found the file in, and the reason that assertion would have proved
    nothing about the defect.
    """
    doc = T.__doc__ if doc is None else doc
    _, _, block = doc.partition("Usage:\n")
    return [line.strip() for line in block.splitlines() if line.strip()]


def declared_options(help_text: str):
    """The option strings the parser itself declares, `--help` excepted.

    Read out of `--help` rather than out of the parser's internals, so what
    this holds is what a reader is shown. `--help` is dropped because it is the
    one option every tool in this tree leaves out of its examples and a reader
    never copies it from a usage block.
    """
    flags = set()
    for line in help_text.splitlines():
        if not OPTION_LINE.match(line):
            continue
        flags.update(OPTION_TOKEN.findall(line.strip().split("  ", 1)[0]))
    return sorted(flags - {"-h", "--help"})


def help_text() -> str:
    # A wide COLUMNS so no option's help string is the thing that wraps: the
    # parser reads it through shutil.get_terminal_size(), and a narrow
    # terminal would put half a flag on a line of its own.
    out = subprocess.run([sys.executable, str(TOOL), "--help"],
                         capture_output=True, text=True, env={**os.environ,
                                                              "COLUMNS": "200"})
    return out.stdout


def usage_omissions(help_out: str, block=None):
    """Which declared options the `Usage:` block never names.

    Split out of the case that uses it so the "the assertion has teeth" case
    can hand it a block with a line removed and get an answer, rather than
    re-deriving the rule a second time and hoping the two agree.
    """
    lines = usage_lines() if block is None else block
    return [flag for flag in declared_options(help_out)
            if not any(flag in line for line in lines)]


def run_in_process(argv, annot=None):
    """`main()`'s own return code, stdout and stderr, for `argv`.

    In-process rather than as a subprocess so the streams can be compared as
    strings: `main()` returns an int instead of calling `sys.exit`, and
    `redirect_stdout` captures exactly the bytes it wrote.

    `annot` repoints the module's annotations directory for the duration of
    the call, which is the only way to run the same command against a tree the
    scan finds nothing in. It is a rebind of one name, restored in a `finally`
    rather than mocked, because the point of the comparison is that the *only*
    difference between the two runs is which directory the scan read.
    """
    saved_argv, saved_annot = sys.argv, T.ANNOT
    if annot is not None:
        T.ANNOT = annot
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["trace_xdata_refs.py"] + list(argv)
        with redirect_stdout(out), redirect_stderr(err):
            rc = T.main()
    finally:
        sys.argv, T.ANNOT = saved_argv, saved_annot
    return rc, out.getvalue(), err.getvalue()


def run_tool(argv, cwd=REPO, text=True):
    """The tool as a reader runs it: a real process, real exit status.

    `text=False` for the one comparison that is about bytes rather than
    lines. `subprocess` decodes in universal-newline mode, which rewrites the
    csv module's own CRLF terminator to LF on the way in -- the same
    translation `check_table()` opens the committed file with `newline=""`
    to avoid, and the reason that case compares in binary.
    """
    return subprocess.run([sys.executable, str(TOOL)] + list(argv),
                          capture_output=True, text=text, cwd=cwd)


class UsageBlockTests(unittest.TestCase):
    """Every declared option has to be named in the `Usage:` block, and that
    assertion has to be able to fail."""

    def test_every_declared_option_is_named_in_a_usage_line(self):
        help_out = help_text()
        # Not a census of how many there are: an expected count turns every
        # option added later into a failure, which is the wrong trade, and
        # `tools/test_readme_suite_table.py` says the same about its own set.
        # What is asserted is the claim -- each declared flag is discoverable
        # from a line a reader can copy.
        self.assertEqual(usage_omissions(help_out), [])
        # And the block is not empty and not one line, because a predicate
        # that found no lines would pass the assertion above vacuously.
        self.assertGreater(len(usage_lines()), 1)

    def test_the_check_is_over_the_usage_block_and_not_the_docstring(self):
        # The teeth. The same predicate, a block with the flag's line removed,
        # has to report it -- and it does only because the predicate reads the
        # `Usage:` slice: the docstring names the flag above the block, in its
        # third point, so a whole-docstring assertion would have stayed green on
        # the file as it was before this change.
        help_out = help_text()
        flag = "--terminator-column"
        without = [ln for ln in usage_lines() if flag not in ln]
        self.assertLess(len(without), len(usage_lines()))
        self.assertIn(flag, usage_omissions(help_out, without))
        self.assertNotIn(flag, usage_omissions(help_out))
        # The distinction, stated as its own fact: the flag is in the
        # docstring, which is why reading that one is not the same check.
        above, _, _ = T.__doc__.partition("Usage:")
        self.assertIn(flag, above)

    def test_every_usage_line_runs_and_accounts_for_its_own_output(self):
        # The issue's acceptance line, in the general form: a reader who copies
        # any `Usage:` line gets a table that reproduces the committed CSV, or
        # is told on stderr what is wrong with it. Each line goes through `sh`
        # because two of them use the shell -- one redirects, one pipes into
        # `diff` -- and a reader pastes into a shell, so running them any other
        # way would test a different command than the one printed. The strings
        # come from the tool's own committed docstring, so nothing outside this
        # repository is executed.
        #
        # cwd is the tool's directory, not the repository root, because that
        # is where the block's `../firmware` and `../annotations` resolve. Only
        # the redirect target moves, into a temporary directory, so no run
        # writes into the checkout.
        #
        # **The `--check` line is held to a different contract, and the
        # difference is deliberate.** `--check`'s exit code is its verdict, not
        # a defect: 0 is "this run reproduces the file" and 1 is "it does
        # not", and both are correct answers to the question the flag asks. So
        # for those lines the requirement is that a non-zero exit says *which
        # file* differed, and every other line must exit 0.
        #
        # One line in the block as committed does take the `--check` branch and
        # does not reproduce -- `0x0860 --csv --census-column --check` asks for
        # one address against the fifteen `xdata-086x-dispatch-sites.csv`
        # carries, so it prints 0 lines and reports 105 of that table's 114
        # rows as not produced. That is pre-existing, it is a finding of its
        # own, and `docs/findings/csv-column-usage-advice.md` carries it with
        # the reproduction. It is not fixed here: the two fixes available are a
        # 193-character line naming all fifteen addresses, or the
        # `--check`-implies-`--census-column` defect this change explicitly
        # defers, and a hand-kept address list inside the docstring is the
        # thing CLAUDE.md's "no hand-kept totals" rule is about. A reader is
        # better served by that being written down than by a long line that
        # silently duplicates a list `walk-window-terminators.md` already
        # prints.
        with tempfile.TemporaryDirectory() as tmp:
            for line in usage_lines():
                with self.subTest(line=line):
                    command = REDIRECT.sub(
                        lambda m: "> " + os.path.join(tmp, m.group(1)), line)
                    out = subprocess.run(command, shell=True, executable="/bin/sh",
                                         cwd=HERE, capture_output=True, text=True)
                    if "--check" in line:
                        if out.returncode:
                            self.assertIn("differs from what this run produced",
                                          out.stderr)
                    else:
                        self.assertEqual(out.returncode, 0,
                                         f"{line}\n{out.stdout}\n{out.stderr}")

    def test_the_terminator_line_reproduces_its_committed_table(self):
        # The same run as a subprocess, compared to the file rather than to an
        # exit status, so a failure names the table and the header. In binary,
        # for the reason `run_tool()` gives: the committed file carries the csv
        # module's own CRLF terminator, and decoding either side would rewrite
        # it to LF and report a difference on every row.
        out = run_tool([FW_ROOT, "0x0751", "--csv", "--terminator-column"],
                       text=False)
        self.assertEqual(out.returncode, 0, out.stderr.decode())
        with open(REPO / "ec/annotations/manual-fan-ctrl-0751-sites.csv", "rb") as f:
            committed = f.read()
        self.assertEqual(out.stdout, committed)
        # The flag was passed, so the new note has nothing to say and stderr
        # says nothing at all.
        self.assertNotIn(b"terminator", out.stderr)
        # The column is the reason, said as a header and not as a row count: a
        # table that reproduced the file with the flag off would be a different
        # table with a different header, and this is what separates the two.
        self.assertIn(b"terminator", committed.splitlines()[0])


class StderrNoteTests(unittest.TestCase):
    """The computed-trigger note, in both directions.

    A note that fires where it is wrong is worse than no note: a tool that
    says "every row is short that cell" to a correct run is dismissed within a
    week and then not read at all. So the does-not-fire cases are half of this
    class and are the half that decide whether the advice is trusted.
    """

    def test_the_note_fires_on_a_bare_csv_run_of_a_terminator_table(self):
        rc, _, err = run_in_process([FW_ROOT, "0x0751", "--csv"])
        self.assertEqual(rc, 0)
        self.assertIn("--terminator-column", err)
        self.assertIn("manual-fan-ctrl-0751-sites.csv", err)
        # The table it names is the one a diff would be against, so the note
        # is a fact about the tree and not an opinion about the run.
        self.assertIn(NEW_NOTE, err)

    def test_the_note_does_not_change_the_table_on_stdout(self):
        # The product is stdout and the note is stderr, asserted rather than
        # assumed: the same command is run against a directory holding no
        # committed table, and the two stdouts have to be byte-identical. That
        # is the strongest version of "the note could not have fired", so a
        # stdout that moved is a stdout that moved because of something other
        # than the note.
        with tempfile.TemporaryDirectory() as empty:
            rc_a, out_a, err_a = run_in_process([FW_ROOT, "0x0751", "--csv"])
            rc_b, out_b, err_b = run_in_process([FW_ROOT, "0x0751", "--csv"],
                                                annot=empty)
        self.assertEqual(rc_a, rc_b)
        self.assertIn(NEW_NOTE, err_a)
        self.assertNotIn(NEW_NOTE, err_b)
        self.assertEqual(out_a, out_b)
        self.assertTrue(out_a.startswith("addr,file_offset,"))

    def test_the_note_stays_quiet_where_it_would_be_wrong(self):
        # 0x0860: the committed table carries a `census` column and no
        # `terminator` one, so the note would name a cell that does not exist
        # in the file it points at. Read as a subprocess rather than through
        # `run_in_process()`, so "stderr is empty" is a fact about the tool and
        # not about the interpreter's warning machinery -- `main()` opens the
        # firmware without a `with`, and in-process under unittest the
        # resulting ResourceWarning lands in the very stream being asserted.
        out = run_tool([FW_ROOT, "0x0860", "--csv"])
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stderr, "",
                         "stderr was not empty on a run the note must stay off")
        # The reason the silence is right, asserted rather than assumed: the
        # table a 0x0860 reader diffs against is this one, and it has a `census`
        # column where the note would claim a `terminator` one. A re-cut that
        # gave it a `terminator` column would make this case wrong, and it
        # should go red when that happens.
        header = T.committed_columns(
            REPO / "ec/annotations/xdata-086x-dispatch-sites.csv")
        self.assertIn("census", header)
        self.assertNotIn("terminator", header)
        self.assertNotIn("terminator", out.stdout.splitlines()[0])

    def test_the_note_stays_quiet_for_an_address_in_no_committed_table(self):
        # Not found by this method, said as such by saying nothing: a scan that
        # located no table is not a claim that nothing is wrong, and a note
        # that fired here would be guessing.
        addrs = ["0xFFF0", "0xDEAD", "0x1234"]
        self.assertEqual(T.committed_terminator_tables(T.ANNOT, addrs), [])
        rc, _, err = run_in_process([FW_ROOT] + addrs + ["--csv"])
        self.assertEqual(rc, 0)
        self.assertNotIn("terminator", err)

    def test_one_covered_address_is_not_enough_to_fire_the_note(self):
        # The rule is *every* requested address, not any. 0x07C4 is a row of a
        # committed `terminator` table and 0x07E2 is a row of none, so a reader
        # diffing both gets a table with no committed counterpart at all and a
        # note pointing at one of the two files would be the wrong advice. This
        # is the case that separates the address match from the cheaper
        # "always-true on a bare --csv" version, which would fire on every
        # `--csv` run in `Usage:` including this one.
        self.assertEqual(
            T.committed_terminator_tables(T.ANNOT, ["0x07C4", "0x07E2"]), [])
        rc, _, err = run_in_process([FW_ROOT, "0x07C4", "0x07E2", "--csv"])
        self.assertEqual(rc, 0)
        self.assertNotIn("terminator", err)
        # The same two addresses with the covered one alone do fire, so the
        # half above is about the match and not about an address this scan
        # cannot read.
        self.assertEqual(
            [os.path.basename(p) for p, _ in
             T.committed_terminator_tables(T.ANNOT, ["0x07C4", "0x07D3"])],
            ["ec-07c4-07d5-sites.csv"])

    def test_the_scan_finds_the_committed_tables_rather_than_a_list(self):
        # The helper is handed a scratch tree, which is the shape every other
        # check in this directory takes and the reason the directory is a
        # parameter. A committed tree the scan finds nothing in is not asserted
        # as a figure: the count moves whenever a table is re-cut, and a
        # number here would be a line every such change has to edit.
        self.assertTrue(T.committed_terminator_tables(T.ANNOT, ["0x0751"]))
        with tempfile.TemporaryDirectory() as scratch:
            self.assertEqual(
                T.committed_terminator_tables(scratch, ["0x0751"]), [])
            # A directory that is not there at all is the same answer, not an
            # error: the scan is advice and must never be what fails a run.
            self.assertEqual(T.committed_terminator_tables(
                os.path.join(scratch, "absent"), ["0x0751"]), [])


class CheckPathIsUnchangedTests(unittest.TestCase):
    """`--check` is what issue #1020 froze, and the new note is off on it.

    The suppression is `args.check is None`, so on that path the old note is
    the only one that prints. These cases assert the `--check` output rather
    than trusting that a guard was added: a scan that ran anyway would double
    the advice, and one that ran *instead* would silence the note that has been
    there since `--terminator-column` landed.
    """

    def test_the_default_check_still_reproduces_its_table(self):
        out = run_tool([FW_ROOT, "0x0860", "0x0862", "0x0865", "0x0866", "0x0867",
                        "0x0868", "0x0869", "0x086A", "0x086B", "0x086D",
                        "0x086E", "0x1C39", "0x1C3A", "0x1F01", "0x1F07",
                        "--csv", "--census-column", "--check"])
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("reproduces it byte for byte", out.stdout)
        # The 0x086x table is the regression test that no `access` or `window`
        # cell moved when the other six tables gained a column, and it can only
        # stay that while the default output has no column in it.
        self.assertNotIn("terminator", out.stdout.splitlines()[0])

    def test_a_check_against_a_terminator_table_prints_the_old_note_once(self):
        out = run_tool([FW_ROOT, "0x0751", "--csv", "--check",
                        "ec/annotations/manual-fan-ctrl-0751-sites.csv"])
        # The exit code is not asserted here. This run is red, and it is red
        # for a second reason this change does not touch: `main()` loads the
        # census map whenever `--check` is given, so the table also grows a
        # `census` column of `not recorded`. Pinning 1 would make that
        # behaviour the expected one, so what is held is the note -- the old
        # one exactly once, the new one not at all.
        self.assertEqual(out.stderr.count(OLD_NOTE), 1, out.stderr)
        self.assertNotIn(NEW_NOTE, out.stderr)


if __name__ == '__main__':
    unittest.main()
