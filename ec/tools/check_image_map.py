#!/usr/bin/env python3
"""Check the `how` column of `trace_xdata_refs.REGIONS` against the image bytes.

`REGIONS` is five-tuples -- `(name, lo, hi, base, how)` -- and the `how` column
is the only thing in the image map that says anything about the *contents* of
the bands it maps. Every consumer throws it away: `region_of()` returns it, and
`xdata_span_survey.py`, `decode_index_table.py`, `pd_index_geometry.py`,
`audit_call_targets.py` and `trace_xdata_refs.py` itself all bind the fifth
element to `_`. So the column carrying the map's only checkable claim about
itself is the one column nothing checks. Today two of its six rows say
`"all 0xFF"`, which is a statement about 32 KiB and 64 KiB of committed bytes
that nothing in the tree was reading.

**What is checked, and what is not, is decided by the `how` string itself.**
`CHECKED` below is a small vocabulary and membership is exact: a row whose `how`
is a key is measured by the test that key names, and a row whose `how` is
anything else is reported `unchecked`, with the tool that *would* check it, or
`unidentified` when no tool is named for it here. That is the whole calibration
mechanism, and it is deliberately strict in the direction that cannot
overclaim: editing a row's prose -- making it longer, more specific or more
careful -- moves it *out* of the vocabulary and into `unidentified`, never into
a pass. A claim this tool has stopped recognising reads as unchecked rather
than as verified, so widening the vocabulary is the only way to get a row
measured, and that edit is a second test written beside the first rather than a
second word added to a list.

**The bands are read in full, never sampled.** 32 KiB and 64 KiB is a cheap
read of a committed file, and a sample cannot answer "is every byte `0xFF`" in
any case -- it can only fail to notice. The whole band is compared against
`{0xFF}` and the bytes that are not are named, with the values found.

**The `0x90` count is the point of the printout, not a footnote.**
`check_register_counts.py` splits each register's site count by region and
reports `main + pd != total` under the comment "Sites in the erased regions
would land here; the image map would be wrong, not the YAML". That branch can
only fire if a `MOV DPTR` byte lands in an erased band, and a band of `0xFF`
cannot contain one -- so the guard is unreachable on an image whose erased
bands really are `0xFF`, and its unreachability is a reading rather than a
conclusion once this tool prints the count. `trace_xdata_refs.MOV_DPTR` is the
constant counted, not the literal.

**What a pass is a claim about.** Run over `ec/firmware/GMxMGxx_11.800` this is
a statement about *that dump* -- the same bytes every other figure in this
repository was taken from. The table itself is a claim about a *map*, and the
difference is the re-derivation path, which `REGIONS`'s own preamble states:
"Re-derive this with find_banks.py before trusting it against a different dump
-- the bank->offset rows are that script's heuristic scoring, not a header
field." So the same command over a re-derived image compares the table's claim
against that image's bytes, and the footer names the tool that re-derives the
table. Neither reading is a claim about what the EC *does* with the bytes: an
erased band being `0xFF` is a measurement of committed content, not a
behavioural result, and nothing here ran on hardware.

**The refusals are the half that makes the rest worth anything.** A band
running past the end of the image is refused rather than sliced, so a truncated
dump cannot pass a claim by running out of bytes; a zero-length band is refused
for the same reason, since `all()` over no bytes is `True` and would otherwise
be a pass on an empty read; and a `how` the vocabulary holds no test for is
refused by `band_faults` itself rather than only by the row loop, so a second
caller that skipped the membership test cannot get a silent pass. All three, and
the failures, are in `--self-test`, which runs on hand-built buffers and reads
no firmware.

Usage:
    python3 check_image_map.py ../firmware/GMxMGxx_11.800
    python3 check_image_map.py --self-test
"""
import argparse
import os
import sys

# Imported rather than restated: a second copy of the map in a second file is
# how a check ends up holding a claim the table no longer makes. `MOV_DPTR` is
# here for the same reason -- the `0x90` printed below is the byte
# `check_register_counts.py`'s split is decided by, and the two must not come
# to disagree about which byte that is.
from trace_xdata_refs import MOV_DPTR, PD_MARKER, REGIONS

