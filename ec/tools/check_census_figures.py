#!/usr/bin/env python3
"""Hold every prose restatement of a census figure to the census itself.

`ec/annotations/xdata-register-map.md` opens on a number and repeats it for the
length of the file, and `docs/findings.md` §3c repeats it back. Issue #292's
count rule reads table cells keyed on a cluster id and, by its own docstring,
leaves free text alone, so all of that sits on the far side of the line the
merge drew -- a legitimate line, with the figures on the wrong side of it. The
figures drift, and the only thing that noticed was an issue opened by a follow-up
pass reading the tree.

So a figure's being *written down* is not evidence of anything. This tool
re-derives the figures from `ec/annotations/xdata-registers.csv` and
`ec/annotations/xdata-clusters.csv` -- the two files
`xdata_register_map.py --check` regenerates cell for cell, so a figure derived
from them is the census figure by construction rather than by assertion -- and
then asks each prose site whether it agrees. A census move turns the prose red.

**Three things this reads, and one it refuses to read.** The two CSVs above, by
`csv`. `ORACLE` and `BUCKET_TOTALS` out of `xdata_register_map.py`, by `ast` --
read as text and parsed, never imported, because importing the census tool runs
its module-level work and a checker that costs a second to start is a checker a
person stops running. That is the technique `check_doc_figure_pins.py` uses for
the same two constants. And the declared site list, by `csv`, which holds **no
expected values**: a row says where a figure lives and which key it means, and
the value it is held to is measured here, every run. That is the whole of what
keeps this from becoming the next hand-kept total -- a census pass moves the
prose, not this file.

The constants are read **by name**. `xdata_register_map.py` has a second
module-level dict, `OWNERSHIP`, and it shares six key names with `ORACLE`;
`OWNERSHIP["distinct"]` agrees with `ORACLE["distinct"]` and
`OWNERSHIP["refs"]` is 10178 against `ORACLE["refs"]`'s 15696, so a reader that
picked up whichever dict it found first would be comparing two different censuses
and would report agreement or disagreement at random. `check_doc_figure_pins.py`
says the same thing about `counter_sweep_entry.ORACLE` and this one.

**Every `ORACLE` key is either derived here or declined with a reason.** That
partition is asserted rather than assumed, so a census pass that adds a key
gets a red run asking whether this tool can see it -- and a key that is dropped
gets one too, rather than quietly ceasing to be anybody's problem. The declined
five are the reference counts *split by spelling*, and the reason is the same
for all of them: an address the decompile spells two ways is one CSV row, and
the row records one `refs` for the address rather than a split of it, so the
committed CSV cannot say which reference took which token. `xdata-clusters.csv`
cannot help either -- it sums addresses, not tokens. Anything finer needs
`scan()`, which is the census tool's own reader of `ec/decompiled/`, and
re-reading the decompiled tree here would make this a second census whose
answer could part company with the first for reasons that have nothing to do
with prose drift.

**Every declined figure is "not read by this method", never "absent".** The
caveat `ec/annotations/registers.yaml` and `check_doc_figure_pins.py` both
carry, and here it is load-bearing rather than decorative: the verdict on
`extmem_raw` is "this tool derives its figures from the two CSVs and the CSV has
no such column", which is a statement about a method. It is not a statement
that nothing holds the figure. `extmem_raw` is `ORACLE["extmem_raw"]` and the
`--self-test` asserts it; the reader who wants it checked by a machine is
reading `xdata_register_map.py`, and §1a of the register map posts the grep
that prints it.

**And what a site is.** `ec/annotations/xdata-census-figure-sites.csv` names a
file, a heading, a figure-free marker substring, the keys the line's figures
mean, and one of two readings:

  * `live` -- the line claims a figure about this tree, and is held to it. The
    keys are matched to the line's figures in the order they are written, and
    `skip` stands for a figure on that line this site does not claim. Every
    figure a `live` line carries must be claimed or explicitly skipped, so a
    line that grows a new number is a red run rather than a silently unchecked
    one.
  * `historical` / `attributed` -- a superseded figure, or someone else's
    measurement restated, kept visible on purpose. This repository keeps wrong
    figures beside their corrections rather than deleting them (`CLAUDE.md`,
    `docs/findings.md` §4a-4d), so a checker that demanded every figure on a
    page match the current census would be red on a correctly-kept correction
    and would be teaching everyone to delete them instead. These rows are not
    unchecked because they are less important; they are unchecked because the
    page is *right* to keep them, and a marker that stops resolving is how this
    tool says so.

**`lines_after` exists because a console transcript puts the figure on its own
line.** A `--check` result is the marker line; a `grep | wc -l` is the command
line and the number is under it. The alternative was a marker naming the number,
which is the expected value in everything but name -- a census pass would then
leave a stale figure sitting in this CSV looking like a locator. So the marker
stays the command, and `lines_after` says which line the figure is on.

**A marker that resolves to no line, or to more than one, is a problem.** Not a
skip. Markers are content rather than line numbers -- `CLAUDE.md` says to cite
by name because line numbers move -- so a marker is how a site survives an edit
above it. The cost is that a reworded page has to update this list, and that
list is exactly where a reader goes looking for what the pages claim.

**And what this tool is not.** It is not in `.github/scripts/agent-gates.sh`, and
cannot be until a human adds it there with a token that has `workflow` scope;
`.github/` is out of this repository's agent reach by construction. It runs by
hand, which is exactly where `check_doc_figure_pins.py` stands today. A checker
nobody runs is the shape of defect issue #819 was, so that standing is stated
here rather than left for a reader to assume a gate exists.

Usage:
    python3 ec/tools/check_census_figures.py
    python3 ec/tools/check_census_figures.py --print
    python3 ec/tools/check_census_figures.py --verbose
"""
import argparse
import ast
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
ANNOT = os.path.join(EC, "annotations")

