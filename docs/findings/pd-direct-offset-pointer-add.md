# The PD image keeps a 16-bit base in direct `0x0D`/`0x0E`: a literal at init, rewritten by an 81-caller add-and-store-back (issue #69)

**Read the headline before anything else.** Everything below is about the
`ITE8850-PD` image at file `0x20000` — a second, self-contained 8051 program
with its own XDATA map and its own internal-RAM direct space. It says
**nothing** about the EC's `0x0D`/`0x0E`, which are a different program's
variables in a different program. `registers.yaml` is untouched by this work and
deliberately so: direct `0x0D`/`0x0E` here are not EC XDATA registers, no
register status changed, and nothing below is a reason to change one. All of it
is static analysis of the committed `ec/firmware/GMxMGxx_11.800`. No register
was read back, no write was attempted, nothing ran on the machine.

`ec/annotations/pd-index-geometry.md` §2.2 removed `0x9A71` from the index-helper
family and left the seven instructions it tail-calls decoded only as far as
showing them. In one line: **`0x0D`/`0x0E` hold a running 16-bit base in the PD
image's internal RAM. `0x1253` adds it to DPTR without keeping the result, and a
sibling entry adds it and writes the result back — so the value is set to a
literal once at init and advanced from then on.** It is not a fixed relocation
constant, and it is not a per-call scratch pointer. The register-bank
explanation, the third of the issue's three, is tested in §4 and does not hold
either.

## 1. Reproducing this

Every figure below comes from one of these, from the repository root:

```console
$ python3 ec/tools/disasm8051.py --self-test
self-test passed: both charge-profile-flow.md windows decode identically, all 4 relative-branch sites resolve as hand-decoded, and all 11 bit-form sites decode as transcribed

$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
self-test passed: the helper bodies and terms match pd-xdata-overlap.md 3, the four 0x04A6 sites sit where trace_xdata_refs.py puts them, the four 0x5E/0x77 addresses sit where ec-0x07d0-sites.md 4 puts them, and all six CSVs regenerate unchanged (PD image at file 0x20000)

$ python3 ec/tools/pd_direct_offset_sites.py ec/firmware/GMxMGxx_11.800
0x1253 adds the 16-bit pair in direct 0x0d/0x0e to DPTR.  Over the pd-image region
0x0000-0xFFFF, by byte scan:

  direct-form writers       11  bank-independent; each names the cell
  register-form writers   2572  conditional on PSW.RS = 1
  lcall/ljmp callers        33  lcall 30, ljmp 3

The same three scans over the main EC, which is a different program with its
own direct space -- so these numbers are not the PD image's and are not an
extension of them:

  common   direct   8   register   854   callers   0
  bank0    direct   6   register   791   callers   0
  bank1    direct   9   register   809   callers   0

ec/annotations/pd-direct-offset-sites.csv holds one row per candidate above, with its framing counts
and its note.  `--writers`, `--register-writers` and `--callers` print the three
censuses; `--base` runs the arithmetic `0x9A71` performs for a named site; and the
write-up is ../../docs/findings/pd-direct-offset-pointer-add.md.

$ python3 ec/tools/pd_direct_offset_sites.py ec/firmware/GMxMGxx_11.800 --check
ec/annotations/pd-direct-offset-sites.csv: this run reproduces it byte for byte (2617 lines)
```

Console blocks in this file are transcribed whole unless a `...` line marks an
elision, and each such line says what stands behind it.

`--writers` prints the direct-form census with its framing evidence,
`--register-writers` the register-form one and the PSW population that decides
its alias, `--callers` the two call forms counted apart, and `--base SITE` the
DPTR arithmetic `0x9A71` performs for a named site. `--csv` writes
`ec/annotations/pd-direct-offset-sites.csv`, the row-per-candidate census every
number below is measured from.

## 2. The two entries, and what makes them different

`0x1253` is the routine §2.2 already transcribed:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x1253; pd 7' /tmp/pd.bin
            0x00001253      e50e           mov a, 0x0e
            0x00001255      2582           add a, dpl
            0x00001257      f582           mov dpl, a
            0x00001259      e50d           mov a, 0x0d
            0x0000125b      3583           addc a, dph
            0x0000125d      f583           mov dph, a
            0x0000125f      22             ret
