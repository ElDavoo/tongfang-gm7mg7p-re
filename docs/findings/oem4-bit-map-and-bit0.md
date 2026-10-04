# The `0x07A6` (`OEM_4`) bit map, and bit 0's owner (issue #93)

**Read this first: everything below is static.** No laptop was opened, no EC
register was read back, no Windows service was run. The three things this file
leans on that are *not* static analysis are all prior observations cited from
committed evidence files, not results of this work: the live byte values in §7
(`0x29` on 2026-09-18, `0x28` on 2026-09-19), the `0x0782` read of `0x9D` in
§3 (2026-09-23), and the service's `RamFan1p5Support`,
`IsProjectIdCommercial` and `CustomizeTarget` values that put it on a
`RamFan1p5` board in §2 (captured 2026-09-18). The EC-side claim in §3 is an
instruction sequence, not an
observed behaviour: that the EC sets bit 0 at `0xABC0` is a reading of
committed bytes, and whether the EC *acts* on the bit is a separate question
this file does not answer.

Issue #93 asked for two things — the full bit map of `0x07A6`, and who owns bit
0. The first is a table. The second has an answer that is a **link between two
things already in the tree** rather than a new discovery: the EC firmware sets
bit 0 at `0xABC0`, inside the function this repo already named
`set_0751_and_07a6_bits`, and `registers.yaml`'s own `OEM_4` note is what
records the open question it settles. Two of the plan's own framings needed
correcting on the way, and both corrections are in §2 and §6 rather than left
implicit: `SetApExist` exists as *two* unrelated methods on two different
bytes, and the BIOS negative holds over host x86 code only, because the BIOS
ROM embeds the EC firmware itself.

Two claims in this file are **negatives**, and are written as "not found by
these searches over these files" for the reason `docs/findings.md` §4c and
`ec/annotations/registers.yaml`'s own header give: the DSDT (§5) and the BIOS
(§6). Neither is "there is none".

## 1. The bit map

All eight bits, one row each, with the instruction or expression and the file
and line it is at. Every address is EC XDATA `0x07A6` (decimal 1958). The
vendor table is regenerable rather than transcribed — see the command under the
table.

| bit | writer (vendor 3.1.39.0) | what it does to the byte | where |
|---|---|---|---|
| 0 | `MyFanManager.SetApExist(bool exist)` | `(!exist) ? (b & 0xFE) : (b \| 1)` | `MyControlCenter/MyFanManager.cs:1500-1507`; same body at `MyFanManager_Intel.cs:2121-2128`, `MyFanManager_QC.cs:1593-1600` |
| 1 | `MyFanManager.SetOverBoostByDynamicTemp(bool bEnable)` | `b2 = (!bEnable) ? 2 : 0; b3 = (byte)((Data & 253) + b2)` | `MyFanManager_Intel.cs:2097-2108`, `MyFanManager_QC.cs:1580-1591`; the same body in all four `MyControlCenter.MyFan/MyFanManager_RamFan1p5*.cs` |
| 2 | `MicMuteControl.SetLED(bool bMute)` | `(!bMute) ? (b & 0xFB) : (b \| 4)` | `GCUService.MySetting.Muter/MicMuteControl.cs:42-49` |
| 3 | `MySettingManager.UserSetTouchPadLedStatus(int status)` | `(status != 1) ? (b & 0xF7) : (b \| 8)` | `MyControlCenter/MySettingManager.cs:559-566`, `MySettingManager_Intel.cs:302-309` |
| 4-5 | `BatteryProtection2.SetHealthProtection{High,Middle,Low}` | `BitArray[4] = …; BitArray[5] = …` (00/01/10) | `GCUService.MySystem/BatteryProtection2.cs:271-302`; the earlier `GCUService.MySystem/BatteryProtection.cs:389-423` does the same |
| 6 | `MySettingManager.TouchpadToggle_ON` / `_OFF` | `_ON` writes `Convert.ToUInt64(Data) & 0xBF`; `_OFF` writes `(byte)(64 + b)` over the same `& 0xBF` | `MyControlCenter/MySettingManager.cs:1224-1248` |
| 7 | **no writer found** by the two scans named below | — | — |

