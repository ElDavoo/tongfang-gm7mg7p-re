# What happened to every hand name: the carry report gets a name-indexed half (issue #881)

Issue [#881](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/881) was
opened by the follow-up pass off #872. It names an asymmetry left standing by
[#851](xdata-names-file-census-anchor.md): #851 split what a carry line
*advises* by census shape, and left what a carry report *covers* alone.
`carry_names()` iterates `for row in new_rows` and appends one record per **new
cluster**, so a hand name whose `cluster_key` is not a cluster of this run and
which no new cluster reaches at `CARRY_MIN_JACCARD` is in no record at all — and
in no cell of the tally either, because those five cells count clusters that
carried a name, which is not the number of rows in the names file.

**None of this is a live test, and none of it is evidence about the firmware.** No
EC is opened, no register is read back, no capture is taken, and no laptop, EC or
Windows machine is involved anywhere below. Every figure is arithmetic over
committed text and is re-derivable from the files this repository holds. No
register's `status:` moved; neither census CSV nor the names file was edited, and
`--check` is the proof rather than a claim about that.

## What the block looked like, on the four runs

Each row below is a run of the committed tool on this tree, each re-measured
after the change landed. The two scratch runs take `--out-*` paths because both
flags refuse to run without them.

```sh
python3 ec/tools/xdata_register_map.py --check
python3 ec/tools/xdata_register_map.py --no-eq-guard        --out-registers /tmp/n1-r.csv --out-clusters /tmp/n1-c.csv
python3 ec/tools/xdata_register_map.py --export-ownership   --out-registers /tmp/n2-r.csv --out-clusters /tmp/n2-c.csv
python3 ec/tools/xdata_register_map.py --threshold 0.6      --out-registers /tmp/n3-r.csv --out-clusters /tmp/n3-c.csv
```

| run | clusters | names in the file | distinct names in the written CSV |
|---|---|---|---|
| `--check` (the anchor) | 439 | 9 | 9 |
| `--no-eq-guard` | 445 | 9 | 9 |
| `--export-ownership` | 440 | 9 | **7** |
| `--threshold 0.6` | 631 | 9 | **5** |

The last two columns differing is the whole issue. On `--check` the tally's five
counters happen to add up to a run about nine names; on `--export-ownership` and
`--threshold 0.6` they do not, and nothing printed said so. A reader of those
runs could not distinguish "every name is accounted for" from "two names fell
under the floor" using only what the run printed.

The two names `--export-ownership` does not carry, with the best Jaccard this
method saw against any of its 440 clusters:

| name | key | best score |
|---|---|---|
| `counter-sweep` | `k733222e83898` | 0.48 |
| `countdown-06cd` | `k801a3e80698f` | 0.33 |

And the three `--threshold 0.6` reaches below the floor, against any of its 631
clusters: `mode-oem-init` (`kefb63d82f8c7`) at 0.33, `level-block-086x`
(`ka39cda99615f`) at 0.32, and `user-clear-bytes` (`k66512c56e77b`) at 0.33.
The fourth it does not write is the duplicate, below. Each of these scores is
re-derivable from the two committed CSVs with `jaccard()` over the two `addrs`
cells — the same derivation #872 used.

## The two halves, and why one record is not enough

`carry_names()` answers the question a **cluster** asks: *what name does this
cluster carry?* One record per new cluster. That is the right question for
deciding what to write into `xdata-clusters.csv`, and it is the wrong question
for deciding whether every hand name survived a re-clustering.

`xdata_name_coverage.coverage()` answers the other one: *what happened to this
name?* One record per row of `annotations/xdata-cluster-names.csv`, which is the
transpose of the other list rather than the same list seen twice — so a name can
appear in it and in no cluster's record at all, and that is precisely the case
that was invisible.

The record is `{name, key, how, jaccard, carried_to, detail, clusters}`. `how`
is the cluster-indexed vocabulary plus two, and the two additions are refusals
rather than new claims:

- **`duplicate`** — more than one new cluster reached this name. A tie between
  the claimants is carried to none, because which of them the name belongs to is a
  fact about the clustering and not a coin this rule flips; this is the mirror of
  the `tie` branch, which already refuses the opposite case. A **hand claim**
  (`seeded`/`exact`) wins outright and unequal scores pick the better cluster,
  because the refusal is for an undecidable case and not for a multi-claim as
  such. All of them is spelled in `resolve_duplicate()`.
- **`key-not-found`** — the names file's key is not a cluster of the committed
  census, so there is **no membership to score**. Reported as that, never as a
  score of `0.00`: a name with nothing to be compared against and a name
  compared against every cluster and matching none are different findings, and
  printing them the same way would make the first look like the second.

## The duplicate, worked through

`flag-pair-0442` (`kb07a0f522a7d`) is two addresses, `0x0442` and `0x0801`. Under
`--threshold 0.6` those two addresses split into two one-address clusters, and
each of the halves scores exactly 0.50 against the pair:

```
  0.5000  main-ec-317    ['0x0442']
  0.5000  main-ec-329    ['0x0801']
```

`names[key] = name` used to attach the name to **both**, so the written CSV held
seven named rows for six distinct names — one name, two rows, and the two rows
disagreeing about which cluster the pair is. The `tie` branch refuses to pick
between two names for one cluster; there was no guard on the symmetric case.

So `carry_names()` gained a second pass, after the per-cluster loop and before
anything is attached. **The first pass's scores are untouched** — only the
attachment moves. `xdata_name_coverage.duplicate_claims()` groups the records that
carry a name, `resolve_duplicate()` picks the survivor, and the losers keep
`name` in the record and take `how = "duplicate"`, so the report still says
which name was refused. The same `--threshold 0.6` run then holds five named rows
for five distinct names, and prints:

```
    flag-pair-0442 (kb07a0f522a7d) is claimed by 2 clusters at Jaccard 0.50 (main-ec-317, main-ec-329); carried to none, because the rule will not pick between them
```

The survivor is chosen in the order of what each rule is evidence of: a
`seeded`/`exact` record over any guess, because that is a human saying which
cluster a name is and this rule's arithmetic does not overrule the hand; then
the best score; then **neither** on a tie, because a tie between the claimants is
the same refusal as a tie between the named rows.

## The tally, and why it is two clauses and not two more counters

`print_carry()`'s tally counts records per outcome, so it is a count of clusters
that carried a name. It cannot be made to account for the names by widening it:
the two numbers are different quantities, and appending unconditional counters
would change the line every committed-shape transcript in the tree carries. #851
left that line byte-identical and this change keeps it that way.

**The tally prints what is there.** On the committed census every hand name is
`seeded`, so both additions are empty and the line is today's line, character for
character — which is why the two are *clauses*, appended only when non-zero:

```
, claimed by more than one cluster, not carried 1
, and 4 of the 9 names in annotations/xdata-cluster-names.csv are not carried by this method
```

The first clause counts a **refusal**, not a carry, and the wording has to say
so: `resolve_duplicate()` took the tie and carried the name to none of the
claimants, `print_coverage()` prints "carried to none" for it, and the written
CSV holds it on zero rows. A clause reading "carried to two clusters" would
contradict both — and the tally is the line a reader takes away from the block.
It says "more than one cluster" rather than a fixed count because
`duplicate_claims()` returns any name in more than one record, and this cell
sums across names whose claimant counts differ.

`print_carry()`'s `coverage` parameter is **required and has no default**. A
default a future caller forgets is the exact failure this signature exists to
prevent: a mode that printed the cluster half and silently left the names out is
how the two halves drifted apart in the first place.

## The wording

Every line either half prints says **not carried by this method**. None says a
name was lost, gone, absent, or dropped, for the reason the tool's module
docstring already gives: a function that stopped decompiling, a threshold that
moved, a guard that was removed and a cluster that stopped existing are four
different things, and this rule can only report that its own rule did not fire.

Three of the lines, verbatim from the runs above:

```
    counter-sweep (k733222e83898) is not carried by this run: best Jaccard 0.48 against any of the 440 clusters, under the 0.50 floor
    flag-pair-0442 (kb07a0f522a7d) is claimed by 2 clusters at Jaccard 0.50 (main-ec-317, main-ec-329); carried to none, because the rule will not pick between them
    level-block-086x (ka39cda99615f) is not carried by this run: best Jaccard 0.32 against any of the 631 clusters, under the 0.50 floor
```

The first is the distinction #851's `none` already promised to keep — "nothing
came close" is not the same as "nothing was even looked for", and the printed
score is what tells them apart.

There is a fourth line shape, for the case where the score *cleared* the floor
and the name is still on no cluster — the cluster it matched took a different
name. That line does **not** say "under the floor", which would be false there.
It also does not say what that cluster carries: a cluster that reached a `tie`
carries nothing at all, so naming another name would be a claim about a record
this half never read. It states only what is provable from the name's own side:

```
    <name> (<key>) is not carried by this run: best Jaccard 0.95 against main-ec-317, and this run carries it on none of them
```

## Where the tool is, and what the tree checks

- **`ec/tools/xdata_name_coverage.py`** (new) — the name-indexed half, a sibling
  of the tool the way `cluster_name_shape.py` is. It must **not** import
  `xdata_register_map`, because the tool imports it and that would be a cycle;
  `jaccard` is restated in three lines instead, and the docstring says why. Kept
  out of `xdata_register_map.py` itself, which is the file the
  `check_eq_guard_citations.py` anchors point into.
- **`ec/tools/test_xdata_name_coverage.py`** (new) — the suite. In-process on
  synthetic fixtures, plus one class that reads the two committed CSVs directly.
- **`ec/tools/xdata_register_map.py`** — `carry_names`' second pass and its
  docstring, `name_clusters` returning `(report, coverage)`, `generate`'s
  5-tuple, `print_carry`'s third parameter and its tally clause, the module
  docstring's outcome list, and the `--map` / `--self-test` call sites.
  `carry_names()` keeps its **2-tuple** return, so `xdata_guard_off_row_join.py`
  and the three `test_xdata_cluster_names.py` call sites are untouched.
- **`--self-test`** holds, beside the existing drop check, which stays where it
  is, that every row of the names file produces a coverage record, that no name
  is written to two clusters of this run, and that every `duplicate` record
  keeps the name it refused and names the clusters that claimed it. The
  existing drop check computes `old_names` from the *committed* census, so it is
  green precisely where nothing is lost; these are about this run's own report
  — and on the committed census they hold vacuously, because every hand name
  is `seeded` onto its own cluster and there is no duplicate to refuse. So the
  duplicate rule is driven once on a fixture, `flag-pair-0442`'s two addresses
  split into one cluster each, and the committed census's green is read as "no
  case here" rather than as "the rule holds".

## What adding lines to the tool cost, and what it was

`ec/tools/check_eq_guard_citations.py` holds the `--no-eq-guard` mechanism's own
line citations. Prose files cite line numbers inside `xdata_register_map.py` for
the flag, the two refusals and the classifier, and the checker resolves each
against the code it names. It was **green on the base commit** and this change
made it red, because the new code adds lines above those anchors and a `:NNN` is
a rank into a file that keeps growing.

That is the checker's own designed behaviour — it prints each anchor's current
line so the fix is one edit rather than a re-measurement — so the citations were
re-anchored to the lines the checker names. Nothing else in those sentences
changed: every edit is the number inside a citation of a named anchor, in
`docs/findings.md`, `ec/annotations/xdata-register-map.md` and two pages under
`docs/findings/`.

It is worth naming here because the shape is the one this repository argues
against elsewhere: these are `file:line` pins rather than the content-hashed
citations it prefers, so any change that grows the file above them costs an edit
here. The alternative — anchoring the code instead of the number — is a change
to the checker and the documents carrying those pins together
(`xdata-no-eq-guard-refusal-contract.md`, `xdata-register-map.md`,
`xdata-4-4-identity-rederivation.md`, `docs/findings.md`), and is its own
issue's work.

## What a reader should take from this

The census's own invariant, *every hand name survives a re-clustering as an
outcome*, is now stated over the run rather than over the committed census — and
on the committed shape it holds vacuously, which is the property that made it
worth saying out loud. The re-clustering runs are where it is load-bearing, and
on those the block now accounts for every name in the file.