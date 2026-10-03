# The 2021 charge-cap archaeology: what is ruled out from committed inputs, and what a recovered artifact would have to show

(Issue #83. Static reading of committed files and committed binaries. No
register is read back, no vendor stack is run, and no laptop, EC or Windows
machine is involved: every figure below comes out of a file in this repository
or a binary under `vendor/`, and each is given with the command that produces
it. Nothing here searched the network — see *What has not been searched*.)

## The claim

**Nothing committed to this repository is a 2021-era Control Center or a
2021-era EC image, so the comparison issue #83 asks for cannot be run yet. What
can be built now is the comparison itself, and building it produced a new
negative result about how a recovered artifact has to be triaged: a Control
Center's own PE version resource dates its *installer* and does not date the
service it installs.**

That is the part worth having. The rest of this file is a status page, and it
says so.

## What the issue asks, and which half of it is reachable from here

Issue #83 asks for two things: recover the 2021 Control Center / EC image that
enforced the charge cap, and *if nothing is recovered*, "document where it was
looked for and close the archaeology angle explicitly."

The first is not reachable from a GitHub-hosted runner, and the reason is
mechanical rather than a judgement:

- **No network.** Each of the `agent-*.yml` pipeline stages passes
  `WebFetch`, `WebSearch`, `Bash(curl:*)` and `Bash(wget:*)` in
  `--disallowedTools`, so no stage that plans, implements, reviews or fixes this
  issue can fetch a 2021-era installer, reach an archive, or query a vendor
  download page. (`.github/workflows/claude.yml` is the one workflow in the
  tree with no `--disallowedTools` at all, so this is a statement about the
  pipeline stages and not about every workflow.) The issue's own text concedes
  the dependency: it "cannot be done from committed inputs — needs the owner's
  old files / download history."
- **No hardware and no Windows.** `docs/findings.md` §4i's three live runs and
  §4m's `0x0522` test were done by a human at the machine. `dotnet_dump.py`
  reads a *running* process's memory and binds `kernel32` at import; it cannot
  run on a Linux runner at all.
- **The owner's files are not here.** `vendor/` holds three Control Center
  versions and one BIOS package. None is 2021-era by the issue's account, and
  the committed BIOS is dated below.

So the deliverable is the issue's second clause plus the machinery that makes
the first clause a one-command job the moment a human hands something over.

## What is ruled out from committed inputs

Four negatives, each reproducible, each a statement about *these files* rather
than about the 2021 question.

**1. The two older decompiled Control Center trees carry no EC call sites at
all, and that is not a property of those versions.** It is what an anti-tamper
casualty looks like to a text scanner.

```
$ python3 windows/tools/ec_callsites.py windows/decompiled/v3.1.6.0/   --summary
addr,addr_kind,reads,writes,writers
$ python3 windows/tools/ec_callsites.py windows/decompiled/v3.9.18.0/ --summary
addr,addr_kind,reads,writes,writers
$ python3 windows/tools/ec_callsites.py windows/decompiled/v3.1.39.0/GCUService/GCUService.MySystem --summary
addr,addr_kind,reads,writes,writers
0x078E,literal,1,0,
0x07A6,literal,6,6,BatteryProtection.SetProtectionHigh; BatteryProtection.SetProtectionLow; BatteryProtection.SetProtectionMiddle; BatteryProtection2.SetHealthProtectionHigh; BatteryProtection2.SetHealthProtectionLow; BatteryProtection2.SetHealthProtectionMiddle
0x07B9,literal,2,1,BatteryProtection2.SetBatteryChargingLimit_Up
0x07CC,literal,1,1,BatteryProtection2.SetTypeCAdaptorSwitch
0x07D0,literal,2,1,BatteryProtection2.SetBatteryChargingLimit_Down
```

The bodies are ciphertext. `windows/decompiled/v3.1.6.0/BatteryProtection2.cs`
carries 27 `Invalid MethodBodyBlock` markers and `v3.9.18.0`'s carries 23, in a
whole-tree count of 27 and 326 respectively; the decrypted 3.1.39.0 tree carries
none.

```
$ python3 windows/tools/cc_version_diff.py windows/decompiled/v3.1.6.0 windows/decompiled/v3.9.18.0
refusing to diff: the input trees carry decompiler markers
...
$ echo $?
2
```

That refusal is the deliverable for the Control Center half of the issue until
someone runs `dotnet_dump.py` on a Windows machine with a 2021-era build
installed. `windows/decompiled/v3.1.6.0/README.md` carries that procedure; it is
a human step and nothing here claims a result from it.

**2. A Control Center's *version resource* dates its installer and not the
service it installs.** This is the new result, and it changes what a human
should try to recover first.

```
$ python3 windows/tools/version_fingerprint.py --self-check
```

