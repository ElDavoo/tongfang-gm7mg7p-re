# `0x0751` (MANUAL_FAN_CTRL) — the 29 reference sites, and what they do not do

`docs/findings.md` §7 closed issue #92 with an explicit hole in it: the
vendor writes `0x0751`, PL1/PL2/PL4 at `0x0783-0x0785`, a 96-byte fan table
at `0x0F00-0x0F5F` and the GPU bytes as one bundle on every mode switch, so
the 2026-09-23 capture cannot say **what the EC does with `0x0751` by
itself**. Issue #99 asks the static half of that: do any of the 29 direct
reference sites read the mode bits and then copy the EC's own per-mode
defaults (`0x0730-0x0737`, `0x07A7-0x07AA`) into the PL registers, or load a
fan table into `0x0F00`?

**The short answer, and its limits.** No site found by this method does. All
29 sites are in the main EC image and every one of them decodes at the site
— there is no `handoff` bucket to chase. What they touch is `0x0751` and
nothing else: nineteen reads that mask or branch on the mode bits, seven
read-modify-writes of those same bits, one blind write, two sites whose
`mov dptr` is staged before an unrelated bit test. The per-mode default blocks turn out never to be *read*
anywhere in the image, and the only main-EC writer of `0x0783-0x0785` is
gated on `AP_OEM` (`0x0741`) bit 0, not on the mode. §4 and §5 are those two
results.

That is a statement about direct `MOV DPTR,#0x0751` sites and an 8-instruction
linear window around each, which is exactly the blind spot `registers.yaml`'s
header and `docs/findings.md` §4d warn about — and §6 below is a live
counter-example found while checking this one, where the same method reports
`0` for an address the EC provably does write. **None of this is a live test
of the byte**; `0x0751` stays `present-untested`, and
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` is the unrun
procedure that would settle it.

**§9 walks the arms the window stops short of.** The window ends at the first
control-flow instruction, and for 17 of the 29 sites that instruction *is* a
conditional branch on a mode bit — so both arms were unexamined when the two
paragraphs above were written. §9 walks all 34 with a different method. It
does not overturn §4 or §5: no arm found by this method writes a PL register
either. What it adds is that both candidate fan-PWM bytes, `0x075B` and
`0x075C`, are written on a path a `0x0751` bit selects, and that the Fan
Boost arms gate on `CPU_TEMP`/`GPU_TEMP`. That is a **prediction for** the
isolation run, not a result from it.

## 1. Reproducing the map

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0751 --counts-only
0x0751: 29 direct MOV DPTR site(s)  bank0=28  bank1=1

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0751 --csv \
          > ec/annotations/manual-fan-ctrl-0751-sites.csv
$ tail -n +2 ec/annotations/manual-fan-ctrl-0751-sites.csv | wc -l
29

$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1 --csv \
          | grep 0x0751

$ python3 ec/tools/walk_branch_arms.py --self-test ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
          0x0751 --callee-depth 1 --csv \
          | diff - ec/annotations/manual-fan-ctrl-0751-arms.csv
```

The 29 rows are the same 29 that `registers.yaml` records as
`static_refs_main_ec` and that `ec/tools/check_register_counts.py` recomputes
from the image, so the table below cannot silently disagree with the number
the rest of the repo quotes. `--callee-depth 1` adds nothing here: the
`callee`/`callee_window` columns are empty for all 29, because no site hands
`DPTR` to a subroutine. It was re-run while writing §9 and the columns are
still empty for all 29, so the arms walk in §9 is a new method rather than
this one re-pointed — and the empty result is recorded here so a later reader
does not take it for untried work.

The last command regenerates §9's table from
`manual-fan-ctrl-0751-arms.csv` and must produce an empty diff. Its own
`--self-test` checks the branch split against hand transcriptions from `r2`;
`python3 ec/tools/test_walk_branch_arms.py` covers the rest of the tool.

Framing, in the `frame_onto`/`frame_over` sense of `bank-call-audit.md` §8:
27 of the 29 sites have all 24 nearby anchors converging onto them. `0xAC17`
has 23 of 24 and `0x9432` 20 of 24 — still the majority verdict, but noted
rather than smoothed over. The two decodes this file actually leans on
(§4, §5) were re-run in `r2 -a 8051` and matched byte for byte; the commands
are in §7.

## 2. The 29 sites

From `manual-fan-ctrl-0751-sites.csv`, committed next to this file.

| runtime | region | access | what the window does |
| --- | --- | --- | --- |
| `0x8942` | bank0 | read | `jnb acc.6` — Fan Boost test |
| `0x898A` | bank0 | read+write | `anl a,#0xbf` — clear Fan Boost, then `lcall 0xA73F` |
| `0x899D` | bank0 | read | `jnb acc.6` — Fan Boost test |
| `0x89EE` | bank0 | read | `jnb acc.7` — USER test |
| `0x8E8B` | bank0 | read | `jnb acc.7` — USER test |
| `0x93CA` | bank0 | read | `jnb acc.7` — USER test |
| `0x9E2F` | bank0 | read | `jnb acc.7` — USER test |
| `0x9E4D` | bank0 | read | `jnb acc.7` — USER test |
| `0x9E6B` | bank0 | read | `jnb acc.7` — USER test |
| `0x9F18` | bank0 | read | `jnb acc.7` — USER test |
| `0x9F36` | bank0 | read | `jnb acc.7` — USER test |
| `0x9F54` | bank0 | read | `jnb acc.7` — USER test |
| `0x9F75` | bank0 | read | `jnb acc.7` — USER test |
| `0xA3BB` | bank0 | read+write | `xrl a,#0x40` — toggle Fan Boost, `ret` |
| `0xA812` | bank0 | write | stores a cleared `a` — the Gaming default, §4 |
| `0xA818` | bank0 | read+write ×2 | `anl a,#0xef` then `orl a,#0x80` — the Office default, §4 |
| `0xABB8` | bank0 | read+write | `xrl a,#0x40` — toggle Fan Boost, `ret` |
| `0xABE8` | bank0 | (no movx in window) | `DPTR` staged, then `jnb acc.1` on `0x049F` — §3 |
| `0xAC00` | bank0 | read+write | `anl a,#0x6f` — clear USER and TURBO, `ret` |
| `0xAC17` | bank0 | read | `jnb acc.4` — TURBO test |
| `0xAC30` | bank0 | read | `jnb acc.7` — USER test |
| `0xB5EA` | bank0 | read | `jnb acc.7` — USER test |
| `0xB73C` | bank0 | read | `jnb acc.7` — USER test |
| `0xBB40` | bank0 | read | `anl a,#0x90`, `ret` — mode getter, §3 |
| `0xC709` | bank0 | read+write | `xrl a,#0x40` — toggle Fan Boost, `ret` |
| `0xC741` | bank0 | (no movx in window) | `DPTR` staged, then `jnb acc.1` on `0x049F` — §3 |
| `0xC759` | bank0 | read+write | `anl a,#0x6f` — clear USER and TURBO, `ret` |
| `0xCA4C` | bank0 | read | `anl a,#0x90`, `ret` — mode getter, §3 |
| `0x9432` | bank1 | read | `anl a,#0x80`, `jnz` — USER test |

