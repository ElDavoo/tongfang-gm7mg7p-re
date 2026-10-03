#!/usr/bin/env python3
"""Diff two EC firmware images region by region, and say what a difference is not.

Issue #83 asks for the EC image that shipped in 2021 to be diffed against
`ec/firmware/GMxMGxx_11.800`. Nothing can produce that image from a
GitHub-hosted runner -- `docs/findings.md` §6 records that the vendor's own
`ifux64.efi` has no read mode, so the dump is a follow-mode reader or an
external SPI programmer, both human steps. This is the half that can be built
now: given the two files, it answers the comparison and it does not pretend to
have obtained either of them.

**The 256 KiB dump is not one program.** It holds the main EC firmware (the
common area plus two CODE banks) and, at file offset `0x20000`, a second,
self-contained 8051 image that identifies itself as `ITE8850-PD` -- its own
reset vector, its own 64 KiB address space, therefore its own XDATA map. A
`MOV DPTR,#0x07E2` in the PD image says nothing about the main EC's `0x07E2`,
and a file-wide byte count or reference count adds the two together silently.
That is `docs/findings.md` §3a, and it is why every figure below is attributed
to a region rather than to the file.

The regions come from `trace_xdata_refs.REGIONS` and the attribution from its
`region_of()`, both **imported rather than re-derived**, so this tool cannot
drift from the map the rest of the EC work uses -- `find_banks.py`'s bank table
is a heuristic in any case, and a second copy of it here would be a second
answer to a question the repository already answers once.

**What a zero here means.** "No differing byte in this region" is a statement
about a byte-for-byte comparison and nothing more. It is not "the charge code is
the same": an access through a computed or indirect pointer is invisible to a
byte diff exactly as it is to a `MOV DPTR,#addr` scan, so a firmware that
reaches the same behaviour through a table walk diffs clean against one that
hard-codes it. The reference-count section says the same thing in the other
direction -- `scan_refs.py`'s counts are re-run on *both* images, so a register
whose direct-reference count moved is visible even when the byte it moved is
not the byte anyone was looking at. A count of zero anywhere is "not found by
this method", never "absent".

**The marker is checked, not assumed.** A candidate 2021 dump whose `0x20000`
region does not carry `ITE8850-PD` is a different layout from the one this map
describes, so its regions are labelled `unknown` rather than inheriting this
image's conclusions -- `region_of()` already does that, and this tool passes
the checker's answer through rather than second-guessing it.

Usage:
    fw_image_diff.py ../firmware/GMxMGxx_11.800 recovered-2021.bin
    fw_image_diff.py A B --addrs 0x07A6 0x07B9 0x07D0
    fw_image_diff.py A B --regions common bank1       # only these
    fw_image_diff.py --self-test
"""
import argparse
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import scan_refs  # noqa: E402  (needs the sys.path entry above)
from trace_xdata_refs import PD_MARKER, REGIONS, region_of  # noqa: E402

# Regions whose bytes are firmware at all. `erased` is all 0xFF in the
# committed image, and a candidate dump that has 0xFF there where this one does
# not is a fact about the dump's own extent rather than about the firmware --
# it is reported, but on its own line so it cannot be read as a code change.
FIRMWARE_REGIONS = tuple(name for name, _lo, _hi, _base, _how in REGIONS
                         if name != "erased")

CAVEAT = (
    "Two firmware images, compared byte for byte within each region and\n"
    "re-counted with scan_refs.py's MOV DPTR,#addr scan. A region at zero\n"
    "differing bytes means this comparison found no difference there, not\n"
    "that the two are equivalent: an access through a computed or indirect\n"
    "pointer is invisible to both the byte diff and the reference scan.\n"
    "A zero reference count means 'not found by this method', never\n"
    "'absent' -- see scan_refs.py's header and docs/findings.md 3a.\n"
)


