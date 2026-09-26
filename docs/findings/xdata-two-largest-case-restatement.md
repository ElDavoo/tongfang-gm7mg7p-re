# The two-largest case passed vacuously; its exhibits are now derived (issue #778)

`ec/tools/test_xdata_cluster_names.py` had a case named
`test_the_two_largest_cited_clusters_are_carried_by_overlap_not_by_key` whose
name claimed it ruled out a key-only identity design, and which could not have
failed for that reason. It is now
`test_every_name_the_key_cannot_find_is_carried_by_overlap`, and it derives the
clusters it examines from the census rather than naming two of them in advance.

**Nothing here is a live observation.** Every figure below is a function of
`ec/annotations/xdata-clusters.csv` and of the committed
`ec/tools/xdata_register_map.py` run over the committed decompiled C. No
hardware, no Windows, no image, no Ghidra. The census CSVs are inputs and this
change touches neither: `xdata_register_map.py` refuses `--no-eq-guard` with
the committed output paths, so every run below writes to a scratch directory.

## The defect was a vacuous pass, not a red

The issue as filed opens "`python3 ec/tools/test_xdata_cluster_names.py` is red
on `main` today — 21 tests, one `setUpClass` error". That was true when it was
written and is not true now: #753 landed the `--no-eq-guard` recipe at
`ec/tools/test_xdata_cluster_names.py:88`, and the suite reports

```console
$ python3 ec/tools/test_xdata_cluster_names.py
Ran 30 tests in 18.166s

OK
```

So the case was not red. It was **green, and passing for the wrong reason**,
which is a worse state than red because nothing about it is visible from the
run. The two pairs it hard-coded are disjoint clusters:

| pair as typed | committed row | guard-off row | Jaccard |
|---|---|---|---|
| `("main-ec-001", "mode-oem-init")` | `main-ec-001`, 152 addrs, **unnamed**, `ke794087e13a6` | `mode-oem-init` at `main-ec-002`, 93 addrs, `kc0f2a0be0103` | **0.0000** |
| `("main-ec-002", "level-block-086x")` | `main-ec-002`, 92 addrs, `mode-oem-init`, `kefb63d82f8c7` | `level-block-086x` at `main-ec-004`, 28 addrs, `ka39cda99615f` | **0.0000** |

```console
$ python3 - <<'PY'
import csv, os, subprocess, sys, tempfile
tmp = tempfile.mkdtemp(); oc = os.path.join(tmp, "c.csv")
subprocess.run([sys.executable, "ec/tools/xdata_register_map.py",
                "--no-eq-guard", "--out-clusters", oc,
                "--out-registers", os.path.join(tmp, "r.csv")], check=True)
rows = lambda p: list(csv.DictReader(open(p, newline="")))
committed, off = rows("ec/annotations/xdata-clusters.csv"), rows(oc)
byname = {r["cluster_name"]: r for r in off if r["cluster_name"]}
for cid, name in (("main-ec-001", "mode-oem-init"),
                  ("main-ec-002", "level-block-086x")):
    old = {r["cluster_id"]: r for r in committed}[cid]
    new = byname[name]
    ja = len(set(old["addrs"].split()) & set(new["addrs"].split())) \
        / len(set(old["addrs"].split()) | set(new["addrs"].split()))
    print(cid, name, "->", f"jaccard={ja:.4f}")
PY
main-ec-001 mode-oem-init -> jaccard=0.0000
main-ec-002 level-block-086x -> jaccard=0.0000
```

