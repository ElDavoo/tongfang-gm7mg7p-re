# A dated claim whose file set has no `addr` column is not checked, and `with_column()` counts columns rather than extensions (issue #990)

The write-up for [issue
#990](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/990), which is
about a **corpus state the committed index does not happen to contain**: a
dated claim, held to the captures its bare date resolves to, where that file
set has no `addr` column to read the claim in. #975 gave the columnar read an
owner and left the owner without an answer for this state. A date resolving to
`ecrw.py dump` output came out `missing` — which asserts the index is wrong,
and on a dump that carries the address in its text the assertion is false —
and a date resolving to a `.csv` whose header names no column came out
`missing` too, *and* printed `1 with an addr column` beside the file count,
because the count was reading file extensions and never opened anything.

What this branch adds is **a decision, one entry of the closed shape list, five
cases and two corrections in place**. The count reads columns, "has a column"
has one definition rather than two, and a dated claim with nothing to ask is
`unresolved` with a reason a reader can see, where before it was an accidental
`missing`.

**Nothing here is a live test, and no capture is opened for anything but a
header.** It is a parser decision over committed text, the same class of claim
as both sibling write-ups: no EC, no firmware image, no laptop. **No row of
`ec/tools/testdata/README.md` is edited, in either column** — the index is not
edited to make a tool green, and this issue's own condition forbids it besides.
The one line that changes in that file is the prose paragraph *below* the
table, which enumerated the tool's dated refusals and would otherwise name two
of three.

## The census, measured on this tree, 2026-09-29

The question the issue could not answer — how many dated file sets are in this
state — is a count of headers, so it is measured over the same predicate the
tool now uses rather than over a second reading of the same directory:

```
$ python3 -c "
import csv, os, sys; sys.path.insert(0, 'ec/tools')
import check_capture_claims as ccc
names = sorted(os.listdir('evidence/ec-watch'))
csv = [n for n in names if n.endswith('.csv')]
print(len(names), 'files,', len(csv), '.csv,', len(names) - len(csv), '.txt')
for n in csv:
    print(' ', 'addr column' if ccc.has_addr_column('evidence/ec-watch/' + n)
          else 'NO addr column', n)
"
15 files, 10 .csv, 5 .txt
  addr column 2026-09-18-ac-plugin-sweep-summary.csv
  addr column 2026-09-18-profile-switch-0400-07ff.csv
  addr column 2026-09-18-profile-switch-0700-07ff.csv
  addr column 2026-09-23-power-mode-cycle-0700-07ff.csv
  addr column 2026-09-23-power-mode-cycle-0f00-0f5f.csv
  addr column 2026-09-24-06c2-06db-perturb-linux.csv
  addr column 2026-09-24-06c2-06db-suspend-linux.csv
  addr column 2026-09-24-06c2-06db-sweep-linux.csv
  addr column 2026-09-24-06d6-reload-linux.csv
  addr column 2026-09-24-06d9-hold-linux.csv
```

**Every one of the ten carries an `addr` header.** Nine are the
`ts,addr,old,new` change log; the AC-plugin sweep summary is the derived
per-address shape, `addr,change_count,first_old,last_new` — which is why
`read_capture()` knows about `change_count` at all, and why the column is the
right thing to ask for even there. Per date: `2026-09-23-*` is six files of
which two are `.csv` and `2026-09-24-*` is six of five.

So the third state has **no instance in the committed corpus**, and what pins
it is scratch cases. That is the same position
[`testdata-row-claims-multi-date-sentence.md`](testdata-row-claims-multi-date-sentence.md)
took for the multi-date refusal, and it is why the new entry joins
`DATED_REFUSALS` rather than the run: `check_every_shape()`'s two-direction
comparison is satisfied by a reason with no instance, and is *broken* by one
that appears without being named.

## The decision

**One condition, two reds:** a dated claim whose file set has no `addr` column
is not checked. `ecrw.py dump` output alone and a columnless `.csv` are the
same answer to the same question, so expressing it as one condition is what
keeps the two from drifting apart the way two branches would.

| state of the date's file set | before | after |
|---|---|---|
| at least one file with an `addr` column | columnar read, `resolved`/`missing` | **unchanged** |
| `ecrw.py dump` output alone | `missing` | `unresolved`, reason `dated capture has no addr column` |
| `.csv` files, none with an `addr` column | `missing`, and the block printed `1 with an addr column` | `unresolved`, and the block prints `0 with an addr column` |

**Why `unresolved` and not `missing`.** `missing` asserts the index is wrong.
On a dump that genuinely carries the address in its text that assertion is
false — the tool did not disagree with the index, it had no way to ask. It is
the vocabulary `check_testdata_index.py` already established and this tool
already prints: "not checked, not absent", counted in the shapes line, and
`report()` still returning 0. The consequence worth stating is that the
disagreement sentence in `report()` needs no second phrasing: a claim that was
never read is not a disagreement, and it never reaches that line.

**Why a `SHAPES` entry and not only a file-count fact.** `with_column()`'s
docstring argued — correctly, and the argument is kept — that the columnless
state is "a fact about the *file set* rather than about any literal's
spelling, so it is reported in the dated block beside the file count rather
than added to the closed `SHAPES` list". That is right about the **count
clause**, which stays and now reads a real number, and silent about the
**verdict**, which is what the issue asked about. A claim that is not checked
needs a `reason` string; `Claim.reason` is the only field `report()` prints
for one; and a reason that reached `claims` but not `shapes` would trip
`check_every_shape()` in the other direction. So the count clause and the
shape entry are two facts about the same state, and both are now here.

**Why "has a column" is one definition.** Before this, `with_column()` tested
`path.endswith(".csv")` and `carried_by_column()` tested
`read_capture(path)[0].get(address)`. They agreed on the corpus by luck and
disagreed on a `ts,note` log: one counted it, the other read it and found
nothing. Both now go through `check_capture_claims.has_addr_column()`, which
asks the file. That is a de-duplication rather than a behaviour change — a set
with no column never reaches the columnar read as a claim, and a mixed set
still reads its columned members — and it is why the figure on the block and
the set the reader walks cannot come to disagree.

## The count, and what it costs to read

`with_column()` was a `sum()`; it opens a file now, once per member of the set.
Measured on this branch over the committed run, by counting calls into the
sibling's `capture_lines()`:

```
28 header reads, over the 6 distinct files of the one dated block
  4  2026-09-23-0751-isolation.txt
  4  2026-09-23-ctgp-live.txt
  6  2026-09-23-power-mode-cycle-0700-07ff.csv
  6  2026-09-23-power-mode-cycle-0f00-0f5f.csv
  4  2026-09-23-power-mode-cycle-0f00-final.txt
  4  2026-09-23-power-mode-snapshot-dc.txt
```

The plan this was built from priced it at *one read per `.csv` member*, on the
assumption that both readers keep an extension pre-filter. **They do not, and
that is deliberate**: a pre-filter in one and not the other is the two
definitions of "has a column" this section exists to remove, and a file that
counted as columnless on the block while being read as a carrier in the claim
would be a worse state than the extra reads. The figure above is therefore the
cost, measured, and it is small against a corpus the textual reader already
opens whole — `carried_by()`'s docstring prices that one the same way.

**A file that cannot be decoded is left to raise**, exactly as
`carried_by_column()` did. Guarding it into a silent `False` would be the
worse of the two errors: a loud failure at one file would become a quiet "this
capture has no column" printed beside a claim that was then never read.

## The precedence, and what holds it

**A sentence's own shape still wins over the file set's.** The helper is
called only where `reason_for()` returned `None`, so a page-aligned bound the
sentence calls a capture is a page whatever the date resolved to. This is the
precedence `reason_for()`'s own docstring argues for the multi-date refusal,
and **no existing case held it**: every shape case in the suite is undated, so
`about_capture` is false and the new reason is unreachable in all of them.
`test_a_dated_shape_still_wins_over_the_no_column_refusal` is the case that
holds it, and without it the ordering is a sentence in a docstring that could
invert silently.

The cases are these, in `TheDatedClaimIsHeldToTheColumn`, and no existing case
is weakened:

- `test_a_txt_only_date_reports_that_it_has_no_column_to_read`, **extended in
  place** — it already built the state and asserted the two printed clauses.
  It now also holds the verdict, `report()`'s return, and both halves of the
  stderr line.
- `test_a_csv_with_no_addr_column_leaves_the_dated_claim_not_checked` — the
  same verdict the other way, held **on the number** as well, since the number
  is what a reader of the block takes away.
- `test_a_columnless_csv_beside_one_with_the_column_does_not_refuse_the_claim`
  — the control, and what makes the pair above unfalsifiable by a blunt rule: a
  set with a columnless member *and* a columned one is still read.
- `test_the_no_column_refusal_is_load_bearing_rather_than_asserted_to_be` —
  the suite's drop-it-in-turn form, patched at the **shared predicate** so one
  patch reaches both consumers, and asserting the verdict flips.
- `test_a_dated_shape_still_wins_over_the_no_column_refusal` — the precedence
  above.

Each was checked against the behaviour it replaces rather than assumed to
matter: removing the refusal fails three of them, restoring the extension count
fails three, and answering "every file has the column" fails four. The control
fails under both wrong implementations, which is the property it is there for.

## Not found by this method

**The committed corpus contains no instance of this state, and that is a fact
about this tree rather than about the tool.** The census above is a count of
headers in one directory as it stands today; nothing in it shows that a later
edit cannot add a dated sentence over a columnless set. The same caveat
`ec/annotations/registers.yaml` carries for a static scan applies here, in the
same words: *not found by this method*, never *cannot happen*. What keeps the
state from being a silent hole is that it is a counted refusal with a stated
reason rather than a code path nobody exercises.

## The limits

- **Whether a `.txt` dump's text would have satisfied the claim is not
  answered, and is not answerable by this tool.** It would be the textual read,
  the sibling's question for fixtures, and re-introducing it for captures is
  the rule #975 removed. The claim is **not checked**, which is not the same
  sentence as **satisfied**.
- **The date's file set is still the whole date.** Narrowing it, or reading the
  prose to tell the date's files apart, is declined here for the reason it was
  declined in
  [`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md).
- **The wording of the dated block's lines is not touched.** That is #974's.
  This moves one *number* inside one existing clause and adds no line and no
  phrasing.
- **Nothing in the index, in a fixture or in a capture is repaired.** Nothing
  was wrong; the run was reporting one state as another.

## One named, deliberate staleness

`docs/ci/agent-gates-testdata-row-claims.patch` carries a comment saying "Two
of those entries are dated refusals, a capture named in prose that resolves to
nothing and a sentence naming two of them", which is **three** after this
change. The patch is left byte-identical: it is a prepared gate change a human
lands later, the CLI is unchanged, nothing executes it, and editing a file
nothing runs is one more conflict surface for no gain. **The sentence is named
here so the human landing that gate updates it then** — recorded rather than
hidden, which is the point of writing it down at all.

## What the run prints, before and after

The invariant held is the run's own output, diffed on the branch, not a figure
quoted anywhere else — the issue's own "done looks like" line is stale against
this tree and was not used:

```
$ python3 ec/tools/check_testdata_row_claims.py --check > before.txt   # pre-change
$ python3 ec/tools/check_testdata_row_claims.py --check > after.txt    # this branch
$ diff before.txt after.txt
2c2
< ... 25 passed over under the five shapes and the two dated refusals, ...
> ... 25 passed over under the five shapes and the three dated refusals, ...
```

**Exactly one line moves, and it is derived**: `shape_label()` prints
`len(SHAPES) - len(DATED_REFUSALS)` non-dated shapes, so adding a reason to
both tuples leaves the shape count alone and moves only the refusal count. The
tallies line, the `2026-09-23-*` block and the closing line are byte-identical
in both, stderr is byte-identical, and the exit is 0 either way. A second
moving line would mean the new reason had found an instance in the committed
index, and this section's "not found by this method" would be wrong.
