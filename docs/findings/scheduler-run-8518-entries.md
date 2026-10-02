# The `0x8518` block decoded: seven entry points, not one, and half of it is invisible to the host (issue #1185)

[`charge-target-caller-chain.md`](charge-target-caller-chain.md) §1 traced one
path: the scheduler's case `0x0A` selects a far-call stub, the stub's immediate
is `0x8539`, and `0x8539` is a slot in the stride-3 run at bank0 `0x8518`. That
is all correct, and it is one entry into a block that the same stub table
reaches seven more times — and the block is not one walk either.

Both facts are re-derived here by `ec/tools/run_entry_map.py` from
`ec/firmware/GMxMGxx_11.800` and the committed
`ec/annotations/task-call-table.csv`, with `ec/tools/test_run_entry_map.py`
holding the byte facts. Nothing here was run on hardware; see
"What this file is not" below.

## 1. The block is seven segments, and the seven stubs name their heads

An `lcall` slot returns into the next slot. An `ljmp` slot does not: it leaves
the block, and what happens next is the target's own return. So a **segment**
is a maximal run of `lcall`s ending at an `ljmp`, and a **head** is the run's
first entry or the slot immediately after an `ljmp`. Both are computed from the
run's own opcodes.

The seven stub immediates that land in the block are exactly the seven heads.
That is the finding, and it is stronger than the issue asked to be settled: the
issue named index 10 as the single split, and index 10 is one of seven. A
scheduler that looks like one `lcall` is one scheduler walking seven entry
points of a single block, and the chain §1 traced is one of those seven walks.

| stub | immediate | run index | segment | segment is |
|---|---|---|---|---|
| `0x155E` | `0x8518` | 0 | 0 | one slot, ending at the `ljmp` at index 0 |
| `0x1564` | `0x851B` | 1 | 1 | indices 1–3 |
| `0x156A` | `0x8524` | 4 | 2 | one slot, ending at the `ljmp` at index 4 |
| `0x1570` | `0x8527` | 5 | 3 | one slot, ending at the `ljmp` at index 5 |
| `0x1576` | `0x852A` | 6 | 4 | indices 6–10 |
| `0x157C` | `0x8539` | 11 | 5 | indices 11–16 — **the chain §1 traced** |
| `0x1582` | `0x854B` | 17 | 6 | indices 17–21 |

These are the only entries in the far-call stub table whose immediate lands in
`0x8518`–`0x8559`. The neighbours either side enter `0x849D`, `0x84EA`,
`0x84EB`, `0x84FD`, `0x8500`, `0x8501`, `0x8502`, `0x850B` — the two earlier
stretches the caller chain's §3 already calls separate runs — and `0x855A`,
`0x8564`, `0x8567`.

