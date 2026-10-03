# The 0x07C9 token in `pd/7B14.c` is a variable row on the *callee*, and the re-export is a fixed point

`docs/findings.md` §18 and `ec/annotations/xdata-register-map.md` §7.1 both
recorded that `ec/decompiled/pd/7B14.c` gained a `DAT_EXTMEM_07c9` token across
the #238 merge and lost the constant `0x1c` its first argument used to carry,
while `pd/7B14.asm` still shows `clr A` / `add A, #0x1c` building it — and both
then said the mechanism was not recorded in the committed tree. It was, one
callee over. This is the measurement that found it, the two new tools that make
it repeatable, and the three sentences of the old account that turn out to be
false.

**Nothing here observed the EC.** Every number below comes from reading the
committed firmware, the committed Ghidra project and the committed annotation
CSVs, and from re-running Ghidra's decompiler over those inputs in a scratch
directory. No hardware, no Windows, no live test, and no sentence here should be
read as a register having been read back.

## The re-export: the PD corpus is a fixed point

`ec/tools/pd_9028_render_probe.py --run` copies the committed Ghidra project to
a scratch directory, corrects the project owner in the copy (see below), and
runs `analyzeHeadless -process pd.bin -noanalysis` with the same post-script
chain `build_ec_decompile.py` uses. Its `baseline` arm drops nothing, so it *is*
the re-export, and it is the thing #275 asked for and did not have.

```console
$ python3 ec/tools/pd_9028_render_probe.py --run --work /tmp/probe
  baseline         no row removed; project owner in the copy was 'dave'
                     byte-identical to the committed ec/decompiled/pd/7B14.c
```

Every decompiled body in the committed PD tree re-renders as committed. The
probe watches one file, so that is its own check against the scratch export
rather than a claim about the tree; the whole tree agrees, read off the probe's
own baseline output with the exporter's comment plate excluded (the plate is
this repository's prose, added after the export) and each `.c` compared as
`xdata_register_map.body_of()` reads it:

```console
$ python3 - <<'EOF'   # over <work>/baseline/out/pd: body_of() on each .c, vs ec/decompiled/pd
...                   # prints the per-file list and then how many moved
EOF
```

The only part of that output the claim rests on is the **zero**: no body in the
tree moved. The identical/moved split is left to the command rather than written
here, because it is a count of files in this repository and moves at the next
merge that changes the corpus.

Nothing is churning, and the 22 `DAT_EXTMEM_07c9` tokens in `7B14.c` are stable
rather than an artefact of a merge. That closes one of the two possibilities the
old account left open — the corpus is not a moving target — and it is what makes
the counterfactual arms worth running.

## The counterfactual: it is the variable row

Three arms, each diffed against the committed file.

| arm | row removed | `7B14.c` against the committed file | `DAT_EXTMEM_07c9` |
|---|---|---|---:|
| `baseline` | none | byte-identical | 22 |
| `drop-variable` | `ghidra-variables.csv` `pd,0x9028,param_1` | differs | 21 |
| `drop-function` | `ghidra-functions.csv` `pd,9028` | differs, every call renamed `FUN_CODE_9028` | 22 |

**The variable row moves the token, and removing it puts `0x1c` back.** The two
arms' own lines at that site, quoted from each file rather than reconstructed as
a diff — the `else` arm of the `(*pbVar7 >> 1 & 1) == 0` test, which is where
`7B14.asm` reaches `7CC1 clr A / 7CC2 add A,#0x1c / 7CC4 lcall 0x9028`:

```c
// ec/decompiled/pd/7B14.c
        else {
          cVar2 = DAT_EXTMEM_07c9;
          make_dptr_r6_minus_3_9028(DAT_EXTMEM_07c9);
          *pbVar7 = 1;
        }
```

```c
// the drop-variable arm's export, <work>/drop-variable/out/pd/7B14.c
        else {
          make_dptr_r6_minus_3_9028(0x1c,DAT_EXTMEM_07c9);
          *pbVar8 = 1;
        }
```

