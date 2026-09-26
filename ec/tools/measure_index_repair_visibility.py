#!/usr/bin/env python3
"""Measure what the two testdata checkers do over a hand-repair's *before* tree.

The index has been repaired by hand twice, in #502 and #720, and both repairs
were to a row's third column -- the description. Every sentence in the corpus
that repeated the fact also repeated the same disclaimer with it: nobody has
run `check_testdata_row_claims.py` or `check_testdata_index.py` over the tree
as it stood before either repair, so whether the checks were red there is
unknown. This tool runs them over it and prints the answer.

**What is measured, and the four limits that bound it.** None of them is a
"this would have caught them", and the first is the one a reader has to hold:

  * *Today's checker, over the old prose.* Neither `check_testdata_row_claims.py`
    nor `check_testdata_index.py` existed at either revision, so there is no
    version of either to run. What is run is the committed one, over a
    pre-repair `root`. That is the only measurement available and its
    **direction** has to be stated with it: a checker that is red on an old
    tree may be red for a reason the old tree's own author would have called
    correct, and one that is green says only that this rule over this text is
    green. The reverse direction is not available and is not claimed.
  * *Only `root` moves.* The `functions`, `registers` and `captures` a run
    reads are the module-level HEAD paths of `check_testdata_row_claims.py`
    and are left there, so a pre-repair sentence's bare date resolves against
    HEAD's `evidence/ec-watch/`. The extraction puts an old `ec/tools` on disk
    only to give the `Feeds` column something to resolve against; **no file
    out of the extracted tree is ever executed or imported** -- the checker is
    this working tree's, and the corpus the extracted one.
  * *An unrunnable row is a stated limit, not a negative result.* If the repair
    also added or renamed the fixture its row names, every claim in that row
    fails for the uninteresting reason that the row resolves to nothing. Such
    a row is reported as "not runnable at that revision, because ..." and its
    claims are never folded into the `missing` count.
  * *A full clone is required*, as for `verify_reassembly.py --verify-provenance`
    and for the reason `HISTORY_REQUIREMENT` gives. A revision that does not
    resolve is "not measurable in this clone", with the command that failed --
    never a count of zero.

**The post-repair control is what makes the number mean anything.** A red
`missing` over a pre-repair tree is only evidence if the same row is green at
the repair, so the repair revision is measured too, over its own extracted
tree, and both numbers are printed together. `verify_reassembly.py` runs its
positive control before its negative check for exactly this reason.

**`check_testdata_index.py` is a control here, not a candidate answer.** It
reads the first column, the `Feeds` column and the nested tables, and never
the third, so by construction it cannot have caught either repair. It is run
over the same two trees to convert "it would have been green through both"
from an assertion into a measurement.

**The repairs are found by content, not by a list.** `repair_rows()` compares
the two images' description cells, so it finds a third-column edit wherever it
is; naming the two commits on the command line is the only input it takes from
outside the tree. A pair of revisions whose third columns do not differ is
reported as "not found by this method", which is a different answer from a
count of zero.

Usage:
    python3 ec/tools/measure_index_repair_visibility.py --base <rev> --repair <rev>
"""
import argparse
import collections
import inspect
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

# The index checker is imported for what it got right: `table_cells()` is the
# sibling's own reader of the table, and this tool parses the index with it
# rather than growing a second reader that could come to disagree with the
# checks it is measuring. It is not a package and not importable by name from
# outside this directory, which is the same arrangement the sibling tools
# already have.
from check_testdata_index import table_cells

import check_testdata_index as ctdi
import check_testdata_row_claims as ctrc

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)

# What to extract, and why it is not `ec/tools/testdata/`.
#
# `check_testdata_index.check()` sets `tools_root = os.path.dirname(root)` and
# resolves the `Feeds` column there, so a bare `testdata/` extraction answers
# `feeds_missing` for every row of the table -- a `Feeds` miss on
# `../grade_0751_isolation.py` is a statement about the extraction, not about
# the revision, and 27 of them would bury the one number this tool exists to
# print. `ec/tools` whole is the smallest extraction that is not an artefact of
# how this file was written.
PATHS = ("ec/tools",)