DEFAULT_FIRMWARE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, "firmware", "GMxMGxx_11.800")

# The tool that would check each claim outside `CHECKED`'s vocabulary, named per
# row so an `unchecked` line is a pointer rather than a shrug. Keyed on the
# `how` string for the reason `CHECKED` is: a row whose prose has been edited
# lands in neither table and is reported as having no named tool at all, which
# is then what it is.
UNCHECKED_BY = {
    "always mapped; same runtime address in every bank image":
        "make_bank_image.py -- the bank windows are what it builds, and the "
        "claim is about the common area landing at one runtime address in each",
    "make_bank_image.py <fw> 0 0x08000":
        "find_banks.py -- a bank->offset row is that script's heuristic "
        "scoring, not a header field, which is what REGIONS's preamble says",
    "make_bank_image.py <fw> 1 0x10000":
        "find_banks.py -- a bank->offset row is that script's heuristic "
        "scoring, not a header field, which is what REGIONS's preamble says",
    "separate ITE8850-PD 8051 image; dd bs=64k skip=2":
        "trace_xdata_refs.PD_MARKER -- the image's own marker, which "
        "pd_index_geometry.py --self-test already refuses without; what is "
        "unchecked is the rest of this row's prose",
}

# A band with a byte that is not 0xFF, on a 64 KiB band, would otherwise print
# 65536 of them. The first few are named and the rest counted, which locates a
# real fill failure and is bounded output on a badly wrong image.
NAMED_FAULTS = 8


def all_ff_fault(lo: int, band: bytes):
    """The `all 0xFF` test: the offending offsets in `band`, read at `lo`.

    Offset, not a bare index, because every number this prints is meant to be
    typed back into a hex dump -- an index into a band the reader cannot see
    the start of is not a location.
    """
    wrong = [i for i, b in enumerate(band) if b != 0xFF]
    if not wrong:
        return []
    named = ", ".join(f"0x{lo + i:05X} is 0x{band[i]:02X}"
                      for i in wrong[:NAMED_FAULTS])
    more = (f", and {len(wrong) - NAMED_FAULTS} more"
            if len(wrong) > NAMED_FAULTS else "")
    return [f"{len(wrong)} of {len(band)} byte(s) are not 0xFF: {named}{more}"]


# The `how` vocabulary, and it is the whole of it. A value, and the test that
# value means -- so a second entry is a second *test* rather than a second word
# this file has never learned to check, and a claim nobody has written a test
# for cannot be a key. Keyed on the exact string `REGIONS` carries, so a row is
# measured only by a claim this file can state the test for; see the module
# docstring for why that direction is the safe one. Below `all_ff_fault` for
# the ordinary reason: a dict of names is built at import, not at call.
CHECKED = {
    "all 0xFF": all_ff_fault,
}


def band_faults(d: bytes, lo: int, hi: int, how: str):
    """What stops `d[lo:hi]` satisfying `how`, as a list of strings.

    Empty is a pass. Every refusal is a string rather than a `None` because
    each is a different reason the claim was not measured, and a caller naming
    one of them needs to say which.

    `how` selects the test through `CHECKED` rather than being decoration, so a
    caller passing a claim this file has no test for gets a refusal and not a
    silent run of whichever test happens to be written below. The two read
    refusals come first: they are about the *read*, and they would apply to any
    claim, so a band too short to read is refused before its `how` is consulted.
    """
    if hi <= lo:
        return [f"the band is empty ({hi - lo} byte(s) at 0x{lo:05X}); `all` "
                "over no bytes is true, so it would pass without reading any "
                "of the claim"]
    if hi > len(d):
        return [f"the band runs {hi - len(d)} byte(s) past the end of a "
                f"{len(d)}-byte image (0x{lo:05X}-0x{hi:05X}); a truncated dump "
                "has to be refused, not sliced short and compared"]
    if how not in CHECKED:
        return [f"{how!r} is not a claim CHECKED states a test for, so this "
                "band was not measured"]
    return CHECKED[how](lo, d[lo:hi])


