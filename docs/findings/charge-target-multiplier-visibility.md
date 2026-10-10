# Charge-target derating: the multiplier at 0x0A47 outside the host window

The charge-limit feature's derating depends on a 16-bit multiplier stored at
XDATA `0x0A47`/`0x0A48`, but the register is outside the host-accessible window
and the scheduler writes it invisibly. This file traces the causal chain and
explains what a capture can and cannot settle about the derating computation.

## 1. The causal chain: `0x0A47` → `charge_target_minus_r3_times_0a47` → `CHARGE_TARGET_MV`

The function at bank0 `0xB35E`, `charge_target_minus_r3_times_0a47`, is cited in
`ec/annotations/ghidra-functions.csv` with the comment:

> Takes its argument in R3, loads the 16-bit multiplier from XDATA 0x0A47, and
> forms the 16-bit product R3 x 0x0A47 with the 16x16 multiply at 0x707D
> (result in R7:R6). It subtracts that product from the big-endian 16-bit value
> at XDATA 0x0A50/0x0A51 and writes the little-endian difference to
> CHARGE_TARGET_MV at 0x0523 (high) and 0x0522 (low).

That chain is: `0x0A47`/`0x0A48` (multiplier) → `R3 x 0x0A47` (product) →
`0x0A50`/`0x0A51` − product (difference) → `CHARGE_TARGET_MV` at `0x0522`/`0x0523`
(output).

The decompiled function is at `ec/decompiled/bank0/B35E.c` and the assembly at
`ec/decompiled/bank0/B35E.asm`. Both are machine-generated from the firmware image.

## 2. The visibility asymmetry: multiplier invisible, output observable

The host XDATA window is `0x0800`–`0x0BFF`. The register spans:

- **Multiplier:** `0x0A47`/`0x0A48` — **outside** the window
- **Output:** `0x0522`/`0x0523` — **inside** the window

This is not an assumption. `docs/findings/scheduler-run-8518-entries.md` §4 ranks
every XDATA address in the scheduler block's write sets against the window and
lists the invisible ones. The entry for slot `0x852A` (which writes the
multiplier) names `0x0A47`–`0x0A48` in its `invis:` cell. The census behind the
window is in `evidence/ec-watch/2026-09-24-host-window-page-census.txt`.

A capture using `ec_timer_capture.HOST_WINDOW` will read `0x0522`/`0x0523` when
the EC updates them but will not see `0x0A47` change. The host therefore
**cannot attribute output changes to multiplier changes** — the observable output
depends on an unobservable input.

## 3. What the scheduler block is doing

The scheduler runs every millisecond. `docs/findings/scheduler-run-8518-entries.md`
§1 decoded its structure: the block is reached via seven stub entry points (far
calls to `0x8518`, `0x851B`, `0x8524`, `0x8527`, `0x852A`, `0x8539`, and `0x854B`),
and each stub dispatches one of seven segments.

Segment 4 (slots `0x852A` onwards) includes the multiplier writer at slot `0x852A`.
There is no committed name for slot `0x852A` itself, but the prose says:

> Writes the `0x0A47`/`0x0A48` constant pair and touches `0x08E2`; the `0x0A48`
> byte is written by the `inc dptr` after `0x0A47`.

Slot `0x854B`, also in segment 6, "Seeds the TCC defaults" and writes
`0x0A47`/`0x0A48` pairs and `0x0A49` (seed_tcc_defaults_from_ba36). The `0x0A47`
register is written by multiple scheduler segments, not just one.

## 4. Why this matters: the register has many writers

`0x0A47` is not written only by the scheduler. The plan issue (#1678) cited
`ec/annotations/xdata-registers.csv`, which lists multiple addresses writing to
`0x0A47`: `0x9277`, `0xA1C8`, `0xADA3`, `0xBCCB`, `0xBE73`, and others. The
scheduler's contribution is invisible to the host, which means:

- The **host cannot see the scheduler's writes** at all
- The **host cannot distinguish the scheduler's writes from other writers** even
  if it could see the byte through another mechanism
- The **host cannot arbitrate between writers** or apply any logic dependent on
  which writer moved the value

This is not a "some slots are invisible" observation (which would be routine); it
is a "the first term in the causal chain is invisible while the last term is
observable" situation that changes what a capture can test.

## 5. What a capture CAN observe

The output of the derating is at `0x0522`/`0x0523`, which **is** in the host
window. An `ec_timer_capture.py` capture at millisecond granularity will record:

- The starting values of `0x0522`/`0x0523`
- Every change to `0x0522`/`0x0523` during the capture
- Timestamps for when those changes occurred (millisecond resolution, relative to
  EC timer ticks)

The charge-limit subsystem is observable through its output. A capture is still
valuable for understanding the *output* behavior of the derating.

## 6. What a capture CANNOT do

A capture cannot:

- Observe the multiplier at `0x0A47`/`0x0A48` (outside the window)
- Attribute a change in `0x0522`/`0x0523` to a specific change in `0x0A47` or a
  specific scheduler segment
- Determine which writer caused a particular multiplier value (the scheduler, the
  fan table handler at `0xBC4F`/`0xBCCB`, or another path)
- Confirm that the derating formula `output = 0x0A50/0x0A51 - (R3 × 0x0A47)` is
  actually executed (the decompile is static; the formula is inferred from the
  code)

Because the host cannot read `0x0A47` and the EC writes it outside the window, a
capture of the scheduler block's activity through the charge-limit path cannot
close the loop from input to output.

## 7. Related work

- `docs/findings/scheduler-run-8518-entries.md` §3 and §4: the scheduler block's
  structure, the seven entry points, and what each segment's invisible write set
  covers.
- `docs/findings/ec-fan-table-defaults.md` §1: how the helper routines `0xBC4F`
  (adds nothing) and `0xBCCB` (adds a byte) feed the multiplier into
  `0x0A47`/`0x0A48`, and the fan-table path's own handling of the pair.
- `docs/findings/xdata-086c-cluster-ruling.md` §200: the paragraph recording the
  `0x0A47`/`0x09EF` clamp (the multiplier is clamped against `0x09EF`, which is a
  related XDATA address).
- `ec/annotations/xdata-registers.csv`: a complete list of every address that
  writes to `0x0A47` (at least, by direct `mov dptr` sites; see the YAML caveat
  for blind spots).

## 8. What this does not settle

- **No behavioral test.** The derating formula is read statically from the
  decompile. The multiplier and the output are observed independently. Whether
  the EC actually executes the formula is not tested.
- **No register status change.** `registers.yaml` will record `0x0A47` with
  status `present-untested`: the register is read from the firmware statically,
  and a window argument explains why behavioral validation is impossible from the
  host side.
- **No capture run.** This is documentation, not results. A capture would need to
  be run by a human with the physical laptop, and would still face the asymmetry:
  observable output, invisible input.
