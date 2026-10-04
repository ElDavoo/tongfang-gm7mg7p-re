#!/usr/bin/env python3
"""Measure the probe appenders' capture formats: the bytes on disk, and the codec.

The `ts,addr,old,new` capture declares `utf-8` at every reader and writer of it,
which is the decision `docs/findings/0751-capture-encoding.md` records, and
`check_capture_encoding.py` re-derives that decision's numbers. Three other
appenders were left out of it deliberately and now declare the codec themselves:
`battery_trace.py` and `charge_target_test.py` write a `ts,phase,...` shape and
`ctgp_dben_probe.py` a `ts,mark,...` one, and `evidence/battery-traces/` -- the
directory both of the first two land captures in -- is a population that tool's
`count()` does not apply to. `docs/findings/probe-csv-encoding.md` is the
write-up; this is what re-derives its numbers so none is a hand-typed claim.

**Two halves, and they are not the same kind of thing.** The *corpus* half
walks the committed captures, reads each twice -- once through the declared
codec and once through the locale default the readers used before -- and
compares the whole decoded text, not a tally of marks, because the sibling's
`marks`/`changes` columns are its product for the `ts,addr,old,new` shape and
mean nothing for a `ts,phase,...` file. It reports three problems: a BOM, a
capture the declared reader refuses, and two reads that disagree.

The *declaration* half is the other direction and is the one that can fail on
any runner: each site is located by a content anchor rather than a line number
and asserted to carry an `encoding=`. A line number would be true only until
the next merge that grew the file above it, and `battery_trace.py`, the file
this is most often cited against, carries a live pin at `:51`.

What this does not do:

  * *Run on Windows, or reach the EC.* Nothing here runs anywhere but this
    checkout. It is *not* a Windows run -- no EC and no laptop is reachable
    from here, and the writes that matter are made by a person standing at the
    machine. A codec is a property of the Python that writes, so what is under
    test is what these scripts ask for, not what a stock Windows interpreter
    would have done with them; that stays a prediction from the documented
    default until a human confirms it at the box.
  * *Cover the two shell writers.* `linux/battery-trace/battery-trace` and
    `limit-pair-test` also land captures in `evidence/battery-traces/`, and a
    shell redirection has no `encoding=` to declare. Their files are in the
    corpus half because they are committed; no claim is made about how they
    handle a byte above 0x7F.
  * *Say the ctgp shape cannot carry a high byte.* That is a property of
    `ctgp_dben_probe.py`'s `COLS` and `ARMS`, held by
    `windows/tools/test_ctgp_dben_probe.py` rather than here, because the
    constants live with the tool that writes them.
  * *Hold a count of the corpus.* What a reader gets is the relations: every
    capture decodes, none carries a BOM, and every capture carrying a high
    byte comes out of the declared reader agreeing with the locale-default one.
    The figures printed are this run's, over whatever is on disk today.
"""

import argparse
import ast
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)

# The two committed capture trees, walked in that order.
# `evidence/battery-traces/` is what `battery_trace.py` and
# `charge_target_test.py` append into, and is the population
# `check_capture_encoding.py` deliberately does not walk (its `ROOTS` comment
# says so and names this file). `evidence/ec-watch/` is walked as well because
# `docs/hardware-tests/ctgp-dben-07c4-bit3.md` §6 sends the ctgp capture
# there, and a directory nobody walks is a directory nothing refuses a bad
# file. It is in the sibling's `ROOTS` too, and is walked here under this
# tool's own rules rather than that one's -- no capture of that shape is
# committed, so what this finds there today is the absence of the ctgp shape.
ROOTS = (
    os.path.join(REPO, "evidence", "battery-traces"),
    os.path.join(REPO, "evidence", "ec-watch"),
)

DECLARED = "utf-8"
BOM_BYTES = b"\xef\xbb\xbf"

