#!/usr/bin/env python3
"""Read `ec/annotations/ghidra-functions.csv`'s `evidence` column in both directions.

`CLAUDE.md` calls that column mandatory and non-empty, and #780 taught
`check_testdata_index.py` to resolve an `evidence` column against the
repository root -- pointed at two **fixture** CSVs holding eleven tokens. The
annotation CSV is the one that matters, it holds thousands of them, and until
now nothing read it. This reads it twice: forwards, every token answered
against the disk, and backwards, every committed `.asm` the column names or
does not.

**The forward half is that check widened, and it is imported rather than
rewritten.** `evidence_pointers()` and `names_a_file()` come from
`check_testdata_index.py`, so the `;`-split, the by-name column read, the three
verdicts and the calibration wording are one implementation and not two that
can come to disagree. A second reader of an `evidence` column would answer "does
this path exist" with its own idea of what a path is, and the two answers would
differ on the first shape neither was written for. The widened check itself is
in that file, reached by the no-argument call the prepared gate patch makes; this
prints its numbers beside the reverse direction, and the reverse half lives here
because `check_testdata_index.py`'s subject is the `testdata/` tree and
`ec/decompiled/**` is not under it.

**The reverse half is a census and not a check, and the split is the design.**
It exits 0 with findings in hand and non-zero only when it located nothing, the
`census_test_line_pins.py` convention: a census that found 822 uncited listings
and one that read no listing at all both print, and only the second may claim
the run was broken. A gated reverse direction would go red the next time a
decompile export lands a listing nobody has read yet, which is the ordinary
state of an unfinished reconstruction rather than a defect -- and the count is a
value every merge has to edit, which is the trap `CLAUDE.md` names four times.
`docs/findings/annotation-evidence-both-directions.md` records the decision in
full.

**Four classes, each computed rather than subtracted.** A listing is
*unannotated* when no row sits at its `(scope, addr)`; *cited elsewhere* when
one does and its `evidence` names no `.asm`; a *deliberate `0xFF` fill* read
through `citation_callers.is_fill`, imported for the reason `census_ff_fill.py`
gives, so this tool and the `call_graph.py` veto cannot come to disagree about
the population; and *not yet exported* when the listing's `.c` sibling is absent
from `index.csv`'s `out_file`. Each is a predicate over committed files and each
is printed even at zero -- a zero that is computed is an answer and a zero that
is a subtraction is a coincidence.

The chain is ordered so each test still has a population left to test, and it
has two exits into `cited elsewhere`: a row that names no `.asm` at all, and a
row that names a *different* `.asm`, which is the case the issue warns about.
They are one class because both answer the same question -- the listing is
uncited and there is an annotation for its address pointing somewhere else --
and the sub-count printed under the table is what says which.

**And the population is a set difference, not a subtraction of two totals.** A
row naming an address with no listing behind it is the other mismatch, it is
reported on its own line, and the two are not allowed to cancel. That is
`pd_unannotated_census.py`'s rule: subtracting two totals is the same number
today and is wrong the first time either side moves alone.

**The limit, stated rather than met.** This splits the uncited set by *kind of
file* and by *which rule found it*. It does not split it by **reason**, and
every listing it prints as unannotated prints as "not named by this method".
Whether a listing is one nobody has read yet or a one-instruction trampoline
that will never be worth a row is a reading, and a tool that guessed one would
produce a figure nobody here can check. That is the same line
`ec/annotations/registers.yaml` draws for a static scan, and **no negative
printed by this tool is "absent"**.

**Nothing here is a behavioural claim.** No EC image is opened, no register is
read, and nothing was observed on hardware: every input is a committed file. A
listing being uncited is a statement about `ghidra-functions.csv`, not about
what the EC does at that address.

**This is not in `.github/scripts/agent-gates.sh`, and cannot be from an agent
branch** -- the plan stage's push token has no `workflow` scope. It runs by
hand, which is where `census_test_line_pins.py` and `census_ff_fill.py` stand
today.

Usage:
    python3 ec/tools/census_evidence_citations.py
    python3 ec/tools/census_evidence_citations.py --verbose
"""
import argparse
import collections
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
sys.path.insert(0, HERE)

