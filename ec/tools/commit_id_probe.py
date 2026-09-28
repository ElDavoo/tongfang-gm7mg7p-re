#!/usr/bin/env python3
"""Decide what a short commit id names, from a fixed vocabulary, without guessing.

**The question.** A write-up cites a commit as `a4f967ed`. Is that a merge id, a
PR head, a squash id, or a sha this repository never committed? Each answer
licenses a different correction: the first three are a citation to repoint, the
fourth is a sentence to correct in place. The four are not distinguishable by
eyeballing, and the two that look alike from inside a checkout are the ones a
reader cannot separate.

**Why seven verdicts and not two.** "Not an object in this repository" and "not
reachable from this branch" are different claims, and collapsing them is the
specific error this tool exists to stop. A checkout configures
`remote.origin.fetch` as `+refs/heads/*:refs/remotes/origin/*`; `refs/pull/*/head`
is not fetched, so a PR head is invisible to `git cat-file` **by construction**
rather than because it was never pushed, and `git log --all` cannot see it
either. A two-state probe reports that as "absent" and is wrong in a way no
amount of re-running it will reveal. The split that matters:

  - in the store, on a reachable ref        -> `resolves-ancestor-of-HEAD`
  - in the store, on no reachable ref       -> `resolves-not-ancestor-of-HEAD`
  - in the store, fsck reports it dangling  -> `resolves-unreferenced`
  - prefix matches more than one object     -> `ambiguous`
  - not in the store, remote 404s           -> `not-an-object`
  - not in the store, remote serves it      -> `remote-only`
  - the API was not consulted or did not
    answer                                  -> `remote-unknown`

**`remote-unknown` is not a fallback for `not-an-object`.** It means *no verdict
is implied* — the local evidence is printed above it and a reader may weigh it,
but a rate-limited or unauthenticated `gh` has not shown the object is absent,
only that nobody asked. A probe that turns a network failure into "absent" is
worse than no probe, because it looks like a result. The last two verdicts are
the pair the issue turned on and they are reachable only by consulting the
remote, so the remote step is not optional by default.

**The remote step is a read-only GET against this repository.** `gh api` against
`ElDavoo/tongfang-gm7mg7p-re/commits/<sha>` opens nothing and comments on
nothing; the prohibition in `CLAUDE.md` is on *opening* issues and PRs, and on
other repositories. `git ls-remote` is here for the same reason and is the only
part of the step that can see a PR head without fetching one.

**What it deliberately does not check.** Whether the commit named the id *should*
be is a different question with a different answer for every citation, and this
tool has no opinion about any of them. It also does not fetch: a ref that would
make a head visible is a `.github/` change, out of scope for the token this
repository's pipeline holds.

Run with a sha and no other argument to probe it here; `--no-remote` stops at
the store; `--self-test` runs the sibling suite, which is the same cases this
tool's own vocabulary is defined by.
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
SLUG = "ElDavoo/tongfang-gm7mg7p-re"

# The vocabulary, in one place, because the verdict is the tool's whole output
# and a caller that re-derives the words gets a second, drifting list. Order is
# the order the decision procedure reaches them in, and a reader comparing two
# runs wants them aligned.
VERDICTS = (
    "resolves-ancestor-of-HEAD",
    "resolves-not-ancestor-of-HEAD",
    "resolves-unreferenced",
    "ambiguous",
    "not-an-object",
    "remote-only",
    "remote-unknown",
)

# `git rev-parse --disambiguate` wants a prefix short enough to be useful and
# long enough to be worth listing. The written id is 8 characters; dropping one
# is what turns "this exact id" into "is the prefix even a valid abbreviation
# of exactly one object", which is the stronger form of the check and the one
# that catches a recorded id that differs from the written one.
PREFIX_CHARS = 7


def _run(argv, cwd=None):
    """(returncode, stdout, stderr) for `argv`, never raising.

    A missing `git`/`gh` is a returncode like any other here: the caller decides
    what an absent tool means, and for the remote step it is `remote-unknown`.
    """
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    except OSError as exc:
        return 127, "", str(exc)
    return done.returncode, done.stdout, done.stderr


def _git(repo, *args):
    return _run(("git",) + args, cwd=repo)


def _object_type(repo, sha):
    """`git cat-file -t`'s answer, or None when it names nothing here."""
    code, out, _err = _git(repo, "cat-file", "-t", sha)
    if code != 0:
        return None
    return out.strip()


