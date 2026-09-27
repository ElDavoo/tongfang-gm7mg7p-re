#!/usr/bin/env python3
"""Re-derive every data region in ec/annotations/data-regions.yaml from the
committed image, and label the scan sites that land inside one.

`bank-call-audit.md` §2 and §5 read several byte ranges as tables rather than
instructions. That reading lived in prose in one file, so every tool in this
directory rediscovered the same phantoms and every future write-up re-derived
them by hand -- which is how a phantom eventually gets reported as a finding.
`data-regions.yaml` makes the reading machine-readable, and this tool is what
holds it to the image.

**Annotate, never suppress.** A site inside a listed region is *labelled* and
still counted. Nothing here filters a row out, and no mode that would is
offered: a scan that dropped the phantoms would report a smaller number, and a
smaller number that nobody can audit is indistinguishable from absence -- the
`docs/findings.md` §4c failure this repository has two recorded instances of.
That is why `filter_regions()` does not exist and `refuse_filtering()` is
tested instead: the rule is a refusal in the tool, not a convention in a
comment, for the same reason `build_ec_decompile.py` refuses its `--out-`
paths.

**`--check` verifies shape, not meaning.** Per entry it recomputes the span's
stride agreement, the entry count, and the first/last decoded value from the
bytes, and fails on any mismatch -- the `check_register_counts.py` model. It
says nothing about what a table *means*; it settles none of
`bank-call-audit.md` §5's bucket C, and the 105 bucket-C sites that fall
outside every listed region (50 of them anchored) are untouched by a green run.
A zero here is "not found by this method", never "absent", which is the caveat
the YAML header carries and the one this file is most subject to: its entire
subject is one method's blind spots.

**`inferred` is about how the extent was chosen, not whether the bytes
agree.** Both `read-by-hand` and `inferred` are checked identically. An
`inferred-unchecked` entry is the third tier and is reported as *unchecked*
rather than as a pass, so a span the tool cannot reach never looks verified.

Usage:
    python3 data_regions.py --check
    python3 data_regions.py --self-test
    python3 data_regions.py --csv
    python3 data_regions.py --for-offset 0x055DC
    python3 data_regions.py ../firmware/GMxMGxx_11.800 --check
"""
import argparse
import csv
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
DEFAULT_YAML = os.path.join(EC, "annotations", "data-regions.yaml")
DEFAULT_FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")

# Closed vocabularies, because a value outside one is a region whose bytes
# would have to be guessed at. Refused rather than tolerated: an `addresses`
# row a reader cannot tell from a `be-words` row is two claims under one name,
# and the whole file is a claim about what was read.
SHAPES = ("ljmp-table", "be-words", "ff-triples", "addresses", "repeat-bytes")

CONFIDENCES = ("read-by-hand", "inferred", "inferred-unchecked")

# The `--csv` header. Kept a list so a column cannot be added to the output
# without it appearing here, and so `--check` and the console table below agree
# on what a row is. Which columns render as hex is stated here rather than
# inferred per row, because `stride` and `entries` are counts and rendering
# them `0x0003` would read as an address.
CSV_COLUMNS = ("name", "file_lo", "file_hi", "stride", "shape", "entries",
               "first_value", "last_value", "confidence")

# Offsets and decoded values are addresses and render as hex; the two counts
# do not. `first_value`/`last_value` are hex for every shape, including
# `repeat-bytes`, where the "value" is the pattern itself.
CSV_HEX = frozenset({"file_lo", "file_hi", "first_value", "last_value"})

# Keys every region must carry. `evidence` is the one that is not optional in
# spirit even when it is optional in YAML: the same rule
# `annotations/ghidra-functions.csv` follows, for the same reason. An entry
# with no evidence is a claim, not a finding.
REQUIRED = ("name", "file_lo", "file_hi", "stride", "shape", "entries",
            "first_value", "last_value", "confidence", "evidence",
            "established_by")

CAVEAT = (
    "This is a record of what was read, re-derived from the committed image by\n"
    "--check. It is not a claim that the rest of the image is code, and a region\n"
    "not listed here is not a claim that its bytes are instructions. A region\n"
    "label marks a site as a likely table entry read one byte out of frame; it\n"
    "does not clear the site, and a site outside every listed region is not a\n"
    "call. Nothing here is a behavioural claim and nothing was observed on\n"
    "hardware -- see docs/findings/ec-data-regions.md 'Limits'.\n"
)


