# The four features `static-refs-audit.md` §3 called unresolvable, resolved —
# and the vendor is wrong about one of the four bytes (2026-10-02, issue #29)

`ec/annotations/static-refs-audit.md` §3 closed with a paragraph saying four
`docs/findings.md` §2 features could not be given EC addresses, and naming the
fix: pull `uniwill-laptop` at `linux/patches/BASE_COMMIT` and read the
defines. This is that, plus the correction the pull turned up.

**Three of the four addresses were already in this repository before the pull,
under names the audit did not use.** `USB_POWERSHARE` is bit 4 of `0x0767`,
which is already a row in §3's own table under the name `TRIGGER`.
`TOUCHPAD_TOGGLE` is bit 6 of `0x07A6`, already a row as `OEM_4`. The fans'
four bytes were named in `windows/decompiled/v3.1.6.0/ECSpec.cs` and read in
`FanInfo.cs`. So the driver fetch is corroboration and naming, not rescue —
which is worth saying plainly, because the issue's framing ("could not
resolve") is a statement about a `grep` over `linux/`, not about the tree.

**The substantive finding is that the vendor's `ECSpec.cs` is wrong about one
byte.** Its `ADDR_EC_SECOND_FAN_RPM_BYTE2` is `0x046B`. The driver, the EC's
own firmware, and two committed hand-decodes all put the second fan's low byte
at **`0x046D`**. `0x046B` is a different byte in a different quartet. The
issue's plan for this work had `0x046B` in it, taken from `ECSpec.cs` at face
value; it is corrected below and the correction is the reason this file is
more than a lookup.

No live test ran. Nothing here was observed on hardware, and no register was
written or read back.

## What each address is, and who says so

Reproduce the whole table with the two `grep`s and the clone at the end of
this file; the committed sources are in the tree and the driver is one
command away.

