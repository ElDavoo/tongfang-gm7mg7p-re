# The 54 image-wide CODE-pointer sites, written down as a regenerable table, and what the list is not

(2026-10-02, issue #41. Static byte scan of one committed image through
`ec/tools/code_pointer_sites.py` over `ec/firmware/GMxMGxx_11.800`, with a
sample of every region/class pair cross-read against `r2 -a 8051`. No capture
opened, no EC, no hardware, no Windows, no `registers.yaml` row touched.)

[`static-refs-audit.md`](../../ec/annotations/static-refs-audit.md) §5.1
reports the aggregate — "image-wide there are 54 such sites across 48
addresses, none of them an address in `registers.yaml`" — and gives one worked
example. The 48 addresses themselves were not written down anywhere, so the
next person who needed them re-derived them, and a re-derivation is only as
good as the walk that produced it that day. **This is the list, regenerated
from the committed image by a command**: one row per *site* in
`ec/annotations/code-pointer-sites.csv`, and `code_pointer_sites.py --check`
holds that file to the bytes the image holds today.

The point is not the 54. The point is that the number §5.1 carries is now
traceable to a file rather than to prose, so §5.1's null can be re-run instead
of re-argued — which is what the two open issues that are about to add
addresses need, and what makes the list usable as a pre-flight check rather
than as a thing to re-derive.

## 1. Reproducing it

```console
$ python3 ec/tools/code_pointer_sites.py --csv > ec/annotations/code-pointer-sites.csv
$ python3 ec/tools/code_pointer_sites.py --check
ec/annotations/code-pointer-sites.csv: this run reproduces it byte for byte (55 lines)
$ python3 ec/tools/code_pointer_sites.py
54 CODE-pointer site(s) across 48 address(es): jmp @a+dptr=18  movc (CODE pointer)=36
  by region: bank0=10  bank1=31  common=8  pd-image=5
  more than one site: 0x63BE x3  0x63D7 x3  0xF13F x2  0xF45B x2  (this is why sites and addresses are different numbers)
  jmp window shapes: x15 `mov r0,a ; add a,r0 ; add a,r0 ; jmp @a+dptr`  x3 `jmp @a+dptr`
  data-regions.yaml overlap: 0 of 54 site(s) fall inside a listed span
```

The classification is `register_ref_table.bucket()` over
`trace_xdata_refs.classify()` over `trace_xdata_refs.walk()` — the same three
functions `static-refs-audit.md` §5's table is built from, imported rather than
re-implemented, so the vocabulary cannot drift between that table and this one.
The two classes are looked up in `register_ref_table.CLASSES` by the column
they are printed under (`movc`, `jmp`) rather than spelled out, so a rename
there moves this tool with it instead of leaving it filtering on a name nothing
produces.

The scan is every `0x90` in the image rather than a per-address query,
because the address is what is being discovered: asking address by address
would need the list first. It is `trace_xdata_refs.sites_for()`'s byte scan
with the same `walk`/`classify`/`bucket` applied to what each `0x90` decodes.

**54 sites and 48 addresses are two numbers, not a contradiction.** Four
addresses carry more than one site — `0x63BE` and `0x63D7` three each,
`0xF13F` and `0xF45B` two each — so the table is per *site*. §5.1's worked
example is one of them: `0x63BE` is at `0xA6A4`, and it has siblings at
`0xA6B7` and `0xA6CC` that §5.1 did not name. The other three are new to this
write-up.

**Two of the numbers are not counts of anything this repository can change.**
The site total, the class split, the per-region split and the four repeated
addresses are a measurement over the committed firmware, and no edit to this
tree can move them. The re-run of §5.1's null in §3 below is a measurement
over `registers.yaml`, which is *not* one of those, and is reported that way.

## 2. The sample, cross-read in r2

