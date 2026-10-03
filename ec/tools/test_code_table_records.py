#!/usr/bin/env python3
"""The claims `docs/findings/code-table-record-writers.md` is written on, and
the refusals that keep the decoder in `code_table_records.py` from guessing
(issue #236).

Two halves, the split the tree uses elsewhere. The **parse half** runs on
hand-built fixtures: the `90 hi lo` / `7A nn` argument pair, each way it can
fail, and the decode of one record's three bytes. The **claim half** runs the
tool against the committed firmware and the committed CSVs: the seven `0xA530
call sites` decode to the bases and counts the write-up tabulates, the 12
records on the `0x0400`-`0x045F` page carry the destinations and values the
issue lists, §6's entry rule re-runs as a negative, and `--check` reproduces
the committed table.

**The entry-rule negative is asserted as a rule, not as a set.** `xdata-
0400-045f.md` §6 leaves 50 bytes out of `registers.yaml` because the EC image
has no direct `MOV DPTR,#addr` site for them, and the finding is that *no*
CODE record names one either. Pinning the 50 addresses here would be a count
of the tree written as a literal -- every byte §6 enters or drops moves it --
so `EntryRuleTests` derives the not-entered set from the committed sites CSV
at test time and asserts the property over whatever that set is on the day.
The set is asserted to be non-empty, because a rule that holds over no bytes
holds over anything.

**Nothing here is a live observation.** No register is read back and no
hardware is touched: the assertions are about bytes in
`ec/firmware/GMxMGxx_11.800` and rows in committed CSVs. A record that stores
`0x00` is a *record*, and the twelve page rows are pinned as such -- the
suites do not say the byte reads as zero, and CLAUDE.md's
readback-is-not-acting rule is why.

**What is deliberately not pinned.** The 226-record and 115-destination
figures, and the per-destination tallies. Those are arithmetic over two
committed corpora that a future helper would move, and `code_table_records.py
--check` already holds the table they are derived from against a fresh
generation. Pinning them as literals would make this suite red for a change
that added a helper and was correct to. What is pinned is the seven named page
bytes, which is the claim the issue is for.
"""
import contextlib
import csv
import importlib.util
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
EC = HERE.parent
TOOL = HERE / "code_table_records.py"
FIRMWARE = EC / "firmware" / "GMxMGxx_11.800"
RECORDS_CSV = EC / "annotations" / "xdata-code-table-records.csv"
SITES_CSV = EC / "annotations" / "xdata-0400-045f-sites.csv"
CALL_TARGETS = EC / "annotations" / "bank-call-targets.csv"

# The tool imports disasm8051 and trace_xdata_refs by bare module name, so the
# tool directory goes on the path before it is loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("code_table_records", TOOL)
ctr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctr)


