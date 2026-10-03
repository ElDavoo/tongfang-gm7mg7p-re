# No transfer in bank 1 names `0xC1E7`, which is why a reading of it stood unchallenged (issue #336)

The BL51 forwarder census
([`forwarder-target-bank-census.md`](forwarder-target-bank-census.md), issue
#465) settled *which bank* each forwarder's `imm16` is read in. It did not
answer a second question that decides what may be concluded from a listing at
one of those addresses: **which program's own transfers name it.** Those are
different questions, and answering the first does not answer the second — which
is the gap this closes.

`ec/annotations/ghidra-functions.csv` `bank1,0xC1E7` is the worked case. It
reads like a live routine with three callers' worth of traffic through it, and
the answer is that **no transfer in bank 1 that the scan can resolve names
`0xC1E7`** — and the one place in the whole tree that does put the address in
bank 1's bytes, `bank1,198A` (`trampoline_to_c1e7`), is a forwarder: its
`mov DPTR,#0xC1E7` is a value used as data and only later transferred by the
`ljmp 0x1100` beneath it, which selects bank 0. So a reader who greps
`ghidra-functions.csv` for `0xC1E7` finds that row, and it is already the
agreement rather than the disagreement: `bank1,198A` resolves the immediate in
bank 0, which is exactly what the scan finds there.

## The measurement

Every figure here comes from one command, which reads committed files only and
writes none:

```console
python3 ec/tools/entry_reachability.py 0xC1E7
```

and its per-(address, program) table:

```console
python3 ec/tools/entry_reachability.py --csv 0xC1E7
```

`0xC1E7` asked of each program in turn, over that program's own window:

| program | transfers naming it | of |
|---|---|---:|
| `common` | none | 6,184 |
| `bank0` | one, `lcall` at `0xD9E7` | 6,297 |
| `bank1` | **none** | 6,074 |

The denominators are the count of transfer sites scanned in each window, printed
beside the answer because an empty row means nothing without the window it was
empty over. Bank 0's single site is the `lcall` at `0xD9E7` that
[`bank-call-targets.csv`](../../ec/annotations/bank-call-targets.csv) records
independently, and it reaches bank 0's `test_1664_bit0`
(`ec/decompiled/bank0/C1E7.asm`).

**This is a per-program answer, and the distinction is the finding.** A 16-bit
`lcall` target does not name a bank: the same three bytes are a same-bank and a
cross-bank call. A tool that scanned the whole image once, or that resolved the
bank from the forwarder rather than from the caller's own bytes, would hand bank
1 bank 0's site and report the row's reading as sound. The suite asserts the
split rather than the total for that reason.

## How bank 1 reaches the entry without naming it

Not by a transfer — by **fall-through**. Thirteen bytes at bank 1 `0xC1DA`–`0xC1E6`,
covered by **no committed bank-1 listing**, decode as:

```
0xC1DA  90 04 90   mov  DPTR, #0x0490
0xC1DD  e0         movx A, @DPTR
0xC1DE  30 e4 4e   jnb  0xe4, 0xc22f
0xC1E1  30 e6 4b   jnb  0xe6, 0xc22f
0xC1E4  30 e2 55   jnb  0xe2, 0xc23c
0xC1E7             <- the entry, by falling off the end of the last jnb
```

`jnb` jumps *when the bit is clear*, so control reaches the entry when all three
bits are **set** — the opposite of the shape the mnemonics suggest at a glance,
and the reason the decode is given in full rather than summarised. The `jnb`
operands are bit addresses, not XDATA addresses: `0xE4`, `0xE6` and `0xE2` are
ACC bits 4, 6 and 2, so each test is of a bit of the byte `movx` has just read
into the accumulator rather than of a byte of its own.

`entry_reachability.py` reports a fall-through as its own thing rather than
counting it as a caller, because it is a different kind of fact: a call site is
something the linker wrote down, and a fall-through is a consequence of what it
did not write.

Those thirteen bytes being unlisted is a coverage limit, not an absence of code
— the entry they fall into *is* exported (`latch_0498_bit1_or_bit3`), and only
the run is not. Landing the listing needs a `--report` run on the pinned
assembler ([`ec/ghidra/README.md`](../../ec/ghidra/README.md)).

## What the row said, and what is corrected

The row carried two sentences, both read against bank 1, and both are now
corrected **in place with the withdrawn text left visible** per `docs/findings.md`
§4a:

> "no instruction in the body writes R7, so the R7 that 0xA389 tests after
> `lcall 0x198A` is not this routine's to set"

True of the bank-1 bytes the row describes, and not what `0xA389` runs.
`lcall 0x198A` reaches **bank 0** (the stub at `0x1100` selects it), and there
`0xC1E7` is `test_1664_bit0`, which does write R7.

> "Two further BL51 forwarders land inside the body, 0xC201 from 0x1762 and
> 0xC209 from 0x1768"

`bank1,1762` and `bank1,1768` both tail-jump to the stub at `0x1100`, so their
immediates name bank 0 — where `0xC201` and `0xC209` are two standalone
eight-byte entries, `set_1604_bit1` and `clear_1604_bit1`, on XDATA `0x1604`
(`ec/decompiled/bank0/C201.asm`, `ec/decompiled/bank0/C209.asm`), not addresses
inside a body at all.

## Why the row was wrong for so long

This is the part the correction adds. A body no transfer in its own bank names
cannot be checked against anything in that bank. Every symptom a bank-1 reading
would produce — no R7 written, no return value to explain — is exactly what
such a body looks like from the inside. The reading was not merely
measured in the wrong bank; it was **unfalsifiable in the bank it was measured
in**, and stayed that way until the question was asked per program rather than
per address.

## What this is not

- **Not a claim that the code is dead.** "Names it nowhere" is **not reached by
  this method**: it covers the three statically resolvable transfer families,
  and not an indirect transfer (`jmp @A+DPTR` and its siblings compute their
  target at run time) or a value used as data before being transferred. That is
  `registers.yaml`'s own caveat about its scans.
- **Not a behavioural claim.** Nothing here was observed on hardware: no
  hardware, no Windows, no live run. Reachability says the linker put a
  reference at an address; it says nothing about what the EC does there. No
  `status:` in `ec/annotations/registers.yaml` moves on any of it, and
  `--self-test` holds that to what the tool reads — it watches `open` over a
  whole run and asserts the recorded set of paths is the firmware image alone,
  so a second input of any kind turns the check red.
- **Not a count of this repository's text.** The denominators above are transfer
  sites in the committed firmware, which moves only if the firmware does.

## The follow-up this opens

Reachability is now answerable per program for any address, and the natural next
question is the one this row raises: **how many annotated entries does their own
bank never name?** That is a census over the whole index, it moves whenever a
listing lands, and it is deliberately not answered here — one address, measured
and cited, is worth more than a figure that every merge would have to edit.