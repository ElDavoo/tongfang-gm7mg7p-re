# The two counter-sweep sites no listing covers, decoded across the gap (issue #625)

`bank1:0x81E7` and `bank1:0xA6DC` are the two census sites of
[`counter-sweep-entry-set.md`](counter-sweep-entry-set.md) that a committed
`.asm` listing cannot classify, because no listing covers the bytes they sit
in. They were reported there as *in a committed gap* — a **different kind of
"not found by this method"** from an identified operand byte, and deliberately
kept apart from one. **Both are now named**: each is the last byte of a
PC-relative branch the image holds, decoded forward across the gap from the
last committed instruction start before it, by
[`ec/tools/gap_span_decode.py`](../../ec/tools/gap_span_decode.py).

`0x81E7` is the `rel8` of a `jc` at `0x81E6`; `0xA6DC` is the `rel8` of a
`cjne` at `0xA6DA`. Both go through the *same* `bucket_of_site()` every other
row in the run goes through — the decode supplies an owner address, an opcode
and a byte index, and the predicate that reads them is one function, not two —
so the sweep's histogram moves rather than gaining a seventh category, and
§3's `gap` row is now a measurement instead of a blind spot. **The headline is
unchanged: exactly one of the 180 sites is at an instruction start**, and it is
still `bank1:0xABB8` `lcall 0x8001` at 24 of 24. `counter_sweep_entry.py
--self-test` asserts the set, not the count.

**The decode is a weaker class of evidence than a listing, and is labelled
`gap-decode` wherever it is used.** The 178 listing-classified sites are settled
against a committed instruction that **names** the owning bytes; these two are
settled against a **decode** of them. `disasm8051.py`'s own docstring is the
standing limit and it applies verbatim — a linear walk is "evidence about
framing, not proof of it", it reads no dispatch table, follows no branch and
recovers no function boundary. Nothing below says a listing agrees, because no
listing covers these bytes.

## The method, and what beside the decode actually corroborates it

Ghidra exported one function per `.asm` and stopped where the function
stopped, so a gap is a boundary of the **listing set**, not a hole in the byte
stream. The image still has an instruction there; the question is which one.
The tool answers it by walking forward from the last committed instruction
start before the gap, using `disasm8051.decode()` — the same stepping rule
`converges_from()` walks, so the two cannot drift — until the walk covers the
site. Per site it reports the gap's own bounds, the left anchor, the
instruction that owns the site, and three measurements. **One of the three
corroborates the decode, one settles nothing either way, and one does not
discriminate at all** — saying which is most of this section:

- **the row's own `earlier_record` cell**, a transcription of the owning
  instruction's bytes made by `audit_call_targets.py` from the same image by a
  different method — a candidate record *spanning* the site, scored by
  `converges_from()` and tie-broken by how far it reaches. That it lands on the
  same address and the same bytes is the corroboration, and **both sites are
  re-grounded on it alone**. Its limit is worth naming: `earlier_record()` only
  ever offers candidates at `off-1` or `off-2`
  ([`audit_call_targets.py:196`](../../ec/tools/audit_call_targets.py)), so at
  `0x81E7` exactly one candidate exists and the `converges_from()` tie-break
  never runs. It confirms the owner address and the raw bytes. It says nothing
  about the framing of the 120 bytes around them;
- **`converges_from()` at the site, equal to the `frame_onto`/`frame_over`
  `bank-call-targets.csv` already records** for that row. Here that is
  corroboration rather than a new claim, because `counter_sweep_entry.py
  --self-test` already asserts it for all 180 rows. The two sites do not score
  alike, and the page below does not pretend they do — and a low score settles
  nothing in the other direction either, being `converges_from()`'s own "not
  thereby misframed" case;
