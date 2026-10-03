# The 0x0390/0x0391 pair: what the 0x9EA1 filter reads, what the `E100` branch selects, and where `0x0391`'s value comes from (issue #295)

Issue [#295](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/295) asked
for three accounts of two adjacent EC XDATA bytes — the filter's input pair,
what the comparison in `FUN_CODE_e100` selects, and where the value in `0x0391`
comes from — and offered a fourth conditionally: rename `XDATA_0390` if the
reading supports a name.

**No live test was run and none could be.** This pipeline has no access to the
machine (`CLAUDE.md`, "Cloud agents cannot reach the hardware"). Everything
below is a reading of the committed listings, and the strongest claim it makes
about behaviour is that a *direction* was resolved statically. Both bytes stay
`present-untested`, which is where `#259` left `0x0390` and is the honest
ceiling for a byte a reader is already looking at.

The fourth ask is answered **no**, with what is known and what would settle it
in the last section.

---

## 1. The filter's input pair is a two-byte shift with a byte injected

`shift_pair_then_sum_and_divide_by_four` at `bank1 0x9EA1` is 39 instructions
(`ec/decompiled/bank1/9EA1.asm:7-45`) and has exactly two callers in the whole
decompile tree — `E100.asm:76` and `E237.asm:39`. A byte scan of the image for
`12 9e a1` returns those two and nothing else, at file offsets `0x16182` and
`0x16276`.

What it does with the pair is not what "shift pair" suggests, and the listing
has to be read in order to see it:

```
9EA3     mov  A, R1
9EA4     movx @DPTR, A       <- R1 goes to the LOW byte of the pair
9EA5     inc DPTR
9EA6     movx A, @DPTR
9EA7     mov  R7, A
9EA8     mov  A, R6
9EA9     movx @DPTR, A       <- and the OLD low byte goes to the high byte
```

(`9EA1.asm:9-15`.) So for `E100`, which passes DPTR `0x03C5`, the effect is
`(0x03C5, 0x03C6) <- (R1, old 0x03C5)`. It is a two-byte shift with a byte
injected at the low end, not a scratch toggle, and nothing in the image
mentions `0x03C6` or `0x03C8` as a literal — `scan_refs.py` finds one site for
`0x03C5` and one for `0x03C7` and none for either second byte, because the only
way in is the `inc DPTR` at `9EA1.asm:11`. **"Not found by this method", never
"absent"**: the two are reached by a walk, which is the same blind spot
`registers.yaml`'s own header warns about.

The two callers differ only in which accumulator and which pair:

| caller | accumulator (R3:R4) | pair (DPTR) | result published to |
|---|---|---|---|
| `E100.asm:73-76` | `0x0390` | `0x03C5`/`0x03C6` | `0x0386`, behind the two guard bits of §2 |
| `E237.asm:36-39` | `0x0391` | `0x03C7`/`0x03C8` | `0x0387` |

### The top two bits, re-derived rather than restated

The existing hand-decode (`9EA1.c:11-13`) says the accumulator is written
`(carry count rotated into the top two bits) | ((sum >> 2) & 0x3F)`. The
instruction is `9EA1.asm:33-43`:

```
9EC5     rr  A          ; sum >> 2, done as two rotates
9EC6     rr  A
9EC7     anl A, #0x3f   ; R1 = (sum >> 2) & 0x3F          -> :36 mov R1, A
9ECA     mov A, R5
9ECB     swap A         ; R5's low nibble into the high nibble
9ECC     rl  A          ; rotate left, CY shifts into bit 0
9ECD     rl  A
9ECE     anl A, #0xc0   ; and the shifted-in carry bits are masked off
9ED0     orl A, R1
9ED1     movx @DPTR, A
```

R5 counts 8-bit carries and is incremented once per add at `9EA1.asm:21-22`,
`:24-25`, `:27-28` and `:31-32`, so **R5 ≤ 4**. `swap` puts R5 in the high
nibble; two `rl` put it in the top two bits and drag whatever was in bit 7 down
into the low bits, which `anl A, #0xc0` discards. For R5 in 0..3 that leaves
exactly `(R5 & 3) << 6`. For R5 = 4 — which is reachable, not merely
theoretical: four addends of `0xFF` sum to `0x3FC`, bit 7 is set, and the
`add A, #0x4` round-to-nearest correction at `:30` carries a fourth time — the
same rotation yields `0x01` and the mask leaves `0x00`, which is `(4 & 3) << 6`
as well.

**Correction to the hand-decode, in place.** `9EA1.c:12-13` says R5 reaching 4
is "which four addends of at most 0xFF cannot produce". They can: `0xFF +
0xFF + 0xFF + 0xFF` is `0x3FC`, and the `+4` at `9EA1.asm:30` then makes
`0x400`. The formula the comment states is unaffected — `(R5 & 3) << 6` covers
R5 = 4 correctly — so only the parenthetical's reachability claim is wrong.
The text lives in `ec/annotations/ghidra-functions.csv` and reaches
`ec/decompiled/` through a re-export, which this change does not do; the wrong
sentence stays where it is with this correction beside it.

So the filter is a recursive smoother over a byte stream: the previous
accumulator output, plus the last three samples, rounded, divided by four.

---

## 2. The `E100` branch selects the larger of the two

`E100.asm:64-93`, in order:

```
E16C     mov  DPTR, #0x1c04 ; E16F movx A, @DPTR ; E170 mov R1, A   R1 = [0x1C04]
E171     mov  DPTR, #0x391  ; E174 movx A, @DPTR ; E175 mov R0, A   R0 = [0x0391]
E176     mov  DPTR, #0x390  ; E179 movx A, @DPTR ; E17A mov R2, A   (dead, see below)
E17B     mov  R4, DPH ; E17D mov R3, DPL                            accumulator = 0x0390
E17F     mov  DPTR, #0x3c5  ; E182 lcall 0x9ea1
E185     mov  R1, A                                                R1 = filter output
E186     clr CY ; E187 subb A, R0 ; E188 jc 0xE18D                   if (output < R0) skip
E18A     85 01 00        mov  0x00, 0x01
E18D     clr A ; E18E mov DPTR, #0x560 ; E191 movx @DPTR, A         0x0560 = 0
E192     mov  DPTR, #0x4fe ; E195 movx A, @DPTR
E196     jb   0xe4, 0xE1D4                                          guard, ACC bit 4
E199     mov  DPTR, #0x3ff ; E19C movx A, @DPTR
E19D     jb   0xe3, 0xE1D4                                          guard, ACC bit 3
E1A0     mov  A, R0 ; E1A1 mov DPTR, #0x386 ; E1A4 movx @DPTR, A    0x0386 = R0
```

### Is direct `0x00` the same storage as R0?

This is the question the decompile cannot answer, because it answers it two
different ways. `E100.c:53` renders `E100.asm:81` as `BANK0_R0 = BANK0_R1;` —
honouring the aliasing — and `E100.c:58` then publishes `bVar2`, its own
stale copy of `[0x0391]`, as `DAT_EXTMEM_0386`, which requires that the
aliasing **not** have happened.

**It does.** Three things settle it, none of which is Ghidra's word for it:

1. **The opcode.** `85` is `MOV direct, direct`, and the source direct address
   is the byte after the opcode. `85 01 00` is therefore *destination `0x00`,
   source `0x01`* — the listing's `mov 0x00, 0x01` prints destination first, the
   same order `ec/tools/disasm8051.py` uses everywhere else in the file.
2. **The same idiom elsewhere in this image, as a cross-check.**
   `A5E6.asm:41-44` is four back-to-back `MOV direct, direct`:
   ```
   A613     85 05 02        mov  0x02, 0x05
   A616     85 00 01        mov  0x01, 0x00
   A619     85 07 04        mov  0x04, 0x07
   A61C     85 06 03        mov  0x03, 0x06
   ```
   which is `R2 := R5`, `R1 := R0`, `R4 := R7`, `R3 := R6` — two 16-bit
   register-to-register moves, `(R2:R1) := (R5:R0)` and `(R4:R3) := (R7:R6)`,
   not a swap (R0 is never written and R7 goes to R4, not to R1), spelled with
   the `0x00`..`0x07` direct addresses. `A5E6.c:44-47` reads the same four as
   `BANK0_R2 = BANK0_R5` and the three beside it. Register moves written over
   `0x00`..`0x07` only type-check if those eight direct addresses *are* the
   bank-0 registers, so the shape of the code says what Ghidra's names only
   assert.
3. **Nothing switches banks in between.** R0 is written by `f8` (`mov R0, A`)
   at `E100.asm:69` and read back by `e8` (`mov A, R0`) at `:91`, with the
   branch between them, so the span that has to be free of a bank switch is
   `:69` to `:91`. That span holds one call, the `lcall 0x9ea1` at `:76`, whose
   own 39 instructions name no PSW either, and no instruction in it writes PSW
   or direct `0xD0`. The rest of the routine agrees: decoding the whole of
   `FUN_CODE_e100` — `E100.asm:9` to `:117`, the routine's full extent in this
   listing — finds no PSW write either, and its only other calls are the two
   `lcall 0x888c` at `:106` and `:108`, whose callee is six instructions
   (`888C.asm`: `mov A, R1` / `movx @DPTR, A` / `inc DPTR` / `mov A, R2` /
   `movx @DPTR, A` / `ret`) and touches neither. So the bank is the same at
   `:69` and at `:91`.

   The nearest miss is worth naming, because it reads like a counter-example:
   `setb 0xe3` at `E100.asm:25` and `setb 0xe7` at `:31` are both `setb`, and
   `jb 0xe4` at `:87` and `jb 0xe3` at `:90` are bit tests. All four are **ACC**
   bits, not PSW bits. `0xE0`-`0xE7` is the accumulator and `0xD0`-`0xD7` is
   PSW, as `disasm8051.py`'s `BIT_SFR` table has it, and the decoder renders
   these four as `setb acc.3`, `setb acc.7`, `jb acc.4` and `jb acc.3`. Three
   committed `ghidra-functions.csv` rows already carry the same correction for
   the same operand bytes — the `0xA750`, `0xA841` and `0xAAB9` annotations,
   each reading "bit addresses in internal RAM 0xE0, not masks on the byte just
   read into A". So `FUN_CODE_e100` writes no register-bank bit anywhere, and
   the "but that path never reaches the comparison" caveat an earlier draft
   carried here is not needed at all: the premise it rested on was wrong.

   What `setb 0xe3` at `:25` does set is bit 3 of the byte just read from
   `0x03A0` and written back at `:26` — `E100.asm:21-26` is `mov DPTR,#0x3a0` /
   `movx A,@DPTR` / `jnb acc.3` / `sjmp` / `setb acc.3` / `movx @DPTR,A` — the
   same read-modify-write on `0x03A0` that the `0xE27D` annotation describes
   for that byte, which exclusive-ORs it with `0x01` and stores it back.

The repo has been bitten by this class of artifact in this very filter:
`9EA1.c:15-16` records that the decompiled
`*(byte *)CONCAT11(param_4,param_3)` pointer is a reading artifact, "the
listing sets DPH from R4 and DPL from R3".

### What the branch therefore selects

`subb A, R0` with carry cleared borrows exactly when the filter's output is
below `[0x0391]`. So:

- **output < `[0x0391]`** — `jc` taken, `E100.asm:81` skipped, R0 still holds
  the raw byte.
- **output ≥ `[0x0391]`** — `jc` not taken, `85 01 00` copies R1 into R0, so
  R0 holds the filter's output.

**The branch selects `max(filter output, [0x0391])` for the value that would
be published.** It is a clamp, not a choice between two named alternatives.
What reaches `0x0386` is that value *conditionally*, though, and the write-up
that said otherwise was wrong: two instructions sit between the branch and the
store. `jb 0xe4, 0xE1D4` at `E100.asm:87` and `jb 0xe3, 0xE1D4` at `:90` both
leave to `ljmp 0xe27d` at `E1D4` before `E1A0`-`E1A4` runs, so on either arm
`0x0386` is not written at all. The store happens only when neither `0x04FE`
bit 4 nor `0x03FF` bit 3 is set. The committed C carries the same guard —
`E100.c:56` is `if (((DAT_EXTMEM_04fe >> 4 & 1) != 1) &&
((DAT_EXTMEM_03ff >> 3 & 1) != 1))` — so this is not a listing artefact, and
the elision those two instructions sat behind in the listing quoted above is
what hid it.

What the two guard bits *mean* is a further question this write-up does not
open; that they gate the store is all the listing settles. `present-untested`
stays the ceiling for both bytes for that reason as much as for the ones
already noted.

The committed C does not carry the clamp account either: `E100.c:58` publishes
its own copy of `[0x0391]`, which under the aliasing resolved above is the
right value on *one* arm and the wrong one on the other, so the C and the
listing disagree in exactly the way this section opened on.

The dead store in the middle of it is worth naming because it is the same one
`XDATA_0390`'s row already records: `E100.asm:72` moves `[0x0390]` into R2,
`0x9EA1` reads R1, R3, R4, R5, R6 and R7 and never R2, and `E100.asm:100`
overwrites R2 with no intervening read. `[0x0390]` still matters — its
*address* is the accumulator handed on as R3:R4 at `E100.asm:73-74` — but the
load into R2 is a sibling of a live reference, not the whole of it.

Downstream, `0x0386` has one reader. `div_23_minus_0386_by_034d_capped_15` at
`D274.asm:7-27` reads it, subtracts it from `0x23`, and falls straight out when
that borrows or comes out zero — so that consumer acts on `0x0386` only below
35 — and otherwise divides what is left by `0x034D` in a loop bounded at 15,
writing `0x03BA`. `E100.asm:94-108` also publishes `R0 × 10 + 0xAA` to `0x0502`
on the same path, gated on bit 1 of `0x0367` being clear (`E100.asm:103-104`).
**That fixes the scale the value travels on — a small integer, and one the
downstream divide only handles below `0x23` — and does not fix what the
quantity is.**

---

## 3. Where the value in `0x0391` comes from

**Not the routine's argument.** `ec/decompiled/bank1/DB0B.c:73` reads
`DAT_EXTMEM_0391 = param_1`, and that is a register-tracking artifact:

- The instruction is `mov A, R3` (`DB0B.asm:100`).
- `param_1` *is* R3 at entry — `DB0B.asm:19-21` has `mov A, R3` →
  `[0x030C] = param_1`, and `DB0B.c:26` agrees.
- But the poll immediately above it, `lcall 0xc4f0` at `DB0B.asm:97`, writes
  R3 on its success path: `C4F0.asm:38` is `mov R3, A` with A loaded from
  XDATA `0x1C04`. The hand-decode at `C4F0.c:10` already records it.
- Nothing else in `0xC541`, the one routine that poll calls on the way out,
  touches R3 (`C541.asm:7-12` — R7 and A only).

So **`0x0391` holds the low byte of the 16-bit value the `0x1C00` block poll
returns in R3:R4** — the same `0x1C04`/`0x1C05` pair the poll hands to its
caller.

At the `E237` site the same value lands in R2 (`E237.asm:35`), and nothing in
`0x9EA1` reads it — the filter's operands are R1, R3, R4, R5, R6 and R7. Unlike
the `E100` R2 the sibling row already calls dead, this one is only *unread by
the filter*: the committed listings end at `E100.asm:117` (`ljmp 0xe27d`) and
`E237.asm` at `0xE27C`, so a later read of R2 would sit past the end of what
this tree shows. That is a limit of the listing, not a measurement.

Which arm writes it is worth being exact about. The store sits on the
**carry-clear** side of `jnc 0xdbc4` at `DB0B.asm:98`, and carry clear is that
poll's success return (`C4F0.asm:46` is `clr CY` on the success path;
`:32` is `setb CY` on the failure path, which is also where the `0x48` mask
test and the 100-iteration timeout land). The carry-set arm falls to
`lcall 0xe8a4` at `DB0B.asm:99`. The `jc` at `DB0B.asm:114` gates the *next*
transfer, the `×10 + 0xAA` write to `0x0502`, and has nothing to do with this
store.