| committed artifact | release it is | `FileVersion` | `Assembly` version | COFF `TimeDateStamp` (UTC) |
|---|---|---|---|---|
| `vendor/control-center-3.9.18.0/setup.exe` | 3.9.18.0 | **3.9.18.0** | not a .NET assembly | `0x5CC41133` (2019-04-27) |
| `vendor/control-center-3.1.6.0/UniwillService_3.1.6.0_STD.exe` | 3.1.6.0 | **3.1.6.0** | not a .NET assembly | `0x5CC41133` (2019-04-27) |
| `vendor/control-center-3.1.39.0/MyControlCenter/GCUService.exe` | 3.1.39.0 | **1.0.2.70** | 1.0.2.70 | `0x61528305` (2021-09-28) |
| `vendor/control-center-3.9.18.0/ACPIDriver/ACPIDriver.sys` | both | *(no version resource)* | not a .NET assembly | `0x5F5F0BAF` (2020-09-14) |
| `vendor/control-center-3.9.18.0/ACPIDriverDll.dll` | both | 1.0.0.1 | not a .NET assembly | `0x5FD1D309` (2020-12-10) |

Three consequences, and the first two are what decide the recovery order:

- **The installer's version resource is self-dating.** The vendor wrote the
  Control Center release into the *installer's* own `VS_VERSION_INFO`. A
  recovered `.exe` or `.msi` from 2021 identifies itself by release.
- **No field in the installed service carries the release.**
  `GCUService.exe` out of release 3.1.39.0 reports `1.0.2.70` in both its
  version resource and its `Assembly` table, and its `ProductName` is the
  string `GCUService`. So a recovered `Program Files\OEM` tree — which is what a
  backup or a restore point gives you — **cannot be placed by release.** That is
  narrower than "undatable": its COFF link stamp and its SHA-256 are both
  there, and both place the file *relative to the committed set*.
  `GCUService.exe`'s own stamp is 2021-09-28 and `ACPIDriver.sys`'s is
  2020-09-14, so a recovered tree's link stamp is a signal worth running
  `--self-check` over — a 2021-era link stamp would be exactly the thing that
  places it in issue #83's window.
