#!/usr/bin/env python3
"""Hold the names prose gives a prepared gate patch to the files on disk.

`tools/test_agent_gates_patches.py` closes the other half of this. Its case 6
checks that each patch *header's* `git apply` line names the file it came from,
which is what a rename or a fold breaks. Prose that names a patch is a different
surface and a fold breaks it the same way: #745 folded
`check_testdata_index()` into `agent-gates-capture-claims.patch` and deleted
`agent-gates-testdata-index.patch`, and repointing the references was six manual
edits across five files with nothing to notice a miss. The next fold costs the
same six edits, and this is what runs instead of a person re-greping.

`check_doc_links()` in `.github/scripts/agent-gates.sh` cannot see any of it.
Its discovery is `grep -rEo '\\]\\(([^:)]+\\.md)\\)'`, so it reads markdown
*links* and nothing else -- not a backticked path, and not a `.patch` at all.
It finds 686 `.md` link references at `271389d` and zero references to a patch,
while the patch set is named in prose 53 times across 16 markdown files at that
commit and linked once. Those figures are that commit's and are here to name the
shape of the gap, not the size of it: this tool's own run prints the current
ones, which is the pair to re-derive. The link `check_doc_links` misses is in
`docs/findings/xdata-census-self-test-gate.md`,
``[`../ci/agent-gates-disasm8051-self-test.patch`](../ci/agent-gates-disasm8051-self-test.patch)``,
and #942 added a second beside it in
`docs/findings/pin-table-row-reconciliation.md` -- two now, both links rather
than prose, and both of them things extending the gate's *link* discovery to
`.patch` reaches. Both spellings are read here for that reason.

**Scope: two directions, two declared file sets.** The *live* direction reads
`docs/ci/` -- every prepared change there, a glob over `.patch` plus the names
in `PREPARED_NON_PATCH`. The *reference* direction reads `REFERENCE_GLOBS`,
`**/*.md` and `docs/ci/**/*.patch`: prose, and the prepared changes' own
headers. A `.patch` naming another `.patch` is a reference class no prose grep
can see, which is the second glob's whole reason. A bare `*.patch` would also
sweep in `linux/patches/`, which holds two upstream driver patches rather than
prepared gate changes; neither names a name in the set, so the scope is stated
here rather than left incidental. (The paragraph this replaces gave
`evidence/ec-reencode/2026-09-23-sdas8051-rowdiff.csv` as the reason to stop at
the `docs/ci/` prefix, and that file is a `.csv` -- never a counterexample to a
`*.patch` glob. The two `linux/patches/` files above are, and they are what
the second glob is drawn around.)

**The historical rule, which is the whole design problem here.** A handful of
names are in prose and deliberately not on disk, and a naive "every name
resolves" rule false-positives on every reference to them. **The count of those
references is a figure of the tree it was counted on and has moved more than
once** -- it read "all four" when the first two were added, and `--verbose`
prints the current one, which is the figure to re-derive:

  * `agent-gates-testdata-index.patch` -- the file as it was, named in
    `docs/findings/prepared-gate-patches.md`'s measured-results table row and in
    the paragraph under it, and in `docs/findings.md` §43 describing the
    collision the fold resolved.
  * `agent-gates-claims-and-testdata.patch` -- the alternative reading #745
    rejected and left out on purpose, named in that same write-up.
  * `agent-gates-check-history-checkouts.patch` -- the filename issue #1033
    asked for, which the same saturation that folded #745's second patch
    declined again: the check went into
    `docs/ci/agent-gates-capture-claims.patch` instead, and the write-up names
    what was asked for beside what was prepared, per `CLAUDE.md` §4a-4d.
  * `agent-gates-audit-call-targets-self-test.patch` -- the filename issue #1094
    asked for, declined for the same reason one region further along: the tail
    of `check_ghidra_tooling()` that the tool wanted was already held by
    `docs/ci/agent-gates-reassembly-bound-check.patch`, and two patches cut at
    one anchor collide in both orders while each applies alone. So the call
    folds into that file and the write-up names what was asked for beside what
    was prepared, per `CLAUDE.md` §4a-4d.

`HISTORICAL` below is that opt-out, keyed on the patch **name** and enumerated
here rather than marked in the prose. The alternative the issue offers -- a
fenced or quoted span at each reference -- was not taken, and the reason is
recorded in `docs/findings/doc-patch-reference-gate.md`: every one of them is a
record, and `CLAUDE.md` §4a-4d says a superseded claim stays visible with a
correction beside it rather than reshaped so a checker can see it. The bound is
stated rather than hidden: any *new* reference to one of the names above is
exempt by construction, so the enumeration is as wide as the reasons it carries
and one entry per reason is the discipline. Both directions are held -- each key
is still absent from `docs/ci/`, and still cited by at least one markdown file
-- so neither a patch reappearing under that name nor a reference being edited
away can leave the exemption quietly true. `--verbose` prints how many keys
there are; that count is a figure of the tree it was measured on and is not
written down here.

**The live direction is checked too, mirroring the sibling:** every prepared
change in `docs/ci/` must be cited by at least one file this check reads -- a
patch by a parsed reference, and the one named non-patch entry by prose, for
the reason `scan` gives. Every reference *in the files this check reads* is
what the reference direction holds; that is narrower than every reference in
the tree, and the `.py` paragraph below is where the difference is. A human
adding a prepared change and documenting it nowhere is the mirror failure, and
it is the half that broke in `test_readme_suite_table.py`. The named entry is
held in both directions, so its deletion is not invisible to a glob that has
stopped matching it.

**What this does not check.** It resolves a *name* against a directory. It does
not read a reference's surrounding sentence to decide whether that sentence is
instructing a `git apply` or describing history -- `HISTORICAL` stands in for
that at name granularity, and the cost of getting it wrong is a false positive a
reader can see and an edit to make. Three further limits, all measured rather
than asserted, and `docs/findings/doc-patch-ref-file-sets.md` has the commands
and the decision behind each:

- **The `.py` population is out of scope, and by name.** Five `ec/tools/` files
  carry live-direction citations this check does not count --
  `grade_0751_isolation.py` and `test_grade_0751_isolation.py` name
  `agent-gates-0751-self-test.patch`, `test_check_pin_table_rows.py` names
  `agent-gates-pin-table-rows.patch`, `test_data_regions.py` names
  `agent-gates-disasm8051-self-test.patch` and
  `test_check_history_checkouts_corpus.py` names
  `agent-gates-capture-claims.patch`. Widening to `*.py` would report this
  tool's and its suite's own deliberately-absent fixture names
  (`agent-gates-a.patch`, `-b`, `-never-existed`, `-gone`) as STALE, and would
  make the "still cited" half of every `HISTORICAL` key self-certifying -- this
  file's own docstring names all three.
- **A citation in a diff body is not a citation.** The one place
  `docs/ci/agent-gates-capture-claims.patch` names
  `agent-gates-deep-schedule.yml` is a `+` line at :197, a comment the patch
  adds to a Python file. That is why the non-patch entry's citation is read
  over prose, and it is why a future patch that adds a backticked patch name
  into a file it patches would contribute a reference that is a diff rather
  than a citation.
- **A renamed non-patch entry leaves its prose citations unreported.** Its name
  is not parsed, so `stale` cannot see them; the `MISSING` verdict reports the
  rename once, by naming the file that is gone.

**Counts print on every run and none is asserted.** A run that found nothing and
a run that found nothing wrong look identical from the exit code alone, so a
discovery of zero references is itself a failure -- the §14b shape
`tools/run-tests.sh` and `ec/tools/census_test_line_pins.py` both name. For the
same reason no count here is a floor: an expected count turns every added test
into a failure, which is what `tools/test_readme_suite_table.py`'s docstring says
about its own comparison, and the suite asserts non-emptiness instead, which is
the assertion that is true of the tree rather than of the tool.

Usage:
    python3 tools/check_doc_patch_refs.py [--check] [--verbose]
    python3 tools/check_doc_patch_refs.py --self-test
"""
import argparse
import collections
import contextlib
import io
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CI = REPO / "docs" / "ci"