def band_facts(d: bytes, lo: int, hi: int):
    """(bytes read, distinct values, MOV DPTR count) over `d[lo:hi]`, or None.

    `None` when the band is not fully present, for the reason
    `census_ff_fill.span_bytes` gives its own short read: a figure taken over
    bytes that were never fetched is a clean-looking result about nothing, and
    the two read refusals in `band_faults` are exactly the cases it happens in.
    Reporting no figure at all is the honest third option beside "the claim
    holds" and "the claim fails".

    The `0x90` count is the number `check_register_counts.py` needs and cannot
    get, printed rather than asserted here so that the branch's unreachability
    on a given image is a reading. `set()` over a 64 KiB `bytes` is a C loop;
    nothing here samples.
    """
    if hi <= lo or hi > len(d):
        return None
    band = d[lo:hi]
    return len(band), sorted(set(band)), band.count(MOV_DPTR)


def row_verdict(d: bytes, row):
    """(verdict, faults) for one `REGIONS` row.

    `verdict` is `checked`, `unchecked` or `unidentified`. The last is the one
    that matters: a `how` no rule here states a test for is reported apart from
    one this file knows another tool owns, so a claim nobody has checked is
    never read as one somebody has.
    """
    _name, lo, hi, _base, how = row
    if how in CHECKED:
        return "checked", band_faults(d, lo, hi, how)
    if how in UNCHECKED_BY:
        return "unchecked", []
    return "unidentified", []


def report(path: str, d: bytes) -> int:
    """The whole table, and how many of its rows are not measurements."""
    print(f"check_image_map.py -- the `how` column of trace_xdata_refs.REGIONS "
          f"against {path}")
    print()
    print("region    file span            bytes  distinct  0x90  claim")
    problems = 0
    measured = {"checked": 0, "unchecked": 0, "unidentified": 0}
    holds = refused = 0
    for row in REGIONS:
        name, lo, hi, _base, how = row
        verdict, faults = row_verdict(d, row)
        measured[verdict] += 1
        span = f"{name:<9}  0x{lo:05X}-0x{hi - 1:05X}"
        if verdict == "checked":
            facts = band_facts(d, lo, hi)
            if facts is None:
                cells = f"  {'-':>7}  {'-':>8}  {'-':>4}"
            else:
                size, distinct, dp = facts
                shown = " ".join(f"0x{b:02X}" for b in distinct) or "-"
                cells = f"  {size:>7}  {shown:>8}  {dp:>4}"
            print(f"{span}{cells}  {how}")
            if faults:
                refused += 1
                for fault in faults:
                    problems += 1
                    print(f"          REFUSED: {fault}", file=sys.stderr)
            else:
                holds += 1
            continue
        blanks = f"  {'-':>7}  {'-':>8}  {'-':>4}"
        if verdict == "unchecked":
            print(f"{span}{blanks}  unchecked. {UNCHECKED_BY[how]}")
        else:
            print(f"{span}{blanks}  unidentified. {how!r} is not a claim "
                  "CHECKED states a test for, and no tool is named for it "
                  "here. It is unchecked, not verified")
    print()
    # "Measured" counts the rows a test was run on, which is not the same as
    # the rows that came back holding: a refused band was measured and failed,
    # and a truncated one was not measurable at all. Both are reported by name
    # rather than folded into a single figure that would read as a pass.
    print(f"{measured['checked']} row(s) put to a test: {holds} hold(s), "
          f"{refused} refused. {measured['unchecked']} reported unchecked with "
          f"the tool that owns them, {measured['unidentified']} reported "
          "unidentified. A row in either unchecked group has not been verified "
          "by this run, whatever its `how` says.")

    # The number that decides the other tool's branch, restated at the bottom
    # so a reader who ran this for that reason is not counting columns.
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X}, so the "
              "pd-image row's own identifying claim is not met by this image "
              "either; the measurements above stand on their own and say "
              "nothing about the regions they did not cover.")
    print("The 0x90 column is trace_xdata_refs.MOV_DPTR counted over each band, "
          "and it is the number check_register_counts.py's `main + pd != total` "
          "branch needs: a MOV DPTR byte inside an erased band would make that "
          "branch fire, so a band of 0xFF cannot contain one.")
    print("The table is a claim about a map; re-derive it with find_banks.py "
          "before trusting it against a different dump -- the bank->offset rows "
          "are that script's heuristic scoring, not a header field "
          "(trace_xdata_refs.REGIONS's own preamble).")
    if problems:
        print(f"{problems} refusal(s): a band's bytes do not satisfy the claim "
              "the map makes about it.", file=sys.stderr)
    return problems


