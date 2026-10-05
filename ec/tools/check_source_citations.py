#!/usr/bin/env python3
"""Hold the prose's `*.py:NNN` citations to a *named anchor* in the tool they name.

`check_eq_guard_citations.py` established the mechanism for one mechanism's own
pins: an **anchor** is a literal string of the target's own source, resolved by
reading the target, and a **locator** is a regular expression over the citing
file's prose whose first group is the line the sentence cites. Its own docstring
names #868 as the owner of the general case, and this is that tool — same two
parts, any target, any file.

**What this tool is: a span check against a declared anchor, with the number
reported rather than required to match.** Neither of the two obvious
alternatives works, and the reason is the defect itself:

  * *Hold the line.* Every merge that grows the target reddens every citation
    into it. That is the lock CLAUDE.md's "Cite code by name" and the unheld pin
    census are about, and it is why `check_citation_lines.py` loosened its Rule 3
    to note rather than fail on 2026-10-04 and why
    `check_eq_guard_citations.py` stopped requiring its `:NNN` to match.
  * *Accept any line inside the named construct.* Looser than that Rule 3, and
    blind to the case that decided the design: the dispatch page's live sentence
    cited a line that **is** inside the right file and lands on a comment in the
    module-level `NOT_IN_TREE` dict, in no function at all, so no "is it in the
    construct" test with the construct named loosely enough to contain it would
    have said anything.

So the cited line must fall **inside the anchor's span**, and four verdicts
follow, each pinned by a case in `test_check_source_citations.py`:

  * the anchor resolves uniquely and the cited line is inside its span -- **pass**.
  * the anchor resolves uniquely and the cited line is outside its span --
    **fail**, naming the anchor's current line so a reader can follow it.
  * the anchor resolves uniquely and the cited line is inside the span but not
    on the anchor's own line -- **note**, not a failure. The sentence claims a
    region ("pins exactly those buckets"), and reddening it would be the line
    rule again wearing a span. The run **reports** this count rather than
    requiring it to be non-zero: whether any live sentence happens to cite an
    anchor's body rather than its opening line is a fact about the prose that
    moves, so the case that fires this verdict lives in the suite's scratch tree
    where it is built on demand.
  * the anchor is **gone, or no longer unique** -- **fail**, naming the anchor.
    Deliberately a failure and not a skip: "the subject of this sentence does
    not exist in the file it names" is not "not checked by this method". This is
    a verdict about **this tool's own declared anchors**, and it is worth being
    exact about what it did and did not catch in the case that opened #868,
    because the two are easy to confuse. On the pre-fix dispatch page (that
    page's text against this target) the `:770` cell is **declined**, not
    failed, and that is the correct reading rather than a gap: `HAND_CHECKED`
    was never declared as an anchor here, so no locator claims that cell and
    there is no anchor for the gone-anchor verdict to fire on. Declaring a
    needle the target does not have would make the anchor fail on every future
    run of a tree that has already retracted it. What the run does report on
    that page is the reworded-citation verdict, because the corrected prose
    does not match the locators written against it -- which is a different
    branch, and `test_check_source_citations.py` pins both of these by running
    the pre-fix page rather than a synthetic anchor.

A citation in a scoped file that no declared locator matches is **declined and
counted**, never passed: a checker that stopped matching would otherwise report
the page clean.

**The supersession boundary, stated rather than left open.** A quoted
supersession is a denial of currency and is passed over -- both shapes
`check_citation_lines.py` reads off *raw* lines, because the marker is markup a
sentence join has already thrown away: any line of the paragraph opening `>`, or
a paragraph opening `CORRECTION` once `>`, `#`, `*`, `-` and whitespace are
stripped. They are **copied rather than imported**: a tool reaching into a
sibling for its vocabulary is a tool whose subject is the sibling. The skip is
counted and printed on every run, so "checked nothing" cannot read as "found
nothing".

**What this does not check, which is as much of the point:**

  * *`ec/annotations/registers.yaml`.* Its one `xdata_register_map.py:NNN` is not
    walked, and the reason is measured rather than assumed: a folded scalar holds
    no blank lines, so a whole `name:` entry is ONE paragraph whose
    `*** CORRECTION` marker sits mid-paragraph, and neither shape above fires on
    it. That is `check_citation_lines.py`'s own measured reason for keeping the
    file out of its `ROW_SCOPE`, and #870 fixed that entry's six cells by hand. A
    file this tool does not walk is reported as not walked, never as clean.
  * *A bare `:NNN` with nothing to say what it is a line of.* The locators
    capture the number out of the sentence that names the code, so every
    **declared** citation is read whatever its spelling. An undeclared bare
    `:NNN` is attributed to no target, and guessing one is the move this tool
    refuses; it is not seen, and saying so is why the declined count is a count
    of `<target>.py:NNN` sites specifically.
  * *Any target outside `ANCHORS`, and any file outside `CITATIONS`.* Those are
    not read at all, which is "not done by this method" and never "there is
    nothing there".
  * *A citation whose subject is a *different* construct that happens to fall
    inside the anchor's span.* Measured, not hypothetical: one live cell in
    `xdata-4-4-identity-rederivation.md` cites `:2723` for "a comment carrying
    'the committed 427 ids'", and that string is in the tool at a line well
    outside the span its declared anchor opens. A span is a region, not a
    subject: containment says the number is somewhere in the construct, and
    nothing here says which line of it the sentence meant. Holding that needs
    the cited line's own text, which is a per-file oracle this tool does not
    have. It is a false negative, stated here rather than left to be found.
  * *A `.c` citation.* `check_citation_lines.py`'s Rule 1 and
    `check_site_census.py` hold the decompile side; this holds pointers into
    source.
  * *The numbers' own agreement with the prose.* A citation that lands inside the
    right construct is held to being inside it, not to the figure the sentence
    attaches to it.

Usage:
    python3 ec/tools/check_source_citations.py            # the committed tree
    python3 ec/tools/check_source_citations.py --repo DIR # a scratch tree
    python3 ec/tools/check_source_citations.py --census    # the class census
"""
import argparse
import bisect
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)