# The names prose names on purpose; one entry per reason, and the reasons are
# enumerated in the docstring above rather than here. The write-up beside this
# tool records why this is an enumeration rather than a per-reference opt-out,
# and what the choice costs.
HISTORICAL = {
    "agent-gates-testdata-index.patch",
    "agent-gates-claims-and-testdata.patch",
    "agent-gates-check-history-checkouts.patch",
    "agent-gates-audit-call-targets-self-test.patch",
}

# The prepared changes in `docs/ci/` that are not `.patch`. One entry today,
# and it is held *by name* rather than by shape: the exclusion
# `docs/findings/prepared-gate-patches.md` records is about what the file is --
# a `cp` into `.github/workflows/`, order-independent, with no pre-image to go
# stale against -- and not about its extension. So the live-side glob is left
# over `.patch` and this is added beside it, which also means a `.rej` an
# editor or a `git apply --reject` left in `docs/ci/` cannot be admitted by
# accident the way widening the glob to `agent-gates-*` would admit it.
# The two directions are now separate: `NAME` still ends in `\.patch`, so this
# name is never *parsed* as a reference, while it is held on disk. See
# `docs/findings/doc-patch-ref-file-sets.md` for what that costs.
PREPARED_NON_PATCH = {
    "agent-gates-deep-schedule.yml",
}

