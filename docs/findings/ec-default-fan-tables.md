# The pointer-pair table at `0x60F2` ends at `0x6162`, and `0x888D` is entered by a branch rather than a call

(2026-10-04. Static reading of `ec/firmware/GMxMGxx_11.800` and committed
files. No image is opened for writing, no register is read back, and no
laptop, EC or Windows machine is involved: every byte below comes out of the
committed image through `ec/tools/decode_fan_tables.py`, and every figure is
reproducible with the commands in §7.)

## The short answer

`manual-fan-ctrl-0751.md` §8 left the payload half of the fan-table mechanism
open with three sentences, and two of them are now closed.

- **The table has a measured end.** `0x60F2` holds **28** pointer pairs, not
  "at least twenty", and the 56 tables they name tile `0x5672`-`0x60F1`
  contiguously — ending immediately below the pointer table's own first byte.
  That second fact is what makes the count a measurement rather than a run
  that stopped (§2).
- **`0x888D` is not host-triggered only.** §6 recorded the trigger as "explicit
  host request" and said "No site in §2 reaches this code". Both understate it:
  the handler is the **fall-through target of a `jz` at `0x887E`**, inside the
  `0x8749` mode tick, gated on `0x06C2` reading zero. Nothing `lcall`s or
  `ljmp`s it, which is exactly why a call-graph search reports no caller (§4).
  So the handler is **reachable from a scheduler pass whenever `0x06C2` reads
  zero** — and the committed captures have it reading zero on the machine they
  came from, which is evidence and not a characterisation (§4).
- **So a driver does not have to ship a table.** On CPU — the fan the shipped
  tables actually carry — neither `M1T1` nor `M2T1` matches the EC's curve on
  any row, in any of the three committed projects (§5). Two things are outside
  that comparison rather than inside it: no committed project ships the Turbo
  table `M3T1`, so Turbo has nothing to compare against, and every project
  ships an **all-zero GPU row**, so there is no shipped GPU curve to compare at
  all. The missing half of the power profile is a mailbox round-trip, not a
  table to embed.

**What keeps that from being a small patch yet** is in §6, and it is not
decidable from the image: whether `0x8749` runs often enough for a round-trip
to land, and what `0x06C2` holds outside the three capture windows §4 names.
The prepared procedure for a human at the machine is
[`../hardware-tests/fan-table-defaults-0f5d.md`](../hardware-tests/fan-table-defaults-0f5d.md).

This is a **payload** half. The mechanism — the base seeded as `0x60F2` at
`0x8653`, the `0x888D` selector, the two `0x30`-byte copies — was decoded in
[`ec-fan-table-defaults.md`](ec-fan-table-defaults.md), which read the four
pairs the handler reaches and named this bullet's extent question as open. That
is the gap this closes, and nothing in `registers.yaml` moves as a result.

## 1. What this is not a second reading of

`ec-fan-table-defaults.md` decoded the four selected tables, compared them
against the tables the service *applies* (the committed `Fan/Table` MQTT
capture), and held the decode against the vendor's own writer. Its §6 left
three things open. Two are closed here and one is not:

| left open in `ec-fan-table-defaults.md` §6 | status |
| --- | --- |
| the pointer table's extent | **closed** — §2 |
| the trigger is still the mailbox | **corrected** — §4 |
| what the 28 pairs the handler cannot reach are for | **still open** — §6 |

Two things are deliberately *not* re-derived. The layout is not restated: it
is `fan_table_defaults.py`'s, reached through the module rather than copied,
because a second copy of a layout is the drift that tool's own test guards
against. And the four selected tables are not re-decoded here — but they are
checked against it, and that check earns its keep: the two tools reach those
four by **different routes** (one walks the handler's offsets, this one walks
the pointer table), and their committed CSVs agree on every row where they
overlap. A walk that had picked up a different pair than the handler does would
be internally consistent and would not show it, so the suite holds the two
against each other rather than only each against the image.

## 2. The extent, and why the count is a measurement

**The predicate, printed on every run** because a count without the rule that
produced it is not a measurement:

> a 4-byte entry at `0x60F2+4n` is a member when its second pointer is its
> first plus `0xC0` and both are below the `0x8000` bank window

The **relation** is what binds, not the magnitude. The weaker test — "both
pointers are below `0x8000`" — is the one that looks safe and is not: the
words that follow the table are also below `0x8000`, so a magnitude test keeps
accepting for a dozen entries past the real break.

