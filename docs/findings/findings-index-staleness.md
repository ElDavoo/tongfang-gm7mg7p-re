# The index is hand-edited by merges and nothing runs the check that would catch it (issue #1137)

**Written 2026-09-28, against `30144f0b`,** the commit this change branches
from. Every figure below is that commit's, measured over the 150 write-ups
indexable there; none of them is a standing number, and this file is the 151st
— which is the reason regenerating `INDEX.md` in the same commit is part of the
change rather than bookkeeping. Nothing here is a hardware, firmware or
Windows claim: no image is opened, no register is read back, no capture is
taken. What is read is committed markdown, one prepared patch and a directory
listing; what is run is `--check`, `git apply --check`, and one counting loop.

## What the issue asked, and what is left of it

The issue was filed against an older tree, and its headline condition is **red
on this one** — not by a fault of the generator's, but by the very mechanism it
names. At the branch point:

```
$ python3 ec/tools/gen_findings_index.py --check
docs/findings/INDEX.md is out of date: a write-up was added, removed or retitled. Regenerate with `python3 ec/tools/gen_findings_index.py > docs/findings/INDEX.md`.
$ echo $?
1
```

152 `*.md` sit under `docs/findings/`; the generator is willing to index 150,
and `checkout-claim-corpus.md` — the write-up the issue names as missing — is
one of them, at `INDEX.md:37`. The two it skips are the skip set at
`ec/tools/gen_findings_index.py:35`: the index itself, and the pin census.

