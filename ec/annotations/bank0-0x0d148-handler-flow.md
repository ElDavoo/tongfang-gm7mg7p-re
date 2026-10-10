# The `bank0` `0x0D148` handlers as control flow

[`bank-call-audit.md`](bank-call-audit.md) §10 enumerates 15 handler tables. This is one
with 12 cases. §10.5 notes that **no handler's control flow was traced** — only the
dispatch table was decoded. This is that walk.

Everything below is **what the bytes in [`ec/firmware/GMxMGxx_11.800`](../firmware/GMxMGxx_11.800)
decode to**. Nothing here was run on hardware, no register was read back, and no
`status:` in [`registers.yaml`](registers.yaml) changes.

## 1. Reproducing it

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
          0x0860 0x0863 0x0864 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
          0x1C04 0x1C05 0x1C11 0x1C15 0x1C16 0x1C35 0x1C39 0x1C3A --callee-depth 1 --csv \
          > ec/annotations/bank0-0x0d148-handler-arms.csv
```

See [`bank0-0x0d148-handler-arms.csv`](bank0-0x0d148-handler-arms.csv) for the complete walk.

## 2. The dispatch site and cases

Cases `0x06`-`0x39` (contiguous or mostly so). The selector is likely derived from a
charging mode, battery threshold, or thermal state enumeration.

## 3. XDATA addresses

Gate and status registers at 0x0860-0x086B (a cluster of charge/battery-related bytes)
and control registers at 0x1C04-0x1C3A (another control region).

## 4. Callees

Handlers call into routines that appear to manage charge thresholds, balancing, and
thermal limits. These are called with different parameters depending on the case value.

## 5. What this walk does not settle

This walk shows reachable code. It does not determine execution order, actual selector
values, or whether writes are acted upon.

Full details: [`bank0-0x0d148-handler-arms.csv`](bank0-0x0d148-handler-arms.csv).