# `TarFile.extractall()` grew a `filter` argument in CPython 3.12, backported
# to 3.8-3.11, and 3.14 applies `data` by default rather than warn. The
# repository pins no Python version -- `.github/actions/project-setup` only
# guarantees that `python3` exists -- so the keyword goes in where the running
# interpreter has it rather than being assumed. `data` is the right policy here
# and not only for the warning: it refuses a member whose path escapes `dest`,
# and a tar being unpacked is the one place that check earns its keep.
UNPACK = ({"filter": "data"}
          if "filter" in inspect.signature(tarfile.TarFile.extractall).parameters
          else {})

# The mode answers from the repository's own history, so how deep the clone is
# is part of its contract the way the assembler is part of
# `verify_reassembly.py --report`'s. Worded from what the workflows say today
# rather than carried over from `verify_reassembly.py`'s own copy of that
# sentence, which was written before `ci.yml` moved to a full checkout and no
# longer matches it.
HISTORY_REQUIREMENT = (
    "  This tool answers from the repository's history, so it needs a full\n"
    "  clone: `git clone` without --depth, or `git fetch --unshallow` in one\n"
    "  that is shallow. The agent stages and ci.yml both check out with\n"
    "  `fetch-depth: 0` and can resolve these revisions; a default-depth\n"
    "  checkout has neither of them, and this tool would go on to report a\n"
    "  count of zero over a tree it never read.")


def _git(*args, repo=None):
    """git, run against the repository whatever the cwd is."""
    return subprocess.run(["git", "-C", repo or REPO] + list(args),
                          capture_output=True, text=True)


def git_lines(*args, repo=None):
    """-> (lines, None) for git's non-empty output lines, or (None, why).

    Copied with attribution from `verify_reassembly.py`'s `git_lines()`, which
    is the repository's only other reader of history, and kept for the reason
    its docstring gives: **None rather than an empty list**, because an empty
    answer and a command that did not run are the two things this tool most
    needs to tell apart. Every measurement here is "git said nothing" -- a
    revision that resolved to no commit, a subject that printed nothing -- so a
    git that failed would read as a clean measurement of an empty tree.
    """
    try:
        r = _git(*args, repo=repo)
    except OSError as exc:
        return None, "git could not be run: %s" % exc
    if r.returncode != 0:
        return None, r.stderr.strip() or ("git exited %d" % r.returncode)
    return [ln for ln in r.stdout.splitlines() if ln.strip()], None


def resolve_revision(rev, repo=None):
    """-> the commit sha `rev` names, or (None, why) if this clone has no such
    commit. `^{commit}` so a branch name or a tag is measured, not a path.

    The reason always names the revision. `--quiet` is what keeps a
    not-a-commit from printing an error to stderr, which is right for a probe
    and wrong for a report: `git exited 1` says a command failed and not which
    of the two revisions it was asked about, and a reader of a report with two
    of those has nothing to act on.
    """
    command = f"git rev-parse --verify --quiet {rev}^{{commit}}"
    lines, why = git_lines("rev-parse", "--verify", "--quiet",
                           rev + "^{commit}", repo=repo)
    if lines is None:
        return None, f"{command} did not resolve ({why})"
    if not lines:
        return None, (f"{command} named no commit; this clone does not have "
                      f"it")
    return lines[0], None


def subject(rev, repo=None):
    """The one-line subject of `rev`, or None if git would not say."""
    lines, _why = git_lines("log", "-1", "--format=%s", rev, repo=repo)
    return lines[0] if lines else None


def parent(rev, repo=None):
    """The first parent of `rev`, or (None, why) -- a root commit has none, and
    that is a fact about the revision rather than about the clone."""
    return resolve_revision(rev + "^", repo=repo)


