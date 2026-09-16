# The PD image's index-helper family, and the geometry behind `0x04A6`

Two files stop at the same sentence. `ec-0x07d0-sites.md` §4 decoded an array
of `0x60`-byte records based at `0x0408` and recorded it as "contents
unidentified". `pd-xdata-overlap.md` §4 found all four PD-image `0x04A6` sites
computing `0x04A6 + R3×0x60 + 2×R3×0x100 + A×0x1F` and said naming the records
"would be a guess and is not made here", with §6 listing "no control-flow
recovery" as the reason the callers were untraced.

This file answers the *arithmetic* those two stopped short of and says
explicitly which of the three questions it still cannot answer. It adds no
retraction: both files' verdicts stand as written, including
`pd-xdata-overlap.md`'s headline that the two images' XDATA maps look
independent as far as static evidence goes.

**What is new here.**

- All eleven named helper routines decode. Ten reduce to one or two symbolic
  terms added to DPTR; the eleventh (`0x9A71`) is not an address helper at all
  and is reported as unmodelled rather than fitted to a term (§2).
- The record stride in this run is `0x260`, not `0x60`. Where a site's two
  index terms both name an identified register, it is the *same* register in
  37 of 37 cases, and `Rn×0x60 + Rn×0x200` is `Rn×0x260` (§3.2). That is
  algebra on the decoded terms, not a new inference.
- All four `0x04A6` sites now have a containing routine and its caller, each
  with its own framing evidence (§4). **No index range is bounded by it**, so
  no record count is stated anywhere in this file — see §5.

**Nothing here was observed on hardware.** No register was read, written or
read back; this is a static decode of `ec/firmware/GMxMGxx_11.800` and that is
all it is (`../../CLAUDE.md`, "Cloud agents cannot reach the hardware"). §6 is
the runtime step, left for a human with the machine.

**`registers.yaml` is untouched by this work and could not have been moved by
it.** A static decode of a second 8051 image's address arithmetic is not
evidence about an EC register's behaviour in either direction, so no `status:`
changes here — including `BAT_CYCLE_COUNT`'s `confirmed-working`, which rests
on a live read, and the `unknown-not-absent` set, which `pd-xdata-overlap.md`
§7 already left standing.

## 1. Reproducing it

`ec/tools/pd_index_geometry.py` is the tool. It takes the image map, the
`ITE8850-PD` marker check and `offset_for_runtime`/`runtime_addr` from
`trace_xdata_refs.py`, and the opcode tables, `converges_from()` and
`paged_target()` from `disasm8051.py`; nothing about the dump's layout or the
8051 encoding is re-derived in it.

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
  ok  0x10BC body is `a42582f582e5f03583f58322` (got `a42582f582e5f03583f58322`)
  ok  0x90CB body is `1210bceb25e02583f58322` (got `1210bceb25e02583f58322`)
  ok  0x10BC adds A×B to DPTR (got A×B)
  ok  0x90CB adds A×B + 0x200×R3 to DPTR (got A×B + 0x200×R3)
  ok  0x998B adds A×B + 0x200×R7 to DPTR (got A×B + 0x200×R7)
  ok  0x9180 adds A×0x1F to DPTR (got A×0x1F)
  ok  PD runtime 0x7421 is file 0x27421 and holds `mov dptr,#0x04a6` (got 0x27421, `9004a6`)
  ok  PD runtime 0x9DEC is file 0x29DEC and holds `mov dptr,#0x04a6` (got 0x29DEC, `9004a6`)
  ok  PD runtime 0xB5D3 is file 0x2B5D3 and holds `mov dptr,#0x04a6` (got 0x2B5D3, `9004a6`)
  ok  PD runtime 0xE9F5 is file 0x2E9F5 and holds `mov dptr,#0x04a6` (got 0x2E9F5, `9004a6`)
  ok  --bases finds 4 site(s) for 0x04A6 (got 4)
  ok  --bases finds 5 site(s) for 0x04A3 (got 5)
  ok  ../annotations/pd-index-helpers.csv has one row per helper (11; got 11)
  ...
  ok  ../annotations/pd-index-callers.csv has 5 row(s) for the four 0x04A6 sites (got 5 committed)

