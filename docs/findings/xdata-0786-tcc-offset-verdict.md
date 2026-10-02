# `0x0786` is a CPU TCC offset: the EC's own bytes decide the naming conflict

(Issue #702. Static reading of the committed firmware
`ec/firmware/GMxMGxx_11.800` plus the committed decompilations under
`ec/decompiled/`. No laptop, no EC and no Windows machine is involved: every
address below is re-derivable from that image with the commands in §7, and
nothing here is a live test of the byte.)

## The claim

**Of the four direct `MOV DPTR,#0x0786` sites the image holds, two read the
byte behind a `jnb` on bit 7 and then overwrite an already-computed TCC target
with `0x0786 & 0x7f`; the other two store a cleared accumulator in an init
pass. Nothing on any of the four builds an address out of the byte, and
nothing adds to it.**

That is the answer to the issue's question, and it is a reading of the
instructions rather than of the function names around them: upstream
`uniwill-laptop`'s `EC_ADDR_FAN_DEFAULT` with `FAN_CURVE_LENGTH 5`
(`uniwill-acpi.c` lines 254-255 at `5a24248`, quoted in
`upstream-excerpt.txt`) describes a five-element array of fan-curve defaults,
which needs the byte to *index* something and to be added to a base. Neither
happens here. The EC treats `0x0786` as the CPU TCC offset — which is what the
DSDT (`APTC:7`/`APTN:1`, `evidence/acpi/dsdt.dsl:52219-52220`) and
`MyFanManager_RamFan1p5.SetCpuTccOffset` already said, and what ECSpec's
`ADDR_L1_PWM_DEFAULT_MYFAN3` and the upstream name disagree with. §5 is where
that disagreement gets its complication: the same five bytes are read the
other way too, by the same service version.

`0x0786` **stays `present-untested`** in `ec/annotations/registers.yaml`. §6
is what that costs and why nothing here moves it.

## 1. The four sites, and the two denominators

Two numbers are attached to this address in the tree and they are not the same
number. Both are printed by tools rather than asserted here:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0786 --counts-only
0x0786: 4 direct MOV DPTR site(s)  bank0=4

$ python3 ec/tools/census_xdata_writers.py ec/firmware/GMxMGxx_11.800 0x0786
0x0786: 2 writer site(s) and 2 read-only site(s) of 4 found by sites_for()
  2 store instruction(s): blind-store 2
```

Four is what `registers.yaml` records as `static_refs_main_ec: 4`, and
`check_register_counts.py` re-derives it from the image.

Ten is what `ec/annotations/xdata-registers.csv` records for the same address
(`refs=10, read=8, write=2, 4 readers, 2 writers, 6 functions`). **Ten is not
a superset of four and not a second opinion on it.** It counts occurrences of
the address in decompiled *text*, and the six `.c` files the census names hold
it more than once each because Ghidra split one contiguous run of code across
four exported functions. Stripping the comments and counting the symbol, the
per-file tally is:

```console
$ python3 - <<'EOF'
import sys, re
sys.path.insert(0, 'ec/tools')
import xdata_register_map as m
total = 0
for f in ('9334', '93FE', '93FF', '948D', 'ACB4', 'CC64'):
    body = m.strip_comments(open(f'ec/decompiled/bank0/{f}.c').read())
    n = len(re.findall(r'\bCPU_TCC_OFFSET\b', body))
    print(f, n); total += n
