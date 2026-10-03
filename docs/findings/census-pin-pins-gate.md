# Two pin censuses prepared for the cheap gate, and the gate list is what stops them carrying a gate line (issue #954)

**Nothing here is a hardware, firmware or Windows claim.** No image is opened,
no register is read back, no capture is taken, and no EC, BIOS or vendor binary
is touched anywhere below. Every figure is a count over text committed in this
repository, measured on 2026-10-03, and the one thing this page cannot claim is
in its last section, where it says so.

## The two tools, and what each one measures

`ec/tools/census_test_line_pins.py` walks the committed markdown for every
`test_*.py:NNN` (or `:NNN-MMM`) pin, resolves each to a file and a line, prints
which resolution answered, and counts five verdicts. Its population is
`docs/findings/test-line-pin-census.md`'s, and it excludes its own write-up,
because that document's table *copies* the pins rather than using them and
counting it would make the class's size a function of the report about it.

`ec/tools/check_pin_table_by_cited_file.py` answers a different question about
the same pins: **which test file does each one name**, plus the other
direction — the indexed suites no pin names at all. It imports the first tool's
extractor rather than walking the markdown a second time, so its population is
the first tool's by construction and the two sets of numbers reconcile.

They are wired as one gate function for the same reason. A second walk of the
markdown would be a second set of numbers, and two headcounts that cannot be
reconciled against each other is exactly the failure
`test-line-pin-census.md`'s whole argument is about.

**Neither renders a verdict, and that is the standing that makes either safe
in a gate.** Both exit 0 on a tree where every pin in it is wrong. Whether a
cited line still carries the claim it was cited for is a reading, and it lives
in `test-line-pin-census.md`'s per-pin table; a gate that reddened on that
would redden on sentences that are true, which is
`prose-line-citations-held.md`'s standing for the same reason.

## What a gate gets, which is narrower than it sounds

The vacuous-pass guard, and nothing else. Both tools exit non-zero on a run
that read **no markdown file at all**, and on a run that found **no pin**, so
"found nothing" can never read as "found nothing wrong". Measured on a scratch
tree holding only the two tools and no markdown, and again with one markdown
file carrying no pins:

```
$ python3 ec/tools/census_test_line_pins.py          # scratch tree, no markdown
census_test_line_pins.py: no markdown file was read at all, so no pin could be
  looked for -- that is a broken census, not an empty one          → exit 1
$ python3 ec/tools/census_test_line_pins.py          # one .md, no pins
census_test_line_pins.py: no `test_*.py:NNN` was found in the markdown
  read, so nothing was censused -- that is a broken census …         → exit 1
```

`check_pin_table_by_cited_file.py` has the same two guards, worded for charging
a pin to a file rather than looking for one, and both were checked the same way.
This is the guard `check_citation_lines.py` and `tools/run-tests.sh` already
carry, and it is the half of a census a gate can hold: it does not stop a
census going stale, it stops a census whose reader has silently stopped reading
from reporting a clean run over nothing.

**It is not a stale-pin check and must not be described as one.** A pin that
names a line which no longer carries the claim prints as `resolves` — the file
was found and the span is one it has — and the census's own docstring is
explicit that `resolves` is a statement about a directory walk and a line
count, never about whether the claim is true.

## The figures, re-measured on this tree

Both tools **exit 0** here, which is the property a landing needs: a patch that
lands a red gate is the cheapest way to get a gate switched off, and
`prepared-gate-patches.md` records that happening once, to
`agent-gates-gap-text-check.patch`.

```
$ python3 ec/tools/census_test_line_pins.py; echo $?
132 pin(s) in 32 markdown file(s): 98 distinct spelling(s), 74 distinct resolved target(s)
  99 resolves, 0 out-of-range, 0 unresolved-path, 0 ambiguous-path, 33 declined
  read 382 markdown file(s) under the tree …; resolved against 154 test file(s)
0
$ python3 ec/tools/check_pin_table_by_cited_file.py; echo $?
132 pin(s) over 154 indexed test file(s): 15 named by a pin, 139 named by none
0
```

Two things about carrying these. They are **figures of the markdown on this
tree**: the census population is a function of the prose, every edit to a
markdown file can move them, and the same is true of the write-ups they are
quoted in. And the issue's own "105 `test_*.py:NNN` line pins" is the corpus as
of its filing, which is not the figure to carry — what the tool prints is. What
does not move, and is the part a landing depends on, is that both are exit 0.

