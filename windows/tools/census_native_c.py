#!/usr/bin/env python3
"""Census the committed native `.c` exports: what each one declares, and which
binary it belongs to.

`windows/ghidra/c-digests.csv` (the #346 layer) says a `.c` has not moved. This
says what is *in* it. The two are different claims and neither substitutes for
the other: a digest cannot be read as a function count, and a census cannot
tell you the file is the export it claims to be.

Why it exists. `GamingCenter3_Cross.c` is 56 MB and 64,588 `// ==== ` lines,
and it is named in no index, no listing and no manifest figure -- its manifest
row is `0,0,0,0,0,not-in-project` because the program is deliberately not in the
committed Ghidra project (a 337 MB buffer file is over GitHub's 100 MB
per-file limit). So the largest artefact in the Windows stack was in no
inventory at all, and a committed CSV sat next to a committed artefact
saying opposite things about it. This is the inventory.

Two things are measured, and they are not the same measurement:

* **What the file declares.** `separators_declared`, `first_addr` and
  `last_addr` are read off the `.c` with `decompile_native._c_markers()` --
  imported, not copied, so the separator grammar is one definition in this
  repository. A separator count is the *decompiled* count: a function that
  fails to decompile emits no separator, so 64,588 declared is 64,588 bodies
  present, not 64,588 functions found.

* **What the manifest recorded.** `project_functions`, `project_decompiled` and
  `project_failed` are copied from `manifest.csv` and asserted against it, so
  the zeros in a `not-in-project` row sit beside a real number instead of
  being the only number. `count_basis` names which of the two a row's count is:
  `measured` where the manifest's total and the file's separators agree, and
  `carried-from-run` where the program is not in the project and the run's own
  function/failed totals cannot be re-derived from the text at all. The tool
  never infers one from the other, and never writes `separators + failed`.

**Which binary, and on what ground.** The binary comes from
`decompile_native.export_label()` applied to the committed target list, which
names exactly one binary per export label. The `.c` header then corroborates it
on a second, independent ground: the `// Source:` provenance line is the *run's
target list*, not per-file provenance, and it pairs each source path with that
input's digest **positionally**. So the pair whose path names the binary is the
binary's digest. On the five projects already in the project those digests are
in the manifest already; for `GamingCenter3_Cross.dll` they are not -- its
manifest row carries an empty `sha256` and `native-binaries.csv` carries
`runtime` for it -- so `binary_sha256` here is the only committed record of
that binary's digest *outside* the retained export's own `// Source:` header,
which is where it is copied from, and the only one in a structured file another
tool can read without parsing 56 MB of C.

A header pair that resolves to no binary, or to more than one, is **refused,
not guessed**. So is a `.c` that is missing, empty, or declares no separator, and
the refusal names the file: a census that silently covered less must not be
readable as a census that is clean.

**What the address range is and is not.** `first_addr`/`last_addr` also read as
a range, and it is tempting to attribute by them. They cannot do that here, and
the tool does not pretend otherwise. `ACPIDriverDll.dll`, `UEFI_Firmware.dll`
and `clrcompression.dll` are all PE32+ at image base `0x180000000` and their
ranges overlap each other, so a range resolves *this* file only because
`GamingCenter3_Cross`'s `0x180DE2000`-`0x1818D1B40` happens to be disjoint from
all of them. `disjoint_exports()` reports the exports a range really can
resolve and every run prints how many that is; it is a second opinion on one
row, not a mechanism, and the header pairing is what does the work.

Needs no Ghidra, no network, no project and no vendor binary. Every file it
opens is committed: the `.c` exports under `decompiled/native/`, and three CSVs
under `ghidra/` -- `c-census.csv` (what it is checking), `manifest.csv` (the
`project_*` columns) and `native-binaries.csv` (the target list
`load_targets()` reads). Each `.c` is read ONCE (the header comes from a 8 KB
prefix of the same file, not a second pass over 56 MB), which is the §14a lesson
`c_presence_problems()` already learned the expensive way.

Usage:
    python3 windows/tools/census_native_c.py                    print the table
    python3 windows/tools/census_native_c.py --check            committed CSV is current
    python3 windows/tools/census_native_c.py --write            regenerate the CSV
    python3 windows/tools/census_native_c.py --self-test        known answers, fixtures
"""
import argparse
import csv
import io
import os
import re
import sys

