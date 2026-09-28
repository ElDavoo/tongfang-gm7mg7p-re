# Who reaches `0xB158` — the charge-target caller chain, and how often it runs (issue #89)

`ec/annotations/charge-target-derating.md` §1 opens with "No direct lcall/ljmp
to 0xB158 was found … it is reached indirectly — a function-pointer table or a
BL51 trampoline. Unresolved." That is still true and still the whole of the
direct-call story; what this file adds is the *path*, which turns out to be
neither of the two mechanisms guessed there. Every hop is verified
byte-for-byte against `ec/firmware/GMxMGxx_11.800`:

```
common 0x0530   timer0 overflow handler: d2 35 = setb 0x35, the _6_5 flag
                                       (bit 5 of internal RAM byte 0x06)
  -> common 0x0C86  poll_flag_bytes_30_to_3b_and_dispatch
    -> common 0x0D7B  inc 0x45, even -> lcall 0x7151 (switch_case_dispatch)
      -> case 0x0A selects common 0x0DFE -> ljmp 0x0E55
        -> common 0x0E55   ljmp 0x157C          the common dispatch block
          -> common 0x157C  90 85 39 02 11 00   the far-call stub table
            -> bank0 0x8539  12 E0 10           a slot in a stride-3 run
              -> bank0 0x853F  12 B1 2C         the next slot in that run
                -> bank0 0xB12C  jb acc.1,0xB158
                  -> bank0 0xB158               charge_target_update
```

Every hop from the `0x0DD6` case table down is re-derived by
`ec/tools/task_call_table.py`, whose `--self-test` pins each against the
committed image and whose `--check` holds the committed
`ec/annotations/task-call-table.csv` (698 rows) to those bytes. The three
hops above it are not: `0x0530` and `0x0C86` are cited from the committed
annotation rows, and the `inc 0x45` / `jnb` gates inside `0x0D7B` are read
off the listing in §1. The tool never reads any of those three addresses.
§4 is where the first two are attributed, and it is the only place the
distinction is drawn.

**The path is closed from the timer interrupt down.** What is *not* closed is
the cycle: how many passes separate two visits to `0xB158` depends on a
counter this file reads but does not follow to its period (§4), and the timer
that raises the flag has a reload whose mode the image does not establish. No
rate is claimed anywhere below.

**This file also corrects an address in two places.** `0x8539` does *not*
`lcall 0xB12C`; it `lcall`s `0xE010`. `0xB12C` is the *next* slot along,
`0x853F`. The conclusion the wrong address supported is unaffected — both are
in the same run and are dispatched together — but the correction is carried in
place at both sites rather than edited away, per CLAUDE.md's rule on
retractions.

## 1. The hops, decoded

**The selector — `common 0x0D7B`, and the case table inline in it.** `0x0D7B`
calls `0x386F`, then `0x0E1E`, then `inc 0x44` and dispatches on that counter
with gates at `0x44 == 2 / 4 / 6 / 8` and a second counter `0x46`. When `0x44`
reads zero it `inc 0x45` and dispatches on *that*:

```
0x0DC3  e5 44     mov  a,0x44
0x0DC5  70 56     jnz 0x0E1D     ; 0x44 still counting -> return
0x0DC7  05 45     inc  0x45
0x0DC9  e5 45     mov  a,0x45
0x0DCB  30 e0 03  jnb  acc.0,0x0DD1   ; even -> the switch
0x0DCE  02 0e 46  ljmp 0x0E46          ; odd  -> a different slot
0x0DD1  e5 45     mov  a,0x45
0x0DD3  12 71 51  lcall 0x7151         ; switch_case_dispatch(0x45)
0x0DD6  0d f5 02  ...                  ; the inline table, 3 bytes per case
```

`0x7151` pops the return address the `lcall` pushed to find that table, so
the table is the data immediately after the call — which is why it is decoded
with the dispatcher's own grammar rather than an assumed one. Nine entries,
`address` then `case` (the shape `bank-call-audit.md` §9 established for this
dispatcher), ending at a triple whose address is `0x0000`, which is the
`jnz` of the dispatcher's `movc`/`jnz` pairs at `0x7157`–`0x7158` and
`0x715C`–`0x715D` saying it has run off the end:

