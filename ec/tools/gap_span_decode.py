#!/usr/bin/env python3
"""Name the bytes a census site owns by decoding *across* a committed gap.

`docs/findings/counter-sweep-entry-set.md` §3 classifies the `bank1` census
sites that target into `bank1:0x8001`-`0x8189` against the instruction starts
parsed out of the committed `.asm` listings, and for all but two of them that
works because a listing **names** the instruction owning the site byte. The
remaining two, `bank1:0x81E7` and `bank1:0xA6DC`, sit in a committed gap --
120 and 123 bytes no listing covers -- so the cross-check has nothing to
cross-check against. That is a *different kind* of "not found by this method"
from an identified operand byte, and §3 kept the two apart for that reason.

This is the other method. Ghidra exported one function per `.asm` and stopped
where the function stopped, so a gap is a boundary of the *listing set*, not a
hole in the byte stream: the image still has an instruction there. The way to
find it is to walk forward from the last committed instruction start before the
gap with `disasm8051.decode()` -- the same stepping rule `converges_from()`
walks, so the two cannot drift -- until the walk covers the site.

**A decode is a weaker class of evidence than a listing, and is named as such
wherever it is used** (`counter_sweep_entry.py` records a `gap-decode`
provenance beside these two and nothing else). Two witnesses sit beside the
decode, and **only the first discriminates**:

- **the row's own `earlier_record` cell**, a transcription of the owning
  instruction's bytes made by `audit_call_targets.py` from the image. This one
  agrees on the address *and* the bytes, which is what lets the tool check
  itself against something that is not its own output, and it is the witness
  both sites are re-grounded on -- for `0x81E7`, the only one there is;
- **`converges_from()` at the site**, which must equal the
  `frame_onto`/`frame_over` `bank-call-targets.csv` already records for that
  row -- a score computed by a different producer, and here corroboration
  rather than a new claim. It settles nothing on its own
  (`../annotations/bank-call-audit.md` 1), and at `0x81E7` it reads 0 of 24, so
  there it corroborates nothing at all.

**The re-entry check is reported, and carries no weight.** All 24 anchors land
exactly on the first byte the next listing covers, at both sites -- and so does
the same walk over *every other* unlisted stretch in `bank1` of the two sites'
own size, and over two fillings in three whose gap bytes have all been replaced
with random ones (`--reentry-calibration`). 24 of 24 is what this metric
returns on this image; it describes the walk, not these bytes. Whether the
anchors are themselves framed code is asked separately, per site, because the
answer differs between them: 24 of 24 at `0x81E7`, 15 of 24 at `0xA6DC`, whose
nine lowest anchors sit in a second unlisted stretch of their own.

**What this is not.** `disasm8051.py`'s own docstring is the standing limit and
it applies here verbatim: a linear walk is "evidence about framing, not proof
of it", and this walk is linear. It reads no dispatch table, follows no branch
and recovers no function boundary, so a gap that begins in the middle of a data
structure would decode exactly as convincingly as one that begins at an
instruction end. `docs/findings/bank1-e582-entry-framing.md` is the prior
decode-across-a-listing-cut case; it reaches a comparable conclusion by a
different byte argument and carries the same limit beside it.

**One method, not two, so the tool refuses an address a listing covers.**
Running this against an already-classified site and reading its answer as a
second opinion is the mistake both `converges_from`'s docstring and
`../annotations/bank-call-audit.md` §1 argue against, so an `--at` inside a
committed listing is an error rather than a second verdict.

`--at` is a **runtime address**, not a file offset -- the trap
`counter_sweep_entry.py --self-test` spends two checks on, and the one every
`bank1` address has: file `0x101E7` is runtime `0x81E7`.

With no `--at` the report covers `PINNED`, the two sites this finding is
about; passing `--at` reports on that one instead, and a third gap site is an
argument away. Enumerating every gap site tree-wide is a different and larger
census, and this tool deliberately does not run it.

Usage:
    python3 gap_span_decode.py --at 0x81E7 --region bank1
    python3 gap_span_decode.py --reentry-calibration
    python3 gap_span_decode.py --csv
    python3 gap_span_decode.py --self-test
"""
import argparse
import bisect
import csv
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# `read_listings`/`owner_of` are the census tool's own, imported rather than
# re-derived: a second listing parser is a second answer to "which bytes does a
# committed `.asm` name", and the two would drift silently. The dependency runs
# this way round only -- `counter_sweep_entry` reaches *this* module from
# inside `site_shape()`, by which time it is fully loaded, so the pair is
# acyclic at load time as well as at call time. Running `counter_sweep_entry.py`
# as `__main__` gives this a second copy of it under its own name; the two hold
# no state and the functions used here are pure, so the copy is a duplicate
# module and not a second answer.
from counter_sweep_entry import (CENSUS_CSV, FIRMWARE, owner_of,  # noqa: E402
                                 read_listings)
