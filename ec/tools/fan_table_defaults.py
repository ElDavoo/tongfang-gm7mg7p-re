#!/usr/bin/env python3
"""The EC's own per-mode default fan tables, decoded out of CODE, against the
tables the vendor service applies (issue #100).

`RefreshDefaultFanTable` (`windows/decompiled/v3.1.39.0/GCUService/
MyControlCenter.MyFan.FanTable/FanTable_Manager1p5.cs:827`) asks the EC for
its own default curve per mode over the `0x0F5D-0x0F5F` mailbox. Only the
host half of that had been read, and `windows/vendor-ec-map.md` "Fan tables"
closed the issue's predecessor with the comparison explicitly open: *"The
stored defaults ... are presumably its output, but nobody has compared them
against what the EC returns today."*

This is that comparison. The EC's handler is bank0 `0x888D`
(`fan_table_mailbox_handler`), decoded in
`../annotations/manual-fan-ctrl-0751.md` §6. It takes a CODE pointer base the
EC seeds at `0x8653`, adds one of four offsets to it, and copies two 48-byte
CODE blobs to `0x0F00` and `0x0F30`. All four offsets resolve to pairs, so
**all eight tables are in the common area and every byte is readable straight
out of the dump** -- `trace_xdata_refs.offset_for_runtime()` is what turns a
CODE address into a file offset here, and the write-up is
`../../docs/findings/ec-fan-table-defaults.md`.

The layout is not restated. `windows/tools/fan_table_replay.py` already
documents it in `ec_image()`, which is the vendor's *writer*; this decodes
into the same field names and `--self-test` re-encodes through `ec_image()`
to hold the two halves to each other, so a decode that drifted from the
writer would fail rather than agree with a second copy of the layout.

**What the comparison is against, exactly.** The `DefaultFanTable_*.json`
files the issue names live in `UserFanTables\\` on the machine and are not in
this repository. What is committed is the `Fan/Table` MQTT capture, one
publish per mode switch: `M1T1` (Gaming), `M2T1` (Office), `M3T1` (Turbo).
`fan_table_replay.py` already proved those publishes equal the bytes the
service wrote into `0x0F00-0x0F5F`, byte for byte, across all seven table
states of the 2026-09-23 capture. So this compares against the tables the
service actually applies, which is a different claim from a comparison
against the stored-default files and is labelled as one everywhere below.

**Everything here is read out of the committed image.** No register was
written, no register was read back, and no laptop, EC or Windows machine is
involved. These are the bytes the handler would copy, on the code that copies
them -- not a table observed running. Per `CLAUDE.md` that is a weaker claim
than a behavioural test, and `../../docs/hardware-tests/fan-table-defaults-0f5d.md`
is the unrun procedure that would settle it.

Usage:
    python3 fan_table_defaults.py                       # decode + comparison
    python3 fan_table_defaults.py --csv                 # the decode, as CSV
    python3 fan_table_defaults.py --check               # hold the committed CSV
    python3 fan_table_defaults.py --self-test           # the refusals + oracle
    python3 fan_table_defaults.py <firmware> --check
"""
import argparse
import csv
import difflib
import io
import os
import sys
import tempfile

import trace_xdata_refs

# `fan_table_replay` is the vendor's own writer and the committed MQTT reader,
# and it imports nothing but stdlib -- so importing it costs an offline tool
# nothing. `grade_gpu_door.py` imports across this boundary the same way, and
# takes its watch table by reference from `windows/tools/gpu_block_watch.py`,
# which is now importable off Windows for the same reason. The one copy of the
# layout is the point; a second would be the
# drift that tool's own test guards against.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.pardir, os.pardir, "windows", "tools"))
import fan_table_replay  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
DEFAULT_FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")
DEFAULT_CSV = os.path.join(EC, "annotations", "fan-table-defaults.csv")
DEFAULT_MQTT = os.path.join(REPO, "evidence", "mqtt-capture",
                            "2026-09-23-power-mode-cycle.jsonl")

