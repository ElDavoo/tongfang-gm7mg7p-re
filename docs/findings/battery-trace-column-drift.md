# The battery trace's column set moved to a shell script, and the append guard never checked what it was appending to (issue #363)

The write-up for [issue
#363](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/363):
`windows/tools/battery_trace.py` had no offline suite, so its function-local
`cols` and its `WATCH` were held by nothing, and the column drift across
`evidence/battery-traces/` was unrecorded. Both are now held, by
`windows/tools/test_battery_trace.py`.

**The append gap below has since been closed**, by the work recorded under
[The append guard](#the-append-guard): `battery_trace.py` now compares the
header already in the `--csv` target with the columns it is about to write and
refuses the append on a mismatch, and `limit-pair-test` does the same before it
writes anything.

**The tool *was* edited, below the lines that hold it.** Two committed citations
pin this file by line number: `ec/ghidra/xdata-overrides.csv:9` cites
`battery_trace.py:51` for `ADDR_CURRENT`, and
[`probe-csv-encoding.md`](probe-csv-encoding.md) cites `battery_trace.py:81` for
the `open()` on `--csv`. Nothing in the tree resolves a prose `path.py:NNN`, so
an edit above either would falsify a citation in silence — which is why the new
guard is placed **below line 84**, leaving everything above byte-unchanged, and
why a case in the suite now asserts each cited line still carries the text it is
cited for rather than merely that it is still numbered 51 and 81. Nothing below
is hardware evidence: no EC is opened, no register is read back, and no row in
this directory was produced by a run that happened now.

## The census

Every file in the directory as committed here, by column set. The suite holds
the file set and the column sets — a file added or removed turns the census
red rather than passing over it. The data-row counts are a one-time
transcription of the committed tree that no check re-derives, so read them as
a record of this tree rather than as a figure something enforces. The
headers are transcribed, not paraphrased, because the point is what a reader
gets if they take row 0 for a header.

| file | header, on row | data rows | written by |
|---|---|---|---|
| `2026-09-09-profiles.csv` | row 0 | 162 | nothing in this tree |
| `2026-09-09-threshold80.csv` | row 0 | 6 | `linux/battery-trace/battery-trace` |
| `2026-09-17-limit-pair.csv` | **row 1** | 171 | `linux/battery-trace/limit-pair-test` |
| `2026-09-18-windows-stationary.csv` | row 0 | 416 | `battery_trace.py` |
| `2026-09-19-windows-bios-defaults.csv` | row 0 | 185 | `battery_trace.py` |
| `2026-09-21-0522-follow.csv` | row 0 | 8 | `charge_target_test.py` |
| `2026-09-21-0522-holdcheck.csv` | row 0 | 3 | `charge_target_test.py` |
| `2026-09-21-0522-stick.csv` | row 0 | 11 | `charge_target_test.py` |

Seven of the eight counts are the file's line count less its one header. The
eighth is not, and the section on that file below is why: its 201 lines are 171
data rows, a header, five `#` annotations and 24 `ecmem.py` write
confirmations, and a count that skipped the header and the `#` lines but
nothing else would put those 24 under *data rows* and report 195.

```
2026-09-09-profiles.csv         ts,ac,status,capacity,charge_now,current_now,voltage_now,profile,ec_hex
2026-09-09-threshold80.csv      ts,ac,status,capacity,charge_now,current_now,voltage_now,thr,r7b9,r7a6
2026-09-17-limit-pair.csv       ts,phase,ac,status,capacity,charge_now,current_now,voltage_now,mem7b9,mem7d0,regmap7b9
2026-09-18-windows-stationary   ts,phase,ac,charging,capacity,remaining_mwh,wmi_rate_mw,ec_current_ma,ec_voltage_mv,ec_07a6,ec_07b9,ec_07d0,ec_07d1,ec_07cc
2026-09-19-windows-bios-defaults  ts,phase,ac,charging,capacity,remaining_mwh,wmi_rate_mw,ec_current_ma,ec_voltage_mv,ec_07a6,ec_07b9,ec_07d0,ec_07d1,ec_07cc
2026-09-21-0522-*.csv           ts,phase,t_s,target_written_mv,target_readback_mv,held,requested_mv,ec_current_ma,ec_voltage_mv,profile_07a6,gate_0490,ac,charging,capacity,remaining_mwh,wmi_rate_mw
```

The `2026-09-21-0522-*` header is the charge-target tool's and is pinned by
`test_charge_target_test.py` against its own copy of it. This page does not
repeat that; the row above names the three so a reader of this directory knows
what the other tool owns.

**The two `battery_trace.py` captures are not one long run each.** `--phase`
is a per-run label (`battery_trace.py:73-74`), so a phase that changes *inside*
one file can only come from a second invocation appending into it:
`2026-09-19-windows-bios-defaults.csv` runs `biosdefaults_nohdmi_stationary` to
file line 132 and `cv88_switch_to_highcap` from 133 to the end, and
`2026-09-18-windows-stationary.csv` carries five phases, two of which
alternate row by row from line 105. So the `phase` column is what separates
the invocations *inside* a file that has only one header, and the row counts
in the table are the total across all of them rather than one run's. That
makes the column load-bearing for reading either file, and it is why the
append guard below has real committed runs behind it.

### The drift is not dead designs

**The natural reading of that table is wrong for two of its rows.**
`2026-09-09-threshold80.csv` and `2026-09-17-limit-pair.csv` look like captures
on shapes the repository has since stopped producing, which would make them
archive and the question closed. They are not archive. `linux/battery-trace/
battery-trace:16` `echo`s the former's ten columns **byte for byte** and
`linux/battery-trace/limit-pair-test:22` names the latter's eleven in its
`HDR=`, both committed, neither superseded.

The drift is not a supersession. The two shell scripts predate
`battery_trace.py` and were never replaced by it — all three are in the tree
today, and `battery_trace.py` is the Windows counterpart rather than the
successor of either. What happened is that a new capture shape was added
alongside the old ones and only the new one got a test.
`limit-pair-test:17` defaults into a directory no committed check validated
until this write-up added one, which is the next paragraph's point.
`battery-trace:9` does not: it hardcodes
`OUT=/var/log/battery-trace/trace-threshold.csv` and takes no argument, so
`2026-09-09-threshold80.csv` sitting in this directory is a copy brought here
from there by a route the tree does not record. What the script is evidence
of is the header, which it emits byte for byte — not the copy.

`2026-09-09-profiles.csv` is the one row with no writer. Its `profile,ec_hex`
tail appears nowhere outside the file itself, so the shape that produced it is
**not found by this method** — the search was the tree, and a script that was
never committed, or was renamed out of it, would look the same.

`limit-pair-test:17` is the consequence worth stating plainly:

```sh
OUT=${1:-evidence/battery-traces/$(date +%F)-limit-pair.csv}
```

Run with no argument it writes a dated capture into this directory. So a human
at the machine running the procedure this repository documents today produces a
file that the census in `test_battery_trace.py` rejects until somebody
classifies it. That is the intended behaviour, not an inconvenience: the
alternative is a check that only ever reads the files it was written against.

`2026-09-17-limit-pair.csv` is also the one file here that is not
header-first, and the only one here with a row that is not on its header's field
count: 29 of its 201 lines are single-field. Five are the operator's
annotation. Row 0 is `# original: 0x07b9=0x00 0x07d0=0x00 `, written by the
script before the header, and four `# charge_types=…` rows are interleaved
*through* the data at lines 94, 115, 136 and 159, each recording which charge
profile the operator had selected — hand-added, since nothing in this tree
writes that line. The other 24 are `ecmem.py`'s own write confirmations,
`0x07b9: was 0x00 wrote 0x3c readback 0x3c` and one line per register, which
the three `$ECM write … >> "$OUT"` redirects in `limit-pair-test`'s phase
sequence put straight into the capture; that is `ecmem.py:56`'s format rendered
exactly.
A `csv.reader` returns every one of the 29 as a single-field row, the shape a
data row with fields missing would also take. So the file is annotated both
before and inside its own row stream, and
`test_charge_target_test.py`'s
`test_the_committed_0522_traces_share_that_header` — which reads row 0 with
`next(csv.reader(...))` — could never have been pointed at it. The suite records
the row-1 header and the leading `#` rather than skipping the file, because a
glob that passed over it would report what it read and mean less than it said.

## The append guard

Every tool that writes here opens the file for append and decides about the
header separately. Four writers, and now two questions asked of them — is the
file empty, and is the header already in it one of ours:

| writer | the guard | what it asks |
|---|---|---|
| `battery_trace.py:83-86` | `if fh.tell() == 0` | is the file empty |
| `battery_trace.py:101-110` | `if found != ",".join(cols)` | is the header already in it ours |
| `charge_target_test.py:154-157` | `if fh.tell() == 0` | is the file empty |
| `linux/battery-trace/battery-trace:15-17` | `if [ ! -s "$OUT" ]` | is the file non-empty |
| `linux/battery-trace/limit-pair-test:39-51` | `if [ "$have" != "$HDR" ]` | is the header already in it ours |

**Two of the five now compare; the other three do not.** `battery_trace.py`
used to be a fourth "no" in this table: it appended a row of fourteen
current-shape columns to a file whose header is `2026-09-17-limit-pair.csv`'s
eleven, and reported exit 0. Column 4 is `status` in one and `charging` in the
other, so a reader that indexed by the file's own header read the wrong field
out of every row added. It refuses now, and `limit-pair-test` — which had no
guard at all, appending its `#` line and header on every run — compares before
it writes. `charge_target_test.py` and `linux/battery-trace/battery-trace` are
named in this table and are **not** covered by this work; they carry the same
gap and have their own follow-up.

Both refusals share one rule: a header that **matches** still appends, and only
a mismatch refuses. That direction is the evidence — `battery_trace.py`'s two
committed captures are each several invocations appending into one file, and
`limit-pair-test`'s `OUT` default is dated, so a same-date second run is a
continuation rather than a collision. Refusing it would have broken a workflow
the tools' own defaults invite.

Two things are *not* claimed here. That this has corrupted a committed file:
it has not, and **no file in the directory carries a data row on a column set
other than its own header's** — which is exactly the damage an append to a
mismatched header causes, and none of them shows any. That is a reading of the
committed tree rather than a check that re-derives it: the census holds every
file to the column set its class claims, which is a property of row 0, and the
29 single-field rows above are non-data lines rather than rows on a foreign
column set, so nothing in the suite walks every row. And that the guard was the
defect: each guard was doing what it was written to do. The gap was that nobody
wrote the check that was not there.

`2026-09-17-limit-pair.csv` opens with a `#` annotation rather than a header, and
the two guards read row 0 differently, so what happens when that capture is
pointed at is worth stating per tool rather than as one rule.
`battery_trace.py` compares the raw first line, so it refuses the file on the
annotation. That is the intended direction for that tool and not an oversight: a
compare that skipped annotation lines could be walked past by a file carrying
one, so its rule is deliberately the strict one, and its suite asserts both
shapes — an annotation-first file, and a file whose row 0 is a foreign header.
`limit-pair-test` compares the first line that is *not* a `#` row, so pointed at
this capture it finds the script's own header, matches it, and appends. That is
the correct outcome rather than a hole: the file is the shape the script writes,
so appending to it continues a capture instead of interleaving into it. The
skip is not a general rule — it is there because this script is the thing that
writes `#` rows — and the stricter reading stays held over the Python tool.

`2026-09-17-limit-pair.csv` is a **single run**: it has exactly one `# original`
line and one header, and neither appears twice. So there is no committed
evidence either way about what a second run of the new guard would produce —
the continuation path is asserted in `battery_trace.py`'s suite (case 9) and
reasoned about for the shell script, but no committed capture records two runs
of `limit-pair-test`. The non-data rows that single run produced are the
`$ECM write` confirmations counted above — the four `# charge_types=` rows are
hand-added. The `2026-09-21-0522-*` files are on the guarded path, and each
carries one header line.

## The two-source property, at the row level

The tool's docstring gives the reason it exists:

> Requiring both to agree before calling a stop is what keeps a cache artefact
> from being written up as an enforced charge limit.

`docs/findings.md` §4a is the retraction that makes this worth a test: a
`capacity` reading and a resting `voltage` were read as proof of an enforced
cap, and the pair of readings that does answer the question is the one §4i names
`battery_trace.py` as logging — `ec_current_ma` from EC `0x0434`/`0x0435` and
the ACPI driver's `wmi_rate_mw`, side by side, because there the gauge read
100% while the **rate/current** column showed the charge had actually stopped at
86% and `capacity` was still climbing. §4a is a retraction and stays exactly as
it stands; nothing here edits it or revises its reading of the committed
traces.

What had no test was the row-level property: that a row carries *both* readings,
each from its own source, and that neither has been derived from the other. The
suite's fixture is the first data row of
`2026-09-19-windows-bios-defaults.csv`, and the assertion is that the row the
tool builds from a byte map and a canned WMI line reproduces that committed row
field for field past the timestamp — 1700 mA little-endian from `0x0434`/`0x0435`
against the ACPI driver's 27992 mW, read from two places and agreeing with
neither. A tool that logged one current twice would satisfy nothing here.

The endianness is under test and not assumed: the expected `u16` is worked out
from the two fixture bytes in the suite rather than by calling the tool's own
`u16`, so a big-endian read fails on the value instead of agreeing with itself.

## What this does not settle

- **That either refusal has been seen to fire on real hardware.** Neither tool
  was run. `battery_trace.py`'s refusal is asserted against a temp file built
  from committed text, and `limit-pair-test` needs root, `ec/tools/ecmem.py` and
  `/sys` to run at all. Its guard was checked **by hand** while this was
  written — `bash -n` on the script, and the compare driven against a copy of
  the committed capture and against a header of another shape. That is a shape
  check, not an execution of the script, and **nothing in the tree repeats it**:
  no gate covers a file with no extension and no suite runs the script, so a
  later edit to that guard is unchecked until someone drives it by hand again.
  The continuation path (a header that matches, so the append proceeds) is
  asserted for `battery_trace.py` and reasoned about for the shell script; no
  committed capture records two runs of `limit-pair-test`, so that direction
  rests on the dated `OUT` default and on nothing observed.
- **That the suite holds a process exit code.** It asserts `main()`'s return
  value, because the tool imports `ecrw` and shells out to powershell and so
  cannot be run as a subprocess here; `sys.exit(main())` is what turns the
  refusal into a non-zero exit, and that line is not under test.
- **Whether the EC acted on any of it.** The suite opens no EC. The `ec_07xx`
  watch columns are asserted to be `WATCH`, in order, and to match what the
  committed captures recorded — that is a statement about a column set, never
  about a register's behaviour. `BAT_CURRENT_MA` and the charge-limit registers
  keep whatever `status:` `ec/annotations/registers.yaml` records.
- **That these are the right files to hold.** The census asserts that every
  file in the directory is classified and that no file is claimed twice. It
  does not assert that the directory should hold them, and it does not
  re-derive any of them. `2026-09-09-profiles.csv`'s absent writer is recorded
  above, not resolved.
- **The `encoding=` question.** ~~`battery_trace.py:81` opens a CSV with no
  `encoding=`~~, named as a deliberate deferral with its own follow-up at
  [`0751-capture-encoding.md`](0751-capture-encoding.md) §2 and repeated in its
  §9. This page does not re-open it and does not duplicate that page's
  reasoning; the overlap is this one line and nothing else.
  **Corrected 2026-10-03 at issue #1277:** the first sentence is no longer
  true — `battery_trace.py` declares `encoding="utf-8"` at its `open()`, as do
  `charge_target_test.py` and `ctgp_dben_probe.py` and every reader of all
  three formats. See [`probe-csv-encoding.md`](probe-csv-encoding.md). The
  rest of the bullet stands: this page still does not re-open that page's
  reasoning, and the two still overlap by that one line. The append guard added
  afterwards opens the `--csv` path a second time to read the header back, and
  that read declares the codec too — so `check_probe_csv_encoding.py` holds it
  as a *reader* site, keyed on the mode argument so it cannot be mistaken for
  the appender. That is a reader of an existing capture, not a fourth appender,
  and it is why the deferred question above stays deferred.
- **The duplicated `wmi()`.** `battery_trace.py:59-63` and
  `charge_target_test.py:89-93` are byte-identical, as are `PS`, `WMI_QUERY` and
  `u16`. The house position, at the same page's §2, is that `windows/tools/` is
  copied onto a box as a directory and the duplicate is deliberate. This suite
  fakes the call locally and asserts nothing about the two bodies being equal,
  so whatever the charge-target work does to that helper applies here without
  this suite blocking it.
- **The append gap, fixed.** ~~It is recorded, tested as today's behaviour, and
  left.~~ `battery_trace.py` wrote both current captures and every row in them
  went through the append path, so the path is not what is untested. What no
  committed run does is *append to a file whose header differs from `cols`*,
  and that narrower case is all a refusal would change — and no committed file
  records such an append either, so a cloud runner has no evidence to check
  the refusal against. Test 10 holds today's behaviour there. Its own issue.
  **Closed:** that was its own issue, and this is it. Both tools refuse on a
  mismatched header, and test 10 — `test_appending_to_a_foreign_header_
  interleaves_it_anyway`, which held the damage — now asserts the refusal
  instead. The reasoning above about there being no evidence to check against
  was right and is why the refusal is asserted as a property of the tool rather
  than read off a capture. What the refusal does **not** establish is stated
  under What this does not settle below.
- **Anything about the `2026-09-09-*` and `limit-pair` designs.** They are named
  and classified, not re-run and not re-derived. Re-deriving a shape would mean
  building the tool that produced it, which this work has no mandate to do.

## Nothing here was run against hardware

No laptop and no Windows machine is reachable from a GitHub-hosted runner. Every
value in the suite's fixture is a byte taken from a committed row or a token
from a canned WMI line; the two Linux scripts above are read as text and never
executed — `limit-pair-test`'s guard included, which needs root, `ecmem.py` and
`/sys` to run for real. The offline proof is:

```
    bash tools/run-tests.sh windows/tools/test_battery_trace.py
```

Scoped to the one suite because that is what this work changes;
`bash tools/run-tests.sh windows/tools` covers the same suite and the ones that
share its fixtures, and is green on this tree.

No gate runs that. `.github/scripts/agent-gates.sh` is copied from
`ElDavoo/agent-pipeline` and a branch cannot edit it; `tools/run-tests.sh` prints
on every run that no workflow calls it, and `docs/agent-pipeline.md` carries the
line that would. `check_python_syntax` in that gate does `py_compile` the
`windows/tools/*.py` glob, so the suite is known to compile and is not known to
pass from a commit. It does **not** cover the shell script — `check_shellcheck`
globs `find . -name '*.sh'` and `limit-pair-test` has no extension — so
`bash -n linux/battery-trace/limit-pair-test` is the syntax check this work
relies on, run by hand.
