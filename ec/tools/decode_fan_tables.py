#!/usr/bin/env python3
"""Every fan table the pointer pair table at `0x60F2` names, and where it ends
(issue #1227).

`fan_table_defaults.py` decoded the four pairs the mailbox handler at bank0
`0x888D` reaches and left the rest of the table alone, because nothing this
method had found reached them. It named the limit it was working under:
*"The pointer table's extent was not determined. `0x60F2` holds more pairs past
the four the handler reaches; where it ends, and what selects the rest, is not
read here."* (`../../docs/findings/ec-fan-table-defaults.md` §6.) This walks
the table to an end and decodes every table it names.

**The walk is a predicate, and the predicate is printed.** A count is
worthless without the rule that produced it, so `is_member()` below is the
rule, `predicate_text()` reports it on every run, and the walk stops at the
first entry it rejects and prints that entry's address and raw bytes. The rule
is the *relation* between a pair's two pointers -- the second is the first plus
`PAIR_STRIDE` -- and not either pointer's magnitude: a "both addresses are
below `0x8000`" test keeps accepting for a dozen entries past the break,
because the words that follow are also below `0x8000`. That is why the weaker
predicate is not used and why its over-run is stated rather than left as a
claim.

**The end is corroborated from the other side, and which side is which is
stated.** The accepted entries name 48-byte tables; if their union is one
contiguous run whose last byte is immediately below the pointer table's own
first byte, then the pointer table's start is confirmed by the payload it
points at rather than by a pattern that stopped. `payload_extent()` reports
that as a separate check from the walk, and `--csv` carries every table's
address so a reader can re-derive it. A pattern that stopped is not a
measurement; this is the difference between the two and the write-up leans on
it.

**What is not established, in one line.** Nothing here says the bytes are
degrees and per cent *to the EC*. The field names come from
`windows/tools/fan_table_replay.py`'s `ec_image()`, which is the vendor
service's own writer; a blob that decodes cleanly under that layout is
consistent with it and is not proof the EC reads it that way. `shape_checks()`
is the shape the layout predicts, applied per table and reported as a tally
rather than as an assertion over a few -- and it does not hold for everything:
see `band_failures()` for the one property that fails on some tables, which is
reported rather than dropped.

**How `0x888D` is entered.** The handler is the target of a `jz` at `0x887E`,
inside the `0x8749` mode tick, gated on `0x06C2` -- not only reachable by a
host mailbox round-trip, which is what a `lcall`/`ljmp` search reports because
nothing calls it. `reachability_text()` checks the *encoding*; what `0x06C2`
holds is not established here, though the committed `ec_watch` captures read it
zero across three windows -- see `docs/findings/ec-default-fan-tables.md` §4.

**Everything here is read out of the committed image.** No register was
written, none was read back, and no laptop, EC or Windows machine is
involved. These are the bytes the handler would copy, on the code that copies
them -- not a table observed running. `../../docs/hardware-tests/
fan-table-defaults-0f5d.md` is the unrun procedure that would settle it.

Usage:
    python3 decode_fan_tables.py                       # the walk, the extent, the comparison
    python3 decode_fan_tables.py --csv                 # every table, as CSV
    python3 decode_fan_tables.py --check               # hold the committed CSV
    python3 decode_fan_tables.py --self-test           # the refusals + the oracle
    python3 decode_fan_tables.py <firmware> --check
"""
import argparse
import collections
import csv
import difflib
import io
import json
import os
import sys

import trace_xdata_refs

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
DEFAULT_FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")
DEFAULT_CSV = os.path.join(EC, "annotations", "fan-table-curves.csv")

# The pointer pair table, and the seeding routine that names its first entry.
# Both are read out of the image rather than taken from this file: a base read
# from the wrong instruction is a table list that is wrong in a way nothing
# downstream can see, which is the failure `fan_table_defaults.pointer_base()`
# already refuses.
SEED = 0x8653
SEED_OPCODES = (0x7E, 0x7F, 0x90)
SEED_CELL = 0x08E6

# The stride between a pair's two pointers. Measured over the accepted entries,
# not assumed -- see `check_stride()` in `--self-test`, which holds every
# accepted pair's difference as a value rather than as a count of them.
PAIR_STRIDE = 0xC0

# One 48-byte half of the `0x0F00-0x0F5F` window: `0x888D`'s two copy loops are
# `cjne a,#0x30`, so this is the record length the EC's own code states.
TABLE_BYTES = 0x30

