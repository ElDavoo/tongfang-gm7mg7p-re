# Which process wrote this mark: a fifth column measured against a `# provenance` row (issue #719)

The write-up for [issue
#719](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/719), which asks
for the measurement and not the change. #548 named the ceiling three times and
was right each time: `warn_unchecked_marks`
(`windows/tools/ec_watch.py:288`) says a run "did not check those marks and
cannot: it did not write them", and nothing in a capture file says which
process wrote which mark. The writing process knows its own `sys.argv`, so the
file *could* carry that. Whether it should is a question about the format, and
this page answers it with `ec/tools/measure_mark_provenance.py` rather than
with an argument about what a CSV ought to look like.

**Nothing in this repository changes.** No reader, no writer, no notice, no
`status:` in `ec/annotations/registers.yaml`. The two new files are a
measurement tool and this page. The recommendation at the end is for the next
issue to implement, not for this one to have implemented.

Every figure below is the tool's output, quoted. Re-derive it with:

```console
python3 ec/tools/measure_mark_provenance.py            # the tables
python3 ec/tools/measure_mark_provenance.py --self-test  # the same run, checked
```

Offline throughout: no EC, no capture, no driver, no §3 block. Section 2 is a
count over two committed directories and section 3 is a reader's behaviour on a
temp file. Neither is a statement about the machine.

---

## The issue's read-side premise, and a correction to it

The issue says a five-column row is backward-compatible on the read side
because it "passes `len(row) < 4` at `:690` and `row[0..3]` unpacks". The first
half is right and the second is not what the code does. Four lines, and the
first is the rule rather than a use of it (`ec/tools/grade_0751_isolation.py`):

| line | reads |
|---|---|
| `:845` | `return not row or row[0].startswith("#") or row[0] == "ts"` |
| `:890` | `if skippable_row(row):` |
| `:1042` | `if len(row) < 4:` |
| `:1044` | `ts, addr, old, new = row[0], row[1], row[2], row[3]` |

`:845` is `skippable_row`'s own body, the one place the skip rule is written
down (#750). `:890` is `read_capture` at `:852` calling it, and `:1042` and
`:1044` are `take_capture_row`'s at `:1015`, the loop body `read_capture` hands
every row the rule lets past (#749). That extraction is #749's and the
consolidation is #750's; nothing about the shape is different, the row is read
by the same code in the same order.

`:1044` is explicit indexing of the first four fields, not an unpack of `row`.
A fifth column is therefore **ignored** — `Window` is constructed from `new`,
which is `row[3]` — where the issue's reading predicts a `ValueError`. The
conclusion the issue draws is the same and the reason is the opposite, so the
reasons are worth getting right: a shape that would have raised on the next
field is a shape that can be extended a field at a time, and one that raises
is a format change every existing reader has to be reopened for.

`:1042` is a real test in the other direction, and the tool's self-test asserts
it: a *three*-column mark row still raises `ValueError`. The first version of
that assertion wrote `MARK,,x`, which is four columns, and the self-test failed
by passing for the wrong reason. A threshold that had stopped testing anything
would have been the more expensive version of that bug.

Above the table, `read_capture` refuses a byte-order mark
before it reads a row (`ec/tools/grade_0751_isolation.py:886`), and it is here
because of the same question the table is about. `skippable_row`'s `ts` test at
`:845` is what tells a header from a data row, and `EF BB BF` at offset 0
decodes under the declared `utf-8` to a U+FEFF that glues itself to the first
field: without that refusal the header would be a data row, `parse_ts` could
not read it, and the notice would name the row carrying the column names as a
row whose timestamp nobody can parse. The declared codec is #748's decision
([the encoding page](0751-capture-encoding.md)); the shape retires the mark
for the three readers that still have to read such a file, and the strict
reader refuses it by name ([the row-shape
page](0751-capture-row-shape.md)). Either way the header is not a data row,
which is the only fact this table's row count depends on.

## The row's census

Seven writers and eight sites carrying the literal, from scanning for the
`"MARK"` literal rather than off a list — so a writer spelled the way these
seven are is in tomorrow's census rather than a row of a list someone
remembered to update:

```console
   7 writer(s) of ts,MARK,,label:
     ec/tools/ec_timer_capture.py:169  sink.row([ts, "MARK", "", label])
     ec/tools/ec_timer_capture.py:204  sink.row([now(), "MARK", "", label])
     ec/tools/ec_timer_capture.py:210  sink.row([now(), "MARK", "", label])
     ec/tools/ec_timer_capture.py:232  sink.row([now(), "MARK", "", label])
     windows/tools/ec_watch.py:473  self._sink.row([ts, "MARK", "", label])
     windows/tools/manual_fan_ctrl_probe.py:443  self.row([now() if ts is None else ts, "MARK", "", label])
     windows/tools/system_id_probe.py:261  self._sink.row([ts, "MARK", "", label])
   8 site(s) consuming it:
     ec/tools/check_capture_encoding.py:166  if len(row) > 1 and row[1] == "MARK":
     ec/tools/check_capture_encoding.py:243  row = ["2026-01-01T12:00:00.000+01:00", "MARK", "", PROBE]
     ec/tools/grade_0751_isolation.py:976  `addr == "MARK"` before the `int()` calls, and so does this. That test
     ec/tools/grade_0751_isolation.py:1045  if addr == "MARK":
     ec/tools/grade_0751_isolation.py:1067  if len(row) > 1 and row[1] == "MARK":
     ec/tools/grade_0751_isolation.py:1099  if addr == "MARK":
     ec/tools/grade_timer_sweep.py:138  if r[1] == "MARK":
     windows/tools/test_manual_fan_ctrl_probe.py:508  if len(r) == 4 and r[1] == "MARK"]
   6 call(s) of the grader's readers, none of which writes the literal:
     ec/tools/check_capture_claims.py:514  index[WATCH + "/" + name] = read_capture(os.path.join(REPO, WATCH, name))
     ec/tools/grade_0751_isolation.py:2968  m, c = read_capture(path)
     ec/tools/grade_0751_isolation.py:2977  rows = read_early_exits(path)
     ec/tools/grade_gpu_door.py:421  m, c = fan.read_capture(path)
     windows/tools/manual_fan_ctrl_probe.py:701  marks, changes = grader.read_capture(str(path))
     windows/tools/manual_fan_ctrl_probe.py:707  void_marks, void_changes = grader.read_capture(str(void_path))
   48 further call(s) inside `test_*.py` suites, counted and not listed.
```

Six of the eight decide a row rather than describing one, and one of those six
(`:1099`) is a second decision inside the grader, in the partition
`partition_capture_rows` — it has to make the same call `read_capture` makes or
it would accept a row the grading refuses. The seventh, `:976`, is prose: the
partition's docstring quoting that branch, which the scan matches because it
spells the same literal in a sentence. The eighth is neither: a *constructed*
row, at `check_capture_encoding.py:243`, which the scan files as a consumer only
because the `.row(` that writes it is on the next line — so the census counts
eight and the tree has six decisions, one quotation and one test input. The scan
cannot tell those apart, so the table counts what it finds and this paragraph
says which is which.

The two `check_capture_encoding.py` rows arrived with #748, which declared the
capture format `utf-8` at every reader and writer ([the encoding
page](0751-capture-encoding.md)). Its mark/change census at `:166` is a reader
over the same shape, written by a second tool rather than by the grader, which
makes it the sixth of the six decision sites above and one this page's original
four-site list did not have. It is listed under "Five sites the issue does not
name" below.

**A second scan, because the first one has a blind side.** A consumer that
never decides whether a row *is* a mark never writes the literal, so the scan
above cannot see it. Six call sites of the grader's readers do not:

```console
   6 call(s) of the grader's readers, none of which writes the literal:
     ec/tools/check_capture_claims.py:514  index[WATCH + "/" + name] = read_capture(os.path.join(REPO, WATCH, name))
     ec/tools/grade_0751_isolation.py:2968  m, c = read_capture(path)
     ec/tools/grade_0751_isolation.py:2977  rows = read_early_exits(path)
     ec/tools/grade_gpu_door.py:421  m, c = fan.read_capture(path)
     windows/tools/manual_fan_ctrl_probe.py:701  marks, changes = grader.read_capture(str(path))
     windows/tools/manual_fan_ctrl_probe.py:707  void_marks, void_changes = grader.read_capture(str(void_path))
   48 further call(s) inside `test_*.py` suites, counted and not listed.
```

> **The figures above moved, and the reasons are four different changes.** The
> four decision sites and six call sites this section was written against grew
> to six and stayed at six when issue #718 added `refused_capture_rows` and
> `existing_mark_findings` (#729), which between them branch on `"MARK"` and
> call two of the grader's readers. Issue #749 then took three of those calls
> out again — one `open()` of a capture and one row list feeding the strict
> rules, the label extraction and the partition, so `existing_mark_findings`
> calls none of the three a second time — which is why the site count held at
> six while the call count fell back to six. Issue #748 then added
> `check_capture_encoding.py`, whose own `count()` skips MARK rows the way
> `read_capture` does and whose writer round-trip writes one, so the site count
> is eight while the writer count is unchanged. Issue #750 then moved the
> grader's own sites again without adding or removing any: it stated the skip
> rule and the first field once (`skippable_row`, `normalised_rows`) and took
> the byte-order-mark refusal out of the row body into the file, so the same
> six decisions sit at six lines rather than four. The `test_*.py` count moved
> twice, because #749's and #750's cases both call the readers. Re-run the tool
> rather than trusting this paragraph: it is a quotation, and a quotation rots.
>
> `windows/tools/ec_watch.py:355` and `:254`/`:280` are cited by the tool and
> are **DRIFT against this tree** — #718's insertions moved them, #748's
> `encoding="utf-8"` moved them again, and nothing here retargets them. The
> same is true of the pins in `ec_timer_capture.py`, `grade_timer_sweep.py`,
> `check_capture_claims.py`, `manual_fan_ctrl_probe.py`, `system_id_probe.py`
> and `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`: they are
> recorded rather than quietly fixed because they are not this change's to
> move, and because a pin that is corrected in passing is a pin whose history
> cannot be read. #748 recorded the same split from its side, and this page
> re-measures the grader's own pins — the ones #749 does own — rather than
> either side's number.
>
> **Correction (2026-09-25, issue #750), leaving the paragraph above as it was
> taken.** The verdict has moved, and #750 is what moved it: #748 never
> retargeted these pins, and all 18 of them read `DRIFT` on `origin/main` after
> it merged. #750's change to the grader moved the `grade_0751_isolation.py`
> lines, which is why re-anchoring the whole table fell to this branch; the
> fifteen pins in the other capture files were drifted by #748 and #749 and are
> re-anchored here too. They all read `ok` on this tree, and the section-5
> transcript below is the evidence. What is left of #748's caution is the rule
> rather than the verdict: a pin in a file this page does not change is
> recorded rather than quietly fixed in passing, because a pin corrected as a
> side effect is a pin whose history cannot be read.

The two scans have opposite blind sides and neither is the whole tree: the
literal scan cannot see a consumer that only counts, and the call scan cannot
see a reader that opened the CSV itself. That is the argument for running both
rather than trusting a hand-assembled list, and it is how the four sites below
were found — none of which the issue names.

**The literal scan has a second blind side, and this tree already shows it.**
It matches the double-quoted `"MARK"` the seven above spell the row with, so a
line quoting it the other way is invisible to it. The two such lines are
`windows/tools/test_ec_watch.py:145` and
`windows/tools/test_system_id_probe.py:311`, both `assertEqual` comparisons in
test suites. Neither constructs a row, so seven is the right count — but that is
a reading of those two files rather than a result of the scan, and a writer
spelling the row `'MARK'` would not be counted. The anti-staleness is enforced
from the other end instead, and §"What the tool checks" below says how: the
citation check's two-way join fails on a scanned site this page does not name,
so a writer the scan *does* find cannot drop out unnoticed either.

## Five sites the issue does not name

The issue names two other writers and readers: `manual_fan_ctrl_probe.py` and
`grade_gpu_door.py:421`. Measuring against the scan rather than against that
list is what turned up the four below that predate this page's second run, and
all five are in scope for a change to the row's shape.

1. **`windows/tools/system_id_probe.py:261` — a third writer**, from a `Marker`
   class of its own. It imports no `ec_watch.Marker`, and it still carries the
   `strip() or f"mark {self._n}"` default that #483/#484 track as open. Shape A
   as the issue scopes it — `Marker._loop` in `ec_watch.py` — would not reach
   it. That is a decision the implementation issue has to make deliberately,
   not one this measurement makes by omission.
2. **`ec/tools/ec_timer_capture.py:169`, `:204`, `:210`, `:232` — a fourth
   writer at four sites.** The rows are the same shape in files the 0751 grader
   would also open, and `grade_timer_sweep.py:138` reads them under a different
   label convention (`resumed` at `:139`, not §3's forms). The row shape is
   genuinely shared across two procedures, which is the strongest argument
   there is for measuring before changing it.
3. **`windows/tools/test_manual_fan_ctrl_probe.py:508` and `:515` — the
   canary.** `mark_rows` is `if len(r) == 4 and r[1] == "MARK"` and
   `:515` asserts `self.assertEqual(len(row), 4, row)` over every row of the
   probe's own capture. This is the only place in the tree that asserts an
   exact column count, so it is the one committed test a fifth column would
   actually fail — *if it ever reached the probe*. Under this issue's scope it
   does not, and that zero is the finding: these two lines are what fires if a
   later issue widens the shape to the probe, and a reader looking for where
   that would show up should look here first.
4. **`ec/tools/check_capture_claims.py:514` — a fifth consumer**, and the only
   one that opens *every* committed capture in `evidence/ec-watch/` through
   `read_capture`. It is a checker for the prose, so a committed capture that
   grew a column is something it would read rather than refuse — but it means
   the fixture set is not inert to a format change, only unchanged by it.
5. **`ec/tools/check_capture_encoding.py:166` — a sixth consumer, and the
   newest of them.** #748's tool counts marks against changes with its own
   `if len(row) > 1 and row[1] == "MARK"`, in a file of its own, over the
   captures it is checking the codec of. It indexes rather than unpacks, so a
   fifth column costs it nothing, and it carries the same declared `utf-8` as
   every other reader — but it is a second implementation of "is this row a
   mark" outside the grader, and a shape change has to reach it deliberately
   rather than by inheritance. Its constructed row at `:243` is the test input
   it hands a writer that takes a label alone, not a writer of its own.

## The committed fixtures

```console
   50 file(s), 247 MARK row(s), column counts [4]; header present in 50, `#` rows present in 44
     ec/tools/testdata: 48 file(s), 239 MARK row(s)
     evidence/ec-watch: 2 file(s), 8 MARK row(s)
```

Counted by this method over those two committed directories. That is the whole
of what the sentence claims: a capture taken at the machine and not committed is
not in it, and "0 fixtures untouched" is a count over a directory, never a
census of every capture that exists anywhere.

All 50 files hold four-column MARK rows, all 50 carry a
`ts,addr,old,new` header, and 44 carry `#` rows. So:

- **Shape A leaves all 50 untouched.** Their mark rows keep their column
  count, a writer's new field changes nothing about a file that has none, and
  every reader above opens them exactly as it does today.
- **Shape B adds a row shape none of the 50 carries.** It does not alter a
  single mark row, and it does not collide with the 44 files' existing `#`
  blocks either — the skip rule is a prefix test and `# provenance` is a
  different prefix from `# CONSTRUCTED INPUT` or `# baseline`. "Adds a row
  shape" is the cost; "breaks a fixture" would be a much larger claim than the
  measurement supports.

The two directories are not symmetric, and neither number should be quoted
without its split. `evidence/ec-watch/` holds 15 committed files — 10 CSVs and
5 `.txt` files that are not captures at all: one `ecrw.py dump` hex dump, two
hand-written test logs (`# Issue #99 …` and `# Issue #8 …`), one read-only EC
snapshot and one `ec/tools/ec_timer_capture.py --census` output — and **2** of
the CSVs hold MARK rows at all; the other 8 hold none. The two are
`2026-09-24-06c2-06db-perturb-linux.csv` (6 marks) and
`2026-09-24-06c2-06db-suspend-linux.csv` (2 marks), both written by
`ec_timer_capture.py` and both in the timer family, so under either shape they
are fixtures a later change would have to be able to read *and* would have
stopped being representative the day a capture was taken with the new shape.

## What each shape costs each reader

The whole measurement, from the tool. Three readers of the 0751 capture and
one of the timer capture, each called on a constructed temp file in three
shapes: no provenance, a fifth column, a `# provenance` comment row. The
constructed files carry an early-exit `#` row and a `resumed` mark so both
phrase-matching readers are actually reached — a zero measured on a branch
nothing entered is not a zero.

```console
0751 capture, over ec/tools/grade_0751_isolation.py
  read_capture
    none             3 mark(s) ['settled', 'wrote 0x0751=0xA0', 'restored 0x0751=0xA0'], 3 change row(s) [('0x796', 47, 48), ('0x796', 48, 49), ('0x751', 160, 160)]
    fifth column     3 mark(s) ['settled', 'wrote 0x0751=0xA0', 'restored 0x0751=0xA0'], 3 change row(s) [('0x796', 47, 48), ('0x796', 48, 49), ('0x751', 160, 160)]
    provenance row   3 mark(s) ['settled', 'wrote 0x0751=0xA0', 'restored 0x0751=0xA0'], 3 change row(s) [('0x796', 47, 48), ('0x796', 48, 49), ('0x751', 160, 160)]
  existing_mark_labels
    none             [('2026-01-01T12:00:10.000+01:00', 'settled'), ('2026-01-01T12:00:41.750+01:00', 'wrote 0x0751=0xA0'), ('2026-01-01T12:01:20.000+01:00', 'restored 0x0751=0xA0')]
    fifth column     [('2026-01-01T12:00:10.000+01:00', 'settled'), ('2026-01-01T12:00:41.750+01:00', 'wrote 0x0751=0xA0'), ('2026-01-01T12:01:20.000+01:00', 'restored 0x0751=0xA0')]
    provenance row   [('2026-01-01T12:00:10.000+01:00', 'settled'), ('2026-01-01T12:00:41.750+01:00', 'wrote 0x0751=0xA0'), ('2026-01-01T12:01:20.000+01:00', 'restored 0x0751=0xA0')]
  read_early_exits
    none             [('2026-01-01 12:01:30+01:00', 'fan stalled: the restore never ran')]
    fifth column     [('2026-01-01 12:01:30+01:00', 'fan stalled: the restore never ran')]
    provenance row   [('2026-01-01 12:01:30+01:00', 'fan stalled: the restore never ran')]
  marks carrying provenance in their own row, of 3:
    none             0
    fifth column     3
    provenance row   0

timer capture, over ec/tools/grade_timer_sweep.py
  grade_timer_sweep.load
    none             2 change row(s) [('0x6d6', 3, 2), ('0x6d6', 2, 1)], watched [1750, 1753], span 3.0, interval 0.0005, 1 resume(s), 1 gap(s)
    fifth column     2 change row(s) [('0x6d6', 3, 2), ('0x6d6', 2, 1)], watched [1750, 1753], span 3.0, interval 0.0005, 1 resume(s), 1 gap(s)
    provenance row   2 change row(s) [('0x6d6', 3, 2), ('0x6d6', 2, 1)], watched [1750, 1753], span 3.0, interval 0.0005, 1 resume(s), 1 gap(s)
  marks carrying provenance in their own row, of 1:
    none             0
    fifth column     1
    provenance row   0
```

### Reading the table

**Both shapes are free in all four readers the tool calls — and in the three
more that reach the same functions — and that is not the interesting part.**
The interesting part is the last line of each block, and it is the only line
in the whole measurement on which the two shapes differ: **3 of 3 and 1 of 1
under shape A, 0 of 3 and 0 of 1 under shape B.** Shape B's provenance is in
the file and not on the mark; shape A's is on the mark. Every other line is
the same for both, and saying "shape B is compatible" on the strength of
those lines would be reading the table upside down.

Per reader. The first three rows and the last are the ones the tool *calls*;
the middle three it does not, and their cells follow from a citation the tool
verifies — `grade_gpu_door.py:421` and `check_capture_claims.py:514` call the
`read_capture` the first row measured, and `grade_0751_isolation.py:2968`
counts that function's return. That is a checked link rather than a second
measurement, and it is worth saying so rather than presenting seven rows as
though seven calls happened.

| site | fifth column | `# provenance` row |
|---|---|---|
| `read_capture` (`:852`) | zero — `:1042` is `len(row) < 4` and `:1044` indexes `row[0..3]`, so the tail is dropped and `Window` is identical | zero — caught by the `row[0].startswith("#")` half of `skippable_row` at `:845` |
| `existing_mark_labels` (`:896`) | zero — `mark_labels_of` at `:1068` returns `(row[0], row[3] if len(row) > 3 else "")`, identical at 4 or 5 columns | zero, same predicate, called at `:1065` |
| `read_early_exits` (`:1342`) | zero — `:1384` tests `row[0]`, and a mark row's `row[0]` is a timestamp, which cannot open with a `#` | zero *by the invariant* documented at `grade_0751_isolation.py:428`, not by the skip: the phrase test is a prefix test, and the safety is that a hand annotation does not open with that phrase |
| `grade_gpu_door.py:421` | zero — it unpacks `read_capture`'s two-tuple, which is what the first row measured | zero, same reason |
| `grade_0751_isolation.py:2968` | zero — `f"{path}: {len(m)} mark(s), {len(c)} change row(s)"` counts and never spells the row | zero, same reason |
| `check_capture_claims.py:514` | zero — it calls the same `read_capture` over committed captures | zero, same reason |
| `grade_timer_sweep.py:138` | zero — `r[1] == "MARK"` then `"resumed" in r[3]` at `:139`; both index, `r[4]` is never read | zero — `:115` drops every `#` line before the CSV parse and only three phrase regexes survive it |

**The preflight returning the same list under both shapes is the real limit of
this measurement, and it is a limit on the notice, not on the format.** It is
a preflight, and a preflight that echoed provenance would be doing the job
`parse_mark` does. But the consequence is the same under both shapes: the
notice at `ec_watch.py:288` calls `existing_findings(path)` at `:361` and gets
the same list either way, so *the provenance a fifth column carries is as
invisible to the notice as a comment row is*. Neither shape, as scoped, makes
`warn_unchecked_marks` say anything new. Both make the fact available to a
tool willing to re-read the file, and shape A is the one where a reader does
not first have to invent a position.

## The `#` namespace

The issue is right that the skip rule is load-bearing and that a phrase-based
namespace is therefore a cost. The measured size of that cost depends on the
family, and the two are not the same:

```console
  windows/tools/manual_fan_ctrl_probe.py:257  ok   '# the run ended early:'
  ec/tools/ec_timer_capture.py:296  ok   'ec/tools/ec_timer_capture.py, read-only, ECMG window '
  ec/tools/ec_timer_capture.py:298  ok   'started '
  ec/tools/ec_timer_capture.py:299  ok   'power: '
  ec/tools/ec_timer_capture.py:300  ok   'interval '
  ec/tools/ec_timer_capture.py:303  ok   'note: '
  ec/tools/ec_timer_capture.py:306  ok   'baseline '
  ec/tools/ec_timer_capture.py:312  ok   'auto-mark state at start: '
  ec/tools/ec_timer_capture.py:342  ok   'ended '
```

**In the 0751 family the namespace is one machine phrase.** The probe writes
`EARLY_EXIT_TAG` at `manual_fan_ctrl_probe.py:927` and nothing else writes a
`#` row into an `ec_watch.py` capture; the grader writes none. `ec_watch.py`
is silent on the `#` namespace entirely, which is what makes
`read_early_exits`'s docstring's reasoning load-bearing rather than
defensive: a second machine phrase would be exactly the thing that reasoning
has to keep holding.

**In the timer family it is already eight, from one writer.**
`ec/tools/ec_timer_capture.py:149` writes `# <text>` and calls it at eight
prefixes, and `grade_timer_sweep.load` matches three of them by regex. So a
`# provenance` row in an `ec_timer_capture.py` capture would be the ninth, in a
namespace nothing keeps an index of. This is a real argument *for* shape A and
the measurement would have hidden it: an issue that reasoned from the 0751
family alone would have called the `#` namespace "one phrase" and been right
only about the file it had in front of it.

## The correction to the issue's framing of shape B

The issue describes shape B as "per process, not per mark, so it answers
'which consoles had the flag' and not 'which mark did which console type'".
The intent is right and the statement is looser than the format: a `#`
provenance row written at startup **does** bind to the marks that follow it,
and a second one binds the rest. Per-mark attribution is reachable, by
position.

The real cost is that nothing returns the position:

- `existing_mark_labels` (`:896`) returns a flat `(ts, label)` list — its
  `mark_labels_of` at `:1068` builds it — with no index, no line number and no
  row. A reader that wanted to bind a provenance row to a mark has to re-read
  the file and re-derive an ordering the preflight deliberately flattened.
- The binding is *positional*, so it is fragile in a way a column is not. An
  operator who reorders a capture, or a writer that appends a provenance row
  after the marks it describes, silently reassigns every mark beneath it. A
  column cannot be reordered away from its mark.
- And under shape A the fifth column is *also* invisible to
  `existing_mark_labels` (`:1068` reads `row[3]` and never `row[4]`). The
  difference is not that shape A is preflight-visible and shape B is not. It is
  that shape A's answer sits on the mark's own row, where a reader can reach it
  without first inventing the order the preflight threw away.

## What each shape would and would not resolve

The runbook's four ways a file comes to hold an unchecked mark are (a) a
pre-flag run, (b) a console started without `--label-vocab`, (c) a watcher
restarted mid-block, and (d) a `manual_fan_ctrl_probe.py` capture. §3's three
commands carry the flag — `manual-fan-ctrl-0751-isolation.md:159`, `:161` and
`:163` — and nothing forces it on all three.

**Both shapes resolve (b) and (c).** A console started without the flag writes
the fact in whatever field it records, and a watcher restarted mid-block writes
a second one. Those two become distinguishable from each other and from (a) and
(d), which is precisely the distinction `warn_unchecked_marks` says it cannot
draw. That is real, and it is the whole of the value.

**Neither shape resolves (a) or (d), and this is the half that has to be said
out loud.** A file written before either shape exists carries no provenance at
all, and (d) is a `manual_fan_ctrl_probe.py` capture whose marks come from
`arm_labels` — §3's forms by construction, checked by a different tool, in a
process that never runs the flag. Under this issue's scope the probe is
unchanged, so its rows would keep four columns and read as *not recorded*
rather than as *held no flag*. So the honest post-change census is two
resolved and two not, and a write-up that let either shape read as closing all
four would be overclaiming in exactly the way this repository's calibration
rule is about.

## The calibration that travels with the recommendation

An argv entry records **the promise the writing process made**. It is not
evidence that a particular label is placeable, and it is not evidence that a
mark parses — those are `parse_mark` and `unplaceable_marks`, which already
exist and are per-label. A `--label-vocab 0751` in the column is what §3's
block 1 would carry, and its absence is what a console started without the
flag would carry. It would still not tell a reader whether a
`manual_fan_ctrl_probe.py` mark was one of §3's forms, because that process
holds no flag either way and would write nothing under a shape scoped to
`ec_watch.Marker._loop`.

So a populated column reads: *a process that said it was checking, wrote this.*
It does not read: *this label was checked*, and it must not be printed as
though it did. #548's own notice already draws that line — it says the marks
in the expected case *were* checked "as they were typed, by the process that
typed them" and still says this run cannot check them. A provenance column
sharpens the same boundary; it does not move it.

## Backward compatibility: three states, not two

A file written before the change carries no provenance, and the notice has to
keep saying exactly what it says today about those marks. So a fifth column
is not a boolean and **a four-column mark row must never be read as "this
process did not hold the flag"** — it means *not recorded*. The states are:

1. **column absent** — a pre-change file, or a probe capture under this scope;
2. **column present and empty** — a process that held no flag;
3. **column present and populated** — a process that held one.

The tool measures state 3 against the base, and the self-test measures state 2
directly: an empty fifth column comes back from `existing_mark_labels` as
exactly `('ts', label)`, the same as a four-column row. The preflight cannot
distinguish 1 from 2 from 3, and that is correct — it is a preflight. What must
be recorded in the format is that a reader *can*, and a reader cannot if empty
and absent are the same bytes. Hence: write the column always, empty when there
is nothing to say, and never infer absence from a missing field.

The notice's wording is unchanged for a file in which no mark carries
provenance, and that is the whole backward-compatibility case. It is also the
most common case for as long as the format is new.

## The recommendation

**Shape A, the fifth column.** The measurement decides it, and the deciding
figure is the one number on which the two shapes differ: **3 of 3 marks carry
their provenance in their own row, against 0 of 3** — and 1 of 1 against 0 of
1 in the timer family. Four grounds:

1. **It is per-mark, which is the question `warn_unchecked_marks` actually
   asks.** The notice names individual marks (`for ts, label in marks:`). A
   per-process row answers a different, coarser question and makes the reader
   re-derive the per-mark one.
2. **It costs zero in all seven consumers** — four called directly and three
   reached through them — because each indexes rather than unpacks: `:1044`
   for `read_capture`, `:1068` for `existing_mark_labels`, `r[3]` for
   `grade_timer_sweep`, and the three programs that only take
   `read_capture`'s two-tuple.
3. **It does not spend the `#` namespace.** The skip rule is documented as
   load-bearing for hand annotation in three docstrings in the grader —
   `read_capture`'s, `existing_mark_labels`'s ("it takes `skippable_row`")
   and `read_early_exits`'s — and the 0751 family currently
   spends that namespace on exactly one machine phrase. The timer family
   already spends eight prefixes from a single writer nothing indexes; a
   ninth is worse than a field.
4. **Its absence is the honest reading of a pre-change file.** A comment row
   has exactly the same property, so this is the weakest of the four — it is
   listed because the issue asks for the backward-compatibility case to be
   argued rather than asserted, and a column that is always present is the
   shape in which "absent" and "empty" are distinguishable at all.

### Its costs, stated as fully as its advantages

- **The argv is repeated on every mark.** §3's block asks for six marks
  (`manual-fan-ctrl-0751-isolation.md:167-181`), so a field the size of the
  tool's own `PROVENANCE` sample — 42 bytes — six times is trivial in bytes
  and O(marks) where shape B is O(1). Six is the number today; it scales with
  the operator's typing, not with the run.
- **It is a format change to a row four writers in this tree share** — seven
  call sites across four files. The implementation issue has to decide the
  other three writers deliberately, rather than letting them drift by omission.
  The two that matter are `system_id_probe.py:261`, which imports no
  `ec_watch.Marker` and so is not reached by scoping to `Marker._loop`, and
  `ec_timer_capture.py`'s four sites, whose files a different grader reads.
- **`windows/tools/test_manual_fan_ctrl_probe.py:515` would fail** if the
  shape were ever widened to the probe. That is the intended behaviour of a
  canary and not an argument against the shape, but it is a real cost to name:
  the first thing a widened implementation hits is a failing assertion.
- **It does not make the notice say anything.** Under either shape
  `existing_mark_labels` at `:896`, building at `:1068`, returns the same flat
  list, so `warn_unchecked_marks` is unchanged. The value lands in the grader
  and in whatever tool reads provenance later, and the implementation issue
  should not promise the operator a better warning as part of it.

If a later measurement contradicts any of the four grounds, the measurement
wins and this section is what has to be edited. The grounds rest on figures
the tool prints, so a run that disagrees is a visible disagreement rather than
a claim buried in prose that nothing re-derives.

## What the tool checks, and what it does not

`check_python_syntax` in `.github/scripts/agent-gates.sh` already globs
`ec/tools/*.py`, so the new tool is py-compiled by the existing gate at no
cost and with no gate edit. Nothing under `.github/` is touched, and the
push token has no `workflow` scope in any case.

`--self-test` runs the whole measurement over a temp tree and exits non-zero if
a reader differs from the base under either shape, if `read_capture` accepts a
three-column row, if it raises on a five-column one, if `existing_mark_labels`
differs between a shape and the base, or if an empty fifth column stops reading
as `('ts', label)`. That is what makes this page's zero-cost cells checkable
rather than asserted. **No gate calls it.** Wiring a new tool into
`agent-gates.sh` is an upstream change to a file copied from
`ElDavoo/agent-pipeline`, not a line to add here, and `tools/run-tests.sh`
discovers `test_*.py` only — which is also why there is no `test_*.py` for
this issue: no behaviour in the tree changes, so there is nothing new to pin,
and the pinning belongs to the implementation issue that follows.

The citation check re-reads every site the tool and this page name, at the
line quoted, and the row-site join closes in both directions — a scanned site
no citation names is a failure, so this census cannot quietly become a
hand-typed list. It already earned its place twice over: it caught
`test_manual_fan_ctrl_probe.py:513` in the tool's own table, which is
`assertEqual(rows[0], ...)`, when the assertion is at `:515`; and the
self-test caught its own three-column fixture, which was written `MARK,,x` and
was four columns. Both are the same class of drift
`docs/findings/0751-append-unchecked-marks.md` §"The issue's line numbers have
drifted" records as a caution, turned into a check.

**One boundary of that closure is worth naming, because it is where this page's
own argument bit.** `check_page` holds *this page* to the tool's output and
nothing holds the summary paragraph in `docs/findings.md` §16a, which is
transcribed by hand. That paragraph is the one place in the measurement with a
figure and no check behind it, and the first draft of it hedged the tool's exact
`50` and `four` as "over 50" and "over four". The figures are the tool's and are
quoted as it prints them now; that they are the tool's is still a claim, not a
check, and a reader should re-run the tool rather than trust the summary for
them.

### The evidence index

Section 5 of the tool's output, printed in full so a reader can see every site
this page rests on without taking the prose's word for which ones exist. The
prose above uses the repository's `:NNN` shorthand, so this table is what ties
a line number to a file.

```console
   ok   windows/tools/ec_watch.py:473  writer: the Marker._loop the issue's shape A is scoped to
   ok   windows/tools/system_id_probe.py:261  writer: a third class, importing no ec_watch.Marker
   ok   ec/tools/ec_timer_capture.py:169  writer: mark_loop
   ok   ec/tools/ec_timer_capture.py:204  writer: auto_mark_loop, the resume branch
   ok   ec/tools/ec_timer_capture.py:210  writer: auto_mark_loop, the machine-state branch
   ok   ec/tools/ec_timer_capture.py:232  writer: input_mark_loop
   ok   windows/tools/manual_fan_ctrl_probe.py:443  writer: MarkCsv.mark
   ok   ec/tools/grade_0751_isolation.py:1045  reader: take_capture_row recognising the row, read_capture's own body
   ok   ec/tools/grade_0751_isolation.py:1099  reader: partition_capture_rows recognising the row -- the fourth site over this shape, and the one the notice partitions its own read with, so a mark row is never hex-read there either
   ok   ec/tools/grade_0751_isolation.py:1067  reader: mark_labels_of recognising the row, existing_mark_labels' own extraction
   ok   ec/tools/grade_0751_isolation.py:976  the partition's docstring quoting that branch, which the scan matches because it is the same literal spelled in prose
   ok   ec/tools/grade_timer_sweep.py:138  reader: grade_timer_sweep.load recognising the row
   ok   ec/tools/check_capture_encoding.py:166  reader: the encoding check's own mark/change census, written against the same shape and declared against the same codec
   ok   ec/tools/check_capture_encoding.py:243  a constructed row rather than a writer: `check_capture_encoding` builds one to hand a writer that takes a label alone, and the literal scan counts it as a consumer because the `.row(` call is on the next line
   ok   windows/tools/test_manual_fan_ctrl_probe.py:508  reader: the only exact-column-count filter in the tree
   ok   windows/tools/test_ec_watch.py:145  a single-quoted MARK the scan cannot match: a test assertion, not a writer
   ok   windows/tools/test_system_id_probe.py:311  the same in the other suite, so the blind side is the tree's and not one file's
   ok   ec/tools/grade_0751_isolation.py:852  read_capture
   ok   ec/tools/grade_0751_isolation.py:845  the one skip rule, where a `# provenance` row goes
   ok   ec/tools/grade_0751_isolation.py:886  read_capture refusing a byte-order mark before it reads a row, which is what keeps the header out of the row shape's data rows
   ok   ec/tools/grade_0751_isolation.py:890  read_capture calls that one skip rule rather than spelling it
   ok   ec/tools/grade_0751_isolation.py:1042  read_capture's only length test: a fifth column passes it
   ok   ec/tools/grade_0751_isolation.py:1044  explicit indexing, not an unpack of row -- the correction to the issue
   ok   ec/tools/grade_0751_isolation.py:896  existing_mark_labels
   ok   ec/tools/grade_0751_isolation.py:1065  mark_labels_of takes that one skip rule, so existing_mark_labels -- which delegates its extraction to it -- cannot spell a second copy
   ok   ec/tools/grade_0751_isolation.py:1086  and so does the partition, over the notice's own read
   ok   ec/tools/grade_0751_isolation.py:1068  the (ts, label) pair: no position, and no fifth column either
   ok   ec/tools/grade_0751_isolation.py:1342  read_early_exits
   ok   ec/tools/grade_0751_isolation.py:1384  the phrase test: a mark's row[0] is a timestamp
   ok   ec/tools/grade_0751_isolation.py:428  the one machine phrase the `#` namespace spends in this family
   ok   ec/tools/grade_0751_isolation.py:2972  the per-capture census line, which counts rather than spells
   ok   ec/tools/grade_gpu_door.py:421  the second consumer of read_capture's two-tuple
   ok   ec/tools/check_capture_claims.py:514  a third, and the only one that reads every committed capture
   ok   ec/tools/grade_timer_sweep.py:115  grade_timer_sweep drops every `#` line before the CSV parse
   ok   ec/tools/grade_timer_sweep.py:139  the one phrase grade_timer_sweep reads a MARK row for
   ok   windows/tools/ec_watch.py:288  the notice the measurement exists for
   ok   windows/tools/ec_watch.py:361  the notice's one call into the grader's reader
   ok   windows/tools/test_manual_fan_ctrl_probe.py:515  the canary: the only committed assertion of an exact column count
   ok   windows/tools/manual_fan_ctrl_probe.py:257  the probe's own spelling of the same phrase
   ok   windows/tools/manual_fan_ctrl_probe.py:927  the only machine-written `#` row in the 0751 family
   ok   ec/tools/ec_timer_capture.py:149  the timer family's `#` writer, which writes by prefix not by phrase
   ok   docs/hardware-tests/manual-fan-ctrl-0751-isolation.md:159  §3 block 1, the console that holds the flag
   ok   docs/hardware-tests/manual-fan-ctrl-0751-isolation.md:161  §3 block 2
   ok   docs/hardware-tests/manual-fan-ctrl-0751-isolation.md:163  §3 block 3
```

What it does not check: whether either shape is a good idea; what a widened
shape should mean for `system_id_probe.py`, `ec_timer_capture.py` or
`manual_fan_ctrl_probe.py`; whether the readers are right about anything but
the shape; and any capture this repository has not committed.

## None of this is a live test.

No EC and no laptop is reachable from a GitHub-hosted runner. No capture was
taken, no register was read, no mark was typed, no §3 block was run, and no
`registers.yaml` `status:` moved. Section 2 is a count over two committed
directories and section 3 is a reader's behaviour on a file the tool wrote
itself. What the measurement settles is what a change would cost, which is a
fact about this tree; whether the column's contents are worth writing on the
machine is a human's step, and implementing the chosen shape is the next
issue's.
