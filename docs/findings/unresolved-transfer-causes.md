# Why the call-graph's unresolved and unreached rows are the ones they are

`ec/annotations/call-graph.md` said, of every transfer site whose target the
index does not carry, that they are "branches into straight-line code, not
evidence of a missing function". `call_graph.py` never supported that for the
population: `scan()` keeps the unresolved targets in a `Counter` and `report()`
prints `sum(unresolved.values())` beside the number of keys, so the eighty keys
were emitted nowhere and one sentence was carrying a per-target cause for all
of them. The sentence is right about the rows it fits and wrong as a claim
about the population, because four different things sit inside it and they call
for different things from a reader.

`ec/tools/call_graph_gaps.py` measures the split and writes it to two committed
tables, and `--check` recomputes both byte for byte. This file is the reading of
them: what each cause is, which of them are weak, and what is still unplaced.

Nothing here is a register claim, nothing moved a `status:` in
`ec/annotations/registers.yaml`, and no live test ran. Every figure is a static
reading of committed listings, `ec/decompiled/index.csv` and
`ec/annotations/registers.yaml`, re-derivable with the command beside it.

## The four causes, and the order they are decided in

Each rule is a predicate over committed files, and the order is not
preference — the first is `Index.resolve()`'s own reason for declining, so a
target in that class is reported under the cause its resolver already gives.

| cause | the predicate | what it means for the target |
|---|---|---|
| `multi-scope` | two or more `index.csv` rows carry the address, and no reaching site's own scope is among them | `Index.resolve()` declined it. The function may well exist in two banks; this scan is not entitled to say which |
| `xdata-or-data` | no index row, and `registers.yaml` records the address | an address `registers.yaml` documents as an XDATA byte — which is **not** a statement that the target is data, as the next section says |
| `interior-entry` | no index row, and the address is strictly inside `[addr, addr+size)` of another row | a branch into a routine the index already carries at a different address |
| `no-index-row` | none of the above | **this method placed the target nowhere.** Not a claim that it has no function |

Measured on the committed tree, with `targets / sites`:

```console
$ python3 ec/tools/call_graph_gaps.py | head -12
  unresolved transfer targets                     80
  sites reaching them                            103
  distinct caller listings reaching them          62
    multi-scope                                     5 targets,      6 sites
    xdata-or-data                                   2 targets,      2 sites
    interior-entry                                 60 targets,     81 sites
    no-index-row                                   13 targets,     14 sites
  of which every reaching site is ajmp/acall       31
  targets the precedence decided over one cause      2
```

That `distinct caller listings` line is a **union** of `(scope, listing)` pairs
over the whole site map, not a sum of the per-target `callers` column. The
column counts distinct callers *per target*, so a listing that reaches two
unresolved targets is one listing and the sum counts it twice; the sum is
reported nowhere, because printing it under the word *distinct* is the same
mistake one level down as reporting a per-target cause as a cause for the whole
population.

**The precedence decides two targets, and printing that is the point.** A
precedence that quietly settles a row is a rule no reader can see, so the
overlap is a reported figure rather than an implementation detail. Both are
`0x074C` and `0x080C`, each an `xdata-or-data` target that is *also* an
interior entry of a routine — and, as the next section shows, each is code.
They are labelled `xdata-or-data` for that one reason: rule 2 outranks rule 3.
The `host_*` columns keep the routine either way, so the precedence does not
cost the reader the pointer:

```console
$ grep -E "^(074C|080C)," ec/annotations/call-graph-unresolved.csv
074C,1,1,ljmp,xdata-or-data,pd,0738,shift_r3r4_right_1,pd/05A6@05EA
080C,1,1,ajmp,xdata-or-data,common,0806,FUN_CODE_0806,common/0D7B@0DE6
```

That the higher cause wins is a decision about *which label to print*, not a
claim that the address is not an entry into a routine — and the artifact keeps
the host row precisely so the losing rule's evidence is not thrown away with
the losing rule.

**`interior-entry` is the population the issue's population 2 is two instances
of.** `0x5A44` and `0x5A46` land one and three bytes into
`common/5A43` `addc_chain_into_r7_5a43`, and the artifact carries the host row
and the paged forms that reach it:

```console
$ grep -E "^(5A44|5A46)," ec/annotations/call-graph-unresolved.csv
5A44,2,1,ajmp,interior-entry,common,5A43,addc_chain_into_r7_5a43,common/5CFE@5D49 common/5CFE@5D79
5A46,5,4,ajmp,interior-entry,common,5A43,addc_chain_into_r7_5a43,common/5A66@5B07 common/5A66@5B37 common/5DC2@5E37 common/5E02@5E07 common/5E82@5F87
```

