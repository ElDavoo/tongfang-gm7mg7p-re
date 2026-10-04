#!/usr/bin/env python3
"""`decode_fan_tables.py`'s claims, held against the image they came from
(issue #1227).

The tool's `--self-test` holds its refusals, its stopping rule on fixtures, and
an oracle transcribed from the byte reads. This is the rest: what
`../../docs/findings/ec-default-fan-tables.md` publishes, held here as a claim
about **this** image rather than about a transcription of it, and the two
in-place corrections the write-up carries.

**Every image assertion opens `ec/firmware/GMxMGxx_11.800`.** A firmware whose
tables moved makes these red instead of leaving the write-up agreeing with a
transcription of last month's bytes, which is the failure
`test_bank1_e582_framing.py` states as the reason a case must not be written
against a fixture when the claim is about the shipped image.

**What is held is a claim, not a census.** The break address, the four entries
the handler reaches, the extent's endpoints and the branch at `0x887E` are all
properties of *this* image and do not move on every landing suite. The suite
never asserts how many tables there are, how many rows the CSV has, or how many
references an address has -- a test that asserts a count of the tree is a value
every merge has to edit, and `CLAUDE.md` says so after three incidents. Where a
count *is* the finding -- the number of member entries, which is the issue's
first question -- it is held as the predicate's break rather than as a number
compared against a list of the same length.

Nothing here touches hardware. No register is written, none is read back, and
no laptop, EC or Windows machine is involved: the inputs are the committed
firmware, the committed vendor tables and the committed CSVs.
"""
import collections
import csv
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
EC = HERE.parent
REPO = EC.parent
TOOL = HERE / "decode_fan_tables.py"
DEFAULTS = HERE / "fan_table_defaults.py"
FIRMWARE = EC / "firmware" / "GMxMGxx_11.800"
CSV_PATH = EC / "annotations" / "fan-table-curves.csv"
PRIOR_CSV = EC / "annotations" / "fan-table-defaults.csv"
BRANCH_TABLE = EC / "annotations" / "bank-relative-branch-targets.csv"
ANNOTATION = EC / "annotations" / "manual-fan-ctrl-0751.md"
PRIOR = REPO / "docs" / "findings" / "ec-fan-table-defaults.md"
VENDOR_ROOT = REPO / "vendor" / "control-center-3.9.18.0" / "UserFanTables"

sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("decode_fan_tables", TOOL)
dft = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dft)
_spec2 = importlib.util.spec_from_file_location("fan_table_defaults", DEFAULTS)
ftd = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(ftd)
_gfi_spec = importlib.util.spec_from_file_location(
    "gen_findings_index", HERE / "gen_findings_index.py")
GFI = importlib.util.module_from_spec(_gfi_spec)
_gfi_spec.loader.exec_module(GFI)

IMAGE = FIRMWARE.read_bytes()
WALK = dft.walk(IMAGE, dft.pointer_base(IMAGE))
ROWS, REFUSED = dft.decode_all(IMAGE, WALK)
BY_ADDR = {r["code_addr"]: r for r in ROWS}


def run(*args):
    """The tool as a subprocess, for the exit codes a unit call would hide."""
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True)


def _prose(path) -> str:
    """A markdown file as one line, with emphasis and quoting stripped.

    A claim about calibration should not turn on where a line broke, on which
    sentence happens to be bolded, or on the correction being a blockquote --
    so all three are normalised away before anything is matched against it.
    """
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        lines.append(line.lstrip().lstrip(">").replace("*", " "))
    return " ".join(" ".join(lines).split())