- **the re-entry check, which is reported and carries no weight.** Each of the
  24 byte anchors ending at the left anchor — the same `back=24` the census's
  frame score uses — is walked forward across the whole gap and asked where it
  lands. **24 of 24 land exactly on the first byte the next listing covers, at
  both sites.** That is what the metric returns on this image, and
  `--reentry-calibration` measures that rather than assuming it:

  - **Control.** The same walk over the **four** other `bank1` unlisted
    stretches of the two sites' own size — 100–145 bytes from the listing
    run's last instruction start to the next listing start, which is the
    geometry `0x81E7` (121) and `0xA6DC` (124) have. All four read **24 of 24**,
    and in all four every one of the 24 anchors is covered by a listing. Same
    geometry, stretches this tool is not being asked to settle, same answer;
  - **Perturbation.** Keep each site's real endpoints, replace **every** byte
    inside the gap with a random one, and walk it: `0x81E7` still reads 24 of
    24 in **185 of 300** fillings and `0xA6DC` in **201 of 300**. A check that
    validated the region it is pointed at would not come out aligned two
    fillings in three of noise.

  The anchors' own coverage is measured for the same reason, and it is not
  uniform: **24 of 24** at `0x81E7`, and **15 of 24** at `0xA6DC`, where the
  nine anchors `0xA6BC`-`0xA6C4` sit in a *second* unlisted stretch that no
  listing covers either — so nine of the 24 starting points the walk departs
  from are themselves unframed bytes here. The 24 of 24 stays in the report,
  in `--csv` and in the self-test as a measured figure. It is not evidence
  about these bytes and nothing below rests on it.

The tool **refuses an address a committed listing does cover** rather than
answering it. Running it against an already-classified site and reading its
answer as a second opinion is the mistake both `converges_from`'s docstring and
`../ec/annotations/bank-call-audit.md` §1 argue against, so a covered `--at` is
an error and the self-test asserts the refusal.

## The two results

Both are the tool's own output. The two `re-entry` lines under each owner are
the calibration §2 describes; the owner address, its bytes and the byte index
are what they were before those lines were added.

```console
$ python3 ec/tools/gap_span_decode.py --at 0x81E7 --region bank1
## gap_span_decode: bank1:0x81E7

  census row      0x101E7  ljmp 0x8008  frame 0/24
  earlier_record  0x101E6 40 02 jc 0x81ea
  committed gap   0x818A-0x8201, 120 bytes, covered by no listing
  left anchor     0x8189  `ret`  -- the last committed instruction start before the gap
  re-entry        24 of 24 anchors decode across the gap and land exactly on 0x8202
  re-entry rate   24 of the 24 anchors are covered by a committed listing; the same walk reads 24 of 24 on 4 of the 4 other 100-145-byte unlisted stretches in bank1
  re-entry base   185 of 300 fillings of this gap with every byte inside it replaced by a random one still read 24 of 24, so the figure above is this metric's base rate on this image and not a finding about these bytes
  frame           0/24 here, 0/24 recorded in bank-call-targets.csv -- agree
  owner           0x81E6  `40 02`  jc 0x81ea
  the site        byte 2 of 2 of that instruction

  the gap decoded from 0x8189 to 0x8202, which is the framing the owner above is read in:

    0x8189  22        ret
    0x818A  90 04 72  mov dptr,#0x0472
    0x818D  74 20     mov a,#0x20
    0x818F  f0        movx @dptr,a
    0x8190  90 04 57  mov dptr,#0x0457
    0x8193  e0        movx a,@dptr
    0x8194  54 f8     anl a,#0xf8
    0x8196  44 fd     orl a,#0xfd
    0x8198  f0        movx @dptr,a
    0x8199  90 09 7c  mov dptr,#0x097c
    0x819C  e0        movx a,@dptr
    0x819D  54 01     anl a,#0x01
    0x819F  70 23     jnz 0x81c4
    0x81A1  90 09 7f  mov dptr,#0x097f
    0x81A4  e0        movx a,@dptr
    0x81A5  54 01     anl a,#0x01
    0x81A7  70 1b     jnz 0x81c4
    0x81A9  12 19 90  lcall 0x1990
    0x81AC  ef        mov a,r7
    0x81AD  70 15     jnz 0x81c4
    0x81AF  12 19 8a  lcall 0x198a
    0x81B2  ef        mov a,r7
    0x81B3  70 0f     jnz 0x81c4
    0x81B5  90 07 56  mov dptr,#0x0756
    0x81B8  e0        movx a,@dptr
    0x81B9  70 09     jnz 0x81c4
    0x81BB  90 08 45  mov dptr,#0x0845
    0x81BE  e0        movx a,@dptr
    0x81BF  70 03     jnz 0x81c4
    0x81C1  12 19 96  lcall 0x1996
    0x81C4  22        ret
    0x81C5  12 8c ec  lcall 0x8cec
    0x81C8  90 04 72  mov dptr,#0x0472
    0x81CB  e0        movx a,@dptr
    0x81CC  54 10     anl a,#0x10
    0x81CE  44 01     orl a,#0x01
    0x81D0  f0        movx @dptr,a
    0x81D1  90 04 57  mov dptr,#0x0457
    0x81D4  e0        movx a,@dptr
    0x81D5  54 f8     anl a,#0xf8
    0x81D7  f0        movx @dptr,a
    0x81D8  12 19 9c  lcall 0x199c
    0x81DB  90 08 00  mov dptr,#0x0800
    0x81DE  e0        movx a,@dptr
    0x81DF  54 80     anl a,#0x80
    0x81E1  70 14     jnz 0x81f7
    0x81E3  12 82 0f  lcall 0x820f
    0x81E6  40 02     jc 0x81ea   <-- the site, byte 2 of 2
    0x81E8  80 08     sjmp 0x81f2
    0x81EA  90 08 03  mov dptr,#0x0803
    0x81ED  e0        movx a,@dptr
    0x81EE  60 2f     jz 0x821f
    0x81F0  14        dec a
    0x81F1  f0        movx @dptr,a
    0x81F2  12 8d bc  lcall 0x8dbc
    0x81F5  40 2e     jc 0x8225
    0x81F7  12 8d 62  lcall 0x8d62
    0x81FA  50 12     jnc 0x820e
    0x81FC  90 04 7e  mov dptr,#0x047e
    0x81FF  74 cd     mov a,#0xcd
    0x8201  f0        movx @dptr,a

```

