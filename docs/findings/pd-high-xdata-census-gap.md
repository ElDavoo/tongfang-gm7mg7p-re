# Every `MOV DPTR` target in the PD image's `0xFFxx` region has a per-address verdict, and the largest group hands DPTR to a routine that adds it to a word rather than dereferencing it (issue #430)

`ec/annotations/pd-xdata-overlap.md` §5.3 counts the PD image's high XDATA
twice and stops: a `90 hi lo` byte scan of `ec/firmware/GMxMGxx_11.800` finds
**45 distinct `0xFFxx` targets across 170 sites** in the PD image, and
`xdata_register_map.py` pins **23** of them in `XSPACE_PD_HIGH`. The gap
between those two numbers is this file's subject, address by address.

The instrument is `ec/tools/pd_high_xdata_probe.py`, and every figure below is
its own output. Nothing here is hardware evidence: each one is read off the
committed firmware image, the committed `ec/decompiled/pd/*.asm` listings and
the committed census, and no register was read back from an EC.

## The gap is twenty-five, and the issue's twenty-two compares two populations

The issue's prose — and its title — say twenty-two, and its list holds
twenty-five. **The list is the one that reproduces from the image, and the
arithmetic is where the two went apart.** Three of the 23 pinned census
addresses are not `MOV DPTR` operands at all: `0xFFC1`, `0xFFD1` and `0xFFDB`
are reached only by an `inc DPTR` from the address below, so a byte scan never
counts them. That makes the residue

> 45 scanned − 20 in both populations = **25**

and not `45 − 23 = 22`, which subtracts a scan from a census. The three that
make the difference are `XSPACE_INC_ONLY`, and they are the reason the probe
classifies the **union** of the two sets: 48 addresses in all, every one of
them with a verdict, and the report prints the scan's 45, the census's 23 and
the 20 that are both rather than only the difference between two of them.

A site is likewise counted under the address it names *and* under the address
one byte above it, which is what an `inc` continuation is. The per-address site
lists below are therefore longer than the scan's 170 and the figure is printed
beside them rather than reconciled by hand.

The issue's list is reproduced by the suite from the issue's own text rather
than from the tool, because a suite that transcribed the tool could only prove
the tool agrees with itself.

## The mechanism is absence of a function, not a function that failed to decompile

§5.3 attributed the residue to "the ordinary lower bound: a function that did
not decompile carries its sites nowhere". **That sentence is retracted in place
in `../annotations/pd-xdata-overlap.md` §5.3, and the mechanism is the
opposite of a lower bound in the ordinary sense: there is no function there at
all.**

The 102 byte-scan sites belonging to the 25 split **16 on a listed instruction
boundary and 86 in bytes no listing covers.** The PD image's listings decode
**9,277 distinct instruction addresses of its 0x20000-byte image — 7.1% — and
stop at runtime `0xF7B7`**, which is below the whole `0xFFxx` region. Nearly
nine sites in ten are not inside any function's span because there is no
function to be inside.

`ec/ghidra/manifest.csv` says the same thing from the other side: the PD row is
`functions=541, decompiled=541, failed=0`. **No function Ghidra found in the PD
image failed to decompile**, so there is no decompilation failure for the
sentence to be about. What the region needs is not a fixed decompiler but
function *entries* at addresses that are currently raw bytes, which is a
seeding question and not a diagnosis of one.

## Five verdicts over the residue, and the one the issue did not name is the largest

The probe gives each address one word from a closed vocabulary, and prints the
per-site tally beside it because the single word is the *strongest* claim any
of an address's sites supports and is often not the whole truth.

| verdict | residue addresses | what it says |
|---|---|---|
| `literal-read` / `literal-write` | 11 | a `movx @DPTR` in the same straight-line run dereferences the seed, in that direction |
| `callee-non-xdata` | 4 | the window ends at a call, and the routine it reaches never names the external data space |
| `callee-rebases` | 7 | the routine reached dereferences `DPTR + R1:R2`, so the seed is a base and the byte touched is elsewhere |
| `callee-derefs` | 2 | the routine reached dereferences DPTR as it stands, so the address is the one read |
| `not-found-by-this-method` | 1 | no `movx` was reached, and the note says which rule stopped the window |

