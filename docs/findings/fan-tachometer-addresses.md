# The four §2 features resolve to five EC addresses, and one of them is not the byte the Windows service reads

(Issue #29. Static reading of the committed firmware
`ec/firmware/GMxMGxx_11.800`, the committed decompilations under
`ec/decompiled/`, the committed vendor source under `windows/decompiled/`,
and the committed driver excerpt under `linux/patches/`. **No laptop, no EC
and no Windows machine is involved**: every address below is re-derivable from
those files with the commands in §8, and nothing here is a live test. The
`confirmed-working` grades rest on the *reading* §2 of `docs/findings.md`
already records — a user who watched the RPM sysfs match the sound of the fan —
and this write-up did not repeat that observation.)

## The claim

**`PRIMARY_FAN`, `SECONDARY_FAN`, `TOUCHPAD_TOGGLE` and `USB_POWERSHARE` all
resolve to an EC address, every one of them re-derivable offline, and the
driver defines are not what this issue said they were missing.**

Two of the four are bits of bytes that already had a `registers.yaml` entry;
two more are tachometer pairs that did not, and take three new entries plus a
fourth for a byte the vendor and the EC disagree about. The address resolution
is the work. The disagreement is the finding worth keeping.

## 1. The premise that is false: the defines are committed here

The issue was written against a sentence this repository carried — that the
`uniwill-laptop` source is not vendored here, so a `grep` over `linux/` finds
no address for these four features. **That sentence is false, and it was false
before this issue was opened.** `linux/patches/gm7mg7p-dmi-entry/` has carried
the quoted defines since `5ba34d9e`:

```console
$ grep -n "EC_ADDR_MAIN_FAN_RPM\|EC_ADDR_SECOND_FAN_RPM\|EC_ADDR_TRIGGER\|EC_ADDR_OEM_4\|TOUCHPAD_TOGGLE_OFF\|TRIGGER_USB_CHARGING" \
    linux/patches/gm7mg7p-dmi-entry/upstream-excerpt.txt
90:     94: #define EC_ADDR_MAIN_FAN_RPM_1		0x0464
92:     96: #define EC_ADDR_MAIN_FAN_RPM_2		0x0465
97:    101: #define EC_ADDR_SECOND_FAN_RPM_1	0x046C
99:    103: #define EC_ADDR_SECOND_FAN_RPM_2	0x046D
149:  [EC_ADDR_TRIGGER -- the super key lock and USB powershare bits]
157:    210: #define EC_ADDR_TRIGGER			0x0767
162:    215: #define TRIGGER_USB_CHARGING		BIT(4)
190:  [EC_ADDR_OEM_4 (charge modes, TOUCHPAD_TOGGLE_OFF) and EC_ADDR_CHARGE_CTRL]
194:    286: #define EC_ADDR_OEM_4			0x07A6
200:    292: #define TOUCHPAD_TOGGLE_OFF		BIT(6)
```

Every line carries its own line number in `uniwill-acpi.c`, and the excerpt's
header names base rev `5a24248f6422a0b673a47cbfd65e19a98eb4c8a9` — the full
SHA of the `5a24248` that `linux/patches/BASE_COMMIT` pins. The four features
are mapped to their addresses beside it, each graded, each with a reason:

| §2 feature | address | `feature-map.csv` verdict |
|---|---|---|
| `PRIMARY_FAN` | `0x0464`/`0x0465` | `live-confirmed;driver-interface-drives` |
| `SECONDARY_FAN` | `0x046C`/`0x046D` | `live-confirmed;driver-interface-drives` |
| `TOUCHPAD_TOGGLE` | `0x07A6` bit 6 | `live-refuted` |
| `USB_POWERSHARE` | `0x0767` bit 4 | `write-accepted-effect-untested` |

`tools/check_dmi_descriptor.py` rule 7 holds that map to the excerpt byte for
byte, so the two cannot drift apart without the gate going red:

```console
$ python3 tools/check_dmi_descriptor.py
15 feature(s) mapped: 8 in the descriptor, 7 excluded with a reason.
```

