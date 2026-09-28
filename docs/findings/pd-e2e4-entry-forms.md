# The `pd` 0xE2E4 entry set: one entry at the first byte, and 35 bytes the export does not cover (issue #340)

The `pd,0xDA44` row in [`../../ec/annotations/ghidra-variables.csv`](../../ec/annotations/ghidra-variables.csv)
records a branch that cannot be taken and does not resolve it. `ec/decompiled/pd/E2E4.asm`
(`poll_d78a_for_indices_0_and_1`) is 15 instructions ending in one `ret`; the
`mov R7, #0x1` at 0xE320 sits immediately before the `ret` at 0xE322, so on every
path the export carries the callee returns the constant 1, and the caller's
`jz 0xDA4D` at 0xDA7C tests for 0 and is not taken.

**The row's own reading of that was left open**: it said 0xE2E4 "has no other
exit", which is a statement about the *export*, and never said whether 0xE2E4 is
one entry or several. Issue #340 asked for the entry set. It is one — and the
answer is not the whole of the finding, because **the span the export does not
cover is 35 of the body's 63 bytes and it ends in a second `ret` that returns
0**.

Everything below is a reading of committed bytes, measured by
[`../../ec/tools/pd_entry_forms.py`](../../ec/tools/pd_entry_forms.py) and
pinned by [`../../ec/tools/test_pd_entry_forms.py`](../../ec/tools/test_pd_entry_forms.py).
**No live run is implied.** There is no laptop and no Windows machine reachable
from a GitHub-hosted runner, and this issue needs neither: it is a control-flow
reading of committed bytes. No hardware test ran, no register was read back, and
no hardware behaviour was observed. **The PD image is a separate program with
its own address space, not a third bank** — every address below is an address
*in that program*, and `0xE2E4` in the main EC's common area is a different
byte. `pd-common-address-spaces.md` is the write-up on that boundary and this
file does not re-derive it.

## The body, and where its length comes from

The body is **0xE2E4 to 0xE322 — 63 bytes**, taken from the committed listing's
own instruction stream, first instruction to the `ret` that terminates it.

`ec/decompiled/listing-index.csv:2639` records `size=28` for `pd,E2E4`, and that
figure is correct: the listing's fifteen instructions sum to 28 bytes. **It is
not an extent.** The listing is not contiguous — 0xE2F8 through 0xE31A is a
35-byte hole — so reading `size` as `[addr, addr+size)` covers 0xE2E4-0xE2FF and
never reaches 0xE31B-0xE322, which is the `inc R2` / `cjne A,#0x1,0xE2E6` /
`mov R7,#0x1` / `ret` that decides the return value and the return the caller
sees. A tool that derived the body from that column would have stopped 35 bytes
short of the question. The two numbers are pinned together in the test so a
regenerated index cannot quietly reintroduce the truncation.

```
$ python3 ec/tools/pd_entry_forms.py
  0xE2E4 to 0xE322 (63 bytes), from the committed listing's own instruction stream
  28 of the 63 bytes are covered by an instruction; 1 committed gap(s) inside the span:
    0xE2F8-0xE31A  (35 bytes)  ea 12 b1 68 e0 fe a3 e0 ff 64 01 4e 60 15 ef f4 70 03
                                   ee 64 01 60 0c ef f4 70 03 ee 64 02 60 03 7f 00 22
```

The `mov R7` claim behind the untaken branch holds **over the listed stream**,
and the qualifier is load-bearing. Two instructions there load R7 — `mov R7,0x02`
at 0xE2E6 (opcode 0xAF, `MOV Rn,direct`, direct 0x02 being R2) and `mov R7,#0x1`
at 0xE320 — and only the second is on the path to the `ret`, immediately before
it. That is what the `pd,0xDA44` row already said and it stays said.

## The entry set

Two populations, reported together and never exchanged for one another.