# The files the reference direction reads, and the prose half kept beside them.
# A tuple rather than a bare `*.patch` glob, because the scope is a decision
# and not an accident of the tree: `linux/patches/` holds two `.patch` files
# that are upstream driver patches, not prepared gate changes, and neither
# names a name in the set below. Prose plus the prepared changes' own headers
# is the whole of it, and a `.patch` naming another `.patch` is a reference
# class no prose grep can see.
PROSE_GLOB = "**/*.md"
PREPARED_GLOB = "docs/ci/**/*.patch"
REFERENCE_GLOBS = (PROSE_GLOB, PREPARED_GLOB)

# The subject, as a shape. `*` is deliberately not in the character class: a
# pattern loose enough to match a bare name also matches the eight prose spans
# that name the *set* -- `` `docs/ci/agent-gates-*.patch` `` -- and those are
# describing a family rather than naming one file, so reading one as a name
# would report a file nobody claimed. `agent-gates-deep-schedule.yml` is
# excluded by the extension rather than by a list, for the same reason.
NAME = r"agent-gates-[A-Za-z0-9._-]+\.patch"

# Two spellings, because the tree uses both and they are not interchangeable.
# The backticked form is the prose one, `docs/ci/`-qualified or bare, and both
# spellings are in use -- the bare one being a table row's first cell and a
# sentence naming one specific file. It is 19 of the 53 measured at `271389d`, so
# a `docs/ci/`-only pattern would hold 64% of the population and would not see
# three of the four deliberate references at all.
BACKTICK = re.compile(r"`(?:docs/ci/)?(" + NAME + r")`")

# The link form. The same `[^:)]` guard `check_doc_links` uses, so a URL is not
# read as a repository-relative path; the *name* is the last component of the
# target, because both links on this tree are `../ci/<name>` from inside
# `docs/findings/` and name the same files the `docs/ci/`-qualified spellings do.
LINK = re.compile(r"\]\(([^:)]+\.patch)\)")

KIND_NAME, KIND_LINK = "name", "link"

# What one run found. A namedtuple rather than a dict so that a field added
# without a reader is a TypeError at construction rather than a `KeyError`
# somewhere a reader is not looking.
Result = collections.namedtuple(
    "Result",
    "refs links files link_files patches stale uncited absent uncited_keys "
    "dead missing")

# A checkout carries directories that are not prose. `.git` is the exclusion
# `tools/test_readme_suite_table.discover` makes and for the same reason: a file
# a build left behind is not a sentence a reader read.
SKIP = {".git"}


def _glob(root, pattern):
    return {p.relative_to(root).as_posix() for p in root.glob(pattern)
            if not set(p.relative_to(root).parts) & SKIP}


def reference_files(root):
    """The reference set as (prose, prepared): the two halves, each sorted.

    Two lists rather than one because two verdicts are computed over different
    halves of it, and the difference is the whole of the `HISTORICAL` liveness
    rule -- see `scan`. `docs/findings/doc-patch-ref-file-sets.md` has why the
    set is those two globs and what a third one would have to answer for.
    """
    return sorted(_glob(root, PROSE_GLOB)), sorted(_glob(root, PREPARED_GLOB))


def markdown_files(root):
    """The prose half of `reference_files`, root-relative, sorted.

    Recomputed per call rather than cached at import, so a case can point it at
    a scratch tree -- which is what makes the rename case below possible at all.
    """
    return reference_files(root)[0]


def references(text):
    """Every patch name `text` names, as (kind, name, line) in reading order.

    Both patterns run over every line and the hits are sorted by position, so a
    line naming a file twice is reported twice in the order it was written
    rather than in the order the two regexes happened to finish.
    """
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        hits = [(m.start(), KIND_NAME, m.group(1))
                for m in BACKTICK.finditer(line)]
        hits += [(m.start(), KIND_LINK, PurePosixPath(m.group(1)).name)
                 for m in LINK.finditer(line)]
        out += [(kind, name, number) for _at, kind, name in sorted(hits)]
    return out


def read_refs(root):
    """Every reference under `root`, as (file, kind, name, line)."""
    prose, prepared = reference_files(root)
    return [(rel, kind, name, line)
            for rel in prose + prepared
            for kind, name, line in
            references((root / rel).read_text(encoding="utf-8"))]


