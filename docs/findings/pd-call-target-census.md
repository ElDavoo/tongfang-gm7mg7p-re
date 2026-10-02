# Sixteen candidates, sixteen verdicts: a control-flow census of the PD image's absolute call sites

`docs/findings/pd-common-address-spaces.md` byte-scans the whole ITE8850-PD
image for the `12 11 c2` encoding, gets sixteen hits, and says of the fifteen
outside a committed listing that "this method can neither call them callers nor
data" — then names what would settle it:

> A control-flow-aware scan that disassembles instead of pattern-matching would
> separate calls from data in one pass, and is the tool this open question
> actually wants.

This is that tool. `ec/tools/pd_call_targets.py` walks the image from a stated
entry set, following control flow rather than matching byte triples, and
`ec/annotations/pd-call-targets.csv` books every candidate site with the
listing its walk was inside and a verdict. The payoff the issue asked for is
delivered: **the sixteen have sixteen answers, and the nine `lcall 0x119C`
sites have nine.**

Nothing here is a confirmed caller, and the section that says so is the one to
read first if the verdict names look stronger than they are.

---

## The correction, with the wrong version left visible

The issue's second premise is **wrong on the committed tree.** It says:

> The `.asm` headers that say a function boundary "came from a call-target byte
> scan and is a hypothesis" — `ec/decompiled/pd/10F1.asm`, `1229.asm` and
> others — are the same method and the same blind spot.

**No `pd` `.asm` header carries that note.** The sentence is in eight
`ec/annotations/ghidra-functions.csv` rows and in the eight generated `.c` files
those rows produce, and what all of them say is that the `.asm` header carries
it. It is in **two spellings**, which is worth knowing before anyone re-runs the
search: seven say "call-target byte scan" and `1229` says "call-target-scan
hypothesis", so a grep for either literal alone finds seven and not eight.

```
$ grep -rl "call-target byte scan" ec/decompiled/pd/*.c | sort
ec/decompiled/pd/0EF3.c
ec/decompiled/pd/10F1.c
ec/decompiled/pd/9A1B.c
ec/decompiled/pd/9A90.c
ec/decompiled/pd/F109.c
ec/decompiled/pd/F126.c
ec/decompiled/pd/F4AB.c
$ grep -rl "call-target-scan" ec/decompiled/pd/*.c
ec/decompiled/pd/1229.c
$ grep -rl "call-target byte scan\|call-target-scan" ec/decompiled/pd/*.asm | wc -l
0
```

**The claim's origin is the annotation CSV, which is the editable surface** —
`pd,1229`'s comment is where the sentence is written, and `build_ec_decompile.py`
copies the row's comment into the `.c`. The correction therefore has one home,
and it is not this change's: editing the CSV without re-running the Ghidra
export leaves `build_ec_decompile.py --check` red, and re-running it rewrites
sixteen generated files for a prose fix. The amendment is its own piece of work,
and the suite holds the eight-row set against the files that carry it so that
piece starts from a measured list rather than from this sentence.

Independently of where it was written, the claim is false on two counts.
`ec/decompiled/listing-index.csv` gives all eight `seed_basis=annotation` — the
boundaries are recorded as hand annotations, not as the output of a call-target
scan. And `build_ec_decompile.py` asserts that "the PD image is never seeded
from the EC call-target census", which is the other half of the answer: there is
no scan these boundaries could have come from.

So the eight "seeds" the issue wanted a control-flow pass to test are eight
hand-annotated function entries, and `--seed-verdicts` says what the walk makes
of them. All eight are reached, all eight frame at 24 of 24 anchors:

| listing | name | `seed_basis` | seeded | reached by a walk | frame |
|---|---|---|---|---|---|
| `0x0EF3` | `or_32bit_r0r3_r4r7` | `annotation` | yes | yes | 24/24 |
| `0x10F1` | `read3_code_to_r3r1` | `annotation` | yes | yes | 24/24 |
| `0x1229` | `load_dptr_then_indirect_jump` | `annotation` | yes | yes | 24/24 |
| `0x9A1B` | `a_r3_b_60_tail_10bc` | `annotation` | yes | yes | 24/24 |
| `0x9A90` | `load_a_from_r7_stub` | `annotation` | yes | yes | 24/24 |
| `0xF109` | `set_or_clear_bit0_via_9028` | `annotation` | yes | yes | 24/24 |
| `0xF126` | `gate_on_6f96_then_tail_122f_with_dp_000a` | `annotation` | yes | yes | 24/24 |
| `0xF4AB` | `store_4bytes_to_0a82` | `annotation` | yes | yes | 24/24 |

