# The closure against the function inventory, and the `0x808E` boundary that answers §4 (issue #1080)

`bank-attribution.md` §4 pins one instance of the walk's framing risk: the
closure reaches the first byte of the `bank0` `0x8038` dispatch table, decodes
`80 54` as `sjmp 0x808E`, follows it into a real routine, and says so plainly —
"a silent gain rather than as a stop: the closure acquires an address on the
strength of a frame the data handed it, and **nothing in the tables distinguishes
that from a real one**."

That last clause is a question, and `ec/decompiled/index.csv` is a function
inventory for this same image, cut by Ghidra rather than by this walk. **The
tables do distinguish it.** What is left open is which table and which
predicate, because the obvious one is false here: `0x808E` **is** inside a named
row.

Every figure below comes from `python3 ec/tools/census_closure_functions.py`,
which reads committed files and writes none. **Nothing here is a behavioural
claim.** No register was read back, no capture was taken, no Ghidra export ran,
and no `status:` in `ec/annotations/registers.yaml` moved. The numbers are
counts over `ec/decompiled/index.csv`, the committed `.asm` listings,
`ec/annotations/task-call-table.csv` and `ec/firmware/GMxMGxx_11.800` — a
population that moves as the export grows, which is why this file quotes what a
run prints rather than holding a total.

## What the comparison shows

Three predicates, and they do not agree, so all three are printed rather than
one being presented as *the* answer:

| predicate | the question it answers |
|---|---|
| inside a row | is the byte inside some row's span? |
| at a row's entry | is the byte *where a row begins*? |
| at an instruction boundary | did any committed listing decode an instruction here? |

The third is the one §4 needs, and it is not the one the issue proposed.

## The population

`ec/decompiled/index.csv` carries `bank0`, `bank1`, `common` and `pd` rows with
an `addr`, a `size` and a `seed_basis` each. The seed-basis census is not
restated here: `python3 ec/tools/census_closure_functions.py ec/firmware/GMxMGxx_11.800`
prints it as the third line of its own report, and it moves every time a seed
row or an annotation does — `seed-basis-program-key.md` is what moved it last.
What the census establishes, and what the figures below depend on, is that the
values in the column are `annotation`, `call-target` and `auto`, with **no
`vector` rows at all**, which corrects the issue's four-way split.

| reading | bank | reached | inside a row | at a row's entry | outside a row | outside runs |
|---|---|---:|---:|---:|---:|---:|
| `size` | `bank0` | 12694 | 10617 | 546 | 2077 | 1191 |
| `size` | `bank1` | 4159 | 3455 | 161 | 704 | 446 |
| `listing` | `bank0` | 12694 | 10751 | 546 | 1943 | 1124 |
| `listing` | `bank1` | 4159 | 3484 | 161 | 675 | 424 |

**Two readings, because a row's span is two things, and they disagree.**
`size` is `index.csv`'s own column. `listing` is the committed `.asm` span, read
through `second_copy_census.row_span()` — the byte range a reader can actually
check an address against. `bank0 0x8054` records 21 and its listing runs
`0x8054`-`0x806B`, so on this image the two are not the same set and which one
is meant decides the figure. Neither is presented as the population.

**`at a row's entry` overlaps `inside a row` rather than summing with it.** A
row's own address is inside its own span, so the two columns are not a partition
and the report does not present them as one.

### The same figures over rows that are not byte-scan-seeded

| bank | reached | inside (all rows) | inside (no `call-target`) | outside (all rows) | outside (no `call-target`) |
|---|---:|---:|---:|---:|---:|
| `bank0` (`size`) | 12694 | 10617 | 8967 | 2077 | 3727 |
| `bank1` (`size`) | 4159 | 3455 | 2814 | 704 | 1345 |
| `bank0` (`listing`) | 12694 | 10751 | 9046 | 1943 | 3648 |
| `bank1` (`listing`) | 4159 | 3484 | 2849 | 675 | 1310 |

A `call-target` row was put in the inventory by a byte scan finding a `74 01`
pair, which is a weaker footing than a hand annotation in exactly the way a
byte-derived walk is a weaker footing than a hand decode. `bank-attribution.md`
§8 makes the parallel point for the walk, so the census makes it for the rows:
**a row is not a boundary**, and a reader who wants the strict reading takes the
third column rather than assuming it. The gap is wide — over a fifth of bank0's
single-span coverage rests on byte-scan-seeded rows — which is the answer to the
issue's "say which rows a given figure rests on", answered per figure rather
than by enumerating them.

## The bucket-B pair targets

| verdict | inside a row (`size`) | of | inside a listing | of |
|---|---:|---:|---:|---:|
| `attributed-same-bank` | 573 | 573 | 573 | 573 |
| `attributed-cross-bank` | 205 | 207 | 207 | 207 |
| `still-ambiguous` | 115 | 115 | 115 | 115 |
| `unreached` | 409 | 410 | 407 | 410 |

