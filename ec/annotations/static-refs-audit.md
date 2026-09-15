# Per-image reference audit of every address in `registers.yaml`

Every `static_refs:` value in `registers.yaml` used to be a file-wide
`scan_refs.py` total, and the 256 KiB dump holds two unrelated 8051 programs
(`../README.md`, `lightbar-bat-flow.md` §2). A total therefore mixes references
made by the EC firmware with references made by the `ITE8850-PD` image, whose
XDATA map is its own — the conflation that had `LIGHTBAR_BAT_*` recorded as
present in firmware that references it zero times (`../../docs/findings.md`
§3a).

When this file was written, "whose XDATA map is its own" was an assumption
inherited from the two programs being separate, and is left standing above
as it was written. It has since been tested against the one address that
collides — see §4 — and survived, with the hedge that test carries.

This file audits all 29 addresses in `registers.yaml`, one table row each, so
the split is checkable rather than assertable. `registers.yaml` now carries
`static_refs_main_ec:` and `static_refs_pd_image:` on every entry — an entry
without them has not been audited — and `../tools/check_register_counts.py`
recomputes both from the committed image and fails on a mismatch.

**What a `0` here means.** "Not found by this method", never "absent". The
indirect-addressing blind spot documented in `../../docs/findings.md` §4c
belongs to `trace_xdata_refs.py` exactly as much as to `scan_refs.py`:
`0x07B9` is a byte Windows demonstrably writes with zero direct `MOV DPTR`
sites anywhere in the image. Nothing in this audit was measured on hardware.

## 1. Reproducing it

`main EC` is the EC firmware itself — the common area plus CODE banks 0 and 1,
file `0x00000`-`0x17FFF`. `PD` is the `ITE8850-PD` image at file `0x20000`.
The blank line `trace_xdata_refs.py` prints between addresses is stripped here
for length; nothing else is edited.

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 --counts-only \
    0x043E 0x044F 0x04A6 0x04A7 0x0726 0x0740 0x0741 0x0743 0x0744 0x0745 \
    0x0746 0x0748 0x0749 0x074A 0x074B 0x074E 0x0765 0x0766 0x0767 0x0768 \
    0x078C 0x07A6 0x07B9 0x07CC 0x07D0 0x07E2 0x07E3 0x07E4 0x07E5 \
  | grep -v '^$'
0x043E: 15 direct MOV DPTR site(s)  bank0=10  bank1=5
0x044F: 14 direct MOV DPTR site(s)  bank0=10  bank1=4
0x04A6: 7 direct MOV DPTR site(s)  bank0=1  bank1=2  pd-image=4
0x04A7: 2 direct MOV DPTR site(s)  bank0=1  bank1=1
0x0726: 0 direct MOV DPTR site(s)  none
0x0740: 1 direct MOV DPTR site(s)  bank0=1
0x0741: 35 direct MOV DPTR site(s)  bank0=30  bank1=5
0x0743: 7 direct MOV DPTR site(s)  bank0=7
0x0744: 1 direct MOV DPTR site(s)  bank0=1
0x0745: 1 direct MOV DPTR site(s)  bank0=1
0x0746: 1 direct MOV DPTR site(s)  bank0=1
0x0748: 0 direct MOV DPTR site(s)  none
0x0749: 0 direct MOV DPTR site(s)  none
0x074A: 0 direct MOV DPTR site(s)  none
0x074B: 0 direct MOV DPTR site(s)  none
0x074E: 4 direct MOV DPTR site(s)  bank0=2  common=2
0x0765: 0 direct MOV DPTR site(s)  none
0x0766: 7 direct MOV DPTR site(s)  bank0=5  bank1=2
0x0767: 10 direct MOV DPTR site(s)  bank0=10
0x0768: 8 direct MOV DPTR site(s)  bank0=5  bank1=3
0x078C: 7 direct MOV DPTR site(s)  bank0=7
0x07A6: 7 direct MOV DPTR site(s)  bank0=7
0x07B9: 0 direct MOV DPTR site(s)  none
0x07CC: 6 direct MOV DPTR site(s)  pd-image=6
0x07D0: 254 direct MOV DPTR site(s)  pd-image=254
0x07E2: 15 direct MOV DPTR site(s)  pd-image=15
0x07E3: 9 direct MOV DPTR site(s)  pd-image=9
0x07E4: 4 direct MOV DPTR site(s)  pd-image=4
0x07E5: 10 direct MOV DPTR site(s)  pd-image=10

