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
recomputes both from the committed image and fails on a mismatch. §5 takes the
same 29 addresses one level further and classifies what each site *does*, from
`../tools/register_ref_table.py`, which re-derives the split and the access
classes in one pass.

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

## 5. Access direction per address

A count says a site exists; it does not say the site accesses a register. Two
things inflate a `MOV DPTR,#imm16` total without being an XDATA access at all:
the instruction also builds **CODE** pointers (`movc a,@a+dptr`, `jmp @a+dptr`
into a string or jump table — the boundary `ec-0x07d0-sites.md` §5 wrote down),
and a site may hand DPTR to a subroutine, where nothing at the site says which
direction the access has. This section classifies all 29 addresses' sites so
those populations are visible rather than averaged into a number.

**What a class does and does not mean.** `write` means an instruction stores to
the address; it is not evidence the EC acts on the value — only a live
behavioural test is (`../../docs/findings.md` §4a). `read` likewise means an
instruction loads it. `handoff` is *unresolved*, not absent: the callee very
likely performs the access, and `ec-0x07d0-sites.md` §3 resolved 79 of them one
level deeper by decoding the callee's first instruction, which this table does
not do by default. `register_ref_table.py --callee-depth 1` now does it for
every address, splitting the column into `handoff->read`/`write`/`r+w`/
`unresolved` (§5.2); the transcript pasted below is the depth-0 output, which
is unchanged by that option. `none` ("no movx in window") is the weakest cell in
the table and means only that the 8-instruction walk ended — usually at a
branch — before any `movx`; see the three EC-side examples below. A `movc` or
`jmp @a+dptr` class is the one that subtracts from a count's meaning: it says
the site is about CODE at that number, not a register. Nothing here was
measured on hardware.

```console
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800
| addr | register | total | main EC | PD | read | write | r+w | movc | jmp | handoff | none |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `0x0740` | `PROJECT_ID` | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| `0x0741` | `AP_OEM` | 35 | 35 | 0 | 25 | 0 | 10 | 0 | 0 | 0 | 0 |
| `0x0743` | `CTGP_DB_CTRL / OFFSET` | 7 | 7 | 0 | 5 | 0 | 2 | 0 | 0 | 0 | 0 |
| `0x0744` | `CTGP_DB_CTRL / OFFSET` | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x0745` | `CTGP_DB_CTRL / OFFSET` | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x0746` | `CTGP_DB_CTRL / OFFSET` | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x074E` | `BIOS_OEM` | 4 | 4 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 |
| `0x0765` | `SUPPORT_1` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x0766` | `SUPPORT_2` | 7 | 7 | 0 | 5 | 0 | 2 | 0 | 0 | 0 | 0 |
| `0x0767` | `TRIGGER` | 10 | 10 | 0 | 8 | 0 | 2 | 0 | 0 | 0 | 0 |
| `0x0768` | `SWITCH_STATUS` | 8 | 8 | 0 | 2 | 1 | 3 | 0 | 0 | 0 | 2 |
| `0x0726` | `OEM_9` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x07A6` | `OEM_4` | 7 | 7 | 0 | 3 | 0 | 4 | 0 | 0 | 0 | 0 |
| `0x07B9` | `CHARGE_CTRL` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x07D0` | `BATTERY_CHARGE_LIMIT_DOWN` | 254 | 0 | 254 | 157 | 8 | 2 | 0 | 0 | 79 | 8 |
| `0x0748` | `LIGHTBAR_AC_CTRL / RED / GREEN / BLUE` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x0749` | `LIGHTBAR_AC_CTRL / RED / GREEN / BLUE` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x074A` | `LIGHTBAR_AC_CTRL / RED / GREEN / BLUE` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x074B` | `LIGHTBAR_AC_CTRL / RED / GREEN / BLUE` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x07E2` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 15 | 0 | 15 | 7 | 4 | 0 | 0 | 0 | 4 | 0 |
| `0x07E3` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 9 | 0 | 9 | 2 | 2 | 0 | 0 | 0 | 5 | 0 |
| `0x07E4` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 4 | 0 | 4 | 3 | 1 | 0 | 0 | 0 | 0 | 0 |
| `0x07E5` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 10 | 0 | 10 | 5 | 3 | 0 | 0 | 0 | 2 | 0 |
| `0x078C` | `KBD_STATUS` | 7 | 7 | 0 | 4 | 0 | 3 | 0 | 0 | 0 | 0 |
| `0x07CC` | `USB_C_POWER_PRIORITY` | 6 | 0 | 6 | 3 | 2 | 1 | 0 | 0 | 0 | 0 |
| `0x043E` | `CPU_TEMP` | 15 | 15 | 0 | 14 | 0 | 0 | 0 | 0 | 0 | 1 |
| `0x044F` | `GPU_TEMP` | 14 | 14 | 0 | 12 | 2 | 0 | 0 | 0 | 0 | 0 |
| `0x04A6` | `BAT_CYCLE_COUNT` | 7 | 3 | 4 | 1 | 1 | 0 | 0 | 0 | 5 | 0 |
| `0x04A7` | `BAT_CYCLE_COUNT` | 2 | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
19 entries / 29 addresses: class buckets sum to the site count and main + PD to the file-wide total for every address
```

