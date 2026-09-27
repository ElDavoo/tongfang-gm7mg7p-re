# Bank attribution from the 403 BL51 trampolines — what the closure decides, and what it does not

[`../tools/bank_attribution.py`](../tools/bank_attribution.py) grows a
per-bank reachability closure from the seed set
[`bank-call-audit.md`](bank-call-audit.md) §3 found and did not use, and this
file is the reading: the counts, the three numbers the issue asked for, the two
hand-decoded pins, and — the part that matters most for the next agent — **what
the numbers do not say**.

**Headline, and the §4c form of it.** Of the **1288 both-banks-live** pairs that
`bank-call-audit.md` §4 says the same-bank assumption is carrying, this closure
attributes **775** to a bank (568 agreeing with the assumption, 207
contradicting it), leaves **115** attributed to both banks so the attribution
does not separate them, and **does not reach 398**. The residue is printed on
its own line and is the honest bottom of all of it.

**Every attribution here is "attributed by this closure", never "proved to be in
bank N",** and that is not a formality. A flow walk has no function-boundary
recovery, so it inherits the framing risk §2 of that file documents: a 23-of-24
anchored site there sits inside a data table. §4 below is this tool's own
instance of the same failure — it walks onto the first byte of the `bank0`
`0x8038` dispatch table and follows its mis-decode out into a real routine —
pinned in `--self-test` in all three directions rather than dropped. A negative
in this file is a statement about *this closure's coverage* and never about the
address it failed to reach.

Nothing here was measured on hardware. No register was read back, no capture
was taken, and no `status:` in [`registers.yaml`](registers.yaml) moves. This is
a byte-level reading of `ec/firmware/GMxMGxx_11.800` alone.

## Reproducing it

No number in this file is taken on trust: every table is either a group-by over
one of the two committed CSVs or a section the tool prints, and the command that
produced it is given in both cases. The two CSVs are written without a comment
header, so `csv.DictReader` reads them directly — the convention
`bank-call-audit.md` §9 states for the tables it left behind.

```console
$ python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --self-test
$ python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --pairs-csv  > ec/annotations/bank-attribution-pairs.csv
$ python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --regions-csv > ec/annotations/bank-attribution-regions.csv

# the two flat images every `r2` transcript below is read against
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
```

The self-test exits 0 and prints 19 checks: the stub→bank decoding re-derived
through `find_stubs()`, the seed census, the two hand-decoded pins below, the
two `jmp @a+dptr` dispatch shapes §5 names, the four verdicts over both
populations, the closure's own internal check, and the per-run `bounds` column
below.

Wiring it into `check_ghidra_tooling`'s tool list in
`../../.github/scripts/agent-gates.sh` would make it permanently self-checking,
and that one line is **out of scope for this branch on purpose**: the push token
has no `workflow` scope, so a branch touching `.github/` fails at the end of the
run rather than the start. A human adds it.

[`bank-attribution-pairs.csv`](bank-attribution-pairs.csv) is one row per
distinct bucket-B (caller bank, target) pair — the 1305 — carrying the byte
classes `bank-call-audit.md` §4 assigned (`own_bank`/`other_bank`), the
closure's `verdict`, and the path count from each bank's closure.
[`bank-attribution-regions.csv`](bank-attribution-regions.csv) is one row per
attributed contiguous run per bank, with the entry points that reach it, how
many of those start at a name the linker wrote down, and which bounds fired
**for the walks that reach that run** — 535 of bank 0's 7006 rows and 68 of
bank 1's 2656 carry a bound and the other 9059 carry none, so an empty cell
means those walks all finished rather than that the bank has no bounds. §5
counts the same thing.

## 1. The seeds, and the one link in the chain that is not new

