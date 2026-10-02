#!/usr/bin/env python3
"""Offline checks for `xdata_span_survey.py`: the two committed tables and the
cross-check that holds them to `trace_xdata_refs.py`.

No firmware upload, no hardware, no Windows, no network. Every input is a file
this repository already ships -- `ec/firmware/GMxMGxx_11.800` and the two
committed CSVs -- so the whole suite runs in a cloud agent's turn.

**What is asserted here is a property of the tables, never their size.** The
full-range collision count is a finding, and it belongs in
`../../docs/findings/pd-xdata-collision-survey.md` beside the command that
produced it; a number here would go stale on the next merge and every branch
with an open PR would edit the same line (CLAUDE.md, "No totals of the
repository's own text"). So `Collisions` pins *which rows are in the table* --
every one of them referenced by both images -- and not how many there are.

**The agreement is checked against the other tool, not against a literal.**
`0x04A6,7,3,4` / `0x04A7,2,2,0` / `0x07D0,254,0,254` are the rows
`pd-xdata-overlap.md` §1 quotes and `registers.yaml`, `static-refs-audit.md` §1
and `ec-0x07d0-sites.md` §1 all cite. The case below re-derives them by running
`trace_xdata_refs.py --counts-only` and comparing, so a change in either tool
shows up as disagreement rather than as a number that quietly moved. Pinned as
literals as well, because a pair of tools that drift *together* agree with each
other forever -- the same vacuous-green shape
`../../docs/findings.md` §14b records.

**The mutations are the reason the rest of the file means anything.**
`--collisions` and `--check` are two additions to a tool whose committed
`0x0400`-`0x07FF` output had to stay byte-identical, and an addition that
quietly changed the table would leave every case below green. So the filter is
checked against the unfiltered run rather than against a stored copy, and
`--check` is pointed at a deliberately wrong file to show it goes red.

Run it directly, or through `bash tools/run-tests.sh`, which discovers every
`test_*.py` in the tree.
"""
import csv
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
TOOL = os.path.join(HERE, "xdata_span_survey.py")
TRACE = os.path.join(HERE, "trace_xdata_refs.py")

SPAN_CSV = os.path.join(HERE, "..", "annotations", "pd-xdata-span-sites.csv")
COLLISIONS_CSV = os.path.join(HERE, "..", "annotations",
                              "pd-xdata-collisions-full.csv")

# The span `pd-xdata-overlap.md` §1 quotes, and the range the premise behind
# these two files is about. Named as constants because the *commands* are what
# have to reproduce the tables -- a range spelled out in four places is four
# places to update.
SPAN = ("0x0400", "0x07FF")
WHOLE = ("0x0000", "0xFFFF")

# §1's three agreement rows, as that page prints them: address, main_ec,
# pd_image. `0x04A6` is the collision the issue opened on; `0x04A7` is the
# address the PD image is *not* found to reference by this scan, which is half
# of what makes `0x04A6` a base rather than a 16-bit pair; `0x07D0` is the
# address `ec-0x07d0-sites.md` is built on.
AGREEMENT = {"0x04A6": (3, 4), "0x04A7": (2, 0), "0x07D0": (0, 254)}


def run_tool(*args):
    """The survey as a command, undecoded.

    Bytes rather than text: `--csv` emits the csv module's own CRLF terminator
    and the committed tables carry it, so `text=True`'s universal-newline
    translation would compare a different thing from the one `--check`
    compares.
    """
    return subprocess.run([sys.executable, TOOL, *args],
                          capture_output=True, cwd=REPO)


def survey_bytes(lo, hi, *flags):
    r = run_tool(FIRMWARE, lo, hi, "--csv", *flags)
    assert r.returncode == 0, r.stderr.decode()
    return r.stdout.decode()


def rows_of(table):
    return list(csv.DictReader(io.StringIO(table, newline="")))


