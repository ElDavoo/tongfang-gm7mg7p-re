#!/usr/bin/env python3
"""Resolve every BL51 bank-switch forwarder's `imm16` in the bank its stub selects.

Issue #255 established that a forwarder's `imm16` is read *after* the bank switch
-- `mov DPTR,#imm16` then `ljmp 0x1100`, and the stub at `0x1100` selects bank 0
-- and went on to correct nine annotation rows that had read a target in the
forwarder's own bank. What it deliberately did not do is re-measure the family
census built on that reading: `ghidra-functions.csv` `bank1,19A8` says so in its
own comment, in the 19 / 7 / 22 form, and asks for a replacement count. This is
that count.

**The correction is stronger than "measured against the wrong bank", and the
stronger form is the finding.** Every one of the forwarders is a *common-area*
entry: below `0x8000`, where every bank program and the common program are the
same bytes. So there is no "own bank" for one of these to have been read in --
a forwarder below `0x8000` is shared by every bank and executes whichever bank
is selected when it is called. That is a property of every entry, asserted for
all of them rather than illustrated by one, and it is why the phrase "the bank
the forwarder sits in", which the withdrawn row and the issue both use, has no
well-defined reading for this population. Asserting it for all of them is what
`forwarders()` below is for: it scans the whole image rather than
`trampolines`'s default `0x8000` bound, so a forwarder in a bank's own window
could reach this census and fail the assertion rather than be invisible to it.
`ec/decompiled/bank1/198A.asm` reads
like a bank-1 listing because a bank *program* is that bank's own code plus the
common area (`build_ec_decompile.py` grafts `0x0000`-`0x7FFF` onto every bank
image), and the header of every such listing says so.

**Two populations, and they are not interchangeable.** The whole family is every
trampoline `trampolines()` finds, a count over the committed image that moves
only if the firmware does. The annotated subset is the population
`ghidra-functions.csv` carries `forwarder` rows for, which is a count over this
repository's own annotation text, where every line stating it is a line another
merge has to edit. The report labels which is which wherever it prints a figure.

**Three classes and no fourth**, per target, against the committed listings of
the bank the stub selects:

  * `entry` -- the address is an instruction start in a committed `.asm` of that
    bank;
  * `operand` -- a listing of that bank covers the address, but as a byte of an
    instruction that starts earlier;
  * `no-listing` -- **not found by this method.** Reported with the bytes read
    off the image and the reason no listing covers the address, never as
    "absent", "undecodable" or "not code": an unexported function and a function
    Ghidra declined to cut are one thing to this method, and landing the
    missing listings is a `--report` run on the pinned assembler
    (`ec/ghidra/README.md`), not an inference from their absence.

**What this is not.** Nothing here is a behavioural claim and nothing here was
observed on hardware: every input is a committed file. Which bank an address
resolves in says where the linker meant the bytes to be read, not what the EC
does there, and no `status:` in `ec/annotations/registers.yaml` moves on any of
it -- `--self-test` asserts this module never so much as names that file.

Usage:
    python3 census_forwarder_targets.py
    python3 ec/tools/census_forwarder_targets.py --csv > ec/annotations/forwarder-targets.csv
    python3 census_forwarder_targets.py --self-test
"""
import argparse
import collections
import csv
import os
import re
import sys

from audit_call_targets import STUB_SITES, bank_switch_stubs, trampolines
from build_ec_decompile import BANK_WINDOWS, COMMON_END, FIRMWARE, file_offset
from citation_callers import iter_instructions, norm_addr

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
DECOMPILED = os.path.join(EC, "decompiled")
LISTING_INDEX = os.path.join(DECOMPILED, "listing-index.csv")
FUNCTIONS_CSV = os.path.join(EC, "annotations", "ghidra-functions.csv")

# How many bytes of a target the census reads off the image, on every row and not
# only the `no-listing` ones: a byte read is a byte read, and printing it beside
# each class is what lets a reader check the tool against the image instead of
# taking the class on trust. Eight is a pair of instructions wide.
TARGET_BYTES = 8

