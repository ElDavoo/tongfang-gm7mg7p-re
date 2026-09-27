# The DSDT's ECMG field list, swept against the EC image

`registers.yaml` has a name for an address because some other source had one:
`uniwill-laptop`, the ECSpec, the Windows service, a live read.
`../../docs/findings.md` §3c measures what that leaves out — 1,022 of the 1,063
XDATA addresses the main EC touches carry no name at all. The DSDT is a second
source of names, one the firmware supplies about itself, and nobody had swept
it. This is that sweep: every field in the EC operation region's element list,
with the per-image `MOV DPTR` site count for the byte it names.

It found **16 addresses the DSDT names and `registers.yaml` did not hold**,
and they are now entries (13 `present-untested`, 3 `unknown-not-absent`). The
other 58 names land on bytes with no direct reference site in either image,
which is the open question this sweep produces rather than a result — and it
is `0x0Exx`, a page the sweep reaches for the first time.

Its direct predecessor is [static-refs-audit.md](static-refs-audit.md), which
does the same join for the addresses `registers.yaml` already held; the
`0x0400`–`0x07FF` sweep it defers to is in
[pd-xdata-overlap.md](pd-xdata-overlap.md) §5.1. Everything below is
reproducible from two committed files with no Ghidra, no network and no
hardware: `evidence/acpi/dsdt.dsl` and `ec/firmware/GMxMGxx_11.800`.

## 1. Which field list

**The issue named the wrong one, and the correction is the first result.**

The field names the issue cites — `CTDB`, `PWRE`, `WIFC`, `ODV0`–`ODV5`, the
`TPL*` block — and the `Offset (0x1F4)`-to-`Offset (0x7A7)` span are all in
`Field (GNVS, ...)` at `evidence/acpi/dsdt.dsl:415`, over
`OperationRegion (GNVS, SystemMemory, 0x98F57000, 0x07FA)` at `dsdt.dsl:414`.
That is a 1,038-element UEFI NVS block, not an EC map. It opens with `OSYS`
and no `Offset` at all, so ASL's byte 0 is where the first field lands and the
1,038 names come out at one per byte across `0x0000`–`0x07F9`: the whole
declared `0x07FA` block, filled to its last byte. The span the issue read is
the later part of a NVS structure, and a NVS block that happens to be large
enough to cover the `0x0400`–`0x07FF` XDATA range says nothing about what is
in it.

The DSDT does have an EC operation region. `OperationRegion (ECMG, SystemMemory,
0xFE410000, 0x00010000)` is at `dsdt.dsl:52193`, inside `Device (EC0)` in
`Scope (_SB.PCI0.LPCB)`, and `Field (ECMG, AnyAcc, NoLock, Preserve)` at
`dsdt.dsl:52194` runs to `dsdt.dsl:52328`. **ECMG is the primary output and
`registers.yaml` is the consumer.**

### Why ECMG's offsets are XDATA addresses

Read as ASL, `Offset (0x43E)` in a `SystemMemory` region based at
`0xFE410000` would be `0xFE41043E`, and the offsets plainly are not that. They
are read here as XDATA addresses, and two independent things say so — neither
of them this sweep:

1. **The accessor declares the same window.** `Method (ECRR, 1)` at
   `dsdt.dsl:50497` and `Method (ECRW, 2)` at `dsdt.dsl:50504` both compute
   `0xFE410000 + Arg0` and `MMRW` it. That is the ECMG `OperationRegion`'s
   base, added to a caller's literal, so the accessor and the field list are
   two descriptions of one window: the declared base is the *EC's* XDATA
   window viewed from the CPU, and the offsets are XDATA addresses in it.
   What this does **not** show is the firmware reaching an EC byte through
   the window. `grep -n "ECRW\|ECRR\|T1WR" evidence/acpi/dsdt.dsl` is five
   lines: the three `Method` declarations above and at `dsdt.dsl:50635`, and
   an unrelated `CreateBitField (BUF0, 0x0C48, ECRW)` pair at
   `dsdt.dsl:4437`-`4438`. Nothing calls them, so the access is *not found by
   this method* in use, not absent. The argument is the agreement of the
   declared base, and it is the second bullet below that carries the weight.
