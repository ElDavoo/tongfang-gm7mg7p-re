#!/usr/bin/env python3
"""Cases for `commit_id_probe.py`, over throwaway repositories.

The probe's whole output is a word from a seven-word list, so a rule that has
never been seen to fire is a rule nobody can trust to have stayed put: five of
the seven verdicts are reachable only by building a repository in the shape that
produces them, and two of them are reachable only by making the remote answer in
a particular way. Every case here is therefore a scratch tree, a stubbed
`_remote_serves` or `_run`, or both.

The negative cases matter more than the positives. A probe that cannot tell
"the object is not here" from "nobody asked" is the failure the tool was written
against, so the `remote-unknown` cases assert not only the verdict but the
*absence* of the two verdicts it must never fall through to — a probe that
printed `not-an-object` when `gh` was missing would pass a verdict-only check
and fail this one.
"""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import commit_id_probe as probe_mod  # noqa: E402


def _git(root, *args, input=None):
    done = subprocess.run(("git",) + args, cwd=root, capture_output=True,
                          text=True, input=input)
    if done.returncode != 0:
        raise AssertionError("git %s failed in %s: %s"
                             % (" ".join(args), root, done.stderr.strip()))
    return done.stdout


def scratch_repo():
    """A repository with one commit on `main`, and its HEAD sha."""
    root = tempfile.mkdtemp()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "probe@example.invalid")
    _git(root, "config", "user.name", "commit id probe")
    # A signature would need a key this environment does not have, and a global
    # `commit.gpgsign=true` would turn every case below into a git error rather
    # than a verdict.
    _git(root, "config", "commit.gpgsign", "false")
    with open(os.path.join(root, "f"), "w", encoding="utf-8") as handle:
        handle.write("one\n")
    _git(root, "add", "f")
    _git(root, "commit", "-q", "-m", "one")
    return root, _git(root, "rev-parse", "HEAD").strip()


def _all_objects(root):
    return [line.split()[0] for line in _git(
        root, "cat-file", "--batch-all-objects",
        "--batch-check=%(objectname)").splitlines() if line.strip()]


def _ambiguous_prefix(root):
    """A prefix git itself calls ambiguous, in a store grown until one exists.

    Found rather than chosen: a sha cannot be written down to collide on
    demand, and a hand-written "two objects with the same prefix" fixture would
    be a lie the day git changed its hashing.

    The two conditions are what makes it a fixture for *this* verdict rather
    than for a mathematical one. Two objects sharing a first character is not
    ambiguity as git reports it -- `git rev-parse --disambiguate=0` answers
    nothing at all and `git cat-file -t 0` says `fatal: Not a valid object
    name`, exactly as it does for an id that was never committed. Searching
    from four characters up is where git starts answering at all, so a shorter
    shared prefix would be testing a case the tool never claims to cover.

    Hence the store is grown first: a one-commit repository holds three objects
    and will not collide in four hex characters in any realistic number of
    tries, so a fixture that did not grow would report a missing rule instead
    of a broken one. `hash-object -w` adds blobs without touching history, so
    the prefixes under test belong to the same store the probe reads.
    """
    for batch in range(40):
        for n in range(batch * 50, batch * 50 + 50):
            _git(root, "hash-object", "-w", "--stdin",
                 input="ambiguous %d\n" % n)
        oids = _all_objects(root)
        for width in range(4, 9):
            seen = {}
            for oid in oids:
                seen.setdefault(oid[:width], []).append(oid)
            for prefix, group in sorted(seen.items()):
                if len(group) > 1 and len(
                        probe_mod._disambiguate(root, prefix)) > 1:
                    return prefix
    raise AssertionError("2000 objects still share no ambiguous prefix in %s"
                         % root)


class _NoRemote(unittest.TestCase):
    """Base that makes every remote call a stub, so no case reaches the net."""

    def setUp(self):
        self._serves = probe_mod._remote_serves
        self._advertised = probe_mod._advertised
        self.addCleanup(setattr, probe_mod, "_remote_serves", self._serves)
        self.addCleanup(setattr, probe_mod, "_advertised", self._advertised)

    def stub_remote(self, served=None, why="gh: not found", status="422"):
        """`_remote_serves` returns one fixed answer. None means "did not ask".

        The second element follows the shape the tool returns: a status for a
        refusal, the reason for an unanswered question, nothing for a hit.
        """
        if served is None:
            answer = (None, why)
        elif served is False:
            answer = (False, status)
        else:
            answer = (True, None)
        probe_mod._remote_serves = lambda *a, **k: answer
        probe_mod._advertised = lambda *a, **k: ([], None)


