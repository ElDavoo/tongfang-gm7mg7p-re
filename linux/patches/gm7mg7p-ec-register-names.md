# Upstream register names for `0x0786` and the Turbo capability bit (GM7MG7P / GM5MG7Y)

Preparation for the upstream `Wer-Wolf/uniwill-laptop` contribution tracked by
issue #10. **Nothing here is opened in another repository**: §6 carries the
question text for a human to send, and this note ships no patch.

These are the two places this repository has found where upstream's spelling of
an EC register disagrees with what the DSDT, the decrypted 3.1.39.0 Control
Center service and this EC image do. Both are recorded in
[`docs/findings.md`](../../docs/findings.md) §7 ("New questions") — upstream
names `0x0786` a fan default where the DSDT and the vendor use it as the CPU
TCC offset, and upstream treats `0x0742` bit 4 as "Turbo supported" where that
bit reads clear on a machine that has Turbo.

| upstream name | what this tree shows | how far that goes |
|---|---|---|
| `EC_ADDR_FAN_DEFAULT` — a fan default at `0x0786` | the DSDT's `EC0` field list and the decrypted 3.1.39.0 service both use the byte as the CPU TCC offset, with bit 7 as the enable, and they agree with each other | this board, on two agreeing authorities and no live write test. Whether the name is wrong on *every* Uniwill board is a question — §5 |
| `FAN_TURBO_SUPPORTED` — a Turbo capability bit at `0x0742` bit 4 | the bit reads clear here while the machine has Turbo; the vendor, and the EC firmware itself, gate Turbo on `0x049F` bit 1 instead | this board, by three routes. Whether `0x049F` bit 1 is the capability bit across boards, and whether upstream ever *reads* its own bit, are both open — §4, §5 |

Every citation below is to a file already committed here, so a maintainer can
check each one offline. The upstream excerpts are pinned to the rev in
[`BASE_COMMIT`](BASE_COMMIT), which both directories under
[`linux/patches/`](README.md) were taken at. Re-fetching them at submission
time is a human's step
(`gm7mg7p-power-profile/fetch-upstream-profile.sh`).

## 1. What upstream asserts

| upstream symbol | value at the pinned rev | quoted from |
|---|---|---|
| `EC_ADDR_FAN_DEFAULT` | `0x0786` | `gm7mg7p-dmi-entry/upstream-excerpt.txt:174` |
| `FAN_CURVE_LENGTH` | `5` | `gm7mg7p-dmi-entry/upstream-excerpt.txt:175` |
| `EC_ADDR_SUPPORT_5` | `0x0742` | `gm7mg7p-power-profile/upstream-excerpt-profile.txt:132` |
| `FAN_TURBO_SUPPORTED` | `BIT(4)` | `gm7mg7p-power-profile/upstream-excerpt-profile.txt:133` |
| `FAN_SUPPORT` | `BIT(5)` | `gm7mg7p-power-profile/upstream-excerpt-profile.txt:134` |

`FAN_TURBO_SUPPORTED` is `EC_ADDR_SUPPORT_5` bit 4, so those two rows are one
statement: *upstream's Turbo capability bit is `0x0742` bit 4*. What upstream
does with that bit is a separate question, and §4 keeps the two apart.

## 2. What `registers.yaml` records

| EC address | registers.yaml entry | status |
|---|---|---|
| `0x0786` | `CPU_TCC_OFFSET (APTC/APTN)` | `present-untested` |
| `0x049F` | `BIOS_INFO_3 (Turbo mode supported)` | `present-untested` |
| `0x07CC` | `USB_C_POWER_PRIORITY` | `unknown-not-absent` |
| `0x0742` | *(no entry)* | *(no entry)* |

The last row is a real gap and worth naming plainly rather than papering over.
**`0x0742` has no entry of its own.** It is currently recorded only inside
other rows' notes — the `USB_C_POWER_PRIORITY` note carries the `0x0742` bit 5
reading, the `CHARGE_CTRL` note the `0x0742` bit 2 gate from a sibling board,
and the `BIOS_INFO_3` note the `0x0742` bit 4 comparison below. An address
with no row of its own is an address nobody has graded, so this note does not
ask a maintainer to accept a status for it; adding the row is separate work
and needs a static-reference figure this note has no new evidence for.

## 3. `0x0786`: a fan default, or the CPU TCC offset

**The DSDT and the decrypted service agree with each other, and neither of
them is the driver.** The DSDT's `EC0` field list puts `APTC` and `APTN` in the
byte at `0x786`, inside the CPU power-limit group, and the ACPI method that
writes it sets `APTN` before `APTC` — bit 7 as the enable, exactly the shape
the vendor's write has.

