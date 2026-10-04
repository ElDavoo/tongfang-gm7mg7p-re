#!/usr/bin/env python3
"""Can any mechanical criterion tell a re-export from a fragment? Two probes.

`export_ownership.py` folds one `.c` into another when the smaller body's
statements are 90% of the way into the larger one, and the fold is a claim the
census then acts on: a non-owner's references are counted through its owner, so
folding a routine that is not an export of the owner deletes it from the census.
`xdata-export-ownership-verdicts.csv` records a reading, per row, of which fold
that is -- `re-export` or `fragment` -- and `export_ownership_verdicts.py`'s own
docstring already records that the obvious mechanical criteria do not decide it:
byte-range containment and literal-slice both fail.

**This asks the question one level up.** Not "does criterion X decide the
verdicts" but "of the two criteria nobody has tried, does either" -- and the
answer is no, measured on the rows where the verdict is already known rather
than argued. The two are the obvious remaining candidates:

  * **A -- does the member's own address get named?** A routine the exporter
    re-cut out of a longer routine is a routine something transfers to, so
    `entry_reachability.sites_naming()` is asked per program whether any
    transfer in that program names the member's address. Per program, and not
    over the whole image, because a 16-bit `lcall` target does not name a bank
    and a bank-1 site's answer to a bank-0 question is the mistake this
    repository has already had to correct once (`entry_reachability.py`'s
    header).
  * **B -- is the member's address an instruction the exporter committed?**
    If the member sits where the exporter happened to cut rather than at a
    routine entry, the committed `.asm` listings would have no instruction
    starting there at all. Read from the listings, not from a disassembly of
    the image, because a criterion that needed a fresh decode would not be
    answerable from what this repository committed.

**Neither separates, and why is the finding rather than a null result.**
A `fragment` is a routine in its own right that the owner's text contains
without being an export of it -- `common/322C.c` is recorded because
`common/30FB.c` *calls* it -- so its address is a routine somebody reaches, and
an address the exporter committed an instruction at. Both are ordinary code at
ordinary entry addresses, which is why both probes answer `yes` for every
fragment and for every re-export alike. The distinction a working criterion
would need is between the exporter's cut and a routine boundary, which is the
defect (`xdata-06c2-06db-timers.md` 8 item 7) and is not in what these two
probes read.

**What a row with no verdict is.** `unmeasured`, and it is the honest word: the
probes say nothing about a fold nobody has read, and a report that printed a
probe result beside no verdict would read as a fold that has been cleared. The
ledger's population is narrow by construction -- an owner at least twice the
member's size and containment exactly `1.00` -- so most non-owner rows are in
this state, and that population is a worklist rather than a coverage figure.

**What this tool asserts.** Nothing about the firmware. It reports two columns
and cross-tabs them against a committed ledger; `test_export_fold_identity.py`
is where a property is asserted, and the property it asserts is that these two
probes do *not* separate the recorded verdicts -- so the day a probe set does,
the suite goes red and says the boundary became mechanically settleable.

**Not in `.github/scripts/agent-gates.sh`, and cannot be from an agent branch.**
The script is a template copy (`docs/agent-pipeline.md`), so adding a tool to
its list is a human's edit. `python3 ec/tools/export_fold_identity.py` reads
the committed map, the committed ledger, the committed firmware image and the
committed `.asm` listings -- no Ghidra, no network, no assembler -- so it is
cheap-tier work whenever a human wires it in.

Usage:
    python3 ec/tools/export_fold_identity.py             the cross-tab
    python3 ec/tools/export_fold_identity.py --rows      one line per non-owner row
    python3 ec/tools/export_fold_identity.py --csv       the same, as CSV
"""
import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import entry_reachability  # noqa: E402
import export_ownership_verdicts  # noqa: E402

EC_DIR = os.path.dirname(HERE)
DECOMPILED = os.path.join(EC_DIR, "decompiled")

