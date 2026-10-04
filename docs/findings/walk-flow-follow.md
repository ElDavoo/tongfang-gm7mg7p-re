# The `none` column re-decoded on one path past the branch, and the 7 cells of 11 that stay `none` with a reason

(2026-09-27, issue #40. Static reading of one committed image through
`ec/tools/walk_flow_follow.py` over `ec/firmware/GMxMGxx_11.800`, with the
three EC-side answers hand-checked against `r2 -a 8051`. No capture opened, no
EC, no hardware, no Windows, no `registers.yaml` row touched, no committed
table re-cut.)

[`static-refs-audit.md`](../../ec/annotations/static-refs-audit.md) §5.3
hand-checked all three of its EC-side `none` cells with `r2 -a 8051` and found
every one to be the walk giving up at a branch rather than a site that does
nothing. It recorded the answers as prose and left the other eight cells to
`ec-0x07d0-sites.md` §3. **This is the tool that turns the prose into a
measurement**: it re-decodes a site by continuing one path past the
control-flow instruction `walk()` stopped at, and of the **11** `none` cells
§5 carried, **4 now resolve and 7 do not**, each of the 7 with a stated
reason. All 11 rows are in `ec/annotations/flow-follow-none-sites.csv`, and
`walk_flow_follow.py --check` re-derives that file byte for byte.