**What is genuinely absent offline is narrower, and it is a different thing
altogether.** The excerpt is not defines-only and saying so would be its own
overclaim: besides the `#define` block it quotes the
`struct uniwill_device_descriptor` definition and several
`.features = UNIWILL_FEATURE_…` descriptor initializers, three of which name
`UNIWILL_FEATURE_PRIMARY_FAN`, `UNIWILL_FEATURE_SECONDARY_FAN` and
`UNIWILL_FEATURE_USB_POWERSHARE` as bits of a board's descriptor. What it does
**not** contain is any function body, and so any EC access at all — there is
no `regmap_bulk_read`, no `be16_to_cpu`, no `ec_read`/`ec_write` and no
read-modify-write anywhere in it outside a `#define` value. *How* the driver
reads or writes each byte is therefore not re-derivable from this tree, and a
claim resting on that is a claim from a clone of `Wer-Wolf/uniwill-laptop`
rather than from a committed input. That boundary is what §6 is for. The
*addresses*, by contrast, are fully re-derivable offline, and §2 to §5 do it.

## 2. The two bits: an alias, not a new byte

Neither feature has an address of its own, and neither is given a `status:` of
its own here — see §5. Each is a bit of a byte that already has an entry, so
what the driver names is recorded in that entry's note and the address is
unchanged.

**`USB_POWERSHARE` → `TRIGGER` (`0x0767`), bit 4.** `uniwill-acpi.c:215`
defines `TRIGGER_USB_CHARGING BIT(4)`. The vendor service agrees on the byte
and the bit, from its own side: `USB_Charger_ON`/`_OFF` read `1895` (`0x0767`),
set or clear `bitArray[4]`, and write it back
(`windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/MySettingManager.cs`;
the callsite census carries both, as `USB_Charger_ON`/`USB_Charger_OFF` read and
write rows on `0x0767`, in `windows/decompiled/v3.1.39.0/ec-callsites.csv`).

**`TOUCHPAD_TOGGLE` → `OEM_4` (`0x07A6`), bit 6.** `uniwill-acpi.c:292`
defines `TOUCHPAD_TOGGLE_OFF BIT(6)`. `TouchpadToggle_ON` masks `& 0xBF` and
`_OFF` writes `64 + b` on `1958` (`0x07A6`) — same file, same shape, and the
same two read/write row pairs in the callsite census. The naming direction is
worth noting because it is the opposite of the byte's other bit:
`TOUCHPAD_TOGGLE_OFF` is set to disable, and `TouchpadToggle_ON` *clears*
bit 6.