CENSUS_TOOL = "xdata_register_map.py"
REGISTERS_CSV = os.path.join(ANNOT, "xdata-registers.csv")
CLUSTERS_CSV = os.path.join(ANNOT, "xdata-clusters.csv")
SITES_CSV = os.path.join(ANNOT, "xdata-census-figure-sites.csv")

# The readings a site row may declare. `live` is held; the other two are
# reported and skipped, each with the reason the page gives for keeping a
# superseded or restated figure where it is.
LIVE, HISTORICAL, ATTRIBUTED = "live", "historical", "attributed"
READINGS = (LIVE, HISTORICAL, ATTRIBUTED)
DECLINED_WORD = "not read"
WHY_SKIPPED = {
    HISTORICAL: "a superseded figure kept visible beside its correction, which "
                "this repository does on purpose",
    ATTRIBUTED: "a measurement this page is restating from someone else, not "
                "one of its own",
}

# The `ORACLE` keys this tool cannot derive from the committed CSVs, each with
# the reason. Asserted as a partition against `ORACLE` rather than left as a
# list to keep in step: a census pass that adds a key fails until this says
# which side of the line it is on.
#
# All five are reference counts split by *spelling*. An address the decompile
# spells two ways is one row of `xdata-registers.csv` carrying one `refs` for
# the address, not a split of it -- `0x07D8` is `symbol+DAT_EXTMEM` on one row,
# and nothing in the committed CSV says which of its references took which
# token. The distinct counts split cleanly because `spellings_by_program` is a
# set, and the reference counts do not because it is not.
DECLINED = {
    "extmem_refs": "the committed CSVs carry no per-spelling reference split",
    "extmem_raw": "a raw token count over ec/decompiled/*.c, which this tool "
                  "does not read -- the grep that prints it is in "
                  "ec/annotations/xdata-register-map.md 1a",
    "extmem_commented": "the difference between the raw token count and the "
                        "comment-stripped one, and this tool strips nothing",
    "extmem_main_refs": "the committed CSVs carry no per-spelling reference "
                        "split",
    "symbol_main_refs": "the committed CSVs carry no per-spelling reference "
                        "split",
}

