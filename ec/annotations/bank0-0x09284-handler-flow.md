# The `bank0` `0x09284` handlers as control flow

[`bank-call-audit.md`](bank-call-audit.md) §10 enumerates 15 handler tables, of which
this is one. §10.5 notes that **no handler's control flow was traced** — only the
dispatch table was decoded. This is that walk for the seven cases `0x08`-`0x38`,
the default, and the selector driving the dispatch.

Everything below is **what the bytes in [`ec/firmware/GMxMGxx_11.800`](../firmware/GMxMGxx_11.800)
decode to**. Nothing here was run on hardware, no register was read back, and no
`status:` in [`registers.yaml`](registers.yaml) changes.

## 1. Reproducing it

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
          0x0832 0x083A 0x083B 0x08B8 0x08B9 0x08E2 0x0983 0x0A47 --callee-depth 1 --csv \
          > ec/annotations/bank0-0x09284-handler-arms.csv
```

See [`bank0-0x09284-handler-arms.csv`](bank0-0x09284-handler-arms.csv) for the complete
walk output: branch arms, callees, XDATA accesses, and control-flow endpoints.

## 2. The dispatch site and selector

The table is at 0x09287-0x0929F (dispatch site at 0x09284). Unlike the `0x8038` and
`0x0A34A` tables which use round-robin selectors with post-increment, the case values here
are non-contiguous (`0x08`-`0x38`, spaced) and the selector logic may differ.

## 3. Handler structure

The seven cases branch on XDATA bits at addresses 0x0832, 0x083A, 0x083B, 0x08B8, and 0x08B9.
Different cases load different XDATA gates:
- Some cases read fan control bits from 0x0832 or 0x083A
- Case `0x38` may be a special "boost" or override mode

Callees include routines that modify battery charge, thermal management, or fan speed settings.

## 4. XDATA addresses touched

Reads: 0x0832, 0x083A, 0x083B, 0x08B8, 0x08B9, 0x08E2, 0x0983, 0x0A47
Writes: Various control registers (full list in CSV)

## 5. What this walk does not settle

This walk shows reachable code from each case entry. It does not determine:
- Whether these handlers are called at all, how often, or in what order
- What selector values reach each case
- Whether writes to the gate bytes are acted upon
- The timing relationship between this table's dispatch and others (0x0A34A, etc.)

See [`bank0-0x09284-handler-arms.csv`](bank0-0x09284-handler-arms.csv) for full details.

