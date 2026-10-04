#!/usr/bin/env python3
"""Hold the `--no-eq-guard` mechanism's own line citations to the code they name.

Five prose files cite **line numbers inside `ec/tools/xdata_register_map.py`**
for the `==` guard, the flag, the two refusals and the classifier around them.
A `:NNN` that lands on a different flag or a different refusal is not a broken
link: it is a sentence that reads correctly and means the wrong line, and
nothing in the tree is red over it. #873 found two of exactly that shape — a
pin for `--no-eq-guard` that resolved to the tail of `--reconcile`'s help, and
a pin for the committed-output refusal that resolved to the `--check` refusal —
and four more that were low by 134 to 1358 lines, by eight different offsets.

**The principle: hold the code, not the number.** A bare `:NNN` is a rank
into a file that keeps growing, and `check_citation_lines.py` already argues the
general case for generated CSVs. Here the population is nine named anchors in
one file: each anchor is a **string of the tool's own source**, resolved by
reading the tool, and each declared citation is a **string of the citing file's
own prose** that names it. An anchor that is gone or no longer unique fails, and
so does a citation reworded out of the shape the declared list expects.

**The `:NNN` itself is not held to today's line** (2026-10-04). It used to be,
and every branch that grew `xdata_register_map.py` above an anchor then had to
re-point five write-ups it had not otherwise touched -- #1849 went red on seven
of them for seeding routines. That is the lock CLAUDE.md's "Cite code by name"
and the unheld pin census are about: the numbers are what the prose measured on
the tree it names, and a citation whose line has since moved is printed as a
note with the anchor's current line beside it, so a reader can follow it, and
the run stays green.

**What it is deliberately not.** This is *not* the general `.py:NNN` pointer
checker: it reads no file outside these five plus the tool, it does not walk the
tree for citations, and it holds no pointer in them. #868 owns
`xdata-086x-dispatch.md:286-288` and states that its fix needs the general tool;
#869 owns the twelve files citing a generated CSV by line outside
`check_citation_lines.py`'s `ROW_SCOPE`; #870 owns the six pointers in
`XDATA_0860`'s 2026-09-24 block. The scope is one mechanism's own pins, and the
census of the class is theirs. The pins these five files carry for *other*
claims — the `--self-test` span, `OUT_CLUSTERS`, `MAP_COLUMNS`, the `--map`
claim rule — are counted and named as **declined**, below.

**What it does not check, which is as much of the point:**

  * *Whether a cited line holds the right code.* That is what this does; a
    checker for the general class would have to answer it for any file and is
    the three open issues above.
  * *A bare `:NNN` this tool cannot attribute.* The locators below capture the
    number out of the sentence that names the code, so every **declared**
    citation is read whatever its spelling. An undeclared bare `:NNN` is a
    number with nothing to say what it is a line *of*, and guessing one is the
    move this tool refuses — it is not seen, and saying so is why the declined
    count is a count of `xdata_register_map.py:NNN` sites specifically.
  * *A superseded figure.* A `>` block is passed over, on
    `check_citation_lines.py`'s own vocabulary: a quoted correction is a denial
    of currency, and `docs/findings.md` §4a-4d requires the figure it replaces
    to stay visible as text beside it. A checker that read those would be red
    on its own corrected tree, which is the surest way to get a check switched
    off. The skip is counted, never silent.
  * *The anchors' uniqueness.* Nine are unique in the tool today and each
    anchor is checked for that; two that are not — `args.out_registers ==
    OUT_REGISTERS` and `args.check or args.self_test`, which each also spell
    `--export-ownership`'s refusals — are declared with the `--no-eq-guard`
    conjunct that distinguishes them, because "a different refusal" is the
    defect this exists for.

Usage:
    python3 ec/tools/check_eq_guard_citations.py            # the committed tree
    python3 ec/tools/check_eq_guard_citations.py --repo DIR # a scratch tree
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
TREE = "d330478"

# (key, what the anchor is, the string of the tool's own source it is). Read by
# `grep -n` and by nothing else -- there is no parse of the tool here, and a
# parse would answer a different question.
ANCHORS = (
    ("store_target",
     "`def store_target(text, start, end, eq_guard=True)` -- the parameter",
     'def store_target(text: str, start: int, end: int, eq_guard: bool = True)'),
    ("eq_guard_reject",
     "the `==` rejection `if eq_guard and stripped.startswith(\"==\")`",
     'if eq_guard and stripped.startswith("==")'),
    ("scan",
     "`def scan(`, where the guard is carried to",
     "def scan(by_file, names, func_names, symbols, eq_guard: bool = True,"),
    ("assign",
     "`ASSIGN`, the operator tuple",
     'ASSIGN = ("=", "|=", "&=", "+=", "-=", "*=", "/=", "^=", "%=", "<<=", ">>=")'),
    ("flip",
     "the `not args.no_eq_guard` flip into the census call",
     "not args.no_eq_guard, args.export_ownership)"),
    ("no_eq_guard_flag",
     "`ap.add_argument(\"--no-eq-guard\", ...)`",
     'ap.add_argument("--no-eq-guard", action="store_true",'),
    ("check_refusal",
     "the `--check`/`--self-test` refusal",
     "if args.no_eq_guard and (args.check or args.self_test)"),
    ("committed_output_refusal",
     "the committed-output refusal",
     "if args.no_eq_guard and (args.out_registers == OUT_REGISTERS"),
    ("reconcile_help",
     "the tail of `--reconcile`'s help -- what `:4457` used to name",
     '"image and registers.yaml, unlike every other mode")'),
)

# (file, ((anchor key, locator), ...)). The locator is a regular expression
# over the file's text with whitespace collapsed, whose **first** group is the
# line number the sentence cites. It is the citation's own content anchor: a
# sentence that stops naming the code stops matching, which is reported rather
# than passed, and that is the half of this the number alone could not do.
#
# Every match of a locator is checked, so a site that appears twice in one file
# is held twice rather than once. Two locators are declared for one anchor
# (`check_refusal`) because two files word the same citation differently, which
# is what a locator is for.
CITATIONS = (
    ("docs/findings/xdata-no-eq-guard-refusal-contract.md", (
        ("check_refusal", r"guard 1, `args\.check or args\.self_test` at `:(\d+)`"),
        ("store_target",
         r"`def store_target\(text, start, end, eq_guard=True\)` at `:(\d+)`"),
        ("eq_guard_reject",
         r"`if eq_guard and stripped\.startswith\(\"==\"\)` at `:(\d+)`"),
        ("scan", r"`def scan\(\)` at `:(\d+)`"),
        ("flip", r"flipped by `not args\.no_eq_guard` at `:(\d+)`"),
    )),
    ("docs/findings/xdata-no-eq-guard-measured-state-correction.md", ()),
    ("ec/annotations/xdata-register-map.md", (
        ("no_eq_guard_flag",
         r"`ap\.add_argument\(\"--no-eq-guard\"`, `\.\./tools/xdata_register_map\.py:(\d+)`"),
        ("committed_output_refusal",
         r"`args\.out_registers == OUT_REGISTERS`, `:(\d+)`"),
        ("check_refusal", r"not the `--check` refusal at `:(\d+)`"),
        ("eq_guard_reject",
         r"`\.\./tools/xdata_register_map\.py:(\d+)` is `if eq_guard and"),
        ("eq_guard_reject",
         r"guard at `\.\./tools/xdata_register_map\.py:(\d+)` — `eq_guard and` —"),
    )),
    ("docs/findings/xdata-4-4-identity-rederivation.md", (
        ("committed_output_refusal",
         r"`args\.out_registers == OUT_REGISTERS`"
         r" at `[\w./-]+xdata_register_map\.py:(\d+)`"),
        ("check_refusal", r"not the `--check` refusal at `:(\d+)`"),
        ("eq_guard_reject",
         r"`if eq_guard and stripped\.startswith\(\"==\"\)` at"
         r" `xdata_register_map\.py:(\d+)`"),
    )),
    ("docs/findings.md", (
        ("store_target", r"`def store_target\(\)` at `xdata_register_map\.py:(\d+)`"),
        ("eq_guard_reject",
         r"`if eq_guard and stripped\.startswith\(\"==\"\)` is at `:(\d+)`"),
        ("assign", r"`ASSIGN` is at `:(\d+)` — not `:277`"),
        ("no_eq_guard_flag", r"`ap\.add_argument` in `xdata_register_map\.py:(\d+)`"),
        ("eq_guard_reject", r"`eq_guard and`, at `xdata_register_map\.py:(\d+)`"),
        # §97's own six, which are the live half of this file's re-points: the
        # #254 block above is a correction paragraph and is skipped, so without
        # these the `store_target` and `ASSIGN` anchors would resolve and be
        # held by nothing at all.
        ("no_eq_guard_flag",
         r"`ap\.add_argument\(\"--no-eq-guard\"` is at \*\*`:(\d+)`\*\*"),
        ("reconcile_help",
         r"the tail of `--reconcile`'s help \(`[^`]+`, now \*\*`:(\d+)`\*\*"),
        ("store_target", r"`def store_target\(\)` is at \*\*`:(\d+)`\*\*"),
        ("eq_guard_reject", r"its `==` rejection at \*\*`:(\d+)`\*\*"),
        ("assign", r"and `ASSIGN` at \*\*`:(\d+)`\*\*"),
        ("eq_guard_reject",
         r"a statement about `xdata_register_map\.py:(\d+)` and nothing else"),
    )),
)

# A citation of the tool in a declared file, in either spelling the corpus uses
# -- `xdata_register_map.py:1220` and `../tools/xdata_register_map.py:1220` are
# one citation, and a span (`:4947-4950`) is one citation opened on its first
# number rather than two. A site no declared locator matched is declined, not
# passed, and counted: "checked nothing" and "found nothing" must not read
# alike.
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
    supersession is a denial of currency, and §4a-4d requires the figure it
    replaces to stay visible as text. Returns the reason rather than a bool so
    `--verbose` can say *why* a citation was passed over.
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


def resolve(tool_text, needle):
    """The 1-based line `needle` is on in the tool, or None.

    `None` for a needle that is not there **and** for one that is there more
    than once: both are *not found by this method*, per `CLAUDE.md`'s rule and
    `ec/annotations/registers.yaml`'s own caveat on the same point, and neither
    is ever reported as the code being absent. An anchor that grew a second
    match is a declaration that has itself gone stale, and it fails.
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
                    continue  # already reported against the tool
                want = resolved[key]
                held += 1
                if cited != want:
                    print(f"  moved {rel}:{at}: cites :{cited} for {key}, which "
                          f"is {TOOL}:{want} on this tree -- the anchor is held, "
                          f"the number is what the prose measured",
                          file=stream)
        unclaimed = pointer_sites(collapsed, starts, lines, seen)
        declined += len(unclaimed)
        for at, cited in unclaimed:
            print(f"  declined {rel}:{at} cites :{cited} -- not in this "
                  f"tool's declared list, which is a different claim",
                  file=stream)
        print(f"  {rel}: {read_count} declared citation(s) read, "
              f"{len(unclaimed)} declined", file=stream)
    return problems, len(resolved), held, declined, skipped