The clobber is worth tracking, because it is what makes the rest of the
routine's arithmetic refer to two different values. `FUN_CODE_db0b` enters with
its argument in R3 and uses it early —

- masked `& 7` into `0x0491` as `0x40`/`0x80`/`0xC0` (`DB0B.asm:34-51`, off the
  `mov A, R3` at `:31`);

— and the poll at `:97` replaces R3 with `[0x1C04]`, after which every use is of
the poll's value and not of the argument:

- the store to `0x0391` itself (`:100-102`);
- `×10 + 0xAA` into `0x0502` (`DB0B.asm:115-126`, off the `mov A, R3` at `:115`
  and the second poll at `:113`);
- and, in `E100`, `R1 = [0x1C04]` at `E100.asm:64-66` is the byte the filter
  injects at the low end of the `0x03C5` pair.

So `0x0391` and the filter's newest sample are **the same byte** — `0x1C04` —
read at two different points, on two different paths through the scheduler. That
is why the comparison in §2 reads the way it does: a freshly-arrived block value
is compared against the smoothed history of the same stream, and the larger of
the two is the value the branch selects for publication — subject to the two
guard bits that §2 shows stand between that selection and the store.

---

## 4. Why `XDATA_0390` keeps its placeholder

The issue's conditional is answered in the negative, and the repo's own rule
says so. A descriptive name needs a unit or a referent, and there is none here:

