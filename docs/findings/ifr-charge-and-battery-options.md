# The charge and battery questions in the Setup IFR, and what hides them

**2026-09-26, issue #95.** The Setup IFR was already committed as
`bios/ifr/Setup.en-US.ifr.txt`; this is the map of it that the issue actually
wanted, plus the answer to its second question about the other form-sets.

**Nothing here is an observation of the running machine.** Every row is a
static reading of `vendor/bios-1.09/BIOS_1.09.zip` as ifrextractor 1.6.1 parsed
it. `Setup`, `CpuSetup`, `PchSetup`, `SaSetup` and `SetupVolatileData` are
boot-services-only on this board (`docs/findings.md` §6,
`evidence/uefi/2026-09-19-variable-list.txt`), so no value in any row below has
been read back from the hardware, no variable was written, and nothing here says
what this machine's menu displays. Reading or changing one is a human's step at
the physical machine, and it is issue #86's.

The machine-derived table is `bios/ifr/charge-questions.csv`; the tool that
derives it is `bios/tools/ifr_census.py`; the commands and the provenance of
each dump are in `bios/ifr/README.md`.

## Six questions carry charge or battery meaning

Every offset below is the one `grep -n` prints, so a reviewer can confirm a row
without running anything. The tool's own output is the authority:

```
$ grep -n 'QuestionId: 0x2A6, VarStoreId' bios/ifr/Setup.en-US.ifr.txt
5953:0x37020: 			OneOf Prompt: "Charging Method", Help: "Select charging method as Normal Charging or Fast Charging.", QuestionFlags: 0x10, QuestionId: 0x2A6, VarStoreId: 0x1, VarOffset: 0x4F3, Flags: 0x10, Size: 8, Min: 0x0, Max: 0x1, Step: 0x0 { 05 91 B5 15 B6 15 A6 02 01 00 F3 04 10 10 00 01 00 }
```

| question | Qid | store | offset | IFR default | hidden? |
|---|---|---|---|---|---|
| Charging Method | `0x2A6` | `Setup` | **`0x4F3`** | `Normal Charging` (0) | **suppressed** unless `NOT(0xE17==1) AND NOT(0xE17==5)` |
| Charger participant | `0x24D` | `Setup` | **`0x3D2`** | `Disabled` (0) | suppressed when `0x229 == 0` |
| Battery Participant | `0x250` | `Setup` | **`0x65D`** | `Disabled` (0) | suppressed when `0x229 == 0` |
| Intel Dynamic Tuning Battery Sampling Period | `0x251` | `Setup` | **`0x3D4`** | 0, 16-bit | suppressed when `0x250 == 0`, and when `0x229 == 0` |
| AC Brick Capacity | `0x127` | `CpuSetup` | **`0xC3`** | `90W AC Brick` (1); 65W (2), 75W (3) | suppressed when `0x126 == 0` |
| Light Bar Effect | `0x29E9` | `Setup` | **`0x740`** | 13 (`Devour`) | suppressed when `0xECB == 0` |

The three varstores, from the `VarStore` lines at the top of the dump:
`Setup` = `EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9`, 0x7D8 bytes; `CpuSetup` =
`B08F97FF-E6E8-4193-A997-5E9E9B0ADB32`, 0x2BB; `SetupVolatileData` =
`EC87D643-…`, 0x97. All three are in the CSV row by row.

Four of the six rows are gated on something a user could actually reach, and
two are not. That difference is the most useful thing in the table.

- **`0x229` is `Intel(R) Dynamic Tuning`** — a visible `OneOf` at
  `Setup[0x3A8]` (`:5415`), "Enable/Disable Intel(R) Dynamic Tuning". The
  charger participant, the battery participant and the sampling period are all
  inside that switch. The sampling period additionally disappears when the
  battery participant does, so it is two gates deep.
- **`0x126` is `EC Turbo Control Mode`** — a visible `OneOf` at
  `CpuSetup[0xC2]` (`:3360`). The AC brick capacity is inside it.
- **`0xE17` and `0xECB` are not reachable at all.** Both are hidden numerics
  with an empty prompt and an empty help, the shape §8 already relies on for
  flags the BIOS exposes to its own conditions. `0xE17` is 8-bit at
  `SetupVolatileData[0x4]` (`:26937`); `0xECB` is 8-bit at `Setup[0x741]`
  (`:27297`).

