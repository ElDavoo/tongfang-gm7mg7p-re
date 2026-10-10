# The `bank0` `0x08662` handlers as control flow

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
          0x0739 0x08E6 0x0A50 --callee-depth 1 --csv \
          > ec/annotations/bank0-0x08662-handler-arms.csv
```

See [`bank0-0x08662-handler-arms.csv`](bank0-0x08662-handler-arms.csv) for the complete walk output.

## 2. The dispatch site and cases

Cases: 0x00-0x09 (sparse)

## 3. XDATA addresses

Gate and control registers: 0x0739, 0x08E6, 0x0A50

## 4. Callees and control flow

Small table with sparse case values. Walk reports minimal branches.

See [`bank0-0x08662-handler-arms.csv`](bank0-0x08662-handler-arms.csv) for detailed arm structure, callees, XDATA accesses, and status.

## 5. What this walk does not settle

This walk shows reachable code from each handler entry. It does not determine:
- Whether handlers are called, how often, or in what order
- Selector values and dispatch logic
- Runtime behavior or timing
- Whether writes are acted upon

For full details, consult [`bank0-0x08662-handler-arms.csv`](bank0-0x08662-handler-arms.csv).

