# The `bank0` `0x0F254` handlers as control flow

[`bank-call-audit.md`](bank-call-audit.md) §10 enumerates 15 handler tables. This is one
of the remaining tables. §10.5 notes that **no handler's control flow was traced** —
only the dispatch table was decoded. This is that walk.

Everything below is **what the bytes in [`ec/firmware/GMxMGxx_11.800`](../firmware/GMxMGxx_11.800)
decode to**. Nothing here was run on hardware, no register was read back, and no
`status:` in [`registers.yaml`](registers.yaml) changes.

## 1. Reproducing it

The walk_branch_arms.py tool was seeded on the gate XDATA addresses derived from
the handler windows:

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
          0x0E00 0x0E01 0x0E02 0x0E03 0x0E04 0x0E05 0x0E06 0x0E07 0x0E08 0x0E09 0x0E0A 0x0E0B 0x0EA8 0x0EA9 0x0EAA 0x0EAB 0x0EAC 0x0EAD 0x0EAE 0x0EAF 0x0F60 0x0F61 0x0F62 0x0F63 0x0F64 0x0F65 0x0F66 0x0F67 0x0F80 --callee-depth 1 --csv \
          > ec/annotations/bank0-0x0f254-handler-arms.csv
```

See [`bank0-0x0f254-handler-arms.csv`](bank0-0x0f254-handler-arms.csv) for the complete walk output.

## 2. The dispatch site and cases

Cases: 0x00-0x08 (9 entries)

## 3. XDATA addresses

Gate and control registers: 0x0E00-0x0E0B, 0x0EA8-0x0EAF, 0x0F60-0x0F67, 0x0F80

## 4. Callees and control flow

16-bit threshold values accessed across multiple ranges.

See [`bank0-0x0f254-handler-arms.csv`](bank0-0x0f254-handler-arms.csv) for detailed arm structure, callees, XDATA accesses, and status.

## 5. What this walk does not settle

This walk shows reachable code from each handler entry. It does not determine:
- Whether handlers are called, how often, or in what order
- Selector values and dispatch logic
- Runtime behavior or timing
- Whether writes are acted upon

For full details, consult [`bank0-0x0f254-handler-arms.csv`](bank0-0x0f254-handler-arms.csv).

