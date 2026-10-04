# The two dispatch tables are closure edges, and `0xEFE7` is a dispatch

`ec/annotations/bank-attribution.md` §5 listed two things its closure could not
see, and §9's second follow-up asked for both as edges: the `jmp @a+dptr`
jump tables, and the index tables behind the common-area `?C?CCASE` reader at
`0x7151`. Both are edges now. `ec/tools/dispatch_edges.py` is the reader and
`ec/tools/bank_attribution.py` seeds them into `closure()`'s worklist.

**What this is.** Reachability, not a re-count. `closure()` stopped at a
computed dispatch *by construction* — `walk_branch_arms.descend()` ends an arm
at a target it cannot resolve — and it stopped at a call into the common area
because no bank owns those bytes. Between them those two decisions put this
image's index tables and its jump tables outside both closures. The handlers
behind the bank0-window index tables were unreachable rather than unattributed,
and that is a different defect with a different fix.

**What this is not.** A verdict on the same-bank assumption, and not a
stronger kind of attribution than the closure already made. See
[The direction of the move](#the-verdicts-move-and-not-all-one-way) below: the
residue drops sharply and the ambiguous class grows by more than four times,
and the second number is the one to read next to the first.

Everything here is static: Python over a committed `bytes` object. No register
was read, no capture was taken, and no `status:` in
`ec/annotations/registers.yaml` moves — none could.

## The two edge kinds are different mechanisms

They are not two spellings of one thing, and the tool gives them separate
provenance values so a downstream consumer can tell them apart.

**`index-table`** is read out of a committed CSV.
[`ec/annotations/index-table-entries.csv`](../../ec/annotations/index-table-entries.csv)
already carries, for every entry of every one of this image's 15 inline tables,
the `lcall` site it follows and the target it names — `decode_index_table.py
--all-csv` resolved each against the reader's layout.
`dispatch_edges.py` reads that mapping and seeds each banked target as an entry
point. Nothing is decoded a second time, so nothing here can drift from the
committed file.

**`dispatch-table`** is read out of the bytes at run time. There is no CSV for
the `jmp @a+dptr` tables, so the tool finds them by shape and takes the base
from the `mov dptr,#imm16` that loads it. It comes in two shapes, which is why
there are two provenance values rather than one:

```
inline   54 mm      anl  a,#mask        ; the mask is the row count minus one
         90 hi lo   mov  dptr,#base
         f8         mov  r0,a
         28         add  a,r0           ; three adds of A to itself: stride 3
         28         add  a,r0
         73         jmp  @a+dptr

shared   90 hi lo   mov  dptr,#base
         12 dl dh   lcall dispatcher    ; whose own prologue is `anl 0x00,#mask`
```

The row count comes from the `anl` mask each shape carries, never from a
constant in the tool — so a table cannot be sized by a guess, and a shape that
stops matching shows up as a self-test failure rather than as a wrong number.

**Both seed an address and let the walk derive where it goes.** A dispatch edge
seeds the *row address*, not the target the row names. `descend()` on a row
address decodes the row's `ljmp` and records the target as a callee, and
`closure()` follows a callee it already trusts:

```console
$ python3 -c '
import sys; sys.path.insert(0, "ec/tools")
from walk_branch_arms import descend
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
arm = descend(d, "bank1", 0x8A45, None, 16, 500, True)
print([(f"0x{pc:04X}", t) for _s, insns in arm.blocks for pc, t in insns])
print(arm.ends, [f"0x{c:04X}" for c in arm.callees])
'
[('0x8A45', 'ljmp 0x8a6c')]
['tail jump to a callee'] ['0x8a6c']
```

That is what makes these control-flow edges rather than table lookups wearing
one: the target is derived by the walk, so a row the tool misreads becomes a
walk that stops, not a fabricated entry in a closure.

## `0xEFE7` is a dispatch, not a byte inside a table

The issue that asked for these edges held one premise backwards, and worth
recording because it is the kind of premise that silently becomes a fabricated
target. `bank-attribution.md` §5's own caveat — *"the seeds are byte-derived
too … a shape match inside a data table would be indistinguishable here from a
real one"* — was landing on one of the seven `jmp @a+dptr` sites the tool
enumerated by shape. The site is real.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xef9a; pd 3' /tmp/bank1.bin
            0x0000ef9a      90efe8         mov dptr, #0xefe8
            0x0000ef9d      12efda         lcall 0xefda
            0x0000efa0      90048c         mov dptr, #0x048c
```

The base is loaded by a `mov dptr,#imm16` two instructions before the call —
exactly the shape the other sites use — and the `73` at `0xEFE7` is the last
byte of a 14-byte routine the committed inventory already names:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xefda; pd 8' /tmp/bank1.bin
            0x0000efda      53000f         anl 0x00, #0xf
            0x0000efdd      e500           mov a, 0x00
            0x0000efdf      2500           add a, 0x00
            0x0000efe1      2500           add a, 0x00
            0x0000efe3      5002           jnc 0xefe7
            0x0000efe5      0583           inc dph
        ┌─< 0x0000efe7      73             jmp @a+dptr
```

Three corroborations, none of them this write-up's own reading:

- [`ec/decompiled/index.csv`](../../ec/decompiled/index.csv) carries
  `bank1,EFDA,dispatch_index_3x_from_byte_00,14` — a 14-byte span that ends at
  `0xEFE7` inclusive, and `0xEFE7` is in no bank's function row as a byte.
- The same file's `bank1,F018,dispatch_via_table_f041` and
  `bank1,F022,dispatch_via_table_f071` name the *wrapper* idiom that loads DPTR
  and calls `0xEFDA`, which is what a shared-dispatch site looks like from the
  other side.
- Row 14 of the `0xEFE8` table sits at `0xF012` and reads `ljmp 0xF040`, which
  `index.csv` independently names `bank1,F012,table_efe8_row14_ljmp_f040`.

Per the pattern `bank-attribution.md` §4 already uses for `0x808C`, **the
bytes are the pin and the listing is not.** `ec/decompiled/*.asm` is a
regenerable export, so a later annotation redrawing these bytes is not a
regression and must not be graded as one. `dispatch_edges.py --self-test`
asserts all four halves — the `73`, the `mov dptr,#0xefe8`, the
`lcall 0xEFDA` between them, and row 14 — and `bank_attribution.py --self-test`
asserts the consequence: that all sixteen rows of the `0xEFE8` table are entry
points of bank1's closure and that `0xF040`, behind row 14, is reached by the
walk following the `ljmp`.

## The bank scoping is load-bearing, and the CSV does not carry it

[`index-table-entries.csv`](../../ec/annotations/index-table-entries.csv) records
a `site` as a bare runtime address. Two of the eleven bank0-window sites,
`0x8662` and `0x918A`, are *also* addresses bank1's closure reaches — and they
are not the same code:

```console
$ python3 -c '
import sys; sys.path.insert(0, "ec/tools")
from trace_xdata_refs import offset_for_runtime
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
for site in (0x8662, 0x918A):
    for region in ("bank0", "bank1"):
        off = offset_for_runtime(site, region)
        print(f"0x{site:04X} {region:6} {d[off:off + 3].hex(\" \")}")
'
0x8662 bank0  12 71 51
0x8662 bank1  f0 22 90
0x918A bank0  12 71 51
0x918A bank1  ea 3c c3
```

Seeding those rows into bank1's closure would attribute bank0's table to bank1
on the strength of a numerical coincidence between two unrelated addresses.
`index_table_sites()` therefore gates every row on the site's bytes *in the
window being walked*, which admits all eleven sites for bank0 and none for
bank1. That is the right answer for a reason the CSV never claimed to carry.

## The worklist is a fixpoint, and on this image it has to be

An edge is emitted only once the instruction that dispatches its table is
inside the walk — a table nothing reached must not put bytes in the closure,
because that is an attribution with no control flow behind it at all. That
makes the edge set depend on the walk and the walk on the edge set, and the
dependency is not hypothetical. bank1's closure converges in four passes, and
each pass after the first opens dispatch sites the previous one could not see:

```console
$ python3 -c '
import sys, collections; sys.path.insert(0, "ec/tools")
import bank_attribution as B, dispatch_edges as DE
from trace_xdata_refs import offset_for_runtime
from walk_branch_arms import descend
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
rows, _s, tramp = B.survey(d); seeds = B.seeds_for(tramp)
reached = collections.Counter(); done = set()
pending = collections.deque((t, "trampoline", None) for t in sorted(seeds[1]))
for turn in range(1, 6):
    while pending:
        start = pending.popleft()[0]
        if start in done: continue
        done.add(start)
        arm = descend(d, "bank1", start, None, 16, 500, True)
        for _s, insns in arm.blocks:
            for pc, _t in insns:
                if pc >= 0x8000: reached[pc] += 1
        for c in dict.fromkeys(arm.callees):
            if c >= 0x8000 and offset_for_runtime(c, "bank1") is not None:
                pending.append((c, "call", start))
    fresh = [e for e in DE.edges(d, "bank1", reached) if e["addr"] not in done]
    print(f"pass {turn}: {len(reached)} addresses, {len(fresh)} new edge(s) at "
          + (", ".join(sorted({f"0x{e['site']:04X}" for e in fresh})) or "-"))
    if not fresh: break
    pending.extend((e["addr"], e["kind"], e["site"]) for e in fresh)
'
pass 1: 4159 addresses, 64 new edge(s) at 0x8a6b, 0x98e4, 0x99df, 0x9b02, 0x9e36, 0xc82f, 0xef9d
pass 2: 8306 addresses, 102 new edge(s) at 0x8aa6, 0x91f9, 0xa308, 0xad76, 0xc8e2, 0xd22d, 0xf01e, 0xf028, 0xf032, 0xf03c
pass 3: 11731 addresses, 16 new edge(s) at 0xc930, 0xcdd9
pass 4: 12258 addresses, 0 new edge(s) at -
```

The cascade is concrete. `0xEFE8` row 0 is `ljmp 0xF018`, and `0xF018` is the
wrapper that loads DPTR with `0xF041` and calls `0xEFDA` — so seeding the
first table is what makes four more dispatch sites reachable at all. A
single-pass implementation would have found the first table and stopped.

## What the edges cover

Per bank, over the committed image:

| bank | index-table entry points | dispatch-table entry points | tables found | outside the walk |
|---|---:|---:|---:|---:|
| `bank0` | 113 | 0 | 0 | 0 |
| `bank1` | 0 | 182 | 19 | 0 |

An entry point is seeded once however many tables name it, so these counts are
entry points and not targets. The eleven bank0-window index sites name 115
distinct banked targets, of which bank0's closure already reached six; **all
109 of the rest became `index-table` entry points**, alongside four of the six
that arrived first as something else, for 113. `0x8054` — the first target of
the `0x8038` table — is the first of the 109, and it is exactly where
`bank-call-audit.md` §9's own table leads. That is the same `0x08035`
`lcall 0x7151` from both sides: §4 pins the mis-decode the walk makes of its
first byte, and this seeds the eight real handlers behind it.

The four common-area sites are excluded, and the tool prints the reason rather
than dropping them: they dispatch within the region every bank maps and no
bank owns, so they are unattributable **by construction** rather than by this
tool's coverage.

## Does this re-create §4's one-byte failure?

The question a reader will have, and the answer is a property of the layout
rather than a reassurance. It does not, and all three halves of §4's negative
pin still hold after the change:

- `bank0 0x8038` is still reached — the walk still sails through the table on a
  frame the data gave it.
- `0x808E` is still followed off it, so the failure mode is still a silent gain
  rather than a stop.
- `0x8039`–`0x8053` are still unreached, because `descend()` has no fall-through
  past an unconditional jump.

The reason is the table's own geometry: **no target any of these tables names
lies inside its own bytes.** Checked against
[`index-table-spans.csv`](../../ec/annotations/index-table-spans.csv), which
carries each site's `table_file_offset` and `table_end`:

```console
$ python3 -c '
import csv, collections
rows = list(csv.DictReader(open("ec/annotations/index-table-entries.csv")))
by_site = collections.defaultdict(set)
for r in rows: by_site[int(r["site"], 16)].add(int(r["target_runtime"], 16))
inside = 0
for sp in csv.DictReader(open("ec/annotations/index-table-spans.csv")):
    lo, hi = int(sp["table_file_offset"], 16), int(sp["table_end"], 16)
    inside += sum(1 for t in by_site[int(sp["site"], 16)] if lo <= t < hi)
print(inside, "target(s) lie inside their own table span")
'
0 target(s) lie inside their own table span
```

A §4-style mis-decode needs a target to point *back into* the data. None does,
so seeding the targets cannot close that loop. The bank0 `0x8038` table is the
tightest case — its span ends at its own first target `0x08054` — which is why
this is a property of the layout and not of the seeding.

## The verdicts move, and not all one way

This is the part worth reading twice, and it belongs next to the numbers rather
than in a footnote. Re-running with the edges in:

| | agreeing | contradicting | still ambiguous | unreached |
|---|---:|---:|---:|---:|
| all bucket-B pairs, before | 573 | 207 | 115 | 410 |
| all bucket-B pairs, after | 625 | 75 | 510 | 95 |
| both-banks-live, before | 568 | 207 | 115 | 398 |
| both-banks-live, after | 614 | 75 | 510 | 89 |

**The residue falls from 398 to 89, which is the coverage the tables were added
for and the reason this change exists.** The ambiguous class rises from 115 to
510, and that is not a rounding detail to skip past: a pair the closure could
not separate before and cannot separate now is not a pair it has decided. A
target this change newly reaches in *both* banks is exactly what an ambiguous
verdict means, and reaching more of the image is the most likely way to produce
more of them. `contradicting` falls from 207 to 75 for the same reason — some
of those targets are now also reached on the calling bank's side.

So this is **more coverage and weaker separation on the pairs that were already
ambiguous**, not a verdict on the same-bank assumption, and not a stronger kind
of attribution than the closure already made. §8 of
`bank-attribution.md` carries the standing caveat and the numbers here sit
beside it.

The closure's own check is unchanged, and that is the load-bearing part of this
table: zero contradictions among the 11 own-live/other-erased pairs and zero
attributions among the 6 both-erased — the two populations that would catch a
broken walk rather than a real cross-bank call. The new edges did not corrupt
the walk.

## Calibration: a table edge is a table edge

Every attribution stays *"attributed by this closure"*. What the table edges add
is reachability under a table's own framing, which is strictly more than a
byte-derived walk could say and strictly less than an attribution:

- The `?C?CCASE` reader **pops the return address into DPTR**
  (`bank-call-audit.md` §4, §9), so the index table's address is never an
  immediate and never appears in a scan. These edges are read out of data.
- The dispatch shapes are found by a byte scan, so they inherit the seeds' own
  caveat: a shape match inside a data table would be indistinguishable here
  from a real one.
- A table edge seeds an *entry point*, not a proof that the firmware executes
  that path. The selector byte's run-time value is not observed anywhere here.

`bank-attribution-regions.csv` grew a **`sources`** column for exactly this: the
sorted set of edge kinds among the entry points covering each run, so a run
reached through a table is distinguishable from one reached only by ordinary
calls. `seed_entries` still counts linker-written seeds and nothing else, and
`--self-test` asserts the pair — a run reached only through a table reports
zero seeds.

**One table is short of its mask, and that is reported rather than padded.**
`bank1 0xA308`'s `anl a,#0x0f` admits sixteen indices, but the table at
`0xA309` has six `ljmp` rows:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xa309; pd 7' /tmp/bank1.bin
       ┌─< 0x0000a309      02a31b         ljmp 0xa31b
       ┌──< 0x0000a30c      02a32c         ljmp 0xa32c
      ┌───< 0x0000a30f      02a33d         ljmp 0xa33d
    ┌────< 0x0000a312      02a34e         ljmp 0xa34e
   ┌─────< 0x0000a315      02a35f         ljmp 0xa35f
  ┌──────< 0x0000a318      02a370         ljmp 0xa370
   │││││└─> 0x0000a31b      7906           mov r1, #0x06
```

Indices 6–15 would read whatever follows the table, so the tool seeds the six
real rows and stops. Whether the compiler emitted a mask wider than the table
it emitted is a question about the build, not about the bytes here; it is named
rather than answered.

## What this does not settle

- **Which bank is mapped at run time.** Unchanged. Reaching a call site says
  its bytes are reachable from that bank's seeds, not that the bank is selected.
- **The reset and interrupt vectors** are still not seeds, and remain the single
  change most likely to move the residue further.
- **The four common-area index tables** dispatch below `0x8000`, so no bank owns
  their handlers. That is unattributable by construction.
- **`docs/findings/closure-vs-function-inventory.md`** imports the closure, so
  its figures move with this change and its prose is now stale. Re-measuring it
  is a follow-up, deliberately not done here: it would put a second write-up in
  this diff for no gain to either.
- **Nothing upstream.** This ends in a prepared patch and this write-up in this
  repository. Submitting it to `Wer-Wolf/uniwill-laptop` or `tuxedo-drivers`
  (issue #10) is a human's action.

## Reproducing it

```console
$ python3 ec/tools/dispatch_edges.py --self-test
$ python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --self-test
$ python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --regions-csv \
    > ec/annotations/bank-attribution-regions.csv
$ python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --pairs-csv \
    > ec/annotations/bank-attribution-pairs.csv
$ python3 ec/tools/census_closure_functions.py ec/firmware/GMxMGxx_11.800 --self-test
```

Both committed CSVs regenerate byte-identically on a second run.
`census_closure_functions.py` reads `ba.PAIR_PINS["all"]`, so it follows the new
figures without being edited.

The offline suite for the edge reader is
[`ec/tools/test_dispatch_edges.py`](../../ec/tools/test_dispatch_edges.py).