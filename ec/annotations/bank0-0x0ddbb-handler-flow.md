# The `bank0` `0x0DDBB` handlers as control flow

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
          0x0860 0x0861 0x0862 0x0863 0x0864 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B --callee-depth 1 --csv \
          > ec/annotations/bank0-0x0ddbb-handler-arms.csv
```

See [`bank0-0x0ddbb-handler-arms.csv`](bank0-0x0ddbb-handler-arms.csv) for the complete walk output.

## 2. The dispatch site and cases

Cases: 0x80-0xFE (16 entries)

## 3. XDATA addresses

Gate and control registers: 0x0860-0x086B (from 0x0D148)

## 4. Callees and control flow

16 cases in high byte range. May share gate cluster with 0x0D148.

See [`bank0-0x0ddbb-handler-arms.csv`](bank0-0x0ddbb-handler-arms.csv) for detailed arm structure, callees, XDATA accesses, and status.

## 5. What this walk does not settle

This walk shows reachable code from each handler entry. It does not determine:
- Whether handlers are called, how often, or in what order
- Selector values and dispatch logic
- Runtime behavior or timing
- Whether writes are acted upon

For full details, consult [`bank0-0x0ddbb-handler-arms.csv`](bank0-0x0ddbb-handler-arms.csv).