> "UNITS NOT DETERMINED, and no name is coined: a wrong unit in a symbol
> outlives the note that would correct it."
> — the `XDATA_1C01` row in `ec/annotations/registers.yaml`, which is the same
> `0x1C00`-block family and the same recurring `0x48` constant this write-up
> leans on

> "The lesson is not that a name was wrong. It is that a name is a claim with a
> basis"
> — `docs/findings/name-basis-and-groups.md`

`gen_xdata_symbols.py`'s own rule against `_LO`/`_HI`/`_BYTE0` suffixes is the
same principle applied to byte order rather than units. What it cannot do is
supply a *referent*, and neither can anything checked and silent here:

- **`ECSpec.cs`** — the Windows service's `Define.ECSpec` constants spell every
  EC address in decimal. Neither `912` nor `913` (0x390, 0x391) appears in the
  committed decompiled `ECSpec.cs`, and no identifier there contains `390` or
  `391`. **Not found by this search.**
- **`evidence/acpi/dsdt.dsl`** — one occurrence of `0390` in the whole table,
  and it is a positional offset label inside a `WQBA` byte buffer
  (`Name (WQBA, Buffer (0x0A93))`), not a field. The `Offset(...)` list inside
  `Device (EC0)` does not cover this page.
- **Upstream `uniwill-laptop`** — no `EC_ADDR_` define in the `0x039x` range
  appears in any committed upstream excerpt under `linux/patches/`, and no
  `0x0390`/`0x0391` token does either. The excerpt's address defines start at
  `EC_ADDR_BAT_REMAIN_CAPACITY_1 = 0x0436`. **Not found by this search.**
