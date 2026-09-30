#!/usr/bin/env python3
"""`fan_table_defaults.py`'s claims, held against the image they came from
(issue #100).

The tool's `--self-test` holds its refusals and an oracle transcribed from
`../annotations/manual-fan-ctrl-0751.md` §6. This is the rest: the
comparison `docs/findings/ec-fan-table-defaults.md` publishes, the
selector-to-mode join read back out of the committed decompile rather than
out of the tool, and the invariants this change deliberately left alone.

**Every image assertion opens `ec/firmware/GMxMGxx_11.800`.** A firmware
whose tables moved makes these red instead of leaving the write-up agreeing
with a transcription of last month's bytes, which is the failure
`test_bank1_e582_framing.py` states as the reason a case must not be written
against a fixture when the claim is about the shipped image.

**What is held is a claim, not a census.** The four CODE addresses, the two
byte-identities, the duty convention and the three top-duty figures are all
properties of *this* image and do not move on every landing suite. The suite
never asserts how many tables there are, how many rows the CSV has, or how
many references an address has -- a test that asserts a count of the tree is a
value every merge has to edit, and `CLAUDE.md` says so after three
incidents.

Nothing here touches hardware. No register is written, none is read back, and
no laptop, EC or Windows machine is involved: the inputs are the committed
firmware, the committed MQTT capture, the committed decompiled C# and the
committed CSV.
"""
import csv
import importlib.util
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import yaml

HERE = Path(__file__).resolve().parent
EC = HERE.parent
REPO = EC.parent
TOOL = HERE / "fan_table_defaults.py"
FIRMWARE = EC / "firmware" / "GMxMGxx_11.800"
CSV_PATH = EC / "annotations" / "fan-table-defaults.csv"
MQTT = (REPO / "evidence" / "mqtt-capture" /
        "2026-09-23-power-mode-cycle.jsonl")
SERVICE = (REPO / "windows" / "decompiled" / "v3.1.39.0" / "GCUService" /
           "MyControlCenter.MyFan.FanTable" / "FanTable_Manager1p5.cs")
VENDOR_MAP = REPO / "windows" / "vendor-ec-map.md"
WRITEOUT = REPO / "docs" / "findings" / "ec-fan-table-defaults.md"
PROCEDURE = REPO / "docs" / "hardware-tests" / "fan-table-defaults-0f5d.md"
REGISTERS = EC / "annotations" / "registers.yaml"

sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("fan_table_defaults", TOOL)
ftd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ftd)

# The four CODE pointer pairs, and the mailbox selector and `0x0782` bit that
# reach each. Transcribed from `../annotations/manual-fan-ctrl-0751.md` §6 and
# `docs/findings/ec-fan-table-defaults.md` §1, not from the tool.
PAIRS = {
    ("gaming", "-"): (0x56A2, 0x5762),
    ("office", "0"): (0x56D2, 0x5792),
    ("office", "1"): (0x5702, 0x57C2),
    ("turbo", "-"): (0x5672, 0x5732),
}

# The duty figures the comparison turns on, in %. The EC's own tables, and the
# service's published ones for the same mode. The two byte-identity results and
# the selector join are held where they belong -- as the pairs and as the
# decompile's own calls -- rather than as constants here that nothing reads.
TOP_DUTY = {"gaming": (90, 85), "office": (50, 55), "turbo": (90, 100)}


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, check=False)