`audit_call_targets.trampolines()` already returns `{entry: (bank, target)}` for
the 403 BL51 trampolines, so the seed set exists, is self-tested, and is
imported rather than re-scanned. **350 route through the bank-0 stub `0x1100`,
53 through the bank-1 stub `0x1114`**, `0x1128`/`0x113C` select banks 2 and 3
with no trampolines, and all 403 targets are at or above `0x8000`. Each is a
`(target, bank)` pair the linker itself wrote down.

One thing to state rather than let a reader assume. The issue calls these
banks "named by the linker", and they are — but the mapping from stub address to
bank number is `find_stubs()` **decoding the stub body** (`setb`/`clr` on
P1.0–P1.2), not a header field. That is the same evidence `bank-call-audit.md`
§3 already records, corroborated by `make_bank_image.py --self-test` (the two
bank windows differ; the reset vector is common). It is the one link in the
chain here that is **not new evidence**, and it is not presented as new.

## 2. The closure, and how far it is from a disassembly

| bank | seeds | entry points | call-derived | addresses | runs |
|---|---:|---:|---:|---:|---:|
| `bank0` | 350 | 816 | 466 | 12694 | 7006 |
| `bank1` | 53 | 182 | 129 | 4159 | 2656 |

`addresses` and `runs` are group-bys over
[`bank-attribution-regions.csv`](bank-attribution-regions.csv) — `bytes` summed
and rows counted. The entry-point columns are the tool's own §2 and are
deliberately *not* in that group-by: the CSV's per-run `entry_points` column is
a union over the run, so summing it would count an entry point that spans two
runs twice. The per-bank totals are the only correct form and they come from the
walk.

```console
$ python3 -c '
import csv, collections
rows = list(csv.DictReader(open("ec/annotations/bank-attribution-regions.csv")))
per = collections.defaultdict(lambda: [0, 0, 0])
for r in rows:
    p = per[r["bank"]]
    p[0] += int(r["bytes"]); p[1] += 1; p[2] = max(p[2], int(r["max_paths"]))
for b, p in sorted(per.items()):
    print(f"{b} {p[0]:>10} {p[1]:>6} {p[2]:>8}")
'
bank0      12694   7006      10
bank1       4159   2656       4
```

**The block descender is borrowed, not reimplemented.** `walk_branch_arms.descend()`
does the block-level work unchanged, with its own `END_*` reason tokens and its
`walked` set covering every decoded address rather than every block start. The
one thing this tool adds is *above* it: an entry-point worklist, because
`descend()` records an `lcall` as a callee and walks past it while a closure has
to descend into same-bank call targets — that is the mechanism. No opcode table
and no target arithmetic is restated, and no shared tool was edited.

**How many independent paths reach each attributed address**, which is the cheap
robustness signal a flow walk needs and does not otherwise have:

| bank | 1 path | 2 | 3 | 4 | 5 | 6 or more |
|---|---:|---:|---:|---:|---:|---:|
| `bank0` | 10233 | 1829 | 182 | 290 | 136 | 24 |
| `bank1` | 3742 | 390 | 19 | 8 | — | — |

A byte one accidental path wandered into carries 1; a routine five independent
calls land in carries 5. **This is corroboration and not proof.** A walk that
walked into a data table five times would score well, and the 10 deepest bank-0
addresses are on 10 paths without any of that being evidence they are code.

## 3. The four verdicts, and the three numbers drawn from them

A bucket-B pair is `(caller bank b, target T)`. The closure is computed
separately per bank, so `T` can be in `closure(b)`, in `closure(1-b)`, both, or
neither — which is why the issue's three numbers double-count if they are read
as three disjoint sets. Four verdicts, and the three are drawn from them without
overlap:

| verdict | condition | which number |
|---|---|---|
| `attributed-same-bank` | `T ∈ closure(b)`, `T ∉ closure(1-b)` | evidence-decided, **agreeing** |
| `attributed-cross-bank` | `T ∈ closure(1-b)`, `T ∉ closure(b)` | evidence-decided, **contradicting** — a subset of it, broken out, not added to it |
| `still-ambiguous` | in both | stays assumption-decided |
| `unreached` | in neither | **the residue** |

