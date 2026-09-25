# The counter sweep's entry set: 180 call sites, one of them a call (issue #555)

`bank1:0x8001`-`0x8189` is 393 bytes ending in a `ret`, and
`ec/decompiled/index.csv` exports them as 42 functions. **31** of the 42 rows in
`../ec/annotations/ghidra-functions.csv` that describe them say in their own
words that the boundary is a hypothesis of the call-target scan's making, and
**28** of them say something stronger and wrong: that the body runs `0x8018`
to the `ret` at `0x8189`. `../ec/annotations/xdata-06c2-06db-timers.md` §8 item
7 has asked for the boundaries to be settled rather than documented.

**They are settled here, by measurement, and the answer is one address:
`0x8001`.** Of the 180 census rows that target into the run, exactly one is at
an instruction start in a committed listing. The other 179 are not: 177 are
operand bytes of instructions a committed listing already carries, 135 of them
the `rel8` displacement of a `cjne`, and the remaining two — `bank1:0x81E7`
and `bank1:0xA6DC` — sit in a committed gap no listing covers, which is a
*different* kind of "not found by this method" from an identified operand byte
and is reported as one. **One confirmed caller found by this method** is the
whole of the finding — not "the only caller in the firmware", and not "179
absent calls". The method is `../ec/tools/counter_sweep_entry.py`; every figure
below is its output, and `--self-test` asserts the load-bearing ones.

**The deletion the issue also asked for is not here, and not because it was
skipped.** Removing the slice rows removes *no* seeds (every one of the 42
annotation addresses is also a census seed), `--mode export-only` cannot
un-carve functions already in the committed `.rep`, and the rebuild that
would is blocked one step later by the pinned assembler behind a single-writer
guard. §5 and §6 are the measurement; §7 is the recipe for the machine that
can finish it.

## 1. The run, re-derived

Every descriptive claim in the issue and in
`../ec/annotations/xdata-06c2-06db-timers.md` §2 holds exactly:

| | |
|---|---:|
| `index.csv` rows with `program=bank1` over `0x8001`-`0x8189` | **42** |
| their `size` values, summed | **393** — the length of the run |
| gaps or overlaps in the tiling | **0** |
| of them one instruction long | **16** |
| their `seed_basis` | `annotation`, all 42 |
| the byte at `0x8000`, before the run | `0x22` (`ret`) — `bank1/8000.asm`, `ret_only_8000` |
| the byte at `0x8189`, the run's last | `0x22` (`ret`) |

## 2. The entry set: how it was measured

`../ec/annotations/bank-call-audit.md` §1 is the standing caveat on
`../ec/annotations/bank-call-targets.csv`: the census is a **byte-scan upper
bound, not a partition**, because a `0x02` or `0x12` byte is read as an
`ljmp`/`lcall` opcode whether or not one is there. This is that caveat turned
into a number for one run.

The method is the repository's own, not a new one. Each of the 180
`bank1`-region rows whose target lands in `0x8001`-`0x8189` is scored with
`../ec/tools/disasm8051.py`'s `converges_from()` — the anchored-decode half of
every count `audit_call_targets.py` already reports — and then cross-checked
against the instruction starts parsed out of the 674 committed
`../ec/decompiled/bank1/*.asm` listings. The two halves are reported together
and never separately, because neither is sufficient:

- **the frame score alone proves nothing.** `converges_from()`'s own docstring
  says a site nobody syncs onto "is not thereby misframed — it may simply be
  preceded by data (a dispatch table, padding) that no linear walk can decode
  into alignment", and `bank-call-audit.md` §1 makes the converse point, listing
  sites that score 24 of 24 and are plainly inside an address table. This
  repository's own note that "the anchored number is not the phantom-free one"
  is why the score is never the verdict here;
- **the listing position alone does not settle framing either**, for the same
  reason. What settles a site is both: a score *and* the committed instruction
  that owns the byte.

The region filter is load-bearing rather than a shortcut. `offset_for_runtime()`
resolves a target at or above `0x8000` against the **caller's own bank**, so a
`bank0` or `common` row naming `0x8001` is about a different byte. 47 such rows
exist in the census and none of them is evidence about this run.

## 3. What the 180 sites are

| what the site is, in a committed listing | count |
|---|---:|
| an instruction start | **1** |
| the `rel8` displacement byte of a `cjne` (opcode `0xb4`, `0xb5`, `0xba` or `0xbf`) | **135** |
| the `rel8` displacement byte of another PC-relative branch | 39 |
| the low target byte of an `ljmp`/`lcall` the listing already carries | 1 |
| an immediate operand of an instruction that is not a branch | 2 |
| in a committed gap, covered by no listing | 2 |