An `ajmp` puts the page in the opcode and only the low byte in the operand, so
`0x5A43`, `0x5A44` and `0x5A46` are three entry points into one body. That is
a property of *how* a target is reached rather than of why it failed to
resolve, so it is the `forms` column and the vocabulary stays at four values.
Thirty-one targets are reached only by `ajmp`/`acall`; twenty-six of the
`interior-entry` ones are.

## The `xdata-or-data` lookup is a membership test, and not a data finding

The lookup establishes exactly one thing: that `registers.yaml` records the
address as an XDATA byte. It does **not** establish that the transfer target is
data, and on this tree it does not even point that way. CODE and XDATA are
separate address spaces on an 8051, so an address appearing in a register
cross-reference says nothing about whether a numerically equal code address is
code. The committed index is the standing counter-example — `0x07C1` is both
the `AP02` entry in `registers.yaml` and the first byte of
`common,07C1,write_0x11_to_1700_1701_1702` in `ec/decompiled/index.csv` — and
the addresses the file carries that are code row starts print as:

```console
$ python3 -c "import sys; sys.path.insert(0, 'ec/tools'); \
    import build_ec_decompile, call_graph, call_graph_gaps as g; \
    xa = build_ec_decompile.registered_addresses('ec/annotations/registers.yaml'); \
    sp = g.spans(call_graph.load_index()); \
    print(' '.join(sorted('0x%04X' % a for a in xa if any(s == a for s, _n, _r in sp))))"
0x0402 0x0408 0x07C1 0x07D0 0x07D6 0x0862 0x086B 0x08A0 0x1666 0x1C14
```

**Both targets the class fires on here are code.** `0x074C` is an instruction
inside the hand-decoded `pd/0738` `shift_r3r4_right_1`, and `0x080C` is the
third byte of the `jnb` at `common/0806`:

```console
$ sed -n '18p' ec/decompiled/pd/0738.asm
074C     a2 d5 -  mov      CY, 0xd5
$ sed -n '11p' ec/decompiled/common/0806.asm
080A     30 e3 15 jnb      0xe3, 0x0822
```

So the value is named for what the lookup found, and the name is the only thing
carrying the caveat. A reader who takes `xdata-or-data` as a data finding is
reading a membership test as a conclusion, on the two rows where this tree can
check it and both of them come out the other way. The `host_*` columns are what
keep the routine visible underneath the label, which is why the precedence
above is affordable at all.

The lookup also has **low recall**: it finds 2 of the 80 targets. **A target
the lookup does not name is not found by this method** — it is not "not
XDATA", and it is emphatically not "code". A two-hit lookup says nothing about
the other seventy-eight, which is why the artifact's own header comment repeats
the caveat too: that file is what someone opens in an editor, and the terminal
that printed the census is not carrying the docstring.

## The unreached rows, and why `entry` is three values

`report()` counts the anonymous rows no transfer reaches and prints one
integer. The question behind that integer — is this row the continuation of a
neighbour, or is nothing reaching it? — has a computable half, and the rule
answers it positionally: is the row immediately after some index row's last
instruction?

It then has to say whether control *actually* falls through there, and the
obvious answer to that — ask whether the predecessor ends in `ret`/`reti` — is
wrong on most of the population. An `ljmp` is three bytes of unconditional
jump, so an address one past one is adjacent by arithmetic and **jumped over**;
calling that a fall-through credits an entry the bytes do not make, which is
the overclaim `CLAUDE.md` puts above every other rule. The question is
therefore asked of `NO_FALLTHROUGH`, which carries two halves and says which is
which: the returns and the unconditional transfers (`ljmp`, `ajmp`, `sjmp`, the
indirect `jmp`), where control provably does not continue; and the conditional
branches, which continue into what follows only when they are **not** taken —
this tool reads listings rather than tracing, so it credits nothing past one,
which is the conservative direction and a statement about the method rather
than about the branch. `lcall`/`acall` are deliberately out of the set, because
a call returns to the instruction after it and a row one past a call really is
fallen into. So `entry` is `fall-through`, `adjacent-no-fallthrough`, or
`not-adjacent`:

| entry | rows | what it says |
|---|---|---|
| `fall-through` | 35 | adjacent, and the predecessor's last instruction is one control does continue past, so **control does continue into the row** |
| `adjacent-no-fallthrough` | 217 | adjacent, and the predecessor's last instruction is one `NO_FALLTHROUGH` covers, so **this method credits it no fall-through** |
| `not-adjacent` | 66 | nothing this method read places it |

Twenty-seven of the rows have a *named* predecessor — four `fall-through` and
twenty-three `adjacent-no-fallthrough` — and the artifact carries which per
row. `common, 0x0F12` is the worked example the issue reached for: it sits
immediately after `common, 0x0EF3` `write_internal_ram_init_constants`, whose
last instruction is a `mov`, and a `mov` is not a boundary, so the row really
is fallen into.