# The routine the whole tool is about, named once rather than spelled into the
# report and the CSV header.
HANDLER = 0x888D

# The seeding routine, called at `0xA828` inside the `0xA7C8` block
# (`manual-fan-ctrl-0751.md` §4). `mov r6,#hi / mov r7,#lo / mov dptr,#cell`
# then two stores: R6 lands in `cell` and R7 in `cell+1`, big-endian, which is
# the pointer the handler offsets. Read out of the image rather than asserted,
# so a firmware whose base moved would decode its own tables.
SEED = 0x8653
SEED_OPCODES = (0x7E, 0x7F, 0x90)
SEED_CELL = 0x08E6

# One 48-byte half of the window. `0x888D` copies `0x30` bytes to `0x0F00` and
# `0x30` to `0x0F30`, so the second copy covers `0x0F30..0x0F5F` inclusive --
# which is what makes the mailbox bytes `0x0F5D-0x0F5F` the last three bytes of
# the GPU blob rather than three bytes beside it.
TABLE_BYTES = 0x30

# The window the handler fills, and the two halves' bases inside it.
WINDOW = (0x0F00, 0x0F5F)
CPU_BASE, GPU_BASE = 0x0F00, 0x0F30

# Offsets within a half, in the vendor's layout. `ec_image()` above writes
# them and `GetEcFanTable` (`FanTable_Manager1p5.cs:499`) reads them back; this
# is that reader's arithmetic rather than a re-derivation of it:
#
#   0x00 + i   entry[i+1].UpT     i = 0..14. 0x0F holds the 0xFF the writer puts
#                                  in the last slot and the reader re-reads as
#                                  entry[15].DownT; entry[0].UpT is hardcoded 0
#   0x10       written by neither SetEcFanTable nor GetEcFanTable
#   0x11 + i   entry[i].DownT     i = 0..14
#   0x20 + i   entry[i].Duty * 2  i = 0..15, so 0xC8 is 100 %
UPT, DOWNT, DUTY = 0x00, 0x11, 0x20

# The one offset in a half that neither `SetEcFanTable` writes nor
# `GetEcFanTable` reads, and `decode_blob()` therefore never looks at.
GAP = 0x10

# The mailbox, as three offsets into the GPU half.
MAILBOX = (0x0F5D, 0x0F5E, 0x0F5F)
MAGIC = (0xFD, 0xC9)

# The four slots, in the order `0x888D` reaches them. `selector` is the value
# the host writes to `0x0F5F`; `offset` is what the handler adds to the low
# byte of the base (`0xBC4F` adds nothing, `0xBCCB` adds the byte the branch
# computed); `oem` is `0x0782` bit 2, which is the *only* thing that separates
# the two Office slots.
#
# The mode names are the service's, from `SetFanMode`'s `0x0751` values
# (`0x00` Gaming, `0xA0` Office, `0x10` Turbo) -- not the mailbox's, which
# numbers them 1/2/3 the other way round. Two numberings, and the tuple below
# is the join, which is the thing a reader of either source needs.
#
# `RefreshDefaultFanTableAll` (`FanTable_Manager1p5.cs:790`) asks for Gaming,
# then Office, then Turbo: three handshakes, and selector 3 is asked for once.
# The two Office rows are that one request with `0x0782` bit 2 in two states,
# which is the whole of what the bit is on this path.
SLOTS = (
    ("gaming", 2, 0x00, "-", "0xBC4F"),
    ("office", 3, 0x04, "0", "0xBCCB"),
    ("office", 3, 0x08, "1", "0xBCCB"),
    ("turbo", 1, 0x0C, "-", "0xBCCB"),
)

# The service publishes one of these per mode (`windows/vendor-ec-map.md`,
# "What `SetUserProfile` writes"). Only the names are transcribed; the values
# are read out of the committed capture.
PUBLISHED_FOR = {"gaming": "M1T1", "office": "M2T1", "turbo": "M3T1"}