`--csv` writes one row per site (`addr,register,file_offset,region,runtime,class,window`)
so the table above is a group-by over committed-image data rather than a
number to be taken on trust; the tool exits non-zero if the class buckets for
any address fail to sum to its site count, or if main + PD fails to sum to the
file-wide total.

### 5.1 No CODE pointer contaminates any of the 29 — and the classifier can see one

**Null result: the `movc` and `jmp` columns are zero for every address.** That
extends `ec-0x07d0-sites.md` §5's finding, which covered only `0x07D0`'s 254,
to all 29 addresses `registers.yaml` holds. No count in this repo is inflated
by a string-table or jump-table pointer by this method.

A column of zeroes is also what a classifier that cannot see the thing would
print, so the branch was checked against sites that do have it. Image-wide
there are 54 such sites across 48 addresses, none of them an address in
`registers.yaml`, and `r2 -a 8051` agrees with the decode on both shapes:

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa6a4; pd 4' /tmp/bank0.bin
            0x0000a6a4      9063be         mov dptr, #0x63be
            0x0000a6a7      93             movc a, @a+dptr
            0x0000a6a8      901803         mov dptr, #0x1803
            0x0000a6ab      f0             movx @dptr, a
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x1051; pd 4' /tmp/bank0.bin
            0x00001051      901100         mov dptr, #0x1100
            0x00001054      73             jmp @a+dptr
            0x00001055      0a             inc r2
            0x00001056      1e             dec r6
```

`0x63BE` is the canonical shape of the blind spot: a `90 63 be` that a count of
"references to XDATA `0x63BE`" would have collected, and that is a table read
in CODE. The two `movx` controls check the other direction — that an ordinary
XDATA site is still classified as one:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x879d; pd 4' /tmp/bank0.bin
            0x0000879d      900741         mov dptr, #0x0741
            0x000087a0      e0             movx a, @dptr
            0x000087a1      4420           orl a, #0x20
            0x000087a3      f0             movx @dptr, a
$ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x3478; pd 2' /tmp/pd.bin
            0x00003478      9007d0         mov dptr, #0x07d0
            0x0000347b      e0             movx a, @dptr
```

(the first is one of `0x0741`'s ten `r+w` rows, the second the `0x07D0` read
`ec-0x07d0-sites.md` §4 decodes).

### 5.2 Where the population is not mostly `movx`

Five addresses have a non-`movx` share worth naming. None of them is a `movc`
case; all are unresolved handoffs, and an unresolved handoff is not evidence of
absence — the callee is where the access is:

| addr | register | non-`movx` sites | which image |
|---|---|---|---|
| `0x04A6` | `BAT_CYCLE_COUNT` | 5 of 7 (handoff) | 4 PD, 1 `bank1` |
| `0x07E3` | `LIGHTBAR_BAT_RED` | 5 of 9 (handoff) | all PD |
| `0x07D0` | `BATTERY_CHARGE_LIMIT_DOWN` | 87 of 254 (79 handoff, 8 `none`) | all PD |
| `0x07E2` | `LIGHTBAR_BAT_CTRL` | 4 of 15 (handoff) | all PD |
| `0x07E5` | `LIGHTBAR_BAT_BLUE` | 2 of 10 (handoff) | all PD |

`0x07D0`'s row is the one already resolved a level deeper: `ec-0x07d0-sites.md`
§3 decodes the 25 callees and lands on 229 reads / 15 writes / 2
read-modify-writes, so its 79 handoffs are unresolved *by this table*, not
unresolved in this repo. `0x04A6`'s four PD handoffs are likewise already
decoded, in `pd-xdata-overlap.md` §3 — every one of them calls the Keil
`DPTR += A×B` helper at `0x10BC` or a variant of it, which is why those sites
use the address as an arithmetic base and never touch the byte.
(That file's §5.4 also checked `0x04A6` for CODE pointers by hand and found
none, so one cell of §5.1's zero column was already established independently
of this tool.)

