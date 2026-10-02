# `caseD_<n>` and `default` are Ghidra's too (issue #631)

Issue #602 installed a rule that a row of `ec/annotations/ghidra-functions.csv`
must not take its name out of Ghidra's own reserved namespace, and pinned the
Python transcription of that namespace against the Java in both directions.
Issue #631 is what the rule could not see: the namespace listed `switchD_` —
the container Ghidra puts a `switch` it framed into — and not the two spellings
it puts on the entries *under* that container. Fourteen committed index rows
were therefore reported `annotated=yes` while holding a name Ghidra chose, and
every figure derived from that column overstates person-chosen names by
fourteen.

This is the write-up: the census over committed files, the fourteen addresses
and what declares each one, the decision and the branch it declined, the
figures before and after, and what is **not** established.

Everything below is a static reading of committed files. No register was read,
no machine was observed, and nothing here was seen in Windows. The one Ghidra
run involved is the export-only re-export in §5, and §5 reports what it changed
and what it did not. Every figure is a measurement over `ec/firmware/GMxMGxx_11.800`
(SHA-256 `158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4`) and
the committed export as of **2026-10-02**.

## 1. The census, and how it was run

`python3 ec/tools/second_copy_census.py --check` already derived the population
and filed each member by mechanism, and it reported `21 row(s): 7
target-of-a-transfer, 14 ghidra-switch-entry, 0 unexplained` before this change.
The fourteen were not a guess and not a reading of the bytes: the tool read the
committed `.c` at each address and found a declaration inside a `switchD_*`
namespace, which it prints beside the row. `annotated=yes` with no
`ghidra-functions.csv` row behind it is the exporter's own
`annotation_ledger()`'s first list, so the population and the column are read by
one definition rather than by two.

**What the issue's own figures said, and what this tree says.** The issue was
filed against a base several annotation tranches behind `main`, so its numbers do
not reconcile here and none of the difference has anything to do with the
predicate:

| | issue says | measured here, 2026-10-02 |
|---|---|---|
| ledger population | 25 (11 `auto` / 9 `call-target` / 1 `vector`) | 21 (11 `auto` / 10 `call-target`) |
| arithmetic | 1,872 − 0 + 11 = 1,883 | 1,961 − 0 + 7 = 1,968 |
| sum | 1,897 | 1,982 |
| bank1 `functions_named` | 605 → 591 | 608 → 594 |

The fourteen addresses the issue lists are correct and all `bank1`. Its second
correction — that a self-test comment misdescribed its bucket as 15 `auto` rows
— was about that older base too: on this tree all eleven `auto` rows **are**
`caseD_0`, so that sentence was accurate when written and is superseded by the
predicate change below rather than by #489's rows. It is not repeated here as a
correction, because there is nothing left to correct.

## 2. The fourteen, and what declares each

Thirteen are `caseD_<n>` and one is the bare word `default`, and every one is
inside a `switchD_CODE:` namespace in the committed `.c` — which is Ghidra's own
switch analysis naming a table it framed, not a name this repository's scripts
gave anything (`SeedFunctions.java` passes `createFunction(a, null)`,
`ApplyAnnotations.java` renames only where a row resolved).

