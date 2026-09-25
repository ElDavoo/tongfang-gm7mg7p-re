# call-graph fixture

A miniature `ec/decompiled/` tree for `call_graph.py --self-test`. Fifteen
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
| `decompiled/common/0EA2.asm` | the issue's worked example: 2 `lcall`s to 0x0EE8, and a 2-byte `ajmp` to 0x5A43 |
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
| `ghidra-functions.csv` `0x029B` | "The shared helper here is 0x5A43" — no verb inside the window, so the pair is reported `undecided` rather than credited or counted as rejected |
| `decompiled/pd/10BC.asm` | a `pd` comment naming the common area's 0x07D0. The two programs have separate address spaces, so this is refused on program identity whatever the sentence says — the one rejection no lexical rule can reach |

The `-` byte-column padding in `0EA2.asm`'s `ajmp` is the trap the module
docstring names: a `[0-9a-f-]{2}` column regex matches nothing on that line
and the site vanishes. `0x1F00` exists so the fixture has an anonymous
caller, which is what makes `callers` != `named_callers` checkable.

Not a model of the real tree, and not meant to be: the real censuses are in
`ec/annotations/call-graph.md`, and the real `.asm` files are generated. This
tree is hand-written and hand-checked, which is what makes it an oracle.