# The `--csv` header. A list so a column cannot reach the output without
# appearing here, which is what `data_regions.py` does for the same reason.
CSV_COLUMNS = ("mode", "selector", "oem_bit_2", "fan", "code_addr",
               "upt", "downt", "duty")


class NotDecodable(Exception):
    """A byte range this tool will not guess at. Every raise site is a refusal
    the `--self-test` exercises, because a decode that guesses is a table in a
    write-up that no image holds."""


# --- reading the image -----------------------------------------------------

def read_code(image: bytes, runtime: int, length: int = 1) -> bytes:
    """`length` CODE bytes at runtime address `runtime`, seen from bank0.

    `offset_for_runtime()` rather than a bare index: the four tables are all
    below 0x8000, so their file offset equals their runtime address, and going
    through the same function the rest of `ec/tools` uses is what keeps a
    future one above 0x8000 from being read at the wrong offset silently.
    """
    off = trace_xdata_refs.offset_for_runtime(runtime, "bank0")
    if off is None:
        raise NotDecodable(
            f"0x{runtime:04X} is not reachable as CODE from bank0, so its file "
            f"offset is unknown -- see trace_xdata_refs.offset_for_runtime()")
    if off + length > len(image):
        raise NotDecodable(
            f"0x{runtime:04X}+{length} runs past the end of the image")
    return image[off:off + length]


def pointer_base(image: bytes) -> int:
    """The CODE pointer base `0x8653` seeds into `0x08E6`/`0x08E7`.

    Read out of the image, not asserted. Six bytes are checked -- the two
    `mov Rn,#imm8` opcodes, the `mov dptr,#cell` opcode and the cell itself --
    because a base read from the wrong instruction is a table list that is
    wrong in a way nothing downstream can see.
    """
    raw = read_code(image, SEED, 8)
    if (raw[0], raw[2], raw[4]) != SEED_OPCODES:
        raise NotDecodable(
            f"0x{SEED:04X} is {raw.hex(' ')}, not the mov r6 / mov r7 / "
            f"mov dptr sequence that seeds the fan-table pointer base")
    cell = (raw[5] << 8) | raw[6]
    if cell != SEED_CELL:
        raise NotDecodable(
            f"0x{SEED:04X} seeds the base into 0x{cell:04X}, not the "
            f"0x{SEED_CELL:04X} the handler reads")
    return (raw[1] << 8) | raw[3]


def pointer_pair(image: bytes, slot_addr: int):
    """One slot's two big-endian CODE pointers, or refuse the whole thing.

    A pointer at or above 0x8000 is a bank window, and which bank is mapped is
    not in the byte -- so a table above the common area is *not* readable out of
    this dump and is refused rather than read at its own runtime address. The
    four this tool finds are all below it, which is what makes this a byte dump
    rather than a disassembly.
    """
    raw = read_code(image, slot_addr, 4)
    cpu, gpu = (raw[0] << 8) | raw[1], (raw[2] << 8) | raw[3]
    for addr in (cpu, gpu):
        if addr >= 0x8000:
            raise NotDecodable(
                f"slot 0x{slot_addr:04X} points at 0x{addr:04X}, at or above "
                f"the 0x8000 bank window: the bank is not in the dump, so "
                f"these bytes are not readable here")
    return cpu, gpu


def slot_address(base: int, offset: int) -> int:
    """`base` with `offset` added to its low byte, as the handler's `add a,#n`.

    The handler adds to the byte at `0x08E7` and leaves `0x08E6` alone, so an
    offset that carried out of the low byte would wrap into a different pair
    rather than the next one -- which is why this refuses instead of computing
    `base + offset`.
    """
    if (base & 0xFF) + offset > 0xFF:
        raise NotDecodable(
            f"base 0x{base:04X} + 0x{offset:02X} carries out of the low byte, "
            f"which the handler's `add a,#n` would wrap rather than carry")
    return (base & 0xFF00) | ((base & 0xFF) + offset)