# The declaration sites, as (repo-relative path, rendered-call anchor, role).
#
# The anchor is a substring of `ast.unparse()` over the call, not a line
# number and not a grep: it has to survive the file growing above the call,
# which is what a bare `file:NNN` in a check does not. The `open(args.csv`
# anchors find the sites each tool opens on its `--csv`. `battery_trace.py`'s
# two carry the mode argument as well, because it opens that path twice -- once
# to append, once to read the header back -- and the second is a reader, whose
# missing keyword means the opposite of the appender's. The `read_text` anchors
# find the capture readers, which are the ones whose argument is a capture path
# rather than a source file.
#
# The `read_text()` sites in these suites that read *source* rather than a
# capture are deliberately *not* here. The undeclared ones are
# `test_battery_trace.py`'s reads of the `battery-trace` and `limit-pair-test`
# scripts and `test_ctgp_dben_probe.py`'s `registers.yaml` read; the reads that
# take a tool's own source and the ctgp suite's other source reads declare a
# codec too, and are in the same different population. Naming the excluded
# sites here would make this table a claim about every `read_text()` in those
# files, which is not what it is -- and a count of them would be stale at the
# next suite that reads another committed file.
# `test_check_probe_csv_encoding.py` holds the classification instead.
DECLARATIONS = (
    ("windows/tools/battery_trace.py", "open(args.csv, 'a'", "writer"),
    ("windows/tools/battery_trace.py", "open(args.csv, 'r'", "reader"),
    ("windows/tools/charge_target_test.py", "open(args.csv", "writer"),
    ("windows/tools/ctgp_dben_probe.py", "open(args.csv", "writer"),
    ("windows/tools/test_battery_trace.py", "(TRACES / name).read_text",
     "reader"),
    ("windows/tools/test_battery_trace.py", "(TRACES / LIMIT_PAIR).read_text",
     "reader"),
    ("windows/tools/test_battery_trace.py", "path.read_text", "reader"),
    ("windows/tools/test_charge_target_test.py", "path.read_text", "reader"),
    ("windows/tools/test_charge_target_test.py", "trace.read_text", "reader"),
    ("windows/tools/test_ctgp_dben_probe.py", "path.read_text", "reader"),
)


def _shown(path):
    """The path a problem should name: repo-relative if the file is in it.

    A `--root` run over a temp tree gets the path it was given rather than a
    `../../../../../tmp/...` chain, because a report nobody can paste into an
    editor is a report nobody opens. The sibling says the same thing about its
    own `_shown`, and for the same reason.
    """
    repo = os.path.abspath(REPO)
    full = os.path.abspath(path)
    if full.startswith(repo + os.sep):
        return os.path.relpath(full, repo)
    return path


def _preferred_encoding():
    """The encoding an `open()` with no `encoding=` uses on this interpreter.

    Locale-dependent by definition -- that is the whole of what the
    declaration removes -- so it is read from a throwaway `open` rather than
    from `locale.getpreferredencoding`, which is not always the answer CPython
    applies when it opens a file.
    """
    with tempfile.TemporaryFile("w") as f:
        return f.encoding


def _decode(raw, encoding):
    """(the decoded text, whether that succeeded)."""
    try:
        return raw.decode(encoding), True
    except UnicodeDecodeError:
        return None, False


def shape(raw):
    """The capture's shape, named by its second header column.

    Read from the bytes rather than from a filename, because the filename is
    the thing a new capture will get wrong: `2026-09-21-0522-follow.csv` says
    nothing about what is in the file. The first line that is neither blank nor
    a `#` annotation carries the header, which is why a file whose annotation
    is on row 0 still reads its shape.

    A file that does not decode as the declared codec is named from a lossy
    decode, so the shape column is not evidence about such a file; whether it
    decodes is the `decodes` column, and that is the one to read.
    """
    text, ok = _decode(raw, DECLARED)
    if not ok:
        text = raw.decode(DECLARED, errors="replace")
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cells = [c.strip() for c in line.split(",")]
        return cells[1] if len(cells) > 1 else "?"
    return "?"


