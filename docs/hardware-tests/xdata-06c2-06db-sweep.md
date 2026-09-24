# The `bank1:0x8001` counter sweep, sampled live: `0x06D6`'s period, and which countdowns tick

**Status: the Linux arms were run on 2026-09-24, on the GM7MG7P itself, read
only.** They were run from a local session on the laptop at the owner's request,
not by the hosted pipeline (which cannot reach the hardware, `CLAUDE.md`).
Nothing was written to the EC. Three things from
`ec/annotations/xdata-06c2-06db-timers.md` §7 are **not** done and are listed in
§6: the Windows arm with the Control Center started and stopped, any run that
perturbs the machine (AC, power mode, lid) to load the countdowns, and §7's
third step as written, which cannot be run through this read path (§3).

Issue #257. The static reading this grades against is
`ec/annotations/xdata-06c2-06db-timers.md`; the summary is `docs/findings.md`
§17a.

## 1. What the code predicts

`bank1:0x8001`-`0x8189` is one routine
(`xdata-06c2-06db-timers.md` §2). Re-derivable from the committed image:

```console
$ cd ec/tools
$ python3 disasm8051.py ../firmware/GMxMGxx_11.800 --at 0x10001 --runtime 0x8001 -n 220
```

- **13 countdowns come before the `0x06D6` test**, in this order:
  `0x06C6 0x06CD 0x06D1 0x06D2 0x06F3 0x0635 0x0636 0x0637 0x0638 0x0639
  0x063A 0x0890 0x07F6`. They are decremented on every pass.
- **`0x06D6` at `0x806C`:** non-zero is decremented, stored, and the routine
  returns at `0x8074`; zero is loaded with 9 at `0x8075` and the pass continues.
  So **every pass changes `0x06D6` exactly once**, its step interval is the
  routine's own period, and a clean capture shows nothing but `-1` steps and
  `0 -> 9` reloads, ten passes to a cycle.
- **25 countdowns come after the return:** `0x06C2 0x06C3 0x06D8 0x06D9 0x06DA
  0x08E4 0x055F 0x09CE 0x070B 0x0706 0x06C5 0x085B 0x0986 0x070D 0x07F3 0x0981
  0x0982 0x0811 0x0809 0x0843 0x0844 0x06DB 0x080D 0x08A7 0x08A8`. They are
  reached only on the pass that found `0x06D6` zero, so they step at one tenth
  of the rate of the 13. `0x06D8`, `0x085B` and `0x06DB` are further gated on
  `0x0440 != 0`. `0x06D9` is further gated on both `lcall 0x1984` and
  `lcall 0x198A` leaving R7 zero.

13 + 25 + `0x06D6` = 39, the countdown total in §3 of the annotation.
`ec/tools/test_grade_timer_sweep.py` re-reads both lists from the image bytes
and fails if either drifts.

## 2. How it was run

Machine: GM7MG7P, NixOS, kernel 7.2.7, `uniwill_laptop` loaded, no vendor
service (Linux). AC connected, battery charging at 91%. The load average was
7.01 at the start of arm 1 and 2.09 just after it. What the operator was doing on the machine was not
controlled or recorded. Each capture's `#` header carries its own conditions.

