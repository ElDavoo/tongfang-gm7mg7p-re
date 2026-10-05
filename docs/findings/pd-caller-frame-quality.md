# A caller frame too short to have held a load cannot certify that it held none

(2026-10-05, issue #1117. Static reading and commands over one committed image,
measured at `29e06182`. No capture opened, no EC, no hardware, no Windows.)

`ec/annotations/pd-index-callers.csv` has five rows. Four carried
`status: unresolved`, which reads as *a search for a literal index load happened
in this caller's frame and found nothing*. One of those four — the `0x7421`
byte-scan row at caller `0xC9DD` — rests on a frame that is **one instruction
long**:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 \
          --callers 0x7421
PD runtime 0x7421
  byte-scan entry 0x7420: reaches the site with no intervening `ret`; preceded by mov  0xf0,#0x60; 0 jump target(s) in between
    file 0x2C9DD  runtime 0xC9DD  call      lcall 0x7420     frame 1/24 (1 insn)  - [frame too short to say]
  containing entry 0x7392: reaches the site with no intervening `ret`; preceded by ret; 1 jump target(s) in between
    file 0x27CD1  runtime 0x7CD1  call      lcall 0x7392     frame 24/24 (19 insn)  - [unresolved]
```

The four rows it was grouped with have 13-, 16-, 16- and 19-instruction frames.
`unresolved` on the fifth is not weaker evidence about an index; it is not
evidence about one at all, and the cell did not say so.
[`pd-index-geometry.md` §4.1](../../ec/annotations/pd-index-geometry.md) had
already attributed that row to a phantom: the byte at `0xC9DD` is the `0x12`
operand byte of a `mov dptr,#0x0012`, not an `lcall` opcode. What was missing was
the *rule* that says so, and the measurement a rule like that needs.

## The criterion

**`MIN_FRAME_INSNS = 4`**, in `ec/tools/pd_index_geometry.py` beside the status
constants. A caller row carrying no literal load and holding fewer than four
instructions of frame is filed **`frame too short to say`** instead of
`unresolved`.

The value is worded around the *frame*, never the index. `unresolved` at least
asserts that something was looked for in something that existed;
`frame too short to say` asserts neither, and must not be readable as "the index
is unbounded" any more than `unresolved` is. It is strictly the weaker of the
two, and it is reached only where the stronger one would have been vacuous.

**The test runs after the literal branch, never before.** `caller_status()`
takes `(literals, index_regs, frame_insns)` and its order is:

```
literals present  ->  index_regs empty ? literals found; site index registers unresolved
                                  : intersection  ? literal load into an index register
                                                 : literals found, none an index register
no literals       ->  frame_insns < MIN_FRAME_INSNS ? frame too short to say
                                                 : unresolved
```

A `mov rN,#imm` in a two-instruction frame is still a load. Grading the frame
first would throw a positive finding away to buy a negative one, and a criterion
that does that is worse than none: it makes a short frame look like a result
where it is only a limitation. So the frame test decides only between the two
values a literal-free row can take.

## The distribution the threshold comes from

`ec/tools/pd_caller_frame_quality.py` enumerates every caller row the byte scan
and the two entry picks produce over `base_sites(d, WHOLE_IMAGE)`, buckets each
by `len(frame_of(d, caller_file_offset))`, and cross-tabulates against `status`,
against `frame_onto == 0`, and against whether the frame carries literals:

```console
$ python3 ec/tools/pd_caller_frame_quality.py ec/firmware/GMxMGxx_11.800
Caller frame length over every base site in the PD image, from 3176 distinct site(s) in the whole image
  Sites come from base_sites(d, WHOLE_IMAGE); rows come from caller_rows() over them.
  frame_insns is len(frame_of(d, caller_file_offset)); the '>= 4' bucket is where pd_index_geometry.MIN_FRAME_INSNS draws the line.

  frame insns    rows  onto==0   lits  unres.  short
  0              1621     1499      0       0   1621
  1               753        0      0       0    753
  2                169        0      1       0    168
  3                 51        0      0       0     51
  >=4            7947        0   3169    4778      0
  total         10541
```