self-test passed: the helper bodies and terms match pd-xdata-overlap.md 3, the four 0x04A6 sites sit where trace_xdata_refs.py puts them, and both CSVs regenerate unchanged (PD image at file 0x20000)
```

(The elided rows are one pair per helper, checking the term string and the
`unmodelled` flag against `pd-index-helpers.csv`; the full run prints 34.)

That self-test is the oracle for everything below. The helper bodies are
pinned against the `r2 -a 8051` listings `pd-xdata-overlap.md` §3 already
transcribed, the site offsets against what `trace_xdata_refs.py` reports, and
the per-base site counts against §1 and §5.2 of the same file — so this tool
cannot silently disagree with a number already committed here.

The two CSVs regenerate with:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --helpers-csv \
          > ec/annotations/pd-index-helpers.csv
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --callers-csv \
          > ec/annotations/pd-index-callers.csv
```

Every `$ r2 …` block below was produced by running radare2 5.5.0, which
`.github/actions/project-setup/action.yml` installs (`ec-0x07d0-sites.md` §1's
"not installed" claim was already corrected in `pd-xdata-overlap.md` §1), on a
flat PD image:

```console
$ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1
1+0 records in
1+0 records out
65536 bytes (66 kB, 64 KiB) copied, 8.3285e-05 s, 787 MB/s
```

r2's trailing `; [0x2000…]` memory-hint column is stripped for width;
nothing else is edited.

## 2. The helper table

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --helpers
```

| entry | adds to DPTR | body |
|---|---|---|
| `0x10BC` | `A × B` | Keil's index helper: `mul ab` then a 16-bit add into DPL/DPH |
| `0x90CB` | `A × B + 0x200 × R3` | `lcall 0x10BC`, then `DPH += 2 × R3` |
| `0x998B` | `A × B + 0x200 × R7` | the same with `R7` |
| `0x998F` | `0x200 × A` | the `DPH += 2 × A` tail on its own, entered directly |
| `0x9180` | `A × 0x1F` | `mov b,#0x1f ; ljmp 0x10bc` |
| `0x9A99` | `A × 0x1F` | byte-identical to `0x9180`; a second copy, not an alias |
| `0x9A98` | `R6 × 0x1F` | `mov a,r6`, falling into `0x9A99` |
| `0x9A3F` | `A × 0x60` | `mov b,#0x60 ; ljmp 0x10bc` |
| `0x9A1B` | `R3 × 0x60` | `mov a,r3`, then the same |
| `0x9987` | `R7 × 0x60 + 0x200 × R7` | `mov a,r7 ; mov b,#0x60`, falling into `0x998B` |
| `0x9A71` | **unmodelled** | not an address helper — see §2.2 |

`A` and `B` unqualified mean "whatever the caller left there"; §3 resolves them
per site. `pd-index-helpers.csv` is the machine-readable form, with each row's
byte length and tail-call target.

### 2.1 The three entry points that share one tail

`0x9987`, `0x998B` and `0x998F` are not three routines. They are three entry
points into one 15-byte run, each skipping more of the prologue — the Keil
idiom of letting a caller that already has `A` and `B` loaded jump past the
loads. The same holds for `0x9A98` falling into `0x9A99`.

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9987; pd 8' /tmp/pd.bin
            0x00009987      ef             mov a, r7
            0x00009988      75f060         mov b, #0x60
            0x0000998b      1210bc         lcall 0x10bc
            0x0000998e      ef             mov a, r7
            0x0000998f      25e0           add a, acc
            0x00009991      2583           add a, dph
            0x00009993      f583           mov dph, a
            0x00009995      22             ret
```

That matters for reading `--bases`: a site calling `0x998B` and a site calling
`0x9987` differ only in who loaded `A`, which is why the tool resolves `A` from
the *site's* frame rather than assuming it.

`add a,acc` doubling `A` and adding it to `DPH` is `DPTR += 2 × A × 0x100`,
i.e. `+ 0x200 × A`. `0x998F` is that tail reached on its own:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x998f; pd 4' /tmp/pd.bin
            0x0000998f      25e0           add a, acc
            0x00009991      2583           add a, dph
            0x00009993      f583           mov dph, a
            0x00009995      22             ret
```

### 2.2 `0x9A71` is not an index helper

It was listed with the others in `pd-xdata-overlap.md` §3.2 because it appears
in the same call sequence. It is not the same kind of routine:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9a71; pd 3' /tmp/pd.bin
        ╎   0x00009a71      f0             movx @dptr, a
        ╎   0x00009a72      900003         mov dptr, #0x0003
        └─< 0x00009a75      021253         ljmp 0x1253

