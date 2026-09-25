# The reset vector's two DPTR-only bank-0 targets, `0xD89F` and `0xD96C` (issue #559)

`ec/decompiled/common/0070.asm:7-21` is the reset vector: it sets the stack
pointer, writes `0x3F` to XDATA `0x1001`, then `lcall`s `0x110A`, `0x158E`,
`0x0F75` and `0x1594` and tail-jumps to `0x00CF`. The two middle calls are
6-byte trampolines into bank 0, and both carry their real target as a DPTR
immediate rather than as a branch operand:

```
158E     90 d8 9f mov      DPTR, #0xd89f
1591     02 11 00 ljmp     0x1100
1594     90 d9 6c mov      DPTR, #0xd96c
1597     02 11 00 ljmp     0x1100
```

`0x1100` is the Keil BL51 cross-bank switch stub that selects bank 0
(`ec/annotations/ghidra-functions.csv`), and 350 of the 403 common-area
trampolines route through it the same way. So both addresses are code targets
on the boot path. Neither had a listing, an index row, an annotation row, a
`bank-call-targets.csv` row, or any mention in a findings file.

**Both were seeded and read for this issue. `0xD89F` is a single `ret` byte, and
`0xD96C` is a 0x25-byte routine that clears 3,837 bytes of XDATA and
steps over three of them.** The two need different answers, and one
of them corrects the expectation the issue was filed with — the issue reads
*"they are not routines in their own right"* and expects a real routine at each.
One is. The other is a real code entry whose entire body is `ret`, which is
neither of the issue's outcomes (a) and (b) as written; §"Which outcome" below
says which it is and why, and leaves the wrong expectation visible rather than
dropping it.

The load-bearing evidence is the committed image and this repository's own
decoder. A Ghidra 12.1.3 export corroborates both function boundaries and
agrees byte for byte; it is cited as corroboration, not as the source of the
reading. The export is **not committed** — §"The export is deferred" gives the
reason and the row-by-row list for the run that does commit it.

---

## `0xD89F`: one byte, `22`, and nothing else

```
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D89F --runtime 0xD89F -n 8
0xd89f  22       ret
0xd8a0  e4       clr  a
0xd8a1  ff       mov  r7,a
0xd8a2  125597   lcall 0x5597
...
```

`0xD89F` is the fourth `ret` in a run — `0xD888`, `0xD893`, `0xD89E`, `0xD89F` —
that terminates two leaf stubs already exported and named:
`ec/decompiled/bank0/D889.asm` (`zero_dptr_and_load_regs`, ends `0xD893`) and
`ec/decompiled/bank0/D894.asm` (`set_dptr_0200_plus_r7`, ends `0xD89E`). The
substantial routine one byte on, at `0xD8A0`, clears A, `lcall`s
`0x5597`/`0xD722`/`0xD72B`/`0xDE65`/`0xD927`/`0xD946`/`0x193C`/`0xBFDE`, clears
XDATA `0x0983` bit 0, reads XDATA `0x201C` bit 1, and loops via `0x0EA2`.

**The trampoline's operand lands one byte short of that routine, and this is
not settled by the bytes.** `0xD89F` and `0xD8A0` each have exactly one
`mov DPTR,#imm16` site in the whole 256 KiB image, and they are different
sites: `common,158E` carries `0xD89F` and `common,1504` carries `0xD8A0`. So
`0xD8A0` is a genuine entry with its own route in, and the reset vector's
operand names the `ret` before it. Whether the linker meant `0xD8A0` and lost a
byte, or meant the stub, is not determinable here, and is a follow-up rather
than a conclusion.

## `0xD96C`: a clear that spares exactly a three-byte cluster

```
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D96C --runtime 0xD96C -n 24
0xd96c  900100   mov  dptr,#0x0100
0xd96f  af82     mov  r7,0x82
0xd971  ae83     mov  r6,0x83
0xd973  c3       clr  c
0xd974  ee       mov  a,r6
0xd975  9410     subb a,#0x10
0xd977  5017     jnc 0xd990
0xd979  c3       clr  c
0xd97a  ef       mov  a,r7
0xd97b  94fd     subb a,#0xfd
0xd97d  ee       mov  a,r6
0xd97e  9407     subb a,#0x07
0xd980  4009     jc   0xd98b
0xd982  d3       setb c
0xd983  ef       mov  a,r7
0xd984  94ff     subb a,#0xff
0xd986  ee       mov  a,r6
0xd987  9407     subb a,#0x07
0xd989  4002     jc   0xd98d
0xd98b  e4       clr  a
0xd98c  f0       movx @dptr,a
0xd98d  a3       inc  dptr
0xd98e  80df     sjmp 0xd96f
0xd990  22       ret
```

