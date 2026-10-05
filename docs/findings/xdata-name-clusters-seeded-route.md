# `name_clusters()` was reached by no case; the route production takes is now held (issue #959)

`ec/tools/xdata_register_map.py`'s `name_clusters()` fills `cluster_name` into
the generated cluster rows, and no suite ran it.
`ec/tools/test_xdata_name_clusters_route.py` does, over the committed census and
a guard-off regeneration, with `load_cluster_names()` as the seed — the route
`generate()` and `--self-test()` both take through it.

**`carry_names()` has other callers, and naming them is the point rather than a
detail.** It is called from three places outside a suite: `name_clusters()`
itself, the duplicate-rule drive *inside* `self_test()` — which builds a
synthetic split and calls `carry_names()` directly rather than through
`name_clusters()` — and `xdata_guard_off_row_join.py`'s `names_report()`. This
suite covers the first, because it is the only one whose result is filled into
`cluster_name` and written into `xdata-clusters.csv`. The other two read the
rule without a fill reaching the census: `self_test()`'s drive checks the
outcome list of a fixture it built, and `names_report()` binds the name map to
`_names` and keeps only the report.

**Nothing here is a live observation.** Every figure below is a function of the
two committed census CSVs and of the committed tool run over the committed
decompiled C. No hardware, no Windows, no image, no Ghidra. The census CSVs are
inputs and this change touches neither: `--no-eq-guard` is refused against the
committed output paths, so every run in the new suite writes to a scratch
directory.

## The gap, and why the three nearest suites did not close it

| suite | what it holds | what it does not reach |
|---|---|---|
| `TheCarry` | `carry_names()` on hand-built fixtures, so the `seeded` *precedence* is held against `exact` | against a key the fixture chose, over the committed census |
| `TheNamesFile` | every names-file key is a cluster of the committed census | it reads the two files and never runs the function that joins them |
| `TheGeneratorsAreUnchanged` | the regeneration is reproducible cell for cell | it excludes `cluster_name` **by name**, beside `cluster_key` |
| `TheGuardOffRegeneration` | the overlap carry, derived from the tool's own report | it passes `{}` as the seed, and no caller outside a suite does |

The third row is the sharp one. Excluding the identity columns from a
reproducibility comparison is correct for what that case is about, and it is
also why nothing caught a fill that puts the right name on the wrong row.

The fourth row is not a gap in it. `{}` is deliberate and its comment says why —
the case is about the route a key-only design would fail, so withholding the
names file is what makes the assertion mean anything. The consequence is
coverage, not error.

## The two routes, and what the run decides

`carry_names()` reaches the same names two ways. A key the names file anchors
is `seeded`; the same key found in a named row of the committed census is
`exact`. `generate()` and `--self-test()` both pass `load_cluster_names()`, so
`seeded` is what a real run reports. Run over the same pair:

```console
$ python3 - <<'PY'
import collections, csv, importlib.util, os, subprocess, sys, tempfile
spec = importlib.util.spec_from_file_location(
    "xrm", "ec/tools/xdata_register_map.py")
xrm = importlib.util.module_from_spec(spec); spec.loader.exec_module(xrm)
tmp = tempfile.mkdtemp(); oc = os.path.join(tmp, "c.csv")
subprocess.run([sys.executable, "ec/tools/xdata_register_map.py",
                "--no-eq-guard", "--out-clusters", oc,
                "--out-registers", os.path.join(tmp, "r.csv")], check=True)
rows = lambda p: list(csv.DictReader(open(p, newline="")))
committed, off = rows("ec/annotations/xdata-clusters.csv"), rows(oc)
for what, seed in (("withheld", {}), ("seeded", xrm.load_cluster_names())):
    fresh = [dict(r) for r in off]
    report, cov = xrm.name_clusters(fresh, committed, seed)
    print(what, dict(collections.Counter(r["how"] for r in report)),
          "coverage records:", len(cov))
    for r in report:
        if r["how"] == "overlap":
            print("   overlap:", r["name"], r["cluster_id"], r["from_key"],
                  "->", r["cluster_key"], f"{r['jaccard']:.4f}")
PY
withheld {'none': 436, 'exact': 8, 'overlap': 1} coverage records: 0
   overlap: mode-oem-init main-ec-0456 kefb63d82f8c7 -> kc0f2a0be0103 0.9681
seeded {'none': 436, 'seeded': 8, 'overlap': 1} coverage records: 9
   overlap: mode-oem-init main-ec-0456 kefb63d82f8c7 -> kc0f2a0be0103 0.9681
```

**The coverage half exists only on the seeded route, and that is not incidental.**
`coverage()` returns one record per row of the **names file**, so a run seeded
with `{}` returns none at all — the withheld route's nine names are carried into
rows of the CSV, and no record accounts for any of them as a *name*. That is
`xdata_name_coverage.py`'s reason for existing in one line, and it is also why
the coverage case below could not be written against the withheld route at all.

