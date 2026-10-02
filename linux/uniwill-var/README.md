# `UniWillVariable` on Linux: read it, and change one byte with a backup

`docs/findings.md` §8 established, live on Windows on 2026-09-23, that the
BIOS setup's hidden **Memory** entry (Intel's Memory Overclocking Menu, form
`0x27B1`) is gated on one byte of one UEFI variable: `OemOcDxe` copies
`UniWillVariable[0x33]` into `Setup[0x7D7]` on every boot, and that is question
`0xEC6`, the suppress-if around the vendor Advanced page's Ref
(`bios/decompiled/OemOcDxe.annotated.c`, `Setup.Oem7D7 =
Uwv.MemoryOverClockSwitch;`).

The variable is `NV|BS|RT`, so the OS can write it, and on Linux that is
`efivarfs`. This directory is the Linux half of what
[`windows/tools/uefi_var.py`](../../windows/tools/uefi_var.py) (decode) and
[`windows/tools/uniwill_set.py`](../../windows/tools/uniwill_set.py) (one-field
write, backup, readback) do through Win32.

**Nothing here has been run against hardware.** The suite is offline, the
write has never been executed on a machine, and §8's *"That route has not been
exercised; only the Windows write above has been"* is still true. What the
Windows run established is the mechanism and the menu; it is cited as such and
never as a Linux result. The write itself is
[`docs/hardware-tests/uniwill-var-memoc-efivarfs.md`](../../docs/hardware-tests/uniwill-var-memoc-efivarfs.md),
which a human at the machine runs.

## The framing, and the path spelling

An efivarfs entry is **4 bytes of attributes, little-endian, then the variable
data**. So this entry is 184 bytes: `07 00 00 00` (NV|BS|RT) followed by the
180-byte `NVRAM_STRUCT`.

`docs/findings.md` §8's "For Linux" paragraph gives the path as

```
/sys/firmware/efi/efivars/UniWillVariable-9f33f85c-13ca-4fd1-9c4a-96217722c593
```

**That is correct, and it is left as it stands.** efivarfs keeps the GUID's
dashes in the dentry name and drops only the braces, so the dashed spelling is
the filename. Every entry on an efivarfs mount is spelled that way —
`BootOrder-8be4df61-93ca-11d2-aa0d-00e098032b8c`,
`CurrentPolicy-77fa9abd-0359-4d32-bd60-28f4e78f784b` — and that is one command
on any efivarfs mount, rather than a claim to take on trust. Produced on a
GitHub-hosted CI runner, not on the laptop; every efivarfs mount is the same
kernel code path, so the block is worth the same wherever it is re-run:

```console
$ ls /sys/firmware/efi/efivars | wc -l
$ ls /sys/firmware/efi/efivars | grep -c -- '-[0-9a-f]\{32\}$'
0
```

The first count is whatever that machine holds and is deliberately not written
down here — it moves with the firmware's variable set. The second is the one
that settles it, and it is 0 on every mount checked, including that runner: no
entry anywhere is named with the 32 bare digits. §8 needs no correction here.

The tool still does not build that path from a hand-typed string. It globs
`UniWillVariable-*` under the directory and checks that the trailing digits are
this GUID **with separators stripped on both sides**, so it finds the entry
whether a given directory spells the GUID dashed or not, and refuses a
different variable's entry sitting under the same name either way. That
tolerance is the reason for the glob, and it is a reason worth having on its
own: `--var` points at a directory chosen by whoever runs the tool, and
refusing a GUID mismatch is the property that keeps a wrong `--var` from
writing the wrong block.

## Commands

Run from the repository root, as root (efivarfs is root-only).

```sh
sudo python3 linux/uniwill-var/uniwill-var.py show
sudo python3 linux/uniwill-var/uniwill-var.py get MemoryOverClockSwitch
sudo python3 linux/uniwill-var/uniwill-var.py set MemoryOverClockSwitch 1 \
    --backup /tmp/uniwill-before.bin
sudo python3 linux/uniwill-var/uniwill-var.py restore /tmp/uniwill-before.bin
```

