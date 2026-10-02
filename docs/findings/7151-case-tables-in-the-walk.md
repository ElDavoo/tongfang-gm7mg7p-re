# The main EC's `0x7151` dispatcher carries a case table inline, so the walk was decoding it as instructions (issue #1257)

**The gap this closes.** `disasm8051.py` had one named exception to "walk
forward one instruction at a time": `INLINE_ARG_CALLS`, a fixed-width argument
block at the PD image's `0x104D`. The main EC's `switch_case_dispatch` at
`0x7151` is the same *kind* of thing in a different shape — a call whose data
sits inline in the code stream — and it was not in that table, so
`find_indirect_xdata.py` and `trace_xdata_refs.py` walked straight through
every one of its tables and decoded the entries as instructions. Its own
docstring claimed "0 times in the EC image" about inline data after a call,
which was true of the `0x104D` *idiom* and read as a claim about the main EC.
It is now scoped to `0x104D`, and `0x7151` has its own entry.

**Nothing was observed and no status moved.** Every figure below is a static
reading of the committed `ec/firmware/GMxMGxx_11.800`. No hardware and no
Windows machine was involved, no register was read back, and no `status:` in
`ec/annotations/registers.yaml` moves in either direction — a static scan is
not a behaviour. `0x07B9`'s standing case and `0x07D0`'s `DO-NOT-WRITE-BLIND`
are untouched, and §5 says why this change *weakens* the negative they sit
beside rather than strengthening it.

## 1. Reproducing this

```console
$ python3 ec/tools/disasm8051.py --self-test
$ python3 ec/tools/find_indirect_xdata.py ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/find_indirect_xdata.py ec/firmware/GMxMGxx_11.800 --csv \
        > ec/annotations/indirect-xdata-sites.csv
$ python3 ec/tools/find_indirect_xdata.py ec/firmware/GMxMGxx_11.800 --check
$ python3 -m unittest test_disasm8051_case_tables.py
$ python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --self-test
```

The population and the `P2` census are `find_indirect_xdata.py`'s own output
and are not restated as a number anywhere else; §3 and §4 are readings of what
that run prints, and `--check` is what holds the per-site table.

## 2. The rule, and where it comes from

`ec/decompiled/common/7151.c` is the reader, hand-decoded and named
`switch_case_dispatch`. Its comment is the whole claim: *"it pops the return
address the preceding lcall pushed into DPTR to get the inline table's address
and takes the selector in A; 15 lcall sites name it and it dispatches through
`jmp @a+dptr` at 0x716B"*. The loop is the extent rule:

```c
for (pcVar1 = (char *)CONCAT11(uStackX_0,in_stack_000000ff);
    (*pcVar1 != '\0' || (pcVar1[1] != '\0')); pcVar1 = pcVar1 + 3) {
  if (pcVar1[2] == param_1) goto LAB_CODE_7161;
}
pcVar1 = pcVar1 + 2;
LAB_CODE_7161:
  (**(code **)pcVar1)();
```

So: **3-byte entries — a 2-byte `ajmp` target plus a selector byte compared
against A — until an entry head reads `00 00`, then the 2 bytes after it as
the default.** The table is `3n + 4` bytes for `n` entries, and `n` is not
knowable without scanning. That is why this is a second table and a second
function rather than a second row in `INLINE_ARG_CALLS`: a fixed width cannot
express a terminator.