def decode_blob(blob: bytes):
    """One 48-byte CODE blob as the vendor's `FanTable1p5` CPU/GPU fields.

    The inverse of `fan_table_replay.ec_image()`, in that file's field names.
    """
    if len(blob) != TABLE_BYTES:
        raise NotDecodable(
            f"a table half is {len(blob)} bytes, not {TABLE_BYTES}")
    duty = []
    for i in range(16):
        raw = blob[DUTY + i]
        if raw & 1:
            # `GetEcFanTable` stores `Data / 2` on a byte, which truncates, so
            # an odd byte is one the vendor's own writer cannot have produced.
            # Refused rather than rounded: the difference is half a percent of
            # fan speed and the decode is not entitled to invent which way.
            raise NotDecodable(
                f"duty slot {i} is 0x{raw:02X}, which /2 truncates")
        duty.append(raw >> 1)
    return {
        "UpT": [0] + [blob[UPT + i] for i in range(15)],
        "DownT": [blob[DOWNT + i] for i in range(15)] + [blob[UPT + 15]],
        "Duty": duty,
    }


def tables(image: bytes):
    """-> (base, [row, ...]), one row per slot, in `SLOTS` order.

    Each row is a dict: the slot's identity, its resolved `slot` address, its
    two CODE addresses, and the two decoded halves.
    """
    base = pointer_base(image)
    rows = []
    for mode, selector, offset, oem, helper in SLOTS:
        slot = slot_address(base, offset)
        cpu, gpu = pointer_pair(image, slot)
        rows.append({
            "mode": mode, "selector": selector, "oem_bit_2": oem,
            "helper": helper, "slot": slot, "cpu": cpu, "gpu": gpu,
            "blob": {"CPU": read_code(image, cpu, TABLE_BYTES),
                     "GPU": read_code(image, gpu, TABLE_BYTES)},
            "table": {fan: decode_blob(read_code(image, addr, TABLE_BYTES))
                      for fan, addr in (("CPU", cpu), ("GPU", gpu))},
        })
    return base, rows


# --- comparing against the service ----------------------------------------

def used(entry) -> list:
    """The levels a table actually uses: up to the first 0xFF step.

    `UpT` is the row that terminates, because the service writes 0xFF into
    every unused step threshold and repeats the last duty below it. Level 0
    comes out with the rest on both sides: `GetEcFanTable` hardcodes
    `entry[0].UpT = 0` and every published table carries `0` there, so it is
    shown rather than dropped.
    """
    out = []
    for i, v in enumerate(entry["UpT"]):
        if v == 0xFF:
            break
        out.append(i)
    return out


def steps(field: str, values) -> str:
    """The distinct consecutive differences in one ramp, ascending.

    Printed because "a uniform 3-4 °C ladder" and "hand-set per level" are
    claims about a *shape*, and this is the shape read off both sides rather
    than a reader's impression of two rows of numbers.

    Cut at the first 0xFF, which is how a row says it has run out, and -- for
    `UpT` only -- at level 0, whose `0` is the constant both `GetEcFanTable`
    and every published table carry rather than a threshold. Leaving either in
    would put a step of 54 or 48 next to real ones.
    """
    vals = list(values)
    if 0xFF in vals:
        vals = vals[:vals.index(0xFF)]
    if field == "UpT":
        vals = vals[1:]
    deltas = sorted({b - a for a, b in zip(vals, vals[1:])})
    return "{" + ", ".join(str(d) for d in deltas) + "}" if deltas else "{}"


def as_fan1p5(decoded) -> list:
    """One decoded half in the vendor's `FanTable1p5` list-of-entries shape.

    `decode_blob()` returns three parallel rows because that is the shape the
    bytes are in; `ec_image()` takes entries because that is the shape the
    vendor's own object is in. The round-trip in `--self-test` goes through
    here, so the two are held to each other rather than to a third copy.
    """
    return [{"UpT": u, "DownT": d, "Duty": y} for u, d, y
            in zip(decoded["UpT"], decoded["DownT"], decoded["Duty"])]