**The listing population** is every transfer instruction in the committed
`ec/decompiled/pd/*.asm` files whose target is in the body: **three**, the
`lcall 0xE2E4` at 0xDA78 and the body's own `jz 0xE31B` at 0xE2EC and `cjne
A,#0x1,0xE2E6` at 0xE31D. These are decoded, so no operand byte can appear.
They are the three `population=listing` rows of
[`../../ec/annotations/pd-entry-forms.csv`](../../ec/annotations/pd-entry-forms.csv),
and that table's `origin` column is what holds them apart: only 0xDA78 is
`outside` and can enter the body, the other two are `inside` and are the
routine's own control flow. That is why the population is three and the entry
count below is one.

**The byte population** is every position in the image's 64 KiB whose bytes
spell a transfer form targeting the body: **eleven**, of which **three** sit
outside the body and can enter it. It is the wider of the two and it exists
because the listings cover **16,381 of 65,536 bytes (25.00%)** — a
listing-scanned absence is *not found by this method* and never *absent*
(`pd-common-address-spaces.md` measures the gap; `CLAUDE.md`'s standing rule is
why the byte scan is here at all). Every row it finds is a **candidate**, not a
caller.

Each candidate is scored with `disasm8051.converges_from()` **and** cross-checked
against the instruction starts parsed out of the committed listings. The two
halves are reported as a pair and neither settles anything alone:
`converges_from()`'s own docstring (`ec/tools/disasm8051.py:374-379`) says a site
nobody syncs onto "is not thereby misframed — it may simply be preceded by data
no linear walk can decode into alignment", and
`bank1-e582-entry-framing.md` §"One column deliberately not banked" is why no
third column is counted as corroboration.

| site | form | target | lands | frame | in a committed listing it is |
|---|---|---|---|---:|---|
| `0xDA78` | `lcall` | `0xE2E4` | first byte | 23/24 | an instruction start in `pd/DA44.asm`; the target is an instruction start |
| `0xE68B` | `ajmp` | `0xE2EF` | inner | 0/24 | no committed listing covers the site; the target is the 2nd byte of `mov B,#0x60` at 0xE2EE |
| `0x0BBA` | `ljmp` | `0xE322` | inner | 1/24 | 3rd byte of the `cjne R3,#0xfe,0x0bbd` at 0x0BB8 in `pd/0BAB.asm`; the target is an instruction start, `ret` |

**One confirmed entry found by this method is the whole of the entry claim: the
`lcall 0xE2E4` at 0xDA78, landing on the body's first byte.** It is not "the
only entry in the program". The other two candidates are each retired by a
different half of the pair, which is the point of reporting the pair:

- **`0x0BBA` is retired by the site half.** The byte is the rel8 displacement of
  the `cjne R3,#0xFE,0x0BBD` at 0x0BB8, which `ec/decompiled/pd/0BAB.asm`
  exports independently of any scan — the strong form of the argument, that the
  byte is reconstructible as a misframed read rather than merely unsupported.
  `bank1-e582-entry-framing.md` is the precedent and the phrasing.
- **`0xE68B` is retired by the target half.** Its target 0xE2EF is the *second
  byte* of the three-byte `mov B,#0x60` at 0xE2EE, not an instruction start; and
  the site itself is in no committed listing and scores 0 of 24 anchors. It is
  additionally readable as the low operand byte of an `ljmp 0x1041` at 0xE689 —
  a displaced alternative that explains the same bytes, the same shape of
  argument. **It stays a candidate, and this file does not claim it is not one.**

### The index tables

`ec/annotations/index-table-entries.csv` and `index-table-spans.csv` are
`decode_index_table.py` output over the main EC image;
`ec/annotations/pd-index-table-spans.csv` is `pd_index_tables.py`'s. A `common`
row at 0xE2E4 is a *different image's byte*, so eligibility is **measured from
the file offset each row names** rather than assumed from which tool wrote it:
**28 rows eligible, 231 discarded by the filter**, and no byte of an eligible
table's span spells a transfer into the body. Both numbers are printed and both
are asserted, because a scope filter whose discarded count is invisible is a
filter nobody can check.

## The 35 bytes the export does not carry

This is the part the issue's question turns on and it is not a candidate site,
so it belongs after the entry set rather than inside it.

