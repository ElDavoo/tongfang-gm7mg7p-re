# Subsystems: from mechanism to function (EC firmware `GMxMGxx_11.800`)

A map from each mechanism this firmware actually has to the named functions that
establish it, over a measured statement of how much of the image those
mechanisms account for. It is written against the committed export on
2026-09-24: `ec/decompiled/index.csv` for the functions, and
`ghidra-functions.csv` for the names. Every function below is cited as
`` `scope` `address` `name` `` so that `ec/tools/build_ec_decompile.py --check`
can resolve it against the CSV, and every one of those resolutions failing is a
failed check.

**Addresses are `common` unless marked otherwise.** The common area is
`0x0000`-`0x7FFF` of the bank image and both bank programs carry it
identically, so a common-area function is exported once (`ec/annotations/README.md`,
"The format") and its address appears in no bank row. A `bank0` or `bank1` row
is a runtime address in that bank's own `0x8000`-`0xFFFF` window.

**Nothing here was observed on hardware.** No register was read, written or read
back, and no interrupt, fan or charge behaviour was exercised. This is a static
reading of `ec/firmware/GMxMGxx_11.800` and its committed decompilation, which
is the same limit [`pd-index-geometry.md`](pd-index-geometry.md) §"Nothing here
was observed on hardware" states for that document.

**This is a set of established mechanisms plus a measured remainder, not a
partition of the firmware.** §2 is the measurement, and it is the reason the
check below exists: a map that read as complete would be a claim the export does
not support. A complete subsystem map is a large project; this file is its first
measured step, and §11 is the work it did not do.

## 1. Reproducing it

The census in §2, the byte readings behind §3, and the citation check are all
reproducible from the committed tree with no Ghidra and no network:

```
python3 ec/tools/build_ec_decompile.py --check
python3 ec/tools/build_ec_decompile.py --self-test
python3 ec/tools/verify_reassembly.py --check
```

`--check` recounts the four numbers in §2 and resolves every citation in this
document against `ghidra-functions.csv`, which is why a rename in that file has
to reach this one. `--self-test` covers the same pass on synthetic fixtures,
including one document that must survive. `verify_reassembly.py --check` is
what establishes that the `.asm` files the readings come from are byte-exact
against the firmware; it reports 0 disagreements over 45,624 instructions, and
§3 leans on that for the three `reti` questions.

The per-function byte readings are the committed listings, one `.asm` and one
`.c` per address, cited in each row of `ghidra-functions.csv`.

## 2. The coverage census

Measured over the committed export, by `index.csv` for the functions and
`ghidra-functions.csv` for the names:

- `exported functions` — 2710
- `annotated function rows` — 1872
- `rows the index marks annotated` — 1897
- `unresolved rows` — 169

By program, as exported minus annotated minus the rest:

| program | exported | annotated | unannotated |
|---|---|---|---|
| `bank0` | 746 | 693 | 53 (7%) |
| `bank1` | 676 | 605 | 71 (11%) |
| `pd` | 535 | 502 | 33 (6%) |
| `common` | 753 | 97 | 656 (87%) |

**The common area is the finding.** It is 28% of the export by row count and
87% of it is unannotated, and it is where the interrupt vectors, the BL51 stubs
and most of the runtime helpers live. It is also the area this document had to
extend to say anything about interrupt entry, which is what §3 is.

**The three counts disagree, and the difference is measured rather than
smoothed.** `index.csv` marks 1897 rows `annotated=yes` and the CSV holds 1872
rows: a gap of 25. Both sides are enumerated. 25 index rows are marked
`annotated=yes` with no CSV row at all, and no CSV row is recorded by the index
as `annotated=no`; 25 − 0 = 25.

Of the 25, 14 carry a name no CSV row has — `caseD_0` at eleven bank1
addresses, plus `caseD_6`, `caseD_1` and `default` — which is the switch-case
naming Ghidra applies to a `switch` it framed, not an annotation. The other 11
are second copies of a name that does have a CSV row, and each is worth a
sentence of its own because the copy is a fact about the framing:

- `bank0` `0x031C` and `bank0` `0x805B` repeat `poll_d6c2_then_branch` and
  `index_table_default` from `0xD236` and `0x8274`;
