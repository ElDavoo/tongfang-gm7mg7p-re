#!/usr/bin/env python3
"""Hold every capture claim in the committed prose to the capture it names.

`check_register_counts.py` recomputes `registers.yaml`'s *numeric keys* from
the firmware image. It never opens a `note:`, so a note can attribute a
movement to a committed capture, with a row count, and nothing disagrees.
That has been wrong twice in this file's history: issue #265, and the
`0x07D4` clause issue #270 had to retract in place. Both were caught by a
re-reading, because no check read the sentence.

So this walks the same prose `check_cluster_citations.py` walks -- it imports
that tool's `units()` rather than writing a second sentence splitter, so a
fix to the splitting logic (issue #273) lands once and both checkers get it,
and the shared module stays the only place that knows how a sentence ends.
For every unit naming an `evidence/ec-watch/*.csv` capture it holds two
things against that file:

  * **address presence** -- an address the unit attributes to the capture
    has to have a row in it;
  * **row count** -- a count the unit states for an address has to equal the
    real count for that address in that file.

Both are decidable against a fixed committed artifact, which is what makes
them worth automating: a capture does not move under a re-run, so a
disagreement is a fact about the prose rather than a race to be re-tried.

**What this does not check, which is as much of the point:**

  * *Denials.* A unit that says an address did *not* move in a capture is
    skipped rather than checked, so "0x07D4 did not move" is never verified
    and a denial that has itself gone stale is not caught. That is the rule
    that keeps `registers.yaml`'s `0x07D1` correction -- a 24-address denial
    naming the capture -- green, and it is the one skip with a known blind
    side to it. It costs real coverage, not hypothetical: the same rule
    skips `findings.md` §4g's "`0x0436` moving 4 times ... and `0x0437`
    never moving", because the denial is in the same sentence.
  * *A table whose capture is named above it.* `units()` makes a table row
    its own unit, so the six-row `changes` column in
    `xdata-0400-045f.md` §8 -- 247/238/180/4/4/1, all of them correct -- is
    not read: the capture is named in the paragraph before the table, not in
    the rows. This is the mis-paired-split problem issue #273 is about, and
    fixing it here would mean editing the walker both tools share. A reader
    looking at that column should not assume this tool read it.
  * *Range bounds.* An address that is a bound of an `A-B` range in the unit
    (`0x0700-0x07FF`, the `0x07C0-0x07D7` block) names a watched window, not
    a byte that moved, and neither bound is expected to have a row. 4 units.
  * *Word numerals.* The count rule reads digits, so a count spelled out --
    "carries two rows" -- is held by the presence rule alone. Reading
    numerals would go the other way too: "changed exactly one non-sensor
    byte ... once per switch" is three rows, and a word-count rule would
    read it as one.
  * *Numbers that are not row counts.* A count is a number immediately
    followed by `times`/`changes`/`rows` and bound to a nearby address.
    Everything else is left alone: `32499` is the row count of the full
    sweep log the committed summary was derived from, and `102`/`449`/`297`
    are paired-sample figures over a derived set. All four are true; none is
    a row count for a named address.
  * *Which* of several named captures an address is in. A unit naming two
    captures is satisfied if the address is in either, and a count is
    satisfied if it matches either. The same weaker sense
    `check_cluster_citations.py` gives "a unit naming two clusters", and the
    same reason: it catches a wrong number, not a wrong pairing.
  * *`.txt` captures.* The four `.txt` files in `evidence/ec-watch/` are
    `ecrw.py dump` output -- one is a hex dump, one a value listing -- and
    have no row-per-change shape to count. A unit naming one is reported as
    skipped rather than passed over in silence.
  * *Addresses the unit does not name.* A count resolves to the enclosing
    `registers.yaml` entry's `addr:`, because the sentence usually does not
    write the address it is about ("Moved 238 times ... the second-busiest
    byte on the page after 0x044C" is about `0x0449`, and binding it to the
    nearest address in the text gets it backwards). Where that entry's
    `addr:` is a list, the subject is two addresses and neither is chosen, so
    the count is not checked; the nearest-address fallback applies only to
    prose with no YAML entry around it.
  * *An `addr:` key.* A `registers.yaml` entry's own `addr:` line declares
    which address the entry is about; it does not say the address moved in a
    capture, so the presence rule reads the note and not the header.
  * *Markdown and YAML only.* A capture named in a `.py` docstring
    (`windows/tools/system_id_probe.py`) is not walked. No code address is
    filtered: this has no census to filter against, the way the cluster
    checker has `xdata-registers.csv`, so a code address that collides with
    an XDATA one in a unit also naming a capture is a possible false
    failure. None is in the tree as merged.
  * *A bare date in prose, and therefore the `addr`-column question.* This tool
    resolves a capture out of a path a unit names, and a bare date is not a
    path: `captures_in()` finds one in 0 of the 100 units of the testdata
    index's third column, which is the whole of the deferral #975 measured
    and then declined to build on here. Giving it the date resolution is a
    separate piece of work, and it is not a small one -- over the 309 units
    of `ROOTS` whose bare date resolves to a capture, holding each unit's
    literals to the `addr` column puts 124 literals MISSING against 56 that
    hold, and 17 of the misses are EC code addresses at or above `0x8000`
    for which the "no code census to filter against" caveat above is the whole
    story. That is a blanket rule turning a green run red, so the dated
    columnar read is `check_testdata_row_claims.py`'s, where the date is
    already resolved and the corpus is two claims' worth.

Every one of those is "not found by this method", never "absent" -- the same
caveat `ec/annotations/registers.yaml` carries for a static scan. The
`0x07B9`/`0x07D0`/`0x07D1` absence `docs/findings.md` §4g rests on is a
*finding*, not a defect: this tool never prints it, and never touches a
`status:`. Passing means the checked sentences agree with the CSVs beside
them; it does not mean the prose is right about the firmware.

The surface is small and the closing line says how small: on the tree as
merged this checks five address-presence claims and two row counts, in
`ec/annotations/registers.yaml` (the `XDATA_0449` and `GPU_DYNAMIC_BOOST_STATUS`
notes) and `docs/hardware-tests/system-id-0456-bit6-divisor.md` §5. A corpus
scan over the same roots finds 19 units naming a `.csv` capture at all (and 10
more naming one of the `.txt` ones); the rest are
the skips above, several of which are deliberate and one of which -- the
`xdata-0400-045f.md` §8 table -- holds true claims this tool cannot reach.
That count is a number to read, not a target: a re-run prints it, so a
future change that widens or narrows the surface is visible rather than
silent.

**The run also reports on itself at file granularity, and that is #975's
half.** A file that yields no claim is named in `--verbose` and counted on a
line of its own, because the `N capture claims checked` figure covers claims
and cannot be decomposed -- and almost every file under `ROOTS` names none, so
without the count those files looked like files nobody opened. The census is
in `docs/findings/testdata-addr-column-claim.md`, which is where a number
belongs; the figure is deliberately not written here, because a file count
quoted in a docstring is invalidated by the next document added to the tree and
this paragraph is one a future `docs/` file invalidates. A per-*unit* line is
declined for the same reason the count is enough: the corpus is 27,032 units,
so that is not a `--verbose` anyone runs.

Usage:
    python3 ec/tools/check_capture_claims.py [--check] [--verbose]
"""
import argparse
import csv
import os
import re
import sys