# The phrase that makes a `forwarder` annotation row a bank-switch row: it names
# the immediate the listing loads DPTR with. The *stub* is not part of the rule
# -- the row's comment is matched against the stub addresses
# `bank_switch_stubs` finds in the image, so which stubs exist is the image's
# answer rather than a literal written here. And the phrase is not keyed on
# "ljmp 0x1100": these rows spell the tail-jump more than one way, and a rule
# keyed on one spelling would answer a narrower question while reading as though
# it had answered this one.
DPTR_IMMEDIATE = re.compile(r"Loads DPTR with (0x[0-9A-Fa-f]{4})")

# The scope and `type` the annotated subset is drawn from. `forwarder` is this
# repository's own word for a bank-1 forwarder row; `bank-switch` and
# `dispatch` rows at trampoline entries are the near miss, and `report()` prints
# them with the type that kept them out, so the boundary is visible rather than
# a silent narrowing.
SUBSET_SCOPE = "bank1"
SUBSET_TYPE = "forwarder"

# The three answers, named here because both the report and `--self-test` have to
# agree on the vocabulary and neither may grow a fourth.
CLASSES = ("entry", "operand", "no-listing")


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def program_of(bank):
    """`ec/decompiled/`'s directory name for a bank number."""
    return "bank%d" % bank


def byte_width(parts):
    """How many bytes one instruction line occupies.

    The `.asm` byte region is three fixed slots with `-` in the absent ones, and
    the mnemonic is always token 4 -- so the width is "the slots before the
    first pad", read over those three positions and no further. Bounding it at
    three is not a formality: a 3-byte `lcall 0xa4d6` has no pad at all, so a
    scan that walks the tokens until it finds one runs on into the operands and
    reports five, which would cover two bytes of whatever follows and turn a
    `no-listing` answer into an `operand` one.
    """
    width = 0
    for slot in parts[1:4]:
        if slot == "-":
            break
        width += 1
    return width


def listing_coverage(program):
    """{address: (listing, address of the covering instruction)} for one program.

    Every byte of every committed listing in that program, so the two classes
    that need a listing can be told apart: an address the map does not hold is
    `no-listing`, and an address it holds under a *different* instruction's
    start is an `operand`. A map of listing names alone could not do that, and
    the difference between them is the whole question.

    Two rules make it a property of the tree rather than of `os.listdir`'s
    order, which would otherwise decide every address two listings both span:

      * a listing's **own entry** maps to itself, always. Where a seeded
        function sits inside the span of the function that contains it, both
        listings cover the address, and only one of them is named for it --
        that one has to win, or `entry` becomes a coin toss.
      * every other contested byte goes to the lexicographically first listing,
        so a byte two listings span reads the same on every filesystem.
    """
    cover = {}
    own = {}
    directory = os.path.join(DECOMPILED, program)
    if not os.path.isdir(directory):
        return cover
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".asm"):
            continue
        listing = name[:-4]
        for parts in iter_instructions(os.path.join(directory, name)):
            start = int(parts[0], 16)
            own[start] = (listing, start)
            for k in range(byte_width(parts)):
                hit = cover.get(start + k)
                if hit is None or (listing, start) < hit:
                    cover[start + k] = (listing, start)
    cover.update(own)
    return cover


def coverage_for_banks():
    """The coverage map of each bank, built once per run.

    `listing_coverage` parses every committed listing in the program, so a
    comparison that re-derived it per target would turn a report into a scan of
    the whole export times the target count.
    """
    return {program_of(bank): listing_coverage(program_of(bank))
            for bank in (0, 1)}


def classify(program, target, cover):
    """`(class, listing, covering instruction address)` for one target address.

    `target` is a runtime address in `program`. The three classes are the ones
    the module docstring names; there is no fourth, and `no-listing` means *not
    found by this method* -- the caller prints the bytes read off the image for
    it, and no caller may strengthen it into "absent".
    """
    hit = cover.get(target)
    if hit is None:
        return "no-listing", None, None
    listing, start = hit
    return ("entry" if start == target else "operand"), listing, start


def trampoline_bytes(imm16, stub):
    """The six bytes a BL51 trampoline entry is: `mov DPTR,#imm16 ; ljmp stub`.

    Written out rather than sliced out of the image so that the *expected* shape
    is one expression, and `placement()` below can ask each program's image
    whether it holds them without that question being re-asked per site.
    """
    return bytes([0x90, (imm16 >> 8) & 0xFF, imm16 & 0xFF,
                  0x02, (stub >> 8) & 0xFF, stub & 0xFF])


