# The fan ramp is a closed loop: two integrators, two error terms, and a setpoint that is a curve lookup (issue #397)

(Static reading of committed files only — `ec/firmware/GMxMGxx_11.800` and the
listings and tables under `ec/decompiled/` and `ec/annotations/`. No laptop, no
EC and no Windows machine is involved: nothing here is a live test, no register
was read back, and no sentence below should be read as one. Every claim is
anchored to a `.asm` address; §8 names the commands that re-derive them, and
`ec/tools/test_fan_ramp_loop.py` holds each cited instruction still present.)

## The claim

`ec/annotations/subsystems.md` §6 groups the fan and thermal routines under
"Fan and thermal control" and says out loud that the group is a grouping and
not a decoded loop: *"There is no control loop here: no closed-loop reading,
no error term, no ordering between the CPU- and GPU-temperature functions."*
**Three things in that sentence are now settled, and the fourth was a misreading
of which byte is which.**

1. **There is a closed loop, and it is bank0 `0x8B14` together with block five
   of `0x8931`** — two routines, not one, that are two instantiations of the
   same controller over the same two integrator bytes. §1, §2.
2. **There are two error terms and they do compose**, CPU first and GPU
   unconditionally after it, in one pass. Not alternatives, not selected by a
   mode bit. §3.
3. **The setpoint is not `0x043E` and never was.** `0x043E` is `CPU_TEMP`, the
   *measured* value, `status: confirmed-working` in
   `ec/annotations/registers.yaml`. The setpoint is a **byte in the fan-curve
   table, indexed by the integrator itself** — which is what makes a fan curve
   a curve and not a comparison against a constant. §4.
4. **The one row §6 flags as `basis: inferred` is now `hand-decoded`,** and
   both halves of its comment were wrong: `0xBC4F` copies two bytes and
   computes no offset at all. §5.

What this does **not** do is settle what the curve entries mean in degrees, or
whether the loop is the one running on the machine — §6 says so plainly and
names the two issues that would.

## 1. The loop, and where it lives

`0x8931` is a 474-byte gate over five blocks. Block five is entered at
`0x8A25` behind two enable bits, and its own row already said what it could
not decode:

> Block five … is a state machine on XDATA `0x0460` that steps it up or down
> against CPU_TEMP and XDATA `0x09E4` … Which blocks run is decided by those
> enable bits alone; **what the thresholds and the `0x0460` ramp govern is not
> decoded.**

That gap is this write-up. The block is `0x8A25`–`0x8B11`, and the `ljmp
0x8C46` at `0x8B11` hands off to the ramp that publishes the result.

The thing the row did not say is that the same controller appears **twice**.
`bank-call-targets.csv` records exactly two `ljmp`s to `0x8B14`, at `0x8A2C`
and `0x8A36` — and those are the *two failed enable-bit arms* of block five's
own gate:

```
8A25     90 07 41 mov      DPTR, #0x741      ; AP_OEM
8A28     e0 - -   movx     A, @DPTR
8A29     20 e0 03 jb       0xe0, 0x8a2f      ; bit 0 clear -> 0x8A2C
8A2C     02 8b 14 ljmp     0x8b14            ;   ... the OTHER controller
8A2F     90 07 c6 mov      DPTR, #0x7c6      ; AP_OEM_6
8A32     e0 - -   movx     A, @DPTR
8A33     20 e2 03 jb       0xe2, 0x8a39      ; bit 2 clear -> 0x8A36
8A36     02 8b 14 ljmp     0x8b14            ;   ... the OTHER controller
8A39     90 04 60 mov      DPTR, #0x460      ; block five proper
```

`0x8B14` is seeded in `ec/decompiled/index.csv` at 306 bytes, which is exactly
`0x8B14`–`0x8C45`, and it ends on `0x8C45 movc A, @A+DPTR` — the last byte
before `0x8C46`. Both controllers therefore converge on the same publisher,
and neither is reached by a call: they are the two arms of one branch.
`bank-relative-branch-targets.csv` records no branch naming `0x8B14` either, so
by the committed scans these two `ljmp`s are its only entries. That is what
this method found, not a claim that no other entry exists.

