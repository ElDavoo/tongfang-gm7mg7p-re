#!/usr/bin/env python3
"""Measure what a fifth column and a `# provenance` row would each cost.

#548 gave `warn_unchecked_marks` a notice for the case it cannot cover: the
grader reads a whole file, a mark no watcher checked refuses the whole run
however it got there, and nothing in the file says which process wrote which
mark. The issue after it (#719) does not ask for a fix -- it asks for the
measurement, because the two candidate shapes cost different things in
different readers and the choice is a fact about this tree rather than about
the format in the abstract.

So this measures and does not change. It writes nothing, opens no capture,
reads no EC and touches no register; it prints, and
`docs/findings/0751-mark-provenance-shapes.md` quotes the output rather than
any hand-copied number, because a figure in that page the tool did not print is
a figure nobody can re-derive. Five sections:

  1. **the row's census** -- every site in the tree that constructs
     `ts,MARK,,label` and every site that consumes it, found by scanning for
     the `"MARK"` literal rather than off a hand-typed list, so a writer
     spelled the way these seven are is in tomorrow's census. The scan matches
     one spelling: the two single-quoted `'MARK'` assertions in the test
     suites are invisible to it, so what keeps a site from going stale is the
     two-way join in section 5, not the scan's coverage;
  2. **the committed fixtures** -- every `*.csv` under `ec/tools/testdata/`
     and `evidence/ec-watch/` that holds a MARK row, with its mark count, its
     column counts, whether it carries a `ts,addr,old,new` header and whether
     it carries `#` rows. This is the count the issue's "how many committed
     fixtures does each shape leave untouched" asks for;
  3. **what each shape costs each reader** -- `read_capture`,
     `existing_mark_labels` and `read_early_exits` on a constructed temp file,
     and `grade_timer_sweep.load` on a second one carrying a `resumed` mark.
     Printed from a call, not concluded from a reading of the source: the
     issue says a fifth column "passes `len(row) < 4` and `row[0..3]`
     unpacks", and only a call settles whether that is an ignored tail or a
     `ValueError`;
  4. **the `#` namespace** -- the machine-written `#` phrases each capture
     family already spends, since one shape's cost is what it takes from a
     namespace the readers treat by exact phrase;
  5. **the citations** -- every site this tool and its page name is re-read
     at the line quoted, and the tool fails loudly when a line has drifted.
     That is the discipline `docs/findings/0751-append-unchecked-marks.md` §
     "The issue's line numbers have drifted" records as a caution, turned
     into a check. The row-site join runs in both directions, as
     `check_site_census.py` does: a scanned site no citation names is a
     missing entry, not a footnote.

**What this does not check, which is as much of the point:**

  * **Whether a shape is a good idea.** The tool measures and prints; the
    page argues. Nothing here fails on a shape being wrong.
  * **The other three writers.** `system_id_probe.py`,
    `ec_timer_capture.py` and `manual_fan_ctrl_probe.py` write the same row
    and are in the census, but nothing here decides what a widened shape
    should mean for any of them. Deciding is the implementation issue's.
  * **A capture this tool cannot see.** The fixture census walks two
    committed directories. A capture taken at the machine and not committed
    is not counted, and "0 fixtures untouched" is a count over those two
    directories and never a census of every capture that exists anywhere.
  * **A run.** Nothing here opens a capture, so nothing here is evidence
    about the machine: no mark was typed, no block was written, no §3 block
    was run. Every figure is offline behaviour of a reader over a file
    constructed for it, or a count over a committed tree.
  * **Whether the *readers* are right.** A reader that silently drops a fifth
    column is the fact being measured; the measurement agreeing with the page
    is not the reader agreeing with the firmware.

Usage:
    python3 measure_mark_provenance.py [--page PATH] [--self-test]
"""
import argparse
import csv
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
GRADER = os.path.join(HERE, "grade_0751_isolation.py")
TIMER = os.path.join(HERE, "grade_timer_sweep.py")
PAGE = os.path.join(REPO, "docs", "findings",
                    "0751-mark-provenance-shapes.md")

# The two committed directories the issue names for its fixture count. Fixed
# rather than globbed so a new directory is a visible decision rather than a
# silently larger denominator.
FIXTURE_ROOTS = (os.path.join(EC, "tools", "testdata"),
                 os.path.join(REPO, "evidence", "ec-watch"))

# The row's marker as it is spelled in every writer. Scanned for as a Python
# string literal: `ts,MARK,,label` appears in three docstrings as prose and
# would make the writer census a census of documentation. The double quotes are
# part of the match, so a line spelling the row `'MARK'` is not found -- the two
# such lines in the tree are `test_ec_watch.py` and `test_system_id_probe.py`,
# both assertions, and the page names the blind side rather than the count.
ROW_LITERAL = '"MARK"'

