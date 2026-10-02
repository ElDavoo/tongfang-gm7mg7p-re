# The bank map, and a second image in the dump

Two things this file records, both over `ec/firmware/GMxMGxx_11.800` and both
re-derivable with the commands beside them:

- **A census of all 256 KiB by measured properties.** Nothing in the repository
  had walked the whole image before. It contains a 32 KiB block that is neither
  erased nor accounted for by the layout, and that block is a distinct firmware
  image carrying USB-PD protocol strings.
- **A joint scoring of the bank-to-file-offset mapping** against the trampoline
  call sites, which is the one load-bearing premise of the reassembly stretch
  goal that was still only a heuristic. The scoring ranks the offsets
  `make_bank_image.py` builds from first, and it says how far ahead they are
  and how much of that is evidence.

Neither tool writes a committed file, and nothing here was observed on
hardware. Every input is a committed file, so a re-run is a re-derivation and
not a diff.

```console
$ python3 ec/tools/firmware_regions.py
$ python3 ec/tools/bank_map_score.py
$ python3 ec/tools/firmware_regions.py --strings 0x28000
```

## 1. The census, and what it settles

`trace_xdata_refs.REGIONS` describes the image as `common` (0x00000-0x07FFF),
`bank0` (0x08000), `bank1` (0x10000), `erased` (0x18000), `pd-image`
(0x20000-0x2FFFF) and `erased` (0x30000). That is a description of what the
linker emitted, and it was never checked against the rest of the image.

| file | verdict | 0xFF | distinct bytes | printable runs >= 6 | head |
|---|---|---:|---:|---:|---|
| `0x00000` | not classified by this method | 14.2% | 256 | 199 | `02` `LJMP` |
| `0x08000` | not classified by this method | 8.8% | 256 | 6 | `e4` |
| `0x10000` | not classified by this method | 9.6% | 256 | 15 | `22` |
| `0x18000` | erased | 100.0% | 1 | 0 | `ff` |
| `0x20000` | non-erased (marker `ITE8850-PD`) | 2.4% | 256 | 8 | `02` `LJMP` |
| `0x28000` | not classified by this method | 8.9% | 256 | 37 | `01` `AJMP` |
| `0x30000` | erased | 100.0% | 1 | 0 | `ff` |
| `0x38000` | erased | 100.0% | 1 | 0 | `ff` |

The verdicts are deliberately weak, and the weakness is the finding rather than
a hedge over it. `erased` means *every* byte is `0xFF`, and nothing else is
asserted: **no block is ever labelled `code`.** A block of 8051 code, a block
of data tables and a block of a different architecture's code all read alike to
a byte census — 256 distinct byte values and no long `0xFF` run — so the tool
reports `not classified by this method` for four of the eight blocks, including
both live EC banks. Calling `0x08000` "code" would be an answer its method
cannot produce.

## 2. The `0x28000` block

`ec/README.md` §Layout accounts for `0x20000-0x2FFFF` as one self-contained
`ITE8850-PD` image of its own 64 KiB address space. The census says that span
is two, not one.

`python3 ec/tools/firmware_regions.py --strings 0x28000` prints 37 printable
runs, spread from `0x2A798` to `0x2F7AD`. All but one of them read as USB-PD
protocol strings — state-machine messages and version constants alike — rather
than compiler strings:

```
SRC Negotiate done     SINK Negotiate done    PR Swap        DR Swap
FR Swap                Set VBUS 5V            VCONN On       VCONN Off
Detect HW Reset        UsbPdVer:01.00         Hotfix:0000    ready to upgrade FW
```

Three measurements separate it from the `0x20000` image beside it:

- **37 printable runs against 8.** Of the 8 in the `0x20000` block, three are
  intentional — the marker and `ProtoVer:01.00 ` / `DriverVer:01.00` at
  `0x20160`/`0x20170` — one is `"(null)`, and four (`MNOx {`, `X@jL@fBB`,
  `P@n-@r.@`, `@.-PCIX`) are code decoding as ASCII by accident. The one
  exception among the 37 is at `0x2F7AD`, `2""""""""""`: a linear decode of
  the three bytes `02 f7 32` gives `ljmp 0xf732` — `0xf7` is the high target
  byte and that `32` the low one — and the ten `0x22` after it are `ret`
  instructions, so it is a stub before the erased tail and not a string.
  Several of the rest open with the
  preceding routine's `0x22` `ret` rather than with the message's first
  character, which moves where a run starts without changing what it says.
- **A different first byte.** The `0x20000` image opens `02 05 00` — an
  `LJMP` into the image, the ordinary way an 8051 reset vector is spelled. The
  `0x28000` block opens `01 90 08 52`, and `0x01` is `AJMP`.
- **No `ITE8850-PD` marker anywhere in it**, where the `0x20000` image carries
  one at file `0x20040`.

So: **a distinct 32 KiB firmware image containing USB-PD protocol strings.**
That is the whole of the claim, and three things are explicitly *not* claimed
by it.

**The architecture is not established.** The `01` head is exactly why a byte
census cannot settle it: `0x01` is `AJMP` on an 8051 and the start of something
else entirely on a different core, and the block's near-total opcode coverage
means the absence of unassigned byte values in it says nothing. Determining the
architecture is separate work; `disasm8051.py` should not be pointed at this
block until something has settled what it is.

**A second image is not a second port.** One Type-C connector can be driven by
one image. Nothing in this dump says how many physical USB-PD controllers the
board has, and "a second firmware image in the dump" is a question, not an
answer.

**It is not imported anywhere.** `ec/ghidra/manifest.csv` has programs for
`common`, `bank0`, `bank1` and `pd`, and this block is in none of them. Adding
it needs the architecture determined first, and a `--mode rebuild-project` that
cannot merge against another branch doing the same.

`trace_xdata_refs.REGIONS` still describes `0x20000-0x30000` as one
`pd-image` region. That is a description of the dump's layout and it is not
wrong about anything it is used for — `offset_for_runtime()` resolves within
the span — but the span holds two images, and a reader looking for the second
one should come here.

## 3. Banks 2 and 3

The linker's bank window is `0x8000-0xFFFF`, so bank N's file slot is the Nth
`0x8000`-sized slot from `0x08000`. `firmware_regions.py` prints that slot and
what is in it:

| stub | selects bank | file slot | that block |
|---|---:|---|---|
| `0x1100` | 0 | `0x08000` | non-erased, 8.8% 0xFF |
| `0x1114` | 1 | `0x10000` | non-erased, 9.6% 0xFF |
| `0x1128` | 2 | `0x18000` | **erased, 100% 0xFF** |
| `0x113C` | 3 | `0x20000` | non-erased, 2.4% 0xFF — the PD image's block |

This answers part of the question issue #20 asked — "banks 2 and 3 have zero
callers found — likely unused on this firmware build, **not yet confirmed why
they exist at all**". Bank 2's slot is measured erased, so a bank-switch into
it would select a window of nothing. Bank 3's slot is *not* erased; it is the
block the PD image lives in, so the four-bank window and the PD image overlap in
this dump. That is an observation about the layout, and what it means for the
linker's four-bank arrangement is **not** settled here.

What is unchanged is the reading of the zero itself. `find_banks.py` finds no
trampoline routing through `0x1128` or `0x113C`, and per `CLAUDE.md` that is
*not found by this method*, never *absent*.
`annotations/ghidra-functions.csv` is careful to say the same about callers and
is still right to. The new fact is about the file slot, which was assumed and
is now measured.

## 4. The bank map, scored

`find_banks.py` gives bank 0's mapping to `0x08000` at 51% and bank 1's to
`0x10000` at 92%. Both figures come from one thing: for each of the trampoline
call sites, is the byte at the candidate offset one of 32 hand-picked
"plausible first opcode" values. That is a single-byte membership test over 32
of 256 byte values, so random bytes score about 12.5%, and the distance
`ec/README.md` reports between a right offset and a wrong one is 51% against
32% — two mediocre numbers, not a margin.

