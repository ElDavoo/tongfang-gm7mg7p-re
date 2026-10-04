# The two committed XDATA methods were blind at the same two bytes, and `agree` was the wrong word for it

Issue #799. `ec/annotations/xdata-086x-dispatch.md` closed its own follow-up
list with "**the decompiler-lost `MOV DPTR` at `0x0D31C`** ... which is a wider
question than this one site ... worth its own issue", and this is that issue.

The short answer to the question it asked — one site or the page? — is
**neither, and the third answer is the one that was missing.** It is not one
site, and it is not the page: it is *every byte on the page whose DPTR is
loaded by a callee*, and which bytes those are depends on which helpers on the
page return with a pointer set. `0x0860` has one such helper (`0xD319`) and two
such sites; `0x0867` and `0x0868` have helpers of their own and three each,
and `0x086C` one through a third. The shape is a property of the page; the
*number* of bytes it costs is not.

What made it worth a machine rather than a paragraph is that both committed
methods missed the same bytes, in opposite ways, and
`ec/tools/check_site_census.py` — the tool built to hold the two methods to
each other site by site — was reporting that shared blindness at the `0x0D31C`
cell as **`agree`**. Two methods agreeing is evidence. Two methods looking in
the same direction and both finding nothing is not, and the difference is the
whole content of this issue.

## The bytes

`ec/decompiled/bank0/D319.asm` is four instructions:

```
D319     e0 - -   movx     A, @DPTR
D31A     54 7c -  anl      A, #0x7c
D31C     90 08 60 mov      DPTR, #0x0860
D31F     22 - -   ret
```

so `0xD319` returns with **DPTR = `0x0860` by construction**, and both committed
callers use exactly that:

```
ec/decompiled/bank0/D091.asm:139-142
D18C     12 d3 19 lcall    0xd319
D18F     70 04 -  jnz      0xd195
D191     f0 - -   movx     @DPTR, A
D192     02 d2 8e ljmp     0xd28e

ec/decompiled/bank0/D236.asm:13-16
D244     12 d3 19 lcall    0xd319
D247     70 03 -  jnz      0xd24c
D249     f0 - -   movx     @DPTR, A
D24A     80 42 -  sjmp     0xd28e
```

The `jnz` makes each fall-through path exactly "A == 0 and DPTR == `0x0860`",
so **`0x0D191` and `0x0D249` are each a conditional store of `0x00` to XDATA
`0x0860`**, and both fall into `copy_0866_86b_to_1c04_1c3a` at `0xD28E`.

## Why neither method saw it

The opcode sweep finds a site by a literal `MOV DPTR,#imm16` **in the same
function**, and the load is three bytes earlier and inside a callee, so
`xdata-086x-dispatch-sites.csv` had no row for either. The census reads the
decompiled C, and Ghidra bound DPTR to its **pre-call** value:
the decompiled `dispatch_on_0860` sets `pcVar4 = (code *)0x864;` and then
stores `*pcVar4 = (code)0x0;`, while the decompiled
`poll_d6c2_then_branch` binds `puVar2 = &DAT_EXTMEM_1c35` and stores through
it. `occurrence_re` matches neither — a bare `0x864` is not a `DAT_EXTMEM_`
token — and `ec/decompiled/bank0/D091.asm`'s own header says the `.c` is "a
reading of it".

**The two failures are different, and only one of them is catchable by
counting.** At `0x0D191` the decompile charges the store to a *wrong address*
(`0x0864`); at `0x0D249` it charges it to *no address at all*, through a
pointer it bound to `0x1C35`. A count cannot see either — both are a zero in the census — which is why the
per-site correspondence, not the totals, is where this lands.

## The resolver, and the answer to "one site or the page"

`ec/tools/callee_dptr_sites.py` reads only the committed
`ec/decompiled/**/*.asm` listings and, for every `movx @DPTR` on
`0x0860`-`0x086E`, walks back through that listing's rows until something
writes DPTR. Every outcome is a named token — `literal`, `callee`,
`predecessor`, `unresolved` — and `unresolved` carries the reason rather than a
guess. The whole population, from `python3 ec/tools/callee_dptr_sites.py`:

