#!/usr/bin/env python3
"""Read back the provenance header every committed `.c` under `ec/decompiled/`
carries, and fail when it is missing, malformed, or names a firmware image
other than the one this tree is built from.

**What it adds to the digest, and what it does not.** `c-digests.csv` says a
`.c` has not moved. This says which image the file claims to have come from,
and no hash can say that: `--write-digests` will hash a `.c` exported from a
different firmware without complaint, because the file is a file and the digest
is a fact about the file. The header is the only place the claim is written
down, so it is the only place a wrong-image `.c` is visible at all -- and that
is a worse fault than a hand edit, because the decompile is then a reading of
bytes this repository does not claim to have read.

**The calibration, which is the digest's and not a stronger one.** A header
that survives is NOT proof that a file is unedited: a determined edit rewrites
the header too, and nothing here re-derives the C from the firmware. What it
buys is what the digest buys -- a change has to be made deliberately and shows
up in the committed diff -- plus the image the file names, which the digest has
no column for. It is not an anti-tamper control and it does not make any
decompile a faithful reading of the firmware. `verify_reassembly.py`'s byte
re-derivation is the stronger claim and a different question: that one
re-derives the listing from the firmware, a trusted input the decompiled C has
no counterpart to.

**The trap this routes around.** A file under `ec/decompiled/common/` declares
`bank0` on its first line and carries bank0's `Source:` clause, while its
`index.csv` row reads `program=common` -- `common` is an export grouping the
de-dup renames a folded bank0 row to, not a program `write_context()` writes a
`source.` line for. So the expected clause is keyed on the program token *the
header itself declares*, never on the directory the file sits in and never on
the index row's `program`. Keyed on either of those it fails every file in
that directory for a reason no export can clear, which is a red `--check`
nobody can fix.

**The wording is not restated here.** The `source.<program>` clauses and the
firmware's path text are the caller's, because the caller is the tool whose
`write_context()` composes them; so are the Ghidra version and the generator
name. That is the same reason the committed digest lives in a CSV rather than
in the manifest: a string that only one writer reaches must not be restated by
the reader. What remains here is the shape -- the four lines
`ExportDecompile.writeFunctionFile()` prints, and the two its
`writeBoundaryCaveat()` adds -- and even that is checked against the Java
rather than trusted: `header_literal_problems()` holds every literal this
module spells out against the literals the exporter concatenates them from, and
the caveat is read from `writeBoundaryCaveat()` outright. That is the same
arrangement, and for the same reason, as `build_ec_decompile.py`'s
`placeholder_name_tests()` holding `TongFang.java`'s `isPlaceholderName()`
against the Python that reimplements it: a Python copy of a Java literal is a
second definition of it, free to drift.

Needs no Ghidra, no network, no project and no hardware: it reads committed
`.c` files, one Java file the committed exports were written by, and a digest
the caller has already computed for its manifest comparison, so it costs no
second pass over the firmware image.

Not in `.github/scripts/agent-gates.sh`; it runs as part of
`build_ec_decompile.py --check`, which that gate already dispatches, and its
cases run under the same tool's `--self-test`.
"""

import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
EXPORT_JAVA = os.path.join(REPO, "ghidra", "scripts", "ExportDecompile.java")

# How far into a `.c` to read. The header is four lines plus at most the two
# of the boundary caveat, so this is a prefix and not a second pass over the
# body -- the §14a lesson, and the reason it is a constant rather than a read.
HEADER_PREFIX = 8192

# Line 1, the shape `writeFunctionFile()` prints and the one
# `c_presence_problems()` already matches. Defined here rather than imported,
# because this module is imported BY the tool that would own it and a
# module-level import back would be a cycle; `build_ec_decompile.py` names this
# one as its `EC_C_HEADER`, so the shape has one spelling in the repository
# rather than two that can drift.
C_HEADER = re.compile(r"^// (\S+) @ ([0-9A-Fa-f]+)\s+(\S+)")

# Line 2 and line 3's markers, as the fragments `writeFunctionFile()` prints
# around the values it interpolates. Named rather than spliced into one literal
# so `header_literal_problems()` below can hold each one against the Java it
# came from -- the same arrangement as `placeholder_name_tests()`, for the same
# reason: a Python string nobody checks against the exporter is a second
# definition, free to drift.
GEN_PREFIX = "// Ghidra "
GEN_MIDDLE = " decompile, generated by "
GEN_SUFFIX = " -- do not edit."
SOURCE_PREFIX = "// Source: "
SOURCE_SEPARATOR = ", SHA-256 "
# Line 4, one whole literal in the Java and so one whole literal here.
MACHINE_OUTPUT = ("// Machine output carrying this repository's symbols. "
                  "Not the vendor's source.")