Two facts fix the threshold at four, and both are in that table.

**Every committed frame the table trusts is above it.** The four real rows are
13, 16, 16 and 19 instructions; the phantom's is 1. Four sits above every frame
the committed CSV reasons from, so no row the existing prose depends on moves.

**Nothing carrying a literal is lost by drawing the line here.** Of the whole-image
rows in the buckets below four, exactly one carries a literal load — and that one
already reads `literals found; site index registers unresolved`, which names no
index register in either direction. So the line costs no positive finding and
gains no false one. Lower it to one and a single `nop` would certify that nothing
was loaded into it; raise it and real negatives start reading as unsearched.

The `lits` column is also why this is a re-filing rather than a demotion: a
frame with no room in it cannot hold a load, so the rows the criterion touches
were not carrying findings that are now being downgraded. They were carrying
nothing.

## Three corrections to what the issue assumed

**1. `converges_from()` returning `onto == 0` does not identify the empty case.**
Every row it catches has an empty `frame_of()`, but not the other way round — the
cross-tabulation puts 1,499 rows in `frame_onto == 0` against 1,621 with an empty
frame. The cause is structural: `converges_from()` steps `inline_arg_len()` and
`case_table_len()` into its walk and `frame_of()` does not, so a site behind an
inline-argument block or a jump table converges for one and not the other. This
is the strongest argument for carrying the criterion as an instruction count
rather than as a test on either existing column: a rule keyed on `frame_onto`
would silently grade the rows the two measures disagree about by the stricter of
the two, and those rows are exactly the ones with no committed example to catch
it. They are also why `frame_insns` is a column and not only a threshold.

**2. The phantom's one instruction is `nop` at `0x2C9DC`, and it is the middle
byte of a three-byte instruction.** `frame_of()` returns
`[(0x2C9DC, b'\x00')]` — `0x00` is `nop` — and those three bytes around it are

```
0x2C9DB   90 00 12    mov dptr,#0x0012
0x2C9DE   74 20       mov a,#0x20
```

so the whole one-instruction frame lies inside the previous instruction's
encoding: its single byte is that instruction's *middle* operand. This is §4.1's
conclusion, and it is stronger than "the frame is short" — there is no
instruction at that address to have been a call at all.

**3. The issue's whole-image row count does not reproduce on this tree.** It
reports 10,535 rows; `base_sites(d, WHOLE_IMAGE)` produces 10,541 here. The
one-, two- and three-instruction buckets match exactly; the empty and `≥ 4`
buckets differ. The load-bearing asymmetry does reproduce — one literal-bearing
row under four instructions, and the whole shape of the table above — so the
threshold stands on the measurement printed above and not on the issue's
arithmetic. The tool states its own site list and prints its own command; a
figure that does not reproduce exactly is not one to argue a threshold from.

## What the committed table now says

`pd-index-callers.csv` carries `frame_insns` beside `frame_onto`/`frame_over`,
and only `0x7421`/`0xC9DD` changes status. Every row, before and after:

| row | `frame_insns` | status | what that value is |
|---|---|---|---|
| `0x7421`/`0xC9DD` | 1 | `frame too short to say` | nothing was read; **not** a claim that `R3` (the index this site decodes to) is unbounded, and **not** a claim that a literal load into it does not exist |
| `0x7421`/`0x7CD1` | 19 | `unresolved` | a 19-instruction frame held no literal load into an index register; `R7` comes from XDATA `0x07C9` (§4.1) |
| `0x9DEC`/`0xB452` | 16 | `unresolved` | as above, for a frame that did hold room for one |
| `0xB5D3`/`0xB838` | 13 | `unresolved` | as above |
| `0xE9F5`/`0x66E4` | 16 | `literals found, none an index register` | three loads, into `R1`/`R2`/`R3`, for a site indexing on `R7`/`R6` |