# What a constructed capture carries in its fifth column and in its
# provenance comment. Representative rather than proposed -- the shape of the
# value is all any reader here sees, and the page argues about what it should
# say separately. No comma, so the row stays five columns under `csv.writer`
# and the comment stays one field.
PROVENANCE = "pid=4821 prog=ec_watch.py label-vocab=0751"
PROVENANCE_TAG = "# provenance"

# Two constructed captures, one per family, because the readers were written
# for different files. §3's is the 0751 shape; the timer one carries the
# `# interval`/`# baseline` metadata `grade_timer_sweep.load` reads and a
# `resumed` mark, because a 0751-shaped file would leave that reader's phrase
# branch untested and "zero cost" measured on an unreached branch is not a
# measurement. `None` is where a shape puts its provenance: on the mark's own
# row, on a row of its own ahead of the marks it covers, or nowhere.
CONSTRUCTED_0751 = [
    ("# the run ended early: 2026-01-01T12:01:30.000+01:00, "
     "fan stalled: the restore never ran", None, None, None, None),
    ("2026-01-01T12:00:02.000+01:00", "0x0796", "0x2F", "0x30", None),
    ("2026-01-01T12:00:10.000+01:00", "MARK", "", "settled", None),
    ("2026-01-01T12:00:24.250+01:00", "0x0796", "0x30", "0x31", None),
    ("2026-01-01T12:00:41.750+01:00", "MARK", "", "wrote 0x0751=0xA0", None),
    ("2026-01-01T12:00:56.000+01:00", "0x0751", "0xA0", "0xA0", None),
    ("2026-01-01T12:01:20.000+01:00", "MARK", "", "restored 0x0751=0xA0",
     None),
]
CONSTRUCTED_TIMER = [
    ("# ec/tools/ec_timer_capture.py, read-only, ECMG window 0xfe410000 via "
     "/dev/mem", None, None, None, None),
    ("# interval 0.0005s  seconds 60.0  2 addresses: 0x06D6 0x06D9", None,
     None, None, None),
    ("# baseline 2026-01-01T12:00:00.000+01:00: 0x06D6=0x03 0x06D9=0x03", None,
     None, None, None),
    ("2026-01-01T12:00:01.000+01:00", "0x06D6", "0x03", "0x02", None),
    ("2026-01-01T12:00:02.000+01:00", "MARK", "", "auto: resumed, ~1.0 s "
     "suspended", None),
    ("2026-01-01T12:00:03.000+01:00", "0x06D6", "0x02", "0x01", None),
]

# The three shapes, by the field `None` above names: no provenance at all (the
# base every other shape is compared against), a fifth column on the MARK row,
# and a `# provenance` comment row ahead of the marks it covers.
SHAPES = ("none", "fifth column", "provenance row")


def repo_path(path: str) -> str:
    """The tree-relative path every message uses, so a figure quoted from this
    tool's output can be opened without a `cd`."""
    return os.path.relpath(path, REPO)


def load_module(name: str, path: str):
    """Import `path` by name, the arrangement `ec_watch.py`'s
    `load_label_vocab` and `test_manual_fan_ctrl_probe.py` already use.

    By path rather than by import so the tool runs from any working directory
    and so the rules it measures are the graders' own functions rather than
    anything copied here: a copy could agree with the grader today and drift
    from it tomorrow, and a measurement of a copy is a measurement of
    nothing."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"importlib has no loader for {repo_path(path)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def py_sources():
    """Every committed `.py` in the tree but this one, sorted. The whole tree
    rather than the four component `tools/` directories `check_python_syntax`
    globs: a writer under `tools/` or a new component directory is exactly
    what a hand-scoped scan would miss, and this is the scan's own blind side.

    This file is excluded because it quotes the row it is measuring -- in the
    citation table, in `own_provenance` and in the constructed captures -- and
    a census that counted its own quotes would report every reader line twice
    and every writer line once more than it exists. Compared as repo-relative
    paths rather than as joined ones: `REPO` is built with `os.pardir` and
    `os.walk` does not normalise what it yields, so the two spellings of this
    file's own path differ as strings and an `==` against the joined one would
    never match."""
    me = repo_path(os.path.abspath(__file__))
    out = []
    for dirpath, dirs, names in os.walk(REPO):
        dirs[:] = sorted(d for d in dirs if d not in (".git", "__pycache__"))
        out += [os.path.join(dirpath, n) for n in names
                if n.endswith(".py")
                and repo_path(os.path.join(dirpath, n)) != me]
    return sorted(out)


def line_of(path: str, lineno: int) -> str:
    """The source line at `lineno`, or `""` past the end of the file, so a
    citation that has drifted *down* past a short file is a mismatch rather
    than an IndexError."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    return lines[lineno - 1] if 0 < lineno <= len(lines) else ""


