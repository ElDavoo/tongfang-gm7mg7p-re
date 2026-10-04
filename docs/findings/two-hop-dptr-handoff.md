# The two hops that take a DPTR handoff further than one call

## What this settles

`register_ref_table.py` answers "what does this site do with the address" by
decoding the callee's own entry point. Two *shapes* of cell resisted that, for
two different structural reasons, and both now resolve — each into a column
that names both hops and is **weaker** than the one beside it, so neither can be
read as a one-call result:

| shape | the cell was | it is now | how |
|---|---|---|---|
| a handoff the site only reaches **past a branch** | `other->flow` | `other->flow->read` | branch, then call |
| a handoff whose **callee forwards DPTR again** | `handoff->unresolved` | `handoff->callee->read` | call, then call |

The first is the `0x4B40` cell `walk-flow-follow.md` §2 recorded as
direction-unresolved. Its answer was already known by hand — `r2` decodes
`0x34A5` as `movx a,@dptr` — and no tool produced it, because
`site_rows()` bucketed a site first and resolved a handoff second, and only
for the depth-0 `HANDOFF` label. A verdict one branch down was already
`other->flow` by the time the resolver was consulted, so it never was.

The second is what §5.2 of `static-refs-audit.md` recorded as "depth 2 is not
attempted". That sentence is now false in the other direction: the depth *is*
attempted, and a cell only the second hop settled prints in its own column
rather than in the one-hop `handoff->read` beside it.

## The measurement

`ec/annotations/two-hop-dptr-handoffs.csv` is the committed census, one row
per cell that took either new hop, and `two_hop_census.py --check`
re-derives it from the committed image:

```console
$ python3 ec/tools/two_hop_census.py --check
ec/annotations/two-hop-dptr-handoffs.csv: this run reproduces it byte for byte (14 lines)
```

The selection is **definitional, not hand-picked**: a row is emitted when the
site's class at that mode is one of the three resolved members of
`FLOW_CALLEE_CLASSES` or `HANDOFF_DEPTH2_CLASSES`. Nothing in the tool names
an address, so a `registers.yaml` that grows moves the census by
regenerating it. The `mode` column is there because the two shapes are not
comparable — averaging a branch-then-call claim with a call-then-call one is
the mistake the separate columns exist to prevent.

`--check` regenerates every mode the file records whatever `--mode` says. A
single-mode regeneration diffed against a file holding both would report the
other mode's rows as drift, which is the failure
`walk_flow_follow.load_recorded()` exists to prevent on the other side; the
one refusal left is a mode the committed file records and this tool does not
implement, since those rows cannot be regenerated at all.

### Shape 1 — the branch, then the call

Every cell here was `other->flow` before and is `other->flow->read` now.
The `via` column is the branch the follow took and the `callee` column the
call it then resolved, so the row names both hops:

| site | via | callee | `r2` at the callee |
|---|---|---|---|
| `0x24B40` (rt `0x4B40`) | `fall-through past jnz +0x12 at 0x4B43` | `0x34A5` | `movx a,@dptr` |
| `0x26757` | `fall-through past cjne a,#0x02,+0x08 at 0x675A` | `0x37DE` | `movx a,@dptr ; …` |
| `0x2233C` | `fall-through past jnz +0x12 at 0x233F` | `0x34A5` | `movx a,@dptr` |
| `0x2AE73` | `sjmp target 0xAE7D` | `0xAE91` | `movx a,@dptr ; mov r7,a ; inc dptr ; …` |
| `0x26DAA` | `fall-through past cjne r5,#0x03,+0x0f at 0x6DAD` | `0x0FAF` | `movx a,@dptr ; mov r4,a ; inc dptr ; …` |
| `0x2D01D` | `fall-through past jnz +0x27 at 0xD020` | `0x714F` | `movx a,@dptr ; mov 0xf0,#0x17 ; …` |
| `0x2BB50` | `fall-through past jnz +0x0f at 0xBB53` | `0xB293` | `movx a,@dptr ; mov 0xf0,#0x5e ; …` |
| `0x2BD80` | `fall-through past jnz +0x0f at 0xBD83` | `0xB293` | `movx a,@dptr ; mov 0xf0,#0x5e ; …` |

The transcripts are against the flat PD image (`dd if=ec/firmware/GMxMGxx_11.800
of=/tmp/pd.bin bs=64k skip=2 count=1`), so the oracle is an independent
disassembler and not the code under test:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x34a5; pd 2' /tmp/pd.bin
            0x000034a5      e0             movx a, @dptr
            0x000034a6      900420         mov dptr, #0x0420
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x0faf; pd 4' /tmp/pd.bin
            0x00000faf      e0             movx a, @dptr
            0x00000fb0      fc             mov r4, a
            0x00000fb1      a3             inc dptr
            0x00000fb2      e0             movx a, @dptr