| table addr | case | where it goes |
|---|---|---|
| `0x0DF5` | `0x02` | `sjmp +0x0A` → `0x0E01` → `ljmp 0x0E49` |
| `0x0DF7` | `0x04` | `sjmp +0x0B` → `0x0E04` → `ljmp 0x0E4C` |
| `0x0DF9` | `0x06` | `sjmp +0x0C` → `0x0E07` → `ljmp 0x0E4F` |
| `0x0DFB` | `0x08` | `ljmp 0x0E52` |
| **`0x0DFE`** | **`0x0A`** | **`ljmp 0x0E55`** — the chain |
| `0x0E01` | `0x0C` | `ljmp 0x0E49` |
| `0x0E04` | `0x0E` | `ljmp 0x0E4C` |
| `0x0DF9` | `0x10` | `sjmp +0x0C` → `0x0E07` → `ljmp 0x0E4F` |
| `0x0E0A` | `0x12` | `ljmp 0x0E58` |
| `0x0000` | — | terminator |

So **the chain runs on the passes where `0x0D7B`'s internal byte `0x45` is
`0x0A`**, and on no other value in that table. Every case value in the table
is even, which is consistent with the `jnb acc.0` at `0x0DCB` sending only
even values to the switch at all.

**`common 0x0E2B`–`0x0E5D` — a 17-slot dispatch block.** Seventeen entries at
a stride of 3, sixteen `ljmp` and one `lcall`:

```
0x0E2B  02 15 2E  ljmp 0x152E      0x0E49  02 15 64  ljmp 0x1564
0x0E2E  12 38 3A  lcall 0x383A     0x0E4C  02 15 6A  ljmp 0x156A
0x0E31  02 15 34  ljmp 0x1534      0x0E4F  02 15 70  ljmp 0x1570
0x0E34  02 15 3A  ljmp 0x153A      0x0E52  02 15 76  ljmp 0x1576
0x0E37  02 15 40  ljmp 0x1540      0x0E55  02 15 7C  ljmp 0x157C   <- hop
0x0E3A  02 15 46  ljmp 0x1546      0x0E58  02 15 82  ljmp 0x1582
0x0E3D  02 15 4C  ljmp 0x154C      0x0E5B  02 15 88  ljmp 0x1588
0x0E40  02 15 52  ljmp 0x1552
0x0E43  02 15 58  ljmp 0x1558
0x0E46  02 15 5E  ljmp 0x155E
```

0x0E2E is the odd one out, and it explains the block's shape: it is a
`lcall`, so control *returns* to 0x0E31 — which is itself a tail
`ljmp 0x1534`, so that arm leaves the block without ever coming back to
`0x0D7B`. Every other slot is a tail jump. The block is a set of
independent cases, not a loop: running it runs one slot, and which one is
what the case table in the previous section decides.

The scheduler enters the block at a *different* slot on each arm, and
nothing falls into `0x0E2E`. Scanning the whole image for `12 0e 2e` and
`02 0e 2e` gives exactly one hit, the `ljmp` at `0x0D88`; the slot
immediately before `0x0E2E` is `0x0E2B`, `02 15 2e`, a tail `ljmp 0x152E`,
so control leaves the block there rather than continuing into `0x0E2E`:

| entry site | transfer | lands on |
|---|---|---|
| `0x0D88` | `ljmp 0x0E2E` | `0x0E2E` |
| `0x0D8B` `0x0DA0` `0x0DA5` `0x0DAA` `0x0DB6` `0x0DBB` | `lcall` | `0x0E34` `0x0E37` `0x0E3A` `0x0E3D` `0x0E40` `0x0E43` |
| `0x0DCE` | `ljmp 0x0E46` | `0x0E46` |
| `0x0DFB` `0x0DFE` `0x0E01` `0x0E04` `0x0E07` `0x0E0A` | the case table above | `0x0E52` `0x0E55` `0x0E49` `0x0E4C` `0x0E4F` `0x0E58` |
| `0x0E17` | `lcall 0x0E5B` | `0x0E5B` |

Fifteen of the block's 17 slots are named by one of those transfers. The
two that are not are `0x0E31`, which is the return address `0x0E2E`'s
`lcall` pushes, and `0x0E2B` — the one entry no transfer names and
nothing falls into.

**`common 0x1150`–`0x1AC1` — the far-call stub table, 403 entries, stride 6.**
Each entry is `mov dptr,#<target>` then `ljmp` to a bank-select stub. There is
exactly one such table in the common area; the split is 350 entries to
`ljmp 0x1100` (bank 0) and 53 to `ljmp 0x1114` (bank 1), which is the same
350/53 `find_banks.py` reports and the same 403 `bank-call-audit.md` §3 counts.
All 403 immediates are banked-window addresses (≥ 0x8000), which is what a
table of this kind is *for*, and is also the tool's own check that the run has
not walked off the end of the table into the code after it.