```sh
# regenerates rows 0-6 above from the committed decompiled tree, not a transcription
python3 windows/tools/ec_callsites.py windows/decompiled/v3.1.39.0/GCUService --addr 0x07A6
```

That command returns 42 sites across 13 distinct methods: 12 that write the
byte and one, `IsOnApLoadFromEc`, that only reads it. Every `file,line` in the
table above is one of them. Compared against the committed
`windows/decompiled/v3.1.39.0/ec-callsites.csv`, its rows are identical **as a
set** (869 rows, same file list) but not in the same *order*: the tool walks
the tree with `os.walk` and does not sort, so row order follows directory
iteration order and differs between filesystems. A reader diffing the two files
byte-wise will see a spurious diff; the set comparison is the meaningful one.

**Bit 1 is an `ADD`, not an `|`.** `253` is `0xFD`, so the mask clears bit 1,
and the bit is then *added* back when `bEnable` is false. The outcome matches
the issue's gloss (set = dynamic-temp overboost off, which is upstream
`uniwill-laptop`'s `OVERBOOST_DYN_TEMP_OFF` `BIT(1)`), but **a scan keyed on
`| 2` or `| 0x02` misses this method entirely.** That is the one row in this
table a naive bit-scan would lose, which is why the expression is written out
rather than summarised as "bit 1".

```sh
sed -n '2097,2108p' windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/MyFanManager_Intel.cs
```

One caution if you go looking for it this way: `(Data & b) + b2` is not unique
to this method. It is the vendor's general *mask-and-add* idiom, and six
sibling methods in the same file use it with other masks — `SetPowerLedStatus`
(251), `SetFanQuietModeEnable` (251), `SetUserHiModeToFantable` (247),
`SetOverBoostMode` (239) and `SetPowerStatus` (127) all on **`0x07A5` (1957)**,
not on this byte. Only `SetOverBoostByDynamicTemp` pairs mask 253 with address
1958, so a `grep` on the expression alone returns seven methods and identifies
none of them. The `sed` above is the check that actually decides it, because it
shows the mask, the expression and the address in one window.