# The two readers this tool does not have. `evidence_pointers()` is the whole of
# the forward direction -- the `;`-split, the by-name column read, the three
# verdicts and the "not checked, not absent" calibration all live in it -- and
# `is_fill()` is the only implementation here of "is this listing an unbroken
# 0xFF run". Reimplementing either is the second-reader defect the module
# docstring names.
from check_testdata_index import evidence_pointers  # noqa: E402
from citation_callers import is_fill, norm_addr  # noqa: E402

# The annotation CSV, by the two names a caller points it at. It lives outside
# `ec/decompiled/`, so `evidence_pointers`'s own `directory` argument is what
# makes it reachable with no new shape in that function.
ANNOTATIONS_CSV = "ghidra-functions.csv"
ANNOTATIONS = os.path.join("ec", "annotations")
DECOMPILED = os.path.join("ec", "decompiled")
INDEX_CSV = "index.csv"

# What "names a listing" means, against what `names_a_file()` means. That
# function asks "is this spelled like a path" and the answer is yes for a `.md`,
# which is the right answer for it and the wrong one here: the question below is
# narrower -- does this token point at a decompiled listing -- and only the
# narrower one decides what the reverse direction is measuring. Used for
# reporting; the forward direction's verdicts never come from here.
LISTING_SUFFIXES = (".asm", ".c")

# The four classes, in the order the chain tests them, and printed in it so a
# reader can see which rule answered for a listing rather than inferring it from
# a column heading.
UNANNOTATED = "unannotated"
CITED_ELSEWHERE = "cited elsewhere"
FILL = "deliberate 0xFF fill"
NOT_EXPORTED = "not yet exported"
CLASSES = (UNANNOTATED, CITED_ELSEWHERE, FILL, NOT_EXPORTED)

# The two exits into `cited elsewhere`, named so the counter under the table can
# say which one a listing took. See the docstring's second paragraph in §"Four
# classes".
NO_ASM = "names no .asm at all"
ANOTHER = "names another listing"

# What one run measured. `forward` is `check_testdata_index.Evidence` -- not a
# copy of it, the namedtuple that reader returns -- so a reader can compare the
# two tools' verdicts field for field rather than trusting that they agree.
#
# `classes` is {area: {class: [relpath, ...]}} over the *uncited* set only and
# `listed` is {area: [addr, ...]} over everything on disk, so the per-area
# denominator and numerator sit beside each other without either being derived
# from the other.
Census = collections.namedtuple(
    "Census", "forward empty document listed named classes uncited orphans "
    "elsewhere out_file_tokens out_file_missing")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tokens_in(cell):
    """Every `;`-separated token in one `evidence` cell, trimmed and non-empty.

    The split is `check_testdata_index.evidence_pointers`'s, and this is not
    the forward direction: the *verdict* for each token is that function's,
    computed over the CSV itself, and this returns tokens only so the reverse
    direction can ask which listings a column names. Two `;`-splitters would be
    two things to keep in step; one is a shared rule with a shared
    implementation.
    """
    return [token.strip() for token in (cell or "").split(";") if token.strip()]


def names_a_listing(token):
    """Whether a token points at a decompiled listing rather than a document.

    The suffix, and not `names_a_file()`'s extension test. That function's
    question is "is this spelled like a path", which a `.md` passes; this one's
    is "does this name a listing", which is the narrower question the reverse
    direction's numerator turns on.
    """
    return token.endswith(LISTING_SUFFIXES)


def listing_key(area, addr):
    """One listing as the `evidence` column spells it: from the repository root.

    This is the *join key* between the two directions -- a cell names a path
    relative to the repository root and the walk found a file under
    `ec/decompiled/` -- so it is spelled the column's way and never
    repository-prefixed. A key built from an absolute root matches no cell,
    which is a reverse direction that reports every listing on disk as uncited
    and reads as a result. Opening a file wants the root joined back on; the key
    is what the two halves agree on, and the two are not the same string.
    """
    return os.path.join(DECOMPILED, area, addr + ".asm")