| program | addr | index name | declared in the committed `.c` | `seed_basis` |
|---|---|---|---|---|
| `bank1` | `0x8A80` | `caseD_0` | `switchD_CODE:8aa6::caseD_0` | `auto` |
| `bank1` | `0x91D0` | `caseD_0` | `switchD_CODE:91f9::caseD_0` | `auto` |
| `bank1` | `0x98B4` | `caseD_0` | `switchD_CODE:98e4::caseD_0` | `auto` |
| `bank1` | `0x99B7` | `caseD_0` | `switchD_CODE:99df::caseD_0` | `auto` |
| `bank1` | `0x9AD2` | `caseD_0` | `switchD_CODE:9b02::caseD_0` | `auto` |
| `bank1` | `0x9E0E` | `caseD_0` | `switchD_CODE:9e36::caseD_0` | `auto` |
| `bank1` | `0xA31B` | `caseD_6` | `switchD_CODE:a308::caseD_6` | `call-target` |
| `bank1` | `0xAD50` | `caseD_0` | `switchD_CODE:ad76::caseD_0` | `auto` |
| `bank1` | `0xC8BB` | `caseD_0` | `switchD_CODE:c8e2::caseD_0` | `auto` |
| `bank1` | `0xC90C` | `caseD_0` | `switchD_CODE:c930::caseD_0` | `auto` |
| `bank1` | `0xD000` | `caseD_0` | `switchD_CODE:d036::caseD_0` | `auto` |
| `bank1` | `0xD003` | `caseD_1` | `switchD_CODE:d036::caseD_1` | `call-target` |
| `bank1` | `0xD037` | `default` | `switchD_CODE:d036::default` | `call-target` |
| `bank1` | `0xD20D` | `caseD_0` | `switchD_CODE:d22d::caseD_0` | `auto` |

**What the predicate sees is the leaf.** `Function.getName()` returns `caseD_0`
for the symbol a `.c` declares as `switchD_CODE:8aa6::caseD_0`, and that is what
both exporters read when they write the `annotated` column and the `[named]`
marker. So the two leaf spellings have to be named as themselves rather than as
a path through the namespace; `caseD_` joins `GHIDRA_RESERVED_PREFIXES` and
`default` joins `GHIDRA_RESERVED_EXACT` in `grade_name_basis.py`, and both Java
copies gained the same two literals.

## 3. `default` is an exact match, and there is a committed row that says why

`caseD_` is a prefix because it is a family Ghidra names. `default` is one
symbol and gets `equals`, for the same reason `entry` does — and with a sharper
answer than `entry`'s, because the tree already contains the case:

| index | rows | `caseD_*` | named exactly `default` |
|---|---|---|---|
| `ec/decompiled/index.csv` | 2720 | 13 | 1 (`bank1 0xD037`) |
| `bios/ghidra/index.csv` | 955 | 0 | 0 |
| `windows/ghidra/index.csv` | 10664 | 0 | 0 |

`bank0 0x549B` is a `ghidra-functions.csv` row of its own named
`default_009d_bf_dispatch_4e2c`. A `startsWith("default")` would have matched it,
reported the row `annotated=no`, and reproduced the exact fault #602 renamed
seven rows over — on a row that is nothing to do with a switch. That row is
asserted in `grade_name_basis.py --self-test` beside the two new positives.

The table is three committed indexes read on 2026-10-02, so the zero in the BIOS
and Windows rows is **not found by this method over those three indexes**, not a
claim that Ghidra never names a function `default`. The BIOS and Windows
projects are not re-exported by this change.

## 4. The decision: both halves, and why neither alone is the answer

The issue offered two branches. Both landed, because neither alone satisfies it.

**The rule — widen the predicate.** `annotated=yes` is what `manifest.csv`'s
`functions_named` counts and what the `[named]` markers count. Those are the
figures the issue names, and a manifest has nowhere to carry a caveat, so
restating the meaning alone would have left 1,982 overstating person-chosen
names by fourteen.

**The meaning — restate the column.** Needed *even after* the widening, because
the widened column still is not "did a person choose this name". Measured, after
the fourteen left: seven `annotated=yes` rows hold no person's name at all —
`bank0 0x031C` / `0x805B`, `bank1 0x031C` / `0x703A` and `common 0x0512` /
`0x10FA` / `0x1207`. They are second copies, where a bare transfer propagated
the target's name across the call;
[`named-without-a-row.md`](named-without-a-row.md) is the per-address reading and
`second_copy_census.py --check` files all seven as `target-of-a-transfer`. So the
sentence in `ec/ghidra/README.md` that read "did Ghidra name this, or did a
person" was false for 14 rows whichever branch was taken, and is restated as
"is this name one Ghidra reserves, or is it a person's" with those seven named
beside it.

