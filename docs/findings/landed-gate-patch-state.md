# A landed gate patch is not a stale one: the four states, and the two-step landing (issue #772)

**Written 2026-09-28, against `a5678a75`.** Every figure below is that
commit's. The gate script is unmoved since it, but the patch set and the
`gate` list are not things to keep re-reading: a landing changes both, which
is the point of this file. Nothing here is a hardware, firmware or Windows
claim. No image is opened, no register is read back, no capture is taken.
What is read is two committed files and a patch set, and what is run is
`git apply`, `bash -n` and `shellcheck`.

## What was measured

Three trees, each built by copying `tools/`, `docs/` and `.github/` aside,
`git init`-ing, committing, and then landing patches and committing again.
This is the shape every header in `docs/ci/` instructs a human to create, so
it is worth being exact about what it did.

| tree | how it was made | the suite before this change |
|---|---|---|
| **prepared** | commit, land nothing | `Ran 15 tests … OK` |
| **one landed** | commit, `git apply docs/ci/agent-gates-capture-claims.patch`, commit | `FAILED (failures=16)` |
| **all landed** | commit, `git apply` each patch in `PATCHES` order, commit | `FAILED (failures=53)` |

The 53 is the prepared case multiplied out: 7 single-patch cases, 42 ordered
pairs, two whole-set cases, and the two retention cases. The issue recorded 8
failures at `3387041`; the number is not comparable and the *set of methods*
is the same, so this is not a correction of the issue — the pair case reports
one failure per ordered pair touching the landed patch, which is twelve of the
sixteen in the one-landed tree, and the tree has since drifted.

`CommittedBaseTests` stayed green throughout, which is the useful part: this
was never a dirty-working-tree artefact. It is worth knowing that the
*uncommitted* applied state is a third thing, and that one is caught by
`test_the_working_tree_gate_script_is_the_committed_one` instead.

**After the change, on a real clone** (`git clone --no-hardlinks`, then
`git apply docs/ci/agent-gates-capture-claims.patch`, `git commit`), which is
the reproduction the issue asks for and which checks the script out at `100755`
rather than `cp -a`-ing it:

| state of the clone | result |
|---|---|
| landed and committed, header not yet marked | `Ran 20 tests … FAILED (failures=1)` |
| the marker added and committed | `Ran 20 tests … OK` |

The one remaining failure is the second step of the landing asking to be done,
for that one patch and no other — which is the intended shape, not a defect.
A third tree, all seven landed and marked, is `Ran 20 tests … OK (skipped=1)`;
the skip is the ordered-pair case with its reason printed, because a tree whose
landings are all done has no pair left to compose.

## The decision: inversion, not retirement

The issue offered two shapes and asked that the choice be written down.

**(a) Retirement.** The landing commit deletes the patch file and drops its
`PATCHES` entry, so `PatchSetTests` records the retirement the way it records
additions, and a case asserts the landed script carries what the retired patch
added.

**(b) Inversion.** The suite reads the committed gate script, and for a patch
whose added lines are already present the expectation becomes "must already be
there" rather than "must apply". The file is kept, as a record of what it was.

**(b) is what is implemented**, for the reason the issue gives and the tree
confirms. `docs/ci/agent-gates-capture-claims.patch` is cited **47 times
across 20 markdown files** at `a5678a75` (re-derived here, because the header
itself says its own 30/13 figure is a per-commit number and a citation count
is exactly the figure a landing moves). Under (a) the first landing deletes a
file that forty-seven sentences point at, on the day its own header's
instruction becomes false.

**(a) has one real advantage, and it is the strongest argument against this
choice**: it needs no header marker. Keeping the file is what leaves a header
reading "git apply this, and that is the whole change" after applying it has
made that false — the exact class of defect this suite exists to catch, in the
one file whose stated purpose is that the header's claim should be true. (b)
pays for the file with a marker, and a landing therefore has two steps rather
than one. That trade is recorded here rather than argued away, so someone who
disagrees can reverse it without re-deriving it.

This does not edit `docs/agent-pipeline.md`, per the issue's own instruction,
and the prepared-not-landed accounting stays in
[`prepared-gate-patches.md`](prepared-gate-patches.md), which points here.

## The four cells

Two facts, both of which the suite already had and neither of which could say
what the pair meant: `git apply --check` against the committed script, and
whether the patch's non-blank `+` lines (diff body only, `+++` excluded) are
all in that script.

| applies | added lines present | state | expectation |
|---|---|---|---|
| yes | no | `prepared` | must apply — today's rule |
| no | yes | `landed` | must **not** apply; the committed script must carry the content; the header must be marked |
| no | no | `stale` | must be re-cut — today's rule, today's message |
| yes | yes | `landed, still applies` | red, naming the double-apply |

Measured on this tree, with nothing assumed:

| tree | `prepared` | `landed` | `stale` | `landed, still applies` |
|---|---|---|---|---|
| prepared | all patches | — | — | — |
| all landed | — | all patches | — | — |

**No patch reaches the fourth cell on this set, in either state, and that was
checked rather than assumed.** It is what makes that cell worth having: it is
an early warning about a patch and a script that disagree about what "landed"
means, not a tripwire that fires on the current set. The same reading applies
to the `stale` cell here — this write-up has run the classifier and not found
a stale patch, which is a statement about this tree and this method, not a
claim that none can exist.

