# Which of the 98 ECMG names the ASL reaches for, and what the two `0x71` arms are (issue #1159)

`ec/annotations/dsdt-ecmg-fields.csv` had one axis — how many direct
`MOV DPTR` sites each of the 98 ECMG elements has — and said nothing about
whether the ASL that declares a name ever *uses* it. That is the other half of
what a name in a field list means, and it is cheap to add to a tool already
parsing the same 130 lines: `ec/tools/dsdt_ec_fields.py` now carries two more
columns, `asl_refs` and `asl_sites`, and `--self-test` re-derives both from
the committed `dsdt.dsl`. `--check` still proves the table byte for byte.

The short version: **35 of the 98 names are referenced by the ASL outside their
own field list, over 52 (name, line) sites.** Three of the claims in the issue
about *which* names those are do not survive the measurement, and the third is
the most useful thing here, so each correction is kept beside what it
corrects.

Nothing below was read on hardware. No EC was opened, no register read back,
no `_Qxx` fired. Every number is a static count over two committed files, and
a zero is always "not found by this method" and never "absent".

## What a reference is, so the count is the same count next time

- A **reference** is an occurrence of a field name in ASL **outside its own
  declaring list's line span**. Comments are stripped first, so iasl's own
  `\_SB_.PCI0.LPCB.EC0_.CTWA` alias comments are never counted as code.
- **Two forms count.** The qualified form, a path written
  `^^PCI0.LPCB.EC0.<name>`, counts anywhere in the file. The bare form, a
  whole-word occurrence, counts only inside the scope brace-enclosing the
  list, because ASL resolves a bare name to the nearest enclosing declaration
  and that is the same reference written shorter.
- A name preceded by any `.` is **not** bare. `^^^^UBTC.MGI0` at
  `dsdt.dsl:52947` writes an `External (_SB_.UBTC.MGI0, IntObj)`
  (`dsdt.dsl:264`, an `IntObj` declared just after its `External (_SB_.UBTC,
  DeviceObj)` parent at `:259`) that merely shares a spelling with ECMG's
  `MGI0`; a bare scan without that guard puts twenty phantom references on
  one byte.
- A reference is attributed to the region that **declares the name**, not to
  the path it was reached through. That is the correction below, and it is
  load-bearing: three of the four regions `Device (EC0)` declares share one
  path prefix.
- A reference has **no direction**. The count is an occurrence: a name the ASL
  loads, a name it stores and a name it tests are one reference each, and
  neither column says which. **Eight of the 35 are written by the ASL and read
  nowhere** — `APL1` (`dsdt.dsl:50639`), `APL2` (`:50643`), `APL4` (`:50648`),
  `APTN` (`:50652`), `APTC` (`:50653`), `DBD1` (`:50687`), `DBD2` (`:50688`)
  and `CGCT` (`:50732`), every one of them by a `T1WR` arm tabulated further
  down. That is not a correction to the count; it is what the count is, and
  `ec/annotations/registers.yaml:471` already records the direction for one of
  them — "T1WR stores `Arg1` * 8 into it" — under a
  `status: unknown-not-absent-DO-NOT-WRITE-BLIND` (`:477`). The direction
  lives on the line, and no column here measures it.
- `asl_refs` is the occurrence count and `asl_sites` the set of `dsdt.dsl`
  lines, so two references on one line are not lost. `PDIN` is the case:
  18 occurrences over 8 lines, three of them inside one `||` chain at
  `dsdt.dsl:50774`.
- A zero reads `not-referenced-by-this-method`, for the same reason
  `not-found-by-this-method` exists. It is not a `registers.yaml` `status:`
  value and cannot be lifted into one.

The per-name table is the committed CSV's two new columns, not a copy of them
here. `python3 ec/tools/dsdt_ec_fields.py ec/firmware/GMxMGxx_11.800 --csv
--check` proves it; this page states claims about it and would rather be
wrong about a sentence than carry a second table that drifts.

## `Device (EC0)` declares four regions, and the issue's list spans three of them

**What the issue measured.** Counting `^^PCI0.LPCB.EC0.<name>` outside the
field list at `dsdt.dsl:52194`-`:52328` "gives 90 uses over 40 distinct
names." That reproduces exactly: 90 occurrences over 40 names, 80
(name, line) sites.

