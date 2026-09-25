#!/usr/bin/env python3
"""Hold the prose's line citations to the committed CSVs they point into.

`ec/annotations/xdata-086x-dispatch.md`, `docs/findings/reset-vector-dptr-targets.md`
and `ec/annotations/registers.yaml` each name a **line number** inside a
generated CSV or a decompiled `.c`. Four of those numbers went stale in
`6bf9c234` (#683), the regeneration of `xdata-registers.csv` that moved the
`0x0860` row from 662 to 817 and the `0x0800` row from 583 to 738, and three
more in that same commit's `xdata-clusters.csv` renumbering, which is what gave
the `0x07FD`-`0x07FF` cluster its present id and rank. Nothing failed: a `:662`
that lands on the `0x077E` row is not a broken link, it is a sentence that reads
correctly and means the wrong row. #752's `D091.c` header rewrite is *not* the
cause of any of them -- it is a different file -- and it is a live mechanism for
Rules 1 and 2 below, which hold `census_refs` into the decompile rather than a
rank into a generated CSV. `check_site_census.py` holds the CSV's own numbers;
this holds the numbers the prose repeats out of it.

**The principle: hold the address, not the number.** Every one of these
citations is a *rank* into a file that keeps growing, which
`check_cluster_citations.py`'s docstring makes the argument for at cluster
length and which applies unchanged to a 1,327-row generated CSV: a rank is not
an identity, and a regeneration inserting a row anywhere above reshuffles every
row below it. So nothing here compares a cited line against a table of expected
lines. Each rule finds the row for a **declared** address and requires the
citation to be that row, so a regeneration reddens it and a `:NNN` that has
quietly stopped meaning anything cannot pass.

**The three rules**, over committed inputs, none of which re-derives another's
measurement:

  * **Rule 1 -- the site table against the mapping CSV, per site.** The
    `xdata-086x-dispatch.md` table is located *structurally* (the markdown
    table whose header carries a `C occurrence(s)` cell, which is unique in that
    file), each row's first cell is split on commas so the merged
    `0x25CE4`/`0x25CFC` row is one row and two sites, and its `C occurrence(s)`
    cell is compared as a **set** against that offset's `census_refs`. The
    `:49` shorthand and the `bank0/` prefix are normalised away. A site in one
    file and not the other is a mismatch in both directions, and a `--` cell
    has to be a CSV row whose `census_refs` is `none`.
  * **Rule 2 -- the `HAND_CHECKED["0x0860"]` comment against the same CSV, as an
    unordered union.** A deliberately *different* rule from Rule 1, and the
    difference is the point: it is insensitive to how the lines group into
    sites, so a regrouping in the CSV does not redden it, and a citation moved
    onto the wrong site cannot hide behind that insensitivity because Rule 1
    catches that one. Both rules read one source of truth and neither re-greps
    the decompile.
  * **Rule 3 -- every `<generated CSV>:NNN` in the scoped files against its
    declared row.** `ROW_SCOPE` below is the visible list of what is held to
    what. The declared subject is a constant in this file rather than something
    read out of the sentence, because a sentence that cites a row does not
    reliably name that row's subject in the same breath:
    `xdata-086x-dispatch.md:326` cites the `0x0860` per-bucket totals and names
    no address at all.

**The vocabulary: what counts as superseded.** A paragraph that announces itself
a correction is skipped, not checked, and this is not a workaround -- it is the
same skip `check_capture_claims.py` already makes for a unit asserting a capture
did not move, and `check_cluster_citations.py` for a denial: **a quoted
supersession is a denial of currency.** `docs/findings.md` 4a-4d requires the
superseded figure to stay visible as text beside its correction, so a checker
that read those paragraphs would be red on its own corrected tree, which is the
surest way to get a check switched off. Two shapes, both read off the *raw*
lines rather than the joined prose because the marker is markup that a sentence
splitter has already thrown away:

  * any line of the paragraph opens with `>` -- quoted material, whatever it
    quotes. The dispatch page's corrections are blockquotes.
  * the paragraph opens with `CORRECTION` once `>`, `#`, `*`, `-` and whitespace
    are stripped -- the `# CORRECTION (...)` comment in `xdata_register_map.py`
    and the `*** CORRECTION ...` block in `registers.yaml` are one sentence in
    two languages.

The skip is never silent: the run prints how many citations it checked and how
many it skipped, so "checked nothing" cannot read as "found nothing". That is
the third element of `check_cluster_citations.py`'s own return for the same
reason, and a rule that located nothing at all is reported rather than passing
quietly.

**What this does not check, which is as much of the point:**

  * *`registers.yaml`.* Every live sentence in the `XDATA_0860` note *is* a
    `*** CORRECTION` paragraph, because 4a-4d and the 2026-09-24 block both
    require the superseded figure to stay as text. A rule that skipped
    corrections would check nothing there; a rule that did not would redden on
    the quoted predecessor. So those three cells are fixed by hand with a dated
    addendum, and `docs/findings/prose-line-citations-held.md` records that no
    rule covers them.
  * *A pointer into a source file*, as against one into a generated CSV:
    `registers.yaml:3013`'s `:359` and `:1490-1496`, and the `:1399` that
    addendum writes. That is a different tool with its own false-positive
    surface; it belongs beside `citation_frames.py`, and those cells are fixed
    by hand and named as a follow-up rather than promised here.
  * *Whether a cited line still holds the right code.* `check_site_census.py`
    reads the decompile through the census and does that; this holds the
    pointers, so the two together cover the chain and neither re-derives the
    other's measurement.
  * *The other `xdata-registers.csv:NNN` in the tree.* Seven files carry the
    form and `ROW_SCOPE` names the two this walks. Of the five it does not,
    `docs/findings/xdata-0860-census-sites-relined.md` holds the `:662` that is
    the *record* of what #752 found and is meant to stay wrong,
    `ec/annotations/registers.yaml` is the cell above, and the three this
    branch added -- `docs/findings.md` section 58, `ec/README.md` and
    `docs/findings/prose-line-citations-held.md` -- carry the form to name the
    cell being repointed rather than as a live pointer.
  * *A citation in a file outside `ROW_SCOPE`.* Those files are not read at
    all, which is "not done by this method" and never "there is nothing there".
  * *The fourteen addresses other than `0x0860`, and the PD image.* See
    `check_site_census.py`'s first two bullets, which this tool does not
    restate.

Usage:
    python3 check_citation_lines.py [--verbose]
"""
import argparse
import csv
import os
import re
import sys

