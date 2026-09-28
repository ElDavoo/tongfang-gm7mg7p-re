# The cited sha is a superseded branch commit, and the sentence it carried was true when written

**2026-09-28, issue #971.** Four pages cited `a4f967ed` and could not resolve
it, and three of them read that unreachability as a verdict: the `diff` it
argues for "unreproduced", its relationship to `bdfddcfd` "not settled here",
the question "a separate open question, not a finding". **Those readings are
wrong, and the sentence they treated as unsettled was right.** `a4f967ed` is a
real commit — the first of the two on the branch of pull request #923,
superseded by `2dd0f187` and squash-merged as `bdfddcfd`. It is invisible to
`git cat-file` from a checkout because no ref points at it, which is a fact
about *refs*, not about the commit.

**Nothing here is a hardware claim.** No image is opened, no register is read
back, and no laptop, EC or Windows machine is involved. The evidence is git
plumbing over committed history and six read-only `GET`s against this
repository.

## The four options, and which one it is

The issue named four: a merged id, a PR head, a squash id, or a sha naming
nothing this repository ever committed. The answer is a fifth shape that sits
between two of them, and the nearest of the four is not quite right either:

| option | verdict |
|---|---|
| the merged id | **no** — that is `bdfddcfd`, the squash |
| the squash id | **no** — same `bdfddcfd`; a squash id is what replaced this commit |
| a PR head | **nearly, but not quite** — a commit *on* a PR's branch, not the branch's head |
| names nothing ever committed | **no** — it is a real commit on the remote |

What it is, exactly: `a4f967ed6dcce168e64550f3fb73584a1eac342f`, authored by
`claude[bot]` at `2026-09-26T03:47:14Z`, whose single parent is `d62730e1`.
Pull request #923 carried exactly two commits, this one and `2dd0f187`
("fix round 1 (review)"), and merged as a squash to `bdfddcfd` at
`2026-09-26T04:04:36Z`. So the two names in the tree are the **same change**,
recorded once as the branch's first commit and once as the squash that replaced
it — which is the first of the issue's four options, "the merged id of the
change `bdfddcfd` also names", arrived at from the other direction.

**A superseded branch commit is the one case a ref-based method cannot find**,
and that is the whole reason this took a full page. A branch head is named by
`refs/pull/N/head` and is therefore visible to `git ls-remote`; this commit is
its parent, nothing points at it, and both `git cat-file` and the advertised-ref
sweep come back empty for it. What finds it is a plain object lookup on the
remote, which does not care about refs at all.

## The procedure, in order, with what each step returned

The order is load-bearing: each step is narrower than the one before, and the
step that settles the question is the one the local store cannot perform.

### 1. Is it an object in the local store?

```console
$ git rev-parse --is-shallow-repository
false
$ git rev-list --all --count
418
$ git cat-file -t a4f967ed
fatal: Not a valid object name a4f967ed
$ git rev-parse --disambiguate=a4f967e

$ git cat-file --batch-all-objects --batch-check='%(objectname)' | grep -ci '^a4f967e'
0
```

A full clone, not a shallow one, and 418 commits across every branch. The
written id names nothing; the 7-character prefix is not a valid abbreviation of
anything; and an exhaustive walk of **every object in the store**, independent
of any ref, finds none beginning `a4f967e`. The last line is the strongest form
of the local check, because it cannot be defeated by a refspec that did not
fetch something.

### 2. A rewritten or unreferenced-but-present object?

```console
$ git fsck --dangling --unreachable --no-reflogs --no-progress
$ ls .git/packed-refs
ls: cannot access '.git/packed-refs': No such file or directory
```

Clean, and there is no `packed-refs` to consult. `--dangling` and not
`--lost-found`: the latter writes `.git/lost-found/`, and an unreachable object
is readable by its own sha without it.

### 3. Does the remote serve it? — the decisive step

```console
$ python3 ec/tools/commit_id_probe.py a4f967ed
a4f967ed  remote-only
  object        : absent from the local store (cat-file: not a valid object name)
  disambiguate  : 0 object(s) match the prefix a4f967e
  advertised    : 303 ref(s) from `origin`, 293 of them a PR head; 0 begin a4f967e
  remote        : the API serves ElDavoo/tongfang-gm7mg7p-re/commits/a4f967ed
```