class TheVerdictsAResolvingIdCanTake(_NoRemote):
    def setUp(self):
        super().setUp()
        self.root, self.head = scratch_repo()
        self.addCleanup(lambda: None)
        self.stub_remote()

    def test_a_full_sha_on_the_current_ref_is_an_ancestor(self):
        verdict, evidence = probe_mod.probe(self.head, repo=self.root)
        self.assertEqual(verdict, "resolves-ancestor-of-HEAD")
        self.assertIn(f"object        : commit {self.head}", evidence)

    def test_an_abbreviation_of_the_same_object_reaches_the_same_verdict(self):
        # The written id in a write-up is short, so the short form is the one
        # the tool is actually asked about; a probe that only handled a full
        # sha would answer every real question with `not-an-object`.
        verdict, _evidence = probe_mod.probe(self.head[:8], repo=self.root)
        self.assertEqual(verdict, "resolves-ancestor-of-HEAD")

    def test_a_prefix_matching_two_objects_is_ambiguous_and_names_both(self):
        prefix = _ambiguous_prefix(self.root)
        verdict, evidence = probe_mod.probe(prefix, repo=self.root)
        self.assertEqual(verdict, "ambiguous")
        said = " ".join(evidence)
        self.assertIn(f"match the prefix {prefix}", said)
        # Named, not merely counted: `ambiguous` that does not say which two is
        # the reader back at the same disambiguation they ran themselves.
        self.assertRegex(said, r"[0-9a-f]{40}")

    def test_an_object_on_another_ref_is_in_the_store_and_not_an_ancestor(self):
        # The PR-head shape, once a head *has* been fetched: readable, on no
        # ref HEAD reaches, and fsck is silent because a ref does reach it.
        _git(self.root, "checkout", "-q", "-b", "side")
        with open(os.path.join(self.root, "g"), "w", encoding="utf-8") as handle:
            handle.write("two\n")
        _git(self.root, "add", "g")
        _git(self.root, "commit", "-q", "-m", "two")
        side = _git(self.root, "rev-parse", "HEAD").strip()
        _git(self.root, "checkout", "-q", "main")
        verdict, evidence = probe_mod.probe(side, repo=self.root)
        self.assertEqual(verdict, "resolves-not-ancestor-of-HEAD")
        self.assertIn(f"object        : commit {side}", evidence)

    def test_a_dangling_object_is_unreferenced_and_not_absent(self):
        # The distinction the whole tool exists for: the object is present and
        # readable, so `not-an-object` would be a false negative, and an object
        # nothing reaches is not an ancestor of anything either.
        _git(self.root, "checkout", "-q", "-b", "side")
        with open(os.path.join(self.root, "g"), "w", encoding="utf-8") as handle:
            handle.write("two\n")
        _git(self.root, "add", "g")
        _git(self.root, "commit", "-q", "-m", "two")
        side = _git(self.root, "rev-parse", "HEAD").strip()
        _git(self.root, "checkout", "-q", "main")
        _git(self.root, "update-ref", "-d", "refs/heads/side")
        verdict, evidence = probe_mod.probe(side, repo=self.root)
        self.assertEqual(verdict, "resolves-unreferenced")
        self.assertNotIn("not-an-object", verdict)
        self.assertTrue(any("dangling or unreachable" in line for line in evidence))