def self_test() -> int:
    """The refusals and the vocabulary, on hand-built buffers, and no firmware.

    The negative control is the part that makes the rest mean anything. This
    check has exactly one shape of pass, so without a way for it to fail there
    is nothing here that distinguishes "the bands are all 0xFF" from "this
    function returns an empty list". Every way the comparison could be made to
    accept wrongly is therefore driven through *the same* `band_faults` call
    the committed rows go through -- at the first byte, the middle and the last,
    with three different wrong values, plus the two shapes a bad slice produces
    -- and each is asserted to be caught.
    """
    bad = 0
    ff = b"\xff"

    def check(ok: bool, label: str, detail: str = "") -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}"
              + (f"\n          {detail}" if detail and not ok else ""))

    def one_byte_at(at: int, value: int):
        """A clean band with one byte wrong, and the faults it produces."""
        band = bytearray(ff * 0x8000)
        band[at] = value
        return band_faults(bytes(band), 0, len(band), "all 0xFF")

    print("check_image_map.py --self-test")

    # The pass the tool exists to reach, built rather than read: 32 KiB of
    # 0xFF, which is the size of the smaller erased band.
    clean = ff * 0x8000
    check(band_faults(clean, 0, len(clean), "all 0xFF") == [],
          "a band that is every byte 0xFF passes (`all 0xFF`)")
    check(band_facts(clean, 0, len(clean)) == (0x8000, [0xFF], 0),
          "and the facts printed for it are 32768 bytes, {0xFF}, 0 MOV DPTR")

    # --- the negative control, through the same comparison ------------------
    # Three positions (the first, the middle, the last) and three values: a
    # 0x00, the MOV DPTR byte the check_register_counts.py branch needs and
    # must never find here, and `0x02`, a real opcode -- so a predicate that
    # had been narrowed to "not 0x00" would go red on two of the nine rather
    # than looking like it works.
    for at in (0, 0x4000, len(clean) - 1):
        for value in (0x00, MOV_DPTR, 0x02):
            faults = one_byte_at(at, value)
            check(len(faults) == 1
                  and f"0x{at:05X} is 0x{value:02X}" in faults[0],
                  f"a 0x{value:02X} at 0x{at:05X} is refused and named "
                  f"(got {faults})")

    # A band that is nearly all wrong, so the naming is bounded output rather
    # than 65536 of them, and the count is still the whole story.
    noisy = bytearray(ff * 0x100)
    noisy[::2] = b"\x00" * 0x80
    faults = band_faults(bytes(noisy), 0, len(noisy), "all 0xFF")
    check(len(faults) == 1 and faults[0].startswith("128 of 256")
          and "and 120 more" in faults[0],
          f"a half-0xFF band is counted, not enumerated (got {faults})")

    # The two shapes a bad slice produces, and the reason each is a refusal
    # rather than a pass.
    faults = band_faults(ff * 0x1000, 0, 0x2000, "all 0xFF")
    check(len(faults) == 1 and "past the end" in faults[0],
          f"a band running past the end of the image is refused (got {faults})")
    faults = band_faults(clean, 0x8000, 0x8000, "all 0xFF")
    check(len(faults) == 1 and "empty" in faults[0],
          f"a zero-length band is refused rather than passed by `all` over no "
          f"bytes (got {faults})")
    # A band that could not be read gets no figure either, for the same reason:
    # a size and a byte-value count taken over bytes that were never fetched
    # would be a clean-looking row about nothing.
    check(band_facts(ff * 0x1000, 0, 0x2000) is None
          and band_facts(clean, 0x8000, 0x8000) is None
          and band_facts(clean, 0, len(clean)) == (0x8000, [0xFF], 0),
          "band_facts reports no figure for a band that is not fully in the "
          "image, and the real one for a band that is")

    # --- the vocabulary, in both directions -------------------------------
    erased = [r for r in REGIONS if r[4] == "all 0xFF"]
    check(len(erased) == 2,
          f"both erased rows still say `all 0xFF` (found {len(erased)})")
    check(all(row_verdict(ff * 0x40000, r)[0] == "checked" for r in erased),
          "and both are measured rather than reported unchecked")

    named = {r[4] for r in REGIONS} - set(CHECKED)
    check(named == set(UNCHECKED_BY),
          f"every other row's `how` is named with the tool that would check it "
          f"({len(named)} row(s) in CHECKED's absence, {len(UNCHECKED_BY)} "
          f"named; unnamed {sorted(named - set(UNCHECKED_BY))}, "
          f"stale {sorted(set(UNCHECKED_BY) - named)})")

    # Editing a row's prose must move it out of coverage, not into it. Both
    # directions: a `how` that merely resembles a checked one, and one no tool
    # is named for at all.
    for how, label in (("all 0xFF (pad to bank 1)", "a reworded `all 0xFF`"),
                       ("some prose nobody wrote", "a `how` no row carries")):
        row = ("erased", 0x18000, 0x20000, None, how)
        check(row_verdict(clean, row) == ("unidentified", []),
              f"{label} is `unidentified`, not a pass")

    # And the same thing one level down, where it is the load-bearing half: a
    # `how` passed straight to `band_faults` is refused rather than falling
    # through to whichever test happens to be written below. Without this a
    # caller that skipped the `CHECKED` membership test -- which is exactly
    # what a future second caller might do -- would get a silent pass.
    faults = band_faults(clean, 0, len(clean), "all 0xFF (pad to bank 1)")
    check(len(faults) == 1
          and "not a claim CHECKED states a test for" in faults[0],
          f"band_faults refuses a `how` it has no test for (got {faults})")

    # Every row reaches a verdict, and the verdict is the one its `how` says it
    # should -- checked when the claim is in `CHECKED`, unchecked when another
    # tool is named for it, unidentified otherwise. Stated against the
    # membership tests rather than as a count of rows, so a table that grows a
    # region or drops one is still held by this rather than renumbering it.
    def want(how):
        return ("checked" if how in CHECKED
                else "unchecked" if how in UNCHECKED_BY else "unidentified")

    verdicts = [(r[4], row_verdict(ff * 0x40000, r)[0]) for r in REGIONS]
    check(all(got == want(how) for how, got in verdicts)
          and set(got for _, got in verdicts)
          <= {"checked", "unchecked", "unidentified"},
          f"every row is measured, unchecked or unidentified exactly as its "
          f"`how` says (got {[got for _, got in verdicts]})")

    print()
    if bad:
        print(f"self-test FAILED: {bad} case(s) disagree")
        return 1
    print("self-test passed: an all-0xFF band passes, a 0x00/0x90/0x02 at the "
          "first, middle and last byte of a 32 KiB band is refused and named, a "
          "half-0xFF band is counted rather than enumerated, a band past the "
          "end of the image and a zero-length band are refused, a `how` this "
          "file has no test for is refused rather than measured, and both "
          "`all 0xFF` rows are measured while every other row is reported "
          "unchecked or unidentified")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (e.g. "
                         "ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--self-test", action="store_true",
                    help="the refusals and the vocabulary, on hand-built "
                         "buffers; reads no firmware")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    d = open(args.firmware, "rb").read()
    return 1 if report(args.firmware, d) else 0


if __name__ == "__main__":
    sys.exit(main())