| dsdt field | field list | byte at | width in bits | bits in that byte |
|---|---|---|---|---|
| `APTC` | `EC0` | `0x786` | `7` | `0-6` |
| `APTN` | `EC0` | `0x786` | `1` | `7-7` |

The DSDT is not describing a fan group anywhere near that offset. The three
bytes immediately before it are `APL1`, `APL2` and `APL4` — the CPU power
limits — and the field list's next `Offset` is `0x788` (`CTWA`), with no
fan-curve field at `0x786` at all. And the vendor's decrypted service writes
the byte the way the DSDT reads it.

**The vendor's own constants table disagrees with the vendor's own code.**
`ECSpec` 3.1.6.0 and 3.1.39.0 both name `1926` (which is `0x786`)
`ADDR_L1_PWM_DEFAULT_MYFAN3`, and `registers.yaml` calls the range it names a
"live naming conflict" on the `MAIN_FAN_L_DUTY` entry and points at
`CPU_TCC_OFFSET`. So this is not vendor-versus-driver: the DSDT and the
3.1.39.0 code agree with each other, and what disagrees with both is upstream's
name and `ECSpec`'s.

| what | citation |
|---|---|
| `SetCpuTccOffset` writes `1926`, with bit 7 set on the offset when the user enables it and the byte cleared otherwise | `windows/decompiled/v3.1.39.0/GCUService/MyControlCenter.MyFan/MyFanManager_RamFan1p5.cs:2054-2066` |
| the ACPI method that writes the TCC offset sets `APTN` and then `APTC` | `evidence/acpi/dsdt.dsl:50652-50653` |
| `ADDR_L1_PWM_DEFAULT_MYFAN3` is `1926`, the ECSpec name for the same byte | `windows/decompiled/v3.1.39.0/GCUService/Define/ECSpec.cs:307` |

**The live half is a snapshot, not the transition log.** `0x0786` reads
`0x00`, and the value is in the 17:52-17:57 read-only session, not in the
delta log that follows it:

| observed address | value | read from | changed during the mode cycle |
|---|---|---|---|
| `0x0786` | `0x00` | `2026-09-23-power-mode-snapshot-dc.txt` | `no` |
| `0x0742` | `0x02` | `2026-09-23-power-mode-snapshot-dc.txt` | `no` |
| `0x049F` | `0x0A` | `2026-09-23-power-mode-snapshot-dc.txt` | `no` |

The two files are different instruments and the distinction is load-bearing.
`2026-09-23-power-mode-cycle-0700-07ff.csv` has the header `ts,addr,old,new`
and records only transitions, so **the absence of a row for `0x0786` there
means no change was observed, not that a value was read** — the `no` above is
that absence, and the `0x00` is the snapshot's. Citing the cycle log for the
value would attribute a reading to a file that never made one.
`windows/vendor-ec-map.md` already carries the `0x0786` row with the same
split, and `registers.yaml` keeps the entry at `present-untested` for the
reason below.

**What is not established.** The name `CPU_TCC_OFFSET` is a hypothesis with two
agreeing authorities, not a confirmed identification, and that is why
`registers.yaml` still says `present-untested`: nothing here has written
`0x0786` with bit 7 set and watched the TCC offset change. A readback of
`0x00` is not that test either — a register write being accepted is not
evidence the EC acts on it. And whether upstream's name is wrong for *every*
Uniwill board, or only for this one, **cannot be settled from a single
machine.** That is a question, not a finding, and it is why no rename is
proposed here; §5 lists what would answer it.

## 4. The Turbo capability bit

**On this board the gate is `0x049F` bit 1, by three routes that do not share
a source.** The live value is `0x0A` — bit 1 set — and `0x0742` is `0x02`, so
upstream's bit 4 is clear on a machine whose vendor offers Turbo. The snapshot
session records the machine in OperatingMode 2 (Turbo), and the cycle capture
that follows moves `0x0751` through `0x10`, `0xA0` and `0x00` in turn, so
Turbo was entered and left during the run. Neither address appears in that
delta log, so both held across it.

**The EC firmware agrees, which is what makes this a firmware fact rather than
a Windows convention.** [`docs/findings.md`](../../docs/findings.md) §7a records
the EC's own Turbo path (`0xABE8`/`0xC741`, behind `0x049F` bit 1) producing
`0x10`. A Windows service and an 8051 program agreeing on a bit number is
worth more than either alone.