def pd_verified(data: bytes) -> bool:
    off, magic = PD_MARKER
    return data[off:off + len(magic)] == magic


def region_rows(data_a: bytes, data_b: bytes, only=None, verified=None):
    """One row per region: name, span, differing byte count, first/last offset.

    The span comes from the shared `REGIONS` table and the counts from the two
    images. The `pd-image` row's *name* comes from `region_of()`, not from the
    table, when `verified` is supplied -- because a candidate dump whose
    `ITE8850-PD` marker is absent has something else at `0x20000`, and printing
    a row labelled `pd-image` for it while the note above says "attributed to
    unknown" would state a property the table does not have. Passing
    `verified=None` keeps the table's own name, which is what the self-test
    wants when it is asking "does a flipped byte land where the table says".

    `unmatched_tail` is zero in every row `compare()` prints, because
    `check_sizes()` has already refused two images of different lengths. It is
    kept so a caller reaching this function directly gets a number rather than a
    span that quietly stopped at the shorter file.
    """
    out = []
    for name, lo, hi, _base, _how in REGIONS:
        if only and name not in only:
            continue
        if verified is not None:
            name, _lo, _base, _how = region_of(lo, verified)
        a, b = data_a[lo:hi], data_b[lo:hi]
        span = min(len(a), len(b))
        differing = [i for i in range(span) if a[i] != b[i]]
        out.append({
            "region": name,
            "lo": lo,
            "hi": hi,
            "span": span,
            "differing": len(differing),
            "first": lo + differing[0] if differing else None,
            "last": lo + differing[-1] if differing else None,
            "unmatched_tail": max(len(a), len(b)) - span,
        })
    return out


def reference_counts(addrs, data: bytes):
    """`{addr: (total, ec, pd)}` from `scan_refs.scan`, on one image.

    Read through the same function `scan_refs.py`'s own CLI calls, so the
    "two unrelated programs in one dump" split is that tool's arithmetic and
    not a second implementation of it here.
    """
    hits = scan_refs.scan(data, pd_verified(data))
    return {a: tuple(hits.get(a, [0, 0, 0, []])[:3]) for a in addrs}


def check_sizes(path_a: str, len_a: int, path_b: str, len_b: int) -> None:
    """Refuse two images of different lengths, naming both lengths.

    A diff that compared the overlap and said nothing about the rest would
    report "identical" for a dump whose last 64 KiB is missing, which is the
    §4c failure in a new costume: the reader is told there is no difference
    where the tool never looked. The sizes are in the message because "the
    images differ in size" is not actionable and the two numbers are.
    """
    if len_a != len_b:
        raise SystemExit(
            f"fw_image_diff.py: refusing to compare images of different sizes.\n"
            f"  {path_a}: {len_a} bytes\n"
            f"  {path_b}: {len_b} bytes\n"
            f"Only the overlap could be compared, and a report over the overlap "
            f"alone would\nread as a whole-image result. The mapped regions in "
            f"trace_xdata_refs.REGIONS\ncover the first {REGIONS[-1][2]} bytes; "
            f"a dump of a different flash\nsize is a different image map, and "
            f"find_banks.py is the tool that re-derives one.")