The committed `r2` transcript for the `0x00DD3` table shows the reader's own
grouping, and shows why the walk must resume *after* the default rather than on
it — the byte at `table_end` is the table's own case-`0x02` target, so it is
code, and a walk that stepped onto the default would re-frame the walk that
follows:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x0dd6; px 32' /tmp/bank0.bin
- offset -   0 1  2 3  4 5  6 7  8 9  A B  C D  E F  0123456789ABCDEF
0x00000dd6  0df5 020d f704 0df9 060d fb08 0dfe 0a0e  ................
0x00000de6  010c 0e04 0e0d f910 0e0a 1200 000e 0d80  ................
```

Grouped the way the reader groups it: `0df5 02 | 0df7 04 | 0df9 06 | 0dfb 08
| 0dfe 0a | 0e01 0c | 0e04 0e | 0df9 10 | 0e0a 12 | 0000 | 0e0d` — nine
entries, terminator at file `0x00DF1`, default `0x0E0D`, and the table ends at
`0x00DF5`. `ec/annotations/bank-call-audit.md` §10.4 has this read by hand,
along with the `0x08662` table.

**The two edges, and why the scan declines rather than guesses.** A table the
buffer does not hold whole is no table, and neither is one whose terminator
does not arrive within `MAX_CASE_ENTRIES` — the cap is the same one
`decode_index_table.py` uses for the same reason, that a `lcall` byte pair
inside data would otherwise scan to the end of the buffer. `inline_arg_len()`'s
"a block the buffer does not hold whole is no block" contract is restated for
the new edge rather than assumed: a scan has a way to fail that a fixed width
does not, so it needs its own.

## 3. The rule is pinned against a second derivation of the same 15 tables

`ec/annotations/index-table-spans.csv` is committed input, produced by
`decode_index_table.py` — which finds the reader from its opcode prologue
(`d0 83 d0 82 f8`), walks the same `00 00` rule, checks each table for
well-formedness, and **never calls the new code**. So the two agreeing extent
for extent is corroboration rather than a restatement, and
`test_disasm8051_case_tables.py` holds them to each other: a drift in either
side fails there rather than passing to the next reader.

The scan reproduces every committed site, every entry count and every
`table_end`:

```console
0x00DD3   31 byte(s)   9 entries  ends 0x00DF5  (csv: 0x00DF5, 9 entries)
0x04064   49 byte(s)  15 entries  ends 0x04098  (csv: 0x04098, 15 entries)
0x041EE   46 byte(s)  14 entries  ends 0x0421F  (csv: 0x0421F, 14 entries)
0x0424B  151 byte(s)  49 entries  ends 0x042E5  (csv: 0x042E5, 49 entries)
0x08035   28 byte(s)   8 entries  ends 0x08054  (csv: 0x08054, 8 entries)
0x08662   28 byte(s)   8 entries  ends 0x08681  (csv: 0x08681, 8 entries)
0x0918A   34 byte(s)  10 entries  ends 0x091AF  (csv: 0x091AF, 10 entries)
0x09284   25 byte(s)   7 entries  ends 0x092A0  (csv: 0x092A0, 7 entries)
0x0A34A   25 byte(s)   7 entries  ends 0x0A366  (csv: 0x0A366, 7 entries)
0x0A682   25 byte(s)   7 entries  ends 0x0A69E  (csv: 0x0A69E, 7 entries)
0x0D148   40 byte(s)  12 entries  ends 0x0D173  (csv: 0x0D173, 12 entries)
0x0D435   76 byte(s)  24 entries  ends 0x0D484  (csv: 0x0D484, 24 entries)
0x0DDBB   52 byte(s)  16 entries  ends 0x0DDF2  (csv: 0x0DDF2, 16 entries)
0x0EBDC   28 byte(s)   8 entries  ends 0x0EBFB  (csv: 0x0EBFB, 8 entries)
0x0F254   25 byte(s)   7 entries  ends 0x0F270  (csv: 0x0F270, 7 entries)
```

`decode_index_table.py --self-test` is unmoved by this change — it never
imports `case_table_len()` — and the independent derivation still produces the
committed spans byte for byte.

**The walk now steps over a table rather than into it.** The site the issue
named is the clearest, because `ec/annotations/ghidra-functions.csv`'s
`bank0,F239` row already says in its own comment that the bytes the linear
listing shows there are table data reached through `0x7151`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x0f254; pd 3; px 32' /tmp/bank0.bin
            0x0000f254      127151         lcall 0x7151
            0x0000f257      f2             movx @r0, a
        ┌─< 0x0000f258      7000           jnz 0xf25a
0x0000f254  1271 51f2 7000 f2f8 01f3 8e03 f3be 04f3  .qQ.p...........
0x0000f264  e106 f3fd 07f4 1408 0000 f42b 900e 00e0  ...........+....

$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0f251 --runtime 0x0f251 -n 3
0xf251  0e       inc  r6
0xf252  01e0     ajmp 0xf0e0
0xf254  127151   lcall 0x7151
0xf257  f27000f2f801f38e03f3be04f3e106f3fd07f414080000f42b case table: 25 bytes
```

Grouped as the reader groups it: `f270 00 | f2f8 01 | f38e 03 | f3be 04 |
f3e1 06 | f3fd 07 | f414 08 | 0000 | f42b` — seven entries, cases `0x00`-`0x08`
with a gap, terminator at `0x0F269`, default `0xF42B`, table ending at
`0x0F270`, where `90 0e 00` is `mov dptr,#0x0e00`. Six of the seven entries
have a lead byte spelling `movx @r0,a` or `movx @r1,a`, and the old walk
reported four of them as `bank0` sites — `0x0F257`, `0x0F25A`, `0x0F260` and
`0x0F266`, entry heads 0, 1, 3 and 5.

## 4. What the corrected walk changes, and what it does not

`--check` was red before the CSV was regenerated and is green after, and the
diff is **deletions only** — the corrected walk removes rows and adds none:

```console
$ python3 ec/tools/find_indirect_xdata.py ec/firmware/GMxMGxx_11.800 --check
ec/annotations/indirect-xdata-sites.csv: this run reproduces it byte for byte (85 lines)
```

Seven rows leave the table, and each is inside a committed table span:
`0x04075`/`0x04078` in `0x04064`'s, `0x0D46F` in `0x0D435`'s, and
`0x0F257`/`0x0F25A`/`0x0F260`/`0x0F266` in `0x0F254`'s. No surviving row's
framing changed. Per-region, per-encoding and control numbers are the
summary's, and `ec/annotations/indirect-xdata-sites.md` §2/§3 are corrected to
match this run.

**The `converges_from()` edit reaches further than `find_indirect_xdata.py`'s
own walk, and the committed tables it reaches are regenerated too.**
`converges_from()` is the shared anchor-walk, and adding `case_table_len()` to
its stepping rule changes the framing evidence for *every* site whose backward
window crosses one of the fifteen tables — not only for the two censuses this
write-up re-derives. `audit_call_targets.py` imports it and emits three
committed CSVs, so all three were regenerated against a fresh run rather than
edited:

```console
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --csv \
        > ec/annotations/bank-call-targets.csv
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --paged-csv \
        > ec/annotations/bank-paged-call-targets.csv
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --relative-csv \
        > ec/annotations/bank-relative-branch-targets.csv
```

Only `frame_onto`/`frame_over` move in them: comparing every other column by
name, no `bucket`, `target`, `in_region`, `earlier_record` or tie-break changed,
so the corrected walk moved framing evidence and nothing else. Each of the
three reproduced its committed file byte for byte before this change, which is
what makes the diff attributable to the walk rather than to drift.

`ec/annotations/bank-call-audit.md` quoted one of the moved scores — `0x0803B`
at 24 of 24 anchors, in a transcript and twice in prose — and is corrected in
place per [`../findings.md`](../findings.md) §4a-4d rather than silently
edited. The site's score fell because it is a byte of the `0x08035` table,
which is the conclusion that audit already drew; the argument it was carrying
("a high frame score is not evidence of a branch") is now carried by §4's
`0x00686`, which the corrected walk leaves alone.

The census tables that read the PD image are untouched, and so is everything
derived from them: `case_table_len()` is keyed on `lcall 0x7151`, which the PD
image does not contain, so it cannot fire there. That is the same
"absent from one program, not from the 8051" reading the PD half of this work
rests on, and it is why `pd-direct-offset-sites.csv`, `pd-entry-forms.csv` and
the `pd-index-*` tables still reproduce byte for byte.

**The population going down is not a cleaner negative — it is a weaker one.**
`indirect-xdata-sites.md` §3a showed the anchored walk decoding a data table at
`0x05C9A` as twelve `mov p2,register` instructions, and said the other three
rows "are not independently corroborated either way." This is a second,
independent instance of the same failure, in a different region and by a
different mechanism, and it is the reason the negative that rests on the
population cannot be read as a fact about the firmware. The corrected walk
removes *bytes of tables* from the population; it does not verify that the
bytes left are code. §5 below is the part that matters most, and it is why §3a
of that page now records the survivors as data-shaped too rather than leaving
them uncorroborated.

## 5. The two survivors look like data too, by a second route

`find_indirect_xdata.py`'s summary reports the `P2`-writing encodings the
corrected anchored walk reaches. `mov p2,register` is unchanged (it is the
`0x05C9A` table, outside every `0x7151` span); `inc p2` and one
`mov p2.x,carry` row leave with the tables that held them; **two single-site
rows survive, both in `bank1`: `mov p2.x,carry` at `0x14C8F` and
`mov p2,direct` at `0x16CA3`.** These are the question the negative rests on,
and the arithmetic says they are table bytes of a *different* kind — an
ascending-step data run, which is the same shape `indirect-xdata-sites.md` §3a
established for the twelve.

**`0x14C8F` is a byte of an ascending run.** The bytes from `0x14C87` step
`0x0E` or `0x0F` each — a stride a table of addresses would not have and a
code stream very much would not either:

```console
$ python3 -c "
d = open('ec/firmware/GMxMGxx_11.800', 'rb').read()
run = d[0x14C87:0x14C92]
print('run  ', ' '.join('%02x' % b for b in run))
print('steps', [run[i+1] - run[i] for i in range(len(run) - 1)])
print('walk decodes 0x14C8F as', d[0x14C8F:0x14C91].hex(' '), '=', 'mov p2.0,c')
"
run   1d 2b 3a 49 57 66 74 83 92 a0 af
steps [14, 15, 15, 14, 15, 14, 15, 15, 14, 15]
walk decodes 0x14C8F as 92 a0 = mov p2.0,c
```