print('total', total)
EOF
9334 2
93FE 2
93FF 2
948D 2
ACB4 1
CC64 1
total 10
```

Eight reads and two writes, over four physical sites. `ec/decompiled/index.csv`
holds the size that starts it: `0x93FE` is **one** instruction with no `ret`
of its own, and `0x93FF` and `0x948D` are separate exports over the
instructions it flows into — `0x93FE` + 1 is `0x93FF`, `0x93FF` + 119 is
`0x9476`, and `0x948D` + 34 is `0x94AF`, so the three tile one contiguous run
with no gap. `0x9334`'s own listing ends at `0x948B`, the instruction
immediately before `0x948D`. The `& 0x7f` pair is therefore *inlined* into four
exported `.c` files and the two stores appear once each in the two init
routines. Same instructions, four accounts.

The four physical sites are `0x9492` (read), `0x94A0` (read), `0xAD81`
(store), `0xCCA9` (store).

## 2. The sequence that decides it

`ec/decompiled/bank0/948D.asm`, which is the machine code and is right where
the decompiled C is a reading of it:

```
9492     90 07 86 mov      DPTR, #0x786
9495     e0 - -   movx     A, @DPTR
9496     30 e7 11 jnb      0xe7, 0x94aa
9499     90 07 41 mov      DPTR, #0x741
949C     e0 - -   movx     A, @DPTR
949D     30 e0 0a jnb      0xe0, 0x94aa
94A0     90 07 86 mov      DPTR, #0x786
94A3     e0 - -   movx     A, @DPTR
94A4     54 7f -  anl      A, #0x7f
94A6     90 0a 4a mov      DPTR, #0xa4a
94A9     f0 - -   movx     @DPTR, A
```

Four things follow, and none of them depends on a name having been chosen
somewhere earlier.

**Bit 7 is an enable, not data.** It is tested with `jnb` before anything
else, and it is stripped with `anl a,#0x7f` before the magnitude is used. A
fan-curve array element has no reason to reserve its top bit for a gate that
gates itself. This is the `APTC`(7)/`APTN`(1) split the DSDT's `ECMG` field
list declares at `evidence/acpi/dsdt.dsl:52219-52220`, arrived at from the EC
side rather than from the ASL.

**There is a second gate, and the three-way naming disagreement never mentions
it.** `AP_OEM` (`0x0741`) bit 0 has to be set too, or the branch at `0x94AA`
skips the whole thing. That is the bit
`MyEcCtrl.Set_APExistToEC` writes (`windows/decompiled/v3.1.39.0/GCUService/MyECIO/MyEcCtrl.cs`),
and `0x0741` is the byte the vendor deliberately parks clear for its fan-table
handshake and sets again afterwards. The offset is only applied when the AP
exists.

**The value replaces a computed TCC target; it indexes nothing.** `0x0A4A`
already holds a byte `select_table_byte_against_044f` picked out of a CODE
table. `0x0786 & 0x7f` *overwrites* it at `0x94A9`. There is no addition, no
comparison and no address built out of the byte — which is exactly what
`EC_ADDR_FAN_DEFAULT` as the base of a `FAN_CURVE_LENGTH 5` array would
require.

**It lands in the TCC path.** The routine falls into `0x94AF` with no `ret` of
its own, and `store_r7_to_098c_and_0463` writes `0x098C` and `0x0463 | 0x80`
(`ec/decompiled/bank0/94AF.asm`). `0x098C`, `0x0A4A` and `0x0463` have no
entry in `registers.yaml`; §6 says what that does and does not block.

## 3. The link to the per-mode TCC defaults

The strongest single piece of evidence is that **one routine seeds the
per-mode TCC defaults and then lets `0x0786` override the selected one.**

`ec/decompiled/bank0/9334.asm` — `seed_tcc_defaults_from_ba36` — writes
`0x07D8`, `0x07D9` and `0x07DA` at `0x93B1`, `0x93BC` and `0x93C9`, three
addresses `registers.yaml` already carries as `MODE_TCC_OFFSET_DEFAULTS`
(the Gaming/Office/Turbo TCC offsets). Its listing then runs on for another
195 bytes and stops at `0x948B`, immediately before the block of §2:

```
93AE     90 07 d8 mov      DPTR, #0x7d8
93B1     f0 - -   movx     @DPTR, A
...
948B     74 03 -  mov      A, #0x3
948D     93 - -   movc     A, @A+DPTR     <- code_byte_to_0a4a_then_push_r7
```

So the routine that fills the per-mode defaults is the same routine whose
selected default `0x0786` then replaces, under two gates, with a seven-bit
magnitude. That is the answer to the issue's "which reading the EC's own code
supports", and it does not rest on the three names the census happened to
attach.

The name `seed_tcc_defaults_from_ba36` was chosen by an earlier hand-decode;
what it rests on is this.

## 4. What seeds it, what indexes what, what consumes it

