# The three probe appenders declare `utf-8`, and `evidence/battery-traces/` is now measured rather than excused (issue #1277)

[`0751-capture-encoding.md`](0751-capture-encoding.md) §2 named three appenders
it left out on purpose and §9 deferred them as "same gap, different column sets,
a follow-up in their own right". This is that follow-up. `battery_trace.py`,
`charge_target_test.py` and `ctgp_dben_probe.py` each declare `encoding="utf-8"`
at their `open()` now, every reader of all three formats declares it too, and
`ec/tools/check_probe_csv_encoding.py` measures the population
`check_capture_encoding.py` does not cover.

**Nothing was broken.** Every committed capture in both directories is pure
ASCII, carries no BOM and decodes as UTF-8, measured over the bytes and
re-derived by the tool below. This is about the next capture.

**Nothing here ran on the laptop or on Windows.** No EC was opened and no
register was read. What a stock Windows Python would have written through these
three `open()` calls stays a prediction from the documented default; a human at
the machine confirms it if they want to.

## 1. What was measured

`python3 ec/tools/check_probe_csv_encoding.py`, run from the repository root.
The corpus half's summary line, from the high-byte figure on; the capture count
it opens with counts this repository's own committed files, so it is not
written here:

```
… 0 with a high byte, 0 with a BOM; each read under the declared
utf-8 and under this interpreter's default (UTF-8), and the two compared
  note: this runner's default is already utf-8, so the two reads are the same
  read here and the agreement column is weak evidence on this machine. The
  strong claim on it is that every capture decodes as utf-8 -- which is what
  declaring any other codec would have broken.
```

Those figures are this run's, over whatever is on disk today. Re-derive them
with that command; nothing here holds them to a fixed value, and a new capture
lands without editing this page.

**No capture in this population carries a byte above 0x7F.** That is a
measurement over the files on disk today, and it is what shapes the rest of the
page: `check_capture_encoding.py`'s corpus does carry high-byte captures to
compare two reads over, and this one does not, so on this corpus the `agrees`
column is trivially `yes` for every file and the disagreement branch is held by
the tool's own fixtures and by a C-locale child process rather than by
anything committed. §4 says why that is a property of the formats rather than a
coincidence — and, for one of the three, a property stronger than "not yet".

## 2. The three writers, and the line-neutrality rule

| file | the call | what it opens |
|---|---|---|
| `battery_trace.py` | `open(args.csv, "a", newline="", encoding="utf-8")` | a `ts,phase,...` capture |
| `charge_target_test.py` | the same call | a `ts,phase,t_s,...` capture |
| `ctgp_dben_probe.py` | the same call | a `ts,mark,t_s,...` capture |

Each edit is a same-line replacement: **no line was inserted or removed in any
of the three files**, which is the whole of the constraint. `battery_trace.py:51`
is pinned by `ec/ghidra/xdata-overrides.csv:9`, `battery_trace.py:81-84` and
`charge_target_test.py:154-157` are pinned in
[`battery-trace-column-drift.md`](battery-trace-column-drift.md)'s append-guard
table, and `0751-capture-encoding.md:117-118` pins all three. ~~The three files'
line counts are unchanged, so every one of those citations still resolves to
the line it was written for.~~

> **Corrected 2026-10-04, by issue #1203.** The claim above was true of *these*
> edits and stopped being true of `battery_trace.py` afterwards: the append
> guard added later grew the file by 26 lines, so its line count is no longer
> what it was when this page was written. Every citation named here still
> resolves, for the reason the guard is placed the way it is — it sits **below
> line 84**, so `battery_trace.py:51` and `battery_trace.py:81` still carry the
> text they are written for, and `charge_target_test.py` and
> `ctgp_dben_probe.py` were not touched at all. What did move is the
> append-guard table's own row: it now reads `battery_trace.py:83-86` rather
> than `81-84`, because the guard is the `else` of the same `fh.tell() == 0`.
> The constraint held where it was aimed — above the cited lines — and the
> correction is recorded rather than the sentence rewritten, per the §4a-4d
> pattern. See [`battery-trace-column-drift.md`](battery-trace-column-drift.md)
> for the guard itself.

