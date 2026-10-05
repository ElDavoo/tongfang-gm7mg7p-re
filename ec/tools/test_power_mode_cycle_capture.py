#!/usr/bin/env python3
"""What `2026-09-23-power-mode-cycle-0f00-0f5f.csv` records, held to its evidence.

Stands in for `docs/findings/power-mode-cycle-0f00-5f-what-the-capture-records.md`,
which reads the file `check_testdata_row_claims.py`'s dated block has named as
row 7's carrier on every run since #974 and which nothing in the corpus
described. That page's claims are about *this capture's contents*, so they are
asserted here against the committed files, and a capture or a table that moved
under the page turns the suite red rather than leaving the page quietly wrong.

**What is asserted, and what is not.** Each case below is a claim the write-up
makes about a named file -- the `0x30`-apart block pair, the duty values those
blocks take, the unused-slot set, the sawtooth -- not a count of the tree. There
is deliberately no assertion of how many rows the capture holds or how many
addresses it touches: `ec_watch` logs changes, so both figures move the moment
anyone captures another mode switch, and a suite that reddens on that gets
deleted rather than fixed. What is held instead is a *relation* per capture, the
shape `test_check_capture_names.py` gives for the same reason.

**The one thing asserted about the corpus as a whole** is that every address the
capture records is one where the published tables differ, and that no such
address is missing from it. That is not a census of the capture; it is the
property that makes the file usable as an oracle at all, and it is the claim
`fan_table_replay.py` depends on when it reconstructs each burst. It states
nothing about how many addresses there are, so a longer capture passes it.

**`ec_image()` is copied from `windows/tools/fan_table_replay.py`, not imported
from it.** The two are the same layout, and importing would have made a
`windows/tools/` change a red run here for a reason that has nothing to do with
this page. It is duplicated deliberately, and the one case that could tell the
two apart -- every burst's rows against the table that burst carried -- is
`test_each_bursts_rows_equal_the_table_that_burst_carried`, which is the claim
itself.

Offline throughout: committed files only -- the four under `evidence/` (the two
captures, the resting dump and the MQTT log) and the annotation CSVs under
`ec/annotations/`. No EC, no laptop, no Windows machine, and no register is read
or written here. Nothing in this suite is hardware evidence.
"""

import csv
import datetime
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
WATCH = os.path.join(REPO, "evidence", "ec-watch")
MQTT = os.path.join(REPO, "evidence", "mqtt-capture",
                    "2026-09-23-power-mode-cycle.jsonl")

WATCH_CAPTURE = "2026-09-23-power-mode-cycle-0f00-0f5f.csv"
SIBLING_CAPTURE = "2026-09-23-power-mode-cycle-0700-07ff.csv"
RESTING_DUMP = "2026-09-23-power-mode-cycle-0f00-final.txt"

# The CPU/GPU half stride. The window is two fans' worth of a 16-entry curve at
# three rows each, so the second fan starts `0x30` after the first -- which is
# the whole of the "two blocks 0x30 apart" observation.
HALF_STRIDE = 0x30
# The window's two duty rows, and the block inside each the capture follows.
CPU_DUTY = 0x0F20
GPU_DUTY = CPU_DUTY + HALF_STRIDE
# The eight duty entries the write-up follows: entries 8..15 of the row, the
# ones above the shortest table's max level and so the only ones that move.
DUTY_BLOCK_START = 8
DUTY_BLOCK_WIDTH = 8
DUTY_BLOCK = slice(DUTY_BLOCK_START, DUTY_BLOCK_START + DUTY_BLOCK_WIDTH)
# The mailbox the service writes `0xFD`/`0xC9` to, as ready tokens. Named so the
# cases that are *not* about it can say so; see
# `test_the_magic_values_are_not_the_mailbox_addresses`.
MAILBOX = (0x0F5D, 0x0F5E)
RAMP_BYTE = 0x070A
# A burst is a run of changes with no gap over this many seconds, the same rule
# `fan_table_replay.py`'s `--gap` applies by default. Named rather than passed
# so the boundary is one edit if the default ever moves.
BURST_GAP = 2.0

