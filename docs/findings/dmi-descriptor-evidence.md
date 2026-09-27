# The DMI descriptor reduces to one bit, and the reason is a missing file

What the TongFang GM7MG7P's `uniwill-laptop` entry can honestly claim, feature
by feature, and why almost none of it is the EC's fault. The deliverable is
`linux/patches/gm7mg7p-dmi-entry/`; this is the reasoning behind it, kept
separate from the artifact so the artifact can be re-cut without re-litigating
it.

Findings are cited **by file and heading** throughout. `docs/findings.md` is
frozen (see its own §1's successors in `docs/findings/prepared-gate-patches.md`
for what that costs an append), so nothing here adds a section number to it.

## The headline, and it is not what issue #10 expected

Issue #10 asks for a DMI entry that claims the features `docs/findings.md`
section 2 lists as confirmed working: CPU and GPU temperature, both fans, the
Fn lock, the Super key, the keyboard backlight hotkey, and the battery charge
modes. Seven features. **The prepared entry claims one of them.**

That is not a judgement about the other six. Five of them are confirmed at the
register level and would be included today if the descriptor could name them.
The blocker is a single absent file, and the shape of it is worth writing down
because it will bite the next person who reads section 2 and starts writing an
entry.

## The missing file

`uniwill-laptop`'s `uniwill-acpi.c` is not vendored in this repository.
`linux/patches/` holds `BASE_COMMIT` and one prepared patch, and nothing else.
A DMI entry's feature column is a set of `UNIWILL_FEATURE_*` bit constants
defined in that file, so **the entry cannot be written without reading it.**

Exactly two of those spellings are recoverable from committed files here, both
quoted in `linux/patches/README.md`:
`UNIWILL_FEATURE_BATTERY_CHARGE_MODES` and `UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT`.
The names in `ec/annotations/registers.yaml` — `CPU_TEMP`, `PRIMARY_FAN`,
`FN_LOCK` and the rest — are *this* repository's names for the register
addresses, and they do not map one-to-one onto upstream's constants. Writing
`UNIWILL_FEATURE_CPU_TEMP` because that is obviously what it is called would be
a guess that applies cleanly, passes every check in this repository, and names
a constant that may not exist.

`ec/annotations/static-refs-audit.md` hit this same wall before, for the same
reason, on the same absent file. Its recorded answer is the precedent worth
following: `PRIMARY_FAN`/`SECONDARY_FAN`, `TOUCHPAD_TOGGLE` and `USB_POWERSHARE`
have no EC address recorded anywhere in this repository, and rather than invent
addresses the file left the cells empty and named the features. The feature map
in the prepared entry does the same, in the `not-recorded-here` and `unsourced`
cells, and the checker refuses an exclusion that has no written reason.

`tools/check_dmi_descriptor.py` makes this mechanical rather than a matter of
restraint: a bit spelling has to be quoted by a committed file the row names,
or read off the driver at `BASE_COMMIT` *and* set by the patch. There is no
third way in.

## The one bit that clears every bar

`BATTERY_CHARGE_MODES`, EC `0x07A6`, `confirmed-working-partially` in
`ec/annotations/registers.yaml`. It is the only row with a sourced bit, a
recorded address and a `confirmed-*` status.

**The caveat has to travel with it, or somebody re-derives this the hard way.**
Writing the three profile values (High Capacity / Balanced / Stationary) is
accepted, and the EC selects a different early-exit current limit at firmware
sites `0xB2E2`/`0xB330` (`ec/annotations/charge-profile-flow.md`). It does not
cap charging: coulomb-counted traces show >1 A still flowing at 95% under both
Trickle and Long_Life (`evidence/battery-traces/2026-09-09-profiles.csv`, and
the summary table in `docs/findings.md` section 2). A user switching to
"Stationary" should not expect charging to stop, and an upstream PR claiming
the bit without saying so would be actively misleading in a way the rest of
this descriptor is not.

`confirmed-working-partially` exists as a status value for exactly this
situation, and its own header gloss in `ec/annotations/registers.yaml` names
`0x07A6` as the reason it is there.

## The five the issue said to resolve or drop

All five resolve the same way — drop, with a cited reason — and one of them is
a place where the issue's own list is out of date.

**`BATTERY_CHARGE_LIMIT`.** Dropped, and the reason is stronger than "untested".
`0x07B9` is `unknown-not-absent`, not absent; that retraction is
`docs/findings.md` section 4c. The paired `0x07B9`/`0x07D0` write — the pair
the Windows service actually writes — was run live through the physical window
in five variants and did not stop charging (section 4f). And there is no cap
behind the bit for it to expose: what the vendor enforces is a charge-*voltage*
target of 16.4 V, derated with age (section 4l), and the EC owns that byte, so
the host cannot set it (section 4m). Upstream issue #7's XMG `X6AR5xxW` reports
the identical symptom, and this account is consistent with that report rather
than contradicting it.

