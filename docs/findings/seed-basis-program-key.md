# The seed-basis map is keyed on `(program, addr)`, and 55 addresses were never the right population (issue #393)

`docs/findings.md` §19 named this defect and declined to fix it: *"The fix is to
key `readBasis()` on `(program, addr)`, and it is not made here because it would
restate the basis column across the whole index and wants its own
verification."* This is that issue, and the verification is below.

**The defect is real and it is in two files, not one.** `readBasis()` read the
three columns of the seed-basis CSV and stored `m.put(f[1]…)` — the address,
dropping `f[0]`, the program — and the lookup was `basis.get(addrHex)`. An
address is not an identity inside a Ghidra project: the EC's three programs
share one 64 KiB space, and the common area is seeded into **both** bank
programs by design, so one address can carry a row in more than one program.
The value recorded was then whichever program's row the CSV wrote last — a
property of the row order, not of the program being exported.

`docs/findings/entry-namespace-two-copies.md` §7 already records that
`ExportDecompile.java` carries a private `readBasis` beside `TongFang`'s, and
that `ExportListing.java` calls **TongFang's**. Both are fixed here. A fix
confined to the copy the issue names would have left `index.csv` and
`listing-index.csv` — and the `.c` and `.asm` headers — disagreeing about the
same address, which is a worse tree than either spelling alone.

Everything below is derived from committed inputs by
`python3 ec/tools/seed_basis_projection.py`, which reads the committed firmware
and two committed CSVs, writes nothing, and needs no Ghidra. **No hardware was
read, no register was observed and no behavioural claim is made here**: a basis
names *how an entry point was found*, and the byte-scan `call-target` it names
is an upper bound (`ec/annotations/bank-call-audit.md` §1).

## What the issue measured, and why that population was the wrong one

The issue counted, over `ec/decompiled/index.csv`, the addresses carrying rows
in more than one program, and got 55: 37 `bank0`↔`bank1` inside
`0x8000`-`0xFFFF`, 12 `common`↔`pd` and 6 `bank0`/`bank1`↔`pd`. That census is
wrong in both directions at once, and the two errors have different causes.

**It overstates the exposure, because most shared addresses agree.** The
population that matters is not "an address seeded into two programs" but "an
address seeded into two programs *that disagree*". A shared address whose two
programs record the same basis is not one a program-keyed map can change, and
on the committed seed set they are the large majority: the derived seed set
carries 842 addresses in more than one program and only 22 of them disagree on
the basis. The issue's 55 is not that 55 — it is a different measurement over a
different file.

**It also understates it, because it reads the index and the exposure lives in
the seed set.** The index misses all fourteen movers, for two separate reasons.
Seven of them — `4B1F`, `8016`, `8026`, `80D7`, `9006`, `E054`, `F0ED` — sit at
addresses the seed set carries in both bank programs but the *index* carries a
row in only one, so a census keyed on `index.csv` cannot see those addresses
were ever at risk. The other seven are at addresses the census does count, and
**every one of the 55 addresses the issue names already recorded the same value
in both its rows**, so a check that looked for a disagreement there would have
found none on the very tree the issue is about. That agreement is not
correctness either: `bank0 0x2BD5` and `bank1 0x2BD5` both read `call-target`,
and bank0's own seed says `annotation`.

This is the §14b shape the issue itself cites — a reader over a fraction of the
file reporting a clean result — and it is the reason a per-address list rather
than a count is what makes this checkable.

## The per-address verdict

The rows below are the ones that moved, in `index.csv` and in
`listing-index.csv` alike. `python3 ec/tools/seed_basis_projection.py` prints
the full table — every shared address with each program's own basis beside it,
and the rows that disagree — and `build_ec_decompile.py --check` holds the
committed rows against the same derivation and prints the exposure's shape.

