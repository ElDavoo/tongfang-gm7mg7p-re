# The pack-temperature producer chain at `0x04A2`/`0x04A3` (issue #1425)

**Nothing here was observed on hardware.** No register was read, written or
read back, and no site was seen run. This is a static reading of committed
listings (`ec/decompiled/`) and committed scans run against the committed image
`ec/firmware/GMxMGxx_11.800`. **Arithmetic is not behaviour**: the dK values
below say what a byte sequence computes, never that a byte held that value,
that a code path executes, or that the EC acted on it. A `write` in the census
is an instruction, not an observation, and "not found by this method" is never
"absent" — `ec/annotations/registers.yaml`'s own header says so and this file
does not restate it as settled.

The pair is 16-bit little-endian with **`0x04A2` low**. Two things this file
settles, one it declines to: the main EC's two store sites for the pair are
both accounted for and neither is a measurement of the pack; the word
`0x0502`/`0x0503` has at least two writers reached from two different call
paths and is not the EC's pack temperature by any evidence here; and the PD
image's five `0x04A3` sites want neither the EC's high byte nor its own
`0x04A3` — they want a **strided field inside the PD's own
`0x04A1`-`0x04A6` block**, and the byte at `0x04A3` itself is dereferenced by
exactly one of the five, at a rebased address.

## 1. The consumer side, as already recorded

Cited, not re-derived.

| what | where |
|---|---|
| `batt_temp_dK` returns "pack temperature in decikelvin from XDATA 0x04A2/0x04A3" | `ec/decompiled/bank0/BAE5.c:7` |
| `BAE7` "Reads XDATA 0x04A3 into R6 and XDATA 0x04A2 into R7, leaving the pair in R7 (low) and R6 (high)" — **low is `0x04A2`** | `ec/decompiled/bank0/BAE7.c:7` |
| its callers | `ec/decompiled/bank0/8B14.c:132`, `ec/decompiled/bank0/8C46.c:50` |
| two consumers compare the **word**: `read_xdata_pair_to_r3r4(0x4a2)` + `cmp_r3r4_against_r1r2_16bit()`, the first against `0x0CEE` | `ec/decompiled/bank1/C3A0.c:7`, `ec/decompiled/bank1/C392.c:15` |
| `0xB0D1` loads the pair back and compares it against a CODE table entry's bytes 0 and 1 | `ec/decompiled/bank1/B0D1.c:11` |
| the 3030 dK / 3130 dK thresholds that weight the stress counter | `ec/annotations/charge-target-derating.md:48` |

`BAE7.c:9` and `C3A0.c:10` both said in their own text that the address had
no `registers.yaml` entry. `BAE7`'s clause is now corrected at source — the
annotation CSV carries the replacement and the re-export put it in the text —
because a comment asserting a register does not exist is a claim the naming
makes false, and leaving it would have been a stale sentence in a file about
naming a register. `C3A0`'s weaker "not documented" clause is left as written:
it is true of `0x0622` and `0x0805`, which still have no entry, and splitting
it to exempt `0x04A2` would edit a shared file for one address's sake.

## 2. Which sites write the pair — issue step 1

`ec/annotations/xdata-registers.csv` row 363 gives `0x04A2` `refs 9 / read 6 /
write 3` and row 364 gives `0x04A3` `refs 8 / read 4 / write 3`, both
`write_main_ec 3`. The annotation named one route. The other two are **not a
third store**, and the census's own `functions` column says why.

### The three `write` references are two store sites, one counted twice

`trace_xdata_refs.py` finds the main-EC `mov DPTR,#0x04a2` sites:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x04A2 \
  | grep -E 'runtime 0x'
  file 0x0BAEC  bank0     runtime 0xBAEC      read x1
  file 0x12F28  bank1     runtime 0xAF28      DPTR handed to lcall 0x888c
  file 0x12F39  bank1     runtime 0xAF39      DPTR handed to lcall 0x888c
  file 0x13134  bank1     runtime 0xB134      DPTR handed to lcall 0x8892
  file 0x13145  bank1     runtime 0xB145      DPTR handed to lcall 0x8892
  file 0x143A7  bank1     runtime 0xC3A7      DPTR handed to lcall 0x8892
