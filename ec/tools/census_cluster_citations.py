#!/usr/bin/env python3
"""Inventory every `main-ec-NNN` in the prose, and what each one is doing there.

Issue #274 named the durable citation form and shipped the tool that reads it
-- `annotations/xdata-cluster-names.csv`, keyed by `cluster_key` and resolved by
`check_cluster_citations.py` -- then stopped one step short of moving the prose
onto it, saying so in three places. This is that step's inventory: it walks the
markdown, finds every `main-ec-NNN`, and says which of five shapes it has,
because the five want opposite treatment and only one of them is a live pointer.

**A census and not a check, and it exits 0 with findings in hand.** The count of
occurrences is a value every merge that touches a `main-ec-NNN` moves, which is
the hand-kept-total trap `CLAUDE.md` names; nothing here is asserted and nothing
here goes red. `census_evidence_citations.py`'s convention: a census that read
nothing at all is the only thing that may claim the run was broken, and that is
the one non-zero exit below.

**Five classes, each decided from the text, tested and printed most specific
first**, so a reader sees which rule answered for an occurrence instead of
inferring it from a column heading:

  * `template` -- the literal `main-ec-NNN`, three `N`s. It names the *form*,
    not a cluster, and a name in its place asserts a membership the sentence
    never had.
  * `fenced` -- inside a properly paired fenced block, read through
    `check_cluster_citations.fence_spans()`. Pasted tool output, and the ids in
    it belong to a census the reader cannot open.
  * `census-row` -- a table row whose first cell is exactly one id, which is
    the row `check_cluster_citations.census_row()` reads. This one bites:
    rewrite the first cell and the row stops being a census row at all, and its
    hand-typed size, references, range and named count go unchecked with no
    error anywhere.
  * `quoted` -- a blockquote line. A correction or a quote is the record of
    what an id was said to be and when, which is the one thing a sweep must not
    rewrite.
  * `prose` -- running text. The only class the sweep is for, and not all of
    it: the sweep is for occurrences doing *pointer* work, and whether an id is
    a pointer or is the subject of its sentence is a reading, not a predicate.
    This prints the class; `docs/findings/cluster-name-citation-sweep.md`
    records the decision per occurrence.

**Whether the id is the subject of its sentence is deliberately not a class.**
"`main-ec-003` is credited with 4,966 references" is prose and is about the
rank, and no predicate over the text tells it from "the `main-ec-003` cluster
read as a block". So the tool prints, for every occurrence, the name that id
could carry and the names file's own `note` for it, and leaves the call to a
reader who has the evidence in front of them. That note is the evidence
`ghidra-functions.csv` makes mandatory for the same reason.

**The gate's own answer is reported beside the tool's.** `cited_clusters()`,
`skip_reason()` and `name_re()` come from `check_cluster_citations.py` rather
than being reimplemented, so this inventory and the gate cannot come to
disagree about what a citation is -- a second reader would answer "is this a
membership claim" with its own idea of what a claim is, and the two would
differ on the first shape neither was written for. The consequence is worth
more than the agreement: a `prose` occurrence the gate skips for "no
membership claim" is a real pointer that nothing checks today, and it is
exactly the class where replacing an id with a name changes what is *checked*
rather than only what the page says.

**What this does not do.** It does not decide which occurrences to sweep and it
sweeps none; the write-up records that decision per occurrence. It does not
check membership or any count -- `check_cluster_citations.py` is that, and it
is the gate. It says nothing about whether a name resolves in a *regenerated*
census: `xdata_register_map.py --map` reports how a name was carried, and a
name that resolves today is not thereby evidence the sentence beside it is
right. And no negative it prints is "absent" -- an occurrence it does not list
is one not found by this walk over the files named on the command line.

**Nothing here is a behavioural claim.** No EC image is opened, no register is
read, and nothing was observed on hardware: every input is a committed file.

**This is not in `.github/scripts/agent-gates.sh`, and cannot be from an agent
branch** -- the plan stage's push token has no `workflow` scope. It runs by hand
and from its own suite.

Usage:
    python3 ec/tools/census_cluster_citations.py
    python3 ec/tools/census_cluster_citations.py --all
    python3 ec/tools/census_cluster_citations.py --class prose --verbose
"""
import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
sys.path.insert(0, HERE)