# Line 3, split rather than compared whole: whether the clause names the program
# the file declares, and whether the digest names the image this tree is built
# from, are two questions, and a whole-line comparison answers both with one
# difference and no diagnosis.
_SOURCE_LINE = re.compile(r"^// Source: (.*), SHA-256 ([0-9A-Fa-f]*)$")

# The lines `writeBoundaryCaveat()` and `writeFunctionFile()` print, read out
# of the Java rather than restated. Both method bodies are bounded on their own
# closing brace at their own indent, so what follows either is not counted --
# `writeFunctionFile()`'s nested try-block closes further in, so it is not
# mistaken for the method's own.
#
# Anchored on the method name rather than its full signature, because that
# signature wraps across two lines in the Java and a regex holding the whole of
# it is a second copy of a line a reformat would break.
_CAVEAT_METHOD = re.compile(
    r"private void writeBoundaryCaveat\(PrintWriter w\) \{(.*?)\n    \}", re.S)
_FUNCTION_FILE_METHOD = re.compile(
    r"private void writeFunctionFile\([^)]*\)[^{]*\{(.*?)\n    \}", re.S)
_CAVEAT_LINE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def java_println_literals(method_re, java_path=EXPORT_JAVA):
    """Every string literal in a matched Java method's body, in source order, or
    [] when the method cannot be read.

    The literal fragments, not the assembled line: `writeFunctionFile()` builds
    line 2 by concatenating four literals around the Ghidra version and the
    generator name, and only the literals are constant text the two
    implementations can be held against. Matching literals rather than whole
    `println("...")` calls is what makes a concatenated line findable at all.

    Every literal in the body is returned, not only the ones on the header
    lines -- `writeFunctionFile()` also compares `seedBasis` against
    `"call-target"` and passes context keys to `get()`. That is the safe
    direction: the set is a superset, so a literal of this module's that is
    genuinely the exporter's is found, and one that is not cannot be found by
    accident from an unrelated line of the same method.
    """
    try:
        with open(java_path, errors="replace") as handle:
            text = handle.read()
    except OSError:
        return []
    match = method_re.search(text)
    return _CAVEAT_LINE.findall(match.group(1)) if match else []


def boundary_caveat_lines(java_path=EXPORT_JAVA):
    """The header lines a `call-target` boundary carries, in source order, or
    [] when the method cannot be read.

    Parsed rather than typed in, and an unreadable Java yields an empty list
    rather than raising: a raise here would read as a broken build instead of
    as the drift it is, and the caller asserts against the empty list, which
    fails. Same arrangement, and the same reason, as
    `build_ec_decompile.py`'s `placeholder_name_tests()`.
    """
    return java_println_literals(_CAVEAT_METHOD, java_path)


def header_literal_problems(java_path=EXPORT_JAVA):
    """Whether this module's own header wording is still what the exporter
    writes.

    The pieces here that no caller supplies -- the "decompile, generated by"
    phrasing, the "// Source: " and ", SHA-256 " markers, the `Machine output`
    sentence -- are literals in `ExportDecompile.java`, and a Python copy of a
    Java literal is a second definition of it. `build_ec_decompile.py` already
    holds `TongFang.java`'s `isPlaceholderName()` against the Python that
    reimplements it, for exactly this reason; this is the same arrangement for
    the header, and it is what stops a rewording in the Java from leaving the
    check red on a tree the exporter wrote correctly.
    """
    literals = java_println_literals(_FUNCTION_FILE_METHOD, java_path)
    if not literals:
        return ["ExportDecompile.java's writeFunctionFile() could not be read, "
                "so the header wording this module holds cannot be checked "
                "against the exporter that writes it"]
    return ["this module's header says %r, which is not a literal "
            "writeFunctionFile() prints -- the exporter's header has been "
            "reworded and this check has to follow it" % want
            for want in (GEN_PREFIX, GEN_MIDDLE, GEN_SUFFIX, SOURCE_PREFIX,
                         SOURCE_SEPARATOR, MACHINE_OUTPUT)
            if want not in literals]