def listed_asm(decompiled):
    """{area: [addr, ...]} for every committed `.asm` under `decompiled`.

    `.asm` only and never the `.c` beside it, for `pd_unannotated_census.py`'s
    reason: the two are one function, so counting both would double the
    population and then have to be divided back out. The address is the
    filename's own stem, which is the four-digit spelling the whole set is
    matched on, read through `citation_callers.norm_addr` so a row spelled
    `0x0ea2` and a file named `0EA2.asm` are the same function.
    """
    areas = {}
    for name in sorted(os.listdir(decompiled)):
        directory = os.path.join(decompiled, name)
        if not os.path.isdir(directory):
            continue
        areas[name] = sorted(norm_addr(stem[:-4]) for stem in os.listdir(directory)
                             if stem.endswith(".asm"))
    return areas


def named_listings(rows):
    """{relpath} for every distinct `.asm` some `evidence` cell names.

    Normalised through `os.path.normpath` because the column is written by hand
    and `ec/decompiled//bank0/0EA2.asm` names the same file as the spelling
    beside it. Unnormalised, a hand edit would read as an uncited listing and
    this tool would report a path the disk holds.
    """
    named = set()
    for row in rows:
        for token in tokens_in(row.get("evidence")):
            if token.endswith(".asm"):
                named.add(os.path.normpath(token))
    return named


def rows_by_listing(rows):
    """{(scope, addr): [row, ...]} over the annotation CSV.

    A list rather than one row because two rows at one address are a defect this
    census is not here to adjudicate, and keeping only the first would hide it
    behind a count that then means something else.
    """
    out = collections.defaultdict(list)
    for row in rows:
        out[(row["scope"], norm_addr(row["addr"]))].append(row)
    return out


def exported(csv_path):
    """({out_file}, tokens, missing) from `index.csv`, resolved at its own base.

    **A second base, and the reason this function exists separately.** `index.csv`
    holds two pointer columns and they resolve against different roots:
    `out_file` is written from `ec/decompiled/` (`bank0/031C.c`) while
    `evidence` in the same file is written from the repository root
    (`ec/decompiled/bank0/031C.asm`). One file, two bases, so a reader of one
    column has to say which it used -- which is why `report()` prints the pair
    and why `missing` is measured against `decompiled` rather than the root.
    Resolving `out_file` at the root would call every one of them absent, and
    would then put every listing in the tree into `not yet exported`.
    """
    out, tokens, missing = set(), 0, 0
    if not os.path.isfile(csv_path):
        return out, tokens, missing
    for row in read_csv(csv_path):
        token = (row.get("out_file") or "").strip()
        if not token:
            continue
        tokens += 1
        out.add(token)
        if not os.path.exists(os.path.normpath(
                os.path.join(os.path.dirname(csv_path), token))):
            missing += 1
    return out, tokens, missing


def classify(rowset, filled, out_files, area, addr):
    """Which of the four classes one uncited listing is, and which exit it took.

    The chain is over predicates, not over counts, and it is ordered so each
    test still has a population left to test. `unannotated` is a set difference
    over matched addresses rather than a subtraction of two totals, per
    `pd_unannotated_census.py`; the two `cited elsewhere` exits are the two
    shapes the issue names separately, a row citing no `.asm` and a row citing a
    *different* one, and the second return value is which.

    It takes no path and asks no question about *this* listing's own citation,
    because a listing that a cell named is not in the uncited set to begin with
    -- the filter is upstream. A caller reusing this over the cited set would
    want that test back, and it is deliberately not here to be mistaken for the
    general form.
    """
    if not rowset:
        return UNANNOTATED, None
    if not any(token.endswith(".asm") for row in rowset
               for token in tokens_in(row.get("evidence"))):
        return CITED_ELSEWHERE, NO_ASM
    if filled:
        return FILL, None
    if "%s/%s.c" % (area, addr) not in out_files:
        return NOT_EXPORTED, None
    return CITED_ELSEWHERE, ANOTHER