class TheTablesResolve(unittest.TestCase):
    """The four pointer pairs, the two byte-identities, and the copy's reach.

    All of it read out of the image, so a firmware whose base or tables moved
    is a red run here rather than a write-up that has quietly stopped
    describing the bytes this machine ships.
    """

    @classmethod
    def setUpClass(cls):
        cls.image = FIRMWARE.read_bytes()
        cls.base, cls.rows = ftd.tables(cls.image)
        cls.by_key = {(r["mode"], r["oem_bit_2"]): r for r in cls.rows}

    def test_the_pointer_base_is_read_out_of_the_image(self):
        # Not asserted as a constant the tool carries: `pointer_base()` is
        # handed the bytes at 0x8653 and this holds the arithmetic.
        self.assertEqual(ftd.pointer_base(self.image), 0x60F2)
        self.assertEqual(self.base, 0x60F2)

    def test_the_seeding_site_is_the_one_manual_fan_ctrl_names(self):
        self.assertEqual(ftd.read_code(self.image, ftd.SEED, 6).hex(" "),
                         "7e 60 7f f2 90 08")

    def test_the_four_slots_resolve_to_the_four_expected_pairs(self):
        got = {k: (r["cpu"], r["gpu"]) for k, r in self.by_key.items()}
        self.assertEqual(got, PAIRS)

    def test_every_table_is_below_the_bank_window(self):
        # The reason no bank image is needed, and the reason the tool refuses
        # a slot at or above 0x8000 rather than reading it: the common area's
        # file offset is its runtime address and a bank's is not.
        for key, (cpu, gpu) in PAIRS.items():
            for addr in (cpu, gpu):
                self.assertLess(addr, 0x8000, key)

    def test_turbo_is_gaming_byte_for_byte(self):
        for fan in ("CPU", "GPU"):
            self.assertEqual(self.by_key[("turbo", "-")]["blob"][fan],
                             self.by_key[("gaming", "-")]["blob"][fan], fan)

    def test_the_two_office_tables_are_byte_identical(self):
        for fan in ("CPU", "GPU"):
            self.assertEqual(self.by_key[("office", "0")]["blob"][fan],
                             self.by_key[("office", "1")]["blob"][fan], fan)

    def test_the_two_identities_do_not_spread_to_the_other_modes(self):
        # What makes the first two findings findings: Gaming and Turbo agree,
        # Office agrees with itself, and Office differs from both. Without
        # this, "all four tables are the same bytes" would satisfy both cases.
        self.assertNotEqual(self.by_key[("office", "0")]["blob"]["CPU"],
                            self.by_key[("gaming", "-")]["blob"]["CPU"])

    def test_the_second_copy_reaches_the_mailbox_bytes(self):
        # 0x0F30 + 0x30 - 1 == 0x0F5F: the mailbox is the GPU blob's own last
        # three bytes, not three bytes the handler writes beside it.
        self.assertEqual(ftd.GPU_BASE + ftd.TABLE_BYTES - 1, ftd.MAILBOX[-1])
        self.assertEqual(ftd.MAILBOX,
                         tuple(a for a in range(ftd.MAILBOX[0],
                                                ftd.MAILBOX[0] + 3)))

    def test_the_copy_leaves_neither_magic_byte_in_the_mailbox(self):
        # `IsReadyToRead` (`FanTable_Manager1p5.cs:814`) unblocks when *both*
        # `0x0F5D` and `0x0F5E` differ from the magic, so one of the two
        # clearing is enough and the pair is what has to be checked.
        for key, row in self.by_key.items():
            over = ftd.writeback(row)
            self.assertNotIn(over[0x0F5D], ftd.MAGIC, key)
            self.assertNotIn(over[0x0F5E], ftd.MAGIC, key)

    def test_the_mailbox_bytes_are_the_last_three_duty_slots(self):
        # Which is what makes them duties: `0x0F5D` is GPU entry 13's stored
        # duty and `0x0F5F` entry 15's, and the selector rides in the slot the
        # service would have written a duty into.
        row = self.by_key[("turbo", "-")]
        over = ftd.writeback(row)
        for addr in ftd.MAILBOX:
            entry = (addr - ftd.GPU_BASE - ftd.DUTY)
            self.assertEqual(over[addr],
                             row["blob"]["GPU"][addr - ftd.GPU_BASE])
            self.assertLessEqual(entry, 15)