2. **Nine addresses agree with names reached from somewhere else.** When this
   sweep ran, 21 of the addresses ECMG names were already in
   `registers.yaml`; nine of those were held under a name the DSDT did not
   supply. Every one of these entries carries a `uniwill-laptop`, `ecspec` or
   `live` tag of its own in `sources` — seven of the nine carry the `dsdt` one
   beside it, `CPU_TEMP` and `GPU_TEMP` do not — and lands on the same byte the
   DSDT gives it:

   | DSDT name | addr | `registers.yaml` entry | the entry's own `sources` tags |
   |---|---:|---|---|
   | `CPTM` | `0x043E` | `CPU_TEMP` | `uniwill-laptop`, `live` |
   | `VGAT` | `0x044F` | `GPU_TEMP` | `uniwill-laptop`, `live` |
   | `GNEN`+`ECDC` | `0x0743` | `CTGP_DB_CTRL / OFFSET` | `uniwill-laptop`, `vendor-3.1.39.0`, `live` |
   | `APL1`–`APL4` | `0x0783`–`0x0785` | `CPU_PL1 / PL2 / PL4` | `ecspec-3.1.6.0`, `vendor-3.1.39.0`, `live` |
   | `APTC`+`APTN` | `0x0786` | `CPU_TCC_OFFSET` | `vendor-3.1.39.0`, `uniwill-laptop`, `live` |
   | `WMS0` | `0x07C6` | `AP_OEM_6` | `uniwill-laptop`, `vendor-3.1.39.0`, `live` |
   | `DBD1` | `0x07D0` | `BATTERY_CHARGE_LIMIT_DOWN` | `ecspec-3.1.6.0`, `acpidriver-3.9.18.0`, `live` |

   That column is each entry's `sources` list in `ec/annotations/registers.yaml`
   with the `dsdt` tag dropped, so every row is checkable against the file; the
   qualifier a tag carries there (`uniwill-laptop(EC_ADDR_FAN_DEFAULT)`,
   `vendor-3.1.39.0(SetCpuTccOffset)`, `ecspec-3.1.6.0(ADDR_PL1/PL2/PL4_SETTING_VALUE)`)
   is dropped here too, because the prefix is what decides. `--self-test`
   checks the *property* each row states — that the entry carries a tag
   matching `uniwill-laptop`, `ecspec`, `live`, `vendor-` or `acpidriver` —
   alongside the address, not this column's wording; the tag is the half of
   the claim that makes this a measurement rather than a restatement. Nine
   addresses a block would have to get right by chance is a better argument
   than any one of them.

   The other twelve are named *from* the DSDT and carry no independent weight:
   `XDATA_0460` 0x0460, `XDATA_0468` 0x0468, `GPU_DYNAMIC_BOOST_STATUS`
   0x07C4, `DBD2` 0x07D1, `GFID` 0x07D3, `CPUA` 0x07D4, `DBAP` 0x07D5, `DBSP`
   0x07D6, `CGCT` 0x07D7, and the three `CTGP_DB_CTRL` bytes 0x0744–0x0746
   that the DSDT supplied names for. `XDATA_0460` and `XDATA_0468` are the
   clearest case: they are named for their own address because the DSDT is the
   only source that has ever given them a name at all.

### The one test that would promote a GNVS offset, taken

A GNVS-named field would become an EC-register candidate if some ASL path both
referenced that name and reached an EC byte. The tool's answer, measured
rather than argued:

- **No ASL path calls `ECRW`, `ECRR` or `T1WR`.** The only *Method*
  declarations of the three are at `dsdt.dsl:50497`, `50504` and `50635`, and
  nothing in this file invokes any of them. The only other occurrence of any
  of the three names is an unrelated `CreateBitField (BUF0, 0x0C48, ECRW)` bit
  field at `dsdt.dsl:4437`-`4438`, an alias into the local buffer declared at
  `dsdt.dsl:4156` that reads and writes no EC byte. So nothing in the NVS list
  can be shown to reach an EC byte.
- **`T1WR`'s body dispatches on values that name fields rather than address
  them.** `Arg0 == 0x81` writes `APL1` (`dsdt.dsl:50637`), `0x84` writes
  `APL4` (`dsdt.dsl:50646`), `0x85` writes `APTN`/`APTC` (`dsdt.dsl:50650`).
  Those are ECMG field names reached by dispatch code, and reading an `Arg0`
  as an address would be a category error.

