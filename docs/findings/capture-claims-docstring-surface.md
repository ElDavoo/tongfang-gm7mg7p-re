# The capture-claims docstring quotes its own run, so a test now holds it to the run (issue #991)

`ec/tools/check_capture_claims.py` reports on itself at file granularity — a
`--verbose` line per file naming how many capture claims it found there — and
its docstring quoted that self-report back. Two readings of one surface, kept
in prose, with nothing comparing them, and they had drifted: the docstring said
**five address-presence claims and two row counts, in two files** where the
run on the same tree says **nine claims in three**, and it named a `.txt`
roster and a corpus-scan count that were each wrong three ways. This branch
corrects the docstring, deletes the figures that are properties of the
evidence tree rather than of the tool, and adds
`test_check_capture_claims.py::TheDocstringSurface` to hold what remains
against a real run.

**Nothing here touches the machine.** No register is read, no capture is
opened, no image is loaded, and no EC, BIOS, Windows or laptop is involved.
Every figure below is a count of occurrences in committed text, produced by a
command that is in this tree. It is the same class of claim as
[`testdata-addr-column-claim.md`](testdata-addr-column-claim.md), which is
where the file-granularity census lives, and one step further from the data:
nothing here is a statement about the firmware at all.

## The three wrong claims, quoted beside their corrections

Per `docs/findings.md` §4a-4d the wrong version stays visible rather than
edited away, so a reader who remembers the old sentence can see what it said
and what it should have said.

**One — the surface paragraph.** It read:

> on the tree as merged this checks five address-presence claims and two row
> counts, in `ec/annotations/registers.yaml` (the `XDATA_0449` and
> `GPU_DYNAMIC_BOOST_STATUS` notes) and
> `docs/hardware-tests/system-id-0456-bit6-divisor.md` §5.

Wrong in the aggregate and per file. `registers.yaml` is 4 presence + 1 count,
not 5 presence, because `XDATA_0449`'s note yields **both** kinds from one
unit: a count (238) bound to the entry's own `addr:`, and a presence claim
for `0x044C`, the comparison address the note names in the same breath. And
`docs/hardware-tests/xdata-06c2-06db-sweep.md` is not mentioned at all, with
two claims in it. The issue that filed this named the third file and not the
per-file split; both are corrected below.

**Two — the `.txt` bullet.** It read:

> The four `.txt` files in `evidence/ec-watch/` are `ecrw.py dump` output --
> one is a hex dump, one a value listing -- and have no row-per-change shape
> to count.

Wrong three ways, and the "hex dump / value listing" half is the only part
that survives. There are **five** `.txt` files, and **none** of them is
`ecrw.py dump` output. Each file's own header says what made it:

| file | line | what its own header says |
|---|---|---|
| `2026-09-24-host-window-page-census.txt` | 1 | `# host-window page census, ec/tools/ec_timer_capture.py --census, ECMG 0xfe410000 via /dev/mem, read-only` |
| `2026-09-23-0751-isolation.txt` | 1 | `# Issue #99 -- write 0x0751 alone, service running, AC, from Turbo (0x10)` — `ec_watch.py` output, one row per change |
| `2026-09-23-power-mode-cycle-0f00-final.txt` | — | no header at all; line 1 is `0F00: 35 39 3b 3d 3f 41 43 4b 50 53 ff ff ...`, a bare hex dump |
| `2026-09-23-ctgp-live.txt` | 1-4 | `# Issue #8 -- cTGP/DynamicBoost live test, ...` — a hand-written observation table |
| `2026-09-23-power-mode-snapshot-dc.txt` | 6 | `# Tool: windows/tools/ecrw.py read. Values copied verbatim from its output.` |

