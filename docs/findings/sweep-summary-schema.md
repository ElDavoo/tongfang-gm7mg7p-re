# The AC-plugin sweep summary has a schema, a reader, and two blind spots written down

Issue #316. The file this is about is
`evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv`, and the reader is
`ec/tools/grade_sweep_summary.py`.

**The correction first, because the issue's premise is wrong in a way this
repository has a rule about.** The issue reports that "no committed tool
writes or reads the summary format", citing `grep -rl
'first_old\|last_new\|change_count'` over `*.py`. That grep does not come back
empty. Three committed tools name this file's schema today:

- `check_capture_claims.py`'s `read_capture()` — its `derived = bool(rows)
  and "change_count" in rows[0]` (`:422 at aa97735a`) is the literal string
  the grep names, its `if derived:` arm (`:428 at aa97735a`) sums the
  `change_count` column per address, and its own docstring above both says
  what the format is: the summary is "a derived per-address summary, one row
  per address with the change total in a `change_count` column".
- `check_testdata_row_claims.py` imports `read_capture` from that tool by
  name rather than growing a second parser, and
  `ec/tools/testdata/capture-claims-example-ac-plugin-sweep-summary.csv` is a
  committed fixture of this exact shape, indexed in
  `ec/tools/testdata/README.md`.
- `fan_pair_correlation.py`'s `read_change_counts()` (`:434 at aa97735a`) has
  its own reader for this shape, reached from `SWEEP_SUMMARY` above it, and
  `read_change_counts` returns `{addr: change_count}` — the count column and
  nothing else.

**What survives is narrower, and it is the part that matters.** All three read
the **count column only** — and so did everything committed before this change,
which is the gap `grade_sweep_summary.py` below fills. That is a claim about a
tree rather than about the current one, so it is written against the commit
this branch is based on and the command is here to keep it checkable:

```console
$ git grep -n 'first_old\|last_new' aa97735a -- '*.py'
```

Every hit it returns is text: a comment and a docstring in
`fan_pair_correlation.py` naming the shape, and the four-column header line
that tool and its suite each write into a fixture of their own. None of them
indexes a row by either name. The same scan over `main` after this lands does
name `grade_sweep_summary.py`, and that is what "the first reader of the value
columns" means — the commit is in the command because the property is about
the tree it was measured on, not about whichever tree is checked out. That is
"not found by this method", the same caveat
`ec/annotations/registers.yaml` carries for a static scan — narrow here
besides, because these are four column *names* and a reader of the file has to
mention them to read them. So the issue's own argument about #277 — a
checker built on a lossy hand-made projection inherits the blind spot it is
meant to catch — is now evidenced by code rather than asserted, and the reader
below exists because that is true. #277's prose-claim checker is *not* pointed
at this file for the same reason.

## The schema

One row per address, four columns, under a `#` comment block:

```
addr,change_count,first_old,last_new
0x07C6,2,0x04,0x04
```

- `addr` — the EC address, four hex digits.
- `change_count` — how many times the watcher recorded a change to that
  address inside the window. This is a **derived total, not a row count**: a
  byte with 1,100 changes is one row.
- `first_old` — the byte's value at the pre-image of its **first recorded
  change**. Not necessarily its value at the window's first sweep.
- `last_new` — its value at the post-image of its **last recorded change**.

`#` lines are dropped before the header is read, by every reader in the tree;
`check_capture_claims.capture_lines()` is the one that says so.

`ec/tools/grade_sweep_summary.py` reads this shape and classifies each row
into one of three, with no fourth:

| condition | what it prints |
|---|---|
| `change_count == 0` and the endpoints are equal | `held` |
| the endpoints differ | `moved, net ±N` |
| the endpoints are equal and `change_count > 0` | `moved N times, returned to its first recorded value` |

**The third row is the whole point.** There is no path by which a byte with a
non-zero change count is printed as `held`, `unchanged` or `quiet`, whatever
its endpoints say. That is a property of the classifier, held over the
committed file by `ec/tools/test_grade_sweep_summary.py` rather than asserted
as a string: collapsing the classifier to "everything held" or to "everything
moved" turns that suite red in both directions.

This is not the format's first reader. `fan_pair_correlation.read_change_counts()`
reads it too, and for a different question — how often a byte moved across a
whole sweep, which is what its correlation is built on — so it returns the
count column and stops. Reading the two value columns is what
`grade_sweep_summary.py` adds, and nothing before it did.

## The two blind spots, in the file's own terms

**1. `first_old == last_new` is ambiguous.** `0x07C6,2,0x04,0x04` is a byte
that moved twice and came back. `0x0363,21,0x00,0x00` is 21 moves that net to
nothing. The four columns cannot tell "moved and returned" from "held", which
is the endpoint-net blind spot
`docs/hardware-tests/gpu-tgp-07c4-07d7-door.md` §6 warns about, and the one
the false #276 sentence walked into.

**2. `first_old` is measured against the first recorded change, not against
the window.** The row `0x0743,1,0x02,0x03` records the byte as already at
`0x02` when the first change in the file was recorded. The `0x00 -> 0x02`
step is in no row of this file, so the row cannot say whether that transition
happened before the window opened or never happened at all. The reader prints
this bound and works it on the first single-change row with two endpoints that
differ, which is the shape where the missing step is one row wide and easiest
to read past. `windows/vendor-ec-map.md` reads `0x0743` as "the same
`0x02` → `0x03` step"; that is right, and it is a statement about where the
step went, not about where the byte started.