```
0x0860-0x086E: 119 movx resolved onto the page in the committed listings
-- callee 9 literal 109 predecessor 1 unresolved 1 -- plus 1 committed
call site(s) of a chased helper in bytes no listing covers; elsewhere in
the tree 814 movx resolved to no address by this method and a further
6945 resolved to an address off the page. Helpers chased: 0xBC7E,
0xBD34, 0xBD3D, 0xD281, 0xD319
```

Nine callee-set `movx` on the page, and **not one of the sites the sweep
already had is one of them**. Two land on `0x0860`; the rest land on `0x0867`,
`0x0868` and `0x086C`, through three *different* helpers (`0xBD34`, `0xBD3D`,
`0xBC7E`) whose own runs end on `mov DPTR,#0x0867`, `#0x0868` and `#0x086C`.
That is the answer to the issue's third item: **the blind spot is a shape the
page repeats, and it reaches `0x0860` because `0xD319` is on the page.**

`predecessor` is a second shape the sweep's rule also cannot see and this
resolver can: a listing that begins where the listing holding the `MOV DPTR`
ends **and falls into it**. `set_0860_ff_then_d284` at `0xD281` is three bytes
long — a bare `mov DPTR,#0x860` with nothing after it — and
`write_ff_to_dptr_then_d28e` at `0xD284` starts where it stops, so the store of
`0xFF` sits in the second listing with DPTR loaded in the first. That is why
§4's `0xD281` row is a site whose store is three bytes away from its `movx` —
a third failure of the same kind, and one only `0x0860` shows.

**The fall-through is load-bearing, and abutting alone is not enough.** The
exporter splits one routine into consecutive listings, so a listing often
begins exactly where the one above it stops, and whether the first one *falls
into* the second is a separate question the extent cannot answer. Two committed
candidates are not fall-ins. `sub_dptr_byte_from_0867` at `0xBD34` ends
`ret`, and `0xBD3D` is reached only by `lcall 0xbd3d` whose callers each load
DPTR themselves (`0x86b`, `0x86c`, `0x86e` at `9D9B`) — the `0x0867` the
listing above holds is the constant its own `subb` uses. `0x58AB` ends
`ljmp 0x10e8`, a tail jump out, and `pd-index-accesses.csv` already books that
site's DPTR as handed in by its callers at `0x07D7` and `0x0852`. Neither is a
predecessor; both are `unresolved`, and the `predecessor` shape has one
committed site rather than three.

**The `unresolved` row and the off-page count beside it are the point of
printing them.** A row whose address could not be established cannot be said to
be on the page or off it, so the emitted set is not a census, and the tool says
how much of the tree it could not place rather than letting a smaller number
stand in for a complete one. What it could not place is the **814**; the count
resolved to an address *off* the page is reported beside it rather than folded
in, because a `movx` the walk resolved and then found to be elsewhere is the
method working, not the method failing, and summing the two would overstate the
failure several times over.

## Two numbers for `0x0860`, and why the census count does not move

The C-level census's `write: 2` is a **correct count of the decompiled text**
and it is deliberately not shifted to the firmware's four. The reasons are
mechanical as well as editorial:

- `xdata-registers.csv` is generated by `xdata_register_map.py` from the
  decompiled C. Moving its `write` cell means teaching that census to read
  `.asm`, which re-freezes every address's numbers across the tree and the
  generated row of every one of them — its own issue, not this one.
- `ec/decompiled/` has not changed on this branch. `strip_comments()` removes
  the annotation header before `occurrence_re` matches, so the census finds the
  same 17 occurrences before and after the annotation-comment corrections this
  issue makes. `python3 ec/tools/xdata_register_map.py --self-test` still
  prints `all assertions passed` and `--check` still reproduces
  `xdata-registers.csv` byte for byte; that greenness is the evidence the
  counts are unmoved, the same argument #752 made.

So the two numbers are both true and they answer different questions:

| quantity | value | counted over | by |
|---|---:|---|---|
| `xdata-registers.csv` `write` for `0x0860` | 2 | occurrences of the address in the decompiled C | `xdata_register_map.py` |
| `movx @DPTR,A` resolving to `0x0860` with DPTR from a literal in the same listing | 1 | the committed `.asm` listings | `callee_dptr_sites.py` |
| … from a **predecessor** listing | 1 | same | same |
| … from a **callee** | 2 | same | same |
| `movx A,@DPTR` resolving to `0x0860` | 14 | same | same |