def row_sites():
    """The `ts,MARK,,label` census: every line carrying the literal, split
    into the sites that construct the row and the sites that consume it.

    A writer is a line with the literal *and* a `.row(` call, which is what
    separates construction from the `== "MARK"` comparisons a reader is made
    of. Both halves are returned so the caller can join them both ways
    against the citation table: a scanned site no citation names is a gap in
    the page, which is the failure this scan exists to make visible."""
    writers, readers = [], []
    for path in py_sources():
        with open(path, encoding="utf-8", errors="replace") as f:
            for n, text in enumerate(f.read().splitlines(), 1):
                if ROW_LITERAL not in text:
                    continue
                site = (repo_path(path), n, text.strip())
                (writers if ".row(" in text else readers).append(site)
    return writers, readers


READER_CALLS = ("read_capture(", "existing_mark_labels(", "read_early_exits(")


def reader_call_sites():
    """(sites, count inside the test suites) for every call of the grader's
    three readers.

    The second half of the census, and it is a second scan because the first
    one has a blind side worth naming: `grade_gpu_door.py:421` never writes
    `"MARK"`. It takes `read_capture`'s two-tuple and counts it, so a
    consumer that never decides whether a row is a mark is invisible to the
    literal scan. This one has the opposite blind side -- it cannot see a
    reader that opened the CSV itself rather than going through the grader --
    and between them the two cover the tree without either pretending to be
    the whole of it.

    A call inside a `test_*.py` is counted and not listed: a suite calling
    the reader is a test of the reader, and listing forty of them would bury
    the six that are a program depending on the row."""
    sites, in_tests = [], 0
    for path in py_sources():
        with open(path, encoding="utf-8", errors="replace") as f:
            for n, text in enumerate(f.read().splitlines(), 1):
                if not any(c in text for c in READER_CALLS):
                    continue
                if text.lstrip().startswith("def "):
                    continue
                if os.path.basename(path).startswith("test_"):
                    in_tests += 1
                else:
                    sites.append((repo_path(path), n, text.strip()))
    return sites, in_tests


def fixture_census():
    """[(relpath, marks, sorted column counts, header?, '#' rows)] per
    committed CSV holding at least one MARK row.

    Read with `errors="replace"` for the reason `existing_mark_labels` gives
    its own docstring: `CsvSink` appends without ever decoding, so a byte the
    default encoding cannot read is a file that exists rather than an
    exception this census would die on."""
    out = []
    for root in FIXTURE_ROOTS:
        for dirpath, dirs, names in os.walk(root):
            dirs[:] = sorted(dirs)
            for name in sorted(names):
                if not name.endswith(".csv"):
                    continue
                path = os.path.join(dirpath, name)
                marks, cols, header, comments = 0, set(), False, 0
                with open(path, newline="", errors="replace") as f:
                    for row in csv.reader(f):
                        if not row:
                            continue
                        if row[0].startswith("#"):
                            comments += 1
                            continue
                        if row[0] == "ts":
                            header = True
                            continue
                        if len(row) > 1 and row[1] == "MARK":
                            marks += 1
                            cols.add(len(row))
                if marks:
                    out.append((repo_path(path), marks, sorted(cols), header,
                                comments))
    return out


