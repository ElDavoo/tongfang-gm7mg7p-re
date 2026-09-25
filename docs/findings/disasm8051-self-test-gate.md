# `disasm8051.py --self-test` is the oracle for the opcode tables, and no gate
# runs it (2026-09-25, issue #798)

What this branch adds is **a prepared patch, not a line in the gate**:
`docs/ci/agent-gates-disasm8051-self-test.patch`, for a human to land with
`git apply`. The reasoning is here so the shared files carry only pointers;
`../agent-pipeline.md` item 11, [`../findings.md` §49](../findings.md) and
[`../../ec/README.md`](../../ec/README.md) each say one sentence and link back.

**Nothing in this branch is a claim that CI runs this.** It does not, until a
human lands the patch. The gate's own `grep -rn "disasm8051.py --self-test"
.github/` returns nothing on the merged tree, and it returns nothing after this
branch either — that is the whole reason the patch is prepared rather than
landed, for the reason [`0751-grader-self-test-gate.md`](0751-grader-self-test-gate.md)
gives: `.github/scripts/agent-gates.sh` is copied from the `agent-pipeline`
template and the pipeline's push token has no `workflow` scope, so a branch
editing it fails at the *end* of a PR rather than the start of one.

Nothing below is a register behaviour, a live test, or evidence about the
laptop. The mode reads a committed firmware image, a committed annotation file
and a hard-coded table. No capture is opened, no EC is opened, no register is
read back, and **no new hardware observation is needed to close this issue** —
so nothing here is deferred to a human at the machine.

## The gap, and why it is load-bearing rather than tidiness

`ec/tools/test_disasm8051.py:3-6` opens by naming this mode as the oracle it
does not replace:

> `disasm8051.py --self-test` holds the r2 hand transcriptions, which are the
> oracle for the opcode and mnemonic tables: if one of those changes, those
> windows disagree with the listing.

And [`../findings.md` §3e](../findings.md) carries a claim on it at
[`:355-356`](../findings.md): no 8051 direct-addressing opcode takes a 16-bit
operand, so a `0xFFxx` value "**cannot** be a direct address whatever anything
spelled it as" — and the sentence says of the `OPCODE_LEN` table behind it that
"its own `--self-test` pins" it. That claim is what settles §3e's ten
`0xFFxx`-in-`pd-001` addresses as XDATA, and the table is 256 entries wide.

So the mode named twice as load-bearing ran in no gate, in either tier:

```console
$ grep -rn "disasm8051.py --self-test" .github/ ; echo $?
1
$ python3 ec/tools/disasm8051.py --self-test > /dev/null ; echo $?
0
```

Both numbers are the point. It is green today, and it is not run today. This is
*not* [`0751-grader-self-test-gate.md`](0751-grader-self-test-gate.md)'s
situation, where the prepared check is held back because the mode is red — a
patch that would turn the gate red is the cheapest way to make a gate get
switched off, and this one does not.

## What the mode holds: five groups, 36 assertions

The issue names two. The mode holds five, and a note that listed only the first
two would be under-calibrated by omission, so the call-site comment and the
patch header both say all five.

| group | n | what it is |
|---|---|---|
| `SELF_TEST` | 18 | the two `ec/annotations/charge-profile-flow.md` windows, decoded and diffed byte-for-byte against the `r2 -a 8051` hand transcriptions (11 instructions at `0xB12C`, 7 at `0xB2E2`) |
| `REL_SITES` | 4 | `relative_target()` against four hand decodes in `bank-call-audit.md` §8 — two of them backward branches the windows contain none of, and `0xFE24` as the last-byte-not-second-byte case |
| `BIT_SITES` | 11 | the mnemonics against the bit-addressed carry forms the windows contain none of, each transcribed from `r2 -a 8051` against the image |
| `TEXTBOOK_BIT_SITES` | 2 | the `0xC1`/`0xC2` `CLR` pair, stated from the manual rather than transcribed — it exists precisely *because* an oracle derived from the tool under test asserts nothing, and the pairing is what catches a decoder keying on operand text |
| page-rule edge | 1 | `paged_target(0x01, 0xFF, 0x07FE) == 0x08FF`, the `ajmp` page rule at its last-two-bytes edge |

The last two are the ones a reader of the issue would not expect, and both are
cases where a **weaker** oracle would have passed. `0xC1` and `0xC2` differ only
in the opcode; a decoder that keyed on the operand text would collapse them and
`disasm8051.py:189-193` keeps them in a separate table for that reason. The page
edge is stated rather than transcribed because this firmware has no `ajmp` in a
page's last two bytes to hand-read — and reading the page off the *site* rather
than off the *following address* would give `0x00FF` and still decode every
`ajmp` in the listing to something.

## What it does not hold

The patch header carries the same list; it is not optional, because the natural
misreading of "the oracle for the opcode tables" is "it checks the opcode
tables."

- **It is not a disassembler check.** `r2` is in the *provenance* of the
  transcriptions, not in the run. No `r2`, no assembler, no Ghidra, no network,
  no `sdas8051` — one committed image and a hard-coded table.
- **It covers 18 of `OPCODE_LEN`'s 256 entries, by transference.** A row change
  outside those windows is not caught, and the windows contain none of the
  bit-addressed carry forms. "Pins the table" means "would disagree with these
  18 hand transcriptions", which is a real property and a narrow one.
- **It says nothing about `decode()`'s bounds contract.** That has its own
  suite, `ec/tools/test_disasm8051.py` (#688), which `tools/run-tests.sh`
  collects and **no gate calls**. So both halves of this decoder's own testing
  are ungated today, in two different ways: one would need this patch landed,
  the other needs a gate call nobody has prepared.
- **It arbitrates none of the `0xA0`/`0xB0` `ANL C,/bit` / `ORL C,/bit`
  disagreement** that `disasm8051.py:176-186` leaves open on purpose — Ghidra's
  SLEIGH, `r2` and `sdas8051` all put `ORL` at `0xA0`, the MCS-51 manual as
  reproduced in common references has them the other way round, and none of the
  three arbitrating the other two is why that is a comment and not a
  correction. No committed instruction is affected either way (all 12
  occurrences sit inside the 45,394 the re-encode covers), so the self-test's
  silence on it is correct rather than a gap.

## Two corrections to the issue's reading, both measured

**1. Its line numbers are off by a few throughout.** The tool list is `:119-129`,
not `:118-129`; the `*)` arm is `:238-242`, not `:239-243`;
`*gen_xdata_symbols.py)`'s arm is `:134-136`, not `:131-136`; the
`xdata_register_map.py` comment is `:210-234`, not `:214-231`;
`disasm8051.py`'s default-path lines are `:506-508`, not `:505-509`. The anchors
in the patch are taken from the file as it stands. This is the same class of
drift the 0751 header records about its own re-cut, and it is why the patch is
cut with `git diff` rather than by hand.

**2. The self-test holds more than the issue lists** — the `0xC1`/`0xC2` pair and
the page-rule edge, on top of the two windows, the four branch sites and the
eleven bit-form sites. Thirty-six assertions in five groups, not 33 in three.
The issue's figure for the part it *does* name is exact: the run prints
`self-test passed: both charge-profile-flow.md windows decode identically, all 4
relative-branch sites resolve as hand-decoded, and all 11 bit-form sites decode
as transcribed`.

## The two hunks, and the placement constraint that forces them

`tools/test_agent_gates_patches.py` applies the set in **every ordered pair**
against a scratch copy of the committed script. Two hunks cutting one
contiguous region cannot both be independently applicable — whichever lands
first inserts a line between the other's leading and trailing context. The
contested regions, read off the committed file:

| region | held by |
|---|---|
| tool list `:119-124` | `agent-gates-gap-text-check.patch` hunk 1 |
| tool list `:123-128` | `agent-gates-0751-self-test.patch` hunk 1 |
| arms `:162-167` | `agent-gates-gap-text-check.patch` hunk 2 |
| arms `:189-194` | `agent-gates-0751-self-test.patch` hunk 2 |
| `check_register_counts` region, `gate` list `:271-277` | capture-claims, testdata-row-claims |

The union of the two tool-list windows is `:119-128`. **`:129` — the
`windows/tools/decompile_native.py; do` line — is the only line in the list
outside every one of them**, which is why hunk 1 splits that line rather than
inserting a new one above it. Hunk 2 takes the other end of the arm list, where
`*)` at `:238` is the first line past the `:189-194` window.

So **the tool-list entry is not grouped with the other `ec/tools/` paths**, and
**the arm is not beside its semantic neighbour** `*citation_gap_scan.py)`. Both
are placement-for-composition. List order here is cosmetic — the loop is over a
`for tool in` word list and nothing reads the order — and **"tidying" either
placement back to where a reader expects it breaks every-ordered-pair landing**,
while each patch still applying cleanly alone, which is the failure mode
[`prepared-gate-patches.md`](prepared-gate-patches.md) exists to catch. The
patch header says this in the same words a reader landing it will need, rather
than leaving the odd-looking placement to be "tidied" by the next person.

The alternative — one hunk, both halves contiguous — was not available. The two
regions are 107 lines apart and the arms between them are two other patches'
context windows.

## The test

Two parts, and the second is the one that matters.

1. **Mechanical, already in the tree.** `tools/test_agent_gates_patches.py`
   gains the path in `PATCHES` (mandatory, not a nicety:
   `discover_patches()` globs `docs/ci/agent-gates-*.patch`, so a committed
   patch the suite does not list fails `test_every_patch_on_disk_is_listed`
   immediately). That makes the existing cases do the work: it applies alone,
   lands after each of the other four in **both** orders, and the full
   five-patch set lands and still parses under `bash -n` **and** `shellcheck`.
2. **One new case, `ArmRetentionTests`, in the `FoldTests` shape.** It asserts
   the landed gate carries both `ec/tools/disasm8051.py; do` and the two-line
   `*disasm8051.py)` / `python3 "$tool" --self-test || rc=1` / `;;` arm as one
   string. The reason: a future re-cut that keeps the tool-list line and drops
   the arm **applies cleanly and passes every other case in the suite**, and the
   drop is precisely what hands the tool `--work "$scratch"` back — the failure
   the issue's second bullet exists to prevent. The arm is one string rather
   than the two lines the issue names because
   `python3 "$tool" --self-test || rc=1` is *already* in the
   `merge_annotation_shards` and `grade_0751` arms, so checking it on its own
   would pass with this patch's arm dropped — the exact case the case exists to
   catch.

Each was checked against the mutation it is supposed to catch, because a suite
that cannot fail is worth nothing. Both mutants — one dropping the arm, one
dropping the list entry — apply cleanly alone, land in every ordered pair, and
pass `bash -n`, `shellcheck`, `test_each_patch_applies_on_its_own` and
`test_each_header_applies_its_own_path`. **`ArmRetentionTests` is the only case
that fails, in both directions.** That is the same reason `FoldTests` exists.

## What was verified, and how

Applied to a scratch tree holding only `.github/scripts/agent-gates.sh`, then
run from the repository root so the tools' relative paths resolve:

```console
$ T=$(mktemp -d); mkdir -p "$T/.github/scripts"
$ cp .github/scripts/agent-gates.sh "$T/.github/scripts/"; (cd "$T" && git init -q .)
$ (cd "$T" && git apply ~/.../docs/ci/agent-gates-disasm8051-self-test.patch)
$ bash "$T/.github/scripts/agent-gates.sh"          # cwd = repo root
```

The `=== ghidra tooling ===` block now ends with all five groups, the four
branch sites, the eleven bit sites, the textbook pair and the page-rule edge:

```
  ok  `c1 d0` = `clr  psw.0`  (CLR bit (0xC1), expected `clr  psw.0`)
  ok  `c2 d0` = `clr  0xd0`  (CLR direct (0xC2), expected `clr  0xd0`)
  ok  `01 ff` at 0x07FE targets 0x08FF, the *following* page (expected 0x08FF)

