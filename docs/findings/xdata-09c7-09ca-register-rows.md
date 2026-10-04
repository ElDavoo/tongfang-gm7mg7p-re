# The charge-derating counters get their `registers.yaml` rows, and the rename is confirmed (issue #299)

`ec/annotations/registers.yaml` had no entry for any of the four bytes the
charge-target age derating counts in. The whole block was recorded in exactly
two places: the prose of
[`charge-target-derating.md`](../../ec/annotations/charge-target-derating.md)
§1, and the regex of one acceptance check. This adds the four rows, so the
newest behaviour decoded in this firmware lives in the file CLAUDE.md names as
the source of truth for EC register status, and it widens that check so it
survives the rename the rows cause.

## The per-address table

`present-untested` throughout, `sources: [xdata-refs]`, none claiming `live`.
The site lists are `ec/tools/trace_xdata_refs.py`'s, the same measurement every
committed XDATA table in this repository is made of:

```console
$ python3 ec/tools/trace_xdata_refs.py --counts-only ec/firmware/GMxMGxx_11.800 0x09C7 0x09C8 0x09C9 0x09CA
0x09C7: 2 direct MOV DPTR site(s)  bank0=2
0x09C8: 2 direct MOV DPTR site(s)  bank0=2
0x09C9: 9 direct MOV DPTR site(s)  bank0=9
0x09CA: 5 direct MOV DPTR site(s)  bank0=5
```

