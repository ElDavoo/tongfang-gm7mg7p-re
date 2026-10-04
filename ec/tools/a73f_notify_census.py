#!/usr/bin/env python3
"""Census every call site of the EC's `0xA73F` notify primitive, and the
command byte each one carries.

`0xA73F` (`store_r7_at_6a_then_jump_1666`) copies R7 to internal RAM 0x6A,
reads it straight back into A and then into R7, and tail-jumps to `0x1666`,
which loads DPTR with the constant 0x896A and tail-jumps to `0x1114`. So the
byte that reaches `0xA73F` in R7 is what `0x896A` acts on, and `0x896A` is
bank1's `gate_06e6_0440_then_call_89b5`: it calls `0x89B5` only when XDATA
0x06E6 reads 0x01 and XDATA 0x0440 is non-zero, and `0x89B5` stores R7 into
XDATA 0x09F2 indexed by bits 0-2 of 0x09F1. **That is the whole of the claim:
the code is the payload, and this tool says which code each of the sites
carries. It does not say what any code *means*.** No code gets a name here,
because nothing static in this image reaches one;
`docs/findings/a73f-notify-path.md` says what would.

**A byte scan is a byte scan, and a site is found by a method that can be
wrong.** The scan looks for the two three-byte sequences `12 a7 3f` and
`02 a7 3f` anywhere in the image, which is a superset of the real sites: a
`12 a7 3f` sitting in a jump table or a data region is still reported here,
labelled with the region it landed in rather than dropped. What the tool adds
on top of the scan is the *resolution*: `disasm8051.converges_from()` over a
backward window says how many anchor offsets decode onto the site, the
cleanest-decode of those walks is taken, and the R7 write nearest the end of
it is read off.

**A site is answered only when one value dominates it, and the refusals name
themselves.** A site reached by two paths carrying two different constants, a
site whose R7 arrives in a callee's return value, and a site whose last R7
write is a register form are each reported `unresolved` with the reason and
whatever candidates were seen -- never guessed, and never reported as zero. An
address this scan does not reach is *not found by this method*, never absent.
The window is a budget and not a proof: a site the walk reaches the edge of
unresolved says so.

**Nothing here is measured on hardware.** A site is a decoded instruction, and
a code is a byte read out of the instruction before it. Neither says the EC
acts on it, or what the value means.

Usage:
    python3 a73f_notify_census.py
    python3 a73f_notify_census.py --csv
    python3 a73f_notify_census.py --self-test
"""
import argparse
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from disasm8051 import (FLOW_OPCODES, OPCODE_LEN, converges_from, decode,
                        paged_target, relative_target)

EC = os.path.join(HERE, os.pardir)
FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")

# The routine whose call sites this is a census of. bank0's 0xA73F; the same
# 16-bit address exists in every bank image and this tool deliberately scans
# the whole file rather than one bank, so a hit is reported with the region it
# fell in and the reader places it.
TARGET = 0xA73F

# `lcall` and `ljmp` to the target. The other two transfer forms that can name
# it -- `acall`/`ajmp` -- are paged and cannot address 0xA73F, whose page is
# 0xA000 and whose offset is above the paged form's reach from the common area.
CALL_SEQ = bytes((0x12, 0xA7, 0x3F))
JUMP_SEQ = bytes((0x02, 0xA7, 0x3F))

# How far back a site is decoded to find the R7 write that dominates it.
# Chosen to cover the longest write-then-call gap on these paths (the 0xC77F
# site's second entry is 13 instructions back) while staying short enough that
# the linear walk does not wander far into unrelated code. It is a budget, not
# a proof: a site whose walk reaches the window edge unresolved says so, and
# raising this constant is not a way to make one resolve.
BACK_WINDOW = 40

# The R7-writing opcodes, and what each says about the value. `mov r7,#imm` is
# the only one that names the code; the rest leave it dependent on a value this
# scan cannot see.
R7_IMM = 0x7F       # mov r7,#imm -- a constant, so the code is known
R7_FROM_A = 0xFF    # mov r7,a   -- register
R7_FROM_RN = range(0xF8, 0xFF)   # mov r7,rN -- register

# The regions the scan is allowed to call code, from trace_xdata_refs.REGIONS.
# A hit outside these is reported with the region name anyway; the map is here
# to say *which* region, and is deliberately not a filter.
from trace_xdata_refs import PD_MARKER, region_of


