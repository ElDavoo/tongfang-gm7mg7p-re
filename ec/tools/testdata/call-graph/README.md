# call-graph fixture

A miniature `ec/decompiled/` tree for `call_graph.py --self-test`. Eighteen
transfer sites, and one deliberate near-miss per mechanism the tool has a
trap for.

Every file here exists because the failure it covers is **quiet**. A graph
that cannot see a paged-form target does not crash, raise, or print a warning
— it prints a smaller number, and the number is the thing the tool exists to
produce. So each case below is a shape the real tree has and a naive parser
misses.

| file / row | what it pins |
|---|---|
| `decompiled/common/05E8.asm` | 3-byte `lcall` into the common area from a **bank0** listing, which must resolve to the `common` row and report `also_in=bank0` rather than a guessed bank |
| `decompiled/bank0/0EA2.asm` | the issue's worked example: 2 `lcall`s to 0x0EE8, and a 2-byte `ajmp` to 0x5A43 |
| `decompiled/common/0ECC.asm` | the second 0x0EE8 caller — what makes 0x0EE8 inbound=2 but cited=1 |
| `decompiled/common/00CF.asm` | reached by a single `ljmp` and no `lcall` at all |
| `decompiled/common/5A43.asm` | reached by 3 `ajmp` and **zero** `lcall`: the case a `lcall`-only scan calls unreachable |
| `decompiled/bank0/1F00.asm` | an anonymous caller, so `named_callers` and `callers` are not the same number |
| `index.csv` row `0xDEAD` | a function in the index that no transfer reaches and no comment cites — the self-test asserts it is **refused**, not invented |
| `ghidra-functions.csv` `0x0EA2` | writes `0x0EE8` twice and `0x64` once: one comment cited once, and the short-form data value credited to nothing |

The frame guard (`../citation_frames.py`) has its own four, and they are the
cases where a wrong answer is a *plausible* number rather than a missing one.

| file / row | what it pins |
|---|---|
| `decompiled/common/018C.asm` | the mixed sentence: the listing carries an `lcall` to **0x07D0** and one to **0x0A5A**, and the comment below names the first as a call and the second only as the top byte of `XDATA 0x0A56-0x0A5A`. Both addresses are reachable anonymous rows in this same fixture, so "the comment mentions a function" and "the comment cites a callee" are separate questions and the guard has to answer the second one |
| `decompiled/common/029B.asm` | the second 0x07D0 caller. Two comments say "calls 0x07D0" and two listings carry the `lcall`, so the self-test's `cited_by == inbound` is two framings agreeing rather than one number that happens to match |
| `ghidra-functions.csv` `0x0070` | the "calls to 0x110A, 0x158E, 0x0F75, 0x1594 and 0x00CF" list, which is the real `bank1` sentence: "to" is a data marker *inside* a code list, so a data veto over the sentence would throw away 21 real citations. It credits all four anonymous addresses; the fifth, 0x00CF, is a **named** row here and so is not a candidate at all, which is the rule the named-callee assertion already pins |
| `ghidra-functions.csv` `0x029B` | "The shared helper here is 0x5A43" — no verb inside the window, so the pair is reported `undecided` rather than credited or counted as rejected. The same pair is what the undecided **rendering** assertions below check |
| `decompiled/pd/10BC.asm` | a `pd` comment naming the common area's 0x07D0. The two programs have separate address spaces, so this is refused on program identity whatever the sentence says — the one rejection no lexical rule can reach |
| `decompiled/common/0D20.asm` | carries an `sjmp` to 0x0D40, a form `TRANSFERS` does not scan, and the comment on that row names the same `sjmp` |
| `ghidra-functions.csv` `0x0D20` | "it ends in an sjmp to 0x0D40" — the one committed sentence that put `sjmp` in the comment lexicon. The self-test asserts **both** halves: the citation is credited, and 0x0D40 still has no inbound edge, because the graph's transfer set and the comment lexicon are different sets |

The caller-listing gate (`../citation_callers.py`) has three more, and each is
the failure a rule that got the precedence wrong would produce.

| file / row | what it pins |
|---|---|
| `decompiled/bank1/F6A0.asm` | an all-`0xFF` run, `mov R7, A` to the end of the function, with a comment that reads as a genuine call enumeration. Seven real `bank1` listings have this shape; **the address is deliberately not one of them**, so the assertion is about the shape and cannot rot into a list of seven addresses |
| `ghidra-functions.csv` `0xF6A0` | that comment — "then calls to 0x0F75, 0x158E and 0x1594 … the .c body is not supported by these instructions". Every mention reads as a code frame and the citing listing still cannot make the call, which is the whole of the defect: **the guard is listing-scoped, not prose-scoped** |
| `decompiled/common/0071.asm` + `index.csv` rows `0x1400`/`0x1410` | the corroborated shape: two mentions with no frame inside the window, and two `lcall`s in the listing that settle them. `cited_by == inbound == 1` is the same two-framings-agree assertion `0x07D0` carries, and it only means something because the frame alone would have left both undecided |
| `decompiled/pd/10E0.asm` | a `pd` listing that **does** carry an `lcall` to the common area, with a comment naming it. It stays refused on program identity, so the precedence is pinned: a listing transfer never overrides a veto. `pd/10BC.asm` has no transfer and cannot carry this case, and `0x0CE1` is its own row rather than `0x07D0` because a `pd` transfer to an address the PD image has no row for resolves to the `common` row and would take 0x07D0's `inbound` to 3 |

The `-` byte-column padding in `0EA2.asm`'s `ajmp` is the trap the module
docstring names: a `[0-9a-f-]{2}` column regex matches nothing on that line
and the site vanishes. `0x1F00` exists so the fixture has an anonymous
caller, which is what makes `callers` != `named_callers` checkable.

Not a model of the real tree, and not meant to be: the real censuses are in
`ec/annotations/call-graph.md`, and the real `.asm` files are generated. This
tree is hand-written and hand-checked, which is what makes it an oracle.

The `evidence` column in both CSVs keeps the real tree's `ec/decompiled/…`
shape, and `../check_testdata_index.py` **does** resolve it — against the
repository root, which is a third base beside the one `Feeds` uses and the one a
nested `.asm` is read from. The self-test still never reads it. A cell whose
path the real tree does not have turns the check red, so six of this fixture's
addresses have their cell **empty**: `0x0D20` and `0x0D40` are fixture-only by
the two cases above, `0x0EA3` is a synthetic row naming an address that is named
nowhere, and `0x0071`, `0xF6A0` and `0x10E0` are fixture-invented addresses with
no counterpart under `ec/decompiled/` at all — `bank1/F6A0` is the one that the
`F6A0` table row above already declares "deliberately not one of them". The
neighbouring real listings (`common/0070.asm`, `pd/10BC.asm`) are present, which
is what makes `0071` and `10E0` absences rather than a directory that went
missing. `bank0,0EA3`'s cell is empty for the same reason its neighbours' are
not: repointing it at the real `bank0/0EA2.asm` would make it assert that this
row's decompilation is a *different function's* file.