**Two unrelated vendor classes read the same byte, the same bit, with the same
meaning.** `GetTurboModeSupport` returns 0 unless it is set; `GetFanModeCount`
returns `3` fan modes instead of `2` when it is set. Neither calls the other —
the first is reached from the fan managers and from `CustomizeCtrl`, the
second once from `TrayCtrl`'s own initialiser — and the second carries a
separate `GetBridgeType()` override of its own. So this is two separate
functions coinciding on a bit number, not one function reached twice.

| what | citation |
|---|---|
| `GetTurboModeSupport` reads `1183` and returns 0 unless bit 1 is set | `windows/decompiled/v3.1.39.0/GCUService/MyECIO/MyEcCtrl.cs:84-93` |
| `GetFanModeCount` reads the same `1183`, tests the same bit 1, and returns `3` instead of `2` | `windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/TrayCtrl.cs:97-111` |
| `GetTypeCAdaptorPrioritySupport` reads `1858` and tests bit 5, not bit 4 | `windows/decompiled/v3.1.39.0/GCUService/MyECIO/MyEcCtrl.cs:95-103` |
| `ADDR_BIOS_INFO_3_BYTE` is `1183`, the ECSpec name for the byte Turbo is gated on | `windows/decompiled/v3.1.39.0/GCUService/Define/ECSpec.cs:129` |
| `ADDR_SUPPORT_BYTE5` is `1858`, the ECSpec name for `0x0742`; it names no bit at all | `windows/decompiled/v3.1.39.0/GCUService/Define/ECSpec.cs:251` |

`1183` is `0x049F` and `1858` is `0x0742`, so those two rows are the same two
bytes from the other direction.

**No callsite in the service reads `0x0742` bit 4, and none writes `0x049F`.**
Both halves are one grep over the committed census, reproducible offline:

```console
$ grep -n ",0x049F," windows/decompiled/v3.1.39.0/ec-callsites.csv
467:MyControlCenter/TrayCtrl.cs,101,MyControlCenter.TrayCtrl,GetFanModeCount,read,0x049F,literal,1183,ref Data
860:MyECIO/MyEcCtrl.cs,87,MyECIO.MyEcCtrl,GetTurboModeSupport,read,0x049F,literal,1183,ref Data

$ grep -n ",0x0742," windows/decompiled/v3.1.39.0/ec-callsites.csv
55:LightingModel/WKDColor.cs,46,LightingModel.WKDColor,,read,0x0742,literal,1858,ref Data
861:MyECIO/MyEcCtrl.cs,98,MyECIO.MyEcCtrl,GetTypeCAdaptorPrioritySupport,read,0x0742,literal,1858,ref Data
```

Every site is a read. `0x049F` has no writer anywhere in the service, which is
what a byte the host only reads looks like. The two
`0x0742` sites read the byte; the one that tests it tests **bit 5**, for
TypeC-adaptor priority, not bit 4. (That bit-5 divergence is a third
disagreement, out of scope here, and it belongs in the issue tracker.)

**The claim deliberately not made.** `FAN_TURBO_SUPPORTED` appears in the
committed excerpts only in its `#define` and in the excerpt files' own
bracket annotations. Nothing in the quoted fragments shows it being read.
That is *not found by these fragments* and never "upstream never reads it" —
the committed excerpts are a selection, and one grep of a maintainer's own
tree settles it. The difference matters: "upstream has a wrong bit" and
"upstream has an unused bit that would be wrong if used" are different
findings, and only the first justifies a change. `§7` below records the
decline, and `tools/check_upstream_register_names.py` holds it against the
excerpts rather than against this sentence.

**What is not established.** Whether `0x049F` bit 1 is *the* Uniwill
capability bit, or something this board family or this BIOS sets, is open. The
ECSpec name for it is `ADDR_BIOS_INFO_3_BYTE`, which is neutral-to-suspicious
for "capability", and is why §5 asks for a board without Turbo rather
than assuming one can be found for it here.

## 5. What a maintainer would need from other boards

Each item is tied to the claim it would settle, and none of them can be
answered from this repository.

For `0x0786`:

1. **The DSDT field list at the same offset, on at least one other Uniwill
   board.** The `iasl` decompile is committed here, so this is a reproducible
   ask rather than a favour: does the byte at `0x786` carry `APTC`/`APTN`
   there too? If it does on every board, the name is wrong everywhere; if it
   is fan data on some, the name is right on those and the fix is per-board.