class Site(object):
    """One call/jump site of `0xA73F` and the code read off its own walk."""

    def __init__(self, offset, region, runtime, kind, code, verdict, note,
                 write_at, candidates, onto, over, listing=""):
        self.offset = offset
        self.region = region
        self.runtime = runtime
        self.kind = kind
        self.code = code
        self.verdict = verdict
        self.note = note
        self.write_at = write_at
        self.candidates = candidates
        self.onto = onto
        self.over = over
        self.listing = listing

    def row(self):
        return {
            "runtime": "0x%04X" % self.runtime if self.runtime is not None else "",
            "file_offset": "0x%05X" % self.offset,
            "region": self.region,
            "kind": self.kind,
            "code": "0x%02X" % self.code if self.code is not None else "",
            "verdict": self.verdict,
            "r7_write": "0x%04X" % self.write_at if self.write_at is not None else "",
            "listing": self.listing,
            "candidates": " ".join("0x%02X" % c for c in self.candidates),
            "note": self.note,
        }


def listings():
    """The exported listings, as (program, first, last, label) spans.

    Read from `ec/decompiled/index.csv`, which is committed text and carries
    each function's `size`, so the join is a containment test rather than a
    guess. This is what turns a column of addresses into a column a reader can
    act on: a site inside a named routine can be read against that routine's
    listing, and a site that is in none is visible as the gap it is -- which is
    how the blind spot below was found in the first place. A missing file means
    every listing reads as unknown rather than as an error, because this is a
    join and not a claim.
    """
    spans = []
    path = os.path.join(EC, "decompiled", "index.csv")
    if not os.path.exists(path):
        return spans
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                first = int(row["addr"], 16)
                last = first + int(row["size"])
            except (KeyError, ValueError):
                continue
            label = "0x%04X %s" % (first, row["name"]) if row.get("name") else ""
            spans.append((row["program"], first, last, label))
    return spans


def containing(spans, region, runtime):
    """The listing a site falls inside, or "" when none does."""
    if runtime is None:
        return ""
    for program, first, last, label in spans:
        if program == region and first <= runtime < last:
            return label
    return ""


def scan(d, target=TARGET, back=BACK_WINDOW, spans=None):
    """Every site of `target` in `d`, resolved as far as this method goes.

    Returns a list of `Site`. Order is by file offset, which for the sites this
    finds is also code order inside bank0. `spans` is the listing table from
    `listings()`, resolved here so a caller that does not care about the
    listing column does not pay for reading it.
    """
    pd_verified = PD_MARKER[1] in d
    if spans is None:
        spans = listings()
    seqs = ((bytes((0x12, target >> 8, target & 0xFF)), "lcall"),
            (bytes((0x02, target >> 8, target & 0xFF)), "ljmp"))
    sites = []
    for seq, kind in seqs:
        i = d.find(seq)
        while i >= 0:
            site = _resolve(d, i, kind, seq, pd_verified, back)
            site.listing = containing(spans, site.region, site.runtime)
            sites.append(site)
            i = d.find(seq, i + 1)
    sites.sort(key=lambda s: s.offset)
    return sites