- `bank1` `0x031C` and `bank1` `0x703A` repeat `0xD236` and `0xE722`;
- `pd` `0x3497`, `0x998B`, `0x9C1B` and `0x9C4D` all repeat
  `add_full_product_to_dptr` from `pd` `0x10BC`, which is the one address in
  that family that is an entry;
- `pd` `0x0000` repeats `0x0500`;
- and the two in the common area, `0x0512` and `0x1207`, are discussed in §3,
  because both are visible from the bytes and neither is settled.

**That list of 11 is a pinned figure, not the authority.**
`python3 ec/tools/second_copy_census.py --check` derives it: 11 of the 25 are a
body that is nothing but a transfer of control into a function this CSV backs
under the same name (7 `ljmp`/`ajmp`, 4 `lcall`), and 14 are Ghidra's own
`switchD_*` namespace, read from the committed `.c`. `--check` fails on a row it
cannot account for, so a 26th named-without-row function that is neither shape
turns this red rather than quietly extending the list above.
[`docs/findings/named-without-a-row.md`](../../docs/findings/named-without-a-row.md)
has the per-address reading.

The 7 the index records as `annotated=no` are `bank1` `0xF113`, `0xF116`,
`0xF119`, `0xF11C`, `0xF11F` and `0xF123`, and `pd` `0x7059` — all seven seeded
by the annotation layer, so the index's `annotated` column is recording the seed
basis rather than the presence of a name.

> **Correction, 2026-09-25 (#602): the sentence above is wrong, and the seven
> rows it names no longer exist in that state.** `thunk_` is Ghidra's reserved
> prefix for an auto-thunk, so those seven names were invisible to the index
> that had to record them: all seven applied, and all seven were reported
> `annotated=no`. The column was not recording the seed basis — it was reading
> the name, and the name read as Ghidra's. The rows have been renamed into the
> repository's existing convention (`forward_to_*`, and `call_122f` for the one
> forwarder that is a bare `lcall`), they now report `annotated=yes`, and the
> count is 0. `docs/findings/thunk-prefix-collision.md` has the account; the
> naming rule is in `README.md`, and a check now refuses the collision from
> either side.

**152 of the 1848 rows are `type: unresolved`, and 271 carry a name that
describes a shape rather than a job** — `call_` (86), `load_` (115),
`trampoline_` (29), `ret_only_` (21), `nop_` (9), `thunk_` (7), `seed_` (4).
Each is counted on the whole prefix, not a narrower one: 78 of the `load_` rows
are `load_dptr_` and the other 37 are the register and table loads beside them.
`sub_input_from_cpu_temp_043e` is a subtraction step; `trampoline_to_c0a2` is a
jump. Neither is a mechanism, and a map built only from the names would be a map
of the disassembler's vocabulary.

