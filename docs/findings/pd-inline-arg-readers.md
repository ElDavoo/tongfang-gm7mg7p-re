# No sweep found a reader for the `??82` cells `lcall 0x104D` fills in, and the count the issue set out to explain was two mistakes at once (issue #1142)

**Read the headline before anything else.** Everything below is about the
`ITE8850-PD` image at file `0x20000` — a second, self-contained 8051 program
with its own XDATA map. It says **nothing** about the EC's own registers, and
`ec/annotations/registers.yaml` is untouched: this is the PD image's XDATA map,
not the EC's, and no EC register status changes. All of it is static analysis of
the committed `ec/firmware/GMxMGxx_11.800`. No register was read back, no write
was attempted, nothing ran on the machine.

`../../docs/findings/pd-inline-arg-trampoline.md` §5 gave the destinations and
stopped: "What reads those cells was not traced." This is that answer. **The
answer is negative**, it is stated below at the confidence three cell sweeps, the
entry sweep and a second independent census can carry, and per row of the census
it comes with the reason it is empty.

## 1. The measurement, and the two mistakes in the count it replaces

The issue read `trace_xdata_refs.py --counts-only` as a reader count and wrote
"174 writers against one reader". `--counts-only` tallies direct `MOV DPTR,#imm16`
**sites**. It does not resolve direction, and it does not separate programs.
Both omissions matter here, and both point the same way.

**The `0x0A82` site is a writer.** It is the only `MOV DPTR` naming `0x0A82`
anywhere in the dump, and decoded it is:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x0A82
0x0A82: 1 direct MOV DPTR site(s)  pd-image=1

  file 0x2F4AB  pd-image  runtime 0xF4AB  [separate ITE8850-PD 8051 image; dd bs=64k skip=2]
    write x2, walks 3 consecutive bytes (inc dptr)
      0xF4AB  900a82   mov  dptr,#0x0a82
      0xF4AE  ef       mov  a,r7
      0xF4AF  f0       movx @dptr,a
      0xF4B0  a3       inc  dptr
      0xF4B1  ed       mov  a,r5
      0xF4B2  f0       movx @dptr,a
      0xF4B3  a3       inc  dptr
      0xF4B4  ea       mov  a,r2
```

`movx @dptr,a` is a store. The site is already annotated
`pd,F4AB,store_4bytes_to_0a82,,writer` in `ec/annotations/ghidra-functions.csv`,
so `0x0A82` is **174 deposits against a second writer and no identified reader**,
not one reader. The issue's "1" is this site, and it is a writer.

**The `0x0782` sites are another program's.** All eleven are in `bank0` — the
main EC, with its own XDATA allocation, which is the independence
`ec/annotations/pd-xdata-overlap.md` establishes. None of them is a consumer of
the 107 values the PD image writes at that number.
`ec/annotations/pd-xdata-span-sites.csv` already carries the split for this
address (`main_ec=11, pd_image=0`), so the cross-program half of the issue's
table was available and is not in dispute.

So the ratio the issue set out to explain — 174 writers against one reader — is
a direction error plus a cross-program artifact. The corrected statement is
**per program and per direction**, and that is a cleaner result than the one the
issue predicted: the two programs' `??82` cells are unrelated, and within the PD
image the cells have no identified consumer.

## 2. Three cell sweeps, and every zero is "not found by this method"

```console
$ python3 ec/tools/pd_inline_arg_readers.py ec/firmware/GMxMGxx_11.800
    cell  deposits  MOV DPTR  read  write  halves   A  where
  0x0A82       174         1     0      2       0   0  pd-image=1
  0x0782       107        11    11      3       0   0  bank0=11
  0x0882        92         0     0      0       0   0  --
  0x0482         7         0     0      0       0   0  --
  0xFF82         7         0     0      0       0   0  --
  0x0082         3         0     0      0       0   0  --
  0x0382         2         8     2      0       0   0  bank1=8
  0x1282         1         0     0      0       0   0  --
  0x0982         1         2     2      0       0   0  bank1=2

