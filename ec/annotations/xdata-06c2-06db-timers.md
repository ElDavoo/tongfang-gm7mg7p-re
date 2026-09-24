# `0x06C2`-`0x06DB`: the counter sweep at `bank1:0x8001`-`0x8189`

Issue #179 asked what the `main-ec-002` cluster actually is: how many distinct
timers it holds, what decrements each, what reloads it, and what gates it. This
is the answer, and it is a reading of `ec/decompiled/bank1/8018.c` beside
`ec/decompiled/bank1/80EF.asm` — the machine code and one reading of it. Every
byte count below is re-derivable from the committed image by §1, and
`../tools/check_register_counts.py` recomputes the `static_refs*` numbers in
`registers.yaml` and fails on a mismatch.

Nothing here is a live observation. No register was read, written or read back,
and nothing ran on the machine (`../../CLAUDE.md`, "Cloud agents cannot reach
the hardware"). All 43 addresses are `present-untested`, and none is `absent`:
no entry in this file or in `registers.yaml` claims a zero is an absence.

**Two things are settled, and one of them is a correction to the issue.**

- **The block is one 393-byte routine, not 43 related registers.** 37 of the 43
  addresses are countdowns the same twenty instructions walk over; the other 6
  are what four of the countdowns do when they reach zero. A co-occurrence read
  as a mechanism is the one thing `xdata-register-map.md` §6 says a cluster must
  not be turned into by accident, so §6 lists exactly what this does not settle
  and the block still gets no name.
- **Its headline census numbers are an artefact of how the routine is
  exported.** `main-ec-002` is credited with 4,965 references and 126 touching
  functions. **At least 4,642 of those references — 93% — are the same 393
  bytes counted 42 times over**, once per overlapping function boundary. The
  43 addresses have **345 direct `MOV DPTR,#addr` sites between them in the
  whole image**, which is the number that means something. §2a measures this.

## 1. How to reproduce it

```console
$ cd ec/tools
$ python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 \
      0x0460 0x0468 0x055F 0x0621 0x0635 0x0636 0x0637 0x0638 0x0639 0x063A \
      0x06C2 0x06C3 0x06C5 0x06D1 0x06D2 0x06D6 0x06D8 0x06D9 0x06DA 0x06DB \
      0x06F3 0x0706 0x070B 0x070D 0x0723 0x07F3 0x07F6 0x0809 0x080C 0x080D \
      0x0811 0x0843 0x0844 0x085B 0x0890 0x08A7 0x08A8 0x08E4 0x0981 0x0982 \
      0x0985 0x0986 0x09CE --csv > /tmp/timers-sites.csv
$ python3 - <<'EOF'
import collections, csv
def bucket(a):
    if a.startswith("DPTR handed"): return "ho"
    if a.startswith("no movx"): return "unr"
    r, w = "read" in a, "write" in a
    return "rmw" if r and w else ("wr" if w else "rd")
rows = list(csv.DictReader(open("/tmp/timers-sites.csv")))
by = collections.defaultdict(list)
for r in rows:
    by[int(r["addr"], 16)].append(r)
print("| addr | EC | PD | rd | wr | rmw | ho | unr | EC-side writers outside 0x8001-0x8189 |")
print("|---|---:|---:|---:|---:|---:|---:|---:|---|")
for a in sorted(by):
    ec = [r for r in by[a] if r["region"] != "pd-image"]
    pd = [r for r in by[a] if r["region"] == "pd-image"]
    m = collections.Counter(bucket(r["access"]) for r in ec)
    out = ", ".join(f"{r['region']} `{r['runtime']}`" for r in ec
                    if "write" in r["access"]
                    and not 0x8001 <= int(r["runtime"], 16) <= 0x8189)
    print(f"| `{a:#06x}` | {len(ec)} | {len(pd)} | {m['rd']} | {m['wr']} |"
          f" {m['rmw']} | {m['ho']} | {m['unr']} | {out or '—'} |")
EOF
```

That is the whole sweep, it is read-only, and it needs no hardware. The second
command is what prints §3. **The last column under-counts writers**, for a
reason §5 measures rather than asserts: `trace_xdata_refs.py` classifies a site
by walking forward from the `MOV DPTR,#addr` and stopping at the first
control-flow instruction, so a store a branch jumps over is invisible to it.
The block's own reload is exactly such a store.

The decompile itself is read, not run:

```console
$ sed -n '16,145p' ec/decompiled/bank1/8018.c
$ sed -n '7,101p'  ec/decompiled/bank1/80EF.asm
```

## 2. One routine, exported 42 times, and the census that followed

`bank1:0x8001`-`0x8189` is **393 bytes ending in a `ret` at 0x8189**, and
`ec/decompiled/index.csv` splits it into 42 exports. Three facts make the split
a hypothesis rather than a description, and all three are checkable:

- **The 42 sizes sum to exactly 393**, the length of the run. The boundaries
  tile it with no gap and no overlap, which is what a function-splitting pass
  produces and what 42 independent routines almost never do.
- **16 of the 42 listings hold exactly one instruction.** `8008.asm` and
  `8010.asm` are one `movx @DPTR, A`; `8017.asm` is one `dec A`. The other 13
  one-instruction listings are the same shape.
- **All 42 `.c` files decompile the whole body.** Every one of them carries the
  sweep's final block — `0x08A8` reaching zero, `0x0985 &= 0xfb`, `0x0723 &=
  0xef` — and that block starts at `0x8171`, 361 bytes past the smallest
  listing's own boundary at `0x8008`. The `.c` is not a decompile of its own
  bytes; it is a decompile of the routine Ghidra actually has.

The clearest single comparison is `8001.c` against `8018.c`. Strip the plate
comments and the two bodies differ in 12 lines out of 135: `8001.c` starts
three instructions earlier, at the `mov DPTR,#0x06C6`, and so spells out
`0x06C6`, `0x06CD` and `0x06D1` explicitly; `8018.c` starts at the store-back
for `0x06D2` and opens with `*param_2 = param_1`. From 0x8019 on they are the
same 43 countdowns, differing only in what Ghidra called the R7 return of the
two `lcall`s (`param_1` vs `param_3`) because the two bodies start at different
points in the register allocation.

**So the run is one routine, and 42 rows in
`../annotations/ghidra-functions.csv` describe slices of it.** The issue listed
20 addresses as unnamed — 18 in the run plus `1984`/`198A`; 17 already had rows,
and the three that did not — `8008`, `8010`, `8017` — are rows this change adds,
each saying in its own comment that the one-instruction boundary is the
call-target scan's hypothesis.
`bank-call-audit.md` §1 is the standing caveat on that census, and it is an
upper bound, not a partition.

### 2a. What that does to the census's headline numbers

`xdata_register_map.py` counts references by searching the **decompiled C** for
address tokens. It has no way to know that 42 of those files are the same 393
bytes, so it counts them 42 times. Counting the `XDATA_`/`DAT_EXTMEM_` tokens
per address and splitting them by whether the file is one of the 42:

| | tokens from the 42 exports of the run | tokens from every other file | total |
|---|---:|---:|---:|
| the sweep's 46 byte addresses | **4,784** | 418 | 5,202 |

For the 43 cluster addresses alone that is **4,642 of the 4,988 their rows sum
to — 93%** — and the per-address result is starker than the total:

| addr | census `refs` | direct `MOV DPTR,#addr` sites in the image |
|---|---:|---:|
| `0x0460` | 115 | 24 |
| `0x0468` | 90 | 17 |
| `0x055F` | 124 | 3 |
| `0x0621` | 43 | 2 |
| `0x0635` | 72 | 1 |
| `0x0636` | 91 | 3 |
| `0x0637` | 97 | 2 |
| `0x0638` | 96 | 1 |
| `0x0639` | 99 | 1 |
| `0x063A` | 136 | 1 |
| `0x06C2` | 126 | 15 |
| `0x06C3` | 115 | 2 |
| `0x06C5` | 128 | 4 |
| `0x06D1` | 42 | 8 |
| `0x06D2` | 47 | 3 |
| `0x06D6` | 148 | 1 |
| `0x06D8` | 115 | 2 |
| `0x06D9` | 118 | 3 |
| `0x06DA` | 124 | 5 |
| `0x06DB` | 131 | 4 |
| `0x06F3` | 60 | 1 |
| `0x0706` | 160 | 1 |
| `0x070B` | 121 | 2 |
| `0x070D` | 132 | 4 |
| `0x0723` | 120 | 16 |
| `0x07F3` | 133 | 9 |
| `0x07F6` | 119 | 9 |
| `0x0809` | 132 | 39 |
| `0x080C` | 60 | 29 |
| `0x080D` | 137 | 78 |
| `0x0811` | 127 | 7 |
| `0x0843` | 168 | 1 |
| `0x0844` | 168 | 1 |
| `0x085B` | 127 | 6 |
| `0x0890` | 106 | 3 |
| `0x08A7` | 132 | 4 |
| `0x08A8` | 170 | 2 |
| `0x08E4` | 126 | 4 |
| `0x0981` | 127 | 2 |
| `0x0982` | 127 | 2 |
| `0x0985` | 115 | 11 |
| `0x0986` | 135 | 5 |
| `0x09CE` | 129 | 7 |
| **total, 43 addresses** | **4,988** | **345** |

(The 4,988 is the sum of the 43 rows in `xdata-registers.csv`. The
`main-ec-002` row in `xdata-clusters.csv` records 4,965 for the same membership,
and the 23 between them is a definitional split inside the tool, not staleness:
both numbers reproduce from a fresh generation. Five of the 43 members are
`program=both` — `0x07F3`, `0x07F6`, `0x0809`, `0x080C`, `0x080D` — and for
those the register row absorbs both programs and counts an address once per
program (`xdata_register_map.py:648-655`, `:674`) while the cluster row sums one
program's own count (`:718`). Two columns both named `refs`, defined
differently. The whole of the gap is those five addresses' PD references, 4 + 4
+ 5 + 2 + 8 = 23. Only the name and spelling columns of the committed CSVs are
stale — §6.)

**So the issue's "nine of the ten busiest addresses in the firmware are in it"
is an artefact of the export, not a statement about the bytes.** `0x0843` and
`0x0844` are credited with 168 references each; each has **one** direct site in
the whole image, and it is this sweep's decrement. `0x06D6` is credited with
148 and has one. `0x08A8` is credited with 170 and has two. None of them is
among the ten busiest addresses in the firmware once the 42-fold count is
removed — that is what §3's table is for, and the largest of the 43 by direct
sites is `0x080D` at 78, of which 74 are in the PD image.

**This is not fixed here**, for the same reason the boundaries are not: the
census has no notion of overlapping exports, and giving it one is the
classifier's own issue. What this change does is record the size of the effect
and refuse to read the inflated columns as evidence — §3 uses the image, not
the census.

## 3. The per-address table

Two tables. The first is the reading — what the sweep does to each byte — and is
not mechanical. The second is §1's, and is.

**37 of the 43 cluster addresses are countdowns this routine decrements, and 6
are the side effects four of them have at zero:**

| what the sweep does to it | n | addresses |
|---|---:|---|
| decrements while non-zero | 29 | `0x06C6` `0x06CD` `0x06D1` `0x06D2` `0x06F3` `0x0635` `0x0636` `0x0637` `0x0638` `0x0639` `0x0890` `0x07F6` `0x06C2` `0x06C3` `0x06DA` `0x08E4` `0x055F` `0x09CE` `0x070B` `0x06C5` `0x0986` `0x070D` `0x07F3` `0x0981` `0x0982` `0x0811` `0x0809` `0x080D` `0x08A7` |
| decrements while non-zero **and** the sign bit is clear | 1 | `0x063A` |
| reloads with 9 at zero, and returns early otherwise | 1 | `0x06D6` |
| decrements only while `0x0440` is non-zero | 3 | `0x06D8` `0x085B` `0x06DB` |
| decrements only while **two predicate calls** both return zero | 1 | `0x06D9` |
| decrements, and does something extra at zero | 4 | `0x0706` `0x0843` `0x0844` `0x08A8` |
| written only as another byte's zero-reach side effect | 6 | `0x0460` `0x0468` `0x0621` `0x0723` `0x080C` `0x0985` |

29 + 1 + 1 + 3 + 1 + 4 = **39 countdowns**, and 39 + 6 = **45 distinct bytes
written**, plus `0x0440` read as a gate: 46 distinct `MOV DPTR,#imm`
immediates in the run, which is what the sweep actually reaches.

**The 37/6 split is the accounting, and the two bytes missing from the cluster
are the clustering's, not the code's.** `0x06C6` and `0x06CD` are the first two
countdowns in the run and are decremented by it exactly like the rest, but the
clustering put `0x06C6` in `main-ec-118` and `0x06CD` in `main-ec-198` — 7 and
26 references on their own rows in `xdata-registers.csv`, which is where the
issue's figures come from. So 37 of the 43 are the countdowns, 6 are the
side-effect targets, and the two the cluster cut away are the two whose reload
is the most legible in the whole block — see §5. The issue was right to scope
the reading to the span rather than the cluster id, and this is the evidence for
it.

| addr | EC | PD | rd | wr | rmw | ho | unr | EC-side writers outside 0x8001-0x8189 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `0x0460` | 24 | 0 | 14 | 2 | 4 | 2 | 2 | bank0 `0x87C1`, bank0 `0x8AA7`, bank0 `0x8AB7`, bank0 `0x8BA9`, bank0 `0x8BB6` |
| `0x0468` | 17 | 0 | 10 | 2 | 4 | 1 | 0 | bank0 `0x87CD`, bank0 `0x8AE2`, bank0 `0x8AFD`, bank0 `0x8BFD`, bank0 `0x8C22` |
| `0x055f` | 3 | 0 | 1 | 2 | 0 | 0 | 0 | bank1 `0xDB88`, bank1 `0xE090` |
| `0x0621` | 2 | 0 | 1 | 1 | 0 | 0 | 0 | — |
| `0x0635` | 1 | 0 | 1 | 0 | 0 | 0 | 0 | — |
| `0x0636` | 3 | 0 | 2 | 0 | 0 | 1 | 0 | — |
| `0x0637` | 2 | 0 | 2 | 0 | 0 | 0 | 0 | — |
| `0x0638` | 1 | 0 | 1 | 0 | 0 | 0 | 0 | — |
| `0x0639` | 1 | 0 | 1 | 0 | 0 | 0 | 0 | — |
| `0x063a` | 1 | 0 | 1 | 0 | 0 | 0 | 0 | — |
| `0x06c2` | 15 | 0 | 15 | 0 | 0 | 0 | 0 | — |
| `0x06c3` | 2 | 0 | 2 | 0 | 0 | 0 | 0 | — |
| `0x06c5` | 4 | 0 | 4 | 0 | 0 | 0 | 0 | — |
| `0x06d1` | 8 | 0 | 5 | 3 | 0 | 0 | 0 | bank0 `0xB58F`, bank0 `0xB6E1`, bank1 `0x8F4F` |
| `0x06d2` | 3 | 0 | 2 | 1 | 0 | 0 | 0 | bank1 `0x8F66` |
| `0x06d6` | 1 | 0 | 1 | 0 | 0 | 0 | 0 | — |
| `0x06d8` | 2 | 0 | 1 | 1 | 0 | 0 | 0 | bank1 `0x9800` |
| `0x06d9` | 3 | 0 | 1 | 2 | 0 | 0 | 0 | bank1 `0x86E2`, bank1 `0x982E` |
| `0x06da` | 5 | 0 | 2 | 3 | 0 | 0 | 0 | bank1 `0x97A9`, bank1 `0xB7E2`, bank1 `0xB83A` |
| `0x06db` | 4 | 0 | 4 | 0 | 0 | 0 | 0 | — |
| `0x06f3` | 1 | 0 | 1 | 0 | 0 | 0 | 0 | — |
| `0x0706` | 1 | 0 | 1 | 0 | 0 | 0 | 0 | — |
| `0x070b` | 2 | 0 | 1 | 1 | 0 | 0 | 0 | bank1 `0x9806` |
| `0x070d` | 4 | 0 | 3 | 1 | 0 | 0 | 0 | bank1 `0xC6B0` |
| `0x0723` | 16 | 0 | 1 | 1 | 14 | 0 | 0 | bank0 `0x910E`, bank0 `0x9117`, bank0 `0x912B`, bank0 `0x9134`, bank0 `0x97F9`, bank0 `0xA00E`, bank0 `0xA1BB`, bank0 `0xA2B5`, bank0 `0xBE0D`, bank1 `0x92C8`, bank1 `0x986E`, bank1 `0xC447`, bank1 `0xC6C7`, bank1 `0xC6D0` |
| `0x07f3` | 4 | 5 | 2 | 2 | 0 | 0 | 0 | bank1 `0x9F61`, bank1 `0xA241` |
| `0x07f6` | 5 | 4 | 3 | 2 | 0 | 0 | 0 | bank1 `0xA1B1`, bank1 `0xA1B8` |
| `0x0809` | 2 | 37 | 1 | 1 | 0 | 0 | 0 | bank1 `0x9F6D` |
| `0x080c` | 7 | 22 | 2 | 5 | 0 | 0 | 0 | bank0 `0xA03A`, bank0 `0xA06A`, bank0 `0xA295`, bank1 `0x986A` |
| `0x080d` | 4 | 74 | 2 | 2 | 0 | 0 | 0 | bank1 `0x9F46`, bank1 `0xAB3F` |
| `0x0811` | 2 | 5 | 1 | 1 | 0 | 0 | 0 | bank1 `0x9FBA` |
| `0x0843` | 1 | 0 | 1 | 0 | 0 | 0 | 0 | — |
| `0x0844` | 1 | 0 | 1 | 0 | 0 | 0 | 0 | — |
| `0x085b` | 2 | 4 | 2 | 0 | 0 | 0 | 0 | — |
| `0x0890` | 3 | 0 | 2 | 1 | 0 | 0 | 0 | bank0 `0xA380` |
| `0x08a7` | 4 | 0 | 3 | 1 | 0 | 0 | 0 | bank0 `0xA1B0` |
| `0x08a8` | 2 | 0 | 1 | 1 | 0 | 0 | 0 | bank0 `0xA1C2` |
| `0x08e4` | 4 | 0 | 2 | 2 | 0 | 0 | 0 | bank1 `0x8716`, bank1 `0xBD2C` |
| `0x0981` | 2 | 0 | 2 | 0 | 0 | 0 | 0 | — |
| `0x0982` | 2 | 0 | 2 | 0 | 0 | 0 | 0 | — |
| `0x0985` | 11 | 0 | 1 | 0 | 10 | 0 | 0 | bank0 `0x90B2`, bank0 `0x90BB`, bank0 `0x90D2`, bank0 `0x90DB`, bank0 `0x9800`, bank0 `0x98FB`, bank0 `0xA015`, bank0 `0xA1B4`, bank0 `0xA2C0` |
| `0x0986` | 5 | 0 | 3 | 2 | 0 | 0 | 0 | bank0 `0x8D16`, bank0 `0x8E29` |
| `0x09ce` | 7 | 0 | 6 | 1 | 0 | 0 | 0 | bank0 `0xCCAD` |

Three columns in that table are worth reading rather than skimming:

- **`0x0809` and `0x080D` are 39 and 78 references, of which 37 and 74 are in
  the PD image.** They are two of the cluster's busiest addresses in the census
  and two of its quietest in the EC firmware, which is 2 and 4 sites
  (`static_refs_main_ec`, and the `EC` column above). A shared
  address *number* is not a shared byte, and the split is why every row in
  `registers.yaml` carries all three count keys. `0x0811` and `0x085B` are
  small versions of the same shape, and `0x07F3`, `0x07F6` and `0x080C` are
  middling ones.
- **`0x0723` and `0x0985` are 14 and 10 read-modify-writes with almost no
  plain reads.** They are flag bytes assembled a bit at a time. That is a shape
  and not a name, and §3 is where the shape goes rather than the symbol.
- **`0x06c2` has 15 sites, all direct reads, and no writer outside the sweep.**
  The busiest address in the `0x06C2`-`0x06DB` span by the measure that counts
  something, and the one whose countdown this reading explains least.

Each address's own reading is in its `registers.yaml` `note:`, one per row, all
`present-untested`. No byte is named from its shape: every one is
`XDATA_<addr>`, which is greppable, unique, and claims nothing.

## 4. The two gates, and the one that is a return

The issue's own question was what gates the block. Two things do, and a third
thing that is not a gate but reads like one.

**`0x0440`, tested as a value, three times.** At `0x807E` and again at
`0x80EC` and `0x8153`, the sweep reads `0x0440` and branches past `0x06D8`,
`0x085B` and `0x06DB` when it is zero. Those three bytes freeze rather than
count down. `0x0440` is `XDATA_0440` in `registers.yaml`: **43 EC-side sites,
every one a direct read, so no direct `MOV DPTR` site writes it** — the page's
busiest byte, with a value nothing here establishes. A writer does exist and is
not one of those 43: `code_table_scatter_to_xdata` (bank1 `0xA530`) stores
`0x00` to it (`xdata-0440-readers.md` §5). Elsewhere the same byte is tested
against `5`, `6` and `7` by `dec_0443_low3_unless_0440_5_6_7` and
`inc_0443_low3_unless_0440_5_6_7` (`bank1:0xF2CA` and `0xF2F3`), so the block's
gate is "not zero" and another routine's is "not 5, 6 or 7". What selects
between those readings is not in the decompile.

**Two predicate calls, tested as returns, on `0x06D9` alone.** At `0x8096` the
sweep `lcall`s `0x1984`, copies R7 into A and branches to `0x80AA` if it is
non-zero; at `0x809C` it does the same with `0x198A`. Only when **both** left
R7 zero does it reach `0x06D9` at all. This is the one countdown in the block
whose progress depends on something other than its own value.

Both forwarders are already annotated, and the reading is in their targets:

| call | row | target | what the target is |
|---|---|---|---|
| `0x1984` | `trampoline_to_c10c` | `0xC10C` | **no exported function in any program** |
| `0x198A` | `trampoline_to_c1e7` | `0xC1E7` | bank0 `test_1664_bit0` — returns 1 in R7 if bit 0 of `0x1664` is set |

**So one of the block's two gates is a test of bit 0 of `0x1664`, and the other
is a routine this repository has not exported at all.** That is the finding, and
it is why `0x06D9` matters more than its 3 sites suggest: a countdown whose
rate is set by a predicate, one arm of which is unread. `0x1664` has no row in
`registers.yaml` and is a follow-up of its own.

**The third thing is a return, not a test.** `0x06D6` is the only reload in the
block: at `0x806C` a non-zero value is decremented and the routine returns at
`0x8074`, skipping everything from `0x06C2` downward; a zero value is loaded
with `9` at `0x8075`, stored at `0x8077`, and the sweep continues. `0x06D6` is
therefore both the reload and the rate control for the lower two-thirds of the
block, and `9` is a set-point the code states rather than one a reader supplies.
It is the only byte in the whole run whose period is legible from the code.

## 5. The reload search, and the store the site scanner cannot see

**What was searched, and how.** Two independent methods over the decompiled
tree, with this run's own 42 fragment `.c` files excluded — they are 42 copies
of the same body and would report every write 42 times, which is §2a's problem
again:

1. the EC-side write sites in §1's sweep, outside `0x8001`-`0x8189`;
2. a spelling search for `DAT_EXTMEM_<addr>` in an assignment position across
   every other `.c` in `ec/decompiled/`, both EC and PD.

**The two methods disagree, in both directions, and the disagreement is the
result.** They are not measuring the same thing:

- **The sweep misses writers.** Its access column comes from a forward walk that
  stops at the first control-flow instruction. `0x06D6`'s reload is exactly that
  shape — the `mov DPTR,#0x06D6` at `0x806C` is followed by `movx A,@DPTR` and
  `jz 0x8075`, so the walk stops and the `movx @DPTR,A` that stores 9 at
  `0x8077` is never seen. The same happens to `0x0636` and `0x0637`: the
  `mov DPTR,#0x0636` at `0xF226` is followed by `movx A,@DPTR` and
  `jnz 0xF242`, so the `movx @DPTR,A` at `0xF22E` is invisible, and the sweep
  reports both as write-free while the decompile at `bank1:0xF219` and
  `0xF246` says otherwise.
- **The spelling search misses writers too.** `0x09CE`'s only writer outside
  the run is at `bank0:0xCCAD`, which lies in the gap between the `0xCC51` and
  `0xCCFC` exports, so it is in no `.c` at all. A grep cannot see a function
  that did not decompile.

Taking the union of the two, for the 43 addresses:

| | count | addresses |
|---|---:|---|
| a writer outside the run was found | 26 | the other 26 |
| **no writer outside the run found by either method** | **17** | `0x0621` `0x0635` `0x0638` `0x0639` `0x063A` `0x06C2` `0x06C3` `0x06C5` `0x06D6` `0x06DB` `0x06F3` `0x0706` `0x0843` `0x0844` `0x085B` `0x0981` `0x0982` |

16 of those 17 are countdowns (`0x0621` is a side-effect target), and for
several of them the sweep is the *only* thing in the firmware that touches the
byte at all: `0x0635`, `0x0638`, `0x0639`, `0x063A`, `0x06D6`, `0x06F3`,
`0x0706`, `0x0843` and `0x0844` have exactly one EC-side site each, and it is
the decrement.

**This is "not found by this method", and the blind spot is named rather than
assumed away.** Neither method can see a write reached through a computed DPTR,
a register-indirect access, or a table — and `0xC10C`, the one routine in the
block that is not exported, is banked code no spelling search over the
decompiled tree can reach at all. It is the prime suspect for the seventeen.

**One correction to the record, because the plan this work follows got it
wrong.** The reading above was first taken to be: no writer outside the sweep
for `0x06C2 0x06C3 0x06C5 0x06D6 0x0706 0x06D8 0x06DB 0x085B`. That is wrong in
both directions. `0x06D8` **does** have one — `bank1:0x9800`, `mov A,#0x0A` then
`movx @DPTR,A` in the body at `0x976E`, the same store that loads `0x070B` and
`0x044C` — and ten more addresses belong in the list that were left out
of it: `0x0621 0x0635 0x0638 0x0639 0x063A 0x06F3 0x0843 0x0844 0x0981 0x0982`. The wrong
version is left here rather than deleted, per `../../docs/findings.md` §4a's
pattern.

**And the two bytes the clustering cut away are the two whose reload is
clearest.** `0x06C6` and `0x06CD` are not in `main-ec-002`, and both are reloaded
by an `if (byte == 0) byte = 2` store that this repository has already
annotated: `dec_0443_low3_unless_0440_5_6_7` and
`inc_0443_low3_unless_0440_5_6_7` write `2` to `0x06C6` at `0xF2CC` and
`0xF2F5`, and `if_06cd_zero_set_02_set_06ff_20` at `bank1:0xF290` does the same
for `0x06CD`. The clustering's boundary dropped the two addresses whose period
is 2 and legible, and kept 17 whose writer was not found. That is not an
argument for or against the clustering — `xdata-register-map.md` §4.2 says a
cluster is a connected component over touching- and writer-sets, and both bytes
have plenty of other readers — but it is the concrete cost of scoping a reading
to a cluster id, and it is why §3 reads the span.

## 6. What this does not establish

- **Nothing observed on hardware.** No register was read, written or read back,
  no live test ran, and no behaviour was observed. Every status is
  `present-untested`: a write being accepted, or a count being readable, is not
  evidence the EC acts on a byte.
- **The block gets no name and no purpose.** 43 addresses reached by one routine
  is evidence about *shape* — which routine, which bytes, in what order — and
  not about meaning. `xdata-register-map.md` §6 is the standing rule: a cluster
  is a co-occurrence, and naming a block of XDATA from it puts a guess where a
  later reader takes it for a fact. The routine's own name,
  `decrement_nonzero_xdata_counters`, describes what it does to the bytes and
  stops there; it is not a claim about what the bytes are.
- **"Timer" is a reading of the instruction, not of the value.** The code
  decrements these bytes once per pass. What the EC then does when one reaches
  zero, and what any of them is *counting*, is not in the decompile. The four
  zero-reach side effects are the only statement about consequence the block
  makes, and they are four of 39.
- **No byte is named from its shape.** All 43 stay `XDATA_<addr>`. `0x0723` and
  `0x0985` are flag-byte shapes, `0x06D6` behaves like a set-point, and neither
  is a name.
- **Every "not found" here is "not found by this method".** §5's seventeen, and
  every zero in the sweep, are gaps in a search with a named blind spot — never
  `absent`. No entry in this change is `absent`, and `registers.yaml`'s own
  header keeps the `0x07B9` retraction for the method's limits.
- **The function boundaries are a hypothesis**, and §2a is a consequence of
  that rather than a separate defect: 42 exports is how the committed project
  has this routine cut, not how the firmware is structured.

### 6a. The direction classifier, measured, and why it is not this change's diff

`xdata-registers.csv` and `xdata-clusters.csv` are **not** regenerated here and
are **not** read as evidence. §2a is the first reason; the second is the
direction classifier, and it was measured rather than asserted.

**The defect.** `ec/tools/xdata_register_map.py:277` decides an occurrence is a
store by testing `stripped.startswith(a) for a in ASSIGN`, and `ASSIGN` at line
138 contains `"="` — so `"== 0x12".startswith("=")` is true, and every `==` in
the tree is counted as a write. **The effect**, from regenerating the census
twice, once as committed and once with a guard that rejects a bare `=` followed
by a second `=`:

| | as committed | with the guard |
|---|---:|---:|
| main-EC `write` references (1,015 addresses, 13,100 refs) | 3,569 | 2,827 |
| main-EC `read` references | 6,773 | 7,519 |
| PD-image `write` references (109 addresses, 605 refs) | 193 | 142 |
| references in `write` for the 48 addresses in both images | 257 | 217 |
| **references leaving `write`, all three programs** | — | **833** |
| **addresses whose `write` column changes** | — | **210 of 1,172** |
| `0x08A8` read / write | 84 / 44 | **126 / 2** |
| `0x0843` read / write | 84 / 42 | **126 / 0** |
| main-EC clusters at threshold 0.50 | 384 | 376 |
| **`main-ec-002`** | **43 addresses, 4,965 refs** | **44 addresses, 248 refs** |

```console
$ rm -rf /tmp/census && mkdir -p /tmp/census/{before,after}/ec/tools
$ for v in before after; do
>   cp ec/tools/xdata_register_map.py /tmp/census/$v/ec/tools/
>   for d in decompiled annotations firmware ghidra; do
>     ln -s "$PWD/ec/$d" /tmp/census/$v/ec/$d
>   done
> done
$ python3 - <<'EOF'
p = '/tmp/census/after/ec/tools/xdata_register_map.py'
s = open(p).read()
old = '''    nxt = text[end:]
    stripped = nxt.lstrip()
    if not any(stripped.startswith(a) for a in ASSIGN):'''
new = '''    nxt = text[end:]
    stripped = nxt.lstrip()
    if stripped.startswith("=="):
        return False
    if not any(stripped.startswith(a) for a in ASSIGN):'''
assert old in s
open(p, 'w').write(s.replace(old, new))
EOF
$ for v in before after; do
>   python3 /tmp/census/$v/ec/tools/xdata_register_map.py \
>       --out-registers /tmp/census/$v/registers.csv \
>       --out-clusters  /tmp/census/$v/clusters.csv \
>       --registers ec/annotations/registers.yaml > /dev/null
> done
$ python3 - <<'EOF'
import csv
u = {r['addr']: r for r in csv.DictReader(open('/tmp/census/before/registers.csv'))}
f = {r['addr']: r for r in csv.DictReader(open('/tmp/census/after/registers.csv'))}
print("references leaving 'write':",
      sum(int(u[k]['write']) - int(f[k]['write']) for k in u))
print("addresses whose 'write' changes:",
      sum(1 for k in u if u[k]['write'] != f[k]['write']), "of", len(u))
EOF
```

**The absolute totals here are the committed census, and they match the
14,801-reference table in `xdata-register-map.md` §4.1** — the unmodified tool
run over the current tree sums to 7,483 / 4,019 / 2,480 / 548 / 271, and its own
full-census oracle passes. What this tree is ahead on is *symbol coverage*: the
43 new symbols move references from the `DAT_EXTMEM_` spelling to the symbol
table's, which is why the committed CSVs' `spelled_as` / `name` /
`named_addrs` / function-name columns are stale and `--self-test` is red on the
`DAT_EXTMEM_` spelling oracles. A rename does not move a reference from one
direction bucket to another, so every absolute number above is the report's
number, and the deltas are a property of the classifier alone.

**The last row is why this is out of scope here, and it is a new question
rather than a footnote: the cluster this issue is scoped to does not survive
the classifier fix in its current shape.** Its 4,965 references are largely the
`==` comparisons in the 42 overlapping exports, and the writer-set Jaccard that
holds the cluster together was computed over exactly those. With the guard it
becomes a 44-address, 248-reference cluster. Neither number is right yet — both
still carry §2a's 42-fold duplication — but the direction is not in doubt, and
an issue scoped to "read `main-ec-002`" would be scoped to a membership its own
prerequisite changes.

The issue's own "`0x08A8` is recorded as 84 reads / 44 writes / 42 read+write,
and 42 of its comparisons are `==`" is a second, independent misreading:
`xdata-register-map.md` §4.1 defines the `read+write` column as "an `=` target
whose right-hand side names the same address", so `0x08A8`'s 42 are 42
read-modify-writes, not 42 equality tests. And per §2a all 42 of them come from
the 42 overlapping exports. The wrong reading is left in the issue, not
silently dropped.

**Nothing in §3 or §4 needs a census column.** Every count in this file comes
from the `.c`, the `.asm` and the image.

## 7. The read-only step, for a human with the machine

**Nothing below was run.** This is the procedure, written down, for someone
holding the laptop. It is read-only on purpose: `0x0440`'s value space is not
established (43 read sites, no direct `MOV DPTR` writer), and this block's
zero-reach writes drive `0x080C`, `0x0621`, `0x0985` and `0x0723`. **A live
*write* to any byte here is
a human's decision, not something this change ships.**

Both tools already exist and need no new code. `ec/tools/ecmem.py` is the Linux
path (root and `CONFIG_DEVMEM`; physical window `0xFE410000`, the same
`MMRW(0xFE410000 + Arg0, …)` the vendor's `ECRW` takes, so a read here reads
what Windows reads). `windows/tools/ec_watch.py` is the Windows one and needs
the vendor's `ecrw`; its 0.25 s default sweep is close enough to the 0.2 s
below to use as is.

```console
# 1. The reload, sampled. Does 0x06D6 step 9 -> 8 -> ... -> 0 and return to 9?
$ for i in $(seq 1 300); do
>   printf '%s %s\n' "$(date +%T)" "$(sudo python3 ec/tools/ecmem.py read 0x06d6)"
>   sleep 0.2
> done

# 2. Which of the 37 actually tick on this machine? Every 0x06Cx byte the
#    sweep touches is inside this window.
$ python3 windows/tools/ec_watch.py --start 0x06c0 --len 0x20 \
      --interval 0.2 --seconds 60 --csv timers.csv

# 3. The predicate gate against the countdown it guards.
$ python3 ec/tools/ecmem.py read 0x1664 0x06d9
```

Read them in this order, because each one distinguishes a pair of readings:

1. **`0x06D6` over time.** The question is whether it steps down to zero and
   comes back to 9 at a fixed period, and what that period is. If it never
   moves within the sample, the reload is reached by a writer this method did
   not find — the block is not reached on the path being watched, or the sample
   is too short. If it moves at an irregular interval, the period is set
   elsewhere. **The period is the one number this block yields that no static
   read can supply**, and `9` is the only set-point the code states.
2. **The sweep window.** `ec_watch.py` separates *busy* from *quiet* addresses
   and neither label is a claim about meaning — it says a byte changed while
   the run went on, not why. What it settles here is narrower and worth
   stating precisely: **which of the 37 count down on this board at all.** A
   byte that never moves is a countdown no current code path reaches, which is
   a different statement from a byte that is not a countdown — and it is the
   boundary between the two claims this file is careful about.
3. **`0x1664` bit 0 against `0x06D9`.** §4 says `0x06D9` only counts down while
   both forwarders return zero, and one of them is `test_1664_bit0`. If
   `0x06D9` holds still whenever bit 0 of `0x1664` is set, the `0xC1E7` gate is
   confirmed behaviourally. If `0x06D9` counts down regardless, that gate means
   something other than what its name says, and the annotation is wrong.

Run 2 with the vendor Control Center started and stopped, as `ec_watch.py`'s
own docstring asks: a byte that only moves while the service runs is the vendor
touching it, not the EC's sweep.

## 8. The open questions

1. **`0xC10C` has no exported function in any program**, and `0x06D9`'s
   countdown hangs off it. This is the highest-value item on the block and it
   needs a function seed — which needs `--mode rebuild-project`, so it wants a
   branch of its own.
2. **The reload path for the seventeen in §5.** The blind spot is named rather
   than bounded: a computed DPTR, a register-indirect access and a table are
   all invisible to both methods here, and `0xC10C` is banked code a spelling
   search cannot reach.
3. **The direction-classifier fix** at `ec/tools/xdata_register_map.py:277`,
   measured in §6a: 833 references out of `write`, 210 addresses, and
   `main-ec-002` itself reshaped. It wants its own diff with its own
   before/after census, and it should be read together with the de-duplication
   question below or the new numbers will be wrong in the other direction.
4. **The census's 42-fold double count** (§2a). Nothing in
   `xdata_register_map.py` knows that 42 exports are one routine, and until
   something does, every reference count for a byte this sweep touches is
   inflated by roughly 42× — which is most of what made this cluster look
   like the firmware's busiest.
5. **`0x1664` is read as a gate by the block and has no `registers.yaml` row.**
   One site, one bit, one caller — but the caller is the only countdown in the
   block whose rate is not its own value.
6. **The 42 wrong function boundaries**, if anyone wants them fixed rather than
   documented. `build_ec_decompile.py --mode rebuild-project` writes the 7 MB
   database, and two branches that both rebuild one cannot merge.
7. **`0x0440`'s value.** 43 read sites, no direct `MOV DPTR` writer, and this
   block reads it three times. What 43 places in the firmware consult it for is
   still open (`xdata-0400-045f.md` §11 carries the same question from the
   other side of the page).
