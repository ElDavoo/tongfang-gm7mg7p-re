# The call-target seeds that land inside a longer instruction

`call_target_seeds()` in `ec/tools/build_ec_decompile.py` turns every target in
`ec/annotations/bank-call-targets.csv` into a Ghidra function entry. Nothing in
that path asks whether the target address is an instruction boundary, so a byte
one or two bytes into a real `ljmp` mints a function whose first instruction is
a decode of that `ljmp`'s middle byte. Those seeds are the `seed_basis=call-target`
rows of `ec/decompiled/index.csv` and the reason a listing exists at that address
at all.

Issue #1110 built the predicate this needs — `audit_call_targets.earlier_record()`,
the record that starts one or two bytes back and spans a site — and stopped at
adding the column. `ec/tools/call_target_seed_frames.py` runs that predicate over
the seed population, decides each affected seed against the committed bytes, and
publishes the result in `ec/annotations/call-target-seed-frames.csv`. Nothing here
was observed on hardware or in Windows; every input is a committed file.

## 1. The population, derived rather than carried

The tool imports `call_target_seeds()`'s own attribution rather than re-deriving
it, so "which census target belongs to which bank program" has one definition.
The predicate is applied **at the target address**, which is not the question the
census's own `earlier_record` column answers: that column describes each row's
*call site*. Reading it as though it described the seed is the confusion this
tool exists to head off, and the CSV carries the target's own covering record.

```
python3 ec/tools/call_target_seed_frames.py --check
```

prints one line, and that line is the source of truth for every figure below:

```
  2849 call-target seed(s) derived, 478 the predicate fires on (92
  mid-instruction, 242 entry-under-walk, 144 unread), 102 distinct target(s)
  named no bank and were not seeded
```

A "seed" is one `(program, target)` pair, because a common-area target is seeded
into both bank programs on purpose and `seed_rows()` de-duplicates per program.
The distinct addresses behind the 478 are fewer, since a common-area address
appears once per bank.

The 102 is bucket C, and it is reported beside the other figures rather than
folded into them. It counts distinct targets; `call_target_seeds()`'s own
docstring calls the same bucket 140 rows, and both are right because several rows
name one target. Those are census targets at or above `0x8000` seen from the
common area, where no byte says which bank is mapped, so `call_target_seeds()`
names them by nobody and seeds them into neither program. "No byte resolves this
target" is a different fact from "the byte resolves to an address inside an
instruction", and settling bucket C is issue #48, untouched here.

### The issue's third figure does not reproduce, and is not carried forward

Issue #1280 states three figures. The first two reproduce exactly against the
committed image — 2,849 distinct seeds, of which 478 land one or two bytes inside
a longer instruction under the predicate — and the third does not, under any
denominator tried:

> 155 of those have a committed listing, of which 85 carry a `[named]` header and
> 70 are `FUN_CODE_*`.

The denominators available all give different numbers, which is why the figure
cannot simply be re-derived into agreement: counting one row per `(program,
target)` seed, counting a distinct address once, counting only the rows whose
committed `seed_basis` is `call-target`, and counting rows against listing paths
rather than index rows each produce a different pair. **The issue does not state
which one it used**, so "155 / 85 / 70" is left here unreconciled rather than
quietly replaced by whichever number the tool happens to print.

What replaces it is the tool's own output, and the split by verdict rather than
by listing name is the one that carries the argument:

| verdict | seeds | what it means |
|---|---|---|
| `mid-instruction` | 92 | no majority of the walk's anchors lands *on* the address and a committed listing sits there, so that listing's first instruction is a decode of a byte inside the record named in the `covering_record` column |
| `entry-under-walk` | 242 | a majority of the walk's anchors land *on* the address, so the framing and the predicate disagree and the seed may be a real entry |
| `unread` | 144 | the predicate fires, there is no committed listing, and no walk settles it — named, not decided |

The 144 are the point of publishing rather than filtering. "The predicate fires"
is not "the entry is wrong", and the blind spot is a class rather than an
absence.

## 2. The rule, and the alternatives it is chosen over

For each seed the predicate fires on, `verdict_for()` reads the pair
`converges_from()` returns — how many of its anchors land on the address and how
many step over it — and nothing else:

- `onto > over` → `entry-under-walk`
- otherwise, a committed listing exists → `mid-instruction`
- otherwise → `unread`

The walk is `disasm8051.converges_from()`, which counts anchors over a window
`BACK` bytes deep clipped to the seed's own region floor, and whose own docstring
says a site nobody syncs onto is not thereby misframed. **The score picks a
better-evidenced reading; it never adjudicates the seed.** A site everybody syncs
onto is not thereby real, and the rule is a stated choice about where to put the
weight, not a measurement of truth.

