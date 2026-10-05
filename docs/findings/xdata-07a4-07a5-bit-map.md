# The `0x07A4` (`GC6S`) bit map: bit 4 is written, and no committed listing reads it (issue #636)

**Read this first: everything below is static.** No laptop was opened, no EC
register was read back, no Windows service was run. Every claim here is a
reading of committed bytes, and the `.asm` listings are the authority over the
decompiled `.c` wherever the two disagree, as each listing's own header says.
Whether the EC *acts* on any bit below is a separate question this file does not
answer, and no `status:` in `registers.yaml` moves on the strength of it: both
bytes stay `present-untested`, which is what
`ec/annotations/registers.yaml`'s gloss on that value already means.

Issue #636 was filed against a tree that has since moved, so two of its premises
were stale when this was worked (§2). What it actually asked for turned out to
be answerable, and the answer inverts the premise it was filed on.

## 1. The answer

**Bit 4 of `0x07A4` is written by one committed site, and no committed listing
reads it.** All three readers of the byte test a different bit — two test bit 0,
one tests bit 2. So the bit `#267` named as the only site with a *named
consequence* is, on the committed evidence, set or cleared by a boot-time seed
and then not consumed by anything in the tree.

The issue expected the consequence to be picked up by "the three other
readers". It is not. That is a **negative**, and it is written as "not found by
this method" rather than "nothing reads it": both committed scans count direct
`mov DPTR,#imm16` sites, so a consumer that reaches the byte through a DPTR
built at run time is invisible to both. `0x07B9` is the standing counter-example
— writable, working, and zero direct sites anywhere in the image
(`docs/findings.md` §4c). The claim is that no *committed listing* reads bit 4,
and §5 says what a live test would have to add to settle the rest.

## 2. Two of the issue's premises were out of date

Both are recorded rather than quietly dropped, because a reader holding the
issue would otherwise be looking for work that is already done.

**"`0x07A4` has no entry in this file"** — it has one. `0x07A4` is `GC6S` in
`ec/annotations/registers.yaml`, at bit 2, `present-untested`, from the DSDT ECMG
field sweep. Its note already carries the `0xDA4F` bit-4 sentence `#267`
parked. `0x07A5` is `XDATA_07A5`, also `present-untested`, and its note already
carries a bit-3 map. The issue was written before `GC6S` landed, so **no new
`registers.yaml` rows are added here** — what was missing was the per-site map
and the reconciliation below, and those are what this file adds.

**The quoted census figures are the C-level method's, and they count a
different unit from the image's.** §3 reconciles the two.

## 3. The two reference counts, reconciled

The two committed methods disagree about `0x07A4`, and neither is wrong: they
count different units over different trees. This is the same disagreement
`XDATA_1665`'s own note records for `0x1665`, in the same shape.

| method | unit | `0x07A4` | `0x07A5` |
|---|---|---|---|
| `xdata_register_map.py` (`xdata-registers.csv`) | occurrences of the address's **symbol** in the decompiled C, comments stripped | 7 | 8 |
| `check_register_counts.py` (`registers.yaml` `static_refs`) | direct `mov DPTR,#imm16` **sites in the image** | 4 | 5 |

The gap is arithmetic, not error. `D9FE.c` spells the writer as two lines of
`GC6S = GC6S & 0xef;` and `GC6S = GC6S | 0x10;`, and each line names the byte
**twice** — once as the assignment target and once on the right-hand side — so
one `mov DPTR` reach contributes two counted occurrences. Three single-line
readers contribute one each. Seven over four sites, and the same relation holds
at `0x07A5`.

```sh
# the image method, and the row it writes
python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
# the census method, whose row is a column of the committed CSV
grep '^0x07A4,' ec/annotations/xdata-registers.csv
```

The census's `readers`/`writers` columns count *functions*, not sites: `0x07A4`
reads 4 and writes 1, which is the same four sites with one writer among them.
`ec/annotations/site-resolution.csv` holds exactly four site rows for `0x07A4`,
agreeing with the image method and with `static_refs: 4`.

## 4. The per-site bit map

One row per site, read off the committed listings. Addresses are the runtime
addresses the listings carry; `0x07A4`'s four sites are the whole of the direct
scan, and `0x07A5`'s five are all inside one routine.

