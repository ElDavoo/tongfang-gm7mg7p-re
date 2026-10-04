#!/usr/bin/env python3
"""§2's two split tables and the partition under both keys, held to the figures
already published (issue #714).

`xdata_program_keyed_table.py` re-keys `xdata-register-map.md` §2's split table
and its three-way partition from the union `spelled_as` column onto the
committed `spellings_by_program` column. That is a **presentation** change with
a published figure behind every cell, and the risk in it is specific: a page
that prints two tables and a paragraph of arithmetic between them can drift
away from the CSV without any of the three moving, which is exactly what §2's
own rule ("re-measure the *table body*, not just its total row") exists to
catch and had not caught before this change.

**The load-bearing class is `TheMapAgrees`** and it is why this suite is not
just the tool's `--check` run twice. `--check` asserts relations *inside* one
derivation; it cannot notice that the markdown beside it says something else.
So every table §2 prints is parsed back out of the page and compared to a
regeneration, the partition's blockquote is parsed with it, and the shell
transcripts beside the tool are re-run rather than believed. A page edit that
drops a row, changes a cell, restores a superseded figure or prints a figure
its own command no longer produces fails here.

**`ThePublishedFigures` holds the page's numbers as constants typed from the
page**, not re-derived from the tool — the distinction
`test_xdata_guard_off_row_join.py` records from #753, where a suite compared a
tool against itself and passed through three re-pointings of the recipe. What
is asserted here is "the committed CSV still says what these pages say", which
is a claim about two artifacts rather than an identity inside one.

**What is deliberately *not* held is a census.** `1,375`, `850` and `7,534` are
values that move when the census is re-derived, and a suite holding one becomes
a number every landing branch has to bump. The tool's `--check` asserts the
relations instead, and this suite asserts that `--check` passes — so what a
re-derivation can break here is a relation or a page/CSV disagreement, never a
constant that quietly describes last month's tree.

Nothing here resolves anything against the firmware. The inputs are one
committed CSV and one committed markdown page; no image is opened, no Ghidra run, no network, and no laptop, EC or
Windows machine is involved.
"""
import csv
import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
EC = HERE.parent
REPO = EC.parent
TOOL = HERE / "xdata_program_keyed_table.py"
REGISTERS = EC / "annotations" / "xdata-registers.csv"
MAP = EC / "annotations" / "xdata-register-map.md"
WRITEOUT = (REPO / "docs" / "findings" /
            "xdata-register-map-per-program-keying.md")

_spec = importlib.util.spec_from_file_location("xdata_program_keyed_table", TOOL)
keyed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(keyed)

# `open(..., "w")` and its two other write modes. Held against the tool's source
# rather than described in its docstring, because a description is the thing
# that goes stale when the next mode is added.
WRITE_OPEN = re.compile(r"open\([^)]*['\"][wax]")

# The figures §2 and the write-up publish, typed from those pages. A page edit
# and a census re-derivation are then both visible: the first by
# `TheMapAgrees`, the second by these.
PER_PROGRAM_SPLIT = [
    ("main-ec", "DAT_EXTMEM", 830, 7292),
    ("main-ec", "DAT_EXTMEM+pair-literal", 44, 490),
    ("main-ec", "pair-literal", 156, 468),
    ("main-ec", "symbol", 174, 6392),
    ("main-ec", "symbol+pair-literal", 14, 196),
    ("pd", "DAT_EXTMEM", 157, 858),
]
PER_PROGRAM_TOTAL = (1375, 15696)

UNION_SPLIT = [
    ("main-ec", "DAT_EXTMEM", 800, 7062),
    ("main-ec", "DAT_EXTMEM+pair-literal", 41, 385),
    ("main-ec", "pair-literal", 155, 461),
    ("main-ec", "symbol", 159, 5787),
    ("main-ec", "symbol+pair-literal", 14, 196),
    ("both", "DAT_EXTMEM", 30, 312),
    ("both", "DAT_EXTMEM+pair-literal", 4, 139),
    ("both", "symbol+DAT_EXTMEM", 15, 751),
    ("pd", "DAT_EXTMEM", 108, 603),
]
UNION_TOTAL = (1326, 15696)