```

Two of the eight are worth naming beyond the table. `0x24B40` is the cell the
issue is about, and `0x2AE73` is reached by an **`sjmp`** rather than a
conditional fall-through — the follow treats an unconditional transfer the
same way, because at that point there is no branch to fall through, and the
`via` cell says which of the two it was so the row is not read as a
fall-through it was not.

### Shape 2 — the call, then the call

These are the cells whose first callee is a forwarder. `0xB1F2` and `0x383A`
each pass the DPTR they were given straight on:

| site | first callee | second callee | verdict |
|---|---|---|---|
| `0x204F9` (`0x07E2`) | `0xB1F2` | `0x10C8` | read ×3 |
| `0x2662D` (`0x07E5`) | `0x383A` | `0x0FCB` | read ×3 |
| `0x0B6E8` (`0x089E`) | `0xBADE` | `0x70E4` | read **and write** |
| `0x2B5F9` (`0x0811`) | `0x9A48` | `0x10C8` | read ×3 |
| `0x2951B` (`0x07D6`) | `0xB2F7` | `0x10C8` | read ×3 |

The `LIGHTBAR_BAT_*` cells are the two §5.2 named. The others were not in the
issue and are a **consequence rather than a coincidence**, which is worth
stating rather than leaving to be found later: `0x204F9`, `0x2B5F9` and
`0x2951B` all reach a first callee that is a one-instruction trampoline onto
`0x10C8`. They resolve as a family because they are one.

`0x089E` is the only cell in either shape that is not a read, and it is `r+w`
for a reason the window shows rather than the bucket asserting — `0x70E4`
reads, adds and writes the same DPTR:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x70e4; pd 7' ec/firmware/GMxMGxx_11.800
            0x000070e4      c5f0           xch a, b
            0x000070e6      f8             mov r0, a
            0x000070e7      a3             inc dptr
            0x000070e8      e0             movx a, @dptr
            0x000070e9      28             add a, r0
            0x000070ea      f0             movx @dptr, a
            0x000070eb      c5f0           xch a, b
```

## What is left in the weaker column, and why

Both new column sets keep an unresolved bucket, and the two hold different
things:

* **`other->flow->unresolved`** — the flow-callee is itself a handoff and the
  bound was one call. Two cells are in it, `0x26498` and `0x2A096`, and both
  reach `0x10C8` at `--callee-depth 2`, so a reader who wants the direction
  asks for the deeper bound rather than being told the method gave up.
* **`handoff->unresolved`** — the residue that reaches the `0x10BC`
  `DPTR += A × B` family, which adds to the pointer and never dereferences
  it. There is no direction to report at any depth, so a deeper bound would
  not move them and none is attempted.

A `movc` or `jmp` found past a branch is the third shape, and it is why
`other->flow` survives as a column of its own: those are verdicts, not
handoffs, and there is no callee to resolve. Giving them a `->callee` column
would claim a call that is not there. **That column is empty on this image** —
every cell the follow reached was a handoff — so it is there for the shape
rather than for a row, and the suite builds the `movc` case rather than reading
it. The same is true of the negative arms of `other->flow->`: every flow
callee that settles at all settles as a read on this image, so a callee that
writes, reads-and-writes, or hands DPTR on again is a fixture and not a row.

## What this does not settle

* **The `ret` cells.** The seven `0x07D0` cells that stay `none` in
  `walk-flow-follow.md` §2 are a caller-of-the-stub question — the read lives
  one call past an accessor stub, and every one of the fourteen callers
  continues into `0x347B` or `0x38CA`, which begin `movx a,@dptr` — and that
  is `walk_branch_arms.py`'s shape, not this one. `0x0420`'s R1:R2 handoff is
  the same shape, which is why `handoff-site-warrant.md`'s forward reference to
  this issue now says what remains rather than pointing at a closed issue for
  work nobody has picked up.
* **`check_site_resolution.py`'s census is deliberately still depth 1.** Its
  `site-resolution.csv` stays byte-identical, and two of its tests hold that
  depth. Worth knowing rather than rediscovering as a bug: at depth 2 the
  `0x089E` site would stop being `unresolved-handoff`, so moving that census
  would have moved `test_check_site_resolution.py`'s "0x0420 is the only
  address resting entirely on unresolved sites". Not moved.
* **A second branch.** The follow walks one path past the branch it stopped
  at, and the branch-taken arm is still `walk_branch_arms.py`'s stronger
  claim. Nothing here weakens that.
* **Anything at run time.** Every input is the committed 256 KiB image. A
  `read` is an instruction that loads a byte on a path this method chose out
  of a bounded number of them; no register was read back, no capture opened,
  and a write is not evidence that the EC acts on the value.

## Reproducing it

```console
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1 --follow-flow
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 2
$ python3 ec/tools/two_hop_census.py --check
$ python3 ec/tools/walk_flow_follow.py --check          # unchanged, byte for byte
$ python3 ec/tools/walk_budget_census.py --check        # the window-column tables
$ python3 ec/tools/check_site_resolution.py --check     # still depth 1
$ bash tools/run-tests.sh
```

Depth 0, depth 1 and `--follow-flow` alone are unchanged in both outputs, and
that is asserted **structurally** — the rows are rebuilt the way
`test_walk_flow_follow.py::rows_the_pre_flag_way` rebuilds them and compared
over the whole of `registers.yaml` as it stands — rather than by a digest of
the whole output, because a digest is a value every `registers.yaml` addition
would have to edit.

`--callee-depth 1 --follow-flow` is deliberately *not* unchanged: it gains the
`other->flow->` columns. No committed artifact holds that mode's output.
