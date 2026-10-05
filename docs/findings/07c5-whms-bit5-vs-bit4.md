# `0x07C5`: bit 5 is the whisper-mode switch, bit 4 is a safety-protect skip (issue #1260)

`0x07C5` carries one DSDT name, `WHMS`, at bit 5, and nothing in the tree had
expanded it. `ec/annotations/dsdt-ecmg-field-sweep.md` put it no further than
"a name, not a statement about what the bit does", and
`ec/annotations/ec-07c4-07d5-sites.md` §9 deferred the question to two issues
that could not answer it. **This file answers it: bit 5 is the GPU whisper-mode
main switch and the service writes it; bit 4 is a different field with its own
name, the office-mode / fan-safety-abnormal-protection skip.** The two are
independent fields on one byte, not one field misread.

It also withdraws a claim this repository made about its own evidence. The
`WHMS` note in `ec/annotations/registers.yaml` said the bit was "independently
pinned by `windows/tools/gpu_block_watch.py` … and the two agree from opposite
ends of the stack". They did not agree from opposite ends, and could not have:
the watch table's status column is held against `registers.yaml` by
`CitationTableTests.test_every_registers_yaml_status_is_verbatim` in
`windows/tools/test_gpu_block_watch.py`, so the oracle cited as corroboration
is a copy of the file it was supposed to corroborate. The wrong sentence is
left standing in the note with the correction beside it, per `CLAUDE.md`'s
calibration rule.

**Nothing here is a live test.** There is no laptop and no Windows machine
reachable from a GitHub-hosted runner, so no register was read back and no
write was attempted. Every claim below is a reading of committed text, and the
strongest statement available is *a name, plus a setter that writes that bit
position*. `WHMS` keeps `status: present-untested`.

## Bit 5: the whisper-mode main switch

`GpuFeatures.SetGpuWhisperModeMainSwitch`, in
`windows/decompiled/v3.1.39.0/GCUService/GCUService.MyFan.Overclocking/GpuFeatures.cs`,
is a read-modify-write of the byte the service spells in decimal, `1989`
(`0x07C5`). Its shape is the one every setter on this byte uses — read, mask,
add, write:

```csharp
byte b  = 159;          // 0x9F
byte b2 = (status == 1) ? 96 : 64;   // 0x60 / 0x40
EcCtrl.Read(GetType().Name, 1989, ref Data);
b3 = (byte)((Data & b) + b2);
EcCtrl.Write(GetType().Name, 1989, b3);
```

(A condensation: the committed `.cs` spells the conditional as an `if`/`else`
so that the `else` arm can also call `SetWhisperModeStatusDisable()`, which
touches `0x07C6` and not this byte. The arithmetic is as shown, and
`ec/tools/test_07c5_whms_bits.py` reads it back out of the file.)

`0x9F` is `0b10011111`, so it clears bits 5 and 6 and preserves bits 0-4 and 7.
The addend then sets the two cleared positions, and because the masked value
has both of them at zero, adding cannot carry into bit 7 (`0x9F + 0x60 = 0xFF`,
the largest the expression can reach). So the two arms are:

| argument | addend | binary | bit 5 | bit 6 |
|---|---|---|---|---|
| `status == 1` | `0x60` | `0b01100000` | **set** | set |
| anything else | `0x40` | `0b01000000` | clear | set |

**Bit 5 follows the argument**, from any prior value of the byte, which is what
the mask is doing: it makes the bit's new state independent of what was there.
`ec/tools/test_07c5_whms_bits.py` replays both arms over every prior byte value
and holds exactly that.