```console
$ python3 -c '
import csv, collections
V = ("attributed-same-bank", "attributed-cross-bank", "still-ambiguous", "unreached")
rows = list(csv.DictReader(open("ec/annotations/bank-attribution-pairs.csv")))
amb = [r for r in rows if r["own_bank"] != "erased" and r["other_bank"] != "erased"]
for label, sel in (("bank0", [r for r in amb if r["caller_bank"] == "bank0"]),
                   ("bank1", [r for r in amb if r["caller_bank"] == "bank1"]),
                   ("both-banks-live", amb), ("all bucket B", rows)):
    t = collections.Counter(r["verdict"] for r in sel)
    print(f"{label:>16} {len(sel):>5} " + " ".join(f"{t[v]:>5}" for v in V))
'
           bank0   682   484    14    44   140
           bank1   606    84   193    71   258
 both-banks-live  1288   568   207   115   398
    all bucket B  1305   573   207   115   410
```

| caller | pairs | agreeing | contradicting | still ambiguous | unreached |
|---|---:|---:|---:|---:|---:|
| `bank0` | 682 | 484 | 14 | 44 | 140 |
| `bank1` | 606 | 84 | 193 | 71 | 258 |
| **both-banks-live** | **1288** | **568** | **207** | **115** | **398** |

**The three numbers the issue asked for, stated once each:**

- **evidence-decided: 775** = 568 agreeing + 207 contradicting.
- **contradictions: 207** — the contradicting part of that, reported separately
  because reporting only the sum would hide it.
- **residue: 398** — pairs this closure never reaches from either bank.

The split is lopsided and the asymmetry is the finding, not a defect of the
table: bank 0 has 350 seeds to bank 1's 53, so bank 1's closure is the smaller
and most of its 606 pairs come out `unreached` (258) or `contradicting` (193),
while bank 0's larger closure agrees with the assumption 484 times.

**A contradiction is a statement about the closure at least as much as about the
call.** `T ∈ closure(1-b)` and `T ∉ closure(b)` says the target is reachable
from the other bank's seeds and was not reached from this bank's — which is a
coverage statement about the second half as much as an attribution in the first.
Two readings stay open for each of the 207 and neither is settled here: the call
really is cross-bank, or the own-bank walk did not reach `T`. The 207 are
evidence that the same-bank assumption is **not** what the closure supports for
those pairs; they are not proof that a cross-bank call exists. §3 of
`bank-call-audit.md` still stands — BL51's own path is indirect, so a direct
`lcall` between banks would not be one of these, and a second bank-switch idiom
spelled differently would be invisible to this walk.

**The strongest sub-class, and the one to quote if only one number is quoted:
632 of the 1288 have the target as an entry point of the caller's own
closure.** 51 are a seed the linker wrote down and 581 are a same-bank call
target one to five hops from one. The depth is measured — each chain walked
back to the seed that reaches it, not counted off a name — and is printed as a
histogram rather than described:

```console
$ python3 -c '
import collections, sys
sys.path.insert(0, "ec/tools")
import bank_attribution as B
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
rows, stubs, tramp = B.survey(d)
seeds = B.seeds_for(tramp)
closures = {b: B.closure(d, b, seeds[b]) for b in (0, 1)}
pairs = B.pair_rows(rows, closures)
amb = B.both_live(pairs)
own = [p for p in amb if p["target"] in closures[int(p["region"][-1])][2]]
depth = collections.Counter()
for p in own:
    b = int(p["region"][-1])
    depth[len(B.entry_chain(closures[b][2], p["target"])) - 1] += 1
print(f"  {len(own)} of {len(amb)}   " + "  ".join(f"{k}: {depth[k]}" for k in sorted(depth)))
'
  632 of 1288   0: 51  1: 187  2: 218  3: 112  4: 57  5: 7
```

