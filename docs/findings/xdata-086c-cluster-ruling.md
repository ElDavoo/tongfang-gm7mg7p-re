# `0x086C` enters `registers.yaml`, and the clustering recorded something real (issue #333)

The write-up for [issue
#333](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/333), which asked
for a `registers.yaml` entry for `0x086C` and then asked a sharper question:
either the `0x087x` override-source cluster boundary records something real —
in which case `0x086C` is the odd one out for a reason worth writing down — or
`0x086C` is misfiled. The answer is the first, and the issue's own reading of
the committed census is wrong in three places, so this file opens by saying so
before it rules.

**Nothing here is a hardware claim.** No register was read back and no laptop,
EC or Windows machine is involved; `docs/hardware-tests/level-block-0860-086e.md`
is still unrun, and its status banner still says so. Every figure below is a
static count over the committed image, the committed decompile, or a committed
annotation, and the commands that produce them are named in §6.

## 1. What the issue asserted, and what the committed tree says

The wrong readings are kept beside the corrections rather than replaced,
because `CLAUDE.md` asks for that shape and because a reader who has the issue
open needs to be able to see which of its claims survived.

1. **The issue places `0x086C` in `main-ec-001`; the census puts it in
   `main-ec-002`.** Its title and its second bullet both invert this. The
   committed row at `ec/annotations/xdata-registers.csv:829`, quoted whole:

   ```text
   0x086C,main-ec,DAT_EXTMEM,0x085F-0x086F,main-ec-002,26,12,12,0,0,2,7,6,9,no,,…
   ```

   Its `cluster_id` is `main-ec-002`, its `cluster_key` `kefb63d82f8c7`, and
   its hand name `mode-oem-init`; the `span_group` value is a label for the
   block of rows and says nothing about membership, which item 2 is about. Its
   immediate siblings at `0x086B` and `0x086E` are in `main-ec-004`, not
   `main-ec-002` either, so "all `symbol`, all `main-ec-002`" describes neither
   the row nor its neighbours.
2. **The `0x085F`-`0x086F` span is five clusters, not one.** `main-ec-002`
   holds `0x085F` and `0x086C`; `main-ec-004` holds `0x0860`, `0x0862`,
   `0x0865`-`0x086B`, `0x086D` and `0x086E`; `main-ec-106` holds `0x0863` and
   `0x0864`; `main-ec-341` holds `0x0861`; and `main-ec-049` holds `0x086F`.
   The issue's second bullet treats the span as one group, and reads
   `0x086C` as the single address outside the main one.
3. **The six `0x9D9B` override sources do not split three-and-three, and the
   issue's `xdata-clusters.csv:2` reading cites the wrong row for both
   clusters.** Committed membership: `0x0873` and `0x087B` are in
   `kefb63d82f8c7` / `main-ec-002`, 26 and 24 references across 10 functions
   each — the `0x95DD`/`0x96AD` OEM-override routines dominate both, which is
   the reason they land there; `0x0872`, `0x0874`, `0x087C` and `0x088A` are
   in `ka39cda99615f` / `main-ec-004`, 3-4 references across 2 functions each;
   `0x087A` is alone in `k25b651b0e92d` and `0x088B` alone in `kc7f3cfc3b1fa`.
   The issue's premise — that block one's sources and block two's sources fall
   on opposite sides of the boundary — does not hold for the committed census,
   and §2 is about what does.
4. **The `0x8942` BOOST citation is `docs/findings.md` §7 ("Power modes"), not
   §6.** §6 is firmware identity and UEFI variables, and says nothing about
   `0x8942`. `ec/annotations/manual-fan-ctrl-0751.md` carries the same §7
   reading, and `0x8942` indeed has no `ghidra-functions.csv` row of its own —
   the routine starts at `0x8931`, and `0x8942` is inside its first block.

The issue's *figures* for `0x086C` are right: 26 references, 12 read, 12
write, 2 address-taken, 7 readers, 6 writers, 9 functions. Every one of them
is a census figure over the decompiled tree, and the last is a count of C
files rather than of routines, which §2 is about. So is its observation that
`0x086B` is 22/12/8 across 5 and `0x086E` is 7/1/3 across 2.

## 2. The ruling: `0x086C` is not misfiled

**The clustering recorded something real, and the co-occurrence is one
routine, not three.** Read in machine code, `0x085F` and `0x086C` share
exactly one routine — `bank0:0x8931`
`gate_0751_0741_blocks_then_tail_jump_8c46`, the fan-boost gate, which reads
`0x085F` at `0x8949` and `0x8999` and `0x086C` at `0x8961`/`0x896A`/`0x896F`
(`ec/decompiled/bank0/8931.asm:14,26,30,33,56`). That body is the gate the
cluster's hand name `mode-oem-init` points at, and one routine reading both
bytes is still a co-occurrence — which is all §4.2 of
`ec/annotations/xdata-register-map.md` claims a cluster is evidence about. The
ruling below needs one shared routine, not three.

**Why the census's `functions` column says three, and the machine code says
one.** That column is a count of **decompiled C files**, not of routines, and
`ec/tools/xdata_register_map.py:115` warns about exactly this ("A source count
is a count of files, and 42 files can be one routine"); `:225` says the same
of `refs`, which is "an upper bound on *distinct* references". Ghidra
**inlined** the `0x8931` body into its two callers, so both `.c` files spell
four `DAT_EXTMEM_086c` occurrences each that no instruction in either `.asm`
backs. `888D.asm:11,16,22,26` are all `ljmp 0x8931`, and `8749.asm:12` and
`8749.asm:171` are `ljmp 0x8939` and `ljmp 0x893e` — jumps into the middle of
the same routine. `grep -c "0x86c" ec/decompiled/bank0/8749.asm` and
`.../888D.asm` both return `0`. The same inlining costs `0x085F` its third
file (`888D.c` names `DAT_EXTMEM_085f` four times, `8749.c` five, against one
instruction at `8749.asm:81` and two at `8931.asm:14,56`), and it costs
`0x086C` the `0xBC7B` and `0xD2BF` stubs, whose listings are a single
`mov DPTR` each and whose bodies are `0xBC7E` and `0xD2C2`
(`ghidra-functions.csv:296,481,482`). `0x8749` is still the one routine that
really does read `0x085F` outside the gate — but it reads `0x085F`, not
`0x086C`.

In machine code `0x086C`'s instruction sites are **five** functions, which is
what `ec/annotations/site-resolution.csv:716-729` already records and what the
census's nine does not: `0x8931` (3), `0x9CA6` (2, at `9CA6.asm:69,94`),
`0x9D9B` (7, the `0x9EE8`-`0x9F14` block), `0xBC7E` (1, at `0xBC7F`) and
`0xD2C2` (1, at `0xD2C3`).

`0x0873` and `0x087B` sit in the same cluster (`kefb63d82f8c7`,
`main-ec-002`, `mode-oem-init`) and carry 10 census functions each, the
`0x95DD` `fill_08xx_from_code_table` and `0x96AD`
`apply_oem_overrides_then_fill_08xx` pair among them. In machine code they
touch `0x086C` in one place as well — `0x9D9B`, at `9D9B.asm:41` and `:160`
beside the `0x086C` reads — and **not** in the OEM routines, which name
neither byte. The two heavily-read OEM-rewritten override sources therefore
join `0x086C` in the level-block routine, not in the OEM path; the cluster
still holds all four, and the working set is one routine per pair rather than
a mode tick, a mailbox handler and an OEM routine sharing one. `0x086B` and
`0x086E` are touched only by the `0x9CA6`/`0x9D9B`/`0xD091`/`0xD28E` set, they
have no such tie to `0x085F`, and they sit with the low-traffic override
sources in `ka39cda99615f` (`main-ec-004`, `level-block-086x`).

Two consequences are worth stating, because they are the point:

- **`0x085F` reaches the mode tick and the boost gate; `0x086B` and `0x086E`
  reach neither.** Cross-tabulating the *instruction sites* over the four
  addresses gives three pairs — `0x085F` with `0x086C` in `0x8931` alone, and
  `0x086B`/`0x086C`/`0x086E` together in `0x9CA6` and `0x9D9B` — with no
  routine touching `0x085F` and either other result. That is the census's
  three-pair shape with one routine in the first pair instead of three, so
  the correction costs the shape nothing. It is a **shape, not a meaning**:
  `CLAUDE.md` and
  `ec/annotations/xdata-register-map.md` §4.2 both say a cluster is evidence
  about which addresses co-occur, and a co-occurrence is not a mechanism. It
  says these four bytes are read together somewhere. It does not say the
  hardware treats them as one quantity, and nothing here should be quoted as
  though it did.
- **The `0x8942` BOOST arm compares `0x085F` against `0x3C` (60) and `0x086C`
  against `0x50` (80)**, then `CPU_TEMP` `0x043E` and `GPU_TEMP` `0x044F`
  against `0x46` (70 °C) — four comparisons in all, and only if every one of
  them holds does the block clear bit 6 of `0x0751` with the `anl A,#0xbf` at
  `0x898E` (`ec/decompiled/bank0/8931.asm:14-46`, cited from `docs/findings.md`
  §7). The byte compared and the byte the mode tick reads are in the same
  cluster, which is the connection worth recording. It is a co-occurrence and
  not a demonstrated mechanism: the block computes `0x086C` first, from
  `0xE389`'s return or from R7, and only then gates on it, so the record
  establishes the order and nothing about the units.

Cite the clusters by `cluster_key` and hand name, not by `main-ec-NNN` rank.
`check_cluster_citations.py`'s docstring is explicit that the rank is not an
identity — one change anywhere in the size-then-references ranking reshuffles
every id below it — and that the key and the name are the durable forms. The
membership claims in this section are held to `ec/annotations/xdata-clusters.csv`
by that tool, tree-wide, and none of them is among its disagreements.

**The tool is red on this branch, and saying so is the point.** It exits 1
with two disagreements, both at
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220` (`0x0464` and
`0x0465`, which that line names under the wrong ids) and both pre-date this
change — they are what it reports on `origin/main` too, at the same count.
A third was this change's to move: entering `0x086C` in `registers.yaml` put
it in `main-ec-002`'s `named_addrs`, which took the census figure from 31 to
32, and §5's "named inside" cell at `ec/annotations/xdata-register-map.md:2165`
was left at 27. It was already four stale before that, so the disagreement is
not a regression in kind; this change re-pins the cell to the census's 32,
which is the direction `check_cluster_citations.py` exists to hold, and the
report is down to the two pre-existing ones.

## 3. The new entry, and what it deliberately does not say

`XDATA_086C` in `ec/annotations/registers.yaml` sits between `XDATA_086B` and
`XDATA_086D`, and carries `status: present-untested` — the same status its two
siblings carry, and the status it keeps because **no live read of
`0x0860`-`0x086E` has happened on this board**. Its `static_refs` triple is
14/14/0, reproduced by `check_register_counts.py` from the image rather than
typed.

The note distinguishes the two count families, as `XDATA_0860`'s does: the
26/12/12/2/7/6/9 figures are `xdata_register_map.py`'s C-level occurrence
counts over the decompiled tree, and are **not** the `static_refs*` numbers,
which are the `MOV DPTR,#addr` opcode sites `scan_refs.py` reports.

It records the `0x50` (80) comparison and says in the same sentence that this
is the only site comparing this byte against a **constant** outside the
level-block computation, naming the one other comparison — `0x9CA6` against
`0x046B`, for the `0x046A`/`0x046B` sync — **which is a reason for caution
and not a unit**. It fixes no scale either: the three clamps are the same
`0x23`/`0x14`/`0x0F` that `0x086B` gets, so all four are numbers the firmware
compares against and nothing here fixes the scale. The `0x48`/`0x4C` seeds
`ec/annotations/xdata-086x-dispatch.md` §5 records are a statement about
`0x0865`, not about `0x086B`, and neither constant appears in
`ec/decompiled/bank0/9D9B.asm`.

`UNITS NOT DETERMINED` is carried over verbatim, and the name stays
`XDATA_086C`. The name is not earned: there is no live observation and no
second source for the units, and `0x086B`/`0x086E` are still `XDATA_086x` for
exactly the same reason. A constant that appears in a comparison is a number
the firmware compares against, which is a fact about the comparison and not
about the unit.

Three shapes the note records. §5's clamp table already carries the first —
the clamps are the same three `MANUAL_FAN_CTRL` (`0x0751`) values `0x086B`
gets (`0x23`, `0x14`, `0x0F`) but routed through `0xBC7B`/`0xBC7E` rather than
inline — and the paragraph under it already carries the `0x0A47`/`0x09EF`
publish described next. The one §5 does not describe is the `0xD2BF`/`0xD2C2`
staging/borrow shape: the pair copies the caller's DPTR byte in and returns it
masked with `0x7E`, reached with DPTR `0x1C00` or `0x1C35`.

## 4. An open question about `0xA73F`, not about this byte

Block two of `0x9D9B` — the one that produces `0x086C` — is the only one of the
three whose third clamp reads and writes `0x0A47`, compares it against
`0x09EF`, and on a change passes it to `0xA73F` with `R7 = 0xBC`
(`ec/decompiled/bank0/9D9B.asm:9F66-9FA0`). Blocks one and three have no such
publish. So **`0xA73F` is called with a command code this record does not
resolve**, and that is a question about the command-code table rather than about
`0x086C`.

It belongs to the `0xA73F` record, and it is written here so the follow-up pass
files it once against the command-code issue rather than opening a second issue
for the same question. This change opens and edits no tracker item.

> **Correction (2026-10-03, issue #1444), leaving the paragraph above as it was
> written.** The command-code table does not exist, so the question above has
> nothing to be filed against and the deferral it asked for was never needed.
> `0xA73F` does not select on the byte it is given: it pushes it as a payload
> into an eight-slot producer/consumer ring at XDATA `0x09F2`-`0x09F9`, indexed
> by a pair of cursors packed into `0x09F1`, and `0xBC` is one literal among
> the values published there. Nothing in the image branches on it, and
> `ec/annotations/task-call-table.csv` records no R7 value for any site. The
> paragraph above is right that the question is about `0xA73F` rather than about
> `0x086C`, and wrong to have called the byte a command code. The walk, with a
> citation per step, is `docs/findings/a73f-09f1-mailbox-payload.md`.

## 5. Coordination

- `bank0:0x8931` is a `0x086C` reader *and* one of the four functions issue #246
  claims for the `0x1804`/`0x1809` question. It already has a
  `ghidra-functions.csv` row (`:1867`). This change does not touch it;
  `0x086C`'s site at `0x8961`/`0x896A`/`0x896F` belongs on that row when #246
  lands. The site-resolution rows for it are already committed, so the address
  is in the census the join reads.
- Issue #250 covers `0x0862`/`0x086D` and is unaffected.
- `ec/annotations/ghidra-functions.csv:296`, the `0xBC7E` row, ended "0x086C
  has no entry in `ec/annotations/registers.yaml`". That clause is now false,
  and it carries a dated correction in the same sentence. That row is *about*
  this byte, which makes it the least-bad place for the correction.

## 6. What this does not establish, and the follow-ups

- **It does not establish a unit, a name, or a meaning for `0x086C`.** The
  status is `present-untested` and stays there. The `0x50` comparison is a
  comparison against a constant.
- **It does not establish anything about a machine.** Every number above is
  static. The live question is
  `docs/hardware-tests/level-block-0860-086e.md` §4.1, which is a human's to
  run at the machine (issue #252).
- **The per-site sweep does not cover `0x086C`,** and that is a real gap.
  `xdata-086x-dispatch.md` §8 has no `0x086C` row, and its contract is that
  every cell is re-derivable from `xdata-086x-dispatch-sites.csv`, so adding an
  unbacked row there would put prose in a table a tool reproduces. Closing it
  means regenerating `xdata-086x-dispatch-sites.csv` and moving the sweep-size
  strings in `trace_xdata_refs.py:49-50`, `check_site_census.py:47`,
  `xdata-086x-dispatch.md` §1/§8,
  `test_walk_budget_census.py`'s `FifteenAddressSweepTests.ADDRESSES` and the
  row counts in `test_trace_xdata_refs_usage.py` — a separate change with its
  own conflict surface, and not needed for the status, because rule 3 of
  `check_status_vocabulary.py` reads `site-resolution.csv`, which is derived
  from `registers.yaml` and not from the doc-scoped sweep. **The new entry's
  note points at this file and not at that table**, for the same reason.
- **The `0xA73F` `R7=0xBC` command code is unresolved** (§4). Answered 2026-10-03 (issue #1444): `0xA73F` takes a payload, not a command code, so there is no table to resolve it against and no value in the `0xA7`-`0xBC` range is interpreted anywhere in the image. What the payload *means* still is not in the firmware, and that part is a live read's to make rather than a scan's -- `docs/findings/a73f-09f1-mailbox-payload.md`.

The commands that reproduce every figure here, all offline from committed
inputs. The first two are the machine-code cross-tabulation §2 rests on, and
they print the five and the two rather than the census's nine and three. All
eight exit 0. The ninth, `check_cluster_citations.py`, **exits 1** and is
listed for that reason rather than as a clean run: it reports the two
pre-existing disagreements §2 names, and the figures it holds this file's
cluster claims to are green either way.

```console
$ grep -cE "DPTR, #0x86c$" ec/decompiled/bank0/*.asm | grep -v ':0$'
$ grep -cE "DPTR, #0x85f$" ec/decompiled/bank0/*.asm | grep -v ':0$'
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/gen_xdata_symbols.py --check
$ python3 ec/tools/xdata_register_map.py --check
$ python3 ec/tools/xdata_register_map.py --self-test
$ python3 ec/tools/check_status_vocabulary.py --check
$ python3 ec/tools/check_site_resolution.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/check_cluster_citations.py
```
