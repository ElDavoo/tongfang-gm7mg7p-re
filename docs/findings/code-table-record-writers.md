# The writers a `MOV DPTR` scan cannot see: every record of the EC's CODE tables

`ec/annotations/xdata-0440-readers.md` §5 found one of these by hand. The
destination address is in a **table in CODE**, not in an instruction, so the
scan that produced `xdata-0400-045f-sites.csv` and every count derived from it
is blind to the class by construction. This is that finding as a method:
`ec/tools/code_table_records.py` walks the helpers' call sites, decodes the
table each one names, and reports every record.

**Nothing here is a live observation.** No register was read back, no capture
opened, no hardware or Windows involved. Every row is a *stored value* read out
of a committed table against a committed image. CLAUDE.md's readback-is-not-
acting rule applies with more force than usual here: eight of the twelve records
on this page store `0x00`, so "the record stores zero" is a very short step from
"the byte reads as zero", and the four that store something else — `0x043E`=
`0x20` and `0x0457`=`0x83`/`0x80`/`0x05` — are no more a statement about what
the byte holds than the eight are. Nothing here establishes either. No
`status:` in `ec/annotations/registers.yaml` moves, and none should.

## 1. How to reproduce it

```console
$ python3 ec/tools/code_table_records.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/code_table_records.py ec/firmware/GMxMGxx_11.800 --csv \
      | diff - ec/annotations/xdata-code-table-records.csv
$ python3 ec/tools/code_table_records.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/code_table_records.py ec/firmware/GMxMGxx_11.800 --self-test
$ python3 ec/tools/code_table_records.py ec/firmware/GMxMGxx_11.800 \
      --csv --page 0x0400-0x045F
```

`ec/annotations/xdata-code-table-records.csv` is the `--csv` output, one row
per record. The suite is `ec/tools/test_code_table_records.py`, which `bash
tools/run-tests.sh` finds without being registered anywhere.

**The columns, and what each one is for.** `helper` names which table a row
came from, which is what keeps the two shapes (§7) from reading as one
population. `call_site` is the `lcall` whose arguments named the table, or the
routine's own address for the in-routine shape. `record_index` counts within
that table from zero, so a row can be pointed at rather than searched for.
`code_runtime` and `code_file_offset` are the same three bytes in the two
addressings the tree uses — a runtime address in the loaded bank image, and an
offset into `ec/firmware/GMxMGxx_11.800` — and both are carried because §3's
`r2` spot checks are written against a bank image while a reader with only the
committed firmware has the other. `xdata` is the destination the record names
and `value` the byte it stores there. A row is the same fact in seven cells; the
destination and the value are the finding, and the rest locate it.

The census, over the seven `0xA530` call sites alone:

| helper | records | distinct destinations | distinct stored values |
|---|---:|---:|---:|
| `code_table_scatter_to_xdata` (bank1 `0xA530`) | 136 | 115 | 18 |
| `init_xdata_from_code_table_64fd` (bank0 `0xBFDE`) | 90 | 90 | 12 |

**136 records over 115 distinct destinations, spanning `0x0363`-`0x2201`.** The
record count and the destination count are different claims and both are
printed: 136 records over 115 destinations says 18 destinations are named by
more than one record, and the tool names them. `0x0457` is the sharpest — four
records storing four different values. The other seventeen are not all named
twice: `0x0440` is named three times, and the remaining sixteen are named twice.
A byte count alone would understate the class.

## 2. Where the call sites come from, and why that is not a byte scan

`ec/annotations/bank-call-targets.csv` — a committed census of every direct call
in the main EC image — has exactly seven `lcall 0xA530` rows and one `lcall
0xBFDE`. Reading them from there rather than scanning for the `12 lo hi` bytes
is not tidiness: a byte scan of an 8051 image counts operand bytes as opcodes,
which is why `xdata-0440-readers.md` §7.3's own exclusion is written the way it
is. A call added to the firmware is already in this tool's input.