Timing, over five runs each on this runner, 2026-10-03:
`census_test_line_pins.py` 0.58–0.59 s, `check_pin_table_by_cited_file.py`
0.61–0.62 s, so about 1.2 s together, against a cheap tier
`docs/agent-pipeline.md` records at 5.9 s. One runner's figures, and the ratio
is the durable part. Re-measured later on the same machine with the test runner
also going, the pair came out at 0.96–1.00 s and 1.03–1.08 s — both figures are
recorded rather than only the flattering one, and the honest reading is that
this is machine load, not a disagreement.

## The anchor table, measured rather than copied

`.github/scripts/agent-gates.sh` is the whole of what this change is placed
against, and the measurement is the reason the patch is shaped the way it is.
Method: parse every hunk of every committed `docs/ci/agent-gates-*.patch`,
locate each hunk's pre-image block in the committed script by exact match, and
take the union of the line ranges those blocks cover. What is left over is what
a new patch may touch. Re-derive it rather than copy this block — the script is
template-copied and a re-copy moves lines in it.

```
CLAIMED: 76-81, 84-89, 93-98, 100-105, 114-119, 130-135, 133-138, 137-142,
         141-147, 152-157, 177-182, 204-209, 298-303, 310-315, 313-318,
         321-326, 324-329, 327-332, 331-336
FREE:    1-75, 82-83, 90-92, 99, 106-113, 120-129, 148-151, 158-176,
         183-203, 210-297, 304-309, 319-320, 337-357
```

`docs/findings/history-checkouts-gate-wiring.md` is the same measurement on an
older revision of the same file. **Its conclusion held and its line numbers did
not**: that write-up puts the `gate` list at `:297-303` where it now sits at
`:327-333`, and it names a smaller set of patches than `docs/ci/` holds today.
Its conclusion is re-confirmed below; its numerals are `d3304785`'s and are
left with that date beside them rather than edited in place, per
`../findings.md` §4a-4d.

### The `gate` list: no free anchor

The list admits one insertion point per gap between its `gate` lines, and
including the two ends. Each was cut as a real one-line insertion (`git diff`
against a seeded scratch tree, not a hand-written hunk) and tried alone and in
**both orders** against every committed patch:

| the new line lands | applies alone | does not compose with |
|---|---|---|
| before `gate 'registers.yaml'` | yes | pin-table-rows |
| after it | yes | capture-claims, pin-table-rows |
| after `gate 'scan_refs.py smoke test'` | yes | capture-claims, pin-table-rows |
| after `gate 'register counts'` | yes | capture-claims |
| after `gate 'ghidra tooling'` | yes | capture-claims |
| after `gate 'python syntax'` | yes | capture-claims |
| after `gate 'shellcheck'` | yes | capture-claims, testdata-row-claims |
| after `gate 'doc links'` | yes | testdata-row-claims |

**Every one applies cleanly alone and not one composes.** That combination is
the whole trap: a `gate` line would be green on `git apply --check`, green on
the one test a person runs before trusting it, and would fail only when a
sibling landed — with a context-mismatch message that reads like staleness
rather than a composition problem. It is the failure
`tools/test_agent_gates_patches.py` exists to catch, and the two patches that
demonstrate it are the reason `agent-gates-testdata-index.patch` no longer
exists. "Re-anchor somewhere else in the list" is not a workaround at any of
them: the list is short enough that every insertion shares a context window
with a held one.

### The function gaps, and the two that are free

Each gap between the `check_*()` definitions was cut as a real function
insertion and tried the same way:

| gap | composes? | held by |
|---|---|---|
| after `check_registers_yaml()` | **yes** | — |
| after `check_scan_refs_smoke_test()` | no | testdata-row-claims |
| after `check_register_counts()` | no | capture-claims |
| after `check_python_syntax()` | no | bank-map-score |
| after `check_ghidra_tooling()` | **yes** | — |
| after `check_shellcheck()` | no | pin-table-rows |
| after `check_doc_links()` | no | findings-frozen, pin-table-rows |

**The patch takes the gap after `check_ghidra_tooling()`**, so its definition
sits between that function and `check_shellcheck()`. It is a gap between two
checks this one has nothing to do with, and it is there because it is free.

### The call: free points exist, and the host is a tidiness choice