Stated in the shape the issue asks for, all four from the committed listings:

| question | answer, and where |
|---|---|
| which routine seeds it | none, by the direct scan. The two writers are init passes that store zero (`0xAD81`, `0xCCA9`, §5). Per-mode defaults come from `0x9334`, which does not write `0x0786` |
| what indexes what | nothing indexes `0x0786`. The temperature bracketing is on the *other* side: `0x93FF` compares `GPU_TEMP` (`0x044F`) against byte 0 and byte 1 of a CODE table and picks a byte out of it. `0x044F` is `confirmed-working` in `registers.yaml`; the table is in CODE, not at `0x0786` |
| what consumes it | `0x948D` → `0x94AF` → `0x098C` and `0x0463 \| 0x80` |
| is anything on the path temperature-shaped | yes, the *path* is: the value `0x0786` overwrites was selected by a `GPU_TEMP`-bracketed CODE table. The *byte itself* is not temperature-indexed — that is the distinction the fan-curve reading would erase |

## 5. The writers, and the `0x0786`-`0x078D` block

Both writers are blind stores of a cleared accumulator, in the same clear run
that zeroes the byte above:

```
AD7C     e4 - -   clr      A          CCA4     e4 - -   clr      A
AD7D     90 07 87 mov      DPTR, #0x787  CCA5  90 07 87 mov      DPTR, #0x787
AD80     f0 - -   movx     @DPTR, A      CCA8  f0 - -   movx     @DPTR, A
AD81     90 07 86 mov      DPTR, #0x786  CCA9  90 07 86 mov      DPTR, #0x786
AD84     f0 - -   movx     @DPTR, A      CCAC  f0 - -   movx     @DPTR, A
```

`0xACB4` (`reset_xdata_flags_and_07d5_to_ff`) and `0xCC64`
(`init_06e6_1_clear_0743_07c5_and_07d5_ff`) are both whole-machine or
power-on init passes. This is what makes the 2026-09-23 `live` reading of
`0x00` unremarkable rather than surprising: it is a cleared byte in a clearing
routine, in the state the default leaves it in.

**ECSpec's `ADDR_L1..L5_PWM_DEFAULT_MYFAN3` is the same wrong name by another
road, and the block is read both ways.** The five MYFAN3 constants are
`1926`-`1930`, i.e. `0x0786`-`0x078A`; `ADDR_L1..L5_PWM_DEFAULT_MYFAN2` is a
second five-byte block at `1929`-`1933`, i.e. **`0x0789`-`0x078D`**
(`ECSpec.cs`, both sets), so the two blocks **overlap by two bytes** — `0x0789`
and `0x078A` are the MYFAN3 block's last two and the MYFAN2 block's first two.

`0x0786` is read as a TCC offset *and* as a five-element curve in the same
service version, and this write-up does not settle which the vendor meant.
`MyFanManager_RamFan1p5.SetCpuTccOffset` writes `1926` as `value | 0x80`, the
shape §2 reads. But `GetFanTablePWMDefault` in `MyFanManager_QC.cs`,
`MyFanManager_Intel.cs` and `MyFanManager.cs` reads `1926`-`1930` into an
`int[5]` and returns it, each class assigns the result to a `DefaultPWM` field
at the top of its init path, and `MyFanManager_QC.cs` then consumes
`DefaultPWM[0]` through `DefaultPWM[4]` as PWM values (`DefaultPWM[0] / 2` and
so on) — the service's own `ec-callsites.csv` books those reads. So the block
is live as a default-PWM curve here, not a dead name.

That does not move the EC-side verdict, which rests on the `0x9492`-`0x94A9`
listing: nothing in the *EC* treats `0x0786` as a base, whatever the service
that fronts it believes the five bytes mean. It does mean the two readings
collide on the same addresses in one shipped build, and that is a real
unresolved conflict in the vendor stack rather than a stale constant beside a
live method. Which reading is intended — a TCC offset the service happens to
also seed from a curve, or one address doing two jobs — is not answerable from
the committed decompilations, and nothing here claims to answer it.