def write_capture(path: str, rows, shape: str):
    """One constructed capture, written in `shape`.

    Through `csv.writer`, not a hand-joined string, because that is what
    `CsvSink.row` and `MarkCsv.row` and `ec_timer_capture.Sink.row` all use and
    a hand-join is a *different* format: the timer family's `auto: resumed,
    ~1.0 s suspended` label carries a comma, and joined rather than quoted it
    would read back as a five-column mark with the label's own tail in column
    five -- which is the very shape under test, appearing in the base the other
    shapes are compared against. Every figure in the table below would then be
    measured against a file none of the three real writers would produce.

    The provenance field is absent for the base and present for the fifth
    column, and the comment row is written ahead of the mark it covers."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["ts", "addr", "old", "new"])
        f.write("# CONSTRUCTED INPUT, NOT A CAPTURE -- "
                "measure_mark_provenance.py, a temp file\n")
        for ts, addr, old, new, provenance in rows:
            if addr is None:
                # Already a `#` line: the timer family's metadata, which the
                # shape is not allowed to rewrite.
                f.write(ts + "\n")
                continue
            fields = [ts, addr, old, new]
            if provenance is not None:
                fields.append(provenance)
            w.writerow(fields)
            if shape == "provenance row" and addr == "MARK":
                # Ahead of the mark it covers, which is the whole of what
                # "per process rather than per mark" buys: the binding is
                # positional, so a reader has to count.
                f.write(f"{PROVENANCE_TAG} {PROVENANCE}\n")


def build(rows, shape: str):
    """`rows` in `shape`, for the write above's `provenance` field.

    The fifth column and the comment row are the same fact in two places, so
    they are built from one rule and not written twice: a drift between the
    two would make the comparison a comparison of different marks."""
    if shape == "none":
        return rows
    if shape == "fifth column":
        return [(ts, addr, old, new, PROVENANCE if addr == "MARK" else None)
                for ts, addr, old, new, _ in rows]
    return rows


def own_provenance(path: str) -> int:
    """How many of a capture's MARK rows carry their provenance in their own
    row. This is the number that separates the two shapes and it is not a
    reader's answer: a reader has to be *asked* for the tail, and the two
    readers measured below are both written not to ask. So it is read here
    off the file, which is the position a later implementation would have to
    put a reader in to get the same answer."""
    n = 0
    with open(path, newline="", errors="replace") as f:
        for row in csv.reader(f):
            if (row and len(row) > 4 and row[0] != "ts"
                    and not row[0].startswith("#")
                    and len(row) > 1 and row[1] == "MARK" and row[4]):
                n += 1
    return n


def probe(call, norm, path: str):
    """`call(path)` normalised by `norm`, or the exception either raised.

    The exception is the result, not a failure of the probe. The question is
    what a reader does with each shape, and "raises" is one of the answers;
    swallowing it would leave the page asserting a cost no run reproduced. The
    normaliser runs inside the same guard because a reader that returns
    something `norm` cannot take apart is a finding too, and one reported as
    `AttributeError` from here would read as the reader's own."""
    try:
        return norm(call(path))
    except Exception as e:                          # noqa: BLE001 - the
        return f"raised {type(e).__name__}: {e}"    # raise *is* the result


def section_rows(tmp: str, name: str, rows, readers) -> int:
    """Print the per-reader table for one capture family and return the number
    of readers whose result changed under either shape.

    Each reader carries its own `norm`, which is what makes the comparison
    decidable at all: every one of these embeds the capture's own path in what
    it returns, and the three captures are three temp files, so an unstripped
    comparison would report all three shapes as different and the question
    would go unasked. Normalising per reader rather than by inspecting types
    keeps the strip next to the reader whose strip it is -- a `Window`'s
    `source` and an `EarlyExit`'s are different fields, and a shared type
    switch would have to guess."""
    print(f"\n{name} capture, over {repo_path(readers[0][1])}")
    base_path = os.path.join(tmp, f"{name}-none.csv")
    write_capture(base_path, build(rows, "none"), "none")
    changed = 0
    for label, _, call, norm in readers:
        base = probe(call, norm, base_path)
        print(f"  {label}")
        for shape in SHAPES:
            path = os.path.join(tmp, f"{name}-{shape.replace(' ', '-')}.csv")
            write_capture(path, build(rows, shape), shape)
            value = probe(call, norm, path)
            differs = shape != "none" and value != base
            changed += differs
            print(f"    {shape:<16} {value}"
                  + ("   <- DIFFERS" if differs else ""))
    total = sum(1 for r in rows if len(r) > 1 and r[1] == "MARK")
    print(f"  marks carrying provenance in their own row, of {total}:")
    for shape in SHAPES:
        path = os.path.join(tmp, f"{name}-{shape.replace(' ', '-')}.csv")
        print(f"    {shape:<16} {own_provenance(path)}")
    return changed


def section_shapes(grader, timer, tmp: str) -> int:
    """The two per-shape tables. Returns the number of readers that changed
    under either shape, which is the figure the page's "zero cost" cells are
    read against.

    The reader list is built here rather than at module scope because each
    entry is a bound method of a module loaded by path at call time; a
    module-level table would have to import at import time, which is the shape
    this tool's own load-by-path rule exists to avoid.

    Each `norm` drops the capture's own path -- which is why the comparison is
    per reader rather than by type -- and drops the timestamps, which the
    probe writes identically into all three captures and so cannot be what
    distinguishes the shapes. What is left is what a reader decides on."""
    families = [
        ("0751", CONSTRUCTED_0751, [
            ("read_capture", GRADER, grader.read_capture,
             lambda v: (f"{len(v[0])} mark(s) "
                        f"{[m.label for m in v[0]]}, "
                        f"{len(v[1])} change row(s) "
                        f"{[(hex(c.addr), c.old, c.new) for c in v[1]]}")),
            ("existing_mark_labels", GRADER, grader.existing_mark_labels,
             lambda v: str([(ts, label) for ts, label in v])),
            ("read_early_exits", GRADER, grader.read_early_exits,
             lambda v: str([(str(e.ts), e.reason) for e in v])),
        ]),
        ("timer", CONSTRUCTED_TIMER, [
            # `load` takes a list of paths, and `RESUMES`/`GAPS` are module
            # globals it fills rather than fields it returns -- a reader
            # whose interesting half is invisible to a return-value
            # comparison is exactly the thing this table must not report as a
            # clean zero.
            ("grade_timer_sweep.load", TIMER, lambda p: timer.load([p]),
             lambda v: (f"{len(v[2])} change row(s) "
                        f"{[(hex(r[1]), r[2], r[3]) for r in v[2]]}, watched "
                        f"{v[0]}, span {round(v[3], 3)}, interval {v[4]}, "
                        f"{len(timer.RESUMES)} resume(s), "
                        f"{len(timer.GAPS)} gap(s)")),
        ]),
    ]
    return sum(section_rows(tmp, name, rows, readers)
               for name, rows, readers in families)