Only 238 are a linker-written name or one hop from one; the other 394 sit two
to five hops out. §7's five confirmations have that same shape — `0xF495` and
`0xF4A4` are call-derived entry points three hops from the `bank0` seed
`0x84EB` — though they sit in the 17 pairs outside the 1288 rather than in the
632, so they illustrate the depth rather than belong to it. Hence the histogram
rather than a summary: an earlier revision of this sentence read the whole
sub-class as "a name the linker wrote down, or one hop from one", which covers
238 of the 632 and mis-describes the 394 behind them.

## 4. The one-byte failure, pinned

The plan for this work expected a negative pin of the form "the closure must not
reach the `bank0` `0x8038` dispatch table". **It reaches its first byte, and
follows what it decodes there out of the table.** That is the finding, and the
pin became the boundary as it actually fell rather than being quietly dropped.

`bank0` `0x8031` is a real routine, named by the trampoline at common `0x1A98`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1a98; pd 2' /tmp/bank0.bin
        ╎   0x00001a98      908031         mov dptr, #0x8031
        └─< 0x00001a9b      021100         ljmp 0x1100
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x8031; pd 4' /tmp/bank0.bin
            0x00008031      9008e0         mov dptr, #0x08e0
            0x00008034      e0             movx a, @dptr
            0x00008035      127151         lcall 0x7151
        ┌─< 0x00008038      8054           sjmp 0x808e
```

The `lcall 0x7151` is `bank-call-audit.md` §9's table dispatch, and the table is
stored **inline after it** — the callee pops the return address into DPTR, so the
table's address is never an immediate and never appears in a scan. A walk that
continues past a call, which is what a closure must do, therefore lands on data.
It lands on `0x8038`, which §9's own layout puts as the table's **first byte** —
8 entries of three from file `0x08038`, `0000` at `0x08050`, the default at
`0x08052`, the span ending at its own first target `0x08054` — not on a byte
standing in front of one. §9 retracted the framing that puts an `sjmp` at the
head of the table, and this section had reintroduced it.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x8038; px 16' /tmp/bank0.bin
- offset -   0 1  2 3  4 5  6 7  8 9  A B  C D  E F  0123456789ABCDEF
0x00008038  8054 0080 9401 80d7 0281 1a03 815d 0481  .T...........]..
```

Read as §9 reads it, that is eight 3-byte entries of `address; case` — `0x8054`
with case `00`, `0x8094` with `01`, `0x80D7` with `02`, … — not instructions.

**The walk does not stop there, and that is the half worth reading twice.**
`0x8038` is `80 54`, the address field of entry 0 — and `80 54` is *also* a
well-formed instruction. `descend()` decodes it as `sjmp 0x808E` and follows
it, because an unconditional jump is a transfer and not a split. `0x808E` is a
real routine (`mov r6,#0x74` / `ajmp 0x8402`), and this closure credits it to
the `0x8031` arm alone — path count 1, one entry point. So the failure mode
shows up here as a **silent gain** rather than as a stop: the closure acquires
an address on the strength of a frame the data handed it, and nothing in the
tables distinguishes that from a real one.

This is still `bank-call-audit.md` §2's "walked into a data table", and it is
worth being exact about which instance: the walk is standing on a frame that
came out of a table, which is the whole of that caveat. What is *not* claimed
is that the table caused visible damage — it is a lucky mis-decode that landed
on real code, and `0x808E` is not a target of any of the 1305 bucket-B pairs,
so no number anywhere in this file moves. What it demonstrates is the shape of
the risk, not its magnitude: a table that decoded to a stop would have shown up
in §5's bounds, and one that decodes to code will not show up at all.

`0x8039`–`0x8053` are unreached, and for a reason that has nothing to do with
the transfer above. `descend()` has no fall-through past an unconditional jump:
`sjmp` ends the linear block and opens a fresh one at the target, so the bytes
after `0x8038` are never decoded. The walk did not decline to follow anything.

