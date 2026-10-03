# The `--self-test` transcripts are corrected, and a check holds the copies

`ec/tools/disasm8051.py --self-test` prints a summary line, and every fence
under `ec/annotations/` that quotes it was quoting a line the run no longer
prints. This corrects each of those to the current output and adds
`check_disasm8051_transcripts.py`, which holds every committed transcript to
the run, so the next one to go stale is a red run rather than something a
reader notices while reading something else.

The mechanism was already documented and deliberately not fixed.
`test_disasm8051_oracle.py`'s `TranscriptContract` holds the *producer* — the
summary line and the four `REL_SITES` rows, byte for byte — and its own
docstring recorded that a reader "discovers by noticing four transcripts have
gone stale". `disasm8051-oracle-from-the-annotations.md` carried the same
observation as a follow-up bullet. What was missing was the other half: nothing
in the tree read those `.md` files at all. A contract that holds the thing being
copied and not the copies is a contract that stops at the tool's boundary.

## What was stale, and the step-1 rationale that was wrong

Each of these files quoted an older summary line. All but the last carried one
line, replaced by the line the run prints today:

| file | what it quoted |
|---|---|
| `ec/annotations/ec-0x07d1-sites.md` | the summary without the bit-form clause |
| `ec/annotations/ec-07c4-07d5-sites.md` | the same |
| `ec/annotations/ec-0x07d0-sites.md` | the summary without *either* clause |
| `ec/annotations/pd-xdata-overlap.md` | the same |
| `ec/annotations/bank-call-audit.md` | a `tail -6` fence, stale in every line but the blank one |

The issue named three of them. Its own Done criterion — `grep -rn "self-test
passed" --include=*.md ec/annotations/` — finds the others, which sit inside
`ec/annotations/` and are quoted by exactly that grep, so leaving them would
close the issue with its own test red. `ec-07d6-07d7-sites.md` and
`ec-09e9-09eb-sites.md` were already current and are unchanged.

**The issue's step 1 explains the tail by the wrong block, and following it
produces a still-wrong transcript.** It says the `tail -6` is byte-identical to
what it was before the `BIT_SITES` work — "the new block prints at the head" —
so that only the summary line's third clause is added. It is the *read-back*
block from `disasm8051_oracle.py` that prints at the head and moves nothing.
The `BIT_SITES` block is what moved the tail, and it prints **after** the
`REL_SITES` block. Measured today, from the repository root:

```console
$ python3 ec/tools/disasm8051.py --self-test | tail -6
  ok  file 0x067F5 (runtime 0x67F5) is `b2 b4` = `cpl  p3.4`  (expected `cpl  p3.4`, image has `b2 b4`)
  ok  `c1 d0` = `clr  psw.0`  (CLR bit (0xC1), expected `clr  psw.0`)
  ok  `c2 d0` = `clr  0xd0`  (CLR direct (0xC2), expected `clr  0xd0`)
  ok  `01 ff` at 0x07FE targets 0x08FF, the *following* page (expected 0x08FF)

self-test passed: both charge-profile-flow.md windows decode identically, all 4 relative-branch sites resolve as hand-decoded, and all 11 bit-form sites decode as transcribed
```

So `bank-call-audit.md`'s block was wrong in every line but the blank one: the
`ok  file 0x0B2EE / 0x0B137 / 0x0F1B0 / 0xFE24` lines are `REL_SITES` output the
run still prints but no longer puts in its last six. The fence body is replaced
wholesale rather than having a clause appended, and the command line is
unchanged.

**Why `| tail -6` stays rather than growing.** Keeping the `REL_SITES` lines
on-topic for §8 would need a wider `tail` — `| tail -21` is the smallest
contiguous tail spanning the branch sites through the summary. That makes two
shared sentences wrong, both naming this block by its pipeline: the oracle
write-up's "The transcript contract" paragraph and `TranscriptContract`'s own
docstring. Paying two shared-file edits for a block that introduces nothing is
the wrong trade under the modularity rule, and §8 has no prose claiming the
block shows the branch sites — the summary line directly beneath it carries
"all 4 relative-branch sites resolve as hand-decoded", which is what §8 needs.
The `REL_SITES` rows are not lost from the tree:
`test_disasm8051_oracle.py`'s `TAIL` pins those rows byte for byte. (The other
`docs/findings/` copies quote the run's *end* — the textbook pair, the page-rule
edge and the summary — not the branch rows, so `TAIL` is the only place they
are held.)