There is no explanatory comment above the `open()` in any of the three, and that
is deliberate: a comment inserted above `battery_trace.py:81` moves every pin
below it. The reasoning is this page, which is where this repository puts it.
`battery_trace.py`'s append guard is below that line for the same reason, and
carries its reasoning in the code where it is read.

## 3. Who reads each format

The broader reading, not the two sites the issue named: closing the writers and
leaving most readers on the inherited default would declare half a format.

| format | its readers | how they read |
|---|---|---|
| `ts,phase,...` | `test_battery_trace.py` | `(TRACES / name)`, `(TRACES / LIMIT_PAIR)` and `path` `read_text()` |
| `ts,phase,t_s,...` | `test_charge_target_test.py` | `path` and `trace` `read_text()` |
| `ts,mark,...` | `test_ctgp_dben_probe.py` | `path` `read_text()` |

Those are the anchors `check_probe_csv_encoding.py`'s `DECLARATIONS` names, so
the two cannot drift apart silently: an anchor that stops matching is the
checker's own "no call matching" problem.

**The `read_text()` calls in those suites that read *source* rather than a
capture are deliberately not in that table.** The undeclared ones are
`test_battery_trace.py`'s reads of the `battery-trace` and `limit-pair-test`
scripts and `test_ctgp_dben_probe.py`'s `registers.yaml` read; the reads that
take a tool's own source, the ctgp suite's other source reads, and every
capture read all declare `encoding="utf-8"`. Naming the exclusion is the point —
the checker would otherwise be a claim about every `read_text()` in those files,
which it is not — and
`ec/tools/test_check_probe_csv_encoding.py` holds that classification against
the tree rather than this page holding a tally of it. A count of them here
would be stale the next time a suite reads another committed file.

The reader's side is what makes the declaration a *format* rather than a
writer's habit: a capture a Windows box wrote as `cp1252` is refused by a
declared utf-8 reader on a machine whose locale is not utf-8, and no reader
that inherits its locale can be relied on to notice.

## 4. What each format can put on disk

The reachability split is the part worth having, because it is why §1's zero
is not an accident waiting to happen in all three.

**`battery_trace.py` and `charge_target_test.py` have a live path to a byte
above 0x7F.** Both write `args.phase` — operator-supplied free text, a
`--phase` label — into column 1 of every row. `§` in a phase label is the
likeliest non-ASCII character a person types at a box, which is why
`check_capture_encoding.py` chose it as its probe. `test_battery_trace.py` and
`test_charge_target_test.py` each drive exactly that through `main()` into a
temp file and assert the bytes on disk: no BOM, decodes as utf-8, and `0xA7`
never standing alone (which is the byte a one-byte-per-character writer would
have spent on `§`).

**`ctgp_dben_probe.py` has no such path, and this is stronger than "yet".**
Its `mark` column is drawn only from the fixed `ARMS` tuple; every other field
is an ISO timestamp, a `0x%02X`, or a small int. There is no `--phase` and no
operator-supplied label in that format at all, so no column of it has a route
to a byte above 0x7F. `test_ctgp_dben_probe.py` holds the ASCII part of that —
it asserts `probe.COLS` and `probe.ARMS` are ASCII-encodable, which is what
makes the claim checkable rather than a note — and asserts the file a real run
produced is utf-8-decodable and BOM-free.

That structural claim is about this tree's constants. It is a test, so a future
edit adding a non-ASCII column turns it red, which is the point of holding it
rather than asserting it in prose.

## 5. Why a second tool and not a wider `ROOTS`

The issue offered both: widen `check_capture_encoding.py`'s walk with a per-shape
rule, or record why the second column set is out of its population. The second
option is what §5 of that page's argument leads to, and it is taken here — but
as **more than a note**, because "the directory is out of scope" is exactly the
state that let a third committed capture tree accumulate with no encoding
coverage at all.

Concretely, `check_capture_encoding.py`'s `count()` applies the
`ts,addr,old,new` skip and the `MARK` rule, so its `marks`/`changes` columns are
its product *for that shape*. Widening `ROOTS` would put a "change rows" tally
against captures whose columns are not marks — replacing one wrong number with
another rather than adding coverage.

