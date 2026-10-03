# Every bucket-A and bucket-C scan site against the committed listings: `anchored` predicts a real opcode across bucket A, and fails to in bucket C and in the fill band (issue #594)

`ec/annotations/bank-call-audit.md` §1 carries an `anchored` column beside its
byte-scan upper bound, and concedes in three lines that for one band the column
means less than it looks: there, "a site that clears the anchored bar is no more
an opcode than one that does not". The concession is scoped to that band, and
nothing had measured the rest of the file to say whether it should stay scoped.
This measures it. **Across bucket A an anchored site is at a real opcode 58.6%
of the time, against 1.0% for an unanchored one — a 57x lift, and a clear
majority rather than a certainty; in bucket C not one anchored site is at a
boundary, and inside bucket A the band is a second place it inverts.** So §1's
caveat stays band-scoped and is now stated with the reason beside it rather than
left implied — but not because the band is the only place the relationship
fails. It is not, and §1 never claimed it was: §1's three lines are about the
band, and what this adds is a cell, bucket C, that the caveat does not name.

The tool is [`census_call_site_framing.py`](../../ec/tools/census_call_site_framing.py).
It reads committed files only and writes none. **Nothing here is a behavioural
claim.** No register `status:` changed, no listing was re-read, no Ghidra export
ran, and nothing was observed on hardware.

## The verdicts

`census_ff_fill.py`'s `listing_coverage()` and `classify_site()` are
**imported, not reimplemented** — one implementation, so this census and the
fill census cannot come to disagree about what a verdict means or which
listings are in scope. Every row of `ec/annotations/bank-call-targets.csv` in
buckets A and C is classified against every committed `.asm`, and there are
three answers and no fourth:

| verdict | rows | share |
|---|---:|---:|
| at an instruction boundary | **1,354** | 49.5% |
| inside another instruction | **397** | 14.5% |
| no committed listing covers the site | **986** | 36.0% |

Bucket B is not read, and **nothing here claims it**: no issue is named as owning
those rows, because a claim about the tracker is one a write-up cannot keep true.
Take the scope as unowned, not covered. It stands on the merge-conflict surface
`CLAUDE.md` warns about instead: two branches writing the same rows collide at
the same hunk. Bucket B is also a different question, which
`bank-call-audit.md` §4 gives the `entry`/`erased`/`other` treatment. The
schemas compose — both key on `(region, runtime, bucket)` — so the same
classification can be run over B and joined on the site by whichever branch
picks it up.

By region and bucket, so no cell is read as the whole:

| region | bucket | boundary | inside | no listing | rows |
|---|---|---:|---:|---:|---:|
| `common` | A | 978 | 84 | 721 | 1,783 |
| `common` | C | 1 | 78 | 61 | 140 |
| `bank0` | A | 184 | 80 | 136 | 400 |
| `bank1` | A | 191 | 155 | 68 | 414 |

The `common`-A and bank-A row counts are `audit_call_targets.py`'s own §1
figures, unchanged; this census splits them rather than restating them.

## `anchored` against the verdict, which is the finding

| | at a boundary | inside another | no listing | rows |
|---|---:|---:|---:|---:|
| anchored (`frame_onto > 0`) | **1,350** | 137 | 901 | 2,388 |
| not anchored | **4** | 260 | 85 | 349 |

Those two rows pool two populations, and pooled they are the one number here
that does not survive being split. **Read per bucket, there is no single
relationship at all**:

| bucket | anchored at a boundary | not anchored at a boundary | lift |
|---|---:|---:|---:|
| A | 1,350 / 2,305 (58.6%) | 3 / 292 (1.0%) | **57x** |
| C | **0 / 83 (0.0%)** | 1 / 57 (1.8%) | **0x** |

**The lift is bucket A's alone.** Not one anchored bucket-C site this census
can see sits at a boundary, while one unanchored C site does — the same
inversion the band shows, in a cell of 140 rows rather than 28, and disjoint
from it, because every one of the 28 band rows is bucket A. So `anchored`
predicts a real opcode **across bucket A** and fails to in **bucket C** and in
the **band**: two exceptions, only one of which is the band §1 names. An
aggregate over A and C describes neither bucket, which is why the report prints
this cross-tab per bucket and states no single lift for the population.

The two failures fail differently, which the aggregate also hides: an anchored
site that is not at a boundary is usually in no listing at all, while an
unanchored one is usually sitting inside an instruction the scan read a pattern
out of. That is the relationship `bank-call-audit.md` §1's caveat is about,
which is why it stays band-scoped and gains a reason rather than being
generalized away.

`anchored` is not a call and not an entry point. It means at least one of 24
preceding byte anchors decodes exactly onto the site: a *candidate decoded entry
point*, §1's own words. This measurement says the candidacy tracks being a real
opcode across bucket A, which is a stronger and narrower claim than "the scan is
right" and much weaker than "the call is real". In bucket C it tracks nothing
this census can see.

