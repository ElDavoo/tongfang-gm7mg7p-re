# The indirect XDATA scan: `movx @Ri` sites, and the answer for `0x07B9` and `0x07D0` (issue #34)

Issue #34 pointed at a specific hole in this repository's own reasoning.
`docs/findings.md` §5 says the static route to `0x07D0` is exhausted on the
firmware side, and that is true *for direct `MOV DPTR,#imm16` references* --
the only thing any tool in `ec/tools/` could see. `0x07B9` is the standing
counter-example to reading such an exhaustion as an absence: Windows writes
that byte and the EC honours it, with zero direct references anywhere in the
image, which is what §4c had to retract. On an 8051 the other XDATA addressing
mode is `movx a,@r0` / `movx @r1,a`, one byte each, with the page in the `P2`
SFR and the low byte in a register -- and nobody had looked for them.

**Both of the issue's questions, answered.** The main EC image does **not**
reach page `0x07` by this method, anywhere (§4). No resolvable site lands on
`0x07B9` or on `0x07D0`, because no site resolves to any address at all (§2).
That is a result about the *form* the issue asked about and not a finding about
`0x07D0`; §5 is the long list of what it is not.

**Nothing was observed, and nothing changed.** No register `status:` moved --
`DO-NOT-WRITE-BLIND` on `0x07D0` stands, and `registers.yaml`'s `0x07B9` and
`0x07D0` rows are not edited. No hardware and no Windows machine was involved,
no register was read back, and no sentence on this page is a claim about EC
behaviour. Every number re-derives from the committed image with the tool named
in §1.

## 1. How to re-derive all of it

```console
$ cd ec/tools
$ python3 find_indirect_xdata.py ../firmware/GMxMGxx_11.800
$ python3 find_indirect_xdata.py ../firmware/GMxMGxx_11.800 --csv \
        > ../annotations/indirect-xdata-sites.csv
$ python3 find_indirect_xdata.py ../firmware/GMxMGxx_11.800 --check
$ python3 find_indirect_xdata.py ../firmware/GMxMGxx_11.800 --page 0x07
$ python3 -m unittest test_find_indirect_xdata.py
```

