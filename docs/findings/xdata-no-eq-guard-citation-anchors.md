# The `--no-eq-guard` mechanism's citations, re-anchored to code (issue #873)

**Issue #873, 2026-09-26.** #816 wrote the correction for two of these sets and
deliberately left the line numbers standing, because a correction that adds
lines to the file it corrects invalidates its own numbers. Two of the sites it
did not measure named the *wrong code* outright, and the rest had drifted by
hundreds of lines. This is the re-point, the measurement behind it, and the
checker that holds it.

**Nothing here is a statement about the EC, the firmware, or any register's
behaviour.** Every number here is a `grep -n` over a committed file, and each
is a property of the tree it was measured on rather than a constant. "The guard
is still a conditional in front of the rejection" is a statement about
`ec/tools/xdata_register_map.py:1753` and nothing else. No register was read
back, no hardware or Windows machine was involved, and the two committed census
CSVs are byte-identical before and after — `xdata_register_map.py --check` and
`--self-test` both exit 0 on this tree, re-run for this change.

## The measurement, on `d330478`

The issue's own "where it actually is" column is a generation stale too. Every
one of those files was re-pointed once already (2026-09-25, #582's re-run) and
the tool has grown since, so a PR that transcribed the issue's table would have
landed seven fresh wrong pins — the exact defect the issue is about. Measured
with `grep -n` on `d330478`:

| anchor in `ec/tools/xdata_register_map.py` | #873's "truth" | **on `d330478`** |
|---|---|---|
| `def store_target(text, start, end, eq_guard=True)` | `:1572` | **`:1730`** |
| `if eq_guard and stripped.startswith("==")` | `:1595` | **`:1753`** |
| `def scan(` | `:2168` | **`:2367`** |
| the `not args.no_eq_guard` flip | `:2917` | **`:3148`** |
| `ap.add_argument("--no-eq-guard", …)` | `:4470` | **`:4947`** (`:4947-4950`) |
| `if args.no_eq_guard and (args.check or args.self_test):` | `:4499` | **`:4976`** (`:4976-4980`) |
| the committed-output refusal | `:4508` | **`:4985`** (`:4985-4989`) |
| `"image and registers.yaml, unlike every other mode"` (`--reconcile`'s help) | — | **`:4934`** |
| `ASSIGN = (…)` | — | **`:377`** |

#873's diagnosis is sound and its corrections are right in kind: on the tree it
measured, `:4457` was the tail of `--reconcile`'s help and `:4499` was the
`--check` refusal. **Its absolute numbers are a generation stale too**, which is
the point of the next section rather than a criticism of the issue.

**The seventeen numbers the prose actually carried are 134 to 1358 lines off**,
by eight different offsets — 510, 510, 763 and 856 for the four-pin walk alone,
and not two pairs that moved together as everyone reading them would assume.
That is why the number alone cannot be the citation: it went stale while nobody
was looking at it, and reading correctly the whole time.

## The two sites that named the wrong code, re-measured

"a line number that is low" and "a line number that is a different thing" are
different defects, and only one of them is a re-measurement. Stated as what
`d330478` holds, not as what the issue's tree held:

- **The flag.** Two files cited `xdata_register_map.py:4568` for
  `--no-eq-guard`. `:4568` is `--co-reading-group-table prints the other half:
  every group over two` — **a different flag's help text**. The flag's
  `add_argument` is at `:4947`. #873 found this exact shape at `:4457` naming
  `--reconcile`'s help; on this tree the same defect has moved on to a *third*
  flag's help, which is the argument for anchoring rather than re-pointing in one
  sentence.
- **The refusal.** Three files cited `:4606-4611` for "the flag is refused with
  the committed output paths". Those two lines are `"first,last")` and
  `f"{g['files'][0]},{g['files'][-1]}")` — the tail of the same
  `--co-reading-group-table` CSV print, and not a refusal at all. The
  committed-output refusal is `:4985` (`args.out_registers ==
  OUT_REGISTERS`); the `--check`/`--self-test` refusal, which is the one
  #873's `:4499` named, is `:4976`.

Each of those sites now names its refusal in the sentence, with the other
refusal's line beside it, so the sentence is unambiguous even if the number
drifts again. `#873` found the refusal confusion at `:4495-4499`, which on its
tree held the `--check` refusal; on this tree `:4495` is `for r in carry))` and
the same confusion is at `:4606-4611`, which is what the correction above fixes.

## The shape of the fix: hold the code, not the number

Every re-pointed citation now carries the code it names, in the sentence:

> `if eq_guard and stripped.startswith("==")` in `ec/tools/xdata_register_map.py` (`:1753`)

and the two refusals name *which* refusal, so the two `if` blocks cannot be
confused by a reader even if the numbers do:

> the committed-output refusal — `args.out_registers == OUT_REGISTERS` at
> `:4985` — **not** the `--check`/`--self-test` refusal at `:4976`

The numbers stay, because readers use them and §4a-4d wants a superseded figure
visible; they are simply no longer the load-bearing part.
`ec/tools/check_eq_guard_citations.py` holds the content anchor, so a stale
number goes red instead of reading correctly.

**Where the tree is named.** The measured tree is recorded in each file's
correction note rather than at every site, and printed by the checker in its
failure text. That is a deliberate departure from repeating `(as of d330478)`
inline at each citation: it is the same provenance in one place per file, the
prose stays readable, and the checker — not the prose — is what carries the
number forward. A reader who wants the tree has it one note away in every file.

## Every pin re-pointed, by file

All of these were in-place re-points with a dated note per §4a-4d, so a
superseded *citation* stays visible as a correction rather than being edited
away — which is the shape §4a-4d asks for, and different from a superseded
*claim*.

| file | site | was | now |
|---|---|---|---|
| `xdata-no-eq-guard-refusal-contract.md` | the `--check` guard-1 clause | `:3618` | `:4976`, anchored on `args.check or args.self_test` |
| " | the four-pin walk | `:1220`/`:1243`/`:1604`/`:2292` | `:1730`/`:1753`/`:2367`/`:3148` |
| " | #816's correction block | left standing; re-measured in a note below it | — |
| `xdata-no-eq-guard-measured-state-correction.md` | the table row and the prose that repeats it | 352/352/564/625 | left standing; re-measured in a note above and below |
| " | the "one thing this turned up" paragraph | `:1582`, `:4495-4499` | left standing; a note records `:1753` and `:4985`, and that the follow-up is discharged |
| `ec/annotations/xdata-register-map.md` | §4.4's flag | `:4568` | `:4947`, on `ap.add_argument("--no-eq-guard"` |
| " | §4.4's and §4.4-transcript's committed-output refusal | `:4606-4611` (×2) | `:4985` (×2), each naming `:4976` beside it |
| " | the parameterised guard | `:1582` (×2) | `:1753` (×2) |
| `xdata-4-4-identity-rederivation.md` | the "writes to `/tmp`" claim | `:4606-4611` | `:4985`, naming `:4976` beside it |
| " | the `GUARD` literal walk | `:1582` | `:1753` |
| `docs/findings.md` | §17's #254 block | `:916`/`:939`/`:243` | `:1730`/`:1753`/`:377` |
| " | §45's re-run | `:4568` | `:4947`, on `ap.add_argument` |
| " | §45's `GUARD` literal | `:1582` | `:1753` |
| " | new §97 | — | a two-sentence summary and this link |

**The one place this read past the issue's wording.** #873's "done" test is "no
`xdata_register_map.py:NNN` that lands on a **different flag or a different
refusal**". By that letter, `docs/findings.md`'s `:916`/`:939`/`:243` are out of
scope: they land on a comment, a tuple and prose. They are included anyway —
same mechanism, one of the five named files, a paragraph already in this diff's
blast radius — because leaving three known-wrong pins in a file this change is
already editing would reproduce the defect under a narrower definition of done.
A reviewer who disagrees can drop those three rows and the checker entry for
`docs/findings.md:4927-4929` without touching the rest — that is §17's #254
block, at `:4890-4892` on this change's own branch and moved by `main`'s edits
to that file in the same window.

## The self-invalidation trap, and what it cost

#816's reason for leaving the pins is a real trap and it is recorded in place:
**a correction that adds lines to the file it corrects invalidates its own line
numbers.** This change does not edit `xdata_register_map.py`, so the tool's
numbers are untouched. The trap moves, though, to **markdown-to-markdown `:NNN`
cross-references**, because a correction note adds lines to a prose file that
other prose files cite by line.

Measured on this tree, before the edits: **eighty-three citations in twenty
files point into the five files this change touches** — this write-up's own
sixteen aside, because a write-up about the citation tax should not inflate its
own measurement. `ec/annotations/xdata-register-map.md` is cited at nineteen
distinct lines, `docs/findings.md` at thirty-five,
`xdata-4-4-identity-rederivation.md` at fifteen and
`xdata-no-eq-guard-refusal-contract.md` at eight, with
`xdata-no-eq-guard-measured-state-correction.md` at none. Two consequences, both
of them visible in the diff:

1. **Every re-point in `ec/annotations/xdata-register-map.md` above `:2665` is
   line-count neutral.** Not by luck: three sites grew by one or two lines with
   the code anchor added, and each was reflowed to hold its own line count —
   which cost three small prose tightenings in the surrounding sentences ("So the
   harm a bare run gets to do is" → "does is", "not by accident" dropped, "a
   follow-up rather than a line to move inside a documentation change" → "here").
   Those tightenings are the price of the anchor and are worth naming, because
   the alternative — a `+2` on nineteen citations across seven files — is a worse
   diff for the same content.
2. **`xdata-register-map.md`'s correction note is at the end of the file**, not
   beside the pins it corrects, for the same reason. A note at `:1090` would have
   moved every one of those nineteen citations. The one place the trap still
   bites is `docs/findings/xdata-no-eq-guard-refusal-contract.md:365-370`, whose
   #816 block cites `xdata-register-map.md:1228` and `docs/findings.md:4885-4890`
   from inside a `>` block; nothing here adds a line above either, which is why
   the new note is quoted rather than folded into that block.

**What the tax actually was: six external citations, in two files.** Measured
by re-running the same sweep after the edits and comparing what each cited line
held before and after, rather than by assuming neutrality worked:

| citing site | was | now | why |
|---|---|---|---|
| `test-line-pin-census.md:1006` | `xdata-register-map.md:1341` | `:1340` | the `:1340`-`:1342` reflow moved the `GUARD` pin up one line |
| `test-line-pin-census.md:1708` | `xdata-register-map.md:1341` | `:1340` | the same pin, named in prose beside the table |
| `test-line-pin-census.md:980`, `:981`, `:982` | `xdata-4-4…:403`, `:447`, `:460` | `:418`, `:462`, `:475` | this change's `>` note in that file, 15 lines |
| `xdata-moved-ranks-fall.md:523` | `xdata-4-4…:401-411` | `:415-426` | the same note, cited as a span |

The first three rows' *citing* lines are `:1006`, `:1707` and `:980`-`:982` on
this tree rather than the `:1008`, `:1685` and `:982`-`:984` this change's own
branch measured: `main` added lines to `test-line-pin-census.md` in the same
window, so those sites moved by −2, +22 and −2 without this change touching
them. The fourth is unmoved. **A re-point records what a citation says, not
where the citation itself is**, and the first three are re-measured on the merged
tree rather than carried from the branch; §4a-4d keeps the branch's figures as
what they were measured on.

**Three further citations in `test-line-pin-census.md` were left alone on
purpose**, and it is worth being explicit about why, because two of them are
citations this change moved. `:1603`'s `xdata-4-4…:433` and `:1879`'s `:446`
were **already pointing at unrelated text before this change** — `:433` at
"`test_every_name_the_key_cannot_find_is_carried_by_overlap`, and it selects
the", `:446` at "which is the command now transcribed in §4.4, and the
two-largest case's id/name" — and both are records of *shapes of defect the
census found* in a section about findings that are no longer live, so re-pointing
them to today's lines would be a different and equally wrong claim. `:1680`'s
`:403` is inside a struck item that records where a pin *was*; §4a-4d keeps that
figure, and `:418` is where it is now. **A pre-existing wrong citation that this
change perturbs is still a pre-existing wrong citation**; fixing it belongs to
the sweep that owns the census, and recording it here is the honest disposition.
The three sites are `:1603`, `:1879` and `:1680` here; the branch measured
`:1581`, `:1858` and `:1658`, moved by `main`'s edits to that file in the same
way the three rows above moved.

One further step was needed rather than a re-point: the new suite takes the
committed pin census up by one indexed test file, which
`test_check_pin_table_by_cited_file.py` asserts. Its step is the same shape as
#1009's and one suite rather than two — `test_check_eq_guard_citations.py` is
indexed and no committed markdown cites a line of it, so it joins the tail, the
named count of 12 does not move, and the assertion moves by one in each of the
denominator and the tail. **On the merged tree that step is not the only one**:
`main` added `test_check_history_checkouts_run.py`, `bios/tools/test_ifr_census.py`
and `test_pd_image_census.py` in the same window, all three also in the tail, so
the merged assertion is **47 / 12 / 35** rather than this branch's `44 / 12 / 32`
or `main`'s `46 / 12 / 34`, and all three figures stay written where each was
measured. That is the axis working: a suite crossing between the two tables is
what it is for, and here four crossed at once.

## The checker, and the negative case that proves it reads

`ec/tools/check_eq_guard_citations.py` is a **new file rather than a mode on
`check_citation_lines.py`**, per `CLAUDE.md`'s rule and because the question is a
different one: that one holds pointers into *generated CSVs* to the row for a
declared address, this one holds pointers into *a source file* to a declared
string of that source. It reads no file outside the five plus the tool, it does
not walk the tree for citations, and it is deliberately **not** the general
`.py:NNN` pointer checker — #868 owns `xdata-086x-dispatch.md:286-288` and states
that its fix needs the general tool, #869 owns the twelve files citing a
generated CSV outside `ROW_SCOPE`, and #870 owns the six pointers in
`XDATA_0860`'s 2026-09-24 block. The census of the class is theirs; this is one
mechanism's own pins.

It prints how many citations it held **and how many it declined**, because a run
that checks nothing must not read from its exit code exactly like a run that
found nothing. The declined count is non-zero on this tree and is meant to be:
these five files carry **sixteen** `xdata_register_map.py:NNN` pins the tool
declines — fourteen of them for *other* claims (`OUT_CLUSTERS`, `MAP_COLUMNS`,
the `--self-test` span) and two in §97's own restatements of the superseded
numbers — and each is
named in the report rather than passed over quietly.

A green run proves only that the tool agrees with itself, so the negative case
is run explicitly — one page copied to `/tmp`, one cited number moved by one
line, the tool red and naming the fix:

```console
$ rm -rf /tmp/eqdemo && mkdir -p /tmp/eqdemo
$ cp --parents ec/tools/xdata_register_map.py docs/findings.md \
    docs/findings/xdata-no-eq-guard-refusal-contract.md \
    docs/findings/xdata-no-eq-guard-measured-state-correction.md \
    docs/findings/xdata-4-4-identity-rederivation.md \
    ec/annotations/xdata-register-map.md /tmp/eqdemo/
$ sed -i 's|ec/tools/xdata_register_map.py:4985|ec/tools/xdata_register_map.py:4984|' \
    /tmp/eqdemo/docs/findings/xdata-4-4-identity-rederivation.md
$ python3 ec/tools/check_eq_guard_citations.py --repo /tmp/eqdemo; echo "exit $?"

  FAIL docs/findings/xdata-4-4-identity-rederivation.md:17: cites :4984 for
  committed_output_refusal, which is ec/tools/xdata_register_map.py:4985 on this
  tree -- hold the code, not the number, or the next growth of the tool is a
  sentence that reads correctly
check_eq_guard_citations.py: 1 problem(s). Every number here is a grep over a
committed file, measured on d330478; nothing in this run is a statement about
the EC or the firmware.
exit 1
```

The green run on the committed tree, in full:

```console
$ python3 ec/tools/check_eq_guard_citations.py; echo "exit $?"
check_eq_guard_citations.py: the 9 anchors of the `--no-eq-guard` mechanism,
resolved in ec/tools/xdata_register_map.py:
  store_target: ec/tools/xdata_register_map.py:1730  `def store_target(text, start, end, eq_guard=True)` -- the parameter
  eq_guard_reject: ec/tools/xdata_register_map.py:1753  the `==` rejection `if eq_guard and stripped.startswith("==")`
  scan: ec/tools/xdata_register_map.py:2367  `def scan(`, where the guard is carried to
  assign: ec/tools/xdata_register_map.py:377  `ASSIGN`, the operator tuple
  flip: ec/tools/xdata_register_map.py:3148  the `not args.no_eq_guard` flip into the census call
  no_eq_guard_flag: ec/tools/xdata_register_map.py:4947  `ap.add_argument("--no-eq-guard", ...)`
  check_refusal: ec/tools/xdata_register_map.py:4976  the `--check`/`--self-test` refusal
  committed_output_refusal: ec/tools/xdata_register_map.py:4985  the committed-output refusal
  reconcile_help: ec/tools/xdata_register_map.py:4934  the tail of `--reconcile`'s help -- what `:4457` used to name
  … per-file lines …
23 citation(s) name the line their code is on, 16 declined as not this tool's, 3 skipped as superseded -- 9 of 9 anchors resolved, over 5 declaring file(s). A run that checks nothing is a failure of this test, not a pass.
exit 0
```

`ec/tools/test_check_eq_guard_citations.py` is the suite, 18 cases over the
committed tree and a scratch copy of it: every anchor resolving, the two
wrong-code sites still resolving to lines no other anchor claims, the two
refusals resolving to different lines from each other, a number moved by one
going red *and* naming the anchor's current line, a citation reworded out of its
declared shape being reported rather than passed, an anchor that has become
ambiguous reported as not found by this method, and a tool that cannot be read
reported as a broken check rather than an empty one.

```console
$ python3 ec/tools/test_check_eq_guard_citations.py
Ran 18 tests in 1.0s

OK
```

## Not found stale by this issue's method — the next sweep's starting list

Observed while measuring, and **not** re-pointed here: they belong to different
claims and different mechanisms, and three of them belong to the three open
issues above. Recorded so the next sweep starts from a list rather than from
zero. "Not stale" means the cited line still holds code of the kind the
sentence names, measured on `d330478`.

**The site column is re-measured on the merged tree**, because `main` edited
three of the four files it names in the same window; the branch's own figures
are `:4607`, `:4850`, `:7473`, `:8857` and `:8898` in `docs/findings.md` and
stand beside these per §4a-4d. **Every `cited` and `what is there now` cell is
a property of `xdata_register_map.py`, which this change does not edit and
neither side did, so those are unmoved and carried.** The `refusal-contract.md`
sites are the exception and this change moved two of them itself: they are
**+11** on this tree against `main`, because the `>` note this change adds above
them carries eleven lines. They are re-measured on the merged tree rather than
carried, which is the whole point of the table — a location copied from a
neighbouring column is the defect this change exists to stop, and it is no less
a defect in the table that hands the next sweep its list.

| site | cited | what is there now | verdict |
|---|---|---|---|
| `refusal-contract.md:24` | `:3196-3201` | `census_shape()`'s docstring; the `--self-test` guard-off machinery is at `:3407-3410` | **stale, not this issue's** — a different claim (`--self-test`) |
| `refusal-contract.md:45` | `:298-299` | a docstring about the flag; `OUT_REGISTERS`/`OUT_CLUSTERS` are at `:332-333` | **stale**, `OUT_CLUSTERS`'s own claim |
| `refusal-contract.md:86` | `:4602-4605` | a `co_reading_group_table` print header | **stale**, a comment that is not there |
| `refusal-contract.md:150`, `:153` | `:3627-3628`, `:3618` | guard 2 and guard 1, i.e. `:4985` and `:4976` | **a record of a past tree, left standing** — the mutation table describes a scratch copy of the tool as it stood, and #873's `:4499`-is-the-other-refusal defect is exactly the confusion a re-point would have hidden here |
| `refusal-contract.md:649` | `:2485` | a blank line | **stale** |
| `refusal-contract.md:683` | `:4623-4632` | `--export-ownership`'s refusal pair, now at `:5002-5011` | **stale** |
| `xdata-register-map.md:1313` | `:4396-4398` | a `check()` call in `--self-test` | **not stale** — plausibly the same rule; left as it is |
| `xdata-4-4-identity-rederivation.md:94` | `:390-393` | a comment; `MAP_COLUMNS` is at `:479` | **stale** |
| `xdata-4-4-identity-rederivation.md:125` | `:4396-4398` | as above | **not stale** |
| `xdata-4-4-identity-rederivation.md:473` | `:2723`, `:2885` | `return True` and `return out` | **stale** |
| `findings.md:4656` | `:1654-1655` | a comment about `F416.c`, not the cluster sort | **stale**, another mechanism |
| `findings.md:4899` | `:277`, "line 138" | a comment; `ASSIGN` is at `:377` | **stale**, and already retracted in place by #254's block below it — the block is re-pointed, the retracted figures stay visible |
| `findings.md:7510` | a line in `test_xdata_register_map.py` | a different file entirely, and the span lands on the module docstring | **not stale**, and not this tool's file |
| `findings.md:8941` | `:4315-4319` | the `check()` that reads `OWNERSHIP["main_distinct"]` | **not stale** |
| `findings.md:8982` | `:1753` | `if eq_guard and stripped.startswith("==")` | **not stale**, and already right |

## What this does not do

- **No tool, CSV, `registers.yaml` row or gate changed.** `xdata_register_map.py`
  is not edited; `agent-gates.sh` is not edited, and the new checker is not wired
  into it, because `.github/` is template-copied and this branch's token has no
  `workflow` scope. A human who wants it in the cheap tier adds one `gate` line
  next to the other `python3` tools, the way `check_citation_lines.py` would
  have to be.
- **No suite other than the new one changed.** `test_xdata_cluster_names.py::TheGuardOffRegeneration`'s
  `setUpClass` `AssertionError` and the `test_xdata_register_map.py`
  route-vs-`§6a` disagreement are live issues with their own owners.
- **No claim about the EC, the firmware, `registers.yaml`, or a register's
  behaviour.** Out of reach and not asked for.
- **No upstream submission.** Nothing here is destined for
  `Wer-Wolf/uniwill-laptop` or `tuxedo-drivers`, and per `CLAUDE.md` no stage
  opens an issue or pull request in another repository. Not applicable, stated
  for completeness.
- **No hardware and no Windows.** Not reachable from a runner, and no part of
  this issue needs it, so no `needs-hardware-test` framing is involved.