class TheWalkStopsWhereTheBytesStop(unittest.TestCase):
    """The extent, as a measurement rather than a pattern that stopped."""

    def test_the_pointer_base_is_read_out_of_the_image(self):
        self.assertEqual(dft.pointer_base(IMAGE), 0x60F2)

    def test_the_walk_stops_at_the_address_the_write_up_quotes(self):
        self.assertEqual(WALK.break_addr, 0x6162)

    def test_the_bytes_at_the_break_are_the_ones_the_write_up_quotes(self):
        self.assertEqual(WALK.break_bytes, b"\x41\x37\x05\x05")

    def test_every_accepted_entry_is_a_stride_apart(self):
        for _, cpu, gpu in WALK.entries:
            self.assertEqual(gpu, cpu + dft.PAIR_STRIDE)

    def test_the_predicate_rejects_a_pair_that_is_only_below_the_window(self):
        # The rule is the relation, not the magnitude: this pair is entirely
        # inside the common area and is still not a member.
        self.assertFalse(dft.is_member(b"\x56\xa2\x57\x72"))

    def test_the_predicate_rejects_a_second_pointer_in_a_bank_window(self):
        self.assertFalse(dft.is_member(b"\x56\xa2\xd7\x62"))

    def test_the_predicate_is_reported_on_every_run(self):
        # A count without the rule that produced it is not a measurement, so
        # the rule is printed rather than left in this file.
        out = run().stdout
        self.assertIn("membership predicate", out)
        self.assertIn("second pointer is its first plus 0xC0", out)

    def test_the_run_reports_the_first_rejected_entry_and_its_bytes(self):
        out = run().stdout
        self.assertIn("first rejected entry at 0x6162", out)
        self.assertIn("41 37 05 05", out)

    def test_the_scan_bound_is_not_presented_as_an_end(self):
        # `walk()` bounds its scan. Reaching the bound reports `break_addr` as
        # None rather than passing for an end.
        w = dft.walk(IMAGE, dft.pointer_base(IMAGE), limit=8)
        self.assertIsNone(w.break_addr)
        self.assertEqual(len(w), 2)

    def test_a_full_run_reports_a_bound_reached_as_not_an_end(self):
        # Into a buffer rather than onto stdout, which is what the other report
        # assertion here does too -- a suite that printed the whole report would
        # bury the runner's own dots.
        buf = io.StringIO()
        dft.report(IMAGE, stream=buf)
        self.assertNotIn("this is a bound, not an end", buf.getvalue())


class ThePayloadCorroboratesIt(unittest.TestCase):
    """The other side: the tables the walk names, as a contiguous block."""

    def test_the_named_tables_are_one_contiguous_run(self):
        _lo, _hi, _n, contiguous = dft.payload_extent(WALK)
        self.assertTrue(contiguous)

    def test_that_run_ends_immediately_below_the_pointer_table(self):
        lo, hi, _n, _c = dft.payload_extent(WALK)
        self.assertEqual(hi, WALK.base)
        self.assertLess(lo, hi)

    def test_the_run_is_as_long_as_its_spans_make_it(self):
        lo, hi, distinct, _c = dft.payload_extent(WALK)
        self.assertEqual(hi - lo, distinct * dft.TABLE_BYTES)

    def test_no_two_accepted_entries_name_the_same_table(self):
        _lo, _hi, distinct, _c = dft.payload_extent(WALK)
        self.assertEqual(distinct, 2 * len(WALK))

    def test_no_accepted_pointer_reaches_a_bank_window(self):
        for _, cpu, gpu in WALK.entries:
            self.assertLess(cpu, 0x8000)
            self.assertLess(gpu, 0x8000)

    def test_every_table_is_forty_eight_bytes_of_the_record_the_handler_copies(self):
        # The length is the handler's own: `0x888D`'s two copy loops are
        # `cjne a,#0x30`. Asserted as the constant the tool uses, so a change
        # to what it copies is a change here.
        self.assertEqual(dft.TABLE_BYTES, 0x30)