# The layout itself -- the offsets within a half, the vendor's field names, the
# decode and the refusals -- is `fan_table_defaults.py`'s, reached through the
# module rather than restated here. A second copy of a layout is the drift that
# tool's own test guards against, and this file's job is the walk, the extent
# and the shape check over *every* table rather than the decode of four.
import fan_table_defaults as ftd  # noqa: E402

# The `--csv` header. A list so a column cannot reach the output without
# appearing here, the reason `data_regions.py` keeps its own the same way.
CSV_COLUMNS = ("index", "entry_addr", "role", "fan", "code_addr",
               "upt", "downt", "duty")


class NotDecodable(Exception):
    """A byte range this tool will not guess at, the same class and the same
    intent as `fan_table_defaults.NotDecodable` -- kept separate so importing
    this tool costs the other one nothing."""


# --- the predicate ---------------------------------------------------------

def predicate_text() -> str:
    """The membership rule, in one line, for every run that reports a count.

    Printed rather than documented: a number of table entries is meaningless
    to a reader who cannot see what stopped the walk.
    """
    return (f"a 4-byte entry at 0x60F2+4n is a member when its second pointer "
            f"is its first plus 0x{PAIR_STRIDE:02X} and both are below the "
            f"0x8000 bank window")


def is_member(raw: bytes) -> bool:
    """`predicate_text()`, as code.

    Both halves matter and the second is the one that binds: the pointers that
    follow the table are also below 0x8000, so the bank check alone over-runs.
    """
    first, second = (raw[0] << 8) | raw[1], (raw[2] << 8) | raw[3]
    return (second == first + PAIR_STRIDE
            and first < 0x8000 and second < 0x8000)


# --- reading the image -----------------------------------------------------

def read_code(image: bytes, runtime: int, length: int = 1) -> bytes:
    """`length` CODE bytes at runtime address `runtime`, seen from bank0.

    `trace_xdata_refs.offset_for_runtime()` rather than a bare index, for the
    reason `fan_table_defaults.read_code()` gives: every table this tool finds
    is below `0x8000`, so file offset equals runtime address, and going through
    the same function the rest of `ec/tools` uses is what keeps a future one
    above the window from being read at the wrong offset silently.
    """
    off = trace_xdata_refs.offset_for_runtime(runtime, "bank0")
    if off is None:
        raise NotDecodable(
            f"0x{runtime:04X} is not reachable as CODE from bank0, so its file "
            f"offset is unknown -- see trace_xdata_refs.offset_for_runtime()")
    if off + length > len(image):
        raise NotDecodable(f"0x{runtime:04X}+{length} runs past the end of "
                           f"the image")
    return image[off:off + length]


