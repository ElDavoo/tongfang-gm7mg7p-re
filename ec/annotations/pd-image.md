# The `ITE8850-PD` image: layout, vectors, strings, dispatch, provenance

**One consolidated map of the 64 KiB at file `0x20000`-`0x2FFFF` of
`ec/firmware/GMxMGxx_11.800`.** It is a self-contained 8051 program that
shares the EC firmware's flash dump, and every address on this page is an
address *in that program* — none of it is evidence about the EC's XDATA at the
same number. `lightbar-bat-flow.md` §2 carries the four independent facts that
make it a separate program (its identity strings, its own vector table, its own
C startup stub, no Keil bank-switch stubs) and that argument is canonical
there; this page cross-references it and does not re-derive it.

What this page adds: the **layout**, a **complete** vector table where §2's
table stops at five rows, the **string pool** with a reference census over all
43 of its candidates, the **host-facing dispatch surface** as far as static
evidence reaches, and the **provenance** answer — which is positive, and
settles the "BIOS, EC update, or both" question issue #26 asked. It does not
settle how many dies that involves; §5.2 says which way that one goes.

Every figure below is re-derived from the committed bytes by
`../tools/pd_image_census.py`, and `--check` holds the two to each other. The
machine-readable form of the string census is
[`pd-image-strings.csv`](pd-image-strings.csv). The per-issue write-up, and
what stays open, is
[`../../docs/findings/pd-image-census.md`](../../docs/findings/pd-image-census.md).

## 0. Reproducing it

Nothing here needs Ghidra, a network, or hardware.

```console
$ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1
$ python3 ec/tools/pd_image_census.py
$ python3 ec/tools/pd_image_census.py --check
$ python3 ec/tools/test_pd_image_census.py
```

The tool is **not registered in any gate.** `.github/scripts/agent-gates.sh`
is a pipeline file and this branch's token has no `workflow` scope, so
registering it is a human's change; the tool is runnable and cited standalone,
which is what `docs/findings.md` §88 records for
`test_check_history_checkouts_run.py` and the reason is the same one. It does
run under the gate's `python3 syntax` check, which only proves it compiles.

The section transcripts below are real `r2 -a 8051` output (radare2 5.5.0), and
they are the independent witness for the load-bearing ones: §2's table, §2.1's
two routines and §3's string offsets are all readable with `dd` and `r2` and
nothing in this repository. The two digests need `sha256sum` and §5 needs the
zip inflated — which is the point of §5.1, not a limitation of the transcript.

## 1. Layout

| | |
|---|---|
| file extent | `0x20000`-`0x2FFFF`, 64 KiB |
| sha256 | `30fe7fb8174535d2846e77ca837239a91548748e616cc6f061cf151ee230f970` |
| in use | `0x0000`-`0xF7B7` |
| erased | `0xF7B8`-`0xFFFF` (2,120 bytes) |
| `0xFF` bytes in total | 3,705 |
| committed listings | 542 (`ec/decompiled/pd/*.asm`), 0 overlapping addresses |
| annotated rows | 542 (`../annotations/ghidra-functions.csv`, `scope` = `pd`) |

The single erased run in the region is the tail. There is no other 64-byte
`0xFF` gap anywhere in it, so the image is packed: Keil/SDCC constant pools sit
between functions rather than being collected at the end, which is why the
string runs of §3 are scattered rather than one block.

**What this is not.** It is not a third CODE bank of the EC. §2's four facts
and `ec/README.md`'s `## Layout` both say so; `find_banks.py` finds zero
callers for banks 2 and 3, and the region's `ljmp`/`lcall` targets spread flat
across the whole 64 KiB rather than clustering in a `0x8000` window. Its own
64 KiB address space means its XDATA map is its own, and a `MOV DPTR,#0x07E2`
in here says nothing about `0x07E2` in the EC — which is the whole of
`docs/findings.md` §3a, and the reason this page never quotes an EC register
name for a PD address.

## 2. Vector table — six entries, not five

`lightbar-bat-flow.md` §2's table stops at five rows. It is not wrong; it
stops. `discover_vector_table()` in `../tools/build_ec_decompile.py` finds six
slots on these bytes, and `../ghidra/README.md` records the same. The sixth is
the serial vector at `0x23`, and the rest of the table's 8-byte slots —
`0x26`-`0x3F`, including the `0x2B` slot a seventh entry would have taken — are
erased.

**The geometry is not the textbook one, and reading it as the textbook one is
the error worth naming.** The reset entry is at `0x00` and each interrupt
entry is at `0x03 + n * 8` — the 3-byte `LJMP` followed by five `0xFF`. An
8-aligned walk from `0x00` reads `0x00`, `0x08`, `0x10`, … and on this image
finds an `LJMP` at `0x00` and **nothing at the other five offsets**, because
they are the padding. That yields a one-entry table which is a plausible-looking
answer to "what is in this image's vector table", and the failure would read as
"this firmware has no handlers there" rather than as a wrong tool.
`pd_image_census.py` walks the table instead, and
`test_eight_aligning_the_whole_table_reads_the_wrong_bytes` pins the wrong
answer so a future edit that "fixed" the walk to be 8-aligned goes red.