The `LIGHTBAR_BAT_*` handoffs have since been chased too, and the tool does
the chasing rather than another hand table — `--callee-depth 1` re-buckets
every handoff in this section by what the callee's own entry point does:

```console
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1 \
  | grep -E '0x04A6|0x07D0|0x07E2|0x07E3|0x07E5'
| `0x07D0` | `BATTERY_CHARGE_LIMIT_DOWN` | 254 | 0 | 254 | 157 | 8 | 2 | 0 | 0 | 72 | 7 | 0 | 0 | 8 |
| `0x07E2` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 15 | 0 | 15 | 7 | 4 | 0 | 0 | 0 | 2 | 1 | 0 | 1 | 0 |
| `0x07E3` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 9 | 0 | 9 | 2 | 2 | 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 |
| `0x07E5` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 10 | 0 | 10 | 5 | 3 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| `0x04A6` | `BAT_CYCLE_COUNT` | 7 | 3 | 4 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 4 | 0 |
```

(columns after `jmp` are `handoff->read`, `handoff->write`, `handoff->r+w`,
`handoff->unresolved`, `none`.) Nine of the eleven `LIGHTBAR_BAT_*` handoffs
resolve — 3 to a callee that loads, 6 to one that stores — and the remaining
two hand DPTR on a second time, which stays `handoff->unresolved` because
depth 2 is not attempted. `lightbar-bat-flow.md` §3.4 carries the per-site
rows and §3.5 decodes each of the eight callees against `r2 -a 8051`. It is
still a PD-image question, not an EC-side one, and not a `status:` question
either way.

**The two rows already resolved by hand are the cross-check, and the tool
agrees with both.** `0x07D0`'s 79 come out 72 read / 7 write, exactly the
split `ec-0x07d0-sites.md` §3 reached by hand. `0x04A6`'s single EC-side
handoff comes out a write — the `0x888C` 16-bit store `pd-xdata-overlap.md` §2
decodes — and its four PD-image ones stay unresolved, which is that file's §3
result in the tool's vocabulary: they call the `0x10BC` `DPTR += A × B` family,
which never dereferences DPTR, so there is no direction to report. Neither of
those files needed a correction, and neither was edited for this.

`0x04A6` is also the only one of the five with an EC-side non-`movx` site, at
`bank1` runtime `0xDFD0`: it calls `0x888C`, which `pd-xdata-overlap.md` §2
decodes as the 16-bit store of `R1`/`R2` into `0x04A6`/`0x04A7`. So that cell
is a write one level down, and the EC-side reading of the entry is unchanged.

That decode picks bank 1's bytes at `0x888C` because `offset_for_runtime()`
assumes a call from a bank stays in that bank, and
[`bank-call-audit.md`](bank-call-audit.md) is the enumeration of what that
assumption covers. It does not overturn this row — no direct cross-bank call
was found anywhere in the image by that method, and the linker's own
cross-bank path is an indirect trampoline — but it does place this site in the
audit's *ambiguous* population: bank 0 also holds non-erased bytes at `0x888C`,
a different instruction sequence that never dereferences the handed-over DPTR
(§6 of that file lists both). So the `handoff->write` verdict here rests on the
same-bank assumption plus its agreement with `pd-xdata-overlap.md` §2's hand
decode, not on anything that distinguishes the two banks at the call site.

Note what the table does *not* show: no EC-side address is handoff-dominated.
Every main-EC site behind a `present-untested` or `confirmed-working` grading
resolves to a `movx` at the site itself, except that one handoff and the three
in §5.3.

### 5.3 What a `none` cell actually is

Three EC-side sites classify as "no `movx` in window", and all three are the
walk giving up at a branch rather than a site that does nothing:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa39c; pd 5' /tmp/bank0.bin
            0x0000a39c      900768         mov dptr, #0x0768
        ┌─< 0x0000a39f      30e606         jnb acc.6, 0xa3a8
        │   0x0000a3a2      e0             movx a, @dptr
        │   0x0000a3a3      54fd           anl a, #0xfd
        │   0x0000a3a5      f0             movx @dptr, a
```

`0x0A848` (`0x0768`) is the same shape behind `cjne a,#0xa5`. `0x0E066`
(`0x043E`) is the other idiom: a chain that picks a DPTR per sensor
(`0x043E`, `0x043F`, …) and `sjmp`s to one shared load at `0xE091`, so the
read is at the jump target rather than in the window:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xe091; pd 1' /tmp/bank0.bin
            0x0000e091      e0             movx a, @dptr