def repair_rows(before_text, after_text):
    """-> (row numbers, None) for the description cells that differ, else
    ([], why).

    The git-free core, and written to be exercised on its own for the reason
    `verify_reassembly.compare_provenance()` is: a comparison that compared
    nothing looks exactly like one that found no difference, and the committed
    pair here is a pair that differs.

    The cells are compared whole and the row numbers are counted from 1, the
    way `check_testdata_row_claims.py` counts them, so a row number in a report
    here is the row number in that tool's output. It is the **cell** that is
    compared rather than the backticked literals inside it, because a reworded
    sentence that keeps every literal is still a repair -- and reporting it as
    one, with zero literals before and after, is how a reader learns that this
    tool's number is zero for a reason that has nothing to do with addresses.

    Two images with different row counts are refused rather than aligned. Row
    numbers are positions, so with 25 rows on one side and 27 on the other
    every row past the shorter one is a different row on each side, and a list
    of "changed" rows computed by zipping them would be the positions rather
    than the repairs. That is not found by this method, and it says so.
    """
    before = table_cells(before_text, column=3)
    after = table_cells(after_text, column=3)
    if len(before) != len(after):
        return [], ("the two images have %d and %d table rows, so a row number "
                    "names a different row in each; the third-column edits are "
                    "not found by this method" % (len(before), len(after)))
    return [number for number, (a, b) in enumerate(zip(before, after), 1)
            if a != b], None


def read_index(root):
    """The text of `<root>/README.md`, or (None, why) if it is not there.

    A revision from before the index existed has no `README.md`, and that is a
    fact about the revision: reported with the path rather than raised, because
    an exception here would read as a crash rather than as "this tree cannot
    be measured".
    """
    path = os.path.join(root, "README.md")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read(), None
    except OSError as exc:
        return None, "%s: %s" % (path, exc)