**The eight comments are left as they are**, and the reason is worth restating
because a reader will otherwise take the table above as a fix. They are written
in `ec/annotations/ghidra-functions.csv` and *generated* into the `.c` files by
`build_ec_decompile.py`, which marks them "do not edit". **What is fixed here is
the census's premise — which seeds these are, and what the walk makes of them —
and not the prose that misdescribes them.**

---

## The verdicts, site by site

The `lcall 0x11C2` sites, in address order. `decoded-lcall` means an aligned
walk from the stated entry set decoded this offset as an `lcall`;
`unreached-by-this-method` means no walk from those entries decoded anything
there, which is **not** a claim that the bytes are data.

| site | verdict | inside a committed listing | enclosing walk seeded at | frame |
|---|---|---|---|---|
| `0x13F6` | `unreached-by-this-method` | no | `0x133F` | 24/24 |
| `0x153E` | `unreached-by-this-method` | no | `0x133F` | 24/24 |
| `0x16A7` | `unreached-by-this-method` | no | `0x133F` | 24/24 |
| `0x1AB6` | `unreached-by-this-method` | no | `0x1820` | 24/24 |
| `0x1C88` | `unreached-by-this-method` | no | `0x1820` | 24/24 |
| `0x3A46` | `unreached-by-this-method` | no | `0x3A33` | 22/24 |
| `0x4587` | `unreached-by-this-method` | no | `0x4402` | 24/24 |
| `0x483A` | `unreached-by-this-method` | no | `0x4800` | 24/24 |
| `0x4FFA` | `unreached-by-this-method` | no | `0x4E84` | 20/24 |
| `0x617D` | `unreached-by-this-method` | no | `0x5950` | 20/24 |
| `0x776C` | `unreached-by-this-method` | no | `0x775C` | 20/24 |
| `0x7948` | `unreached-by-this-method` | no | `0x775C` | 20/24 |
| **`0x8288`** | **`decoded-lcall`** | **no** | `0x821B` | 24/24 |
| `0x83CF` | `unreached-by-this-method` | no | `0x821B` | 20/24 |
| `0x92EF` | `unreached-by-this-method` | no | `0x9177` | 20/24 |
| **`0xCB4A`** | **`decoded-lcall`** | **yes** | `0xCB2A` | 24/24 |

The `lcall 0x119C` sites:

| site | verdict | inside a committed listing | enclosing walk seeded at | frame |
|---|---|---|---|---|
| `0x136C` | `decoded-lcall` | yes | `0x133F` | 24/24 |
| `0x1F2D` | `decoded-lcall` | yes | `0x1EFE` | 24/24 |
| `0x42C5` | `decoded-lcall` | no | `0x3FEA` | 24/24 |
| `0x44D2` | `decoded-lcall` | no | `0x4402` | 24/24 |
| `0x4C35` | `decoded-lcall` | yes | `0x4C27` | 24/24 |
| `0x6B4C` | `unreached-by-this-method` | no | `0x68CE` | 24/24 |
| `0xA34B` | `decoded-lcall` | yes | `0xA339` | 24/24 |
| `0xADE6` | `decoded-lcall` | yes | `0xADAB` | 24/24 |
| `0xC879` | `decoded-lcall` | yes | `0xC873` | 24/24 |

`--for-target 0x11C2` and `--for-target 0x119C` print exactly these two tables
from the committed CSV, decoded at each site's own offset, so neither is a
number in prose that nothing re-derives.

### `0x8288` is the site this census adds

`pd-common-address-spaces.md` records that only `0xCB4A` of the sixteen falls
inside a committed `pd` listing, and that remains true — the `in_listing` column
here agrees with it, site for site. **What the walk adds is a second site it
reaches and no listing holds.** The walk seeded at `0x821B`
(`fill_0849_0857_block`) decodes straight through it:

```
0x8274  90 08 49     mov  dptr,#0x0849
0x8277  e0           movx a,@dptr
0x8278  fb           mov  r3,a
0x8279  90 04 24     mov  dptr,#0x0424
0x827C  12 99 c1     lcall 0x99c1
0x827F  12 99 8f     lcall 0x998f
0x8282  e0           movx a,@dptr
0x8283  fe           mov  r6,a
0x8284  a3           inc  dptr
0x8285  e0           movx a,@dptr
0x8286  8e f0        mov  0xf0,r6
0x8288  12 11 c2     lcall 0x11c2      <- decoded, and in no listing
```