108 of the 180 score 0/24 outright. The ten most-framed of the rest, with the
listing evidence beside the score:

| runtime | file | census says | frame | in a committed listing it is |
|---|---|---|---:|---|
| `0xABB8` | `0x12BB8` | `lcall 0x8001` | **24/24** | **an instruction start** |
| `0x9C34` | `0x11C34` | `ljmp 0x801A` | 5/24 | byte 3 of 3 — `cjne A, #0x5a, 0x9c37` |
| `0x8CFE` | `0x10CFE` | `ljmp 0x800B` | 3/24 | byte 2 of 2 — `jnc 0x8d01` |
| `0x9C4A` | `0x11C4A` | `ljmp 0x8004` | 3/24 | byte 3 of 3 — `cjne A, #0x69, 0x9c4d` |
| `0xA45F` | `0x1245F` | `ljmp 0x8013` | 3/24 | byte 3 of 3 — `cjne A, #0xd, 0xa462` |
| `0xE2E7` | `0x162E7` | `ljmp 0x803C` | 3/24 | byte 3 of 3 — `cjne A, #0x3, 0xe2ea` |
| `0x9C16` | `0x11C16` | `ljmp 0x8020` | 2/24 | byte 3 of 3 — `cjne A, #0x0, 0x9c19` |
| `0x9C20` | `0x11C20` | `ljmp 0x8021` | 2/24 | byte 3 of 3 — `cjne A, #0x20, 0x9c23` |
| `0x9F08` | `0x11F08` | `ljmp 0x800B` | 2/24 | byte 3 of 3 — `cjne A, #0x5b, 0x9f0b` |
| `0xA484` | `0x12484` | `ljmp 0x8024` | 2/24 | byte 3 of 3 — `cjne A, #0x8, 0xa487` |

**The `cjne` row is the finding, and it is one measurable place where the
caveat bites.** A `cjne` is three bytes with its displacement last, so a scan
looking for a literal `0x02` or `0x12` opcode finds that displacement and reads
the following two bytes as a 16-bit target. 135 of the 180 sites are exactly
that. Nine of the ten rows above are of this kind or its `sjmp`/`jz`/`jc`/
`jnc`/`jb`/`jnb` equivalents.

**The entry is `0x8001`, and it is corroborated three ways that do not depend
on each other.** The one site at an instruction start is `bank1:0xABB8`
`lcall 0x8001` at 24 of 24 — the only perfect score anywhere in the run, the
next best being 5. The byte before the run is the `ret` that ends the
preceding routine, so `0x8001` is a hard start and not a continuation. And
`0xABB8` is independently annotated
(`call_8001_c613_91e8_a8f0_a916_1aa4_a2f3`, a seven-call forwarder whose *first*
call is `0x8001`), which is a reading of the bytes that predates this tool.

The five census "callers" of `0x8001` are worth reading in full, because four
of the five are the `cjne` shape and only the fifth is a call:

| runtime | frame | in a committed listing it is |
|---|---:|---|
| `0x899D` | 1/24 | byte 3 of 3 — `cjne A, 0x00, 0x89a0` |
| `0x89DB` | 1/24 | byte 3 of 3 — `cjne A, 0x00, 0x89de` |
| `0x9293` | 1/24 | byte 3 of 3 — `cjne R7, #0xf, 0x9296` |
| `0x95D1` | 0/24 | byte 3 of 3 — `cjne A, #0x2, 0x95d4` |
| `0xABB8` | **24/24** | **an instruction start** — `lcall 0x8001` |

## 4. Five of the six hypotheses the issue asked to be settled are refuted; `0x8001` is confirmed as the entry

| address | census "callers" | best frame | target in a listing | annotation row | verdict |
|---|---:|---:|---|---|---|
| `0x8001` | 5 | **24/24** | yes | yes | **the entry** |
| `0x8008` | 8 | 1/24 | yes | yes | slice — a seed #179 added |
| `0x8010` | 4 | 1/24 | yes | yes | slice — a seed #179 added |
| `0x8017` | 6 | 1/24 | yes | yes | slice — a seed #179 added |
| `0x8018` | 3 | 1/24 | yes | yes | slice — the "body starts here" claim is wrong |
| `0x80EF` | 1 | 1/24 | yes | yes | slice — the "listing agrees with the body" claim is wrong |

**The three seeds are not confirmed; they are refuted as entry points.** Their
own comments said the one-instruction boundary was "the call-target scan's
hypothesis". The hypothesis is now tested and does not hold: no site naming
`0x8008`, `0x8010` or `0x8017` scores above 1 of 24, and the best-placed of the
three is a `cjne` displacement byte — except `0x8017`, whose single best site
is a byte in a committed gap between two listings. They remain useful rows —
they are the only per-slice reading of those bytes — but they are not entry
points and must not be described as candidate ones.