from disasm8051 import (OPCODE_LEN, converges_from, decode,  # noqa: E402
                        inline_arg_len)
from trace_xdata_refs import offset_for_runtime, runtime_addr  # noqa: E402

# Both pinned sites are `bank1`, and `--region` is the argument that makes a
# third program an option rather than an edit. It is checked rather than
# assumed: `--at` is resolved through `offset_for_runtime()` against the
# caller's own bank, so naming the wrong one lands somewhere else in the image
# and the refusal below says which.
DEFAULT_REGION = "bank1"

# The same `back` `converges_from()` uses, so the re-entry count and the
# census's frame score are over the same 24 anchors and a reader is not
# comparing a 24 against a 24 by coincidence.
ANCHORS = 24


def step(d: bytes, i: int) -> int:
    """The next instruction start after `d[i]`.

    This is `decode()`'s and `converges_from()`'s stepping rule, written out
    once here because the re-entry walk is neither of them: it has to carry on
    past the left anchor, which is the one point both of those stop at. The
    expression is copied rather than imported for that reason, and the
    self-test pins what it produces -- if the rule ever moves, the 24/24 below
    is a red run rather than a quietly different number."""
    return i + OPCODE_LEN[d[i]] + inline_arg_len(d, i)


def squeeze(text: str) -> str:
    """`mnemonic()`'s column padding removed.

    `audit_call_targets.earlier_record()` writes its cell the same way, for
    the same reason -- the padding is a rendering choice and the cell is the
    instruction rather than the layout -- and the two being identical is what
    makes the cell checkable against the decode below."""
    return " ".join(text.split())


def reentry(d: bytes, anchor_off: int, hi_off: int, back: int = ANCHORS) -> tuple:
    """(onto, total) for the re-entry check: of the `back` byte anchors ending
    at `anchor_off`, how many decode across the whole gap and land *exactly*
    on `hi_off`.

    **A measured figure, not a witness.** It was written up as one -- the
    argument being that a framing invented by a byte scan inside an unframed
    stretch could not cross the whole of it and come out aligned from 24
    starting points -- and `reentry_calibration()` is what refutes that
    argument: the same walk reads 24 of 24 on every other unlisted stretch in
    `bank1` of the two sites' own size, and still reads 24 of 24 after every
    byte inside either gap has been replaced with random ones. What is left
    is that the walk is self-consistent across the stretch, which is a fact
    about `step()` rather than about the bytes it was pointed at.

    Whether the anchors are themselves bytes a listing frames is
    `anchor_coverage()`'s question, asked separately because the two sites
    answer it differently."""
    onto = total = 0
    for b in range(1, back + 1):
        i = anchor_off - b
        if i < 0:
            continue
        total += 1
        while i < hi_off:
            i = step(d, i)
        if i == hi_off:
            onto += 1
    return onto, total


def anchor_coverage(anchor: int, starts, listings,
                    back: int = ANCHORS) -> tuple:
    """(covered, total) for the `back` byte anchors `reentry()` starts from:
    how many of them a committed listing actually covers.

    Measured rather than assumed, because the assumption does not hold
    everywhere. The anchors are outside the gap by construction -- they end at
    the left anchor -- but "outside the gap" is not the same as "framed", and
    a site's own gap can have another one immediately below it. At `0x81E7`
    all 24 are covered; at `0xA6DC` nine of them (`0xA6BC`-`0xA6C4`) sit in a
    second unlisted stretch no listing covers either, so nine of the 24
    starting points `reentry()` walks from are themselves unframed bytes here.

    This is the premise that made 24 independent starting points worth
    anything, and it is worth 15 rather than 24 at a site where it fails."""
    covered = 0
    for b in range(1, back + 1):
        a = anchor - b
        if a < 0:
            continue
        if owner_of(a, starts, listings)[0] is not None:
            covered += 1
    return covered, back


