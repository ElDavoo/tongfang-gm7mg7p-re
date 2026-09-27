# A `0x0751`-only platform profile would report a new mode and not move the machine's power limits

(2026-09-27, issue #102. Prepared against upstream `Wer-Wolf/uniwill-laptop` at
`5a24248` ("Bump minimum supported kernel version to 7.2"), fetched and quoted
at that rev. No image is opened and no register is read back by this work: the
EC claims below are the ones already recorded in `ec/annotations/registers.yaml`
and in the 2026-09-23 captures under `evidence/ec-watch/`, cited where each is
used. The artefact this write-up describes is
[`linux/patches/gm7mg7p-power-profile/`](../linux/patches/gm7mg7p-power-profile/);
nothing in it has been compiled, and nothing has been loaded on a machine.)

## The finding

**Writing `0x0751` on this EC changes nothing else, so a platform profile that
wrote only `0x0751` would change the label on the machine and none of its
behaviour.** Every value the profile needs is readable from an EC default
block, so the profile can be written without a hard-coded wattage — but it
cannot be written without the PL replay that #99's answer made mandatory.

This is not a new result; it is the negative answer to #99, applied to a
deliverable. It is written up here because the *shape* of the conclusion is the
part that is easy to get wrong: the natural reading of "which registers does
the handler need" is "the mode byte, plus whatever the EC turns out to do
with it", and the measurement says the answer is the opposite — the EC does
nothing with it, and the host has to do all of it.

## What was measured, and where each half lives