# The five direction buckets, as `BUCKET_TOTALS` names them and as the
# registers CSV spells them as columns. `read+write` is a column name with a
# `+` in it, which is also the arithmetic operator in a `derived:` key, so a
# derived expression may not name a bucket -- see `EXPR`.
BUCKETS = ("read", "write", "read+write", "passed-to-call", "address-taken")

# A census figure as this corpus writes one: a bare decimal, thousands commas
# optional. The guards are the three ways a digit run is not a figure -- inside
# a longer number, a decimal (`0.5`, a threshold), or abutting an identifier
# that owns it.
FIGURE = re.compile(r"(?<![0-9A-Za-z_.])(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)"
                    r"(?![0-9])(?!\.[0-9])")

# Removed from a site line before any number is read out of it. Hex first,
# because `0x043E` would otherwise leave `043e` behind. A file path is removed
# whole so `xdata-06c2-06db-timers.md` does not read as a figure, and the
# `...` a transcript elides a home directory with is removed with it.
NOT_A_FIGURE = re.compile(
    r"0[xX][0-9A-Fa-f]+"
    r"|\b0x[0-9A-Fa-f]*\.\.\."
    r"|[\w./-]+\.(?:py|md|csv|ya?ml|sh|json|txt|asm|c|yml)\b"
    r"|§[0-9]+[a-z]?"
    r"|#[0-9]+"
    r"|\bissue[s]?\s+#?[0-9]+"
)

HEADING = re.compile(r"^(#{2,6})\s+(.*)$")

# A `derived:` key's grammar: terms joined by `+`/`-`, each a named key or a
# literal. The literal is what lets a sentence that counts a total less one
# address say so, rather than forcing the prose to restate a figure no census
# key publishes.
TERM = r"(?:(?:ORACLE|census):[A-Za-z_][A-Za-z0-9_]*|[0-9]+)"
EXPR = re.compile(rf"{TERM}(?:[+-]{TERM})*")

SKIP = "skip"


def rel(path):
    """`path` as the repository spells it, so a report row can be cited."""
    return os.path.relpath(path, REPO)


def read_csv(path):
    """The data rows of a committed CSV, or [] where it cannot be read.

    [] rather than an exception, so the caller can decide: the census CSVs and
    the site list each have one caller that refuses to report a clean run over
    nothing, and a traceback naming a line would say less than that refusal
    does.
    """
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def int_dict(tool, table):
    """{key: value} for one module-level int dict, read by `ast`.

    By name rather than by shape, because this module has two dicts with
    overlapping keys and only one of them is the census; see the module
    docstring. Returns {} for a name the module does not define or a table that
    is not a literal dict of ints, which the caller reports rather than
    mistaking for a table of zeroes.
    """
    path = os.path.join(HERE, tool)
    try:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError):
        return {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        target = node.targets[0]
        if not (isinstance(target, ast.Name) and target.id == table):
            continue
        out = {}
        for key, value in zip(node.value.keys, node.value.values):
            if (isinstance(key, ast.Constant) and isinstance(key.value, str)
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, int)
                    and not isinstance(value.value, bool)):
                out[key.value] = value.value
        return out
    return {}


def spellings(row):
    """{program: set(spelling)} out of one row's `spellings_by_program` cell.

    The per-program column rather than `program` plus `spelled_as`, because the
    census's main/pd halves are per-*program* facts and a `both` row's
    `spelled_as` is the union across two of them: `0x04A3` is `pair-literal`
    to the main EC and `DAT_EXTMEM` in the PD image, and no single spelling
    describes the row. `ec/annotations/xdata-register-map.md` §2 is the
    reconciliation, and it is why the `extmem_main_distinct` figure and the
    `extmem_pd_distinct` one come out of different columns of the same cell.
    """
    out = {}
    for part in (row.get("spellings_by_program") or "").split(";"):
        if not part.strip():
            continue
        program, _, spelled = part.partition("=")
        out[program.strip()] = set(spelled.strip().split("+"))
    return out