# The gate's own reader, imported rather than reimplemented, for the reason the
# module docstring gives in its fourth paragraph. `cells`, `clean` and
# `census_row`'s two-line head test are the count rule's; `fence_spans` is what
# makes a block transcript rather than prose; `cited_clusters`, `skip_reason`
# and `units` are what make "a citation" one answer rather than two.
from check_cluster_citations import (  # noqa: E402
    CLUSTER_ID, cells, census, cited_clusters, clean, fence_spans, name_re,
    skip_reason, transcript_lines, units)

NAMES = os.path.join(HERE, os.pardir, "annotations", "xdata-cluster-names.csv")
ROOTS = ("ec", "docs", "evidence")

# The form itself rather than an id. Matched before the id regex would reach it,
# and matched at all only because `main-ec-NNN` is a thing this corpus says out
# loud: `ec/README.md` and `xdata-register-map.md` §4.4 both name the form in
# running prose, and a name in those sentences would be nonsense.
TEMPLATE = re.compile(r"main-ec-NNN")

# The five classes, in the order they are tested and printed. A `census-row` is
# tested before `quoted` because the test is about the row's *first cell* and
# reads nothing of the line's markup, so a row a correction quotes keeps the
# reading that decides it: the cell is still the one `census_row()` would read.
TEMPLATE_CLS = "template"
FENCED = "fenced"
CENSUS_ROW = "census-row"
QUOTED = "quoted"
PROSE = "prose"
CLASSES = (TEMPLATE_CLS, FENCED, CENSUS_ROW, QUOTED, PROSE)

# The seven files issue #435 scopes the sweep to, as repository-relative paths
# so the output is comparable with a gate's. `docs/findings.md` is in the list
# and is not a contradiction: it is frozen as to *sections*, and this sweep
# rewrites prose inside them.
SWEPT = (
    "ec/README.md",
    "ec/annotations/manual-fan-ctrl-0751.md",
    "ec/annotations/xdata-06c2-06db-timers.md",
    "ec/annotations/xdata-086x-dispatch.md",
    "ec/annotations/xdata-register-map.md",
    "docs/findings.md",
    "docs/hardware-tests/gpu-tgp-07c4-07d7-door.md",
)

# One occurrence. `note` is the names file's own `note` column -- the reason that
# name is that name -- and is None for an id the census does not name, which is
# the common case and is why the column is optional rather than a fixed
# placeholder.
Occurrence = collections.namedtuple(
    "Occurrence", "path lineno cid cls name note text")

# What one run found, kept as a namedtuple so the report and any caller read the
# same fields rather than a dict each inventing its own keys.
Found = collections.namedtuple(
    "Found", "paths occurrences classes named gate classes_by_file")


def say(line=""):
    print(line)


def names_by_id(clusters_csv=None, names_csv=None):
    """{cluster id: (name, note)} for every cluster the names file names.

    Joined through `cluster_key`, not through the rank, because that is the
    handle the file is keyed by and the one a reshuffle does not move: a lookup
    by rank here would re-point every name at whatever cluster inherits that
    number, which is the defect issue #274 exists to stop. A row whose key the
    census does not carry resolves to nothing and is dropped rather than
    guessed at -- that is "not found by this method", the same verdict
    `cited_clusters()` gives a key or a name this generation does not have.
    """
    _, _, _, by_key, by_name = census(clusters_csv)
    out = {}
    with open(names_csv or NAMES, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r.get("cluster_key") or "").strip()
            name = (r.get("cluster_name") or "").strip()
            cid = by_key.get(key)
            if cid and name and name in by_name:
                out[cid] = (name, (r.get("note") or "").strip())
    return out