```

Two of the five bank1 sites write and three read, by what the *callee* does:
`0x888c` is `write_r1r2_to_xdata_pair` and `0x8892` is
`read_xdata_pair_to_r3r4`. So the main EC has **two** store sites for the pair,
`0xAF28` and `0xAF39`, and the census's three come from three `.c` files:

```console
$ grep -rn 'write_r1r2_to_xdata_pair(0x4a2' ec/decompiled/*/*.c
ec/decompiled/bank1/AD7D.c:27:      write_r1r2_to_xdata_pair(0x4a2);
ec/decompiled/bank1/AF06.c:31:      write_r1r2_to_xdata_pair(0x4a2);
ec/decompiled/bank1/AF32.c:12:  write_r1r2_to_xdata_pair(0x4a2,0x72,0xb);
```

`AD7D.asm` is one instruction:

```console
$ cat ec/decompiled/bank1/AD7D.asm | tail -1
AD7D     02 af 06 ljmp     0xaf06
```

so its `.c` is the decompiler following that tail jump, and the store it shows
at line 27 is `AF06`'s at `0xAF28` re-rendered. `AD7D.c:7-9` says so in its own
text. **The third `write` reference is the first one counted twice**, which is
the answer issue step 1 asked for; the per-access count is the same route and
no site is unaccounted for.

### Route 1 — `0xAF32`, and the value it stores

`0xAF06`'s gate has three routes (`AF06.c:7-14`, `AF06.asm:7-27`): bit 2 of
`0x0490` clear → `call 0xAF32`; bit 2 set and bit 3 of `0x04FF` set → straight
to `0xB0D1`; both held with bit 3 of `0x04FF` clear → a `0x0505` of 1 copies
`0x0502`/`0x0503` into `0x04A2`/`0x04A3`, a `0x0505` of 0 falls to route 1, and
any other value returns without reaching `0xB0D1`.

Route 1's store is the one the issue's own text did not name, and the value is
**a literal in the listing, not a caller's**:

```console
$ sed -n '9,13p' ec/decompiled/bank1/AF32.asm
AF32     90 0b 72 mov      DPTR, #0xb72
AF35     aa 83 -  mov      R2, DPH
AF37     a9 82 -  mov      R1, DPL
AF39     90 04 a2 mov      DPTR, #0x4a2
AF3C     12 88 8c lcall    0x888c
```

`DPTR` is loaded with `0x0B72` and split into `R1` (low, `0x72`) and `R2`
(high, `0x0B`) before the store helper, so the value written to
`0x04A2`/`0x04A3` is **`0x0B72` = 2930 dK**, whatever the caller left in R1:R2.
Ghidra renders the same bytes as the inlined literal
`write_r1r2_to_xdata_pair(0x4a2,0x72,0xb)` (`AF32.c:12`), which is how a
reviewer can mistake it for arguments that arrived from a caller. The `.asm`
is the machine code and the `.c` is a reading of it, as every listing's header
says.

**What `0x0B72` means is not established here.** The arithmetic: `0x0B72` is
2930 dK, and the consumer's first threshold in
`charge-target-derating.md:48` is 3030 dK — so the constant sits **100 dK
below** the first threshold, and 200 dK below the second. It is a fixed
constant either way, not a measurement, and **whether the EC ever actually
reaches this store with a real temperature in `0x0502`/`0x0503` is the
hardware question this file does not answer**. `AF32` also writes `0x056B = 4`
and `0x0493 = 0` (`AF32.asm:14-19`, `AF32.c:13-14`), which is what makes it
route 1 rather than a plain copy: it resets the step index `0xB0D1` walks.

`AF32`'s function boundary is a **hypothesis** from the call-target byte scan,
which `ec/annotations/bank-call-audit.md` §1 calls an upper bound. The
instructions above `0xAF4A`'s `ret` are all of the listing this change reads;
another entry inside the span would mean the listing is not the whole routine.

## 3. What `0x0502`/`0x0503` is — issue step 2

`xdata-registers.csv` rows 392-393 give `0x0502` 8 refs / 4 write and `0x0503`
10 refs / 4 write, all `main-ec`, all in the same seven functions. Read them
all, which is what the issue asked for.

### `0xAC84 ten_step_check_1aaa_889e` — the sensor-probe evidence

`AC84.c:33-87` and `AC84.asm:11-90`: the routine runs **ten** steps, each
loading `R3 = 0x16`, `R4` = one of ten constants and `R5 = 0x0C`, calling
`0x1AAA`, bailing with carry set if that returned carry, and on carry clear
setting DPTR to the matching address and calling `0x889E`
(`write_r3r4_to_xdata_pair`). The ten DPTR immediates, in listing order:

| # | R4 | DPTR | # | R4 | DPTR |
|---|---|---|---|---|---|
| 1 | `0x08` | `0x0502` | 6 | `0x09` | `0x0506` |
| 2 | `0x0F` | `0x0518` | 7 | `0x3C` | `0x053A` |
| 3 | `0x18` | `0x052A` | 8 | `0x3D` | `0x053C` |
| 4 | `0x19` | `0x052E` | 9 | `0x3E` | `0x053E` |
| 5 | `0x0D` | `0x0514` | 10 | `0x3F` | `0x0540` |

`0x0502` is **the first of ten**, and it is the only one of the ten the
`0xAF06` chain then reads. Steps 7-8 are conditional on bits 6-7 of `0x0491`
(`AC84.asm:56-76`); the rest run on every path. The other nine are read by
other routines — `0x0514` by `0x8BD1` and `0xB2D5` among them — so this is a
**ten-slot probe table** and `0x0502` is slot 1, not a lone measurement. What
`0x1AAA` and the ten R4 constants select is not decoded here, and the
`XDATA` slots' contents are not either; the issue's hardware question is
whether slot 1 is a pack thermistor, and this file does not answer it.

### `0xE8A4 compute_097e_times_10_write_0386_0387` — a second writer, different provenance

`E8A4.c:58-63` and `E8A4.asm:41-51`: the routine counts a loop down from
`0x097E` (substituting 1 for 0), stores the result back to `0x097E`, forms
the 16-bit product **R5 × 10** in `R3:R4` (`mov B,#0x0a; mul ab`), adds
`0x0A46` to it via `0x8854`, and stores that to `0x0502`/`0x0503` with
`0x889E` — then the same value to `0x0504`/`0x0505`. So the word here is a
**loop count times 10 plus a constant**, and nothing in this routine is a
temperature. It is a second writer reached from a different path.

### `0xDB0B` and `0xE100` — the same shape, and the same caveat

`DB0B.asm:125-126` stores `R3:R4` to `0x0502` through `0x889E`, where `R3:R4`
is `R3 × 10 + 0x0AAA` computed at `DBE3-DBF1` from the R3 `0xCBF3` returned
(`DB0B.c:85`). `E100.asm:105-108` stores `R1:R2` to `0x0502` and `0x0504`
through `0x888c`, where the value is `DAT_EXTMEM_0391 × 10 + 0x0AAA` built at
`E1A0-E1B0` (`E100.c:60-63`), guarded by bit 4 of `0x04FE` and bit 3 of `0x03FF`
both clear and bit 1 of `0x0367` clear. **Both are the same
"value × 10 + 0x0AAA" shape**, which is the strongest single fact this file
carries about the word: two of its four writers compute a scaled constant
rather than reading a sensor.

**Both functions' boundaries are hypotheses.** `DB0B.c:5-6` and `E100.c:5-6`
both carry the same header clause — "function boundary from a call-target byte
scan; that census is an upper bound (`ec/annotations/bank-call-audit.md` §1), so
this boundary is a hypothesis" — so a store at an address inside either span
that the export did not reach would not appear in the listing read above.

### `0x8BD1 select_probe_address_and_return_carry` — the issue's "strongest hint", adjudicated

The issue calls this name the strongest evidence that a sensor probe is
involved. It is a **consumer of the word, three times, and never a writer**:

| arm | DPTR | comparison constant, R4:R3 | source |
|---|---|---|---|
| 1 | `0x0502` → `0x8886` | `0x0CE4`, or `0x0D48` if bit 0 of `0x0497`, else `0x0D16` | `8BD1.asm:29-61` |
| 2 | `0x0502` → `0x8886` | `0x09F6`, or `0x0ABE` under the same `0x0497` bit | `8BD1.asm:64-96` |
| 3 | `0x0506` → `0x8886` | `0x2328`, or `0x2EE0` / `0x1770` by bits 6-7 of `0x0491` | `8BD1.asm:98-119` |

Arms 1 and 2 re-read the *same* `0x0502` pair; arm 3 reads a different word,
`0x0506`. The name is about selecting which comparison to make, and the
selection is driven by `0x0497`/`0x0398`/`0x030D`/`0x0491` — configuration
bytes, not by anything measured. **The name is not evidence of a probe**, and
nothing here turns it into some.

One arithmetic note the issue asked for. `0x0CE4` is **ten dK** below the
`0x0CEE` the temperature consumers compare against, not one: `0x0CEE` is 3310
and `0x0CE4` is 3300. The two are the same scale and 10 dK apart, which is
consistent with arm 1 testing the same quantity one step below the `0x0CEE`
threshold — but that is a reading of two constants, and this file records it
as such rather than converting either to °C.

### The bounded verdict

**The word `0x0502`/`0x0503` has at least two writers reached from two
different call paths — `0xAC84`'s ten-step probe sweep and `0xE8A4`'s
loop-count product, plus `0xDB0B` and `0xE100` on the `×10 + 0x0AAA` shape —
and it is read by `0xAF06`, by `0x8BD1` twice, and through the `0xAD7D`
forwarder.** Whether it tracks the pack is a hardware question and is **not
this file's claim**.

Two of the four writers compute `value × 10 + 0x0AAA` and one computes
`value × 10 + 0x0A46`, so the word is at minimum **overwritten by scaled
arithmetic on four different paths**, and on at least two of them the stored
value does not come from anything that looks like a measurement. Whether
`0xAC84`'s slot-1 store is later clobbered before `0xAF06` reads it is not
settled by a static reading and is not settled here.

**"The producer is not established" is not upgraded to "the EC never writes
it" anywhere in this file.** The opposite is what the four writers are, and
each is a `write` in a census, which is an instruction and not an observation
that the EC acted on it.

## 4. The PD adjudication — issue step 3

The precedent the issue names is `BAT_CYCLE_COUNT`'s: for `0x04A6`,
`pd-xdata-overlap.md` answered "does the PD write this?" by showing all four
PD sites use the address as the **base of strided address arithmetic and never
access the byte**. For `0x04A3` the question is sharper, because
`pd:0xF22E read_04a3_then_call_9a90` *does* dereference — `F22E.asm:9-10` is
`movx A,@DPTR` / `mov R6,A`. The byte-level reading settles it, and it settles
it **in favour of the precedent, for a reason the `0x04A6` answer did not need**.

All five sites hand DPTR to a helper, and every helper **returns** — it adds
a stride term and hands the caller back a computed address:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 \
    --helpers 0x10BC 0x9987 0x998B 0x9A1B 0x9A3F
0x10BC  (file 0x210BC)  DPTR += A×B
0x9987  (file 0x29987)  DPTR += R7×0x60 + 0x200×R7
0x998B  (file 0x2998B)  DPTR += A×B + 0x200×R7
0x9A1B  (file 0x29A1B)  DPTR += R3×0x60
0x9A3F  (file 0x29A3F)  DPTR += A×0x60
```

A returning helper is not by itself the answer, because what follows the
`lcall` is the site's own code — and **three of the five dereference the
pointer the helper handed back.** `0x9DA6` is `90 04 a3 | 12 99 8b | e0`, and
`0xE0` is `movx A,@DPTR`; `0x9E52` is `90 04 a3 | 12 9a 3f | ee | 12 99 8f |
ef | f0`, ending in `0xF0`, `movx @DPTR,A`. So the question is not *whether*
a site dereferences but *which address* — and `--bases 0x0400-0x04FF` answers
that for all five:

| site | helper | term the helper adds to DPTR | the site dereferences DPTR? |
|---|---|---|---|
| `0x917A` | `0x10BC` (direct `ljmp`) | `A×B` | no — the chain ends at the tail call into `0x10BC` |
| `0x9DA6` | `0x998B` | `A×B + 0x200×R7` | **yes, at the rebased address** |
| `0x9E52` | `0x9A3F` | `A×0x60` | **yes, at the rebased address** |
| `0xEDB7` | `0x9A1B` | `R3×0x60` | no — the chain stops unmodelled at `0x99D5`, so it reaches no `movx` *under this model* |
| `0xF22E` | `0x9987` | `R7×0x60 + 0x200×R7` | **yes, at the rebased address** |

The tool's own census of the block says, in its own words, which of the five
ended at a `movx` — **three, not one**:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --bases 0x0400-0x04FF
0x04A3: 5 site(s)
      DPTR = 0x04A3 + A×0x60 [chain ends at tail call into 0x10BC]
      DPTR = 0x04A3 + A×0x60 + 0x200×R7 [chain ends at movx: DPTR dereferenced here]
      DPTR = 0x04A3 + A×0x60 + 0x200×R6 [chain ends at movx: DPTR dereferenced here]
      DPTR = 0x04A3 + R3×0x60 + 0x200×R3 [chain ends at 0x99D4 is unmodelled: 0x99D5 `add  a,#0x01` is outside the term model]
      DPTR = 0x04A3 + R7×0x60 + 0x200×R7 [chain ends at movx: DPTR dereferenced here]
```

**Every effective address is `0x04A3 + n`, for an `n` the tool's terms make
non-zero in general** — and that, not the count of dereferencing sites, is
what decides the question. The `movx` at `0xF234` reads `0x04A3 + R7×0x60 +
0x200×R7` — the value R7 held at the site — and not the byte the site names;
`0x9DA6`'s `movx A,@DPTR` reads `0x04A3 + A×0x60 + 0x200×R7`, and `0x9E52`'s
`movx @DPTR,A` writes `0x04A3 + A×0x60 + 0x200×R6`. None of the three reaches
`0x04A3` itself. `0xF22E` is a *strided read of a field*, exactly the `0x04A6`
shape, and the `&DAT_EXTMEM_04a3` in `F22E.c:20` is the decompiler spelling
the **base**, not the address the `movx` touches. The PD image is never given a
symbol table (`gen_xdata_symbols.py`'s own refusal), which is why the base is
the only thing in that file named at all.

**The answer, in the three words the issue offers:** the PD wants **a third
thing** — a field at a strided offset inside the PD's own `0x04A1`-`0x04A6`
block, with `0x04A3` as the base rather than as the datum. It does not want
the EC's high byte, and the `BAT_CYCLE_COUNT` answer **does** transfer here,
with the sharper form that all three sites which dereference do so at a
rebased address, and the two that do not are the two whose chains reach no
`movx` under this model. Two caveats the transfer does not erase: the
`0x200×` term's coefficient is `0xE0` added to the carry-adjusted DPH
(`9987.asm` line `0x998f 25e0`), which is `pd-index-geometry.md`'s `0x200×`
naming and not something derived here; and one of the five chains stops
**unmodelled** at `0x99D5`, so its own term is a lower bound.

`ec/annotations/pd-index-geometry.md:329-330` needs no edit: five `0x04A3`
sites and four with the `0x200×` term is what `--strides` still reports, and
nothing above moves a site or a term.

## 5. What this does not establish

- **Nothing here is a behaviour.** The `0x0B72` constant, the four writers of
  `0x0502`/`0x0503` and the PD's five handoffs are all instruction-level
  readings of committed listings. No byte was watched move.
- **Not "absent".** No method here searched for a writer the export does not
  contain. `DB0B`'s and `E100`'s boundaries are hypotheses from a byte scan
  that is an upper bound, so a store inside either span that the export missed
  would not appear above.
- **Not a unit.** The dK readings rest on
  `charge-target-derating.md:48`, which is cited and not edited. This file does
  not convert `0x0CE4`, `0x09F6` or `0x0ABE` to °C, and does not claim
  `0x0502`/`0x0503` is a temperature in any unit.
- **The hardware half is untouched.** Whether the pair tracks the pack, and
  what the `0x04FF` bit 3 / `0x0505` gate selects, need the physical machine.
  The issue says so and this file agrees; no script, transcript or observation
  implying a live test is included, and none is prepared.

## 6. The next hops, named and not walked

- The four CODE tables `0xB0D1` compares the pair against — `0xAFF1`,
  `0xAFB1`, `0xB031`, `0xB071` — are **not decoded** here. A separate question
  with its own inputs.
- `bank0:0x8590`, which `AC84`'s sweep calls, is read only as far as `AC84.c`
  and its `.asm` show.
- `0x0505` and `0x0506` get no `registers.yaml` row from this change. `0x0505`
  is the gate `0xAF06` tests, and what it selects is the issue's own hardware
  question; `0x0506` is a third comparison slot in `0x8BD1` and a second slot
  in `AC84`'s sweep. Both are named here and neither is a settled register.