# The walker, not a copy of it. Issue #273 is about the shared weaknesses in
# this splitting logic, and the narrowest coordination that serves both tools
# without doing #273's work is one import: tools run with their own directory
# on sys.path, the way check_register_counts.py imports trace_xdata_refs.
from check_cluster_citations import units

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
ROOTS = ("ec", "docs", "evidence", "windows")

# Where a named capture is looked up. testdata/ is here so a negative case can
# be a real capture file next to a real sentence rather than an injected dict:
# the testdata README's rule is that a fixture carries a `constructed` header
# and a 2026-01-01 timestamp, which is also what keeps it apart from a
# capture at a glance.
WATCH = "evidence/ec-watch"
FIXTURES = "ec/tools/testdata"

PROSE = (".md", ".yaml", ".yml")

# The prefix is case-insensitive because a `.upper()` on the whole token
# before matching turns every `0x0449` in a capture into `0X0449`, and a
# checker that quietly finds zero references under that mistake is a checker
# that passes by checking nothing.
ADDRESS = re.compile(r"0[xX]([0-9A-Fa-f]{4})\b")
FILE_TOKEN = re.compile(r"[\w./-]*[\w-]+\.(?:csv|txt)\b")

# A unit only claims a capture changed something if it says something
# changed. A filename next to an address is not a claim, and the units that
# say so most plainly are the ones that need it: `evidence/README.md`'s entry
# for the two power-mode captures, and the door procedure's preamble, which
# names both captures precisely so nobody mistakes them for a run.
MOVEMENT = re.compile(
    r"\b(?:mov(?:e|es|ed|ing)|chang(?:e|es|ed|ing)|writ(?:e|es|ing|ten)|wrote"
    r"|land(?:ed|s|ing)|step(?:s|ped|ping)|tick(?:s|ed|ing)"
    r"|climb(?:s|ed|ing)|carri(?:es|ed)|rows?|record(?:ed|s|ing)?"
    r"|show(?:s|ed|ing)?|drift(?:s|ed|ing)|ramp(?:s|ed|ing)"
    r"|go(?:es|ing)?|went|publish(?:ed|es|ing)|saw|seen|observed)\b",
    re.IGNORECASE,
)