The store's target renames with the row (`pbVar7` → `pbVar8`), which a
presentation that showed only the call changing would have hidden. The diff
between the two arms is the whole function rather than one site — the probe
prints it in full under `--run`, and the excerpts above are the part this claim
rests on.

The listing reaches that site on the arm of the `jnb 0xe1, 0x7ccc` at `7CBC`
that falls through. `pd/9028.asm` is six instructions — `mov R7,A / mov A,R6 /
addc A,#0xfd / mov DPL,R7 / mov DPH,A / ret` — and it takes **two** inputs: the
column byte in A, which becomes DPL, and the row index in R6, which becomes the
high byte. The committed render passes one argument; the `drop-variable` render
passes both, in the order the instructions put them.

The signature is the whole of it, and the two neighbours show the shape:

| file | committed | `drop-variable` |
|---|---|---|
| `pd/9028.c` | `char make_dptr_r6_minus_3_9028(char r6_value)` | `char make_dptr_r6_minus_3_9028(char param_1)` |
| `pd/9026.c` | `char make_dptr_r6_minus_3_9026(byte param_1,char r6_value)` | unchanged |

`0x9026` keeps both parameters because `ghidra-variables.csv` gives it *two*
rows (`param_1` and `param_2`, the latter also named `r6_value`). `0x9028` has
one (`param_1`, also `r6_value`), and that one row is enough to make the
decompiler read the single surviving parameter as R6 and drop the A input.
That is the #259 shape — a row naming a decompiler-promoted scratch register as
an `artifact` — at a second callee, and it is the mechanism the old account
said did not exist.

**One function row was measured and it is not the mechanism here.** Dropping
`ghidra-functions.csv`'s `pd,9028` row renames every call in `7B14.c` to
`FUN_CODE_9028` and leaves the token count at the committed figure. That is one
row, so it rules *that row* out rather than settling the function layer: whether
a name can move a caller's argument value is not settled by one row. What the
code says is narrower still — the only effect of a function row that reaches the
decompiler is `f.setName(name, SourceType.USER_DEFINED)`, and the `signature`
column is *recorded, not applied* (the row also sets the plate comment, which
the exporter prints and the decompiler does not read) — but that is consistency,
not the claim. A rename is not *provably* inert: Ghidra's decompiler is
name-sensitive and this tree does not model that, so what settles any given row
is a re-render with that row absent, which is what the `drop-function` arm is.

## Three corrections to the old account

Left in place at `ec/annotations/xdata-register-map.md` §7.1 and `docs/findings.md`
§18, per the calibration rule: the wrong version stays readable with the
correction beside it.

1. **"`0x7B14` has no row in `ghidra-functions.csv` or `ghidra-variables.csv`"
   is false.** `0x7B14` has a hand-decoded function row,
   `stage_07c9_index_then_dispatch_on_flag_bits`, and the name has propagated
   into `call-graph-callees.csv`, `xdata-export-ownership.csv`,
   `cross-decoder.csv` and `xdata-registers.csv`. The absence that mattered was
   at `0x9028`, not at `0x7B14` — and it is in the *variables* layer, which the
   sentence covered by naming both files and finding neither.
2. **"not an annotation effect" was the wrong conclusion**, and it followed from
   (1). It is an annotation effect; the one that moved is on the callee.
3. **"What made Ghidra re-render the file is not recorded in the committed
   tree" was true of the caller and false of the callee.** It is recorded, at
   `ghidra-variables.csv`'s `pd,0x9028,param_1,r6_value,artifact`.

## Settled, decided, and still open

**The `21`, and it is settled rather than left open.** The old account measured
21 → 22 across the #238 merge and could not say why. That merge is `1fcd5f1e`,
and the history answers it without a third arm:

```console
$ git log --oneline -S'pd,0x9028,param_1' -- ec/annotations/ghidra-variables.csv
1fcd5f1e implement issue #133 (#238)
$ git show 1fcd5f1e~1:ec/decompiled/pd/7B14.c | python3 -c '…findall…'   # 21
$ git show  1fcd5f1e:ec/decompiled/pd/7B14.c | python3 -c '…findall…'   # 22
```