```

(`r2` here is `radare2 -a 8051` against `/tmp/pd.bin`, which is
`dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1`; the
trailing memory-hint column is stripped for width, as
`pd-index-geometry.md` line 129 already does.)

`0x0E` is the low half and `0x0D` the high — the order is the routine's own, and
it is *not* the little-endian order the two addresses' spellings suggest. That
matters for §5, where the add carries out of the low half.

**Thirty-six bytes lower there is a second entry that does the same add and then
writes the answer back**, and `0x1253` is the routine §2.2 already named. The
two are adjacent, not nested: the block below ends in its own `ret` at `0x1252`,
and `0x1253` is a separate entry whose body is the add and nothing else.

**None of the reading below is new to the repository, and this section is not
the first place it is written down.** `ec/annotations/ghidra-functions.csv:1405`
already names the entry `add_dptr_to_word_0d0e_ea_guard`, and its comment is the
conclusion of this section: "Adds the 16-bit value in DPTR to the direct
internal-RAM word at 0x0E (low byte) and 0x0D (high byte). If the new high byte
equals the old one, only 0x0E is stored; otherwise EA (direct bit 0xAF) is
cleared around the two-byte store and set again if it had been set, so the pair
is not seen half-updated by an interrupt." `ec/decompiled/pd/122F.asm` carries
the listing reproduced below and `122F.c` its decompile, which spells the two
cells `BANK1_R5`/`BANK1_R6` — the bank-1 aliasing §4 comes back to. The sibling
row `ghidra-functions.csv:1406` is `add_word_0d0e_to_dptr`, commented "Nothing
is written to memory", which is the other half of the contrast. The listing is
reproduced here so those rows and this write-up can be read against each other;
**it is not claimed as new, and this section's contribution is the counts
below, not the store-back reading.**

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2122F --runtime 0x122F -n 12
0x122f  e50e     mov  a,0x0e
0x1231  2582     add  a,0x82
0x1233  f582     mov  0x82,a
0x1235  e50d     mov  a,0x0d
0x1237  3583     addc a,0x83
0x1239  f583     mov  0x83,a
0x123b  b50d04   cjne a,0x0d,0x1242
0x123e  85820e   mov  0x0e,0x82
0x1241  22       ret
0x1242  10af06   jbc  ie.7,0x124b
0x1245  85820e   mov  0x0e,0x82
0x1248  f50d     mov  0x0d,a
0x124a  22       ret
```

Read as one routine with three exits, it is a textbook atomic 16-bit store:

- **The add.** `0x122F`-`0x1239` is `0x1253`'s body verbatim: DPTR becomes
  DPTR + (0x0D:0x0E).
- **The high-byte test.** At `0x123B`, A holds the add's *new* high byte and
  `0x0D` still holds the *old* one, because the store has not run yet. If they
  are equal the high half has not changed, so the short path at `0x123E` stores
  the low half only and returns — which is why the compare is against `0x0D`
  and not against a constant.
- **The interrupt bracket.** Otherwise both halves must change together, so
  `0x1242 jbc ie.7,0x124b` clears EA and branches, `0x1245`-`0x124A` does the
  two stores, and `0x124B`-`0x1252` (the `mov 0x0e,0x82 ; mov 0x0d,a ; setb
  ie.7 ; ret` tail not shown above) re-sets EA on the way out. `jbc` is
  "jump if set, then clear", so the fall-through at `0x1245` is the case where
  EA was already clear and the `setb` is not needed.

So the two entries differ in one respect and one only: **`0x122F` folds the
add's result back into the pair, `0x1253` does not.** Both advance DPTR by the
same 16-bit value, and §3 is what the second entry's callers are counted
against. That difference is the whole of the issue's "is the value set once or
per call" question, and §3 answers it from the call counts.