**What the two differ in is where the curve table lives, not what the loop
does.** `0x8B14` reads its setpoints out of **CODE**, through the XDATA pointer
pair at `0x0A47`/`0x0A48`; block five reads them out of the **XDATA `0x0F00`
page**. Everything else — the integrator bytes, the error terms, the direction,
the publish — is the same shape in both.

| | block five (`0x8A25`) | `0x8B14` |
|---|---|---|
| setpoint table | XDATA `0x0F00 + n` | CODE, via XDATA `0x0A47` |
| threshold table | XDATA `0x0F10 + n` | CODE, via XDATA `0x0A47` |
| CPU integrator | XDATA `0x0460` | XDATA `0x0460` |
| GPU integrator | XDATA `0x0468` | XDATA `0x0468` |
| publishes to | `0x8C46` | falls into `0x8C46` |
| entered when | both enable bits **set** | either enable bit **clear** |

## 2. Per-site reading of the integrator

The controller is easiest to read in `0x8B14`, where the two arms are spelled
out. Both arms of it open the same way — read `0x0460`, subtract 3, and branch
on the result:

```
8B14     90 04 60 mov      DPTR, #0x460
8B17     e0 - -   movx     A, @DPTR
8B18     d3 - -   setb     CY
8B19     94 03 -  subb     A, #0x3          ; A - 3 - 1: carry set below 4
8B1B     50 6b -  jnc      0x8b88           ; >= 4 -> the plain arm
```

`setb CY` before the `subb` is the same idiom `0xBEAA` uses to subtract `0x33`
rather than `0x32`; here it makes the test "is the integrator at least 4".
Below 4 the controller runs the **dwell** arm, which is the interesting one.

### 2a. The dwell arm — a rate limit, not just a threshold

```
8B1D     90 0a 47 mov      DPTR, #0xa47      ; the XDATA pointer pair
8B20     12 b9 87 lcall    0xb987            ;   DPTR <- that pair, big-endian
8B23     12 bc e9 lcall    0xbce9            ;   DPTR <- the CODE pointer inside it
8B26     c0 83 - -   push   DPH
8B28     c0 82 - -   push   DPL              ;   save the table pointer
8B2A     90 04 60 mov      DPTR, #0x460
8B2D     e0 - -   movx     A, @DPTR         ;   A <- the integrator
8B2E     d0 82 - -   pop    DPL              ;   DPTR <- table + integrator
8B30     d0 83 - -   pop    DPH
8B32     12 bb 5e lcall    0xbb5e            ;   A <- the setpoint byte
8B35     fd - -   mov      R5, A
8B36     90 04 3e mov      DPTR, #0x43e
8B39     e0 - -   movx     A, @DPTR         ;   A <- CPU_TEMP
8B3A     d3 - -   setb     CY
8B3B     9d - -   subb     A, R5            ;   the error term
8B3C     40 19 -  jc       0x8b57            ;   too cold -> the down arm
```

`0xBB5E` adds the integrator into the table pointer and reads a CODE byte:
`add A, DPL` at `0xBB5E`, then — with no `ret` of its own, so the byte-scan
seeding splits it — `mov DPL,A` / `addc A,DPH` / `mov DPH,A` / `movc A,@A+DPTR`
/ `ret` at `0xBB60`. That is the whole of "the setpoint is a lookup keyed by the
integrator", and it is why the answer to the issue's "is `0x043E` the setpoint"
is no: `0x043E` is the right-hand operand at `0x8B39`, and the left-hand one
came out of a table. `0xBCE9` is the other half of the same idea one step
earlier — it reads a big-endian CODE pointer out of the table and leaves it in
DPTR, which is why the pair at `0x0A47` is a pointer to a pointer.