$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
19 entries / 29 addresses: every static_refs, static_refs_main_ec and static_refs_pd_image reproduced from ec/firmware/GMxMGxx_11.800
```

## 2. The audit table

| addr | register | total | main EC | PD | status before | status after |
|---|---|---:|---:|---:|---|---|
| `0x043E` | `CPU_TEMP` | 15 | 15 | 0 | confirmed-working | confirmed-working |
| `0x044F` | `GPU_TEMP` | 14 | 14 | 0 | confirmed-working | confirmed-working |
| `0x04A6` | `BAT_CYCLE_COUNT` | 7 | 3 | 4 | confirmed-working | confirmed-working |
| `0x04A7` | `BAT_CYCLE_COUNT` | 2 | 2 | 0 | confirmed-working | confirmed-working |
| `0x0726` | `OEM_9` | 0 | 0 | 0 | absent | absent |
| `0x0740` | `PROJECT_ID` | 1 | 1 | 0 | confirmed-working | confirmed-working |
| `0x0741` | `AP_OEM` | 35 | 35 | 0 | confirmed-working | confirmed-working |
| `0x0743` | `CTGP_DB_CTRL` | 7 | 7 | 0 | present-untested | present-untested |
| `0x0744` | `CTGP_DB_OFFSET` | 1 | 1 | 0 | present-untested | present-untested |
| `0x0745` | `CTGP_DB_OFFSET` | 1 | 1 | 0 | present-untested | present-untested |
| `0x0746` | `CTGP_DB_OFFSET` | 1 | 1 | 0 | present-untested | present-untested |
| `0x0748` | `LIGHTBAR_AC_CTRL` | 0 | 0 | 0 | confirmed-not-this-mechanism | confirmed-not-this-mechanism |
| `0x0749` | `LIGHTBAR_AC_RED` | 0 | 0 | 0 | confirmed-not-this-mechanism | confirmed-not-this-mechanism |
| `0x074A` | `LIGHTBAR_AC_GREEN` | 0 | 0 | 0 | confirmed-not-this-mechanism | confirmed-not-this-mechanism |
| `0x074B` | `LIGHTBAR_AC_BLUE` | 0 | 0 | 0 | confirmed-not-this-mechanism | confirmed-not-this-mechanism |
| `0x074E` | `BIOS_OEM` | 4 | 4 | 0 | confirmed-working | confirmed-working |
| `0x0765` | `SUPPORT_1` | 0 | 0 | 0 | absent | absent |
| `0x0766` | `SUPPORT_2` | 7 | 7 | 0 | present-untested | present-untested |
| `0x0767` | `TRIGGER` | 10 | 10 | 0 | confirmed-working | confirmed-working |
| `0x0768` | `SWITCH_STATUS` | 8 | 8 | 0 | confirmed-working | confirmed-working |
| `0x078C` | `KBD_STATUS` | 7 | 7 | 0 | present-untested | present-untested |
| `0x07A6` | `OEM_4` | 7 | 7 | 0 | confirmed-working-partially | confirmed-working-partially |
| `0x07B9` | `CHARGE_CTRL` | 0 | 0 | 0 | unknown-not-absent | unknown-not-absent |
| `0x07CC` | `USB_C_POWER_PRIORITY` | 6 | 0 | 6 | present-untested | present-untested |
| `0x07D0` | `BATTERY_CHARGE_LIMIT_DOWN` | 254 | 0 | 254 | unknown-not-absent | unknown-not-absent |
| `0x07E2` | `LIGHTBAR_BAT_CTRL` | 15 | 0 | 15 | unknown-not-absent | unknown-not-absent |
| `0x07E3` | `LIGHTBAR_BAT_RED` | 9 | 0 | 9 | unknown-not-absent | unknown-not-absent |
| `0x07E4` | `LIGHTBAR_BAT_GREEN` | 4 | 0 | 4 | unknown-not-absent | unknown-not-absent |
| `0x07E5` | `LIGHTBAR_BAT_BLUE` | 10 | 0 | 10 | unknown-not-absent | unknown-not-absent |

**No status changed.** The three `present-untested` entries resting on a count
alone — `SUPPORT_2` (`0x0766`), `CTGP_DB_CTRL / OFFSET` (`0x0743`-`0x0746`) and
`KBD_STATUS` (`0x078C`) — are EC-side in full, so the evidence they rest on
survives the split. `SUPPORT_2` was the flagged candidate for a correction and
is not one: its 7 sites are `bank0=5`, `bank1=2`, no PD image. `USB_C_POWER_PRIORITY`
(`0x07CC`) is still labelled `present-untested` on a PD-only count; its entry
already says the count is not EC-side evidence, and re-grading it is a
vocabulary question this audit deliberately does not open.

Two results worth naming:

- **`0x04A6` (`BAT_CYCLE_COUNT`) is the only split address outside
  `0x0700`-`0x07FF`**: 3 of its 7 sites are in the EC image and 4 in the PD
  image. That it has PD-image sites at all was already noted in
  `docs/findings.md` §3a ("has some in the PD image too"); the 3/4 split and
  the "only one outside the range" part are new here. Its status is
  confirmed-working from a live read (445 cycles), and a live confirmation is
  not weakened by where static sites sit. What the PD image does with its own
  `0x04A6` is untouched by this and unanswered. (Answered since, in
  `pd-xdata-overlap.md`: it is the base of strided address arithmetic, not a
  counter. §4.)
- **The PD contamination reaches seven addresses** — `0x04A6`, `0x07CC`,
  `0x07D0`, `0x07E2`-`0x07E5` — and none of the seven is a new discovery:
  `0x07E2`-`0x07E5` are `lightbar-bat-flow.md` §1 and §3, `0x07D0` and
  `0x07CC` are §6 of that file, and `0x04A6` is `docs/findings.md` §3a. What
  this audit adds is that the set is exactly these seven and that each count
  is machine-checkable: every other address in the file is either wholly
  EC-side or has no sites at all. That is a measurement over the 29
  addresses `registers.yaml` holds; it is not a statement about addresses
  nobody has looked at.

## 3. The `findings.md` §4d validation subset

§4d says the static-scan method was checked against **20 registers with
independently confirmed live behaviour** (15 working, 5 not) and predicted all
20 correctly. That set is not enumerated register-by-register anywhere in this
repo, so this table cannot claim to *be* those 20. What it is: every address in
`registers.yaml` whose status comes from live observation — 14 addresses, 10
graded live-working and 4 live-negative.

| addr | register | live verdict | main EC | PD | consistent with §4d |
|---|---|---|---:|---:|---|
| `0x043E` | `CPU_TEMP` | works (vs. coretemp) | 15 | 0 | yes — referenced, works |
| `0x044F` | `GPU_TEMP` | works (vs. nvidia-smi) | 14 | 0 | yes |
| `0x04A6` | `BAT_CYCLE_COUNT` | works (445 cycles) | 3 | 4 | yes |
| `0x04A7` | `BAT_CYCLE_COUNT` | works | 2 | 0 | yes |
| `0x0740` | `PROJECT_ID` | works (reads `0x0F`) | 1 | 0 | yes |
| `0x0741` | `AP_OEM` | works (profile gate) | 35 | 0 | yes |
| `0x074E` | `BIOS_OEM` | works (Fn+F10) | 4 | 0 | yes |
| `0x0767` | `TRIGGER` | works (flips `0x0768`) | 10 | 0 | yes |
| `0x0768` | `SWITCH_STATUS` | works (Super key dies) | 8 | 0 | yes |
| `0x07A6` | `OEM_4` | partially (taper only) | 7 | 0 | yes |
| `0x0748` | `LIGHTBAR_AC_CTRL` | no effect on write | 0 | 0 | yes — unreferenced, inert |
| `0x0749` | `LIGHTBAR_AC_RED` | no effect on write | 0 | 0 | yes |
| `0x074A` | `LIGHTBAR_AC_GREEN` | no effect on write | 0 | 0 | yes |
| `0x074B` | `LIGHTBAR_AC_BLUE` | no effect on write | 0 | 0 | yes |

So §3a's prose claim — "every live-confirmed register in §2 does have
references in the EC image" — holds for all 10 live-working addresses this
repo records an address for, `0x04A6` included, and the 4 live-negative ones
have zero references in either image. The claim is measured now rather than
asserted.

`0x07B9` is deliberately not a row above. It is the counter-example, not a
validation case: a live-relevant address with 0 sites in both images, whose
`absent` reading §4c retracted. It is why every zero in this file reads
"not found by this method".

**What this subset cannot cover, and why.** §4d's 20 include features whose EC
addresses are not recorded anywhere in this repository:
`PRIMARY_FAN`/`SECONDARY_FAN`, `TOUCHPAD_TOGGLE` and `USB_POWERSHARE` appear in
`../../docs/findings.md` §2 by feature name only, and `grep` over `linux/`
finds no address for them — the `uniwill-laptop` source is not vendored here,
only a patch and a `BASE_COMMIT` (`../../linux/patches/`). Filling those rows
would mean inventing addresses, so they are left out and named here instead.
Resolving them needs the driver source pulled at that commit and its address
defines read off; that is a follow-up issue, not a gap quietly dropped.

## 4. The separate-maps premise, tested

`0x04A6` was the lever: the only address in §2's table with sites in both
images, so the only one where "the PD image's `0x04A6` is not the EC's" could
be checked rather than assumed. `pd-xdata-overlap.md` decodes all seven sites
and surveys both images across `0x0400`-`0x07FF`. **Verdict: the maps look
independent as far as that evidence goes** — the EC image maintains
`0x04A6`/`0x04A7` as a 16-bit counter incremented together, while all four PD
sites use `0x04A6` as the base of strided address arithmetic and the PD image
never references `0x04A7` at all — with the hedge that static code shape is
not memory topology, and that only a runtime observation on the machine can
tell a genuinely separate map from two programs fighting over one.

No status in `registers.yaml` changed, and none of the `unknown-not-absent`
gradings is re-read on the strength of this. What that file adds for §2's
framing is that it is now a tested assumption rather than an untested one,
and that 40 of the span's 1024 addresses collide between the images — so
`0x04A6` was never special, only the only collision this audit's 29 addresses
happened to include.