**What it is.** The prefix `^^PCI0.LPCB.EC0.` does not reach one region.
`Device (EC0)` (`dsdt.dsl:52161`, braces `:52162`-`:52985`) declares **four
operation regions over five `Field` lists**, and the path reaches three of the
four — `ECMG`, `ECMP` and `ECXP`. The fourth is the `IO` port region at
`:52163`, which the path does not reach, and its two lists are the `:52164` and
`:52175` rows of the table below:

| list | line | names | note |
|---|---|---|---|
| `Field (IO, …)` | :52164, :52175 | 10 | status/command port registers, not XDATA |
| `Field (ECMG, …)` | :52194 | 98 | the committed table's subject |
| `Field (ECMP, …)` | :52331 | 1 | `DEVS` at 0x7B, no reference |
| `Field (ECXP, …)` | :52338 | 94 | `EmbeddedControl` `Zero, 0xFF`, a different address space |

The two EC regions' names **do not overlap** — 98 and 94, disjoint — so a
path-keyed count merges two disjoint lists into one. Of the issue's 40 names:
**15 are ECMG, 24 are ECXP, and 1 is not a field at all.**

**The one that is not a field.** `THOT` is `Name (THOT, Zero)` at
`dsdt.dsl:52190`, a named constant in the same scope as the ECMG list. It
carries no `OperationRegion` and no `Field`, so there is no address to place
it at and it cannot be a reference *to* anything. The tool reports it, and the
seven other names it cannot place, as unplaceable rather than dropping them:
the four constants beside it (`CPSZ`/`OSEC`/`VGTT`/`NVCB` at
`:52188`-`:52192`) and `_HID` (`:52472`), `_CRS` (`:52473`) and `OSDT`
(`:52897`) — the eight `--self-test` prints. Two of iasl's own alias comments
(`dsdt.dsl:52543`, `:52983`) resolve to `OSEC`, which is the fourth route
agreeing with that classification.