**The two fill the same names on the same rows and differ only in the label.**
Every `exact` becomes a `seeded` and nothing else moves: the `none` and `overlap`
records are the same records either way, and the `cluster_name` column each route
writes is identical — including on the rows the other route reaches by a
different key. That is the design property `name_clusters()`'s docstring states,
that `seeded` and `exact` are *the same claim arrived at differently*, and it is
a property of the design rather than of this tree, which is why it is the thing
asserted.

**Every key the names file anchors lands on the row the names file names.** The
last clause of the suite's `seeded_records()` is the one the tree had no way to
state: the committed census's row of that key carries that name. A names-file
key belonging to some *other* row satisfies `TheNamesFile`'s check — the key is
in the census — and fails here.

**The one name the key cannot find arrives by overlap**, under both routes, and
the coverage record for it carries that Jaccard rather than the `None` a
genuinely unfindable key would. Its exhibit is derived — the names-file keys
absent from the regeneration, each of which must arrive — so no id, key or
score is typed anywhere. `mode-oem-init`'s key now reads
`kefb63d82f8c7`, the third it has carried and the second re-key, and the row's
own note records each move for a re-derivation that changed the membership; a
typed pair would have gone stale silently, and #279's pair-accessor pass is what
that happened to last.

## A correction to the issue's proposal

The issue asks the new case to assert `from_key == cluster_key` for seeded
records. It does not hold. In `carry_names()` the `seeded` branch assigns `name`
and `how` and leaves `from_key` at its `""` initial; only the `exact` branch
assigns `from_key = key`. Measured, every seeded record on this tree carries
`from_key == ""`.

The case asserts that instead. It is the branch's own shape, and it is what
distinguishes a seeded record from an exact one at the record level — which
matters here precisely because the two routes agree on the row and differ only
in the label, so the record fields are the only place the difference shows.
Writing the assertion the issue proposed would have meant changing
`carry_names()` to populate `from_key` on that branch, which is a report-shape
change reaching every transcript carrying a `seeded … from` line: a design call
about what the report claims, not a missing test. The case holds the shape as it
stands.

## The negative control, and the check it is aimed at

A names-file row re-keyed onto a different cluster's key. `TheNamesFile` reads
the two files and asks whether each key is a cluster of the census, and the
forged key **is** one, so that case stays green — a check that passes on a name
attached to the wrong row is worse than no check, because it is read as the row
being right. Three claims here catch it instead:

- the fill moves between the two routes, so a seed is sensitive to which key the
  names file anchors;
- the anchor clause refuses the seeded record, naming the different name the
  committed census gives that key;
- the transpose reports the name landing on **two** rows. The forged map leaves
  it on the key it moved off, which still resolves `exact` in the committed
  census, *and* on the key it moved onto, now `seeded`. `resolve_duplicate()`'s
  first rule keeps both, because both claims are by key and neither is the
  tool's guess — so the coverage list names one `carried_to` where the report
  holds two carried records.

Each of those three was checked by removing it and watching the control stop
failing, and the suite was checked against a tool with the `seeded` branch
disabled and against one whose fill was broken. A hold case that has never gone
red has never been shown capable of it.

## The choice: sit beside, do not replace

The `{}` route stays. It is what the restatement is about and its comment says so
explicitly; replacing it would delete the case the restatement exists for, and
with it the derived exhibits the restated case is the record of. The seeded route
is what every caller outside a suite runs and was uncovered — no caller outside
one passes an empty seed at all, so the `{}` route is reached only from suites.
Both are correct and disagreeing by construction is the design — which is only
assertable while both exist, and is what
`test_the_two_routes_differ_only_where_the_names_file_anchors` holds.

## What this does not claim

- **No figure of the census is held.** Nothing in the new suite asserts a row
  count, a name count or a `how`-tally figure; every claim is a set relation or
  a per-record property, so a re-derivation moves the assertion rather than
  reddening it. The figures above are what this tree gave, beside the command
  that produced them.
- **`test_xdata_cluster_names.py` is untouched.** A new suite file rather than a
  case appended to it: that file carries prose pins into its line numbers, and
  its own `TheNamesShape` docstring records that any line added above an
  existing class moves them. The restated case keeps deriving its own exhibits
  and the pinned lines stay where they are.
- **The suite is not wired into `.github/scripts/agent-gates.sh`,** so none of
  this is enforced in CI. The runner reaches it through `bash
  tools/run-tests.sh`, which discovers by `find`; wiring the XDATA suites into
  the gate is #162's, by way of #773's prepared-patch route, and the push token
  has no `workflow` scope.
- **`ec/annotations/registers.yaml` is untouched.** No register's status moved,
  and nothing here is a live register observation.
- **Nothing was re-derived or renamed at the census level.**
  `xdata-clusters.csv` and `xdata-registers.csv` are inputs, and
  `xdata_register_map.py --check` still exits 0.
- **A static comparison over committed text is not a live observation.** Every
  claim above is reproducible from the committed CSVs by the command shown, and
  none of it says anything about how the EC behaves.