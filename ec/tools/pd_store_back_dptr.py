#!/usr/bin/env python3
"""The DPTR each caller of the PD image's `0x122F` store-back loaded first.

`../../docs/findings/pd-direct-offset-pointer-add.md` settles that direct
`0x0D`/`0x0E` hold a *running* 16-bit base in the PD image's internal RAM --
`0x27FF` loaded at reset, advanced by every execution of the `0x122F`
store-back entry, read by the `0x1253` add at 33 call sites -- and names in its
section 8 what it does not establish: "What the running base relocates."
Naming the structure a base indexes needs either a live trace or a
caller-by-caller reading of the sites. This is the caller-by-caller half, which
is the half that converts a mechanism into a fact about the image.

**The measurement, in one paragraph.** For every `lcall`/`ljmp` of the store-back
entry, the DPTR its caller loaded before transferring, read as a signed
displacement from the running base. The load sits at a gap of 3 at every site,
so it is the instruction immediately before the transfer rather than merely the
nearest one in range, and the immediates run from `-0x22` to `+0x23` -- every
one of them inside the symmetric band `BAND` around zero, against a
whole-region baseline where 7.8% of `mov dptr,#imm16` immediates land in it. A
cursor walked by `-1`, `-4`, `-3` is what that looks like. **That is an
inference from a displacement distribution and it is labelled as one:** the
bytes name the offsets the firmware adds and not the structure they walk, and
nothing here is evidence about that structure's contents, its width or its
record count.

**Why this is a separate file and not another mode on
`pd_direct_offset_sites.py`.** Per `CLAUDE.md`, "a new tool is a new file, not
another mode bolted onto an existing one" -- that parent's table has four
`form` values and its own self-test, and a fifth mode with a fifth set of claims
would land in the file two branches collide on. Everything here is *imported*
from it rather than copied, which is the part that matters: `DPTR_SCAN = 32`,
`FRAME_BACK = 24` and `fold_back()`'s own constants are the same numbers the
parent's figures were measured with, and a second copy of `dptr_before()` here
would be a second answer to "what is the gap" free to drift from the first.
The entry is **derived** through `fold_back()` rather than written down as
`0x122F`, so this follows the bytes if the entry ever moves -- which is why the
parent spells that constant as an address in this image and not as a derived
value.

What this cannot do, stated once so no output below has to repeat it:

  * **The store-back entry is derived from the bytes, and the sites are a byte
    scan.** The same two-sided blind spot `pd_direct_offset_sites` documents
    applies in full: a `12 12 2f` inside a data table reads exactly like an
    `lcall 0x122F`, and a call reached through a dispatch table carries no
    target bytes at all. A site with no displacement is "not found by this
    method", never "that caller loads nothing".
  * **`dptr_signed` is a reading of the immediate, not a claim about how the
    firmware sign-extends.** It is the two's-complement value of the same
    16-bit immediate `dptr_loaded` already carries, added to nothing and
    resolved against nothing. Where it is useful -- saying that two sites load
    immediates four apart -- it is arithmetic a reader can do from the row; it
    is not evidence that the firmware treats the immediate as a displacement.
  * **`entry_pick` stays a heuristic** -- the nearest preceding call target by
    byte scan, not a function boundary -- and rows that disagree within one
    pick are read as disagreeing, which is the check §4 of the write-up uses.
  * **Nothing here observes hardware.** No register is read, written or read
    back, and the value the pair holds when a given site executes is a function
    of what the firmware has done since reset, not something these bytes
    decide. Every figure below is a byte-pattern count over the committed
    image, and the baseline beside it is the same band test applied to every
    `mov dptr,#imm16` in the region -- without it, "the immediates cluster" is
    a shape a reader could get from a bad scan.

Read-only: it opens the firmware image for reading and writes nothing but
stdout.

Usage:
    python3 pd_store_back_dptr.py ../firmware/GMxMGxx_11.800
    python3 pd_store_back_dptr.py ../firmware/GMxMGxx_11.800 --sites
    python3 pd_store_back_dptr.py ../firmware/GMxMGxx_11.800 --csv \
            > ../annotations/pd-store-back-dptr-sites.csv
    python3 pd_store_back_dptr.py ../firmware/GMxMGxx_11.800 --check
    python3 pd_store_back_dptr.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import collections
import csv
import glob
import io
import os
import re
import sys

from disasm8051 import converges_from
# `fold_back` is what makes the entry derived rather than written down, and
# `dptr_before` is the scan whose gap column the whole reading turns on; both
# are imported by bare module name the way `addc_dph_sites.py` and
# `computed_dptr_sites.py` reach across this directory. `FRAMED`/`PARTIAL`/
# `UNSYNCABLE` come across for the same reason -- the two tables must not
# disagree about what a framing count means -- and because the suite holding
# this table reads its closed `note` vocabulary off this module rather than
# re-spelling three phrases it would then have to keep in step.
from pd_direct_offset_sites import (DEFAULT_FIRMWARE, DPTR_SCAN, FRAME_BACK,
                                    FRAMED, IMAGE_PD, PARTIAL, UNSYNCABLE)
from pd_direct_offset_sites import (dptr_before, entries, entry_pick,
                                    fold_back, frame_pair, pd_base, pd_bounds)
from trace_xdata_refs import PD_MARKER, check_table, repo_path

HERE = os.path.dirname(os.path.abspath(__file__))
SITES_CSV = os.path.join(HERE, os.pardir, "annotations",
                         "pd-store-back-dptr-sites.csv")
LISTINGS_DIR = os.path.join(HERE, os.pardir, "decompiled", "pd")

# The band the reading is about, as inclusive signed displacements from the
# running base. It is spelled as a width around zero rather than as two
# endpoints because that is the shape the finding has: a narrow band the
# immediates land in, whose width was read off the spread and not chosen first.
BAND = 0x23

COLUMNS = ["form", "image", "file_offset", "runtime", "dptr_loaded", "dptr_gap",
           "dptr_signed", "frame_onto", "frame_over", "entry_pick",
           "in_committed_listing", "note"]

# The `note` vocabulary. Each says what this method found about the row and
# nothing more; the framing phrases are `pd_direct_offset_sites`' own, imported
# above so the two tables cannot disagree about what a framing count means.
# The row that says the scan found no load in range is spelled as its own
# phrase rather than left as an empty cell, so a blank `dptr_loaded` reads as
# the answer it is instead of as an omission.
NO_LOAD = "no `mov dptr,#imm16` within {n} bytes: not found by this scan"

# A committed `.asm` line, as the exporter writes it: the runtime address in
# four bare hex digits, the instruction's bytes, then the mnemonic and its
# target. Anchored at both ends so an operand elsewhere on the line cannot be
# mistaken for the transfer -- `ec/decompiled/pd/122F.asm` carries `ljmp
# 0x1253` inside the routine the tool is measuring the callers of, and a
# looser pattern would count it as one of its own.
LISTING_RE = re.compile(
    r"^([0-9A-Fa-f]{4})\s+(?:[0-9a-f]{2} ){2}[0-9a-f]{2}\s+"
    r"(lcall|ljmp)\s+0x([0-9a-fA-F]+)\s*$", re.M)
# The same line shape with the mnemonic and its operand left off, for the
# span `listing_ranges()` needs. It cannot be derived from LISTING_RE, which
# matches only the two transfer forms; matching the address-and-bytes prefix on
# its own is what lets a listing contribute its whole length to its span rather
# than only the transfers inside it.
INSN_RE = re.compile(r"^([0-9A-Fa-f]{4})\s+(?:[0-9a-f]{2} ){2}[0-9a-f]{2}",
                     re.M)


def pd_verified(d: bytes) -> bool:
    """Whether the committed dump carries the ITE8850-PD marker.

    The same test `pd_direct_offset_sites` and `pd_inline_arg_sites` each carry,
    read off the shared `trace_xdata_refs.PD_MARKER` rather than written as an
    offset here. **Kept separate rather than imported**, for the reason
    `pd_direct_offset_sites.pd_base()` gives: neither tool imports the other.

    It is also what makes the refusal *visible*. `check_pd_marker_contract.py`
    reads a module's marker contract off the block that names `PD_MARKER`, and
    an imported `pd_verified` is a name it cannot follow back to the marker --
    so a `main()` that plainly prints a note to stderr and returns 1 gets
    filed as `silent`, beside the `refuse` row on the siblings that carry the
    guard themselves. A committed row that says this tool says nothing about
    the marker, on a tool whose whole refusal is a note saying exactly that, is
    the wrong record.
    """
    off, magic = PD_MARKER
    return d[off:off + len(magic)] == magic


def signed_of(imm: int) -> int:
    """A `mov dptr,#imm16` immediate read as a two's-complement displacement.

    A *reading of the immediate* and nothing more: the same 16 bits
    `dptr_loaded` carries, with bit 15 taken as a sign. It says two sites load
    immediates four apart, which is what makes the rows comparable; it does not
    say the firmware adds a displacement, and the write-up's section 5 is what
    keeps that apart."""
    return imm - 0x10000 if imm >= 0x8000 else imm


def store_back_entry(d: bytes):
    """The store-back entry's runtime address, derived from the bytes.

    `fold_back()` finds it by locating the block that rewrites the pair from
    DPTR and returning the add that feeds it, so this follows the image rather
    than pinning `0x122F`. A hard-coded address here would be a second
    statement of where the entry is, free to go stale in a way the parent's own
    comment says it must not."""
    return fold_back(d)["entry"]


def store_back_sites(d: bytes, entry: int) -> list:
    """Every `lcall`/`ljmp` of the store-back entry, in offset order.

    The same `12 hi lo`/`02 hi lo` byte scan and the same two-forms counting
    `pd_direct_offset_sites.caller_sites` uses, against this tool's derived
    entry rather than its `POINTER_ADD`. It over- and under-counts in exactly
    the way that function documents, and is labelled the same way."""
    if entry is None:
        return []
    out = []
    for op, form in ((0x02, "ljmp"), (0x12, "lcall")):
        for i in range(len(d) - 2):
            if d[i] == op and (d[i + 1] << 8 | d[i + 2]) == entry:
                out.append((i, form))
    out.sort()
    return out


def listing_sites(entry: int, listings=None) -> set:
    """Runtime addresses a committed `.asm` decodes as a transfer to `entry`.

    The independent half of the reading. The byte scan takes every `12 12 2f`
    in the region; a committed listing carries only what a recovered function's
    decoded instruction stream holds. Where the two overlap, the displacement
    does not depend on the scan's known phantom problem.

    Read from the committed listings rather than from `call-graph-callees.csv`,
    which reports the same population as an `inbound` count over the whole PD
    image and so cannot say *which* sites they are. `listings` is a parameter so
    a case can hand in a directory of its own."""
    out = set()
    if entry is None:
        return out
    for path in sorted(glob.glob(os.path.join(listings or LISTINGS_DIR, "*.asm"))):
        with open(path, encoding="utf-8", errors="replace") as f:
            for m in LISTING_RE.finditer(f.read()):
                if int(m.group(3), 16) == entry:
                    out.add(int(m.group(1), 16))
    return out


def listing_ranges(listings=None) -> list:
    """The (first, last + 3) byte span of every committed PD listing.

    `listing_sites` answers "did a listing decode *this transfer*". This
    answers the different and weaker question "do these three bytes fall inside
    any listing's span at all", which is what tells the two apart for a site
    whose transfer a listing carries while its load falls in the gap between two
    recovered functions. The span is first-instruction to
    last-instruction-plus-three rather than an end address of its own, because
    a listing records the instructions the exporter emitted and nothing else."""
    spans = []
    for path in sorted(glob.glob(os.path.join(listings or LISTINGS_DIR, "*.asm"))):
        with open(path, encoding="utf-8", errors="replace") as f:
            insns = [int(m.group(1), 16) for m in INSN_RE.finditer(f.read())]
        if insns:
            spans.append((min(insns), max(insns) + 3))
    return sorted(spans)


def covered_by(spans: list, addr: int) -> bool:
    """Whether any listing's span contains `addr`."""
    return any(lo <= addr < hi for lo, hi in spans)