def header_problems(decompiled_dir, source_by_program, firmware_sha256,
                    ghidra_version, generator, call_target_files):
    """`([problems], n_files)` over every `.c` under `decompiled_dir`.

    `source_by_program` is `write_context()`'s own `source.<program>` clauses
    keyed by program; `firmware_sha256` is the digest the caller has already
    computed; `generator` and `ghidra_version` are the caller's constants;
    `call_target_files` the `out_file`s whose index row has
    `seed_basis == call-target`, which is the exporter's own condition for
    writing the caveat. None is defaulted: a header check that fell back to a
    built-in expectation when the caller passed none would be the check that
    quietly stopped checking, which is the shape this exists to catch.

    Each problem names its file. The count is returned so `--check` can print
    what it compared -- such figures belong in the check's own output, which
    nobody commits, rather than in a document every merge has to edit.
    """
    problems = header_literal_problems()
    caveat = tuple(boundary_caveat_lines())
    if not caveat:
        problems.append("ExportDecompile.java's writeBoundaryCaveat() could "
                        "not be read, so no .c can be held against the caveat "
                        "the exporter writes for a call-target boundary")
    seen = []
    for abs_path in _committed_c(decompiled_dir):
        rel = os.path.relpath(abs_path, decompiled_dir).replace(os.sep, "/")
        seen.append(rel)
        with open(abs_path, errors="replace") as handle:
            lines = handle.read(HEADER_PREFIX).split("\n")
        if len(lines) < 4:
            problems.append("%s: %d line(s), so the exporter's four-line "
                            "provenance header is not there"
                            % (rel, len(lines)))
            continue
        head = C_HEADER.match(lines[0])
        if head is None:
            problems.append("%s: line 1 is %r, not the `// <program> @ <addr>  "
                            "<name>` the exporter writes" % (rel, lines[0][:80]))
            continue
        program = head.group(1)
        want_source = source_by_program.get(program)
        if want_source is None:
            problems.append("%s: declares program %r, which has no `source.` "
                            "clause, so where it came from cannot be named"
                            % (rel, program))
            continue
        want_line2 = ("%s%s%s%s%s" % (GEN_PREFIX, ghidra_version, GEN_MIDDLE,
                                      generator, GEN_SUFFIX))
        if lines[1] != want_line2:
            problems.append("%s: line 2 is %r, not %r"
                            % (rel, lines[1][:100], want_line2))
        src = _SOURCE_LINE.match(lines[2])
        if src is None:
            problems.append("%s: line 3 is %r, not a `// Source: <clause>, "
                            "SHA-256 <hex>` clause" % (rel, lines[2][:100]))
        else:
            if src.group(1) != want_source:
                problems.append("%s: the `// Source:` clause names %r, not %r -- "
                                "this file was not exported from the program it "
                                "declares" % (rel, src.group(1)[:80],
                                              want_source[:80]))
            if src.group(2) != firmware_sha256:
                problems.append("%s: the `// Source:` SHA-256 is %s, which does "
                                "not match the digest of the committed firmware "
                                "%s -- a `.c` left behind by an export of another "
                                "image" % (rel, src.group(2) or "(none)",
                                           firmware_sha256))
        if lines[3] != MACHINE_OUTPUT:
            problems.append("%s: line 4 is %r, not the `Machine output` line"
                            % (rel, lines[3][:100]))
        # The caveat, in both directions: ExportDecompile writes it exactly when
        # the row's seed_basis is call-target, so a file that gained one without
        # the index saying so asserts something the index does not back, and the
        # same fault in reverse is a hypothesis the file no longer carries.
        has = tuple(lines[4:4 + len(caveat)]) == caveat
        wants = rel in call_target_files
        if has and not wants:
            problems.append("%s: carries the call-target boundary caveat, which "
                            "its index row's seed_basis does not call for" % rel)
        elif wants and not has:
            problems.append("%s: its index row is seeded from the call-target "
                            "census, so it owes that boundary caveat, and does "
                            "not carry it" % rel)
    if not seen:
        problems.append("no committed .c under %s: there is nothing here for "
                        "the provenance header to cover, so every assertion "
                        "above would pass without reading anything"
                        % os.path.relpath(decompiled_dir, REPO).replace(
                            os.sep, "/"))
    return problems, len(seen)


