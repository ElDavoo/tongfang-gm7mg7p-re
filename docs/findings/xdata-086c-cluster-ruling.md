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
write, 2 address-taken, 7 readers, 6 writers, 9 functions. So is its
observation that `0x086B` is 22/12/8 across 5 and `0x086E` is 7/1/3 across 2.

## 2. The ruling: `0x086C` is not misfiled

**The clustering recorded something real.** `0x086C` shares exactly three
routines with `0x085F` — the mode tick, the fan-table mailbox handler and the
fan-boost gate, which is the mode/OEM set the cluster's hand name
`mode-oem-init` describes:

- `bank0:0x8749` `mode_tick_084c_07a5_09ee`
- `bank0:0x888D` `fan_table_mailbox_handler`
- `bank0:0x8931` `gate_0751_0741_blocks_then_tail_jump_8c46`

`0x0873` and `0x087B` sit in the same cluster (`kefb63d82f8c7`,
`main-ec-002`, `mode-oem-init`) and carry 10 functions each, the `0x95DD`
`fill_08xx_from_code_table` and `0x96AD`
`apply_oem_overrides_then_fill_08xx` pair among them. That is what co-reads
`0x086C` with `0x085F` and with the two heavily-read OEM-rewritten override
sources: one working set of bytes that a mode tick, a fan-table mailbox handler
and the OEM override path all read. `0x086B` and `0x086E` are touched only by
the `0x9D9B`/`0x9CA6`/`0xD091`/`0xD28E` set, they have no such tie to `0x085F`,
and they sit with the low-traffic override sources in `ka39cda99615f`
(`main-ec-004`, `level-block-086x`).

Two consequences are worth stating, because they are the point:

- **`0x086C` is the only one of the three result bytes that the mode tick and
  the fan-table mailbox handler touch.** Cross-tabulating the census's own
  `functions` column over the four addresses gives three pairs — `0x085F` with
  `0x086C` alone, and `0x086B`/`0x086C`/`0x086E` together in `0x9CA6` and
  `0x9D9B` — with no routine touching `0x085F` and either other result. That
  is a **shape, not a meaning**: `CLAUDE.md` and
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
by that tool, tree-wide.

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
is the only constant comparison of this byte anywhere in the record and the
closest thing to a unit the block has — **which is a reason for caution and
not a unit**. Nothing else fixes the scale. The `0x086B` note makes the same
kind of statement about the `0x48`/`0x4C` seeds.

`UNITS NOT DETERMINED` is carried over verbatim, and the name stays
`XDATA_086C`. The name is not earned: there is no live observation and no
second source for the units, and `0x086B`/`0x086E` are still `XDATA_086x` for
exactly the same reason. A constant that appears in a comparison is a number
the firmware compares against, which is a fact about the comparison and not
about the unit.

Three shapes the note records, none of which the block's own §5 clamp table
describes: the clamps are the same three `MANUAL_FAN_CTRL` (`0x0751`) values
`0x086B` gets (`0x23`, `0x14`, `0x0F`) but routed through `0xBC7B`/`0xBC7E`
rather than inline; the `0xD2BF`/`0xD2C2` pair copies the caller's DPTR byte in
and returns it masked with `0x7E`, reached with DPTR `0x1C00` or `0x1C35`; and
the `0x0A47`/`0x09EF` publish described next.

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
- **The `0xA73F` `R7=0xBC` command code is unresolved** (§4).

The commands that reproduce every figure here, all offline from committed
inputs:

```console
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/gen_xdata_symbols.py --check
$ python3 ec/tools/xdata_register_map.py --check
$ python3 ec/tools/xdata_register_map.py --self-test
$ python3 ec/tools/check_status_vocabulary.py --check
$ python3 ec/tools/check_site_resolution.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/check_cluster_citations.py
```