from decompile_native import (  # imported, not copied: one separator grammar
    C_CENSUS,
    DECOMPILED_DIR,
    PROJECT_EXCLUDED,
    _c_markers,
    committed_c_files,
    export_label,
    load_targets,
    retained_decompilations,
)

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOWS_DIR = os.path.dirname(HERE)
REPO = os.path.dirname(WINDOWS_DIR)
MANIFEST_CSV = os.path.join(WINDOWS_DIR, "ghidra", "manifest.csv")

CENSUS_COLUMNS = [
    "path", "export_label", "binary", "binary_sha256", "source",
    "separators_declared", "first_addr", "last_addr", "in_project",
    "project_functions", "project_decompiled", "project_failed", "count_basis",
]

# What `count_basis` may say, and why the vocabulary is data rather than a
# string built at the call site.
#
#   measured          the file's separator count and the manifest's function
#                     total are the same quantity for this row, so the row is a
#                     measurement with a manifest beside it.
#   carried-from-run  the program is not in the committed project. The manifest
#                     records zeros because it has no run-produced row to
#                     record, and the run's own function/failed totals cannot be
#                     recovered from the text -- a function that failed to
#                     decompile emits no separator. So only `separators_declared`
#                     is a measurement here, and the row says so rather than
#                     inviting a reader to add the two columns up.
COUNT_BASES = ("measured", "carried-from-run")

# The provenance line the shared exporter writes, and how far in to look for
# it. 8 KB because the header is four to six comment lines and the longest
# `source=` list in this tree is five paths; reading the first 8 KB of a 56 MB
# file is a prefix, not a second pass, and that distinction is the whole reason
# this is a constant rather than a re-read.
_HEADER_PREFIX = 8192
_SOURCE_LINE = re.compile(r"^// Source: (.*), SHA-256 (.*)$", re.M)


def read_header_pairs(path):
    """The `// Source:` line's `[(source, sha256)]`, paired positionally, or
    None when the file has no such line.

    Positional because that is how the exporter writes it -- one joined
    `source=` list and one joined `sha256=` list, in the same target order -- so
    a line whose two lists are different lengths is a line this tool does not
    understand, and a mismatched pairing would attribute a digest to the wrong
    binary without anything looking wrong. Refused rather than repaired.
    """
    try:
        with open(path, errors="replace") as f:
            head = f.read(_HEADER_PREFIX)
    except OSError:
        return None
    m = _SOURCE_LINE.search(head)
    if not m:
        return None
    sources = [s.strip() for s in m.group(1).split(",")]
    digests = [d.strip() for d in m.group(2).split(",")]
    # An empty cell counts as absent. The regex is happy with a trailing
    # `, SHA-256 ` and nothing after it, and one blank digest would otherwise
    # be recorded as this binary's SHA-256 -- a digest column that reads as a
    # hash and is not one is worse than no column.
    if not sources or len(sources) != len(digests) or not all(digests):
        return None
    return list(zip(sources, digests))


def binary_of_source(source):
    """The file name a `// Source:` path names.

    `extract:` prefixes the archive the bytes came out of and `#` separates that
    from the member path inside it, so both are turned into separators before
    the basename is taken. Neither appears in a real file name, and without the
    substitution a source ending in a fragment rather than a path would resolve
    to no binary at all -- a refusal, which is the safe direction but the wrong
    one.
    """
    return os.path.basename(source.replace("#", "/"))


def header_attribution(pairs, binary):
    """`(source, sha256)` for `binary` from the header's pairs, or None.

    None means the header does not name that binary -- zero matching pairs, or
    more than one, which is equally unusable. Returning None rather than a
    guess is the point: this is the ground that decides which of the two
    same-stem binaries a 64,588-row export belongs to, and a wrong answer here
    would be a confident provenance claim for the largest artefact in the
    Windows stack.
    """
    hits = [p for p in (pairs or ()) if binary_of_source(p[0]) == binary]
    return hits[0] if len(hits) == 1 else None


