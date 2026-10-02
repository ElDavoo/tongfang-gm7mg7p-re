# Five `pd` dispatch call sites whose tables the annotation rows read as instructions (issue #643)

Seven committed `pd` listings reach one of the PD image's two code-table
dispatchers: `pd 133F`, `pd 0x1EFE`, `pd 0x4C27`, `pd 0xA339`, `pd ADAB`,
`pd C873` and `pd CB2A`. Each has its table starting at the address the `lcall`
returns to, because both dispatchers pop the return address into DPTR before
their first `MOVC`. Two of the seven rows said so. The other five described the
bytes after the `lcall` in five different ways: three as a call-and-return tail
(`pd 133F`, `pd 0x1EFE`, `pd ADAB`), one as a carry/rotate sequence ending in a
compare (`pd C873`), and one not at all (`pd 0x4C27`). This write-up is what the
five now say, where each figure comes from, and what is deliberately still
unsaid.

**Nothing here is a behavioural claim, and no live test ran.** Every figure is a
static decode of committed firmware against a committed tool, and two of the
seven are also walked by hand from the committed `.asm` listings. No hardware is
reachable from a GitHub-hosted runner, no handler of any table here is claimed
to execute, and nothing in `ec/annotations/registers.yaml` moves — these are
CODE-space tables in the PD image, and reading them adds no XDATA site.

---

## The framing, from the dispatcher's own body

`ec/annotations/pd-0x38-consumers.md` §5.1 carries the complete disassembly of
`0x119C..0x11C1`, and it settles the framing on its own:

```text
119C  d083 d082 f8           POP DPH; POP DPL; MOV R0,A
11A1  e4 93 7012            CLR A; MOVC A,@A+DPTR; JNZ 11B7
11A5  7401 93 700d          MOV A,#01; MOVC A,@A+DPTR; JNZ 11B7
11AA  a3 a3                INC DPTR; INC DPTR
11AC  93 f8 7401 93         MOVC A,@A+DPTR; MOV R0,A; MOV A,#01; MOVC A,@A+DPTR
11B1  f582 8883 e4 73       MOV DPL,A; MOV DPH,R0; CLR A; JMP @A+DPTR
11B7  7402 93 68 60ef       MOV A,#02; MOVC A,@A+DPTR; XRL A,R0; JZ 11AC
11BD  a3 a3 a3 80df         INC DPTR; INC DPTR; INC DPTR; SJMP 11A1
```

Three things follow, and every corrected row rests on the first of them.

1. **The table starts at the return address.** The two entry pops consume the
   address the `lcall` pushed, so DPTR already points at the table when the
   first `MOVC` runs. There is no prologue in the caller and no header in the
   table: the first record begins at the byte after the `lcall`.
2. **Neither dispatcher returns.** The only exit of `0x119C` is `JMP @A+DPTR` at
   `0x11B1`, and `pd CB2A`'s row already records that `0x11C2`'s only exit is the
   indirect jump at `0x11DC`. Nothing after the `lcall` is this function's
   continuation, so a `ret`, a `dec R6` or an `ajmp` rendered there is a byte of
   a record that a linear disassembler read as an instruction.
3. **A record is target, target, key.** A nonzero target pair is followed by a
   third byte the reader compares against the selector in A; an all-zero target
   pair is the terminator, and the two bytes after it are the default target.
   Three bytes per entry under `0x119C`; `0x11C2` walks four, which is where
   `pd CB2A` differs and why its figures are quoted under that tool's own
   `reader_stride`.

The layout is a decode under one reader's rule, not a trace of anything: the
reader at `0x119C` is a routine in this image like any other, and a different
reading of its body would give a different table. That is the caveat
`ec/tools/pd_index_tables.py` carries, and it is repeated in each corrected row
rather than only here.

## The seven sites, and where each figure comes from

Every row below is the `pd-index-table-spans.csv` row for that site's `lcall`
address, named rather than cited by line so a regeneration is what invalidates
it. The framing itself — where the table begins — is re-derivable from the
`.asm` listing alone, because the `lcall` is three bytes and the dispatcher's
first two instructions are the pops. The entry count, the key range, the default
and the last byte are not, for five of the seven; see the paragraph under the
table. Where the `.asm` *does* reach, it is quoted below.