```console
$ python3 ec/tools/gap_span_decode.py --at 0xA6DC --region bank1
## gap_span_decode: bank1:0xA6DC

  census row      0x126DC  ljmp 0x8017  frame 1/24
  earlier_record  0x126DA b5 04 02 cjne a,0x04,0xa6df
  committed gap   0xA6D5-0xA74F, 123 bytes, covered by no listing
  left anchor     0xA6D4  `ret`  -- the last committed instruction start before the gap
  re-entry        24 of 24 anchors decode across the gap and land exactly on 0xA750
  re-entry rate   15 of the 24 anchors are covered by a committed listing; the same walk reads 24 of 24 on 4 of the 4 other 100-145-byte unlisted stretches in bank1
  re-entry base   201 of 300 fillings of this gap with every byte inside it replaced by a random one still read 24 of 24, so the figure above is this metric's base rate on this image and not a finding about these bytes
  frame           1/24 here, 1/24 recorded in bank-call-targets.csv -- agree
  owner           0xA6DA  `b5 04 02`  cjne a,0x04,0xa6df
  the site        byte 3 of 3 of that instruction

  the gap decoded from 0xA6D4 to 0xA750, which is the framing the owner above is read in:

    0xA6D4  22        ret
    0xA6D5  e9        mov a,r1
    0xA6D6  b5 03 06  cjne a,0x03,0xa6df
    0xA6D9  ea        mov a,r2
    0xA6DA  b5 04 02  cjne a,0x04,0xa6df   <-- the site, byte 3 of 3
    0xA6DD  80 17     sjmp 0xa6f6
    0xA6DF  c0 83     push 0x83
    0xA6E1  c0 82     push 0x82
    0xA6E3  89 82     mov 0x82,r1
    0xA6E5  8a 83     mov 0x83,r2
    0xA6E7  e4        clr a
    0xA6E8  93        movc a,@a+dptr
    0xA6E9  a3        inc dptr
    0xA6EA  a9 82     mov r1,0x82
    0xA6EC  aa 83     mov r2,0x83
    0xA6EE  d0 82     pop 0x82
    0xA6F0  d0 83     pop 0x83
    0xA6F2  f0        movx @dptr,a
    0xA6F3  a3        inc dptr
    0xA6F4  80 df     sjmp 0xa6d5
    0xA6F6  22        ret
    0xA6F7  90 18 04  mov dptr,#0x1804
    0xA6FA  74 78     mov a,#0x78
    0xA6FC  f0        movx @dptr,a
    0xA6FD  90 18 09  mov dptr,#0x1809
    0xA700  74 78     mov a,#0x78
    0xA702  f0        movx @dptr,a
    0xA703  90 1f 06  mov dptr,#0x1f06
    0xA706  74 00     mov a,#0x00
    0xA708  f0        movx @dptr,a
    0xA709  90 1f 09  mov dptr,#0x1f09
    0xA70C  74 f0     mov a,#0xf0
    0xA70E  f0        movx @dptr,a
    0xA70F  22        ret
    0xA710  90 1f 06  mov dptr,#0x1f06
    0xA713  74 00     mov a,#0x00
    0xA715  f0        movx @dptr,a
    0xA716  90 1f 09  mov dptr,#0x1f09
    0xA719  74 05     mov a,#0x05
    0xA71B  f0        movx @dptr,a
    0xA71C  90 08 02  mov dptr,#0x0802
    0xA71F  e0        movx a,@dptr
    0xA720  54 df     anl a,#0xdf
    0xA722  f0        movx @dptr,a
    0xA723  22        ret
    0xA724  90 1f 02  mov dptr,#0x1f02
    0xA727  74 00     mov a,#0x00
    0xA729  f0        movx @dptr,a
    0xA72A  90 1f 03  mov dptr,#0x1f03
    0xA72D  74 00     mov a,#0x00
    0xA72F  f0        movx @dptr,a
    0xA730  90 1f 04  mov dptr,#0x1f04
    0xA733  74 80     mov a,#0x80
    0xA735  f0        movx @dptr,a
    0xA736  90 1f 06  mov dptr,#0x1f06
    0xA739  74 00     mov a,#0x00
    0xA73B  f0        movx @dptr,a
    0xA73C  90 1f 09  mov dptr,#0x1f09
    0xA73F  74 05     mov a,#0x05
    0xA741  f0        movx @dptr,a
    0xA742  90 1f 01  mov dptr,#0x1f01
    0xA745  74 27     mov a,#0x27
    0xA747  f0        movx @dptr,a
    0xA748  22        ret
    0xA749  90 1f 07  mov dptr,#0x1f07
    0xA74C  74 5c     mov a,#0x5c
    0xA74E  f0        movx @dptr,a
    0xA74F  22        ret

```