It sets `DPTR,#0x0100` and loops upward, capturing DPL/DPH into R7/R6 at the
top of each pass — the `sjmp` at `0xD98E` returns to `0xD96F`, not to `0xD973`,
so the bounds are re-tested from the current DPTR on every iteration rather
than computed once.

**The range.** The exit test at `0xD977` is a 16-bit unsigned compare of DPH
against `0x10` (`clr C` / `mov A,R6` / `subb A,#0x10` / `jnc`), so the loop
leaves at DPTR `0x1000` and the range is XDATA `0x0100`–`0x0FFF`, 3,840 bytes.

**The exclusion, which is the sharper finding.** The second bound is *not* the
range end, and it is not the `0x07FF` its own immediates spell out. Two 16-bit
`subb` chains test DPTR, and the **`setb c` at `0xD982` is what makes the
second one read as `0x0800`**: with carry already set, `subb a,#0xff` is an
effective `−0x100` that always borrows, so the chain's high `subb a,#0x07`
computes `DPH−0x08` rather than `DPH−0x07`.

| address | test | lands on | effect |
|---|---|---|---|
| `0xD980` | DPTR < `0x07FD` | `jc 0xD98B` → `clr A` | **stores** 0x00 |
| `0xD989` | DPTR < `0x0800` | `jc 0xD98D` → `inc DPTR` | **skips** the store |

The two `jc` arms land on **different** instructions, so the first chain's
`DPTR < 0x07FD` store and the second chain's `DPTR < 0x0800` skip overlap on
`0x07FD`–`0x07FF`: the first having already established `DPTR ≥ 0x07FD`, the
second decides the whole skip window.

So the loop writes `0x0100`–`0x0FFF` with three exceptions: **`0x07FD`,
`0x07FE` and `0x07FF` are all stepped over, and none of the three is
re-cleared.** 3,840 − 3 = **3,837 bytes cleared**. This was checked by
executing the 24 committed instructions at `0xD96C`–`0xD990` with 8051
`subb`/`jc` semantics, not by reading the count off the disassembly: `0x07FC`
takes the `0xD980` store arm, `0x07FD`–`0x07FF` fall through to the skip, and
`0x0800` stores again. The branch offsets are 2-byte *relative* (`jc 0xD98B` at
`0xD980` is `40 09`), and treating them as absolute step-over corrupts the
carry into the first `subb` — the two ways this number has been got wrong.

**The skip window is exactly the cluster, and that is all that is claimed.**
`ec/annotations/xdata-clusters.csv:87` carries `main-ec-086` over
`0x07FD`–`0x07FF` — three bytes, 6 direct citing functions, 21 total, with
named writers among them (`bank0:0xD5D4`
`write_33_to_1501_join_loop_d5db`, `bank0:0xD74F`
`write_33_to_1511_then_loop`). The three bytes the loop steps over are those
three bytes, and no others. The window landing on the whole span rather than on
part of it is a fact about the bytes; what the range clear is *for* is not
established here.

**No register row is added, and none should be from this.** No row in
`ec/annotations/registers.yaml` names `0x07FD`, `0x07FE` or `0x07FF`; the
nearest named addresses in that page are `0x07A6` (`OEM_4`,
`confirmed-working-partially`, the battery-profile byte) and `0x07F3` / `0x07F6`
(`XDATA_07F3` / `XDATA_07F6`, both `present-untested`). This routine clears a
*range*, not a register, so it is not evidence of any register's status, and the
three spared bytes are named by nothing. `ec/annotations/xdata-symbols.csv` is
generated from `registers.yaml` and is not hand-edited.

**What is not claimed.** The loop steps over `0x07FD`/`0x07FE`/`0x07FF`; that
it is *meant* to preserve them across a warm reset is a hypothesis this reading
does not establish, and it is left to whoever takes the cluster next. Nothing
here was observed on hardware.

## Both addresses are instruction starts, not operand bytes

```
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D89F --converge
0x0D89F: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D96C --converge
0x0D96C: 24 of 24 preceding anchors decode onto it, 0 step over it
```