**This step is not optional, and the case for it is mechanical.** A checkout
configures `remote.origin.fetch` as `+refs/heads/*:refs/remotes/origin/*`;
`refs/pull/*/head` is never fetched, so a pull-request commit is invisible to
`git cat-file` *by construction* rather than because it was never pushed, and
`git log --all` cannot see it either. A negative from the local store is worth
nothing on its own, and the plan that produced this page said so before it was
run.

The control that gives the negative its meaning, run first and separately:

```console
$ python3 ec/tools/commit_id_probe.py 65c8c201
65c8c201  remote-only
  object        : absent from the local store (cat-file: not a valid object name)
  disambiguate  : 0 object(s) match the prefix 65c8c20
  advertised    : 303 ref(s) from `origin`, 293 of them a PR head; 1 begin 65c8c20
                  65c8c20161bbd9742c4f46495d3f3e5b89bb1312 refs/pull/1002/head
  remote        : the API serves ElDavoo/tongfang-gm7mg7p-re/commits/65c8c201
```

`65c8c201` is a live pull-request head, and the procedure finds it: absent
locally, named by an advertised ref, served by the API. So each of those three
lines is capable of a positive. `a4f967ed` produces the first and the third
and not the second, and the second is exactly the difference between the two
objects — one has a ref, one does not.

**What the API answered**, so the verdict rests on the response rather than on
the tool's word:

```console
$ gh api repos/ElDavoo/tongfang-gm7mg7p-re/commits/a4f967ed --jq '{sha, parents: [.parents[].sha]}'
{"parents":["d62730e1e4d4a62addb42a75067aaca6c3af4c20"],"sha":"a4f967ed6dcce168e64550f3fb73584a1eac342f"}
```

A 40-character sha beginning with the eight written, on a commit whose parent is
`d62730e1` — the parent `bdfddcfd` also has. The endpoint is not one that
answers 200 to anything: a sha which cannot exist is refused.

```console
$ gh api repos/ElDavoo/tongfang-gm7mg7p-re/commits/0000000000000000000000000000000000000000
{"message":"No commit found for SHA: 0000000000000000000000000000000000000000","documentation_url":"https://docs.github.com/rest/commits/commits#get-a-commit","status":"422"}
### exit 1
```

### 4. Which pull request, and where did it go?

The advertised-ref sweep from step 3 finds nothing, for the reason given above:
no ref points at a superseded commit. What finds it is the remote's own
commit-to-pull-request association.

```console
$ gh api repos/ElDavoo/tongfang-gm7mg7p-re/commits/a4f967ed6dcce168e64550f3fb73584a1eac342f/pulls \
    --jq '.[] | {number, head: .head.sha, merge_commit_sha}'
{"head":"2dd0f187a78a5542729c7cd66a35dd9e76470696","merge_commit_sha":"bdfddcfdb26c148cb7c61db6494b93f10ab39d2c","number":923}

$ gh api repos/ElDavoo/tongfang-gm7mg7p-re/pulls/923/commits --jq '.[].sha'
a4f967ed6dcce168e64550f3fb73584a1eac342f
2dd0f187a78a5542729c7cd66a35dd9e76470696

$ gh api repos/ElDavoo/tongfang-gm7mg7p-re/pulls/923 \
    --jq '{merged_at, merge_commit_sha, head: .head.sha, commits}'
{"commits":2,"head":"2dd0f187a78a5542729c7cd66a35dd9e76470696","merge_commit_sha":"bdfddcfdb26c148cb7c61db6494b93f10ab39d2c","merged_at":"2026-09-26T04:04:36Z"}
```

Two commits, the first of which is the one in question, the second of which is
the branch head, squashed to `bdfddcfd`. The tree is consistent to the last
detail: `refs/pull/923/head` is `2dd0f187`, and `2dd0f187`'s only parent is
`a4f967ed`.

### 5. The claim the sentence was making, re-derived

[`xdata-write-direction-correction.md`](xdata-write-direction-correction.md)'s
paragraph says `a4f967ed` "adds `write_movement()` and the four cases on top
of" `d62730e1`, and that a `diff` against the working tree came out empty. Held
to the parent the API reports, that is checkable rather than asserted:

```console
$ git diff --stat d62730e1 bdfddcfd -- ec/tools/xdata_moved_ranks.py
 ec/tools/xdata_moved_ranks.py | 124 +++++++++++++++++++++++++++++++++++++-
 1 file changed, 122 insertions(+), 2 deletions(-)
$ git diff d62730e1 bdfddcfd -- ec/tools/xdata_moved_ranks.py | grep -c '^+.*def write_movement'
1
$ git diff d62730e1 bdfddcfd -- ec/tools/xdata_moved_ranks.py | grep -c '^+.*check('
4
$ git log --format=%P -1 bdfddcfd
d62730e1e4d4a62addb42a75067aaca6c3af4c20
```

One `write_movement`, four `check(` cases, one parent. The sentence describes
this change accurately.

**And the transcript was not fabricated.** The file at `a4f967ed` is
byte-identical to the file at `bdfddcfd`, which is the statement that makes the
original `diff` come out empty:

```console
$ diff <(git show bdfddcfd:ec/tools/xdata_moved_ranks.py) \
       <(gh api "repos/ElDavoo/tongfang-gm7mg7p-re/contents/ec/tools/xdata_moved_ranks.py?ref=a4f967ed6dcce168e64550f3fb73584a1eac342f" \
             -H 'Accept: application/vnd.github.raw')
### exit 0
```

No output, and a zero exit. The right-hand side is read through the contents
endpoint rather than a `fetch`, because fetching a ref is a change to the
checkout this repository's CI makes for itself and out of scope here; the bytes
are the same either way. Zero differences means the review commit `2dd0f187`
did not touch this file, so "the tool was never edited on two sides and no
merge needed reconciling" is true of the file as well as of the change.

That transcript was run at a time when the branch **was** at `a4f967ed` — the
page's own words are "this branch is one commit on `d62730e1`", and `a4f967ed`
is exactly that one commit. `git show a4f967ed:<file>` and the working tree
were the same file, so the empty diff is what that command printed then. It is
the *later* inference that is wrong, not the transcript.

## What is wrong, precisely

The claim that needs correcting is not the sentence at `:34-36`. It is the
reading three later passes gave the sentence's **unreachability**:

- `xdata-write-direction-correction.md` — "`a4f967ed` is not reachable from
  this tree, so the diff above is unreproduced". The premise is true and the
  conclusion does not follow: unreachability from a checkout says a ref does not
  point at the commit, which is what a squash merge does to the branch commit it
  replaces. The diff was reproduced, at the time it was run, and it is
  re-derivable above.
- `xdata-moved-ranks-pin-decisions.md` — "its relationship to `bdfddcfd` is not
  settled here", and the walk's "`a4f967ed` is unreached … that is a separate
  open question, not a finding". Settled: the same change, recorded twice, the
  second name being the squash of a branch whose first commit is the first name.
- `xdata-moved-ranks-collision-scope.md` — "is not reachable from this tree … so
  the `diff` it is an argument for is marked unreproduced there". Same premise,
  same non-conclusion.

Each keeps its sentence, per §4a-4d, and gains one beside it.

## The test that proves it

```console
$ python3 ec/tools/commit_id_probe.py a4f967ed          # the verdict line, above
$ python3 ec/tools/test_commit_id_probe.py -v
```

Thirteen cases over throwaway repositories, covering every verdict in the
vocabulary — a full sha and its abbreviation resolving, an ambiguous prefix
built from real colliding objects, a dangling object reported as
`resolves-unreferenced` rather than absent, and an API stubbed to fail
returning `remote-unknown` **and not one of the two verdicts it must never fall
through to**. The suite is discovered by `bash tools/run-tests.sh`, so it needs
no CI edit. The probe's own `--self-test` is not in a gate, because wiring a
new tool into `agent-gates.sh` is a `.github/` change and the pipeline token has
no `workflow` scope; the committed transcripts above are what stands in for it.

**The tool is the contribution, not the lookup.** A census pass over the tree's
commit citations needs a vocabulary to report into and a rule for when a
negative is worth anything, and both are the seven verdicts and the
`remote-unknown` discipline rather than a per-sha re-derivation. One caution
carries forward from step 4: **a ref sweep finds heads, not superseded
commits**, so a census that resolves ids by listing refs will report
`not-an-object` for every one of them and be wrong every time.