## The boundary set is a work list, and it is smaller than 1,354

The boundary rows are the useful half — the sites where the scan's read is a
real opcode — and behind them:

- **498 distinct (target program, target) pairs.** One naming pass is 498
  targets, not 1,354 sites.
- **1,049 of the 1,353 resolvable rows name a target with an `index.csv` row**;
  633 name one with a `ghidra-functions.csv` row, and 95 of the 498 distinct
  targets carry one. Those two columns are **labels, never filters**,
  `data_regions.py`'s discipline: a target with no export is still classified,
  and an export is not a confirmation that the scan read the call correctly.
- **99 boundary rows sit at a listing's own entry address.** That is a fact
  about the **site** — the covering listing starts at the site's own address,
  so the scan matched at a listing's first byte — and it is not a second,
  smaller answer to the target question. The target-side figures are the two
  counts in the bullet above, and neither set is a subset of the other.
  A boundary read makes the **site** an opcode and says nothing about the
  **target**; the two are separate questions, so this is not multiplied into a
  single "clears both" figure, which would be a count of neither.
- **One row's target program is unresolvable** and is reported as such rather
  than guessed at: `common,0x0504` is a bucket-C `lcall` to `0x9000`, and
  nothing in the byte says which bank is mapped. That is the case
  `trace_xdata_refs.offset_for_runtime()` returns `None` for and §5 declines to
  resolve, and it is left declined here.

`--rows` writes the whole set as CSV — every row, nothing dropped, with the
covering instruction and all three label columns — to stdout, or to wherever
`--out` points. **No table is committed**, and the reason is the next sentence
rather than a rule the tool enforces: the verdict is a function of the committed
listings, so a committed table would go stale at the next Ghidra export with no
gate here to catch it.

## Where the misreads cluster

The 397 rows inside another instruction are the scan's false positives, and
they are not spread evenly:

| the site sits inside | rows |
|---|---:|
| `mov` | 122 |
| `jz` | 59 |
| `sjmp` | 42 |
| `cjne` | 35 |
| `ljmp` | 20 |
| `jnc` | 15 |

**53 of the 397 sit inside a `mov DPTR,#imm16` immediate** — 27 read as
`lcall`, 26 as `ljmp`, and they land on both bytes of that immediate rather than
only one (24 at the instruction's second byte, 29 at its third). **This census
re-reports those addresses so
[#508](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/508) can reconcile
against the population rather than recount it**; #508's own count is not
re-derived, re-litigated, or restated here, and this figure is not offered in
its place. The rows are reachable with `--rows` for it to read.

The three worked examples, read byte by byte, in
[`ff-fill-census.md`](ff-fill-census.md)'s style:

- **`common`, site `0x7159`, `lcall` → `0x7401`, inside another instruction.**
  `common/7151.asm` is `7158  70 12  jnz 0x716c` then `715A  74 01  mov A,
  #0x1`. The `12` at `0x7159` is that branch's rel8 and the `74 01` at `0x715A`
  is the next instruction's opcode and immediate. Read as an `lcall` they spell
  `12 74 01` → `0x7401`, which is unprogrammed. This is `ff-fill-census.md`'s
  original case, reproduced here as a check that the generalization did not
  change it.
- **`bank1`, site `0xD756`, `ljmp` → `0x7E01`, inside another instruction.**
  `bank1/D6EE.asm` is `D755  50 02  jnc 0xd759` then `D757  7e 01  mov R6,
  #0x1`. Same shape: `02` is a rel8, `7e 01` a `mov` immediate.
- **`bank0`, site `0xE716`, `lcall` → `0x7F01`, inside another instruction.**
  `bank0/E6F4.asm` is `E715  7b 12  mov R3, #0x12` then `E717  7f 01  mov R7,
  #0x1`.
- **`bank1`, site `0x809C`, `lcall` → `0x198A`, at an instruction boundary.**
  The contrasting case, and the shape the boundary half actually has:
  `bank1/8096.asm` is `8096  12 19 84  lcall 0x1984`, then `8099  ef  mov A,
  R7`, then `809C  12 19 8a  lcall 0x198a`. Here `0x809C` genuinely starts the
  third instruction — the scan matched a real `lcall` opcode. Note what this
  does **not** show: that `0x198A` is a function, or that the call reaches it.
  The row is a candidate for a naming pass, and the `--rows` target columns say
  which candidates already have a name.

## The uncovered rows, and the scoping that keeps them honest

The 986 `no committed listing covers the site` rows are **not found by this
method**, never *there is no code here*: the caller may be code Ghidra never
exported, and this census cannot tell that from an address nothing was decoded
at. The verdict is also **scoped to the caller's own program**, and the report
prints which other programs cover the same runtime address, because the common
area and the bank images are separate address spaces that share those numbers:

| caller | bucket | a bank overlay also covers it | only a non-bank program | no program at all |
|---|---|---:|---:|---:|
| `common` | A | 161 | 30 | 530 |
| `common` | C | 10 | 4 | 47 |
| `bank0` | A | 102 | 12 | 22 |
| `bank1` | A | 57 | 4 | 7 |

The `common`-A `bank overlay` cell is the one worth a follow-up: those are
addresses a bank program *does* cover and the common program does not — code
Ghidra exported into the bank images and not into `common`, which is a
`citation_gap_scan.py`-shaped question and is named as follow-up rather than
answered here. The larger `no program at all` cell beside it is the ordinary
case and says less: nothing in this tree decoded an address in any program.

## The control: the band reproduces exactly

The population [`ff-fill-census.md`](ff-fill-census.md) measured first is a
control on this generalization, and it comes out of the same two imported
functions at the same **0 / 22 / 6** — not one of the 28 at a boundary, 22
inside another instruction, 6 under no listing. The self-test pins that split by
address, the way `census_ff_fill.py` pins its own population, so the
generalization is shown not to have changed the one population already measured.

That agreement is also why §1's caveat is not restated here. The 28 are a
sample of the A/C population and this census says what the rest of it looks
like; §1's three lines about the band are **not wrong** and are not corrected in
place, because nothing here contradicts them. All 28 band rows are bucket A, so
the band is an exception *inside* the bucket where the measure holds rather than
a separate phenomenon beside it. Bucket C is the second exception, and the one
§1's caveat does not name — §1 never claimed the band was the only one, so this
is an addition to what §1 covers and not a correction of it.

## Composition, reported and not resolved

**With [`bucket-c-codemap.md`](bucket-c-codemap.md):** the two compose and
disagree in the way that file already flagged. All **16** bucket-C sites its
flow walk reached are `no listing covers it` against the committed listings,
and the single boundary-classified bucket-C row (`common,0x0504`, the
`lcall 0x9000`) is `not-reached` / `mid-instruction` to the walk. **This census
does not resolve it**, and the disagreement is not evidence that either tool is
wrong: a flow walk cannot distinguish code from a table it wandered into, and a
listing boundary set cannot see a routine Ghidra never exported. They answer
different questions about the same 140 rows.

**With #508:** reconciled rather than recounted, above.

**Not re-derived here, named as different populations:** #461 and #543 (targets
nothing reaches, and undecided rows), #542 and #527 (`Index.resolve`'s row
fallback, and comment mentions resolving to no index row). None of those
classifies the direct-call rows, and none should wait for this.

