# `--callee-depth` follows a chain of handoffs, and the two `LIGHTBAR_BAT_*` sites that were unresolved at depth 1 are reads at depth 2

(2026-10-02, issue #44. Static reading of one committed image through
`ec/tools/register_ref_table.py` over `ec/firmware/GMxMGxx_11.800`, with the
two chains' terminals hand-checked against the `r2 -a 8051` transcript
`ec/annotations/lightbar-bat-flow.md` §3.5 already commits. No capture opened,
no EC, no hardware, no Windows, no `registers.yaml` `status:` touched.)

Issue #42 left two of the eleven `LIGHTBAR_BAT_*` handoffs unresolved, and
`lightbar-bat-flow.md` §3.5 was explicit about why: `0xB1F2` and `0x383A`
each pass the DPTR they were given to a further routine, and a chain resolved
by eye is the one-linear-walk claim `docs/findings.md` §4 warns about. **This
is the tool that follows the chain**, the same way #42 made the tool do depth
1 rather than adding another hand table: `--callee-depth` takes an integer
depth N instead of `choices=(0, 1)`, and at N ≥ 2 it follows a callee that
forwards DPTR again and reports the path it walked.

**The two sites now carry a direction, with the tool's transcript behind it,
and the class is the same bucket at every depth** — `handoff->read` at depth
3 is the same label as at depth 1, and the depth is in a `--csv` column
rather than in the name. That is deliberate: `ec-0x07d0-sites.md` §3 and
`pd-xdata-overlap.md` §3 are hand decodes at one level, and a shared label
makes the cross-check below a like-for-like comparison instead of a rename.

## 1. The two named sites, asserted against the committed `r2` transcript

`ec/tools/test_callee_depth.py` asserts these from the committed image. The
expected chains are transcribed from the `r2 -a 8051` listing in
`lightbar-bat-flow.md` §3.5, not from this tool's own output, so the
suite cannot grade its own homework.

| site | file | chain | terminal window |
|---|---|---|---|
| `0x07E2` | `0x204F9` | `0xB1F2` → `0x10C8` | `movx a,@dptr ; mov r3,a ; inc dptr ; movx a,@dptr ; mov r2,a ; inc dptr ; movx a,@dptr ; mov r1,a` |
| `0x07E5` | `0x2662D` | `0x383A` → `0x0FCB` | `movx a,@dptr ; mov r0,a ; inc dptr ; movx a,@dptr ; mov r1,a ; inc dptr ; movx a,@dptr ; mov r2,a` |

The two windows differ in which register group they load into, which is what
makes them worth pinning separately: a chain that swapped the two links would
still read `callee reads`, and would be caught here.

```console
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 2 --csv \
  | python3 -c "
import csv, sys
for r in csv.DictReader(sys.stdin):
    if r['addr'].startswith('0x07E') and ' -> ' in r['chain']:
        print(r['addr'], r['runtime'], '|', r['class'], '| chain:', r['chain'])"
0x07E2 0x04F9 | handed to lcall/ljmp -> callee reads | chain: 0xB1F2 -> 0x10C8
0x07E5 0x662D | handed to lcall/ljmp -> callee reads | chain: 0x383A -> 0x0FCB
```

The `LIGHTBAR_BAT_*` rows at depth 2, against the same rows at depth 1:

| addr | depth 1 (`read` / `write` / `handoff->read` / `handoff->write` / `handoff->unresolved`) | depth 2 |
|---|---|---|
| `0x07E2` | 7 / 4 / 2 / 1 / 1 | 7 / 4 / **3** / 1 / **0** |
| `0x07E3` | 2 / 2 / 1 / 4 / 0 | unchanged |
| `0x07E4` | 3 / 1 / 0 / 0 / 0 | unchanged |
| `0x07E5` | 5 / 3 / 0 / 1 / 1 | 5 / 3 / **1** / 1 / **0** |

So the 38 PD sites behind the four addresses are 20 read / 16 write / 2
unresolved at depth 1 and **22 / 16 / 0** at depth 2, where before the
`--callee-depth` flag existed at all it was 17 / 10 with 11 unresolved.

## 2. Three more cells move, and one of them is a corroboration

The issue names two. Across every address in `registers.yaml`, **five** rows
change between depth 1 and depth 2, and the suite asserts that set exactly —
as a claim about the image, so a future image that moves a sixth fails by
naming it.

| addr | site | chain | becomes | what it was |
|---|---|---|---|---|
| `0x089E` | `0x0B6E8` | `0xBADE` → `0x70E4` | `r+w` | `registers.yaml` says the direction is "unresolved by this method" |
| `0x0811` | `0x2B5F9` | `0x9A48` → `0x10C8` | read | unresolved at depth 1 |
| `0x07D6` | `0x2951B` | `0xB2F7` → `0x10C8` | read | unresolved at depth 1 |