**Nothing enters the middle of a segment.** An unaligned scan of the whole
image for `12 xx xx` and `02 xx xx` naming any of the block's own addresses
returns zero hits. That is *not found by this method* — two opcodes, unaligned,
over the whole 0x40000-byte image — and it is not an absence claim. A transfer
built at run time, or one through a function-pointer table, would not be found by
it, and this repository has already found one such mechanism in this image
(`common 0x7151`, the `switch_case_dispatch` the caller chain's §1 relies on).

## 2. Why a tail-jumped slot leaves the block — the one load-bearing premise

The reachability table above rests on a single claim: **a tail-jumped slot's
target returns to the entry's caller rather than resuming the block.** It is not
a reading of the run; it is a property of the bank-select trampoline all seven
stubs go through. Each stub is `mov dptr,#<target> ; ljmp 0x1100`, and `0x1100`
is 20 bytes:

```
0x1100  c0 08     push 0x08      ; save the caller's byte
0x1102  74 11     mov  a,#0x11   ; the marker's high byte
0x1104  c0 e0     push acc       ; push it
0x1106  c0 82     push 0x82      ; push DPL
0x1108  c0 83     push 0x83      ; push DPH
0x110A  75 08 0a  mov  0x08,#0x0a
0x110D  c2 90     clr  0x90
0x110F  c2 91     clr  0x91
0x1111  c2 92     clr  0x92
0x1113  22        ret            ; pops DPH, DPL -> jumps to the far address
```

The stub's own `ret` consumes the two DPTR bytes, so what the far routine's own
`ret` pops is the **marker** — the accumulator and the saved byte — not the
caller's return address. The marker's high byte is the stub's own
`mov a,#0x11`, a constant in these bytes, so a far routine returns somewhere in
**`0x1100`–`0x11FF`** whatever the low byte is. That window contains no address
in the run, which is the whole of the claim.

The marker's **low** byte is direct `0x08`'s value at entry, which is a runtime
value and is not guessed at. The four bank-select stubs each write their own
value into `0x08`, so the four possible landings are `0x110A`, `0x111E`,
`0x1132` and `0x1146` — each one the stub's own bank-select tail, each inside
the window. The claim rests on the window, not on any one of the four.

`run_entry_map.py --self-test` derives all of that from the stub's bytes and
checks the window against the run's own addresses. If the stub ever stopped
having this shape, the tool prints `reach unsettled` in place of the
reachability column rather than publishing a table built on the assumption.

## 3. Slot by slot: what each does, and what it writes

One row per slot. `vis` is the write set the **host can see** and `invis` the
one it cannot, both split against `ec_timer_capture.HOST_WINDOW` — see §4 for
why the split is the point. The names are the committed ones from
`ec/annotations/ghidra-functions.csv`; a target with no row there says so rather
than leaving the cell blank.

Reproduce with `python3 ec/tools/run_entry_map.py ec/firmware/GMxMGxx_11.800
--callee-depth 1`; the per-slot per-address table is `--writes-csv`.

| slot | op | target | seg | stub | committed name | what it does per pass, and what it writes |
|---|---|---|---|---|---|---|
| `0x8518` | `ljmp` | `0xB065` | 0 | `0x155E` | `ten_count_gate_then_set_1300_and_200f` | Gates on `0x0440`/`0x047E`/`0x06DB`/`0x06E6`, then a ten-count latch sets `0x1300`/`0x1304` and `0x200F`. vis: none. invis: `0x0B00` `0x0BFD` `0x0BFE` `0x1300` `0x1302` `0x1304` `0x2007` `0x200F` |
| `0x851B` | `lcall` | `0xA7C8` | 1 | `0x1564` | *no committed name* | A power-mode profile gate: on `0xBE9C` clear it sets bits in `0x0742`/`0x0782`/`0x078E` and clears `0x0783`–`0x0785`/`0x078B`, and rewrites `0x0751` from the bits it just read. vis: `0x0730`–`0x0732` `0x0737` `0x0739` `0x073A` `0x0742` `0x0751` `0x0782`–`0x0785` `0x078B` `0x078E` `0x07A7`–`0x07AA`. invis: `0x08E6` `0x0A50` `0x0A51` |
| `0x851E` | `lcall` | `0xA844` | 1 | — | `update_0476_flags` | Sets or clears bit 4 of `0x0768` from `0x0398`, then sets or clears bits 5 and 6 of `0x0476` against `0x0490` bit 2, `0x04AB` and a 16-bit compare. vis: `0x0476` `0x0768`. invis: `0x084F` `0x0850` |
| `0x8521` | `ljmp` | `0xCFC6` | 1 | — | `collect_two_flags_into_0816_then_raise_ap_oem_bit7` | Scans 253 bytes of `0x0B00` for two markers, sets bit 0 or 1 of `0x0816`, and on both seen sets bit 7 of `0x0741`. vis: `0x0741`. invis: `0x0816` |
| `0x8524` | `ljmp` | `0x9049` | 2 | `0x156A` | `countdown_0806_and_branch_on_0490` | Gates on `0x0490` bits 0 and 2 with `0x0398` and `0x06E6`, reloads and decrements the `0x0806` countdown. vis: none. invis: `0x0806` `0x1607` `0x1641` |
| `0x8527` | `ljmp` | `0xB0DC` | 3 | `0x1570` | `sync_0983_bit5_against_support_2_bit4` | Sets or clears bit 5 of `0x0983` to follow bit 4 of `0x0440`/`0x0766`. vis: none. invis: `0x0983` |
| `0x852A` | `lcall` | `0xB83B` | 4 | `0x1576` | *no committed name* | Writes the `0x0A47`/`0x0A48` constant pair and touches `0x08E2`; one `movx` rides a DPTR built at run time and is unattributed. vis: none. invis: `0x08E2` `0x0A47` `0x1607` |
| `0x852D` | `lcall` | `0x924C` | 4 | — | `set_0838_0839_0832_on_049f_bit2` | Clears bit 2 of `0x049F` if set, then writes `0x0838`/`0x0839` and sets bit 2 of `0x0832`. vis: `0x049F`. invis: `0x0832` `0x0838` `0x083A` `0x083B` `0x08B9` `0x08E2` |
| `0x8530` | `lcall` | `0xD091` | 4 | — | `dispatch_on_0860` | The `0x0860` dispatch: copies six `0x1Cxx` bytes into `0x0866`–`0x086B` and writes `0x0865`, then dispatches. vis: `0x07FD`–`0x07FF`. invis: `0x0864`–`0x086C` `0x08EB` `0x1063` `0x1C00`–`0x1C05` `0x1C15` `0x1C16` `0x1C39` `0x1C3A` `0x1F01` `0x1F06` `0x1F07`. **Cut** at the routine's `jmp @a+dptr` |
| `0x8533` | `lcall` | `0xDFDF` | 4 | — | `gate_06e6_then_store_0464` | Gates on `0x06E6` then stores the `0x0464`/`0x0465` pair. vis: `0x0464`. invis: none |
| `0x8536` | `ljmp` | `0xAC4A` | 4 | — | `toggle_08e2_bit4` | Returns unless `0xB9D8` is zero and `0x073C` is exactly `0x01`, then sets or clears bit 4 of `0x08E2` and adjusts `0x0826` and `0x086F`. vis: none. invis: `0x0826` `0x086F` `0x08E2`. **This is the split the issue named** |
| `0x8539` | `lcall` | `0xE010` | 5 | `0x157C` | `load_06e6` | Loads `0x06E6` and, on `0x01`, stores R6:R7 to `0x046C`/`0x046D`. vis: `0x046C`. invis: none |
| `0x853C` | `lcall` | `0x9167` | 5 | — | `gate_on_074c_then_dispatch` | Three gates on `0x074C`, then sets bit 5 and dispatches on the low nibble. vis: `0x0463` `0x074C`. invis: `0x098C`. **Cut** at the `0x7151` dispatcher's `jmp @a+dptr` |
| `0x853F` | `lcall` | `0xB12C` | 5 | — | `manual_ctrl_profile_gate` | The chain's target: sets `0x078E` bit 3, forces the manual-ctrl profile back to High Capacity, and on `0x0490` bit 1 clear zeroes the `0x09C7`–`0x09C9` stress counters. vis: `0x0522` `0x0523` `0x078E` `0x07A6`. invis: `0x09C7` `0x09C8` `0x09C9` `0x0A47` `0x0A4A` `0x0A4E` |
| `0x8542` | `lcall` | `0xB4A8` | 5 | — | *no committed name* | A state machine over `0x08EB`/`0x09E6`/`0x09E7`; its tail clears `0x08EB` bit 5 and zeroes `0x08A1` and `0x089C`/`0x089D`. vis: `0x047F` `0x06D1`. invis: `0x089C` `0x08A1` `0x08EB` `0x09E6` `0x09E7` |
| `0x8545` | `lcall` | `0xB5D3` | 5 | — | *no committed name* | A larger state machine over the same `0x08EB` family, plus `0x0875`/`0x089E`/`0x08A2` and the `0x0A47`/`0x0A49` pair. vis: `0x047F` `0x06D1`. invis: `0x0875` `0x089E` `0x08A2` `0x08EB` `0x09E6` `0x09E7` `0x0A47` `0x0A49` |
| `0x8548` | `ljmp` | `0xB737` | 5 | — | *no committed name* | The USER-bit branch of the `0x0751` state machine; its exit clears `0x08EB` bit 6 and zeroes the `0x08A0` count. vis: none. invis: `0x08A0` `0x08EB` `0x0A47` |
| `0x854B` | `lcall` | `0x9334` | 6 | `0x1582` | `seed_tcc_defaults_from_ba36` | Seeds the TCC defaults: writes the `0x07D8`–`0x07DA` offsets, `0x0A47`/`0x0A48` pairs and `0x0A49`. vis: `0x0463` `0x07D8` `0x07D9` `0x07DA`. invis: `0x098C` `0x0A47` `0x0A49` `0x0A4A` |
| `0x854E` | `lcall` | `0x9CA6` | 6 | — | `gate_06e6_442_then_sync_046a_from_086b` | Gates on `0x06E6` and `0x0442`, counts `0x0893` to `0x17`, then syncs the `0x046A`/`0x046B`/`0x046E`/`0x046F` group from `0x086B`–`0x086E`. vis: `0x0463` `0x0466` `0x046A` `0x046B` `0x046E` `0x046F` `0x0730`–`0x0732` `0x0737` `0x07A7`–`0x07AA` `0x07C6`. invis: `0x080F` `0x0865`–`0x0869` `0x086B`–`0x086C` `0x086E` `0x0893` `0x09C1` `0x09EF` `0x0A47` `0x0A50` `0x0A51` |
| `0x8551` | `lcall` | `0x83FF` | 6 | — | `sync_0788_and_07d4_from_09e9` | Copies `0x09E9` into `0x0788` and, when `0x0743` bit 0 is set, `0x09EA`/`0x09EB` into `0x07D4`/`0x07D5`. vis: `0x0788` `0x07C4` `0x07C5` `0x07D4` `0x07D5`. invis: none |
| `0x8554` | `lcall` | `0xA2E0` | 6 | — | `step_0859_then_toggle_0858_bit0` | Steps the `0x0859` countdown, and at zero toggles bit 0 of `0x0858` against a `0xC224` read of `0x1604`. vis: none. invis: `0x0850` `0x0858` `0x0859` |
| `0x8557` | `ljmp` | `0xA97B` | 6 | — | `dispatch_on_06e6_and_0741` | Gates on `0x06E6` and `0x0741`, decrements the `0x8A5`/`0x8A6` pair, sets or clears `0x0741` bit 2 and `0x086F`. vis: `0x0741` `0x0769` `0x076A` `0x076B`. invis: `0x086F` `0x08A5` `0x1803` `0x1805` `0x1808` |

**What a row is and is not.** A `write` is an instruction storing to an address
in the block's own walk plus one level of `lcall` callee — it is not evidence
the EC acts on the value, and no value is read back. The walks are
`walk_branch_arms.descend()` used unchanged, so its refusals are these rows'
refusals: a `movx` on a DPTR built at run time is **unattributed** rather than
charged to the last `mov dptr`, and `--callee-depth 1` is a *declared* depth —
past it a callee reads `unresolved` or `partial`, and the write set is a lower
bound rather than the whole set. **Cut** marks a walk that stopped at a bound
rather than at a terminator, and the two such rows are cut at a `jmp @a+dptr`
whose target the bytes do not resolve. A slot whose write set is empty would be
reported as "no arm found by this method writes an XDATA address" and never as
"the EC does not"; no slot here is empty, but the wording is the tool's.

## 4. The host-window split — the reason half of this cannot be graded by a capture

`ec_timer_capture.py` documents that this machine's window maps `0x0000`–`0x07FF`
and `0x0C00`–`0x0FFF`, and `evidence/ec-watch/2026-09-24-host-window-page-census.txt`
is the measurement behind that: pages `0x0800`–`0x0BFF` and everything above
`0x1000` came back **0 of 256 bytes non-`0xFF`**. A byte the block writes in one
of those pages reads `0xFF` to the host whatever the EC holds, and the host
cannot tell that from a byte the EC has left alone.

The `vis` / `invis` split in §3 is that classification, computed against the
imported `HOST_WINDOW`. The consequence a future run needs most: **several
named slots have a write set that is wholly outside the window** — `0x8518`
(`0x1300`, `0x1304`, `0x200F`), `0x8524` (`0x0806`), `0x8527` (`0x0983`),
`0x852A` (`0x08E2`, `0x0A47`), `0x8536` (`0x0826`, `0x086F`, `0x08E2`),
`0x8548` (`0x08A0`, `0x08EB`, `0x0A47`) and `0x8554` (`0x0850`, `0x0858`,
`0x0859`). A capture of the dispatch period that watches one of these and sees
`0xFF` throughout has learned nothing about the counter — it has learned that
the byte is outside the window, which §3 already said.

This is the **prepared input** to such a run, not its result. The capture
itself, and any grading of what it produced, is a human's at the machine;
`ec_timer_capture.py` cannot be run from a cloud runner. The observable set for
the slots that *are* visible is the `vis` column.

## 5. Methods, including what found nothing

| method | region | result |
|---|---|---|
| segment heads from the run's opcodes vs. stub immediates from `task-call-table.csv` | the run, the stub table | **equal** — the claim, compared as two independently derived sets |
| unaligned `12 xx xx` / `02 xx xx` naming any of the run's own addresses | whole 0x40000-byte image | **0 hits** — *not found by this method*, not absent |
| stub immediates landing in `0x8518`–`0x8559` | the 403-entry stub table | the seven in §1, and no others |
| `0x1100` trampoline's stack shape | the stub's own 20 bytes | marker premise settled; landing window `0x1100`–`0x11FF` |
| `descend()` per slot, one level of callee | each slot's target | the write sets in §3 |

The zero-hit row is the one worth reading twice. It is a two-opcode unaligned
scan, and this repository has already found a dispatch mechanism in this image
that such a scan cannot see — the `movc`/`jmp @a+dptr` table at `common 0x7151`
that the caller chain's §1 depends on. The scan constrains where a *direct*
transfer enters the block; it says nothing about a computed one.

## 6. What this file is not

- **No hardware ran.** No register was read, written, or read back, and no
  routine was watched running. §4 is a classification of a write set against a
  window, not an observation. The `0x0490` = `0x0F` reading the caller chain
  cites stays cited from `charge-target-derating.md` §3 and is not restated here
  as this file's own.
- **No rate and no period.** The seven entry points are a count of entries, not
  of times. The tick's own period and the dispatcher's period against the flag
  are the two open ends `charge-target-caller-chain.md` §4 already names, and
  nothing here closes either.
- **No `status:` moves.** Nothing in `ec/annotations/registers.yaml` changes. A
  static decode is not the behavioural evidence a status change needs, and the
  five unnamed targets below are characterised from their committed
  decompiles, not from anything observed.
- **Five targets still have no committed name.** `0xA7C8`, `0xB83B`, `0xB4A8`,
  `0xB5D3` and `0xB737` have no row in `ghidra-functions.csv`; §3 describes what
  each does from the committed `ec/decompiled/bank0/<ADDR>.{asm,c}` and from its
  callees' committed rows. Naming them is a separate change and the finding does
  not depend on it. It was tried here and dropped on a stated rule rather than
  at review time: a row in that CSV only takes effect through
  `build_ec_decompile.py --mode export-only`, and the resulting diff is not
  confined to the five functions' own `.asm`/`.c` — it moves the manifest's
  `annotations_applied`, the annotated-row census `ec/annotations/subsystems.md`
  states in two places, and the export reports. The export is also not runnable
  from a cloud runner whose Ghidra project was committed under a different user
  (`ghidra.util.NotOwnerException: Project is owned by dave`), so the diff could
  not be produced to be judged. Five characterisation lines in §3 are the
  complete result; the naming is a human's or a clean runner's.
- **No upstream submission.** Nothing here is offered to
  `Wer-Wolf/uniwill-laptop` or `tuxedo-drivers`; if a driver behaviour falls
  out of it, the deliverable is a prepared patch and description committed here.

## 7. Reproducing it

```
python3 ec/tools/run_entry_map.py --self-test ec/firmware/GMxMGxx_11.800
python3 ec/tools/run_entry_map.py ec/firmware/GMxMGxx_11.800 --callee-depth 1
python3 ec/tools/run_entry_map.py ec/firmware/GMxMGxx_11.800 --writes-csv
python3 ec/tools/task_call_table.py ec/firmware/GMxMGxx_11.800 --check
bash tools/run-tests.sh ec/tools
```

`task_call_table.py --check` is in that list because this file reads its CSV and
writes nothing: the table the run and the stub table come from is still that
tool's, and still held to the image.