Over every cell named by the committed census: 394 deposits,
22 direct `MOV DPTR` site(s) -- 15 read, 5 write --
0 immediate-half pair(s) and 0 accumulator-built site(s) naming them
anywhere in the PD image.  **0 of all of that is a read inside the PD image.**
```

**Read that table per row. The `where` column is the point**, and it is why
there is no blended total in it: a read in `bank0` or `bank1` is not a read in
the PD image, and a column that summed them would be reporting a fact about
neither program. The 15 reads are all in another program's address space.

The three cell sweeps are `MOV DPTR,#imm16` (the one `--counts-only` uses), an
adjacent `mov DPL,#data8` / `mov DPH,#data8` pair, and `mov A,#data8` followed
by `mov DPL,a` / `mov DPH,a`. Each one's miss conditions are printed by the mode
that exists to state them:

```console
$ python3 ec/tools/pd_inline_arg_readers.py ec/firmware/GMxMGxx_11.800 --blind-spots
  mov-dptr  (column `mov_dptr_reads`)
    finds:  direct `MOV DPTR,#imm16` at the cell, direction from the window that follows
    sees:   3176 candidate site(s) in the PD image
    blind:  a DPTR built any other way; a `movx` past the first branch, a DPTR reload,
            or the 8-instruction budget; a window handed to a subroutine, which
            `classify()` reports as unresolved rather than as a direction
```

with the same `finds` / `sees` / `blind` triple for the other two. A blind spot
stated without a size is not one, which is why `sees` is there: it says how much
of the image each sweep looked at, so a reader can judge the zero against the
search rather than take it on trust. `docs/findings.md` §4c asks for this
wording and `CLAUDE.md`'s calibration rule asks for it twice over, so **no zero
in this file means "there is none".**

## 3. An independent second census agrees, which is what makes the zero a result

`ec/annotations/xdata-registers.csv` is built from the Ghidra decompile rather
than from a byte scan, so it cannot have the same blind spots, and over the same
cells it reads `0x0A82` as zero reads against writes and carries `BIOS_OEM_2`
for `0x0782` under `program=main-ec`. `0x0882` has no row in it at all:

```console
$ python3 - <<'PY'
import csv
rows = {r["addr"].upper(): r for r in
        csv.DictReader(open("ec/annotations/xdata-registers.csv"))}
for addr in ("0X0A82", "0X0782", "0X0882"):
    r = rows.get(addr)
    print(addr, "->", "no row" if r is None else
          f'program={r["program"]} read={r["read"]} write={r["write"]}'
          f' name={r["name"] or "-"}')
PY
0X0A82 -> program=pd read=0 write=1 name=-
0X0782 -> program=main-ec read=12 write=0 name=BIOS_OEM_2
0X0882 -> no row
```

Two methods whose blind spots differ, converging on "no PD-side reader", is the
strongest statement this evidence carries. Neither alone is: one
method reporting zero is a shrug, and this file would have said so had the other
agreed for a reason that was not independence.

## 4. `0x0882`, settled

The 92-deposit cell with no reader is **not** a claim about the page it sits on.
The `0x08xx` page is read constantly — 932 `MOV DPTR,#0x08xx` sites in the PD
image, whose decoded windows carry 456 `movx a,@dptr` reads:

```console
$ python3 - <<'PY'
import sys; sys.path.insert(0, "ec/tools")
from trace_xdata_refs import walk_why
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
sites = [o for o in range(0x20000, 0x30000 - 2) if d[o:o+2] == b"\x90\x08"]
print("pd-image MOV DPTR,#0x08xx sites:", len(sites))
print("  decoded movx a,@dptr riding them:",
      sum(sum(1 for _, raw, _ in walk_why(d, o)[0][1:] if raw[0] == 0xE0)
          for o in sites))
PY
pd-image MOV DPTR,#0x08xx sites: 932
  decoded movx a,@dptr riding them: 456
```