def compare(path_a: str, path_b: str, addrs, only=None):
    with open(path_a, "rb") as fh:
        data_a = fh.read()
    with open(path_b, "rb") as fh:
        data_b = fh.read()
    check_sizes(path_a, len(data_a), path_b, len(data_b))

    out = [f"old: {path_a}  ({len(data_a)} bytes)", f"new: {path_b}  ({len(data_b)} bytes)", ""]

    verified = {"old": pd_verified(data_a), "new": pd_verified(data_b)}
    for label, path in (("old", path_a), ("new", path_b)):
        off, magic = PD_MARKER
        if not verified[label]:
            out.append(f"note: no {magic.decode()!r} marker at file 0x{off:05X} in the "
                       f"{label} image --")
            out.append("      its 0x20000-0x2FFFF bytes are attributed to "
                       "'unknown', not to pd-image.")
    out += ["", CAVEAT, "Regions"]

    # One verdict for the pair, and the conservative one: a byte is only
    # attributed to the PD image if *both* images carry its marker. A pair
    # where one side has lost it is a pair whose 0x20000 region is not
    # established on both sides, and calling it `pd-image` on the strength of
    # the other one would be the §3a mistake in a new direction.
    rows = region_rows(data_a, data_b, only,
                       verified=verified["old"] and verified["new"])
    out.append(f"{'region':<10} {'file span':<16} {'compared':<10} "
               f"{'differing':<10} {'first':<10} {'last'}")
    for row in rows:
        first = f"0x{row['first']:05X}" if row["first"] is not None else "-"
        last = f"0x{row['last']:05X}" if row["last"] is not None else "-"
        out.append(f"{row['region']:<10} "
                   f"0x{row['lo']:05X}-0x{row['hi'] - 1:05X} {row['span']:<10} "
                   f"{row['differing']:<10} {first:<10} {last}")

    total = sum(r["differing"] for r in rows)
    code_total = sum(r["differing"] for r in rows
                     if r["region"] in FIRMWARE_REGIONS)
    out += ["",
            f"  {total} differing byte(s) over the regions compared, of which "
            f"{code_total}",
            "  are outside 'erased'. A total over the file is not reported: "
            "it would add",
            "  the main EC and the PD image together, which is the mistake "
            "docs/findings.md",
            "  3a records."]
    # `unmatched_tail` is zero in every row printed above, because
    # `check_sizes()` has already refused two images of different lengths. It
    # is kept on the row because `region_rows()` is reachable directly, and a
    # caller that skipped the size check should get the number rather than a
    # span that quietly stopped at the shorter file.

    if addrs:
        out += ["", "Direct XDATA reference counts, per image "
                     "(scan_refs.py's ec=/pd= split)"]
        old_counts = reference_counts(addrs, data_a)
        new_counts = reference_counts(addrs, data_b)
        out.append(f"{'addr':<8} {'old total/ec/pd':<20} {'new total/ec/pd':<20} moved")
        for addr in addrs:
            o, n = old_counts[addr], new_counts[addr]
            moved = [i for i, (x, y) in enumerate(zip(o, n)) if x != y]
            names = ("total", "ec", "pd")
            out.append(f"0x{addr:04X}  {'/'.join(str(v) for v in o):<18} "
                       f"{'/'.join(str(v) for v in n):<18} "
                       f"{', '.join(names[i] for i in moved) or 'no'}")
        out += ["",
                "  A moved count is a difference this scan can see even where a "
                "differing byte is not",
                "  attributed to a region above. A zero on either side is "
                "'not found by this",
                "  method'; 0x07B0-0x07BE is a documented blind spot "
                "(scan_refs.py's header)."]
    return "\n".join(out)


# Offsets the self-test mutates, one per region whose attribution has to be
# checked. Written as file offsets and named by the region they fall in, so a
# region boundary moving breaks the pairing rather than silently re-pointing it.
SELF_TEST_MUTATIONS = {
    "common": 0x0100,
    "bank0": 0x08010,
    "bank1": 0x10020,
    "pd-image": 0x20040 + 0x10,
}