Every mask in that table is one of the four bits upstream names
(`FAN_MODE_TURBO` 4, `FAN_MODE_HIGH` 5, `FAN_MODE_BOOST` 6, `FAN_MODE_USER`
7). Nothing in the window of any site addresses another XDATA byte.

`0xABB8`/`0xABE8`/`0xAC00`/`0xAC17`/`0xAC30` and
`0xC709`/`0xC741`/`0xC759`/`0xCA4C` are the same routines twice, with the
same masks at the same relative offsets. Which of the two copies runs — or
whether both do, on different project IDs — is not answered here.

## 3. The mode setters, and what they say the three values mean

`0xABE8` and `0xC741` are the two "no movx in window" rows. The window is
misleading rather than empty: the site stages `DPTR` for the *next* block and
the `jnb` tests an accumulator loaded a moment earlier.

```
0xabe4  90049f   mov  dptr,#0x049f     ; BIOS_INFO_3 -- bit 1 = Turbo supported
0xabe7  e0       movx a,@dptr
0xabe8  900751   mov  dptr,#0x0751
0xabeb  30e115   jnb  acc.1,0xac03     ; Turbo not offered -> fall into the 0xAC00 block
0xabee  e0       movx a,@dptr
0xabef  547f     anl  a,#0x7f          ; clear USER
0xabf1  f0       movx @dptr,a
0xabf2  e0       movx a,@dptr
0xabf3  4410     orl  a,#0x10          ; set TURBO
0xabf5  f0       movx @dptr,a
0xabf6  22       ret
```

So the EC's own "go to Turbo" is `USER` cleared and `TURBO` set — `0x10`,
the byte the vendor service writes for Turbo
(`windows/vendor-ec-map.md` "Power modes"). The fall-through at `0xAC03` is
the tail of the `0xAC00` site, `anl a,#0x6f`: `USER` and `TURBO` both
cleared, which from `0x10` or `0xA0` lands on `0x00`, the vendor's Gaming
value. `0xBB40`/`0xCA4C` are the matching getter, `anl a,#0x90` — the two
bits that distinguish the three modes and nothing else.

This is a real, if small, independent confirmation of the mode encoding §7
took from the vendor's constants: the EC agrees with the service about what
`0x00` and `0x10` mean. It says nothing about whether the EC *acts* on a
value the host wrote, which is the whole question.

## 4. The one blind write: a boot-time default mode, and the PL clear next to it

`0xA812` and `0xA818` are both inside one routine entered at `0xA7C8`,
confirmed in `r2` (§7):

```
0xa7fe  900782   mov  dptr,#0x0782     ; BIOS_OEM_2
0xa801  e0       movx a,@dptr
0xa802  30e026   jnb  acc.0,0xa82b     ; gate
0xa805  e0       movx a,@dptr
0xa806  30e522   jnb  acc.5,0xa82b     ; one-shot flag; skip if already consumed
0xa809  e0       movx a,@dptr
0xa80a  54df     anl  a,#0xdf
0xa80c  f0       movx @dptr,a          ; consume it
0xa80d  e0       movx a,@dptr
0xa80e  30e407   jnb  acc.4,0xa818     ; bit 4 = default power mode
0xa811  e4       clr  a
0xa812  900751   mov  dptr,#0x0751
0xa815  f0       movx @dptr,a          ; default Gaming -> 0x00
0xa816  800b     sjmp 0xa823
0xa818  900751   mov  dptr,#0x0751
0xa81b  e0       movx a,@dptr
0xa81c  54ef     anl  a,#0xef          ; default Office -> clear TURBO,
0xa81e  f0       movx @dptr,a
0xa81f  e0       movx a,@dptr
0xa820  4480     orl  a,#0x80          ;                   set USER
0xa822  f0       movx @dptr,a
0xa823  e4       clr  a
0xa824  ff       mov  r7,a
0xa825  1294d0   lcall 0x94d0
0xa828  128653   lcall 0x8653          ; seeds the fan-table CODE base, §6
0xa82b  900741   mov  dptr,#0x0741     ; AP_OEM
0xa82e  e0       movx a,@dptr
0xa82f  20e011   jb   acc.0,0xa843     ; "AP exists" -> leave the PLs alone
0xa832  e4       clr  a
0xa833  900783   mov  dptr,#0x0783
0xa836  f0       movx @dptr,a          ; PL1 = 0
0xa837  900784   mov  dptr,#0x0784
0xa83a  f0       movx @dptr,a          ; PL2 = 0
0xa83b  900785   mov  dptr,#0x0785
0xa83e  f0       movx @dptr,a          ; PL4 = 0
0xa83f  90078b   mov  dptr,#0x078b
0xa842  f0       movx @dptr,a
0xa843  22       ret
```

`0x0782` bit 4 is the byte `registers.yaml` already documents as "the default
power mode (0 Office, 1 Gaming)" from the vendor's `GetDefaultMode`, and the
two branches match on the bits they touch: Gaming writes `0x00` outright,
Office sets `USER` and clears `TURBO`. Note Office is a read-modify-write
that leaves `HIGH` (bit 5) as it found it, so it only lands on the vendor's
`0xA0` if bit 5 was already set — what the byte holds when this runs is not
established here. So the EC does set the mode byte itself — once, off a BIOS
setup bit, behind a flag it clears as it goes.

**This is the closest thing in the image to the mechanism the issue asks
about, and it is not that mechanism.** The PL clear at `0xA833-0xA83B` is in
the same routine, a dozen instructions after the mode write, and it is the
*only* main-EC writer of `0x0783-0x0785` this method finds (§5). But the two
are independently gated: the PL branch tests `AP_OEM` (`0x0741`) bit 0, the
host-present flag, and never looks at `0x0751` or at the value just written
to it. And what it writes is a cleared accumulator — zero, not a per-mode
default.

Read as a claim about a Linux driver, the interesting half is the `AP_OEM`
gate, not the mode: on this path the EC zeroes PL1/PL2/PL4 unless bit 0 of
`0x0741` is set. `uniwill-laptop` already sets that bit in
`uniwill_ec_init()` for the charge-profile path (see the `0x0741` entry in
`registers.yaml`), so a profile driver would inherit it — but *when* this
routine runs is not established here. Its one direct caller is `0x851B`,
which sits in a run of consecutive three-byte `lcall`/`ljmp` entries whose
framing this repo has not resolved (`bank-call-audit.md`); whether that is a
boot chain, a dispatch table or a polled task is an open question, and
"boot-time" above is the shape of the `0x0782` bit-5 one-shot, not a
scheduling claim.

## 5. The per-mode default blocks are written by the EC and read by nobody

The issue's hypothesis — the EC copies `0x0730-0x0737` / `0x07A7-0x07AA`
into the PLs on a mode change — requires something to *read* those bytes.

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x0730 0x0731 0x0732 0x0733 0x0734 0x0735 0x0736 0x0737 \
      0x07A7 0x07A8 0x07A9 0x07AA 0x0783 0x0784 0x0785 --counts-only
```

Every one of the fourteen default-block sites decodes as a **write**. Some
take their value from a CODE table via `movc` (`0x9528`, `0x9551`,
`0xBEC9`); the rest are immediates, in a run guarded by a `cjne r0,#…`
comparison chain — one of several per-model variants, and which one applies
to this chassis is not decided here:

```
0x95c0  9007a7   mov  dptr,#0x07a7
0x95c3  7464     mov  a,#0x64
0x95c5  f0       movx @dptr,a
0x95ca  900730   mov  dptr,#0x0730
0x95cd  742d     mov  a,#0x2d
0x95cf  f0       movx @dptr,a
```

Worth flagging rather than smoothing over: `0x2D` is not the `0x3C` that
`registers.yaml` records as the live value of `0x0730`, which is consistent
with this block not being the branch that runs on this machine — but
"consistent with" is all it is.

Not one read site is found for any of the twelve default bytes. The shape is
the EC *publishing* its defaults for the host to fetch — which is precisely
how the vendor uses them: §7 records `SetUserProfile` seeding its PL values
from these bytes and then writing the PLs itself.

On the destination side, `0x0783`, `0x0784` and `0x0785` have five sites
each: four reads per address (`subb`-against-zero at `0x96B4`/`0x96C2`/`0x96D0`
and `jz` presence checks at `0x97D8`/`0x98C4`/`0x9DC8` and the equivalents
for the other two bytes) and the single write in §4.

So, stated as narrowly as the evidence allows: **no path found by this method
carries a per-mode default byte into a PL register.** A driver that writes
`0x0751` and expects the PLs to follow has, on static evidence, nothing to
follow them with. The live test is still what decides it.

## 6. `0x0F00`: zero direct sites, and why that is not an answer

`0x0F00-0x0F5C` has **zero** direct `MOV DPTR` sites in the whole image;
`0x0F5D` has one and `0x0F5F` two. Taken at face value that would say the EC
never touches its own fan table. It is wrong, and it is worth writing down
*why* it is wrong, because this is the same shape of error `docs/findings.md`
§4d had to retract.

The EC reaches the page by building `DPH` at run time. Eight sites in bank0
do it — `34 0F F5 83`, `addc a,#0x0f ; mov DPH,a` — at `0x8AC6`, `0x8AD8`,
`0x8AF3`, `0x8B0C`, `0xBCE3`, `0xBDEC`, `0xE86B` and `0xF312`, e.g.

```
0xbcda  900460   mov  dptr,#0x0460
0xbcdd  e0       movx a,@dptr
0xbcde  2410     add  a,#0x10
0xbce0  f582     mov  0x82,a
0xbce2  e4       clr  a
0xbce3  340f     addc a,#0x0f
0xbce5  f583     mov  0x83,a           ; DPTR = 0x0F10 + [0x0460]
0xbce7  e0       movx a,@dptr
```

and, on the write side, `0xF312` walks `0x0F61 + r7`. The site scan cannot
see any of them, which is the standing caveat in `registers.yaml`'s header
made concrete on a second address besides `0x07B9`.

More usefully, this is the EC side of the handshake `docs/findings.md` §7
lists as unread. `0x888D` is the handler: it requires `0x0F5D = 0xFD` and
`0x0F5E = 0xC9` as a magic, then reads `0x0F5F` as a table selector accepted
only in `1..3`.

```
0x88b3  e0       movx a,@dptr
0x88b4  b40108   cjne a,#0x01,0x88bf
0x88b7  9008e7   mov  dptr,#0x08e7     ; selector 1 -> base + 0x0C
0x88ba  e0       movx a,@dptr
0x88bb  240c     add  a,#0x0c
0x88bd  8025     sjmp 0x88e4
0x88bf  900f5f   mov  dptr,#0x0f5f
0x88c2  e0       movx a,@dptr
0x88c3  b40205   cjne a,#0x02,0x88cb
0x88c6  12bc4f   lcall 0xbc4f          ; selector 2 -> base + 0x00
0x88cb  900f5f   mov  dptr,#0x0f5f
0x88ce  e0       movx a,@dptr
0x88cf  b40315   cjne a,#0x03,0x88e7
0x88d2  900782   mov  dptr,#0x0782     ; selector 3 -> 0x0782 bit 2 picks
0x88d5  e0       movx a,@dptr
0x88d6  9008e7   mov  dptr,#0x08e7
0x88d9  30e205   jnb  acc.2,0x88e1
0x88dc  e0       movx a,@dptr
0x88dd  2408     add  a,#0x08          ;   bit 2 set   -> base + 0x08
0x88df  8003     sjmp 0x88e4
0x88e1  e0       movx a,@dptr
0x88e2  2404     add  a,#0x04          ;   bit 2 clear -> base + 0x04
```

`0x0782` bit 2 is the byte `registers.yaml` already calls "the Office
fan-table type (its getter is never called)" — so selector 3 is Office, and
the EC keeps two Office tables. `windows/vendor-ec-map.md` records the same
numbering (1 Turbo, 2 Gaming, 3 Office) from the *service* side, read out of
`RefreshDefaultFanTable`. The two were derived independently and agree.

The same section notes the service clears `AP_OEM` (`0x0741`) bit 0 for the
duration of the handshake and sets it again afterwards. That is the exact
condition §4's PL clear waits for. Whether the two can overlap depends on
when `0xA7C8`'s routine runs, which is not established — but it is the first
thing to check if PL bytes are ever seen going to zero around a fan-table
refresh. The base is a CODE pointer the EC seeds as
`0x60F2` at `0x8653` — the routine called at `0xA828`, in §4's block. At
`0x60F2` is a table of big-endian CODE pointer pairs
(`0x56A2 0x5762`, `0x56D2 0x5792`, `0x5702 0x57C2`, `0x5672 0x5732`, …), and
the handler copies `0x30` bytes from the first of a pair to `0x0F00` and
`0x30` from the second to `0x0F30`:

```
0x88ec  900a4b   mov  dptr,#0x0a4b
0x88ef  740f     mov  a,#0x0f
0x88f1  f0       movx @dptr,a
0x88f2  a3       inc  dptr
0x88f3  7400     mov  a,#0x00          ; destination 0x0F00
...
0x890b  b430f6   cjne a,#0x30,0x8904   ; 48 bytes
0x890e  900a4b   mov  dptr,#0x0a4b
0x8911  740f     mov  a,#0x0f
0x8915  7430     mov  a,#0x30          ; destination 0x0F30
...
0x892e  b430f6   cjne a,#0x30,0x8927   ; 48 more
```

Two 48-byte halves is the layout of the captured page. The CODE tables have
the same internal shape as the live bytes in
`evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt` — a
`0xFF`-terminated ramp, a second `00 30 …` ramp, then a `00 3C 3C 46 5A …`
row — while the values differ, which is what you would expect when the
capture was taken with the vendor service pushing its own JSON tables over
the EC's defaults. That agreement in shape is the evidence; it is not a
byte-for-byte match and is not offered as one.

**For this issue the conclusion is a negative one and it is the useful one:**
the EC does load a fan table of its own into `0x0F00`, but the trigger found
here is the `0x0F5D-0x0F5F` mailbox, on explicit host request. No site in §2
reaches this code, and the selector is read from `0x0F5F`, never from
`0x0751`. On static evidence a mode change alone does not reload the table.
Whether some other path also calls the copy is not something a site scan can
rule out — see the DPH construction above for why.

## 7. Spot-checks against an independent disassembler