> **Correction, 2026-09-25 (#602): recounted against the committed CSV, and
> every number in the paragraph above is stale — not only the `thunk_` (7) the
> rename removed.** The current figures are 169 `type: unresolved` rows of 1872,
> and 269 names over the same seven prefixes: `call_` (87), `load_` (117),
> `trampoline_` (29), `ret_only_` (21), `nop_` (9), `seed_` (6), of which 80 of
> the `load_` rows are `load_dptr_` and the other 37 are the register and table
> loads beside them. Only two of those moved because of the rename: `thunk_`
> (7) is gone and `call_` gained the one `call_122f`. `load_` 115 → 117,
> `seed_` 4 → 6, 1848 → 1872 and 152 → 169 were **already wrong on `main`** —
> the paragraph was written against an older CSV and nothing recounted it,
> because unlike the four bullets above it is not one of the counts
> `check_subsystems` holds to a recount. The six renamed `forward_to_*` rows are
> a shape census item too and are not in the 269, because `forward_to_` is not
> one of the seven prefixes this document enumerates; they bring that separate
> family to 17.

## 3. Reset and interrupt entry

The table at `0x0000`-`0x002F` is the entry point the issue asks for, and it is
the one group in this firmware whose every slot now carries an annotation row.
One thing it reaches does not: the entry at `0x002B` tail-jumps to `0x05E7`,
which is exported and unannotated, and is read from its bytes below rather than
from a row. `ec/tools/build_ec_decompile.py`'s
`discover_vector_table()` walks it rather than assuming the textbook layout, and
what the walk finds is 12 `ljmp` entries interleaved with 4 lone `ret` bytes.

The six already-named forwarders hold the standard slots:

- `common` `0x0000` `reset_vector_forwarder_to_0070`
- `common` `0x0003` `int0_vector_forwarder_to_052f`
- `common` `0x000B` `timer0_vector_forwarder_to_0530`
- `common` `0x0013` `int1_vector_forwarder_to_0556`
- `common` `0x001B` `timer1_vector_forwarder_to_05b6`
- `common` `0x0023` `serial0_vector_forwarder_to_05e6`

Their six targets, added here:

- `common` `0x0070` `reset_entry_stack_bank0_then_code_init` — sets SP to
  `0xC0`, writes `0x3F` to XDATA `0x1001`, selects bank 0 through `0x110A`,
  calls `0x158E`/`0x0F75`/`0x1594`, copies XDATA `0x2006` to `0x0004`, and
  tail-jumps to `0x00CF`
- `common` `0x0530` `timer0_target_decrements_xdata_0a00` — 38 bytes, the full
  save and restore of A, B, DPH, DPL and PSW, one call to `0x0E5E`, and a
  decrement of XDATA `0x0A00` when it is non-zero
- `common` `0x0556` `int1_target_six_calls_14c8_012f_018c_029b_7110_7177` —
  96 bytes, the same save and restore, six calls and a branch on a byte between
  them
- `common` `0x05B6` `timer1_target_splits_internal_ram_41_on_carry` — 48 bytes,
  the same save and restore, then a test and clear of bit 4 of internal RAM
  `0x41`
- `common` `0x052F` `int0_target_is_one_byte_reti` [unresolved] — one `reti`
  byte, discussed below
- `common` `0x05E6` `serial0_target_is_one_byte_reti` [unresolved] — one `reti`
  byte, discussed below

Six more `ljmp` entries sit at the eight-byte-stride offset the six forwarders
do not use, five of them reaching the `0x1150`-`0x1168` group of §4 and one not:

- `common` `0x0007` `table_entry_to_1150`
- `common` `0x000E` `table_entry_to_1156`
- `common` `0x0016` `table_entry_to_115c`
- `common` `0x001E` `table_entry_to_1162`
- `common` `0x0026` `table_entry_to_1168`
- `common` `0x002B` `table_entry_to_05e7` — the one that does not join that
  group: its target is the lone `reti` one byte past `0x05E6`

And four slots hold a bare `ret`:

- `common` `0x0012` `ret_only_0012` [unresolved]
- `common` `0x001A` `ret_only_001a` [unresolved]
- `common` `0x0022` `ret_only_0022` [unresolved]
- `common` `0x002A` `ret_only_002a` [unresolved]

**The three one-byte `reti` targets, and what is and is not established.**
`0x052F`, `0x05E6` and `0x05E7` are each a single `reti` byte. Ghidra's
boundaries on this firmware cut through straight-line code often enough that a
one-byte function is exactly the shape a split epilogue takes, so the framing
question had to be settled from the bytes before any of this could be written
down. It settles three ways:

- `0x052F`'s seven preceding bytes, `0x0528`-`0x052E`, are a run of `ret`s
  after a separate function that ends in a `ret` at `0x0527`. The byte after it,
  `0x0530`, is the opening `push A` of the timer0 handler. Nothing runs into
  `0x052F` from either side.
- `0x05E5`, the byte before `0x05E6`, is the timer1 handler's **own** `reti`:
  `0x05B6`'s framed body is 48 bytes and ends exactly there, and its listing
  shows the matching `pop`/`pop` epilogue. So `0x05E6` is not that handler's
  tail, which is the one reading a `reti` at `0x05E6` would otherwise invite.
- `0x05E7`'s predecessor is `0x05E6`, itself a lone `reti`.

`ec/ghidra/reassembly.csv` records all three as `match` and
`verify_reassembly.py --check` reports 0 disagreements, so this is a statement
about the bytes and not about Ghidra's opinion of them. `0x0022` is the one
exception worth naming: the reassembler emits no bytes for it at all
(`assembler-gap`, "no bytes emitted at 0022"), which is a property of the
`sdas8051` used to re-assemble the listing, not a disagreement about the `ret`
that is there.

**What that does not establish, stated plainly.** "The vector target is one
`reti`" is a claim about this image. It is *not* "int0 and serial 0 are
unimplemented": whether the EC services those sources is a question about the
interrupt-enable and peripheral registers, which none of these addresses reads
and which this document does not decode. **Two of the three carry a row** —
`common` `0x052F` and `common` `0x05E6`, both `type: unresolved` for that
reason and both cited above with the marker, so a reader cannot take them for
decoded handlers. **`0x05E7` carries no row at all**:
`ec/decompiled/index.csv` exports it as `FUN_CODE_05e7` with `annotated=no`, and
no citation in this document reaches it, so `--check` cannot see it either.
Everything said about it above is read from its bytes and its `reassembly.csv`
record, which is why it is written out here rather than cited.

**The two common-area duplicates from §2.** Both are visible in the bytes and
neither is settled:

- `common` `0x0512` is `ajmp 0x0003` — two bytes, and a real second path to the
  int0 forwarder, so Ghidra's `int0_vector_forwarder_to_052f` name at that
  address is right about where it goes. It exists because the call-target byte
  scan found `01 03` there, not because the vector table does.
- `common` `0x1207` is a bare `ljmp 0x1100` and the index names it
  `bl51_bank_select_0`. The three bytes before it, at `0x1204`, are
  `90 bf 62` — `mov DPTR,#0xBF62` — so `0x1204`-`0x1207` is one two-instruction,
  six-byte thunk of the same shape as every function in §4, split in two by a
  call-target frame, and the second half inherited the name of the first. Whether
  the common area genuinely carries a second copy of the stub or Ghidra split one
  routine is not established by the bytes alone.

**Correction, 2026-09-25 (#601): one of the two is settled, and the other's
"second path" is withdrawn.** The paragraph above is left as written.

- `0x1207`'s *framing* is settled. `ec/decompiled/common/1204.asm` is a
  committed listing in its own right and carries one instruction, so
  `0x1204`-`0x1206` is a whole exported function and `0x1207` begins the next
  statement rather than sitting inside one. The name is the target's: `0x1100`
  is `bl51_bank_select_0` and a row of `ghidra-functions.csv` names it. What the
  bytes still do not decide is the question the paragraph above leaves open —
  a second copy or one routine split in two is about the vendor's linker output,
  not about the bytes at either address.
- `0x0512`'s *name* is settled and is `common 0x0003`'s: the two bytes
  `01 03` are an `ajmp 0x0003`, `0x0003` is the int0 vector slot, and the
  decompiled C at `0x0512` is `0x0003`'s. The **"a real second path to the int0
  forwarder" above is withdrawn**: read linearly from `0x050D`, the bytes at
  `0x0512`-`0x0513` are the immediate and the displacement of the
  `cjne a,#0x01,0x0517` at `0x0511`, and all 24 anchors in the 24 bytes to the
  left step over `0x0512` rather than landing on it — so the frame is a byte
  scan's `01 03` pattern inside a real instruction, and no execution reaches
  `0x0512` as an instruction start by that read. The same read is
  `disasm8051.converges_from()`, whose own docstring warns that a site nobody
  syncs onto may instead be preceded by data no linear walk can align to; the
  window here is code either way (`0x050D`-`0x0517` is a compare and two
  stores), which is what rules that out rather than the anchor count alone.
  [`docs/findings/named-without-a-row.md`](../../docs/findings/named-without-a-row.md)
  §5 has the reading and the same four-address finding for `bank0 0x031C`,
  `bank1 0x031C` and `bank1 0x703A`.

## 4. Cross-bank code access (BL51)

Full detail in [`bank-call-audit.md`](bank-call-audit.md). Four stubs, all
`type: gate`, all in the common area:

- `common` `0x1100` `bl51_bank_select_0`
- `common` `0x1114` `bl51_bank_select_1`
- `common` `0x1128` `bl51_bank_select_2`
- `common` `0x113C` `bl51_bank_select_3`

The five thunks §3's table entries reach, each a `mov DPTR,#imm16` and an
`ljmp 0x1100`:

- `common` `0x1150` `load_dptr_bf1c_tail_jump_1100`
- `common` `0x1156` `load_dptr_bf1d_tail_jump_1100`
- `common` `0x115C` `load_dptr_bf1e_tail_jump_1100`
- `common` `0x1162` `load_dptr_bf1f_tail_jump_1100`
- `common` `0x1168` `load_dptr_bf20_tail_jump_1100`

The trampolines that reach the stubs from the rest of the image, measured over
the committed listings by shape — a function whose whole body is
`mov DPTR,#imm16` followed by `ljmp <stub>` — are 290 across the export, of
which 282 name a BL51 stub: 261 to `0x1100` and 21 to `0x1114`, and none to
`0x1128` or `0x113C`. **82 of those 282 are annotated** (62 and 20
respectively), so the stub addresses are established and the callers are
mostly not. The looser count — rows whose `comment` field names `0x1100` or
`0x1114` — is 94, and it is a different and weaker measurement: it catches a
row that discusses a stub without being one of the 282. `--check` recounts
only the four census figures, so this one is not held to a recount by the gate
and is stated here as a count of one named column rather than as a figure
something will catch if it drifts.

**The same-bank caveat carries over unchanged.** `bank-call-audit.md` states
that a trampoline whose target lies in the banked window does not establish
which bank the caller reaches, because the same address means different bytes in
each bank. The five thunks above are in that position exactly as the annotated
trampolines are, so this document does not restate the caveat as a bank mapping.

## 5. Charge-voltage target

Full detail in [`charge-target-derating.md`](charge-target-derating.md), and the
traced flow in [`charge-profile-flow.md`](charge-profile-flow.md) — including
that file's 2026-09-19 correction, which is linked here rather than restated or
quietly superseded. Four named functions establish it:

- `bank0` `0xB12C` `manual_ctrl_profile_gate` — force-resets the profile to High
  Capacity when `AP_OEM` bit 0 is clear
- `bank0` `0xB158` `charge_target_update` — the per-cell derating in mV
- `bank0` `0xB1F0` `charge_stress_update` — the age and temperature terms
- `bank0` `0xB35E` `charge_target_minus_r3_times_0a47` — the target arithmetic
  against the cell count

This group does not establish that the host can set the target, or that
`0x07B9` does not exist: `docs/findings.md` §4m and §4c are where those two
questions live, and the second is a retraction that stays visible.

## 6. Fan and thermal control

Not one of the issue's five candidates, and it should be here: the issue's own
first motivating example is "to change a fan curve". What follows is a
**grouping**, not a decoded control loop. The group is by shared XDATA
neighbourhood and by the existing rows' own comments; a follow-up decodes it.

- `bank0` `0x8653` `seed_fan_table_base`
- `bank0` `0x888D` `fan_table_mailbox_handler`
- `bank0` `0xBB40` `fan_mode_get`
- `bank0` `0xBC4F` `fan_table_base_offset_helper` — the one row of the group
  whose `basis` is `inferred` rather than `hand-decoded`
- `bank0` `0xCA4C` `read_fan_mode_bits_4_and_7`
- `bank0` `0xBAD4` `sub_input_from_cpu_temp_043e`
- `bank0` `0xBAE5` `batt_temp_dK`
- `bank0` `0xBB56` `cpu_temp_minus_code_table_byte`
- `bank0` `0xBBDE` `gpu_temp_minus_code_table_byte`
- `bank0` `0xBDF2` `gpu_temp_minus_xdata_byte`
- `bank0` `0xCCFC` `power_on_init_and_two_hang_paths`
- `bank1` `0x8ECC` `select_r4_from_cpu_temp_and_0620_0626`
- `bank1` `0x9416` `adjust_0627_index_against_gpu_temp`

**What this group does not establish.** There is no control loop here: no
closed-loop reading, no error term, no ordering between the CPU- and
GPU-temperature functions. The two tables these functions index are the subject
of [`xdata-0400-045f.md`](xdata-0400-045f.md) and
[`manual-fan-ctrl-0751.md`](manual-fan-ctrl-0751.md), and the fan-mode byte's
own per-site table is `manual-fan-ctrl-0751-sites.csv`. Six of these thirteen
names describe a subtraction or a read rather than a fan, which is the honest
state of the decode and the reason this section is a grouping.

## 7. Power modes (`0x0751`)

`0x0751` is a register, not a function, so this section cites the functions
that read it. [`../../docs/findings.md`](../../docs/findings.md) §7 has what
Office, Gaming and Turbo write; §7a and
[`manual-fan-ctrl-0751.md`](manual-fan-ctrl-0751.md) have the 29 direct
reference sites, all of them in the main EC image and every one of them
touching `0x0751` and no other XDATA byte. The named functions among them:

- `bank0` `0xAC08` `dispatch_on_0751_bits` — the one function whose whole job is
  branching on the mode byte
- `bank0` `0xAB9E` `set_0751_and_07a6_bits` — writes the mode byte alongside the
  charging profile
- `bank0` `0xBB40` `fan_mode_get` — also in §6
- `bank0` `0xCA4C` `read_fan_mode_bits_4_and_7` — also in §6
- `bank0` `0x8DE0` `ramp_1804_toward_0670_and_set_1809`
- `bank0` `0x95DD` `fill_08xx_from_code_table`
- `bank0` `0x9D9B` `compute_level_blocks_086b_086c_086e`
- `bank0` `0xB716` `clear_08eb_bit3_09e6_09e7_08a2_089e_089f`
- `bank0` `0xB82E` `clear_08eb_bit6_and_zero_08a0`

**What this group does not establish.** The arm walk is finished, not open:
[`../../docs/findings.md`](../../docs/findings.md) §7b records both arms of all
17 mode-bit branches walked, 34 `kind: arm` rows in
[`manual-fan-ctrl-0751-arms.csv`](manual-fan-ctrl-0751-arms.csv), every one
`status: complete`. That does not answer this section's question, because the
arm table records what each arm *touches* and *reaches* rather than which mode
bit selects which of the functions above. Three of the nine are reached —
`bank0` `0xBB40` `fan_mode_get`, `0xB716` and `0xB82E` all appear in the arms'
`callees` column — and the other six appear in no column of it at all. So
which of these functions a given mode actually reaches is still not
established, and a Linux `platform_profile` cannot be written from this list
yet.

## 8. Lightbar

[`../../docs/findings.md`](../../docs/findings.md) §3's finding is the one to
carry: **the EC path is real, just not for this chassis.** Every uniwill EC
lightbar register (`0x0748`-`0x074B`) was written live with the animation
running; every write landed and changed nothing visible. Full detail in
[`lightbar-bat-flow.md`](lightbar-bat-flow.md) and §3a-§3e.

The functions cited there are **not** in the EC half of this map, and the
reason matters. §3a's finding is that the battery-side lightbar registers live
in the separate `ITE8850-PD` program, not the EC: `pd` `0x0760`
`saturate_r4_from_d5_r5_80` is one of the two named rows that touch them, and
`pd` `0x0FCB` `load_xdata_to_r0_r1_r2_or_r3` the other. There is no named
`bank0` or `bank1` function that writes `0x0748`-`0x074B`.

**What this group does not establish.** Nothing about the lightbar on this
chassis: the live result is a negative one and this document adds no EC-side
path to it.

## 9. The index/data path

The issue asks for "the EC index/data port accessors, if they can be identified
at all". The honest answer is **partly, and not on the EC side where the phrase
points**, and it splits in two.

**The literal index/data port is a BIOS mechanism.** The `0x62`/`0x66` pair with
`0xA3`/`0xA2` index bytes does not exist in the 8051 at all; it is the ACPI EC
interface, and it is already mapped and typed `ec-io` in
[`../../bios/annotations/ghidra-functions.csv`](../../bios/annotations/ghidra-functions.csv).
Thirty rows carry that type, and the one that performs the whole write is:

- `OemOcDxe` `0xF38` `EcWriteCommandData` — the `0xA3`/`0xA2` register write as a
  three-argument call, waiting for IBF and draining OBF around it

The function that carries the `0x62` port base and the index byte as its
arguments is a neighbour of that set rather than a member of it, and its type
says so:

- `OemTurboModeDxe` `0x778` `write_index_data_byte` — every call site passes
  `0x62` as the port base; it is `type: writer`, not `ec-io`, and is not one of
  the thirty

**The EC-side analogue is the index-helper family, and it is partly named.**
[`pd-index-helpers.csv`](pd-index-helpers.csv) has 11 rows, of which four are
named functions:

- `pd` `0x10BC` `add_full_product_to_dptr` — the one address in the family that
  is an entry, and the target six of the others tail-jump to
- `pd` `0x9987` `load_a_from_r7_9987`
- `pd` `0x998F` `dbl_a_add_dph_write_dph`
- `pd` `0x9A1B` `a_r3_b_60_tail_10bc`

The other seven rows of that CSV carry no annotation row of their own: six are
not exported functions at all, and `pd` `0x998B` is exported but carries only
the inherited name of `pd` `0x10BC`, which §2 records. And the four *site*
accessors the issue's phrase points at —
`0x7421`, `0x9DEC`, `0xB5D3` and `0xE9F5` — **are not exported functions at
all**: each is a code site inside a larger routine that no `lcall` names.
[`pd-index-callers.csv`](pd-index-callers.csv) traces all four, and **four of
its five rows are `status: unresolved`**; the fifth found literal index loads
rather than resolving a caller either.

**What this group does not establish.** Which entry those four sites belong to,
and therefore whether the EC has one index-helper routine or several. Making
those sites functions is a separate decompilation job and this document does
not attempt it.

## 10. XDATA naming, at its current extent

`ec/ghidra/xdata-symbols.csv` is **generated** from
[`registers.yaml`](registers.yaml) by `ec/tools/gen_xdata_symbols.py` and must
never be hand-edited. It currently carries **177 names**, each with the register
it came from, that register's `status:`, and how it was derived. The generator
reads `registers.yaml` and never writes it, so a symbol rename cannot imply a
`status:` change.

`registers.yaml` itself holds **145 registers**, and has no cluster, group or
subsystem field — its keys are `addr`, `name`, `note`, `sources`, the three
reference counts, and `status`. So there is no machine-readable grouping to map
from, and this section is the whole of it: the names exist, the grouping does
not.

**`registers.yaml` is untouched by this document and could not have been moved
by it.** A static decode of a common-area function is not evidence about a
register's behaviour in either direction, which is the
[`pd-index-geometry.md`](pd-index-geometry.md) precedent. This document adds no
register status and moves no pin.

The XDATA *cluster* work is deliberately not here: the issue itself says it is
the same work as the register-map issue and should not be done twice, and
[`pd-xdata-overlap.md`](pd-xdata-overlap.md),
[`xdata-0400-045f.md`](xdata-0400-045f.md) and
[`xdata-register-map.md`](xdata-register-map.md) are that work.

## 11. The measured remainder

The same four totals as §2, restated here so the remainder can be read on its
own. `--check` compares both occurrences against the same recount, so they
cannot drift apart silently:

- `exported functions` — 2710
- `annotated function rows` — 1872
- `rows the index marks annotated` — 1897
- `unresolved rows` — 169

**656 of the 753 common-area functions are unannotated, and that is the largest
single block of undecoded firmware in this repository** — larger than the whole
`pd` program. It is the natural next issue, and §2 is what sizes it. The 152
`unresolved` rows are a second, separate queue: functions that were looked at
and are correctly described as far as the bytes go.

## 12. What this does not establish

Stated as a list, because the limit is the point of the document:

1. **It is not a partition of the firmware.** §2's counts are the evidence, and
   677 common-area functions and 152 `unresolved` rows are not in any group
   here.
2. **Nothing was observed on hardware.** No register behaviour, no interrupt
   delivery, no fan response, no charge current. Every claim above traces to a
   committed `.asm` or a committed decompilation.
3. **A one-byte `reti` at a vector target is not an unimplemented interrupt.**
   §3 says what the framing is and what it is not.
4. **The bank a trampoline reaches is not established**, for §4's five thunks or
   for the 200 callers of those stubs that §4's shape census finds exported
   but unannotated. The
   `bank-call-audit.md` same-bank caveat is carried, not resolved.
5. **The fan and thermal group is a grouping, not a control loop.** §6.
6. **Which functions a power mode reaches is not established.** §7.
7. **The four index-helper site accessors are not functions**, and four of the
   five `pd-index-callers.csv` rows are unresolved. §9.
8. **No register `status:` moved**, and none could have. §10.
9. **A single-byte `ret` in a vector slot is a fact about this image, not about
   the part.** §3.
