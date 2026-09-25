# `0x07D0` — the 254 reference sites, enumerated

`0x07D0` is `ADDR_BATTERY_CHARGE_LIMIT_DOWN` in the Windows service's
`ECSpec.cs`, and the address with the most direct `MOV DPTR` references in
`ec/firmware/GMxMGxx_11.800` — 254 of them. That count is what
`registers.yaml` flags `DO-NOT-WRITE-BLIND` over, and mapping it was the
"next concrete step" both `charge-profile-flow.md` §3 and `docs/findings.md`
§5 pointed at. This file is that map: every one of the 254, where it is, what
the bytes around it do, and which of them are plausibly not instructions at
all.

**Read the headline before the tables.** All 254 sites are in the `ITE8850-PD`
image at file `0x20000` — a second 8051 program with its own XDATA map, per
`lightbar-bat-flow.md` §2. This file therefore characterises *the PD
firmware's variable at its XDATA `0x07D0`*, which is not the EC register
Windows writes; they share a number and nothing else. Nothing below is
evidence about what the EC does with its own `0x07D0`, and nothing below
makes writing that register any safer. See §6.

Within the PD image the picture is consistent and boring: a byte that is
read almost everywhere, written in fifteen places, incremented in place in
two, and used as a multiplier against structure strides (`0x5E`, `0x60`,
`0x77`) to index arrays — the shape of an index or state variable, not of a
threshold. "The shape of" is the claim; naming what it indexes would be a
guess and is not made.

## 1. Reproducing the map

```console
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x07D0
This dump holds two 8051 programs; ec= counts sites in the EC firmware
(common area + CODE banks), pd= sites in the separate ITE8850-PD image,
whose XDATA map is unrelated. A pd-only count is not EC-side evidence.
A zero means 'not found by this scan', never 'absent' -- see the
indirect-addressing blind spot in docs/findings.md.

0x07D0  refs=254   ec=0     pd=254   referenced in the PD image ONLY, not by the EC   0x07D0

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D0 --counts-only
0x07D0: 254 direct MOV DPTR site(s)  pd-image=254

$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D0 --csv \
          --terminator-column \
          > ec/annotations/ec-0x07d0-sites.csv
$ tail -n +2 ec/annotations/ec-0x07d0-sites.csv | wc -l
254
```

The trailing `terminator` column says which of the five guards
`walk_why()` can stop on ended this row's window, so a window the
instruction budget cut is not in the same shape as one that stopped on a
real terminator. This file's rows that the budget truncates are listed in
`walk-budget-census.csv` and counted by `../../ec/tools/walk_budget_census.py`;
the write-up is `../../docs/findings/walk-window-terminators.md`.

That is the reconciliation check this file rests on: the enumerated rows are
the same 254 the counter in `registers.yaml` and `docs/findings.md` cite, and
their per-region counts sum to it — so the site table cannot silently
disagree with the number everything else quotes. `ec-0x07d0-sites.csv` is
committed next to this file; every table below is derived from it, and each
one names the command that re-derives it.

Drop `--csv` for the per-site decode, add `--r2-commands` for paste-able
`r2 -a 8051` seek lines (radare2 is not installed on the CI runner, so
nothing here was produced by it — the commands are there so a human with r2
can spot-check any site against an independent disassembler). **Correction:
radare2 *is* installed on the runner** — `.github/actions/project-setup/action.yml`
installs it, and `pd-xdata-overlap.md` was produced by running it there. The
parenthesis above is left as written; what is still true of *this* file is
that nothing in it was produced by r2. Individual
windows below were produced with `ec/tools/disasm8051.py`, whose opcode
tables are pinned by `--self-test` against the two windows
`charge-profile-flow.md` transcribed from r2 by hand:

```console
$ python3 ec/tools/disasm8051.py --self-test
...
self-test passed: both charge-profile-flow.md windows decode identically
```

## 2. Where the 254 are