The `literals` column is untouched. A short frame is not a reason to drop a
literal load, and a long frame with no literals is still a real negative.

## The test

Three guards, each falsified before it was believed.

**`pd_index_geometry.py --self-test`** pins the status *and* `frame_insns` for
every row against `CALLER_STATUSES`, transcribed from
[`pd-index-geometry.md` §4](../../ec/annotations/pd-index-geometry.md) rather
than read back from the CSV, asserted against both the committed cell and the
freshly computed one. The `caller_status()` block exercises the new value from
hand-built dicts, including the two that decide the branch order: a literal-free
row one instruction under the threshold, and a literal-bearing row *at* two
instructions that must still take its literal-based value.

- Replacing the frame test with the old `not literals -> unresolved` path makes
  `--self-test` exit non-zero and name three disagreements: the `0xC9DD` pin,
  the `caller_status()` case, and the CSV byte-comparison.
- Hoisting the frame test out as an **early return above** the literal test —
  `if frame_insns < MIN_FRAME_INSNS: return CALLER_SHORT_FRAME`, placed first —
  makes it exit non-zero and name the one case that exists to catch exactly
  that. Swapping the two `if` blocks instead does not: the frame test reads
  literals only in the branch literals have already emptied, so the two orders
  compute the same function and `--self-test` passes on both. The mutation that
  has to be made is the one that lets the frame test see a row that *does* carry
  literals, and that is the loss of a positive finding, not a relabelling.
  `test_pd_caller_frame_quality.py` fails on that mutation too, swept over every
  frame length below the threshold rather than at the one spot above.

**`ec/tools/test_pd_caller_frame_quality.py`** is a suite rather than more
`--self-test`, because `pd_index_geometry.py --self-test` is in no gate and in no
CI while `bash tools/run-tests.sh` finds a `test_*.py` by name. It holds what
`--self-test` cannot: that the committed `frame_insns` equals
`len(frame_of(d, file_offset))` recomputed from the image for every row, so a
hand-set column cannot satisfy the byte-comparison; that no row carrying
literals is ever filed short, swept over every frame length below the threshold
rather than spot-checked; and that the threshold separates the phantom from the
four real frames in both directions. Its expected values are **recomputed from
the bytes, not read back from the tool under test** — the frame-length case
walks the image with `disasm8051.OPCODE_LEN` itself, because `frame_of()`
returning the wrong instructions still returns the right number of them. A
hand-set committed `frame_insns`, a hand-set status, and a dropped column each
fail it.

**`pd_caller_frame_quality.py --self-test`** asserts the relations the
distribution's shape depends on — that the buckets partition the rows, that the
threshold is where the buckets split, that `caller_status()` flips at the same
place, and that `frame_onto == 0` is a one-way test of the empty frame. That last
one is asserted as a **set inclusion over rows**, `census()` returning the two
sets of row identities and the check comparing them, not as `a <= b` on the two
counts. The distinction is the whole claim: a violation moves rows *between* the
sets without necessarily moving either count, so a count comparison reads `ok`
with the relation false. Forcing one 16-instruction row to report
`frame_onto == 0` is what showed that — it leaves the counts at 1503 against
1621 with the count form still passing. The two figures stay in the printed
message, and they are `len()` of the two sets. Deliberately the self-test pins
**no counts**: a figure over the whole image belongs in this page beside the
command that prints it, and a second copy in a test assertion is a value every
later change to `caller_rows()` or the term model would have to be reflected in.
Moving `bucket_of()` off the threshold makes it fail by name, and makes the
report refuse rather than cross-tabulate rows into a bucket that does not exist.

## Readings taken, and what was left out