# The anchor-to-next-listing distances of the two pinned sites are 121 and 124
# bytes, so the control is drawn from a band wide enough to hold both and
# narrow enough to keep the geometry the same: an unlisted stretch of about a
# hundred bytes between two committed listings, walked from the last listing
# start below it.
REENTRY_SPAN = (100, 145)

# How many random fillings the perturbation arm of the calibration uses. Fixed
# so the figure is a measurement of the walk rather than of the run, and seeded
# from the site address so two sites do not share a filling.
PERTURB_FILLINGS = 300


def reentry_calibration(d: bytes, starts, listings, region: str,
                        exclude=()) -> dict:
    """The re-entry metric's base rate in `region`, and the perturbation that
    shows the metric is insensitive: `{"control", "rows", "perturb"}`.

    *Control.* Every unlisted stretch between two consecutive listing runs whose
    anchor-to-next-listing distance falls in `REENTRY_SPAN`, walked exactly as
    `reentry()` walks a site and with `exclude` left out. This is the same
    geometry at stretches the tool is not being asked to settle, so a 24 of 24
    here means a 24 of 24 at a site is what the metric does rather than what
    the image says.

    *Perturbation.* Each excluded site's own endpoints, with every byte inside
    the gap replaced by a deterministic pseudo-random byte, walked
    `PERTURB_FILLINGS` times. If the check noticed the region it is meant to be
    validating, a gap of noise would stop it coming out aligned; the count of
    fillings that still read 24 of 24 is how little it notices. The image is
    copied per site and the gap restored afterwards, so the committed bytes are
    never written to."""
    pairs, full, rows = 0, 0, []
    for i, lo in enumerate(starts[:-1]):
        nxt = starts[i + 1]
        gap_lo = lo + len(listings[lo][0])
        if nxt == gap_lo:
            continue                      # a contiguous run is not a stretch
        if not REENTRY_SPAN[0] <= nxt - lo <= REENTRY_SPAN[1]:
            continue
        # A stretch holding one of the sites is not a control for it, however
        # little the metric distinguishes: the exclusion is by containment,
        # so it holds whichever way the site sits relative to the anchor.
        if any(gap_lo <= s < nxt for s in exclude):
            continue
        lo_off = offset_for_runtime(lo, region)
        hi_off = offset_for_runtime(nxt, region)
        if lo_off is None or hi_off is None:
            continue
        onto, over = reentry(d, lo_off, hi_off)
        pairs += 1
        full += onto == over
        cov = anchor_coverage(lo, starts, listings)
        rows.append({"anchor": lo, "gap_lo": gap_lo,
                     "hi": nxt, "stretch": nxt - lo,
                     "onto": onto, "over": over, "covered": cov[0],
                     "cov_total": cov[1]})

    perturb = {}
    for site in exclude:
        w = next((p for p in PINNED if p["site"] == site), None)
        if w is None:
            continue
        lo_off = offset_for_runtime(w["gap_lo"], region)
        hi_off = offset_for_runtime(w["gap_hi"], region)
        anchor_off = offset_for_runtime(w["anchor"], region)
        if None in (lo_off, hi_off, anchor_off):
            continue
        real = bytes(d[lo_off:hi_off])
        img = bytearray(d)
        rng = random.Random(site)
        still = 0
        for _ in range(PERTURB_FILLINGS):
            for k in range(lo_off, hi_off):
                img[k] = rng.randrange(256)
            onto, over = reentry(bytes(img), anchor_off, hi_off)
            still += onto == over
        img[lo_off:hi_off] = real
        perturb[site] = (still, PERTURB_FILLINGS)
    return {"control": (full, pairs), "rows": rows, "perturb": perturb}


