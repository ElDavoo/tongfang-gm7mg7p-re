#!/usr/bin/env python3
"""Census every `test_*.py:NNN` the committed markdown carries, and say which file it named.

Issue #849's `check_doc_figure_pins.py` and issue #801's `check_citation_lines.py`
each hold one narrow class of citation. Neither reaches a line number written
into a **test file**, and `tools/README.md` says so in its own eighth-thing
paragraph: *"nothing checks a citation into a test file, which is why the two
pre-existing ones are still wrong."* Those citations move for a reason no rule
can predict -- #852 put four lines into `ec/tools/test_xdata_cluster_names.py`
at `:291` and every `file:line` the tree cited into that file past `:291` went
stale in the same commit, silently, because a stale pin is a sentence that reads
correctly and means the wrong line.

So this tool is a **census and not a check**, and the split is the whole design:

  * the mechanical half runs here -- find the pins, resolve each to a file and a
    line, say which resolution was used, and count the verdicts;
  * the judgement half does not, and cannot: whether the line a pin names still
    carries the claim it is cited for is a reading, and it lives in
    `docs/findings/test-line-pin-census.md`'s per-pin table.

**This tool renders no verdict on the claim and never fails on drift.** It exits
0 on a tree where every pin is wrong, which is the standing
`prose-line-citations-held.md` records for a rule that would redden on its own
corrected tree: "the surest way to get a check switched off, and then nothing
would be left." It exits non-zero only on a usage error, or on a run that located
no pins at all -- a rule that looked at nothing reports that rather than
returning clean, and the same is true of a census that found nothing.

**The verdicts, each counted and printed:**

  * `resolves` -- the file was found and the span is one it has.
  * `unresolved-path` -- no such file. Where exactly one `test_*.py` in the tree
    has that base name, the report names it, because a wrong directory prefix and
    a deleted file look identical from the exit code and are not the same defect.
  * `ambiguous-path` -- the pin named a bare module and more than one file in the
    tree is called that. Counted and **never guessed**: the two `test_export_*`
    spellings of a rename would otherwise resolve to whichever sorted first.
  * `out-of-range` -- the file is there and the line past its end.
  * `declined` -- a shape this reader refuses, counted and printed with its
    reason and never failing the run. There is exactly one: a pin whose citing
    line is inside a fenced block is a **transcript** of a tool's output, not a
    citation. Declining it is not a guess, and the report says how many it
    passed over so "found nothing" cannot read as "found nothing wrong".

**Every negative here is "not read by this method", never "absent"** -- the caveat
`ec/annotations/registers.yaml` carries for a static scan and
`check_cluster_citations.py` prints for a citation check. Here it is
load-bearing rather than decorative: `unresolved-path` says *no file of that name
is at that path in this tree*, which is a statement about a directory walk, and
`out-of-range` says *this line is not one the file has*, which is a statement
about a line count. Neither is a statement about whether the claim the pin was
written for is true.

**What the reader accepts as a pin.** A `test_*.py` followed by `:NNN` or
`:NNN-MMM`, anywhere in a markdown file, with whatever directory prefix the page
wrote. The prefix is taken **whole** rather than matched against a fixed list of
spellings: a scan that recognises `tools/` but not `windows/tools/` truncates the
second into the first and reports four sound citations as broken paths, which is
the defect this tool exists to measure, one level down. A leading `(` or a
backtick is a boundary; a `/` or a letter is part of the path. A path is read
against the tree first and, if the tree does not have it, **beside the citing
file** -- `ec/annotations/xdata-register-map.md` writes `../tools/…` for its own
neighbour, and reading that against the tree reports a sound pin as a missing
one. Both readings are named in the report for every pin they answer.

**What is not read.** The markdown under `vendor/` (it is committed vendor
material, not this repository's prose), anything under `.git/`, and this census's
own write-up `docs/findings/test-line-pin-census.md` -- whose per-pin table is a
copy of the pins rather than an independent use of them, so counting it would
make the class's size a function of the report about the class. That exclusion is
`check_doc_figure_pins.py`'s `SELF_MODULES` rule applied to a document: a
measurement of the measurement is not evidence about the census. The tree is read
from the filesystem rather than from `git ls-files`, so a scratch copy of it is
census-able, which is what the suite's red demonstration needs.

**And what this tool is not.** It is not in `.github/scripts/agent-gates.sh`, and
cannot be from an agent branch: the plan stage's push token has no `workflow`
scope, so a branch touching `.github/` fails at the very end of the run. It runs
by hand, which is where `check_cluster_citations.py` and
`check_doc_figure_pins.py` stand today. A checker nobody runs is the shape of
defect issue #819 was, so that standing is stated here rather than left for a
reader to assume a gate exists.

Usage:
    python3 ec/tools/census_test_line_pins.py
    python3 ec/tools/census_test_line_pins.py --verbose
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)

# Directories that are walked past rather than pruned on content. `vendor/` is
# committed binary and third-party documentation, `.git/` is the object store;
# both are in the docstring and in `--help` so the population is never a secret.
PRUNED = (".git", "vendor")

# This census's own write-up, for the reason in the docstring: its table copies
# the pins rather than using them. A constant rather than a literal at the call
# site so the suite can hold the exclusion to the file it names.
SELF_DOC = "docs/findings/test-line-pin-census.md"

# A pin: an optional directory prefix, the module, and a line or a line span.
# The lookbehind is what makes `windows/tools/test_x.py:12` one path rather than
# a `tools/` prefix with `windows/` left over the front of it -- without it the
# second is a prefix that exists and the file under it does not, which reads as a
# broken citation and is not one.
PIN = re.compile(r"(?<![\w./-])(?P<path>[\w./-]*test_[a-z0-9_]+\.py)"
                 r":(?P<lo>[0-9]+)(?:-(?P<hi>[0-9]+))?")

RESOLVES = "resolves"
UNRESOLVED = "unresolved-path"
AMBIGUOUS = "ambiguous-path"
OUT_OF_RANGE = "out-of-range"
DECLINED = "declined"
VERDICTS = (RESOLVES, OUT_OF_RANGE, UNRESOLVED, AMBIGUOUS, DECLINED)

# How a pin found its file, printed with every pin so a reader can see which
# rule answered rather than having to infer it from the path. A bare module name
# is resolved against the tree's own inventory; a pin that names a path is
# resolved against that path and nothing else, so a wrong prefix is reported as
# a wrong prefix rather than quietly repaired.
BY_PATH = "by-path"
BY_NAME = "by-name"
BY_BESIDE = "beside-the-citing-file"

# The landing shape of a resolved pin's first cited line -- the distribution
# that is the evidence for the no-checker verdict, and the reason it is worth
# printing on every run rather than only under `--verbose`.
DEF_TEST = "def test_"
ASSERTION = "assertion"
COMMENT = "comment"
BLANK = "blank"
OTHER = "other"
SHAPES = (DEF_TEST, ASSERTION, COMMENT, BLANK, OTHER)


def walk(root, suffix, pruned=PRUNED):
    """Repo-relative paths under `root` ending in `suffix`, sorted, pruned.

    Sorted so a report is reproducible and a case can compare two runs without
    ordering them first. The walk reads the tree it is given rather than
    `git ls-files`, so a scratch copy of the repository is census-able.
    """
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in pruned)
        for name in files:
            if name.endswith(suffix):
                found.append(os.path.relpath(os.path.join(base, name), root))
    return sorted(found)


def lines_of(text):
    """`text` as a list of lines, one entry per line the file really has.

    A trailing newline is a terminator rather than a line, so the empty string
    `split("\\n")` leaves after it is dropped. Without that a two-line file
    counts three lines and a pin naming its last line reads as in range for one
    it is not -- an `out-of-range` that never fires is the verdict this census
    would then be unable to report at all.
    """
    lines = text.split("\n")
    return lines[:-1] if lines and lines[-1] == "" else lines


def suites(root):
    """({relpath: [line, ...]}, {basename: [relpath, ...]}) for the tree.

    Both halves from one walk: the resolved file's text, and the index that
    decides whether a bare module name is unique. A basename with more than one
    file is what `ambiguous-path` is for, so the index keeps the list rather
    than collapsing it to the first match.
    """
    files, index = {}, {}
    for rel in walk(root, ".py"):
        base = os.path.basename(rel)
        if not base.startswith("test_"):
            continue
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as f:
                files[rel] = lines_of(f.read())
        except OSError:
            # A file that cannot be read is not evidence of anything, and the
            # census says so rather than reporting a line count of zero.
            continue
        index.setdefault(base, []).append(rel)
    return files, index


def markdown(root):
    """Repo-relative markdown paths to read, `vendor/` and this census's own
    write-up excluded (see the docstring for why the second is excluded)."""
    return [rel for rel in walk(root, ".md") if rel != SELF_DOC]


def fenced_lines(text):
    """The set of 1-based line numbers inside a ``` fenced block.

    Toggled on the fence line itself, so the opening ``` and its body are both
    inside and the closing one is outside. Markdown's own rule, which is what
    makes "is this a citation or is this a transcript" answerable from the text
    rather than from a convention nobody wrote down.
    """
    inside, out = set(), False
    for at, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith("```"):
            inside.add(at)
            out = not out
        elif out:
            inside.add(at)
    return inside


def pins(text):
    """[(lineno, match)] for every pin in one markdown file, in reading order.

    Whole-line scanning rather than per-paragraph: a pin is a `file:line` spelling
    wherever it is written, and a paragraph-level reader would have to be told
    where a paragraph starts.
    """
    blocks = fenced_lines(text)
    found = []
    for at, line in enumerate(text.split("\n"), 1):
        for hit in PIN.finditer(line):
            found.append((at, hit, at in blocks))
    return found


def shape_of(line):
    """The landing shape of one cited line.

    Read off the first line of the span, which is the convention a range pin
    follows -- `test_disasm8051.py:3-6` names the docstring by its blank opening
    line and `test_grade_0751_isolation.py:16-20` names the import block the same
    way -- so the start is the line a reader is sent to and the end is the one
    that bounds the claim. `blank` is therefore a real answer here and not a miss:
    a span that opens on the blank line above what it is about is the house
    spelling, and a census that counted those as unreadable would misreport its
    own corpus.

    The assertion test is a *call* rather than the word, so a line whose string
    mentions an assertion is not one.
    """
    if re.match(r"^\s*def\s+test_", line):
        return DEF_TEST
    if not line.strip():
        return BLANK
    if re.match(r"^\s*#", line):
        return COMMENT
    if (re.search(r"\bassert\w*\s*\(", line) or re.match(r"^\s*assert\b", line)
            or re.search(r"\bcheck\(", line)):
        return ASSERTION
    return OTHER


def resolve(spelling, base, citing, index, files):
    """(verdict, path, detail) for one pin's module name.

    Three steps, in this order, and the report says which one answered:

      1. a path is resolved **against the tree**, so `ec/tools/test_x.py` is
         that file from anywhere in the repository. A path that is not there is
         not repaired into something that is -- repairing it is the guess
         `docs/findings/test-line-pin-census.md` records as costing four sound
         citations.
      2. a path that is not in the tree is retried **beside the citing file**,
         because `ec/annotations/xdata-register-map.md` writes `../tools/…`
         and `../../docs/findings/…` for its own neighbours and means them. This
         is a second reading, not a choice between two files that both exist:
         step 1 already took the tree's answer whenever there was one.
      3. a bare module name goes to the index, and more than one candidate is
         `ambiguous-path` rather than a silent first match.

    A path that resolves by neither is `unresolved-path`, and the detail names
    the one file of that base name if the tree has exactly one -- a wrong
    directory prefix and a deleted file look identical from an exit code and
    have opposite fixes.
    """
    if "/" in spelling:
        if spelling in files:
            return (RESOLVES, spelling, f"the pin names the path ({BY_PATH})")
        beside = os.path.normpath(os.path.join(citing, spelling))
        if beside != spelling and beside in files:
            return (RESOLVES, beside,
                    f"the path is not in the tree, and it resolves beside the "
                    f"citing file ({BY_BESIDE})")
        elsewhere = index.get(os.path.basename(spelling), [])
        hint = (f"; the only file of that name in the tree is {elsewhere[0]}"
                if len(elsewhere) == 1 else
                "; no file of that name is in the tree" if not elsewhere else
                "; the files of that name are " + ", ".join(elsewhere))
        return (UNRESOLVED, None,
                f"the pin names the path {spelling!r}, which is not in the tree, "
                f"and {beside!r} beside the citing file is not either" + hint)
    candidates = index.get(base, [])
    if len(candidates) == 1:
        return (RESOLVES, candidates[0], f"the module name is unique ({BY_NAME})")
    if not candidates:
        return (UNRESOLVED, None, f"no test_*.py called {base!r} is in the tree")
    return (AMBIGUOUS, None, "the module name is " + ", ".join(candidates)
            + " -- not guessed")


def census(root):
    """(records, files) for every pin under `root`.

    A record is `(citing, lineno, spelling, verdict, path, how, shape, text)`:
    the resolution used and the target's own text are carried so the report and
    a reader's own `--verbose` run say the same thing, and the claiming half of
    the question is left to the write-up's table rather than answered here.
    """
    files, index = suites(root)
    records = []
    for rel in markdown(root):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        for at, hit, fenced in pins(text):
            spelling = hit.group("path")
            lo, hi = int(hit.group("lo")), hit.group("hi")
            if fenced:
                records.append((rel, at, f"{spelling}:{lo}"
                                + (f"-{hi}" if hi else ""), DECLINED, None, "-",
                                "-", ""))
                continue
            verdict, path, how = resolve(spelling, os.path.basename(spelling),
                                         os.path.dirname(rel), index, files)
            lo = max(lo, 1)
            last = max(int(hi), lo) if hi is not None else lo
            if verdict == RESOLVES and last > len(files[path]):
                verdict = OUT_OF_RANGE
                how = f"the file has {len(files[path])} line(s)"
            text_line = (files[path][lo - 1] if verdict == RESOLVES else "")
            records.append((rel, at, f"{spelling}:{lo}" + (f"-{hi}" if hi else ""),
                            verdict, path, how,
                            shape_of(text_line) if verdict == RESOLVES else "-",
                            text_line.strip()))
    return records, files


def tally(records, at):
    """{key: count} over the `at`-th field of every record."""
    counts = {}
    for record in records:
        counts[record[at]] = counts.get(record[at], 0) + 1
    return counts


def report(root, records, files, verbose):
    """The census's whole output, and the counts a run has to be readable by."""
    for citing, at, spelling, verdict, path, how, shape, text in records:
        if not verbose:
            continue
        where = f"{path}:{spelling.rsplit(':', 1)[1]}" if path else "-"
        print(f"  {citing}:{at}  {spelling}  {verdict:<15} {where:<44} {how}")
        if shape != "-":
            print(f"      {shape:<12} {text[:96]}")
        elif verdict == DECLINED:
            print("      the citing line is inside a fenced block, so this is "
                  "a transcript of a run and not a citation")

    verdicts = tally(records, 3)
    shapes = tally([r for r in records if r[3] == RESOLVES], 6)
    targets = {(r[4], r[2].rsplit(":", 1)[1]) for r in records if r[3] == RESOLVES}
    print(f"{len(records)} pin(s) in {len({r[0] for r in records})} markdown "
          f"file(s): {len({r[2] for r in records})} distinct spelling(s), "
          f"{len(targets)} distinct resolved target(s)")
    print("  " + ", ".join(f"{verdicts.get(v, 0)} {v}" for v in VERDICTS))
    print("  " + ", ".join(f"{shapes.get(s, 0)} {s}" for s in SHAPES)
          + " (of the pins that resolve)")
    print(f"  read {len(markdown(root))} markdown file(s) under the tree, "
          f"excluding {'/'.join(PRUNED)}/ and {SELF_DOC}; resolved against "
          f"{len(files)} test file(s) in it")
    print("  no claim is measured here: whether a cited line still carries the "
          "claim it is cited for is a reading, and it is "
          "docs/findings/test-line-pin-census.md's table")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="name every pin: the citing file:line, the target, the "
                         "resolution used, the landing shape and the target "
                         "line's own text")
    args = ap.parse_args()

    read = markdown(REPO)
    if not read:
        print("census_test_line_pins.py: no markdown file was read at all, so "
              "no pin could be looked for -- that is a broken census, not an "
              "empty one", file=sys.stderr)
        return 1
    records, files = census(REPO)
    report(REPO, records, files, args.verbose)
    if not records:
        print("census_test_line_pins.py: no `test_*.py:NNN` was found in the "
              "markdown read, so nothing was censused -- that is a broken "
              "census, not an empty one", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
