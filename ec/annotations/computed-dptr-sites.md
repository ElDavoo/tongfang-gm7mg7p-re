# The eight `DPH` builds that reach page `0x0F`, and what a zero here still does not cover (issue #110)

[`manual-fan-ctrl-0751.md`](manual-fan-ctrl-0751.md) §6 is this repository's own
worked counter-example against its own tooling. `ec/tools/trace_xdata_refs.py`
reports **zero** direct sites for `0x0F00`-`0x0F5C`, a page the EC reads and
writes bytes on, because the EC reaches it by building the pointer in the
accumulator over two instructions — `add a,#lo ; mov DPL,a ; clr a ; addc
a,#0x0f ; mov DPH,a` — and the address is in neither of them. This page is the
scan that sees that spelling, the eight sites it finds, and the sentence in
`registers.yaml`'s header that now names this scan beside the ones before it.

**The eight are found with no seeding, and the answer is eight at every window
width from 2 to 9.** §2 has the run and §2a the ends of that range. A count a
`--window` knob can manufacture is a property of the knob, so the summary prints
the page-`0x0F` count at several widths beside the default on every run, and
`test_computed_dptr_sites.py` sweeps them as the acceptance criterion.

**The page is carried, not assumed, and no row invents a concrete address.**
§3 and §4: all eight are `clr a ; addc a,#0x0f`, and `clr a` clears the
accumulator *and* the carry, so `0x0F` is proved rather than guessed. The low
byte at every one of the eight is a run-time value — a `movx a,@dptr` result or
`mov a,#0x80 ; add a,r7` — so the address is not derivable and the tool says so
per row, naming the instruction that supplied A.

**Nothing was observed, and nothing was re-graded.** No register `status:`
moved, no entry entered or left `registers.yaml` — **`0x0F00` is deliberately
still absent**, and §6 says why that is load-bearing. No hardware and no
Windows machine was involved, and no sentence here is a claim about EC
behaviour.

## 1. How to re-derive all of it

```console
$ cd ec/tools
$ python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800
$ python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800 --csv \
        > ../annotations/computed-dptr-sites.csv
$ python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800 --check
$ python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800 --page 0x0F
$ python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800 --page 0x07
$ python3 -m unittest test_computed_dptr_sites.py
```

`--check` diffs the committed table byte for byte against a fresh generation and
needs no Ghidra, no network and no hardware; the suite asserts the same thing
end to end, so a CSV that stopped describing the image would fail a test rather
than a reader. `--page 0x07` exits non-zero, which is the finding for
`0x07B9`/`0x07D0` and not a failure of the run.