def decode_site(d: bytes, addr: int, region: str, starts, listings,
                census=None, calibration=None) -> dict:
    """Measure the gap `addr` sits in and the instruction that owns it, or
    None when the committed listings already cover `addr`.

    None is the refusal, and it is deliberate: this tool answers only for
    bytes no listing names, so a covered address has no gap to decode across
    and `counter_sweep_entry.py` has already classified it from the listing
    itself. Returning an answer there would be a second opinion on a settled
    row, which is the one thing a second method is not allowed to be.

    A site the walk reaches past without covering is also None -- the framing
    did not survive the gap -- and `counter_sweep_entry.py` keeps such a row in
    its `gap` bucket, which is where it belongs."""
    if owner_of(addr, starts, listings)[0] is not None:
        return None

    site_off = offset_for_runtime(addr, region)
    if site_off is None:
        return None

    # The gap: one past the end of the last committed listing below the site,
    # up to the first committed listing start above it. Both ends are
    # committed bytes, which is what makes the walk between them anchored at
    # both ends rather than at one.
    below = bisect.bisect_left(starts, addr)
    if below == 0 or below == len(starts):
        return None
    anchor = starts[below - 1]
    lo = anchor + len(listings[anchor][0])
    hi = starts[below]

    anchor_off = offset_for_runtime(anchor, region)
    hi_off = offset_for_runtime(hi, region)
    span = [(off, raw, text) for off, raw, text
            in decode(d, anchor_off, hi_off - anchor_off,
                      runtime_addr(anchor_off, True))
            if off < hi_off]
    owner = next((e for e in span if e[0] <= site_off < e[0] + len(e[1])), None)
    if owner is None:
        return None
    # An `INLINE_ARG_CALLS` argument block would surface here as an
    # `inline args:` line rather than an instruction; the EC image carries no
    # such call (`test_disasm8051_inline_args.py` pins the zero against the
    # PD image's 458), so what is named is always an instruction.
    owner_off, owner_raw, owner_text = owner

    row = census_row(census, region, addr) if census is not None else None
    onto, over = converges_from(d, site_off)
    return {
        "region": region,
        "site": addr,
        "file_offset": site_off,
        "gap_lo": lo,
        "gap_hi": hi,
        "gap_len": hi - lo,
        "anchor": anchor,
        "anchor_text": listings[anchor][1],
        "span": span,
        "owner": runtime_addr(owner_off, True),
        "owner_file_offset": owner_off,
        "owner_bytes": bytes(owner_raw),
        "owner_text": squeeze(owner_text),
        "owner_opcode": owner_raw[0],
        "owner_index": site_off - owner_off,
        "reentry": reentry(d, anchor_off, hi_off),
        "reentry_cov": anchor_coverage(anchor, starts, listings),
        "calibration": calibration,
        "frame": (onto, over),
        "census_opcode": row["opcode"] if row else "",
        "census_target": row["target"] if row else "",
        "census_frame": ((int(row["frame_onto"]), int(row["frame_over"]))
                         if row else None),
        "earlier_record": row["earlier_record"] if row else "",
    }


def census_row(census, region, addr):
    """The one `bank-call-targets.csv` row for a site, or None.

    A site with no census row is a normal outcome, not an error: this tool
    reads a committed image and knows nothing about the census beyond asking it
    about a site, and `--at` takes any address in a gap. What it costs is the
    two corroborating witnesses that come from the row, so the report says
    "no census row" rather than printing an empty cell that reads like a
    silent agreement."""
    for r in census:
        if r["region"] == region and int(r["runtime"], 16) == addr:
            return r
    return None


def load_census():
    with open(CENSUS_CSV, newline="") as f:
        return list(csv.DictReader(f))


def earlier_record_agrees(cell, owner_off, raw, text) -> bool:
    """Whether a census `earlier_record` cell names the decoded owner, on its
    address, on its bytes and on its text.

    Written as a comparison against the cell rather than a re-derivation of it:
    the cell was produced by `audit_call_targets.earlier_record()` from the
    same image, which is a different producer with a different method (a
    candidate record *spanning* the site, scored by `converges_from()` and
    tie-broken by reach). That it lands on the same address and the same three
    bytes is the corroboration; re-deriving it here would assert the tool
    against itself, which is the argument `test_paged_trampoline_framing.py`
    makes for transcribing the table instead of importing it."""
    parts = cell.split()
    if len(parts) < len(raw) + 2 or not parts[0].startswith("0x"):
        return False
    return (int(parts[0], 16) == owner_off
            and " ".join(f"{b:02x}" for b in raw)
            == " ".join(parts[1:len(raw) + 1])
            and squeeze(" ".join(parts[len(raw) + 1:])) == text)


# --------------------------------------------------------------------------
# The two sites
# --------------------------------------------------------------------------

