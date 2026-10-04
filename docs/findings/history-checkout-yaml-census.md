# The checkout-depth census read `*.yml` and told a `.yaml` tree its census was broken

**Issue #1054. Written 2026-10-04.** `ec/tools/check_history_checkouts.py`
globbed `.github/workflows/` for `*.yml` and nothing else, and its own docstring
gave the reason: *"`*.yml` and not `*.yaml` because that is what the directory
holds, and a glob that quietly widened to both would report a file the pipeline
does not read as one it does."* That argument was about the cost of an
over-report, and it priced that cost at silence — which it was, while an unread
workflow only went missing from the table. It stopped being silent when #1037's
refusal began failing a run that read no workflows at all, and the tree that
run could not read is a tree whose workflows are spelled `.yaml`, which GitHub
Actions reads perfectly well.

The reason was also never true about Actions, which reads `.yml` and `.yaml`
interchangeably, and **the same file contradicted it**: `SCAN_EXTENSIONS` has
included `.yaml` since the prose half became a derived walk, so the prose half
reads a `.yaml` file's sentences and judges them under the one rule while the
measured half would not open the workflow beside them. That inconsistency is
the defect. The census now reads both spellings, and this page is why, what it
moved, and what it does not claim.

## What was measured, before anything was decided

Two scratch trees under `/tmp`. The first is a byte-for-byte copy of the
committed `ci.yml` under the other spelling, with nothing else in
`.github/workflows/`:

```
$ mkdir -p /tmp/y1/.github/workflows
$ cp .github/workflows/ci.yml /tmp/y1/.github/workflows/ci.yaml
$ git show HEAD:ec/tools/check_history_checkouts.py > /tmp/old/chc.py
$ python3 /tmp/old/chc.py --repo /tmp/y1 ; echo "exit=$?"
check_history_checkouts.py: every actions/checkout under .github/workflows/.
  no workflow was read, so nothing below is a measurement of this tree -- that is a broken census, not an empty one
  .github/workflows/: no *.yml in it
...
$ # on stderr, unwrapped here:
$ # check_history_checkouts.py: no workflow was read, so the report above is not a measurement of this tree -- that is a broken census, not an empty one, and a run that read nothing does not pass.
exit=1
```

The copy is not a straw tree. It is the workflow this repository runs, with the
one property changed that the issue is about, so the run refusing it is the run
refusing a tree the pipeline executes. With the census widened it is a
measurement and the run passes:

```
$ python3 ec/tools/check_history_checkouts.py --repo /tmp/y1 ; echo "exit=$?"
check_history_checkouts.py: every actions/checkout under .github/workflows/.
  ci.yaml / gates / Checkout: fetch-depth: 0  full
  ci.yaml / tests / Checkout: fetch-depth: 0  full
  ci.yaml / workflows / Checkout: depth 1 (the action's default)
...
exit=0
```

The second tree is the mixed one the issue asks about: the committed `ci.yml`,
copied in beside a `.yaml` derived from it. Every stated `fetch-depth` is
removed from that copy, so the one job in it that runs a history reader resolves
to the action's default of one.

```
$ mkdir -p /tmp/y2/.github/workflows
$ cp .github/workflows/ci.yml /tmp/y2/.github/workflows/ci.yml
$ cp .github/workflows/ci.yml /tmp/y2/.github/workflows/ci.yaml
$ sed -i '/^          fetch-depth: 0$/d' /tmp/y2/.github/workflows/ci.yaml
$ python3 /tmp/old/chc.py --repo /tmp/y2 ; echo "exit=$?"
$ # nothing on stderr, and the report never names ci.yaml at all
exit=0
```

**That is the case the widening earns its keep on**, and it is worth being
precise about what it was. `main()` keys the refusal on the census being
*empty*, so the conforming `.yml` beside the defect kept the run at zero, and
the shallow reader in the `.yaml` half was measured by nothing in the file.
After the widening the same tree is one failure, and the failure names the job
that caused it:

```
$ python3 ec/tools/check_history_checkouts.py --repo /tmp/y2 ; echo "exit=$?"
$ # on stderr, wrapped here:
$ #   FAIL ci.yaml/gates: runs '.github/scripts/agent-gates.sh' but its checkout is depth 1 (actions/checkout default), not `fetch-depth: 0` -- the mode will report a history requirement rather than an answer
exit=1
```

