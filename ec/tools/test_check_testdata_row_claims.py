#!/usr/bin/env python3
"""Offline checks for check_testdata_row_claims.py: committed files only.

The tool is a pointer-checker, so its failure mode is silence rather than a
crash. Loosen a shape rule and it stops counting the literals it should be
passing over while still exiting 0, and the only thing that notices is a
reader who has already been misled -- which is how the index needed hand-repair
twice, in #502 and #720, with no check reading that column either time. So what
is pinned here is the line between what the tool claims and what it declines
to check, from both sides: each rule that makes it strict, each of the five
shapes and the two dated refusals that make it conservative, and then
**each of the nine rules dropped in turn** -- eight of them asserted to make
the run check *more* and the ninth, the dated-capture resolution, in the other
direction, because a rule that stops changing the answer has stopped
mattering, whichever way the answer moves, and that is the same defect in the
suite as a check that stops firing.

The descriptions are written inline rather than stored beside the tree, and
that is the same reason the sibling suite keeps its prose inline: a sentence
naming a fixture and claiming an address in it is exactly what this tool
flags, so committing one under `ec/` would make the committed-tree case red by
construction. What the scratch cases check *against* is real text on disk --
the fixtures beside the scratch index, and the captures beside them -- so the
presence read is exercised rather than stubbed. The last class is the
committed tree itself, and it asserts the run reached something rather than any
figure it reached.
"""
import collections
import contextlib
import csv
import importlib.util
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).parent
# The tool imports its walker from check_cluster_citations and its token reader
# from check_testdata_index, the way check_capture_claims imports
# check_cluster_citations; loading both by path is no different from running
# them, and the directory is the same sys.path entry.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_testdata_row_claims', HERE / 'check_testdata_row_claims.py')
ctrc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctrc)
spec = importlib.util.spec_from_file_location(
    'check_testdata_index', HERE / 'check_testdata_index.py')
ctdi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctdi)

# The header a scratch index needs to be read as the `File` table. The `Feeds`
# cell is never resolved here -- that column is check_testdata_index.py's, and
# this suite is not about it -- so every scratch row carries the same one.
HEADER = '| File | Feeds | What it constructs |\n| --- | --- | --- |\n'
FEEDS = '`../grade_0751_isolation.py`'

# A change-log fixture in the schema the real ones use, with the `constructed`
# header and the placeholder timestamp that keeps a fixture from being
# mistaken for a capture at a glance.
CSV_HEADER = ('# CONSTRUCTED INPUT, NOT A CAPTURE. No EC was read to make this\n'
              '# file; every byte below was written by hand.\n'
              'time,addr,old,new\n')


def a_csv(*addresses):
    """One change-log fixture carrying `addresses` and nothing else."""
    rows = "".join(f"2026-01-01T12:02:00,0x{a:04X},0x00,0x01\n"
                   for a in addresses)
    return CSV_HEADER + rows


