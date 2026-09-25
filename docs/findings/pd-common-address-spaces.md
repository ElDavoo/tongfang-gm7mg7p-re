# The lone `pd` proxy edge was a missing annotation, not a cross-program call (issue #470)

The write-up for [issue #470](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/470),
which asked `group-proxy-populations.md` to settle the one question it had
deferred: is the single `pd` proxy edge a program-boundary question or a banking
one? **It is neither. It was a missing `ghidra-functions.csv` row**, and the
deliverable is that one row plus this note saying what the edge *is*, so the
next reader does not re-derive it.

**No grouping rule changed.** `cluster()`'s join logic is untouched,
`region_of()` is untouched, `cross_bank_groups` is untouched, and the proxy
rule still refuses to join two banks through a common-area node. The annotation
was the defect; the rule stays as it is, and `--self-test` grows rather than
gaining an exemption.

`docs/findings/group-proxy-populations.md` has the proxy accounting this moves,
`pd-common-address-attribution.md` has the adjacent reach-bookkeeping bug, and
`name-basis-and-groups.md` has the grouping layer itself. This file has the
program-versus-address question, the byte evidence, and what is left open.

---

## The question, and the answer

`group-proxy-populations.md` recorded the lone `pd` edge this way: "`pd 0xCB2A`
(`store_0803_0805_then_jump_c808`) targets `common 0x11C2`
(`load_dptr_bf57_tail_jump_1100`) … the two rows are not two endpoints of one
call, they are one row in each of two firmware images, and the question 'which
bank ran this' is the wrong question for them. `region_of()` has no vocabulary
for a program boundary, only for a bank one."

**The premise was right and the conclusion was not.** The two rows *are* one row
in each of two firmware images, and they are not two endpoints of one call. But
that is not what the edge was, and it is not why the proxy branch was reached.

The proxy branch is reached on exactly one condition:

```python
if taddr in by_addr.get(scope, {}):        # the caller's OWN scope has a row
    union(caller, (scope, taddr))          # same-scope join
elif taddr in by_addr.get("common", {}):   # ...and it does not
    ... build a proxy ...
```

So for a `pd` caller, reaching the proxy branch means **"there is no `pd` row at
this address"**. That is a statement about `ghidra-functions.csv`, and nothing
more. The branch never asks which image the caller is in, and it would take the
same branch for a `pd` caller whose target had no row at all, no `common` row,
and no `pd` row — that case is simply not an edge this tool can join or count.

`region_of()` needs no new vocabulary because it was never the thing being
consulted. A second region kind would have modelled a question the code does not
raise.

**"No `pd` row at 0x11C2" meant *not found in this table*.** It did not mean
absent from the PD program. There were 38 `pd` listings with no row; annotating
one leaves 37, and each of the remaining 37 is its own ordinary annotation
work rather than a classification problem.

---

## The row, and what is at 0x11C2

`ec/decompiled/pd/11C2.asm` was already exported — the function entry was seeded
from the call-target scan, so the listing existed with a `FUN_CODE_11c2` name
and no row behind it. Only the hand-read row was missing.

**`pd 0x11C2` is `dispatch_code_table_2byte_key`.** It is the two-byte-key twin
of `pd 0x119C` (`dispatch_code_table`), 0x26 bytes earlier and instruction for
instruction the same routine with one comparison added:

| | `pd 0x119C` | `pd 0x11C2` |
|---|---|---|
| entry | `pop DPH` / `pop DPL` / `mov R0, A` | identical |
| record test | byte +2 against A (`xrl A, R0`) | byte +2 against **B** (`cjne A, B`), then byte +3 against **A** |
| exit | `clr A` / `jmp @A+DPTR` at 0x11B6 | `clr A` / `jmp @A+DPTR` at 0x11DC |

Both consume the popped return address as a CODE-table pointer and scan 4-byte
records whose first two bytes are the target and whose last two are the key; a
record whose first two bytes are both zero supplies the default target from the
next two, and a match jumps to the target pair -- the first two bytes -- not to
the key bytes that matched. **Neither has a `ret`**: the only exit is the
indirect jump, so neither returns to its caller. That is the same framing
[`pd-0x38-consumers.md`](../../ec/annotations/pd-0x38-consumers.md) already
recorded for 0x119C, and it is why the row is graded `code-shape` — the name
rests on the instruction sequence and nothing else.

**`common 0x11C2` stays exactly as it was.** In the EC image those bytes are
`mov DPTR,#0xBF57` / `ljmp 0x1100` — a bank-select trampoline, which is what
`load_dptr_bf57_tail_jump_1100` and its `bank-switch` type say. **The two rows
are not two endpoints of one call, and merging them would be the exact
conflation this change removes.**

---

## The byte evidence

Offsets from `ec/ghidra/manifest.csv` and `ec/tools/make_bank_image.py`:
`common` is `firmware[0x00000:0x08000]`, the ITE8850-PD image is
`firmware[0x20000:0x28000]`. The two 32 KiB low areas are **not
interchangeable**:

```
$ python3 - <<'PY'
d = open('ec/firmware/GMxMGxx_11.800', 'rb').read()
common, pd = d[0:0x8000], d[0x20000:0x28000]
print("agree %d of %d (%.2f%%)" % (sum(a == b for a, b in zip(common, pd)),
                                   len(common),
                                   100 * sum(a == b for a, b in zip(common, pd)) / len(common)))
PY
agree 503 of 32768 (1.54%)
```

1.54% is what two unrelated 8051 images look like; 98.46% of the shared address
range is different code. At the ten addresses that carry rows in **both** scopes,
every one differs in its first four bytes:

| address | `common` row | `pd` row | `common` bytes | `pd` bytes |
|---|---|---|---|---|
| `0003` | `int0_vector_forwarder_to_052f` | `ljmp_0056` | `02 05 2f 22` | `02 00 56 ff` |
| `000B` | `timer0_vector_forwarder_to_0530` | `ljmp_0094` | `02 05 30 02` | `02 00 94 ff` |
| `0013` | `int1_vector_forwarder_to_0556` | `ljmp_00b2` | `02 05 56 02` | `02 00 b2 ff` |
| `001B` | `timer1_vector_forwarder_to_05b6` | `ljmp_00f0` | `02 05 b6 02` | `02 00 f0 ff` |
| `0023` | `serial0_vector_forwarder_to_05e6` | `ljmp_010e` | `02 05 e6 02` | `02 01 0e ff` |
| `0C7A` | `clear_low_nibble_of_1304` | `mul_r7_r5_r4_into_r6r7` | `cd ef cd 90` | `ef 8d f0 a4` |
| `0EF3` | `write_internal_ram_init_constants` | `or_32bit_r0r3_r4r7` | `78 b4 76 22` | `ef 4b ff ee` |
| `10F1` | `zero_xdata_200b` | `read3_code_to_r3r1` | `e4 90 20 0b` | `e4 93 fb 74` |
| `11C2` | `load_dptr_bf57_tail_jump_1100` | `dispatch_code_table_2byte_key` | `90 bf 57 02` | `d0 83 d0 82` |
| `383A` | `set_direct_bit_0c_3` | `unresolved_0x383A` | `d2 63 22 ed` | `12 0f cb c3` |

**This is a comparison of two images, not a statement about firmware behaviour.**
It says the two files are not the same program laid out twice. It does not say
what either program does at any of these addresses beyond what the rows
themselves already said.

**The ten is the figure after this change; it was nine.** `0x11C2` is the tenth
because it now carries a `pd` row beside the `common` one, and
[`pd-common-address-attribution.md`](pd-common-address-attribution.md) and
`ec/annotations/README.md` both say nine. Each is corrected in place with the
wrong figure left visible.

**The issue's "four" is a subset, and the subset is the useful part.** Four of
the ten are `pd`→annotated-`common` **call targets** — `0x0C7A` (from
`pd 0x36CB`), `0x0EF3` (twice, from `pd 0xC62B`), `0x10F1` (from `pd 0x0050`,
`0x10FD` and `0x9850`) and `0x11C2` (from `pd 0xCB2A`) — and those seven edges
are the whole of the overlap the grouping layer sees. The other six carry a
`pd` row that no `pd` row calls: the first five are the PD's interrupt-vector
table against the EC's, independently written, and `0x383A` is coincidence —
one image's `set_direct_bit_0c_3` and the other's `unresolved_0x383A` have
nothing to establish about each other, and nothing here says they do.

So the honest phrasing of the original note's "four addresses" is: **four of the
shared addresses are ones a `pd` row actually calls.** Six of the seven edges
joined the `pd` row and never touched the `common` one; the seventh was the gap
this change closed.

---

## What moved, measured

All of it static, over the committed listings, reproducible with
`python3 ec/tools/group_functions.py --report`:

| figure | before | after |
|---|---|---|
| `proxy_edges` | 196 (bank0=126, bank1=69, **pd=1**) | **195 (bank0=126, bank1=69)** |
| distinct `common` targets reached | 36 | **35** |
| edges onto rows a non-bank caller also reaches | 81 | **80** |
| edges onto `reached_only_by_bank` rows | 115 | **115** |
| `reached_only_by_bank` (rows) | 26 | **26** |
| `cross_region` (edges) | 27 | **27** |
| `callgraph_pd_0003` component | 413 | **414** |
| `callgraph_pd_0003` rows carrying the name | 303 | **303** |

**The two `callgraph` figures differ on purpose, and the reason is the seed.**
`group_rows()` gives a `type` seed precedence over a cluster, and the new row is
`type=dispatch`, so `pd 0x11C2` lands in `dispatch-tables` rather than in
`callgraph_pd_0003`. It still joined the component — 413 → 414 is the edge
`pd 0xCB2A` → `pd 0x11C2` that the proxy used to intercept — but the rows
carrying the group *name* stay at 303. Reading "303 → 304" off the CSV would be
wrong: `--report` is where the 303 named-row count is read
(`callgraph_pd_0003=303`), and the component size is the `One of 414` comment
the same tool writes into `ec/annotations/function-groups.csv`.

**`ungrouped` does not move under this change** — it is 478 on the merged
tree, 474 on either side of it, and the +4 is issue #267's four seeded `bank0`
routines landing ungrouped rather than anything #470 did — and the report's
split line prints the new total against the new edge count (70 of the 195, not
of the 196). The table above is what this change moved. Two things in the diff
are not in it, so they are named here rather than left to be found: the 303
`callgraph_pd_0003` rows in `function-groups.csv` all carry a component-size
comment that goes `One of 413` → `One of 414`, which is the component line above
expressed per row; and `group-proxy-populations.md` had a `456`/`440`
`ungrouped` figure that was **already stale before this change** (another pass's
drift), which had to move to 474/458 once the report block quoted verbatim
beside it was made current, and on to 478/462 when the merge brought #267's four
`bank0` rows with it. Neither is a figure this change altered, and the
tranche-history figures in that file and in §20 of `docs/findings.md` are
untouched.

---

## The wording, because the counting was never the problem

The `pd=1` was always counted correctly. What it was *read as* was the failure:
a single token inside a `bank->common` parenthetical, under a `bank->common`
label, reads as a banking result. A reader who took it at face value would
conclude the banking rule had a case it could not describe — which is how the
deferred question survived as long as it did.

`--report` now prints a non-bank caller scope as its own term, with the gap
stated on a line of its own, and says what closes it:

```
    bank->common edges cut by the per-bank proxy rule: 1 (1 non-bank caller scope(s) (pd=1)). ...
    1 of the 1 proxied edges have a non-bank caller scope, and that is an annotation gap
    rather than a banking result: the target has no row in the caller's own program, so
    the row the edge lands on is another image's function. Annotating the listing joins
    the edge directly and drops it out of this line. A listing with no row is not found
    by this method, never absent from the PD program; see
    docs/findings/pd-common-address-spaces.md.
```

On the committed tree that second line is now **absent**, because there is no
longer a `pd` caller on the proxy line. It is printed when the case comes back,
and two `--self-test` fixtures pin both halves: a `pd` caller whose target has a
`pd` row proxies nothing and joins directly, and a `pd` caller whose target has
only a `common` row proxies one edge and is reported as a gap. The second fixture
asserts the printed **strings**, because the whole point is the reading and not
the arithmetic — a tool that counted the gap correctly and printed it as a bank
result would pass every numeric assertion in the suite.

---

## The CB2A comment tension, recorded and not resolved

`pd 0xCB2A`'s comment said the `lcall 0x11C2` "exchanges the last result with
R3, ANDs it with R5, and jumps to 0xC808" — a call-and-return shape the new row
contradicts. `pd 0x11C2` has no `ret`; its only exit is `jmp @A+DPTR` at
0x11DC, and its two entry pops take the return address the `lcall` at 0xCB4A
pushed, leaving DPTR at 0xCB4D. The three instructions at 0xCB4D..0xCB4F are
therefore the bytes `pd 0x11C2` reads at that table pointer, not a tail the call
falls through to. **The comment is amended to say exactly that much and no
more**, with the reasoning here.

**What is deliberately left open.** What the table at 0xCB4D actually selects is
a question about one call site, and this change does not answer it. Its four
records read `cb 5d 01 08 / cb 66 02 06 / cb 6f 02 07 / 00 00 cb 76`: the first
three carry a nonzero target pair and a two-byte key, so a match on B=0x01 and
A=0x08 leaves for 0xCB5D, and the last is the `00 00` default, which selects
0xCB76. A here is whatever `pd 0x38D3` returned, which the bytes do not fix.
**That is as far as this goes.** Whether any particular call site is
reached, what it selects, and whether the record scan can run past the end of
the table it was given are separate questions that want their own issue; none of
them affects the classification, which turns only on which rows exist.

---

## What this does not establish

**Nothing here is a behavioural claim, and no live test ran.** Every figure is a
static measurement over committed `.asm` listings and the committed firmware,
reproducible with the commands above. No hardware is reachable from a
GitHub-hosted runner, and nothing in this change needs any.

**The byte comparison is a comparison of two images.** 503 of 32768 is a fact
about the dump, not about what the firmware does. It is not evidence that the
two programs never share code, and it is not evidence that they do.

**"No `pd` row" is not found-by-this-method.** 37 `pd` listings still have no
row, and that is a statement about `ghidra-functions.csv`, not about the PD
program. Annotating them is ordinary annotation work and may move these figures
again; the classification will not change, because it never depended on which
rows exist.

**Nothing here says the two dispatchers at 0x119C and 0x11C2 are called with the
same tables, or that their tables overlap.** They are the same routine shape
0x26 bytes apart and this change says nothing further.

**No file now claims a cross-program call the bytes do not support**, which was
the issue's completion bar. `common 0x11C2` keeps its own name, its own
`bank-switch` type, and its own bytes.