# (target relative to the repo root, key, what the anchor is, the string of the
# target's own source it is). Read by reading the target and matching nothing
# else: there is no parse of the target here, because a parse would answer a
# different question -- *whether the line is right*, rather than *whether the
# subject still exists*.
#
# An anchor's **span** is its own line and every following line indented past
# it, so `CLASSIFIER_SHAPE = (` spans the whole literal and
# `if eq_guard and stripped.startswith("==")` spans the `if` and its `return`.
# That is what makes "inside the construct" checkable without a parse.
ANCHORS = (
    ("ec/tools/xdata_register_map.py", "classifier_shape",
     "`CLASSIFIER_SHAPE`, the narrow direction oracle's literal snippets",
     "CLASSIFIER_SHAPE = ("),
    ("ec/tools/xdata_register_map.py", "corpus_wide_invariant",
     "the corpus-wide direction invariant, which holds the buckets a shape "
     "cannot",
     'check("the corpus-wide direction invariant: every occurrence that '),
    ("ec/tools/xdata_register_map.py", "hand_oracle_removed",
     "the comment recording that the per-address hand oracles were removed",
     "The per-address hand oracles that stood here"),
    ("ec/tools/xdata_register_map.py", "map_columns",
     "`MAP_COLUMNS`, the `--map` table's columns",
     "MAP_COLUMNS = ["),
    ("ec/tools/xdata_register_map.py", "assign",
     "`ASSIGN`, the operator tuple",
     'ASSIGN = ("=", "|=", "&=", "+=", "-=", "*=", "/=", "^=", "%=", "<<=", ">>=")'),
)