```console
$ r2 -a 8051 -e scr.color=0 -q -c 'p8 0x2c @ 0' /tmp/pd.bin
020500020056ffffffffff020094ffffffffff0200b2ffffffffff0200f0ffffffffffff02010effffffffffff
$ r2 -a 8051 -e scr.color=0 -q -c 'pD 0x2c @ 0' /tmp/pd.bin
        ┌─< 0x00000000      020500         ljmp 0x0500
       ┌──< 0x00000003      020056         ljmp 0x0056
       ││   0x00000006      ff             mov r7, a
       ...
      ┌───< 0x0000000b      020094         ljmp 0x0094
       ...
     ┌────< 0x00000013      0200b2         ljmp 0x00b2
       ...
    ┌─────< 0x0000001b      0200f0         ljmp 0x00f0
       ...
   ┌──────< 0x00000023      02010e         ljmp 0x010e
       ││││││  0x00000026      ff             mov r7, a
```

(r2's graph column is left as printed; the 44 bytes are the whole table plus
its padding. The reset target's C startup stub is §2's fact 3 and is not
repeated here.)

| entry | 8051 vector | target | target is |
|---|---|---|---|
| `0x00` | reset | `0x0500` | `c_startup_idata_clear` — the Keil/SDCC IDATA clear |
| `0x03` | external interrupt 0 | `0x0056` | `vector_wrapper_dp_0151` |
| `0x0B` | timer 0 | `0x0094` | `vector_wrapper_dp_0154` |
| `0x13` | external interrupt 1 | `0x00B2` | `vector_wrapper_dp_0157` |
| `0x1B` | timer 1 | `0x00F0` | `vector_wrapper_dp_015a` |
| `0x23` | serial port | `0x010E` | `vector_wrapper_dp_015d` |

The 8051 vector *names* are the architectural names for those offsets, not
anything this program says about them — the five interrupt vectors are
interchangeable in the architecture, and nothing in the image distinguishes
which physical source is on which.

### 2.1 The five interrupt entries are one wrapper each, and the CODE address is the selector

This is the part of the vector table that says something, and it is a
**positive** referrer result — the counterpart to the null in §3.

**The selector is a CODE address, and this repository's own annotations already
said so** — `../annotations/ghidra-functions.csv`'s five `vector_wrapper_dp_…`
rows each read "loads DPTR with the CODE address `0x0151`" (and `0x0050`'s reads
"reads three CODE bytes at DPTR into R3, R2 and R1"). An earlier draft of this
page carried the same constants as **XDATA** addresses, on the reasoning that
`pd-base-strides.csv` files them among its XDATA bases; that reasoning is wrong,
because a `MOV DPTR` immediate does not name a space — on an 8051 `MOVC`
(`0x93`) reads CODE, `MOVX` reads XDATA, and the path from `0x10F1` contains no
`MOVX` at all. The annotations were right and the page was wrong. The
correction is recorded here rather than made silently because the wrong label
propagated into
[`../../docs/hardware-tests/pd-controller-enumeration.md`](../../docs/hardware-tests/pd-controller-enumeration.md),
where it sent a human to read the EC's memory window at a CODE address.

The five wrappers share a shape but come in two forms, not one routine with a
constant swapped: three are long-form (`0x0056`, `0x00B2`, `0x010E`, which do
`mov psw,#0x00` and then push R0-R7 explicitly) and two are short-form
(`0x0094`, `0x00F0`, which do `mov psw,#0x10` and push no R0-R7). Within a form
the bytes are identical apart from the three DPTR immediate bytes; what
separates the forms is PSW and the push set. All five load DPTR with a
per-vector **CODE** address, `lcall 0x0050`, restore, `reti`:

| vector | `mov dptr,#…` | `lcall` | pushes before the call | `mov psw,#…` |
|---|---|---|---|---|
| `0x03` | `0x0151` | `0x0050` | 13 | `0x00` |
| `0x0B` | `0x0154` | `0x0050` | 5 | `0x10` |
| `0x13` | `0x0157` | `0x0050` | 13 | `0x00` |
| `0x1B` | `0x015A` | `0x0050` | 5 | `0x10` |
| `0x23` | `0x015D` | `0x0050` | 13 | `0x00` |

The shared body is `0x0050 call_10f1_then_jmp_1229`, and the two routines it
reaches are already named in the annotations CSV:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 'pD 0x10 @ 0x10f1' /tmp/pd.bin
            0x000010f1      e4             clr a
            0x000010f2      93             movc a, @a+dptr
            0x000010f3      fb             mov r3, a
            0x000010f4      7401           mov a, #0x1
            0x000010f6      93             movc a, @a+dptr
            0x000010f7      fa             mov r2, a
            0x000010f8      7402           mov a, #0x2
            0x000010fa      93             movc a, @a+dptr
            0x000010fb      f9             mov r1, a
            0x000010fc      22             ret