Editing inside `bank-call-audit.md` §8 is safe for the oracle: neither the old
nor the new lines match `disasm8051_oracle._SECTION_ROW`, which wants a row
starting `0x` in column one after whitespace and these start `  ok  file 0x…`.
`parse_section()` and `reconcile_sites()` see no change, and that suite is
unchanged green.

## Why in-place edit rather than §4a-4d

`docs/findings.md` §4a-4d keeps a wrong **claim** visible beside its
correction, and its subject is a figure or a conclusion a reader could act on.
A transcript is a verbatim quotation of a tool's output: the line was true when
it was pasted and stopped being true when the mode grew a clause. There is no
claim to retract, and the two transcripts that were already correct are the
precedent — they carry today's line because somebody re-ran the command.
Annotating those console fences with dated corrections would be the append-log
shape `check_no_append_logs.py` exists to stop. §4a-4d is declined here, with
the reason, rather than silently not used.

## What the check holds, and the three things it declines

`check_disasm8051_transcripts.py` runs `self_test()` with stdout captured, takes
its last line, and compares every committed transcript's summary line to it
byte for byte. **The check carries no literal of its own**: it takes the line
from the run rather than restating it, so the copies are held against the
producer. A literal in the check would go stale exactly the way the markdown
does, one merge later.

`test_disasm8051_oracle.py`'s `TranscriptContract.SUMMARY` *is* a literal of
that line, and this branch does not remove it. It pins the **producer** —
asserting the run's last line against what the mode prints, which is the half
that was already there — and it is the half the copies were missing. The two
hold opposite directions of the same string, so the claim worth making is about
which is which, not about how many of it exist.

Three things are declined, counted and printed, never failed. Every one is
*not read by this method*, never *absent* — the caveat
`ec/annotations/registers.yaml` carries for a static scan:

1. **the command in an `sh` fence.** `pd-index-geometry.md` §8.2 lists
   `python3 ec/tools/disasm8051.py --self-test` as one step of a reproduction
   recipe and quotes no output at all. Editing it into a transcript would be a
   fix to nothing;
2. **a summary line under another tool's prompt.** `pd-index-geometry.md` also
   quotes `pd_index_geometry.py --self-test`, whose summary is that tool's;
3. **nothing else.** In particular the lines *between* prompt and summary are not
   held: transcripts elide the run's middle with `...` inconsistently, and
   holding those lines would pin the generated `BIT_SITES` and
   `TEXTBOOK_BIT_SITES` rows into the annotation files, making a legitimate
   addition to either table a documentation merge conflict.

Two shapes that look like declines are **failures**, because in both the corpus
has quietly shrunk and the run would otherwise stay green:

- a summary line with **no prompt above it at all** — not another tool's mode,
  since something else's prompt would say so, but a transcript of nothing, held
  by no reader;
- a `console` fence naming the command and quoting **no summary**. A fence
  written to quote a session promised one, and the fence's info string is what
  makes that decidable: `sh` and `console` are the two conventions the committed
  tree already draws, and every transcript uses `console`.

The corpus is printed by the check, not asserted here, so a merge that adds or
removes a transcript needs no edit to this file:

```console
$ python3 ec/tools/check_disasm8051_transcripts.py --verbose
```

That names every file it holds and every line it passed over, with the reason.
There is no "there are N transcripts" constant in the check and no test that
asserts one, and none in this prose. The message the run prints *does* carry the
number, and that number is computed from what the run found on this tree, so a
merge that adds or removes a transcript moves it with no edit anywhere. The
vacuity guard is that the corpus is **not empty**, not that it is a particular
size: an asserted census would be a value every merge adding a transcript has
to edit, which is the shape that has bitten this repository repeatedly.