# Every site this tool's page names, as (path, line, the text that must be
# there, what it is). The text is the whole check: a line that moves is a
# mismatch whether it moved because the file grew above it or because the
# claim was wrong, and the two need a reader, not a guess.
CITATIONS = [
    # -- writers -------------------------------------------------------------
    ("windows/tools/ec_watch.py", 355,
     'self._sink.row([ts, "MARK", "", label])',
     "writer: the Marker._loop the issue's shape A is scoped to"),
    ("windows/tools/system_id_probe.py", 256,
     'self._sink.row([ts, "MARK", "", label])',
     "writer: a third class, importing no ec_watch.Marker"),
    ("ec/tools/ec_timer_capture.py", 164, 'sink.row([ts, "MARK", "", label])',
     "writer: mark_loop"),
    ("ec/tools/ec_timer_capture.py", 199,
     'sink.row([now(), "MARK", "", label])',
     "writer: auto_mark_loop, the resume branch"),
    ("ec/tools/ec_timer_capture.py", 205,
     'sink.row([now(), "MARK", "", label])',
     "writer: auto_mark_loop, the machine-state branch"),
    ("ec/tools/ec_timer_capture.py", 227,
     'sink.row([now(), "MARK", "", label])',
     "writer: input_mark_loop"),
    ("windows/tools/manual_fan_ctrl_probe.py", 438,
     'self.row([now() if ts is None else ts, "MARK", "", label])',
     "writer: MarkCsv.mark"),
    # -- readers that index the row -----------------------------------------
    # The grader's pins are the ones #749 retargets, and #749 was rebased on
    # #748, which declared utf-8 at the readers and added a leading-BOM check
    # to the row body -- so every line below is re-measured on the merged tree
    # rather than carried over from either tip. The pins in the other files are
    # #748's to move and are left where it left them (#748 records that red).
    ("ec/tools/grade_0751_isolation.py", 831, 'if addr == "MARK":',
     "reader: take_capture_row recognising the row, read_capture's own body"),
    ("ec/tools/grade_0751_isolation.py", 884, 'if addr == "MARK":',
     "reader: the partition naming the mark rows it accepted, a mark row is "
     "never hex-read"),
    ("ec/tools/grade_0751_isolation.py", 853,
     'if len(row) > 1 and row[1] == "MARK":',
     "reader: mark_labels_of recognising the row, existing_mark_labels' own "
     "extraction"),
    ("ec/tools/grade_timer_sweep.py", 134, 'if r[1] == "MARK":',
     "reader: grade_timer_sweep.load recognising the row"),
    ("windows/tools/test_manual_fan_ctrl_probe.py", 508,
     'if len(r) == 4 and r[1] == "MARK"]',
     "reader: the only exact-column-count filter in the tree"),
    # -- the spelling the literal scan cannot see ----------------------------
    ("windows/tools/test_ec_watch.py", 145,
     "('MARK', '', 'wrote 0x0751=0xA0')",
     "a single-quoted MARK the scan cannot match: a test assertion, not a "
     "writer"),
    ("windows/tools/test_system_id_probe.py", 311,
     "('MARK', '', 'GPU mode -> dGPU')",
     "the same in the other suite, so the blind side is the tree's and not "
     "one file's"),
    # -- the lines the read-side claim rests on -----------------------------
    ("ec/tools/grade_0751_isolation.py", 679, "def read_capture(path):",
     "read_capture"),
    ("ec/tools/grade_0751_isolation.py", 695,
     'if not row or row[0].startswith("#") or row[0] == "ts":',
     "read_capture's skip rule, where a `# provenance` row goes"),
    ("ec/tools/grade_0751_isolation.py", 828, "if len(row) < 4:",
     "read_capture's only length test: a fifth column passes it"),
    ("ec/tools/grade_0751_isolation.py", 830,
     "ts, addr, old, new = row[0], row[1], row[2], row[3]",
     "explicit indexing, not an unpack of row -- the correction to the issue"),
    ("ec/tools/grade_0751_isolation.py", 701,
     "def existing_mark_labels(path):", "existing_mark_labels"),
    ("ec/tools/grade_0751_isolation.py", 871,
     'if not row or row[0].startswith("#") or row[0] == "ts":',
     "mark_labels_of takes read_capture's skip rule"),
    ("ec/tools/grade_0751_isolation.py", 854,
     'out.append((row[0], row[3] if len(row) > 3 else ""))',
     "the (ts, label) pair: no position, and no fifth column either"),
    ("ec/tools/grade_0751_isolation.py", 1083, "def read_early_exits(path):",
     "read_early_exits"),
    ("ec/tools/grade_0751_isolation.py", 1110,
     "if not row or not row[0].startswith(EARLY_EXIT_TAG):",
     "the phrase test: a mark's row[0] is a timestamp"),
    ("ec/tools/grade_0751_isolation.py", 428,
     'EARLY_EXIT_TAG = "# the run ended early:"',
     "the one machine phrase the `#` namespace spends in this family"),
    ("ec/tools/grade_0751_isolation.py", 2698,
     'read = f"{path}: {len(m)} mark(s), {len(c)} change row(s)"',
     "the per-capture census line, which counts rather than spells"),
    ("ec/tools/grade_gpu_door.py", 421, "m, c = fan.read_capture(path)",
     "the second consumer of read_capture's two-tuple"),
    ("ec/tools/check_capture_claims.py", 508,
     "read_capture(os.path.join(REPO, WATCH, name))",
     "a third, and the only one that reads every committed capture"),
    ("ec/tools/grade_timer_sweep.py", 111, 'if line.startswith("#"):',
     "grade_timer_sweep drops every `#` line before the CSV parse"),
    ("ec/tools/grade_timer_sweep.py", 135, 'if "resumed" in r[3]:',
     "the one phrase grade_timer_sweep reads a MARK row for"),
    # -- the notice, the canary, and the `#` namespace -----------------------
    ("windows/tools/ec_watch.py", 254,
     "def warn_unchecked_marks(path, existing_marks):",
     "the notice the measurement exists for"),
    ("windows/tools/ec_watch.py", 280, "marks = existing_marks(path)",
     "the notice's one call into the grader's reader"),
    ("windows/tools/test_manual_fan_ctrl_probe.py", 515,
     "self.assertEqual(len(row), 4, row)",
     "the canary: the only committed assertion of an exact column count"),
    ("windows/tools/manual_fan_ctrl_probe.py", 257,
     'EARLY_EXIT_TAG = "# the run ended early:"',
     "the probe's own spelling of the same phrase"),
    ("windows/tools/manual_fan_ctrl_probe.py", 922,
     'sink.row([f"{EARLY_EXIT_TAG} {now()}",',
     "the only machine-written `#` row in the 0751 family"),
    ("ec/tools/ec_timer_capture.py", 144, 'self._fh.write(f"# {text}\\n")',
     "the timer family's `#` writer, which writes by prefix not by phrase"),
    # -- the runbook ---------------------------------------------------------
    ("docs/hardware-tests/manual-fan-ctrl-0751-isolation.md", 144,
     "--mark --label-vocab 0751 --csv",
     "§3 block 1, the console that holds the flag"),
    ("docs/hardware-tests/manual-fan-ctrl-0751-isolation.md", 146,
     "--mark --label-vocab 0751 --csv", "§3 block 2"),
    ("docs/hardware-tests/manual-fan-ctrl-0751-isolation.md", 148,
     "--mark --label-vocab 0751 --csv", "§3 block 3"),
]