The issue was right that this population is in far better shape than the address
count suggests: agreement with a named row is near-total on every verdict, and
the exceptions are named individually rather than counted.

**They are not the same addresses under the two readings**, which is the reason
both are printed:

| reading | the targets that fall outside every row |
|---|---|
| `size` | `bank0` `0x9022` (contradicting), `bank1` `0x9003` (contradicting), `bank1` `0xF0ED` (unreached) |
| `listing` | `bank0` `0xF0A1`, `bank1` `0xD235`, `bank1` `0xF0ED` — all unreached |

`bank0 0x9022` sits in the gap between `write_1_to_dptr` and `write_2_to_0817`;
`bank1 0x9003` in the one between `ret_only_fragment` and `load_dptr_06ce`.
Under the `listing` reading the first two are covered and two byte-scan-seeded
`FUN_CODE_*` rows drop out instead — rows the `size` column calls 1 byte and
whose listings are absent. **No row covering an address is *not found by this
method*, never "there is no function here"**: it is a statement about
`index.csv`, and none of it is pinned, because a later annotation would
legitimately flip any of it. The census prints its seed-basis census at the top
of its own report so a reader can tell a later change from a wrong reading.

## §4's `0x808E`, answered

`0x8038` is named `index_table_base` (`seed_basis=annotation`), and
`ec/annotations/ghidra-functions.csv` carries a row for it whose comment already
says in prose that the bytes are the eight-entry dispatch table and not a
function. The two handlers the table's entry fields point at are named too:
`0x8094` `index_case_01` and `0x80D7` `index_case_02`.

| address | inside a row's span | starts an instruction in a listing |
|---|---|---|
| `0x8038` | yes, `index_table_base` | yes |
| `0x808E` | yes, `store_byte_through_0a59_into_0600` | **no** |
| `0x8094` | yes, `index_case_01` | yes |
| `0x80D7` | yes, `index_case_02` | yes |

**The proposed test was "`0x808E` is in no row of the index", and that is false
on this tree** — `bank0 0x806C`'s row of size 40 covers it. Pinning it would
have put a red run in a suite over a correct tool.