$ r2 -a 8051 -e scr.color=0 -q -c 'pD 0x0a @ 0x1229' /tmp/pd.bin
            0x00001229      8a83           mov dph, r2
            0x0000122b      8982           mov dpl, r1
```

**So the vector table is a table.** `0x10F1 read3_code_to_r3r1` reads three
CODE bytes at the CODE address the wrapper loaded, and `0x1229
load_dptr_then_indirect_jump` takes the middle and last of them as a
big-endian 16-bit CODE pointer and jumps there. **The five interrupt handlers
are fixed in the image, in a constant table of five CODE words:**

| vector | 3 CODE bytes read from | the jump target is | that target is |
|---|---|---|---|
| `0x03` | `0x0151`-`0x0153` | the big-endian word at `0x0152`/`0x0153` | `0xA8AE` — a committed entry, `event_dispatch_ff80_ffe0` |
| `0x0B` | `0x0154`-`0x0156` | `0x0155`/`0x0156` | `0xF7AE` — `ret` |
| `0x13` | `0x0157`-`0x0159` | `0x0158`/`0x0159` | `0xF7AF` — `ret` |
| `0x1B` | `0x015A`-`0x015C` | `0x015B`/`0x015C` | `0xF790` — `lcall 0xEFEA` then `ret` |
| `0x23` | `0x015D`-`0x015F` | `0x015E`/`0x015F` | `0xF7B0` — `ret` |

```console
$ xxd -s 0x150 -l 0x10 /tmp/pd.bin
00000150: ffff a8ae fff7 aeff f7af fff7 90ff f7b0  ................
```

The leading byte of each triple is fetched into R3 and is not used by the jump;
it is `0xFF` in all five, which is at least consistent with the compiler
emitting a fixed 3-byte read. Whether it needs three for a reason this image
does not show is **not determined** — the bytes say only that three are read.

**What the five words point at, and how far that is decoded.** `0xA8AE` is a
committed function entry, `event_dispatch_ff80_ffe0` (§4.1's table). The other
four are **not** committed entries — no listing in `ec/decompiled/pd/` starts
at or spans `0xF790`, `0xF7AE`, `0xF7AF` or `0xF7B0`, all four of which fall in
the gaps the committed extents leave inside `0xF78B`-`0xF7B7`. Their raw bytes
are `0xF790` = `12 ef ea 22` and `0xF7AE`/`0xF7AF`/`0xF7B0` = `22`, a bare
`RET`, inside the ten-byte run of `0x22` at `0xF7AE`-`0xF7B7` that ends the
image's used range — the committed `ret_only_f7b2` … `ret_only_f7b7` rows are
the same shape.

**What those four bytes are is now settled, and it is not padding.** The
paragraph above used to end by saying that whether they are "real handlers,
padding, or an artefact of reading a constant pool as code is not determined
here"; the correction is recorded here rather than made silently, because what
replaced it is a positive reading of the same committed bytes. Three of the five
vectors — `0x0B`, `0x13` and `0x23` — are wired to a **`ret`**, and a `ret` ends
a body, so each of those three handlers does nothing and returns. Three pieces
of committed code carry that:

- **A bare `ret` is this convention's spelling of "does nothing", not padding.**
  The chain is fixed by bytes and by nothing else. `0x010E
  vector_wrapper_dp_015d` pushes 13 registers, `mov dptr,#0x015d`, `lcall
  0x0050`, pops 13, `reti` — so a return address is on the stack. `0x0050` is
  `lcall 0x10f1` then `ljmp 0x1229`; the `lcall` pushes, and `0x10f1` ends in a
  `ret`, so the stack is back where the wrapper left it when the `ljmp` runs.
  `0x1229` builds DPTR from R2:R1 and falls through into `0x122D`, whose last
  instruction is `jmp @a+dptr` (`0x73`) and which pushes nothing. **So a
  handler is reached by a jump, and the top of stack on entry is the wrapper's
  return address.** A `ret` there pops exactly that and resumes the wrapper at
  its first `pop`, which unwinds and executes `reti`.
- **The same `0x22` bytes are demonstrably callable.** `0xF7B2`, `0xF7B3`,
  `0xF7B4` and `0xF7B7` are bare-`ret` stubs inside this same run, and
  `ec/decompiled/pd/DA44.asm` and `A8AE.asm` `lcall` them. A `0x22` here is a
  no-op stub that committed code calls. Padding has no caller; that is what
  rules it out here.
- **The run reads as code throughout.** Between `0xF786 tailcall_7b14_with_r7_zero`
  and the erased tail it holds `ljmp` forwarders at `0xF78B`, `0xF79C`, `0xF79F`,
  `0xF7A8` and `0xF7AB`; `lcall`-then-`ret` bodies at `0xF790` (to `0xEFEA`) and
  `0xF798` (to `0xE5EB`); register-setting stubs at `0xF7A2` and `0xF7A5`, which
  return R7 = 2 and R7 = 3; and the ten-byte `0x22` run at `0xF7AE`-`0xF7B7`.
  Three shapes, and the committed `forwarder` rows either side of the gap fix
  the first of them.

**So the positive finding is about the wiring, not only the bytes: of the five
interrupt vectors, `0x03` goes to a dispatcher (`0xA8AE`), `0x1B` goes to a
call into `0xEFEA`, and `0x0B`, `0x13` and `0x23` are wired to no-op returns.**
`0xEFEA` and `0xE5EB` are **not decoded here** and no committed `pd` listing
contains an `lcall` to either; that is *not found by this method* and not
*unreachable* — a byte scan finds two sites for each, one of them the run's own
call, and not one of them is inside a committed listing. A candidate is not a
caller.

`ec/tools/pd_vector_handlers.py` derives every cell of the table above from the
committed image and the committed annotations, and `--check` holds the two to
each other in both directions; the write-up is
[`../../docs/findings/pd-vector-handler-words.md`](../../docs/findings/pd-vector-handler-words.md).

**What is still open, and it is not the four targets.** The five
`vector_wrapper_dp_*` rows' careful "What the `0x015X` table entry selects is not
decoded here" now carry the selection beside the sentence they replace. What is
*not* decoded is `0xEFEA` and `0xE5EB`, which of the physical sources sits on each
vector, and whether the three no-op vectors are ever enabled — the last is a
hardware observation and needs the machine. **One framing question stays open
too**: a linear walk from `0xF78B` reads `inc a` at `0xF78E` and then a `jbc` at
`0xF78F` whose operand bytes are `0xF790`-`0xF791`, so it steps over `0xF790`
rather than landing on it. `0xF790` is an entry on the other reading, because
the `0x1B` vector's word names it and `jmp @a+dptr` lands there. The two
framings cannot both be the executed one and nothing in this image settles
which is; the tool reports the conflict rather than picking a side.

That makes the five CODE addresses a per-vector selector table with a 3-byte
stride, and it ends exactly where `ProtoVer:01.00 ` begins: the last entry's
word is at `0x015E`/`0x015F` and the string is at `0x0160`.
`pd-base-strides.csv` already lists all five addresses among its 448
`unresolved` XDATA bases and says what they are not; that is not contradicted
here, because it is a census of `MOV DPTR` immediates and cannot know which
space the program means by one. Each has exactly **one** `MOV DPTR` site in the
whole region, and it is the wrapper that loads it — so "the vector table
dispatches through a table of CODE constants" is a site count, not a shape
someone saw.

**Why the two wrapper forms differ.** The three that push 13 also zero PSW
before the call and save R0-R7 explicitly; the two that push 5 set PSW to
`0x10`, which selects register bank 1. That is consistent with the short-form
handlers running out of bank 1 and the long-form ones out of bank 0, and
consistent with the two timer vectors being on a different priority — but
"consistent with" is the whole of it. **Which source sits on which vector, and
why the two timer vectors are the short ones, is not established here.**

## 3. String pool, and what references it

43 candidates: every NUL-terminated run of at least 4 printable bytes in the
region. The scan is mechanical and keeps the false ones — `"NaN`, `+INF` and
`-INF` at `0x07CC`/`0x07D1`/`0x07D6` are float-formatting fragments that happen
to be printable, and a filter that guessed which candidates were real would be
the tool making the finding. The `after_nul` column of the CSV is what tells
them apart: a real pool entry starts right after a NUL (`yes`), and one that
starts at the head of a printable run may have swallowed an opcode. `0xA798`
is the worked example — `0xA798` holds `22` (`RET`), which is also the
printable character `"`, so the run head lands one byte before
`Drop Retry Rx-Msg` and the row reads `after_nul=no`.

