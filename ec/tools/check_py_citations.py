#!/usr/bin/env python3
"""Hold the committed Python sources' line citations into `xdata_register_map.py`
to the code those citations name.

`ec/tools/xdata_register_map.py` is thousands of lines and most of its prose
about itself lives in docstrings that name *other* lines of itself. Citations
into it are written from committed Python files -- hand-written sentences in a
docstring or a comment, in `inc_dptr_sites.py`, `test_xdata_cluster_names.py`,
`test_xdata_register_map.py` and `test_xdata_guard_off_row_join.py` -- and on
the tree named below, **every one of them names the wrong code**. Not one line
off: a sentence reading "`cluster_key` is a content hash of program plus sorted
members" pointed at a dict literal in `cluster_rows_build()`, and one reading
"the two `list(...)` defaults" pointed into a `--self-test` sweep block. A
`:NNN` that resolves to a different statement is not a broken link; it is a
sentence that reads correctly and means the wrong line, and nothing in the tree
is red over it.

**The principle is the sibling's** (`check_eq_guard_citations.py`, which holds
the `--no-eq-guard` mechanism's own prose pins): hold the code, and let the
number follow. Each anchor below is a **string of the tool's own source**,
resolved by reading the tool; each declared citation is a **string of the
citing file's own prose** whose `:NNN` must be the line that anchor is on
today. So the fix for a red row is one edit rather than a re-measurement, and
a citation whose sentence has been reworded is *reported* rather than passed --
which is the half a bare number could not do.

**Why this is a separate tool rather than a wider `CITATIONS` in the sibling.**
Most of these citations are not about the `--no-eq-guard` mechanism at all: the
pair fold, the `list(...)` defaults and the `cluster_key` hash are claims about
`scan()`, `main()` and `cluster_key()`. Holding them in a tool whose declared
identity is *"the `--no-eq-guard` mechanism's own pins"* would mean either
putting a different mechanism's claims in a tool about this one, or holding
unrelated claims under `--no-eq-guard` anchors -- which is exactly the "a number
that resolves to a different thing" defect this exists to catch. The sibling's
`CITATIONS` and its `TREE` are therefore left untouched.

**What it is deliberately not.** This is *not* the general `.py:NNN` pointer
checker, and it is not a census of every line citation in the repository. It
reads the declaring files named in `CITATIONS` plus the tool; it does not walk
the tree for citations. #868 owns `xdata-086x-dispatch.md:286-288` and states
that its fix needs the general tool; #869 owns the files citing a generated CSV
by line outside `check_citation_lines.py`'s `ROW_SCOPE`; #870 owns the pointers
in `XDATA_0860`'s 2026-09-24 block; #1050 is the open question of whether the
supersession vocabulary has been counted over the wider class at all. The
write-up is `docs/findings/py-source-citations.md`.

**What it does not check, which is as much of the point:**

  * *The synthetic fixtures.* A literal inside `check_doc_figure_pins.py`'s
    `TABLE`, `census_test_line_pins.py`'s `pins()` input or
    `check_eq_guard_citations.py`'s own regex docstring is the checker's
    *expectation* or an *illustration*, not a claim about the code. They are
    declined and counted below rather than held, so a reader can tell a claim
    from a fixture by whether it is in `CITATIONS`.
  * *A bare `:NNN` this tool cannot attribute.* The locators capture the number
    out of the sentence that names the code, so every **declared** citation is
    read whatever its spelling. An unclaimed `xdata_register_map.py:NNN` is
    reported as **declined** and counted: "checked nothing" and "found nothing"
    must not read alike, so a run that read no citation at all exits non-zero.
  * *A superseded figure.* A paragraph opening `CORRECTION`, or a quoted `>`
    block, is passed over on `check_citation_lines.py`'s own vocabulary: a
    quoted correction is a denial of currency, and `CLAUDE.md`'s rule is that
    the figure it replaces stays visible as text beside it. The skip is
    counted, never silent.
  * *The anchors' uniqueness.* Every anchor is checked for that, and an anchor
    that is gone or ambiguous is a **stale declaration** and fails. It is never
    reported as the code being absent -- `CLAUDE.md` and
    `ec/annotations/registers.yaml`'s own caveat both say that a static scan
    finding zero hits means "not found by this method".

**The citation population is fixed by being declared, not by being counted.**
A site appearing in a declared file that no locator claimed is declined and
counted, not silently held; that is the point at which this either grows a
declared locator or earns its own tool, and the report says which happened. The
number of citations is therefore never written down here: it is the `held` count
in the run, and a count of this repository's own text is out of date at the next
merge for the reason `CLAUDE.md` gives.

Usage:
    python3 ec/tools/check_py_citations.py            # the committed tree
    python3 ec/tools/check_py_citations.py --repo DIR # a scratch tree
"""
import argparse
import bisect
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
TOOL = os.path.join("ec", "tools", "xdata_register_map.py")

