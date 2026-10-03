# What calls `0xA7C8`, and whether the host-writes-PLs / EC-zeroes-PLs race is real

**The chain is a polled dispatch slot, not a boot chain, and the race is
possible.** `0x851B` is reached from the divide-down scheduler's case table on
two of its nine cases, through a named slot of the seventeen-slot dispatch
block and a far-call stub that has a row in the committed
`task-call-table.csv`. Every hop below is decoded from
`ec/firmware/GMxMGxx_11.800`; the byte facts are held by
`ec/tools/test_a7c8_dispatch_slot.py`, which reads the committed image rather
than re-running any scan that produced a table quoted here.

The race needs three things and the evidence splits cleanly across them:

| | verdict | what carries it |
|---|---|---|
| Is `0xA7C8` called after boot? | **yes** — a recurring turn of a polled scheduler, on cases `0x02` and `0x0C` | §1 |
| Does it then zero `0x0783`-`0x0785` when `0x0741` bit 0 is clear? | **yes**, on every pass that gets past the routine's two entry gates — which have never been evaluated | §2 |
| Is bit 0 ever clear while a host has set the PLs? | **yes, two independent ways** — the vendor parks it clear on purpose, and the EC revokes it and never restores it | §3 |
| Do those overlap *in time*, on this machine, on a given run? | **not established** — same two entry gates, plus the scheduler's phase | §4 |

Nothing here was run on hardware. The procedure that would settle the last row
is `../hardware-tests/pl-clear-0741-gate.md`, and it has not been run.

## 1. The chain, hop by hop

