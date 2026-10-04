#!/usr/bin/env python3
r"""Hold the prose to `evidence/ec-watch/2026-09-23-ctgp-live.txt` as a table.

`check_capture_claims.py` asks a capture for an `addr` **column**, because a
claim about an address is a claim about a row keyed on it. That file has no such
column, and not because it is a `.txt`: its header is

    state                    0x0743 0x0744 0x0745 0x0746   enforced.power.limit

-- a table whose **rows are the states a person put the machine in** and whose
**columns are the registers**. The addresses *are* the columns. It is the
capture behind `registers.yaml`'s `CTGP_DB_CTRL / OFFSET` entry, whose live
evidence is that file and nothing else, so the one claim in the repository's
source of truth that rested on a columnless capture had no reader at all.

**A missing column is a refusal, never a disagreement, and that is the whole of
what this reader is.** The columns are the capture's **watch set**: a byte that
is not one was not read in that run, which is not the same sentence as "the
byte did not move", and reporting the two as one is how a table gets held to a
claim it never made. So this emits two answers and no third:

  * **held** -- the address the unit attributes to the capture is a column it
    has. This is the affirmative half, and it is the one worth automating:
    `registers.yaml`'s cTGP note names `0x0743`-`0x0746`, the table has all
    four, and that note's live claim now has something checking it.
  * **not read by this method** -- the unit names something the table cannot
    answer. Named, counted, printed on every run, and **not** a failure.

**Polarity does not enter, and the reason is worth stating rather than leaving
to a reader.** The obvious second rule is to invert the presence check for a
denial, the way `check_capture_claims.py` does -- and it would change no
verdict, because **an address with no column is a refusal under either
polarity**. What it would do is *describe* the claim wrongly:
`docs/hardware-tests/ctgp-dben-07c4-bit3.md`'s "it watched the dGPU's *enforced
power limit*, not `0x07C4`" is a denial, and reporting it as an unread
attribution says the opposite of what the sentence says. Since neither reading
changes a verdict, the polarity walk is left out rather than imported for the
one sentence it would mislabel -- and the refusal's own wording is written to
cover both, which is why it says the byte's movement is unread rather than
saying the capture denies it.

**Presence-only by construction, and the count rule is declined for the same
reason.** A row here is a *state*, not a change: the table records `0x0743` as
`03` on four of its five rows and `07` on the fourth, and from that one can say
the byte was *observed at* those values -- not that it moved twice, and not how
many times, because the rows are not consecutive moments of one run but
interventions a person chose between them. So a count naming this file is
**not read by this method**, is never answered `0`, and does not enter the held
figure: "there is no count in this table" and "the count is zero" are different
sentences and only the first is true. The *presence* half of a counting
sentence is still read, exactly as the checker reads both halves of "`0x0436`
moving 4 times ... and `0x0437` never moving" -- what is refused is the count,
not the sentence.

**Why a new file and not a mode on the checker.** `check_capture_claims.py`
indexes by `has_addr_column()` precisely so that a capture it cannot read a
claim in stays *outside* the oracle and is reported, per unit, as skipped.
Widening its index to "every named capture" would put the `.txt` files in as
empty oracles: `read_capture()` over this one returns `per={}`, because a
`DictReader` over prose has no `addr` fieldname and every row yields `None` --
so every claim naming one would be reported as a disagreement that does not
exist. Routing a *capture* to the reader that can read it is the fix; routing a
*claim* into a reader that cannot is the bug. The census that priced this file
against the four `.txt` captures it declines is in
`docs/findings/capture-claims-column-oracle.md`.

**Nothing here exits 1 on the prose.** The one non-zero exit is a table this
reader cannot parse, which is a broken reader rather than a finding. A run over
the committed tree is green, and it is green because every claim in it was read
-- the held figure is printed for exactly that reason, and a run that read
nothing prints `0`.

**No live run, and nothing is re-derived here.** This reads committed bytes. The
*content* of the capture is a human's live result from 2026-09-23, already
committed and already cited; this holds the prose to it and neither adds nor
confirms a hardware observation.

**Not in any gate.** `.github/` is copied from `ElDavoo/agent-pipeline` and the
branch token has no `workflow` scope, so no `docs/ci/agent-gates-*.patch` is
written and no workflow is touched -- the same reasoning
`check_capture_dates.py` and `check_capture_names.py` are ungated on.
`tools/run-tests.sh` is the only thing that runs this.

Usage:
    python3 ec/tools/read_ctgp_state_table.py [--check] [--verbose]
"""
import argparse
import os
import sys