**`0xE17` is the one that makes this table worth having.** All six rows are
suppressed, so what separates `Charging Method` is *which* byte gates it: it is
the only one of the six gated on a byte of a *volatile* store — the other five
gates are in `Setup` or `CpuSetup` — and it is shown unless that boot-populated
byte holds 1 or 5. `0xE17` is compared against exactly the values 1, 2, 3, 4
and 5, in 39 conditions across the dump (12 against 4, 8 against 2, 8 against
1, 7 against 5, 4 against 3) — so it reads as a five-valued platform-type
selector rather than anything about charging, and `DeepSx Power Policies` is
gated on the same byte three lines into its own option list. It has no `Default`
statement at all: its block is the question and an `End` (`:26937-26938`).
Whatever sets it is a PEI-or-early-DXE platform probe, and the IFR does not say
which. `docs/findings.md` §8 already located the vendor mechanism that writes a
*non-volatile* setup byte from a runtime variable at boot; this is a different
byte, in a different store, with no located writer.

**This is a reading of the condition tree, not a statement about the menu.**
`Charging Method`'s condition is a flat stream evaluated on a stack, not a tree:
`EqIdVal(0xE17==1)`, `Not`, `EqIdVal(0xE17==5)`, `Not`, `And`, which leaves
`NOT(0xE17==1) AND NOT(0xE17==5)`. Reading it by indentation instead — which is
the obvious thing to do with this format — puts the two `Not`s and the `And` at
the same depth and gets a different expression. The tool evaluates the stream
and the suite pins the result, because this is the kind of parse that is wrong
in a way nothing else notices. Every condition in the eight-row census resolved
in full; the tool prints the count of any that did not, and it is zero.

## The `Default` column is the IFR's default, not this board's

The table's defaults come from the `Default` statement (DefaultId 0x0 normal,
0x1 manufacturing) or, for a `OneOf` that states it there instead, from the
`OneOfOption` flagged `Default`/`MfgDefault`. That is a statement about the
IFR.

The ROM's factory values are a different thing: an NVAR `StdDefaults` store,
which UEFIExtract dumps under `…/NVRAM external defaults/…/StdDefaults/<n>
<Name>/body.bin` and which is deliberately **not committed**
(`bios/README.md`, "Default values"). Nothing in `ifr_census.py` or in the CSV
reads it, and no column here says what this machine currently holds. §8 used the
two together once, for `CpuSetup[0x1B7]`, and found they agreed; that was one
comparison, not a rule, and this table keeps them apart.

## Matched the vocabulary, and is not a charge option

Two more rows match the phrase list and are carried in the CSV with the verdict
`matched-not-a-charge-option` rather than dropped. A match that vanishes
silently is indistinguishable from a question the list never saw, and both of
these are the kind of row a reader would otherwise have to re-derive to believe
the table is complete.

- **`Boot performance mode`** (`0xFA`, `CpuSetup[0x0E]`) matches on the option
  label `Max Battery`, one of three performance states the firmware picks at
  reset. It is a label, not a charge control.
- **`DeepSx Power Policies`** (`0x705`, `PchSetup[0x4]`) matches on the option
  `Enabled in S4-S5/Battery`. It is a deep-sleep policy for the S4-S5 states.
  This row is **not in the issue's plan**, which expected six charge questions
  and one carried-but-not-counted; the phrase list finds eight, and this is the
  one the plan did not name. It is a sleep policy that mentions battery power,
  so it is in the second group, but recording it is what makes the first group's
  count trustworthy.

## What the vocabulary has to keep out, and how that is auditable

