# The digest step the two component READMEs were missing, the message that calls the repository's own convention corruption, and a timing figure with three generations (issue #372)

(2026-09-27. Static reading of committed files plus three commands named
below. No image is opened, no register is read back, and no laptop, EC or
Windows machine is involved: this is prose and one message string, checked on
a GitHub-hosted runner.)

## The claim

**The pages that describe how to regenerate a `.c` come in two kinds, and the
digest-refresh mode was documented in only one of them. The two component
pages — the ones other documents here cite as authoritative for their
component, and one of which carries the canonical recipe — said nothing about
it.**

The digest machinery is right. Every committed `.c` under a component's
`decompiled/` has a row in `<component>/ghidra/c-digests.csv`, and the row count
equals the file count in each of the three trees (re-derive with
`tail -n +2 <component>/ghidra/c-digests.csv | wc -l` against
`find <component>/decompiled -name '*.c' | wc -l`). The bug is that a person
who runs the documented command, gets a legitimate new export, and then runs
the documented check is told their tree is broken, and the one command that
fixes it is in a file they were never sent to.

That is not a hypothetical path. The two blocks are adjacent in the page — the
regeneration command, then the check command — and a person who runs them in
that order is exactly who the missing step was for.

## Why these two pages, and not the three that already had it

The `--write-digests` mode landed with the digest itself, documented in
`bios/ghidra/README.md`, `ec/ghidra/README.md` and
`windows/decompiled/native/README.md`. All three are *build-level* pages: the
page you read once you have already decided to re-export, and you got there
from a tool's `--help` or from another engineer.

`bios/README.md` and `ec/README.md` are the *component* pages, and the
difference is not a matter of taste — the BIOS one says so itself. Its table
row for `ghidra/` ends "`ghidra/README.md` is the long version". The component
page is the primary; the `ghidra/` page is the longer statement of the same
thing. And the primary is the one that gets cited as the component's authority
from outside the component: `bios/ifr/README.md` repeatedly, plus
`docs/agent-pipeline.md` and `docs/findings.md` for the EC and a long run of
`ec/annotations/*.md`.

So the gap is a missed audience, and the specific harm falls on the newcomer
rather than on the person who already knows the repository: a documented
regeneration recipe whose last step is missing. The general form is worth
naming, because it is not about this mode — **a mode added to a tool reaches
the build-level README by the route that introduced it, and reaches the
component page only if somebody notices.**

## What the message says now, and what it still does

`verify_c_digests()` has two failure strings, one for a byte-count disagreement
and one for a hash disagreement, and both ended by listing the same three
causes: *truncated, overwritten or hand-edited*. For
`bios/decompiled/OemOcDxe.annotated.c` the third of those is not a fault. The
same page's table row calls that file **Hand-written**, and its "Which layer is
which" section explains that a generated version of it would be the pointer
chains it exists to replace. A reader who followed the convention, edited the
prose, and ran the check was told they had corrupted a file.

The message now branches, on a module-level `HAND_EDITED_C` in
`bios/tools/bios_extract.py`, keyed on the **basename** so it holds wherever
the file sits — `--self-test` calls `verify_c_digests()` against `/tmp`
fixtures, and a branch keyed on the repo-relative path would be exercised only
by the tree it was written for. For that file the message says the digest is
behind rather than the file damaged, and that re-blessing it is the step.

**Both branches still fail. That is the invariant, and it is why this is a
message change and not a severity change.** The digest's job on this file is
`committed_c_files()`'s own stated one: it exists so that editing the readable
layer is a *visible committed diff* rather than an edit the gate cannot see. A
branch that downgraded this one file to a warning would have deleted the only
mechanism the repository has for noticing a change to its restatement, and it
would have done it quietly — the file would still be digested, the row would
still be stale, and `--check` would simply stop saying so. Nothing about the
digest row changes; only the sentence after the measured facts does, which is
also why the two failure strings share one helper rather than each growing its
own branch.

**The message does not claim the reading is right.** It says the digest records
that the file changed, not that the C means what it says — which is the same
calibration `verify_c_digests()`'s own docstring and
`windows/decompiled/native/README.md` already state, and `--write-digests`
will re-bless a mangled file just as happily. What the digest buys is a
corruption check and a visible diff. It is not an anti-tamper control and it is
not evidence that a decompile is a faithful reading of the firmware, and
nothing here changes that.

## Why only the BIOS copy branches

The same sentence is in `ec/tools/build_ec_decompile.py` and
`windows/tools/decompile_native.py`, and it is **correct in both**: neither
tree has a hand-edited `.c`. The measurement is one command —
`find . -name '*.annotated.c' -not -path './.git/*'` — and it returns exactly
one file, in `bios/`. The BIOS is also the only tree where the asymmetry is
deliberate rather than incidental: its `committed_c_files()` has no exclusion
*on purpose*, and its docstring says the point is that the hand-written layer
gets a digest like every other file.

So two more shared files were left alone. Editing them would have been a
fourth shared-file edit to fix a condition that cannot occur in either tree,
and the two copies are free to diverge — that is the arrangement §15c of
`docs/findings.md` describes for the annotation vocabulary, and it is the
right one here too: three copies, each honest about its own tree.

