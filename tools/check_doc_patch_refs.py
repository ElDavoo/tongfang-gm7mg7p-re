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

**Scope, and why it stops at this prefix.** The subject is the
`docs/ci/agent-gates-*.patch` set, and the check is scoped to it: a bare `*.patch`
would sweep in `evidence/ec-reencode/2026-09-23-sdas8051-rowdiff.csv` and the
version matrix beside it, which cite a run artefact that is legitimately a
snapshot rather than a file in this tree.

**The historical rule, which is the whole design problem here.** Two names are
in prose and deliberately not on disk, and a naive "every name resolves" rule
false-positives on all four references to them:

  * `agent-gates-testdata-index.patch` -- the file as it was, named in
    `docs/findings/prepared-gate-patches.md`'s measured-results table row and in
    the paragraph under it, and in `docs/findings.md` §43 describing the
    collision the fold resolved.
  * `agent-gates-claims-and-testdata.patch` -- the alternative reading #745
    rejected and left out on purpose, named in that same write-up.

`HISTORICAL` below is that opt-out, keyed on the patch **name** and enumerated
here rather than marked in the prose. The alternative the issue offers -- a
fenced or quoted span at each reference -- was not taken, and the reason is
recorded in `docs/findings/doc-patch-reference-gate.md`: three of the four are
records, and `CLAUDE.md` §4a-4d says a superseded claim stays visible with a
correction beside it rather than reshaped so a checker can see it. The bound is
stated rather than hidden: any *new* reference to one of these two names is
exempt by construction. It is two names wide, and both directions are held --
each key is still absent from `docs/ci/`, and still cited by at least one
markdown file -- so neither a patch reappearing under that name nor a reference
being edited away can leave the exemption quietly true.

**The live direction is checked too, mirroring the sibling:** every patch in
`docs/ci/` must be cited by at least one markdown file. A human adding a sixth
prepared patch and documenting it nowhere is the mirror failure, and it is the
half that broke in `test_readme_suite_table.py`.

**What this does not check.** It resolves a *name* against a directory. It does
not read a reference's surrounding sentence to decide whether that sentence is
instructing a `git apply` or describing history -- `HISTORICAL` stands in for
that at name granularity, and the cost of getting it wrong is a false positive a
reader can see and an edit to make. It also does not check the `.py` population:
`tools/test_agent_gates_patches.py` names the deleted patch in three further
places, and widening the scan to `*.py` would put this tool inside a file issue
#772 owns.

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

# The two names prose names on purpose; see the docstring. The write-up beside
# this tool records why this is an enumeration rather than a per-reference
# opt-out, and what the choice costs.
HISTORICAL = {
    "agent-gates-testdata-index.patch",
    "agent-gates-claims-and-testdata.patch",
}

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
    "refs links files link_files patches stale uncited absent uncited_keys dead")

# A checkout carries directories that are not prose. `.git` is the exclusion
# `tools/test_readme_suite_table.discover` makes and for the same reason: a file
# a build left behind is not a sentence a reader read.
SKIP = {".git"}


def markdown_files(root):
    """Every `*.md` under `root`, root-relative, sorted.

    Recomputed per call rather than cached at import, so a case can point it at
    a scratch tree -- which is what makes the rename case below possible at all.
    """
    return sorted(p.relative_to(root).as_posix()
                  for p in root.rglob("*.md")
                  if not set(p.relative_to(root).parts) & SKIP)


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
    out = []
    for rel in markdown_files(root):
        text = (root / rel).read_text(encoding="utf-8")
        out += [(rel, kind, name, line)
                for kind, name, line in references(text)]
    return out


def on_disk(root):
    """The `agent-gates-*.patch` files in `root/docs/ci`, as bare names.

    Bare names, because that is what both spellings resolve to and what the
    report prints. `agent-gates-deep-schedule.yml` is not matched and is not a
    patch, which is what `docs/findings/prepared-gate-patches.md` records about
    it and the reason this is a glob over `.patch` rather than over everything.
    """
    ci = root / "docs" / "ci"
    if not ci.is_dir():
        return []
    return sorted(p.name for p in ci.glob("agent-gates-*.patch"))


def scan(root):
    """A `Result` for one tree.

    The subject is a root rather than a `docs/ci` path, so a scratch copy is
    scanned with the same call the committed tree is and no rule below knows
    which tree it is on.
    """
    disk = set(on_disk(root))
    refs = read_refs(root)
    cited = {name for _f, _k, name, _l in refs}

    # A name is stale when it resolves to nothing in `docs/ci/` and is not one of
    # the two the docstring says prose names on purpose. That second clause is
    # the exemption and it is the *only* one: a fourth absent name is refused
    # here rather than needing a fourth entry, so the exemption cannot widen by
    # accident.
    stale = [(rel, line, name) for rel, _k, name, line in refs
             if name not in disk and name not in HISTORICAL]

    # A patch on disk that no markdown file names is a prepared change nobody
    # can find -- the mirror of a stale name, and the half that broke in the
    # sibling suite.
    uncited = sorted(disk - cited)

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
        uncited_keys=sorted(n for n in HISTORICAL if n not in cited),
        dead=[n for n in sorted(HISTORICAL)
              if n in disk or n not in cited],
    )