**What the format carries no word for at all:** the intermediate values, the
timestamps, the order, and whether an address with no row in the file moved at
all. A missing row means *not found to move in this file*, never *never
written* — the same wording `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`
uses for the twenty-two addresses in `0x07C0`-`0x07D7` that neither committed
capture gives a row.

## The header reconciliation, reported and not adjudicated

The `#` block states how many rows the source log held; the `change_count`
column sums to what this file's own rows account for. On the committed file:

```console
$ python3 ec/tools/grade_sweep_summary.py evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv
```

reports **32,499** in the header and a **change_count** sum of **34,710**, a
difference of 2,211. Both are computed on every run and neither is written
into the tool.

Which is right **cannot be settled from anything committed**, because the
source log is not in the tree. The two also describe different things: one is
every change the whole log held, the other what this file's rows account for.
A header naming rows this file does not carry would push the column above the
log — which is one way to read the gap and not a conclusion this change draws.
The exit is 0 by default; `--strict` makes a non-reconciling pair non-zero, for
a human who still holds the log.

The header's second clause — "this is the per-address change count plus every
row for the charge-limit registers" — names a set of registers the file does
not identify by address, and nothing committed identifies it either. It is
left as a clause rather than resolved into a register list here.

## The decision on the uncommitted 32,499-row source: recorded, not resolved

Issue #316 offered two options. **The one taken is to record which inferences
the four columns do and do not support**, in two places: this write-up, and
**ten `#` comment lines added to the head of the CSV itself**, where the next
reader's eye lands before any document does. The `#` block is dropped before
the header by every reader in the tree, so the addition is inert to all of
them, and it introduces no date other than the file's own.

**The other option — committing a reduced per-address value sequence — was not
available, and the reason is worth recording.** The source log is not in the
tree, and neither committed 2026-09-18 raw log covers this file's window: the
summary's own header states `22:49:29..22:53:00`, while
`2026-09-18-profile-switch-0700-07ff.csv` runs `22:56:01..22:59:55` and
`2026-09-18-profile-switch-0400-07ff.csv` runs `23:03:08..23:05:13`. Nothing
derivable can be derived from those. A per-address value sequence written by
hand from the four columns would reproduce exactly the defect this issue is
about: a lossy projection, this time with an extra step.

So **no generator ships**, and the file stays hand-made. What changes is that
"hand-made" is now a recorded decision with its two blind spots beside it,
which is the branch of the issue that asks for it. Recovering a real reduced
sequence needs the original log from the 2026-09-18 machine — a human's
artifact, not something this repository can reconstruct.

## The reader, and what its gate is not

`ec/tools/grade_sweep_summary.py` is stdlib-only: no EC, no firmware image, no
Ghidra, no network, no scratch directory. It reads the file it is handed and
prints the classification, the header reconciliation, the reference-point
bound, and the closing "none of this is hardware evidence" line every report
in this repository prints.

Its suite, `ec/tools/test_grade_sweep_summary.py`, is found by
`bash tools/run-tests.sh` like every other `test_*.py`, so it runs per commit.

**A gate for it is prepared and not landed.** `.github/scripts/agent-gates.sh`
is copied from the agent-pipeline template and this pipeline's push token has
no `workflow` scope, so a branch editing it fails at the *end* of a pull
request rather than at the start of it; the gate changes a human wants are
prepared beside the file under `docs/ci/` instead.

This one **folds into `docs/ci/agent-gates-capture-claims.patch`** rather than
shipping as its own file, and the reason is measured rather than assumed. The
cut was made as its own patch first, against the committed script, with its
`check_sweep_summary()` and its `gate` line in the one place the plan named as
free: the gap between `check_doc_links()` and the first `gate` line.
`python3 tools/test_agent_gates_patches.py` then refused it — landing it first
splits `agent-gates-pin-table-rows.patch`'s context, and landing that one first
splits this one's, so the two cannot be landed together in either order. That
patch's insertion point *is* the gap this one was aimed at, which is what a
saturated anchor looks like from the inside.

The function side is still free; the `gate` line is the saturated half, and it
is the half that decides composition. `agent-gates-capture-claims.patch` already
holds an anchor for both, so the pair rides there. This is the fourth fold into
it, and `docs/findings/history-checkouts-gate-wiring.md` is where the
saturation is measured anchor by anchor.

**Until a human runs `git apply`, nothing runs this suite from the gate per
commit.** No line of the patch, the mode, or this section is a claim about a
laptop: the suite reads committed CSVs, no EC is opened, and no register is
read back.

## Not done here, and why

- **`check_capture_encoding.py` counts this file's rows as change rows.** Its
  skip rule keys on `row[0] == "ts"`, and this file's header row starts `addr`.
  The count is meaningless for this file but is consistent across both codecs,
  so nothing fails. It is a real, small bug and fixing it means editing a
  shared tool and its suite; it is a follow-up, not a side effect here.
- **No `status:` in `ec/annotations/registers.yaml` changes.** Nothing in this
  work is a claim about a register's behaviour. A row in this file is a
  passive record of what a watcher saw, not a readback and not evidence that
  the EC acts on a byte.
- **No hardware or Windows run is claimed, implied or prepared.** There is
  nothing to prepare: the tool reads a committed CSV.