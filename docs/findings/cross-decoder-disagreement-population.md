# What the cross-decoder's `disagree` bucket is made of (issue #510)

`ec/ghidra/cross-decoder.csv` records, per sampled function, whether Ghidra's
exported C names the XDATA addresses `disasm8051.py` finds in the function's
opening straight-line instructions. Its `disagree` bucket is the one that says
they did not, and it is a single answer over several situations. `docs/findings.md`
§14i gave the bucket a sample and a denominator;
`cross-decoder-blind-population.md` gave `vacuous` a per-row cause. This is the
other half of the same report, and it is the half issue #510 is about.

Issue #510's own example is the reason this was worth an issue now rather than
later. `pd 0xF4CD`'s listing has read `mov DPTR, #0x07d6` throughout; what moved
was the C. Committing a callee's signature changed how the decompiler infers the
call's arguments, and `ec/decompiled/pd/F4CD.c` now spells the address as a cast
and a pointer local where it had spelled it as `DAT_EXTMEM_07d6`:

```c
  puVar1 = (undefined1 *)0x7d6;
  store_a_to_dptr(0,(undefined1 *)0x7d6,param_1);
```

The address is still there, the decompile is the better reading of the listing,
and the recorded ratchet cell moved to `disagree` — **for a spelling**. Every
address the variable layer is about to name as a pointer is a candidate for the
same move, and the next tranche of that layer is 99 rows of pointer annotations.

This measures the bucket and closes the spelling. `names_an_address()` in
`ec/tools/build_ec_decompile.py` now collects every address the C reaches by
either spelling it uses, and `ec/tools/cross_decoder_disagreement.py` gives
every remaining `disagree` row a committed per-row `cause` in
`ec/ghidra/cross-decoder-disagreement.csv`, over the same `(program, addr)`
keys. It adds nothing to `CROSS_DECODER_OUTCOMES`, moves no outcome the widening
did not, and touches no register status.

## The re-measurement (2026-10-02, this runner, committed inputs)

Rule as shipped: a body names an address if the address appears as a symbol
carrying it (`DAT_EXTMEM_07d6`, `XDATA_1664`) **or** as a hex literal of that
value (`(undefined1 *)0x7d6`), read with the exporter's annotation comment and
its `//` banner removed.

| | agree | disagree | vacuous | no-export |
|---|---|---|---|---|
| before (the committed report this change replaced) | 719 | **328** | 1008 | 2 |
| after | 920 | **127** | 1008 | 2 |

The counts move whenever the export or the sample does; that table is what was
measured on the tree at `83a05d76`, and the live figures are the ones
`build_ec_decompile.py --report` prints and the committed CSV carries. Nothing
else in the denominator moved: `vacuous` is unchanged because a window that
finds no address never reaches the matcher at all.

Across the 328 rows the old bucket held, 456 linear-address instances are
involved, and under the shipped rule:

| how the body names it | instances |
|---|---|
| a symbol carrying its own address — what `_EXTMEM` already matched | 98 |
| a hex literal only — what this change adds | 203 |
| neither | 155 |

### The rule has to be read off the body, and that is the whole measurement

**Matching the file rather than the body is not a small difference. It is the
difference between a check and a comment.** The same tree, the same matcher,
one argument apart:

| what the matcher is handed | agree | disagree |
|---|---|---|
| the whole file | 1038 | **9** |
| the body, annotation comment removed (shipped) | 920 | **127** |
| the body, every comment removed | 920 | **127** |

**118 of the 127 rows that stay `disagree` are there only because the
annotation is in scope** — the other 9 disagree either way, and no row is
half-rescued. `pd/F4CD.c` opens `/* With DPTR loaded from 0x07D6 ... */`, and so
does most of the export's annotation layer, because that is what an annotation is
for. The nine-row answer is §14b's failure in a new place: a check that reads a
fraction of its input and prints the result in the same form as a full pass.

The other two rows of that table are the useful half. **Removing the annotation
alone and removing every comment give the same census**, so which comment a
reader chooses to strip is a choice and not a tuning; the binary is *whether a
comment is removed at all*. `build_ec_decompile.py --self-test` asserts the
equality over the whole sample every run, and
`ec/tools/test_cross_decoder_disagreement.py` asserts the negative — that the
whole-file reading really does disagree about the bucket — so the rule is a
held fact in both directions.

### The false-positive surface, measured

A value match can be satisfied by a constant that is not an address: a bit mask,
a count, a byte offset into a base. That is the price of the hex route and it is
stated rather than argued. Over every row this change moves to `agree`, **no
matched literal is context-free**: each one sits in a cast to a pointer type, on
the right of an assignment, in a call's argument list, or after a `+`/`-` from a
base. The check is syntactic and so it cannot prove each match *is* the address
rather than a coincidence that happens to sit in argument position — but it does
say none of them is a bare constant that only coincides.