# The two probes, named because the cross-tab's columns are these and a reader
# should not have to match a column header back to a paragraph. The order is
# the order the report prints them in and nothing depends on it.
PROBES = ("named_by_transfer", "instruction_start")

# What a row is called when the ledger records no reading of it. Not a verdict
# and not a third verdict: `export_ownership_verdicts.VERDICTS` is a closed
# vocabulary and this word is deliberately outside it, so a row carrying it can
# never be mistaken for one a person decided.
UNMEASURED = "unmeasured"

# What a probe says when it ran and what it says when it could not. Three
# values, not two, because the third is the whole reason this is not a boolean:
# `entry_reachability.AUDITED` is `common`, `bank0` and `bank1`, and a non-owner
# row in `pd` has no A answer at all. Reporting that row as `no` would say the
# scan found nothing naming it, which is a claim about the bytes from a scan
# that never ran over them.
NOT_AUDITED = "not-audited"

# What `listing-index.csv` puts in `out_file` for an export the decompiler
# emitted no instructions for, rather than recording no row at all. Read here so
# that probe B's one boundary has one name: it is a `build_ec_decompile.py`
# convention, not a fact about the firmware, and a second spelling of it in the
# suite would be a second thing to be wrong about.
NO_INSTRUCTIONS = "(no-instructions)"

# An `.asm` line is an address in four hex digits, then the bytes, then the
# mnemonic. Anchored and fixed-width on the address because the alternative --
# matching anything hex-ish at the start of the line -- also matches the `;`
# banner comments, and a comment line would then read as an instruction start.
ASM_ADDRESS = re.compile(r"^([0-9A-F]{4})\s")

# The programs whose listings this reads, named rather than globbed off the
# directory so that a program gaining a directory is a decision somebody makes
# here rather than a silent widening of what probe B is over.
PROGRAMS = ("common", "bank0", "bank1", "pd")


def instruction_starts(program, root=DECOMPILED) -> set:
    """Every address a committed listing in `program` starts an instruction at.

    A set rather than a count, because the probe is a membership question and
    the tree holds one listing per export, so a member's own address is in here
    by construction unless the listing at that address has no instructions at
    all. That is worth knowing before reading a fire as evidence: see the
    docstring, and `test_export_fold_identity.py`'s control case.
    """
    starts = set()
    directory = os.path.join(root, program)
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".asm"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as f:
            for line in f:
                m = ASM_ADDRESS.match(line)
                if m:
                    starts.add(int(m.group(1), 16))
    return starts


def programs_index(root=DECOMPILED) -> dict:
    """program -> its instruction starts, read once for the whole report."""
    return {p: instruction_starts(p, root) for p in PROGRAMS}


def probe_named(image, row) -> str:
    """A: does a transfer in the member's own program name its address?

    `entry_reachability.sites_naming()` is asked one program at a time and never
    the whole image, so a bank-1 site's answer can never reach a bank-0 row.

    `not-audited` rather than `no` for a program outside
    `entry_reachability.AUDITED`, which is what makes the distinction between
    "the scan found nothing" and "the scan does not cover this program" -- the
    same one that tool's own header is about, and the one this row would
    otherwise lose silently.
    """
    if row["program"] not in entry_reachability.AUDITED:
        return NOT_AUDITED
    return "yes" if entry_reachability.sites_naming(
        image, row["program"], int(row["addr"], 16)) else "no"


def probe_instruction_start(index, row) -> str:
    """B: is the member's address an instruction start in its own program?

    A set membership, so two values rather than three -- every program in
    `PROGRAMS` has a listing tree here, and a program without one would be a
    missing directory rather than an unanswered question.
    """
    return "yes" if int(row["addr"], 16) in index.get(row["program"], ()) \
        else "no"


def non_owner_rows(records) -> list:
    """The rows a fold is a claim about: every `shared=yes` row of the map.

    Derived from the committed CSV rather than typed, so the population moves
    with the map instead of with this file. `--check` on `export_ownership.py`
    is what holds that CSV to the tree.
    """
    return [r for r in records if r["shared"] == "yes"]