**The two call counts are different censuses of different populations, and the
repository already carries the smaller one.** This file reports 81 byte-pattern
sites reaching `0x122F` and 33 reaching `0x1253`; `call-graph-callees.csv:147`
gives `pd,122F` an `inbound` of 20 (`lcall` 13, `ljmp` 7) and `:802` gives
`pd,1253` an `inbound` of 2 (`lcall` 2, `ljmp` 0). Neither number is an error
in the other. `ec/tools/call_graph.py` walks the committed `.asm` listings and
records a transfer only where the listing that carries it decoded one, so its
`inbound` is bounded twice over: by which functions the exporter recovered — 535
listings stand over the PD image's 64 KiB — and by each listing's own decoded
instruction stream. A byte scan has neither condition and takes every
`12 12 2f` in the region. The two agree exactly where they overlap, which is the
check that says they are counting the same thing at different depths:

```console
$ grep -oiE '\b(lcall|ljmp)\s+0x122f\b' ec/decompiled/pd/*.asm | wc -l
20
$ grep -oiE '\b(lcall|ljmp)\s+0x1253\b' ec/decompiled/pd/*.asm | wc -l
2
```

**The gap is 61 and 31 sites lying in parts of the region no committed listing
covers.** Which of those are calls and which are three bytes inside some other
instruction is not settled by the two counts against each other; §3's framing
column is the evidence for it, and `call_graph.py` cannot supply that evidence
because it never decodes those stretches as code at all.

## 3. The writer census

`ec/annotations/pd-direct-offset-sites.csv` has one row per candidate.
`--writers` prints the direct form:

```console
$ python3 ec/tools/pd_direct_offset_sites.py ec/firmware/GMxMGxx_11.800 --writers
  0x20514  0x0514  75 0d 27  mov  0x0d,#0x27      imm 0x27  frame 24/24  pick 0x001D (back 29)
  0x20517  0x0517  75 0e ff  mov  0x0e,#0xff      imm 0xff  frame 24/24  pick 0x001D (back 32)
  0x2123E  0x123E  85 82 0e  mov  0x0e,0x82                 frame 24/24  pick 0x1093 (back 61)
  0x21245  0x1245  85 82 0e  mov  0x0e,0x82                 frame 24/24  pick 0x1093 (back 68)
  0x21248  0x1248  f5 0d     mov  0x0d,a                    frame 24/24  pick 0x1093 (back 71)
  0x2124B  0x124B  85 82 0e  mov  0x0e,0x82                 frame 24/24  pick 0x1093 (back 74)
  0x2124E  0x124E  f5 0d     mov  0x0d,a                    frame 24/24  pick 0x1093 (back 77)
  0x2A5A9  0xA5A9  85 12 0d  mov  0x0d,0x12                 frame 1/24  pick 0x98E0 (back 6)
  0x2A5C8  0xA5C8  85 12 0d  mov  0x0d,0x12                 frame 1/24  pick 0x98DF (back 9)
  0x2B979  0xB979  f5 0e     mov  0x0e,a                    frame 0/24  pick 0x8007 (back 11)
  0x2E8A3  0xE8A3  f5 0e     mov  0x0e,a                    frame 0/24  pick 0x7D03 (back 4)
```

Eleven byte-pattern candidates over the region. **They are not eleven
writers**, and the split is the finding:

- **Two are the init literal**, at `0x0514`/`0x0517`, and they frame from every
  anchor in range. `0x0500`-`0x0512` is a cold-start sequence — clear internal
  RAM down from `0x7F`, then clear 8 pages of XDATA from `0x0000` — and the
  pair is set immediately after it, so the value **`0x27FF`** is what the pair
  holds before anything else runs. The load-bearing half of that sentence is
  *reset*, not *init-looking*, and it is `ec/annotations/pd-image.md` §2's
  vector table that supplies it: entry `0x00`, 8051 vector `reset`, target
  `0x0500`, target-is `c_startup_idata_clear`. Without that row this would be a
  guess from the shape of the bytes. That is the one resolved number in this
  file, and §5 is careful about what it resolves.
- **Five are the store-back block of §2**, `0x123E` through `0x124E`, also
  24/24. These *change* the value rather than initialise it.