2. **Whether any board genuinely has a fan-curve block at `0x0786`, and where
   that block starts.** `FAN_CURVE_LENGTH 5` implies a five-byte curve, while
   upstream's `EC_ADDR_FAN_DEFAULT` names a single byte. Those are different
   claims about the same address and a maintainer can settle it from a tree
   they already have. Worth asking on its own — it is the question that
   decides whether §1 is a rename or a misreading.
3. **Whether the name was taken from one board's disassembly or from vendor
   documentation.** This changes what a correct fix looks like: a name copied
   from one board's ASM should probably become a per-board alias, not a
   global rename.

For the Turbo bit:

1. **`0x0742` and `0x049F` raw values on a Uniwill board with no Turbo mode.**
   This is the decisive test. If `0x049F` bit 1 is clear there, it is a
   capability bit; if it is set anyway, it is not, and the correct gate is
   something this note has not found.
2. **The same two bytes on a second board that does have Turbo**, to show the
   bit is not simply this BIOS revision.
3. **Whether `FAN_TURBO_SUPPORTED` is read anywhere in current upstream, and
   on which boards.** One grep. If nothing reads it, the disagreement is
   latent rather than live, and the answer is a note rather than a patch.
4. **The ECSpec name for `1183` and `1858` in a service version other than
   3.1.6.0 / 3.1.39.0.** The 3.9.18.0 build in this tree agrees with both, so
   the name looks settled; what is *not* settled is whether a name that
   neutral is a capability bit at all.

**The alternative to a global rename, so the choice is real.** A DMI-gated
`#define` that spells `0x0786` as the TCC offset only for boards whose field
list says so, with `EC_ADDR_FAN_DEFAULT` kept for the rest, is a smaller and
safer change than renaming the constant. A per-board alias is the same idea
one level down. This note does not push either; it says a change is probably
warranted for *this* board and leaves the deciding question to §6.

## 6. The question text to put upstream

Drafted to be sent by a human, and to be stripped of the citations when it is.
Nothing below is a claim that a rename is already agreed.

> Two register names disagree with what the DSDT and the vendor's own service
> do on a GM7MG7P / GM5MG7Y, and I cannot tell from one board whether the
> names are wrong everywhere or only here.
>
> **`EC_ADDR_FAN_DEFAULT` (`0x0786`).** This board's DSDT puts `APTC` (7 bits)
> and `APTN` (1 bit) in that byte, in the CPU power-limit group, right after
> `APL1`/`APL2`/`APL4`, and the ACPI method that writes it sets `APTN` before
> `APTC`. The vendor's Control Center service writes the same byte as a CPU
> TCC offset with bit 7 as the enable, and its own `ECSpec` table calls the
> same decimal a fan PWM default. The byte reads `0x00` here and I have never
> seen it written. I have not established that the name is wrong on other
> boards, which is why I am asking rather than sending a rename — but on this
> board the name does not describe the byte, and `FAN_CURVE_LENGTH 5` also
> implies a five-byte block where I can only find one byte.
>
> **`FAN_TURBO_SUPPORTED` (`EC_ADDR_SUPPORT_5` bit 4, `0x0742`).** On this
> board `0x0742` reads `0x02`, so bit 4 is clear, and the machine has Turbo.
> The vendor gates Turbo on `0x049F` bit 1 instead, which reads `0x0A`, and so
> does this machine's EC firmware in its own Turbo path — a driver using the
> `0x0742` bit would decide this laptop has no Turbo mode. Two questions: is
> `FAN_TURBO_SUPPORTED` read anywhere in the driver today, and has anyone seen
> `0x049F` bit 1 on a board without Turbo? A board without Turbo is what would
> tell us whether bit 1 is a capability bit or a per-BIOS one.

## 7. Calibration

| claim | kind | standing |
|---|---|---|
| `0x0786` reads `0x00` on this board | this-board | confirmed-live |
| `0x0786` carries the CPU TCC offset, with bit 7 as the enable | this-board | hypothesis-agreeing-sources |
| the name `EC_ADDR_FAN_DEFAULT` is wrong for every Uniwill board | cross-board | not-established |
| `FAN_CURVE_LENGTH 5` describes a real block at `0x0786` on some board | cross-board | not-established |
| `0x049F` bit 1 is the Turbo gate on this board | this-board | confirmed-static |
| `0x049F` bit 1 is the Turbo capability bit across Uniwill boards | cross-board | not-established |
| no 3.1.39.0 callsite writes `0x049F` | pinned-source | confirmed-static |
| no 3.1.39.0 callsite reads `0x0742` bit 4 | pinned-source | confirmed-static |
| upstream reads `FAN_TURBO_SUPPORTED` | upstream-use | not-established |
| upstream's `0x0786` name came from disassembly rather than documentation | upstream-use | not-established |

