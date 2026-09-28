#!/usr/bin/env python3
"""Run `--verify-provenance` in a full clone and in a `--depth 1` clone, and
read what each printed.

The mode's answers to the two depths were, until issue #421, held only as a
prose *fragment*: `ec/tools/history_checkout_sites.py` keeps the corrected
`ci.yml` sentence by a substring of it, which proves the words are still in the
source and does not run the mode at all. The issue's own "done when" is
behavioural -- "a full-clone checkout and a `--depth 1` checkout both behave
correctly" -- and nothing in the tree was checking it. These cases are that
check, and the two halves are what the sentence is about:

  1. the control, that each scratch clone really is the depth it is made to be;
  2. a full clone resolves both revisions and reaches the `PASS` verdict
     `docs/findings.md` §14f records;
  3. a `--depth 1` clone resolves neither, exits 1, and prints
     `HISTORY_REQUIREMENT` whole rather than a fragment of it;
  4. that printed requirement **names a job and not the whole workflow** -- the
     regression #421 filed, and the one it says "matters most", because a red
     `gates` run reaches a human through this text.

**The control is first because without it case 3 passes vacuously.** A
`git fetch` that quietly fetched the whole history leaves a directory that
still answers `true` to nothing and fails to resolve nothing, and the mode
would then exit 0 in a tree this suite believes is shallow. So the depth is
read back with `git rev-parse --is-shallow-repository` rather than inferred
from the command that made the clone. It is the same discipline
`test_check_history_checkouts.py` uses by pasting the four stale sentences
verbatim rather than paraphrasing them: a control that reconstructs the thing
it is meant to check is not a control.

**What case 4 holds is the claim's shape, not its content.** The pre-#421
sentence asserted that ``a default-depth checkout -- actions/checkout's default,
which is what ci.yml uses`` -- naming a workflow and no job -- so a reader went
looking for a cause in a checkout that has the history. The positive half is
what keeps the negative from being a floor: a rewrite that dropped the `ci.yml`
claim altogether would pass `assertNotIn` while leaving the reader with no idea
which checkout to look at. But job ids here are ordinary English words, so a
sentence naming the *wrong* job passes this case too, exactly as
`docs/findings/history-checkout-claims.md` says of the quotation rule it
anchors. The content is `check_history_checkouts.py`'s and
`history_checkout_sites.py`'s subject, not this suite's.

**No case asserts a count.** The `2,705` in the mode's own output is a number
about the corpus, not a verdict on the mode, and a figure in a test is a value
every merge that moves the corpus has to edit. What is asserted is the exit
status and the shape of the answer.

**Both clones are built from the committed tree, so this is a statement about
`main` and not about the working directory.** That is deliberate -- the
corrections being checked in are committed ones, and the gate runs committed
code -- but it is a limit worth stating: a local edit to
`HISTORY_REQUIREMENT` is not what these cases measure until it is committed.
The prose in the working tree is held separately, and by value, in
`history_checkout_sites.py`.

**The full-clone half skips on a shallow runner, and a shallow runner is "not
found by this method" rather than a defect here.** `git clone` propagates a
source repository's shallow boundary, so a suite running on a `--depth 1`
checkout cannot make a full clone at all and there is no full clone to measure.
The message is the degradation and the wording verbatim, the same ones
`test_measure_index_repair_visibility.py`'s `CommittedRepairTests` uses. The
depth-1 half needs no history in the outer clone and always runs.

**Scratch clones live under `tempfile`, never in the working tree.** They are
half a gigabyte of checkout each, and `tools/run-tests.sh` prunes `.git/`,
`.claude/` and `vendor/` when it counts while `check_testdata_index.py` and
`census_test_line_pins.py` walk the tree -- a clone in the working directory is
a second checkout for all three to trip over, which is the problem those
prunings exist for.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

# The three revisions, as `.github/scripts/agent-gates.sh:160-163` runs the mode
# and as `docs/findings.md` §14f records the run. Written out rather than read
# out of that script because this suite needs them in a *different* clone than
# the one the gate runs in, and a small list of this repository's own revisions
# is not the thing a re-copy invalidates. What a re-copy does invalidate is the
# `fetch-depth: 0` the mode depends on, and that is case 2's subject.
BASE = "08b72e2"
MIGRATION = "a56b3bb"
LISTINGS_FROM = "8c7985e"

# The pre-#421 wording of the clone-depth sentence, verbatim. Held here so the
# negative in case 4 is a control that can be shown rejecting the text that was
# wrong, rather than a `not in` over a phrase a paraphrase could have softened
# into passing. `history_checkout_sites.py` holds the corrected half the same
# way, for the same reason.
STALE_CI_YML_CLAIM = "which is what ci.yml uses"

# ...and the corrected form, held for the other half of case 4. A negative alone
# would be satisfied by a rewrite that dropped the `ci.yml` claim altogether.
CORRECTED_CI_YML_CLAIM = "ci.yml's `workflows` job"

# Built once per run and shared by the cases, because each clone is a ~500 MB
# checkout of which these cases only read. Keyed by depth, and pruned by
# `tearDownModule`.
_CLONES = {}


def has_git():
    return shutil.which("git") is not None


def git(tree, *args, check=True):
    """git, run in a scratch directory.

    `check` because a clone that silently did not happen is a tree the cases
    below would then measure as something it is not, and the raise is what says
    so rather than a green run over the wrong depth.
    """
    proc = subprocess.run(["git", "-C", str(tree)] + list(args),
                          capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise AssertionError("git %s in %s failed: %s"
                             % (" ".join(args), tree, proc.stderr))
    return proc


def clone(kind):
    """A scratch clone of this repository at `kind` depth -> its path.

    `full` is `git clone` against the local path, so the objects are hardlinked
    and it costs about as much as reading the directory list. `shallow` is
    `git init` then `git fetch --depth 1 file://<repo> HEAD` then
    `git checkout FETCH_HEAD` -- `file://` because git refuses `--depth` against
    a plain local path, and the `init` + `fetch --depth 1` idiom is the one this
    repository already documents at
    `linux/patches/gm7mg7p-power-profile/README.md:38`.

    Each lives at `<mkdtemp>/clone` so `tearDownModule` can take the scratch
    tree whole rather than leaving the temp directory it made it in.
    """
    if kind not in _CLONES:
        parent = tempfile.mkdtemp(prefix="verify-provenance-%s-" % kind)
        dest = os.path.join(parent, "clone")
        if kind == "full":
            git(parent, "clone", "--quiet", str(REPO), dest)
        else:
            os.makedirs(dest)
            git(dest, "init", "--quiet")
            git(dest, "remote", "add", "origin", "file://%s" % REPO)
            git(dest, "fetch", "--quiet", "--depth", "1", "origin", "HEAD")
            git(dest, "checkout", "--quiet", "FETCH_HEAD")
        _CLONES[kind] = dest
    return _CLONES[kind]


def tearDownModule():
    for dest in _CLONES.values():
        shutil.rmtree(os.path.dirname(dest), ignore_errors=True)
    _CLONES.clear()


def is_shallow(tree):
    """`true` or `false` as the tree itself answers about its own depth."""
    return git(tree, "rev-parse", "--is-shallow-repository").stdout.strip()


def resolves(rev):
    """Whether `rev` names a commit in the clone running this suite."""
    return git(REPO, "rev-parse", "--verify", "--quiet", rev + "^{commit}",
               check=False).returncode == 0


def run_mode(tree):
    """(exit status, stdout) from one run of the mode, inside `tree`.

    `sys.executable` rather than `python3` so the run cannot pick up a
    different interpreter from the one this suite is running under, and `cwd`
    because the mode derives its repository from `__file__` -- it reads the
    history of the checkout the tool was loaded from, which is the whole
    question here, and pointing `cwd` at the same tree keeps the run honest
    about which one that is.
    """
    proc = subprocess.run(
        [sys.executable,
         os.path.join(tree, "ec", "tools", "verify_reassembly.py"),
         "--verify-provenance", "--base", BASE, "--migration", MIGRATION,
         "--listings-from", LISTINGS_FROM],
        capture_output=True, text=True, cwd=tree)
    return proc.returncode, proc.stdout


def requirement_in(tree):
    """`HISTORY_REQUIREMENT` as *that* checkout holds it.

    Read from the clone rather than imported from this working tree on purpose:
    what case 3 claims is that the mode prints this constant, and the only
    constant it can print is the one in the tree it was loaded from. Importing
    the working tree's copy instead would make the case a comparison between two
    trees, which a local edit could turn red without saying anything about the
    mode. `module_from_spec` + `exec_module` is the sibling's arrangement for
    the same reason (`test_check_history_checkouts.py`): a second module object
    for the tool, read rather than rebound.
    """
    spec = importlib.util.spec_from_file_location(
        "verify_reassembly_in_clone",
        os.path.join(tree, "ec", "tools", "verify_reassembly.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.HISTORY_REQUIREMENT


@unittest.skipUnless(has_git(), "no git on PATH")
class CloneDepthTests(unittest.TestCase):
    """The two depths, measured by running the mode rather than reading it."""

    def skip_without_history(self):
        """Skip a case that needs the clone running this suite to have history.

        Skipped rather than failed, with the degradation and the wording
        `test_measure_index_repair_visibility.py`'s `CommittedRepairTests`
        already uses for the same limit: a shallow checkout cannot answer this,
        and saying so is the correct result rather than a defect in the suite.
        """
        if not resolves(BASE):
            self.skipTest("the base revision (%s) is not in this clone; "
                          "this mode needs a full clone "
                          "(`git fetch --unshallow`)" % BASE)

    def test_the_scratch_clones_are_the_depths_this_suite_claims(self):
        """The control: each clone is read back, not assumed from its command.

        The depth-1 half is asserted unconditionally, because it is the one
        that keeps case 3 from passing vacuously and case 3 runs everywhere.
        The full half needs the history, since `git clone` propagates a source
        repository's shallow boundary and would hand back a shallow clone
        without it -- so it skips on a shallow runner rather than reporting a
        clone that was never going to be full as a broken one.
        """
        self.assertEqual(is_shallow(clone("shallow")), "true")
        self.skip_without_history()
        self.assertEqual(is_shallow(clone("full")), "false")

    def test_a_full_clone_resolves_both_revisions_and_answers(self):
        """The half the mode exists for, and the half `docs/findings.md` §14f
        records as having passed by hand.

        The `PASS` fragment is the verdict's own first line. Its figures are
        not asserted: `2,705` is a number about the corpus rather than a verdict
        on the mode, and a figure written into a test is a value every commit
        that moves the corpus has to edit.
        """
        self.skip_without_history()
        code, said = run_mode(clone("full"))
        self.assertEqual(code, 0, said)
        self.assertIn("PASS  the migration changed the column and nothing "
                      "beneath it", said)

    def test_a_depth_1_clone_fails_and_says_which_revision_it_could_not_resolve(self):
        """Exit 1, the revision named, and the requirement printed whole.

        `HISTORY_REQUIREMENT` is compared as the constant rather than as a
        substring of it, so this is "the failure path prints the requirement"
        and not "the failure path prints something about clone depth". The
        `git fetch --unshallow` half is separate because #421 asked for that
        advice to survive the correction, and it is the one line of the block a
        reader who is not in CI can act on.
        """
        tree = clone("shallow")
        code, said = run_mode(tree)
        self.assertEqual(code, 1, said)
        self.assertIn("cannot resolve the base revision '%s'" % BASE, said)
        self.assertIn(requirement_in(tree), said)
        self.assertIn("`git fetch --unshallow`", said)

    def test_the_printed_requirement_names_a_job_and_not_the_whole_workflow(self):
        """The regression #421 filed: the sentence a red `gates` run prints.

        Read off the *printed* block with its whitespace run together, which is
        what `history_checkout_sites.py` does for the same claim held as a
        fragment: the constant is wrapped across six source lines, so matching
        the source layout would be a test of a wrap rather than of a sentence.

        **This holds the claim's shape, not its content.** The negative is that
        the pre-#421 wording -- which asserted that ``a default-depth checkout
        ... which is what ci.yml uses``, naming no job -- is gone, and the
        positive is that a job is still named, so a rewrite cannot satisfy the
        first by dropping the claim and leaving a reader with no checkout to
        look at. A sentence naming the *wrong* job passes both, because job ids
        here are ordinary English words; that limit is the one
        `docs/findings/history-checkout-claims.md` states about the quotation
        rule this case's shape is borrowed from.
        """
        _code, said = run_mode(clone("shallow"))
        printed = " ".join(said.split())
        self.assertNotIn(
            STALE_CI_YML_CLAIM, printed,
            "the printed requirement still carries the pre-#421 wording -- see "
            "STALE_CI_YML_CLAIM above for it verbatim -- which named a "
            "workflow and no job, so a reader on a red run would go looking "
            "for the cause in a checkout that has the history")
        self.assertIn(
            CORRECTED_CI_YML_CLAIM, printed,
            "the printed requirement no longer says which checkout is the "
            "default-depth one, so the correction above was made by dropping "
            "the claim rather than by naming the job")


if __name__ == "__main__":
    unittest.main()