And the calibration both `--at` reports above is quoting, on its own:

```console
$ python3 ec/tools/gap_span_decode.py --reentry-calibration
## gap_span_decode: what the re-entry check is worth in bank1

  **4 of the 4 other 100-145-byte unlisted stretches** in bank1, walked exactly as a site is walked and with the 24 anchors starting at the listing run below each one, read 24 of 24 as well:

  | anchor | unlisted stretch | stretch | anchors a listing covers | re-entry |
  |---|---|---:|---:|---:|
  | `0x8A03` | `0x8A04-0x8A6B` | 105 | 24/24 | 24/24 |
  | `0x9385` | `0x9386-0x9415` | 145 | 24/24 | 24/24 |
  | `0xBB3D` | `0xBB40-0xBBA3` | 103 | 24/24 | 24/24 |
  | `0xE42A` | `0xE42D-0xE48F` | 102 | 24/24 | 24/24 |

  And the walk barely notices that the region it is validating is nonsense: with each site's own endpoints kept and **every byte inside the gap replaced by a random one**, it still reads 24 of 24 in

  | site | fillings still reading 24 of 24 |
  |---|---:|
  | `bank1:0x81E7` | 185 of 300 |
  | `bank1:0xA6DC` | 201 of 300 |

  A framing invented by a byte scan inside an unframed stretch was never going to cross the whole of it and come out aligned from 24 starting points. It does, about two fillings in three of pure noise, and it does on every stretch of this size that this tool is not being asked about. The 24 of 24 at a site is what this metric returns on this image.

```