class TheRemoteHalf(_NoRemote):
    """The three verdicts only a consulted remote can reach."""

    def setUp(self):
        super().setUp()
        self.root, self.head = scratch_repo()
        self.absent = "0" * 39 + "1"

    def test_a_refusal_is_not_an_object(self):
        # The *decision* half, with the decision stubbed: `probe` has to turn
        # `_remote_serves`' refusal into `not-an-object` and print the status
        # that decided it. Which statuses count as a refusal is the other half,
        # and it is `_RealGhStderr` below rather than this case — stubbing the
        # return value leaves the line that reads `gh`'s error untested, and
        # that line is the one that made the verdict unreachable when it only
        # matched a 404 the endpoint does not answer with.
        self.stub_remote(served=False, status="422")
        verdict, evidence = probe_mod.probe(self.absent, repo=self.root)
        self.assertEqual(verdict, "not-an-object")
        self.assertTrue(any("HTTP 422" in line for line in evidence))

    def test_the_api_serving_an_absent_id_is_remote_only(self):
        self.stub_remote(served=True)
        verdict, _evidence = probe_mod.probe(self.absent, repo=self.root)
        self.assertEqual(verdict, "remote-only")

    def test_an_unanswered_api_is_remote_unknown_and_implies_nothing(self):
        # The calibration case. `gh` missing, unauthenticated or rate-limited
        # has not shown the object is absent -- it has shown nobody asked, and
        # the two verdicts a reader would otherwise take away are the two this
        # must not print.
        self.stub_remote(served=None)
        verdict, evidence = probe_mod.probe(self.absent, repo=self.root)
        self.assertEqual(verdict, "remote-unknown")
        self.assertNotIn(verdict, ("not-an-object", "remote-only"))
        self.assertTrue(any("no verdict is implied" in line for line in evidence))

    def test_no_remote_consulted_is_remote_unknown_rather_than_absence(self):
        # Same shape as the case above, reached by the flag instead of by a
        # failing `gh`; the two are the same claim about the evidence.
        probe_mod._remote_serves = self._serves
        probe_mod._advertised = self._advertised
        verdict, evidence = probe_mod.probe(self.absent, repo=self.root,
                                            consult_remote=False)
        self.assertEqual(verdict, "remote-unknown")
        self.assertTrue(any("not consulted" in line for line in evidence))

    def test_a_resolving_id_never_reaches_the_remote(self):
        # Reachability is settled by the store, so a probe that asked anyway
        # could turn a working id into `remote-unknown` whenever the network
        # was down -- the same conflation, reached from the other direction.
        def _must_not_be_called(*_a, **_k):
            raise AssertionError("the remote was consulted for a resolving id")
        probe_mod._remote_serves = _must_not_be_called
        probe_mod._advertised = _must_not_be_called
        verdict, _evidence = probe_mod.probe(self.head, repo=self.root)
        self.assertEqual(verdict, "resolves-ancestor-of-HEAD")


class _RealGhStderr(_NoRemote):
    """The remote half driven by recorded `gh` error text, not by a return value.

    The seam here is `_run`, so `_remote_serves` reads the error the way it
    reads the real one. Stubbing `_remote_serves` instead — which is what the
    other cases do — asserts only that a verdict comes out of a two-tuple, and
    never touches the line deciding whether an error *is* a refusal; that line
    is what decides whether `not-an-object` is reachable at all, and it is what
    read "404" while this endpoint answers 422, so that a genuinely-absent id
    reported `remote-unknown` against the live API.

    Every string below is a transcript of
    `gh api repos/<slug>/commits/<sha> 2>&1 >/dev/null` against this
    repository, and the ones committed in
    `docs/findings/a4f967ed-commit-identity.md` §"Does the remote serve it?"
    are the same runs.
    """

    def setUp(self):
        super().setUp()
        self.root, self.head = scratch_repo()
        self.absent = "0" * 39 + "1"

    def gh_answers(self, stderr, code=1):
        """`_run` gives the remote step this `gh` answer and defers otherwise.

        Everything that is not the `gh api` call goes to the real `_run`, so
        the store half of the probe is a real git against a real scratch
        repository and a case passing here has passed the whole way through.
        """
        real = probe_mod._run
        self.addCleanup(setattr, probe_mod, "_run", real)

        def _routed(argv, cwd=None):
            if tuple(argv[:2]) == ("gh", "api"):
                return code, "", stderr
            return real(argv, cwd=cwd)

        probe_mod._run = _routed
        probe_mod._advertised = lambda *a, **k: ([], None)

    def assert_refused(self, verdict, evidence):
        self.assertEqual(verdict, "not-an-object")
        self.assertTrue(any("the API answered HTTP" in line
                            for line in evidence))

    def assert_unanswered(self, verdict, evidence):
        self.assertEqual(verdict, "remote-unknown")
        self.assertNotIn(verdict, ("not-an-object", "remote-only"))
        self.assertTrue(any("no verdict is implied" in line
                            for line in evidence))

    def test_the_422_the_endpoint_answers_is_absence(self):
        # The transcript the write-up commits. This is the code that carries
        # the whole `not-an-object` half of the vocabulary, so it is the case
        # that has to exist rather than a 404 nobody has watched this endpoint
        # produce.
        self.gh_answers("gh: No commit found for SHA: %s (HTTP 422)\n"
                        % self.absent)
        verdict, evidence = probe_mod.probe(self.absent, repo=self.root)
        self.assert_refused(verdict, evidence)
        self.assertTrue(any("HTTP 422" in line for line in evidence))

    def test_a_404_is_also_a_refusal(self):
        # Observed for a slug the API does not serve, not for a sha, and kept
        # as a second refusal because a completed 404 is still a completed
        # answer. The limit is recorded rather than papered over: it speaks
        # about the resource the request named, so a wrong or invisible slug
        # would answer 404 for every sha.
        self.gh_answers("gh: Not Found (HTTP 404)\n")
        verdict, evidence = probe_mod.probe(self.absent, repo=self.root)
        self.assert_refused(verdict, evidence)

    def test_a_422_about_something_else_is_not_absence(self):
        # 422 is GitHub's validation code in general, so only the message says
        # what was wrong; the match takes both, and a 422 that arrives for
        # another reason has to fall to `remote-unknown` rather than be read
        # as the refusal this case's neighbour is.
        self.gh_answers("gh: Invalid request (HTTP 422)\n")
        verdict, evidence = probe_mod.probe(self.absent, repo=self.root)
        self.assert_unanswered(verdict, evidence)

    def test_a_rejected_token_is_not_absence(self):
        # Observed: `gh api` with a bad token exits 1 having answered nothing
        # about the sha. Nobody asked, so the probe must not answer.
        self.gh_answers("gh: Bad credentials (HTTP 401)\n")
        verdict, evidence = probe_mod.probe(self.absent, repo=self.root)
        self.assert_unanswered(verdict, evidence)

    def test_a_rate_limited_api_is_not_absence(self):
        # 403 is GitHub's rate limit *and* its "you may not see this", which
        # is why it is not a refusal: reading it as absence is the conflation
        # the tool exists to stop, and erring the other way costs a re-run
        # rather than a wrong verdict.
        self.gh_answers("gh: API rate limit exceeded for user ID 1. (HTTP 403)\n")
        verdict, evidence = probe_mod.probe(self.absent, repo=self.root)
        self.assert_unanswered(verdict, evidence)

    def test_a_transport_failure_carries_no_status_and_is_not_absence(self):
        # `gh` missing, offline, or a connection that dropped: there is no
        # `(HTTP NNN)` in the error at all. This is also the case that a
        # substring match reads worst — matching nothing can only be read as
        # "not a refusal", and the point of the case is that the tool says so
        # rather than deciding it by absence of evidence.
        self.gh_answers("error connecting to api.github.com\n")
        verdict, evidence = probe_mod.probe(self.absent, repo=self.root)
        self.assert_unanswered(verdict, evidence)