## The timing figure, reduced to one home

`ec/README.md`'s `tools/build_ec_decompile.py` bullet carried two bare
timings with no date and no caveat. They were the third generation of one
number, and the trail is worth naming because the third generation was the
only unbounded one:

| where | `--check` | `--self-test` | bounded? |
|---|---|---|---|
| `docs/findings.md` §15c, the generation it superseded | 0.24 s | 0.15 s | dated, and §15c names it as the pair the two `ec/README.md` copies quoted |
| `docs/findings.md` §15c | 0.19 s | 0.13 s | dated, tree named, five runs each |
| `ec/ghidra/README.md` | 0.34 s | 0.59 s | dated, machine class, warm page cache, and it says what it superseded |
| `ec/README.md` | 0.19 s | 0.13 s | **no** |
| `docs/findings.md` §14j, merged tree | 0.48 s | 0.77 s | three runs each, on the tree carrying §14j and §14i both |

The fix is to **remove the figure and point**, not to correct it. A corrected
figure in `ec/README.md` would be a fourth number with a fourth thing to keep
true, which is the opposite of what the issue asks for and the thing
`docs/findings/no-append-logs.md` is about. So the bullet now says the cost is
measured and dated in `ghidra/README.md`, which is already the last thing the
bullet points at for method and coverage.

**Re-measurement was available and was deliberately not taken.** `--check` and
`--self-test` need no Ghidra and no network, so a fresh figure is a
sub-second command on any machine. Writing one into a shared README is exactly
the figure that will be one merge behind the next time §14j's tree changes, and
§14j is already the merged-tree measurement with three runs each. The pointer is
the deliverable; a fourth number is not.

`ec/ghidra/README.md` needs no edit to its own numbers, and that is a
judgement worth stating rather than leaving implied. A dated, machine-classed,
self-superseding figure is calibrated; the bare pair in a sibling page is not,
and the one being fixed is the bare one. §14j says the same about §14i — those
numbers are *still correct of the trees they measured*. What that page does
need is one sentence saying the pair was re-taken on the merged tree and what
it is now, because `ec/README.md`'s new pointer lands there and a pointer to a
figure one merge behind is not a pointer. It is a cross-reference in live prose
about a different measurement; nothing is retracted and no note accumulates.

## What this does not claim

- **No `c-digests.csv` and no `.c` is regenerated by this change.** The digests
  are correct as committed; the thing that was wrong was two documents and one
  message string. No mechanism changed and no committed artefact is new.
- **No live test, and nothing here is evidence about the machine.** Every
  assertion is over committed files and `/tmp` fixtures. The failure strings
  were read off the tool's own return value, not off a run on hardware.
- **The issue's own file counts are behind the tree**, and they are left out of
  the prose rather than repeated. A file count in a shared README is a claim
  that stops being true the next time a module lands, and the counts this write-
  up needs are re-derivable with the two commands given at the top.
- **Nothing is submitted upstream.** There is no Linux driver work here, and in
  any case the deliverable for that is a prepared patch in this repository for
  a human to submit.

## The part of this that is a test rather than a fix

`--write-digests` is the fourth recurrence of one shape: a mode added to a
tool reaches the build-level README by the route that introduced it, and
reaches the component page only if somebody notices.
`tools/test_digest_doc_coverage.py` pins that, and only that. It discovers the
tools by reading them rather than from a list of paths, derives each tool's
page from where the tool lives, and requires the mode to be named on any
component page that *enumerates* that tool's flags.

"Enumerates" is structural and deliberately so: a fenced command block, a
table row, or a bold-lead list entry naming the tool is a list of what the
tool accepts, and a sentence that mentions it is not. That distinction is
load-bearing rather than a convenience — `windows/README.md` says what
`decompile_native.py` wants to run and lists none of its flags, so it is not
an incomplete enumeration and a rule that swept it in would have made the
right page wrong. Four cases pin the predicate itself, because a predicate that
answers "no" for everything is exactly the shape that lets the case above pass
having compared nothing.

The issue asked for no new check, and this is the one place the change goes past
that. It is a test and not a gate: `tools/run-tests.sh` is deliberately not
called from `agent-gates.sh`, so it adds no CI surface and no `.github/` edit,
which is the same reason wiring it up is an `ElDavoo/agent-pipeline` change
rather than one this repository makes. The cost is one row in this
repository's most conflict-prone table.

## Left open

- **Nothing yet stops a fourth generation of a timing figure from appearing.** A
  pointer is a convention, not a gate, and the suite above covers digest modes
  only. The measurable form would be a check that a shared README carries no
  timing figure a sibling README also carries; that is a new tool, and a new
  tool is a new file and a new question rather than something to add to a docs
  fix.
- **The missed-audience shape is general and only this instance is measured.**
  The suite checks that one mode is named on one kind of page. It says nothing
  about the other modes these tools carry, nothing about the other shared
  documents a person reads, and nothing about whether `bios/ghidra/README.md`
  is the right place for a mode in the first place. The general question —
  which pages a mode owes a mention to — is not answered here and the suite is
  not the place it would be.