- **`docs/related-projects.md`** — nothing on these addresses, so no sibling
  project has read them either.

One near-miss is worth naming so nobody re-runs the grep and believes it:
`windows/decompiled/native/GamingCenter3_Cross.c` contains a contiguous run
`0x391, 0x392, … 0x3c5, 0x3c6, 0x3c7` that is a Windows **language-ID**
registration table, not EC addresses.

**What would settle a name**, and it is a human's step at the laptop or a
document this repo does not have:

1. A live trace of one `0x1C00`-block transfer, recording what arrives in
   `0x1C04`/`0x1C05` — that byte is the whole question, and the EC alone never
   says.
2. The Windows-side field name for the corresponding request, which is the kind
   of thing that lives in a vendor protocol document rather than in
   `GCUService.exe`'s address constants.

Meanwhile `0x0391` gets the placeholder `XDATA_0391` for exactly the reason
`0x0390` has one, and even a `confirmed-working` byte would keep it: live
behaviour proves the byte acts, it does not supply a name.

---

## 5. What this does not establish

- **No live test, and no claim that one happened.** Both bytes are
  `present-untested`, and the direction resolved here is a static reading of the
  opcodes at three sites, not an observation.
- **`0x03C5`, `0x03C6`, `0x03C7`, `0x03C8` are not named.** They are the
  filter's *input*, which is a different question with a different warrant, and
  the issue itself notes them as the next hop rather than claiming them.
- **`0x0386`/`0x0387` and `0x0502`/`0x0504` are not given rows.** They are cited
  here as the consumer of the filter's output and as the scale the value travels
  on, which is a third and fourth question.
- **The unit.** What the compared quantity *is* — what a value of, say, 17 means
  to the firmware — is untouched by anything above. The scale is bounded; the
  referent is not known.