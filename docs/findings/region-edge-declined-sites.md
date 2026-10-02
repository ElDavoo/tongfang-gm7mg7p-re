# The six offsets the rel8 site walk declines are now reported by the tool rather than verified once

(2026-10-02, issue #1093. Static reading and arithmetic over committed bytes.
No capture opened, no EC, no hardware, no Windows, no `registers.yaml` row
touched.)

[`trampoline-relative-branch-sites.md`](trampoline-relative-branch-sites.md)
*What this means for #48* is the one place in this repository that argues a
byte scan's negative is exhaustive rather than sampled, and it names its own
exception in the same sentence: the walk tests `d[i] in REL_OPCODES` at every
offset of the three audited regions "bar the two at each region's top edge
(whose six addresses all hold `0xFF`, not a relative opcode, so nothing is
dropped)". That is the right caveat, and it rests on six byte values a reader
checked once. This makes the tool report the exemption on every run, so the
caveat is a printed line rather than a remembered measurement.

**The positive claim, and its exact size: `audit_call_targets.py` now walks the
edge window itself, prints the address and the byte at each end of it, and
fails if any of them opens a relative branch.** Nothing else about the scan
changed — the site count is the same, the census is byte-identical, and every
pre-existing `--self-test` line still prints. `declined_sites()` is added beside
`relative_sites()` as the guard's other branch, so the offsets the walk skips
are nameable by a caller rather than only inferable from the absence of a row.

## What the guard declines, and the two branches of one predicate

`relative_sites()` requires the whole instruction inside the region, because the
displacement is its last byte and that byte must not come out of the next one:

```python
    for i in range(lo, hi):
        op = d[i]
        if op in REL_OPCODES and i + OPCODE_LEN[op] <= hi:
            yield i, op, relative_target(op, d[i + OPCODE_LEN[op] - 1],
                                         runtime_addr(i, True))
```

The refusal is a **bounds** decision, and
[`rel8-displacement-bound.md`](rel8-displacement-bound.md) settled it as one:
`hi` is a constant out of `region_bounds()`, and reading a 3-byte form's
displacement out of the neighbouring program would be a claim about a different
address space. That verdict is not reopened here. What was missing is the
**coverage** half — the byte scan's one-directional error argument (a scan can
invent a branch but cannot miss one) holds everywhere except here, and the only
thing holding it here was those six bytes.

So the two generators are the same predicate read both ways, and they partition
it: every relative-shaped byte in `[lo, hi)` is a site in one or declined in
the other, never neither and never both. `declined_sites()` yields
`(offset, opcode, length, byte)`; the fourth element is the byte the offset
holds, carried so a caller reporting a window does not index `d` itself. There
is deliberately no target, and none is invented: for a declined offset the
displacement byte is at or past `hi`, so a target here would be the
cross-region read the guard exists to refuse.

**This is a narrowing of the issue's preferred shape, stated as one.** The
issue asked for `relative_sites()` to yield the declined offsets "under a
distinct class", which would have made them rows. It does not, for two reasons
that are properties of the data and not of taste. There are **no declined
offsets on this image to put in a column** — zero at all six addresses — so a
`declined` column on [`bank-relative-branch-targets.csv`](../../ec/annotations/bank-relative-branch-targets.csv)
would be empty on every row and would regenerate a committed generated file for
nothing. And a declined row has **no target by construction**, so emitting it
means either fabricating a cross-region target or inventing an empty-target
case for every downstream group-by to handle. The refusal is the right call;
the fix reports it rather than quietly overruling it. `declined_sites()` is the
"distinct class" at the module's API level, and `relative_sites()`'s docstring
names it so a reader arriving from the issue finds the answer.

## The window, and a correction to the issue's reading of it

The issue names **six addresses** — `0x7FFE`, `0x7FFF`, `0xFFFE`, `0xFFFF`,
`0x17FFE`, `0x17FFF` — and describes them as "the last two bytes of all three
audited regions", read as one symmetric window. The six addresses and their
byte values are right. **The two are not symmetric**, and a check written to
the issue's wording as a symmetric pair would be wrong in a way that shows up
as a false red:

| address | declined by a 2-byte form | declined by a 3-byte form |
|---|---|---|
| `hi - 2` (`0x7FFE`, `0x0FFFE`, `0x17FFE`) | **no** — `i + 2 == hi` is admitted | yes |
| `hi - 1` (`0x7FFF`, `0x0FFFF`, `0x17FFF`) | yes | yes |

`hi - 1` is at risk from *any* relative form and `hi - 2` only from a 3-byte
one. A 2-byte form planted at `hi - 2` is an ordinary site, correctly reported
by `relative_sites()` and **not** declined.