def walk_captures(roots=ROOTS):
    """(path, shape, byte count, BOM, high byte, decodes, locale reads,
    agrees), one per capture under `roots` -- `ROOTS` unless a caller says
    else.

    `agrees` is the load-bearing column and it compares the *whole decoded
    text*: a file both readers accept and both agree on is a file the
    declaration changed nothing about, and a mark tally would not say that for
    a shape whose columns are not marks.
    """
    locale = _preferred_encoding()
    for root in roots:
        for base, _, names in os.walk(root):
            for name in sorted(names):
                if not name.endswith(".csv"):
                    continue
                path = os.path.join(base, name)
                with open(path, "rb") as f:
                    raw = f.read()
                bom = raw.startswith(BOM_BYTES)
                high = any(b > 0x7F for b in raw)
                declared, decodes = _decode(raw, DECLARED)
                inherited, locale_reads = _decode(raw, locale)
                yield (_shown(path), shape(raw), len(raw), bom, high,
                       decodes, locale_reads,
                       bool(decodes and locale_reads
                            and declared == inherited))


def _direct_call(call):
    """Whether `call` is the call itself rather than something wrapping one.

    The test is that `call.func` invokes nothing -- no `Call` anywhere inside
    it. One neighbouring call fails that and would otherwise be reported as
    the site the anchor was written for:
    `path.read_text(...).splitlines()`, whose rendering starts with
    `path.read_text` and whose keywords belong to `.splitlines()`.

    (The other neighbour, an enclosing `csv.reader(path.read_text(...))`, is
    caught by the prefix rule instead; its function expression is a plain
    name.) Without this the checker reads the keywords of the wrong call,
    which is worse than reading none: it would report the capture reader as
    declaring a codec because of what its `.splitlines()` was handed.

    A receiver that is a computed path, as `(TRACES / name).read_text` is, is
    not a call and is fine -- the anchor is naming the `read_text`.
    """
    return not any(isinstance(n, ast.Call) for n in ast.walk(call.func))


def keywords_at(path, anchor):
    """`{keyword: rendered value}` for every call in `path` that `anchor` names.

    The anchor must be a **prefix** of the call's own rendering, and the call
    must be one `_direct_call` accepts; together those two say the anchor is
    naming this call rather than a call around it. Rendering rather than raw
    text, so the anchor names a call and not a line: the file can grow above
    it and the anchor still finds the same call, and the whitespace of a
    wrapped call does not matter.

    The value comes back with the name because *which* codec is declared is
    the claim: a site declaring `encoding="cp1252"` carries a keyword and is
    the exact failure `0751-capture-encoding.md` §3 argued against, so a check
    that only asked whether `encoding` was among the keywords would pass it.
    """
    with open(path, encoding=DECLARED) as f:
        tree = ast.parse(f.read(), filename=path)
    return [{kw.arg: ast.unparse(kw.value).strip("'\"")
             for kw in call.keywords if isinstance(kw, ast.keyword)}
            for call in ast.walk(tree)
            if isinstance(call, ast.Call) and _direct_call(call)
            and ast.unparse(call).startswith(anchor)]


# What a site with the wrong or absent declaration is doing with the wrong
# bytes. The two roles differ in direction, and saying "writes" of a reader
# would be a claim about the wrong half of the round trip.
_WHAT_A_MISSING_KEYWORD_MEANS = {
    "writer": "the bytes it puts on disk are the writing process's locale's, "
              "not this repository's",
    "reader": "the bytes it reads are the reading process's locale's, so a "
              "capture this repository declares can be refused",
}


def check_declarations(sites=DECLARATIONS, root=REPO):
    """(rows, problems) for the declaration table.

    `sites` and `root` are arguments rather than module constants so a caller
    can point the same check at a copy of one tool in a temp tree -- which is
    the only way to see this go red without editing the file it holds.
    """
    rows, problems = [], []
    for rel, anchor, role in sites:
        path = os.path.join(root, rel)
        try:
            found = keywords_at(path, anchor)
        except (OSError, SyntaxError) as e:
            problems.append(f"{_shown(path)}: {anchor} could not be read ({e}), "
                            f"so its declaration is unchecked rather than held")
            continue
        if not found:
            problems.append(f"{_shown(path)}: no call matching {anchor!r}, so "
                            f"this check is not looking at the {role} it names")
        for keywords in found:
            declared = keywords.get("encoding")
            rows.append((_shown(path), anchor, role, declared))
            if declared is None:
                problems.append(
                    f"{_shown(path)}: the {role} matching {anchor!r} declares no "
                    f"encoding=, so "
                    f"{_WHAT_A_MISSING_KEYWORD_MEANS[role]}")
            elif declared.lower().replace("_", "-") != DECLARED:
                problems.append(
                    f"{_shown(path)}: the {role} matching {anchor!r} declares "
                    f"encoding={declared!r} rather than {DECLARED}; the format "
                    f"is {DECLARED} with no BOM "
                    f"(0751-capture-encoding.md §3)")
    return rows, problems