The case's load-bearing assertion was `assertNotEqual(new["cluster_key"],
old["cluster_key"])` — and that is true of **any two distinct clusters**, by
definition of a key being a function of the membership. It compared the largest
cluster in the census, which carries no name at all, against an unrelated one,
and both halves passed. The case's own comment was half true even then:
"`main-ec-001` and `main-ec-002` are the two largest clusters the prose cites"
— `main-ec-001` is the largest and is unnamed, and the most-cited named cluster
is `counter-sweep` at `main-ec-003` (16 markdown files cite the id, against 15
for `main-ec-002` and 8 for `main-ec-001`), which this regeneration leaves
untouched.

## What the carry actually does on this census

Nine committed names, 445 clusters under the guard-off regeneration:

```console
$ python3 - <<'PY'
import csv, collections, importlib.util, os, subprocess, sys, tempfile
spec = importlib.util.spec_from_file_location(
    "xrm", "ec/tools/xdata_register_map.py")
xrm = importlib.util.module_from_spec(spec); spec.loader.exec_module(xrm)
tmp = tempfile.mkdtemp(); oc = os.path.join(tmp, "c.csv")
subprocess.run([sys.executable, "ec/tools/xdata_register_map.py",
                "--no-eq-guard", "--out-clusters", oc,
                "--out-registers", os.path.join(tmp, "r.csv")], check=True)
rows = lambda p: list(csv.DictReader(open(p, newline="")))
_n, report = xrm.carry_names(rows("ec/annotations/xdata-clusters.csv"), {},
                             rows(oc))
print(dict(collections.Counter(r["how"] for r in report)))
for r in report:
    if r["how"] == "overlap":
        print(r)
PY
{'none': 436, 'overlap': 1, 'exact': 8}
{'cluster_id': 'main-ec-002', 'cluster_key': 'kc0f2a0be0103',
 'name': 'mode-oem-init', 'how': 'overlap',
 'jaccard': 0.9680851063829787, 'from_key': 'kefb63d82f8c7', 'detail': ''}