**That pointer-to-a-pointer is two dereferences, and the census splits each of
the two calls in half.** `0xB987` is seeded in `index.csv` at two bytes —
`movx A,@DPTR` / `mov R6,A`, an XDATA read — but it has no `ret` of its own, so
execution runs on into `0xB989 finish_dptr_be16_load` (seeded at seven bytes,
`0xB989`–`0xB98F`) and the first `ret` after `0xB987` is that `0xB98F`. So the
XDATA byte is not left dead in R6 for `0xBCE9` to overwrite: the run-on consumes
it at `0xB98D mov DPH,R6`, and what `lcall 0xB987` returns with is DPTR holding
the XDATA pair. `0xBCE9` splits the same way, at five bytes and then
`0xBCEE dptr_from_code_be16` — the second `movc A,@A+DPTR`, `mov R7,A`,
`mov DPL,A`, `mov DPH,R6` and the `ret` at `0xBCF4`. Read as whole routines the
path is therefore XDATA `0x0A47`/`0x0A48` → a CODE address → the big-endian
CODE pair at that address, which is the table `0xBB5E` indexes. This is worth
setting out because taking either seeded entry for the whole routine is what
makes the XDATA load look dead and the pair look like a CODE address, and
`disasm8051.py` over the image is what shows both run-ons.

The same address in CODE is not what is read here, and the distinction is not
subtle once stated: `0x8B1D` loads DPTR with `0xa47` for a **`movx`**, so DPTR
addresses XDATA. The CODE bytes at `0x0A47` are a different address space, and
reaching them would take a `movc` with DPTR still at `0x0A47`; there is no
`movc` between `0x8B1D` and the `push` at `0x8B26`, and `0xB987` has already
moved DPTR off `0x0A47` by then.

The error term is `CPU_TEMP - setpoint`, computed with the carry preset, and
the branch is on the borrow. Too cold (`jc` taken) goes to `0x8B57`; too hot
falls through to `0x8B3E`:

```
8B3E     12 bc 5f lcall    0xbc5f            ; 0x09E4++ , A <- the new value
8B41     20 e7 03 jb       0xe7, 0x8b47
8B44     74 80 - -   mov    A, #0x80
8B46     f0 - -   movx     @DPTR, A         ; saturate at 0x80
8B47     90 04 60 mov      DPTR, #0x460
8B4A     e0 - -   movx     A, @DPTR
8B4B     64 03 -  xrl      A, #0x3
8B4D     70 1e -  jnz      0x8b6d
8B4F     90 09 e4 mov      DPTR, #0x9e4
8B52     74 ff - -   mov    A, #0xff
8B54     f0 - -   movx     @DPTR, A         ; at 3, force 0xFF
8B6D     12 be aa lcall    0xbeaa            ; (0x09E4 & 0x7F) - 0x33
8B70     40 4a -  jc       0x8bbc            ; not yet -> do not move
8B72     e0 - -   movx     A, @DPTR
8B73     90 04 60 mov      DPTR, #0x460
8B76     30 e7 05 jnb      0xe7, 0x8b7e      ; direction = bit 7 of 0x09E4
8B79     e0 - -   movx     A, @DPTR
8B7A     04 - -   inc      A
8B7B     f0 - -   movx     @DPTR, A         ;   up
8B7E     e0 - -   movx     A, @DPTR
8B7F     14 - -   dec      A
8B80     f0 - -   movx     @DPTR, A         ;   down
8B81     e4 - -   clr      A
8B82     90 09 e4 mov      DPTR, #0x9e4
8B85     f0 - -   movx     @DPTR, A         ; clear the dwell counter
```

**`0x09E4` is the rate limit, and bit 7 of it is the direction.** `0xBC5F`
increments it and returns the new value; the integrator only moves once
`0xBEAA` reports `(0x09E4 & 0x7F) >= 0x33`, i.e. after 51 ticks in the same
direction. The counter is then zeroed at `0x8B85`. Bit 7 survives the `& 0x7F`
precisely because it carries the sign, and it is what `jnb 0xe7` at `0x8B76`
tests to pick `inc` over `dec`.

The two saturations are worth naming because they are what keeps a wrap from
becoming a direction flip: `0x8B41`–`0x8B46` forces `0x80` whenever bit 7 of
the value `0xBC5F` returned is clear — `jb 0xe7, 0x8b47` skips the store only
when it is set, so this is every increment landing below `0x80` and not the
`0xFF`→`0x00` case alone — and `0x8B4B`–`0x8B54` forces `0xFF` when the
integrator is sitting at exactly 3, which is the top of the dwell arm.

### 2b. The plain arm