**The two sites are not equally well evidenced, and the page does not average
them.** `0xA6DC` scores 1 of 24 and its span *reads* as one coherent
instruction sequence: a `DPTR`-to-`DPTR` block copy that saves R1/R2 into
`0x82`/`0x83` before the `movc` and restores them after, loops back to
`0xA6D5` on `sjmp`, and counts the two lengths in A before the `movx @dptr,a`.
A misframed read does not produce a balanced push/restore around a `movc`; that
is the same kind of byte argument
[`bank1-e582-entry-framing.md`](bank1-e582-entry-framing.md) makes about the
`push 0x07`/`lcall`/`pop 0x07` triple at `0xE57E`. So `0xA6DC` has the census's
cell **and** a structural argument, from two different directions.

`0x81E7` scores **0 of 24** and its span carries no argument of that kind — it
is ordinary XDATA flag-testing code, and a `jc` over a 2-byte displacement is
what any number of framings would produce. The 0/24 is stated beside it rather
than buried: a site nobody syncs onto is not thereby misframed, and the reading
here does not need it to be. But with the re-entry check withdrawn above, that
leaves one thing standing.

### Named residual: `0x81E7` rests on a single witness

**`0x81E7`'s owner rests on the census's `earlier_record` cell alone** — not on
the frame score (0 of 24), not on the re-entry check (which does not
discriminate), and not on a byte argument (its span carries none). That cell is
a transcription of `0x101E6 40 02` made by `audit_call_targets.py` from the same
image by a different method, and it names the same address and the same two
bytes the decode does. It is the strongest thing available for this site and
also the whole of the case: **one producer agreeing with another on two bytes.**

What would move it is named so a later reader does not have to guess. The
headline "exactly one of the 180 is at an instruction start" holds for the other
179 sites on committed listings that *name* the owning instruction. For
`0x81E7` it holds only because the single witness says the site is byte 2 of a
two-byte `jc`. Were that cell wrong, `0x81E7` would be the one site in the run
whose class rests on nothing at all, and the headline would have to be re-read
against whatever the bytes turned out to be.

Nothing found here says the cell is wrong, and it is the strongest thing
available for this site — but its candidate set is two offsets, one of which
did not span the site at all, so what the two producers agree on is *which of
two adjacent bytes owns it*, not the 120 bytes around them. The image settles
this site's **owner** rather than its **framing**, and that is the limit the
issue's fallback branch exists for: a site the image cannot settle is carried
as a stated residual with the method's limit named, not folded into the
histogram as though it had been settled by the same method as its neighbours.
Nothing in this repository's methods closes it; what would is a second producer
reaching `0x81E7` by a route that is not "the one or two bytes before the site",
or a trace of the running EC, which is a human at the machine and is listed as
a follow-up below.

## What moved in the sweep, and what did not

`counter_sweep_entry.py`'s own histogram is the source for the figures; this
page does not keep a second copy:

```console
$ python3 ec/tools/counter_sweep_entry.py
## 2. What those sites are, and what names the bytes

  180 site(s), 70 distinct target(s), 108 scoring 0/24

| what the site is | count |
|---|---:|
| an instruction start | 1 |
| the rel8 displacement byte of a `cjne` -- opcode 0xb4, 0xb5, 0xba or 0xbf, each of which ends in 0x02 or 0x12 | 136 |
| the rel8 displacement byte of another PC-relative branch | 40 |
| the low target byte of an `ljmp`/`lcall` the listing already carries | 1 |
| an immediate operand of an instruction that is not a branch | 2 |
| in a committed gap, and named by neither a listing nor the gap decode | 0 |

  178 of the 180 are named by a committed `.asm` listing and 2 by a decode across a committed gap (`ec/tools/gap_span_decode.py`). The second is the weaker of the two classes -- a listing names the owning bytes, a decode reads them -- and `docs/findings/counter-sweep-gap-sites.md` states its limit beside them.
```