# Phrases that take an address *out* of a capture's movement. These units are
# skipped, not checked: see the docstring.
DENIAL = re.compile(
    r"\b(?:did|does|do|was|were|has|have|had)\s+not\b"
    r"|\bnever\b"
    r"|\bno\b[^.;]{0,80}?\b(?:rows?|changed?|moved?|written)\b"
    r"|\bnot\b[^.;]{0,40}?\b(?:written|found|present|appear\w*|occur\w*)\b"
    r"|\bwithdrawn\b"
    r"|\bomit(?:s|ted)?\b"
    r"|\bquiet\b"
    r"|\bunchanged\b",
    re.IGNORECASE,
)

# A count is a number immediately followed by a movement noun, so that a
# version string, a timestamp, a sensor value and a derived paired-sample
# figure are all outside it by construction. `32499 recorded byte changes` is
# the shape that fixes "immediately": the noun is two words away, and what
# 32499 counts is the full log, not a row of the committed summary.
COUNT = re.compile(r"\b(\d+)\s+(?:times?|changes?|rows?)\b", re.IGNORECASE)

# How far a count looks for the address it is about, either side, in prose
# with no YAML entry to carry the subject down from. Wide enough for "`0x0449`
# across `0x22`-`0x5A` over 238 changes"; a count with no address that close is
# left to nothing rather than guessed at.
COUNT_WINDOW = 60

# `A-B` bounds a range, and a range bounds a window rather than naming bytes
# that moved in it. The spaces matter: "0x075B - 0x075C" in a sentence about
# a difference is the same shape as a window, and both are skipped.
RANGE = re.compile(
    r"0x[0-9A-Fa-f]{4}\s*(?:-|–|—|to)\s*`?0x[0-9A-Fa-f]{4}`?")

# A registers.yaml entry, and the `addr:` key inside one. Tracked over the raw
# lines rather than through pyyaml because pyyaml discards line numbers, and
# the report has to be able to point at one.
ENTRY = re.compile(r"^\s*-\s+name:")
ADDR_KEY = re.compile(r"^\s*addr:\s*(\[?)(0x[0-9A-Fa-f]{4})\b")

# Three answers to "which entry is this line in", not two. A scalar `addr:`
# names the entry's subject; a list `addr:` names two or more and picking one
# would be the guess this tool exists to stop making; no match at all is prose
# outside a YAML entry, where the nearest address is the only thing there is.
AMBIGUOUS = object()


def normalise(address: str) -> str:
    """`0x0449` and `0X0449` are one address; the file's spelling is not."""
    return "0x" + address[2:].upper()