# What the measurement is expected to be, transcribed rather than computed, so
# that `--self-test` is an oracle and not a restatement of this tool's own
# output. `docs/findings/counter-sweep-gap-sites.md` is where each figure is
# read against the bytes; a value here that the image no longer supports is a
# red run, not a corrected line.
PINNED = (
    {
        "region": "bank1", "site": 0x81E7, "file_offset": 0x101E7,
        "gap_lo": 0x818A, "gap_hi": 0x8202, "gap_len": 120,
        "anchor": 0x8189, "anchor_text": "ret",
        "owner": 0x81E6, "owner_bytes": b"\x40\x02",
        "owner_text": "jc 0x81ea", "owner_index": 1,
        "reentry": (24, 24), "reentry_cov": (24, 24), "frame": (0, 24),
        "census_opcode": "ljmp", "census_target": "0x8008",
        "earlier_record": "0x101E6 40 02 jc 0x81ea",
    },
    {
        "region": "bank1", "site": 0xA6DC, "file_offset": 0x126DC,
        "gap_lo": 0xA6D5, "gap_hi": 0xA750, "gap_len": 123,
        "anchor": 0xA6D4, "anchor_text": "ret",
        "owner": 0xA6DA, "owner_bytes": b"\xb5\x04\x02",
        "owner_text": "cjne a,0x04,0xa6df", "owner_index": 2,
        "reentry": (24, 24), "reentry_cov": (15, 24), "frame": (1, 23),
        "census_opcode": "ljmp", "census_target": "0x8017",
        "earlier_record": "0x126DA b5 04 02 cjne a,0x04,0xa6df",
    },
)


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def print_site(m, show_span=True):
    reg, site = m["region"], m["site"]
    print(f"## gap_span_decode: {reg}:0x{site:04X}")
    print()
    print("  census row      "
          + (f"0x{m['file_offset']:05X}  {m['census_opcode']} "
             f"{m['census_target']}  frame {m['frame'][0]}/{sum(m['frame'])}"
             if m["census_opcode"] else "none -- this address is not a "
             "census site, so the two row-borne witnesses are unavailable"))
    print(f"  earlier_record  {m['earlier_record'] or '(empty cell)'}")
    print(f"  committed gap   0x{m['gap_lo']:04X}-0x{m['gap_hi'] - 1:04X}, "
          f"{m['gap_len']} bytes, covered by no listing")
    print(f"  left anchor     0x{m['anchor']:04X}  "
          f"`{m['anchor_text']}`  -- the last committed instruction start "
          "before the gap")
    print(f"  re-entry        {m['reentry'][0]} of {m['reentry'][1]} anchors "
          f"decode across the gap and land exactly on 0x{m['gap_hi']:04X}")
    cov, cal = m.get("reentry_cov"), m.get("calibration")
    print("  re-entry rate   "
          + (f"{cov[0]} of the {cov[1]} anchors are covered by a committed "
             "listing" if cov else "anchor coverage not measured")
          + (f"; the same walk reads {m['reentry'][0]} of {m['reentry'][1]} on "
             f"{cal['control'][0]} of the {cal['control'][1]} other "
             f"{REENTRY_SPAN[0]}-{REENTRY_SPAN[1]}-byte unlisted stretches in "
             f"{reg}" if cal else ""))
    print("  re-entry base   "
          + (f"{cal['perturb'][site][0]} of {cal['perturb'][site][1]} fillings "
             "of this gap with every byte inside it replaced by a random one "
             f"still read {m['reentry'][0]} of {m['reentry'][1]}, so the figure "
             "above is this metric's base rate on this image and not a finding "
             "about these bytes"
             if cal and site in cal["perturb"]
             else "not measured; run --reentry-calibration"))
    print(f"  frame           {m['frame'][0]}/{sum(m['frame'])} here, "
          + (f"{m['census_frame'][0]}/{sum(m['census_frame'])} recorded in "
             "bank-call-targets.csv -- agree"
             if m["census_frame"] else "no census row to compare against"))
    print(f"  owner           0x{m['owner']:04X}  "
          f"`{m['owner_bytes'].hex(' ')}`  {m['owner_text']}")
    print(f"  the site        byte {m['owner_index'] + 1} of "
          f"{len(m['owner_bytes'])} of that instruction")
    if show_span:
        print()
        print(f"  the gap decoded from 0x{m['anchor']:04X} to 0x{m['gap_hi']:04X},"
              " which is the framing the owner above is read in:")
        print()
        for off, raw, text in m["span"]:
            mark = ("   <-- the site, byte %d of %d"
                    % (m["owner_index"] + 1, len(raw))
                    if off == m["owner_file_offset"] else "")
            print(f"    0x{runtime_addr(off, True):04X}  {raw.hex(' '):<9}"
                  f" {squeeze(text)}{mark}")
    print()