def head_is_id(line):
    """Whether this line is a table row the count rule would read.

    `census_row()`'s own head test, and not a looser one: it takes the first
    cell, strips the markdown `clean()` strips, and requires that what is left
    is *exactly* one id. A cell naming two clusters is not a census row, because
    whose figures would they be, and a cell reading a name is not one either --
    which is why this class is the one the sweep must not touch. A row with
    fewer than three cells is never one, and a file with no table in it answers
    `False` without a read.
    """
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    row = cells(stripped)
    if len(row) < 3:
        return False
    head = clean(row[0])
    ids = CLUSTER_ID.findall(head)
    return len(ids) == 1 and head == ids[0]


def classify(token, lines, fences, lineno):
    """Which of `CLASSES` this *occurrence* is, most specific first.

    The token decides `template` and the line decides the rest, and the two are
    not the same question: a sentence can name the form and cite a cluster in
    one breath ("a document writes the form as `main-ec-NNN` and cites
    `main-ec-002` beside it"), and classifying that line once would file a live
    citation under the form and hand a sweep a line to rewrite that is half
    history. A `fenced` answer outranks `quoted` because a transcript pasted
    inside a correction is still a transcript, and the ids in it belong to a
    run the reader cannot reproduce. A `census-row` outranks both because the
    count rule reads the row's cells and never looks at the line's markup, so a
    correction quoting a §5 row leaves it just as checkable.
    """
    if token == "main-ec-NNN":
        return TEMPLATE_CLS
    if lineno in fences:
        return FENCED
    if head_is_id(lines[lineno - 1]):
        return CENSUS_ROW
    if lines[lineno - 1].lstrip().startswith(">"):
        return QUOTED
    return PROSE