`ec/tools/disasm8051.py` is a linear decoder, not a disassembler, so the two
listings this file's argument rests on were re-run in radare2 (installed by
`.github/actions/project-setup`, as `pd-xdata-overlap.md` §3 did):

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa7fe; pd 24' /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa828; pd 12' /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x88e4; pd 16' /tmp/bank0.bin
```

Both matched the listings in §4 and §6 instruction for instruction.

§9's argument rests on the listings below, which were re-run the same way. The
`0x8949` arm and the `0x8F0A` write are the two the conclusion leans on hardest
— one supplies the temperature gate, the other is the `0x075C` write:

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 1 0x10000 /tmp/bank1.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8949; pd 6'   /tmp/bank0.bin   # the 0x085F/0x3C gate
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8978; pd 9'   /tmp/bank0.bin   # CPU_TEMP and GPU_TEMP vs 0x46
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x89d7; pd 6'   /tmp/bank0.bin   # the 0x075B write
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8e92; pd 4'   /tmp/bank0.bin   # USER-set  tach threshold
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8ec2; pd 4'   /tmp/bank0.bin   # USER-clear tach threshold
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8ef0; pd 8'   /tmp/bank0.bin   # the 0x1804/0x1809 join
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9e2f; pd 8'   /tmp/bank0.bin   # the replicated clamp
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9e6f; pd 8'   /tmp/bank0.bin   # ... and the next copy
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9e89; pd 13'  /tmp/bank0.bin   # the 0x08C1 copy block
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9eb1; pd 3'   /tmp/bank0.bin   # the 0x0784 read
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xbb22; pd 5'   /tmp/bank0.bin   # callee -> 0x075B
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xbb28; pd 4'   /tmp/bank0.bin   # callee -> 0x075B
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8f0f; pd 5'   /tmp/bank0.bin   # callee -> 0x075C
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xe389; pd 6'   /tmp/bank0.bin   # callee -> 0x0435
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9432; pd 8'   /tmp/bank1.bin   # the bank1 arms, CODE pointers
```

All matched the CSV rows in §9 instruction for instruction. `walk_branch_arms.py
--self-test` holds a hand transcription of all seventeen branch encodings and
targets, so the split the tool performs is itself checked against `r2` rather
than only the listings quoted here.

## 8. What is still open

- **The whole live question.** Nothing above is a behavioural test. Writing
  `0x0751` and watching is `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`,
  which has not been run. §9's arms are a *prediction for* that run.
- **When `0xA7C8`'s routine runs**, and therefore whether the `AP_OEM`-gated
  PL clear in §4 can fire after a host has written the PLs, or only before.
  Resolving `0x851B`'s framing (`bank-call-audit.md`) is the way in.
- **The duplicated `0xABxx` / `0xC7xx` mode routines** — two copies, same
  masks. Which one is live, and on what condition.
- **The default fan tables themselves.** At least twenty CODE pointer pairs
  at `0x60F2`, of which the mailbox handler selects four (where the table
  ends was not determined). Decoding them and
  comparing against the vendor's announced tables (`windows/tools/fan_table_replay.py`)
  would answer whether a Linux driver could skip shipping tables entirely and
  ask the EC for its own.
- **What the arms behind `0xB5F8` and `0xB758` do.** Both are a bare `ljmp`
  to a callee, and §9's `--callee-depth 1` follows exactly one level; the two
  routines they reach (`0xB716`, `0xB82E`) are themselves long. Following
  them is the same kind of work as §9 and is not done here.

  > **Corrected 2026-09-24.** "are themselves long" was wrong, and this file's
  > own table contradicted it: `manual-fan-ctrl-0751-arms.csv` records **20**
  > and **8** instructions for `0xB716` and `0xB82E`, both ending in `ret`.
  > The long things at those two sites are the *fall-through* arms, `0xB5F1` at
  > 165 and `0xB743` at 154, which §9.1 already summarises. The reading is
  > done — see **§8a** below. The error was reading a short clearing routine as
  > a long one, which is the same shape as the `0x0F00` mistake in §6: a
  > summary that sounds like the answer standing in for an answer nobody had
  > looked at.
- **What `0x075B` and `0x075C` actually are.** §9 finds the EC storing to
  both. That they are fan PWM is still an assumption from issue #99, not a
  measurement — see the file header of
  `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` §3 for the range
  that must not be swept.

### 8a. The two routines the USER branches tail-jump to

`0xB5F8` and `0xB758` are one-instruction arms, so §9's `--callee-depth 1`
rows for `0xB716` and `0xB82E` are the whole of them. Both are short, both end
in `ret`, and both are pure clearing routines — no call, no branch, no
arithmetic. The listings are §7's convention, and `r2` re-decodes both
instruction for instruction (commands at the end):

```
0xb716  9008eb   mov  dptr,#0x08eb
0xb719  e0       movx a,@dptr
0xb71a  54f7     anl  a,#0xf7            ; clear bit 3
0xb71c  f0       movx @dptr,a
0xb71d  9009e6   mov  dptr,#0x09e6
0xb720  e0       movx a,@dptr
0xb721  54fd     anl  a,#0xfd            ; clear bit 1
0xb723  f0       movx @dptr,a
0xb724  9009e7   mov  dptr,#0x09e7
0xb727  e0       movx a,@dptr
0xb728  54fd     anl  a,#0xfd            ; clear bit 1
0xb72a  f0       movx @dptr,a
0xb72b  e4       clr  a
0xb72c  9008a2   mov  dptr,#0x08a2
0xb72f  f0       movx @dptr,a            ; 0
0xb730  90089e   mov  dptr,#0x089e      ; 0xB730 is its own entry; see below
0xb733  f0       movx @dptr,a            ; 0
0xb734  a3       inc  dptr               ;   -> 0x089f
0xb735  f0       movx @dptr,a            ; 0
0xb736  22       ret
```

```
0xb82e  9008eb   mov  dptr,#0x08eb
0xb831  e0       movx a,@dptr
0xb832  54bf     anl  a,#0xbf            ; clear bit 6
0xb834  f0       movx @dptr,a
0xb835  e4       clr  a
0xb836  9008a0   mov  dptr,#0x08a0
0xb839  f0       movx @dptr,a            ; 0
0xb83a  22       ret
```

**Why the `0xB716` listing is 20 instructions when the committed `.asm` shows
15.** `0xB730` is its own function entry (`ghidra-functions.csv`, bank0
`0xB730`, `store_a_to_089e_and_089f`) whose body sits inside `0xB716`'s span,
and the exporter stops a function body where the next entry begins — so
`ec/decompiled/bank0/B716.asm` ends at `0xB72F` and the six instructions from
`0xB730` to `0xB736` appear only in the `.c`. That is the existing explanation
on the `B716` annotation row, not a truncation to repair: repairing it would
mean `--mode rebuild-project`, which two branches cannot both do. The 20 is
the two entries added together and is what the arms CSV's `insns` column
records.