$ r2 -a 8051 -e scr.color=0 -q -c 's 0x1253; pd 7' /tmp/pd.bin
            0x00001253      e50e           mov a, 0x0e
            0x00001255      2582           add a, dpl
            0x00001257      f582           mov dpl, a
            0x00001259      e50d           mov a, 0x0d
            0x0000125b      3583           addc a, dph
            0x0000125d      f583           mov dph, a
            0x0000125f      22             ret
```

It *stores* `A` through the pointer it was handed, then loads an unrelated
DPTR (`0x0003`) and adds the 16-bit value in direct locations `0x0D`/`0x0E` to
it. So `0x9DFE lcall 0x9a71` in `pd-xdata-overlap.md` §3.2 is the second half
of that site's 16-bit store, completed inside the callee — and the DPTR it
leaves behind belongs to a different access. The tool reports it `unmodelled`
with its listing rather than inventing a term for it, and nothing in §3 rests
on it.

### 2.3 Beyond the eleven

The eleven are not the whole family. The 151 base sites in §3 hand DPTR to 78
distinct entries, of which 9 are from the table above; 38 of the other 69
decode under the same two byte templates and the rest do not. Enumerating them
is not attempted here — it is the next question this opens, not a gap in what
is claimed.

## 3. The base/stride/field layout

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --bases
151 PD-image MOV DPTR site(s) with a base in 0x0400-0x04A8, over 37 base(s)
```

The span is the low run `pd-xdata-overlap.md` §5.2 found. 37 of its addresses
are used as an immediate DPTR base somewhere in the PD image.

### 3.1 One stride

Across all 151 sites the term decode produces exactly two stride constants:
`0x60`, used 100 times, and `0x1F`, used 3 times. Every base in the run whose
sites resolve a stride at all resolves `0x60`; where `0x1F` appears it is a
second, inner term *alongside* `0x60` at the same site, never instead of it.
The `0x5E` and `0x77` strides `ec-0x07d0-sites.md` §4 saw against other bases
are not produced by the term decode for any site in this run — which is a
statement about what this method resolves, not about what the 35 unresolved
sites do.

### 3.2 The record stride is `0x260`, not `0x60`

75 of the 151 sites apply both a `×0x60` term and a `0x200×` term. In 37 of
them both terms name an identified register, and in **all 37 it is the same
register**; the remaining 38 have one side unresolved and are counted neither
way. Where the register is shared the two terms collapse:

    Rn × 0x60 + Rn × 0x200  =  Rn × 0x260

So the object `Rn` indexes is `0x260` (608) bytes wide, and the `0x60` figure
`ec-0x07d0-sites.md` §4 and `pd-xdata-overlap.md` §3 both quote is one term of
two rather than the record size. This is arithmetic on the decoded terms, not a
new inference — but it is arithmetic on *those* terms, so it is exactly as
strong as the framing evidence behind them and no stronger.

The `0x1F` term, where it appears, always names a *different* register from the
`0x260` index — a second, inner index. `0x260` is not a whole multiple of
`0x1F`, so the two do not tile; nothing here says what the inner index
addresses.

### 3.3 `0x04A1`-`0x04A6` are field offsets into one layout

`pd-xdata-overlap.md` §5.2 observed that `0x04A1` through `0x04A6` are
contiguous and all have the index-helper shape. The term decode makes that
concrete: every one of them that resolves a stride resolves the same `×0x60`,
and five of the six have sites carrying the `0x200×` page term as well.

| base | sites | strides seen | sites with the `0x200×` term |
|---|---|---|---|
| `0x04A1` | 3 | `0x60` | 3 |
| `0x04A2` | 5 | `0x60` | 4 |
| `0x04A3` | 5 | `0x60` | 4 |
| `0x04A4` | 2 | — | 0 |
| `0x04A5` | 3 | `0x1F` `0x60` | 2 |
| `0x04A6` | 4 | `0x1F` `0x60` | 4 |
| `0x04A8` | 1 | `0x60` | 1 |

`0x04A4`'s two sites both hand DPTR to a routine the term model does not cover
(`0x99E2` begins `mov r6,a`), so its dash is "not resolved by this method", not
"no stride".

The four `0x04A6` sites in full, with the chain of helpers each one runs:

```console
0x04A6: 4 site(s)
    file 0x27421  runtime 0x7421  frame 24/24  A=R3 B=0x60  -> 0x90CB
      DPTR = 0x04A6 + R3×0x60 + 0x200×R3 [chain ends at `push 0x83` at 0x7427]
    file 0x29DEC  runtime 0x9DEC  frame 24/24  A=R6 B=0x60  -> 0x10BC 0x998F 0x9A99
      DPTR = 0x04A6 + R6×0x60 + 0x200×R6 + R5×0x1F [chain ends at movx: DPTR dereferenced here]
    file 0x2B5D3  runtime 0xB5D3  frame 22/24  A=A B=0x60  -> 0x998B
      DPTR = 0x04A6 + A×0x60 + 0x200×R7 [chain ends at `push 0x83` at 0xB5D9]
    file 0x2E9F5  runtime 0xE9F5  frame 24/24  A=R7 B=0x60  -> 0x998B 0x9A98
      DPTR = 0x04A6 + R7×0x60 + 0x200×R7 + R6×0x1F [chain ends at movx: DPTR dereferenced here]
```

Read against `pd-xdata-overlap.md` §3: `0x7421` and `0xB5D3` stop where that
section's save-and-restore detour starts (`push dph ; push dpl`, an unrelated
read, then `pop` and one more helper call). DPTR surviving a stack round trip
is control flow, and this is not a control-flow recovery tool, so the chain
reports where it stopped instead of guessing across it. §3's hand decode
supplies the missing `A×0x1F` for `0x7421`; the tool does not.

`0x9DEC` and `0xE9F5` run to the `movx` with no detour, and their three terms
are the complete address arithmetic for those two accesses.

## 4. The callers

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 \
          --callers 0x7421 0x9DEC 0xB5D3 0xE9F5
PD runtime 0x7421
  byte-scan entry 0x7420: reaches the site with no intervening `ret`; preceded by mov  0xf0,#0x60; 0 jump target(s) in between
    file 0x2C9DD  runtime 0xC9DD  call      lcall 0x7420     frame 1/24  unresolved
  containing entry 0x7392: reaches the site with no intervening `ret`; preceded by ret; 1 jump target(s) in between
    file 0x27CD1  runtime 0x7CD1  call      lcall 0x7392     frame 24/24  unresolved

PD runtime 0x9DEC
  byte-scan entry 0x9D51: reaches the site with no intervening `ret`; preceded by ret; 1 jump target(s) in between
    file 0x2B452  runtime 0xB452  call      lcall 0x9d51     frame 24/24  unresolved

PD runtime 0xB5D3
  byte-scan entry 0xB59B: reaches the site with no intervening `ret`; preceded by ret; 0 jump target(s) in between
    file 0x2B838  runtime 0xB838  call      lcall 0xb59b     frame 24/24  unresolved

PD runtime 0xE9F5
  byte-scan entry 0xE9E3: reaches the site with no intervening `ret`; preceded by ret; 0 jump target(s) in between
    file 0x266E4  runtime 0x66E4  call      lcall 0xe9e3     frame 24/24  R1=#0x00, R2=#0x08, R3=#0x01
```

Each site gets two entry picks: the nearest preceding call target by byte scan
(the upper bound, which can be a phantom) and the nearest that also passes two
structural tests — a linear walk from it reaches the site without returning,
and some anchor decodes into it landing on an unconditional flow break. Where
the two agree only one row is printed. That is the same
byte-scan-bound-beside-anchored-count pairing `bank-call-audit.md` §1 reports,
for the same reason: neither framing settles on its own.

### 4.1 `0x7421`'s byte-scan entry is a phantom, and the scan says so

`lcall 0x7420` at `0xC9DD` has one converging anchor in 24. It is not an
instruction:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xc9db; pd 4' /tmp/pd.bin
            0x0000c9db      900012         mov dptr, #0x0012
            0x0000c9de      7420           mov a, #0x20
            0x0000c9e0      120c58         lcall 0x0c58
            0x0000c9e3      900013         mov dptr, #0x0013
```

`0xC9DD` is the `0x12` operand byte of `mov dptr,#0x0012`, followed by `74 20`
— the `12 74 20` that reads as `lcall 0x7420` spans an operand and the next
instruction. This is precisely the over-count `bank-call-audit.md` §1 measured,
caught here by the framing column rather than by anyone noticing.

The containing pick is `0x7392`, preceded by a `ret`:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x7380; pd 10' /tmp/pd.bin
            0x00007380      ff             mov r7, a
            0x00007381      7b10           mov r3, #0x10
        ┌─< 0x00007383      8007           sjmp 0x738c
        │   0x00007385      90080c         mov dptr, #0x080c
        │   0x00007388      e0             movx a, @dptr
        │   0x00007389      ff             mov r7, a
        │   0x0000738a      7b10           mov r3, #0x10
        └─> 0x0000738c      7d01           mov r5, #0x01
            0x0000738e      12c901         lcall 0xc901
            0x00007391      22             ret