```

**Eight `exact`, one `overlap`, 436 `none`.** The one name the key cannot find
is `mode-oem-init`, carried from committed key `kefb63d82f8c7` onto guard-off
key `kc0f2a0be0103` at Jaccard **0.9681** — the same cluster the census file's
own note records as re-keyed three times, most recently for #279 at 0.84.

**The same run's own summary line reads `seeded 8, exact 0, carried by
overlap 1 … with no name 436`, and the two are not a disagreement.** The tool
passes `xdata-cluster-names.csv` as its `seeded` map, so a name the names file
already anchors is reported `seeded`; the case under test passes `{}`, so the
same eight arrive by the census's own key instead and read `exact`. Same nine
names, same one overlap, same 436. The distinction is the point of the
`seeded` outcome — a human saying so outranks the tool's guess — so the case
deliberately withholds the names file to exercise the route the assertion is
about.

This confirms the reading already published in
[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md) and
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md): `level-block-086x` is
found by its key, key and membership both unchanged, and `mode-oem-init` is the
only name that arrives on overlap. Neither finding is corrected here. What
changes is that the suite now *demonstrates* it from the census rather than
asserting a consequence of two typed literals.

## Deriving rather than typing

A typed pair is a snapshot of the merge it was written on, and this one was
written on an older census. #279's pair-accessor pass (`6bf9c234`) moved
`mode-oem-init` to `main-ec-002` and `level-block-086x` to `main-ec-004`, and
the case went on comparing `main-ec-001` against `main-ec-002`. Nothing failed,
because a wrong id is still a valid id and the assertion on it is true of any
cluster that is not the one it names.

The replacement calls the tool's own carry and keeps the records it labels
`overlap`, which is by construction "a named committed row whose key did not
match this one and whose membership did". It then asserts, per record:

- `from_key != cluster_key` — the rule the case exists for;
- `jaccard >= xrm.CARRY_MIN_JACCARD` — the tool's own 0.50, not a literal;
- the guard-off row at `cluster_id` carries `name`;
- `from_key` resolves to a committed row carrying the same name.

Nothing in it reads a cluster id or a name, so the next re-key moves the
exhibits rather than breaking them.

**The count stays prose.** One overlap record today, at 0.9681, and the case
asserts `assertTrue(carried, …)` rather than `assertEqual(len(carried), 1)` for
the reason `test_and_the_tool_says_what_moved_about_it` already gives for
keeping `assertTrue(movers, …)`: a pasted count goes red on any re-derivation
for a reason that says nothing about the design being argued.

## The negative control, and the one that distinguishes this from the status quo

Pointing the derived set at `level-block-086x` — a cluster the key *does* find,
`exact` at unchanged key `ka39cda99615f` — turns the case red:

```
AssertionError: 'ka39cda99615f' == 'ka39cda99615f' : level-block-086x was found
by its key, so it is not one of the clusters a content hash alone would have lost
```

The old case could not fail this way: the assertion it made, key inequality
between two typed clusters, is what the temporary edit above *satisfies*. That
is the whole difference between a case that tests its name and one that does
not, and it is a property of the selection rather than of the tree.

Selecting an outcome with no records turns it red on the census-naming
message instead, which is the second half of the guard:

```
AssertionError: [] is not true : no committed name reached the guard-off census
on membership overlap, so nothing here shows a cluster_key is not a sufficient
identity: 9 committed names ['countdown-06c6', 'countdown-06cd',
'counter-sweep', 'fan-step-08a0', 'ff-fill-stubs', 'flag-pair-0442',
'level-block-086x', 'mode-oem-init', 'user-clear-bytes'], 9 in the guard-off
census, and none of them cleared 0.5 against a cluster whose key had changed
```

Both edits were temporary and both are reverted; the committed case carries
neither.

## The docstring's three figure sets

`TheGuardOffRegeneration`'s docstring carries three generations of the
guard-off regeneration's figures: issue #274's "427 clusters become 439, 48 of
the ranks survive intact and 379", the superseded middle pair "430 → 439 with 64
ranks intact and 366 changed", and the current "439 → 445 with 124 ranks intact
and 315 changed". A reader had three generations and no statement of which one
the class runs on.

It now says so, and adds why the three can stay where they are: the class's
assertions are threshold-based (`> 300` moved ranks, and §6a's figures held to
§6a rather than to a rank count), so a re-derivation moves all three of these
without turning the class red. The historical sets are not edited — they are the
record of the trees they were measured on, which is what the docstring already
said about them.

**One correction to the issue, in the same place.** The issue offers a
guard-on re-run as "439 → 439" and reads the third set as stale. It is not
stale. A guard-on generation from this tree is 439 rows, cell-for-cell the
committed census — which is what `--check` exiting 0 means — but that is a
*different* measurement, and the docstring never claimed to be about it. The
third set is the guard-off one and it is what the run gives today. The narrower
edit is the one that landed.

## What this does not claim

- The suite is **not** wired into `.github/scripts/agent-gates.sh`, so none of
  the above is enforced in CI. That is #162's, by way of #773's prepared-patch
  route, and the push token has no `workflow` scope.
- `bash tools/run-tests.sh` reports **`35 suite(s) run, 1076 tests; one or more
  FAILED`** on this tree, with exactly one suite red:
  `test_check_cluster_citations.py`, on two citations in
  `xdata-cluster-names-guard-off-recipe.md:220` that name clusters `0x0464` and
  `0x0465` are not members of. It is **pre-existing and unrelated** — it fails
  identically on a stashed tree, and `xdata_register_map.py --check` exits 0, so
  the census it checks against is current and the disagreement is in the prose.
  (`test_walk_budget_census.py` is named as red in the issue's own write-up; it
  is green here, 52 tests. Named rather than passed over, since a second claim
  in that direction would be the same error as the first.)
  *(Corrected at the merge: on the merged tree the runner reads **`38 suite(s)
  run, 1161 tests; one or more FAILED`**, and the red set is **two** suites
  rather than one. `test_check_cluster_citations.py` is unchanged — same case,
  same line, same message, and it reproduces identically on a clean `origin/main`
  at `24460001`. The second is `ec/tools/test_check_pin_table_by_cited_file.py`,
  which is **red on `origin/main` too**: two of its three failures are this
  merge's, because this issue's one new pin moved the first row of the
  by-cited-file breakdown and the concentration pair, and both were re-measured
  beside
  [`pin-table-by-cited-file.md`](pin-table-by-cited-file.md)'s transcript; the
  third is a `37`-indexed-suites pin that #944's
  `tools/test_doc_patch_refs.py` made stale on `main` before this merge was
  opened, and it is left red and named in the case's own comment rather than
  quietly re-measured from a merge that did not move it. The suite and test
  totals moved by #944's 22 cases and the suite with them, and **this issue
  changed no suite's case count** — the rename is a rename, which is why `30`
  above is the same number here.)*
- `ec/annotations/registers.yaml` is untouched. No register's status moved, and
  nothing here is a live register observation.
- Nothing was re-derived or renamed at the census level. The `main-ec-NNN` ranks
  are the ones the census has; this change makes the suite stop depending on
  which is which, and a prose sweep across the tree is a separate job.

## Pins

Editing the test file moved lines, and the pins the tree carries into it went
with them. `census_test_line_pins.py` reads 105 -> 106 records and 73 -> 74
resolves across the sweep, 0 out-of-range, unresolved and ambiguous before and
after, with `declined` held at 32. Both increments are this file's own single
pin, the `other` shape being what moved, 33 -> 34. 33 pin occurrences across 11
markdown files are repointed to the line each one named before — a statement
about the sweep's mechanics, not about the claim: whether a given pin carries
the figure it is cited for is a separate reading, and
[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md)
records one that does not. `check_doc_figure_pins.py --section 2b` still reads
18 figures, 18 held, 0 unheld — it resolves line numbers from the AST live, so
the `held`/`unheld` verdicts cannot move on a renumbering, and the transcript
in [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) is repointed to match
what the tool now prints.

`docs/findings/test-line-pin-census.md`'s per-pin table is **not** repointed
here. It is a dated record of one run, and the tool excludes it from its own
census precisely because a copy of the pins is not an independent use of them
(`census_test_line_pins.py`'s `SELF_MODULES` rule, applied to a document). Its
line column now lags the tree, which is the state a dated table is in.

*(Corrected at the merge with #942, and the reasoning above did not survive it.)
**#942 landed in the same window: `ec/tools/check_pin_table_rows.py` reconciles
that table's four mechanical columns against the census's own run, and a table
whose line column lags is what it reports as `unplaced-row` and
`read-differs` rather than as a dated record.** The exclusion above is untouched
and still right — the tool must not count the pins the table copies, or the
census would measure itself — but the consequence the paragraph drew from it does
not hold now that something reads the table against the run. **So the table was
re-derived on the merged tree rather than left to lag: the 33 target columns
above re-registered to the line each one names now, three citing lines
re-registered as this merge's own edits to the markdown moved them, one row added
for this file's own pin, and the result is 106 rows against 106 records, 106
placed and all seven classes 0.** *(The three citing lines are **six** on the
merged tree: a thirteen-line correction added beside this merge to
[`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) moved the three rows citing
*that* file by the same thirteen, and the table was re-derived again to follow.
The verdicts did not move either time — 33 re-registrations and three citing lines
by this merge, three more by the correction, and not one reading redone.)* What carried forward
is the half the tool does not read: each row keeps the verdict it was read with,
and the one row with no predecessor — this file's `:22`, the `--no-eq-guard`
recipe this section's own first paragraph cites, and the row
[`test-line-pin-census.md`](test-line-pin-census.md)'s per-pin table now
carries — was read here and **carries**. The 33 re-registrations needed no new
reading because
every one of them names the same line it named before: the census's own record
carries the cited line's text, and it is byte-for-byte identical on both sides of
every one of the 33. That is the strongest form of "a re-registration moves the
pin, not the claim", and it was available before the merge and is left unclaimed
on the branch that had no table to reconcile.*)
