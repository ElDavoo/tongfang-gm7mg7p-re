# A citation is a code frame, not an address (issue #453)

`ec/tools/call_graph.py` credits a named function's comment to the anonymous
callee it cites, and it found that comment by matching `0x` + 4 uppercase hex
digits. On this firmware that token is a function entry *and* an XDATA byte
constantly — 0x07D0 is `FUN_CODE_07d0` in `decompiled/index.csv` and `DBD1` in
`ec/annotations/registers.yaml` — so the top of the committed ranking was a
census of XDATA addresses wearing a call graph's clothes.

`ec/tools/citation_frames.py` is the fix: a bounded window around the mention
decides whether a code frame governs it, a data frame vetoes it, a `pd` comment
is refused the EC address space outright, and anything the window does not
settle is reported as `undecided` rather than defaulted. This file has the
census, the collision set, the corrections, and the limits. `docs/findings.md`
§24 has the summary; `ec/annotations/call-graph.md` carries the rule beside the
canonical-width rule it succeeds.

What `python3 ec/tools/call_graph.py` prints, and what this file quotes from
it: the 382/152/185/45 partition, the 99 ranked callees and 142 citing
comments, the 67 candidates naming an unranked callee, the 45 cross-program
rejections and the 3 of those reading as a code frame, and 0x1C00's 20/19/1.
**The remaining figures are not printed by that run** and are derived from the
lists behind it on this tree, so re-derive them from `citations()`'s own output
rather than looking for the number in the report: the 295 comments and 107
kept callees, the 142/138/35 in-table split, the collision table, the 158
cross-program pairs left to the frame test, the 13 weak-marker credits, and
the 5,697/1,690 unresolved-mention census. The `FILLER_BUDGET` variants are
the exception that is re-run rather than read: they come from re-running the
gate with the constant at 2 and at 3.

---

## The population

`citations()` finds **382** distinct `(callee, comment)` pairs: 295 distinct
comments naming an anonymous function row in canonical-width form, of which
one comment can name several callees and one callee can be named by several
comments. The guard partitions all 382, and the partition is the first result
worth having — before it there was no way to ask what the matcher had seen.

| verdict | pairs | |
|---|---:|---|
| kept — a code frame governs the mention | 152 | enters `cited_by` |
| rejected — a data frame, or another program's row | 185 | reported, not dropped |
| undecided — no frame inside the window | 45 | reported, not defaulted |

Those 152 kept pairs are 107 distinct callees, 99 of which the table can rank.
Before the guard the same matcher credited 315 comments to 141 callees, **so
142 of the 315 — 45% — were calls at all; 138 were rejected, 136 of them in a
data frame and 2 on program identity alone, and 35 are undecided.** The ranked
table's own top three were `common,07D0`
(27), `common,0A5A` (24) and `common,07D6` (16) — every one of them a data
byte.

The largest rejection reasons, by pair:

| reason | pairs | what matched |
|---|---:|---|
| `data-marker:xdata` | 91 | `XDATA 0x…` — the collision in its plainest form |
| `cross-program` | 45 | a `pd` comment naming a `common`/`bank` row |
| `data-marker:dptr` | 24 | `DPTR,#0x…` and `points DPTR at 0x…` |
| `data-marker:writes` / `:bytes` / `:byte` / `data-noun:sites` | 9, 8, 8, 8 | store verbs, and "the 0x07D0 sites" |
| `data-marker:copies` | 5 | `copies 0x0A5A into 0x0096` |

A pair can carry two reasons, which is why the column does not sum to 185.

## The collision set

Every callee that lost at least three citations to the guard, with what the
listings and comments support. "Lost" is `rejected + undecided` per
`citations()` callee key, and **17 callees clear that bar on this tree — the
16 rows below are all of them**, one row carrying the 0x08CD/0x08CF pair.
Re-derivable with:

    python3 -c "import sys,collections; sys.path.insert(0,'ec/tools'); import call_graph as cg; k,r,u=cg.citations(cg.load_index()); print(collections.Counter(c.callee for c in r+u).most_common(20))"

`before` is the pre-guard `cited_by` the ranking table carried before this
change, so a reader auditing the correction can diff the two against each
other; a callee with **no row in that table at all**, because no transfer
reaches it, reads `—` rather than a count.