At `0x0460 >= 4` the controller skips the dwell machinery entirely and steps
on every pass through the same comparison — `0x8B88` for the CPU, identical in
shape, ending `0x0460--` at `0x8BBA`. Block five has the same fork at
`0x8A40`, where `0x0460 >= 4` leaves for `0x8A98`.

So the integrator is **rate-limited near the bottom of its range and free near
the top**, which is the shape you would expect of a curve that is meant to
stop hunting once it has climbed out of the quiet band, and it is a reading of
these instructions rather than a conclusion about intent.

## 3. Two error terms, and they compose

This is issue item 2, and the answer is that the CPU and GPU terms are **not
alternatives**. Block five runs the CPU integrator to completion at `0x8ABD`
and then runs the GPU integrator unconditionally after it:

```
8ABD     90 04 60 mov      DPTR, #0x460      ; --- CPU half ends, GPU begins
8ACF     90 04 68 mov      DPTR, #0x468
8AD2     e0 - -   movx     A, @DPTR
8AD3     24 30 -  add      A, #0x30
8AD5     f5 82 -  mov      DPL, A
8AD7     e4 - -   clr      A
8AD8     34 0f -  addc     A, #0x0f
8ADA     f5 83 -  mov      DPH, A           ; DPTR = 0x0F30 + [0x0468]
8ADC     d3 - -   setb     CY
8ADD     12 bd f2 lcall    0xbdf2            ; GPU_TEMP - that byte
8AE0     40 08 -  jc       0x8aea
8AE2     90 04 68 mov      DPTR, #0x468
8AE6     04 - -   inc      A
8AE7     f0 - -   movx     @DPTR, A         ; GPU integrator up
8AEA     90 04 68 mov      DPTR, #0x468
8AEE     24 40 -  add      A, #0x40         ; the other threshold band
8AF7     c3 - -   clr      CY
8AF8     12 bd f2 lcall    0xbdf2
8AFB     50 06 -  jnc      0x8b03
8AFD     90 04 68 mov      DPTR, #0x468
8B01     14 - -   dec      A
8B02     f0 - -   movx     @DPTR, A         ; GPU integrator down
8B03     90 04 68 mov      DPTR, #0x468
8B07     24 50 -  add      A, #0x50
8B09     f5 82 -  mov      DPL, A
8B0B     e4 - -   clr      A
8B0C     34 0f -  addc     A, #0x0f
8B0E     f5 83 -  mov      DPH, A           ; DPTR = 0x0F50 + [0x0468]
8B10     e0 - -   movx     A, @DPTR
8B11     02 8c 46 ljmp     0x8c46           ; A <- the GPU duty
```

`0xBDF2` is `gpu_temp_minus_xdata_byte`: it reads the byte at the caller's
DPTR, subtracts it from `GPU_TEMP` (`0x044F`) and returns. So the GPU error
term is built at `0x8ADD` and `0x8AF8` against **two different threshold
bands**, `0x0F30 + n` and `0x0F40 + n` — the up-threshold and the
down-threshold — which is a hysteresis band rather than a single comparison.
The CPU half has the same pair in the other controller: `0xBB5E` against the
first table (`0x8B32`, `0x8B9D`, `0x8BF1`) and `0xBABF` against the second
(`0x8B57`, `0x8BB1`).

Both error terms drive **different integrator bytes** — `0x0460` for CPU,
`0x0468` for GPU — and both integrators index **different table pages**. That
is the answer to "which integrator each drives": one each, and neither is
shared.

### 3a. `0xBB56` against `0xBBDE`: ordered, and not from the loop

The issue asks whether the CPU and GPU threshold routines are alternatives
selected by a mode bit. **They are not called from the loop at all.**
`call-graph-callees.csv` gives `0xBB56` one inbound `lcall` and `0xBBDE` two,
and `bank-call-targets.csv` names all three sites: `0xB6F7 → 0xBB56`,
`0xB703 → 0xBBDE`, `0xB51A → 0xBBDE`. **They are not all in one routine.** Two
are inside `0xB5D3` (`ec/decompiled/index.csv` seeds it at 323 bytes,
`0xB5D3`–`0xB715`) and the third is inside `0xB4A8` (266 bytes,
`0xB4A8`–`0xB5B1`), so this write-up reads two chains, not one.