def ledger_by_member(verdicts) -> dict:
    """out_file -> the recorded verdict, for the members the ledger names."""
    return {v["out_file"]: v["verdict"] for v in verdicts}


def assess(records, verdicts, image, index=None) -> list:
    """One record per non-owner row: both probes, and the verdict or not.

    `index` is taken rather than built so a caller that has several rows to
    assess pays for the listings once, and a test that wants a controlled
    `index` can hand one in -- the listings are the one input here big enough
    that reading them per row would dominate the run.
    """
    index = programs_index() if index is None else index
    ledger = ledger_by_member(verdicts)
    out = []
    for row in non_owner_rows(records):
        out.append({
            "out_file": row["out_file"],
            "program": row["program"],
            "addr": row["addr"],
            "owner_out_file": row["owner_out_file"],
            "named_by_transfer": probe_named(image, row),
            "instruction_start": probe_instruction_start(index, row),
            "verdict": ledger.get(row["out_file"], UNMEASURED),
        })
    return out


def crosstab(assessed) -> list:
    """`(verdict, probe, value) -> count`, over the rows that carry a verdict.

    Only the rows a person has read are counted. An `unmeasured` row is in
    neither column, and counting it would answer a question nobody asked --
    how many non-owner rows does a probe fire on -- with a number that grows
    whenever a seed is added.
    """
    counts = collections.Counter()
    for row in assessed:
        if row["verdict"] == UNMEASURED:
            continue
        for probe in PROBES:
            counts[(row["verdict"], probe, row[probe])] += 1
    return counts


def separates(counts, verdicts, probe) -> bool:
    """Whether `probe` reads one verdict off another with no row left over.

    True when each verdict's rows carry one value between them and the two
    verdicts' values differ -- a criterion that fires on every re-export and on
    no fragment, or the other way round, so either answer names the fold. A
    criterion that fires on both, or on neither, separates nothing, and neither
    does one that splits a verdict's own rows: a probe answering `yes` on most
    re-exports and on some fragments reads no fold off either answer, because
    the two classes share `yes` on the rows where both carry it. That is a
    partial signal and not a criterion that settles anything, so it must not
    read as one -- `report()` prints a conclusion about the boundary from this
    answer, and the direction that errs is the one that claims settleability.

    Read off `counts` rather than off a list of rows so a caller can ask it
    about the cross-tab it already built, and so the answer is a property of
    the measurement rather than of how the measurement was iterated.
    """
    seen = {}
    for verdict in verdicts:
        if verdict == UNMEASURED:
            continue
        values = {value for (v, p, value) in counts
                  if v == verdict and p == probe}
        if not values:
            # No row of this verdict, so nothing to separate: not a
            # discriminator, and not evidence of one either.
            return False
        if len(values) > 1:
            # This verdict's own rows disagree, so no single answer of the
            # probe's names the fold and the boundary is not settled by it.
            return False
        seen[verdict] = values
    if len(seen) < 2:
        return False
    first, *rest = list(seen.values())
    return all(values.isdisjoint(first) for values in rest)