def extract(rev, dest, repo=None):
    """Extract `PATHS` at `rev` into `dest`, or (False, why).

    `git archive` piped into the standard library's streaming `tarfile`, rather
    than the shell `tar` the corpus reaches for by hand
    (`docs/findings/xdata-guard-off-key-distinctness.md`): `python3` is
    guaranteed by `.github/actions/project-setup` and `tar` is declared nowhere,
    so a tool that shelled out would be runnable in one clone and not another.
    `r|` is the streaming mode, so the archive is never held whole in memory
    against a pipe that is feeding it.
    """
    try:
        proc = subprocess.Popen(["git", "-C", repo or REPO, "archive", rev]
                                + list(PATHS), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    except OSError as exc:
        return False, "git could not be run: %s" % exc
    with proc:
        try:
            with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
                archive.extractall(dest, **UNPACK)
        except tarfile.TarError as exc:
            proc.stdout.close()
            return False, "git archive %s did not read: %s" % (rev, exc)
        finally:
            if proc.stdout and not proc.stdout.closed:
                proc.stdout.close()
        why = proc.stderr.read().decode("utf-8", "replace").strip()
        if proc.wait() != 0:
            return False, why or ("git archive %s exited %d"
                                  % (rev, proc.returncode))
    return True, None


# What one run over one tree found. `claims` is `check_testdata_row_claims.py`'s
# own list, kept whole rather than re-tallied here, so a row's claim is the
# sibling's claim and this tool cannot be the place where the two disagree
# about one. The `index_*` fields are the disagreements of
# `check_testdata_index.py`, broken out rather than summed, for the same
# reason that tool reports them in four directions.
Measure = collections.namedtuple(
    "Measure", "root literals resolved missing unresolved checked "
    "claiming_rows claims shapes gaps index_missing feeds_missing "
    "nested_missing")


def measure(root):
    """A `Measure` for one testdata tree, or (None, why) if it cannot be read.

    Both checks run in-process against `root` and nothing else moves. Neither
    CLI takes a root -- `check_testdata_row_claims.main()` calls
    `check(captures=CAPTURES)` and `check_testdata_index.main()` calls
    `check(TESTDATA)`, both at the module's own HEAD paths -- so the in-process
    call is the only way to point one at a tree, which is the whole reason
    this tool exists rather than a shell line from the issue.
    """
    text, why = read_index(root)
    if text is None:
        return None, why
    try:
        claims = ctrc.check(root=root)
        index = ctdi.check(root)
    except OSError as exc:
        return None, "%s: %s" % (root, exc)
    return Measure(root, claims.literals, claims.resolved, claims.missing,
                   claims.unresolved, claims.checked, claims.claiming_rows,
                   claims.claims, claims.shapes, index.gaps, index.missing,
                   index.feeds_missing, index.nested_missing), None


def row_claim_count(text, row):
    """How many backticked address literals row `row`'s description cell holds.

    The number that explains a zero. `check_testdata_row_claims.py` reads a
    backticked `0xNNNN` as a claim and has nothing to hold when a cell carries
    none, so a row whose description names only fixture paths, mark labels and
    status words cannot go red however wrong it is about the fixture -- and a
    `missing` of 0 across a repaired row is that case unless a count says
    otherwise.

    It is counted with the sibling's own `literals()`, over the whole cell
    rather than sentence by sentence, because a cell is what the two images are
    compared on and the two counts have to be about the same thing. The shapes
    `check()` would have passed those literals over under are not applied: this
    is "how many literals the cell spells", not "how many claims it makes", and
    only the second is the sibling's to answer.
    """
    cells = table_cells(text, column=3)
    if not 1 <= row <= len(cells):
        return None
    return len(ctrc.literals(cells[row - 1]))


def row_files(text, row, root):
    """The files row `row`'s first column resolves to, at this tree.

    The runnability flag. Empty means the row names nothing that is on disk
    here, so every claim in it would fail for the uninteresting reason that
    there is no file to hold it to -- which is a stated limit on the
    measurement, never a finding about the checker.
    """
    cells = table_cells(text, column=1)
    if not 1 <= row <= len(cells):
        return []
    return ctrc.row_files(cells[row - 1], root)


def repair(base, target, repo=None, scratch=None):
    """-> (report, exit code) for the repair at `target` measured over `base`.

    `base` is the pre-repair revision and `target` the repair. The whole of the
    measurement is the two runs and the rows between them, and the report is
    the lines a write-up pastes, so it is returned rather than printed: the
    suite builds a scratch repository and reads this, and a function that
    printed its own result could only be tested through its exit code.
    """
    lines = []
    for rev, label in ((base, "pre-repair"), (target, "post-repair")):
        sha, why = resolve_revision(rev, repo=repo)
        if sha is None:
            lines.append(f"{rev}: not measurable in this clone -- {why}")
            return lines, 2
        lines.append(f"{label} revision {rev} -> {sha}")
    base_sha, _ = resolve_revision(base, repo=repo)
    target_sha, _ = resolve_revision(target, repo=repo)

    head = subject(target_sha, repo=repo)
    lines.append(f"repair: {target_sha}" + (f" -- {head}" if head else ""))

    with tempfile.TemporaryDirectory(prefix="repair-measure-",
                                     dir=scratch) as tmp:
        trees = {}
        for label, rev, sha in (("before", base, base_sha),
                                ("after", target, target_sha)):
            root = os.path.join(tmp, label, "ec", "tools", "testdata")
            os.makedirs(root, exist_ok=True)
            done, why = extract(sha, os.path.join(tmp, label), repo=repo)
            if not done:
                lines.append(f"the {label} tree at {sha} could not be extracted: "
                             f"{why}")
                return lines, 2
            found, why = measure(root)
            if found is None:
                lines.append(f"the {label} tree at {sha} could not be measured: "
                             f"{why}")
                return lines, 2
            trees[label] = (root, found, read_index(root)[0])

        # Everything below reads the extracted trees, so it is all inside the
        # `with`: the paths a report names are into a directory that stops
        # existing the moment the block closes, and a runnability flag answered
        # after that is a flag about an empty scratch tree rather than about
        # the revision.
        before, after = trees["before"], trees["after"]
        rows, why = repair_rows(before[2], after[2])
        if why:
            lines.append(why)
            return lines, 2
        if not rows:
            lines.append(f"no third-column difference between {base_sha} and "
                         f"{target_sha}: the repair is not found by this method")
            return lines, 0

        lines.append("rows whose description cell differs: "
                     + ", ".join(str(r) for r in rows))
        for row in rows:
            first = table_cells(before[2], column=1)[row - 1]
            lines.append(f"  row {row} -- {first}")
            literal_before = row_claim_count(before[2], row)
            literal_after = row_claim_count(after[2], row)
            lines.append(f"    backticked address literals in the description: "
                         f"{literal_before} before, {literal_after} after")
            files = row_files(before[2], row, before[0])
            if not files:
                # The stated limit, printed as its own thing so it cannot be
                # read as a count of zero or as a row the checker passed.
                lines.append("    not runnable at that revision, because its "
                             "first column resolved to no file on disk: every "
                             "claim in it would fail for that reason alone, "
                             "and none is counted here")
                continue
            lines.append(f"    runnable at that revision: first column "
                         f"resolved to {len(files)} file(s)")
            for label, (_root, found, _text) in (("pre-repair", before),
                                                 ("post-repair", after)):
                missed = [c for c in found.claims
                          if c.row == row and c.verdict == ctdi.MISSING]
                lines.append(f"    {label}: {len(missed)} missing claim(s) in "
                             f"this row, of {found.checked} checked over the "
                             f"whole index ({found.missing} missing tree-wide)")
                for claim in missed:
                    lines.append(f"      row {claim.row} {claim.address} "
                                 f"[{claim.files}]")

        for label, (_root, found, _text) in (("pre-repair", before),
                                             ("post-repair", after)):
            lines.append(
                f"control, {label}: {found.literals} literal(s), "
                f"{found.resolved} resolved, {found.missing} missing, "
                f"{found.unresolved} unresolved, {len(found.shapes)} passed "
                f"over")
            lines.append(
                f"control, check_testdata_index.py over the {label} tree: "
                f"{len(found.gaps)} gap(s), {len(found.index_missing)} path "
                f"miss(es), {len(found.feeds_missing)} Feeds miss(es), "
                f"{len(found.nested_missing)} nested miss(es)")
            # The token, not the sibling's `note`: `note` is the same path
            # re-based through `repo_path()`, which against a scratch tree is a
            # chain of `..` out of a temporary directory and says nothing the
            # token does not.
            for _where, token, _note in (found.index_missing
                                         + found.feeds_missing
                                         + found.nested_missing):
                lines.append(f"    not on disk at that revision: {token}")

    # The control is the check this tool can fail on. A pre-repair number with
    # a red row *after* the repair is not evidence of anything: the row would
    # have been red for a reason the repair did not remove, and the number
    # beside it would read as though it had.
    after_rows = [c for c in after[1].claims if c.row in rows
                  and c.verdict == ctdi.MISSING]
    if after_rows:
        lines.append(f"the post-repair control is red on the repaired row(s) "
                     f"({len(after_rows)} claim(s)), so the pre-repair number "
                     f"beside it is not evidence of anything; the repair did "
                     f"not move what this checker reads")
        return lines, 1
    return lines, 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True,
                    help="the revision the tree stood at *before* the repair")
    ap.add_argument("--repair", required=True,
                    help="the revision that repaired it")
    ap.add_argument("--scratch",
                    help="directory to extract under (default: a tempdir)")
    args = ap.parse_args()

    if shutil.which("git") is None:
        print("  git is not on PATH, so no revision can be resolved and "
              "nothing here is measurable.", file=sys.stderr)
        print(HISTORY_REQUIREMENT, file=sys.stderr)
        return 2
    lines, code = repair(args.base, args.repair, scratch=args.scratch)
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