One more thing weighed: the plan for this issue assumed the widening would
break two live machine-checked pins in `measure_mark_provenance.py`. **That is
no longer true**, and the assumption is recorded here because a write-up that
quietly dropped it would leave the next reader with a stale reason. `resolve()`
now holds a citation to its quoted text rather than its line number, as of
2026-10-03, and the tool resolves both pins with the comment edit below in
place. So the argument for the second option is the one above and only that.

The edit to `check_capture_encoding.py` is comment-only and says the exclusion
in the tool itself, so a reviewer who disagrees has exactly one place to change
it. **No code in that file was edited** and its own suite is unchanged and
green, which is what shows the edit was code-neutral.

## 6. The check, and what it found

`ec/tools/check_probe_csv_encoding.py`, with
`ec/tools/test_check_probe_csv_encoding.py` beside it. Two halves, because they
are not the same kind of thing:

- **The corpus half** walks `evidence/battery-traces/` and `evidence/ec-watch/`,
  names each file's shape off its *header row* rather than its filename
  (`2026-09-21-0522-follow.csv` says nothing about what is in the file), reads
  each twice — once through the declared codec, once through this
  interpreter's inherited default — and compares the **whole decoded text**. A
  mark tally would not be a comparison for a shape whose columns are not marks.
  It reports a BOM, a capture the declared reader refuses, and two reads that
  disagree.
- **The declaration half** locates every site by a content anchor and asserts it
  carries `encoding="utf-8"` — not merely an `encoding=` keyword, because a
  site declaring `utf-8-sig` has the keyword and is exactly the failure
  `0751-capture-encoding.md` §3 argued against.

`evidence/ec-watch/` is walked too, so the ctgp capture that
`docs/hardware-tests/ctgp-dben-07c4-bit3.md` §6 sends there is covered by the
day it lands. No capture of that shape is committed today, so what the walk
finds there now is its absence.

Every site is found by an anchor and never by a line number. That is not
stylistic: `battery_trace.py` carries a live pin at `:51`, and a check holding
a line would have to be re-anchored by the next merge that grew the file above
it.

**What it found:** the site table is fully declared and the corpus is clean. Its
suite is what makes that worth anything — one case per problem branch, each
asserted to be named by the path it was found at, plus the sharpness case where
a good capture sits in a broken tree and must not be named.

## 7. What this does not settle

- **What a stock Windows Python writes.** A codec is a property of the Python
  that writes, so what is under test here is what these scripts now *ask* for.
  Whether a cp1252 Windows box would have written `§` as a single `0xA7` stays
  a prediction from the documented default. The `§` round-trips run on a Linux
  runner with `ecrw` stubbed and would pass on a utf-8 interpreter with no
  declaration at all — which is why the declaration cases, not those, are the
  ones that can go red.
- **The two shell writers.** `linux/battery-trace/battery-trace` and
  `limit-pair-test` also land captures in `evidence/battery-traces/`, and a
  shell redirection has no `encoding=` to declare. Their files are in the
  corpus half because they are committed; no claim is made about how they
  handle a byte above 0x7F.
- **Whether this format should ever accept a BOM.** The separate question
  `0751-capture-encoding.md` §9 names.
- **The append-guard gap.** ~~None of the four writers compares the header
  already in the file with the columns it is about to write, which
  `battery-trace-column-drift.md` records and deliberately leaves open.~~
  Closed for two of them at issue #1203: `battery_trace.py` and
  `limit-pair-test` now compare the header already in the file and refuse a
  mismatch, which leaves `charge_target_test.py` and
  `linux/battery-trace/battery-trace` still carrying it, as that page records.
  Encoding is not that gap, and fixing one does not fix the other — the guard
  adds no codec question, and the header read it needed declares `utf-8` like
  the appender.
- **The two shells' and `2026-09-09-profiles.csv`'s provenance.** The absent
  writer is recorded as *not found by this method* at
  `battery-trace-column-drift.md`; it is not re-opened here.