# `0x06C2`-`0x06DB`: the counter sweep at `bank1:0x8001`-`0x8189`

Issue #179 asked what the `main-ec-002` cluster actually is: how many distinct
timers it holds, what decrements each, what reloads it, and what gates it. This
is the answer, and it is a reading of `ec/decompiled/bank1/8018.c` beside
`ec/decompiled/bank1/80EF.asm` — the machine code and one reading of it. Every
byte count below is re-derivable from the committed image by §1, and
`../tools/check_register_counts.py` recomputes the `static_refs*` numbers in
`registers.yaml` and fails on a mismatch.

> **Correction, 2026-09-24 (issue #253).** The `main-ec-002` issue #179 asked
> about is `main-ec-002` again in the committed census, and the block this file
> sweeps shares not one address with the one that took the old `main-ec-002`'s
> meaning: `xdata-clusters.csv` row 3 gives `main-ec-002` 43 addresses and 4,966
> references over `0x0460`-`0x09CE`, which is this block, while the old 44-address
> block has since split in two: its 28-address half is row 4, `main-ec-003` over
> `0x045C`-`0x1C3A`, its 11-address half is row 12, `main-ec-011` over
> `0x045E`-`0x1F07`, and the four-address remainder, `0x044C 0x05F0 0x05F1 0x0841`,
> is row 50, `main-ec-049`. None of those four `addrs` columns intersects the
> others, and none of them holds an address §1 sweeps. All 43 addresses §1 sweeps carry
> `cluster_id=main-ec-002` in `xdata-registers.csv`. The ids moved when issue
> #4.3's census regeneration landed (#133 / #238), and moved again on the
> 2026-09-24 re-derivation of the census on the merged tree:
> `xdata_register_map.py:1654-1655`
> numbers clusters by size, so the 43-address block is now numbered ahead of
> the 28-address one, and `xdata-register-map.md` §5 records the same hazard for
> its own table. (`:1027`, the citation this replaces, never pointed at the sort
> on `main` either — the key is at 1629 there, and 1027 is
> `return oper in ("DPH", "DPL")` — so this corrects a long-stale citation
> rather than relocating a sound one.) Every stale id below is corrected in
> place. The ones
> inside a quote of issue #179 are left as it wrote them with this beside them,
> because
> the quote is the evidence that the id moved.
>
> **Issue #254's own instruction to change this block's id to `main-ec-003` was
> not applied, because the prediction it rested on was itself stale.** #254
> predicted `main-ec-003` from the pre-split numbering; the committed census
> puts the 43-address / 4,966-reference sweep at `main-ec-002`, and
> `../tools/check_cluster_citations.py` passes, so this page's `main-ec-002`
> needed no change and the stale `main-ec-003` was in `ec/README.md`, which is
> the copy that moved. Left visible here so a reader holding #254 reads the
> unapplied instruction rather than an oversight.
> `../tools/check_cluster_citations.py` is what holds the rest of the tree to
> the census.
>
> **This block now has a carried name, and the `main-ec-NNN` above is still a
> rank** (issue #274). The census's `cluster_key` is a content hash over the
> cluster's program and its membership, and `annotations/xdata-cluster-names.csv`
> gives this cluster the name `counter-sweep` — a name follows a cluster through
> a regeneration in changed form, an id does not, and `xdata-register-map.md`
> §4.4 is the method and the measurements behind it. Nothing in this file's
> block is rewritten: the ids above are left where the correction found them,
> because the quote and the correction are the record that the rank moved.
> `counter-sweep` is the handle new prose should quote.

Nothing here is a live observation. No register was read, written or read back,
and nothing ran on the machine (`../../CLAUDE.md`, "Cloud agents cannot reach
the hardware"). All 43 addresses are `present-untested`, and none is `absent`:
no entry in this file or in `registers.yaml` claims a zero is an absence.

> **Update, 2026-09-24 (issue #257).** The paragraph above was true when this
> file was written and is left as it was. Since then the Linux half of §7 has
> been run on the machine, read only. `0x06D6` cycles as §4 reads it, with a
> 0.997 s period. An AC unplug loaded `0x06D8` and `0x070B`, and both stepped
> once per `0x06D6` cycle, as bytes below the return should, and a suspend and
> resume loaded `0x06C5`, which does the same. Those four are now
> `confirmed-working`, and the other 39 are unchanged.
> The host window cannot reach 16 of the block's bytes or either `0x06D9` gate
> byte. The result is `../../docs/hardware-tests/xdata-06c2-06db-sweep.md`.

**Two things are settled, and one of them is a correction to the issue.**

- **The block is one 393-byte routine, not 43 related registers.** 37 of the 43
  addresses are countdowns the same twenty instructions walk over; the other 6
  are what four of the countdowns do when they reach zero. A co-occurrence read
  as a mechanism is the one thing `xdata-register-map.md` §6 says a cluster must
  not be turned into by accident, so §6 lists exactly what this does not settle
  and the block still gets no name.
- **Its headline census numbers are an artefact of how the routine is
  exported.** `main-ec-002` is credited with 4,966 references and 127 touching
  functions (issue #179 quoted 4,965 and 126 under the id `main-ec-002`; the
  figures moved by one each with the 2026-09-24 re-derivation). **At least 4,642 of those references — 93% — are the same 393
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
`main-ec-002` row in `xdata-clusters.csv` records 4,966 for the same membership,
and the 22 between them is a definitional split inside the tool, not staleness:
both numbers reproduce from a fresh generation. Five of the 43 members are
`program=both` — `0x07F3`, `0x07F6`, `0x0809`, `0x080C`, `0x080D` — and for
those the register row absorbs both programs and counts an address once per
program (`xdata_register_map.py:1385` `merge_group()`, `:1669-1670`) while the
cluster row sums one program's own count (`:1738`). Two columns both named
`refs`, defined differently. The whole of the gap is those five addresses' PD
references, 3 + 4 + 5 + 2 + 8 = 22. Only the name and spelling columns of the
committed CSVs are stale — §6. The earlier version of this parenthetical said
4,989, a gap of 23, and gave `0x07F3`'s PD share as 4; all three are one too
high, and 4,988 / 22 / 3 are what the committed CSVs sum to today.)

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
clustering put `0x06C6` in `main-ec-123` and `0x06CD` in `main-ec-201` — 7 and
26 references on their own rows in `xdata-registers.csv`, which is where the
issue's figures come from. Both ids are the census's; this file used to name
`main-ec-118` for `0x06C6`, and that id is `0x03BF 0x03C3` and holds neither
byte. So 37 of the 43 are the countdowns, 6 are the
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

Both forwarders are already annotated, and the reading is in their targets.
**Both `imm16` operands are bank-0 addresses, not bank-1 ones, and that is worth
saying before the targets are read.** Each forwarder is `mov DPTR,#imm16` then
`ljmp 0x1100`, and `0x1100` is the common-area stub this tree names
`bl51_bank_select_0`; [`bank-call-audit.md`](bank-call-audit.md) §2 counts the
trampolines that route through it — 350 to bank 0, against 53 to bank 1 through
the stub at `0x1114` — so the address is resolved *after* the bank switch, in
the bank the stub selects and not the bank the forwarder sits in. The same
audit's `bank-call-targets.csv` records both of these sites independently, at
lines 2976 and 2977, as bank0 `lcall` entries rather than as anything inside a
bank-1 body.

| call | row | target | what the target is |
|---|---|---|---|
| `0x1984` | `trampoline_to_c10c` | bank0 `0xC10C` | unexported, but it decodes to a thunk on `0xC0C9` — returns 1 in R7 if bits 1 and 2 of `0x3202` are both set |
| `0x198A` | `trampoline_to_c1e7` | bank0 `0xC1E7` | `test_1664_bit0` — returns 1 in R7 if bit 0 of `0x1664` is set |

Reading either `imm16` against a bank-1 listing gives the wrong answer, and did:
eight rows in [`ghidra-variables.csv`](ghidra-variables.csv) and one in
`ghidra-functions.csv` (`bank1,19A8`) read a forwarder target in bank 1. Seven
of them carried `0xC10C` and `0xC118` as operand bytes inside bank-1's
`FUN_CODE_c0a8` and called the questions open; the eighth (`bank1,0xA389`)
carried `0xC1E7` as bank-1's `latch_0498_bit1_or_bit3`, which writes no R7, and
so concluded the R7 it tested came from somewhere else. The bytes they read are
at the same offset in the wrong bank, and the two banks hold unrelated code
there: in bank 0, `0xC10B` and `0xC117` are the closing `ret` of the twelve-byte
thunk that precedes each, `0xC10C` and `0xC118` are `lcall` instructions, and
`0xC1E7` is `test_1664_bit0` — which does write R7, so that row's conclusion
about its own R7 was wrong too. All nine rows now carry the bank-0 reading with
the withdrawn version quoted beside it, per `docs/findings.md` §4a. What the
`19A8` row's 48-forwarder census measures is left as it is: it is a count
against **bank-1** listings, it is not re-measured here against bank 0, and no
replacement count is claimed.

**Both arms of the gate are now readable, and neither of them tests anything in
this block.** That is the finding, and it is why `0x06D9` matters more than its
3 sites suggest: a countdown whose rate is set by a predicate, and both arms of
that predicate read bytes from elsewhere in the map.

> **Superseded.** This section previously read: *"So one of the block's two gates
> is a test of bit 0 of `0x1664`, and the other is a routine this repository has
> not exported at all … one arm of which is unread. `0x1664` has no row in
> `registers.yaml` and is a follow-up of its own."* What was wrong is the
> inference, not the census: an absent export was read as an absent decoding,
> and `0xC10C` is unseeded rather than undecodable (issue #255) — the twelve
> bytes decode by hand to a thunk on `0xC0C9`, §4 below. It still has no
> committed listing, and that gap is real; what it never implied is that the
> bytes are unread. `0x1664` now carries a row. The wrong version is left here
> rather than edited away, per `docs/findings.md` §4a.

**`0xC10C` is a state-dependent predicate, and the state it reads is in its
callee.** The body is seven instructions in twelve bytes, with no `MOV DPTR`
among them:

```
C10C  12 c0 c9   lcall  0xC0C9
C10F  ef         mov    A, R7
C110  60 03      jz     0xC115
C112  7f 01      mov    R7, #0x01
C114  22         ret
C115  7f 00      mov    R7, #0x00
C117  22         ret
```

It `lcall`s `0xC0C9` — already annotated as `return_1_if_3202_bits_1_and_2` —
and restates that callee's answer in R7 as a 1 or a 0, adding nothing to it. So
**the first gate is not a plain test of `0x06D9`, nor of any byte in this
block**: what it tests is bits 1 and 2 of `0x3202`, read one call deeper, and
because `0xC0C9` returns 1 only when *both* of those bits are set, `0xC10C`
leaves R7 zero unless both are set.

No `C10C.asm` or `C10C.c` is committed — the export is deferred to a
pinned-toolchain run, §8.1 — so the twelve bytes above, read at file offset
`0x0C10C`, are the statement of the result. For whoever runs that export: the
R7 return is the thing to check, because the decompiler drops it in the sibling
rows that already say so in their own comments, `0xC0C9` and `0xC0E7` both
decompiling to a bare `return;` with no assignment to R7 anywhere.

`0x3202` has **no row in `registers.yaml`**. Four annotations read it
(`0xC0B8`, `0xC0C9`, `0xC0DA`, `0xC0E7`), and the first three say in their own
comments that it has no row — `0xC0E7` records what it reads and says nothing
about the map. Giving it a row means correcting those three, which is why it is
a follow-up of its own and not a rider here — see §8.1.

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

> **Live counterexample, 2026-09-24 (issue #257).** `0x06C5` is in this row, and
> a suspend to S3 and resume loaded it with `0x05`. It was `0x00` before and
> `0x05` at the first sample after, and then counted down through the sweep
> (`../../evidence/ec-watch/2026-09-24-06c2-06db-suspend-linux.csv`). So it has
> a writer neither method found. That is the blind spot the next paragraphs
> name, now with one live instance. The row is left as the search measured it,
> because it records what the search can see.

16 of those 17 are countdowns (`0x0621` is a side-effect target), and for
several of them the sweep is the *only* thing in the firmware that touches the
byte at all: `0x0635`, `0x0638`, `0x0639`, `0x063A`, `0x06D6`, `0x06F3`,
`0x0706`, `0x0843` and `0x0844` have exactly one EC-side site each, and it is
the decrement.

**This is "not found by this method", and the blind spot is named rather than
assumed away.** Neither method can see a write reached through a computed DPTR,
a register-indirect access, or a table. `0xC10C` was named here as the prime
suspect for the seventeen on the grounds that it was the one routine in the block
that is not exported, and a spelling search over the decompiled tree therefore
could not reach it at all. **That reason is now wrong**: `0xC10C` decodes to a
thunk on `0xC0C9` and so reads `0x3202` (§4), one of seventeen bytes rather
than one of the eight the sweep walks. It still has no committed listing, so
the export gap is real, but it was never what made `0xC10C` a suspect: the
suspect was the wrong inference from the census, and the blind spot itself is
unchanged and is the real reason this search cannot close.

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

### 6a. The `==` direction-classifier defect: measured, and fixed since #178

`xdata-registers.csv` and `xdata-clusters.csv` are **not** regenerated here and
are **not** read as evidence. §2a is the reason, and now it is the whole of it:
this section used to give a second reason — that the direction classifier was
wrong — and that reason was withdrawn when the classifier was fixed. It is no
longer a reason to distrust the census.

**The defect.** `store_target()` decides an occurrence is a store by testing
`stripped.startswith(a) for a in ASSIGN`, and `ASSIGN`
(`ec/tools/xdata_register_map.py:243`) contains `"="` — so `"== 0x12"
.startswith("=")` is true, and every `==` in the tree was counted as a write.
The rejection is at `ec/tools/xdata_register_map.py:939`, inside
`store_target()` (`:916`), with the comment above it recording 838 occurrences
against two dereference stores. It landed in issue #178, and
`xdata-register-map.md` §4.3 is the retraction written at the time.

**The committed census is post-guard, and is exactly what the committed tool
produces.** Regenerating with no arguments reproduces every `read`, `write`,
`refs` and `addrs` cell of both CSVs: 0 differences across 1,171 register rows
and 430 cluster rows. The tree's own `BUCKET_TOTALS` oracle
(`xdata_register_map.py:668`) reads `read 8341 write 3195 read+write 2482
passed-to-call 534 address-taken 267`, which are the post-guard figures.

**The effect**, from running the committed tool twice — once as it stands, and
once with `--no-eq-guard`, which re-runs the census with the `==` rejection
turned off and is therefore the pre-#178 classifier measured on today's tree,
not a number remembered from 2026-09-23:

| | guard removed (`--no-eq-guard`) | as committed today |
|---|---:|---:|
| main-EC `write` references (1,014 addresses, 13,123 refs) | 3,577 | 2,835 |
| main-EC `read` references | 6,792 | 7,538 |
| PD-image `write` references (109 addresses, 604 refs) | 193 | 142 |
| references in `write` for the 48 addresses in both images | 258 | 218 |
| **references leaving `write`, all three programs** | — | **833** |
| **addresses whose `write` column changes** | — | **210 of 1,171** |
| `0x08A8` read / write | 84 / 44 | **126 / 2** |
| `0x0843` read / write | 84 / 42 | **126 / 0** |
| main-EC clusters at threshold 0.50 | 388 | 380 |
| **`main-ec-002` (this block)** | **43 addresses, 4,966 refs** | **43 addresses, 4,966 refs** |

**What the guard does and does not change.** It moves references *between*
direction buckets and out of none of them: **0 of 1,171 addresses have a
different `refs` total** either way. Every row of §2a's 43-address table is
therefore guard-invariant, and that is the direct confirmation that §2a's
42-fold double count is a wholly separate defect — the guard neither creates
nor repairs it.

**The last row is the one this section previously got wrong, and the wrong
version is kept above rather than deleted.** This block used to close by
arguing that the cluster this issue is scoped to "does not survive the
classifier fix in its current shape", reporting `main-ec-002` going from 43
addresses / 4,966 references to 44 / 248. **That is wrong, and the reason is
that `main-ec-NNN` is a rank slot and not an identity** — clusters are ordered
by size, then references, then lowest address
(`xdata_register_map.py:150`). Re-measured, `main-ec-002` holds the same 43
addresses with the same 4,966 references both with and without the guard, with
membership identical address for address, and the two runs agree on the
`refs` of every one of the 1,171 rows. The cluster survives the fix intact.
What the guard does move is the *number* of main-EC clusters (388 → 380),
because it shrinks writer sets everywhere, and it moves the sweep's own
direction buckets — which is the `0x08A8` and `0x0843` rows above. No 44-address
/ 248-reference cluster exists in either generation, and none did when this was
first written either: the 44/248 pair belonged to a different membership that
merely held rank slot 2 at the time, which is the same hazard the correction
at the top of this file records for the ids themselves.

```console
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-registers /tmp/before-registers.csv \
    --out-clusters  /tmp/before-clusters.csv                  # the pre-#178 classifier
$ python3 - <<'EOF'
import csv
u = {r['addr']: r for r in csv.DictReader(open('/tmp/before-registers.csv'))}
f = {r['addr']: r for r in csv.DictReader(open('ec/annotations/xdata-registers.csv'))}
print("references leaving 'write':",
      sum(int(u[k]['write']) - int(f[k]['write']) for k in u))
print("addresses whose 'write' changes:",
      sum(1 for k in u if u[k]['write'] != f[k]['write']), "of", len(u))
print("addresses whose 'refs' changes:",
      sum(1 for k in u if u[k]['refs'] != f[k]['refs']), "of", len(u))
EOF
references leaving 'write': 833
addresses whose 'write' changes: 210 of 1171
addresses whose 'refs' changes: 0 of 1171
```

`--self-test` and `--check` are **not** part of that reproduction and neither is
green today: both exit 1 on `main`, on the naming drift described below. What
they do still establish is the part this section rests on — `--self-test`'s
`BUCKET_TOTALS` oracle and its corpus-wide direction invariant both pass, and a
default regeneration differs from the committed CSVs in **no** `read`, `write`,
`refs` or `addrs` cell. Neither mode is in `agent-gates.sh`'s tool list, so that
redness does not currently fail the build; that is a gap in the gate, not a
green light, and closing it belongs with whoever regenerates the CSVs.

**The reproduction this replaces was a no-op, and the reason it was is worth
keeping.** It copied the tool and patched a *second* `==` guard in, which the
committed file has had since #178, so its two censuses came out byte-identical
and it compared the tool against itself. A commit pointer is not a usable
recipe either — `git log --oneline -S 'startswith("==")' -- ec/tools/xdata_register_map.py`
reaches **two commits on `origin/main`**: #206, which is itself the commit that
added the guard, and #302, whose tree-wide invariant added two more occurrences
of the same string (three on this branch, once this issue's own docstring
sentence is in the tree). Neither is the pre-#178 classifier, which appears only
at #206's parent — a revision the search does not name — so `--no-eq-guard` was
added instead, and the tool's self-test pins that it flips exactly the `==` lines
of `CLASSIFIER_SHAPE` and nothing else. The numbers were right; the recipe was
the defect.

**A note on the figures above and on `--self-test`.** The left-hand column is
the pre-#178 classifier run on the current tree, so it is a live measurement;
the *earlier* version of this table quoted 3,569 / 2,827, 6,773 / 7,519,
257 / 217, 210 of 1,172 and 384 / 376, measured when the decompiled tree was
smaller. Those have drifted with the tree and are superseded by the numbers
above, which are the ones `--no-eq-guard` produces. Separately, `--self-test`
and `--check` are **red on `main` at the time of writing, for an unrelated
reason**: issue #504 added 9 `XDATA_` symbol rows to `xdata-symbols.csv` and
named 3 previously unnamed functions in `ghidra-functions.csv` (`bank1:0xE2D3`,
`0x9CE8`, `0x9D53`), neither of which regenerated the census, so the `name` /
`functions` / `shared_functions` / `named_addrs` columns drift on 32 register
rows and 6 cluster rows (`name` on 9 register rows, `functions` on 29, 6 in
both; `shared_functions` on 5 cluster rows, `named_addrs` on 3, 6 in the
union). Every direction and membership column still matches — `read`, `write`,
`read+write`, `refs`, `size`, `addrs` and `spelled_as` among them — which is
the 0-difference result above. That
redness is a naming backlog, not a direction-classifier problem, and it is not
fixed here.

The issue's own "`0x08A8` is recorded as 84 reads / 44 writes / 42 read+write,
and 42 of its comparisons are `==`" is a second, independent misreading:
`xdata-register-map.md` §4.1 defines the `read+write` column as "an `=` target
whose right-hand side names the same address", so `0x08A8`'s 42 are 42
read-modify-writes, not 42 equality tests — and they are 42 on both sides of
the guard above. Per §2a all 42 of them come from the 42 overlapping exports.
The wrong reading is left in the issue, not silently dropped.

**Nothing in §3 or §4 needs a census column.** Every count in this file comes
from the `.c`, the `.asm` and the image.

## 7. The read-only step, for a human with the machine

> **Run in part, 2026-09-24.** Steps 1 and 2 were run on Linux (no vendor
> service), with a faster sampler than the loop below:
> `../tools/ec_timer_capture.py`. Step 3 cannot run as written because `0x1664`
> and `0x3202` are outside the ECMG host window. A perturbation arm (AC, the Fn
> key, the lid, a suspend and resume) was also run. The Windows arm was not.
> Commands, captures and result: `../../docs/hardware-tests/xdata-06c2-06db-sweep.md`.
> The sentence below is the procedure as first written, left as it was.

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

# 3. Both predicate gates against the countdown they guard, and 0x06D9 itself.
$ python3 ec/tools/ecmem.py read 0x1664 0x3202 0x06d9
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
3. **Both gate bytes against `0x06D9`.** §4 says `0x06D9` only counts down while
   both forwarders return zero, which now names two bytes and three bits between
   them: bit 0 of `0x1664`, and bits 1 and 2 of `0x3202`. Sample all three
   together — `read 0x1664 0x3202 0x06d9` — so the two gates are not separated in
   the record. If `0x06D9` holds still whenever `0x1664` bit 0 is set, the
   `0xC1E7` gate is confirmed behaviourally; the same for either `0x3202` bit and
   the `0xC10C` gate. If `0x06D9` counts down with all three set, both gate
   annotations mean something other than what they say and are wrong. The
   reading is static: nothing here has watched a single countdown step, and no
   hardware was involved in producing this list.

Run 2 with the vendor Control Center started and stopped, as `ec_watch.py`'s
own docstring asks: a byte that only moves while the service runs is the vendor
touching it, not the EC's sweep.

## 8. The open questions

1. ~~**`0xC10C` has no exported function in any program**, and `0x06D9`'s
   countdown hangs off it. This is the highest-value item on the block and it
   needs a function seed — which needs `--mode rebuild-project`, so it wants a
   branch of its own.~~ **Half closed by #255, and the half that is left is the
   export, not the reading.** §4 has the body, decoded by hand from the twelve
   bytes at file `0x0C10C`: seven instructions, a thunk on `0xC0C9`. That was
   the highest-value part — what it reads is `0x3202`, not a byte in this block,
   and that opens the next item. What is *not* done is the listing. Seeding it
   needs no `--mode rebuild-project` (the default export-only mode seeds into
   its copy of the project, a one-line CSV diff rather than a 7 MB database
   one), but committing the export needs a row in `ec/ghidra/reassembly.csv`,
   and that report is single-writer: adding one row without rewriting the other
   2,707 requires the pinned assembler `ec/ghidra/README.md` names, which a
   runner does not have. So the seed row and the export are deliberately *not*
   on this branch — a red `verify_reassembly.py --check` is not a way to land
   them. What the runner *did* establish is the weaker half, and it is worth
   being exact about which half that is: the twelve bytes at file `0x0C10C` are
   `12 c0 c9 ef 60 03 7f 01 22 7f 00 22` in the image, and they disassemble as
   the seven instructions quoted in §4. That is the firmware side of the claim
   and it is reproducible from the committed image. **The independent
   re-encode has not been run** — `verify_reassembly` refuses outright when
   `sdas8051` is absent rather than reporting a partial result, so the earlier
   wording of this item (`match`, 7 of 7 instructions re-encoded) described a
   run that did not happen, and it is withdrawn here. Whoever runs the pinned
   `--report` is the first to have that number.
2. **`0x3202` has no `registers.yaml` row**, and it is the register the `0x06D9`
   gate actually reads. Four existing annotations read it (`0xC0B8`, `0xC0C9`,
   `0xC0DA`, `0xC0E7`), and the first three say in their own comments that it has
   none, so the row is three comment corrections as well — and
   `build_ec_decompile.py:stale_no_entry_claims` fails the build the moment the
   row lands and they do not. Deliberately not a rider on #255. With four read
   sites and no writer found by this method, its value space is unestablished, so
   a row would claim nothing beyond the address.
3. **The reload path for the seventeen in §5.** The blind spot is named rather
   than bounded: a computed DPTR, a register-indirect access and a table are
   all invisible to both methods here. `0xC10C` used to be named here as a
   suspect on the separate grounds that it was unexported. It still is (item 1
   is that export), but its twelve bytes, decoded by hand in §4, are a thunk on
   `0xC0C9` that reads `0x3202`, so that reason is gone (§5).
4. ~~**The direction-classifier fix** at `ec/tools/xdata_register_map.py:277`,
   measured in §6a: 833 references out of `write`, 210 addresses, and
   `main-ec-002` (this block) itself reshaped. It wants its own diff with its own
   before/after census, and it should be read together with the de-duplication
   question below or the new numbers will be wrong in the other direction.~~
   **Closed — the diff it asked for landed in issue #178**, and the guard is at
   `xdata_register_map.py:939`. Two things in the withdrawn text were wrong
   besides the line citation: `:277` was never the classifier's location, and
   `main-ec-002` does **not** reshape — it keeps the same 43 addresses and the
   same 4,966 references with and without the guard, because the guard moves
   references between direction buckets and out of none of them (0 of 1,171
   `refs` totals change). §6a carries the corrected measurement and
   `--no-eq-guard` re-derives it. What is genuinely still open is item 5.
5. **The census's 42-fold double count** (§2a). Nothing in
   `xdata_register_map.py` knows that 42 exports are one routine, and until
   something does, every reference count for a byte this sweep touches is
   inflated by roughly 42× — which is most of what made this cluster look
   like the firmware's busiest.
6. ~~**`0x1664` is read as a gate by the block and has no `registers.yaml`
   row.** One site, one bit, one caller — but the caller is the only countdown
   in the block whose rate is not its own value.~~ **Closed by #255**, in the
   other direction from what the item expected: it is **three** sites, not one.
   `0xC1DA` and `0xC1F4` sit in unexported gaps, so the decompiled-C token
   census saw only `0xC1E7` and understated the address three-to-one. The row
   carries 3/3/0 and `check_register_counts.py` holds it there. If that is
   systematic, the `read`/`refs` columns understate any address whose readers
   sit in unexported gaps — a census question distinct from §2a, and open.
7. **The 42 wrong function boundaries**, if anyone wants them fixed rather than
   documented. `build_ec_decompile.py --mode rebuild-project` writes the 7 MB
   database, and two branches that both rebuild one cannot merge.
8. **`0x0440`'s value.** 43 read sites, no direct `MOV DPTR` writer, and this
   block reads it three times. What 43 places in the firmware consult it for is
   still open (`xdata-0400-045f.md` §11 carries the same question from the
   other side of the page).