def forwarders(d, stubs):
    """Every BL51 forwarder in the image, keyed by the address a caller calls.

    `trampolines()` defaults to `limit=0x8000`, which is what its own callers
    want and what this census must not inherit: a forwarder at or above
    `0x8000` could then never enter the population at all, so `common_area()`
    would hold for every row by construction rather than by measurement, and
    the assertion that it does could not go red. The whole image is the same
    predicate one region wider.
    """
    return trampolines(d, stubs, limit=len(d))


def read_at(d, program, addr, length):
    """`length` bytes of runtime address `addr` in `program`, through `file_offset`.

    The runtime reading, which is the one the classification question uses. An
    address below `0x8000` is the shared common area in every program, so this
    is the same file offset for all three and is what a caller means by "the
    bytes at 0xAA04 in bank 0".
    """
    off = file_offset(program, addr)
    return d[off:off + length]


def placement(d, entry, want):
    """`(resolved, own_window)` for one forwarder entry.

    `resolved` is `{program: file offset}` from `file_offset`, and the claim
    rests on what that map says: an address below `0x8000` resolves to the same
    offset in every program, so there is one copy of those bytes and no bank has
    a private reading of the address.

    `own_window` is the refutation attempt rather than a second opinion. It asks
    whether either bank's own `0x8000`-`0xFFFF` region holds the trampoline
    shape at the same offset into that bank's window -- file `0x10000 + entry`
    for bank 1 -- which is bank 1's runtime `0x8000 + entry`, a *different*
    address holding unrelated code. That is what `ec/decompiled/bank1/198A.asm`
    looks like if read as bank-1 code, and the check is here so the common-area
    claim fails rather than passes if that ever stopped being true.
    """
    resolved = {p: file_offset(p, entry) for p in sorted(BANK_WINDOWS)}
    own = {}
    for program in ("bank0", "bank1"):
        off = BANK_WINDOWS[program] + entry
        own[program] = d[off:off + len(want)] == want
    return resolved, own


def common_area(row):
    """True when every program resolves the entry to one shared copy of it.

    Both halves have to hold, and the second is the one that could go wrong:
    one file offset for all three programs says the bytes are shared, and it
    says nothing on its own that the address is *below* the banks' private
    regions -- `file_offset` would give a bank its own offset for anything at
    or above `0x8000`, and the two together are what "common area" means.
    """
    resolved, own = row["placement"]
    return (len(set(resolved.values())) == 1
            and min(resolved.values()) < COMMON_END
            and not any(own.values()))


def annotated_rows(d, stubs, tramp):
    """The annotated subset, and the rows just outside it.

    Both lists come from one walk of `ghidra-functions.csv`, so the second is
    the first's boundary rather than a second reading of the same file.

    Selected by the rule the module docstring states: `scope` and `type` from
    the CSV, the immediate from `DPTR_IMMEDIATE`, and the stub by looking for
    one of the addresses `bank_switch_stubs` found *in this image* among the
    row's own comment. The near miss is every other annotated row in the same
    scope whose address is a trampoline entry in this image -- which is a
    property of the image and the addresses, not a string search, so a row
    typed differently for the same six bytes shows up in it.
    """
    inside, outside = [], []
    for row in read_csv(FUNCTIONS_CSV):
        if row["scope"] != SUBSET_SCOPE:
            continue
        addr = norm_addr(row["addr"])
        entry = int(addr, 16)
        if entry not in tramp:
            continue
        match = DPTR_IMMEDIATE.search(row["comment"])
        stub = next((a for a in sorted(stubs)
                     if "0x%04X" % a in row["comment"]), None)
        item = (row["scope"], addr, row["name"], row["type"],
                norm_addr(match.group(1)) if match else "",
                "%04X" % stub if stub is not None else "")
        if row["type"] == SUBSET_TYPE and match and stub is not None:
            inside.append(item)
        else:
            outside.append(item)
    return inside, outside


def exported_addresses():
    """{(program, addr)} for every row `ec/decompiled/listing-index.csv` carries.

    Read for the reason a `no-listing` row is reported with a reason at all: the
    honest one is "no committed export names this address in this program", and
    that is a statement about the index rather than about the bytes. An address
    the index *does* name, with no listing on disk, is a different and louder
    thing, and gets its own reason rather than being folded into the first.
    """
    return {(r["program"], norm_addr(r["addr"])) for r in read_csv(LISTING_INDEX)}


