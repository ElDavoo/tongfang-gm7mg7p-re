# `0x0786` and `0x078E` are two unrelated bytes: a seven-bit TCC offset and a set-only capability byte

(Issue #1248. Static reading of the committed firmware
`ec/firmware/GMxMGxx_11.800` plus the committed decompilations under
`ec/decompiled/` and `windows/decompiled/`. No laptop, no EC and no Windows
machine is involved: every address below is re-derivable from those files with
the commands in §7, and nothing here is a live test of either byte.)

## The claim

**`0x0786` and `0x078E` are not one structure. They are eight bytes apart, in
different span groups, reached by disjoint function sets, and read for entirely
different reasons — one as a value the EC masks to seven bits and stores, the
other as a byte the EC only ever ORs bits into.**

The issue was handed a sharper disagreement than the tree supports, and
correcting it dissolves most of the tension. Three things in it do not survive
a `grep`:

1. **The five-entry curve belongs to `0x0786`, not `0x078E`.** Upstream
   attaches `FAN_CURVE_LENGTH 5` to `EC_ADDR_FAN_DEFAULT`, and
   `EC_ADDR_FAN_DEFAULT` is `0x0786`. `0x078E` is spelled as three independent
   bits (`upstream-excerpt.txt`, quoting `uniwill-acpi.c:254-268`):

   ```c
   254: #define EC_ADDR_FAN_DEFAULT		0x0786
   255: #define FAN_CURVE_LENGTH		5
   ...
   265: #define EC_ADDR_FAN_CTRL		0x078E
   266: #define FAN3P5				BIT(1)
   267: #define CHARGING_PROFILE		BIT(3)
   268: #define UNIVERSAL_FAN_CTRL		BIT(6)
   ```

   So "upstream calls `0x078E` a curve with five entries" is not what upstream
   says. `0x078E` is a flag byte in upstream's own spelling, and the curve is
   the *other* address's claim.

2. **The EC corroborates `CHARGING_PROFILE` exactly, and sets three more bits
   beside it.** `B12C` does `mov dptr,#0x078e / orl a,#0x08` — bit 3, the bit
   upstream names `CHARGING_PROFILE`. `A7C8` ORs in `0x04`, `0x40` and `0x20`
   against the same byte. §3 has the listing. The EC sets four bits across the
   two routines and never stores a cleared one, which is a capability byte's
   behaviour and not a value's.

3. **The class that runs on this board calls `0x0786` a TCC offset.** The
   conflicting PWM-curve name comes from code in classes this machine does not
   run. §5 has the reach argument.

Both bytes keep `present-untested`. §6 is what that costs and why nothing here
moves either one.

## 1. The two addresses side by side

From `ec/annotations/xdata-registers.csv`, which is what
`xdata_register_map.py` generates from the committed tree:

| | `0x0786` | `0x078E` |
|---|---|---|
| census row | `670` | `675` |
| `spelled_as` | `symbol` (`CPU_TCC_OFFSET`) | `DAT_EXTMEM` |
| span group | `0x077E-0x0788` | `0x078E-0x078E` |
| functions touched | `0x9334`, `0x93FE`, `0x93FF`, `0x948D`, `0xACB4`, `0xCC64` | `0xA7C8`, `0xB12C` |
| direct `MOV DPTR` sites | four | two |

**No function in the first list appears in the second, and the two span groups
do not overlap.** The addresses between them are not part of either structure:
of the seven in `0x0787`-`0x078D`, `registers.yaml` names `0x0788` (`CTWA`),
`0x078B` (`XDATA_078B`) and `0x078C` (`KBD_STATUS`), and leaves the rest. The
census row for `0x078E` had an empty `name` cell until this issue; it is
`XDATA_078E` now.

One thing the census does *not* separate them on, so that it is not read as
evidence: both rows carry the same `cluster_id`, `main-ec-002`, whose
`addr_range` is `0x0456-0x1809`. A cluster that wide is a fact about the
clustering threshold rather than about these two addresses, which is why the
argument above rests on the span groups and the function sets instead.