# (file, ((anchor key, locator), ...)). The locator is a regular expression over
# the file's text with whitespace collapsed, whose **first** group is the line
# number the sentence cites. It is the citation's own content anchor: a sentence
# that stops naming the code stops matching, which is reported rather than
# passed, and that is the half of this the number alone could not do.
#
# Every match of a locator is checked, so a site that appears twice in one file
# is held twice rather than once.
CITATIONS = (
    ("ec/annotations/xdata-086x-dispatch.md", (
        # The live paragraph, as the correction leaves it: the three subjects it
        # names instead of the removed oracle. Each is a claim that the subject
        # is still there, which is the whole of what this holds.
        ("hand_oracle_removed",
         r"comment\s+where they stood at `ec/tools/xdata_register_map\.py:(\d+)`"),
        ("classifier_shape",
         r"held instead by `CLASSIFIER_SHAPE`'s literal snippets \(`:(\d+)`\)"),
        ("corpus_wide_invariant",
         r"the corpus-wide direction invariant \(`:(\d+)`\)"),
        # The #249 quoted predecessors. Declared and **not** repointed: they are
        # meant to stay wrong, because a quoted supersession is a denial of
        # currency and §4a-4d wants the figure it replaces visible as text.
        # They are declared so the skip is a counted, printed skip rather than
        # a number this tool never looked at -- and so the `assign` anchor has a
        # consumer in this file. The path prefix is optional because two of them
        # spell the same citation differently, and a locator matching only one
        # spelling would report the other's skip as a failure.
        ("assign",
         r"`ASSIGN` is at `(?:ec/tools/)?xdata_register_map\.py:(\d+)`"),
        ("assign",
         r"`ec/tools/xdata_register_map\.py:(\d+)` defines `ASSIGN`"),
    )),
    ("docs/findings/xdata-4-4-identity-rederivation.md", (
        ("map_columns", r"`MAP_COLUMNS` at `xdata_register_map\.py:(\d+)"),
    )),
    # Declared with no citation, and walked anyway: the census found its
    # thirteen live cells name subjects the tool no longer holds, and a file
    # this tool reads and holds nothing for must still say so rather than read
    # as a file with nothing in it.
    ("docs/findings/xdata-census-rederivation-checklist.md", ()),
)

# A citation of a **declared target** in a scoped file, in either spelling the
# corpus uses -- `xdata_register_map.py:1220` and `../tools/xdata_register_map.py:1220`
# are one citation, and a span (`:4947-4950`) is one citation opened on its
# first number rather than two. Built from `ANCHORS`' own targets, so a target
# added there is scanned for without a second edit here.
def pointer(targets):
    names = "|".join(re.escape(os.path.basename(t)) for t in targets)
    return re.compile(r"(?<![\w./-])(?:\.{1,2}/)?(?:[\w-]+/)*"
                      rf"(?:{names}):(\d+)(?:-(\d+))?")


# `check_citation_lines.py`'s supersession vocabulary, copied rather than
# imported, for the reason the docstring gives. Both shapes are read off the raw
# lines, because the marker is markup a join has already thrown away.
QUOTE = ">"
MARKERS = re.compile(r"^[>\#*\-\s]*")
ANNOUNCES = re.compile(r"^CORRECTION\b", re.IGNORECASE)


def flat(text):
    """-> (whitespace-collapsed text, starts) for `text`.

    `starts` maps a character's offset in the collapsed text to the 1-based
    line it came from, one entry per line, so a report can name the line a
    match is on. Collapsing is what lets a locator written as one sentence
    match a paragraph that wraps it across four lines -- which is the normal
    shape here, and a matcher that required the code and its number to share a
    line would silently check nothing in a file that wraps at 79 columns.
    """
    pieces, starts, at = [], [], 0
    for number, line in enumerate(text.splitlines(), 1):
        piece = line.strip()
        starts.append((at, number))
        pieces.append(piece)
        at += len(piece) + 1
    return " ".join(pieces), starts


def line_of(starts, offset):
    """The 1-based line the character at `offset` in the collapsed text is on."""
    at = [s for s, _ in starts]
    return starts[max(bisect.bisect_right(at, offset) - 1, 0)][1]