The export's `821B.asm` holds 33 instruction starts ending at `0x8258`, so
`0x8288` is past the listing's own committed body and past the `size=64` extent
`listing-index.csv` records. The walk runs on through it because
`enclosing`'s boundary is the *next listing start* (`0x856F`), not the end of
this listing's instruction bytes. **This does not contradict the older file's
"only `0xCB4A` is inside a committed listing": the two answer different
questions, and the column is kept separate for exactly that reason.** It is a
candidate caller, not a confirmed one, for the reason in the last section.

---

## Two coverage figures, and they are two methods'

This is the second thing the issue asked for — "publish the coverage figure the
method reached rather than the coverage figure the listings reach" — and it is
printed with both, separately named, because printing one and calling it *the*
coverage would be the failure `docs/findings.md` §4 records:

```
$ python3 ec/tools/pd_call_targets.py --report
2. Coverage, and it is two methods'
  this walk decoded 20723 of 65536 bytes (31.62%) as 25052 instructions
    what a stated entry set reaches. It is not a claim that the rest is data, and the
    budget named in any `max_insns` cell is why this is not the figure below.
  the committed `pd` listings hold 16423 bytes (25.06%)
    what has a committed listing for it, counted from the listings' own instruction streams.
    [...three more lines, the rest of section 2...]
```

The first is what a stated entry set decodes to; the second is what a quarter of
the image has a committed listing for. **Neither is "these bytes are code."**
The second is re-derived here from the listings' own instruction streams rather
than read from `listing-index.csv`'s `size` column. The two agree byte for byte
on this tree — `size` *is* a listing's instruction bytes — and the figure is
derived anyway so a hand-edited cell cannot move it quietly. Both numbers are in
the pinned block at the end and `--check` re-derives them.

`pd-common-address-spaces.md` measured the same quantity over an earlier and
smaller set of `pd` listings, so its figure is not this one and is not restated
here.

---

## The entry set, and why the walk is not a linear decode

Every seed is a committed address. Nothing is found by scanning the image for
something that looks like an entry, which is the whole difference from
`opcode-len-bounds-census.md`'s method and from the byte scan:

- **`vector`** — the six vector-table targets, from
  `pd_image_census.vector_table()`. That module's `--self-test` pins the
  8-aligned reading as *wrong* on these bytes, which is why the geometry is
  imported rather than walked a second time.
- **`listing`** — every `pd` row of `ec/decompiled/listing-index.csv`.
- **`call-graph`** — every `pd` row of `ec/annotations/call-graph-callees.csv`.
  On the committed tree these are a subset of the listing rows; the overlap is
  measured and printed rather than assumed either way.
- **`discovered`** — a target the walk decoded that is not a seed, added to the
  worklist so the loop closes over its own output.

An address seeded by more than one source is counted under both, so the
per-source numbers do not sum to the distinct-entry count; both are printed
together for that reason, and both are in the pinned block.

**The descent follows both arms of every conditional branch**, so the result is
"reachable from here" and not a guess about the hot path. `lcall` is recorded
and the walk continues past it; `ljmp` and `ajmp` end the walk and their targets
join the worklist. The `ljmp` half is not decorative here: neither
`0x119C` nor `0x11C2` has a `ret`, their only exit being `jmp @A+DPTR`, so a
tail `ljmp` into either is a real and distinguishable call shape. A
`jmp @a+dptr` ends the walk and is recorded as a cut, because that target is
not in the bytes.

### `enclosing` is a listing fact, and what the rule costs

A walk from entry *E* stops at the lowest committed `pd` listing start strictly
above *E* and records `next listing boundary` among its terminators. Without it
a mis-seeded entry runs for thousands of bytes and every call site inside it
gets the wrong enclosing function.

**The rule is measured rather than assumed free.** Dropping it and letting a
walk run to the end of the image decodes 22 more call/jump sites and 230 more
bytes, and `boundary_ablation()` recomputes both on every `--report` and
`--check`, because a boundary rule nobody has costed is a rule nobody can trust
on the rows where it does decide something. The suite asserts that the two walks
really do differ, so the cost figure cannot go stale silently.

### One blind spot, named

The `mid-instruction` verdict — a committed listing holds an instruction
covering a candidate byte and no walk decoded it — has two causes, and only one
is a property of the method:

- **A listing whose export begins above its own first instruction.** A walk
  runs forward from a seed, so bytes below that seed are unreachable from it.
  Four committed `pd` listings have this shape, and they are printed by name in
  `--report`:

  ```
  0B85.asm  entry 0x0B85, first instruction 0x0B51
  0E54.asm  entry 0x0E54, first instruction 0x0E18
  4D6F.asm  entry 0x4D6F, first instruction 0x4A12
  C873.asm  entry 0xC873, first instruction 0xC819
  ```

- **A listing whose instructions are on no path the walk took**, because the
  walk ended at a `ret` or a tail jump first. That is ordinary reachability,
  not a defect.

---

## What this does not establish

**No row here is a confirmed caller.** `decoded-lcall` means an aligned walk
from a stated entry set decoded this offset as an `lcall`.
`audit_call_targets.py`'s docstring is why that is not more than it says:
framing is unsettled in *both* directions there, and its anchored count is
"demonstrably not phantom-free" — sites that score 24 of 24 and are plainly
inside an address table. Of the sixteen, nine score 24 of 24, six score 20 and
one scores 22. **The frame column is high for sites this tool calls
unreached, which is the clearest single reason to read the two columns together
and neither alone.**

**`unreached-by-this-method` is not absence.** It means no walk from the stated
entries decoded anything there. The fourteen unreached `0x11C2` sites may be
calls reached by an entry this census does not seed, table data, or an operand
of an instruction no walk reached. This tool cannot choose between those.

**A `data-region` verdict is 0 and the `region` column reads `not listed`
throughout, because `data-regions.yaml` lists no region in the PD extent at
all.** That is a fact about the annotation map and not about the image: no PD
byte is thereby code. A region added there would label rows here without
changing any other count. `refuse_filtering()` is a refusal rather than a
convention, so no output mode can drop such a row when one appears.

**The method reaches about a third of the image and the rest is not thereby
data.** The coverage figure is a statement about what this walk decoded. The
walk does run to the last non-erased byte — `0xF7B7`, above which the image is
`0xFF` — so the unreached two thirds are *inside* the live image, not a padding
tail. What is unreached is code this entry set never reaches, table data, and
the `pd` listings whose export begins above its own first instruction. The
figure says how much a stated entry set decodes; it does not say the remainder
is anything in particular.

**Nothing here is behavioural.** Every input is a committed file:
`ec/firmware/GMxMGxx_11.800` and the committed CSVs. No hardware is reachable
from a GitHub-hosted runner, no register was read back, and nothing in this
change is evidence the PD program acts on any of these bytes.

**The 2-byte paged forms and the PC-relative family are not here.** They are
`ec/annotations/bank-paged-call-targets.csv` and
`bank-relative-branch-targets.csv` for the bank images, and a second tool's
census inside this tool's file is how two vocabularies merge. A `--paged-csv`
mode is the obvious follow-up and is the first thing to add.

**What the table at `0xCB4D` selects is untouched.**
`pd-common-address-spaces.md` leaves it open and
[`pd-11c2-dispatch-key-selector.md`](pd-11c2-dispatch-key-selector.md) is where
that derivation lives; whether a given site is a *caller* and what a given
execution *selects* are separate questions and this change answers only the
first, for two of the sixteen.

**The eight annotation comments still cite a note that is not there.** See the
correction above and the reason for not editing them; this change fixes the
census's premise, not the prose.

---

## The committed table, and what holds it

`ec/annotations/pd-call-targets.csv` is the product of exactly one command and
is checked against it:

```
$ python3 ec/tools/pd_call_targets.py --csv > ec/annotations/pd-call-targets.csv
$ python3 ec/tools/pd_call_targets.py --check
```

`--check` regenerates the table, diffs it byte for byte, and re-derives every
figure in the block below. It walks the **union** of the block's keys and the
tool's own, so a figure the page gains without the tool producing it fails as
well as one the tool produces that the page does not pin. A *missing* CSV is a
failure rather than something to create, and `--csv` is refused alongside
`--check` — a check that writes the file it is checking cannot fail on it.

Columns: `file_offset, runtime, candidate, verdict, target, enclosing, ends,
frame_onto, frame_over, in_listing, region`. `target` is what the bytes at the
site name whether or not a walk decoded it, so an unreached row still carries
the operand a byte scan read; on a decoded row it is the number the walk
resolved. `ends` is the terminator set of the walk seeded at that row's
`enclosing`, which is why a bound is named on the rows whose walk it cut and
`no walk seeded above this address` on the rows with no walk above them. Every
cell is drawn from `walk_branch_arms.py`'s terminator vocabulary plus
`next listing boundary`, and `--self-test` fails on a cell naming anything else.