The chain's entry is index 178:

```
0x157C  90 85 39  02 11 00   mov dptr,#0x8539 ; ljmp 0x1100
```

**`bank0 0x8518`–`0x8559` — a 22-entry stride-3 run of transfers.** 0x8539 is
index 11 and 0x853F is index 13:

```
0x8539  12 E0 10  lcall 0xE010     0x853F  12 B1 2C  lcall 0xB12C   <- hop
0x853C  12 91 67  lcall 0x9167     0x8542  12 B4 A8  lcall 0xB4A8
```

**`bank0 0xB12C` — the routine that branches in.**

```
0xB12C  90 07 8E  mov  dptr,#0x078E    ; set bit 3
0xB12F  E0        movx  a,@dptr
0xB130  44 08     orl   a,#0x08
0xB132  F0        movx  @dptr,a
0xB133  90 07 41  mov  dptr,#0x0741
0xB136  E0        movx  a,@dptr
0xB137  20 E0 07  jb    acc.0,0xB141
0xB13A  90 07 A6  mov  dptr,#0x07A6    ; manual-ctrl clear -> High Capacity
0xB13D  E0        movx  a,@dptr
0xB13E  54 CF     anl   a,#0xCF
0xB140  F0        movx  @dptr,a
0xB141  90 04 90  mov  dptr,#0x0490
0xB144  E0        movx  a,@dptr
0xB145  20 E1 10  jb    acc.1,0xB158   ; 0xB148+3+0x10 = 0xB158
0xB148  E4        clr   a               ; else: zero the stress counters
0xB149  90 09 C7  mov  dptr,#0x09C7
0xB14C  F0        movx  @dptr,a
0xB14D  90 09 C8  mov  dptr,#0x09C8
0xB150  F0        movx  @dptr,a
0xB151  90 09 C9  mov  dptr,#0x09C9
```

`jb acc.1,0xB158` tests bit 1 of `0x0490`, so **the call condition the issue
asked about is answerable from the image**: `0xB158` runs on the passes where
`0x0490` bit 1 is set, and the other arm clears the seconds, minutes and stress
counters. `0x0490` reads `0x0F` live (charge-target-derating.md §3), so bit 1
is set and the branch is taken in practice — but that is a *reading of the
byte*, cited from that file, not a claim that this was watched happening. The
issue's "only on AC?" half is this bit, and the image does not say what sets
it.

## 2. The correction: `0x8539` is not the slot that calls `0xB12C`

Both [§3 of `charge-target-derating.md`](../../ec/annotations/charge-target-derating.md)
and [§4m of `docs/findings.md`](../findings.md) said the task-dispatch slot at
`0x8539` does `lcall 0xB12C`. It does not:

| address | bytes | instruction |
|---|---|---|
| `0x8539` | `12 E0 10` | `lcall 0xE010` |
| `0x853C` | `12 91 67` | `lcall 0x9167` |
| `0x853F` | `12 B1 2C` | `lcall 0xB12C` |

An `lcall` to `0xB12C` occurs exactly once in the whole image, at file
`0x853F`; `task_call_table.py --self-test` pins both the zero and the one.
The reading is off by one slot in a stride-3 table, which is the shape of
mistake a hand walk makes and the shape the tool's own table catches.

What the wrong address got right, and is not being taken back: `0xB12C` *is*
reached on every pass the run is dispatched, and the `0xE010` at `0x8539` is
the *other* `0x0522` writer both files already named, on the slot immediately
before it. So the two facts were one slot apart and both were in the run.

## 3. The three tables, and their extent

`ec/annotations/task-call-table.csv` is the tool's committed output, one row
per entry, 698 rows:

| table | region | extent | rows | `run` column |
|---|---|---|---|---|
| `far-call-stub` | common | `0x1150`–`0x1AC1`, stride 6 | 403 | `0x1150` |
| `bank0-transfer-run` | bank 0 | 35 runs of 4+, stride 3 | 208 | each run's base |
| `switch-case` | common | 4 tables, stride 3 | 87 | each `lcall 0x7151`'s address |

**The run holding the chain's slot is `0x8518`, 22 entries — not `0x84EB`.**
A linear decode anchored at `0x84EB` walks through it, which is where the
off-by-one in §2 came from, but it is not a single stride-3 run:

```
0x84EB .. 0x84FD   7 transfers, then `ret` `ret` at 0x8500/0x8501
0x8502 .. 0x850E   5 transfers, then `mov a,r7` / `jz` / lcall / `ret`
0x8518 .. 0x8557  22 transfers -- 0x8539 and 0x853F are in this one
0x855A             mov dptr,#0x085F -- a different routine
```

40 instructions over `0x84EB`–`0x855A`, 35 of them 3-byte transfers, five not
(three `ret`s, one `mov a,r7`, one `jz`). The two earlier stretches are runs in
their own right and are rows in the CSV under their own `run` values; the tool
asserts all three separately, because "one of 22 slots" and "one of 35 runs"
are different claims and only the first is the useful one.

## 4. How often it runs — what the image gives, and what it does not

#89 opened with the tick rate treated as out of reach from the image, and the
caller chain as the deliverable. **A tick source turned out to be reachable
after all, and the dispatch down to `0xB158` is now traced.** The rate is
still not, and the two are separate claims.

**Established, by cited bytes and existing annotation rows:**

- `common 0x0530` is a timer-0 overflow handler — already named
  `timer0_target_decrements_xdata_0a00` in `ghidra-functions.csv`, reached
  from the `common 0x000B` vector (`bank-call-targets.csv`). Its committed
  comment already records that it "sets bit 5 of internal RAM byte 0x06 — the
  bit address 0x35, which is the byte the .c prints as `_6_5`".
- `common 0x0C86` is already named `poll_flag_bytes_30_to_3b_and_dispatch`,
  and its committed comment already records that flag `0x35` calls **`0x0D7B`**.
- `0x0D7B` is the divide-down scheduler decoded in §1, and its case table
  names the chain's slot at case `0x0A`.

**Not established. There are two gaps, not one, and a rate needs both:**

- **The tick's period.** The handler calls `common 0x0E5E`, already named
  `timer0_reload_8a_06_8c_f1_clear_8d`, which writes `0x06` to `0x8A` and
  `0xF1` to `0x8C`. Its own committed comment gives the reason no interval
  follows: *"The reload interval is not claimed … TMOD at 0x89 is not read
  here, so the timer mode is not established."* Without the mode the two
  reload bytes are not a period.