The four identity strings and the eight protocol strings §2 quotes as evidence
that the region is PD firmware, all at the offsets that file gives:

| region offset | file offset | string | run head |
|---|---|---|---|
| `0x0040` | `0x20040` | `ITE8850-PD` | `0x0040` |
| `0x0160` | `0x20160` | `ProtoVer:01.00 ` (trailing space in the image) | `0x0160` |
| `0x0170` | `0x20170` | `DriverVer:01.00` | `0x0160` |
| `0xA7AB` | `0x2A7AB` | `PR Swap` | `0xA798` |
| `0xA7D5` | `0x2A7D5` | `Error Recovery` | `0xA798` |
| `0xA818` | `0x2A818` | `Set VBUS 5V` | `0xA798` |
| `0xA824` | `0x2A824` | `DR Swap` | `0xA798` |
| `0xA82C` | `0x2A82C` | `FR Swap` | `0xA798` |
| `0xA863` | `0x2A863` | `SRC Negotiate done` | `0xA798` |
| `0xA876` | `0x2A876` | `SINK Negotiate done` | `0xA798` |
| `0xD663` | `0x2D663` | `VCONN On` | `0xD616` |
| `0xE1C0` | `0x2E1C0` | `UsbPdVer:01.00` | `0xE19C` |

```console
$ r2 -a 8051 -e scr.color=0 -q -c 'p8 0x20 @ 0xa799' /tmp/pd.bin
44726f702052657472792052782d4d7367005052205377617000535720526573
$ r2 -a 8051 -e scr.color=0 -q -c 'ps @ 0xa7ab' /tmp/pd.bin
PR Swap
$ r2 -a 8051 -e scr.color=0 -q -c 'p8 0x20 @ 0xd663' /tmp/pd.bin
56434f4e4e204f6e0056434f4e4e204f66660090080deff075f05ea424f9f582
$ r2 -a 8051 -e scr.color=0 -q -c 'p8 0x10 @ 0xe1c0' /tmp/pd.bin
55736250645665723a30312e30300000
```