All in the PD image, spread across it rather than concentrated:

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d0-sites.csv')))
print(collections.Counter(r['region'] for r in rows))
h = collections.Counter(int(r['runtime'], 16) >> 12 for r in rows)
print('  '.join(f'0x{k:X}xxx:{v}' for k, v in sorted(h.items())))"
Counter({'pd-image': 254})
0x3xxx:49  0x4xxx:34  0x5xxx:25  0x6xxx:29  0x7xxx:40  0x8xxx:39  0x9xxx:12  0xAxxx:6  0xCxxx:9  0xDxxx:9  0xExxx:2
```

254 distinct file offsets, from PD runtime `0x3478` to `0xE8F9`, spread
over eleven of the image's 4 KiB pages. **So the issue's either/or — "one
function called 254 times, or 254 distinct call-sites?" — resolves to the
second**, with a qualifier that matters more than the count: the sites are
distinct, but they are not 254 independent pieces of logic. 79 of them hand
the address straight to one of 25 shared accessor routines (§3), and 68 sit
immediately after one repeated call idiom (§5). What the histogram shows is a
variable the whole PD program reaches for, not 254 separate decisions about a
threshold.

For context on the neighbourhood, the same block `lightbar-bat-flow.md` §3.1
described — `0x07CF`-`0x07E9` referenced with no gaps — puts `0x07D0` at the
top by a wide margin (PD-image counts, one `--counts-only` run per
address): `0x07CF`:55, **`0x07D0`:254**, `0x07D1`:76, `0x07D2`:47,
`0x07D4`:68, `0x07D6`:142, `0x07D7`:71.

## 3. What the sites do

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d0-sites.csv')))
k = collections.Counter()
for r in rows:
    a = r['access']
    k['handed to a helper' if a.startswith('DPTR handed') else
      'read-modify-write' if 'read' in a and 'write' in a else
      'read' if 'read' in a else 'write' if 'write' in a else
      'no movx in window'] += 1
print(sorted(k.items(), key=lambda x: -x[1]))"
[('read', 157), ('handed to a helper', 79), ('write', 8), ('no movx in window', 8), ('read-modify-write', 2)]
```

| at the site | sites |
|---|---|
| reads it (`movx a,@dptr`) | 157 |
| hands DPTR to a subroutine — direction not resolvable at the site | 79 |
| writes it (`movx @dptr,a`) | 8 |
| no `movx` in the decoded window | 8 |
| read-modify-write | 2 |

The 79 handoffs go to 25 distinct entry points. Decoding each one's first
instruction resolves the direction one level deeper — 72 of the 79 call a
routine that begins `movx a,@dptr`, i.e. they are reads too; 7 call one that
begins by storing (`0x37AE`, `0xB159`):

| helper | sites | first instructions (`disasm8051.py --at <0x20000+helper>`) |
|---|---|---|
| `0x357E` | 12 | `movx a,@dptr ; mov r3,a ; mov 0xf0,#0x60` |
| `0x34D9` | 10 | `movx a,@dptr ; mov 0xf0,#0x5e ; mul ab` |
| `0x347B` | 8 | `movx a,@dptr ; mov r3,a ; mov 0xf0,#0x60` |
| `0x34A5` | 6 | `movx a,@dptr ; mov dptr,#0x0420 ; mov r7,a` |
| `0x37AE` | 6 | `mov a,r7 ; movx @dptr,a ; mov r6,0x04` |
| `0x34FB` | 5 | `movx a,@dptr ; mov r7,a ; mov dptr,#0x0408` |
| `0x39AC` | 4 | `movx a,@dptr ; mov r7,a ; mov r3,#0x01` |
| 18 more, 1-3 sites each | 28 | all but `0xB159` begin `movx a,@dptr` |

Several of these entry points are mid-routine — `0x34D9` is the tail of a
routine whose head at `0x34D6` loads `0x07D6` instead — which is ordinary
Keil tail-sharing and is why the entry addresses are unaligned-looking.

Net: **229 of the 254 sites read the byte, 15 write it, 2 read-modify-write
it, and 8 are unresolved by this method.** The eight "no `movx`" sites are
seven instances of `lcall 0xF739 ; mov dptr,#0x07d0 ; ret` — a routine
returning with DPTR left pointing at the byte, so the access is in its
callers — plus one site where a `jnz` intervenes.

## 4. What the value is used as

Read sites overwhelmingly feed the byte into address arithmetic. The
canonical form, and the single most common shape in the whole set:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x23478 --runtime 0x3478 -n 6
0x3478  9007d0   mov  dptr,#0x07d0
0x347b  e0       movx a,@dptr
0x347c  fb       mov  r3,a
0x347d  75f060   mov  0xf0,#0x60
0x3480  900408   mov  dptr,#0x0408
0x3483  1210bc   lcall 0x10bc
```

`0xF0` is `B` and `0x82`/`0x83` are `DPL`/`DPH`, so that is: read the byte,
load `B` with `0x60`, point DPTR at `0x0408`, and call `0x10BC` — the Keil
index helper, `DPTR += A * B`:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x210BC --runtime 0x10BC -n 7
0x10bc  a4       mul  ab
0x10bd  2582     add  a,0x82
0x10bf  f582     mov  0x82,a
0x10c1  e5f0     mov  a,0xf0
0x10c3  3583     addc a,0x83
0x10c5  f583     mov  0x83,a
0x10c7  22       ret
```

