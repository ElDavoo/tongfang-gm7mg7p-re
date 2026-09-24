# call-graph fixture

A miniature `ec/decompiled/` tree for `call_graph.py --self-test`. Six
transfer sites, six functions, and one deliberate near-miss.

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

The `-` byte-column padding in `0EA2.asm`'s `ajmp` is the trap the module
docstring names: a `[0-9a-f-]{2}` column regex matches nothing on that line
and the site vanishes. `0x1F00` exists so the fixture has an anonymous
caller, which is what makes `callers` != `named_callers` checkable.

Not a model of the real tree, and not meant to be: the real censuses are in
`ec/annotations/call-graph.md`, and the real `.asm` files are generated. This
tree is hand-written and hand-checked, which is what makes it an oracle.
