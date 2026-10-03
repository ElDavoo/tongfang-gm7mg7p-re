# The `0x086x` page's site census, joined for every address

`ec/annotations/xdata-086x-dispatch-sites.csv` carries a ninth column,
`census`, holding what the C-level census says at each of the 114 `MOV DPTR`
sites the `0x086x` page sweeps. Issue #281 recorded that column for `0x0860`
and left the other fourteen addresses reading `not recorded` -- an explicit
"this work did not join the two methods here", which is not the same claim as
"there is nothing there" and is the failure the column exists to prevent. This
is that join, for the whole page.

The correspondence is committed as data, one file per address
(`ec/annotations/xdata-<addr>-census-sites.csv`), and
**`ec/tools/check_site_census.py --all`** holds each file to the sweep's own
`access` cell, to the census's own classification of every line it cites, and
to the per-bucket totals in the generated `ec/annotations/xdata-registers.csv`.
It exits non-zero on any disagreement.

```console
$ python3 ec/tools/check_site_census.py --all
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
      0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv --census-column --check
```

**Nothing here is a claim about what the EC does with any of these bytes.** It
is a census of two readings of the same instructions, and every verdict in it
is a statement about whether those two readings agree. No register `status:`
moves, no capture is opened, and no number below was measured on hardware --
there is no laptop and no Windows machine reachable from a GitHub-hosted
runner.

## What the join found

Every site resolves under one of four outcomes. Most addresses join cleanly;
four shapes did not fit the vocabulary #281 wrote, and each needed a name
rather than a workaround. The `0x0860` rows are unchanged.

### Shape 1 -- twelve sites where the sweep decoded an access and the decompile names no address

**`census-blind`.** Neither method is wrong and the two cannot be joined: the
sweep read or wrote the byte, and the C-level reader has no line for it.
`0x1F01` is the starkest case in the page -- four `write x1` sites, one
occurrence between them:

```
$ grep . ec/annotations/xdata-1F01-census-sites.csv
region,file_offset,census_state,census_bucket,census_count,census_refs
bank0,0x0D065,mapped,write,1,bank0/D065.c:17
bank0,0x0D6B5,census-blind,none,0,none
bank0,0x0FED4,census-blind,none,0,none
bank1,0x12742,census-blind,none,0,none
```

The one occurrence is `bank0/D065.c:17` -- `XDATA_1F01 = 0x20;` in
`init_1f01_1f06_1f07`, a routine that is three unconditional stores and no
branching. The three blind sites are elsewhere, and the listings say why.
`0x0D6B5` and `0x0FED4` are the first store of a four-store block
(`0x1F01`, `0x1F06`, `0x1F07`, and a fourth byte) that both listings carry as
plain `mov DPTR,#imm ; mov A,#imm ; movx @DPTR,A` triples. **Neither decompile
renders that block**, and the reason in each case is where that decompile
stops. `FUN_CODE_d673`'s body renders through the
`call_0ea2_twice_with_fa()` pair and the self-spin and then ends
(`bank0/D673.c:27-31`): the `0x08EB`, `0x1063` and `0x1F01` stores from
`0xD6A8` on are in `bank0/D673.asm:31-42` and in no `.c`. The helper that body
*does* call is not one that carries them -- `write_a_to_dptr_set_1f06` writes
`0x07FD` and then `0` to `0x1F06`, and takes its pointer argument as `0x7fd`
(`bank0/D673.asm:21-25`, `bank0/D6EA.c:19-20`).
`poll_1304_1500_dispatch_0083` shows its `0xFE` case as an
empty infinite loop, which its own annotation comment already records as "an
empty infinite loop rather than four stores followed by the self-spin". The
stores are in the image; the C-level reader has no line naming `0x1F01` there.
`0x12742` is different again: a bank-1 site whose runtime address `0xA742` is
spanned by no `bank1` `.asm` listing at all, so there is no decompiled text
covering it to read the store out of.

**Read this as a limit of the C-level reader, not as three dead sites.** The
sweep's `mov a,#0x20 ; movx @dptr,a` is the evidence the byte is written; what
is missing is a line of decompiled C that names `0x1F01` there. This is the
generalisation of the `0x0D31C` blind spot the page already records, where
*both* methods were blind together and the row could honestly say "nothing for
either method to see". Here only one is blind, and calling that agreement would
be a claim neither method supports.