def read_capture(path: str):
    """(count per address, rows, distinct addresses) for one capture.

    A capture is a change log, so a row is a change and counting rows counts
    changes. The AC-plugin sweep summary is the exception: it is a derived
    per-address summary, one row per address with the change total in a
    `change_count` column, so its counts come from that column rather than
    from a row tally -- a row tally would report 1 for an address that
    changed a thousand times.

    `#` comment lines are dropped before the header is read, not after:
    `2026-09-18-ac-plugin-sweep-summary.csv` opens with three of them, and a
    naive DictReader takes a comment as the header and yields three garbage
    fieldnames -- which reads as "the file has no addr column" rather than as
    a parser that skipped what it should not have.

    `utf-8` is declared, as every other reader and writer of this shape
    declares it. This is the reader that walks the whole committed corpus, so
    it is the one most likely to meet a file a foreign writer produced, and
    the codec is the format's rather than whatever this process's locale
    prefers.
    """
    with open(path, newline="", encoding="utf-8") as f:
        lines = [line for line in f if not line.lstrip().startswith("#")]
    rows = list(csv.DictReader(lines))
    derived = bool(rows) and "change_count" in rows[0]
    per = {}
    for row in rows:
        address = normalise(row["addr"]) if row.get("addr") else None
        if not address:
            continue
        if derived:
            try:
                per[address] = per.get(address, 0) + int(row["change_count"])
            except (TypeError, ValueError):
                per[address] = per.get(address, 0) + 1
        else:
            per[address] = per.get(address, 0) + 1
    return per, len(rows), len(per)


def captures_in(unit: str):
    """(named captures, named non-csv captures) in one unit.

    A path is resolved repository-relative, and `ec-watch/...` -- how
    `evidence/README.md` names its own files -- is the same file with the
    `evidence/` prefix implied. Anything that resolves to a `.txt` is
    reported rather than dropped, so "this is outside the oracle" stays
    visible in `--verbose` instead of being indistinguishable from "nothing
    to check".
    """
    csvs, others = set(), set()
    for token in FILE_TOKEN.findall(unit):
        path = token.strip("`'\"()[]")
        if path.startswith("./"):
            path = path[2:]
        if not path.startswith((WATCH + "/", FIXTURES + "/")):
            continue
        (csvs if path.endswith(".csv") else others).add(path)
    return sorted(csvs), sorted(others)


def address_tokens(unit: str):
    """(address, offset) for each address, in reading order."""
    return [(normalise(m.group(0)), m.start()) for m in ADDRESS.finditer(unit)]


def range_bounds(unit: str):
    """The addresses that bound an `A-B` range, which are not movers."""
    bounds = set()
    for m in RANGE.finditer(unit):
        bounds |= {address for address, _ in address_tokens(m.group(0))}
    return bounds


def unit_lines(lines, lineno, unit):
    """(source line number, that line's share of the unit) for each line.

    `units()` hands back a joined paragraph and the line it starts on, and
    this puts the two back together, which is what lets a report point at
    the line an address is *on* rather than the line the unit opens on. In a
    wrapped sentence the capture and the address it is wrong about are often
    not on the same line, and a report that points at the wrong line is
    worse than none.

    Spelled out here rather than imported from check_cluster_citations,
    whose `line_of_address` re-splits the unit it is given and so counts
    lines from 1 inside a string that has already lost the file's numbering.
    It cannot answer this question; its own caller does not notice, because
    the answer it gets is 0 and the `or lineno` fallback covers the one
    shape its test uses.
    """
    seen = 0
    for n in range(lineno, len(lines) + 1):
        stripped = lines[n - 1].strip()
        if not stripped:
            return
        yield n, unit[seen:seen + len(stripped)]
        seen += len(stripped) + 1