| program, addr | was | is | what the address carried |
|---|---|---|---|
| `bank0` `2BD5` | `call-target` | `annotation` | `bank1=call-target`; a cited entry beats a byte scan (`seed_rows()`'s `STRENGTH` order) |
| `bank0` `3A60` | `call-target` | `annotation` | `bank1=call-target`; same rule |
| `bank0` `4B1F` | `call-target` | `annotation` | `bank1=call-target`; same rule |
| `bank0` `8016` | `call-target` | `annotation` | `bank1=call-target`; same rule |
| `bank0` `8026` | `call-target` | `annotation` | `bank1=call-target`; same rule |
| `bank0` `80D7` | `call-target` | `annotation` | `bank1=call-target`; same rule |
| `bank0` `9006` | `call-target` | `annotation` | `bank1=call-target`; same rule |
| `bank0` `BBA4` | `call-target` | `annotation` | `bank1=call-target`; same rule |
| `bank0` `C4AF` | `annotation` | `call-target` | `bank1=annotation`; bank1's row was written after bank0's and both are byte scans, so the row read bank1's |
| `bank0` `CA1D` | `annotation` | `call-target` | `bank1=annotation`; same shape as `C4AF` |
| `bank0` `E054` | `call-target` | `annotation` | `bank1=call-target`; same rule as `2BD5` |
| `bank0` `E090` | `call-target` | `annotation` | `bank1=call-target`; same rule |
| `bank0` `E722` | `annotation` | `auto` | **`bank0` has no seed at all here**; the row read bank1's annotation, and with the borrow gone the honest answer is `auto` |
| `bank0` `F0ED` | `call-target` | `annotation` | `bank1=call-target`; same rule |

Three things in that table are worth stating rather than leaving to be counted.

**Every mover is a `bank0` row, and that is not a coincidence of the fix.** The
driver writes the seed-basis CSV bank0 first, bank1 second, `pd` third, and an
address-only map keeps the last row written. So a shared address whose
disagreement favours bank1 records bank1's answer, which is *right* for bank1's
own row and wrong for bank0's — and the bank1 row at the same address is not
itself a mover, because for bank1 the borrowed value happened to be its own.
That is why thirteen of the 22 disagreement addresses produce a mover and the
other nine do not: the nine are bank1 rows reading bank1's own answer, which the
defect never had any reason to change. Which side a disagreement lands on is
decided by the CSV's row order, and that is the defect in one sentence — the
recorded value was a property of row order.

**`bank0` `0xE722` is the only mover with no seed of its own.** `seed_rows()`
builds no bank0 row at that address, so under a program-keyed map the lookup
misses and the exporter's own fallback, `auto`, applies. That is the honest
answer rather than a gap in the export: nothing seeded bank0 at `0xE722`, and
Ghidra framed the function itself. The converse is worth having too, and it is
what makes `auto` safe to leave in a derivation — **a row already reading `auto`
cannot move**, because `auto` means no program had a row at that address at all,
so neither an address-only nor a program-keyed lookup finds one.

**The `.c` and `.asm` files move too, and that is a coupling worth naming.**
`seedBasis` is not only an index column: `ExportDecompile.writeFunctionFile()`
and the listing's writer both emit a two-line boundary caveat into the `.c` and
the `.asm` whenever it reads `call-target`, because a call-target boundary is
a byte scan's hypothesis (`bank-call-audit.md` §1). Eleven of the thirteen
caveat-bearing addresses cross that boundary in one direction and two in the
other, so this change edits 13 `.c` and 13 `.asm` files as well as the two
indexes, and `verify_c_digests()` stays red until `--write-digests` runs. The
issue's "the export reproduces byte-identical output" was not reachable, and
this is why.

## `pd 0x0012` does not move, and §19's premise had aged out

§19 records that `discover_vector_table()` over the PD bytes returns offsets 0,
3, 11, 19, 27 and 35 and no `0x12`, so `seed_rows()` builds no PD seed there.
That is true of the **vector walk** and it is still true. It stopped being true
of `seed_rows()`, which also seeds from `annotation_seeds()`: a `pd`-scoped row
at `0x0012` exists (`ff_filler_not_a_function_0012`), so the PD program *is*
seeded at that address, on its own row, with basis `annotation`.

So `pd 0x0012` records `annotation` both before and after this change, and for
the first time for a reason that belongs to the PD image rather than to the EC.
§19's paragraph gets an in-place correction beside it rather than a silent
edit, per `CLAUDE.md`'s calibration rule.

## What `--check` asserts, and what it cannot

The issue asked for an assertion that "a `(program, addr)` pair in the
seed-basis CSV is not shadowed by another program's row at the same address."
That is not a property this input has and cannot be made to have: the common
area is seeded into both bank programs deliberately, at every common-area seed,
so the assertion as written fails immediately and means nothing. What is
asserted instead is the pair that would actually have caught this, plus the one
real shadowing case a program-keyed map can suffer:

- **Every committed `index.csv` and `listing-index.csv` row records its own
  program's basis** (a `common` row resolved to bank0, which is what it is —
  `join_index()` renames a folded bank0 row and deletes bank1's). This is the
  ratchet: the next seed row to land at an address another program already has
  is a red run rather than a silent absorption.
- **The seed set holds no duplicate `(program, addr)`**, which is the real
  shadowing case: a program-keyed map drops the second row silently, and which
  of the two is the better reading is not a question a dict answers.
  `seed_rows()` de-duplicates before it returns, so this is a check and not a
  reading.

Both are properties of the tree. Neither is a count of it. `--check` prints the
exposure's *shape* on a green run — how many shared addresses there are and how
many of them disagree — rather than only the absence of a complaint, and this
module's CLI prints the per-address set itself, so nothing has to be asserted
for a reader to see the population the assertion covers.

## The BIOS shares the Java, and its exposure was measurable after all

`ghidra/scripts/*.java` is shared, and `bios/tools/bios_extract.py` writes its
own seed-basis CSV through the same two exporters. Its modules share one x86
address space, so the same borrowing is available there — and the first draft of
this change assumed the BIOS was unaffected, on the grounds that its seed set
"cannot be derived offline". **That is wrong**, and the correction matters more
than the assumption was worth: `bios/ghidra/load-map.csv` is committed and
carries each module's `entry`, and `bios/annotations/ghidra-functions.csv` is
committed, so the BIOS seed set derives offline exactly as the EC's does. A
"no exposure there" claim written from that assumption would have been the exact
failure `CLAUDE.md` puts above every other: a confident negative resting on a
method that was never run.

Derived, **56 of the 955 rows in `bios/ghidra/index.csv` record a basis their
own module does not have**: 31 read `annotation` with no annotation of their own
at that address and move to `auto`, 24 read another module's `annotation` at an
address that *is* their own module's entry point and move to `entry`, and one —
`Setup` `0x3D0`, whose entry is elsewhere — reads `OemOcDxe`'s `entry` and
moves to `auto`. Most of the 24 are recognisable in the committed index by their
names: `module_entry`, `dxe_module_entry`, `entry`, `smi_handler_entry` and
their variants are what the annotation layer named a module entry, so a reader
can pick the entry class out without re-deriving it.

**This change does not re-export the BIOS, and the reason is measured rather
than cautious.** The re-export was run and it is correct — afterwards both BIOS
indexes agree with that derivation on every row, and the BIOS basis vocabulary
has no `call-target`, so no `.c` or `.asm` header moves there. But it also moves
eighteen rows that have nothing to do with this defect (the next section), and
two of those change a row's *name*, which flips a figure pinned in
`bios_extract.py --self-test` that counts the export rather than asserting a
property of it. Shipping the re-export would mean either bumping that figure —
the move `CLAUDE.md` calls out by name — or rewriting an unrelated tool's
assertions inside a change about the seed-basis column. Reverting is the smaller
of the three, and nothing is hidden by it: the derivation is two reads of
committed files, `bios/ghidra/load-map.csv` for each module's entry and
`bios/annotations/ghidra-functions.csv` for the annotation seeds, and the
re-export that applies them is one command.

```sh
python3 bios/tools/bios_extract.py --work /tmp/bios   # regenerates both BIOS indexes
```

## A second, unrelated staleness the re-exports surfaced, and did not fix

Both re-exports moved rows and files the seed-basis derivation did not predict,
and the response to that is a finding rather than a re-bless: every extra moved
row and file was classified before any digest was regenerated, and the ones that
belonged to neither this defect nor the EC's `seed_basis` column were reverted
rather than blessed. Both extra movements are the same shape and both are
pre-existing — **the committed export predates the committed inputs that feed
it**, so each file is internally consistent and the pair is not.

**On the EC, `DAT_EXTMEM_*` placeholders.** The committed `ec/decompiled/**/*.c`
carry placeholder names that the committed `ec/ghidra/xdata-symbols.csv` names —
`DAT_EXTMEM_046c` where the symbols file says `SECOND_FAN_RPM_0`, and so on —
because `ApplyAnnotations.java` applies that file during the export.
`gen_xdata_symbols.py --check` holds the symbols file against `registers.yaml`,
and nothing holds the `.c` files against the symbols file.

**On the BIOS, renames and `evidence` paths.** The export moves two rows' names
(`EcPs2Kbd` `0x260` and `Setup` `0x4B0`, both formerly `entry`) and the
`evidence` column of fifteen `OemOcDxe` rows. Same cause: the annotations CSV
gained rows and citations after the last BIOS export, and no gate compares the
committed indexes against the CSV's current join.

**Both are reverted**, and the EC's reverts are exact: the unpredicted movement
there is a separate set of whole files, none entangled with a `seed_basis` row.
The EC population is measured by reading `ec/ghidra/xdata-symbols.csv` and
grepping the committed `.c` for `DAT_EXTMEM_`/`XDATA_` placeholders at addresses
it names — `0x046C` → `SECOND_FAN_RPM_0` and `0x04A0` → `XDATA_04A0` are two of
them — and it moves with every rename, so what is durable is that the check does
not exist rather than what it would print. Re-running either export reproduces
both, and clearing them is a follow-up against the export rather than against the
seed basis.

## What this does not establish

- **Nothing here is a behavioural claim.** No register was read back, no
  capture taken, no live run made. The change is static over committed inputs.
- **`call-target` is still a hypothesis.** Correcting which program's row a
  boundary's basis came from does not make the boundary real; the caveat that
  moves with the column says so on the affected files.
- **The exposure is a property of the committed seed set, not of the
  firmware.** A future annotation at one of these addresses changes the
  population, which is why the assertion is relational and the census is
  printed.