The same setter shape is spelled out in the three branch siblings that carry
their own `SetGpuWhisperModeSwitch` — `MyFanManager_RamFan1p5_CML`,
`…_NV` and `…_Normal` — with the identical `0x9F` mask and the same two
addends, the conditional written the other way round
(`b2 = (byte)((status != 1) ? 64 : 96)`). Those three are private and this
finding does not claim they are called. `GpuFeatures`'s is public, and
`MyFanManager_RamFan1p5` calls it from `Disable` and from `Uninstall` behind
`m_IsNvGpu`, and from `SetUserProfile` behind `m_IsNvGpu` and then
`m_IsHeroProject`. That is a call-graph reading of committed `.cs`, not an
observation of the service running, and whether this board satisfies either
guard is not settled here.

## Bit 4: the safety-protect skip

Two setters take the same byte and touch bit 4 only:

| setter | mask | addend | field |
|---|---|---|---|
| `MyFanManager_RamFan1p5.SkipOfficeModeSafetyProtect` | `0xEF` | `status == 1 ? 0x10 : 0` | office-mode safety protection |
| `…_CML.SkipFanSafetyAbnormalProtection`, and its `_NV` / `_Normal` siblings | `0xEF` | same | fan-safety-abnormal protection |

`0xEF` is `0b11101111`: bit 4 cleared, every other bit preserved, and again no
carry out of bit 7 (`0xEF + 0x10 = 0xFF`). Bit 4 therefore tracks the argument
and nothing else on the byte moves.

**Neither touches bit 5.** One byte, two independent setters, in three
separate classes. `SkipOfficeModeSafetyProtect` is the uncalled one already
recorded in `docs/findings/uncalled-vendor-setters.md`;
`SkipFanSafetyAbnormalProtection` is the called one — each of the three
siblings passes it
`currentProfile.FAN.SkipSafetyAbnormalProtection` from its `SetUserProfile`.
So bit 4 is not dead on the service side, which the uncalled-setter write-up
could not say about the byte.

This is the bit `ec-annotations/ec-0x07c5-sites.md` §3.5 found the firmware
testing: `jnb acc.4` at `0xB5F5` and `0xB755`, the matched pair in the USER fan
path, is the same bit position. That walk recorded the coincidence as "a fact
about the two halves' instruction streams and … not evidence that the service
and the firmware mean the same field by it", which was right about what it had;
the mask arithmetic is what adds to it, and it adds the same caution.

The whole byte, the service's writers and the field list together:

| bit | set by | named by |
|---|---|---|
| 0-2 | `SingleZone.StartBreathingMode`, mask `0xF8` | the RGB keyboard's per-zone breathing-colour index; see the `0xBB80`/`0xBB81` section |
| 4 | `SkipOfficeModeSafetyProtect` / `SkipFanSafetyAbnormalProtection`, `0xEF`/`0x10` | office-mode and fan-safety-abnormal protection skip |
| 5 | `SetGpuWhisperModeMainSwitch`, `0x9F`/`0x60`/`0x40` | `WHMS`, the DSDT's name for the bit |
| 6 | set by both whisper arms; cleared by the EC's `0x83FF` | — |
| 7 | `FanTable_Manager1p5.SetEcFanControlRespective`, `0x7F`/`0x80` | CPU/GPU fan-table split; upstream `SPLIT_TABLES` |

Bit 3 is the one position this file has nothing for: no setter in the service
and no site in the walk moves it, and the DSDT leaves it unnamed.

## The ASL reads the same bit and publishes it as a hardware event

`WHMS` is host-visible, not just a bit the service writes.
`evidence/acpi/dsdt.dsl:50727` has `T1WR`'s `Arg0 == 0x75` arm assign
`^^NPCF.WMEN = ^^PCI0.LPCB.EC0.WHMS` and then `Notify(NPCF, 0xC1)`, so a write to
the bit becomes a hardware event; a second read at `dsdt.dsl:52817` assigns the
same field to the same `WMEN`, an ASL name that pairs with `WHMS` the way
`SetGpuWhisperModeMainSwitch` pairs with the bit it writes. **The pairing is a
reading, and only that** — two names that look like the same feature spelled
twice is not a statement about what either one does.