**The per-register attribution, and the one `unattributed` store resolved.**
`0xB716` clears bit 3 of `0x08EB`, bit 1 of `0x09E6` and bit 1 of `0x09E7` —
three read-modify-writes, masks `0xF7`/`0xFD`/`0xFD` — and then writes `0` to
`0x08A2`, `0x089E` and `0x089F`. `0xB82E` clears bit 6 of `0x08EB` (mask
`0xBF`) and writes `0` to `0x08A0`. The arms CSV records **one** `unattributed`
store in the `0xB716` row and that is the whole of the mystery: it is the
`movx @dptr,a` at `0xB735`. The tool tracks `DPTR` from the last
`mov dptr,#imm16` and an `inc dptr` is not one, so the store lands on `0x089F`
in the machine code and on nothing in the tool. `0x089E` and `0x089F` are
written as one 16-bit store, and the `static_refs` count of 1 for `0x089F` in
`registers.yaml` is a count of direct `mov dptr` sites, not of writers.

**The USER bit is one gate among several, and it is not the only one that
reaches either routine.** This is where the issue's framing has to be weakened:
USER set and USER clear do not decide whether `0x08A0` and `0x08A2` are
written at all — both paths write. What USER changes is the value. On the
USER-**clear** path (the taken arm of both `jnb acc.7`) the EC *forces the
byte to `0`*; on the USER-**set** fall-through arm it *computes and stores* one.
Zero against a computed value, not present against absent.

But "USER clear reaches `0xB716`" is itself only one of three ways in, and
two of the three are not the USER bit:

```
0xb5e3  9006e6   mov  dptr,#0x06e6
0xb5e6  e0       movx a,@dptr
0xb5e7  b4010e   cjne a,#0x01,0xb5f8     ; 0x06E6 != 1 -- 0x0751 not read yet
0xb5ea  900751   mov  dptr,#0x0751
0xb5ed  e0       movx a,@dptr
0xb5ee  30e707   jnb  acc.7,0xb5f8       ; USER clear
0xb5f1  9007c5   mov  dptr,#0x07c5
0xb5f4  e0       movx a,@dptr
0xb5f5  30e403   jnb  acc.4,0xb5fb       ; 0x07C5 bit 4 SET -> fall into 0xb5f8
0xb5f8  02b716   ljmp 0xb716
```

`0xB5E7` fires **before the mode byte is read at all**, so `0xB716` runs on a
path where USER never entered the decision. And `0xB5F5` is the same gate
that §9.1's `0xB743` row turns on at `0xB755`: `0x07C5` bit 4 set means the
USER-**set** arm runs the USER-**clear** routine. `0xB82E` is looser still —
four branches reach `0xB758` directly, and only `0xB740` is the USER bit:

```
0xb737  12b9d8   lcall 0xb9d8
0xb73a  701c     jnz  0xb758             ; non-zero -- 0x0751 not read yet
0xb73c  900751   mov  dptr,#0x0751
0xb73f  e0       movx a,@dptr
0xb740  30e715   jnb  acc.7,0xb758       ; USER clear
0xb743  900490   mov  dptr,#0x0490
0xb746  e0       movx a,@dptr
0xb747  30e00e   jnb  acc.0,0xb758       ; 0x0490 bit 0 clear, on the USER-set arm
0xb74a  9004ab   mov  dptr,#0x04ab
0xb74d  e0       movx a,@dptr
0xb74e  b46407   cjne a,#0x64,0xb758     ; 0x04AB != 100, on the USER-set arm
0xb751  9007c5   mov  dptr,#0x07c5
0xb754  e0       movx a,@dptr
0xb755  30e403   jnb  acc.4,0xb75b       ; 0x07C5 bit 4 SET -> fall into 0xb758
0xb758  02b82e   ljmp 0xb82e
0xb75b  12ba36   lcall 0xba36
```

`0xB755` is a fifth gate rather than a fifth branch: `jnb acc.4` is *taken*
when `0x07C5` bit 4 is clear, and its target is the `lcall 0xba36` at
`0xB75B`, not the `ljmp 0xb82e` at `0xB758` — the same shape as the `0xB5F5`
line above, which also reaches its tail jump by fall-through.

So neither routine is "the USER-clear arm's routine". Both are the reset half
of a state machine that USER selects *between*, alongside `0x06E6`, `0x07C5`
bit 4, `0x0490` bit 0, `0x04AB` and whatever `0xB9D8` decides.

**What the USER-set arm writes into the same bytes.** It is the other half of
the pair, and it is where `0x08A0`'s real shape shows:

```
0xb7e8  9008a0   mov  dptr,#0x08a0
0xb7eb  e0       movx a,@dptr
0xb7ec  04       inc  a
0xb7ed  f0       movx @dptr,a
0xb7ee  e0       movx a,@dptr
0xb7ef  d3       setb c
0xb7f0  940a     subb a,#0x0a
0xb7f2  4046     jc   0xb83a             ; A - 0x0A - 1 borrows: 0x0A or below -> retire
0xb7f4  9008eb   mov  dptr,#0x08eb
0xb7f7  e0       movx a,@dptr
0xb7f8  4440     orl  a,#0x40            ; from 0x0B -> set bit 6
0xb7fa  f0       movx @dptr,a
0xb7fb  22       ret
```

The `setb c` at `0xB7EF` is load-bearing: `subb` carries in, so the `0xB7F2`
compare is really `A - 0x0A - 1` and it retires at `0x0A` **or below**, not
below `0x0A`. Bit 6 therefore latches from `0x0B` up, and the count runs one
further than the operand suggests. The same idiom at `0x9E45` — `setb c`,
`subb a,#0x23` — clamps a byte to `0x23` the same way, so this is the file's
established reading of a carry-in compare rather than an inference from this
one site.

`0x08A0` is therefore a count that runs to `0x0A` and latches bit 6 of
`0x08EB` on the next increment — and `0xB82E` clears the bit *and* zeroes the
count, so the two instructions `0xB82E` performs are one reset of one
mechanism rather than two unrelated writes. `0x08A2` has no such shape: the
USER-set arm stores the immediate `0x04` at `0xB6A1` and the USER-clear
routine stores `0` at `0xB72C`, and nothing else found by this method writes
either byte.

**What the accumulator holds at the `0xB730` store — the open question this
reading had to settle.** `0xB730` has two entries in the main EC, and the
`0xB716` annotation's "with A = 0 on entry" was true but attributed to the
wrong place, because `0xB716` zeroes it itself one instruction earlier. The
other entry is the USER-set path's `ljmp` at `0xB6A5`, and it arrives with `A`
zeroed at `0xB6A4`, immediately before:

```
0xb690  9008eb   mov  dptr,#0x08eb
0xb693  e0       movx a,@dptr
0xb694  4408     orl  a,#0x08            ; set bit 3
0xb696  f0       movx @dptr,a
0xb697  9009e6   mov  dptr,#0x09e6
0xb69a  e0       movx a,@dptr
0xb69b  4402     orl  a,#0x02            ; set bit 1
0xb69d  f0       movx @dptr,a
0xb69e  9008a2   mov  dptr,#0x08a2
0xb6a1  7404     mov  a,#0x04
0xb6a3  f0       movx @dptr,a            ; 0x08A2 = 4
0xb6a4  e4       clr  a                  ; A = 0 ...
0xb6a5  02b730   ljmp 0xb730             ; ... and 0x089E/0x089F get it
```

