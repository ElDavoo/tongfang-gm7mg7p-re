# `0x0726` bit 3 on AC insert with the machine off, and what `0x0765` holds across a power sequence

**Status: not run (issue #1108).** This procedure was written by the pipeline
for a human at the physical GM7MG7P. No laptop and no Windows machine is
reachable from the runner that wrote it, so nothing below has been observed:
no register has been written, no register has been read back, and no result is
recorded anywhere in this repository. The instrument
([`../../ec/tools/ecmem.py`](../../ec/tools/ecmem.py)) is committed; the
reading is not. §8 says what a result has to say, and `OEM_9
(AC_AUTO_BOOT_ENABLE)` and `SUPPORT_1` in
[`../../ec/annotations/registers.yaml`](../../ec/annotations/registers.yaml)
both stay `absent` until a human runs this and commits the capture — a
`status:` move is for a *behavioural observation*, and a prepared procedure is
not one.

**Two addresses, one page, and the pairing is the point.** `0x0726` and
`0x0765` are the pair [`pd-only-status-vocabulary.md`](../findings/pd-only-status-vocabulary.md)
§"Two questions this surfaces" question 1 names: the two entries carried at
`absent` on a zero-in-both-images count. Writing the procedure for one and
leaving the other as a one-line note is how the asymmetry the pair documents
persists, so the capability-byte question rides here as §5 rather than as a
second page. §5 is read-only and the reason it is read-only is not a
formality.

## 1. The question

`0x0726` is `OEM_9` in
[`../../ec/annotations/registers.yaml`](../../ec/annotations/registers.yaml).
Its own note names the missing observation exactly:

> Real verdict: unknown, needs a live behavioural test (does the laptop
> actually auto-boot on AC insert while off?)

That sentence is the whole reason this file exists. The entry sits at
`absent` on `static_refs: 0 / static_refs_main_ec: 0 / static_refs_pd_image: 0`,
and per that file's own header caveat a zero is "not found by this method" and
never "does not exist" — the same negative `docs/findings.md` §4c had to
retract for `0x07B9`, and the same grade `0x07B9`, `0x07C7` and `0x07C8` carry
as `unknown-not-absent` instead. Whether `absent` is the right word for a zero
in both images is the open question 1 above records as **open**, and
`check_status_vocabulary.py` deliberately does not encode it: the tool refuses
a status whose *warrant* is a count with no sites behind it, which is a
different question from whether `absent` is the right word. Nothing here
settles it, and §8 says so in the outcome that would bear on it hardest.

**The bit's name is written down; its behaviour is not.** Upstream names both
the byte and the bit —
[`upstream-excerpt.txt:109-110`](../../linux/patches/gm7mg7p-dmi-entry/upstream-excerpt.txt)
carries `#define EC_ADDR_OEM_9 0x0726` and `#define AC_AUTO_BOOT_ENABLE
BIT(3)` — and the excerpt's own section header is candid that the name lives
there: `[EC_ADDR_OEM_9 -- upstream's AC_AUTO_BOOT_ENABLE bit lives here]`. A
`:NNN` on that file is its own file line; the `NNN:` each quoted line carries
is its line in `uniwill-acpi.c`, and the two are not the same numbers. But
**no use site of that `#define` is in the excerpt**, and no behaviour
attaches to the name anywhere in this tree. That is a materially weaker
footing than a polarity, so this procedure is built to be polarity-agnostic:
it runs both polarities of bit 3 and reports which of them, if either,
discriminates. It never assumes that set means enabled, and it never tries to
settle the polarity statically. The ASL does not name the address either — the
`ECMG` field list at [`../../evidence/acpi/dsdt.dsl`](../../evidence/acpi/dsdt.dsl)
covers `0x07C4` at lines 52238-52242 and has nothing anywhere in `0x0720`-`0x072F`.

**Half the question is already answered, and it is not this machine's off
state.** [`../../evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv`](../../evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv)
is a per-address change count over `0x0000`-`0x07FF` across an AC plug-in on a
**running** Linux machine. `0x0726` is not among the 205 addresses it lists,
while other addresses in the same sweep did change — `0x071D`, `0x071E`,
`0x071F`, `0x0743`, `0x075B`, `0x075C`. So the byte did not change across an
AC insertion while the machine was up, which is already committed and is not
what §3 repeats. What that capture cannot speak to is the **off** window, and
it fixes the evidence shape as much as the answer: no host runs while the
machine is off, so there is no capture spanning the interesting moment and none
can be taken. The record is two fragments joined by the operator's wall clock,
and §7 names the file shape for exactly that.

**The first question is not the polarity, it is survival.** Whether XDATA
survives a full shutdown with AC removed is not knowable from the firmware
image, is not asserted anywhere in this tree in either direction, and is the
run's first observation rather than a precondition the run assumes. It is
also the one that can void the run: if the power sequence clears the byte, then
"set bit 3, shut down, insert AC" tested nothing. The control arm in §3 exists
to answer it, and §3 states what its answer can and cannot show.

## 2. Before you start

- **Root, and `CONFIG_DEVMEM=y`.** `ecmem.py` maps physical `0xFE410000`
  through `/dev/mem` itself, which is the same window the DSDT's `ECRR` uses
  (`docs/findings.md` §4e) and so the same bytes the Windows vendor driver's
  `ECRW` method reads and writes. On this machine the window is listed under
  `INTC1036:00` in `/proc/iomem` and `/dev/mem` access to it works despite
  `IO_STRICT_DEVMEM` (2026-09-17, kernel 7.2.6). Check the build before
  starting: `grep DEVMEM /boot/config-$(uname -r)`.
  ([the `0x0436` procedure](remain-capacity-0436.md) §2 is the source of this
  pair of lines.)
- **A working `ecmem.py read` on this machine, before anything is written.**
  `sudo python3 ec/tools/ecmem.py read 0x0726 0x0765` printing two values is
  the check. `ecmem.py`'s docstring records that its reads were cross-checked
  against the `uniwill-laptop` regmap debugfs dump for `0x43E`/`0x44F`/
  `0x456`/`0x7A6`/`0x7B9`/`0x7CC`/`0x7E2` before its first write — **neither
  address in this page is on that list**, so a first run's reads are the
  run's own cross-check and the values go in the log verbatim whatever they
  are. A read path that cannot produce a plausible byte here is a stopped run,
  not a negative.
- **A full shutdown, not a suspend.** Suspend keeps the EC powered, so it does
  not exercise the question at all and a suspend-based run must not be reported
  as one. `systemctl poweroff` or the power menu's *Shut Down*; the machine
  has to go to the state where the AC insert is the event being tested.
- **AC out before the shutdown, and out for the whole off window.** The event
  under test is AC arriving.
- **Someone at the machine for the whole sequence.** The observation that
  matters most is the wall-clock interval between the AC insert and the first
  visible sign of POST, and no software on the machine can time that — there is
  no host running. A phone or a watch is enough.
- **Battery health noted before starting.** A machine that will not hold
  charge, or whose pack is swelling enough to be cut out, makes an AC-insert
  observation about the charger rather than about `0x0726`. Record
  `upower -i /org/freedesktop/UPower/devices/battery_BAT0` (or the equivalent)
  in the log, and treat a pack in poor health as a reason to stop rather than
  as a caveat to write around.

## 3. The run, three arms

Three arms, one file, one clock, in this order. The control arm is first on
purpose: it is the only reading of what "unchanged" looks like across this
power sequence, and a treated arm whose read-back matches its write is
uninformative without it.

Every command below is a template. `0xNN` is the value the run reads or
computes, never a literal — the byte's other bits are not this test's to
change, and a hardcoded `0x08` or `0x00` would overwrite them.

**Arm 0 — control. The byte is not touched.**

```console
$ sudo python3 ec/tools/ecmem.py read 0x0726 0x0765
0x0726=0xNN
0x0765=0xNN
```

Record both lines verbatim; they are the run's starting pair and §6's restore
target. Then close the lid, shut down fully, wait, insert AC, and go through
§4's timing and boot recording without having written anything.

**Arms 1 and 2 — bit 3 forced each way.** For each arm, with the machine
running and on battery or AC as recorded:

```console
$ sudo python3 ec/tools/ecmem.py read 0x0726
0x0726=0xNN
$ sudo python3 ec/tools/ecmem.py write 0x0726=0xNN
0x0726: was 0xMM wrote 0xNN readback 0xNN
```

Compute the written value from the value just read, not from anything in this
file:

- **bit 3 set** — observed value `| 0x08`.
- **bit 3 clear** — observed value `& 0xF7`.

`ecmem.py` takes the value with `int(v, 0)`, so `0x08` is a valid argument; the
write form is the tool's own documented shape (`ecmem.py write 0x7b9=60`). The
tool prints `was`, `wrote` and `readback` and **all three go in the log** —
the `was` is what makes the arm auditable afterwards, and the read-back is
what §3's survival limit below is about.

Then: full shutdown, AC out, wait, insert AC, and record §4's two times.
**Do not press the power button for a fixed interval first** — note the moment
AC goes in, then note the first visible sign, then power on when you are ready
and say in the log at what point you pressed. A machine that boots on its own
in two seconds and a machine that boots because you pressed the button thirty
seconds later are different observations and the log has to be able to tell
them apart.

**At first OS contact, before anything writes, read the pair again:**

```console
$ sudo python3 ec/tools/ecmem.py read 0x0726 0x0765
0x0726=0xNN
0x0765=0xNN
```

This has to happen before any driver or vendor service has a chance to write
the byte. On Linux that means a shell with `uniwill-laptop` not yet loaded —
a live USB reaching a root prompt, or the module blacklisted for the run.
Getting there is a judgement about the machine, not a step this file can
prescribe; what it can say is that a read taken after the desktop has loaded
is a different and weaker observation, and the log should say which one was
taken.

**What this read can and cannot show.** A read-back at first OS contact is a
**lower bound** on survival, and only that. It cannot detect a value the power
sequence changed and changed back, and it cannot separate "the byte survived"
from "the power sequence rewrote it to the same value". Arm 0 is what tells
the two apart where they can be told apart at all: if arm 0's post-boot value
equals its pre-shutdown value and a treated arm's equals its own written value,
that is consistent with survival *and* with a rewrite-to-the-same-value, and
the log has to say which of those the run can rule out — which, for the
treated arms, it cannot. **The honest statement is that this run can detect a
byte the power sequence clears to a different value, and cannot certify one it
leaves alone.** Do not write "the byte survived" where the log supports "the
byte read back as written".

## 4. What counts as a boot

The test is binary and the test has never been defined, so define it here
rather than deciding after seeing which way it went.

**A boot is the machine reaching firmware POST with something visible**: a
POST screen, a beep, a logo. That is the threshold.

**Not a boot:** a rise in charge-circuit current, a fan twitch, an EC or
charging LED, the display backlight lighting with no POST behind it, or the
fans spinning briefly. Each of those is a plausible-looking event that this
file cannot grade, and a run that records one of them as a boot has recorded
an ambiguity rather than a result.

**Record two times against the operator's clock**, not the machine's, for
every arm: the moment AC is inserted, and the moment the first visible sign
appears. "It booted by itself" and "it eventually booted" are different
observations, and only the first is what an `AC_AUTO_BOOT` bit is supposed to
control — the second is equally consistent with a boot that took no notice of
the byte at all. If the operator pressed the power button before any sign
appeared, record the press as its own timestamp; it is the boundary between
the two readings.

## 5. `0x0765`: a read-only arm

`0x0765` is `SUPPORT_1`, also carried at `absent` on a zero-in-both-images
count, and also half of the pair
[`pd-only-status-vocabulary.md`](../findings/pd-only-status-vocabulary.md)
question 1 names. Its note reads: "driver reads this for capability bits
(SUPER_KEY_LOCK, LIGHTBAR, FAN_BOOST); not referenced by this firmware build".

**No committed line puts those three capability names at `0x0765`.** That is a
narrower claim than "no committed line at all", and it is the one that holds:
the names themselves are not missing from this tree, and every line behind them
lands on some other byte. The excerpt carries no `0x0765` line — its silence
is worth stating carefully, because the excerpt is a curated fragment set
rather than the whole of `uniwill-acpi.c`, so this is not a claim that upstream
does not define the address. What is checkable is narrower still, and it is
enough: the excerpt's only `FAN_BOOST` token is `TRIGGER_FAN_BOOST BIT(2)` at
`upstream-excerpt.txt:160`, which the excerpt's own section header puts under
`EC_ADDR_TRIGGER 0x0767`; `SUPER_KEY_LOCK_STATUS` and `LIGHTBAR_STATUS` are
`0x0768` bits at `upstream-excerpt.txt:169-170`; and outside the excerpt the
vendor stack has a fan boost of its own, the `FAN_BOOST_ON` and `FAN_BOOST_OFF`
cases at
`MyFanManager_RamFan1p5.cs:270,274`
([`../../windows/decompiled/v3.1.39.0/GCUService/MyControlCenter.MyFan/`](../../windows/decompiled/v3.1.39.0/GCUService/MyControlCenter.MyFan/MyFanManager_RamFan1p5.cs))
reaching a `SetFanMode` that writes bit 6 of `0x0751`, which
[`../../windows/vendor-ec-map.md:56,71`](../../windows/vendor-ec-map.md) traces
under both `SetFanMode` and `SetFanBoost`, and which its `_CML`, `_NV` and
`_Normal` platform variants do in the same shape. So `0x0767`, `0x0768` and
`0x0751` are three different bytes behind the three names, and none of them is
`0x0765`. The ASL's `ECMG` field list — the
`OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)` at
`dsdt.dsl:52193-52194`, and the only field list in the DSDT that names XDATA
addresses in that window, the other two EC regions being the `ECRR`/`ECRW`
methods, which take the offset as an argument rather than naming one, and the
`ECMP`/`ECXP` embedded-controller regions, which reach `0x7B` and bit 0
respectively — carries no `Offset` anywhere in `0x0720`-`0x072F` or in
`0x0760`-`0x076F`. The one literal `0x076x` in the DSDT is
`CreateBitField (BUF0, 0x0768, D4RW)` at `dsdt.dsl:4365`, and it is not an
XDATA address: `CreateBitField`'s second operand is a **bit offset into the
object named first**, and `BUF0` is `Name (BUF0, Buffer (0x021C) {…})` at
`dsdt.dsl:4156`, a local ASL buffer whose siblings (`0x0358` `C0RW`, `0x0428`
`C4RW`, `0x05C8` `CCRW`, `0x0698` `D0RW`) are buffer bit offsets too, so it
is evidence about neither range. `registers.yaml`'s `sources: [uniwill-laptop]`
tag is then the only thing in the tree that attaches the three names to
`0x0765`, and the committed scan reports `0x0765: 0 direct MOV DPTR site(s)
none` — which is the vocabulary of `static-refs-audit.md:60` and, in
`xdata_register_map.py:1238`, already graded as "not found by this method".

The driver-facing consequence, stated plainly: **on this board a Linux driver
cannot source `SUPER_KEY_LOCK`, `LIGHTBAR` or `FAN_BOOST` capability from
`0x0765`.** The argument is documentary, and it stands on its own: no
committed line places those three names at this byte, and the three lines that
do carry them land on `0x0767`, `0x0768` and `0x0751`. What backs the byte up
is weaker and is stated in its own terms — `static_refs_main_ec: 0,
static_refs_pd_image: 0` is a direct-`MOV DPTR` scan, so it means *no direct
`MOV DPTR` use site for `0x0765` was found in either image by the committed
scan*, not that the byte is unread. A use reached by a computed DPTR, a paged
write, or a route through code the scan does not disassemble would leave that
count at zero, which is precisely the `0x07B9` blind spot
[`docs/findings.md` §4c](../findings.md) was retracted for, and it is why the
row is not `absent` on the strength of the count. Either way a
driver taking those bits from `0x0765` would be reading a name, not a
capability.

**So this arm is read-only, and the reason is the point.** A host write into a
byte the stack may consult is an intervention whose effect on the driver is
unknown — it could make a driver take a path the byte never named, which is
the opposite of what a capability probe is for. "May consult" is as far as the
evidence goes in *either* direction, and that is the same blind spot: the
scan's zero rules out the direct `MOV DPTR` sites it can see and nothing
beyond them, which is a reason to leave the byte alone rather than a reason
to probe it harder. There is no write here, no restore, and no "flip a bit
and see". Read the raw value at the three states below, in this order, and
record each verbatim:

```console
$ sudo python3 ec/tools/ecmem.py read 0x0765
0x0765=0xNN
```

- **AC in, machine running** — the state most of the run lives in.
- **AC out, machine running** — the transition, read after the machine has
  been on battery long enough for the reading to be steady. Say how long.
- **First OS contact, before anything writes** — the `read 0x0726 0x0765` §3
  already takes, recorded here for `0x0765` with the state it was taken in.
  It is the only reading adjacent to the off window this run can produce, and
  it is *adjacent* rather than in it: a reading with the machine fully off is
  not available at all, because the instrument maps `/dev/mem` and needs a
  running OS, which is the same fact §1 gives for why no capture spans the
  moment. Do not substitute "read it immediately before shutting down" for
  this state — that is the second bullet under a different label, and the log
  has to be able to tell them apart.

A byte that reads the same in all three is *not found by this method, within
these windows* — and that wording is not a formality, it is the correction
`docs/findings.md` §4c exists to enforce. The driver-facing statement above
does not change either way, and neither does the converse: it rests on the
documentary half — no committed line puts the three names at this byte, and
the three lines that do carry them land on `0x0767`, `0x0768` and `0x0751` —
not on this run's readings, and not on the scan's zero, which says what that
scan looked for and not that nothing looks for it.

## 6. Restore

§3's first `read` is the restore target. Once the run's arms are done, and
**before the machine goes down for anything else**:

```console
$ sudo python3 ec/tools/ecmem.py write 0x0726=0xNN
0x0726: was 0xMM wrote 0xNN readback 0xNN
$ sudo python3 ec/tools/ecmem.py read 0x0726
0x0726=0xNN
```

`0xNN` is the first value §3 recorded, exactly as recorded. Log both lines.

**The restore may be a no-op, and if it is, that has to be written down as
observed rather than assumed.** If §3's post-boot read-back showed the power
sequence rewriting the byte, then "restored" restores a value the machine was
already not holding, and the confirmation read will agree with the write
without any of that being evidence the EC keeps it. A `readback` equal to
`wrote` here means the write landed; it is not evidence the EC acts on the
byte (`CLAUDE.md`: a register write being accepted is not evidence the EC
acts on it), and §8's second bullet is the same point written as a grading
rule.

**Safety.** This test writes one byte, `0x0726`, and reads `0x0765` without
writing it. That is the whole of the intervention: `0x0726` is `absent` on a
zero-in-both-images count and `0x0765` is untouched, so the committed scan
has shown no direct `MOV DPTR` writer for either — which, per §5, is what that
scan can and cannot see. The restore is the last line of defence, and it is
done with the machine up rather than left for later
— not because a host write to this window has ever been observed to damage
anything, but because there is no reason to carry a modified byte across
another shutdown.

## 7. Where the output goes

```
evidence/ec-watch/<date>-ac-autoboot-0726-0765.txt
```

`<date>` is that run's YYYY-MM-DD.

**A text file, not a CSV**, and the reason is the shape of the evidence rather
than a preference: no host runs while the machine is off, so there is nothing
to stream from and no timestamped sample series to put in a column. The record
is two fragments — everything before the shutdown and everything after the
first OS contact — joined by the operator's wall clock. A `ts,addr,old,new`
schema would imply a continuity the window does not have.

Use the `#`-commented header shape of
[`../../evidence/ec-watch/2026-09-23-ctgp-live.txt`](../../evidence/ec-watch/2026-09-23-ctgp-live.txt)
and of `2026-09-23-0751-isolation.txt`: a run identity block of `#` lines, then
the arms as labelled sections beneath it. The header fields this run needs:

- date, and the machine and EC firmware build (`GMxMGxx_11.800`) it was taken
  on;
- kernel, and the path `ecmem.py` was invoked through;
- battery health, from §2;
- per arm: the starting value of `0x0726` as read, the value written, the
  `was`/`wrote`/`readback` line, and the post-boot pair;
- per arm: AC-insert time, first-visible-sign time, any power-button press,
  and the boot verdict as §4 defines it;
- the three `0x0765` readings from §5, with the state each was taken in.

Then add the file to [`../../evidence/README.md`](../../evidence/README.md),
which is the index every findings claim cites through, and say in that entry
what the run was: which arms, AC state throughout, and the verdict per arm.
A run that produced an ambiguous result says so in the index entry rather than
leaving it to be discovered in the file.

The follow-on edits a run is for, named here so a later pass does not have to
re-derive them, and to be made **only after a capture exists**:

- `OEM_9 (AC_AUTO_BOOT_ENABLE)` and `SUPPORT_1` in
  [`../../ec/annotations/registers.yaml`](../../ec/annotations/registers.yaml) —
  what the run observed, in the note. **A `status:` move is not this run's to
  make on its own**; §8 says what each outcome does and does not license.
- [`../findings/pd-only-status-vocabulary.md`](../findings/pd-only-status-vocabulary.md)
  question 1 — a negative run result is an input to that open decision, not
  the decision.

## 8. What a result has to say

One bullet per outcome, each a scoped positive followed by an explicit
negation. A bullet that stops at the positive is how a row carried at `absent`
turns into confident-sounding prose.

- **No arm booted, control included.** A real negative, and the one this
  procedure exists to make possible. What it establishes is scoped: *with bit 3
  at each polarity, and with the byte untouched as a control, the machine did
  not power on by itself when AC was inserted, within these windows and on this
  machine.* It moves `0x0726` **toward** the `unknown-not-absent` argument —
  the same shape as `0x07B9`, `0x07C7` and `0x07C8`, and the same calibration
  rule `docs/findings.md` §4c was retracted for. It moves it **not** toward
  `absent`, and it does not settle the grade at all: whether `absent` is the
  right word for a zero in both images is the open question
  [`pd-only-status-vocabulary.md`](../findings/pd-only-status-vocabulary.md)
  records as open and `check_status_vocabulary.py` deliberately does not
  encode, and a run is not the only evidence that could bear on it. The entry
  keeps its caveat, which is the right one: "0 direct refs" is "not found by
  this method", per the `0x07B9` retraction.
- **The read-back matched and nothing booted.** This is the case that reads
  like a success, and it is worth separating out loud for that reason. It
  settles **nothing** about whether the EC acts on the byte — `CLAUDE.md`, "a
  register write being accepted (readback matches) is not evidence the EC acts
  on it" — and the correct write-up is a negative with the read-back recorded,
  not a confirmation. The `ctgp-dben` procedure states the same discipline at
  its own §7, for the same reason.
- **Both polarities booted.** Report it as *the bit is not the discriminator*,
  and check the control arm before writing that at all: if the control booted
  too, the byte was never the variable and the honest statement is that this
  machine auto-boots on AC insert with `0x0726` at either value. It is **not**
  a statement that the byte is inert, and **not** a statement that bit 3 has no
  effect — a byte can gate something that does not show up as an
  auto-power-on.
- **One arm booted and the other did not.** Report the polarity, as an
  observation: *the arm with bit 3 <value> is the one this machine booted on.* If
  one arm was run once, say it ran once. The polarity then becomes an
  observation rather than an inference from a `#define` — which is the only
  thing in this repository that can make it one, and it is still one machine
  and one firmware build. Repeat the pair before writing it down as settled.
- **The byte did not survive the power sequence**, in either polarity and
  visibly in the control arm. Then **the arms did not test what they were
  written to test and the run is void, not negative.** Nothing about the
  polarity follows from a run whose value was overwritten before the event
  under test, and §3's control arm exists precisely so this is recognisable
  rather than mistaken for a result. What the run has established is a fact
  about XDATA survival on this board, which is worth recording in its own
  right.
- **`0x0765` read the same at all three of §5's states** — AC in running, AC
  out running, and first OS contact before anything writes. That is *not found
  by this method, within these windows*, and it is not a verdict on a fourth
  state: no host runs while the machine is off, so no run of this procedure
  produces a reading from inside the off window and §5 does not ask for one.
  The driver-facing statement in §5 is unchanged by it, because that statement
  rests on the documentary half — no committed line puts the three capability
  names at `0x0765`, and the three that do carry them land elsewhere — rather
  than on this run's readings. A single differing reading is worth a second run
  before anything is written about it, and it is a statement about the byte
  across those three states and not about what the byte means.

---

**Running this is a human step on the physical GM7MG7P. This repository
contains no result from it.**