def as_int(cell):
    """A CSV cell as an int, or 0 where it is empty or not one.

    0 rather than a skip because the census writes no empty count cells; a cell
    that stops parsing is a regenerated CSV this tool has not seen, and that is
    a disagreement the figure comparison reports on its own.
    """
    try:
        return int(str(cell).strip())
    except (TypeError, ValueError):
        return 0


def derive(registers, clusters):
    """{name: figure} for everything the committed CSVs decide.

    The names are `ORACLE`'s where `ORACLE` has one, so the comparison below is
    a same-name comparison, and the derivations are the census's own arithmetic:
    a data row is a distinct address, `refs` is the sum of the `refs` column,
    and `main_refs` is the sum of `refs_main_ec` rather than of `refs` over the
    main rows -- a `both` row's `refs` carries the PD program's references too,
    and summing that column over the main rows would count them twice.
    """
    rows = list(registers)
    per = [spellings(row) for row in rows]
    main = {"main-ec", "both"}
    pd = {"pd", "both"}

    def rows_in(programs):
        return [row for row in rows if row.get("program") in programs]

    def spelled(token, program):
        return [row for row, seen in zip(rows, per)
                if token in seen.get(program, ())]

    def column(rs, name):
        return sum(as_int(row.get(name)) for row in rs)

    figures = {
        "distinct": len(rows),
        "refs": column(rows, "refs"),
        "main_distinct": len(rows_in(main)),
        "main_refs": column(rows, "refs_main_ec"),
        "pd_distinct": len(rows_in(pd)),
        "pd_refs": column(rows, "refs_pd"),
        "pd_only": len(rows_in({"pd"})),
        "both": len(rows_in({"both"})),
        # The `name` cell is `symbols.get(addr, "")` in the census, so a row
        # carries one exactly when the symbol table names an address the census
        # reaches -- which is the set `ORACLE["named_in_tree"]` counts.
        "named_in_tree": sum(1 for row in rows if (row.get("name") or "").strip()),
        "extmem_distinct": sum(1 for seen in per
                               if any("DAT_EXTMEM" in s for s in seen.values())),
        "extmem_main_distinct": len(spelled("DAT_EXTMEM", "main-ec")),
        "extmem_pd_distinct": len(spelled("DAT_EXTMEM", "pd")),
        "extmem_pd_refs": column(spelled("DAT_EXTMEM", "pd"), "refs_pd"),
        "symbol_main_distinct": len(spelled("symbol", "main-ec")),
        "symbol_pd_distinct": len(spelled("symbol", "pd")),
        "symbol_pd_refs": column(spelled("symbol", "pd"), "refs_pd"),
        # Derived without an `ORACLE` counterpart, so nothing here is a pin on
        # them and they are checked only where prose names them. Not to be
        # confused with `OWNERSHIP["clusters"]`, which is a different census's
        # figure and which this tool does not read.
        "clusters": len(clusters),
    }
    for bucket in BUCKETS:
        figures[bucket] = column(rows, bucket)
    return figures


def clusters_by_id(clusters):
    """{cluster_id: row} for the committed cluster census."""
    return {row.get("cluster_id"): row for row in clusters}


CLUSTER_COLUMNS = ("size", "refs", "functions_touched")
CLUSTER_COUNTS = ("named",)


def cluster_figure(by_id, cluster_id, column):
    """One cluster's own count, or None where the census has no such cluster.

    `named` is a count of the row's `named_addrs` list rather than a column,
    because the census writes that cell as the addresses themselves: "34" and
    "34 addresses" are the same figure and only one of them is in the file.
    """
    row = by_id.get(cluster_id)
    if row is None:
        return None
    if column in CLUSTER_COUNTS:
        return len((row.get("named_addrs") or "").split())
    if column in CLUSTER_COLUMNS:
        return as_int(row.get(column))
    return None