def _disambiguate(repo, prefix):
    """Full oids the prefix is a valid abbreviation of."""
    code, out, _err = _git(repo, "rev-parse", f"--disambiguate={prefix}")
    if code != 0:
        return []
    return [line.strip() for line in out.split() if line.strip()]


def _is_ancestor(repo, oid, ref):
    code, _out, _err = _git(repo, "merge-base", "--is-ancestor", oid, ref)
    return code == 0


def _unreferenced(repo, oid):
    """Whether `git fsck` calls this object dangling or unreachable.

    `--dangling` and not `--lost-found`: the latter writes `.git/lost-found/`,
    and nothing here needs the side effect, because an unreachable object is
    still readable by its own sha. `--no-reflogs` because a reflog is not a ref
    -- an object kept alive only by one is exactly the "present but unreferenced"
    case this verdict names.
    """
    code, out, err = _git(repo, "fsck", "--dangling", "--unreachable",
                          "--no-reflogs", "--no-progress")
    if code not in (0, 1):
        return None
    return oid in out or oid in err


def _advertised(repo, remote):
    """(refs advertised by `remote`, error or None), for the PR-head question.

    `git ls-remote` lists what the server advertises, which on GitHub includes
    `refs/pull/*/head` -- the one population a plain fetch never brings down.
    It cannot see a merged ancestor, because no ref points at one, so a hit here
    is a head and a miss is only ever about heads. `docs/findings/` records the
    negative it produced and the control that gives the negative its meaning.
    """
    code, out, err = _run(("git", "ls-remote", remote), cwd=repo)
    if code != 0:
        return [], err.strip() or "git ls-remote failed"
    refs = [line.split(None, 1) for line in out.splitlines() if line.strip()]
    return [(parts[0], parts[1]) for parts in refs if len(parts) == 2], None


def _remote_serves(repo, slug, sha, remote="origin"):
    """(True, None) / (False, None) / (None, why-unknown) for the remote half.

    Three outcomes rather than a boolean, and the third is the one that has to
    exist: `gh` absent, unauthenticated, rate-limited or offline all mean the
    question was not asked, which is not the same answer as "no".
    """
    code, _out, err = _run(("gh", "api", f"repos/{slug}/commits/{sha}"), cwd=repo)
    if code == 0:
        return True, None
    if "404" in err:
        return False, None
    return None, (err.strip().splitlines() or ["gh exited %d" % code])[0]