What does distinguish the two is **instruction boundaries**. No committed `.asm`
starts an instruction at `0x808E`: the listing holding those bytes draws
`0x808C` `lcall 0xbe7e`, and that instruction is three bytes long, so it runs
`0x808C`-`0x808E` and `0x808E` is its last byte.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x8089; px 12' /tmp/bank0.bin
- offset -   0 1  2 3  4 5  6 7  8 9  A B  C D  E F  0123456789ABCDEF
0x00008089  12ba 3d12 be7e 7481 0282 1f90            ..=..~t.....
```

So the walk decoded table data as `sjmp 0x808E` and landed on a byte **no
committed listing ever decoded an instruction at**. That is the distinction §4
asked for, and it is the inventory's own, not this tool's.

**No listing starts an instruction at this address** is *not found by this
method*, never "this is not code". It is what one decompilation of one image
decoded, and the census prints the boundary figure without pinning it: the
predicate reads `ec/decompiled/*.asm`, a regenerable export, so a later
annotation redrawing those bytes would legitimately change the answer and a
red run there would grade a correct tool as broken. What `--self-test` pins
instead is the reason underneath the figure — bank0 `0x808C` is `12 be 7e` in
the committed firmware, `lcall 0xbe7e`, three bytes spanning `0x808C`-`0x808E`
— which no merge can move.

## The `ret` runs, and the reframe

`0x22` is `ret` in the 8051 map. These are the two maximal runs of at least 8
bytes in bank0's window, measured out of the firmware rather than taken from any
report:

| run | bytes | reached | unreached | far-call stubs targeting it |
|---|---:|---:|---:|---:|
| `0xBF1B`-`0xBF2B` | 17 | 17 | 0 | 16 |
| `0xBF54`-`0xBFDD` | 138 | 134 | 4 | 133 |

**The issue's endpoints are off.** `0xBF55`-`0xBFDA` is not the run: `0xBFDB`,
`0xBFDC` and `0xBFDD` are `0x22` too, and `0xBF54` is the `ret` that ends the
block before it. Before the run, `0xBF4E` is `90 09 e3 74 1e f0`; after it,
`0xBFDE` is `90 16 74 74 18 f0`. The issue's "followed by real code at
`0xBFDB`" is three bytes early.

**The attribution here is the linker's, not the walk's, and that is the
substantive correction.** The issue read the large run as "a linear block
walking forward through a linker-reserved gap" and credited its bytes to the
closure. They are not walk-derived frames: **every entry point inside a run is a
trampoline seed**, which is the linker's own far-call stub and the tool's
strongest footing. In each run the one byte that is not a seed is the run's own
first byte, reached from the block before it because that block ends in a `ret`
there — `0xBF1B` from `0xBF12`, `0xBF54` from `0xBF2C`.

So the framing risk this looked like is not an instance of it. The walk adds
nothing here; the closure is crediting the linker.

**149 of the 403 far-call stubs target a byte of one of the two runs**, at a
stride of 1 in target space. That is a count of the linker's own committed
table rather than a fraction of the walk's output, and it is cross-checkable
against a CSV (`ec/annotations/task-call-table.py --check` holds the table).
It is worth more than the address fraction it replaces.

**What is not explained is why BL51 emits a far-call stub per byte of a `ret`
run.** That is a linker/relocation question, this repository does not have the
vocabulary for it, and it stays open.

### What it does to §2's path-count table

| bank | reached | 1 path | of those, `0x22` bytes | of those, inside a `0x22` run |
|---|---:|---:|---:|---:|
| `bank0` | 12694 | 10233 | 673 | 151 |
| `bank1` | 4159 | 3742 | 192 | 0 |

Of bank0's **10233** single-path addresses, **673 are `0x22` bytes** and **151**
are inside these two runs. A byte in a `ret` run reads as path count 1 by
construction — there is nothing in it for a second path to disagree about — so
the `1` column carries a block of filler that is not a weak claim in either
direction. `10233` should not be read as 10,233 separate weak claims, and this
is the measurement behind that. The rest of the `0x22` column is the single
`ret` byte that ends whichever block it terminates, which reads as one path for
the same reason; bank0's runs are the part of it that is visibly a run, and
bank1 has no `0x22` run of the threshold length at all.

**`1 path` here is the path count, which is the distinction that matters.**
`closure()`'s `reached[addr]` is incremented once per block an address appears
in, while `who[addr]` is the *set* of entry points that decode it — so
`len(who[addr]) == 1` is a different and larger set over the same addresses,
and it does not even nest inside the path count. Reading §2's column off
`who` instead would therefore report a different figure for the same table.
The census prints both vocabularies and says which it used; the suite holds the
two apart on a fixture where an address sits in two blocks of one entry point,
which is the case that separates them.

## The second blind spot

§4 says a table that decoded to a stop "would have shown up in §5's bounds, and
one that decodes to code will not show up at all." A `ret` run is the same blind
spot by another route: **each `ret` ends a flow cleanly**, so a walk entering one
would descend into it and stop at the first byte without ever firing a bound.
§5's `bounds` column genuinely cannot see this, and the runs above are the
largest instance in bank0.

## What is not claimed

- **Not a behavioural claim.** Every input is a committed file. Nothing was
  observed on hardware, in Windows, or by a Ghidra run, and nothing here is
  evidence about what the EC executes.
- **Not "proved to be in bank N".** These are the same *attributed by this
  closure* figures §8 of `bank-attribution.md` already qualifies, cross-read
  against an inventory.
- **Not that a row is a function boundary.** A `call-target` row is a byte scan
  that matched; the split above is what keeps that honest, and §8's caveat cuts
  both ways.
- **Not "no row covers this address, therefore no function is here."** That is
  the calibration rule, and it is why the boundary census reports and does not
  pin: the boundary reads the regenerable `.asm` export, so it is printed as a
  dated measurement and the firmware bytes beneath it carry the claim.
- **Not that the exceptions are defects.** Three pair targets outside a row is a
  gap in the inventory's coverage, and the walk's reaching them may be right.
- **No `status:` in `registers.yaml` moved**, and none could have: this is
  Python reading committed files.

## Follow-ups this hands on

1. **Why BL51 emits a far-call stub per byte of a `ret` run.** The real question
   this opens, and a linker/relocation one. It needs the BL51 output or a `.M51`
   map, which this repository does not have.
2. **Annotation rows for the runs**, on the `index_table_base` precedent — but
   one row per run rather than per byte, and by whoever can afford a lone
   `--mode rebuild-project`, since an annotation row seeds a function entry in
   Ghidra and `.gitattributes` makes two branches that both rebuild the project
   unmergeable.

## Re-deriving

One command prints every figure above, and its `--self-test` pins the runs, the
stub count, the seeds inside the runs, and §4's case as the firmware bytes that
explain it. Neither a count of the tree nor a fraction of the walk's output is
asserted, and the instruction boundaries are printed rather than pinned; what is
asserted is the claim.

```console
$ python3 ec/tools/census_closure_functions.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/census_closure_functions.py ec/firmware/GMxMGxx_11.800 --self-test
```

This tool is deliberately **not** wired into `.github/scripts/agent-gates.sh`:
that file is a template copy under `.github/`, and the agent pipeline's token
has no `workflow` scope, so a branch touching it fails at the very end.
`--self-test` is the check, run by hand and quoted here.

Both of the walk's committed CSVs still regenerate byte-identically, which is
the check that this measurement changed the walk's accounting in no way:

```console
$ python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --regions-csv \
    | diff - ec/annotations/bank-attribution-regions.csv
$ python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --pairs-csv \
    | diff - ec/annotations/bank-attribution-pairs.csv
$ python3 ec/tools/task_call_table.py --check ec/firmware/GMxMGxx_11.800
```