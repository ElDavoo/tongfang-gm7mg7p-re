#!/usr/bin/env python3
"""Read back the provenance header every committed `.c` under
`windows/decompiled/native/` carries, and fail when it is missing, malformed,
or names a binary or a digest the committed inputs do not back.

The Windows counterpart of `ec/tools/c_header_provenance.py`, over the other of
the two `.c` trees this repository generates. Same shape, and the same
calibration: `windows/ghidra/c-digests.csv` says a `.c` has not moved and no
hash can say which bytes it was produced from, so --write-digests would bless a
`.c` exported from a different build of a vendor binary without complaint. A
header that survives is NOT proof a file is unedited -- a determined edit
rewrites the header too -- and it is not proof the decompile is a faithful
reading of the binary. What it buys is what the digest buys, a change has to
be made deliberately and shows up in the committed diff, plus which binary and
which digest the file claims. It is not an anti-tamper control.

**Nothing is re-parsed here that `census_native_c.py` already parses.** The
`// Source:` line's `(source, sha256)` pairing, the `binary_of_source` mapping
a path onto a file name, the attribution of a digest to the binary whose path
names it, and the label-to-binary resolution are all imported from that
module, which is also where they were first written. `decompile_native.py`
reaches this module the way it reaches `census_native_c.py` -- a sibling import
by path, deferred so the two importers of each other cannot deadlock on a
module-level cycle.

**The header's own wording is held against the Java that writes it.**
`header_literal_problems()` reads the string literals out of
`ExportDecompile.java`'s `writeHeader()` and requires every literal this module
spells out to be one of them, because a Python copy of a Java literal is a
second definition of it. That is the same arrangement, and the same reason, as
`build_ec_decompile.py`'s `placeholder_name_tests()` holding `TongFang.java`'s
`isPlaceholderName()` against the Python that reimplements it.

**Two oracles for a digest, and one export with neither.** The header carries
the run's whole target list, paired positionally, so most digests in it are
for binaries that are not the export's own. Each is still checked, against
whichever committed file records it: `native-binaries.csv`'s `sha256` column
for a committed source, and that binary's own `manifest.csv` row for one
extracted at run time.

`GamingCenter3_Cross.dll` has neither. It is in `PROJECT_EXCLUDED` -- a 337 MB
analysis database is over GitHub's per-file limit -- so `native-binaries.csv`
records `runtime` for it and `manifest.csv`'s row carries an empty `sha256` by
construction. The only committed record of that binary's digest outside the
retained export's own header is `c-census.csv`, which is derived from that
header, so it cannot confirm it. This module therefore reports that binary's
export as unattributable on every run rather than folding it into a pass,
which is the arrangement `decompile_native.py --check` already uses for the
same file's missing `.asm` listing. A carve-out that prints nothing is how a
check stops meaning anything.

**The Ghidra version is asserted against what the export recorded**, read from
`manifest.csv` rather than held as a constant here: this driver derives it from
the installed Ghidra at run time, so there is no constant to hold it against
and the committed record of what a run used is the manifest. That is the whole
of the claim, and it is stated here rather than left for a reader to assume.

Needs no Ghidra, no network, no project and no Windows machine: it reads the
committed `.c` files, `native-binaries.csv` and `manifest.csv`.

Not in `.github/scripts/agent-gates.sh`; it runs as part of
`decompile_native.py --check`, which that gate already dispatches, and its
cases run under the same tool's `--self-test`.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

if HERE not in sys.path:
    # A sibling module by path, not a package, and it has to come BEFORE the
    # import below or that raises ModuleNotFoundError. sys.path[0] is this
    # directory when decompile_native.py is run as a script, which is the
    # gate's invocation; the insert is for the case where something imported
    # this module by path from elsewhere.
    sys.path.insert(0, HERE)
import census_native_c  # noqa: E402  (the path insert above is what makes this work)

# The header `ExportDecompile.writeHeader()` prints for a per-program export,
# as the literal fragments that method concatenates them from. Fragments and
# not assembled lines because `writeHeader()` interpolates the label, the
# version, the generator and the source list between them, and only the
# literals are constant text both implementations can name.
#
# Line 5 is the `Machine output` line because this driver's context carries
# neither `symbols=` nor `annotations=`; the two optional lines writeHeader()
# puts before it are absent for want of those keys, so pinning line 5 is
# pinning the header this driver writes. A driver that grew one is expected to
# make this red -- that is what it is for.
LABEL_PREFIX = "// "
LABEL_MIDDLE = ": Ghidra "
LABEL_SUFFIX = " decompile"
GENERATED_PREFIX = "// Generated by "
GENERATED_SUFFIX = " -- do not edit;"
IMPROVE_BY = ("// improve this by editing the annotations and re-running the "
              "generator.")
SOURCE_PREFIX = "// Source: "
SOURCE_SEPARATOR = ", SHA-256 "
MACHINE_OUTPUT = ("// Machine output carrying this repository's symbols. "
                  "Not the vendor's source.")

# The lines this module expects against those fragments. Assembled once, so a
# check and its fixture cannot disagree about what the header is.
LABEL_LINE = LABEL_PREFIX + "%s" + LABEL_MIDDLE + "%s" + LABEL_SUFFIX
GENERATED_BY = GENERATED_PREFIX + "%s" + GENERATED_SUFFIX

# `writeHeader()`'s body, for the same drift guard the EC module runs: a Python
# copy of a Java literal is a second definition of it, and
# `build_ec_decompile.py` already holds `TongFang.java`'s `isPlaceholderName()`
# against the Python that reimplements it for exactly this reason. The body is
# bounded on the method's own closing brace at its own indent.
EXPORT_JAVA = os.path.join(REPO, "ghidra", "scripts", "ExportDecompile.java")

_HEADER_METHOD = re.compile(
    r"private void writeHeader\(PrintWriter w, String program, "
    r"Map<String, String> ctx\) \{(.*?)\n    \}", re.S)
_JAVA_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')


def header_literal_problems(java_path=EXPORT_JAVA):
    """Whether this module's own header wording is still what the exporter
    writes.

    Every literal of `writeHeader()`'s body is returned rather than only the
    ones on the header lines -- it also reads the `ghidra_version`, `symbols`
    and `annotations` context keys -- and that is the safe direction: the set
    is a superset, so a literal of this module's that is genuinely the
    exporter's is found, and one that is not cannot be found by accident.
    """
    try:
        with open(java_path, errors="replace") as handle:
            text = handle.read()
    except OSError:
        text = ""
    match = _HEADER_METHOD.search(text)
    if not match:
        return ["ExportDecompile.java's writeHeader() could not be read, so "
                "the header wording this module holds cannot be checked "
                "against the exporter that writes it"]
    literals = _JAVA_LITERAL.findall(match.group(1))
    return ["this module's header says %r, which is not a literal "
            "writeHeader() prints -- the exporter's header has been reworded "
            "and this check has to follow it" % want
            for want in (LABEL_PREFIX, LABEL_MIDDLE, LABEL_SUFFIX,
                         GENERATED_PREFIX, GENERATED_SUFFIX, IMPROVE_BY,
                         SOURCE_PREFIX, SOURCE_SEPARATOR, MACHINE_OUTPUT)
            if want not in literals]

# `native-binaries.csv`'s placeholder for a binary whose digest is computed at
# run time rather than committed. It is a value, not an absence, so it is
# matched as one: reading it as a hex and failing the comparison would report
# four exports as corrupt for saying so.
RUNTIME = "runtime"
_HEX = re.compile(r"^[0-9A-Fa-f]{64}$")

# How far into a `.c` to read, and the same prefix census_native_c reads its
# own `// Source:` line from -- so the two cannot disagree about where the
# header ends. A prefix and not a second pass over a 56 MB body, which is
# census_native_c's reason for having a constant at all.
HEADER_PREFIX = 8192


def _committed_c(decompiled_dir):
    """Every `.c` under `decompiled_dir`, sorted, so two runs over one tree
    produce their problems in the same order."""
    out = []
    for dirpath, _dirs, names in os.walk(decompiled_dir):
        for name in names:
            if name.endswith(".c"):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


def _head_lines(path):
    """The first five lines of `path`, or [] when it cannot be read.

    Five and not one, because the header is five lines and a check that reads
    only the first would pass on a file whose fourth line had gone.
    """
    try:
        with open(path, errors="replace") as handle:
            return handle.read(HEADER_PREFIX).split("\n")
    except OSError:
        return []


def header_problems(decompiled_dir, targets, manifest, generator):
    """`([problems], [unattributable])` over every `.c` under
    `decompiled_dir`.

    `targets` is `native-binaries.csv` as `load_targets()` reads it and
    `manifest` is `manifest.csv` keyed by program, both the caller's -- this
    module holds no copy of either file's shape. `generator` is the
    `generator=` this driver writes into the context it exports from.

    Each problem names its file. `unattributable` is a list of sentences, not
    problems: they are the exports this module cannot confirm from any committed
    file, and the caller prints them on every run rather than passing over them
    in silence.
    """
    problems = header_literal_problems()
    unattributable, seen = [], []
    sha_in_csv = {os.path.basename(t["binary"]): t["sha256"] for t in targets}
    for abs_path in _committed_c(decompiled_dir):
        label = os.path.basename(abs_path)[:-2]
        rel = os.path.relpath(abs_path, REPO).replace(os.sep, "/")
        seen.append(rel)
        lines = _head_lines(abs_path)
        if len(lines) < 5:
            problems.append("%s: %d line(s), so the exporter's five-line "
                            "provenance header is not there"
                            % (rel, len(lines)))
            continue

        binary = census_native_c.resolve_binary(label, targets)
        if binary is None:
            problems.append("%s: export label %r matches no committed target "
                            "exactly once, so no binary can be named for this "
                            "header" % (rel, label))
            continue
        mrow = manifest.get(binary, {})
        version = (mrow.get("ghidra_version") or "").strip()

        # The four fixed lines. The version is compared against the manifest's
        # own record of the run, which is the only committed statement of what
        # Ghidra this export was made with; where the manifest has none there is
        # nothing to compare against, so the line is reported as
        # unattributable below rather than passed over. Lines 2, 3 and 5 name
        # no run at all and are compared either way.
        if version and lines[0] != LABEL_LINE % (label, version):
            problems.append("%s: line 1 is %r, not %r"
                            % (rel, lines[0][:100], LABEL_LINE % (label, version)))
        for i, expected in ((1, GENERATED_BY % generator), (2, IMPROVE_BY)):
            if lines[i] != expected:
                problems.append("%s: line %d is %r, not %r"
                                % (rel, i + 1, lines[i][:100], expected))
        if lines[4] != MACHINE_OUTPUT:
            problems.append("%s: line 5 is %r, not the `Machine output` line"
                            % (rel, lines[4][:100]))
        if not version:
            unattributable.append(
                "%s: %s (%s) has no `ghidra_version` in manifest.csv, so the "
                "Ghidra its header names is the only record of it"
                % (rel, label, binary))

        # The `Source:` line. read_header_pairs() returns None both for a file
        # with no such line and for one whose source and digest lists are
        # different lengths, and both are refused rather than repaired -- so the
        # problem names both rather than picking one and being wrong half the
        # time.
        pairs = census_native_c.read_header_pairs(abs_path)
        if pairs is None:
            problems.append("%s: no `// Source:` clause pairing each named "
                            "source with a digest, or one whose two lists are "
                            "different lengths -- refused rather than repaired"
                            % rel)
            continue
        for source, digest in pairs:
            named = census_native_c.binary_of_source(source)
            hits = [t for t in targets
                    if os.path.basename(t["binary"]) == named]
            if len(hits) != 1:
                problems.append("%s: the `// Source:` line names %s, which "
                                "resolves to %d committed target(s) rather than "
                                "one" % (rel, source, len(hits)))
                continue
            if hits[0]["source"] != source:
                problems.append("%s: the header says %s came from %r and "
                                "native-binaries.csv says %r; two committed "
                                "files disagree about the same binary"
                                % (rel, named, source, hits[0]["source"]))
                continue
            # Each digest is checked against whichever committed file records
            # it, and a file that records none is not silently passed: the two
            # oracles are named so a reader can see which one a refusal used,
            # and neither being there is reported below.
            csv_sha = (sha_in_csv.get(named) or "").strip()
            manifest_sha = _manifest_sha(manifest.get(named) or {})
            oracles = [(where, recorded)
                       for where, recorded in
                       (("native-binaries.csv", csv_sha),
                        ("manifest.csv", manifest_sha))
                       if _HEX.match(recorded)]
            for where, recorded in oracles:
                if recorded != digest:
                    problems.append("%s: the header records %s as %s and %s "
                                    "records %s; one of the two is describing "
                                    "different bytes"
                                    % (rel, named, digest, where, recorded))
            if not oracles:
                unattributable.append(
                    "%s: %s (%s) has no committed digest to check its header "
                    "against -- native-binaries.csv %s and manifest.csv %s -- "
                    "so that header is the only record of it"
                    % (rel, label, named,
                       "records `runtime` for it" if csv_sha == RUNTIME
                       else ("records nothing for it" if not csv_sha
                             else "records %s" % csv_sha),
                       "records none for it" if not manifest_sha
                       else "records %s" % manifest_sha))
    if not seen:
        problems.append("no committed .c under %s: there is nothing here for "
                        "the provenance header to cover, so every assertion "
                        "above would pass without reading anything"
                        % os.path.relpath(decompiled_dir, REPO).replace(
                            os.sep, "/"))
    return problems, unattributable


def _manifest_sha(row):
    """`manifest.csv`'s sha256 from a row already keyed by program, or "" when
    the row records none -- which is not the same as a row that disagrees."""
    return (row.get("sha256") or "").strip()


def self_test(check):
    """The fixture cases, reported through the caller's `check`.

    The known-good case is FIRST, for the reason every other self-test in this
    tree states: a guard exercised only on known-bad input cannot tell "clean"
    from "never ran". Every mutation is in a `/tmp` fixture, and each asserts
    that the refusal NAMES THE FILE.
    """
    import shutil
    import tempfile

    targets = [
        {"binary": "a.sys", "kind": "native", "sha256": "a" * 64,
         "source": "vendor/a.sys"},
        {"binary": "b.dll", "kind": "native", "sha256": RUNTIME,
         "source": "extract:x.msix#v1/b.dll"},
    ]
    manifest = {"a.sys": {"sha256": "a" * 64, "ghidra_version": "12.1.3"},
                "b.dll": {"sha256": "b" * 64, "ghidra_version": "12.1.3"}}
    generator = "windows/tools/decompile_native.py"

    def header(label="b", sources=None, digests=None, generated=None,
               version="12.1.3"):
        sources = ["vendor/a.sys", "extract:x.msix#v1/b.dll"] \
            if sources is None else sources
        digests = ["a" * 64, "b" * 64] if digests is None else digests
        return [
            LABEL_LINE % (label, version),
            GENERATED_BY % (generator if generated is None else generated),
            IMPROVE_BY,
            "// Source: %s, SHA-256 %s" % (",".join(sources), ",".join(digests)),
            MACHINE_OUTPUT,
        ]

    # One tree per case. Reusing one would leave each fixture's file behind for
    # the next case to trip over, which is a fixture bug that reads as a check
    # bug -- and the exact confusion the tests below exist to rule out.
    trees = []

    def tree(name, lines):
        root = tempfile.mkdtemp()
        trees.append(root)
        with open(os.path.join(root, name), "w") as handle:
            handle.write("\n".join(lines) + "\n\n// ==== FUN_0001 @ 0001\n")
        return root

    try:
        # A file the exporter wrote, exactly as it writes it. Both its digests
        # are reachable and each is checked against a different committed file
        # -- a.sys against native-binaries.csv, b.dll against its manifest row
        # -- so a run that reached only one would pass on a header half-wrong.
        p, u = header_problems(tree("b.c", header()), targets, manifest,
                               generator)
        check("header provenance: a .c carrying the exporter's header passes",
              not p and not u, "%s / %s" % (p[:1], u[:1]))

        # The `Generated by` line altered: what a re-export from a renamed
        # driver would leave behind on every file in the tree at once.
        p, _ = header_problems(
            tree("b.c", header(generated="windows/tools/some_other.py")),
            targets, manifest, generator)
        check("header provenance: a .c whose Generated by line names another "
              "generator is caught, and the file is named",
              len(p) == 1 and "b.c" in p[0] and "Generated by" in p[0], str(p))

        # A skewed source list. read_header_pairs() refuses it rather than
        # repairing it, because a repaired pairing attributes a digest to the
        # wrong binary with nothing looking wrong.
        p, _ = header_problems(tree("b.c", header(digests=["a" * 64])),
                               targets, manifest, generator)
        check("header provenance: a .c whose Source: list is skewed -- more "
              "sources than digests -- is refused rather than repaired, and "
              "the file is named",
              len(p) == 1 and "b.c" in p[0]
              and "different lengths" in p[0], str(p))

        # A source path the committed target list does not carry: the same
        # disagreement census_native_c.build_rows() refuses on, checked here at
        # the header rather than through the census.
        p, _ = header_problems(
            tree("b.c", header(sources=["vendor/a.sys",
                                        "extract:x.msix#v1/c.dll"],
                               digests=["a" * 64, "c" * 64])),
            targets, manifest, generator)
        check("header provenance: a .c naming a source native-binaries.csv "
              "does not resolve to exactly one target is caught, and the file "
              "is named",
              len(p) == 1 and "b.c" in p[0]
              and "committed target(s)" in p[0], str(p))

        # A digest that disagrees with the committed source binary's column.
        # Both oracles are consulted and both disagree here, so two problems
        # are the right answer and the assertion says so rather than expecting
        # one -- a check that reached only native-binaries.csv would pass on a
        # manifest describing different bytes.
        p, _ = header_problems(
            tree("a.c", header(label="a", digests=["c" * 64, "b" * 64])),
            targets, manifest, generator)
        check("header provenance: a .c whose digest disagrees with "
              "native-binaries.csv is caught by both oracles that record it, "
              "and the file is named",
              len(p) == 2 and all("a.c" in x and "different bytes" in x
                                  for x in p)
              and any("native-binaries.csv" in x for x in p)
              and any("manifest.csv" in x for x in p), str(p))

        # The export whose digest has no committed oracle at all is reported as
        # unattributable rather than folded into a pass: no problems, but named.
        p, u = header_problems(
            tree("c.c", header(label="c", sources=["extract:x.msix#v1/c.dll"],
                               digests=["d" * 64])),
            targets + [{"binary": "c.dll", "kind": "native", "sha256": RUNTIME,
                        "source": "extract:x.msix#v1/c.dll"}],
            {"c.dll": {"sha256": "", "ghidra_version": ""}}, generator)
        check("header provenance: an export with no committed digest behind it "
              "is reported rather than folded into a pass, and named",
              not p and any("c.c" in x and "only record of it" in x
                            for x in u), "%s / %s" % (p, u))

        # The floor: a tree with nothing in it is a check that read nothing,
        # not a check that passed.
        p, _ = header_problems(os.path.join(trees[0], "no-such-tree"),
                               targets, manifest, generator)
        check("header provenance: an empty tree is reported rather than "
              "passing with nothing compared",
              any("nothing here" in x for x in p), str(p))

        # The header wording this module does not take from its caller, held
        # against the Java that writes it -- the arrangement
        # build_ec_decompile.py's placeholder_name_tests() uses for
        # isPlaceholderName(), for the same reason.
        check("header provenance: every header literal this module holds is a "
              "literal writeHeader() prints, so a rewording there cannot leave "
              "this check red on a tree the exporter wrote correctly",
              not header_literal_problems(), str(header_literal_problems()))
        # And that it fires when one is not: a guard against drift, exercised
        # only on the committed Java, cannot tell "still matching" from "never
        # compared anything".
        java = os.path.join(trees[0], "ExportDecompile.java")
        shutil.copyfile(EXPORT_JAVA, java)
        with open(java) as handle:
            text = handle.read()
        with open(java, "w") as handle:
            handle.write(text.replace(
                "// improve this by editing the annotations and re-running the "
                "generator.",
                "// improve this by editing the annotations."))
        p = header_literal_problems(java)
        check("header provenance: a rewording of a header line in the Java is "
              "reported, and this module's copy is named",
              len(p) == 1 and "improve this by editing" in p[0], str(p))
        with open(java, "w") as handle:
            handle.write(text.replace(
                "private void writeHeader(PrintWriter w, String program,",
                "private void writeSomeOtherHeader(PrintWriter w,"))
        p = header_literal_problems(java)
        check("header provenance: a Java whose writeHeader() cannot be found is "
              "reported rather than passing with nothing compared",
              p and "could not be read" in p[0], str(p))
        check("header provenance: an absent Java is refused the same way",
              header_literal_problems(os.path.join(trees[0], "no.java")) != [])
    finally:
        for root in trees:
            shutil.rmtree(root, ignore_errors=True)
    return True


if __name__ == "__main__":
    # Import-safe, like census_native_c.py. The entry point is
    # decompile_native.py's --check and --self-test.
    print(__doc__)