def listing_evidence(spans: list, off: int, gap: int) -> str:
    """What a committed listing says about a site, in three grades.

    Split in three rather than two because the two halves can disagree, and
    where they do the row has to carry the disagreement rather than round it up
    to `both`. `both` is a decoded listing holding the load *and* the transfer,
    which is adjacency confirmed by text rather than by a byte scan;
    `transfer only` is a listing that decoded the transfer while the load falls
    in the gap between two recovered functions, so the listing says nothing
    about the load at all."""
    has_transfer = covered_by(spans, off)
    has_load = gap is not None and covered_by(spans, off - gap)
    if has_transfer and has_load:
        return "both"
    if has_transfer:
        return "transfer only"
    return "no"


def site_rows(d: bytes, base: int, targets: set, spans: list) -> list:
    """One dict per candidate, keyed by `COLUMNS`.

    Every column is either derived from the bytes by this file or carried from
    the parent's own helpers, so a row cannot disagree with the table it
    extends about what a framing count or an `entry_pick` means."""
    out = []
    for off, form in store_back_sites(d, store_back_entry(d)):
        imm, gap = dptr_before(d, off)
        onto, over = converges_from(d, off, FRAME_BACK)
        pick, pick_gap = entry_pick(d, off, targets)
        out.append({
            "form": form,
            # The region, for the reason the parent carries it: a PD address is
            # not evidence about the EC's XDATA at the same number.
            "image": IMAGE_PD,
            "file_offset": f"0x{base + off:05X}",
            "runtime": f"0x{off:04X}",
            "dptr_loaded": f"0x{imm:04X}" if imm is not None else "",
            "dptr_gap": gap if gap is not None else "",
            "dptr_signed": f"{signed_of(imm):+d}" if imm is not None else "",
            "frame_onto": onto,
            "frame_over": over,
            "entry_pick": f"0x{pick:04X} (back {pick_gap})" if pick is not None else "",
            # What a committed `.asm` says about this site, in three grades, so
            # the rows resting on the byte scan alone are separable from the
            # ones a decoded listing corroborates -- and so the one row whose
            # load falls outside every listing is not rounded up to `both`.
            # All remain candidates; the column says which evidence there is,
            # not which sites are real.
            "in_committed_listing": listing_evidence(spans, off, gap),
            "note": NO_LOAD.format(n=DPTR_SCAN) if imm is None
                    else frame_pair(onto, over),
        })
    return out