The `lcall 0x10bc` at 0xE2F5 is three bytes, so the next instruction address is
**0xE2F8** — 20 of 24 anchors decode onto it — and the committed export for
0xE2E4 stops there. The 35 bytes from 0xE2F8 to 0xE31A are covered by **no
committed listing**, and read linearly they are a complete block ending
**`mov R7,#0x00` at 0xE318 and `ret` at 0xE31A**. They also contain
`mov R7,A` at 0xE300, a second R7 load 32 bytes before the one the row rests on.

Two readings are available and the committed tree does not choose between them.
Either Ghidra's function body for 0xE2E4 is right and those 35 bytes are a
separate routine reached only by fall-through — in which case the row's
"no other exit" is a claim about the export, exactly as amended; or the body is
narrower than the control flow actually reaches, in which case the `jz 0xE31B`
at 0xE2EC not being taken leads to 0xE2F8 and out through a `ret` returning
**R7 = 0** — which is precisely the value the caller's `jz 0xDA4D` tests.

**Nothing here decides between them, and the write-up does not lean.** Deciding
it is a question about a Ghidra function-body boundary, not about a transfer
form, and the method in this file measures transfer forms. It is named below.

## What moved, and what did not

**One row changed**: `pd,0xDA44` in `ec/annotations/ghidra-variables.csv`, one
comment field, **amended and not replaced** — the superseded "0xE2E4 has no
other exit" clause stays visible in place, per `CLAUDE.md`'s calibration rule and
the idiom already used in that file and at `common,0x158E` in
`ghidra-functions.csv`. The amendment adds the entry-set result, both retired
candidates, and the narrowing of the single-exit clause to the export, with the
35 bytes named as what it rests on.

**Explicitly not touched**, so a reader does not think it was overlooked:

- **`docs/findings.md`** — frozen, and `check_findings_frozen.py` fails a change
  that adds a section. The issue asked for the "no live run is implied" sentence
  *there*; it is the one instruction this change follows deliberately rather
  than literally, and it is the second paragraph of this file instead.
- **`ec/annotations/registers.yaml`** and the generated `ec/ghidra/xdata-symbols.csv`
  — nothing here is a register claim and no `status:` moves.
- **`ec/annotations/ghidra-functions.csv`** — no function entry is seeded. The
  reason is the instruction stream and not scheduling: 0xE2E4 is the first byte
  of the routine and the only confirmed entry is a call to it, so seeding
  anything inside would split a routine for no reason. 0xE320 stays where it is.
  **`--mode rebuild-project` is not required by this issue.**
- **`ec/decompiled/listing-index.csv`** — the `size` discrepancy is asserted and
  documented, not fixed. That file regenerates byte for byte, so a hand edit
  would be undone *and* would be a pure merge hazard; `bank1-e582-entry-framing.md`
  gives the same reasoning for not editing `bank-call-targets.csv`.
- **`.github/**`** — pipeline-copied, and the push token has no `workflow`
  scope. The new tool is therefore not registered in any gate: it is runnable,
  cited standalone and covered by `bash tools/run-tests.sh`'s `test_*.py` glob,
  which is the arrangement `ec/annotations/pd-image.md` §0 already records.
  Registering a gate is a human's change.

## What this does not establish

- **"One entry found by this method" is not "one entry in the program."** The
  byte scan is a pattern match over committed bytes and cannot tell a real
  transfer from a displaced read; the two candidates it retires are retired by
  the committed listings, not by the scan.
- **The 25% coverage is the residual gap, and it is not closed.** Annotating the
  pd listings that would cover any unlisted candidate is ordinary annotation
  work, and the byte scan is what makes the *unlisted* half visible rather than
  silent. No claim here is a whole-program claim.
- **Nothing here is a behavioural claim.** No live test ran, no register was
  read back, and no hardware behaviour was observed.
- **What `0xE2E4` does is not re-derived.** The `0x10BC`/`0x0424` arm, and what
  `0xD78A`'s R7 would mean if it were returned, are open — the issue says so and
  this file agrees. The entry question is the whole of what was asked.
- **Whether the vendor's source has a genuinely untaken branch there is not
  knowable from committed bytes.** It is recorded as the first of the issue's
  two readings, not as a conclusion.

## What this opens