`--self-test` asserts all three halves — that `0x8038` **is** reached, that the
mis-decode **is** followed to `0x808E`, and that `0x8039`–`0x8053` are **not** —
so the failure mode stays visible in the form it actually takes, and the
one-byte spread stays a measured fact rather than a claim.

## 5. What the closure cannot see, measured

Ten entry points across the two closures stop at a bound, and they are reported
by where they stopped rather than as a rate — together with how much of each
closure rests on them, which is the number that decides how much weight the rest
of this file can carry.

| bank | entry points that stopped | first at | addresses reached by a stopped walk | of those, by no other | of those, runs |
|---|---|---|---:|---:|---:|
| `bank0` | 1 depth limit, 2 instruction budget | `0x8749`, `0x95DD`, `0x96AD` | 849 of 12694 | 637 | 535 of 7006 |
| `bank1` | 7 indirect jump | `0x8A04` and six more | 115 of 4159 | 115 | 68 of 2656 |

The first five columns are the tool's own printed section 7; the last is a
group-by over [`bank-attribution-regions.csv`](bank-attribution-regions.csv),
and it is the one a consumer of that file needs. The address column weights a
stop by how much it reached, where the `bounds` column is one cell per run, so
the two are not the same measurement: the 535 and 68 runs carry `854` and `120`
bytes against the `849` and `115` addresses the stopped walks reached, the
difference being addresses in those runs that a walk which *finished* also
reaches.

```console
$ python3 -c '
import csv, collections
rows = list(csv.DictReader(open("ec/annotations/bank-attribution-regions.csv")))
per = collections.defaultdict(lambda: [0, 0, 0])
for r in rows:
    p = per[r["bank"]]
    p[0] += 1
    if r["bounds"]:
        p[1] += 1
        p[2] += int(r["bytes"])
for b, p in sorted(per.items()):
    print(f"{b} {p[1]:>5} of {p[0]:>5} runs carry a bound, holding {p[2]:>5} bytes")
'
bank0   535 of  7006 runs carry a bound, holding   854 bytes
bank1    68 of  2656 runs carry a bound, holding   120 bytes
```

**The calls that leave the bank window are the larger blind spot, and they are
counted.** bank0's 130 entry points call 67 distinct common-area targets —
`0x445E` from 18 of them and `0x7151` from 12 — and bank1's 43 call 42. The
closure records each and follows none, because the common area is mapped in every
bank and no bank owns those bytes. What that costs is larger than the count
suggests: the `?C?CCASE` reader at `0x7151` dispatches all 15 of this image's
inline index tables — every one of the 15 `site` values in
[`index-table-entries.csv`](index-table-entries.csv) is an `lcall 0x7151`, 11 of
them inside bank0's window and 4 in the common area — and it is itself common
area, so **all 15 handlers are out of reach of this closure** unless some other
path reaches them too.

```console
$ python3 -c '
import csv
rows = list(csv.DictReader(open("ec/annotations/index-table-entries.csv")))
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
for s in sorted({r["site"] for r in rows}):
    off = int(s, 16)
    where = "common" if off < 0x8000 else "bank0"
    print(s, where, d[off:off + 3].hex(" "))
'
0x00DD3 common 12 71 51
0x04064 common 12 71 51
0x041EE common 12 71 51
0x0424B common 12 71 51
0x08035 bank0 12 71 51
0x08662 bank0 12 71 51
0x0918A bank0 12 71 51
0x09284 bank0 12 71 51
0x0A34A bank0 12 71 51
0x0A682 bank0 12 71 51
0x0D148 bank0 12 71 51
0x0D435 bank0 12 71 51
0x0DDBB bank0 12 71 51
0x0EBDC bank0 12 71 51
0x0F254 bank0 12 71 51
```

