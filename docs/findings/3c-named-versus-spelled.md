# §3c's named-versus-spelled counts, re-derived, and the 17 addresses that sit between them (issue #1162)

The write-up for [issue
#1162](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1162), which is
about [`docs/findings.md` §3c](../findings.md) carrying figures the census no
longer produces. What this branch changes is that section's named-and-spelled
paragraph, and this file.

**Nothing here is a hardware claim.** No register was read back, no capture was
opened, no firmware image was interpreted, and no laptop, EC or Windows machine
is involved. Every figure below is a count over committed files, produced by a
command given next to it.

## The measurement

Two commands, both offline and both reading only committed files:

```
$ python3 ec/tools/xdata_register_map.py --self-test
...
all assertions passed

$ python3 ec/tools/check_census_figures.py --print
```

The first is `xdata_register_map.py`'s own known-answer run; the second derives
every figure in this write-up from `annotations/xdata-registers.csv` and prints
the `ORACLE` key each one corresponds to. Neither needs the image, Ghidra or a
network. What §3c had no way to be held to is the reason the second exists:
`check_doc_figure_pins.py` reads figures out of tables carrying a `verdict`
column, and §3c has none, so the one tool built to answer "which of this
section's numbers is held" reports nothing for it:

```
$ python3 ec/tools/check_doc_figure_pins.py docs/findings.md --section 3c
docs/findings.md §3c: no table in this section has a column headed 'verdict', so
no figure in it was measured -- a section that stops declaring its held/unheld
split would otherwise report a clean run
```

That is why the deliverable here is a suite and not a paragraph. The section
drifted twice under a checker that could not see it.

## What moved, and what did not

§3c's census table — 1,218 / 157 / 1,326 distinct and 14,838 / 858 / 15,696
references — is **still correct on this tree**, re-derived and unmoved. So are
the token pins the oracle holds beside it: `extmem_main_distinct` 882,
`symbol_main_distinct` 180 and `extmem_commented` 9. The census the section was
written against has not moved under the table; only the paragraph below it has.

**One figure in §3c did not re-derive, and it is not one of those.** The `CPU_TEMP`
mention count in the paragraph *above* the table reads 56 raw
(`grep -ro CPU_TEMP ec/decompiled/ --include=*.c | wc -l`) and 43 once
`xdata_register_map.py`'s `strip_comments()` removes this repository's own
annotation prose — 13 of the 56 are annotation comments quoting the decompile.
**43 is the figure the census carries**, in `xdata-registers.csv`'s `refs` column
for `0x043E`, so the two methods agree once comments come out and the raw 56 is
the outlier. §3c's own "54" is neither. That is why the correction block in
`docs/findings.md` certifies the table and the `ORACLE` pins and explicitly
*not* "the token figures beside them": this one does not hold, and a sentence
that certifies a figure which has stopped deriving is the failure this issue
exists to stop.

What moved is the paragraph below that table, and it moved twice: once for issue
#342 (2026-10-02), which corrected the table and left the sentence's own counts
behind, and again since. The stale figures are the ones §3c's own prose carries:

| figure | §3c reads | this tree | what counts it |
|---|---:|---:|---|
| addresses `xdata-symbols.csv` names | 101 | **258** | rows of the generated symbol table |
| named addresses the census reaches | 79 | **204** | of those, the ones the census reaches at all |
| ... touched by the main EC | 72 | **197** | of the 204, the ones the main EC's programs touch |
| ... touched only by the PD image | 7 | **7** | of the 204, the rest — unmoved |
| main-EC addresses the `.c` spells by symbol | 172 | **180** | `ORACLE["symbol_main_distinct"]` |

§3c states 101 and 79 as "79 of `registers.yaml`'s 101 addresses", 72 and 7 as
the split of those 79, and — in #342's nested parenthetical — 172 as the
symbol-spelled figure, having itself corrected an earlier 41. **Both the 101 and
the 258 are `registers.yaml`'s address union**, so the two are the same kind of
number and the distance between them is that the register file grew. At
`cda28a25` (2026-09-24), a tree whose `xdata-symbols.csv` held exactly 101 rows,
`registers.yaml` held 69 rows covering 101 addresses, so the old figure was
already an address count and not a row count. §3c has never read 101 rows.

The union exceeds the **204 rows** that produce it because 17 of those rows hold
an `addr` **list** — one register covering a run of bytes contributes one address
per element: `CTGP_DB_CTRL` is `addr: [0x0743, 0x0744, 0x0745, 0x0746]` and so
names four. The generated table carries one row per address, so a register added
as a 4-byte run moves the union by four. Any prose counting
"`registers.yaml`'s addresses" has to say which of the two it means — the
address union or the rows — because they differ by exactly that list run, and a
figure that moves when the file grows is a reading of this tree either way.

`NOT_IN_TREE` is what makes 204 the reached figure rather than the named one: 54
of the 258 are named and not reached, and that set carries a stated reason per
address rather than being a bare gap.

## The distinction §3c exists to keep, named as a set

§3c's correction insists that two facts are separate: an address being *in*
`xdata-symbols.csv`, and an address being **spelled** by that symbol in the
committed `.c`. Both are true of 197 addresses; only 180 are spelled. The 17 in
between are named, reached, and written something else — and they are what makes
the distinction a fact about this tree rather than a caveat.

The gap is not one mechanism but two, and the census's `spellings_by_program`
column tells them apart. That column and not `spelled_as`, because on a
`program=both` row `spelled_as` is the union of what *either* program writes and
so cannot separate the two halves — which is what §39 of `docs/findings.md`
records, and why the same file names `0x04A3` there as the worked case.

**Eight are written `DAT_EXTMEM_xxxx` by the main EC in the committed C.**
`0x047C` `MAILBOX_PAYLOAD_LATCH`, `0x070F` `EVENT_RING_INDEX`, `0x078E`
`XDATA_078E`, `0x09EF` `MAILBOX_PUBLISH_GUARD`, `0x09F0` `MAILBOX_DRAIN_COUNT`,
`0x09F1` `MAILBOX_INDEX`, `0x09F2` `MAILBOX_RING_SLOT0`, and `0x0A47`
`MAILBOX_PUBLISH_VALUE`. A name exists in the symbol table and the export
predates it: `build_ec_decompile.py` applies the table to the project *copy* the
export makes, so a name added afterwards does not reach the text until the next
export. **These eight are the ones a re-export moves**, and they are why §3c's
figure has to be read as a reading of the committed `.c` rather than of the
register file.

**Nine are reached only through a pair-accessor argument**, which is neither
spelling: `0x0402` `BAT_DESIGN_CAPACITY_0`, `0x0404` `BAT_FULL_CAPACITY_1`,
`0x0408` `BAT_DESIGN_VOLTAGE_1`, `0x040A`, `0x040C`, `0x040E`, `0x0410`, `0x043A`
(`XDATA_` each), and `0x04A3` `PACK_TEMP_DK_1`. No `DAT_EXTMEM_` token names any
of them *as the main EC spells them*, and the pair pass is what resolves them —
`bank1/B56C.c` reads `read_xdata_pair_to_r1r2(0x43a)`, a hex literal, and Ghidra
typed `0x0402` as `FUN_CODE_0402` at **ten** of those pair-accessor sites rather
than as an XDATA address at all: seven `read_xdata_pair_to_r3r4` arguments in
`bank1/AD85.c`, `B33B.c`, `B407.c`, `B40E.c`, `B415.c`, `B41C.c` and `B43B.c`, and three
*write* arguments — `write_r1r2_to_xdata_pair` in `bank1/DEE8.c` and `bank1/DEF1.c`,
and `write_r3r4_to_xdata_pair` in `bank1/DB0B.c`. The spelling occurs fifteen
times over in `ec/decompiled/`, but the other five are not sites: the function's
own banner and definition (`common/0402.c`, `common/0402.asm`) and one row each
in `index.csv` and `listing-index.csv`. The census therefore reaches addresses
the decompiler's own spelling never names.

`0x04A3` is the one address in this group that is in both programs, and its
`DAT_EXTMEM_04a3` token is real — `grep -rn DAT_EXTMEM_04a3 ec/decompiled/`
returns exactly one line, `pd/F22E.c`. That is the **PD image's** spelling. The
main EC's seven references to it are all `0x4a2` accessor arguments, which is why
its row carries `spellings_by_program` = `main-ec=pair-literal;pd=DAT_EXTMEM`
while `spelled_as` reads the union `DAT_EXTMEM+pair-literal`. §39 of
`docs/findings.md` already records this exact per-program split; it is named
here rather than restated as if it were new, and it is why filing `0x04A3` under
`DAT_EXTMEM` would claim a re-export moves an address the main EC never spells
that way.

**A re-export does not obviously move these**, and this write-up does not claim
it will. Renaming a `DAT_EXTMEM_` token is what the export path demonstrably
does; naming a *literal argument*, or overriding Ghidra's `FUN_CODE_` typing,
is a different question about `build_ec_decompile.py` that no committed output
answers. That holds for all nine, `0x04A3` among them — its `DAT_EXTMEM` token is
one the PD image writes, so a main-EC re-export is not what would reach it. That
is the honest state of it, and it is why the correction calls both
figures readings of the tree rather than properties of `registers.yaml`.

## What this does not say

Nothing here claims the 17 are absent, unused, or wrongly named. Each is
reached by the census and named by the symbol table; the gap is only about which
of the two spellings the committed `.c` happens to use. Reading any of them as
"the firmware does not use this" would invert the section's own correction.

No `status:` in `ec/annotations/registers.yaml` moved, and this change adds no
row to it. The suite below is what holds the counts.

## The suite

`ec/tools/test_findings_3c_census_figures.py` derives the census by calling into
`xdata_register_map` the way its existing suite does, and asserts **relations
rather than copied constants** — CLAUDE.md's rule that a test holds a property of
the tree and not a census of it. No expected figure is written into the suite, so
a branch that legitimately moves the census updates the prose and the suite
follows; what turns red is a *sentence* that no longer matches the census, and
the failure names the sentence rather than a number.

The `CPU_TEMP` correction above is held too, by the same rule and as the same
kind of relation: the count of `CPU_TEMP` left after `strip_comments()` equals
the `refs` cell `xdata-registers.csv` carries for `0x043E`. A figure the block
itself flags as the one that does not re-derive is the one most likely to drift
again, and a freshly corrected number with nothing watching it would repeat this
issue in miniature. The raw 56 is deliberately not compared to anything — it is
the outlier, and it moves whenever an annotation is reworded.

It also pins the §4a-4d invariant the correction depends on: the superseded
figures stay in §3c, visible, beside the correction. That is the first thing a
later tidy-up would break, and it is the reason the correction is a blockquote
beside the old text rather than an edit of it — `check_citation_lines.py` skips a
paragraph whose raw lines open with `>`, so a block full of deliberately
superseded figures is passed over rather than checked as if it were current.

Green:

```
$ python3 -m unittest ec.tools.test_findings_3c_census_figures
```

`bash tools/run-tests.sh` finds it without registration.

## Left for a follow-up

`ec/annotations/xdata-register-map.md` and
`ec/annotations/dsdt-ecmg-field-sweep.md` also carry §3c-era named/unnamed pairs
in the present tense. Both are long shared files that cite line numbers, the
issue scopes to §3c, and neither is wrong in the way §3c was. Named here rather
than edited in beside the correction.