from check_cluster_citations import units

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
ANNOTATIONS = os.path.join(EC, "annotations")
SITES_CSV = os.path.join(ANNOTATIONS, "xdata-0860-census-sites.csv")
REGISTERS_CSV = os.path.join(ANNOTATIONS, "xdata-registers.csv")
CLUSTERS_CSV = os.path.join(ANNOTATIONS, "xdata-clusters.csv")
DISPATCH_MD = os.path.join(ANNOTATIONS, "xdata-086x-dispatch.md")
RESET_MD = os.path.join(REPO, "docs", "findings", "reset-vector-dptr-targets.md")
MAP_PY = os.path.join(HERE, "xdata_register_map.py")

# Rule 3's scope: (file, csv basename, declared subject, the column holding it).
# The declared subject is a constant here and not read out of the prose, for
# the reason the docstring gives. A file appears twice over the same CSV when
# it cites two subjects from it, and then either declared row satisfies its
# citations -- which is the check and not a loosening of it: a `:NNN` that is
# neither row is the failure, and naming the rows it could have been is what
# makes the report readable.
ROW_SCOPE = (
    (DISPATCH_MD, "xdata-registers.csv", "0x0860", "addr"),
    (RESET_MD, "xdata-registers.csv", "0x0800", "addr"),
    (RESET_MD, "xdata-clusters.csv", "main-ec-086", "cluster_id"),
    (RESET_MD, "xdata-clusters.csv", "main-ec-104", "cluster_id"),
)

# The one file carrying a site table. Rule 1 asks for the file rather than
# walking the tree for a table, so a file with no site table is a file the rule
# does not apply to and not one it failed to find -- which is what keeps the
# "not located" report meaning a renamed column rather than an absent file.
SITE_TABLE_MD = DISPATCH_MD

# The header cell that identifies the site table structurally. Matching the
# header rather than a line number is what lets a `D091.c` rewrite or a section
# renumber move the table without moving the check, and requiring the cell to
# still be there is what stops a renamed column reading as a vacuous pass.
SITE_COLUMN = "C occurrence(s)"