def report(captures, root=REPO):
    """Print both halves. Returns the problems found, which is the exit code.

    `root` is an argument because `--declarations-root` is: it is what lets the
    suite run this over a copy of one tool with a keyword removed. The site
    table itself is not a parameter -- no caller wants a different one, and an
    argument nobody can be seen to pass is a lie about what is configurable.
    """
    problems = []

    print("== the committed corpus, read two ways ==\n")
    print(f"{'file':<62} {'shape':<7} {'bytes':>7} {'BOM':>4} {'hi':>3} "
          f"{'decodes':>8} {'agrees':>7}")
    high = boms = total = 0
    for path, form, size, bom, is_high, decodes, _read, agree in captures:
        total += 1
        high += bool(is_high)
        boms += bool(bom)
        print(f"{path:<62} {form:<7} {size:>7} {'yes' if bom else '-':>4} "
              f"{'yes' if is_high else '-':>3} {'yes' if decodes else 'NO':>8} "
              f"{'yes' if agree else 'NO':>7}")
        if not decodes:
            problems.append(f"{path} is not {DECLARED}-decodable, so the "
                            f"declared reader refuses it; a capture is defined "
                            f"to be {DECLARED}")
        if bom:
            problems.append(f"{path} carries a BOM; the format is {DECLARED} "
                            f"with no BOM")
        elif decodes and not agree:
            problems.append(f"{path}: the declared read and the "
                            f"locale-default read disagree, so the declaration "
                            f"changed what this file says")
    locale = _preferred_encoding()
    print(f"\n{total} capture(s), {high} with a high byte, {boms} with a BOM; "
          f"each read under the declared {DECLARED} and under this "
          f"interpreter's default ({locale}), and the two compared")
    if locale.lower().replace("_", "-") == DECLARED:
        # True on a CI runner, and the reason `agrees` is not the whole result:
        # on a UTF-8 interpreter the two reads are the same read, so the
        # column is trivially `yes` and what it is really showing is that
        # every file *decodes*. That is the claim worth making -- the corpus
        # is utf-8, so declaring utf-8 admits all of it and refuses none. The
        # disagreement branch below is unreachable here, which is why the
        # declaration half, not this one, is the half that can fail.
        print(f"  note: this runner's default is already {DECLARED}, so the "
              f"two reads are the same read here and the agreement column is "
              f"weak evidence on this machine. The strong claim on it is that "
              f"every capture decodes as {DECLARED} -- which is what declaring "
              f"any other codec would have broken.")

    rows, declared_problems = check_declarations(root=root)
    problems += declared_problems
    print("\n== every probe site that touches a capture ==\n")
    print(f"{'file':<38} {'role':<7} {'call':<28} encoding")
    for path, anchor, role, enc in rows:
        print(f"{path:<38} {role:<7} {anchor:<28} {enc or "--"}")
    print(f"\n{len(rows)} site(s) matched; each is a call found by its own "
          f"anchor, not by a line number")

    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true",
                    help="print only the problems, not the per-file table")
    ap.add_argument("--root", action="append", metavar="DIR",
                    help="walk this directory instead of the two committed "
                         "capture trees; repeatable")
    ap.add_argument("--declarations-root", metavar="DIR", default=REPO,
                    help="resolve the declaration table against this "
                         "directory (default: the repository)")
    args = ap.parse_args(argv)

    if args.quiet:
        out = sys.stdout
        sys.stdout = io.StringIO()
    try:
        problems = report(list(walk_captures(args.root or ROOTS)),
                          root=args.declarations_root)
    finally:
        if args.quiet:
            sys.stdout = out

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  {p}")
        return 1
    print("\nok: every committed capture reads the same under the declared "
          "codec as under the locale default, and every probe site declares "
          "one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())