**The proximate cause is one commit old, and it is a hand-edit.** `30144f0b`
(#1212) added a write-up and touched `INDEX.md` by `1 0` lines
(`git show 30144f0b --numstat -- docs/findings/INDEX.md`): the entry line for
`ecmg-asl-references.md`, typed in by hand, with the header left reading
`149 write-ups.` over 150 entries. The banner at `INDEX.md:3` says "do not
edit", and the entry it added is the one the generator would have written — it
is only the count that was never regenerated. **This is the issue's failure
mode, reproduced one commit before this branch adds anything to it**, and the
counterfactual is one commit further back: at `d96676d4` the index read
`149 write-ups.` over 149 entries and `--check` exited 0.

The issue's arithmetic is 115 → 116 entries, and that is a **per-commit figure
rather than a wrong one**: #1291 regenerated the index in the same commit that
added the write-up — `git show d96676d4 --numstat -- docs/findings/INDEX.md` is
`2 1` — which is the rule stated below, and the one #1212 did not follow. Three
of the issue's citations are dated the same way, and are corrected here rather
than in the files they point at — a re-cut moves a patch header's own line
numbers, so correcting one in a file a human is meant to `git apply` is churn
in a shared file for no reader's benefit.

| issue says | `d96676d4` | `30144f0b` (branch point) |
|---|---|---|
| 115 entries; `checkout-claim-corpus.md` missing | 149; present; `--check` exits 0 | 150; present; `--check` **exits 1** |
| `docs/ci/agent-gates-findings-frozen.patch:78` (the call) | `:112` — the header grew | `:112` |
| same file `:37` ("here for the") | `:43` | `:43` |
| `tools/README.md:3535-3536` | `:33-34` — the file shed the append log | `:33-34` |

What is left is therefore the narrowest useful reading of the issue: the
regeneration is **both** a step this change performs **and** the repair of the
hand-edit one commit above it — the same two lines, fixed for both — and the
durable half is item 3, what made it stale, and which half of the #1135/#1137
pair is true.

## Why a merge that hand-edited the index shipped green

Re-measured rather than taken from the issue, because this answer is a negative
one and negative answers drift:

```
$ grep -rn 'gen_findings_index\|check_findings_frozen\|check_no_append_logs\|check_no_conflict_markers' .github/
(no matches)
```

`.github/workflows/ci.yml`'s `gates` job runs exactly one thing,
`.github/scripts/agent-gates.sh` (`ci.yml:45`), and that script calls none of
the four. The only line in the tree that would run the index check as part of a
gate is `docs/ci/agent-gates-findings-frozen.patch:112`,
`+  python3 ec/tools/gen_findings_index.py --check || rc=1`, inside a patch
whose own header at `:43` says it is "here for the" same reason from the other
direction. Every other mention is prose or a reproduction block a reader pastes
by hand — `test-site-fits-guard.md:328` is one, under a comment reading "the
two gates this touches" — and none of them runs on a merge.

**Put in its plainest form, there are two causes and both are needed: the
index is a generated file that a merge hand-edited, and the check that would
have said so is correct and has no caller.** Neither alone tells the story. A
hand-edit alone is a one-line slip a reviewer may or may not catch, which is
why it happens; an unrun check alone would leave the index correct, as
`d96676d4` shows, and leave a finding with nothing to point at. What this tree
holds is the pair — `30144f0b` hand-edited, and nothing noticed, because
`bash .github/scripts/agent-gates.sh` exits 0 with "All gates passed" at that
same commit, against that same red index. That is the write-up's own claim,
demonstrated rather than argued.

The same is true of `check_findings_frozen.py` beside it, so `CLAUDE.md`'s
"`docs/findings.md` is closed, and this is enforced rather than advised" is, on
this tree, enforced by two tools that no merge runs.

## Which half of the pair is true: all three of #1135's defects are latent here

The issue and #1135 could each end up right in a way that left the record
claiming both "the tool is fine, nobody called it" and "the tool is broken", so
all three of #1135's items were measured rather than argued. **All three are
real, and none of them could have caused this.**

### The fence-unaware title scan

`entries()` at `ec/tools/gen_findings_index.py:52-59` takes the first line
starting with `# ` and breaks, without tracking fences — so a `# ` line inside a
fenced block can only corrupt a title if it *precedes* the real heading.
Twenty write-ups contain such a line, and **in all twenty it comes after the
heading the scan already stopped at**, so the recorded title is the real one in
every case. Re-derivable over the indexable set:

```python
import os, re
root, SKIP = "docs/findings", {"INDEX.md", "test-line-pin-census.md"}
FENCE = re.compile(r"^\s*`{3}")  # `{3}`: three literal backticks close this block
fenced, corrupted = set(), []
for name in sorted(os.listdir(root)):
    if not name.endswith(".md") or name in SKIP:
        continue
    infence, first_any, first_real, seen = False, None, None, []
    for n, line in enumerate(open(os.path.join(root, name), encoding="utf-8"), 1):
        s = line.rstrip("\n")
        if FENCE.match(s):
            infence = not infence
            continue
        if s.startswith("# "):
            if infence:
                seen.append(n)
            elif first_real is None:
                first_real = n
            if first_any is None:
                first_any = n
    if seen:
        fenced.add(name)
        if first_real is None or first_any < first_real:
            corrupted.append(name)
print(len(fenced), len(corrupted))  # 20 0
```

### The `continue` that cannot change anything

`ec/tools/gen_findings_index.py:56`'s `if line.strip(): continue` is a
trailing `continue` in a loop body: whether or not the condition holds, the
next thing the loop does is read the next line, so the statement cannot alter
behaviour. It is never reached in this tree either — **0 of the 150** write-ups
have a non-blank line before their first `# ` heading, so every title is set on
a file's opening line and the loop never gets to `:59`. The two-line comment
under it, about a file that opens with prose, describes a case the set does not
contain.

### The one real coupling

`§97` is written into the rendered header as a literal at
`ec/tools/gen_findings_index.py:71`, while the section count that actually
gates anything is `FROZEN_SECTIONS = 97` at
`ec/tools/check_findings_frozen.py:65`, and **nothing ties the two**. That is
latent rather than live: both read 97 today, and a raise to one would leave the
other stating something false in a file that is generated rather than edited.
It is #1135's to fix, and it is the only one of the three with a failure mode
that reaches a reader.

Fixing all three would not have made this merge red, and leaving them does not
make it green. **The generator is fine; a merge hand-edited its output, and no
check was called to notice.**

## Who checks the index, in the meantime

Item 2 of the issue offers a fallback to landing the patch, and this is that
fallback, stated plainly because the issue asked for it: **the index is checked
by hand, by whoever adds, removes or retitles a write-up, in the same commit,
before pushing.**

```
python3 ec/tools/gen_findings_index.py --check
```

`docs/ci/agent-gates-findings-frozen.patch` stays prepared and unlanded. Nothing
about that is comfortable — it is a rule in prose exactly where the repository's
own `docs/ci/` header argues the check belongs in a gate — and the reason it
cannot be more is the same one the patch's header gives: landing it is a
`.github/` edit, the gate script is copied from the `agent-pipeline` template,
and the pipeline's push token has no `workflow` scope, so a branch editing it
fails at the *end* of the PR rather than at the start. That is a reason a human
runs `git apply`, not a reason the check is optional.

This change is the rule's own demonstration: it adds a write-up, and it
regenerates `INDEX.md` in the same commit. `--check` goes red the moment a
write-up lands without that, which makes it a regression test for this finding
rather than a tidiness check — adding a write-up is precisely what made the
index stale the first time. `30144f0b` is the counterexample in the tree
itself: the same step, skipped, and the header left behind.

## The prepared patch, measured rather than refreshed

The issue asks for `docs/ci/agent-gates-findings-frozen.patch` to be "brought
up to date". Measured, it is up to date, and it was left alone:

```
$ git apply --check docs/ci/agent-gates-findings-frozen.patch   # exit 0
$ python3 tools/test_agent_gates_patches.py
Ran 20 tests … OK
```

The pair suite is the proof of the header's own strongest claim — that no other
patch in the set has `check_doc_links()` in any hunk's context window, which is
what lets this one add no `gate` line at all — and it is green unchanged across
all seven patches. **A patch that is correct and unlanded is a different failure
from a stale one**, and it is worth naming them apart, because "bring it up to
date" reads as a defect and the measurement says otherwise. This is the same
result [`prepared-gate-patches.md`](prepared-gate-patches.md) records for #811:
a patch that needs no edit is a result, not an omission. The placement proof a
re-cut would need is already at `prepared-gate-patches.md:324-360`.

## What was not done, and why

- **Landing the patch, or any edit under `.github/`.** The `workflow`-scope
  reason above; a human runs `git apply`.
- **#1135's three generator fixes.** They belong to the issue that owns them,
  and the measurements above are published so that one need not re-derive
  them. Fixing the tool is not this issue's change, and on this evidence would
  not have prevented the staleness.
- **Any summary row, pointer or `§N` in `docs/findings.md`.** It is frozen, and
  `ec/tools/check_findings_frozen.py` fails a change that adds, deletes or
  renumbers a section; this change is verified still to read 97.
- **A live hardware or Windows run.** Nothing here needs one, and no sentence
  above implies one.