`0x07D6` is the one worth reading twice: `ec-07d6-07d7-sites.md` §4.4 had
already resolved that site by hand, from committed exports, as a read. The
tool now reaches the same verdict by a path that does not run through those
exports. That is a **corroboration, not a new claim**, and it is recorded as
one — two methods agreeing on one site is one agreement.

`0x089E` is the only cell whose terminal is not one of the `0x10xx` Keil
multi-byte helpers. `0x70E4` is `xch a,0xf0 ; mov r0,a ; inc dptr ; movx
a,@dptr ; add a,r0 ; movx @dptr,a ; ...` — it reads the byte, adds a
register to it and writes it back, which is why the cell is `r+w` and not
`read`. The suite pins that window for the same reason it pins the other
two.

## 3. Both cross-checks hold, at every depth

`0x07D0`'s 79 handoffs must still split 72 to a callee that loads and 7 to
one that stores (`ec-0x07d0-sites.md` §3), and `0x04A6`'s four PD handoffs
must still come out unresolved at any depth, because the `DPTR += A × B`
family at `0x10BC` never dereferences DPTR (`pd-xdata-overlap.md` §3). A
depth-N change that "resolves" those four has a bug, not a result. The suite
asserts both **over the whole file at depths 2, 3, 4 and 8**, so a run that
quietly dropped a site elsewhere would fail the reconciliation rather than
pass the two spot checks.

Both hold. The verdicts are unchanged; only the *reason* on `0x04A6`'s rows
is one hop further out, which is what a `stop` column is for — at depth 2
each of the four names `0x10BC` and says `no direction at 0x10BC: ...`. **That
is this method stopping, not a claim that nothing dereferences those
addresses**; the distinction is the one `docs/findings.md` §4c is about and
the one `ec/annotations/registers.yaml`'s own caveat on `absent` turns on.

## 4. The measurement that bounds the feature — and why the guards are still built

Over the 438 handoff sites in the image, **the longest chain is two links**,
and depths 2, 3, 4 and 8 produce byte-identical rows. N is a fixed point at 2
on this image, so **the depth cap is never load-bearing here**.

```console
$ cd ec/tools && python3 -c "
import yaml, register_ref_table as rrt
from trace_xdata_refs import PD_MARKER, sites_for, walk, classify
d = open('../../ec/firmware/GMxMGxx_11.800','rb').read()
off, magic = PD_MARKER
pd = d[off:off+len(magic)] == magic
regs = yaml.safe_load(open('../annotations/registers.yaml'))['registers']
for depth in (1, 2, 3, 4, 8):
    n = longest = 0
    for _name, a in rrt.addresses(regs):
        for o in sites_for(d, a):
            ins = walk(d, o)
            if rrt.bucket(classify(ins)) != rrt.HANDOFF:
                continue
            n += 1
            longest = max(longest, len(rrt.resolve_handoff(d, o, ins, pd, depth)[3]))
    print(f'depth {depth}: {n} handoff site(s), longest chain {longest}')"
depth 1: 438 handoff site(s), longest chain 1
depth 2: 438 handoff site(s), longest chain 2
depth 3: 438 handoff site(s), longest chain 2
depth 4: 438 handoff site(s), longest chain 2
depth 8: 438 handoff site(s), longest chain 2
```

That is a fact about the image, and it is *not* evidence the cycle guard and
the cap are unnecessary — it is the reason they cannot be tested from the
image. A depth-N recursion with no cycle check passes every image-derived
case in the suite and then recurses until the interpreter gives up on the
first loop a future image contains; a cap that never fires is untested in the
only sense that matters. So both are built as `common`-region byte fixtures
(file offset equals runtime address, as `test_walk_flow_follow.py` does), on
the stated principle that a fixture anchored at an address keeps testing what
it was written to test only until the bytes there change:

- two routines that hand DPTR to each other terminate with the cycle reason
  naming where the loop closed, and do not hang;
- a chain of ten forwarders ending in a reader terminates with the cap
  reason, at depths 1, 2, 3 and 8, and resolves at the depth that reaches
  the end — so the cases above are the cap and not a chain that never
  resolves.

The cap names **the depth that was asked for**, not the budget left when it
fired. A run asked for 8 says `callee-depth cap 8`; naming the remainder
would put `cap 1` on a run that never mentioned 1, and the row would not say
which of the depths a reader could have passed would have carried it further.