class ScratchIndex:
    """A throwaway `testdata/`, its `ec-watch/`, and the index that describes
    them.

    One cell per row, because a case here is about a sentence, and a second
    row would only be a second thing to keep true. `note` is the third column
    verbatim, which is the point: the cell is the unit under test, not a
    paraphrase of it. The second root is `evidence/ec-watch/`, where a
    sentence naming a dated capture is resolved, and it is empty in every case
    that is not about one -- which is itself the point of the near-miss cases,
    since a backticked date has to stay about the row's own fixture whether or
    not a capture of that date exists beside it.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.testdata = os.path.join(self.root, "testdata")
        self.captures = os.path.join(self.root, "ec-watch")
        os.mkdir(self.testdata)
        os.mkdir(self.captures)
        self.rows = []

    def write(self, rel, text='', root=None):
        """Create `rel` under the scratch `testdata/` (or `root`), parents
        and all."""
        path = os.path.join(root or self.testdata, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def row(self, cell, note):
        """Add one table row naming `cell` and describing it with `note`."""
        self.rows.append(f'| `{cell}` | {FEEDS} | {note} |')
        return self

    def set(self, rel, *addresses):
        """Write a change-log fixture at `rel` carrying `addresses`."""
        return self.write(rel, a_csv(*addresses))

    def capture(self, rel, *addresses):
        """Write a change-log capture at `rel` under the scratch `ec-watch/`.

        The same schema as a fixture, deliberately: the tool reads both as
        text, and a capture written in a schema of its own would be testing a
        reader no committed file exercises.
        """
        return self.write(rel, a_csv(*addresses), root=self.captures)

    def header_capture(self, rel, *addresses, rows=()):
        """A capture naming `addresses` in its `#` header block.

        `rows` are written as real `addr` rows, so a case can put an address
        in the header alone, in the rows alone, or in both. A header mention
        is not a row, and that is the whole distinction a columnar read turns
        on. The header is a real shape rather than a contrived one:
        `read_capture()` drops `#` lines before it reads the header precisely
        because `2026-09-18-ac-plugin-sweep-summary.csv` opens with three.
        """
        head = "".join(f"# page swept at 0x{a:04X}\n" for a in addresses)
        return self.write(rel, head + a_csv(*rows), root=self.captures)

    def txt_capture(self, rel, text):
        """An `ecrw.py dump` capture: text, with no column to read."""
        return self.write(rel, text, root=self.captures)

    def check(self):
        """The tool's `Result` for this scratch tree.

        The index is written to disk rather than handed in, because the tool
        reads it from `testdata/README.md` and a case that bypassed that would
        be testing a reader no run ever uses. The capture root is handed in
        for the same reason: it is the other tree, and a case that could not
        point the tool at a scratch one would be a case about the committed
        captures only.
        """
        self.write("README.md", HEADER + "".join(r + "\n" for r in self.rows))
        return ctrc.check(self.testdata, captures=self.captures)

    def verdicts(self):
        """{address: verdict} for this scratch tree, checked reading order.

        A dict rather than a list because a case that cares about *which*
        addresses were read should not also have to state the order, and a cell
        that names the same byte twice is a real shape in the committed index.
        """
        return collections.OrderedDict(
            (c.address, c.verdict) for c in self.check().claims)

    def shapes(self):
        """{address: the shape that passed it over}, checked reading order."""
        return collections.OrderedDict(
            (c.address, c.reason) for c in self.check().claims if c.reason)


class ReportsRealDrift(ScratchIndex, unittest.TestCase):
    """The strict half: what the tool is for, and the reading the issue
    conditions it on -- across the files a row names, never per file."""

    def test_a_claim_no_file_the_row_names_carries_is_missing(self):
        self.set("example.csv", 0x07C4)
        self.row("example.csv", "`0x07D0` steps up inside one window.")
        result = self.check()
        self.assertEqual(self.verdicts(), {"0x07D0": "missing"})
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ctrc.report(result), 1)

    def test_the_report_names_the_row_the_address_and_the_fixture(self):
        self.set("example.csv", 0x07C4)
        self.row("example.csv", "`0x07D0` steps up inside one window.")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            ctrc.report(self.check())
        line = err.getvalue().splitlines()[0]
        self.assertIn("row 1", line)
        self.assertIn("example.csv", line)
        self.assertIn("0x07D0", line)

    def test_the_search_is_over_the_union_of_the_rows_files(self):
        # The issue's own example, and the condition it puts on the whole
        # direction: `0x075B` occurs 16 times in ONE of
        # `0751-isolation-run-staged/`'s three CSVs and in neither of the other
        # two, while the row names the directory. A per-file reading fails a
        # row that is true today.
        self.set("staged/0700-07ff.csv", 0x075B)
        self.set("staged/0400-045f.csv", 0x0402)
        self.set("staged/0f00-0f5f.csv", 0x0F0A)
        self.row("staged/*.csv", "The `0x075B` rows are placed on either side "
                                 "of the `watch over` mark.")
        self.assertEqual(self.verdicts(), {"0x075B": "resolved"})

    def test_the_same_claim_over_one_file_of_the_three_is_missing(self):
        # The other half of the union case, and what makes the one above a rule
        # rather than a coincidence: a row that names the single CSV without
        # the byte in it is a real disagreement, not a glob artefact.
        self.set("staged/0700-07ff.csv", 0x075B)
        self.set("staged/0400-045f.csv", 0x0402)
        self.row("staged/0400-045f.csv", "The `0x075B` rows are placed on "
                                         "either side of the mark.")
        self.assertEqual(self.verdicts(), {"0x075B": "missing"})

    def test_the_discrimination_the_two_3blocks_rows_claim(self):
        # `3blocks/` carries no `0x0784` row and `3blocks-moved/` carries one,
        # which is the whole difference between the two rows the index makes,
        # and the reason the union rule is not a licence to read any file in
        # the tree.
        self.set("3blocks/0700-07ff.csv", 0x0402)
        self.set("3blocks-moved/0700-07ff.csv", 0x0402, 0x0784)
        self.row("3blocks/*.csv", "Every byte lands in the right window.")
        self.row("3blocks-moved/*.csv", "**One `0x0784` row added** inside "
                                        "block 1's write window.")
        self.assertEqual(self.verdicts(), {"0x0784": "resolved"})


class SkipsDeliberately(ScratchIndex, unittest.TestCase):
    """The five shapes, the two dated refusals, and the entry predicate,
    each as a case saying so.

    Every one of them would otherwise report a row which is true today, and a
    skip that is not deliberate is the bug. Each rule gets both halves where
    it has one: the shape is passed over, and the near-miss that looks like it
    is still checked.
    """

    def test_a_range_starting_on_a_page_boundary_names_a_page(self):
        # The corpus writes its three sweep ranges by their page start and the
        # narrow runs inside the page by their first byte, and the page
        # boundary is what tells them apart. `0x043E` and `0x044F` in the same
        # sentence are the other half: mid-page, named as bytes, and checked.
        self.set("example.csv", 0x07C4, 0x043E, 0x044F)
        self.row("example.csv", "the candidate bytes in the `0x0700-0x07FF` "
                                "capture, `0x043E`/`0x044F` in the "
                                "`0x0400-0x045F` one.")
        self.assertEqual(self.shapes(), {"0x0700": "capture/window bound",
                                         "0x07FF": "capture/window bound",
                                         "0x0400": "capture/window bound",
                                         "0x045F": "capture/window bound"})
        self.assertEqual(self.verdicts(), {"0x0700": "unresolved",
                                           "0x07FF": "unresolved",
                                           "0x043E": "resolved",
                                           "0x044F": "resolved",
                                           "0x0400": "unresolved",
                                           "0x045F": "unresolved"})

    def test_a_mid_page_range_is_still_a_claim(self):
        self.set("example.csv", 0x0F5D, 0x0F5F)
        self.row("example.csv", "The `0x0F5D-0x0F5F` mailbox poke as three "
                                "change rows inside the write window.")
        self.assertEqual(self.verdicts(), {"0x0F5D": "resolved",
                                           "0x0F5F": "resolved"})

    def test_a_bare_page_address_the_sentence_calls_a_capture_is_a_page(self):
        # Row 18's own sentence, and the reading the two ranges above cannot
        # reach: three bare page-aligned addresses, none of which bounds
        # anything, and the word `capture` is behind the second of them.
        self.set("example.csv", 0x0751, 0x0F0A)
        self.row("example.csv", "byte for byte in the `0x0700` and `0x0400` "
                                "captures, with the mark missing from the "
                                "`0x0F00` capture — its `0x0F0A` row is the "
                                "control arm's own movement.")
        self.assertEqual(self.shapes(), {"0x0700": "capture/window bound",
                                         "0x0400": "capture/window bound",
                                         "0x0F00": "capture/window bound"})
        self.assertEqual(self.verdicts()["0x0F0A"], "resolved")

    def test_a_page_address_nobody_calls_a_capture_is_still_a_claim(self):
        # The other half of the rule above, and what keeps the page word from
        # being a hole: page alignment on its own does not excuse a literal.
        self.set("example.csv", 0x0400)
        self.row("example.csv", "The `0x0400` byte steps up inside one window.")
        self.assertEqual(self.verdicts(), {"0x0400": "resolved"})

    def test_a_two_token_span_is_a_watched_set_and_not_a_range(self):
        # The corpus writes a byte range as one token and a set as two, and a
        # set the grader watches is not a byte the fixture holds.
        self.set("example.csv", 0x07C4)
        self.row("example.csv", "The ACPI half (`0x07C4`-`0x07D7`) leading "
                                "the host half in both windows.")
        self.assertEqual(self.shapes(), {"0x07C4": "watched-set span",
                                         "0x07D7": "watched-set span"})

    def test_a_one_token_range_of_the_same_addresses_is_a_range(self):
        # The contrast that makes the rule a rule rather than a guess: the
        # same two addresses written as one token are bytes, and are held.
        self.set("example.csv", 0x07C4, 0x07D7)
        self.row("example.csv", "Differing at `0x07C4-0x07D7` and at nothing "
                                "else.")
        self.assertEqual(self.verdicts(), {"0x07C4": "resolved",
                                           "0x07D7": "resolved"})

    def test_a_denial_naming_the_addresses_is_skipped(self):
        # Row 9's own sentence, the sharpest of the two spellings: the denial
        # takes the literals as its object, and the inventory of what the file
        # *has* in the same sentence is still checked. `0x0746` is the address
        # the backward reach of a proximity window would take with it.
        self.set("example.csv", 0x07C4, 0x07C6, 0x0743, 0x0745, 0x0746)
        self.row("example.csv", "A log in the committed `2026-01-01` file's "
                                "shape — the two `0x07C4` writes, a `0x07C6` "
                                "run, the `0x0743`/`0x0745`/`0x0746` plug-in "
                                "sweep — and **no row at all for `0x07D4` or "
                                "`0x07D5`**.")
        self.assertEqual(self.shapes(), {"0x07D4": "denial",
                                         "0x07D5": "denial"})
        self.assertEqual(self.verdicts(), {"0x07C4": "resolved",
                                           "0x07C6": "resolved",
                                           "0x0743": "resolved",
                                           "0x0745": "resolved",
                                           "0x0746": "resolved",
                                           "0x07D4": "unresolved",
                                           "0x07D5": "unresolved"})

    def test_a_trailing_denial_skips_the_literal_it_denies(self):
        # Row 23's own sentence, in the other spelling: the phrase denies the
        # clause in front of it, so the direction is the other way. `0x0784`
        # is a row in a *copy* of the set, which is the whole claim.
        self.set("example.csv", 0x0402)
        self.row("example.csv", "It is reached only over a copy of this set "
                                "with one `0x0784` row added, not by a "
                                "committed run.")
        self.assertEqual(self.shapes(), {"0x0784": "denial"})

    def test_a_disclaimer_about_the_future_is_not_a_denial(self):
        # "not a prediction" is about the future and says nothing about the
        # fixture, so the address it names is still a claim. Both door rows
        # close on a sentence in this shape, and reading it as a denial would
        # have dropped half of row 12's claims.
        self.set("example.csv", 0x07D0)
        self.row("example.csv", "It is *not* a prediction that the host half "
                                "leads, or that `0x07D0` moves at all.")
        self.assertEqual(self.verdicts(), {"0x07D0": "resolved"})

    def test_a_dump_command_argument_is_not_a_claim(self):
        # Row 22's own sentence: two arguments to `ecrw.py`, and the page the
        # command was a short dump of rather than the whole of.
        self.set("example.csv", 0x0751)
        self.row("example.csv", "The four dumps are a short "
                                "`ecrw.py dump 0x0750 0x0010` around `0x0751` "
                                "rather than the whole `0x0700` page.")
        self.assertEqual(self.shapes(), {"0x0750": "dump-command argument",
                                         "0x0010": "dump-command argument",
                                         "0x0700": "capture/window bound"})
        self.assertEqual(self.verdicts()["0x0751"], "resolved")

    def test_a_mark_label_is_not_a_command(self):
        # The sharp edge of the rule above: the label has a space in it too,
        # and what tells the two apart is that it does not name a tool. Row
        # 25's claim is of this shape and is about a byte in the file.
        self.set("example.csv", 0x0751)
        self.row("example.csv", "the 12:00 one is spelled `restored "
                                "0x0751=0x0a` in the `0x0700` capture.")
        self.assertEqual(self.verdicts()["0x0751"], "resolved")

    def test_a_firmware_code_address_is_not_a_byte(self):
        # Row 8's own sentence. `0x888D` is the §6 handler in the EC image and
        # is in `ghidra-functions.csv`; the filter has to be that census minus
        # `xdata-registers.csv`, because the annotation index holds `0x07D0` as
        # a function entry too and the door byte is a claim.
        self.set("example.csv", 0x0F5D, 0x0F5F, 0x07D0)
        self.row("example.csv", "differing at `0x0F5D-0x0F5F` **only**, and "
                                "holding a selector the handler at `0x888D` "
                                "requires, with `0x07D0` among the hits.")
        self.assertEqual(self.shapes(), {"0x888D": "firmware code address"})
        self.assertEqual(self.verdicts(), {"0x0F5D": "resolved",
                                           "0x0F5F": "resolved",
                                           "0x888D": "unresolved",
                                           "0x07D0": "resolved"})

    def test_a_bare_date_resolves_and_its_literals_are_the_captures(self):
        # Row 7's own sentence, and the case #794 was filed about: the two
        # literals are `resolved` **against the capture**, and the row's own
        # fixture carries neither, so the run is green only because the date
        # was resolved. An implementation that ignored the date and held the
        # sentence to the row's own files would report two misses here, and
        # saying so is the point of the case.
        self.set("example.csv", 0x0F5D)
        self.capture("2026-09-23-cycle-0f00-0f5f.csv", 0x0F58, 0x0F5C)
        self.row("example.csv", "is the shape the 2026-09-23 power-mode-cycle "
                                "capture shows, where they track "
                                "`0x0F58-0x0F5C`.")
        self.assertEqual(self.shapes(), {})
        self.assertEqual(self.verdicts(), {"0x0F58": "resolved",
                                           "0x0F5C": "resolved"})
        # And the claim names what it was held to, so a reader of the report
        # cannot mistake a dated claim for one about the row's own cell.
        self.assertEqual({c.files for c in self.check().claims},
                         {"2026-09-23-*"})

    def test_a_dated_claim_is_not_also_the_rows_own(self):
        # The other half of the rule, and the one that makes "instead of"
        # mean something. The row's own fixture *does* carry `0x0F58` and the
        # capture of the date does not, so the union the issue forbade would
        # report this as resolved where this reading reports the one
        # disagreement the tool can raise. It is the case that makes the fix
        # able to fail, and it is why a dated `missing` needed no wording of
        # its own: a false claim in a dated sentence is a defect in the
        # index's prose about a fixture exactly as one in an undated sentence
        # is.
        self.set("example.csv", 0x0F58)
        self.capture("2026-09-23-cycle-0f00-0f5f.csv", 0x0F5C)
        self.row("example.csv", "is the shape the 2026-09-23 power-mode-cycle "
                                "capture shows, where they track "
                                "`0x0F58-0x0F5C`.")
        self.assertEqual(self.verdicts(), {"0x0F58": "missing",
                                           "0x0F5C": "resolved"})
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ctrc.report(self.check()), 1)

    def test_a_bare_date_resolving_to_nothing_is_unresolved_and_not_absent(self):
        # The other half of the whole change, and the calibration line made
        # mechanical: a date whose `<date>-*` glob is empty has no file set to
        # hold the sentence's literals to, so the answer is the one the other
        # five shapes give -- "not checked by this method", never absent --
        # and the report line names the glob that came back empty, so a reader
        # can see *which* date failed rather than only that one did.
        self.set("example.csv", 0x0F58)
        self.row("example.csv", "is the shape the 2026-01-01 power-mode-cycle "
                                "capture shows, where they track `0x0F58`.")
        self.assertEqual(self.shapes(), {"0x0F58": "dated capture not found"})
        result = self.check()
        self.assertEqual(self.verdicts(), {"0x0F58": "unresolved"})
        self.assertEqual(result.missing, 0)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctrc.report(result), 0)
        self.assertIn("2026-01-01-*", err.getvalue())
        self.assertIn("dated capture not found", err.getvalue())
        self.assertIn("not absent", err.getvalue())

    def test_a_backticked_date_is_a_file_the_comparison_is_drawn_from(self):
        # Row 9's own sentence, and the counterpart of the cases above: the
        # rule is the *spelling* of the date, and this one is load-bearing in
        # a way it was not before #794, because a capture of that date now
        # exists beside the fixture and does *not* carry these two addresses.
        # Read as a bare date they would both be misses.
        self.set("example.csv", 0x07C4, 0x07C6)
        self.capture("2026-09-23-example-0700-07ff.csv", 0x07D4)
        self.row("example.csv", "A log in the committed `2026-09-23` file's "
                                "shape — the two `0x07C4` writes and a "
                                "`0x07C6` run.")
        self.assertEqual(self.shapes(), {})
        self.assertEqual(self.verdicts(), {"0x07C4": "resolved",
                                           "0x07C6": "resolved"})

    def test_a_two_date_sentence_is_refused_rather_than_read_from_the_first(self):
        # The issue's own example, and the half of it that is a row which is
        # true today: both literals are in the **second** day's captures, so a
        # reading that takes the first match reports them `missing` and turns
        # the run red on a sentence the index states correctly. Only the second
        # date is added to the case above's own sentence, which is what makes
        # the first match the thing under test rather than the date. A
        # cross-date union is the other wrong answer and fails here too --
        # `resolved`, against a set drawn from two unrelated capture families.
        self.set("example.csv", 0x0F5D)
        self.capture("2026-09-23-cycle-0f00-0f5f.csv", 0x0F0A)
        self.capture("2026-09-24-06d6-reload-linux.csv", 0x0F58, 0x0F5C)
        self.row("example.csv", "is the shape the 2026-09-23 power-mode-cycle "
                                "capture and the 2026-09-24 plug-in sweep "
                                "show, where they track `0x0F58-0x0F5C`.")
        reason = "two dated captures in one sentence"
        self.assertEqual(self.shapes(), {"0x0F58": reason, "0x0F5C": reason})
        result = self.check()
        self.assertEqual(self.verdicts(), {"0x0F58": "unresolved",
                                           "0x0F5C": "unresolved"})
        self.assertEqual(result.missing, 0)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctrc.report(result), 0)
        self.assertIn("not absent", err.getvalue())
        # Both globs on **one** line, and the separator left open: what the
        # reader needs is that neither date was dropped, not how the two are
        # joined. A refusal that printed only the first fails here.
        self.assertTrue(
            any("2026-09-23-*" in line and "2026-09-24-*" in line
                for line in err.getvalue().splitlines()), err.getvalue())
        # And each date reaches the breakdown on its own, with its own file
        # count: the block is the one that says the run read dates at all, and
        # a date the run could not read has to be visible in it too.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ctrc.dated_report(result)
        self.assertIn("2026-09-23-* (1 capture(s)", out.getvalue())
        self.assertIn("2026-09-24-* (1 capture(s)", out.getvalue())
        # Twice each: the sentence's literals are listed under **both** dates,
        # unresolved, rather than once under whichever was read.
        self.assertEqual(out.getvalue().count("row 1 0x0F58 unresolved"), 2)
        self.assertEqual(out.getvalue().count("row 1 0x0F5C unresolved"), 2)

    def test_a_two_date_sentence_is_refused_with_its_literals_in_neither_day(self):
        # The other half, and what keeps the refusal from being a way of
        # excusing a claim that is false. A first-match reading reports these
        # two as `missing` and fails the run, which asserts the claim is wrong
        # at a sentence the tool has just said it cannot read -- and neither
        # day carrying the bytes is a fact about two capture sets rather than
        # about what the sentence claims, which is the same thing the other
        # six shapes say when they pass a literal over.
        self.set("example.csv", 0x0F5D)
        self.capture("2026-09-23-cycle-0f00-0f5f.csv", 0x0F0A)
        self.capture("2026-09-24-06d6-reload-linux.csv", 0x0F5A)
        self.row("example.csv", "is the shape the 2026-09-23 power-mode-cycle "
                                "capture and the 2026-09-24 plug-in sweep "
                                "show, where they track `0x0F58-0x0F5C`.")
        reason = "two dated captures in one sentence"
        self.assertEqual(self.shapes(), {"0x0F58": reason, "0x0F5C": reason})
        result = self.check()
        self.assertEqual(self.verdicts(), {"0x0F58": "unresolved",
                                           "0x0F5C": "unresolved"})
        self.assertEqual(result.missing, 0)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctrc.report(result), 0)
        self.assertIn(reason, err.getvalue())
        self.assertIn("not absent", err.getvalue())

    def test_two_dates_of_which_one_resolves_to_nothing_are_refused_still(self):
        # The only place the two dated reasons compete: a date that resolved
        # to nothing is a refusal of its own, and so is a sentence naming two
        # of them. What decides is the count of the dates and never what they
        # resolve to, so the empty `2026-01-01-*` is named beside the full
        # `2026-09-23-*` rather than swallowed by the reason that would have
        # applied to it alone -- and the order the two are written in does not
        # settle it either, which is why the empty one is written first.
        self.set("example.csv", 0x0F5D)
        self.capture("2026-09-23-cycle-0f00-0f5f.csv", 0x0F58, 0x0F5C)
        self.row("example.csv", "is the shape the 2026-01-01 plug-in sweep "
                                "and the 2026-09-23 power-mode-cycle capture "
                                "show, where they track `0x0F58-0x0F5C`.")
        reason = "two dated captures in one sentence"
        self.assertEqual(self.shapes(), {"0x0F58": reason, "0x0F5C": reason})
        result = self.check()
        self.assertEqual(self.verdicts(), {"0x0F58": "unresolved",
                                           "0x0F5C": "unresolved"})
        self.assertEqual(result.missing, 0)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctrc.report(result), 0)
        self.assertTrue(
            any("2026-01-01-*" in line and "2026-09-23-*" in line
                for line in err.getvalue().splitlines()), err.getvalue())
        # Each glob in the breakdown with its **own** count, so the date that
        # resolved to nothing reads as the zero it is and not as the file count
        # of the date beside it.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ctrc.dated_report(result)
        self.assertIn("2026-01-01-* (0 capture(s)", out.getvalue())
        self.assertIn("2026-09-23-* (1 capture(s)", out.getvalue())

    def test_two_digit_values_are_not_addresses(self):
        # `0x50 -> 0x28` is the value the dumps carry, `0xFD`/`0xC9` the magic,
        # `0xA0`/`0x10` the two mark values, `0x0a`/`0x99` the two spellings
        # of a mistyped one. Widening `ADDRESS` to two digits makes the
        # committed tree red on the day it lands, which is why the width is
        # four. The two that do come out are the ones the column means as
        # addresses -- the byte the mark label names, and the mailbox poke.
        sentence = ("`0x50 -> 0x28` is the move, with the `0xFD`/`0xC9` magic, "
                    "the `0xA0` and `0x10` marks, `restored 0x0751=0x0a` "
                    "against `0x99`, and `0x0F5D` in it.")
        self.assertEqual([a for a, _, _ in ctrc.literals(sentence)],
                         ["0x0751", "0x0F5D"])

    def test_a_bare_address_in_running_prose_is_not_a_claim(self):
        # The entry predicate. The index writes an address it means in
        # backticks; reading a running mention of one as a claim would be a
        # parser guessing at what the sentence is about.
        self.assertEqual(ctrc.literals("The row for 0x07D0 is the one that "
                                      "carries the byte."), [])

    def test_an_unresolved_literal_does_not_fail_the_run_and_says_not_absent(self):
        # The calibration line, made mechanical: a shape the tool cannot read
        # is "not found by this method", never "absent", and it does not fail
        # the run. The report has to say so rather than stay silent, because
        # silence is what a reader would take for agreement.
        self.set("example.csv", 0x07C4)
        self.row("example.csv", "The ACPI half (`0x07C4`-`0x07D7`) leads.")
        result = self.check()
        self.assertEqual(result.missing, 0)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctrc.report(result), 0)
        self.assertIn("not absent", err.getvalue())
        self.assertIn("watched-set span", err.getvalue())

    def test_the_dated_breakdown_names_each_literal_and_its_file_set(self):
        # The issue's "reporting each with the file it was checked against".
        # Asserted on a **scratch** tree and never as a count over the
        # committed one: the dated sentences there resolve, so an expected
        # number of them would turn every dated sentence a later PR adds into a
        # failure, which is the same trade `docs/agent-pipeline.md` records
        # against a floor. What is pinned is that the block exists, says which
        # glob, how wide the file set was, and what became of each literal.
        self.set("example.csv", 0x0F5D)
        self.capture("2026-09-23-cycle-a.csv", 0x0F58)
        self.capture("2026-09-23-cycle-b.csv", 0x0F5C)
        self.row("example.csv", "is the shape the 2026-09-23 power-mode-cycle "
                                "capture shows, where they track "
                                "`0x0F58-0x0F5C`.")
        result = self.check()
        self.assertEqual([pattern for pattern, _, _ in result.dated],
                         ["2026-09-23-*"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ctrc.dated_report(result)
        block = out.getvalue()
        self.assertIn("2026-09-23-* (2 capture(s)", block)
        self.assertIn("row 1 0x0F58 resolved", block)
        self.assertIn("row 1 0x0F5C resolved", block)

    def test_an_unresolving_date_is_listed_in_the_breakdown_too(self):
        # The other half of the block: a date that resolved to nothing still
        # appears, with its verdict and its empty file set, rather than being
        # absent from the report that says the run reached something.
        self.set("example.csv", 0x0F58)
        self.row("example.csv", "is the shape the 2026-01-01 power-mode-cycle "
                                "capture shows, where they track `0x0F58`.")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ctrc.dated_report(self.check())
        self.assertIn("2026-01-01-* (0 capture(s)", out.getvalue())
        self.assertIn("row 1 0x0F58 unresolved", out.getvalue())


class TheDatedClaimIsHeldToTheColumn(ScratchIndex, unittest.TestCase):
    """A claim about a capture is columnar, and a claim about a fixture is not.

    #975 gave the `addr`-column question an owner, and it is this tool: a
    sentence naming a dated capture is about a real capture, where the schema
    is `ts,addr,old,new` and the column *is* the question. The same reasoning
    over a fixture would be wrong -- rows 20, 22 and 25 claim mark labels,
    which are a comment-shaped way of carrying an address and have no column
    at all -- which is why this is a second reader beside the textual one and
    not a change to it.

    So these cases are the half the issue asked for and the one that can fail.
    An implementation that resolved the date and then fell back to the textual
    read would pass row 7's committed claims either way, because there the two
    readings agree, and the only thing that separates them is a capture that
    names an address somewhere a text search finds it and a column does not.
    """

    SENTENCE = ("is the shape the 2026-09-23 power-mode-cycle capture shows, "
                "where they track `{address}`.")

    def dated_row(self, address):
        """One row whose sentence names `address` and a date of its own."""
        self.set("example.csv", 0x0F5D)
        return self.row("example.csv", self.SENTENCE.format(address=address))

    def test_a_header_mention_is_not_a_row_and_the_claim_is_missing(self):
        # The case the whole rule exists for. `0x0F58` is in the capture --
        # a `re.search` over the bytes finds it on the first `#` line -- and
        # there is no `addr` row for it, so the claim about the capture is a
        # disagreement. Reading this textually is the wrong implementation,
        # and it is green, which is why it needs a case rather than a claim.
        self.dated_row("0x0F58")
        self.header_capture("2026-09-23-cycle-0f00-0f5f.csv", 0x0F58)
        self.assertEqual(self.verdicts(), {"0x0F58": "missing"})
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ctrc.report(self.check()), 1)

    def test_an_addr_row_resolves_even_with_the_address_also_in_the_header(self):
        # The other half, and what keeps the case above from being satisfied
        # by a reader that simply refuses every address it finds in a comment.
        # The header names both addresses, one of which has a row and one of
        # which does not, so the pair separates "drops `#` lines" from
        # "rejects commented addresses".
        self.dated_row("0x0F5A")
        self.header_capture("2026-09-23-cycle-0f00-0f5f.csv", 0x0F5A, 0x0F5B,
                            rows=(0x0F5A,))
        self.assertEqual(self.verdicts(), {"0x0F5A": "resolved"})

    def test_a_txt_only_date_reports_that_it_has_no_column_to_read(self):
        # A date can resolve to `ecrw.py dump` output alone, and then the
        # columnar read has nothing to ask. That is the row 6 and row 8 shape,
        # and it is a fact about the *file set* rather than about any
        # literal's spelling, so it is reported on the file-count line beside
        # the count and not added to the closed shape list.
        self.dated_row("0x0F58")
        self.txt_capture("2026-09-23-dump.txt", "0x0F58: 0x00 -> 0x6e\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ctrc.dated_report(self.check())
        block = out.getvalue()
        self.assertIn("2026-09-23-* (1 capture(s)", block)
        self.assertIn(", 0 with an addr column)", block)

    def test_the_rule_is_load_bearing_rather_than_asserted_to_be(self):
        # The refusal, in the form the suite uses elsewhere: put the wrong
        # implementation in and watch the case above go green. The direction
        # is the one place this suite's drop-it-in-turn form differs from
        # `EachRuleIsLoadBearing` -- there, dropping a rule changes how *many*
        # claims are checked; here the claim is still checked either way and
        # what moves is its *verdict*, so the assertion is a flip and there
        # is no count to compare.
        self.dated_row("0x0F58")
        self.header_capture("2026-09-23-cycle-0f00-0f5f.csv", 0x0F58)
        with mock.patch.object(ctrc, "carried_by_column",
                               ctrc.carried_by):
            self.assertEqual(
                self.verdicts(), {"0x0F58": "resolved"},
                "reverting the dated claim to the textual read satisfies a "
                "claim the capture has no row for, so this case would not "
                "have failed before the rule and does now")


class EachRuleIsLoadBearing(unittest.TestCase):
    """Every rule the tool has, dropped in turn, against the committed tree.

    A rule that stops changing the answer is a rule that has stopped
    mattering, and a suite that does not notice has the same defect as a check
    that does not fire. Each loosening is asserted to make the run *check
    more* -- to turn literals it was passing over into claims, or a claim into
    a `missing` -- and is asserted against the run as shipped rather than
    against a figure, so a fixture row added to the index later does not break
    any of them. None is a floor on the tree's size.

    **One rule is asserted the other way round**, the dated-capture
    resolution, and the reason is in the helper's own name: before #794 it was
    the `another capture's address` shape, whose loosening made the run check
    *more*, and it is now the rule that turns row 7's two literals into claims
    in the first place, so loosening it -- pointing the run at a capture root
    with nothing in it -- takes them back out. A rule whose direction has
    inverted still has to change the answer or it has stopped mattering, so the
    assertion is the same claim with the other sign; what changed is which way
    the answer moves.

    Three of the five shapes cannot make the run *red* by being dropped, and
    saying so is part of the case: `0x07C4`/`0x07D7` really are in the file
    row 11 names, `0x0750`/`0x0010` in the dumps row 22 names, and `0x888D` in
    the fixture header row 8 names. What dropping those rules does is
    under-report, which is what the assertion is about. The sixth and seventh
    entries of the shape list -- both dated refusals, a capture that resolved
    to nothing and a sentence naming two of them -- have no instance in the
    committed tree at all, so each is pinned in a scratch case instead. **The
    multi-date rule is not dropped here and cannot be**: loosening it needs a
    two-date sentence, and the committed index has none for the shape to be
    exercised on. The scratch cases are the pinning, which is why this class's
    docstring says it rather than leaving the omission to be found.
    """

    NEVER = re.compile(r"(?!x)x")

    def assert_the_rule_is_load_bearing(self, why, **patches):
        before = ctrc.check()
        with mock.patch.multiple(ctrc, **patches):
            after = ctrc.check()
        self.assertGreater(after.checked, before.checked, why)

    def assert_the_rule_costs_less_without(self, why, captures):
        """The dated-capture resolution, whose loosening checks *fewer*.

        The sibling of the helper above rather than a second copy of it: the
        two differ in the sign of the comparison and in what is loosened, and
        keeping them apart is what makes the inversion legible instead of a
        special case buried in a general assertion.
        """
        before = ctrc.check()
        after = ctrc.check(captures=captures)
        self.assertLess(after.checked, before.checked, why)

    def test_the_page_range_rule(self):
        self.assert_the_rule_is_load_bearing(
            "dropping the page-boundary range rule checks the bounds of every "
            "sweep range as if they were bytes in the file, and two of them "
            "are not in any fixture",
            page_bounds=lambda sentence: set())

    def test_the_page_word_rule(self):
        self.assert_the_rule_is_load_bearing(
            "dropping the capture/page word checks every bare page-aligned "
            "address as a byte",
            PAGE_WORD=self.NEVER)

    def test_the_watched_set_span_rule(self):
        self.assert_the_rule_is_load_bearing(
            "dropping the two-token span rule checks the ends of a watched "
            "set as bytes the fixture holds",
            span_bounds=lambda sentence: set())

    def test_the_denial_rule(self):
        self.assert_the_rule_is_load_bearing(
            "dropping the denial rule checks the addresses the index says are "
            "not there, and row 23's 0x0784 becomes a missing",
            DENIAL_OBJECT=self.NEVER, DENIAL_ADJUNCT=self.NEVER)

    def test_the_dump_command_rule(self):
        self.assert_the_rule_is_load_bearing(
            "dropping the command rule checks the arguments of an ecrw.py "
            "invocation as if they were addresses in the file",
            COMMAND=self.NEVER)

    def test_the_firmware_code_address_rule(self):
        self.assert_the_rule_is_load_bearing(
            "dropping the code-address filter checks a handler in the EC image "
            "as a byte in a capture",
            code_addresses=lambda *a, **k: set())

    def test_the_dated_capture_rule(self):
        # The inverted one. With the capture root emptied, row 7's date
        # resolves to nothing, both of its literals become the sixth shape, and
        # the run checks two fewer claims -- which is the whole of what the
        # resolution is for, asserted in the direction it now works.
        empty = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, empty)
        self.assert_the_rule_costs_less_without(
            "with no capture root, the addresses the index attributes to a "
            "dated capture are not checked at all, which is the exemption "
            "#794 removed",
            empty)

    def test_the_width_rule(self):
        self.assert_the_rule_is_load_bearing(
            "widening ADDRESS to two digits reads the dumps' values and the "
            "marks' values as addresses",
            ADDRESS=re.compile(r"0[xX]([0-9A-Fa-f]{2,4})\b"))

    def test_the_backticked_predicate(self):
        self.assert_the_rule_is_load_bearing(
            "reading an address in running prose as a claim checks mentions "
            "the index never made claims about",
            BACKTICKED=re.compile(r"([^\s`]+)"))


class TheCommittedTree(unittest.TestCase):
    """The real thing: the index's address claims and the fixtures beside them
    currently agree.

    This goes red on any future edit that drifts a claim, which is the point of
    having the tool in the tree at all. What it asserts is that the run
    reached something -- a run reporting no claims and no disagreements is
    green for the wrong reason -- and never how much, because an expected count
    turns every added fixture into a failure.
    """

    def setUp(self):
        self.result = ctrc.check()

    def test_the_committed_index_agrees_with_the_fixtures_it_names(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            misses = ctrc.report(self.result)
        self.assertEqual(misses, 0, err.getvalue())

    def test_the_run_reached_something(self):
        # Each tally non-empty, and the shapes non-empty on top of them, read
        # out of what the run *printed* rather than off a `Result`: the claim
        # being pinned is the docstring's, that the counts are the output, since
        # a run that checked nothing and a run that found nothing look the same
        # from the exit code alone.
        out, err = io.StringIO(), io.StringIO()
        argv = sys.argv
        sys.argv = ['check_testdata_row_claims.py', '--check']
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = ctrc.main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0, err.getvalue())
        counts = {}
        for line in out.getvalue().splitlines():
            for piece in re.split(r'[:,]', line):
                number, _, label = piece.strip().partition(' ')
                if number.isdigit() and label:
                    counts[label] = int(number)
        for name, label in (('rows', 'table row(s)'),
                            ('literal-bearing rows', 'literal-bearing'),
                            ('literals', 'literal(s)'),
                            ('resolved claims', 'resolved'),
                            ('checked claims', 'claim(s) checked'),
                            ('claiming rows', 'claiming row(s)'),
                            ('passed-over literals',
                             'passed over under the five shapes and the two '
                             'dated refusals')):
            self.assertGreater(
                counts.get(label, 0), 0,
                f"the run reached no {name}: a run that checked nothing and a "
                "run that found nothing look the same from the exit code alone")

    def test_every_literal_is_four_hex_digits(self):
        # The width rule, over the whole column rather than one sentence. A
        # claim about the *shape* of the literals today, not a count of them.
        self.assertTrue(self.result.literals)
        for claim in self.result.claims:
            self.assertRegex(claim.address, r"^0x[0-9A-F]{4}$")

    def test_the_two_readers_of_the_file_column_agree(self):
        # `files_for()` re-implements `check_testdata_index.resolve()`'s six
        # branches because the sibling returns a verdict and throws the paths
        # away. Agreement is asserted per token over the committed table, so
        # drift is caught rather than assumed away -- and it is asserted
        # against the sibling's own answers rather than a number, so a row
        # added to the index later does not break it.
        with open(ctdi.INDEX, encoding="utf-8") as f:
            cells = ctdi.table_cells(f.read())
        tokens = [token for cell in cells for token in ctdi.TOKEN.findall(cell)]
        self.assertTrue(tokens, "the file column read no tokens at all")
        for token in tokens:
            verdict, _ = ctdi.resolve(token, ctdi.TESTDATA)
            found, paths = ctrc.files_for(token, ctdi.TESTDATA)
            self.assertEqual(found, verdict, token)
            # `resolved` means paths, and only a resolved token has any: a
            # check that said "resolved" for a token naming nothing would be
            # passing a row it never read.
            self.assertEqual(bool(paths), verdict == ctdi.RESOLVED, token)

    def test_the_row_count_is_the_siblings(self):
        # The same argument one level up: this tool counts the rows the index
        # checker counts, and reads the third column beside the first rather
        # than fused with it -- which is what feeding `units()` a whole file
        # would have done, since a table row is a unit of its own to it.
        self.assertEqual(self.result.rows, ctdi.check(ctdi.TESTDATA).rows)

    def test_the_committed_tree_exercises_every_shape(self):
        # Each of the five has an instance in the committed index, so none of
        # them is a rule that only ever runs in a scratch tree -- and an eighth
        # entry appearing here is a change to the docstring rather than a
        # silent widening of the check. Neither dated refusal is named, the
        # sixth and seventh entries of the docstring's list: the one dated
        # sentence in the tree names one date and resolves, so both have no
        # instance here by construction, and each is pinned in a scratch case
        # instead. **The count stays at five** -- a sixth instance here is a
        # sentence in the index naming two bare dates, which is a change to
        # what this tree exercises and not a reason to widen the check.
        self.assertEqual(
            sorted({reason for _, _, reason in self.result.shapes}),
            sorted(["capture/window bound", "denial", "dump-command argument",
                    "firmware code address", "watched-set span"]))

    def test_the_dated_claims_resolve_in_the_addr_column(self):
        # Row 7's two literals are `resolved` under **both** readings, and
        # that is the check that #975 moved the question being asked of them
        # rather than the answer it gives -- the tallies are byte-identical
        # across the change. So what is pinned here is *which* reader
        # resolved them, asserted on the run as shipped rather than against a
        # figure: each is in the `addr` column of the date's captures. Four
        # of that date's six files are `.txt` dumps with no column at all, so
        # the text they carry is not what the claim rests on either.
        dated = [claim for _, _, claims in self.result.dated for claim in claims]
        self.assertTrue(dated, "the run read no dated sentence at all")
        for claim in dated:
            self.assertEqual(claim.verdict, ctrc.RESOLVED, claim.address)
        for pattern, paths, _ in self.result.dated:
            self.assertLess(ctrc.with_column(paths), len(paths),
                            f"{pattern} resolved to .csv files only, so this "
                            "run no longer exercises the .txt half of a date")

    def test_the_two_door_discriminations_the_issue_names(self):
        # `0751-isolation-run-3blocks/` has no `0x0784` row and
        # `...-3blocks-moved/` has one; `gpu-door-example-quiet.csv` has no
        # `0x07C4` and no `0x07D0` row. Both are real and verified, and both
        # rows carry no address literal at all -- so the checker reaches
        # neither, which is why they are asserted here over the fixtures
        # rather than over a run.
        for rel, address in (("0751-isolation-run-3blocks/"
                              "2026-01-01-0751-isolation-0700-07ff.csv",
                              0x0784),
                             ("gpu-door-example-quiet.csv", 0x07C4),
                             ("gpu-door-example-quiet.csv", 0x07D0)):
            with open(os.path.join(ctdi.TESTDATA, rel), newline="",
                      encoding="utf-8") as f:
                rows = list(csv.DictReader(
                    line for line in f if not line.lstrip().startswith("#")))
            held = {ctdi.as_address(r["addr"]) for r in rows}
            self.assertNotIn(address, held, rel)
        self.assertTrue(ctrc.carried_by("0x0784", [os.path.join(
            ctdi.TESTDATA, "0751-isolation-run-3blocks-moved/"
            "2026-01-01-0751-isolation-0700-07ff.csv")]))


if __name__ == '__main__':
    unittest.main()