| site | bank | function | bit | instruction | effect |
|---|---|---|---|---|---|
| `0xB889` | bank0 | `09ee_bit1_edge_drives_0897_countdown` | 2 (read) | `jnb 0xe2, 0xB89E` | bit 2 clear → set bit 1 of `0x09EE`; bit 2 set → clear it and start the `0x0897` countdown |
| `0xDA53` | bank0 | `seed_07d3_gfid_and_08xx_defaults` | **4 (write)** | `orl a,#0x10` / `anl a,#0xef` | **sets** bit 4 when `0x1665` bit 6 is set, **clears** it when not |
| `0x8FE5` | bank1 | `gate_06c2_0472_0801_then_count_06ce` | 0 (read) | `anl a,#0x01` | bit 0 clear → `mov R5,#0x19` + `lcall 0x88F0` |
| `0x9638` | bank1 | `set_0476_bit1_then_branch_on_r7` | 0 (read) | `anl a,#0x01` | bit 0 clear → `lcall 0x1804`; set → return |
| `0x8812` | bank0 | `mode_tick_084c_07a5_09ee` | 3 (write) | `orl a,#0x08` | sets bit 3 above the CPU/GPU thresholds |
| `0x882C` | bank0 | `mode_tick_084c_07a5_09ee` | 3 (write) | `anl a,#0xf7` | clears bit 3 below them |
| `0x8840` | bank0 | `mode_tick_084c_07a5_09ee` | 3 (read) | `jnb 0xe3, 0x884B` | bit 3 → R6, compared against `0x09EE` bit 0 |
| `0x8851` | bank0 | `mode_tick_084c_07a5_09ee` | 3 (read) | `jnb 0xe3, 0x8861` | bit 3 → sets or clears bit 0 of `0x09EE` to match |
| `0x8873` | bank0 | `mode_tick_084c_07a5_09ee` | 3 (write) | `anl a,#0xf7` | clears bit 3 on the `XDATA_0440`-zero arm |

The `0x07A5` half confirms the claim `XDATA_07A5`'s note already made — all five
sites are bit 3, the one bit the Windows service's four uncalled setters do not
touch. The two readers are the part that note's set/clear wording does not
itself cover: `0x8840` and `0x8851` read bit 3 to decide whether `0x09EE` bit 0
follows it, which is a **consumer relationship between two bytes** and is why
bit 3 is not simply "written and unread" the way bit 4 is.

**`0x8851` reads `0x07A5` even though its `mov DPTR` has already moved on.**
Between the read at `0x8854` and the branch at `0x8858` sits `mov DPTR,#0x9ee`,
and that does not touch the accumulator — so the `jnb 0xe3` is testing bit 3 of
the byte loaded two instructions earlier, not of the new DPTR. The store that
follows each arm does go to `0x09EE`. Reading this site off the DPTR alone would
give the wrong byte, which is why the map above names the bit test rather than
the address it branches on.

**`0xDA53` writes a bit of `0x07A4` under a test of a *different* byte.** The
sequence loads `0x1665`, branches on bit 6, and only then loads the `0x07A4`
DPTR. That ordering is the whole reason the site is a write rather than a fourth
reader, and it is what §6's census row loses sight of.

**Neither bit-0 reader can write back through the call it makes.** Each leaves
DPTR pointing at `0x07A4` across its `lcall`, which would otherwise make it a
handoff the callee could store through — the one shape that could give bit 0 a
writer inside these two routines. It is not one: `0x88F0` begins by rebuilding
DPTR (`mov DPTR,#0x0440`), and `0x1804` builds a CODE pointer and tail-jumps
(`mov DPTR,#0xc48f` / `ljmp 0x1100`). So the bit-0 reads are reads, and the byte
has exactly one confirmed writer in the committed tree.

```sh
# the two arms, in the listing that is authority over the .c
sed -n '/^DA4F/,/^DA63/p' ec/decompiled/bank0/D9FE.asm
# the whole bit map, decoded from the committed image
python3 ec/tools/walk_branch_arms.py ec/firmware/GMxMGxx_11.800 0x07A4
```

The `sed` addresses the listing by its own instruction labels rather than by
line number, for CLAUDE.md's reason: a `file:NNN` pin is true only until the
next merge grows the file above it, and `D9FE.asm` is regenerated.

## 5. What is open

**Whether anything reads bit 4 at run time.** Not settled, and not settleable
from this tree. A consumer reached through a computed DPTR would not appear in
either committed scan, and `0x07B9` shows what that blind spot costs when it
bites.

**What writes bit 0, 1, 3, 5, 6 or 7 of `0x07A4`.** Nothing found by this
method. The DSDT names bit 2 and calls it `GC6S`; the expansion is not in the
ASL, so what the EC is expected to *do* with the byte is not established here.