24 of 24 with 0 stepping over is the score the repository's frame evidence uses
at its strongest. It rules out the `bank1,19A8` failure mode, where an operand
byte was mistaken for an entry. The decode rests on `disasm8051.py` unmodified;
`--self-test` is the oracle for the decoder's own tables and is not re-run here
because nothing about it changed.

## Uniqueness: one DPTR immediate each, and no `lcall`/`ljmp` operand anywhere

Scanning the committed 256 KiB image for the three opcodes that could name
these addresses:

| target | `90 hi lo` (DPTR immediate) sites | `12`/`02` operand sites |
|---|---|---|
| `0xD89F` | 1 — at `0x158E` (`common,158E`), the reset trampoline | 0 |
| `0xD8A0` | 1 — at **`0x1504`**, a different trampoline | 0 |
| `0xD96C` | 1 — at `0x1594` (`common,1594`), the reset trampoline | 0 |

The common area is identity-mapped in `ec/firmware/GMxMGxx_11.800` — file
`0x158E` holds `90 d8 9f 02 11 00`, the reset trampoline itself — so
`common,158E` is the image byte `0x158E` and `common,1504` is `0x1504`; bank
0's code is at image offset `0x8000` + (addr − `0x8000`), so `bank0,0xD89F` is
image byte `0x0D89F`.

**This is why neither address has a census row, and it is a category fact
rather than a gap.** `ec/annotations/bank-call-targets.csv` counts `lcall` and
`ljmp` *operands*. A `mov DPTR,#imm16` is neither, so it produces no row — the
census never claimed these two addresses, and they are not phantoms it missed.
Its 5,998-record pin is unchanged and correct.

The next entry after `0xD96C`'s `ret` is `0xD991`
(`store_r4_r5_into_record_6e65`), already exported. It has 7 rows in
`bank-call-targets.csv`, of which **5 fall inside committed bank-0 listings**
(`D5C4`, `0xDCA7`, `0xDCC3`, `0xDD03`, `0xDD19`); the sites at `0x0D4FF` and
`0x0E0E8` are in bytes no committed listing covers. That 7-versus-5 gap is
`bank-call-audit.md` §1's upper-bound property showing up in a single target,
and is the reason the two DPTR immediates had to be found this way.

## Which of the issue's three outcomes this is

**Not (c), and provably so.** (c) is "the call-target census that seeded the
neighbourhood was a false positive." The census counts `lcall`/`ljmp` operands,
and a `mov DPTR,#imm16` yields no row at all, so it never claimed either
address; and the 24/24 convergence scores rule out misframing. Nothing in
`bank-call-audit.md` §1 is falsified. The defect this fills is the one §6
already names — *"the trampoline's own DPTR-carried target … remain invisible to
any byte scan"* — which is an absent census, not a wrong one.

**`0xD96C` is (a), and more specifically than (a).** It is a real routine on the
boot path. The issue's (a) says "real routines on the boot path, which is the
answer worth having"; what the bytes add is the shape — an XDATA clear that
preserves all three bytes of a named cluster.

**`0xD89F` is closest to (b), but (b) as written does not fit it either, and
the issue's premise is corrected here rather than dropped.** The issue frames
the two 6-byte listings as *"not routines in their own right"* and reads the
question as expecting a real routine at each. For `0xD89F` the bytes are:

- **not data** — `22` is `ret` under both decoders, at an address 24/24 of
  anchors agree is an instruction start;
- **not a table** — the window `0xD800`–`0xDFFF` is 2,048 bytes of which 34 are
  `0xFF`, so this is not an erased region either, and the byte sits between two
  named stubs that the committed listings already terminate;
- **not unprogrammed flash** — same row, opposite sign;
- **a real code entry whose entire body is `ret`.** The reset path does call
  it; the one instruction simply does not say what the caller expected.

So the honest classification is a fourth thing the issue did not name, and it
is closer to (b) than to (a) in that no routine is there to read. A reader
arriving with the issue's expectation should know that half the premise was
wrong: **one of the two is not a routine, and the other is not reachable by
`lcall` from anywhere in the image.**

### The correction that belongs one level up

`ec/annotations/bank-call-audit.md` §3 counts 403 trampolines (350 through the
bank-0 stub) and **never decodes or labels a single one of their DPTR
immediates**. Two of them are read here, and they come out one real routine and
one bare `ret` — so **nothing may be inferred about the other 401**, and nothing
is. That is the whole of the correction, and it moves no count: the 403 and the
350 stand, and the `entry`/`erased`/`other` buckets §4 gives bucket B's targets
are a different question from what a trampoline's immediate points *at*.