# The `#` phrases a machine writes into a capture, as (path, line, phrase).
# Counted rather than asserted, because "the `#` namespace is one phrase" is a
# claim about a moving tree and the answer differs per family: the 0751
# family has one, and the timer family already has a writer that emits any
# prefix at all.
COMMENT_PHRASES = [
    ("windows/tools/manual_fan_ctrl_probe.py", 257,
     "# the run ended early:"),
    ("ec/tools/ec_timer_capture.py", 291, "ec/tools/ec_timer_capture.py, "
     "read-only, ECMG window "),
    ("ec/tools/ec_timer_capture.py", 293, "started "),
    ("ec/tools/ec_timer_capture.py", 294, "power: "),
    ("ec/tools/ec_timer_capture.py", 295, "interval "),
    ("ec/tools/ec_timer_capture.py", 298, "note: "),
    ("ec/tools/ec_timer_capture.py", 301, "baseline "),
    ("ec/tools/ec_timer_capture.py", 307, "auto-mark state at start: "),
    ("ec/tools/ec_timer_capture.py", 337, "ended "),
]


def check_citations(scan: set) -> list:
    """Every citation's problems: a line whose text has drifted, a row site
    the scan found and no citation names, and a row citation the scan no
    longer finds. Loud rather than quiet in all three, because each is a fact
    the page's prose rests on."""
    problems = []
    named = set()
    for path, lineno, want, what in CITATIONS:
        full = os.path.join(REPO, path)
        got = line_of(full, lineno).strip()
        if want not in got:
            problems.append(f"{path}:{lineno} ({what}): the page quotes "
                            f"{want!r} and the line reads {got!r} -- the line "
                            "moved or the claim is wrong")
        if ROW_LITERAL in want:
            named.add((path, lineno))
    for path, lineno in sorted(scan - named):
        problems.append(f"{path}:{lineno}: a `ts,MARK,,label` site no citation "
                        "names, so the page's census is a hand-typed list and "
                        "not this scan")
    for path, lineno in sorted(named - scan):
        problems.append(f"{path}:{lineno}: cited as a `ts,MARK,,label` site, "
                        "and the scan no longer finds one there")
    return problems


