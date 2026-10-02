# bank-map-score fixture

**Nothing here was read from an EC.** `score-example-image.bin` and
`score-example-targets.csv` were written by hand to exercise
`../bank_map_score.py`'s branches; not one byte is evidence of anything about
the real dump, and neither file carries the `2026-01-01` timestamp a reader
would want to see on a capture. It is the directory README and the image's
construction that say so here, which is the same arrangement the binary census
fixture uses and for the same reason — see its README.

`score-example-targets.csv` is the sixth row of this fixture rather than
one of the table's own, for a reason worth stating: `../../check_testdata_index.py`
reads a `X.csv` named beside a backticked address in a self-indexed directory's
table as an `addr`-column reference, and this CSV mirrors
`../../annotations/bank-call-targets.csv`, whose address column is
`file_offset` and which has no `addr`. Naming it there would print
`not checked, not absent` on every run and leave the one property this
directory's index otherwise states -- that every reference resolves -- false.

**This is the fixture that makes the tool's answer mean anything.** Every
assertion `../test_bank_map_score.py` makes against the committed image is
satisfied by a tool that returns `0x08000` and `0x10000` without reading a
byte, because those are the offsets the committed image resolves to. So this
image is built with the banks somewhere else.

| file | what it pins |
|---|---|
| `score-example-image.bin` blocks `0x10000` and `0x18000` | bank 0's and bank 1's targets land on live bytes here — **not** at `0x08000` and `0x10000`. A tool reading the bytes answers `(0x10000, 0x18000)`; a tool reciting the committed mapping answers `(0x08000, 0x10000)` and every one of its targets lands on erased flash |
| `score-example-image.bin` blocks `0x08000`, `0x20000`, `0x38000` and `0x40000` | left as `0xFF` throughout, so the wrong candidates are rejected on erased landings rather than on a fraction, and the search has no trivially good answer sitting in a gap |
| `score-example-image.bin` bytes `0x1100`-`0x1127` | the two bank-switch stubs, copied from the committed image so `find_stubs()` recognises them. They are a tool constant (`STUB_PROLOGUE`), not a claim about the firmware, and copying them is what lets the fixture have real stubs without inventing some |
| `score-example-image.bin` site 0x0250, as the CSV row beside it | a row whose `calls_stub` names bank 1 over an instruction that is **not** `mov dptr,#imm16`. This is the population's drop path as bytes rather than as a synthetic row: it is the disagreement between the CSV and the image that `population()` refuses to score, and dropping it is what stops a target being read from three bytes too far left |
| `score-example-image.bin` sites 0x0200-0x0240 | the five scored sites, each a real `mov dptr,#imm16 ; ljmp <stub>` pair, with the runtime targets written into their own banks' blocks at the same offsets |

The `0x0250` row is the one that matters most and is the easiest to remove by
accident: delete it and the fixture still exercises the search, still answers
`(0x10000, 0x18000)`, and every assertion except the drop path still passes. It
is kept because a tool that scored that row would invent a target from whatever
two bytes happened to sit in front of the `ljmp`.

**It is *not* a prediction that the real bank offsets are `0x10000` and
`0x18000`.** They are not, and `../bank_map_score.py` over
`../../firmware/GMxMGxx_11.800` says so. This image exists only so that the
committed answer and the fixture's answer differ, which is the one thing a
committed-input-only assertion cannot tell.