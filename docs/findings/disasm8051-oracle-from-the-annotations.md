# The two hand transcriptions are re-read now, and the sentence the gate comment carries is true (2026-09-26, issue #811)

`disasm8051.py --self-test` is the oracle for the two opcode tables: the
`SELF_TEST` and `REL_SITES` tuples are the hand transcriptions, and if
`OPCODE_LEN` or `mnemonic()` changes in a way that disagrees with one of them,
the tables are wrong. That much was already true.

What was not true is the sentence that comes next. `self_test()` had exactly one
`open()`, on the firmware image; the two `.md` files were named in **comments** at
the top of each table as where the rows were transcribed *from*. That is
provenance, not a check, and it left a drift hole the thesis depends on: correct
`charge-profile-flow.md`, and the literals kept the old text, `--self-test` stayed
green, and a green run said nothing about the file a reader is told it checks. It
was worse in the failure direction — the `self-test FAILED:` line named two files
the run had never opened, so a red run pointed a human at a `.md` to read for a
disagreement the code could not have observed.

## What this branch adds

`ec/tools/disasm8051_oracle.py`: the two listing parsers and the two
reconcilers, imported **inside `self_test()`**. Eleven tools under `ec/tools/`
`import disasm8051` for its opcode tables, and none of them wants a
`--self-test`-only dependency on a markdown parser — so the import stays lazy
and the sibling is resolved off `Path(__file__).resolve().parent` rather than off
the cwd, exactly as `main()`'s firmware default already is. A new standalone tool
would have left the same sentence false, because the only thing the prepared gate
arm runs is `python3 "$tool" --self-test`; closing the hole inside the mode is
the only place the claim can become true.

**The two files are in two different listing dialects, and that is why this is
decidable rather than a text-diff guess.** `charge-profile-flow.md` writes in the
decoder's own style — `jb   acc.0,0xb141`, two spaces after the mnemonic, no
space after the comma, `; trailing comments`, `0xb141   ...` elisions.
`bank-call-audit.md` §8 quotes `r2 -a 8051` **verbatim** inside a `console`
fence — `jb acc.0, 0xb141`, a space after the comma, and r2's box-drawing branch
glyphs (`┌─<`, `╎`, `└─>`) ahead of the address column. A single text normaliser
would have been the fragile part of the whole change, so there isn't one: the
windows compare on the full text, which is one dialect, and the branch sites
compare on **bytes and target** — the hex column and the trailing `0x....` —
which are the same in both. A case in the suite records that the two spellings of
`0xB137` really do differ, so the choice is visible rather than incidental.

## What is checked, and what is not

| group | n | reconciled against |
|---|---|---|
| `SELF_TEST` | 18 | the `charge-profile-flow.md` rows inside each window's own span |
| `REL_SITES` | 4 | the `bank-call-audit.md` §8 listing at that address, on bytes and target |
| `BIT_SITES` | 11 | **nothing — no committed transcription exists to reconcile against** |
| `TEXTBOOK_BIT_SITES` | 2 | **nothing — stated from the manual on purpose** |
| page-rule edge | 1 | **nothing — arithmetic, deliberately not transcribed** |

The last three rows are the calibration, and the wording is the repository's own
for an unsearched population rather than an empty one. `grep -rn
"0xEDA4\|0xeda4" --include=*.md ec/annotations/` returns nothing, and `0x9287`
appears in the annotations only as one end of an anchor span, never as a
transcription — so the bit-form sites are **not found by this method**, which is
not the same as `registers.yaml`'s own caveat about a static scan finding no
reference. Writing a listing to hold them would be a transcription project, not
a parsing one.

## The vacuity guard, which is the whole point

A parser that finds nothing reconciles perfectly: an empty parse equals an empty
window span, and a missing address is not a disagreement if nothing is looking
for it. Three shapes are therefore refused rather than passed, each with a case:

- a window whose span covers **no parsed row**;
- a `.md` with **no fenced block** at all (and, for §8, a file whose `## 8.`
  heading is gone — a `## Eight.` would otherwise leave the parser scanning a
  file that still parses);
- a `REL_SITES` address **absent from §8**, which is a failure and never a skip:
  a skipped row would leave an entry that nothing has ever checked reading
  exactly like one that was checked and agreed.

An unreadable file is a *reported problem* rather than a traceback, and one
unreadable file does not take the other file's verdict down: a run whose
`charge-profile-flow.md` has gone still checked the four branch sites, and
saying so is more use than a total that means nothing.

**The one the positional comparison gets wrong, which is why the windows compare
by address.** Pairing the parsed list against the expected list in order and
reporting the pairs that differ is the obvious version, and it fails two ways
that both read as *green*. A row **removed** from a window leaves every surviving
row still paired with a row that agrees, so the ordered zip reports **nothing
at all**; and a row **added** is reported as a cascade of text disagreements one
address to the right, none of which is the address that actually changed. Keyed
on the address, each edit is one line naming the address it is about, and a row
listed twice in one span is its own line rather than a silent last-wins. Both
shapes are in the suite, and so is the same removal wearing the other spelling —
an elision `...` written over a real row, which the parser drops, so nothing
downstream ever sees the row to notice it is gone.

## The 0xB330 block is reported, not added

`charge-profile-flow.md` §2 transcribes a second block at `0xB330` (`BALANCED`,
R3 = 100) that `SELF_TEST` has never carried. The mode prints one line naming it
and saying that nothing checks it, and the line is a **report, not a finding**:
the block is transcribed and correct, it is simply not in the table. Adding it
would move the "36 assertions" figure in the patch header, in
`disasm8051-self-test-gate.md`, in `docs/findings.md` §49, in `ec/README.md` and
in `docs/agent-pipeline.md` item 11, for a reason no issue asked for. The parse
therefore yields all 24 rows and the reconciler reports the 6 the table does not
carry, so a file that grew a *third* block would show there too.

## What was verified, and how

`--self-test` is green on the committed tree, and red on every mutation:

```console
$ python3 ec/tools/disasm8051.py --self-test > /dev/null ; echo $?
0
$ bash tools/run-tests.sh ec/tools
```

The mutations are the ones that matter and each is a case, not a claim:
`0xB130`'s operand re-transcribed; a row added inside a window; a row removed
from a window; that removal as an elision; the `0xB137` §8 line retargeted; §8's
byte column for `0xF1B0` edited; §8's target for `0xFE24` edited. The suite was
then itself mutated, in the oracle rather than in a `.md`, to show it can fail:
returning no problems at all (**9 failures**), comparing the windows by position
again (**1 failure, 16 errors**), dropping the no-fence refusal (**1**), turning
the missing-`REL_SITES`-address refusal into a skip (**8**), and matching
elisions instead of dropping them (**2**). Every one is red; the tree is green.

**The transcript contract.** Five committed transcripts quote `--self-test`'s tail
verbatim — `disasm8051-self-test-gate.md`, `ec-07d6-07d7-sites.md`,
`ec-09e9-09eb-sites.md` and the `tail -6` at `bank-call-audit.md` — so the new
block prints immediately after the image is read and **before** the window loop,
every existing `print` keeps its text, and the summary line gains no clause. The
suite asserts the summary line and the four `REL_SITES` lines byte for byte, and
asserts that everything the read-back prints lands above the first `    0x` row.
The fourteen `BIT_SITES` / `TEXTBOOK_BIT_SITES` / page-edge lines are counted and
their ends pinned rather than pinned whole, because those are generated from
tables the suite holds elsewhere and pinning them here would make a legitimate
addition to `BIT_SITES` a failure of this file.

(For the record, and not this branch's job: several of those transcripts are
**already** stale — `bank-call-audit.md`, `ec-0x07d1-sites.md` and
`ec-07c4-07d5-sites.md` quote a pre-`BIT_SITES` summary. This branch adds no
sixth stale one and fixes none of the existing ones; that is a separate pass.)

