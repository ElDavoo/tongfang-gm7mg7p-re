#!/usr/bin/env python3
"""Measure the capture format's encoding against the captures on disk.

The `ts,addr,old,new` format now *declares* `utf-8` at every reader and every
writer of it, which is the decision `docs/findings/0751-capture-encoding.md`
records and argues. This is what re-derives the numbers that decision rests on,
so none of them is a hand-typed claim in prose: the corpus is walked, each
capture is read twice -- once through the declared codec and once through the
locale default the readers used before -- and the two are compared.

**The load-bearing result.** The 36 captures carrying high bytes have to come
out of the declared reader byte for byte as they did out of the old one. The
declaration changes what the format *means*; it must not change what those
files *contain*, and this is the check that would say so if it did. A capture
that parsed before and does not parse now is the failure this exists to catch,
and it is reported by name rather than as a tally.

The writer half is the other direction, and it is the half the reader half
cannot reach: a `§` mark is round-tripped through each of the five writer
classes and the bytes are read back off disk. Before the declaration those bytes
were whatever the writing process's locale preferred, so the round-trip is the
only way to show the codec on disk is the declared one rather than the
interpreter's. It is a round-trip through a temp directory, not a capture, and
it writes nothing into the tree.

What this does not do:

  * *Open a capture on a Windows box, or reach the EC.* Nothing here runs
    anywhere but this checkout. The claim that a stock Windows Python would
    have written `§` as a single 0xA7 stays a prediction from the documented
    default; nothing here confirms or refutes it, and the round-trip does not
    stand in for having done so.
  * *Check that a writer class declares the codec*, only that it puts the
    declared bytes on disk. The declarations themselves are in the diff, and
    `grep` reads them; what this checks is the consequence.
  * *Depend on `measure_mark_provenance.py`.* That tool's citation check
    crashes on a tuple of the wrong length (`:601`) and is red on `main` for
    reasons that have nothing to do with encoding, so nothing here imports it
    -- a measurement that cannot run is not a control.
"""

import argparse
import csv
import importlib.util
import io
import os
import re
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)

# The two corpora, walked in that order. `ec/tools/testdata/` is the fixture
# tree the grader's own suite runs against; `evidence/ec-watch/` is a finished
# run committed as the file it was captured to, which is the other way a
# capture reaches a reader.
ROOTS = (
    os.path.join(HERE, "testdata"),
    os.path.join(REPO, "evidence", "ec-watch"),
)

DECLARED = "utf-8"

# The five writer classes of this shape, as (repo-relative path, class name).
# Four of them are named as writers of the `ts,addr,old,new` capture and one
# (`ec_timer_capture.Sink`) is a fifth that writes the same shape by its own
# docstring; `check_capture_claims` and `grade_timer_sweep.load` are readers of
# it rather than writers and are not in this table.
WRITERS = (
    ("windows/tools/ec_watch.py", "CsvSink"),
    ("windows/tools/system_id_probe.py", "CsvSink"),
    ("windows/tools/ec_validate.py", "SampleCsv"),
    ("windows/tools/manual_fan_ctrl_probe.py", "MarkCsv"),
    ("ec/tools/ec_timer_capture.py", "Sink"),
)

# `§` is the byte this is about, and not an arbitrary one: a mark label is free
# text and the whole vocabulary is named after §3 and §6, so `§` in a label is
# the likeliest non-ASCII character an operator types at the box.
PROBE = "§3 block 2"


def _stub(name, source):
    """A stand-in for a Windows-only sibling import, with the names it imports.

    All four of the Windows writers do `from ecrw import ...` at module scope,
    and `ecrw.py` calls `ctypes.WinDLL("kernel32")` at module scope, so none of
    them can be imported on a Linux runner at all -- the tool would be
    unrunnable here rather than wrong, and the writer half of this check would
    have no answer to give. The names are read out of the writer's own import
    line rather than listed here, so a writer that starts importing a fourth
    name does not need this file edited to stay loadable.

    What this does and does not buy: the class under test is the writer's real
    source, executing its real `open()` call, and the bytes checked are the
    bytes it wrote. It is *not* a Windows run -- no EC and no box is reachable
    from here, and the `ctypes` call the stub stands in for is precisely the
    part that cannot be. A codec is a property of the Python that writes, and
    that is what is under test.
    """
    stub = types.ModuleType(name)
    for line in source.split("\n"):
        m = re.match(rf"from {name} import (.+)$", line.strip())
        if m:
            for attr in m.group(1).split(","):
                setattr(stub, attr.strip(), _Unusable)
    return stub