| `pd` row | `lcall` | dispatcher | table at | entries | keys | default | last byte |
|---|---|---|---|---|---|---|---|
| `pd 133F` | `0x136C` | `0x119C` | `0x136F` | 20 | `0x01`–`0x16`, `0x0E`/`0x0F` absent | `0x1DE6` | `0x13AE` |
| `pd 0x1EFE` | `0x1F2D` | `0x119C` | `0x1F30` | 8 | `0x01`–`0x07`, `0x0F` | `0x26D6` | `0x1F4B` |
| `pd 0x4C27` | `0x4C35` | `0x119C` | `0x4C38` | 11 | `0x00`–`0x0C`, `0x07`/`0x08` absent | `0x4FE1` | `0x4C5C` |
| `pd ADAB` | `0xADE6` | `0x119C` | `0xADE9` | 15 | `0x01`–`0x0F` | `0xAE7A` | `0xAE19` |
| `pd C873` | `0xC879` | `0x119C` | `0xC87C` | 8 | `0x22`–`0x99`, stride `0x11` | `0xC900` | `0xC897` |
| `pd 0xA339` | `0xA34B` | `0x119C` | `0xA34E` | 7 | `0x00`–`0x11` | `0xA435` | `0xA366` |
| `pd CB2A` | `0xCB4A` | `0x11C2` | `0xCB4D` | 4, stride 4 | `0x01`–`0xCB` | `0xCB76` | `0xCB5C` |

The last two rows were already framed and are not changed by this write-up; they
are here so the enumeration is the whole set rather than the part that moved.
`pd CB2A`'s row is `well_formed=no` under the census, and that is a statement
about the main EC's three-byte rule being applied to a four-byte table, not a
verdict about the table — the wording `pd_index_tables.py` gives that column.

Every census site that falls inside a committed `pd` listing is in that table;
the census's other rows name sites that no listing covers, so no annotation row
describes them and none is corrected here.

Of the seven listings, only `C873.asm` and `A339.asm` carry a table's whole
span. `133F.asm` stops at `0x1371`, `1EFE.asm` at `0x1F32`, `ADAB.asm` at
`0xADEB` and `CB2A.asm` at `0xCB4F` — all four stop mid-table — and
`4C27.asm` skips a range in the middle of its own (below). So for five of the
seven the entry count, the key range, the default and the last byte are not
re-derivable from the listing at all; they are cited from the census row, and
the two listings that do close their table are the cross-check.

## Two hand-walks, as a cross-check that does not go through the census

A generated CSV that a comment cites is only as good as the generator, so two of
the tables were also walked by hand from the listing bytes. Both agree with the
table above exactly.

**`pd 0x4C27`, at `0x4C38`.** Striding three into `4c 5d 00 / 4c 92 01 / 4c 9e
02 / 4d 15 …` gives eleven records, then `00 00`, then the default pair, ending
at `0x4C5C`. That is the byte dump `ec/annotations/pd-0x38-consumers.md` §5.1
already carries for this range, written out there in full:

```text
4c5d00 4c9201 4c9e02 4d1503 4d2c04 4d5f05
4d6f06 4e8409 4f5c0a 4fc20b 4fd60c 0000 4fe1
```

which is also where the `0x07`/`0x08` gap in the key range comes from: the keys
run `00 01 02 03 04 05 06 09 0a 0b 0c`. The listing **skips `0x4C43`–`0x4D14`**,
because `0x4C40` decodes as `ljmp 0x4D15` and the disassembler follows it — so
the fourth record's key byte is not in `4C27.asm` at all, and the hand-walk
alone cannot finish this table. Only the image can, which is why the entry count
and the last byte are cited from the census and the walk is the cross-check
rather than the source.

**`pd C873`, at `0xC87C`.** Striding three into `c8 a0 22 / c8 98 33 / c8 c7 44
/ c8 b4 55 / c8 c7 66 / c8 a8 77 / c8 da 88 / c8 f0 99`, then `00 00 c9 00`:
eight keys spaced `0x11` apart, a terminator, default `0xC900`. Of the two, this
is the one where the hand-walk closes the table, and it is the site where the old
row was most confident, so it is worth being explicit about what the old reading
was made of. The row said the function "runs a carry/rotate sequence over R5, R0,
@R1 and direct byte 0x77 … ending in a compare of A against `0x55`", and the
listing renders `b4 55 c8` at `0xC886` as exactly that compare. Those three
bytes are the low target byte of the record keyed `0x55`, its key byte, and the
high target byte of the record keyed `0x66`. The compare is a key byte that
happens to decode as an opcode — which is why the row's name,
`compare_55_then_mark_0819`, names the decoder's accident rather than the code.