def print_calibration(cal, region):
    """The base rate of the re-entry check, on its own.

    This is the report that decides what the 24 of 24 in the site report is
    worth, so it is a first-class output rather than a footnote: the control
    is the same walk over the same geometry somewhere it is not being asked to
    settle, and the perturbation is the same walk over a gap of noise.
    """
    full, pairs = cal["control"]
    print(f"## gap_span_decode: what the re-entry check is worth in {region}")
    print()
    print(f"  **{full} of the {pairs} other {REENTRY_SPAN[0]}-"
          f"{REENTRY_SPAN[1]}-byte unlisted stretches** in {region}, walked "
          f"exactly as a site is walked and with the {ANCHORS} anchors starting "
          "at the listing run below each one, read "
          f"{ANCHORS} of {ANCHORS} as well:")
    print()
    print("  | anchor | unlisted stretch | stretch | anchors a listing covers "
          "| re-entry |")
    print("  |---|---|---:|---:|---:|")
    for r in cal["rows"]:
        print(f"  | `0x{r['anchor']:04X}` | "
              f"`0x{r['gap_lo']:04X}-0x{r['hi'] - 1:04X}` | {r['stretch']} "
              f"| {r['covered']}/{r['cov_total']} | "
              f"{r['onto']}/{r['over']} |")
    print()
    print("  And the walk barely notices that the region it is validating is "
          "nonsense: with each site's own endpoints kept and **every byte "
          "inside the gap replaced by a random one**, it still reads "
          f"{ANCHORS} of {ANCHORS} in")
    print()
    print("  | site | fillings still reading 24 of 24 |")
    print("  |---|---:|")
    for site, (still, fills) in sorted(cal["perturb"].items()):
        print(f"  | `{region}:0x{site:04X}` | {still} of {fills} |")
    print()
    print("  A framing invented by a byte scan inside an unframed stretch was "
          "never going to cross the whole of it and come out aligned from 24 "
          "starting points. It does, about two fillings in three of pure "
          "noise, and it does on every stretch of this size that this tool is "
          "not being asked about. The 24 of 24 at a site is what this metric "
          "returns on this image.")
    print()


CSV_COLUMNS = ("region", "site", "file_offset", "gap_lo", "gap_hi", "gap_len",
               "anchor", "owner", "owner_bytes", "owner_text", "owner_index",
               "reentry", "reentry_total", "reentry_cov", "reentry_cov_total",
               "reentry_base_full", "reentry_base_pairs",
               "reentry_perturb_full", "reentry_perturb_fills",
               "frame_onto", "frame_over",
               "census_opcode", "census_target", "earlier_record")


def write_csv(rows):
    w = csv.writer(sys.stdout)
    w.writerow(CSV_COLUMNS)
    for m in rows:
        cal = m.get("calibration") or {}
        pert = cal.get("perturb", {}).get(m["site"], ("", ""))
        cov = m.get("reentry_cov") or ("", "")
        w.writerow([
            m["region"], f"0x{m['site']:04X}", f"0x{m['file_offset']:05X}",
            f"0x{m['gap_lo']:04X}", f"0x{m['gap_hi']:04X}", m["gap_len"],
            f"0x{m['anchor']:04X}", f"0x{m['owner']:04X}",
            m["owner_bytes"].hex(" "), m["owner_text"], m["owner_index"],
            m["reentry"][0], m["reentry"][1], cov[0], cov[1],
            *cal.get("control", ("", "")), *pert,
            m["frame"][0], m["frame"][1],
            m["census_opcode"], m["census_target"], m["earlier_record"],
        ])


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

