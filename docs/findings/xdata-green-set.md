# The green set is empty, and the four sentences that said otherwise (issue #819)

The write-up for [issue
#819](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/819), about #753
landing and leaving four status sentences in the tree false. What this branch
changes is two annotation pages, one clause in §46, and this file. **No tool, no
CSV, no YAML, no suite and no gate script is edited** — the whole content is
that four claims are now wrong in writing, and three more are named.

**Nothing here is a hardware claim.** No register was read back, no capture was
opened, no image was parsed, and no laptop, EC or Windows machine is involved.
Every figure below is the output of a command over committed text, and the one
thing this branch reads that the prose does not is `ec/decompiled/index.csv`,
which is a file read. `git status` was clean of untracked scratch afterwards.
Nothing here establishes anything about the firmware: `XDATA_0860` stays
`present-untested` and no `status:` in `ec/annotations/registers.yaml` moved.

**The title is a measurement, and one dated correction now sits under it.** The
green set was empty when this issue was measured; it is **29 of 30** since, on
`ec/tools/test_check_cluster_citations.py`, which is red on this tree and on
`main` alike. The title is left as written, per §4a-4d; the blockquote under
**The measurement** is the correction, and the row under **Superseded claims**
is where it joins the set.

## The measurement

From the repo root, 2026-09-25:

```console
$ python3 ec/tools/xdata_register_map.py --self-test
...
  ok    the committed CSVs match a fresh generation (run without --check after changing anything the census reads)
  439 clusters at threshold 0.5; 1218 main-EC and 157 PD addresses
  all assertions passed                                            # rc 0

$ python3 ec/tools/xdata_register_map.py --check
  names: seeded 9, exact 0, carried by overlap 0, tied, not carried 0, with no name 430
ec/annotations/xdata-registers.csv: 1326 rows match a fresh generation from the committed tree at threshold 0.5
ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5
                                                                     # rc 0

$ python3 -m unittest discover -s ec/tools -p 'test_xdata_cluster_names.py'
Ran 28 tests in 15.7s
OK

$ python3 -m unittest discover -s ec/tools -p 'test_check_site_census.py'
Ran 45 tests in 0.6s
OK

$ bash tools/run-tests.sh
All 30 suite(s) passed, 882 tests.       # as this file recorded it; the re-run is below
```

The `run-tests.sh` command is recorded **twice on purpose**. The first is the
line this file carried, and it is kept rather than overwritten — the correction
below is what says it is false, which is the `../findings.md` §4a-4d pattern,
and a superseded line that is replaced rather than kept leaves the correction
pointing at nothing. The second is the same command re-run on this tree:

```console
$ bash tools/run-tests.sh
ec/tools/test_bank1_e582_framing.py: 10 tests, passed
ec/tools/test_check_capture_claims.py: 28 tests, passed
ec/tools/test_check_cluster_citations.py: FAILED
...                                  # the remaining 27 suites are green
30 suite(s) run, 882 tests; one or more FAILED.
```

The two per-suite discoveries are quoted separately on purpose: a total is a
property of the merge, and a failure should name its suite rather than only the
total. The paths in the `--check` output are printed absolute by the tool and
are shown repo-relative here; the rows and the counts are the tool's.

> **(Correction, 2026-09-25, issue #820) — the first of those two
> `run-tests.sh` lines is not what the runner prints, and the suite the failure
> names is red on this tree and on `main`.** That line read `All 30 suite(s)
> passed, 882 tests.`, which is false: the runner prints `30 suite(s) run, 882
> tests; one or more FAILED.`, and the failure is
> `ec/tools/test_check_cluster_citations.py::TheCommittedTree::test_committed_prose_matches_committed_census`
> — `2 citation(s) disagree with ec/annotations/xdata-clusters.csv`, both at
> `docs/findings/xdata-cluster-names-guard-off-recipe.md:220`, where `0x0464` and
> `0x0465` "are not a member of any cluster this line names …; it is a member of
> `main-ec-145`". **The 882 is unchanged and the other 29 suites are green; the
> totals line was never the part that was wrong to quote — the "All 30 suite(s)
> passed" before it was.** The wrong version is left above rather than deleted, per
> §4a-4d, and the four other measurements in that block are untouched: `--check`
> and `--self-test` both still exit 0 on this tree, and the two per-suite
> discoveries are still `OK`.
>
> **It is not this branch's red, and the way to know that is to re-run it on
> `main`.** In a clean worktree at `244c992b` (`origin/main`),
> `test_check_cluster_citations.py` fails with the same message on the same line;
> this branch touches neither that suite nor the line it reads. What the branch
> does do is touch this file, whose title claims the green set is empty, so
> leaving that claim standing would put a second falsehood in the same paragraph
> as the first — and **the cheap gate catches neither one**, because
> `agent-gates.sh` runs neither `tools/run-tests.sh` nor any check that reads
> prose. A green gate and a false recorded command are not in tension; the gate
> was never the witness for either.

**The two modes were cleared by different commits, and that is why each half of
the sentence naming both was wrong for its own reason.**
`test_check_site_census.py` went green in `23240095` (#752), which re-pinned
four `0x0860` rows to the lines the corrected `D091.c` has.
`test_xdata_cluster_names.py` went green in `64dbde19` (#753), which replaced
its copy-and-patch recipe with the tool's own `--no-eq-guard`. The sentence in
`xdata-register-map.md` that named both as red for "their own separate reasons"
described two unrelated defects, and a single landing did not clear either of
them.

## Why `--self-test` passes now, which is a mechanism and not the evidence

`xdata-register-map.md` recorded the failing assertion by name: *"the annotation
CSV and `index.csv` agree on every address they share"*, failing on
`bank1:0x9CE8`, `bank1:0x9D53` and `bank1:0xE2D3` because
`ec/decompiled/index.csv` still spelled all three `FUN_CODE_*`. Those three
rows now carry the annotation CSV's names:

| address | `ghidra-functions.csv` | `index.csv` |
|---|---|---|
| `bank1:0x9CE8` | `seed_1c12_trio_or_update_1c11_1c15_1c16` (`:914`) | same name (`:996`) |
| `bank1:0x9D53` | `seed_1c12_trio_9f_or_run_0x9d7a_ladder` (`:915`) | same name (`:999`) |
| `bank1:0xE2D3` | `dispatch_036c_low3_then_seed_1c00_block` (`:1182`) | same name (`:1333`) |

**That is why the command has something to pass, not the evidence that it
does.** The assertion is over every address the two files share, and these were
the three that used to disagree; the arbiter is `--self-test` itself, and a
fourth disagreeing address would still turn it red whatever these three rows
say. Re-derive it by running the command.

**What this does not explain, and the page that claims it does is still wrong
for it.** The re-export that brought `index.csv` up to date is
`build_ec_decompile.py` in its default export-only mode, which rewrites the
generated `ec/decompiled/**` tree. Nothing here says which commit did that or
that the naming backlog is otherwise closed — `--self-test` says the annotation
CSV and `index.csv` agree, which is one assertion, and `xdata-register-map.md`
still describes the `--self-test` half of its own bullet as unwired. **#815 owns
that half and this branch does not touch it.**

## The three owning issues, named so nobody files a fourth copy

| issue | what it owns | where the claim is |
|---|---|---|
| **#815** | the `--self-test` half of the naming drift, the gate's `--self-test` reason comment, and the decision to wire the mode | `xdata-register-map.md:2585-2591`; the `--self-test` half of both corrections in `xdata-06c2-06db-timers.md`; `.github/scripts/agent-gates.sh:218-234` |
| **#816** | "the only working scripted route to a guard-off census" — one of two since `64dbde19` | `xdata-no-eq-guard-refusal-contract.md:250-252` |
| **#817** | `tools/README.md`'s "874 tests" and "two of the thirty are red" | `tools/README.md:14-39` |

**`agent-gates.sh:138` is not this tool's arm**, which the issue's body gets
wrong and the next reader would inherit if the correction did not say so. `:138`
is the `*decompile_native.py)` case; the `xdata_register_map.py` arm is the
`*xdata_register_map.py)` case at `:235-236`, `python3 "$tool" --check || rc=1`,
under the comment at `:210-234` that explains why it is a cheap-tier gate.
*(Both pins are the pre-#823 file, recorded rather than edited for the same reason
as the table below: since `244c992b` the arm has moved to `:261-263` and reads
`--check && --self-test`, and the comment ends "So the honest description of what
is gated here is no longer the two CSVs" at `:253-254`. The `:138` finding — that
the issue's body names the wrong case — is unaffected, because `:138` still is
the `*decompile_native.py)` case.)* The
`for tool in` list entry at `:127` is right, and is the only one of the three
lines the issue quotes that is. `xdata-register-map.md:2582-2584` has said the
`--check` half is wired since #256, so the timers page's "Neither mode is in
`agent-gates.sh`'s tool list" contradicted a sibling page for as long as it
stood.

## Superseded claims, recorded here rather than edited

The same pattern `xdata-cluster-names-guard-off-recipe.md` set two merges ago.
Each of these phrases the red set in the present tense and is false for the
measurement above. **They are recorded, not edited**, and **a reviewer can
overrule that at a cost of one line each**:

| where | claim | now | owner |
|---|---|---|---|
| `xdata-register-map.md:2586` | "`--self-test` is red on `main` … `index.csv` still spells all three `FUN_CODE_*`" | `--self-test` exits 0; all three carry the annotation names | **#815** |
| `xdata-no-eq-guard-refusal-contract.md:261-269` | `test_check_site_census.py` "45 tests, 1 failure" | 45 tests, OK | #752 landed this; the page is a record |
| `xdata-no-eq-guard-refusal-contract.md:250-252` | "the only working scripted route to a guard-off census" | one of two, since `64dbde19` | **#816** |
| `docs/findings.md:6514` | "`tools/run-tests.sh` is 19 of 22 suites", in a dated section | 30 of 30 | inside an already-dated section; left as the record |
| `docs/findings.md:6682` | "21 of 23 suites, 609 tests … both reproduce on a pristine `main`" | 30 of 30, none red | as above |
| `docs/findings.md:7181` (§45) | "`ec/tools/test_xdata_cluster_names.py` is **red on `main`**" | green, since `64dbde19` | inside a dated section; the sentence already says "reported, not edited around" |
| `0751-grader-self-test-gate.md:349-354` | "the runner is red today. That was three suites … and is two now" | no failures | its own `Left out on purpose` bullet, already telling the reader to re-derive |
| `0751-grader-self-test-gate.md:360-365` | "the runner is red today on the two suites finding (2) names" | no failures | as above |
| `runner-red-suite-set.md:70-90` | "the runner is red … **is still one** … should expect two rather than three" | the set is empty | the file this issue's write-up is the complement of; its §46 companion now says so |
| `runner-red-suite-set.md:146-149` | "**The two remaining red suites** … Naming them is the point" | neither remains | as above |
| `ec/tools/test_check_cluster_citations.py` — **not a claim but a new member of the set**, so it is a row and not a correction | `TheCommittedTree::test_committed_prose_matches_committed_census`, red on this tree and on `244c992b` | **1 of 30 red**, since the measurement above | the `#820` blockquote under **The measurement**; unowned as of that correction |
| `xdata-cluster-names-guard-off-recipe.md:289-292` | "No gate is wired … `--check`/`--self-test`, which are red on `main`" | both green; `--check` *is* wired | a **closed** issue's write-up; its "What this does not do" records that PR's scope, not a live claim |
| `.github/scripts/agent-gates.sh:218-234` | "`--self-test` is deliberately not run … It is red on `main` for a reason no census change can clear" | the decision stands, **the reason is gone** | **#815**; template-copied, so a change is upstream and a re-copy |

**The last row is the one that is false on its condition rather than on its
conclusion.** The gate still declines to run `--self-test`, and the
deliberateness is unchanged; what has gone is the justification. Correcting it
is a change to a file copied from `ElDavoo/agent-pipeline`, and this repository's
push token has no `workflow` scope, so it is named here instead. *(Superseded in
turn by #823, `244c992b`, which wired `--self-test` in and rewrote the comment; the
row is left as the #819 measurement.)*

**Every `now` cell in that table that reads "30 of 30", "none red", "no
failures", "the set is empty" or "neither remains" was true when this issue was
measured and is false now, by the one suite in the new row.** They are left
unedited for the same reason the claims they name are — each is a dated answer to
a question, and the dated answer is the record. The current answer is **29 of 30,
one red**, and the way to re-derive it is `bash tools/run-tests.sh`; the totals
line it prints is deliberately not quoted here, for
`runner-red-suite-set.md:40-47`'s reason. This file's own title claims the green
set is empty, and **it was, at `d87d877e`; it is not, and the correction to that
is the blockquote under **The measurement** rather than a rewrite of the title.**

**What the new member is, and is not.** It is a bookkeeping disagreement about a
transcribed cluster id: a printed console block in a **closed** issue's write-up
names eleven `main-ec-*` clusters, and `0x0464`/`0x0465` are in `main-ec-145`,
which that line does not name. Whether the transcript moves or the CSV does is a
judgement about a closed record, not a mechanical edit, and it is not this
branch's — the branch does not touch that line. The green set going from empty
to one is therefore **not** evidence for any earlier claim on this page going the
other way: two census modes being green and 29 suites being green are separate
measurements, and a suite red in a third place says nothing about either of them.
Which measurement produced the empty set, and whether anyone re-ran the runner
after it, is not recorded in the tree and is not guessed at here.

## The five sentences corrected in place, and where

Each gets a dated blockquote directly beneath it, per §4a-4d; not one is deleted
or reworded. **Each correction quotes the sentence it corrects rather than
pinning its line number**, for the reason
`xdata-cluster-names-guard-off-recipe.md:249` gives: line pins in corrections
have already moved once in this file.

- `xdata-register-map.md` — the "two other suites … are red for their own
  separate reasons" sentence, and the same block's own closing "that leaves
  **one** suite of the two red". Appended **inside** the existing #752
  blockquote as a second dated paragraph, so one block carries both in date
  order rather than printing a correction under a paragraph that then contradicts
  it — which is the defect this issue is filed about.
- `xdata-06c2-06db-timers.md` — both sentences of the "neither is green today"
  paragraph, including the "Neither mode is in `agent-gates.sh`'s tool list"
  clause, and separately the second phrasing at the note on `--self-test`.

**The issue counts four unowned sentences in two files; these are five sites, and
the fifth is the one its own table splits across two rows.** The timers page
phrases the mode claim twice — once as "neither is green today: both exit 1 on
`main`" and again, nine lines later, as "**red on `main` at the time of
writing**" — and the issue assigns the `--check` half of the first to this issue
and the `--self-test` half to #815, while the second phrasing asserts the same
thing about the same two modes. Correcting one copy and leaving the next would
reproduce, at that sentence, exactly the defect the issue is filed about at
`xdata-register-map.md:2606`. **A reviewer who prefers the issue's own count can
drop the second blockquote on that page and nothing else moves.**

**The drift figures in that page's second paragraph are left alone.** Its 9
symbol rows, 3 function names, 32 register rows and 6 cluster rows described a
drift that was real, and they are part of a dated record; only the present-tense
verdict and the closing "that redness … is not fixed here" are corrected. The
correction says the drift was real and has since been cleared, and does not
re-derive the figures — the current answer to the same question is `--check`
reporting 1,326 rows matching a fresh generation, which is a statement about the
committed CSVs and not a re-derivation of the 32 and 6.

## Left out on purpose

- **`xdata-register-map.md:2585-2591`**, the `--self-test` half. #815's row in
  the issue's own table, and its title names the comment and those three rows.
  It is false for the same reason, and this branch points at #815 rather than
  correcting a claim another issue is mid-way through.
- **`agent-gates.sh`**, for the three independent reasons above: the issue
  assigns it to #815, it is copied from `ElDavoo/agent-pipeline`, and #815's
  title covers it. `.github/scripts/` *is* pushable — only
  `.github/workflows/` and `.github/actions/` are not — but pushable is not the
  same as ours to edit.
- **Wiring `--self-test` or `tools/run-tests.sh` into the gate** (#815, #162).
  A template-copied file and a deliberate decision, both owned elsewhere. *(The
  `--self-test` half of that decision has since been taken by #823, `244c992b`,
  which wired the mode in and rewrote the comment giving the reason; `tools/run-tests.sh`
  is still unwired and #162 is still open for it. Recorded rather than edited,
  per the same reason as the table above.)*
- **`tools/README.md` (#817), `xdata-no-eq-guard-refusal-contract.md` (#816),
  and the dated sections named in the table above.** Recorded, not edited:
  editing a closed PR's write-up or an already-dated section is rewriting a
  record, and these are one line each.
- **A new test.** There is no gate in this repository that reads prose, so a
  "claims stay true" check would be a new tool for a five-sentence change, and
  `tools/test_readme_suite_table.py`'s job is the suite *index*, not the claims
  in the pages it indexes. The commands are the test, and they are above.
- **The §6a figures.** They are right and are not re-derived here;
  `ec/tools/test_xdata_cluster_names.py:339`
  (`test_the_census_is_the_one_6a_measured`) now pins all eleven — the seven it
  pinned when this was written, and the four per-subset direction rows #850
  added.
- **`ec/tools/test_check_cluster_citations.py`**, the one suite red on this tree
  and on `main` as of the `#820` correction above. **Naming it is the point;
  fixing it is not**, for the reason `runner-red-suite-set.md:146-149` gives about
  its own two — it wants a printed transcript in a closed issue's write-up either
  to move the eleven clusters it names or to have the committed CSV change under
  it, and that is a judgement about a record rather than a mechanical edit. It is
  not this branch's either: the failing line,
  `xdata-cluster-names-guard-off-recipe.md:220`, is untouched here and the same
  case fails identically at `244c992b`.
- **Hardware, Windows, the image, and a `build_ec_decompile.py --work`
  re-export.** Nothing here needs one and no sentence written may be read as
  reporting one.
- **Anything upstream, and any issue closure.** Nothing in this change ends at a
  `Wer-Wolf/uniwill-laptop` or `tuxedo-drivers` pull request, so there is no
  prepared patch to hand over; #10 stays where it is. #568 and the siblings
  stay open — whether a superseded issue should be closed is a human's call.

## The test that proves it works

The issue's chain, which is still a prose fix and one command each — but **the
third command in it is red**, and that is the `#820` correction under **The
measurement** rather than a new measurement:

```console
$ python3 ec/tools/xdata_register_map.py --check && \
  python3 ec/tools/xdata_register_map.py --self-test && \
  bash tools/run-tests.sh
```

The two census modes are the first two and both exit 0; `tools/run-tests.sh` is
the third and stops the `&&`. Run the first two on their own for the claim this
issue makes.

and the two greps that show where the false phrasing still stands, and where it
stands only as a quotation. **Both carry a pathspec, and both patterns are
shorter than the sentence**, and the reason is that **neither `../findings.md`
line this block used to record is what its own command returned.** The first
pattern was `exit 1 on \`main\``, which does not occur on any single line of
`../findings.md` at all — it wraps across `:7447-7448`, so
`git grep -n "exit 1 on \`main\`" -- docs/findings.md` prints nothing and the
`:7400` line the block carried was the block's own transcript, not a hit. The
second pattern was `are red for their own separate reasons`, which does match,
but at `:7445` and reading `are red for their own separate reasons" and that
block's own closing "that` — not the `two other suites that read these CSVs …`
the block recorded against `:7397`, which is a string that runs from `:7398` into
`:7399`. The patterns below fit on one line in every file they match, and
the `:!docs/findings/xdata-green-set.md` exclusion is what keeps this block from
matching its own transcript:

```console
$ git grep -n "green today: both exit" -- . ":!docs/findings/xdata-green-set.md"
docs/findings.md:7447:`ec/annotations/xdata-06c2-06db-timers.md`, "neither is green today: both exit
docs/findings/xdata-census-self-test-gate.md:219:  — "neither is green today: both exit 1 on `main`". Both exit 0. Its
ec/annotations/xdata-06c2-06db-timers.md:973:green today: both exit 1 on `main`, on the naming drift described below. What

$ git grep -n "red for their own separate reasons" -- . ":!docs/findings/xdata-green-set.md"
docs/findings.md:7445:are red for their own separate reasons" and that block's own closing "that
ec/annotations/xdata-register-map.md:2609:  CSVs are red for their own separate reasons and are not in that loop either:
```

**Five hits, and only two of them want a correction.** Three of them are
somewhere else quoting the sentences in order to name them, which is what a
write-up of this kind is for: both hits in `../findings.md` are §51, and
`xdata-census-self-test-gate.md:219` is the same move in that file's **Named, not
edited** list, where the false sentence is the item being named. None of the
three is a claim of its own, so none wants a second correction; the two that
matter are distinguished by what follows them, not by the string. The timers
paragraph ends at `:979` and a `#819` blockquote opens at `:981`. The register-map
sentence at `:2609` is followed at `:2615` by the `#752` block, and `#819`'s
entry is appended **inside** that block at `:2631` — one block carrying two dated
entries in date order, which is the point: the issue's complaint was a paragraph
contradicting the correction printed immediately beneath it, and a second block
*under* the first would have been that defect again. **So `grep -A6` is the wrong
window for the second of the two**; what settles it is that the next `> **` after
the sentence is a correction block, and the next `issue #819` inside that same
block — not a new block.

The issue writes the first grep with backticks inside single quotes, which a
shell will not do; the double-quoted form above is the runnable one. Everything
the commands need — `python3`, the standard library's `unittest`, `git grep`,
`bash` — is preinstalled on `ubuntu-latest` or installed by
`.github/actions/project-setup`. Nothing here needs Ghidra, radare2, sdcc,
ilspycmd, UEFIExtract or a network, and a reviewer can re-derive every figure in
about fifteen seconds.
