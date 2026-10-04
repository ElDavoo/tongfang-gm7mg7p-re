# The charge-derating counters are cleared by the boot path, not persisted (issue #90)

`ec/annotations/charge-target-derating.md` §3 carried the question open: *does
`stress` survive an EC reset?* **It does not.** `0x09C7`–`0x09CA` are plain
XDATA RAM, the EC's reset path zeroes them, and no direct-encoded site outside
the charge-target routine writes them. That much was already half on record —
§3 noted `0xB141`'s else-branch clearing all four under one condition, and
[`reset-vector-dptr-targets.md`](reset-vector-dptr-targets.md) had decoded a
boot-time clear covering `0x0100`–`0x0FFF`. This is the question those two
half-answers leave open, closed against the committed image, with a tool that
re-derives it on every run.

> **Calibration, before the numbers.** Everything below is a static read of
> `ec/firmware/GMxMGxx_11.800`. No EC was powered, no register was read back,
> and none of these bytes is host-readable anyway (the third bullet of §"What
> this does not settle"). The claim is *the reset path clears these four bytes
> and no directly-encoded site writes them afterwards* — not *nothing can
> persist them*. The population that would falsify the second reading is named,
> and searched, in that same section.

## The answer, per byte

```console
$ python3 ec/tools/boot_xdata_sites.py 0x09C7 0x09C8 0x09C9 0x09CA
0x09C7  cleared          direct sites: 2  [bank0=2]
0x09C8  cleared          direct sites: 2  [bank0=2]
0x09C9  cleared          direct sites: 9  [bank0=9]
0x09CA  cleared          direct sites: 5  [bank0=5]
```

`cleared` is this tool's word for a specific thing: **the last instruction the
boot path executed that stored to this byte stored `0x00` there.** It is read
off an execution of the firmware's own instructions, not off a scan — see §How
the verdict is derived. The direct-site column is delegated to
`ec/tools/trace_xdata_refs.py`, so it is the same measurement every committed
XDATA table in this repository is made of.

## How the verdict is derived

`trace_xdata_refs.py` cannot answer "is this byte cleared at boot". Its own
header says why: it decodes what a direct site does and **stops at every DPTR
handoff**, which is exactly the shape a range clear takes — the clear builds
DPTR in a register, walks it, and stores. A `90 hi lo` scan cannot see it.

So `ec/tools/boot_xdata_sites.py` executes the boot path instead. Three
properties of its answer are worth stating, because each is a way the tool
could have been wrong:

**The routine set is read off the vector's bytes, not written down.**

```console
$ python3 ec/tools/boot_xdata_sites.py --report
boot walk from the reset vector 0x0000 over a 262144-byte image:
  routines reached: 4
    0x110A
    0x158E
    0x0F75
    0x1594
```

`common 0x0000` is a single `ljmp 0x0070`; `0x0070` calls four routines and
tail-jumps. This matters more than it looks. **`0x0F75` is a second XDATA
clearer on the same path** — `ec/annotations/ghidra-functions.csv` names it
`clr_xdata_0000_00ff_iram_20_bf_xdata_9000_97ff`, and its own annotation row
already measures the three loops: XDATA `0x0000`–`0x00FF`, **internal** RAM
`0x20`–`0xBF`, and XDATA `0x9000`–`0x97FF`. Nothing in the reset vector's bytes
points at it as an XDATA clearer; that row is where the ranges are established.
A tool that enumerated the clearers by hand and found only `0xD96C` would have
been **right about the counters and wrong about the boot path** — and would have
said so.

That same row settles the `0x0070` body independently: *"sets the stack pointer
to 0xC0, writes 0x3F to XDATA 0x1001, then calls 0x110A … followed by 0x158E,
0x0F75 and 0x1594. It then copies XDATA 0x2006 to XDATA 0x0004 … and
tail-jumps to 0x00CF"* — which is this walk's step order, reached here by
executing the bytes rather than by reading the annotation.

**The stored set is executed, not asserted.** The four counters' `cleared`
verdicts fall out of walking the same instructions
`reset-vector-dptr-targets.md` walked by hand. That file's figure — 3,837
bytes stored, `0x07FD`–`0x07FF` stepped over — re-derives here from the same
committed bytes, and the tool's `--self-test` holds both against it.

**A routine that clears the stack stops the walk there, and says so.**
`0x0F75` zeroes internal RAM `0x20`–`0xBF` — the range its annotation row
measures as 160 bytes — and `0x81` is SP, which is inside it. So by its `ret` at
`0x0FA5` the stack pointer reads 0. A faithful interpreter pops the return
address out of cleared IRAM and jumps into whatever those bytes decode as,
which is not a call this vector made. The tool stops, names the address and the
reason, and still reports the routine's stores — it halts **on** that `ret`,
which `0F75.asm` places after all three of the routine's clearing loops, so
every store `0x0F75` makes is already recorded when the walk stops. It reports
this on every `--report` run rather than swallowing it:

```
  stopped at 0x0FA5, return address not followed: 0x0F75 cleared SP (it
    zeroes IRAM 0x20-0xBF, which includes 0x81), so this `ret` pops the
    return address out of cleared IRAM; the stores above are complete, and
    where control goes next is not established here
```

**What the boot path leaves behind**, from the same run:

| range | bytes | written by |
|---|---|---|
| `0x0000`–`0x07FC` | 2,045 | `0x0F75`'s first XDATA loop, then `0xD96C` over `0x0100`+ |
| `0x0800`–`0x0FFF` | 2,048 | `0xD96C` |
| `0x1001` | 1 | the vector's own `mov A,#0x3f` |
| `0x9000`–`0x97FF` | 2,048 | `0x0F75`'s second XDATA loop |
| `0x07FD`–`0x07FF` | 3 walked, **not** written | the skip window `reset-vector-dptr-targets.md` established |

The vector writes one byte outside those ranges and it is not one of the four:
`0x0073`–`0x0078` puts `0x3F` at XDATA `0x1001`. Further along, `0x0085`–`0x008F`
reads a byte from XDATA `0x2006` and writes it to `0x0004` — **after** `0x0F75`
has already cleared `0x0004`. So `0x0004` is the one address in the cleared
low page that does not end the boot holding a zero, and the tool reports it as
`written-unknown` rather than `cleared`: it wrote a byte there, and this walk
cannot say what value. That distinction is why the verdict vocabulary has five
tokens and not two.

## The direct-encoded sites are all in one routine

`trace_xdata_refs.py`'s site census, delegated into every row above, puts all
eighteen sites in `bank0` between `0xB149` and `0xBD9E` — inside `0xB12C`'s
routine and its helpers:

| address | direct sites | what the scan shows at each site |
|---|---:|---|
| `0x09C7` | 2 | cleared in the `0x0490` gate below; incremented at `0xB211` |
| `0x09C8` | 2 | cleared in the same gate; incremented at `0xB234` |
| `0x09C9` | 9 | `0xB151`, the `0x0490` gate's own clear, writes two bytes walking into `0x09CA`; `0xB241` hands DPTR to `0xBCF5`; `0xB25C` and `0xB272` load the address and the scan's window ends before any `movx`; `0xB2F7`, `0xB319`, `0xB345`, `0xBD91`, `0xBD9E` read it |
| `0x09CA` | 5 | read at five sites |

Two of the ten read sites carry an annotation row — `bank0,0xBD8B`
`tier_250_eligible` and `bank0,0xBD98` `tier_200_eligible` — and the other eight
carry none. So **this write-up does not call all ten read sites tier
compares**: what the scan establishes for every one of them is the direction,
read. Which comparison each makes is the reading in
`charge-target-derating.md` §1's helper table, not a measurement made here, and
the eight unannotated sites are left as reads whose comparison this does not
identify.

The three sites the scan leaves unresolved are worth their own note rather
than being smoothed into "incremented". `trace_xdata_refs.py` reports `0xB241`
as a **DPTR handoff**: the site loads the counter's address and calls a helper,
so the scan does not resolve what happens inside. That helper is named —
`ghidra-functions.csv` has `bank0,0xBCF5` `stress_headroom`, annotated
*"computes 65000 minus the stress counter minus 1, so the caller can skip the
increment on borrow"* — so what this site does with `0x09C9` is read here from
a committed annotation rather than from the bytes. The direction at `0xB241` is
therefore **not** established by this scan either way, and where the increment
itself lands is not settled here.

`0xB25C` and `0xB272` are the same class and are named here rather than left
out of the row: the scan reports **"no movx found in the decoded window"** for
both, because each site's window ends on a flow opcode before any `movx`. Over
those two addresses `disasm8051.py` shows each one loading `0x09C9` into DPTR,
clearing `A`, writing the IRAM byte `0xf0` and branching away — `0xB263` is a
`sjmp 0xB280`, and both arms of `0xB276`'s `jnc` write `0xf0` before reaching
`0xB280`. So neither site stores through the DPTR it loads. **That is what
`disasm8051.py` over these addresses resolves and what the scan does not give:**
whether the loaded DPTR is consumed by whatever the branch reaches next is not
settled by these two sites, and this write-up asserts no direction for either
beyond the absence of a `movx` in the decoded window.

The classification is `ec/decompiled/bank0/B12C.c`, which is committed: its
`0x0490`-bit-1 branch is

```c
  if ((DAT_EXTMEM_0490 >> 1 & 1) != 1) {
    XDATA_09C7 = 0;
    XDATA_09C8 = 0;
    XDATA_09C9 = 0;
    XDATA_09CA = 0;
    return;
  }
```

so the routine's own reading is that a counter which is not accumulating is
zeroed rather than left to drift. **Every one of those sites is in `bank0`** —
none in `common`, `bank1` or `pd-image` — and that is a statement about the
direct encoding only, which is §"What this does not settle"'s subject.

## What this retires, and in which direction

`charge-target-derating.md` §3's standing advice was *"don't treat an EC reset
as a way to undo the derating."* That advice survives, and the sharper form is
**stronger, not weaker** — it was right for the wrong reason, and the correction
is in place with the answer:

- **An EC power loss does reset the counter.** It is plain XDATA RAM and the
  reset path zeroes it. The derating would fall back to the cycle-count tier —
  450 cycles on this pack → 200 mV/cell → 16600 mV against the 16400 mV
  `charge-target-derating.md` §2 read on the machine. That target and the cycle
  count are cited live readings from that file; **the counter clearing is not**,
  and is the static claim above.
- **It climbs back.** The counter gains +1/h below 30 °C, +3/h at 30–40 °C,
  +7/h above, and only while the pack is above 4.1 V/cell. The 250 mV tier
  needs `stress > 18144`: roughly 2,592 h above 40 °C, 6,048 h at 30–40 °C, or
  18,144 h below 30 °C of accumulated high-voltage time. On a machine kept
  plugged in near 40 °C that is months.

So the derating **is not a latch an EC reset clears**. It is a function of
accumulated high-voltage time, and a reset returns it to zero rather than
removing it. The advice becomes: an EC reset does reset the counter, and it
will climb back. What it does **not** establish is what causes the reset in
the first place — and on this machine an EC reset is not a user-facing
operation at all, which is the practical reason the old advice was worth
stating in the first place.

## What this does not settle

- **Indirect and DPTR-handed stores are not searched.** A pointer built in
  registers, a base-plus-offset access, or a DPTR handed to one of the seven
  parameterised "zero N bytes at DPTR" helpers (`0xB963`, `0xEDE1`, `0xEE58`,
  `0xF07C`, `0xF099`, `0xF17B`, `0xF4AD`, per
  [`../../ec/annotations/xdata-0440-readers.md`](../../ec/annotations/xdata-0440-readers.md)
  §7.5) is invisible to both a `90 hi lo` scan and to this walk. Whether any of
  those seven is handed `0x09C9` is **not established either way** — it is a
  call-graph question this tool does not attempt, and it is the largest
  remaining hole in the answer.
- **Nothing is claimed about `0x07FD`–`0x07FF`.** They are the three bytes the
  boot clear deliberately steps over, which
  [`xdata-07fd-07ff-witness-triple.md`](xdata-07fd-07ff-witness-triple.md) is
  about. This tool reports them as `spared` and says nothing further.
- **The counter cannot be read on this machine at all.** `0x0800`–`0x0DFF` is
  outside the host's `0xFE410000` window, so there is no possible live test of
  this claim here — not for a CI runner and not for a human at the machine,
  without a different access path. "Disconnect the battery, boot, and read the
  charge target" would measure the *derating tier*, which is a different claim
  from the counter's persistence, and is not needed to answer this one.
- **The PD image's XDATA map.** A `0x09C9` in `pd-image` would be a different
  program's byte, and there is none — but this write-up does not attempt a
  general proof that the PD image cannot be a second maintainer.
- **No `registers.yaml` row moved.** `0x09C7`–`0x09CA` have no row today, and
  this is about *lifetime across a reset*, not about whether the EC touches the
  bytes. Adding rows would mean inventing a `status:` for four bytes the host
  cannot read, which is the overclaiming CLAUDE.md's calibration rule forbids.
- **Nothing was observed on hardware.** Every verdict is a static execution of
  committed bytes.

## Reproducing this

All of it from committed inputs, no Ghidra and no hardware:

```console
$ python3 ec/tools/boot_xdata_sites.py --report          # the routine set, the stops, the store set
$ python3 ec/tools/boot_xdata_sites.py 0x09C7 0x09C8 0x09C9 0x09CA
$ python3 ec/tools/boot_xdata_sites.py --self-test      # known answers, then the refusals
$ python3 ec/tools/boot_xdata_sites.py --csv --check    # reproduces ec/annotations/boot-xdata-sites.csv
$ python3 -m unittest discover -s ec/tools -p 'test_boot_xdata_sites.py'

# the direct-site half, delegated rather than re-derived
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x09C7 0x09C8 0x09C9 0x09CA --counts-only

# the reset vector and the two clearers, by hand
$ cat ec/decompiled/common/0070.asm ec/decompiled/common/0F75.asm
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D96C --runtime 0xD96C -n 24

# the routine the counters live in, and the branch that zeroes them
$ grep -n -A6 'DAT_EXTMEM_0490 >> 1' ec/decompiled/bank0/B12C.c

$ bash .github/scripts/agent-gates.sh
```

`ec/annotations/boot-xdata-sites.csv` is the tool's output, one row per address
the boot walk touched, carrying the verdict, the byte it left there, and the
delegated direct-site count with its region split. It is generated and
`--check`ed, never hand-edited.

## Not in any gate, for the reason

`.github/scripts/agent-gates.sh` and the rest of `.github/` are pipeline files,
and this branch's token has no `workflow` scope, so a branch touching them fails
at the very end. `boot_xdata_sites.py` is therefore **runnable and cited
standalone**, the way [`pd-image-census.md`](pd-image-census.md) §"Not in any
gate, for the reason" records for that census. No `docs/ci/*.patch` either,
for the reason that section gives.

What the cheap tier *does* pick up is `python3 -m py_compile` over
`ec/tools/*.py`, which only proves the new files compile. The suite is found by
`bash tools/run-tests.sh`'s `find`, and no gate calls that runner.

## Follow-ups this opens

- **Do any of the seven parameterised "zero N bytes at DPTR" helpers get
  `0x09C9` handed to them?** The largest hole in the answer above, and a
  call-graph question rather than a scan.
- **What restores SP after `0x0F75` clears it?** The reset path zeroes the
  stack pointer on its way through, and this write-up does not say where
  control goes when `0x0F75` returns. The XDATA stores are unaffected; the
  control flow after them is open.
- **Should `0x09C7`–`0x09CA` get `registers.yaml` rows at all**, given they are
  host-unreadable? The answer here is "not yet", and that is worth revisiting
  if a Linux driver ever needs to reason about the tier.