def refuse_filtering() -> None:
    """Why this module offers no way to drop a region site.

    Called by the self-test and reachable from nowhere else, deliberately: the
    rule the issue asks for -- annotate, never suppress -- is only worth
    anything if it survives someone adding a `--only-in-data-regions` flag. It
    is here so the refusal is a function with a name rather than a sentence in
    a docstring, and so a future edit that adds a filtering mode has to delete
    this to do it.
    """
    raise SystemExit(
        "error: no output mode filters rows out of a scan. A site inside a\n"
        "       listed data region is labelled, not dropped: dropping it makes\n"
        "       a future scan's zero look like absence, which is the failure\n"
        "       docs/findings.md §4c records twice already.")


def be_word(d: bytes, off: int) -> int:
    """The 16-bit big-endian word at `off`."""
    return (d[off] << 8) | d[off + 1]


def entry_value(d: bytes, lo: int, off: int, stride: int, shape: str):
    """The decoded value of the entry at `off`, or None if the shape fails.

    None is the load-bearing return: it is how `--check` decides a span ends
    where it is declared to, and how a one-byte-shifted start is caught. A
    `ljmp-table` entry is a leading 0x02, a `ff-triples` entry a leading 0xFF,
    a `be-words` entry a word below the one before it, an `addresses` entry a
    word holding a common-area address, and a `repeat-bytes` entry a
    repetition of the span's first one.

    `lo` is the span's first offset and is load-bearing twice over. A
    `be-words` entry is defined by the entry *before* it, and at `lo` there is
    none -- comparing against the two bytes in front of the span instead would
    be comparing a word table against the last instruction that happens to
    precede it, which is how a well-formed table gets rejected because of
    whatever the compiler emitted above it. A `repeat-bytes` entry is defined
    against the first one for the same reason: its stride is the pattern
    length rather than a field width, so there is no per-entry decode at all.
    """
    if shape == "repeat-bytes":
        if d[off:off + stride] != d[lo:lo + stride]:
            return None
        return int.from_bytes(d[lo:lo + stride], "big")
    if off + 2 > len(d):
        return None
    if shape == "ljmp-table":
        return be_word(d, off + 1) if d[off] == 0x02 else None
    if shape == "ff-triples":
        return be_word(d, off + 1) if d[off] == 0xFF else None
    if shape == "be-words":
        w = be_word(d, off)
        return w if off == lo or w < be_word(d, off - stride) else None
    if shape == "addresses":
        # A common-area address, which is the *claim* this shape makes over
        # `be-words`: a word table of targets, not a descending run. The run
        # ends where the words stop being common-area addresses.
        w = be_word(d, off)
        return w if w < 0x8000 else None
    return None


def region_at(regions, off: int):
    """The first region containing `off`, or None. Half-open [file_lo, file_hi).

    None means "not in a listed region" and never "there is nothing there" --
    the caller prints it as `not listed`, not as an absence.
    """
    for r in regions:
        if r["file_lo"] <= off < r["file_hi"]:
            return r
    return None


def load(path: str = DEFAULT_YAML):
    """The region list, validated for the keys and vocabularies only.

    Deliberately not a check against the image: `--check` does that, and a
    loader that re-derived would make the file's own numbers unarguable in the
    wrong direction -- a wrong number in the YAML would be reported as the
    YAML's error rather than as a disagreement to look at.
    """
    with open(path) as fh:
        doc = yaml.safe_load(fh)
    regions = doc.get("regions") or []
    for r in regions:
        missing = [k for k in REQUIRED if k not in r]
        if missing:
            raise SystemExit(
                f"error: {path}: region {r.get('name', '?')!r} is missing "
                f"{', '.join(missing)}")
        # Present-but-empty is the case a key check alone lets through, and it
        # is the one that matters: `evidence: ""` is a claim with nothing
        # behind it, which is what the key exists to prevent.
        if not str(r["evidence"]).strip():
            raise SystemExit(
                f"error: {r['name']}: evidence is empty. A region with no "
                f"evidence is a claim, not a finding -- the same rule "
                f"annotations/ghidra-functions.csv follows.")
        if not str(r["established_by"]).strip():
            raise SystemExit(
                f"error: {r['name']}: established_by is empty, so the entry is "
                f"not re-derivable with a command line, which is the bar "
                f"CLAUDE.md sets for anything upstream is meant to hold up to.")
        if r["shape"] not in SHAPES:
            raise SystemExit(
                f"error: {r['name']}: shape {r['shape']!r} is not one of "
                f"{', '.join(SHAPES)}")
        if r["confidence"] not in CONFIDENCES:
            raise SystemExit(
                f"error: {r['name']}: confidence {r['confidence']!r} is not one "
                f"of {', '.join(CONFIDENCES)}")
    return regions