def resolve_binary(label, targets):
    """The one committed target whose export label is `label`, or None.

    The same derivation the rest of the Windows tooling already uses -- the
    exporter keys its index on the label and `export_label()` maps a binary to
    it, and it exists because `GamingCenter3_Cross.exe` and
    `GamingCenter3_Cross.dll` share a file stem. It is exact for all six
    committed exports; a label that matches none, or more than one, is None,
    because a label naming two binaries is exactly the collision the exporter
    refuses with `EXPORT LABEL COLLISION`.
    """
    hits = [t["binary"] for t in targets
            if export_label(os.path.basename(t["binary"])) == label]
    return hits[0] if len(hits) == 1 else None


def measure_export(path):
    """`(separators, first_addr, last_addr)` for one `.c`, or None.

    `separators` counts separator *lines*, which is what `grep -c '^// ==== '`
    gives and therefore what a reader can re-derive; it is summed from the
    per-address name sets rather than counted from a second read, so the two
    can never come from different passes over the file. A duplicate address
    declared under two names therefore counts 2 here and contributes 1 to
    `first_addr`/`last_addr`'s key space -- which is the shape
    `_c_markers()`'s set-of-names was built to keep visible rather than
    silently collapse.

    Addresses are ordered as integers, not as the uppercase hex the file
    spells them in: string order is right only while every address in one image
    has the same width, and a sort that is accidentally right is the kind that
    stops being right on the next binary.
    """
    by_addr = _c_markers(path)
    if not by_addr:
        return None
    ordered = sorted(by_addr, key=lambda a: int(a, 16))
    return sum(len(names) for names in by_addr.values()), ordered[0], ordered[-1]


def disjoint_exports(measured):
    """The export labels whose address range overlaps no other export's.

    A second opinion, on one row, and deliberately not the attribution
    mechanism. `ACPIDriverDll.dll`, `UEFI_Firmware.dll`, `clrcompression.dll`
    and `GC3_launcher` share image base `0x180000000` and overlap each other, so
    on the committed tree this returns just two of the six --
    `GamingCenter3_Cross`, and `ACPIDriver`, which is PE32 at `0x140000000` and
    so overlaps none of them. That is the honest reading, and the reason the
    header pairing is what decides the binary. Returning the names rather than
    a count is so that a run which suddenly resolves one of the overlapping ones
    says which.
    """
    ranges = {}
    for label, (_n, lo, hi) in measured.items():
        if lo is None or hi is None:
            continue
        ranges[label] = (int(lo, 16), int(hi, 16))
    return {label for label, (lo, hi) in ranges.items()
            if not any(other is not label and lo <= hi_o and lo_o <= hi
                       for other, (lo_o, hi_o) in ranges.items())}