| half | what it found | where |
|---|---|---|
| static | All 29 firmware sites that touch `0x0751` touch no other XDATA byte. They are bit tests and read-modify-writes of bits 4-7. The per-mode default blocks (`0x0730-0x0737`, `0x07A7-0x07AA`) have **no read site at all** in the image, and the EC's only found writer of `0x0783-0x0785` is gated on `AP_OEM` (`0x0741`) bit 0 rather than on the mode, and writes zero. | `ec/annotations/manual-fan-ctrl-0751.md` §2 (the 29 sites), §4 (the one `0x0783-0x0785` write) and §5 (the default blocks); `ec/annotations/registers.yaml`, `MANUAL_FAN_CTRL` |
| live | On AC, from Turbo, service running, `0x0751` was set to each of `0xA0`/`0x00`/`0x10` and held 20 s while `0x0783-0x0787`, `0x07C5`, `0x07C6`, `0x0743-0x0746` and `0x0F00-0x0F5F` were watched. Nothing else moved. A silent write persisted — the service, not event-triggered, did not revert it. | `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; `evidence/ec-watch/2026-09-23-0751-isolation.txt` |

Both halves agree, which is the only reason the conclusion above is worth
stating as a finding rather than as a prediction. The static half is a
negative and this repository's own caveat applies to it in full: all 29 sites
found is **"not found by this method"**, and the method is blind to indirect
access, which `0x0F00` proves it is (§6 of the same file — the EC builds
`DPH` at run time and no direct `MOV DPTR` site exists for it). The live half
is what carries the claim, and it is a *negative* live result: the prediction
was "the EC will derive the bundle", and the run says it does not.

## The mapping, and where each value comes from

| driver profile | firmware mode | `0x0751` | PL1/PL2/PL4 replayed from |
|---|---|---|---|
| `low-power` | Office | `FAN_MODE_USER \| FAN_MODE_HIGH` (0xA0) | `0x0734-0x0736` |
| `balanced` | Gaming | 0x00 | `0x0730-0x0732` |
| `performance` | Turbo | `FAN_MODE_TURBO` (0x10) | `0x07A7-0x07A9` |

Three of those four columns are the firmware's own encoding rather than this
repository's, and that is the point:

- The three mode bytes are what `SetFanMode` writes on the board
  (`windows/vendor-ec-map.md`, "Power modes", live-verified in
  `evidence/ec-watch/2026-09-23-power-mode-cycle-0700-07ff.csv`). More usefully,
  **the EC produces the same `0x10` itself** on its own Turbo path at bank0
  `0xABE8` and `0xC741`, so the firmware and the service agree on the encoding
  (`ec/annotations/manual-fan-ctrl-0751.md` §3). Writing 0xA0/0x00/0x10 is
  therefore not a transcription of the service's constants; it is writing what
  the EC already writes.
- The PL triples are read out of the EC's own default blocks at apply time.
  Read live 2026-09-23 as `3C 3C A5 01` (Gaming), `23 23 A5 01` (Office) and
  `4B 4B A5 01` (Turbo) (`ec/annotations/registers.yaml`, `MODE_PL_DEFAULTS`).
  **No wattage is compiled in**, which is what the issue asked for and also
  what makes the patch correct on a board whose EC was programmed differently.
- `balanced` is the EC's own default (`0x0782` bit 4, read live `0x9D` with bit
  4 set), so the driver's initial profile and the firmware's agree with no
  special case.

`tools/check_power_profile.py` rule 3 is what makes "no wattage" checkable
rather than a promise: every `value_source` in `profile-map.csv` has to name a
bit spelling, an EC default block, a register the driver reads or a firmware
site, and a bare `0xA0` or `35` is refused by name.

## Two upstream disagreements the profile has to take a side on

**The Turbo gate is `0x049F` bit 1, not `FAN_TURBO_SUPPORTED`.** Upstream defines
`FAN_TURBO_SUPPORTED` as bit 4 of `EC_ADDR_SUPPORT_5` (`0x0742`). On this board
`0x0742` reads `0x02`, so that bit is **clear** — while `0x049F` reads `0x0A`
and the Fn key demonstrably cycles through Turbo. The vendor service offers
Turbo on `0x049F` bit 1 (`MyEcCtrl.GetTurboModeSupport`,
`windows/decompiled/v3.1.39.0/GCUService/MyECIO/MyEcCtrl.cs:84`).
`ec/annotations/registers.yaml` records both readings and says explicitly that
**"the two haven't been reconciled."** This work does not reconcile them
either. It gates on the bit that works, and the checker holds that as an
*absence* rule — a patch that gates on `FAN_TURBO_SUPPORTED` is refused — so
the disagreement cannot be tidied away by a later reader who has not read the
live value.

**`0x0786` is not the fan default.** Upstream calls it
`EC_ADDR_FAN_DEFAULT` (`FAN_CURVE_LENGTH 5`). Both the DSDT
(`APTC:7`/`APTN:1`) and the 3.1.39.0 vendor service use it as the CPU TCC
offset, and they agree with each other. The name is wrong for this board and
renaming it is a separate upstream change; it is prose in the PR body, not part
of this patch.

## The one invariant the PL replay rests on, and what it costs

**Writing the power limits is safe here only because the driver already holds
`0x0741` bit 0 set, and only because the profile never touches that byte.**
The EC's zeroing of `0x0783-0x0785` runs on the arm where `AP_OEM` bit 0 is
*clear*. `uniwill_ec_init()` sets that bit at probe, so the clear is not armed
in normal operation; the vendor service, by contrast, deliberately parks the EC
with the bit clear for the fan-curve handshake
(`windows/vendor-ec-map.md`, "Fan tables").

That is the whole reason the curve is left out, and it is a real trade rather
than an omission. The curve's mailbox at `0x0F5D`/`0x0F5E`/`0x0F5F` requires
clearing and re-setting `0x0741` bit 0, which is exactly the window in which
the PL clear at `0xA833` can fire. `ec/annotations/manual-fan-ctrl-0751.md` §4
("The one blind write") is where that clear is documented, and its §6 calls
the overlap "not established" and names it the first thing to check if PL
bytes ever go to zero around a table refresh; `windows/vendor-ec-map.md:276`
is where the same overlap is called "unresolved". **The consequence is
stated in the PR body rather than left for a reviewer to infer: a profile
switch changes the power limits and not the curve.**

The mechanism is decoded, so the follow-up does not start from zero. EC
handler at bank0 `0x888D`; magic `0xFD` at `0x0F5D` and `0xC9` at `0x0F5E`;
selector at `0x0F5F` accepted only in 1-3, where **1 = Turbo, 2 = Gaming,
3 = Office**; two 48-byte CODE tables copied to `0x0F00` and `0x0F30`; selector
3 additionally split by `0x0782` bit 2, the Office fan-table type; CODE base
seeded `0x60F2` at `0x8653`. The selector numbering is derived from firmware
rather than borrowed from the service's constants, and the two agree.

## What this does not establish

- **Whether the mode bits change fan behaviour at all.** This is the one that
  matters most and is the least established. `0x0751` stays `present-untested`
  for exactly this reason (`ec/annotations/registers.yaml`, `MANUAL_FAN_CTRL`):
  the 2026-09-23 run that established the table above was **near-idle**, and
  the fan duty at `0x075B`/`0x075C` moved the same amount under a no-op control
  write — i.e. thermally. Whether the mode bits scale fan behaviour along the
  (unchanged) curve is **unseparated from temperature**, and the fixed-load
  comparison that would separate it is issue #122/#123 and has not been run. A
  profile switch here changes the power limits; treating it as a fan-profile
  switch is not what the evidence supports.
- **Anything about the patched driver on hardware.** It has not been compiled —
  there is no kernel headers tree on this runner — and nothing has been loaded
  anywhere. `PR_DESCRIPTION.md` says so to whoever pastes it, because a PR body
  that implied a working driver would be the overclaim `CLAUDE.md` exists to
  prevent.
- **Battery behaviour.** The vendor writes PL1/PL2/PL4 = 0 on battery and what
  0 means to this EC is untested, so the handler skips the PL write off AC
  rather than shipping an untested semantic. Which is also why a follow-up that
  *does* want the limits to change on battery needs a measurement first.
- **The `0x0782` read is not made volatile**, and that is deliberate. It is
  already cacheable at `5a24248`, nothing writes it while the machine runs, and
  declaring it volatile would change what the HID lightbar and the China-mode
  path see. The registers this patch *adds* are the ones declared volatile,
  because the EC writes all four on its own.

## The finding inside the finding: upstream had no platform profile at all

The issue this work answers was written on the assumption that
`Wer-Wolf/uniwill-laptop` at `5a24248` has a platform-profile framework to
write a handler into — it names "the `platform_profile` struct, the
`UNIWILL_PLATFORM_PROFILE_UNK`/low-power/balanced/performance enum and the
existing profile store/cycle helpers". It does not, and two measurements say
so, of different weight. The first is a quotation rather than a search:
`struct uniwill_device_descriptor` is reproduced in full at
`upstream-excerpt-profile.txt:237-244` (upstream lines 428-435, closing brace
included), five members, and no `platform_profile` member among them. The
second is a scan of four spellings, over the whole extracted tree:

    $ grep -rn 'platform_profile\|PLATFORM_PROFILE\|profile_cycles\|profile_available' .
    (no output)

So: none of those four names occurs anywhere at `5a24248`. That is what the
scan shows, and it is not by itself a claim about functionality it did not
look for — the missing struct member above is what carries that, and the
patch needs both halves of that sentence to justify adding a framework rather
than a callback. The only trace of the idea in the tree is the keymap line at
`uniwill-acpi.c:478`, commented "Reported when user wants to cycle the
platform profile" and mapped to `KEY_F14` — an event with nothing to cycle.

So the patch has to add the framework, and the three names above are names it
introduces. Two smaller consequences, both recorded in the artefact rather
than smoothed over: the enum spells the unknown member
`UNIWILL_PLATFORM_PROFILE_UNKNOWN` where the issue wrote `..._UNK`, following
the kernel's vocabulary, because a future move to
`dev_pm_platform_profile_register()` should not have to translate; and the
sysfs pair is the driver's own `DEVICE_ATTR` idiom, because the patch was
written with no headers tree to compile against and an API whose current
signature could not be checked here is not something to guess at. The PR body
invites the maintainer to ask for the kernel API in the same patch, which
would be a better home and is about twenty lines of translation.

**A scope note for the issue tracker:** the issue as filed asked for a
`0x0751`-only draft with the PL and fan-table replay left as a TODO. That
instruction was premised on #99 being open. It is closed, and it was closed
with the negative answer, so the `0x0751`-only deliverable is not built as a
standalone patch — a patch that renames a mode without moving the power limits
is worse than not offering the profile at all. The mode byte is kept as the
first layer and the PL replay is added; the fan-table replay stays out, for
the reason above. The **fixed-load fan-behaviour run** is the follow-up this
opens, alongside a cTGP/DynamicBoost profile question that belongs to #8.