A byte scan of bank0 for `02 b7 30` finds that one caller and no other, so
**both** entries carry `A = 0` and `0x089E`/`0x089F` are zeroed on the USER-set
path as well as the USER-clear one. The bit pattern here is the mirror image of
`0xB716` — bits 3 and 1 are *set* where `0xB716` clears them — which is what
makes the two routines read as one mechanism's two ends.

**And what `0x089E`/`0x089F` are for is not settled.** On the USER-set path
they are read back, big-endian, and subtracted from a bound computed out of a
CODE table (`movc` at `0xB6B0` with `A = 0x0A`, then `mov b,#0x0A ; mul ab`,
so the limit is ten times `table[0x0A]`):

```
0xb6b7  90089f   mov  dptr,#0x089f
0xb6ba  e0       movx a,@dptr
0xb6bb  9f       subb a,r7
0xb6bc  90089e   mov  dptr,#0x089e
0xb6bf  e0       movx a,@dptr
0xb6c0  95f0     subb a,0xf0             ; B
0xb6c2  4024     jc   0xb6e8
```

A zeroed 16-bit value compared against a derived bound reads as an elapsed
count or a countdown, and the structure around it is consistent with that —
but "reads as" is the whole of the claim, and this file does not get to make
it. The `0xB5CC` annotation, on the `0x089C`/`0x089D` twin of this store, says
it in one line: callers set `A` first, and the listing itself has no
arithmetic. What `0xB6C2` does on the comparison is not read here, and a
reader who wants the mechanism should treat this as the question rather than
the answer.

**What this section does not say.** All seven bytes are now in
`ec/annotations/registers.yaml` at `present-untested` — `0x08A0`, `0x08A2`,
`0x08EB`, `0x089E`, `0x089F`, `0x09E6`, `0x09E7` — named `XDATA_*` rather than
after the USER bit, because "USER clear zeroes it" is a fact about several
code paths and not a statement about what the register *is*. Nothing here was
read back: per `CLAUDE.md` a store being written is not evidence the EC acts on
the byte, and no value of any of the seven has ever been observed. A zero from
a scan is "not found by this method", never absent, so "no site sets bit 1 of
`0x09E7`" and "no site branches on bit 0 of `0x08EB`" are both statements about
the scan. The one reader found for `0x08A2` (bank1 `0xA987`) was not decoded,
and the remaining four members of the `main-ec-012` cluster are still unnamed.

One thing §9.1 already had and this section makes precise: the `0xB5F1` row
lists `0x08A2 write` and `0x09E7 r+w` even though the USER-**set** arm does not
run `0xB716`. The reason is ordinary conditional reachability rather than any
tail-jump descent: the `jnc 0xb736` at `0xB714` **falls through** into
`0xB716`, so the arm's own linear block from `0xB6E8` decodes the whole
`0xB716 … 0xB736 ret` body — including the `mov dptr,#0x08a2` at `0xB72C`,
the `mov dptr,#0x09e7` at `0xB724`, and the `mov dptr,#0x089e` at `0xB730`
that puts `0x089E` in the arm's `writes`. `walk_branch_arms.py` does *not*
follow a tail jump inline: at `walk_branch_arms.py:380-388` it appends the
target to `arm.callees` and ends the arm, so the callee's own instructions are
never decoded into it. `0xB716` is in this arm's `callees` too, but for an
unrelated path — the `ljmp 0xb716` at `0xB5F8` — which is not what puts those
addresses in the `xdata` column. The addresses were visible; what was missing
was which instruction wrote each one and what value.

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb716; pd 20' /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb82e; pd 8'  /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb5e3; pd 10' /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb737; pd 15' /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb6a1; pd 4'  /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb6b7; pd 6'  /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb7e8; pd 13' /tmp/bank0.bin
```

Each `pd` count is the length of the listing above it: 20 and 8 are the two
`insns` values §8's corrected bullet quotes, and 10/15/4/6/13 are just where
the last quoted instruction falls. The instruction counts in this section are
the `insns` column of `manual-fan-ctrl-0751-arms.csv` — `0xB716` 20, `0xB82E`
8, `0xB5F1` 165, `0xB743` 154 — and there is no gate that checks a document
against that CSV, so they were compared by hand and by the commands above.


## 9. The 17 mode-bit branch arms

§4 and §5 are statements about an 8-instruction window around each of the 29
sites, and the window stops at the first control-flow instruction. For the 17
sites whose window *ends on a conditional branch*, that means both arms of the
branch have never been looked at — and the two arms are where the code is.
This section walks all 34.

The method is `ec/tools/walk_branch_arms.py`, a bounded recursive descent from
each branch target:

```console
$ python3 ec/tools/walk_branch_arms.py --self-test ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 \
          0x0751 --callee-depth 1 --csv \
          | diff - ec/annotations/manual-fan-ctrl-0751-arms.csv
$ python3 ec/tools/test_walk_branch_arms.py
```

A conditional branch is followed on both sides, so a row is a
"reachable from here" set, not a guess about the hot path. `ret`/`reti` ends
an arm; `ljmp`/`ajmp` hands it to another routine (recorded as a callee, which
is what the callee table is for); `lcall`/`acall` is recorded and the walk
continues past it, because the code after a call is still the arm's own. An
address already walked is a loop, not more code. **At the default bounds all
34 arms report `status: complete`** in the CSV — nothing was cut short, which
is what lets the negatives below be stated without a hedge.

Two things the descent refuses to guess, because guessing them is how a
bounded scan produces a confident wrong answer:

- **DPTR is tracked, not assumed.** A `movx` is charged to whatever
  `mov dptr,#imm16` last set, and to nothing before that. Any store to DPL
  (`0x82`) or DPH (`0x83`) — from the accumulator *or from a register* — makes
  the pointer unknown from there on, and every later `movx` is counted
  `unattributed` rather than charged to whatever address happened to be loaded
  earlier. That is §6's shape, and here it is load-bearing: the bank1 arms
  hand `0x93B6`/`0x93E6` to `r2`/`r1` and rebuild DPTR from them, so a tool
  watching only `mov 0x82,a` would report `0x93E6` as an XDATA register.
- **`>= 0x8000` is CODE.** In the main EC's map the common area ends at
  `0x7FFF` and the bank windows start at `0x8000`, so an immediate at or above
  that cannot be an XDATA address — it is the `movc`/CODE-pointer blind spot
  `trace_xdata_refs.classify()` names. It is labelled, not folded into the
  XDATA column.

**Branch targets come from the decoded stream, never from the displacement
column.** The `+0x..` in `manual-fan-ctrl-0751-sites.csv` is a relative
displacement, not an offset from the site, and adding it to the site address
lands mid-instruction on 10 of the 17. For the 16 bank0 sites the branch is at
`site + 7` and the target is `site + 10 + rel`; `0x9432` is
`90 07 51 e0 54 80 70 05`, so the `anl a,#0x80` puts the `jnz` at `site + 6`
and the target at **`site + 8 + rel` = `0x943F`**, not the `0x943E` the same
arithmetic gives. `0x943E` is the second byte of the `mov dptr,#0x93E6` that
follows, and would decode as something plausible.

### 9.1 The 34 arms

`region` is the image the site and both arms are in — a branch target at or
above `0x8000` is resolved in the caller's own bank, which is the same-bank
assumption `offset_for_runtime()` already carries and documents. `0x9432` is
the only bank1 row.