def occurrences_in(path, by_id):
    """Every `main-ec-NNN` in one file, in line order, with its class.

    The `main-ec-NNN` template is matched on its own first and its matches are
    reported under `template`, so the count of occurrences is the count of
    things a reader would find with `grep` and the classes partition it. Both
    regexes are run over the line and the results merged by position, so a line
    naming the form and a cluster yields two occurrences in reading order. An
    occurrence of an id the census does not carry is still reported, with no
    name: "not found by this method" is what a stale id deserves, and a silent
    drop would make a broken cross-reference look like a swept one.
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fences = {n for open_at, close_at in fence_spans(lines)
              for n in range(open_at, close_at + 1)}
    found = []
    for lineno, line in enumerate(lines, 1):
        spans = [(m.start(), m.end(), m.group(0)) for m in TEMPLATE.finditer(line)]
        spans += [(m.start(), m.end(), m.group(0)) for m in CLUSTER_ID.finditer(line)]
        for _, _, token in sorted(spans):
            name, note = by_id.get(token, (None, None))
            found.append(Occurrence(path, lineno, token,
                                    classify(token, lines, fences, lineno),
                                    name, note, line.strip()))
    return found


def gate_verdicts(path, clusters_csv=None, registers_csv=None):
    """{class: n} over the gate's own reasons, for the occurrences in one file.

    The gate decides a *unit*, not an occurrence, so this is not a per-line
    answer and does not pretend to be one: it runs `cited_clusters()` and
    `skip_reason()` over the same units the gate walks, and counts what the gate
    would check and what it would pass over. That is the number that says how
    much of this file's prose a name in place of an id would put under a check
    that does not exist today, and it is why `pairings()`'s refusal to read a
    `cluster_name` matters to a sweep rather than being a note in a docstring.
    """
    members, known, counts, by_key, by_name = census(clusters_csv, registers_csv)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if "main-ec-" not in text and not names_here(by_name, text):
        return {}
    transcripts = transcript_lines(text)
    names = name_re(by_name)
    verdicts = collections.Counter()
    for lineno, unit in units(text):
        if not cited_clusters(unit, by_key, by_name, names):
            continue
        reason = skip_reason(lineno, unit, transcripts)
        verdicts[reason or "checked"] += 1
    return dict(verdicts)


def names_here(by_name, text):
    """Whether this file mentions a cluster name at all, for the pre-filter.

    The gate's own pre-filter asks the same question of the same three citation
    forms, so the two agree about which files were worth reading; a census that
    walked a different population from the gate's would be reporting a figure
    about a set nothing else has seen.
    """
    pattern = name_re(by_name)
    return pattern.search(text) if pattern else None


def walk(paths, by_id, clusters_csv=None, registers_csv=None, gate=True):
    """(Found) for the given files.

    The gate half is optional and off for anything but the swept set: it is a
    second walk of the same text, and running it over every markdown under the
    three roots to answer a question only the swept files pose would make a
    census slower for a figure nobody reads. It is summed over the files rather
    than reported per file, because the reason names are reasons *about units*
    and a reader wants the population, not seven slices of it.
    """
    found = collections.defaultdict(list)
    verdicts = collections.Counter()
    for path in paths:
        rel = os.path.relpath(path, REPO)
        found[rel] = occurrences_in(path, by_id)
        if gate:
            verdicts.update(gate_verdicts(path, clusters_csv, registers_csv))
    occurrences = [o for rel in sorted(found) for o in found[rel]]
    classes = collections.Counter(o.cls for o in occurrences)
    by_file = {rel: collections.Counter(o.cls for o in found[rel])
               for rel in sorted(found)}
    return Found(sorted(found), occurrences, dict(classes),
                 collections.Counter(o.cid for o in occurrences if o.name),
                 dict(verdicts), by_file)


def markdown_paths():
    """Every committed `.md` under the three roots, in sorted order."""
    out = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, root)):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            out += [os.path.join(dirpath, f) for f in filenames if f.endswith(".md")]
    return sorted(out)


def report(found, verbose=False, only=None, wide=0, grouped=False):
    """The run, as a table over the files that carry one and a class total.

    Files with no occurrence are not listed, and the count of those is printed
    instead. Nearly every markdown in the tree names no cluster at all, so a
    row per file turns `--all` into a wall of blanks that hides the few files
    the walk is for.
    """
    if only:
        found = found._replace(
            occurrences=[o for o in found.occurrences if o.cls == only],
            classes={only: sum(1 for o in found.occurrences if o.cls == only)})
    by_file = {rel: c for rel, c in found.classes_by_file.items() if c}
    rolled = groups(found, grouped)
    say()
    say("  main-ec-NNN in the prose, by what each occurrence is")
    say()
    header = "  %-46s  %s" % ("directory" if rolled else "file",
                              "  ".join("%11s" % c for c in CLASSES))
    say(header)
    say("  " + "-" * (len(header) - 2))
    for rel in (sorted(rolled) if rolled else sorted(by_file)):
        counts = rolled.get(rel) or by_file[rel]
        say("  %-46s  %s"
            % (rel, "  ".join("%11s" % (counts.get(c, 0) or "") for c in CLASSES)))
    totals = collections.Counter()
    for counts in by_file.values():
        totals.update(counts)
    say("  " + "-" * (len(header) - 2))
    say("  %-46s  %s"
        % ("total", "  ".join("%11s" % totals.get(c, 0) for c in CLASSES)))
    say("  %d of %d file(s) read carry one; the rest name no cluster, which is"
        % (len(by_file), len(found.paths)))
    say("  the ordinary state of a tree where most pages are about something else.")
    say()
    say("  The five classes are disjoint and every occurrence lands in one, so the")
    say("  total row is the occurrence count decomposed rather than that count minus")
    say("  something. Only `prose` is a candidate for re-pointing at a name, and not")
    say("  all of it: an id that is the subject of its sentence -- a rank being")
    say("  counted, keyed or compared -- reads as nonsense with a name in its place,")
    say("  and no predicate over the text tells that from a pointer.")
    named = [o for o in found.occurrences if o.name]
    say()
    say("  %d occurrence(s) name a cluster this census carries; %d name one that"
        % (len(named), len(found.occurrences) - len(named)))
    say("  carries no name, and are not in scope for a name at all.")
    for cid, n in sorted(found.named.items(), key=lambda kv: (-kv[1], kv[0])):
        first = next(o for o in named if o.cid == cid)
        say("    %-12s %-18s %4d  %-11s first at %s:%d"
            % (cid, first.name, n, first.cls,
               os.path.relpath(first.path, REPO), first.lineno))
    if found.gate:
        say()
        say("  The gate's own answer for these files, by its own skip reasons:")
        for reason, n in sorted(found.gate.items(), key=lambda kv: (-kv[1], kv[0])):
            say("    %-34s %d unit(s)" % (reason, n))
        say("    A unit listed as `checked` is the only kind a name in place of")
        say("    its id would put under a membership rule; the rest are pointers")
        say("    nothing verifies today.")
    if verbose:
        say()
        for o in found.occurrences:
            if only and o.cls != only:
                continue
            say("  %s:%d  %-11s %-12s %-18s"
                % (os.path.relpath(o.path, REPO), o.lineno, o.cls, o.cid,
                   o.name or "-"))
            say("      %s" % o.text[:wide or 100])
            if o.note:
                say("      note: %s" % o.note[:wide or 100])
    say()
    say("  Every negative above is not found by this method, never absent: an")
    say("  occurrence this walk does not list is one not found in the files named")
    say("  on the command line. No EC image is opened, no register is read, and")
    say("  nothing here was observed on hardware.")


def groups(found, grouped):
    """{directory: {class: n}} when the walk is tree-wide, else {}.

    `--all` reads every markdown under the three roots and most of them name no
    cluster, so the per-file table is a wall of zeros. Collapsing to the
    directory each file sits in makes the residue legible without dropping a
    single occurrence: the per-file view is what `--verbose` is for, and the
    swept set is small enough that it is the default.
    """
    if not grouped:
        return {}
    out = collections.defaultdict(collections.Counter)
    for rel, counts in found.classes_by_file.items():
        if counts:
            out[os.path.dirname(rel) or "."].update(counts)
    return dict(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true",
                    help="walk every committed .md under ec/, docs/ and "
                         "evidence/ rather than the files issue #435 scopes the "
                         "sweep to")
    ap.add_argument("--class", dest="only", choices=CLASSES,
                    help="report one class only, which is the useful filter for "
                         "a sweep and the reason --verbose exists")
    ap.add_argument("--verbose", action="store_true",
                    help="list every occurrence with its line and the names "
                         "file's note for the name it could carry")
    ap.add_argument("--width", type=int, default=0,
                    help="column width for --verbose excerpts (0: 100)")
    ap.add_argument("--clusters", default=None,
                    help="clusters CSV to resolve names through (default: the "
                         "committed one)")
    ap.add_argument("--registers", default=None,
                    help="registers CSV the gate's address column comes from")
    args = ap.parse_args(argv)

    paths = (markdown_paths() if args.all
             else [os.path.join(REPO, p) for p in SWEPT])
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        print("census_cluster_citations.py: no such file: %s"
              % ", ".join(os.path.relpath(m, REPO) for m in missing),
              file=sys.stderr)
        return 1
    by_id = names_by_id(args.clusters)
    if not by_id:
        print("census_cluster_citations.py: no name in %s resolved through a "
              "cluster_key in the census -- that is a broken walk, not an empty "
              "one" % os.path.relpath(NAMES, REPO), file=sys.stderr)
        return 1
    found = walk(paths, by_id, args.clusters, args.registers, gate=not args.all)
    if not found.occurrences:
        print("census_cluster_citations.py: no `main-ec-NNN` was read at all, so "
              "the walk had no population -- that is a broken census, not an "
              "empty one", file=sys.stderr)
        return 1
    report(found, args.verbose, args.only, args.width, grouped=args.all)
    return 0


if __name__ == "__main__":
    sys.exit(main())