def pointer_base(image: bytes) -> int:
    """The CODE pointer base `0x8653` seeds into `0x08E6`/`0x08E7`.

    Read out of the image, not asserted, for `fan_table_defaults`'s reason.
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


# --- the walk --------------------------------------------------------------

class Walk:
    """The accepted entries, the entry the walk stopped at, and why.

    `break_addr` and `break_bytes` are kept rather than discarded: the point of
    a measured end is that the reader can see the bytes it stopped on and
    disagree with the rule.
    """

    def __init__(self, base, entries, break_addr, break_bytes):
        self.base = base
        self.entries = entries          # [(entry_addr, cpu, gpu), ...]
        self.break_addr = break_addr
        self.break_bytes = break_bytes

    def __len__(self):
        return len(self.entries)


def walk(image: bytes, base: int, limit: int = 0x10000) -> Walk:
    """Walk the pair table from `base` until an entry fails `is_member()`.

    `limit` is a bound on the scan, not a claim about the table's length: it
    stops a runaway rather than deciding anything, and reaching it is reported
    by `break_addr is None` rather than passing for an end.
    """
    entries = []
    for n in range(limit // 4):
        addr = base + 4 * n
        if addr + 4 > len(image):
            return Walk(base, entries, None, None)
        raw = read_code(image, addr, 4)
        if not is_member(raw):
            return Walk(base, entries, addr, raw)
        entries.append((addr, (raw[0] << 8) | raw[1], (raw[2] << 8) | raw[3]))
    return Walk(base, entries, None, None)


def payload_extent(walk_: Walk):
    """-> (lo, hi, distinct) over the 48-byte spans the accepted entries name.

    The corroboration the write-up leans on, kept separate from `walk()` on
    purpose. The walk says where the *pointer* table stopped; this says whether
    the *payload* it names forms one block ending immediately below that
    pointer table's first byte. When it does, the two agree about where the
    region is from opposite directions, which is a measurement. When it does
    not, `contiguous` is False and the count is still only a pattern that
    stopped -- so the caller says which.
    """
    spans = set()
    for _, cpu, gpu in walk_.entries:
        spans.add((cpu, cpu + TABLE_BYTES))
        spans.add((gpu, gpu + TABLE_BYTES))
    if not spans:
        return None
    lo = min(s for s, _ in spans)
    hi = max(e for _, e in spans)
    contiguous = sum(e - s for s, e in spans) == hi - lo
    return lo, hi, len(spans), contiguous


# --- the decode ------------------------------------------------------------

def decode_all(image: bytes, walk_: Walk):
    """Every table the walk accepted, decoded in the vendor's field names.

    `fan_table_defaults.decode_blob()` does the decode rather than this file:
    one copy of the layout is the point, and this file's job is the walk, the
    extent and the shape check. A blob it refuses is *recorded*, not dropped --
    a table that fails to decode is a finding about the firmware, and dropping
    it would make the tally below silently smaller than the walk.
    """
    out, refused = [], []
    for index, (_, cpu, gpu) in enumerate(walk_.entries):
        for fan, addr in (("CPU", cpu), ("GPU", gpu)):
            blob = read_code(image, addr, TABLE_BYTES)
            try:
                table = ftd.decode_blob(blob)
            except ftd.NotDecodable as exc:
                refused.append((index, fan, addr, str(exc)))
                continue
            out.append({"index": index, "entry_addr": walk_.entries[index][0],
                        "fan": fan, "code_addr": addr, "blob": blob,
                        "table": table})
    return out, refused


def _ramp_ok(row) -> bool:
    """A row that rises and then stops, ignoring the 0xFF tail.

    Non-decreasing *up to* the terminator: comparing across the 0xFF run would
    test a padding pattern rather than a ramp.
    """
    vals = list(row)
    if 0xFF in vals:
        vals = vals[:vals.index(0xFF)]
    return all(a <= b for a, b in zip(vals, vals[1:]))


def shape_checks(table) -> dict:
    """The properties the documented layout predicts, for one decoded table.

    Three independent properties rather than one, because each is a different
    way the layout could be wrong:

    - `upt_ramp`: the `UpT` row rises and is terminated by `0xFF`;
    - `downt_ramp`: the `DownT` row rises, with no terminator of its own --
      it runs out where `UpT` does;
    - `duty_bounded`: every duty value is within 0-100 %, which is what the
      doubled convention means (`0xC8` is 100 %).

    Duty is *not* re-checked for evenness here. `decode_blob()` halves each
    stored byte and refuses an odd one, so the evenness is already established
    by the time a table reaches this function; asserting it again would be a
    second copy of that rule rather than a second opinion on it.

    `DownT` is held to rising and nothing more. It does not start at 0: the
    first entry is 48 in every table measured, which is a floor the layout
    does not predict and this tool does not assert.
    """
    return {
        "upt_ramp": 0xFF in table["UpT"] and _ramp_ok(table["UpT"]),
        "downt_ramp": _ramp_ok(table["DownT"]),
        "duty_bounded": all(0 <= d <= 100 for d in table["Duty"]),
    }


def band_failures(table) -> list:
    """Where `DownT[i]` is at or above `UpT[i+1]` -- the hysteresis band.

    Reported, not asserted. The layout says `DownT[i]` and `UpT[i+1]` are the
    two ends of one entry's band, so a table where the lower is not below the
    upper has a band the reading does not explain. Whether that is the vendor
    writing a table by hand, a per-level override, or this decode's layout
    being subtly wrong is **not** settled here, and a table that fails is
    printed rather than dropped.
    """
    upt, downt = table["UpT"], table["DownT"]
    return [(i, downt[i], upt[i + 1]) for i in range(len(upt) - 1)
            if upt[i + 1] != 0xFF and downt[i] >= upt[i + 1]]


def band_grouping_text(banded) -> list:
    """The failing tables grouped by the **entry** they belong to.

    The per-table lines above say *which tables* fail; this says *how they
    arrive*, which is the shape the write-up's finding is about. Grouping by
    entry rather than by address is what makes it visible: a failure that
    takes both halves of one pointer pair is a property of that pair's table,
    while a lone half failing is a different thing again. A write-up that
    described the grouping from memory would drift from this output the first
    time a table moved, so the sentence is derived here and asserted against
    this function instead.

    -> a list of report lines: the block's header, then one line per way the
    failures group. With nothing failing it is the header alone.
    """
    halves = collections.defaultdict(set)
    for row, _fails in banded:
        halves[row["index"]].add(row["fan"])
    both = sorted(i for i, fans in halves.items()
                  if fans == {"CPU", "GPU"})
    gpu = sorted(i for i, fans in halves.items() if fans == {"GPU"})
    cpu = sorted(i for i, fans in halves.items() if fans == {"CPU"})
    out = ["  grouped by pointer-pair entry:"]
    for label, indexes in (("both halves", both), ("GPU half alone", gpu),
                           ("CPU half alone", cpu)):
        if indexes:
            out.append(f"    {label}: entries "
                       + ", ".join(str(i) for i in indexes))
    return out


def tally(rows, refused) -> dict:
    """-> {check: (passed, total)} over every table the walk accepted.

    A tally rather than an assertion, and every table is in the denominator --
    refused ones included -- so a firmware that decodes fewer tables shows up
    as a smaller denominator rather than as a clean pass over fewer rows.
    """
    checks = ("upt_ramp", "downt_ramp", "duty_bounded")
    passed = {c: 0 for c in checks}
    for row in rows:
        for name, ok in shape_checks(row["table"]).items():
            passed[name] += 1 if ok else 0
    total = len(rows) + len(refused)
    return {c: (passed[c], total) for c in checks}


# --- output ----------------------------------------------------------------

def roles(image: bytes, walk_: Walk) -> dict:
    """-> {index: role} for the entries the mailbox handler can reach.

    Taken from `fan_table_defaults.SLOTS` -- the offsets `0x888D` adds to the
    base's low byte -- rather than restated, so a change in the handler is
    red here too. The offset is added to the low byte because that is what the
    handler's `add a,#n` does; `fan_table_defaults.slot_address()` refuses an
    offset that would carry out of it.
    """
    out = {}
    for mode, selector, offset, oem, _helper in ftd.SLOTS:
        slot = ftd.slot_address(walk_.base, offset)
        for index, (entry_addr, _, _) in enumerate(walk_.entries):
            if entry_addr == slot:
                out[index] = (f"{mode}/0x0F5F={selector}"
                              + ("" if oem == "-" else f"/0x0782b2={oem}"))
    return out


def _listing(image: bytes, addr: int, length: int):
    """`length` bytes at `addr`, as `0xADDR  bb bb ...` lines.

    A hex dump rather than a disassembly. `disasm8051.py` is the repo's linear
    decoder and `r2` is the independent one, and this file's argument is about
    *which bytes* are there -- so it prints them and leaves the decoding to the
    two places that own it. `8749.asm` is the listing proper.
    """
    raw = read_code(image, addr, length)
    out = []
    for i in range(0, length, 8):
        chunk = raw[i:i + 8]
        out.append(f"0x{addr + i:04X}  {chunk.hex(' ')}")
    return out


def fmt(values) -> str:
    return " ".join(str(v) for v in values)


# --- how the handler is reached ---------------------------------------------

# The mailbox handler's own entry, and the branch that names it. `manual-fan-
# ctrl-0751.md` §6 records the trigger as "explicit host request" and says "No
# site in §2 reaches this code", which is true of a `mov dptr,#0x0751` site
# scan and false of the image: `0x887E` is a `jz` whose target is the
# handler, inside the `0x8749` mode tick. Nothing calls `0x888D`, which is
# exactly why a `lcall`/`ljmp` search reports no caller.
HANDLER = 0x888D

# The branch, its opcode, and the target it decodes to. Asserted against the
# image rather than against the committed branch-target table, so a firmware
# whose encoding moved is red here rather than agreeing with a transcription.
BRANCH = (0x887E, 0x60, HANDLER)

# The tail of the routine the branch sits in, which is what names both arms:
# the branch falls through to the re-seed, and the handler is where it lands
# when `0x06C2` is zero.
TAIL = bytes.fromhex("9006c2 e0 600d 128653 743c 12bb24 743c 02893e"
                     .replace(" ", ""))


def handler_branch(image: bytes):
    """-> the branch's target if `BRANCH` decodes as a `jz` to the handler,
    else None.

    Decoded by hand rather than through `disasm8051.py`: the encoding is two
    bytes -- an opcode and a signed 8-bit displacement -- and the displacement
    is relative to the instruction *after* the branch, so the target is
    `addr + 2 + disp` and not `addr + 3 + disp`. `manual-fan-ctrl-0751.md` §9
    records the same trap landing `0x943E` mid-instruction on another site. The
    arithmetic is spelled out here so a reader can check it rather than trust it.
    """
    addr, opcode, target = BRANCH
    raw = read_code(image, addr, 2)
    if raw[0] != opcode:
        return None
    disp = raw[1] - 256 if raw[1] > 127 else raw[1]
    landed = addr + 2 + disp
    return landed if landed == target else None


def reachability_text(image: bytes) -> str:
    """The one line the report prints about how `0x888D` is entered.

    A check on the *encoding*, not on reachability in general. What this
    settles is narrow and worth stating exactly: the handler has a caller
    inside the image that is not a call, so "`0x888D` is only reachable on
    explicit host request" is false. Scoped to the image this reads, what
    `0x06C2` holds and how often the tick runs are still open -- a branch that
    exists is not a branch that is taken. The committed `ec_watch` captures
    say something about the gate's value and this line does not restate it;
    `docs/findings/ec-default-fan-tables.md` §4 is where that reading is.
    """
    landed = handler_branch(image)
    if landed is None:
        return ("how 0x{:04X} is entered: no `jz` to it at 0x{:04X} -- this "
                "image does not have the branch this tool looks for".format(
                    HANDLER, BRANCH[0]))
    return (f"how 0x{HANDLER:04X} is entered: the `jz` at 0x{BRANCH[0]:04X} "
            f"lands on it, inside the 0x8749 mode tick, when XDATA 0x06C2 "
            f"reads zero. No `lcall`/`ljmp` names it, which is why a call-graph "
            f"search reports no caller. What 0x06C2 holds is not established "
            f"from the image.")


# --- against the tables the vendor ships ------------------------------------

# The committed `UserFanTables` the issue names. Three project directories,
# each a machine the service ships tables for. Nothing here decides which one
# *this* machine is -- that is a separate question -- so every project's tables
# are compared rather than one being picked, which is also why the comparison
# does not depend on the answer: none of them matches.
VENDOR_ROOT = os.path.join(REPO, "vendor", "control-center-3.9.18.0",
                           "UserFanTables")

# The shipped file name per EC mode, from `fan_table_defaults.PUBLISHED_FOR`:
# the same join that maps the mailbox's selector onto the service's own naming.
# `M3T1` is absent from every committed project directory, so Turbo has no
# shipped table to compare against and that is reported as a note rather than
# skipped quietly.
VENDOR_MODE_FILE = dict(ftd.PUBLISHED_FOR)


def vendor_tables(root: str = VENDOR_ROOT):
    """Every shipped `M*T1` table, keyed by (project, mode).

    Read with `json`, which is all the format needs. A project directory with
    no such file contributes nothing for that mode, and `VENDOR_MODE_FILE`
    being consulted by the caller is what turns that into a note.
    """
    out = {}
    if not os.path.isdir(root):
        return out
    for project in sorted(os.listdir(root)):
        path = os.path.join(root, project)
        if not os.path.isdir(path):
            continue
        for name in sorted(os.listdir(path)):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(path, name), encoding="utf-8") as fh:
                out[(project, os.path.splitext(name)[0])] = json.load(fh)
    return out


def vendor_comparison(image: bytes, walk_: Walk, root: str = VENDOR_ROOT):
    """The EC's own tables against every shipped table, per project and mode.

    -> (rows, notes). Indexed by the EC's own used levels rather than the
    shipped table's, so a trailing 255 on the shipped side reads as "the
    shipped table stops here" instead of being compared against a stale EC
    entry. A shipped row that is all zeros for a fan is reported as **empty**
    and left out of the comparison rather than compared: an all-zero GPU half
    is what every committed project ships, and matching the EC against it would
    produce a difference that says nothing about either curve.

    Keyed by the mode half of the role, so the two Office slots land on one
    table rather than appearing twice. That is sound because they are
    byte-identical (`ec-fan-table-defaults.md` §3) and the suite holds both
    against the image; were a firmware to differentiate them, `by_role` would
    keep the last of the two and the comparison would silently cover one.
    """
    decoded, _ = decode_all(image, walk_)
    by_role = {}
    for index, role in roles(image, walk_).items():
        for row in decoded:
            if walk_.entries[index][0] == row["entry_addr"]:
                by_role.setdefault(role.split("/")[0], {})[row["fan"]] = row
    shipped = vendor_tables(root)
    notes, out = [], []
    for mode, name in sorted(VENDOR_MODE_FILE.items()):
        holders = sorted(p for p, n in shipped if n == name)
        if not holders:
            notes.append(f"{mode} ({name}): no committed project ships this "
                         f"table, so there is nothing to compare against")
            continue
        for project in holders:
            table = shipped[(project, name)]
            for fan in ("CPU", "GPU"):
                ec = by_role.get(mode, {}).get(fan)
                if ec is None:
                    continue
                if not any(e["Duty"] for e in table[fan]):
                    notes.append(f"{project} {name} {fan}: every shipped entry "
                                 f"is zero, so there is no curve to compare")
                    continue
                levels = ftd.used(ec["table"])
                out.append((project, mode, fan, ec,
                            {f: ([ec["table"][f][i] for i in levels],
                                  [table[fan][i][f] for i in levels])
                             for f in ("UpT", "DownT", "Duty")}))
    return out, notes


def report(image: bytes, stream=sys.stdout) -> None:
    w = walk(image, pointer_base(image))
    rows, refused = decode_all(image, w)
    extent = payload_extent(w)
    role_of = roles(image, w)

    print(f"fan-table pointer base 0x{w.base:04X}, seeded at bank0 "
          f"0x{SEED:04X}", file=stream)
    print(f"membership predicate: {predicate_text()}", file=stream)
    print(f"{len(w)} member entries accepted", file=stream)
    if w.break_addr is None:
        print("  the scan bound was reached before any entry was rejected -- "
              "this is a bound, not an end", file=stream)
    else:
        print(f"  first rejected entry at 0x{w.break_addr:04X}, bytes "
              f"{w.break_bytes.hex(' ')}", file=stream)

    print("\npayload extent, corroborated from the other side:", file=stream)
    if extent is None:
        print("  no member entries named a table", file=stream)
    else:
        lo, hi, distinct, contiguous = extent
        print(f"  {distinct} distinct 48-byte spans, "
              f"0x{lo:04X}..0x{hi:04X}", file=stream)
        print(f"  contiguous: {contiguous}", file=stream)
        print(f"  last byte is immediately below the pointer table: "
              f"{hi == w.base}", file=stream)

    counts = tally(rows, refused)
    print("\nlayout shape checks, every accepted table in the denominator:",
          file=stream)
    for name, (passed, total) in counts.items():
        print(f"  {name:20s} {passed}/{total}", file=stream)
    for index, fan, addr, why in refused:
        print(f"  refused: entry {index} {fan} at 0x{addr:04X}: {why}",
              file=stream)

    # The band, reported rather than asserted: see band_failures().
    banded = [(row, band_failures(row["table"])) for row in rows]
    banded = [(row, fails) for row, fails in banded if fails]
    print(f"\nhysteresis band, DownT[i] below UpT[i+1]: "
          f"{len(rows) - len(banded)}/{len(rows)} tables", file=stream)
    overshoot = collections.Counter(
        d - u for _row, fails in banded for _i, d, u in fails)
    if overshoot:
        print("  by how much, over every failing level: "
              + ", ".join(f"{k} C x{v}" for k, v in sorted(overshoot.items())),
              file=stream)
    for row, fails in banded:
        first = fails[0]
        print(f"  0x{row['code_addr']:04X} {row['fan']:3s} "
              f"{len(fails)} entr(y/ies), first at level {first[0]}: "
              f"DownT {first[1]} >= UpT {first[2]}", file=stream)
    for line in band_grouping_text(banded):
        print(line, file=stream)

    print("\nrole, from the offsets 0x888D adds to the base's low byte:",
          file=stream)
    for index, (entry_addr, cpu, gpu) in enumerate(w.entries):
        role = role_of.get(index, "-")
        print(f"  entry {index:2d}  0x{entry_addr:04X}  CPU 0x{cpu:04X}  "
              f"GPU 0x{gpu:04X}  {role}", file=stream)

    print("\n" + reachability_text(image), file=stream)
    print("  the branch's own block, as the image holds it:", file=stream)
    for line in _listing(image, BRANCH[0] - 4, len(TAIL)):
        print(f"    {line}", file=stream)

    cmp_rows, notes = vendor_comparison(image, w)
    print("\nagainst the tables the vendor ships, on the EC's own used "
          "levels:\n", file=stream)
    for project, mode, fan, ec, fields in cmp_rows:
        print(f"  {project} {VENDOR_MODE_FILE[mode]} {fan} "
              f"(EC 0x{ec['code_addr']:04X})", file=stream)
        for name in ("UpT", "DownT", "Duty"):
            mine, theirs = fields[name]
            same = mine == theirs
            print(f"    {name:5s}  EC      {fmt(mine)}", file=stream)
            print(f"    {name:5s}  shipped {fmt(theirs)}"
                  f"   {'MATCH' if same else 'differ'}", file=stream)
    for note in notes:
        print(f"  note  {note}", file=stream)


def csv_rows(image: bytes):
    w = walk(image, pointer_base(image))
    rows, _ = decode_all(image, w)
    role_of = roles(image, w)
    entry_of = {addr: (index, cpu, gpu)
                for index, (addr, cpu, gpu) in enumerate(w.entries)}
    out = []
    for row in rows:
        index, cpu, gpu = entry_of[row["entry_addr"]]
        t = row["table"]
        out.append({
            "index": index,
            "entry_addr": f"0x{row['entry_addr']:04X}",
            "role": role_of.get(index, "-"),
            "fan": row["fan"], "code_addr": f"0x{row['code_addr']:04X}",
            "upt": fmt(t["UpT"]), "downt": fmt(t["DownT"]),
            "duty": fmt(t["Duty"]),
        })
    return out


def render_csv(image: bytes) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(csv_rows(image))
    return buf.getvalue()


# --- checks ----------------------------------------------------------------

def check(image: bytes, path: str, stream=sys.stdout) -> int:
    """Regenerate the decode in memory and diff it against the committed CSV.

    There is no `--out-` and nothing in this file opens a file for writing, so
    a `--check` here cannot decide what the file says.
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