#238 added that one row and took the count from 21 to 22, so the row *is* the
+1 — read off the tree rather than inferred from the counterfactual. The
`drop-variable` arm renders 21, the pre-merge figure, and all ten `0x9028` call
forms in its export are identical to the pre-merge file's. The two bodies are
not byte-identical, and the difference is three lines, none of them `0x9028`'s:
each is a later annotation's work — `FUN_CODE_e930` renamed to
`write_07ca_indexed_and_restore_saved_byte_when_flag_e7`, an argument added to
`read_byte_at_dptr_to_r1`, and an argument added to
`make_dptr_r6_minus_3_col_r3`. What is left over from #238 is the row.

(`git log --oneline | wc -l` is a count of commits in whatever clone is asking,
so it is not quoted here; the commands above are what a reader runs.)

**The decision: the committed file stays as re-rendered, and so does the row.**
The issue asked for this and it is a decision rather than a deferral, so the
reasoning is here rather than implied.

`pd/7B14.c` is not corrected. Two things argue for it: `ec/decompiled/**` is
generated output that is re-exported rather than hand-edited, and
`xdata-register-map.md` §7.1's policy already rejected removing a correct
hand-decoded annotation to stabilise a number. `ghidra-variables.csv` is
untouched for the same reason, and `c-digests.csv` is not refreshed.

**And neither arm is right, which is why this is not fixed here.** Every
`lcall 0x9028` in `pd/7B14.asm` is preceded by an `add A, #imm` that sets the
column byte — the exporter prints them unpadded, and the ten are `#0x3`,
`#0x14`, `#0xd`, `#0x19`, `#0x14`, `#0x11`, `#0x14`, `#0x14`, `#0x1c`,
`#0x1c`, several of them after a `clr A` or a `mov A,Rn` — and `A` is what
`pd/9028.asm` moves into DPL. The committed C passes **one** argument at every
one of its ten calls, so one of the two inputs is unrendered at every site.
Removing the row does not repair that: it restores the `0x1c` at the site the
issue named, and elsewhere it drops an argument at some sites and folds a column
constant into the *other* argument at others
(`make_dptr_r6_minus_3_9028(cVar7 + '\x1c')`, where the listing's `0x1c` is the
A input and `pd/9028.asm` never adds it to R6). Deciding which render is closer
at each of the ten sites needs statement-level alignment between the decompile
and the listing, which this change does not attempt and which neither arm
supplies. The disagreement is recorded in the census table and in the two
corrections above rather than closed.

**The general shape.** A `.c` access with no listing counterpart is a class, and
`bank1/E237.c` is the instance its own annotation plate already described. It is
now measured by a tool rather than by a hand annotation, and the class turned
out to be bigger than the two cases this started from.

## The durable half: `ec/tools/c_asm_counterpart.py`

The census `xdata_register_map.py` keeps counts `DAT_EXTMEM_xxxx` tokens over
the decompiled C, which makes every `refs` figure a lower bound on the machine
code. That is the right way round for a count and the wrong way round for a
claim that a byte is touched. `c_asm_counterpart.py` asks the opposite question
of the same corpus — a `.c` that names an address, where the `.asm` beside it
holds no `mov DPTR, #imm` seeding it — and classifies what it could establish.

`bank1/E237.c`'s annotation plate says the decompiled C "continues past 0xE27C
with writes to 0x0680, 0x0681, 0x0683, 0x03A0 and 0x1C05 that this listing does
not contain". All four the body actually names are reported — `0x03A0`,
`0x0680`, `0x0683`, `0x1C05` — and each is classified `beyond-listing-extent`
with `via = bank1:E27D/listing`; `0x0681` is the plate's alone, so nothing files
it. `E237.asm`
runs `[0xE237,0xE27D)` and `bank1/E27D.asm` begins at 0xE27D and holds the
seeds. That is `ExportListing.java`'s `getFunctionContaining` bucketing against
a decompiler that follows the flow graph — the exporter cut the function, the
decompile ran past the cut — and until now the annotation said the phenomenon
without saying where the bytes went.