def probe(sha, repo=REPO, ref="HEAD", slug=SLUG, remote="origin",
          consult_remote=True):
    """`(verdict, evidence)` for `sha`. Evidence is a list of printed lines.

    `consult_remote=False` stops at the object store and returns
    `remote-unknown` rather than one of the three store-side verdicts, because
    a verdict about absence is only ever the pair `not-an-object` / `remote-only`
    and neither can be reached without the remote.
    """
    evidence = []
    kind = _object_type(repo, sha)

    if kind is None:
        # A prefix that is a valid abbreviation of exactly one object resolves
        # even though the written id does not, which is a different situation
        # from one that matches nothing and is the case the issue's
        # "--disambiguate" is for.
        prefix = sha[:PREFIX_CHARS] if len(sha) > PREFIX_CHARS else sha
        matches = _disambiguate(repo, prefix)
        evidence.append(f"object        : absent from the local store "
                        f"(cat-file: not a valid object name)")
        evidence.append(f"disambiguate  : {len(matches)} object(s) match the "
                        f"prefix {prefix}")
        if len(matches) > 1:
            evidence.append(f"                {' '.join(matches)}")
            return "ambiguous", evidence
        if len(matches) == 1:
            sha, kind = matches[0], _object_type(repo, matches[0])
            evidence.append(f"                the prefix is a valid "
                            f"abbreviation of {sha}")

    if kind is not None:
        evidence.append(f"object        : {kind} {sha}")
        if kind == "commit" and _is_ancestor(repo, sha, ref):
            evidence.append(f"reachability  : an ancestor of {ref}")
            return "resolves-ancestor-of-HEAD", evidence
        unreached = _unreferenced(repo, sha)
        if unreached is True:
            evidence.append(f"reachability  : on no ref; git fsck reports it "
                            f"dangling or unreachable")
            return "resolves-unreferenced", evidence
        if unreached is None:
            evidence.append(f"reachability  : git fsck did not answer, so "
                            f"unreferenced-ness is untested")
        else:
            evidence.append(f"reachability  : in the store, on no ref {ref} "
                            f"reaches")
        return "resolves-not-ancestor-of-HEAD", evidence

    if not consult_remote:
        evidence.append(f"remote        : not consulted (--no-remote); the "
                        f"store cannot rule out an unfetched PR head")
        return "remote-unknown", evidence

    refs, ls_err = _advertised(repo, remote)
    if ls_err is None:
        heads = sum(1 for _o, name in refs if name.startswith("refs/pull/"))
        hit = [(o, n) for o, n in refs if o.startswith(sha[:PREFIX_CHARS])]
        evidence.append(f"advertised    : {len(refs)} ref(s) from `{remote}`, "
                        f"{heads} of them a PR head; {len(hit)} begin "
                        f"{sha[:PREFIX_CHARS]}")
        for oid, name in hit:
            evidence.append(f"                {oid} {name}")
    else:
        evidence.append(f"advertised    : not listed ({ls_err})")

    served, why = _remote_serves(repo, slug, sha, remote)
    if served is True:
        evidence.append(f"remote        : the API serves {slug}/commits/{sha}")
        return "remote-only", evidence
    if served is False:
        evidence.append(f"remote        : the API 404s for {slug}/commits/"
                        f"{sha}")
        return "not-an-object", evidence
    evidence.append(f"remote        : not consulted ({why}); **no verdict is "
                    f"implied** and this is not evidence of absence")
    return "remote-unknown", evidence


def render(sha, verdict, evidence):
    """The printed form: the verdict on one line, the evidence under it.

    The verdict line is the quotable part and it leads, because it is what a
    write-up cites and what a reader takes away when they quote one line.
    """
    return "\n".join([f"{sha}  {verdict}"] + [f"  {line}" for line in evidence])


def _self_test():
    """Run the sibling suite rather than repeating its cases here.

    Two copies of the vocabulary's cases is two copies to drift, and the drift
    is invisible: a self-test that still passes against a broken probe is worse
    than no self-test. `ec/tools/test_commit_id_probe.py` is the one place the
    cases live, and this is the same trade `check_no_append_logs.py` makes by
    being checked by the committed tree rather than by its own suite.
    """
    sys.path.insert(0, HERE)
    import unittest
    try:
        import test_commit_id_probe  # noqa: F401
    except ImportError:
        print("test_commit_id_probe.py is not beside this tool; "
              "the cases live there, not here", file=sys.stderr)
        return 1
    return 0 if unittest.main(
        module=None, argv=["commit_id_probe --self-test", "test_commit_id_probe"],
        exit=False, verbosity=2).result.wasSuccessful() else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("sha", nargs="?", help="the short id to identify")
    parser.add_argument("--repo", default=REPO,
                        help="repository root (default: this one)")
    parser.add_argument("--ref", default="HEAD",
                        help="the ref reachability is measured against "
                             "(default: HEAD)")
    parser.add_argument("--slug", default=SLUG,
                        help="the repository the remote step queries")
    parser.add_argument("--remote", default="origin",
                        help="the remote to list advertised refs from")
    parser.add_argument("--no-remote", action="store_true",
                        help="stop at the object store; the verdict is then "
                             "`remote-unknown` unless the sha resolves here")
    parser.add_argument("--self-test", action="store_true",
                        help="run the sibling suite's cases")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()
    if not args.sha:
        parser.error("a short id is required, or --self-test")

    verdict, evidence = probe(args.sha, repo=args.repo, ref=args.ref,
                              slug=args.slug, remote=args.remote,
                              consult_remote=not args.no_remote)
    print(render(args.sha, verdict, evidence))
    # 0 on any verdict reached, including `remote-unknown`. The verdict is the
    # output and a caller reads it; an exit code that encoded "absent" would
    # make `remote-unknown` indistinguishable from `not-an-object` to every
    # caller that did not parse stdout, which is the conflation this tool is
    # built against.
    return 0


if __name__ == "__main__":
    sys.exit(main())
