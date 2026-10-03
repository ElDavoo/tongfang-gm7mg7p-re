# All six residual `addc A,#imm ; mov DPH,A` sites close: four build page `0x0D`/`0x0E`, two build page `0x2A` and read CODE (issue #519)

(2026-10-03, issue #519. Static reading of the committed firmware, the
committed decompiled listings and the committed annotations. No capture was
opened, no register was read back, no EC, hardware or Windows machine was
involved, and no `status:` moved.)

`ec/annotations/xdata-1c3x-consumers.md` §6.2 scans the EC window for
`34 xx f5 83`, finds 64 `addc A,#imm ; mov DPH,A` sites, and reports that 58
are immediately preceded by `clr A` and so "take the high byte as the
immediate exactly". **That reason is wrong and §2 corrects it** — `clr a`
clears the accumulator and leaves the carry, so those sites build the
immediate *or* the next page up, exactly like the other six. What the
immediates settle is not one answer but two, because a `{imm, imm+1}` set
holds a page `P` when the immediate is `P` **or** `P-1`: page `0x1C` is
unreachable, neither `0x1C` nor `0x1B` being among them, while page `0x08`
**is** reached — by exactly one `clr a` site, `0x8360`, immediate `0x08`,
set `{0x08, 0x09}`. That site is the bank0 `0x8365` store §6.2 is built
around rather than a second writer of the page. The other six are not
preceded by `clr A`, so their `DPH` is whatever `A` already held plus the
immediate plus the carry, and §6.2 leaves them open: "a store through one
of the six reaching either `0x0862`/`0x086D` or any `0x1Cxx` byte is **not
excluded**."

**All six close, and none of them can reach either page by this
construction.** Four build page `0x0D` or `0x0E`; two build page `0x2A`, and
their computed pointer is consumed by a `movc` — a CODE read — with the `movx`
after it aimed at a hard literal. §2 and §3 are the arithmetic. This is a
negative scoped to the construction, exactly as §6.2's other rows are: it is
not "no writer exists", and §7 says what is left.

## 1. How to re-derive all of it

```console
$ python3 ec/tools/addc_dph_sites.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/addc_dph_sites.py ec/firmware/GMxMGxx_11.800 --csv \
        > ec/annotations/xdata-addc-dph-residual-sites.csv
$ python3 ec/tools/addc_dph_sites.py ec/firmware/GMxMGxx_11.800 --check
$ python3 -m unittest discover -s ec/tools -p "test_addc_dph_sites.py"
$ python3 ec/tools/disasm8051.py --self-test
```

`--check` diffs the committed table byte for byte against a fresh generation
and needs no Ghidra, no network and no hardware. The census reproduces §6.2's
exactly: 64 sites, 58 preceded by `clr A`, the six at `0x2266`, `0x2270`,
`0x2278`, `0x22DF`, `0x28EF` and `0x2912`. The tool also prints the `clr a`
population's immediates and reads both pages off them, which is what the
`0x1C` negative for that half rests on and what shows page `0x08` reached by
`0x8360` alone (§2).

**The tool is deliberately mechanical, and the semantic argument is not in
it.** `addc_dph_sites.py` reports each site's predecessor — a call target to
chase, or a register to read — and stops. Deciding what a call target
*returns* is a claim about an export boundary, and the boundary is a
hypothesis (`bank-call-audit.md` §1 calls the call-target census an upper
bound). So the closure below is argued against the raw bytes with
`disasm8051.py` as the oracle, which is where a semantic claim about an export
belongs and not in a census a reader re-runs.

## 2. The four `xx`=`0x0D` sites: `DPH` is `0x0D` or `0x0E`

Each of the four is preceded by a three-byte `lcall`, and **three distinct
callees** are involved:

| site | callee | the callee's own `add` | carry out iff | `DPH` |
|---|---|---|---|---|
| `0x2266` | `FUN_CODE_2a7b` | `0x90 + [0x67]` | `[0x67] >= 0x70` | `0x0D` / `0x0E` |
| `0x2270` | `FUN_CODE_2a7b` | `0x90 + [0x67]` | `[0x67] >= 0x70` | `0x0D` / `0x0E` |
| `0x2278` | `FUN_CODE_2a8f` | `0x80 + [0x67]` | `[0x67] >= 0x80` | `0x0D` / `0x0E` |
| `0x22DF` | `FUN_CODE_2a7d` | caller's `A` + `[0x67]` | not established — the caller's `A` is | `0x0D` / `0x0E` |