def on_disk(root):
    """The prepared changes in `root/docs/ci`, as bare names.

    Bare names, because that is what both spellings resolve to and what the
    report prints.

    The glob is over `.patch` and `PREPARED_NON_PATCH` is added beside it, and
    only when the file is there. That conditional is what keeps `uncited`
    meaning "a prepared change that is on disk and nothing names it": a
    `mini_tree` fixture holding one synthetic patch and no yml has to stay
    green, or every synthetic case in this file and its suite would be
    reporting the yml as uncited on a tree that never had it.
    """
    ci = root / "docs" / "ci"
    if not ci.is_dir():
        return []
    return sorted({p.name for p in ci.glob("agent-gates-*.patch")}
                  | {n for n in PREPARED_NON_PATCH if (ci / n).is_file()})


def scan(root):
    """A `Result` for one tree.

    The subject is a root rather than a `docs/ci` path, so a scratch copy is
    scanned with the same call the committed tree is and no rule below knows
    which tree it is on.
    """
    prose, prepared = reference_files(root)
    by_file = {rel: (root / rel).read_text(encoding="utf-8")
               for rel in prose + prepared}
    prose_refs = [(rel, kind, name, line)
                  for rel in prose
                  for kind, name, line in references(by_file[rel])]
    refs = prose_refs + [(rel, kind, name, line)
                         for rel in prepared
                         for kind, name, line in references(by_file[rel])]

    disk = set(on_disk(root))
    cited = {name for _f, _k, name, _l in refs}

    # The `HISTORICAL` half of the enumeration is read over *prose only*, and
    # this is the one place where the widened set and the narrower one part
    # company. `docs/ci/agent-gates-capture-claims.patch` names the deleted
    # patch in its own header, so with liveness over the whole set that one
    # header would satisfy "still cited" by itself and every markdown
    # reference to the key could be deleted with nothing going red -- the
    # exemption would keep its place on the strength of a diff of a file that
    # is itself about the key. Staleness below *is* over the whole set,
    # because a name a patch header no longer matches is just as stale as one
    # a sentence no longer matches.
    prose_cited = {name for _f, _k, name, _l in prose_refs}

    # A prepared change that is not a patch is cited by a coarser test than a
    # patch is, and over a narrower set. `NAME` ends in `\.patch` on purpose,
    # so this name is never parsed as a reference and the citation is the name
    # appearing at all -- in prose, and only in prose.
    #
    # Prose only, because the widened set is not a set of citations. The one
    # place `docs/ci/agent-gates-capture-claims.patch` names this file is a
    # `+` line at :197 -- a comment the patch *adds* to a Python file, not a
    # header of its own naming a sibling. Counting it would let a diff body
    # sustain the liveness of a prepared change whose every real citation had
    # been deleted, which is a false negative produced by a phantom rather than
    # a false positive a reader can see. The two patch-name references the
    # widened set does pick up are both `#` header lines, so nothing else
    # here is affected; `docs/findings/doc-patch-ref-file-sets.md` records the
    # diff-body caveat as the realised case rather than a hypothetical one.
    for name in PREPARED_NON_PATCH:
        if any(name in by_file[rel] for rel in prose):
            cited.add(name)

    # A name is stale when it resolves to nothing in `docs/ci/` and is not one
    # of the names the docstring says prose names on purpose. That clause is
    # the exemption and it is the *only* one: a fourth absent name is refused
    # here rather than needing a fourth entry, so the exemption cannot widen by
    # accident.
    stale = [(rel, line, name) for rel, _k, name, line in refs
             if name not in disk and name not in HISTORICAL]

    # A prepared change on disk that nothing this check reads names is one
    # nobody can find -- the mirror of a stale name, and the half that broke in
    # the sibling suite.
    uncited = sorted(disk - cited)

    # And the named prepared change that is *not* there. The same
    # both-directions arrangement `HISTORICAL` has: a rename or a delete of the
    # yml is invisible to a glob that no longer matches it, so the written-down
    # expectation is compared against discovery here rather than left to a
    # reader who already knows the file was there.
    missing = sorted(n for n in PREPARED_NON_PATCH if n not in disk)

    # The enumeration read in both directions, so `check` can say whether a key
    # is still doing the work it was added for rather than only whether it is
    # still being tolerated. A key that has stopped being absent -- a patch
    # reappearing under that name -- or stopped being cited is dead weight, and
    # a reader who cannot see that from a green run has no way to notice it.
    return Result(
        refs=[r for r in refs if r[1] == KIND_NAME],
        links=[r for r in refs if r[1] == KIND_LINK],
        files=sorted({rel for rel, k, _n, _l in refs if k == KIND_NAME}),
        link_files=sorted({rel for rel, k, _n, _l in refs if k == KIND_LINK}),
        patches=sorted(disk),
        stale=stale,
        uncited=uncited,
        absent=sorted(n for n in HISTORICAL if n not in disk),
        uncited_keys=sorted(n for n in HISTORICAL if n not in prose_cited),
        dead=[n for n in sorted(HISTORICAL)
              if n in disk or n not in prose_cited],
        missing=missing,
    )


