# The battery trace's column set moved to a shell script, and the append guard never checked what it was appending to (issue #363)

The write-up for [issue
#363](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/363):
`windows/tools/battery_trace.py` had no offline suite, so its function-local
`cols` and its `WATCH` were held by nothing, and the column drift across
`evidence/battery-traces/` was unrecorded. Both are now held, by
`windows/tools/test_battery_trace.py`.

**The tool is not edited by this.** Two committed citations hold it by line
number — `ec/ghidra/xdata-overrides.csv:9` cites `battery_trace.py:51` for
`ADDR_CURRENT`, and [`0751-capture-encoding.md`](0751-capture-encoding.md)
cites `battery_trace.py:81` for the `open()` with no `encoding=`. Editing
above either line silently falsifies a citation and nothing would catch it, so
the deliverable here is tests and this page. Nothing below is hardware evidence:
no EC is opened, no register is read back, and no row in this directory was
produced by a run that happened now.

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
| `2026-09-17-limit-pair.csv` | **row 1** | 195 | `linux/battery-trace/limit-pair-test` |
| `2026-09-18-windows-stationary.csv` | row 0 | 416 | `battery_trace.py` |
| `2026-09-19-windows-bios-defaults.csv` | row 0 | 185 | `battery_trace.py` |
| `2026-09-21-0522-follow.csv` | row 0 | 8 | `charge_target_test.py` |
| `2026-09-21-0522-holdcheck.csv` | row 0 | 3 | `charge_target_test.py` |
| `2026-09-21-0522-stick.csv` | row 0 | 11 | `charge_target_test.py` |

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

### The drift is not dead designs

**The natural reading of that table is wrong for two of its rows.**
`2026-09-09-threshold80.csv` and `2026-09-17-limit-pair.csv` look like captures
on shapes the repository has since stopped producing, which would make them
archive and the question closed. They are not archive. `linux/battery-trace/
battery-trace:16` `echo`s the former's ten columns **byte for byte** and
`linux/battery-trace/limit-pair-test:24` `echo`s the latter's eleven, both
committed, neither superseded.

The drift is not a supersession. The two shell scripts predate
`battery_trace.py` and were never replaced by it — all three are in the tree
today, and `battery_trace.py` is the Windows counterpart rather than the
successor of either. What happened is that a new capture shape was added
alongside the old ones and only the new one got a test; the two writer scripts
emit into a directory nothing in the tree validates.

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
header-first. Row 0 is `# original: 0x07b9=0x00 0x07d0=0x00 `, written by the
script before the header, and four further `# charge_types=…` rows are
interleaved *through* the data at lines 94, 115, 136 and 159, each recording
which charge profile the operator had selected. So the file is annotated both
before and inside its own row stream, and
`test_charge_target_test.py`'s
`test_the_committed_0522_traces_share_that_header` — which reads row 0 with
`next(csv.reader(...))` — could never have been pointed at it. The suite records
the row-1 header and the leading `#` rather than skipping the file, because a
glob that passed over it would report what it read and mean less than it said.

## The append guard

Every tool that writes here opens the file for append and decides about the
header separately. Four of them, three different decisions:

| writer | the guard | what it asks |
|---|---|---|
| `battery_trace.py:81-84` | `if fh.tell() == 0` | is the file empty |
| `charge_target_test.py:154-157` | `if fh.tell() == 0` | is the file empty |
| `linux/battery-trace/battery-trace:15-17` | `if [ ! -s "$OUT" ]` | is the file non-empty |
| `linux/battery-trace/limit-pair-test:23-24` | none | nothing; it appends the `#` line and the header on every run |

**None of the four compares the header already in the file with the columns it
is about to write.** `battery_trace.py` appends a row of fourteen
current-shape columns to a file whose header is `2026-09-17-limit-pair.csv`'s
eleven, and reports exit 0. Column 4 is `status` in one and `charging` in the
other, so a reader that indexed by the file's own header reads the wrong field
out of every row added. The suite asserts today's behaviour and says in a
comment that the gap is unfixed; closing it turns that case red, which is the
record turning over rather than a defect in the fix.

Two things are *not* claimed here. That this has corrupted a committed file:
it has not, and each file above is internally consistent — checked by reading
them, and by the census holding every one to the column set its class claims.
And that the guard is the defect: the guard is doing what it was written to do.
The gap is that nobody wrote the check that is not there.

The one writer of the four with **no** guard is the interesting one, because it
is the one that would double. `limit-pair-test` appends its `#` line and its
header on every run, so two runs on one date would put a second header in the
middle of the file — and `2026-09-17-limit-pair.csv` has exactly one of each,
so the committed capture is a single run with four hand-added annotations after
it. The `2026-09-21-0522-*` files are on the guarded path, and each carries one
header line.

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
- **The `encoding=` question.** `battery_trace.py:81` opens a CSV with no
  `encoding=`, named as a deliberate deferral with its own follow-up at
  [`0751-capture-encoding.md`](0751-capture-encoding.md) §2 and repeated in its
  §9. This page does not re-open it and does not duplicate that page's
  reasoning; the overlap is this one line and nothing else.
- **The duplicated `wmi()`.** `battery_trace.py:59-63` and
  `charge_target_test.py:89-93` are byte-identical, as are `PS`, `WMI_QUERY` and
  `u16`. The house position, at the same page's §2, is that `windows/tools/` is
  copied onto a box as a directory and the duplicate is deliberate. This suite
  fakes the call locally and asserts nothing about the two bodies being equal,
  so whatever the charge-target work does to that helper applies here without
  this suite blocking it.
- **The append gap, fixed.** It is recorded, tested as today's behaviour, and
  left. Refusing a mismatched header is a behaviour change to a tool no
  committed run exercises, which makes it a change nobody can check from a
  cloud runner — its own issue.
- **Anything about the `2026-09-09-*` and `limit-pair` designs.** They are named
  and classified, not re-run and not re-derived. Re-deriving a shape would mean
  building the tool that produced it, which this work has no mandate to do.

## Nothing here was run against hardware

No laptop and no Windows machine is reachable from a GitHub-hosted runner. Every
value in the suite's fixture is a byte taken from a committed row or a token
from a canned WMI line; the two Linux scripts above are read as text and never
executed. The offline proof is:

```
    bash tools/run-tests.sh windows/tools
```

No gate runs that. `.github/scripts/agent-gates.sh` is copied from
`ElDavoo/agent-pipeline` and a branch cannot edit it; `tools/run-tests.sh` prints
on every run that no workflow calls it, and `docs/agent-pipeline.md` carries the
line that would. `check_python_syntax` in that gate does `py_compile` the
`windows/tools/*.py` glob, so the new suite is known to compile and is not known
to pass from a commit.