def census(repo=None):
    """The whole measurement, as a `Census`.

    Every path is derived from `repo` rather than from the module globals, so a
    fixture tree is read through the same function the committed tree is. The
    alternative is a tool whose committed figures and whose suite cases come
    from two different code paths, which is how a census ends up certifying a
    derivation it never ran.

    `repo` is defaulted to the module global **at call time** and not as
    `repo=REPO`, for the reason `check_testdata_index.check()` gives: a
    def-time default binds at import and silently defeats a caller that patches
    the base, so the suite's trees would be read through a path the module
    captured before the patch and the run would be about the committed tree
    while the case believed otherwise.
    """
    if repo is None:
        repo = REPO
    annotations = os.path.join(repo, ANNOTATIONS)
    decompiled = os.path.join(repo, DECOMPILED)
    path = os.path.join(annotations, ANNOTATIONS_CSV)

    forward = evidence_pointers(ANNOTATIONS_CSV, annotations, repo)
    rows = read_csv(path) if os.path.isfile(path) else []
    named = named_listings(rows)
    at_listing = rows_by_listing(rows)
    listed = listed_asm(decompiled) if os.path.isdir(decompiled) else {}
    out_files, out_tokens, out_missing = exported(
        os.path.join(decompiled, INDEX_CSV))

    classes, elsewhere, uncited = {}, collections.Counter(), []
    for area, addrs in listed.items():
        buckets = {name: [] for name in CLASSES}
        for addr in addrs:
            key = listing_key(area, addr)
            if key in named:
                continue
            uncited.append(key)
            rowset = at_listing.get((area, addr), [])
            name, exit_ = classify(
                rowset, is_fill(os.path.join(decompiled, area, addr + ".asm")),
                out_files, area, addr)
            if exit_:
                elsewhere[exit_] += 1
            buckets[name].append(key)
        classes[area] = buckets

    # The other mismatch, reported rather than netted against the uncited set.
    on_disk = {(area, addr) for area, addrs in listed.items() for addr in addrs}
    orphans = sorted(set(at_listing) - on_disk)
    return Census(
        forward,
        sum(1 for row in rows if not (row.get("evidence") or "").strip()),
        [token for row in rows for token in tokens_in(row.get("evidence"))
         if not names_a_listing(token)],
        listed, named, classes, sorted(uncited), orphans, elsewhere,
        out_tokens, out_missing)


def resolved(forward):
    """The token count less the two that were subtracted from it.

    A named helper because the relation is the claim the report's numbers have
    to satisfy and a reader should not have to re-derive it off three printed
    integers. A `columnless` CSV is a fact about the file and counts against no
    token, so this cannot go below zero because of a CSV this tool could not
    read a column out of.
    """
    return forward.tokens - len(forward.missing) - len(forward.unresolved)


def suffixes(tokens):
    """{extension: count} over a token list, for the document tally.

    The shape the issue asked to be counted -- its `.yaml` tokens, its `.md`
    tokens, its one `.csv` -- and the answer to whether the column needs a rule
    per document shape: `names_a_file()` is an extension test, so all of them
    resolve against the repository root on the day the check widens, and a rule
    for a shape the existing rule already reads is a rule that cannot fail.
    """
    return collections.Counter(
        os.path.splitext(token)[1] or "<none>" for token in tokens)