- **The divide factor.** The chain runs when `0x45` is `0x0A`, so its rate is
  the tick period times however many ticks it takes `0x45` to come round to
  `0x0A` again — **and that was not followed. `0x0D7B` has a tail-dispatch path
  (`ljmp 0x0E2E` at `0x0D88`) that leaves its own frame, so whether `0x45`
  advances on every entry to `0x0D7B` is not settled by these bytes alone.**
  **A gap that would sink a rate claim even if the first one closed**, which is
  why none is written down here in any form.
  > **CORRECTION (2026-09-27, issue #1183).** The clause above is withdrawn and
  > the gap is closed; the superseding wording stays visible per `CLAUDE.md`.
  > `0x45` does **not** advance on every entry, and that is what makes the count
  > computable: `0x44` counts 1…10, so `inc 0x45` fires on **one entry in ten**,
  > and `0x0A` → `0x0A` is 20 such firings, giving **200 entries to `0x0D7B`**
  > per case-`0x0A` turn (`lcall 0x0E5B` every 12,000). The reason the earlier
  > reading could not see it is that the issue's polarity was inverted —
  > `jnb acc.0` jumps when bit 0 is **clear**, so an *even* `0x44` reaches the
  > ladder at `0x0D8B` and an odd one abandons the frame; the tail-dispatch
  > path is real but takes the *other* half the values, and it is `0x44`
  > reaching 10 that clears the counter. **This is a count of entries, not a
  > period, and it is not a rate**: the tick's own period is the open gap
  > above, the counts-to-seconds step needs an oscillator frequency that
  > appears nowhere in the tree, and the poller's period against the flag is
  > unestablished too, so not even "200 ticks" is licensed. Decoded in
  > [`scheduler-divide-down-cycle.md`](scheduler-divide-down-cycle.md), whose
  > byte pins are `ec/tools/test_scheduler_cycle.py`.
- **`0x09C7`/`0x09C8` are not the tick source, and must not be read as one.**
  The issue raised the seconds/minutes counter as implying a once-per-second
  caller, and flagged the inference itself. It is worse than an inference: the
  counter is *inside* the task, and `0xB12C`'s else arm at `0xB148` zeroes
  `0x09C7`–`0x09CA` directly. A counter a task maintains and a counter that
  drives a task are not the same thing, and nothing here is evidence of the
  second.
- **How often `0x0C86` runs relative to the flag** — the dispatcher's own
  period — is not read either.

**What a real answer would need**, and this is a separate issue rather than
this one: a live capture of the counter against wall clock, run by a human at
the machine. `ec/tools/ec_timer_capture.py` is the right instrument and cannot
be run from a cloud runner; preparing that run is its own deliverable, and
nothing in this file has been run on hardware.

## 5. What the open ends are now

One, and it is small. The second was closed by issue #1183.

**What the `0x0E2E` slot does, and whether it returns.** `0x0E2E` is
`lcall 0x383A` and the `ret` comes back at `0x0E31`, which is a tail jump, so
`0x0D7B`'s frame is abandoned on the `ljmp 0x0E2E` path. Whether the far-called
routines return to it or the block's own chain unwinds differently is not
traced. **The count in §4's correction does not depend on this**: the
`ljmp 0x0E2E` arm is taken on an *odd* `0x44`, and it is `0x44` reaching 10 —
on the even arm — that clears the counter and advances `0x45`. The two arms are
disjoint, so this stays open without making the 200 contingent.

**What the `0x45` counter's other values select.** The nine cases are decoded
in §1 and the chain's is the `0x0A` one. The `0x0E0D` default arm — where the
dispatcher falls off the end of a table and jumps to whatever follows the
terminator — clears `0x45` and increments `0x47`, so the counter does wrap;
**by what route back to `0x0A` was not traced.**
> **CORRECTION (2026-09-27, issue #1183).** The route back to `0x0A` is the
> default arm itself, and it is the only route: `0x45` counts up, the first even
> value past the table's last key `0x12` is `0x14`, and `0x14` is what
> `0x7151` sends to `0x0E0D` through the table's `00 00 0e` sentinel. So
> `0x45` runs `0x01`…`0x14` and returns to zero, and `0x0A` → `0x0A` is 20
> firings — which is the second term of the 200 in §4's correction. Decoded in
> [`scheduler-divide-down-cycle.md`](scheduler-divide-down-cycle.md). This
> supersedes the "was not traced" above rather than deleting it.

The one that remains is not the mechanism issue #89 asked about, and it is
named here so the next reader does not have to rediscover that it was looked
at.

## 6. Methods tried, including what found nothing

"Not found" below means not found *by this method over this region*. None of
these is an absence claim. `task_call_table.py --search` re-runs every line of
the table but one: it does not do the `0xB158`-as-a-16-bit-constant scan, in
either byte order. §7 carries that row as an explicit command instead, since
no mode of the tool performs it.

| method | region | result |
|---|---|---|
| `lcall`/`ljmp` naming `0xB158`, unaligned byte scan | whole 0x40000-byte image | **0 hits** — unchanged from the issue |
| `0xB158` as a 16-bit constant, both byte orders | whole image | **0 hits** either order |
| `lcall`/`ljmp` naming `0xB12C` | whole image | **1 hit**, file `0x853F` |
| `lcall`/`ljmp` naming `0x157C` | whole image | **1 hit**, file `0x0E55`, a real instruction |
| `jmp @a+dptr` (`0x73`) | common `0x0D00`–`0x0FFF` | **0 hits** |
| `movc`-style code-pointer table | — | **this one was it**: `common 0x7151` `switch_case_dispatch`, and its inline table at `0x0DD6` is what selects `0x0E55` (§1) |
| BL51 trampoline audit | — | re-derived, not regenerated: 403 stubs, 350/53, matching `bank-call-audit.md` §3 |

The `0x157C` row names the file `0x0E55`, which is the `ljmp 0x157C` at the
end of the dispatch block in §1. The `0x0DFE` that also appears there is a
different thing: it is the *address* the case table's `0x0A` triple carries,
and its own bytes are `02 0e 55`, a `ljmp 0x0E55`.

The `jmp @a+dptr` scan is bounded the way the issue framed it, and the bound
is reported rather than dropped. The wider common area — `0x0000`–`0x7FFF`,
per `trace_xdata_refs.REGIONS` — contains 17 `0x73` bytes
(`0x769 0x0C3E 0x1054 0x126C 0x41F6 0x4262 0x6659 0x66D9 0x6759 0x67D9
0x6859 0x68D9 0x6B5A 0x6D7B 0x702F 0x716B 0x717C`), of which **none** falls in
the scanned `0x0D00`–`0x0FFF`; the committed decompiles show most of the rest
inside data rather than code. The dispatcher that *does* read a jump table is
at `0x7151`, well outside the scanned region, and is reached through an
`lcall` rather than a `jmp @a+dptr` at this site — its `jmp @a+dptr` is the
last instruction of the routine, `0x7151`+`0x1A` = `0x716B`.

## 7. Reproducing it

```
python3 ec/tools/disasm8051.py --self-test          # the framing oracle; run first
python3 ec/tools/task_call_table.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/task_call_table.py ec/firmware/GMxMGxx_11.800 --check
python3 ec/tools/task_call_table.py ec/firmware/GMxMGxx_11.800 --chain
python3 ec/tools/task_call_table.py ec/firmware/GMxMGxx_11.800 --search

# the one row --search does not cover: 0xB158 as a 16-bit constant, both
# byte orders, unaligned, over the whole image. Prints "0 hits" twice.
python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read(); [print(p.hex(), sum(d[o:o+2]==p for o in range(len(d)-1)), 'hits') for p in (b'\xb1\x58', b'\x58\xb1')]"
```

`--check` is **not** wired into `.github/scripts/agent-gates.sh`, and no patch
for it is prepared under `docs/ci/`. The reason is specific rather than a
shrug at the shared file.

The cheap gate's `check_ghidra_tooling` loop reaches a tool with this shape —
no `--work`, no scratch dir, `--check` then `--self-test` — through a per-tool
`case` arm, and `.github/scripts/agent-gates.sh` is copied from the
`agent-pipeline` template, so a branch editing it fails at the end of a PR
rather than the start. The repository's arrangement for that is
`docs/ci/agent-gates-<name>.patch`, a `git apply` a human runs, and
`tools/test_agent_gates_patches.py` holds the set: it requires every patch to
apply alone **and** every ordered pair of them to compose.

They compose by leaving each patch's hunks outside the others' three lines of
context. On the committed script the `for tool in` list is `:119`–`:130`, and
all of it is already held:

| hunk | context window |
|---|---|
| `agent-gates-gap-text-check.patch` hunk 1 | `:119`–`:124` |
| `agent-gates-0751-self-test.patch` hunk 1 | `:123`–`:128` |
| `agent-gates-disasm8051-self-test.patch` hunk 1 | `:127`–`:133` |

The set is green as it stands. `python3 tools/test_agent_gates_patches.py`
reports 15 tests and no failures, and all seven patches pass
`git apply --check` against the committed script. Green there already means
composing, because the suite requires each patch to apply alone *and* every
ordered pair of them to compose.

What stops a seventh patch is one specific collision, not a broken set.
`agent-gates-disasm8051-self-test.patch` hunk 1 is `@@ -127,7 +127,9 @@` and
rewrites the list's last line: `windows/tools/decompile_native.py; do` becomes
a continuation plus `ec/tools/disasm8051.py; do`. That is the only line a new
entry can be appended to — `:130` is where the `; do` terminator lives — so a
patch adding `ec/tools/task_call_table.py` to the list takes the same three
lines of context, and the two genuinely cannot both land.

So no patch for it is prepared here. One written against the committed file
would not compose, and adding it to `PATCHES` would turn the suite red for a
known reason rather than a real one. Landing the gate entry needs a human to
land the disasm8051 patch first; after that `:130` frees up and the patch can
be cut against the patched file.

**Until then, a CSV that stops describing the image merges green.** That
consequence does not rest on the set being broken — it rests on `--check`
being in no gate in either tier, and on no patch for it existing under
`docs/ci/`. The commands above are cheap — both modes read only the committed
image and the committed CSV, no Ghidra, no network — and are the substitute in
the meantime.

## 8. What this file is not

- **No hardware ran.** No register was read, written, or read back, and no
  live timing was taken. The `0x0490` = `0x0F` reading and the `<101 µs`
  reclaim are cited from `charge-target-derating.md` §3 and `docs/findings.md`
  §4m, not re-measured.
- **No rate.** §4 gives the structure and the two things that would have to be
  known to turn it into one. A sentence here reading "the EC recomputes
  `0x0522` every N ms" would be the failure mode CLAUDE.md's calibration rule
  exists to stop.
- **No `status:` moves.** This is a call-graph result. Nothing in
  `ec/annotations/registers.yaml` changes, and a readback or a decode is not
  the behavioural evidence a status change would need.
- **`bank-call-targets.csv` and `bank-call-audit.md` are not regenerated.**
  The new table overlaps them for the stub table and cites them; another branch
  may be rebuilding them.