def check(d: bytes, regions) -> int:
    """Recompute each span from the image. Returns the number of problems.

    Per entry: the declared stride fits the declared span exactly, every
    entry decodes at the declared shape, the count matches, the first and
    last decoded values match, and -- the check that catches a shifted start
    -- the shape does *not* still hold one entry past the declared end.
    """
    problems = 0
    for r in regions:
        name, shape = r["name"], r["shape"]
        lo, hi, stride = r["file_lo"], r["file_hi"], r["stride"]

        if stride is None:
            print(f"{name}: stride is null, so the span cannot be "
                  f"re-derived -- see the confidence tier in the file header",
                  file=sys.stderr)
            problems += 1
            continue
        if (hi - lo) % stride:
            print(f"{name}: span 0x{lo:05X}-0x{hi:05X} is not a whole number "
                  f"of stride-{stride} entries", file=sys.stderr)
            problems += 1
            continue

        vals = []
        off = lo
        while off < hi:
            v = entry_value(d, lo, off, stride, shape)
            if v is None:
                what = ("the pattern breaks" if shape == "repeat-bytes"
                        else f"no {shape} entry")
                print(f"{name}: {what} at 0x{off:05X} (entry "
                      f"{(off - lo) // stride} of {(hi - lo) // stride})",
                      file=sys.stderr)
                problems += 1
                break
            vals.append(v)
            off += stride

        if len(vals) != r["entries"]:
            print(f"{name}: entries says {r['entries']}, the image has "
                  f"{len(vals)}", file=sys.stderr)
            problems += 1
        if vals:
            if vals[0] != r["first_value"]:
                print(f"{name}: first_value says "
                      f"0x{r['first_value']:04X}, the image has "
                      f"0x{vals[0]:04X}", file=sys.stderr)
                problems += 1
            if vals[-1] != r["last_value"]:
                print(f"{name}: last_value says 0x{r['last_value']:04X}, the "
                      f"image has 0x{vals[-1]:04X}", file=sys.stderr)
                problems += 1

        # The declared end has to be where the run actually stops. Without
        # this a span that stops early passes every check above, which is the
        # half of `--check` that a shifted start would otherwise get for free.
        past = entry_value(d, lo, hi, stride, shape)
        if past is not None:
            print(f"{name}: the {shape} shape still holds at the declared end "
                  f"0x{hi:05X}, so the span is declared short", file=sys.stderr)
            problems += 1
    return problems


def unchecked(regions):
    """Regions `--check` cannot reach, so it can only report rather than pass.

    An `inferred-unchecked` entry is the file saying out loud that its edge is
    a reading `--check` has no way to test. It is returned rather than counted
    as a problem so a green run is not a lie about it: the count says how many
    regions were verified, and this says how many were not.
    """
    return [r for r in regions if r["confidence"] == "inferred-unchecked"]


def self_test(d: bytes, regions) -> int:
    """The refusals, and an oracle the tool did not write for itself.

    Both halves, per this repository's standing argument that a check which
    has quietly stopped rejecting everything looks exactly like a check that
    is working. The refusals are where a wrong file would show up; the oracle
    is where a right file on a wrong image would.
    """
    bad = 0
    print("data_regions.py --self-test")

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

    # --- the refusals -----------------------------------------------------
    expect("a read-by-hand region with no evidence is refused",
          refuses(load, write_yaml([dict(regions[0], evidence="")])))
    expect("a region with no evidence key at all is refused",
          refuses(load, write_yaml([{k: v for k, v in regions[0].items()
                                     if k != "evidence"}])))
    expect("a confidence outside the vocabulary is refused",
          refuses(load, write_yaml([dict(regions[0], confidence="probably")])))
    expect("a shape outside the vocabulary is refused",
          refuses(load, write_yaml([dict(regions[0], shape="mystery-bytes")])))
    expect("the annotate-never-suppress refusal is a refusal",
          refuses(refuse_filtering))

    # --- a shifted start, which is the mutation this file exists for ------
    for r in regions:
        shifted = dict(r, file_lo=r["file_lo"] + 1)
        expect(f"{r['name']}: a span shifted one byte later is refused",
              check_one(d, [shifted]) > 0)
    for r in regions:
        early = dict(r, file_hi=r["file_hi"] - r["stride"])
        expect(f"{r['name']}: a span cut one entry short is refused",
              check_one(d, [early]) > 0)

    # --- the oracle --------------------------------------------------------
    # Transcribed from bank-call-audit.md, NOT from this file: the audit names
    # the phantoms and the corrected §5 says which side of a region each one
    # falls on. A tool that graded its own map against itself would pass
    # whatever the map said.
    for off, want_in in ORACLE:
        got = region_at(regions, off)
        expect(f"0x{off:05X} is {'inside' if want_in else 'outside'} a region",
              (got is not None) == want_in,
              f"got {got['name'] if got else 'not listed'}")
    for off, want in ORACLE_REGION:
        got = region_at(regions, off)
        expect(f"0x{off:05X} resolves to {want}",
              got is not None and got["name"] == want,
              f"got {got['name'] if got else 'not listed'}")

    # --- the committed file passes its own check --------------------------
    expect("the committed regions pass --check", check(d, regions) == 0)
    expect("no region is unchecked today", not unchecked(regions))

    print(f"{'all checks passed' if not bad else f'{bad} FAILED'}")
    return 1 if bad else 0


