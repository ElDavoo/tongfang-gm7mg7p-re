#!/usr/bin/env python3
"""Adjudicate the call-target seeds `build_ec_decompile.py` mints inside a longer
instruction, and publish the adjudication as a committed CSV.

**The question.** `call_target_seeds()` turns every census *target* into a Ghidra
function entry, and the bytes at a target are never tested for being an
instruction boundary. Issue #1110 built the predicate that test needs --
`audit_call_targets.earlier_record()`, the record that starts one or two bytes
back and spans a site -- and wired it to nothing. This tool is the wiring: it
applies that predicate **at the target address** and decides each affected seed
against the committed bytes.

**The predicate is applied at the target, not at the census row's site.** The
committed `earlier_record` column describes each row's *call site*, which is a
different question with a different answer; reading that column as though it
described the seed is the confusion this tool exists to prevent, and the CSV
carries the target's own covering record rather than the row's.

**Three answers, and the third is the honest one.** For each seed the predicate
fires on, the walk decides which of the three applies:

  `mid-instruction`    no *majority* of the anchors lands on the address --
                       at least half of them step over it -- and a committed
                       listing sits there to be wrong about, so that listing's
                       first instruction is a decode of the covering record's
                       operand or displacement byte. It is a majority test and
                       not a unanimous one: a minority of anchors landing here
                       is what `0x1706`'s 2 of 24 is, and `bank1 0xF018` is
                       the population's only tie, so this class does not mean
                       no walk reaches the address.
  `entry-under-walk`   a majority of the walks *do* land on the address, so the
                       framing and the predicate disagree and the seed may be a
                       real entry after all. `common 0x012F` is the worked
                       example: it trips the predicate, because `0x012E` pairs as
                       `b0 90`, and it is a hand-decoded real routine whose
                       listing survives today.
  `unread`             the predicate fires but there is no committed listing to
                       compare against and no walk to settle it. Named, not
                       decided, and the point of publishing them rather than
                       filtering is that "the predicate fires" is not "the entry
                       is wrong", and the blind spot is a class rather than an
                       absence.

**"Majority" is a stated choice among named alternatives, not a result.** The
walk is `disasm8051.converges_from()`, which returns how many of its 24 anchors
land on the address versus step over it, and `0x1706` is why the count cannot
be read as either half: 2 of 24 anchors land there and 22 step over it, which is
the same shape as a site preceded by data. Three thresholds were measured over
the population and each is asserted to *lose* somewhere in
`test_call_target_seed_frames.py`; `converges_from()`'s own docstring says a
site everybody syncs onto is not thereby real, so the score picks a
better-evidenced reading and never adjudicates the seed.

**The verdicts are about framing only.** Nothing here was observed on hardware,
nothing was observed in Windows, and no sentence in the write-up claims the EC
executes any of these bytes. No register `status:` moves and no row of
`ghidra-functions.csv` is added or removed, because a framing disagreement is
not a claim about what the firmware does.

**Why the population is published rather than filtered.** `seed_rows()` sorts
seeds with `annotation` ahead of `call-target` precisely so a byte-scan target
one byte into a real instruction cannot swallow the evidence-backed entry inside
it, and `common/012F.asm` survives today on exactly that ordering. So this tool
**reports** every affected seed and `call_target_seeds()` **labels** what it
emits; neither drops a row. §1's byte-scan upper bound is what every count in
`../annotations/bank-call-audit.md` rests on, and a filter that discarded rows
would destroy the ability to say what they contained.

**Where the census's two writers and the unattributed bucket go.** Bucket C --
140 rows whose target lands at or above `0x8000` seen from the common area, so
no byte says which bank is mapped -- is named by nobody and is not seeded into
either bank, so it is not in this population. That is #48's open question and
this tool does not touch it. The rows are counted and reported separately rather
than folded in, so the difference between "no byte resolves this" and "the byte
resolves to an address inside an instruction" stays visible.

Usage:
    python3 call_target_seed_frames.py
    python3 call_target_seed_frames.py --write
    python3 call_target_seed_frames.py --check
    python3 call_target_seed_frames.py --self-test
"""
import argparse
import collections
import csv
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from disasm8051 import OPCODE_LEN, converges_from
from trace_xdata_refs import offset_for_runtime

FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
ANNOTATIONS = os.path.join(REPO, "ec", "annotations")
INDEX = os.path.join(REPO, "ec", "decompiled", "index.csv")
FRAMES = os.path.join(ANNOTATIONS, "call-target-seed-frames.csv")

# The published population, as this tool writes it. A closed vocabulary and a
# fixed column order, both of them the tool's own rather than read back from the
# file: a CSV whose header is whatever it happens to hold is a CSV whose meaning
# is whatever the last writer typed, and `--check` compares every cell of every
# row against this list.
FRAME_COLUMNS = ["program", "target", "region", "verdict", "covering_record",
                 "onto", "over"]

# The three verdicts, and no fourth. One outside this vocabulary is a bug in
# this file rather than a new kind of framing, and the `--self-test` case that
# asserts the rule reaches no fourth is what holds it.
VERDICTS = ("mid-instruction", "entry-under-walk", "unread")

# How far back the framing walk looks. `disasm8051.converges_from()`'s own
# default, carried here rather than restated as a literal at the call site so
# the number has one home.
BACK = 24

# The file-offset floor of each region in the committed image, for clipping the
# walk window to the region the seed's own bytes fall in. The bytes before a
# bank's `0x8000` are the common area and the bytes before the common area's
# `0x0000` are the previous image's tail, so a window that ran past either edge
# would be reading a different address space and calling the result a framing.
#
# These are the `lo` values from `trace_xdata_refs.REGIONS`, transcribed rather
# than read from that table because the walk needs them as a plain lookup keyed
# by region name and importing the table would mean matching its five-region
# shape against a three-region question. `--self-test` holds them against the
# image: a floor that moved would let a window read another region's bytes and
# still produce a plausible pair.
REGION_FLOOR = {"common": 0x00000, "bank0": 0x08000, "bank1": 0x10000}


