# Does the memory-OC unlock work through efivarfs on Linux?

**Status: not run (issue #118).** This procedure was written by the pipeline,
which has no machine to run it on — `CLAUDE.md` is explicit that the
GitHub-hosted runners cannot reach the hardware. The tool
([`linux/uniwill-var/`](../../linux/uniwill-var/README.md)) and its offline
suite are committed; the write is not. Nothing in this file reports a result,
and nothing under `evidence/` comes from it.

The one thing in the tree that *is* a result is
[`evidence/uefi/2026-09-23-memory-menu-observation.md`](../../evidence/uefi/2026-09-23-memory-menu-observation.md):
the owner's 2026-09-23 **Windows** write of the same byte through
`windows/tools/uniwill_set.py`, after which the "Memory" entry appeared. That
established the mechanism and the menu. It is not a run of this procedure, and
it says nothing about whether the efivarfs route reaches the same place —
`docs/findings.md` §8 says in terms that the Linux route *"has not been
exercised; only the Windows write above has been."* That sentence is what this
file is for.

**Prediction, stated before the run so it can be wrong.** If the efivarfs entry
for this variable holds `07 00 00 00` as its first four bytes — NV|BS|RT, the
attributes `evidence/uefi/2026-09-19-UniWillVariable.txt` records for the live
variable — then a write of `MemoryOverClockSwitch` 0x00 → 0x01 through efivarfs
will be accepted and survive the reboot, and the BIOS setup's Advanced page will
show the "Memory" entry, because `OemOcDxe` copies `UniWillVariable[0x33]` into
`Setup[0x7D7]` on every boot whatever wrote it. If the first four bytes are
anything else, **stop**: the framing assumption is wrong, the offsets in this
procedure are addressing the wrong bytes, and the first four bytes themselves
are the more interesting result.

The prediction is about the *bytes*, and it is deliberately not about the menu
being guaranteed. Two independent things could each break the second half
without the first half failing: the vendor service could rewrite the whole
cached block before the reboot (§8's caveat), or the write could be accepted
and the menu still not appear. §4 separates these.

## 1. The question

One byte, one variable, one mechanism — `docs/findings.md` §8 has it in full and
there is no reason to restate it here beyond what a run needs. `OemOcDxe` copies
`UniWillVariable[0x33]` into `Setup[0x7D7]` at boot (RVA 0x7A8,
[`bios/decompiled/OemOcDxe.annotated.c`](../../bios/decompiled/OemOcDxe.annotated.c));
`Setup[0x7D7]` is IFR question `0xEC6`, the suppress-if around the Ref "Memory"
on the vendor Advanced form `0x2712`; and that Ref leads to Intel's form
`0x27B1`, "Memory Overclocking Menu".

`UniWillVariable` is NV|BS|RT, so the OS may write it. On Linux that is
`/sys/firmware/efi/efivars/`, one file per variable, 4 bytes of attributes then
the data, immutable until the flag comes off.

Two things this run adds to §8, and only two: whether the **efivarfs route**
works, and whether the framing is what §8 says it is. It is not a test of the
mechanism — that is done, and re-testing it through a different syscall is not
new knowledge about `OemOcDxe`.

## 2. Before you start

- **The machine must have booted UEFI, not CSM.**
  `/sys/firmware/efi/efivars` does not exist on a CSM boot and never will. If
  `ls /sys/firmware/efivars` says no such directory, stop: this procedure does
  not apply and no amount of retrying will create it.
- **Root.** efivarfs is root-only.
- **`python3` from the repository root**, and a checkout of this repository at
  the revision you are running. The tool is two files and no dependencies
  beyond the standard library.
- **A way back.** §3 writes a backup the tool refuses to overwrite, and §3's
  `restore` puts it back. Do the read-only half first.
- **Nothing that rewrites the block between the write and the reboot.** This is
  the single most likely way to get a null result. The vendor service caches
  the whole struct at `Init()` and writes the whole cached copy back on any
  field change (§8), so **do not open Control Center, do not change power mode,
  do not let a Control Center background sync run** between §3's write and the
  reboot. On Linux there is no Control Center, but check for a
  `UniwillControlCenter`/`GCUService`-equivalent process and for anything else
  with a UEFI-variable daemon. Record what you found either way; "the service
  was not running" is a fact about the run, and its absence is the difference
  between a null result and an untested one.
- **A note of the wall-clock time of the write**, by hand. The dumps are not
  timestamped, and the reboot time is what pairs them.

## 3. The run

Three commands. The first is read-only and is the pre-flight; **read its output
before running the second**, because it is where the framing assumption is
either confirmed or refuted.

```console
# <date> is that run's YYYY-MM-DD. §6 names the finished files the same way, so
# following this produces the §6 files with no rename step.
#
# The pre-flight. Two halves: the tool finds the entry itself (it globs
# UniWillVariable-* and checks the GUID digits, tolerating either spelling of
# the GUID rather than hardcoding the path docs/findings.md §8 gives, which is
# the dashed form efivarfs actually writes) and prints the decoded variable;
# od prints the raw first four bytes so the framing claim is checked against
# bytes rather than believed.

sudo python3 linux/uniwill-var/uniwill-var.py show \
        --save evidence/uefi/<date>-UniWillVariable-linux-before.bin

sudo od -An -tx1 -N4 /sys/firmware/efi/efivars/UniWillVariable-* \
        > evidence/uefi/<date>-UniWillVariable-linux-attrs.txt
```

**Stop here if the first four bytes are not `07 00 00 00`.** The rest of this
procedure assumes a 4-byte attribute prefix followed by a 180-byte
`NVRAM_STRUCT`, and those bytes are the evidence for that. Whatever they
actually are is worth committing on its own — see §6.

Then the write, and the readback of the same byte from a second process:

```console
# The write. --backup is mandatory and the tool refuses to overwrite an
# existing file, so pick a name that is not already there. The backup lands in
# evidence/uefi/ under the same <date> so §6's list is what follows.
#
# What this prints on success is that the 184 bytes written are the 184 bytes
# read back. That is a transport check. It is not evidence the EC or the BIOS
# did anything, and it is the shape of docs/findings.md §4a's error.

sudo python3 linux/uniwill-var/uniwill-var.py set MemoryOverClockSwitch 1 \
        --backup evidence/uefi/<date>-UniWillVariable-linux-backup.bin
```

```console
# Read it again from a fresh process, and save it under the name §6 lists. This
# is the dump that pairs with the before-dump.

sudo python3 linux/uniwill-var/uniwill-var.py show \
        --save evidence/uefi/<date>-UniWillVariable-linux-after.bin
```

**Then reboot, and touch nothing that could rewrite the block.** Not Control
Center, not a power-mode change, not a settings app. Enter BIOS setup and look
on the **Advanced** page for a "Memory" entry, and write down in §4's style
what you see — including, if you see nothing, that you saw nothing.

Do not change anything inside the menu. §7 says why, and it is §8's reason:
the voltage override at `SaSetup[0x03]` is the one knob to leave alone until
someone knows what this board's regulator does with it, and any live test of
the menu's settings is a separate issue with its own procedure.

## 4. What to read off

Three observations, and the order matters — the first is worth most and the
third is worth least.

### 4.1 The four attribute bytes

`07 00 00 00` is the prediction. Anything else is a real finding about the
framing, not a failed run, and it invalidates every offset in §3. Record the
bytes as they are.

### 4.2 The byte changed, and only that byte

`cmp evidence/uefi/<date>-UniWillVariable-linux-before.bin
evidence/uefi/<date>-UniWillVariable-linux-after.bin` should differ at byte
0x33 and nowhere else. The 2026-09-23 Windows pair behaved exactly this way
(`evidence/README.md`), so this is the shape the mechanism predicts.

A difference **anywhere else** is a finding in its own right and needs its own
note: something else is writing this variable, and §8 already has one open
question of exactly that shape (who zeroes `MemoryOverClockSupport` at 0x60).

### 4.3 The menu entry

Look on the Advanced page for "Memory". Four outcomes, all reportable:

- **It appears.** The efivarfs route reaches the same place the Windows route
  did. This is the result the procedure is for.
- **It does not appear, and the byte survived the reboot.** §8 lists what can
  do this: `CpuSetup[0x1B7]` ("OverClocking Feature") being 0, which suppresses
  the Ref independently; or a `Setup` load-defaults having run. Both are
  checkable and neither is the efivarfs route failing.
- **It does not appear, and the byte was reverted before the reboot.** Then
  something rewrote the block, which is the caveat §2 asks you to watch for. The
  before/after dumps and the wall-clock note are what say so.
- **The `set` was refused, and the entry is byte-identical to the before-dump.**
  A refusal is `set` exiting non-zero with the tool's own message — the backup
  path already taken, an immutable flag that would not clear, or the kernel
  refusing a rewrite of an entry that already exists. That last one is the shape
  this pipeline cannot test and that
  [`linux/uniwill-var/README.md`](../../linux/uniwill-var/README.md) declines
  to claim either way, so it is the likeliest way the run goes sideways. **A
  `cmp` reporting no difference at 0x33 is the expected result here, not a
  mistake**: nothing was written, so nothing changed. Record the tool's message
  verbatim and the `cmp` output, and stop — there is no reboot to do. §7 says
  what such a report owes the reader.

Note the shape of a negative here: **a matching readback is not the menu
appearing**, and neither is a clean reboot with the byte still set. The menu
appearing is the only observation that closes this, and it is a human's.

### 4.4 The report

Write the observation to §6's fifth file, in the style of
[`evidence/uefi/2026-09-23-memory-menu-observation.md`](../../evidence/uefi/2026-09-23-memory-menu-observation.md):
board, BIOS version, kernel version, what you ran, the four bytes, the `cmp`
result, the reboot, and the owner's own words about what was on screen. That
last file's **Scope** section — what was and was not established — is the part
worth copying, because the temptation after a successful run is to claim the
whole menu was exercised when only its visibility was.

## 5. What this cannot settle

- **Anything inside the menu.** Whether the XMP profiles are offered (which
  depends on the fitted DIMMs' SPD), whether any timing or voltage setting is
  honoured by memory training on the i7-10875H, and whether this board can move
  VDDQ at all. All separate issues with their own procedures; §8 flags the
  voltage knob as the one to leave alone first.
- **What `GPP_B22` drives.** §8 records that `OemOcDxe` drives it high when the
  switch is 1 on a CNL/CML-H PCH and never drives it low again, and that what it
  is wired to cannot be read from the BIOS. It is observable on Linux —
  `pinctrl-cannonlake` exposes the pad under debugfs — but that is its own
  question, not this one.
- **The other 180 bytes.** This procedure changes one byte. It says nothing
  about the 17 fields past `0x42` whose offsets depend on the unresolved
  `Pack` question, and nothing about whether the vendor's own code agrees with
  the alignment this tool assumes. `linux/uniwill-var/README.md` has the
  derivation; the point here is that a successful run at 0x33 does not settle
  the layout for a field at 0x60.
- **The Windows route, or the vendor service.** Whether the service still
  rewrites the block on this machine, and whether `SetUserProfile()` would put
  0x33 back, is a question about the service. A Linux run cannot see it.
- **A second board.** One machine, one firmware (`GMxMGxx_11.800`). See
  [`docs/related-projects.md`](../related-projects.md).

## 6. Where the output goes

Name the files the way the existing UEFI evidence does, so the Linux pair sits
beside the Windows one and reads as the same variable:

```
evidence/uefi/<date>-UniWillVariable-linux-attrs.txt
evidence/uefi/<date>-UniWillVariable-linux-before.bin
evidence/uefi/<date>-UniWillVariable-linux-backup.bin
evidence/uefi/<date>-UniWillVariable-linux-after.bin
evidence/uefi/<date>-UniWillVariable-linux-observation.md
```

`<date>` is that run's YYYY-MM-DD. §3's commands produce the first four with the
names above, in the order they are run, so following this produces these files
with no rename step.

The fifth is written by hand, from §4.4: **it is the observation file, and only
a person can produce it.** The other four are what the tool wrote; the
observation is what it is *for*, and a run that stops at the four byte dumps has
produced the transport evidence and nothing else.

The backup is the fourth-named `bin` and it is the restore arm, so keep it: if
the run goes wrong, §3's `restore` puts the original back and nothing else in
this repository depends on the machine being in any particular state.

Add each file to [`evidence/README.md`](../../evidence/README.md), the index
every findings claim cites through, and say in the entry what the run was: the
board, the BIOS version, the kernel version, whether the vendor service was
running, the four attribute bytes, the `cmp` result, and the reboot. None of
that is in the dumps.

## 7. What a result has to say

**Both outcomes are reportable, and this file is not written as though only one
closes the issue.** Concretely:

- **§4.3 shows the entry appearing.** The efivarfs route reaches the same place
  the Windows route did, and §8's "For Linux" paragraph can be extended to say
  so — in place, leaving the original sentence readable beside the addition,
  per `CLAUDE.md`. The paragraph's *path spelling* needs no correction: the
  dashed GUID it gives is the filename efivarfs writes, and
  [`linux/uniwill-var/README.md`](../../linux/uniwill-var/README.md) records
  the glob that finds the entry without hardcoding it.
- **§4.1 shows different attribute bytes.** That is a finding about the framing,
  and it is worth more than a successful run would have been: it says the whole
  §8 Linux paragraph rests on a byte order that this machine does not have, and
  the offsets need re-deriving against the bytes actually there.
- **§4.2 shows a difference at a byte other than 0x33.** Another writer exists
  and it is not the tool. That is §8's open question about who rewrites the
  block, with a second writer to name.
- **§4.3 shows the write was refused.** Nothing was written, so the route is
  untested rather than shown to fail, and the report says exactly that: the
  tool's refusal message, the `cmp` showing the entry unchanged, and the
  question it opens — whether efivarfs accepts a plain in-place rewrite of an
  entry that already exists. That is worth more than a silent retry would have
  been, and it does not close anything.
- **The run does not happen.** That is not a failure of this file. The issue
  stays open, nothing is committed to `evidence/`, and §8's sentence stays
  exactly as true as it is now.

And the sentences a result **must not** produce, which is §4a's trap in new
dress and the reason this section exists:

- Not **"the write was accepted, so the menu is unlocked."** A matching readback
  is a transport check. The tool says so in its own output on every successful
  write.
- Not **"the efivarfs route works"** on the strength of a byte that survived to
  the next `show`. It survived to the next `show`; the menu is §4.3's, and it
  is a human's.
- Not **"the memory overclocking menu is enabled"** as a summary of §4.3. What
  was established is that an *entry* became visible. Nothing inside it was
  touched, and §5 lists what that leaves open — first among it the VDDQ
  override, which §8 orders any future run not to touch before the SPD-advertised
  XMP profile.
- Not any sentence implying the tool was run by the pipeline. It has not been,
  on any machine, and `docs/findings.md` §8's "That route has not been
  exercised" is true until a human's files say otherwise.