The `0xB5D3` chain is straight-line in code order:

```
B6F4     74 07 -  mov      A, #0x7
B6F6     c3 - -   clr      CY
B6F7     12 bb 56 lcall    0xbb56           ; CPU band, index 7
B6FA     50 3a -  jnc      0xb736
B700     74 08 -  mov      A, #0x8
B702     c3 - -   clr      CY
B703     12 bb de lcall    0xbbde           ; GPU band, index 8
B706     50 2e -  jnc      0xb736
B70E     74 09 -  mov      A, #0x9
B710     c3 - -   clr      CY
B711     12 bd a6 lcall    0xbda6           ; a third band, index 9
B714     50 20 -  jnc      0xb736
```

**A gate chain, in code order, CPU before GPU, each `jnc`-guarded and each
jumping to the same `0xB736` exit.** So the ordering is fixed by the fallthrough
structure, not selected: there is no mode bit choosing between them, and the
`mov A, #0x7` / `#0x8` / `#0x9` before each call is an **index into the same
CODE table**, which is a third way the curve is keyed besides the two the loop
uses. `0xB5D3` reaches this chain from `0xB6C2 jc 0xB6E8`, and `0xB5D3`'s own
row is `FUN_CODE_b5d3` — unnamed, and not what §6 grouped.

The `0xB4A8` chain has the same shape over a different index pair, which is why
the answer to issue item 2 does not depend on picking one of them:

```
B50E     e4 - -   clr      A
B50F     12 bb 55 lcall    0xbb55           ; CPU band, index 0 (0xBB55 is 0xBB56's setb CY)
B512     50 0e -  jnc      0xb522          ;   within band -> carry clear, carry on
B518     74 01 - -   mov      A, #0x1
B51A     12 bb de lcall    0xbbde           ; GPU band, index 1
B51D     50 03 -  jnc      0xb522
B51F     02 b5 d2 ljmp     0xb5d2           ;   both bands exceeded -> 0xB5D2 is a bare ret
```

CPU before GPU again, at indices 0 and 1 rather than 7 and 8, and both `jnc`s
leave to the same `0xB522`. **So `0xBBDE` has a caller the `0xB5D3` ordering
argument does not account for, and it points the same way:** in both routines the
CPU test is reached first, and passing it skips the GPU test. What is *not*
established here is what selects between the two chains, or whether either
composes with the loop: `0xB4A8`'s exceed-both path returns through the bare
`ret` at `0xB5D2`, so what reaches that routine — and how it relates to the
`0xB5D3` chain — is not resolved here. Issue item 2's "compose or are they
alternatives" is therefore answered for each chain's internal ordering and not
for the relationship between them.

This is the §7 handoff, and it is a partial one: the mode bit governs **block
selection at `0x8931`**, which is a different question from these ladders'
selector. `ec/annotations/subsystems.md` §7 lists `0x95DD` and `0x9D9B` as the
unreached sites for that question, and this write-up does not reach either.

## 4. Reconciling `0x0460`-`0x046F` before using it as an output

Issue item 3 asks that the `0x0460`-`0x046F` readings be reconciled before
`0x0460` is used as a loop output, and the plan's answer is that it is
reconciled. It is, and the reconciliation is worth stating because it is what
makes the rest of this write-up usable.

`0x0460` and `0x0468` are **ramp indices**, not tachometer readings, and
nothing here rests on the tachometer reading of that page:

- `registers.yaml` carries both as `present-untested` with **no upstream name**,
  and both notes record the same writer list — `0x87C1`/`0x87CD` plus the
  read-modify-writes at `0x8AA7`, `0x8AB7`, `0x8BA9`, `0x8BB6` and their GPU
  twins, which are the integrator steps read here.
- Their *use* is now decoded: each is the index into its own pair of threshold
  tables and its own duty table, and each is incremented and decremented by
  exactly the comparisons above.
- The page `0x0460`-`0x046F` is still called the fan-tachometer bytes by
  `windows/tools/manual_fan_ctrl_probe.py` and by
  `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`, and ECSpec puts
  the RPM pairs at `0x0464`/`0x0465` and `0x046B`/`0x046C` inside that same
  page. **That conflict is untouched by this write-up and issue #245 stays
  open.** What is settled is narrower and is about `0x0460` and `0x0468`
  specifically: as ramp indices they are read-modify-written by the loop and
  never by a tachometer path in anything read here. The bytes at `0x0464`
  and `0x0465` are a different question and are not answered here.