# The tables the service published on `Fan/Table` during the capture, in the
# order the capture passed through them: the pre-burst state, then one table per
# burst. `fan_table_replay.py` prints this order and matches all six against
# what the service announced, so a name here that the capture does not follow
# would fail `test_each_bursts_rows_equal_the_table_that_burst_carried` rather
# than pass quietly.
TABLES_IN_ORDER = ("M3T1", "M2T1", "M1T1", "M3T1", "M2T1", "M1T1", "M3T1")


def read_capture(name):
    """-> [(ts, addr, old, new)] for every data row, in file order.

    `old` is kept because it is the only record of a byte's value before the
    capture began, which is what makes a row a *change* row rather than a
    sample. Read with the encoding the format declares rather than the
    interpreter's default (`docs/findings/0751-capture-encoding.md`).
    """
    rows = []
    with open(os.path.join(WATCH, name), newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if not row.get("addr"):
                continue
            rows.append((datetime.datetime.fromisoformat(row["ts"]),
                         int(row["addr"], 16),
                         int(row["old"], 16),
                         int(row["new"], 16)))
    return rows


def read_dump(name):
    """-> {addr: byte} from a `ecrw.py dump` listing."""
    mem = {}
    with open(os.path.join(WATCH, name), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or ":" not in line:
                continue
            head, tail = line.split(":", 1)
            for offset, byte in enumerate(tail.split()):
                mem[int(head.strip(), 16) + offset] = int(byte, 16)
    return mem


def published_tables():
    """-> {Name: {addr: byte}} for every `Fan/Table` publish in the capture."""
    tables = {}
    with open(MQTT, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if '"Duty"' not in line:
                continue
            payload = json.loads(line)["payload"]
            tables[payload["Name"]] = payload
    return tables


def ec_image(payload):
    """The EC bytes `SetEcFanTable` writes for one published table.

    Copied from `windows/tools/fan_table_replay.py`'s `ec_image()`; see the
    module docstring for why it is copied rather than imported.
    """
    image = {}
    for side, base in (("CPU", 0x0F00), ("GPU", 0x0F30)):
        entries = payload[side]
        for i in range(16):
            image[base + i] = entries[i + 1]["UpT"] if i < 15 else 0xFF
            if i < 15:
                image[base + 0x11 + i] = entries[i]["DownT"]
            image[base + 0x20 + i] = (entries[i]["Duty"] * 2) & 0xFF
    return image


def bursts(rows, gap=BURST_GAP):
    """Split `rows` into bursts of changes with no gap over `gap` seconds."""
    out = [[rows[0]]]
    for prev, row in zip(rows, rows[1:]):
        if (row[0] - prev[0]).total_seconds() > gap:
            out.append([])
        out[-1].append(row)
    return out


def block(rows, base):
    """The rows of one eight-byte duty block, as (offset, old, new) from `base`."""
    return [(addr - base, old, new)
            for _, addr, old, new in rows if base <= addr < base + 8]


class CaptureShape(unittest.TestCase):
    """The `0x30` structure, and what the two blocks' values are.

    The write-up's central claim is that the block pair the issue found is one
    thing rather than two: CPU duty entries 8-15 and GPU duty entries 8-15.
    These cases hold that as a property of the committed files.
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = read_capture(WATCH_CAPTURE)
        cls.images = {name: ec_image(payload)
                      for name, payload in published_tables().items()}

    def test_the_two_duty_blocks_move_identically(self):
        """`0x0F28-0x0F2F` and `0x0F58-0x0F5F` are equal address-for-address.

        Stated relative to each block's own base, because the two bases differ
        by `0x30` and comparing raw addresses would compare `0x0F28` with
        `0x0F58` and call them different rows.
        """
        cpu = block(self.rows, CPU_DUTY + DUTY_BLOCK.start)
        gpu = block(self.rows, GPU_DUTY + DUTY_BLOCK.start)
        self.assertTrue(cpu, "the CPU duty block has no rows in the capture")
        self.assertEqual(cpu, gpu)

    def test_the_block_is_the_same_addresses_in_both_halves(self):
        """The `0x30` stride is the CPU/GPU split, so the offsets match too.

        Without this the equality above would also hold of two blocks that were
        the same bytes at different offsets, which is a different claim.
        """
        cpu = {addr for _, addr, _, _ in self.rows
               if CPU_DUTY + DUTY_BLOCK.start <= addr < CPU_DUTY + 16}
        gpu = {addr - HALF_STRIDE for _, addr, _, _ in self.rows
               if GPU_DUTY + DUTY_BLOCK.start <= addr < GPU_DUTY + 16}
        self.assertEqual(cpu, gpu)

    def test_every_value_the_block_takes_is_a_published_table_duty(self):
        """The block holds duty bytes and nothing else.

        `0x6E`, `0xAA` and `0xC8` are 110, 170 and 200, which is the vendor's
        `Duty * 2` storage for 55 %, 85 % and 100 % -- and those are the top
        duties of `M2T1`, `M1T1` and `M3T1`. This is the case that says the
        block is being *set to a table* rather than restored to a remembered
        value, which is what makes "the restore pass does not restore" a table
        change rather than a repair.

        Asserted per address rather than as a set of three values, so it holds
        whatever duty levels the published tables carry.
        """
        duty_bytes = {addr: {image[addr] for image in self.images.values()}
                      for addr in (CPU_DUTY + DUTY_BLOCK.start + i
                                   for i in range(DUTY_BLOCK_WIDTH))}
        for _, addr, _, new in self.rows:
            if addr not in duty_bytes:
                continue
            with self.subTest(addr="0x%04X" % addr, new="0x%02X" % new):
                self.assertIn(new, duty_bytes[addr],
                              "the block took a value no published table "
                              "gives that duty slot")

    def test_the_duty_rows_of_every_published_table_match_between_fans(self):
        """Why the dump's `0F20`/`0x50` pair is the one that matches.

        The write-up says the identical row-pair is a property of the service's
        tables rather than a coincidence of this capture. Held over every
        published table, so a future publish whose GPU duty row diverged from
        its CPU one would turn the claim red instead of leaving it stale.
        """
        for name, payload in sorted(published_tables().items()):
            with self.subTest(table=name):
                cpu = [e["Duty"] for e in payload["CPU"]]
                gpu = [e["Duty"] for e in payload["GPU"]]
                self.assertEqual(cpu, gpu)

    def test_the_upt_and_downt_rows_differ_between_fans(self):
        """The complementary half: the other two row-pairs do *not* match.

        A suite that only held the equality above would be satisfied by a
        capture where all three row-pairs matched, which is not what the dump
        shows.
        """
        for name, payload in sorted(published_tables().items()):
            with self.subTest(table=name):
                for field in ("UpT", "DownT"):
                    cpu = [e[field] for e in payload["CPU"]]
                    gpu = [e[field] for e in payload["GPU"]]
                    self.assertNotEqual(cpu, gpu,
                                        "%s's %s rows now agree between fans"
                                        % (name, field))


class RowsMatchTheirTable(unittest.TestCase):
    """Every row of every burst is the table that burst carried.

    This is the write-up's whole-content claim, and it is the property that
    makes the file an oracle rather than a sample: `ec_watch` logs changes, so a
    burst's rows are exactly the addresses on which the new table differs from
    the old one, and `fan_table_replay.py` relies on that to reconstruct each
    table from the log plus the final dump.
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = read_capture(WATCH_CAPTURE)
        cls.images = {name: ec_image(payload)
                      for name, payload in published_tables().items()}

    def test_every_address_the_capture_records_is_one_the_tables_disagree_on(self):
        """No row for an address that is constant across the three tables.

        The inverse of this -- an address where the tables differ but the
        capture is silent -- is
        `test_no_varying_address_is_missing_from_the_capture`.
        """
        varying = {addr for image in self.images.values() for addr in image
                   if len({i[addr] for i in self.images.values()}) > 1}
        recorded = {addr for _, addr, _, _ in self.rows}
        self.assertEqual(recorded - varying, set(),
                         "the capture holds rows for addresses no table "
                         "changes, so it is recording the window rather than "
                         "the event")

    def test_no_varying_address_is_missing_from_the_capture(self):
        """Every address the tables disagree on is one the capture recorded.

        The other half of the property above, and the half that makes the file
        usable: a change-row capture that dropped an address would let a table
        be reconstructed wrongly while still replaying cleanly.
        """
        varying = {addr for image in self.images.values() for addr in image
                   if len({i[addr] for i in self.images.values()}) > 1}
        recorded = {addr for _, addr, _, _ in self.rows}
        self.assertEqual(varying - recorded, set(),
                         "the capture is silent on addresses the tables "
                         "change, so a table cannot be reconstructed from it")

    def test_each_bursts_rows_equal_the_table_that_burst_carried(self):
        """Burst by burst, every row's new value is that burst's published table.

        The pre-burst state is `M3T1` -- which is the state
        `fan_table_replay.py` reconstructs by walking the dump backwards -- and
        the bursts then carry the remaining tables in `TABLES_IN_ORDER`. A row
        disagreeing means either the capture or the MQTT log is not what the
        write-up says it is.
        """
        found = bursts(self.rows)
        self.assertEqual(len(found), len(TABLES_IN_ORDER) - 1,
                         "the burst count no longer matches the number of "
                         "table writes the write-up describes")
        for target_name, segment in zip(TABLES_IN_ORDER[1:], found):
            target = self.images[target_name]
            for ts, addr, _, new in segment:
                if target[addr] != new:
                    self.fail("%s: %s wrote 0x%02X but %s gives 0x%02X"
                              % (target_name, ts.isoformat(), new,
                                 target_name, target[addr]))

    def test_the_resting_dump_is_the_table_in_force_at_the_end(self):
        """The dump equals the capture's final table byte for byte.

        The dump is the absolute anchor the replay walks backwards from, so
        this is what makes "before the first burst the state was `M3T1`" a
        reading rather than an assumption.
        """
        dump = read_dump(RESTING_DUMP)
        final = self.images[TABLES_IN_ORDER[-1]]
        differing = {addr for addr in final if dump.get(addr) != final[addr]}
        self.assertEqual(differing, set(),
                         "the resting dump is not the capture's final table")


class UnusedSlots(unittest.TestCase):
    """`0xFF` is a table's marker for a slot at or past its max level.

    The issue asked what the `0xFF` transients mean and recorded that nothing
    in the corpus said. They are the vendor's unused-step marker, and each one
    the capture writes is an address that is real in a longer published table
    and `0xFF` in a shorter one.
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = read_capture(WATCH_CAPTURE)
        cls.images = {name: ec_image(payload)
                      for name, payload in published_tables().items()}

    def test_each_ff_address_is_used_by_one_table_and_unused_by_another(self):
        """Every `0xFF` row is an address whose value differs across tables.

        Asserted as the relation rather than as a set of eight addresses, so a
        capture that recorded a ninth such address would pass rather than need
        an edit here.
        """
        written = {addr for _, addr, old, new in self.rows
                   if 0xFF in (old, new)}
        self.assertTrue(written, "the capture holds no 0xFF row at all")
        for addr in sorted(written):
            with self.subTest(addr="0x%04X" % addr):
                used = {name for name, image in self.images.items()
                        if image[addr] != 0xFF}
                unused = set(self.images) - used
                self.assertTrue(used and unused,
                                "0x%04X is 0xFF in every published table, so "
                                "no table write can have produced the row"
                                % addr)

    def test_ff_is_written_only_over_a_real_value_and_read_back(self):
        """Each `0xFF` row is a real value overwritten, not a slot left alone.

        `ec_watch` logs changes only, so a row into `0xFF` whose `old` is
        already `0xFF` would be a second write of the same value -- which the
        format does not produce, and which would mean the row is not a change.
        """
        for ts, addr, old, new in self.rows:
            if 0xFF not in (old, new):
                continue
            with self.subTest(ts=ts.isoformat(), addr="0x%04X" % addr):
                self.assertNotEqual(old, new)
                self.assertIn(0xFF, (old, new))

    def test_the_dump_ff_runs_are_the_tails_of_the_upt_and_downt_rows(self):
        """Each `0xFF` run in the dump ends one of the window's temp rows.

        The layout puts `UpT`, `DownT` and `Duty` in each half, so an unused
        tail is contiguous and runs to the end of its row. A run that stopped
        short of a row's end, or that sat inside the `Duty` row, would be
        something this page has not accounted for.
        """
        dump = read_dump(RESTING_DUMP)
        # Each row's last byte, by the layout `ec_image()` builds.
        row_ends = {0x0F0F, 0x0F1F, CPU_DUTY + 0x0F,
                    0x0F3F, 0x0F4F, GPU_DUTY + 0x0F}
        duty_rows = {CPU_DUTY, GPU_DUTY}
        seen = []
        run_start = None
        for addr in range(0x0F00, 0x0F60):
            blank = dump.get(addr) == 0xFF
            if blank and run_start is None:
                run_start = addr
            if not blank and run_start is not None:
                seen.append((run_start, addr - 1))
                run_start = None
        self.assertTrue(seen, "the dump holds no 0xFF run at all")
        for start, end in seen:
            with self.subTest(run="0x%04X-0x%04X" % (start, end)):
                self.assertIn(end, row_ends,
                              "the 0xFF run ending at 0x%04X does not end a "
                              "row of the window" % end)
                self.assertNotIn(start, duty_rows,
                                 "the 0xFF run at 0x%04X starts in a duty "
                                 "row, which the write-up says is fully used "
                                 "in every published table" % start)

    def test_the_tables_say_how_many_slots_they_use(self):
        """Both temp rows fill no slot past the table's declared max level.

        The write-up says the unused slots track `CpuTemp_DefaultMaxLevel` /
        `GpuTemp_DefaultMaxLevel`. Held as the relation between the declared
        level and the filled slots -- never as a count of either, which a future
        table would move -- and over both rows, because the two cut at
        different entries and the write-up says so.
        """
        for name, payload in sorted(published_tables().items()):
            for side, level_key in (("CPU", "CpuTemp_DefaultMaxLevel"),
                                    ("GPU", "GpuTemp_DefaultMaxLevel")):
                level = payload[level_key]
                for field in ("UpT", "DownT"):
                    used = [i for i, e in enumerate(payload[side])
                            if e[field] != 0xFF]
                    with self.subTest(table=name, fan=side, row=field):
                        self.assertTrue(used, "%s %s %s fills no slot at all"
                                        % (name, side, field))
                        self.assertLessEqual(
                            max(used), level,
                            "%s %s %s fills slot %d but declares max level %d"
                            % (name, side, field, max(used), level))

    def test_the_downt_row_cuts_earlier_than_the_upt_row(self):
        """The two rows' `0xFF` boundaries differ, which is why the write-up
        does not give one entry number.

        `UpT` is indexed by the entry it gates and `DownT` by the entry it
        leaves, so a table's last `DownT` is written at the entry *before* its
        last `UpT`. Held as an ordering rather than as an exact offset, so a
        future table that agreed between the rows would need the write-up
        revisited rather than this case quietly failing on a magic number.
        """
        for name, payload in sorted(published_tables().items()):
            for side in ("CPU", "GPU"):
                first_blank = {}
                for field in ("UpT", "DownT"):
                    first_blank[field] = next(
                        i for i, e in enumerate(payload[side])
                        if e[field] == 0xFF)
                with self.subTest(table=name, fan=side):
                    self.assertLess(first_blank["DownT"],
                                    first_blank["UpT"],
                                    "%s %s now cuts both rows at the same "
                                    "entry" % (name, side))


class TheRampByte(unittest.TestCase):
    """`0x070A` is a counter, not a poked byte.

    The issue's other half. The dated rule resolves row 7's literals in the
    carrier, and the `0xFD`/`0xC9` occurrences row 7's sentence is about are in
    the sibling -- which is the whole reason the two captures are read together.
    In that sibling, `0x070A` climbs monotonically modulo 256 and wraps, so
    `0xC9` and `0xFD` are points it passes through rather than values it holds,
    the opposite of the mailbox reading the issue proposed.
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = [row for row in read_capture(SIBLING_CAPTURE)
                    if row[1] == RAMP_BYTE]

    def steps(self):
        """The byte-to-byte deltas, modulo 256, in capture order.

        Taken from each row's `old`/`new` rather than from consecutive `new`
        values, because a capture is a change log: a byte written between two of
        its logged rows would otherwise show up as one large step instead of the
        two the EC actually made.
        """
        return [(new - old) % 0x100 for _, _, old, new in self.rows]

    def test_the_ramp_byte_only_ever_steps_forward_by_a_small_amount(self):
        """Every step is `+1`, `+2` or `+3` -- the steady ramp, in both directions
        of the byte's range.

        Modulo 256, so this is the claim that holds *across* the wraps too: a
        byte that jumped to an unrelated value would show a step outside the
        set. Asserted as a set rather than as a count of each step size, so a
        capture that caught more or fewer `+1` and `+3` passes.
        """
        self.assertTrue(self.rows, "the capture holds no row for 0x070A")
        outside = sorted({s for s in self.steps() if s not in (1, 2, 3)})
        self.assertEqual(outside, [],
                         "0x070A takes a step outside {+1, +2, +3}, so it is "
                         "not the steady ramp the write-up describes")

    def test_the_ramp_byte_wraps_at_least_once(self):
        """The sawtooth claim needs a wrap to be a sawtooth rather than a ramp.

        Without this the case above would be satisfied by a byte climbing
        steadily out of the top of its range and never coming back, which is a
        different claim -- and the one row 7's `0xC9` is about sits near the top.

        A wrap is a step that lands lower than it started. Modulo 256 that is
        still a forward step, so it is found by comparing `new` against `old`
        directly rather than by looking for a large delta.
        """
        wraps = [ts for ts, _, old, new in self.rows if new < old]
        self.assertTrue(wraps,
                        "0x070A never wraps in this capture, so nothing here "
                        "distinguishes a sawtooth from a one-way ramp")

    def test_the_ramp_byte_holds_no_value_it_returns_to(self):
        """The `0xC9` and `0xFD` occurrences are pass-throughs, not settings.

        Each occurrence is a row whose `old` or `new` is the value, and the
        value is left again on the next row for that address. A byte that
        settled on `0xC9` would have it as `new` twice with nothing between.
        """
        held = [value for value in (0xC9, 0xFD)
                if any(value in (old, new) for _, _, old, new in self.rows)]
        self.assertTrue(held, "the capture never shows either value")
        for value in held:
            leaves = [i for i, (_, _, old, new) in enumerate(self.rows)
                      if value in (old, new)
                      and i + 1 < len(self.rows)]
            for i in leaves:
                with self.subTest(value="0x%02X" % value, row=i):
                    self.assertNotEqual(self.rows[i + 1][3], value,
                                        "0x%02X is still 0x%02X on the next "
                                        "row, so the byte held it"
                                        % (value, value))

    def test_the_carrier_capture_holds_neither_value(self):
        """Row 7's "the `0xFD`/`0xC9` magic never appears" is true of the carrier.

        This is the sentence `check_testdata_row_claims.py` checks, and the
        reason the carrier it names makes the sentence true is worth holding:
        the carrier is the `0x0F00` window, and the byte that takes those values
        is in the sibling capture.
        """
        carrier = read_capture(WATCH_CAPTURE)
        for value in (0xFD, 0xC9):
            with self.subTest(value="0x%02X" % value):
                self.assertEqual(
                    [row for row in carrier if value in (row[2], row[3])], [])

    def test_the_magic_values_are_not_the_mailbox_addresses(self):
        """No row the carrier holds for the mailbox carries a ready token.

        The issue's proposed reading was a host poke at the ready-token
        mailbox, `0x0F5D`/`0x0F5E`. Those addresses are a different one from
        the ramping `0x070A`, and they are in the *carrier* rather than the
        sibling, so this reads the rows that are there: both addresses have
        rows, and not one of them carries `0xFD` or `0xC9`.

        **Not asserted: that the mailbox went unpoked.** `ec_watch` logs a byte
        only where it differs from the previous sweep, so a poke whose token
        window fell between two sweeps would leave no row at all and this case
        could not see one -- the sweep period here is about 0.21 s, while
        `ec-fan-table-defaults.md` §4 has the host polling `IsReadyToRead` every
        500 ms until the EC overwrites both. What is held is the narrow claim
        the write-up makes, and the half that does not need a poke ruled out:
        `ec-fan-table-defaults.md` §4's reading that these bytes are duty slots
        the GPU copy overwrites, which the rows here are consistent with.
        """
        self.assertNotIn(RAMP_BYTE, MAILBOX)
        carrier = read_capture(WATCH_CAPTURE)
        for addr in MAILBOX:
            rows = [row for row in carrier if row[1] == addr]
            with self.subTest(addr="0x%04X" % addr):
                self.assertTrue(rows,
                                "the carrier holds no row for 0x%04X, so it "
                                "says nothing about the mailbox" % addr)
                for _, _, _, new in rows:
                    self.assertNotIn(new, (0xFD, 0xC9),
                                     "the mailbox at 0x%04X took a ready-token "
                                     "value in this capture" % addr)


class StaticWriter(unittest.TestCase):
    """The EC-side routines the annotations name as touching `0x070A`.

    `0x070A` reaching `0xC9` in the capture is explained by the byte being
    ramped; this is the committed annotation half of that explanation. Read
    from the CSVs rather than asserted about the decompiled C, so it is a
    statement about what the annotations record.
    """

    ANNOTATIONS = os.path.join(REPO, "ec", "annotations")

    def _rows(self, name):
        with open(os.path.join(self.ANNOTATIONS, name), newline="",
                  encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def _rows_naming_the_ramp_byte(self):
        """The arms-CSV rows whose `xdata` column names `0x070A`.

        Matched on the address alone rather than on `0x070A r+w`, because the
        access mode is the *other* case's claim -- matching the whole phrase
        here would make that case unable to fail.
        """
        return [row for row in self._rows("manual-fan-ctrl-0751-arms.csv")
                if "0x070A" in (row.get("xdata") or "")]

    def test_the_ramp_byte_is_a_callee_xdata_not_an_arm_one(self):
        """`0x070A` appears only in `kind=callee` rows of the arms CSV.

        An `arm` row is the branch structure of the `0x0751` handler itself; a
        `callee` row is what a routine it calls touches. The distinction is the
        claim: the byte belongs to a routine the handler reaches, not to the
        handler's own dispatch.
        """
        rows = self._rows_naming_the_ramp_byte()
        self.assertTrue(rows, "the arms CSV records no row touching 0x070A")
        self.assertEqual([row["kind"] for row in rows],
                         ["callee"] * len(rows))

    def test_the_ramp_byte_is_read_write_in_every_row_that_names_it(self):
        """Every one of those rows records `0x070A` as `r+w`, never read-only.

        A read-only entry would make the byte a counter this page read rather
        than one a routine advances, which is a different claim.
        """
        for row in self._rows_naming_the_ramp_byte():
            modes = [part.strip() for part in row["xdata"].split(";")]
            with self.subTest(callee=row.get("callee")):
                self.assertIn("0x070A r+w", modes)

    def test_the_annotation_csv_names_an_ec_side_ramp_that_increments_it(self):
        """`ghidra-functions.csv` describes routines that increment `0x070A`.

        Named by function rather than by address so the case survives a
        re-export, per CLAUDE.md's rule about citing code by name.
        """
        rows = self._rows("ghidra-functions.csv")
        ramping = [row for row in rows
                   if "0x070A" in row.get("comment", "")
                   and "increment" in row["comment"].lower()]
        self.assertTrue(ramping,
                        "no annotated function is described as incrementing "
                        "0x070A, so the capture's ramp has no static writer")
        for row in ramping:
            with self.subTest(function=row["name"]):
                self.assertTrue(row["evidence"],
                                "%s names no evidence file" % row["name"])


if __name__ == "__main__":
    unittest.main()