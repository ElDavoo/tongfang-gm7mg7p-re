# Bucket C against a recovered code map: 16 of the 140 sites are on an instruction boundary, and 14 of those 16 sit inside spans already listed as data tables

**Committed bytes only. No capture was opened, no EC was powered, no
hardware and no Windows were involved, and no `status:` in
`ec/annotations/registers.yaml` moved. Every figure below is a static read of
`ec/firmware/GMxMGxx_11.800` and of files already in the tree, or the output
of a command over them.**

`ec/annotations/bank-call-audit.md` §5 hands this over by name: "Anyone who
needs bucket C settled should decode the common area from a recovered function
boundary set, which is a disassembler's job and a different issue." This is
that, for the one question it settles, and it leaves the reached-span set in a
form [#20](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/20) can
consume. The tool is [`bucket_c_codemap.py`](../../ec/tools/bucket_c_codemap.py);
the committed table is
[`bucket-c-codemap.csv`](../../ec/annotations/bucket-c-codemap.csv), one row per
site, and `--check` re-derives all 140 of them from the image. `--spans` is a
separate export of the same walk and carries **every descent it made**, seed and
callee alike, under a `#` header that says so — see "Limits" for what that
changed in the measurements below.

## The seed set, and why each element's code-ness is not in question

A recursive descent is only as good as where it starts, so the seeds are the
part worth arguing about. Four bases, all **discovered rather than restated**,
sorted so two branches produce the same table.

| base | names | contributes | why its code-ness is not in question |
|---|---:|---:|---|
| `vector-target` | 12 | 12 | the targets the image's own vector table points at |
| `stub` | 4 | 4 | the four BL51 bank-switch stubs |
| `trampoline` | 403 | 398 | the 403 entries the linker's own cross-bank path is made of |
| `bank-call-target` | 317 | 201 | reached from a bank-side call |
| **the seed set** | | **615** | `0x0000`-`0x7F04` |

**`vector-target`** is found by `build_ec_decompile.discover_vector_table()`
walking the image, and not by a list written out here. That function's
docstring records what a hardcoded list does: the two images in this dump both
defeat the textbook vector layout, so a hardcoded list silently seeds the
wrong addresses on one of them and the failure reads as "the firmware has no
handler there" rather than as a wrong tool.

**`stub`** is the four addresses at `0x1100`/`0x1114`/`0x1128`/`0x113C`, whose
`C0 08 74` prologue `audit_call_targets.py --self-test` counts four of in this
image and zero of in the PD image. Four entries for four stubs is the census's
own framing, not this tool's.

**`trampoline`** is the 403 entries `audit_call_targets.trampolines()` finds by
shape — `90 hi lo 02 11 xx` — which is the same framing `find_banks.py` keys
on, and which that same self-test pins as one unbroken 6-byte-stride run over
`0x1150`-`0x1ABC`. A run with no gap in it is a run the linker's own output
produced, which is a stronger claim about code-ness than any inference from
framing.

**`bank-call-target` is the weak one, and it is stated rather than assumed
away.** It is the census's **upper bound**, not its anchored subset, and it
inherits `bank-call-audit.md` §1's framing caveat whole: a byte scan over-counts,
and §4 of that file lists sites that score 24 of 24 on `converges_from()` and
are plainly inside an address table. Restricting it to anchored rows would read
the issue's phrase more literally and would make the whole question circular —
a site is reached because the scan named it, and then the walk is reported to
have reached it, which says nothing. §3 below is where that weakness shows up,
and it shows up hard: **every one of the 16 reached sites was reached from this
base.**

The bases overlap, which is why `contributes` is smaller than `names` for two
of them: most of the common-area addresses a bank-side call names are
trampoline entries, because the trampoline block *is* a dispatcher over the
common area. A base contributing fewer than it names is not a smaller
population; it is a population the stronger bases already held.

## The walk, and its terminator vocabulary

The descent primitive is `walk_branch_arms.descend()` — the repository's only
reusable one — with an entry-point worklist above it. `descend()` records an
`lcall`/`acall` as a callee and walks on, and ends the arm at an `ljmp`/`ajmp`
after recording that too, so the entry points those name are the caller's
business. That arrangement is not new: `bank_attribution.closure()` is built the
same way over the same function, and it is also why this is a new file rather
than a mode on it. `closure()` **hard-refuses to descend below `0x8000`**
(`BANK_FLOOR`), and that refusal is precisely the gap.

`walk_reason` is a closed vocabulary, and the split that matters is between
what the walk **decided** and what it **could not see past**:

| decided — the site is `not-reached` | could not see past — the site is `unknown` |
|---|---|
| `ret`, `reti`, `tail-jump`, `loop`, `mid-instruction`, `erased-run`, `no-seed-nearby` | `indirect-jump`, `instruction-budget`, `depth-limit`, `end-of-image`, `undecodable-byte`, `bank-edge-jump` |

Two of those cells are worth naming.

**`mid-instruction`** is the strongest negative the tool has, and it is the one
the census's over-count actually needs: the walk decoded *over* the byte, so the
`0x12`/`0x02` the scan found there is an operand byte of a real instruction and
not the first byte of one. It is a different claim from "not in any function",
and it is checked before the walk's own verdict, because `0xFF` — the erased
byte — is also `mov r7,a` and would otherwise make a block of erased flash read
as a run of instructions.

**`bank-edge-jump`** is the same unresolvability this whole issue is about,
seen from the other side. The walk follows control flow and stops when a branch
target is not in the common area at all: **31 of this image's 950 descents end
on a transfer into a bank window**, where nothing in the bytes says which bank
is mapped. It is a class of its own rather than a terminator inside the region
because it is the one terminator that is a *question* rather than an answer.

There is deliberately **no** "a branch led elsewhere" cell, although it looks
like the one that belongs there. It is unreachable: `descend()` walks a
PC-relative branch's fall-through inside the same block, so the nearest decoded
instruction below a gap is never a branch, and a block that does end on one did
so because a cut fired at it — which the cut rule reports instead, and which is
a different claim about the same byte.

## The classification: 16 / 123 / 1, each a count of this walk from this seed set

| verdict | sites | what it means |
|---|---:|---|
| `reached-by-walk` | 16 | on an instruction boundary inside a span this walk decoded |
| `not-reached` | 123 | outside every reached span; `walk_reason` says which terminator stopped the frontier, **not** how far below it this site sits |
| `unknown` | 1 | outside every reached span, and the walk could not decide |

By reason: `mid-instruction` 74, `tail-jump` 29, `ret` 20, `reached` 16,
`indirect-jump` 1. **Each of those is a count of this walk from this seed
set**, and none of them is a claim about what the byte is. `not-reached` is not
"is a data table" and `reached-by-walk` is not "is a call": a flow walk cannot
distinguish code from a table it wandered into, which is the sentence
`bank_attribution.py` and `disasm8051.py` both carry in their own module
docstrings, and it is why the next section reports three membership columns
against each other instead of reconciling them.

The single `unknown` is `0x0427C` (`lcall 0xA543`), and it is `unknown` because
the function containing it runs into a computed `jmp @a+dptr` that no byte scan
and no forward walk can follow. That is the `unknown` verdict doing the job it
exists for: "this method gave up here", with the reason in the next cell, rather
than a silent drop into the same column as a real negative.

### The three membership columns, and where they disagree

| reason | sites | in a listed data region | in a Ghidra function | is a seed |
|---|---:|---:|---:|---:|
| `indirect-jump` | 1 | 0 | 1 | 0 |
| `mid-instruction` | 74 | 0 | 63 | 0 |
| `reached` | 16 | 14 | 0 | 3 |
| `ret` | 20 | 11 | 5 | 0 |
| `tail-jump` | 29 | 10 | 11 | 0 |

`in_data_region` is `data_regions.region_at()`'s answer and is a **label,
never a filter** — `data_regions.py` refuses filtering rather than suppressing a
labelled site, and that discipline is copied here: a site inside a listed table
is still classified, and a site outside every listed table is not thereby a
call. `in_ghidra_function` is membership in a `[addr, addr+size)` from a
`common` row of `ec/decompiled/index.csv` — 753 of them, a boundary set this
walk never saw.

**The disagreement, stated and not resolved.** All 16 of the reached sites are
either inside a span `data-regions.yaml` lists as a table, or are a seed the
census itself supplied. **Not one of the 16 is inside a Ghidra function.** So
on these 16 the walk decoded an instruction boundary, Ghidra's boundary set has
no function covering it, and `data-regions.yaml` positively names 14 of them as
tables. Three readings survive that, and this write-up does not pick one:

- the walk wandered into a dispatch table and decoded it as code, which is
  exactly what a flow walk cannot rule out;
- the Ghidra functions are larger than the code and swallow the neighbouring
  table, which would make `in_ghidra_function` the wrong question;
- the `bank-call-target` seeds named table addresses, so the walk started
  inside tables and found what it was pointed at.

The `0x00390`-`0x003B4` run is the worked example of the first: thirteen
stride-3 entries in `common-032f-ljmp-table`, reached because a bank-side call
named `0x0390` and the walk decoded from there. Thirteen `lcall`s whose decoded
targets step by `0x600` is a dispatch table read as code, and it is in the table
as `reached-by-walk` because that is what happened — the walk did decode those
bytes — with the `in_data_region` cell beside it carrying the correction.

The `mid-instruction` row is a different shape and is worth reading as
carefully. **63 of its 74 sites sit inside a Ghidra function and inside no
listed data region** — and that is *agreement*, not disagreement: a function
body is a span, and an operand byte inside one is still inside the function, so
"inside a real function" and "not the first byte of an instruction" are two
questions with two true answers. Jointly they are the phantom signature the
census's over-count needed: **a `0x12`/`0x02` the byte scan found in the middle
of a real routine, as an operand of a real instruction.** The other 11 are in
neither a listed table nor a Ghidra function, so for those the walk is the only
thing that says anything, and what it says is that the byte is not an
instruction start.

So the columns conflict in exactly one place, and it is the one that was
already flagged: the 16 `reached-by-walk` sites, where the walk decoded an
instruction boundary and Ghidra's boundary set has no function covering it.

## The one target a trampoline also names: `0xE000`, and the two banks disagree about it

Exactly **1 of the 102** distinct bucket-C targets is also an address some BL51
trampoline names. If these were genuine calls into banked code one would expect
them to land on entry points; 101 of 102 do not. This one is `0xE000`, named by
trampoline entry `0x14F8`, which routes it to **bank 0**. Its one site is
`0x021C6` — the 24-of-24 site `bank-call-audit.md` §5's correction already
flagged as the one no listed region explains.

Two decoders, kept apart on purpose, and neither arbitrating the other
(`verify_reassembly.py` is explicit that Ghidra's SLEIGH, `sdas8051` and
`disasm8051.py` are three things and the comparison is worth nothing if they are
conflated):

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 bank0.bin
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 bank1.bin

$ r2 -a 8051 -e scr.color=0 -q -c 's 0xe000; pd 6' bank0.bin
            0x0000e000      900045         mov dptr, #0x0045
            0x0000e003      e0             movx a, @dptr
        ┌─< 0x0000e004      b43306         cjne a, #0x33, 0xe00d
        │   0x0000e007      12c8c5         lcall 0xc8c5
        │   0x0000e00a      7f33           mov r7, #0x33
        └─> 0x0000e00d      7f00           mov r7, #0x00
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xe000; pd 6' bank1.bin
            0x0000e000      32             reti
            0x0000e001      12888c         lcall 0x888c
            0x0000e004      90031a         mov dptr, #0x031a
            0x0000e007      128886         lcall 0x8886
            0x0000e00a      900520         mov dptr, #0x0520
            0x0000e00d      12888c         lcall 0x888c
```

**Bank 0 holds a well-formed function at `0xE000`**: read XDATA `0x0045`,
compare it against `0x33`, call `0xC8C5` and return `'3'` in `r7`, or return
`0x00`. Two arms, a `ret` on each, no byte out of frame. **Bank 1 does not.**
`0xE000` there is a single `reti` — not a prologue — followed by what reads as
an unrelated `mov dptr` / `lcall 0x888C` store sequence. So the linker's answer
and bank 0 agree: this address was a real bank-0 entry point when the
trampoline was generated, and bank 1 does not hold one.

That is the target resolved. **The site does not resolve, and the reason is the
most interesting thing in this write-up** — because it is a hole in the map
rather than a verdict about the bytes. Both decoders read the site cleanly:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x21c6; pd 4' bank0.bin
            0x000021c6      12e000         lcall 0xe000
            0x000021c9      e0             movx a, @dptr
            0x000021ca      f0             movx @dptr, a
            0x000021cb      1200e1         lcall 0x00e1

$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x021c6 -n 3 --runtime 0x21c6
0x21c6  12e000   lcall 0xe000
0x21c9  e0       movx a,@dptr
0x21ca  f0       movx @dptr,a

$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x021c6 --converge
0x021C6: 24 of 24 preceding anchors decode onto it, 0 step over it
```

Three things line up here, and they are the strongest evidence the bucket
offers: 24 of 24 anchors sync onto the byte, two independent decoders read the
same instruction from it, and that instruction names a bank-0 entry point the
linker itself recorded. The site is **not** inside a listed data region — the
nearest one, `0x219C`-`0x21B4`, ends 0x12 bytes before it, which is the
`0x021C6` §5's correction already established, and no listed region covers it.

So why is the table's verdict `not-reached`? **Because the walk has a
943-byte hole exactly there.** The nearest decoded instruction below
`0x021C6` is `0x1E2D` and the nearest above is `0x21DC`, and this seed set
decodes **zero** bytes in the 943 between them:

```console
$ python3 -c "
import sys; sys.path.insert(0,'ec/tools')
import bucket_c_codemap as B
d = open('ec/firmware/GMxMGxx_11.800','rb').read()
rows, seeds, reached, descents, cm, known, _, _ = B.build(d)
inside = [pc for pc in reached if 0x1E2D < pc < 0x21DC]
print(len(inside), 'decoded bytes between 0x1E2D and 0x21DC')"
0 decoded bytes between 0x1E2D and 0x21DC
```

**This is the one row in the table where the verdict is weakest, and the reason
is a fact about coverage rather than about the byte.** `not-reached` normally
means "the walk decoded around it and the site is not an instruction"; here it
means "the walk never went there". Those are different claims, and the
distinction is the whole reason the classification has a `walk_reason` column
next to the verdict: this row's reason is `tail-jump` at `0x1E2D`, which is
where the frontier below stopped, not a statement about `0x021C6` at all.

**A walk that did not reach a byte is not a walk that found the byte to be a
data table** — `docs/findings.md` §4c, and the rule that governs this whole
write-up. So the finding is not "this is a call" either. It is narrower and
more useful: **this is the strongest candidate for a genuine common-to-bank
direct call in the bucket, and the one thing standing between it and a verdict
is a gap in the code map where the site is.** Closing that gap is the next step,
and it is a question about where the common area's code is, not about banking.

If a genuine common-to-bank direct call does exist here, `offset_for_runtime()`
becomes a question about *what that function can be asked to do* — it keeps
returning `None`, which is correct for a target whose bank the bytes do not
name. That is raised as a follow-up rather than patched in silently.

## Limits

- **Every count is a count of this walk from this seed set.** Sixteen is not
  "16 calls". A different seed set, a different budget or a different depth
  would move it, and the table is regenerated rather than reconciled when it
  does. A zero anywhere would be "not found by this method", never "absent" —
  the caveat on `ec/annotations/registers.yaml`, and `docs/findings.md` §4c.
- **`reached-by-walk` is not "is a call", and `not-reached` is not "is a
  table".** 16 of the reached sites are in listed data regions; the walk
  decoded those bytes as instructions because it was pointed at them. A flow
  walk has no way to tell code from a table it wandered into, and this write-up
  reports the columns against each other rather than picking a winner.
- **Framing is not settled here in either direction.** `converges_from()`
  measures it and 24 of 24 does not prove it; §4 of the audit lists 24-of-24
  sites that are plainly inside an address table. The `0x021C6` case above is
  the same question with a live example.
- **The seed set inherits the census's upper bound.** All 16 reached sites came
  from the `bank-call-target` base, so the walk is partly graded on inputs the
  census produced and whose framing it does not vouch for. Seeds drawn from an
  upper bound can seed phantoms, and §3 is where that shows.
- **`not-reached` is not always a finding about the byte, and no column in the
  CSV says which kind a row is.** A site far below the walk's frontier is a
  statement about *this seed set* — the walk stopped and never came back — and
  not about the byte sitting there. `walk_reason` does **not** distinguish the
  two cases: it records which terminator stopped the frontier, so `0x021C6`
  reads `tail-jump` exactly as the other `tail-jump` rows do while lying 921
  bytes below the nearest decoded instruction. Nor is `0x021C6` a singleton —
  measured against the nearest decoded address below, a tail of `not-reached`
  rows sits hundreds of bytes past the frontier, not one row. *(Superseded in
  part: "hundreds of bytes" was inflated by the export carrying only the seed
  set's blocks. Measured against the nearest decoded address below, 44 of the
  123 `not-reached` rows sat at least 200 bytes past the frontier under the
  seed-only export and 14 do under the complete one; the rows that move are
  66, and every one of them moves **shallower**, because the full walk's decoded
  set is a superset of the seed set's. `0x021C6`'s own 921 is unchanged — its
  nearest decoded address below is `0x1E2D` under both.)* **A reader who wants
  the second kind has to measure the gap**, from the `--spans` export: take each
  `not-reached` `file_offset` and its distance to the nearest address in the
  decoded `block_lo`-`block_hi` ranges — which, since the export now carries
  every descent, are the whole walk's decoded bytes and not the seed set's.
  The figure is not carried in the CSV because it is a reading over two
  artifacts rather than a property of either, and a column that meant "the walk
  stopped here" would be a claim about coverage wearing a row's clothes.
- **Three of the 16 reached sites are themselves seeds**, which is circular by
  construction: a site the scan named cannot then be evidence that the scan
  found a real entry. They are in the table as reached, and the `is a seed`
  column above is what keeps that visible.
- **No hardware, no Windows, no capture, no `registers.yaml`.** Nothing in this
  write-up measures a byte. No register was read back, and no behavioural claim
  about any register is made or denied.
- **Not a code/data separation of the image.** That is
  [#20](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/20). This is the
  narrow slice of it one question needed, and `--spans` emits the reached-span
  set in a form #20 can consume: **every descent the walk made**, each block one
  row. *(Superseded: this bullet previously read "**1007 blocks over 615 entry
  points**", with the 335 callee-discovered entries "in the coverage count and
  **not** in the file", because `write_spans()` iterated `seeds` rather than
  the descents the walk returned. It now iterates the descents, and the export
  opens with a `#` block stating the population it covers, so a file that has
  lost descents is visibly short rather than silently so.)* The `basis` column
  still separates the two kinds — a `SEED_BASES` member from a seed the walk was
  given, `call-from-0xNNNN` for one it reached through a caller — so a consumer
  that wants the old seed-only view filters on that column and gets exactly it
  back. **A consumer has to drop the `#` lines before parsing**: `csv.DictReader`
  run on the whole file reads the first one as the fieldnames.
- **Banks 2 and 3 are taken as unused** on the word of `find_banks.py`, which
  `audit_call_targets.py` already takes as given; this tool does not re-derive
  it.
- **The self-test pins four figures and a set of refusals, not a proof.** The
  140/83/102/1 oracle is transcribed into
  [`test_bucket_c_codemap.py`](../../ec/tools/test_bucket_c_codemap.py)'s
  docstring from `bank-call-audit.md` §5 rather than read from this tool's
  output, so the tool cannot grade its own homework — but a census that moved
  would fail there rather than being explained here.
- **`--check` is not a gate.** It is not in
  `.github/scripts/agent-gates.sh`, which is a template copy the push token has
  no `workflow` scope to edit, and whose tool-list region is already contested
  by six prepared patches per
  [`prepared-gate-patches.md`](prepared-gate-patches.md). The suite is
  ungated and `tools/run-tests.sh` collects it today.

## Reproducing it

From the repository root. `--check` is the reproducibility claim, `--self-test`
the refusals, and the plain run prints the seed set, the terminator histogram,
the three counts and the one trampoline-named target in both banks.

```sh
python3 ec/tools/bucket_c_codemap.py ec/firmware/GMxMGxx_11.800 --check
python3 ec/tools/bucket_c_codemap.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/bucket_c_codemap.py ec/firmware/GMxMGxx_11.800
python3 ec/tools/bucket_c_codemap.py ec/firmware/GMxMGxx_11.800 --spans | head
python3 ec/tools/test_bucket_c_codemap.py
python3 ec/tools/test_bucket_c_codemap_spans.py

# the census did not move, and no region was edited
python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 | sed -n '/## 4/,/^$/p'
python3 ec/tools/data_regions.py --check

# the r2 transcripts above, from bank images cut from the same image
python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 bank0.bin
python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 bank1.bin
r2 -a 8051 -e scr.color=0 -q -c 's 0xe000; pd 6' bank0.bin
r2 -a 8051 -e scr.color=0 -q -c 's 0xe000; pd 6' bank1.bin
```

## Follow-ups this opens

- **`0x021C6` is a 24-of-24 `lcall 0xE000` that both decoders read the same
  way, naming a bank-0 entry point a trampoline also names, sitting in a
  943-byte hole in the code map.** It is the one row in
  `bucket-c-codemap.csv` whose `not-reached` is a coverage statement rather than
  a finding about the byte, and closing the hole is the narrowest useful next
  step. [`ec-data-regions.md`](ec-data-regions.md) §4 already follows it as a
  24-of-24 site no listed region explains; this write-up does not settle it
  and does not claim to.
- **31 descents end on `bank-edge-jump`** — a common-area branch into a bank
  window, which `audit_call_targets.py` §6 measures from the other side and
  finds to be a checked property of this image. Nothing in this table classifies
  those *sites*; they are the walk's frontier, and whether any of them is a
  common-to-bank direct call is the same open question.
- **The full code map.** `--spans` gives every block of every descent this walk
  made — seed-derived and callee-discovered alike, with `basis` saying which is
  which — so the gaps between them, and not just the gaps between the seeds, are
  where the next seed set has to come from. *(Superseded: this bullet previously
  read "the 1007 blocks, over the 615 entries this seed set reached", which
  understated the walk by the entries it reached through a callee.)*
- **The erased-fill `0xFF` blocks in the export are a separate defect.** 41 of
  the blocks `--spans` emits begin inside an erased run — `erased_index()` puts
  them all in the `0x7400`-`0x7F04` band at the top of the common area — and
  decode `0xFF` as `mov r7,a`, which is not code. That is the seed policy's
  problem rather than the export's: the export reports what the walk decoded,
  faithfully, and a walk pointed into erased flash has nothing to decode
  correctly. It is not folded in here so that each defect keeps one owner.