## The export is deferred, and the reading is not

**Both seeds matched.** `export-only` copies the committed project to scratch,
seeds the copy's functions from `ghidra-functions.csv` and exports from it; the
committed `.rep` is never opened for writing. The scratch run reports
`annotations_applied 767`, **`annotations_unmatched 0`** for bank0, and emits
`D89F.asm`/`D89F.c` and `D96C.asm`/`D96C.c` in scratch. The boundaries it
corroborates are the ones above: `D89F.asm` is a single `ret` instruction and
`D96C.asm` is `0xD96C`–`0xD990`, 0x25 bytes and 24 instructions, matching
`disasm8051.py` byte for byte. `D96C.c` shows the same store/skip structure
the two `jc` arms encode.

**So one risk in the plan this was written against did not occur, and the
reason is worth recording: the tree already holds 77 one-byte `ret`-only
listings.** A scan of every `.asm` under `ec/decompiled/` for a listing with
exactly one instruction, that instruction a `ret`, finds 77 — 21 in the common
area, 19 in bank 0, 33 in bank 1, 4 in `pd` — including named precedents
`bank0,0xD9DB` `ret_stub` and `bank0,0xD2BE` `ret_only_d2be`, both
`type: unresolved` / `name_basis: unresolved`. The premise that `0xD89F` would
be the first such listing, and that Ghidra might decline to emit a function for
it, was wrong; it emits one, and the row grades as the two precedents do. So
this address sets no new precedent either way — it joins a family of 77.

**A second environment fact, which blocks the export on any runner.** The
committed Ghidra project records its owner, and it is not the user a CI runner
runs as:

```
$ grep -o 'VALUE="[a-z]*"' ec/ghidra/project/ec.rep/project.prp
VALUE="dave"
$ analyzeHeadless ... -process bank0.bin ...
ERROR Abort due to Headless analyzer error: ghidra.util.NotOwnerException:
      Project is owned by dave
```

This fails **identically on a clean tree with no annotation rows added** (run as
a control, same exit status), so it is the environment and not this change. The
`ec/ghidra/README.md` export-only path therefore needs the scratch copy's
`project.prp` `OWNER` value set to the running user before Ghidra will open it;
the committed project is untouched by that, since the copy is the disposable
artifact the mode exists to create. The commands below do this.

**Why the artifacts are not committed.** `verify_reassembly.py:check` fails the
listing/report asymmetry in both directions
(`ec/tools/verify_reassembly.py:1178-1187`): a `listing-index.csv` row with no
`reassembly.csv` row prints *"the report predates this export"*, and a report
row with no listing prints *"the report is stale"*. The only writer of that row
is a full `--report`, which `refuses_committed_report` will not narrow to a
single row, and `ec/ghidra/README.md:415-446` states the consequence: the
runner's own `sdas8051` rewrites all 2,707 `assembler` strings and moves 52
outcomes, so a new export wants a machine with the nix toolchain.
`.github/scripts/agent-gates.sh` runs that `--check`, so landing the export here
means landing a red gate.

**This is issue #255's shape exactly.** It read twelve bytes at file `0x0C10C`
and, *"rather than land the export with `verify_reassembly.py --check` red, left
the seed row and the listing off its branch for a pinned-toolchain run to add
both."* So this lands the reading and defers the export.

**One correction to the issue's own premise.** The issue calls this *"a project
rebuild, so it cannot share a branch with another EC rebuild"*, and asks for
`--mode rebuild-project`. **`--mode rebuild-project` is not required and was not
used.** `export-only` seeds the copy and exports from it; the committed `.rep`
is never opened for writing, so there is no binary diff and no `.gitattributes
-merge` refusal. This branch is a one-line CSV diff plus two prose pointers and
can merge alongside another EC change. If a seed ever *does* report
`annotations_unmatched`, that is the README's "the project needs
`--mode rebuild-project`" case and the run has to say so rather than let it
pass — it did not arise here.

### The row-by-row list for the pinned-toolchain run

Everything that moves when the export lands, so that run needs no re-derivation:

| # | file | change |
|---|---|---|
| 1 | `ec/annotations/ghidra-functions.csv` | add the 2 rows: `bank0,0xD89F` `ret_only_d89f` (`unresolved`/`unresolved`) and `bank0,0xD96C` `clear_xdata_0100_0fff_sparing_07fd_07fe_07ff` (`init`/`code-shape`), both `basis: hand-decoded` with the `evidence` paths the .asm/.c pair will exist under |
| 2 | `ec/decompiled/bank0/` | add `D89F.asm`, `D89F.c`, `D96C.asm`, `D96C.c` |
| 3 | `ec/decompiled/index.csv` | +2 rows, 2,710 → 2,712 |
| 4 | `ec/decompiled/listing-index.csv` | +2 rows, 2,710 → 2,712 |
| 5 | `ec/ghidra/reassembly.csv` | +2 rows, 2,707 → 2,709, via a full `--report` on the pinned toolchain |
| 6 | `ec/ghidra/c-digests.csv` | +2 rows, 2,710 → 2,712, via `--write-digests` |
| 7 | `ec/tools/build_ec_decompile.py` | the 1,855 pins at lines 1810, 1812 and 1828 → 1,857, plus the history comment at 1807; the 2,710 pins at 1774, 1776, 1777, 1779 and 1793 → 2,712, plus the history comment at 1770 |
| 8 | `ec/annotations/subsystems.md` | `annotated function rows` 1855 → 1857 at **both** line 58 and line 444; `exported functions` 2710 → 2712 at **both** line 57 and line 443; the per-program `bank0` row and the unannotated percentage, which `check_subsystems()` recomputes |
| 9 | `docs/findings/citing-listing-evidence.md` | 1,855 → 1,857 at lines 112 and 277 |

Items 7–9 were written against the 1,851 the CSV held when this list was
derived. **Issue #558 has since added four rows** (`common,0x07F0`, `0x0F75`,
`0x158E`, `0x1594`), so the CSV is 1,855 and each of those three items starts
from 1,855 and lands on 1,857 rather than from 1,851 to 1,853. The `bank0`
per-program row and the 2,710 figures are unmoved, because #558's four rows are
all common-area and it changed no export row count.

Items 3–9 are all build gates rather than documentation figures, which is why
none of them is moved here: every one of them is a hard `--check` that a
half-landed export would turn red.

## Reproducing this

The decode rests on the committed image and an unmodified `disasm8051.py`, so
every claim above re-derives from committed inputs:

```sh
# 1. the two decodes
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D89F --runtime 0xD89F -n 8
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D96C --runtime 0xD96C -n 24

# 2. both are instruction starts, not operand bytes: 24 of 24 onto, 0 over
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D89F --converge
python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0D96C --converge

# 3. the machine code the two disagree about, and the reset vector
cat ec/decompiled/common/0070.asm ec/decompiled/common/158E.asm ec/decompiled/common/1594.asm
cat ec/decompiled/bank0/D889.asm ec/decompiled/bank0/D894.asm

# 4. the cleared count: execute the committed bytes, 3,837 stored, sparing
#    0x07FD-0x07FF. jc/sjmp are 2-byte *relative*; setb c at 0xd982 is what
#    makes the second chain's bound 0x0800 rather than 0x07FF.
python3 - <<'EOF'
img=open('ec/firmware/GMxMGxx_11.800','rb').read()
def rel(pc):
    o=img[pc+1]; return pc+2+(o-0x100 if o>0x7F else o)
C=0;A=0;r7=r6=0;dptr=0x0100; stored=set(); pc=0xD96C
while True:
    op=img[pc]
    if   op==0x90: dptr=(img[pc+1]<<8)|img[pc+2]; pc+=3
    elif op==0xAF: r7=dptr&0xFF; pc+=2
    elif op==0xAE: r6=(dptr>>8)&0xFF; pc+=2
    elif op==0xC3: C=0; pc+=1
    elif op==0xD3: C=1; pc+=1
    elif op==0xEE: A=r6; pc+=1
    elif op==0xEF: A=r7; pc+=1
    elif op==0x94: t=A-img[pc+1]-C; C=1 if t<0 else 0; A=t&0xFF; pc+=2
    elif op==0x50: pc = rel(pc) if C==0 else pc+2
    elif op==0x40: pc = rel(pc) if C==1 else pc+2
    elif op==0xE4: A=0; pc+=1
    elif op==0xF0: stored.add(dptr); pc+=1
    elif op==0xA3: dptr=(dptr+1)&0xFFFF; pc+=1
    elif op==0x80: pc = rel(pc)
    elif op==0x22: break
print(len(stored), [hex(x) for x in range(0x100,0x1000) if x not in stored])
EOF
# -> 3837 ['0x7fd', '0x7fe', '0x7ff']

# 5. the cluster the clear spares all of, and the absent register rows
sed -n '82p' ec/annotations/xdata-clusters.csv
grep -nE '0x?0?7[Ff][d-f]' ec/annotations/registers.yaml || echo "(no row)"

# 6. the 77 existing one-byte ret-only listings, and the two named precedents
for f in $(find ec/decompiled -name '*.asm'); do
  n=$(grep -cE '^[0-9A-F]{4} +[0-9a-f]{2} ' "$f")
  [ "$n" = 1 ] && grep -qE '^[0-9A-F]{4} +22 +.*ret' "$f" && echo "$f"
done | wc -l
cat ec/decompiled/bank0/D9DB.asm ec/decompiled/bank0/D2BE.asm

# 7. the gate, which stays green because nothing generated moved
bash .github/scripts/agent-gates.sh
```

