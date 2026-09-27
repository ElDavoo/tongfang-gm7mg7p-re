# How many entries to the divide-down scheduler is one case-`0x0A` turn (issue #1183)

**The answer is 200, and it is a count of entries to `common 0x0D7B` — not a
period, not a rate, and not convertible to either from this image.** `0x0E5B`,
the longer arm the same reset drives, is every 12,000. Everything below is a
reading of the committed image; nothing ran on hardware and nothing ran on
Windows, so nothing here is deferred to a human at the machine for that reason.

The lead is the limit, because the limit is what a reader is most likely to
drop. Four separate things would have to be known before "200" could become a
time, and they are listed in [§5](#5-why-no-rate-follows). The one a reader is
most likely to combine by accident is the third: the poller's own period
against the flag is itself unestablished, so **not even "200 ticks" is
licensed**, let alone "200 ticks of some length".

This closes the second of the two gaps
[`charge-target-caller-chain.md`](charge-target-caller-chain.md) §4 named. The
first — the tick's own period — is untouched and still open, so §4 there still
does not yield a rate.

## The issue had the polarity backwards, and §1 already had it right

The issue read `0x0D85 jnb acc.0,0x0D8B` as "odd `0x44` takes the `0x0D8B` arm,
even `0x44` falls through to `0x0D88 ljmp 0x0E2E`". **`jnb` jumps when bit 0 is
clear**, so it is the other way round:

```
0x0D81  05 44     inc  0x44
0x0D83  e5 44     mov  a,0x44
0x0D85  30 e0 03  jnb  acc.0,0x0D8B    ; bit 0 CLEAR -> jump: 0x44 even
0x0D88  02 0e 2e  ljmp 0x0E2E          ; 0x44 odd falls through to here
```

An **even** `0x44` reaches the ladder at `0x0D8B`; an **odd** one abandons the
frame. `0x0DCB jnb acc.0,0x0DD1` is the same shape on `0x45`, and the
`charge-target-caller-chain.md` §1 listing already printed both correctly
(`docs/findings/charge-target-caller-chain.md:59`). So **this is a gap closed,
not a retraction of §1** — only its §4 follow-through and §5's second open end
were wrong, and both are corrected in place there.

Two further consequences follow, and both invert what the issue expected:

- **The four `lcall`s at `0x0DA0`/`0x0DA5`/`0x0DAA` (and the `0x46` pair at
  `0x0DB6`/`0x0DBB`) are reachable.** The ladder's tests are for `0x44` of 4, 6,
  8 and 2 — all even — and even is precisely the arm that is taken.
- **`0x44` is not 1 on every entry, and `inc 0x45` does not fire every entry.**
  Both are below.

`ec/decompiled/common/0D7B.c:20` reads it correctly all along
(`if ((DAT_INTMEM_44 & 1) != 0) { FUN_CODE_0e2e(); return; }`), so the committed
`.c` and `.asm` never disagreed with each other. The issue was the outlier.

## The cycle

The ladder is a running subtraction, and that is the one piece of arithmetic
worth stating carefully, because the immediates chain:

| address | instruction | A becomes | branch | `0x44` selected |
|---|---|---|---|---|
| `0x0D90` | `add a,#0xfc` | `0x44 - 4` | `jz 0x0DA5` | 4 |
| `0x0D94` | `add a,#0xfe` | `0x44 - 6` | `jz 0x0DAA` | 6 |
| `0x0D98` | `add a,#0xfe` | `0x44 - 8` | `jz 0x0DAF` | 8 |
| `0x0D9C` | `add a,#0x06` | `0x44 - 2` | `jnz 0x0DC0` | 2 (the fall-through) |

The second `add a,#0xfe` tests `0x44 - 6`, not `0x44 - 2` — the deltas
accumulate. And the last arm is `jnz`, so `0x44 == 2` is the value that *falls
through* to the `lcall` at `0x0DA0` while everything else branches to the clear.
Reading that one the other way round would put `0x44` of 10 on the `lcall` arm
and 2 on the clear — and the count would come out the same by accident, which
is why the test asserts the branch's polarity and not only the value.

So the whole ladder, per entry:

| `0x44` | what happens |
|---|---|
| odd (1, 3, 5, 7, 9) | `ljmp 0x0E2E` at `0x0D88` — the frame is abandoned |
| 2 | `lcall 0x0E37` |
| 4 | `lcall 0x0E3A` |
| 6 | `lcall 0x0E3D` |
| 8 | `inc 0x46`, then `0x0E40` or `0x0E43` on `0x46`'s parity |
| 10 (and any larger even) | `clr a ; mov 0x44,a` at `0x0DC0` |

**`0x44` therefore counts 1…10**, and `0x0DC3 mov a,0x44 ; jnz 0x0E1D` falls
through to `inc 0x45` on the single entry where the clear ran. **`inc 0x45`
fires on one entry in ten.** That is the whole of the divide factor's first
term, and it is the step the issue could not decide.

`0x45` then counts up. `0x0DCB` sends odd values to `ljmp 0x0E46` and even
values to the inline case table at `0x0DD6`, whose nine keys are
`0x02`…`0x12`. **The first even value past the end is `0x14`**, which reaches
the default arm at `0x0E0D` — clears `0x45`, increments `0x47`, and on the
`0x3C` wrap calls `0x0E5B`.

**One case-`0x0A` turn is 20 `inc 0x45` firings, and each is 10 entries, so 200
entries to `0x0D7B`.** `0x0A` → `0x0A` spans `0x0B`…`0x14` (10 steps, the last
taking the default arm) then `0x01`…`0x0A` (10 more). `0x47` rides the same
reset, so `lcall 0x0E5B` is every `0x3C` of those: **12,000 entries**.

The period is **start-independent** — the same 200 from every starting
`(0x44, 0x45)` tried, because `0x44` is forced into 1…10 within two entries of
any start. The *phase*, which entry number the first case-`0x0A` lands on, does
depend on the reset values of `0x44` and `0x45`, and **the image does not
establish those**. So 200 is a period and the phase is open; a reader wanting
"the first one is at entry N" has no N here.

### The `ret` at `0x0E1D` returns to the poller, not into the table

This is the non-obvious part, and "the `ret` falls into the jump table" is the
obvious wrong reading. `0x7151` opens `d0 83 d0 82` = `pop 0x83 ; pop 0x82`:
it consumes the return address that its **own** `lcall 0x7151` at `0x0DD3`
pushed, and never pushes it back. So the `ret` at `0x0E1D` returns to
**`0x0CF8`** — the poller's own instruction after `lcall 0x0D7B` — not into
`0x0D7B` and not into the table bytes at `0x0DD6`. Every case arm and the
default arm unwind to the poller. The counters are written before the jump, so
the count is unaffected either way; it is worth saying because a reader
following the stack will otherwise have to work it out.

## The one assumption the count rests on

The ladder is only reached if `lcall 0x0E34` at `0x0D8B` returns. `0x0E34` is
`ljmp 0x153A`, and `0x153A` is `90 84 eb 02 11 00` = `mov dptr,#0x84EB ; ljmp
0x1100` — a BL51 far-call stub. **The stub uses `ljmp`, not `lcall`, so it
pushes nothing**, so the banked routine's `ret` lands on the address `0x0D7B`'s
`lcall` pushed, which is `0x0D8E` — the instruction after the call. The chain
`12 a0 0e`…`02 b3 8e` at `0x84EB` tail-jumps to `0xB38E`, and every branch out
of `0xB38E` lands on a `ret` (`0xB3D1`, `0xB3D8`, `0xB3DC`, `0xB3E3`, and
`0xB3EE`/`0xB404` past the last one).

**This is a trampoline design property plus consistency with a working charge
target, not a proof.** If the arm did *not* return, `0x44` would climb through
even values forever, `0x45` would never increment, and case `0x0A` could fire at
most once — which is inconsistent with a machine that maintains a charge
target. That is an inference from behaviour, and it is labelled as one here
rather than folded into the count silently. The count is **conditional** on it.

## Falsifier 1 — is `0x44` private? Not provably, and the issue's sites do not survive their bytes

`scan_refs.py` scans only `MOV DPTR,#imm16`, which is XDATA and cannot see a
direct internal byte at all, so nothing in the tree covered this question.
`ec/tools/intmem_refs.py` is new for it: a direct internal-RAM byte census over
the 17 opcodes whose operand names a direct address, with per-region
attribution and an `in_data_region` label from
`ec/annotations/data-regions.yaml`. **Every count below is "not found by this
method"** — indirect access is invisible to it, and the bit-addressable forms
name bits, so `d2 44` is a write to a bit of byte `0x28`, not to byte `0x44`
(the issue says to exclude them, and it is right to).

```console
$ python3 ec/tools/intmem_refs.py ec/firmware/GMxMGxx_11.800 0x44
```

| encoding | file offsets | region / runtime |
|---|---|---|
| `05 44` `inc 0x44` | `0x0D81`, `0x0B0AC`, `0x12E66`, `0x13540` | common `0x0D81` (the scheduler's own); bank0 `0xB0AC`; **bank1** `0xAE66`, `0xB540` |
| `f5 44` `mov 0x44,a` | `0x0DC1` only | common — the scheduler's own clear |
| `e5 44` `mov a,0x44` | `0x0D83`, `0x0D8E`, `0x0DC3` (own), `0x295CB` (pd-image) | — |

**Three of the four `inc 0x44` sites are not references to `0x44` at all — and
only one of the three is a framing artefact.** The issue's census is wrong in
four citable ways, and the distinction between a *displaced decode* and a
*correctly framed instruction read as the wrong thing* is the point of listing
them separately: a frame score catches the first and is blind to the second.

1. **"common `0x0B0A`" is not a hit.** That address decodes to `04 f0` =
   `inc a ; movx @dptr,a`. The site the scan finds is `0x0B0AC`, whose bytes
   are `e0 30 02 05 44 04 f0 80` — a `movx a,@dptr`, a `jnb`, then
   `orl a,#0x04`. The `05` is the `jnb`'s displacement and the `44` is the
   `orl`'s opcode. `converges_from` gives **0 of 24** onto that pair, so this
   one *is* a displaced decode.
2. **"`0xAE66` and `0x0B540` are bank0" is a region mislabel.** The runtime
   addresses are right; the region is **bank1**
   (`trace_xdata_refs.REGIONS`: bank1 runtime = `0x8000 + (off - 0x10000)`).
3. **Both bank1 sites are `mov dptr,#0x0544` — an XDATA address.** The bytes at
   `0x12E65` and `0x1353F` are `90 05 44`, a real `mov dptr,#0x0544`, and the
   low two bytes of an XDATA pointer are not a reference to internal byte
   `0x44`. This one is **not** a misframing: `converges_from` gives 23 of 24
   and 24 of 24, because these are correctly framed instructions. That makes
   it the sharpest of the four corrections and the one a frame score alone
   would have passed — the bytes are real code, and reading them as a counter
   is reading the wrong *address space*, which no framing evidence can catch.
4. **The four "readers" at `0x0BF45`/`0x0C449`/`0x0CB16`/`0x0CBF2` are an
   immediate, not a reference.** The bytes there are `74 44`, and the opcode is
   `0x74` — `mov a,#0x44`, an immediate load of the *constant*. The issue read
   the pair as `e5 44`, the same two bytes with the other opcode and a
   different meaning. The framing here is 23 of 24, so like the bank1 pair this
   is a correctly framed instruction being read as the wrong thing rather than
   a displaced decode; the `74` one byte earlier also happens to be the
   displacement of a preceding `20 06 74` = `jb 0x20.6,0xbfba`. There is no
   `e5 44` and no `74 44` (as `mov 0x44,#imm`) instruction at any of the four.

**The residual risk is real and is not waved away.** The two banks alias one
`0x8000`–`0xFFFF` window, so banked and common code do not run concurrently —
but **the `lcall` arms run banked code with `0x44` live and nonzero**, and that
window is exactly where a banked writer of `0x44` would fire. Whether any is
reached on this path is **not established**. So the correct statement is: `0x44`
is not provably private, the count is conditional on no other code touching
`0x44` mid-cycle, and if one did, the even arm's ladder test would be skipped
and the count would shift.

### The frame score is evidence, not proof — and `0xE434` is why

`intmem_refs.py` prints `converges_from`'s onto/over pair per site and **never
filters on it**, because a filter that dropped the low scorers would make a
future scan's zero look like absence. That restraint is not decoration. The
`0x45` census turns up `bank1 0xE434` at **24 of 24** — a score a reader would
take as settled — and it is a data island. The bytes are
`03 44 44 03 45 45 03 46 46 05`: a run of repeated single-byte values that a
linear walk steps through cleanly precisely *because* every one of them is a
1- or 2-byte instruction. It sits in the gap between `bank1/E3B5.asm` and
`bank1/E490.asm`, in no committed listing. This is the `bank0,D091` standing
warning made concrete, and it is why the column is a pair a reader
adjudicates rather than a verdict.

## Falsifier 2 — `0x45` and the two prologue calls

`05 45` `inc 0x45` at `0x0DC7` and `0x244E3` (pd-image `0x44E3`); `f5 45`
`mov 0x45,a` at `0x0E0E` only. So the issue's "written only at `0x0DC7` and
`0x0E0E` in the main EC" is **right for the main EC**; the other two are a
different program (the PD image) and a different bank, and saying so precisely
is the whole of the correction — "private" would overclaim.

The census does turn up two more EC-side `0x45` sites, and both are phantoms:
`bank1 0xAD89` is the middle and last byte of `02 c2 45` = `ljmp 0xC245`, which
`ec/decompiled/bank1/AD88.asm` commits as its own first and only instruction;
`bank1 0xE434` is the data island above.

The two prologue calls, which the issue says "re-enter the far-call stub table":

- **`lcall 0x386F` at `0x0D7B` is a nine-byte local routine** (`0x386F`–`0x3877`):
  `mov r0,#0xad ; mov a,@r0 ; cjne a,#0x33,+0x02 ; setb 0x26.3 ; ret`. It
  touches internal `0xAD` and bit `0x26.3` and **reaches no writer of `0x45`**.
- **`lcall 0x0E1E` at `0x0D7E`** is `setb 0x27.0 ; mov r7,0x40 ; swap a ; anl
  a,#0x0f ; jnb acc.0,+0x02 ; setb 0x26.7 ; ljmp 0x152E`, and it tail-jumps to
  the far-call stub `0x152E` = `mov dptr,#0x849D ; ljmp 0x1100`, i.e. bank0
  `0x849D`. It reads `0x40` and sets two bits; it does not name `0x45`.

The honest ceiling: **none of the 403 stubs is statically known to write
`0x45`, and that is "not found by this method", not "cannot".**

## Falsifier 3 — how often `0x0D7B` is entered at all: one new fact, one refusal

`12 0d 7b` occurs **exactly once** in the image, at file `0x0CF5`, inside
`ec/decompiled/common/0C86.asm` — already a row in
`ec/annotations/bank-call-targets.csv:355`. The issue's companion claim that
`0d 7b` "appears once in the image as a constant" is **true but not independent
evidence**: `0x0CF6` is that same `lcall`'s operand byte. One fact, not two.

**The new fact, and it is worth having — the poller clears the flag *before*
the call:**

```
0x0CF0  30 35 1c  jnb  0x26.5,+0x1c
0x0CF3  c2 35     clr  0x35        ; flag cleared BEFORE the call
0x0CF5  12 0d 7b  lcall 0x0d7b
0x0CF8  90 00 7e  mov  dptr,#0x007e
```

so **one pass of `0x0C86` enters `0x0D7B` at most once**, and the arm is not
re-entered within the pass. What the poller's own period is *relative to the
flag* is **not established** and is not this issue — it is named in
[§5](#5-why-no-rate-follows) and deliberately left open.

## The `00 00 0e` sentinel, and how `0x0E0D` is reached

Cited rather than re-derived, because it is
`task_call_table.py:236`'s rule and re-arguing it here would be a second
source. The table ends `0x0DF1: 00 00 0e`; an address of zero is what tells
`0x7151` it has run past the end, and it then takes the *next* triple's address
as a default arm. In the dispatcher's own bytes, `0x715F`/`0x7160` `inc dptr`
twice to `0x0DF3` and read `0x0DF3`/`0x0DF4` = `0e 0d` into DPTR, so
`jmp @a+dptr` lands on **exactly `0x0E0D`**.

## 5. Why no rate follows

Four separate refusals, each named, so a reader cannot combine them by
accident:

1. **200 is a count of entries to one function, not a period.** It is a period
   *of the counter state machine*, and that is all it is.
2. **The tick period is unestablished.** `0x0E5E` writes `0x06` to `0x8A` and
   `0xF1` to `0x8C`, but `TMOD` at `0x89` is never read, so the timer mode — and
   with it the interval — is unknown. Carried forward from
   `charge-target-caller-chain.md` §4 and unchanged by this file.
3. **Counts to seconds additionally needs an oscillator frequency, which
   appears nowhere in the tree.**
4. **The poller's own period relative to the flag is also unestablished**, so
   even "200 ticks" is not licensed. This is falsifier 3's open half, and the
   issue itself says it is not this issue.

## What was not done

- **No rate, period, interval or frequency** is written down anywhere above, and
  the four refusals travel with the number rather than sitting in a footnote.
- **The `0x0E2E` slot's own unwind** — what `0x383A` does, and whether the
  chain re-enters — is untouched. It is `charge-target-caller-chain.md` §5's
  first open end, the count does not depend on it, and §5 says so.
- **The poller's entry frequency** is falsifier 3's open half; only "at most
  one entry per pass" is delivered.
- **No `status:` moves** in `ec/annotations/registers.yaml`. `0x44`–`0x47` are
  internal RAM, and a decode is not the behavioural evidence a status change
  would need. `ec/ghidra/xdata-symbols.csv` is untouched and is generated, so
  it is not hand-edited.
- **No hardware and no Windows.** Nothing here needs either, so nothing is
  deferred to a human at the machine for that reason. No live timing was taken
  and no register was read.
- **`call-graph-callees.csv`, `bank-call-targets.csv`, `task-call-table.csv`
  and `xdata-export-ownership.csv` are cited, not regenerated** — another
  branch may be rebuilding them. The `common 0D7B` annotation row is added and
  the default `--mode export-only` re-export ran, so `0D7B.{asm,c}`,
  `0C86.c`, `index.csv`, `listing-index.csv`, `manifest.csv`, `c-digests.csv`
  and `cross-decoder.csv` move; `c-digests.csv` and `cross-decoder.csv` carry
  a pre-existing regeneration drift alongside this change, which was measured
  by running the same export on a pristine tree and is named here rather than
  presented as this row's doing.
- **No gate entry for `intmem_refs.py`.** `.github/workflows/` and
  `.github/actions/` are off limits to this pipeline's token, and
  `charge-target-caller-chain.md` §7 already establishes that a **seventh**
  `docs/ci/agent-gates-*.patch` cannot compose against the committed script:
  `agent-gates-disasm8051-self-test.patch` hunk 1 is `@@ -127,7 +127,9 @@` and
  rewrites `:130`, the only line a new list entry can be appended to. So no
  patch is prepared, and this is said rather than left silent. Landing it needs
  a human to land the disasm8051 patch first. The tool carries its own
  `--self-test` for the same reason `scan_refs.py` has none in any gate.

## Reproducing it

From the repository root. Every command reads only committed inputs — no
Ghidra, no network.

```sh
# the framing oracle first, per the house order
python3 ec/tools/disasm8051.py --self-test

# the polarity, the ladder, the clear and the gate that reads it back
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D7B -n 12 --runtime 0x0D7B
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0DC0 -n 6  --runtime 0x0DC0

# the default arm, and the sentinel that reaches it
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0E0D -n 8  --runtime 0x0E0D
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x7151 -n 20 --runtime 0x7151

# the poller clears the flag before the call
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0CF0 -n 6  --runtime 0x0CF0

# the far-call stub the count's premise rests on
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x153A -n 2  --runtime 0x153A

# the writer census, and the tool's own pins
python3 ec/tools/intmem_refs.py --self-test ec/firmware/GMxMGxx_11.800
python3 ec/tools/intmem_refs.py ec/firmware/GMxMGxx_11.800 0x44 0x45

# the four phantoms, one at a time
for a in 0x0B0AC 0x12E65 0x1353F 0x0BF45; do
  python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at $a -n 2
  python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --converge --at $a
done

# the count itself, computed from the image rather than asserted
python3 -m unittest discover -s ec/tools -p test_scheduler_cycle.py
```

The 200 is computed by `TheCounterArms.step()` walking the counter arms as the
bytes read, so a changed ladder constant, a changed case table or a changed
image moves it and the failure says so. A literal `200` in an `assertEqual`
would have kept passing through every one of those.