`0x0787` is the byte ECSpec calls `ADDR_L2_PWM_DEFAULT_MYFAN3` and it has five
direct sites; `0x0788` is `CTWA` in the DSDT and has four. `0x0789` and
`0x078A` have **no direct `MOV DPTR` site by the scan in §7**, which is "not
found by this method" and not "unused" (§6). Those are the two bytes a
five-element array at `0x0786` would need past `0x0788`, and under the
corrected range they are exactly `ADDR_L1`/`ADDR_L2_PWM_DEFAULT_MYFAN2` — the
fan reading's own constants name them, which is a sharper reason to keep the
question open than the scan's silence was. The rest of the `0x0786`-`0x078D`
block is a separate question this write-up stops short of, and
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` §4 item 4 still asks
for it.

## 6. What this does not establish

The honest ceiling, and it is the same one every count in this tree is held
to.

**`0x0786` stays `present-untested`.** Nothing here is a live observation of
what the EC does with the byte. What is established is the static shape: which
routine reaches the byte, that the value replaces rather than indexes, and
that the consuming path is temperature-*shaped* without the byte being
temperature-*indexed*.

**The `live` source in the entry settles nothing.** The 2026-09-23 capture
records `0x00` (`evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt`).
Per `jnb 0xe7` at `0x9496`, a `0x00` byte is one the EC *ignores entirely* —
the branch is not taken — so that observation is **consistent with** this
reading and confirms nothing about behaviour. It is a quiet value in one
window, in the state a clear run leaves it in.

**"Four sites" means four by these methods.** A store through a run-time-built
DPTR is invisible to both `scan_refs.py` and `trace_xdata_refs.py`, and
`find_indirect_xdata.py --page 0x07` resolves none of its five anchored bank0
`movx @Ri` sites — 91 of 91 across the image are unresolved, every one of them
"no `P2` write in the window", against `mov p2,#imm` occurring 0 times in this
image. That is a fact about the scan's form, not about the byte.

**What a live test would settle, and it is a human's step.** Write `0x0786`
with bit 7 set — and `0x0741` bit 0 set, or the second gate skips the whole
branch — hold it, and read `0x098C` and `0x0463` back. If the TCC offset
follows the byte, that is the entry moving off `present-untested` in the
direction `confirmed-working`; if it does not, the four sites are real and the
EC ignores the value, which is `confirmed-inert`. Both readings are worth
having and neither can be reached from this pipeline. A `--watch-page` arm of
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` would produce the
change row; it has never been run and cannot be run from here.

## 7. Reproducing every line above

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0786 --counts-only
$ python3 ec/tools/census_xdata_writers.py ec/firmware/GMxMGxx_11.800 0x0786
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/check_status_vocabulary.py
$ python3 ec/tools/find_indirect_xdata.py ec/firmware/GMxMGxx_11.800 --page 0x07
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x0787 0x0788 0x0789 0x078A --counts-only
```

`gen_findings_index.py` prints the index to stdout rather than writing it, so
regenerating it is a redirect, and `--check` is what fails on a stale one. Its
last line carries the write-up count and is not restated here — that is the
command's output, not a figure a reader should maintain:

```console
$ python3 ec/tools/gen_findings_index.py > docs/findings/INDEX.md
$ python3 ec/tools/gen_findings_index.py --check
```

Every listing quoted in §2, §3 and §5 is the committed
`ec/decompiled/bank0/*.asm`, which is machine output. Where a decompiled `.c`
disagrees with it, the `.asm` is right, and the two differ nowhere that matters
here — the C for `0x948D` reads the same block as the `if` on bit 7 and
`AP_OEM & 1` that the listing shows.

## Where this is recorded elsewhere

- `ec/annotations/registers.yaml`, the `CPU_TCC_OFFSET (APTC/APTN)` entry — the
  note carries the verdict and a `bits:` line the entry did not have.
- `windows/vendor-ec-map.md` — the same disagreement in one line, with a dated
  correction beside it.
- `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` §4 item 4 — the
  sweep instruction stays; the half of its reason that named this conflict is
  corrected in place.
- `linux/patches/gm7mg7p-tcc-offset-name.md` — the upstream consequence,
  prepared here and not submitted anywhere.