def _resolve(d, offset, kind, seq, pd_verified, back):
    """Frame `offset` as best this method can, then read the R7 write off it."""
    name, _lo, base, _how = region_of(offset, pd_verified)
    runtime = None if base is None else base + (offset - _lo)

    onto, over = converges_from(d, offset, back)
    if onto == 0:
        # No backward anchor lands on it. Not "not a site" -- the byte pair is
        # there, and the framing evidence is reported so a reader can judge.
        return Site(offset, name, runtime, kind, None, "unframed",
                    "no backward anchor in %d bytes decodes onto this offset" % back,
                    None, [], onto, over)

    # Among the anchors that do land on it, take the walk with fewest `db`
    # bytes; a walk that decoded cleanly is evidence about framing that one
    # full of undecodable bytes is not. Ties go to the longer walk, then to the
    # lower offset, so the choice is deterministic.
    best = None
    for b in range(1, back + 1):
        start = offset - b
        if start < 0 or not _lands_on(d, start, offset):
            continue
        seqs = list(decode(d, start, back, addr=start))
        cut = [i for i, (o, _raw, _t) in enumerate(seqs) if o == offset]
        if not cut:
            continue
        walk = seqs[:cut[0]]
        db = sum(1 for _o, _raw, t in walk if t.startswith("db"))
        key = (db, -len(walk), start)
        if best is None or key < best[0]:
            best = (key, walk)
    walk = best[1]

    # Two ways into the site: the fall-through, and any branch elsewhere in
    # the window whose target *is* the site. Both have to agree on R7 or the
    # code is not one value, and a site with two of them is the case a
    # linear scan is most likely to answer wrongly -- reading the fall-through
    # alone and reporting one candidate as if it were the code.
    paths = [("fall-through", walk)]
    for i, (o, raw, t) in enumerate(walk):
        if raw[0] in FLOW_OPCODES and _branch_target(d, o, raw) == offset:
            paths.append(("branch at 0x%04X" % o, walk[:i]))

    found = [_r7_before(d, p, back) for _label, p in paths]
    # A path is usable only where the search reached a *constant*. `_r7_before`
    # returns an offset even when it stopped at a branch, so the filter is on
    # the code, not on the offset.
    usable = [f for f in found if f[1] is not None]
    codes = sorted({f[1] for f in usable})

    if len(usable) != len(paths):
        why = "; ".join("%s: %s" % (label, f[2])
                        for (label, _p), f in zip(paths, found) if f[1] is None)
        # `write_at` names the write the walk reached even when its value is
        # not a constant. Unresolved means "this says nothing about the code",
        # not "nothing was found", and a reader who is sent to the address can
        # check the refusal rather than take it.
        return Site(offset, name, runtime, kind, None, "unresolved", why,
                    found[0][0], codes, onto, over)
    if len(codes) > 1:
        return Site(offset, name, runtime, kind, None, "unresolved",
                    "%d paths into this site carry different codes"
                    % len(paths),
                    usable[0][0], codes, onto, over)
    return Site(offset, name, runtime, kind, usable[0][1], "resolved", "",
                usable[0][0], codes, onto, over)


def _r7_before(d, path, back):
    """The R7 write nearest the end of `path`, as (offset, code, why-not).

    Walking backwards from the site rather than forwards from the anchor is
    what makes this the *dominating* write: the last thing before the site is
    the one whose value is still live when the site runs. A branch or a call
    met on the way back ends the search, because past it the value in R7 is
    whatever that transfer left rather than something this window wrote.
    """
    for o, raw, t in reversed(path):
        if raw[0] == R7_IMM:
            return o, raw[1], None
        if raw[0] == R7_FROM_A or raw[0] in R7_FROM_RN:
            return o, None, "R7 arrives by '%s', which carries no constant" % t
        if raw[0] in FLOW_OPCODES:
            return o, None, ("a %s carries the value into the site, and no "
                             "R7 write in this window follows it" % t.split()[0])
    return None, None, "no R7 write in the %d-byte backward window" % back


def _branch_target(d, off, raw):
    """Absolute target of the transfer instruction at `off`, or None."""
    op = raw[0]
    if op in (0x02, 0x12):
        return (raw[1] << 8) | raw[2]
    if op in (0x01, 0x11):
        return paged_target(op, raw[1], off)
    return relative_target(op, raw[-1], off)


def _lands_on(d, start, offset):
    """Does a linear decode from `start` step exactly onto `offset`?"""
    i = start
    while i < offset:
        if i >= len(d):
            return False
        i += OPCODE_LEN[d[i]]
    return i == offset


def codes(sites):
    """The distinct codes the resolved sites carry, sorted."""
    return sorted({s.code for s in sites if s.verdict == "resolved"})


def table(sites):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(sites[0].row().keys()),
                       lineterminator="\n")
    w.writeheader()
    for s in sites:
        w.writerow(s.row())
    return buf.getvalue()