Every single-line insertion point inside `check_ghidra_tooling()` was cut and
tried the same way. The free ones are `:105-113`, `:119-129`, `:147-151`,
`:157-176`, `:182-203`, `:209-297`, and they are **not the same kind of place**.
The tool loop is `for tool in` at `:133` and its `case` at `:146-299`, so
`:147-151`, `:157-176`, `:182-203` and `:209-297` are inside a `case` arm and a
call there would run once per tool rather than once per gate. **`:105-113` and
`:119-129` are above the loop**, in the function's own comment block, and a call
there runs once per gate as intended: `:109` and `:126` were each cut as a real
one-line insertion and tried alone and in both orders against every committed
patch, and each applies cleanly, composes with all of them, and passes `bash -n`
and `shellcheck`. The head of the function, beside its `local rc=0` line, is
`agent-gates-bank-map-score.patch`'s; the tail, beside `rm -rf "$scratch"`, is
`agent-gates-reassembly-bound-check.patch`'s.

**So the call is in neither of those free places, and that is a tidiness
choice rather than a forced one.** Both hosts available are wrong labels for a
markdown census — `check_ghidra_tooling()` would print `=== ghidra tooling ===`,
which sends a reader looking at Ghidra, and `check_shellcheck()` prints
`=== shellcheck ===`, which sends them looking at shell scripts — and neither is
worse than the other on that count. The call sits at the tail of
`check_shellcheck()`, immediately before that function's `return`, because that
is the tidier of the two: a one-line call lands beside a `return` in the
ordinary way, whereas the free points inside `check_ghidra_tooling()` are all
inside a run of comment lines explaining the loop, and a bare
`check_pin_census || rc=1` wedged between two comment paragraphs reads as a
stray line rather than as a check. The cost is real and it is stated in the
patch header where the next reader of the gate will see it. The census's own
stderr names what failed — the guards above print
`… that is a broken census, not an empty one` — so the run does say what went
wrong, under the wrong heading.

`check_doc_links()` would be the **better** host: a stale pin in markdown is a
documentation defect, that tier is already about markdown, and
`agent-gates-findings-frozen.patch` sets exactly that precedent. Its only free
gap is inside its own `while read` loop, and a census cannot run once per link.
Recorded so the next reader does not re-derive it, and does not "fix" the
placement into something that cannot compose. Of the two hosts that do work,
neither carries a label that fits, so the choice between them is tidiness and
not correctness — which is the honest description of what the paragraph above
now says it is.

## A shape the other two retention cases do not cover

`tools/test_agent_gates_patches.py` covered two shapes. `FoldTests` holds the
folded patch's functions *and* its `gate` lines — dropping either is visible in
the patch file. `ArmRetentionTests` holds the disasm8051 patch's per-tool list
entries *and* per-tool `case` arms.

This patch has a **shape neither of those covers**, and it is the one with no
cheap tell. Its two halves are a **definition and a call**, in two different
functions. A re-cut that lands `check_pin_census()` and drops
`check_pin_census || rc=1` applies cleanly, composes in every ordered pair, and
passes **both `bash -n` and `shellcheck`** — because an uncalled shell function
is valid shell, exactly as valid as a called one. Nothing else in the suite
notices, and what is lost is the gate: the census stops running per commit and
no run says so.

`CallRetentionTests` is the case for it. It holds **three** strings — the
opening line, one body line, and the call — the shape and not a count, for the
reason `ArmRetentionTests`' own docstring records: *"this is not a count of the
tree and must not become one"*. Another shape gets another string on the same
list; it does not edit a sentence to say how many.

**The third string is there because two were not enough, and the mutation is
what showed it rather than an argument.** The first version held the opening
line and the call, on the reasoning that the opening line stands for the
function. It does not: a re-cut that lands

```sh
check_pin_census() {
  :
}
```

still contains `check_pin_census() {`, still contains
`check_pin_census || rc=1`, and is just as valid shell as the original — the
body is what makes the check *do* anything, and it is the one line the opening
line cannot speak for. That mutant was cut and run: it applies alone, composes
in **both orders against every committed patch**, the landed result passes
**both `bash -n` and `shellcheck`**, and `tools.test_agent_gates_patches` came
back green — with both censuses gone from the gate. So this section's earlier
claim that two strings covered the shape was overstated in exactly the direction
that costs the gate silently, and the third string is the correction. It is
`python3 ec/tools/census_test_line_pins.py || rc=1`: the census, because the
census is the deliverable and the by-cited-file tool only breaks its population
down. One body string rather than both, on `ArmRetentionTests`' reasoning — a
shape that grows is another string, not an edit to the sentence above.

What the class still cannot see is a body that runs *something else*. That is
a different defect with a different cheap tell, and saying so is the honest
boundary rather than leaving the reader to assume the list is exhaustive.

**The mutations were run, not assumed.** All three were produced the honest
way — the patch applied, the *landed* script edited to weaken one half, and the
patch re-cut from that with `git diff` so the `@@` counts stay right. Each
mutant still classifies as `prepared`, still applies, still composes in every
ordered pair, still passes `bash -n` and `shellcheck`, and each turns
`CallRetentionTests` red and nothing else:

```
re-cut dropping the call    → prepared; only failure is CallRetentionTests
                               (line='check_pin_census || rc=1')
re-cut emptying the body    → prepared; only failure is CallRetentionTests
                               (line='python3 ec/tools/census_test_line_pins.py || rc=1')
re-cut dropping the def     → prepared; only failure is CallRetentionTests,
                               on two of its strings at once
                               (line='check_pin_census() {')
                               (line='python3 ec/tools/census_test_line_pins.py || rc=1')
```

Dropping the definition takes the body with it, so that mutant trips both
strings rather than one — expected, and the reason the third string does not
change what the first two already caught. Each mutant's *only* failures are in
that one case; every other case in the suite stays green.

A first attempt at these mutations edited the *patch file* rather than the
landed script, which corrupted the `@@` counts and made three unrelated cases
fail on `corrupt patch`. That is the mutation being wrong, not the case being
redundant: the numbers above are from the corrected version.

## Left out, and what it would cost

**A `gate` line.** Unavailable standalone; the table above is why. The only
route is a fold into a patch that already holds one — `pin-table-rows`,
`capture-claims` or `testdata-row-claims` — the route #745 and #1033 each took.
That would buy a correct `gate` label at the price of this file, a `PATCHES`
entry, a `check_doc_patch_refs.py` citation, and a patch whose name would carry
one more concern than it already does. The issue names a file, so it was not
taken; the alternative and its price are here so a reader who disagrees does
not have to re-derive it.

**A fold into `agent-gates-findings-frozen.patch`**, which is the closer of the
two and the one a reader is most likely to suggest. It already holds a function
and a call in free regions, and it is about the same thing — both are checks
over this repository's own documents — so the fit is good. Not taken because
the issue names this file, and because a fold is a smaller change than the one
filed: it would cost the `PATCHES` entry, the header's own anchor discussion,
and a patch whose name would carry one more concern than it already does.

**`ec/tools/check_pin_table_rows.py`, which is red on this tree and is not
called by this patch.** It is the other tool in this family — the one that
holds `test-line-pin-census.md`'s per-pin table to the census's own run rather
than counting — and it exits 1 on the committed tree. Confirmed at `HEAD` in a
detached worktree, where its output is **byte-identical** to its output in this
working tree: the reds are rows whose citing line has moved and rows the census
reads with no table row behind them, across `0751-mark-provenance-column.md`,
`0751-mark-provenance-shapes.md`, `docs/agent-pipeline.md` and
`xdata-register-map.md` among them. It is several rows, not one, and the count
moves with every prose edit; what does not move is that a landing of every pin
patch at once gets a red cheap gate **from those rows**. Its patch is
`docs/ci/agent-gates-pin-table-rows.patch` and its remedy belongs there;
folding another patch's table repair into this one is the thing
`prepared-gate-patches.md`'s "Left red, and why" section exists to refuse. The
patch header says so rather than letting a landing be a surprise.

## The two standing tests that keep holding

`test_census_test_line_pins.py` and `test_check_pin_table_by_cited_file.py`
each carry a case asserting the tool's name does **not** appear in
`.github/scripts/agent-gates.sh`. Both stay green, and they must: the patch is
prepared, not landed, so the name is still absent and the case still describes
the tree. What the prepared patch changes is the *reason* the name is absent —
from "no anchor for it" to "a human has not run `git apply` yet" — so each
tool's docstring now names the patch, and a human landing it updates the case
rather than deleting it. Neither tool's docstring says anything false in the
meantime.

## What is not claimed

- **That the gate runs these tools.** It does not, and cannot from an agent
  branch: `.github/scripts/agent-gates.sh` is copied from the agent-pipeline
  template and the pipeline's push token has no `workflow` scope. This is a
  prepared patch plus the re-copy recipe, for a human to `git apply`. Until
  that happens no commit runs the censuses at all.
- **That the anchor table stays true.** The script is a template-copied file
  and a re-copy may move any line in it. Re-derive it; `tools/run-tests.sh`
  fails if the patch stops applying, and `CallRetentionTests` fails if it
  stops landing both halves.
- **That a pin the census counts as `resolves` is a correct citation.** It is
  a file that exists and a line it has. The verdict is the per-pin table's,
  and the table is a reading.
- **That these figures survive the next prose edit.** They are a function of
  the markdown and will move.
- Any verdict of any tool, any register status, and any hardware or Windows
  fact.