Read the two arm columns with the sense of the branch in mind: `jnb acc.N,target`
*falls through* when bit N is set and takes the branch when it is clear, so on
16 of these 17 rows the **fall-through arm is the bit-set path** and the taken
arm is the bit-clear one. `0x9432` is the exception — it masks and then `jnz`,
so its **taken** arm is the USER-set path.

| site | test | taken arm | fall-through arm |
| --- | --- | --- | --- |
| `0x8942` bank0 | `jnb acc.6` FAN BOOST | `0x8998` 211 insn — clears `0x085F`, falls into the `0x899D` site, then the `0x899D` arms; writes `0x075B`, reads `0x043E` | `0x8949` 249 insn — `0x085F` vs `0x3C`, then `0x043E` and `0x044F` vs `0x46`, then **writes `0x0751` back**; writes `0x075B` |
| `0x899D` bank0 | `jnb acc.6` FAN BOOST | `0x89C2` 190 insn — consumes `0x0768` bit 2 and **writes `0x075B`** from `0x0768` or `0x0469`; reads `0x043E` | `0x89A4` 15 insn — sets `0x0768` bit 2, clears `0x0824` bit 7 |
| `0x89EE` bank0 | `jnb acc.7` USER | `0x8A09` 146 insn — reads `0x043E`, `0x0460`/`0x0468` r+w | `0x89F5` 146 insn — same, plus `0x0782` read |
| `0x8E8B` bank0 | `jnb acc.7` USER | `0x8EC2` 41 insn — `0x0460`/`0x0468` vs `0x04`/`0x07`, **writes `0x075C`** | `0x8E92` 42 insn — `0x0460`/`0x0468` vs `0x04`/`0x08`, **writes `0x075C`** |
| `0x93CA` bank0 | `jnb acc.7` USER | `0x93D9` 115 insn — reads `0x044F` and `0x0786` | `0x93D1` 106 insn — same, and reads `0x0751` again |
| `0x9E2F` bank0 | `jnb acc.7` USER | `0x9E4D` 225 insn — the replicated block, §9.2 | `0x9E36` 237 insn — ditto |
| `0x9E4D` bank0 | `jnb acc.7` USER | `0x9E6B` 210 insn — ditto | `0x9E54` 222 insn — ditto |
| `0x9E6B` bank0 | `jnb acc.7` USER | `0x9E89` 195 insn — ditto | `0x9E72` 207 insn — ditto |
| `0x9F18` bank0 | `jnb acc.7` USER | `0x9F36` 107 insn — ditto, and `0x0785` read | `0x9F1F` 118 insn — ditto |
| `0x9F36` bank0 | `jnb acc.7` USER | `0x9F54` 93 insn — ditto | `0x9F3D` 104 insn — ditto |
| `0x9F54` bank0 | `jnb acc.7` USER | `0x9F75` 78 insn — ditto | `0x9F5B` 90 insn — ditto |
| `0x9F75` bank0 | `jnb acc.7` USER | `0x9F8C` 67 insn — ditto | `0x9F7C` 75 insn — ditto |
| `0xAC17` bank0 | `jnb acc.4` TURBO | `0xAC2D` 12 insn — reads `0x0751` and nothing else | `0xAC1E` 18 insn — reads `0x049F` then `0x0751`; lands on the `0xAC30` site |
| `0xAC30` bank0 | `jnb acc.7` USER | `0xAC3D` 6 insn — no XDATA by this method | `0xAC37` 2 insn — no XDATA by this method |
| `0xB5EA` bank0 | `jnb acc.7` USER | `0xB5F8` 1 insn — a bare `ljmp 0xB716`; no XDATA by this method | `0xB5F1` 165 insn — a long routine, `0x07C5` read and `0x08A2` write among others |
| `0xB73C` bank0 | `jnb acc.7` USER | `0xB758` 1 insn — a bare `ljmp 0xB82E`; no XDATA by this method | `0xB743` 154 insn — reads `0x043E` and `0x044F`, writes `0x08A0` |
| `0x9432` bank1 | `anl a,#0x80 ; jnz` USER | `0x943F` 57 insn — `mov dptr,#0x93E6`, a **CODE** pointer; writes `0x0626`/`0x0627`/`0x0895` | `0x943A` 57 insn — `mov dptr,#0x93B6`, likewise; same three XDATA writes |

The full per-arm XDATA set, the decoded blocks, the callee list and the stop
reasons are in `manual-fan-ctrl-0751-arms.csv`, committed beside this file and
regenerated by the command above. The table here is a reading of it; the CSV
is the evidence.

### 9.2 The replicated `0x9Exx` block, deduplicated

Seven of the seventeen are one routine, replicated. `0x9E2F`'s arm at
`0x9E4D` is the next site's address; from `0x9E4D` to `0x9E6B`, from there to
`0x9E89`, and so on through `0x9F18`/`0x9F36`/`0x9F54`/`0x9F75`. Each ~`0x1E`-byte
copy does the same thing and re-tests USER before the next one:

```
0x9e2f  900751   mov  dptr,#0x0751
0x9e32  e0       movx a,@dptr
0x9e33  30e717   jnb  acc.7,0x9e4d          ; USER clear -> next copy
0x9e36  9007c6   mov  dptr,#0x07c6          ; AP_OEM_6
0x9e39  e0       movx a,@dptr
0x9e3a  20e110   jb   acc.1,0x9e4d
0x9e3d  e0       movx a,@dptr
0x9e3e  30e00c   jnb  acc.0,0x9e4d
0x9e41  90086b   mov  dptr,#0x086b
0x9e44  e0       movx a,@dptr
0x9e45  d3       setb c
0x9e46  9423     subb a,#0x23              ; clamp against 0x23 / 0x14 / 0x0F
0x9e48  4003     jc   0x9e4d
0x9e4a  7423     mov  a,#0x23
0x9e4c  f0       movx @dptr,a
```

and the last copy falls into the `0x08C1` copy block at `0x9E89`, which is
where all seven arms converge:

```
0x9e89  9008c1   mov  dptr,#0x08c1
0x9e8c  e0       movx a,@dptr
0x9e8d  900865   mov  dptr,#0x0865
0x9e90  f0       movx @dptr,a              ; ... and 0x0866, 0x0867,
...                                         0x0868, 0x0869 in the same shape
0x9eb1  900784   mov  dptr,#0x0784          ; CPU_PL2
0x9eb4  e0       movx a,@dptr
0x9eb5  6005     jz   0x9ebc                ; read, and branched on
```

So the seven rows of §9.1 are one routine, and the table says "ditto" rather
than repeating the same twenty-address set seven times. `0x9E6B`'s USER-clear
arm is the one that starts at the `0x9E89` copy block itself.

### 9.3 What the arms do and do not do

**No arm found by this method writes a PL register.** Not `0x0783`, `0x0784`
or `0x0785` — in any of the 34 arms, and not in the 137 callee rows at
`--callee-depth 1`. §5's conclusion survives the arms: still no path found by
this method carries a per-mode default into a PL. What the arms add is a
*read*: the `0x9Exx` block loads `0x0784` (`CPU_PL2`) and `0x0785` (`PL4`) and
branches on them, so the mode bits gate code that *consults* the power limits
rather than one that sets them. Read and write are different claims and the
distinction is the whole of what §5 concluded, so this is a refinement of it
rather than a correction of it.