# §2's three-way partition of the main EC, per program and on the union key.
#
# **The three terms are not pinned here.** The `named` term has moved on every
# one of issues #649, #635 and #338 and again on this one, always by the same
# mechanism and never because the partition rule changed: a re-export carries
# symbol renames the committed `.c` had not caught up to, and each renamed
# address moves off `DAT_EXTMEM` and onto `named`. A tuple of those three
# numbers was therefore a value every branch whose export renames anything has
# to edit -- a count of this repository's own decompiled text, and the shape
# `CLAUDE.md` names under "no hand-kept totals".
#
# Nothing is lost by dropping it. Every property the tuple stood in for is
# already asserted by `--check`, which this suite runs in
# `TheToolChecksTheRelations`: that each partition places every main-EC row,
# that its three terms sum to the main EC's distinct address count, and that the
# two keyings differ in the pair-literal term by exactly the addresses whose
# bucket moves. What the tool cannot see is the markdown beside it, and that is
# what `TheMapAgrees` and `ThePublishedFigures` are for;
# `check_census_figures.py --print` prints the figures themselves for a reader
# who wants them.

# The one address whose partition bucket moves, and the two directions. Held by
# address rather than by count, and it is the claim: the two keyings disagree
# about this one address and no other.
MOVED = [("0x04A3", "DAT_EXTMEM", "pair-only")]


def section_two(text):
    """§2's text, from its heading to the next `## ` one.

    Found by heading rather than by line number on purpose: a checker that
    pinned its own section's line numbers would be invalidated by exactly the
    class of edit it exists to catch, and the map's §2 grew a table under this
    change.
    """
    start = text.index("\n## 2. ")
    end = text.index("\n## 3. ", start)
    return text[start:end]


def markdown_rows(text, header):
    """Every `| a | b | n | n |` row under `header`, as (a, b, n, n).

    The header is matched exactly rather than by position, because §2 prints
    two tables with the same shape and the pair is the whole point: the
    per-program one is headed `program | spelling` and the union one
    `program | spelled_as`. Matching on the wrong one would compare the union
    table against the per-program figures and fail for a reason that has nothing
    to do with either.

    Cells are stripped of the emphasis markdown and the backticks, so a table
    that starts bolding its cells is the same table. The header is looked for
    *before* the blank-cell and rule rows are skipped, because a header row is
    neither -- skipping first is what made an earlier version of this function
    return nothing at all for a table that was present and correct.
    """
    rows, seen = [], False
    for line in text.splitlines():
        if not line.startswith("|"):
            # A non-table line ends the table. Without this the parser would
            # keep collecting into the next table on the page and the two §2
            # prints would arrive as one list.
            if rows:
                break
            continue
        cells = [c.strip().strip("*").strip().strip("`").strip()
                 for c in line.strip().strip("|").split("|")]
        if not seen:
            seen = [c.strip("`*").strip() for c in cells] == header
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(tuple(cells[:2]) + tuple(
            int(c.replace(",", "")) for c in cells[2:]))
    return rows


def blockquote(text, first_words):
    """The `>` block whose first line contains `first_words`, as its integers.

    Joined across the block's lines rather than read off the first one: the
    quoted sentence wraps, and taking only the line that matched made the count
    of figures depend on where the wrap fell, which is a line number a reflow
    would move.

    `§N` references are stripped before the figures are read, for the reason
    `check_doc_figure_pins.py` gives for stripping them there: §4.7 is a
    cross-reference, not a claim about how many addresses anything reaches, and
    a reader who counted it as a figure would be right about the prose and
    wrong about the partition.
    """
    block, taking = [], False
    for line in text.splitlines():
        if line.startswith(">"):
            if taking:
                block.append(line)
            elif first_words in line:
                taking = True
                block.append(line)
        elif taking:
            break
    if not taking:
        raise AssertionError(f"no blockquote containing {first_words!r} in §2")
    joined = re.sub(r"§\s*[\d.]+[a-z]?", " ", " ".join(block))
    return tuple(int(n.replace(",", ""))
                 for n in re.findall(r"\b\d[\d,]*\b", joined))