def build_rows(decompiled_dir=DECOMPILED_DIR, manifest_path=MANIFEST_CSV):
    """`([rows], [refusals])` -- the census as it would be written, and every
    reason a file could not be measured or a binary could not be attributed.

    Two lists rather than one because a refusal must be loud and must name the
    file. A row quietly dropped for an unreadable export is a census that
    reports clean having covered less, which is the one failure mode this whole
    exercise exists to stop: the manifest said `0` and nothing said otherwise.
    """
    targets = load_targets()
    manifest = {}
    if os.path.isfile(manifest_path):
        with open(manifest_path, newline="") as f:
            for r in csv.DictReader(f):
                manifest[r.get("program")] = r
    retained = retained_decompilations()
    # `retained_decompilations()` names the FILES it retained, because that is
    # what the driver's own checks compare against; the label here has no `.c`.
    # Comparing the two directly is a test that is False for every export on
    # every tree, which is the kind of guard that looks like coverage and is
    # not: the exclusion would then be carried by the manifest's `mode` alone,
    # and a retained program whose row ever read a project mode would be
    # labelled `measured` off a count the project never produced.
    retained_labels = {name[:-2] for name in retained}

    rows, refusals = [], []
    for abs_path, rel in committed_c_files(decompiled_dir):
        label = os.path.basename(abs_path)[:-2]
        measured = measure_export(abs_path)
        if measured is None:
            refusals.append("%s: missing, empty, or carrying no `// ==== "
                            "<name> @ <addr>` separator, so there is nothing to "
                            "census" % rel)
            continue
        separators, first, last = measured

        binary = resolve_binary(label, targets)
        if binary is None:
            refusals.append("%s: export label %r matches no committed target "
                            "exactly once, so no binary can be named for it"
                            % (rel, label))
            continue

        pairs = read_header_pairs(abs_path)
        hit = header_attribution(pairs, binary)
        if hit is None:
            refusals.append("%s: the `// Source:` header names %s %d time(s) or "
                            "not at all, so the run's provenance cannot confirm "
                            "the binary. Refused rather than guessed."
                            % (rel, binary,
                               len([p for p in (pairs or ())
                                    if binary_of_source(p[0]) == binary])))
            continue
        header_source, header_sha = hit

        target = next((t for t in targets
                       if os.path.basename(t["binary"]) == binary), None)
        source = target["source"] if target else header_source
        if header_source != source:
            refusals.append("%s: the header says %s came from %r and "
                            "native-binaries.csv says %r; two committed files "
                            "disagree about the same binary"
                            % (rel, binary, header_source, source))
            continue

        mrow = manifest.get(binary, {})
        mode = (mrow.get("mode") or "").strip()
        if not mode:
            refusals.append("%s: no manifest row for %s, so its project figures "
                            "cannot be carried beside the measurement"
                            % (rel, binary))
            continue
        in_project = "no" if mode == "not-in-project" else "yes"
        try:
            project = tuple(str(int(mrow.get(col) or 0))
                            for col in ("functions", "decompiled", "failed"))
        except ValueError:
            refusals.append("%s: manifest row for %s has a non-numeric count "
                            "(functions=%r decompiled=%r failed=%r)"
                            % (rel, binary, mrow.get("functions"),
                               mrow.get("decompiled"), mrow.get("failed")))
            continue

        # The row's count basis, decided by whether the manifest's own total and
        # the file's separators are the same quantity -- not by whether the
        # program happens to be excluded, because a `not-in-project` row whose
        # manifest total happened to match would be a coincidence and a
        # `measured` label would launder it into a fact.
        carried = label in retained_labels or mode == "not-in-project"
        basis = "carried-from-run" if carried else "measured"
        if not carried and project[0] != str(separators):
            refusals.append("%s: in-project, but the manifest records %s "
                            "function(s) for %s and the file declares %s "
                            "separator(s), so this row is not a measurement of a "
                            "whole-program export"
                            % (rel, project[0], binary, separators))
            continue

        rows.append({
            "path": rel,
            "export_label": label,
            "binary": binary,
            "binary_sha256": header_sha,
            "source": source,
            "separators_declared": str(separators),
            "first_addr": first,
            "last_addr": last,
            "in_project": in_project,
            "project_functions": project[0],
            "project_decompiled": project[1],
            "project_failed": project[2],
            "count_basis": basis,
        })
    return rows, refusals