*(Superseded: "14 are ECMG fields, 24 are ECXP fields, and `THOT` is not a
field at all" — the printed list is 40 names, not 39, and 15 of them are
ECMG's.)*

## The split, for all 98

Grouped by what each group *is*, because the grouping is the finding and a
per-name list would be a second copy of the CSV.

**Referenced, and the ASL is the only evidence for the byte (19 names).** The
one method below reaches for twenty `0x0Exx` names — `CCI0`–`CCI3` and
`MGI0`–`MGIF`, 0x0EA4-0x0EA7 and 0x0EB0-0x0EBF, all of them loads, since
`^^^^UBTC.MGI0 = MGI0` reads ECMG's byte and writes another object — and this
group is the nineteen of the twenty with **no** `MOV DPTR` site anywhere in
the EC image. The twentieth is `MGI8` (0x0EB8), which has one and sits in the
next group, so the two together are the 35.

**Referenced, and the EC image names them too (16 names).** `PDIN` (18
occurrences over 8 lines), `CTWA` (4 over 4), `GFID` (4), `MGI8` (1), `DBEN`
(2), `WHMS` (2), `CPUA` (2), `DBAP` (2), `APL1`/`APL2`/`APL4`/`APTC`/`APTN`
(1 each), `DBD1`/`DBD2`/`CGCT` (1 each). The last eight are the direction-free
column's own edge: each is written by a `T1WR` arm and read nowhere. `CTWA` is
the one name of the 35 the ASL both writes and reads, and it does so inside
the one live arm: the `0x1171` arm writes it at `dsdt.dsl:50662` and reads it
back two lines later at `:50663`, with `_Q83` (`:52787`) reading it too. The
fourth site, `:50670`, is in the `0x71` arm, which is unreachable for the
reason below — so the "both writes and reads" claim does not rest on it.

**Declared only, and the EC image names them (24 names).** The mirror image
of the row above, and the sharper half: `CPTM`, `VGAT`, `FFAN`, `SDAN`,
`GNEN`, `ECDC`, `CTVA`, `DBCT`, `MXDB`, `GC6S`, `AP01`, `AP02`, `AP10`,
`DBST`, `WMS0`, `DBSP`, and `CTL0`–`CTL7`. Every one of them has at least one
direct `MOV DPTR` site — 1 to 142 across the group — so this half raises no
addressing question of its own: the blind-spot reading belongs to the group
above, whose bytes have no direct site to find. What the pair shows is two
independent facts, a byte the firmware names and a name the ASL does not reach
for, and "unused" is a third claim that neither column reports — which is why
the two columns are kept apart.

**Declared only, and no evidence either way (39 names).** The rest:
`MIDB`, the `PMAX`/`PBSS`/`PSRC`/`DTTF`/`VBNL`/`RBHF`/`CMPP` run, `CPUT`,
`PCHT`, the `SN1T`–`SN5T` and `F1SH`/`F1SL`/`F1DC`/`F1CM`/`F2DC`/`F2CM` and
`UVER`/`RESV` groups, and `MGO0`–`MGOF`.

One of the 98 is declared in an earlier list before ECMG declares it, so its
row reports the earlier declaration's references rather than its own: `PBSS` is
in `Field (PMIO, …)` at `dsdt.dsl:7950`, and it is referenced nowhere under
either declaration, so nothing above moves for it. The same happens to one of
ECXP's 94 — `WUSB` in `Field (OGNV, …)` at `:1493` — and there it does move a
number, because first declaration wins, as it does in `parse_regions()`, and
`OGNV`'s scope runs to `dsdt.dsl:53348`. `WUSB` is referenced **twice** under
that earlier declaration: at `:8163`, which is a real bare read
(`If ((WUSB == One))`), and at `:52417`, which is not a reference at all but
ECXP's own element line redeclaring the name. A count keyed on the first
declaration's scope and not on the list the name is written in cannot tell
those apart, so the tool now excludes every `Field` list that declares a name
rather than only the first one, and `WUSB` comes back as the one reference at
`:8163`. The ECXP figures in follow-up 1 are the ones without the artifact:
**35 names over 66 occurrences on 65 lines, 14 of those lines inside
`Device (EC0)`**. `--self-test` names both cases, and pins the ECXP total.

### The sixteen

`ec/annotations/dsdt-ecmg-field-sweep.md` §6 records sixteen names added to
`registers.yaml`: `PDIN` (0x074C), `CTWA` (0x0788), `GC6S` (0x07A4), `WHMS`
(0x07C5), `AP01`/`AP02`/`AP10` (0x07C0-0x07C2), `CTL0`–`CTL7`
(0x0EA8-0x0EAF) and `MGI8` (0x0EB8). Measured against the ASL: **four are
referenced and twelve are not.** `PDIN`, `CTWA`, `WHMS` and `MGI8` are
referenced — all four are read, and `CTWA` is also written, by the `0x1171`
arm at `dsdt.dsl:50662` — while `GC6S`, the three `AP0*` and the eight `CTL*`
are not.

*(Superseded: "3 of the 16 entries this merge added are in the live set —
`PDIN` (`0x074C`), `CTWA` (`0x0788`) and `WHMS` (`0x07C5`) — and 13 are
declared only: `GC6S`, `AP01`/`AP02`/`AP10`, `CTL0`-`CTL7` and `MGI8`." Three
of the four are right. `MGI8` is read, at `dsdt.dsl:52955`; so the split is
4 and 12, not 3 and 13, and `MGI8` moves from the second list to the first.)*

## The bare form a qualified-only scan misses

`Method (UCEV, 0, Serialized)` at `dsdt.dsl:52943`-`:52970` writes sixteen
`External (_SB_.UBTC.MGI*, IntObj)` objects from ECMG's `MGI0`–`MGIF` and
four more from `CCI0`–`CCI3` — twenty names, all by **bare** name, one per
line:

```
52947:                ^^^^UBTC.MGI0 = MGI0 /* \_SB_.PCI0.LPCB.EC0_.MGI0 */
…
52963:                ^^^^UBTC.CCI0 = CCI0 /* \_SB_.PCI0.LPCB.EC0_.CCI0 */
```

A `^^PCI0.LPCB.EC0.`-only scan calls all twenty declared-only. They are the
reason the reference count has two forms, and the reason the issue's
"declared only" column is wrong for a quarter of the page.

The same shape appears in ten `_Qxx` EC-query methods, which are the
firmware's own second path to these bytes: `_Q83` reads `CTWA` (:52787),
`_Q84` reads `DBEN`/`CPUA`/`DBAP` (:52796`, `:52801`, `:52802`), `_Q85` reads
`WHMS` (:52817), and `_Q70`, `_Q71`, `_Q72`, `_Q06`, `_Q0C`, `_Q53` and `_Q6E`
read ECXP names. Every one of those is a bare reference too.

## The `0x0Exx` page: 20 of 59 referenced, and that is a lead, not an answer

*(Superseded: "**The 59 `0x0Exx` names are all declared-only**, which is the
leading for the separate `0x0Exx` question rather than an answer to it." Not
all: **20 of the 59 are read**, `CCI0`–`CCI3` and `MGI0`–`MGIF`, all by that
one `UCEV` method. The rest of the sentence stands — it is a leading, not an
answer — and the lead is now a sharper one.)*

The sweep's §5 already asks what it means that 50 of the page's 59 names have
no direct `MOV DPTR` site, and names the indirect-addressing blind spot of
[../findings.md](../findings.md) §4c as one of the two things it could be.
The ASL reference makes the question more specific rather than answering it:

- **19 of the 20 bytes the ASL reaches for there, the EC image never names.**
  Only `MGI8` (0x0EB8) has a site, and that is the one the sweep put in the
  tree **because of** `bank0:0xF221` — one direct site, the read-modify-write
  in that routine, which is a statement about the site a scan for `MOV DPTR`
  byte patterns found and not about every path that could reach the byte.
- **8 of the 9 bytes the EC image does name there, the ASL never reaches
  for** — `CTL0`–`CTL7` (0x0EA8-0x0EAF). The ASL reads 0x0EA4-0x0EBF as one
  run bar those eight, and those eight are a hole in the middle of it.
- `CCI0`–`CCI3` (0x0EA4-0x0EA7) sit **immediately below** the `CTL0`–`CTL7`
  run that `bank0:0xF335` copies byte by byte into 0x0F61-0x0F68. The ASL
  takes the range in two pieces, 0x0EA4-0x0EA7 and 0x0EB0-0x0EBF, with the
  eight bytes the EC copies filling the gap between them; the EC code that has
  been decoded treats only those eight as one block.

Three things line up on 0x0EA4-0x0EBF being a controller block the EC reaches
by computed addressing, and none of them decodes it. Deciding what writes
`0x0EA8` and what reads `0x0F61`-`0x0F68` is the question the sweep's §5
already opened, and this is a lead for it.

## `T1WR`'s twenty arms

`Method (T1WR, 3, NotSerialized)` at `dsdt.dsl:50635` dispatches on **20
`Arg0 ==` comparisons over 19 distinct values** — `0x71` appears twice. That
is the figure `ec/annotations/dsdt-ecmg-field-sweep.md:131`-`:134` commits to
and it is re-derived by `--self-test`, along with the 30 distinct values the
file carries across **the 14 methods that write their dispatch as
`ElseIf ((Arg0 == 0x…))`**. `T1WR` is 19 of them; `UHID`, `RPTS`, `TRAP`,
`UARB`, `RWAK`, `GETA`/`GETB`/`GETC`, `SETA`/`SETB`/`SETC`, `_WED` and `_REG`
carry the other 11.

**That 30 is a count of one spelling, not of the file.** Three further methods
dispatch on `Arg0` as `Switch (Arg0)` / `Case (0x…)` rather than as an
`ElseIf` chain — `D3CS` (`dsdt.dsl:17262`), `RSON` (`:17342`) and `RSOF`
(`:17420`), each carrying the same ten values `0x04`-`0x16` — and
`--self-test` pins that population rather than leaving it to be re-derived by
eye. Three of those ten (`0x04`, `0x06`, `0x08`) are already among the 30, so
seven are further and the two spellings together come to **37 distinct values
over 17 methods**. Two more methods dispatch on `Arg0` and are excluded from
all of it deliberately: `CLKC` (`:6219`) and `CLKF` (`:6237`) switch on the
symbolic `Zero`/`One`, which the `0x…`-literal pattern does not match because
a command-protocol argument value is what is being counted here and a
`Zero`/`One` index is not one. `--self-test` names them as excluded rather
than leaving them uncounted and unmentioned.

The table below is `ec/tools/dsdt_ec_fields.py`'s `T1WR_ARMS` constant, and
`--self-test` rebuilds every cell of it from the committed `.dsl` and
`registers.yaml` — value, header line, the field each arm reaches, and that
field's entry and status. A row that drifts is red, so this table cannot
survive a change to either file.

| Arg0 | line | field(s) | `registers.yaml` entry | `status:` |
|---|---|---|---|---|
| `0x81` | :50637 | `APL1` | `CPU_PL1 / PL2 / PL4 (APL1/APL2/APL4)` | `present-untested` |
| `0x82` | :50641 | `APL2` | `CPU_PL1 / PL2 / PL4 (APL1/APL2/APL4)` | `present-untested` |
| `0x83` | :50645 | — | — | — |
| `0x84` | :50646 | `APL4` | `CPU_PL1 / PL2 / PL4 (APL1/APL2/APL4)` | `present-untested` |
| `0x85` | :50650 | `APTN`, `APTC` | `CPU_TCC_OFFSET (APTC/APTN)` | `present-untested` |
| `0x86` | :50655 | — | — | — |
| `0x87` | :50656 | — | — | — |
| `0x71` | :50657 | — | — | — |
| `0x1171` | :50658 | `CTWA` | `CTWA` | `present-untested` |
| `0x71` | :50667 | `CTWA` | `CTWA` | `present-untested` |
| `0x1172` | :50675 | — | — | — |
| `0x1173` | :50680 | `DBD1`, `DBD2` | `DBD1 (DSDT name; ECSpec calls the same byte BATTERY_CHARGE_LIMIT_DOWN)`, `DBD2 (DSDT name; no vendor constant, no committed Windows writer)` | `unknown-not-absent-DO-NOT-WRITE-BLIND` |
| `0x2273` | :50693 | — | — | — |
| `0x73` | :50700 | `DBEN`, `CPUA`, `DBAP` | `GPU_DYNAMIC_BOOST_STATUS (DSDT DBEN bit 3, DBST bit 5)`, `CPUA (DSDT)`, `DBAP (DSDT)` | `present-untested` |
| `0x74` | :50719 | — | — | — |
| `0x1175` | :50720 | — | — | — |
| `0x75` | :50725 | `WHMS` | `WHMS` | `present-untested` |
| `0x1176` | :50730 | `CGCT` | `CGCT (DSDT)` | `unknown-not-absent` |
| `0x76` | :50735 | — | — | — |
| `0x61` | :50739 | — | — | — |

Ten arms reach no EC field, and that is the answer for those arms rather than
a gap in the scan. Four of them — `0x1172`, `0x2273`, `0x1175`, `0x76` — reach
a `Notify` and nothing under `Device (EC0)`, and three of the four write an
`\_SB.NPCF` field on the way: `0x1172` `DBAC` (`:50677`), `0x2273` `ATPP`
(`:50697`) and `0x1175` `WMEN` (`:50722`). The fourth, `0x76`, writes none of
either — its whole body is `Notify (^^PCI0.PEG0.PEGP, 0xC0)` (`:50737`), the
same object the `0x1176` arm notifies (`:50733`). Five are the empty
arms iasl writes on one line as `ElseIf ((Arg0 == 0x86)){}`: `0x83`, `0x86`,
`0x87`, `0x74`, and the first `0x71`. The `0x61` arm calls `SGOV`.

## The two `0x71` arms

**What the issue said.** "There are two consecutive `ElseIf ((Arg0 == 0x71))`
arms at `dsdt.dsl:50667` and `:50669`, the second unreachable. The first is
the `0x1171` branch's neighbour and both read `CTWA`."

**What is there.** The arms are at **`dsdt.dsl:50657` and `:50667`** — ten
lines apart, not consecutive, and `:50669` is not an arm at all: it is
`Local0 = Zero`, the first statement of the `:50667` arm's body, which opens at
`:50668`. The `0x1171` body's own span is `:50659`-`:50666`, and it does not
reach `:50669`. The one at `:50657` is the empty `ElseIf ((Arg0 == 0x71)){}`
and it is the `0x1171` arm's immediate neighbour at `:50658`. The one at
`:50667` reads `CTWA`, multiplies it by 8, mirrors it to `NPCF.UOCT` and
`Notify`s `NPCF` 0xC0.

So "both read `CTWA`" is wrong — the first reads nothing — and the
reachability conclusion is right, for a reason worth stating: a caller
passing `0x71` matches the arm at `:50657` and leaves the chain, and a caller
passing anything else that reaches `:50667` has already failed the `0x71`
test. No `Arg0` satisfies both.

Checked against a second method rather than asserted from this one, as the
issue asked: `--self-test` confirms no other method in the file dispatches on
`0x71`. The thirteen other `==` methods carry 0x2-0x9 and 0xD0-0xD2, none of
their eleven values being one of `T1WR`'s nineteen, and none of the three
`Switch (Arg0)` methods carries it either — their values are `0x04`-`0x16`,
and `CLKC`/`CLKF`'s are `Zero`/`One`. So the reachability conclusion does not
rest on a spelling the scan did not read.

**Why it is probably still there.** `Method (_Q83, 0, NotSerialized)` at
`dsdt.dsl:52783` has the same body as the `0x71` arm — read `CTWA`, times 8,
`^^^^NPCF.UOCT`, `Notify (NPCF, 0xC0)` — differing only in an `IO80 = 0x83`
line and the leading `^` count. `_Q84` (:52793) and `_Q85` (:52814) are the
same shape as the `0x73` and `0x75` arms respectively. The ASL's EC-query
methods are a second, hardware-triggered copy of the command arms, and the
`0x71` arm looks like a copy of `_Q83` that was pasted into the chain below
an arm already testing the same value. That is a reading of the shape, not a
claim about the vendor's intent, and nothing here can confirm it without a
caller on the machine.

## What this does not say

- **A reference is evidence about the ASL, not about the EC.** Nothing here
  says the EC acts on a byte the ASL reaches for, and a `Notify` firing on a
  field says nothing about what the field does. Deciding what the EC does with
  `CTWA`, `WHMS`, `MGI8` or the `0x0Exx` page needs a human at the laptop.
- **A zero in `asl_refs` is not "unused".** It is what this method did not
  find, from two files, with a rule that cannot see a computed name, a name
  built at load time, or a caller in an ACPI client that is not in this
  repository.
- **No `registers.yaml` `status:` changes here.** An ASL reference is
  evidence about the ASL. Promoting anything is a live-test question and
  needs the hardware, so `ec/annotations/registers.yaml` and the symbol table
  generated from it are untouched.
- **`t1wr_callers.py`'s term list grew by two, not by thirteen.** `0x1175`
  and `0x1176` are four hex digits and five decimal ones and discriminate
  cleanly; the thirteen short `Arg0` values do not, and were measured before
  being left out. `0x81` matches `ECSpec.User_Fan_Level1`
  (`windows/decompiled/v3.1.39.0/GCUService/Define/ECSpec.cs:27`), `0x83`
  matches ILSpy's own `Invalid method header: 0x83` markers, and the decimal
  `97` matches 94 times in `windows/decompiled/v3.9.18.0`. What a caller of
  the CPU-PL or `0x75` arms would look like is still open, and needs a term
  list keyed on the call site rather than on the argument value. The census
  itself is clean: `0x1175` and `0x1176` are one hit each in the DSDT control
  input and **zero in every committed Windows input**, which is a measured
  negative rather than an unsearched one.
- **[../findings.md](../findings.md) §4o** owns the `0x1173` caller search and
  is not reopened here. Its census figures are historical: `ACPI_ARGS` now
  carries two more values, and the tool's own `--self-check` and
  `EXPECTED_TEXT` are where the current numbers live.
- **`ec/annotations/dsdt-ecmg-field-sweep.md` is not edited.** Its §1 last
  paragraph ("The ASL accessor sweep … is **not** here … It is a follow-up")
  and its §5 are half-answered by this, and its own §7 sets the precedent in
  the other direction: *"Recorded here and not by editing that file, per
  CLAUDE.md's rule that a retraction stays visible in place and a correction
  from outside it does not rewrite the original."* So both passages are
  quoted and one half of each is measured above. Its §2 transcript of the
  same command is likewise left as it was: it predates the two ASL columns
  and prints two lines fewer than the block in this file's **Reproducing
  it**, which is current. A reader who runs the command and sees the
  difference is seeing that, not a tool that changed its mind.

## Reproducing it

```console
$ python3 ec/tools/dsdt_ec_fields.py ec/firmware/GMxMGxx_11.800
ECMG  :52194 (AnyAcc)  over OperationRegion :52193 (SystemMemory, base 0xFE410000)
  98 named field(s) over 93 distinct byte address(es), 0x043E-0x0ECF, 16 unnamed bit(s) declared and unallocated
  40 start at an address registers.yaml already holds; 58 do not
  of those 58: 0 with EC-side site(s), 0 PD-image only, 58 with no site found by this method
  35 of 98 name(s) are referenced by the ASL outside their own field list, over 52 (name, line) site(s)
  of those, 16 have a site in the EC image as well; 19 do not, which is a question about the EC's addressing and not about the ASL

$ python3 ec/tools/dsdt_ec_fields.py ec/firmware/GMxMGxx_11.800 --csv --check
$ python3 ec/tools/dsdt_ec_fields.py --self-test        # includes T1WR_ARMS
$ python3 ec/tools/test_dsdt_ec_fields.py
$ python3 windows/tools/t1wr_callers.py --self-check
```

## Follow-ups this opens

1. **`ECXP` has had no sweep at all.** `Field (ECXP, ByteAcc, Lock, Preserve)`
   at `dsdt.dsl:52338` is 94 names in an `EmbeddedControl` region of a
   different address space from ECMG's `SystemMemory` window, and the 24
   names the issue's list attributed to ECXP, which are not ECMG's, are its
   entry point. Measured only as far as this page needed, and pinned by
   `--self-test`: 35 of its 94 names are referenced by the ASL, over 66
   occurrences on 65 lines. **Only 14 of those lines are inside
   `Device (EC0)`** — eleven in the `_Qxx` EC-query methods, two in `_REG` and
   one in `EWAK`. The other **51 are in methods defined outside the device**,
   reached through the same qualified `^^PCI0.LPCB.EC0.<name>` form that this
   page's "What a reference is" counts anywhere in the file: `RKBC` at
   `:51483` (11), `WKBC` (11), `SCMD` (9), `_BST` (8 — 9 occurrences, two of
   them on `:53105`), `ECBE` (7), `_PSR` (2), `_STA` (1), `_TMP` (1), and the
   bare `WUSB` read at `:8163` that is the first-declaration-wins case
   documented above. So a sweep started from the picture "EC0 methods reach
   ECXP" would start from the wrong place for three quarters of its
   references. Nothing says what the offsets mean — that is a separate sweep
   over a region this tool's docstring explicitly declines to join to the EC
   image.
2. **The `0x0Exx` page, with a lead.** See above: 19 of the 20 bytes the ASL
   reaches for have no direct site, the eight it does not reach for are the
   eight the EC copies, and `CCI0`–`CCI3` bridge them.
3. **A caller search keyed on the call site, not the argument value.** The
   thirteen short `Arg0` values cannot be searched by value; what a `T1WR`
   caller looks like in the managed side is a different method.
4. **The other `Arg0`-dispatching methods' arms are untabulated.** `T1WR` is
   19 of the 30 values the `==` methods carry, and of the file's 37 once
   `D3CS`/`RSON`/`RSOF` are counted, and this page tabulates only `T1WR`'s
   twenty. Sweeping the rest means reading the `Switch (Arg0)` arms as well as
   the `ElseIf` chains, and the three `Switch` methods are a different question
   from `T1WR`'s: each of their ten cases is a `CondRefOf` test over
   `\_SB.PCI0.RP05` through `RP23`, not a field of any region this tool
   parses.