**The sequencing on #626 is merge ordering, not correctness.** The guard in
`build_ec_decompile.py --self-test` reads the canonical `TongFang.java` only, and
the `equals`/`startsWith` divergence on `entry` is invisible to it — #602's own
re-export went through with that drift already in place. This change adds two
*different* literals to the same expressions and does not touch the divergence,
so it stays green either side of #626. It is placed after it because both edit
the same two methods.

## 5. What moved, measured

The anti-regression evidence is the diff of the re-export. It was run in a copy
of the repository rather than in the tree, because `write_outputs()` opens with
`shutil.rmtree(OUTDIR)` and `OUTDIR` is the committed `ec/decompiled`; the
`--work` directory is where the project copy and Ghidra's output go, not where
the export lands.

One step came before the run, and it is
[`call-graph-unresolved.md`](call-graph-unresolved.md)'s own separate issue,
**not** fixed here: the committed `ec/ghidra/project/ec.rep/project.prp` is owned
by `dave`, so `analyzeHeadless` refuses the copy with `NotOwnerException`.
Correcting the owner **in the scratch copy only** and re-running is what
follows, and the committed database is not written either way.

- **`ec/decompiled/index.csv`: exactly 14 rows**, all `bank1`, all the
  `annotated` column flipping `yes` → `no`. No other row in the 2,720-line index
  moved, which is the direct answer to the issue's "without moving any genuine
  Ghidra auto-thunk off `annotated=no`": `annotated=no` goes 738 → 752 by exactly
  these fourteen.
- **`ec/decompiled/listing-index.csv`: exactly 14 rows**, the same fourteen from
  the listing exporter.
- **28 `.c` / `.asm` files, one header line each.** The `.c` marker comes from
  `ExportDecompile.java` and the `.asm` header from `ExportListing.java`; after
  the re-export the two agree exactly at **1,968 `[named]` headers of each kind**,
  which is also the manifest's `functions_named`.
- **`ec/ghidra/manifest.csv`: exactly one cell**, bank1's `functions_named`
  608 → 594. `annotations_applied` (828 / 725 / 541) and
  `annotations_unmatched` (0) did not move, because the same rows still apply at
  the same addresses.
- **`ec/ghidra/c-digests.csv`: exactly 14 rows** — the header line is inside the
  digest.
- **`ec/annotations/call-graph-callees.csv`: exactly 2 rows**, `bank1 0xA31B` and
  `0xD037`, regenerated by `call_graph.py`, which copies the index's `annotated`
  column verbatim. The eleven `caseD_0` rows were seeded `auto` and never entered
  that file.

| | before | after |
|---|---|---|
| `functions_named`, sum | 1,982 | 1,968 |
| `functions_named`, `bank1` | 608 | 594 |
| `[named]` `.c` headers | 1,982 | 1,968 |
| `[named]` `.asm` headers | 1,982 | 1,968 |
| `annotated=no` rows | 738 | 752 |
| named-without-a-CSV-row | 21 (11 `auto` / 10 `call-target`) | 7 (all `call-target`) |
| `second_copy_census.py --check` | `7 target-of-a-transfer, 14 ghidra-switch-entry, 0 unexplained` | `7 target-of-a-transfer, 0 ghidra-switch-entry, 0 unexplained` |

`ghidra-functions.csv` is byte-untouched — `grade_name_basis.py --check` remaining
a clean no-op is the evidence — so no `registers.yaml` `status:` is engaged and
`ec/ghidra/xdata-symbols.csv` does not move.

**The census's `ghidra-switch-entry` bucket stays and has no instance.** It is
still the right answer to a question this tool asks: it is what classifies a
switch entry whose bytes reach somewhere real under a name that is not its own,
and it is what keeps `unexplained` reachable from the other side. Deleting it
would remove the classifier that answers for a row that has not arrived yet. The
fixture refusal in `second_copy_census.py --self-test` — a jump whose target is
a row under another name — is where it is exercised now.

### Found on the way, and deliberately not absorbed

