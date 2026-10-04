#!/usr/bin/env python3
"""Offline checks for `a73f_notify_census.py`: no hardware, no Ghidra, and no
network, so this suite runs in the cheap tier with the rest of `ec/tools`.

It stands in for three things. Against the committed firmware, it holds the
relations the write-up's table rests on -- that every site the tool reports is
a real instruction carrying the bytes it claims, that a resolved code is the
immediate at the write the tool names, and that every code and every listing
the write-up cites is one this tool re-derives rather than one a reader has to
take on trust. Against inline fixtures, it holds the refusals: a register-fed
R7, a call between the write and the site, two paths carrying two codes, and a
byte sequence with nothing behind it. Against the annotation CSV, it holds that
the rows this decode corrected say what the tool now measures.

**It asserts no population.** Not how many sites there are, not how many codes,
not how many rows the CSV carries. Those are the census, and CLAUDE.md records
a test that asserts a count of the tree failing repeatedly -- every merge moves
the number, and the line carrying it is one every other branch edits. What is
asserted here is that the sets agree with each other and with the image.
"""
import csv
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import a73f_notify_census as census

ANNOTATIONS = HERE.parent / "annotations"
FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
FUNCTIONS_CSV = ANNOTATIONS / "ghidra-functions.csv"
WRITEOUT = HERE.parent.parent / "docs" / "findings" / "a73f-notify-path.md"


def read_rows():
    with open(FUNCTIONS_CSV, newline="") as f:
        return list(csv.DictReader(f))


class CensusAgainstTheImage(unittest.TestCase):
    """The tool's output against the bytes it claims to have read."""

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()
        cls.sites = census.scan(cls.d)
        cls.by_runtime = {s.runtime: s for s in cls.sites}

    def test_every_site_is_the_byte_sequence_its_kind_names(self):
        for s in self.sites:
            self.assertEqual(self.d[s.offset], 0x12 if s.kind == "lcall" else 0x02)
            self.assertEqual(self.d[s.offset + 1:s.offset + 3], bytes((0xA7, 0x3F)))

    def test_every_site_is_in_a_named_region(self):
        for s in self.sites:
            self.assertNotEqual(s.region, "unknown", hex(s.offset))
            self.assertIsNotNone(s.runtime)

    def test_a_resolved_code_is_the_immediate_at_the_write_the_tool_names(self):
        for s in self.sites:
            if s.verdict != "resolved":
                continue
            self.assertEqual(self.d[s.write_at], census.R7_IMM)
            self.assertEqual(self.d[s.write_at + 1], s.code)

    def test_a_resolved_site_has_exactly_one_r7_write_between_it_and_its_code(self):
        # Two writes and the nearer one is what reached the site, so the
        # resolver picking the earlier one would be reporting a value the site
        # overwrites -- the failure mode `scan`'s backward walk exists to avoid.
        for s in self.sites:
            if s.verdict != "resolved":
                continue
            between = self.d[s.write_at + 2:s.offset]
            self.assertFalse(any(b in (census.R7_IMM, census.R7_FROM_A)
                                 for b in between), hex(s.runtime))

    def test_an_unresolved_site_names_a_reason(self):
        for s in self.sites:
            if s.verdict == "resolved":
                continue
            self.assertTrue(s.note, "unresolved with no reason at %#x" % s.offset)

    def test_an_unresolved_site_does_not_also_carry_a_code(self):
        # The two columns are alternatives. A row with both would let a reader
        # quote the code without reading the refusal beside it.
        for s in self.sites:
            if s.verdict == "resolved":
                self.assertIsNotNone(s.code)
            else:
                self.assertIsNone(s.code)

    def test_codes_is_exactly_the_resolved_sites_codes(self):
        self.assertEqual(census.codes(self.sites),
                         sorted({s.code for s in self.sites
                                 if s.verdict == "resolved"}))

    def test_the_csv_carries_a_row_for_every_site_and_no_others(self):
        text = census.table(self.sites)
        got = [r["runtime"] for r in csv.DictReader(text.splitlines())]
        self.assertEqual(got, ["0x%04X" % s.runtime for s in self.sites])

    def test_the_table_names_every_code_the_csv_does(self):
        # The write-up pastes the markdown table; a code in one and not the
        # other is how the two drift apart without anything going red.
        table = census.report(self.sites)
        for code in census.codes(self.sites):
            self.assertIn("0x%02X" % code, table)


