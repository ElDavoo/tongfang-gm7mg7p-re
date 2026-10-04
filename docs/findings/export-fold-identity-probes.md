# Two more mechanical criteria for the fold, and neither separates a re-export from a fragment

`ec/tools/export_ownership.py` folds one decompiled `.c` into another when the
smaller body's statements are 90% of the way into the larger one, and the fold
is not a presentation choice: a non-owner's references are counted through its
owner, so folding a routine that is *not* an export of the owner deletes it
from the census. `ec/annotations/xdata-export-ownership-verdicts.csv` records
which fold that is, per row, and `export_ownership_verdicts.py`'s own docstring
already records that the obvious mechanical criteria do not decide it —
byte-range containment and literal-slice both fail.

This asks the question one level up: not whether criterion X decides the
verdicts, but whether the **two criteria nobody has tried** do. Both come from
committed inputs, and both were tested against the population where the answer
is already known rather than argued.

**The answer is no, and why is the finding rather than a null result.**
That is stated narrowly and deliberately below: these two probes do not
separate the two recorded verdicts on the rows where both exist. It is not a
claim that no mechanical criterion could — `export_ownership_verdicts.py` names
two others that fail on the same rows, and a fourth is not ruled out. What it
does establish is that the boundary is still not mechanically settleable from
what this repository has committed, so §8 item 7's rebuild remains the only
route, and that conclusion now rests on four failed criteria rather than two.

The tool is `ec/tools/export_fold_identity.py`, the population is derived from
the committed map, and every figure here is what it prints:

```
python3 ec/tools/export_fold_identity.py
python3 ec/tools/export_fold_identity.py --csv
```

## The two probes, and why each is the obvious candidate

**A — does a transfer name the member's own address?** A routine the exporter
re-cut out of a longer routine is a routine something transfers to, so if
reachability tracks the cut, a fragment should be less reachable than a
re-export of a different routine. Asked through
`entry_reachability.sites_naming()`, **one program at a time**: a 16-bit
`lcall` target does not name a bank, so a bank-1 site must never answer a
bank-0 question. That is the mistake `entry_reachability.py` exists to make
impossible, and it is why this probe is a call into that tool rather than a
second implementation of "every transfer in this image".

**B — is the member's address an instruction the exporter committed?** If the
member sits where the exporter happened to cut, rather than at a routine entry,
that cut is a boundary artefact and the member's address would not be an
instruction start at all. Read from the committed `.asm` listings rather than
from a fresh decode, because a criterion needing a disassembly this repository
does not commit would not be answerable from what it has.

Both fire on the member's address *being a place the toolchain pointed at*,
which is also exactly what the fragment case is. That is the whole of why they
fail, and it is visible in the results below rather than argued in advance.

## The result

Cross-tabulated by `export_fold_identity.py`, over the rows
`export_ownership_verdicts.py` puts on trial:

| verdict | rows | A fires | B fires |
|---|---:|---:|---:|
| `re-export` | 15 | 15 | 15 |
| `fragment` | 10 | 10 | 10 |

Neither separates. Every fragment is exactly as reachable and exactly as
instruction-aligned as every re-export, and the reason is structural rather than
accidental: **whatever put the member's address in the tree, the address is a
routine somebody reaches.** A fragment is a routine in its own right that the
owner's text contains without being an export of it — `common/322C.c` is
recorded because `common/30FB.c` *calls* it, and `bank0/F08B.c` because a
one-instruction `bank0/F078.asm` decompiles into its body. Both are ordinary
code at ordinary entry addresses, so both probes answer `yes`, and a criterion
keyed on the address cannot tell them from a re-export. The distinction these
probes would need is the one between the exporter's cut and a routine boundary
— which is the defect itself, and is not in what they read.

Note also that B fires on 145 of the 146 non-owner rows, so on this tree it is
close to a constant rather than a criterion. The one row where it does not fire
is `bank0/F0A1.c`, whose committed listing is `(no-instructions)` — a seed the
call-target byte scan cut at an address no listing covers. **That is reported,
not resolved:** it is the shape a discriminating criterion would take, and it is
a single row with no recorded verdict, so nothing here says which kind of fold
it is. It is the most promising lead on this page and the smallest one.