**The re-export also produced six `.c` files this change does not touch.**
`bank0/8749.c`, `bank0/95DD.c`, `bank0/96AD.c`, `bank0/A7C8.c` and
`bank1/A916.c` came back printing `XDATA_078B` / `XDATA_07A5` where the committed
copies still print `DAT_EXTMEM_078b` / `DAT_EXTMEM_07a5`, and `bank0/ACB4.c`,
whose committed copy carries no annotation plate at all although
`ec/annotations/ghidra-functions.csv` has a comment row for it, came back
carrying one. Which correction that plate holds, and which it predates, is not
something this tree shows.
This is **pre-existing staleness in the committed export, not drift caused by
this change**: the committed `ec/ghidra/xdata-symbols.csv` already carries
`XDATA_078B` and `XDATA_07A5`, so the committed `.c` files contradict their own
committed symbol table, and nothing in this change touches an XDATA symbol or an
annotation comment.

Absorbing them would have put a register-tranche regeneration and an annotation
re-export inside a diff whose whole argument is a predicate, and would have made
`c-digests.csv` carry twenty rows where it carries fourteen. They are reported
here and left alone. Regenerating the EC export picks them up as a matter of
course; that is the fix, and it is not this branch's.

## 6. What this does not establish

Nothing here is a hardware or Windows observation, and nothing claims to be. No
register was read, written or read back; no interrupt, fan or charge behaviour
was exercised. The change is a naming decision plus a regenerated static export,
and the proof is the diff of that export and the checks that count it.

It says nothing about the fourteen *functions*. `bank1 0xD037` was a
`switchD_CODE:d036::default` entry before this change and is one after; the
bytes, the declared name and the frame Ghidra drew are untouched. The `annotated`
column never claimed to be a statement about the code.

**Whether a `--mode rebuild-project` from the CSV alone would re-derive these
names is not established, and the predicate does not answer it.** The new literals
record that the declaration sits in Ghidra's own switch namespace, which is a
statement about a name's provenance; `named-without-a-row.md` §1 is careful about
the same boundary for the other seven, and that care carries over. Ghidra's own
switch analysis is what produced the name, and nothing in this repository's
scripts reproduces it — but "these scripts would not re-derive it" is not the
claim, and "Ghidra would" is not established either.

Nor does it follow that no future export will produce another reserved name. The
predicate is a list, it is transcribed twice, and `build_ec_decompile.py
--self-test` holds the two transcriptions to each other in both directions. That
is a check and it fires on the next drift; it is not a proof of completeness.

`ec/tools/test_named_marker_agreement.py` is the belt to that braces: it holds
every committed index row's `[named]` marker — in its `.c` **and** its `.asm` —
equal to `annotated == "yes"`, because the self-test's two-sided guard reads
`TongFang.java` only. Widening one Java copy and not the other turns nothing red
in the guard, while `index.csv` (written by `ExportDecompile`) and
`listing-index.csv` plus the `.asm` headers (written by `ExportListing` →
`TongFang`) disagree in committed output. It is ungated by design:
`.github/` is template-copied and this branch's token has no `workflow` scope,
so `tools/run-tests.sh` is what reaches it.

## 7. Follow-ups

1. **The six stale `.c` files in §5.** `bank0/8749.c`, `bank0/95DD.c`,
   `bank0/96AD.c`, `bank0/A7C8.c` and `bank1/A916.c` print XDATA names their own
   committed symbol table has already replaced, and `bank0/ACB4.c` carries no
   annotation plate though `ec/annotations/ghidra-functions.csv` has a comment
   row for it. The next EC re-export picks them up; nothing here needs deciding,
   only running.
2. **The same widening over the BIOS and Windows projects.** Measured as zero
   rows in both committed indexes (§3), so re-exporting is not needed to make
   the claim true. It would confirm the widening is harmless in two more
   components, which is a different and weaker thing than this change asserts.
3. **The seven second copies, as a question the column cannot answer.**
   `annotated=yes` on a row whose name is a propagated copy of a target's is
   correct under "not reserved" and misleading under "a person named it". The
   predicate cannot see it and should not try to; the honest answer is that the
   column's meaning is the reserved-list question and nothing wider, which is
   what `ec/ghidra/README.md` now says.