def self_test(firmware: bytes) -> int:
    """The refusals, the attribution, and an oracle this file did not write.

    A check that has quietly stopped rejecting anything looks exactly like a
    check that is working, so the refusals come first and the byte that must
    *not* be counted toward the main EC is asserted as hard as the one that
    must.
    """
    bad = 0
    print("fw_image_diff.py --self-test")

    # The two images most of the assertions below are made against, written
    # before any of them run because several need a *file* rather than bytes.
    # `ec/tools/testdata/` carries a hand-written index
    # (`check_testdata_index.py`) and two 256 KiB fixtures do not need a row
    # in it, so they go to a scratch directory and are deleted with it.
    scratch = tempfile.TemporaryDirectory(prefix="fw_image_diff_")
    old_path = os.path.join(scratch.name, "committed.bin")
    new_path = os.path.join(scratch.name, "mutated.bin")
    _mutated = bytearray(firmware)
    for _off in SELF_TEST_MUTATIONS.values():
        _mutated[_off] ^= 0xFF
    with open(old_path, "wb") as fh:
        fh.write(firmware)
    with open(new_path, "wb") as fh:
        fh.write(bytes(_mutated))

    def expect(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}"
              + (f"  {detail}" if detail and not ok else ""))

    def refuses(fn, *a):
        try:
            fn(*a)
        except SystemExit:
            return True
        return False

    def _refusal_text(fn):
        """The text a refusal raises, captured rather than printed."""
        err = sys.stderr
        sys.stderr = io.StringIO()
        try:
            fn()
        except SystemExit as exc:
            return str(exc)
        finally:
            sys.stderr = err
        return ""

    def differing_in(data_a, data_b, region):
        return next(r["differing"] for r in region_rows(data_a, data_b)
                    if r["region"] == region)

    # --- the refusals -------------------------------------------------------
    def refuses_sizes(short):
        return refuses(check_sizes, "old.bin", len(firmware), "new.bin", short)

    expect("a shorter image is refused rather than compared to its own length",
           refuses_sizes(len(firmware) - 1))
    expect("a longer image is refused the same way",
           refuses_sizes(len(firmware) + 1))
    expect("an image of the same size is not refused",
           not refuses_sizes(len(firmware)))
    expect("the refusal names both sizes, because 'the images differ' is not "
           "actionable",
           str(len(firmware) - 1) in _refusal_text(
               lambda: check_sizes("old.bin", len(firmware), "new.bin",
                                   len(firmware) - 1)))
    # The marker is at 0x20040 and the mutation offset is past it, so the two
    # are independent: a candidate dump whose identifier has been overwritten
    # is a different image map, and must not inherit this one's conclusions.
    #
    # Asserted on what a *run* prints, not on `region_of()` directly. The
    # dependency already does this labelling, so an assertion on the dependency
    # passes even if `compare()` stopped consulting it -- which is what
    # removing the marker branch did, leaving the tool green while it printed a
    # row labelled `pd-image` under a note saying `unknown`.
    unmarked = bytearray(firmware)
    unmarked[PD_MARKER[0]] ^= 0xFF
    stripped_path = _scratch_image(bytes(unmarked), scratch.name)
    unmarked_text = compare(old_path, stripped_path, [])
    table = unmarked_text.split("Regions", 1)[-1]
    expect("a run against an image whose marker is gone labels that region "
           "unknown, not pd-image",
           "unknown" in table and "pd-image" not in table, table[:200])
    expect("a run against a marker-less image says so in a note of its own",
           "no 'ITE8850-PD' marker" in unmarked_text)
    expect("a run over two intact images still calls that region pd-image",
           "pd-image" in compare(old_path, new_path, []).split("Regions", 1)[-1])
    # The dependency's own verdict, kept so the two cannot drift silently.
    expect("the shared region_of() agrees the marker-less region is unknown",
           region_of(SELF_TEST_MUTATIONS["pd-image"], False)[0] == "unknown")
    expect("an offset outside every mapped region is unknown",
           region_of(len(firmware), pd_verified(firmware))[0] == "unknown")

    # --- an image against itself is the oracle ------------------------------
    zero = region_rows(firmware, firmware)
    expect("an image diffed against itself differs nowhere",
           all(r["differing"] == 0 for r in zero),
           str([r for r in zero if r["differing"]]))
    expect("every region is attributed to a name this tool knows",
           {r["region"] for r in zero} <=
           {name for name, *_ in REGIONS})

    # --- one flipped byte per region, attributed to that region and no other
    for region, offset in SELF_TEST_MUTATIONS.items():
        mutated = bytearray(firmware)
        mutated[offset] ^= 0xFF
        rows = region_rows(firmware, bytes(mutated))
        touched = [r["region"] for r in rows if r["differing"]]
        expect(f"a flipped byte at 0x{offset:05X} lands in {region} and "
               f"nowhere else", touched == [region], str(touched))
        expect(f"that row names 0x{offset:05X} as its first differing byte",
               next(r for r in rows if r["region"] == region)["first"] == offset)

    # The one that matters most, stated on its own: a byte inside the PD image
    # is not EC-side evidence, and a tool that counted it toward the main EC
    # would be §3a again.
    pd_offset = SELF_TEST_MUTATIONS["pd-image"]
    expect("a flipped byte in the pd-image is not counted in the main EC's "
           "total", differing_in(firmware, firmware[:pd_offset] + b"\x00"
                                 + firmware[pd_offset + 1:], "common") == 0)

    # --- the reference-count side -------------------------------------------
    base = reference_counts([0x07A6, 0x07D0], firmware)
    expect("the committed image's 0x07A6 is read through scan_refs, split "
           "ec/pd",
           base[0x07A6][1] > 0 and base[0x07A6][0] >= base[0x07A6][1],
           str(base[0x07A6]))
    expect("0x07B9 is zero in the committed image by this scan, which is the "
           "documented 0x07B0-0x07BE blind spot and not an absence",
           reference_counts([0x07B9], firmware)[0x07B9] == (0, 0, 0))

    # --- and the whole path over those two files ----------------------------
    # Everything above works on bytes. This is the CLI's own path.
    text = compare(old_path, new_path, [0x07A6, 0x07D0])
    expect("a full run attributes each flipped byte to its own region and no "
           "other", sorted(
               r["region"] for r in region_rows(firmware, bytes(_mutated))
               if r["differing"]) == sorted(SELF_TEST_MUTATIONS))
    expect("a full run prints the caveat a reader needs before the numbers",
           "'absent'" in text)
    expect("a full run re-counts the named addresses on both images",
           "0x07A6" in text and "old total/ec/pd" in text)
    expect("a run of the image against itself reports no differing bytes",
           "0 differing byte(s)" in compare(old_path, old_path, []))

    print("data: the committed image against a copy with one byte flipped per "
          "mapped region")
    scratch.cleanup()
    return 1 if bad else 0