`bank_map_score.py` scores each **pair** of offsets against the call sites
jointly, counting two landing-byte classes that cannot be an instruction at
all: `0xFF`, and the four values the MCS-51 map assigns to none
(`0x06`, `0x07`, `0x16`, `0x17` — the same criterion
`citation_gap_scan.py` uses for its `not-code` verdict). The population is the
committed one: the `calls_stub` column of
`annotations/bank-call-targets.csv`, with each site's runtime target read out of
the `mov dptr,#imm16` three bytes earlier in the image rather than re-derived.

| bank | sites | offset | erased | unassigned | runner-up |
|---|---:|---|---:|---:|---|
| 0 | 350 | `0x08000` | 0 | 0 | `0x10000`, 7 bad |
| 1 | 53 | `0x10000` | 0 | 0 | `0x08000`, 1 bad |

Both winners are the offsets `make_bank_image.py` builds its images from. Every
candidate pointing at the erased block at `0x18000` takes all of its sites as
erased landings, so there is no trivially good answer sitting in a gap.

**How much of that is evidence.** Five of 256 byte values are erased or
unassigned, so an offset with no relationship to the sites is expected to take
that fraction of them:

| bank | sites | expected bad landings | P(no bad landing) |
|---|---:|---:|---:|
| 0 | 350 | 6.8 | 0.001 |
| 1 | 53 | 1.0 | 0.352 |

The two rows are not equally good, and printing them together is the point.
Bank 0's clean score against an expectation of nearly seven is a real margin.
**Bank 1's is weak**: over 53 sites a chance offset would come up clean about a
third of the time, so bank 1's mapping rests on a much thinner base than bank
0's, and its 92% in `ec/README.md` overstated it long before this tool existed.

The joint ranking adds nothing here, and that is worth stating rather than
leaving implied: the two banks' independently-best offsets are already
different blocks, so the constraint that they stay different is not binding.
The joint search is what would catch a tool that pointed both banks at the same
block, and the fixture in `testdata/bank-map-score/` is what makes it a test
rather than a promise.

## 5. Framing, and why it is not the ranking

The obvious better metric is to walk instructions forward from each landing
byte, using `disasm8051.py`'s opcode-length table, and score on how far a walk
gets before running into padding. It is a strictly richer read of the same
bytes. It does not work, and the way it fails is the second finding here.

Bank 0's best offset **moves with the walk limit**:

| walk limit | best offset for bank 0 |
|---|---|
| 8 | `0x08000` |
| 16 | `0x08000` |
| 32 | `0x08000` |
| 64 | `0x10000` |

The ranking holds through a limit of 32 and inverts at 64, and the instruction
counts `bank_map_score.py` prints for the same two offsets are near-equal at
the shorter limits and clearly separated at 64. What accounts for the difference
is not measured here: a walk stops on the first erased or unassigned byte it
reaches, so how far it gets is a property of where those bytes sit in the
candidate block rather than of the mapping. A metric whose winner depends on a
parameter would be asserting something the data does not carry, so the ranking
uses the depth-independent composite and **prints the per-limit counts anyway**,
so the sensitivity is visible to anyone who would otherwise have assumed a
framing metric settles it.

This is also the honest reason the 51% figure was not simply raised. The
premise underneath `make_bank_image.py`, the Ghidra project, every `.asm`
listing and `verify_reassembly.py`'s byte check is a single-byte test whose
margin over the runners-up is a couple of percent. What the table above shows
is that the richer version of the same idea does not separate the two offsets
either. `verify_reassembly.py` cannot catch this premise being wrong, because
the listings it compares were produced *from* the image that
`make_bank_image.py` built at that offset — the check is circular with respect
to the mapping.

