# The capture format is `utf-8`, declared rather than inherited (issue #748)

The write-up for [issue
#748](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/748), which asks
for one named encoding at every reader and writer of the `ts,addr,old,new`
shape. #718 measured the consequence and wrote it down: the grader was not
encoding-portable, and the same capture could be gradeable on one box and
refused on another. This is the fix that sentence asks for, and the writer half
#718 deliberately left out of scope.

**The decision: `utf-8`, no BOM**, declared at all thirteen read and write
sites, on both sides. A capture already on disk in another encoding is
**refused, with the encoding and the remedy named** — not decoded per row. The
argument for both is below, and the BOM interaction is stated rather than
decided.

Every figure is `ec/tools/check_capture_encoding.py`'s output, quoted.
Re-derive it with:

```console
python3 ec/tools/check_capture_encoding.py            # the tables
python3 ec/tools/check_capture_encoding.py --quiet    # just the verdict
```

Offline throughout: no EC, no laptop, no Windows box. The one claim about a
Windows interpreter stays a **prediction from the documented default** and is
labelled as such in §5. Nothing here ran on a machine that has hardware.

---

## 1. What was on disk, measured

The corpus is what the declaration has to be compatible with. Walking every
committed capture under `ec/tools/testdata/` and `evidence/ec-watch/`:

| | `ec/tools/testdata/` | `evidence/ec-watch/` | total |
|---|---|---|---|
| captures | 52 | 10 | **62** |
| carrying a high byte | 36 | 0 | **36** |
| carrying a BOM | 0 | 0 | **0** |
| not UTF-8-decodable | 0 | 0 | **0** |

The 36 are hand-written `#` comment lines containing `§`
(`0751-isolation-run-3blocks/2026-01-01-0751-isolation-0700-07ff.csv:4` and
the other five runs) — the format's own vocabulary, typed by hand into a
comment. The other ten are a finished run committed as the file it was captured
to, and are ASCII.

**Zero of 62 carry a BOM.** That number is what decides §3, and it is the
reason this is a declaration rather than a widening: the corpus is already
UTF-8, so declaring UTF-8 admits all of it and refuses none of it.

## 2. The sites, all thirteen

Readers and writers of the shape, and whether the change made them stricter.
The split is the point, not an accident of the edit:

| Site | Side | `errors=` | Line |
|---|---|---|---|
| `grade_0751_isolation.py` `read_capture` | read | — (strict) | `:852` |
| `grade_0751_isolation.py` `existing_mark_labels` | read | `replace` | `:896` |
| `grade_0751_isolation.py` `refused_capture_rows` | read | `replace` | `:957` |
| `grade_0751_isolation.py` `capture_snapshot`, which `existing_mark_findings` reads through | read | `replace` (in `capture_lines`) | `:1134` |
| `grade_0751_isolation.py` `read_early_exits` | read | — (strict) | `:1364` |
| `grade_0751_isolation.py` `read_dump` | read | — (strict) | `:1421` |
| `grade_0751_isolation.py` `capture_rows`, the four readers' shared stream (#750) | read | the caller's — bare or `replace` | `:749` |
| `ec_watch.py` `CsvSink` | write | — | `:143` |
| `system_id_probe.py` `CsvSink` | write | — | `:217` |
| `ec_validate.py` `SampleCsv` | write | — | `:163` |
| `manual_fan_ctrl_probe.py` `MarkCsv` | write | — | `:429` |
| `ec_timer_capture.py` `Sink` | write | — | `:143` |
| `check_capture_claims.py` `read_capture` | read | — (strict) | `:228` |
| `grade_timer_sweep.py` `load` | read | — (strict) | `:112` |

The `Line` column is the merged tree's, and every value in it is a line that
opens, names or reads the site in its own row. It was this page's own tree when
the page was written and has moved three times since: #749 split the readers'
bodies out (`take_capture_row`, `mark_labels_of`, `partition_capture_rows`,
`capture_snapshot`, `capture_lines`), #750 added the shared `capture_rows`
stream on top, and #771 added docstring prose above `refused_capture_rows` and
changed no line of code. The first six rows sat at `:693`, `:740`, `:789`,
`:919`, `:1108` and `:1135` before that, and the last two of those were already
stale even on #748's own tree — `read_early_exits` is at `:937` and `read_dump` at
`:979` there — so all six are re-anchored here rather than left naming the
wrong function. The split itself — strict readers bare, preflights `replace` —
is unchanged, and is now made once in `capture_rows` rather than six times.

**Three of these the issue's list missed**, and taking its done-condition —
"one named encoding, in *every* reader and writer of the `ts,addr,old,new`
shape" — as authoritative rather than its bullet list:

- **`ec_timer_capture.py` `Sink` is a fifth writer.** Its own docstring says
  the format is the one `grade_0751_isolation.py` and
  `check_capture_claims.py` already read. It is a Linux tool, which is not a
  reason to leave it alone: it writes the shape the Windows graders read.
- **`check_capture_claims.py` is a seventh reader**, and the one most likely to
  meet a foreign byte, because it walks the *entire* committed corpus rather
  than the files a run is given.
- **`grade_timer_sweep.py` `load` is an eighth reader** of the same shape.

`grade_gpu_door.py:421` calls `fan.read_capture` and so inherits the change
with no edit of its own; it is a consumer to re-run, not a file to change.

**The literal is repeated, not shared, on purpose.** A shared constant module
would break the deployment the runbook depends on: `windows/tools/` is copied
as a *directory* onto a Windows box, and `ec_watch.py` loads the grader **by
path** precisely so no second copy of a rule can drift from the thing that
enforces it (#548). A new cross-import would either need copying too, or
reintroduce the drift the design removes. Each writer class carries the
literal, which is also the existing state: three of these classes are already
separate copies of the same idea, and the repo accepts that copy over a broken
standalone tool. The repo's own idiom agrees — `mqtt_decode.py:87` and
`mqtt_sniff.py:196` already write `encoding="utf-8"`, and
`windows/tools/ec_callsites.py:78` already uses `utf-8-sig` for a different
format.

**Three appenders left out, deliberately.** `battery_trace.py:81`,
`ctgp_dben_probe.py:231` and `charge_target_test.py:154` also open a CSV with
no `encoding=`, but their column sets are `ts,phase,...` and
`ts,mark,t_s,...`. **Not this format.** Named here so the omission reads as a
decision rather than an oversight; they are worth a follow-up in their own
right.

## 3. `utf-8`, not `utf-8-sig`

`utf-8-sig` was the live alternative and it loses on the measurement:

- **0 of 62 committed captures carry a BOM.** Declaring `utf-8-sig` would state
  a property no file in the corpus has.
- Worse, on the **write** side `utf-8-sig` *emits* a BOM. The five writer
  classes would then have to agree on emitting one, and the corpus would gain
  a property it does not have today.
- The repo has one BOM precedent (`ec_callsites.py:78`, a different format and
  a read side), so the choice is worth the argument rather than a shrug.

`utf-8` keeps the bytes symmetric and honest: what the writers declare is what
the readers accept, and what the 62 committed captures already are.

## 4. A capture already on disk in another encoding is refused

Refused, with the encoding and the remedy named — not decoded per row.

*Why refuse rather than per-row decode:* per-row decoding would make the
meaning of the file a property of the reader again, which is exactly what this
change retires. It would also let the strict reader accept a file whose bytes
are not the format, so the codec a reader reports and the file's real bytes
could disagree — which is the bug, not the fix. (On this tree the strict
readers no longer open the file a second time to ask what codec they used:
#749 merged in alongside, and the codec now comes out of the decode that
failed. The argument is the same either way — the disagreement, not the
particular way of learning the codec.)

*Why refusal is safe on the lenient side:* the three preflight readers keep
`errors="replace"`. The startup notice still cannot die on a foreign byte. The
operator sees the byte as U+FFFD inside a label they are being shown anyway,
and still sees every mark; the grading then refuses the file, naming it. That
split already existed in `existing_mark_findings` and this change keeps it.

So a lone 0xE9 — latin-1 and cp1252 both write it for `café` — now produces,
on every interpreter:

```
the grader's reader cannot decode a byte of this file in the utf-8 a capture
is defined to be, and raises before it reaches a row: 'utf-8' codec can't
decode byte 0xe9 in position 55: invalid continuation byte. A capture is
utf-8; this one is written in something else. Re-save it as utf-8, or re-run
the capture with a writer that declares the codec.
```

`read_early_exits` has **no `errors=`** today, so a foreign byte was already a
grading-time crash there and not only a notice-time one. Under a declared
encoding that becomes the format's rule rather than an accident of the
interpreter, and the codec is named in the `UnicodeDecodeError` it propagates.

## 5. The BOM interaction, and the Windows prediction

**A BOM is not retired, and saying so is the point.** `encoding="utf-8"` alone
does not consume a leading BOM: `utf-8` decodes U+FEFF as a character, it glues
to the first field, the `row[0] == "ts"` header test misses, and the header is
graded as a change row and refused on `int("addr", 16)`. That is a complaint
about a hex literal on a line that is not a change, and it never mentions the
encoding. So `read_capture` catches it before the hex is read:

```
capture.csv: starts with a byte-order mark, so its first field is '﻿ts' and
not 'ts'. A capture is utf-8 with no BOM; re-save this one without one.
```

**Whether the format should ever *accept* a BOM is a separate question and this
does not decide it.** That is the separate open BOM issue; this states which of
`utf-8` / `utf-8-sig` the format is, and makes the resulting refusal legible
rather than mysterious.

**The Windows prediction is not retired by observation.** "A stock Windows
Python 3.12 writes `§` as 0xA7" remains a **prediction from the documented
default, with no box reached**. Nothing here confirms it. What changes is that
it stops being load-bearing: with the encoding declared, which interpreter
reads the file is no longer part of what the file means. The prediction is
retired *in words only*.

**What the writer half does and does not show.** `check_capture_encoding.py`
round-trips a `§` mark through all five writer classes and reads the bytes back
off disk; all five put UTF-8 on disk with no BOM. The class under test is each
writer's real source executing its real `open()`, but it is running on a Linux
runner with `ecrw` stubbed — `ecrw.py` calls `ctypes.WinDLL("kernel32")` at
module scope, so none of the four Windows writers can be imported here at all.
A codec is a property of the Python that writes, and that is what is under
test. It is **not** a Windows run, and the round-trip does not stand in for one.

## 6. The check, and what it found

`check_capture_encoding.py` reads each of the 62 captures twice — once under
the declared codec, once under this interpreter's default — and compares. All
62 agree, all 62 decode, none carries a BOM.

**How strong is that?** Weaker than it looks on this runner, and the tool says
so in its own output: this machine's default is already UTF-8, so the two reads
are *the same read* and the agreement column is close to trivial. The strong
claim is the narrower one: **all 62 decode as UTF-8**, which is what a
declaration of any other codec would have broken. The comparison earns its keep
on a runner whose default differs.

The check is not a check that cannot fail. Against a constructed tree it
reports a BOM, reports a capture that is not UTF-8-decodable, and reports a
disagreement between the two reads — three distinct problems, named by path.

## 7. The gate this makes redder, measured rather than hidden

`measure_mark_provenance.py` holds a `CITATIONS` table of 37 exact `path:line`
pins, re-reads each one, and `check_citations` fails loudly on drift. It was
**already red on `main` before this change**, for reasons that have nothing to
do with encoding:

- **6 of 37 had already drifted** (e.g. `read_early_exits` pinned at `:739`,
  now at `:937`).
- It then **crashes**: `ValueError: not enough values to unpack (expected 3,
  got 2)` at `:601`, because `scan` yields 2-tuples and the loop unpacks 3.

So it could not serve as a regression check for this change, and this does not
claim it as one. What the change did to it, counted the same way both times:

| | before | after |
|---|---|---|
| citations | 37 | 37 |
| drifted | **6** | **29** |
| newly drifted | — | **23** |

The new drift is line movement, not a change in what is cited: the encoding
declarations and the BOM refusal are comments and `open()` arguments that sit
*above* pinned lines in five files. 27 of the 29 resolve to an exact new line
by searching the file for the pinned text; the two that do not —
`ec_watch.py:254` and `:280` — had **no copy of their pinned text anywhere in
the file before this change either**, so re-anchoring them needs judgement
rather than arithmetic.

**Recorded, not fixed.** The crash and the re-anchoring are a pre-existing
defect in another tool, they are unrelated to encoding, and re-anchoring 37
entries inside an encoding PR is not verifiable from here — the tool that
would verify it is the thing that is broken. Fixing it belongs to its own
issue, and this makes an already-red gate redder and says so rather than
quietly editing pins to look tidy.

## 8. The two places the tree promised otherwise

Both promised that a capture grades identically at the machine or brought back.
Both are corrected **in place**, with the wrong version left visible, per the
retraction pattern in `docs/findings.md` §4a-4d:

- `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` — "grades
  identically either way" was true for the ten files of §6 as committed and
  was not a property of the format. It now names the encoding.
- `docs/findings.md` — the same claim in a different sentence, from #548.

`windows/tools/ec_watch-marks.md`'s encoding section described an **inherited
locale default** and is corrected and extended, dated, in place.

## 9. What this does not settle

- **Whether the format should accept a BOM.** A separate open issue owns it.
- **The Windows cp1252 case, by observation.** No box is reachable from here.
  A human at the machine runs that if they want it confirmed.
- **The three non-capture CSV appenders** (§2). Same gap, different column
  sets, a follow-up in their own right.
- **`measure_mark_provenance.py`'s crash and its 29 drifted pins** (§7). Its
  own issue.
- **Register behaviour of any kind.** Nothing here touches
  `ec/annotations/registers.yaml`; this is a file-format decision.