The class where that risk is largest is `named-by-decimal-literal` below, and it
is a **cause**, not an outcome: a row in it is still `disagree`, so nothing was
decided by a decimal match. The rule also excludes a digit that opens a hex
literal (`0x3f8`), that follows a letter, a dot or another digit
(`BAT_VOLTAGE_MV_0`, `bVar0`, `1.0`), or that is a character constant — `'\0'`
is a character, not the address 0x0000, and without that exclusion most bodies
in the export would name the address zero.

## The five causes, and the residue, cause by cause

Every row is in `ec/ghidra/cross-decoder-disagreement.csv`; the counts below are
what `cross_decoder_disagreement.py` prints on a run and are read from there,
not typed in here.

| cause | n | what it is |
|---|---|---|
| `named-by-register-symbol` | 43 | the body names the address with a register's real name, which carries no address in its spelling |
| `names-other-addresses` | 45 | the body names addresses and none of them is one the window found |
| `names-nothing` | 26 | the body names no address at all in the comparison's own vocabulary |
| `named-by-decimal-literal` | 7 | the body spells the address as a decimal literal of that value |
| `named-by-code-symbol` | 6 | the window's DPTR immediate named a *code* address and the export spells it in its own code space |

Each of the first three is a candidate to widen the matcher further, and each of
the last two is a vocabulary the comparison never had. The classes are decided
in that order — register symbol, code symbol, decimal, then the body's own
vocabulary — and each of the first three requires **every** missing address to
satisfy it, so a row whose addresses split between two routes falls through to
`names-other-addresses` rather than taking the first class that fits half of it.

### `named-by-register-symbol` — `bank0 0x8F09 copy_dptr_byte_to_075c`

```c
void copy_dptr_byte_to_075c(undefined1 *param_1)

{
  MAIN_FAN_R_DUTY = *param_1;
  return;
}
```

Three instructions: load A from the caller's DPTR, point DPTR at XDATA 0x075C,
store A there. The window finds `mov DPTR,#0x075c`; the body spells the address
`MAIN_FAN_R_DUTY`. `ec/annotations/registers.yaml` carries that name for
0x075C, `ec/ghidra/xdata-symbols.csv` exports it, and `_EXTMEM` cannot see it
because the name does not contain the address — which is the deliberate other
half of the vocabulary question §14i's issue #255 correction records ("a name
that is a register's real name (PROJECT_ID) carries no address and is
deliberately out of the vocabulary"). This class is that half, measured: it is
the largest cause, it is not a decompile defect, and every row in it is a
candidate for the matcher to learn `xdata-symbols.csv`'s names.

`bank0 0xB158 charge_target_update` is the row §14i's byte-pair fold and the one
issue #510 named, and it reads here:

```c
  store_be16_a(BAT_VOLTAGE_MV_0,0xa48,BAT_VOLTAGE_MV_1);
```

against a window that finds `mov DPTR,#0x0438` and `mov DPTR,#0x0439`. The pair
reaches the C as two register names inside one helper's argument list, so the
addresses are present and unreadable by any address-spelling route. It is
pinned at `named-by-register-symbol` and **not** at a fold of its own, because a
cause called "the fold" would need a judgement about which of a function's
reads is a fold. That judgement is what `CROSS_DECODER_OUTCOMES`'s own comment
refuses, and issue #140's option B — enumerating the folds rather than
describing them — is still the separate piece of work this does not do.

### `named-by-code-symbol` — `common 0x00CF walk_code_table_6f39`

```c
  pbVar6 = &DAT_CODE_6f39;
  while( true ) {
    ...
```

The window's `mov DPTR,#0x6f39` names a **code** address — the base of a table
this routine walks — and the export renders it in the export's own code space.
No XDATA vocabulary could ever have matched it, so calling the row a
disagreement is the comparison measuring the wrong address space. The export has
two spellings for that space and both are in the class: `bank0 0xBC95`'s
`(&DAT_CODE_632d)[*param_1]` is a table and `bank0 0xBADB`'s
`be16_add(0,FUN_CODE_08ce,1)` is a function entry, and 0x08CE is just as much a
code address in the second as 0x632D is in the first.

### `named-by-decimal-literal` — `common 0x1228 FUN_CODE_1228`

```c
void FUN_CODE_1228(void)

{
  bl51_bank_select_0(49000);
  return;
}
```