class TheDecodeHolds(unittest.TestCase):
    """The layout, over every table rather than over a chosen few."""

    def test_every_accepted_table_decodes(self):
        self.assertEqual(REFUSED, [])

    def test_the_layout_properties_hold_across_every_table(self):
        for name, (passed, total) in dft.tally(ROWS, REFUSED).items():
            with self.subTest(check=name):
                self.assertEqual((passed, total), (total, total))

    def test_the_shape_checks_are_not_vacuous(self):
        # Three properties that could all be True of a decode that read every
        # row as zero. Held as the rows actually carrying the ramps.
        counts = dft.tally(ROWS, REFUSED)
        self.assertEqual(set(counts),
                         {"upt_ramp", "downt_ramp", "duty_bounded"})

    def test_the_gap_offset_is_zero_in_every_table(self):
        # The one offset neither `SetEcFanTable` writes nor `GetEcFanTable`
        # reads. Named rather than passed over.
        for row in ROWS:
            with self.subTest(addr=row["code_addr"]):
                self.assertEqual(row["blob"][ftd.GAP], 0x00)

    def test_the_ramp_check_would_reject_a_descending_row(self):
        # Otherwise "the ramp rises" could be satisfied by anything.
        self.assertFalse(dft._ramp_ok([0, 54, 50, 58]))
        self.assertTrue(dft._ramp_ok([0, 54, 58, 0xFF, 0xFF]))

    def test_the_downt_row_is_not_asserted_to_start_at_zero(self):
        # The first `DownT` is 48 in every table measured. That is a floor the
        # layout does not predict, so the check holds the ramp and not the
        # first entry -- the mistake this suite exists to catch.
        firsts = {r["table"]["DownT"][0] for r in ROWS}
        self.assertEqual(firsts, {48})
        for row in ROWS:
            self.assertTrue(dft.shape_checks(row["table"])["downt_ramp"])


class TheBandIsReportedNotAsserted(unittest.TestCase):
    """The one thing the decode does not explain, held as a known finding."""

    def test_some_tables_have_a_downt_at_or_above_the_next_upt(self):
        banded = [r for r in ROWS if dft.band_failures(r["table"])]
        self.assertTrue(banded, "no table broke the band; the finding moved")

    def test_the_band_finding_is_named_in_the_report(self):
        out = run().stdout
        self.assertIn("hysteresis band", out)
        self.assertIn("DownT", out)

    def test_the_office_tables_are_among_them(self):
        # `ec-fan-table-defaults.md` §3 held the two Office tables byte
        # identical, so both sides of the identity break the band together and
        # neither finding becomes vacuous.
        for addr in (0x56D2, 0x5702):
            with self.subTest(addr=addr):
                self.assertTrue(dft.band_failures(BY_ADDR[addr]["table"]))

    def test_the_failures_arrive_in_whole_entries(self):
        # The write-up's §6 sentence is about the *grouping*, not the tally:
        # a failure that takes both halves of one pointer pair is a property
        # of that pair, and a lone half failing is a different thing again.
        # Held as the grouping the image produces rather than as a count --
        # the number of failing tables is the tool's to print, and what this
        # suite fixes is that the write-up's sentence cannot drift from it.
        banded = [(r, dft.band_failures(r["table"])) for r in ROWS]
        banded = [(r, f) for r, f in banded if f]
        halves = collections.defaultdict(set)
        for row, _fails in banded:
            halves[row["index"]].add(row["fan"])
        both = sorted(i for i, fs in halves.items() if fs == {"CPU", "GPU"})
        alone = sorted(i for i, fs in halves.items() if fs != {"CPU", "GPU"})
        self.assertTrue(both, "no entry failed on both halves; the shape moved")
        # Every lone-half failure is the GPU half of an entry whose CPU half
        # passes -- the asymmetry the sentence turns on. An entry that failed
        # on both halves would be in `both`, so this holds by construction
        # unless the set is empty.
        self.assertTrue(alone, "no lone-half failure; the shape moved")
        for i in alone:
            with self.subTest(entry=i):
                self.assertEqual(halves[i], {"GPU"})

    def test_the_report_and_the_write_up_agree_on_the_grouping(self):
        # The sentence in §6 quotes the report's grouping block. If a table
        # moved, one of the two has to be wrong and this says which -- so the
        # entry lists are compared, not just the header either side carries.
        banded = [(r, dft.band_failures(r["table"])) for r in ROWS]
        banded = [(r, f) for r, f in banded if f]
        expected = {}
        for line in dft.band_grouping_text(banded):
            label, sep, entries = line.strip().partition(": entries")
            if not sep:
                continue  # the block's own header, which carries no entries
            expected[label] = [int(n) for n in entries.split(",")]

        out = run().stdout
        self.assertIn("grouped by pointer-pair entry:", out)
        for label, indexes in expected.items():
            with self.subTest(where="report", label=label):
                self.assertIn(f"{label}: entries "
                              + ", ".join(str(i) for i in indexes), out)

        # ...and the write-up carries the same lists, rather than describing
        # the failures as clustering on whichever tables a reader saw first.
        doc = _prose(REPO / "docs" / "findings" / "ec-default-fan-tables.md")
        self.assertNotIn("cluster on the Office tables", doc)
        for label, indexes in expected.items():
            with self.subTest(where="write-up", label=label):
                self.assertIn(f"{label}: entries "
                              + ", ".join(str(i) for i in indexes), doc)