The `0x22DF` row is the `0x2A7B` / `0x2A7D` overlap of §4 seen from the other
side: entered at `0x2A7D`, the `mov a,#0x90` at `0x2A7B` **does not execute**,
so the `add` there is the caller's own `A` plus `[0x67]`, not `0x80 + [0x67]`.
The page set is `{0x0D, 0x0E}` either way, so the conclusion does not turn on
it; the row records the add that actually runs.

The three routines, read from the image rather than from the truncated
listings:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2A7B -n 6
0x02a7b  7490     mov  a,#0x90
0x02a7d  af67     mov  r7,0x67
0x02a7f  2f       add  a,r7
0x02a80  f582     mov  0x82,a
0x02a82  e4       clr  a
0x02a83  22       ret
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2A8F -n 7
0x02a8f  ff       mov  r7,a
0x02a90  7480     mov  a,#0x80
0x02a92  ae67     mov  r6,0x67
0x02a94  2e       add  a,r6
0x02a95  f582     mov  0x82,a
0x02a97  e4       clr  a
0x02a98  22       ret
```

All three end `clr a ; ret`, and **`clr a` clears the accumulator and not the
carry** — an 8051's `clr a` is `mov A,#0` and touches no flag. This
repository states that twice already, in
`docs/findings/pd-index-low8-propagation.md` ("`clr a` does not touch the
carry flag on an 8051 and neither does `mov a,#hi`") and in
`docs/findings.md` §96 ("`clr a` leaves the carry out of `add a,#0x9B` live
into `addc a,#0x08`").

So `A` is `0` on entry to every one of the four `addc`s, whatever the
caller's `A` was, **and** the carry the `addc` adds is the one the callee's
own `add` left behind — precisely *because* the `clr a` does not clear it.
That carry this method does not establish, because `[0x67]` is a run-time
byte (and at `0x22DF` the caller's own `A` is unestablished besides). Hence a
**two-element page set**, `{0x0D, 0x0E}`, and never a single value. Neither
member is `0x08` and neither is `0x1C`.

The set is two elements for that reason alone. Had `clr a` cleared `CY` — as
`docs/findings/pd-index-low8-propagation.md` is careful to say it does not —
the set would have been the single value `{0x0D}`, and §6.2's "the immediate
exactly" would have been right for the wrong reason. It is not right, so both
pages have to be read off the two-element set instead — and a set of that
shape holds page `P` when the immediate is `P` **or** `P-1`, which is what
makes the page-`0x1C` negative hold for the whole `clr a` population while the
page-`0x08` half resolves to `0x8360` alone rather than to nothing (§1).

**Only one of the four writes.** `0x2266` is followed by
`mov A,0x66 ; movx @DPTR,A`, the one store through a computed pointer among
the six. Its `DPL` is not an immediate in the caller — `FUN_CODE_2a7b` sets
`DPL = (0x90 + [0x67]) & 0xFF` — so the destination set is
`{0x0D, 0x0E} << 8 | ((0x90 + [0x67]) & 0xFF)`. `[0x67]` is unconstrained,
which does not matter: the *page* is what decides `0x0862`/`0x086D` versus a
`0x1Cxx` byte, and the page is bounded either way. The other three are reads
(`movx A,@DPTR` at `0x2274`, `0x227C` and `0x22E3`).

## 3. The two `xx`=`0x2A` sites: `DPH` is `0x2A`, and the pointer reads CODE

Both are in `FUN_CODE_28d1` (`ec/decompiled/common/28D1.asm`), and both read
`A` from `R6`, which the same routine loads with `#0x00` a few instructions
earlier and does not write again before `mov A,R6`:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x28E2 -n 10
0x028e2  7e00     mov  r6,#0x00
0x028e4  900a4d   mov  dptr,#0x0a4d
0x028e7  e0       movx a,@dptr
0x028e8  541f     anl  a,#0x1f
0x028ea  2400     add  a,#0x00
0x028ec  f582     mov  0x82,a
0x028ee  ee       mov  a,r6
0x028ef  342a     addc a,#0x2a
0x028f1  f583     mov  0x83,a
0x028f3  e4       clr  a
```

**The carry is `0` here, provably, so `DPH` is `0x2A` exactly rather than a
set.** The last instruction before the `addc` to touch `CY` is the `add`:
`anl a,#0x1f` bounds `A` to `0x00`-`0x1F`, and adding `0x00` to that cannot
carry out, so `CY` is `0`; `mov 0x82,a` and `mov a,r6` change no flag. At
`0x2912` the same shape holds with `anl a,#0x03` bounding `A` to `0x00`-`0x03`
and `add a,#0x20` unable to carry out of it. So both pages are the single
value `0x2A`, which is neither `0x08` nor `0x1C`.

This is the one place in the write-up where a single page is established, and
it is established from the *`add`*, not from a `clr a`: the argument is that
the instruction that set `CY` provably set it to `0`. That is a different
route to a single value from §2's, and it does not need the premise §2's
original wording rested on.

These two also close on a second, page-independent ground, which is the more
useful half because it does not depend on the arithmetic at all:

```asm
28EE     ee         mov  a,r6
28EF     34 2a      addc a,#0x2a
28F1     f5 83      mov  dph,a
28F3     e4         clr  a
28F4     93         movc a,@a+dptr     ; <- CODE read, not XDATA
28F5     90 00 23   mov  dptr,#0x0023  ; <- pointer replaced by a literal
28F8     f0         movx @dptr,a       ;    the store goes to 0x0023
```

The computed DPTR is consumed by a `movc`, and the `movx` is aimed at a hard
literal `0x0023` (at `0x28F5`) or `0x0024` (at `0x2918`). So whatever `DPH`
held, **neither site can be an XDATA writer through the computed pointer.**
`0x93` is confirmed by `disasm8051.mnemonic()` at both `0x28F4` and
`0x2917`, which is the repo's own oracle rather than this document's reading
of a listing.

## 4. Three corrections to the document this closes

**The callee attribution was wrong in detail.** §6.2 said "four carrying
`xx`=`0x0D` after a `lcall 0x2A7B`". There are **three** callees: `0x2278`
follows `lcall 0x2A8F` and `0x22DF` follows `lcall 0x2A7D`; only `0x2266` and
`0x2270` follow `0x2A7B`. The conclusion is unchanged — all three return
`A=0` — but the sentence as written would leave a reader checking one routine
and assuming it covered the other three.

**`0x28EF` was over-claimed.** §6.2 said "`0x2266` and `0x28EF` are confirmed
real instructions against the raw image (`mov a,0x66 / movx @dptr,a` at
`0x226A`-`0x226C` stores through the computed pointer)". That parenthetical
describes `0x2266` only. At `0x28EF` there is no `mov a,0x66` and no `movx`
through the computed pointer at all — the `movc` of §3 is what is there. Both
readings close the site, but the sentence asserts a store at a site that has
none, which is the overclaim `CLAUDE.md`'s calibration rule is about.

**Checked and not present: a `0x227D` misdecode.** `0x227D` is `6f`, which is
`xrl A,R7` and not `mov R7,A`. The only committed listing carrying that address
is `ec/decompiled/common/2275.asm`, and it decodes it as `xrl A, R7`;
`disasm8051.mnemonic()` agrees, and `verify_reassembly.py --check` compares
every listing byte against the firmware and reports no disagreement.
`ec/decompiled/common/223F.asm` ends at `0x2274` and resumes at `0x22B5`, so it
does not decode that address at all and has nothing to be wrong about. Recorded
because it was worth ruling out rather than assuming.

**`0x2A7B` and `0x2A7D` are one byte range under two exported names**, which
is a hazard for anyone who reads a single listing. `0x22DC` calls `0x2A7D`
directly while `0x2263`/`0x226D` call `0x2A7B`, so the call-target census
found a boundary at `0x2A7D` inside a routine that starts at `0x2A7B`. Each
`.asm` stops at its own entry: `ec/decompiled/common/2A7B.asm` is **one
instruction long**, `mov A, #0x90`, which is a reading with the wrong return
value and no `ret` in it. The closure here does not depend on resolving the
overlap, and it is worth saying why the negative is safe to state even from the
truncated reading: taking `2A7B.asm` alone at face value would give `DPH` in
`{0x9D, 0x9E}`, which also misses `0x08` and `0x1C`. Merging the two exports
is a `--mode rebuild-project` change and is left alone (§7).

## 5. The `#110` pointers, all of them, and which reading each gets

`#519` asks that every `#110 ... stays open` reference in the tree either name
an open issue or be corrected in place. The sweep is one command, and this
section is its reading of the tree **as it stood before this change** — every
one of that sweep's hits is accounted for below, because a correction pass
that corrected the lot would have destroyed the ones that are correct:

```console
$ git grep -n "#110\b" origin/main -- '*.md' '*.csv' '*.yaml' '*.py' \
      | grep -vE '#110[0-9]'
```

Run against the working tree instead of `origin/main` the same grep also
returns this document and the correction blocks below, which quote `#110` in
order to correct it; those are the corrections, not further claims, and they
are the only difference between the two runs.

They are **not** all the same claim:

- **Corrected in place** — the ones that assert `#110` is open, or hand it the
  work: `xdata-1c3x-consumers.md` §6.2's residual paragraph, §7's last row and
  §9's follow-up 1 (three places); `xdata-086x-dispatch.md` §6's "Answered"
  block and §9's follow-up 1 and its closing list (three places);
  `registers.yaml`'s `XDATA_1C36` note; `ghidra-functions.csv`'s `bank1,9CE8`
  row; `xdata-0440-readers.md` §7.2's "This is the method issue #110 is adding
  to `trace_xdata_refs.py`".
- **Left standing** — provenance, not state. These cite the blind spot rather
  than assert an owner: `registers.yaml`'s `XDATA_07C7`, `XDATA_07C8`,
  `XDATA_1665`, `XDATA_1666`, `GPU_DYNAMIC_BOOST_STATUS`, `GFID`, `CPUA` and
  `DBAP` (each of the form "invisible to both scans" or "a lower bound");
  `ec-07d6-07d7-sites.md` §5 and §8; `ec-07c4-07d5-sites.md` §9;
  `static-refs-audit.md` §8; `xdata_register_map.py`'s `0x07C7` and `0x07C8`
  cells; `docs/findings/07d6-07d7-pd-image-census.md` §"The four grades";
  `docs/findings/common-07f0-0f75-158e-1594-tranche.md` §`0x07F0`;
  `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`'s `0x07C7`/`0x07C8` rows;
  `computed-dptr-sites.md`'s title, which names the issue that document
  answers; `test_computed_dptr_sites.py`'s two comments.
- **Not correctable here** — `docs/findings.md` carries the pointer twice, and
  `check_findings_frozen.py` fails any edit to that file. One is the §"the gap
  is issue **#110**" line; the other is §4c's "`#110` owns the blind spot that
  would have to close first", which asserts the same owner for the same
  remaining work rather than citing the blind spot. The correction is recorded
  here instead; thawing a frozen file is a human's call.

**What the correction says, and how far it goes.** This implement stage could
not run `gh issue view 110`, so the correction is phrased against what is
checkable from the tree: **no open issue in this repository covers general
computed-DPTR visibility in `trace_xdata_refs.py`**, and the bounded
single-address version of that method *is* committed — `computed_dptr_sites.py`
and `computed-dptr-sites.md` — as a **sibling tool rather than a mode of
`trace_xdata_refs.py`**, for the compatibility reason that tool's own docstring
gives. That is a statement about the tree, not an assertion about the state of
the queue, and it is the form the corrections use. What remains unowned is
stated as unowned.

**Two further facts about the issue's own list, both checked.** Only the
`bank1,9CE8` row of the two named CSV rows carries the "stays open" text;
`bank1,9D53` does not mention `#110` at all, so one row is edited and not two.
And the tree has moved since the issue was filed — `computed_dptr_sites.py`
and its write-up now exist, which is why the pointers say "stays open" about
work that has since been partly done.

## 6. Distinct from #399, and complementary to it

#399 asks for a `dptr-carried` category: a `movx` that lives in the **caller**,
past the `lcall`, whose `DPL` the callee built. `0x226A`-`0x226C` is exactly
that shape — the store is in the caller, and `FUN_CODE_2a7b` built its `DPL`.
These six are the other direction: the pointer is built in place and used in
the same listing. Neither subsumes the other, the category is **not** in the
committed tool today, and adding it here would duplicate #399. `dptr-seed-census-gap.md`
§6 already draws the same three-way distinction and is the fuller statement.

## 7. What this does not establish

- **Not "no writer exists."** Every negative here is scoped to the
  `addc`-into-`DPH` construction, at these six sites. `mov DPTR,#imm16`,
  `movx @Ri` with `P2` paging, and a `DPTR` handed in through a subroutine are
  three other spellings this pattern cannot see, and
  `computed_dptr_sites.py`'s docstring is the list.
- **The page-`0x08` conditional store at bank0 `0x8365` stands**, and its
  `XDATA[0x0A56]` gate is still unobserved. It is a `clr a` site — `0x8360`,
  immediate `0x08`, set `{0x08, 0x09}` — which is the other half of why the
  split in this document matters: it is the **only** `clr a` site whose set
  holds `0x08`, so the six that were open are not where page `0x08` is written,
  and nothing here is a second writer of that page. Its `DPH` is `0x08` or
  `0x09`, not the `0x08` alone that §6.2's reading of it assumes — which is a
  question about *that* table, not about these six, and §8 records it.
- **A live read of `XDATA[0x0A56]`** is still the only thing that settles
  whether that store ever fires. No hardware is reachable from a GitHub-hosted
  runner; the step is already written down in §9's follow-up item 3 of the page
  document and this change does not re-prepare it.
- **The six `0xD173`-`0xD24E` case handlers and the three unexported bank-1
  routines** of the `0x1C01`-`0x1C03` sites remain unseeded, as
  `xdata-1c3x-consumers.md` §9 records. Seeding them is a
  `--mode rebuild-project` change.
- **Merging the `0x2A7B` / `0x2A7D` exports** (§4) is left alone: a
  `--mode rebuild-project` change, two branches that both rebuild the project
  cannot merge, and the negative does not need it.
- **A pre-existing mangled sentence in `xdata-086x-dispatch.md` §9**, where a
  "`That is a gap in `.asm` listings; and a **conditional computed-DPTR writer
  found for…`" clause runs two bullets together. It predates this change, no
  gate catches it, and fixing it would put an unrelated hunk in a file several
  branches are editing. Named here, left alone.

## 8. What this opens

- **The general tool-side category is unowned.** Neither
  `trace_xdata_refs.py`'s `dptr-carried` (that is #399's) nor a
  `trace_xdata_refs.py` mode for this construction is in the committed tool.
  The bounded sibling exists; the general one does not, and this document is
  the record of why that is a gap rather than an oversight.
- **`0x2A7B`/`0x2A7D` as one routine under two names** (§4) is a live hazard
  for anyone reading a single export, and it is the kind of thing a
  `build_ec_decompile.py` check could catch rather than a reader.
- **The page-`0x08` conditional store's own arithmetic needs a second look, and
  this change does not give it one.** §2's correction — `clr a` clears the
  accumulator and leaves `CY` alone — reaches further than the sentence it
  corrects. `xdata-1c3x-consumers.md` §6.2 reads `FUN_CODE_8294` at bank0
  `0x8360` as `clr a ; addc a,#0x08 ; mov DPH,A` with "`DPH` is hard `0x08`",
  and tabulates `0x0862` as reached when `XDATA[0x0A56]` is `0x49` or `0xC9`
  and `0x086D` when it is `0x4E` or `0xCE`. Under the corrected reading the
  carry into that `addc` is the carry out of `add a,#0xd0` at `0x835B`, and
  every one of those four values carries:

  ```console
  $ python3 - <<'EOF'
  for a in (0x49, 0xC9, 0x4E, 0xCE):
      v = 2*a + 0xD0
      print(f"0x{a:02X} -> DPL=0x{v & 0xFF:02X} DPH=0x{0x08 + (v >= 256):02X}")
  EOF
  0x49 -> DPL=0x62 DPH=0x09
  0xC9 -> DPL=0x62 DPH=0x09
  0x4e -> DPL=0x6C DPH=0x09
  0xce -> DPL=0x6C DPH=0x09
  ```

  So those `DPL`s land on **page `0x09`**, and page `0x08` is reached only for
  `XDATA[0x0A56] < 0x18`, whose `DPL`s run `0xD0`-`0xFE` and never include
  `0x62` or `0x6C`. **§6.2's table of gate values for `0x0862` and `0x086D`
  therefore does not follow from the bytes, and neither does its "reached
  when" column.** That is a question about a table this pass did not build and
  does not correct: the page-`0x08` store, its `XDATA[0x0A56]` gate and the
  `present-untested` rows all stand exactly where they were, and nothing in
  §2 depends on them. What this pass does assert is the narrower and negative
  claim it can support — no site in the **residual**, the six of §2 and §3,
  reaches page `0x08` or page `0x1C` by this construction, and the `clr a`
  half reaches `0x08` only through the one already-known `0x8360`. Filing
  the table's own arithmetic as its own issue is a human's call; it needs the
  `0x08xx` page re-derived, not a line edited here.