The count is twelve sites, all in the two `0x1Cxx` addresses and the two
`0x1Fxx` ones:

| addr | sites | agree | `census-blind` |
|---|---:|---:|---:|
| `0x1C39` | 5 | 2 | 3 |
| `0x1C3A` | 5 | 2 | 3 |
| `0x1F01` | 4 | 1 | 3 |
| `0x1F07` | 5 | 2 | 3 |

The three `0x1C39` / `0x1C3A` blind sites are the case handlers at `0xD225`,
`0x0D24F` and `0x0D26F`, which §9 of the page already names as having no
function entry: the `0x7151` reader's `jmp @a+dptr` reaches them and no `lcall`
does, so no decompiled function covers them. The sweep found the stores; the
decompile has nothing to read them out of.

So the twelve fall into two kinds, and **"the C-level reader names no address"
is the only thing they have in common.** Four (`0x1F01` `0x0D6B5`, `0x1F01`
`0x0FED4`, `0x1F07` `0x0D6C1`, `0x1F07` `0x0FEE0`) sit inside a `.asm`
listing whose `.c` exists and does not name the address — the four-store block
described above. The other eight are sites **no `.asm` listing spans at all**:
the six `0x1C39`/`0x1C3A` case handlers at `0xD225`, `0x0D24F`, `0x0D26F`,
`0x0D22D`, `0x0D253` and `0x0D277`, and the two bank-1 sites `0x12742` and
`0x12749`. For those there is no decompiled text covering the site to read,
which is a different gap from a decompile that dropped a block.

Nothing here measures the decompiler, and no count of "instances across the
tree" follows from twelve on one page.

### Shape 2 -- eight `address-taken` occurrences, which name no direction

The census's `address-taken` bucket is not a direction. It is what
`xdata_register_map.classify()` returns for `&XDATA_0866`: Ghidra turned a
`MOV DPTR,#addr` whose byte is then used *through a pointer variable* into the
address-of expression, so the sweep sees a read and the decompile sees an
address taken. **One instruction, two vocabularies** -- the same shape as the
`passed-to-call` row #281 already had, and admitted only where the sweep's own
cell names no direction to contradict: a `DPTR handed to <call>` handoff, or a
window that is one bare `movx a,@dptr` and nothing else.

All eight pair with the four bank-0 handoffs and four bare-read sites the plan
expected, and `0x0866`'s three `&XDATA_0866` lines are at `9D9B.c:62`, `:112`
and `:180`, each immediately before a `sub_dptr_byte_from_0867` /
`sub_dptr_byte_from_0868` call or a `*pbVar4` store:

```
$ grep -h address-taken ec/annotations/xdata-086[6BE]-census-sites.csv
bank0,0x09DFB,mapped,address-taken,1,bank0/9D9B.c:62
bank0,0x09EE4,mapped,address-taken,1,bank0/9D9B.c:112
bank0,0x09FEB,mapped,address-taken,1,bank0/9D9B.c:180
bank0,0x09E03,mapped,address-taken,1,bank0/9D9B.c:65
bank0,0x09E10,mapped,address-taken,1,bank0/9D9B.c:70
bank0,0x09D59,mapped,address-taken,1,bank0/9CA6.c:84
bank0,0x09FF3,mapped,address-taken,1,bank0/9D9B.c:183
bank0,0x0A000,mapped,address-taken,1,bank0/9D9B.c:188
```

Four of them are at `DPTR handed to <call>` sites -- `0x086B` `0x09E03` and
`0x09E10`, `0x086E` `0x09FF3` and `0x0A000` -- and #281's table called a bucket
at a handoff an *error*, on the reasoning that "the decompile names no address,
so no occurrence can exist there". **That reasoning is false for these four.**
The decompile does name it, as `pbVar4 = &XDATA_086B;` on the line before the
call. The error clause survives for every other bucket, and is narrowed rather
than removed.

### Shape 3 -- three sites where the sweep's window stopped before the store