class _Unusable:
    """Stands in for a name no writer class under test ever calls."""

    def __init__(self, *a, **k):
        raise AssertionError("a Windows-only driver call reached the writer "
                             "half of this check, which is not what it runs")


def load(path):
    """One repo-relative module by path, as `ec_watch.py` loads the grader.

    By path rather than by import because the Windows tools are deployed as a
    directory rather than as a package, and importing them by module name here
    would be testing an arrangement none of them is run under. That deployment
    is also why the module's own directory goes on `sys.path` for the load:
    `ec_watch.py` does `from ecrw import Ec`, and ecrw is a sibling file, not a
    package member -- exactly as it resolves when the tool is run from the
    directory it was copied to.
    """
    full = os.path.join(REPO, path)
    name = os.path.basename(path)[:-len(".py")]
    here = os.path.dirname(full)
    source = open(full, encoding="utf-8").read()
    stubbed = None
    for sibling in re.findall(r"^from (ecrw|ecmem) import ", source, re.M):
        if sibling not in sys.modules:
            stubbed = sys.modules[sibling] = _stub(sibling, source)
    sys.path.insert(0, here)
    try:
        spec = importlib.util.spec_from_file_location(f"_enc_{name}", full)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(here)
        if stubbed is not None:
            del sys.modules[stubbed.__name__]
    return module


def count(path, encoding):
    """(marks, change rows) from one capture read under `encoding`.

    `read_capture`'s own rules, applied in a few lines rather than by calling
    it: this has to read the *same file* under two different codecs, and the
    declared one is the argument rather than a fact baked into the function.
    A `#` or blank row and the `ts` header are skipped the way the grader
    skips them, so the two counts are the grader's rows and not a tally of
    lines.
    """
    marks = changes = 0
    with open(path, newline="", encoding=encoding) as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0] == "ts":
                continue
            if len(row) > 1 and row[1] == "MARK":
                marks += 1
            else:
                changes += 1
    return marks, changes


def classify(raw):
    """(has a BOM, has a high byte, decodes as the declared encoding)."""
    return (raw.startswith(b"\xef\xbb\xbf"),
            any(b > 0x7F for b in raw),
            _decodes(raw, DECLARED))


def _decodes(raw, encoding):
    try:
        raw.decode(encoding)
        return True
    except UnicodeDecodeError:
        return False


def walk_captures():
    """(path, byte count, BOM, high byte, decodes, marks, changes, agrees).

    `agrees` is the load-bearing column: the declared read and the locale-
    default read, compared on what came out of them. A file that both readers
    accept and both agree on is a file the declaration changed nothing about.
    """
    for root in ROOTS:
        for base, _, names in os.walk(root):
            for name in sorted(names):
                if not name.endswith(".csv"):
                    continue
                path = os.path.join(base, name)
                raw = open(path, "rb").read()
                bom, high, decodes = classify(raw)
                locale = _preferred_encoding()
                try:
                    declared = count(path, DECLARED)
                    inherited = count(path, locale)
                    agree = declared == inherited
                except UnicodeDecodeError:
                    # Only reachable when the *locale* read is the stricter
                    # one, which a UTF-8 locale cannot do for a utf-8-decodable
                    # file. Reported rather than swallowed, because a corpus
                    # file this cannot compare is a gap in the check.
                    declared = inherited = None
                    agree = False
                yield (os.path.relpath(path, REPO), len(raw), bom, high,
                       decodes, declared, inherited, agree)


def _preferred_encoding():
    """The encoding an `open()` with no `encoding=` uses on this interpreter.

    Locale-dependent by definition -- that is the whole of what the declaration
    removes -- so it is read from a throwaway `open` rather than from
    `locale.getpreferredencoding`, which is not always the same answer CPython
    applies when it opens a file.
    """
    with tempfile.TemporaryFile("w") as f:
        return f.encoding


