# The cited set was intersected with the reachable set, and the work list was the intersection (issue #460)

Issue [#460](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/460)
reported a structural defect in `call_graph.py`'s work list: `build()`
iterated `edges.items()`, so a callee no transfer in the scanned set reaches
had **no row at all** in `call-graph-callees.csv`, and `report()` read its
cited set off that table — so the "anonymous callees a comment names"
population was the cited set ∩ the reachable set. The comments naming the
difference were counted by the frame gate and then absent from the ranking,
on no evidence but the missing edge. This file records what the population is
once the intersection is gone, which rows it added, why each one has no
inbound edge, the decision on `named_callers`, and the sentences elsewhere in
this repository that the change makes false.

**Nothing here is a claim about the EC's behaviour.** No register, no
`status:` change, no annotation row, no hardware, no Windows. Every figure
below comes from committed listings, the committed `decompiled/index.csv`
and the committed `ghidra-functions.csv`, re-derive by running the tool.

## The issue's numbers are one measurement behind, and the shape is the same

Re-measured on the tree this was written against (2026-10-03):

| quantity | issue text | this tree, before | this tree, after |
|---|---|---|---|
| `citations()` kept keys | 174 | 112 | 112 |
| `report()`'s "anonymous callees a comment names" | 141 | 104 | 112 |
| cited keys with no CSV row | 33 | 8 | 0 |
| citing comments dropped | 63 | 9 | 0 |

The defect is the one filed; the magnitudes are not the ones filed, because
other tranches landed between. Every figure this file carries is the tool's
own output on the tree it ran against, and none of the issue's literals is
carried forward as a result.

## What the change is

`build()` keeps its pass over `edges` and adds a second over `citations()`'s
`kept`: every key not already emitted gets a row built from an **empty**
inbound list, so `inbound`, the four form columns, `callers` and
`named_callers` are 0 and `cited_by` / `citing` carry the naming comments.
`citations()` proposes a key only where `Index.resolve()` returned a `FUN_*`
row, and it keys that pair on `(row["program"], row["_addr"])` — the key
`by_scope_addr` is built from — so every added key resolves to the row that
put it there and needs no new resolution rule.

The before → after movement of the report's own figures, on this tree:

| line the report prints | before | after |
|---|---|---|
| anonymous rows the table carries (was "targets still anonymous") | 397 | 405 |
| inbound sites to those | 552 | 552 |
| anonymous rows no transfer reaches | 318 | 318 |
| anonymous rows the table carries no row for (before: that same count, read off the row above) | 318 | 310 |
| anonymous callees a comment names | 104 | 112 |
| comments that name one | 125 | 134 |
| rejected or undecided naming a callee with no row | 75 | 64 |
| distinct targets reaching a row | 1841 | 1841 |
| rows in `call-graph-callees.csv` | 1841 | 1849 |

Two of those deserve their reasons, because neither is a measurement moving
underneath us:

- **"anonymous rows no transfer reaches" does not move.** It is a statement
  about the transfer scan, so it is counted off the rows that carry an
  inbound edge. Subtract the whole table instead and it falls by exactly the
  number of rows this change added on purpose, which would understate the
  blind spot rather than describe it.
- **"naming a callee with no row" falls from 75 to 64, and that is the
  change working twice.** It counts refused `(callee, comment)` pairs. The
  nine kept pairs it used to contain are now in the table; two refused pairs
  also stopped appearing in it, because the callee they name is now in the
  table on the strength of a *different*, kept pair — `bank0,B4A8` and
  `bank1,9B3C` each carry one refused mention beside their kept ones.

**`inbound == 0` in the committed CSV now means exactly one thing:** no
transfer in the scanned set reaches it *and* a kept citation names it. No
other row shape produces it — every edge-derived row has at least one site.
That is asserted in `call_graph.py --self-test` rather than assumed, and it is
what keeps `rank_common_runtime.py`'s "no zero-count row" rule from being
silently violated by a row the table now emits on purpose. On this tree every
added row is `bank0`- or `bank1`-scoped and `rank_common_runtime.py` reads
only the `common` rows, so that check is untouched; the property to preserve
if a tranche ever cites a `common` callee nothing reaches is the shape
invariant, not the check.

## The rows that were missing, and why each has no inbound edge

Eight keys, nine naming comments. **No claim here is that any of them is a
missing function.** Each is named by a comment that records how it *is*
reached, which is the opposite of a hole in the export; the mechanisms, as
those comments state them:

| key | cited by | how its own comment says it is reached |
|---|---|---|
| `bank0,A716` | `bank0,A6C6` | "sets DPTR to 0x0857 and falls through to 0xA716, which increments the byte there" |
| `bank1,B224` | `bank1,B1B3` | "Masks XDATA 0x0490 with 7: 6 jumps to 0xB1F5, 7 jumps to 0xB224" |
| `bank0,E7BB` | `bank1,CA02` | "0xC9BE falls into this address and `bank-call-targets.csv` also records an ljmp to it" |
| `bank1,9B3C` | `bank1,9B03` | "it ends in an sjmp to 0x9B3C" |
| `bank0,A7C8` | `bank0,8653` | "it is the routine called at 0xA828 inside the 0xA7C8 routine" |
| `bank0,B4A8` | `bank0:B5B2`, `bank0:B5D2` | "with A = 0 on entry from 0xB4A8"; "the destination of the ljmp instructions at 0xB51F, 0xB533 and 0xB53B in 0xB4A8" |
| `bank0,B5D3` | `bank0,B736` | "the destination of the ljmp instructions at 0xB66F … in 0xB5D3" |
| `bank0,B737` | `bank0,B82E` | "It is the destination of the ljmp at 0xB758 in 0xB737" |

**One of those quotations is looser than its own listing.** `bank0,A6C6`'s
comment reads "sets DPTR to 0x0857 and falls through to 0xA716", but
`bank0/A6C6.asm`'s last two instructions are `A6D7 80 3d  sjmp 0xa716` and
`A6D9 80 3f  sjmp 0xa71a` — a branch, not a fall-through, on either arm. The
listing header's own rule applies ("where the two disagree, this file is
right"), and the mechanism that puts `bank0,A716` in the table is the `sjmp`.
Left visible rather than tidied, because the comment is not this change's to
rewrite and its second sentence about the 0xA71A arm is exact.

**Four of the eight are named by exactly one `sjmp` in the committed
listings** — `bank0/A6C6.asm`'s `sjmp 0xa716`, `bank1/B1B3.asm`'s
`sjmp 0xb224`, `bank0/E722.asm`'s `sjmp 0xe7bb` and `bank1/9B03.asm`'s
`sjmp 0x9b3c`. That is the same blind spot §"What is left" of
[`ec/annotations/call-graph.md`](../../ec/annotations/call-graph.md) already
names, stated here per-address. `sjmp` is deliberately **not** a member of
`citation_callers.TRANSFERS` and must not become one — a PC-relative branch
is not a call, and the comment lexicon and this tool's transfer set are
deliberately different sets. The fix here is to make the row visible, not to
widen the grammar; widening it is three separate changes to the transfer
grammar and none of them is asked for by this issue.

**The other four are named by no committed instruction at all**, and the byte
immediately before each is a `ret`, so a fall-through does not account for
them either:

```console
$ python3 - <<'PY'
import glob, os, re
rows = []
for p in sorted(glob.glob("ec/decompiled/*/*.asm")):
    scope = os.path.basename(os.path.dirname(p)); stem = os.path.basename(p)[:-4]
    for line in open(p, errors="replace"):
        if line.startswith(";"):
            continue
        m = re.match(r"^([0-9A-Fa-f]{4})\s+((?:[0-9a-f]{2}|-)"
                     r"(?:\s+(?:[0-9a-f]{2}|-))?(?:\s+(?:[0-9a-f]{2}|-))?)"
                     r"\s+(\S+)\s*(.*)$", line)
        if m:
            rows.append((scope, int(m.group(1), 16), stem, m.group(3),
                         m.group(4).strip()))
print(len(rows), "instructions parsed")
for probe in (0x9B3C, 0xB5D2, 0x8863,      # positives: the scan does find these
              0xA7C8, 0xB4A8, 0xB5D3, 0xB737):
    hits = [r for r in rows if re.search(r"0x%04x\b" % probe, r[4], re.I)]
    print("%04X %d" % (probe, len(hits)))
PY
```

**Not found by this method is not absent**, and that is the whole of the
limit here: the exporter's own header calls the boundary census these entries
came from "an upper bound", and an address a firmware reaches through a
dispatch table, a function pointer or a branch the byte-scan boundaries cut
apart names nothing. Each of the four is an established routine by its own
listing — `bank0,A7C8` opens with `lcall 0xbe9c`, `bank0,B737` opens with
`lcall 0xb9d8` — so nothing here suggests a function is missing.

## `common,1C00` is the other shape, and it still has no row

The limit sentence's worked example is unchanged by this change and for the
other reason. `common,1C00` is named by 22 comments, **21 of them in a data
frame and 1 unsettled**, so it has no *kept* citation; and no transfer
reaches it either. Two things leave a callee rowless and the gate refusing
the pair is one of them — no transfer in the scanned set reaches it, and no
kept citation names it — so it still has no row to be right or wrong in.
That is the shape to watch for in any other count here: not ranked is not
absent.

What makes 0x1C00 the worked example is **weight, not uniqueness.** An
earlier draft of the correction to `call-graph.md` said it was "the only
shape of its kind" and "the one callee that is outside on both counts at
once", and that was wrong: on this tree the callees reached by no transfer
*and* named by no kept citation number **29**, and 0x1C00 is the heaviest of
them by a wide margin. The set, and the count of it, come from:

```python
import sys; sys.path.insert(0, "ec/tools")
import call_graph as cg
idx = cg.load_index()
edges, *_ , listings = cg.scan(idx)
kept, rej, undec, _ = cg.citations(idx, listings)
table = {(r["scope"], r["addr"]) for r in cg.build(idx, edges, kept)}
both = {c.callee for c in rej + undec
        if c.callee not in table and c.callee not in edges}
print(len(both), sorted(both))
```

Weighting that set by how many comments name each member puts `common,1C00`
first at 22 mentions; the next two, `common,1300` and `common,1602`, carry 4
each, and nothing else in the set reaches 4. So the sentence the tool prints
is defensible — "the worked example on both counts", meaning the example that
exercises both conditions at once, not the sole member of a one-element class
— while a uniqueness reading of it is not. `call-graph.md` now states the
weight and drops the uniqueness claim; neither file carries a count of the
set as a hand-kept total, since both the set and its membership move with
every annotation and every listing.

## The `named_callers` decision, taken: deliberately not a ranking term

Issue #460 asked for either a decision made or one recorded, and this is the
second: **`named_callers` stays printed and stays out of the sort key**, with
the reason written into `call_graph.py`'s module docstring, into `build()`'s,
and into §"Ordering" of `call-graph.md`.

- **It answers a different question.** `named_callers` counts the *callee's*
  callers. The premise it was being asked to police is about the *citing
  comment's* row — "a named function's comment names it". `report()` now
  prints that figure, and on this tree it is **134 kept pairs whose citing row
  is a named function and 0 whose is not**. It is not `named_callers`, and it
  is not a signal to watch as comments land either: **the 0 is structural, not
  measured.** A citing row can only be a row of `ghidra-functions.csv`, and
  every row of that names a function, so the not-named arm can only be
  non-empty on a skew between the annotation CSV and `decompiled/index.csv` —
  an annotation whose re-export has not landed. What the split actually checks
  is that those two files agree, and `report()` labels the arm `(0 by
  construction)` for the same reason `kept_unranked` above it carries one.
- **It is structurally undefined for the rows this change adds.** It counts
  callers of a row that has an inbound edge; making it a term would rank
  exactly the `inbound=0` rows on their *citers* while their own callers
  stayed uncounted.
- **Making it a term reorders the list**, which would oblige §"Ordering" to be
  re-argued on a statistic that is not the one the ranking is about. That is a
  design call to be made by a reader holding the whole table, not inside a
  counting fix.

The weight stays visible rather than dropped. **16 of the cited rows carry
`named_callers == 0`, holding 17 of the 134 citation mentions**, and they are
two different populations that the one column now carries together:

- **eight of them are the rows this change added**, which read 0 because they
  have no callers at all. That is the second reason in the bullet above: the
  column is undefined for them, so a ranking built on it would rank them on
  something it cannot count.
- **eight are reachable and each is `inbound=1, callers=1`** — the row's one
  caller is itself anonymous. They are `bank0,D5DB`, `bank0,E6F4`,
  `bank1,B43B`, `common,0FE6`, `common,150A`, `common,34C6`, `common,492D`
  and `common,5A5A`, and they carry 8 of the 125 mentions among the reachable
  cited rows.

The issue's "25 of 315, 26% of the weight" was a different measurement on a
different tree; nothing about the shape changed.

## The sentences this change makes false, corrected here

**`docs/findings.md` §25's `(0x9B3C has no row in it: no form in TRANSFERS
reaches a PC-relative branch)` is no longer true.** It was true when §25 was
written and it is true of what that section measured — a *row*, in the table,
carrying an inbound count — and `bank1,9B3C` now holds a row, reading
`inbound=0` with `cited_by=1` and `citing bank1:9B03`. The reason in the
parenthesis is still exactly right; only the consequence changed. The
sentence is left standing in that file, which is frozen at §97 and where
`check_findings_frozen.py` fails an added section. This paragraph is the
correction, and `ec/annotations/call-graph.md` §"What is left" carries it
beside the population it changed under.

**`docs/findings/pd-07d0-accessor-stubs.md`'s "`call-graph-callees.csv` is a
*callee-reached* census, not an inventory"** was the right reading of the
table when written and its *conclusion* still holds — a callee no committed
listing reaches **and** no comment names still gets no row, which is what
that write-up is about. What is no longer true is the word *only*: the table
is now over the reached set **or** the kept-cited set. That write-up's own
conclusion is unaffected, because none of the seven `pd 0x07D0` stubs carries
a kept citation (0 kept, 0 rejected, 0 undecided on all seven), so
`ec/tools/test_pd_07d0_accessor_stubs.py`'s "a row exists exactly when a
committed listing reaches it" still holds — narrowed in what it claims, not in
what it asserts, which is why that case's name and docstring were reworded
rather than its assertion changed.

## Reproducing

```console
$ python3 ec/tools/call_graph.py            # regenerate the table, read the report
$ python3 ec/tools/call_graph.py --check    # byte equality against the committed CSV
$ python3 ec/tools/call_graph.py --self-test
```

`--self-test` carries the shape on its own fixture: the `0x0D40` case the
fixture already held — an `sjmp` target the comment lexicon credits and
`TRANSFERS` cannot reach — is now asserted to be **in** the table reading
`inbound=0`, and the assertion it replaces is left in the source beside it
with its reason, because a reader who remembers it should be able to see what
moved. `0xDEAD` still gets no row, which is what keeps the table from being an
inventory of every anonymous row.
