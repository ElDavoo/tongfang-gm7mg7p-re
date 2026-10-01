# What issue #318 asked for is already in the gate; what was missing is what holds it there (2026-10-01, issue #318)

Issue #318 asked for a `case` arm in `check_ghidra_tooling()` running
`xdata_register_map.py --check && --self-test`, on the grounds that the tool
was absent from the gate's tool list and that no `case` arm existed for it.
**Both halves of that are false of the tree this branch starts from.** The arm
is there and both modes exit 0 in CI. This branch therefore does not land the
arm; it adds the check that would have made the issue unnecessary — one that
compares `check_ghidra_tooling()`'s tool list against its `case` arms, and a
tool's claim about the gate against the arms.

**Nothing here is a register behaviour, a live test, or evidence about the
laptop.** Both modes of the census tool read committed text only, and so does
this checker: no image, no Ghidra, no hardware, no Windows.

## The retraction, in place

Per [`../findings.md` §4a-4d](../findings.md) the wrong version stays visible
with the correction beside it. Every premise in the issue is restated as filed
and then answered from the committed tree.

| issue claims | committed tree |
|---|---|
| tool list is `agent-gates.sh:119-124`, six tools, no `xdata_register_map.py` | `check_ghidra_tooling()`'s `for tool in` list carries twelve tools, and `ec/tools/xdata_register_map.py` is one of them |
| `grep -c xdata_register_map` on the two gate scripts returns `0` and `0` | returns 3 in `agent-gates.sh` and 0 in `agent-gates-deep.sh`; the deep tier `exec`s the cheap one when `AGENT_GATES_DEEP=1`, so the arm runs there too |
| the tool needs its own arm because `*)` passes `--work` it rejects | it has one, running `--check && --self-test`. The `*)` fallback is for `build_ec_decompile.py` and `bios_extract.py`, which the arm's own comment names |
| neither `--check` nor `--self-test` has a caller in any workflow | `ci.yml` runs `agent-gates.sh`, which runs both; the arm's comment records that #256 wired `--check` and #815 wired `--self-test` |
| the seven assertions sit between `:1720` and `:1940` | they are present in `self_test()` by name. The issue's line numbers belong to a version of the file that no longer exists — it has moved since, and editing to them would be editing to a phantom |
| the write-up is the deliverable | `xdata-census-self-test-gate.md` exists and is indexed |

Two of these need a caveat rather than a flat "false". The issue's line numbers
were correct against the tree it was filed against; that tree is gone. And
`grep -c` returning 0 for `agent-gates-deep.sh` is still true — the deep tier
does not name the tool, it delegates. Neither is a premise the issue needed.

**The `--work` trap the issue describes is real and current.** Running the tool
with the fallback's arguments exits 2 with `unrecognized arguments: --work`.
What has changed is that the arm is what avoids it, and the arm is there.

**Read as a stale read, not as a request.** It was opened automatically by
`agent-followups` against a tree state that no longer exists. The requested diff
is not this branch's job: re-landing a correct arm is a no-op at best, and a
conflict on `.github/scripts/agent-gates.sh` — the file several open agent PRs
collide on — at worst.

## What was actually missing

A tool added to the gate's list with no `case` arm for it falls to `*)`, which
runs `python3 "$tool" --work "$scratch" --check`. For a tool whose argparse has
no `--work` that is not a degraded run but a hard exit 2; for a tool that
accepts it silently, it is a check that is not the one anyone read. **Nothing
compared the two halves of that function to each other**, which is why the
stale read above could become an issue at all rather than a red run.

`ec/tools/check_gate_arm_coverage.py` holds the relationship in three
directions:

1. **Listed, so dispatched.** Every tool in the `for` list is matched by some
   `case` pattern, or is named in the `*)` arm's own comment as one of the two
   that take `--work`.
2. **Dispatched, so listed.** Every `case` pattern matches at least one listed
   tool. This is the direction a one-way check fails open on: a renamed tool
   leaves its arm behind, the glob matches nothing, the tool takes `*)`, and the
   run is *green* if the fallback's flags happen to parse.
3. **A claim, checked against reality.** A tool whose docstring says it lives in
   the gate has an arm that runs it — which is the shape of #318 from the other
   end, since `xdata_register_map.py`'s docstring has claimed that place since
   the tool was written.

Direction 2 is what makes this not a one-liner. Direction 1 alone would pass the
rename, which is the more common way the same state arrives.

### The exemption is read out of the script, not copied here

The two tools that legitimately take `*)` are exempt because **the `*)` arm's
comment names them** — `# build_ec_decompile.py and bios_extract.py both take
--work.` A hand-kept list of them in the checker would be a second answer to the
same question, and would go stale in the direction that matters: a third
`--work` tool added to the fallback would red the committed tree and the reader
would be sent to edit the checker rather than the arm that is already correct.

### Direction 3 needed a boundary, and the boundary is the interesting part

Most docstrings in this tree that name the gate are *declining* a place in it —
"It is not in `.github/scripts/agent-gates.sh`, and cannot be from an agent
branch" is a sentence several tools open with, and it is **true**. A predicate
that matched on the path alone fires on every docstring in the tree that names
the gate, which is how a gate teaches everyone to ignore it.