class TheHandlerReachesFourEntries(unittest.TestCase):
    """The four the mailbox selects, pinned to the handler's own offsets."""

    def test_the_four_slots_are_the_first_four_entries(self):
        role_of = dft.roles(IMAGE, WALK)
        for index, entry_addr in ((0, 0x60F2), (1, 0x60F6),
                                  (2, 0x60FA), (3, 0x60FE)):
            with self.subTest(index=index):
                self.assertEqual(WALK.entries[index][0], entry_addr)
                self.assertIn(index, role_of)

    def test_the_roles_come_from_the_handler_offsets_not_a_local_list(self):
        # `SLOTS` belongs to the tool that decodes the handler's own selection;
        # this file restating it would be a second place to edit when the
        # handler changes. Compared by value rather than by identity because
        # `importlib` loads the tool twice here, once through each spec.
        self.assertEqual(dft.roles.__module__, "decode_fan_tables")
        self.assertEqual(dft.ftd.SLOTS, ftd.SLOTS)

    def test_the_roles_name_the_modes_the_service_applies(self):
        role_of = dft.roles(IMAGE, WALK)
        self.assertTrue(role_of[0].startswith("gaming/0x0F5F=2"))
        self.assertTrue(role_of[3].startswith("turbo/0x0F5F=1"))

    def test_no_entry_beyond_the_four_carries_a_role(self):
        role_of = dft.roles(IMAGE, WALK)
        self.assertEqual(len(role_of), len(ftd.SLOTS))