The corroborating export needs the owner fix described above, on the scratch
copy only:

```sh
# seed the two rows into ec/annotations/ghidra-functions.csv first, then:
rm -rf /tmp/ec && python3 ec/tools/build_ec_decompile.py --work /tmp/ec || true
# the run above fails at project open on a runner; patch the scratch copy's owner
sed -i 's/VALUE="dave"/VALUE="runner"/' /tmp/ec/project-copy/ec.rep/project.prp
# and re-run the same analyzeHeadless command line the tool printed, per program
# (bank0.bin, bank1.bin, pd.bin) -> /tmp/ec/out/bank0/D89F.{asm,c}, D96C.{asm,c}
grep -h annotations_unmatched /tmp/ec/reports/apply-bank0.tsv   # 0
```

## The §26 summary was one unit too wide

`ec/tools/check_cluster_citations.py` reads §26's summary of this write-up in
`docs/findings.md` and reported one disagreement with
`ec/annotations/xdata-clusters.csv`:

```console
$ python3 ec/tools/check_cluster_citations.py
docs/findings.md:5636: 0x0800 is not a member of any cluster this line names (`main-ec-086`); it is a member of `main-ec-104`
1 citation(s) disagree with ec/annotations/xdata-clusters.csv
```

**The summary's unit was wrong — not the membership claim, and not the any-of
fallback.** The claim is right: §26 named exactly `main-ec-086`'s three bytes.
The fallback is doing what its docstring says it does, which is to hold a unit
that names one cluster against that one cluster. The one unit it reported, which
started at `docs/findings.md:5636`, carried two attributions:

| attribution | addresses | cluster named |
|---|---|---|
| the membership claim, "those three are the whole of the … cluster" | `0x07FD` `0x07FE` `0x07FF` | `main-ec-086` |
| the bound operand, the `setb c` at `0xD982` making the second bound | `0x0800` | none |

`0x0800` is in `ec/annotations/xdata-registers.csv:738`, so it is a known XDATA
address, and `0x0630 0x06C4 0x0800` is `main-ec-104`
(`ec/annotations/xdata-clusters.csv:105`) rather than the `main-ec-086` the same
unit named. The summary now says the two things in two sentences, in a fenced
block rather than a blockquote so that the split does not depend on where the
line breaks fall (see follow-up 6):

```
… except it steps over `0x07FD`, `0x07FE` and `0x07FF`** — 3,837 of 3,840
bytes, and those three are the whole of the `main-ec-086` cluster.
The `setb c` at `0xD982` is what makes the second bound `0x0800` rather than
the `0x07FF` its own immediates spell out.
```

**No claim changed** — the same three bytes, the same 3,837, the same cluster,
the same `setb c` and the same two bounds; only the sentence boundary moved. The
bound sentence picks up this write-up's own wording for why `0x07FF` is not the
bound, from "The exclusion, which is the sharper finding" above, which already
stated it in a unit that named no cluster. **The summary should say things the
way the write-up it points at already says them** — and the write-up was silent
on the committed tree until now, which is why this section exists.

The first sentence now names one cluster and every address it carries that the
registers CSV knows is a member of it (`0x0100` and `0x0FFF` have no registers
row; `0xD89F` and `0xD96C` are code). The second names no `main-ec-NNN`, key or
name, so `cited_clusters()` returns empty and the unit is skipped before any
rule runs. Nothing was added to the tool, no regex was loosened, and no skip
was introduced.