def console_pairs(text, containing):
    """The `$ ` commands of the console block holding `containing`, each with
    the lines printed under it.

    Keyed on a substring of the block rather than on its position or its first
    command: the write-up's other blocks hold `awk` programs written across
    several lines, so a `$ ` line inside one of those is a fragment of a
    command rather than one. A block chosen by index would run half an `awk`
    program and fail for a reason that has nothing to do with the transcript.

    A command with nothing printed under it is still returned, with an empty
    output, so a `$ ` line that lost its figure is visible rather than dropped
    from the pairing.
    """
    body = None
    for chunk in text.split("```console")[1:]:
        block = chunk.split("```")[0]
        if containing in block:
            body = block
            break
    if body is None:
        raise AssertionError(f"no console block containing {containing!r}")
    pairs, printed = [], None
    for line in body.splitlines():
        if line.startswith("$ "):
            pairs.append((line[2:].strip(), []))
            printed = pairs[-1][1]
        elif printed is not None and line.strip():
            printed.append(line)
    return [(command, "\n".join(out)) for command, out in pairs]


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, check=False)


class TheToolChecksTheRelations(unittest.TestCase):
    """`--check` and `--self-test`, over the committed CSV and over fixtures.

    The gate that runs these is `bash tools/run-tests.sh`, not
    `.github/scripts/agent-gates.sh`: the agent-push token has no `workflow`
    scope, so a branch that edits the gate fails at the end rather than the
    start, and this is how `check_doc_figure_pins.py` and
    `check_pin_table_rows.py` are covered today.
    """

    def test_check_passes_against_the_committed_csv(self):
        proc = run("--check")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("FAIL", proc.stdout)

    def test_self_test_passes(self):
        proc = run("--self-test")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("FAIL", proc.stdout)

    def test_the_bare_run_prints_both_keyings_under_one_provenance_line(self):
        proc = run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.count("<!-- source:"), 1)
        self.assertIn("sha256", proc.stdout)
        # The SHA-256 is of the bytes the numbers came from, so it is derived
        # rather than transcribed: a page holding a stale digest would not pass
        # `TheMapAgrees`, and one holding a mis-derived one would not pass here.
        digest = re.search(r"sha256 ([0-9a-f]{64})", proc.stdout).group(1)
        self.assertEqual(digest,
                         hashlib.sha256(REGISTERS.read_bytes()).hexdigest())

    def test_check_fails_on_a_census_that_no_longer_reconciles(self):
        # A scratch CSV whose `refs_main_ec` column has been short by one on a
        # single row: every published figure still adds up and only the
        # relation between the two reference columns fails, which is the shape
        # a regeneration bug would have and the shape a hard-coded total would
        # not have caught.
        rows = keyed.read_rows(REGISTERS)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.csv"
            header = ("addr,program,spelled_as,refs,spellings_by_program,"
                      "refs_main_ec,refs_pd").split(",")
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=header,
                                        extrasaction="ignore")
                writer.writeheader()
                for index, row in enumerate(rows):
                    short = dict(row)
                    if index == 0:
                        short["refs_main_ec"] = str(
                            int(row["refs_main_ec"]) - 1)
                    writer.writerow(short)
            proc = subprocess.run(
                [sys.executable, str(TOOL), "--check", "--registers", str(path)],
                capture_output=True, text=True, check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("FAIL", proc.stdout)

    def test_check_fails_on_a_csv_naming_an_undeclared_program(self):
        rows = keyed.read_rows(REGISTERS)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "third-program.csv"
            header = ("addr,program,spelled_as,refs,spellings_by_program,"
                      "refs_main_ec,refs_pd").split(",")
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=header,
                                        extrasaction="ignore")
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
                # A second main-EC-only image, which the report cannot print a
                # reference column for and must therefore refuse rather than
                # quietly total over.
                writer.writerow({
                    "addr": "0xFFFF", "program": "both", "spelled_as": "DAT_EXTMEM",
                    "refs": 2, "spellings_by_program": "main-ec=DAT_EXTMEM;ps2=DAT_EXTMEM",
                    "refs_main_ec": 2, "refs_pd": 0})
            proc = subprocess.run(
                [sys.executable, str(TOOL), "--check", "--registers", str(path)],
                capture_output=True, text=True, check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("undeclared", proc.stdout)


class TheToolWritesNothing(unittest.TestCase):
    """The same standing `test_xdata_guard_off_row_join.py` holds.

    Every mode here reports; none of them may write, because the census CSVs
    are committed and a report that measured the census by regenerating it is a
    report one argument away from overwriting the input it is reading.
    """

    def test_no_write_mode_in_the_source(self):
        source = TOOL.read_text(encoding="utf-8")
        self.assertIsNone(WRITE_OPEN.search(source),
                          "the tool opens a file for writing")

    def test_no_output_argument_over_the_argument_parser(self):
        # Over the parser rather than the docstring, which names `--out-` and
        # the write modes to say there are none: a grep over the prose would
        # read its own explanation as the thing it forbids. The scope is
        # `main()` and below, so a module constant cannot satisfy it either.
        source = TOOL.read_text(encoding="utf-8")
        parser = source[source.index("def main()"):]
        for flag in ("--write", "--out", "--out-registers", "--out-csv"):
            self.assertNotIn(f'"{flag}"', parser,
                             f"{flag} would give this tool a way to touch the "
                             f"committed census")

    def test_a_full_run_leaves_the_tree_byte_identical(self):
        before = self._status()
        for mode in ([], ["--check"], ["--self-test"], ["--moved"]):
            self.assertEqual(run(*mode).returncode, 0, mode)
        self.assertEqual(self._status(), before)

    @staticmethod
    def _status():
        proc = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                              capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise unittest.SkipTest("git is not available here")
        return proc.stdout


class ThePublishedFigures(unittest.TestCase):
    """The committed CSV still says what §2 and the write-up say it says.

    Constants typed from the pages, compared against a derivation from the
    committed CSV — the distinction `test_xdata_guard_off_row_join.py` records
    from #753. A re-derivation that moved the census makes these red, and that
    is the point: the pages have to be re-measured with it, which is what
    `TheMapAgrees` then makes mechanical.
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = keyed.read_rows(REGISTERS)

    def test_the_per_program_split(self):
        counts, refs = keyed.per_program_split(self.rows)
        self.assertEqual(
            [(k[0], k[1], counts[k], refs[k]) for k in sorted(counts)],
            sorted(PER_PROGRAM_SPLIT))
        self.assertEqual((sum(counts.values()), sum(refs.values())),
                         PER_PROGRAM_TOTAL)

    def test_the_union_split(self):
        counts, refs = keyed.union_split(self.rows)
        self.assertEqual(
            [(k[0], k[1], counts[k], refs[k]) for k in sorted(counts)],
            sorted(UNION_SPLIT))
        self.assertEqual((sum(counts.values()), sum(refs.values())), UNION_TOTAL)

    def test_the_two_totals_differ_by_the_both_rows_and_nothing_else(self):
        # The identity the page states as "1,375 is 1,326 + 49". Asserted as a
        # relation and not as a typed 1,375, because the per-program total is a
        # value a re-derivation moves and `both` is a value it moves with it.
        per, _ = keyed.per_program_split(self.rows)
        union, _ = keyed.union_split(self.rows)
        both = sum(1 for r in self.rows if r["program"] == "both")
        self.assertEqual(sum(per.values()) - sum(union.values()), both)

    def test_one_address_and_one_only_changes_partition_term(self):
        # The pair-literal disagreement between the two keyings, pinned to the
        # address that causes it. Held by value because the *address* is the
        # claim; the two counts that move with it are not asserted anywhere,
        # and `--check` already asserts they differ by exactly this many rows.
        moves = [(a, was, now) for a, was, now, _, _ in keyed.bucket_moves(self.rows)]
        self.assertEqual(moves, MOVED)

class TheMapAgrees(unittest.TestCase):
    """§2's tables, its partition blockquote and its shell transcripts, read
    back out of the pages beside the tool.

    `--check` asserts relations inside one derivation and cannot see the
    markdown beside it, so a page edit that changes a cell, drops a row or
    restores a superseded figure passes every gate in the tree. This class is
    that gap closed, and it is why the suite is more than the tool's own two
    modes run twice. The two transcripts are here for the same reason: a figure
    printed under a command a reader can paste is a claim about the committed
    tree, and holding it means re-running the command.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = section_two(MAP.read_text(encoding="utf-8"))

    def test_the_per_program_table_is_the_first_one_and_holds(self):
        rows = markdown_rows(self.text, ["program", "spelling",
                                         "distinct", "references"])
        self.assertEqual(
            [(program, spelling, distinct, refs)
             for program, spelling, distinct, refs in rows],
            PER_PROGRAM_SPLIT + [("total", "", PER_PROGRAM_TOTAL[0],
                                  PER_PROGRAM_TOTAL[1])],
            "§2's per-program table has drifted from the committed CSV")

    def test_the_union_table_is_the_second_one_and_holds(self):
        rows = markdown_rows(self.text, ["program", "spelled_as",
                                         "distinct", "references"])
        self.assertEqual(
            [(program, spelling, distinct, refs)
             for program, spelling, distinct, refs in rows],
            UNION_SPLIT + [("total", "", UNION_TOTAL[0], UNION_TOTAL[1])],
            "§2's union table has drifted from the committed CSV")

    def test_the_per_program_table_comes_first(self):
        # Order is the claim being made — the per-program reading is the one the
        # section is argued from — and a table swap would leave both tables'
        # contents right.
        self.assertLess(self.text.index("| program | spelling |"),
                        self.text.index("| `program` | `spelled_as` |"))

    def test_the_partition_blockquote_holds_the_per_program_reading(self):
        # The quoted sentence is §2's restatement of the issue's claim, so it
        # has to be the reading the per-program table supports: 172 named of
        # 1,218, the other 1,046 split 890 / 156. The order of the figures is
        # the order the sentence reads them in, which is the only thing that
        # makes the tuple below mean anything. It moved off 167 / 1,051 / 895
        # in issue #1425, when `0x04A2` left the `DAT_EXTMEM` term for
        # `symbol`; §2's correction block beside the superseded figures says so
        # and attributes four of the five addresses to #333 and #573.
        named, total, other, extmem, pair = blockquote(
            self.text, "of the 1,218 XDATA addresses")
        self.assertEqual((named, total, other, extmem, pair),
                         (175, 1218, 1043, 887, 156))
        self.assertEqual(named + other, total)
        self.assertEqual(extmem + pair, other)

    def test_the_rekey_did_not_retract_a_superseded_figure(self):
        # The calibration rule is the reason §2 keeps its history, so the
        # versions the re-key sits beside must still be there: a well-meaning
        # tidy-up that deleted them would pass every other check here.
        for figure in ("1,171", "14,819", "1,172", "14,801", "147", "6,201",
                       "41", "448", "161", "902", "155", "6,416", "1,057",
                       "6,337", "6,468"):
            self.assertIn(figure, self.text,
                          f"§2 no longer carries {figure} visibly")
        # And the corrections that replace them are dated and attributed, not
        # bare replacements.
        self.assertIn("*(Correction, 2026-09-30, issue #714.", self.text)
        # The two stale cells are named as wrong, not silently overwritten.
        self.assertIn("822 / 7,334", self.text)
        self.assertIn("137 / 5,515", self.text)

    def test_the_cpu_temp_transcript_is_the_one_the_tree_prints_now(self):
        # §2's opening claim is a shell transcript, so it is re-runnable, and a
        # transcript that no longer reproduces is evidence that has gone stale
        # under a reader without anybody noticing a table had moved. Held by
        # re-running the two commands rather than by holding the number, which
        # is the whole reason §2 shows them.
        tree = REPO / "ec" / "decompiled"
        hit = subprocess.run(["grep", "-n", "CPU_TEMP", "bank0/8749.c"],
                             cwd=tree, capture_output=True, text=True, check=False)
        third = hit.stdout.splitlines()[2]
        mentions = subprocess.run(
            "grep -rhoE '\\bCPU_TEMP\\b' common/*.c bank0/*.c bank1/*.c | wc -l",
            cwd=tree, shell=True, capture_output=True, text=True, check=False)
        count = mentions.stdout.strip()
        console = self.text.split("```console")[1].split("```")[0]
        self.assertIn(third, console)
        self.assertRegex(console, rf"\|\s*wc -l\n{count}\n",
                         f"the transcript says {count} mentions but the "
                         f"committed tree prints {count}")
        # The `DAT_EXTMEM_043e` half of the sentence is a negative claim about
        # the same three trees, so it is re-run rather than trusted too.
        # `-l` and not `-c`: `-c` prints `file:0` for every clean file, so a
        # count-based check reads a tree with no matches as a tree full of them.
        stale = subprocess.run(
            "grep -rl 'DAT_EXTMEM_043e' common bank0 bank1 || true",
            cwd=tree, shell=True, capture_output=True, text=True, check=False)
        self.assertEqual(stale.stdout.split(), [],
                         "a DAT_EXTMEM_043e spelling appeared in the EC tree")

    def test_the_row_counts_the_map_still_prints_stay_row_counts(self):
        # The two 1,326s that are *not* program-addresses, and the header rule
        # that says which is which. Both count CSV rows, so the re-key must
        # leave them alone; a change here would be the re-key claiming a
        # figure it does not own.
        text = MAP.read_text(encoding="utf-8")
        self.assertIn("0 of 1,326 addresses", text)
        self.assertIn("the 1,326 register rows", text)

    def test_the_writeup_shell_transcript_still_reproduces(self):
        # The write-up's four shell one-liners are the same *kind* of claim as
        # §2's `CPU_TEMP` transcript: a command and the figure it prints, so a
        # reader can re-run it instead of taking the page's word for it. One of
        # the four was wrong once — `NR - 1` undercounts a stream `tail` has
        # already shortened, and it printed 1325 under a 1326 — and nothing in
        # the tree noticed, so the block is re-run rather than held by the
        # figures it prints.
        pairs = console_pairs(WRITEOUT.read_text(encoding="utf-8"), "{s+=$6}")
        # Four, because a `$ ` line quietly dropped from the block would leave
        # the survivors reproducing and the page one figure short. The count is
        # of this block and not of the tree, so no landing branch bumps it.
        self.assertEqual(len(pairs), 4,
                         "the four-command transcript is not four commands")
        for command, printed in pairs:
            hit = subprocess.run(command, cwd=REPO, shell=True,
                                 capture_output=True, text=True, check=False)
            self.assertEqual(
                hit.stdout.strip(), printed.strip(),
                f"the transcript no longer reproduces:\n"
                f"  $ {command}\n"
                f"  the page prints {printed!r}, the committed tree prints "
                f"{hit.stdout.strip()!r}")

    def test_the_writeup_and_the_index_are_present(self):
        self.assertTrue(WRITEOUT.exists(),
                        "the write-up for this change is missing")
        index = (REPO / "docs" / "findings" / "INDEX.md").read_text(
            encoding="utf-8")
        self.assertIn("xdata-register-map-per-program-keying.md", index,
                      "docs/findings/INDEX.md is stale; run "
                      "python3 ec/tools/gen_findings_index.py")


if __name__ == "__main__":
    unittest.main()