def report(found, out=None, verbose=False):
    """Print both directions. Every number here is derivable from the tree.

    `out` is resolved at call time rather than bound as `out=sys.stdout`, for
    the reason `census()`'s `repo` is: a def-time default captures the stream
    the module was imported with, so a caller that redirects stdout -- which is
    how a run's transcript is read off a scratch tree -- watches the report go
    past it and reads an empty string back.
    """
    stream = sys.stdout if out is None else out

    def say(line=""):
        print(line, file=stream)

    forward = found.forward
    per_area = {area: sum(len(buckets[c]) for c in CLASSES)
                for area, buckets in found.classes.items()}
    totals = {c: sum(len(found.classes[a][c]) for a in found.classes)
              for c in CLASSES}

    say("census_evidence_citations.py -- the `evidence` column of "
        "ec/annotations/%s, both directions" % ANNOTATIONS_CSV)
    say()
    say("forward, every token resolved against the repository root by "
        "check_testdata_index.evidence_pointers()")
    say("  %d evidence cell(s), %d empty, %d evidence path token(s): "
        "%d resolved, %d missing, %d unresolved"
        % (forward.cells, found.empty, forward.tokens, resolved(forward),
           len(forward.missing), len(forward.unresolved)))
    kinds = suffixes(found.document)
    say("  %d of the token(s) name a document rather than a listing (%s): "
        "counted, resolved, and\n  deliberately out of the reverse direction's "
        "numerator, because a row citing a write-up has not cited a listing"
        % (len(found.document),
           ", ".join("%d %s" % (n, k) for k, n in sorted(kinds.items()))
           or "none"))
    for where, token, _note in forward.missing:
        say("    %s: the `evidence` column names `%s`, which is not on disk"
            % (where, token))
    for where, token, _note in forward.unresolved:
        say("    %s: the `evidence` column names `%s`, which this tool cannot "
            "resolve to a path -- not checked, not absent" % (where, token))
    for where, _token, note in forward.columnless:
        say("    %s: %s -- not checked, not absent" % (where, note))
    say("  ec/decompiled/%s carries both bases in one file: `out_file` "
        "resolves against\n  ec/decompiled/ (%d of %d) and `evidence` against "
        "the repository root (%d of %d)."
        % (INDEX_CSV, found.out_file_tokens - found.out_file_missing,
           found.out_file_tokens, forward.tokens - len(forward.missing),
           forward.tokens))
    say()
    say("reverse, every committed .asm named by no token")
    say("  %d committed .asm under ec/decompiled/, %d named by an `evidence` "
        "cell,\n  %d named by none"
        % (sum(len(a) for a in found.listed.values()), len(found.named),
           len(found.uncited)))
    say("  annotation rows naming an address with no listing on disk: %d%s"
        % (len(found.orphans),
           "  (" + ", ".join("%s %s" % pair for pair in found.orphans) + ")"
           if found.orphans else ""))
    say()
    width = max([len(a) for a in found.classes] + [5])
    say("  %-*s  %7s  %8s  %s"
        % (width, "area", "on disk", "uncited",
           "  ".join("%*s" % (max(len(c), 8), c) for c in CLASSES)))
    for area in sorted(found.classes):
        say("  %-*s  %7d  %8d  %s"
            % (width, area, len(found.listed[area]), per_area[area],
               "  ".join("%8d" % len(found.classes[area][c]) for c in CLASSES)))
    say("  %-*s  %7d  %8d  %s"
        % (width, "total", sum(len(a) for a in found.listed.values()),
           len(found.uncited), "  ".join("%8d" % totals[c] for c in CLASSES)))
    say("  the four classes are disjoint and sum to the uncited set, so the "
        "last column\n  is the uncited count decomposed rather than the "
        "uncited count minus something. Of the\n  %d `cited elsewhere`, %d "
        "name no `.asm` at all and %d name a different\n  listing -- the two "
        "shapes the issue names separately, one class."
        % (totals[CITED_ELSEWHERE], found.elsewhere.get(NO_ASM, 0),
           found.elsewhere.get(ANOTHER, 0)))
    if verbose:
        for area in sorted(found.classes):
            for name in CLASSES:
                for listing in found.classes[area][name]:
                    say("    %-20s %s" % (name, listing))
    say()
    say("  every negative above is not named by this method, never absent: a "
        "listing is a Ghidra")
    say("  function boundary and it is on disk. What is missing is a human "
        "reading of it. The")
    say("  class says which rule found the listing, not why nobody has read "
        "it, and a")
    say("  classification by reason would be a guess -- see the write-up. "
        "Closing the %d is"
        % len(found.uncited))
    say("  its own piece of work and needs per-area reading; this sizes the "
        "population and")
    say("  stops. No EC image is opened, no register is read, and nothing here "
        "was observed")
    say("  on hardware.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="name every uncited listing with the class it fell in")
    args = ap.parse_args(argv)

    found = census()
    if not found.forward.tokens:
        print("census_evidence_citations.py: no `evidence` token was read at "
              "all, so neither direction could be walked -- that is a broken "
              "census, not an empty one", file=sys.stderr)
        return 1
    if not found.listed:
        print("census_evidence_citations.py: no committed .asm was found under "
              "ec/decompiled/, so the reverse direction had no population -- "
              "that is a broken census, not an empty one", file=sys.stderr)
        return 1
    report(found, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