class HowTheHandlerIsReached(unittest.TestCase):
    """`0x887E`: the branch that is not a call, and what it does not settle."""

    def test_the_branch_decodes_to_the_handler(self):
        self.assertEqual(dft.handler_branch(IMAGE), 0x888D)

    def test_the_displacement_is_relative_to_the_next_instruction(self):
        # `jz` is two bytes, so the target is `addr + 2 + disp`. Held as the
        # wrong reading too, because the point is that it lands somewhere
        # plausible: reading it as a three-byte instruction gives `0x888E`,
        # which is a real address inside the handler and would pass a check
        # that only asked whether it landed nearby.
        raw = dft.read_code(IMAGE, dft.BRANCH[0], 2)
        self.assertEqual(raw, bytes((0x60, 0x0D)))
        self.assertEqual(dft.BRANCH[0] + 2 + raw[1], dft.HANDLER)
        self.assertNotEqual(dft.BRANCH[0] + 3 + raw[1], dft.HANDLER)

    def test_the_gate_is_06c2(self):
        # `mov dptr,#0x06c2` is the three bytes before the `movx` that feeds the
        # `jz`, so the immediate is TAIL[1:3] rather than TAIL[0:2].
        raw = dft.read_code(IMAGE, dft.BRANCH[0] - 4, len(dft.TAIL))
        self.assertEqual(raw, dft.TAIL)
        self.assertEqual(raw[0], 0x90)          # mov dptr,#imm16
        self.assertEqual((raw[1] << 8) | raw[2], 0x06C2)
        self.assertEqual(raw[3], 0xE0)          # movx a,@dptr
        self.assertEqual(raw[4:6], bytes((0x60, 0x0D)))   # the jz itself

    def test_the_fall_through_re_seeds_the_base_and_the_branch_does_not(self):
        # The two arms of the branch, from the bytes: the fall-through calls
        # the seeding routine, and the handler is what the branch lands on.
        raw = dft.read_code(IMAGE, dft.BRANCH[0] + 2, 3)
        self.assertEqual(raw, bytes((0x12, 0x86, 0x53)))

    def test_the_committed_branch_table_agrees(self):
        rows = list(csv.DictReader(BRANCH_TABLE.open(encoding="utf-8")))
        hits = [r for r in rows
                if int(r["runtime"], 16) == 0x887E
                and int(r["target"], 16) == 0x888D]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["opcode"], "jz")

    def test_no_lcall_or_ljump_names_the_handler(self):
        # The reason a call-graph search reports no caller, and the reason the
        # branch above is the whole of how the handler is entered here.
        for opcode in (0x12, 0x02):
            with self.subTest(opcode=opcode):
                hits = [off for off in range(len(IMAGE) - 2)
                        if IMAGE[off] == opcode
                        and (IMAGE[off + 1] << 8 | IMAGE[off + 2]) == 0x888D]
                self.assertEqual(hits, [])

    def test_the_listing_the_correction_cites_says_the_same_thing(self):
        asm = (EC / "decompiled" / "bank0" / "8749.asm").read_text()
        self.assertIn("887E     60 0d", asm)
        self.assertIn("jz       0x888d", asm)

    def test_r2_agrees_when_it_is_installed(self):
        # The independent decoder, per `manual-fan-ctrl-0751.md` §7's
        # convention. Skipped rather than failed when absent: the hosted
        # runners install it, a bare checkout may not have it.
        with tempfile.TemporaryDirectory() as tmp:
            bank = Path(tmp) / "bank0.bin"
            made = subprocess.run(
                [sys.executable, str(HERE / "make_bank_image.py"),
                 str(FIRMWARE), "0", "0x08000", str(bank)],
                capture_output=True, text=True)
            if made.returncode != 0:
                self.skipTest("make_bank_image.py failed")
            if not shutil.which("r2"):
                self.skipTest("r2 is not installed here")
            out = subprocess.run(
                ["r2", "-a", "8051", "-e", "scr.color=0", "-q",
                 "-c", "s 0x887A; pd 4", str(bank)],
                capture_output=True, text=True)
        self.assertIn("jz 0x888d", out.stdout)


class TheTwoToolsAgree(unittest.TestCase):
    """The four selected tables, decoded twice by two tools that share no
    decode code.

    `fan_table_defaults.py` walks the handler's offsets; this file's tool walks
    the pointer table. They meet on the eight rows covering Gaming, Office
    (both `0x0782` states) and Turbo. Agreeing on all eight is what says the
    walk did not pick up a different pair than the handler does -- a plausible
    failure that a self-consistent tool cannot see.
    """

    def setUp(self):
        self.rows = {(r["code_addr"], r["fan"]):
                     (r["upt"], r["downt"], r["duty"])
                     for r in csv.DictReader(
                         CSV_PATH.open(encoding="utf-8"))}

    def test_the_prior_tools_rows_are_all_present_here(self):
        for row in csv.DictReader(PRIOR_CSV.open(encoding="utf-8")):
            with self.subTest(addr=row["code_addr"], fan=row["fan"]):
                self.assertIn((row["code_addr"], row["fan"]), self.rows)

    def test_the_prior_tools_decodes_agree_with_this_ones(self):
        for row in csv.DictReader(PRIOR_CSV.open(encoding="utf-8")):
            key = (row["code_addr"], row["fan"])
            with self.subTest(addr=key[0], fan=key[1]):
                self.assertEqual(self.rows[key],
                                 (row["upt"], row["downt"], row["duty"]))

    def test_the_two_office_slots_really_are_the_same_table(self):
        # `vendor_comparison()` keys by mode, so both Office entries collapse
        # onto one table. That is only sound while they are byte-identical, so
        # the identity is held here against the image rather than assumed.
        # `BY_ADDR` keys on the CODE address, and `0x56D2`/`0x5702` are the
        # CPU blobs of the two Office entries.
        self.assertEqual(BY_ADDR[0x56D2]["blob"], BY_ADDR[0x5702]["blob"])
        self.assertEqual(BY_ADDR[0x5792]["blob"], BY_ADDR[0x57C2]["blob"])

    def test_one_row_per_project_and_mode_is_produced(self):
        rows, _notes = dft.vendor_comparison(IMAGE, WALK)
        self.assertEqual(len(rows), len(set(
            (p, m, f) for p, m, f, _ec, _fields in rows)),
            "the comparison emitted a duplicate row")


