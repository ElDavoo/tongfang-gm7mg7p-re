# #658 asked for a pin that #849 had already laid: the `OWNERSHIP` main-EC keys, and the one line that could not show its own drift

**Written 2026-09-28, against `300dfb30`.** Every line number below is that
commit's. Nothing here is a hardware, firmware or Windows claim: no image is
opened, no register is read back, no capture is taken. What is read is the
committed tool and the committed findings, and what is run is
`xdata_register_map.py --self-test` and a one-line perturbation of it that is
reverted in the same working tree.

## What the issue asked, and what was already on the tree

Issue #658 asked for `OWNERSHIP["main_distinct"]` and `OWNERSHIP["main_refs"]`
to be computed per-group in the `--self-test` ownership block, asserted there
against the constant, and for the comment claiming `main_refs` was unasserted
to be updated. **That work is on the tree, and landed by issue #849.** The
residue was two things, and both are named below: the one place where the new
check could not show its own drift, and the one sentence still asserting the
gap, which is the sentence the followups pass read to file #658 in the first
place.

**The issue's own figures are a pre-#279 snapshot, and they are kept here
rather than replaced.** #658 quotes `8,546` / `1,062` from
[`xdata-export-ownership-page-census.md`](xdata-export-ownership-page-census.md),
measured by #654 before #279 re-pinned; that file's 2026-09-25/#279 banner at
`:21` already says its numbers are what the #654 runs printed and not the
current census. The pins on this tree are `1218` / `9320`, not the issue's, and
the disagreement is a dated snapshot rather than a second finding. **Reading
the issue's numbers as today's is what makes a duplicate look like a gap.**

## The four "Done when" criteria, and where each is satisfied

| #658's criterion | where the tree satisfies it |
|---|---|
| `--self-test` computes and asserts both keys | `ec/tools/xdata_register_map.py:4368-4378` — `own_main_refs` is summed beside `own_refs` (`:4357`) and both keys are read by the same `check()` |
| the comment no longer claims `main_refs` is unasserted | `ec/tools/xdata_register_map.py:1444-1451` — "**Every key below is read by a check in the --self-test ownership block**", naming the check. The sentence the issue quotes verbatim does not exist in the tool |
| perturbing `main_refs` by one makes the mode exit non-zero | `check` clears `ok` (`:3401-3405`), `self_test` returns `0 if ok else 1` (`:4600`), `main()` ends in `sys.exit(main())` (`:5106`). This was true before this change, but the line could not *show* it — see the next section |
| `agent-gates.sh` green | `.github/scripts/agent-gates.sh:262-263` runs `--check && --self-test \|\| rc=1` for this tool |

**The issue is not wrong about the tree it was written against; it is written
against a tree that no longer exists.** It quotes the old `OWNERSHIP` comment
verbatim and cites `OWNERSHIP` at `:1006-1027` and that comment at `:1014-1016`,
whereas on this tree the constant is at `:1452` and the comment at `:1444-1451`.
#849 landed in between and rewrote the comment, so the sentence the issue
quotes is one this tree no longer contains at any line. **An issue citing a line
that has since moved is a snapshot, in the same way the census file's figures
are** — which is the whole reason the four criteria above are recorded by path
and current line, so the next reader of #658 can check rather than re-derive.

## The one residue: a FAIL line whose expected and got agreed

The check printed the **measured** value in the expected slot. `own_main_refs`
appears twice in the message — once where the pinned value belongs, once in the
`got` — so `OWNERSHIP['main_refs']` never appeared in the line at all, and a
perturbed pin produced this, on a tree where the check was working exactly as
intended:

```
  FAIL  and its main-EC half is 1218 distinct / 9320 references, the per-program line the 6b console block prints (got 1218/9320)
```

**`9320` and `9320` agree, and the line is marked FAIL.** Nothing on it names
the number being held; the pin that had moved by one was the only value in the
constant not printed, and the shape is worse than an unhelpful message because
it is a message that reads as self-consistent. The sibling check just above it
(`:4359-4362`) uses expected-then-got properly and does print
`OWNERSHIP['refs']`, so this was one check departing from the block's own
convention rather than a block-wide style.

The same perturbation on this tree, after the change:

```
  FAIL  and its main-EC half is 1218 distinct / 9321 references, the per-program line the 6b console block prints (got 1218/9320)
```

`9321` is the pin as edited, `9320` is what the committed census measures, and
the difference is one edit. This is #658's done-when #3 — **and the
perturbation is what makes the fix observable**: before it, that same run
printed `9320`/`9320` and the criterion could not be checked from the output at
all, only from the exit code. The binding at `:4368` is unchanged, because the
predicate at `:4377-4378` needs the measured value; only the message changed.

**Nothing was re-pinned or re-derived here.** `main_refs` is where #279 put it
and `own_main_refs` is what the committed tree measures, so the two agree and
there was nothing to move. A re-derivation that moved the pin should fail this
check, which is the whole point of it.

## What this file is not

The substance is not forked here. The record of *why* the `main_*` pair was the
sharpest case of an unheld figure — "a value in a constant that no check reads
is a promise wearing the costume of a pin" — is
[`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md)
§2b, where #849 closed the `main_*` pair and #850 the other four rows. That file
cites this check at `ec/tools/xdata_register_map.py:4315-4319` and `OWNERSHIP`
at `:1414`, which were this check's and the constant's lines on an earlier tree;
they are left there rather than re-cut, because a write-up about a different
figure is not the place to re-number another one.

**No new test file.** A committed case asserting `main_refs == 9320` would be a
test that asserts a count of the tree, which is a value every merge has to
edit, and `ec/tools/test_xdata_register_map.py` is the refusal-contract suite
rather than the home for a pin. The standing gate is `agent-gates.sh`; the
perturbation above is a manual step and its output belongs in the PR body,
where it is dated by the run that produced it.

**Still unheld in that same table, and named so the next pass need not
rediscover it:** the `157`/`858` PD pair, which checklist §2b records as left
open for a narrow reason — `ORACLE["extmem_pd_*"]` measures the **default**
census's token spellings and `OWNERSHIP` carries no `pd_*` key at all. The two
`main-ec-002`/`main-ec-003` cluster rows stay unpinned; #654 decided that on the
record and #658 did not reopen it.
