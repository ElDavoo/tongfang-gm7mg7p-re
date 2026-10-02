#!/usr/bin/env python3
"""Decode the three tables the charge-target task chain runs through, and the
chain itself.

Issue #89 asked how bank0 `0xB158` (the routine that writes the charger's
constant-voltage target `0x0522`) is reached, given that no `lcall`/`ljmp`
names it anywhere in the image. The answer is a chain in which every hop runs
through a table rather than a call, which is why the direct-call census in
`../annotations/bank-call-targets.csv` could not see any of it:

    common 0x0DD6   the inline case table of the scheduler 0x0D7B, whose
                    case 0x0A entry selects 0x0DFE
      -> common 0x0DFE .. 0x0E5D  a block of `ljmp`s into the far-call stubs
        -> common 0x1150..0x1AC1   the far-call stub table, 403 entries
          -> bank0 0x8539          a slot in a stride-3 run of calls/ljmp
            -> bank0 0x853F        the next slot in that run, `lcall 0xB12C`
              -> bank0 0xB12C      which falls through `jb acc.1,0xB158` into
                                   0xB158

This tool re-derives the three tables from the committed image so the chain is
checkable rather than asserted, and writes
`../annotations/task-call-table.csv` -- one row per table entry -- which
`--check` holds to those bytes.

**What the three tables are, defined as bytes rather than as intent.**

  * The *far-call stub table* is every `90 hi lo 02 11 xx` in the common area:
    `mov dptr,#<target>`, then `ljmp` to one of the two bank-select stubs
    `find_banks.py` names (0x1100 selects bank 0, 0x1114 selects bank 1).
    There is exactly one such table, 403 entries at 0x1150 on a stride of 6,
    and every one of its 403 immediates is a banked-window address (>= 0x8000)
    -- the table exists to make a common-area caller reach banked code, so a
    target below 0x8000 would mean the scan has run off the end of the table
    into whatever follows, and `--check` reports the count rather than
    accepting it.
  * The *stride-3 transfer runs* are maximal runs, inside bank 0, of
    consecutive 3-byte absolute transfers -- `lcall addr16` (0x12) and
    `ljmp addr16` (0x02) -- each starting exactly 3 bytes after the last. The
    0x02 form needs the 0x93 carve-out: `02 93` is `ljmp @a+dptr`, a
    two-byte opcode, and reading it as `ljmp` would put a phantom entry in the
    table at whatever address followed it.
  * The *switch case table* is the one inline table the chain's top runs
    through: the three-byte `address-then-case-value` triples that follow an
    `lcall 0x7151` in the common area, which is the `switch_case_dispatch`
    entry this repository has already named. It is read with the dispatch
    code's own grammar rather than an assumed one -- a triple whose address is
    0x0000 is the terminator, because that is the test in the movc/jnz pair
    at 0x7157-0x7158 and 0x715C-0x715D, and the table ends there.

The run *containing* the chain's slot is bank0 0x8518, 22 entries. It does not
start at 0x84EB, which is where a linear walk from 0x84EB reaches it: two
earlier runs (0x84EB, 7 entries, and 0x8502, 5) sit at the same stride but are
separated from it by `ret`s and a `mov a,r7` / `jz` pair, so they are runs of
their own. `--chain` prints all three, because the distinction is the whole
difference between "one of 22 slots" and "one of 35".

**What this cannot do, stated once so no output below has to repeat it.**

  * A table row is a byte pattern, not a claim that the row is *executed*.
    `--chain` resolves which case selects the chain's slot, but it does not
    follow what raises that case, and it says so: the rate is written up as
    open in `../../docs/findings/charge-target-caller-chain.md`, which is where
    the two remaining gaps are named.
  * Nothing here observes hardware. No register is read, written or read back,
    and no tick rate is claimed: `--chain` reports the structure that dispatches
    the chain, not how often it runs. `0x09C7`/`0x09C8` are a seconds/minutes
    counter *inside* the dispatched task, not a tick source driving it.
  * `--search` prints "not found by this method, over these regions", with the
    region on the line. It is not an absence claim, and the one it makes about
    `0xB158` is exactly the negative result issue #89 asked to have recorded.

**Refusals are the half of `--self-test` that matters.** The known answers
below pin the table-finding logic against the committed image, so a scan that
has quietly started finding the wrong thing is red. `check_table()` is the
same function `--check` runs, driven against a table mutated three ways, so
the claim that `--check` still rejects drift is asserted rather than assumed:
a check that has quietly started accepting everything looks exactly like a
check that is working.

Usage:
    python3 task_call_table.py ../firmware/GMxMGxx_11.800
    python3 task_call_table.py ../firmware/GMxMGxx_11.800 --chain
    python3 task_call_table.py ../firmware/GMxMGxx_11.800 --search
    python3 task_call_table.py ../firmware/GMxMGxx_11.800 --check
    python3 task_call_table.py ../firmware/GMxMGxx_11.800 --self-test
    python3 task_call_table.py ../firmware/GMxMGxx_11.800 --write
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEFAULT_FIRMWARE = os.path.join("ec", "firmware", "GMxMGxx_11.800")
CSV_PATH = os.path.join(HERE, os.pardir, "annotations", "task-call-table.csv")

# The region map, from the module every other tool reads it out of, so the two
# bank windows and the common area cannot drift apart between tools. Bank 0
# sits at file 0x08000, bank 1 at 0x10000, and the common area is file ==
# runtime for its whole extent -- which is what lets a common-area address be
# used as a file offset directly below.
sys.path.insert(0, HERE)
from trace_xdata_refs import REGIONS  # noqa: E402

COMMON = next(r for r in REGIONS if r[0] == "common")
BANK0 = next(r for r in REGIONS if r[0] == "bank0")

COLUMNS = ["table", "run", "index", "address", "opcode", "target", "via",
           "bank"]

# The two bank-select stubs, and which bank each one selects. 0x1100/0x1114
# are the addresses `find_banks.py` reports and the two every `mov dptr,#X;
# ljmp 0x11xx` in the common area resolves to; 2 and 3 (the stubs for banks 2
# and 3) are absent from this image and the tool says so rather than inventing
# a mapping for them.
SELECT_STUBS = {0x1100: "bank0", 0x1114: "bank1"}

# The slot chain. These are the addresses `docs/findings/
# charge-target-caller-chain.md` walks, and the numbers `--self-test` asserts
# them against; they live in one place so the write-up, the chain printer and
# the self-test cannot quote three different values. The two hops past the stub
# are not named here: `--self-test` pins their bytes directly, because what
# matters about them is the three-byte instruction and not a name.
CHAIN_TARGET = 0x8539   # bank0: the slot the stub hands DPTR to
CHAIN_STUB = 0x157C     # common: the stub whose immediate is CHAIN_TARGET

# A run shorter than this is a coincidence of bytes, not a table. Four is the
# smallest run in the committed image that `--self-test` asserts on, so the
# floor cannot silently start cutting a real run in half; a shorter run is
# reported as a run, not dropped, and the `--check` row count is what moves.
MIN_RUN = 4

# The two addresses at the top of the chain, and the opcode that finds a case
# table. `switch_case_dispatch` at common 0x7151 is reached by `lcall`, and the
# table it reads is the inline data *after* the call, because the dispatcher
# gets the table's address by popping the return address the call pushed
# (`d0 83 d0 82` at 0x7151). So `lcall 0x7151` is both the anchor and the
# grammar: the table starts three bytes later. Held here rather than as a
# literal in a scan so the address and the byte pattern cannot drift apart.
SWITCH_DISPATCH = 0x7151
SWITCH_CALL = bytes([0x12, SWITCH_DISPATCH >> 8, SWITCH_DISPATCH & 0xFF])
# The case value the chain's top is selected by. This is a fact about the
# committed table, asserted in `--self-test` and not inferred from anything
# here; it is named so the chain printer and the write-up quote one number.
CHAIN_CASE = 0x0A


def stub_entries(d):
    """Every `90 hi lo 02 11 xx` in the common area, as a run.

    Returns `(base, entries)`, where each entry is
    `(address, target, select_stub, bank)`. One run: a break in the pattern
    ends the table, and a second run of the same shape would be reported as a
    new table rather than appended, because appending across a gap is how a
    scan walks off the end of a table into the code after it.
    """
    lo, hi = COMMON[1], COMMON[2]
    base = None
    entries = []
    at = None
    for o in range(lo, hi):
        if at is not None and o < at:
            continue
        if d[o] == 0x90 and d[o + 3] == 0x02 and d[o + 4] == 0x11:
            at = o + 6
            if base is None:
                base = o
            entries.append((o, (d[o + 1] << 8) | d[o + 2], 0x1100 + d[o + 5],
                            SELECT_STUBS.get(0x1100 + d[o + 5], "?")))
        else:
            at = None
            if base is not None:
                break
    return base, entries


def transfer_run(d, at):
    """Length in entries of the stride-3 transfer run starting at `at`, or 0.

    A run ends at the first byte that is not the start of a 3-byte absolute
    transfer, which is the definition and not a heuristic: every entry is
    exactly 3 bytes, so the next entry's address is fully determined by the
    last one and there is nothing to infer.
    """
    lo, hi = BANK0[1], BANK0[2]
    n = 0
    while at + 2 < hi and is_transfer(d, at + 3 * n):
        n += 1
    return n


def is_transfer(d, at):
    """True if a 3-byte absolute transfer starts at `at`.

    `02 93` is `ljmp @a+dptr` and is two bytes, so it is excluded here rather
    than read as an `ljmp` to `0x??93` -- the mistake would insert a bogus
    entry and, worse, a bogus *target* into the committed CSV.
    """
    if d[at] == 0x12:
        return True
    return d[at] == 0x02 and d[at + 1] != 0x93


def transfer_runs(d, minimum=MIN_RUN):
    """Every stride-3 transfer run in bank 0 of at least `minimum` entries,
    as `(base, [(address, mnemonic, target), ...])`."""
    lo, hi = BANK0[1], BANK0[2]
    runs = []
    at = None
    for o in range(lo, hi):
        if at is not None and o < at:
            continue
        if is_transfer(d, o):
            n = transfer_run(d, o)
            if n >= minimum:
                rows = []
                for k in range(n):
                    a = o + 3 * k
                    rows.append((a, "lcall" if d[a] == 0x12 else "ljmp",
                                 (d[a + 1] << 8) | d[a + 2]))
            else:
                # A short run still consumes its bytes, so a six-entry run
                # whose first four entries happen to open a longer one is not
                # reported twice. It is not *in* the table either: the
                # `minimum` floor is what `--check` pins the row count to.
                at = o + 3 * n
                continue
            at = o + 3 * n
            runs.append((o, rows))
        else:
            at = None
    return runs


def switch_case_tables(d):
    """Every inline case table the `switch_case_dispatch` call sites carry, as
    `(call_site, [(address, case), ...])`.

    The walk stops at the first triple whose address is 0x0000, which is the
    dispatcher's own test -- the `jnz` of the movc/jnz pair at 0x7157-0x7158
    and 0x715C-0x715D -- and not a shape this file invents:
    an address of zero is what tells `0x7151` it has run past the end, and it
    then takes the *next* triple's address as a default arm. Reading a fixed
    number of triples instead would put whatever follows the table into the
    committed CSV.
    """
    lo, hi = COMMON[1], COMMON[2]
    tables = []
    at = None
    for o in range(lo, hi - 2):
        if at is not None and o < at:
            continue
        if d[o:o + 3] == SWITCH_CALL:
            entries = []
            p = o + 3
            while p + 2 < hi:
                addr = (d[p] << 8) | d[p + 1]
                if addr == 0:
                    break
                entries.append((addr, d[p + 2]))
                p += 3
            at = p
            tables.append((o, entries))
        else:
            at = None
    return tables


def rows(d):
    """The two tables as CSV rows, in the committed order."""
    out = []
    base, entries = stub_entries(d)
    for i, (addr, target, via, bank) in enumerate(entries):
        out.append({"table": "far-call-stub", "run": f"0x{base:04X}",
                    "index": i, "address": f"0x{addr:04X}", "opcode": "ljmp",
                    "target": f"0x{target:04X}", "via": f"0x{via:04X}",
                    "bank": bank})
    for base, entries in transfer_runs(d):
        for i, (addr, mnemonic, target) in enumerate(entries):
            out.append({"table": "bank0-transfer-run", "run": f"0x{base:04X}",
                        "index": i, "address": f"0x{addr:04X}",
                        "opcode": mnemonic, "target": f"0x{target:04X}",
                        "via": "", "bank": "bank0"})
    for site, entries in switch_case_tables(d):
        for i, (addr, case) in enumerate(entries):
            out.append({"table": "switch-case", "run": f"0x{site:04X}",
                        "index": i, "address": f"0x{addr:04X}",
                        "opcode": f"case 0x{case:02X}", "target": "",
                        "via": f"0x{SWITCH_DISPATCH:04X}", "bank": "common"})
    return out


class _Sink:
    """csv needs a file-like; a list of lines is the byte-for-byte comparison
    `--check` wants, and a temp file is not worth it for 698 rows."""

    def __init__(self, sink):
        self._sink = sink

    def write(self, text):
        self._sink.append(text)


def render(table):
    buf = []
    w = csv.DictWriter(_Sink(buf), fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(table)
    return "".join(buf)


def diff_table(have, want):
    """Lines describing a row-level difference between the committed table
    `have` and the recomputed `want`. Empty when every row parses equal, which
    is **not** the same as identical; the byte comparison is the pass
    condition and it lives in `check_table()`.

    A function rather than an inline block in `main()` so `self_test()` can
    drive the *same* comparison the gate runs.
    """
    have_rows = list(csv.DictReader(have.splitlines()))
    want_rows = list(csv.DictReader(want.splitlines()))
    lines = []
    for a, b in zip(have_rows, want_rows):
        if a != b:
            lines.append(f"  {a['table']} {a['run']}/{a['index']}:")
            for k in COLUMNS:
                if a.get(k) != b.get(k):
                    lines.append("    %-8s committed %r, recomputed %r"
                                 % (k, a.get(k), b.get(k)))
    if len(have_rows) != len(want_rows):
        lines.append("  row count: committed %d, recomputed %d"
                     % (len(have_rows), len(want_rows)))
    return lines


def check_table(have, want):
    """`(exit_code, lines)`: what `--check` returns, and the lines it prints
    on the way there. Byte equality is the pass condition and it is the only
    one -- a table whose rows read the same while its bytes do not is a table
    this tool did not write (CRLF from a checkout, a trailing blank line,
    reordered columns).

    `.gitattributes` now marks `ec/annotations/task-call-table.csv`
    `text eol=lf`, which covers the committed table's own bytes. Two things
    that attribute does not reach, both worth stating rather than leaving to be
    discovered: this tool's `--check` is not in `agent-gates.sh`, so the
    hazard it guards was latent rather than gate-reachable, and its `--write`
    opens `CSV_PATH` without `newline=""` where the three `check_table`
    siblings do -- so on Windows it *produces* CRLF, and `-text` or `eol=lf`
    on the read side cannot address that. The writer is the remaining gap, and
    it belongs with the other tools' `lineterminator` work rather than here.

    `lines` is never empty when the code is 1, so a failure always says
    something.
    """
    if have == want:
        return 0, []
    lines = diff_table(have, want)
    if not lines:
        lines = ["  bytes differ and every row parses equal: line endings, a "
                 "trailing blank line, column order or quoting differ from "
                 "what this tool writes"]
    return 1, lines


def find_callers(d, target):
    """File offsets of every `lcall`/`ljmp` naming `target`, over the whole
    image. Unaligned, so a hit inside a data table reads as a call; that is
    the same over-count `../annotations/bank-call-audit.md` 1 measures, and
    `--self-test` pins the 0xB158 pair to zero rather than to a guess."""
    pat = bytes([0x12, target >> 8, target & 0xFF])
    alt = bytes([0x02, target >> 8, target & 0xFF])
    return sorted(i for i in range(len(d) - 2)
                  if d[i:i + 3] == pat or d[i:i + 3] == alt)


def chain(d, target=CHAIN_TARGET):
    """The hops from the scheduler's case table down to a bank-0 slot, as
    `(label, detail)` pairs, plus the runs the slot sits in.

    Stops where the bytes stop. The top hop is the *selected* one, so a case
    value that no table carries is reported as absent rather than guessed at:
    the answer would be a different slot, not this chain.
    """
    hops = []
    sites = switch_case_tables(d)
    hit = [(s, e) for s, entries in sites for e in entries if e[1] == CHAIN_CASE]
    if not hit:
        return hops, []
    site, (case_addr, _) = hit[0]
    hops.append((f"case 0x{CHAIN_CASE:02X} of the inline table at "
                 f"0x{site + 3:04X} (the `lcall 0x{SWITCH_DISPATCH:04X}` at "
                 f"0x{site:04X} pushes its own address)",
                 f"selects 0x{case_addr:04X} -> ljmp 0x0E55"))

    base, entries = stub_entries(d)
    stub = [e for e in entries if e[1] == target]
    if not stub:
        return hops, []
    addr, tgt, via, bank = stub[0]
    hops.append((f"stub common 0x{addr:04X} (index {(addr - base) // 6} of "
                 f"the table at 0x{base:04X})",
                 f"mov dptr,#0x{tgt:04X}; ljmp 0x{via:04X} -> {bank}"))
    # Matched on the stub's *immediate*, not on the stub's own address: the
    # stub sits in the common area and the run it hands DPTR to sits in bank 0,
    # so the two are not comparable addresses and matching on the wrong one
    # finds no run and reports a broken chain instead of an absent one.
    runs = [r for r in transfer_runs(d) if r[0] <= tgt < r[0] + 3 * len(r[1])]
    if runs:
        rbase, entries_r = runs[0]
        i = (tgt - rbase) // 3
        hops.append((f"slot {bank} 0x{tgt:04X} (index {i} of {len(entries_r)} "
                     f"in the run at 0x{rbase:04X})",
                     f"{entries_r[i][1]} 0x{entries_r[i][2]:04X}"))
    return hops, runs


def report(d) -> int:
    base, entries = stub_entries(d)
    banks = {}
    for _a, _t, via, bank in entries:
        banks[bank] = banks.get(bank, 0) + 1
    print(f"far-call stub table: {len(entries)} entries at common "
          f"0x{base:04X}, stride 6")
    for bank, n in sorted(banks.items()):
        print(f"  {bank}: {n} entries select it "
              f"(ljmp 0x{[k for k, v in SELECT_STUBS.items() if v == bank][0]:04X})")
    low = [e for e in entries if e[1] < 0x8000]
    print(f"  {len(entries) - len(low)} of {len(entries)} immediates are "
          f"banked-window addresses (>= 0x8000)")
    if low:
        print(f"  ! {len(low)} below 0x8000, so the run has left the table: "
              f"{[hex(e[0]) for e in low[:8]]}")

    runs = transfer_runs(d)
    n_entries = sum(len(e) for _b, e in runs)
    print(f"\nbank0 stride-3 transfer runs (>= {MIN_RUN} entries): "
          f"{len(runs)} runs, {n_entries} entries")
    for rbase, entries_r in sorted(runs, key=lambda r: -len(r[1]))[:5]:
        print(f"  0x{rbase:04X}-0x{rbase + 3 * len(entries_r):04X}  "
              f"{len(entries_r)} entries")
    print(f"  ({len(runs) - 5} further runs not shown; --write the table for all)")

    tables = switch_case_tables(d)
    n_cases = sum(len(e) for _s, e in tables)
    print(f"\nswitch case tables behind the `lcall 0x{SWITCH_DISPATCH:04X}` call "
          f"sites in common: {len(tables)} tables, {n_cases} cases")
    for site, entries in tables:
        cases = [c for _a, c in entries]
        print(f"  0x{site:04X}  {len(entries):2d} cases, "
              f"0x{cases[0]:02X}..0x{cases[-1]:02X}")

    hops, runs = chain(d)
    print("\nchain:")
    for label, detail in hops:
        print(f"  {label}\n    {detail}")
    return 0


def search(d) -> int:
    """The scans behind the write-up's methods table. Each line states its
    region, because 'not found by this method' is a claim about a method over
    a region and reading it as 'absent' is the error CLAUDE.md warns about."""
    for target, what in ((0xB158, "the charge-target routine: a direct caller "
                                 "would be an lcall/ljmp naming it"),
                         (0xB12C, "the routine that branches into it"),
                         (CHAIN_STUB, "the far-call stub carrying the chain")):
        hits = find_callers(d, target)
        sites = ", ".join(f"0x{h:05X}" for h in hits) or "none"
        print(f"lcall/ljmp 0x{target:04X} ({what}), unaligned byte scan over "
              f"the whole 0x{len(d):05X}-byte image: "
              f"{len(hits)} hit{'' if len(hits) == 1 else 's'} ({sites})")

    lo, hi = 0x0D00, 0x1000
    hits = [o for o in range(lo, hi) if d[o] == 0x73]
    sites = ", ".join(f"0x{o:05X}" for o in hits) or "none"
    print(f"\njmp @a+dptr (0x73) in common 0x{lo:04X}-0x{hi - 1:04X}, the "
          f"issue's code-pointer-table candidate: {len(hits)} hits ({sites})")
    # The issue's scan was bounded, so the bound is reported rather than
    # dropped -- but the count is over the whole common area, not the
    # scanned window, so a reader can see the window is a strict subset.
    clo, chi = COMMON[1], COMMON[2]
    wide = [o for o in range(clo, chi) if d[o] == 0x73]
    print(f"  for scale, the whole common area 0x{clo:04X}-0x{chi - 1:04X} "
          f"contains {len(wide)}: "
          f"{', '.join(f'0x{o:04X}' for o in wide)}")
    print("  the dispatcher that *does* read a jump table is common 0x7151, "
          "switch_case_dispatch, outside this region")
    return 0


def self_test(fw_path: str) -> int:
    d = open(fw_path, "rb").read()
    bad = 0

    def check(label, cond):
        nonlocal bad
        if not cond:
            bad += 1
        print(f"  {'ok ' if cond else '!  '} {label}")

    print("known answers, from the committed image\n")
    base, entries = stub_entries(d)
    check(f"the far-call stub table is one run at common 0x{base:04X} "
          f"({len(entries)} entries)", base == 0x1150 and len(entries) == 403)

    i = (0x157C - base) // 6
    check(f"0x157C is index {i} and is `90 85 39 02 11 00`",
          d[0x157C:0x1582] == bytes.fromhex("90 85 39 02 11 00") and i == 178)

    banks = {}
    for _a, _t, _via, bank in entries:
        banks[bank] = banks.get(bank, 0) + 1
    check(f"select-stub split is bank0=350 / bank1=53 (got {banks})",
          banks == {"bank0": 350, "bank1": 53})
    check("every immediate is a banked-window address",
          all(e[1] >= 0x8000 for e in entries))

    runs = {r[0]: r[1] for r in transfer_runs(d)}
    check("the bank0 run holding 0x8539 starts at 0x8518 with 22 entries",
          0x8518 in runs and len(runs[0x8518]) == 22)
    check("0x8539 is index 11 in it, 0x853F is index 13",
          (0x8539 - 0x8518) // 3 == 11 and (0x853F - 0x8518) // 3 == 13)
    check("0x84EB and 0x8502 are separate runs, not the same one",
          0x84EB in runs and 0x8502 in runs and 0x8518 in runs)
    check(f"0x853F is `12 b1 2c` and 0x8539 is `12 e0 10`",
          d[0x853F:0x8542] == bytes.fromhex("12 b1 2c")
          and d[0x8539:0x853C] == bytes.fromhex("12 e0 10"))
    check("0xB12C branches into 0xB158 on 0x0490 bit 1 (`20 e1 10` at 0xB145)",
          d[0xB145:0xB148] == bytes.fromhex("20 e1 10")
          and 0xB145 + 3 + 0x10 == 0xB158)
    check("0xB148 zeroes 0x09C7 (the else arm)",
          d[0xB148:0xB14D] == bytes.fromhex("e4 90 09 c7 f0"))

    hops, runs = chain(d)
    check("the chain resolves CHAIN_CASE to 0x0DFE, then the stub at 0x157C, "
          "then the 0x8518 run",
          len(hops) == 3 and "0x0DFE" in "".join(hops[0])
          and "0x157C" in hops[1][0] and "0x8518" in hops[2][0])

    tables = switch_case_tables(d)
    chain_table = [e for _s, e in tables if any(c == CHAIN_CASE for _a, c in e)]
    check(f"one case table carries case 0x{CHAIN_CASE:02X}, at the 0x0D7B "
          f"scheduler ({len(tables)} tables in the common area)",
          len(chain_table) == 1 and len(tables) == 4)
    check("its case 0x0A entry is `0d fe 0a` -- 0x0DFE, which is `02 0e 55`",
          d[0x0DE2:0x0DE5] == bytes.fromhex("0d fe 0a")
          and d[0x0DFE:0x0E01] == bytes.fromhex("02 0e 55"))
    check("the table ends at a 0x0000 address, the dispatcher's own test",
          d[0x0DF1:0x0DF4] == bytes.fromhex("00 00 0e"))
    check("an address no stub names gets the case hop and no stub hop, "
          "rather than a guessed second one",
          len(chain(d, 0xB158)[0]) == 1)

    print("\nthe negative results the issue asked to have recorded\n")
    check("no lcall/ljmp names 0xB158 anywhere in the image",
          find_callers(d, 0xB158) == [])
    check("`12 b1 2c` has exactly one hit, at file 0x853F",
          find_callers(d, 0xB12C) == [0x853F])
    check("no jmp @a+dptr in common 0x0D00-0x0FFF",
          [o for o in range(0x0D00, 0x1000) if d[o] == 0x73] == [])
    check("`02 93` is not read as an ljmp",
          not is_transfer(d, next(o for o in range(0x8000, 0x10000)
                                  if d[o:o + 2] == b"\x02\x93")))

    print("\nrefusals: --check must still reject a table that drifted\n")
    good = render(rows(d))
    rc, _ = check_table(good, good)
    check("an unchanged table passes", rc == 0)

    table = rows(d)
    table[0]["target"] = "0xDEAD"
    rc, lines = check_table(good, render(table))
    check(f"a mutated cell fails and names the cell ({len(lines)} lines)",
          rc == 1 and any("target" in ln for ln in lines))

    table = rows(d)
    table.append(dict(table[0]))
    rc, lines = check_table(good, render(table))
    check("an added row fails on the row count",
          rc == 1 and any("row count" in ln for ln in lines))

    rc, lines = check_table(good + "\n", good)
    check("byte drift with every row parsing equal still fails, and says so",
          rc == 1 and lines and "line endings" in lines[0])

    print()
    if bad:
        print(f"self-test FAILED: {bad} assertion(s)")
        return 1
    print("self-test passed: the tables, the chain, the negative results, and "
          "the check's refusals")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help=f"raw EC firmware image (default {DEFAULT_FIRMWARE}, "
                         "relative to the repository root)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="recompute the table and fail on any diff")
    mode.add_argument("--self-test", action="store_true",
                      help="known answers and refusals against the committed image")
    mode.add_argument("--chain", action="store_true",
                      help="print the chain's hops and the runs around them")
    mode.add_argument("--search", action="store_true",
                      help="the scans behind the write-up's methods table")
    mode.add_argument("--write", action="store_true",
                      help="write ec/annotations/task-call-table.csv")
    args = ap.parse_args()

    # The default is repository-relative, so this resolves from the repo root
    # and not from wherever the tool happens to be invoked -- the same reason
    # disasm8051.py's self-test resolves its sibling module off __file__.
    path = args.firmware if os.path.isabs(args.firmware) \
        else os.path.join(REPO, args.firmware)
    if not os.path.isfile(path):
        ap.error(f"no firmware image at {args.firmware}")
    d = open(path, "rb").read()

    if args.self_test:
        return self_test(path)
    if args.check:
        table = render(rows(d))
        with open(CSV_PATH) as f:
            have = f.read()
        rc, lines = check_table(have, table)
        print(f"{os.path.relpath(CSV_PATH, REPO)}: {len(rows(d))} rows "
              f"recomputed from {os.path.basename(path)}")
        for line in lines:
            print(line)
        print("task-call-table.csv: unchanged" if rc == 0
              else "task-call-table.csv: FAILED")
        return rc
    if args.write:
        table = render(rows(d))
        with open(CSV_PATH, "w") as f:
            f.write(table)
        print(f"wrote {os.path.relpath(CSV_PATH, REPO)}: {len(rows(d))} rows")
        return 0
    if args.chain:
        hops, runs = chain(d)
        for label, detail in hops:
            print(f"{label}\n  {detail}")
        print(f"\nruns touching the chain's slot:")
        for rbase, entries in runs:
            print(f"  0x{rbase:04X}-0x{rbase + 3 * len(entries):04X}  "
                  f"{len(entries)} entries")
        return 0
    if args.search:
        return search(d)
    return report(d)


if __name__ == "__main__":
    sys.exit(main())