The last is the only one whose header names a tool, and it says **read**. The
`ecrw.py dump` attribution most likely crossed over from the testdata fixture
`ec/tools/testdata/0751-isolation-example-moved-fan-after-0f00.txt`, whose
header does say "the same `ecrw.py dump 0x0F00 0x0060` as §3's step 6 takes
it" — a *constructed* input modelled on a dump, which `--verbose` also reports
as a `.txt` skip, and not a member of the evidence tree at all.

**Three — the corpus-scan sentence.** It read:

> A corpus scan over the same roots finds 19 units naming a `.csv` capture at
> all (and 10 more naming one of the `.txt` ones).

This is the sentence that had to be **deleted rather than corrected**, and the
next section is why. It is stale as well as misplaced: the same scan on this
tree measures **38 units in 14 files** and **16 units**.

## The measurement, re-derived from the run, 2026-09-27

Nothing below is taken from the issue or from the predecessor write-up; all of
it comes from running the tool. The run:

```
$ python3 ec/tools/check_capture_claims.py --check --verbose
195 files / 99083 lines / 9 capture claims checked against 10 committed captures: every checked claim agrees with the capture it names
192 of those 195 file(s) were read in full and named no capture claim; `--verbose` names each one
```

The per-file surface `--verbose` prints, with the presence/count split derived
by neutering `ccc.COUNT` — a module global looked up at call time inside
`check()`, so taking it out leaves the presence rule standing and the second
total is the presence figure — and cross-checked against a `sys.settrace` pass
over the two `checked += 1` sites:

| file | `--verbose` | presence | count |
|---|---|---|---|
| `ec/annotations/registers.yaml` | 5 | 4 | 1 |
| `docs/hardware-tests/system-id-0456-bit6-divisor.md` | 2 | 1 | 1 |
| `docs/hardware-tests/xdata-06c2-06db-sweep.md` | 2 | 1 | 1 |
| **total** | **9** | **6** | **3** |

And every claim by address and line, which is what "re-derive the split" is
worth:

| file:line | address | kind | stated |
|---|---|---|---|
| `ec/annotations/registers.yaml:1267` | `0x0449` | count | 238 |
| `ec/annotations/registers.yaml:1269` | `0x044C` | presence | — |
| `ec/annotations/registers.yaml:3895` | `0x0743` | presence | — |
| `ec/annotations/registers.yaml:3895` | `0x0745` | presence | — |
| `ec/annotations/registers.yaml:3896` | `0x0746` | presence | — |
| `docs/hardware-tests/system-id-0456-bit6-divisor.md:275` | `0x0449` | count | 238 |
| `docs/hardware-tests/system-id-0456-bit6-divisor.md:276` | `0x0449` | presence | — |
| `docs/hardware-tests/xdata-06c2-06db-sweep.md:144` | `0x06D6` | count | 260 |
| `docs/hardware-tests/xdata-06c2-06db-sweep.md:145` | `0x06D6` | presence | — |

`registers.yaml` is five claims over three lines because three of the
addresses are named on one line and one of them twice; `0x0743` and `0x0745`
share `registers.yaml:3895`, which is the `GPU_DYNAMIC_BOOST_STATUS` note's
"where `0x0743/0x0745`/`0x0746` land". A sentence that says three addresses
attributed to one capture is three claims, not one, and this is the table that
says so.

## Why the corpus-scan sentence was deleted rather than re-quoted

Three reasons, and the first is the whole of it.

**It is not a property of the tool.** `units naming a .csv capture` is a
census of a corpus that grows with every document added to the tree, and the
run does not print it — nothing in the tool computes it. It was a separate
scan, hand-run and hand-quoted, sitting in a docstring that otherwise quotes
the run. The docstring's own next paragraph already states the rule this
sentence broke: a file count quoted in a docstring "is invalidated by the next
document added to the tree". The same applies with more force to a unit count.