### 3.1 The reference census: 0 of 43, and what that is not

**Not one of the 43 candidates is named by a `MOV DPTR,#addr` + `MOVC` pair.**
The census reports it as `not found by this method` in every row, and that
wording is load-bearing. Concretely, the tool looked for the 3-byte
`90 hi lo` sequence with `hi:lo` equal to each candidate's address, anywhere in
the 64 KiB, and then for a `MOVC` within four bytes of the site. Not one
candidate is named by such a pair. The two address bytes of the pool head
`0xA799`, read on their own, occur zero times in the 64 KiB in either order.

**This is not evidence the strings are unreachable.** Three ways this program
reaches CODE that a literal `MOV DPTR` scan cannot see, all of them present in
this image:

- **a `DPTR` carried in from a caller**, which is how every `reader` and
  `writer`-typed row in the annotations works.
- **a `DPTR` built arithmetically** — the `base + index * stride` idiom that
  `pd-index-geometry.md` is about, which this image uses heavily (the `0x5E`-
  and `0x67`-strided rows of `pd-base-strides.csv`).
- **a `jmp @a+dptr` through a table whose address is a caller's return
  address.** `0x119C dispatch_code_table`, `0x11C2
  dispatch_code_table_2byte_key` and the unnamed `0x11EF` all pop the return
  address into DPTR and read the caller's inline argument bytes with `movc`, so
  **every table in the program is a literal in the image** — which makes this
  the most plausible remaining route from a literal to a string, and it is
  measured rather than only listed: **9 `lcall 0x119C` sites, 16 `lcall 0x11C2`
  sites and 3 `lcall 0x11EF` sites, and none of those 28 inline tables opens a
  pool entry**, read at each dispatcher's own entry width (3, 4 and 6 bytes
  respectively — why the width is per dispatcher rather than one constant is
  [`pd-code-table-inline-width.md`](../../docs/findings/pd-code-table-inline-width.md)).
  `0x11EF` is named here by address only: it has no row in
  `ghidra-functions.csv`, and §6's sixth item already carries the argument for
  that. *(Corrected, issue #1120: both halves are now false. `0x11EF` has the
  row `pd,11EF,dispatch_code_table_4byte_key_r4r7`, seeded once its 6-byte
  entry layout was established in
  [`pd-reader-entry-layouts.md`](../../docs/findings/pd-reader-entry-layouts.md),
  and §4.1's dispatch table below lists it by that name. "The unnamed `0x11EF`"
  a few lines up predates the row the same way. §6's sixth item is about naming
  `state`-typed rows and is unaffected.)*

So the honest reading is: **the pool is reached by an address this method
cannot compute**, and the way to find it is to watch DPTR rather than to grep
for it. The census's job is to say where a string sits and to rule out the
access forms it can see, so that a later pass starts from a known list instead
of re-scanning. Resolving the reference is follow-up work, and it is named as
such — see §6.

**The `movc`-mediated null is the part of this the census holds, not the part it
concludes.** Both are one code path over the same 43 candidates, and
`test_the_census_finds_a_referrer_when_one_exists` builds a synthetic region
with a planted `mov dptr`/`movc` pair and asserts the same path reports it — so
a method that could only return the null would fail that case rather than pass
this one for the wrong reason.

The one place the two halves of the #181 collision can be told apart is
worth recording: `+INF` at `0x07D1` has **76** `MOV DPTR,#0x07D1` sites and
`-INF` at `0x07D6` has **142**, and not one of them is followed by a `MOVC`.
On an 8051 those two instructions are byte-identical, so those 218 sites are
XDATA references to the numbers `0x07D1` and `0x07D6` that happen to coincide
with two string offsets — a collision, not a reference. That is issue #181's
point, and it is why the CSV keeps `dptr_sites` and `movc_referrers` in
separate columns rather than summing them.

## 4. Host-facing command surface

### 4.1 What is decoded

21 of the 542 `pd`-scoped annotation rows are typed `dispatch`:

| addr | name | addr | name |
|---|---|---|---|
| `0x0180` | `dispatch_r5_write_083b_0300` | `0x4E84` | `dispatch_case_09` |
| `0x0B85` | `index_from_r5_r3_then_jmp_at_0b05` | `0xA339` | `stash_args_dispatch_code_table` |
| `0x0F45` | `read4_ptr_kind_dispatch` | `0xA571` | `dispatch_on_state_07d0` |
| `0x10FD` | `read3_ptr_kind_dispatch` | `0xA8AE` | `event_dispatch_ff80_ffe0` |
| `0x119C` | `dispatch_code_table` | `0xADAB` | `copy_0809_to_080a_then_dispatch_0805` |
| `0x11C2` | `dispatch_code_table_2byte_key` | `0xB24C` | `load_r3_r0_jmp_0f0e` |
| `0x11EF` | `dispatch_code_table_4byte_key_r4r7` | `0xC901` | `dispatch_on_r3_then_add_product_to_0699` |
| `0x133F` | `clear_0807_0808_dispatch_0805` | `0xE458` | `store_07d8_and_dispatch_07da` |
| `0x1EFE` | `gate_0803_then_dispatch_through_code_table` | `0xEF59` | `stage_07d6_call_715e_6faf_tail_e5b3` |
| `0x4C27` | `dispatch_entry` | `0xEF79` | `stage_07d6_call_716c_6faf_tail_e5b3` |
| `0x4D6F` | `dispatch_case_06` | | |

Three of those — `0x0F45`, `0x10FD` and `0xB24C` — dispatch on a *pointer
kind* register (R3 = 1 / 0 / `0xFE` / default), which selects XDATA versus
internal RAM versus CODE for a load. They are dispatchers and they are not
host-facing, and a count of "21 dispatch routines" that did not say which
would be a number without a referent.

### 4.2 The XDATA block a host would touch

| XDATA | `MOV DPTR` sites | note |
|---|---|---|
| `0xFF80` | 5 | the event word `0xA8AE event_dispatch_ff80_ffe0` dispatches on |
| `0xFFE0` | 6 | |
| `0xFFE1` | 4 | |
| `0xFFE2` | 4 | ends at `0x10` per that annotation |
| `0xFFE3` | 0 | **not found by this method** |
| `0xFFD0` | 2 | |
| `0xFFD1` | 0 | **not found by this method** |
| `0xFFD5` | 2 | |

**What this is.** A count of how often this program *names* an XDATA address.
`trace_xdata_refs.py` is the tool that says what it does with it — direction,
width, whether the site hands DPTR to a subroutine — and it is the right one
for that. What the table does **not** say is that `0xFFE0`-`0xFFE2` is an
I2C/SMBus or EC-mailbox register block, that any of it is writable from the
host, or that it is the only host-facing block. Those three addresses are in
the census because `0xA8AE`'s committed annotation already points at them; the
search was for the ones this repository had already flagged, and it is a
seeded search, not an exhaustive one.

**What the driver-relevant question therefore looks like answered, and doesn't.**
Issue #26 asked for an I2C/SMBus or EC-mailbox dispatch table, and said that
table is the piece that could eventually matter to a driver. Static evidence
here gives: a 16-bit XDATA address space with a dense compiler-allocated block
around `0x0800`-`0x0AFF` and an SFR-ish page at `0xFF00`-`0xFFFF`; an event
word at `0xFF80`; a five-entry CODE pointer table at `0x0151` (§2.1); and no
identified wire protocol. **No register in `0xFFE0`-`0xFFE2` is named, and
none is claimed to be.** Whether a Linux driver could talk to this program at
all depends on where it runs — which is §5's open question and a hardware
observation.

## 5. Provenance: **both**, and the EC update is the one that matters

