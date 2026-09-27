# Upstream PR body — GM7MG7P platform profile

**This file is a prepared body for a human to paste, not something any tool
in this repository posts.** No pull request, issue or comment has been opened
against `Wer-Wolf/uniwill-laptop` or anywhere else; see `CLAUDE.md`. The
cross-reference to upstream issue #7 in the third section is prose for the
person submitting it.

Everything between the two rules is the body itself.

---

## 1. Title

`platform/x86/uniwill-laptop: add a platform profile for the GM7MG7P`

## 2. What this does

**The driver has no platform-profile support, so this patch adds it** — a
`profile` and `profile_cycles` sysfs pair, a `platform_profile` callback on
`struct uniwill_device_descriptor`, and a `UNIWILL_OSD_PERFORMANCE_MODE_TOGGLE`
arm that cycles the profile instead of reporting `KEY_F14` on boards whose
descriptor carries a handler. The GM7MG7P descriptor is the first one to carry
one, and this diff is against `5a24248` on its own: the GM7MG7P descriptor and
the DMI row pointing at it do not exist there, and nothing already in the tree
is modified. On every other board the new `0xB0` arm falls through to the arm
below it, so nothing about today's behaviour changes anywhere.

**Apply this one, not the other GM7MG7P patch.** I have a second patch for
this board, against the same rev, that adds the same descriptor with the eight
feature bits and no profile, and the same DMI row. This one is the superset,
so the two are alternatives rather than a series: applied to one tree in
either order, the second one fails at the descriptor hunk, because
`gm7mg7p_descriptor` and that row are already there. If the smaller patch
reaches upstream first, drop this patch's descriptor and DMI row hunks and
rebase the rest onto them.

The three real modes on this board map as the issue asked:

| driver profile | firmware mode | `EC_ADDR_MANUAL_FAN_CTRL` | power limits from |
|---|---|---|---|
| `low-power` | Office | `FAN_MODE_USER \| FAN_MODE_HIGH` (0xA0) | the `0x0734-0x0736` block |
| `balanced` | Gaming | 0x00 | the `0x0730-0x0732` block |
| `performance` | Turbo | `FAN_MODE_TURBO` (0x10) | the `0x07A7-0x07A9` block |

Three things about that table are worth stating plainly.

**The mode byte alone does not move the power limits on this EC, so the handler
writes them too.** This is the part that is easy to get wrong by omission.
Holding `EC_ADDR_MANUAL_FAN_CTRL` at each of the three values and watching
`EC_ADDR_PL1_SETTING`, `EC_ADDR_PL2_SETTING` and `EC_ADDR_PL4_SETTING` moved
none of them, and the fan curve did not follow either; statically, none of the
29 firmware sites for that byte touches another address, and the per-mode
default blocks have no read site in the image at all. A handler that wrote only
the mode byte would report a new profile while the machine stayed in the old
one.

**No wattage is compiled in.** The limits are read out of the EC's own
per-mode default block and written back, so a board whose EC was programmed
differently follows its own EC rather than a constant in this file.

**Turbo is gated on `EC_ADDR_BIOS_INFO_3` (0x049F) bit 1, and deliberately not
on the existing `FAN_TURBO_SUPPORTED`.** `0x0742` reads `0x02` on this board,
so `FAN_TURBO_SUPPORTED` is clear while Turbo demonstrably works. I have not
reconciled the two bits and do not think this patch should — but a reviewer
should know the gate is not an oversight, and the new define is right beside
the old one in the source.

## 3. Cross-reference

This was developed against the driver at `5a24248`. Related discussion, for
whoever wants to follow it up rather than for a dependency: upstream issue #7.

## 4. Why it is written in this driver's own idiom, and what I would change

`dev_pm_platform_profile_register()` from `<linux/platform_profile.h>` is the
right home for this and I would rather it were there. The reason it is not in
this patch is a practical one worth stating before anyone finds it: it was
written without a kernel headers tree to compile against, so an API whose
current signature I could not check here was not something to guess at. The
enum carries the kernel's member names in the kernel's order, so moving the
attribute across is a translation of about twenty lines rather than a
redesign. If you would prefer that in the same patch, say so and it can be
done — it just needs to be built once.

## 5. What this does not do