Both of these were already recorded, before this issue: the `TOUCHPAD_TOGGLE`
and `USB_POWERSHARE` rows of `feature-map.csv` say so explicitly ("an address
IS readable for it — the exclusion is the live result", and "so the address is
readable here too"), and the callsite census carries the read/write pairs.
The overclaim this write-up corrects is not that these two were missing an
address. It is the sentence that said no `linux/` address existed for any of
the four.

## 3. The tachometer pairs: three new entries, big-endian

Neither fan pair had an entry. Both are written and read by the EC as one
16-bit value, and both are reachable from the driver and the vendor at the
same addresses.

| address | vendor constant | upstream define | EC pair |
|---|---|---|---|
| `0x0464` | `ADDR_EC_MAIN_FAN_RPM_BYTE1` (1124) | `EC_ADDR_MAIN_FAN_RPM_1` | high byte |
| `0x0465` | `ADDR_EC_MAIN_FAN_RPM_BYTE2` (1125) | `EC_ADDR_MAIN_FAN_RPM_2` | low byte |
| `0x046C` | `ADDR_EC_SECOND_FAN_RPM_BYTE1` (1132) | `EC_ADDR_SECOND_FAN_RPM_1` | high byte |
| `0x046D` | — (no constant in any of the three `ECSpec.cs`) | `EC_ADDR_SECOND_FAN_RPM_2` | low byte |

The vendor constants are at `windows/decompiled/v3.1.6.0/ECSpec.cs:221-229`,
byte-identical across the three service versions this repository holds.
`FanInfo.GetEcCpuFanRpm` reads 1124 then 1125 and returns `(num << 8) | b`
(`windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/FanInfo.cs`), so the
first pair's byte order is the vendor's own.

**The EC's reading of the second pair agrees, and settles the one question the
vendor leaves open.** `store_r6_r7_to_046c_046d` (bank0 `0xE024`) writes one
value across both bytes across an `inc DPTR`, and
`be16_046c_046d_minus_100` (bank0 `0xBD6B`) reads them back as one, taking
the constant from the low byte and letting the borrow land in the high one:

```console
$ sed -n '/^BD6B/,/^BD78/p' ec/decompiled/bank0/BD6B.asm
BD6B     c3 - -   clr      CY
BD6C     90 04 6d mov      DPTR, #0x46d
BD6F     e0 - -   movx     A, @DPTR
BD70     94 64 -  subb     A, #0x64
BD72     90 04 6c mov      DPTR, #0x46c
BD75     e0 - -   movx     A, @DPTR
BD76     94 00 -  subb     A, #0x0
BD78     22 - -   ret
```

A 16-bit subtract takes its constant from the low byte and carries the borrow
into the high one, so the byte the constant comes off — `0x046D` — is the low
byte, exactly as upstream's `_1`/`_2` spelling puts it.
`be16_0464_0465_minus_100` (bank0 `0xBD5D`) has the same shape over the first
pair, so both pairs take the same order. `ec/annotations/xdata-clusters.csv`
agrees independently: `main-ec-145` holds `0x0464 0x0465` and `main-ec-138`
holds `0x046C 0x046D`, neither holding a member of the other pair.

**Byte order is kept out of the symbol names.** `gen_xdata_symbols.py`'s stated
rule is `<BASE>_0`/`<BASE>_1` by address order and never `_HI`/`_LO`, and the
same convention is already spelled that way for the other 16-bit entries in
`ec/ghidra/xdata-overrides.csv`. The big-endian fact is real and citable, so
it is in the `registers.yaml` notes — where a correction can be made in place
— rather than baked into a generated symbol that will outlive it.

## 4. `0x046B` is not the second fan's low byte

**`ECSpec.cs` names `ADDR_EC_SECOND_FAN_RPM_BYTE2` as `1131` = `0x046B`, and
`FanInfo.GetEcGpuFanRpm` reads `0x046C` then `0x046B` as `(num << 8) | b`.
Upstream at the pinned rev, the EC's own store, the EC's own read and the
committed capture all put the low byte at `0x046D`.**

This is a fact about the vendor's code, not about the hardware, and it is worth
recording in the register file rather than leaving it as an aside — it is the
one address in this write-up whose name and whose use disagree.

`0x046B`'s four direct `MOV DPTR` sites all sit inside one routine,
`gate_06e6_442_then_sync_046a_from_086b` at bank0 `0x9CA6`. Two of them — the
read at `0x9D22` and the write at `0x9D4D` — are in that routine's single
four-byte sync of `0x046A`/`0x046B`/`0x046E`/`0x046F` from `0x086B`-`0x086E`:
read, compare, and copy the whole quartet when any member differs
(`ec/decompiled/bank0/9CA6.asm`, the `xrl a,r7` chain at `0x9D1A` through
`0x9D3E` and the store run at `0x9D41` through `0x9D60`). A third, the read at
`0x9D69`, is downstream of that sync rather than in it: it sits past the end of
the store run, in the tail that stages `0x046A`/`0x046B`/`0x046F` into R7 for
the `0xDF1E`/`0xDF35`/`0xDF78` calls, and never reads `0x046E` — the same shape
as the `0x046A` read at `0x9D61` and the `0x046F` read at `0x9D71`. So it is a
read staged for a call, not a member of the quartet.

The fourth site, the write at `0x9CEB`, is not part of that sync either, and
saying so matters more than it looks: it is the one place where "four sites"
would be doing work the listing does not support. It sits on an earlier path in
the same routine, which stores `0x0781` (or `0x08C0` when that is zero) into
`0x046A`, `0x08C1` into `0x046B` and `0x08C3` into `0x046F`, then `sjmp`s into
the store run at `0x9D5C` — a **three**-byte write that never touches `0x046E`
and takes its second byte from `0x08C1` rather than from `0x086C`. So the sites
split three ways: two are in the quartet, one is downstream of it and one is not
related to it at all. The conclusion is unaffected — `0x046B` is still a sync
member and still not a fan low byte — but "all four are part of a single
four-byte sync" would have been an overclaim about two sites in four.

The routine's own name already says which byte it is really about: it syncs
`0x046A` from `0x086B`. `0x046B` is the second member of that quartet, and
the quartet does not read as a fan pair at all: `ECSpec.cs` names its first
member `ADDR_EC_BIOS_INFO5` (`1126`), which is a different register entirely,
and its last two members `0x046E`/`0x046F` carry no name in `ECSpec.cs` or in
`registers.yaml`. Only the second member is named as a fan, and that name is
the one the EC contradicts.

The committed capture agrees with the EC and against the service. Across the
one committed record of how often a byte moved
(`evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv`), the four
tachometer bytes and the disputed one:

| address | change count |
|---|---:|
| `0x0464` (first pair, undisputed) | 126 |
| `0x0465` (first pair, undisputed) | 540 |
| `0x046C` | 154 |
| `0x046D` | 536 |
| `0x046B` | **1** |

A 16-bit value has a high byte that moves on the low byte's carry, so the two
halves of a real pair sit in the same order of magnitude — which the
undisputed first pair shows at 126 against 540. A byte that moved **once**
beside one that moved 154 is not the low half of what its partner is.

`docs/findings/fan-duty-channel-075b-075c.md` §4 already carries this
divergence, the correlation over the committed samples, and both byte orders
measured, and reaches the same place: a lead, not a naming. **This write-up
does not close it and does not claim to.** What it adds is that `0x046B` now
has a `registers.yaml` entry, graded for what the EC demonstrably does with it
and not for what the vendor reads.

## 5. Status grading, and what is deliberately not graded

Per the issue's own constraint — no status may be upgraded on the strength of
a reference count alone — and per `CLAUDE.md`'s calibration rule:

**`0x0464`/`0x0465`/`0x046C`/`0x046D` → `confirmed-working`,** on the reading
`docs/findings.md` §2 already records: "confirmed (RPM sysfs matches physical
sound)". That is a live read cross-checked against a physical observation,
which is the definition of the vocabulary, and it is not a count. The note says
what it is: a **read** verdict. It establishes that the driver/EC model
matches the machine; it does not establish that the bytes are writable
controls, and nothing here writes them.