# The walker, not a copy of it, for the same reason `check_capture_claims.py`
# imports it: one place knows how a sentence ends, and a second splitter here
# would be a second answer to that question one module apart. The tool
# directory is already on sys.path when this runs as a script, and a sibling
# tool does the same for the same reason.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_capture_claims import (  # noqa: E402
    ADDRESS, COUNT, MOVEMENT, ROOTS, WATCH, capture_lines, normalise,
)
from check_cluster_citations import units  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
CAPTURE = WATCH + "/2026-09-23-ctgp-live.txt"

# The refusal's wording, in the vocabulary `ec/annotations/registers.yaml`
# carries for a static scan and `check_testdata_row_claims.py` prints for a
# dated claim with nothing to ask. Held here rather than spelled at each call
# site so the phrase a reader searches for is one string.
NOT_READ = "not read by this method"


def columns(path: str):
    """(the addresses this table has a column for, the header they are in).

    The header is carried back so a reader of the run can see what was read
    rather than only what was concluded, which is the difference between a claim
    a human can check against the file and one they have to take on trust.

    It is the first line that carries something. `capture_lines()` drops the
    comment block for the reason `read_capture()`'s docstring gives -- a `#`
    block taken as a header is a parser that skipped what it should not have --
    and it keeps blank lines, which here is the other half of the same trap:
    this file's `#` block is followed by an empty line before the header, so
    "the first line the filter left" is not the header either. Reading the first
    line that is neither is what makes a change to the comment block invisible
    here, which is the right direction: the columns are what a data row is keyed
    on, and prose *about* them is not them. This file's own comment block names
    its watch set ("`0x0743-0x0746` read-modify-restore"), and reading that as
    the header would find the same four addresses by accident rather than by
    construction.
    """
    for line in capture_lines(path):
        header = line.strip()
        if header:
            return [normalise(m.group(0)) for m in ADDRESS.finditer(header)], header
    return [], ""


def has_column(path: str, address: str) -> bool:
    """Whether `address` is one of this table's columns.

    The one rule. Normalised through the checker's own `normalise()`, so `0X0743`
    in prose and `0x0743` in the header are one address -- an upper() applied
    before the comparison makes every column look absent, and the reader then
    refuses every claim in the tree and still exits 0: a checker that passes by
    reading nothing.
    """
    return normalise(address) in columns(path)[0]


def not_read(capture: str, address: str) -> str:
    """The refusal for a claim this table cannot answer, carrying its reason.

    Returned rather than raised so `report()` prints one vocabulary for "outside
    the oracle" wherever it appears. The address is in it because a refusal
    naming no subject is a refusal the reader has to go and find the subject of.

    **This is not a disagreement**, and the distinction is the reader's whole
    claim to be calibrated. `0x0799` is not in the header because nobody read it
    in that run; the prose naming it was not shown to be wrong, it was not shown
    at all. A run that reported it as a disagreement would be holding prose to a
    capture that says nothing about it -- the same defect as reading "not
    covered" as "absent from what was watched", which
    `check_capture_claims.py`'s own window guard exists to avoid.
    """
    return (f"{normalise(address)} is not a column of "
            f"`{os.path.basename(capture)}`: that table records one value per "
            f"state, so whether the byte moved is {NOT_READ}")