def compare(rows, mqtt_path: str):
    """EC decode against the committed `Fan/Table` publishes.

    -> ({(mode, oem): {fan: {field: (ec_values, svc_values)}}}, notes).
    `notes` names what a per-slot table cannot: a mode with no publish in the
    capture. Keyed per slot, so both Office slots are named and the reader can
    see the publish is missing for the mode rather than for one bit of it.
    """
    published = {p["Name"]: p
                 for _, p in fan_table_replay.load_published(mqtt_path)}
    out, notes = {}, []
    for row in rows:
        name = PUBLISHED_FOR.get(row["mode"])
        svc = published.get(name)
        if svc is None:
            notes.append(f"{row['mode']} (0x0782 bit 2 = {row['oem_bit_2']}): "
                         f"no {name} publish in {os.path.basename(mqtt_path)}")
            continue
        per_fan = {}
        for fan in ("CPU", "GPU"):
            levels = used(row["table"][fan])
            per_fan[fan] = {
                field: ([row["table"][fan][field][i] for i in levels],
                        [svc[fan][i][field] for i in levels])
                for field in ("UpT", "DownT", "Duty")}
        out[(row["mode"], row["oem_bit_2"])] = per_fan
    return out, notes


def writeback(row):
    """The bytes the GPU copy leaves in the mailbox, keyed by address.

    The second copy is `0x30` bytes to `0x0F30`, so it covers `0x0F5D`,
    `0x0F5E` and `0x0F5F` -- the GPU blob's own offsets `0x2D`, `0x2E`, `0x2F`.
    That is the whole of what "the EC has overwritten both" means
    (`IsReadyToRead`, `FanTable_Manager1p5.cs:814`), and it is a side effect of
    the copy rather than a store to those three addresses: `scan_refs.py` finds
    one direct `mov dptr,#0x0F5D` site, **zero** for `0x0F5E` and two for
    `0x0F5F`, and the handler reaches all three by `inc dptr` from `0x0F5D`
    (`../decompiled/bank0/888D.asm:8898`). A zero is "not found by this
    method", never absent.
    """
    return {addr: row["blob"]["GPU"][addr - GPU_BASE] for addr in MAILBOX}


# --- output ----------------------------------------------------------------

def fmt(values) -> str:
    return " ".join(f"{v:3d}" for v in values)


def report(image: bytes, mqtt_path: str, stream=sys.stdout) -> None:
    base, rows = tables(image)
    print(f"EC fan-table pointer base 0x{base:04X}, seeded at bank0 "
          f"0x{SEED:04X}; handler 0x{HANDLER:04X} adds one of four offsets to "
          f"its low byte", file=stream)
    print("  slot   0x0F5F  0x0782 b2  helper   CPU      GPU", file=stream)
    for row in rows:
        print(f"  0x{row['slot']:04X}   {row['selector']}         "
              f"{row['oem_bit_2']:>2}        {row['helper']}  "
              f"0x{row['cpu']:04X}  0x{row['gpu']:04X}", file=stream)

    cmp_, notes = compare(rows, mqtt_path)
    print("\nBoth sides indexed by the EC's used levels, so a trailing 255 on "
          "the\nservice row is where the service's table stops earlier.\n",
          file=stream)
    for mode in ("gaming", "office", "turbo"):
        mine = [r for r in rows if r["mode"] == mode]
        row = mine[0]
        key = (mode, row["oem_bit_2"])
        if key not in cmp_:
            continue
        print(f"{mode}  (0x0F5F = {row['selector']}, service table "
              f"{PUBLISHED_FOR[mode]})", file=stream)
        for other in mine[1:]:
            same = all(row["blob"][f] == other["blob"][f] for f in ("CPU", "GPU"))
            print(f"  0x0782 bit 2 = {other['oem_bit_2']}: "
                  f"{'byte-identical to' if same else 'DIFFERS from'} the "
                  f"bit-2 = {row['oem_bit_2']} table", file=stream)
        for fan in ("CPU", "GPU"):
            for field in ("UpT", "DownT", "Duty"):
                ec, svc = cmp_[key][fan][field]
                print(f"  {fan}  {field:5s}  EC       {fmt(ec)}"
                      f"   steps {steps(field, ec)}", file=stream)
                print(f"  {fan}  {field:5s}  service  {fmt(svc)}"
                      f"   steps {steps(field, svc)}", file=stream)
            ec, svc = cmp_[key][fan]["Duty"]
            print(f"  {fan}  max duty: EC {max(ec)} %, service {max(svc)} %"
                  f"  -- {'same' if max(ec) == max(svc) else 'DIFFERENT'}",
                  file=stream)
        print("  mailbox after the copy: "
              + "  ".join(f"0x{a:04X}={b:02X}" for a, b in
                          sorted(writeback(row).items())), file=stream)
        print("", file=stream)
    for note in notes:
        print(f"note  {note}", file=stream)