The window finds `mov DPTR,#0xbf68`; the export passes 0xBF68 to the BL51 stub
as **49000**. This is §14i's bank-switch-trampoline paragraph — "the address is
in the output as a literal argument, but not as a symbol carrying its address" —
and a literal argument is a route the matcher now reads, which is why the vast
majority of those rows are no longer in the bucket at all. What is left in this
class is the tail where the argument is small enough that Ghidra rendered it
decimal: `pd 0x7108`'s `add_word_0d0e_to_dptr(7)` is 0x0007, `pd 0xDB89`'s
`store_3byte_r3r2r1(1999)` is 0x07CF, and `bank1 0xCFB1`'s
`read_xdata_pair_to_r1r2(900)` is 0x0384.

The other bank-switch trampolines survive in `names-nothing` instead, because
their stub has a committed callee signature: `bank1 0x198A trampoline_to_c1e7`
decompiles to `bl51_bank_select_0(latch_0498_bit1_or_bit3); return;`, where the
address is in no literal at all — the signature swallowed it. That is the same
mechanism as `pd 0xF4CD`, one rung further along, and it is the direction the
variable layer is heading in.

### `names-nothing` — `common 0x4BB0 FUN_CODE_4bb0` and `pd 0x357E`

```c
void FUN_CODE_4bb0(void)

{
                    /* WARNING: Do nothing block with infinite loop */
  do {
  } while( true );
}
```

```c
undefined1 read_byte_to_r3_stride_60(undefined1 *param_1)

{
  return *param_1;
}
```

Neither body names an address, so there is nothing in either to be in or out
of. `4BB0` is the class's own reason for reading the code rather than the file:
its Ghidra warnings name five unreachable code addresses, and a classifier asked
of the file rather than of the code would call an empty loop a body that names
something. `pd 0x357E` is the other end — the pointer arrives from the caller.

### `names-other-addresses` — `bank0 0xB93A set_dptr_0a51_b93a`

```c
undefined1 set_dptr_0a51_b93a(void)

{
  return DAT_EXTMEM_0a52;
}
```

The window finds `mov DPTR,#0x0a51`; the body names **0x0A52**. This is the
honest remainder: the two decoders read different bytes, or one of them folded an
address away, and the comparison is right that they differ. `bank0 0xB947` is
the same shape at larger size — a window finding 0x0A48/0x0A49 against a body
that stages 0x0A59–0x0A5C — and the class spans the range rather than sitting at
one end of it.

## The split that is not made here

`names-other-addresses` is not divided further, and the reason is the one
`cross_decoder_blindness.py` gives for leaving `no-literal-named` undivided.
The shapes inside it are all real and all nameable: the body is an empty loop,
the pointer arrives from the caller, the immediate became an argument to an
annotated callee, the C names the neighbouring byte. Telling them apart means
reading each `.c` and deciding what its render *means* — and

> guessing which of a function's C reads is a fold would manufacture the very
> distinction the comparison is meant to measure

is `CROSS_DECODER_OUTCOMES`'s own stated reason for leaving `disagree` whole.
A regex proxy does produce buckets, and they would not be these ones: a
function is not reliably one or the other. So the class states the thing that is
true of every row in it, and the finer split is named here as the thing a future
method has to earn.

## The two directions, and why one of them is now unreachable

An `agree` → `disagree` move has two causes and the column cannot tell them
apart: a decompile that lost an address, or a matcher that stopped accepting how
the decompile names one. `pd 0xF4CD` was the second, and for the whole
`entry_dptr` tranche every move would have been the second again.

**It is now a property rather than a hope.** `names_an_address()` can only grow
the set it returns, so `missing = linear - in_c` can only shrink, so **no row can
reach `disagree` through the spelling route at all.** That is asserted rather
than argued:

- `build_ec_decompile.py --self-test` compares the committed report against a
  fresh run and fails if any sampled row moved `agree` → `disagree`. `pd 0xF4CD`
  is the first named case in the comment above `CROSS_DECODER_OUTCOMES`.
- `ec/tools/test_cross_decoder_disagreement.py` asserts the same relation, and
  asserts the mechanism underneath it: over every sampled function, the set the
  matcher returns is a superset of what `_EXTMEM` alone read out of the same
  text.

Both are properties over the tree, so they survive every future export; neither
is a count of it. The remaining half of the diagnostic is smaller and is in
`cross_decoder_problems()`: when a cell does move, the message names the
direction rather than saying "the export or the comparison moved".

## The limit