So `dsdt_ec_fields.py` **refuses the count join for GNVS** rather than
performing it and annotating: a `static_refs` column beside 1,038 NVS offsets
would read as evidence about those bytes while measuring something else. The
same call §3a makes about the two 8051 programs sharing one dump.
`--region gnvs` still extracts and reports the list — that is what the issue
asked for, and it costs one extra mode — and the committed CSV covers ECMG
alone.

The ASL accessor sweep is a genuinely different and larger question, and it is
**not** here. `T1WR` alone dispatches on 19 distinct `Arg0 == 0x…` values and
the DSDT has 30 across every such method; those are a vendor command protocol,
not XDATA addresses, so it is not a grep. It is a follow-up.

## 2. Reproducing it

```console
$ python3 ec/tools/dsdt_ec_fields.py ec/firmware/GMxMGxx_11.800
ECMG  :52194 (AnyAcc)  over OperationRegion :52193 (SystemMemory, base 0xFE410000)
  98 named field(s) over 93 distinct byte address(es), 0x043E-0x0ECF, 16 unnamed bit(s) declared and unallocated
  40 start at an address registers.yaml already holds; 58 do not
  of those 58: 0 with EC-side site(s), 0 PD-image only, 58 with no site found by this method
```

Two figures in that summary are a function of *when* you run it, and both are
worth stating rather than leaving to be noticed. The sweep found **24 of the
98 elements**, at 21 of the 93 bytes, starting at an address `registers.yaml`
held; 74 elements at 72 bytes were left to consider. §3 lands 16 of those as
entries, so a fresh run today reports 40 elements at 37 bytes held and 58 not,
with none of the 58 carrying a site. The `in_registers` and `grade` columns of
the committed CSV are a join against `registers.yaml`, so that table moves when
`registers.yaml` does and `--check` is what notices.

```console
$ python3 ec/tools/dsdt_ec_fields.py ec/firmware/GMxMGxx_11.800 --csv --check
ec/annotations/dsdt-ecmg-fields.csv: this run reproduces it byte for byte (99 lines)

$ python3 ec/tools/dsdt_ec_fields.py --self-test
dsdt_ec_fields.py --self-test
  ok    DBEN is bit 3 of 0x07C4, width 1 (dsdt.dsl:52240) -- registers.yaml: GPU_DYNAMIC_BOOST_STATUS
  ok    DBST is bit 5 of 0x07C4, width 1 (dsdt.dsl:52242) -- registers.yaml: GPU_DYNAMIC_BOOST_STATUS
  ok    WHMS is bit 5 of 0x07C5, width 1 (dsdt.dsl:52245) -- windows/tools/gpu_block_watch.py: (0x07C5, WHMS b5)
  ok    all 9 of the addresses ECMG names that registers.yaml holds are still held
  ok    and all 9 of them were named from something other than the DSDT, which is what makes them independent agreement
  ok    ECMG names 98 fields over 93 byte addresses, 0x043E-0x0ECF
  ok    ECMG declares one field list, at dsdt.dsl:52194
  ok    GNVS names 1038 fields and the tool still says it is a NVS block, not a register map
  ok    GNVS opens with fields and no Offset, so ASL's byte 0 is where OSYS lands -- which is why its 1,038 names come out one per byte across 0x0000-0x07F9, filling the whole declared 0x07FA block, and not the 0x1F4-0x7A7 window the issue read them out of
  ok    the ECMG offsets reach past the block registers.yaml and xdata_span_survey.py already cover (0x0400-0x07FF), which is why the 0x0Exx page is new
  ok    refuses an Offset that is not a literal byte offset -- ...
  ok    refuses an Access keyword, whose element widths read differently -- ...
  ok    refuses one name used at two addresses in the same region -- ...
  ok    refuses a field list that never opens -- ...
  ok    refuses a Field list naming a region with no OperationRegion -- ...
  ok    refuses a line the grammar does not name -- ...
  all assertions passed

$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
176 entries / 208 addresses: every static_refs, static_refs_main_ec and static_refs_pd_image reproduced from ec/firmware/GMxMGxx_11.800
```

The last one is the test that matters. It recomputes all three count columns
for all 208 addresses from the committed image and fails on any mismatch, so
the 16 new rows' numbers are reproduced rather than trusted.