The neighbouring `0x0461` and `0x0469` are **duty targets**, and they are not
in conflict with anything: `0x8C46`'s existing row already ramps `0x1804` and
`0x1809` toward them, and `0x8ABD`–`0x8ACE` is what fills `0x0461` — the byte
at `0x0F20 + [0x0460]`, which is the CPU's share of the curve. So the chain
is: **temperature → error → integrator → curve lookup → duty target**, and
`0x0461`/`0x0469` are where the curve's output lands before the ramp.

## 5. `0xBC4F`: `inferred` corrected, and the comment was wrong too

Issue item 4 asks for the one §6 row with `basis: inferred` to be confirmed or
corrected. It was wrong on both counts, and the committed listing reads:

```
BC4F     90 08 e6 mov      DPTR, #0x8e6
BC52     e0 - -   movx     A, @DPTR
BC53     ff - -   mov      R7, A
BC54     a3 - -   inc      DPTR
BC55     e0 - -   movx     A, @DPTR
BC56     90 0a 47 mov      DPTR, #0xa47
BC59     cf - -   xch      A, R7
BC5A     f0 - -   movx     @DPTR, A
BC5B     a3 - -   inc      DPTR
BC5C     ef - -   mov      A, R7
BC5D     f0 - -   movx     @DPTR, A
BC5E     22 - -   ret
```

**It copies `0x08E6` and `0x08E7` into `0x0A47` and `0x0A48` big-endian, and
returns nothing in A.** The `xch A, R7` at `0xBC59` is what puts `0x08E6`
(saved in `R7` at `0xBC53`) into the low half and `0x08E7` into the high half
of the pair. **No instruction does arithmetic on either value** — the only two
`inc`s are `inc DPTR` at `0xBC54` and `0xBC5B`, which walk the destination
pointer across the pair and are not an offset. The `base + 0x00` the old
comment carried was read off the `0x888D` call site, where
`manual-fan-ctrl-0751.md` §6 annotates selector 2 as `base + 0x00`, and that
annotation describes the *selector*, not the routine.

So it is the no-argument twin of `0xBCCB store_be16_of_08e6_and_arg_to_0a47`,
which is the same shape with the low byte taken from the caller's A instead of
from `0x08E7`. `0xBCCB` is what `0x888D` and block four call; `0xBC4F` is what
`0x888D` calls for selector 2 and block four calls at `0x8A22`. Between them
they are the two ways `0x08E6` and the byte above it become the pointer pair
at `0x0A47`/`0x0A48`.

**Those two addresses are XDATA on both sides, and that is what links this
routine to `0x8B14`.** `0x8B1D` sets DPTR to `0x0A47` and `lcall 0xB987` reads
it with `movx`, so the pair `0xBC4F` writes is the pair `0x8B14` reads; §2a
spells out that read and the CODE dereference that follows it. The routine §6
flagged as the weakest row in the group is therefore on the path that decides
where this controller reads its setpoints from. The same pair has a second
reader, §3a's ladder, which loads it with `0xB93D load_dptr_be16_from_xdata`
at `0xB6EE`/`0xB6F1` and then indexes CODE with `0xBB56`'s `movc` — a
different consumer reached a different way, and worth naming so the pair is not
read as `0x8B14`'s alone.

**Two fields of that row are deliberately not changed, and it is worth saying
why here rather than only in the row.** The *name* is left as it is: renaming
it in one row would fork every generated CSV and the decompiled `.c` header
off it until the next `--mode rebuild-project`. The `type` still reads `math`
where its twin reads `writer`, which now understates it — but that column
drives the grouping rule, so changing it moves the row between groups in the
derived `ec/annotations/function-groups.csv`, and regenerating that file
rewrites a dozen rows belonging to other branches. Both are a separate edit
for whoever next regenerates it, and neither affects the reading above, which
rests on the instructions rather than on the annotation's own bookkeeping.