**Nothing about the decode moved.** `walk()`, `walk_why()` and `classify()` are
byte-identical; the follow lives *beside* them in a new file that imports
them, which is the arrangement `walk-window-terminators.md` (#846) and
`walk_budget_census.py` established. The new flag on
`register_ref_table.py` is opt-in and its depth-0 default output is unchanged
byte for byte. Only `none` sites are re-decoded at all, so every other bucket
is still `classify()` over the bytes `walk()` decoded — which is what makes
"no `static_refs*` count moves" structural rather than a check bolted on
beside it. Worth being precise about the coupling the issue names:
`check_register_counts.py` derives its counts from `sites_for()` and
`region_of()` alone and never calls `walk()` or `classify()`, so a change to
the walk *cannot* move a count. The check is the confirmation, not the thing
that makes it true.

## 1. The three EC-side cells, asserted against r2

`test_walk_flow_follow.py` reads these three out of the committed image and
asserts the verdicts, which are transcribed here from `r2 -a 8051` and so do
not come from the code under test. Issue #40 calls them the regression test
and they are the reason the tool exists.

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa39c; pd 5' /tmp/bank0.bin
            0x0000a39c      900768         mov dptr, #0x0768
        ┌─< 0x0000a39f      30e606         jnb acc.6, 0xa3a8
        │   0x0000a3a2      e0             movx a, @dptr
        │   0x0000a3a3      54fd           anl a, #0xfd
        │   0x0000a3a5      f0             movx @dptr, a
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa848; pd 5' /tmp/bank0.bin
            0x0000a848      900768         mov dptr, #0x0768
        ┌─< 0x0000a84b      b4a506         cjne a, #0xa5, 0xa854
        │   0x0000a84e      e0             movx a, @dptr
        │   0x0000a84f      4410           orl a, #0x10
        │   0x0000a851      f0             movx @dptr, a
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xe066; pd 2; s 0xe091; pd 2' /tmp/bank0.bin
            0x0000e066      90043e         mov dptr, #0x043e
        ┌─< 0x0000e069      8026           sjmp 0xe091
            0x0000e091      e0             movx a, @dptr
        ┌─< 0x0000e092      8009           sjmp 0xe09d
```

and what the tool says about the same three:

```console
$ python3 ec/tools/walk_flow_follow.py ec/firmware/GMxMGxx_11.800 0x0768 0x043E
  file 0x0A39C  bank0     0xA39C
    linear:   no movx found in the decoded window
    followed: read x1, write x1
    via:      fall-through past jnb acc.6,+0x06 at 0xA39F
  file 0x0A848  bank0     0xA848
    linear:   no movx found in the decoded window
    followed: read x1, write x1
    via:      fall-through past cjne a,#0xa5,+0x06 at 0xA84B
  file 0x0E066  bank0     0xE066
    linear:   no movx found in the decoded window
    followed: read x1
    via:      sjmp target 0xE091
```

§5.3 called the first two "reads/RMWs" and the third a read. That is what
comes back. The two `0x0768` cells are read-modify-writes: `movx a,@dptr`,
`anl`/`orl a,#imm`, `movx @dptr,a` — clear one bit, store it back.

**The two strengths are a column apart, and that is the load-bearing part.**
`linear` is what `classify()` says today, `followed` is what the one path this
method chose reaches, and `via` names the instruction that carried the follow.
A site resolved by walking past a branch cannot be read as one resolved where
it sits. Two further weaknesses belong to the same sentence and are not hidden
by it: the **branch-taken arm is not walked** (a conditional's other side may
contain a different access), and **DPTR is not tracked** the way
`walk_branch_arms.py` tracks it, so a `movx` past the branch is charged to the
site's own `mov dptr` on the strength of the decode being continuous.
`walk_branch_arms.py` walks both arms with DPTR tracked and is the stronger
claim for both; this is the single-path reading, and it says so.

## 2. The eight `0x07D0` cells, and the seven that stay `none`

§5.3 recorded these as "seven `lcall 0xF739 ; mov dptr,#0x07d0 ; ret`, one
`jnz`". That description turns out to be exact, and the follow sorts them into
one that resolves and seven that do not.

**The `jnz` one (runtime `0x4B40`, file `0x24B40`) resolves, to a handoff.**
The fall-through of the `jnz` is an `lcall 0x34A5`, and `classify()` reports a
DPTR handed to a call — a different verdict from "no movx", and the reason
`register_ref_table.py --callee-depth 1` exists:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x4b40; pd 3' /tmp/pd.bin
            0x00004b40      9007d0         mov dptr, #0x07d0
        ┌─< 0x00004b43      7012           jnz 0x4b57
        │   0x00004b45      1234a5         lcall 0x34a5
```

This lands in `other->flow`, not in `read->flow`, and deliberately so. A
handoff found one level down is a weaker claim than a handoff at the site, so
`flow_bucket()` is deliberately not `bucket()` and the two never share a
column. For the record and **not as this tool's claim**: `r2` decodes `0x34A5`
as `movx a,@dptr`, so the callee does load the byte.

**Correction (issue #1103): the cell now carries a direction, in a column that
names both hops.** `--callee-depth 1` given together with `--follow-flow`
resolves a handoff the follow reached, by decoding the callee's entry point the
way depth 1 always did — the resolver was simply never handed the segment the
follow landed on. `0x4B40` is now
`other->flow->read`, with `flow_via` = `fall-through past jnz +0x12 at 0x4B43`
and `callee` = `0x34A5`:

```console
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 \
  --callee-depth 1 --follow-flow --csv | grep 0x24B40
0x07D0,DBD1 (DSDT name; ECSpec calls the same byte BATTERY_CHARGE_LIMIT_DOWN),0x24B40,pd-image,0x4B40,DPTR handed to a call reached only by following a branch -> callee reads,jnz +0x12,0x34A5,"movx a,@dptr",,fall-through past jnz +0x12 at 0x4B43
```

The column is a new one and not `read->flow` or `handoff->read`, because the
cell is now two hops from the site where each of those is one: a branch, then
a call. `two-hop-dptr-handoff.md` is the write-up and
`two_hop_census.py` records which cells took each new hop.

**The seven that stay `none` are all one shape, and the shape is the reason.**
`0x4C15`, `0x4C1C`, `0x4C23`, `0x52F2`, `0x5322`, `0x7B10` and `0x8572` are
byte-identical 7-byte units, `12 F7 39 90 07 D0 22`:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x4c19; pd 6' /tmp/pd.bin
            0x00004c19      12f739         lcall 0xf739
            0x00004c1c      9007d0         mov dptr, #0x07d0
            0x00004c1f      22             ret
            0x00004c20      12f739         lcall 0xf739
            0x00004c23      9007d0         mov dptr, #0x07d0
            0x00004c26      22             ret
```

A `ret` is the end of the routine and has no fall-through, so there is nothing
for the follow to continue at and the reason on the row is `ret`. Three
measurements turn that from a shrug into a stated reason.

* A byte scan of the whole PD image finds **exactly seven** units matching
  `lcall 0xF739 ; mov dptr,#0x07d0 ; ret`, and they are these seven runtimes.
  (There are 37 `lcall 0xF739 ; mov dptr,#<addr>` units in all, across **13**
  distinct addresses — an accessor-stub family. 7 of the 37 end in `ret`, and
  those 7 are exactly the ones loading `0x07D0`.)
* **The unit's entry is three bytes *before* the site.** Each `none` cell is
  the `mov dptr` at entry+3, so the `lcall 0xF739` that starts the unit is at
  `site - 3`: `0x4C12`, `0x4C19`, `0x4C20`, `0x52EF`, `0x531F`, `0x7B0D`,
  `0x856F`. The `r2` transcript above already shows it, anchored at `0x4C19`
  and `0x4C20` — the two entries either side of the `0x4C1C` and `0x4C23` cells.
* So the caller scan has to be anchored at the entry, not at the cell.
  Anchored at the `mov dptr` it finds **no** `lcall` or `acall` at all, and
  that null is a property of the anchor rather than of the image — an earlier
  draft of this file reported it and built "so these are not called" on it.
  Anchored at the entry it finds **two `lcall`s per stub, fourteen in all**,
  13 of them the byte-identical triple
  `lcall <stub> ; lcall 0x347B ; lcall 0x104D` and the 14th
  `lcall 0x4C20 ; lcall 0x38CA ; lcall 0x3497`:

```console
$ python3 - <<'EOF'   # PD image at file 0x20000, mnemonic() from ec/tools/disasm8051.py
import sys; sys.path.insert(0, "ec/tools")
from disasm8051 import mnemonic
pd = open("ec/firmware/GMxMGxx_11.800", "rb").read()[0x20000:]
sites = [0x4C15, 0x4C1C, 0x4C23, 0x52F2, 0x5322, 0x7B10, 0x8572]
entries = sorted(s - 3 for s in sites)
for label, targets in (("mov dptr (site)", sites), ("unit entry (site-3)", entries)):
    hits = [(o, (pd[o+1] << 8) | pd[o+2]) for o in range(len(pd) - 2)
            if pd[o] == 0x12 and ((pd[o+1] << 8) | pd[o+2]) in targets]
    print("%-20s %d lcall sites" % (label, len(hits)))
    for o, t in hits:
        print("   0x%05X  %s ; %s ; %s" % (o, mnemonic(pd, o, o),
              mnemonic(pd, o + 3, o + 3), mnemonic(pd, o + 6, o + 6)))
EOF
mov dptr (site)      0 lcall sites
unit entry (site-3)  14 lcall sites
   0x0488F  lcall 0x4c12 ; lcall 0x347b ; lcall 0x104d
   0x04932  lcall 0x4c12 ; lcall 0x347b ; lcall 0x104d
   0x0496C  lcall 0x4c19 ; lcall 0x347b ; lcall 0x104d
   0x04989  lcall 0x4c19 ; lcall 0x347b ; lcall 0x104d
   0x04AE9  lcall 0x4c20 ; lcall 0x347b ; lcall 0x104d
   0x04B1D  lcall 0x4c20 ; lcall 0x38ca ; lcall 0x3497
   0x05131  lcall 0x52ef ; lcall 0x347b ; lcall 0x104d
   0x051B2  lcall 0x52ef ; lcall 0x347b ; lcall 0x104d
   0x051E6  lcall 0x531f ; lcall 0x347b ; lcall 0x104d
   0x051FE  lcall 0x531f ; lcall 0x347b ; lcall 0x104d
   0x079B3  lcall 0x7b0d ; lcall 0x347b ; lcall 0x104d
   0x07A5A  lcall 0x7b0d ; lcall 0x347b ; lcall 0x104d
   0x0842F  lcall 0x856f ; lcall 0x347b ; lcall 0x104d
   0x0844B  lcall 0x856f ; lcall 0x347b ; lcall 0x104d
```

**The reason the seven stay `none` is a DPTR handoff across a `ret`, not an
unreachable stub.** The unit loads `0x07D0` into DPTR and returns, handing
DPTR to a caller that exists. Every one of those fourteen callers continues
with a call, and both targets of it — `0x347B`, at 13 of the 14, and `0x38CA`
at the 14th — begin `movx a,@dptr`. So the read of `0x07D0` happens **in the
caller**, one call past the site: which is precisely what a single-path walk
cannot see, and precisely what the `ret` stops it reaching. The walk's `ret`
end is still the correct verdict for a single-path walk; what makes it
uninformative here is a handoff the method does not follow.

**What remains open is the caller's own path** — what the fourteen do with
the DPTR they are handed past that first read, and whether the `0x4AE9`
caller, which no committed PD listing spells, is shaped like the other
thirteen. That is a different question from the one the retracted scan was
answering. Whether these seven cells should be re-graded a read is
`--callee-depth`'s question and not this file's.

**The committed call census does not carry these edges**, which is a gap in
the listing export rather than a disagreement with the bytes, so a reader
should not read the two as conflicting. `call-graph-callees.csv` holds one
row for the family, at `0x4C20`, with `inbound=1 lcall=1`; the other six
entries hold no row at all, so of the 14 edges the census carries 1. The one
it does carry is the `0x4B1D` site, which `pd/4D6F.asm` spells as
`lcall 0x4c20`; the other 13 sites have no committed listing that spells
them, and `call_graph.py` parses listings, so it had nothing to read them
from.

**The six entries are functions now, and the census still reads one row — for a
different reason.** Issue #1101 gave `0x4C12`, `0x4C19`, `0x52EF`, `0x531F`,
`0x7B0D` and `0x856F` their `ghidra-functions.csv` rows and their listings, so
the missing-row property above is no longer "these are not functions" but the
census's own shape: `call_graph.py` writes a row per callee a committed listing
reaches, so a callee nothing reaches gets no row at all rather than a row
reading `inbound=0`, and seeding six more *callees* adds no caller. The
regenerated census moves one line and it is not one of the seven — `0xF739`
goes `inbound` 18 → 24 and `callers` 10 → 16, because each of the six new
listings contributes its one `lcall 0xf739` to it — while `0x4C20` is unmoved
and the file is still 1,841 rows. So **1 of the 14 stands, and the reason is
which edges are still unspelled** rather than the wrong-anchor property
retracted above: the thirteen caller addresses below are still in no listing
that spells them, and naming the targets did not and could not add them. Taking
the census to 14 of 14 means seeding those thirteen *caller* functions, which is
the follow-up. The write-up is
[`pd-07d0-accessor-stubs.md`](pd-07d0-accessor-stubs.md).

**One of those thirteen is inside a listing's span without being spelled by
it**, which is the trap that makes a span test and a parse test disagree here.
`pd/4D6F.asm` runs `0x4A12`–`0x4E58`, covering `0x4B1D` (spelled, at
`4D6F.asm:13`) and `0x4AE9` (not spelled, because the listing's `ajmp 0x4b12`
at `0x4A12` skips the block holding it). A listing spanning an address is not a
listing containing an instruction; only the parse tells them apart, and the
span has to be measured in `pd`'s own address space — seven more of the
fourteen reach a span only if a `common`, `bank0` or `bank1` listing is allowed
to cover a `pd` address, which is the conflation
[`pd-common-address-attribution.md`](pd-common-address-attribution.md) is
about.

**So the 7 cells are: the walk gives up, and not because the method ran out.**
It reached a `ret` and stopped, which is the correct answer for a single-path
walk, and the handoff that `ret` carries is one this method does not follow.
The wording is the one `scan_refs.py` and `static-refs-audit.md` already
carry: **"not found by this method", never "this site does not access the
register"**, with `0x07B9` as the standing counter-example.

## 3. What this does not do, and what it refuses to guess

- **The branch-taken arm is not walked.** `walk_branch_arms.py` walks both
  arms with DPTR tracked, and it is a stronger claim. If a cell here stays
  `none` and only the taken arm would settle it, that tool is the next
  question. Folding the two together would make one column mean two things.
- **The decoder's validation is not widened.** That is #37. This adds control
  flow over the same opcode tables and nothing else.
- **`walk()`'s budget is not raised.** `walk_budget_census.py` measured that a
  budget of 64 would rewrite 13 committed `access` cells, 10 of them wrongly,
  and deliberately left it at 8. A budget is not a branch, so the follow stops
  where `walk_why()` stopped and re-uses that function's own token rather than
  renaming it.
- **No callee is followed, and no `inc dptr` span is attributed across a
  follow.** Both are `--callee-depth 1` and `inc_dptr_sites.py`'s questions.
  This is not hypothetical: §2's seven `ret` cells turned out to be exactly
  this — the `0x07D0` read lives in a callee's caller, one call past the site,
  and this tool stops before it rather than charging it to the site.
- **`registers.yaml` is not touched.** No `status:`, no `static_refs*` count,
  no grade. The `none` column is a reading of sites and issue #32 owns the
  grading question.

The tool's own docstring carries the calibration sentences, including the
`0x07B9` counter-example, because a `--csv` cell outlives the file that
explains it. `register_ref_table.py --follow-flow` puts the same distinction in
the table: `read` and `read->flow` are different columns, and a `none` that
survives the follow is still `none`.

## 4. Reproducing it

```console
$ python3 ec/tools/walk_flow_follow.py ec/firmware/GMxMGxx_11.800 \
    0x043E 0x0768 0x07D0 --check
ec/annotations/flow-follow-none-sites.csv: this run reproduces it byte for byte (12 lines)

$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --follow-flow \
  | grep -E '0x043E|0x0768|0x07D0'
| `0x0768` | `SWITCH_STATUS` | 8 | 8 | 0 | 2 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| `0x07D0` | `DBD1` | 254 | 0 | 254 | 157 | 8 | 2 | 0 | 0 | 79 | 0 | 0 | 0 | 1 | 7 |
| `0x043E` | `CPU_TEMP` | 15 | 15 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |

$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
```

The columns after `handoff` are `read->flow`, `write->flow`, `r+w->flow`,
`other->flow` and `none`. `0x07D0`'s `1` is the `jnz` cell of §2 and its `7`
are the seven `ret` cells; `0x0768`'s `2` are the two read-modify-writes of
§1 and `0x043E`'s `1` is the `sjmp` one. The nine committed `window`-column
tables are untouched and their `--check`s reproduce byte for byte — the
fifteen-address sweep is in `walk-window-terminators.md` §1.