**Four stores of `0x0860` in the committed listings, and a fifth at an address
no listing covers.** `XDATA_0860` stays `present-untested`: a store in a
listing is a store in the firmware, and whether the EC *acts* on the value is
`docs/hardware-tests/level-block-0860-086e.md`'s question, still unrun and not
claimed here.

## `0x0D1E3`: a fifth store in bytes no committed listing covers

`ec/annotations/bank-call-targets.csv` books **three** `lcall 0xD319` rows
(`0x0D18C`, `0x0D1E3`, `0x0D244`), the two committed listings decode two, and
`ec/annotations/call-graph-callees.csv` books inbound **2**. That discrepancy
is not an inconsistency to be smoothed over: `call_graph.py`'s `scan()` walks
`ec/decompiled/*/*.asm` and resolves transfers out of the listings, so it
cannot see a site in bytes no export reaches. `bank-call-targets.csv` is a
byte scan of the image and does. The two numbers measure different populations,
and regenerating `call-graph-callees.csv` would not change the second one.

The third site decodes as the same shape as its two siblings. Read by hand:

```
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 \
      --at 0x0D1E3 --runtime 0xD1E3 -n 8 --converge
0xd1e3  12d319   lcall 0xd319
0xd1e6  7004     jnz  0xd1ec
0xd1e8  f0       movx @dptr,a
0xd1e9  02d28e   ljmp 0xd28e
0xd1ec  02d284   ljmp 0xd284
0xd1ef  e4       clr  a
0xd1f0  901c15   mov  dptr,#0x1c15
0xd1f3  f0       movx @dptr,a
0x0D1E3: 24 of 24 preceding anchors decode onto it, 0 step over it
```

and confirmed against `r2 -a 8051` over the image
`make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 bank0.bin` builds:

```
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xd1e3; pd 8' bank0.bin
        0x0000d1e3      12d319         lcall 0xd319
    ┌─< 0x0000d1e6      7004           jnz 0xd1ec
    │   0x0000d1e8      f0             movx @dptr, a
    ┌──< 0x0000d1e9      02d28e         ljmp 0xd28e
    ┌─└─> 0x0000d1ec      02d284         ljmp 0xd284
```

**This is a reading of bytes no committed listing covers, and it is labelled
one.** `disasm8051.py`'s own docstring is the caveat and it is quoted here
rather than paraphrased: it "cannot tell you that the byte you pointed it at is
the start of an instruction — if you anchor it mid-instruction it will happily
decode the garbage that follows. Alignment is therefore always anchor-relative:
`--converge` measures how many nearby anchors a linear walk syncs onto a given
offset from, **which is evidence about framing, not proof of it.**" The 24-of-24
line is that evidence; `r2` is the confirmation, and the two agree. It is still
evidence, not a listing.

So `0x0D1E3` appears in `ec/annotations/xdata-0860-callee-dptr-sites.csv` as
one row with **empty `listing` and `movx` cells** and `dptr_source` `unresolved`
— a committed call site of a chased helper that no listing covers, and nothing
more. It is **not** promoted to a fifth sweep site and moves no count. The
reason is mechanical: `ghidra-functions.csv` rejects an annotation whose address
has no function, and the only cure is `--mode rebuild-project`, which two
branches that both rebuild cannot merge (`.gitattributes` makes git refuse
rather than text-merge the database). Seeding the six case handlers at
`0xD173`/`0xD198`/`0xD1C0`/`0xD1EF`/`0xD221`/`0xD24E` has the same obstacle and
stays a follow-up, as `xdata-086x-dispatch.md` §9 already says.

## What changed in the committed data