**Its replacement is not stable either.** The issue proposed replacing "19 and
10" with "13 `skip (capture is not a .csv)` lines … across seven files". That
figure is *also* already stale on the tree the issue was filed against: the
run prints **19** such lines, across **11** files, naming **six** distinct
`.txt` paths (the five under `evidence/ec-watch/` plus the testdata fixture
above). It is a better figure — the run prints it, at least — but it is still
a count of units in a corpus, and it moves the same way.

**A count of skips is a count of the corpus, not of the checker.** The
`skip (…)` lines are one per *unit that named a capture and was not checked*,
so their number is a joint property of the prose and the rules above. What a
reader wants from that paragraph is how much the tool holds and what it cannot
reach, and the answer to the second is the list of skip rules — which is the
bullet list directly above it, and needs no figure at all.

So the paragraph now says what `--verbose` prints, and the census line's own
count — `192 of those 195 file(s)`, printed on every run, the *run's* own
figure rather than a separate scan's — is where a count belongs. This is
flagged explicitly because it is the one place this change does **less** than
the issue literally asks: it drops figures rather than re-quoting them, and
the reason is that the issue's own replacement numbers are stale on the tree
they were filed against.

## Subset, not equality, and the direction that decides it

The invariant the new cases hold is that the docstring's file list is a
**subset** of what a run confirms, and that each figure it quotes is the one
the run prints for that file. It is deliberately not `run == docstring`, and
the reason is directional:

- A file appears in that table **because a claim in it was checked**. That is
  a real invariant, and it is the one that catches a docstring naming a file
  the tool never opened — which is how the drift here started.
- A **new** claiming file is expected to appear in the run first and in the
  table only when somebody writes it down. Pinning equality would turn the
  next capture a human commits into a red suite, which is the same reason
  `docs/findings/testdata-addr-column-claim.md`'s row-claim suite asserts
  decompositions rather than figures.
- The only way this docstring has **ever** drifted is by *gaining* a file the
  run confirms and the prose does not name. So that is the direction to check,
  and a run confirming a fourth claiming file is a green case.

A claim-count **floor** would be the wrong shape for the same reason, and
nothing in the new class asserts an expected total.

## The new cases, and a demonstration that they have been seen red

`test_check_capture_claims.py::TheDocstringSurface` is six cases over one real
`main()` run, shared by the class through `setUpClass`. Three parse helpers do
the work: `docstring_surface()` reads `ccc.__doc__` and returns
`{path: (claims, presence, count)}`; `verbose_surface()` parses the
`claim(s) checked` lines into `{path: claims}`; and `derives_presence_split()`
calls `check()` on one file twice, once as shipped and once with `ccc.COUNT`
neutered.

**Both parsers raise on an empty parse, and that is the load-bearing detail.**
A regex that matches nothing and asserts nothing is exactly the "checker that
passes by checking nothing" failure this suite's own module docstring opens
on — every membership and per-file case would go green against `{}`, and the
suite would report a docstring that names nothing the run confirms. The
symptom is indistinguishable from a correct result, so the guard belongs in
the parser rather than in each case.

The cases are: every named file yields a claim (membership); each quoted
figure is the one the run prints; the split is the one the walk derives; the
count rule is what moves that split; and two synthetic sharpness cases. Plus a
third, synthetic, that holds the subset direction green.

A case that has never been seen red is not evidence of anything, so the real
tree was doctored on purpose — the docstring edited in place, the class run,
the file restored. All four directions, verbatim from those runs:

| doctored docstring | result |
|---|---|
| a fourth row naming `docs/hardware-tests/never-opened-by-this-tool.md` | **red** — `AssertionError: 'docs/hardware-tests/never-opened-by-this-tool.md' not found in {'docs/hardware-tests/system-id-0456-bit6-divisor.md': 2, 'docs/hardware-tests/xdata-06c2-06db-sweep.md': 2, 'ec/annotations/registers.yaml': 5}` |
| `registers.yaml`'s total moved 5 → 6 | **red** — `AssertionError: 5 != 6 : docstring: ec/annotations/registers.yaml` |
| `registers.yaml`'s split moved `4, 1` → `5, 0` | **red** — `First differing element 0: 4 5  - (4, 1)  + (5, 0)` |
| the `xdata-06c2-06db-sweep.md` row **deleted** | **green** — `Ran 7 tests ... OK` |