The walk stops at `0x6162`, whose four bytes are `41 37 05 05`.

**The corroboration, which is the part that makes it a measurement.** The
accepted entries name 48-byte tables. Those spans are one contiguous run from
`0x5672` to `0x60F2` — that is, **the last payload byte is immediately below
the pointer table's first byte**. Two independent directions now agree about
where the region is: the pointer table stopped at `0x6162` walking forward, and
the payload ends at `0x60F2` walking backward from the tables it names. A
pattern that stopped and a boundary that two structures agree on are different
claims, and the write-up leans on the second.

The run length is the check that would fail if the agreement were a
coincidence: `0xA80` bytes is exactly 56 × `0x30`, so the contiguous run is
accounted for by its spans with nothing left over.

**The record length is the handler's, not this tool's.** `0x888D`'s two copy
loops are `cjne a,#0x30` (`ec/decompiled/bank0/888D.asm`), so 48 bytes is what
the EC's own code states. The two facts are different and are kept apart
throughout: *the handler copies 48 bytes* is measured from the copy loops, and
*the 48-byte records tile `0x5672`-`0x60F1`* is measured from the walk. Neither
implies the other.

## 3. The layout over every table, not over a chosen few

Checked per table over all 56 and reported as a tally, because a property that
holds across the whole set is a different claim from one that holds in the four
the earlier work looked at:

| property | |
| --- | --- |
| `UpT` rises and is `0xFF`-terminated | 56/56 |
| `DownT` rises | 56/56 |
| every duty within 0-100 % | 56/56 |
| the one unwritten offset, `0x10`, is `0x00` | 56/56 |

The duty convention is *not* re-checked for evenness here.
`fan_table_defaults.decode_blob()` halves each stored byte and refuses an odd
one, so evenness is established before a table reaches this check; asserting it
again would be a second copy of that rule rather than a second opinion on it.

**`DownT` is held to rising and nothing more.** It does not start at 0: the
first entry is 48 in every table measured. The issue's framing described the
second row as starting `0x00`, which conflated the gap byte at offset `0x10`
with the first `DownT` at `0x11`. The tool asserts the ramp and not the first
entry, and the suite holds that decision so a later reader does not "fix" it
back.

**What is not established is what the bytes are *to the EC*.** The field names
are the vendor's, from `fan_table_replay.ec_image()`. A blob that decodes
cleanly under that layout is consistent with it; it is not proof the EC reads
those bytes as degrees and per cent. The duty×2 convention is the service's.

## 4. How `0x888D` is entered, and why a call-graph search missed it

`manual-fan-ctrl-0751.md` §6 concluded the trigger was the mailbox on explicit
host request, and that "No site in §2 reaches this code". The first half is
about `0x0751` sites and the caller is not one. The handler is a **branch
target**:

```
0x887a  90 06 c2   mov  dptr,#0x06c2
0x887d  e0         movx a,@dptr
0x887e  60 0d      jz    0x888d          ; 0x06C2 == 0 -> the mailbox handler
0x8880  12 86 53   lcall 0x8653          ; the other arm: re-seed the base
0x8883  74 3c      mov   a,#0x3c
0x8885  12 bb 24   lcall 0xbb24
0x8888  74 3c      mov   a,#0x3c
0x888a  02 89 3e   ljmp  0x893e
```

`0x888D` is the fall-through target of a conditional branch **inside the
`0x8749` mode tick**, gated on `0x06C2`. The `0x8749` annotation row describes
the *other* arm, which is why the row and the branch disagree on the surface;
a scan of bank0 for `lcall`/`ljmp` naming `0x888D` finds **none**, and that is
the whole of why §6 read this as host-only.

Two independent corroborations in the tree, plus the independent decoder:

- `ec/annotations/bank-relative-branch-targets.csv` records `0x0887E jz →
  0x0888D` as the only branch naming the handler.
- `ec/decompiled/bank0/8749.asm` carries the same three bytes at the same
  address.
- `r2 -a 8051` decodes it identically (§7's convention, and §7's spot-check
  command). `decode_fan_tables.py` asserts the encoding against the **image**,
  not against either of those, so a firmware whose bytes moved is red here.

The `jz` is **two** bytes, so the target is `addr + 2 + disp` and not
`addr + 3 + disp`. Reading it as three lands `0x888E` and decodes as something
plausible — the same trap `manual-fan-ctrl-0751.md` §9 records landing
`0x943E` mid-instruction on another site.

**The chain closes to the polled scheduler**, which is what makes the branch
reachable from that pass rather than a dead end inside the mode tick:

```
0x0db6  12 0e 40   lcall 0x0e40        ; gated on 0x46 bit 0
0x0e40  02 15 52   ljmp  0x1552
0x1552            the far-call stub, immediate 0x8502
0x8502  12 87 49   lcall 0x8749
0x8749            ... ends in the `jz` above
```

(`charge-target-caller-chain.md` §1 for the dispatch block,
`task-call-table.csv` for the stub.) That is **a different slot of the same
dispatch block** from §4's `0xA7C8`, which is reached on cases `0x02`/`0x0C`
through `0x0E49` and stub `0x1564` rather than by this direct `lcall`. The two
therefore recur on the same scheduler, which is what puts §4's `AP_OEM`-gated
PL clear and this copy in the same neighbourhood — but they are not the same
case value, and **whether they fire on the same pass is not established.**

**What this does not settle, stated as narrowly as the evidence allows.**
`0x06C2` is `XDATA_06C2`, `present-untested`, with 15 direct reads and no
writer found outside the `bank1:0x8001`-`0x8189` sweep. A branch that exists
is not a branch that is taken.

The three committed `ec_watch` windows
(`evidence/ec-watch/2026-09-24-06c2-06db-*.csv`) do carry a reading of the
gate, and it is a positive one. Each has `0x06C2=0x00` on its `# baseline` line
and no `0x06c2` change row anywhere in it, so on the machine those windows came
from the byte held zero across the plain 300 s sweep, the 600 s
AC-out/Fn-power-mode-key/lid perturbation and the 150 s S3 suspend arm — that
last one's clock stopping in suspend, so it counts awake time only. That is
what `ec_timer_capture.py`'s docstring says the baseline line is *for*: "a byte
that never moved is still on record with the value it held, while the data rows
stay one per change", and it is the argument
[`xdata-06c2-06db-sweep.md`](../hardware-tests/xdata-06c2-06db-sweep.md) §4a
already applies to `0x0751` in the same capture family. So the gate reads zero
in ordinary operation on this machine, which is real evidence that the copy
fires on a scheduler pass — and it is **not** turned into "the gate is normally
open": three windows, on one machine with no vendor service running, are not a
characterisation of every mode or every machine, what the byte holds outside
them is still **not** established, and a live read of `0x06C2` across a mode
change is what would settle it. `0x06C2` stays `present-untested`; the
captures justify a stronger note, not a status change.

And §6's other negative survives the correction: the selector still comes from
`0x0F5F`, so what the branch changes is *when* a table is copied, not *which*
one. A mode change still does not by itself choose a curve.

## 5. Against the tables the vendor ships

`ec-fan-table-defaults.md` §5 compared against the committed MQTT capture —
the tables the service *applies* — and said the `UserFanTables\*.json` files
"live on the machine and are **not in this repository**". That is no longer
true: `vendor/control-center-3.9.18.0/UserFanTables/` is committed, three
project directories of them. So the comparison the issue actually asked for is
available now and is made here.

**Neither mode that any committed project ships matches, on any row, on CPU** —
that is `M1T1` and `M2T1`, each against all three project directories. The
other two exclusions are not comparisons either, and the sentence above is
bounded by them rather than sweeping over them:

- **Turbo `M3T1` has no counterpart.** No committed project ships it — they
  carry `M1T1`..`M1T3` and `M2T1`..`M2T3` and nothing else — so there is
  nothing to compare Turbo against, and the tool prints that as a note in the
  same shape as the GPU one below. This is a gap in the committed inputs, not
  a finding about Turbo's curve. `windows/vendor-ec-map.md` records `M3T1` as
  the Turbo table the service applies, so Turbo is a real mode and the
  exclusion is a real absence.
- **The GPU halves have no curve to compare against at all:** every committed
  project ships an all-zero GPU row, and the tool reports that per project
  rather than matching the EC against zeros.

On CPU, against the EC's own used levels:

| | `UpT` EC | `UpT` shipped | `Duty` EC | `Duty` shipped |
| --- | --- | --- | --- | --- |
| Gaming `M1T1` | 0 54 58 62 66 69 72 75 78 81 84 | 0 54 60 65 70 73 | 0 30 30 35 45 45 50 50 65 75 90 | 0 25 30 35 50 60 60 60 60 60 60 |
| Office `M2T1` | 0 54 58 62 66 69 72 75 78 | 0 54 60 | 0 30 30 35 45 45 50 50 50 | 0 25 30 30 30 30 30 30 30 |