def report(sites):
    lines = []
    lines.append("# 0x%04X call sites, and the code each carries" % TARGET)
    lines.append("")
    lines.append("`found by a byte scan for %s and %s`; the code column is the "
                 "R7 write the site's own walk puts in front of it."
                 % (CALL_SEQ.hex(" "), JUMP_SEQ.hex(" ")))
    lines.append("")
    lines.append("| runtime | region | kind | code | verdict | R7 write | listing | note |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for s in sites:
        lines.append("| 0x%04X | %s | %s | %s | %s | %s | %s | %s |" % (
            s.runtime if s.runtime is not None else 0,
            s.region, s.kind,
            "0x%02X" % s.code if s.code is not None else "-",
            s.verdict,
            "0x%04X" % s.write_at if s.write_at is not None else "-",
            s.listing or "none exported",
            s.note))
    return "\n".join(lines) + "\n"


def self_test() -> int:
    """Known answers, from the committed listings and from inline fixtures.

    The committed-image half checks the two things a reader would otherwise
    have to take on trust: that the sites the image really has are the ones
    reported, and that each resolved code is the byte its own listing shows.
    Neither asserts a population -- that is the census, and CLAUDE.md records
    that shape failing repeatedly. The fixture half is where the refusal cases
    live, because those are the ones a future edit to the resolver would break
    silently.
    """
    bad = 0

    def check(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print("  %s  %s%s" % ("ok  " if ok else "FAIL", label,
                              "" if ok or not detail else "  " + detail))

    print("a73f_notify_census.py --self-test")

    with open(FIRMWARE, "rb") as f:
        d = f.read()

    sites = scan(d)
    resolved = [s for s in sites if s.verdict == "resolved"]
    print("  %d site(s), %d resolved, %d distinct code(s) -- the census, "
          "printed not asserted" % (len(sites), len(resolved), len(codes(sites))))

    # Every site is a real three-byte sequence at its own offset.
    check("every site sits on the byte sequence its kind names",
          all(d[s.offset] == (0x12 if s.kind == "lcall" else 0x02)
              and d[s.offset + 1:s.offset + 3] == bytes((0xA7, 0x3F))
              for s in sites))

    # Every site's region is one this map knows, and its runtime address
    # reconstructs its file offset.
    check("every site names a region and a runtime address that round-trips",
          all(s.region != "unknown" and s.runtime is not None
              and (s.runtime - 0x8000) + 0x8000 == s.runtime
              for s in sites),
          ", ".join("%s" % s.region for s in sites if s.region == "unknown"))

    # A resolved code is the byte at the R7 write the walk found, read out of
    # the image rather than out of the resolver's own bookkeeping.
    check("each resolved code is the immediate at its own R7 write",
          all(d[s.write_at] == R7_IMM and d[s.write_at + 1] == s.code
              for s in resolved))

    # The byte before a resolved site's write is not itself an R7 write, so the
    # site is not carrying a code that a later instruction overwrites.
    check("no resolved site has a second R7 write inside its own window",
          all(not any(d[o] in (R7_IMM, R7_FROM_A) or d[o] in R7_FROM_RN
                      for o in range(s.write_at + 2, s.offset))
              for s in resolved))

    # The two sites in the 0x8F0F listing are the fan publish's own pair, and
    # 0x8F0F.asm is committed with both immediates in it.
    fan = [s for s in sites if s.runtime in (0x8F17, 0x8F1C)]
    check("the 0x8F0F pair is present and carries the fan publish's two codes",
          sorted(s.code for s in fan) == [0x43, 0xA7],
          "got %s" % sorted(s.code for s in fan))

    # The 0xC77F site is the two-candidate case the resolver must refuse, and
    # the committed bytes show both candidates.
    two = [s for s in sites if s.runtime == 0xC77F]
    check("the two-candidate site is reported unresolved, not guessed",
          len(two) == 1 and two[0].verdict != "resolved")
    check("both of that site's candidate writes are the bytes the image holds",
          d[0xC772] == R7_IMM and d[0xC772 + 1] == 0xBA
          and d[0xC77D] == R7_IMM and d[0xC77D + 1] == 0xB8)

    # The 0x9FA0 site is the nearest-write case, and the walk has to stop at
    # the *last* write rather than the first: `mov r7,a` runs five bytes
    # earlier on the same path, and reporting that one would answer the site
    # with a value the site overwrites.
    near = [s for s in sites if s.runtime == 0x9FA0]
    check("the site with an earlier register write resolves on the nearest one",
          len(near) == 1 and near[0].code == 0xBC and near[0].write_at == 0x9F9E,
          "got %s at %s" % (near[0].code, near[0].write_at) if near else "missing")
    check("the register write that earlier site walks past is in the image",
          d[0x9F90] == R7_FROM_A)

    # The 0xC5A5 site is the call-carries-the-value case: an `lcall` sits
    # between the last R7 write this window can see and the site, so what
    # arrives is the callee's return value rather than anything decoded here.
    call = [s for s in sites if s.runtime == 0xC5A5]
    check("a site whose R7 arrives in a callee's return value is unresolved",
          len(call) == 1 and call[0].verdict == "unresolved")
    check("that site's byte is the lcall the walk names",
          d[0xC5A2] == 0x12 and d[0xC5A2 + 1:0xC5A2 + 3] == bytes((0xC9, 0xFF)))

    # --- inline fixtures: the shapes the committed image does not contain ---
    # `mov r7,a` immediately before the call, which carries no constant.
    check("a fixture whose dominating write is `mov r7,a` is unresolved",
          _fixture_verdict(bytes((0xFF, 0x12, 0xA7, 0x3F))) == "unresolved")
    # The same constant reaching the site by `ljmp` as by `lcall`.
    check("a fixture's `ljmp` and `lcall` shapes both resolve",
          _fixture_verdict(bytes((0x7F, 0x9B, 0x12, 0xA7, 0x3F))) == "resolved"
          and _fixture_verdict(bytes((0x7F, 0x9B, 0x02, 0xA7, 0x3F))) == "resolved")
    # An `lcall` between the write and the site, which is the shape the three
    # unresolved EC sites have: the value is in the callee's return, so the
    # site is refused rather than answered with the earlier constant.
    check("a fixture whose last write is separated by a call is refused",
          _fixture_verdict(bytes((0x22, 0x7F, 0x22, 0x12, 0xCA, 0x2D,
                                  0x12, 0xA7, 0x3F))) == "unresolved")
    # A branch into the site carrying a second constant: two paths, two codes,
    # and no way to say which ran. The site is refused with both named. The
    # `sjmp` displacement is 4 because it is measured from the byte after it,
    # which is offset 4 -- the site is at 8.
    amb = scan(bytes((0x7F, 0x11, 0x80, 0x04, 0x00, 0x00, 0x7F, 0x22,
                      0x12, 0xA7, 0x3F)), back=8)
    check("a fixture with two paths carrying different codes is refused",
          len(amb) == 1 and amb[0].verdict == "unresolved"
          and amb[0].candidates == [0x11, 0x22],
          "verdict %s candidates %s"
          % (amb[0].verdict, [hex(c) for c in amb[0].candidates]) if amb else "no site")
    # No write at all in the window.
    check("a fixture with no R7 write is unresolved",
          _fixture_verdict(bytes((0x22, 0x22, 0x12, 0xA7, 0x3F))) == "unresolved")
    # The scan is a byte scan: a sequence with no framing behind it is still
    # reported, carrying that verdict rather than being dropped.
    check("a byte sequence with no framing behind it is reported unframed",
          _fixture_verdict(bytes((0x00, 0x00, 0x12, 0xA7, 0x3F)), 4)
          in ("unframed", "unresolved"))
    # A target other than 0xA73F is the same census run elsewhere, which is how
    # the suite reaches shapes the EC image has no instance of.
    check("the census follows its target argument",
          [s.runtime for s in scan(bytes((0x7F, 0x5A, 0x12, 0x11, 0x22)),
                                   target=0x1122)] == [0x0002])

    print("\n%s" % ("self-test FAILED" if bad else "self-test passed"))
    return 1 if bad else 0


def _fixture_verdict(blob, back=4):
    """The verdict `scan` gives the one site in a hand-built buffer.

    A fixture is a handful of bytes, so it gets a window of its own rather
    than the image's: a backward window wider than the buffer would let the
    walk run off the front of it and the refusal being tested would pass for
    the wrong reason.
    """
    sites = scan(blob, back=back)
    return sites[0].verdict if sites else "absent"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=FIRMWARE,
                    help="EC image (default: the committed one)")
    ap.add_argument("--csv", action="store_true",
                    help="one row per site on stdout instead of the table")
    ap.add_argument("--self-test", action="store_true",
                    help="run the known answers and exit")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    with open(args.firmware, "rb") as f:
        d = f.read()
    sites = scan(d)
    if not sites:
        print("no site of 0x%04X found by this method in %s"
              % (TARGET, args.firmware), file=sys.stderr)
        return 1
    if args.csv:
        print(table(sites), end="")
    else:
        print(report(sites), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())