The `pred_*` columns name the **listing whose last instruction lands on the
row**, which is not always the index row `index.csv` says owns those bytes: a
listing that runs past its own declared `size` covers rows the index assigns
elsewhere. Each listing's header already calls its boundary a hypothesis, so
this is a precision limit in a supporting column rather than a
misclassification — the byte immediately before the row really does hand
control on either way, which is what `entry` reports.

`not-adjacent` is **not** "reached by a function pointer". It is this method
reading no transfer and no continuation for the row — the same calibration the
`inbound == 0` rows of `call-graph-callees.csv` carry, and stated as such in
both artifacts' headers.

The refuted case is on the committed tree, and it is the reason the set is
wider than the returns. `common/0016` ends in a three-byte `ljmp`, so `0x0019`
one past it is jumped over:

```console
$ tail -1 ec/decompiled/common/0016.asm
0016     02 11 5c ljmp     0x115c
$ grep "^common,0019," ec/annotations/call-graph-unreached.csv
common,0019,FUN_CODE_0019,1,adjacent-no-fallthrough,common,0016,table_entry_to_115c,yes,common/0019.asm
```

## A figure that did not re-derive: the `0x5A43` inbound count

Issue #461 reports `0x5A43` as having **8 `ajmp` inbound** and asks that "11
`ajmp`" be corrected wherever it does not re-derive. **On the committed tree
both figures are right and the disagreement is between two columns, not two
readings.** `call-graph-callees.csv` records:

```console
$ grep "^common,5A43," ec/annotations/call-graph-callees.csv
common,5A43,addc_chain_into_r7_5a43,yes,bank1,11,0,0,11,0,8,0,0,
```

which is `inbound=11`, `lcall=0`, `ljmp=0`, `ajmp=11`, `acall=0`,
`callers=8`. Eleven `ajmp` **sites** reach `0x5A43`, from **8 distinct caller
listings** — `call_graph.py`'s own docstring is explicit that a function calling
the same callee from three places is one caller and not three, because the
listing's stem is the caller's entry address. The issue's "8" is the
`callers` column.

So `ec/README.md`'s bullet, the `call_graph.py` docstring and the three
`call-graph.md` lines that say "11 `ajmp`" **all hold, and none of them is
edited.** The wrong figure is left visible here beside the table row that
corrects it, rather than corrected in a file that already carries a correction
table. What is added is the caller-versus-site distinction the two columns were
always keeping apart, which is the part of the issue's paragraph that was a
real gap.

## What is still unplaced

**Thirteen targets are `no-index-row` and stay unclassified**, which is the
issue's own instruction and this tool's calibration rule. They are not errors
in the classifier and not a population waiting to be relabelled: they are rows
where an index lookup, a `registers.yaml` lookup and a size-span search all came
back empty, and the honest reading of three misses is that this method placed
them nowhere. Hand-reading them is real work and is the next tranche if anyone
wants it; it is not something a fourth value in the vocabulary would settle.

**The `bank1` twin of `0x3A60` is still anonymous.** `0x3A60` is a
`multi-scope` target: `common/0213`'s `lcall` reaches an address that
`index.csv` carries as a named bank0 row (`cascade_gate_170a_1709_1708`) and an
anonymous bank1 row (`FUN_CODE_3a60`). The artifact records both host rows
rather than picking one, because a bank program can only reach its own copy and
`Index.resolve()` is right to decline. Naming the bank1 twin is an annotation
tranche, not a classifier decision, and it is not made here.

**`0x845D` is not re-derived.** It is open as [#366](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/366)
and this change records only what the artifact measures: `0x845D` is an
`interior-entry` whose host is `bank0,83FF` `sync_0788_and_07d4_from_09e9`,
whose `size` of 157 runs to `0x849C`. The artifact carries no note column and
no prose cell, precisely because a hand-maintained column is prose that has
escaped `--check`.

## Cross-program hosts are recorded, not filtered

Some `interior-entry` hosts sit in a program other than the reaching site's own
— a `pd` transfer lands inside a `common` row. The two programs have separate
address spaces (`citation_frames.program_reason`, and
[`pd-common-address-spaces.md`](pd-common-address-spaces.md)), so the host is
deliberately **not** looked up under the reaching site's scope. Narrowing the
search would report those rows as unplaced, which is the quiet direction: a
filter that drops rows looks exactly like a tool that found fewer of them.
`host_scope` carries the program's name, so the reader sees which is which and
can count the split off the artifact. It is not counted here because the two
populations differ: the host lookup fires for more targets than the
`interior-entry` label names, since the precedence keeps a host for a target
whose winning cause did not need one.