def _committed_c(decompiled_dir):
    """Every `.c` under `decompiled_dir`, sorted, so two runs over one tree
    produce their problems in the same order."""
    out = []
    for dirpath, _dirs, names in os.walk(decompiled_dir):
        for name in names:
            if name.endswith(".c"):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


def self_test(check):
    """The fixture cases, reported through the caller's `check`.

    The known-good case is FIRST, for the reason every other self-test in this
    tree states: a guard exercised only on known-bad input cannot tell "clean"
    from "never ran". Every mutation is in a `/tmp` fixture -- corrupting the
    committed tree to prove a check works is not a thing this may do -- and each
    asserts that the refusal NAMES THE FILE, because a check that fails without
    saying which of thousands it failed on is a check nobody can act on.
    """
    import shutil
    import tempfile

    firmware = "ec/firmware/GMxMGxx_11.800"
    source = {
        "bank0": "%s, CODE bank 0 at file 0x08000 + the 0x0000-0x7FFF common "
                 "area" % firmware,
        "bank1": "%s, CODE bank 1 at file 0x10000 + the 0x0000-0x7FFF common "
                 "area" % firmware,
    }
    digest = "a" * 64
    generator = "ec/tools/build_ec_decompile.py"
    version = "12.1.3"

    def header(program="bank1", caveat=False, source_line=None, drop=()):
        lines = [
            "// %s @ F153   bare_ret_f153   [named]" % program,
            "// Ghidra %s decompile, generated by %s -- do not edit."
            % (version, generator),
            "// Source: %s, SHA-256 %s" % (source[program], digest),
            MACHINE_OUTPUT,
        ]
        if caveat:
            lines.extend(boundary_caveat_lines())
        if source_line is not None:
            lines[2] = source_line
        return [l for i, l in enumerate(lines) if i not in drop]

    def fixture(root, rel, lines):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write("\n".join(lines) + "\n\nvoid bare_ret_f153(void) {}\n")
        return rel

    def run(root, calls=()):
        return header_problems(root, source, digest, version, generator, calls)

    tmp = tempfile.mkdtemp()
    try:
        # A file the exporter wrote, exactly as it writes it.
        fixture(tmp, "bank1/F153.c", header())
        p, n = run(tmp)
        check("header provenance: a .c carrying the exporter's header passes",
              not p and n == 1, "%s (%d file(s))" % (p[:1], n))

        # The generator line dropped. The lines after it shift up, so the check
        # says so on each of them rather than on one; what is asserted is that
        # it notices and names the file, not how many lines it takes.
        fixture(tmp, "bank1/F153.c", header(drop=(1,)))
        p, _ = run(tmp)
        check("header provenance: a .c with the generator line removed is "
              "caught, and the file is named",
              p and all("bank1/F153.c" in x for x in p)
              and any("line 2 is" in x for x in p), str(p))

        # The load-bearing case: another image. Every other assertion this
        # repository makes about a decompile passes on this file.
        fixture(tmp, "bank1/F153.c",
                header(source_line="// Source: %s, SHA-256 %s"
                       % (source["bank1"], "b" * 64)))
        p, _ = run(tmp)
        check("header provenance: a .c whose Source: SHA-256 is another "
              "image's digest is caught, and the file is named",
              len(p) == 1 and "bank1/F153.c" in p[0]
              and "does not match the digest of the committed firmware" in p[0],
              str(p))

        # The clause gone altogether, which is what a header that has lost both
        # its source and its digest looks like.
        fixture(tmp, "bank1/F153.c", header(drop=(2,)))
        p, _ = run(tmp)
        check("header provenance: a .c whose Source: clause is missing is "
              "caught, and the file is named",
              p and all("bank1/F153.c" in x for x in p)
              and any("not a `// Source:" in x for x in p), str(p))

        # The clause naming a different program than the file declares: the
        # other half of the clause question, and one the digest cannot see.
        fixture(tmp, "bank1/F153.c",
                header(source_line="// Source: %s, SHA-256 %s"
                       % (source["bank0"], digest)))
        p, _ = run(tmp)
        check("header provenance: a .c whose Source: clause names another "
              "program's window is caught, and the file is named",
              len(p) == 1 and "bank1/F153.c" in p[0]
              and "not exported from the program it declares" in p[0], str(p))

        # The `common/` trap, made executable. The file declares bank0 and
        # carries bank0's clause while sitting in the directory the index calls
        # `common`: keying the expectation on either the directory or the index
        # row's program fails every file in it for a reason no export can clear.
        common = tempfile.mkdtemp()
        try:
            fixture(common, "common/0000.c", header("bank0"))
            p, n = run(common)
            check("header provenance: a .c in common/ that declares bank0 and "
                  "carries bank0's Source: clause passes, so the expectation "
                  "is keyed on the program the header declares",
                  not p and n == 1, "%s (%d file(s))" % (p[:1], n))
        finally:
            shutil.rmtree(common, ignore_errors=True)

        # The caveat, both directions, against the exporter's own condition.
        fixture(tmp, "bank1/F153.c", header(caveat=True))
        p, _ = run(tmp)
        check("header provenance: a caveat on a file whose index row is not a "
              "call-target row is caught, and the file is named",
              len(p) == 1 and "bank1/F153.c" in p[0]
              and "does not call for" in p[0], str(p))
        fixture(tmp, "bank1/F153.c", header())
        p, _ = run(tmp, ("bank1/F153.c",))
        check("header provenance: a call-target row's .c with the caveat "
              "dropped is caught, and the file is named",
              len(p) == 1 and "bank1/F153.c" in p[0]
              and "call-target census" in p[0], str(p))
        fixture(tmp, "bank1/F153.c", header(caveat=True))
        p, _ = run(tmp, ("bank1/F153.c",))
        check("header provenance: a call-target row's .c carrying the caveat "
              "passes, so both directions are held by one predicate",
              not p, str(p))

        # The floor: a tree with nothing in it is a check that read nothing,
        # not a check that passed.
        p, n = run(os.path.join(tmp, "no-such-tree"))
        check("header provenance: an empty tree is reported rather than passing "
              "with nothing compared",
              len(p) == 1 and n == 0 and "nothing here" in p[0], str(p))

        check("header provenance: the boundary caveat is read out of "
              "ExportDecompile.java's writeBoundaryCaveat() rather than "
              "restated here, so a rewording there cannot leave this module "
              "asserting a caveat no export writes",
              len(boundary_caveat_lines()) == 2,
              repr(boundary_caveat_lines()))

        # The header wording this module does not take from its caller, held
        # against the Java that writes it -- the arrangement
        # build_ec_decompile.py's placeholder_name_tests() uses for
        # isPlaceholderName(), for the same reason.
        check("header provenance: every header literal this module holds is a "
              "literal writeFunctionFile() prints, so a rewording there cannot "
              "leave this check red on a tree the exporter wrote correctly",
              not header_literal_problems(), str(header_literal_problems()))
        # And that it fires when one is not. A guard against drift, exercised
        # only on the committed Java, cannot tell "still matching" from "never
        # compared anything" -- the same known-good-first rule as above.
        _java = os.path.join(tmp, "ExportDecompile.java")
        shutil.copyfile(EXPORT_JAVA, _java)
        with open(_java) as _f:
            _text = _f.read()
        with open(_java, "w") as _f:
            _f.write(_text.replace(
                "// Machine output carrying this repository's symbols. Not the "
                "vendor's source.",
                "// Machine output carrying OUR symbols. Not the vendor's "
                "source."))
        _p = header_literal_problems(_java)
        check("header provenance: a rewording of the Machine output line in "
              "the Java is reported, and this module's copy is named",
              len(_p) == 1 and "Machine output" in _p[0], str(_p))
        with open(_java, "w") as _f:
            _f.write(_text.replace("writeFunctionFile(File f, String program,",
                                   "writeSomeOtherThing(File f, String program,"))
        check("header provenance: a Java whose writeFunctionFile() cannot be "
              "found is reported rather than passing with nothing compared",
              header_literal_problems(_java) != []
              and "could not be read" in header_literal_problems(_java)[0],
              str(header_literal_problems(_java)))
        check("header provenance: an absent Java is refused the same way",
              header_literal_problems(os.path.join(tmp, "no-such.java")) != [])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return True


if __name__ == "__main__":
    # Import-safe, like every sibling this tool imports. The entry point is
    # build_ec_decompile.py's --check and --self-test, which is where the
    # expectations -- the clauses, the version, the generator, the digest --
    # live; there is nothing to run from here.
    print(__doc__)