**The "body starts at `0x8018`" claim is affirmatively wrong, not merely
unproven.** 28 of the 42 rows say the body runs `0x8018` to the `ret` at
`0x8189`, which is 370 bytes. The body is 393 bytes and starts 23 bytes
earlier, at `0x8001`. The 23 bytes the claim omits are the `0x06C6` and
`0x06CD` countdowns in full and the `mov DPTR,#0x06D1` / `movx` / `jz` / `dec A`
that precede the store-back at `0x8018`. Separately, 31 of the 42 rows say in
their own words that the boundary is a hypothesis of the call-target scan's
making; that hypothesis is now tested rather than open. The wrong wording is
left standing in every affected row with the correction beside it, per
`docs/findings.md` §4a.

**The `0x80EF` "here the listing and the body agree" claim needs the same
treatment, and the correction is narrower than it looks.** What that row says:

> The tail of the body that starts at 0x8018, all 94 instructions of it
> including the `ret` at 0x8189, so here the listing and the body agree.

The **94 instructions and the extent are right** — `80EF.asm` really does run
from `0x80EF` to the `ret` at `0x8189`, 155 bytes, and `index.csv`'s
`size=155` agrees. What is wrong is the comparison: the listing at `0x80EF` and
the body at `0x8018` are the same 155 bytes only because the body was
mis-stated. Against the entry this tool establishes, the body is `0x8001`
(393 bytes, 238 more) and the listing is its tail. The two are the same
*function*, not the same span.

## 5. Why the deletion and the re-export cannot land unattended

Two independent blockers, each measured.

**Deleting the slice rows removes no seeds at all.**
`../ec/tools/build_ec_decompile.py:seed_rows()` (`:509`) builds each program's
seed set as a **union** of `ghidra-functions.csv` and the
`bank-call-targets.csv` census, de-duplicated on `(program, addr)` after
sorting by evidential strength (`STRENGTH` at `:536`, `annotation`=0 ahead of
`call-target`=3). Running the tool's own `call_target_seeds()` over the
committed census: **all 42 annotation addresses in the run are also census
seeds** — the annotation-only count is zero — and the census independently seeds
**70** addresses in the run, 28 of which have no annotation row. Delete all 42
rows and 70 seeds remain, seeding exactly the same boundaries. The per-target
table above carries the `annotation row` column that derives this from the two
committed CSVs alone.

**Export-only mode cannot un-carve.** The default mode
`shutil.copytree`s the committed project and opens the copy with `-noanalysis`
(`:708`/`:710`), applying only annotation seeds. The 42 functions are already
baked into the 7.4 MB committed `.rep`, and **no script under
`ghidra/scripts/` calls `removeFunction`, `clearListing` or `deleteFunction`**
(grepped all five: `SeedFunctions.java`, `ApplyAnnotations.java`,
`ExportListing.java`, `ExportDecompile.java`, `TongFang.java`). Nothing in the
pipeline merges them back. So the default mode leaves 42 functions and 42
exports whatever the CSV says.

**Corollary: deleting the 41 slice rows with no rebuild would be strictly
regressive.** The rows are load-bearing twice. They hold the only per-slice
reading of those bytes. And the retained `bank1,8001` row is what makes
`STRENGTH` place the entry *ahead* of the 70 census seeds, so a future rebuild
carves the right function first rather than whichever census target sorts
first. Strip 41 comments with no rebuild and the same 42 functions remain, 41
of them undocumented.

## 6. Why the rebuild is blocked one step later

`--mode rebuild-project` would change the listing set: **41 listings disappear
and `bank1/8001.asm` grows from 3 bytes to 393.** Then:

- `../ec/ghidra/reassembly.csv` carries a `listing_digest` per listing
  *precisely so* `--check` can see a text edit
  (`../ec/ghidra/README.md` §"The disassembly, and the 1:1 property");
- `verify_reassembly.py --check` runs in the **cheap gate tier**
  (`.github/scripts/agent-gates.sh:159`) and fails any listing without a row
  there, and fails any row whose digest no longer matches the listing;
- regenerating it needs the pinned
  `sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14` (nix, SDCC 4.6.0).
  `.github/actions/project-setup` installs Ubuntu's apt `sdcc`, which reports
  `02.00` — a different ASxxxx that **moves 52 outcomes and rewrites all 2,707
  `assembler` cells** (2,705 of the committed rows carry the pinned string and
  2 carry `02.00`);
- `refuses_committed_report` (`verify_reassembly.py:699`) is a single-writer
  guard — `reassembly.csv` *"is written by --report and by nothing else"* — and
  `../ec/ghidra/README.md` draws the consequence: *"there is no path that adds
  one row and leaves the rest of the file measured with the pinned assembler."*