def supersession(lines):
    """Why this paragraph is not checked, or "" if it is.

    `check_citation_lines.py`'s rule and its reason, restated: a quoted
    supersession is a denial of currency, and `docs/findings.md` §4a-4d requires
    the figure it replaces to stay visible as text beside it. Returns the reason
    rather than a bool so a run can say *why* a citation was passed over.
    """
    for line in lines:
        if line.strip().startswith(QUOTE):
            return "quoted material"
    head = MARKERS.sub("", lines[0].strip()) if lines else ""
    return "a correction paragraph" if ANNOUNCES.match(head) else ""


def paragraph(lines, number):
    """(first line number, raw lines) of the paragraph holding `number`.

    A run of non-blank lines, which includes a whole markdown table: a table
    row's line is a unit to a line-at-a-time reader and a run of rows to this,
    which is harmless for the supersession test because a table is neither
    quoted material nor a paragraph that opens with the word.
    """
    start = end = number - 1
    while start > 0 and lines[start - 1].strip():
        start -= 1
    while end < len(lines) and lines[end].strip():
        end += 1
    return start + 1, lines[start:end]


def resolve(target_text, needle):
    """(line, last line of span) for `needle` in the target, or (None, None).

    `None` for a needle that is not there **and** for one that is there more
    than once: both are *not found by this method*, per `CLAUDE.md`'s rule and
    `ec/annotations/registers.yaml`'s own caveat on the same point, and neither
    is ever reported as the code being absent. An anchor that grew a second match
    is a declaration that has itself gone stale, and it fails.

    The span runs from the anchor's own line through every following line
    indented past it. `CHECK_COLUMNS` and a `check(...)` call both open a
    construct that spans, and a single line would report every citation into the
    body of one as outside it.
    """
    lines = target_text.splitlines()
    found = [n for n, line in enumerate(lines, 1) if needle in line]
    if len(found) != 1:
        return None, None
    first = found[0] - 1
    base = len(lines[first]) - len(lines[first].lstrip())
    last = first
    while last + 1 < len(lines):
        nxt = lines[last + 1]
        if not nxt.strip():
            last += 1
            continue
        if len(nxt) - len(nxt.lstrip()) <= base:
            break
        last += 1
    return first + 1, last + 1


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def census(repo, stream=None):
    """Print every `<target>:NNN` cell in the tree, classed. -> the site count.

    The census the write-up records is printed here rather than written down as
    a figure, because a count of the repository's own prose goes stale at the
    next merge and CLAUDE.md's "no totals of the repository's own text" is the
    rule that says so. Walking the tree is also what keeps the *scope* honest:
    a number of the cells this tool holds says nothing about how many there
    are, and this prints both.

    Three classes, and the third is the one that decides scope:

      * **live** -- not in quoted or correction material, so the sentence makes
        a present-tense claim about where the code is.
      * **quoted-superseded** -- inside a blockquote or a `CORRECTION`
        paragraph, and meant to stay wrong per §4a-4d.
      * **declines to attribute** -- a bare `:NNN` with nothing in the sentence
        saying what file it is a line *of*. Guessing one is the move this tool
        refuses, so these are counted and never counted as clean.

    Only `.md` and `.yaml` are walked, and only for the declared targets: a
    census of a class this tool does not hold would be a different tool's.
    """
    stream = sys.stdout if stream is None else stream
    pattern = pointer(sorted({target for target, _, _, _ in ANCHORS}))
    classes = {"live": 0, "quoted-superseded": 0, "declines to attribute": 0}
    per_file = []
    for base, dirs, names in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in sorted(names):
            if not name.endswith((".md", ".yaml")):
                continue
            rel = os.path.relpath(os.path.join(base, name), repo)
            try:
                text = read(os.path.join(repo, rel))
            except OSError:
                continue
            collapsed, starts = flat(text)
            lines = text.split("\n")
            counts = Counter()
            for match in pattern.finditer(collapsed):
                at = line_of(starts, match.start())
                counts["quoted-superseded" if supersession(paragraph(lines, at)[1])
                      else "live"] += 1
            # A bare `:NNN` is counted in its own class whatever paragraph it
            # sits in, and *not* folded into the other two: the supersession
            # test says whether a figure is still claimed, and it cannot say
            # which file an unattributed number is a line of, so calling one
            # "quoted" would credit this census with knowing something it does
            # not.
            for match in re.finditer(r"(?<![\w./-]):(\d+)(?:-(\d+))?(?![\w/])",
                                     collapsed):
                counts["declines to attribute"] += 1
            if counts:
                per_file.append((rel, counts))
                for key, value in counts.items():
                    classes[key] += value
    for rel, counts in sorted(per_file):
        detail = ", ".join(f"{value} {key}" for key, value in sorted(counts.items()))
        print(f"  {rel}: {detail}", file=stream)
    print(file=stream)
    for key in sorted(classes):
        print(f"  {classes[key]:6d}  {key}", file=stream)
    return sum(classes.values())