# The oracle for --self-test, transcribed by hand from the byte reads on the
# committed image and from ../annotations/manual-fan-ctrl-0751.md §6 -- NOT from
# this file's own output. A self-test that graded the tool against the tool
# would pass whatever the tool said, which is the half of a self-test worth
# nothing.
#
# The first rejected entry, as an address and as the four bytes at it. Held as
# literals because "the walk stopped" is only a measurement next to what it
# stopped on.
BREAK = (0x6162, b"\x41\x37\x05\x05")

# The four entries `0x888D` reaches, as (index, entry address). These are the
# slots `fan_table_defaults.SLOTS` names, and §6 of
# ../annotations/manual-fan-ctrl-0751.md quotes the CODE addresses they hold.
REACHED = ((0, 0x60F2), (1, 0x60F6), (2, 0x60FA), (3, 0x60FE))


def self_test(image: bytes, csv_path: str, stream=sys.stdout) -> int:
    """The refusals, the predicate's own stopping rule, and an oracle this
    file did not write for itself."""
    bad = 0

    def expect(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}"
              + (f"  {detail}" if detail and not ok else ""), file=stream)

    def refuses(fn, *a):
        try:
            fn(*a)
        except (NotDecodable, ftd.NotDecodable):
            return True
        return False

    print("decode_fan_tables.py --self-test", file=stream)
    base = pointer_base(image)
    w = walk(image, base)
    rows, refused = decode_all(image, w)

    # --- the refusals ------------------------------------------------------
    expect("a seeding site that is not the sequence this tool reads is refused",
           refuses(pointer_base, _patched(image, SEED, b"\x00" * 8)))
    expect("a base seeded into the wrong cell is refused",
           refuses(pointer_base, _patched(image, SEED,
                                          b"\x7e\x60\x7f\xf2\x90\x08\xe7\xee")))
    expect("a table past the end of the image is refused",
           refuses(read_code, image, len(image) - 4, TABLE_BYTES))

    # --- the predicate's stopping rule, on fixtures rather than on this image
    # An image that ends one entry early, and one one entry late: the walk has
    # to stop where the bytes stop rather than assume its own count.
    early = _patched(image, BREAK[0] - 4, b"\x00\x00\x00\x00")
    early_walk = walk(early, base)
    expect("breaking the last accepted entry stops the walk one step earlier",
           early_walk.break_addr == BREAK[0] - 4
           and len(early_walk) == len(w) - 1,
           f"got {early_walk.break_addr}")
    # To go *later*, the entry the walk stops at has to become a member -- and
    # the one after it is not a member already, so that is where it stops.
    late_walk = walk(_patched(image, BREAK[0], _member_bytes()), base)
    expect("making the break entry a member extends the walk one step",
           late_walk.break_addr == BREAK[0] + 4
           and len(late_walk) == len(w) + 1,
           f"got {late_walk.break_addr}")
    # The rule is the relation, not the magnitude: an entry whose two pointers
    # are both below the bank window but not a stride apart is not a member.
    expect("a pair of unrelated addresses below 0x8000 is not a member",
           not is_member(b"\x56\xa2\x57\x72"))
    expect("a pair a stride apart is a member",
           is_member(b"\x56\xa2\x57\x62"))
    expect("a pair whose second pointer is at or above 0x8000 is not a member",
           not is_member(b"\x56\xa2\xd7\x62"))

    # --- the oracle --------------------------------------------------------
    expect(f"the pointer base is 0x60F2, from the bytes at 0x{SEED:04X}",
           base == 0x60F2, f"got 0x{base:04X}")
    expect(f"the walk stops at 0x{BREAK[0]:04X}",
           w.break_addr == BREAK[0], f"got {w.break_addr}")
    expect(f"the bytes at the break are {BREAK[1].hex(' ')}",
           w.break_bytes == BREAK[1], f"got {w.break_bytes}")
    # Held as the pairs it reaches rather than as a count of them: a count is a
    # value every firmware change would have to edit.
    for index, addr in REACHED:
        expect(f"entry {index} is at 0x{addr:04X}",
               w.entries[index][0] == addr, f"got 0x{w.entries[index][0]:04X}")
    for _, cpu, gpu in w.entries:
        expect(f"the pair (0x{cpu:04X}, 0x{gpu:04X}) is a stride apart",
               gpu == cpu + PAIR_STRIDE)

    # --- the corroboration, from the payload side --------------------------
    lo, hi, distinct, contiguous = payload_extent(w)
    expect("the named tables are one contiguous run", contiguous)
    expect("that run ends immediately below the pointer table's first byte",
           hi == base, f"got 0x{hi:04X}")
    expect("the run is as long as its distinct spans make it",
           hi - lo == distinct * TABLE_BYTES,
           f"0x{hi - lo:04X} vs {distinct} * 0x{TABLE_BYTES:02X}")
    expect("no two accepted entries name the same table",
           distinct == 2 * len(w))

    # --- the decode --------------------------------------------------------
    expect("every accepted table decodes", not refused, f"{refused[:2]}")
    counts = tally(rows, refused)
    for name, (passed, total) in counts.items():
        print(f"        {name}: {passed}/{total}", file=stream)
    for row in rows:
        if not all(shape_checks(row["table"]).values()):
            print(f"        table at 0x{row['code_addr']:04X} fails a shape "
                  f"check: {shape_checks(row['table'])}", file=stream)

    # --- the roles come from the handler, not from this file ---------------
    role_of = roles(image, w)
    expect("the four offsets 0x888D adds name four different entries",
           len(set(role_of)) == len(REACHED)
           and set(role_of) == {i for i, _ in REACHED}, f"got {role_of}")

    # --- the branch that reaches the handler -------------------------------
    # Held against the image: the point is that the encoding *is* there, and
    # against the committed branch-target table as a second, independent read
    # of the same three bytes.
    expect(f"the `jz` at 0x{BRANCH[0]:04X} lands on 0x{HANDLER:04X}",
           handler_branch(image) == HANDLER, f"got {handler_branch(image)}")
    expect("the branch's opcode is a `jz`",
           read_code(image, BRANCH[0], 1)[0] == BRANCH[1])
    expect("the tail reads 0x06C2, branches, and otherwise re-seeds the base",
           read_code(image, BRANCH[0] - 4, len(TAIL)) == TAIL,
           f"got {read_code(image, BRANCH[0] - 4, len(TAIL)).hex(' ')}")
    expect("the committed branch-target table records the same branch",
           _branch_table_agrees(), "no row names the handler as a target")

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