def count_subject(unit: str, offset: int, entry):
    """The address a count at `offset` is about, or None if there isn't one.

    The enclosing entry's `addr:` wins, because that is the shape the count
    claims are written in: XDATA_0449's note says "Moved 238 times in
    ... the second-busiest byte on the page after 0x044C" and never writes
    `0x0449` at all. Proximity is only the fallback for prose with no entry
    to carry down, and it is the wrong first answer even where it applies:
    `0x044C` there is the *comparison*, not the subject, so a rule that
    bound the count to the nearest address in the text would compare 238
    against 247 and report a disagreement that does not exist.

    Within `COUNT_WINDOW` either side, nearest wins. The window is what keeps
    a derived figure -- a version number, a sensor value -- from being read
    as being about an address it merely sits near.
    """
    if entry is AMBIGUOUS:
        return None
    if entry:
        return entry
    nearest = None
    for address, at in address_tokens(unit):
        if abs(at - offset) <= COUNT_WINDOW and (
                nearest is None or abs(at - offset) < nearest[1]):
            nearest = (address, abs(at - offset))
    return nearest[0] if nearest else None


def entry_subjects(lines):
    """{line number: the entry subject in force at that line}.

    A note is a YAML block scalar, so its own lines carry no `addr:`; the
    value has to be carried down from the key above it.
    """
    subjects = {}
    current = None
    for lineno, line in enumerate(lines, 1):
        key = ADDR_KEY.match(line)
        if key:
            current = AMBIGUOUS if key.group(1) else normalise(key.group(2))
        elif ENTRY.match(line):
            current = None
        subjects[lineno] = current
    return subjects


def entry_subject(lines, subjects, lineno):
    """The entry subject for a unit that starts on `lineno`.

    Forward as well as backward, because a unit can begin on the `- name:`
    line and run on into the note -- `units()` joins a block scalar into the
    paragraph above it -- and at that line the entry has no `addr:` yet. The
    scan stops at the blank line or the next entry, so a unit that lies
    outside any note still resolves to nothing rather than to the address of
    whichever entry comes next.
    """
    if subjects[lineno] is not None:
        return subjects[lineno]
    for later in range(lineno + 1, len(lines) + 1):
        line = lines[later - 1]
        if not line.strip() or ENTRY.match(line):
            return None
        if subjects[later] is not None:
            return subjects[later]
    return None


def check(path, index, verbose):
    """(problems, lines read, claims checked) for one file.

    Each problem is (repo-relative path, lineno, capture, address, kind,
    stated, real) -- `kind` is `presence` or `count`, `stated` is the count
    the prose gave or None, and `real` is what the file has. The path is made
    relative here rather than in `main`, so the report can name a file it has
    already walked.

    The third element of the return is what keeps the tool honest about
    itself: a run that checked nothing prints `0`, and a reader who sees
    that on a green gate knows the surface is empty rather than the check
    having silently stopped working. A number in the output, not a floor --
    see `docs/agent-pipeline.md` on why a gate here does not grow one.
    """
    problems = []
    checked = 0
    where = os.path.relpath(path, REPO)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    subjects = entry_subjects(lines)

    for lineno, unit in units(text):
        captures, others = captures_in(unit)
        if others:
            if verbose:
                for name in others:
                    print(f"  skip (capture is not a .csv) {where}:{lineno} {name}",
                          file=sys.stderr)
            continue
        if not captures:
            continue
        if DENIAL.search(unit):
            if verbose:
                print(f"  skip (denies movement) {where}:{lineno}", file=sys.stderr)
            continue
        if not MOVEMENT.search(unit):
            if verbose:
                print(f"  skip (no movement claim) {where}:{lineno}", file=sys.stderr)
            continue
        absent = [c for c in captures if c not in index]
        if absent:
            if verbose:
                print(f"  skip (capture not in the tree) {where}:{lineno} "
                      f"{', '.join(absent)}", file=sys.stderr)
            continue

        # Which addresses the unit actually *says* something about, and on
        # which line. A registers.yaml `addr:` key is a declaration -- this is
        # the address the entry is about -- and says nothing about whether it
        # moved in a capture, so it is left out. The distinction has to be
        # per line and not per file: 0x044C is XDATA_044C's own `addr:` and is
        # also named in XDATA_0449's note, where the mention is a claim and
        # this check is the one that holds it to 247 rows.
        spoken = {}
        for n, chunk in unit_lines(lines, lineno, unit):
            if ADDR_KEY.match(lines[n - 1]):
                continue
            for address, _ in address_tokens(chunk):
                spoken.setdefault(address, n)

        bounds = range_bounds(unit)
        for address, at in spoken.items():
            if address in bounds:
                if verbose:
                    print(f"  skip (range bound) {where}:{at} {address}",
                          file=sys.stderr)
                continue
            checked += 1
            if any(index[c][0].get(address) for c in captures):
                continue
            for capture in captures:
                _, rows, distinct = index[capture]
                problems.append((where, at, capture, address,
                                 "presence", None,
                                 f"{rows} rows, {distinct} distinct addresses"))

        subject = entry_subject(lines, subjects, lineno)
        for m in COUNT.finditer(unit):
            address = count_subject(unit, m.start(), subject)
            stated = int(m.group(1))
            if address is None:
                if verbose:
                    print(f"  skip (count with no address) {where}:{lineno} "
                          f"{m.group(0)!r}", file=sys.stderr)
                continue
            checked += 1
            if any(index[c][0].get(address, 0) == stated for c in captures):
                continue
            at = spoken.get(address, lineno)
            for capture in captures:
                problems.append((where, at, capture, address,
                                 "count", stated, index[capture][0].get(address, 0)))

    if verbose:
        # The two halves of one self-report. A file that yielded a claim is
        # named with the count; a file that yielded none is named too, because
        # `if not captures: continue` above is the one skip in this function
        # that used to be silent, and a file read in full and finding nothing
        # is otherwise indistinguishable, in `--verbose` and in the summary
        # alike, from a file nobody opened. The summary counts the same set,
        # so neither reading stands alone.
        if checked:
            print(f"  {where}: {checked} claim(s) checked", file=sys.stderr)
        else:
            print(f"  {where}: read in full, no claim to check", file=sys.stderr)
    return problems, len(lines), checked