def csv_rows(image: bytes):
    _, rows = tables(image)
    out = []
    for row in rows:
        for fan in ("CPU", "GPU"):
            table = row["table"][fan]
            out.append({
                "mode": row["mode"], "selector": row["selector"],
                "oem_bit_2": row["oem_bit_2"], "fan": fan,
                "code_addr": f"0x{row[fan.lower()]:04X}",
                "upt": " ".join(str(v) for v in table["UpT"]),
                "downt": " ".join(str(v) for v in table["DownT"]),
                "duty": " ".join(str(v) for v in table["Duty"]),
            })
    return out


def render_csv(image: bytes) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(csv_rows(image))
    return buf.getvalue()


# --- checks ----------------------------------------------------------------

def check(image: bytes, path: str, stream=sys.stdout) -> int:
    """Regenerate the decode in memory and diff it against the committed CSV.

    There is no `--out-` and no code path in this file that opens a file for
    writing, so a `--check` here cannot decide what the file says -- the
    property `bios/tools/test_ifr_census.py` pins for its own pair.
    """
    want = render_csv(image)
    try:
        with open(path, encoding="utf-8") as fh:
            have = fh.read()
    except FileNotFoundError:
        print(f"  {path} does not exist, and a --check that wrote the file it "
              f"is checking would decide what the file says", file=sys.stderr)
        return 1
    if have == want:
        print(f"  {os.path.basename(path)}: {len(csv_rows(image))} row(s) "
              f"re-derived from the image", file=stream)
        return 0
    for line in difflib.unified_diff(
            have.splitlines(True), want.splitlines(True),
            fromfile=path, tofile="regenerated from the image"):
        sys.stderr.write(line)
    print(f"  {path} does not match the image", file=sys.stderr)
    return 1


# The oracle for --self-test, transcribed by hand from
# ../annotations/manual-fan-ctrl-0751.md §6 and
# ../../docs/findings/ec-fan-table-defaults.md -- NOT from this file's own
# output. A self-test that graded the tool against the tool would pass
# whatever the tool said, which is the half of a self-test worth nothing.
ORACLE = [
    ("gaming", "-", 0x56A2, 0x5762),
    ("office", "0", 0x56D2, 0x5792),
    ("office", "1", 0x5702, 0x57C2),
    ("turbo", "-", 0x5672, 0x5732),
]

# The `mov r6,#0x60 / mov r7,#0xf2 / mov dptr,#0x08e6` at 0x8653, as the bytes
# `manual-fan-ctrl-0751.md` §6 quotes. The `mov dptr` is in the same list
# because the base is only meaningful against the cell it is seeded into.
SEED_ORACLE = "7e 60 7f f2 90 08 e6 ee"

# The byte-identities §1 of the write-up rests on, held as the *pairs* the
# comparison names rather than as a count of them: a count is a value every
# firmware change would have to edit.
IDENTICAL = [("turbo", "-", "gaming", "-"),
             ("office", "0", "office", "1")]