The `jmp @a+dptr` sites are the same story at the other end. bank1's closure
stops at seven: `0x8A6B`, `0x98E4`, `0x99DF`, `0x9B02`, `0x9E36`, `0xC82F`,
`0xEFE7`. The first is the dispatch idiom §9 reads at the common-area `0x7151`,
with the table base in a `mov dptr,#table` rather than popped off the stack —
and a jump table is exactly what a byte-derived walk cannot enumerate:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x8a5d; pd 10' /tmp/bank1.bin
            0x00008a5d      9006f8         mov dptr, #0x06f8
            0x00008a60      e0             movx a, @dptr
            0x00008a61      04             inc a
            0x00008a62      f0             movx @dptr, a
            0x00008a63      5407           anl a, #0x07
            0x00008a65      908a45         mov dptr, #0x8a45
            0x00008a68      f8             mov r0, a
            0x00008a69      28             add a, r0
            0x00008a6a      28             add a, r0
            0x00008a6b      73             jmp @a+dptr
```

bank0's closure stops at none, which is a property of which routines its seeds
reach and **not** evidence that bank0 has no dispatch. Both `mov dptr,#table`
bytes and both `0x73` opcodes are pinned in `--self-test`.

**Named blind spots, none of which this tool closes:**

- `jmp @a+dptr` is a computed target no byte-derived walk can resolve.
- **The reset vector and the interrupt vectors are not seeds.** They are
  common-area entry points no trampoline names, and adding them changes the
  closure's size materially. This is the single change most likely to move the
  398.
- A second bank-switch idiom spelled differently would be invisible: this walk
  treats every same-bank call as intra-bank.
- Banks 2 and 3 are taken as unused on `find_banks.py`'s word and were not
  re-derived.
- A call into the common area is not a failure of the walk and is not an
  attribution.
- **The seeds are byte-derived too.** `trampolines()` finds them by shape
  (`mov dptr,#imm` + `ljmp`/`lcall` a stub), and a shape match inside a data
  table would be indistinguishable here from a real one. §4 is the case where
  the shape was real; this is the caveat, not a counter-example.
- A seed's bank is a fact about the *stub*, not about the target's bank at run
  time. The closure propagates the trampoline's bank through edges; it never
  observes which bank is selected.

## 6. The `0x04A6` handoff at bank-1 `0xDFD0` — the two halves answer differently

[`bank-call-audit.md`](bank-call-audit.md) §6 and
[`static-refs-audit.md`](static-refs-audit.md) §5.2 agree that this site's
`handoff->write` verdict rests on the same-bank assumption plus one hand decode
([`pd-xdata-overlap.md`](pd-xdata-overlap.md) §2). **This run found the target
and not the caller**, and the difference is the whole result.

**The target `0x888C` is inside bank 1's closure and outside bank 0's.** The
path is one hop from a name the linker wrote down: the trampoline at common
`0x1954` names bank-1 `0x92F7`, and the walk from `0x92F7` reaches
`lcall 0x888C` at `0x9343`.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1954; pd 2' /tmp/bank1.bin
        ╎   0x00001954      9092f7         mov dptr, #0x92f7
        └─< 0x00001957      021114         ljmp 0x1114
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x9340; pd 4' /tmp/bank1.bin
            0x00009340      900646         mov dptr, #0x0646
            0x00009343      12888c         lcall 0x888c
            0x00009346      22             ret
            0x00009347      9005b2         mov dptr, #0x05b2
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x888c; pd 6' /tmp/bank1.bin
            0x0000888c      e9             mov a, r1
            0x0000888d      f0             movx @dptr, a
            0x0000888e      a3             inc dptr
            0x0000888f      ea             mov a, r2
            0x00008890      f0             movx @dptr, a
            0x00008891      22             ret
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x888c; pd 3' /tmp/bank0.bin
            0x0000888c      3e             addc a, r6
            0x0000888d      900f5d         mov dptr, #0x0f5d
            0x00008890      e0             movx a, @dptr