| addr | sites | what each does |
|---|---|---|
| `0x09C7` | 2 | `0xB149` writes it in `0xB12C manual_ctrl_profile_gate`'s `0x0490`-bit-1-clear else-branch; `0xB211` is `movx a,@dptr / inc a / movx @dptr,a / movx a,@dptr / clr c / subb a,#0x3c / jc` — the seconds counter, `0x3C` being the 60 §1 calls a minute |
| `0x09C8` | 2 | the same shape at `0xB14D` (the gate's clear) and `0xB234` (the increment) |
| `0x09C9` | 9 | `0xB151` writes two bytes walking into `0x09CA`; `0xB241` hands DPTR to `0xBCF5 stress_headroom`; `0xB25C` and `0xB272` load the address and the linear walk ends before any `movx`; reads at `0xB2F7`, `0xB319`, `0xB345`, `0xBD91`, `0xBD9E` |
| `0x09CA` | 5 | all direct reads, at `0xB2F1`, `0xB313`, `0xB33F`, `0xBD8B`, `0xBD98`, each a `movx A,@DPTR` then a `subb` against `0xb8`, `0xc8`, `0xc0`, `0xe0`, `0xd8` — the **low** bytes of §1's tier thresholds (`0x2CB8`, `0x1FC8`, `0x12C0`, `0x46E0`, `0x39D8`); the same site then takes the high-byte compare on `0x09C9` |

The two spellings of the seconds threshold are one compare, not two
claims. `clr c / subb a,#0x3c / jc` is Ghidra's `if (0x3b < XDATA_09C7)` — the
same "is it 60 yet" test, written the way a borrow and a strict `<` each
prefer. The table above quotes the listing, the oracle transcript below quotes
the decompilation, and both are `>= 0x3C`.

No site is in the PD image. The big-endian store is inline, in two places, and
**not** in helper `0xBB90` / `0xBD54`: the `mov dptr,#0x09c9 / movx @dptr,a /
inc dptr / movx @dptr,a` at `0xB151`, and `0xB20A` in
`charge_stress_update`, which stores `0x39` then `0xd9` — `0x39D9`, the value
§1 describes. `0xB20A` is not one of the nine sites above, because it carries no
`MOV DPTR` of its own: it writes through the DPTR that `0xBD98
tier_200_eligible` leaves at `0x09C9`. The two helpers are the store pair for
the `0x0A47..0x0A51` overlay locals, which is what §1 says about them; every
call site in the image (two each) loads an `0x0A4x` DPTR first.

`0x09C9`/`0x09CA` are added as **two scalar entries, not one multi-byte
entry**, so no endianness claim is baked into a symbol name:
`charge-target-derating.md` §1 reads the pair as a big-endian `u16`, but that is
a hand reading of one routine rather than a decoded property of the stores, and
`gen_xdata_symbols.py`'s own preamble says why a `_LO`/`_HI` suffix is the wrong
trade for it.

## What `present-untested` does and does not claim here

It is exactly the static warrant: the EC writes these bytes and reads them
back, and no host has ever read one. The distinction the vocabulary draws is
the one that matters for this block — **a static scan finding zero references
would mean "not found by this method", never "absent"** — and the converse
holds too: finding many sites is not evidence the EC *acts* on the bytes. What
it acts on is `charge-target-derating.md` §1's reading, and §2's inference from
the live charge target to the 250 mV/cell tier, which is an inference and says
so.

**`0x09C9` is not readable by a host at all**, which is why
[`charge-derating-counters-not-persisted.md`](charge-derating-counters-not-persisted.md)
deferred the question of whether these bytes get rows at all, and why the
answer there was "not yet":
`charge-target-derating.md` §2 records `0x09C9` reading back `0xFF` because
the host's `0xFE410000` window does not map `0x0800-0x0DFF`, and all four
addresses are inside that unmapped run. A note that said only "present" would
let a reader infer the byte had been exercised; each of the four says it was
not. What would settle the four on hardware is a read the host window cannot
perform, so it is a different exercise, and a human's.

The sites at `0xB25C` and `0xB272` resolve to nothing in
`ec/annotations/site-resolution.csv`, which records both as `unresolved-none`
because the depth-1 walk finds no `movx` in the decoded window. That is the
linear walk's limit, not evidence the byte is untouched there, and the same
write-up already reads both sites by hand rather than leaving them at that.
The committed `ec/annotations/two-hop-dptr-handoffs.csv` *does* resolve both,
one call on: each hands DPTR to `0xB280`'s `lcall 0x70e4`, which reads and
writes. The two files do not disagree — they are two depths of the same walk,
and only the two-hop pass follows the `sjmp` out of the window the depth-1 pass
stops at. Adding the `0x09C9` row is what puts the pair in that census at all,
so the row is regenerated here.

## The rename, confirmed rather than assumed

Adding these rows adds four symbols to `ec/ghidra/xdata-symbols.csv`, and that
file is what names an XDATA byte at decompile time. `DAT_EXTMEM_09c7` is the
exporter's own placeholder, which is what the byte was called precisely because
`registers.yaml` had no row for it; with a row it becomes `XDATA_09C7`. The
issue asks for that to be confirmed by export rather than assumed, and it is:

```console
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ec --mode export-only
$ git diff --stat ec/decompiled/
```

The files whose spelling moved are `bank0/B12C.c`, `bank0/B158.c`,
`bank0/B1F0.c`, `bank0/BD8B.c` and `bank0/BD98.c`, and nothing else: every
changed line is the token substitution, and no `.asm` moves because no listing
names an XDATA byte. The command above is the record of which files those are —
it is this change's own diff, not a property of the tree, so nothing holds it
and the suite does not try to.

**One more generated table moves with the export, and no gate runs its tool.**
`ec/ghidra/c-asm-counterpart.csv` pairs each `.c` address against the `.asm`
listing beside it, and its `symbol` and `spellings` columns follow the rename.
`test_c_asm_counterpart.py` is what catches that —
`c_asm_counterpart.py --check` is not in `.github/scripts/agent-gates.sh`, so a
re-export that misses it is green in the gate and red in `tools/run-tests.sh`.
Whoever re-exports after this should regenerate it with
`python3 ec/tools/c_asm_counterpart.py --report`.

## The oracle had to survive it

`build_ec_decompile.py`'s `ORACLE_FACTS` second entry matched
`DAT_EXTMEM_09c7 = DAT_EXTMEM_09c7 + 1` — a rename-proof fact written in a way
a register rename breaks, which is the one failure the table's own comment says
it was built not to have. Its first entry defends the *callee*
(`FUN_CODE_bf08` → `sub_0a4e_against_4d_with_borrow`) by matching on address;
the local the increment touches was still pinned to a name.

The alternation goes **inside the one pattern**, at all three token positions,
rather than into a second table entry: two entries would report the same code
as two facts, and `opt_in_ghidra_oracle()`'s negative case requires each fact
to be removable on its own and the other one not to be reported.

```console
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ec --self-test --oracle
  ok    bank0 0xB1F0: the export contains an lcall to 0xbf08 at 0xB200
  ok    bank0 0xB1F0: the export contains the 0x09c7 increment followed by its 0x3b compare
  ok    the export contains the 0x09c7 increment followed by its 0x3b compare exactly once, so taking it out is a deliberate break and not a no-op
  ok    taking it out of the c is reported, and the other fact is not
```

The negative case is the part that matters, and it is the part that was not
runnable without Ghidra: the widened pattern is now also exercised against
three synthetic exports — the old spelling, the new spelling, and the new
spelling with the fact removed — by
[`test_xdata_09c7_09ca_rows.py`](../../ec/tools/test_xdata_09c7_09ca_rows.py).
An assertion nobody has ever seen fail is not an assertion, and this one had
only ever been seen pass.

## What this does not settle

- **No live behaviour.** Nothing here reads a register back, and nothing here
  says the EC's derating counter ever reached a tier. `0x09C9` cannot be read
  through the host window at all; confirming the block on hardware is a
  different exercise, and a human's.
- **What `0x09C9` handed to `0xBCF5` does.** The DPTR handoff resolves to a
  *direction* one call down, which is what rule 3 asks for and all it asks for.
  The store's value is not read here.
- **`0x09C9`'s two unresolved sites**, left where
  `charge-derating-counters-not-persisted.md` left them.
- **Whether the counter persists across an EC reset.** That is #90, answered
  2026-10-03, and nothing here adds to it.
- **What `0x0490` and its bits are.** That is #241. `0x0B12C` is cited here as
  a writer of this block, not described.

## Follow-up this opens

- **The committed export on `main` is stale against its own annotations**, and
  this change is not what made it so. Re-exporting from a pristine `HEAD` with
  no input changed at all moves `.c` files that have nothing to do with this
  block — `bank0/8749.c`, which the committed tree still spells
  `DAT_EXTMEM_0464` where a fresh export writes `MAIN_FAN_RPM_0`, is one —
  because `ec/ghidra/xdata-symbols.csv` and `ec/annotations/ghidra-functions.csv`
  name addresses the last export predates. Reproduce it by exporting a clean
  checkout and diffing the two directories. This change re-exports and commits
  **only** the files its own rename moves, so the rest stays as it is rather
  than being swept in under an issue about four counters. Whether the rest
  should be refreshed, and whether anything should be holding the export
  against its inputs, is its own piece of work.