def self_test(d, starts, listings, census) -> int:
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {text}")

    print("gap_span_decode.py --self-test")

    for want in PINNED:
        reg, site = want["region"], want["site"]
        m = decode_site(d, site, reg, starts, listings, census)
        if m is None:
            check(False, f"{reg}:0x{site:04X} is decoded at all -- it is in a "
                     "committed gap, and the walk did not settle it")
            continue

        check((m["gap_lo"], m["gap_hi"], m["gap_len"])
              == (want["gap_lo"], want["gap_hi"], want["gap_len"])
              and m["file_offset"] == want["file_offset"],
              f"{reg}:0x{site:04X} is file 0x{want['file_offset']:05X} and "
              f"sits in the committed gap 0x{want['gap_lo']:04X}-"
              f"0x{want['gap_hi'] - 1:04X} ({want['gap_len']} bytes)")

        check((m["anchor"], m["anchor_text"])
              == (want["anchor"], want["anchor_text"]),
              f"  whose left anchor is 0x{want['anchor']:04X} "
              f"`{want['anchor_text']}` -- the last committed instruction "
              "start before it")

        check((m["owner"], m["owner_bytes"], m["owner_text"])
              == (want["owner"], want["owner_bytes"], want["owner_text"]),
              f"  and the walk from there owns the site at "
              f"0x{want['owner']:04X} `{want['owner_bytes'].hex(' ')}` = "
              f"`{want['owner_text']}`")

        check(m["owner_index"] == want["owner_index"]
              and m["owner_index"] == len(want["owner_bytes"]) - 1,
              f"  the site is byte {want['owner_index'] + 1} of "
              f"{len(want['owner_bytes'])} of that instruction -- its last, "
              "which is what a PC-relative branch's displacement is")

        check(m["reentry"] == tuple(want["reentry"]),
              f"  and {want['reentry'][0]} of {want['reentry'][1]} anchors "
              f"before it decode the whole gap and land exactly on "
              f"0x{want['gap_hi']:04X}")

        # Whether those anchors are bytes a listing frames is measured, not
        # assumed, and the two sites answer it differently -- so this is
        # asserted per site rather than as a shared property, and 0xA6DC's row
        # reads as the exception it is.
        check(m["reentry_cov"] == tuple(want["reentry_cov"]),
              f"  {want['reentry_cov'][0]} of those {want['reentry_cov'][1]} "
              f"anchors are themselves covered by a committed listing"
              + (" -- all of them, so this one is walked from known-framed "
                 "bytes" if want["reentry_cov"][0] == want["reentry_cov"][1]
                 else f" -- the other {want['reentry_cov'][1] - want['reentry_cov'][0]} "
                      "sit in a second unlisted stretch below it, which no "
                      "listing covers either"))

        check(m["frame"] == tuple(want["frame"]) and m["census_frame"]
              == tuple(want["frame"]),
              f"  the frame score at the site is {m['frame'][0]}/"
              f"{sum(m['frame'])} computed here and "
              f"{m['census_frame'][0]}/{sum(m['census_frame'])} recorded in "
              f"bank-call-targets.csv for the {m['census_opcode']} "
              f"{m['census_target']} row")

        check(earlier_record_agrees(m["earlier_record"], m["owner_file_offset"],
                                    m["owner_bytes"], m["owner_text"]),
              f"  and that row's `earlier_record` cell "
              f"(`{m['earlier_record']}`) names the same address and the same "
              "bytes")

    # The refusal, asserted rather than documented: an `--at` a committed
    # listing already covers has no gap to decode across, and answering it
    # anyway would be a second opinion on a row
    # `counter_sweep_entry.py` settles from the listing itself. Each site's
    # own left anchor is the covered address to try it with, so the case needs
    # no constant of its own and cannot drift away from the geometry above.
    for want in PINNED:
        anchor = want["anchor"]
        check(owner_of(anchor, starts, listings)[0] is not None
              and decode_site(d, anchor, want["region"], starts, listings,
                              census) is None,
              f"{want['region']}:0x{anchor:04X} is a committed listing start "
              "and is refused rather than answered")

    # The base rate, asserted as the *claim* the write-up rests on rather than
    # as a count of the tree: 24 of 24 is what this walk returns on the same
    # geometry elsewhere in the image, so it is not evidence about these two
    # sites. A control set that emptied out would make the claim vacuous, so
    # the pairs are checked to be non-empty; how many there are is printed,
    # not pinned. The two sites themselves are excluded, or the control would
    # contain what it is measuring.
    cal = reentry_calibration(d, starts, listings, DEFAULT_REGION,
                              exclude={w["site"] for w in PINNED})
    full, pairs = cal["control"]
    check(pairs >= 1 and full == pairs,
          f"  and the {full} of {pairs} other "
          f"{REENTRY_SPAN[0]}-{REENTRY_SPAN[1]}-byte unlisted stretches in "
          f"{DEFAULT_REGION} all read {ANCHORS} of {ANCHORS} the same way, so "
          f"that figure is the metric's base rate here rather than a fact "
          f"about {DEFAULT_REGION}:0x{PINNED[0]['site']:04X} or "
          f"0x{PINNED[1]['site']:04X}")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def measure_all(d, args, census, starts, listings):
    """The sites to report on: `--at` if given, else `PINNED`.

    A refusal and an unsettled walk are both reported as such rather than
    skipped, because a tool that prints nothing for an address it could not
    settle reads exactly like a tool that found nothing there.

    The calibration rides along on each row so the report prints the base rate
    beside the 24 of 24 it qualifies, rather than in a separate run a reader
    has to remember to make. It is measured once per invocation, and the
    control leaves out every stretch holding a site the tool is reporting on --
    both pinned ones whatever `--at` says, so the control is the same set of
    stretches whichever site is under the report and a site is never counted as
    evidence about itself.
    """
    exclude = {w["site"] for w in PINNED}
    if args.at is not None:
        addr = int(args.at, 16)
        exclude.add(addr)
        off = offset_for_runtime(addr, args.region)
        if off is None:
            # The one refusal here is the one that can fire: for a banked
            # region `runtime_addr()` is the exact inverse of
            # `offset_for_runtime()`, so an address that maps does not need a
            # second opinion about whether it maps back.
            print(f"0x{addr:04X} does not name a byte of this image as seen "
                  f"from region {args.region!r}, so there is nothing here to "
                  "decode", file=sys.stderr)
            return [], 1
        if owner_of(addr, starts, listings)[0] is not None:
            print(f"0x{addr:04X} is covered by a committed {args.region} "
                  "listing, so this tool has nothing to say about it -- use "
                  "counter_sweep_entry.py, which classifies it from the "
                  "listing itself", file=sys.stderr)
            return [], 1
        cal = reentry_calibration(d, starts, listings, args.region,
                                  exclude=exclude)
        m = decode_site(d, addr, args.region, starts, listings, census, cal)
        if m is None:
            print(f"0x{addr:04X} is in a committed gap, but the walk from "
                  "the left anchor did not reach it, so the site is left "
                  "unsettled -- a named residual, not an absence",
                  file=sys.stderr)
            return [], 1
        return [m], 0

    cal = reentry_calibration(d, starts, listings, DEFAULT_REGION,
                              exclude=exclude)
    return [m for m in (decode_site(d, w["site"], w["region"], starts,
                                    listings, census, cal) for w in PINNED)
            if m is not None], 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=FIRMWARE,
                    help="raw EC firmware image (default: the committed one)")
    ap.add_argument("--at", help="runtime address to report on, e.g. 0x81E7 "
                                  "(a runtime address, not a file offset)")
    ap.add_argument("--region", default=DEFAULT_REGION,
                    help=f"program the address is in (default: {DEFAULT_REGION})")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per site on stdout instead of the report")
    ap.add_argument("--reentry-calibration", action="store_true",
                    help="report the re-entry check's base rate -- the same "
                         "walk over other stretches of the same geometry, and "
                         "over random fillings of each site's own gap -- "
                         "instead of the sites")
    ap.add_argument("--self-test", action="store_true",
                    help="assert both gaps' spans, owners, byte indexes, "
                         "re-entries and anchor coverage, frames and "
                         "earlier_record cells against the committed tree")
    args = ap.parse_args(argv)

    d = open(args.firmware, "rb").read()
    census = load_census()
    starts, listings = read_listings(args.region)

    if args.self_test:
        return self_test(d, starts, listings, census)

    if args.reentry_calibration:
        exclude = {w["site"] for w in PINNED}
        if args.at is not None:
            exclude.add(int(args.at, 16))
        print_calibration(reentry_calibration(d, starts, listings,
                                              args.region, exclude=exclude),
                         args.region)
        return 0

    rows, rc = measure_all(d, args, census, starts, listings)
    if rc:
        return rc

    if args.csv:
        write_csv(rows)
        return 0

    for m in rows:
        print_site(m, show_span=len(rows) == 1)
    if len(rows) > 1:
        print("Both sites are reported without their decoded spans; --at "
              "prints the walk for one.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