def resolve(spec, figures, oracle, by_id):
    """(value, detail, kind) for one site key.

    `kind` is what the caller reports on, and there are three of them:
    `ok` (measured), `declined` (this tool does not measure it, and says why --
    the site is legitimate and the figure is held by something else), and
    `unreadable` (the site names something that does not exist, which is a
    problem, not a decline). Keeping the last two apart is the whole point of
    the `registers.yaml` caveat: "this method does not read it" and "there is
    nothing there" are different claims, and only one of them is allowed to
    pass.
    """
    if spec == SKIP:
        return (None, "not claimed by this site", "declined")
    if spec.startswith("derived:"):
        return resolve_expression(spec[len("derived:"):], figures)
    if spec.startswith("ORACLE:"):
        key = spec[len("ORACLE:"):]
        if key in DECLINED:
            return (None, DECLINED[key], "declined")
        if key in oracle:
            return (oracle[key], f'ORACLE["{key}"]', "ok")
        return (None, f"no ORACLE key named {key!r}", "unreadable")
    if spec.startswith("census:"):
        key = spec[len("census:"):]
        if key in figures:
            return (figures[key], f"derived from the committed CSVs ({key})",
                    "ok")
        return (None, f"nothing derives a census figure named {key!r}",
                "unreadable")
    if spec.startswith("cluster:"):
        parts = spec.split(":")
        if len(parts) != 3:
            return (None, f"{spec!r} is not cluster:<id>:<column>", "unreadable")
        value = cluster_figure(by_id, parts[1], parts[2])
        if value is None:
            return (None, f"xdata-clusters.csv has no {parts[1]!r} row",
                    "unreadable")
        return (value, f"the {parts[1]} row's {parts[2]}", "ok")
    return (None, f"{spec!r} is not a key this tool reads", "unreadable")


def resolve_expression(text, figures):
    """(value, detail, kind) for a `derived:` expression's terms and operators.

    Evaluated left to right over the *derived* figures rather than over
    `ORACLE`, because the point of a derived key is that it is arithmetic over
    what the CSVs say -- `ORACLE` is what those are compared against, and using
    it here would make a correction to one side show up as agreement on both.
    """
    text = text.strip()
    if not EXPR.fullmatch(text):
        return (None, f"{text!r} is not a derived expression", "unreadable")
    value = None
    sign = 1
    for part in re.split(r"([+-])", text):
        if part == "":
            continue
        if part in "+-":
            sign = 1 if part == "+" else -1
            continue
        if part.isdigit():
            term = int(part)
        else:
            space, _, key = part.partition(":")
            if space == "ORACLE" and key in DECLINED:
                return (None, DECLINED[key], "declined")
            if space not in ("ORACLE", "census") or key not in figures:
                return (None, f"{part!r} is not a figure this tool derives",
                        "unreadable")
            term = figures[key]
        value = term if value is None else value + sign * term
    if value is None:
        return (None, f"{text!r} reads no figure", "unreadable")
    return (value, f"derived from the committed CSVs ({text})", "ok")


def figures_on(line):
    """The figures a site line carries, in the order it writes them.

    The order matters because a site row's keys are matched positionally: a
    table row reading `1,063 | 157 | 1,172` is three figures and three keys,
    and matching them as multisets would let a transposed row pass. Hex
    addresses, file paths and `§2b`/`#849` references go first, so the `0x043E`
    and `xdata-registers.csv` on a line are not figures.
    """
    text = NOT_A_FIGURE.sub(" ", line)
    return [int(m.group(0).replace(",", "")) for m in FIGURE.finditer(text)]