def report(problems):
    """Print each disagreement, and return how many there were.

    `problems` carries the repository-relative path already, so the line
    prefix is a join and not another `relpath` -- running one over a relative
    path resolves it against the current working directory, which turns
    `ec/annotations/registers.yaml` into a chain of `../..` on any run from
    outside the repository root. A report nobody can paste into an editor is
    a report nobody opens.
    """
    for path, lineno, capture, address, kind, stated, real in problems:
        where = f"{path}:{lineno}"
        if kind == "presence":
            print(f"{where}: {address} is attributed to a change in `{capture}`, "
                  f"and this read of that file found no row for it ({real})",
                  file=sys.stderr)
        else:
            print(f"{where}: {address}: the note says {stated} in `{capture}`; "
                  f"that file has {real}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} capture claim(s) disagree with the committed "
              f"captures under {WATCH}/", file=sys.stderr)
        print("A disagreement here is a defect in the prose. It is not a reason "
              "to change a register status.", file=sys.stderr)
    return len(problems)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="check the committed prose against the committed "
                         "captures (the default, and the gate's entry point)")
    ap.add_argument("--verbose", action="store_true",
                    help="report every unit skipped, and why")
    args = ap.parse_args()

    index = {}
    for name in sorted(os.listdir(os.path.join(REPO, WATCH))):
        if name.endswith(".csv"):
            index[WATCH + "/" + name] = read_capture(os.path.join(REPO, WATCH, name))

    paths = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, root)):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            paths += [os.path.join(dirpath, f) for f in sorted(filenames)
                      if f.endswith(PROSE)]
    paths.sort()

    problems = []
    read = checked = 0
    uncounted = 0
    for path in paths:
        found, lines, seen = check(path, index, args.verbose)
        problems += found
        read += lines
        checked += seen
        if not seen:
            uncounted += 1

    if report(problems):
        return 1
    print(f"{len(paths)} files / {read} lines / {checked} capture claims checked "
          f"against {len(index)} committed captures: every checked claim agrees "
          "with the capture it names")
    # On its own line, and that is a constraint rather than a style: the suite
    # parses the claim count out of the line above by splitting on
    # `' lines / '`, so anything appended to it moves what that split returns.
    print(f"{uncounted} of those {len(paths)} file(s) were read in full and "
          f"named no capture claim; `--verbose` names each one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
