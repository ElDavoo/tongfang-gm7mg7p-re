# A `Usage:` line that reproduces its table, and a note for the diff a reader writes instead (issue #1020)

`ec/tools/trace_xdata_refs.py`'s `Usage:` block gave six example invocations and
never named `--terminator-column`, which the module docstring describes in its
third point and which `--csv` needs to reproduce a committed sites table. The
flag is optional, so nothing complains: a reader who takes the natural command
from the block gets a table one cell short per row, exit 0, and empty stderr.

The tool already knew the shape. Where `--check` is given it reads the committed
header, and if that header carries a `terminator` column and the flag was not
passed, it says so on stderr. **That note is on the `--check` path only** — and
the `| diff -` command a reader actually writes hands the tool no file to read a
header out of, so the one direction that needed saying had no way to say it.

The other direction was never the problem: the same comment calls it, and it is
right. A run that produces *extra* cells is explained by the diff. A run
producing *missing* ones is a diff that looks identical to a genuine content
change, which is why this one needed a note and that one did not.

## The failure, re-measured on committed inputs

No hardware, no Windows, no Ghidra. `python3` and the committed 256 KiB image.
**The transcript below was measured before this change**, which is the state it
describes. At the commit this write-up lands on, the same command *also* prints
the new note on stderr, and *Reproducing it* runs it again as it is now:

```sh
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0751 --csv \
    | diff - ec/annotations/manual-fan-ctrl-0751-sites.csv
1,30c1,30
# all 30 lines replaced, exit 0, stderr empty
```

One cell short per row and nothing on stderr. The flag fixes it:

```sh
$ (cd ec/tools && python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 0x0751 \
    --csv --terminator-column | diff - ../annotations/manual-fan-ctrl-0751-sites.csv)
# exit 0, no output
```

**The line numbers in the issue are from an older revision.** At the commit this
was written against, the `Usage:` block is the last thing in the module docstring
and the `--check` note is in the `--csv` branch of `main()`. The content matches
the report in every particular, so the finding stands; the code is located here
by the quoted text rather than by the number in the issue.

## Half one: the `Usage:` line, which is the whole finding

A usage block is the only surface a reader reaches before running anything. The
omission costs nothing until a reader diffs — and then it costs a diff failure
that has nothing to do with the change being verified. So the block now carries
one line:

```
python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 0x0751 --csv --terminator-column | diff - ../annotations/manual-fan-ctrl-0751-sites.csv
```

Three choices in that spelling, each of which would have taught a command that
does not work if it went the other way:

- **The `| diff -` form, not `> sites.csv`.** The block already teaches the
  generation case, where the flag is *not* wanted; the case that bites is a diff
  against a committed table, and the pipe is the spelling
  `walk-window-terminators.md`'s reproducing section already prints six times.
- **`0x0751`, not `0x0860`.** The 0x086x table carries a `census` column and no
  `terminator` one, so an example pairing the flag with `0x0860` would teach a
  command that does **not** reproduce its committed table — the defect, inverted.
- **One line, not two.** A second `--check` pairing was not asked for and would
  add a second address-to-table mapping to maintain.

`ec/tools/test_trace_xdata_refs_usage.py` holds the general form, so this cannot
regress silently: **every option the parser declares must be named in a
`Usage:` line**, and every `Usage:` line is run as written. A flag added without
an example is red there, which is the defect and forward.

The check is deliberately over the `Usage:` slice and not the whole docstring.
The docstring names `--terminator-column` above the block, in its third point,
so an assertion over the whole of it would have stayed green on the file
exactly as it was — a passing test that proved nothing about the omission. The
suite asserts that distinction directly, by feeding the same predicate a block
with the line removed and requiring it to report the flag.

## Half two: the note, and the reading I took

**The issue's literal second ask is not implementable, so this substitutes a
computed trigger and says so here.** The `--check` condition is a fact about
*the file the reader is diffing against*, and on the `| diff -` path the tool
does not have that file — "extend the condition" has nothing to extend it
*with*.

**The rejected alternative was an unconditional note on any bare `--csv` run.**
It would fire on `… 0x07D0 --csv > sites.csv`, which is exactly right without
the flag, and on `… 0x0860 --csv --census-column`, whose committed table has no
`terminator` column at all. A tool that says "every row is short that cell" to a
correct run is the overclaim this repository's calibration rule exists to
prevent, and it would be muted within a week.

**The substitute computes the trigger instead of typing it.**
`committed_terminator_tables()` takes the annotations directory and the requested
addresses, and returns the committed tables under `ec/annotations/` whose header
carries `terminator` **and** whose `addr` column already has a row for **every**
requested address. The note fires when `--csv` is on, `--terminator-column` is
off, and `--check` is off:

```
note: ec/annotations/manual-fan-ctrl-0751-sites.csv carries a `terminator` column
and covers 0x0751; a diff against it needs --terminator-column, and this run did
not pass it, so every row is short that cell.
```

