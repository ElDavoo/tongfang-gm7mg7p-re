# The `--no-eq-guard` citation checker is prepared into the cheap gate, and one of its two placements looks wrong (issue #1129)

`docs/ci/agent-gates-eq-guard-citations.patch` wires
`ec/tools/check_eq_guard_citations.py` into `.github/scripts/agent-gates.sh`.
It is **prepared, not landed**: `.github/` is template-copied and a branch
editing it fails at the *end* of a pull request rather than the start, so the
change ships as a patch a human applies with `git apply`.

**The check is not unrun today, and this patch does not turn an uncaught defect
into a caught one.** `.github/workflows/ci.yml` runs `bash tools/run-tests.sh`
as its `tests` job on every push to `main` and every pull request,
`tools/run-tests.sh` discovers every `test_*.py` in the repository, and
`ec/tools/test_check_eq_guard_citations.py`'s
`TheCommittedTree::test_the_committed_citations_hold` runs this checker against
the committed tree and asserts it exits 0. A drifted citation is therefore
already a red run, and a red `tests` job on an `agent/issue-*` branch reaches a
human through `agent-fix-ci.yml`. Both halves of that were measured rather than
assumed, by perturbing a scratch copy of the tree: a citation moved by one line
in `ec/annotations/xdata-register-map.md`, and `xdata-4-4`'s committed-output
refusal swapped onto the `--check` refusal in
`docs/findings/xdata-4-4-identity-rederivation.md`, each turn that case red.

What the patch adds is the **tier**. The check lives in the slow leg — a job of
its own, behind a full checkout, with a 45-minute timeout — and in
`agent-conflicts.yml`'s run beside the gates. `agent-gates.sh` is what
`agent-implement.yml` and `agent-fix.yml` run on every round and before the
push, so landing this moves an existing check from *after the push, in the slow
leg* to *in the round that made the change*. That is the whole of the claim,
and it is the reason the patch carries a measured green rather than an assumed
one: a check brought into the cheap tier is one whose cost is paid every round,
so a red one there is a red tree.