**What each standing rests on.** `confirmed-live` is a value in a committed
capture, cited by path in §3. `confirmed-static` is read off committed source
— the DSDT, the decrypted service, the vendor's own constants, the callsite
census — and is re-derivable offline. `hypothesis-agreeing-sources` is two
independent authorities that agree with each other and no live test that
they are right; that is the whole of the `CPU_TCC_OFFSET` identification.

**`not-established` is the interesting column, and it is a refusal rather than
a hedge.** Those rows split into what this repository cannot answer from one
machine and what it cannot answer about upstream's own tree. Nothing in
this note was observed live: the snapshot and the cycle capture are cited
by path, and no register was read or written for it. The decisive observation
for the Turbo question — a Uniwill board without Turbo — needs another
machine and a human at it, which is why §5 asks for it rather than
predicting it.

**The sentences below are deliberately weaker than they could be**, and that
is load-bearing:

- `FAN_TURBO_SUPPORTED` is **not found being read** in the committed
  excerpts, which is a statement about a selection of fragments rather than
  about upstream's code. §4 says so where the claim is made, and a maintainer
  settles it with one grep.
- `0x049F` bit 1 is the Turbo gate **on this board**. The same bit may or may
  not be the general capability bit, and `present-untested` on the
  `BIOS_INFO_3` row is the honest status for the same reason: the EC
  reference count and the live read agree with each other, and neither is the
  write-and-watch test that would settle it.

**A citation correction carried over from the issue that asked for this
note.** The issue filed for it cited
`evidence/ec-watch/2026-09-23-power-mode-cycle-0700-07ff.csv` for `0x0786`
reading `0x00` "through the whole capture". That file is a delta log: its
header is `ts,addr,old,new` and it records transitions, so it never read
`0x0786` at all. The value is in the separate snapshot session immediately
before it. §3 cites each for the half it can actually support — the value from
the snapshot, the unchanged-across-the-cycle claim from the log's silence —
because a value attributed to a transition log is an overclaim in the shape of
a citation, which is the one this repository's own rules are most careful
about.

## What is deliberately not here

- **No `.patch`, and no draft PR description to paste.** The two patches
  already in this directory are alternatives against the same rev and conflict
  at the descriptor hunk (see
  [`gm7mg7p-power-profile/PR_DESCRIPTION.md`](gm7mg7p-power-profile/PR_DESCRIPTION.md)),
  and a header rename is a separate change with its own review path. Per
  [`docs/findings/power-profile-gm7mg7p.md`](../../docs/findings/power-profile-gm7mg7p.md),
  the `0x0786` rename was already ruled "prose in the PR body, not part of
  this patch". Drafting the rename once §5's questions are answered is the
  follow-up.
- **No `0x0742` row in `registers.yaml`.** It would need a static-reference
  figure this change has no new evidence for, and `registers.yaml` is a
  structured file every other open branch edits. The gap is named in §2
  instead.
- **The `0x0742` bit 5 divergence.** Upstream calls bit 5 `FAN_SUPPORT`; the
  vendor's `GetTypeCAdaptorPrioritySupport` calls the same bit TypeC-adaptor
  priority. It surfaced while checking §4 and belongs in the issue tracker,
  but it is a third disagreement and this note is about the two the issue
  named.
- **Nothing opened in another repository.** No PR, no issue and no comment
  against `Wer-Wolf/uniwill-laptop`; #10 tracks the eventual submission.

## The check that holds this note

[`tools/check_upstream_register_names.py`](../../tools/check_upstream_register_names.py)
holds every citation above against the committed file it names — the upstream
excerpts, `registers.yaml`, the decompiled sources, the snapshot and the cycle
log, and the DSDT field list, which it derives rather than takes from a
transcription here. Its two refusals that are not about accuracy are the two
this note's calibration depends on: a citation to a `0x0742` row in
`registers.yaml`, which does not exist, and a claim that upstream *reads*
`FAN_TURBO_SUPPORTED`, which the committed excerpts do not show.
[`tools/test_check_upstream_register_names.py`](../../tools/test_check_upstream_register_names.py)
drives each refusal over a copy and asserts it goes red *and names the
problem*. Neither is wired into a gate — `.github/scripts/agent-gates.sh` is
copied from `ElDavoo/agent-pipeline` and the change is upstream's to make;
`bash tools/run-tests.sh` runs the suite.