# The tree every number in the write-up was measured on, named in the failure
# text and nowhere else. It is a fact about the prose, not something this tool
# can derive, and a checker that guessed its own revision would be a claim it
# cannot support.
TREE = "ad595588"

# (key, what the anchor is, the string of the tool's own source it is). Read by
# substring search over the tool's lines and by nothing else -- there is no
# parse of the tool here, and a parse would answer a different question.
ANCHORS = (
    ("no_eq_guard_flag",
     "`ap.add_argument(\"--no-eq-guard\", ...)`",
     'ap.add_argument("--no-eq-guard", action="store_true",'),
    ("thresholds_list_default",
     "the `--thresholds` `default=list(SWEEP_THRESHOLDS)`",
     "default=list(SWEEP_THRESHOLDS),"),
    ("floors_list_default",
     "the `--floors` `default=list(SWEEP_COREADING_FLOORS)`",
     'default=list(SWEEP_COREADING_FLOORS), metavar="N",'),
    ("no_eq_guard_output_refusal",
     "the `--no-eq-guard` committed-output refusal",
     'ap.error("--no-eq-guard would overwrite the committed census, so it "'),
    ("export_ownership_output_refusal",
     "the `--export-ownership` committed-output refusal",
     'ap.error("--export-ownership would overwrite the committed census, so "'),
    ("pair_fold",
     "the `a`/`a+1` pair fold inside `scan()`",
     "for addr, direction in pair_sites(text, accessors, pattern):"),
    ("cluster_key_def",
     "`def cluster_key(g, addrs)`",
     "def cluster_key(g: str, addrs) -> str:"),
    ("after_census_build",
     "`own_map = load_ownership()`, the after-census built in-process",
     "own_map = load_ownership()"),
)

# (file, ((anchor key, locator), ...)). The locator is a regular expression over
# the file's text with whitespace collapsed, whose **first** group is the line
# number the sentence cites. It is the citation's own content anchor: a sentence
# that stops naming the code stops matching, which is reported rather than
# passed. Every match of a locator is checked, so a site written twice in one
# file is held twice rather than once.
#
# The declaring files are the committed `*.py` files carrying a hand-written
# `xdata_register_map.py:NNN`. `check_eq_guard_citations.py` and
# `test_check_doc_figure_pins.py` are listed with no locator at all: they carry
# only synthetic fixtures and illustrative literals, and listing them empty is
# what makes their sites come out **declined** rather than unexamined.
CITATIONS = (
    ("ec/tools/inc_dptr_sites.py", (
        ("pair_fold", r"same spelling \(\s*`xdata_register_map\.py:(\d+)(?:-\d+)?`"),
    )),
    ("ec/tools/test_xdata_cluster_names.py", (
        ("no_eq_guard_flag",
         r"turned off\" \(`xdata_register_map\.py:(\d+)(?:-\d+)?`\)"),
        ("after_census_build",
         r"built in-process \(\s*`xdata_register_map\.py:(\d+)(?:-\d+)?`"),
    )),
    ("ec/tools/test_xdata_register_map.py", (
        ("thresholds_list_default",
         r"`list\(\.\.\.\)` defaults at\s*`xdata_register_map\.py:(\d+)(?:-\d+)?`"),
        ("floors_list_default",
         r"and\s*`:(\d+)`\s*out: they"),
        ("no_eq_guard_output_refusal",
         r"guards' reasons at xdata_register_map\.py:(\d+)(?:-\d+)?"),
        # The second refusal's number is written bare and unbackticked, as the
        # sentence has it; the two are one claim about two refusals, and a
        # locator per number is what tells them apart.
        ("export_ownership_output_refusal",
         r"and\s*#?\s*:(\d+)(?:-\d+)?\s*would be stale"),
    )),
    ("ec/tools/test_xdata_guard_off_row_join.py", (
        # A `#` before the citation is the comment continuing across the wrap,
        # which is the one shape a markdown locator does not have to allow for.
        ("cluster_key_def",
         r"sorted members\s*#?\s*\(\s*`xdata_register_map\.py:(\d+)(?:-\d+)?`"),
    )),
    ("ec/tools/check_eq_guard_citations.py", ()),
    ("ec/tools/test_check_doc_figure_pins.py", ()),
)