def pointer_sites(collapsed, starts, lines, seen):
    """-> [(line, number)] for each tool citation no declared locator claimed.

    Two tests, and the second is why this is a count rather than a note: a
    citation inside a superseded paragraph is *skipped* rather than declined,
    or every `>` block quoting a superseded number — including the five this
    repository's own corrections carry — would show up here as work this tool
    declined to do.
    """
    out = []
    for match in POINTER.finditer(collapsed):
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
    args = ap.parse_args()

    print(f"check_eq_guard_citations.py: the {len(ANCHORS)} anchors of the "
          f"`--no-eq-guard` mechanism, resolved in {TOOL}:")
    problems, resolved, held, declined, skipped = check(args.repo)
    if problems:
        print(file=sys.stderr)
        for problem in problems:
            print(f"  FAIL {problem}", file=sys.stderr)
        print(f"check_eq_guard_citations.py: {len(problems)} problem(s). Every "
              f"number here is a grep over a committed file, measured on {TREE}; "
              f"nothing in this run is a statement about the EC or the firmware.",
              file=sys.stderr)
        return 1
    if not held:
        print("check_eq_guard_citations.py: read no citation at all, which is a "
              "broken check rather than a clean tree", file=sys.stderr)
        return 1
    print(f"{held} citation(s) name code the tool still has, {declined} "
          f"declined as not this tool's, {skipped} skipped as superseded -- "
          f"{resolved} of {len(ANCHORS)} anchors resolved, over "
          f"{len(CITATIONS)} declaring file(s). A run that checks nothing is a "
          f"failure of this test, not a pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