`--check` diffs the committed table byte for byte against a fresh generation
and needs no Ghidra, no network and no hardware; the suite asserts the same
thing end to end, so a CSV that stopped describing the image would fail a test
rather than a reader. Neither the suite nor the `--check` is wired into
`.github/scripts/agent-gates.sh`: that file is copied from
[`ElDavoo/agent-pipeline`](https://github.com/ElDavoo/agent-pipeline) and
registering a gate there is an upstream change and a re-copy, not an edit in
this repository. Until that is made, both are run by hand, and this page does
not imply CI runs them.

**Why a new tool and not a mode of `trace_xdata_refs.py`.** That tool is a
shared file with four committed tables hanging off its `--check`, and
CLAUDE.md's "new work goes in new files" settles the placement. It still owns
the region map: `find_indirect_xdata.py` imports `REGIONS`, `region_of`,
`runtime_addr` and `PD_MARKER` from it, so there is one definition of where the
PD image starts and one refusal (`unknown` rather than `pd-image`) when its
marker is absent.

## 2. The population, and what resolved

**A byte scan over-counts 8x, and both counts are printed.** 0xE2, 0xE3, 0xF2
and 0xF3 are common *operand* bytes inside `mov dptr,#imm16`, `jnb bit,rel` and
`cjne`, so most of what a byte scan finds is somebody's immediate:

| | raw byte(s) | anchored site(s) |
|---|---|---|
| `common` | 123 | 28 |
| `bank0` | 128 | 5 |
| `bank1` | 218 | 11 |
| **main EC** | **469** | **44** |
| **PD image** | **285** | **47** |

754 raw against 91 anchored. The two programs are never added together: a
`movx @Ri` in the PD image reaches a different program's XDATA byte, which is
`lightbar-bat-flow.md` §2's mistake and `trace_xdata_refs.py`'s docstring's
first point. The site list is
[`indirect-xdata-sites.csv`](indirect-xdata-sites.csv), one row per site, with
the window's own decode in the last column so a reader can re-derive the
resolution cell from the row.

**Zero of the 91 resolve, and the reason is the same one every time.** All 91
report `no P2 write in the window`, and all 91 windows ended at
`window exhausted (24 bytes)` rather than at the start of the region. Two of
the 91 do have a literal `mov rN,#imm` behind them -- `mov r0,#0x1C` before the
`movx a,@r0` at file `0x16A15` and `mov r0,#0x28` before the one at `0x16A83`,
both in `bank1` -- and no site has a `P2` write behind it at all, so there is
no page to pair a low byte with.

**The framing is not the reason.** All 91 sites have `frame_onto` > 0: at least
one nearby anchor's linear decode lands exactly on each of them, and the
`frame_onto`/`frame_over` pair is in the table beside every row. That is
`disasm8051.py`'s evidence and it is a lower bound on a site's being real
rather than a proof of it -- `converges_from()`'s own docstring says to read the
pair and not either half -- but a population of 91 sites that no decode walks
onto would have been a different claim.

## 3. The `P2` zero, and the control that makes it citable

`mov p2,#imm` is `0x75 0xA0 <imm>`. It occurs **0 times** in the whole 256 KiB
image. A zero is only a finding next to evidence that the query works, so the
summary prints the identical two-byte-plus-immediate query for six other
byte-addressed SFRs over the same file, on every run:

| encoding | occurrences |
|---|---|
| `mov b,#imm` | 529 |
| `mov acc,#imm` | 11 |
| `mov psw,#imm` | 10 |
| `mov p1,#imm` | 4 |
| `mov sp,#imm` | 3 |
| `mov p0,#imm` | 1 |
| **`mov p2,#imm`** | **0** |

Three orders of magnitude between `B` and `P2` through one query is what makes
this a statement about the *form* in this image and not about the scan. The
`MOV DPTR,#imm16` idiom the other two tools look for is everywhere in the
image; the `P2` half of the indirect idiom is not in it at all.

**The tool does not stop at the literal.** An 8051 has 19 encodings that write
`0xA0`-`0xA7`, and only `mov p2,#imm` supplies a page this tool can name; the
other 18 make the half `unresolved` and say which one defeated it. Four of the
19 occur in this image, and none of the four is the literal:

| encoding | anchored occurrences | where |
|---|---|---|
| `mov p2,#imm` | 0 | -- |
| `mov p2,register` | 12 | all in `common`, and all of them probably not a `P2` write -- §3a |
| `mov p2.x,carry` | 2 | `bank0` `0x9287`, `bank1` `0x14C8F` |
| `inc p2` | 1 | `bank0` `0xA35E` |
| `mov p2,direct` | 1 | `bank1` `0x16CA3` |

The 15 that do not occur are not found by this method, which is not the same
as their being absent from the 8051. The nineteenth, `xch a,direct` (`0xC5`),
was missing from the tool's table until #1169 was reviewed: it is in
`ec/tools/pd_index_geometry.py`'s `DIRECT_DST_OPS`, and a table assembled from
`sdcc`'s assembler alone does not reach it. It occurs zero times here, so the
census above is unchanged by adding it -- the count that moved is the
completeness guarantee, not the measurement.

### 3a. The 12 `mov p2,register` are a data table the walk decoded as code

All twelve are the same two bytes, `8c a0`, at `0x05C9A` .. `0x0608A` on a
0x30-byte grid (steps of 0x30 and 0x90, i.e. one and three records). The bytes
around them are not an instruction stream:

```console
$ python3 -c "d=open('../firmware/GMxMGxx_11.800','rb').read(); print(d[0x5C9A:0x5CCA].hex(' '))"
8c a0 b4 b4 b4 b4 b4 b4 36 3a 3d 3f 40 42 44 4b 50 55 ff ff ff ff ff ff 00 30 32 3c 3e 3f 41 43 46 4f 52 ff ff ff ff ff 00 3c 3c 46 5a 5a 64 6e
```

One 48-byte record is `8c a0`, six `0xB4` filler bytes, a nine-byte ascending
run, six `0xFF`, a `0x00` separator, an eleven-byte run, five more `0xFF`, a
second `0x00` and a final seven-byte run. `disasm8051.py` decodes the filler as
two `cjne a,#0xb4` and the byte after it as `db 0x36`, which is what a table of
a repeated byte decodes as rather than a plausible instruction sequence. The
structure continues to the left of `0x05C9A` with records whose first two
bytes are something else -- so the table is wider than the twelve records whose
head happens to spell an instruction. `data_regions.yaml` lists no span
covering `0x05C9A`-`0x060B9`.

So the honest reading is that the anchored walk reached each record boundary
and decoded the record's first two bytes as `mov p2,r4`, twelve times. **These
are almost certainly not `P2` writes**, and the census row above is reported
because reporting it is what the method produced, not because the method is
right about it. This is the anchored pass's framing limitation landing on a
real case rather than a hypothetical one, and it is worth holding in mind when
reading the other three rows: `mov p2,direct`, `inc p2` and `mov p2.x,carry`
are single sites and are not independently corroborated either way.

**One of those 18 rows was wrong in the first cut of this table, and the tool's
own output is what found it.** `0x40` is `jc rel` -- and `0x42` is
`orl direct,A` -- so a range spanning `0x40`-`0x43` reads every `jc` whose
target byte falls in `0xA0`-`0xA7` as a write to `P2`, and `P2` is the page an
indirect `movx @Ri` reads, so the false positive lands on exactly the sites
this tool exists to explain. The first `--csv` run reported two `movx @Ri` sites
whose last `P2` write was `orl p2,#imm-or-a`, and the `window` cell on the same
two rows rendered those bytes as `jc +0xa2` and `jc +0x98`. The three logic rows
start at `0x02` into their decade, and
[`../tools/test_find_indirect_xdata.py`](../tools/test_find_indirect_xdata.py)
pins the collision in both directions. The whole table is transcribed from
`sdas8051`'s own listing rather than recalled, which is how that came out
right the second time.

## 4. The two addresses the issue named

`--page 0x07` is the mode that answers the issue's question directly, per
image, and it exits non-zero when the main EC reaches the page nowhere:

```console
$ python3 find_indirect_xdata.py ../firmware/GMxMGxx_11.800 --page 0x07
page 0x07, by the sites this tool can resolve:

  common    0  -- not reached by any resolvable site
  bank0     0  -- not reached by any resolvable site
  bank1     0  -- not reached by any resolvable site
  pd-image  0  -- not reached by any resolvable site

So the main EC reaches page 0x07 by this method nowhere, and the PD
image's indirect XDATA is a different program's byte either way.
```

- **`0x07B9`**: no site resolves onto it, and no site resolves onto anything.
  The direct route was already empty by `docs/findings.md` §4c's standard and
  the indirect route is empty by this page's. The blind spot the issue asked to
  narrow has narrowed, and it narrowed to a fact about the *encoding*: the
  main EC has 44 anchored `movx @Ri` sites and not one of them has a `P2` write
  within 24 bytes behind it.
- **`0x07D0`**: the same, with `DO-NOT-WRITE-BLIND` unchanged and the
  `unknown-not-absent-DO-NOT-WRITE-BLIND` status unchanged. Nothing here
  re-grades it, and nothing here could have: a static scan is not a behaviour.

## 5. What this does not establish

This is a result about four opcodes and a 24-byte window. The following are
unexamined by it, and each is a place a reader could otherwise read a
conclusion that is not in it:

- **It is not "`0x07D0` has no EC-side writer."** The PD image's 47 sites are
  another program's bytes, and they are excluded above for exactly that reason
  -- their exclusion is not evidence about the main EC. And a byte written from
  Windows or from the DSDT, which §4o of the 0x07D0 entry already records, is
  not a byte the firmware has to write.
- **Register- and table-supplied `P2` are only partly covered.** The tool names
  a `mov p2,register` when the anchored walk reaches one and refuses to turn it
  into a page, but what the register holds is not modelled, and -- as §3a
  shows -- the twelve this image yields are a data table rather than twelve
  real writes, so the row count is a statement about the walk and not about
  the firmware.
- **`P2` set across a call boundary stays a blind spot**, as the issue said it
  would. A `lcall` into a routine that sets `P2` is not followed, and the
  window stops at whatever the linear decode reaches.
- **The low half is a literal load, not a register value.** The tool records
  the last `mov r0,#imm` / `mov r1,#imm` it can see; it does not model the
  instructions that modify a register afterwards, so a resolved row would be a
  statement about a load, not about a value. On this image it never comes to
  that, because no row has a `P2` half.
- **`mov @Ri,#data` (0x76/0x77) is not in this population.** It writes the
  same XDATA byte through the same `P2` half and the issue asked for `movx`
  specifically. It is the natural next scan and the tool's docstring says so.
- **`@dptr` walks are a different population.** `inc_dptr_sites.py` owns those
  for the direct form and nothing here touches them.
- **The anchored pass is one linear decode per region.** It re-syncs a byte at
  a time at a region's tail and nothing else re-frames anything, so one
  mis-framing shifts every site behind it. `frame_onto`/`frame_over` are the
  evidence about that and, as §2 says, a lower bound.
- **Nothing was run on hardware or on Windows.** No register was read back, and
  a static scan is not a behaviour.

## 6. What it opens

- **The 44 main-EC sites are unclassified.** They are anchored, they are
  spread across `common` (28), `bank1` (11) and `bank0` (5), and nothing
  beyond the framing columns says what any of them does. A caller table, a
  `movc`-style lookup and a genuine register access are all still one row each.
  The `window` column on each row is the raw material for telling them apart
  and nothing has been read out of it yet.
- **The table at `0x05C9A` is worth a `data-regions.yaml` row.** §3a
  establishes that it is a data structure and that the anchored pass decodes
  its record heads as instructions. It is unlisted, so every future scan in
  this repository will walk through it, and any of them that counts a decoded
  instruction there is counting a table. What the records hold -- a
  48-byte frame of `0xB4` filler, `0xFF` padding and three ascending byte
  runs, none of them obviously a register map -- is the natural next question.
- **The two `mov @Ri,#data` opcodes are the next scan.** 0x76 and 0x77 reach
  the same XDATA byte through the same `P2` half, and §5 says why they are not
  in this population. Widening the tool to them is a scope decision and the
  natural one next.
- **The 24-byte window is a choice with a number attached.** `--window` moves
  it and the cell names the budget that ran out, and all 91 of the committed
  sites end at that budget rather than at a region boundary. A wider run would
  say whether the two `mov r0,#imm` sites at `0x16A15` and `0x16A83` pick up a
  `P2` write further back; this run does not claim the answer either way.