def self_test(image: bytes, csv_path: str, stream=sys.stdout) -> int:
    """The refusals, the layout held against the vendor's own writer, and an
    oracle this file did not write for itself."""
    bad = 0

    def expect(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}"
              + (f"  {detail}" if detail and not ok else ""), file=stream)

    def refuses(fn, *a):
        try:
            fn(*a)
        except NotDecodable:
            return True
        return False

    print("fan_table_defaults.py --self-test", file=stream)
    base, rows = tables(image)

    # --- the refusals ------------------------------------------------------
    # A slot pointing into a bank window: readable at no single offset in this
    # dump, so the tool says so rather than returning the wrong 48 bytes.
    expect("a pointer at or above 0x8000 is refused",
           refuses(pointer_pair, _patched(image, 0x60F2,
                                          b"\x80\x00\x80\x20"), 0x60F2))
    # A table near the end of the dump: the bytes are not there.
    expect("a table past the end of the image is refused",
           refuses(read_code, image, len(image) - 4, TABLE_BYTES))
    # A duty byte the vendor's own /2 could not have produced.
    expect("an odd duty byte is refused rather than rounded",
           refuses(decode_blob, _duty_blob(0x41)))
    expect("a short blob is refused",
           refuses(decode_blob, b"\x00" * (TABLE_BYTES - 1)))
    # A seeding site that is not the sequence this tool reads, and one that
    # seeds the wrong cell: both are a base that is wrong invisibly.
    expect("a wrong seeding site is refused",
           refuses(pointer_base, _patched(image, SEED, b"\x00" * 8)))
    expect("a base seeded into the wrong cell is refused",
           refuses(pointer_base, _patched(image, SEED,
                                          b"\x7e\x60\x7f\xf2\x90\x08\xe7\xee")))
    # An offset that carries out of the low byte is not the next pair.
    expect("an offset carrying out of the low byte is refused",
           refuses(slot_address, 0x60F8, 0x0C))
    # A capture with no publish in it is a note per slot, not a crash and not
    # a silent zero-row comparison.
    empty = os.path.join(tempfile.gettempdir(), "fan_table_defaults-empty.jsonl")
    open(empty, "w").close()
    try:
        cmp_, notes = compare(rows, empty)
    finally:
        os.unlink(empty)
    expect("a capture with no Fan/Table publish reports one note per slot",
           len(notes) == len(SLOTS) and not cmp_, f"got {notes}")

    # --- the layout, held against the vendor's own writer ------------------
    for row in rows:
        written = fan_table_replay.ec_image(
            {fan: as_fan1p5(row["table"][fan]) for fan in ("CPU", "GPU")})
        for fan in ("CPU", "GPU"):
            half, covered = _half_from(written, fan)
            expect(f"{row['mode']} (bit 2 = {row['oem_bit_2']}) {fan}: "
                   f"decode/encode round-trips through "
                   f"fan_table_replay.ec_image() over the {len(covered)} "
                   f"offsets it writes",
                   decode_blob(half) == row["table"][fan])
            expect(f"{row['mode']} (bit 2 = {row['oem_bit_2']}) {fan}: the one "
                   f"offset neither side writes, 0x{GAP:02X}, is 0x00 in the "
                   f"EC's blob",
                   row["blob"][fan][GAP] == 0x00)
    # The convention the duty row is stored in, on a blob of our own rather
    # than this firmware's, so what is held is the rule and not the table.
    expect("0xC8 is 100 %", decode_blob(_duty_blob(0xC8))["Duty"][0] == 100)
    expect("0x00 is 0 %", decode_blob(_duty_blob(0x00))["Duty"][0] == 0)

    # --- the oracle --------------------------------------------------------
    expect(f"the pointer base is 0x60F2, from the bytes at 0x{SEED:04X}",
           base == 0x60F2, f"got 0x{base:04X}")
    expect(f"the seeding site holds `{SEED_ORACLE}`",
           read_code(image, SEED, 8).hex(" ") == SEED_ORACLE)
    got = {(r["mode"], r["oem_bit_2"]): (r["cpu"], r["gpu"]) for r in rows}
    by_key = {(r["mode"], r["oem_bit_2"]): r for r in rows}
    for mode, oem, cpu, gpu in ORACLE:
        expect(f"{mode} (0x0782 bit 2 = {oem}) is CPU 0x{cpu:04X} / "
               f"GPU 0x{gpu:04X}", got.get((mode, oem)) == (cpu, gpu),
               f"got {got.get((mode, oem))}")
    for a, ao, b, bo in IDENTICAL:
        for fan in ("CPU", "GPU"):
            expect(f"{a} (bit 2 = {ao}) {fan} is byte-identical to "
                   f"{b} (bit 2 = {bo}) {fan}",
                   by_key[(a, ao)]["blob"][fan] == by_key[(b, bo)]["blob"][fan])
    # The writeback, as the mechanism rather than as three numbers: the second
    # copy covers 0x0F30..0x0F5F, so the mailbox bytes are the GPU blob's own.
    expect("the second copy's 0x30 bytes reach 0x0F5F inclusive",
           GPU_BASE + TABLE_BYTES - 1 == WINDOW[1],
           f"0x{GPU_BASE + TABLE_BYTES - 1:04X}")
    for row in rows:
        over = writeback(row)
        for addr in MAILBOX:
            expect(f"{row['mode']} (bit 2 = {row['oem_bit_2']}): 0x{addr:04X} is "
                   f"left at 0x{over[addr]:02X} by the GPU copy, which is "
                   f"neither magic byte",
                   over[addr] not in MAGIC)

    # --- the committed CSV passes its own check ----------------------------
    expect("the committed CSV reproduces", check(image, csv_path, stream) == 0)

    print(f"{'all checks passed' if not bad else f'{bad} FAILED'}", file=stream)
    return 1 if bad else 0


