# Is the `ITE8850-PD` image on a controller of its own, and is it enumerable?

**Status: not run (issue #26).** The pipeline that wrote this file has no
machine to run it on — `CLAUDE.md` is explicit that the GitHub-hosted runners
cannot reach the hardware. **No bus scan, no `/sys/class/typec/` read, no UCSI
enumeration and no `/dev/mem` read of the EC window has happened on this
board.** Nothing in `ec/annotations/registers.yaml`, [`../findings.md`](../findings.md)
or [`../../ec/annotations/pd-image.md`](../../ec/annotations/pd-image.md)
records one, and there is no `evidence/` file covering USB-C or Type-C at all.
The instruments named below are committed; the readings are not. §5 says what a
result has to say, and **both** outcomes of §4a are reportable.

The question is the one `pd-image.md` §5.2 leaves open, in its own words: a
single 256 KiB `ecflash.nsh` write updates the EC firmware and the PD firmware
together, which is consistent with a shared SPI flash and therefore narrows the
"the EC hands off a payload" story — but it does not establish how many dies are
involved. One flash holding two images is compatible with one die running both
programs, with two dies behind one flash, and with a die that hands the second
image to a part over a link this evidence does not name. **This is a hardware
observation and nothing static can settle it.**

## 1. The question

`ec/firmware/GMxMGxx_11.800` is two programs in one file. The main EC is
Keil-banked and reaches its hardware through a memory-mapped window at
physical `0xFE410000` (`ec/tools/ecmem.py`, the same path the vendor's
`ACPIDriver.sys` ECRW method takes). The `ITE8850-PD` image at file
`0x20000` is a self-contained 8051 program in its own 64 KiB address space
with its own vector table, its own XDATA allocation and its own C startup stub
(`pd-image.md` §1, §2, and `lightbar-bat-flow.md` §2). The two images ship in
one 256 KiB write (`pd-image.md` §5), and **which part of the board executes
the second one is not something the bytes say.**

So the concrete, cheap form of the question is: **does the running board
present a second responder — on a bus, or as a Type-C partner port — that this
repository has no other explanation for?** A responder the EC does not account
for, or a Type-C port with a live partner, is the shape a separate PD
controller would take. Nothing found is equally reportable: it says the kernel
and the buses expose no such device, which narrows the topology just as much
as a hit does, and points the next pass at the SPI layout's descriptor table
(`pd-image.md` §5.1's open question) rather than at enumeration. **Both are
worth an hour, and the second is the one that makes the driver question
answerable at all.**

**What cannot be asked here, and why.** An earlier draft of this file made the
primary read a lookup of the PD image's interrupt-selector table at
`0x0151`-`0x015F` through the EC window, on the reading that those five
addresses are XDATA. **They are not** — `pd-image.md` §2.1 now records the
correction: they are CODE constants inside the PD image, and a `MOV DPTR`
immediate does not name a space. A read of the EC's window at `0x0151` returns
the EC's own XDATA there, which is a different memory, so it could not have
returned what the old §5.1 said it would and could not have discriminated
anything: the selector table's contents are already known from the image
offline, with no hardware at all. **The read is kept, demoted, in §4d, as a
baseline of the EC's memory and nothing more.**

## 2. Before you start

- A machine: this is a TongFang GM7MG7P / Uniwill GM5MG7Y. Record
  `sudo dmidecode -s system-product-name` and the EC/BIOS version you are on
  into the capture header — a run on a different EC revision is a different
  question, and `ecflash.nsh` names `GMxMGxx_11.800`, so the EC firmware
  version matters more here than usual.
- Root for §4a-§4c. Root and `CONFIG_DEVMEM` for §4d; `ec/tools/ecmem.py`
  documents that on this machine the `INTC1036:00` window is listed in
  `/proc/iomem` and `/dev/mem` access to it works despite `IO_STRICT_DEVMEM`.
- Nothing installed, nothing flashed. This run is read-only in intent
  throughout; there is no write step anywhere in this document, and **do not
  run any `ecmem.py write`, and do not flash `GMxMGxxN109A08.ROM` or re-run
  `ecflash.nsh` to "check" anything** — `pd-image.md` §5 already settled that
  the committed image is byte-identical to both, and a flash is not a read.
- Linux arm is the primary one (`ecmem.py`, `i2cdetect`, `lsusb`, `lspci`,
  `dmesg`). §4f is the Windows arm and needs the vendor ACPI driver installed,
  which is the `ACPIDriver.sys` path `ecmem.py`'s docstring names.

### Safety

There is no write step and nothing is flashed. Two cautions are still real:

- **`i2cdetect` is a bus scan, not a passive read.** `i2cdetect -r` issues an
  SMBus read transaction to every address on the bus, and a device that
  misbehaves on an unexpected read can misbehave. The EC sits on the same
  buses this document scans, so **prefer `i2cdetect -r`, take it one bus at a
  time, and stop if the machine misbehaves** rather than pressing on. If the
  scan is not worth that risk on this particular machine, §4b and §4c are
  passive and can be run alone — say in the capture that §4a was skipped and
  why, because a skipped primary read is a gap in the record, not a result.
- **§4d's read opens `/dev/mem` read-only.** Reading an address the running EC
  is actively using is safe, but **capture a full baseline before and after**
  so that a misread is visible as a change rather than assumed to be a value.

## 3. What to record

One text file, the usual shape: the commands, their full output, and the
timestamp of each. Commit it under `evidence/` when it is done, and add a line
to `ec/annotations/pd-image.md` §5.2 saying which §4 branch came out. Until
then, both the page and this file say the question is open, and that is the
sentence every downstream claim has to carry.

## 4. The run

### 4a. The bus census — is there a responder that is not the EC?

The primary read. Record the full list, not just a hit: this is a census, so a
later pass can tell a new device from a known one.

```console
$ sudo i2cdetect -l
$ for d in $(sudo i2cdetect -l | sed 's/^i2c-\([0-9]*\).*/\1/'); do
      echo "== i2c-$d"; sudo i2cdetect -y -r "$d"; done
```

A device at an address the EC also uses is **not** a PD controller — the EC
sits on the same bus in most Uniwill designs, and an address collision is the
expected result, not a surprise. What would count is an address that responds,
is stable across reboots, and is *not* the EC's own. Repeat the scan after a
reboot and diff the two lists: a responder that moves is not evidence of a
part.

### 4b. The Type-C side — what the kernel already exposes

Passive, and often the cheapest thing in the document.

```console
$ ls -l /sys/class/typec/ 2>&1
$ for d in /sys/class/typec/*/; do
      echo "== $d"; cat "$d"/{vendor,model,uevent} 2>&1
      echo "-- partner:"; ls -l "$d"partner* 2>&1; done
$ ls /sys/bus/i2c/drivers/ucsi 2>&1
$ ls /dev/ucsi* 2>&1
$ ls -l /sys/kernel/debug/ucsi 2>&1
```

A **`partner` port is the strongest single thing this run can find**: it is the
kernel reporting a real Type-C connection on the far side of a port, which is
what a separate PD controller looks like from here. `uevent` names the
connector and mode. A `ucsi` device bound and readable means the kernel is
already talking to whatever handles that port, and its driver is the next place
to look.

Empty output and a missing `/sys/class/typec/` are both reportable and neither
is a negative finding about the hardware: it says the kernel exposes no Type-C
class device, which is a statement about the kernel's driver set on this board
and about nothing else. Record it as that — not as "no PD controller".

### 4c. PCI, USB and the boot log

```console
$ sudo lspci -nn 2>&1
$ sudo lsusb -t
$ dmesg | grep -iE 'i2c|typec|ucsi|usb-pd|ite|8850'
```

An ITE or PD-capable part bound to a PCI function is a candidate responder with
a name attached, which §4a's bare addresses do not give you. Record the `dmesg`
lines whole, including the ones that only mention the EC: the boot log is where
a handoff between two programs would announce itself, and its absence is the
datum that later makes a "no second die" reading stronger.

### 4d. Baseline: the EC window (a memory baseline, **not** a topology test)

Kept because a baseline is worth having, and demoted because it is not a
discriminator. **This reads the EC's own XDATA. It is not the PD image's
selector table**, and no outcome of it bears on §5.2 — see §1 for why the old
version of this step claimed otherwise and why the claim was wrong.

```console
$ for i in 1 2 3; do
      echo "== pass $i"
      sudo python3 ec/tools/ecmem.py read 0x0150 0x0151 0x0152 0x0153 0x0154 \
        0x0155 0x0156 0x0157 0x0158 0x0159 0x015a 0x015b 0x015c 0x015d 0x015e 0x015f
      sleep 1; done
```

Do the three passes before interpreting anything and record all three: a
pointer-shaped value that moves is a live variable and a pointer-shaped value
that does not is a constant, and "it moved once" is itself a datum. What the
result is *for* is the §4e cross-check below and any later pass that needs to
know what the EC's low XDATA looks like on this machine.

### 4e. Cross-check: what `uniwill-laptop` already binds

```console
$ lsmod | grep -i uniwill
$ dmesg | grep -i uniwill
$ find /sys/bus/platform/devices -name 'regmap' -path '*uniwill*' -exec ls {} \;
```

If the module is loaded, its regmap debugfs dump is the cheapest baseline for
§4d, and `ec/tools/ecmem.py`'s docstring records that its reads were already
cross-checked against exactly that dump for `0x7B9`, `0x44F`, `0x456`, `0x7A6`,
`0x7CC` and `0x07E2`. The same dump is worth reading for **which addresses the
EC driver claims** — a region the driver does not touch and nothing else names
is where a second program's window would show up, if it shows up in the EC's
address space at all.

### 4f. The Windows arm, if the Linux arm is inconclusive

The vendor's `ACPIDriver.sys` exposes the same window, and
`windows/tools/ecrw.py` is the committed instrument for it. Run §4d and §4c
again through it, with Control Center running and then stopped, the way
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` §3a separates the two.
**The `GCUService` comparison is the point of the Windows arm**: the vendor
stack talking to the same window and not moving the baseline bytes is a
statement about that window, and it is worth having before any later pass builds
on it.

## 5. What to read off

### 5.1 The bus read — the two outcomes of §4a

**Hit.** An address on a bus that responds, is stable across the reboot in
§4a, and is not one the EC driver claims (§4e). Record the bus, the address,
both scans, and the `dmesg` lines. **This is a candidate responder, not a
controller**: nothing here has named a part, and the identification work is
§4c's PCI/USB result plus a datasheet, which is §6's first bullet.

**Miss.** No such address, or only ones the EC already accounts for. **That is
a real result and the more interesting one**: the PD image is not behind a bus
this machine exposes, which pushes the topology question onto the SPI layout's
descriptor table (`pd-image.md` §5.1) and onto the shared-flash reading — one
die booting both images, or a handoff over a link no enumeration step can see.
Either way, §5.2's question gets narrower.

**Not a result either way.** The scan was refused, `i2cdetect` aborted, or a bus
could not be opened. Record that as a tooling outcome and do not read a
topology conclusion into it.

### 5.2 The Type-C read

Whether `/sys/class/typec/` exists, whether any port has a `partner`, and
whether the `ucsi` driver and `/dev/ucsi*` exist at all. As §4b says, an empty
result is a statement about the kernel's driver set and nothing more — and a
`partner` port is the one finding this whole document is built to catch.

### 5.3 The EC window baseline

What the EC's own `0x0150`-`0x015F` holds, and whether it moves. **It is not
the PD program's selector table** and it is not evidence about one; if it
happens to hold five big-endian values that look like code addresses, that is a
coincidence of the EC's own allocation, and §1 says why the earlier draft of
this file read it the other way.

## 6. What this cannot settle

- **Whether the PD program is the vendor's own firmware or a payload.** The
  provenance result in `pd-image.md` §5 shows one flash holding both images;
  an enumeration result narrows the topologies but does not say who wrote what.
- **The identity of any part.** Naming a controller needs a PCI/USB ID, a
  datasheet and a bus address that agrees with both — see §5.1. Nothing in
  §4a alone identifies one.
- **What `0xFFE0`-`0xFFE2` is.** `pd-image.md` §4.2 names the addresses and
  nothing else, and they are the PD program's XDATA, which this run cannot
  reach. Reading the EC's window at those numbers would be §4d's mistake again.
- **Anything about the string pool.** `pd-image.md` §3.1's null is a static
  one and no amount of enumeration resolves it; it needs DPTR watch, which is a
  debugger, not a bus scan.
- **Whether a Linux driver could talk to the PD controller.** A miss makes it
  harder, not settled.

## 7. Where the output goes

One text file under `evidence/pd-controller/` named for the date and the EC
firmware version, in the shape
[`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md)'s
captures are. Then a `docs/findings/pd-controller-enumeration.md` write-up, and
**one line added to `ec/annotations/pd-image.md` §5.2 and one to §6** — §6's
item 5 is this, and closing it is a deletion from a list of open questions
rather than an edit to the sentence that raised it.

## 8. What a result has to say

**On a hit:** that the enumeration found a responder at the named bus and
address on this machine on this date, that it is stable and is not one the EC
driver claims, with the raw capture in `evidence/`, and — stated as an
inference with its evidence, not as a conclusion — that a separate controller
is the more economical reading of it. A hit is *not* a licence to name
`0xFFE0`-`0xFFE2`, and it does not retire `lightbar-bat-flow.md` §2's
separate-program conclusion, which is about address spaces and is unaffected.

**On a miss:** that no bus this machine exposes answers for the PD image, with
the raw capture and the reason it is a miss rather than a tooling failure, and
that the topology question is now narrowed to the SPI image's descriptor table
and to "one die or a handoff over a link this run cannot see" — which is a
better-posed question than "one chip or two".

**On either, the sentence this run must not produce:** that a PD controller
was *identified*. Nothing here identifies a controller. A hit finds a
responder; a miss does not. Naming the part is what `dmesg`, a PCI/USB ID and a
datasheet are for, and if the run gets that far that is a separate write-up.

**And the sentence this run must not produce either:** that the two programs
share an XDATA address space. The old version of §8 said that, on the strength
of the old §4a read, and it was a claim about two memories that happen to share
a numbering. There is no reading in this document that bears on it — the PD
image's XDATA is its own 64 KiB program's allocation and is not the EC's
window.

## Cross-references

- [`../../ec/annotations/pd-image.md`](../../ec/annotations/pd-image.md) —
  the map, §2.1 for the selector table and its correction, §5.2 for the
  question this file asks.
- [`../../ec/annotations/lightbar-bat-flow.md`](../../ec/annotations/lightbar-bat-flow.md)
  §2 — why the region is a separate program, and the handoff question this
  narrows.
- [`../../ec/tools/ecmem.py`](../../ec/tools/ecmem.py) — the §4d instrument.
- [`../../ec/annotations/pd-base-strides.csv`](../../ec/annotations/pd-base-strides.csv)
  — the 448 bases §4a's neighbours are listed among, and the CSV that cannot
  say which space each names.
