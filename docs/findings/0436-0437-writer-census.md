# The `0x0436`/`0x0437` writer census: eight stores and none of them a counter, and the PD's five sites name a base rather than a byte

`registers.yaml` said the only writer of `0x0436` was the zero-clear at bank1
`0xB8BF`-`0xB8D4`. That is true of the `wr` column and false of writers:
`ec/annotations/site-resolution.csv`, committed and never cross-read against
the note, carries seven more. The note is the file that was wrong; it is
corrected in place with its original claim left visible and the correction
dated beside it, the form `registers.yaml` already uses elsewhere.
Separately, all five PD-image sites of `0x0437` hand DPTR to
a routine that computes with the pointer and contains no `movx` in any of its
own bytes, so the "the PD reads the high byte and never the low one"
asymmetry is a property of a record array's base addresses and not evidence
about a 16-bit value.

Nothing here was measured on hardware, and no `status:` moves.

## 1. The writer census, and the correction

The note's claim was "The only writer is in the zero-clear at bank1
`0xB8BF`-`0xB8D4". That sentence is left standing in `registers.yaml` with a
dated correction beside it; this section is what the correction says.

`0x0436` has 17 EC-side sites. Grouped by `site-resolution.csv`'s own
`resolution` column, 8 resolve to `write` and 9 to `read`, and the 8 writing
sites are in 8 distinct routines:

| site | routine | what it stores |
|---|---|---|
| `0xB8BF` | `FUN_CODE_b88c` | `0`, directly (`movx @DPTR,A` with `A` = 0) |
| `0xB1D3` | `dispatch_0490_low3` | `0xFFFF`, from two immediates |
| `0xB255` | `FUN_CODE_b224` | XDATA `0x0518`/`0x0519`, verbatim |
| `0xB2CE` | `cmp_0404_vs_0518_then_store_0436` | `0x0201`, or the `0x0404`/`0x0405` pair |
| `0xBAD8` | `stage_0577_against_0834_0836` | `0`, from two immediates |
| `0xC28A` | `set_0432_from_0494` | `0`, from two immediates |
| `0xDBA8` | `FUN_CODE_db0b` | the `0x0514` × `0x0342` product |
| `0xDF45` | `FUN_CODE_def1` | the same product |

`ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1`
reaches the same split by a different route — it reads the image rather than
the census, and classifies `0x0436` as read 1, write 1, handoff→read 8,
handoff→write 7. So the issue's disagreement was never between two counts. It
was between a note written from the `wr` column, which counts stores *at the
site* and so counts one, and a `ho` column of 15 handoffs whose direction §4
resolves and which the note never folded back in.

The corrected wording is the smallest true one: the only **direct** store is
the zero-clear; seven further sites hand DPTR to a pair writer (`0x888C`
`write_r1r2_to_xdata_pair` for six of them, `0x889E`
`write_r3r4_to_xdata_pair` for the seventh) and are stores at the callee's
entry rather than at the site.

**`FUN_CODE_b88c` is a clear, not a maintainer.** Its body is four
`mov a,#0x00 ; movx @dptr,a` blocks — `0x0400`, `0x0401`, then `0x0436`-`0x0439`
with the pair gated on XDATA `0x0575` reading 0, the `jnz` at `0xB8BD` being
what skips it — interleaved with four calls to `zero_xdata_bytes_r2r1_through_r2r3`.
It stores zero. It has exactly one caller, bank1 `0xB867`, inside
`arm_05f2_countdown_0575_clears_0490`; a clear on a countdown arm is not what
would produce a running value. The seven handoff sites are.

`0x0438` carries the identical false sentence one entry down
(`BAT_VOLTAGE_MV`: "The only writer is the shared zero-clear"), and it is the
same defect: `0x0438` has 5 writing sites, one direct and 4 handoff-resolved.
Both notes are corrected in this change.

**No writer increments.** This is the part that bears on the capture in §4.
Three store immediates, two store a product, one copies another XDATA pair
verbatim, one stores a literal or a copy depending on a compare. None reads
`0x0436`, adds to it and writes it back — checked against the `inc`/`add`/
`addc` opcodes in each of the seven routines that reach a pair writer, and the
only `add`/`addc` among them (`FUN_CODE_db0b`) sits *after* the `0x0436` store
and builds a different register pair for a different destination. The `inc
DPTR` inside `write_r1r2_to_xdata_pair` walks the pointer to the second byte;
it is not an increment of the value.

## 2. The PD image does not consult `0x0437` as a byte

All five PD-image sites of `0x0437` are the same three-instruction shape, and
the routine they hand to is pointer arithmetic:

```console
$ cat ec/decompiled/pd/10BC.asm
10BC     a4 - -   mul      AB
10BD     25 82 -  add      A, DPL
10BF     f5 82 -  mov      DPL, A
10C1     e5 f0 -  mov      A, B
10C3     35 83 -  addc     A, DPH
10C5     f5 83 -  mov      DPH, A
10C7     22 - -   ret
```