`vendor/bios-1.09/BIOS_1.09.zip` is a stock AMI kit: `EFI/boot/bootX64.efi`,
`GM7MG7P/ifux64.efi` (ITE's EC updater), `AfuEfix64.efi` (the SPI writer),
`AMIDEEFIx64.EFI`, the payloads, and `GM7MG7P/ecflash.nsh`.

**`grep -rla 'ITE8850-PD' vendor/` returns nothing, and that null is an
artefact.** Every member of the zip large enough to hold the marker is DEFLATE,
so the bytes are not in the container a reader greps — the string is in the
*inflated* members. (The one member stored uncompressed is
`GM7MG7P/ecflash.nsh`, 29 bytes of plaintext, which does not contain it
either.) A compression artefact read as an absence is the failure
`docs/findings.md` §4 records twice, in two different directions, so it is
worth the sentence. Inflating the members:

| member | result |
|---|---|
| `GM7MG7P/GMxMGxx_11.800` | carries the region at `0x20000` and the marker at `0x20040`; **byte-identical** to the committed `ec/firmware/GMxMGxx_11.800` (both sha256 `158d1c64…`) |
| `GM7MG7P/GMxMGxxN109A08.ROM` (13 MiB SPI image) | **five** byte-identical copies of the 64 KiB region (each sha256 `30fe7fb8…`), at `0x020000`, `0x45CA2C`, `0x49CA4C`, `0x4DCA6C`, `0x51CA8C`; and the whole 256 KiB EC image, **byte-identical, 0 differing bytes**, at `0x43CA2C` |
| the other six members | the marker is **not found by this method** — read, not asserted absent, by the same inflation |

The container holds **8** non-empty members (`prov_zip_members`) and the table
names two of them, so the last row is the remaining **6**
(`prov_zip_other_members`). Both numbers are derived from `zipfile`'s
`infolist()` and pinned, because a count written only in prose is a count that
drifts: this page said seven until the tool measured it.

`ecflash.nsh` is 29 bytes, read from the zip rather than transcribed here:

```console
$ python3 -c "import zipfile;print(zipfile.ZipFile('vendor/bios-1.09/BIOS_1.09.zip').read('GM7MG7P/ecflash.nsh'))"
b'IFUX64.efi GMxMGxx_11.800 0 1'
```

`IFUX64.efi <file> 0 1` is one write of the whole 256 KiB image, `0x20000`
region included. **So the answer to issue #26's "BIOS, EC update, or both" is
both, and the route that matters is the EC update.**

### 5.1 The comparison that gives the wrong answer, and why

Comparing the ROM's **first** 256 KiB against the `.800` reports **82,281**
differing bytes out of 262,144 and looks like an older EC revision. Both
readings are wrong, and the wrongness is structural: `0x00000`-`0x3FFFF` of a
13 MiB SPI image is the BIOS region, which has no reason to resemble the EC
firmware. The comparison to make is the one at `0x43CA2C`, and it is 0
differing bytes. Recorded here rather than left out because the failure mode is
specific and repeatable: the wrong comparison produces a *large* number rather
than an obviously-broken one, and "the ROM ships a different EC revision" is a
conclusion that would survive into a write-up.

The five region copies sit at `0x020000` and then at a `0x40020` stride from
`0x45CA2C`, and the copy at `0x020000` is byte-identical to the one at
`0x43CA2C + 0x20000`. So the PD region appears once in the BIOS-region area of
the ROM and four more times alongside the embedded EC image; **which of the
five a flash tool writes, and whether all five are live, is not determined
here** — that is a question about the SPI layout's descriptor table, not about
the bytes.

### 5.2 What this does and does not settle about "one chip or two"

`lightbar-bat-flow.md` §2's last paragraph leaves it open: "whether that image
runs on a physically separate PD controller or is a payload the EC hands off is
*not* determined here." That is still true, and the provenance result narrows
it without settling it:

- **It does narrow the EC-hands-off-a-payload story.** A single 256 KiB write
  that updates the EC firmware and the PD firmware together is consistent with
  a shared SPI flash, which is what a handoff payload on a *different* device
  would not be.
- **It does not establish how many dies are involved.** One SPI flash holding
  two images is compatible with one die running both programs, with two dies
  behind one flash, and with a die that boots one image and hands the other to
  a second part over a link this evidence does not name. Static bytes cannot
  separate those.

The topology question is a hardware observation, and the procedure for it is
[`../../docs/hardware-tests/pd-controller-enumeration.md`](../../docs/hardware-tests/pd-controller-enumeration.md).
**It has not been run**, nothing in this repository records a live read of
USB-C or Type-C state, and no sentence here should be read as one.

## 6. What is not established

Stated as a list, because each item is a follow-up and a reader who cannot
tell which sentences are load-bearing will over-read the ones that are.

1. **How the string pool is reached.** §3.1: not by a literal `MOV DPTR` +
   `MOVC`, and not by a table this census found. The lead is to watch DPTR
   writes rather than to grep for the addresses.
2. **Whether `0xFFE0`-`0xFFE2` is a host-facing register block**, and if so
   what protocol carries it. §4.2 names the addresses and nothing else.
3. **Which physical source drives each of the five interrupt vectors**, why the
   two timer vectors are the short-form wrappers, and whether the three no-op
   vectors (`0x0B`, `0x13`, `0x23`) are ever enabled. §2.1 reads all five jump
   targets; what is left is which source drives each, and the last of those
   three is a hardware observation that needs the machine.
4. **The five region copies in the SPI image**: which one a flash tool writes,
   and whether the descriptor table makes the other four live. §5.1.
5. **Whether the PD program runs on a die of its own.** §5.2, and it needs
   the machine.
6. **The state names as a symbol set.** The `state`-typed rows in the
   annotations CSV name PD state by XDATA address (`0x07D0`-`0x07D8`) rather
   than by the protocol state the strings name. Naming the routines after the
   protocol states is the obvious next step, and it is deliberately *not* done
   here: a `ghidra-functions.csv` row needs a `name_basis` the CSV's
   vocabulary accepts, and none of the string-derived anchors is anchored to
   the referring routine yet, because §3.1 has not found the referrers. Doing
   it now would be a rename with no evidence behind it, and a rename churns
   `ec/decompiled/pd/*.c` paths across 542 functions.

## 7. Pinned figures

`pd_image_census.py --check` regenerates this block's values from the committed
bytes and exits non-zero on any difference, in both directions — a figure the
page has and the tool does not derive is a failure as much as one it derives
and the page got wrong. **The tool derives; this block records.** A mismatch
means one of two things, and the message says which: a figure the page has
moved is a page edit, and a figure the tool stopped producing is a tool
regression. Fixing the tool to match the page is the one move that makes the
check meaningless.

```text
# pd-image-census pinned figures
region_offset = 0x20000
region_length = 65536
region_sha256 = 30fe7fb8174535d2846e77ca837239a91548748e616cc6f061cf151ee230f970
firmware_sha256 = 158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4
used_end = 0xF7B7
erased_tail = 0xF7B8-0xFFFF
ff_bytes = 3705
longest_ff_run = 2120
vector_entries = 6
vectors = 0x00->0x0500@c_startup 0x03->0x0056@dptr0x0151,lcall0x0050,pushes13 0x0B->0x0094@dptr0x0154,lcall0x0050,pushes5 0x13->0x00B2@dptr0x0157,lcall0x0050,pushes13 0x1B->0x00F0@dptr0x015A,lcall0x0050,pushes5 0x23->0x010E@dptr0x015D,lcall0x0050,pushes13
vector_gap = 0x26-0x3F erased (0xFF)
vector_code = 0x0151=1site@vector_wrapper_dp_0151 0x0154=1site@vector_wrapper_dp_0154 0x0157=1site@vector_wrapper_dp_0157 0x015A=1site@vector_wrapper_dp_015a 0x015D=1site@vector_wrapper_dp_015d
pool_candidates = 43
pool_referrers = 0
code_table_inline = 0x119C=9site/0open_a_string 0x11C2=16site/0open_a_string 0x11EF=3site/0open_a_string
identity_strings = ITE8850-PD@0x0040 ProtoVer:01.00@0x0160 DriverVer:01.00@0x0170 UsbPdVer:01.00@0xE1C0
pd_listings = 542
pd_listing_overlaps = 0
pd_annotation_rows = 542
pd_dispatch_rows = 21
host_block = 0xFF80=5 0xFFE0=6 0xFFE1=4 0xFFE2=4 0xFFE3=0 0xFFD0=2 0xFFD1=0 0xFFD5=2
prov_ec_member_sha256 = 158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4
prov_ec_member_is_committed = True
prov_region_in_ec_member = True
prov_rom_size = 13631488
prov_rom_region_copies = 0x020000 0x45CA2C 0x49CA4C 0x4DCA6C 0x51CA8C
prov_rom_region_copy_count = 5
prov_rom_ec_image_at = 0x43CA2C
prov_rom_ec_image_is_committed = True
prov_nsh = IFUX64.efi GMxMGxx_11.800 0 1
prov_zip_members = 8
prov_zip_other_members = 6
```

## Related

- [`lightbar-bat-flow.md`](lightbar-bat-flow.md) §2 — why the region is a
  separate program. Canonical, and not re-argued here.
- [`pd-0x38-consumers.md`](pd-0x38-consumers.md) — five manual traces of who
  builds the pointers the `0x0FAF` four-byte XDATA reader then consumes, and
  the `0x119C` CODE-table cases. (This bullet used to credit the file with the
  `0x0F45`/`0x10FD` pointer-kind dispatchers; neither address appears in it.
  `0x0F45` is decoded in the next entry, [`pd-0x07d8-flow.md`](pd-0x07d8-flow.md),
  and `0x10FD` is its three-byte sibling in
  `annotations/ghidra-functions.csv`.)
- [`pd-0x07d8-flow.md`](pd-0x07d8-flow.md) — what `0x35DA`'s `ljmp 0x0F45` does
  with the program's own `0x07D8`-`0x07DA`, and the read/write/handoff split
  behind those three addresses.
- [`pd-index-geometry.md`](pd-index-geometry.md) — the indexed DPTR idiom that
  §3.1 says is a way this program reaches CODE.
- [`pd-base-strides.csv`](pd-base-strides.csv) — the 448 XDATA bases §2.1 names
  five of.
- [`../ghidra/manifest.csv`](../ghidra/manifest.csv) — the `pd` row: this image
  is already the third program of the committed `ec.gpr`, 542 functions, 542
  decompiled, 0 failed, 542 seeds, 542 annotations applied. Issue #26 asked
  whether it belongs in #20's Ghidra scope; it does, and has.
- [`../../docs/findings/pd-image-census.md`](../../docs/findings/pd-image-census.md)
  — the write-up, in the house shape.
- [`../../docs/hardware-tests/pd-controller-enumeration.md`](../../docs/hardware-tests/pd-controller-enumeration.md)
  — **not run.** The procedure for §5.2.