class TheDutyConvention(unittest.TestCase):
    """Duty is stored doubled, and the arithmetic that follows from it.

    Held on blobs built here rather than on this firmware's, so what is
    asserted is the rule `0xC8` is 100 % and not one table's contents.
    """

    def test_c8_is_one_hundred_percent(self):
        self.assertEqual(ftd.decode_blob(ftd._duty_blob(0xC8))["Duty"][0], 100)

    def test_the_magic_bytes_are_above_a_hundred_percent(self):
        # The hazard the hardware-test procedure is written around: the
        # handshake parks two duty slots at 126.5 % and 100.5 % of a scale
        # whose 100 % is 200.
        self.assertGreater(0xFD / 2, 100)
        self.assertGreater(0xC9 / 2, 100)
        self.assertEqual(0xFD // 2, 126)
        self.assertEqual(0xC9 // 2, 100)

    def test_a_47_byte_half_is_refused(self):
        # What `ec_image()` produces for one fan, and therefore what a decode
        # handed the writer's own output would have to reject.
        with self.assertRaises(ftd.NotDecodable):
            ftd.decode_blob(b"\x00" * 0x2F)


class TheComparison(unittest.TestCase):
    """EC decode against the committed `Fan/Table` publishes.

    The figures the write-up leads with, read out of the image and the capture
    rather than out of the tool's own report.
    """

    @classmethod
    def setUpClass(cls):
        cls.base, rows = ftd.tables(FIRMWARE.read_bytes())
        cls.cmp, cls.notes = ftd.compare(rows, str(MQTT))
        cls.rows = {(r["mode"], r["oem_bit_2"]): r for r in rows}

    def test_the_capture_carries_all_three_modes(self):
        # Otherwise the comparison below would be against a mode that was
        # never published, and every "DIFFERENT" would be vacuous.
        self.assertEqual(self.notes, [])
        self.assertEqual({k[0] for k in self.cmp}, {"gaming", "office", "turbo"})

    def test_no_modes_table_matches_the_service_byte_for_byte(self):
        for key, per_fan in self.cmp.items():
            for fan, fields in per_fan.items():
                for field, (ec, svc) in fields.items():
                    self.assertNotEqual(ec, svc, (key, fan, field))

    def test_the_top_duty_differs_in_every_mode(self):
        for mode, (ec, svc) in TOP_DUTY.items():
            got = self.cmp[(mode, "0" if mode == "office" else "-")]
            for fan in ("CPU", "GPU"):
                self.assertEqual(max(got[fan]["Duty"][0]), ec, (mode, fan))
                self.assertEqual(max(got[fan]["Duty"][1]), svc, (mode, fan))

    def test_office_tops_at_fifty_where_the_service_tops_at_fifty_five(self):
        got = self.cmp[("office", "0")]["CPU"]["Duty"]
        self.assertEqual(got[0], [0, 30, 30, 35, 45, 45, 50, 50, 50])
        self.assertEqual(got[1], [0, 30, 30, 35, 45, 48, 50, 55, 55])

    def test_the_ec_up_t_ramp_is_a_uniform_ladder_and_the_services_is_not(self):
        # The claim, measured on both sides rather than read off two rows of
        # numbers. `UpT` is the row that carries it; `Duty` steps by five on
        # the EC's and by 2/3/5/10/15 on the service's.
        gaming = self.cmp[("gaming", "-")]["CPU"]
        self.assertEqual(ftd.steps("UpT", gaming["UpT"][0]), "{3, 4}")
        self.assertEqual(ftd.steps("UpT", gaming["UpT"][1]), "{2, 4, 5, 8}")
        self.assertEqual(ftd.steps("Duty", gaming["Duty"][0]), "{0, 5, 10, 15, 30}")

    def test_gaming_and_turbo_really_do_decode_to_one_table(self):
        # The comparison reports each mode separately against a *different*
        # service table, so the identity behind two of the three rows is a
        # fact about the EC side only. Held here so a reader does not take the
        # report for three distinct EC curves, and so the byte-identity in
        # `TheTablesResolve` is visible in the comparison too.
        for fan in ("CPU", "GPU"):
            for field in ("UpT", "DownT", "Duty"):
                self.assertEqual(self.cmp[("gaming", "-")][fan][field][0],
                                 self.cmp[("turbo", "-")][fan][field][0],
                                 (fan, field))
            self.assertNotEqual(self.cmp[("gaming", "-")][fan]["Duty"][1],
                                self.cmp[("turbo", "-")][fan]["Duty"][1], fan)


class TheModeMapping(unittest.TestCase):
    """Selector 1/2/3 -> Turbo/Gaming/Office, held to the committed decompile.

    Two numberings meet in this file and the issue names both: the service's
    `0x0751` values (`0x00` Gaming, `0xA0` Office, `0x10` Turbo) and the
    mailbox's selectors (1 Turbo, 2 Gaming, 3 Office). The tool joins them in
    `SLOTS`, and a join that quietly inverted one of them would still produce
    four plausible-looking tables. So the three handshake calls are parsed
    back out of the committed `.cs` and the tool's selectors are held against
    them -- a re-derivation the tool cannot do, because the tool never reads
    the decompile.
    """

    REFRESH = re.compile(
        r"RefreshDefaultFanTable\(ref (?P<name>\w+), (?P<mode>\d+)\)")

    @classmethod
    def setUpClass(cls):
        cls.text = SERVICE.read_text(encoding="utf-8")
        cls.calls = {m.group("name"): int(m.group("mode"))
                     for m in cls.REFRESH.finditer(cls.text)}

    def test_the_three_handshakes_are_in_the_decompile(self):
        self.assertEqual(self.calls, {"DefaultFanTable_Gaming": 2,
                                      "DefaultFanTable_Office": 3,
                                      "DefaultFanTable_Turbo": 1})

    def test_the_tools_selectors_agree_with_them(self):
        for row in ftd.SLOTS:
            mode, selector, _, _, _ = row
            name = f"DefaultFanTable_{mode.capitalize()}"
            self.assertEqual(selector, self.calls[name], mode)

    def test_the_published_table_names_agree_with_vendor_ec_map(self):
        # `vendor-ec-map.md` "What `SetUserProfile` writes" is the row that
        # joins the mode to the table name the service applies, and it is the
        # only place in the tree that does.
        for mode, name in ftd.PUBLISHED_FOR.items():
            vendor = "Gaming" if mode == "gaming" else mode.capitalize()
            self.assertRegex(VENDOR_MAP.read_text(encoding="utf-8"),
                             rf"\|\s*{vendor}\s+`{name}`\s*\|",
                             f"{mode} -> {name} is not in the table row")


class TheCheckHoldsTheCSV(unittest.TestCase):
    """`--check` in both directions, and the file it will not create."""

    def _check(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fan-table-defaults.csv"
            if text is not None:
                path.write_text(text, encoding="utf-8")
            return ftd.check(FIRMWARE.read_bytes(), str(path), io.StringIO())

    def test_the_committed_csv_reproduces(self):
        self.assertEqual(self._check(CSV_PATH.read_text(encoding="utf-8")), 0)

    def test_a_doctored_cell_is_caught(self):
        doctored = CSV_PATH.read_text(encoding="utf-8").replace(
            "0 30 30 35 45 45 50 50 50", "0 30 30 35 45 45 50 50 55", 1)
        self.assertNotEqual(doctored, CSV_PATH.read_text(encoding="utf-8"))
        self.assertEqual(self._check(doctored), 1)

    def test_a_missing_csv_fails_rather_than_being_created(self):
        # A `--check` that wrote the file it is checking would decide what the
        # file says, and the refusal has to be in the tool rather than in this
        # suite's good intentions.
        self.assertEqual(self._check(None), 1)
        self.assertTrue(CSV_PATH.exists())

    def test_no_mode_offers_an_output_argument(self):
        # Over the parser rather than the docstring, which names the write
        # modes in order to say there are none.
        source = TOOL.read_text(encoding="utf-8")
        parser = source[source.index("def main("):]
        self.assertNotIn('"--out', parser)
        self.assertNotIn('"--write', parser)

    def test_a_full_run_leaves_the_tree_byte_identical(self):
        before = self._status()
        for mode in ([], ["--csv"], ["--check"], ["--self-test"]):
            self.assertEqual(run(*mode).returncode, 0, mode)
        self.assertEqual(self._status(), before)

    @staticmethod
    def _status():
        proc = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                              capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise unittest.SkipTest("git is not available here")
        return proc.stdout


class WhatThisChangeDeliberatelyLeftAlone(unittest.TestCase):
    """The two refusals this issue invites, recorded so a later branch sees
    they were decisions.

    `check_power_profile.py` names `0x0F00` as the one address permitted to sit
    outside `registers.yaml` ("Only the fan table is allowed to be outside the
    file") and `linux/patches/gm7mg7p-power-profile/profile-map.csv` relies on
    that empty cell while citing this very mechanism. So the mailbox has no
    entry and `0x0782` has not moved off `present-untested`: this work reads
    `0x0782` bit 2 statically and changes nothing about its behaviour, and a
    `status:` is for a behavioural observation. Doing the `0x0F00` entry
    properly is its own issue against that open power-profile PR.
    """

    def setUp(self):
        # `registers.yaml` is the structured source of truth and its `addr:`
        # is an int to a YAML reader -- or a list, for the entries that cover a
        # block -- so the file is read as YAML rather than grepped: a regex
        # over the prose would miss a decimal `addr:` and would also match the
        # dozens of `0x0F5D`-shaped strings the notes carry.
        self.regs = yaml.safe_load(REGISTERS.read_text(encoding="utf-8"))
        self.addrs = set()
        for entry in self.regs["registers"]:
            addr = entry["addr"]
            self.addrs.update(addr if isinstance(addr, list) else [addr])

    def test_the_mailbox_window_still_has_no_register_entry(self):
        for addr in (0x0F00, 0x0F5D, 0x0F5E, 0x0F5F):
            self.assertNotIn(addr, self.addrs,
                             f"0x{addr:04X} gained a registers.yaml entry")

    def test_0782_is_still_present_untested(self):
        entry = next(r for r in self.regs["registers"] if r["addr"] == 0x0782)
        self.assertEqual(entry["name"].split(" (")[0], "BIOS_OEM_2")
        self.assertEqual(entry["status"], "present-untested")

    def test_the_write_up_and_the_procedure_are_both_there(self):
        self.assertTrue(WRITEOUT.exists())
        self.assertTrue(PROCEDURE.exists())

    def test_the_procedure_is_marked_not_run(self):
        # `CLAUDE.md`: nothing in this change may state or imply a live test
        # happened, and the heading is the place a reader looks first.
        head = PROCEDURE.read_text(encoding="utf-8")[:1200]
        self.assertIn("**Status: not run (issue #100).**", head)

    def test_the_write_up_claims_no_live_observation(self):
        # A single stray sentence claiming a register was read back would
        # undo the calibration the whole file is written to preserve, and no
        # lint looks for it.
        text = WRITEOUT.read_text(encoding="utf-8")
        for phrase in ("was read back", "we observed on hardware",
                       "the run showed", "captured live"):
            self.assertNotIn(phrase, text, phrase)

    def test_the_committed_csv_has_a_row_per_slot_and_fan(self):
        with CSV_PATH.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(list(rows[0]), list(ftd.CSV_COLUMNS))
        # Two fans per slot, and the slots the tool resolves. Held as the
        # pairs it names, not as a number.
        self.assertEqual({(r["mode"], r["oem_bit_2"], r["fan"]) for r in rows},
                         {(m, o, f) for m, o in PAIRS for f in ("CPU", "GPU")})


if __name__ == '__main__':
    unittest.main()