- **The `0x7421`/`0xC9DD` row stays.** Deleting it was on the table. It is §4.1's
  worked example of the scan catching an over-count *through the framing
  columns*, and the row is where `bank-call-audit.md` §1's measured over-count
  is visible. Deleting it deletes the demonstration. Re-statusing it keeps the
  catch visible and adds the reason it was vacuous.
- **Not a threshold keyed on `frame_onto`.** Correction 1 is the reason: the two
  framing measures disagree on a set of rows no committed example covers, and a
  rule on either column inherits that disagreement silently.
- **Not applied to rows that carry literals.** The issue's own caution, and the
  branch order above. A short frame is not grounds for a claim in *either*
  direction.
- **`--accesses` and `pd-index-accesses.csv` are untouched.** Those rows carry
  `frame_onto`/`frame_over` with the same weakness and no `frame_insns`, so the
  criterion would need its own measurement there rather than being extended by
  analogy. It is an open question, named rather than done.
- **Not done: tracing a literal through the entry.** What the callee leaves in
  the register bank is not followed, and that is the limit the positive status
  value is worded around rather than a gap this change closes.
- **No `registers.yaml` change, and none could have.** A decode of a second 8051
  image's address arithmetic is not evidence about an EC register in either
  direction — the reasoning `pd-index-geometry.md`'s preamble and `subsystems.md`
  §10 already record. The committed table's counts that *did* become false —
  `subsystems.md` §9 and `docs/findings.md` — are corrected in place, and
  `pd-callers-status-intersection.md`'s "no fifth status value" reading is
  overturned beside the original text rather than deleted.
- **The whole-image census itself is not filed here.** The measurement is
  computable from committed inputs today and the criterion needs it; the census
  as a committed artefact belongs to the wider census issue, and this page does
  not claim to have produced one.

## What this does not establish

- **No live test ran.** No EC was opened, no register was read or read back, no
  capture taken, no hardware and no Windows involved. Every number above is a
  static read of `ec/firmware/GMxMGxx_11.800` or of a committed CSV.
- **No index range and no record count is bounded.** A short frame is not a
  statement that the index is unbounded, and `pd-index-geometry.md` §5's "no
  record count" stands unchanged.
- **A frame length is not a measure of a frame's quality.** Four instructions
  that are a data table rather than code clear the threshold just as a
  four-instruction body of real code does. What the threshold says is that there
  was room to search, not that what was in it was code; §4.1's phantom is one
  instruction long *and* that instruction is not one, and only the second half of
  that is what the criterion could ever have told you.
- **Neither framing measure is proof of framing.** `frame_of()` and
  `converges_from()` both say so in their own docstrings, and the disagreement
  correction 1 measures is one instance of it. `MIN_FRAME_INSNS` inherits that
  caveat rather than settling it.
- **The distribution is over the sites this byte scan reaches**, which
  `pd-index-geometry.md` §5 records as both over- and under-counting. A
  distribution over a biased row set bounds the criterion only over that set.
- **The self-test pins values, not wording.** It asserts that the committed
  cells, the computed values and `CALLER_STATUSES` agree; it does not assert
  that `frame too short to say` is the best string for the claim.

## Reproducing it

From the repository root.

```sh
python3 ec/tools/pd_caller_frame_quality.py ec/firmware/GMxMGxx_11.800
python3 ec/tools/pd_caller_frame_quality.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --callers \
        0x7421                              # the block at the head of this page
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --callers \
        0x7421 0x9DEC 0xB5D3 0xE9F5          # pd-index-geometry.md 4's block
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --callers-csv \
        > /tmp/pd-callers.csv
cmp /tmp/pd-callers.csv ec/annotations/pd-index-callers.csv
bash tools/run-tests.sh ec/tools               # the suite this page names
```

Neither `--self-test` runs in `.github/scripts/agent-gates.sh`, and neither can
be added from an agent branch: that file lives under `.github/`, which this
pipeline's push token cannot write. Adding them is a human's change. The
`--self-test` output and the distribution run both belong in a pull request
body, which is where a reader of one looks for them.