**The shipped tables are also shorter**, which is the difference a reader
should notice first. Counting entries before the first `0xFF` threshold, the
EC's Gaming CPU row has eleven and Office nine, where every committed project
ships six and three. That is a property of the shipped files on every project
directory, and it is reported rather than smoothed over by indexing both sides
on the EC's levels — a trailing 255 on the shipped side reads as "the shipped
table stops here", not as a stale EC entry being compared.

**One thing this does not establish: which project this machine is.** All three
are compared and none matches, so the comparison does not depend on the answer.
Naming the project is a separate question, and the differences between the
three are the kind of thing a byte scan can show and cannot attribute:
`PH6TRX1`'s `M1T1` CPU duties run 5 points below `PH4TRX1`'s at levels 1-3 and
10 below at 4-5, with the same thresholds.

## 6. The band the decode does not explain

One property the layout predicts **does not hold** across the set, and it is
reported rather than dropped: `DownT[i]` is at or above `UpT[i+1]` in **13 of
the 56** tables, at the first offending level by:

```
0x56d2 CPU  first at level 2: DownT 63 >= UpT 62
0x5792 GPU  first at level 1: DownT 55 >= UpT 54
```

The layout says `DownT[i]` and `UpT[i+1]` are the two ends of one entry's
hysteresis band, so a table where the lower is not below the upper has a band
this reading does not explain. **The overshoot is never more than 1 °C** —
every failing comparison is either equal or one degree over.

**The failures arrive in whole entries, not in individual tables.** Grouped by
the pointer-pair entry they belong to, six entries break the band on **both**
the CPU and the GPU half, and one breaks on the GPU half alone:

```
grouped by pointer-pair entry:
  both halves: entries 1, 2, 5, 6, 13, 14
  GPU half alone: entries 27
```

That grouping is the shape the finding has, and it is a constraint on the three
readings rather than a detail of them: a failure that takes both halves of one
pair is a property of that pair's table, while a lone half failing is a
different thing again. Entries 1 and 2 are the two Office tables the handler
selects, and entries 5, 6, 13 and 14 are two CPU/GPU pairs that nothing found
here selects — so the pattern is not the handler's four tables and not confined
to them either. **Which** of the three readings it is, is not decided here: a
vendor writing a table by hand, a per-level override, and a subtly wrong layout
all fit these bytes. What it is not is a decoding failure: the rows are
internally consistent under the same checks the other tables pass.

Both Office tables break it, which is useful — they are byte-identical
(`ec-fan-table-defaults.md` §3), so the finding does not depend on `0x0782`
bit 2 and neither does the identity it sits beside.

## 7. Reproducing it

```console
$ python3 ec/tools/decode_fan_tables.py                   # the walk and the extent
$ python3 ec/tools/decode_fan_tables.py --csv | diff - ec/annotations/fan-table-curves.csv
$ python3 ec/tools/decode_fan_tables.py --check
$ python3 ec/tools/decode_fan_tables.py --self-test
$ python3 ec/tools/test_decode_fan_tables.py
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x887a; pd 9' /tmp/bank0.bin
```

The `--self-test` holds an oracle transcribed from the byte reads on the
committed image rather than from the tool's own output, and the suite holds the
write-up's figures against the image rather than against a transcription of
either. A firmware whose tables moved makes both red.

## 8. What this opens

- **What the 24 pairs the handler cannot reach are for.** The count is
  measured and the tables are decoded, and nothing found here selects them.
  Whether they are per-project or per-model variants is a byte scan's
  question — it can show the grouping and cannot name it.
- **`0x06C2` outside the three windows §4 names, and how often the tick runs.**
  The two open links in §4's answer, and a `needs-hardware-test` item for a
  human.
- **The 13 band failures in §6.** Whether they are hand-set tables, overrides,
  or a layout this reading has slightly wrong.
- **A fixed-width-record shape for `data_regions.py`,** so `0x5672`-`0x6161`
  can be listed as the data region it now measures itself to be. Its shape
  vocabulary has no member for a 48-byte record whose halves differ, and the
  tool's refusal of unknown shapes is a deliberate design property rather than
  an oversight to route around in a pull request about fan curves.
- **The driver decision this unblocks.** A platform profile that replays PLs
  but leaves the curve is a half-feature, and §2 and §5 say the missing half is
  a round-trip rather than bytes to embed — while §4 says it cannot be written
  from the image alone. That is the shape of the next issue, not this one.