**No `movx` at all.** `add_full_product_to_dptr` is `DPTR += A × B`, it
returns, and it dereferences nothing. `0x0437` is the *base* of a stride-`0x60`
record array, not a byte at that address. `ec/tools/check_pd_site_bases.py`
classifies all five `stride-base` from that decode, and
`ec/annotations/pd-0436-0437-bases.csv` is the committed per-site artifact:

What each site's *own* routine does with the pointer afterwards differs, and
the difference is `ljmp` against `lcall`: an `lcall` returns to the site's own
bytes, a tail `ljmp` does not. Three of the five tail-jump, so for those the
callee's `ret` returns the rebased DPTR to the *site's caller* and the site's
routine is over.

| PD site | hands to | class | how it hands over | what its own routine does with the pointer after |
|---|---|---|---|---|
| `0x358F` | `0x10BC` | `stride-base` | `ljmp` — tail call | nothing; the routine ends at the jump and `0x3599` is a separate entry point |
| `0x39BC` | `0x10BC` | `stride-base` | `ljmp` — tail call | nothing; `0x39C8` belongs to the routine entered at `0x39C5` |
| `0x6FF1` | `0x10BC` | `stride-base` | `lcall` — returns to `0x6FF7` | `0x6FFE` `lcall 0x10C8` `read3_xdata_to_r3r1_10c8` reads 3 bytes |
| `0x8724` | `0x10BC` | `stride-base` | `lcall` — returns to `0x872E` | the routine ends `ret` at `0x8735`, handing the rebased pointer to its caller |
| `0x8802` | `0x10BC` | `stride-base` | `ljmp` — tail call | nothing; `0x8808` belongs to the routine entered there |

**The three tail-jumping rows are not evidence either way about the record.**
The read at `0x3599` `read4xdata_to_r4_r7`, the discarded pointer at `0x39C8`
and the store at `0x8808` are all real instructions and all belong to
*separate* entry points — each reached by other `lcall`s elsewhere in the PD
image and by none from these five sites, since control leaves the site at the
jump. Whether the PD reads or writes a stride-`0x60` record at all is a
question about those callers, not about the five sites, and walking them is a
separate piece of work this census does not do. What the five sites establish
is narrower and is all this section claims: each hands `0x0437` to a routine
that computes with the pointer and dereferences nothing.

The effective address equals `0x0437` only when every index term is zero, and
no index bound is known here. So the lopsidedness the issue read as evidence
against the pair framing dissolves: `0x0434` and `0x0437` are not two halves
of a 16-bit value the PD reads unevenly, they are two stride bases in a
family `ec/annotations/pd-base-strides.csv` already records on its `0x60` row
and `ec/annotations/pd-reached-helpers.csv` already records on its `0x10BC`
row. The rule was written down before this issue, for `0x04A6`, in
`ec/annotations/pd-xdata-overlap.md` §3 — "never read or written as a byte at
all: all four sites load it as the *base* of address arithmetic" — and
`ec/annotations/xdata-inc-dptr-only.md` §4 states the discriminator in general
terms: **the address space is a property of the callee's body, not of the
token.** `0x0437` is a member of that class, not a new one.

**The direction was never unresolvable; it was unresolved by the walk.**
`trace_xdata_refs.py`'s `access` column says "direction unresolved here"
because its window stops at the `ljmp`/`lcall`, one instruction deep. That is
a statement about the method's depth, not about the bytes.

One spelling correction falls out of reading them. The census renders
`mov 0xf0,#0x60`, which is `mov B,#0x60` — `0xF0` is the SFR B, and Ghidra's
own listings of the same bytes read it that way (`ec/decompiled/pd/3635.asm`,
`ec/decompiled/pd/6FD5.asm`). All five sites load it, so `B` is `0x60` at every
handoff to `0x10BC`; `0x6FF1` and `0x8802` load it immediately *before* the
`mov dptr,#0x0437` (`0x6FED` and `0x87FE`) where the other three load it after.
The argument is visible in the disassembly rather than in the class column,
which reports the callee and not the argument.

**The containing functions are not named.** All five sites fall in
inter-listing gaps in `ec/decompiled/pd/`, so naming their routines needs a
seed and a `--mode rebuild-project`. That is a separate change, and the
classification stands on the committed bytes and the committed `size` spans
without it. The two `0x0434` PD sites at `0x37DA` and `0x878A` are the same
shape for the same reason — `mov DPTR,#0x0434` then `ret`, handing the base
back to a caller — and are recorded `unresolved` by the tool rather than
guessed at, because a base returned to a caller is not a dereference this
census can attribute.

## 3. `0x0201`, read as bytes and offered as a reading