def _patched(image: bytes, runtime: int, raw: bytes) -> bytes:
    """A copy of the image with `raw` laid down at runtime address `runtime`."""
    d = bytearray(image)
    off = trace_xdata_refs.offset_for_runtime(runtime, "bank0")
    d[off:off + len(raw)] = raw
    return bytes(d)


def _duty_blob(raw: int) -> bytes:
    b = bytearray(b"\x00" * TABLE_BYTES)
    b[DUTY] = raw
    return bytes(b)


def _half_from(written: dict, fan: str):
    """(the 48-byte half `ec_image()` would leave, the offsets it wrote).

    `SetEcFanTable` writes neither `0x0F10` nor `0x0F40`, so its image of a
    half is 47 bytes and a half is 48. The gap between the two step rows is
    also the one offset `decode_blob()` never reads, so the round-trip covers
    exactly the bytes the writer produces -- and `GAP` names the one neither
    side touches, rather than letting the count of 47 pass as 48.
    """
    base = CPU_BASE if fan == "CPU" else GPU_BASE
    half, covered = bytearray(TABLE_BYTES), []
    for i in range(TABLE_BYTES):
        if base + i in written:
            half[i] = written[base + i]
            covered.append(i)
    return bytes(half), covered


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: the committed one)")
    ap.add_argument("--csv", action="store_true",
                    help="the decode as CSV on stdout, and nothing else")
    ap.add_argument("--check", action="store_true",
                    help="regenerate the decode and diff it against the "
                         "committed CSV")
    ap.add_argument("--self-test", action="store_true",
                    help="the refusals, the layout round-trip, and an oracle "
                         "transcribed from the annotation")
    ap.add_argument("--csv-file", default=DEFAULT_CSV,
                    help="the committed CSV --check compares against")
    ap.add_argument("--mqtt", default=DEFAULT_MQTT,
                    help="the decoded MQTT JSONL the comparison reads")
    args = ap.parse_args(argv)

    image = open(args.firmware, "rb").read()

    if args.self_test:
        return self_test(image, args.csv_file)
    if args.check:
        return check(image, args.csv_file)
    if args.csv:
        sys.stdout.write(render_csv(image))
        return 0
    report(image, args.mqtt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