def section_body(lines, token):
    """(lo, hi) line indexes of the section `token` names, or None.

    The section runs to the next heading of the same or a lower level, so a
    `###` stops at the next `##` and a `##` takes everything under it. An
    ambiguous or absent token is refused rather than guessed: a checker that
    quietly reads §1a when it was asked for §1 is a green run over the wrong
    text, which is the failure this whole tool exists to stop.
    """
    hits = [(i, len(m.group(1))) for i, line in enumerate(lines)
            if (m := HEADING.match(line))
            and re.search(r"(?<![0-9A-Za-z])" + re.escape(token)
                          + r"(?![0-9A-Za-z])", m.group(2))]
    if len(hits) != 1:
        return None
    start, level = hits[0]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        m = HEADING.match(lines[i])
        if m and len(m.group(1)) <= level:
            end = i
            break
    return (start + 1, end)


def site_rows():
    """The declared site rows, each with the CSV line it is written on.

    Read from the CSV rather than held here, so adding a page's figures to the
    sweep is a one-line change to a line-granular file instead of an edit to a
    tool -- and so the file's own convention is line-granular, which
    `xdata-cluster-names.csv` and `ec-0x07d0-sites.csv` already are. The line
    number is kept so a problem can name the row that caused it rather than
    making a reader count down a list.
    """
    return list(enumerate(read_csv(SITES_CSV), 2))


def check_sites(rows, figures, oracle, by_id, root=REPO):
    """(results, declined, problems) for every declared site.

    A result is `(file, lineno, marker, written, value, source)` per figure, in
    the order the site list declares them, so the report and the exit code read
    the same walk. Declined is `(file, lineno, what, reason)`: counted and
    printed, never a failure.

    `rows` and `root` are parameters rather than module state so a case can run
    the whole walk against a small tree of its own -- which is the only way to
    see the mechanism failures, since on the real tree every rule is satisfied
    and a rule that stopped firing would report a clean run.
    """
    results, declined, problems = [], [], []
    for csv_lineno, site in rows:
        where = f"{rel(SITES_CSV)}:{csv_lineno}"
        name = site.get("file") or ""
        marker = site.get("marker") or ""
        token = site.get("section") or ""
        reading = site.get("reading") or ""
        if reading not in READINGS:
            problems.append(f"{where}: reading is {reading!r}; it is one of "
                            + ", ".join(READINGS))
            continue
        path = os.path.join(root, name)
        if not name or not os.path.exists(path):
            problems.append(f"{where}: {name or '(no file)'} is not in this tree")
            continue
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        if token:
            span = section_body(lines, token)
            if span is None:
                problems.append(f"{where}: {name} has no single heading naming "
                                f"{token!r}, so nothing in it was measured")
                continue
            lo, hi = span
        else:
            lo, hi = 0, len(lines)
        at = [i for i in range(lo, min(hi, len(lines)))
              if marker in lines[i]]
        if not at:
            problems.append(f"{where}: {name} has no line reading {marker!r}"
                            + (f" in its {token} section" if token else "")
                            + " -- the figure moved or the sentence was reworded")
            continue
        if len(at) > 1:
            problems.append(f"{where}: {marker!r} is on {len(at)} lines of "
                            f"{name} ("
                            + ", ".join(str(i + 1) for i in at)
                            + "), so which one the site means is a guess; make "
                              "the marker longer")
            continue
        lineno = at[0] + 1
        after = as_int(site.get("lines_after"))
        target = at[0] + after
        if target >= hi:
            problems.append(f"{where}: {name}:{lineno} says the figure is "
                            f"{after} line(s) below it and there is nothing "
                            f"there")
            continue
        written = figures_on(lines[target])
        lineno += after
        if reading != LIVE:
            declined.append((name, lineno, marker, WHY_SKIPPED[reading]))
            continue
        specs = [s.strip() for s in (site.get("keys") or "").split("|")]
        if len(specs) != len(written):
            problems.append(
                f"{where}: {name}:{lineno} carries {len(written)} figure(s) "
                f"and names {len(specs)} key(s); every figure on a live site has "
                f"to be claimed or written `skip`")
            continue
        for spec, figure in zip(specs, written):
            value, detail, kind = resolve(spec, figures, oracle, by_id)
            if kind == "unreadable":
                problems.append(f"{where}: {name}:{lineno} names {spec!r} and "
                                f"it is not readable -- {detail}")
                continue
            if kind == "declined":
                declined.append((name, lineno, f"{figure} ({spec})", detail))
                continue
            results.append((name, lineno, marker, figure, value, detail))
            if figure != value:
                problems.append(
                    f"{where}: {name}:{lineno}: the page writes {figure}, and "
                    f"{detail} reads {value}")
    return results, declined, problems