| callee | before | after | rejected | undecided | what the citing comments read |
|---|---:|---:|---:|---:|---|
| `common,07D0` | 27 | **2** | 25 | 0 | all 25 from `pd` comments naming the PD image's own byte; the 2 kept are the two real `lcall`s |
| `common,0A5A` | 24 | **0** | 24 | 0 | every one `XDATA 0x0A5A` or the top byte of `XDATA 0x0A56-0x0A5A` |
| `common,07D6` | 16 | **1** | 15 | 0 | all 15 from `pd` comments naming the other program's bytes; 1 `common,012F` calls it |
| `common,0806` | 7 | **0** | 7 | 0 | `clears 0x0806`, `reloads 0x0806` |
| `common,1606` | 6 | **0** | 6 | 0 | every one `XDATA 0x1606` — and **no `registers.yaml` row at all** |
| `common,08CE` | 5 | **0** | 5 | 0 | `MOV DPTR,#0x08CE`, `writes … to XDATA 0x08CE` |
| `common,08CD`, `common,08CF` | 4 each | **0** | 4 each | 0 | halves of a 16-bit XDATA pair |
| `pd,06EA` | 8 | **1** | 4 | 3 | a 16-bit counter's halves, `0x06EA/0x06EB`; the 1 kept is `pd,88BE`'s "calling 0x05A6 and 0x06EA" |
| `common,1C00` | — | **0** | 19 | 1 | 19 in a data frame ("bit 0 set in 0x1C00", "0xFF to XDATA 0x1C00") and 1 unsettled — and it has no row in the table at all; see the limits |
| `common,1C14` | — | **0** | 3 | 0 | the 0x1C12-0x1C14 trio named as a seeded XDATA group by `bank1,9CE8` and `bank1,9D53`, and `bank0,D2EF`'s `stores the accumulator to 0x1C14` — and, like 0x1C00, **no row in the table at all** |
| `common,086B` | 4 | **0** | 2 | 2 | a six-byte copy into `0x0866-0x086B` and a compare of `0x046A/0x046B/0x046E/0x046F` against `0x086B/0x086C/0x086D/0x086E`; the 2 unsettled are `0x086B to 0x1C3A` and the 0x086B result byte |
| `common,1504` | 4 | **0** | 3 | 1 | the `0x1500`/`0x1504` poll and dispatch, reading and writing the status byte (`0x66 does the same with XDATA 0x1500 and 0x1504`); 1 unsettled, from a `registers.yaml` caveat naming `0x1500-0x1504` |
| `common,1510` | 5 | **1** | 3 | 1 | the 1 kept is `bank0,EBD5`'s `calls 0x1510`; the 3 lost are `XDATA 0x1510` and `0x1514` reads and a `writes 0 to XDATA 0x1510`, and the 1 unsettled is the `0x1510-0x1514` caveat |
| `common,1602` | — | **0** | 4 | 0 | four `Read-modify-write of the byte at XDATA 0x1602`, two setting a bit and two clearing it — and, like 0x1C00, **no row in the table at all** |
| `common,0862` | 3 | **0** | 3 | 0 | three staging comments, each `copies 0x0862 to 0x1C02` / `0x1C13` / `0x1C37` |
| `common,09E9` | 3 | **0** | 3 | 0 | `copies 0x09E9 into 0x0788`, `derives 0x09E9 from 0x0744`, and `writes 0x00 to XDATA 0x09E9` |

`common,1510` is the row a reader auditing the ranking is most likely to go
looking for, because **its five pre-guard citations were visible in the table
this change corrects** — `bank0:D5D4 bank0:D757 bank0:E256 bank0:EBD5
bank1:8418` — and one of the five survives the guard. `bank0,EBD5` reads
"calls 0x1510", which is a real claim about a real transfer, so it is credited
rather than counted as a collision; the other four are the other half of this
section's subject, comments that name 0x1510 and 0x1514 as a status pair in
XDATA rather than a function to call. A callee can be a collision **and** keep
a citation, and the `before`/`after` pair is what shows which is which.

### 0x1606 is the argument against a `registers.yaml` lookup

The obvious guard is "reject an address that is a register". `common,1606` has
six citations, every one of them `XDATA 0x1606`, and **`registers.yaml` has no
row for 0x1606 at all** — so that guard credits all six of the worst cases. The
discriminator has to be the prose and the program, not the register census,
and this is the address that forces it.

## Two corrections

**0x07D0 is 2 citations, not 0 and not 27.** Issue #453 says "no comment citing
0x07D0 is citing that code function". That is too strong, and the wrong version
is left visible here rather than quietly fixed. `common,018C` reads "The other
arm calls 0x07D0"; `common,029B` reads "The other arm writes 0x11 to 0x1700,
calls 0x07D0"; and both listings carry the transfer —
`ec/decompiled/common/018C.asm:40` and `029B.asm:50` are `lcall 0x07d0`. So
`cited_by` is 2, which is also its `inbound=2`. **The two framings agreeing is
the check**: a guard that zeroed all 27 would have produced a tidier number and
a wrong one, and only the agreement catches it. The fixture pins the same
agreement on its own 0x07D0 row.