`--self-test` is run by hand rather than from `../../.github/scripts/agent-gates.sh`:
that file lives under `.github/`, which this repository's pipeline push token
cannot write, so adding the mode to the gate's tool loop is a human's change
to a template file. `../tools/test_dsdt_ec_fields.py` holds the parser's edge
cases and the `--check` failure path, and is runnable standalone the same way.

**Why bit-granular.** `Offset (0x7C4)` is three unnamed bits, `DBEN`, one
unnamed bit, `DBST` — so `DBEN` is bit 3 and `DBST` is bit 5, and a parser
that rounds sub-byte widths to whole bytes puts both at bit 0. That is not
hypothetical: it is the reading `registers.yaml`'s own note records having had
to correct in place. The two bit oracles are pinned from opposite ends of the
stack — `registers.yaml` reads `0x07C4` from the DSDT, and
`windows/tools/gpu_block_watch.py` names `(0x07C5, "WHMS b5")` from the
Windows capture side — so the arithmetic has to satisfy both.

## 3. The candidates

16 addresses the DSDT names, `registers.yaml` did not hold, and this sweep
lands as entries. Ranked by EC-side count, as the issue asked:

| addr | bit | width | DSDT name | dsdt.dsl | main EC | PD | status landed |
|---|---:|---:|---|---:|---:|---:|---|
| `0x07C5` | 5 | 1 | `WHMS` | :52245 | 10 | 0 | `present-untested` |
| `0x074C` | 0 | 4 | `PDIN` | :52213 | 9 | 0 | `present-untested` |
| `0x0788` | 0 | 8 | `CTWA` | :52222 | 4 | 0 | `present-untested` |
| `0x07A4` | 2 | 1 | `GC6S` | :52225 | 4 | 0 | `present-untested` |
| `0x0EA8` | 0 | 8 | `CTL0` | :52288 | 3 | 0 | `present-untested` |
| `0x0EA9`–`0x0EAF` | 0 | 8 | `CTL1`–`CTL7` | :52289–52295 | 1 each | 0 | `present-untested` |
| `0x0EB8` | 0 | 8 | `MGI8` | :52304 | 1 | 0 | `present-untested` |
| `0x07C0` | 0 | 8 | `AP01` | :52235 | 0 | 1 | `unknown-not-absent` |
| `0x07C1` | 0 | 8 | `AP02` | :52236 | 0 | 1 | `unknown-not-absent` |
| `0x07C2` | 0 | 8 | `AP10` | :52237 | 0 | 1 | `unknown-not-absent` |

The three `unknown-not-absent` rows are the existing vocabulary for the case
`../../docs/findings.md` §3a settled: the one site that made each address look
present is in the ITE8850-PD image, a separate program with its own XDATA
map, so it is a reference to a different program's byte. `present-untested`,
and not `unknown-not-absent`, would be the wrong reading of a PD-only hit, and
`absent` would be the worse one — see §4.

Three of the thirteen are the most interesting:

- **`PDIN` 0x074C, 9 sites.** The ASL reads all four of its bits as a value
  it switches on, not as a flag: `Method (SMRW, 1)` at `dsdt.dsl:50764`
  compares it against `0x08`/`0x07`/`0x05` (`dsdt.dsl:50774`) and `0x04`/`0x06`
  (`dsdt.dsl:50786`) inside a test on `GFID`, and again at `:50801`, `:50813`,
  `:50828`, `:50841` and `:50856` for the other `GFID` arms. So the DSDT
  gives both a name and the width that name occupies, from two directions.
- **`CTL0`–`CTL7` at 0x0EA8–0x0EAF, 10 sites across 8 bytes.** Disassembled
  rather than inferred from the count, because the eight-byte spacing invites
  exactly the wrong guess: bank0 `0xF335`-`0xF374` is eight 8-byte stanzas,
  each `mov DPTR,#src / movx A,@DPTR / mov DPTR,#dst / movx @DPTR,A`, copying
  `0x0EA8`-`0x0EAF` into `0x0F61`-`0x0F68` one byte at a time. **There is no
  `inc dptr` in it** — it is a straight-line copy, so the run is a value
  something chooses rather than a table being walked. That block is eight of
  the ten sites, one per byte. The other two are both inside bank0 `0xF221`:
  `0xF221` reads `0x0EA8` and compares it against `0x12`, and `0xF234` is that
  `cjne`'s own branch target — `mov DPTR,#0x0ea8 / movx A,@DPTR / ret` — so
  the mismatch arm re-reads the byte and hands it back to the caller. That
  function *is* in the census, and it is why `0x0EA8` and `0x0EB8` are reached
  while `CTL1`-`CTL7` are not. What writes `0x0EA8` is still not established,
  and the copy says only that the eight bytes are read together.