- **Settle the 0xE2F8-0xE31A block.** Whether Ghidra's exclusion of those 35
  bytes from the 0xE2E4 body is right is the question the entry set cannot
  answer, and it is the one that decides whether `0xE2E4` has one exit or two.
  Re-deriving the body from Ghidra's own flow graph, or annotating 0xE2F8 and
  re-exporting, is the work. If the block turns out to be inside the body, this
  file's entry claim is unchanged and the `pd,0xDA44` row's return value is
  not.
- **Annotate the pd listings covering 0xE68B and 0xE2F8.** Either would let a
  future sweep say something stronger than "no committed listing covers this
  site". Ordinary annotation work; named, not done.
- **Credit the boundary-cut edges.** The `lcall 0xE2E4` at 0xDA78 is a real
  inbound edge to a pd function and
  `ec/annotations/call-graph-callees.csv` has no way to record one whose source
  and target are in a routine the export splits. Not measured here.

## The test that proves it works

[`ec/tools/test_pd_entry_forms.py`](../../ec/tools/test_pd_entry_forms.py)
(new; picked up by `bash tools/run-tests.sh`, which globs `test_*.py` per
directory — no gate edit). It asserts **from the committed image, the committed
listings and the committed tables**, not by re-running the scan that produced
them, so a regeneration that diverges fails loudly rather than passing on a
stale CSV:

1. The fifteen listed instructions, their 28 bytes, and that the same bytes read
   back out of the image at the listed addresses are the same 28 — and that a
   contiguous slice at `[0xE2E4:0xE300)` is **not**, which is the misreading
   being ruled out.
2. The listing is not contiguous: the 35 bytes at 0xE2F8-0xE31A are in no
   committed listing, and the span is 63 bytes while `listing-index.csv` records
   28.
3. The 35 unlisted bytes are pinned whole, with their second `mov R7` and their
   second `ret`.
4. The only R7 loads on a listed path are the two, and the deciding one is
   immediately before the `ret`.
5. The entry set, as set membership plus a landing-site check rather than a bare
   count: exactly three candidates from outside the body, exactly one of them a
   committed instruction start, and it is `lcall 0xE2E4` at 0xDA78 on the first
   byte — with the framing pair recomputed from the image.
6. `0x0BBA` is the `cjne` displacement `pd/0BAB.asm` already carries, and
   `0xE2EF` is the second byte of the `mov B,#0x60` at 0xE2EE.
7. The index-table scope filter: 28 eligible, 231 discarded, no eligible byte
   spelling a transfer into the body, and no EC-scope row naming an offset inside
   the pd extent.
8. The address-space rule, asserted: only `pd/E2E4.asm` covers any address in the
   span, `bank0 0xE256` and `bank1 0xE2D3` are a different image's bytes, and
   slicing the dump at `[0xE2E4:0xE323]` reads the main EC's common area.
9. The `pd,0xDA44` comment carries the sweep's answer **and** still carries the
   clause it amends, names the bytes the narrowing rests on, and moves no
   `status:` — presence checks, not exact-prose ones, so a later edit cannot
   silently drop the visible correction.

The tool's own `--self-test` asserts the same figures from inside the tool, plus
the two silent misreadings this shape invites, which the plan called for and
which are worth keeping: a listing line's operand text carries its own
four-hex-digit tokens, so an unanchored regex for an address matches a branch
target as readily as the address column (`jz 0xe31b` beside `E2EC`); and a pd
runtime address is not a file offset — the base is 0x20000, **not**
`PD_MARKER`'s 0x20040, which is the marker's offset *inside* the image, so
slicing the 256 KiB dump at a runtime address reads the wrong program and still
decodes.

## Re-deriving

From the repository root.

```sh
python3 ec/tools/pd_entry_forms.py
python3 ec/tools/pd_entry_forms.py --self-test
python3 ec/tools/pd_entry_forms.py --csv > ec/annotations/pd-entry-forms.csv
python3 ec/tools/pd_entry_forms.py --check
python3 ec/tools/test_pd_entry_forms.py

head -8 ec/decompiled/pd/E2E4.asm
sed -n '32p' ec/decompiled/pd/DA44.asm
grep -n '^pd,0xDA44' ec/annotations/ghidra-variables.csv
```

`ec/annotations/pd-entry-forms.csv` is generated by the third command and held to
the tree by the fourth.