`cmp_0404_vs_0518_then_store_0436` (`0xB2A0`) loads `0x0404`/`0x0405` into
R3:R4, `0x0518`/`0x0519` into R1:R2, compares them with
`cmp_r3r4_against_r1r2_16bit` at `0x8863`, and then stores. Both arms store:
the `jc` at `0xB2C8` skips the two immediate loads, so on borrow the pair
receives the `0x0404`/`0x0405` value and on no-borrow it receives R4=2, R3=1 —
`0x01` into `0x0436`, `0x02` into `0x0437`, little-endian **`0x0201`**.
Separately, `set_carry_if_0404_0405_is_0201` (`0xB214`) sets carry exactly
when `0x0404`/`0x0405` reads `0x01`/`0x02`: it loads R3:R4 from `0x0404`,
loads R1:R2 from `0x0436`, and calls `set_carry_if_r3r4_is_0102` (`0x887A`),
which reads R3 and R4 and nothing else. The `0x0436` read is therefore
incidental to that carry — R1:R2 is loaded and not consulted — so the test is
against `0x0404`, not against this pair.

`0x0201` is therefore a value the firmware both stores to this pair and tests
`0x0404` against — which is what a saturation or sentinel marker looks like in
bytes, and is offered here as **a reading of the encoding and nothing more**.
What the sentinel would mean, and whether `0x0436`/`0x0437` is where a capacity
figure would live, is not established by this and is not claimed to be. It is
recorded because the constant appears on both sides of a store and a compare,
which is a fact about the bytes and a lead worth someone's time, not a
conclusion about the field.

## 4. The `+0x14` ramp is not explained, and this change does not say it is

The one committed observation of `0x0436` on this board steps `0x70` → `0x84`
→ `0x98` → `0xAC` → `0xC0`, exactly `+0x14` about every 35 s
(`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv`). No writer
found by these methods increments, so **no committed image is found to produce
that ramp**, and the honest finding is the negative one: the two candidates
that store a computed value (`0xDBA8`, `0xDF45`) both take it from
`publish_0514_and_0342_product` at bank1 `0xCBF3`
(`ec/decompiled/bank1/CBF3.asm`), a `0x0514` × `0x0342` product whose
arithmetic this change does not work out and does not guess at.
Saying which of these produces a periodic ramp without decoding that product
would be exactly the "reads as" overclaim the note already declines once.

What would settle it is already written and waiting for a human at the
physical machine: `docs/hardware-tests/remain-capacity-0436.md` and the `0x0436`
arm of `windows/tools/ec_validate.py`. Neither is re-prepared here —
re-preparing finished preparation is not progress — and this runner has no
hardware and never will.

## 5. Both blind spots, named

Both of the issue's gaps could in principle hide a writer of this pair, and
they differ:

- **Issue #110, computed DPTR — partly already covered.** The 15 handoffs
  into `0x0436` *are* computed-DPTR sites: DPTR arrives in a register pair and
  is dereferenced by the callee, which no `MOV DPTR,#imm16` byte scan can see.
  `register_ref_table.py --callee-depth 1` resolves them by decoding the
  callee. What remains unseen is a writer behind a *depth-2* chain, or behind
  a callee outside the four pair helpers. That is the residual.
- **Issue #34, indirect `movx @Ri` + P2 paging — already run.**
  `find_indirect_xdata.py ec/firmware/GMxMGxx_11.800 --check` reproduces
  `ec/annotations/indirect-xdata-sites.csv` byte for byte, and its committed
  answer stands: anchored `movx @Ri` sites in the main EC, none resolving to
  an address, and `mov p2,#imm` occurring zero times. That zero is a property
  of the *encoding* the tool queries, and the tool says so itself — it is not
  a statement that the EC never sets P2 by another form. The argument is
  cited from that file rather than re-derived.

Both are lower bounds, in both directions. Per `registers.yaml`'s own preamble
and `docs/findings.md` §4c, a zero is "not found by this method" and never
"absent", and neither gap moves a `status:` in either direction.

## What this unblocks

The writer set is closed enough to be argued about: eight stores, named by
routine, none of them an increment. That is the precondition the live run in
`docs/hardware-tests/remain-capacity-0436.md` needs and did not have — a run
that reads a value which changes has to say which of eight candidates could
have written it, and before this the note's answer was one.

The `0x0437` PD finding is the more reusable half. `check_pd_site_bases.py` is
a sibling of `check_site_resolution.py`, not a mode on it: that tool filters
PD sites out on purpose, because the two programs have separate XDATA maps and
a direction for the other program's byte is a category error. This one keeps
that separation and answers the question the filter raises — what the site
*names* — for any address, so the next asymmetry in `static_refs_pd_image` is
a command rather than a hand argument. Its two limits are in its own docstring:
it does not follow control flow, and a class is a statement about instructions
rather than about behaviour.

Naming what the stride-`0x60` record *is* — a structure this repository has not
named, and one `ec/annotations/pd-xdata-overlap.md` §5.2 already reads
`0x04A1`-`0x04A6` as "field offsets into one strided structure" — is the
natural follow-up and is deliberately not started here. Neither is seeding the
five sites' containing functions, which is issue #175's shape of work.

Re-derive anything here with:

```console
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1
$ python3 ec/tools/check_pd_site_bases.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/check_pd_site_bases.py --check
$ python3 ec/tools/find_indirect_xdata.py ec/firmware/GMxMGxx_11.800 --check
```