## Limits

- **A boundary read is about the site, not the call.** It establishes that the
  bytes at the site's address are a real opcode in a committed listing. It does
  not establish that the scan's `target` is a function, that anything reaches
  it, or that the transfer is what the scan took it for. The `--rows` target
  columns are labels for a naming pass; the boundary rows at a listing's own
  entry address are a fact about where the scan matched, not a count of good
  targets, and neither figure filters the other.
- **`anchored` predicts a real opcode in bucket A, not across A and C.** Not
  one anchored bucket-C site is at a boundary, and the aggregate lift over both
  buckets is A's. Read the per-bucket cross-tab, never the pooled one.
- **"No committed listing covers the site" is not "there is no code here."** The
  caller may be code Ghidra never exported. Same rule as everywhere else in
  this tree.
- **The verdict is scoped to the caller's own program**, and the cross-program
  column exists so the scoping is visible rather than assumed.
- **The verdicts move when the listings do.** They are a function of the
  committed `.asm` set, so a Ghidra export will move them. That is the reason no
  table is committed, and it is why the self-test asserts the *shape* — the
  partition, the selection, the verdict as a function of `(region, runtime)` —
  rather than the totals, which are printed and quoted here instead.
- **The census totals are printed, not asserted.** A test that holds 1,354 is a
  value every merge that exports a listing has to edit, which is the mistake
  `CLAUDE.md` records three times over. The self-test pins the band, five worked
  examples by transcription, three structural invariants and three refusals.
- **Nothing here is behavioural.** No register was read, no capture opened, no
  EC powered, and no `status:` in `ec/annotations/registers.yaml` moves.

## Re-deriving

One command from the repository root prints every figure in this file. The
`--self-test` is the check.

```console
$ python3 ec/tools/census_call_site_framing.py --self-test
$ python3 ec/tools/census_call_site_framing.py
$ python3 ec/tools/census_call_site_framing.py --rows --rows-for common
```

This tool is deliberately **not** wired into `.github/scripts/agent-gates.sh`:
that file is a template copy under `.github/`, and the agent pipeline's token
has no `workflow` scope, so a branch touching it fails at the very end. The
`--self-test` is the check, run by hand and quoted here;
`census_ff_fill.py` made the same choice for the same reason and
`ff-fill-census.md` records it. A human can add the `case` arm upstream in
[`ElDavoo/agent-pipeline`](https://github.com/ElDavoo/agent-pipeline) if it
should be gated.