Two properties of the lookup are load-bearing and both are asserted, because
each failed silently at least once while this was being written:

- **A helper the census names no caller for is reported, not skipped.** An empty
  result is a question about the lookup, and `0xA530` has seven callers and
  `0xBFDE` one, so a zero means the query broke. It did: the first version
  compared the `target` column as an uppercased *string*, which uppercases the
  `x` in `0xA530` too, matched nothing, and reported a clean sweep of 90
  records from the other helper. The compare is numeric now, and a helper with
  no committed call site is a refusal.
- **A table this tool cannot decode is a refusal with a reason, never a
  skip.** `decode_call_site()` raises rather than returning `None`, so a caller
  cannot drop it on the floor, and `main()` exits non-zero.

## 3. The argument rule, and that it is a shape rather than a window

Every `0xA530` call site is immediately preceded by `mov DPTR,#imm16`
(`90 hi lo`) then `mov R2,#imm8` (`7A nn`), and that five-byte pair is the whole
of the table's base and length. `decode_call_site()` checks all three opcodes —
including the `lcall` at the census's `file_offset` — and refuses anything else.
Read with `r2` over the bank images §1's bank1 build makes, at the four
unexported call sites:

```console
$ cd ec/tools
$ python3 make_bank_image.py ../firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x82c4; pd 4' /tmp/bank1.bin
            0x000082c4      908594         mov dptr, #0x8594
            0x000082c7      7a01           mov r2, #0x01
            0x000082c9      12a530         lcall 0xa530
            0x000082cc      1295ae         lcall 0x95ae

$ r2 -a 8051 -e scr.color=0 -q -c 's 0x83b2; pd 4' /tmp/bank1.bin
            0x000083b2      908453         mov dptr, #0x8453
            0x000083b5      7a43           mov r2, #0x43
            0x000083b7      12a530         lcall 0xa530
            0x000083ba      900801         mov dptr, #0x0801
```

The same three-instruction shape holds at `0x82F8`/`0x82FB` and
`0x8418`/`0x841B`, and `0x8418` is inside the exported
`zero_1510_and_clear_xdata_flag_bits`. `r2` and this tool agree on all seven
bases and counts, which is the second decoder `trace_xdata_refs.py`'s docstring
asks for on anything load-bearing.

**A window would have been the alternative and it is wrong here.** "Read
`imm16` out of the five bytes before the call" decodes a table that is not there
whenever the caller sets DPTR for its own reasons and passes the count in a
register. `mov R2,Rn` (`0x8A`) is a plausible shape for a helper taking its
length from a variable, and it is refused by name — the failure says what it
found, because a message reading only "undecodable" sends the reader looking
for the reason instead of showing it.