class Refusals(unittest.TestCase):
    """The cases the resolver has to decline rather than answer.

    Inline fixtures rather than EC addresses, because the image has one
    instance of some of these shapes and none of others, and a refusal test
    that depended on a site the next annotation change could reframe would be
    a test of the image rather than of the rule.
    """

    @staticmethod
    def verdict(blob, back=8):
        sites = census.scan(blob, back=back)
        return sites[0].verdict if sites else "no site"

    def test_a_register_fed_r7_is_unresolved(self):
        self.assertEqual(self.verdict(bytes((0xFF, 0x12, 0xA7, 0x3F))), "unresolved")

    def test_a_register_fed_r7_still_names_the_write_it_found(self):
        # Unresolved is not "nothing was found": the write is named so a reader
        # can go and look at it, and the note says why it carries no constant.
        site = census.scan(bytes((0xFF, 0x12, 0xA7, 0x3F)), back=8)[0]
        self.assertEqual(site.write_at, 0)
        self.assertEqual(site.note.count("mov  r7,a"), 1)

    def test_both_transfer_shapes_resolve_the_same_way(self):
        for op in (0x12, 0x02):
            site = census.scan(bytes((0x7F, 0x9B, op, 0xA7, 0x3F)), back=8)[0]
            self.assertEqual(site.verdict, "resolved")
            self.assertEqual(site.code, 0x9B)

    def test_a_call_between_the_write_and_the_site_is_refused(self):
        # The shape of the EC's own 0xC5A5: the value arrives in a callee's
        # return, so the earlier constant is not the code.
        blob = bytes((0x22, 0x7F, 0x22, 0x12, 0xCA, 0x2D, 0x12, 0xA7, 0x3F))
        self.assertEqual(self.verdict(blob), "unresolved")

    def test_two_paths_with_two_codes_are_refused_with_both_named(self):
        # The `sjmp` at offset 2 measures its displacement from offset 4, and
        # the site is at 8.
        blob = bytes((0x7F, 0x11, 0x80, 0x04, 0x00, 0x00, 0x7F, 0x22,
                      0x12, 0xA7, 0x3F))
        site = census.scan(blob, back=8)[0]
        self.assertEqual(site.verdict, "unresolved")
        self.assertEqual(site.candidates, [0x11, 0x22])

    def test_no_write_at_all_is_unresolved(self):
        self.assertEqual(self.verdict(bytes((0x22, 0x22, 0x12, 0xA7, 0x3F))),
                         "unresolved")

    def test_a_sequence_with_nothing_behind_it_is_reported_not_dropped(self):
        # A byte scan is a superset of the sites. Reporting the hit with its
        # framing verdict is what keeps "found by a byte scan" honest; dropping
        # it would report a smaller population than the method found.
        self.assertIn(self.verdict(bytes((0x00, 0x00, 0x12, 0xA7, 0x3F)), 4),
                      ("unframed", "unresolved"))

    def test_the_scan_follows_its_target_argument(self):
        sites = census.scan(bytes((0x7F, 0x5A, 0x12, 0x11, 0x22)), target=0x1122)
        self.assertEqual([s.runtime for s in sites], [0x0002])
        self.assertEqual(sites[0].code, 0x5A)