"Majority" is the part that needed choosing, and `0x1706` is why: 2 of its 24
anchors land and 22 step over it, which has the same shape as a site preceded by
data. Three named alternatives were measured against the population, and
`test_call_target_seed_frames.py` pins each to *losing* on at least one seed, so a
later refactor cannot swap in a simpler rule that looks equivalent:

| alternative | why it loses |
|---|---|
| *any anchor lands* (`onto > 0`) | the rule a reader reaches for first; it files `0x1706` and others like it as entries on the strength of one or two anchors out of two dozen |
| *no anchor steps over* (`onto >= over`) | demands unanimity, and rules a site out on the strength of a single dissenting anchor |
| *a fixed count* (`onto > BACK / 2`) | compares an absolute vote count rather than the pair, so it misreads every seed whose window the region floor clipped — the count of anchors is not the same on both sides of an edge |

The last is the sharpest of the three, and the clipped windows are why: `BACK`
bounds the window but does not set its length, so a seed near a region's floor is
offered fewer anchors than one mid-region and any fixed threshold is reading a
denominator that moved.

The ordering is the other half. A rule that tested the listing before the walk
would file a real entry whose bytes happen to trip the predicate as
`mid-instruction` on the strength of the listing alone, and the walk is the only
evidence here that speaks to framing.

## 3. Four sites, read out of the committed bytes

| address | record spanning it | walk | listing | verdict |
|---|---|---|---|---|
| `0x1706` | `0x1705 02 11 00 ljmp 0x1100` | 2 / 22 | `FUN_CODE_1706`, `seed_basis=call-target` | `mid-instruction` |
| `0x0064` | `0x0063 02 11 86 ljmp 0x1186` | 1 / 23 | `FUN_CODE_0064`, `seed_basis=call-target` | `mid-instruction` |
| `0x0512` | `0x0511 b4 01 03 cjne a,#0x01,0x0517` | 0 / 24 | `int0_vector_forwarder_to_052f` | `mid-instruction` |
| `0x012F` | `0x012E b0 90 anl c,/p1.0` | 23 / 1 | `chan_init_170a_then_jmp_11b6`, `seed_basis=annotation` | `entry-under-walk` |

`0x1706` is the case
[`docs/findings/paged-trampoline-hits-by-hand.md`](paged-trampoline-hits-by-hand.md)
read by hand and [`earlier-record-column.md`](earlier-record-column.md) deferred:
one byte into a three-byte `ljmp`, and the listing's first instruction `acall
0x1000` is a decode of that `ljmp`'s middle byte. `0x0064` is the same shape and
had been read by nobody. `0x0512` is the `#data` byte of the `cjne`, and the
listing's `ajmp 0x0003` is a decode of it; the name claims a forward to `0x052F`,
which is what `0x0003`'s copy of the name says too — see
[`named-without-a-row.md`](named-without-a-row.md), which already records it.

**`0x012F` is the counter-example, and it is why none of this is a filter.** It
trips the predicate — `0x012E` pairs as `b0 90` — and it is a hand-decoded real
routine whose listing survives today precisely because `seed_rows()` sorts
`annotation` ahead of `call-target`, so the byte-scan target cannot swallow the
evidence-backed entry inside it. A rule that dropped every seed the predicate
fires on, or that filed them all as `mid-instruction`, would retire a function
somebody read by hand from the disassembly.

### What the annotations already agreed with

Nine of the affected addresses carry a `ghidra-functions.csv` row whose **name or
comment already says the address is not an instruction boundary** —
`mid_instruction_of_row_f053`, `operand_of_mov_dptr_f02f`,
`last_byte_of_row_f0ec`, `single_movx_store_not_a_function` and their siblings.
This tool's rule classes every one of them `mid-instruction`. That is
corroboration rather than a restatement: those rows were written by people
reading the disassembly one address at a time, and this is a corpus-wide rule
that never read their comments.

The caution §4 states about a smaller agreement applies here too — nine
agreements is not proof the rule is right. What it is worth is that these rows
were written from a different direction, and the rule reaches the same answer
without them. To re-derive the count, join the published CSV's `target` column
against `ghidra-functions.csv` and read the rows whose name or comment says so;
the tool does not compute it, because a rule matching a regex over prose is not
evidence about the firmware.

## 4. Two index subtleties, and a reading that had already been made

`mid-instruction` needs to know whether a committed listing sits at the address,
and both obvious ways of asking are wrong — in opposite directions, so the two
bugs cancelled each other's effect on the totals and neither showed up in a
count. Both were caught by the frame table below, not by arithmetic.

