# The battery PL default block, and what a zero in the PLs means

Issue #1228 §1 asks one question — *name the battery PL default bytes, or
record that the tree has no record of them* — and leaves four more (§2-§5) to
a run. This is the answer to §1, plus a static reading of the asymmetry §4
opens, from the EC side.

**Nothing here is a measurement.** No register was read, written or read back,
and no hardware was reached; every claim below is a statement about a committed
file, and every negative is a statement about a named method rather than about
the firmware. The procedure that would turn the open question at the end into
an answer is [`../hardware-tests/battery-pl-limit-effect.md`](../hardware-tests/battery-pl-limit-effect.md),
which has not been run.

## 1. There is no separate battery PL block: `0x07A7`-`0x07AA` is it

The tree does name the battery PL defaults, and the name is not "battery" —
it is `ADDR_BATTERYSAVER`. `windows/decompiled/v3.1.6.0/ECSpec.cs` defines
exactly three `*_PL*_DEFAULT_VALUE` four-byte groups:

| ECSpec constant | address | block |
|---|---|---|
| `ADDR_GAMING_PL1/PL2/PL4/D_DEFAULT_VALUE` | 1840-1843 | `0x0730`-`0x0733` |
| `ADDR_OFFICE_PL1/PL2/PL4/D_DEFAULT_VALUE` | 1844-1847 | `0x0734`-`0x0737` |
| `ADDR_BATTERYSAVER_PL1/PL2/PL4/D_DEFAULT_VALUE` | 1959-1962 | `0x07A7`-`0x07AA` |

1959 is `0x07A7`, so the third group is exactly the `0x07A7`-`0x07AA` block
that `ec/annotations/registers.yaml` already carries as the last four bytes of
`MODE_PL_DEFAULTS`.

**There is no `ADDR_TURBO_PL*_DEFAULT_VALUE`.** Searching `windows/` for
`ADDR_TURBO` returns one hit per version, `ADDR_TURBO_TCC_OFFSET_DEFAULT_VALUE`
= 2010, which is a TCC byte in a different block. That is a whole-tree search
of the committed decompiled sources; it is not a statement about the vendor's
own source, which is not here.

So the block that the fan manager calls **Turbo** and that `ECSpec` calls
**BATTERYSAVER** is one block, under two names, in two class generations:

- `GetBatterySaverPLDefaultValue` reads 1959/1960/1961 — PL1/PL2/PL4, no
  D-state — in `MyFanManager_QC.cs` and `MyFanManager_Intel.cs`.
- `GetTurboPLDefaultValue` reads the same three and additionally 1962, the
  D-state byte, in `MyFanManager_RamFan1p5_Normal.cs` and
  `MyFanManager_RamFan1p5_CML.cs`.

The two names never coexist in one class, so "which one is the battery set" is
not a question the tree poses: there is one byte range, and each generation
reads the part of it that generation has a field for.

`MODE_PL_DEFAULTS`'s note already records the identification ("ECSpec calls
the last block BATTERYSAVER; the 3.1.39.0 fan manager reads it as Turbo"), so
this section confirms rather than corrects it. What is new here is the
negative — that no fourth block exists — and the literal-0 finding below.

### The battery branch writes a literal 0, and consults no default block

`SetUserProfile` in `MyFanManager_RamFan1p5.cs` has an AMD arm and an
non-AMD arm, and both branch on `PowerModeEvent.g_ACLineStatus == 1` and then
write hard-coded zeros:

```csharp
if (PowerModeEvent.g_ACLineStatus == 1)
{
    SetPL1Value(currentProfile.CPU.PL1);
    SetPL2Value(currentProfile.CPU.PL2);
    SetPL4Value(currentProfile.CPU.PL4);
}
else
{
    SetPL1Value(0);
    SetPL2Value(0);
    SetPL4Value(0);
}
```

The zero is a literal in the argument list. No `GetBatterySaverPLDefaultValue`
call, no `GetTurboPLDefaultValue` call, and no read of `0x07A7`-`0x07AA` sits
in that branch — the default block is read when a profile is *seeded*
(`RefreshMode`), and the battery path writes `0` regardless of what was
seeded. So on battery the vendor is not replaying `0x4B 0x4B 0xA5`; it is
writing zero on purpose. That is consistent with the bytes reading `0x00` in
`evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt`, and it means the
tree does contain a record of the battery PL *behaviour* even though the
battery PL *defaults* block is a block with two names rather than a fourth
block.

## 2. What a zero in the PLs means to the EC

The issue notes an asymmetry: the vendor writes zero on battery, and the EC's
own clear at bank0 `0xA833`/`0xA837`/`0xA83B` writes zero too, so a driver
writing zero and the firmware clearing may not be the same thing. The
firmware side of that can be read statically, and the answer is that they are
the same register state — and that the PL consumers treat it one way.

### Every PL read site is a presence test

