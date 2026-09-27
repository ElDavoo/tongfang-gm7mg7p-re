# The prepared `uniwill-laptop` power profile for the GM7MG7P

Issue #102's deliverable: a patch and a PR body, committed here for a human to
review and submit to
[`Wer-Wolf/uniwill-laptop`](https://github.com/Wer-Wolf/uniwill-laptop)
themselves. **Nothing in this repository opens a pull request or an issue
against another repository** — see `CLAUDE.md`. The cross-reference to upstream
issue #7 is prose in `PR_DESCRIPTION.md` for the human to paste, not a comment
anyone posted.

## What is here

| file | what it is |
|---|---|
| `uniwill-acpi-profile-gm7mg7p.patch` | the diff against `BASE_COMMIT`. Purely additive — not one `-` line in the body — and it adds the platform-profile framework the driver does not have as well as the GM7MG7P handler |
| `PR_DESCRIPTION.md` | the upstream PR body, verbatim as a human pastes it |
| `profile-map.csv` | the structured source of truth: 18 rows, one per (mode × register), each with where its value comes from and what the patch does with it |
| `upstream-excerpt-profile.txt` | the committed evidence — the power-mode block, the PL registers, the regmap gates and the notify path, each with its line number in `uniwill-acpi.c` |
| `fetch-upstream-profile.sh` | re-derives the excerpt from a fresh fetch and diffs it. Needs the network, so it is not in any gate |

## The other patch for this board, and which one to submit

`../gm7mg7p-dmi-entry/` holds a second prepared patch for the same board and
the same `BASE_COMMIT`. It adds the `gm7mg7p_descriptor` with its eight
feature bits and the `PCSpecialist GM7MG7P` DMI row, and no profile.
**This patch supersedes both of those**: its descriptor is the same eight
feature bits plus `.probe` and `.platform_profile`, its DMI row is identical,
and its hunks are written against the tree as it is *before* that patch, so it
applies to `BASE_COMMIT` on its own.

They are alternatives, not a series. Applied to one tree in either order, the
second one fails at `uniwill-acpi.c:2860` — the descriptor hunk — because the
descriptor and the row are already there. Checked on 2026-09-27 in a throwaway
checkout of `5a24248` — not in this repository, which is not the tree either
patch is diffed against — with `<repo>` for this repository's root:

```console
$ cd <throwaway> && git init -q . && git fetch -q --depth 1 \
      https://github.com/Wer-Wolf/uniwill-laptop 5a24248f6422a0b673a47cbfd65e19a98eb4c8a9 \
      && git checkout -q FETCH_HEAD
$ git apply <repo>/linux/patches/gm7mg7p-dmi-entry/uniwill-acpi-dm-gm7mg7p.patch
$ git apply --check <repo>/linux/patches/gm7mg7p-power-profile/uniwill-acpi-profile-gm7mg7p.patch
error: patch failed: uniwill-acpi.c:2860
error: uniwill-acpi.c: patch does not apply
```

The same command with the two patches swapped fails the same way, at the same
line.

**So submit this one for the board.** If the DMI-entry change reaches upstream
first, drop this patch's descriptor and DMI-row hunks and rebase the rest onto
it — do not apply both. That is also what the sentence in this patch's header
now says: "no existing descriptor, DMI row, feature bit or keymap entry is
modified" is true of this diff applied on its own to `BASE_COMMIT`, and of
nothing else.

## The thing that changed the shape of the work

**No reference to `platform_profile`, `PLATFORM_PROFILE`, `profile_cycles` or
`profile_available` anywhere in the tree at `5a24248`.** That is what the scan
showed, over the whole fetched tree:

```console
$ grep -rn 'platform_profile\|PLATFORM_PROFILE\|profile_cycles\|profile_available' .
(no output)
```

Four spellings is what it looks for, so on its own that is a statement about
those four names rather than about the driver's functionality. What carries
the functional half is a quotation instead: `struct uniwill_device_descriptor`
is reproduced complete in the excerpt (upstream lines 428-435), five members
and no `platform_profile` member, so the struct this patch adds a callback to
has nowhere to put one. And what the tree does carry is the keymap line at
`uniwill-acpi.c:478`, commented "Reported when user wants to cycle the
platform profile" and mapped to `KEY_F14` — an event with nothing to cycle.

The issue was written assuming otherwise: it asked for a handler written
against "the `platform_profile` struct, the
`UNIWILL_PLATFORM_PROFILE_UNK`/low-power/balanced/performance enum and the
existing profile store/cycle helpers". All three are names this patch
*introduces*. So the patch is larger than the issue asked for, and
`PR_DESCRIPTION.md` says so in its first paragraph rather than letting a
reviewer discover it. The full measurement, and what the excerpt can and
cannot quote as a result, is in the excerpt's own header.

Two smaller consequences, both recorded rather than smoothed over: the enum
carries `UNIWILL_PLATFORM_PROFILE_UNKNOWN` where the issue wrote `..._UNK`,
following the kernel's spelling; and the sysfs pair is the driver's own
`DEVICE_ATTR` idiom rather than `dev_pm_platform_profile_register()`, because
the patch was written with no kernel headers tree to compile against and an API
whose signature could not be checked here is not something to guess at. The PR
body invites the maintainer to ask for the other one.

## What the handler does, and from where

| driver profile | firmware mode | `0x0751` | power limits from |
|---|---|---|---|
| `low-power` | Office | `FAN_MODE_USER \| FAN_MODE_HIGH` (0xA0) | the `0x0734-0x0736` block |
| `balanced` | Gaming | 0x00 | the `0x0730-0x0732` block |
| `performance` | Turbo | `FAN_MODE_TURBO` (0x10) | the `0x07A7-0x07A9` block |

- **Turbo is gated on `0x049F` bit 1**, which reads `0x0A` on this board.
  Upstream's `FAN_TURBO_SUPPORTED` is `0x0742` bit 4, which reads `0x02` — so
  clear that Turbo would be hidden on a machine that has it. The checker
  asserts the patch uses `0x049F` and does **not** use `FAN_TURBO_SUPPORTED`;
  an absence rule, because that disagreement is the one most likely to be
  "corrected" back by a later reader who has not read the live value.
- **`balanced` is the EC default** (`0x0782` bit 4; reads `0x9D`, bit 4 set),
  so the driver's default profile and the firmware's agree with no special case.
- **No literal wattages anywhere.** The three mode bytes are spelled as the bit
  names the firmware's own encoding has everywhere else, and the PL triple is
  copied out of an EC default block at apply time. The checker refuses a map
  row whose `value_source` is a literal and a patch line that assigns a bare
  decimal to a limit.
- **`0x0741` is never written.** The EC zeroes the power limits on the arm
  where its bit 0 is *clear*, and the fan-curve handshake parks the EC in
  exactly that state. The driver sets that bit once from `uniwill_ec_init()`
  and the profile never touches it — which is what makes writing the limits
  without the curve safe rather than merely convenient.
- **Fan Boost stays out of the mode byte.** The OSD owns bit 6 and adds it
  while boost is on; the profile writes bits 0-5 and 7 through
  `FAN_PROFILE_MASK`, so two writers never share one byte.
- **`0xB0` → profile cycle, and no other board changes.** The new notify arm
  falls through to the arm below it whenever the descriptor's callback is
  NULL, which is every board but this one. The keymap line is untouched, which
  is why the diff is additive.

## The #99 inversion, and why the PL replay is in

The issue said to draft a `0x0751`-only version and leave the PL/fan-table
replay as a TODO "until #99 answers it". #99 is answered, statically and live,
and the answer is the negative one — so a `0x0751`-only profile is a patch this
repository has already measured and knows does not switch power modes. Three
committed places say it, and the plan is built on all three:

- `ec/annotations/manual-fan-ctrl-0751.md` §2 — all 29 firmware sites that
  touch `0x0751` touch no other XDATA byte; and its §5 — the per-mode default
  blocks have no read site in the image at all.
- `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md:3` — "**Status: run
  2026-09-23 (issue #99); the prediction held.**" On AC, from Turbo, service
  running, `0x0751` was set to each of `0xA0`/`0x00`/`0x10` and held 20 s
  while `0x0783-0x0787`, `0x07C5`, `0x07C6`, `0x0743-0x0746` and
  `0x0F00-0x0F5F` were watched. Nothing else moved. Raw log:
  `evidence/ec-watch/2026-09-23-0751-isolation.txt`.
- `ec/annotations/registers.yaml`, `MANUAL_FAN_CTRL` — "So a Linux platform
  profile has to write the PLs and the fan table itself, from the EC default
  blocks; 0x0751 alone will not."

So the mode byte is kept as the first layer, because that is what the issue
asks for, and the **PL replay is added**, because #99 established it is
mandatory and every one of its values is readable from an EC default block,
exactly as the issue says. The fan-table replay stays out, as the issue
directs, and for a second reason as well — see below.

## What is left out, and why

- **The fan-table replay.** The issue defers it. There is also a second,
  independent reason: the mailbox at `0x0F5D`/`0x0F5E`/`0x0F5F` requires
  clearing and re-setting `0x0741` bit 0, and that is the exact window in
  which the PL clear at `0xA833` can fire — `manual-fan-ctrl-0751.md` §4
  documents that clear, and its §6 calls the overlap "not established" and
  names it the first thing to check if PL bytes ever go to zero around a table
  refresh; the word "unresolved" for that overlap is
  `windows/vendor-ec-map.md:276`. The mechanism is written down in
  `docs/findings/power-profile-gm7mg7p.md` and in the PR body, so the follow-up
  starts from the decode rather than from zero.
  **Consequence, stated in the PR body:** the curve does not follow the mode.
- **The GPU bytes `0x0743-0x0746`.** cTGP/DynamicBoost is issue #8. Keeping it
  out also keeps this patch clear of the 25-vs-15-vs-5 W DynamicBoost
  disagreement, which is a cTGP-init question and not a profile one — and the
  vendor writes identical GPU bytes in all three modes, so there is nothing
  per-mode for a profile to switch.
- **Battery behaviour.** The vendor writes PL1/PL2/PL4 = 0 on battery, and
  what 0 means to the EC is untested. The handler skips the PL write off AC.
  A driver that wrote 0 there would be shipping an untested semantic as a
  feature.
- **Renaming `EC_ADDR_FAN_DEFAULT`.** `0x0786` is the CPU TCC offset in the
  DSDT (`APTC`/`APTN`) and in the vendor service, so the name is wrong for this
  board — but that is a separate upstream change and bundling it makes this
  harder to review. Prose in the PR body only.
- **Any live hardware validation.** No machine is reachable from this pipeline.
  The profile's own behaviour on the GM7MG7P is unrun and the patch says so.

## The status vocabulary the map is held to

Every `registers_status` in `profile-map.csv` is a value
`ec/annotations/registers.yaml`'s own header comment declares, **parsed out of
that comment and never copied into the checker** — a second copy of the list is
how the two drift apart silently. The checker then requires each `register` to
resolve to an address `registers.yaml` records and its status to equal the one
recorded there.

The other direction is the one this map needs and the DMI map does not.
`0x0F00` has **no** `registers.yaml` entry, so the fan-table row must leave
`registers_status` empty — and an empty cell on an address the file *does*
record is a refusal, because that is how an ungraded register would slip
through as nobody's business. Rule 1 of the checker is that in both directions
and `--self-test` holds a positive and a negative for each half.

`registers.yaml` is **read-only** here. This change packages statuses already
recorded; it changes none. So no row is edited, which also keeps a branch that
does edit one from colliding.

## Reproducing it

Offline — no network, no `git`, nothing but the committed files:

```sh
python3 tools/check_power_profile.py --check      # the nine rules
python3 tools/check_power_profile.py --self-test  # the refusals themselves
python3 -m unittest discover -s tools -p 'test_check_power_profile.py'
```

With the network, to re-derive the evidence:

```sh
bash linux/patches/gm7mg7p-power-profile/fetch-upstream-profile.sh
```

And to confirm the patch still applies to the pinned source:

```sh
git apply --check linux/patches/gm7mg7p-power-profile/uniwill-acpi-profile-gm7mg7p.patch
```

That last one is a command for a maintainer to re-run, not something any gate
in this repository runs: it needs the network, and this repository does not
describe a check that only sometimes runs as one that does.

**It was run once, on 2026-09-27, and this is the record of it.** Against a
fresh `git fetch --depth 1` of
`5a24248f6422a0b673a47cbfd65e19a98eb4c8a9` into an empty tree, whose
`uniwill-acpi.c` is 90,721 bytes with sha256
`914d876fa3255e6ad8f8669162eaa844b23eaf9f41fd181113447c49c3ecc2a7` — the digest
`upstream-excerpt-profile.txt` already records, so the checkout is the source
this patch was made against and not some other one:

```console
$ cd <throwaway> && git init -q . && git fetch -q --depth 1 \
      https://github.com/Wer-Wolf/uniwill-laptop 5a24248f6422a0b673a47cbfd65e19a98eb4c8a9 \
      && git checkout -q FETCH_HEAD
$ git apply --check -v <repo>/linux/patches/gm7mg7p-power-profile/uniwill-acpi-profile-gm7mg7p.patch
Checking patch uniwill-acpi.c...
Hunk #5 succeeded at 688 (offset 1 line).
Hunk #6 succeeded at 738 (offset 1 line).
Hunk #7 succeeded at 772 (offset 1 line).
Hunk #8 succeeded at 1342 (offset 1 line).
Hunk #9 succeeded at 1419 (offset 8 lines).
Hunk #10 succeeded at 1471 (offset 8 lines).
Hunk #11 succeeded at 2332 (offset 8 lines).
Hunk #12 succeeded at 2433 (offset 8 lines).
Hunk #13 succeeded at 2452 (offset 8 lines).
Hunk #14 succeeded at 2587 (offset 8 lines).
Hunk #15 succeeded at 3076 (offset 8 lines).
Hunk #16 succeeded at 3668 (offset 8 lines).
$ echo $?
0
```

Every hunk accepted, no warning, no fuzz, and exit 0. The block is not silent,
though, and the offsets are the part to read: **twelve of the sixteen hunks
apply at a line offset from the one their `@@` header names**, because the
patch was hand-written against a reading of the source rather than produced by
`git diff` off a prepared tree. Hunk #1-#4 land on the line they claim; #5-#8
are one line out and #9-#16 are eight.

That is benign here, and it is worth saying why rather than leaving a reader
to work it out from a log. An offset means git did not find the hunk where its
header said, but it did find it — a hunk is located by its context lines, not
by its line number, so the twelve above are the twelve whose context still
matched at a different line. This diff touches one file and adds lines only,
not one `-` line anywhere in the body, so there is no removed line for an
offset to re-target at the wrong place. A maintainer rebasing onto a tree
where upstream has moved further will see those offsets grow, and possibly
start seeing rejects; the check to re-run is the one above, against their own
tree.

`PR_DESCRIPTION.md` says so to whoever pastes it upstream, and it says it
*here* first because a claim in a body bound for another repository is only as
good as what this one records. The same throwaway checkout is what the
stacking result in "The other patch for this board" above was measured on.

**`fetch-upstream-profile.sh` is a deliberate near-duplicate of
`gm7mg7p-dmi-entry/fetch-upstream.sh`, not an oversight.** The two range lists
are disjoint — that one quotes the feature bits, the cTGP block, the charge
block and the DMI table; this one quotes the power-mode block, the PL
registers, the regmap gates and the notify path. Generalising the existing
script into a shared one would mean editing a file other branches have open,
which is the merge conflict this repository's conventions exist to avoid. What
is shared rather than copied is the behaviour: the rev comes from
`linux/patches/BASE_COMMIT`, the two pins are checked for agreement before the
network is touched, two clients are tried because a refused command is a fact
about a command and not about the network, and only the fragments below the
delimiter line are diffed. Say so in a review of either; it is a decision, not
a slip.

The full 90 KB `uniwill-acpi.c` is deliberately not vendored. The excerpt is
~390 lines and reviews in a diff, and the full file is GPL-2.0-only —
`upstream-excerpt-profile.txt` carries the attribution and the `MODULE_LICENSE`
line it comes from.

## What is not verified, and who is left holding it

- **The patched driver has not been compiled**, and nothing has been loaded on
  a machine. There is no kernel headers tree on the runner;
  `linux/nix/uniwill-laptop.nix` is the human's build path.
- **The profile's own behaviour on the GM7MG7P is unrun.** Every claim about
  what the EC does rests on measurements of the *EC* recorded in `evidence/`,
  not on a run of this patch.
- **Whether the mode bits change fan behaviour at all is unseparated from
  temperature.** The 2026-09-23 run was near-idle and the fan duty moved the
  same amount under a no-op control write. A mode switch here changes the power
  limits; it is not established that it changes the curve, and the fixed-load
  comparison that would separate them (#122/#123) has not been run. The PR body
  says this to whoever pastes it, because a PR body that implied otherwise
  would be the overclaim `CLAUDE.md` exists to prevent.
- **`acpi_get_battery_info()` is used and not exercised.** It is the API the
  file's existing `<acpi/battery.h>` include already reaches for, and the
  handler's off-AC skip depends on it, but nothing here has run it.

## Before you submit

1. `bash fetch-upstream-profile.sh` — the excerpt still matches the pinned source.
2. `git apply --check uniwill-acpi-profile-gm7mg7p.patch` against a fresh
   checkout of `5a24248`. Run once and recorded under "Reproducing it"; this
   is the re-run, on your own checkout, and it is the step that would catch a
   base that has moved under the pin.
3. `python3 tools/check_power_profile.py --check` — nine rules, green.
4. Read `profile-map.csv` and agree with all eighteen rows, not just the four
   writes. The exclusions are the part a reviewer is most likely to challenge,
   and the fan table's in particular is a deliberate absence rather than an
   oversight.
5. Read "The other patch for this board" above, and submit **this** patch, not
   the `../gm7mg7p-dmi-entry/` one. They are alternatives; stacked, the second
   does not apply.
6. **Build it.** `linux/nix/uniwill-laptop.nix`. The first build is part of the
   review, not a formality — see the PR body's fourth section.
7. Load it, and check `profile_cycles` reads `low-power balanced performance`
   and that `echo performance > profile` moves `0x0783-0x0785` to `4B 4B A5`
   and back. This is the step this repository cannot do.
8. Only then: open the PR, pasting `PR_DESCRIPTION.md`. Not before, and not
   from here.