`docs/findings/ecmg-asl-references.md` already tabulates every ASL use of the
field against `registers.yaml`, `WHMS` among them. That is issue #1159's work
and is referenced here, not redone. The `0x75` arm is held machine-readably in
`ec/tools/dsdt_ec_fields.py`'s `T1WR_ARMS`, which re-derives it from the parsed
body and the `registers.yaml` entry on every `--self-test`.

## Bit 6: an observation, and nothing more

Both arms of the whisper switch set bit 6 (`0x60` and `0x40` both have it), and
the EC's `0x83FF` clears it — `jnb acc.6` at `0x8410`, per
`ec/annotations/ec-0x07c5-sites.md` §3.2, where the note about the per-site
window stopping at a branch applies. **No writer in the decrypted
`v3.1.39.0` tree clears bit 6 of this byte**, and every one of them is swept
in `ec/tools/test_07c5_whms_bits.py` rather than the claim resting on this
file's reading. The two other committed trees are partial — anti-tamper
casualties — and a scan of them finds no reference to the byte at all, which is
a weaker claim than the same scan of the decrypted tree;
`windows/tools/test_ec_addr_reach.py` is where that asymmetry is argued.

All of this is a fact about two instruction streams meeting at a bit position.
No capture says what the position does, and whether the EC acts on it at all is
not established. It is the first question `ec-annotations/ec-0x07c5-sites.md`
§8 lists as open, and it stays open here.

## Why the generated census could not have answered this

`windows/decompiled/v3.1.39.0/ec-callsites.csv` records the service's EC
accesses, and **every write row for `0x07C5` carries `value_expr` `b3`** — the
variable holding the masked result. The column that would separate the bits is
the column the census does not carry. `ec_callsites.py` emits one row per call
site — the method, the direction, the address and the argument expressions as
written — and the mask that names the bit lives one statement earlier in the
method body, which is why the answer came from the `.cs` and not from the table.
`ec/tools/test_07c5_whms_bits.py` holds that property, so if the census ever
learns to resolve a mask the suite says so instead of the limitation going quiet.

## `0xBB80` and `0xBB81` were already answered

The pair the issue asks about is not re-derived here.
`ec/annotations/ec-0x07c5-sites.md` §2.1 reads `0xBB80` as one
`movx @DPTR,A` against whatever `DPTR` the caller left — it never addresses this
byte — and records that the `[writer]` tag `xdata_register_map.py` puts on
`bank0:0xBB80=store_a_then_read_07c5` is therefore wrong. The tag is generated,
so the correction lives in the walk and in the door procedure's `0x07C5` cell
rather than in a hand-edit of the CSV. §3.6 reads `0xBB81` as
`is_07c5_bit0_clear`: it returns `1` when bit 0 is clear and `0` when set, and
the `xrl` scrambles the other seven bits into the return value without carrying
information.

Bit 0 is not named by the DSDT field list, and this write-up does not name
it either. What it does record, because it bears on a question
`ec/annotations/ec-0x07c5-sites.md` §8 leaves open: the service does write
the low bits of this byte. `MyControlCenter.MyRgbKeyboard.SingleZone`
`StartBreathingMode` masks the byte with `0xF8` and adds an index of 0-4, so
bits 0-2 are one small field carrying the per-zone breathing-colour index of
the RGB keyboard. That is a naming of the low bits from the Windows side
only. Whether the EC's `0xBB81` and `0xA777` — which reads bit 0 alone and
tests bits 0-2 as a unit — are looking at this field is a separate reading
that this file does not attempt and that a capture would settle.

## The retraction, and what replaces it

The `WHMS` note claimed:

> That bit is independently pinned by windows/tools/gpu_block_watch.py, which
> watches this byte for exactly this field ("WHMS b5", citing dsdt.dsl:52243 and
> this row), and the two agree from opposite ends of the stack.