**Both candidate fan-PWM bytes are written by arms of a mode-bit branch.**
This is the result the issue was for, and it is a prediction *for* the
isolation run, not a result from it — no laptop is reachable from here and
nothing in this file has been observed on hardware. Addresses below are the
`mov dptr,#imm16` site, the same convention `trace_xdata_refs.py` counts.

- `0x075B` is written at the `0x89E0` site, which is in the **Fan Boost not
  set** arm of `0x899D` — and is reached from *both* arms of `0x8942` through
  it, since `0x8942`'s set arm clears `0x085F` and falls straight into the
  `0x899D` site. The value is staged through `0x1804` and comes from `0x0768`
  or `0x0469` depending on the carry out of `0xBBE6`. A second site, `0xBB29`,
  is reached only through a callee: `0xBB22` from the `0x8942`/`0x899D` arms
  (it falls through into it) and `0xBB28` from `0x8E8B`'s.
- `0x075C` is written at `0x8F0A`, in **both** arms of `0x8E8B` — the USER bit,
  not the Fan Boost bit — and again at `0x8F11`, inside the callee `0x8F0F`,
  which the `0x8942` and `0x899D` arms also call.

A byte scan of the main EC puts the two bytes' write sites at exactly five
addresses, and four of the five are the ones above: `0x89E0`, `0xBB29`,
`0x8F0A`, `0x8F11`. The fifth, `0x87C5`, is not reachable from any of the 34
arms or their `--callee-depth 1` callees, so whatever writes it is a path
these arms do not cover.

Neither address is in `registers.yaml`; issue #99 named them from the Windows
side and neither has been confirmed. What is established here is narrower and
is what the isolation run can act on: *the EC stores to both, on a path
selected by a bit of `0x0751`*. Whether that makes `0x0751` a usable control
is the question §4 of
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` exists to answer, and
it is now a better-posed question than it was, because the run has two named
bytes to watch and a named bit to flip.

**The mode bits gate a thermal test, not a duty copy.** `0x8942`'s
Fan-Boost-**set** arm — its fall-through, since `jnb acc.6` falls through when
the bit *is* set — reads `0x085F` against `0x3C` (60), then `0x086C`
against `0x50` (80), then **`CPU_TEMP` `0x043E` and `GPU_TEMP` `0x044F`
against `0x46` (70 °C)** — both `confirmed-working` in `registers.yaml` — and
if both are under the limit it goes on to clear Fan Boost *in `0x0751`
itself*:

```
0x8978  90043e   mov  dptr,#0x043e     ; CPU_TEMP
0x897b  e0       movx a,@dptr
0x897d  9446     subb a,#0x46          ; 70 degC
0x897f  501c     jnc  0x899d
0x8981  90044f   mov  dptr,#0x044f     ; GPU_TEMP
0x8986  9446     subb a,#0x46
0x8988  5013     jnc  0x899d
0x898a  900751   mov  dptr,#0x0751
0x898e  54bf     anl  a,#0xbf          ; clear FAN BOOST
0x8990  f0       movx @dptr,a
```

That is a second reason the byte may not stay as written, and it belongs
beside §4's `0xA812`/`0xA818` boot-time defaults: the EC writes `0x0751` on
at least three paths, and only one of them is the host. `0x93CA` and `0xB73C`
read `0x044F` and `0x043E` too, so the temperature dependency is not confined
to the Fan Boost arms.

**`0x8E8B`'s two arms differ only in a tachometer threshold.** USER set tests
`0x0460` and `0x0468` against `0x04`/`0x08`; USER clear tests the same two
bytes against `0x04`/`0x07`. Both then join at `0x8EFF` and write `0x075C`. So
the USER bit selects a comparison constant here, not a destination.

**The bank1 arms select a CODE pointer and converge.** `0x9432`'s two arms
load `0x93B6` and `0x93E6` respectively and both `sjmp` to `0x9444`, which
copies DPTR into `r2`/`r1`, offsets it by `r7`, and indexes it with `movc`.
USER set and clear pick which of two tables: set takes `0x943F` and loads
`0x93E6`, clear falls through to `0x943A` and loads `0x93B6` — the opposite
sense to the sixteen `jnb` rows above, because this one is a `jnz`. Both
`0x93B6` and `0x93E6` are CODE addresses and are not XDATA registers; the
arms' only XDATA claim is `0x0626`/`0x0627`/`0x0895`.

### 9.4 The callees

`--callee-depth 1` follows one level into every `lcall`/`acall`/`ljmp`/`ajmp`
target the 34 arms reach — 137 rows, all in the CSV. The ones that carry a
finding. The "set"/"clear" column is the bit's state on that path: a `jnb
acc.N,target` *falls through* when bit N is set and takes the branch when it is
clear, so a set path is a fall-through arm; `0x9432`'s `jnz` is the other way
round and is labelled from the code.

| callee | reached from | what it does |
| --- | --- | --- |
| `0xBB22` | `0x8942` (both arms), `0x899D` set | stages `0xC8` in `0x1804` and falls through into `0xBB28`, which writes `0x075B` |
| `0xBB28` | `0x8E8B` (both arms) | `movx a,@dptr ; mov dptr,#0x075B ; movx @dptr,a` |
| `0x8F0F` | `0x8942`/`0x899D` (all four arms) | reloads and stores to `0x075C`, then `mov r7,#0xA7` |
| `0xE389` | `0x8942` BOOST set | reads `0x0435`/`0x0434`, calls `0xE3C4`, stages in `0x0A50` |
| `0xBEA3` | `0x8942` BOOST set | reads `0x044C` |
| `0xBB40` | `0x89EE` USER clear | reads `0x0751` and masks it |
| `0xB716` | `0xB5EA` USER clear | the whole `ljmp` target; `0x08A2` write among others |
| `0xB82E` | `0xB73C` USER clear | the whole `ljmp` target; `0x08A0` write |

`0xE389` and `0xBEA3` are the pair the arm at `0x8949` calls before the
temperature test, and they read `0x0435`/`0x0434` and `0x044C` — sensor
addresses, not the temperatures themselves. What they compute is not
established here.

### 9.5 What this section does not say

The bounds are real and the negatives are scoped to them. Reading them as
"the EC does not" is the error `docs/findings.md` §4d had to retract, and §6
of this file is the worked counter-example on a second address: `0x0F00` has
zero direct sites and the EC provably writes it, because eight sites build
DPH at run time. So:

- The negatives above are **"no arm found by this method reaches X"**, and the
  method's blind spots are named in §9's own `unattributed` column: indirect
  `movx @Ri`, a DPTR built at run time, and a callee not followed. An arm with
  any of those is not a clean negative, and the CSV's `status` column says so
  per row.
- `0x075B` and `0x075C` being written is an **instruction-level** fact. It is
  not evidence the EC *acts* on `0x0751`, and per `CLAUDE.md` a write being
  stored is not evidence of anything behavioural.
- **Nothing here is a live test.** No register was read back and no hardware
  was observed. §9 is a static prediction handed to whoever runs
  `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` §4.4.