**`0x046B` → `present-untested`,** named for what the EC does with it — the
four-byte sync of §4 — rather than for the vendor's fan reading, which the
EC's own code contradicts. Not `absent`, because it has sites. Not
`confirmed-inert`, because that would assert the service's read is wrong *at
runtime*, and no live test here says so; the committed capture is a static
sweep of one moment, not a verdict on the byte.

**Nothing is `absent`.** Every count here is non-zero, and a static count is
never "does not exist" in any case.

**`USB_POWERSHARE` and `TOUCHPAD_TOGGLE` get no `status:` of their own,** and
that is the conservative choice rather than an oversight:

- `USB_POWERSHARE`'s §2 evidence is "EC bit flips on write; real-world effect
  untested". A readback is not evidence the EC acts on the byte — the exact
  distinction `CLAUDE.md` draws, and the exact mistake `OEM_9`'s note records
  as a downgrade from `confirmed-inert`.
- `TOUCHPAD_TOGGLE`'s is "Fn+F5 emits no WMI event at all". The test failed
  **upstream of the EC**: no WMI event means the hotkey never reached the
  service's handler, so the byte was never touched and no verdict about it
  exists either way.

## 6. What is available offline, stated precisely

Several different things were being conflated in the sentence this write-up
corrects. Separated:

| claim | re-derivable from this tree? | from where |
|---|---|---|
| the four features' EC **addresses** | **yes** | `upstream-excerpt.txt` (defines), `feature-map.csv`, the vendor `ECSpec.cs`/`MySettingManager.cs`, and the EC firmware |
| each feature's `UNIWILL_FEATURE_*` **bit** | **yes** | `upstream-excerpt.txt`, which quotes those defines and the `.features =` initializers |
| the EC's own **use** of those bytes | **yes** | `ec/decompiled/bank0/`, `trace_xdata_refs.py`, `xdata-clusters.csv` |
| the driver's **use** of the defines — the `regmap_bulk_read`/`be16_to_cpu` pair, the touchpad read, the read-modify-write | **no** | a clone of `Wer-Wolf/uniwill-laptop`; the excerpt quotes no function body |

Only the last row is unavailable, and nothing in this write-up rests on it.
The full 90 KB `uniwill-acpi.c` is deliberately not vendored — that is the
committed, correct arrangement, and
[`dmi-descriptor-evidence.md`](dmi-descriptor-evidence.md) is the write-up
that drew the line between "not vendored" and "not readable". What the
earlier sentence got wrong was not that arrangement; it was turning a fact
about the excerpt's *contents* into a fact about the repository's.

## 7. What a live test would still have to answer

Nothing above needs a machine. These do, and none of them is done here:

- **Whether the tachometer bytes are writable controls.** They are read by the
  EC and read by the driver; nothing in this tree shows a host write to
  `0x0464`-`0x046D` changing anything, and nothing should.
- **Whether `USB_POWERSHARE` bit 4 has a real effect.** The write is accepted;
  §2 of `docs/findings.md` already records the real-world effect as untested.
- **Whether the touchpad bit reaches the EC at all.** The Fn+F5 test failed
  before the byte, so it says nothing about `0x07A6` bit 6.
- **Which byte is the second tachometer's low half, on hardware.** The four
  independent sources in §4 agree on `0x046D` and the vendor's own read says
  `0x046B`; a live tach read settles it, and
  `docs/findings/fan-duty-channel-075b-075c.md` §6 is the procedure.

Issue #29 is not labelled `needs-hardware-test` and this write-up does not
make it one.

## 8. Reproducing every figure

The counts, against the committed firmware:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 --counts-only \
    0x0464 0x0465 0x046B 0x046C 0x046D | grep -v '^$'
0x0464: 3 direct MOV DPTR site(s)  bank0=3
0x0465: 1 direct MOV DPTR site(s)  bank0=1
0x046B: 4 direct MOV DPTR site(s)  bank0=4
0x046C: 3 direct MOV DPTR site(s)  bank0=3
0x046D: 1 direct MOV DPTR site(s)  bank0=1
```

All five are main-EC, `bank0`; no PD-image site, so `static_refs_pd_image` is
`0` throughout. `check_register_counts.py` re-derives all three keys for every
entry from the image and is the guard:

```console
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
```

The vendor constants, read rather than taken on trust:

```console
$ grep -n "ADDR_EC_MAIN_FAN_RPM_BYTE\|ADDR_EC_SECOND_FAN_RPM_BYTE" \
    windows/decompiled/v3.1.6.0/ECSpec.cs
$ grep -n "USB_Charger_\|TouchpadToggle_" \
    windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/MySettingManager.cs
```

The capture rows behind §4's table:

```console
$ grep -E "^0x046[45BCD]," evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv
```

The committed defines behind §1's table, and the check that holds the map to
them, are quoted in §1. The suite holding this write-up's byte facts —
that every resolved address's three counts re-derive from the image, that
`0x046B`'s four sites all sit inside the `0x9CA6` listing and that the routine's
quartet names all four of its members, that the excerpt quotes every address and
bit this write-up resolves and no EC access, and that a file saying the driver
defines are unavailable also says where they are committed — is
`ec/tools/test_fan_tachometer_addresses.py`.