def report(result, verbose=False):
    """Print every disagreement and return how many there were.

    The stale half and the uncited half are counted separately rather than
    folded in, because a reader who fixed the first has not fixed the second
    and the two want opposite edits. The `dead` half is counted separately from
    both again: it is a property of this tool's own enumeration, and it is not
    something an edit to any markdown file can fix. The `missing` half is a
    fourth of the same kind -- also this tool's own enumeration, also not
    something an edit to prose can fix, and also a `git rm` rather than a
    sentence.
    """
    for rel, line, name in result.stale:
        if verbose:
            print(f"STALE: {rel}:{line}: names `{name}`, which is not in "
                  f"docs/ci/ and is not a historical name")
        else:
            print(f"STALE: {name} <- {rel}")
    for name in result.uncited:
        print(f"UNCITED: docs/ci/{name} is on disk and nothing this check "
              f"reads names it")
    for name in result.dead:
        why = ("a patch by that name is back on disk"
               if name in result.patches else
               "no markdown file names it any more")
        print(f"DEAD KEY: `{name}` is in HISTORICAL and {why}, so the "
              f"exemption is not earning its place")
    for name in result.missing:
        print(f"MISSING: docs/ci/{name} is in PREPARED_NON_PATCH and is not "
              f"there, so a rename or a delete of it is invisible to the glob")

    total = (len(result.stale) + len(result.uncited) + len(result.dead)
             + len(result.missing))
    if total:
        print(f"{total} problem(s): {len(result.stale)} stale reference(s), "
              f"{len(result.uncited)} uncited prepared change(s), "
              f"{len(result.dead)} dead historical key(s), "
              f"{len(result.missing)} missing prepared change(s)", file=sys.stderr)
    return total


def population(result):
    """The measured line, printed whether or not anything was found.

    The two historical-key directions are in the line rather than only in the
    verdict, because a key that has stopped being absent or stopped being cited
    is the one failure here whose cause is not visible in a reader's own file:
    nothing in the prose changed, the exemption just quietly stopped applying.
    The named prepared change's two directions are in the line for the same
    reason, and this line is the figure to re-derive rather than any count
    written in a document beside it.
    """
    return (f"{len(result.refs)} name reference(s) in {len(result.files)} "
            f"file(s), {len(result.links)} link(s) in "
            f"{len(result.link_files)} file(s); "
            f"{len(HISTORICAL)} historical key(s), {len(result.absent)} still "
            f"absent and {len(HISTORICAL) - len(result.uncited_keys)} still "
            f"cited; {len(result.patches)} prepared change(s) in docs/ci/, "
            f"{len(PREPARED_NON_PATCH) - len(result.missing)} of "
            f"{len(PREPARED_NON_PATCH)} named non-patch one(s) there")


@contextlib.contextmanager
def mini_tree(files):
    """A scratch tree holding `docs/ci/` empty and `files`, keyed by path.

    For the synthetic cases, where the point is that *this* sentence is the only
    one naming *that* name, and a copy of the committed tree would put every
    other reference in the same run and make the finding unreadable.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "docs" / "ci").mkdir(parents=True)
        for rel, text in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        yield root


@contextlib.contextmanager
def scratch_tree():
    """A throwaway copy of the committed tree's markdown and its `docs/ci`.

    For the case that needs a real population to perturb: renaming a patch has
    to go red on *every* reference to it, and that is a claim about this tree's
    53 references rather than about two lines of fixture. Nothing here writes to
    the committed tree.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ci = root / "docs" / "ci"
        ci.mkdir(parents=True)
        for path in sorted(CI.iterdir()):
            if path.is_file():
                shutil.copy2(path, ci / path.name)
        for rel in markdown_files(REPO):
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / rel, target)
        yield root