| file | what |
|---|---|
| `ec/tools/callee_dptr_sites.py` | new: the resolver. `--csv`, `--check`, `--self-test` |
| `ec/tools/test_callee_dptr_sites.py` | new: its suite |
| `ec/annotations/xdata-0860-callee-dptr-sites.csv` | new: its per-site table, `--check`-reproducible |
| `ec/tools/trace_xdata_refs.py` | `--callee-column`, reading that table; `DPTR from` access spelling |
| `ec/tools/test_trace_xdata_refs_callee_column.py` | new: the flag's population contract |
| `ec/tools/check_site_census.py` | `dptr-from-callee` state and its own outcome |
| `ec/annotations/xdata-0860-census-sites.csv` | two `dptr-from-callee` rows |
| `ec/annotations/xdata-086x-dispatch-sites.csv` | regenerated under `--callee-column`: the two `0x0860` stores and the callee-set sites of the other page addresses §1 sweeps, nothing removed, same columns |
| `ec/annotations/ghidra-functions.csv` | `0xD091`, `0xD236`, `0xD319` comments corrected in place |
| `ec/annotations/registers.yaml` | `XDATA_0860`'s dated correction; **no value moves** |
| `ec/annotations/xdata-086x-dispatch.md` | §1, §3, §4, §8, §9, §11 corrected in place |

`python3 ec/tools/check_site_census.py`, over the widened set:

```
0x0860: 7 of 11 site(s) agree across both methods, 0 blind to the decompile,
0 behind a branch the sweep's window stopped at, 2 found only through a
callee's DPTR and counted in no bucket, 2 unchecked (other program),
17 occurrence(s) accounted for once each -- read 14 write 2 read+write 0
passed-to-call 1 address-taken 0, refs 17
```

**The agreed count does not move.** On `origin/main` the same command prints
`0x0860: 7 of 9 site(s) agree`; here it prints `7 of 11`. Seven is seven on both
trees — what rises is the site count and the reported (callee-set) count, by
the two `0x0860` stores, and the denominator rises with them because they are
in no bucket. The six callee-set sites the other page addresses gained are
counted in *their own* address's line, not this one. The bucket totals and
`refs 17` do not move either. That is the shape of the fix: **the two sites are
now named, and neither method is credited with having seen them.** `agree` was
the wrong word for them before this change and is still the right word for the
seven that were always there.

## What this does not establish

- **That the EC does anything with a value written by any of these stores.** A
  store in a listing is a store in the firmware. `XDATA_0860` is
  `present-untested` and stays so.
- **That the other fourteen addresses of the page are free of this shape.**
  The resolver covers the whole `0x0860`-`0x086E` page and this write-up
  records what it establishes *for `0x0860`*; the census correspondence for the
  others stays `not recorded` — "not done by this method", never an absence.
- **That a `movx` the resolver could not resolve is off the page.** The
  unresolved count is printed for that reason, kept apart from the count
  resolved off the page, and an `unresolved` row in the table is a named token
  with the method named beside it.
- **Anything about the six case handlers.** They have no function entry and no
  listing, so the bytes `0x0D173`-`0x0D24E` were not read by any method here.
  `0x0D1E3` is the one address in that range this issue touched, and only
  because the committed call-site table already named it.

## Follow-ups this opens

1. **The tree-wide version.** `callee_dptr_sites.py` reads the committed
   listings, so it answers for what they cover and reports what they do not
   rather than decoding around it. A version that walks the image would need
   function boundaries the image does not carry.
2. **The census still reads the C.** A `dptr-from-callee` class now exists in
   one table for one address; the same join for the other fourteen page
   addresses, and the tree-wide version of it, are separate work.
3. **`0xBD3D`'s entry `movx`** reads `0x0867` from the caller's own DPTR, which
   each of its three callers loads before the `lcall`, and the sweep's
   8-instruction window does not reach across the listing boundary. Whether
   that is a site the sweep should book is a window question, and
   `--callee-column` deliberately does not decide it.
4. **The six case handlers still have no function entry**, and `0x0D1E3` is
   now the third `lcall 0xD319` in bytes no listing covers — which is a
   coverage statement, not a finding about the bytes.
5. **`0x0864` has no row in `xdata-086x-dispatch-sites.csv` and no
   `registers.yaml` entry.** It is not absent from the committed data:
   `xdata-registers.csv` books it with two references (one write, one
   passed-to-call), and this resolver's table places a bank0 read at `0x0D17E`
   and a bank0 write at `0x0D27E`, both `literal` — each listing loads DPTR
   itself. §1's fifteen-address sweep does not sweep it. What is missing is a
   `registers.yaml` entry, and that is its own issue.