self-test passed: both charge-profile-flow.md windows decode identically, all 4 relative-branch sites resolve as hand-decoded, and all 11 bit-form sites decode as transcribed
ghidra tooling: passed
```

and the run closes:

```
=== doc links ===
doc links: passed

note  this tier does not run: the sdas8051 re-encode of the committed
      listing, and the advisory cross-decoder comparison. Both are in
      agent-gates-deep.sh, which AGENT_GATES_DEEP=1
      .github/scripts/agent-gates.sh runs after this.

All gates passed (14s elapsed).
```

The timing is 0.02 s for the mode itself, over five runs, against a cheap tier
`../agent-pipeline.md` records at 5.9 s. That is one runner's figure and the
ratio is the point; item 6 gives the same caveat for `call_graph.py`.

**The unittest runner is red, and this branch does not fix it.**
`bash tools/run-tests.sh` on this tree: **30 suites, 875 tests, one failing** —
`ec/tools/test_xdata_cluster_names.py::TheGuardOffRegeneration`, which reports
that "the `==` guard is not where §6a's recipe deletes it". It reads
`ec/tools/xdata_register_map.py` and the committed decompile, neither of which
this branch touches, and it is the failure
[`runner-red-suite-set.md`](runner-red-suite-set.md) and
[`prepared-gate-patches.md`](prepared-gate-patches.md) already record; the plan
this branch was built from expected **two** red suites, and the other one,
`ec/tools/test_check_site_census.py`, is green since §48's `census_refs`
re-derivation. So the honest reading is one known failure, not two, and this
branch is not a pass because of it. `tools/test_agent_gates_patches.py` itself
reports **15 tests, passed**.

**Read the transcript for what it is.** It is a *landed copy in a scratch tree*,
not CI. CI runs the committed `.github/scripts/agent-gates.sh`, which does not
contain these two hunks and will not until a human applies the patch. The
`doc links` gate passing is also the check over the new `.md` links in this
branch.

## The deep tier is the neighbouring half, and is not this issue

The cross-decoder ratchet over `ec/ghidra/cross-decoder.csv` belongs to
`agent-gates-deep.sh`, not here. The cheap tier prints at `:284-287` that it
does not run the cross-decoder, that note is deliberate, and **#774** owns the
unlanded `docs/ci/agent-gates-deep-schedule.yml` that would carry it. This
write-up says so rather than widening the patch to reach it — the patch is
already at the limit of what the collision analysis allows.

Wiring `tools/run-tests.sh` into a gate is the other neighbouring half, and is
**not** done here for the same reason: `../agent-pipeline.md:342-379` records the
recipe and says deliberately not the gate call, and **#775**/**#773** own it.
It is named because this branch's "what it does not hold" list depends on that
gap staying open: close the `run-tests.sh` gap and `test_disasm8051.py`'s bounds
contract becomes gated too, and that sentence becomes stale.

Also out of scope, deliberately: **re-opening §3e.** This makes the mode that
pins `OPCODE_LEN` runnable per commit. It does not revisit the `0xFFxx`-is-XDATA
conclusion, which stands on its own argument about instruction encodings and
which this issue does not touch.

## Follow-ups this opens

- **`ec/tools/test_disasm8051.py` — the bounds contract — still runs nowhere**,
  because `tools/run-tests.sh` has no gate call. One of the two halves of this
  decoder's own testing is now gated once this patch is landed; the other is
  not, and does not become gated by it.
- **The `0xA0`/`0xB0` `ANL`/`ORL C,/bit` assignment stays unsettled.** No
  committed instruction is affected either way, so nothing is blocked on it and
  the self-test's silence on it is correct rather than a gap.
- **If the tool list ever grows enough that the `:119-128` collision band widens
  into `:129`**, a re-copy of the template plus a sixth prepared patch would need
  the same re-anchoring the 0751 header records, and this patch would have to be
  re-cut rather than re-based. Worth knowing before the eleventh tool becomes
  the twelfth; it is not a change to anything today.

## Drop order, if this needs a rebase

`../../ec/README.md`'s clause and this file's entry in
[`prepared-gate-patches.md`](prepared-gate-patches.md) go first — both are pure
pointers whose content the patch header and this write-up already carry. Then
[`citation-gap-scan.md`](citation-gap-scan.md)'s correction, which this file can
carry instead with a pointer back. **`tools/test_agent_gates_patches.py` does
not drop**: without the `PATCHES` entry the branch is red on
`test_every_patch_on_disk_is_listed`, and without `ArmRetentionTests` a later
half-re-cut passes silently.