def round_trip(path, cls, tmp):
    """The bytes one writer class puts on disk for a `§` mark.

    Returns the raw file, so the caller can decode it under the declared codec
    and be looking at what actually landed rather than at what the class was
    asked to write. The label is written through the class's own `row` where
    it has one, because `MarkCsv.mark` and `Sink.row` differ in how they stamp
    a timestamp and the point here is the codec, not the stamping.
    """
    module = load(path)
    sink = getattr(module, cls)(os.path.join(tmp, f"{cls}.csv"))
    try:
        row = ["2026-01-01T12:00:00.000+01:00", "MARK", "", PROBE]
        try:
            sink.mark(PROBE)  # MarkCsv writes the shape from a label alone.
        except AttributeError:
            sink.row(row)  # The rest take the row.
    finally:
        sink.close()
    return open(os.path.join(tmp, f"{cls}.csv"), "rb").read()


def report(captures, writers):
    """Print both halves. Returns the problems found, which is the exit code."""
    problems = []

    print("== the committed corpus, read two ways ==\n")
    print(f"{'file':<62} {'bytes':>6} {'BOM':>4} {'hi':>3} "
          f"{'marks':>6} {'changes':>8} {'agrees':>7}")
    high = boms = total = 0
    for path, size, bom, is_high, decodes, declared, inherited, agree in captures:
        total += 1
        high += bool(is_high)
        boms += bool(bom)
        counts = (f"{declared[0]:>6} {declared[1]:>8}"
                  if declared else f"{'--':>6} {'--':>8}")
        print(f"{path:<62} {size:>6} {'yes' if bom else '-':>4} "
              f"{'yes' if is_high else '-':>3} {counts} "
              f"{'yes' if agree else 'NO':>7}")
        if not decodes:
            # Not a disagreement but the stronger thing: the declared reader
            # refuses this file outright, so it does not grade at all. Which
            # is what the declaration is *for*, and the reason this corpus
            # reading clean is the result worth having.
            problems.append(f"{path} is not {DECLARED}-decodable, so the "
                            f"declared reader refuses it; a capture is defined "
                            f"to be {DECLARED}")
        if bom:
            problems.append(f"{path} carries a BOM; the format is {DECLARED} "
                            f"with no BOM")
        elif decodes and not agree:
            problems.append(f"{path}: the declared read and the "
                            f"locale-default read disagree ({declared} against "
                            f"{inherited}), so the declaration changed what "
                            f"this file grades as")
    locale = _preferred_encoding()
    print(f"\n{total} capture(s), {high} with a high byte, {boms} with a BOM; "
          f"each read under the declared {DECLARED} and under this "
          f"interpreter's default ({locale}), and the two compared")
    if locale.lower().replace("_", "-") == DECLARED:
        # True here, and the reason the `agrees` column is not the whole
        # result: on a UTF-8 runner the two reads are the same read, so the
        # column is trivially `yes` and what it is really showing is that
        # every file *decodes*. That is the claim worth making -- the corpus
        # is utf-8, so declaring utf-8 admits all of it and refuses none.
        print(f"  note: this runner's default is already {DECLARED}, so the two "
              f"reads are the same read here. The agreement is therefore weak "
              f"evidence on this machine and the strong claim is that all "
              f"{total} decode as {DECLARED} -- which is what a declaration of "
              f"any other codec would have broken.")

    print("\n== a § mark through each writer class ==\n")
    for path, cls in WRITERS:
        with tempfile.TemporaryDirectory() as tmp:
            raw = round_trip(path, cls, tmp)
        try:
            text = raw.decode(DECLARED)
        except UnicodeDecodeError as e:
            problems.append(f"{path}:{cls} put bytes on disk that are not "
                            f"{DECLARED}: {e}")
            print(f"{path:<44} {cls:<10} NOT {DECLARED}")
            continue
        landed = "yes" if PROBE in text else "NO"
        bom = "yes" if raw.startswith(b"\xef\xbb\xbf") else "no"
        print(f"{path:<44} {cls:<10} {len(raw):>4}B  {PROBE!r} landed: "
              f"{landed:<4}  BOM: {bom}")
        if PROBE not in text:
            problems.append(f"{path}:{cls} did not write the probe label "
                            f"under {DECLARED}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true",
                    help="print only the problems, not the per-file table")
    args = ap.parse_args()

    if args.quiet:
        out = sys.stdout
        sys.stdout = io.StringIO()
    try:
        problems = report(list(walk_captures()), WRITERS)
    finally:
        if args.quiet:
            sys.stdout = out

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(f"  {p}")
        return 1
    print("\nok: every committed capture reads the same under the declared "
          "codec as under the locale default, and every writer class puts the "
          "declared codec on disk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