**`AC_AUTO_BOOT`.** `0x0726` carries the status value `absent`, and its own note
records the real verdict as unknown, needing a live behavioural test, downgraded
from an earlier `confirmed-inert` call. The map carries the status value
verbatim and carries the note's calibration in its verdict column rather than
restating the note as a stronger claim. A zero from a static scan is
not-found-by-this-method; it is never proof (sections 4a-4d).

**`USB_POWERSHARE`.** The EC bit flips on write and the real-world effect is
untested. A write being accepted is not evidence the EC acts on it — the same
standard that downgraded `AC_AUTO_BOOT`, applied to the same register-file
neighbour.

**`USB_C_POWER_PRIORITY`.** `0x07CC` is `unknown-not-absent`: all 6 of its
sites are in the ITE8850-PD image rather than the EC firmware, so the reference
count is not EC-side evidence at all
(`ec/annotations/lightbar-bat-flow.md`, section 6).

**`NVIDIA_CTGP_CONTROL`.** **This is the one the issue gets wrong.** Issue
#10's list calls it untested; `ec/annotations/registers.yaml` grades `0x0743`
`confirmed-working`, with all 10 sites EC-side so the count is not PD
contamination. `registers.yaml` is the source of truth for status (CLAUDE.md),
so the map follows it, and the checker's rule 2 is what holds the two in step —
a hand-typed status in the map that a later `registers.yaml` edit leaves behind
is a red run. It is still excluded, for the single reason the other four
confirmed features are: the bit spelling is not recoverable. A stale issue list
turning into a wrong descriptor is exactly what the status rule is for.

## The lightbar is a different driver, and saying so is the useful part

`0x0748`-`0x074B` is `confirmed-not-this-mechanism`. A live test wrote every one
of those bytes — WELCOME/rainbow toggle, `S0_OFF`, RGB `0xC8` — with zero
observable effect while the lightbar kept animating its own pattern, corroborated
three independent ways with no site in either image.

The real device is a USB HID: `048D:6005`, usage page `0xFF03`
(`docs/hardware-identity.md`). No Linux driver claims it. So this is not a
descriptor row to leave out, it is a **different driver** — `ite_8291_lb` in
`tuxedo-drivers` — and this repository already has work on it under
`linux/lightbar/`. The prepared entry points there and at issue #5 rather than
claiming a bit it would drive wrongly.

## The gap the issue did not raise: the keyboard backlight is RGB

`docs/findings.md` section 2 lists `KEYBOARD_BACKLIGHT` (hotkey path) as
confirmed, and it is — Fn+F6/F7, WMI events 177/178. **But that is the EC hotkey
event, not the sysfs brightness interface**, and those are different things.

Three facts pull in different directions:

- the hotkey is confirmed working at the EC level;
- `0x078C` `KBD_STATUS`, the software LED-class path a brightness node would
  actually drive, is `present-untested`, and its own note says the hotkey path
  is "separate and untested";
- `docs/hardware-identity.md` records this board's backlight as `048D:CE00`, a
  **4-zone RGB** device, while upstream's `kbd_led_*` interface is a single
  brightness.

Whether a single-brightness interface drives a 4-zone RGB backlight correctly
is settled by no committed file in this repository. Including the bit wrongly
is the worse error, so the map excludes it and `PR_DESCRIPTION.md` names it as
the one item a maintainer or a human at the machine should settle.

This is also the clearest place the calibration rule bites against a literal
reading of the issue: `KEYBOARD_BACKLIGHT` is on the issue's "confirmed
working" list, and including it is still the wrong call. **Excluding costs the
Fn+F6/F7 hotkeys; including it wrongly is worse.** Per-zone RGB control, if
that is what this needs, is `ite_8291_lb`'s business too.

## Left out on purpose, and recorded so the omission reads as a decision

- **The paired `0x07B9`/`0x07D0` hardware test as a prerequisite.** It is not a
  prerequisite. Section 4f already ran it and it already answers the question.
  Re-preparing finished preparation is not progress.
- **Resolving the charge limit further.** Issues #1, #3 and #4 own it.
  Section 4o records that the static route to `0x07D0` is exhausted and the
  remaining question needs a 2021-era EC image nobody here has.
- **Compiling the patched driver.** Needs a kernel headers tree;
  `linux/nix/uniwill-laptop.nix` is the build path and nix is not on the CI
  runner.
- **Bumping `BASE_COMMIT` to current upstream `HEAD`.** The pin is deliberate
  and the nix rev matches it. A bump invalidates both and is a human's call.
- **Editing `docs/hardware-identity.md`.** Its sentence saying this board is
  not in `uniwill-laptop`'s DMI table is still exactly true: the entry is
  *prepared*, not upstream. It becomes false the day a human submits it, and
  that is the day to change it.

## What would move the number

One fetch. `curl` the `BASE_COMMIT` tarball, read the `UNIWILL_FEATURE_*` enum
out of `uniwill-acpi.c`, and most of the `unsourced` cells become one-word
edits with the evidence already sitting behind them. That is the whole of the
remaining work on this entry, and it needs a network and a person — not a
reverse-engineering insight, and not another issue.