# A citation of the tool in a declaring file, in either spelling the corpus uses
# -- `xdata_register_map.py:1861` and `../tools/xdata_register_map.py:1861` are
# one citation, and a span (`:1861-1869`) is one citation opened on its first
# number rather than two. A site no declared locator claimed is declined, not
# passed, and counted.
POINTER = re.compile(r"(?<![\w./-])(?:\.{1,2}/)?(?:[\w-]+/)*"
                     r"xdata_register_map\.py:(\d+)(?:-(\d+))?")

# `check_citation_lines.py`'s supersession vocabulary, copied rather than
# imported: a tool that reached into a sibling for this would be a tool whose
# subject is the sibling. Both shapes are read off the raw lines, because the
# marker is markup a join has already thrown away.
QUOTE = ">"
MARKERS = re.compile(r"^[>\#*\-\s]*")
ANNOUNCES = re.compile(r"^CORRECTION\b", re.IGNORECASE)


def flat(text):
    """-> (whitespace-collapsed text, starts) for `text`.

    `starts` maps a character's offset in the collapsed text to the 1-based
    line it came from, one entry per line, so a report can name the line a
    match is on. Collapsing is what lets a locator written as one sentence
    match a docstring that wraps it across four lines -- which is the normal
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
    supersession is a denial of currency, and `CLAUDE.md` requires the figure
    it replaces to stay visible as text. A `CORRECTION` paragraph is the same
    shape in a Python source, where there is no markdown to quote with --
    `test_grade_0751_isolation.py`'s in-place corrections are `#`-commented
    `CORRECTION` lines, which is why `MARKERS` above strips `#` and not only
    `>`. Returns the reason rather than a bool so the report can say *why* a
    citation was passed over.
    """
    for line in lines:
        if line.strip().startswith(QUOTE):
            return "quoted material"
    head = MARKERS.sub("", lines[0].strip()) if lines else ""
    return "a correction paragraph" if ANNOUNCES.match(head) else ""


def paragraph(lines, number):
    """(first line number, raw lines) of the paragraph holding `number`.

    A run of non-blank lines, which for a Python source is a run of adjacent
    docstring or comment lines. That is the right unit here for the same reason
    it is right in the sibling: the locator's match and the
    `xdata_register_map.py:NNN` it accounts for routinely straddle a wrap, and
    a line-keyed set would decline the very citation it had just held.
    """
    start = end = number - 1
    while start > 0 and lines[start - 1].strip():
        start -= 1
    while end < len(lines) and lines[end].strip():
        end += 1
    return start + 1, lines[start:end]


def resolve(tool_text, needle):
    """The 1-based line `needle` is on in the tool, or None.

    `None` for a needle that is not there **and** for one that is there more
    than once: both are *not found by this method*, and neither is ever
    reported as the code being absent. An anchor that grew a second match is a
    declaration that has itself gone stale, and it fails.
    """
    found = [n for n, line in enumerate(tool_text.splitlines(), 1)
             if needle in line]
    return found[0] if len(found) == 1 else None


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def check(repo, stream=None):
    """-> (problems, resolved, held, declined, skipped) over `repo`.

    `stream` is resolved inside rather than defaulted in the signature, so a
    caller that redirects `sys.stdout` -- the suite does, to read the report
    rather than let it print over the runner's own output -- redirects this too.
    A default bound at import time is the one a redirect cannot reach.
    """
    stream = sys.stdout if stream is None else stream
    problems = []
    tool_path = os.path.join(repo, TOOL)
    try:
        tool_text = read(tool_path)
    except OSError as exc:
        return ([f"{TOOL}: not read ({exc.__class__.__name__}) -- that is a "
                 f"broken check, not an empty one"], 0, 0, 0, 0)

    resolved = {}
    for key, what, needle in ANCHORS:
        line = resolve(tool_text, needle)
        if line is None:
            problems.append(f"{TOOL}: {what} is not found by this method "
                            f"(needle {needle!r}) -- the anchor is declared "
                            f"from the tool's own source and is either gone or "
                            f"no longer unique; that is a stale declaration, "
                            f"not an absence")
            continue
        resolved[key] = line
        print(f"  {key}: {TOOL}:{line}  {what}", file=stream)

    held = declined = skipped = 0
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
                    f"reworded out of the shape the declared list expects, "
                    f"which is not the same as its number being right")
                continue
            for match in matches:
                at = line_of(starts, match.start())
                cited = int(match.group(1))
                first, raw = paragraph(lines, at)
                why = supersession(raw)
                # Keyed on the paragraph, not the line: see `paragraph()`.
                seen.append((first, cited))
                if why:
                    skipped += 1
                    print(f"  skip ({why}) {rel}:{at} cites :{cited}",
                          file=stream)
                    continue
                read_count += 1
                if key not in resolved:
                    continue  # already reported against the tool
                want = resolved[key]
                if cited == want:
                    held += 1
                else:
                    problems.append(
                        f"{rel}:{at}: cites :{cited} for {key}, which is "
                        f"{TOOL}:{want} on this tree -- hold the code, not the "
                        f"number, or the next growth of the tool is a sentence "
                        f"that reads correctly")
        unclaimed, passed_over = pointer_sites(collapsed, starts, lines, seen)
        declined += len(unclaimed)
        skipped += len(passed_over)
        for at, cited in unclaimed:
            print(f"  declined {rel}:{at} cites :{cited} -- not in this "
                  f"tool's declared list, which is either a synthetic fixture "
                  f"or a claim this tool does not hold", file=stream)
        for at in passed_over:
            print(f"  skip (superseded) {rel}:{at} -- a figure kept visible "
                  f"beside the correction that replaced it", file=stream)
        print(f"  {rel}: {read_count} declared citation(s) read, "
              f"{len(unclaimed)} declined, {len(passed_over)} skipped",
              file=stream)
    return problems, len(resolved), held, declined, skipped