- **The two installers share one link stamp, which is why a link stamp is not a
  release date.** `0x5CC41133`, on two files wrapping two different releases.
  The stamp therefore dates something both files have in common rather than
  either release — the shared Inno Setup stub is the obvious candidate and is
  consistent with it, but that is an inference from one stamp on two files that
  differ from byte `0x158`, not a measurement. What *is* measured is the
  consequence: the two files that most obviously *are* timestampable are the two
  a timestamp would misdate into each other. This limits what the stamp is
  *for* without making it useless — the same package's own payloads post-date
  it (`ACPIDriver.sys` 2020-09-14, `ACPIDriverDll.dll` 2020-12-10, against the
  installers' 2019-04-27). And `GCUService.exe`'s stamp is later than the BIOS
  date below and earlier than its recorded install date of 2025-05-04
  (`windows/decompiled/v3.1.39.0/README.md`), so a link stamp is not an install
  date either.

**"Not found by this method," once more.** "No version resource" above means
the vendor did not write one into that file. It does not mean the file is
undated in every sense: the SHA-256 and the COFF stamp are there, and an
artifact shipped alongside any of the committed EC binaries can be placed
relative to those. The claim is narrower than it first reads.

**Nothing here dates either release.** The `vendor/control-center-*` directory
names encode a version number, not a time, and no committed file carries a
release date for 3.1.6.0 or for 3.9.18.0: `setup.ini` has no date key, neither
`vendor/` tree has a README, and `windows/decompiled/v3.1.6.0/README.md` — the
only README among them — dates the `innoextract` run that produced it
(2026-09-23), not the release. So this file does not say how far apart those two
releases are, and no interval should be read into the shared stamp: the claim it
supports is the narrower one, that one stamp spans two different releases.

**3. The committed EC image has a known identity, and no second EC image is
committed.** `docs/findings.md` §6 records it: `vendor/bios-1.09/BIOS_1.09.zip`
carries `GM7MG7P/GMxMGxx_11.800`, byte-identical to `ec/firmware/GMxMGxx_11.800`,
flashed by `ecflash.nsh` as `IFUX64.efi GMxMGxx_11.800 0 1`. The same zip's
13 MiB SPI image `GMxMGxxN109A08.ROM` carries that 256 KiB EC image a second
time, again byte-identical, and `ec/annotations/pd-image.md` §5 has already
mapped both. So a recovered 2021 image has a real baseline to diff against, and
that comparison is one command away:

```
$ python3 ec/tools/fw_image_diff.py ec/firmware/GMxMGxx_11.800 recovered-2021.bin \
      --addrs 0x07A6 0x07B9 0x07CC 0x07D0 0x0522
```

The baseline the command would report against, from the committed image:

| address | total | ec | pd |
|---|---|---|---|
| `0x07A6` (mode) | 7 | 7 | 0 |
| `0x07B9` (charge limit up) | 0 | 0 | 0 |
| `0x07CC` (complex power) | 6 | 0 | 6 |
| `0x07D0` (charge limit down) | 254 | 0 | 254 |
| `0x0522` (charge target) | 10 | 10 | 0 |

`0x07B9` at zero is `scan_refs.py`'s documented `0x07B0`-`0x07BE` blind spot,
not an absence — its header says so and `fw_image_diff.py` repeats it on every
run. Note also that `0x07D0`'s 254 sites are all PD-side: the committed tree
has no EC-side `MOV DPTR,#0x07D0` at all — §3b walked all 254 and named the gap
that leaves. This is exactly why `fw_image_diff.py` attributes every count and
every byte to a region rather than to the file.

**4. The archaeology is not the only explanation, and this change does not make
it one.** `docs/findings.md` §4l already accounts for the 2021 observation from
the *current* firmware: a young pack below every age tier puts Stationary's
200 mV/cell floor at 17400 − 800 = 16600 mV, and the screenshot's 16.654 V at
86% is what that predicts. §4i's reframe note says so in as many words: "No
different EC image or CC version is needed to account for it. The archaeology
in #83 is no longer the only path." §4l's own calibration paragraph marks the
tier as inferred from the decode and rests the 2021 reading on one screenshot,
so this file cites §4l as the later explanation and does not strengthen it,
contradict it, or reopen it.

## The BIOS date does not reconcile, and this file does not reconcile it

The issue states the owner confirmed "the BIOS was already the June-2021
version when the 2021 cap worked."

Every BIOS date committed in this repository is **2021-03-18**, for BIOS
`N.1.09A08`. Three places record it:

- `docs/hardware-identity.md`, in the hardware-identity table:
  `N.1.09A08` / `2021-03-18`;
- `docs/findings.md` §6: "The live machine runs BIOS `N.1.09A08` (2021-03-18)";
- `linux/patches/gm7mg7p-dmi-entry/PR_DESCRIPTION.md`, in the same table for
  the prepared upstream patch.

Grepping the tree for `2021-06` and `June 2021` finds no statement of a
June-2021 BIOS anywhere outside this file — the only hits are the sentences
here.

**This file does not assert that the owner is wrong**, and does not reconcile
the two dates into one. They could both be true — a June-2021 build on a machine
whose *committed* package is the March one, say, or two different machines, or
a date the owner remembers approximately. Reconciling them is a question for the
owner, and until it is answered the issue's premise that "a BIOS *version*
change is ruled out" rests on a date this repository does not corroborate. The
issue's own fallback — a BIOS *setting*, tracked separately at #86 — is
unaffected either way, since §4j records a run in which the owner had loaded
BIOS setup defaults before the session and the machine charged straight through.

## What a recovered artifact would have to show

Stated as falsifiable tests, so that whoever recovers a file knows what would
settle the question and what would not.

**A recovered Control Center installer or service build.** Triage it with
`version_fingerprint.py` first: the SHA-256 says whether it is one of the three
already committed, and the version resource says whether it is even a
version-bearing artifact. Then the comparison is:

1. Commit the decrypted tree under `windows/decompiled/v<version>/` — the
   decompilation needs `dotnet_dump.py` first, since the shipped bodies are
   ciphertext on every version measured here. A tree diffed while still
   encrypted is refused by `cc_version_diff.py`, which is the correct outcome
   and not a tool failure.
2. `cc_version_diff.py <2021 tree> windows/decompiled/v3.1.39.0/GCUService` —
   what settles it is a **mode→register write that the 2021 version makes and
   3.1.39.0 does not**, or one the two versions make to different addresses. A
   diff with no address differences is a real result and it says the two
   services reach the EC the same way; it does not say the EC behaved the same,
   because the EC is the other half of the question.
3. §4k established that on 3.1.39.0 `SetBatteryChargingLimit_Up/Down` exist and
   are never called. **Whether a 2021 version calls them is the single most
   decisive thing a recovered Control Center could show**, because those are the
   two methods that write `0x07B9` and `0x07D0` — the charge-limit pair
   `CHARGE_CTRL` and its sibling. A tree in which they are called would make
   the software half of the cap live for the first time in this repository's
   evidence.

**A recovered EC image.** The committed baseline is real and the comparison is
ready:

1. `fw_image_diff.py ec/firmware/GMxMGxx_11.800 <recovered>` and read the
   per-region rows. **A difference confined to `common`/`bank0`/`bank1` is
   EC-side; a difference only in `pd-image` is not**, and the tool's refusal to
   add them together is §3a's mistake being not repeated.
2. A *zero* differing bytes is a real result and a weak one. It means this
   byte-for-byte comparison found no difference. An access through a computed
   or indirect pointer is invisible to it exactly as it is to a `MOV DPTR,#addr`
   scan, so a firmware that reaches the same charge behaviour through a table
   walk diffs clean against one that hard-codes it. Do not read a clean diff as
   "the charge code is identical".
3. What would actually settle it is a difference in the charge-target
   computation. §4l places it in bank 0 at `0xB158`-`0xB38D`, and
   `ec/annotations/charge-target-derating.md` is the decode of it — so a
   recovered image whose bytes at `0xB158` differ from the committed ones is a
   concrete, checkable difference rather than a count.

**Neither artifact, and the question closes anyway.** §4l's explanation stands
on its own and the charge-limit thread's live question becomes the Linux side
of `0x07A6`, which is what this repository's mission actually asks for. That is
the "close the archaeology angle explicitly" branch of the issue's deliverable,
and this file is that closure: **the search space reachable from committed
inputs is exhausted, and what remains needs the owner's own files.**

## What has not been searched

Named so that the absence is a fact rather than an omission, and so that a
human does not repeat work:

- **No web archive, vendor download page, or file-sharing index.** All of them
  need `curl`, `WebFetch` or `WebSearch`, none of which any agent stage may use.
- **No search of the owner's own machine.** System Restore points, `%ProgramData%
  \Package Cache`, the OEM recovery partition, browser and mail download
  history, and any `Program Files\OEM` backup are all plausible sources and
  none is reachable from here.
- **No attempt to reconstruct a 2021 Control Center from the committed one.**
  That would be a guess wearing a diff's clothes; nothing here does it.

The search terms worth trying, in rough order of yield:

1. `UniwillService` / `Uniwill Service` installer files by date — the committed
   3.1.6.0 file is named `UniwillService_3.1.6.0_STD.exe`, so the naming
   convention embeds the version and a 2021-era file of the same shape would
   identify itself in a directory listing.
2. `GamingCenter` / `Control Center` for TongFang, filtered to 2021.
3. EC/BIOS update packages from 2021, as `.ROM` or as a flashable `.bin`.
4. The Wayback Machine's captures of the vendor's download page, if the owner
   can reach it.

Per point 1, note the finding above: an *installer* is self-dating by
release, so a directory listing of recovered files is worth more than a file's
metadata for that one question. Look for the installer first — but do run
`version_fingerprint.py` over a recovered `Program Files\OEM` tree as well
rather than setting it aside, because its link stamp and SHA-256 do place it
relative to the committed set even where no field names the release.

## What would follow from this

- **Issue #84** (proving the running EC was flashed from `GMxMGxx_11.800`
  rather than a later image) is a separate task and needs a dump the vendor
  flasher cannot make. §6 records that `ifux64.efi` has no read mode; it needs
  a follow-mode reader or an external SPI programmer. `fw_image_diff.py`
  accepts such a dump when it exists and does not claim to have produced one.
- **Nothing here moves a `registers.yaml` `status:`.** No register's behaviour
  was observed. `CHARGE_CTRL` (`0x07B9`) stays `unknown-not-absent`; the fact
  that `scan_refs.py` returns zero for it is the documented blind spot, not
  new evidence.
- **Flashing is not reading.** Re-running `ecflash.nsh`, or programming
  `GMxMGxxN109A08.ROM` "to check" a version, overwrites the thing being asked
  about. `docs/hardware-tests/pd-controller-enumeration.md` says so in the
  imperative — "do not flash `GMxMGxxN109A08.ROM` or re-run `ecflash.nsh` to
  'check' anything ... and a flash is not a read" — and the identity it cites
  for that is `ec/annotations/pd-image.md` §5's, above. The recovery route is a
  *copy of the owner's own files*.

## The tools, and how to check them

Each tool below carries a self-test that is also a run of its own, and a suite
beside it that `tools/run-tests.sh` collects:

| tool | self-test | suite | what it refuses to do |
|---|---|---|---|
| `windows/tools/version_fingerprint.py` | `--self-check` | `windows/tools/test_version_fingerprint.py` | infer a version from a sibling field, or report one from a resource it did not parse |
| `windows/tools/cc_version_diff.py` | `--self-test` | `windows/tools/test_cc_version_diff.py` | print a diff when either tree carries decompiler markers |
| `ec/tools/fw_image_diff.py` | `--self-test` | `ec/tools/test_fw_image_diff.py` | compare two images of different sizes, or attribute a PD-image byte to the main EC |

Each suite's refusal cases are written to go red when the refusal is removed,
which is the property this repository keeps asking for: a check that has
quietly stopped rejecting anything looks exactly like a check that is working.