**A purely syntactic veto would have been a larger corruption than the one
being fixed.** Issue #453 proposes rejecting "to/from 0x…". Seven `bank1`
comments read "then calls to 0x110A, 0x158E, 0x0F75, 0x1594 and 0x00CF" — one
code enumeration with a data marker in it — and a sentence-wide data veto
rejects every address in every one of those comments. Three of the five are
still anonymous, so the guard would have thrown away **21 real citations** to
save 27 fake ones. This is why the rule is a **bounded window walked left from
the mention**, with the verb nearest the mention deciding, rather than a pattern
matched against the sentence.

## The second signal: program identity

**45 of the 71 `pd`-scoped candidate pairs name a `common` or `bank` row**, and
25 of them name `common,07D0`. They cannot: the 256 KiB dump holds two 8051
programs, the EC firmware and, at file 0x20000, the `ITE8850-PD` image with its
own vectors and its own XDATA map. `ec/annotations/registers.yaml` says so in
its own `static-scan` caveat ("Refs in the PD image are not refs to an EC
register"), and `build_ec_decompile.py:1421` refuses an EC XDATA name on a `pd`
row for the same reason. `Index.resolve` hands a `pd` comment the `common` row
only because the PD image has no row of its own at that address — the collision
the address space creates, not one the matcher invents.

This is decidable from **program identity**, not prose, which is the whole
reason it is a separate check and not a bigger lexicon. **Three of the 45 read
as a code frame**, so the program check is doing work no lexical rule reaches;
the tool counts them and prints the count beside the gate's, so that number
stays checkable. (A neighbouring figure is four: that is how many of the 45
carry no data reason at all — `common,1042`←`pd,1041`, `common,10F0`←`pd,10E8`,
`common,07D0`←`pd,ACE1`, `common,07D6`←`pd,B2CD` — which is a different
question, and the one this paragraph was once miscounted from.)

The complementary case is deliberately *not* decided. A `bank0`/`bank1` comment
citing a `common` row is legitimate — a common-area function is exported once
and reached from both bank programs, which the `Index` docstring in
`call_graph.py` already encodes — so 158 cross-program pairs fall to the frame
test alone.

## What the undecided 45 are

They are pairs where no code verb or data marker falls inside the window: the
governing word is two or more ordinary nouns away, or the mention stands alone
in its clause. They are the conservative cost of `FILLER_BUDGET = 1`, and they
are printed rather than credited, so a human reading the sentence can settle
them. Three shapes, all real:

- **Lists and enumerations introduced without a verb.** `bank1,0xC924` reads
  "Cases 0-6 land on 0xC931, 0xC979, 0xC9BE, 0xCA1D, 0xCA3E, 0xCAB8 and
  0xCB08" — six genuine code targets, and `land` is not in the code lexicon.
  Same for `bank0,0xE893`'s "byte-identical to the exits at 0xE7B8 and
  0xE7C7".
- **A real citation across an aside.** `common,0070` reads "calls 0x110A -- the
  tail half of bl51_bank_select_0, so the reset path selects bank 0 -- followed
  by 0x158E, 0x0F75 and 0x1594", and **`ec/decompiled/common/0070.asm:12-14`
  does carry `lcall 0x158e`, `lcall 0x0f75` and `lcall 0x1594`**. So these
  three are true positives the guard reports as undecided. That is the
  population's honest reading: not wrong, not settled, and the listing is how
  to settle it.
- **A mention with no verb anywhere near it.** `common,029B`'s "the shared
  helper here is 0x5A43" in the fixture, which is the shape the third self-test
  case pins.

The window is one ordinary word wide, and that is measured rather than
guessed. Widening it to 2 credits **no new citation** and converts 7 unsettled
pairs into rejections, **6 of which name code addresses**: "then 0x1E1A twice
with", "the same bytes as ACALLs to 0xD673, 0xD698", "returns zero, and it is
byte-identical to the exits at 0xE7B8 and 0xE7C7", "it ends in an sjmp to
0x9B3C", "waits on a 0x07F0 poll". In each the walk reaches a data word that
describes something *other* than the address — a return value, an instruction
encoding, an earlier clause's XDATA. The first new credits arrive at 3, two
addresses in one decompiler-target list, and by then **9 of the 13 new
rejections name code addresses**. **A wrong rejection is worse than an
unsettled pair**: one becomes a fact in a census, the other stays a line in a
report asking for a human to read the sentence.

## What this does not establish

- **The top of the table is now right about the addresses and still wrong about
  who calls them.** Ranks 1–3 are `common,0F75`, `common,158E` and
  `common,1594`, 7 citations each, **all seven from the same seven `bank1`
  `0xFF`-fill comments** whose text says the decompiled body "is not supported
  by these instructions, and that code is not present at this address". Each
  citation does read as a call to a code address, which is what the guard
  tests; what the comment is attached to is fill, not the reset path those
  calls live in. That is a second, separate defect — the comment refutes the
  decompile and still names its callees — and it is the obvious next thing to
  fix. `ec/annotations/call-graph.md` §"Two known distortions" carries it.
- **A frame test is a bag of words.** It is lexical, bounded, and it will be
  wrong on prose it has not seen. Every one of the 152 kept pairs was read,
  because a wrong citation enters a work list and a settled-looking one does
  not announce itself. **14 of them rest on a weak marker** rather than on
  `calls`/`lcall`/`ljmp` — `callee` (2), `tail-jumping` (3), `entry` (2),
  `jumping` (2), `routine` (2), `caller`, `reaches`, `routines` (1 each) — and
  all 14 name code addresses: "the callee pairs 0x4AB8/0x4A69", "tail-jumping
  to 0xA873, 0xA88D, 0xA8A7, 0xA8C5, 0xA8DA, 0xA8DF and 0xA8E4", "the next
  entry, 0xE6F4", "The sibling of the routine at 0x9CE8", "The caller at
  0x9CE8". That is a census of the committed
  tree, not a claim about the next comment written.
- **0x1C00 is not ranked, and that is not absence.** 20 comments name it, 19
  in a data frame and 1 unsettled, and it has no row in
  `call-graph-callees.csv` because no transfer reaches it — so it was never in
  the ranking to be wrong in. **67 candidate pairs name a callee the table
  carries no row for**, and the tool prints that number beside the gate's.
- **Canonical-width mentions that resolve to no index row are still not
  reported.** 5,697 of them over 1,690 distinct addresses (1,892 distinct
  `(scope, addr)` pairs — a `pd` mention and a `common` mention of the same
  address are counted once each), mostly register bytes (0x0490 alone, 92).
  That is outside this guard's population and a separate question; "not found
  by this method" is the whole of what the 5,697 means.
- **No register `status:` changed, no listing was re-read, and no live test
  ran.** Nothing here is a claim about what the EC does. `registers.yaml` and
  `ec/ghidra/xdata-symbols.csv` are untouched, and no address was read back
  from hardware — this is a text measurement over committed inputs.

## Follow-ups this opens

1. **The fill-comment artifact** (above): 21 of the top three's citations are
   the same seven comments, and no lexical frame distinguishes "names a callee"
   from "names a callee in a body it rejects".
2. **The 45 undecided pairs** want a human reading each sentence, the way
   `common/0070.asm:12-14` settled three of them. A wider code lexicon would
   settle more and would need its own evidence for each word it adds. **Done
   in issue #526**: all 45 carry a recorded verdict in
   `docs/findings/citation-undecided-verdicts.md`, `report()` now renders the
   population, and `FILLER_BUDGET` is unchanged at 1 — 44 of the 45 are
   readings that re-confirm this section's measurement rather than move it.
3. **The gate arm is wired; a template re-copy of it is the thing to watch.**
   `call_graph.py --check` and `--self-test` both run per commit from
   `check_ghidra_tooling` — the tool list at `.github/scripts/agent-gates.sh:125`
   and the `case` arm at `:187-188`. An earlier draft of this file claimed the
   check was unwired and made wiring it this follow-up; that was wrong, and
   `ec/annotations/call-graph.md` retracts it under "Correction (2026-09-24,
   issue #454)". What that correction leaves as the live follow-up is the
   re-copy risk it records: re-copying `agent-gates.sh` from the `agent-pipeline`
   template drops the tool and its arm, and `docs/agent-pipeline.md` item 6
   carries both for re-applying. This change touches nothing under `.github/`
   because the pipeline's push token has no `workflow` scope, so it could not
   wire or re-wire that arm either way.
4. **`ec/tools/test_citation_frames.py` has no gate arm.** Its 25 unit tests are
   collected by `tools/run-tests.sh`, which discovers every `test_*.py`, but
   nothing per-commit runs that runner: `ci.yml:45` runs `agent-gates.sh`, which
   has no `unittest` arm, and the only reference to `run-tests.sh` in
   `.github/workflows/` is a conflict-resolving agent's prompt. The gated
   `call_graph.py --self-test` is what covers the classifier end to end, on the
   fixture — a regression it does not reach would be caught here first.