Neither the suite nor the `--check` is wired into
`.github/scripts/agent-gates.sh`: that file is copied from
[`ElDavoo/agent-pipeline`](https://github.com/ElDavoo/agent-pipeline), and
`check_ghidra_tooling()`'s tool list is hand-listed rather than a glob, so a new
tool gets no gate line from an agent branch whose push token has no `workflow`
scope. Both run by hand and under `bash tools/run-tests.sh`, and this page does
not imply CI runs them.

**Why a sibling tool and not a mode of `trace_xdata_refs.py`.** That tool's
`--csv` *default* is what `registers.yaml`'s `static_refs_main_ec` and the
committed `0x086x`/`0x0400`/`0x07C4` tables are reproduced byte for byte from,
and its `csv_table()` docstring says in so many words that the default carries
no extra column *so that the other tables reproduce unchanged*. A new bucket in
that output would change the meaning of a number the rest of the repository
quotes without changing its value, which is the silent meaning-change the issue
asks this pass to avoid. This tool imports `REGIONS`, `region_of`,
`runtime_addr`, `PD_MARKER`, `classify` and `check_table` from it and shares no
output, so there is still one region map and one refusal when the PD marker is
absent.

## 2. The population, and the eight

Three populations, and they are not a refinement of one claim: a byte scan
finds every `F5 83`, the anchored decode finds the ones it reaches as an
instruction, and the sites are the ones of those with an immediate `add`/`addc`
behind them.

| | raw pair(s) | anchored `mov 0x83,a` | site(s) |
|---|---:|---:|---:|
| `common` | 37 | 36 | 32 |
| `bank0` | 46 | 46 | 32 |
| `bank1` | 4 | 4 | 0 |
| **main EC** | **87** | **86** | **64** |
| **PD image** | **255** | **255** | **178** |

The two programs are never added: a DPTR built in the PD image is another
program's byte, which is `lightbar-bat-flow.md` §2's mistake and
`trace_xdata_refs.py`'s docstring's first point. The per-site list is
[`computed-dptr-sites.csv`](computed-dptr-sites.csv), one row each, with the
window's own decode in the last column so a reader can re-derive every cell
before it from the row.

**A `mov 0x83,a` this scan did not turn into a site is a limit, and the summary
counts them.** The 341 anchored stores are the 242 sites and the 99 declined
between them, once each, and a declined store names the reason it is not one:
95 had no immediate `add`/`addc` in the window, each naming the budget that ran
out, and 4 are the build the next paragraph is about. Those are the two reasons
this image produces — a store at the very start of a region, which has no budget
to name and carries its own token, is not among them. No reason is a claim about
the byte.

**A high-byte build is a site once, however many stores follow it.** The linear
walk does not stop at control flow, so where a `ret` is followed by the bytes
`F5 83` the walk decodes a second `mov 0x83,a` and opens the same `addc`
twice. The nearest store is the one the build feeds and the row names it; the
case is `0x0DB85` in `bank0`. Counting a build twice would make the
population a function of what follows a `ret`, which is the anchored pass's own
limitation and is §7's last bullet.

**Page `0x0F` is reached by eight sites, and they are the eight §6 names:**

```
0x08AC6  0x08AD8  0x08AF3  0x08B0C  0x0BCE3  0x0BDEC  0x0E86B  0x0F312
```

All eight are in `bank0`, where a file offset and a runtime address are the
same number, so §6's listing and this table are read against each other without
translating. The first of them, with the window the tool read it from:

```
0x8ac1  add  a,#0x20   ; A from a movx a,@dptr at 0x8ac0 -- a run-time value
0x8ac3  mov  0x82,a    ; DPL
0x8ac5  clr  a         ; also clears C
0x8ac6  addc a,#0x0f   ; DPH = 0x0F  (carry provably 0)
0x8ac8  mov  0x83,a
0x8aca  movx a,@dptr
```

and its row in the CSV:

```csv
0x08AC6,0x8AC6,bank0,"addc a,#0x0f",0x08AC8,24,0,0x0F,"at run time; A from `add a,#0x20` at 0x08AC1","page 0x0F, low byte at run time; A from `add a,#0x20` at 0x08AC1",read x1,"add a,#0x20 ; mov 0x82,a ; clr a ; addc a,#0x0f ; mov 0x83,a"
```

`frame_onto` is 24 for all eight, which is the strongest framing evidence
`disasm8051.py`'s metric offers and is a lower bound rather than a proof — as
`converges_from()`'s own docstring says, read the pair and not either half.

### 2a. The window width, and why the count is printed beside it

The default is four instructions, which is the width of the idiom behind the
anchor. Every run prints the count at several widths beside it, because "eight
at the default" is a claim a reader has to be able to check without re-running
the tool:

| window | main-EC sites | on page `0x0F` |
|---:|---:|---:|
| 2 | 64 | 8 |
| 3 | 64 | 8 |
| 4 (default) | 64 | 8 |
| 5 | 64 | 8 |
| 6 | 64 | 8 |
| 8 | 64 | 8 |

Both columns hold across the widths this table prints and across the full range
the suite sweeps, 2 to 9, and the `0x0F` count is 8 at width 2 as well — the
narrowest that can still hold an `add` at all, since the anchor store is not
itself in the window. That is the acceptance criterion: the eight are a property
of the image, not of the knob.

The range is bounded because the tool accepts widths outside it and prints only
the six above. Narrower than 2 the window never reaches the `add`/`addc` — at
`--window 1` it holds the `clr a` alone — so the `0x0F` count is 0 and not 8.
Wider than 9 the main-EC column moves: `--window 10` reports 66 against the 64
above. So the sweep's 2 to 9 is the range the evidence covers, and the 64 in §2's
table is a property of the default width rather than of the image.

## 3. The carry, and why the eight are decidable

`addc a,#imm` is `A + imm + C`, so the immediate alone is not the high byte and
the accumulator decides whether it is *any* of it. The tool reads A and the
carry from the one instruction before the `add`/`addc` — the only place it can
see them — and gets three answers:

- **determinate**, where that instruction establishes both. `clr a` (0xE4)
  clears A *and* the carry on a 8051, which is the idiom all eight use. So
  `clr a ; addc a,#0x0f` is provably `0x0F` and not `0x0F`-or-`0x10`. 58 of the
  64 main-EC sites are this shape.
- **a candidate set** `{page, page+1}`, where A is known and the carry is not —
  `mov a,#NN` before the `addc`. A set is printed as a set and is **never**
  collapsed to its low member: that collapse is the `docs/findings.md` §4d shape,
  a claim as though the method had established something it had not.
- **not established**, naming the encoding that defeated it, for everything
  else. The 6 main-EC refusals are 4 preceded by an `lcall` — which returns
  whatever the callee left in A — and 2 by a `mov a,rN`; both are limits on the
  look rather than facts about the accumulator.

**A refusal leaves its page open, and `--page` prints it rather than dropping
it.** An accumulator this tool could not read is not a page it can rule out, so
a refusal is listed under every page asked rather than under the one its
immediate happens to name — the high byte is `A + imm [+ C]`, and those agree
only where `A` is zero. That is what makes the `0x07` zero in §5 a measurement
instead of a silence.

**`clr c` (0xC3) is a real way to write "no carry", and it is deliberately not a
page source.** It establishes the carry and *not* the accumulator, so
`clr c ; addc a,#0x0f` computes `A + 0x0f` and not `0x0f`. Reading the
immediate off it would be the same over-claim as reading an unresolved `P2` as a
page in `indirect-xdata-sites.md`, and `test_computed_dptr_sites.py` pins the
refusal in both carry-setter directions.

**One limit is worth stating, because it makes the answer smaller rather than
larger.** A and the carry are read from the *same* single instruction, and only
`clr a` establishes both at once — so a site that sets them in two
instructions, `mov a,#0x0f ; clr c ; addc a,#0x00`, is refused rather than
resolved. No row in this image is that shape, so the cost is nil here, and where
it is not nil the direction is safe: `--page` reports fewer pages than the
firmware reaches, never more.

## 4. The low byte, and why no address is printed

The issue also asked for "the concrete address" where the low byte is an
immediate or a known-value read. **At none of the eight is it**, and the tool
says so per row rather than composing an address nobody read.

The `low` cell is read off the instruction in front of the nearest `mov DPL,a`:
`mov a,#imm` gives a literal and therefore a concrete address, and anything
else is a refusal naming the instruction that supplied A, with its offset, so a
reader can chase it. On this image **not one row resolves** — 60 of the 64
main-EC sites are supplied at run time and 4 have no `mov DPL,a` in the window
at all. The 60 that do have one are 47 supplied by an `add a,#imm` and 13 by an
`add a,rN`. For the eight the supplies are:

| site | low byte |
|---|---|
| `0x08AC6`, `0x08B0C`, `0x0BCE3`, `0x0BDEC` | `add a,#0x20` / `#0x50` / `#0x10` / `#0x00` |
| `0x08AD8`, `0x08AF3` | `add a,#0x30` / `#0x40` |
| `0x0E86B`, `0x0F312` | `add a,r7` on `mov a,#0x80` / `#0x61` |

So `xaddr` reads `page 0x0F, low byte at run time; A from …` and never
`0x0F20`. §6's own description of `0xF312` — "walks `0x0F61 + r7`" — is the
concrete instance: the offset is a literal, the low byte is not.

The `literal` branch is not dead code and is not hypothetical: a fixture
`mov a,#0xB9 ; mov 0x82,a ; clr a ; addc a,#0x07 ; mov 0x83,a` is `0x07B9` built
in five instructions, and the suite asserts the `xaddr` cell reads `0x07B9`
there. The branch is empty on this image, which is the finding.

## 5. `0x07B9` and `0x07D0`, and the read/write-versus-handoff split

`--page 0x07` is the mode that answers the issue's second question, per image,
and it exits non-zero because the main EC reaches the page by no site it can
establish:

```console
$ python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800 --page 0x07 ; echo $?
page 0x07, by the sites whose page this tool can establish:

  common    0  -- not reached by any site with an established page
  bank0     0  -- not reached by any site with an established page
  bank1     0  -- not reached by any site with an established page
  pd-image  0  -- not reached by any site with an established page

  and 21 site(s) this tool could not place, and 0x07 is not
  ruled out by any of them -- neither a hit nor a miss, and listed so the zero above is a
  measurement:
    0x02266  common    not established; the instruction before it is `lcall 0x2a7b`
    0x02270  common    not established; the instruction before it is `lcall 0x2a7b`
    0x02278  common    not established; the instruction before it is `lcall 0x2a8f`
    0x022DF  common    not established; the instruction before it is `lcall 0x2a7d`
    0x028EF  common    not established; the instruction before it is `mov a,r6`
    0x02912  common    not established; the instruction before it is `mov a,r6`
    0x22C58  pd-image  no instruction before it in the window
    0x22E38  pd-image  no instruction before it in the window
    0x27BE8  pd-image  not established; the instruction before it is `mov a,r6`
    0x2902A  pd-image  not established; the instruction before it is `mov a,r6`
    0x2906F  pd-image  not established; the instruction before it is `mov a,r6`
    0x29080  pd-image  not established; the instruction before it is `mov a,r6`
    0x290EA  pd-image  not established; the instruction before it is `mov a,r6`
    0x297BF  pd-image  not established; the instruction before it is `mov a,r4`
    0x297CD  pd-image  not established; the instruction before it is `mov a,r6`
    0x2B174  pd-image  no instruction before it in the window
    0x2B220  pd-image  not established; the instruction before it is `mov a,r6`
    0x2C6F5  pd-image  not established; the instruction before it is `mov a,r6`
    0x2D795  pd-image  not established; the instruction before it is `mov a,r6`
    0x2F3E4  pd-image  not established; the instruction before it is `mov a,r6`
    0x2F3ED  pd-image  not established; the instruction before it is `mov a,r6`

So the main EC reaches page 0x07 at no computed-`DPH` site this
scan can establish, and the PD image's computed DPTR is a different
program's byte either way. That is "not found by this method", and it
is a statement about the method.
$ echo $?
1
```

The rows under the zero are the refusals, and they are the reason the zero is a
measurement rather than a silence: this tool could not read the accumulator in
front of those `addc`s, so it cannot rule `0x07` out for any of them either.

- **`0x07B9`** (`static_refs_main_ec: 0`, `status: unknown-not-absent`): not
  contradicted and not rescued. The new bucket narrows what its zero licenses,
  from "not found by `MOV DPTR,#imm16` or by `movx @Ri`" to "nor by a run-time
  `DPH` built from an immediate". The row is not edited, because the row does
  not claim otherwise.
- **`0x07D0`** (254 direct sites, all in the PD image, so zero in the main EC):
  the same, with `DO-NOT-WRITE-BLIND` unchanged. A static scan is not a
  behaviour.

**The zero is this scan's, and the closing sentence says which.** A direct
`MOV DPTR,#imm16` on the same page is a different spelling with its own scan —
`scan_refs.py`, named in `registers.yaml` beside this one, reaches `0x07` in
the main EC — so the negative above narrows what those two rows' zeros license
and says nothing about theirs. That scoping is what `test_computed_dptr_sites.py`
holds: the closing sentence names a *computed* `DPH` site, and a general one
would be false against the committed image.

**Six of the eight are followed by `movx @dptr`; the other two are not, and the
population is not filtered on it.** `0x08AD8` and `0x08AF3` do `setb c ; lcall
0xBDF2` and `clr c ; lcall 0xBDF2` — they hand DPTR to a subroutine.
`trace_xdata_refs.classify()` already has a token for that, so the split is a
**reported column** and a reader can see it. A population filtered on `movx`
would find six of the eight and would have failed the issue's own test while
looking like a clean run, which is why the suite names those two.

**The same column says something the page count alone would hide.** Of the 64
main-EC sites, 25 read or write through `@dptr`, 3 hand DPTR to a subroutine, 9
have no `movx` in the decoded window, and **27 use the pointer they built as a
CODE pointer** — a `movc a,@a+dptr` is a table lookup in CODE and says nothing
about a register of that number, which is `classify()`'s own docstring and
`ec-0x07d0-sites.md` §5. So a page this tool reports as reached may be reached
only as a CODE table. `--page 0x49` is the worked instance: six sites build
`0x49` and every one of them is a CODE pointer, and the run says so rather than
letting the count read as six register references.

## 6. `registers.yaml`: the header, and the row that is not added

**The header caveat gets a sibling paragraph**, naming which spellings are now
covered and repeating the uncovered list of §7. No `status:` moves, and no row
is edited.

**`0x0F00` is deliberately still absent from `registers.yaml`, and adding it
would break a prepared upstream patch.** Eight sites on page `0x0F` make the
page look obvious, and it is not: `tools/check_power_profile.py` rule 2
*requires* `0x0F00` to have no entry, because
`linux/patches/gm7mg7p-power-profile/` is a fan-table map whose whole claim
about that address is a deliberate absence, and `tools/test_check_power_profile.py`
pins the requirement by deleting `0x0F00` from its own fixture. This pass finds
sites on the page; it says nothing about what the EC *does* with them, which is
the distinction the whole of `CLAUDE.md`'s calibration rule is about.

**The two `registers.yaml` notes that read "0x0F00 and 0x0F20 have zero direct
`MOV DPTR` sites" stay true and are not rewritten.** The claim is about
`MOV DPTR,#imm16`, and this is a different spelling. Rewriting them as though
they had been wrong is the error the calibration rule exists to prevent, so each
gets a pointer sentence naming this tool and its eight sites, and nothing else.

## 7. What this does not establish

The list the issue asked for, and the header paragraph carries the same one.

- **Register-indirect `movx @Ri`.** `P2` paging is a different addressing mode
  and a different tool: `find_indirect_xdata.py` owns it, and its
  `indirect-xdata-sites.md` §5 is the full list of what *that* does not
  establish. `mov @Ri,#data` (0x76/0x77) writes the same XDATA byte and is in
  neither population.
- **A `DPTR` built from a stored pointer or a table.** This scan reads the one
  instruction in front of the `add`; a page loaded from XDATA or CODE and
  added to is a different construction and is not here.
- **A `DPTR` handed in through a subroutine's own `DPL`/`DPH` writes.** The
  window is the linear decode behind the store and stops at the region edge; a
  callee that builds the pointer itself is not followed. The `access` column
  reports the handoff rather than resolving it, which is why `0x08AD8` and
  `0x08AF3` are in the population with their direction unresolved.
- **CODE jump tables.** A `jmp @a+dptr` is filed under the same "CODE pointer"
  heading as `movc` above and is a jump table, not a register reference.
- **The `add`/`addc` register forms.** `add a,r7` (0x2F) and `addc a,r4` (0x3C)
  build a high byte from a register this tool does not model, so they are not
  in `ADDS`. `0x0E86B` and `0x0F312` are found anyway, because the
  `addc a,#0x0f` in front of their `mov 0x83,a` is the site's high byte and the
  register add belongs to the low one.
- **Anything about behaviour.** No register was read back, no write accepted,
  no capture taken. The `0x0F` mechanism is already mapped statically
  (`windows/vendor-ec-map.md` "Fan tables", §6 above, and `profile-map.csv`'s
  `0x0F5D`-`0x0F5F` mailbox row); this pass changes which static sites a tool
  can see and claims nothing about what the EC does with them.
- **A page that is absent from the summary's list.** That is "built by no site
  whose page this scan can establish", which is a statement about the method
  and not about the page: the rows this tool could not place are open on every
  page, so a page one of them might build is absent from that list too. `0x07`
  is in that position, and `--page` on it prints the zero, exits non-zero, and
  names the rows it could not place beside it.
- **The anchored pass's own framing.** One linear decode per region, which
  re-syncs a byte at a time at the region's tail and does not stop at control
  flow — §2's `ret` case is that limitation landing on a real row.
  `frame_onto`/`frame_over` are the evidence about it and, as §2 says, a lower
  bound.

## 8. What it opens

- **The 27 CODE-pointer sites are unclassified.** They build a DPTR this scan
  resolves and then read it with `movc`, so they are a page census that is not
  an XDATA register census — and they are the largest single bucket in the
  main-EC split. `inc_dptr_sites.py` owns the `@dptr` walk for the direct form
  and nothing here touches these.
- **Page `0x3A` is six sites, five of them CODE pointers.** The largest page in
  §2's list after `0x49`, and the same shape.
- **The declined stores are a census nobody has read.** The ones saying
  `no immediate add/addc in the window` are four instructions wide, so most of
  them are probably `mov a,#hi ; mov 0x83,a` — the ordinary immediate form,
  already `trace_xdata_refs.py`'s population. Reading one of them against the
  listing would say whether the two populations are disjoint, which is a
  question about the two tools rather than about the image.
- **Confirming the eight on the machine is still a human's step.** This is a
  static scan and §7 says so; closing the issue does not need it, and doing it
  is not something an agent branch can do.