| feature | address | the committed source that names it |
|---|---|---|
| `USB_POWERSHARE` | `0x0767` **bit 4** | `MySettingManager.cs:1204-1224`, `USB_Charger_ON`/`_OFF`, RMW with `bitArray[4] = true`/`false` over a read of the same address (constant 1895); also `windows/decompiled/v3.1.39.0/ec-callsites.csv:429-432` and the "USB powershare (issue #7)" row of `windows/vendor-ec-map.md` |
| `TOUCHPAD_TOGGLE` | `0x07A6` **bit 6** | `MySettingManager.cs:1224-1246`, `TouchpadToggle_ON`/`_OFF`, `& 0xBF` and `64 + b` (constant 1958); `ec-callsites.csv:433-436` |
| first fan RPM | `0x0464`/`0x0465` | `ECSpec.cs:221,223` — `ADDR_EC_MAIN_FAN_RPM_BYTE1 = 1124`, `_BYTE2 = 1125`; read big-endian by `FanInfo.cs:24-32` |
| second fan RPM | `0x046C`/**`0x046D`** | `ECSpec.cs:227,229` names `0x046C`/`0x046B`; the driver and the EC firmware say `0x046C`/`0x046D` — see below |

The `USB_POWERSHARE` and `TOUCHPAD_TOGGLE` rows are the strongest agreement in
this repo's register map, and they are worth separating from the fan rows
because they are agreement of a *different kind*. Two implementations written
by different teams, on different sides of the same vendor, name the same byte
and the same bit. The driver does it as `TRIGGER_USB_CHARGING BIT(4)` on
`EC_ADDR_TRIGGER = 0x0767` (`uniwill-acpi.c:210,215`) and the vendor as
`USB_Charger_ON`. For the touchpad the driver writes `TOUCHPAD_TOGGLE_OFF
BIT(6)` on `EC_ADDR_OEM_4 = 0x07A6` (`uniwill-acpi.c:292`) — note the polarity
reads backwards against the vendor's `TouchpadToggle_ON`, which *clears* bit 6
— so a reader comparing the two needs to know that `uniwill-laptop` names the
bit for the state it disables and the vendor names the method for the state it
sets. Same byte, same bit, same behaviour, opposite-looking names.

## The driver fetch

```console
$ git clone --filter=blob:none --no-checkout https://github.com/Wer-Wolf/uniwill-laptop.git ul
$ cd ul && git rev-parse 5a24248
5a24248f6422a0b673a47cbfd65e19a98eb4c8a9
$ git checkout 5a24248f6422a0b673a47cbfd65e19a98eb4c8a9
```

`linux/patches/BASE_COMMIT` records the short SHA and its subject; the full
SHA is above. That file is deliberately left as it is — upgrading the pin is a
separate change, and this one is about what the commit *says*.

The driver source is **not vendored here** and nothing in this repository
cites it as a committed input. Every address above is independently
re-derivable from `windows/decompiled/`; the driver is a second opinion on a
source that is one `git clone` away, and that is how it is described here.

What the driver settles — all four addresses, in `uniwill-acpi.c`:

```
#define EC_ADDR_TRIGGER                    0x0767
#define EC_ADDR_OEM_4                      0x07A6
#define TOUCHPAD_TOGGLE_OFF                BIT(6)
#define TRIGGER_USB_CHARGING               BIT(4)
#define EC_ADDR_MAIN_FAN_RPM_1              0x0464
#define EC_ADDR_MAIN_FAN_RPM_2              0x0465
#define EC_ADDR_SECOND_FAN_RPM_1            0x046C
#define EC_ADDR_SECOND_FAN_RPM_2            0x046D
```

The two fan reads are `regmap_bulk_read` of `sizeof(rpm)` bytes from the
`_1` address followed by `be16_to_cpu` (`uniwill-acpi.c:1399,1403`), so the
driver's pairs are **consecutive** — `0x0464`/`0x0465` and `0x046C`/`0x046D`.

## The divergence, and why the driver is right about `0x046B`

`ECSpec.cs` is not self-inconsistent here, and that is what makes it worth
writing down: it puts the *first* fan at `1124`/`1125` = `0x0464`/`0x0465`,
which is consecutive and correct, and then the *second* at `1132`/`1131` =
`0x046C`/`0x046B`, which is not. The high byte is right and the low byte is
wrong, so the error is invisible to anything that checks only one address of
the pair.

Three independent things put the low byte at `0x046D`:

1. **The driver** — `EC_ADDR_SECOND_FAN_RPM_2 0x046D`, read as a consecutive
   bulk pair with `be16_to_cpu`, above.
2. **The EC's own firmware** — `store_r6_r7_to_046c_046d` (bank0 `0xE024`)
   writes R6 to `0x046C`, increments DPTR, and writes R7 to `0x046D`. The
   committed `.asm` is nine lines and unambiguous:

   ```asm
   E024     90 04 6c mov      DPTR, #0x46c
   E027     ee - -   mov      A, R6
   E028     f0 - -   movx     @DPTR, A
   E029     a3 - -   inc      DPTR
   E02A     ef - -   mov      A, R7
   E02B     f0 - -   movx     @DPTR, A
   E02C     22 - -   ret
   ```

   The routine's name in `ec/annotations/ghidra-functions.csv` is a
   hand-decode, not a generated one, and it was written before this issue.
3. **A second committed hand-decode** — `be16_046c_046d_minus_100` (bank0
   `0xBD6B`) subtracts `0x64` from `0x046D` into `0x046C` through the borrow,
   the same shape as `be16_0464_0465_minus_100` (bank0 `0xBD5D`) over the
   first pair. Both were already annotated with the `046D` spelling.

And `0x046B` is positively accounted for elsewhere, which is what rules it out
rather than merely making it unattested. `ec/annotations/xdata-clusters.csv`
puts it in `main-ec-004` with `0x046A`, `0x046E` and `0x046F`, all four synced
from `0x086B`-`0x086E` by `gate_06e6_442_then_sync_046a_from_086b` (bank0
`0x9CA6`), whose hand-decode at
`ec/annotations/ghidra-functions.csv` spells that quartet out. Its four
`sites` are all inside that one routine. It is a state byte copied from a
table, not a tachometer.

**This is not a new claim.** `registers.yaml`'s `0x075B` entry already
recorded the doubt — "GetEcGpuFanRpm's pairing is in doubt, which is a fact
about the vendor's code rather than about this register" — and named the same
three pieces of evidence. What is new is that the driver has now been read at
the pinned commit and agrees with the EC against the vendor, which turns a
recorded lead into a resolved address.

**What stays open.** Which pair is the *first* physical fan, and whether the
other is the second fan or a second reading of the same one. `ECSpec`'s names
are ordinal (`MAIN`/`SECOND`) with no left/right or CPU/GPU in them, the
driver's are `hwmon_fan` channels 0 and 1, and neither says which physical
connector is on which. That is the same open question
`docs/findings/fan-duty-channel-075b-075c.md` is written for, and it is
settled by holding or unplugging one fan — not by anything here.

## The counts, measured

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 --counts-only \
    0x0464 0x0465 0x046C 0x046D
0x0464: 3 direct MOV DPTR site(s)  bank0=3
0x0465: 1 direct MOV DPTR site(s)  bank0=1
0x046C: 3 direct MOV DPTR site(s)  bank0=3
0x046D: 1 direct MOV DPTR site(s)  bank0=1
```

All four are main-EC and none is in the PD image, so these are one program's
XDATA and not the `0x04A6` kind of collision. Where the sites are:

- `0x0464` — read at `0x8778` (inside `mode_tick_084c_07a5_09ee`) and at
  `0xBD64` (inside `be16_0464_0465_minus_100`); written at `0xDFF3` across two
  consecutive bytes, R6 then R7, so that one site writes `0x0464` *and*
  `0x0465`.
- `0x0465` — read at `0xBD5E`, the single site.
- `0x046C` — read at `0x8793` and `0xBD72`; written at `0xE024`, the pair walk
  above, which writes `0x046C` and `0x046D`.
- `0x046D` — read at `0xBD6C`, the single site.

The `0x0464` reader at `0x8778` is inside a routine that tests **both** pairs
for zero and sets bit 5 of `AP_OEM` (`0x0741`) when both are zero
(`ec/annotations/ghidra-functions.csv`, `mode_tick_084c_07a5_09ee`). That is
the clearest committed statement that the EC treats these as two 16-bit pairs
rather than four loose bytes, and it is the same routine that decided this
question from the firmware side.

The two addresses the EC walks as a pair have a lower direct-site count each
(3 and 1) than either would if read separately, because one `inc dptr` walk
covers both bytes and `trace_xdata_refs.py` attributes it to the address the
walk starts at. That is a property of the counting method, not evidence that
the low byte is less used.

## Status grading, and where it is deliberately conservative

**Both fan pairs → `confirmed-working`.** `docs/findings.md` §2 records
`PRIMARY_FAN`/`SECONDARY_FAN` as "confirmed (RPM sysfs matches physical
sound)" — a live read cross-checked against an observation outside the
machine, which is what the vocabulary's `confirmed-working` means. Two limits
are recorded on the entries rather than left implicit:

- It is a **read** verdict. It establishes that the driver/EC model for these
  bytes is right. It says nothing about writing them, and the entries say so.
  Duty is a different byte (`0x075B`/`0x075C`) and PWM a third
  (`0x0743`-`0x0747`).
- The `0x046C`/`0x046D` grade rests on the same live observation as the first
  pair's, and on the address resolution above. It does **not** rest on the
  vendor's read being right — that read is `0x046C`/`0x046B`, and if the
  vendor's pairing were the correct one the live RPM figure would be wrong in
  its low byte, which is not something this repo can rule out from a
  committed file. The firmware's own 16-bit arithmetic over `0x046C`/`0x046D`
  is what settles the address.

**Not `absent` for anything.** Every count is non-zero. Had any come back
zero, the correct value would be `unknown-not-absent` in the `0x07B9` shape,
never `absent`.

**`USB_POWERSHARE` and `TOUCHPAD_TOGGLE` get no `status:` at all.** Each is a
bit of a byte that already carries one, and neither has a live verdict at the
register:

- `USB_POWERSHARE`'s §2 evidence is "EC bit flips on write; real-world effect
  untested". That is a **readback**, and CLAUDE.md is explicit that a write
  being accepted is not evidence the EC acts on it — the same reasoning that
  downgraded `0x0726`'s `OEM_9` out of `confirmed-inert`. The driver adds a
  caution worth keeping next to it: it records that the RMW "could also
  trigger the super key toggle, but the EC seems to take care that those bits
  are always read as 0" (`uniwill-acpi.c:1197-1200`), which is a reason not to
  blind-write this byte and is *not* a verified property of this EC.
- `TOUCHPAD_TOGGLE`'s is "Fn+F5 emits no WMI event at all". That test failed
  **upstream of the EC**: no event reached the service, so the byte was never
  written. It is evidence about the hotkey path, not about bit 6.

Recording either as a live row would be exactly the overclaim this file
exists to correct.

**Byte order stays out of the symbol names.**
`ec/tools/gen_xdata_symbols.py` names a multi-address register `<BASE>_0`,
`<BASE>_1` by address order and its `--self-test` refuses `_HI`/`_LO`/
`_BYTE1`. The big-endian fact is real and citable — `FanInfo.cs:31` does
`(num << 8) | b`, and the driver's `be16_to_cpu` agrees — so it is in the
entries' notes and in the `ec/ghidra/xdata-overrides.csv` reasons, where a
later correction can reach it, and not in a symbol that will outlive it.

## The overclaim this corrects

`ec/annotations/static-refs-audit.md` §3, as written:

> **What this subset cannot cover, and why.** §4d's 20 include features whose
> EC addresses are not recorded anywhere in this repository:
> `PRIMARY_FAN`/`SECONDARY_FAN`, `TOUCHPAD_TOGGLE` and `USB_POWERSHARE` appear in
> `../../docs/findings.md` §2 by feature name only, and `grep` over `linux/`
> finds no address for them

and `docs/findings.md` §3c, in the strong form:

> include features (`PRIMARY_FAN`/`SECONDARY_FAN`, `TOUCHPAD_TOGGLE`,
> `USB_POWERSHARE`) whose EC addresses are nowhere in this repo, so they
> could not be checked either way.

**"nowhere in this repo" and "not recorded anywhere in this repository" are
false as written, for all four features.** `USB_POWERSHARE` and
`TOUCHPAD_TOGGLE` are bits of addresses that were already rows in the audit's
own §2 table and §3 table. The fans' bytes are named in `ECSpec.cs` and read
in `FanInfo.cs`, both committed, and were cited by name inside
`registers.yaml`'s `0x075B` entry before this issue began.

The sentence is defensible only in its narrower form — *`grep` over `linux/`
finds no address, because the driver source is not vendored here* — and that
is what it is corrected to, with the wrong wording left in place beside the
correction per the `docs/findings.md` §4a-4d pattern. The narrower claim was
never wrong; the strong claim built on it was, and it is the kind of error
CLAUDE.md's calibration rule exists to stop: a statement about what a method
found, phrased as a statement about the world.

## What the re-derivable subset is now

`docs/findings.md` §4d's parenthetical says what is re-derivable from
committed files is a set of addresses. The four fan bytes have joined it: they
are now rows of `registers.yaml` and of §3's table in
`ec/annotations/static-refs-audit.md`, two addresses for each of the two
pairs, all four `confirmed-working`, all four main-EC with non-zero counts.

`USB_POWERSHARE` and `TOUCHPAD_TOGGLE` did **not** join it, because each is a
bit of a byte already in the set (`0x0767` and `0x07A6` are rows in §3's
live-verdict table) rather than a new address, and neither has a live verdict
of its own to add.

The original 20 is still not enumerated register-by-register anywhere, and
growing the re-derivable subset does **not** retroactively show that the scan
predicted all 20 correctly. That claim still rests on the original testing
notes. This only makes more of it checkable.

`static-refs-audit.md` §2 and §5 are a 29-address snapshot taken when that
file was written, and they stay that way; §9 below states what this changes
about them rather than editing tables written under different conditions.

## What the fetch did not settle

- **Which physical fan is which pair.** Named above; needs the machine.
- **Whether writing these bytes does anything.** Nothing here tests it, and
  the live evidence is a read.
- **Whether the vendor's `0x046B` read returns a plausible-looking wrong
  number**, which is what a bug like this usually looks like from the outside.
  `FanInfo.GetEcGpuFanRpm` computing `(0x046C << 8) | 0x046B` would produce a
  large plausible RPM rather than an obviously broken one, so the vendor's
  GPU-fan readout may have been quietly wrong on this machine for as long as
  the service has run. Whether it visibly was is not something a committed
  file can say, and no one should go looking for a symptom on the strength of
  this paragraph.
- **Whether the two pairs are two fans at all**, as opposed to one fan read
  twice. The `0x046C`/`0x046D` pair being written by a routine gated on
  `0x06E6` and fed from `0x1821`/`0x1820` (bank0 `0xE010`-`0xE02C`) is a
  structural difference from the `0x0464`/`0x0465` pair's `0x181F`/`0x181E`
  source, and it is suggestive rather than decisive.

## Reproducing all of it

```console
# the two bit-level claims, from committed files
$ grep -n "USB_Charger_\|TouchpadToggle_" \
    windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/MySettingManager.cs
$ grep -n "ADDR_EC_MAIN_FAN_RPM_BYTE\|ADDR_EC_SECOND_FAN_RPM_BYTE" \
    windows/decompiled/v3.1.6.0/ECSpec.cs

# the counts
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 --counts-only \
    0x0464 0x0465 0x046C 0x046D

# the EC's own pair walks, already committed
$ cat ec/decompiled/bank0/E024.asm

# the gate
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/gen_xdata_symbols.py --check
$ python3 ec/tools/xdata_register_map.py --check
$ python3 ec/tools/xdata_register_map.py --self-test

# the driver, which is not vendored here
$ git clone --filter=blob:none --no-checkout https://github.com/Wer-Wolf/uniwill-laptop.git ul
$ cd ul && git rev-parse 5a24248 && git checkout 5a24248
$ grep -n "MAIN_FAN_RPM\|SECOND_FAN_RPM\|TOUCHPAD_TOGGLE\|USB_CHARGING" uniwill-acpi.c
```

## What changed in the tree

- `ec/annotations/registers.yaml` — two new entries, `MAIN_FAN_RPM` over
  `0x0464`/`0x0465` and `SECOND_FAN_RPM` over `0x046C`/`0x046D`, each with all
  three reference-count keys; a note-only addition to `TRIGGER` (`0x0767`) for
  the `USB_POWERSHARE` bit-4 alias, and one to `OEM_4` (`0x07A6`) for the
  `TOUCHPAD_TOGGLE` bit-6 alias and its polarity. No existing `status:`,
  count, or name moved.
- `ec/ghidra/xdata-overrides.csv` — four rows, the hand-maintained escape hatch
  a multi-address entry needs (`gen_xdata_symbols.py` refuses to guess).
- `ec/ghidra/xdata-symbols.csv`, `ec/annotations/xdata-registers.csv`,
  `ec/annotations/xdata-clusters.csv` — **generated**, regenerated by their own
  tools, never hand-edited.
- `ec/annotations/ghidra-functions.csv` — two hand-decode comments said "no
  entry in `registers.yaml`" about `0x0464`/`0x0465` and `0x046C`/`0x046D`.
  That was true when written and false once this change landed, so both now
  name the entry instead. `build_ec_decompile.py --self-test` is what caught
  them; it refuses a comment that contradicts the register file. Four rows in
  the same file also move `name_basis` `code-shape` → `ec-register`
  (`0xBD5D`, `0xBD6B`, `0xDFDF`, `0xE024`), because their names cite XDATA
  addresses that are now in `registers.yaml` and the listing shows those
  addresses in a DPTR immediate — which is the rule `grade_name_basis.py`
  states. Applied with that tool's own `--apply`, not by hand;
  `grade_name_basis.py --check` is what caught it.
- `ec/tools/xdata_register_map.py` — the `named_in_tree` pin, and nothing else.
  The reasoning for the export decision below lives in this file rather than in
  a comment above that dict: a paragraph there moves every line pin in the
  repository, and `check_eq_guard_citations.py` and `test_check_doc_figure_pins.py`
  are two of the checks that read those pins.
- `ec/annotations/static-refs-audit.md` — §3's closing paragraph corrected in
  place, §3's table extended, and a new dated §10.
- `docs/findings.md` — the §3c clause and the §4d parenthetical corrected in
  place, with the wrong wording left readable.

No new tool, and nothing opened outside this repository.

**No decompiled `.c` was re-exported, and that is deliberate.** Running
`build_ec_decompile.py --mode export-only` does carry the four new names into
the committed text — the symbol table is applied to the project *copy* the
export makes, the mechanism #250's ORACLE block describes. Measured against
the parent commit it renames seven rows' `spelling` and changes no reference
count at all: −7/+7 distinct and −35/+35 references across the two halves.
Four of those seven are this issue's. **The other three, `0x078B`, `0x07A5`
and `0x0803`, are pre-existing staleness the export also sweeps up** — their
`xdata-symbols.csv` rows were committed long before this issue while the
committed decompile still spelled them `DAT_EXTMEM_*`, which is the defect
#250's block describes. Taking them here would put three renames nobody asked
for into this change and move the file-wide `extmem_raw` token count on the
strength of an export that is the opt-in tier rather than the gate.

None of that is needed for the address resolution: `xdata-symbols.csv` is the
layer Ghidra reads at export time, and the census's `name` column is populated
from it whether or not the tree spells the address that way — a property
`xdata_register_map.py --self-test` asserts directly. The export is left to
whichever run wants it, and this paragraph records the decision rather
than the consequence. Only `named_in_tree` moves as a result (190 → 194); the
`extmem_*` and `symbol_*` pins are unchanged, which `--self-test` confirms.