`trace_xdata_refs.py` finds twelve direct read sites for `0x0783`/`0x0784`/
`0x0785` — four per address — plus the three writes:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x0783 0x0784 0x0785 --csv
```

Per address, one site is the `subb`-against-zero form and three are the
`jz` form. Every one of them **reads the PL, tests it against zero, and stores
it only when it is non-zero**. The two forms are the same test written twice,
because one is a byte compare and the other a presence test:

```
96B4     90 07 83 mov      DPTR, #0x783     ; PL1
96B7     e0 - -   movx     A, @DPTR
96B8     d3 - -   setb     CY
96B9     94 00 -  subb     A, #0x0         ; A - 0, borrow iff A == 0
96BB     40 05 -  jc       0x96c2          ; zero -> skip the store
96BD     e0 - -   movx     A, @DPTR
96BE     90 08 c0 mov      DPTR, #0x8c0
96C1     f0 - -   movx     @DPTR, A
```

and, from `compute_level_blocks_086b_086c_086e` at bank0 `0x9D9B`:

```
9DC8     90 07 83 mov      DPTR, #0x783     ; PL1
9DCB     e0 - -   movx     A, @DPTR
9DCC     60 05 -  jz       0x9dd3           ; zero -> skip the store
9DCE     e0 - -   movx     A, @DPTR
9DCF     90 08 66 mov      DPTR, #0x866
9DD2     f0 - -   movx     @DPTR, A
```

So zero does not substitute a default and does not propagate: the store is
skipped and the destination keeps whatever it held. Stated as narrowly as the
evidence allows — **for every direct read site found by this method, a zero in
`0x0783`-`0x0785` means "no override", not a limit of zero watts.**

That is the answer to the asymmetry from the EC side. A driver writing zero
and the `0xA833` clear writing zero leave the same bytes, and both mean the
same thing to the consumers: leave the destination alone. Which resolves the
open half of §4's asymmetry — the "may not be the same thing at all" worry is
not borne out. What it does **not** resolve is what a *non-zero* value does on
battery, which is the whole of what the procedure has to measure.

### The destinations this feeds are not host-visible

The destinations are `0x08C0`-`0x08C6` in `apply_oem_overrides_then_fill_08xx`
(bank0 `0x96AD`) and `0x0866` in `compute_level_blocks_086b_086c_086e` (bank0
`0x9D9B`) — all three of that routine's PL sites write `0x0866`, and its
neighbour `0x0867` is written from `0x0872`/`0x087A`/`0x088A` rather than from a
PL, so it is adjacent rather than fed. Every one of these is on page `0x0800`,
which reads **0 of 256 bytes non-`0xFF`** in the committed host-window census:

```console
$ grep '^0x0800' evidence/ec-watch/2026-09-24-host-window-page-census.txt
0x0800   0/256
```

`ec_timer_capture.py` refuses an address outside `HOST_WINDOW` unless
`--outside-window` is given, precisely because such an address reads `0xFF`
whatever the EC holds — the census is what that refusal is taken from. **The
copy landing cannot be watched on this machine**, by the tool this repository
uses, and no override of that refusal would make it a measurement of the EC
rather than of the window. This is the reason the procedure grades on
behaviour — sustained clock and package power — rather than on a byte: the
byte that would settle it statically is not readable, and the byte the driver
writes is only half the claim.

Note what that blindness does and does not cover. It is the *values* on page
`0x0800` that the host cannot see, and those are the values every downstream
consumer works from, so nothing about how the copied limit is used is visible
from the host either. The consumer *code* is not on that page and is not hidden
by it: `trace_xdata_refs.py` puts the reads of `0x08C0` at bank0 `0x9935`,
`0x9DA0`, `0x9DA8`, `0x9DB0`, `0x9DB8`, `0x9DC0` and `0xA021`, and of `0x0866`
at `0x9DFB`, `0x9EE4`, `0x9FEB`, `0xBBF2` and `0xD28E` — pages `0x0900`
through `0x0D00`, ordinary mapped firmware. So a reader looking for the code
that consumes these destinations should look there, not at `0x0800`; what the
host cannot do is watch the byte those sites read.

What seeds `0x08C0` and `0x08C4` when no PL override fires is a separate
question this section does not answer; the immediate and CODE-table seeds exist
in the image (`0x9614`/`0x961A` in bank0 `95DD.asm` are immediates, the
`store_code_byte_to_08c*` helpers are CODE-table reads), and the order in which
they run relative to the override sites is not established here.

### Two corrections to the site list

Both are to `ec/annotations/manual-fan-ctrl-0751.md` §5, and both are stated
here rather than silently fixed there.

**The enumeration is by reference, not a list.** §5 says "four reads per
address (`subb`-against-zero at `0x96B4`/`0x96C2`/`0x96D0` and `jz` presence
checks at `0x97D8`/`0x98C4`/`0x9DC8` and the equivalents for the other two
bytes)". The count of four stands — `trace_xdata_refs.py` finds four per address.
Six addresses are named and the other six are covered by the phrase "the
equivalents for the other two bytes", which is complete rather than wrong: those
are `0x97E3`/`0x98CF`/`0x9EB1` for `0x0784` and `0x97EE`/`0x98DA`/`0x9FC3` for
`0x0785`. **No site is missing.** What the phrase costs is that the six it
covers cannot be checked by eye against the disassembly, which is why the
enumeration is listed out here rather than left as a shorthand — a reader who
wants to confirm the level-block routine's sites one by one has nothing to read.
The count was never wrong and the list was never short; only its resolution
required work.

**`0x9DC8` is not under the `0x0741` guard.** This is the substantive one.
§5 groups `0x9DC8` with the `0x96AD.asm` sites in one parenthetical, which reads
as though the twelve sites share a gate. They do not. The three sites in
`compute_level_blocks_086b_086c_086e` sit in a routine that never mentions
`0x0741` — there is no `mov DPTR, #0x741` anywhere in bank0 `9D9B.asm` — so
they are not gated on `AP_OEM` bit 0. The nine sites in `96AD.asm` are: each of
its three guarded blocks opens with a `0x0741` read and a `jnb 0xe0`, at
`0x96AD`, `0x97D1` and `0x98BD`. The guard is a property of the routine, not of
the idiom, and the idiom is unguarded in the other one. This does not change
the zero semantics — the presence test is local to the site either way — but it
does mean a PL override can reach `0x0866` whether or not a host agent has
announced itself, which the grouping obscured.

