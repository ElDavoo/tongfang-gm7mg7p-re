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
as `movx a,@dptr`, so the callee does load the byte. Resolving it that way is
`--callee-depth 1`'s question and not this one's, and `--callee-depth 1` does
not reach a handoff it only finds after a follow, so **this cell is still
direction-unresolved by the repository's own tools** and closing it is
`--callee-depth 2`'s.

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
for the follow to continue at and the reason on the row is `ret`. Two
measurements turn that from a shrug into a stated reason:

* A byte scan of the whole PD image finds **exactly seven** units matching
  `lcall 0xF739 ; mov dptr,#0x07d0 ; ret`, and they are these seven runtimes.
  (There are 37 `lcall 0xF739 ; mov dptr,#<addr>` units in all, across 14
  distinct addresses — an accessor-stub family, of which seven happen to load
  `0x07D0` and return.)
* A scan of the same image for `lcall`/`acall` targeting any of the seven
  finds **none**. So these are not called; whatever reaches them is not a
  direct call in the bytes.

What reaches them, and therefore where the `0x07D0` access happens, is
**open**. A computed dispatch and a table this decode walked into are both
consistent with what was measured, and this file does not choose between them.
`ec-0x07d0-sites.md` §5's blind spot is the neighbouring question — a
`90 07 d0` byte pattern is also what a table entry looks like — and a table
would mean `sites_for()` is counting entries rather than code. That is a
follow-up, not a claim.

**So the 7 cells are: the walk gives up, and not because the method ran out.**
It reached a `ret` and stopped, which is the correct answer for a single-path
walk; the register may well be accessed by the code that calls these stubs.
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