**`callee-non-xdata` is the category the issue did not name, and by site it is
by far the largest** — 84 of the residue's site instances, against 16 for
`callee-rebases` and 34 for the two `literal` words together. It is four
addresses rather than seven because an address is counted once however many of
its sites say the same thing, and the report's tally is where the two readings
are told apart. All 16 of the listed sites hand DPTR to `0x122F` (15 of them)
or to `0x7059` (1), and `pd/7059.asm` is a single line — `lcall 0x122F` — so
the two are the same destination. `pd/122F.asm` is
`add_dptr_to_word_0d0e_ea_guard`: it adds DPTR into the internal-RAM word at
`0x0D`/`0x0E`, stores the low byte back to direct `0x0E` and returns, and its
seventeen rows contain **no `movx` at all**.

```console
$ sed -n '7,23p' ec/decompiled/pd/122F.asm
122F     e5 0e -  mov      A, 0x0e
1231     25 82 -  add      A, DPL
1233     f5 82 -  mov      DPL, A
1235     e5 0d -  mov      A, 0x0d
1237     35 83 -  addc     A, DPH
1239     f5 83 -  mov      DPH, A
123B     b5 0d 04 cjne     A, 0x0d, 0x1242
123E     85 82 0e mov      0x0e, DPL
1241     22 - -   ret
1242     10 af 06 jbc      0xaf, 0x124b
1245     85 82 0e mov      0x0e, DPL
1248     f5 0d -  mov      0x0d, A
124A     22 - -   ret
124B     85 82 0e mov      0x0e, DPL
124E     f5 0d -  mov      0x0d, A
1250     d2 af -  setb     0xaf
1252     22 - -   ret
$ grep -c movx ec/decompiled/pd/122F.asm
0
```

So at those sites `mov DPTR,#0xFFFF` is not a pointer being loaded — **DPTR is
consumed as an integer.** Counting them as XDATA addresses would be exactly the
overclaim `xdata-register-map.md` §5.1 is written against, and it is why
`callee-non-xdata` is a verdict rather than a silent skip. The issue did predict
a helper here; the helper is real, and it is not an accessor.

**`callee-rebases` is the same argument one step on.** `pd/0D38.asm` adds the
caller's `R1:R2` into DPTR and only then dereferences it:

```console
$ sed -n '7,18p' ec/decompiled/pd/0D38.asm
0D38     bb 01 10 cjne     R3, #0x1, 0x0d4b
0D3B     e5 82 -  mov      A, DPL
0D3D     29 - -   add      A, R1
0D3E     f5 82 -  mov      DPL, A
0D40     e5 83 -  mov      A, DPH
0D42     3a - -   addc     A, R2
0D43     f5 83 -  mov      DPH, A
0D45     e0 - -   movx     A, @DPTR
0D46     f5 f0 -  mov      B, A
0D48     a3 - -   inc      DPTR
0D49     e0 - -   movx     A, @DPTR
0D4A     22 - -   ret
```

A seed in front of a call to that is a base, and the byte read lands at
`DPTR + R1:R2`. **That the routine dereferences something is not evidence that
it dereferences the seed**, and reading it as such would be the overclaim in the
other direction.

`callee-derefs` is kept separate for the same reason: `pd/10C8.asm` is three
`movx a,@dptr` with an `inc DPTR` between each and no arithmetic, so a seed in
front of a call to it really is the address read. Lumping it in with `0x122F`
would file a real three-byte read beside a routine that touches no external
memory at all.

## Eleven of the twenty-five are XDATA by the same encoding argument §5.3 makes

`xdata_space()` returns `None` for all 25, because it reads the committed
`.asm` and no listing covers these sites. Decoding the uncovered bytes with
`disasm8051.py` — which shares no code with Ghidra's SLEIGH, and is the
instrument `citation_gap_scan.py` already uses for this same gap — finds a
dereferencing `movx` immediately behind the seed at **eleven** of them:

| address | direction | seed sites |
|---|---|---|
| `0xFF00` | read | `0xAAA1` `0xAB96` `0xC424` |
| `0xFF02` | write | `0xA699` `0xA751` |
| `0xFF04` | read and written | `0xA684` `0xA692` `0xA6B2` `0xA6CD` `0xA6DB` `0xA72E` `0xA78A` `0xAA5B` `0xAB3E` `0xECD8` |
| `0xFF08` | read and written | `0xA68C` `0xA6D5` `0xD36F` `0xD384` `0xD394` `0xD3A2` `0xECE3` |
| `0xFF0A` | write | `0xA69F` |
| `0xFF0E` | write | `0xA6AE` `0xA72A` |
| `0xFFC4` | write | `0xCE43` `0xD2A3` |
| `0xFFCF` | write | `0xF453` |
| `0xFFD9` | read | `0xB117` `0xB13F` `0xE68F` `0xE6A7` |
| `0xFFDC` | write | `0xCD75` |
| `0xFFDD` | write | `0xCD90` |

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2AAA1 --runtime 0xAAA1 -n 4
0xaaa1  90ff00   mov  dptr,#0xff00
0xaaa4  e0       movx a,@dptr
0xaaa5  ff       mov  r7,a
0xaaa6  900a49   mov  dptr,#0x0a49
```

The `0xFF04`/`0xFF08` pair at `0xA684`/`0xA68C` is §5.2's block structure
continuing above `0xF800` — a `mov DPTR` into each in turn, `0x80` and then `0x00`
written through the first, `0xFF` through the second — and each of the two is
written at two of its sites and read at most of the others. That is why the
direction column can say `read+write` and a single `read`/`write` cell would
have lost half of it.

**This strengthens §5.3's conclusion and retracts its explanation.** The region
is a region; eleven more of its addresses are backable by encoding. What the
gap is made of is not undecoded functions.

## One of the twenty-five is a byte-scan artifact, and the framing column says so

`0xFFA3` is on the issue's list and it has no instruction. Its single site is at
`0xCC53`, and the byte before it starts a call that swallows the seed:

```console
$ xxd -s 0x2CC47 -l 16 ec/firmware/GMxMGxx_11.800
0002cc47: 1290 ffe0 1290 24e0 5401 ff12 90ff a312  ......$.T.......
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2CC47 --runtime 0xCC47 -n 5
0xcc47  1290ff   lcall 0x90ff
0xcc4a  e0       movx a,@dptr
0xcc4b  129024   lcall 0x9024
0xcc4e  e0       movx a,@dptr
0xcc4f  5401     anl  a,#0x01
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2CC52 --runtime 0xCC52 -n 3
0xcc52  1290ff   lcall 0x90ff
0xcc55  a3       inc  dptr
0xcc56  1210c8   lcall 0x10c8
```

`12 90 ff` appears twice in that run, at `0xCC47` and at `0xCC52`, and it is the
same `lcall 0x90FF` both times. The byte scan reads the `90 ff` **inside** each
one as a `mov DPTR` opcode and takes the low byte from whatever instruction
follows the call: `e0` at `0xCC4A`, which is the `movx` of the next real
instruction, giving `0xFFE0`; and `a3` at `0xCC55`, which is the `inc DPTR` of
the next one, giving `0xFFA3`. So both addresses are in the scan's 45 for that
reason, and `0xFFA3` — which has no other site — is not reachable by any method
here.

The probe refuses a site no linear walk lands on: `converges_from()` scores
`0xCC53` **0 of 24**, against 20–24 for every site behind the eleven above, and
the site's verdict becomes `not-found-by-this-method` with the reading the
window would have given kept beside it in an `unframed` field rather than
discarded. **`0xFFE0` is a census address and keeps its verdict**, because it
has six other sites; the rule demotes a site, not an address.

`0xFFFC` and `0xFFFD` are the two `callee-derefs` residue addresses, and the
tally under the table is where the honest reading of them is: `0xFFFD` hands
DPTR to `0x122F` at twenty-three of its twenty-four sites and to a routine that
dereferences it at one, so the single word `callee-derefs` is the strongest
claim and the minority one. `0xFFFC` is fourteen to one the same way.

## The per-address table

Every address either population names. `verdict` is the strongest claim any of
the address's sites supports and `reach` is the one way it is reached, which
is what separates the census's three `inc` continuations from its literal
seeds. `sites` counts those sites, including any counted under the address
one byte above the one they name.

| address | in census | verdict | reach | direction | sites | framing |
|---|---|---|---|---|---|---|
| `0xFF00` | no | `literal-read` | `literal` | read | 3 | 23-24/24 |
| `0xFF02` | no | `literal-write` | `literal` | write | 2 | 22-24/24 |
| `0xFF04` | no | `literal-read` | `literal` | read+write | 11 | 20-24/24 |
| `0xFF08` | no | `literal-read` | `literal` | read+write | 7 | 24/24 |
| `0xFF0A` | no | `literal-write` | `literal` | write | 2 | 24/24 |
| `0xFF0C` | no | `callee-rebases` | `callee-rebases` | none | 1 | 24/24 |
| `0xFF0E` | no | `literal-write` | `literal` | write | 5 | 22-24/24 |
| `0xFF40` | yes | `census` | `literal` | read | 5 | 24/24 |
| `0xFF42` | yes | `census` | `literal` | read+write | 6 | 21-24/24 |
| `0xFF4A` | yes | `census` | `literal` | read | 5 | 23-24/24 |
| `0xFF62` | yes | `census` | `literal` | read | 2 | 24/24 |
| `0xFF80` | yes | `census` | `literal` | read | 5 | listed |
| `0xFF84` | yes | `census` | `literal` | read | 1 | listed |
| `0xFF88` | yes | `census` | `literal` | read | 3 | 24/24 |
| `0xFFA3` | no | `not-found-by-this-method` | `not-found-by-this-method` | none | 1 | 0/24 |
| `0xFFC0` | yes | `census` | `literal` | read | 1 | listed |
| `0xFFC1` | yes | `census` | `inc` | read | 1 | listed |
| `0xFFC2` | yes | `census` | `literal` | read | 2 | listed |
| `0xFFC4` | no | `literal-write` | `literal` | write | 2 | 24/24 |
| `0xFFC6` | yes | `census` | `literal` | read | 4 | 24/24 |
| `0xFFCF` | no | `literal-write` | `literal` | write | 1 | 24/24 |
| `0xFFD0` | yes | `census` | `literal` | write | 3 | listed |
| `0xFFD1` | yes | `census` | `inc` | write | 2 | listed |
| `0xFFD3` | yes | `census` | `literal` | read | 4 | 24/24 |
| `0xFFD4` | yes | `census` | `literal` | read | 10 | 24/24 |
| `0xFFD5` | yes | `census` | `literal` | read | 8 | listed |
| `0xFFD8` | yes | `census` | `literal` | read+write | 4 | 24/24 |
| `0xFFD9` | no | `literal-read` | `literal` | read | 8 | 24/24 |
| `0xFFDA` | yes | `census` | `literal` | write | 5 | listed |
| `0xFFDB` | yes | `census` | `inc` | write | 1 | listed |
| `0xFFDC` | no | `literal-write` | `literal` | write | 1 | 23/24 |
| `0xFFDD` | no | `literal-write` | `literal` | write | 2 | 22/24 |
| `0xFFDE` | no | `callee-non-xdata` | `callee-non-xdata` | none | 2 | 24/24 |
| `0xFFDF` | yes | `census` | `literal` | write | 2 | listed |
| `0xFFE0` | yes | `census` | `literal` | read+write | 7 | listed |
| `0xFFE1` | yes | `census` | `literal` | read | 10 | 24/24 |
| `0xFFE2` | yes | `census` | `literal` | read | 8 | listed |
| `0xFFF4` | no | `callee-non-xdata` | `callee-non-xdata` | none | 1 | 22/24 |
| `0xFFF5` | no | `callee-rebases` | `callee-rebases` | none | 3 | 22/24 |
| `0xFFF6` | no | `callee-rebases` | `callee-rebases` | none | 3 | 22/24 |
| `0xFFF7` | no | `callee-rebases` | `callee-rebases` | none | 2 | 22/24 |
| `0xFFF8` | no | `callee-rebases` | `callee-rebases` | none | 4 | 22-24/24 |
| `0xFFFA` | no | `callee-rebases` | `callee-rebases` | none | 5 | 22-24/24 |
| `0xFFFB` | no | `callee-rebases` | `callee-rebases` | none | 6 | 22-24/24 |
| `0xFFFC` | no | `callee-derefs` | `callee-derefs` | read | 15 | 22/24 |
| `0xFFFD` | no | `callee-derefs` | `callee-derefs` | read | 24 | 22/24 |
| `0xFFFE` | no | `callee-non-xdata` | `callee-non-xdata` | none | 15 | 22-24/24 |
| `0xFFFF` | no | `callee-non-xdata` | `callee-non-xdata` | none | 22 | 22-24/24 |

The 23 census rows are read from `XSPACE_PD_HIGH` and independently re-derived:
`xdata_space()`'s own reach and the probe's agree on all 23, which is what makes
the probe's reading of the other 25 worth reading.

## Why the census is not extended here

The issue offered a fork: extend `XSPACE_PD_HIGH` and the census with what is
found, **or** record the residue with its per-address reason. This takes the
second, and the reason is mechanical rather than cautious.

**`ec/annotations/xdata-clusters.csv` is generated** — `OUT_CLUSTERS` in
`xdata_register_map.py`, held by `--check` — from Ghidra's exported functions.
The census cannot see the eleven without new function *entries* at their sites,
which means annotation seed rows in `ec/annotations/ghidra-functions.csv` plus
`--mode rebuild-project`. `CLAUDE.md` records that two branches that both rebuild
one project cannot merge, and `.gitattributes` makes git refuse rather than
text-merge the database. On a tree with several agent PRs open that is a
collision waiting to happen, not a judgement call about the finding.

So the census is untouched, and the work-list is the eleven addresses with their
seed sites — the table in the encoding section above is exactly the input the
next tranche needs. That is the issue's "extend the census" branch, deferred
with the reason, not skipped.

## What this does not establish

- **Nothing here is a behaviour.** Every figure is a static reading of the
  committed image, the committed listings and the committed census. No EC was
  opened, no register was read back, and none of the eleven has been shown to
  be an address the part acts on — only that the instruction after the seed
  dereferences a pointer holding it. `ec/annotations/registers.yaml` is
  unchanged for the same reason: a `status:` change would need evidence that
  the EC acts on an address, and nothing measured here bears on that.
- **`0xFFxx` is still not shown to be XDATA at all.** This file is about how
  the PD image *uses* the numbers, and `pd-xdata-overlap.md` §6's refusal to
  answer the window's topology stands. The eleven are XDATA *by the same
  encoding argument* `xdata-register-map.md` §5.1 makes for the census's ten, and
  that argument is about what `movx` names, not about what the window is.
- **A `callee-rebases` verdict is a fact about the site, not about the
  address.** `0x0D38` dereferences `DPTR + R1:R2`, and this tool does not
  resolve `R1:R2`, so which byte is touched is not established. The verdict says
  the seed is a base and nothing more.
- **The chase is bounded at two levels and says so.** A callee with no listing
  is decoded from the image for one window's worth of rows, and a routine whose
  entry run ends at a branch or a `ret` comes back `not-found-by-this-method`
  rather than `callee-non-xdata` — the entry run not reaching a dereference is
  not the routine having none. A depth the chase never reached is never
  reported.
- **The decoded path steps over rows `disasm8051` assigns to no instruction.**
  There are 36 such opcodes; `0xF4` (`cpl A`) is one of them and appears in
  `pd/A8AE.asm` at `0xA984`. A window containing one is a window this tool
  cannot fully see, which is a lower bound in the same direction as a listing
  that stops short.
- **A byte-scan site is a byte, not an instruction.** `0xFFA3` is the worked
  case; the framing column is what distinguishes them and 0 of 24 is the score
  that says "do not read this one".
- **A site's direction is its *first* dereference.** The window stops at the
  first `movx`, so a read-modify-write site is recorded as the read — `0xA692`
  loads `0xFF04`, reads it, ORs `0x01` into A and writes it back, and the
  verdict is `literal-read`. The address-level direction is unaffected here
  because `0xFF04` is genuinely written at two other sites, but a site that
  both read and wrote and had no other site would be reported as a read.

## Re-deriving all of it

Every figure above comes out of the tool, from committed inputs, with no
Ghidra, no network and no hardware:

```console
$ python3 ec/tools/pd_high_xdata_probe.py
$ python3 ec/tools/pd_high_xdata_probe.py --notes      # every site's own reason
$ python3 ec/tools/pd_high_xdata_probe.py --self-test
$ python3 ec/tools/xdata_register_map.py --self-test    # the 23 still pin
$ python3 ec/tools/xdata_register_map.py --check        # the CSVs are byte-identical
$ python3 ec/tools/disasm8051.py --self-test            # the decoder's own oracle
```

The suite at `ec/tools/test_pd_high_xdata_probe.py` holds the claim rather than
a count of the tree: the residue is the issue's list transcribed from the
issue, the eleven are exactly eleven and each carries a direction read off the
`movx` operand, every address carries a word from the declared vocabulary, the
probe's reach agrees with `xdata_space()` on all 23, and each boundary of the
window rule is made to fire on hand-built rows — including the one that costs
all three of the census's `inc` continuations if it is got wrong, which is that
a `movx` which does *not* dereference the address under test does not end the
window. `pd/F2FB.asm` is the case: it writes `0xFFDA`, walks DPTR up one and
writes `0xFFDB`, so the continuation is found *behind* a `movx` for a
different address.