**The obvious form of that test is vacuous, and the tool does not use it.**
"The address is outside `[entry, end)`" holds for *every* row in the corpus,
because an XDATA byte is never numerically inside a CODE function's range: the
two are different address spaces sharing sixteen bits. The first draft of the
tool used that form and it classified every row it found. Naming the successor
is what makes the verdict say something.

**What it cannot see is this write-up's own case.** The census is per
*(function, address)*, and `pd/7B14.asm` seeds DPTR with `0x07C9` at twelve
sites, so at that granularity the listing *does* witness the address and
`c_asm_counterpart.py` files no row for `pd/7B14.c`. The disagreement is between
the C's argument at one call site and the listing's instructions at that site,
which is a statement-alignment question no text census over the `.c` can
answer. `ec/tools/test_c_asm_counterpart.py` asserts that absence on purpose: a
later change that widened the census to cover it would have to say so rather
than quietly drop the limit.

**One bucket is mostly explained, and is recorded rather than counted.** The
`inc DPTR` walk is a real route to a byte and `xdata_register_map.py`'s
`xdata_space()` measures it properly for the census, but no `mov DPTR,#imm`
names the address, so it is not a listing counterpart and folding the two
together would make one bucket mean two things. The `walked_from` column carries
the seed one byte below whenever the listing has one, so the `no-witness` rows
read as the walk they mostly are instead of as an absence. `bank0/8054.c`'s
0x08D1 against `bank0/8054.asm`'s `mov DPTR,#0x8D0` is the worked case, and
`ec/annotations/xdata-register-map.md` §7.1 already records 0xFFC1, 0xFFD1 and
0xFFDB as reachable only this way.

## Two things this could not do, and one it did not try

- **`build_ec_decompile.py --check` is not the gate here.**
  `c_asm_counterpart.py --check` recomputes `ec/ghidra/c-asm-counterpart.csv`
  and byte-diffs it, which is the shape `citation_gap_scan.py` established.
- **The Ghidra arm is deliberately not in `tools/run-tests.sh`.**
  `pd_9028_render_probe.py --self-test` exercises the CSV surgery — that an arm
  drops the named row and nothing else, that writing the copy over the file it
  read is refused, and that a key matching no row raises rather than producing
  a render indistinguishable from the baseline — and
  `ec/tools/test_pd_9028_render_probe.py` is what runs it, alongside the same
  properties held against the committed CSVs rather than a fixture: that each
  arm's key matches exactly one committed row, that the layer an arm does not
  target is handed over as the committed path so the arm differs from the
  baseline in one row, and that both committed CSVs are byte-identical after
  the arms have been built. So the guard that keeps a counterfactual from
  editing a committed annotation is exercised by the runner and not only by a
  human typing the flag. `--run` needs the toolchain and minutes of wall clock,
  and is still not wired in.
- **The `NotOwnerException` is worked around in the copy, not in the tree.** The
  committed project records its owner as `dave`, and Ghidra refuses to open a
  project owned by another user before it analyses anything.
  `docs/findings.md` §18 records this as one of two pre-existing defects. The
  probe rewrites `project.prp` in its scratch copy and leaves the committed file
  byte-identical.

## What this opens

- **The `beyond-listing-extent` class is not E237's alone.** It is a property of
  where Ghidra's function boundaries fall against where the decompiler's flow
  graph goes, and it recurs across the corpus. The census is the table; nobody
  has read it.
- **The 0x0390 pin did not go red.** `xdata_register_map.py --self-test` pins
  the `.asm` witness for `0x0390` against its absent census row, and is written
  to fail on exactly the improvement being chased. Nothing here moved 0x0390, so
  the pin held and this change does not touch it. A pin moves only with a
  measured reason recorded in the same change, and there is no measurement to
  record.
- **`ORACLE` and `BUCKET_TOTALS` are not re-derived.** `xdata_register_map.py`
  rests on `.c` files that this change has now shown reproduce byte for byte
  from the committed project, which is a weaker version of the question the old
  account left open: not "do they re-render" but "what rests on them". That is a
  different change on a different question.