def check(repo, stream=None):
    """-> (problems, resolved, held, noted, declined, skipped) over `repo`.

    `stream` is resolved inside rather than defaulted in the signature, so a
    caller that redirects `sys.stdout` -- the suite does, to read the report
    rather than let it print over the runner's own output -- redirects this too.
    A default bound at import time is the one a redirect cannot reach.
    """
    stream = sys.stdout if stream is None else stream
    problems = []

    resolved = {}
    for target, key, what, needle in ANCHORS:
        try:
            text = read(os.path.join(repo, target))
        except OSError as exc:
            problems.append(f"{target}: not read ({exc.__class__.__name__}) "
                            f"-- that is a broken check, not an empty one")
            continue
        first, last = resolve(text, needle)
        if first is None:
            problems.append(f"{target}: {what} is not found by this method "
                            f"(needle {needle!r}) -- the anchor is declared from "
                            f"the target's own source and is either gone or no "
                            f"longer unique; that is a stale declaration, not an "
                            f"absence")
            continue
        resolved[key] = (first, last)
        print(f"  {key}: {target}:{first}-{last}  {what}", file=stream)
    if not resolved:
        return (problems, 0, 0, 0, 0, 0)

    held = noted = declined = skipped = 0
    # Built here rather than by `main()`, because `check()` is the whole of this
    # tool's reading and a caller that calls it directly must get the same run
    # the command line does. A module global assigned by `main()` is `None` to
    # such a caller, and a case that happened to run after one that called
    # `main()` would pass on that accident rather than on its own fixture.
    pattern = pointer(sorted({target for target, _, _, _ in ANCHORS}))
    print(file=stream)
    for rel, declared in CITATIONS:
        try:
            text = read(os.path.join(repo, rel))
        except OSError as exc:
            problems.append(f"{rel}: not read ({exc.__class__.__name__}) -- "
                            f"that is a broken check, not a clean file")
            continue
        lines = text.split("\n")
        collapsed, starts = flat(text)
        read_count, seen = 0, []
        for key, locator in declared:
            matches = list(re.compile(locator).finditer(collapsed))
            if not matches:
                problems.append(
                    f"{rel}: a declared {key} citation is not found by this "
                    f"method (locator {locator!r}) -- the sentence has been "
                    f"reworded out of the shape the declared list expects, which "
                    f"is not the same as its number being right")
                continue
            for match in matches:
                at = line_of(starts, match.start())
                cited = int(match.group(1))
                first, raw = paragraph(lines, at)
                why = supersession(raw)
                # Keyed on the paragraph, not the line: a locator's match and
                # the `xdata_register_map.py:NNN` it accounts for routinely
                # straddle a wrap, and a line-keyed set would decline the very
                # citation it had just held.
                seen.append((first, cited))
                if why:
                    skipped += 1
                    print(f"  skip ({why}) {rel}:{at} cites :{cited}",
                          file=stream)
                    continue
                read_count += 1
                if key not in resolved:
                    continue  # already reported against the target
                first_line, last_line = resolved[key]
                held += 1
                if first_line <= cited <= last_line:
                    if cited != first_line:
                        noted += 1
                        print(f"  note {rel}:{at}: cites :{cited} for {key}, "
                              f"which is inside that anchor's span "
                              f":{first_line}-{last_line} but not on its "
                              f"opening line -- the sentence claims a region, "
                              f"and a line rule would redden it", file=stream)
                    continue
                problems.append(
                    f"{rel}:{at}: cites :{cited} for {key}, whose span is "
                    f":{first_line}-{last_line} -- the anchor holds, and this "
                    f"number names a line outside the construct the sentence "
                    f"gives it to")
        unclaimed = pointer_sites(pattern, collapsed, starts, lines, seen)
        declined += len(unclaimed)
        for at, cited in unclaimed:
            print(f"  declined {rel}:{at} cites :{cited} -- not in this "
                  f"tool's declared list, which is a different claim",
                  file=stream)
        print(f"  {rel}: {read_count} declared citation(s) read, "
              f"{len(unclaimed)} declined", file=stream)
    return problems, len(resolved), held, noted, declined, skipped


