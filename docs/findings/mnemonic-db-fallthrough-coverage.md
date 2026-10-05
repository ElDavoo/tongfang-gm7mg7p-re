# The 29 byte values `disasm8051.mnemonic()` printed as `db`, and the one that still is

`mnemonic()` fell through to `return f"db   0x{op:02x}"` for 29 opcode values.
The MCS-51 map assigns 28 of them; `0xA5` is the one it does not. All 28 now have
a name, and this document is the record of which name came from where — because
the ones that could be transcribed from the committed Ghidra listings were, and
the ones that could not are marked as stated from the manual instead. The `db`
fall-through is reachable for `0xA5` alone, and `disasm8051.py` now says so at
the return.

The issue this came from (#1153) measured 35 reaching the fall-through and 34
assigned. That was true when written; `direct-address-opcode-rendering.md` landed
six names since, and the count on the tree this starts from is 29. The issue's
numerator reconciles exactly against the numbers below — 292 on the 29 that
remain, plus the 76 the six carry, is the 368 it reported — so nothing was lost
by those six. Its *denominator* does not reconcile, and should not: the 45,643
instruction starts it counted was the corpus at an earlier base, and listings
have been seeded since.

## The set, and the 28/1 split

One command, no image, no Ghidra and no r2. **This is what it prints now, after
the change;** it read `29 ['0xa5']` on the tree this branch starts from, which is
the state the paragraph below describes:

```console
$ python3 -c 'import sys;sys.path.insert(0,"ec/tools");import disasm8051 as D,opcode_coverage as C;db=[o for o in range(256) if D.mnemonic(bytes([o]+[0]*7),0).startswith("db")];print(len(db),[hex(o) for o in db if not C.MCS51_LEN[o]])'
1 ['0xa5']
```

29 values reached the fall-through before this change, and `MCS51_LEN` — the
manual transcription `opcode_coverage.py` holds, and the table both `UNASSIGNED`
sets cite as their source — assigned 28 of them a length and left `0xA5` at 0.
That 28/1 split is what this work had to preserve, and it is preserved: the
values that reached `db` and that the manual assigns are now the same set, which
is the empty one, and `0xA5` is still the single value the map leaves open. The
28 named values carried **292** of the instruction starts in `ec/decompiled/` on
that tree.

Both figures are measurements over committed firmware rather than over this
repository, and both move when a listing is seeded.
`python3 ec/tools/opcode_coverage.py --coverage --summary` prints the denominator
for the tree as it is now, and the per-value split below is what it sums.

## Every name, and what it was decided from

The oracle is the committed listings, read from disk rather than reconstructed
from the decoder — the discipline `disasm8051.BIT_SITES` and
`TEXTBOOK_BIT_SITES` both record, for the reason `direct-address-opcode-rendering.md`
states: an encoding derived from the tool under test asserts nothing.

**Every one of the 28 has at least one listing start naming it.** That was not
obvious before measuring, and it settles the method question the issue left open:
there is no value here that had to be named from the manual because the corpus
had nothing to transcribe from. (Issue #1153 predicted that four would be. They
are not — `0x72`, `0x82`, `0x86`/`0x87`, `0xA6`/`0xA7` and `0xB6`/`0xB7` all
appear at instruction starts — so the `TEXTBOOK_BIT_SITES` shape is not needed
here and was not used.)

| op | MCS-51 | len | renders as | listing row it was read from |
|---|---|---:|---|---|
| `0x06` | `INC @R0` | 1 | `inc  @r0` | `ec/decompiled/bank0/B065.asm` — `inc @R0` |
| `0x07` | `INC @R1` | 1 | `inc  @r1` | `ec/decompiled/bank0/8048.asm` — `inc @R1` |
| `0x16` | `DEC @R0` | 1 | `dec  @r0` | `ec/decompiled/bank0/2BD5.asm` — `dec @R0` |
| `0x17` | `DEC @R1` | 1 | `dec  @r1` | `ec/decompiled/bank0/D091.asm` — `dec @R1` |
| `0x26` | `ADD A,@R0` | 1 | `add  a,@r0` | `ec/decompiled/bank1/E9CE.asm` — `add A, @R0` |
| `0x27` | `ADD A,@R1` | 1 | `add  a,@r1` | `ec/decompiled/bank1/E9CE.asm` — `add A, @R1` |
| `0x36` | `ADDC A,@R0` | 1 | `addc a,@r0` | `ec/decompiled/bank0/D091.asm` — `addc A, @R0` |
| `0x37` | `ADDC A,@R1` | 1 | `addc a,@r1` | `ec/decompiled/bank0/D091.asm` — `addc A, @R1` |
| `0x46` | `ORL A,@R0` | 1 | `orl  a,@r0` | `ec/decompiled/bank1/EAC3.asm` — `orl A, @R0` |
| `0x47` | `ORL A,@R1` | 1 | `orl  a,@r1` | `ec/decompiled/common/5A66.asm` — `orl A, @R1` |
| `0x56` | `ANL A,@R0` | 1 | `anl  a,@r0` | `ec/decompiled/bank1/EAC3.asm` — `anl A, @R0` |
| `0x57` | `ANL A,@R1` | 1 | `anl  a,@r1` | `ec/decompiled/bank1/8504.asm` — `anl A, @R1` |
| `0x66` | `XRL A,@R0` | 1 | `xrl  a,@r0` | `ec/decompiled/bank0/A312.asm` — `xrl A, @R0` |
| `0x67` | `XRL A,@R1` | 1 | `xrl  a,@r1` | `ec/decompiled/bank0/A312.asm` — `xrl A, @R1` |
| `0x96` | `SUBB A,@R0` | 1 | `subb a,@r0` | `ec/decompiled/bank0/D434.asm` — `subb A, @R0` |
| `0x97` | `SUBB A,@R1` | 1 | `subb a,@r1` | `ec/decompiled/common/6A02.asm` — `subb A, @R1` |
| `0x72` | `ORL C,bit` | 2 | `orl  c,<bit>` | `ec/decompiled/pd/A890.asm` — `orl CY, 0x20` |
| `0x82` | `ANL C,bit` | 2 | `anl  c,<bit>` | `ec/decompiled/bank0/8048.asm` — `anl CY, 0x31` |
| `0x76` | `MOV @R0,#data` | 2 | `mov  @r0,#0x..` | `ec/decompiled/common/012F.asm` — `mov @R0, #0x2` |
| `0x77` | `MOV @R1,#data` | 2 | `mov  @r1,#0x..` | `ec/decompiled/common/6A02.asm` — `mov @R1, #0xc0` |
| `0xA6` | `MOV @R0,direct` | 2 | `mov  @r0,0x..` | `ec/decompiled/bank0/A663.asm` — `mov @R0, 0x9e` |
| `0xA7` | `MOV @R1,direct` | 2 | `mov  @r1,0x..` | `ec/decompiled/bank1/E722.asm` — `mov @R1, 0x89` |
| `0x86` | `MOV direct,@R0` | 2 | `mov  0x..,@r0` | `ec/decompiled/bank0/8653.asm` — `mov 0x81, @R0` |
| `0x87` | `MOV direct,@R1` | 2 | `mov  0x..,@r1` | `ec/decompiled/pd/0D0D.asm` — `mov B, @R1` |
| `0xB6` | `CJNE @R0,#data,rel` | 3 | `cjne @r0,#0x..,<rel>` | `ec/decompiled/bank1/E9CE.asm` — `cjne @R0, #0x1c, 0xe9e6` |
| `0xB7` | `CJNE @R1,#data,rel` | 3 | `cjne @r1,#0x..,<rel>` | `ec/decompiled/bank1/EAC3.asm` — `cjne @R1, #0x33, 0xebac` |
| `0xD4` | `DA A` | 1 | `da   a` | `ec/decompiled/bank0/D434.asm` — `da A` |
| `0xF4` | `CPL A` | 1 | `cpl  a` | `ec/decompiled/bank0/D091.asm` — `cpl A` |

Three of the renderings differ from the listing's spelling, and each difference
is this module's own convention rather than a disagreement about the
instruction: registers are lower-case (`@R0` → `@r0`), bit operands go through
`bit_name()` (`0x20` → `0x23.0`), and mnemonics are padded to four columns
(`da A` → `da   a`) so the `da`-that-is-also-two-hex-digits problem
`opcode_coverage.LINE_RE`'s padded byte column exists for cannot arise. The
suite that holds these reads each listing's *first token* live off disk and
compares only that, which is the instruction name and nothing else.

Grouped as they are coded rather than as 28 separate cases: the `X A,@Ri`
ladder is one keyed expression over twelve opcodes (one row per operation, the
register in the low bit), and `0xB6`/`0xB7` extend the existing `0xB8`-`0xBF`
`CJNE Rn` range rather than adding a shape. The `@Ri` ladder is keyed on the
twelve opcode values rather than on a mask like its `Rn` sibling, because the
low two bits of those rows are not free — `0x21`, `0x41` and `0x61` are `AJMP`,
`0x31` and `0x51` are `ACALL`, and `0x90`/`0x91` are `mov direct,#data` and
`ACALL` — so a `(op & 0x0F) < 2` shortcut would swallow six paged forms.

**`OPCODE_LEN` is unchanged for every one of the 28**, which is why this is a
naming job and not a framing one, and it is held by
`test_disasm8051_db_fallthrough.py` against `MCS51_LEN` rather than against a
copy of itself.

## `0xA5`: no name, and why

The manual assigns `0xA5` no instruction, so there is no name to give it. Two
independent routes agree that it is not an instruction: no committed listing
places it at an instruction start (`opcode_coverage.py --coverage --summary`
reports it under *not found by this method*, with `0xC1`), and `r2 -a 8051`
prints `invalid` for it — `printf '\xa5' > /tmp/a5.bin && r2 -a 8051 -q -c 'pd 1 @ 0'
/tmp/a5.bin`, which is the same reading `docs/findings/opcode-table-coverage.md`
already records. Neither is "absent" — `OPCODE_LEN` still gives it a length,
so a walk landing on one is a byte this firmware uses as something other than an
opcode, which is the standing caveat `ec/annotations/registers.yaml` states for
a static scan. `disasm8051.py` now says this at the `db` return rather than
leaving the fall-through looking like an oversight.

`0xA5` is also the reason the `db` return stays. A decoder that printed nothing
here would satisfy "these bytes are not data" vacuously.

## `0xA6`/`0xA7`: the `#`, and the one row that disagrees

The manual assigns this row `MOV @Ri,direct` at 2 bytes — the same reading the
committed listings give, and the `#data` form belongs to `0x76`/`0x77` directly
above in the encoding. Reading `#data` onto `0xA6`/`0xA7` would both duplicate an
existing opcode and break the map's symmetry with `0x86`/`0x87`
(`MOV direct,@Ri`), which the listings read the other way round.

Two things make the listings' missing `#` evidence rather than decoration. The
exporter does print `#` for an immediate — the same listings write `0x76` as
`mov @R0, #0x2` at `ec/decompiled/common/012F.asm` — so the omission is the tool
distinguishing the two forms rather than a formatting habit. And it resolves the
byte to an SFR *name*, which an immediate byte would never be given:
`ec/decompiled/pd/0D70.asm` has `a7 f0` at `0D81` as `mov @R1, B`, and `B` is
`0xF0`, an SFR in `BIT_SFR`.

**The disagreement is not between the manual and the listings, and this document
previously said it was.** It is between the manual and one mis-transcribed row —
the `0xa6`/`0xa7` row of the set table in `opcode-table-coverage.md`'s
text-comparison section, which is corrected in place. Three committed tools
already carried `direct` for these two values before this change, each in a
table of its own: `iram_boot_sites.RI_TABLE` puts the `#` on `0x76`/`0x77` and
not on `0xA6`/`0xA7`, `dptr_rebuild_forms.py` carries `mov  @r0,direct` and
`mov  @r1,direct`, and `verify_gap_text.py` annotates both rows
`# MOV @Ri,direct` in a table of manual-given direct operands. The wrong claim
was this document's own, and it is what made a settled reading look open.

What this tree cannot do is check the rendering *by length*, which is a limit on
the decoder's own output rather than a question about the encoding. Both forms
are two bytes over the same operand positions, and `opcode_coverage.py
--divergence` reads `MCS51_LEN`, which carries lengths and no names, so it is
blind to the distinction by construction. The name here came from the listings,
as every other name in this document did.

## The contradiction this surfaces in two other tools

Naming `0x06`/`0x07`/`0x16`/`0x17` contradicts a set that two other tools grade
committed data against. `citation_gap_scan.UNASSIGNED` and
`bank_map_score.UNASSIGNED` both hold exactly these four values, and both
described them as *the byte values the MCS-51 map assigns to no instruction*.

**That description is wrong, and it is the substantive finding of this work.**
The MCS-51 map assigns all four (`INC @R0`/`@R1`, `DEC @R0`/`@R1`, one byte
each), `OPCODE_LEN` sized them correctly throughout, `MCS51_LEN` — the table
those comments cite as the manual — assigns all four a length, and the committed
listings place real instruction starts on every one and name them. The one value
`MCS51_LEN` alone leaves unassigned is `0xA5`. This is the same class of
mis-transcription as the `0x96`/`0x97` error that
`docs/findings/opcode-table-coverage.md` records retracting twice, in the same
family.

The claim was not confined to those two definitions: it had been copied into
each tool's self-test prose and into the suite cases that asserted, as a
consequence, that all four print `db`. Every site is corrected in place, with the
old text visible beside the correction. **The two `UNASSIGNED` sets themselves
are untouched**, and the corrections say why:

- The `not-code` verdict is driven by `window[i] in UNASSIGNED`, a literal in
  `citation_gap_scan.py`. It never consulted `mnemonic()`, so naming the four
  moves no verdict. `citation_gap_scan.py --check` still reports one `not-code`
  pair, the same `bank0,3AD6` row.
- `bank_map_score.UNASSIGNED` feeds `p_bad` and every ranking derived from it.
  Changing the set re-cuts those.

Fixing the two sets is therefore a **different change from a rendering one** — it
moves a published verdict and a ranking rather than a spelling, and it needs its
own re-cut and its own review. That is the follow-up issue this surfaces.

### What the re-cut did change

`ec/ghidra/gap-citation-scan.csv` is generated by `citation_gap_scan.py
--report` and compared byte-for-byte by `--check`, so naming the values required
re-cutting it rather than leaving it stale. Exactly one row moved, and one
column of it: the `db` count on the `bank0,3AD6` `not-code` row, **25 → 1**. The
`unassigned` count on that row stays 9, and the verdict stays `not-code`.

Several committed annotation tables carry decoder text in their
`earlier_record`/`window` cells. The ones the issue's file list named were re-cut
from their generators (`audit_call_targets.py --csv`/`--paged-csv`/
`--relative-csv` and `find_indirect_xdata.py --csv`, each with the firmware path)
and diffed; every change is confined to those two columns — no row was added,
dropped or reordered.

**That list was illustrative, not exhaustive, and the full set is a diff.**
Naming the opcodes reaches every committed table that carries its text, in
whatever column its generator chose — the audit tables in `earlier_record`, the
`window` column of `computed-dptr-sites.csv` and
`xdata-addc-dph-residual-sites.csv`, the `note` of
`pd-direct-offset-sites.csv`, the `succ_first` of
`pd-no-ret-fallthrough.csv`, and the `earlier_record` cells of
`call-target-seed-frames.csv`. Each was re-cut from its own tool
(`computed_dptr_sites.py --csv`, `addc_dph_sites.py --csv`,
`pd_direct_offset_sites.py --csv`, `pd_no_ret_fallthrough.py --csv`,
`call_target_seed_frames.py --check`) and now passes that tool's `--check` byte
for byte.

`git diff --name-only origin/main...HEAD -- 'ec/annotations/*.csv'` names the
committed tables that moved, which is the set the writing tools cannot report
because each knows only its own. `ec/tools/test_addc_dph_sites.py`'s
committed-table case is what found the last of them, after the rest had already
been re-cut.

## What naming the bytes broke, and the shape of it

Several suites failed on this change and all of them failed the same way: each
had recorded the decoder's *incompleteness* as a fact, and each became false the
moment the decoder was completed. They are worth naming as a class, because the
next decoder change will meet the same pattern.

| suite | what it had asserted | corrected to |
|---|---|---|
| `test_direct_address_renderings.py` | the four `UNASSIGNED` bytes print `db` | they are named, and `UNASSIGNED` is read from the scanner |
| `test_citation_gap_scan.py` (twice) | the same four print `db`; `0xD4` as an example of a byte the decoder declines | the same, plus `0xA5` for the second |
| `test_check_site_census.py` | `0xB6`/`0xB7` are `UNRENDERABLE` because they have no mnemonic | dropped; `cjne` was already in `FLOW_TAIL` from the `0xB8`-`0xBF` forms |
| `test_pd_high_xdata_probe.py` | `0xF4` is a `db`, so a window steps over it | built from whichever byte value the decoder does decline |

Two of them — the `0xD4` case and the `0xB6`/`0xB7` exclusion — had picked a
byte as an *example* of a category, and the category outlived the example. That
is the trap: a suite saying "this byte is unrenderable" makes a claim about a
table it does not own, and the claim expires silently the first time someone
else extends that table. Where it was possible the corrections now read the
example out of the decoder rather than typing it, so the next rename cannot
break them.

Every correction keeps the assertion that was worth keeping, and two replacements
are *stronger* than what they replaced: "the four print `db`" became "the four
are named, paired against the instruction either side of each", and "a `db` is
not `not-code`" became "a `db` is not `not-code`, and the one that stays a `db` is
the one the map assigns nothing".

## What this does not establish

- **Nothing about what the EC does.** Every input is a committed file, and no
  hardware or Windows step was needed or taken. No live test ran, no register was
  read back, no behaviour was observed.
- **That the 292 renamed bytes are 292 instructions.** Naming a byte is not
  evidence the byte sits at an instruction start.
  `direct-address-opcode-rendering.md` graded its own re-cut and found a
  substantial minority of its renamed cells without an anchor — *not found by
  this method* to be framed, which is what a linear decoder anchored
  mid-instruction produces. The same caveat applies to every figure here.
- **That the cross-decode hazard is gone for the operand spellings.** A
  first-token agreement is what the new suite checks; it does not check that this
  module's `bit_name()` rendering or its lowercase registers match Ghidra's, and
  those are conventions rather than disagreements.
- **The `0xA6`/`0xA7` rendering against anything but the listings.** The manual
  and the listings agree on `MOV @Ri,direct`, but no check here compares this
  module's output against the manual's *names*; `--divergence` reads lengths.
- **The `0xA8`-`0xAF` three-way disagreement.** `walk_branch_arms.py` reads
  `mov direct,@Ri`, `disasm8051.py` prints `mov r0,0x..`, and
  `pd_inline_arg_sites.py` takes a third reading of the same eight bytes. Those
  render as instructions today and this change does not touch them. Picking a
  side is the same arbitration as `0xA6`/`0xA7`: nothing here can settle it.

## Reproducing it

```console
$ python3 -c 'import sys;sys.path.insert(0,"ec/tools");import disasm8051 as D,opcode_coverage as C;db=[o for o in range(256) if D.mnemonic(bytes([o]+[0]*7),0).startswith("db")];print(len(db),[hex(o) for o in db if not C.MCS51_LEN[o]])'
1 ['0xa5']
$ python3 ec/tools/disasm8051.py --self-test
$ python3 ec/tools/test_disasm8051_db_fallthrough.py
$ python3 ec/tools/citation_gap_scan.py --check
```

The first line is the claim. `--self-test` is unchanged and still passes: it
holds the two `charge-profile-flow.md` windows, the four `REL_SITES`, the eleven
`BIT_SITES` and the `TEXTBOOK_BIT_SITES` pair, none of which is affected. The
suite is the new one and holds the wider table against the listings. `--check` is
the byte-for-byte comparison of the re-cut CSV.