**What `--self-test` does with that is a choice, and it is the conservative
one.** The new line reports the *window* claim — "the scan tests every offset
bar these two, and none of them opens a branch" — rather than the guard's, so
it reddens on a relative opcode at either position including `hi - 2`. A 2-byte
form there is not dropped, so the failure clause says so in as many words
("which the guard admits, so nothing is dropped there") instead of leaving a
reader to work it out. Reading the line as a claim about the *guard* rather than
about the window is the alternative, and it is the weaker check: it would be
blind to a branch at `hi - 2` in a dump where the window is what a reader
cares about, and it is the window that
`trampoline-relative-branch-sites.md`'s quotable sentence is stated over. The
width is two bytes rather than one for the same reason: `hi - 1` is where every
form is refused, `hi - 2` only where a 3-byte one is, and the sentence being
inherited names both. The issue's figure and this table are both left here
rather than one replacing the other.

## The six addresses, and what they hold

| region | address | byte | what it is | in `REL_OPCODES`? |
|---|---|---|---|---|
| `common` | `0x07FFE` | `0xFF` | `mov r7,a` | no |
| `common` | `0x07FFF` | `0xFF` | `mov r7,a` | no |
| `bank0` | `0x0FFFE` | `0xFF` | `mov r7,a` | no |
| `bank0` | `0x0FFFF` | `0xFF` | `mov r7,a` | no |
| `bank1` | `0x17FFE` | `0xFF` | `mov r7,a` | no |
| `bank1` | `0x17FFF` | `0xFF` | `mov r7,a` | no |

All six hold `0xFF`, read against the committed
`ec/firmware/GMxMGxx_11.800` and by the tool's own walk over `AUDITED` rather
than by a scan written for this page:

```console
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test
  ok   none of the 6 offsets the rel8 site walk declines at a region edge (0x07FFE=0xff, 0x07FFF=0xff, 0x0FFFE=0xff, 0x0FFFF=0xff, 0x17FFE=0xff, 0x17FFF=0xff) holds a relative opcode, so the scan drops nothing at any region edge
```

`declined_sites()` yields **zero** over all three audited regions, and
`relative_sites()` still yields the same total it always did. The line is the
question asked of the bytes every run, and it is a question with a failure
mode: `ec/tools/test_relative_edge_guard.py` plants a relative opcode at each
of the two window positions in each of the three regions and asserts the tool's
own `self_test()` returns 1, asserts the failure names the address, and asserts
that every *other* line of the transcript is unchanged — otherwise "the new
line went red" would prove nothing about which line saw it. The two cases are
distinguished in the output, which is the asymmetry above being visible where a
reader meets it:

```console
# a 2-byte form at `hi - 2` -- admitted by the guard, so nothing is dropped
  FAIL  none of the 6 offsets the rel8 site walk declines at a region edge
        (0x07FFE=0x40, 0x07FFF=0xff, ...) holds a relative opcode, so the scan
        drops nothing at any region edge -- a relative opcode is there at
        0x07FFE (which the guard admits, so nothing is dropped there)

# a 2-byte form at `hi - 1` -- refused, so this one is a dropped site
  FAIL  none of the 6 offsets the rel8 site walk declines at a region edge
        (0x07FFE=0xff, 0x07FFF=0xff, 0x0FFFE=0xff, 0x0FFFF=0x40, ...) holds a
        relative opcode, so the scan drops nothing at any region edge -- a
        relative opcode is there at 0x0FFFF
```

(the transcript's own lines are not wrapped; the wrapping above is this page's
width. `python3 ec/tools/audit_call_targets.py … --self-test` prints each check
on one line.)

## Why the exhaustive negative still holds, and on what terms

`trampoline-relative-branch-sites.md` *What this means for #48* argues that 0
of 9076 sites reaching the trampoline block from outside it is an **exhaustive**
negative for this image rather than a sample, and the argument's weakest link
was that it held on six byte values. It holds on them still — the line above is
the same measurement, taken by the tool — and it is now a measurement the tool
repeats. On an image that *did* put a relative opcode at a region edge the site
total would fall by however many the guard refuses, and this line would name the
addresses and go red. **That is the trigger, and it has not happened here.**

The thing being fixed is not a wrong count. It is that the count had a silent
failure mode: a dropped site leaves no trace in `bank-relative-branch-targets.csv`
— the census has no row for an offset the walk declined — and no trace in the
`--self-test` transcript either, so the count 9076 could have been inherited by
an image it was never measured on. That is the one thing
`trampoline-relative-branch-sites.md` *What this does not say* already forbids
for a different image. What the tool now does is make the exemption *visible*,
so inheriting the verdict means inheriting a line that says whether it should
be.

## Why the CSV column was declined, and what would reverse that