def pointer_sites(collapsed, starts, lines, seen):
    """-> ([(line, number)] declined, [line] skipped) for each unclaimed site.

    A citation no declared locator claimed is one of two things, and reporting
    it as either without saying which is how "checked nothing" and "found
    nothing" come to read alike: it is **declined** when it is a claim this
    tool does not hold, and **skipped** when it sits in a superseded
    paragraph. The skip is the in-place correction this repository makes when
    it re-points one of these, which names the figure it replaces and so must
    stay visible as text -- counting it as work the tool declined to do would
    make every correction look like an unexamined claim.

    Keyed on the line and the number, so a line that spells one citation twice
    -- `check_eq_guard_citations.py` writes `xdata_register_map.py:1220` and
    `../tools/xdata_register_map.py:1220` in a single sentence to say the two
    are one claim -- is counted once. That sentence is the sibling's own
    argument for reading both spellings, and counting it twice here would
    report the same claim as two.
    """
    declined, skipped, counted = [], [], set()
    for match in POINTER.finditer(collapsed):
        at = line_of(starts, match.start())
        cited = int(match.group(1))
        first = paragraph(lines, at)[0]
        if (first, cited) in seen:
            continue
        if (at, cited) in counted:
            continue
        counted.add((at, cited))
        why = supersession(paragraph(lines, at)[1])
        if why:
            skipped.append(at)
        else:
            declined.append((at, cited))
    return declined, skipped


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # `--repo` rather than nothing, so a case can point the whole report at a
    # scratch tree and read the same output a human reads. The scratch tree is
    # where the failing invariant is demonstrated: nothing in this repository
    # makes the check red, by design.
    ap.add_argument("--repo", default=REPO,
                    help="repository root to read (default: this one)")
    args = ap.parse_args()

    print(f"check_py_citations.py: the {len(ANCHORS)} anchors of the committed "
          f"Python sources' own citations into {TOOL}:")
    problems, resolved, held, declined, skipped = check(args.repo)
    if problems:
        print(file=sys.stderr)
        for problem in problems:
            print(f"  FAIL {problem}", file=sys.stderr)
        print(f"check_py_citations.py: {len(problems)} problem(s). Every "
              f"number here is a grep over a committed file, measured on {TREE}; "
              f"nothing in this run is a statement about the EC or the firmware.",
              file=sys.stderr)
        return 1
    if not held:
        print("check_py_citations.py: read no citation at all, which is a "
              "broken check rather than a clean tree", file=sys.stderr)
        return 1
    print(f"{held} citation(s) name the line their code is on, {declined} "
          f"declined as not this tool's, {skipped} skipped as superseded -- "
          f"{resolved} of {len(ANCHORS)} anchors resolved, over "
          f"{len(CITATIONS)} declaring file(s). A run that checks nothing is a "
          f"failure of this test, not a pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())