The starting point is the one the issue names. `manual-fan-ctrl-0751.md` §4
decoded the run and recorded that `0x851B`'s framing was unresolved. What that
run **is** was already in the tree — `scheduler-run-8518-entries.md` (§1, issue
#1185) decoded it as seven independent segments and matched the seven stub
immediates against the seven segment heads. `0x851B` is the head of segment 1,
and stub `0x1564` is the one that names it. What no file joined is the other
end: **which scheduler case reaches that stub.** Both halves were committed;
the join was not.

```
common 0x0CF0  poll_flag_bytes_30_to_3b_and_dispatch   30 35 1c / c2 35 / 12 0d 7b
  -> common 0x0D7B   the divide-down scheduler
       inc 0x45 ; jnb acc.0,0x0DD1 ; lcall 0x7151 ; the inline table at 0x0DD6
         case 0x02 -> 0x0DF5  80 0a    sjmp 0x0E01
         case 0x0C -> 0x0E01  02 0e 49 ljmp 0x0E49
           -> common 0x0E49   02 15 64  ljmp 0x1564        slot 11 of 0x0E2B-0x0E5D
             -> common 0x1564   90 85 1b / 02 11 00        far-call stub, bank 0
               -> bank0 0x851B   12 a7 c8  lcall 0xA7C8
```

The bytes, read off the image. Common-area addresses are file offsets, which is
what `trace_xdata_refs.REGIONS` says for the `0x0000`-`0x7FFF` region:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0DCB -n 4 --runtime 0x0DCB
0x0dcb  30 e0 03  jnb  acc.0,0x0dd1
0x0dce  02 0e 46  ljmp 0x0e46
0x0dd1  e5 45     mov  a,0x45
0x0dd3  12 71 51  lcall 0x7151

$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0DF5 -n 4 --runtime 0x0DF5
0x0df5  80 0a     sjmp 0x0e01
0x0df7  80 0b     sjmp 0x0e04
0x0df9  80 0c     sjmp 0x0e07
0x0dfb  02 0e 52  ljmp 0x0e52

$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0E01 -n 1 --runtime 0x0E01
0x0e01  02 0e 49  ljmp 0x0e49

$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0E49 -n 1 --runtime 0x0E49
0x0e49  02 15 64  ljmp 0x1564

$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x1564; pd 2' /tmp/bank0.bin
        ╎   0x00001564      90851b         mov dptr, #0x851b
        └─< 0x00001567      021100         ljmp 0x1100
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8518; pd 4' /tmp/bank0.bin
        ┌─< 0x00008518      02b065         ljmp 0xb065
        │   0x0000851b      12a7c8         lcall 0xa7c8
        │   0x0000851e      12a844         lcall 0xa844
        ┌──< 0x00008521      02cfc6         ljmp 0xcfc6
```

`0xA7C8` is reached from `0x851B` and from nowhere else. An unaligned scan of
the whole 0x40000-byte image for `12 a7 c8` and `02 a7 c8` returns exactly one
hit, that `lcall` — in the main EC, in the PD image, and in the erased regions
alike. That is *not found by this method*, not absent: a transfer built at run
time or routed through a function-pointer table would not be seen by a
two-opcode byte scan, and this repository has already found one such mechanism
in this image (`common 0x7151`, the `switch_case_dispatch` two hops above).

### The case table, decoded rather than quoted

The nine triples at `0x0DD6`, and the `00 00 0e` sentinel that follows them:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0DD6 -n 1 --runtime 0x0DD6
0x0dd6  0df5020df7040df9060dfb080dfe0a0e010c0e040e0df9100e0a1200000e0d  case table: 31 bytes
```

The sentinel's third byte is doing double duty, which is worth seeing once
rather than taking as a coincidence: `0x0DF1` holds `00 00`, the address the
dispatcher reads as "past the end", and the following two bytes `0x0DF3`/
`0x0DF4` are `0e 0d` — which is `0x0E0D`, the default arm. `0x715F`/`0x7160`
`inc dptr` twice from `0x0DF1` to `0x0DF3` and read those two into DPTR, so the
table carries its own escape in its terminator.

| table addr | case | where it goes |
|---|---|---|
| `0x0DF5` | `0x02` | `sjmp +0x0A` → `0x0E01` → `ljmp 0x0E49` |
| `0x0DF7` | `0x04` | `sjmp +0x0B` → `0x0E04` → `ljmp 0x0E4C` |
| `0x0DF9` | `0x06` | `sjmp +0x0C` → `0x0E07` → `ljmp 0x0E4F` |
| `0x0DFB` | `0x08` | `ljmp 0x0E52` |
| `0x0DFE` | `0x0A` | `ljmp 0x0E55` — the chain `charge-target-caller-chain.md` §1 traced |
| **`0x0E01`** | **`0x0C`** | **`ljmp 0x0E49`** |
| `0x0E04` | `0x0E` | `ljmp 0x0E4C` |
| `0x0DF9` | `0x10` | `sjmp +0x0C` → `0x0E07` → `ljmp 0x0E4F` |
| `0x0E0A` | `0x12` | `ljmp 0x0E58` |
| `0x0000` | — | terminator |

This table is not new — `charge-target-caller-chain.md` §1 prints the same nine
rows and derives the same two-hop shape for `0x02` and `0x0C`. What is new is
the second column's consequence: `0x0E01` is `ljmp 0x0E49`, and `0x0E49` is
`ljmp 0x1564`, so **cases `0x02` and `0x0C` are the two that reach `0xA7C8`.**

### `0x0E49` is one slot of seventeen, and which slot is the point

The block at `0x0E2B`-`0x0E5D` is seventeen entries at a stride of 3 — sixteen
`ljmp` and one `lcall` — each naming a far-call stub:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0E2B -n 18 --runtime 0x0E2B \
    | tail -n 8
0x0e49  021564  ljmp 0x1564      <- slot 11, the one that reaches 0xA7C8
0x0e4c  02156a  ljmp 0x156a
0x0e4f  021570  ljmp 0x1570
0x0e52  021576  ljmp 0x1576
0x0e55  02157c  ljmp 0x157c
0x0e58  021582  ljmp 0x1582
0x0e5b  021588  ljmp 0x1588
0x0e5e  758a06  mov  0x8a,#0x06  <- the 18th: 17 entries, then the reset's own code
```

The whole listing is `charge-target-caller-chain.md` §1's, and the reason
`0x0E2E` is the odd one out is its §1's too; neither is repeated. The one fact
this file needs is that `0x0E49` is slot 11 of 17 and names stub `0x1564`, so
it is **not** interchangeable with the sixteen siblings — a scheduler that
reaches one slot has not reached the block.

### The polarity, which is the thing a reader will get backwards

`0x0DCB` is `30 e0 03`, `jnb acc.0,0x0DD1`. **`jnb` jumps when bit 0 is
clear**, so an *odd* `0x45` abandons the frame at `0x0DCE ljmp 0x0E46` (stub
`0x155E` → bank0 `0x8518`, segment 0) and an *even* one reaches the switch.
Every key the table holds is even, so the gate and the table agree. This is
the same bit issue #1183 had inverted for `0x44` and `scheduler-divide-down-cycle.md`
corrected; the suite pins it here for `0x45` so a decoder regression cannot pass
on a stale table.

### So: a turn of the scheduler, not a boot event

`0x45` counts up through `0x01`-`0x13` (the odd values taking the `0x0E46` arm)
and the first even value past the end of the table, `0x14`, reaches the default
arm at `0x0E0D`, which clears `0x45` and increments `0x47`:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0E0D -n 6 --runtime 0x0E0D
0x0e0d  e4        clr  a
0x0e0e  f5 45     mov  0x45,a
0x0e10  05 47     inc  0x47
0x0e12  e5 47     mov  a,0x47
0x0e14  b4 3c 06  cjne a,#0x3c,0x0e1d
```

So `0x02` and `0x0C` are each a **turn** of that counter, and the cycle repeats:
**`0xA7C8` is entered twice per `0x45` cycle.** It is a periodic
initialisation pass with a one-shot inside it, not a boot event — see §2 for
why the one-shot does not make it boot-shaped.

That is a count of entries to `common 0x0D7B` and **not a period**. The chain
runs from the flag the timer interrupt handler at `common 0x0530` raises to the
store, and the step between them — how often the poller `0x0C86` is itself
entered, and against what — is exactly what
`scheduler-divide-down-cycle.md` §5 leaves open, along with the tick's own
period (`TMOD` at `0x89` is never read). So not even "twice every *N* ticks" is
licensed, and this file does not convert it into one. All four refusals travel
with `scheduler-divide-down-cycle.md` §5 and are not restated as this file's
own finding.

The **phase** is a separate open end and this file does not close it: the
counter's period is start-independent, but which entry the first case `0x02`
lands on depends on the reset values of `0x44`/`0x45`, and the image does not
establish those. So "twice per cycle" says how often relative to the counter and
nothing about when the first one is.

## 2. What the routine does once it is there — and why it is not boot-shaped

The whole of `0xA7C8` is committed, as `ec/decompiled/bank0/A7C8.asm`. Two of
its gates stand between the entry and the PL clear, and both are named routines
in `ec/annotations/ghidra-functions.csv`:

```
A7C8  12 be 9c  lcall  0xbe9c     read_x0780_xor_a2:  A = [0x0780] ^ 0xA2
A7CB  60 76     jz     0xa843     A == 0  ->  ret, the tail never runs
...
A7EA  12 b9 d8  lcall  0xb9d8     read_06e6_xor_01:   A = [0x06E6] ^ 0x01
A7ED  60 04     jz     0xa7f3     A != 0  ->  xrl a,#0x05 ; ret at 0xa7f2
...
A7FE  90 07 82  mov    dptr,#0x782
A801  e0        movx   a,@dptr
A802  30 e0 26  jnb    acc.0,0xa82b
A805  e0        movx   a,@dptr
A806  30 e5 22  jnb    acc.5,0xa82b
A809  e0        movx   a,@dptr
A80A  54 df     anl    a,#0xdf     ; the one-shot: consume 0x0782 bit 5
A80C  f0        movx   @dptr,a
...
A828  12 86 53  lcall  0x8653
A82B  90 07 41  mov    dptr,#0x741
A82E  e0        movx   a,@dptr
A82F  20 e0 11  jb     acc.0,0xa843   ; bit 0 SET -> ret, PLs untouched
A832  e4        clr    a
A833  90 07 83  mov    dptr,#0x783   ; PL1 = 0
A836  f0        movx   @dptr,a
A837  90 07 84  mov    dptr,#0x784   ; PL2 = 0
A83A  f0        movx   @dptr,a
A83B  90 07 85  mov    dptr,#0x785   ; PL4 = 0
A83E  f0        movx   @dptr,a
A83F  90 07 8b  mov    dptr,#0x078b
A842  f0        movx   @dptr,a
A843  22        ret
```

**The entry conditions, stated as the two XORs rather than left as "a gate":**
the PL gate at `0xA82B` is reached when `[0x0780] != 0xA2` **and**
`[0x06E6] == 0x01`. Both bytes are read-only to this routine; both are named in
the committed annotation CSV. `[0x06E6]` is a state the EC itself writes —
`trace_xdata_refs.py` finds `mov a,#0x01 ; movx @dptr,a` at bank0 `0xCC8E` and
`0xCCD2`, alongside `0x03` at `0xCCE5` and `0x05` at `0xCCFC` — so `0x01` is a
value the machine reaches rather than one the image never produces. **What
selects among those four is not established here**, and neither is `0x0780`,
which has no entry in `registers.yaml`. That is §4's open end and the follow-up
this opens.

**The one-shot does not make the routine boot-shaped, and this is the issue's
question answered against the boot reading.** `0xA80A`'s `anl a,#0xdf` consumes
`0x0782` bit 5, and it guards *only* the `0x0751` mode write between `0xA809`
and `0xA823`. The PL clear is at `0xA82B`, and it is the branch target of
**both** `jnb`s — `0xA802` on bit 0 and `0xA806` on bit 5 — as well as the
fall-through from `0xA828`'s `lcall`. All three paths converge on it. So on
every pass that gets past the two entry gates, `0xA82B` runs and the PLs are
zeroed if bit 0 is clear; the one-shot decides whether the *mode byte* is
rewritten, and has nothing to say about the PLs. A routine that recurs and has
a one-shot inside it is a periodic init pass, and that is what this is.

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa802; pd 3' /tmp/bank0.bin
        ┌─< 0x0000a802      30e026         jnb acc.0, 0xa82b
        │   0x0000a805      e0             movx a, @dptr
        ┌──< 0x0000a806      30e522         jnb acc.5, 0xa82b
```

### Why entering the run at its base does not reach this

`0x8518` is `02 b0 65`, a tail `ljmp`, so segment 0 is one slot and it leaves
the block — entering the run at its base never reaches `0x851B`. Entering *at*
`0x851B` runs `0xA7C8`, then falls into `0x851E`'s `lcall 0xA844`, then leaves
through `0x8521`'s `ljmp 0xCFC6`. The two stubs therefore reach different
code, which is why "what is the framing of this run" was worth asking. This is
`scheduler-run-8518-entries.md` §1's and §2's material and is cited rather
than re-derived; the suite pins the four bytes it rests on.

## 3. Is bit 0 ever clear while a host has set the PLs? Two ways, and one of them is the vendor's own

### 3a. The vendor parks it clear on purpose

`windows/vendor-ec-map.md` "Fan tables" records the handshake from the service
side: clear `0x0741` bit 0, write the mode code to `0x0F5F`, write `0xFD`/
`0xC9` to `0x0F5D`/`0x0F5E`, poll, set bit 0 again. The source is
`windows/decompiled/v3.1.39.0/GCUService/MyControlCenter.MyFan.FanTable/FanTable_Manager1p5.cs`:

```csharp
private bool RefreshDefaultFanTableAll()
{
    bool result = false;
    EcCtrl.Set_APExistToEC(bExist: false);          // <-- bit 0 clear, once
    bool num  = RefreshDefaultFanTable(ref DefaultFanTable_Gaming, 2);
    ...
    bool flag2 = RefreshDefaultFanTable(ref DefaultFanTable_Turbo, 1);
    ...
    EcCtrl.Set_APExistToEC(bExist: true);           // <-- bit 0 set, once
    return result;
}

private bool RefreshDefaultFanTable(ref FanTable1p5 fantable, byte mode)
{
    ...
    int num = 0;
    do
    {
        Thread.Sleep(500);
        if (IsReadyToRead()) { ...; return true; }
        num++;
    }
    while (num != 3);
    ...
}
```

**The window is derived from that loop, not measured.** Three calls, each a
`do { Thread.Sleep(500); ... } while (num != 3)` that runs three iterations
unless it returns early: between 1.5 s and 4.5 s of `Thread.Sleep` in total,
and there is unaccounted time between the calls for
`GetCpuTemMaxLevel`/`GetGpuTemMaxLevel`/`WriteFanTableToJson`. So the bit is
clear for **at least 1.5 s** on each `RefreshDefaultFanTableAll`, and no
longer figure is claimed. It runs from `FanTable_Refresh`, which
`FanTable_Init` calls in four branches — the EC version differs, the local
JSONs are invalid, they are all zero, or they are not found — so this is a
startup path, not something the user asked for. **It is not a host error; it
is the vendor's own service creating the exact condition `0xA82B` waits
for**, which is what makes the race worth naming rather than filing as a
hypothetical.

### 3b. The EC revokes bit 0 itself and never restores it

This is the half that was not in prose anywhere, and it is the driver-relevant
half. `0x0741` bit 0 is host-owned: `0xA82F` skips the PL clear when it is
set, and `0xB13A` keeps the manual-ctrl profile only while it is set. It is
`confirmed-working` in `registers.yaml`, and the note there says the driver sets
it once in `uniwill_ec_init()`.

**The EC clears it at `0xBD03` and — by the method below — never sets it.**

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xbd03; pd 4' /tmp/bank0.bin
            0x0000bd03      900741         mov dptr, #0x0741
            0x0000bd06      e0             movx a, @dptr
            0x0000bd07      54fe           anl a, #0xfe
            0x0000bd09      f0             movx @dptr, a
```

`0xBD03` has the committed name `clear_0741_bit0_and_08e2_bit4`, and exactly
two `lcall 0xBD03` sites exist in the image — `0xAB75` and `0xACFC`. The first
is `set_06e2_bit0_from_c412`, which reaches it only when `XDATA 0x06E6 == 0x05`;
the second is inside `0xACB4`, `reset_xdata_flags_and_07d5_to_ff`, the
whole-machine reset, which `0xCFC3` tail-jumps to.

The negative that matters is a **scan that can fail**, not an assertion:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0741 --csv \
      | grep 'write'
```

Every writer this method finds on `0x0741`, and what each does to bit 0:

| site | operation | bit 0 |
|---|---|---|
| `0x8782`, `0x879D` | `orl a,#0x20` | untouched |
| `0x87AC` | `anl a,#0xdf` | untouched |
| `0xA990`, `0xAD17` | `anl a,#0xfb` | untouched |
| `0xA9E1` | `orl a,#0x04` | untouched |
| `0xAD46`, `0xCF78` | `anl a,#0x7f` | untouched |
| `0xBD03` | `anl a,#0xfe` | **cleared** |
| `0xCFEE` | `orl a,#0x80` | untouched |

**No `orl a,#0x01` on `0x0741` is found.** That is *not found by this method*:
the scan is a direct `MOV DPTR,#0x0741` census with an eight-instruction window
around each site, so a blind whole-byte store, and any store through a DPTR
built at run time, are invisible to it — `manual-fan-ctrl-0751.md` §6 is the
worked counter-example on a second address. Bit 0 is not established absent.

What the negative does license is narrower and is the point: **the EC can take
the bit away and this method finds nothing that gives it back**, so a driver
that sets it once at init does not get a sticky bit. The `0xACB4` caller is a
whole-machine reset, so losing the bit there is expected. What reaches
`set_06e2_bit0_from_c412` at `0xAB6E` is **not established here** — that is
§6's second follow-up, and it is written down as the question rather than as
the connection it might be. Either way the driver's exposure is not bounded by
having set the bit once, which is the part `manual-fan-ctrl-0751.md` §4
assumed and this corrects.

## 4. The verdict, and what it is not

**The race is possible, and it is more reachable than the issue framed it.**
The path is closed from the timer handler's flag to the store, the routine
recurs, and the bit is host-owned and revocable. What is *not* established is
how often that path runs, or that the two overlap in time on this machine —
and the honest ceiling is that **the two entry gates have never been
evaluated.** `[0x0780] != 0xA2` and
`[0x06E6] == 0x01` are both runtime facts about two bytes, one of which has no
`registers.yaml` entry, and a static decode cannot say whether either holds at
the same time — let alone whether it holds while the vendor service is inside
its fan-table handshake.

So the strongest correct statement is three separate ones, and they should not
be collapsed:

1. `0xA7C8` **is** a recurring polled task, reached on scheduler cases `0x02`
   and `0x0C`. Not boot-shaped. (Static, closed.)
2. Whenever it is entered with `0x0741` bit 0 clear and both entry gates
   satisfied, the four stores at `0xA833`-`0xA842` **execute**. "The stores
   execute" is the claim; that the EC then *acts* on the zeros is a separate
   question this file does not answer. (Static, closed.)
3. Bit 0 **is** clear for at least 1.5 s during the vendor's own
   `RefreshDefaultFanTableAll`, and **can be** left clear indefinitely by the EC
   itself. Whether that intersects (1) is a run-time question. (Not decided.)

**This does not establish:**

- **Any rate, period or interval.** §1's "twice per `0x45` cycle" is a count of
  entries to `common 0x0D7B`. The four refusals are `scheduler-divide-down-cycle.md`
  §5's and travel with the number; the phase is open on top of them.
- **That the clear ever fires on this machine.** The two entry gates are
  unevaluated, and `0x06E6` and `0x0780` are runtime bytes. Nothing here says the
  conditions have ever held together.
- **That bit 0 is never set.** That is the §3b scan's shape, named above.
- **That `0xA7C8` is the only PL writer, or that the clear is the only thing in
  the run that touches the PLs.** §2's gates are a decode, not an observation,
  and no register was read back.
- **That the framing debt is closed for the run.** It is closed for `0xA7C8`.
  `0x83FF` at `0x8551` — `ec-07c4-07d5-sites.md` §2/§9,
  `docs/hardware-tests/ctgp-dben-07c4-bit3.md` §6 and
  `ec/annotations/static-refs-audit.md` — is a **different** slot in the same run
  (segment 6, indices 17-21), and those files' open items are unchanged here.
- **Anything about `0x0782` bit 5.** Its `registers.yaml` note documents bits
  1/2/4/6 and says nothing about bit 5 or its one-shot at `0xA80A`. §2 reads the
  bytes; closing the row's gap is a separate edit to a shared entry.

## 5. A correction to the premise, carried in place

The issue, and four files with it, attribute this run's framing to
`ec/annotations/bank-call-audit.md`: `manual-fan-ctrl-0751.md` §4 and §8,
`ec-07c4-07d5-sites.md` §2/§9, `ctgp-dben-07c4-bit3.md`, and
`static-refs-audit.md`. **That file never claimed it.** It is about
`lcall`/`ljmp` framing and the BL51 trampolines, and it does not mention
`0x8518`, `0x851B`, or the boot-chain/dispatch-table/polled-task question at
all. The attribution arrived with the 0751 note's §4 and was copied onward
without anyone opening the target. The debt was real; the pointer was not.

Two more files recorded the question as open without naming a target —
`windows/vendor-ec-map.md` and the safety section of `fan-table-defaults-0f5d.md`
— and are corrected the same way. All five corrections leave the original
wording visible beside them, per `CLAUDE.md`. `ec-07c4-07d5-sites.md`,
`ctgp-dben-07c4-bit3.md` and `static-refs-audit.md` are **not** edited, because
what they ask about is `0x83FF`, which §4 above is explicit this does not close.

The framing itself was in fact resolved by `scheduler-run-8518-entries.md`
(issue #1185) before this file, which is why §1 can cite it rather than redo it.
The remaining misdirection was that nothing had connected the *stub* to the
*scheduler*, which is this file's whole contribution.

## 6. Follow-ups this opens

- **What selects `0x06E6` between `0x01`, `0x03` and `0x05`, and what holds
  `0x0780` away from `0xA2`.** These are the two gates on the PL clear, and they
  are one trace from `0xCC8E`/`0xCCD2`/`0xCCE5`/`0xCCFC`. This is the live
  question, and the one that decides whether the race is reachable on this
  machine rather than merely possible in principle.
- **What reaches `set_06e2_bit0_from_c412` at `0xAB6E`, and with what
  `0x06E6`.** That is the non-reset caller of `0xBD03`, and it is the same byte
  the `0xA7C8` gate reads — suggestive, not established, and written here as the
  question rather than the connection.
- **`0x83FF`'s framing, as its own issue.** The same case table names the stub
  for that segment too: case `0x12` → `0x0E0A` → `ljmp 0x0E58` → `ljmp 0x1582`
  → `mov dptr,#0x854B ; ljmp 0x1100`, and `0x854B` is the head of segment 6.
  Stated here because the next planner needs it and because it costs nothing to
  read off the table above — **not** claimed as this change's answer, and the
  three files that call it unresolved are left as they are.
- **A live run.** `../hardware-tests/pl-clear-0741-gate.md`, unrun.

## 7. Reproducing it

Every command reads committed inputs only. No Ghidra, no network, no hardware.

```sh
# the framing oracle first, per the house order
python3 ec/tools/disasm8051.py --self-test

# the parity gate and the case table
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0DCB -n 4 --runtime 0x0DCB
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0DD6 -n 1 --runtime 0x0DD6
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0E0D -n 6 --runtime 0x0E0D

# the dispatch slot and the stub, and the run's own four bytes
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0E49 -n 1 --runtime 0x0E49
python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
r2 -a 8051 -e scr.color=0 -q -c 's 0x1564; pd 2' /tmp/bank0.bin
r2 -a 8051 -e scr.color=0 -q -c 's 0x8518; pd 4' /tmp/bank0.bin
r2 -a 8051 -e scr.color=0 -q -c 's 0xa802; pd 3' /tmp/bank0.bin
r2 -a 8051 -e scr.color=0 -q -c 's 0xbd03; pd 4' /tmp/bank0.bin

# the only two callers of 0xBD03, and the writer census that is a negative
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0741 --csv | grep write
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x06E6 --counts-only

# the tables this file cites, still the tools'
python3 ec/tools/task_call_table.py --self-test ec/firmware/GMxMGxx_11.800
python3 ec/tools/task_call_table.py ec/firmware/GMxMGxx_11.800 --check

# the byte facts, read from the image rather than from any table above
python3 -m unittest discover -s ec/tools -p 'test_a7c8*.py'
```