class AgainstTheShippedTables(unittest.TestCase):
    """The issue's third question: the EC's tables against the vendor's."""

    def test_the_committed_project_directories_are_there(self):
        self.assertTrue(VENDOR_ROOT.is_dir())
        projects = sorted(p.name for p in VENDOR_ROOT.iterdir() if p.is_dir())
        self.assertTrue(projects)

    def test_every_shipped_table_is_parsed_as_the_service_shapes_it(self):
        tables = dft.vendor_tables()
        self.assertTrue(tables)
        for key, table in tables.items():
            with self.subTest(table=key):
                self.assertIn("CPU", table)
                self.assertIn("GPU", table)

    def test_no_project_and_mode_fan_pair_matches_byte_for_byte(self):
        rows, notes = dft.vendor_comparison(IMAGE, WALK)
        self.assertTrue(rows, "nothing was compared")
        for project, mode, fan, _ec, fields in rows:
            with self.subTest(project=project, mode=mode, fan=fan):
                for name, (mine, theirs) in fields.items():
                    self.assertNotEqual(
                        mine, theirs,
                        f"{project} {mode} {fan} {name} matched; if that is "
                        f"real it is a finding, not a pass")

    def test_a_shipped_gpu_row_of_all_zeros_is_reported_not_compared(self):
        rows, notes = dft.vendor_comparison(IMAGE, WALK)
        self.assertTrue(any("every shipped entry is zero" in n for n in notes))
        # ...and no all-zero shipped fan ends up in the comparison.
        for _project, _mode, fan, _ec, _fields in rows:
            self.assertEqual(fan, "CPU")

    def test_a_mode_no_project_ships_is_a_note_rather_than_a_silence(self):
        _rows, notes = dft.vendor_comparison(IMAGE, WALK)
        self.assertTrue(any("no committed project ships this table" in n
                            for n in notes))