**A red mode is not documentation drift.** If `self_test()` exits non-zero the
check prints the run's own output and exits 2 without comparing anything. A mode
disagreeing with its transcriptions is a different defect, and reporting it as a
list of stale `.md` files would be wrong in the direction hardest to diagnose
from the message alone. Exit codes are 0 clean, 1 a transcript disagrees, 2 a
red mode or a usage error.

## The corpus is `ec/annotations/` only, and why

The scoping rule is **prompt-scoped**: a `self-test passed:` line is a transcript
only when a fenced block above it names this tool with `--self-test`. That is
what makes discovery decidable — the same tool is invoked all over
`ec/annotations/` as `--at 0x…`, one decode after another, and a rule without the
flag would read every one of those as a transcript with a missing summary.

A fence marker is matched preceded by whitespace, by `>` blockquote markers, or
by both, and the opening marker's prefix is stripped from the block's body. That
is not an optimisation: several files under `ec/annotations/` already write
fenced blocks inside list items and blockquotes, and a reader that recognised
only a column-one marker would drop an indented transcript out of the corpus
without declining it — the same quiet shrinkage the two failure shapes exist to
prevent. No committed transcript sits in an indented fence today, so the verdict
this branch verified is the same either way; the shape is read so that writing
one there is not a silent hole.

`docs/findings/` is out of scope rather than half-covered, and the reason is not
that its copies lack prompts — several carry a valid `$ python3
ec/tools/disasm8051.py --self-test` line and a prompt-scoped walk would find
them. The reason is that **the same directory holds transcripts this rule cannot
reach**, so a rule aimed at it would cover the directory unevenly and quietly,
which is worse than a stated boundary:

- `disasm8051-self-test-gate.md` quotes the summary inside a fence whose prompt
  line is a scratch `$ bash …/agent-gates.sh`, not the command that printed it;
- `disasm8051-oracle-from-the-annotations.md` quotes it in a gate-output block
  whose `$ ` prompt is the same scratch gate.

Both are current today and stay that way by re-running. Covering them needs a
discovery rule that does not lean on the prompt, which means deciding what a bare
console fence quoting a tool's output is when the tool is never named on that
line. That is a follow-up, not something half-solved here.

`docs/findings.md` is frozen and stays frozen: this is a new file and nothing
else, and the generated `docs/findings/INDEX.md` carries it.

## Not claimed

No hardware, no capture, no EC, no register read back, nothing deferred to a
human at the machine. The check reads committed markdown and one committed
image — the same input the gate's own arm reads — and compares strings. No
`status:` in `ec/annotations/registers.yaml` moves, and nothing here is evidence
about the laptop.

## Follow-ups this opens

- **Gate wiring for the new check.** `.github/scripts/agent-gates.sh` is an
  `ElDavoo/agent-pipeline` template copy under `.github/`, which this
  repository's push token cannot write, so a branch touching it fails at the very
  end. The sanctioned route is a prepared patch under `docs/ci/` plus an entry in
  `tools/test_agent_gates_patches.py`, which requires every patch to apply in
  every ordered pair — a shared-file conflict magnet several open branches share.
  `test_disasm8051_oracle.py` is likewise ungated today, so this is the same
  shape as an existing gap rather than a new one.
- **The `docs/findings/` copies.** Covering them needs a discovery rule that does
  not lean on the prompt, which means deciding what a bare console fence quoting
  a tool's output is when the tool is not named on that line. Stated rather than
  guessed.
- **A transcription for `BIT_SITES` / `TEXTBOOK_BIT_SITES`.** The oracle's
  docstring names this as the reason those rows stay literals rather than read
  back out of markdown. Without one, the middle of the run cannot be held either,
  and only the summary line is checked. Same cost that branch declined for the
  `0xB330` block.
- **The `...` elisions.** Some transcripts elide the run's middle and some quote
  it whole. Left alone: inserting `...` into files that are already correct is a
  cosmetic edit to shared files that changes no claim.