`show` is the default and is read-only: the hexdump, the §8 field table, and the
attributes. `get` is one field, its offset and its value. `set` and `restore`
write, and everything below about safety applies to both.

Decoding a dump you already have, with no root and no machine — the shape of
the committed `evidence/uefi/*.bin`:

```sh
python3 linux/uniwill-var/uniwill-var.py show \
    --body-only evidence/uefi/2026-09-19-UniWillVariable.bin
```

**A readback is a transport check and nothing more.** The tool's success
criterion is "the 184 bytes I wrote are the 184 bytes I read back", which is
`uniwill_set.py`'s contract. It says the write landed. It does not say the EC
or the BIOS acted on it, and it does not say the menu appeared. That is
`docs/findings.md` §4a's trap in new dress: a write being accepted is not
evidence it did anything. The only thing that shows the menu is a reboot and a
person looking at the Advanced page.

## The safety envelope

`set` and `restore` refuse, in this order, and each refusal is a test case:

- **`--backup` is mandatory** for `set`, and the tool will not overwrite an
  existing backup file. The backup is written before the variable is touched.
- **A body that is not exactly 180 bytes is refused.** This is the one that
  matters most: efivarfs does not patch, it *replaces* the variable with
  whatever was written, so a tool that wrote 179 bytes would leave a
  179-byte `NVRAM_STRUCT` behind and the next read would be nonsense.
- **`--body-only` is a decode-only input.** No write subcommand accepts it. A
  body file is not the live variable, and building a write from one would
  replace a 184-byte entry with a file whose first four bytes are somebody's
  memory clock.
- **Array fields are refused** (`Reserved`, `RGBKeyboard1A`, …). The tool writes
  scalars only.
- **An unknown field name and an out-of-range value are refused**, and a typo is
  not reported as an array field.
- **An already-equal value writes nothing**, printing `already set; nothing
  written`, matching `uniwill_set.py`. The backup is still written: it is the
  record of what was there.
- **A readback that does not match is a failure**, reported as one, and the tool
  exits non-zero.
- **The immutable flag goes back on in a `finally`**, so a write that raises
  cannot leave the entry writable. A filesystem with no flag ioctl at all is
  reported in a note rather than assumed either way — the write still happens,
  but the tool does not claim an immutability it did not get.

Everything else is carried across untouched: every other byte of the body, and
the attribute word itself. A variable carrying `APPEND` keeps carrying it —
this is `uniwill_set.py`'s contract (it passes `attr` back untouched), and
efivarfs stores the attributes it is given.

## Why 0x33 is the one field this can write blind

The struct declares no `Pack`, so the CLR aligns each field to its own size:
180 bytes that way, 178 packed. `docs/findings.md` §8 does not settle which the
vendor's own code sees, and for most fields that matters.

`MemoryOverClockSwitch` is at **0x33 under both**, because every field before
it is a byte or an 8-byte array and neither forces padding. The first
offset-sensitive field is `ACpuFreqValue`: the single-byte
`ACpuOverClockSupport` at 0x42 leaves three bytes of pad before the following
`uint`, so it sits at 0x44 aligned and 0x43 packed, and the 17 fields from it
onward shift with it.

So a field at or before 0x42 can be written without resolving the pack
question, and one past it cannot. **That is why the tool refuses a wrong-sized
body rather than guessing**: for 0x33 the offsets are settled, and the size
check is what tells it the machine's variable is the struct it thinks it is.
`nvram_layout.py`'s docstring carries the derivation, and
`test_uniwill_var.py`'s `LayoutClaimTests` asserts all of it rather than leaving
it in prose.

## `MemoryOverClockSupport` (0x60) is not the way in

The tool will write it, because it is a general tool and refuses only what is
unsafe. But it is the wrong door, and `docs/findings.md` §8 says why: the
service publishes `MEM_MemoryOverClockSupport` from that byte, and with it at 1
the service's `SetUserProfile()` calls
`SetMemoryOverClockSwitch(currentProfile.MEM.MemoryOverClockSwitch)` — which
runs from `Init()` and on every power-mode change, and would put the profile's
saved 0 back. §8 deliberately left 0x60 at 0. The service's `DebugMode`
registry value also forces it to 1, but the same block rewrites the SMAPC power
table to PL1/PL2/PL4 = 120/120/165, so it is not a safe way in either.