**Bit 7 is "no writer found", not "unused".** Two independent scans over the
committed tree return nothing for it — `ec_callsites.py` (vendor C#, 3.1.39.0)
and `trace_xdata_refs.py` (EC firmware, §3). Per this repository's standing
rule that is a statement about the two methods, not about the bit.

**The address is stable across vendor versions.** All three committed
decompiled trees define `ADDR_AP_OEM_BYTE4 = 1958` at line 365 of their
`ECSpec.cs` (`v3.1.6.0/ECSpec.cs`, `v3.9.18.0/Define/ECSpec.cs`,
`v3.1.39.0/GCUService/Define/ECSpec.cs`), so the byte is a stable vendor
concept and not an artefact of one build. Comparing the older trees' bit maps
is separate work and is not done here.

## 2. Why the fan manager that runs here cannot write bit 0 — and the `SetApExist` trap

The issue's framing was that the class running on this machine inherits
`MyFanManager` but never reaches its private `SetApExist`. That is right, and
the reason is sharper than "inherits but doesn't call".

`MyFanCtrl`'s constructor (`MyControlCenter/MyFanCtrl.cs:26-72`) chooses exactly
one `m_Manager`, and on a RamFan1p5 board it is one of four classes:
`MyFanManager_RamFan1p5` (`:54`), `_NV` (`:50`, `:65`), `_Normal` (`:62`) or
`_CML` (`:68`). All four derive from `MyFanManager`.

**This machine takes a `RamFan1p5*` arm, and that is a recorded fact, not an
assumption** — it is the pivot the whole answer rests on, so here is the
evidence for it. The first branch is `:30`, `if (!EcCtrl.IsSuportRamFan1p5())`;
if it were true the constructor would have instantiated the plain
`MyFanManager` instead and the answer below would be the *opposite* one. The
service publishes both branch conditions to a topic this repo has captured:

| field | recorded here | which branch it decides | who writes / reads it |
|---|---|---|---|
| `RamFan1p5Support` | `1` | `EcCtrl.IsSuportRamFan1p5()` is true, so `:30` is false and the plain-`MyFanManager` arm (`:35`, `:39`, `:42`) is skipped | computed at `CustomizeCtrl.cs:373`, written to `HKLM\SOFTWARE\OEM\GamingCenter2\ItemSupport` at `:392`, read back at `MqttClientCtrl.cs:236` |
| `IsProjectIdCommercial` | `0` | `!EcCtrl.GetProjectIdFromEC().IsProjectId_Commercial()` is true, so the `:46` arm is taken | `m_ProjectID = EcCtrl.GetProjectIdFromEC()` at `CustomizeCtrl.cs:34` — the same call `MyFanCtrl.cs:46` makes — inverted at `:361`, written at `:388`, read back at `MqttClientCtrl.cs:232` |
| `CustomizeTarget` | `1` | not 42, so the `:48` test fails and `:54` is reached | `MqttClientCtrl.cs:250-253` reads `SOFTWARE\OEM\GamingCenter2\CustomizeTarget`, the same key and the same default-of-1 as `RegistryCtrl.GetCustomizeTarget()` (`RegistryCtrl.cs:161`) reads for `MyFanCtrl.cs:28` |

The values are from `evidence/mqtt-capture/2026-09-18-profile-and-connect.jsonl`
— line 12 is the first `Customize/SupportInfo` publish carrying all three, and
the topic is `RegistryBuilder()`'s dictionary verbatim. **This is a prior
recorded capture of the service on this machine, cited from a committed file;
nothing was re-run for this write-up.** Taken together the three select
`MyFanManager_RamFan1p5` at `:54` specifically, though the argument below needs
only "one of the four".

Measured over the four files:

| | `SetApExist` | `base.Init()` | `base.Uninstall()` |
|---|---|---|---|
| `MyFanManager_RamFan1p5.cs` | 0 | 0 | 0 |
| `MyFanManager_RamFan1p5_CML.cs` | 0 | 0 | 0 |
| `MyFanManager_RamFan1p5_NV.cs` | 0 | 0 | 0 |
| `MyFanManager_RamFan1p5_Normal.cs` | 0 | 0 | 0 |

`SetApExist` is `private` (`MyFanManager.cs:1500`), so it is not
inherited-visible in the first place. Its only two call sites are `:389`, in
`public virtual void Uninstall()`, and `:1030`, in `Init()` — and the derived
classes override both without calling `base`. `RamFan1p5.Uninstall()`
(`MyFanManager_RamFan1p5.cs:221-250`) is a full replacement that ends by
writing `ApExistFlag` to **NVRAM** (`:248`, via `NvramVariable.SetFwVars`)
rather than the EC byte. So the same "AP exists" fact is still recorded on the
uninstall path — through the UEFI variable, not through `0x07A6`. **The fan
manager running on this machine cannot write bit 0 of `0x07A6`.**

**The predicate is load-bearing**, which is why the branch condition is cited
above rather than left to the class hierarchy. Had the recorded
`RamFan1p5Support` been `0`, `MyFanCtrl.cs:30` would have taken the plain arm
and `m_Manager` would have been a `MyFanManager` — whose `Uninstall()` calls
`SetApExist(exist: false)` at `MyFanManager.cs:389`, clearing bit 0, and whose
`Init()` calls it at `:1030`, setting it. A vendor method *would* then have
owned bit 0 and issue #93's question would have had the other answer. What
decides which way it goes is the recorded predicate, so that is what has to be
cited wherever this conclusion is repeated.

**The trap: `SetApExist` is two methods, on two different bytes.** A reader who
greps the name finds thirteen call sites, not two:

```sh
grep -rn "SetApExist(" windows/decompiled/v3.1.39.0/GCUService | grep -v "void SetApExist"
```

Four are the fan managers above (`MyFanManager.cs:389`, `:1030`, and
`MyFanManager_Intel.cs:306`, `MyFanManager_QC.cs:275`). The other **nine** —
`MyRgbLightbarManager.cs:47`, `:64`, `:170` and three each in its `_Intel` and
`_QC` siblings — call a *different* method with the same name and
near-identical bit-0 semantics:

```
MyControlCenter/MyRgbLightbarManager.cs:547
private void SetApExist(int mode)
{
    byte Data = 0;
    EcCtrl.Read(GetType().Name, 1864, ref Data);   // 1864 = 0x0748, NOT 0x07A6
    byte b = (byte)(Convert.ToUInt64(Data) & 0xFF);
    b = ((mode != 0) ? ((byte)(b | 1)) : ((byte)(b & 0xFE)));
    EcCtrl.Write(GetType().Name, 1864, b);
    LogCtrl.Write($"... After SetApExist, AP read 0x0748h = 0x{b:X}");
}
```

Same `& 0xFE` / `| 1` idiom, `int` instead of `bool`, and **`0x0748` instead of
`0x07A6`** — the RGB lightbar register. All three definitions are identical
here and all three write 1864 (`MyRgbLightbarManager.cs:547-555`,
`_Intel.cs:539-547`, `_QC.cs:546-554`); each even logs the same `0x0748h`.
`ec-callsites.csv` separates them cleanly (`:370-371` carry `0x0748`; the
fan-manager rows carry `0x07A6`), which is the reason the tool is the citation
and a `grep` on the method name is not. This is a name collision across two
unrelated registers, and it is the most likely way for a future reader to draw
the wrong conclusion from this file.

## 3. The EC-side census, and bit 0's owner

```sh
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07A6 --csv
```

Seven sites, all in `bank0`, none in the PD image. The `access` column is that
tool's linear walk, which stops at the first control-flow instruction.

| site | access | window | what it does to the byte |
|---|---|---|---|
| `0x0AAC6` | read x1 | `movx a,@dptr ; jnb acc.6,+0x03` | reads bit 6 (into a named function, `advance_0d14_state`) |
| **`0x0ABC0`** | **read x1, write x1** | **`movx a,@dptr ; orl a,#0x01 ; movx @dptr,a`** | **sets bit 0** |
| `0x0AD0D` | read x1, write x1 | `movx a,@dptr ; anl a,#0xbf ; movx @dptr,a` | clears bit 6 |
| `0x0B13A` | read x1, write x1 | `movx a,@dptr ; anl a,#0xcf ; movx @dptr,a` | clears bits 4-5 (the profile reset) |
| `0x0B2E2` | read x1 | `movx a,@dptr ; anl a,#0x30 ; …` | reads bits 4-5 |
| `0x0B330` | read x1 | `movx a,@dptr ; anl a,#0x30 ; …` | reads bits 4-5 |
| `0x0CD11` | read x1, write x1 | `movx a,@dptr ; anl a,#0xbf ; movx @dptr,a` | clears bit 6 |

**Bit 0's owner is the EC, at `0xABC0`** — which is inside a function this repo
already named and annotated. `ec/decompiled/bank0/AB9E.asm:24-27`:

```
ABC0     90 07 a6 mov      DPTR, #0x7a6
ABC3     e0 - -   movx     A, @DPTR
ABC4     44 01 -  orl      A, #0x1
ABC6     f0 - -   movx     @DPTR, A
```

`ec/annotations/ghidra-functions.csv:152` already carries that row, named
`set_0751_and_07a6_bits`, with a plate comment that already says "Otherwise it
sets bit 0 of 0x7A6 (OEM_4)". **This work is the link between that row and
`registers.yaml`'s open question, not a new row** — which is why
`ghidra-functions.csv` is deliberately untouched.

**The gate in front of that write is the part worth knowing.** `AB9E.asm:7-9`
reads `0x0782` (`BIOS_OEM_2`) and branches past the setter:

```
AB9E     90 07 82 mov      DPTR, #0x782
ABA1     e0 - -   movx     A, @DPTR
ABA2     30 e1 1b jnb      0xe1, 0xabc0      ; if bit 1 clear -> 0xABC0, set bit 0
```

Bit 0 of `0x07A6` is therefore set **only when bit 1 of `0x0782` is clear**.
`ec/annotations/registers.yaml`'s `BIOS_OEM_2` entry — `addr: 0x0782`, at
`:1975-1989` in this branch's tree, and the name plus address is the part that
survives the next edit above it — calls bit 1 the Q-key and records a live read
of `0x9D` on 2026-09-23. `0x9D` has bit 1 clear, so the condition held on this
machine. That is a real fact about the firmware, and it is checkable from
committed files without a laptop.

**No site in this census clears or reads bit 0.** Nothing masks with `0xFE`;
`0xAD0D` and `0xCD11` clear bit 6, `0x0B13A` clears bits 4-5, and the three
read sites test bit 6 or bits 4-5. That is the answer to the issue's "if the EC
reads bit 0, say what it does with it": **by this scan, it does not read it.**

That last sentence carries the weight this repository's calibration rule puts on
it, so the caveat is stated rather than left in the tool's docstring:

> It is still a static scan and is NOT `live`: a zero is "not found by this
> method", never "absent", and a read-modify-write is evidence the EC touches a
> byte, not that it acts on it. The access column is a linear walk that stops at
> the first control-flow instruction, so a store a branch jumps over is
> invisible to it.
> — `ec/annotations/registers.yaml`, the `xdata-refs` source note

The blind spot is documented for this exact image: `0x07B0-0x07BE` is a range
where Windows writes a byte that works and no direct `MOV DPTR` reference exists
anywhere (`docs/findings.md` §4c). So "no clearer found" is a statement about
`trace_xdata_refs.py` over this image, and the 2026-09-19 observation in §7 is
the reason that distinction is load-bearing rather than pedantic.

## 4. "Bit-addressable forms" — there are none, and that is a fact about the ISA

The issue asked for `orl a,#0x01` / `anl a,#0xFE` after `mov dptr,#0x07a6`
**plus bit-addressable forms**. The second half of that has no answer to find:
on the 8051, bit addressing covers only internal RAM and the SFRs, never
XDATA. `ec/tools/disasm8051.py:108-110` holds the SFR set (`BIT_SFR`), and
`bit_name()` at `:126-132` is the rule in code — an operand at `0x80` and above
is a bit of an SFR, anything lower is `0x20 + (b >> 3)`, i.e. internal RAM.
XDATA is reached through DPTR and has no bit-addressable form at all, so a
"bit-addressable write to `0x07A6`" cannot be encoded.

One thing that looks like one and is not: `jnb acc.6` at `0xAAC6`
(`ec/decompiled/bank0/AAC6.asm:9`) tests bit 6 of **a value the EC read into
the accumulator**, not a bit of the XDATA byte. The disassembly reads
`movx a,@dptr` first. Same instruction mnemonic, different operand space.

## 5. The DSDT: `GC6S` is `0x07A4` bit 2, and is never used

The DSDT does name something two bytes of fan-mode state near `0x07A6`, and the
arithmetic is a trap worth writing out so it cannot recur silently.
`evidence/acpi/dsdt.dsl:52223-52225`:

```
Offset (0x7A4),
    ,   2,
GC6S,   1,
```

An `Offset (n)` is a **bit** index, not a byte. `0x7A4` is bit 15648; the two
reserved bits after it carry the field to bit 15650; `15650 / 8` is byte 1956
= **`0x07A4`, bit 2**. It is not `0x07A6`, and not bit 0 of anything. The
arithmetic is one command:

```sh
python3 -c "print(0x7A4*8+2, '->', hex((0x7A4*8+2)//8), 'bit', (0x7A4*8+2)%8)"
# 15650 -> 0x7a4 bit 2
```

`0x07A6` is one byte from `0x07A4` and the whole issue is about `0x07A6`, which
is exactly the combination that produces a skimming error. **The DSDT declares
no field in `0x07A6` at all** — the next `Offset` after `0x7A4` is `0x7B3`
(`dsdt.dsl:52226`), which steps over it.

`GC6S` itself occurs **once** in the file — the declaration, and nothing else:

```sh
grep -c GC6S evidence/acpi/dsdt.dsl     # 1
```

That is a fact about the *text* of the ASL, not a scan result about the
hardware: the field is declared and the ASL never reads or writes it. So the
honest statement of the DSDT half is two-part — the DSDT names no bit of
`0x07A6`, and the one GC6-named field it does declare is never used.

## 6. The BIOS: no reference found by these searches, over host code

**Not found by these searches, over these files.** Never "the BIOS does not
write it" — `docs/findings.md` §4c is exactly that mistake, retracted in place.

Searched: `bios/decompiled/` (39 `.c`, 38 `.asm`), `bios/ghidra/listings/`
(955 `.asm`), `bios/ifr/` including the 2.4 MB `Setup.en-US.ifr.txt`,
`bios/annotations/`, the five committed `.efi` modules, and the ROM inside
`vendor/bios-1.09/BIOS_1.09.zip`. Patterns `7A6`, `0x7A6`, `1958`,
`0FE4107A6` in both cases, as text *and* as bytes (little- and big-endian,
16- and 32-bit). Every hit classifies as something else: x86 instruction
addresses like `000007A6 … mov RSI, RDX`, a Setup variable pointer
`u_Setup_00001958` (`OemOcDxe.c:316`, `:348`), a Setup question id `0x27A6`,
IFR byte-offset markers, and SHA-256 substrings. **Zero hits for `0xFE4107A6`
anywhere in the component, as text or as bytes.**

**Three qualifications, all of which change what the negative is about.**

*The BIOS contains no EC-window access at all — which is a stronger statement
than the one the plan made.* The only `0xFE41xxxx` appearance in the whole
component is a **magic-word constant** in `write_cfg_magic_word`
(`bios/decompiled/OemHooksPei.c:520-521`, `.asm:742`, `:748`): `0xFE410001` is
loaded into a register and stored into two *module data* dwords (`0xFD882740`,
`0xE00F8098`), and `0xFE410000` is compared against a dword at `0xE00F80A8`.
Nothing reads or writes the physical ECMG window. The repo's own prior note
(`ec/annotations/xdata-0440-readers.md:566-568`) already says this — "a
magic-word compare against `0xFE410001` — base+1".

*The ROM embeds the EC firmware, so a byte scan of it is not a BIOS search.*
`GM7MG7P/GMxMGxxN109A08.ROM` inside the zip contains **35** occurrences of the
8051 encoding `90 07 A6` (`mov DPTR,#0x07A6`), in five 64 KiB regions with seven
each. None of them is host code: the committed `ec/firmware/GMxMGxx_11.800`
occurs **verbatim** in that ROM at offset `0x43CA2C`, and the seven `0x07A6`
sites §3 is built from are that same firmware. So the negative above is
precisely *no reference in host x86 code*, and a reader who byte-scans the ROM
will get 35 hits that are the EC talking to itself. The BIOS's own firmware
copy is not evidence about the BIOS's behaviour; the EC image is.

*Both of the above are about one channel, and the EC has another.*
`docs/findings/bios-ec-io-census.md` is the correction to the wording above,
and it is a correction of scope rather than a retraction of the search: every
pattern named here is a **literal address**, and the EC's index/data channel
never spells one. It is reached over the ACPI EC port pair with four command
bytes — `0xA3` carrying the high byte of an EC RAM address, `0xA2` the low
byte, `0xA4` to read the byte there and `0xA5 <val>` to write it — so a write
to `0x07A6` on that channel carries `0xA6` against a `0x07` base and `0x7A6`
never appears at all. The searches above could not have found such a write
whatever it was, and "the BIOS contains no EC-window access at all" overstates
a negative that was only ever about the `0xFE41xxxx` window.

What that channel does contain is tabulated in
[`bios/annotations/ec-io-writes.csv`](../../bios/annotations/ec-io-writes.csv),
regenerable with `python3 bios/tools/ec_io_census.py --check`. **No row carries
`(0x07, 0xA6)`** — the pair §1 asks about — and that is the whole of what the
census says about it: not found by this census over these listings and these
call sites. The write-up names the rows whose base or index the tool could not
read rather than leaving them out of the table; one of those selects base `0x04`
(`Setup` `0x1B9A0`, no call site for it in the committed listings), so `0x04A6`
is not excluded by the same census — "indexed by `0xA6`" means nothing without
the base, and neither does the negative.

It also names a second boundary, and this is the one to carry here: the channel
has an encoding the tool's site pattern does not match. `OemI2cDevices` reaches
the same `0x66`/`0x62` pair by loading the port into `EDX` and issuing
`out DX, AL` inline, with no `mov DL, <command>` literal anywhere in the
module, so no row names it at all — invisible rather than unresolved. The bytes
it sends are its functions' arguments and nothing in the committed listings
settles them, which is exactly where a write would hide if one existed in that
encoding rather than the tabulated one. So the negative is bounded by that
boundary too, not only by the unresolved rows.

## 7. What this leaves open

- **What clears bit 0.** The EC has one setter, at `0xABC0`, and across all
  seven sites **no clearer and no reader was found**. That leaves the
  2026-09-19 live observation unexplained by anything this scan can see: §4j
  records `0x07A6` reading `0x28` after the owner's BIOS load-defaults where it
  had read `0x29`, i.e. bit 0 cleared by something. **This is a new question
  this work opens, not one it closes**, and it is worth its own issue.
- **What bit 0 *means* to the EC.** The vendor's
  `SetApExist` / `IsOnApLoadFromEc` pair — set on first boot, cleared on
  service uninstall (`MyFanManager.cs:1489-1507`, `:1030`, `:389`) — is the
  best available reading of the semantics, and the `0x0782` bit-1 gate is a
  real fact about the firmware. **Neither is a decode of what the EC wants the
  bit to do.** "The EC sets bit 0 here" is what the evidence supports; "bit 0
  is the AP-present flag" is one step further than it goes, and a static
  instruction sequence is not evidence the EC acts on the bit at all.
- **Bit 7.** No writer in the vendor tree, no site in the EC image. Not found
  by these two methods — not "unused".
- **Re-confirming the live values.** `0x29` (2026-09-18) and `0x28`
  (2026-09-19) are cited from `evidence/ec-watch/`, as prior observations. No
  sweep was re-run; that is a human's job at the machine.

## Where this landed

- `ec/annotations/registers.yaml`, the `OEM_4` entry: `bits:` widened to
  `[0, 1, 2, 3, 4, 5, 6]`, two `sources:` tags added, and a dated paragraph
  appended to `note:` recording the bit map, the `0xABC0` setter with its
  `0x0782` gate, and the "no clearer found" statement. The existing note is not
  edited or reordered — it carries two live observations and the `CORRECTION`
  §4l depends on, and a superseded claim stays visible with its correction
  beside it. `status:` stays `confirmed-working-partially` (bit 0's owner is
  not a behaviour change for the profile bits) and the three `static_refs*`
  counts stay at 7/7/0, which this census reproduces exactly.
- `docs/findings.md` §4j: an additive correction clause beside the sentence
  that says bit 0's owner "was not established". The file is frozen at §97
  (`ec/tools/check_findings_frozen.py`), so this is the form a correction takes
  there rather than a new section.