- **`MGI8` 0x0EB8, 1 site.** The only byte of the 32 in the `MGI0`–`MGIF` and
  `MGO0`–`MGOF` banks at 0x0EB0–0x0ECF with any direct site. Sixteen
  neighbouring bytes and one site is a shape this file does not explain. The
  site is the read-modify-write in `bank0:0xF221` that also reads `0x0EA8`
  and compares it with `0x12`, so `MGI8` is written when that comparison
  passes — which is a statement about the branch, not about what the byte
  means.

## 4. Calibration

This is the part `../../docs/findings.md` §4 exists to enforce, so it is
stated here rather than left to the reader.

- **A DSDT field name is a hint about vendor intent, not a confirmed
  function.** None of the 16 names is expanded. `WHMS` is a name, not a
  statement about what the bit does, and nothing in this sweep is evidence the
  EC acts on any of the sixteen. The two conclusions
  [../../docs/findings.md](../../docs/findings.md) §4 records having had to be
  retracted — a charge-cap claim from a resting battery voltage, and a "this
  register does not exist" claim from a static scan that turned out to have a
  blind spot — were both phrased more strongly than their evidence supported,
  and neither is a shape this file writes in.
- **A reference count is not behaviour.** The counts are `MOV DPTR,#addr` byte
  patterns, the same scan `../tools/scan_refs.py` performs. A site can build a
  CODE pointer or hand DPTR to a subroutine; `../tools/trace_xdata_refs.py`'s
  `classify()` is what separates those, per site, and this sweep does not run
  it. A register write being accepted would still not be evidence the EC acts
  on it.
- **Every zero here is "not found by this method", never "absent."** The CSV's
  `grade` column spells it out — a row with no site reads
  `not-found-by-this-method`, which is deliberately **not** one of
  `registers.yaml`'s `status:` values, so it cannot be lifted into an entry by
  someone reading the table for candidates. A test in
  `../tools/test_dsdt_ec_fields.py` asserts that token is absent from
  `registers.yaml`'s vocabulary, which is the property that makes it safe.
  `0x07B9` is the standing counter-example beside every zero in the table: a
  byte Windows demonstrably writes, with zero direct references anywhere in
  the image.
- **Nothing was read on hardware, and nothing here could be.** No live test
  ran. Promoting any of the sixteen needs a human at the machine, and that is
  a separate piece of work with a separate issue.
- **The whole-window `0x0400`–`0x07FF` sweep is not repeated here.**
  `../tools/xdata_span_survey.py` produces the per-block table and
  `pd-xdata-overlap.md` §5.1 carries it over exactly that span. Re-running it
  would produce a second number for a question already answered.

## 5. What a zero leaves open: the `0x0Exx` page

Of the 98 names, **59 sit on the `0x0Exx` page** (`0x0E0D`–`0x0ECF`) — the
largest single group in the list, and the part of it `xdata_span_survey.py`'s
`0x0400`–`0x07FF` span never covered. Nine of those 59 **names** have a direct
site — the `CTL0`–`CTL7` run and `MGI8` — and those nine names carry ten sites.
The other **50 have none** — `SN1T`–`SN5T`,
`F1SH`/`F1SL`/`F1DC`/`F1CM`/`F2DC`/`F2CM`, `UVER`/`RESV`, `CCI0`–`CCI3`, the
`MGI`/`MGO` banks either side of the one byte that has a site, and the
controller page's opening `CPUT`/`PCHT`.

**That is stated as an open question, not a conclusion.** An ASL-visible
controller block the EC image never names with a direct `MOV DPTR` is exactly
what the indirect-addressing blind spot in `../../docs/findings.md` §4c would
produce — and it is also what a subsystem the EC does not touch would look
like. One static method cannot tell those apart, and this file does not pick
one. The count is 50 names with no direct site, which is a lower bound on what
is there and nothing else.