Three consequences follow, and all three are asserted in
`counter_sweep_entry.py --self-test` rather than left to a reader:

- **`gap` is 0.** No site in the run is left unclassified by either method, and
  the six buckets still sum to the 180. A site the decode *had* failed to reach
  would stay in the `gap` bucket — the issue's fallback branch, kept live — and
  the bucket is what it would land in;
- **the headline is unchanged.** Exactly one of the 180 is at an instruction
  start, and the self-test now asserts the *set* `{0xABB8}` rather than the
  count, because a count would not catch a second site arriving at index 0 of
  its owner;
- **`0x8017` loses an exception — to a narrower claim, not a wider one.** It
  was the only one of the five annotation-argued addresses whose best site was
  a gap byte, which is the whole reason
  [`counter-sweep-entry-set.md`](counter-sweep-entry-set.md) §4 said "*except*
  `0x8017`". Its best site is now named — the `rel8` of the `cjne` at
  `0xA6DA` — so it is refuted as an entry candidate like `0x8008` and `0x8010`,
  and the exception clause is gone because the reason for it is. **The
  refutation is stated at the strength its evidence class allows**: `0x8008`
  and `0x8010` are refuted against committed listings that name the owning
  bytes, and `0x8017` against a decode across a committed gap, which is the
  weaker of the two classes. A `cjne` displacement is not a call either way,
  but "the same evidence as every other" would be the wrong sentence for the
  one row of the three that reads `gap-decode` — which is exactly why the
  per-target table carries a `site source` column, so that row cannot pass for
  a listed operand.

## What this does not establish

- **Not a listing's agreement, because there is none.** No committed `.asm`
  covers any byte of either gap. These two are a decode, and every table they
  appear in now says which class they are in.
- **Not a proof of framing.** `disasm8051.py`'s docstring is the limit: a
  linear walk reads no dispatch table, follows no branch and recovers no
  function boundary, so a gap beginning in the middle of a data structure would
  decode exactly as convincingly. The re-entry check does **not** repair that
  limit — the control and the perturbation in §2 are there to show it is this
  metric's base rate rather than a witness, and a check that survives random
  bytes is not evidence about the bytes it read. So what stands behind these two
  decodes is the `earlier_record` agreement, and for `0x81E7` that is one
  witness, named above as a residual rather than smoothed over here.
- **Not 180 absent calls, and not a second opinion on the other 178.** The tool
  refuses a covered address for exactly this reason.
- **Not a register claim.** No `status:` in `../ec/annotations/registers.yaml`
  moves; the sweep's 43 XDATA addresses keep the readings
  `../ec/annotations/xdata-06c2-06db-timers.md` gives them.
- **Not a live observation.** No byte was read, written or read back, and no
  behaviour was observed. This is a byte-frame and text measurement over
  committed inputs, reproducible by anyone holding the committed firmware.
- **Not a gap census, and not #594.** How many census sites tree-wide sit in a
  committed gap, and what they decode to, is a census this change
  deliberately does not run: the tool takes one `--at`, and enumerating the
  gaps of `bank1` or of any other program is a separate and larger job.
  #594 classifies bucket-A/C rows **against the committed listings**, and a
  site in a gap is outside what that method reaches — #594 would still report
  these two as gaps, and this change does not pre-empt it.
