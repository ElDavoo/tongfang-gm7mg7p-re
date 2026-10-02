# Every trampoline in the BL51 block gets a decoded target, read in the bank its stub selects (issue #574)

`ec/annotations/bank-call-audit.md` §3 counts the BL51 bank-switch block —
`0x1150`–`0x1ABC`, one `MOV DPTR,#imm16` and a tail `ljmp` per entry — and
counted the callers, and decoded none of the immediates. The immediate is what
makes the call cross-bank and it is not a branch operand, so no census in the
tree matched one. Two had been read by hand off the reset vector
([`reset-vector-dptr-targets.md`](reset-vector-dptr-targets.md), issue #559),
and that write-up says in as many words that one real routine and one bare
`ret` license nothing for the rest. This is the rest: one row per entry, the
immediate, the bank its own tail-jump stub selects, the byte read **in that
bank**, and whether a committed listing covers it.

```console
$ python3 ec/tools/trampoline_target_census.py --write
$ python3 ec/tools/trampoline_target_census.py --check
$ python3 ec/tools/trampoline_target_census.py          # the tables below
```

The committed table is
[`ec/annotations/trampoline-target-census.csv`](../../ec/annotations/trampoline-target-census.csv),
one row per entry in `bank-call-targets.csv`'s own column order plus five of
this tool's. `--check` regenerates it in memory and diffs it; a missing file
fails rather than being created.

**Nothing here was observed on hardware.** No register was read back, no
capture was opened, no Windows machine and no Ghidra run was involved. Every
figure is a static read of `ec/firmware/GMxMGxx_11.800` and of files already
committed, and no `status:` in `ec/annotations/registers.yaml` moves on any of
it.

## The order is the method, not a convenience

Each row is read in three steps, and they cannot be reordered:

1. the entry's tail operand names the stub;
2. the stub names the bank;
3. only then is the target's first byte read **in that bank**.

There is no other order available, and that is not a stylistic preference.
Every entry in this block is common-area code — below `0x8000`, where a bank
program and the common program are the same bytes — so "the bank the entry sits
in" has no well-defined reading for this population at all. A forwarder below
`0x8000` runs whichever bank is selected when it is called, and of the six bytes
in an entry the stub is the only part that says which.

That is the shape of issue #255's correction, run across the whole block at
once. `ec/annotations/ghidra-functions.csv`'s `bank1,19A8` row withdrew a
family counted against bank-1 listings when the stub at `0x1100` selects bank
0, and the row now carries the replacement count that withdrawal asked for.

**The block's framing is asserted, not assumed.** Every entry opens with `0x90`
and carries a 3-byte tail whose operand is a stub `find_banks.find_stubs()`
found, the entries are one unbroken six-byte stride with no gap, and the block's
two ends are the two addresses the census names. `--self-test` re-derives all
of that from the bytes rather than from the scan's own dict, so it can catch a
`trampolines()` that lost its bank rather than grade itself against it.

**`entry` is a scoring heuristic, not a decode**, and the table says so where it
uses it: `entry` is `find_banks.START_OPCODES`, `erased` is a run of at least
16 `0xFF` bytes, `other` is neither. That is `bank-call-audit.md` §4's own
vocabulary with no new member, read through `audit_call_targets.byte_class()`
rather than reimplemented. **A byte is not a body**: a row whose `target_byte`
is `0x22` says the first byte is `ret` and nothing else.

## The class distribution

| stub | selects | entries | `entry` | `erased` | `other` |
|---|---|---:|---:|---:|---:|
| `0x1100` | bank 0 | 350 | 179 | 0 | 171 |
| `0x1114` | bank 1 | 53 | 49 | 0 | 4 |

**No target in the family reads `erased`.** Bank 0 has three erased runs and
bank 1 one, and no entry routes into any of them — which is worth saying in
both directions, because bank 0 holds a 2,354-byte erased run at `0xF4CE`–
`0xFDFF` and bank 1 a 2,976-byte one at `0xF460`–`0xFFFF`. Both near misses
are one target each. The highest bank-0 target, `0xFE00` (from forwarder
`0x1630`), is the byte immediately after that first run and is itself `0xE4`,
`clr a`; the highest bank-1 target, `0xF381`, sits below the second. Had
either run started one byte earlier, that row would have read `erased`.

**§4's 16-byte rule changes no row of this table**, and the reason is stated so
a reader is not left assuming it did the work: no target's first byte is `0xFF`,
so a one-byte test and a run-length test answer identically here. The rule is
carried because it is the right test, and it is reported rather than relied on.

## 169 targets begin with `ret`, and 166 of them are inside a run of it

This is the result the issue asked for and stopped at, and it is not visible in
the class column: `0x22` is `ret`, `other` is what the heuristic says about it,
and `entry`/`erased`/`other` have no opinion about a *run* of the same byte.

**169 of the 403 targets have `ret` as their first byte in the bank their stub
selects, and 166 of those have a `ret` immediately below them.** That needs no
threshold: a target whose immediate predecessor in the selected bank is also
`ret` is not the first byte of a run, so whatever routine it names begins one
byte into a run of identical bytes. Three do sit at the start of one —
`0x84EA` and `0xADA2` as a lone `ret` each, and `0x8500` as the first of a
two-byte run.

Those 169 targets fall in fifteen runs of `ret` bytes. The largest holds 133 of
them:

| bank | run | bytes | targets |
|---|---|---:|---:|
| bank 0 | `0xBF54`–`0xBFDD` | 138 | 133 |
| bank 0 | `0xBF1B`–`0xBF2B` | 17 | 16 |
| bank 0 | `0xC921`–`0xC926` | 6 | 2 |
| bank 0 | `0xDFFB`–`0xDFFE` | 4 | 3 |
| bank 0 | `0xCB95`–`0xCB97` | 3 | 2 |
| bank 1 | `0x86B4`–`0x86B6` | 3 | 2 |
| bank 0 | `0xC1D7`–`0xC1D9` | 3 | 2 |
| bank 0 | `0xD565`–`0xD566` | 2 | 1 |
| bank 0 | `0x8500`–`0x8501` | 2 | 2 |
| bank 0 | `0xD89E`–`0xD89F` | 2 | 1 |
| bank 0 | `0xCA9D`–`0xCA9E` | 2 | 1 |
| bank 1 | `0x8293`–`0x8294` | 2 | 1 |
| bank 1 | `0x85F3`–`0x85F4` | 2 | 1 |
| bank 0 | `0xADA2` | 1 | 1 |
| bank 0 | `0x84EA` | 1 | 1 |

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0BF54 --runtime 0xBF54 -n 4
0xbf54  22       ret
0xbf55  22       ret
0xbf56  22       ret
0xbf57  22       ret
```

**What this does and does not say.** It says that 133 of the 350 bank-0
trampolines name an address inside one 138-byte run of identical bytes in the
bank their own stub selects. It does **not** say those calls are dead, that the
addresses are unreachable, or that the run is padding — a `lcall` into the
middle of a run is possible, and a trampoline naming an address is not evidence
that any caller runs. A `ret` immediately above a `ret` cannot be distinguished
from the bytes around it by anything in the image, and that is the whole of
the claim.

The one-byte test would have been no more decisive here than §4 says it is for
`0xFF`: the tree holds named one-instruction `ret` routines (`bank0,0xD9DB`
`ret_stub`, `bank0,0xD2BE` `ret_only_d2be`), so a `ret` byte is code and only a
run says otherwise. Issue #559's `0xD89F` is one of the 166, not one of the
three — it has a `ret` at `0xD89E` immediately below it, which is the same fact
`reset-vector-dptr-targets.md` records in its own words when it calls `0xD89F`
"the fourth `ret` in a run". The two rows the reset vector names are in this
table and agree with what that write-up read:

| entry | stub | target | byte | class | listing |
|---|---|---|---:|---|---|
| `0x158E` | `0x1100` (bank 0) | `0xD89F` | `0x22` | `other` | none |
| `0x1594` | `0x1100` (bank 0) | `0xD96C` | `0x90` | `entry` | none |

Both `listing` cells are empty, and that is a fact about the export rather than
about the bytes: `reset-vector-dptr-targets.md` §"The export is deferred"
records that the Ghidra export covering `0xD89F` and `0xD96C` is not committed,
because landing it needs a `--report` run on the pinned assembler. An empty cell
here is **not covered by a committed listing** — not found by this method,
never "absent".

## Which listing covers a target, and which does not

| stub | selects | covered | not covered |
|---|---|---:|---:|
| `0x1100` | bank 0 | 43 | 307 |
| `0x1114` | bank 1 | 11 | 42 |

The lookup is over `ec/decompiled/listing-index.csv` spans, in the *selected*
bank, with `also_in` honoured — a `common`-scoped row whose `also_in` names a
bank is that bank's copy of the same bytes, because `build_ec_decompile.py`
de-duplicates a function present in both into one row. On this population the
`also_in` clause never decides: every `common` row is below `0x8000` and every
target is at or above it. It is carried because it is what makes the lookup
bank-specific rather than a grep, and asking for a listing without the bank test
would let a bank-0 row vouch for a bank-1 target — the mistake this whole method
exists to avoid.

**The 349 uncovered targets are seeds, and landing them is a separate run.** Each
is an address a `--report` run on the pinned assembler
([`ec/ghidra/README.md`](../../ec/ghidra/README.md)) could export; none is
inferred from the absence of a listing, and nothing here says what any of them
does. They are carried row by row in the committed CSV so that run needs no
re-derivation. This is the shape issue #255 set, as
`reset-vector-dptr-targets.md` §"The export is deferred" describes it: it read
twelve bytes at file `0x0C10C` and, rather than land a half-landed export with
`verify_reassembly.py --check` red, left the seed row and the listing off its
branch for a pinned-toolchain run to add both.

## The one address the two banks answer differently about

402 distinct targets over 403 entries, and the repeat is the sharp case.
`0x8294` is named by two entries routing through opposite stubs:

| entry | stub | selects | byte | class | listing |
|---|---|---|---:|---|---|
| `0x19E4` | `0x1100` | bank 0 | `0x90` | `entry` | `bank0/8294.asm` |
| `0x1894` | `0x1114` | bank 1 | `0x22` | `other` | none |

Same address, two answers, and nothing in the bytes says which is which. The
stub is what picks, and reading either bank for both rows is the withdrawn
`bank1,19A8` count reproduced in miniature. `--self-test` uses this address as
its regression for the ordering: a run that read one bank for both would report
one class twice and be caught here.

## What this is beside the other two censuses, and which count the tree publishes

Three censuses of this family are in the tree and they are about different sets.
Naming them is what the issue asks for, and the answer is not simply "this one
supersedes those".

**`bank-call-audit.md` §3's block count** is range-restricted to the exporter's
trampoline block and is what this table's population is. Nothing here moves it:
the 350/53 split is recomputed from `find_banks.find_stubs()` on every
`--self-test` run and printed, and the entries' framing is re-derived from the
bytes.

**`subsystems.md` §4's export-shape count** is measured over the committed
export by shape — a function whose whole body is `mov DPTR,#imm16` followed by
`ljmp <stub>` — which is a different question over a different population (the
export, not the image's common area). It stands, it is not superseded by this,
and this table does not fold it in.

**The forwarder-family count** is `census_forwarder_targets.py`, which closed
#465 on 2026-10-02 and censused **the same 403 entries** against the committed
`.asm` files. So the withdrawn 19 / 7 / 22 is no longer the tree's answer: the
replacement is `25` entry / `0` operand / `23` not-found-by-this-method for the
annotated `bank1` subset, against bank 0. This issue's plan predates that
landing and read #465 as open; it is closed, and its write-up,
[`forwarder-target-bank-census.md`](forwarder-target-bank-census.md), is cited
here rather than re-derived.

**The overlap with #465 is exact and it is not a second count.** Both tools run
`audit_call_targets.trampolines()` over the same stub map and reach the same
403. They ask different questions of the same entries:

| | this census | `census_forwarder_targets.py` |
|---|---|---|
| what decides a class | the byte in the selected bank, read off the image | an instruction start in a committed `.asm` of that bank |
| vocabulary | `entry` / `erased` / `other` (`bank-call-audit.md` §4) | `entry` / `operand` / `no-listing` |
| a target no listing covers | still classified, and the `ret` runs the target falls in are reported | left `no-listing`, with eight bytes of context printed beside it |

The covered/not-covered split agrees in both directions, and the suite asserts
that the two committed tables agree rather than asserting either against a
number written here — so a drift in one is a red run. What this census adds is
the class a listing-based census cannot reach: 174 of the 349 uncovered targets
begin with a byte `START_OPCODES` would score `entry`, and `erased` is not a
class a method that only reads what is on disk can produce at all.

**So: which count does the tree publish?** Of the three, the block census is
the one the tree now publishes *decoded*, one row per entry, and it is
**range-restricted by block rather than by shape** — which is the only sense in
which it supersedes anything. It does not merge the export-shape count into
itself and it does not replace #465's per-target table; it reads the same
population in a different bank-safe way and the two cross-check each other.
§4's buckets for *bucket-B targets* remain a separate question from what a
trampoline immediate points at, and `bucket`, `own_bank` and `other_bank` are
left empty on these rows rather than reinterpreted.

## Out of scope, and what a follow-up would need

- **The export itself.** No `ghidra-functions.csv` row, no
  `ec/decompiled/*/` listing, and none of `build_ec_decompile.py`'s pins. The
  seeds are named here and carried in the CSV, which is the issue's own second
  option, and landing them is a pinned-toolchain `--report` run.
- **`--mode rebuild-project`.** Not required and not used; no export is landed,
  so the committed `.rep` is never opened for writing.
- **Re-measuring #465's family.** Closed, and cited above rather than redone.
- **Any register status, and any claim about hardware behaviour.** Nothing here
  was run on the machine, and a `ret` run is not evidence that a call into it
  never happens.

## Reproducing this

Every figure above comes from one command over committed inputs, or from the
committed CSV beside it:

```console
# the tables in this write-up, and the committed table's derivation
$ python3 ec/tools/trampoline_target_census.py
$ python3 ec/tools/trampoline_target_census.py --check
$ python3 ec/tools/trampoline_target_census.py --write

# the refusals and the re-derivation of the block's framing
$ python3 ec/tools/trampoline_target_census.py --self-test

# the two targets the reset vector already read, and the 0xFF run rule
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D89F --runtime 0xD89F -n 2
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0BF54 --runtime 0xBF54 -n 4

# the census this table's population and its stub map come from, and the
# per-target table of the sibling census it agrees with
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test
$ python3 ec/tools/census_forwarder_targets.py

# the suite
$ bash tools/run-tests.sh ec/tools
```