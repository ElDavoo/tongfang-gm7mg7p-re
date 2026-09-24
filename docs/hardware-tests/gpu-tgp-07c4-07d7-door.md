# The `0x07D0` door: what moves first under a GPU TGP change, and who opens it

**Status: not run.** This procedure was written by the pipeline for a human at
the physical GM7MG7P (issue #184). The watcher and its offline suite are
committed; the observation is not. Nothing in this file reports a result, and
nothing under `evidence/` comes from it — the first capture of this kind will be
a human's, taken on that machine. The `0x07D0` live-write record in
`../../docs/findings.md` §4f (2026-09-17) is **not** a run of this procedure and
does not cover this block: it wrote `0x07D0` directly and watched what that
write did, which is the opposite question from which process moves the byte
when the Control Center's GPU page does.

The two committed captures are not a run of this either, and are named here so
nobody mistakes them for one: `evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv`
(§4g) and `evidence/ec-watch/2026-09-23-power-mode-cycle-0700-07ff.csv` (§7)
swept this block across an AC plug-in and an Fn mode cycle. `0x07C0`-`0x07D7`
was quiet in both except `0x07C4` twice at the plug-in. A GPU-only TGP change
is the one UI action neither bundle contains.

## 1. The question

`../../docs/findings.md` §4o closes on a negative and leaves a hazard in it.
Two decoded paths write the same physical byte, `0xFE4107D0`: the vendor
charge-limit write over `ECRW` (§4e) and the DSDT's GPU TGP write, `T1WR
Arg0 == 0x1173`, which stores `Arg1 * 8` into `0x07D0`/`0x07D1`. They disagree
about scale — an `ECRW` write of a 55% limit lands as `0x37`, while `T1WR
0x1173` cannot produce more than `0xF8` — so the byte's value carries a
different meaning depending on which door wrote it, and a reader of the byte
cannot tell which. That is arithmetic on two decoded paths, **not an observed
failure**: nothing in §4o or §4f saw a clash, and the hazard remains a hazard
however the capture comes out.

The question this procedure asks is the *door*, not the register: **under a GPU
action that is not the Fn mode bundle, does `0x07C4`-`0x07D7` move, does
`0x0743`-`0x0746` move, which moves first, and which process issued the
`DeviceIoControl` that did it.** The two blocks are in one capture on purpose.
The service's own `GpuFeatures` class writes the `0x0743`-`0x0746` half
(`../../windows/vendor-ec-map.md:84-87`), and the DSDT names the same four bytes
as `GNEN`/`ECDC`, `CTVA`, `DBCT`, `MXDB` — so if the host half moves first, the
service moved; if the ACPI half moves first under a GPU-only change, nothing in
the committed tree says what did. Two `ec_watch.py` instances would put the two
halves in two files with two start times, which is exactly the cross-file
correlation this is trying to avoid.

**Out of scope, so it is not redone here.** The register-effect half of a
Control Center GPU action — which MQTT `*/Control` command reaches which EC
register — belongs to issue #87. This procedure performs the UI action and
records marks; it does not map the command, and it does not pair the action with
`mqtt_sniff` output beyond what §3 asks for. The grading of the capture, once
there is one, belongs to issue #168.

## 2. Before you start

- Windows, Control Center 3.1.39.0 installed, and `python windows\tools\ecrw.py
  read 0x07D0` printing a value — that is the same proof
  [the `0x0751` procedure](manual-fan-ctrl-0751-isolation.md) §2 asks for, and
  it says the vendor driver is present and you are elevated.
- An **elevated** shell. `ECRR` through `\\.\ACPIDriver` needs it, and so does
  most of ProcMon's stack capture.
- Sysinternals ProcMon (or WinDbg, per §4b) available and working.
- The **starting AC state written down**, and the starting value of `0x07D0`,
  `0x07D1`, `0x0743`-`0x0746` from `ecrw.py read`. The `ac plug` / `ac unplug`
  mark in §3 means what it says only if the operator knows which way it started.
- Not a fan test. This block does not include the fan-tachometer bytes
  (`0x0460`-`0x046F`) and never should; issue #94 is the open work on `ECRR`
  pacing, and `docs/related-projects.md` records bulk sweeps stalling the fans
  on a sibling board.

### Safety

**This procedure writes nothing.** `gpu_block_watch.py` has no write path at
all, and every action in §3 is a Control Center click or a cable. `0x07D0` and
`0x07D1` are `DO-NOT-WRITE-BLIND` in `../../ec/annotations/registers.yaml` and
that stands: the only hands-on test of `0x07D0` so far is §4f's, and it relaxed
the standing instruction by exactly as much as that note records and no further.
If a capture seems to need a write to complete it, it does not; write it up as
a gap instead.

## 3. The byte capture

One watcher, both windows, one clock:

```console
rem  --interval 0.25 is ec_watch.py's default and a starting point, not a
rem  validated-safe one: one ECRR per byte, 24 of them per sweep, with
rem  nothing between calls (#94). If the fans audibly change, stop, raise it
rem  and start again.
python windows\tools\gpu_block_watch.py --csv <date>-gpu-door-07c4-07d7.csv --mark
```

`gpu_block_watch.py` prints its watch table before it opens the driver, so the
console log and the CSV's sibling table both record what was watched:
`0x07C4`-`0x07D7` and `0x0743`-`0x0746`, each address's DSDT field name and its
current `registers.yaml` `status:`. `--names-only` prints that table and exits,
if you want to read it without the machine.

Type a label + Enter to stamp a mark; Ctrl-C to stop. Take these three actions,
each as **its own pair of marks with a hold between them** — mark, act, hold,
mark — the way §3 of
[the `0x0751` procedure](manual-fan-ctrl-0751-isolation.md) paces its own,
because a window that runs from one mark to the next is only one action if the
marks are far enough apart:

1. `gpu tgp <old>W-><new>W` — move the GPU TGP target in the Control Center's
   GPU page. The `W` is the unit the UI shows; record the old and new numbers
   as displayed.
2. `fn mode <old>-><new>` — switch Fn power modes. The service rewrites a whole
   bundle on a mode change (§7), `0x0743`-`0x0746` included, so this is the arm
   that tells a GPU-only write from a mode bundle.
3. `ac plug` or `ac unplug` — the AC transition, whichever the run needs.

Hold ~30 s after each action before the closing mark. `--seconds` defaults to
running until Ctrl-C, which is the right default here: the length of the run
does not matter, the marks inside it do. A mark typed after the watcher has
exited is written nowhere — `CsvSink` drops it rather than traceback
(`../../windows/tools/ec_watch.py:63-69`) — so the run's value is in its marks,
and the last label `gpu_block_watch.py` prints at the end is the last one the
capture holds.

**Both blocks in one file is the requirement, not a convenience.** The question
is an ordering, and an ordering across two captures is an ordering across two
start times. If a second run is needed, start a second *file* with its own
marks; do not merge two files and read the union.

## 4. The attribution capture

This is the part no committed input substitutes for, and it is why §3's capture
is not optional decoration: `../../docs/findings.md` §4o's `T1WR` census is a
negative over committed inputs, and a caller that is none of those inputs is
invisible to it by construction.

### 4a. ProcMon, the primary route

1. Start ProcMon before the actions. Filter **Operation is DeviceIoControl**
   *and* **Path ends with `\ACPIDriver`**; drop everything else, or the
   `.PML` will be dominated by the watcher's own `ECRR` traffic and by the rest
   of Windows.
2. Back the trace to a `.PML` (`File ▸ Save As`) with the marks from §3 still
   legible — write the mark labels and their timestamps on paper or in a text
   file next to the trace, because the `.PML` does not carry them.
3. For **each** §3 mark, read out of the capture:
   - the **PID**,
   - the **IOCTL code in the Detail column**,
   - the **stack**, if ProcMon's stack tracing is enabled for this capture.

The IOCTL code is the load-bearing part, and it is worth saying why in the
terms the committed inputs give. `ACPIDriver.sys` hardcodes the ACPI method name
per IOCTL — `movl $0x52524345,0x54(%rsp) ; MethodName = 'ECRR'`
(`../../windows/native/ACPIDriver.sys.analysis.md:177`) — and
`../../windows/native/ACPIDriverDll.dll.analysis.md:71-76` maps the codes:

| IOCTL | ACPI method | door |
|---|---|---|
| `0x9C40A488` | `ECRR` | EC read, raw 16-bit address |
| `0x9C40A48C` | `ECRW` | EC write, raw 16-bit address — the vendor charge-limit door (§4e) |
| `0x9C40A4D0` / `D4` / `D8` | `T1RD` / `T2RD` / `T3RD` | temp-read doors |
| `0x9C40A4DC` | `T1WR` | the `T1WR` door — the one `Arg0 == 0x1173` would come through |
| `0x9C40A4E0` / `E4` | `T2WR` / `T3WR` | the other two temp-write doors |

So an `ECRW` and a `T1WR` are told apart by **the handle that issued them**,
before anyone asks which byte moved. That is the whole of the "door" the
question is named for, and it is why the attribution capture is not a second
half of this procedure but the half that answers it.

4. At the moment of each mark, record the **loaded-module list** for the PID
   §4a.3 found:

   ```powershell
   Get-Process -Id <pid> | Select -Expand Modules     # or Listdlls.exe <pid>
   ```

   **Calibrate what this is worth.** A module loaded is not a call made. It
   distinguishes a JIT or reflectively-loaded caller from a plain one, and
   nothing more: a module that has been mapped since boot tells you nothing
   about this instant. What it is good for is the negative §4o's census could
   not close — if a module appears in this list that is not a process in the
   committed tree, that is a lead, and it is worth a new term set for
   `../../windows/tools/t1wr_callers.py`.

### 4b. WinDbg, if ProcMon's stack is not enough

Needs a kernel debugger session on the machine — a second step, not a
substitute you can skip to. `IRP_MJ_DEVICE_CONTROL` lands at `0x140007130` in
`ACPIDriver.sys`
(`../../windows/native/ACPIDriver.sys.analysis.md:162`); break there, inspect
the IRP and the stack, and read the control code the same way as ProcMon's
Detail column. The handler for `0x9C40A488` is `0x14000125C`, and §"How one
handler works, in full" of that file walks what the stack frame holds at that
point.

## 5. The blank result table

One row per §3 mark, filled in by the human who ran it. No example row is
given: an example row reads as an observation, and this repository is not where
that mistake is cheap.

| mark label | mark ts | `0x07C4`-`0x07D7` addresses moved (DSDT name) | `0x0743`-`0x0746` addresses moved | which block first, and by how many ms | ProcMon PID | process image | IOCTL code on the `\.\ACPIDriver` handle | modules loaded at that instant | verdict |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |

"Which block first" is the ordering the console summary prints, and the number
to put in the cell is that number read off the CSV rather than off the terminal
scrollback. "Verdict" is the human's call against §6, not the tool's: the tool
prints a timing report and says so, and issue #168 owns grading a capture.

## 6. What a result would settle, and what it would not

Written before the run, on purpose: the three-way reading below is what makes
the table's verdict column a judgement rather than a summary.

- **`0x07D0` moves under a GPU-only change, with no host `ECRW` at the mark** —
  evidence *for* the GPU reading of the byte, and the first thing anyone has
  observed rather than decoded. It does not establish that the EC acts on it:
  `T1WR 0x1173` sets `AMAT` from its own argument, not from the byte (§4o), so
  a movement with no visible host write is a question, not a confirmation.
- **Movement only when the Fn bundle runs** — a service write, and the
  `0x0743`-`0x0746` half is where to look for the one that did it. This is the
  result that changes the reading order least.
- **No movement at all, under all three actions** — the clobber hazard stays
  exactly as §4o records it: arithmetic on two decoded paths, not an observed
  failure. That is a result, and it moves §4o toward "a GPU power byte the
  BIOS writes" and toward the `AMAT`/`ATPP` double-writer hazard being
  arithmetically possible rather than reachable by any service the committed
  inputs can see.

Two caveats belong next to the table rather than in a footnote.

- **The window delta is an endpoint net.** A byte that moves and comes back
  between two of the watcher's sweeps reads as quiet. A zero here is "not moved
  by this method under this action" — never "the GPU does not read it" — and
  read any zero through issue #168 first.
- **A readback is not an effect.** Nothing in this procedure checks whether the
  EC acted on a byte, and the table deliberately has no "readback OK ⇒
  confirmed" column. Do not add one. `../../CLAUDE.md`: a register write being
  accepted is not evidence the EC acts on it, and this run does not even write.

## 7. The citation list

Static, hand-checked into the tool's watch table and pinned there by
`../../windows/tools/test_gpu_block_watch.py`, which fails if any cell below
stops matching `../../evidence/acpi/dsdt.dsl` or
`../../ec/annotations/registers.yaml` — if this table's own status column
stops agreeing with the tool's, and if the EC-side cross-reference column of
the four rows the per-site census covers stops agreeing, in both directions,
with `../../ec/annotations/ec-07c4-07d5-sites.csv` and its `.md`. The DSDT
names and bits come from the `ECMG` field list at
`../../evidence/acpi/dsdt.dsl:52204-52212` and `:52238-52258`.

| addr | DSDT field (bit) | `registers.yaml` `status:` | EC-side cross-reference |
|---|---|---|---|
| `0x0743` | `GNEN` b0, `ECDC` b1 (`dsdt.dsl:52204`) | `confirmed-working` — `CTGP_DB_CTRL` | `xdata-registers.csv`: `main-ec`, `main-ec-001`, no `[writer]`-tagged site in the row |
| `0x0744` | `CTVA` (`dsdt.dsl:52207`) | `confirmed-working` — `CTGP_DB_CTRL` | `xdata-registers.csv`: `main-ec`, `main-ec-001`, no `[writer]`-tagged site in the row |
| `0x0745` | `DBCT` (`dsdt.dsl:52207`) | `confirmed-working` — `CTGP_DB_CTRL` | `xdata-registers.csv`: `main-ec`, `main-ec-001`, no `[writer]`-tagged site in the row |
| `0x0746` | `MXDB` (`dsdt.dsl:52207`) | `confirmed-working` — `CTGP_DB_CTRL` | `xdata-registers.csv`: `main-ec`, `main-ec-001`, no `[writer]`-tagged site in the row |
| `0x07C4` | `DBEN` b3, `DBST` b5 (`dsdt.dsl:52238`) | `present-untested` — `GPU_DYNAMIC_BOOST_STATUS` | `xdata-registers.csv`: `main-ec`, `main-ec-001`, writer `bank0:0x94C0=set_07c4_bit4_from_r7`; that is the one site the row's own tag names, not the only one in the image — `../../ec/annotations/ec-07c4-07d5-sites.md` §2-§4.1 is the full EC-image census: four sites in `bank0:0x83FF=sync_0788_and_07d4_from_09e9` (`bank0:0x843D` read, `bank0:0x844A` read, `bank0:0x8483` and `bank0:0x8490` read-modify-write of bit 3) and `bank0:0x94C1`, a read-modify-write of bit 4 inside `0x94C0=set_07c4_bit4_from_r7`, fed from bit 1 of `CTGP_DB_CTRL` by its one caller at `bank0:0x9711` |
| `0x07C5` | `WHMS` b5 (`dsdt.dsl:52243`) | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `main-ec`, `main-ec-001`, writer `bank0:0xBB80=store_a_then_read_07c5` |
| `0x07C6` | `WMS0` b0-1 (`dsdt.dsl:52246`) | `present-untested` — `AP_OEM_6` | `xdata-registers.csv`: `main-ec`, `main-ec-001`, no `[writer]`-tagged site in the row |
| `0x07C7` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | no row in `../../ec/annotations/xdata-registers.csv` |
| `0x07C8` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | no row in `../../ec/annotations/xdata-registers.csv` |
| `0x07C9` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-001`, no `[writer]`-tagged site in the row |
| `0x07CA` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-001`, no `[writer]`-tagged site in the row |
| `0x07CB` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-001`, no `[writer]`-tagged site in the row |
| `0x07CC` | none declared | `present-untested` — `USB_C_POWER_PRIORITY` | `xdata-registers.csv`: `pd`, `pd-001`, writer `pd:0xF63F=store_r7_to_07cc_r5_to_0945` |
| `0x07CD` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-001`, no `[writer]`-tagged site in the row |
| `0x07CE` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-001`, no `[writer]`-tagged site in the row |
| `0x07CF` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-018`, no `[writer]`-tagged site in the row |
| `0x07D0` | `DBD1` (`dsdt.dsl:52248`) | `unknown-not-absent-DO-NOT-WRITE-BLIND` — `DBD1` | `xdata-registers.csv`: `pd`, `pd-027`, no `[writer]`-tagged site in the row (the row's own function tags are not a writer census; `../../ec/annotations/ec-0x07d0-sites.md` enumerates all 254) |
| `0x07D1` | `DBD2` (`dsdt.dsl:52248`) | `unknown-not-absent-DO-NOT-WRITE-BLIND` — `DBD2` | `xdata-registers.csv`: `pd`, `pd-026`, no `[writer]`-tagged site in the row |
| `0x07D2` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-016`, writers `pd:0x36F2`, `pd:0x68CE`, `pd:0xC755` |
| `0x07D3` | `GFID` b4-6 (`dsdt.dsl:52251`) | `present-untested` — `GFID` | `xdata-registers.csv`: `both`, `main-ec-001`, writers `bank0:0xBA46`, `pd:0xC755`; `../../ec/annotations/ec-07c4-07d5-sites.md` §2, §4.2 is the full EC-image census: `bank0:0x94D5` read (tests `GFID == 3`), `bank0:0xBA46=clear_low_nibble_07d3` a read-modify-write of the low nibble, and `bank0:0xDA2D` and `bank0:0xDA41` outright writes of `0x30`/`0x40`/`0x50`/`0x70` — `GFID` 3, 4, 5 and 7, branching on bit 4 of `0x166A` |
| `0x07D4` | `CPUA` (`dsdt.dsl:52254`) | `present-untested` — `CPUA` | `xdata-registers.csv`: `both`, `main-ec-001`, writers `pd:0xD013`, `pd:0xEE68`; `../../ec/annotations/ec-07c4-07d5-sites.md` §2, §3 adds the two bank0 sites `xdata-registers.csv` does not name: `bank0:0x8460` read and `bank0:0x8477` write, both in `bank0:0x83FF=sync_0788_and_07d4_from_09e9` and both under the `CTGP_DB_CTRL` (`0x0743`) bit-0 guard, copying `[0x09EA]` in |
| `0x07D5` | `DBAP` (`dsdt.dsl:52254`) | `present-untested` — `DBAP` | `xdata-registers.csv`: `both`, `main-ec-001`, writers `pd:0xD013`, `pd:0xEE68`; `../../ec/annotations/ec-07c4-07d5-sites.md` §2, §3, §4.3 adds the four bank0 sites `xdata-registers.csv` does not name: `bank0:0x846C` read and `bank0:0x847F` write, both in `bank0:0x83FF=sync_0788_and_07d4_from_09e9`, copying `[0x09EB]` in; and `bank0:0xAD99` and `bank0:0xCC78`, both storing `0xFF`, the first inside `reset_xdata_flags_and_07d5_to_ff` and the second in a run of the same three instructions whose entry point is not determined |
| `0x07D6` | `DBSP` (`dsdt.dsl:52254`) | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-028`, writers `pd:0xBECB`, `pd:0xF247`, `pd:0xF440` |
| `0x07D7` | `CGCT` (`dsdt.dsl:52254`) | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-029`, writers `pd:0xABBF`, `pd:0xBECB` |

Four notes on reading the table, each of which is a place a table like this
gets misread:

- **"No row" is a statement about `registers.yaml`, not about the address.** It
  is 12 of the 24, and it is the §4c retraction in table form
  (`../../docs/findings.md` §4c retracted a "does not exist" claim built on a
  zero-reference scan). 12 cells saying "no row" is the sentence most
  likely to be read back as 12 claims of absence; they are not. The per-site
  EC-side census of the four rows that do have one is
  `../../ec/annotations/ec-07c4-07d5-sites.md`, which walks the fifteen
  main-EC sites of `0x07C4`/`0x07D3`/`0x07D4`/`0x07D5` — a write *class* in
  the instruction stream, not evidence the EC acts on the byte.
- **`0x07C4`'s `DBEN` is bit 3, not bit 0.** §4o writes the gate as "`DBEN`
  (`0x07C4` bit 0)"; the field list at `dsdt.dsl:52238-52242` allocates three
  unnamed bits before it, so `DBEN` is bit 3 and `DBST` bit 5. The bit column
  here is the field list's, and the suite checks it against the file rather than
  against prose. §4o's prose is left as written rather than edited from here.
- **`0x0743`'s bit semantics differ between the two sources, and both are
  right.** The DSDT field list names two bits (`GNEN` b0, `ECDC` b1); the
  `registers.yaml` note describes three (bit 0 DB function control, bit 1 DB
  enable, bit 2 cTGP enable). The name column is the field list's; the status
  column is `registers.yaml`'s. Neither file is corrected by this one.
- **The `xdata` columns name their file every time, including when the answer
  is no row.** A bare "none" is indistinguishable from a scan that did not run.
  `../../ec/annotations/xdata-registers.csv` and
  `../../ec/annotations/xdata-clusters.csv` are inputs this procedure only
  reads; `../../ec/ghidra/xdata-symbols.csv` is generated from
  `registers.yaml` and must never be hand-edited.

## Cross-references

- **#87** owns mapping each MQTT `*/Control` command to its EC-register effect.
  The register-effect half of a Control Center GPU action is not repeated here.
- **#168** owns grading a capture. This procedure emits a CSV in the schema
  `ec_watch.py` and `../../ec/tools/grade_0751_isolation.py` already read, and
  the grading is that issue's.
- **#96** and **#1** are what the answer feeds: the upstream correction must not
  be written as though `0x07D0` has one meaning, and the paired `0x07B9`/
  `0x07D0` write is still the experiment that would settle whether the byte is a
  threshold at all.
- **#8 / `ctgp_live_test.py`** established the `0x0743`-`0x0746` half
  host-side against `nvidia-smi`, and is the established *writer* for that
  block. It does not watch `0x07C4`-`0x07D7`, which is why this tool exists
  alongside it rather than instead of it.
- **#131 / §4o** is the census this procedure is the human half of, and
  `../../windows/tools/t1wr_callers.py --self-check` is what must still pass for
  its negative to mean what §4o says it means.
- **#94** owns `ECRR` pacing and is why `--interval` is a starting point here.
- **`../../ec/annotations/ec-07c4-07d5-sites.md`** is the per-site EC-side
  census of the `0x07C4`/`0x07D3`/`0x07D4`/`0x07D5` rows above, all fifteen of
  their main-EC sites. It supersedes the single-site credit this table gave
  `0x07C4` before, and it reads a write class, not an effect.

---

**Running this is a human step on the physical GM7MG7P. This repository
contains no result from it.**