**What a live test would have to do.** Read `0x07A4` back before and after the
`seed_07d3_gfid_and_08xx_defaults` path runs, with `0x1665` bit 6 set and then
clear, and check whether anything else in the byte moves. That needs the
physical machine; this repo's pipeline cannot reach it, and no step here claims
otherwise. A register write being accepted is not evidence the EC acts on it,
so nothing above would substitute for that observation.

## 6. One census row understates a real writer, and it is not the tool's fault

`ec/annotations/site-resolution.csv` records the `0xDA53` site as
`no movx in window` / `unresolved-none`. The listing resolves it in the open:
`orl a,#0x10` and `movx @DPTR,A` on one arm, `anl a,#0xef` and `movx @DPTR,A`
on the other. The row is not wrong about its own method — `walk()` decodes
forward until the first control-flow instruction, and the `jnb 0xe6, 0xDA5F` at
`0xDA56` is one, so the linear window ends before either store. That is exactly
what `unresolved-none` is documented to mean: "no `movx` in the decoded window
at all. Not evidence of anything, in either direction."

**The committed instrument that settles it already exists and is a separate
tool on purpose.** `check_site_resolution.py`'s docstring says a direction
reached by following a branch is a weaker claim than one resolved where it sits,
"and exactly why it may not be allowed to warrant a grade" — which is why the
census keeps the weaker verdict. `walk_flow_follow.py` is that other instrument:

```sh
python3 ec/tools/walk_flow_follow.py ec/firmware/GMxMGxx_11.800 0x07A4
```

It resolves `0xDA53` to a read and a write, reached by falling through the
`jnb`. So the two committed tables disagree about this row, both correctly, and
**this change fixes neither**: editing `check_site_resolution.py` to follow the
branch would resolve the row but would also change what the `resolution` column
*means*, in a table `check_status_vocabulary.py` rule 3 reads as the warrant for
a `present-untested` grade.

The blast radius was measured before that was declined rather than assumed.
Resolving a `none` row by walking **both** arms of the branch its window stopped
at moves sixteen rows across eight addresses — `0x0460`, `0x0751`, `0x07A4`,
`0x07C4`, `0x07D3`, `0x08EB`, `0x09C9` and `0x0A47` — well past this byte's
neighbourhood, and past the point where the change is about one row. Every one
of the eight already carries a resolved label from another site, so no grade
would move; but the census would stop being a census of *where a direction is
established* and become one of *where one can be found by following a branch*,
which is the distinction the `->flow` columns exist to keep. That is a change to
a shared tool's contract, not a correction to one row, and it belongs to whoever
owns that contract.

```sh
# the population the fix would touch, re-derivable from the committed image
python3 ec/tools/check_site_resolution.py ec/firmware/GMxMGxx_11.800 --summary
```

The disagreement is recorded here instead, which is what it is worth: a reader
of `site-resolution.csv` who lands on `unresolved-none` for `0x07A4` now has the
row's other half.

## 7. Corrections kept visible

Per `docs/findings.md` §4, nothing here overwrites a prior claim; each is
corrected beside what it replaced.

- `XDATA_1665`'s note ends its `0xDA4F` bullet by saying the consequence "lands
  on an undocumented byte; recorded as a follow-up rather than expanded into
  here." **That sentence is left as written**, with a correction beside it naming
  the row that now exists and this file. Folding it into the original would have
  left a reader who remembers the old wording with no way to see it was retired.
- `XDATA_07A5`'s existing claim that the EC's direct sites "write one bit of
  this byte between them, bit 3" is **confirmed, not corrected** (§4). What the
  write-up adds is the two reader sites that claim does not mention.
- `GC6S`'s row keeps its `bit: 2` and its `present-untested` grade. Its note
  already recorded that bit 4 is "the one bit of this byte something in the
  committed listings is known to write, and it is not GC6S"; §1 answers what
  that bit is for.

## What the test holds

`ec/tools/test_xdata_07a4_07a5_bit_map.py` pins the claims rather than the
counts: each site's deciding instruction is at the address this file names, the
`0xDA53` arms store what is claimed, each reader's callee rebuilds DPTR so it
cannot write back through the pointer it was handed, `0x8851` still reads
`0x07A5` across the `mov DPTR` that moves on, both bytes stay
`present-untested`, and `XDATA_1665`'s note still carries #267's sentence.

Two things it pointedly does **not** assert. It holds no figure out of
`xdata-registers.csv` against a fresh scan — that column is regenerated by
`xdata_register_map.py --check` and moves whenever another branch seeds a
routine, so the suite asserts only the *relation* §3 describes. And it asserts
**no census of the tree** — no total of write-ups, suites or rows — with its one
negative phrased as a property of the scanned sites, for the reason §1 gives.

```sh
bash tools/run-tests.sh
```