**The widening closes the spelled-as-a-cast case and not the general one.** The
matched set is the union of two routes over a file's text. An address the C
reaches through pointer arithmetic, a caller-supplied pointer, a base plus an
offset that happens to fold, or a value the export never writes down at all is
still `missing` — `pd 0x357E`'s `return *param_1;` is the smallest example and
`bank1 0x198A`'s swallowed stub argument is the largest kind.

**The window still stops at the first flow instruction, by design.** So
`disagree` keeps meaning *the two decoders saw different things in the opening
window*, and nothing here changes that. Past the first branch the linear walk
desyncs and its `0x90` bytes are operands it has lost track of; that is why the
window is bounded, and a disagreement here is a statement about the opening and
not about the function.

**And a local initialised from an address is not a fourth mechanism.** Issue
#510 asked for it to be folded in. A local is initialised from an address by
writing the address, so once every way of writing one is in the set the local
follows: `puVar1 = (undefined1 *)0x7d6;` is the hex route, not a route of its
own. A second mechanism that resolved pointer locals to addresses would be a
second answer to a question this one answers, and the first whose correctness
would be a judgement about a C rather than a fact about its text.

## What was decided against

**Not the local-initialiser fold.** As above: subsumed, and building it would be
a redundant second mechanism.

**Not in the CSV's header comment.** `cross_decoder_problems()` reads the
committed report through `read_index()` → `csv.DictReader`, which has no comment
handling, so a leading comment line would be consumed as the header row and
break `--check` on every commit. The two-directions statement is in the tool,
beside the `CROSS_DECODER_OUTCOMES` comment that already carries the
"one bucket on purpose" reasoning.

**Not a fifth outcome.** `CROSS_DECODER_OUTCOMES` stays at four, so
`denominator_line()` and `degenerate_sample_problems()` keep meaning exactly
what they mean. The reasoning is `cross_decoder_blindness.py`'s and it holds
here for the same reason: `outcome` answers *did the two decoders agree*; why
this row is what it is is metadata about the row.

**Not §7.2 of `ec/annotations/xdata-register-map.md`.** Issue #510 notes that
§7.2 accounts for 0x07D6 going 37 → 36 and does not say that the same event
flipped a cross-decoder verdict. That is true, and it is content for a new file
rather than a corrected figure: this records it and cites §7.2 by heading.
Editing §7.2 in place would be a second concurrent-PR conflict site in a long
shared document for a sentence this file already carries.

**No register status moved.** `ec/annotations/registers.yaml` and
`ec/annotations/ghidra-variables.csv` are read-only inputs here, and no Ghidra
run, project rebuild or decompile re-export was needed: the whole change is
`python3` over committed inputs.

## Reproducing it

```sh
python3 ec/tools/build_ec_decompile.py --work /tmp/ec --report    # the CSV
python3 ec/tools/build_ec_decompile.py --work /tmp/ec --check     # the ratchet
python3 ec/tools/build_ec_decompile.py --work /tmp/ec --self-test --cross-decoder
python3 ec/tools/cross_decoder_disagreement.py            # the census below
python3 ec/tools/cross_decoder_disagreement.py --check
python3 ec/tools/cross_decoder_disagreement.py --report
python3 ec/tools/cross_decoder_disagreement.py --self-test
```

`ec/ghidra/cross-decoder-disagreement.csv` is generated by that tool's
`--report` and by nothing else, from committed inputs alone. Its `--check`
recomputes every row cell-for-cell and fails on a row the sidecar carries that
the sample no longer has, a sampled row it does not carry, any cell that moved,
and a `disagree` row that fell in no cause at all. It is not in a gate:
`docs/ci/agent-gates-cross-decoder-disagreement.patch` is prepared for a human
to land, and until then it runs under `tools/run-tests.sh`, which is what the
blindness sidecar does today.

The one file outside this change's own two that had to move is
`ec/ghidra/cross-decoder-blindness.csv`: it carries the parent's `outcome`
column, so 201 rows of it changed. Regenerated by its own `--report`; no `blind`
class moved.

## Limits

- **The five causes are a partition of one bucket, not a diagnosis.** They say
  where the address is spelled, not whether the comparison is right, and a
  `names-nothing` row is not a claim that a register is unused.
- **The hex route is a value match.** The measured false-positive surface is
  above: no newly-`agree` row is matched by a context-free literal. That is a
  statement about syntax, not a proof that each match is the address.
- **`named-by-register-symbol` is read from `ec/ghidra/xdata-symbols.csv`**,
  which is the export's own symbol table and can be regenerated. A name given to
  two addresses answers for both and for neither other; a name that is not in
  the table answers for nothing.
- **Nothing here is measured on hardware.** Every figure is a property of
  committed bytes, committed listings, a committed report and committed
  decompiles. No register was read back and no vendor code ran.