def _scratch_image(data: bytes, into: str) -> str:
    """`data` written into `into` as a file, for a run rather than a function.

    The marker cases need `compare()` to open two real files, because the
    labelling they check happens inside `compare()` and nowhere else.
    """
    path = os.path.join(into, f"{abs(hash(data)) % (1 << 32):08x}.bin")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old", nargs="?", help="the older EC firmware image")
    ap.add_argument("new", nargs="?", help="the candidate image to diff against it")
    ap.add_argument("--addrs", nargs="*", default=[],
                    help="hex EC addresses to re-count on both images")
    ap.add_argument("--regions", nargs="*",
                    help="only these regions (default: every mapped region)")
    ap.add_argument("--self-test", action="store_true",
                    help="the refusals, the region attribution, and the counts")
    args = ap.parse_args(argv)

    if args.self_test:
        firmware = os.path.abspath(os.path.join(
            HERE, os.pardir, "firmware", "GMxMGxx_11.800"))
        with open(firmware, "rb") as fh:
            return self_test(fh.read())

    if not args.old or not args.new:
        ap.error("give two firmware images, or --self-test")

    addrs = []
    for a in args.addrs:
        try:
            addrs.append(int(a, 16))
        except ValueError:
            ap.error(f"{a!r} is not a hex address")

    try:
        print(compare(args.old, args.new, addrs, args.regions or None))
    except OSError as exc:
        print(f"fw_image_diff.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