class TheCommittedTree(unittest.TestCase):
    def test_this_repository_probes_offline_without_a_verdict_it_cannot_earn(self):
        # `a4f967ed` is the id the write-up under repair names, and
        # `docs/findings/a4f967ed-commit-identity.md` is the page that records
        # what was found. Run here with the remote off, because the committed
        # suite must be offline: a run that reached the network would be a test
        # whose result depends on the day.
        #
        # What is asserted is the *property* and not the verdict this checkout
        # happens to produce. The object is absent from a plain clone, which is
        # the finding's whole point, but it is a real commit and one
        # `fetch refs/pull/*/head` away — so a verdict-only assertion would
        # fail on a checkout change for a reason that says nothing about the
        # probe. What must hold either way is that turning the remote off
        # cannot produce a verdict about absence.
        verdict, _evidence = probe_mod.probe("a4f967ed", repo=REPO,
                                             consult_remote=False)
        self.assertNotIn(verdict, ("not-an-object", "remote-only"))

    def test_the_offline_flag_answers_remote_unknown_for_a_sha_nothing_can_hold(self):
        # The same claim, on a sha this suite controls, so it cannot be decided
        # by what the tree's fetch shape has brought down: an all-zero-ish sha
        # no checkout will contain, which is the shape that must read
        # `remote-unknown` and not one of the two verdicts that would be a
        # claim about a remote nobody consulted.
        verdict, evidence = probe_mod.probe("0" * 39 + "1", repo=REPO,
                                            consult_remote=False)
        self.assertEqual(verdict, "remote-unknown")
        self.assertNotIn(verdict, ("not-an-object", "remote-only"))
        self.assertIn("not consulted", " ".join(evidence))

    def test_the_verdict_list_is_the_one_the_page_documents(self):
        # Seven words, and the page's table is the prose copy of this tuple. A
        # verdict added here without one there is a reader looking for a claim
        # the tool cannot make.
        self.assertEqual(len(probe_mod.VERDICTS), 7)
        self.assertEqual(set(probe_mod.VERDICTS), {
            "resolves-ancestor-of-HEAD", "resolves-not-ancestor-of-HEAD",
            "resolves-unreferenced", "ambiguous", "not-an-object", "remote-only",
            "remote-unknown"})

    def test_every_verdict_a_probe_returns_is_in_the_list(self):
        root, head = scratch_repo()
        for sha in (head, head[:8], "0" * 39 + "1"):
            verdict, _evidence = probe_mod.probe(sha, repo=root,
                                                 consult_remote=False)
            self.assertIn(verdict, probe_mod.VERDICTS)


if __name__ == "__main__":
    unittest.main()