The record bytes agree with the second decoder too, which settles the field
order and the stride rather than assuming them:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8594; px 3' /tmp/bank1.bin
0x00008594  0457 83                                  .W.
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8453; px 24' /tmp/bank1.bin
0x00008453  0440 0004 5700 0440 0022 00ff 2201 0006  .@..W..@.".."...
```

`0x0457 = 0x83` and, at the table's head, `0x0440 = 0x00`, `0x0457 = 0x00`,
`0x0440 = 0x00` again — big-endian destination, value third, stride three.

## 4. The seven tables, and what each one seeds

| call site | containing routine | CODE base | records | destinations in `0x0400`-`0x04FF` |
|---|---|---|---:|---|
| bank1 `0x83B7` | unexported; entry bank1 `0x8354` | `0x8453` | 67 | 18, listed below |
| bank1 `0x841D` | `zero_1510_and_clear_xdata_flag_bits` (`0x8418`) | `0x851C` | 23 | 4 |
| bank1 `0x82FD` | unexported (nearest exports `0x820F` / `0x8300`) | `0x8561` | 17 | 5 |
| bank1 `0x82C9` | unexported (nearest exports `0x820F` / `0x8300`) | `0x8594` | 1 | 1 |
| bank1 `0xC740` | `setup_state_and_copy_30_byte_table` (`0xC700`) | `0xC6E2` | 10 | none (`0x0390`-`0x0898`) |
| bank1 `0xC7AC` | `copy_6_bytes_via_a530_and_clear_0497b7` (`0xC7A7`) | `0xC7A1` | 2 | none (`0x038E`-`0x038F`) |
| bank1 `0xC7F2` | `copy_48_bytes_via_a530_from_c7bd` (`0xC7ED`) | `0xC7BD` | 16 | none (`0x0363`-`0x082F`) |

The first three bases are contiguous — `0x8453` + 67×3 = `0x851C`, + 23×3 =
`0x8561`, + 17×3 = `0x8594` — so 108 records over `0x8453`-`0x8596` are one
table walked in four chunks. `xdata-0440-readers.md` §5 already noted the
contiguity for the 108; what it did not have is the 28 records at `0xC6E2`,
`0xC7A1` and `0xC7BD`, and those three are what carry the method past this one
table.

## 5. The twelve records on the `0x0400`-`0x045F` page

Seven bytes, twelve records, and **every one of them invisible** to
`trace_xdata_refs.py`, `xdata_register_map.py` and
`ec/annotations/xdata-0400-045f-sites.csv`, because the destination is in CODE
and those scans look for `MOV DPTR`:

```
0x043E <- 0x83B7#12 = 0x20      (CPU_TEMP, seeded to 32)
0x0440 <- 0x83B7#0  = 0x00, 0x83B7#2  = 0x00, 0x841D#9  = 0x00
0x0457 <- 0x83B7#1  = 0x00, 0x841D#1  = 0x05, 0x82FD#2  = 0x80, 0x82C9#0 = 0x83
0x0459 <- 0x841D#2  = 0x00
0x045B <- 0x83B7#52 = 0x00
0x045C <- 0x83B7#36 = 0x00
0x045F <- 0x83B7#13 = 0x00
```

Reproduce just these with `--page 0x0400-0x045F`. Three of them are
`xdata-0440-readers.md` §5's records for `0x0440`, which now arrive from a
re-runnable tool rather than an inline snippet; the other nine are new to this
page.

**What each seed changes, read exactly.**

- **`0x043E` (`CPU_TEMP`) is seeded to `0x20`.** A three-byte CODE record stores
  32 into the byte. That is the strongest single statement here and it is
  still narrow: it does not say the byte *reads* 32 between reset and the
  first real reading, because **when** these tables are walked is not
  established. `xdata-0440-readers.md` §5 gives the reason for the whole class:
  the routine holding `0x83B7` has no export and no recorded caller (entry
  bank1 `0x8354`), the one holding `0x841D` is reached from `0x86EE`, which is
  neither, and `bank-call-targets.csv` has no row targeting either. So the
  timing limit is stated wherever the seed is, and `CPU_TEMP` stays
  `confirmed-working` on its live coretemp cross-check — which this neither
  strengthens nor weakens. The seed is a static fact about a table.
- **`0x0457` is seeded four different ways** — `0x00`, `0x05`, `0x80`, `0x83`,
  from four call sites. This is the sharpest case on the page and the reason it
  is worth a method: two of the four call sites sit in unexported routines
  (`0x82FD`, `0x82C9`), and its four EC-side `MOV DPTR` sites are all
  read-modify-writes, one in each of the four named exports
  `ec/decompiled/bank1/818A.asm`, `81C5.asm`, `823A.asm` and `8261.asm`
  (§5 of the page document, §11
  item 4). Four whole-byte stores and four bit operations on one byte.
- **`0x0440` keeps its §5 reading**: three records, all storing `0x00`. The
  entry's "no direct writer" is now explained by mechanism rather than left as
  a puzzle — the writer is in CODE, which is *why* no scan finds it, and
  `static_refs` stays 43 with `static_refs_main_ec` 43 and no writer row,
  because those keys count `MOV DPTR` sites and a record is not one.
- **`0x0459`, `0x045B`, `0x045C`, `0x045F`** each gain a `0x00` seed *on top of*
  the direct writers their entries already name. This is the distinction the
  issue's wording blurred and it is worth keeping: **`0x043E` and `0x0440` have
  no direct writer at all** — their EC-side sites never store — so for those
  two the record is the only writer this repository has found, while for the
  other five the record is an additional writer that a site count cannot see.
  Both suites assert the split.

**What none of the twelve is.** Not a readback, not a behavioural test, not
evidence the EC acts on the value afterwards, and not an `absent` or `inert`
claim about anything. A zero stored by a record is a zero stored by a record.

## 6. §6's entry rule re-run, and committed as a negative

`ec/annotations/xdata-0400-045f.md` §6 enters a byte in `registers.yaml` if and
only if the EC image has a direct `MOV DPTR,#addr` site for it, which leaves 50
bytes out — 39 with no site in any image, 11 with sites only in the PD image.
The rule was checked once, by hand, in a PR about a different byte. Re-run with
the record pass in the loop:

**No record names any of the 50.** The rule holds for the whole page, not only
for `0x0440`.

That is committed as a **property, not a list** —
`EntryRuleTests.test_no_code_record_names_a_not_entered_byte` recomputes the
not-entered set from `xdata-0400-045f-sites.csv` at test time and asserts
nothing in it is named by a record, so it holds whatever the set is on the day.
Two guards keep it from passing vacuously: the set is asserted non-empty, and
the converse is asserted too — the records *do* reach the page, so the negative
cannot pass by the walk having reached nothing. The 50 addresses are §6's to
state and this file does not repeat them.

**Why the negative matters and where it stops.** It says the record class does
not reach the 50; it does not say the 50 are unused, and §6's own caveat —
"a zero here means not found by this method" — is unchanged by it. A byte
reached by a helper nobody has enumerated, or by one of the seven
parameterised "zero N bytes at DPTR" helpers, would still be invisible here.

## 7. The second helper, and why it is in the same table

`init_xdata_from_code_table_64fd` (bank0 `0xBFDE`) is the same class in a
different shape: 90 three-byte records at CODE `0x64FD`, the first two bytes of
each a big-endian XDATA destination. `xdata-0440-readers.md` §7.3 already
bounded it — all 90 destinations are in `0x1600`-`0x16F0`, none on this page —
and it is carried here so the class is one population rather than two findings.

Its base and count are **inside the routine**, not in a caller's arguments: a
`mov DPTR,#0x64FD` and a `cjne A,#0x5a` loop bound, against
`ec/decompiled/bank0/BFDE.asm`. That is why `HELPERS` dispatches on the shape
and a third helper is a new row rather than a rewrite of the decode. Two
properties of the rule are worth stating because a looser version of either gets
the wrong answer on this routine:

- The base is the `mov DPTR` that **two** bytes are read through — the two
  leading bytes that become the destination's high and low halves. `0xBFDE` also
  loads `0x64FF` and reads one byte from it, which is the *value* of the record
  at `0x64FD` + 2. The scan walks instructions (`disasm8051.OPCODE_LEN`), not
  bytes: a rule of the form "is there a `movc` within 24 bytes of this
  `mov DPTR`" would answer yes for `0x1674`, the unrelated `mov DPTR` in the
  routine's preamble, and pick the wrong base.
- The count is the `cjne` immediate, and the scan stops at the routine's `ret`.
  A second decoy table past the `ret` is not reached — asserted on a fixture.

`--self-test` re-derives both from the image and compares them against the
constants in `HELPERS`, so a stale constant shows up as a self-test failure
rather than quietly decoding some other table.

## 8. What this changes, and what it leaves stale