def fragment(figures, oracle):
    """The markdown a page can cite instead of transcribing a figure.

    `--print` is the answer to "prefer deriving to transcribing" for a page
    that keeps its figures in prose: this emits them once, with the command
    that produced them, and a page that quotes a figure can name the line
    rather than carry the number. The `ORACLE` column is the census's own pin
    where it has one, and `--` where the figure is derived without a pin -- so
    the fragment says which figures are held by a constant and which are only
    held by this derivation.
    """
    lines = [
        "<!-- Generated by `python3 ec/tools/check_census_figures.py --print`. "
        "Do not hand-edit: every figure below is re-derived from "
        "`ec/annotations/xdata-registers.csv` and `ec/annotations/xdata-clusters.csv` "
        "on every run. -->",
        "",
        "| figure | value | `xdata_register_map.py`'s pin | derived from |",
        "|---|---:|---|---|",
    ]
    sources = {
        "distinct": "data rows of `xdata-registers.csv`",
        "refs": "the `refs` column, summed",
        "main_distinct": "rows whose `program` is `main-ec` or `both`",
        "main_refs": "the `refs_main_ec` column, summed",
        "pd_distinct": "rows whose `program` is `pd` or `both`",
        "pd_refs": "the `refs_pd` column, summed",
        "pd_only": "rows whose `program` is `pd`",
        "both": "rows whose `program` is `both`",
        "named_in_tree": "rows with a non-empty `name`",
        "extmem_distinct": "rows any program spells `DAT_EXTMEM`",
        "extmem_main_distinct": "rows the main EC spells `DAT_EXTMEM`",
        "extmem_pd_distinct": "rows the PD image spells `DAT_EXTMEM`",
        "extmem_pd_refs": "the `refs_pd` column of those rows, summed",
        "symbol_main_distinct": "rows the main EC spells by symbol",
        "symbol_pd_distinct": "rows the PD image spells by symbol",
        "symbol_pd_refs": "the `refs_pd` column of those rows, summed",
        "clusters": "data rows of `xdata-clusters.csv`",
    }
    order = [k for k in sources]
    order += [b for b in BUCKETS]
    for key in order:
        if key not in figures:
            continue
        pin = f'`ORACLE["{key}"]`' if key in oracle else "--"
        if key in BUCKETS:
            pin = f'`BUCKET_TOTALS["{key}"]`'
            sources.setdefault(key, f"the `{key}` column, summed")
        lines.append(f"| `{key}` | {figures[key]:,} | {pin} | "
                     f"{sources.get(key, 'the committed CSVs')} |")
    for key in sorted(DECLINED):
        held = f'`ORACLE["{key}"]`' if key in oracle else "--"
        lines.append(f"| `{key}` | not read by this method | {held} | "
                     f"{DECLINED[key]} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", dest="emit", action="store_true",
                    help="emit the figures as a markdown fragment for prose to "
                         "cite, instead of checking the declared sites")
    ap.add_argument("--verbose", action="store_true",
                    help="name every figure this run derived, so a reader can "
                         "see how wide 'not read by this method' was over")
    args = ap.parse_args()

    registers = read_csv(REGISTERS_CSV)
    clusters = read_csv(CLUSTERS_CSV)
    if not registers:
        print(f"{rel(REGISTERS_CSV)} could not be read, so no census figure was "
              f"measured -- this is a declined run, not a clean one",
              file=sys.stderr)
        return 2
    if not os.path.exists(SITES_CSV):
        # Refused rather than reported as a run over zero sites. A checker whose
        # failure mode is silence has no worse case than a clean exit over an
        # empty site list, which is what the missing-file path would give.
        print(f"{rel(SITES_CSV)} is not in this tree, so there was nothing to "
              f"hold to the census", file=sys.stderr)
        return 2
    oracle = int_dict(CENSUS_TOOL, "ORACLE")
    buckets = int_dict(CENSUS_TOOL, "BUCKET_TOTALS")
    if not oracle or not buckets:
        print(f"{CENSUS_TOOL}'s ORACLE / BUCKET_TOTALS could not be read by ast, "
              f"so the prose has nothing to be held to", file=sys.stderr)
        return 2
    figures = derive(registers, clusters)

    if args.emit:
        print(fragment(figures, oracle))
        return 0

    by_id = clusters_by_id(clusters)
    rows = site_rows()
    results, declined, problems = check_sites(rows, figures, oracle, by_id)

    # The partition first: an `ORACLE` key this tool neither derives nor
    # declines is a key the prose can name and nothing holds, and a key it
    # derives that `ORACLE` has moved is a stale pin. Both are the conditions
    # this tool exists to make loud, so they are reported before the sites.
    for key in sorted(set(oracle) - set(DECLINED) - set(figures)):
        problems.append(f'ORACLE["{key}"] is neither derived from the committed '
                        f"CSVs nor listed in DECLINED, so this tool has no "
                        f"measurement for it")
    for key in sorted(set(DECLINED) & set(figures)):
        problems.append(f'ORACLE["{key}"] is listed in DECLINED but the '
                        f"committed CSVs do derive it ({figures[key]}), so the "
                        f"decline is stale and the figure needs a site")
    for key in sorted(set(figures) & set(oracle)):
        if figures[key] != oracle[key]:
            problems.append(f'ORACLE["{key}"] reads {oracle[key]} and the '
                            f"committed CSVs derive {figures[key]}; the pin is "
                            f"stale")
    for key in sorted(buckets):
        if key not in figures:
            problems.append(f'BUCKET_TOTALS["{key}"] has no column in the '
                            f"committed registers CSV")
        elif figures[key] != buckets[key]:
            problems.append(f'BUCKET_TOTALS["{key}"] reads {buckets[key]} and '
                            f"the committed CSVs derive {figures[key]}")

    for name, lineno, marker, written, value, detail in results:
        state = "ok" if written == value else "MISMATCH"
        print(f"  {state:<8} {rel(os.path.join(REPO, name))}:{lineno}  "
              f"{written} vs {value}  {detail}")
    for name, lineno, marker, why in declined:
        print(f"  {DECLINED_WORD:<11} {rel(os.path.join(REPO, name))}:{lineno}  "
              f"{why}")
    if args.verbose:
        print(f"  {len(figures)} figure(s) derived from "
              f"{rel(REGISTERS_CSV)} and {rel(CLUSTERS_CSV)}: "
              + ", ".join(f"{k}={figures[k]}" for k in sorted(figures)))
        print(f"  {len(DECLINED)} ORACLE key(s) declined: "
              + ", ".join(sorted(DECLINED)))

    checked = [r for r in results]
    agreed = sum(1 for r in checked if r[3] == r[4])
    print(f"census figures: {len(checked)} site figure(s), {agreed} agree, "
          f"{len(checked) - agreed} disagree, {len(declined)} not read by this "
          f"method ({len(rows)} site(s) declared in {rel(SITES_CSV)})")

    for line in problems:
        print(f"check_census_figures: {line}", file=sys.stderr)
    if problems:
        print(f"check_census_figures: {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print("check_census_figures: every declared site agrees with the committed "
          "census")
    return 0


if __name__ == "__main__":
    sys.exit(main())