```

So the 16-bit store `pd-xdata-overlap.md` §2 decoded by hand is **attributed to
bank 1 by this closure as well as by that hand decode** — a second, independent
line of evidence, and it agrees. That is what `0x888C` was the stake of, and it
is worth having.

**The call site `0xDFD0` is not reached by either closure.** So the caller half
is unchanged: `0xDFD0` being bank-1 code is still the assumption plus the hand
decode, and no amount of the target's attribution settles it. §5.2's wording
stands unedited, and nothing here is a correction to it — there was nothing to
correct, only an evidence line that did not arrive.

**What this does not do, in the tool's own words:** it does not convert
"assumed" into "proved". The walk has no function-boundary recovery, so the
attribution is *attributed by this closure*, and the verdict for the site as a
whole becomes *assumption + closure (target only) + hand decode* rather than
proof. And the negative half — `0xDFD0` unreached — is a statement about this
closure's coverage of bank 1, **not** a statement about `0xDFD0`.

For contrast, the two banks at that runtime address, which is what the ambiguity
actually looks like:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xdfd0; pd 4' /tmp/bank1.bin
            0x0000dfd0      9004a6         mov dptr, #0x04a6
            0x0000dfd3      12888c         lcall 0x888c
            0x0000dfd6      900528         mov dptr, #0x0528
            0x0000dfd9      12888c         lcall 0x888c
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0xdfd0; pd 4' /tmp/bank0.bin
        ╎   0x0000dfd0      e6             mov a, @r0
        ╎   0x0000dfd1      7d20           mov r5, #0x20
        └─< 0x0000dfd3      02724b         ljmp 0x724b
```

The same runtime address is different code in each bank's window. That is
ordinary, and it is the ambiguity rather than the resolution of it: once the
caller's bank is fixed the three bytes are fixed too, and what they do not name
is which window the CPU is in when it arrives. A same-bank and a cross-bank
`lcall` are the same three bytes in the window they are read from.

## 7. The closure's own check: the 17 pairs outside the 1288

The 11 own-live/other-erased pairs are the shape that would *falsify* the
same-bank assumption, so a contradiction among them is evidence **the walk is
wrong**, not that a cross-bank call exists. The 6 both-erased pairs should be
attributed to neither bank, since both hold erased flash at the target.

| caller | target | own / other | sites | closure verdict |
|---|---|---|---:|---|
| `bank0` | `0xF467` | `other` / `erased` | 2 | unreached |
| `bank0` | `0xF485` | `entry` / `erased` | 2 | unreached |
| `bank0` | `0xF493` | `entry` / `erased` | 2 | unreached |
| `bank0` | `0xF495` | `entry` / `erased` | 1 | agreeing |
| `bank0` | `0xF498` | `other` / `erased` | 4 | agreeing |
| `bank0` | `0xF499` | `entry` / `erased` | 4 | agreeing |
| `bank0` | `0xF4A4` | `entry` / `erased` | 7 | agreeing |
| `bank0` | `0xF4AB` | `entry` / `erased` | 4 | unreached |
| `bank0` | `0xF4B3` | `entry` / `erased` | 2 | unreached |
| `bank0` | `0xF4C1` | `entry` / `erased` | 2 | unreached |
| `bank0` | `0xF566` | `erased` / `erased` | 1 | unreached |
| `bank0` | `0xF583` | `erased` / `erased` | 1 | unreached |
| `bank0` | `0xFAE8` | `erased` / `erased` | 1 | unreached |
| `bank0` | `0xFE0F` | `entry` / `erased` | 3 | agreeing |
| `bank0` | `0xFF90` | `erased` / `erased` | 1 | unreached |
| `bank1` | `0xF902` | `erased` / `erased` | 1 | unreached |
| `bank1` | `0xFF63` | `erased` / `erased` | 3 | unreached |