**Nothing here changes the mapping.** The scoring ranks what
`make_bank_image.py` already builds, so no listing, digest, `reassembly.csv`
row or the 7 MB `ec.gpr` moves, and `--mode rebuild-project` is not run. Had
the scoring contradicted `0x08000`/`0x10000`, acting on it would have churned
all of those *and* collided with any other branch rebuilding — which is a
follow-up of its own, not something to do inside a change that also found a
second image.

## 6. What is not established

- **No pair is confirmed.** §4 gives the ranking, the margin, and the chance
  baseline. A ranking over landing bytes is evidence about where bytes land,
  not about what the hardware selects.
- **A pair that scored badly here would not be disproved.** A wrong mapping
  whose targets all happened to land on instruction-shaped bytes scores like a
  right one, and nothing here tells those apart.
- **Computed targets are not in the population.** A target built at run time
  (`jmp @a+dptr` and its relatives) names no file offset to check. The
  population is the static call sites only.
- **The common-area callers naming a banked target are not scored.** They are
  bucket C in `annotations/bank-call-audit.md`, and
  `offset_for_runtime()` returns `None` for the shape because no byte resolves
  which bank a common-area caller meant.
- **Framing cuts both ways.** The walk ranking moves with its limit; the
  composite does not, because it does not walk. Neither is proof of alignment.
- **The `0x28000` block's architecture, chip, and controller count** are open,
  as §2 says.
- **No register's behaviour was observed.** Nothing in `registers.yaml` moves.

## 7. The gate wiring

`docs/ci/agent-gates-bank-map-score.patch` puts both tools' `--check` and
`--self-test` into the cheap tier as one `check_bank_map()`. It is **prepared
and not landed** — `.github/scripts/agent-gates.sh` is copied from the
agent-pipeline template and this branch's push token has no `workflow` scope,
so a human applies it with `git apply docs/ci/agent-gates-bank-map-score.patch`.

Its placement is a measurement rather than a preference, and it is the part
worth knowing before someone re-cuts it. The obvious shape is two entries in
the `for tool in` list and one `gate` line, and neither is available: the
`gate` list is saturated. Every patch in `docs/ci/` wanting a line takes a
three-line context window out of it, so cut a one-line patch at each insertion
point the way `git diff` cuts a real one, and try each against the committed
set in both orders — **each one collides with an existing patch and none
composes**. The tool list is saturated the same way. So the patch adds one
function at a free anchor and one call from
`check_ghidra_tooling`, whose own comment calls it the pipeline's self-tests and
staleness checks and whose every arm is a `--check` plus a `--self-test` on a
tool that needs no Ghidra.
`agent-gates-findings-frozen.patch` is the precedent for calling a check rather
than taking a `gate` line. `tools/test_agent_gates_patches.py` proves every
ordered pair, and this is the placement that needs no pair.

Until it lands, `bash tools/run-tests.sh` is what runs both suites, and
`testdata/firmware-regions/` and `testdata/bank-map-score/` are collected by
that runner rather than by a gate.

## 8. Follow-ups

1. **What is the `0x28000` image?** Its architecture, its chip, and whether it
   is a second physical controller or a differently-built sibling of the
   `0x20000` one. The `01` head and the absent `ITE8850-PD` marker are the open
   ends, and nothing here settles either.
2. **Bank 3's slot is the PD image's block.** §3 measured it and did not
   explain it. If the linker's four-bank window really does overlap the PD
   image in this dump, that is a layout question worth its own issue.
3. **`make_bank_image.py`'s docstring.** If this scoring is not to be treated
   as settling the mapping, the tool that builds the bank images from it should
   say so where a reader of that tool will meet it.
4. **Bank 1's margin is thin.** Fifty-three call sites is a small population
   for a five-in-256 landing test. Widening it would need the computed targets,
   which is item 5 above.

Nothing was observed on hardware and nothing was reflashed. The reflash test
harness issue #20 asks for is untouched and stays out of scope: no flash tooling
exists in this tree, and upstream `uniwill-laptop` issue #7 records a *register
write* alone needing a 30 s power-button EC reset, which is the reason that has
to be a human-at-the-machine project.