**The generated files still carry the pre-correction text, and that is worth
saying rather than leaving to be discovered.** `ec/decompiled/index.csv` still
records the `BC4F` row as `basis` `inferred` with the
`manual-fan-ctrl-0751.md` evidence, and `ec/decompiled/bank0/BC4F.c` still
carries the retracted "annotated in the listing as yielding base + 0x00" with
`basis: inferred` and nothing beside it. Both are generated from
`ghidra-functions.csv` and hand-editing them is out (CLAUDE.md, "The editable
surface is a CSV, not the project"), so a reader who opens the `.c` rather than
the annotations sees the claim this section retracts, standing alone, until the
next `--mode rebuild-project` export picks the corrected row up. The retraction
itself lives in the annotations CSV and here.

`0x0A47` is `MAILBOX_PUBLISH_VALUE` in `registers.yaml`, and its note is
unchanged by this: nothing here is a payload, and the byte's 121 sites are
still far too many to characterise from one write.

## 6. What this does not establish

Plainly, and in the order a reader is most likely to over-read it:

- **This is a static reading of `GMxMGxx_11.800`.** Nothing was run on the
  machine. Whether these two controllers are the ones executing, and what
  fraction of passes reach block five at all, is not established — a branch
  that exists is not a branch that is taken.
- **The curve entries' units are not established.** The field names come from
  the vendor side (`windows/vendor-ec-map.md`) and are not proof the EC reads
  the bytes that way; `docs/findings/ec-fan-table-defaults.md` already carries
  that caveat and it is unchanged.
- **Issue #245 stays open**, as §4 says.
- **Issue #380 (the live `0x0751` comparison) and #381 (the
  `RefreshDefaultFanTable` capture) are the confirmation route**, which is why
  this issue takes no `needs-hardware-test` label: nothing here needs the
  machine to be *written* to, only to be *confirmed*, and that is what those
  two are for.
- **`0x09E4` has no entry in `registers.yaml`** and none is added — its use is
  read here, but a use is not a status, and inventing a `status:` value is the
  thing the vocabulary exists to prevent. The two rules that govern it (51
  ticks, bit 7 is the direction) are the finding; the byte's identity is not.
- **§7's `0x95DD` and `0x9D9B` stay unreached**, as §3a says.

## 7. What a driver would need, and does not get here

The mission's first motivating example for this group was "to change a fan
curve", and this write-up is the first thing in the tree that says what one
*is* on the EC side: two integrator bytes, two error terms against
`CPU_TEMP` and `GPU_TEMP`, a setpoint read from a table indexed by the
integrator, a 51-tick dwell near the bottom of the range, and a published
duty at `0x0670`.

That is enough to say what a Linux fan-curve interface would have to touch,
and **not enough to write one**, for two reasons that are about evidence and
not about effort. The curve tables' **location and format differ between the
two controllers** (§1), so "the curve" is not one thing until the enable bits'
runtime values are known. And the **units of every curve byte are
unestablished** (§6). A driver that wrote `0x0460` on the strength of this
write-up alone would be guessing at both.

The nearest thing to a next step that this write-up hands over is the pair of
tables behind the XDATA pointer pair at `0x0A47`/`0x0A48`, since `0x8B14`'s
whole setpoint path goes through it and `0xBC4F` is one of the two writers of
it.

## 8. Reproducing this

Every address above is a line in a committed listing, and the suite checks
that each cited instruction is still the instruction this write-up says it is:

```console
$ python3 -m unittest discover -s ec/tools -p 'test_fan_ramp_loop.py'
$ bash tools/run-tests.sh
```

The `0xBB56`/`0xBBDE` ordering claim is the one that rests on a decoded window
rather than a Ghidra listing, so it is checked against the image as well as
against `B5D3.asm`, with the alignment caveat `disasm8051.py` states for
itself:

```console
$ python3 ec/tools/disasm8051.py --at 0xB6F0 -n 24 ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/disasm8051.py --at 0x8B14 -n 12 --converge ec/firmware/GMxMGxx_11.800
```

`--converge` reports how many nearby anchors decode onto the offset; it is
evidence about framing, not proof of it, which is why the `0x8B14` readings in
§2 are cited to `ec/decompiled/bank0/8B14.asm` and the linear decode is only
the cross-check.