Each state also has its own message, because today's message is actively wrong
in one of them: for a landed patch it advises a re-cut, and the correct next
step is the opposite one — do not re-cut it, applying it a second time would
add a second `check_*()` definition and a second `gate` line.

## The two-step landing

Both steps are text-file edits with no `workflow` scope involved, which is why
a human can do them at all.

```sh
git apply docs/ci/agent-gates-capture-claims.patch
git add -A && git commit -m 'land the capture-claims gate patch'
```

Then, naming that commit:

```
# LANDED in 1a2b3c4 -- every check below is in .github/scripts/agent-gates.sh;
# see docs/findings/landed-gate-patch-state.md.
```

as a `#` line in the patch's own header, committed as its own change. The
suite asks for step two by name: with step one done and step two not, the run
is red on `test_a_header_says_whether_it_is_landed` for that patch and green
for every other one.

**The marker must not contain a `git apply <path>.patch` string.**
`GIT_APPLY` captures the whole header, so such a line becomes a second apply
target and `test_each_header_applies_its_own_path` fails on a marker that
landed correctly. The existing capture already enforces this; the marker only
has to respect it.

The marker is checked in **both** directions, so neither half passes on an
empty loop: a prepared patch carrying one is a failure, because a reader who
trusts it would skip a gate edit that is still waiting.

## The mode, and what the seeds were actually exercising

`scratch_tree()` seeded with `target.write_bytes(...)`, which creates the file
`0644`. The committed script is `100755` and every patch in this set whose
`index` line exists carries `… 100755` on it. So every `git apply` in the
suite printed

```
warning: .github/scripts/agent-gates.sh has type 100644, expected 100755
```

and **exited 0**. The mode bit the patches carry was being carried and never
exercised, in a suite whose failures all come from exit codes. `shutil.copy2`
seeds the file as the committed one, and a case now reads the committed mode
out of `git ls-tree HEAD -- <gate>` and holds the seeded copy to it. The
warning is gone from the run.

`git ls-tree` rather than `stat` on purpose: the mode under test is the one
the patches' `index` lines were cut against, which is a property of the commit
and not of whichever checkout the suite is running in. Where there is no
commit, the case says so out loud rather than falling back to the working
tree's mode — `copy2` copies that, so comparing against it would assert that
`copy2` copies, which is not the claim.

## Six places that will need re-deriving on the day

These argue the fold from "the `gate` list is seven lines long". It is seven
lines at `.github/scripts/agent-gates.sh:313-319` on this tree, and **ten** the
moment `agent-gates-capture-claims.patch` lands — that patch carries three
`gate` lines, which is the same number of checks it carries. All six are
correct today, and re-cutting them now to describe a state that does not
exist yet would be churn in exactly the long shared files `CLAUDE.md` says not
to churn. They are named by path so that the landing commit does not have to
re-find them.

- `docs/agent-pipeline.md:224`
- `docs/agent-pipeline.md:369`
- `docs/agent-pipeline.md:528`
- `docs/ci/agent-gates-capture-claims.patch:23`
- `docs/ci/agent-gates-capture-claims.patch:32`
- `docs/ci/agent-gates-testdata-row-claims.patch:17`

**The issue's own line reference has already drifted, which is why these are
by path.** The issue points at `docs/agent-pipeline.md:305` for this claim; at
`305` on this tree is a sentence about the 0751 grader's runtime, and the
seven-line claim is at `:224`.

## `agent-gates-testdata-row-claims.patch` has no `index` line, and should not be given one

The other six carry `index <old>..<new> 100755`, and it is tempting to treat
the seventh as an omission. It is not, and the case that would demand an
`index` line on all of them is deliberately absent.

An `index` line names the blob the patch was cut **from**, and the correct
answer is historical, not current. These six name three different blobs
between them — `ce9f0964`, `de5db1f` and `125d647` — which is what a set of
patches cut at different times looks like, and it is why a rule demanding the
line match *today's* blob would be a fabrication rather than a check. A value
derived from the present tree would make the set look consistent by asserting
something the patches never claimed.

## What the landed path is exercised by

`LandedStateTests` builds a landed tree in a `tempfile` and drives the
production helpers over it, so the second state is permanently exercised
rather than described — including a **half-landed** case, because a landed-path
case nobody has seen go red is the same defect in a new place, and
[`prepared-gate-patches.md`](prepared-gate-patches.md) already records that
discipline for this suite.

Its fixture is synthetic on purpose. Borrowing the real
`agent-gates-capture-claims.patch` cannot work: in a tree where that patch is
already landed, applying it to the committed script is impossible, which is
the very state the case exists to describe. A fixture is the only pre-image
that is the same in every state, and the patch is cut from the seed with
`difflib` so it applies by construction.

**Nothing here says a gate was landed in this repository.** No patch in
`docs/ci/` is touched by the change this file describes, and `.github/` is not
edited — that is the premise of the whole arrangement, not a limitation
worked around. Every landing measured above happened in a scratch tree or a
scratch clone under `/tmp`.