`../ec/ghidra/README.md` states it outright: *"A new export wants a machine
with the nix toolchain."* This is the identical wall
`../ec/annotations/xdata-06c2-06db-timers.md` §8 item 1 documented for the
`0xC10C` seed, where the precedent was explicit: *"a red
`verify_reassembly.py --check` is not a way to land them."* It also writes the
7.4 MB `.rep` that `.gitattributes` makes unmergeable, so per the issue it
"lands alone or not at all".

## 7. The recipe, and the prediction to check against it

On a machine with nix, from the repository root, with the 41 slice rows already
deleted from `../ec/annotations/ghidra-functions.csv` and the `bank1,8001` row
kept:

```console
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ec --mode rebuild-project
$ SDAS8051=$(nix build nixpkgs#sdcc && echo $out/bin/sdas8051) \
    python3 ec/tools/verify_reassembly.py --work /tmp/ec --report
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ec --write-digests
$ python3 ec/tools/call_graph.py   # no --check: writes the committed table
$ bash .github/scripts/agent-gates.sh
```

`--write-digests` is in the recipe on purpose and must **not** be run for this
change on a runner: the digests are of the committed `.c` files, and a
`--mode rebuild-project` rewrites them.

**What to expect, stated as a prediction and not as a result.** One row at
`0x8001` spanning 393 bytes, with the other 69 in-run census seeds rejected as
overlaps — `SeedFunctions.java` counts a `createFunction()` that returns `null`
as `already`, and `manifest.csv` records `seeds_applied` and `seeds_rejected`
per program. Confirm it from `../ec/decompiled/index.csv` and
`../ec/ghidra/manifest.csv`. **If more than one row survives, that is a finding
to record, not a reason to re-add slice rows.**

## 8. What this does not establish

- **Not "the only caller in the firmware".** One caller was *confirmed* by this
  method. The other 179 sites are a gap in a byte scan with a named blind spot;
  a caller reached through a computed DPTR, a function-pointer table or a BL51
  trampoline is invisible to every method named here.
- **Not 179 absent calls.** Read §3's table the other way round: 135 are
  positively identified as something else.
- **Not a register claim.** Nothing here bears on what any byte *means*. The
  sweep's 43 XDATA addresses keep the readings and the `status:` values
  `../ec/annotations/xdata-06c2-06db-timers.md` gives them, and no row in
  `../ec/annotations/registers.yaml` moves.
- **Not a live observation.** No byte was read, written or read back, and no
  behaviour was observed. This is a byte-frame and text measurement over
  committed inputs, reproducible by anyone with the committed firmware.
- **Not the census's de-duplication.** 2a's 42-fold count is a separate defect
  and its figures are unchanged by this. The issue said to feed this back to the
  census-dedup work rather than fold it in, and the boundaries landing is what
  that work needs, not what it needs from this page.
- **The frame score is one method's opinion, reported beside the listing
  evidence for that reason.** `converges_from()` is the repository's own, and
  `bank-call-audit.md` §1's note that its anchored counts are demonstrably not
  phantom-free applies to the 24/24 here as much as to the 0/24s.

## Reproducing it

```console
$ python3 ec/tools/counter_sweep_entry.py            # the four sections above
$ python3 ec/tools/counter_sweep_entry.py --self-test
$ python3 ec/tools/counter_sweep_entry.py --csv > /tmp/entry.csv
```

`--self-test` asserts the 42/393/16 shape and the tiling, the 180/70 counts, that
the tool's own `converges_from()` scores reproduce the census's recorded ones on
all 180 rows, the single anchored site and its 24/24, the five slice scores, the
`ret` at each end, the 42-of-70 seed union, and the two silent misreadings it is
easy to commit here — that a `bank1` *file offset* is not a runtime address
(`0x12BB8` is `0xABB8`, so the listing is `bank1/ABB8.asm`), and that a listing
line's operand text carries its own four-hex-digit tokens, so the address parse
has to be anchored at the start of the line.

The other checks a reader should run, and what each one proves:

```console
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ec --check --self-test  # no Ghidra
$ python3 ec/tools/call_graph.py --check
$ python3 ec/tools/verify_reassembly.py --check   # proves no committed listing moved
$ python3 ec/tools/check_cluster_citations.py
$ bash .github/scripts/agent-gates.sh
```

`verify_reassembly.py --check` staying green is the direct evidence that this
change is entirely on the static side of the rebuild line: no `.asm`, no `.c`,
no `index.csv` and no `reassembly.csv` row moved. `--write-digests` must **not**
be run for it.