`92 a0` is the run's ninth and tenth bytes, and `0x14C92`-`0x14C94` continues
it (`bd cc dc`, stepping 0x0F and 0x10 — the run is already off `0x0E`/`0x0F`
by then, the `0x0E` being the step *into* `bd`). The `mov p2.0,c` is the walk
reading two bytes of a one-byte-per-step sequence as an instruction.

**`0x16CA3` sits inside a 16-bit ascending run.** Read as
little-endian words from `0x16CA1`, the values are `0x1940 0x1985 0x19A0
0x19BB 0x19D5 0x1AF0 0x1A0B 0x1A25`. The low byte steps by `0x1A`/`0x1B` for
the middle of the run, with a high byte that crosses `0x19`→`0x1A` once — but
the sequence is not a uniform stride, and the deltas below show where it stops
being one: the first step is `0x45` and one step wraps negative. A run that
mostly steps by a near-constant `0x1A`/`0x1B` is a record table's shape and not
an instruction stream's:

```console
$ python3 -c "
d = open('ec/firmware/GMxMGxx_11.800', 'rb').read()
lo = 0x16CA1
print('bytes ', d[lo:lo + 16].hex(' '))
print('LE    ', ' '.join('%04x' % (d[i] | d[i+1] << 8) for i in range(lo, lo + 16, 2)))
print('low   ', [d[i + 2] - d[i] for i in range(lo, lo + 14, 2)])
print('walk decodes 0x16CA3 as', d[0x16CA3:0x16CA6].hex(' '), '=', 'mov 0xa0,0x19')
"
bytes  40 19 85 19 a0 19 bb 19 d5 19 f0 1a 0b 1a 25 1a
LE     1940 1985 19a0 19bb 19d5 1af0 1a0b 1a25
low    [69, 27, 27, 26, 27, -229, 26]
walk decodes 0x16CA3 as 85 19 a0 = mov 0xa0,0x19
```

The `85 19 a0` is the whole `0x1985` record plus the low byte of the `0x19A0`
record — one instruction assembled out of the tail of one word and the head of
the next. `P2_WRITERS` reads the *third* byte as the `P2` destination, which
is why the row exists: `0xa0` is the low byte of a word, not an SFR write.

**This is an indication with the arithmetic shown, not a verdict**, and the
distinction is the one CLAUDE.md's calibration rule turns on. What is
established: the two bytes/three bytes are part of an ascending-step run, by
the same reading that established the twelve. What is not: that the runs are
records rather than code, that no `P2` write happens there, or that the whole
`0x16C7D`-`0x16CD8` region is one table — a run of data can pass every
well-formedness test, which is what `bank-call-audit.md` §10.2 says of the
`0x7151` tables themselves. **The `data-regions.yaml` question is opened here
rather than settled**, and §6 is where it belongs.

## 6. What this does not establish

- **It does not establish that a `P2` write is impossible in these windows; it
  makes the negative weaker.** "No `P2` write in the main-EC windows" now
  rests on a smaller population none of whose sites was ever checked for a
  `P2` write being real code, and both surviving single-site rows are
  candidates for being data by §5's arithmetic. A smaller population of
  unexamined sites is not a cleaner result. This is the consequence of the
  change and it belongs in the pull request rather than in a footnote.
- **A `00 00` that happens to appear is not proof of a table.** The rule is
  keyed on the *call* — fifteen `lcall 0x7151` sites, all in the main EC — and
  a `00 00` outside them is data or an operand, and the walk says nothing
  about it.
- **It does not establish that a table byte is never executable.** It
  establishes that a linear walk cannot know that, and that these bytes are
  outside a 3-byte-entry structure the reader owns.
- **It says nothing about what the tables select.** The reader dispatches to
  the entries' targets; nothing here reads a handler, and
  `bank-call-audit.md` §9/§10 already say the `0x8038` family's handlers were
  not followed.
- **It touches no `status:` row, in either direction, and no hardware.** The
  `0x07B9` / `0x07D0` questions need a human at the machine and stay open; see
  `docs/MISSION.md`'s hardware rule.
- **It is the main-EC counterpart of #1141 and #1122/#1119/#1123**, the
  PD-image `0x104D`/`0x11C2`/`0x11EF` dispatchers. Same idiom, different
  program, different file: one named entry and one terminator scan here, three
  widths there. The family is stated so the two are not done twice.
  `pd_inline_arg_sites.py` needed no change — its refusal at `:420-422` fires
  only when `len(INLINE_ARG_CALLS) != 1`, and a *sibling* table leaves that at
  one — and `test_disasm8051_inline_args.py` stays green unchanged, which is
  the proof that this mechanism did not reach into the PD one.