One caveat stands regardless of how the byte was set: the service caches the
whole struct when it starts and writes the whole cached copy back on any field
change, so **a Control Center action taken before the next boot can revert
0x33**. Reboot without touching it.

## Why this stays userspace, and is not a kernel interface

Issue #118 asked for a judgement here rather than a patch, so here it is.

**None of the `UniWillVariable` fields belongs in a kernel driver.**

1. **They are boot-consumed settings, not runtime EC state.** `OemOcDxe` copies
   them into `Setup`/`CpuSetup`/`SaSetup` during DXE
   (`bios/decompiled/OemOcDxe.annotated.c`), and
   [`docs/findings/ifr-charge-and-battery-options.md`](../../docs/findings/ifr-charge-and-battery-options.md)
   settles what kind of consumer that makes: a form-set that could not see the
   byte would not need the copy, so **the consumer is DXE code, not a
   form-set** — DXE code, not HII, and not a driver. The same file's negative
   half is a bounded scan, twelve `bios/ifr/` dumps and the decompiles finding
   **zero** references to the variable. That is *not found by that method*, and
   not a claim that no form-set anywhere uses it.
2. **efivarfs already is the kernel's userspace ABI for exactly this.** Parsing
   a vendor struct in-kernel would duplicate an interface that exists, and would
   duplicate it in the one layer that has to be ABI-stable.
3. **Every one of these is a userspace-time change followed by a reboot.** The
   vendor service caches the whole struct and rewrites the whole block on any
   field change (§8), so there is no runtime state for a driver to expose —
   `0x33` is consumed once, by `OemOcDxe`, on the next boot.
4. **The charge-limit fields are a different mechanism wearing the same
   names.** `BatteryLimitation`, `ChargeMaximumLimit` and
   `ChargeMinimumLimit` at 0x30-0x32 look like `uniwill-laptop` territory, and
   they are not: this is NVRAM read by `OemOcDxe`, not the EC/ACPI charge-control
   path that upstream's charge-limit work targets. Conflating the two is the
   easy mistake here, so it is named rather than left implicit.

Hence a small CLI and a documented procedure, not a sysfs driver. **No
`linux/patches/` entry is created**, because the answer is a negative one and a
negative conclusion needs no prepared diff. Nothing has been or will be opened
upstream from here (see `CLAUDE.md`).

Worth carrying into the next issue on §8: the open question of what `GPP_B22`
drives is answerable **with an existing kernel interface** — `pinctrl-cannonlake`
exposes the pad under debugfs — which is a further reason this particular
question never needed a new kernel interface of its own.

## Offline tests

The suite is stdlib `unittest`, discovers no hardware, and opens nothing under
`/sys`. Its only inputs are the three committed 180-byte dumps in
`evidence/uefi/` and the two source files the field table is transcribed from.
For this directory alone:

```sh
python3 -m unittest discover -s linux/uniwill-var -p test_uniwill_var.py
```

or the whole repository's suites, which is what CI runs:

```sh
bash tools/run-tests.sh
```

What a green run proves, precisely: the decoder reads the committed dumps the
way §8 and `evidence/uefi/2026-09-19-UniWillVariable.txt` already record them;
the tool's own field-set turns `…-before-memoc.bin` into
`…-after-memoc.bin` byte for byte, reproducing the operator's 2026-09-23
transformation from committed inputs and touching exactly one byte; all three
copies of the field table agree with the decompiled `NVRAM_STRUCT.cs` field for
field; the layout claims above hold under both packings; and each refusal
leaves the variable byte-identical.

**What it does not prove:** that the efivarfs route works, that a write to this
variable is accepted by a real firmware, or that the BIOS menu appears. Those
need the machine, and they are what the hardware-test document is for.