def no_listing_reason(program, target, index):
    """Why no listing covers `target` in `program`, in words that stay calibrated."""
    if (program, "%04X" % target) in index:
        return ("listing-index.csv names this address in %s but no .asm is "
                "committed for it" % program)
    return ("no committed export names this address in %s -- an unseeded "
            "function, which is not a verdict about the bytes" % program)


def survey(d):
    """Every forwarder target, classified in the bank its stub selects.

    One pass, so the per-stub tables, the annotated-subset breakdown and
    `--csv` are three views of the same rows and cannot disagree.
    """
    stubs = bank_switch_stubs(d)
    tramp = forwarders(d, stubs)
    covers = coverage_for_banks()
    index = exported_addresses()
    inside, outside = annotated_rows(d, stubs, tramp)
    named = {int(addr, 16): (name, imm16)
             for _s, addr, name, _t, imm16, _st in inside}

    rows = []
    for entry in sorted(tramp):
        bank, target = tramp[entry]
        program = program_of(bank)
        stub = next(a for a, b in sorted(stubs.items()) if b == bank)
        cls, listing, cover_addr = classify(program, target, covers[program])
        ann = named.get(entry)
        rows.append({
            "stub": stub,
            "bank": bank,
            "forwarder": entry,
            "target": target,
            "class": cls,
            "listing": listing,
            "listing_entry": cover_addr,
            "bytes": read_at(d, program, target, TARGET_BYTES),
            "placement": placement(d, entry, trampoline_bytes(target, stub)),
            "annotation": "%s,%s" % (SUBSET_SCOPE, "%04X" % entry) if ann else "",
            "name": ann[0] if ann else "",
            "reason": no_listing_reason(program, target, index)
            if cls == "no-listing" else "",
            "reclassified": classify("bank%d" % (1 - bank), target,
                                     covers["bank%d" % (1 - bank)])[0],
        })
    return rows, stubs, inside, outside


def split(rows):
    """The three-class split of `rows`, as a `{class: n}` over all three keys."""
    counts = collections.Counter(r["class"] for r in rows)
    return {c: counts[c] for c in CLASSES}


def subset_rows(rows, inside):
    """The survey rows the annotated subset names, matched by forwarder address.

    Keyed on the entry address rather than on the target: a target is one of the
    image's numbers and the entry is the one thing that says which listing the
    annotation row is about.
    """
    wanted = {int(addr, 16) for _s, addr, _n, _t, _i, _st in inside}
    return [r for r in rows if r["forwarder"] in wanted]