def count_not_read(capture: str, stated: str) -> str:
    """The refusal for a count, which this table cannot express at all.

    Separate from `not_read()` because it is a different claim about a
    different shape: an address that is not a column is unread, and a count is
    unread *even where the address is a column*. `0x0743` is watched in all five
    rows and the table still cannot say it moved three times, because a row is a
    state and not a change.
    """
    return (f"`{stated}` is {NOT_READ} against "
            f"`{os.path.basename(capture)}`: that table records one value per "
            f"state, so it has no per-address change count to compare with")


def check(path: str, capture=CAPTURE, verbose=False):
    """(refusals, lines read, claims held) for one prose file.

    The checker's own three-tuple with its middle word changed, because the
    first is not the same thing: there are no problems here to report, only
    claims that were held and claims this shape cannot answer.
    """
    refusals = []
    held = 0
    where = os.path.relpath(path, REPO)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    for lineno, unit in units(text):
        if capture not in unit:
            continue
        if not MOVEMENT.search(unit):
            if verbose:
                print(f"  skip (no movement claim) {where}:{lineno}",
                      file=sys.stderr)
            continue

        # The count first, because a count is unread whether or not its address
        # is a column, and a unit carrying one has to say so even when its
        # presence claim is held. Refused rather than answered: answering `0`
        # would put a number in the run's output that looks like a measurement
        # of the firmware.
        for m in COUNT.finditer(unit):
            refusals.append((where, lineno, m.group(0),
                             count_not_read(capture, m.group(0))))

        # One claim per address, first mention wins: a unit naming `0x0743` in
        # two clauses is one claim about the byte, and counting it twice would
        # make the run's figure a count of sentences where the claim is about a
        # register.
        seen = set()
        for m in ADDRESS.finditer(unit):
            address = normalise(m.group(0))
            if address in seen:
                continue
            seen.add(address)
            if has_column(os.path.join(REPO, capture), address):
                held += 1
            else:
                refusals.append((where, lineno, address, not_read(capture, address)))

    if verbose:
        if held or refusals:
            print(f"  {where}: {held} claim(s) held against "
                  f"{os.path.basename(capture)}, {len(refusals)} not read",
                  file=sys.stderr)
        else:
            print(f"  {where}: read in full, no claim to check", file=sys.stderr)
    return refusals, len(lines), held


def report(refusals, capture=CAPTURE):
    """Print each refusal, and return how many there were.

    Named and counted on every run rather than only under `--verbose`, because a
    refusal nothing prints is a refusal with no teeth: the whole of what this
    reader contributes over `check_capture_claims.py` skipping the file is the
    reader being able to see it. `check_capture_dates.py` prints its refusals
    the same way and for the same reason.
    """
    for where, lineno, _subject, reason in refusals:
        print(f"{where}:{lineno}: {reason}", file=sys.stderr)
    print(f"{len(refusals)} cTGP state-table claim(s) {NOT_READ} against "
          f"{capture}, and none of them is a disagreement",
          file=sys.stderr)
    return len(refusals)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="hold the committed prose to the committed state "
                         "table (the default; see the note on exits below)")
    ap.add_argument("--verbose", action="store_true",
                    help="report every unit skipped, and why")
    args = ap.parse_args()

    found, header = columns(os.path.join(REPO, CAPTURE))
    if not found:
        print(f"read_ctgp_state_table.py: {CAPTURE} has no address column, so "
              f"no claim can be read in it -- that is a broken reader, not an "
              f"empty table", file=sys.stderr)
        return 1

    prose = (".md", ".yaml", ".yml")
    paths = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, root)):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            paths += [os.path.join(dirpath, f) for f in sorted(filenames)
                      if f.endswith(prose)]
    paths.sort()

    refusals = []
    read = held = 0
    for path in paths:
        found_refusals, lines, seen = check(path, CAPTURE, args.verbose)
        refusals += found_refusals
        read += lines
        held += seen

    report(refusals, CAPTURE)
    print(f"{len(paths)} files / {read} lines / {held} cTGP state-table claim(s) "
          f"held against {os.path.basename(CAPTURE)} "
          f"(`{header}`): every held claim names a column that table has")
    return 0


if __name__ == "__main__":
    sys.exit(main())