## Where the table stops and code resumes, which is a different address

A table ending is not the same as "everything after the `lcall` is data", and
getting that backwards produces a new falsehood in the other direction. The
census's third well-formedness check is the guard: the byte after the table must
be one of the table's own targets, and it passes at every site in the table
above. So each corrected row names **where code resumes**, and that address is a
record's target:

| `pd` row | last table byte | the byte after it | which record it is |
|---|---|---|---|
| `pd 133F` | `0x13AE` | `0x13AF` | the record keyed `0x02` |
| `pd 0x1EFE` | `0x1F4B` | `0x1F4C` | the record keyed `0x01` |
| `pd 0x4C27` | `0x4C5C` | `0x4C5D` | the record keyed `0x00` |
| `pd ADAB` | `0xAE19` | `0xAE1A` | the record keyed `0x03` |
| `pd C873` | `0xC897` | `0xC898` | the record keyed `0x33` |

`pd C873` is the one that needs this stated, because its listing shows real code
immediately past the table: `0xC898` is `lcall 0x96FB`, then `movx A,@DPTR`,
`orl A,#0x08`, `movx @DPTR,A`, `ret`. That is a handler body, reached when the
selector matches `0x33` — not the `0xC873` body's "on a match" arm, which is what
the old row said it was. The correction stops at the table's last byte for that
reason.

`pd 0xA339` holds at `0xA367` the same way, and it is left unchanged: its row
already framed the bytes as not-a-fall-through, so it claims nothing about them
being this function's instructions. Where its boundary is named is a separate
imprecision, recorded under "Left open" below rather than fixed here.

## What changed, and what the old text claimed

The five rows were corrected by replacement, not by a correction chain: the
annotation CSV is a generated layer with one cell per fact, and a chain there
would be read by nobody. The wrong readings are recorded here instead, so a
reader who remembers the old text can find what replaced it.

- **`pd 133F`** ended `… passes it to 0x119C, decrements R6, increments R1 and
  jumps into the 32-bit XDATA adder at 0x1013`. The bytes at `0x136F` are
  `1e 09 01`, one record: target `0x1E09`, key `0x01`. `0x1013` is
  `paged_target(0x01, 0x13, 0x1371)` — the disassembler's `ajmp` target for the
  two bytes `01 13` it reads at `0x1371`, which are record 1's key byte and
  record 2's high target byte. **No record in that table targets `0x1013`, and
  neither does its default**, so the corrected row does not repeat it: it says
  what the bytes are.
- **`pd ADAB`** ended `… loads R6 with 0x7A and tail-jumps to 0xA8AE`. The bytes
  at `0xADE9` are `ae 7a 01` — target `0xAE7A`, key `0x01` — so `ae 7a` is one
  8051 `MOV R6,direct` whose operand is the record's own target, and the `01`
  that became its `ajmp` opcode is the key byte. The shape of the error is
  worth keeping in view: `0xAE7A` is also the table's **default** and the target
  of eleven of the fifteen records, so the two bytes the disassembler read as an
  opcode and an operand really are a target, and the byte it read as the next
  instruction really is a key. Nothing in that reading looks wrong, which is what
  makes it worth recording rather than just correcting.
- **`pd C873`** is described above.
- **`pd 0x1EFE`** said the fall-through at `0x1F29` "reads XDATA 0x0805,
  dispatches it through 0x119C, decrements R7, ORs the result with R4 and
  transfers to 0x1820 with `ajmp`". The `dec R7` at `0x1F30` and the `orl A,R4`
  at `0x1F31` are the record `1f 4c 01` — target `0x1F4C`, key `0x01` — and
  `0x1820` is `paged_target(0x01, 0x20, 0x1F32)` built out of that record's key
  byte and record 2's high target byte.