One site per region/class pair that actually occurs, plus §5.1's two `movx`
controls. Every transcript is `make_bank_image.py` plus `r2 -a 8051`, the way
§5.1 does it, so these are an independent decoder's reading of the same bytes
the tool decoded. The `common` rows are read from a bank image because
`make_bank_image.py` copies the common area in verbatim, so its file offset and
its runtime address are the same number there.

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
$ python3 ec/tools/make_bank_image.py --pd ec/firmware/GMxMGxx_11.800 /tmp/pd.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x00cf; pd 4' /tmp/bank0.bin
            0x000000cf      906f39         mov dptr, #0x6f39
            0x000000d2      e4             clr a
            0x000000d3      7e01           mov r6, #0x01
            0x000000d5      93             movc a, @a+dptr
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x1051; pd 4' /tmp/bank0.bin
            0x00001051      901100         mov dptr, #0x1100
            0x00001054      73             jmp @a+dptr
            0x00001055      0a             inc r2
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9c89; pd 4' /tmp/bank0.bin
            0x00009c89      906234         mov dptr, #0x6234
            0x00009c8c      93             movc a, @a+dptr
            0x00009c8d      901807         mov dptr, #0x1807
            0x00009c90      f0             movx @dptr, a
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x85f9; pd 4' /tmp/bank1.bin
            0x000085f9      90f13f         mov dptr, #0xf13f
            0x000085fc      93             movc a, @a+dptr
            0x000085fd      901501         mov dptr, #0x1501
            0x00008600      f0             movx @dptr, a
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8a65; pd 5' /tmp/bank1.bin
            0x00008a65      908a45         mov dptr, #0x8a45
            0x00008a68      f8             mov r0, a
            0x00008a69      28             add a, r0
            0x00008a6a      28             add a, r0
            0x00008a6b      73             jmp @a+dptr
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x0561; pd 4' /tmp/pd.bin
            0x00000561      90df22         mov dptr, #0xdf22
            0x00000564      e4             clr a
            0x00000565      7e01           mov r6, #0x01
            0x00000567      93             movc a, @a+dptr
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x0ba7; pd 2' /tmp/pd.bin
            0x00000ba7      900b05         mov dptr, #0x0b05
            0x00000baa      73             jmp @a+dptr
```

`0x1051` is §5.1's own example and comes back unchanged, which is the point of
including it: the list reproduces a transcript that was taken by hand before
the list existed.

**The two controls, which is the direction the list has to be right in.**
`0x0741` at `bank0:0x879D` is one of §5.1's ten `r+w` rows and `0x07D0` at
`pd-image:0x3478` is the read `ec-0x07d0-sites.md` §4 decodes; neither is on
the list, and neither should be:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x879d; pd 4' /tmp/bank0.bin
            0x0000879d      900741         mov dptr, #0x0741
            0x000087a0      e0             movx a, @dptr
            0x000087a1      4420           orl a, #0x20
            0x000087a3      f0             movx @dptr, a
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x3478; pd 2' /tmp/pd.bin
            0x00003478      9007d0         mov dptr, #0x07d0
            0x0000347b      e0             movx a, @dptr
```

**The `0x9C89` and `0x85F9` transcripts are the calibration in one screen.**
Each is a CODE-pointer site with an ordinary XDATA write four bytes later —
`0x1807` and `0x1501` respectively — and **neither neighbour is on the list**,
which is correct: they are different sites with different addresses, and the
table buckets per site for exactly this reason. A reader who saw the two
`mov dptr` lines in one `pd 4` and read the row as "this address is a table"
would be wrong about the address next to it in the same listing.

## 3. §5.1's null, re-run over whatever `registers.yaml` holds today

```console
$ python3 ec/tools/code_pointer_sites.py --against-registers
217 address(es) in ec/annotations/registers.yaml, 0 of them on the CODE-pointer list
none. This is a statement about this method over this image: a
       site reached past a branch, or a `90 xx xx` that is an
       operand rather than an instruction, is not on the list and
       is not excluded by it.
```

§5.1's null was written over the 29 addresses `registers.yaml` held then. The
file has grown considerably since, and the null still holds: the intersection
of the 48 CODE-pointer addresses with **every** address in the current file is
empty. The figure above is that intersection re-derived at the moment of the
run, not a population written down anywhere — `registers.yaml` changes at
almost every landing change here, so a null pinned to a count would go stale
without anything turning red. `--against-registers 0xNNNN` answers it for one
address, which is the form the two open issues want:

```console
$ python3 ec/tools/code_pointer_sites.py --against-registers 0x63BE 0x0741
  0x0741  no CODE-pointer site (found by this method)
  0x63BE  ON THE LIST (found by this method)
```

Note the exit code is 0 either way. A non-empty intersection is a fact about
an address and not a failure of the tool, and the mode's whole job is to print
the sites behind one.

## 4. The `jmp` shape split, and what it is not

Of the 18 `jmp @a+dptr` sites, 15 share one decoded window and 3 carry a bare
`jmp @a+dptr`:

| window | sites | where |
|---|---:|---|
| `mov r0,a ; add a,r0 ; add a,r0 ; jmp @a+dptr` | 15 | all `bank1` |
| `jmp @a+dptr` | 3 | `common` `0x1051`, `common` `0x702C`, `pd-image` `0x0BA7` |

The scaled shape computes `base + 3 × A` and dispatches, which is a
three-byte-stride table; `0x8A45` is the worked example in §2's transcript. The
split falls exactly along the region boundary, which is a fact about where the
scaled form is emitted and not about the two kinds of table. **What any of
those tables holds is not answered here.** This is a record of an instruction
shape, taken from the same `classify()` decode every other column in the CSV
comes from, and reading a `movc`/`jmp` as evidence about a register is the
error `static-refs-audit.md` §5.1 exists to prevent.

## 5. Limits — what this list is not

- **It is a floor, and the floor belongs to the method, not to the image.**
  `walk()` is a linear best-effort decode over an 8-instruction window that
  stops at the first control-flow instruction, so a CODE pointer reached past
  a branch is invisible. The `90 xx xx` scan is also a byte scan and not an
  instruction-aligned one, so a hit can in principle be an operand. `0x1051`
  is a site the walk resolves; nothing here claims it resolves every one.
- **A hit is a flag, not a verdict.** It means *this address has at least one
  CODE-pointer site*. It does **not** mean a `static_refs` count for that
  address is bogus: an address can carry both a table site and real register
  access, and `0x9C89`'s neighbour `0x1807` in §2 is the same idea from the
  other side — a `static_refs` count is per address and the classification is
  per site, so the two are not in correspondence even in principle.
- **Not being on the list means "this method found no CODE pointer", never
  "absent".** `0x07B9` is the standing counter-example to reading a zero of
  this kind as an absence, and the caveat is the reason `--against-registers`
  prints its own sentence.
- **Nothing here was measured on hardware.** A `movc` is a statement about the
  opcode stream. No `status:` in `registers.yaml` moves because an address is
  on this list, and whether any of the 48 is *also* a live register is a
  separate question this change does not answer.
- **The data-region overlap is a label and is zero.** `data_regions.region_at()`
  is asked about every site, and none of them falls inside a span
  `data-regions.yaml` records as a table. That says no site of this scan
  coincides with a known phantom; it does not say these sites are therefore
  real instructions, and the tool refuses to filter on it either way
  (`refuse_filtering()`, the same rule `data_regions.py` keeps as a refusal).
- **A dump whose `0x20000` region is not the PD image is refused, not
  reported.** Without the `ITE8850-PD` marker `region_of()` calls that region
  `unknown`, the per-region split silently loses its `pd-image` row, and the
  result is a smaller scan that looks like a measurement.

## 6. What a follow-up would take

The list is the guard the DSDT sweep and the `uniwill-laptop` address work need
before a new `static_refs` count is read as evidence. It does not resolve
either of them, and nothing in it is a claim about what any of the 48
addresses is.

What it opens, and what this change deliberately did not do: a CODE pointer
reached past a branch is still invisible to it, so a stricter census needs a
`walk_flow_follow`-shaped second pass over the `none`-classified sites of the
whole image, the way
[`walk-flow-follow.md`](walk-flow-follow.md) did for the eleven `none` cells
§5 carried. That is a different population from this one and a different
claim, and it is a candidate for its own issue rather than a mode to bolt on
here.