So the claim is read per **clause**: a clause naming the gate, carrying a
membership phrasing, carrying no negation. On the committed tree that leaves
exactly one claim — `xdata_register_map.py`'s — which is the honest reading of
this tree: the rest either declines membership or does not discuss it.

Two boundaries are load-bearing and both are pinned:

- **"run under" is not a membership phrasing.**
  `ec/tools/test_pd_image_census.py`'s claim that it runs under the gate's
  `python3 syntax` check is true, and it is not a tool-list claim. Reading it
  as one would be a false positive on a correct file.
- **A path split across two lines is still a path.** Several docstrings wrap
  `.github/scripts/agent-gates.sh`, and one that names the gate across a line
  break is still naming it.

## What this establishes, and what it does not

**It establishes** that the two halves of `check_ghidra_tooling()` agree with
each other: every listed tool is dispatched, every arm dispatches something
listed, and every gate claim a docstring makes is met by an arm. It asserts
**membership throughout and no count of anything** — not the number of tools,
not the number of arms. A census here is a value every landing edit has to
touch, which is the failure `CLAUDE.md` records four times over; this checker is
meant to keep passing as `check_ghidra_tooling()` grows, and the suite says so
in a case that adds a tool with a correct arm and stays green.

**It does not establish** that any tool's `--check` or `--self-test` passes.
That is the gate's own job and this checker never runs a tool. Nor does it
establish that the list is *complete* — nothing in the script names what ought
to be in it, which is what direction 3 is for, and direction 3 is a **floor**: a
tool whose docstring claims no place is not on this checker's list of claims, and
adding one that should be is a human's read.

**A gate script this cannot read is not a clean one.** A missing file, a script
with no `check_ghidra_tooling()`, an unbraced function and an empty tool list
each exit non-zero with the reason on stderr. A checker that cannot find its
target must not read as a clean run, because empty is what a clean run reports.

## The control that decides whether this is worth having

`ec/tools/test_gate_arm_coverage.py` runs issue #318 as a fixture rather than
leaving it as an issue. The state the issue reported — the tool in the list, no
arm for it — is a red run naming `ec/tools/xdata_register_map.py`, and it is red
under **both** direction 1 and direction 3, from the same removal.

The negative controls are the substance, because a rule that fires on everything
passes every positive. Four docstrings that decline the gate are asserted to
stay green; the same claim with an arm is green and without one is red, which is
what makes direction 3 a claim-checked-against-reality rather than a substring
test; a claim about the syntax check stays green; and a tool added to the list
with a correct arm stays green, which is what keeps the checker from becoming a
census.

Every mutation is a `tempfile` scratch tree, never `.github/`, and one case holds
`git status --porcelain` byte-identical across a run — same shape
`test_xdata_program_keyed_table.py` uses for the same reason. The one file this
reads is the one several open agent PRs collide on, so a checker that rewrote it
would be a merge conflict wearing a gate's clothes.

### Reproducing it

```console
$ python3 ec/tools/check_gate_arm_coverage.py ; echo $?
gate arm coverage: every listed tool is dispatched by an arm, every arm
dispatches a listed tool, and every gate claim a docstring makes is met by one.
0
```

Delete the `*xdata_register_map.py)` arm in a scratch copy and the same command
names the tool twice — once for the dispatch and once for the claim:

```console
$ python3 ec/tools/check_gate_arm_coverage.py --gate /tmp/no-arm.sh ; echo $?
ec/tools/xdata_register_map.py is in check_ghidra_tooling()'s tool list and no
`case` arm dispatches it.
    ...
ec/tools/xdata_register_map.py says it lives in the gate and no `case` arm runs
it.
    ...
2 gate-arm coverage problem(s) found.
1
```

## What is not done here, and what a human would do

**This checker is not wired into `agent-gates.sh`,** and the reason is the
pipeline file-copy rule rather than an oversight: the gate script is copied from
`ElDavoo/agent-pipeline`, so a gate call is upstream's change and a re-copy, not
a line here. `tools/README.md` carries that note on every ungated row, and
`bash tools/run-tests.sh`'s own closing note says the same thing about itself.

**The gate script is read, never written.** Nothing in this branch needed an
edit to it — the arm is already correct — so the file several open PRs collide
on is untouched.

**The same check is worth propagating to `ElDavoo/agent-pipeline`**, because a
template re-copy of `agent-gates.sh` is what would drop an arm in the first
place; that re-copy is the mechanism behind every premise in the retraction
above. Per `CLAUDE.md`, nothing is opened in another repository without explicit
approval, so this is recorded and left.

**The census tool's own refusal suite is not wired either.** No gate calls
`ec/tools/test_xdata_register_map.py`, which holds the `--no-eq-guard` and
`--export-ownership` refusals; the arm's comment says so. That is #773's, and it
is a different subject from this issue's.

The write-up for the census tool's gate arm, and the decision recorded there
about `.github/scripts/` being pushable while only `.github/workflows/` and
`.github/actions/` are not, is `xdata-census-self-test-gate.md`. The point is
moot here: nothing needed editing.