All reads go through the physical ECMG window (`0xFE410000`, the `MMRW` path
the vendor's `ECRW` takes) with `ec/tools/ec_timer_capture.py`, which maps
`/dev/mem` read-only and refuses the fan page `0x0460`-`0x046F` (issue #94) and
any address outside the host window before it opens anything.

```console
$ cd ec/tools
# 0. Which pages the host window maps at all.
$ sudo python3 ec_timer_capture.py --census > host-window-page-census.txt
# 1. 0x06D6 alone, every 2 ms, 120 s.
$ sudo python3 ec_timer_capture.py --addrs 0x06d6 --interval 0.002 --seconds 120 \
      --csv 06d6-reload-linux.csv
# 2. Every sweep byte inside the host window, every 10 ms, 300 s.
$ sudo python3 ec_timer_capture.py --interval 0.01 --seconds 300 \
      --addrs 0x06C6,0x06CD,0x06D1,0x06D2,0x06F3,0x0635,0x0636,0x0637,0x0638,0x0639,0x063A,0x07F6,0x06D6,0x06C2,0x06C3,0x06D8,0x06D9,0x06DA,0x055F,0x070B,0x0706,0x06C5,0x070D,0x07F3,0x06DB,0x0621,0x0723,0x0440 \
      --csv 06c2-06db-sweep-linux.csv
# 3 (substitute, see section 3). 0x06D9 every 0.5 ms against 0x06D6, with the
#   in-window bytes of the routine that stores 3 into it.
$ sudo python3 ec_timer_capture.py --interval 0.0005 --seconds 60 \
      --addrs 0x06D6,0x06D9,0x04FE,0x0480,0x05F1,0x05F0,0x0490,0x0498,0x06DA \
      --csv 06d9-hold-linux.csv
# Grading, offline, over any of them:
$ python3 grade_timer_sweep.py <capture.csv>
```

The committed files are
`evidence/ec-watch/2026-09-24-host-window-page-census.txt`,
`evidence/ec-watch/2026-09-24-06d6-reload-linux.csv`,
`evidence/ec-watch/2026-09-24-06c2-06db-sweep-linux.csv` and
`evidence/ec-watch/2026-09-24-06d9-hold-linux.csv`.

## 3. The host window does not map 16 of the sweep's bytes, or either gate byte

The census reads every page of the 64 KiB mapping once. On this machine
`0x0000`-`0x07FF` and `0x0C00`-`0x0FFF` hold data; **every byte of
`0x0800`-`0x0BFF` and of `0x1000`-`0xFFFF` reads `0xFF`**. That is consistent
with the window not mapping those pages, and it is the same reading
`docs/findings.md` §4g already takes for `0x0A40`-`0x0A5F`. It is not a statement
about what the EC holds there. The sweep loses these bytes to it:

- 1 of the 13 before the return: `0x0890`;
- 13 of the 25 after it: `0x08E4 0x09CE 0x085B 0x0986 0x0981 0x0982 0x0811
  0x0809 0x0843 0x0844 0x080D 0x08A7 0x08A8`;
- 2 of the side-effect targets: `0x080C` and `0x0985`;
- **both gate bytes on `0x06D9`: `0x1664` (the `0xC1E7` test) and `0x3202`
  (the `0xC10C` thunk's callee, per issue #255 / PR #287).**

So §7's third step (read `0x1664`, and now `0x3202`, beside `0x06D9`) **cannot
be run through ECMG on this machine**. `0x0460` and `0x0468` are in the window
but were refused on purpose (the fan page). That leaves 24 countdowns, the
reload, `0x0621`, `0x0723` and the `0x0440` gate: 28 addresses, all in arm 2.

The census is also a finding for the rest of the repository: any
`registers.yaml` row at `0x0800`-`0x0BFF` or at `0x1000` and above cannot be
read live through this window, and per `docs/findings.md` §4e the vendor's
`ECRW` path goes through the same window.

## 4. Results

**`0x06D6` behaves exactly as the code says, and its period is 1.0 s.**

| capture | sample | span | `0x06D6` changes | `-1` steps | `0 -> 9` reloads | anything else | step, median / mean | cycle, median / mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| arm 1 | 2 ms | 120 s | 1204 | 1084 | 120 | 0 | 100.0 / 99.72 ms | 0.998 / 0.9972 s |
| arm 2 | 10 ms | 300 s | 3009 | 2708 | 301 | 0 | 100.0 / 99.70 ms | 1.000 / 0.9970 s |
| arm 3 | 0.5 ms | 60 s | 602 | 542 | 60 | 0 | 100.0 / 99.75 ms | 0.997 / 0.9975 s |

- Every change in all three captures is a `-1` step or the `0 -> 9` reload,
  so no other writer touched `0x06D6` at a moment a sample could resolve.
- The step is 98-102 ms in arm 1, one 2 ms sample either side of 100 ms. Arm 2's
  wider 89-111 ms spread is its 10 ms sampling. **The routine at `0x8001` runs
  about every 99.7 ms by the host clock**, very regularly, and the part after
  the return runs once per 0.997 s. That is the 10x relation the code predicts,
  and arm 1 measures it as 9.98.
- The committed Windows captures agree once aliasing is accounted for.
  `evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv` samples about
  every 0.48 s and carries 260 rows for `0x06D6`, alternating between values 5
  apart (`0x02`/`0x07`, `0x03`/`0x08`): a 1 s ten-step cycle sampled at about
  half its period.

**No other in-window countdown moved.** In arm 2, 23 of the 24 countdowns held
still for the full 300 s at `0x00`, and so did `0x0621` and `0x0723`. `0x0440`
held at `0x07`, which is non-zero, so its gate was not what kept `0x06D8`,
`0x06DB` or `0x085B` still (the last is out of window anyway). The committed
`2026-09-18` AC plug-in summary (`0x0000`-`0x07FF`, 0.4 s) lists `0x06D6` and
no other sweep byte, and the Windows profile-switch capture above has rows for
`0x06D6` and for none of the others. So on idle Linux, across an AC plug-in,
and across Windows profile switches, these countdowns sat at zero: **not reached
on the paths watched**, which is not "not a countdown" and not absent. Because
none of them was loaded, **the rate-ratio test between the two groups could not
be measured**. `grade_timer_sweep.py` says so rather than printing a ratio.

**`0x06D9` held at `0x03` throughout, while the code that reaches its gate ran
about once a second.** Every `0 -> 9` reload is the store at `0x8077`, and the
same fall-through reaches the two gate calls at `0x8096`/`0x809C`. So the gate
was consulted with `0x06D9` non-zero at least 301 times in arm 2 and 60 times in
arm 3, and **no decrement is visible at either 10 ms or 0.5 ms resolution**.
Two readings survive, and this capture cannot fully separate them:

1. a gate returned non-zero on every pass (`0x1664` bit 0 set, or bits 1 and 2
   of `0x3202` both set), so the decrement never ran; or
2. the decrement ran and something stored `0x03` back within 0.5 ms each time.
   One writer that stores exactly `0x03` is known: bank1 `0x982E`, in
   `enter_state_0480_05f1_06d9` (`0x9817`).

The in-window bytes around that writer narrow it without settling it. The only
jumps to `0x9817` in the exported listings are the two `ljmp`s in `0x976E`
(`clear_0480_bit0_then_step_05f1_countdown`, `ec/decompiled/bank1/976E.asm`
lines 10 and 15). That routine goes there if `0x04FE` bit 0 is set, or if bit 1
is clear and `lcall 0x198A` leaves R7 non-zero. A jump from code in an
unexported gap would not show up in that search.
`0x04FE` held at `0x00` for arm 3's 60 s, so on that entry **`0x9817` is only
reachable when `0x198A` (`test_1664_bit0`) returns non-zero, and that is the
same call that closes `0x06D9`'s second gate in the sweep**. `0x0480` held at
`0x03` (bit 0 set, which `0x9817` sets and `0x976E`'s other arm clears) and
`0x05F1` at `0x01` (which `0x9817` stores). That is the state `0x9817` leaves
behind. Both readings therefore point at `0x1664` bit 0 being set. **That is an
inference from code and from in-window bytes, not a read of `0x1664`.** It
assumes `0x976E` is the only way into `0x9817` and that no other writer holds
`0x0480`/`0x05F1`. The first is only as good as the listing search above, and
the second has not been searched for.

## 5. What this settles and what it does not

Settled, from the captures:

- `0x06D6` is a live 10-step countdown reloaded with 9, and the only writer
  visible in three captures is the sweep. **Its period is 0.997 s (1.0 s to the
  precision that matters), and the sweep at `0x8001` runs every ~99.7 ms.**
  These are the two numbers issue #257 asked for.
- The early return at `0x8074` does what the listing says, at least for
  `0x06D6`: ten passes to a cycle.
- On this machine ECMG maps `0x0000`-`0x07FF` and `0x0C00`-`0x0FFF` and nothing
  else.

Not settled:

- **The rate ratio between the 13 and the 25.** Nothing was loaded. It needs a
  run that loads the countdowns (§6).
- **Whether `0x06D9`'s gate is `0x1664`, `0x3202`, or a rewrite.** §4's
  inference points at `0x1664` bit 0. A read of `0x1664` needs a path the host
  window does not give.
- **What `0x06D6` times, or what any countdown counts.** A period is not a
  purpose. The block keeps its `XDATA_<addr>` names.
- **The 16 bytes outside the window** were not observed at all. For them this
  capture is silent, not a zero.
- **Anything with the vendor service up.** This was Linux.

## 6. What is left, for a human with the machine

1. **Load the countdowns and measure the ratio.** Run arm 2's command with
   `--mark`, and perturb the machine one action at a time, about 30 s apart:
   AC out, AC in, a power-mode change, lid close and open, suspend and resume.
   `0x06DA`, `0x06D8` and `0x070B` have known writers in the `0x976E` routine
   (`0x0A`), and a byte that gets loaded then shows its decrement interval
   directly. `grade_timer_sweep.py` prints the ratio as soon as one byte in
   each group makes two consecutive `-1` steps. Read-only, but the AC and
   suspend actions are the operator's.
2. **The Windows arm** from §7 of the annotation: `ec_watch.py` over
   `0x06C0`-`0x06DF` with the Control Center started and stopped.
3. **A read path to `0x1664` and `0x3202`.** Something other than the ECMG
   window, if the EC offers one. Until then §7's third step stays unrunnable
   as written.