class TheToolRuns(unittest.TestCase):
    """`--self-test` exists and passes, rather than merely being defined."""

    def test_self_test_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, str(HERE / "a73f_notify_census.py"), "--self-test"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("self-test passed", proc.stdout)

    def test_both_output_modes_succeed(self):
        for flag in ([], ["--csv"]):
            proc = subprocess.run(
                [sys.executable, str(HERE / "a73f_notify_census.py")] + flag,
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue(proc.stdout.strip())


class AnnotationRows(unittest.TestCase):
    """The CSV rows this decode touched, held to what the tool now measures.

    The retraction is the point here. A set of trampoline rows carried the
    sentence "0x1114 is not present in this decompiled tree", and every one of
    them has to keep it beside the correction: a retraction done by silent edit
    is the failure CLAUDE.md puts above every other, because the wrong claim is
    what a reader three merges back would otherwise find with nothing next to
    it. So the assertion is a pairing -- a row carrying the claim and a row
    carrying the correction are the same row -- and not a count of either.

    The same sentence appeared against the 0x1100 stub in a different wording,
    and that one was the same scope error, so it is corrected too. Which rows
    these are is not asserted here: that is the census, and it moves.
    """

    # Both wordings of the claim, because the false sentence was written twice
    # and a retraction that catches one shape of it leaves the other standing.
    FALSE_CLAIMS = ("0x1114 is not present in this decompiled tree",
                    "The body at 0x1100 is not present in this decompiled tree")
    CORRECTION = "Correction, issue #248"

    @classmethod
    def setUpClass(cls):
        cls.rows = read_rows()
        cls.by_addr = {(r["scope"], r["addr"].lower().lstrip("0x")): r
                       for r in cls.rows}

    def _carrying(self, needle):
        return [r for r in self.rows if needle in r["comment"]]

    def test_every_row_carrying_a_retracted_claim_carries_the_correction(self):
        for row in self.rows:
            if any(c in row["comment"] for c in self.FALSE_CLAIMS):
                self.assertIn(self.CORRECTION, row["comment"],
                              "%s %s: the wrong claim is still standing alone"
                              % (row["scope"], row["addr"]))

    def test_the_correction_cites_the_listing_that_decodes_the_stub(self):
        # A correction that names the scope but not the file is a reader with
        # nowhere to check it, which is the state this retraction is correcting.
        # Each correction cites the listing for the stub it corrects, which is
        # 0x1100 for the two rows that said so about 0x1100.
        for row in self._carrying(self.CORRECTION):
            self.assertRegex(row["comment"], r"ec/decompiled/common/1(?:100|114)\.asm",
                             "%s %s" % (row["scope"], row["addr"]))

    def test_the_correction_names_the_stub_the_listing_calls_it(self):
        for row in self._carrying(self.CORRECTION):
            self.assertIn("bl51_bank_select_", row["comment"],
                          "%s %s" % (row["scope"], row["addr"]))

    def test_the_correction_names_what_the_stub_does_with_dptr(self):
        # The claim being retracted was about the stub's behaviour, so the
        # correction has to answer that and not only say the stub exists.
        for row in self._carrying(self.CORRECTION):
            self.assertIn("cross-bank call", row["comment"],
                          "%s %s" % (row["scope"], row["addr"]))

    def test_the_1114_correction_says_where_the_notify_chain_ends(self):
        # The 0x1114 family is the one 0xA73F goes through, so its correction
        # has to point at the chain rather than leaving the reader to rejoin it.
        # Rows that merely mention bl51_bank_select_1 without carrying a
        # correction are a different set and are not asserted about.
        for row in self._carrying(self.CORRECTION):
            if "bl51_bank_select_1" not in row["comment"]:
                continue
            self.assertIn("0x896A", row["comment"],
                          "%s %s" % (row["scope"], row["addr"]))

    def test_every_annotation_row_has_a_non_empty_evidence_path(self):
        for row in self.rows:
            self.assertTrue(row["evidence"].strip(),
                            "%s %s" % (row["scope"], row["addr"]))
            for path in row["evidence"].split(";"):
                path = path.strip()
                if path:
                    self.assertTrue((HERE.parent.parent / path).exists(), path)

    def test_the_a73f_row_names_where_the_code_goes(self):
        row = self.by_addr[("bank0", "a73f")]
        self.assertIn("0x1666", row["comment"])
        self.assertIn("R7", row["comment"])

    def test_the_a73f_row_no_longer_calls_its_destination_undecoded(self):
        # The retracted sentence in this row was about 0x1666; the correction
        # has to replace that claim, not sit beside it as a new one.
        row = self.by_addr[("bank0", "a73f")]
        self.assertNotIn("Nothing in this listing shows what 0x1666 does",
                         row["comment"])
        self.assertIn("bl51_bank_select_1", row["comment"])

    def test_the_a73f_row_still_refuses_to_name_a_codes_meaning(self):
        # The chain being decoded is not a licence to interpret the payload.
        row = self.by_addr[("bank0", "a73f")]
        self.assertIn("not decoded here", row["comment"])

    def test_the_caller_rows_point_at_the_census_rather_than_saying_open(self):
        for addr in ("8f0f", "a3c3", "a312", "8749"):
            row = self.by_addr[("bank0", addr)]
            self.assertNotIn("is still open", row["comment"],
                             "0x%s still calls 0xA73F open" % addr)

    def test_the_8f0f_row_names_the_census_tool(self):
        row = self.by_addr[("bank0", "8f0f")]
        self.assertIn("a73f_notify_census.py", row["comment"])


class IntmemCensusIsTheCommittedTools(unittest.TestCase):
    """The `0x6A` census is `intmem_refs.py`'s output, quoted not re-counted.

    An earlier version of the write-up stated its own `0x6A` figures -- "exactly
    two stores and two loads", and no second reader -- and both were wrong:
    this repository already ships `intmem_refs.py` for that question, and its
    output disagrees. The claim was in three files at once (the write-up, this
    row of the CSV, and the generated `.c` that follows the CSV), which is what
    a hand-carried figure looks like when nothing checks it against the tool.

    So the figure is held to the tool. Not to a constant written here: that
    would be a second hand-kept copy going stale the same way, and CLAUDE.md is
    explicit that a test asserts a property rather than a count. What is
    asserted is the *relation* -- the write-up names this tool as its source,
    and quotes no figure the tool does not print -- so a scan that changes, or
    a document that drifts from it, goes red instead of into the next merge.
    """

    # The false census, in the two wordings it was written in. Matched against
    # whitespace-normalised text, because a phrase that straddles a line wrap
    # is still the phrase -- and a test that only sees it when the wrap happens
    # to fall elsewhere is a test that passes for the wrong reason.
    FALSE_CENSUS = ("finds exactly two stores and two loads",
                    "Two stores and two loads")
    # What a retraction of this claim looks like in prose. The false census is
    # *meant* to survive in the write-up, beside its correction: CLAUDE.md
    # requires the wrong version stay visible, and a silent edit is the failure
    # it puts above every other. So the assertion is a pairing, not an absence.
    CORRECTION = ("retracted", "wrong", "Both halves are wrong")

    @classmethod
    def setUpClass(cls):
        cls.proc = subprocess.run(
            [sys.executable, str(HERE / "intmem_refs.py"),
             str(FIRMWARE), "0x6A"],
            capture_output=True, text=True)
        cls.output = cls.proc.stdout
        cls.text = WRITEOUT.read_text()
        # Split into paragraphs on the blank lines FIRST, then flatten each one.
        # Flattening the whole document instead would collapse the blank lines
        # too, and "the paragraph this mention sits in" would quietly become
        # "the whole document" -- which passes for any correction stated
        # anywhere, and so cannot tell a retraction from a rewrite.
        cls.paras = [re.sub(r"\s+", " ", p)
                     for p in re.split(r"\n\s*\n", cls.text)]
        cls.flat = " ".join(cls.paras)
        cls.rows = read_rows()
        cls.a73f = next(r for r in cls.rows
                        if (r["scope"], r["addr"].lower().lstrip("0x"))
                        == ("bank0", "a73f"))

    def test_the_census_tool_answers_for_the_image(self):
        # A green suite over a tool that failed would assert nothing, so the
        # scan is checked for having run and found something before its figures
        # are trusted as the reference.
        self.assertEqual(self.proc.returncode, 0, self.output + self.proc.stderr)
        self.assertRegex(self.output, r"(?m)^0x6A\s+refs=\d+", self.output)

    def test_the_retracted_census_is_quoted_rather_than_silently_dropped(self):
        # The retraction is only a retraction if the wrong claim is still there
        # to be read. This is the assertion that makes the one below mean
        # something: without it, "every mention carries a correction" would
        # also be satisfied by deleting the claim outright, which is the edit
        # CLAUDE.md rules out.
        self.assertTrue(any(p in self.flat for p in self.FALSE_CENSUS),
                        "the retracted 0x6A census was silently removed from %s"
                        % WRITEOUT.name)

    def test_every_mention_of_the_false_census_carries_its_correction(self):
        # Both wordings, because the claim was written twice and a retraction
        # catching one shape leaves the other standing -- the 0x1114 lesson,
        # applied here. Scoped to the paragraph each mention sits in, so the
        # correction has to be beside the claim rather than somewhere else in
        # the document.
        for para in self.paras:
            if not any(p in para for p in self.FALSE_CENSUS):
                continue
            self.assertTrue(any(c in para for c in self.CORRECTION),
                            "the retracted census stands without its "
                            "correction: %r" % para[:160])

    def test_the_a73f_row_no_longer_carries_the_false_census(self):
        # The CSV row is the other half of this claim, and unlike the write-up
        # it is not the place a retraction lives -- the correction points at the
        # write-up instead. So here the requirement really is absence: the row
        # must not go on asserting the figure it was measured against.
        flat = re.sub(r"\s+", " ", self.a73f["comment"])
        for phrase in self.FALSE_CENSUS:
            self.assertNotIn(phrase, flat,
                             "the retracted 0x6A census is back in the CSV row")

    def test_the_writeup_names_the_tool_it_quotes(self):
        # A figure with no named source is the failure being fixed, so the
        # citation is what is asserted -- not the figure beside it.
        self.assertIn("intmem_refs.py", self.text)

    def test_the_a73f_row_names_the_tool_it_quotes(self):
        self.assertIn("intmem_refs.py", self.a73f["comment"])

    def test_the_writeup_quotes_a_figure_the_tool_prints(self):
        # The numbers the write-up states for this census are the ones the tool
        # renders. Held as a relation to the tool's output, so both move
        # together; a figure invented by hand has no line to match and fails.
        quoted = {int(m) for m in re.findall(r"refs=(\d+)", self.text)}
        printed = {int(m) for m in re.findall(r"^0x6A\s+refs=(\d+)",
                                              self.output, re.M)}
        self.assertTrue(quoted, "the write-up quotes no refs= figure")
        self.assertTrue(quoted.issubset(printed),
                        "write-up quotes refs=%s, the tool prints refs=%s"
                        % (sorted(quoted), sorted(printed)))

    def test_the_writeup_leaves_the_open_site_open(self):
        # The one hit the census cannot adjudicate has to read as open in the
        # write-up. Naming it as settled in either direction -- "it is a table"
        # or "it is a real reader" -- is the overclaim this correction is
        # correcting, so the refusal is what is asserted.
        self.assertRegex(self.text, r"0x8486")
        self.assertIn("not adjudicated here", self.text)


class WriteupTable(unittest.TestCase):
    """The write-up's site table is the tool's site table.

    A table pasted into a document and never re-derived is a second copy of the
    census, and the two drift the moment an annotation change reframes a site.
    These read the write-up's table back and hold it against the tool one cell
    at a time, so a drift names the row rather than being noticed by a reader.
    """

    # The write-up's own column headings, mapped to the keys the tool's
    # `Site.row()` uses. Read through this so the heading can be written for a
    # reader ("R7 write") without the check having to know it.
    COLS = {"runtime": "runtime", "region": "region", "kind": "kind",
            "code": "code", "verdict": "verdict", "R7 write": "r7_write",
            "listing": "listing", "note": "note"}

    @classmethod
    def setUpClass(cls):
        cls.text = WRITEOUT.read_text()
        cls.sites = census.scan(FIRMWARE.read_bytes())

    def _rows(self):
        """The write-up's site table, keyed by the column names it prints.

        The column names are read out of the write-up's own header row rather
        than carried here, so a column added to the tool's table is a column
        this checks rather than one that silently stops being compared.
        """
        lines = self.text.splitlines()
        cols = None
        rows = []
        for line in lines:
            if cols is None and line.startswith("| runtime"):
                cols = [self.COLS.get(c.strip(), c.strip())
                        for c in line.strip().strip("|").split("|")]
                continue
            if cols is None or not line.startswith("| 0x"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == len(cols):
                rows.append(dict(zip(cols, cells)))
        return cols, rows

    def test_the_writeup_has_a_site_table(self):
        _cols, rows = self._rows()
        self.assertTrue(rows, "no | 0x.... | table rows found in %s"
                                   % WRITEOUT.name)

    def test_the_table_has_a_row_for_every_site_and_no_others(self):
        _cols, rows = self._rows()
        self.assertEqual([r["runtime"] for r in rows],
                         ["0x%04X" % s.runtime for s in self.sites])

    def test_every_cell_of_every_row_is_what_the_tool_says(self):
        _cols, rows = self._rows()
        for row, site in zip(rows, self.sites):
            where = row["runtime"]
            self.assertEqual(row["verdict"], site.verdict, "verdict at %s" % where)
            self.assertEqual(row["code"],
                             "0x%02X" % site.code if site.code is not None else "-",
                             "code at %s" % where)
            self.assertEqual(row["r7_write"],
                             "0x%04X" % site.write_at
                             if site.write_at is not None else "-",
                             "R7 write at %s" % where)
            self.assertEqual(row["listing"], site.listing or "none exported",
                             "listing at %s" % where)

    def test_every_row_names_a_listing_or_says_none_is_exported(self):
        # A site with no exported listing is the blind spot, and it has to read
        # as one rather than as an empty cell. This is also the only assertion
        # that would notice a listing column quietly going unsourced.
        _cols, rows = self._rows()
        for row in rows:
            self.assertTrue(row.get("listing"), "no listing column at %s"
                                                       % row["runtime"])

    def test_an_unresolved_row_says_why(self):
        # A refusal with no reason beside it reads as a gap in the census rather
        # than as a limit of the method, which is the one thing the calibration
        # rule will not accept.
        _cols, rows = self._rows()
        for row in rows:
            if row["verdict"] == "unresolved":
                self.assertTrue(row.get("note"),
                                "no reason given at %s" % row["runtime"])

    def test_the_writeup_holds_no_hardware_claim(self):
        # The pipeline has no laptop and no Windows machine, so a sentence
        # asserting an observation is the one failure here that cannot be undone
        # later. Checked as assertions rather than as bare phrases, because the
        # document opens by *denying* exactly these -- "no register was read
        # back" contains the phrase an assertion would use.
        for sentence in re.findall(r"[^.!?]*\b(?:we|the trace|it|holding|"
                                   r"observing)\b[^.!?]*[.!?]", self.text):
            for verb in ("read back", "observed", "measured on hardware",
                         "captured", "watched"):
                if verb in sentence.lower():
                    self.fail("write-up makes an observation claim: %s"
                              % sentence.strip())


class TheOtherStubDestinationsAreDerived(unittest.TestCase):
    """The write-up's `0x1114` table is `bl51_trampolines.py`'s, not a hand list.

    An earlier version of "What this does not say" named seven constants
    reaching `0x1114` and called them the rest. They are the contiguous
    `0x163C`-`0x1672` entry group minus `0x896A`, nothing scoped the sentence
    to that group, and the annotated population is larger -- which is the
    overclaim CLAUDE.md puts above every other rule, in the one section whose
    job is to state the open surface completely.

    So the list is derived here rather than trusted: `bl51_trampolines.py`
    recognises a trampoline by its whole-body *shape* and re-derives the set
    from the annotation rows and their committed `.asm` on every run, and the
    write-up's table is read back against it row for row. What is asserted is
    the relation -- the document's rows are the tool's rows, and each one's
    "destination" cell is what the CSV actually says -- never how many there
    are. A count is the census, and every merge moves it.

    The destination column is asserted because that is where the earlier
    sentence was wrong twice: it told a reader every constant was one
    `gate`/`writer` row away, and most are not. A column asserting that would
    be a claim with nothing behind it.
    """

    STUB = "1114"      # the bank-1 select stub this decode walks through
    NOTIFY = "896A"    # the one constant this decode followed to a conclusion

    @classmethod
    def setUpClass(cls):
        import bl51_trampolines
        cls.rows = read_rows()
        cls.text = WRITEOUT.read_text()
        listings = bl51_trampolines.trampoline_listings(cls.rows)
        cls.derived = {}
        for (scope, addr), path in listings.items():
            if not bl51_trampolines.is_trampoline(path, {cls.STUB}):
                continue
            first = bl51_trampolines.read_listing(path)[0]
            const = re.search(r"0x([0-9A-Fa-f]{4})", first[2]).group(1).upper()
            cls.derived[const] = (scope, addr.upper())
        cls.by_addr = {r["addr"].lower().lstrip("0x"): r for r in cls.rows}

    def _table(self):
        """The write-up's stub-destination table as {constant: (addr, cell)}.

        Read off the document's own header rather than carried here, so the
        check follows a renamed column instead of quietly comparing nothing --
        the `_rows()` shape `WriteupTable` already uses for the site table.
        """
        cols = None
        out = {}
        for line in self.text.splitlines():
            # Stripped first: this table sits inside a bullet, so its rows are
            # indented and a `startswith` against the raw line would match
            # nothing and leave every assertion below vacuous.
            line = line.strip()
            if cols is None and line.startswith("| trampoline"):
                cols = [c.strip() for c in line.strip("|").split("|")]
                continue
            if cols is None or not line.startswith("| `0x"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            row = dict(zip(cols, cells))
            const = self._hex(row["DPTR constant"])
            out[const] = (self._hex(row["trampoline"]),
                          row["its destination in "
                              "`ec/annotations/ghidra-functions.csv`"])
        return out

    @staticmethod
    def _hex(cell):
        """`0x163C` -> `163C`, so a document cell and a derived address compare.

        One spelling on both sides of every comparison below. Comparing a
        document's `0x`-prefixed cell to a bare derived address would fail on
        formatting and read as a disagreement about the firmware.
        """
        return cell.strip().strip("`").upper().removeprefix("0X")

    def test_the_derived_set_is_not_empty(self):
        # The scan is what every assertion below is measured against, so an
        # empty one would make a green suite mean nothing.
        self.assertTrue(self.derived,
                        "bl51_trampolines matched no trampoline to 0x%s"
                        % self.STUB)

    def test_the_notify_constant_is_one_of_them(self):
        # The write-up's chain rests on this one, so if it stopped being a
        # trampoline into the stub the whole decode would be about something
        # else and the table would have quietly stopped covering it.
        self.assertIn(self.NOTIFY, self.derived)

    def test_the_table_holds_every_derived_constant_and_no_others(self):
        table = self._table()
        self.assertTrue(table, "no stub-destination table found in %s"
                                  % WRITEOUT.name)
        # `0x896A` is subtracted because the table is the destinations *other*
        # than the one this decode followed -- it is named in the prose beside
        # the table and covered by the chain section above. Comparing against
        # the full derived set would make a correct table fail for the one row
        # it is right to leave out, which is how a check like this gets
        # "fixed" by adding a row nobody asked for.
        expected = set(self.derived) - {self.NOTIFY}
        self.assertEqual(sorted(table), sorted(expected),
                         "the write-up's table and bl51_trampolines.py "
                         "disagree about which constants reach 0x%s"
                         % self.STUB)

    def test_the_table_names_each_trampoline_address_the_derivation_found(self):
        # The address column is what makes a reader's next step possible, and
        # it is the half of the row that can drift from the annotation rows.
        for const, (addr, _cell) in self._table().items():
            scope, derived_addr = self.derived[const]
            self.assertEqual(addr, derived_addr,
                             "0x%s: write-up says %s, derivation says %s %s"
                             % (const, addr, scope, derived_addr))

    def test_the_table_names_the_notify_entry_it_excludes_from_its_own_list(self):
        # The table is the destinations *other* than the one this decode
        # followed, so the followed one has to be named beside it or a reader
        # cannot tell the table's population from the whole. It appears in the
        # stub's own row, which the chain section already covers.
        self.assertNotIn(self.NOTIFY, self._table())
        self.assertIn(self.NOTIFY, self.derived)

    def test_each_destination_cell_is_what_the_csv_actually_says(self):
        # "none in the CSV" is the cell most of these carry, and it is the one
        # an earlier sentence got wrong by asserting the opposite of what the
        # file says. Read back out of the rows rather than trusted.
        for const, (_addr, cell) in self._table().items():
            dest = self.by_addr.get(const.lower().lstrip("0"))
            flat = re.sub(r"\s+", " ", cell)
            if dest is None:
                self.assertIn("none in the CSV", flat,
                              "0x%s: %r contradicts a row that exists"
                              % (const, cell))
            else:
                self.assertIn(dest["name"], flat,
                              "0x%s: %r does not name the row's name"
                              % (const, cell))

    def test_the_table_does_not_claim_every_destination_is_one_row_away(self):
        # The claim being corrected. Asserted as a relation on the table rather
        # than on a phrase: what has to be true is that the document no longer
        # tells a reader every constant resolves to a row, so the destinations
        # the CSV cannot supply are named as such somewhere in the table's own
        # surroundings.
        self.assertTrue(any("none in the CSV" in cell
                            for _addr, cell in self._table().values()),
                        "no destination is reported unresolvable, which is "
                        "what the retracted sentence claimed for all of them")

    def test_the_writeup_scopes_the_entry_group_it_names(self):
        # The failure was a count with no scope: seven constants that are the
        # `0x163C`-`0x1672` group minus `0x896A` read as the whole
        # population. What has to survive an edit is that the group is named
        # as a group, so the same reading cannot be reconstructed from a
        # sentence that no longer says "seven".
        # Matched within one line, and on the prose spelling of the range
        # rather than the table's `0x163C` cell: `.*` without DOTALL still
        # walks a newline in the other direction here, and a pattern loose
        # enough to be satisfied by the table row would pass after the
        # sentence it exists to check had been deleted.
        self.assertRegex(self.text, r"`0x163C`-`0x1672`")


if __name__ == '__main__':
    unittest.main()