Read that wording against what it is not allowed to say. It is a fact about the
committed tree, and it does not tell the reader the run was wrong — a reader
writing a fresh `sites.csv` is doing the right thing. Where the method cannot
tell, it says nothing: an address in no committed table, an address in a table
with no `terminator` column, or **one address covered and another not** all
produce silence. A scan that located nothing never reads as "nothing is wrong",
and the suite holds the fires and the does-not-fire directions as separate cases
because the second is the half that decides whether the advice gets read.

Three properties make it cheap and safe:

- **The tables are found by a scan and never listed.** A seventh committed table
  carrying the column needs no edit to `committed_terminator_tables()` or to any
  test. The census below is a measured run with its command beside it, not a
  figure any later change has to update.
- **The column test is exact membership, not a substring.**
  `walk-budget-census.csv` carries `terminator_at_budget` and
  `terminator_at_extend`; a substring test over the joined header would fire
  on it and name a cell the file does not have. The test is membership in the
  header list, so it does not.
- **The whole scan is skipped whenever `--check` is given**, which the issue
  requires. On that path the old note is the only one that prints, and
  `test_trace_xdata_refs_usage.py` asserts the old note appears exactly once
  with the new one absent — "suppressed rather than doubled", as the issue puts
  it, asserted rather than trusted.

### The scan's output, over the committed tree

The nine committed tables this tool's `--csv` output reproduces, measured by
reading each header (the producing command is in *Reproducing it*):

| committed table | addresses | column past `window` | `terminator`? |
|---|---|---|---|
| `ec-07c4-07d5-sites.csv` | 4 | `terminator` | **yes** |
| `ec-07d6-07d7-sites.csv` | 2 | `terminator` | **yes** |
| `ec-09e9-09eb-sites.csv` | 3 | (none) | no |
| `ec-0x07d0-sites.csv` | 1 | `terminator` | **yes** |
| `ec-0x07d1-sites.csv` | 1 | `terminator` | **yes** |
| `manual-fan-ctrl-0751-sites.csv` | 1 | `terminator` | **yes** |
| `xdata-0400-045f-sites.csv` | 57 | `terminator` | **yes** |
| `xdata-086x-dispatch-sites.csv` | 15 | `census` | no |
| `xdata-1c3x-consumers-sites.csv` | 11 | (none) | no |

Six carry the column and three do not, which is exactly the premise of the
issue's note — and the three that do not are why an unconditional note would be
wrong for three of the nine committed tables this tool reproduces. The
`addresses` column is what makes the "every requested address" rule necessary
rather than decorative: `xdata-0400-045f-sites.csv` covers 57 addresses, so a
reader asking for one of them and one other thing gets a table with no committed
counterpart at all.

**Six is a measurement, not a constant.** The scan holds no list of them, so
the table above is a transcript of a run rather than a list anything maintains.
The figure *is* written down in two places, both prose in
`trace_xdata_refs.py` and both predating this issue — a line of
`csv_table()`'s docstring, and the comment over the `--check` note below it.
They record what was true where they were written, no code reads either, and a
seventh table makes one of them stale without breaking anything. Only the scan
has to stay list-free, and the suite holds that by finding a table the scan
locates rather than by counting the tables it found. Re-cutting a table moves
the measurement and the test that would notice
is the one asserting that the note is *quiet* for 0x0860, which fails the day
that table grows the column.

## The stale sentence this makes false, corrected in place

`descend-index-guard.md`'s *Reproducing it* section said:

> **Both flags are load-bearing, and one of them is not in the tool's own usage
> list** — `trace_xdata_refs.py`'s `Usage:` block lists `--census-column` and
> `--check` but never `--terminator-column`, so the natural command omits it and
> the sites table comes out a column short.

The claim was true and the consequence is now wrong. That file is corrected
where the sentence is rather than here alone, per `docs/findings.md` §4a-4d, and
the fenced commands below it are byte-identical: the flag was always needed
there and the reproduce command still works as printed, which is the issue's
"the reproduce command has to work as printed" and is a different question from
whether the flag is discoverable.

## Two things the new suite found, neither fixed here

**The `--check` example in the block does not reproduce its default table.**
`python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 0x0860 --csv
--census-column --check` asks for one address against the fifteen
`xdata-086x-dispatch-sites.csv` carries, so the run produces a header and the 9
`0x0860` rows — ten lines, and its diff reports the other 105 of that table's
114 data rows as not produced, exit 1. The `--check` invocation prints nothing
of its own on stdout: `check_table()` sends the verdict and the unified diff to
stderr, where the hunk reads `@@ -11,105 +10,0 @@`. This is the same
class of defect as the one this change fixes — a `Usage:` line a reader can copy
that does not do what it appears to do — and it is the reason the suite's
per-line contract is *runs and accounts for its own output* rather than a
blanket exit 0.

It is not fixed here, and the reason is the next item.

**`--check PATH` implies `--census-column`.** `main()` loads the census map
whenever `args.check is not None`, so `--check` against any table other than the
0x086x one emits a table with a spurious `census` column of `not recorded` and
reports rows differing that are in fact identical:

```sh
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0751 --csv \
    --check ec/annotations/manual-fan-ctrl-0751-sites.csv
# every one of the 30 lines replaced: the header, and 29 rows whose only
# differing cell is the trailing one, `terminator` against `not recorded`
```

A real defect, and the reason the `--check` example above cannot simply be
repaired: the only `--check` command that exits 0 today is the default one with
its full address set, and writing that set into the docstring is a
193-character line duplicating a list `walk-window-terminators.md` already
prints — a hand-kept list in a hot spot, which is the thing `CLAUDE.md`'s
no-hand-kept-totals rule is about. Fixing the census defect would let the
example name a short address set instead. It is out of scope here because it
changes the `--check` behaviour this issue explicitly freezes, so it is a
follow-up of its own with this reproduction attached. The suite deliberately
does not assert the exit code of that run, because pinning 1 would make the
census defect the expected behaviour.

## What did not change

- **No committed table.** All six `terminator` tables still reproduce byte for
  byte; the 0x086x `--check` still exits 0 and still says so. stdout is
  byte-identical to the pre-change tool on every `--csv` path, which the suite
  asserts by running the same command against a directory the scan finds nothing
  in and requiring the two stdouts to match.
- **No exit code moved.** A note is not a status.
- **No register claim.** `ec/annotations/registers.yaml` is untouched, and
  `docs/findings.md` is not edited at all, per its frozen rule: this file is
  the whole of the finding. It is reachable from `docs/findings/INDEX.md`, from
  `tools/README.md`'s row for the new suite, and from that suite's module
  docstring — and not from the tool's own docstring, which names the flag and
  the two terminator censuses but not this write-up.
- **No hardware, no Windows, no Ghidra.** Every command below reads a committed
  file. Nothing here is evidence about the EC.

## Reproducing it

From the repository root. No image beyond the committed 256 KiB dump, no
network, no assembler, and under a second for the whole set.

```sh
# the failure, then the fix, then the note
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0751 --csv \
  | diff - ec/annotations/manual-fan-ctrl-0751-sites.csv          # short, silent
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0751 --csv 2>&1 >/dev/null
# -> the note above
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0860 --csv 2>&1 >/dev/null
# -> nothing: that table has no `terminator` column

# the six `terminator` tables, byte for byte, and the 0x086x regression
# (walk-window-terminators.md's reproducing section prints all seven)
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07C4 0x07D3 0x07D4 0x07D5 \
    --csv --terminator-column | diff - ec/annotations/ec-07c4-07d5-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D0 \
    --csv --terminator-column | diff - ec/annotations/ec-0x07d0-sites.csv
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0860 0x0862 0x0865 0x0866 \
  0x0867 0x0868 0x0869 0x086A 0x086B 0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 \
  --csv --census-column --check

# the census above, read off the committed headers rather than carried forward
python3 - <<'PY'
import csv, os, sys
sys.path.insert(0, 'ec/tools')
import trace_xdata_refs as T
PREFIX = "addr,file_offset,region,runtime,frame_onto,frame_over,access,window"
for name in sorted(os.listdir(T.ANNOT)):
    if not name.endswith('.csv'):
        continue
    path = os.path.join(T.ANNOT, name)
    header = T.committed_columns(path) or []
    if ",".join(header[:8]) != PREFIX:
        continue
    rows = list(csv.DictReader(open(path, newline='')))
    addrs = {r['addr'] for r in rows}
    print(name, len(addrs), 'terminator' in header)
PY

# the suite, and the repository's own runner
python3 -m unittest discover -s ec/tools -p test_trace_xdata_refs_usage.py
bash tools/run-tests.sh ec/tools
python3 ec/tools/gen_findings_index.py --check
python3 ec/tools/check_findings_frozen.py
```

## Follow-ups this opens

1. **`--check PATH` implies `--census-column`**, with the reproduction above.
   Until it is fixed, the only `--check` command in the tool that exits 0 is the
   default one, which is why the block's `--check` example cannot name a short
   address set. Fixing it retires the other finding in this file's previous
   section at the same time.
2. **The block's `--check` example does not reproduce its default table.**
   Follows from (1); with the census defect gone it is a one-line edit naming
   `0x0751` and a path.
3. **A checker that every tool's `Usage:` block names every flag, run across
   `ec/tools/`.** This change fixes one instance and pins it, but the same class
   of omission is plausible in the other twenty-odd tools in that directory, and
   a general checker would find them all at once. That is a bigger finding than
   this issue and a new tool rather than a new case.
4. **Gate wiring for the new suite**, as a prepared
   `docs/ci/agent-gates-<name>.patch` for a human to land. Not absorbed here:
   `.github/scripts/agent-gates.sh` is copied from the `agent-pipeline` template
   and the push token has no `workflow` scope, so a branch editing it fails at
   the end of the PR rather than the start. `tools/test_agent_gates_patches.py`
   holds every patch against the committed gate script and checks they compose
   in any order, so it has to be a **new file** — editing a shipped patch breaks
   its context lines.