**11 own-live/other-erased pairs, 0 contradicting. 6 both-erased pairs, 0
attributed to a bank at all.** Both are what they should be, and both are pinned.

```console
$ python3 -c '
import csv
SHORT = {"attributed-same-bank": "agreeing", "attributed-cross-bank": "contradicting",
         "still-ambiguous": "still ambiguous", "unreached": "unreached"}
rows = list(csv.DictReader(open("ec/annotations/bank-attribution-pairs.csv")))
for r in rows:
    if "erased" in (r["own_bank"], r["other_bank"]):
        print("| `{}` | `{}` | `{}` / `{}` | {} | {} |".format(
            r["caller_bank"], r["target"], r["own_bank"], r["other_bank"],
            r["sites"], SHORT[r["verdict"]]))
'
```

The five that agree are the strongest same-bank confirmations available without a
disassembler, and the paths say why. `0xF495` and `0xF4A4` are call-derived
entry points three hops from the `bank0` **seed** `0x84EB` (named by the
trampoline at common `0x153A`) — `0x84EB` → `0xF239` → `0xF1E9` → `0xF495` —
and `0xF498`/`0xF499` are the two instructions after `0xF495` itself. `0xFE0F` is
one hop from the `bank0` **seed** `0xFE00` (trampoline at common `0x1630`), and
is the only one of the five two independent paths reach. In all five, bank 1
holds erased flash at the target, so the same-bank reading is the only one that
lands on code at all.

## 8. What is not claimed

- **Not "proved to be in bank N", anywhere.** Every attribution is *attributed
  by this closure*, with the walk's framing risk stated in §4 rather than at the
  end.
- **Not "the closure did not reach it, so it is not code."** A negative is a
  coverage statement about the seeds and the bounds. The 398 and the
  unreached `0xDFD0` are both of this kind.
- **Not "207 cross-bank calls exist."** They are pairs the closure does not
  support as same-bank. §3 says what the two readings are and that neither is
  settled.
- **Not a verdict on the same-bank assumption.** The residue is 398, the
  agreeing population is 568, and a coverage number is not a verdict. The
  assumption is unverified in the §4c sense `bank-call-audit.md` §6 already
  states; this file adds an independent line for 775 of the pairs and does not
  close the question for the rest.
- **Not a region map.** `bank-attribution-regions.csv` is the per-run form of
  this closure, with entry-point counts and bound reasons, for the region map
  (#50) to consume the way it wanted `index-table-spans.csv`. It is not one:
  those runs inherit the walk's framing risk, and a region map that folded them
  in as fact would launder that risk into a name.
- **No `registers.yaml` `status:` moved, and none could have.** Nothing here is
  about a register; this is Python walking a `bytes` object.
- **No live test ran and none is proposed.** Nothing in this work needs the
  machine. If a behavioural check is ever wanted, that is a separate
  `needs-hardware-test` issue and a human's.

## 9. Follow-ups this hands on

- **The reset vector and the interrupt vectors as additional seeds.** The single
  change most likely to move the 398, and the one whose result would say most
  about whether the residue is seeds or bounds.
- **The `jmp @a+dptr` dispatch as a closure edge**, now that the sites are
  enumerated: 7 in bank 1 at the addresses in §5, plus the 15 index-table
  handlers behind the common-area `0x7151` reader once the table contents are
  enumerated as edges. This needs the table→target mapping, which
  [`index-table-entries.csv`](index-table-entries.csv) already carries.
- **The region map (#50)** consuming
  [`bank-attribution-regions.csv`](bank-attribution-regions.csv) — with the
  caveat in §8 about what those runs are.
- **A function-boundary set**, which is the only thing that would turn
  "attributed by this closure" into a claim a banked entry point can carry.
- **`offset_for_runtime()`** stays as it is. Its same-bank reading is
  contradicted by nothing here: 568 pairs agree with it, 398 are outside this
  closure's reach, and 207 are the open population above.