def report(assessed) -> str:
    """The cross-tab, and the coverage gap beside it.

    Each probe column is one count per value rather than a count of fires, so a
    `not-audited` cell is visible as its own number instead of being folded into
    a `no` that reads as the scan having run and found nothing.

    The gap is printed because it is the half of this measurement a reader is
    most likely to over-read: a probe that fails to separate two verdicts says
    nothing about the rows no verdict covers, and a table of the fired columns
    without that line reads as though it did.
    """
    judged = [r for r in assessed if r["verdict"] != UNMEASURED]
    unjudged = [r for r in assessed if r["verdict"] == UNMEASURED]
    verdicts = sorted({r["verdict"] for r in judged})
    columns = ["%-12s %5s" % ("verdict", "rows")]
    columns += ["%-22s" % probe for probe in PROBES]
    lines = ["export_fold_identity.py -- two probes against the recorded "
             "verdicts",
             "",
             "  ".join(columns)]
    for verdict in verdicts:
        here = [r for r in judged if r["verdict"] == verdict]
        cells = ["%-22s" % _cells(here, probe) for probe in PROBES]
        lines.append("  ".join(["%-12s %5d" % (verdict, len(here))]
                              + cells).rstrip())
    # Stated from `separates` rather than hardcoded, so the sentence is a
    # property of the cross-tab printed directly above it. A conclusion typed
    # in beside a table that can contradict it is a claim about the tool, not
    # a measurement of the tree, and this is the line the write-up offers as
    # the evidence for the negative result.
    counts = crosstab(assessed)
    discriminates = [probe for probe in PROBES
                     if separates(counts, verdicts, probe)]
    if discriminates:
        verdict_line = [
            "%s %s the recorded verdicts, so the boundary is mechanically"
            % (", ".join(discriminates),
               "separates" if len(discriminates) == 1 else "separate"),
            "settleable from the committed decompile. The negative result "
            "this write-up",
            "records no longer holds; re-derive it before citing it."]
    else:
        verdict_line = [
            "Neither probe separates the two verdicts, so the boundary is "
            "still not",
            "mechanically settleable from the committed decompile "
            "(annotations/xdata-06c2-06db-timers.md",
            "8 item 7)."]
    lines += [""] + verdict_line + [
              "A row with no verdict is %r, and a probe firing on "
              "it" % UNMEASURED,
              "says nothing about the fold: %d of %d non-owner rows carry no "
              "verdict, over" % (len(unjudged), len(assessed)),
              "%d owners." % len({r["owner_out_file"] for r in unjudged}),
              "",
              "Probe A's window is the audited programs %s, one at a"
              % (", ".join(entry_reachability.AUDITED),),
              "time. A row in any other program reads %r rather than `no`, "
              "because" % NOT_AUDITED,
              "the scan does not cover it rather than having covered it and "
              "found nothing.",
              ""]
    return "\n".join(lines)


def _cells(rows, probe) -> str:
    """`yes=15 no=0` for one probe over one verdict's rows, every value shown."""
    counts = collections.Counter(r[probe] for r in rows)
    return " ".join("%s=%d" % (value, counts[value]) for value in sorted(counts))


def write_csv(assessed, stream=sys.stdout) -> None:
    """One row per non-owner row, both probes and the verdict or `unmeasured`."""
    columns = ["out_file", "program", "addr", "owner_out_file"] + list(PROBES) \
        + ["verdict"]
    writer = csv.writer(stream)
    writer.writerow(columns)
    for row in assessed:
        writer.writerow([row[c] for c in columns])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument("--rows", action="store_true",
                       help="one line per non-owner row, both probes and the "
                            "verdict, instead of the cross-tab")
    modes.add_argument("--csv", action="store_true",
                       help="the same table as CSV, for a diff or a write-up")
    ap.add_argument("--map", default=export_ownership_verdicts.MAP_CSV,
                    help=f"the ownership map (default: "
                         f"{export_ownership_verdicts.MAP_CSV})")
    ap.add_argument("--verdicts", default=export_ownership_verdicts.VERDICTS_CSV,
                    help=f"the ledger (default: "
                         f"{export_ownership_verdicts.VERDICTS_CSV})")
    args = ap.parse_args(argv)

    records = export_ownership_verdicts.load_map(args.map)
    verdicts = export_ownership_verdicts.load_verdicts(args.verdicts)
    assessed = assess(records, verdicts, entry_reachability.read_image())

    if args.csv:
        write_csv(assessed)
        return 0
    if args.rows:
        for row in assessed:
            print("%-16s %-7s %-6s A=%-11s B=%-3s %s"
                  % (row["out_file"], row["program"], row["addr"],
                     row["named_by_transfer"], row["instruction_start"],
                     row["verdict"]))
        return 0
    print(report(assessed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