**The obvious objection to probe A is answered here rather than left standing.**
Some of these rows exist *because* a transfer names them — `index.csv`'s
`seed_basis` is `call-target` for some, `annotation` for others — so for a
call-target-seeded row "somebody transfers to it" is close to the reason the
row is in the tree at all, and a fire there could be circular rather than
evidence. It is not what the result rests on: **restricting to the
annotation-seeded rows, where the seed is a person naming a routine rather than
a call site naming an address, A still fires on every row of both verdicts.**
Both classes are present in that subset, so the negative result is not an
artefact of how the rows were seeded. The `seed_basis` column is in
`index.csv`; this is a join of the two committed CSVs and adds no measurement.

## Coverage, and what "not measured" means here

The ledger's population is narrow **by construction** — an owner at least twice
the member's size, and containment exactly `1.00` — because those are the rows
a relative check has to spare the 42-file class to get right. So the gap is
large, and it is stated as a gap rather than as a margin:

- every non-owner row of the committed map: **146**
- of those, carrying a recorded verdict: **25**
- carrying none: **121**, across **44** owners

That last group is the coverage statement, and it is stated as *unmeasured*
rather than as agreement: a probe firing on a fold nobody has read says nothing
about that fold. `export_fold_identity.py` prints `unmeasured` for those rows
and keeps them out of the cross-tab entirely, and `test_export_fold_identity.py`
holds both — the word, and its absence from the ledger's closed vocabulary, so a
row carrying it can never read as decided.

**The 121 include every non-owner row of the 42-file `bank1/8001.c` class**,
which the ledger's population excludes by its own definition. So the one class
this whole body of work is about has no verdict on any of its folded rows, and
the two probes would not settle them if it did. They are named here as a
worklist, not a target: by that ledger's own account a verdict is a person
reading two `.c` files and their `.asm`, and doing 121 of them unattended would
put unsourced readings into a committed CSV.

## What this settles, and what it does not

It confirms §8 item 7's gate on its own evidence rather than by appeal to the
earlier two criteria: the function boundary cannot be recovered from the
committed decompile, so `--mode rebuild-project` is the only route, and the
recipe and prediction for that run stay where §8 item 7 puts them
(`docs/findings/counter-sweep-entry-set.md` §7). This branch does not attempt
the rebuild and does not touch `--export-ownership`'s default.

Three things it is **not**, stated so a later reader does not have to infer
them:

- **Not "no mechanical criterion can."** Four criteria have now failed on these
  rows; that is evidence about four, not a theorem about the rest.
- **Not a claim about the bytes.** Every input is the committed firmware image
  and the committed listings. Nothing here was observed on hardware, and no
  register was read back.
- **Not coverage.** The result is a negative one over 25 rows. The other 121
  non-owner rows are unmeasured, and the cross-tab's silence about them is not
  a clearance.

`export_fold_identity.py` is not in `.github/scripts/agent-gates.sh`, and cannot
be from an agent branch — that script is a template copy
(`docs/agent-pipeline.md`). It reads only the committed map, ledger, image and
listings, with no Ghidra, no network and no assembler, so it is cheap-tier work
whenever a human wires it in. Neither is `export_ownership.py`, so the wiring
is a human's edit for both.

## The suite

`ec/tools/test_export_fold_identity.py` asserts relations rather than figures,
so it stays true as the map moves. The case that matters is the negative one:
**the probes do not separate the recorded verdicts**, asserted directly against
the committed tree, so the day a future probe set *does* discriminate the suite
goes red and says the boundary became mechanically settleable. A control builds
the discriminating shape and shows the check recognises it — otherwise a
`separates()` that always answered `no` would pass while measuring nothing — and
the rest hold the three edges a reader could over-read: a program the
reachability scan does not audit reads `not-audited` rather than `no`, an
unmeasured row stays out of the counts, and the population is derived from the
committed map rather than typed.

The one case that reads the committed tree asserts that every recorded verdict
names a row the map contains — a relation — and not how many rows there are,
because a census is a value every merge has to edit.