> **CORRECTION (2026-09-25, issue #801): three line pointers in this file
> were stale, and the sentences they sat in were not.** The superseded figures
> stay visible here per `docs/findings.md` §4a-4d, which is also why this is a
> blockquote rather than a paragraph in the file's own voice: a correction
> written as ordinary prose reads as current, and `check_citation_lines.py`
> checks a live paragraph and skips a quoted one. Each cell is named by the
> sentence it sits in rather than by line number, because a correction citing
> the line numbers of the file it is correcting goes stale on arrival — which
> is this note's own subject.
>
> - The bound operand, "so it is a known XDATA address", cited
>   `ec/annotations/xdata-registers.csv:583`; the `0x0800` row is at **`:738`**.
> - The same sentence, "rather than the `main-ec-086` the same unit named",
>   cited `ec/annotations/xdata-clusters.csv:101`; `main-ec-104` is at
>   **`:105`**.
> - "The skip window is exactly the cluster" and the hand re-check below both
>   cited `ec/annotations/xdata-clusters.csv:82`; `main-ec-086` is at **`:87`**.
>
> **No claim changed, and no figure in any of the four sentences moved** —
> only the pointer did, because each was a rank into a generated CSV that has
> since grown above the row. The first two cells are issue #801's own item; the
> third is in the same file and the same class and the issue did not reach it,
> since `grep -n 'csv:'` over this file returns exactly these four and no
> other. A cluster id is a rank for the reason
> `check_cluster_citations.py`'s docstring gives at length, and a CSV line is
> the same kind of handle with none of the fallbacks — there is no
> `cluster_key` to resolve a line number with.
> `ec/tools/check_citation_lines.py` now holds all four to the row for the id
> or address they name;
> [`prose-line-citations-held.md`](prose-line-citations-held.md) is the
> write-up, and its table says which row each superseded line actually held.

### The measurement

| | before | after |
|---|---|---|
| `check_cluster_citations.py` | exit 1, 1 disagreement | exit 0 |
| `test_check_cluster_citations.py` | 46 tests, 1 failure (`test_committed_prose_matches_committed_census`) | 48 tests, 0 failures |

**The count going 1 → 0 is not the evidence**, and it is recorded next to the
re-check below for the reason the issue gives: a rule change that silently
admitted real drift would show the same way.

### The hand re-check

`main-ec-086` is `0x07FD 0x07FE 0x07FF` and nothing else
(`ec/annotations/xdata-clusters.csv:87`), which is what the reworded first
sentence still says, and the new bound sentence makes no membership claim at
all. The `0xD96C` loop's own execution trace (recipe 4 under "Reproducing
this") puts `0x0800` on the store arm, so **the boot-path clear stores `0x00`
at `0x0800`, a byte the `main-ec-104` cluster names** — 3 addresses, 4
references, `functions_touched` 2, one of them
`bank1:0x8DBC=write_05_to_06c4_after_1984_check [gate]`, `co_reading` 0 and
`co_reading_dominant` `no`.

That is a **static co-membership reading from the committed image and the
committed census**, and three things about it are not claimed:

- **The store was not observed.** It is derived by executing the 24 committed
  instructions at `0xD96C`–`0xD990` with `subb`/`jc` semantics, the same check
  recorded under "The exclusion" above. Nothing here ran on hardware.
- **It is not a claim that the store matters.** Whether `bank1:0x8DBC` reads
  `0x0800`, and what a boot-path write to it does, is not established. The
  function's name says it writes `0x06C4`, a sibling member, after a check at
  `0x1984`; that is a reading of a name, and the body has not been read.
- **Neither cluster is wrong.** The census is right about both, and a boot-path
  clear that stores into one of them is ordinary. This is an observation about
  co-membership, not a defect and not a claim about the `setb c` bound.

### Why the fallback did not learn the exemption instead

The issue offered the alternative — an exemption for an address a sentence
introduces as a bound or operand — and it is declined here, in the order that
decided it:

1. **The two exemptions cited as precedent are not this family.** §5's census
   rows (`xdata-register-map.md:1313`), the `0x06E6`/`0x0860` gate-block row
   among them at `:1405`, are skipped by the membership rule because a
   *structural* condition is absent: none of them says "member" anywhere, so the
   cue never fires and `census_row()` is the only rule that reads them. §26's
   sentence did say it, and did mean it. The difference is unit size, not the
   cue.
2. **"Introduced as a bound or operand" is a lexicon, and this tool is built
   against lexicons.** Nothing marks that role structurally in markdown; it can
   only be read off words like *bound*, *immediate*, *operand*, *target*. The
   tool's own docstring lists a lexicon false positive — a name like
   `charge-target` read as a citation — as a known limit, and the resolution
   recorded there was to constrain the *input* (multi-token slugs), not to
   loosen the matcher. A range is the one such role the tool can see without
   words, because `0xAAAA-0xBBBB` is a single token (`SPAN`) and
   `census_row()` reads it as a row's range rather than as two member claims.
   A new skip would also have to earn the case the test file's docstring
   demands — *a skip that is not deliberate is the bug* — and the set it would
   newly admit is not enumerable from the committed tree.
3. **A rule change needs its own corpus-wide re-run.** Whether a lower
   disagreement count means the rule is right or means drift newly admitted is
   not decidable from the count. That re-run is its own issue (follow-up 5), not
   a half-measure inside a reword.

The gap is real and is recorded as a follow-up rather than closed.

### The case that pins the decision

`ec/tools/test_check_cluster_citations.py` now carries both directions as
`OneAttributionPerUnit`: the split pair is silent, and the re-packed
one-sentence form still reports `0x0800`. It is a `known=` override and a
fixture census carrying the real two clusters, so the case is self-contained
and cannot perturb the 46 it does not touch. The re-packed case is *expected* to
report: it says the unit was too wide, and a rule that stopped reporting it here
would be a corpus-wide loosening made by half-measure against one sentence.

## Follow-ups

1. **Seed and read `0xD8A0`** — the real init routine the `0xD89F` operand sits
   one byte short of, with its own unique `mov DPTR,#0xD8A0` at `common,1504`.
   The most substantive of these, and the one that would settle whether the
   reset path's second call was meant to land there.
2. **Label the 403 trampoline DPTR immediates** (350 through the bank-0 stub)
   with the same `entry`/`erased`/`other` treatment bucket B gets, so the
   family is not an undecoded 403-row gap. This is the real gap; it is a
   separate change that would touch `audit_call_targets.py` and
   `bank-call-audit.md` substantially.
3. **What XDATA `0x07FD`/`0x07FE`/`0x07FF` are** — the three bytes a boot-time
   clear spares, which are exactly `main-ec-086` (`0x07FD`–`0x07FF`, 21 citing
   functions), with no `registers.yaml` row and placeholder rows at
   `0x07F3`/`0x07F6` either side. A value preserved across a warm reset is the
   obvious hypothesis and is explicitly not claimed here.
4. **The export itself**, on a machine with the nix-pinned `sdas8051`, per the
   row-by-row list above.
5. **Whether the any-of fallback should learn an operand exemption** — it has
   none today for an address a sentence introduces as a bound or operand, which
   is the shape §26's summary had and `0x0800` fired on. The summary was
   reworded instead and the tool is left conservative, so the unit-sizing gap
   above is still open. If the exemption is wanted it is a corpus-wide
   loosening: it needs its own re-run over every committed citation, and the
   set of units it would newly admit is not enumerable from the committed tree,
   so it is a separate change with its own issue rather than a tuning pass
   against one sentence.
6. **`units()` keeps a blockquote's `>` in the joined text, so a sentence
   boundary inside one is recognised only where the `>` does not fall between
   the period and the next capital.** `TERMINATOR` looks ahead for
   `[A-Z\`*_|-]`, and `>` is not in that set, so where a quote is wrapped decides
   whether its two sentences are one unit or two. Measured here by accident: the
   reworded pair quoted as a blockquote passed with the period mid-line and went
   red on the next wrap, with no change in the text. Five membership-checked
   units in the corpus carry the markup today (two each in
   `manual-fan-ctrl-0751.md` and `xdata-06c2-06db-timers.md`, one in
   `xdata-086x-dispatch.md`). **Stripping every `>` in `ec/`, `docs/` and
   `evidence/` and re-running changes no verdict** — 0 disagreements either way
   — so this is a latent limit rather than a live false positive, and the
   candidate fix is verdict-neutral on today's corpus. Whether a blockquote
   citation should be split at all is still open, and the direction is not
   settled: a merged unit carries more addresses into the fallback, while also
   letting one denial skip a claim that shared the unit.