The issue proposes pinning this mixed tree as a *not found by this method*
entry, on the reasoning that a miss is the honest shape when the glob cannot see
the file. Under the widening the miss does not exist to record: the `.yaml` job
is measured like any other, so the case is pinned as a **detection** instead, in
`ec/tools/test_check_history_checkouts_yaml_census.py`. The cases beside it pin
the tree this section reproduces, the two spellings of one workflow's bytes
measured identically, the unreadable-file clause reached through the suffix that
used to be invisible, and the bound at two suffixes.

## Why widening rather than rewording the refusal

The issue offers two defensible answers: widen the census, or keep the narrow
glob and make the refusal name its cause. The second is `load_workflows()`'s
`unreadable`, which already distinguishes *directory not listed* from *no
workflow file in it*, and which `main()` discards as `_unreadable`.

Widening is what this takes, and it leaves that second answer with nothing left
to say rather than leaving it un-taken. The refusal's message describes the
causes that remain correctly — a directory that is not listed (a `git archive`
extraction, which is what
[`history-checkout-run-contract.md`](history-checkout-run-contract.md) names),
a directory holding no workflow file, and every file failing to parse — and the
narrow glob supplied one more that the message misdescribed: a directory holding
a workflow under a spelling this tool declined to read. Removing it is what
makes the message and the verdict agree, and the fix is one tuple rather than a
reworded message and the `main()` edit behind it.

**The bound is the two suffixes and nothing else.** Actions reads `.yml` and
`.yaml`, so both are read; a `.txt` or a `.json` sitting in the workflow
directory is not a workflow file however much it parses. The old docstring's
worry was a real worry about a glob that widens too far, and it is answered by
a case rather than by leaving the rule narrow.

## What is not claimed

- **That any gate or workflow runs this tool.** `check_history_checkouts()` and
  its `gate` line exist in `docs/ci/agent-gates-capture-claims.patch` and no
  commit runs them until a human lands that; #1033 is the consumer whose gate
  this makes correct to key on, not one that exists. This page changes what the
  return value *says*, and nothing about whether anything reads it.
- **That the committed tree's measurement moved.** It did not. No committed
  workflow is spelled `.yaml` — `ls .github/workflows/` is the command that
  says so, and every one is `.yml` — so the widening adds no row to the table
  [`history-checkout-claims.md`](history-checkout-claims.md) transcribes and
  moves no checkout triple. The committed run's exit code and both verdicts are
  unchanged, which is the acceptance criterion, not a claim that the change was
  large.
- **That the mixed tree above was ever broken CI.** It is a scratch tree. What
  the widening changes is that a defect in it is *reported*; that it would
  have reached the pipeline is a counterfactual about a rename nobody made.
- **Any hardware, Windows, EC or BIOS evidence.** Nothing here opens the
  laptop, a Windows machine, the EC image or the BIOS image. Every claim above
  is a tool run over committed YAML and two directories under `/tmp`.
- **That `.yaml` is now a blind spot of this tool.** It is not, and it is not
  added to the *what is not found by this method* list: under the widening it
  is read, so recording it as a known miss would state the opposite of what
  landed. What remains outside the census is unchanged, including
  `docs/ci/agent-gates-deep-schedule.yml`, which is prepared rather than landed
  and so is outside the directory the glob reads at all — a different fact from
  a spelling, and still true after this change.
- **That this page makes no claim about a committed workflow's depth.** It does
  not, and that is what the prose sweep says about it: the transcript above is a
  depth claim inside a fenced block, so the quotation rule reports it and does
  not judge it, and the file lands in the corpus suite's pinned set the way the
  #1032 and #1033 write-ups did. The claims this page argues are about a glob
  and about two directories under `/tmp`.

## The alternative, recorded because this branch took the other one

The issue's second option — threading `unreadable` through `main()` so the
verdict names its own cause, rather than widening the census — is not taken
here, and the reason is the section above rather than a preference: after the
widening no remaining cause of an empty mapping is misdescribed by the message,
so it would be a change to code that is no longer wrong. A reviewer who reads
the empty-directory string as still hiding something should read this as the
claim it is making, not as something quietly dropped.