**A common-area address is not always filed under `common`.** `join_index()` folds
one only where both bank programs agree on its address, name and size, and keeps
both bank-scoped rows where they disagree. `bank0 0x031C` and `bank0 0x703A` are
common-area addresses that kept theirs, and a lookup on the folded name alone finds
no listing at either, filing seeds that do have one as `unread`. The tool
looks the address up rather than the folded name, which is what
`listing_at()` documents.

**An address is not exclusive to one program.** `ec/decompiled/index.csv` also
carries the PD image, whose addresses are the same numbers in a different address
space. `pd 0x1229` is the *only* index row at that address, so an unscoped
by-address lookup found it and reported a main-EC seed with no listing of its own
as `mid-instruction` — another program's bytes standing in for this one's.
`MAIN_EC_PROGRAMS` is the exclusion, and `test_call_target_seed_frames.py` asserts
that no published seed's verdict rests on a `pd` row.

**What caught both.** [`named-without-a-row.md`](named-without-a-row.md) §5
publishes a frame table settled by its own `converges_from()` walk, recording
`bank0 0x031C`, `bank1 0x031C`, `bank1 0x703A` and `common 0x0512` as
`mid-instruction` — "all 24 anchors step over the address and none lands on it",
with the covering instruction named. This tool's rule classes all four the same
way, from a population it derives independently and with a walk window it clips
itself, and neither reading consulted the other. That is the strongest evidence in
this document, and it is worth being precise about what it is: four agreements is
not proof the rule is right, and this document does not claim it is.
`converges_from()`'s own docstring says a site everybody syncs onto is not thereby
real, and a rule agreeing with every hand reading would be agreeing with the
repository's own conclusions rather than with the firmware. What it shows is that
two independent methods disagree nowhere they both speak — and that they *did*
disagree, once, until this section's two fixes.

## 5. Report, don't drop

`call_target_seeds()` now reads the published CSV and labels what it emits. It
**never drops a row on the verdict**, and that is what keeps the filter safe:
`bank-call-audit.md` §1 is explicit that the census is a byte-scan upper bound, so
every count in that document rests on the census including its misframed rows, and
discarding them would destroy the ability to say what they contained. The
`STRENGTH` ordering in `seed_rows()` is the mechanism that already keeps a
misframed byte-scan seed from swallowing the entry inside it, and a filter here
would be a second mechanism pulling the other way.

`build_ec_decompile.py --check` gains one ratchet over the published file,
reached from the existing gate arm. It compares the derivation against the
committed CSV and fails on any difference, **naming the seed**:

```
FAIL  seed frames: bank0 0x1706: verdict is 'entry-under-walk' in
ec/annotations/call-target-seed-frames.csv and 'mid-instruction' now.
Re-run with --write.
```

A live assertion — fail on any seed the predicate says is mid-instruction — is
deliberately *not* what this is, and the reason is the committed tree: it already
holds hundreds of them, so that check is red on arrival, and a check that cannot
go green on the tree it ships with is not a guard. The live assertion replaces the
ratchet in the pull request that lands the rebuild and empties the list.

## 6. What this does not settle

**Landing the corrected listings.** Retiring the entries the bytes rule out, and
seating the real ones, both need `--mode rebuild-project`. `CLAUDE.md` records why
that is its own landing: two branches that both rebuild the 7 MB EC database
cannot merge, and `.gitattributes` makes git refuse rather than text-merge a
database. Nothing in this change hand-edits `ec/decompiled/`, and the rebuild has
not been run.

**Whether `0x1F8D`, `0x1654` and `0x16FC` get a listing of their own.** The first
and last are **not call-target seeds** — the census names neither as a `target`,
so no seed was minted there and this rule has nothing to seat. They are the
boundary question #54 deferred, and #54 sequences it after `0x1706` is settled by
the rebuild, because "a function boundary chosen on the strength of this reading"
is the wrong order of operations. Left where #54 left it.

**Any claim about EC behaviour.** The verdicts are about framing only. No register
`status:` moves, no row of `ghidra-functions.csv` is added or removed, and no
sentence here says the EC executes any of the bytes read above.

**Adjudicating every affected listing one at a time.** The rule branch was taken
instead; sites the rule cannot decide are labelled `unread`, not guessed.

## 7. Reproducing any of this

```
python3 ec/tools/call_target_seed_frames.py              # every affected seed
python3 ec/tools/call_target_seed_frames.py --write     # regenerate the CSV
python3 ec/tools/call_target_seed_frames.py --check     # the ratchet
python3 ec/tools/call_target_seed_frames.py --self-test # the rule, on fixtures
python3 ec/tools/build_ec_decompile.py --work "$scratch" --check
python3 -m unittest ec.tools.test_call_target_seed_frames
```

`ec/annotations/call-target-seed-frames.csv` is this tool's output and is
regenerable with `--write`; nothing under `ec/decompiled/` is touched by it.