**`window-cut`,** and this one was not in the issue's list. `0x086B`'s three
clamps decode as:

```
9E41  90 08 6b  mov DPTR, #0x86b
9E44  e0        movx A, @DPTR
9E45  d3        setb CY
9E46  94 23     subb A, #0x23
9E48  40 03     jc 0x9e4d          <- the sweep's window ends here
9E4A  74 23     mov A, #0x23
9E4C  f0        movx @DPTR, A      <- the store, on the other arm
```

`walk_why()` stops at the `jc`, so the sweep's `access` cell records
`read x1` and the `0x23` store is not in it. The decompile names both
(`9D9B.c:80` reads it twice for the comparison, `:81` writes it). Each of these
three sites therefore carries **two** mapping rows -- a `read` and a `write` --
and the join is still per-occurrence, so both rows are checked and the site
counts once.

`verdict()` admits the extra row only where the window ends at a
**conditional** branch **and** the site has another row the sweep's direction
does name. Both conditions are narrow, and both are load-bearing. The second is
what stops this becoming a general way for a map to assert a bucket the sweep
contradicted: a site whose only row disagrees is still an error, window or no
window. The first is what makes "the window stopped early" mean something: a
window ending at a `ret`, `sjmp`, `ljmp` or `jmp` also stopped at control flow,
but with no fall-through arm left for an access to hide in, so the decode
simply reached the end of the straight-line run and an extra row there is a
plain disagreement. `ends_in_branch()` is the predicate, and it reads a tuple
of the conditional branches only rather than the wider set of everything
`walk_why()` stops on. Both halves are pinned by
`test_check_site_census.py::WindowCutRatherThanDisagreeing`, with the
`ret`-terminated case asserted as the error it is.

### Shape 4 -- the denominators differ in both directions

The plan noted this and it is worth stating because it is why the join cannot
be a per-site count comparison. `0x0869` has 8 sweep sites against 13
occurrences; `0x1F01` has 4 against 1. The sweep records one row per
`MOV DPTR`, and a C-level chain re-reads A without reloading DPTR: six
comparisons land on one `0x0860` row, and `0x09E22` -- a `0x0869` site in
`compute_level_blocks_086b_086c_086e` -- carries three
(`bank0/9D9B.c:75,76,77`) behind one `read x1` window that decodes as
`movx a,@dptr ; clr c ; subb a,r7 ; jnc +0x05`. The totals are compared per
bucket against `xdata-registers.csv` instead, which is what makes them close.

## The two corrections to the issue's arithmetic

Both are measurements against the committed CSV, not edits to the issue.

**The 105 rows are over 14 addresses, and the issue's parenthetical names 10 of
them.** "Every row of `0x0862` ... `0x086E`" accounts for 86. The other 19 are
`0x1C39` (5), `0x1C3A` (5), `0x1F01` (4) and `0x1F07` (5) -- four addresses
the issue never mentions, on the same page, in the same sweep, carrying
`not recorded` in exactly the same way. The tool's own docstring said 14, so
the docstring was right and the issue's enumeration was the incomplete half.
All fourteen are covered.

**There are 7 `DPTR handed to lcall` rows, not 8.** The issue's breakdown sums
to 106 against 105 rows: 58 `write x1`, 38 `read x1`, 1 `read x1, write x1`,
1 `write x1, walks 2 consecutive bytes (inc dptr)` is 98, leaving 7 handoffs.
They are `0x0867` `0x25DFF`; `0x0868` `0x25E30` and `0x25E59`; and `0x086B`
`0x09E03`, `0x09E10`; `0x086E` `0x09FF3`, `0x0A000`. **Three are `pd-image`**
and so are `other-program` before the bucket is ever looked at; **four are
bank-0**, and those four are exactly the `address-taken` rows of shape 2 --
which is why the verdict is not `error` everywhere.

## Item 3 re-decided: the `0x0862` / `0x086D` writer sentence survives

`xdata-086x-dispatch.md` §11 item 3 reads "`0x0862` and `0x086D` have no writer
this method can see". **It survives the join, as a finding**, and the join
confirms it from the other side: both addresses' per-bucket totals close with
`write 0`, which the check would reject otherwise.