A `declined` column on the relative-branch census, or a `--declined-csv` mode,
is the natural next step and is **not built**, for the reason above: there is
nothing to put in either. Both would be empty on every row of the committed
image, `declined_sites()` yields zero over all three audited regions, and
regenerating a committed generated file to add an empty column is a shared-file
edit that buys no reader anything today.

**What would reverse that** is named rather than left open: the day
`--self-test`'s edge line goes red — that is, the day a declined offset exists
in a region this tool walks — a declined offset becomes a thing a reader can
want to count, diff between images, or put in a census row, and the column
earns its churn. The trigger is a *red line*, not a schedule.

## What this does not say

- **This is not a claim that anything was missed on this image.** The six bytes
  are `0xFF`, and that is a fact about this dump and not about the guard. The
  positive claim is that the tool now reports the exemption and fails if it
  changes — never that "the guard is safe" or "nothing is dropped, full stop".
- **The negative stays a per-image result and is not inherited by another SKU.**
  This runner has one firmware image and no second dump to measure against, so
  the sentence above is about `ec/firmware/GMxMGxx_11.800` and nothing else,
  and this page is not a claim about any other dump. A hypothetical image that
  did put a relative opcode at a region edge is named with its trigger — the
  count would fall and the line would go red — and is not a measurement.
- **No live test ran.** No EC was opened, no register read back, no capture
  opened, no hardware and no Windows involved. Every number here is a static
  read of `ec/firmware/GMxMGxx_11.800` or of a command over it.
- **No EC claim.** The subject is a property of Python walking a `bytes`
  object and of one arithmetic comparison. It says nothing about what the EC
  does, and it is not evidence that a branch at a region edge would be taken.
- **The census is not re-decided.** This work does not re-run the scan that
  wrote `bank-relative-branch-targets.csv` to check the census is right; it
  checks that this change regenerates nothing, which is a different and much
  narrower question.
- **No `registers.yaml` `status:` moved**, and none should: an edge is not
  evidence the EC acts on anything, which is the same line
  `trampoline-relative-branch-sites.md` draws. Nothing in
  `ec/annotations/registers.yaml` is touched by this change.
- **The guard's verdict is not reopened.** *The two branches* above argues
  that declining a cross-region displacement is right and leaves that standing;
  this adds reporting, not a licence to read the next region.

## Reproducing it

All from the repository root, all over committed inputs.

```sh
# 1. the new line, among the existing ones
python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test

# 2. the generated census is untouched by any of this -- must print nothing
python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 \
  --relative-csv | diff - ec/annotations/bank-relative-branch-targets.csv

# 3. the suite, which plants bytes to redden the line in both directions
python3 -m unittest discover -s ec/tools -p 'test_relative_edge_guard.py'
```

Command 2 must print nothing. `audit_call_targets.py` over the committed image
is **not** in `.github/scripts/agent-gates.sh` — the cheap tier runs
`registers.yaml`, `scan_refs.py`, the register counts, the Ghidra-tooling loop,
`py_compile`, shellcheck and the doc-link check — so the guard rides in the
tool's own `--self-test` and nothing under `.github/` has to move for it.
Adding it to a gate is a human's change upstream in `ElDavoo/agent-pipeline`,
which is the same position
`trampoline-relative-branch-sites.md` *Reproducing it* records for its own two
lines.

`bash tools/run-tests.sh` is green and picks up the new suite by `find`, with no
registration step. The plan this was built from recorded a red
`test_check_cluster_citations.py` in the merged tree, named by
[`rel8-displacement-bound.md`](rel8-displacement-bound.md) and
[`opcode-len-bounds-census.md`](opcode-len-bounds-census.md); **it is green on
this tree** and was green on `origin/main` before this branch, so there is
nothing to report. `guard-off-transcript-scope.md`'s red-set table is where that
suite's own change is recorded.

## Follow-ups this opens

- **The `declined` column is not queued speculatively.** It is named above with
  its trigger — the edge line going red — so the next person to see that line
  turn red knows the column is what the situation calls for. A follow-up issue
  filed today would be a follow-up with nothing to do.
- **The two other site walks have the same shape and are not touched.**
  `paged_sites()`'s `range(lo, hi - 1)` stops at `hi - 2` and `call_sites()`'s
  `range(lo, hi - 2)` at `hi - 3`, so both leave a window at the top edge a
  relative form of the right length would land in, and the argument above
  applies to them in the form it applies here. Nothing in this work suggests
  their exemptions matter to any current verdict, and a report nobody needs is
  what this change was made to avoid; the question is left for whoever finds a
  verdict that rests on it.
- **`--self-test` is not in any gate**, for the reason *Reproducing it* gives.
  That is a pipeline question, not a finding, and it belongs upstream.