def counts_only(addr):
    """`trace_xdata_refs.py --counts-only`'s per-image counts, as a dict.

    Regions with no sites are absent from the printed line rather than printed
    as a zero, so every name defaults to 0 here. `0x04A7` is the case that
    needs it: the line reads `bank0=1 bank1=1` with no `pd-image=` at all.
    """
    r = subprocess.run([sys.executable, TRACE, FIRMWARE, addr, "--counts-only"],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    line = next(l for l in r.stdout.splitlines() if l.startswith(addr))
    counts = {name: int(n) for name, n in re.findall(r"([a-z0-9-]+)=(\d+)",
                                                     line)}
    assert not counts or sum(counts.values()) == int(
        re.search(r": (\d+) direct", line).group(1)), line
    return counts


# What this run produces, read once: the full-range survey is a 65536-row walk
# and every case below that wants one wants the same one.
SPAN_TABLE = survey_bytes(*SPAN)
WHOLE_TABLE = survey_bytes(*WHOLE)
COLLISION_TABLE = survey_bytes(*WHOLE, "--collisions")


class CommittedTables(unittest.TestCase):
    """`--check`, on the two files that are the product of the commands."""

    def test_the_span_table_is_reproduced_byte_for_byte(self):
        r = run_tool(FIRMWARE, *SPAN, "--csv", "--check", SPAN_CSV)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("reproduces it byte for byte", r.stdout.decode())

    def test_the_collision_table_is_reproduced_byte_for_byte(self):
        r = run_tool(FIRMWARE, *WHOLE, "--csv", "--collisions",
                     "--check", COLLISIONS_CSV)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("reproduces it byte for byte", r.stdout.decode())

    def test_the_span_table_did_not_move(self):
        """The addition's own constraint, asserted as bytes rather than as a
        description of the change.

        `--collisions` and `--check` are edits to a tool whose `0x0400`-`0x07FF`
        output `pd-xdata-overlap.md` §1 quotes as the cross-check against
        `trace_xdata_refs.py`. A row moved, a column reordered or a terminator
        changed and every case in `Agreement` below would still pass, because
        those cases read the columns by name.
        """
        with open(SPAN_CSV, "rb") as f:
            self.assertEqual(SPAN_TABLE.encode(), f.read())

    def test_check_is_red_on_a_table_that_drifted(self):
        """The mutation. `--check` is the only thing standing between a
        regenerated table and a hand-edited one, so it is pointed at a table
        with one cell changed and has to say so through its exit code."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "drifted.csv")
            drifted = SPAN_TABLE.replace("0x04A6,7,3,4", "0x04A6,7,4,3", 1)
            self.assertNotEqual(
                SPAN_TABLE, drifted,
                "the span table no longer carries '0x04A6,7,3,4', so this case "
                "has stopped testing the mutation")
            with open(path, "w", newline="") as f:
                f.write(drifted)
            r = run_tool(FIRMWARE, *SPAN, "--csv", "--check", path)
        self.assertEqual(r.returncode, 1)
        self.assertIn("differs from what this run produced", r.stderr.decode())
        self.assertIn("regenerate rather than edit", r.stderr.decode())

    def test_an_unreadable_path_is_reported_rather_than_compared(self):
        r = run_tool(FIRMWARE, *SPAN, "--csv", "--check",
                     os.path.join(HERE, "no-such-table.csv"))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, b"")
        self.assertNotIn("Traceback", r.stderr.decode())


class Collisions(unittest.TestCase):
    """What `--collisions` keeps, and the premise it is committed for."""

    def test_every_row_is_referenced_by_both_images(self):
        """The invariant the committed file exists to hold.

        Not the same as "the file is what the tool prints" -- the previous
        class already says that. This is the property a *reader* relies on:
        that a row can be called a collision without re-running anything. A
        `--collisions` that filtered on `total` rather than on both sides, or
        that dropped the last row, would still reproduce a committed file
        generated by the same wrong filter.
        """
        rows = rows_of(COLLISION_TABLE)
        self.assertTrue(rows, "the collision table is empty")
        for row in rows:
            self.assertGreater(int(row["main_ec"]), 0, row["addr"])
            self.assertGreater(int(row["pd_image"]), 0, row["addr"])
            self.assertEqual(int(row["total"]),
                             int(row["main_ec"]) + int(row["pd_image"]), row)

    def test_the_filter_is_the_two_sides_and_nothing_else(self):
        """The filter's definition, against the unfiltered run rather than
        against a stored copy -- so widening, narrowing or inverting it is
        visible here even though `--check` would stay green on a table the
        wrong filter had generated."""
        whole = {r["addr"]: r for r in rows_of(WHOLE_TABLE)}
        wanted = [r["addr"] for r in rows_of(WHOLE_TABLE)
                  if int(r["main_ec"]) and int(r["pd_image"])]
        got = [r["addr"] for r in rows_of(COLLISION_TABLE)]
        self.assertEqual(got, wanted)
        self.assertEqual(got, sorted(got), "rows are not in address order")
        self.assertEqual(whole[got[0]], rows_of(COLLISION_TABLE)[0])

    def test_the_span_collisions_are_the_span_tables_own(self):
        """The issue's premise, as a property: the `0x0400`-`0x07FF` collisions
        the §5.1 audit sampled from one of are the *same rows* the full-range
        table carries, not a second measurement of them.

        `0x04A6` is then in that set because it is in the set, and a reader can
        see from the two tables alone that it is one address among several --
        which is the claim the issue made about it, and which no number here
        pins.
        """
        span = [r["addr"] for r in rows_of(SPAN_TABLE)
                if int(r["main_ec"]) and int(r["pd_image"])]
        whole = [r["addr"] for r in rows_of(COLLISION_TABLE)
                 if SPAN[0] <= r["addr"] <= SPAN[1]]
        self.assertEqual(span, whole)
        self.assertIn("0x04A6", whole)
        self.assertTrue(len(span) > 1,
                        "0x04A6 is alone again, so the issue's premise that "
                        "the audit met it by sampling no longer holds")

    def test_a_lo_above_hi_is_refused(self):
        r = run_tool(FIRMWARE, "0x07FF", "0x0400")
        self.assertEqual(r.returncode, 2)
        self.assertIn("lo must not be above hi", r.stderr.decode())

    def test_both_flags_are_refused_without_csv(self):
        """Neither flag means anything against the summary, and a run that
        accepted one and ignored it would report the span totals as if the
        request had been honoured."""
        for flag in (("--collisions",), ("--check", "x.csv")):
            with self.subTest(flag=flag):
                r = run_tool(FIRMWARE, *SPAN, *flag)
                self.assertEqual(r.returncode, 2)
                self.assertIn("about the --csv table", r.stderr.decode())


class Agreement(unittest.TestCase):
    """The cross-check §1 exists for, held over the wider span too."""

    def test_the_span_table_agrees_with_trace_xdata_refs(self):
        rows = {r["addr"]: r for r in rows_of(SPAN_TABLE)}
        for addr, (main_ec, pd) in AGREEMENT.items():
            with self.subTest(addr=addr):
                got = counts_only(addr)
                self.assertEqual(got.get("pd-image", 0), pd, addr)
                self.assertEqual(sum(v for k, v in got.items()
                                     if k != "pd-image"), main_ec, addr)
                self.assertEqual((int(rows[addr]["main_ec"]),
                                  int(rows[addr]["pd_image"])), (main_ec, pd))

    def test_the_whole_range_table_agrees_too(self):
        """The same three addresses, read out of the `0x0000`-`0xFFFF` run.

        The counting code is shared, so this cannot fail on the bytes -- what it
        can fail on is a range that changed the addressing. That is the drift
        the issue asks to keep closed ("keep the tool's agreement check intact
        for the wider span"), and a widening that quietly stopped being the
        same measurement would otherwise be invisible.
        """
        rows = {r["addr"]: r for r in rows_of(WHOLE_TABLE)}
        for addr, (main_ec, pd) in AGREEMENT.items():
            with self.subTest(addr=addr):
                self.assertEqual((int(rows[addr]["main_ec"]),
                                  int(rows[addr]["pd_image"])),
                                 AGREEMENT[addr])

    def test_the_summary_counts_the_span_the_table_lists(self):
        """The printed summary is derived from the same `counts` the CSV is,
        so the two cannot disagree about which addresses are collisions. If
        `csv_table()` filtered somewhere `main()` did not, this is where it
        shows."""
        r = run_tool(FIRMWARE, *WHOLE)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        both = int(re.search(r"both\s+:\s+(\d+)", r.stdout.decode()).group(1))
        self.assertEqual(both, len(rows_of(COLLISION_TABLE)))


class Calibration(unittest.TestCase):
    """The vocabulary the tool's own contract is written in."""

    def test_a_zero_in_the_summary_is_not_an_absence(self):
        """The same rule the census suites hold, on the other tool.

        `pd-xdata-overlap.md` §6 says every zero in this family means "not
        found by this method", and `0x04A7`'s absent PD column is the one the
        whole `0x04A6` reading turns on. A summary that said an address was
        "absent" or "unused" would be making the claim the page is careful not
        to make, in the one place a reader skims.
        """
        r = run_tool(FIRMWARE, *SPAN, "--page", "0x40")
        text = r.stdout.decode()
        for word in ("absent", "unused", "not used", "free", "unreferenced"):
            self.assertNotIn(word, text.lower(),
                             f"the summary reads as {word!r}, which is the "
                             "claim this tool does not make")
        self.assertIn("address(es) with sites in each image", text)

    def test_the_marker_note_goes_to_stderr_so_a_redirect_stays_a_csv(self):
        """`--csv > file` is how both committed tables were made, so a note on
        stdout would corrupt them."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "no-marker.800")
            with open(FIRMWARE, "rb") as src, open(path, "wb") as dst:
                data = bytearray(src.read())
                data[0x20040:0x20048] = b"ITE8850-X"
                dst.write(bytes(data))
            r = run_tool(path, *SPAN, "--csv")
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("no 'ITE8850-PD' marker", r.stderr.decode())
        rows = rows_of(r.stdout.decode())
        self.assertEqual(rows[0]["addr"], "0x0400")
        self.assertNotIn("ITE8850-PD", r.stdout.decode())


if __name__ == "__main__":
    unittest.main(verbosity=2, argv=[sys.argv[0]])