def census(d: bytes, base: int) -> list:
    """Every row the committed table holds, in offset order."""
    return site_rows(d, base, entries(d), listing_ranges())


def csv_table(rows: list) -> str:
    """The `--csv` table, as a string rather than a write.

    A string because `--check` diffs the same bytes this prints and the tool's
    contract is that it writes nothing but stdout."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for row in rows:
        w.writerow([row[c] for c in COLUMNS])
    return buf.getvalue()


def displacements(rows: list) -> list:
    """The signed displacements the rows carry, in row order."""
    return [int(r["dptr_signed"]) for r in rows if r["dptr_signed"]]


def band_share(values: list) -> float:
    """What fraction of `values` falls in `-BAND .. +BAND`, as a percentage.

    The baseline the finding rests on. "The immediates cluster" is a claim
    about *this* population against *that* one, and a reader who has only the
    first half has been handed the shape without the comparison that makes it
    a shape."""
    if not values:
        return 0.0
    return 100.0 * sum(1 for v in values if -BAND <= v <= BAND) / len(values)


def region_displacements(d: bytes) -> list:
    """Every `mov dptr,#imm16` immediate in the region, read the same way.

    The population the baseline is measured over. Scanned by opcode rather than
    reported by the table, so the two figures come from the same band test
    over the same region and differ only in *which* `mov dptr` bytes they
    cover: every one of them here, against the ones immediately preceding a
    transfer above. A displacement absent from the table is counted here."""
    out = []
    for i in range(len(d) - 2):
        if d[i] == 0x90:
            out.append(signed_of((d[i + 1] << 8) | d[i + 2]))
    return out


def histogram(values: list) -> str:
    """The signed displacements, most frequent first, as one line.

    Frequency order rather than numeric order because the shape being read is
    a concentration, and a run of `-1`, `-4`, `-3` reads as one where a sorted
    list of a hundred immediates reads as noise."""
    counts = collections.Counter(values)
    return "  ".join(f"{v:+#06x} x{c}" for v, c in counts.most_common())


def print_sites(d: bytes, base: int) -> None:
    """One line per candidate, framing and pick beside the displacement."""
    rows = census(d, base)
    grades = collections.Counter(r["in_committed_listing"] for r in rows)
    print(f"Store-back call sites of {store_back_entry(d):#06x} in the pd-image: "
          f"{len(rows)} byte-pattern candidate(s) -- "
          + ", ".join(f"{k} {v}" for k, v in sorted(
              collections.Counter(r['form'] for r in rows).items()))
          + ".\nThe `in_committed_listing` column grades what a committed "
            "`.asm` says about each:\n  both "
          f"{grades['both']} load and transfer inside one decoded listing, "
          f"transfer only {grades['transfer only']}\n  (its load falls in the "
          f"gap between two recovered functions), no {grades['no']} rest on the "
          "byte scan alone.  All are candidates.\n")
    for r in rows:
        print(f"  {r['file_offset']}  {r['runtime']}  {r['form']:<5} "
              f"{r['dptr_loaded'] or '-':>6} {r['dptr_signed'] or '-':>6}  "
              f"gap {str(r['dptr_gap'] or '-'):>2}  "
              f"frame {r['frame_onto']}/{r['frame_onto'] + r['frame_over']}  "
              f"pick {r['entry_pick'] or '-':<18} "
              f"listing {r['in_committed_listing']}")
    if not rows:
        print("  none found by this method over this span")
    print(f"\n{repo_path(SITES_CSV)} holds one row per candidate above.  The "
          "write-up is\n../../docs/findings/pd-store-back-relocated-base.md, "
          "and the mechanism it reads is\n../../docs/findings/pd-direct-offset-"
          "pointer-add.md.")
    print()


def summary(d: bytes, base: int) -> int:
    """The displacement distribution and the baseline it is read against."""
    entry = store_back_entry(d)
    rows = census(d, base)
    values = displacements(rows)
    whole = region_displacements(d)
    gaps = collections.Counter(r["dptr_gap"] for r in rows if r["dptr_gap"])
    listed = [r for r in rows if r["in_committed_listing"] == "both"]
    listed_values = displacements(listed)
    print(f"Every caller of {entry:#06x} loads a DPTR before it transfers.  "
          f"Read as a signed\ndisplacement from the running base in direct "
          "0x0d/0x0e, the immediates over the\n"
          f"pd-image region 0x0000-0x{len(d) - 1:04X} are:\n")
    print(f"  store-back candidates  {len(rows):>5}  byte scan over the region, "
          "the way `--callers` counts")
    print(f"  with a load in range   {len(values):>5}  of "
          f"{DPTR_SCAN} bytes back")
    print(f"  gap of the load        "
          + ("  ".join(f"{g} bytes x{c}" for g, c in sorted(gaps.items()))
             if gaps else "not found by this scan"))
    print(f"  observed range         {min(values):+d} .. {max(values):+d}")
    print(f"  inside -{BAND:#x}..+{BAND:#x}         "
          f"{band_share(values):.1f}% of these {len(values)}, against "
          f"{band_share(whole):.1f}% of\n"
          f"{'':>21}the region's {len(whole)} `mov dptr,#imm16` immediates -- "
          "the baseline, and\n"
          f"{'':>21}the comparison the finding rests on")
    print("\n  the values, most frequent first:\n")
    print(f"    {histogram(values)}\n")
    if listed_values:
        # The counts are printed rather than asserted, because they are facts
        # about the committed listings and not properties of the reading: what
        # makes these rows corroboration is that every displacement here is one
        # the byte scan also found, which the self-test states as a relation.
        print(f"The {len(listed)} sites a committed `.asm` decodes with their "
              f"load inside the same\nlisting carry {len(set(listed_values))} of "
              "the values above, which is what says the\nreading does not rest "
              "on the scan's phantoms:\n")
        print(f"    {histogram(listed_values)}\n")
    print("  What that supports, at the strength the bytes carry: the running "
          "base is a\n  displacement base into a record-like structure the "
          "firmware walks by small\n  negative offsets, rather than a "
          "relocated table base.  It is an inference from\n  the distribution "
          "above and not a name for the structure; the write-up says\n  what "
          "it does not establish.")
    print(f"\n  {repo_path(SITES_CSV)} holds one row per candidate, with its "
          "framing counts, its\n  entry pick and whether a committed listing "
          "covers it.  `--sites` prints one line\n  per candidate; "
          "`pd-direct-offset-sites.csv` holds the writer and `0x1253` caller "
          "census\n  this extends.  The write-up is "
          "../../docs/findings/pd-store-back-relocated-base.md.\n")
    return 0


# --- self-test -------------------------------------------------------------
#
# Every expectation below is a relation the committed image and the committed
# listings already fix, or a byte run transcribed from an `r2 -a 8051` decode,
# so the tool cannot drift from the prose that cites it without a red run here.

# The two decodes the write-up quotes, byte for byte, as
# `r2 -a 8051 -e scr.color=0 -q -c 's ADDR; pd N' /tmp/pd.bin` prints them with
# the trailing memory-hint column stripped. The first is the store-back entry
# this tool derives and measures the callers of; the second is one of those
# callers, at the two instructions a committed listing (`717C.asm`) carries
# whole, so the adjacency the whole reading rests on can be checked against
# committed text by eye rather than only against this tool's own scan.
R2_DECODES = (
    (0x122F, 9, ("mov  a,0x0e", "add  a,0x82", "mov  0x82,a", "mov  a,0x0d",
                 "addc a,0x83", "mov  0x83,a", "cjne a,0x0d,0x1242",
                 "mov  0x0e,0x82", "ret")),
    (0x717C, 2, ("mov  dptr,#0xffff", "ljmp 0x122f")),
)

# The population shapes the reading rests on, pinned so a scan that quietly
# widened or a decode that stopped finding the entry is a red run here rather
# than a revised paragraph. The gap is the load's distance back from the
# transfer and is pinned because it is what makes the load *adjacent* rather
# than merely in range -- the whole difference between the two claims.
STORE_BACK_TOTALS = {"lcall": 45, "ljmp": 36}
LOAD_GAP = 3
# The entry `fold_back()` must derive, pinned as an address so a derivation
# that silently picks a different routine is caught here rather than becoming a
# table full of confident wrong rows.
EXPECTED_ENTRY = 0x122F
# The two entry_pick groups the write-up reads for internal coherence, and what
# every site under each loads. `entry_pick` is a heuristic, so these are pinned
# as "this pick carries these sites and they agree", not as a function boundary.
PICK_GROUPS = {0x007A: 0xFFFC, 0x10E8: None}


def self_test(fw_path: str) -> int:
    from disasm8051 import decode
    d = open(fw_path, "rb").read()
    if not pd_verified(d):
        print("note: no ITE8850-PD marker; the region is unidentified, so "
              "there is nothing to check", file=sys.stderr)
        return 1
    base = pd_base(True)
    lo, hi = pd_bounds()
    region = d[lo:hi]
    bad = 0

    def check(ok, what):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else '!  '} {what}")

    print("Self-test: the decodes transcribed from `r2 -a 8051`")
    for addr, n, want in R2_DECODES:
        # `mnemonic` pads to four columns and r2 does not, so both sides are
        # compared with the padding collapsed -- the same reason
        # pd_direct_offset_sites' own transcriptions are written unpadded.
        got = [" ".join(text.split()) for _, _, text
               in decode(region, addr, n, addr)]
        want = [" ".join(t.split()) for t in want]
        check(got == want, f"0x{addr:04X} decodes to {' / '.join(want)} "
                           f"(got {' / '.join(got)})")

    print("\nSelf-test: the population and the entry it is derived from")
    entry = store_back_entry(region)
    check(entry == EXPECTED_ENTRY,
          f"fold_back() derives the store-back entry as {entry:#06x} "
          f"(expected {EXPECTED_ENTRY:#06x})")
    sites = store_back_sites(region, entry)
    kinds = collections.Counter(form for _, form in sites)
    check(dict(kinds) == STORE_BACK_TOTALS,
          f"callers of {entry:#06x}: {dict(kinds)} (expected "
          f"{STORE_BACK_TOTALS})")

    rows = census(region, base)
    check(all(r["runtime"] == f"0x{off:04X}" for r, (off, _) in zip(rows, sites)),
          "the rows and the scan are in the same offset order")
    check(all(r["form"] == form for r, (_, form) in zip(rows, sites)),
          "every row carries the transfer form its own bytes spell")

    print("\nSelf-test: the loads, which are what the reading is")
    check(all(r["dptr_gap"] == LOAD_GAP for r in rows),
          f"every candidate's `mov dptr,#imm16` sits {LOAD_GAP} bytes back, so "
          "the load is the\n      instruction immediately before the transfer "
          "and not merely the nearest one in range")
    check(all(int(r["dptr_signed"]) == signed_of(int(r["dptr_loaded"], 16))
              for r in rows),
          "every `dptr_signed` is the two's-complement reading of the same "
          "immediate its row carries")
    check(all((int(r["dptr_signed"]) >= -BAND and
               int(r["dptr_signed"]) <= BAND) for r in rows),
          f"every displacement falls inside the -{BAND:#x}..+{BAND:#x} band the "
          "write-up reads")

    print("\nSelf-test: the baseline the finding rests on")
    values, whole = displacements(rows), region_displacements(region)
    check(band_share(values) > band_share(whole),
          f"the store-back sites' share of the band ({band_share(values):.1f}%) "
          f"exceeds the whole region's ({band_share(whole):.1f}% of "
          f"{len(whole)}),\n      which is the comparison that makes the "
          "concentration a finding rather than a shape")
    check(band_share(values) == 100.0,
          f"and it is the whole population, not most of it "
          f"({band_share(values):.1f}%)")

    print("\nSelf-test: the committed listings agree, independently of the scan")
    listed = listing_sites(entry)
    check(listed <= {off for off, _ in sites},
          f"every site a committed `.asm` decodes as a transfer to "
          f"{entry:#06x}\n      ({len(listed)} of them) is among the byte "
          "scan's candidates -- the reverse direction of the\n      parent's "
          "reconciliation, from the listings rather than from the counts")
    both = [r for r in rows if r["in_committed_listing"] == "both"]
    check(all(r["dptr_gap"] == LOAD_GAP for r in both),
          f"and every one of the {len(both)} sites a listing carries *with* "
          f"its load inside\n      the same listing has the same {LOAD_GAP}-byte "
          "gap, so the adjacency is confirmed by decoded text\n      rather than "
          "only by the byte scan")
    check(set(listed) >= {int(r["runtime"], 16) for r in both},
          "the grade `both` is a subset of the sites a listing decodes, so it "
          "cannot\n      promote a site no listing carries")
    check(set(displacements(both)) <= set(values),
          "their displacements are among the values the byte scan found, so a "
          "listing\n      cannot be quietly reporting a band the scan missed")
    # The grade that keeps a disagreement visible rather than rounding it up:
    # a transfer a listing decodes whose load falls in the gap between two
    # recovered functions. One exists in the committed tree, and the write-up
    # quotes it, so the case that would collapse it into a `both` is the one
    # that matters.
    transfer_only = [r for r in rows if r["in_committed_listing"]
                     == "transfer only"]
    check(all(int(r["runtime"], 16) in listed for r in transfer_only),
          f"the {len(transfer_only)} site(s) graded `transfer only` are "
          "transfers a listing\n      does decode, with their load outside "
          "every listing -- the disagreement the\n      grade exists to keep "
          "visible instead of rounding up to a `both`")

    print("\nSelf-test: the entry_pick groups the write-up reads")
    picks = collections.defaultdict(list)
    for r in rows:
        if r["entry_pick"]:
            picks[int(r["entry_pick"].split()[0], 16)].append(r)
    for pick, want in PICK_GROUPS.items():
        got = sorted({int(r["dptr_loaded"], 16) for r in picks[pick]})
        if want is None:
            # Named as a small set rather than one value where the sites
            # disagree, because `entry_pick` is a byte-scan heuristic and the
            # property worth holding is the coherence of the group, not an
            # identity this tool can promise across a change to the image.
            check(len(got) <= 2 and all(v >= 0xFFF8 for v in got),
                  f"the sites under pick {pick:#06x} load {len(got)} near-zero "
                  f"value(s)\n      {[hex(v) for v in got]}, so the group is "
                  "internally coherent")
        else:
            check(got == [want],
                  f"every site under pick {pick:#06x} loads "
                  f"{want:#06x} (got {[hex(v) for v in got]})")

    print("\nSelf-test: the committed table")
    check(sorted(set(r["form"] for r in rows)) == ["lcall", "ljmp"],
          "the census carries both transfer forms")
    check(all(r["image"] == IMAGE_PD for r in rows),
          "every row names the region it was scanned in, so no row reads as an "
          "EC claim")
    check(all(r["note"] == NO_LOAD.format(n=DPTR_SCAN) or r["dptr_loaded"]
              for r in rows),
          "a row with no load says so in its note rather than leaving an "
          "empty cell")
    print(f"\n  {repo_path(SITES_CSV)}: {len(rows)} row(s) + header")
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the committed "
              f"decodes and the committed image")
    else:
        print("self-test passed: the decodes match the `r2 -a 8051` "
              "transcriptions, the entry is\nderived at the address named and "
              "its candidates hold their gap and their band, the\nbaseline "
              "comparison is the one the write-up reads, and the committed "
              "listings\ncorroborate the scan from the other direction")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=None,
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--sites", action="store_true",
                    help="one line per candidate, with its displacement")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site table as CSV on stdout instead "
                         "of the summary")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="diff this run against the committed table and exit "
                         f"non-zero on any difference (default: "
                         f"{repo_path(SITES_CSV)})")
    ap.add_argument("--self-test", action="store_true",
                    help="check the decodes, the loads and the baseline "
                         "against the committed image and listings")
    args = ap.parse_args()

    if args.self_test:
        return self_test(args.firmware or os.path.join(HERE, DEFAULT_FIRMWARE))

    if not args.firmware:
        ap.error("give a firmware image, or --self-test")

    d = open(args.firmware, "rb").read()
    # The marker unpacked beside the guard rather than inside it, the shape
    # `pd_inline_arg_sites.py` uses: `check_pd_marker_contract.py` reads the
    # refusal off the block that names `PD_MARKER`, so a guard that unpacks it
    # internally files this tool as `silent` -- which `pd_verified()` above
    # explains at more length.
    off, magic = PD_MARKER
    if not pd_verified(d):
        # stderr, so `--csv` redirected to a file stays a clean CSV, and
        # non-zero: without the marker the region is unidentified, so every
        # runtime address below would be somebody else's.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "the pd region is unidentified, so this tool has no population "
              "to read\n", file=sys.stderr)
        return 1

    base = pd_base(True)
    lo, hi = pd_bounds()
    region = d[lo:hi]

    if args.check is not None or args.csv:
        generated = csv_table(census(region, base))
        if args.check is not None:
            return check_table(generated, args.check)
        sys.stdout.write(generated)
        return 0

    if args.sites:
        print_sites(region, base)
        return 0
    return summary(region, base)


if __name__ == "__main__":
    sys.exit(main())