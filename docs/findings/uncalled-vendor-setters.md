# The three bytes the uncalled vendor setters write (issue #106)

Eight private setters in `windows/decompiled/v3.1.39.0/` write three EC bytes,
and none of them is called on this board. That much was already in
`windows/vendor-ec-map.md`. What was not settled is the pair of questions a dead
setter raises about the bytes themselves: **does anything else write them, and
does the EC image reference them at all?** This file answers both, per byte,
with the command that reproduces each answer beside it.

**The result in one line: all three bytes have EC-side writers in the image —
so none is `absent` or `unknown-not-absent` and all three warrant
`present-untested` — and for `0x07A5` the bit the EC's direct sites write is
one none of the eight setters touches.** The service's path to these bytes is
dead; the firmware's is not. That is the distinction the issue's question 1
turns on, and the two ends of it had to be measured separately to get there.

**Every figure here is re-derivable from committed inputs with a command named
beside it.** Nothing below is a behavioural claim about hardware, and no live
test ran — there is no laptop and no Windows box reachable from a
GitHub-hosted runner. Where a byte's real behaviour is the open question, it is
left as one.

## The eight setters, and where each one goes

The class that runs on the GM7MG7P is `MyFanManager_RamFan1p5`
(`windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/MyFanCtrl.cs:54`; the
other four branches pick `_NV` at `:50` and `:65`, `_Normal` at `:62` and `_CML`
at `:68`, and the plain `MyFanManager` at `:35`, `:39` and `:42`). Every address
below is the decimal constant in the method body, converted:

| setter | file:line | decimal | byte | bits | mask |
|---|---|---|---|---|---|
| `SetGPUdstate` | `MyFanManager_RamFan1p5.cs:2086` | 1931 | `0x078B` | 0-2 | `0xF8` |
| `SetGPUdstateByGpuMode` | `:2097` | 1931 | `0x078B` | 0-2 | `0xF8` |
| `SetPowerLedStatus` | `:2154` | 1957 | `0x07A5` | 0-1 | `0xFC` |
| `SetFanQuietModeEnable` | `:2181` | 1957 | `0x07A5` | 2 | `0xFB` |
| `SetOverBoostMode` | `:2205` | 1957 | `0x07A5` | 4 | `0xEF` |
| `SetPowerStatus` | `:2218` | 1957 | `0x07A5` | 7 | `0x7F` |
| `SkipOfficeModeSafetyProtect` | `:2322` | 1989 | `0x07C5` | 4 | `0xEF` |
| `SetOverBoostByDynamicTemp` | `:2231` | 1958 | `0x07A6` | 1 | `0xFD` |

Each body is the same read-modify-write: `EcCtrl.Read`, mask the byte, add the
new bit value, `EcCtrl.Write`. The mask is what fixes the bit — the setters
never name a bit, they name a mask.

**`0x07A6` bit 1 is issue #93's and is not claimed here.** It is in the table
because it is the eighth setter the issue counted, and it is listed so the
count reconciles; nothing in this file is evidence about `0x07A6`, whose bit map
and bit-0 owner `docs/findings/oem4-bit-map-and-bit0.md` already holds.

### One polarity trap, in `SetOverBoostByDynamicTemp`

`:2237` reads `b2 = (byte)((!bEnable) ? 2 : 0)`. **Bit 1 is set when the
argument is `false`.** Every other setter in the file sets its bit when its
argument is `true`, so a reader carrying the pattern across will get this one
backwards. It is worth writing down precisely because it is the only setter
whose polarity differs, and because `0x07A6` is shared with three live writers
(`TouchpadToggle_ON/OFF`, `UserSetTouchPadLedStatus`, `MicMuteControl.SetLED`,
`BatteryProtection2`) that the issue does not concern.

## What "never called" survives, and what it does not

**The absence is real, not a decompilation artifact.** The concern with a
`never called` claim is that anti-tamper protection emptied the method bodies
that would have contained the call sites, so the absence would be an artifact of
the extraction rather than a fact about the program. Two checks rule that out
here, and both are greps over the committed tree:

```console
$ grep -rl "Invalid MethodBodyBlock" --include=*.cs windows/decompiled/v3.1.39.0/ | wc -l
0
$ grep -rl "halt_baddata" --include=*.cs windows/decompiled/v3.1.39.0/ | wc -l
0
```

The first is the marker `ilspycmd` leaves when a method body could not be
recovered; the second is Ghidra's spelling of the same condition. Neither
appears anywhere in the tree. This is consistent with
`windows/antitamper/README.md`, which records that v3.1.39.0's bodies were
captured from a running process with 0 invalid method bodies (issue #3). So the
IL here is complete, and a call site that is not in it is a call site the
program does not have.

**Within the class that runs, each setter has one hit — its own definition —
and no call.** Scoped to the file, the counts are:

```console
$ cd windows/decompiled/v3.1.39.0/GCUService/MyControlCenter.MyFan
$ for m in SetFanQuietModeEnable SetOverBoostMode SetPowerLedStatus SetPowerStatus \
           SetOverBoostByDynamicTemp SetGPUdstateByGpuMode SetGPUdstate \
           SkipOfficeModeSafetyProtect; do
    printf '%-30s %s\n' "$m" "$(grep -c "$m" MyFanManager_RamFan1p5.cs)"
  done
SetFanQuietModeEnable          2
SetOverBoostMode               2
SetPowerLedStatus              2
SetPowerStatus                 2
SetOverBoostByDynamicTemp      2
SetGPUdstateByGpuMode          2
SetGPUdstate                   4
SkipOfficeModeSafetyProtect    1
```

`SetGPUdstate` reads 4 because `SetGPUdstateByGpuMode` contains it as a prefix;
its own two hits are the definition at `:2086` and a log label at `:2094`.
**Every count of 2 is a definition plus a log label, not a call** — the second
hit is the method-name string literal passed to `LogCtrl.TraceMessage` inside
the method's own body (`:2094, 2117, 2177, 2190, 2214, 2227, 2240`).
`SkipOfficeModeSafetyProtect` is the one with a single hit in the whole tree,
because it is the only one of the eight with no `TraceMessage` line:

```console
$ grep -rn "SkipOfficeModeSafetyProtect" --include=*.cs windows/decompiled/v3.1.39.0/
.../MyFanManager_RamFan1p5.cs:2322:	private void SkipOfficeModeSafetyProtect(int status)
```

**This corrects a sentence in `vendor-ec-map.md`**, which said "the file's only
reference to each is its definition". That was wrong for seven of the eight.
The conclusion it supported is unaffected — a log label is not a call — but the
sentence as written was falsifiable and false, and a reader checking it would
have found the mismatch and stopped trusting the row.

### The claim is also under-scoped in the other direction

"Never called in this class" is not the same as "never called", and for six of
the eight the distinction is the whole point for a driver author. Those six
**are** called, from two classes this board never instantiates:

| setter | called at |
|---|---|
| `SetPowerLedStatus` | `MyFanManager_QC.cs:846`, `MyFanManager_Intel.cs:1405` |
| `SetGPUdstateByGpuMode` | `MyFanManager_QC.cs:869`, `MyFanManager_Intel.cs:1421` |
| `SetOverBoostMode` | `MyFanManager_QC.cs:888`, `MyFanManager_Intel.cs:1440` |
| `SetOverBoostByDynamicTemp` | `MyFanManager_QC.cs:889`, `MyFanManager_Intel.cs:1441` |
| `SetFanQuietModeEnable` | `MyFanManager_QC.cs:903, 909, 920`, `MyFanManager_Intel.cs:1451, 1465, 1471` |
| `SetPowerStatus` | `MyFanManager_QC.cs:1621`, `MyFanManager_Intel.cs:2149` |

`MyFanCtrl` never constructs `MyFanManager_QC` or `MyFanManager_Intel`
(`MyFanCtrl.cs:50-68`), so on this machine they are other boards' code. **The
vendor ships these features; it ships them on hardware this machine is not.**
That is the difference between "the control center has a fan-quiet mode" and
"the control center has a fan-quiet mode, for the SKU that selects `*_QC`", and
it is worth the sentence because a driver author reading only the first would
build a knob the vendor's own tooling never reaches on this chassis.

**`SetGPUdstate` is the exception and is dead everywhere.** Stripping
definitions and log labels leaves no call site in any class:

```console
$ grep -rn "SetGPUdstate(" --include=*.cs windows/decompiled/v3.1.39.0/ \
    | grep -v "private void" | grep -v TraceMessage | grep -v LogCtrl
```

So `0x078B` bits 0-2 are reachable only through `SetGPUdstateByGpuMode`, and
that only on other boards.

**The three sibling `RamFan1p5` classes are dead too**, which is worth saying
because it is the difference between "the four classes this board can pick from
have one live path" and "every `RamFan1p5` variant has none". `_NV`, `_CML` and
`_Normal` each carry their own copy of the six setters the loop below counts,
and each copy is definition + log label only.
`SkipOfficeModeSafetyProtect` is the exception and is unique to
`MyFanManager_RamFan1p5.cs`, which the section above already establishes:

```console
$ cd windows/decompiled/v3.1.39.0/GCUService/MyControlCenter.MyFan
$ for f in MyFanManager_RamFan1p5_NV.cs MyFanManager_RamFan1p5_CML.cs \
           MyFanManager_RamFan1p5_Normal.cs; do
    printf '%-40s ' "$f"
    for m in SetFanQuietModeEnable SetOverBoostMode SetPowerLedStatus \
             SetPowerStatus SetOverBoostByDynamicTemp SetGPUdstateByGpuMode; do
      printf '%s=%s ' "${m:0:12}" "$(grep -c "$m" "$f")"
    done; echo
  done
```

Every count is 2, and for the same reason as above: a definition and a
`TraceMessage` label. So across the whole `RamFan1p5` family the setters on
`0x07A5`/`0x07A6`/`0x078B`/`0x07C5` are unreachable, and the only place in
the tree where they run is the two classes for other platforms.

## The EC reference counts, and the per-image split

The issue's question 2 asks for a count from `scan_refs.py`. It is the count
that carries the caveat every entry in `registers.yaml` inherits, so it is
worth stating the caveat *with* the number rather than beside it: the 256 KiB
dump holds **two** 8051 programs, and a site in the ITE8850-PD image is a
reference to a different program's XDATA, not to an EC register.

```console
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x07A5 0x078B 0x07C5
0x07A5  refs=5     ec=5     pd=0     referenced   in_data_region=0   0x07A5
0x078B  refs=3     ec=3     pd=0     referenced   in_data_region=0   0x078B
0x07C5  refs=10    ec=10    pd=0     referenced   in_data_region=0   0x07C5
```

**All three counts are wholly main-EC.** That is the fact that decides the
status, and it is worth being exact about what it does and does not license:
`ec/tools/check_status_vocabulary.py` rule 2 requires
`static_refs_main_ec >= 1` before a byte may be graded `present-untested`,
because that grade's entire warrant is a reference count, and `0x07CC` once
carried it with six sites and none of them EC-side. These three have real
EC-side sites, so `present-untested` is available — **and it is the ceiling.**
None of the three is `absent`, and none is `unknown-not-absent`: both of those
grades are for bytes this scan cannot reach, and these are bytes it reaches
five, three and ten times.

A different tool gives different numbers for the same bytes, and the difference
is definitional rather than a disagreement. `scan_refs.py` counts direct
`MOV DPTR,#addr` operands — one per site. `ec/annotations/xdata-registers.csv`
counts accesses rather than sites, so a read-modify-write contributes two
references where `scan_refs.py` counts the single `mov dptr` that sets DPTR, and
it also carries sites that hand DPTR to a subroutine or take the address:

| byte | `scan_refs.py` | census `refs` | split |
|---|---|---|---|
| `0x07A5` | 5 | 8 | 5 read, 3 read+write |
| `0x078B` | 3 | 6 | 5 read, 1 write |
| `0x07C5` | 10 | 23 | 15 read, 6 read+write, 2 address-taken |

Quoting the first without the second would understate what the tree holds, and
quoting the second without the first would break `check_register_counts.py`,
which recomputes the `static_refs*` columns from the image.

Per site, with the instruction that follows each `mov dptr`, from
`trace_xdata_refs.py` — the tool that answers "which image, which address, and
does it read, write or pass DPTR on":

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07A5 0x078B
```

```text
0x07A5: 5 direct MOV DPTR site(s)  bank0=5
  0x8812  read x1, write x1   mov dptr,#0x07a5 / movx a,@dptr / orl a,#0x08 / movx @dptr,a
  0x882C  read x1, write x1   mov dptr,#0x07a5 / movx a,@dptr / anl a,#0xf7 / movx @dptr,a
  0x8840  read x1             mov dptr,#0x07a5 / movx a,@dptr / jnb acc.3,+0x04
  0x8851  read x1             mov dptr,#0x07a5 / movx a,@dptr
  0x8873  read x1, write x1   mov dptr,#0x07a5 / ...

0x078B: 3 direct MOV DPTR site(s)  bank0=2  bank1=1
  0x96DE  read x1   mov dptr,#0x078b / movx a,@dptr / setb c / subb a,#0x00
  0xA83F  write x1  mov dptr,#0x078b / movx @dptr,a / ret
  0xA93B  read x1   mov dptr,#0x078b / movx a,@dptr / dec a / mov r1,a
```

**Read-modify-write on `0x07A5` and a plain store on `0x078B`.** That is worth
saying on its own: the EC does not merely look at these bytes, it writes them,
and on `0x078B` the single `movx @dptr,a` at bank0 `0xA83F` is a bare store
with no read behind it. A write being present in the image is still not
evidence the EC *acts* on the value — that is the standing rule, and nothing
below upgrades a store into a behaviour.

## The DSDT names neither byte, and the way it does not is worth being precise about

`evidence/acpi/dsdt.dsl` declares `OperationRegion (ECMG, SystemMemory,
0xFE410000, 0x00010000)` at `:52193` and walks it as a `Field` list from
`:52194`. In ASL a field's width is in **bits**, so `CTWA, 8` is one byte, not
eight. That is the reading that decides both addresses, and getting it wrong
inverts the answer:

- **`0x07A5`** — the list gives `Offset (0x7A4)` two unnamed bits, then
  `GC6S, 1` (`:52223-52225`), then steps to `Offset (0x7B3)` (`:52226`). So
  `GC6S` is **bit 2 of `0x07A4`**, which `registers.yaml` already records, and
  `0x07A5` sits in the unnamed gap `0x07A5`-`0x07B2`. It carries no ASL field
  name.
- **`0x078B`** — the list gives `Offset (0x788)`, `CTWA, 8` (`:52221-52222`),
  then steps straight to `Offset (0x7A4)` (`:52223`). `CTWA` is **byte
  `0x0788`**, and bytes `0x0789`-`0x07A3` are an unnamed gap. `0x078B` is in
  that gap, not inside `CTWA`.

The sweep's own census records the ASL reference counts, and they are the
check on the reading:

```console
$ grep -E "0x0788|0x07A4,2|0x07C5,5" ec/annotations/dsdt-ecmg-fields.csv
ECMG,0x0788,0,8,CTWA,52222,4,4,0,CTWA,present-untested,4,50662 50663 50670 52787
ECMG,0x07A4,2,1,GC6S,52225,4,4,0,GC6S,present-untested,0,not-referenced-by-this-method
ECMG,0x07C5,5,1,WHMS,52245,10,10,0,WHMS,present-untested,2,50727 52817
```

**The four `CTWA` references are all to byte `0x0788` and not to `0x078B`**,
which is what makes the "unnamed gap" reading load-bearing rather than
incidental. One of the four is a *write* —
`^^PCI0.LPCB.EC0.CTWA = Arg1` at `:50662` — and the other three read the byte
into `UOCT` scaled by `0x08` (`:50663`, `:50670`, and again in the EC query
method `_Q83` at `:52787`). So the DSDT is actively read-write on `0x0788`,
two bytes below where the question was asked. Reading `0x0788`'s references as
evidence about `0x078B` would be the mistake this section exists to prevent.

**How this is stated matters more than usual, so it is stated narrowly:** over
this file, by this method, the DSDT names no field at `0x07A5` or `0x078B` and
no ASL statement references either byte by name. **That is not "the DSDT never
writes them."** An unnamed byte inside a region ASL can still address
numerically, and the sweep finds named-field references; it does not prove the
absence of an addressing route this search did not take. `ECMG` is walked as a
plain `Field` list and carries no `Create*Field` call anywhere in the `EC0`
device body, so the named-field sweep is reading the only field declaration
there; the `CreateBitField (BUF0, 0x0C48, ECRW)` at `:4437` is a PCI-config
scratch buffer in `Device (PCI0)`, unrelated to ECMG. So there is no second,
wider field declaration hiding here, but
that is the specific thing checked, not a general proof.

`0x07C5` is the one of the three the DSDT does name: `WHMS, 1` at bit 5
(`:52243-52245`), with two ASL references, both reads that publish the bit to
the ACPI notification as `WMEN` (`:50727`, `:52817`). **Neither touches bit 4**,
the bit `SkipOfficeModeSafetyProtect` writes. A byte being ASL-visible does not
make every bit of it reachable from ASL.

## What the EC already does with `0x07A5`, and why that is the calibration this issue needed

The EC's own annotations name a routine for `0x07A5`:
`bank0:0x8749=mode_tick_084c_07a5_09ee`. It is the function the five sites
above sit in, and it drives **bit 3** — clearing it with `anl a,#0xf7` and
setting it with `orl a,#0x08`:

```c
/* ec/decompiled/bank0/8749.c:92-103 */
DAT_EXTMEM_09ee = DAT_EXTMEM_09ee & 0xfe;
DAT_EXTMEM_07a5 = DAT_EXTMEM_07a5 & 0xf7;
...
if ((CPU_TEMP < 0x5f) && (GPU_TEMP < 0x57)) {
  if ((CPU_TEMP < 0x51) && (GPU_TEMP < 0x51)) {
    DAT_EXTMEM_07a5 = DAT_EXTMEM_07a5 & 0xf7;
  }
}
else {
  DAT_EXTMEM_07a5 = DAT_EXTMEM_07a5 | 8;
}
```

**And the bits are disjoint: the EC uses bit 3, the eight setters use 0-1, 2,
4, 7.** No setter touches the bit the firmware drives, and no direct site the
EC scan finds touches a bit any setter owns.

This is the whole calibration, stated as a concrete case rather than as a
principle. A dead setter in the service is evidence about the setter. Had the
dead setters covered bit 3, the natural but wrong reading would have been "the
byte is untouched". They do not, and the byte is not untouched. **A reader who
graded these bytes from the Windows side alone would have got the wrong answer
in the direction that matters** — not by overclaiming a live control, but by
under-counting a bit the EC is actively driving.

The same holds for `0x078B`, whose three sites are `bank0:0x96AD`
(`apply_oem_overrides_then_fill_08xx`, which stores `0x078B - 1` into `0x08BB`
on the non-zero path at `96AD.c:48-49`), `bank0:0xA7C8` (the bare store) and
`bank1:0xA916` (`clamp_078b_level_into_0804`, which reads and decrements it).
None of those is a bit-0-2 GPU D-state writer, so the byte's firmware use and
the service's intent do not visibly meet — which is a question, not a conflict.

**What none of this establishes: what the EC *acts* on.** `mode_tick_084c_07a5_09ee`
reads as "drive bit 3 from CPU/GPU temperature", and the thresholds are right
there in the bytes, but a read-modify-write in a static listing is not a
behavioural observation, and bit 3 is graded `present-untested` like every other
unexercised byte in `registers.yaml`. Whether the EC's choice of bit 3 and the
service's absence of a setter for bit 3 are connected is **not** something this
file claims, and it is the most interesting question the sweep opens.

## What was not checked, and is not claimed

1. **The BIOS half of "does something else write it".** `UEFIExtract` and
   `ifrextractor` are available and a BIOS image is committed, but sweeping it
   for three addresses with no DSDT field name to chase is its own piece of work
   with its own evidence file. **Not checked** — which is not "no writer".
2. **No live test, and none is needed to close this.** There is no laptop and no
   Windows box on this runner. `present-untested`'s warrant is a reference count,
   the same warrant `0x07C5` and `0x074C` carry, so no hardware-test document
   was written and none should be: re-preparing finished preparation is not
   progress.
3. **`0x07A6` bit 1** belongs to issue #93, per the issue's own instruction.
   It appears in the tables above only to reconcile the count of eight.
4. **The indirect-addressing blind spot is not excluded**, in either direction.
   `ec/tools/find_indirect_xdata.py` finds 44 `movx @Ri` sites in the EC image
   and resolves none of them to an address, so a writer reaching these bytes
   through a computed DPTR is outside what any count here can see. The three
   counts are non-zero, so this does not threaten the statuses — but it does
   mean "five sites" is "five sites this method finds", not a total.
5. **Nothing upstream.** No issue or PR was opened outside this repository, and
   none will be: issue #10 tracks the eventual `Wer-Wolf/uniwill-laptop` /
   `tuxedo-drivers` contribution and a human submits it.

## Where this landed

- **`ec/annotations/registers.yaml`** gains `XDATA_07A5` and `XDATA_078B` at
  `present-untested`, each carrying the count split and the uncalled-setter
  note, and the existing `WHMS` (`0x07C5`) note gains the bit-4 setter. All
  three carry the full `static_refs` / `static_refs_main_ec` /
  `static_refs_pd_image` triple, which is what
  `ec/tools/check_register_counts.py` recomputes.
- **`windows/vendor-ec-map.md`** has the three corrections in place: the seven
  log labels the old sentence denied, the six setters that are live in
  `*_QC`/`*_Intel`, and the bit-3 disjointness.
- **The four generated artifacts** — `ec/annotations/site-resolution.csv`,
  `ec/ghidra/xdata-symbols.csv`, `ec/annotations/xdata-registers.csv`,
  `ec/annotations/xdata-clusters.csv` — are regenerated by their own tools, not
  edited. The first is what `check_status_vocabulary.py` rule 3 reads, and it
  gained eight rows (three for `0x078B`, five for `0x07A5`), each resolving to a
  direction.
- **`ORACLE["named_in_tree"]` in `ec/tools/xdata_register_map.py` moves**, and
  that pin is the one figure in this change every merge has to
  edit, which is the shape CLAUDE.md warns about. The arithmetic is the same as
  every block above it: both new ones reached by exported functions and
  `NOT_IN_TREE` unchanged at 27. On the branch's own tree that was 214 named
  addresses and 214 − 27 = 187, re-derived with `--self-test` rather than taken
  from the plan, which is what that comment block asks for at the 182 step; the
  failure named `0x07A5` and `0x078B` and nothing else.
  **On the merged tree it is 216 − 27 = 189, and neither side's 187 is right
  here.** Issue #1425 added `PACK_TEMP_DK` over `0x04A2`/`0x04A3` from the same
  185 this one did, so this is the second time two branches have written their
  own `185 → 187` for two names each from one parent. `NOT_IN_TREE` is still 27
  because all four addresses are reached by exported functions, so the merged
  count is 185 + 4 = 189. Both comment blocks are kept in the tool, and a third
  records why their other halves do not stack: #1425's re-export renamed five
  addresses in `ec/decompiled/` and so moved the census pins, while this
  branch's two names reach the symbol table without a re-export and keep the
  `DAT_EXTMEM` spelling in the committed decompile. Only `named_in_tree` moves
  for this one, which is the distinction the 0x086C block above the pair draws.