## 2. `0x0786`: read, masked to seven bits, stored

The EC-side verdict is already written up, and this issue does not re-derive
it: `docs/findings/xdata-0786-tcc-offset-verdict.md` (issue #702) walks all
four sites. What §2 here adds is only the part of it this issue's question
turns on — that the two addresses are not related — so it is one listing:

```
9492     90 07 86 mov      DPTR, #0x786
9495     e0 - -   movx     A, @DPTR
9496     30 e7 11 jnb      0xe7, 0x94aa      ; bit 7 is the enable
9499     90 07 41 mov      DPTR, #0x741
949C     e0 - -   movx     A, @DPTR
949D     30 e0 0a jnb      0xe0, 0x94aa      ; and AP_OEM bit 0 must be set
94A0     90 07 86 mov      DPTR, #0x786
94A3     e0 - -   movx     A, @DPTR
94A4     54 7f -  anl      A, #0x7f
94A6     90 0a 4a mov      DPTR, #0xa4a
94A9     f0 - -   movx     @DPTR, A
```

(`ec/decompiled/bank0/948D.asm`.) The value **replaces** an already-computed
TCC target at `0x0A4A`, and the routine then falls into `0x94AF` with no `ret`
of its own — `store_r7_to_098c_and_0463` writes `0x098C` and `0x0463 | 0x80`.
That is a magnitude being stored into a path, not an index into a curve.

`0x0A4A`, `0x098C` and `0x0463` have **no row in `registers.yaml`**. They are
named here as the consumer chain because the walk needs them, not as
characterised bytes; §6 says what that does and does not block, and adding
three rows for them is a follow-up rather than something this issue smuggles in.

## 3. `0x078E`: four `orl`s, and nothing that stores a cleared bit

Every direct site in the image, from `ec/decompiled/bank0/A7C8.asm` and
`B12C.asm`:

```
A7DB     90 07 8e mov      DPTR, #0x78e
A7DE     e0 - -   movx     A, @DPTR
A7DF     44 04 -  orl      A, #0x4          ; bit 2
A7E1     f0 - -   movx     @DPTR, A
A7E2     e0 - -   movx     A, @DPTR         ; same DPTR, no reload
A7E3     44 40 -  orl      A, #0x40         ; bit 6
A7E5     f0 - -   movx     @DPTR, A
A7E6     e0 - -   movx     A, @DPTR
A7E7     44 20 -  orl      A, #0x20         ; bit 5
A7E9     f0 - -   movx     @DPTR, A
```

```
B12C     90 07 8e mov      DPTR, #0x78e
B12F     e0 - -   movx     A, @DPTR
B130     44 08 -  orl      A, #0x8          ; bit 3
B132     f0 - -   movx     @DPTR, A
```

`A7C8` sets three bits in one pass off a single `DPTR`, and `B12C` sets a
fourth. That is four independent capabilities, and **no store to `0x078E` in
the image is produced by anything but an `orl`** — the two `mov DPTR,#0x78e`
sites are the only ones the scan finds, and at each the value written back is
the accumulator with bits added to it.

Stated about *stores* rather than about instructions, because the distinction
is real: `FUN_CODE_a7c8` does `xrl a,#0x5` at `0xA7F0` with `DPTR` still
holding this address, which decompiles to `return *pbVar3 ^ 5`
(`A7C8.c`). That reads the byte into the function's return value and writes
nothing back, so it is a read rather than the clearing a bare `xrl` scan would
have reported. What the listings support is that nothing here *stores* a
cleared bit; `ec/tools/test_xdata_078e_capability_byte.py` holds that by
walking each site and checking what produced the accumulator at each write-back.

### The masks are the captured value

The union of the four masks is exactly what the 2026-09-23 capture recorded for
this address:

```console
$ grep 078E evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt
0x078E = 0x6C
```

`0x04 | 0x40 | 0x20 | 0x08` is `0x6C`. Bits 2, 3, 5 and 6 set; bits 0, 1, 4
and 7 clear in both the EC's masks and the captured byte.

**That is a shape, not a live test.** It says the byte on this machine is the
one the EC's own ORs describe, which is why this write-up does not treat it as
an open question what kind of byte it is. It does **not** say the EC reads any
bit back, and it is one capture of one power mode. Bit 7 is the useful
counterweight: `WKDColor` reads `0x078E` bit 7 and it is clear, so the vendor
does read bits back that this EC never sets — the set-only shape is a fact
about these four instructions, not a claim that the byte is write-only, and
`A7C8` reading it for a return value is a second thing it does besides
setting it.

### The bit 4 cross-check

Bit 4 is the RGB-lightbar support bit the vendor tests —
`MyRgbLightBarDefault.isSupportRGBLBFromEC` reads `0x078E` and checks
`& 0x10` — and it is **clear**, in the masks and in the capture alike. That
independently agrees with the lightbar verdict in
`docs/findings/dmi-descriptor-evidence.md`, and it is the reason this write-up
reads the byte as capabilities rather than as a mode: a machine's lightbar
support is not a thing it toggles.

## 4. The vendor names it a support byte, twice

`ECSpec.cs` gives `1934` (`0x078E`) two names in the same file:

```csharp
319:		public const ushort ADDR_SINGLEKBL_SUPPORTPOWER = 1934;
351:		public const ushort ADDR_SUPPORT_BYTE6 = 1934;
```

Both are present in every committed `ECSpec.cs` version at the same two lines.
A single-zone keyboard backlight power flag and a generic "support byte 6" are
not two readings of a value; they are one byte that answers two capability
questions, which is what the four `orl`s say from the EC side.

Ten call sites read it, every one a single-byte read, and six distinct bits are
tested across them — bits 2, 3, 4, 5, 6 and 7. **No site writes it.** So in the
Windows stack `0x078E` is a strictly-read capability byte, and the write side
is entirely the EC's.

One caveat on the census, since a reader will hit it: `ec-callsites.csv`
records eight reads of `0x078E`, and there are ten. The tool's `CALL` pattern
requires an explicit receiver (`EcCtrl|MyEcCtrl.Instance|AcpiModel|EcModel`),
so the two unqualified `Read(` calls inside `MyEcCtrl` itself — `isSupportRGBLBFromEC`
and `IsSuportRamFan1p5` — are missed. **Eight is this tool's population, not the
vendor stack's**, and it undercounts rather than overcounts. Fixing the pattern
is a separate change to a shared generated CSV and is named as a follow-up
rather than folded in here.

## 5. `0x0786`'s conflicting name is other platforms' code

The PWM-curve reading of `0x0786` is real and is in the shipped service:
`GetFanTablePWMDefault` reads `1926`-`1930` into an `int[5]` returned as
`DefaultPWM`, which `MyFanManager_QC` then consumes as PWM values.

It does not run on this machine, and what settles that is where the base calls
it from. `GetFanTablePWMDefault` is `private` and defined separately in
`MyFanManager`, `MyFanManager_QC` and `MyFanManager_Intel`. In the base
`MyFanManager` — the class `MyFanManager_RamFan1p5` derives from — the method is
reached from exactly one place: the private `LoadRegistry`
(`MyFanManager.cs:731`), which calls it (`MyFanManager.cs:769`).
`LoadRegistry` in turn has exactly two call sites in that class, and both sit
inside a `virtual` method the derived class overrides:

| `LoadRegistry()` call | Enclosing method in `MyFanManager` | Override in `MyFanManager_RamFan1p5` |
|---|---|---|
| `MyFanManager.cs:112` | `public virtual void EnableByService` | `MyFanManager_RamFan1p5.cs:170` |
| `MyFanManager.cs:335` | `public virtual void Resume` | `MyFanManager_RamFan1p5.cs:466` |

`MyFanManager_RamFan1p5` — the class `windows/vendor-ec-map.md` records as the
one this board selects — overrides both, and contains no `base.` call anywhere
(`grep -c 'base\.'` on it returns 0). Neither override chains to the base, so
neither reaches the base's `LoadRegistry`, so `GetFanTablePWMDefault` never runs
for this class. Its two overrides do their own setup (`LoadProfileAll`, then
`Init`) in place of the base's `LoadRegistry` call.

The privacy of `GetFanTablePWMDefault` is not what does this work, and the
difference is worth stating, because privacy is the obvious thing to reach for
and it does not hold: a `private` member is not inherited at all, so "the
derived class cannot call it" would read the same for a class that *did* chain
to the base — the base's own copy would still run and still read the block. The
derived class also names neither `LoadRegistry` nor `DefaultPWM`, which is
consistent with that but does not decide it either, for the same reason: a
derived class not naming a method says nothing about whether the base's copy of
it runs. What excludes the read here is the override. The same two-step applies
to `LoadRegistry`, itself `private`: the derived class could not have called it
directly either, but that is beside the point, because the route that would
have reached it — the base's `virtual` `EnableByService` and `Resume` — is
exactly the one the overrides replace.

So on this board `0x0786` is **written** by
`MyFanManager_RamFan1p5.SetCpuTccOffset`, which writes `value | 0x80` or `0`,
and **read by nobody** in the service. What the spec class for that same variant
calls it agrees: `RamFan1p5_ECSpec.cs` names `1926`
`ADDR_TimAP_TccOffset_Setting`, against the generic `ECSpec.cs`'s
`ADDR_L1_PWM_DEFAULT_MYFAN3` for the same address.

That does not make the naming conflict go away — it locates it. The five-byte
PWM-default block is a real reading in a real shipped service, and it is not
this machine's. `registers.yaml`'s `0x0786` note carries the correction beside
the paragraph it corrects rather than replacing it, because the paragraph is a
claim about what the service version contains and that is still true.

## 6. What this does not establish

**Both bytes stay `present-untested`.** For `0x0786` that is #702's ceiling and
this issue does not lift it: nothing here is a live observation. For `0x078E`
it is worth saying why the §3 result does not lift it either — the EC sets the
byte and the capture reads it back the same, and **a byte the EC writes and
reads back identically is exactly the case CLAUDE.md rules settles nothing**.
The status moves on a live test of behaviour, not on a matching readback.

**"Two direct sites" means two by these methods.** A store through a
run-time-built DPTR is invisible to `scan_refs.py` and
`trace_xdata_refs.py`, and `find_indirect_xdata.py` resolves none of its
anchored bank0 `movx @Ri` sites in this image. That is a fact about the scan's
form, not about the byte — and it is the reason "only `orl` stores it" above is a
statement about the image as these tools read it.

**What a live test would settle, and it is a human's step.** For `0x078E`:
clear one capability bit this EC sets, confirm the EC re-ORs it on the next
pass it makes through `A7C8` or `B12C`, and watch whether anything downstream
changes. That distinguishes "the EC maintains these bits" from "the EC writes
them once and forgets", which the committed files genuinely cannot say. For
`0x0786` the step is unchanged from #702: write it with bit 7 and `0x0741`
bit 0 both set and read `0x098C` and `0x0463` back.

## 7. Reproducing every line above

```console
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x0786 0x078E
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0786 0x078E --counts-only
$ python3 ec/tools/check_site_resolution.py ec/firmware/GMxMGxx_11.800 --csv | grep ^0x078E
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/gen_xdata_symbols.py --check
$ python3 ec/tools/xdata_register_map.py --check
$ grep -n 'ADDR_SINGLEKBL_SUPPORTPOWER\|ADDR_SUPPORT_BYTE6' \
      windows/decompiled/v3.1.39.0/GCUService/Define/ECSpec.cs
$ grep -rn 'GetFanTablePWMDefault\|DefaultPWM' windows/decompiled/v3.1.39.0/GCUService/
```

§5's reach argument is the two greps below, in this order: the base calls its
`LoadRegistry` only from `virtual` methods the derived class overrides, and the
derived class never chains to the base.

```console
$ grep -n 'LoadRegistry()' \
      windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/MyFanManager.cs
$ grep -c 'base\.' \
      windows/decompiled/v3.1.39.0/GCUService/MyControlCenter.MyFan/MyFanManager_RamFan1p5.cs
```

The byte facts §3 rests on — the two sites, the masks, the set-only stores and
the union — are pinned by `ec/tools/test_xdata_078e_capability_byte.py`, which
the runner finds without registration:

```console
$ python3 -m unittest ec.tools.test_xdata_078e_capability_byte
```

The union check in §3 is arithmetic on the four masks the listings show, and
the capture line is `grep` against `evidence/`. Every listing quoted in §2 and
§3 is the committed `ec/decompiled/bank0/*.asm`, which is machine output;
where a decompiled `.c` disagrees with it, the `.asm` is right.

`gen_findings_index.py` prints the index to stdout rather than writing it, so
regenerating it is a redirect, and `--check` is what fails on a stale one. Its
last line carries the write-up count and is not restated here — that is the
command's output, not a figure a reader should maintain:

```console
$ python3 ec/tools/gen_findings_index.py > docs/findings/INDEX.md
$ python3 ec/tools/gen_findings_index.py --check
```

## Where this is recorded elsewhere

- `ec/annotations/registers.yaml` — the new `XDATA_078E` entry, and a dated
  correction beside the `CPU_TCC_OFFSET (APTC/APTN)` note recording that the
  PWM-default reading is unreachable on this board.
- `ec/annotations/site-resolution.csv` — the two `0x078E` rows
  (`check_status_vocabulary.py` rule 3 requires them for a `present-untested`,
  and it derives its population from `registers.yaml`).
- `windows/vendor-ec-map.md` — already records the class selection §5 rests on.

## What this opens

- The two capability bits this EC sets and upstream does not name (`0x04` and
  `0x20`), and the one upstream name with no vendor test behind it here:
  `FAN3P5` is bit 1, but `MyFanManager.GetMyFan3p5Flag` tests **bit 2** of this
  byte, so upstream and the vendor disagree on which bit the fan-3.5 flag is.
  The other two upstream names both do have a vendor test — `CHARGING_PROFILE`
  bit 3 as `BatteryProtection.BatteryProctionSupport`, which
  `InitializeHealthSwitch` reads by `BitArray[3]` — though `B12C` also clears
  `0x07A6` in the same routine that sets the bit, which is worth a look.
- `ec_callsites.py`'s `CALL` pattern missing unqualified `Read(` calls inside
  `MyEcCtrl`, which undercounts this byte in a committed census.
- `registers.yaml` rows for `0x0A4A`, `0x098C` and `0x0463`, the TCC consumer
  chain — named by #702 and untouched here.

One thing this issue hit that is worth knowing before writing the next suite:
`check_doc_figure_pins.py` reads **every integer inside an asserting call** as a
candidate measurement of some figure in
`docs/findings/xdata-census-rederivation-checklist.md`, from the parse tree
rather than the text. Writing the `mov DPTR,#0x078e` opcode as
`bytes((0x90, 0x07, 0x8E))` therefore put the integer `142` — that page's
PD-image `write` reference count — into an assertion here, and the pin check
reported this suite as a competing measurement of a figure it has nothing to do
with. It is not wrong to do that; the tool is doing what it is for. The fix is
to build the opcode from the address (`DPTR_078E` at the top of the suite)
rather than to weaken the pin, which is why that constant is named and
commented rather than inlined.