# The two shapes that count as a correction paragraph, both read off the raw
# lines. `units()` strips the `>` and a sentence splitter would read the `#` as
# text, so the marker is recovered from the source rather than the join.
QUOTE = ">"
MARKERS = re.compile(r"^[>\#*\-\s]*")
ANNOUNCES = re.compile(r"^CORRECTION\b", re.IGNORECASE)

# One left-to-right alternation rather than four passes, so the file context
# walks in reading order: `D091.c:71,72` sets the file at the explicit citation
# and the `,72` continues it, `bank0/D091.c's` sets the file without claiming a
# line, and the `(lines 45, 49, ...)` list that follows is bound to it.
# Leftmost-first is what makes that ordering fall out of one scan.
CITATION = re.compile(
    r"(?P<explicit>(?<![\w.])(?:(?:bank\d|common)/)?(?P<efile>\w+)\.c:(?P<eline>\d+))"
    r"|(?P<context>(?<![\w.])(?:(?:bank\d|common)/)?(?P<cfile>\w+)\.c)\b"
    r"|(?P<short>(?<![\w.]):(?P<sline>\d+)\b)"
    r"|(?P<listed>\blines?\b[^.;:()]*?(?P<llist>\d+(?:\s*(?:,|and)\s*\d+)+))"
    r"|(?P<cont>,(?P<cline>\d+)\b)"
)

# The `census_refs` cell, in the CSV's own spelling: one file, a colon, and its
# lines as bare numbers.
CSV_REFS = re.compile(r"(?P<file>[\w./-]+\.c):(?P<lines>\d[\d,]*)")

# A `<generated>.csv:NNN` pointer, in either spelling the corpus uses --
# `xdata-registers.csv:662` or `ec/annotations/xdata-registers.csv:662`. The
# basename is what the scope list keys on, so the path is not part of the
# pattern; `[\w-]` does not cross the `/`.
POINTER = re.compile(r"([\w-]+\.csv):(\d+)")

# A cell without the markdown wrapped around it, a site cell's comma-separated
# offsets, and the three ways this corpus says "this row cites nothing" rather
# than "this row cites zero".
MARKUP = re.compile(r"[`*]")
NO_CITATION = re.compile(r"—|–|-|\bnone\b", re.IGNORECASE)
OFFSET = re.compile(r"0x[0-9A-Fa-f]+")

# `HAND_CHECKED` is keyed by address; this entry's comment is the one in scope,
# and the reason is Rule 2's: it is the comment that re-derives the per-address
# bucket totals the page's own table sums.
HAND_CHECKED = "0x0860"


def repo_path(path: str) -> str:
    return os.path.relpath(path, REPO)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def read_sites(path: str = SITES_CSV) -> list:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def csv_line_of(text: str, id_column: str, declared: str) -> int:
    """The 1-based line number of the row whose `id_column` is `declared`.

    Read off the raw text rather than through `csv.DictReader` alone, because
    the line number is the whole point -- it is the rank the caller has to
    compare a citation against. Raises `KeyError` naming the subject, because a
    declared subject with no row is a scope list that has itself gone stale and
    the failure has to say which.
    """
    for offset, row in enumerate(csv.DictReader(text.splitlines()), start=2):
        if row.get(id_column) == declared:
            return offset
    raise KeyError(f"{declared!r} has no {id_column} row")


def row_label(text: str, lineno: int) -> str:
    """What one line of a CSV is, for a report: its own key, or why it is not
    a row at all. Naming `the header row` or `past the end of the file` is the
    difference between a diagnosis and a number the reader has to look up."""
    lines = text.split("\n")
    if lineno == 1:
        return "the header row"
    if lineno < 1 or lineno > len(lines):
        return "past the end of the file"
    return f"the {lines[lineno - 1].split(',')[0]} row"


def supersession(lines: list) -> str:
    """Why this paragraph is not checked, or "" if it is.

    The reason is returned rather than a bool so `--verbose` can say *why* a
    citation was passed over, which is the whole difference between a
    deliberate skip and a check that has stopped looking.
    """
    for line in lines:
        if line.strip().startswith(QUOTE):
            return "quoted material"
    head = MARKERS.sub("", lines[0].strip()) if lines else ""
    return "a correction paragraph" if ANNOUNCES.match(head) else ""