def self_test():
    """The refusals, on synthetic text and on a `tempfile` copy of the tree.

    An oracle never recorded from this tool: a self-test that derives its
    expectation from the code it is testing asserts nothing, which is the note
    `disasm8051.self_test` and `verify_gap_text.self_test` both make about their
    own digests.
    """
    ok = True

    def assert_that(cond, what):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", what))
        ok = ok and bool(cond)

    def quiet(fn, *argv, **kwargs):
        """Run a reporting function and keep its transcript off the self-test's.

        The printing is exercised, not asserted: what a reader needs to see is
        the verdict, and a refusal's own wording is the docstring's subject.
        Returns the stdout the call produced, for the one case that is about it.
        """
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            rc = fn(*argv, **kwargs)
        return sink.getvalue(), rc

    # The parse, on both spellings and on the two shapes that must not be names.
    text = "\n".join([
        "qualified: `docs/ci/agent-gates-capture-claims.patch`, and bare:",
        "`agent-gates-testdata-row-claims.patch`, on one line",
        "the set itself: `docs/ci/agent-gates-*.patch`",
        "a link: [the patch](../ci/agent-gates-gap-text-check.patch)",
        "a sibling that is not a patch: `docs/ci/agent-gates-deep-schedule.yml`",
    ])
    found = references(text)
    assert_that([(k, n) for k, n, _l in found]
                == [(KIND_NAME, "agent-gates-capture-claims.patch"),
                    (KIND_NAME, "agent-gates-testdata-row-claims.patch"),
                    (KIND_LINK, "agent-gates-gap-text-check.patch")],
                "both spellings are read, the bare one included, and a link is "
                "a link")
    assert_that(len(found) == 3,
                "three references on that text, so neither the glob-shaped span "
                "nor the `.yml` sibling contributed one -- the `*` is outside "
                "the character class and the extension is part of the pattern")

    # One line in both spellings is two references, not one. The only link in
    # the committed tree is written this way -- a backticked path that is also
    # the link's text -- and the population line is the arithmetic that has to
    # come out right, so the shape is pinned rather than left to whichever
    # pattern runs first.
    both = references("x [`agent-gates-a.patch`](../ci/agent-gates-a.patch)")
    assert_that([k for k, _n, _l in both] == [KIND_NAME, KIND_LINK],
                "a line carrying one name in both spellings is two references, "
                "in the order they were written")

    # A synthetic absent name: refused, and reported with both the name and the
    # file that named it, because a reader fixes one and needs the other.
    with mini_tree({"docs/note.md":
                    "a name that is not there: `agent-gates-never-existed.patch`\n",
                    "docs/ci/agent-gates-a.patch": "a patch\n"}) as root:
        result = scan(root)
        assert_that([(n, rel) for rel, _l, n in result.stale]
                    == [("agent-gates-never-existed.patch", "docs/note.md")],
                    "an absent name is stale and the finding carries the name "
                    "and the citing file")
        assert_that(quiet(check_mode, result)[1] == 1, "and the run is red")

    # A second absent name is refused the same way. `HISTORICAL` is an explicit
    # enumeration and a name outside it is stale, which is the whole of the "the
    # exemption cannot widen silently" claim: there is no path that admits a
    # name the enumeration does not hold, whatever its width. Both names here
    # are absent from a `docs/ci/` holding one patch, and the second is the
    # "fourth" one the issue asks about.
    with mini_tree({"docs/note.md":
                    "`agent-gates-a.patch`\n`agent-gates-b.patch`\n",
                    "docs/ci/agent-gates-a.patch": "a patch\n"}) as root:
        result = scan(root)
        assert_that([n for _rel, _l, n in result.stale] == ["agent-gates-b.patch"],
                    "one of the two is on disk and one is not: only the absent "
                    "one is stale")
        assert_that(result.uncited == [],
                    "the live direction is the other half of the same run, and "
                    "the patch that is on disk is cited, so nothing is uncited")

    # The mirror failure: a patch on disk that nothing names.
    with mini_tree({"docs/note.md": "no names here\n",
                    "docs/ci/agent-gates-a.patch": "a patch\n"}) as root:
        result = scan(root)
        assert_that(result.uncited == ["agent-gates-a.patch"],
                    "a patch nobody can find is reported -- the direction that "
                    "broke in test_readme_suite_table.py")
        assert_that(quiet(check_mode, result)[1] == 1, "and it is red")

    # `--verbose` names the line, and the default does not.
    with mini_tree({"docs/one.md": "first line\n`agent-gates-gone.patch`\n",
                    "docs/ci/agent-gates-a.patch": "a patch\n"}) as root:
        result = scan(root)
        plain, _ = quiet(report, result)
        loud, _ = quiet(report, result, verbose=True)
        assert_that("STALE: agent-gates-gone.patch <- docs/one.md" in plain
                    and "docs/one.md:2:" not in plain,
                    "the default report names the name and the citing file")
        assert_that("docs/one.md:2: names `agent-gates-gone.patch`" in loud,
                    "and --verbose names the line it is on")

    print()

    # The rename case, on a copy of the committed tree. This is what the issue's
    # "done" clause is about: delete or fold a fourth patch and the check goes
    # red for *every* reference to it rather than the first.
    with scratch_tree() as root:
        target = "agent-gates-0751-self-test.patch"
        before = scan(root)
        assert_that(target in before.patches,
                    "the copied tree holds %s to rename" % target)
        (root / "docs" / "ci" / target).rename(
            root / "docs" / "ci" / "agent-gates-renamed.patch")
        after = scan(root)
        citing = [(rel, line) for rel, _k, n, line in read_refs(root)
                  if n == target]
        assert_that({n for _r, _l, n in after.stale} == {target},
                    "renaming it makes every reference in the files this check "
                    "reads to that name stale, and nothing else stale")
        assert_that([(rel, line) for rel, line, _n in after.stale] == citing,
                    "and every one of them is reported, in the order the tree "
                    "holds them -- a check that stopped at the first would leave "
                    "the rest to the manual sweep this exists to end. The count "
                    "is deliberately not printed here: it is a count of "
                    "references to the target *in whatever tree this was run "
                    "on*, so pasting this line into a document would add one and "
                    "make the next run read higher. "
                    "`test_doc_patch_refs.py` is where the shape is pinned, and "
                    "it pins it without a number too.")
        assert_that(quiet(report, after)[1] == len(citing) + 1,
                    "and the run is red: the stale references plus the renamed "
                    "file, which is now uncited")
        assert_that(not before.stale and not before.uncited and not before.dead,
                    "while the copy before the rename is clean, so the red is "
                    "the rename's and not the copy's")

    print()

    # The enumeration, in both directions, on that same copy. A key that has
    # stopped being absent -- a patch reappearing under a historical name -- and
    # a key that has stopped being cited are the two ways an exemption rots
    # without anybody touching the prose, and both are refusals here rather than
    # notes, because a check that keeps accepting an exemption it no longer
    # needs is the thing this repository keeps writing suites about.
    # Both directions for *every* key rather than for two of them by position:
    # #1033 widened the enumeration, and a loop over `sorted(HISTORICAL)[0]` and
    # `[1]` would have left the new key with no case here at all while reading
    # exactly as before.
    for name in sorted(HISTORICAL):
        for mutate in ("restored", "un-cited"):
            with scratch_tree() as root:
                if mutate == "restored":
                    (root / "docs" / "ci" / name).write_text("a patch\n",
                                                             encoding="utf-8")
                else:
                    # Edit the reference away rather than the file, because that
                    # is the direction a real edit takes.
                    for rel in markdown_files(root):
                        path = root / rel
                        text = path.read_text(encoding="utf-8")
                        if name in text:
                            path.write_text(text.replace(name, "a name retired"),
                                            encoding="utf-8")
                result = scan(root)
                assert_that(result.dead == [name]
                            and quiet(check_mode, result)[1] == 1,
                            "`%s` is refused when it is %s: the exemption has "
                            "stopped earning its place, and the failure names "
                            "the key rather than counting it"
                            % (name, mutate))

    print()

    # The named non-patch prepared change, in both directions, on the committed
    # tree first and then on a copy. The glob over `.patch` does not match it,
    # so without these two the seventh prepared change in `docs/ci/` is on disk
    # with nothing holding either half of it.
    for name in sorted(PREPARED_NON_PATCH):
        assert_that(name in on_disk(REPO) and name not in scan(REPO).uncited,
                    "`%s` is a prepared change in docs/ci/ and something names "
                    "it -- the live direction, held for a file the `.patch` "
                    "glob cannot see" % name)

        with scratch_tree() as root:
            (root / "docs" / "ci" / name).unlink()
            gone = scan(root)
            assert_that(gone.missing == [name] and gone.uncited == [],
                        "and deleting it is refused: the missing-entry verdict "
                        "names the file rather than counting it, and a glob "
                        "that stopped matching it is not a clean tree")
            assert_that(quiet(check_mode, gone)[1] == 1, "and the run is red")

        # The citation half, stripped the way a real edit takes it: the name
        # out of every prose file that has it. Prose and not the whole declared
        # set, because the one place a `.patch` names this file is a `+`
        # diff-body line -- see `scan`.
        with scratch_tree() as root:
            (root / "docs" / "ci" / name).write_text("a\n", encoding="utf-8")
            for rel in markdown_files(root):
                path = root / rel
                text = path.read_text(encoding="utf-8")
                if name in text:
                    path.write_text(text.replace(name, "a retired change"),
                                    encoding="utf-8")
            stripped = scan(root)
            assert_that(stripped.uncited == [name] and not stripped.missing,
                        "and stripping every prose citation of it is refused "
                        "the other way: it is on disk and nothing names it, "
                        "which is the mirror of a stale name")
            assert_that(quiet(check_mode, stripped)[1] == 1, "and red again")

    print()

    # A citation from a diff body does not sustain the liveness of a
    # historical key, which is what keeps the widened reference set from
    # making "still cited" satisfy itself. The one non-prose reference to the
    # deleted patch in this tree is a bare mention in a patch header, so the
    # case has to write the parsed spelling to have anything to hold.
    with scratch_tree() as root:
        key = "agent-gates-testdata-index.patch"
        header = root / "docs" / "ci" / "agent-gates-capture-claims.patch"
        header.write_text("# a prepared change citing `" + key + "`\n",
                          encoding="utf-8")
        assert_that(("docs/ci/agent-gates-capture-claims.patch", 1) in
                    {(rel, line) for rel, _k, _n, line in read_refs(root)},
                    "a backticked name in a prepared change's own header is a "
                    "reference, which is the class a prose grep cannot see -- "
                    "asserted on the file it came from, because this key is "
                    "named in the tree's prose too and asserting the name alone "
                    "would pass on that and pin nothing")
        for rel in markdown_files(root):
            path = root / rel
            text = path.read_text(encoding="utf-8")
            if key in text:
                path.write_text(text.replace(key, "a retired name"),
                                encoding="utf-8")
        result = scan(root)
        assert_that(result.uncited_keys == [key] and result.dead == [key],
                    "and with every markdown citation gone the key is still "
                    "reported dead: the liveness half is read over prose, so a "
                    "patch's own header cannot keep the exemption alive on its "
                    "own and the references could have been deleted unnoticed")

    print()

    # resolved; it is a tree this tool read nothing in, and the two must not read
    # alike from an exit code.
    with mini_tree({"docs/note.md": "nothing here\n"}) as root:
        result = scan(root)
        assert_that(not result.refs and not result.links,
                    "a tree with no markdown naming a patch is found empty")
        assert_that(quiet(check_mode, result)[1] == 1,
                    "and --check exits non-zero on it, so 'found nothing' "
                    "cannot be read as 'found nothing wrong'")

    print()

    # The committed tree, measured rather than asserted. No count is compared,
    # per the docstring: the assertions are that it is not empty and that it is
    # clean, which are properties of the tree rather than of this tool.
    live = scan(REPO)
    assert_that(live.refs and live.patches,
                "the committed tree is not empty: %d name reference(s) in %d "
                "file(s) and %d prepared change(s) in docs/ci/"
                % (len(live.refs), len(live.files), len(live.patches)))
    # No count here, per the docstring's own rule applied to itself: this
    # assertion read `len(live.links) == 2`, pinned against
    # `xdata-census-self-test-gate.md` (#777) and `pin-table-row-reconciliation.md`
    # (#942), and every later merge that added a link turned it red. The tree
    # moved; the assertion did not. Non-emptiness is the claim that is true of
    # the tree rather than of this tool, and the names stay in the message so a
    # reader who emptied the set is told which ones went.
    assert_that(live.links and live.link_files,
                "and the markdown links onto a patch are found: %s"
                % ", ".join(live.link_files))
    assert_that(not live.stale and not live.uncited and not live.dead,
                "and the committed tree is clean")

    print()
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def check_mode(result, verbose=False):
    """The `--check` verdict for one `Result`: 0 clean, 1 otherwise.

    A run that located nothing fails, separately from the disagreements.
    Without that clause an empty tree is a perfect score, and so is a `docs/ci`
    that stopped being a directory or a pattern that stopped matching -- the
    three ways this check goes quiet are the ones a green run cannot see.
    Every verdict `report` counts is part of the total this returns, the
    `missing` one included.
    """
    if not result.refs and not result.links:
        print("found no patch reference at all: the population is empty, which "
              "is a broken discovery rather than a clean tree", file=sys.stderr)
        return 1
    return 1 if report(result, verbose) else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail on a stale reference, an uncited prepared "
                         "change, a dead historical key or a named prepared "
                         "change that is not there (the default, and the gate's "
                         "entry point)")
    ap.add_argument("--self-test", action="store_true",
                    help="the refusals, on synthetic text and on a tempfile "
                         "copy of the committed tree")
    ap.add_argument("--verbose", action="store_true",
                    help="name the line each stale reference is on")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    result = scan(REPO)
    # The scope and the population print on every run, before the verdict, the
    # way `tools/run-tests.sh` prints what it ran: a reader holding only the exit
    # code should still be able to tell a clean tree from a discovery that
    # matched nothing. The scope names the declared set rather than saying
    # "every", because the set is a decision -- `REFERENCE_GLOBS` is two globs,
    # and a reader who widens it has to know there was a width to widen.
    print(f"every reference in the declared set ("
          f"{', '.join('`%s`' % g for g in REFERENCE_GLOBS)}) under the "
          f"repository root, patch names against docs/ci/, "
          f"{len(HISTORICAL)} historical key(s) exempt and "
          f"{len(PREPARED_NON_PATCH)} named non-patch prepared change(s) held "
          f"both ways")
    print(population(result))
    return check_mode(result, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