- **Four are phantoms, named rather than dropped.** The framing column is why:
  `0xB979` and `0xE8A3` are reached by no linear anchor at all, and the `f5 0e`
  in each is the second and third byte of a `lcall 0xF50E` at `0xB978` and
  `0xE8A2` — the routine's own target address, not a `mov 0x0e,a`.
  `0xA5A9` and `0xA5C8` score 1/24 and each straddle the boundary between two
  adjacent calls: the `85` is the third byte of `lcall 0x9885`, and the `12 0d`
  that follows is the first two of `lcall 0x0D38`. **Every one of the four is a
  run of bytes inside call instructions**, which is what a byte scan cannot see
  and a framing count can. A tool that thresholded on `frame_onto` would have
  reported **seven** writers and dropped **all four** of these — a threshold at
  `frame_onto == 24` keeps the seven real writers and none of the phantoms,
  since these score `1/24` and `0/24`. That is the point rather than a
  counter-example: the framing count is what identifies them, and a filter is
  what would have thrown them away. `--self-test` states it the same way, "the
  other four are labelled, not dropped".

**`0x27FF` is therefore the value at reset and not a bound on the value.** Every
execution of the `0x122F` entry advances it by whatever DPTR held, and the
census counts 81 byte-pattern sites that reach it — the same entry the
committed `call-graph-callees.csv` counts 20 of, reconciled in §2:

```console
$ python3 ec/tools/pd_direct_offset_sites.py ec/firmware/GMxMGxx_11.800 --base 0x9B76
...
  it runs the add at 0x122F, 0x1253, then stores the low half out of DPTR at 0x123E, 0x1245, 0x124B and the high half out of A at 0x1248, 0x124E
  so the block folds the add's own result back into the pair: it rewrites the
  value, it does not just read it.  0x122f is called lcall 45, ljmp 36 -- 81 byte-pattern candidate(s),
  counted the way `--callers` counts and over- and under-counting the same way.
```

(The `...` stands for the command's opening block — the `0x9A71` framing and the
`0x27FF` candidate arithmetic §5 quotes — and for the paragraph between the two
kept lines.)

So the issue's three hypotheses resolve as: **a fixed relocation constant, no**
— `0x27FF` is overwritten by 81 call sites; **a per-call scratch pointer, no** —
the pair is not written at the `0x1253` call sites, and the 81 that do write it
are a different entry; **a register-bank artefact, no — but on a different basis
than this file first gave.** §4 originally dismissed it because no PSW write in
the region selected bank 1. That was a transposition of the two RS bits, and it
was wrong: two writes *do* select bank 1. What argues against the artefact
reading now is narrower — along the part of those two paths this method
follows, no R5 or R6 is written. The bank argument is withdrawn, not the
conclusion. What it is instead is a **running 16-bit base in internal RAM**: a
literal at reset, then a relocation the firmware maintains by folding DPTR into
itself, which is what makes `0x1253`'s 33 call sites cheap. That last reading is
an *inference* from the two facts above, and it is labelled as one: nothing in
the bytes names what the base is a base *of*.

## 4. The register-bank question, and the two windows it opens

The complication the issue does not mention is that in the 8051 direct space
`0x00`-`0x1F` is the four register banks, so `0x0D` and `0x0E` are R5 and R6
*of bank 1*. A `mov r5,#imm` therefore names direct `0x0D` only when
**PSW.RS = 1**, and a byte scan over the region finds 2,572 register-form
candidates against 11 direct-form ones — a factor of 234, which is why the two
have to be separate modes and separate `form` values in the table rather than
one grep for `0x0D`.

The question is therefore whether anything selects bank 1. **Two writes do.** RS0
is PSW.4 and RS1 is PSW.3 — RS0 is the low-order bit of the two-bit RS field,
so it has to sit at the lower bit position — so bank is `RS1*2 + RS0`, and
`#0x10` sets bit 4, which is RS0 alone: **bank 1**, the one whose R5 is direct
`0x0D`. Every PSW write in the region is accounted for by:

```console
$ python3 ec/tools/pd_direct_offset_sites.py ec/firmware/GMxMGxx_11.800 --register-writers
Register-form writers of R5/R6 in the pd-image: 2572 byte-pattern candidate(s).
These mean direct 0x0d/0x0e only under PSW.RS = 1, so none of them is a writer
until the bank at the site is known.  Both distributions below are over the whole region.

  framing        reached by all 24 anchors: 1251, by some but not all: 710, by none: 611
  PSW writes     21 byte-pattern candidate(s) -- bank 0: 7, bank 1: 2; RS not fixed: 12
  alias bank     1 is selected by 2 of them

  ... 2560 more, all of them in ec/annotations/pd-direct-offset-sites.csv
```

(The three `framing`/`PSW writes`/`alias bank` lines are the whole of the
summary the argument below uses. The command then prints one block per
candidate — twelve shown, 2,560 more by its own count — each carrying that
row's `note`, and closes on the line the `...` stands in for.)

Bank 0 in seven places, bank 1 in two, and twelve that fix nothing — ten
`pop psw` byte patterns, and `mov psw,r0` at `0x526D` (`88 d0`) and
`mov psw,@r1` at `0x59C1` (`87 d0`). `disasm8051.py` renders the second as
`db 0x87` because its mnemonic table starts the `mov direct,Rn` arm at `0x88`,
which `docs/findings/opcode-table-coverage.md` records among the opcodes that
fall through to `db 0x..` and gives the manual's name for; the byte is
unambiguous either way. **The two `mov psw,#0x10` sites are the two that
matter, and they are exactly the ones that select the aliasing bank.** They are
**two separate brackets**, not one, and each carries its own `mov dptr`
immediate:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x0094; pd 14' /tmp/pd.bin
            0x00000094      c0e0           push acc
            0x00000096      c0f0           push b
            0x00000098      c083           push dph
            0x0000009a      c082           push dpl
            0x0000009c      c0d0           push psw
            0x0000009e      75d010         mov psw, #0x10
            0x000000a1      900154         mov dptr, #0x0154
            0x000000a4      120050         lcall 0x0050
            0x000000a7      d0d0           pop psw
            0x000000a9      d082           pop dpl
            0x000000ab      d083           pop dph
            0x000000ad      d0f0           pop b
            0x000000af      d0e0           pop acc
            0x000000b1      32             reti

$ r2 -a 8051 -e scr.color=0 -q -c 's 0x00F0; pd 14' /tmp/pd.bin
            0x000000f0      c0e0           push acc
            0x000000f2      c0f0           push b
            0x000000f4      c083           push dph
            0x000000f6      c082           push dpl
            0x000000f8      c0d0           push psw
            0x000000fa      75d010         mov psw, #0x10
            0x000000fd      90015a         mov dptr, #0x015a
            0x00000100      120050         lcall 0x0050
            0x00000103      d0d0           pop psw
            0x00000105      d082           pop dpl
            0x00000107      d083           pop dph
            0x00000109      d0f0           pop b
            0x0000010b      d0e0           pop acc
            0x0000010d      32             reti
```

**Both of them are already committed and named, which is what makes them two
routines rather than two fragments of one.** They are the timer 0 and timer 1
interrupt vectors: `vector_wrapper_dp_0154` at
`ec/annotations/ghidra-functions.csv:1356` and `vector_wrapper_dp_015a` at
`:1358`, listed at `ec/decompiled/pd/0094.asm` and `00F0.asm`, and given those
vector entries by `ec/annotations/pd-image.md` §2 (`0x0B` timer 0 → `0x0094`,
`0x1B` timer 1 → `0x00F0`). The names are the immediates — `0x0154` and `0x015A`
are the CODE addresses the wrappers load — and that difference is the whole of
what separates the two brackets. What the two share is the
bracket shape and nothing else, and each carries **exactly one** `lcall` in its
whole 14 instructions, so the reading below rests on both listings:

**Each bracket runs one callee, `0x0050`, in bank 1**, whose body is
`lcall 0x10F1 ; ljmp 0x1229` (`ec/decompiled/pd/0050.asm`, named
`call_10f1_then_jmp_1229` in the same CSV). `0x10F1` reads a three-byte index
off the code stream into R3/R2/R1 and returns; `0x1229` moves R2:R1 into DPTR
and jumps through it — `ec/decompiled/pd/1229.c` carries Ghidra's "Could not
recover jumptable at 0x122e" and calls the target, so the destination is not
determined by this method. **Along the part of that path this method follows,
no R5 or R6 is written** — `0x10F1` writes R3/R2/R1 and `0x1229` writes
DPH/DPL, and that is the whole of it.

That is a statement about the followed path, not about the bank, and the
difference matters: the bank-1 window is open at both brackets and this scan
does not close it. The same is true of the other 2,570 candidates, and for a
stronger reason than the two brackets — **twelve of the 21 PSW writes leave RS
unfixed**, and only seven fix bank 0, so for 14 of the 21 a register-form
candidate's bank is not something this scan knows. The census's 2,572 rows are
candidates, and the bank column does not reduce them to non-writers.

**Three committed comments say `mov PSW,#0x10` selects register bank 1, and
they are right; an earlier reading in this file was the thing that was wrong.**
`ghidra-functions.csv:1356` (the `0x0094` forwarder) and `:1358` (the `0x00F0`
one) both describe their PSW write that way, and `pd-image.md:242` says the
same of the pair. RS0 is PSW.4 and RS1 is PSW.3, bank is `RS1*2 + RS0`, and
`0x10` sets RS0 alone. This file previously read the two bits the other way
round, carried the error into the tool that produced the table above, and then
proposed in §8 to correct those two rows — which would have replaced two
accurate committed findings with the error, and regenerated three decompiles to
carry it into their headers. **The rows need no change and the §8 item is
withdrawn.** The tool's `--self-test` had pinned the transposed values, so it
agreed with itself; the three committed rows are what caught it.

**This is bounded the way every count in this repository is bounded.** A `pop
psw` in a routine this method does not follow could bring RS = 1 in from off the
stack, and a byte scan cannot rule that out; the twelve "RS not fixed" writes
are where that would have to come from. Nor does this follow a bank switch into
a computed jump, which is what `0x1229` ends in. What is established is that
**two PSW writes found by this scan select bank 1, and that along the part of
their path this method follows, no R5/R6 is written** — a narrower claim than
"no register-form writer of the pair exists in this image", and the honest one.

## 5. The callers, and what `0x9A71` leaves in DPTR

`--callers` reports 33 candidates: **30 `lcall` and 3 `ljmp`**, counted apart
because a tail call is a different idiom. 26 of the 30 calls frame from every
anchor in range, and the four that do not — `0x95B7`, `0x9DBD` and `0xA6A8` at
22/24, `0x999B` at 23/24 — are printed with the count beside them rather than
filtered on it. All three tail calls frame fully, and one of them is `0x9A75`,
inside `0x9A71` itself.

**Zero in the main EC.** The same byte scan over `common`, `bank0` and `bank1`
finds no `lcall`/`ljmp 0x1253` in any of them, which is what
`ec/annotations/pd-image.md` says the region is — a separate program with its
own address space — now measured rather than assumed. The helper belongs to the
second program alone.

`0x9A71` is the store entry, and its two halves are worth separating because
`pd-xdata-overlap.md` §3.2's chain already resolved the first one:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9a71; pd 3' /tmp/pd.bin
        ╎   0x00009a71      f0             movx @dptr, a
        ╎   0x00009a72      900003         mov dptr, #0x0003
        └─< 0x00009a75      021253         ljmp 0x1253
```

- **What it stores through is not open.** The `movx @dptr,a` takes the DPTR it
  was handed, and §3.2's chain (`0x9DEC → 0x10BC → 0x998F → 0x9A99`, ending at
  that `movx`) already accounts for it. Nothing in this file revises that, and
  the `0x04A6` destination is resolved by §3.3's term arithmetic, not by
  anything here.
- **What it leaves in DPTR is `0x0003 + (0x0D:0x0E)`** — the add of §2, applied
  to an immediate, with the pair's low half added first and the carry taken into
  the high half. Under §3's init literal that is `0x0003 + 0x27FF = 0x2802`,
  and the sum carries out of the low half, which is why the routine is an add
  and not an `or`. **`0x2802` is a candidate, not an answer:** it holds only if
  no one of the 81 store-back sites has run since `0x0514`, and §3 says the
  bytes cannot say whether one has.
- **The returned pointer is used, and that much is settled.** The instruction
  after the call reads it:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x29DFA --runtime 0x9DFA -n 5
0x9dfa  ea       mov  a,r2
0x9dfb  f0       movx @dptr,a
0x9dfc  a3       inc  dptr
0x9dfd  eb       mov  a,r3
0x9dfe  129a71   lcall 0x9a71
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x29E01 --runtime 0x9E01 -n 4
0x9e01  e0       movx a,@dptr
0x9e02  c4       swap a
0x9e03  5407     anl  a,#0x07
0x9e05  1299b8   lcall 0x99b8
```

`0x9E01 movx a,@dptr` takes the DPTR `0x9A71` just built, byte-swaps it and
masks to three bits. **So the store entry's second pointer is not dead code**,
which is the question §2.2 left open and this closes at the strength of the
next instruction. *What the byte is used for is not resolved here* — a value read
back through a pointer whose value is not known, then reduced to three bits, is
not a decoded field. `disasm8051.py` decodes linearly and the repository has
deliberately not attempted control-flow recovery (`ec/README.md`, "toolchain
proven, not attempted"), so following what `0x99B8` does with it is that work
and not this issue's.

## 6. What this does not establish

- **Nothing about the EC's `0x0D`/`0x0E`.** See the header. Those are a
  different program's internal RAM. The `image` column in the committed table
  says `pd` on every row so that a row cannot be quoted as an EC claim.
- **Nothing observed on hardware.** No register was read back, no write was
  attempted, nothing was run on the machine. Static analysis of a committed
  image, and that is all it is. The value `0x0D`/`0x0E` holds when `0x1253`
  runs is a runtime question, and §5's `0x2802` is the arithmetic of a stated
  condition, not a measurement.
- **Not that the bank-1 windows are closed.** §4 finds two PSW writes that
  select bank 1, and that no R5/R6 is written along the part of their path this
  method follows. It does not follow the computed jump `0x1229` ends in, and it
  does not follow a `pop psw` in a routine it does not reach; the twelve writes
  whose RS is not fixed are where a further bank switch would have to come from.
  Only seven of the 21 PSW writes fix bank 0, so for the other 14 a
  register-form candidate's bank is not something this scan knows.
- **A zero is "not found by this method".** The zero callers in the main EC is
  a byte scan for `12 12 53` and `02 12 53`; a call to the same helper spelled
  some other way would not be found, exactly as `docs/findings.md` §4c requires
  this repository to say.
- **No control-flow recovery, and no function boundaries.** The `entry_pick`
  column is the nearest preceding call target *by byte scan* — a `12 hi lo`
  inside a data table is indistinguishable from an `lcall` — so it is a
  heuristic and rows that disagree should be read as disagreeing. The framing
  counts are evidence about alignment, not proof of it, and a site preceded by a
  dispatch table has no converging anchor and is not thereby misframed.
- **The 33 caller sites are static sites.** Which of them execute, how often,
  and in what order is not determined, and the 81 store-back sites are a
  candidate count over the same method. Whether some of either sit in the same
  routine is not determined either.
- **Not what the running base is a base of.** §3 reads `0x27FF` at reset and a
  mechanism that relocates it. What the firmware is relocating — a table, a
  window, an image — is not in these bytes, and `0x2802` is not evidence for
  any particular one.
- **Not the `0x9A71` store's destination.** §5 says §3.2 and §3.3 already had
  that, and repeats it rather than re-deriving it.
- **Nothing about issue #36's `0x104D` inline-argument convention**, which is a
  different routine and a different idiom. §7 says whether the two resemble
  each other; they stay separate either way.
- **Nothing runs this tool in CI, and that is deliberate rather than an
  oversight.** `.github/scripts/agent-gates.sh` is copied from
  `agent-pipeline`, `docs/agent-pipeline.md` says a repository running it should
  not edit those files casually, and the branch's push token has no `workflow`
  scope — so a change that touched the gate would fail at the end of the run,
  not the start. The repository's answer for a tool in that position is a
  prepared patch under `docs/ci/`, which is a human's `git apply`. This change
  registers nothing, which is what the closest sibling does too:
  `pd_index_geometry.py` and `pd_inline_arg_sites.py` are called by
  `tools/run-tests.sh` and `agent-gates.sh` neither, so their `--self-test` is a
  command a reader runs and not a check CI performs. **The `--self-test` and
  `--check` transcripts in §1 are therefore the reproduction, and they are not
  backed by an automatic run.**

## 7. Whether `0x104D` and `0x1253` share machinery

The issue asks that a shared mechanism be reported if one is found, and it is
not found — but the resemblance is worth naming, because it is the same shape
and not the same implementation.

Both are **argument-passing idioms over storage the call does not name**:
`0x104D` carries a 4-byte constant in the code stream immediately after the
call, and `0x1253`/`0x122F` take a 16-bit constant out of a fixed pair of
direct cells. Both exist so a caller does not have to load the value into DPTR
first. Beyond that they differ in every particular that matters: `0x104D`'s
argument travels *with the call site* and the helper pops its own return address
to find it, while `0x1253`'s addend lives in a *running* cell that the store-back
entry keeps current, so its value is a function of what the firmware has done
since reset rather than of the call. `0x104D` is idempotent and reentrant per
call site; the `0x1253` pair is shared state. **A resemblance in shape is not a
shared implementation, and the two issues stay separate.**

## 8. Open questions, for whoever picks these up

1. **What the running base relocates.** `0x27FF` at reset, advanced by 81
   store-back sites and read by 33. Naming the structure it indexes needs
   either a live trace or a caller-by-caller reading of the 81 sites, which is
   the work §5 declines. **The caller-by-caller reading is done**, in
   [pd-store-back-relocated-base.md](pd-store-back-relocated-base.md), and its
   answer is that the base is a displacement base into a record-like structure
   the firmware walks by small negative offsets rather than a relocated table
   base. What the record contains, its width and its record count are still
   open, and that write-up says so.
2. **The twelve PSW writes whose RS is not fixed, and the computed jump
   `0x1229` ends in.** Together these are what keeps the bank-1 windows open.
   A `pop psw` is the only route by which RS could arrive without a
   byte-pattern `mov psw` to find, and this method cannot follow it; nor does it
   follow the table `0x1229` jumps through, whose destination `1229.c` records
   as unrecovered.
3. **The four computed stores outside the block** (`0xA5A9`, `0xA5C8`,
   `0xB979`, `0xE8A3`). All four are inside other instructions' bytes as far as
   this method can tell, and each is named here rather than dropped; whether
   any is a real writer in a routine reached only by a computed jump is not
   decided.
4. **What `0x9B8` does with the three-bit value `0x9E01` reads through the
   returned DPTR.** The pointer is consumed; the use is not decoded, and closing
   it is control-flow recovery this repository has not attempted.
5. **Whether `0x9A71` is called anywhere but `0x9DEC`.** §5 pins the `0x9DFE`
   call as *a* call, not the only one, and no census of `lcall 0x9A71` was run
   because the issue asked about `0x1253`'s callers.
6. **Withdrawn — and recorded rather than deleted, per `docs/findings.md` §4a.**
   An earlier version of this section proposed correcting the "register bank 1"
   reading in `ec/annotations/ghidra-functions.csv:1355`, `:1356` and `:1358` in
   place, and rebuilding `0056.c`/`0094.c`/`00F0.c` to carry the correction into
   their generated headers. **Those three rows are correct and need no change.**
   `ghidra-functions.csv:1356` and `:1358` describe their `mov PSW,#0x10` as
   selecting register bank 1, `pd-image.md:242` says the same of the pair, and
   the standard 8051 PSW map confirms all of them: bit 4 is RS0, bit 3 is RS1,
   and `#0x10` sets RS0 alone. This write-up's own earlier reading was the one
   that was wrong, and the proposal would have replaced three accurate committed
   findings with that error while accusing them of causing a divergence they did
   not cause. The tool's `--self-test` is what let the error through: it pinned
   the transposed values, so the tool agreed with itself. It now pins the 8051
   map instead, and the pin is what catches this next time.
