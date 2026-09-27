# What `tools/check_doc_patch_refs.py` reads, in both directions (issue #955)

Issue [#955](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/955) opened
by the follow-up pass off #944 read the check added by
[#777](doc-patch-reference-gate.md) and found that **both of its "every"
claims were narrower than the wording used for them, in two different
directions**. The live direction held a glob over `*.patch` while its
write-up said every patch in `docs/ci/`. The reference direction read `*.md`
while its write-up, its self-test assertion and its `tools/README.md` cell all
said every reference. Both gaps are demonstrable on a `tempfile` copy of the
committed tree, and this file records what was decided, what it cost, and what
is still not checked.

Neither direction is a live test and nothing here is evidence about the
firmware. This is arithmetic over committed text and copies of it: no EC is
opened, no register is read back, no capture is taken, no `status:` in
`registers.yaml` moved, and no laptop, EC or Windows machine is involved.

## What each direction covered before

`on_disk()` was `sorted(p.name for p in ci.glob("agent-gates-*.patch"))` — a
glob over `.patch` — and `markdown_files()` was `root.rglob("*.md")`. The
subject is the `docs/ci/agent-gates-*.patch` set, and `docs/ci/` holds seven
files: six patches plus `agent-gates-deep-schedule.yml`, which
[`prepared-gate-patches.md`](prepared-gate-patches.md) records as a deliberate
exclusion and which is a `cp` into `.github/workflows/` rather than a
`git apply`.

The exclusion is right for the *name parse* — `NAME` ends in `\.patch`, and
`tools/test_doc_patch_refs.py::test_the_yml_sibling_is_not_a_name` pins that a
`.yml` span is not a name. The on-disk side is a different code path, and
nothing held it. The issue's demonstration stands: rewrite every citation of
the yml to a paraphrase on a scratch copy and the run stayed green.

## Decision 1 — the live direction: a named non-patch entry beside the glob

Taken, over "admit the `.yml` by shape".

- A module constant beside `HISTORICAL` — `PREPARED_NON_PATCH` — naming the
  prepared changes in `docs/ci/` that are not `.patch`. One entry today.
- `on_disk()` keeps its `.patch` glob and **adds that name only when the file
  is present**, so `uncited` keeps meaning "a prepared change that is there and
  nothing names it". The conditional is load-bearing: a `mini_tree` fixture
  holding one synthetic patch and no yml has to stay green, or every synthetic
  case in the tool and its suite would report the yml on a tree that never had
  it.
- Presence is a **separate verdict**, not a fold into `uncited`. A new `Result`
  field, a `MISSING:` line in `report()`, a term in `population()`, and a term
  in the total `check_mode()` returns. That is the same bidirectional
  arrangement the `HISTORICAL` `absent`/`dead` pair already has and the same
  one `tools/test_readme_suite_table.py` is cited for: the written-down set is
  compared against discovery in both directions, so a rename or a delete of the
  yml goes red and the failure names the file.

**The alternative declined, and why.** Widening the glob to `agent-gates-*` or
`agent-gates-*.*` admits any file a `git apply --reject`, an editor backup or a
stray copy leaves in `docs/ci/`. The exclusion recorded in
`prepared-gate-patches.md` is about *what the file is* — a `cp`, with no
pre-image to go stale against, and order-independent — and not about its
extension, so a shape is the wrong thing to key on.

**The name parse is untouched.** `NAME` still ends in `\.patch`, and
`test_the_yml_sibling_is_not_a_name` is unchanged. The two directions are now
deliberately decoupled: the file is held on disk and is not parsed as a
reference. That decoupling is the thing this file exists to explain, and it is
what makes the citation half of the entry a coarser test than the other
entries get (below).

## Decision 2 — the reference direction: a declared set, with `*.py` out

Taken as a partial widening, which is a third path the issue lists but does not
spell out.

- The declared set is **prose (`**/*.md`, minus `SKIP`) plus
  `docs/ci/**/*.patch`**, as an explicit tuple (`REFERENCE_GLOBS`) beside the
  two globs, not a bare `*.patch`: `linux/patches/` holds two `.patch` files
  outside the set, and the scope is stated rather than incidental. Neither of
  those two names a name in the subject today, so nothing changes for them.
- **What the widening actually finds**, measured rather than assumed:

  | file | line | names | in a `#` header? |
  |---|---|---|---|
  | `docs/ci/agent-gates-pin-table-rows.patch` | 55 | `agent-gates-testdata-row-claims.patch` | yes |
  | `docs/ci/agent-gates-testdata-row-claims.patch` | 16 | `agent-gates-capture-claims.patch` | yes |

  Both are live names, so staleness over the widened set stays at zero, and
  what the widening buys is that a *future* rename of one patch goes red on the
  *other* patches' header comments — a reference class no prose grep can see,
  and one `tools/test_agent_gates_patches.py` case 6 does not cover, since case
  6 holds each header's own `git apply` line rather than cross-references
  between headers.

- **`.py` is left out, with the reason.** Measured, a `*.py` scan would find 49
  parsed references tree-wide and report **four distinct deliberately-absent
  fixture names — 16 occurrences — as STALE**:

  | fixture name | occurrences |
  |---|---|
  | agent-gates-a.patch | 8 |
  | agent-gates-gone.patch | 4 |
  | agent-gates-never-existed.patch | 2 |
  | agent-gates-b.patch | 2 |

  They are the names this tool's own self-test and suite use for "a patch on
  disk", "a patch nobody names" and "a name that is not there", and they are
  **written without backticks in that table on purpose**: a backticked one is a
  parsed reference, so the check reports this file's own table as STALE. That
  is the check working rather than a defect, and it is a small demonstration of
  the rule — the first draft of this paragraph had them in backticks and
  `--check` went red on it.

  A `*.py` scan would also make the "still cited" half of every `HISTORICAL`
  key self-certifying, because this tool's own docstring names all three. That
  is the exclusion this tool's design argues against — "a fourth absent name is
  refused here rather than needing a fourth entry, so the exemption cannot
  widen by accident" — and a `*.py` scan would have to introduce exactly the
  mechanism the sentence rules out.

### The `.py` citations, by name and by path

Recorded rather than counted, per the decision above. Five `ec/tools/` files
carry **live-direction** citations the check does not see, so a rename of any
of those three patches is reported against the prose and not against these:

| file | line | names |
|---|---|---|
| `ec/tools/grade_0751_isolation.py` | 228 | `agent-gates-0751-self-test.patch` |
| `ec/tools/test_grade_0751_isolation.py` | 4376 | `agent-gates-0751-self-test.patch` |
| `ec/tools/test_check_pin_table_rows.py` | 630 | `agent-gates-pin-table-rows.patch` |
| `ec/tools/test_data_regions.py` | 14 | `agent-gates-disasm8051-self-test.patch` |
| `ec/tools/test_check_history_checkouts_corpus.py` | 84 | `agent-gates-capture-claims.patch` |

The issue named three of these five. The files a wider scan would newly govern
are issue #772's, which is why this is recorded here and left as it is.

## Three populations in one tool, and which verdict is computed over which

This is the part a reader has to be able to hold, so it is stated as a table
rather than left implicit in the code:

| verdict | population | why |
|---|---|---|
| `stale` | the whole declared set | a name a patch header no longer matches is as stale as one a sentence no longer matches |
| `uncited` (patches) | the whole declared set | same reasoning, mirrored |
| `uncited` (the non-patch entry) | **prose only** | see the diff-body finding below |
| `uncited_keys`, `dead` — `HISTORICAL` liveness | **prose only** | a patch's own header must not keep an exemption alive by itself |
| `missing` | the named constant against `docs/ci/` | a write-down compared against discovery |

The two prose-only rules are not tidiness. Each prevents a specific silent
pass, and each has a case that goes red when it is reverted.

## The diff-body finding: a `+` line is not a citation

The issue lists, as a *future* risk, that a patch that adds markdown
containing a backticked patch name would contribute a reference that is a diff
body rather than a live citation. **For the non-patch entry that risk is
already realised.** The one place
`docs/ci/agent-gates-capture-claims.patch` names
`agent-gates-deep-schedule.yml` is line 197:

```
+# schedule, which is prepared at docs/ci/agent-gates-deep-schedule.yml and not
```

That is a `+` line — a comment the patch *adds* to a Python file — not a header
of its own naming a sibling. It is the only non-prose mention of the yml
anywhere in the declared set.

So the non-patch entry's citation is read over prose. Two reasons, and the
second is the decisive one:

1. It is the only population in which every match is a citation by a reader,
   which is what makes `uncited` a true statement about the tree.
2. Counting the `+` line would let a **diff body sustain the liveness of a
   prepared change whose every real citation had been deleted** — a false
   negative produced by a phantom, which is worse here than a false positive a
   reader can see and an edit to make. That is the same trade
   `doc-patch-reference-gate.md` states for `HISTORICAL`.

The widening's own two references are both `#` header lines, so nothing else is
affected. The suite pins **discovery** — that a `.patch` file is read as a
reference source at all — without pinning the diff-body verdict, so the caveat
cannot be mistaken for a decision.

## The census, re-measured over the set the check now reads

The figures below are measurements, and the command is here so a reader
re-derives them rather than trusting them. **`--check` prints the live one.**

Two facts make a pasted number here a poor substitute for that line, and both
are worth stating rather than working around. This file's own references are
part of the population it measures, so writing the figure down moves it; and
`doc-patch-reference-gate.md` makes the same point about its own census. So the
figures are given as differences, which do not move:

| tree | name references | files | links | prepared changes |
|---|---|---|---|---|
| as found, before this change | 112 | 32 | 6 | 7 |
| after the widening, before this file existed | 114 | 34 | 6 | 8 |

The difference between those two rows is **exactly the two table rows above**
and nothing else: two more references, in two more files, both in a prepared
change's `#` header; and one more prepared change, the yml. The link count and
the historical-key count did not move at all.

What did **not** move, and is worth stating because the issue expected it to:
the `.py` population is in none of those figures. It is counted in the table
above and excluded by decision, and no number in the census is a floor — the
check prints whatever the tree holds when it is run.

## The two scratch-tree demonstrations

Both are in the suite, and both are the shape the issue asked for.

**Removing the yml from a copy** goes red by name, and is *not* reported a
second time as an uncited change — the file is not there to be named, and the
two verdicts want different edits:

```
MISSING: docs/ci/agent-gates-deep-schedule.yml is in PREPARED_NON_PATCH and is not there, so a rename or a delete of it is invisible to the glob
```

**Rewriting every prose citation of the yml to a paraphrase** — the issue's
"done" clause, and the tree it could not go red on — now goes red the other
way, by the mirror half:

```
UNCITED: docs/ci/agent-gates-deep-schedule.yml is on disk and nothing this check reads names it
```

The strip is over **prose**, and that is the measured distinction rather than a
convenience: a strip over the whole declared set leaves
`capture-claims.patch`'s `+` line in place, and for that reason alone the run
would stay green. The suite pins both — the strip that goes red, and the
`+`-line boundary that keeps it scoped.

## A pre-existing red, found while planning and fixed here

`--self-test` **failed on the committed tree before this change**, on
`assert_that(len(live.links) == 2 and live.link_files, ...)`. That was a
hand-pinned count written when the tree carried two markdown links onto a
patch; the tree now carries six across four files, and every later merge that
added one turned the self-test red. `tools/test_doc_patch_refs.py` passed
throughout precisely because `test_the_link_onto_a_patch_resolves` asserts
non-emptiness rather than a number.

The assertion is now the non-empty form, with the named files kept in the
message so a reader who emptied the set is told which ones went. This is the
tool's own "no count is asserted" rule applied to itself, and without it the
self-test could not go green at the end of a change to this tool.

## The wording, and where it was fixed

The "every" claim is the subject of the issue, so the fix is exact rather than
approximately generous. Each place now names the set:

- `tools/check_doc_patch_refs.py` — the scope paragraph, the live-direction
  paragraph, the "what this does not check" limits, the self-test's rename
  assertion, and `main()`'s scope line, which prints the declared tuple.
- `tools/test_doc_patch_refs.py` — the module docstring, the rename assertion,
  and the liveness case, which now says *prose* rather than *markdown* because
  that is what it reads.
- `tools/README.md` — the one cell for this suite, and no other cell, no new
  row, and no count.
- `doc-patch-reference-gate.md` — in place, per §4a-4d: a fifth entry in the
  corrections list, a dated correction beside the live-direction paragraph, a
  dated correction beside the `.py` bullet, and a pointer to this file. Its
  console transcript block is left verbatim, because it is a record of that run
  at that commit and the file already labels it as one.

## The mutations, and which case caught which

A widening that cannot fail is not a widening, so each change was run once
against a copy of the tool with that change reverted. Every case below is red
under its own mutation and green without it:

| mutation | caught by |
|---|---|
| the named entry dropped from `on_disk` | 3 self-test assertions, 6 suite cases |
| `docs/ci/**/*.patch` dropped from the declared set | 1 self-test assertion, 4 suite cases |
| `HISTORICAL` liveness moved off prose-only | 1 self-test assertion, 1 suite case |
| the non-patch citation moved off prose-only | 2 self-test assertions, 1 suite case |

The third and fourth are the interesting pair: they move in opposite
directions, and each is caught only by the case written for the rule it
violates. The fourth is not in the issue and is here because the diff-body
finding above is the reason the rule exists.

## What this does not check

- **The `.py` population**, by decision. The five files and the reason are
  above; the files a wider scan would newly govern are #772's.
- **A renamed non-patch entry leaves its prose citations unreported.** Its name
  is not parsed, so `stale` cannot see them. The `MISSING` verdict reports the
  rename once, by naming the file that is gone; the surviving stale citations
  are not enumerated. Named here rather than fixed, because the issue's own
  instruction is to leave the name parse alone.
- **A diff-body reference.** A `+` line naming a patch would be counted as a
  reference. It is the caveat above, realised for one name today and possible
  for others; nothing distinguishes a header from a diff body in the parse.
- **Whether a reference's sentence is instructing or describing.** That is what
  `HISTORICAL` stands in for, at name granularity, at a cost stated in
  `doc-patch-reference-gate.md`.
- **The patches themselves.** Whether each applies, and whether its header
  names itself, is `tools/test_agent_gates_patches.py`'s.
- **Anything about the laptop.** No EC, no capture, no register, no Windows box.
  Nothing here needs `needs-hardware-test` and no live run is implied.