class TheCommittedArtefacts(unittest.TestCase):
    """The generated CSV, in both directions."""

    def test_the_committed_csv_reproduces(self):
        self.assertEqual(run("--check").returncode, 0)

    def test_a_doctored_cell_is_caught(self):
        text = CSV_PATH.read_text(encoding="utf-8")
        doctored = text.replace("0x56A2", "0x56A3", 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doctored.csv"
            path.write_text(doctored, encoding="utf-8")
            got = subprocess.run(
                [sys.executable, str(TOOL), "--check", "--csv-file", str(path)],
                capture_output=True, text=True)
        self.assertEqual(got.returncode, 1)

    def test_a_missing_csv_fails_rather_than_being_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "absent.csv"
            got = subprocess.run(
                [sys.executable, str(TOOL), "--check", "--csv-file", str(path)],
                capture_output=True, text=True)
            self.assertEqual(got.returncode, 1)
            self.assertFalse(path.exists())

    def test_no_run_offers_an_output_argument(self):
        self.assertNotIn("--out", run("--help").stdout)

    def test_a_full_run_leaves_the_tree_byte_identical(self):
        before = CSV_PATH.read_bytes()
        run()
        run("--check")
        run("--self-test")
        self.assertEqual(CSV_PATH.read_bytes(), before)

    def test_the_csv_carries_the_spans_the_extent_is_re_derived_from(self):
        rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
        addrs = {r["code_addr"] for r in rows}
        self.assertEqual(addrs, {f"0x{a:04X}" for _, a, _ in WALK.entries}
                         | {f"0x{b:04X}" for _, _, b in WALK.entries})
        for row in rows:
            with self.subTest(row=row["code_addr"]):
                self.assertIn(row["fan"], ("CPU", "GPU"))
                self.assertIn(row["role"] != "-", (True, False))


class TheInPlaceCorrections(unittest.TestCase):
    """What this change corrected, and that it left the old wording visible."""

    def test_the_prior_write_ups_open_item_is_still_there(self):
        # `ec-fan-table-defaults.md` §6 said the extent was not determined.
        # Per CLAUDE.md a retraction stays visible beside its correction, so
        # the sentence is asserted rather than deleted.
        self.assertIn("The pointer table's extent was not determined",
                      PRIOR.read_text(encoding="utf-8"))

    def test_the_annotation_still_says_at_least_twenty(self):
        text = ANNOTATION.read_text(encoding="utf-8")
        self.assertIn("At least twenty CODE pointer pairs", text)

    def test_the_annotation_carries_a_correction_naming_the_measured_end(self):
        text = ANNOTATION.read_text(encoding="utf-8")
        self.assertIn("0x6162", text)

    def test_the_annotation_still_says_no_site_reaches_the_handler(self):
        # The sentence this change corrects, kept visible per the calibration
        # rule.
        self.assertIn("No site in §2 reaches this code",
                      ANNOTATION.read_text(encoding="utf-8"))

    def test_the_correction_names_the_branch_that_reaches_it(self):
        # Case-insensitively: the listing block spells it `0x887e` to match
        # `8749.asm` and the prose spells it `0x887E`, and which one a file
        # uses is not what this test is about.
        text = ANNOTATION.read_text(encoding="utf-8").lower()
        self.assertIn("0x887e", text)
        self.assertIn("0x888d", text)


class WhatThisChangeDeliberatelyLeftAlone(unittest.TestCase):
    """The boundaries, held so a later change has to decide to cross them."""

    def test_registers_yaml_has_no_0x0f00_entry(self):
        # `check_power_profile.py` names `0x0F00` as the one address allowed
        # to sit outside the file, and the power-profile patch relies on that
        # empty cell.
        text = (EC / "annotations" / "registers.yaml").read_text(encoding="utf-8")
        self.assertNotIn("addr: 0x0F00", text)

    def test_0782_is_still_present_untested(self):
        # Read statically here; a `status:` move is for a behavioural
        # observation and nothing in this change observed anything.
        text = (EC / "annotations" / "registers.yaml").read_text(encoding="utf-8")
        block = text.split("addr: 0x0782", 1)[1][:600]
        self.assertIn("status: present-untested", block)

    def test_no_ghidra_annotation_row_was_added_for_the_tables(self):
        # The tables are data, not code. An annotation row at an address with
        # no function is reported and fails the build.
        text = (EC / "annotations" / "ghidra-functions.csv").read_text(
            encoding="utf-8")
        for addr in ("0x60F2", "0x5672", "0x56A2"):
            self.assertNotIn(f",{addr},", text)

    def test_the_write_up_claims_no_live_observation(self):
        # Normalised before matching: the disclaimer is prose and may wrap
        # across a line, and a claim about calibration should not turn on where
        # a line broke.
        text = _prose(REPO / "docs" / "findings" / "ec-default-fan-tables.md")
        self.assertIn("no laptop, EC or Windows machine", text)
        self.assertIn("no register is read back", text)
        for overclaim in ("was observed", "we read back", "the run confirmed"):
            self.assertNotIn(overclaim, text)

    def test_the_write_up_is_where_the_index_reads(self):
        # The index is `gen_findings_index.py`'s output, not a committed file
        # (2026-10-04), so "indexed" means a titled file in docs/findings/.
        self.assertIn("ec-default-fan-tables.md",
                      {name for name, _ in GFI.entries(str(REPO))})

    def test_neither_file_says_the_ec_reloads_on_its_own(self):
        # `0x06C2` is `present-untested`, so a statically reachable branch whose
        # predicate is a runtime byte licenses a statement about
        # *reachability* and not one about what the EC does. The unconditional
        # form is the one a skimmer reads, and it is what the correction in
        # `manual-fan-ctrl-0751.md` used to carry. The three captures have the
        # gate reading zero on the machine they came from, which is the next
        # test's subject and deliberately not folded in here: it is evidence
        # about a value, not about the shape of the branch.
        for path in (REPO / "docs" / "findings" / "ec-default-fan-tables.md",
                     ANNOTATION):
            text = _prose(path)
            for overclaim in ("reloads its own curve on a scheduler pass",
                              "reloads its own fan table on a scheduler",
                              "the EC reloads on its own"):
                with self.subTest(path=path.name, phrase=overclaim):
                    self.assertNotIn(overclaim, text)
            # The bounded form is asserted instead, so the check cannot pass by
            # the sentence simply being deleted.
            self.assertIn("reachable from a scheduler pass whenever `0x06C2` "
                          "reads zero", text)

    def test_the_captures_are_read_for_the_gate_value_not_assumed_absent(self):
        # Both prose files once said the `ec_watch` captures "record changes
        # only and carry no `0x06c2` change rows, which says the byte was
        # steady across those windows and not what it was". That reads the
        # baseline line as carrying no value, which is the opposite of what
        # `ec_timer_capture.py` writes it for -- "a byte that never moved is
        # still on record with the value it held". So the three captures are
        # read here, from the committed files, and the prose is held to what
        # they carry.
        for name in ("sweep", "perturb", "suspend"):
            path = (REPO / "evidence" / "ec-watch" /
                    f"2026-09-24-06c2-06db-{name}-linux.csv")
            lines = path.read_text(encoding="utf-8").splitlines()
            baseline = [ln for ln in lines if ln.startswith("# baseline")]
            self.assertEqual(len(baseline), 1, name)
            self.assertIn("0x06C2=0x00", baseline[0], name)
            # The data rows are one per change, so a byte with no row of its
            # own never moved inside the window. Counting them is the claim the
            # prose makes, not a count of the repository.
            self.assertFalse([ln for ln in lines
                              if not ln.startswith("#")
                              and ",0x06C2," in ln], name)

        for path in (REPO / "docs" / "findings" / "ec-default-fan-tables.md",
                     ANNOTATION):
            text = _prose(path)
            with self.subTest(path=path.name):
                # The misreading, in the two shapes it was written in.
                self.assertNotIn("and not what it was", text)
                # The value, and the limit that keeps it from being
                # "the gate is normally open": three windows are not a
                # characterisation, and the byte's value outside them is open.
                self.assertIn("0x06C2=0x00", text)
                self.assertIn("baseline", text)
                self.assertIn("present-untested", text)
                self.assertIn("not established", text)

    def test_the_gate_status_did_not_move_on_this_evidence(self):
        # The captures are evidence about a value, and the strongest reading of
        # them is still not a live test -- so `registers.yaml` keeps its
        # `present-untested` and nothing in this change moves a `status:`.
        import yaml
        regs = yaml.safe_load(
            (EC / "annotations" / "registers.yaml").read_text(
                encoding="utf-8"))["registers"]
        row = next(r for r in regs if r.get("name") == "XDATA_06C2")
        self.assertEqual(row["addr"], 0x06C2)
        self.assertEqual(row["status"], "present-untested")

    def test_neither_file_claims_every_mode_was_compared(self):
        # `M3T1` is shipped by no committed project, so "no mode matches any
        # shipped table" covered a mode that was never compared -- and the
        # write-up did not say so while the tool printed the exclusion.
        for path in (REPO / "docs" / "findings" / "ec-default-fan-tables.md",
                     ANNOTATION):
            text = _prose(path)
            for overclaim in ("No mode matches any shipped table",
                              "none matches on any row"):
                with self.subTest(path=path.name, phrase=overclaim):
                    self.assertNotIn(overclaim, text)
            # The exclusion itself, not merely the table's name: `M3T1` is
            # named in both files for other reasons, so asserting the bare
            # string would pass on a file that had dropped the caveat.
            self.assertIn("no committed project ships", text.lower())

    def test_the_turbo_exclusion_is_the_tools_own_note(self):
        # The write-up's Turbo exclusion is not a judgement about the curve;
        # it is the absence the tool reports, so hold the two to each other.
        _rows, notes = dft.vendor_comparison(IMAGE, WALK)
        self.assertTrue(any("M3T1" in n and "no committed project ships" in n
                            for n in notes), notes)
        self.assertIn("no committed project ships this table", run().stdout)


if __name__ == "__main__":
    unittest.main()