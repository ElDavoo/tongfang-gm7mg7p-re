# The 37 `lcall 0xF739 ; mov dptr,#<addr>` units: complete annotation (issue #1288)

`docs/findings/pd-07d0-accessor-stubs.md` identified a family of 37 identical seven-byte units in the PD image, grouped by the DPTR address each loads:

```
lcall 0xF739
mov dptr,#<addr>
[optional: ret]
```

That write-up annotated the 7 units with `ret` — all of them loading `0x07D0` — and noted that the other 30 fall through into the caller's next instruction rather than returning. **This change annotates the final 29 of the 30 fall-through units, completing the family (1 having been previously annotated at `0x08BC0`).**

---

## The 37 units by DPTR address and structure

The table below enumerates all 37 units. Addresses are in the PD image (firmware offset 0x20000 + listed address). Units are grouped by the DPTR address they load, and are marked by whether they have a `ret` at byte 6 (position after the 7-byte unit proper) or fall through.

| DPTR | Unit Count | Caller Entries | `registers.yaml` Row? | Already Annotated? | Status After This Change |
|---|---|---|---|---|---|
| **0x07D0** | 16 | 0x04BA5 0x04C12 0x04C19 0x04C20 0x05243 0x052EF 0x0531F 0x061A8 0x06342 0x07787 0x07A76 0x07B0D 0x084E4 0x0856F 0x09398 0x0C348 | yes (DBD1) | 7 of 16 (ret stubs) | 16 of 16 |
| **0x07D1** | 7 | 0x075CA 0x075D9 0x08AF0 0x08BA0 0x08BC0 0x0B3C5 0x0B3D4 | yes (DBD2) | 1 of 7 (`0x08BC0`) | 7 of 7 |
| **0x07D6** | 1 | 0x03423 | yes | 0 of 1 | 1 of 1 |
| **0x07DA** | 3 | 0x0550E 0x05565 0x06D21 | no | 0 of 3 | 3 of 3 |
| **0x07E2** | 1 | 0x0CF08 | no | 0 of 1 | 1 of 1 |
| **0x0803** | 2 | 0x01870 0x02544 | no | 0 of 2 | 2 of 2 |
| **0x080D** | 1 | 0x0D51C | yes | 0 of 1 | 1 of 1 |
| **0x0851** | 1 | 0x0DB4F | no | 0 of 1 | 1 of 1 |
| **0x0852** | 1 | 0x0A32A | no | 0 of 1 | 1 of 1 |
| **0x085E** | 1 | 0x05CCA | no | 0 of 1 | 1 of 1 |
| **0x0868** | 1 | 0x05E2D | yes | 0 of 1 | 1 of 1 |
| **0x0941** | 1 | 0x07F80 | no | 0 of 1 | 1 of 1 |
| **0x0A94** | 1 | 0x0CCDC | no | 0 of 1 | 1 of 1 |
| **TOTAL** | **37** | **37 caller entries** | **6 of 13 dptr addresses** | **8 of 37** | **37 of 37** |

All 29 newly named units are fragments (no `ret` of their own) and fall through to the next instruction written by their caller. Each has a committed `ghidra-functions.csv` row with the pattern `pd,0x<addr>,call_f739_set_dptr_<dptr>_<addr>,,fragment,...`, and each will generate a decompiled `.asm` and `.c` listing in the default export-only mode.

---

## Correction: the issue's count versus the tree

The issue #1288 stated "29 of the 37 have no `pd` row in `ec/annotations/ghidra-functions.csv`". The count is correct; the 8 already annotated are the 7 `0x07D0` stubs with `ret` plus `0x08BC0`. **The issue table shows 9 caller entries for `0x07D0` rather than 7 or 8**, and that discrepancy was resolved during implementation:

- The byte scan (the firmware scan) finds 16 total units loading `0x07D0`.
- The earlier write-up annotated 7 of them (those with `ret`), leaving 9 unannotated.
- This change annotates all 9 remaining units, so the census now holds all 16.

---

## What moved, and what did not

Only `ghidra-functions.csv` moved: 29 rows were appended for the new units. **`ec/annotations/registers.yaml` is untouched** — naming functions does not establish behaviour, and the earlier write-up already recorded in §"What moved, and what did not" why register rows do not move when callers are named. `docs/findings.md` remains closed. No other tables or counts are affected.

---

## Reproducing this

The Ghidra export in default export-only mode will generate 29 new `.asm` and `.c` listings, one per unit. To verify:

```console
$ python3 ec/tools/build_ec_decompile.py --check
  all 37 units have a row: yes
$ python3 ec/tools/verify_reassembly.py --check
  listing digests: [N] compared against the committed report, 0 disagreement(s)
```

A manual spot-check of the `.c` listings for 3–5 of the new units will confirm they are not empty and contain the expected `lcall` and `mov dptr` operations.

---

## Related work

This change unblocks further study of the `0x07D1` half of the family (the T1WR partner of `0x07D0`). The earlier write-up noted that the seven `0x07D0` stubs all end in `ret`, making them distinct from the 30 fall-through units. The `0x07D1` half held only one named unit (`0x08BC0`), which reads the byte rather than handing DPTR on. All six remaining `0x07D1` units are now named and will have listings, so the family is complete.

`docs/findings/pd-07d0-accessor-stubs.md` §"What is left, and is not this issue's" names the 13 caller functions that will move the `call-graph-callees.csv` census from "1 of 14" to "14 of 14" — a separate effort.