- **`XDATA_0457`, `XDATA_0459`, `XDATA_045B`, `XDATA_045C` and `XDATA_045F`
  gain a note, not a count and not a status.** Each entry's prose named its
  direct writers and was silent about the record seed on top of them. That is
  silence completed, not a false claim retracted — with one exception below.
  Every `static_refs*` value and every `status:` is unchanged, and the new
  source tag is deliberately **not** added: `static_refs*` are `MOV DPTR` counts
  recomputed from the image by `check_register_counts.py`, and adding a
  `code-record` tag would make them read as though records were included in
  them. `xdata-0440-readers.md` §9 already states the mechanism for `0x0440`;
  the same sentence now covers the other five.
- **`XDATA_0457`'s "no writer at all" reading is corrected.** Its entry names
  four sites and the issue reads that as no writer; in fact all four are
  read-modify-writes and therefore do write. What was true is that the entry is
  *silent* about four record seeds. The correction is that silence, and the
  wording it replaces is left visible beside it.
- **`CPU_TEMP` gets one line** in the same terms as §5's: a three-byte CODE
  record stores `0x20` into `0x043E`, and when that table is walked is not
  established. `status: confirmed-working` stands on its cited coretemp
  cross-check, which this neither strengthens nor weakens.
- **No `docs/findings.md` section, and no summary anywhere else.** This file is
  the write-up; `docs/findings/INDEX.md` is regenerated, never hand-edited.
- **No `ec/annotations/xdata-0400-045f-sites.csv` row is added.** That file is
  the verbatim `--csv` output of `trace_xdata_refs.py` and is held to its shape
  by three committed checks — `test_walk_budget_census.py` compares six re-cut
  tables against a pinned baseline SHA *and* asserts `len(old) == len(after)`,
  `walk_budget_census.py --check` reproduces it from those tables, and
  `test_dptr_rebuild_forms.py` lists it. The records therefore join the page
  through its per-address table, which is narrower than folding them into a
  `MOV DPTR` site census would have been and is the right home for a
  seven-table method.
- **`ec/annotations/ghidra-functions.csv` is untouched.** Its `bank1,A530` row
  already enumerates all seven call sites and the table bases; extending it to
  name the page destinations is a one-row nicety, left out to keep shared-file
  surface down.
- **Seven plate comments in `ec/decompiled/` are already stale** for the reason
  §11 of the page document gives, and §5's four-way `0x0457` seed makes one of
  them staler. `build_ec_decompile.py --self-test` is the check for the "no
  entry" idiom; the fix is in the annotation CSV, and the next export that is
  meant to carry the renames carries them.

## 9. What this does not reach

Stated rather than hidden, in the same form `xdata-0440-readers.md` §7.6 uses
for its own residual:

1. **The 15 unresolved call sites of §7.6** — the largest remaining hole in the
   writer hunt, and the only one that could still turn up a writer this class
   does not name. Their DPTR comes from a table read, a loop or a subroutine.
2. **The seven parameterised "zero N bytes at DPTR" helpers** of §7.5, whose
   callers are not searched. A caller handing one of them `0x0440` is invisible
   here; they are the natural next input, and `HELPERS` is shaped to take them.
3. **Seeding the routines the call sites sit in** — `0x8354`, the routine
   holding `0x82C9` and `0x82FD`, and the `0xF326`-`0xF350` stubs. That needs
   `--mode rebuild-project` and a 7 MB database change that cannot merge
   alongside anything else, and it is what would establish *when* these tables
   are walked. Issue #175 owns it; this change names them by address.
4. **Whether a seeded value is ever the value observed.** A live read of
   `0x043E`, `0x0457` or `0x045F` at reset beside a real reading is a human at
   the machine. The procedure is already written down for these bytes and
   re-preparing it is not progress, so nothing further is prepared here.

**Excluded, in the tool's own terms:** a table walked by a helper nobody
enumerated in `HELPERS`; a call site whose base or count is not a literal
immediately before the `lcall`; a record read past the end of the mapped
region. Each is a refusal the tool reports rather than a result it reports, and
a zero anywhere in `xdata-code-table-records.csv` means "not found by this
method" — `ec/annotations/registers.yaml`'s own caveat, and
`docs/findings.md` §4c's retracted case of reading such a zero as absence.