The place to start is the `CTL0`–`CTL7` run at `0x0EA8`. Ten sites across
eight consecutive bytes is the one place on the page with enough signal to
decode, and it has now been decoded: bank0 `0xF335` copies the run into
`0x0F61`-`0x0F68` byte by byte, and bank0 `0xF221` reads `0x0EA8`, compares
it with `0x12`, and at `0xF234` re-reads it to return it to the caller when
the comparison fails. What that leaves open is the half the sweep cannot
reach — what *writes* `0x0EA8`, and what reads `0x0F61`-`0x0F68` afterwards,
which is a different sweep over a different region. The copy is a real
result; the page's meaning is not, and one routine that moves bytes says
nothing about the other 50 the EC never names directly.

## 6. What the sixteen did downstream

Adding a name to `registers.yaml` moves four things in this tree that read
it. They are recorded here because a reader diffing this change will see all
four, and because two of them are the kind of consequence that looks like a
regression if it is not explained.

**`named_in_tree` 175 → 181, and the gap 17 → 27.** `xdata_register_map.py`'s
oracle is `len(symbols) - len(NOT_IN_TREE)`, so 16 new names and 10 of them
not in the decompiled tree moves both terms. The arithmetic is the same one
every previous move in that comment block records, and the measurement behind
it is more interesting than the number: **six** of the sixteen are in the tree
and **ten** are not, and the split is not the one a reader would guess.

- `0x074C`, `0x0788`, `0x07A4`, `0x07C5` are in the tree — the four EC-side
  hits outside the `0x0Exx` page, each reached by an exported function.
- `0x0EA8` and `0x0EB8` are in the tree **because of `bank0:0xF221`**, an
  exported function that reads `0x0EA8`. `CTL1`-`CTL7` are not, because their
  only sites are in the unexported copy at bank0 `0xF335`. So the head of a
  run and its tail land on opposite sides of this boundary for a reason that
  has nothing to do with the run, which is worth a reader knowing before they
  read a count as a property of the bytes.
- `0x07C0`-`0x07C2` are not, and for a different reason: their only site is in
  the PD image, so the EC export has nothing to find.

Each of the ten has a `NOT_IN_TREE` reason, in the tool's three-word
vocabulary, citing the site or the gap it re-derives from. None uses the word
that vocabulary forbids, and the self-test asserts that.