def paragraph(lines: list, lineno: int) -> tuple:
    """(first line number, raw lines) of the paragraph holding 1-based
    `lineno`.

    A paragraph is a run of non-blank raw lines, and that includes a whole
    markdown table: a table row's own line is a unit to `units()` and a run of
    rows to this, which is harmless for the correction test because a table is
    not quoted material and does not open with the word.
    """
    start = end = lineno - 1
    while start > 0 and lines[start - 1].strip():
        start -= 1
    while end < len(lines) and lines[end].strip():
        end += 1
    return start + 1, lines[start:end]


def line_of(raw: list, start: int, needle: str) -> int:
    """The line `needle` is on inside a paragraph, for the report.

    Not the line the paragraph or the sentence starts on: a citation and the
    sentence making the claim about it are often not on the same line once the
    text is wrapped, and a report that points a reader at the wrong line is
    worse than one that points at none.
    """
    for offset, line in enumerate(raw):
        if needle in line:
            return start + offset
    return start


def parse_citations(text: str) -> set:
    """{(file, line), ...} for every `.c` line a piece of prose points at.

    A *set*, because both callers are unordered: a table cell is compared
    against `census_refs` as a set, since the CSV does not care which order a
    reader lists its lines in, and the `HAND_CHECKED` comment is compared
    against the union over all mapped sites, since that comment does not group
    them into sites at all. File names are reduced to their basename, so the
    CSV's `bank0/D091.c` and the prose's `D091.c` are one file.
    """
    out, current = set(), None
    for m in CITATION.finditer(text or ""):
        if m.group("explicit"):
            current = m.group("efile") + ".c"
            out.add((current, int(m.group("eline"))))
        elif m.group("context"):
            current = m.group("cfile") + ".c"
        elif m.group("short"):
            # `:49` continuing the file the last citation named. With no file
            # named ahead of it there is nothing for the number to be a line
            # *of*, and guessing one is the move this tool exists to refuse.
            if current:
                out.add((current, int(m.group("sline"))))
        elif m.group("listed"):
            if current:
                for number in re.findall(r"\d+", m.group("llist")):
                    out.add((current, int(number)))
        elif current:
            out.add((current, int(m.group("cline"))))
    return out


def parse_csv_refs(text: str) -> set:
    """{(file, line), ...} for a `census_refs` cell: `bank0/D091.c:45,49`."""
    out = set()
    for m in CSV_REFS.finditer(text or ""):
        name = os.path.basename(m.group("file"))
        for number in m.group("lines").split(","):
            out.add((name, int(number)))
    return out


def clean(cell: str) -> str:
    return MARKUP.sub("", cell).strip()


def site_table(text: str) -> tuple:
    """(column index, [(line number, cells)]) for the site table's body rows,
    or (None, None) when no table carries the header.

    Located by the header cell rather than by a line number, so a rewrite that
    moves the table moves the check with it, and the occurrence column is read
    at the index the header puts it rather than at a fixed one. The body is the
    *contiguous* run of table rows that follows the header: this file carries
    six tables and the rows of the next one are not sites, so a scan that ran
    on to the end of the file would report every unrelated `0x0NNN` in it as a
    site with no CSV row.
    """
    seen_header, body = None, None
    for lineno, unit in units(text):
        if not (unit.startswith("|") and unit.rstrip().endswith("|")):
            if body is not None:
                break  # the table ends at the first line that is not a row
            continue
        row = [clean(c) for c in unit.strip().strip("|").split("|")]
        if seen_header is None:
            if SITE_COLUMN in row:
                seen_header, body = row.index(SITE_COLUMN), []
            continue
        if set(row[0]) <= set("-: "):
            continue  # the `|---|---|` separator under the header
        body.append((lineno, row))
    return (seen_header, body) if seen_header is not None else (None, None)