**Correction, same day (issue #1129's re-review).** An earlier cut of this
write-up, of the patch header and of `docs/agent-pipeline.md`'s item said the
opposite thing about the tier: that *until a human lands the patch, no commit
runs this check*, and that a drifted citation therefore *arrives in a green
tree*. **That was false, and it was false in the direction that made the change
look worth more.** The `tests` job of `ci.yml` runs the suite on every push and
every pull request, and the suite runs this checker against the committed tree,
so the drift is red today — as the two perturbations above show, one of them
being exactly the *"a number that has drifted onto the other refusal"* case this
write-up called silent. The wrong sentences are quoted here rather than only
replaced, because they are the claim a later reader would otherwise reconstruct
from the patch's own title, and because a write-up that had claimed a red tree
was green has no reason to be trusted about the next thing. What survives the
correction is the narrower claim, and it is the one the patch actually
delivers: **an existing check moves from the slow leg into the cheap tier.** The
prepared set has always bought the tier rather than the first line of coverage —
the checkers behind the other prepared patches have suites
`tools/run-tests.sh` discovers the same way — so this patch is another of that
trade and not a new one.

Nothing here is a claim about the EC. Every number is a `grep -n` over a
committed file, re-derived by running the tool. No firmware image was opened,
no register was read back, and no hardware or Windows machine was involved.

## What the check catches, and what it still does not

The defect class is **silent by construction**. Five prose files cite `:NNN`
inside `ec/tools/xdata_register_map.py` for one mechanism — the `--no-eq-guard`
flag, the `==` guard it turns off, and the two refusals that stop it being
combined with `--check` and with the committed-output paths. A number that has
drifted onto *a different flag's help text*, or onto *the other refusal*, is not
a broken link: the sentence reads exactly as well and means the wrong line, and
no reader and no tool that is not this one can tell.

"Silent" is a statement about the class, not about the tree. The tree does go
red — `check_eq_guard_citations.py` is what goes red, and it is already run by
the `tests` job of `ci.yml` through its suite, as the paragraph above sets out.
What is silent is everything else: nothing catches this drift by accident, and
so a check that catches it on purpose has to be *run*, deliberately, by something.

The check holds each of those citations to the line its code is on today.
#873 is what found the class, and it found two of the sites naming the
*wrong code* outright rather than merely drifting; how far the rest had gone,
and by how many distinct offsets, is measured in
`docs/findings/xdata-no-eq-guard-citation-anchors.md` and not restated here.

Three boundaries are worth stating plainly, because each is a place the check
*does not* decide:

- **It is not the general `.py:NNN` pointer checker.** It reads no file outside
  its declared five plus the tool, it does not walk the tree for citations, and
  it holds no pointer in them. #868, #869 and #870 own that class; the census of
  it is theirs.
- **A citation inside a `>` block is skipped, not passed.** A quoted correction
  is a denial of currency and `docs/findings.md` §4a-4d requires the superseded
  figure to stay visible as text beside its replacement, so reading those would
  make the check red on its own corrected tree. The skip is counted on every
  run, never silent.
- **A declined count is a count of "checked nothing", not "found nothing".**
  The pins these same five files carry for *other* claims — `OUT_CLUSTERS`,
  `MAP_COLUMNS`, the `--self-test` span — are named as declined on every run
  rather than passed over, and a run that resolves nothing is a failure rather
  than a pass. Both are visible in the tool's own output for that reason.

## The anchors have moved again since the tree the write-up measured

`docs/findings/xdata-no-eq-guard-citation-anchors.md` measured its table on
`d330478`. The tool has grown since, so every figure in that table is a
generation stale — which is the point rather than a criticism of it, and the
reason a number is the wrong thing to hang a citation on. Measured with `grep -n`
on both trees, the `d330478` column kept beside the current one per §4a-4d:

| anchor in `ec/tools/xdata_register_map.py` | on `d330478` | **today** |
|---|---|---|
| `def store_target(text, …, eq_guard=True)` | `:1730` | **`:2017`** |
| `if eq_guard and stripped.startswith("==")` | `:1753` | **`:2040`** |
| `def scan(` | `:2367` | **`:2686`** |
| `ASSIGN = (…)` | `:377` | **`:398`** |
| the `not args.no_eq_guard` flip | `:3148` | **`:3529`** |
| `ap.add_argument("--no-eq-guard", …)` | `:4947` | **`:5561`** |
| the `--check`/`--self-test` refusal | `:4976` | **`:5590`** |
| the committed-output refusal | `:4985` | **`:5599`** |
| the tail of `--reconcile`'s help | `:4934` | **`:5548`** |

The offsets run from **21 to 614 lines and are not one number**: the flag, both
refusals and the help tail all moved 614 together, while `ASSIGN` moved 21 and
`store_target` 287. A reader who assumed "the tool grew, so add N" would be
wrong for five of these nine, which is the argument for anchoring on a string of
the tool's source rather than re-pointing in one sentence.

**The prose is already correct against today's tree**, so nothing here was
re-pointed. `main` has re-anchored these citations by hand more than once —
`6eb55f9d` for the `--no-eq-guard` set, and again in `a2eb723d` once the tool
had grown past that — and the point of the gate is that the *next* growth does
not need a person to do it again.

## One half sits where a reader expects it, and one half looks wrong

The two halves are placed for two different reasons, and only one of them is
composition.

**The function sits with the other `check_*` functions**, after
`check_registers_yaml()`, because that boundary is free. Content-matching every
prepared patch's hunk pre-image against the committed script — rather than
reading the `@@` headers, which are stale for most of the set — puts no other
patch's window anywhere near the boundary; the nearest occupied one belongs to
`agent-gates-testdata-row-claims.patch`, well clear of it. Nothing forced this
one, and a first cut of this patch said it was forced. Saying that would send
the next author to the end of the file for a placement they did not need, so the
correction is recorded rather than quietly dropped — the claim was wrong, and it
was the thing that produced the unnecessary cost.

**The `gate` line reads below the "this tier does not run" note** instead of
beside its siblings, and that one *is* composition. Every position in the
`gate` list is another patch's context window: the region is held by
`agent-gates-findings-frozen.patch`, `agent-gates-pin-table-rows.patch`,
`agent-gates-capture-claims.patch` and `agent-gates-testdata-row-claims.patch`,
with contiguous windows across it. Each candidate was re-cut and tested rather
than reasoned about — a `gate` line at any position in the list still applies
alone, and collides with at least one of those four once either lands first. A
`gate` line put in the tidier spot lands in some orders and not others, and the
failure is silent in the way that matters: **each patch still applies cleanly
alone.**

`docs/findings/prepared-gate-patches.md` records the collision table;
`tools/test_agent_gates_patches.py` applies the set in every ordered pair, so
the composition is checked rather than claimed here.

List order is cosmetic — the `gate` calls are independent and nothing reads the
order — so the cost of the one forced half is a placement that looks wrong and a
header that has to explain it. That is the same trade
`agent-gates-findings-frozen.patch` made for the same reason, and the precedent
for not taking a `gate` line at all when the list is saturated.

## Both halves are held, because a re-cut can drop either

This patch is one function and one `gate` line, and either can be dropped by a
re-cut that **still applies, still composes in every ordered pair, and still
passes `bash -n` and `shellcheck`** — shellcheck does not resolve a function
name against its definition, so a `gate` line naming a function that was never
defined is a green run of nothing, and a function nothing calls is the same
green run. Both mutations were built and checked rather than assumed;
`tools/test_agent_gates_patches.py`'s `GateLineRetentionTests` is the only case in
the suite that fails against either, and holding both strings rather than the
function's alone is what it is for. It is also the reason the two halves ship in
one patch file: two files would let a landing take one without the other.

## Green as prepared, measured before the patch was cut

A patch that lands a red gate is the cheapest way to get a gate switched off,
so the figure is in the header rather than assumed:

```console
$ python3 ec/tools/check_eq_guard_citations.py; echo "exit $?"
…
23 citation(s) name the line their code is on, 16 declined as not this tool's,
3 skipped as superseded -- 9 of 9 anchors resolved, over 5 declaring file(s).
A run that checks nothing is a failure of this test, not a pass.
exit 0
$ python3 -m unittest discover -s ec/tools -p 'test_check_eq_guard_citations.py'
…
OK
$ git apply --check docs/ci/agent-gates-eq-guard-citations.patch; echo "exit $?"
exit 0
```

The check reads five markdown files, one Python file and the standard library,
which is what puts it in the cheap tier: no firmware image, no Ghidra, no
network, no assembler. It measures 0.14 s here against the cheap tier
`docs/agent-pipeline.md` records at 5.9 s — one runner's figure, and the ratio
is the durable part.

**Landing it is a human's step**: `git apply
docs/ci/agent-gates-eq-guard-citations.patch`, and then marking the header
`# LANDED in <sha>`, which is what tells the next reader the `git apply` line
above it is no longer a thing to do.
