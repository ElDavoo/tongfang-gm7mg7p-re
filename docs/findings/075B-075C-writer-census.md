# The `0x075B` / `0x075C` writer census — all stores are blind, not read-modify-writes

(2026-10-09, issue #1499. Static reading of `ec/firmware/GMxMGxx_11.800` and
two committed tables, plus mode decoding around each writer read in
`r2 -a 8051`. No capture opened, no EC, no hardware, no Windows.)

Issue #1499 noted that §7 of `docs/findings/0751-writer-census.md` identified
`0x075B` and `0x075C` as registers that "want the same census" — the same
static enumeration of all write sites and classification of access shapes. This
is that census.

**Three writer sites for `0x075B`, two for `0x075C`**, committed as
[`ec/annotations/manual-fan-ctrl-0x075B-writers.csv`](../../ec/annotations/manual-fan-ctrl-0x075B-writers.csv)
and
[`ec/annotations/manual-fan-ctrl-0x075C-writers.csv`](../../ec/annotations/manual-fan-ctrl-0x075C-writers.csv),
derived by
[`ec/tools/census_xdata_writers.py`](../../ec/tools/census_xdata_writers.py) on
every run. Unlike `0x0751`, **all stores are blind stores** — whole-byte writes
without read-modify-write. Not one read-modify-write between them.

## 1. What the census found: all blind stores

A blind store writes the whole byte without having read it, so it is the only
shape that can destroy a bit a host set. `0x075B` and `0x075C` are the register
names `registers.yaml` assigns to `MAIN_FAN_L_DUTY` and `MAIN_FAN_R_DUTY`, the
ones `windows/decompiled/*/ECSpec.cs` publishes to the Control Center as
`ADDR_EC_MAIN_FAN_L/R_DUTY_BYTE` and that `FanInfo.GetEcCpuFanDuty` /
`GetEcGpuFanDuty` read.

| register | writer sites | store instructions | shapes |
|---|---|---|---|
| `0x075B` | 3 | 3 | 3 blind stores |
| `0x075C` | 2 | 2 | 2 blind stores |

**The three writer sites for `0x075B` are `0x87C5`, `0x89E0`, and `0xBB29`.**
Each site carries one store instruction, and each store is a blind write with
`no load` in the mask cell. At `0x87C5`, the accumulator arrives unrelated to
this register. At `0x89E0` and `0xBB29`, the same: no `movx a,@dptr` pending
before the `movx @dptr,a`.

**The two writer sites for `0x075C` are `0x8F0A` and `0x8F11`.** Each carries
one store instruction, and each is a blind store with `no load` in the mask
cell. At `0x8F0A`, there is no prior load. At `0x8F11`, the same.

## 2. What the census did not find

The census found a third site for `0x075C` at `0x87D5` — a `mov dptr,#0x075C`
that is reached by control flow and `classify()` marks as no access in the
window, like the two branch-followed sites for `0x0751` that `walk_flow_follow`
resolves. This site is not a writer site and does not appear in the writers
table; it is listed here because the plan noted it as part of the count. The
distinction is the same §1 of `0751-writer-census.md` draws: a site the
classification gives no direction for is a weaker claim than one that says
`write`, and the two are not interchangeable.

## 3. The conditions each store fires under

`condition` and `condition_evidence` are hand-filled off the listing for later
use. No rows carry a condition assignment yet; the columns exist and are ready
for analysis once the code flow around each store is traced. `host-write-through`
is expected empty for both registers, for the reason the `0x0751` census
records: the host writes `0x075B` and `0x075C` over `ECRR`, which is not a
`MOV DPTR,#0x075B` or `MOV DPTR,#0x075C` site, so no instruction for that path
exists to be found here. **This is "not found by this method", never "the host
does not write it"**, per the same discipline `0751-writer-census.md` §3
states.

## 4. Why all blind stores, and what it means

The one blind store found for `0x0751` at `0xA815` is an exception — twelve of
its thirteen stores are read-modify-writes. For `0x075B` and `0x075C`, the
opposite is true: all stores are blind. `registers.yaml` names both bytes as
`MAIN_FAN_L/R_DUTY`, and the Windows stack reads them for fan duty cycle —
that is the basis of `manual-fan-ctrl-0751.md` §4's assumption that the bytes
hold PWM duty, matched by a live capture in §7 of `0751-writer-census.md`.

A blind store to a fan duty register is the shape that can destroy a bit the
host set, and the EC has done so: every store to `0x075B` and `0x075C` writes
the whole byte. That is the technical fact this census establishes. **Whether
the EC acts on any of these stores at all, how often they run, and whether a
host write persists once stored, are behavioural questions** that belong to
issue #1393, where live observation is the only measure.

## 5. Reproducing it

```console
$ python3 ec/tools/census_xdata_writers.py ec/firmware/GMxMGxx_11.800 0x075B --csv
$ python3 ec/tools/census_xdata_writers.py ec/firmware/GMxMGxx_11.800 0x075C --csv
$ bash tools/run-tests.sh
```

The two CSVs are committed; `--check` is not run per commit until a human
lands the gate, which is `docs/ci/agent-gates-075B-075C-writer-census.patch`.