def read_rows(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


class NoWrites(contextlib.AbstractContextManager):
    """Make any write-mode `open` inside the block raise.

    `inc_dptr_sites.py`'s suite pins this from both sides and says why; the
    short of it is that asserting "the committed files are unchanged after a
    run" is also satisfied by a run that wrote identical bytes, and the
    property worth holding is that the tool cannot write one at all.
    """

    def __enter__(self):
        self.real_open = open
        recorder = self

        def guarded(file, mode="r", *args, **kwargs):
            if any(flag in mode for flag in ("w", "a", "x", "+")):
                raise AssertionError(
                    f"code_table_records.py opened {file!r} for writing "
                    f"(mode {mode!r}); it reads committed files and writes "
                    f"stdout only")
            return recorder.real_open(file, mode, *args, **kwargs)

        self._patch = mock.patch("builtins.open", side_effect=guarded)
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()
        return False


class DecodeTests(unittest.TestCase):
    """The argument-pair decode, on a buffer of its own.

    The fixtures supply bytes rather than borrowing the committed image,
    because the shapes that must be *refused* are shapes the real firmware
    does not contain: no `0xA530` site sets R2 from a register, so that case
    is unreachable from the image and a refusal nothing can reach is a
    refusal nothing tests.
    """

    # `mov DPTR,#0x8453` / `mov R2,#0x02` / `lcall 0xA530`, at file 40.
    PAIR = bytes((0x90, 0x84, 0x53, 0x7A, 0x02, 0x12, 0xA5, 0x30))

    def fixture(self):
        buf = bytearray(b"\x00" * 64)
        buf[40:48] = self.PAIR
        return buf

    def test_the_pair_decodes_base_and_count(self):
        self.assertEqual(ctr.decode_call_site(bytes(self.fixture()), 45),
                         (0x8453, 2))

    def test_the_base_is_big_endian_and_the_count_is_the_last_byte(self):
        # The order is the whole of the decode, and a byte-swapped base is a
        # table that exists elsewhere in this image rather than a wrong
        # number that would look wrong.
        buf = self.fixture()
        buf[41], buf[42] = 0x53, 0x84
        self.assertEqual(ctr.decode_call_site(bytes(buf), 45)[0], 0x5384)

    def test_a_pair_that_is_not_immediately_before_the_call_is_refused(self):
        # A `mov DPTR` five bytes early, with something else in the slots the
        # rule reads: the shape is the claim, and a sliding window would
        # decode this one.
        buf = self.fixture()
        buf[43] = 0x8A
        with self.assertRaises(ctr.Undecodable) as caught:
            ctr.decode_call_site(bytes(buf), 45)
        self.assertIn("not `mov R2,#imm8`", str(caught.exception))

    def test_an_r2_set_from_a_register_is_refused_by_name(self):
        buf = self.fixture()
        buf[43] = 0x8A
        with self.assertRaises(ctr.Undecodable) as caught:
            ctr.decode_call_site(bytes(buf), 45)
        self.assertIn("0x8A", str(caught.exception))

    def test_a_missing_mov_dptr_is_refused_by_name(self):
        buf = self.fixture()
        buf[40:43] = b"\x00\x00\x00"
        with self.assertRaises(ctr.Undecodable) as caught:
            ctr.decode_call_site(bytes(buf), 45)
        self.assertIn("not `mov DPTR,#imm16`", str(caught.exception))

    def test_an_offset_that_is_not_a_call_is_refused(self):
        # The census's `file_offset` column is the tool's input, so a row
        # pointing into the middle of an instruction would otherwise decode
        # five bytes of data as an argument pair.
        buf = self.fixture()
        buf[45] = 0x90
        with self.assertRaises(ctr.Undecodable) as caught:
            ctr.decode_call_site(bytes(buf), 45)
        self.assertIn("no `lcall`", str(caught.exception))

    def test_an_offset_past_the_end_is_refused_not_indexed(self):
        with self.assertRaises(ctr.Undecodable):
            ctr.decode_call_site(bytes(self.fixture()), 10_000)

    def test_a_record_decodes_big_endian_with_the_value_third(self):
        # base 0x2000 in the common area, one record: 0x12 0x34 0x56 is
        # XDATA 0x1234 = 0x56.
        buf = bytearray(b"\x00" * 0x2000)
        buf[0x2000:0x2003] = bytes((0x12, 0x34, 0x56))
        xdata, value, runtime, off = ctr.record_at(bytes(buf), 0x2000,
                                                   "common", 0)
        self.assertEqual((xdata, value), (0x1234, 0x56))
        self.assertEqual((runtime, off), (0x2000, 0x2000))

    def test_a_record_index_steps_by_the_record_length(self):
        buf = bytearray(b"\x00" * 0x2009)
        buf[0x2006:0x2009] = bytes((0xAB, 0xCD, 0xEF))
        got = ctr.record_at(bytes(buf), 0x2000, "common", 2)
        self.assertEqual(got[:2], (0xABCD, 0xEF))
        self.assertEqual(got[2], 0x2000 + 3 * 2)

    def test_a_record_running_past_the_image_is_refused(self):
        # Truncation has to raise rather than pad: a partial record read as a
        # whole one puts a destination in the table no store ever reached.
        buf = bytearray(b"\x00" * 0x20)
        with self.assertRaises(ctr.Undecodable):
            ctr.record_at(bytes(buf), 0x2000, "common", 0)

    def test_a_bank1_record_reads_from_bank1_and_not_bank0(self):
        # The bank window is the reason this tool reads REGIONS rather than
        # writing the ranges out: bank1 starts at file 0x10000, and reading
        # 0x453 there instead would decode bank0's bytes as the table.
        buf = bytearray(b"\x00" * 0x11000)
        buf[0x10453:0x10456] = bytes((0x04, 0x40, 0x00))
        buf[0x08453:0x08456] = bytes((0xDE, 0xAD, 0xBE))
        self.assertEqual(ctr.record_at(bytes(buf), 0x8453, "bank1", 0)[:2],
                         (0x0440, 0x00))

    def test_the_bank_window_matches_the_trace_tool_it_reads(self):
        # `file_offset_for` and `file_region` are this file's own; REGIONS is
        # `trace_xdata_refs`'s. If the two ever disagree about a bank edge,
        # every record past it is read out of the wrong bank, so the round
        # trip is asserted rather than trusted.
        for name, lo, hi, base, _ in ctr.REGIONS:
            if base is None:
                continue
            for off in (lo, lo + 0x137, hi - 1):
                region = ctr.file_region(off)
                self.assertEqual(region, name)
                runtime = ctr.file_offset_for(region, off - lo + base)
                self.assertEqual(runtime, off)


class InRoutineTests(unittest.TestCase):
    """The shape whose base and count live inside the helper, not at a call.

    Built as a miniature of `0xBFDE` rather than borrowing the real routine,
    so the two properties that make the rule work are each isolated: the base
    is the `mov DPTR` **two** bytes are read through, and the count is the
    `cjne` immediate that closes the loop. The real routine loads a third
    `mov DPTR` and reads one byte through it, which is the case a
    "first `mov DPTR` followed by a `movc`" rule gets wrong.
    """

    # mov dptr,#0x1674 / mov a,#0x18 / movx @dptr,a / clr a / ret, then the
    # loop: mov dptr,#0x64ff (one byte read), mov dptr,#0x64fd (two), cjne.
    def routine(self, base=0x64FD, value_at=0x64FF, count=0x5A):
        buf = bytearray(b"\x00" * 0x7000)
        i = 0x2000
        def put(*op):
            nonlocal i
            buf[i:i + len(op)] = bytes(op)
            i += len(op)
        put(0x90, 0x16, 0x74)          # mov dptr, #0x1674 (an unrelated store)
        put(0x74, 0x18, 0xF0, 0xE4)    # mov a,#0x18 / movx @dptr,a / clr a
        put(0x90, value_at >> 8, value_at & 0xFF)   # mov dptr, #0x64ff
        put(0x93)                       # movc -- ONE byte read here
        put(0x90, base >> 8, base & 0xFF)           # mov dptr, #0x64fd
        put(0x93, 0x93)                 # movc -- TWO bytes read here
        put(0xB4, count, 0x00)          # cjne a,#0x5a,<rel>
        put(0x22)                       # ret
        return buf

    def test_the_base_is_the_dptr_two_bytes_are_read_through(self):
        # Taking the first qualifying `mov DPTR` would land on 0x64ff, which
        # is the *value* of the record at 0x64fd + 2.
        self.assertEqual(ctr.routine_table(bytes(self.routine()), "common",
                                           0x2000), (0x64FD, 0x5A))

    def test_the_count_is_the_cjne_immediate(self):
        _, count = ctr.routine_table(bytes(self.routine(count=0x2A)),
                                     "common", 0x2000)
        self.assertEqual(count, 0x2A)

    def test_the_scan_stops_at_the_routine_and_does_not_run_on(self):
        # A second, decoy table past the `ret` must not be reached: the first
        # is the routine's.
        buf = self.routine()
        buf[0x2100] = 0x90
        buf[0x2101:0x2103] = b"\x7f\xff"
        base, _ = ctr.routine_table(bytes(buf), "common", 0x2000)
        self.assertEqual(base, 0x64FD)

    def test_a_routine_with_no_cjne_is_refused(self):
        buf = self.routine()
        i = buf.index(bytes((0xB4, 0x5A, 0x00)))
        buf[i] = 0x00
        with self.assertRaises(ctr.Undecodable) as caught:
            ctr.routine_table(bytes(buf), "common", 0x2000)
        self.assertIn("cjne", str(caught.exception))

    def test_a_routine_with_no_two_byte_read_is_refused(self):
        # One `movc` under the last `mov DPTR` means no destination pair, and
        # the tool says so rather than falling back to the single-read DPTR.
        # The byte replaced is the *second* `movc` (0x200F), not an operand
        # of the `mov DPTR` above it -- a `0x00` in an operand is `nop`, and
        # a routine that still reads two bytes would decode.
        buf = self.routine()
        buf[0x200F] = 0x00
        with self.assertRaises(ctr.Undecodable) as caught:
            ctr.routine_table(bytes(buf), "common", 0x2000)
        self.assertIn("two bytes", str(caught.exception))

    def test_an_address_outside_every_region_is_refused(self):
        with self.assertRaises(ctr.Undecodable) as caught:
            ctr.routine_table(bytes(self.routine()), "bank1", 0x2000)
        self.assertIn("outside every mapped region", str(caught.exception))

    def test_an_address_past_the_end_of_the_image_is_refused(self):
        # A routine that maps cleanly onto a region but lands beyond the
        # buffer is a short image, and says so -- which is a different answer
        # from "the table is not here", and the two must not read alike.
        buf = self.routine()
        with self.assertRaises(ctr.Undecodable) as caught:
            ctr.routine_table(bytes(buf), "bank1", 0x8400)
        self.assertIn("past the end", str(caught.exception))

    def test_a_truncated_tail_does_not_index_past_the_buffer(self):
        # The walk reads `d[i+1]`/`d[i+2]` for `mov DPTR` and `d[i+1]` for
        # `cjne`, so an instruction claiming bytes the buffer does not have is
        # a shape a byte-oriented walk gets an IndexError on. Cutting the
        # routine off inside its last `mov DPTR` must refuse, not raise.
        buf = self.routine()
        buf[0x200B] = 0x90          # the base's `mov DPTR`, left unterminated
        del buf[0x200C:]
        with self.assertRaises(ctr.Undecodable):
            ctr.routine_table(bytes(buf), "common", 0x2000)


class CommittedImageTests(unittest.TestCase):
    """The decode, against the committed firmware and census."""

    @classmethod
    def setUpClass(cls):
        cls.image = FIRMWARE.read_bytes()
        cls.rows, cls.bad = ctr.collect(cls.image)

    def test_every_committed_call_site_decodes(self):
        self.assertEqual(
            self.bad, [],
            f"{len(self.bad)} table(s) refused, which is never silently the "
            f"same as a helper with no callers")

    def test_the_a530_helpers_sites_and_their_tables(self):
        # The write-up's per-call-site table, as (runtime, base, count).
        # Each is a claim about named bytes at a named address, which is what
        # the write-up is for; the totals above it are not pinned here.
        scatter = next(h for h in ctr.HELPERS if h["target"] == 0xA530)
        got = {}
        for site in ctr.call_sites(scatter):
            base, count, _ = ctr.table_for(
                self.image, scatter, int(site["file_offset"], 16),
                site["region"])
            got[site["runtime"]] = (base, count)
        self.assertEqual(got, {
            "0x82C9": (0x8594, 0x01),
            "0x82FD": (0x8561, 0x11),
            "0x83B7": (0x8453, 0x43),
            "0x841D": (0x851C, 0x17),
            "0xC740": (0xC6E2, 0x0A),
            "0xC7AC": (0xC7A1, 0x02),
            "0xC7F2": (0xC7BD, 0x10),
        })

    def test_the_in_routine_helper_reproduces_its_recorded_table(self):
        helper = next(h for h in ctr.HELPERS if h["shape"] == "args_in_routine")
        base, count = ctr.routine_table(self.image, helper["region"],
                                        helper["target"])
        self.assertEqual((base, count), (helper["base"], helper["count"]))
        # And the destination bound `xdata-0440-readers.md` §7.3 states, held
        # as a range over the records rather than as the range's endpoints.
        dests = [int(r["xdata"], 16) for r in self.rows
                 if r["helper"] == helper["name"]]
        self.assertTrue(all(0x1600 <= d <= 0x16F0 for d in dests),
                        "every 0xBFDE record destination is in 0x1600-0x16F0")

    def test_the_seven_a530_sites_are_the_committed_ones(self):
        # `collect()` walking `bank-call-targets.csv` is the input claim: the
        # population is the census's, not a threshold this tool chose.
        scatter = next(h for h in ctr.HELPERS if h["target"] == 0xA530)
        committed = {r["runtime"] for r in read_rows(CALL_TARGETS)
                     if int(r["target"], 16) == 0xA530}
        self.assertEqual({s["runtime"] for s in ctr.call_sites(scatter)},
                         committed)
        self.assertEqual(len(committed), 7)


class PageRecordTests(unittest.TestCase):
    """The twelve records on the `0x0400`-`0x045F` page.

    This is the finding: seven bytes on the page, twelve records, and every
    one of them invisible to the `MOV DPTR` scan its per-address table is cut
    from. They are pinned as records -- a destination and a stored value read
    out of a table -- and nothing here says what the byte reads as afterwards.
    """

    PAGE_LO, PAGE_HI = 0x0400, 0x045F

    # The issue's own list, as (destination, call site, record index, value).
    PAGE_RECORDS = (
        (0x043E, "0x83B7", 12, 0x20),
        (0x0440, "0x83B7", 0, 0x00),
        (0x0440, "0x83B7", 2, 0x00),
        (0x0440, "0x841D", 9, 0x00),
        (0x0457, "0x82C9", 0, 0x83),
        (0x0457, "0x82FD", 2, 0x80),
        (0x0457, "0x83B7", 1, 0x00),
        (0x0457, "0x841D", 1, 0x05),
        (0x0459, "0x841D", 2, 0x00),
        (0x045B, "0x83B7", 52, 0x00),
        (0x045C, "0x83B7", 36, 0x00),
        (0x045F, "0x83B7", 13, 0x00),
    )

    @classmethod
    def setUpClass(cls):
        cls.image = FIRMWARE.read_bytes()
        cls.rows, _ = ctr.collect(cls.image)

    def page_rows(self):
        return [r for r in self.rows
                if self.PAGE_LO <= int(r["xdata"], 16) <= self.PAGE_HI]

    def test_the_twelve_records_carry_the_destinations_and_values(self):
        got = sorted((int(r["xdata"], 16), r["call_site"],
                      int(r["record_index"]), int(r["value"], 16))
                     for r in self.page_rows())
        self.assertEqual(got, sorted(self.PAGE_RECORDS))

    def test_the_records_land_on_seven_distinct_bytes(self):
        self.assertEqual(len({d for d, _, _, _ in self.PAGE_RECORDS}), 7)
        self.assertEqual(len({r["xdata"] for r in self.page_rows()}), 7)

    def test_two_of_the_seven_have_no_direct_writer_at_all(self):
        # The mechanism, asserted rather than described. `0x043E` and
        # `0x0440` have EC-side sites that never store, so the record is not
        # an extra writer on top of a `MOV DPTR` one -- it is the only writer
        # this repository has found for either byte, which is why `0x0440`
        # carried a 43-reader / 0-writer row for as long as it did.
        writes = {int(r["addr"], 16) for r in read_rows(SITES_CSV)
                  if r["region"] in ("common", "bank0", "bank1")
                  and "write" in r["access"]}
        seeded = {int(r["xdata"], 16) for r in self.page_rows()}
        with_direct_writer = seeded & writes
        self.assertEqual(with_direct_writer,
                         {0x0457, 0x0459, 0x045B, 0x045C, 0x045F})
        self.assertEqual(seeded - with_direct_writer, {0x043E, 0x0440})

    def test_the_other_five_seeds_sit_under_a_direct_writer(self):
        # The other direction, so the case above cannot pass by the page
        # having no writers anywhere: five of the seven are seeded on top of
        # direct sites, which is what "silently, on top of them" means and
        # why a byte count alone would understate the class.
        writes = {int(r["addr"], 16) for r in read_rows(SITES_CSV)
                  if r["region"] in ("common", "bank0", "bank1")
                  and "write" in r["access"]}
        seeded = {int(r["xdata"], 16) for r in self.page_rows()}
        self.assertEqual(seeded & writes,
                         {0x0457, 0x0459, 0x045B, 0x045C, 0x045F})

    def test_0457_is_seeded_four_different_ways(self):
        # The sharpest byte on the page, and the reason this is more than a
        # zero: four records, four values, four call sites.
        got = sorted((r["call_site"], int(r["value"], 16))
                     for r in self.page_rows() if r["xdata"] == "0x0457")
        self.assertEqual(got, [("0x82C9", 0x83), ("0x82FD", 0x80),
                               ("0x83B7", 0x00), ("0x841D", 0x05)])

    def test_the_record_value_is_a_stored_value_not_a_readback(self):
        # Calibration as an assertion: `0x043E` is the only non-zero seed
        # among the two page bytes with no direct writer (`0x0440`'s three
        # records all store `0x00`), and this suite never claims what the byte
        # reads. What it does claim is that the record stores 0x20 -- the
        # sentence the `registers.yaml` note is allowed to make.
        seeds = {r["xdata"]: int(r["value"], 16) for r in self.page_rows()
                 if r["xdata"] == "0x043E"}
        self.assertEqual(seeds, {"0x043E": 0x20})


class EntryRuleTests(unittest.TestCase):
    """`xdata-0400-045f.md` §6's negative, as a rule rather than a set.

    A byte enters `registers.yaml` iff the EC image has a direct
    `MOV DPTR,#addr` site for it. The finding is that the record walk does not
    reach any of the bytes that rule leaves out -- so the rule holds for the
    whole page, and not only for `0x0440`.

    **Why the set is recomputed rather than written out.** §6's 50 addresses
    move every time a byte on the page is entered or dropped, and a literal
    list of 50 of them in a test is a line every such change has to edit --
    the shape CLAUDE.md's no-totals rule is about. So the not-entered set is
    derived from the committed sites CSV here, and the assertion is the
    property over it. It is asserted non-empty: a rule over no bytes holds
    over anything and would pass vacuously.
    """

    PAGE_LO, PAGE_HI = 0x0400, 0x045F

    def not_entered(self):
        ec = {int(r["addr"], 16) for r in read_rows(SITES_CSV)
              if r["region"] in ("common", "bank0", "bank1")}
        return {a for a in range(self.PAGE_LO, self.PAGE_HI + 1) if a not in ec}

    def test_the_not_entered_set_is_not_empty(self):
        # The vacuity guard. If the sites CSV ever stopped carrying this
        # page's rows, every rule below would hold over the empty set and
        # say nothing -- which is `run-tests.sh`'s empty-discovery failure
        # one level up.
        self.assertTrue(self.not_entered(),
                        "no byte on the page is without an EC-side site, so "
                        "the entry rule's negative has no population")

    def test_no_code_record_names_a_not_entered_byte(self):
        rows, bad = ctr.collect(FIRMWARE.read_bytes())
        self.assertEqual(bad, [])
        named = {int(r["xdata"], 16) for r in rows}
        overlap = named & self.not_entered()
        self.assertEqual(
            overlap, set(),
            f"{len(overlap)} byte(s) §6 leaves out are named by a CODE "
            f"record: {', '.join(hex(a) for a in sorted(overlap))}. Either "
            f"the entry rule or the record census is wrong, and both are "
            f"committed claims")

    def test_the_entered_bytes_the_records_reach_all_have_a_site(self):
        # The converse, so the negative above cannot pass by the record walk
        # having reached nothing at all: the records do land on the page, and
        # every byte they land on is one §6 admits.
        rows, _ = ctr.collect(FIRMWARE.read_bytes())
        on_page = {int(r["xdata"], 16) for r in rows
                   if self.PAGE_LO <= int(r["xdata"], 16) <= self.PAGE_HI}
        self.assertTrue(on_page, "no record reaches the page at all")
        self.assertEqual(on_page & self.not_entered(), set())


class CommittedTableTests(unittest.TestCase):
    """`--check` round-trip, and the refusals `--check` cannot reach.

    `--check` holding the committed table against a fresh generation is the
    reproducibility claim; it is not the claim that the table says what the
    write-up says, and `PageRecordTests` is that. Two things are added here
    because a byte-for-byte diff cannot see them: that the tool writes no
    file, and that it fails rather than exiting zero on a table it could not
    decode.
    """

    def test_check_reproduces_the_committed_table(self):
        self.assertEqual(ctr.check_table(
            ctr.render(ctr.collect(FIRMWARE.read_bytes())[0]),
            str(RECORDS_CSV)), 0)

    def test_check_fails_on_a_drifted_table(self):
        # `--check` going green is only a claim if it can go red. `open` with
        # `newline=""` rather than `Path.read_text`, which has no such
        # parameter and would translate the committed CRLF terminators into
        # the very difference this case is trying to fake.
        with open(RECORDS_CSV, newline="") as handle:
            on_disk = handle.read()
        self.assertIn("\r\n", on_disk, "the committed table is CRLF")
        drifted = on_disk.replace("0x20", "0x21", 1)
        self.assertNotEqual(drifted, on_disk, "the fixture really drifted")
        stderr = io.StringIO()
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                         newline="") as handle:
            handle.write(drifted)
            path = handle.name
        try:
            with contextlib.redirect_stderr(stderr):
                rc = ctr.check_table(
                    ctr.render(ctr.collect(FIRMWARE.read_bytes())[0]), path)
            self.assertEqual(rc, 1)
            self.assertIn("differs from what this run produced",
                          stderr.getvalue())
        finally:
            os.unlink(path)

    def test_the_tool_writes_no_file(self):
        with NoWrites():
            rows, bad = ctr.collect(FIRMWARE.read_bytes())
            ctr.render(rows)
        self.assertEqual(bad, [])
        self.assertTrue(rows)

    def test_a_helper_with_no_committed_caller_is_reported_not_skipped(self):
        # The guard against the census lookup finding nothing and the census
        # reading as a clean sweep. A helper nobody calls is a question about
        # the census, and it must arrive as a refusal.
        helper = dict(ctr.HELPERS[0], target=0xDEAD)
        self.assertEqual(ctr.call_sites(helper), [])
        rows, bad = ctr.collect(FIRMWARE.read_bytes(),
                                path=str(CALL_TARGETS))
        self.assertNotIn("code_table_scatter_to_xdata",
                         {h for h, _, _ in bad},
                         "the real 0xA530 helper has committed callers")

    def test_a_census_missing_its_columns_is_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("a,b\n1,2\n")
            path = f.name
        try:
            with self.assertRaises(ValueError):
                ctr.call_sites(ctr.HELPERS[0], path)
        finally:
            os.unlink(path)

    def test_the_self_test_mode_passes_on_the_committed_image(self):
        proc = subprocess.run(
            [sys.executable, str(TOOL), str(FIRMWARE), "--self-test"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("self-test passed", proc.stdout)

    def test_a_page_filter_cannot_be_combined_with_check(self):
        # A filtered table diffed against the unfiltered committed one would
        # report every filtered row as a deletion -- a difference that says
        # nothing about the two runs.
        proc = subprocess.run(
            [sys.executable, str(TOOL), str(FIRMWARE), "--check",
             "--page", "0x0400-0x045F"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("cannot be combined", proc.stderr)

    def test_a_single_address_is_not_a_page(self):
        with self.assertRaises(ValueError):
            ctr.parse_page("0x0440")


class CsvShapeTests(unittest.TestCase):
    """The committed table's header, its locating columns, and that every
    column is used.

    `docs/findings/csv-column-usage-advice.md` is about a `Usage:` block that
    omits a flag; the same failure has a second form here, a column nobody
    reads. Every column in `COLUMNS` is named by the write-up or by a case
    here, and this holds the header to `COLUMNS` so a column cannot be added
    without someone deciding what reads it.

    The two locating columns are pinned on their own because they are the
    bridge to the second decoder: §3's `r2` spot checks are written against a
    `make_bank_image.py` bank image (`code_runtime`) and a reader holding only
    the committed firmware has the file offset (`code_file_offset`). Neither
    number appears in the prose, so `--check`'s byte-for-byte diff is the only
    thing that would notice one of them going wrong.
    """

    def test_the_committed_header_is_the_columns_the_tool_writes(self):
        with open(RECORDS_CSV, newline="") as handle:
            header = next(csv.reader(handle))
        self.assertEqual(tuple(header), ctr.COLUMNS)

    def test_every_committed_row_names_a_known_helper(self):
        for row in read_rows(RECORDS_CSV):
            self.assertIn(row["helper"], {h["name"] for h in ctr.HELPERS})

    def test_the_offset_columns_agree_with_the_committed_image(self):
        # Every committed row is re-derived from the bytes rather than
        # trusted: a `code_runtime` that drifted would send a reader's `r2`
        # to the wrong address, and a `code_file_offset` that drifted would
        # send them to a record that is not there. `--check` catches both --
        # it is a byte-for-byte diff -- but this names the row instead of
        # printing a unified diff.
        image = FIRMWARE.read_bytes()
        # Decoded once per helper rather than per row: `table_for` wants a
        # FILE OFFSET for the call site (what `bank-call-targets.csv` carries
        # and what `decode_call_site` reads bytes at), not the runtime address
        # the `call_site` column spells. Passing the runtime address here
        # decodes bank0's bytes as a bank1 instruction and refuses, which is
        # the tool behaving correctly about a caller's mistake.
        decoded = {}
        for helper in ctr.HELPERS:
            if helper["shape"] == "args_in_routine":
                # Keyed on the label `collect()` writes for it, which is the
                # routine's own address rather than a call site.
                decoded[(helper["name"], f"0x{helper['target']:04X}")] = (
                    ctr.table_for(image, helper, None, helper["region"]))
                continue
            for site in ctr.call_sites(helper):
                decoded[(helper["name"], site["runtime"])] = ctr.table_for(
                    image, helper, int(site["file_offset"], 16),
                    site["region"])
        for row in read_rows(RECORDS_CSV):
            index = int(row["record_index"])
            base, count, region = decoded[(row["helper"], row["call_site"])]
            self.assertLess(index, count)
            got = ctr.record_at(image, base, region, index)
            self.assertEqual(
                (f"0x{got[2]:04X}", f"0x{got[3]:05X}"),
                (row["code_runtime"], row["code_file_offset"]),
                f"{row['helper']} record {index} of {row['call_site']} "
                f"locates elsewhere than the committed row says")
            self.assertEqual((f"0x{got[0]:04X}", f"0x{got[1]:02X}"),
                             (row["xdata"], row["value"]))

    def test_the_committed_rows_are_the_generated_rows(self):
        # Both directions: the table is the tool's, and a hand-edited row
        # fails here rather than at `--check` only.
        generated = ctr.render(ctr.collect(FIRMWARE.read_bytes())[0])
        with open(RECORDS_CSV, newline="") as handle:
            self.assertEqual(handle.read(), generated)


if __name__ == "__main__":
    unittest.main()