**Six `name_basis` cells moved from `code-shape` to `ec-register`.** The
grader's definition of `ec-register` is "an XDATA address in `registers.yaml`
carrying a decoded name", so the six functions that touch `0x074C`, `0x07C5`
or `0x0EB8` now qualify on the rule's own terms. `grade_name_basis.py
--apply` wrote them; no name was changed.

**Eight plate comments were reworded.** `"0x07C5 has no entry in
ec/annotations/registers.yaml"` is a house idiom for saying what a byte is
*not* yet, and `build_ec_decompile.py` polices it precisely because a stale
one is worse than a missing one. Each of the eight — `0x83FF`, `0x9167`,
`0xBA36`, `0xBB80`, `0xBB81`, `C4F8`, `0xCC64` and `0xCCFC` — now names the new
entry where the name helps (`read_low_nibble_074c`'s returned nibble *is*
`PDIN`, since the DSDT gives that name to the byte's low four bits) and keeps
the no-entry claim over the addresses that still have none. The other two rows
this sweep touched, `bank0:F221` and `bank1:92DC`, moved `name_basis` only;
neither comment carried the idiom.

**The committed decompile has not been re-exported.** `ANNOTATIONS` and
`XDATA` are both passed as `-postScript` arguments to `ExportDecompile.java`
(`../tools/build_ec_decompile.py:721`-`722`, and again at `:700`-`701` on the
rebuild path), so the names and the reworded comments are applied at *export*
time — in `export-only` mode as much as in `rebuild-project`, since that mode
copies the committed project to scratch and applies both to the copy. Only
`rebuild-project` writes the `.gpr`/`.rep`, so a plain re-export would pick
all of this up without the mode two branches cannot both run. The committed
`.c` simply has not been re-exported: re-exporting is a separate, large diff
and is not this change. Until it happens the committed `.c` still spells
`DAT_EXTMEM_0ea8`, and §3c's "41 main-EC addresses the decompile spells by
symbol" is unchanged by this sweep. The eight reworded plate comments travel
the same route, so a reader diffing this tree against `ec/decompiled/bank0/`
will find eight exported `.c` files still carrying the pre-#30 sentences. Five
carry the literal "0x074C has no entry in
ec/annotations/registers.yaml" or "0x07C5 has no entry" for bytes that now hold
`PDIN` and `WHMS` (`9167.c`, `BA36.c`, `BB80.c`, `BB81.c`, `C4F8.c`); the other
three carry the same idiom in its list form (`CC64.c` and `CCFC.c` over
`0x07C5`/`0x0788`, `83FF.c` over the `0x0788` that `0x09E9` is synced into —
though `83FF.c`'s own no-entry claim is about `0x09E9` and is still true, so
what is stale there is only the missing `CTWA`). That is expected until the
re-export, and nothing in the generated files is edited to hide it.

## 7. A note on `static-refs-audit.md`'s scope line

`static-refs-audit.md` scopes itself in three places: "This file audits all 29
addresses in `registers.yaml`", "`registers.yaml` now carries
`static_refs_main_ec:` and `static_refs_pd_image:` on every entry", and the
`check_register_counts.py` output it quotes reading "19 entries / 29
addresses". **All three are now historical.** `registers.yaml` holds 176
entries over 208 addresses, 16 of them added by this sweep, and the tool says
so on every run.

Recorded here and not by editing that file, per CLAUDE.md's rule that a
retraction stays visible in place and a correction from outside it does not
rewrite the original: nothing in `static-refs-audit.md` is wrong about the 29
addresses it audited, and its scope statement was true when written. Re-run
`../tools/check_register_counts.py` for the current figures.

## Files

- `../tools/dsdt_ec_fields.py` — the extraction and the join. Modes: default
  table, `--csv`, `--check`, `--self-test`, `--region {ecmg,gnvs}`, `--out`.
- `../tools/test_dsdt_ec_fields.py` — the bit arithmetic, the refusals and the
  `--check` failure path.
- `dsdt-ecmg-fields.csv` — generated, 98 rows, one per named element. Columns:
  `region, addr, bit, width, name, dsdt_line, static_refs,
  static_refs_main_ec, static_refs_pd_image, in_registers, grade`. Written by
  the tool; `--check` proves it.
- `registers.yaml` — 16 new rows at the end of the list, 13
  `present-untested` and 3 `unknown-not-absent`, each with its `dsdt.dsl`
  line and all three counts.
- `../ghidra/xdata-symbols.csv` — regenerated by
  `../tools/gen_xdata_symbols.py`, never hand-edited. 192 → 208 symbols. Each
  row carries `register_status` verbatim, so a decompilation that spells `CTL0`
  instead of `DAT_EXTMEM_0ea8` also shows the reader that the entry says
  `present-untested`.
- `ghidra-functions.csv` — `grade_name_basis.py --apply`, which regraded six
  rows from `code-shape` to `ec-register` (the rule's own definition: the
  routine touches an XDATA address `registers.yaml` now carries a decoded name
  for). Eight plate comments saying one of the sixteen bytes "has no entry in
  `ec/annotations/registers.yaml`" were reworded, each to name the new entry
  where the name helps and to keep the no-entry claim over the addresses that
  still have none. That idiom is a house convention and
  `build_ec_decompile.py` polices it, so adding an entry makes the sentences
  that denied one false.
- `xdata-registers.csv`, `xdata-clusters.csv` — regenerated by
  `xdata_register_map.py`, which reads `registers.yaml` for names. Six rows
  gain their DSDT symbol and two clusters gain a named-addresses list; no row
  count and no cluster key moves.
- `../tools/xdata_register_map.py` — ten `NOT_IN_TREE` reasons added (7/3, see
  §6) and the `named_in_tree` oracle moved 175 → 181, which is 208 − 27 and
  the same arithmetic every previous move in that comment block records. The
  decompile is deliberately not rebuilt; §6 says why.

**Not touched:** [static-refs-audit.md](static-refs-audit.md) (referenced, not
edited), [xdata-register-map.md](xdata-register-map.md),
`../annotations/README.md`, `../README.md`, `../../docs/MISSION.md`, anything
under `.github/`.
