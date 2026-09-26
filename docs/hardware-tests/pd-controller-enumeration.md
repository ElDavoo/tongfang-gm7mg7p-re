# Is the `ITE8850-PD` image on a controller of its own, and is it enumerable?

**Status: not run (issue #26).** The pipeline that wrote this file has no
machine to run it on — `CLAUDE.md` is explicit that the GitHub-hosted runners
cannot reach the hardware. **No bus scan, no `/sys/class/typec/` read, no UCSI
enumeration and no `/dev/mem` read of the EC window has happened on this
board.** Nothing in `ec/annotations/registers.yaml`, [`../findings.md`](../findings.md)
or [`../../ec/annotations/pd-image.md`](../../ec/annotations/pd-image.md)
records one, and there is no `evidence/` file covering USB-C or Type-C at all.
The instruments named below are committed; the readings are not. §8 says what a
result has to say, and **both** outcomes of §4.1 are reportable.

The question is the one `pd-image.md` §5.2 leaves open, in its own words: a
single 256 KiB `ecflash.nsh` write updates the EC firmware and the PD firmware
together, which is consistent with a shared SPI flash and therefore narrows the
"the EC hands off a payload" story — but it does not establish how many dies
are involved. One flash holding two images is compatible with one die running
both programs, with two dies behind one flash, and with a die that hands the
second image to a part over a link this evidence does not name. **This is a
hardware observation and nothing static can settle it.**

## 1. The question

`ec/firmware/GMxMGxx_11.800` is two programs in one file. The main EC is
Keil-banked and reaches its hardware through a memory-mapped window at
physical `0xFE410000` (`ec/tools/ecmem.py`, the same path the vendor's
`ACPIDriver.sys` ECRW method takes). The `ITE8850-PD` image at file
`0x20000` has its own 64 KiB space, its own XDATA allocation, and — from
`pd-image.md` §2.1 — a five-entry **interrupt-handler pointer table at its own
XDATA `0x0151`-`0x015F`**, read three bytes at a time by
`0x10F1 read3_code_to_r3r1` and jumped through by
`0x1229 load_dptr_then_indirect_jump`.

So the concrete, cheap form of the question is: **is that XDATA reachable from
the EC?** If it is, the two programs share a die or at least a bus, and §4.1
says what follows. If it is not, the PD image runs somewhere this repository
has no path to, and the rest of the run is about finding what that something
is. **Both are worth an hour**, and the second is the one that makes the
driver question answerable at all.

## 2. Before you start

- A machine: this is a TongFang GM7MG7P / Uniwill GM5MG7Y. Record
  `sudo dmidecode -s system-product-name` and the EC/BIOS version you are on
  into the capture header — a run on a different EC revision is a different
  question, and `ecflash.nsh` names `GMxMGxx_11.800`, so the EC firmware
  version matters more here than usual.
- Root and `CONFIG_DEVMEM` for §4.1; `ec/tools/ecmem.py` documents that on this
  machine the `INTC1036:00` window is listed in `/proc/iomem` and `/dev/mem`
  access to it works despite `IO_STRICT_DEVMEM`.
- Nothing installed, nothing flashed. This run is read-only throughout; §4.1
  writes nothing, and there is no write step anywhere in this document.
- Linux arm is the primary one (`ecmem.py`, `i2cdetect`, `lsusb`, `dmesg`).
  §4.4 is the Windows arm and needs the vendor ACPI driver installed, which is
  the `ACPIDriver.sys` path `ecmem.py`'s docstring names.

### Safety

There is no write step, so there is no write risk. The one caution is §4.1's
read: `ecmem.py read` opens `/dev/mem` read-only, and reading an address the
running EC is actively using is safe, but **capture a full baseline before and
after** (§4.2) so that a misread is visible as a change rather than assumed to
be a value. Do not run any `ecmem.py write` as part of this procedure, and do
not flash `GMxMGxxN109A08.ROM` or re-run `ecflash.nsh` to "check" anything —
`pd-image.md` §5 already settled that the committed image is byte-identical to
both, and a flash is not a read.

## 3. What to record

One text file, the usual shape: the commands, their full output, and the
timestamp of each. Commit it under `evidence/` when it is done, and add a line
to `ec/annotations/pd-image.md` §5.2 saying which §4 branch came out. Until
then, both the page and this file say the question is open, and that is the
sentence every downstream claim has to carry.

## 4. The run

### 4a. The XDATA test — is the PD image's memory reachable from the EC?

The one that decides the most, and it is a read. `pd-image.md` §2.1 says the
five interrupt handlers are selected by a 3-byte-stride table whose 16-bit
words sit at `0x0152`/`0x0153`, `0x0155`/`0x0156`, `0x0158`/`0x0159`,
`0x015B`/`0x015C` and `0x015E`/`0x015F` — so read the whole 16-byte block
plus its neighbours, and repeat it three times:

```console
$ for i in 1 2 3; do
      echo "== pass $i"
      sudo python3 ec/tools/ecmem.py read 0x0150 0x0151 0x0152 0x0153 0x0154 \
        0x0155 0x0156 0x0157 0x0158 0x0159 0x015a 0x015b 0x015c 0x015d 0x015e 0x015f
      sleep 1; done
```

**A pointer table is stable and a live EC variable is not**, and that is a
cheap way to tell the two readings apart before deciding what either means. Do
the three passes before interpreting anything, and record all three: one pass
is not enough to call a byte stable, and "it moved once" is itself a datum.

### 4b. The bus test — is a second device there?

```console
$ sudo i2cdetect -l
$ for d in $(sudo i2cdetect -l | sed 's/^i2c-\([0-9]*\).*/\1/'); do
      echo "== i2c-$d"; sudo i2cdetect -y -r "$d"; done
$ sudo lsusb -t
$ dmesg | grep -iE 'i2c|typec|ucsi|usb-pd|ite'
```

Record the full `i2c-*` list, not just a hit. A device at an address the EC
also uses is **not** a PD controller — the EC sits on the same bus in most
Uniwill designs, and an address collision is the expected result, not a
surprise. What would count is an address that responds, is stable across
reboots, and is *not* the EC's own.

### 4c. The USB-C side — what the kernel already thinks it knows

```console
$ ls -l /sys/class/typec/ 2>&1
$ for d in /sys/class/typec/usb-c*/; do echo "== $d"; cat "$d"/{vendor,model} 2>&1; done
$ ls /sys/bus/i2c/drivers/ucsi 2>&1
$ ls /dev/ucsi* 2>&1
```

Empty output and a missing `/sys/class/typec/` are both reportable and neither
is a negative finding about the hardware: it says the kernel exposes no
Type-C class device, which is a statement about the kernel's driver set on this
board. Record it as that.

### 4d. Cross-check: what `uniwill-laptop` already binds

```console
$ lsmod | grep -i uniwill
$ dmesg | grep -i uniwill
$ find /sys/bus/platform/devices -name 'regmap' -path '*uniwill*' -exec ls {} \;
```

If the module is loaded, its regmap debugfs dump is the cheapest baseline for
§4a and §4.2, and `ec/tools/ecmem.py`'s docstring records that its reads were
already cross-checked against exactly that dump for `0x7B9`, `0x44F`, `0x456`,
`0x7A6`, `0x7CC` and `0x07E2`.

### 4e. The Windows arm, if the Linux arm is inconclusive

The vendor's `ACPIDriver.sys` exposes the same window, and
`windows/tools/ecrw.py` is the committed instrument for it. Run §4a and §4c
again through it, with Control Center running and then stopped, the way
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` §3a separates the two.
**The `GCUService` comparison is the point of the Windows arm**: the vendor
stack talking to the same window and not moving `0x0151`-`0x015F` is evidence
that the PD image's XDATA is *not* that window.

## 5. What to read off

### 5.1 The primary read — the two outcomes of §4.1

**Hit.** `0x0152`/`0x0153`, `0x0155`/`0x0156`, `0x0158`/`0x0159`,
`0x015B`/`0x015C`, `0x015E`/`0x015F` hold five 16-bit big-endian values that
are **identical across all three reads of §4a** and each of which is the entry
point of a function in `ec/decompiled/pd/`:

```console
$ for f in ec/decompiled/pd/*.asm; do basename "$f" .asm; done \
    | sort -u > /tmp/pd-entries.txt
$ wc -l /tmp/pd-entries.txt
535
$ grep -x -F -e 0056 -e 0F0E /tmp/pd-entries.txt    # your five values
```

(The filter is on `.asm` because every function has both an `.asm` and a `.c`
in that directory; `ls | sed` alone leaves 1,070 lines and a name list twice
over. `ecmem.py` prints `0x0152=0x3c` — strip the `0x` from the value and it is
already the four-digit upper-case name `grep` wants.)

**A value being in the `0x0000`-`0xF7B7` range proves nothing on its own** — the
EC's common area is `0x0000`-`0x7FFF` too, and the two ranges overlap almost
entirely, so "the numbers look like PD addresses" is a shape argument and not a
measurement. The measurement is that all five are *committed function entries of
the PD program specifically*, and that they do not move. The name of each is in
`ec/annotations/ghidra-functions.csv` and its bytes are in the committed
listing, so a value that lands on one can be checked against real code: the
first instruction should be an interrupt routine, not a `MOV DPTR` or a jump
table.

**Then the two programs share an XDATA address space**, `pd-image.md` §5.2's
question is answered in the direction of one die, and the interrupt table
becomes live evidence.

**Miss.** The bytes are the EC's own, or they move between reads, or they do
not land on PD function entries. **Then the PD image is not reachable through
the EC's window**, and that is a real result and the more interesting one: it
puts the PD controller outside everything this repository has a path to, and it
makes §4b/§4c the load-bearing steps rather than the confirming ones.

**Not a result either way.** The read errors, `/dev/mem` is refused, or the
window is not where `ecmem.py` expects. Record that as a tooling outcome and do
not read a topology conclusion into it — `ecmem.py` works on this board as of
2026-09-17 on 7.2.6, and a different kernel may refuse `/dev/mem` for reasons
that have nothing to do with the PD controller.

### 5.2 The bus read

Which addresses respond, and which of them are already accounted for by the
EC. §4b's list is a census, not a hunt: record it whole, so a later pass can
tell a new device from a known one.

### 5.3 The USB-C read

Whether `/sys/class/typec/`, the `ucsi` driver and `/dev/ucsi*` exist at all.
As §4c says, an empty result is a statement about the kernel's driver set and
nothing more.

## 6. What this cannot settle

- **Whether the PD program is the vendor's own firmware or a payload.** The
  provenance result in `pd-image.md` §5 shows one flash holding both images;
  a hit in §4.1 narrows the topologies but does not say who wrote what.
- **What `0xFFE0`-`0xFFE2` is.** `pd-image.md` §4.2 names the addresses and
  nothing else. If §4.1 hits, reading that page live would be a *different*
  issue and a different procedure.
- **Anything about the string pool.** `pd-image.md` §3.1's null is a static
  one and no amount of enumeration resolves it; it needs DPTR watch, which is
  a debugger, not a bus scan.
- **Whether a Linux driver could talk to the PD controller.** A negative §4.1
  makes it harder, not settled.

## 7. Where the output goes

One text file under `evidence/pd-controller/` named for the date and the EC
firmware version, in the shape
[`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md)'s
captures are. Then a `docs/findings/pd-controller-enumeration.md` write-up, and
**one line added to `ec/annotations/pd-image.md` §5.2 and one to §6** — §6's
item 5 is this, and closing it is a deletion from a list of open questions
rather than an edit to the sentence that raised it.

## 8. What a result has to say

**On a hit:** that the PD image and the EC share an XDATA address space as
observed at `0x0151`-`0x015F` on this machine on this date, with the raw read
in `evidence/`, and — stated as an inference with its evidence, not as a
conclusion — that one die is the more economical reading. A hit is *not* a
licence to name `0xFFE0`-`0xFFE2`, and it does not retire `lightbar-bat-flow.md`
§2's separate-program conclusion, which is about address spaces and is
unaffected.

**On a miss:** that the PD image's XDATA is not the EC window on this machine,
with the raw read and the reason it is a miss rather than a tooling failure,
and that the topology question is now narrowed to "somewhere this repository
has no path to" — which is a better-posed question than "one chip or two".

**On either, the sentence this run must not produce:** that a PD controller
was *identified*. Nothing here identifies a controller. A hit identifies a
reachable address; a miss identifies an unreachable one. Naming the part is
what `dmesg`, the I2C address and a datasheet are for, and if the run gets
that far that is a separate write-up.

## Cross-references

- [`../../ec/annotations/pd-image.md`](../../ec/annotations/pd-image.md) —
  the map, §2.1 for the pointer table, §5.2 for the question this file asks.
- [`../../ec/annotations/lightbar-bat-flow.md`](../../ec/annotations/lightbar-bat-flow.md)
  §2 — why the region is a separate program, and the handoff question this
  narrows.
- [`../../ec/tools/ecmem.py`](../../ec/tools/ecmem.py) — the §4a instrument.
- [`../../ec/annotations/pd-base-strides.csv`](../../ec/annotations/pd-base-strides.csv)
  — the 448 XDATA bases, five of which §4a reads.