The four reasons are distinct strings and none of them is the depth-0
`HANDOFF` label — a `stop` that could be confused with a class would leave a
reader unable to tell a reason from a bucket, and a reader who cannot is back
to the bare `unresolved` the column exists to break up. A negative depth is
refused by name rather than silently treated as 0: `choices` cannot express
"any non-negative N", and a negative depth is not a shallower table, it is a
request to walk a chain backwards.

## 5. What this does *not* settle

**The two `ljmp` tails are still untraced, and that is a walk() limit, not a
depth limit.** `walk()` stops at the first control-flow instruction, so
`0xB1F2` decodes as exactly one instruction (`lcall 0x10C8`, terminator
`flow opcode`) and its `mov a,#0x01 ; ljmp 0x0C46` tail is in no window at
any N. `ec/decompiled/pd/B1F2.c` shows what that tail does — it calls
`write_byte_by_tag_r3(1, ...)` — so "this routine reads" would be **wrong
about the routine** even though it is right about the handed DPTR. Following
the tail is `walk_flow_follow.py`'s existing job, and folding it in here
would change the depth-1 output, so it is left there. The suite asserts the
one-instruction decode so a future relaxation of the flow stop cannot make
the depth-2 claim quietly stronger than this paragraph says it is.

**The `0x0FCB` read count is the walk's, not the routine's.** The tool's
window for `0x0FCB` is eight instructions and ends `max_insns (8) exhausted`,
three MOVX reads in; the instruction after it is `inc dptr`, and at a budget
of 12 the same routine is four reads into `R0`-`R3`, which is what
`pd-0x38-consumers.md` records and what `ghidra-functions.csv`'s `pd,0x0FCB`
row resolves. Both readings are right about the budget each used. The
`read` above is the **direction**, which both budgets agree on; only the count
depends on the budget, and the budget stays at 8. That decision's cost is
`walk_budget_census.py`'s to record, and run over this firmware it reports
that a budget of 64 changes three committed `access` cells, all three verdict
`B` — the same site's own further accesses, none of them a cell the larger
budget gets wrong. Its docstring keeps the figures it had to retract beside
that correction. The suite pins the budget-limited number so a future budget
change cannot rewrite it out from under the write-ups that quote it.

**The honest ceiling, restated because the depth makes it easy to overstate:**

- this is still a static decode of the PD image, and says **nothing** about
  the EC's own `0x07E2`-`0x07E5`;
- a decoded store is not evidence that anything acts on the value, and a
  decoded load is not evidence that anything read it first;
- the claim is about the DPTR that was handed on, not about what the
  forwarding routine then does with it;
- `status:` stays `unknown-not-absent`, and
  `lightbar-bat-flow.md` §5 is still the live probe, still for a human at
  the physical machine. Nothing here was read back from hardware.

**The names stay `unresolved_0xB1F2` / `unresolved_0x383A`.** The tool
settled the handed-DPTR question, not what the routine does with the result,
so the name is still the honest one; a rename would put `index.csv`,
`listing-index.csv`, `reassembly.csv`, `cross-decoder.csv` and two `.c` files
through a re-export for a claim that has not got stronger. That rename is a
separate issue and the PR says so.

## 6. What stayed byte-identical, and what did not

Depth 0 and depth 1 are unchanged, which is the invariant the whole change
rests on — every transcript already pasted in `ec/annotations/` was taken at
one of them:

- `classes_for(0) is CLASSES`, and every site's row at depth 0 is what
  `walk()` + `bucket(classify())` produced before the flag existed;
- the `--callee-depth 1 --csv` output is byte-for-byte the committed table,
  header included;
- the new `chain` and `stop` columns are emitted **only** above depth 1, so a
  depth-0 or depth-1 reader's `cut -d, -f6` keeps working and no committed
  transcript gains an empty cell;
- `reconcile()` still gates: at depth 2 the class buckets sum to the site
  count and main + PD to the file-wide total for every address, and it is
  still red on a dropped site, on a split that does not add up, and on a
  class no column is named for.

**One thing this did not fix, and did not cause.** Two committed artefacts
had already drifted from their own documented reproduction command before
this change — `ec/annotations/pd-0x07d8-ref-table.csv`, whose four rows differ
in `window`/`callee_window` since the switch-case work in #1600, and seven
`ec/decompiled/*.c` files whose `XDATA_*` symbols and `name_basis` predate the
current `registers.yaml`. Running the documented commands on a clean tree
reproduces both, and this change's tool output is byte-identical to the
pre-change tool's on every one of them. Re-cutting them is a separate change
with its own review; flagging it here rather than folding it in.