- **The fan curve is not replayed, so the curve does not follow the mode.** The
  OEM service's curve handshake parks the EC with `EC_ADDR_AP_OEM` bit 0 clear,
  and that is the state in which the EC's own zeroing of the power limits runs
  — a path whose timing is unresolved. The driver holds that bit set from
  probe, and nothing in this patch clears it, which is what makes writing the
  limits without the curve safe. Adding the curve later is not a small
  addition; it has to resolve that overlap first. The mechanism is decoded
  rather than unknown, so the follow-up starts from it: EC handler at bank0
  `0x888D`, magic `0xFD`/`0xC9`, selector `0x0F5F` in 1..3 (1 = Turbo, 2 =
  Gaming, 3 = Office), two 48-byte CODE tables to `0x0F00` and `0x0F30`,
  selector 3 additionally split by `0x0782` bit 2.
- **The cTGP/DynamicBoost bytes `0x0743-0x0746` are not written.** They are
  issue #8 in the driver's own tracker, and this patch deliberately stays clear
  of the 25-vs-15-vs-5 W DynamicBoost disagreement, which is a cTGP-init
  question and not a profile one. The vendor writes identical GPU bytes in all
  three modes, so there is nothing per-mode for a profile to switch here.
- **Battery behaviour is not implemented.** The vendor writes PL1/PL2/PL4 = 0 on
  battery and what 0 means to this EC is untested, so the handler skips the
  limits write off AC rather than shipping an untested semantic as a feature.
- **`EC_ADDR_FAN_DEFAULT` is not renamed.** `0x0786` is the CPU TCC offset in
  this machine's DSDT (`APTC`/`APTN`) and in the vendor's own service, so the
  name is wrong here, but that is a separate change and bundling it makes this
  harder to review.
- **Fan Boost stays out of the mode byte.** The OSD owns bit 6 and adds it while
  boost is on; the profile writes bits 0-5 and 7 only.

## 6. What is unproven, in the interest of not overselling it

- **Whether the mode bits change fan behaviour at all is untested.** The
  measurement that showed the mode byte moves nothing else was taken near-idle,
  and the fan duty moved the same amount under a no-op control write, so what
  changed there was thermally. A profile switch here changes the power limits.
  Whether it also changes the curve is **not established**, and should be read
  as not established until somebody watches it under load.
- **This patch has been neither compiled nor loaded.** It was written against
  the source alone. Treat the first build as part of the review, and treat
  `profile_cycles` reading `low-power balanced performance` on the GM7MG7P as
  the first thing to check.

## 7. Testing

- `git apply --check` against `5a24248`: clean. Run on 2026-09-27 into an
  empty tree, from a fresh `git fetch --depth 1` of
  `5a24248f6422a0b673a47cbfd65e19a98eb4c8a9` whose `uniwill-acpi.c` is the
  `7a2eeae` blob this diff is written against:

  ```sh
  git apply --check -v uniwill-acpi-profile-gm7mg7p.patch
  Checking patch uniwill-acpi.c...
  Hunk #5 succeeded at 688 (offset 1 line).
  ...
  Hunk #16 succeeded at 3668 (offset 8 lines).
  ```

  Exit 0, every hunk accepted, no warning and no fuzz. Twelve of the sixteen
  hunks apply at a line offset from the one their `@@` header names, because
  the diff is hand-written rather than produced by `git diff`: a hunk is
  located by its context lines, that context still matched, and the diff adds
  lines only. Rebasing onto a tree where upstream has moved further will grow
  those offsets. Separately, note that this patch carries **no `index` line**,
  for the same reason it is hand-written — the base is the `Base commit:`
  header above, and `7a2eeae` is the blob at that rev. That is a check of the
  diff against the pinned source and nothing more; the last bullet is what is
  still not done.
- The regmap gates this touches were read off the source rather than assumed:
  `EC_ADDR_MANUAL_FAN_CTRL`, the three `EC_ADDR_PL*_SETTING` bytes,
  `EC_ADDR_BIOS_INFO_3` and the three default blocks are in
  `writeable_reg`/`readable_reg` as the patch adds them, and the mode byte and
  the three limit registers are declared `volatile` because the EC writes all
  four on its own — without that, a read would return the driver's own last
  write rather than what the EC believes.
- Not yet done, and the reason it is listed here rather than above: build it,
  load it, cycle it on the machine.

---

Everything below this line is context for the person submitting, not part of
the body. Every address, bit and value above is recorded row by row with its
evidence, including the two this repository grades `present-untested` and the
four the patch deliberately does not touch, in `profile-map.csv` beside this
file, and `tools/check_power_profile.py` fails if a row's value source becomes
a literal or a spelling stops matching the pinned upstream source.
