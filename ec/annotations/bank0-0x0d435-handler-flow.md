# The `bank0` `0x0D435` handlers as control flow

[`bank-call-audit.md`](bank-call-audit.md) §10 enumerates 15 handler tables. This is the
largest: 24 cases spanning `0x90`-`0xDD`. §10.5 notes that **no handler's control flow
was traced** — only the dispatch table was decoded. This is that walk.

Everything below is **what the bytes in [`ec/firmware/GMxMGxx_11.800`](../firmware/GMxMGxx_11.800)
decode to**. Nothing here was run on hardware, no register was read back, and no
`status:` in [`registers.yaml`](registers.yaml) changes.

## 1. Reproducing it

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
          0x0046 0x06E6 0x08EB 0x0E00 0x1102 0x1106 0x1B01 0x1B05 --callee-depth 1 --csv \
          > ec/annotations/bank0-0x0d435-handler-arms.csv
```

See [`bank0-0x0d435-handler-arms.csv`](bank0-0x0d435-handler-arms.csv) for the complete walk.

## 2. The dispatch site and cases

The table has 24 cases (non-contiguous, gaps in case values). Cases are `0x90`, `0xA8`,
`0xB9`, `0xC1`, `0xC2`, `0xC9`, `0xCD`, `0xCE`, `0xD0`, `0xD1`, `0xD2`, `0xD3`, 
`0xD5`, `0xD6`, `0xD7`, `0xD8`, `0xD9`, `0xDA`, `0xDB`, `0xDC`, `0xDD`, and others.

The large case span and non-contiguity suggest a `switch` statement with many branch labels
compiled from the image's C source.

## 3. XDATA addresses touched

The walk identifies accesses to:
- 0x0046, 0x06E6, 0x08EB, 0x0E00: Gate XDATA or status registers
- 0x1102, 0x1106, 0x1B01, 0x1B05: Configuration or control values
- Additional addresses per case (see CSV)

## 4. Callees

Multiple callees are invoked by different cases, suggesting:
- Shared utility routines for power management
- Case-specific branches into separate subsystems (EC clock, regulator control, etc.)

## 5. What this walk does not settle

This walk shows reachable code. It does not determine:
- Which selector values the EC actually dispatches to
- Execution order or frequency
- Whether writes are acted upon at runtime
- The relationship between this table and others (0x0A34A, 0x09284, etc.)

Full control-flow details are in [`bank0-0x0d435-handler-arms.csv`](bank0-0x0d435-handler-arms.csv).