```

and named by one anchored caller:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x7cca; pd 6' /tmp/pd.bin
        ┌─< 0x00007cca      8008           sjmp 0x7cd4
        │   0x00007ccc      9007c9         mov dptr, #0x07c9
        │   0x00007ccf      e0             movx a, @dptr
        │   0x00007cd0      ff             mov r7, a
        │   0x00007cd1      127392         lcall 0x7392
        └─> 0x00007cd4      129166         lcall 0x9166
```

`R7` there comes from XDATA `0x07C9`, not from a literal — so this caller
bounds nothing about the index.

### 4.2 The one caller that does load literals still bounds nothing

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x66da; pd 8' /tmp/pd.bin
            0x000066da      07             inc @r1
            0x000066db      d2e0           setb acc.0
            0x000066dd      ff             mov r7, a
            0x000066de      7b01           mov r3, #0x01
            0x000066e0      7a08           mov r2, #0x08
            0x000066e2      7900           mov r1, #0x00
            0x000066e4      12e9e3         lcall 0xe9e3
```

`R1`, `R2` and `R3` get literals. The site at `0xE9F5` indexes on `R7` and
`R6`, and `R7` here is built by `setb acc.0` on a value from somewhere else.
None of the three literals is an index for this access.

**Net for §4: five caller rows for four sites, four of them a single anchored
`lcall` each, and not one index register bounded by a literal.** That is the
result, not a failure of the scan — and it is why no record count appears
anywhere in this file.

## 5. What this does not establish

- **No record count.** Bounding one needs the index registers' ranges, and §4
  found no literal load for any of them. The honest form is: the observed
  literal index loads at these four sites are none, and nothing here bounds the
  rest. `0x260` is the stride, not a count and not a total size.
- **No name for the record contents.** A `0x260`-byte record with a `0x1F`
  sub-stride in a USB-PD controller could be a port context, a message log, a
  negotiation-state block or something else. `ec-0x07d0-sites.md` §4 and
  `pd-xdata-overlap.md` §4 both stopped at this line and this file stops here
  too.
- **The listed callers are not the complete caller set, and none is known to
  execute.** A call reached through a table, or a computed `jmp @a+dptr`,
  carries no target bytes and is invisible to this scan. "One caller found"
  means "one found by this method", never "one exists" — the blind spot that
  forced the `0x07B9` retraction (`../../docs/findings.md` §4c). The scan errs
  in both directions at once: it over-counts on phantoms (§4.1) and
  under-counts on indirection, and neither error cancels the other.
- **The containing-entry choice is a heuristic**, stated as one in the tool's
  own preamble. Its known failure direction: a genuine routine entry sitting
  immediately after a data table has no converging anchor and would be rejected
  by the same test that caught `0x7420`. That would be a miss, not a
  refutation, which is why the byte-scan pick is printed beside it rather than
  replaced by it.
- **`0x04A4`'s dash, and the 35 sites with no resolved term, mean "not
  resolved by this method"**, never "no arithmetic there". Most of them hand
  DPTR to one of the 69 unnamed entries in §2.3.
- **Nothing here bears on whether the EC and PD images share XDATA.**
  `pd-xdata-overlap.md`'s headline verdict and its hedge stand exactly as
  written; this file decodes one image's internal address arithmetic and says
  nothing about the other's map.
- **No `registers.yaml` status moved, and none could have.** See the preamble.

## 6. What would settle it, and what follows

The record count and the record contents both need something this pipeline
cannot do.

- **Runtime, needs the physical machine — not done here.** Trace the PD
  controller's XDATA while a USB-C PD source is plugged, unplugged and
  renegotiated, and read what the index registers actually hold at these four
  sites. That is the same human-at-the-machine step `pd-xdata-overlap.md` §7
  already asks for, and it is out of reach from a GitHub-hosted runner
  (`../../CLAUDE.md`).
- **Static, and reachable from here:** enumerate the 69 unnamed helper entries
  of §2.3 and check whether the unresolved sites in §3 collapse to the same
  `0x260`/`0x1F` geometry. That is a bounded piece of work on committed inputs
  and would move the 35 no-term sites one way or the other.
- **Also static:** a recursive call graph of the PD image would replace §4's
  heuristic entry choice with a real one and could bound the index ranges by
  following the callers upward. That is `#26`'s territory and the reason this
  file produces geometry rather than attempting it.