# Transcribed from ec/annotations/bank-call-audit.md, corrected in place for
# this issue. 0x055DC and 0x00381 are the audit's two named table phantoms;
# 0x021C6 is the one the audit called a table entry and is not -- §5's
# correction is what these three lines encode.
ORACLE = [
    (0x055DC, True),    # bank-call-audit.md §2: inside the 0x55A8 word table
    (0x00381, True),    # §5: inside the ljmp dispatch table, one byte out of frame
    (0x021C6, False),   # §5 as corrected: 0x12 bytes past the 0x219C triples
    (0x00686, True),    # §1 bucket-C table, inside the 0x0656 address table
    (0x06E83, True),    # §1 bucket-C table, inside the 0x6E7D word table
    (0x006E78, True),   # inside the 0x6E65 repeat-pattern region
]

ORACLE_REGION = [
    (0x055DC, "common-055a8-be-words"),
    (0x00381, "common-032f-ljmp-table"),
    (0x00686, "common-0656-address-table"),
    (0x06952, "common-690b-ff-triples"),
    (0x06E83, "common-6e7d-be-words"),
    (0x006E78, "common-6e65-repeat-bytes"),
]


def check_one(d: bytes, regions) -> int:
    """`check()` with its diagnostics off, for the self-test's mutations.

    A shifted span prints a line per problem, and a self-test that prints six
    expected failures buries the one that is unexpected. The count is what the
    test asserts on.
    """
    saved, sys.stderr = sys.stderr, open(os.devnull, "w")
    try:
        return check(d, regions)
    finally:
        sys.stderr.close()
        sys.stderr = saved


def write_yaml(regions) -> str:
    """A throwaway YAML file holding `regions`, for the refusal cases."""
    import tempfile
    fh = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    yaml.safe_dump({"regions": regions}, fh)
    fh.close()
    return fh.name


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: the committed one)")
    ap.add_argument("--regions", default=DEFAULT_YAML,
                    help="data-regions.yaml to read (default: the one beside "
                         "this tool)")
    ap.add_argument("--check", action="store_true",
                    help="re-derive every region from the image and fail on "
                         "any mismatch")
    ap.add_argument("--self-test", action="store_true",
                    help="the refusals, the shifted-span mutations, and the "
                         "audit's named phantoms")
    ap.add_argument("--csv", action="store_true",
                    help="the region table as CSV on stdout")
    ap.add_argument("--for-offset", type=lambda s: int(s, 0),
                    help="name the region containing one file offset")
    args = ap.parse_args()

    regions = load(args.regions)

    if args.for_offset is not None:
        r = region_at(regions, args.for_offset)
        # The three-way answer is the point: a caller must be able to tell
        # "inside a region" from "outside every listed region" without
        # concluding the latter means the bytes there are instructions.
        print(f"0x{args.for_offset:05X}  "
              f"{r['name'] if r else 'not listed'}"
              f"{'  (entry-aligned)' if r and (args.for_offset - r['file_lo']) % r['stride'] == 0 else ''}")
        return 0

    if args.csv:
        w = csv.writer(sys.stdout)
        w.writerow(CSV_COLUMNS)
        for r in regions:
            w.writerow([f"0x{r[c]:04X}" if c in CSV_HEX else r[c]
                        for c in CSV_COLUMNS])
        return 0

    if args.self_test:
        return self_test(open(args.firmware, "rb").read(), regions)

    if args.check:
        print(CAVEAT)
        d = open(args.firmware, "rb").read()
        problems = check(d, regions)
        pending = unchecked(regions)
        for r in regions:
            state = ("unchecked" if r["confidence"] == "inferred-unchecked"
                     else r["confidence"])
            print(f"  {r['name']:28s} 0x{r['file_lo']:05X}-0x{r['file_hi']:05X}  "
                  f"{r['stride']}-byte {r['shape']:12s} {r['entries']:>3} entries  "
                  f"{state}")
        if pending:
            print(f"\n{len(pending)} region(s) are inferred-unchecked: "
                  f"{', '.join(r['name'] for r in pending)}")
        if problems:
            print(f"\n{problems} problem(s)", file=sys.stderr)
        else:
            print(f"\nall {len(regions)} regions re-derived from "
                  f"{os.path.basename(args.firmware)}")
        return 1 if problems else 0

    ap.error("give --check, --self-test, --csv or --for-offset")
    return 1


if __name__ == "__main__":
    sys.exit(main())