```text
# pd-call-target-census pinned figures
base_offset = 0x20000
image_bytes = 65536
candidate_sites = 7266
candidate_byte_scan = 7266
verdicts = decoded-lcall=1595 decoded-ljmp=196 operand=263 mid-instruction=26 data-region=0 unreached-by-this-method=5186
entry_distinct = 541
entry_vector = 6
entry_listing = 541
entry_callgraph = 505
entry_discovered = 162
walk_instructions = 25052
walk_decoded_bytes = 20723
walk_coverage_pct = 31.62
listing_starts = 9277
listing_bytes = 16423
listing_coverage_pct = 25.06
terminators = ret=866 reti=7 tail jump to a callee=778 indirect jump -- target not resolvable from the bytes=13 next listing boundary=160 loop=1634 depth limit=11
dispatch_sites = 0x119C=136C:decoded-lcall,1F2D:decoded-lcall,42C5:decoded-lcall,44D2:decoded-lcall,4C35:decoded-lcall,6B4C:unreached-by-this-method,A34B:decoded-lcall,ADE6:decoded-lcall,C879:decoded-lcall 0x11C2=13F6:unreached-by-this-method,153E:unreached-by-this-method,16A7:unreached-by-this-method,1AB6:unreached-by-this-method,1C88:unreached-by-this-method,3A46:unreached-by-this-method,4587:unreached-by-this-method,483A:unreached-by-this-method,4FFA:unreached-by-this-method,617D:unreached-by-this-method,776C:unreached-by-this-method,7948:unreached-by-this-method,8288:decoded-lcall,83CF:unreached-by-this-method,92EF:unreached-by-this-method,CB4A:decoded-lcall
dispatch_in_listing = 0x119C=136C,1F2D,4C35,A34B,ADE6,C879 0x11C2=CB4A
```

Every figure above is a property of the committed image or of the committed
listings, re-derived on every `--check`; none of them is a total of this
repository that a merge would falsify without turning the check red.

---

## Wiring it into a gate, for whoever has the token

`ec/tools/pd_call_targets.py` is **not** in
`.github/scripts/agent-gates.sh` and cannot be added from an agent branch: the
plan stage's push token has no `workflow` scope, so a branch touching
`.github/` fails at the end of the pull request rather than the start.

The recipe, for a human or for a follow-up:

1. `check_ghidra_tooling()` runs a fixed tool list. A `--check` arm is added
   beside the existing `--self-test` arms, e.g.
   `python3 ec/tools/pd_call_targets.py --check`.
2. The prepared-patch route exists — `docs/ci/agent-gates-*.patch`, landed by a
   human with `git apply`, and
   [`prepared-gate-patches.md`](prepared-gate-patches.md) is the write-up for
   it. **A new patch cannot be added freely**:
   `tools/test_agent_gates_patches.py::CompositionTests` applies the set in
   every ordered pair and fails when two patches cut the same line.
   `docs/ci/agent-gates-disasm8051-self-test.patch`'s header says the free hunks
   in the gate are already spent, which is why its own second and third tools
   folded into that one file rather than shipping a second patch.
   **The same line is what a new tool would have to cut.** The way through is to
   fold this mode into the existing patch and add both strings to
   `FoldTests.REQUIRED`, rather than to add another patch file.
3. Until then the suite covers `--check` directly, the way
   `bios/tools/test_ifr_census.py` covers a committed dump, so the check is
   exercised on every `bash tools/run-tests.sh` rather than merely present.

## Related

- [`pd-common-address-spaces.md`](pd-common-address-spaces.md) — the byte scan,
  the sixteen sites, and the `0x11C2` annotation this census does not
  contradict.
- [`pd-11c2-dispatch-key-selector.md`](pd-11c2-dispatch-key-selector.md) — what
  a given key pair selects at `0xCB4D`, which is a different question from
  whether a site is a caller.
- [`pd-image-census.md`](pd-image-census.md) — the vector geometry, the string
  pool and the provenance of the same 64 KiB region.
- [`pd-e2e4-entry-forms.md`](pd-e2e4-entry-forms.md) — the same
  candidate-versus-confirmed distinction applied to one body, and the reason
  the `in_listing` column is kept separate from the verdict here.
- [`no-append-logs.md`](no-append-logs.md) — why none of the figures above is
  written in prose in a place every merge has to edit.