So the page is very much in use, and `0x0882` specifically is read by nothing
any of the three sweeps found, with no row for it in the decompile-derived census
either. That is a statement about one address, and it is the distinction the
issue asked for when it said the case should be "settled either way rather than
left as a count".

## 5. The entry spelling is a fourth population, and 458 is one reading of it

The census in `pd_inline_arg_sites.py` scans for `12 10 4d`, which is `lcall
0x104D` and one spelling of the entry. The helper is reachable three more ways
in this image, and all three are in the same population the 458 comes from:

```console
$ python3 ec/tools/pd_inline_arg_readers.py ec/firmware/GMxMGxx_11.800 --blind-spots
    target  form    sites   of which pd-image
  0x104D  lcall     458                 458
  0x104D  ljmp        2                   2
  0x107E  lcall       2                   2
  0x107E  ljmp        0                   0
  0x1098  lcall       2                   2
  0x1098  ljmp        0                   0
```

`0x107E` is `cjne r3,#1 / mov 0x82,r1 / mov 0x83,r2 / ljmp 0x104D` — the same
helper, with the destination built in **registers** — and `0x1098` adds `R1:R2`
into DPTR before the same `ljmp`. Both are called, and each call carries four
inline bytes after it exactly as the `lcall 0x104D` form does. **So 458 counts
one spelling of the mechanism, not the mechanism.**

**These entries are counted as entries and not as destinations, and that is a
decision rather than an omission.** An entry that takes the destination's high
byte in a register reaches a different cell at every call, and no byte in the
image says which — so a column of its own would hold the same number on every
row, which is a census of the entry spelling wearing a row's clothes.

**No `ghidra-functions.csv` row names `0x107E`, and that is a measured refusal
rather than an oversight.** A row is the documented way to put a routine reached
only by a branch or a table into the Ghidra project, and this one is reached
only by an `lcall`. `build_ec_decompile.py --check` was given the row and
reported `annotation pd 0x107E resolves to no exported function -- either a typo
or the project needs a rebuild`: `0x107E` sits between two routines the project
does have (`0x1064` and `0x10BC`) rather than at an entry it recognises, so
naming it needs
`--mode rebuild-project`, which writes a 7 MB database that two branches both
rebuilding cannot merge. Adding the row also moved the annotated-row census in
`subsystems.md`, a second shared file. **The finding does not depend on the row**
— §5 and the `--blind-spots` transcript carry it — so the row was dropped rather
than the project rewritten for a name.

## 6. `dest` by decode: 48 of the 64 empty rows recovered, 16 with a reason

The `dest` column of `ec/annotations/pd-inline-arg-sites.csv` is derived by
scanning backward for the byte pattern `90 xx xx`, which §5 of the trampoline
write-up says cannot tell a `mov dptr,#imm16` from the same three bytes inside
another instruction. Rows with no such pattern in range write an **empty** cell.
`ec/tools/pd_inline_arg_dest.py` replaces the scan with a decode: every
candidate start offset is walked forward, stepping over an
`disasm8051.INLINE_ARG_CALLS` argument block the way `converges_from()` does,
and a start that lands **exactly** on the call is a walk that reaches it.

```console
$ python3 ec/tools/pd_inline_arg_dest.py ec/firmware/GMxMGxx_11.800
442 of 458 carry a value (435 agreeing, 7 not),
and 16 carry no `mov dptr` on any converging walk and 0 have no walk that
reaches the call at all.  Both are 'not found by this method', never 'there is none'.
```

**The scan was not wrong where it had an answer.** Over the rows that carry a
`dest` and a decoded value, every one decodes to the cell the scan recorded, and
the suite asserts that from the firmware rather than by re-running the tool. So
the decode is a replacement that reproduces the scan's readings before its extra
reach counts for anything. Five rows carry a `dest` and *no* decoded value:
their walks disagree, and the paragraph below on why a disagreement is reported
rather than resolved is the reason that is an answer and not a gap.