def check_row_pointers(path: str, text: str, scope: list, csvs: dict,
                       verbose=False) -> tuple:
    """Rule 3: every `<generated CSV>:NNN` in one file, against its declared
    row. (problems, checked, skipped).

    `scope` is this file's entries from `ROW_SCOPE` and `csvs` maps a CSV
    basename to its raw text.
    """
    problems, checked, skipped = [], 0, 0
    expected = {}
    for _, name, declared, column in scope:
        try:
            expected.setdefault(name, {})[declared] = csv_line_of(
                csvs[name], column, declared)
        except KeyError as e:
            problems.append(f"{repo_path(path)}: the scope list names {e}")

    lines = text.split("\n")
    for lineno, unit in units(text):
        if not POINTER.search(unit):
            continue
        start, raw = paragraph(lines, lineno)
        why = supersession(raw)
        for name, cited in POINTER.findall(unit):
            at = line_of(raw, start, f"{name}:{cited}")
            # Ordered before the scope test, not after: a quoted supersession
            # is a denial of currency whatever it names, so a correction that
            # quotes a row this tool holds nothing for is passed over rather
            # than reported. A check that reddened on its own corrected tree
            # would be switched off, and then nothing would be left.
            if why:
                skipped += 1
                if verbose:
                    print(f"  skip ({why}) {repo_path(path)}:{at} "
                          f"{name}:{cited}", file=sys.stderr)
                continue
            if name not in expected:
                problems.append(
                    f"{repo_path(path)}:{at}: cites {name}:{cited}, and this "
                    f"tool declares no subject of {name} in this file")
                continue
            if int(cited) in expected[name].values():
                checked += 1
                continue
            problems.append(
                f"{repo_path(path)}:{at}: cites {name}:{cited}, which is "
                f"{row_label(csvs[name], int(cited))}, not "
                + " or ".join(f"the {d} row at {n}" for d, n in
                              sorted(expected[name].items(), key=lambda kv: kv[1]))
                + " -- a rank into a file that keeps growing, so the address "
                  "is what a citation is held to, not the number")
    return problems, checked, skipped


def check_site_table(path: str, text: str, rows: list, verbose=False) -> tuple:
    """Rule 1: the site table against the mapping CSV, per site.

    (problems, checked, skipped). The join is settled in both directions before
    anything is compared, so a site in one file and not the other is a visible
    mismatch rather than a silent one, and a report never mixes "disagrees"
    with "no row" and sends the reader after the wrong one.
    """
    problems, checked = [], 0
    by_offset = {r["file_offset"]: r for r in rows}
    column, body = site_table(text)
    if body is None:
        problems.append(
            f"{repo_path(path)}: no table carries a {SITE_COLUMN!r} header "
            "cell, so the site correspondence was not located -- that is a "
            "broken check, not a clean table")
        return problems, 0, 0

    mapped, listed = {}, []
    for lineno, row in body:
        offsets = OFFSET.findall(row[0])
        if not offsets:
            continue
        listed += offsets
        for offset in offsets:
            if offset not in by_offset:
                problems.append(
                    f"{repo_path(path)}:{lineno}: site {offset} is in the "
                    f"table but {repo_path(SITES_CSV)} has no row for it")
            elif offset in mapped:
                problems.append(
                    f"{repo_path(path)}:{lineno}: site {offset} is in two rows "
                    "of the table")
            else:
                mapped[offset] = (lineno, row[column] if column < len(row) else "")
    for offset in sorted(by_offset):
        if offset not in listed:
            problems.append(
                f"{repo_path(path)}: site {offset} is in "
                f"{repo_path(SITES_CSV)} with no row in the table")
    if problems:
        return problems, 0, 0

    for offset, (lineno, cell) in sorted(mapped.items()):
        want = parse_csv_refs(by_offset[offset]["census_refs"])
        if NO_CITATION.fullmatch(cell):
            if want:
                problems.append(
                    f"{repo_path(path)}:{lineno}: site {offset} cites nothing, "
                    f"and {repo_path(SITES_CSV)} cites "
                    f"{', '.join(f'{f}:{n}' for f, n in sorted(want))} for it")
            else:
                checked += 1
            continue
        got = parse_citations(cell)
        if not got:
            problems.append(
                f"{repo_path(path)}:{lineno}: site {offset} names the C "
                f"occurrence(s) {cell!r}, which holds no `.c:line` to check")
        elif got == want:
            checked += 1
        else:
            problems.append(
                f"{repo_path(path)}:{lineno}: site {offset} cites "
                + ", ".join(f"{f}:{n}" for f, n in sorted(got))
                + " where "
                + (", ".join(f"{f}:{n}" for f, n in sorted(want)) or "nothing")
                + f" -- {repo_path(SITES_CSV)}'s row for that site is the one "
                  "the sweep and the census were joined on")
    return problems, checked, 0