So the byte at `0x07D0` is the *index* and `0x0408` the base of an array of
`0x60`-byte records. The same multiply appears inline in helper `0x34D9`
(stride `0x5E`, base `0x08FC`), at site `0xC2FA` (stride `0x5E`), at site
`0xDA9B` (stride `0x77`), and in `0x578E` (stride `0x77`) — several arrays,
one index.

`pd-index-geometry.md` §7 decodes all four and names the bases the other three
index: `0x08F8` for `0xC2FA`, `0x0870` for `0xDA9B` (through helper `0x5950`)
and `0x089B` for `0x578E`, which lands its pointer in `R2:R1` rather than in
DPTR. It also answers what these arrays do *not* have: none of them carries the
`0x200 × Rn` page term that makes the `0x0400`-`0x04A8` records `0x260` bytes
wide, so the strides quoted above stand as the effective ones — as far as a
static term decode resolves.

**Correction (#74), retaining the preceding claim as history.** `0x578E`
returns the address halves in **A:R1**, not R2:R1; `mov r2,a` is a separate
instruction at `0x5901` in a subsequent helper. The `0x34DD` and `0xC302`
multiplies discard B, so their addresses are `0x08FC + low8(A × 0x5E)`
and `0x08F8 + low8(R7 × 0x5E)`, respectively. `0xDAA3 → 0x5950` gives
`0x0870 + low8(R7 × 0x77)`. Here `low8(x) = x & 0xFF`, the low-base
addition still carries into the high byte, and addresses wrap at 16 bits.
Only the `0x578E` form retains the full product: `0x089B + A × 0x77`.
Thus the multiplication constants above are not globally linear record
widths. No page term was resolved by this bounded decode; that is not proof
that callers or unsupported idioms add none. See `pd-index-geometry.md` §8
for independent byte checks and the separate construction/access census.

Two sites advance it in place, which is what an index does and what a
threshold does not:

```console
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2A678 --runtime 0xA678 -n 5
0xa678  9007d0   mov  dptr,#0x07d0
0xa67b  e0       movx a,@dptr
0xa67c  04       inc  a
0xa67d  f0       movx @dptr,a
0xa67e  02a571   ljmp 0xa571
```

(`0xDC20` is the same four instructions followed by `sjmp`.) Of the writes
that are not this increment, most store a value already in `R7`; `0xDBEE`
stores a literal zero (`clr a ; mov dptr,#0x07d0 ; movx @dptr,a`) — a reset
to the first element, on the same reading.

**What that supports, and where it stops.** It supports "the value is used as
an array index / iteration state in the PD firmware". It does not identify
*what* is indexed. A `0x60`-byte record in a USB-PD stack could be a port
context, a message buffer, a negotiation-state block, or something else
entirely; nothing here was correlated with a PD packet capture or with the
image's strings, and the containing routines were not traced to an entry
point. Recorded as "index into `0x0408`-based records, contents
unidentified".

`pd-index-geometry.md` decodes the helper family around `0x10BC` and the whole
`0x0400`-`0x04A8` base run, `0x0408` included. It finds `0x60` used as a stride
by every base in that run that resolves one, but often as only one of two index
terms: two of `0x0408`'s seven sites also add `0x200 × Rn`, and across the run
that second register is the same one as the `×0x60` index wherever both are
identified, making the effective stride `0x260`. It does not identify the
contents either, and states no record count — the recording above stands.

## 5. Are all 254 real instructions?

`scan_refs.py` counts the byte pattern `90 07 D0` with no instruction
alignment, so in principle some hits are operand bytes inside other
instructions or bytes inside a data table. Testing that needs an anchor, and
any anchor is itself a guess — `disasm8051.py --converge` therefore reports
*evidence*, not a verdict: it decodes linearly from each of the 24 bytes
preceding a site and counts how many walks land exactly on it versus step
over it.

```console
$ python3 -c "
import csv, collections
rows = list(csv.DictReader(open('ec/annotations/ec-0x07d0-sites.csv')))
print(collections.Counter('syncs from every anchor' if r['frame_over'] == '0' else
      'syncs from none' if r['frame_onto'] == '0' else 'mixed' for r in rows))"
Counter({'syncs from every anchor': 154, 'mixed': 55, 'syncs from none': 45})
```

The 45 that no preceding anchor syncs onto are the ones worth explaining, and
all 45 are accounted for without any of them being misframed:

- **42 sit immediately after `lcall 0x104D` followed by four bytes of inline
  data.** 68 of the full 254 sit there; for the other 26 some anchor inside
  the inline bytes happens to land on the site anyway, which is its own
  reminder of how weak the sweep is. `0x104D` pops its own return address
  into DPTR, fetches four bytes from the code stream through `0x1064`
  (`clr a ; movc a,@a+dptr ; inc dptr`), and resumes past them with
  `jmp @a+dptr`:

  ```console
  $ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x2104D --runtime 0x104D -n 10
  0x104d  a882     mov  r0,0x82
  0x104f  8583f0   mov  0xf0,0x83
  0x1052  d083     pop  0x83
  0x1054  d082     pop  0x82
  0x1056  121064   lcall 0x1064
  0x1059  121064   lcall 0x1064
  0x105c  121064   lcall 0x1064
  0x105f  121064   lcall 0x1064
  0x1062  e4       clr  a
  0x1063  73       jmp  @a+dptr
  ```

  A linear decoder cannot know those four bytes are arguments, so it walks
  through them and comes out misaligned — `disasm8051.py` renders them as
  `nop`s, which is exactly the failure mode its docstring warns about:

  ```console
  $ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x23AA8 --runtime 0x3AA8 -n 4
  0x3aa8  12104d   lcall 0x104d
  0x3aab  00       nop
  0x3aac  00       nop
  0x3aad  00       nop
  ```

- **3 sit immediately after a table of code addresses that includes their
  own.** At file `0x23A81` the preceding bytes are `3e 6f 01 0c | 3f 38 01 0d
  | 3a 81 01 ff | 00 00`: four-byte entries whose first halves are code
  addresses, the last of them (`3a 81`) the site's own runtime address. Same
  shape before file `0x24869` (`48 69 02 ff | 00 00`) and file `0x283E2`
  (`83 e2 04 02 | ... | 85 02 04 ff | 00 00`). What dispatches through these
  tables was not traced.

So this method found **no site among the 254 that looks like a false
positive**: every one is followed by a coherent `movx` access, a handoff to a
routine that performs one, or — for the eight in §3 — a `ret` or branch that
leaves DPTR loaded, and every site the sweep could not sync onto has an
identified non-code reason. That is not the same as proving all 254 are
executed, or executable on this SKU — see §6.

One related caution, since it is a boundary on reference counting that this
repo had not written down: `MOV DPTR,#imm16` builds **CODE** pointers as well
as XDATA ones, and in this image CODE `0x07D0` is inside the float-formatting
string table (`"NaN"` at `0x07CD`, `"+INF"` at `0x07D1`, `"-INF"` at
`0x07D6`, which `0x07C1`/`0x07C8` load pointers to). None of the 254 turned
out to be that — every site whose direction resolves is a `movx`, not a
`movc` — but a `90 xx xx` count cannot tell the two apart on its own, and a
future scan of some other address may land in a string table and mean nothing.

## 6. What this does not establish

- **Nothing about the EC's `0x07D0`.** The register `ECSpec.cs` names, that
  `uniwill-laptop` has no concept of and Windows writes as the DOWN half of a
  charge-limit pair, lives in the main EC image's XDATA — which references
  `0x07D0` **zero** times by this method (`lightbar-bat-flow.md` §6). The 254
  sites are a different program's variable. `registers.yaml` keeps
  `DO-NOT-WRITE-BLIND`, and this file does not lift it, propose lifting it, or
  add any tool that writes the byte.
- **Nothing observed on hardware.** No register was read back, no write was
  attempted, nothing was run on the machine. This is static analysis of a
  committed firmware image and that is all it is.
- **Not proof that the EC ignores `0x07D0`.** Zero direct references is the
  same signal `docs/findings.md` §4c retracted for `0x07B9`, with the same
  indirect-addressing blind spot. The honest status is undetermined.
- **No control-flow recovery.** `disasm8051.py` decodes linearly and stops at
  the first branch; "254 distinct sites" counts *static* sites, and says
  nothing about how many execute, how often, or in what order. Whether some
  of those sites sit in the same function is not determined — that needs a
  recursive disassembly the repo has deliberately not attempted
  (`ec/README.md`, "toolchain proven, not attempted").
- **Nothing from the Windows side was re-derived here.** The `ECSpec.cs`
  constants are cited as they stand; no anti-tamper-protected method body was
  involved (`windows/antitamper/README.md`).

## 7. What would actually settle the EC-side question

Unchanged from `docs/findings.md` §5, and still a human-at-the-machine step:
write `0x07B9` and `0x07D0` **together**, the way `BatteryProtection2` does,
then coulomb-count through the claimed cap exactly as in that file's §4b.
This file removes one objection to designing that experiment — "we don't know what else
in the firmware touches `0x07D0`" now has an answer, namely "nothing in the EC
image does, by this method" — and adds none of its own. Decrypting the
`BatteryProtection2` bodies (`windows/antitamper/`) remains the route that
would answer it without touching the hardware at all.