def audit_module():
    """`audit_call_targets`, loaded by path.

    Deferred and by-path because the tool directory is not necessarily on
    `sys.path` for a caller that imported this file from elsewhere, and because
    `audit_call_targets` imports `disasm8051`, `find_banks` and
    `trace_xdata_refs` by bare module name -- so the path has to be set up
    before it is loaded, the shape `test_earlier_record_column.py` uses for the
    same reason."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    spec = importlib.util.spec_from_file_location(
        "audit_call_targets", os.path.join(HERE, "audit_call_targets.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exporter():
    """`build_ec_decompile`'s two seed rules, imported on first use.

    `call_target_seeds()` is the *attribution* -- which census target belongs to
    which bank program -- and re-deriving it here would be a second definition
    of the very population this tool is about. Deferred rather than module-level
    because `build_ec_decompile.py --check` imports *this* module for the
    ratchet, and an import in both directions at module scope is a cycle. Both
    functions are pure and read nothing but the rows handed to them, so the
    second module object a deferred import creates while the exporter runs as
    `__main__` answers identically -- which is what makes importing them cheaper
    than keeping a second copy of the attribution."""
    from build_ec_decompile import call_target_rows, call_target_seeds
    return call_target_rows, call_target_seeds


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def population():
    """Every distinct (program, target) call-target seed, and the unattributed
    count beside it.

    Two programs' worth, because `call_target_seeds()` is asked per bank and the
    common area is seeded into both on purpose; a common-area target is
    therefore one address and two seeds, and the difference is the same
    `seed_rows()`'s own per-program de-dup keeps. `region` is not a third input:
    it is read off the target, since a target below `0x8000` is in the common
    area and one at or above it is in the window of the bank whose row named it.

    The unattributed bucket is returned rather than dropped so `--check` can say
    how many rows named no bank and stayed unseeded. That is a different fact
    from the one this tool adjudicates -- no byte resolves those targets at all,
    rather than resolving them to an address inside an instruction -- and folding
    it in would make the second look like the first."""
    call_target_rows, call_target_seeds = exporter()
    census = call_target_rows()
    seeds = set()
    unattributed = set()
    for bank in ("bank0", "bank1"):
        mine, unattr = call_target_seeds(bank, census)
        for target, _basis in mine:
            seeds.add((bank, target))
        unattributed.update(target for target, _basis in unattr)
    return seeds, len(unattributed)


# The programs the seed population is drawn from, and so the ones whose index
# rows may answer "does a committed listing sit at this address". `pd` is the
# separate ITE8850-PD image and is **not** in this set even though its addresses
# are the same numbers: `pd 0x1229` is the only index row at that address, and a
# lookup that counted it would file a main-EC seed that has no listing of its own
# as `mid-instruction` on the strength of another program's bytes.
MAIN_EC_PROGRAMS = ("common", "bank0", "bank1")


def index_rows():
    """The committed index, keyed by `(program, addr)` and by address alone.

    The second key is the one that matters here, and it exists because of what
    `join_index()` does: a common-area function is folded into one `common` row
    **only where both bank programs agree** on its address, name and size, and
    where they disagree both are kept under `bank0` and `bank1` and flagged. So
    "a common-area address is filed under `common`" is true for most of them and
    false for the rest -- `bank0 0x031C` and `bank0 0x703A` are common-area
    addresses that kept their bank-scoped rows, and a lookup keyed on the folded
    name alone finds no listing at either and would file a seed that does have
    one as `unread`.

    So the lookup is by address, and `MAIN_EC_PROGRAMS` is what narrows it: the
    by-address key carries every program in the index including the PD image,
    whose rows share this image's address numbers and are a different program's
    bytes."""
    rows, by_addr = {}, {}
    for row in read_csv(INDEX):
        addr = row["addr"].upper().replace("0X", "")
        rows[(row["program"], addr)] = row
        by_addr.setdefault(addr, []).append(row)
    return rows, by_addr


def listing_at(by_addr, target):
    """The committed main-EC listing at `target`, or None.

    `pd` is excluded on purpose and the reason is the one case that makes it
    load-bearing: `pd 0x1229` is the *only* index row at that address, so a
    lookup that did not scope by program would find it and report a main-EC seed
    with no listing of its own as `mid-instruction`.

    The index's own `addr` spelling: every address in `index.csv` is four hex
    digits, both the common area's and the bank windows', so one format covers
    both and the mask a 16-bit target would want is unnecessary. `index_rows()`
    keys on the address exactly as the file spells it."""
    return [row for row in by_addr.get("%04X" % target, ())
            if row["program"] in MAIN_EC_PROGRAMS] or None


def verdict_for(onto, over, has_listing):
    """The framing class for one seed. The rule, and nothing else it decides.

    `entry-under-walk` when a majority of the anchors land on the address, on
    `converges_from()`'s own reading of its pair -- "read the pair, not either
    half", and the pair is (onto, over). `mid-instruction` when no majority
    lands on it -- at least half step over -- and a committed listing exists
    for the address to be wrong about. `unread` when it does not, which is the
    residual: the predicate fires, and nothing committed is there to be wrong.
    Which class is the largest is a property of the population and `--check`
    prints it; it is not a property of the rule.

    The ordering matters and is why `0x012F` is in `--self-test`: a rule that
    tested the listing first would file a real entry whose bytes happen to trip
    the predicate as `mid-instruction` on the strength of the listing alone, and
    the walk is the only evidence here that speaks to framing."""
    if onto > over:
        return "entry-under-walk"
    if has_listing:
        return "mid-instruction"
    return "unread"


def frames(fw):
    """The published population: one row per seed the predicate fires on.

    Only the affected seeds are written. The seeds the predicate does not fire on
    are not a verdict this tool has anything to say about -- the census target is
    on an instruction boundary, or nothing one or two bytes back spans it -- and a
    file carrying a row per seed would put the bulk of it in front of every reader
    and in the diff of every re-derivation, to say nothing the affected rows do
    not already say.

    Sorted by `(program, target)` with the addresses read as numbers, so a
    regenerated file is byte-identical to the committed one rather than
    reordered by a CSV writer's idea of string order: `0x1000` before `0x2000`
    is the same either way, and `0x10000` before `0x2000` is not."""
    earlier_record = audit_module().earlier_record
    seeds, unattributed = population()
    _index, by_addr = index_rows()
    rows = []
    for program, target in sorted(seeds):
        region = "common" if target < 0x8000 else program
        off = offset_for_runtime(target, region)
        if off is None:
            # Named, not counted: `offset_for_runtime()` returning None means no
            # byte resolves this target, which is a different fact from the one
            # the predicate answers and is reported by the caller rather than
            # filed as an empty verdict. No seed reaches here today -- the
            # unattributed bucket is where an unresolvable target goes, and it
            # is not seeded -- so this is a refusal rather than a measurement.
            continue
        record = earlier_record(fw, off, REGION_FLOOR[region])
        if not record:
            continue
        onto, over = windowed_walk(fw, off, min(BACK, off - REGION_FLOOR[region]))
        listing = listing_at(by_addr, target)
        rows.append({"program": program, "target": "0x%04X" % target,
                     "region": region,
                     "verdict": verdict_for(onto, over, listing is not None),
                     "covering_record": record,
                     "onto": str(onto), "over": str(over)})
    return rows, unattributed, len(seeds)


# How far past the address the walk's window reaches. The buffer is the image's
# own bytes rather than a zero-padded one, so a helper reading `d[i+1]` or
# `d[i+2]` past the last anchor sees this firmware's bytes and not a `nop` the
# window invented. One longest instruction covers that read.
#
# Whether the padding changes a verdict is a property of the population and not
# of this constant: on the committed census no anchor of any published seed's
# window names an inline-argument or case-table block, which is the only way
# `converges_from()`'s step can read past the address. So the padding changes no
# verdict today, and
# `test_call_target_seed_frames.py::test_the_window_agrees_with_a_whole_image_walk`
# holds the strong form -- the windowed walk equals a walk over the whole image
# at every published seed -- which is the property that matters and the one that
# would catch a census introducing such an anchor.
OPCODE_SLACK = max(OPCODE_LEN)


def windowed_walk(fw, off, back):
    """`converges_from()` over the window `[off - back, off + OPCODE_SLACK)`.

    The window starts at the region's own floor -- the caller passes a `back` no
    larger than `off - lo` -- so no anchor reads a neighbouring address space.
    That is the one edge where a slip is invisible in the output: the bytes
    before a bank's `0x8000` are the common area's, and they decode perfectly
    well, so a window that ran past the floor would produce a plausible pair and
    no complaint.

    The other edge is padded from the committed image rather than with zeros, so
    a helper reading forward sees this firmware's bytes rather than a `nop` the
    window invented. See `OPCODE_SLACK` for what that padding does and does not
    currently change."""
    return converges_from(fw[off - back:off + OPCODE_SLACK], back)


def read_labels(path=FRAMES):
    """`{(program, target): verdict}` from the published CSV, or {} when it is
    not there or is not this tool's.

    What `build_ec_decompile.py` reads so a caller can print what it is seeding
    rather than seed it blind. An unreadable file is `{}` and not an error: the
    labels are a report, and the file's absence is `file_problems()`'s business --
    failing a build over a missing *report* would make an optional artefact a
    precondition of an export that does not need it."""
    if not os.path.isfile(path) or file_problems(path):
        return {}
    return {(r["program"], r["target"]): r["verdict"] for r in read_csv(path)}


def write_frames(rows, path=FRAMES):
    """(Re)write the committed CSV from the rows derived here.

    The file is this tool's output and is regenerable in one command, the way
    `../ghidra/cross-decoder.csv` is. It is committed because the adjudication
    is a reading a reader should not have to re-run to check, and because
    `--check`'s ratchet needs a published population to compare the derivation
    against -- a ratchet with no file behind it is an assertion that the tool
    agrees with itself."""
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FRAME_COLUMNS, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in FRAME_COLUMNS})
    return path


def frame_problems(committed, derived, path=FRAMES):
    """The committed population against this run's derivation. -> problems.

    The ratchet, and it fails on any difference rather than on the *content* of
    a verdict: a mid-instruction seed appearing, a verdict being quietly
    reverted, and a row that is in the file and no longer derived all look the
    same from the outside, and all three are the thing this exists to catch.

    Each problem **names the seed** -- program, target, region, the covering
    record -- and the file to regenerate. A bare "population differs" is a
    failure a reader has to go and reproduce before they can act on it, and the
    one case this check exists for is a single seed added to a census.

    A live assertion ("fail on any seed the predicate says is mid-instruction")
    is deliberately not what this is: the committed tree already holds hundreds
    of them, `build_ec_decompile.py --check` runs in the cheap gate, and a check
    that cannot go green on the tree it ships with is not a guard. The live
    assertion replaces this in the pull request that lands the rebuild and empties
    the list -- which needs `--mode rebuild-project`, and two branches that both
    rebuild the 7 MB EC database cannot merge.

    The committed file's *readability* is a separate question with its own
    problems (`file_problems`), so a header that is not this tool's is reported
    once rather than as one difference per row."""
    rel = os.path.relpath(path, REPO)
    problems = []
    mine = {(r["program"], r["target"]): r for r in derived}
    theirs = {(r["program"], r["target"]): r for r in committed}
    for key in sorted(set(theirs) - set(mine)):
        problems.append(
            "%s %s (region %s) is adjudicated in %s and the predicate no longer "
            "fires on it: covering record %r. Either the census changed or the "
            "rule did -- re-run with --write and say which in the same commit."
            % (key[0], key[1], theirs[key].get("region", "?"), rel,
               theirs[key].get("covering_record", "")))
    for key in sorted(set(mine) - set(theirs)):
        row = mine[key]
        problems.append(
            "%s %s (region %s) is a seed the predicate fires on and %s carries "
            "no verdict for it: covering record %r. Re-run with --write."
            % (key[0], key[1], row.get("region", "?"), rel,
               row.get("covering_record", "")))
    for key in sorted(set(mine) & set(theirs)):
        for column in FRAME_COLUMNS:
            if theirs[key].get(column, "") != mine[key].get(column, ""):
                problems.append(
                    "%s %s: %s is %r in %s and %r now. Re-run with --write."
                    % (key[0], key[1], column, theirs[key].get(column, ""), rel,
                       mine[key].get(column, "")))
    return problems


def file_problems(path=FRAMES):
    """Whether the committed population can be compared at all. -> problems.

    Separate from the comparison because a file that is absent or carries a
    header this tool did not write has no rows to compare, and folding that into
    one message per row would report hundreds of differences that all mean "you
    are looking at the wrong file". The header is asserted rather than assumed
    for the reason `build_ec_decompile.py` asserts its own: this file is what a
    person or an agent edits to change a verdict, and a column that moved is a
    change in what every row means."""
    rel = os.path.relpath(path, REPO)
    if not os.path.isfile(path):
        return ["no %s: the adjudication has to be published for --check to "
                "compare anything against, and a ratchet with no file behind it "
                "is this tool agreeing with itself. Run with --write." % rel]
    with open(path, newline="") as f:
        header = next(csv.reader(f), None)
    if header != FRAME_COLUMNS:
        return ["%s: header is %r, not this tool's %d-column %s"
                % (rel, header, len(FRAME_COLUMNS), ",".join(FRAME_COLUMNS))]
    return []


def summary_line(rows, total, unattributed):
    """The population, as one line a reader of a `--check` run sees.

    The verdict counts are the finding and belong here rather than in a README
    or a docstring headline, where they would be a figure nothing regenerates.
    `docs/findings/call-target-seed-frames.md` carries them beside the command
    that prints this line."""
    tally = collections.Counter(r["verdict"] for r in rows)
    return ("%d call-target seed(s) derived, %d the predicate fires on "
            "(%s), %d distinct target(s) named no bank and were not seeded"
            % (total, len(rows),
               ", ".join("%d %s" % (tally[v], v) for v in VERDICTS if tally[v]),
               unattributed))


# --------------------------------------------------------------------------
# Self-test. Scratch bytes, not addresses in the firmware -- the reason
# `test_walk_branch_arms.py` gives: a fixture anchored in the image keeps
# testing what it was written to test only until those bytes change. The one
# exception is the `0x012F` counter-case, which is *about* those bytes and
# cannot be stood in for by a buffer that has to be arranged to reproduce them.
# --------------------------------------------------------------------------

# A scratch region shaped like the two ways a seed's framing comes out. Offset 2
# is one byte into the `00 74` pair, so every anchor walks over it; offset 3 is
# where the anchors land, and the gap between the two is the contrast the whole
# rule turns on. The bytes past offset 3 are never read by either case and are
# there so a decode stepping over an address still has real bytes to step over.
SCRATCH = bytes((0x00, 0x74, 0x22, 0x02, 0x11, 0x00, 0x90, 0x17))


def self_test():
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print("  %s  %s" % ("ok  " if cond else "FAIL", label)
              + ("  (%s)" % detail if detail and not cond else ""))
        if not cond:
            ok = False

    print("call_target_seed_frames.py --self-test")
    fw = open(FIRMWARE, "rb").read()
    earlier_record = audit_module().earlier_record
    scratch = tempfile.TemporaryDirectory()
    work = scratch.name

    # The rule, on each verdict's own shape. The first two cases share every
    # byte and differ only in whether a listing exists, so a rule that consulted
    # the listing before the walk would pass both while filing a real entry whose
    # bytes trip the predicate in the wrong class.
    onto, over = windowed_walk(SCRATCH, 2, 2)
    check("a site every anchor steps over is not entry-under-walk",
          onto <= over and verdict_for(onto, over, True) == "mid-instruction",
          "%d/%d" % (onto, over))
    check("the same site with no listing is unread, and the walk is not what "
          "changed it", verdict_for(onto, over, False) == "unread")
    onto, over = windowed_walk(SCRATCH, 3, 3)
    check("a site the anchors land on is entry-under-walk",
          onto > over and verdict_for(onto, over, True) == "entry-under-walk",
          "%d/%d" % (onto, over))
    check("no verdict outside the vocabulary is reachable",
          all(v in VERDICTS for v in (verdict_for(0, 0, True),
                                      verdict_for(1, 0, True),
                                      verdict_for(0, 0, False))))

    # The counter-case that makes the rule honest, on the committed bytes: a
    # seed that trips the predicate and is a real entry anyway. A rule that
    # dropped every trip -- or that filed every trip as `mid-instruction` -- goes
    # red here, and the suite asserts the same case against the image.
    twelve_f = 0x012F
    check("0x012F trips the predicate (0x012E pairs as `b0 90`)",
          audit_module().earlier_record(fw, twelve_f, 0) != "",
          audit_module().earlier_record(fw, twelve_f, 0))
    onto, over = windowed_walk(fw, twelve_f, BACK)
    check("0x012F's walk lands on it, so the rule keeps it",
          verdict_for(onto, over, True) == "entry-under-walk",
          "%d/%d" % (onto, over))

    # The window is clipped to the region floor and padded from real bytes. A
    # window running past either edge would be reading a neighbouring address
    # space; a window padded with zeros would be decoding bytes this firmware
    # does not contain, and the two-byte `00 74` at the image's own start is
    # exactly the case that tells them apart.
    floor = REGION_FLOOR["common"]
    first_seed = floor + 1
    back = min(BACK, first_seed - floor)
    onto, over = windowed_walk(fw, first_seed, back)
    check("a seed at the region's own floor is walked without reading before it",
          onto + over == back, "%d/%d" % (onto, over))
    # The floors themselves, against the region table they are transcribed from.
    # A floor that moved would let a window read a neighbouring region's bytes --
    # and the common area decodes perfectly well, so nothing downstream would say
    # so. Clean first, for the reason every structural case in this repository
    # puts it first: a guard exercised only on bad input cannot tell "clean" from
    # "never ran".
    from trace_xdata_refs import REGIONS as _REGIONS
    _mine = {name: lo for name, lo, _hi, _base, _how in _REGIONS}
    check("every region's floor here is the one the region table gives",
          all(_mine.get(name) == value for name, value in REGION_FLOOR.items()),
          str(REGION_FLOOR))
    check("and no region this tool walks is missing from that table",
          set(REGION_FLOOR) <= set(_mine), str(sorted(set(REGION_FLOOR))))
    # The bytes the walk reaches *past* the address are the image's own, and
    # there are at least as many of them as the longest instruction is long --
    # otherwise the anchor that lands inside a spanning instruction decodes it
    # off the end of the buffer, which is the case this predicate fires on.
    past = fw[first_seed:first_seed + OPCODE_SLACK]
    check("the window reaches past the address by the longest instruction, so "
          "one spanning it decodes whole",
          len(past) == OPCODE_SLACK >= max(OPCODE_LEN),
          "%d byte(s) past the address, longest instruction is %d"
          % (len(past), max(OPCODE_LEN)))

    # The ratchet, seen to fail. A check that has never been seen to reject is
    # not known to reject, and the shape exercised here is the one it exists for:
    # a seed the committed file carries and the derivation no longer produces.
    rows, unattributed, total = frames(fw)
    check("a committed file that agrees with the derivation has no problem",
          not frame_problems(rows, rows), str(frame_problems(rows, rows)[:2]))
    first = (rows[0]["program"], rows[0]["target"])
    reverted = [dict(r) for r in rows]
    reverted[0] = dict(reverted[0], verdict="mid-instruction"
                        if reverted[0]["verdict"] != "mid-instruction"
                        else "entry-under-walk")
    got = frame_problems(reverted, rows)
    check("a verdict the derivation does not produce is reported",
          len(got) == 1 and first[0] in got[0] and first[1] in got[0],
          str(got[:2]))
    check("the problem names the seed and the file to regenerate, rather than "
          "raising a bare error",
          got and first[1] in got[0] and "--write" in got[0], str(got[:1]))
    invented = list(rows) + [{"program": "bank0", "target": "0xFFF0",
                              "region": "common", "verdict": "unread",
                              "covering_record": "0x0FFEE 74 22 mov a,#0x22",
                              "onto": "0", "over": "4"}]
    got = frame_problems(rows, invented)
    check("a derived seed the committed file does not carry is reported",
          len(got) == 1 and "0xFFF0" in got[0], str(got[:2]))
    got = frame_problems([dict(r) for r in rows], [dict(r) for r in rows[:-1]])
    check("a row the derivation no longer produces is reported, and it names "
          "the record that used to span it",
          len(got) == 1 and rows[-1]["target"] in got[0]
          and rows[-1]["covering_record"] in got[0], str(got[:2]))
    check("a missing file is reported once, before any per-row comparison",
          len(file_problems(path=os.path.join(work, "absent.csv"))) == 1)
    write_frames(rows, os.path.join(work, "wrong-header.csv"))
    with open(os.path.join(work, "wrong-header.csv"), "w", newline="") as f:
        f.write("program,target\nbank0,0x0002\n")
    bad = file_problems(path=os.path.join(work, "wrong-header.csv"))
    check("a header that is not this tool's is reported once, not once per row",
          len(bad) == 1 and "header" in bad[0], str(bad))

    # The population's own shape, held as relations rather than as a census: a
    # figure of the tree is a value every landing edit has to touch, and these
    # are the properties that make the counts around them mean what they say.
    check("every published row carries a verdict from the vocabulary",
          all(r["verdict"] in VERDICTS for r in rows))
    check("every published row names the record that spans it",
          all(r["covering_record"] for r in rows))
    check("every published row is a seed, and none is written twice",
          len({(r["program"], r["target"]) for r in rows}) == len(rows))
    check("the walk counted every anchor it was given, on every row",
          all(int(r["onto"]) + int(r["over"]) > 0 for r in rows))
    check("only the affected seeds are published",
          0 < len(rows) <= total, "%d of %d" % (len(rows), total))
    check("every published row is one the predicate still fires on",
          all(earlier_record(fw, offset_for_runtime(int(r["target"], 16),
                                                    r["region"]),
                             REGION_FLOOR[r["region"]])
              for r in rows),
          "a published row the predicate no longer fires on")

    print("  %s" % summary_line(rows, total, unattributed))
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    scratch.cleanup()
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="compare the committed population against a fresh "
                         "derivation and fail, naming the seed")
    ap.add_argument("--write", action="store_true",
                    help="(re)write the committed population CSV")
    ap.add_argument("--self-test", action="store_true",
                    help="known-answer assertions, on scratch bytes and on the "
                         "one committed site whose bytes are the claim")
    args = ap.parse_args(argv)
    if args.write and args.check:
        raise SystemExit("error: --write regenerates %s from the current tree; "
                         "it cannot be combined with --check, which compares "
                         "against it. Run them separately."
                         % os.path.relpath(FRAMES, REPO))
    if args.self_test:
        return self_test()
    fw = open(FIRMWARE, "rb").read()
    rows, unattributed, total = frames(fw)
    if args.write:
        path = write_frames(rows)
        print("wrote %s: %d row(s)"
              % (os.path.relpath(path, REPO), len(rows)))
        print("  %s" % summary_line(rows, total, unattributed))
        return 0
    if args.check:
        print("call_target_seed_frames.py --check")
        print("  %s" % summary_line(rows, total, unattributed))
        problems = file_problems()
        if not problems:
            problems = frame_problems(read_csv(FRAMES), rows)
        for problem in problems[:10]:
            print("  FAIL  %s" % problem)
        if len(problems) > 10:
            print("  FAIL  ... and %d more population problem(s)"
                  % (len(problems) - 10))
        print("  all checks passed" if not problems else "  FAILURES ABOVE")
        return 0 if not problems else 1
    for row in rows:
        print("  %-6s %s %-16s %-9s %s  %d/%d"
              % (row["program"], row["target"], row["verdict"], row["region"],
                 row["covering_record"], int(row["onto"]), int(row["over"])))
    print("  %s" % summary_line(rows, total, unattributed))
    return 0


if __name__ == "__main__":
    sys.exit(main())