The issue's word "or similar" is a committed list rather than a judgement call.
`CHARGE_TERMS` in `ifr_census.py` is
`("battery", "charg", "flexicharge", "ac brick", "ac power")`, matched against
three fields — prompt, help, and each `OneOfOption` label — with the term and
the field recorded per row in the CSV. All three fields are needed:
`Light Bar Effect` is recognisable only from its help ("If remove AC power, USB
light Bar will be disabled", `:117`) and `Boot performance mode` only from an
option value.

A bare `ac` is not usable. `grep -i ac` over the dump returns thousands of
lines, most of them the hex byte pair `AC` inside a `OneOfOption`'s byte block
(`09 07 AC 1A 00 00 20`) — which is also why the matcher reads the label and
never the byte block — plus `AC Loadline` / `DC Loadline` (VR settings),
`AC termination` / `ACT` (SerDes), `ACPI` thermal trip points, `RAPL PL 1
Power`, `Energy Efficient Turbo` and `Intel Speed Optimizer`. `AC Brick
Capacity` and `AC Power` are two-word phrases precisely so that a `Charge
Method` row can be found without taking in the rest.

`--list-excluded` prints the **521** questions a looser probe (`ac`, `pow`,
`adapter`, `batter`, `charg`) would have caught and this list declined, with
which probe term hit which field, so the exclusion is a decision a reader can
overturn rather than a silence:

```
$ python3 bios/tools/ifr_census.py --list-excluded | head -6
521 question(s) trip 'ac' / 'pow' / 'adapter' / 'batter' / 'charg' and none of battery / charg / flexicharge / ac brick / ac power.
  0x2A2B  Operating Mode                               'pow' in help
  0x2A2C  Operating Mode                               'pow' in help
  0x2A2F  Light Effect                                 'pow' in help
  0x2A2D  Light Effect                                 'pow' in help
  0x2A2E  Light Effect                                 'pow' in help
```

The three the issue named are all in that list: `AC Loadline` (`:4386` and
three more), `ACPI Debug` (`:1722`), and `PEP SATA` (`:1862`), whose
`Adapter D0/F1` and `Adapter D3` are *option labels* rather than its prompt —
so that one is only visible to a matcher that reads option labels at all.

## `UniWillVariable`: not found in any form-set here

`UniWillVariable`, GUID `{9f33f85c-13ca-4fd1-9c4a-96217722c593}`, appears
**zero** times in `Setup.en-US.ifr.txt`, and no `VarStore` line in it declares
that name or that GUID. No `HiiAddPackage` appears in any of the 39 committed
decompiles either.

Method, so the negative can be re-run: a case-insensitive substring search for
`UniWillVariable` and for `9f33f85c` over all twelve dumps in `bios/ifr/`, and
a case-insensitive search for `HiiAddPackage` over `bios/decompiled/*.c` and
`*.asm`. This is **not found by this method** — a search of those twelve dumps
and a symbol-level search of the decompiles this repository holds. It is not a
claim about every module in the ROM, and it is not a claim that no form-set
anywhere references the variable.

The positive half is §8's and is not re-derived here: `OemOcDxe` copies
`UniWillVariable[0x33]` into `Setup[0x7D7]` at boot, which is how a runtime
variable gates a boot-services-only one. **That consumer is DXE code, not a
form-set.** A form-set that could not see the byte would not need the copy, so
the copy is evidence for this reading rather than against it.

## The other form-sets: eleven more, and none of them charges

`Setup` is not the only module in this ROM carrying an IFR. The sweep, the
method and the two modules that needed extra work are in
`bios/ifr/README.md`; the result is **twelve form-sets in twelve modules**, all
committed:

`Setup`, `FboGroupForm`, `HddAcousticDynamicSetup`, `HttpBootDxe`, `Ip4Dxe`,
`NvmeDynamicSetup`, `PciDynamicSetup`, `PciOutOfResourceSetupPage`,
`ReFlash`, `VlanConfigDxe`, `RaidDriver` (Intel Rapid Storage), and
`6B237146-C179-4B5D-A52F-641BC0DFCACD` (Realtek Ethernet Controller, a
GUID-named FFS with no module name to use).

**`AMITSE` and `AMITSESetupData` carry no HII package.** Both are compressed,
so their image is not readable until UEFIExtract has decompressed it;
`ifrextractor` was run on every nested body of both and neither produced any
output. That is the issue's specific `AMITSE` question answered, scoped: *not
found by this method, on this ROM, by this ifrextractor*.

**None of the eleven adds a charge or battery question.** Running
`ifr_census.py --ifr` over each of the other eleven dumps reports `0 matched` on
every one of them, and that is the result the charge map rests on: not one adds
a row to the census. A `grep -ril pow` over the twelve does turn up two strings
outside `Setup` — `ReFlash`'s "DO NOT TURN THE POWER OFF !!!" (`:20`) and
`PciOutOfResourceSetupPage`'s "It is strongly recommended to Power Off the
system" (`:22`) — but `pow` is the near-miss probe, not a `CHARGE_TERMS` entry,
and both are `Subtitle` statements rather than questions. A `Subtitle` carries
no `VarStoreId`/`VarOffset`, so the census never considers one. The charge map
is `Setup`'s alone, which is the answer the issue's first bullet needed and the
reason the other eleven dumps are a completeness result rather than new charge
findings.

**The method that does not work, recorded so nobody repeats it.** Handing
`ifrextractor` every `body.bin` in the dump — 2,813 of them — looks more
thorough and is not. Two of those bodies are the DXE firmware volume and the
volume containing it; `ifrextractor` scans a multi-megabyte blob for package
signatures and emits a slice per hit, which came to **342** outputs, every one
a different digest, with form-set titles and `VarStore` names belonging to
different modules than the address ranges around them. One slice carries the
title *"Built-in EFI Shell"* over a `HTTP_BOOT_CONFIG_IFR_NVDATA` store. None
of the 342 is a form-set a firmware would show, and the twelve real ones are all
found by handing the tool one module at a time.

## New questions this opens

- **Who writes `SetupVolatileData[0x4]`?** It is the only thing standing
  between a user and the `Charging Method` question, it is compared against
  five values in 39 conditions, and it has no located writer. The same question
  for `Setup[0x741]` (`0xECB`), which gates the light bar. Both are PEI-or-early-DXE
  platform probes by the look of them, and neither is in `bios/ghidra/load-map.csv`'s
  38 decompiled modules unless it happens to be one of them.
- **Does anything read `Setup[0x4F3]`?** The IFR says the question exists and
  says when it is visible. It does not say what the firmware does with the byte.
  That is a charge trace, not an IFR reading.
- **`UniWillVariable`'s battery bytes 0x30-0x32.** §6 records
  `BatteryLimitation`, `ChargeMaximumLimit` and `ChargeMinimumLimit` there,
  read 0 after load-defaults, and §8 records that `OemOcDxe` does not touch
  them. Now there is a `Setup` byte that means "fast charging" and a
  `CpuSetup` byte that means "which AC brick", and no located code connects
  either to that runtime variable. A pre-boot read of `UniWillVariable[0x30-0x32]`
  next to a charge trace would be the test.

## Left out on purpose

- **Reading or writing any setup variable live, and the UEFI-shell procedure
  for it.** Issue #86's step, and a human's, at the physical machine. No
  sentence above states or implies a live read happened.
- **Whether `Setup[0x4F3]`, `Setup[0x3D2]`, `Setup[0x65D]` or `CpuSetup[0xC3]`
  changes anything on this board.** That needs a charge trace, not an IFR. The
  natural follow-up is a documented UEFI-shell read of these offsets,
  prepared but not run.
- **Committing the ROM's NVAR `StdDefaults` store.** Deliberately not committed
  (`bios/README.md`); adding it is a separate decision with a separate size
  argument, and this table does not need it.
- **A census of all 3,659 store questions.** The tool can emit one to a scratch
  path — `--ifr` with `--match` and `--offset` is the lookup — but committing a
  large derived file whose value is a lookup rather than a review is the wrong
  trade. The committed artefact is the filtered census.
- **Wiring `ifr_census.py --check` into `.github/scripts/agent-gates.sh`.** That
  list is explicit, and `.github/` is copied from `ElDavoo/agent-pipeline`
  rather than edited here, so a branch that touches it fails at the end rather
  than the start. The prepared gate change is one line, in the same shape as
  `docs/ci/agent-gates-*.patch`, and is left for a human.
- **Extending `bios/tools/bios_extract.py` to regenerate the other eleven
  dumps.** The script's own `ifr()` covers `Setup`; the other eleven came from
  the same command written down in `bios/ifr/README.md`, and a second mode on a
  shared file with open PRs against it is the change CLAUDE.md rules out.
- **Any upstream pull request** (`Wer-Wolf/uniwill-laptop`, `tuxedo-drivers`,
  issue #10). This work ends in a doc and a CSV in this repository, so there is
  no patch to submit.
- **The EC-side charge work** (§4l, §4m, §4n). The IFR is a different layer, and
  nothing here changes an EC register's `status:`; `ec/annotations/registers.yaml`
  and `bios/annotations/ghidra-functions.csv` are not opened.