What it must keep is "this method can see". Issue #250's conditional
computed-DPTR writer is not a `MOV DPTR` site, so **neither** the sweep nor
the C-level census can reach it, and the join is not evidence against it. A
reader who saw the census say `write 0` for `0x0862` and concluded the byte has
no writer would be reading past the end of both methods. Whether that writer
ever fires is still §10's live step, still a human's, and still unrun.

## Per-address results

Each line is `check_site_census.py --all`'s own output; `refs` is
`xdata-registers.csv`'s count for that address, and every occurrence is
accounted for exactly once.

| addr | sites | agree | blind | window-cut | unchecked | refs |
|---|---:|---:|---:|---:|---:|---:|
| `0x0860` | 9 | 7 | 0 | 0 | 2 | 17 |
| `0x0862` | 5 | 3 | 0 | 0 | 2 | 3 |
| `0x0865` | 10 | 10 | 0 | 0 | 0 | 10 |
| `0x0866` | 12 | 12 | 0 | 0 | 0 | 13 |
| `0x0867` | 15 | 9 | 0 | 0 | 6 | 10 |
| `0x0868` | 11 | 9 | 0 | 0 | 2 | 10 |
| `0x0869` | 8 | 8 | 0 | 0 | 0 | 13 |
| `0x086A` | 2 | 2 | 0 | 0 | 0 | 3 |
| `0x086B` | 14 | 14 | 0 | 3 | 0 | 22 |
| `0x086D` | 2 | 2 | 0 | 0 | 0 | 2 |
| `0x086E` | 7 | 7 | 0 | 0 | 0 | 7 |
| `0x1C39` | 5 | 2 | 3 | 0 | 0 | 3 |
| `0x1C3A` | 5 | 2 | 3 | 0 | 0 | 3 |
| `0x1F01` | 4 | 1 | 3 | 0 | 0 | 1 |
| `0x1F07` | 5 | 2 | 3 | 0 | 0 | 2 |

The twelve `other-program` sites are PD-image and carry no direction by
construction -- the two programs have separate XDATA maps. The census is still
scanned for occurrences there, so a PD occurrence appearing one day would be
reported as unaccounted rather than quietly ignored.

## What this opens

**The `census-blind` shape is now named and counted on this page; how many
instances exist across the tree is still not known.** This work swept fifteen
addresses and read the decompiled functions covering them. It did not ask
whether other addresses have sites where the sweep decoded an access and the
decompile names none, which is `xdata-086x-dispatch.md` §11's last numbered
item and remains open. This names twelve instances of a shape the page already
had one instance of; it does not bound the population.

**`address-taken` is a pointer, not a direction, and that is now load-bearing
in the tool rather than a note.** #281's table called it an error wherever it
appeared, and it had never appeared. Eight occurrences now depend on the
narrowing, and `0x0866`'s three are the case that shows why: the sweep reads a
byte and Ghidra writes `&XDATA_0866`, and both are describing
`mov DPTR,#0x866 ; movx A,@DPTR`.

**`0x086B`'s clamp stores were invisible to the sweep, not absent.** The three
`window-cut` rows are real `movx @DPTR,A` instructions at `0x9E4C`, `0x9E6A`
and `0x9E88`, each storing a constant through a DPTR the site loaded and each
behind a conditional branch. A reader taking the sweep's `access` column alone
would see three reads and no stores. Nothing here says what the clamps are *for*
-- that is §10's live question -- but the store existing at all is now recorded
rather than left to be inferred from an absent column.

## Reproducing it

Everything above runs offline against committed inputs: no firmware image
beyond the one `--check` reads, no Ghidra, no network, no hardware.

```console
$ python3 ec/tools/check_site_census.py --all
$ python3 ec/tools/test_check_site_census.py
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
      0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv --census-column --check
$ python3 ec/tools/xdata_register_map.py --check
```

The third command is what makes "no `not recorded` cell is left" a check rather
than a promise: it regenerates the sites table from the image and the mapping
files and diffs it against the committed one, so a hand-typed `census` column
would go red. `check_site_census.py::check_cells()` holds the same column
against the mapping a second time, from the other direction, so neither file can
drift from the other unnoticed.