## The patch needed no change, which is worth saying

`docs/ci/agent-gates-disasm8051-self-test.patch` is **untouched**, and so is
`tools/test_agent_gates_patches.py` — 15 cases, green unchanged, which is itself
the evidence the patch was not disturbed. Both sentences the issue quotes as
false — the header's "the two hand transcriptions in `ec/annotations/`" and the
`case` arm's "It reads a committed image and a committed annotation file" —
become true the moment the code reads the files, so the patch's hunks, its `@@`
line counts and its `ArmRetentionTests.REQUIRED` string (which sits *below* the
comment, at the arm body) are all unaffected. **A future re-cut should not go
looking for a correction to make here.** This is also the modularity result: the
`--self-test`-only claim is held by the mode, so nothing outside it moved.

The patch's own scenario was run end to end rather than reasoned about, with the
gate script patched into a scratch copy and executed from the repository root so
the tools' relative paths resolve:

```console
$ T=$(mktemp -d); mkdir -p "$T/.github/scripts"
$ cp .github/scripts/agent-gates.sh "$T/.github/scripts/"
$ (cd "$T" && git init -q . && git apply .../agent-gates-disasm8051-self-test.patch)
$ bash "$T/.github/scripts/agent-gates.sh" ; echo $?
  --  6 rows at 0xB330..0xB33A in charge-profile-flow.md are transcribed and are not in SELF_TEST, so nothing here checks them
  ok  22 transcribed rows in SELF_TEST and REL_SITES re-read from ec/annotations/ and reconciled
self-test passed: both charge-profile-flow.md windows decode identically, all 4 relative-branch sites resolve as hand-decoded, and all 11 bit-form sites decode as transcribed
ghidra tooling: passed
0
```

The new block is at the head and the summary line is the one five transcripts
quote, which is the whole of what the placement constraint was for. **The gate
still does not run this until a human applies that patch** — the run above is a
scratch copy, and `grep -rn "disasm8051.py --self-test" .github/` still returns
nothing on the committed tree.

## The new failure mode, stated

From now on an edit to `charge-profile-flow.md`'s listings or to §8's r2
transcript can turn the cheap tier red **through a prepared patch**, once a human
lands it. The natural first reaction to a red gate is to switch it off, so
`docs/agent-pipeline.md` item 11 now says what a red run from this check means:
it means a transcription and the table built from it disagree, and which of the
two is wrong is a question about the *bytes*, answerable in `r2 -a 8051` against
a `make_bank_image.py` image. It is the cheapest possible red to diagnose, and
it is red in the direction the whole oracle exists to catch.

## Not claimed

No hardware, no capture, no EC, no register read back, nothing deferred to a
human at the machine. The check reads **two committed markdown files, one
committed image and a hard-coded table**. No `status:` in
[`../../ec/annotations/registers.yaml`](../../ec/annotations/registers.yaml)
moves, and nothing here is evidence about the laptop.

Two other suites remain where they were: `ec/tools/test_disasm8051.py` — the
`decode()` bounds contract — still runs in **no gate**, and
`ec/tools/test_disasm8051_oracle.py` is likewise collected by
`tools/run-tests.sh` and called by no gate. Its docstring's first sentence
("`disasm8051.py --self-test` holds the r2 hand transcriptions, which are the
oracle…") is more true after this branch, not less. Wiring either into a gate is
`docs/ci/`'s job and not this one.

## Follow-ups this opens

- **The two unparsed groups stay literal, and that is now a *stated* gap** rather
  than an unstated one: 11 `BIT_SITES` and the `0xC1`/`0xC2` pair have no
  committed transcription to reconcile against. A follow-up could add one, at
  the cost this branch declined for `0xB330`.
- **The pre-existing stale transcripts** listed above.
- **The `0xA0`/`0xB0` `ANL`/`ORL C,/bit` disagreement** stays deliberately open
  in `disasm8051.py`, where no committed instruction is affected either way.