def hand_checked_comment(text: str) -> list:
    """The raw comment lines above `HAND_CHECKED`'s entry, oldest first.

    Walks back over the contiguous comment run, which is this entry's own prose
    and nothing above it: the run stops at the previous entry's closing line.
    The leading `#` is stripped, so a `#`-only separator line reads as the
    empty line that ends a comment paragraph.
    """
    lines = text.split("\n")
    index = next((i for i, line in enumerate(lines)
                  if line.strip().startswith(f'"{HAND_CHECKED}": {{')), None)
    run = []
    for i in range(index - 1, -1, -1) if index is not None else ():
        stripped = lines[i].strip()
        if not stripped.startswith("#"):
            break
        run.append(stripped.lstrip("#").strip())
    return list(reversed(run))


def check_hand_checked(path: str, text: str, rows: list,
                       verbose=False) -> tuple:
    """Rule 2: the `HAND_CHECKED` comment against the mapping CSV, as a union.

    (problems, checked, skipped). The union runs over every mapped site's
    `census_refs`, so the comment is held to naming the same lines *in some
    grouping* -- which is what it does, being a per-address count oracle that
    happens to justify itself by listing the lines. A CSV that regrouped them
    across sites reddens Rule 1 and leaves this one alone, and that asymmetry
    is the reason both rules exist.
    """
    problems = []
    run = hand_checked_comment(text)
    if not run:
        problems.append(
            f"{repo_path(path)}: no comment above the "
            f"HAND_CHECKED[{HAND_CHECKED!r}] entry, so Rule 2 checked "
            "nothing -- that is a broken check, not a clean comment")
        return problems, 0, 0

    want = set()
    for row in rows:
        if row["census_state"] == "mapped":
            want |= parse_csv_refs(row["census_refs"])

    got, skipped, para = set(), 0, []
    for line in run + [""]:
        if line:
            para.append(line)
            continue
        if not para:
            continue
        why = supersession(para)
        if why:
            skipped += len(parse_citations(" ".join(para)))
            if verbose:
                print(f"  skip ({why}) the HAND_CHECKED[{HAND_CHECKED}] "
                      f"comment: {para[0][:60]}", file=sys.stderr)
        else:
            got |= parse_citations(" ".join(para))
        para = []

    if got != want:
        problems.append(
            f"{repo_path(path)}: the HAND_CHECKED[{HAND_CHECKED}] comment "
            "cites " + (", ".join(f"{f}:{n}" for f, n in sorted(got)) or "nothing")
            + " where "
            + (", ".join(f"{f}:{n}" for f, n in sorted(want)) or "nothing")
            + f" is what {repo_path(SITES_CSV)} holds over the mapped sites")
    return problems, len(got), skipped


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="name the citations passed over as superseded, and why")
    args = ap.parse_args()

    csvs = {"xdata-registers.csv": read(REGISTERS_CSV),
            "xdata-clusters.csv": read(CLUSTERS_CSV)}
    sites = read_sites()
    bodies = {DISPATCH_MD: read(DISPATCH_MD), RESET_MD: read(RESET_MD),
              MAP_PY: read(MAP_PY)}

    problems, checked, skipped = [], 0, 0
    for path, text in bodies.items():
        # `bodies` is keyed by path, so a file holding two rules runs both and
        # the one that has no rule for a file is not asked. Three rules, three
        # pairs, and no rule walks a file `ROW_SCOPE` does not name.
        rules = []
        if path == MAP_PY:
            rules.append((check_hand_checked, (path, text, sites, args.verbose)))
        else:
            scope = [s for s in ROW_SCOPE if s[0] == path]
            rules.append((check_row_pointers,
                          (path, text, scope, csvs, args.verbose)))
            if path == SITE_TABLE_MD:
                rules.append((check_site_table, (path, text, sites, args.verbose)))
        for rule, argv in rules:
            found, hit, miss = rule(*argv)
            problems += found
            checked += hit
            skipped += miss

    for problem in problems:
        print(f"check_citation_lines.py: {problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} citation(s) name a line that has moved, or a "
              "rule that located nothing", file=sys.stderr)
        return 1
    print(f"0x0860: {checked} citation(s) resolve to the row they name, "
          f"{skipped} skipped as superseded -- {len(ROW_SCOPE)} declared row(s) "
          f"in {len({s[0] for s in ROW_SCOPE})} markdown file(s), the site "
          f"table and the HAND_CHECKED comment against {repo_path(SITES_CSV)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