def pointer_sites(pattern, collapsed, starts, lines, seen):
    """-> [(line, number)] for each target citation no declared locator claimed.

    `pattern` is passed in rather than read from a module global, so this
    function depends on its arguments rather than on whether something else in
    the process has run `main()` yet.

    Two tests, and the second is why this is a count rather than a note: a
    citation inside a superseded paragraph is *skipped* rather than declined, or
    every `>` block quoting a superseded number would show up here as work this
    tool declined to do.
    """
    out = []
    for match in pattern.finditer(collapsed):
        at = line_of(starts, match.start())
        cited = int(match.group(1))
        first = paragraph(lines, at)[0]
        if any(first == s and cited == c for s, c in seen):
            continue
        if supersession(paragraph(lines, at)[1]):
            continue
        out.append((at, cited))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # `--repo` rather than nothing, so a case can point the whole report at a
    # scratch tree and read the same output a human reads. The scratch tree is
    # where the failing invariant is demonstrated: nothing in this repository
    # makes the check red, by design.
    ap.add_argument("--repo", default=REPO,
                    help="repository root to read (default: this one)")
    ap.add_argument("--census", action="store_true",
                    help="print every source-line cell in the tree and its "
                         "class, rather than checking the declared scope")
    args = ap.parse_args()

    if args.census:
        print(f"check_source_citations.py: the census of source-line citations "
              f"into {len({t for t, _, _, _ in ANCHORS})} target file(s):")
        census(args.repo)
        return 0

    scope = sorted({target for target, _, _, _ in ANCHORS})

    print(f"check_source_citations.py: the {len(ANCHORS)} declared anchors, "
          f"resolved in {len(scope)} target file(s):")
    problems, resolved, held, noted, declined, skipped = check(args.repo)
    if problems:
        print(file=sys.stderr)
        for problem in problems:
            print(f"  FAIL {problem}", file=sys.stderr)
        print(f"check_source_citations.py: {len(problems)} problem(s). Every "
              f"number here is a read of a file in {args.repo}; "
              f"nothing in this run is a statement about the EC or the firmware.",
              file=sys.stderr)
        return 1
    if not held:
        print("check_source_citations.py: read no citation at all, which is a "
              "broken check rather than a clean tree", file=sys.stderr)
        return 1
    print(f"{held} citation(s) name an anchor the target still has, {noted} "
          f"inside a span rather than on its opening line, {declined} declined "
          f"as not this tool's, {skipped} skipped as superseded -- {resolved} of "
          f"{len(ANCHORS)} anchors resolved, over {len(CITATIONS)} declaring "
          f"file(s). A run that checks nothing is a failure of this test, not a "
          f"pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())