- **Not on the far side of the rebuild line.** No `.asm`, `.c`, `index.csv`,
  `ghidra-functions.csv`, `bank-call-targets.csv` or `reassembly.csv` row moved,
  and the deferred rebuild in
  [`counter-sweep-entry-set.md`](counter-sweep-entry-set.md) §7 is untouched.
  `verify_reassembly.py --check` is the direct evidence, and it needs no
  assembler: it compares every byte of every committed listing against the
  firmware image and recomputes every `listing_digest` from the listing it
  names, on any machine. It prints `listing bytes: 45661 instruction(s)
  checked against the firmware, 0 disagreement(s)` and `listing digests: 2717
  compared against the committed report, 0 disagreement(s)`, then `all checks
  passed`. The
  `sdas8051 not found` message belongs to `verify()` — the full re-encode tier,
  which needs SDCC and which this change does not rely on; `--check` dispatches
  to `check()` and never reaches it. Either way `--write-digests` must **not**
  be run for it.

## Reproducing it

```console
$ python3 ec/tools/gap_span_decode.py --at 0x81E7 --region bank1
$ python3 ec/tools/gap_span_decode.py --at 0xA6DC --region bank1
$ python3 ec/tools/gap_span_decode.py --reentry-calibration
$ python3 ec/tools/gap_span_decode.py --csv
$ python3 ec/tools/gap_span_decode.py --self-test
$ python3 ec/tools/counter_sweep_entry.py --self-test
```

`gap_span_decode.py --self-test` asserts both gaps' spans and left anchors,
each owner address with its raw bytes **and** its `mnemonic()` text, each site's
byte index within its owner, 24-of-24 re-entry on each, **how many of that 24 a
listing actually covers — 24 of 24 at `0x81E7` and 15 of 24 at `0xA6DC`, asserted
per site so the second reads as the exception it is** — `converges_from()`
equal to the census's recorded pair, and the `earlier_record` cell equal to the
owner address and bytes. It also asserts that the base rate is what §2 says it
is (every same-geometry control reads 24 of 24, and there is at least one), and
the refusal, so the tool cannot be run against an already-classified site and
its answer read as a second opinion.

Beside them, unchanged by this change but decisive for it:

```console
$ python3 ec/tools/verify_reassembly.py --check   # proves no committed listing moved
$ python3 ec/tools/gen_findings_index.py > docs/findings/INDEX.md
$ python3 ec/tools/gen_findings_index.py --check
$ python3 ec/tools/check_no_conflict_markers.py
$ python3 ec/tools/check_no_append_logs.py
$ python3 ec/tools/check_findings_frozen.py
$ bash .github/scripts/agent-gates.sh
$ bash tools/run-tests.sh
```

**`gap_span_decode.py --self-test` is not in the cheap gate tier, and cannot
be from this change.** `.github/scripts/agent-gates.sh` and the workflow files
around it are copied from
[`agent-pipeline`](https://github.com/ElDavoo/agent-pipeline), and the plan
stage's push token has no `workflow` scope, so a branch touching them fails at
the end rather than the start. The route is a `docs/ci/agent-gates-*.patch`
plus an upstream change and a re-copy — a human's, and the reason the tool is
run from the block above instead. `counter_sweep_entry.py` is in the same
position today.

## Follow-ups

- How many census sites tree-wide sit in a committed gap, and what do they
  decode to? `gap_span_decode.py` takes one `--at`; the census is a flag away
  and is deliberately not run here.
- A second producer for `bank1:0x81E7` that reaches it by something other than
  "the one or two bytes before the site" — a forward walk from the next listing
  start backwards, a scan seeded from a control-flow edge rather than from the
  site — which is what would close the residual above. `0xA6DC` does not need
  it, and the shape of the answer is already known for both sites; what is
  missing is an independent route to `0x81E7`. A trace of the running EC would
  settle it directly and needs a human at the machine: preparing that run is
  its own issue, and nothing here has been tested against hardware.
- Whether the unlisted stretch `0xA6BC`-`0xA6C4` below the `0xA6DC` gap is its
  own decoding problem. Nine of that site's 24 re-entry anchors start inside
  it, and nothing here says whether a listing cut or a function end is what
  makes it unlisted.
- A gate line for `gap_span_decode.py --self-test`, which needs a
  `docs/ci/agent-gates-*.patch` and an `agent-pipeline` re-copy.