```

All three sites
do access the register; the branch is simply where a linear walk has to give
up. `none` means "this method stopped", and reading
it as "this site does not access the register" would be exactly the
`docs/findings.md` §4c error in miniature. Eight more `none` cells sit in
`0x07D0`'s PD population and are accounted for in `ec-0x07d0-sites.md` §3
(seven `lcall 0xF739 ; mov dptr,#0x07d0 ; ret`, one `jnz`).

**No `status:` value changed here, and no `static_refs*` number moved** —
`check_register_counts.py` re-verifies all three counts per address and is the
guard on that. Issue #32 owns the grading question this table feeds.

## 6. `0x07D1` added to `registers.yaml` (2026-09-23, issue #131)

`0x07D1` (`DBD2`) joined the file when the `0x07D0` entry was re-graded —
it is the other half of the pair the DSDT's `T1WR` `Arg0 == 0x1173` branch
writes, and the half the vendor stack has no name for at all. Two
consequences for this file, both stated here rather than by editing the
sections above:

- **§2 and §5 are a 29-address snapshot, taken when this file was written.**
  `registers.yaml` has held more addresses since, and holds 57 now. The
  tables were not extended address by address as that happened — they
  record one pass over one set — and they are not extended here either.
  The guard for every address in the file, present and later, is
  `../tools/check_register_counts.py`, which recomputes all three counts per
  address from the committed image and is in the agent gate. The rule this
  file states in its own header is that an entry without the split keys has
  not been audited, and `0x07D1` carries them.
- **The `0x07D0` rows above show the name that entry had then**,
  `BATTERY_CHARGE_LIMIT_DOWN`. The re-grade renamed it `DBD1` in
  `registers.yaml` — the DSDT's own name, with the vendor constant kept in
  the parenthetical — and `ec/ghidra/xdata-symbols.csv` follows it, because
  that file is generated from `registers.yaml` and is never hand-edited. No
  count, no image split and no `status:` value moved with the rename. The
  reasoning is in `../../docs/findings.md` §4o and in the entry's note.

The new row's own numbers, from the two tools above and reproducible from
the committed image (as in §1, the blank line `trace_xdata_refs.py` prints
between addresses is stripped here):

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 --counts-only 0x07D0 0x07D1
0x07D0: 254 direct MOV DPTR site(s)  pd-image=254
0x07D1: 76 direct MOV DPTR site(s)  pd-image=76

$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --markdown \
  | grep -E '0x07D0|0x07D1'
| `0x07D0` | `DBD1` | 254 | 0 | 254 | 157 | 8 | 2 | 0 | 0 | 79 | 8 |
| `0x07D1` | `DBD2` | 76 | 0 | 76 | 46 | 13 | 0 | 0 | 0 | 17 | 0 |