That sentence is wrong, and it was not a slip of phrasing — the agreement could
not have been anything else. `gpu_block_watch.py`'s `0x07C5` row now reads
`(0x07C5, "WHMS b5", "present-untested", …)`, and
`CitationTableTests.test_every_registers_yaml_status_is_verbatim` holds its
status column **against** `registers.yaml`. A cell derived from the file it is
cited to corroborate cannot corroborate it. `ec/tools/dsdt_ec_fields.py`'s
`ORACLES` rested on the same claim — its comment read "Two sources, two stacks,
one bit index" while naming `gpu_block_watch.py` as one of the two, and quoted a
tuple spelling `NO_ROW` that the watch table no longer holds.

**What replaces it is two readings that do not come from `registers.yaml`,
and neither of them is a copy of anything else here:**

- **The service's mask arithmetic**, in the committed `.cs` above, which puts
  the whisper-mode main switch at bit 5 of the same byte from the other end of
  the stack. Nothing in this repository holds that file against
  `registers.yaml`, and no tool regenerates it.
- **The EC's own `anl a,#0xdf`** at `0xAD8C` and `0xCC6B`, in the two init
  routines `ec/annotations/ec-0x07c5-sites.md` §3.1 walks, which clear that
  same bit position from firmware bytes rather than from either.

The DSDT's field list — `Offset (0x7C5)`, five unnamed bits, then `WHMS, 1` at
`dsdt.dsl:52243`-`:52245` — is where the index came from in the first place,
so it cannot corroborate itself and is not counted here. What the three inputs
give is two independent readings agreeing with the bit the ASL named: a bit
position, which is all this file claims.

The status value does not move. `WHMS` stays `present-untested`: a matching
setter name and a matching ASL field name are agreement about a bit position,
not evidence that the EC acts on it, and `CLAUDE.md` is explicit that only a
live behavioural test is that.

## What this does not establish

- **Not that the EC acts on bit 5.** Three inputs agreeing on a bit index is
  agreement about a position. No capture shows the bit moving, and none of the
  three inputs is a measurement of firmware behaviour.
- **Not what bit 6 does**, only that both arms of the whisper switch set it and
  one EC routine clears it.
- **Not what bit 4 means to the firmware** beyond the position. The USER fan
  path's `jnb acc.4` is now a matching position against a named service field;
  what the two sides mean by it is still a capture's question.
- **Not that the service's setters and the firmware's sites correspond**, which
  `ec/annotations/ec-0x07c5-sites.md` §4 also leaves open and which nothing
  here closes.
- **Not a status change**, and not a bit-0 name.
- **Nothing observed on hardware.** No register was read back, no write was
  attempted, no EC was opened. The door procedure's `0x07C5` row in §5 stays
  blank; an example row there reads as an observation, and
  `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md` already carries that
  procedure and its grader.

## Reproducing

The mask arithmetic, from the committed decompile:

```sh
sed -n '/SetGpuWhisperModeMainSwitch/,/^	}/p' \
  windows/decompiled/v3.1.39.0/GCUService/GCUService.MyFan.Overclocking/GpuFeatures.cs
sed -n '/SkipOfficeModeSafetyProtect/,/^	}/p' \
  windows/decompiled/v3.1.39.0/GCUService/MyControlCenter.MyFan/MyFanManager_RamFan1p5.cs
```

The DSDT's bit index for the name:

```sh
sed -n '52243,52245p' evidence/acpi/dsdt.dsl
```

The ASL arm, re-derived rather than quoted —
`WHMS is bit 5 of 0x07C5` must stay `ok`:

```sh
python3 ec/tools/dsdt_ec_fields.py --self-test
```

The two statements in this file that a future vendor dump could falsify — the
masks, and the census's inability to separate the bits — are held by
`ec/tools/test_07c5_whms_bits.py`, which reads the same `.cs` files this
write-up reads and fails if a mask moves.

The site walk this file leans on rather than restates is
`ec/annotations/ec-0x07c5-sites.md`, with its per-site table in
`ec/annotations/ec-0x07c5-sites.csv`.