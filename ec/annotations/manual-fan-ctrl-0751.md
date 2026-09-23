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
```

The 29 rows are the same 29 that `registers.yaml` records as
`static_refs_main_ec` and that `ec/tools/check_register_counts.py` recomputes
from the image, so the table below cannot silently disagree with the number
the rest of the repo quotes. `--callee-depth 1` adds nothing here: the
`callee`/`callee_window` columns are empty for all 29, because no site hands
`DPTR` to a subroutine.

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

## 8. What is still open

- **The whole live question.** Nothing above is a behavioural test. Writing
  `0x0751` and watching is `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`,
  which has not been run.
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
