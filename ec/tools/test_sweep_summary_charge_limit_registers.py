"""
Test that the six charge-limit registers are absent from the AC plug-in sweep summary.

This test verifies the finding in docs/findings/charge-limit-registers-absent-from-ac-plugin-sweep.md:
the charge-limit registers (0x07B9, 0x07D0, 0x07D1, 0x0522, 0x0523, 0x030E, 0x030F) do not appear
in the 2026-09-18 AC plug-in sweep summary file.
"""

import unittest
from pathlib import Path


SWEEP_SUMMARY_FILE = Path(__file__).parent.parent.parent / "evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv"

CHARGE_LIMIT_REGISTERS = {
    0x07B9,  # CHARGE_CTRL
    0x07D0,  # DBD1 / BATTERY_CHARGE_LIMIT_DOWN
    0x07D1,  # DBD2
    0x0522,  # CHARGE_TARGET_MV (low byte)
    0x0523,  # CHARGE_TARGET_MV (high byte)
    0x030E,  # SBS_CHARGING_VOLTAGE (low byte)
    0x030F,  # SBS_CHARGING_VOLTAGE (high byte)
}


def read_sweep_summary_addresses():
    """Read the addresses present in the sweep summary CSV, skipping comment lines."""
    addresses = set()
    with open(SWEEP_SUMMARY_FILE, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            if line.startswith("addr"):
                continue
            if line.strip():
                parts = line.split(",")
                addr = int(parts[0], 16)
                addresses.add(addr)
    return addresses


class TestChargeLimitRegistersAbsent(unittest.TestCase):
    def test_charge_limit_registers_are_absent(self):
        """All six charge-limit registers must be absent from the sweep summary."""
        addresses = read_sweep_summary_addresses()
        absent = CHARGE_LIMIT_REGISTERS - addresses
        self.assertEqual(absent, CHARGE_LIMIT_REGISTERS,
            f"Expected all charge-limit registers to be absent from the sweep summary, "
            f"but found {CHARGE_LIMIT_REGISTERS - absent} present"
        )

    def test_sweep_summary_has_rows(self):
        """The sweep summary must have at least some rows to be meaningful."""
        addresses = read_sweep_summary_addresses()
        self.assertGreater(len(addresses), 0, "Sweep summary has no data rows")

    def test_header_mentions_charge_limit_registers(self):
        """The CSV header must explicitly mention that charge-limit registers are absent."""
        with open(SWEEP_SUMMARY_FILE, "r") as f:
            header = f.read(500)
        self.assertIn("charge-limit registers", header.lower(),
            "CSV header should mention charge-limit registers"
        )
        self.assertIn("0x07B9", header, "CSV header should list 0x07B9")
        self.assertIn("0x07D0", header, "CSV header should list 0x07D0")