The last row is the one the issue explicitly asks to stay green, and it is the
only direction a growing tree travels on its own.

The derivation is held to be load-bearing in the sibling suite's form: the
neutering has to *lower* the checked total, so a walk that answered the same
way under both would make every row count above zero by accident.

## A correction to the issue, so the next reader does not chase it

The issue points at `docs/hardware-tests/xdata-06c2-06db-sweep.md:200` — "35
addresses (arm 2's 28, …)" — as the count claim the docstring's split was
missing. It is not one, and correctly is not: that is a **distinct-address
count over a whole capture**, which the docstring's own "Numbers that are not
row counts" bullet leaves alone *by construction* — a count has to be a number
immediately followed by `times`/`changes`/`rows` and bound to a nearby address.
The count claim in that file is `:144`'s "260 rows", which is what the table
above records. Recorded so the correction is not re-derived.

## What this deliberately does not change

- **A pre-existing off-by-one in the generated index**, noted because this
  change's regeneration moves that number and a diff showing `123` → `125`
  deserves a sentence. `docs/findings/INDEX.md` listed 124 write-ups and said
  **123**; the entry list was complete and correct and only the prose count
  was stale, on the tree as received. `gen_findings_index.py --check` fails on
  it, but nothing runs that check — `docs/ci/agent-gates-findings-frozen.patch`
  is the patch that would put it in `.github/scripts/agent-gates.sh` and it is
  not applied, so the drift was invisible. Regenerating for this write-up
  fixes it as a side effect: 125 entries, 125 stated. Not investigated further
  here; the check that would have caught it is a human's `git apply` away, and
  that is the same patch this change leaves alone.
- **`docs/findings/testdata-addr-column-claim.md`** is a dated record of what
  #975 measured and declined, and its §"A finding this PR names but does not
  fix" is scoped to "this PR". Its census figures (145 of 148, 146 of 149) no
  longer describe the tree — this run says 192 of 195 — but rewriting another
  branch's dated record is the append-log shape `check_no_append_logs.py`
  exists to stop. This file names it as the predecessor and carries today's
  figures, dated. The docstring's pointer to it names a *file*, which is why
  the pointer is still right and its figures are not quoted.
- **`tools/README.md`**'s suite row is a *description*, and
  `tools/test_readme_suite_table.py` states outright that descriptions are not
  checked. Adding a class to an existing suite needs no row, and the existing
  description is not falsified by the new one.
- **`docs/ci/agent-gates-capture-claims.patch`** stays byte-identical. The
  tool's CLI does not change, only its docstring, so the patch is still held
  against the same gate by `tools/test_agent_gates_patches.py`. The checker is
  still not wired into CI; that remains a human's `git apply`.
- **The tool's scope.** No new regex, no new capture source, no new predicate,
  no change to `main()`'s index and none to its output. This is a docstring, a
  test class and a write-up.

## Follow-ups this exposes

- **`evidence/ec-watch/2026-09-23-ctgp-live.txt` is described nowhere.** It is
  the one `.txt` in the capture root that `evidence/README.md` does not index —
  the other four are at `:42`, `:45`, `:50` and `:77`. Correcting the docstring
  to point readers at `evidence/README.md` for what any individual capture is
  makes that gap load-bearing, and `evidence/README.md` is a shared file this
  change does not touch. Named here rather than fixed.
- **The `0x06D6` pair at `xdata-06c2-06db-sweep.md:144`/`:145` was invisible to
  every prior statement of the surface**, including the issue's. That is what
  the per-file table is for: a file the paragraph does not name is a file
  whose claims nothing was keeping track of.