## 3. What is not found by this method

- **No AC/battery differentiation on any PL path.** A search of the main EC
  image for the PL read sites' surrounding guards finds no AC-present,
  battery-present or mode byte compared at any of the twelve sites, and
  `ec/annotations/registers.yaml` carries no AC-detection symbol among the
  registers these paths touch. All AC/battery differentiation found is
  host-side, in `SetUserProfile`'s `g_ACLineStatus` branch. This is "not found
  by this method", not "the EC cannot tell": the EC certainly reads some byte
  that reflects its input, and which one has not been identified here.
- **No path found by this method carries a default block byte into a PL
  register.** This restates `manual-fan-ctrl-0751.md` §5's conclusion for the
  battery block specifically, and it inherits that section's caveat about
  indirect access.
- **Which service class runs on this board.** `v3.1.39.0` ships both
  generations, and they differ in what they *seed*: `MyFanManager.cs` has
  `GetGamingPLDefaultValue` and `GetOfficePLDefaultValue` and no accessor for
  the third block at all, while `MyFanManager_RamFan1p5*.cs` has
  `GetTurboPLDefaultValue`, reading the same three addresses plus `0x07AA`.
  `GetBatterySaverPLDefaultValue` is the same block under the other name and
  is defined in `MyFanManager_QC.cs` and `MyFanManager_Intel.cs`; as §1 records,
  the two names never coexist in one class. They do **not** differ on what they
  write on battery — `SetFanMode` in the older one takes a `g_PowerMode == 0`
  branch that calls `SetPL124Tau(0u, 0u, 0u, ...)` for each mode, which is the
  same hard-coded zero the newer one writes from `SetUserProfile`. So the
  literal zero on battery is a property of the service, not of one generation,
  and which generation is loaded does not change the answer. What it could
  still change is whether the vendor re-seeds the profile and re-asserts the
  PLs during a run, which is why the procedure asks the operator anyway.
- **What a non-zero PL does on battery.** Not answerable from any of this.

## 4. What the run has to settle

Given the above, the question narrows and sharpens. It is no longer "what
does zero mean" — for every read site found, that is settled. It is:

> On battery, with the vendor's zero in place, does a **non-zero** value
> written to `0x0783`/`0x0784`/`0x0785` reach the sustained clock and package
> power under a fixed load?

The static answer says the path is live — the sites are unconditional reads
with a presence test, not gated on any AC byte this method could find — so a
non-zero write *should* propagate. "Should" is not "does", and the run is
what separates them.

[`../hardware-tests/battery-pl-limit-effect.md`](../hardware-tests/battery-pl-limit-effect.md)
is that run. It watches the PL registers the driver writes, the fan duty
bytes and the die temperature, and grades on sustained clock and package power
rather than on a byte — because §2 above establishes that the byte the EC
copies into is not host-readable.

## 5. Files

- [`../hardware-tests/battery-pl-limit-effect.md`](../hardware-tests/battery-pl-limit-effect.md) —
  the unrun procedure.
- `ec/annotations/manual-fan-ctrl-0751.md` §5 — the site list corrected in
  place against §2 above.
- `ec/annotations/registers.yaml`, `MODE_PL_DEFAULTS` and
  `CPU_PL1 / PL2 / PL4` rows — one appended line each, naming this write-up.
  No `status:` moves: nothing here is behavioural evidence.
- `windows/vendor-ec-map.md` "Power modes" — the capture that recorded the
  zero on battery, and the AC plug-in re-apply that would contaminate a run.