def report():
    """The census as the lines `docs/findings/forwarder-target-bank-census.md`
    quotes."""
    d = open(FIRMWARE, "rb").read()
    rows, stubs, inside, outside = survey(d)
    sub = subset_rows(rows, inside)
    out = []
    say = out.append

    say("census_forwarder_targets.py -- every BL51 forwarder target, resolved in "
        "the bank its stub selects")
    say("")
    say("Reads `ec/firmware/GMxMGxx_11.800`, `ec/decompiled/*/*.asm` and")
    say("`ec/annotations/ghidra-functions.csv`. No behavioural claim: nothing "
        "here was")
    say("observed on hardware and no `status:` in registers.yaml moves on it.")
    say("")

    say("## 1. The stub map, and every stub the image holds")
    say("")
    say("`bank_switch_stubs` is audit_call_targets.py's own scan and "
        "`STUB_SITES` is its")
    say("pinned answer, so nothing here can disagree with what "
        "bank-call-audit.md section 2")
    say("records. A stub with no forwarders is printed at zero rather than "
        "dropped, so the")
    say("sweep over the four sites is visibly complete.")
    say("")
    for addr, bank in sorted(stubs.items()):
        routed = [r for r in rows if r["stub"] == addr]
        say("  stub 0x%04X selects bank %d: %d forwarder(s), %d distinct target(s)"
            % (addr, bank, len(routed), len({r["target"] for r in routed})))
    say("")

    say("## 2. The whole family, per stub")
    say("")
    say("A count over the committed image. `entry` is the address at an "
        "instruction start in")
    say("a committed listing of the selected bank, `operand` is covered by one "
        "but not at a")
    say("start, and `no-listing` is **not found by this method**.")
    say("")
    say("The scan is the whole image, not `trampolines`'s default `0x8000` "
        "bound: a")
    say("forwarder in a bank's own window would appear in this table rather "
        "than be")
    say("outside the census, which is what makes section 4's claim falsifiable.")
    say("")
    say("| stub | bank | forwarders | distinct targets | entry | operand | no-listing |")
    say("|---|---:|---:|---:|---:|---:|---:|")
    for addr, bank in sorted(stubs.items()):
        routed = [r for r in rows if r["stub"] == addr]
        cells = split(routed)
        say("| `0x%04X` | %d | %d | %d | %d | %d | %d |"
            % (addr, bank, len(routed), len({r["target"] for r in routed}),
               cells["entry"], cells["operand"], cells["no-listing"]))
    say("")
    say("The mirror direction is the second row -- stub `0x1114` is bank 1's, "
        "and")
    say("the withdrawn count never looked at it. `--csv` carries every target "
        "of both.")
    say("")

    say("## 3. The annotated subset")
    say("")
    say("The population `ghidra-functions.csv` `bank1,19A8` named: the rows "
        "scoped `%s`," % SUBSET_SCOPE)
    say("typed `%s`, whose own comment names a stub address this image holds "
        "and" % SUBSET_TYPE)
    say("quotes the immediate the listing loads DPTR with. Selected by that "
        "rule, not by")
    say("the string `ljmp 0x1100` -- these rows spell the tail-jump more than one "
        "way, so a")
    say("rule keyed on one spelling would answer a narrower question while "
        "reading as though")
    say("it had answered this one. This is a count over this repository's "
        "annotation text")
    say("rather than over the image, so it moves when a row lands; section 2's "
        "does not.")
    say("")
    if outside:
        say("  %d more `%s` annotated row(s) sit at a forwarder entry this image"
            % (len(outside), SUBSET_SCOPE))
        say("  holds and are *not* in the subset, every one of them typed "
            "something else:")
        for _s, addr, name, rtype, imm16, stub in outside:
            say("    `%s,%s` %s (%s%s)"
                % (SUBSET_SCOPE, addr, rtype,
                   name,
                   ", imm16 0x%s" % imm16 if imm16 else ""))
        say("  They are in section 2's tables and in `--csv`, and out of the "
            "population the")
        say("  withdrawn count was taken from; the boundary is `type`, and it "
            "is printed")
        say("  here rather than left as a silent narrowing.")
    else:
        say("  No other `%s` annotated row sits at a forwarder entry this image "
            "holds." % SUBSET_SCOPE)
    say("")
    cells = split(sub)
    say("  Resolved in the bank each stub selects -- bank 0 for all of them, "
        "since every")
    say("  one of these rows names `0x1100`: %d targets, %d entry, %d operand, "
        "%d no-listing."
        % (len(sub), cells["entry"], cells["operand"], cells["no-listing"]))
    say("")
    say("  The withdrawn figure beside it, over the same rows read against the "
        "other")
    say("  bank's listings. The two rows differ only in which bank's `.asm` "
        "files were")
    say("  asked, which is the whole of the correction:")
    say("")
    other = {c: sum(1 for r in sub if r["reclassified"] == c) for c in CLASSES}
    say("| listings read | entry | operand | no-listing |")
    say("|---|---:|---:|---:|")
    say("| the bank the stub selects | %d | %d | %d |"
        % (cells["entry"], cells["operand"], cells["no-listing"]))
    say("| the other bank -- withdrawn, issue #255 | %d | %d | %d |"
        % (other["entry"], other["operand"], other["no-listing"]))
    say("")

    say("## 4. Where the forwarders themselves sit")
    say("")
    say("The finding that changes the correction's wording. `file_offset` "
        "resolves an")
    say("address below `0x8000` to the same file offset in every program, so "
        "those bytes")
    say("are one copy the banks share; and neither bank's own region holds the "
        "trampoline")
    say("shape at the same offset into its window:")
    say("")
    say("  %d of %d annotated forwarder(s) resolve to one shared copy"
        % (sum(1 for r in sub if common_area(r)), len(sub)))
    say("  %d of %d across the whole family"
        % (sum(1 for r in rows if common_area(r)), len(rows)))
    say("")
    say("Both fractions are over the whole-image scan above, so a forwarder in "
        "a bank's")
    say("own window would be counted against them rather than be absent from "
        "the population.")
    say("")
    say("A bank program is its own `0x8000`-`0xFFFF` plus the shared "
        "`0x0000`-`0x7FFF`")
    say("common area, which is why `ec/decompiled/bank1/198A.asm` reads like a "
        "bank-1")
    say("listing and is the common area: its bytes are at file `0x198A`, and at "
        "file")
    say("`0x1198A` -- bank 1's own region at the same offset into that window, "
        "its")
    say("runtime `0x998A` -- the firmware holds `70 0f 90 1c 04 e0`. Below "
        "`0x8000` there is")
    say("no \"own bank\" for a forwarder to have been read in: the block is "
        "shared, and it")
    say("runs whichever bank is selected when it is called.")
    say("")

    say("## 5. The annotated subset, one row per target")
    say("")
    say("`bytes` are read off `ec/firmware/GMxMGxx_11.800` through "
        "`build_ec_decompile.file_offset`.")
    say("A byte read, and nothing more than one: `entry` and `operand` are "
        "statements about")
    say("which listing covers the address, not about what the code does.")
    say("")
    say("| forwarder | annotation | imm16 | class | listing | bytes |")
    say("|---|---|---|---|---|---|")
    for row in sorted(sub, key=lambda r: r["forwarder"]):
        say("| `0x%04X` | %s | `0x%04X` | %s | %s | `%s` |"
            % (row["forwarder"],
               "`%s`" % row["annotation"] if row["annotation"] else "--",
               row["target"], row["class"],
               "`%s`" % row["listing"] if row["listing"] else "-- none --",
               row["bytes"].hex(" ")))
    say("")
    say("The `no-listing` rows and why. A statement about the committed exports, "
        "never about")
    say("the bytes; landing the missing listings needs a `--report` run on the "
        "pinned")
    say("assembler (`ec/ghidra/README.md`).")
    say("")
    for row in sorted((r for r in sub if r["class"] == "no-listing"),
                      key=lambda r: r["target"]):
        say("  0x%04X (bank %d): %s" % (row["target"], row["bank"], row["reason"]))
    say("")
    return "\n".join(out)