def check_page(path: str) -> list:
    """Whether the page names every citation this tool prints.

    The closure that makes the page checkable: a `file:line` in it that the
    tool did not print, or one the tool stopped printing, is a figure nobody
    can re-derive -- which is the whole reason the measurement is a tool
    rather than a paragraph."""
    if not os.path.isfile(path):
        return [f"{repo_path(path)}: not there, so nothing in it can be "
                "checked against this tool's output"]
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return [f"{p}:{n}: cited here and not named in {repo_path(path)}"
            for p, n, _, _ in CITATIONS if f"{p}:{n}" not in text]


def section_comment_namespace() -> None:
    """The machine-written `#` phrases, per file, and how a reader treats
    them. This is section 4 and it is short on purpose: one shape's cost is
    what it takes from a namespace, and the answer is a count."""
    for path, lineno, phrase in COMMENT_PHRASES:
        got = line_of(os.path.join(REPO, path), lineno)
        ok = phrase in got
        print(f"  {path}:{lineno}  {'ok ' if ok else 'DRIFT'}  {phrase!r}")


def self_test() -> int:
    """The measurement run over a temp tree, checked rather than printed.

    What makes the page's "zero cost" cells checkable: each reader is asserted
    to come back exactly as it does on the base under both shapes, and to
    raise where the page says it does not -- `read_capture` on a short row is
    the one raise the table records, and it is checked here so the sentence
    that says the fifth column does *not* raise cannot go stale into the
    opposite claim."""
    grader = load_module("grade_0751_isolation", GRADER)
    timer = load_module("grade_timer_sweep", TIMER)
    print("self-test: the measurement below, checked rather than read. Every "
          "line it\n  prints is the thing being asserted, so a failure names "
          "the cell it contradicts.")
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        changed = section_shapes(grader, timer, tmp)
        if changed:
            problems.append(f"{changed} reader(s) changed under a shape; the "
                            "page's per-reader table says none do")
        # The other direction, and the one the table's read_capture row turns
        # on: a row one column short still raises, so `:689` is a real test
        # and not a threshold a fifth column would move. Three fields, not
        # four -- `MARK,,x` is four and is a row `read_capture` is meant to
        # take, so the first version of this line asserted the opposite of
        # what it meant to and the check passed for the wrong reason.
        short = os.path.join(tmp, "short.csv")
        with open(short, "w", newline="") as f:
            f.write("ts,addr,old,new\n"
                    "2026-01-01T12:00:02.000+01:00,MARK,settled\n")
        try:
            grader.read_capture(short)
            problems.append("read_capture accepted a 3-column MARK row; "
                            "`:689` is not the test the page describes")
        except ValueError:
            pass
        try:
            grader.read_capture(os.path.join(tmp, "0751-fifth-column.csv"))
        except Exception as e:                      # noqa: BLE001
            problems.append(f"read_capture raised on a 5-column MARK row: {e}")
        # A provenance comment row is skipped by the preflight, so the notice
        # reads the same for a file whose marks carry provenance by position
        # and one whose marks carry none -- which is the backward-
        # compatibility case stated as an assertion.
        base = grader.existing_mark_labels(os.path.join(tmp, "0751-none.csv"))
        for shape in ("fifth-column", "provenance-row"):
            got = grader.existing_mark_labels(
                os.path.join(tmp, f"0751-{shape}.csv"))
            if got != base:
                problems.append(f"existing_mark_labels differs under {shape}: "
                                f"{got} against {base}")
        # And the empty-column third state, which is the one a 4-column row
        # must never be read as.
        empty = os.path.join(tmp, "empty-column.csv")
        with open(empty, "w", newline="") as f:
            f.write("ts,addr,old,new\n"
                    "2026-01-01T12:00:10.000+01:00,MARK,,settled,\n")
        if grader.existing_mark_labels(empty) != [
                ("2026-01-01T12:00:10.000+01:00", "settled")]:
            problems.append("an empty fifth column does not come back as "
                            "('ts', label); the three-state claim is stale")
    for problem in problems:
        print(f"measure_mark_provenance.py: {problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} self-test failure(s)", file=sys.stderr)
        return 1
    print("self-test passed: no reader's result differs under either shape, "
          "and the two raising cases still raise.\n"
          "  No EC was opened, no capture was taken, no register was read:\n"
          "  every reader above ran over a temp file this tool wrote.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--page", default=PAGE,
                    help=f"the findings page to hold to this tool's output "
                         f"(default: {repo_path(PAGE)})")
    ap.add_argument("--self-test", action="store_true",
                    help="run the measurement over a temp tree and check it "
                         "rather than print it")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()

    grader = load_module("grade_0751_isolation", GRADER)
    timer = load_module("grade_timer_sweep", TIMER)
    writers, readers = row_sites()

    print("1. The row's census, found by scanning for the \"MARK\" literal")
    print(f"   {len(writers)} writer(s) of ts,MARK,,label:")
    for path, lineno, text in writers:
        print(f"     {path}:{lineno}  {text}")
    print(f"   {len(readers)} site(s) consuming it:")
    for path, lineno, text in readers:
        print(f"     {path}:{lineno}  {text}")
    calls, in_tests = reader_call_sites()
    print(f"   {len(calls)} call(s) of the grader's readers, none of which "
          f"writes the literal:")
    for path, lineno, text in calls:
        print(f"     {path}:{lineno}  {text}")
    print(f"   {in_tests} further call(s) inside `test_*.py` suites, counted "
          "and not listed.")

    census = fixture_census()
    marks = sum(c[1] for c in census)
    cols = sorted({n for c in census for n in c[2]})
    print(f"\n2. The committed fixtures holding a MARK row, under "
          f"{' and '.join(repo_path(r) for r in FIXTURE_ROOTS)}")
    print(f"   {len(census)} file(s), {marks} MARK row(s), column counts "
          f"{cols or 'none'}; header present in "
          f"{sum(1 for c in census if c[3])}, `#` rows present in "
          f"{sum(1 for c in census if c[4])}")
    for root in FIXTURE_ROOTS:
        under = [c for c in census if c[0].startswith(repo_path(root) + os.sep)]
        print(f"     {repo_path(root)}: {len(under)} file(s), "
              f"{sum(c[1] for c in under)} MARK row(s)")
    print("   a file a shape leaves untouched is one whose MARK rows keep the "
          "column counts above and whose `#` rows stay the skip rule's own")

    print("\n3. What each shape costs each reader, on a temp file")
    with tempfile.TemporaryDirectory() as tmp:
        section_shapes(grader, timer, tmp)

    print("\n4. The machine-written `#` phrases already in each family")
    section_comment_namespace()
    print("   read_capture and existing_mark_labels skip every `#` row; "
          "read_early_exits and\n   grade_timer_sweep.load match named phrases "
          "only, so an unclaimed prefix costs\n   nothing to read and one new "
          "phrase is a second entry in a namespace two\n   of these already "
          "share.")

    print("\n5. The citations")
    scan = {(p, n) for p, n, _ in writers + readers}
    problems = check_citations(scan)
    for path, lineno, want, what in CITATIONS:
        ok = want in line_of(os.path.join(REPO, path), lineno).strip()
        print(f"   {'ok ' if ok else 'DRIFT'}  {path}:{lineno}  {what}")
    for problem in problems:
        print(f"   {problem}")
    page_problems = check_page(args.page)
    for problem in page_problems:
        print(f"   {problem}")
    problems += page_problems
    if problems:
        print(f"   {len(problems)} citation problem(s)", file=sys.stderr)
        return 1
    print(f"   {len(CITATIONS)} citations resolve at the line quoted, the "
          f"row-site join closes both ways,\n   and {repo_path(args.page)} "
          "names every one of them.")
    print("\nNothing here is hardware evidence: no EC was opened, no capture "
          "was taken, no\nregister was read and no mark was typed. Section 2 "
          "is a count over two committed\ndirectories; section 3 is a reader's "
          "behaviour on a file this tool wrote.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