- **`pd 0x4C27`** claimed no fall-through and was not wrong about that. What it
  lacked was the sentence: the row cited
  `ec/annotations/pd-0x38-consumers.md` as its evidence and left that document's
  §5.1 reading — "Thus the bytes at `4C38..4C5C` are data" — to the reader. It
  now carries the framing and the figures itself.

### The one correction to the issue's own body

The issue says `pd 0x1EFE` "has no row at all" and routes it to #489. It has one,
at `ec/annotations/ghidra-functions.csv`, and it described the post-`lcall`
bytes as code — the `1f 4c 01` at `0x1F30` read as `dec R7` / `orl A,R4` /
`ajmp`, exactly as above. Nothing was added and nothing was deferred; an
existing row was corrected with the other four. `ec/tools/test_pd_call_site_table_framing.py`
holds that row's existence as a case of its own, so a later reader does not
re-route it to #489 on the strength of the issue text.

The issue's other reading of `pd 0x1EFE` is right and the old row is what is
wrong: the table at `0x1F30` is `1f 4c 01`, three bytes, not the four
`1f 4c 01 20`. The fourth byte is record 2's high target byte.

## What these figures are not

- **A decode under one rule, not a trace.** Every entry count, key range,
  default and last byte above is what `decode_index_table.py`'s three-byte
  layout produces when pointed at the image, imported rather than reimplemented
  by `pd_index_tables.py` precisely so the two readings cannot drift. A different
  reading of `0x119C`'s body would give a different table; nothing here claims
  this one is the only correct reading, only that it is the one the committed
  tool makes and the `.asm` bytes do not contradict.
- **No handler is claimed to execute.** Nothing here says which selector values
  occur at run time, or that any particular target is reached. `pd 0x4C27`'s
  reachability question is untouched by this reading and its row still says so.
- **A weaker region check than it reads.** `malformed()` requires every target
  and the default to resolve inside the caller's own region. In the main EC that
  means *banked*; the PD image is flat, so the same test only asks for a
  `0x0000`–`0xFFFF` CODE address. The other two checks — cases strictly
  ascending, and the byte after the table being one of its own targets — are
  unchanged, and it is the third of those that carries the table-end figures
  above.
- **Not a `registers.yaml` change.** These are CODE-space tables: every target
  in them resolves as an address in the PD image's own space, which is what the
  census's region check tests and the only thing it tests in a flat image. No
  `status:` moves and no direct-`MOV DPTR` site is added by this reading.

## Left open

- **`pd C873`'s name.** `compare_55_then_mark_0819` describes the decoder's
  accident, as §"Two hand-walks" above sets out. Renaming it moves `name_basis`
  and the named-annotation counters, and is not this issue's work.
- **`pd 0xA339`'s boundary.** Its row says the bytes "between `0xA34E` and
  `0xA36D`" are not a fall-through path, and places the decompile's calls to
  `0xA5B3` and `0xE757` inside that region. The table's last byte is `0xA366`,
  so `0xA367` (`acall 0xA5B3`), `0xA36A` (`lcall 0xE757`) and `0xA36D`
  (`ljmp 0xA435`) are past it: the first is the record keyed `0x00`'s target
  and the rest are that handler's continuation and the default's. The row does
  not claim those bytes are this function's instructions, so it satisfies the
  issue's Done criterion and is left alone here — but its range is six bytes
  too wide, and narrowing it is a separate edit.
- **`pd 0x4C27`'s reachability.** The row already declines to establish who
  reaches `0x4C27`, whether reset reaches it, or whether any selector occurs.
  Reading its table changes none of that.
- **What any of these tables selects.** Nothing here says what a handler at
  `0x1E09`, `0x1F4C`, `0x4C5D`, `0xAE7A` or `0xC8A0` does. `pd 0xADAB`'s
  eleven-of-fifteen repetition is recorded as a fact about the table's shape and
  is not interpreted here.

## Reproducing this

```console
$ python3 ec/tools/pd_index_tables.py
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ec --check
$ python3 -m unittest discover -s ec/tools -p test_pd_call_site_table_framing.py
```

The first reproduces the seven rows the corrected comments cite; the second
confirms every committed `.c` — the five regenerated headers among them —
against its digest; the third is the suite that holds each row to those figures,
and includes the negative controls that fail on the pre-change CSV.