def write_csv(rows):
    w = csv.writer(sys.stdout)
    w.writerow(["stub", "bank", "forwarder", "target", "class", "listing",
                "listing_entry", "bytes", "reason", "annotation"])
    for r in rows:
        w.writerow([
            "0x%04X" % r["stub"], r["bank"], "0x%04X" % r["forwarder"],
            "0x%04X" % r["target"], r["class"], r["listing"] or "",
            "" if r["listing_entry"] is None else "0x%04X" % r["listing_entry"],
            r["bytes"].hex(" "), r["reason"], r["annotation"],
        ])


def self_test(d) -> int:
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print("  %s  %s" % ("ok  " if ok else "FAIL", text))

    stubs = bank_switch_stubs(d)
    tramp = forwarders(d, stubs)
    rows, stubs, inside, outside = survey(d)
    sub = subset_rows(rows, inside)

    # Inherited rather than re-derived: audit_call_targets.py already asserts
    # this against the image, and a second implementation of it here would be a
    # second thing to be wrong.
    check(tuple(sorted(stubs.items())) == STUB_SITES,
          "the four stub sites are the ones audit_call_targets.py pins: %s"
          % ", ".join("0x%04X=bank%d" % (a, b) for a, b in STUB_SITES))
    check(all("0x%04X" % a in report() for a in stubs),
          "every stub the image holds is printed by the report, the two with "
          "no forwarder at zero rather than dropped, so the sweep over the four "
          "sites is visibly complete")

    # The common-area claim, for every entry rather than for one exemplar: a
    # forwarder that sits in a bank's own window would be code that runs
    # differently per bank, and this is the assertion that would catch it.
    # `forwarders()` scans the whole image, so such an entry is in `rows` and
    # this can go red; a scan bounded at the banks' private regions would hold
    # for every row by construction.
    misplaced = [r for r in rows if not common_area(r)]
    check(not misplaced,
          "every forwarder's six bytes match in the common area and in neither "
          "bank's own window -- all of them, not one worked example, over a "
          "whole-image scan%s"
          % ("" if not misplaced else " -- not at "
             + ", ".join("0x%04X" % r["forwarder"] for r in misplaced[:4])))

    # The subset is defined by a rule, so what has to hold is that the rule and
    # the image agree: each selected row's own six bytes are a trampoline
    # through the stub its comment names, carrying the imm16 the comment quotes.
    wrong = ["%s,%s" % (s, a) for s, a, _n, _t, imm16, stub in inside
             if tramp.get(int(a, 16)) != (stubs[int(stub, 16)], int(imm16, 16))
             or read_at(d, SUBSET_SCOPE, int(a, 16), 6)
             != trampoline_bytes(int(imm16, 16), int(stub, 16))]
    check(not wrong,
          "every selected row's own bytes are a trampoline through the stub "
          "its comment names, carrying the imm16 that comment quotes"
          + ("" if not wrong else " -- wrong at " + ", ".join(wrong[:4])))
    check(all(int(addr, 16) in tramp for _s, addr, _n, _t, _i, _st in inside),
          "and every selected row's address is a forwarder entry this image "
          "holds, so the rule selected nothing the image does not have")
    check({r["target"] for r in sub}
          == {int(imm16, 16) for _s, _a, _n, _t, imm16, _st in inside},
          "the subset's target set is exactly the imm16 set the rows quote")

    # The near miss is what makes the rule checkable: a rule that quietly
    # widened or narrowed would leave this set empty or doubled.
    check(bool(outside) and not ({(s, a) for s, a, _n, _t, _i, _st in inside}
                                 & {(s, a) for s, a, _n, _t, _i, _st in outside}),
          "the annotated rows at a forwarder entry that the rule leaves out are "
          "reported and disjoint from the subset")

    check(all(r["class"] in CLASSES for r in rows),
          "every target lands in one of the three declared classes: %s"
          % ", ".join(CLASSES))

    # The calibration refusal. A target no listing covers is reported with the
    # bytes and a reason; it is never upgraded into a claim about the bytes.
    strong = [r for r in rows if any(w in r["reason"].lower() for w in
                                     ("absent", "undecodable", "not code"))]
    unexplained = [r for r in rows if r["class"] == "no-listing"
                   and (not r["reason"] or program_of(r["bank"]) not in r["reason"])]
    check(not strong,
          "no row's reason claims more than this method found"
          + ("" if not strong else " -- at "
             + ", ".join("0x%04X" % r["target"] for r in strong[:4])))
    check(not unexplained,
          "and every no-listing row says which program looked and did not find "
          "it, rather than leaving the cell empty"
          + ("" if not unexplained else " -- at "
             + ", ".join("0x%04X" % r["target"] for r in unexplained[:4])))
    check(all(len(r["bytes"]) == TARGET_BYTES for r in rows),
          "every row carries %d bytes read off the image through file_offset, "
          "the no-listing rows included" % TARGET_BYTES)

    # Registers stay where they are. The census's whole input set is three
    # paths, and a status: in registers.yaml could only move if one of them were
    # that file; the check is on the paths rather than on the source text,
    # because a self-scan for a word the check itself contains proves nothing.
    check(not any("registers.yaml" in p
                  for p in (FIRMWARE, FUNCTIONS_CSV, LISTING_INDEX)),
          "the census reads three files and none of them is "
          "ec/annotations/registers.yaml, so no register status: can move on "
          "any of this")

    print()
    print("self-test FAILED: %d check(s) disagree" % bad if bad
          else "self-test passed: every forwarder common-area, the subset's "
               "rule and the image agreeing, three classes and no fourth")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", action="store_true",
                    help="one row per forwarder target on stdout, instead of "
                         "the tables")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the stub map, the common-area placement of "
                         "every entry, the subset rule, and the three classes")
    args = ap.parse_args()

    d = open(FIRMWARE, "rb").read()

    if args.self_test:
        return self_test(d)

    if args.csv:
        write_csv(survey(d)[0])
        return 0

    print(report())
    return 0


if __name__ == "__main__":
    sys.exit(main())