**The reach is a parameter and the tool says so.** Straight-line code has no
backward edge to stop at, so "how far back to look" is a choice and not a
derivation, and the recovery figure is a point on a curve rather than a property
of the firmware:

```console
$ python3 ec/tools/pd_inline_arg_dest.py ec/firmware/GMxMGxx_11.800 --reach-sweep
 reach   decoded-unique   ambiguous   no value
    32              389           5         64
    48              414           6         38
    64              435           7         16  <- default
    80              440           9          9
    96              441           9          8
   128              446           9          3
   192              449           9          0
```

The default recovers 48 of the 64 rows the scan missed; more reach buys the rest
at the cost of more rows whose framing is only probably real. **`decoded-unique`
keeps rising with the reach and would keep rising**, because a long enough walk
reaches *some* `mov dptr` whether or not the framing is real — which is why the
16 that stay empty carry a reason token instead of a blank, and why an ambiguous
row is reported rather than resolved.

## 7. The values per cell: a lead, not a meaning

The same instruction, the same helper, different populations per cell:

| cell | deposits | distinct values | commonest |
|---|---|---|---|
| `0x0A82` | 174 | 13 | `1` (93), `0` (59) |
| `0x0782` | 107 | 18 | `0` (51), `1` (16) |
| `0x0882` | 92 | 21 | `0` (38), `1` (16), `800` (10), `5000` (6) |

The large values sit in `0x0882` and the near-binary ones in `0x0A82`. **That is
a fact about the writes and nothing more**, offered because it is the kind of
distribution a consumer would explain and this file has none. It does not say
the two cells are the same kind of thing, and it does not supply a unit.

## 8. What this does not establish

- **Nothing about the constant's meaning.** §4 of the trampoline write-up stops
  at the enumeration and this does not move it. **A consumer is what a unit
  would come from, and §2 is the finding that there is none to read one off** —
  so §7's distribution is offered as a lead for whoever picks this up, and
  naming the constant is left explicitly undone rather than guessed.
- **Nothing about hardware.** No register was read back, no write was attempted,
  nothing ran on the machine. Static analysis of a committed image.
- **Not that no consumer exists.** Not found by three cell sweeps, the entry
  sweep and a second census, each method's miss conditions stated in §2 and the
  entry spelling in §5.
- **Not which of two framings is real.** The decode reads bytes linearly and
  does not follow branches; a row whose walks disagree is reported as ambiguous
  rather than decided. Which of two framings is correct needs control-flow
  recovery, which `ec/README.md` records as deliberately not attempted.
- **Nothing about the EC's `0x07D0`.** The main EC's registers are a different
  program's, and its eleven `0x0782` sites are named in §1 as *not* consumers.
- **The 458 is still one spelling.** §5 names the three others. Folding them into
  the committed census is its own change and is filed as the follow-up this
  opens.

## 9. Reproducing this

```console
$ bash tools/run-tests.sh                                    # picks the new suites up by find
$ python3 ec/tools/pd_inline_arg_readers.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/pd_inline_arg_readers.py ec/firmware/GMxMGxx_11.800 --blind-spots
$ python3 ec/tools/pd_inline_arg_dest.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/pd_inline_arg_dest.py ec/firmware/GMxMGxx_11.800 --reach-sweep
$ python3 ec/tools/pd_inline_arg_sites.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/disasm8051.py --self-test                  # untouched, must stay green
```

The two `--check`s are the load-bearing ones: they say the committed tables are
what the committed image derives. `test_pd_inline_arg_dest.py` and
`test_pd_inline_arg_readers.py` hold the decode's framing rules and the census's
per-program, per-direction split on hand-built fixtures, and assert the figures
above from the firmware rather than from the tool that wrote them.

The one test that makes the negative falsifiable is
`test_a_pd_image_read_is_counted_as_one`: it builds a PD-image site that *does*
read one of these cells and requires the `pd_side_reads` column to report it, so
the zeros in §2 are a measurement rather than a column wired to zero.