def render_csv(rows):
    """The census as bytes, so `--check` compares a file rather than a parse of
    one and a quoting difference cannot pass unnoticed."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CENSUS_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def read_census(path):
    """Committed rows, read strictly, or None when the file is not there.

    Strict for the same reason `read_index()` is: csv's default reader ends a
    row early on a bad quote instead of raising, the row comes back short, and
    every count taken from it is then quietly smaller than the file.
    """
    if not os.path.isfile(path):
        return None
    with open(path, newline="") as f:
        reader = csv.reader(f, strict=True)
        try:
            header = next(reader)
        except StopIteration:
            return []
        if header != CENSUS_COLUMNS:
            return []
        return list(csv.DictReader(f, fieldnames=CENSUS_COLUMNS, strict=True))


def census_problems(path=C_CENSUS, decompiled_dir=DECOMPILED_DIR,
                    manifest_path=MANIFEST_CSV):
    """Whether `path` is what this tool derives from `decompiled_dir` right now.

    Named invariants first and the re-derivation second, in that order, so a
    failure says which rule broke rather than which cell differs. The re-derive
    is what catches a hand-edited cell the invariants have no opinion about;
    the invariants are what turn a cell difference into a sentence.
    """
    problems = []
    committed = read_census(path)
    if committed is None:
        return ["no %s: nothing records what is in the committed native exports, "
                "so the `not-in-project` manifest row is the only figure there "
                "is. Run with --write." % os.path.relpath(path, REPO)]
    if committed == []:
        return ["%s: empty or not this tool's %d-column header"
                % (os.path.relpath(path, REPO), len(CENSUS_COLUMNS))]

    rows, refusals = build_rows(decompiled_dir, manifest_path)
    problems.extend(refusals)

    # Coverage in both directions. A census covering some of the tree is a
    # check that has quietly stopped checking the rest, and the two halves are
    # different mistakes: a row for a file that is gone, and a file with no row.
    on_disk = {rel for _abs, rel in committed_c_files(decompiled_dir)}
    seen = set()
    for r in committed:
        rel = (r.get("path") or "").strip()
        if rel in seen:
            problems.append("%s: two census rows for one file" % rel)
        seen.add(rel)
        if rel not in on_disk:
            problems.append("%s: a census row names a file that is not on disk"
                            % rel)
    for rel in sorted(on_disk - seen):
        problems.append("%s: a committed .c with no census row" % rel)
    if len(committed) != len(on_disk):
        problems.append("%d census row(s) for %d committed .c: a census covering "
                        "some of the tree is not covering the rest"
                        % (len(committed), len(on_disk)))

    # The vocabulary, and the two rules that are really one: a count that is not
    # a measurement has to say it is not, and a row that claims to be a
    # measurement has to have one.
    for r in committed:
        rel = r.get("path", "?")
        if (r.get("count_basis") or "") not in COUNT_BASES:
            problems.append("%s: count_basis is %r, not one of %s"
                            % (rel, r.get("count_basis"), "|".join(COUNT_BASES)))
        try:
            separators = int(r.get("separators_declared") or "")
        except ValueError:
            problems.append("%s: separators_declared is %r, not a number"
                            % (rel, r.get("separators_declared")))
            continue
        if r.get("in_project") == "no" and separators and \
                r.get("count_basis") == "measured":
            problems.append("%s: not in the project, yet carrying a non-zero "
                            "count as `measured`. Its %d separator(s) are a "
                            "measurement and the manifest's %s function(s) are "
                            "the zeros a `not-in-project` row always records; "
                            "`count_basis` has to say which column is which"
                            % (rel, separators, r.get("project_functions")))

    # Every deliberately-excluded program is in the census. This is the row the
    # whole exercise exists for: a 337 MB buffer file is over GitHub's limit, so
    # the program is not in the project, so the manifest's row for it is zeros
    # by construction -- and the decompile that was produced anyway is the
    # largest artefact in the Windows stack.
    for name in sorted(PROJECT_EXCLUDED):
        label = export_label(name)
        hit = [r for r in committed if r.get("export_label") == label]
        if not hit:
            problems.append("%s (%s) is excluded from the project and has no "
                            "census row, so the artefact retained for it is "
                            "recorded nowhere" % (name, label))
        elif (hit[0].get("in_project") or "") != "no":
            problems.append("%s: in_project is %r for a program in "
                            "PROJECT_EXCLUDED" % (label, hit[0].get("in_project")))

    # The header's digests against the manifest's, wherever the manifest records
    # one. Empty is not a claim, so a `not-in-project` row with a blank
    # `sha256` is exempt; a non-empty one that disagrees with the header is a
    # provenance line and a manifest describing different bytes.
    manifest_sha = {}
    if os.path.isfile(manifest_path):
        with open(manifest_path, newline="") as f:
            for r in csv.DictReader(f):
                manifest_sha[r.get("program")] = (r.get("sha256") or "").strip()
    for r in committed:
        want = manifest_sha.get(r.get("binary"))
        if want and want != (r.get("binary_sha256") or "").strip():
            problems.append("%s: the .c header records %s as %s and the "
                            "manifest records %s; one of the two is describing "
                            "different bytes"
                            % (r.get("path"), r.get("binary"),
                               r.get("binary_sha256"), want))

    # The re-derivation, field by field, so a hand-edited cell that satisfies
    # every named rule above is still red.
    derived = {r["path"]: r for r in rows}
    for r in committed:
        want = derived.pop((r.get("path") or "").strip(), None)
        if want is None:
            continue
        for col in CENSUS_COLUMNS:
            if (r.get(col) or "") != want[col]:
                problems.append("%s: %s is %r in the census and %r is what the "
                                "file derives"
                                % (r.get("path"), col, r.get(col), want[col]))
    for rel in sorted(derived):
        problems.append("%s: this tool derives a row for it and the census has "
                        "none" % rel)

    if path is not None and os.path.isfile(path) and not problems:
        with open(path, newline="") as f:
            on_disk_text = f.read()
        if on_disk_text != render_csv(rows):
            problems.append("%s: differs from what this tool derives in a way "
                            "the field comparison above did not name -- line "
                            "endings or quoting" % os.path.relpath(path, REPO))
    return problems


def do_check(path=C_CENSUS, decompiled_dir=DECOMPILED_DIR):
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print("  %s  %s%s" % ("ok  " if cond else "FAIL", label,
                              "  (%s)" % detail if detail and not cond else ""))
        if not cond:
            ok = False

    print("census_native_c.py --check")
    rows, refusals = build_rows(decompiled_dir)
    problems = census_problems(path, decompiled_dir)
    check("every committed .c is measured and attributed",
          not refusals, "; ".join(refusals[:3]))
    check("%s is what the .c files derive" % os.path.relpath(path, REPO),
          not problems, "; ".join(problems[:3]))
    for r in rows:
        print("  --    %s: %s -> %s, %s separator(s) over %s-%s, manifest %s "
              "(%s)" % (r["export_label"], r["binary"], r["binary_sha256"][:12],
                        r["separators_declared"], r["first_addr"], r["last_addr"],
                        r["project_functions"], r["count_basis"]))
    measured = {r["export_label"]: (int(r["separators_declared"]),
                                    r["first_addr"], r["last_addr"])
                for r in rows}
    # Printed on every run, never asserted. It is a statement about which rows a
    # second ground can reach, and it is here so a reader who notices the range
    # column is not empty learns the range is not the attribution mechanism.
    print("  --    range: %d of %d export(s) have a range disjoint from every "
          "other's (%s); the other %d overlap at least one other export, so a "
          "range resolves nothing for those"
          % (len(disjoint_exports(measured)), len(measured),
             ", ".join(sorted(disjoint_exports(measured))) or "none",
             len(measured) - len(disjoint_exports(measured))))
    print("  all checks passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def do_write(path=C_CENSUS, decompiled_dir=DECOMPILED_DIR):
    rows, refusals = build_rows(decompiled_dir)
    if refusals:
        raise SystemExit("error: refusing to write %s:\n  %s"
                         % (os.path.relpath(path, REPO), "\n  ".join(refusals)))
    if not rows:
        raise SystemExit("error: refusing to write %s: no committed .c was "
                         "measured, so this would be an empty census that --check "
                         "reads as current" % os.path.relpath(path, REPO))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        f.write(render_csv(rows))
    print("wrote %s: %d row(s)" % (os.path.relpath(path, REPO), len(rows)))
    return 0


def print_table(decompiled_dir=DECOMPILED_DIR):
    rows, refusals = build_rows(decompiled_dir)
    for problem in refusals:
        print("refused: %s" % problem)
    if not rows:
        print("no committed .c was measured, so there is no census to print. "
              "That is a refusal, not a clean result.")
        return 1
    widths = [max(len(col), max(len(r[col]) for r in rows))
              for col in CENSUS_COLUMNS]
    print("  ".join(col.ljust(w) for col, w in zip(CENSUS_COLUMNS, widths)))
    for r in rows:
        print("  ".join(r[col].ljust(w) for col, w in zip(CENSUS_COLUMNS, widths)))
    print("\n%d row(s); %d separator(s) declared in total; %d export(s) have a "
          "range disjoint from every other's."
          % (len(rows), sum(int(r["separators_declared"]) for r in rows),
             len(disjoint_exports({r["export_label"]:
                                    (int(r["separators_declared"]),
                                     r["first_addr"], r["last_addr"])
                                    for r in rows}))))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--decompiled-dir", default=DECOMPILED_DIR,
                    help="the committed .c tree (default "
                         "windows/decompiled/native)")
    ap.add_argument("--census", default=C_CENSUS,
                    help="the derived census (default windows/ghidra/c-census.csv)")
    ap.add_argument("--write", action="store_true",
                    help="regenerate the census from the .c files on disk")
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed census is not what the .c files "
                         "derive; needs no Ghidra and no project")
    ap.add_argument("--self-test", action="store_true",
                    help="known-answer assertions against hand-built fixtures")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    # --write first of the two modes that touch the committed CSV, and refused
    # alongside --check: a run that both re-blessed the file and compared
    # against it would exit green on anything.
    if args.check and args.write:
        raise SystemExit("error: --write regenerates %s from the .c files on "
                         "disk; it cannot be combined with --check, which "
                         "compares against it." % os.path.relpath(C_CENSUS, REPO))
    if args.check:
        return do_check(args.census, args.decompiled_dir)
    if args.write:
        return do_write(args.census, args.decompiled_dir)
    return print_table(args.decompiled_dir)


# --------------------------------------------------------------------------
# --self-test
# --------------------------------------------------------------------------

def _fixture(tmp, name, body):
    path = os.path.join(tmp, name)
    with open(path, "w") as f:
        f.write(body)
    return path


def _header(sources, digests, label="fixture"):
    return ("// %s: Ghidra 12.1.3 decompile\n"
            "// Generated by windows/tools/decompile_native.py -- do not edit;\n"
            "// improve this by editing the annotations and re-running the "
            "generator.\n"
            "// Source: %s, SHA-256 %s\n"
            "// Machine output carrying this repository's symbols. Not the "
            "vendor's source.\n\n"
            % (label, ",".join(sources), ",".join(digests)))


def self_test():
    ok = True

    def check(label, cond, detail=""):
        nonlocal ok
        print("  %s  %s%s" % ("ok  " if cond else "FAIL", label,
                              "  (%s)" % detail if detail and not cond else ""))
        if not cond:
            ok = False

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        # The known-good case FIRST, so a guard exercised only on bad input
        # cannot tell "clean" from "never ran".
        good = _fixture(tmp, "Good.c", _header(
            ["a.sys", "b.dll"], ["a" * 64, "b" * 64]) + (
            "// ==== FUN_0001 @ 0001\n\nvoid FUN_0001(void) { }\n\n"
            "// ==== FUN_0002 @ 0002\n\nvoid FUN_0002(void) { }\n\n"
            "// ==== FUN_0003 @ 0010\n\nvoid FUN_0003(void) { }\n"))
        got = measure_export(good)
        check("a three-separator file measures three, first 0001 last 0010",
              got == (3, "0001", "0010"), repr(got))
        check("the header pairs each path with a digest positionally",
              read_header_pairs(good) == [("a.sys", "a" * 64),
                                          ("b.dll", "b" * 64)],
              repr(read_header_pairs(good)))
        check("attribution picks the pair whose path names the binary",
              header_attribution(read_header_pairs(good), "b.dll")
              == ("b.dll", "b" * 64))
        check("an unknown binary is refused rather than guessed",
              header_attribution(read_header_pairs(good), "c.dll") is None)

        # Separator parsing, the three ways it is wrong.
        dup = _fixture(tmp, "Dup.c", _header(
            ["a.sys"], ["a" * 64]) + (
            "// ==== FUN_0001 @ 0001\n\nvoid FUN_0001(void) { }\n\n"
            "// ==== ALIAS_0001 @ 0001\n\nvoid ALIAS_0001(void) { }\n"))
        check("one address under two names counts two separators, one address",
              measure_export(dup) == (2, "0001", "0001"),
              repr(measure_export(dup)))
        check("the duplicate is still two names at that address",
              sorted(_c_markers(dup)["0001"]) == ["ALIAS_0001", "FUN_0001"])
        check("a file with no separator is refused",
              measure_export(_fixture(tmp, "Empty.c", "no markers here\n")) is None)
        check("an unreadable file is refused",
              measure_export(os.path.join(tmp, "Absent.c")) is None)
        check("a mismatched path/digest list is refused, not repaired",
              read_header_pairs(_fixture(tmp, "Skew.c", _header(
                  ["a.sys", "b.dll"], ["a" * 64]))) is None)
        check("a file with no // Source: line is refused",
              read_header_pairs(_fixture(tmp, "Bare.c", "// nothing\n")) is None)

        # The range ground's limit, made executable. Two exports at one image
        # base overlap, so neither is resolvable by range. The committed tree
        # does contain that case -- four of its six exports share
        # `0x180000000` -- so these fixtures are the pair that separates the two
        # behaviours without depending on which exports are committed.
        ranges = {"a": (1, "0005", "0009"), "b": (1, "0007", "0014"),
                  "c": (1, "0064", "0078")}
        check("overlapping ranges attribute nothing; a disjoint one does",
              disjoint_exports(ranges) == {"c"},
              repr(sorted(disjoint_exports(ranges))))

        # Attribution across the whole tree, in both directions.
        check("a label matching no target is refused",
              resolve_binary("NotAProgram", load_targets()) is None)
        check("the retained export's label names the .dll and not the .exe",
              resolve_binary("GamingCenter3_Cross", load_targets())
              == "GamingCenter3_Cross.dll",
              repr(resolve_binary("GamingCenter3_Cross", load_targets())))
        check("the launcher's label names the .exe and not the .dll",
              resolve_binary("GC3_launcher", load_targets())
              == "GamingCenter3_Cross.exe")

        # A census that does not exist is a refusal, not an empty pass.
        check("a missing census file is reported rather than created",
              census_problems(path=os.path.join(tmp, "absent.csv")) != [])
        empty = _fixture(tmp, "Empty.csv", "wrong,header\n")
        check("a header-less census file is reported",
              census_problems(path=empty) != [])

        # The committed tree: the census this tool derives has to be the census
        # in the tree, and the retained export is the row that has to be in it.
        problems = census_problems()
        check("the committed %s re-derives from the committed .c files"
              % os.path.relpath(C_CENSUS, REPO), not problems,
              "; ".join(problems[:3]))
        committed = read_census(C_CENSUS) or []
        retained = [r for r in committed
                    if r.get("export_label") == "GamingCenter3_Cross"]
        check("the retained export has a row, and it is the not-in-project one",
              len(retained) == 1 and retained[0]["in_project"] == "no"
              and retained[0]["count_basis"] == "carried-from-run",
              repr(retained[:1]))
        # The committed file and the row agreeing is the whole point, and it is
        # asserted against the file rather than a figure: the count moves when
        # a re-export lands, and a test holding a number would go red on that.
        if retained:
            measured = measure_export(os.path.join(REPO, retained[0]["path"]))
            check("the committed row's separator count is the file's own",
                  measured is not None
                  and str(measured[0]) == retained[0]["separators_declared"]
                  and measured[1] == retained[0]["first_addr"]
                  and measured[2] == retained[0]["last_addr"],
                  repr(measured))
        check("every declared count_basis is in the vocabulary",
              all(r.get("count_basis") in COUNT_BASES for r in committed))

    print("  all self-tests passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