$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
30 entries / 57 addresses: every static_refs, static_refs_main_ec and static_refs_pd_image reproduced from ec/firmware/GMxMGxx_11.800
```

`0x07D1` is the same shape as `0x07D0`: every site in the PD image, none in
the EC firmware, no CODE pointer, and 17 handoffs that the table leaves
unresolved for the reason §5.2 gives. Unlike `0x07D0`, none of its sites has
been walked site by site in a file of its own — `ec-0x07d0-sites.md` covers
`0x07D0` only, and a walk of `0x07D1` is not done here. That is a real gap
in the PD-image question and it is left open rather than papered over; the
`0`-means-"not found by this method" caveat at the top of this file applies
to the EC-side column in the same way it does to `0x07D0`'s.

**Correction (issue #185, 2026-09-24), leaving the sentence above as it was
written.** The gap is now closed: `ec-0x07d1-sites.md` walks all 76 site by
site, with `ec-0x07d1-sites.csv` beside it, by the method
`ec-0x07d0-sites.md` used. The correction is to this file's closing sentence
only — nothing else in §6 moves, and no count, image split or `status:` value
changed with the walk.

The 17 handoffs are no longer unresolved by the repo, which is what §5.2's
verdict was about: decoding the 8 callees one level deeper gives 14 read and
3 write, so `--callee-depth 1` now reports
`handoff->read 14 / handoff->write 3 / handoff->unresolved 0` and the
population resolves to 60 read / 16 write with nothing left over. The
site's own summary in the new file is that all 17 resolve, where this
table's `handoff` column is a statement about the table and not the code —
the same relationship §5.2 records for the `0x07D0` and `0x04A6` rows.

Two things the walk found that the count-based rows above could not show, and
which are recorded in full in the new file rather than summarised here: the
`CODE`-pointer question for this address is a tighter one than for `0x07D0`
(CODE `0x07D1` is the `+` of the `"+INF"` string, a live string start rather
than the NUL terminator that `0x07D0`'s is) and the answer is still zero —
both the `movc` and `jmp` columns hold; and five of the 76 walk past their own
byte through `inc dptr`, four of them treating `0x07D1`+`0x07D2` as one
16-bit little-endian quantity, a shape the single-byte class in §2's
vocabulary scores as one access. The last point is why the `read`/`write`
columns here are counts of *instructions storing or loading at the site*, not
of bytes reached.

## 7. `0x075B`/`0x075C` added to `registers.yaml` (2026-09-24, issue #123)

`MAIN_FAN_L_DUTY` (`0x075B`) and `MAIN_FAN_R_DUTY` (`0x075C`) joined the file
as the EC's published fan-duty bytes — the vendor's
`ADDR_EC_MAIN_FAN_L/R_DUTY_BYTE`, read and halved by `FanInfo` and never
written by it. They had been carried as a bare "fan PWM 0x075B/0x075C" aside
inside the `0x0751` note, with no entry, no `status:` and no count. The
naming, the status reasoning and the duty-versus-PWM distinction are in those
entries; what belongs here is the three counts, the site classes, and why the
tables above are not extended.

Three consequences for this file, on the same terms §6 set out:

- **§2 and §5 stay a 29-address snapshot.** Not extended here either. The
  guard for these two, as for `0x07D1`, is `../tools/check_register_counts.py`,
  which walks every entry, requires all three split keys, recomputes each
  count from the committed image and fails on a mismatch. Both new entries
  carry the split.
- **§5.2 does not get a row, and the reason is the tool's, not the bar's.**
  `0x075C` does have a non-`movx` site — one of three is a DPTR handoff, which
  is 1 of 3 against §5.2's smallest listed share of 2 of 10 — so the
  arithmetic alone would have put it in that table. But every row in §5.2 is
  an *unresolved* handoff, and this one resolves: `--callee-depth 1` reads
  `0xBC3F`'s own entry point, whose first instruction is `movx @dptr,a`, and
  buckets it `handoff->write`. With that resolved, both addresses are 3 of 3
  `movx` writes with no `none` cell and nothing left over, so they have no
  non-`movx` share to name. A row here would have said the opposite of the
  table's own thesis.
- **These are not the fan table's routines.** The issue asked whether the
  writer sites are the same routines as the fan-table readers, and the answer
  is that no such routine exists to be the same as: `0x0F00` and `0x0F20` have
  zero direct `MOV DPTR` sites anywhere in the image, so the table is reached
  indirectly. `0x075B`/`0x075C` are published from the EC's own scratch bytes
  `0x1804`/`0x1809` instead, through the helper at `0xBB22`/`0xBB28`. That
  leaves §6 of `manual-fan-ctrl-0751.md` exactly as open as it was.

The rows' own numbers, from the tools above and reproducible from the committed
image (as in §1, the blank line `trace_xdata_refs.py` prints between addresses
is stripped here):

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 --counts-only 0x075B 0x075C
0x075B: 3 direct MOV DPTR site(s)  bank0=3
0x075C: 3 direct MOV DPTR site(s)  bank0=3

$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1 --markdown \
  | grep -E '0x075B|0x075C'
| `0x075B` | `MAIN_FAN_L_DUTY` | 3 | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x075C` | `MAIN_FAN_R_DUTY` | 3 | 3 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |

$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
71 entries / 103 addresses: every static_refs, static_refs_main_ec and static_refs_pd_image reproduced from ec/firmware/GMxMGxx_11.800
```

The `0` means at the top of this file still applies to the positive counts: 3
is a direct `MOV DPTR` site count, not a count of register accesses, and the
`0x07B9` blind spot is unchanged. `0x0786`, in the same `0x0700` neighbourhood,
remains the live naming conflict its own entry records — `EC_ADDR_FAN_DEFAULT`
upstream against APTC/APTN in the DSDT and 3.1.39.0, and
`ADDR_L1_PWM_DEFAULT_MYFAN3` in ECSpec. That conflict is a reason to keep
sweeping `0x0700`-`0x07FF` rather than trust any one name, and it is why
§4 of `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` keeps its sweep
instruction after the "unconfirmed" wording came out.