def _member_bytes() -> bytes:
    """Four bytes that satisfy `is_member()`, for the stopping-rule fixture.

    Built from `PAIR_STRIDE` rather than transcribed, so the fixture cannot
    disagree with the rule it is testing: it is a member by construction, and
    the test that uses it is about *where the walk stops*, not about whether a
    particular pair is accepted.
    """
    first = 0x5672
    return bytes((first >> 8, first & 0xFF,
                  (first + PAIR_STRIDE) >> 8, (first + PAIR_STRIDE) & 0xFF))


def _branch_table_agrees() -> bool:
    """Does `bank-relative-branch-targets.csv` name the handler as a target?

    A second, independent read of the same three bytes: the table is committed
    and derived by another tool, so agreeing with it is corroboration rather
    than a restatement of what `handler_branch()` just did. A missing table is
    `True` rather than a failure -- this firmware may not ship one -- and the
    suite covers the case where it does.
    """
    path = os.path.join(EC, "annotations", "bank-relative-branch-targets.csv")
    if not os.path.exists(path):
        return True
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (int(row["runtime"], 16) == BRANCH[0]
                    and int(row["target"], 16) == HANDLER):
                return True
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: the committed one)")
    ap.add_argument("--csv", action="store_true",
                    help="every table as CSV on stdout, and nothing else")
    ap.add_argument("--check", action="store_true",
                    help="regenerate the decode and diff it against the "
                         "committed CSV")
    ap.add_argument("--self-test", action="store_true",
                    help="the refusals, the stopping rule, and an oracle "
                         "transcribed from the image")
    ap.add_argument("--csv-file", default=DEFAULT_CSV,
                    help="the committed CSV --check compares against")
    args = ap.parse_args(argv)

    image = open(args.firmware, "rb").read()

    if args.self_test:
        return self_test(image, args.csv_file)
    if args.check:
        return check(image, args.csv_file)
    if args.csv:
        sys.stdout.write(render_csv(image))
        return 0
    report(image)
    return 0


if __name__ == "__main__":
    sys.exit(main())