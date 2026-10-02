# `pd` 0x34EF falls through into `pd` 0x34F2, and the two are entries over a shared tail rather than one routine split in half (issue #646)

`ec/annotations/ghidra-functions.csv`'s `pd,34EF` row read `set_dptr_0424`
with `type=unresolved` and the comment "A single `mov DPTR,#0x424` with no
ret, so the pointer's use is not decoded here." It is now `type=forwarder`,
and the comment records what the bytes do. The clause was not wrong about
there being no `ret`; it was answering a question about where Ghidra's export
put a function boundary and reading it as a statement about where control
goes. `pd,34F2` starts immediately after and is a listing in its own right, so
control runs straight into it.

The change that fixes this is one annotation row. The rest of this write-up
is the measurement behind it and the family it belongs to, published by
[`ec/tools/pd_no_ret_fallthrough.py`](../../ec/tools/pd_no_ret_fallthrough.py)
and held by
[`ec/tools/test_pd_no_ret_fallthrough.py`](../../ec/tools/test_pd_no_ret_fallthrough.py).
Every figure below is reproducible from committed inputs with the commands in
[Re-deriving](#re-deriving) at the end.

---

## The bytes

`ec/decompiled/pd/34EF.asm` is one instruction and
`ec/decompiled/pd/34F2.asm` is two, and `listing-index.csv` records
`size=3` and `size=6` for them:

```
34EF     90 04 24 mov      DPTR, #0x424
34F2     75 f0 60 mov      B, #0x60
34F5     02 10 bc ljmp     0x10bc
```

They are contiguous: 0x34F2 is 0x34EF + 3. There is no gap and no other
listing between them, so a `lcall 0x34EF` runs off the end of its own three
bytes into the next two instructions.

`ec/decompiled/pd/10BC.asm` is where that lands, and it ends in `ret`:

```
10BC     a4 - -   mul      AB
10BD     25 82 -  add      A, DPL
10BF     f5 82 -  mov      DPL, A
10C1     e5 f0 -  mov      A, B
10C3     35 83 -  addc     A, DPH
10C5     f5 83 -  mov      DPH, A
10C7     22 - -   ret
```

`mul AB` with `B = 0x60` is `A * 96`, added into `DPL` with the carry into
`DPH`, so the effect on the pointer the caller left is

    DPTR = DPTR_in + 0x60 * A

and the `ret` at 0x10C7 means control comes back to the instruction after
whichever `lcall` got here.

### The two entries, and why that is the whole of the retyping

**A `lcall 0x34EF` is at 0x67E0 and at 0xCB40**, both inside committed
listings (`pd,6673.asm` and `pd,CB2A.asm` respectively), so the return address
is **0x67E3** or **0xCB43**. The 0xCB40 site is the one the companion
dispatch-key issue reads, and it is why 0xCB43 rather than 0x67E3 is the
address that chain returns to.

**`pd,34F2` is `lcall`ed in its own right, at 0x6782** — inside `pd,6673.asm`,
the same listing that holds the `lcall 0x34EF` at 0x67E0. This is the fact
that decides the row's `type`, and it is the one the issue's framing did not
have. Without it, 0x34F2 would be reachable only by falling in from 0x34EF,
the two listings would be one routine cut in half by the export, and the
honest `type` would be an argument about whether to merge the rows. With it,
the pair is two separately-callable entries over one shared tail: `shared-tail`
in the tool's vocabulary.

### Three figures in the issue body that do not hold

Per `CLAUDE.md`'s calibration rule each wrong version is left visible with its
correction beside it, rather than quietly dropped, and none of the three is
repeated anywhere else in this repository.

1. **"`ec/decompiled/pd/34F2.asm` is `mul AB / add A,DPL / …`"** — that body
   is `ec/decompiled/pd/10BC.asm`. `34F2.asm` is `mov B,#0x60 / ljmp 0x10bc`,
   as the issue's own decode block shows two lines earlier. The consequence is
   that the *tail* routine is 0x10BC, not 0x34F2, and the two are named
   separately in every table below.

2. **"The routine at `0x34EF` is therefore complete at 6 bytes"** — 0x34EF is
   3 bytes and 0x34F2 is 6, contiguous, so the span from 0x34EF to 0x34F7 is
   **9**. 6 is 0x34F2's own size, which is a different question.

3. **"178 `pd` rows carry a 'not decoded here' or 'no ret' clause"** and
   **"filtering to those … leaves 20"** — neither reproduces. The clause
   matches a larger population than 178, and `--check` against the committed
   CSV is what prints its size on the tree as it stands. The issue's stated
   filter — take the next address as `addr + listing-index.csv`'s `size`,
   decode one instruction there, keep the rows whose successor begins a
   `ljmp`/`jmp`/`sjmp`/`ajmp` — yields these rows and no others: 0x0000,
   0x0012, 0x7045 and 0xF786.

   **0x34EF is not among them**, and the reason is worth keeping because it is
   what a filter built this way gets wrong: `pd,34F2` begins `mov B,#0x60`, and
   the `ljmp` is an instruction later. A successor's *first* instruction says
   nothing about whether control leaves it. The predicate that does find
   0x34EF is the **byte arm** below.

---

## The family, and the two arms it is not one of

Two membership tests are printed side by side, and neither is presented as
"the" family, because they answer different questions.

**The clause arm** is a regex over the annotation comment for either of the
two clauses. It is a **text match over prose**: a row whose comment does not
carry the clause is invisible to it whatever its bytes say, and a row that does
is in it whatever its bytes say.

**The byte arm** is a decode. The listing's last instruction is neither a
return nor a transfer of control, and `addr + size` is another listing's entry
— so control leaves the listing by running past its end, into a boundary rather
than off the end of the export. `reti` counts as a return here, not just `ret`:
a listing ending in `reti` falls into nothing whatever its comment says, and
reading only `0x22` would admit 0x0056, 0x0094, 0x00B2 and 0x00F0 for a reason
that has nothing to do with the boundary.

**The byte arm is not a subset of the clause arm** — rows qualify on their bytes
while their comment carries neither clause, which is what a text filter cannot
see — and `pd,34EF` is in both.

Neither population's size is written down here or in the tool's `--self-test`,
because a comment or a listing that lands moves both, and a figure held in two
places is a value every other open branch has to edit. `--check` against
`ec/annotations/pd-no-ret-fallthrough.csv` prints them on the tree as it
stands; what `--self-test` asserts is membership and relationship, which
survive a row arriving.

The tool prints each count with the predicate that produced it, so a reader who
wants a different family can see which one is being reported.

### Verdicts, from the decoded listings

Each family row gets one of three verdicts, decided on the **committed
listings' own decoded instructions** and never on the byte scan:

| verdict | what it means |
|---|---|
| `shared-tail` | the successor is itself a transfer target, so the two listings are two entries over one tail |
| `falls-through-unentered` | the successor is contiguous and nothing transfers to it, so the two listings are one routine's worth of code with the boundary inside it |
| `boundary-wrong` | nothing transfers to the row's own address either: it is reached only by falling in from the previous listing, so the boundary is misdrawn and the real entry is elsewhere |

`pd,34EF` is `shared-tail`, on the 0x6782 site.

The rows that are **not** `shared-tail` are the interesting ones, and all seven
are in
[`ec/annotations/pd-no-ret-fallthrough.csv`](../../ec/annotations/pd-no-ret-fallthrough.csv)
with their bytes:

| addr | listing | size | successor | successor's first instruction | verdict | successor reached from |
|---|---|---:|---|---|---|---|
| `0x0012` | `ff_filler_not_a_function_0012` | 1 | `0x0013` | `ljmp 0x00b2` | `falls-through-unentered` | nothing, by either measure |
| `0x3632` | `set_dptr_042f_then_fall_through` | 3 | `0x3635` | `mov 0xf0,#0x60` | `falls-through-unentered` | 0x44A1 by byte scan only |
| `0x90F3` | `set_dptr_0004_then_fall_through` | 3 | `0x90F6` | `lcall 0x1253` | `falls-through-unentered` | 0xCC7A, 0xCCAA by byte scan only |
| `0xB2AE` | `mul38_ptr_0946` | 4 | `0xB2B2` | `add a,#0x46` | `falls-through-unentered` | 0x4DAA by byte scan only |
| `0x34D6` | `index_stride_5e_from_07d6` | 3 | `0x34D9` | `movx a,@dptr` | `boundary-wrong` | 0x7DB3, 0x859C |
| `0x56ED` | `read_xdata_0852` | 4 | `0x56F1` | `mov 0xf0,#0x77` | `boundary-wrong` | 0xF5C4 |
| `0xB24C` | `load_r3_r0_jmp_0f0e` | 1 | `0xB24D` | `mov r2,a` | `boundary-wrong` | 0xA02B |

**`pd,3632` is the row this table exists for.** Its own comment says 0x3632
and 0x3635 "look like one routine split by the function boundary". The byte
scan names `lcall 0x3635` at 0x44A1, but **0x44A1 is not an instruction start
any committed listing decodes**, so that is a candidate and 0x3635's
reachability in its own right is *not found by this method* — the same
calibration §"What this does not establish" applies to every byte-scan
position. The verdict column reads `falls-through-unentered` for exactly that
reason, which is the tool reporting the limit of its own narrow population
rather than deciding the question in either direction. **That row is not edited
here**; it is not this change's to touch, and the correction belongs with
whatever reads 0x3632 next.

The three `boundary-wrong` rows are the same shape one step earlier: each is
reached only by falling in from the listing before it, so the boundary that
matters is the one above the row, not the fall-through below it. `pd,34D6` is
the clearest — no committed listing decodes a transfer to 0x34D6, while its
successor 0x34D9 has two committed call sites. The byte scan does name 0x34D6
from five positions (0x30FA, 0x310D, 0x31BE, 0x31D5 and 0x32BD); none of the
five is an instruction start a committed listing decodes, so they are
candidates the narrow population cannot confirm rather than call sites.

---

## The entry-site census, and the de-duplication behind it

Entry sites are counted **twice**, as two populations, and the two are never
exchanged for one another.

**The byte scan**, over the image's whole 64 KiB for `12 aa aa` / `02 aa aa`,
finds **7266** sites naming **1866** distinct targets. This is the wide half,
and both figures are counts over the committed image, so no change to this
repository moves them.

**The committed listings' own decoded instructions** are the narrow half, and it
is the one verdicts are assigned from, because a site there is an instruction
start a committed listing states and so cannot be an operand byte. Its size is
not written down here: it moves with every export, and `--check` against the
committed CSV is what prints it. What is held instead is the relationship —
every `lcall`/`ljmp` a committed listing decodes is a site the byte scan also
finds, since it spells the same three bytes at the same address.

**De-duplication is by site address, and it is not a nicety.** A per-listing
walk over the listings' own spans finds **more** sites than those spans hold,
and every address it counts twice is in 0x4C12-0x4D18: `pd/4D6F.asm` spans
0x4A12-0x4E58 and carries rows at 0x4C12-0x4D18, which are the same bytes
`pd/4C12.asm`, `pd/4C19.asm`, `pd/4C20.asm` and `pd/4C27.asm` are the subjects
of. One address, two listings, one site — and a census reporting the walk's
figure would be wrong by a difference it could not explain. The byte scan
walks each position once by construction, which is what makes the two halves
comparable.

---

## What this does not establish

**Nothing behavioural, and no live test ran.** Every figure is a static
measurement over committed `.asm` listings and the committed firmware. No
hardware is reachable from a GitHub-hosted runner, no register was read back,
no write was attempted, and nothing here is a claim about what the machine
does.

**A row this scan did not reach is *not found by this method*, never absent.**
The committed pd listings cover a fraction of the image, and the byte scan
cannot tell code from data in either direction: a site it finds may be an
operand byte, and a target it misses may still be reached by a paged or
relative form or from a byte no listing covers. `pd,3632` above is the case
where the two halves disagree, and the disagreement is left standing rather
than resolved in either direction.

**The byte arm's rows are candidates, not defects.** A candidate is a listing
whose boundary may be a function-boundary artefact. This change retypes one row
and proposes nothing for the rest; the CSV carries the classification so a
follow-up can land the comments in tranches rather than in one large diff to
the file most likely to collide with other open work.

**The clause arm is a text match over prose** and settles nothing on its own.
It is printed beside the byte arm for exactly that reason, and a reader who
wants a different population should say which predicate produced it.

**The `0x0424` read/write direction is still unresolved here, and this change
does not resolve it.** What is established is the arithmetic — 0x34EF sets the
pointer and `pd,10BC` adds `0x60 * A` to it — not whether the resulting
address is read or written.
[`ec/annotations/xdata-0400-045f-sites.csv`](../../ec/annotations/xdata-0400-045f-sites.csv)
row 88 keeps saying "direction unresolved here" for the 0x34EF site, and that
sentence is still true.

**The 0x11C2 dispatch key is untouched.** `pd 0x38D3` is
`read_be16_from_dptr`, returning the byte pair at the incoming DPTR in A:B;
at 0xCB2A the DPTR it reads is whatever 0x349B left, and 0xCB4A is one of the
`lcall 0x11C2` candidates the byte scan names in the image. A candidate carries
no table behind it — nothing in the committed inputs establishes what follows
any of them — so this write-up attributes none to the other call sites.
This change narrows the CB2A chain — 0x34EF's contribution to it is now
recorded rather than left as an unresolved clause — and decides nothing about
the key. The chain itself is written up in
[`pd-11c2-dispatch-key-selector.md`](pd-11c2-dispatch-key-selector.md), and
[`pd-common-address-spaces.md`](pd-common-address-spaces.md) §"The CB2A comment
tension" is the section this issue's row sat behind.

**`pd,3632` and `pd,3635` are not merged, and `pd,34EF` is not renamed.** The
0x3632 precedent goes the other way on the naming question — it is
`set_dptr_042f_then_fall_through` and does carry its fall-through in the name —
and `set_dptr_0424` does not. Renaming would ripple through five name-keyed
generated CSVs and both export headers for a name that is not false, so it is
left as a follow-up with its cost recorded rather than asserted. The issue
asked whether the two should share one row and to *note* rather than assert
the answer; the answer is that the 0x6782 site makes them two entries, so the
merge is not indicated on this evidence.

---

## What this opens

- **The remaining `shared-tail` rows.** Each is a pair the export separated and
  the bytes do not, and each is a candidate for the same treatment 0x34EF got.
  The CSV is sorted by address and carries the successor's first instruction, so
  the rows cluster visibly around 0x3494-0x3506, where the `mov B,#0x60 /
  ljmp 0x10BC` idiom repeats.
- **`pd,3632`'s comment**, which calls its pair "one routine split by the
  function boundary", where the byte scan's `lcall 0x3635` at 0x44A1 is a
  candidate no committed listing decodes. Whether that is enough to call the
  comment a half-statement is what a later reader with a decompile can settle.
- **Whether the `boundary-wrong` rows' real entries are the addresses above
  them.** Three listings are reachable only by falling in, and each names a
  successor that is a committed call target.
- **The sites in 0x4C12-0x4D18 that two listings both carry**, which is a
  property of `pd/4D6F.asm` spanning rows other listings are the subjects of.
  Any other tool that walks listings by span rather than by site address has the
  same bug.

---

## The test

[`ec/tools/test_pd_no_ret_fallthrough.py`](../../ec/tools/test_pd_no_ret_fallthrough.py)
holds the byte claims and **no census total** — a test asserting how many rows
the family has is a value every merge has to edit, which this repository has
been burned by repeatedly. The population lives in one place,
`ec/annotations/pd-no-ret-fallthrough.csv`, which `--check` reproduces; the
tool's `--self-test` asserts the two arms' membership and their relationship to
each other, and the suite runs that for its exit code, so what it asserts is
asserted here transitively too.

What the suite holds: the pair's bytes, each re-read out of the image rather
than trusted from a transcription, with the **adjacency asserted separately**
because "control falls straight into it" needs both the bytes and the absence
of a gap; `pd/10BC.asm`'s `ret` at 0x10C7; the two return addresses derived as
*call site + 3* rather than written down, so 0xCB43 is a consequence of the
call site rather than a fourth fact to keep in step; the 0x6782 site as a
**committed instruction start** and not a byte pattern, since that is what
separates `shared-tail` from a merge candidate; the corrected annotation row
read from the outside, including the clause it must no longer carry; and the
two rows this change does *not* edit, held as they stand so a merge that
quietly took them fails.

---

## Re-deriving

```console
$ python3 ec/tools/pd_no_ret_fallthrough.py --self-test
$ python3 ec/tools/pd_no_ret_fallthrough.py --check
$ python3 ec/tools/pd_no_ret_fallthrough.py            # the report
$ python3 -m unittest discover -s ec/tools -p 'test_pd_no_ret_fallthrough.py'
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ec
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ec --write-digests
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ec --check
$ python3 ec/tools/gen_findings_index.py --check
```

The three listings this rests on can also be read straight out of the image:

```console
$ python3 -c "import sys;sys.path.insert(0,'ec/tools');import disasm8051; \
  from trace_xdata_refs import offset_for_runtime; \
  b=offset_for_runtime(0,'pd-image'); \
  d=open('ec/firmware/GMxMGxx_11.800','rb').read()[b:b+0x10000]; \
  [print('%04X %s'%(a,t)) for a,_,t in disasm8051.decode(d,0x34EF,0x03,addr=0x34EF)]"
34EF  mov  dptr,#0x0424
34F2  mov  0xf0,#0x60
34F5  ljmp 0x10bc
```

`ec/tools/pd_no_ret_fallthrough.py` is **not registered in any gate**:
`.github/scripts/agent-gates.sh` is a pipeline file and this branch's token
has no `workflow` scope, so a gate call is a human's change. It is runnable,
cited here, and covered by `bash tools/run-tests.sh`'s `test_*.py` glob.