def report(result, verbose=False):
    """Print every disagreement and return how many there were.

    The stale half and the uncited half are counted separately rather than
    folded in, because a reader who fixed the first has not fixed the second
    and the two want opposite edits. The `dead` half is counted separately from
    both again: it is a property of this tool's own enumeration, and it is not
    something an edit to any markdown file can fix.
    """
    for rel, line, name in result.stale:
        if verbose:
            print(f"STALE: {rel}:{line}: names `{name}`, which is not in "
                  f"docs/ci/ and is not a historical name")
        else:
            print(f"STALE: {name} <- {rel}")
    for name in result.uncited:
        print(f"UNCITED: docs/ci/{name} is on disk and no markdown file names it")
    for name in result.dead:
        why = ("a patch by that name is back on disk"
               if name in result.patches else
               "no markdown file names it any more")
        print(f"DEAD KEY: `{name}` is in HISTORICAL and {why}, so the "
              f"exemption is not earning its place")

    total = len(result.stale) + len(result.uncited) + len(result.dead)
    if total:
        print(f"{total} problem(s): {len(result.stale)} stale reference(s), "
              f"{len(result.uncited)} uncited patch(es), "
              f"{len(result.dead)} dead historical key(s)", file=sys.stderr)
    return total


def population(result):
    """The measured line, printed whether or not anything was found.

    The two historical-key directions are in the line rather than only in the
    verdict, because a key that has stopped being absent or stopped being cited
    is the one failure here whose cause is not visible in a reader's own file:
    nothing in the prose changed, the exemption just quietly stopped applying.
    """
    return (f"{len(result.refs)} name reference(s) in {len(result.files)} "
            f"markdown file(s), {len(result.links)} link(s) in "
            f"{len(result.link_files)} file(s); "
            f"{len(HISTORICAL)} historical key(s), {len(result.absent)} still "
            f"absent and {len(HISTORICAL) - len(result.uncited_keys)} still "
            f"cited; {len(result.patches)} patch(es) in docs/ci/")


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

    # A second absent name is refused the same way. `HISTORICAL` is two wide and
    # a name outside it is stale, which is the whole of the "the exemption
    # cannot widen silently" claim: there is no path that admits a third. Both
    # names here are absent from a `docs/ci/` holding one patch, and the second
    # is the "fourth" one the issue asks about.
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
                    "renaming it makes every reference to that name stale and "
                    "nothing else stale")
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
    for name, mutate in (
        (sorted(HISTORICAL)[0], "restored"),
        (sorted(HISTORICAL)[1], "un-cited"),
    ):
        with scratch_tree() as root:
            if mutate == "restored":
                (root / "docs" / "ci" / name).write_text("a patch\n",
                                                         encoding="utf-8")
            else:
                # Edit the reference away rather than the file, because that is
                # the direction a real edit takes.
                for rel in markdown_files(root):
                    path = root / rel
                    text = path.read_text(encoding="utf-8")
                    if name in text:
                        path.write_text(text.replace(name, "a name retired"),
                                        encoding="utf-8")
            result = scan(root)
            assert_that(result.dead == [name] and quiet(check_mode, result)[1] == 1,
                        "`%s` is refused when it is %s: the exemption has "
                        "stopped earning its place, and the failure names the "
                        "key rather than counting it" % (name, mutate))

    print()

    # The found-nothing refusal. An empty tree is not a tree in which every name
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
                "file(s) and %d patch(es) in docs/ci/"
                % (len(live.refs), len(live.files), len(live.patches)))
    # 2, not the 1 this branch was written against: #777 added the link in
    # `xdata-census-self-test-gate.md` and #942 added the one in
    # `pin-table-row-reconciliation.md`, so the merged tree carries both.
    assert_that(len(live.links) == 2 and live.link_files,
                "and the two markdown links onto a patch are found: %s"
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
                    help="fail on a stale reference, an uncited patch or a dead "
                         "historical key (the default, and the gate's entry "
                         "point)")
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
    # matched nothing.
    print(f"every `*.md` under the repository root, patch names against "
          f"docs/ci/, {len(HISTORICAL)} historical key(s) exempt")
    print(population(result))
    return check_mode(result, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
