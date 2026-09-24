# What grounds a name, and what a group is (issue #135)

The write-up for [issue #135](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/135),
which asked for two separable things: evidence grading on function *names*, and
a grouping layer. Both are in, both are mechanical, and both come with the
thing that makes them auditable rather than merely new.

`docs/findings.md` §20 has the summary. This file has the reasoning, the
distributions and the things the work does **not** establish.

---

## Part 1 — `name_basis`

### The problem, stated precisely

A function name in this repository asserts a *mechanism*. `load_dptr_88f0_tail_jump_1114`
is a true description of two instructions; `timer1_counted_delay_using_0a56`
asserts that a routine waits on Timer 1 overflow. Before this change nothing
recorded **what the assertion rests on**, so a name decoded from a register map
read exactly like a name guessed from instruction shape, and a reader had no
way to tell them apart.

The issue's own worked example is why this is not a tidiness point.
`bank0 0x0EA2` was named `timer1_counted_delay_using_0a56` while its comment
said *"a stock 8051 places TC1 at 0x8E and TF1 at 0x8F"*. The name was right
and the comment was wrong — TCON is at 0x88, so 0x8E is TCON.6 = TR1 and 0x8F is
TCON.7 = TF1, which is what Ghidra's C has and what
`ec/tools/disasm8051.py`'s `bit_name()` independently says. The correction is
in place with the wrong version left visible. **The lesson is not that a name
was wrong. It is that a name is a claim with a basis, and the name and its own
comment were contradicting each other with nothing recording which to believe.**

### The column

`name_basis`, appended to both `ghidra-functions.csv` files. Mandatory and
non-empty, exactly like `evidence`, and refused by the build on the same
grounds: *a name that asserts a mechanism with no recorded footing is a claim,
not a finding.*

| value | the mechanism rests on |
|---|---|
| `register-map` | a decoded SFR/bit identity — 0x8E is TCON.6 = TR1. Checkable against `bit_name()` and `BIT_SFR`. |
| `ec-register` | an XDATA address in `registers.yaml` carrying a decoded name/status. |
| `abi-symbol` | a toolchain or ABI symbol rather than the bytes — the BL51 bank-select stubs, EDK II type/protocol names. |
| `code-shape` | only the instruction sequence's shape. |
| `mixed` | the name asserts two things with different footing. |
| `unresolved` | the row is `type: unresolved` and the name is a placeholder claiming nothing. |

### The grading rule, and why it is asymmetric

**Strongest footing actually traceable to a committed input, else `code-shape`.**
The default points at the weak end on purpose. Grading by name-regex would
overclaim — a name containing `write` is not thereby grounded in a register map
— and grading the other way would under-claim, which is its own inaccuracy.

The rule is implemented in `ec/tools/grade_name_basis.py`, which reads the
row's own committed `.asm` rather than its name, and `--check` re-grades the
committed column and fails on any disagreement, so the column and the rule
cannot drift. **The rule is stated rather than left in the tool's head
precisely so a later reader can re-derive any row and get the same answer.**

The discriminator between an SFR citation and an XDATA one is the listing, not
the number: `clr 0x8E` is a bit operand and `mov DPTR,#0x0080` is an XDATA
byte, and a name saying `0x80` could be either. Only the committed bytes
decide.

### The measured distribution

EC, 1,804 rows:

| grade | rows | |
|---|---:|---|
| `code-shape` | 1,477 | the default, and the largest class by design |
| `ec-register` | 134 | |
| `register-map` | 83 | |
| `abi-symbol` | 57 | |
| `unresolved` | 49 | |
| `mixed` | 4 | |

BIOS, 788 rows: 729 `code-shape`, 43 `abi-symbol`, 9 `register-map`, 6
`unresolved`, 1 `mixed`. Reproduce either with
`python3 ec/tools/grade_name_basis.py --report`.

### The issue's worked example is a finding, and it is a negative one

The issue floats renaming `timer1_counted_delay_using_0a56` to
`delay_polling_0a56` as what a `code-shape` name should look like. **That name
is not shape-founded and is not renamed.** 0x8E/0x8F are TCON.6/TF1, decoded
and corroborated two ways. Its grade is `register-map`.

Getting there needed one thing the plan did not anticipate: the name says
`timer1` in **words** and never writes `0x8E`, so a rule keyed on hex literals
alone grades it `code-shape` and loses the decode — the exact failure the
column exists to prevent. The grader therefore recognises an SFR identity
named in words (`timer1`, `tf1`, `et1`, `tcon`, …) and corroborates it the
same way, against the listing. A name asserting a timer the bytes never
reference still gets nothing.

**This is the column earning its keep, and it is also the plan's "Reading left
out" applied honestly:** no mass renaming. The basis is recorded in the row,
which is what the issue's own "**or in the row**" reading allows, and which
avoids re-symboling Ghidra and churning every generated header plus both
`index.csv` name columns for a change the column itself already captures.

### The `pd` finding

**The PD image is a separate 8051 program with its own XDATA map**, so a
`MOV DPTR,#0x07E2` in it is *not* a reference to the EC register at 0x07E2.
497 of the EC CSV's rows are `pd`-scoped, and the rule that keeps them off a
false footing is a check, not a convention:

> a `pd`-scoped row may not be graded `ec-register`.

It is the **third** lock on that door, after `gen_xdata_symbols.py` never
emitting pd rows and `ApplyAnnotations.java` refusing to apply one. It fires
independently of the "must cite a registers.yaml address" rule, which is what
makes it worth having: a pd row naming an address that *is* in the map would
pass rule 2 and still be a cross-image overclaim. Verified by poisoning a pd
row and watching both rules fire.

### The four cross-field rules

1. non-empty, and in the closed list;
2. a row graded `ec-register` must cite an address present in `registers.yaml`;
3. a `pd`-scoped row may not be `ec-register`;
4. a row graded `register-map` must name an address `bit_name()` decodes, or
   an SFR in `BIT_SFR`.

Rule 4 reads the **name, not the comment**, deliberately: a comment may
discuss a decoded bit anywhere while the name itself is shape-only, and
grading on the comment would make a `register-map` grade unfalsifiable.

One copy of the rules lives in `grade_name_basis.py` and both build tools
`import` it. Two copies is how "the EC checks it and the BIOS means something
slightly different" happens; the BIOS CSV is held to the same four rules, and
the `pd` rule is carried there even though the BIOS has no PD image, for the
same reason.

### A bug worth recording, because it was silent

The first implementation's `DPTR_IMM` pattern was case-sensitive and the
listing spells the register `DPTR` and the operand `0x`. It matched neither, so
XDATA detection was **completely dead** — and the report showed
`ec-register=0` across 1,804 rows, which reads as a finding rather than as a
broken pattern. It was caught by the grader's own `--self-test` fixture, which
is the only reason it was caught at all. A zero that means "the method is
broken" and a zero that means "the method found nothing" are the same number.

---

## Part 2 — the grouping layer

`ec/annotations/function-groups.csv` and `bios/annotations/function-groups.csv`,
one row per annotated function: `scope,addr,group,group_basis,comment,evidence`.

`group_basis` is closed: `type`, `vector`, `module`, `callgraph`, `shared`,
`ungrouped`.

### The seeds, which are the part that says what a group is *for*

- the 30 `type=bank-switch` rows → `bank-switch-trampolines` (the issue's own
  example);
- the interrupt table → `interrupt-vectors`;
- `type=charge-target` (2), `type=ec-io` (2), and the other mechanism-typing
  `type` values;
- the BIOS's 38 modules → `group_basis=module`.

**The vector family is 6 rows, not the 25 the plan measured.** `index.csv`
carries only 3 `seed_basis=vector` rows because the seed set was built from
the call census; the rest of the table reached the export by annotation. The
handlers are all there and named for the interrupt each one is
(`reset_vector_forwarder_to_0070`, `int0_vector_forwarder_to_052f`, …), so the
grouping tool matches the table **on the name** and gets all of them. The
plan's 25 was counting a different set.

### The banking caveat, inherited and not softened

Nothing in an `lcall` names a bank: bank0→bank1 and bank0→bank0 are the same
three bytes, and both banks are mapped at base 0x8000. So
`ec/tools/group_functions.py` **never joins bank0 to bank1**. The rule is
**structural**, not a filter applied afterwards: the union-find never sees a
cross-region edge, so there is no cluster to reject and the invariant cannot
be violated by a bug in a later pass.

Measured over the committed listings: **bucket A = 973, bucket B = 1,428,
bucket C = 450**, using `audit_call_targets.py`'s own `bucket_of()`. Bucket B
is the population an `lcall` cannot resolve and it is the largest of the three,
which is the honest shape of this firmware's call graph. 27 cross-region edges
are counted and reported, never merged. Every run prints these numbers, so a
small group count cannot read as a topology.

### What a group is not

**A `callgraph` group is a connected component, not a subsystem.** Union-find
answers "are these mutually reachable", and on this firmware the largest
component holds **323 of 1,804 rows**; the next two hold 302 and 145. That is
a real structural fact and a poor subsystem boundary, so the groups are named
`callgraph_<scope>_<addr>`, their size is in every row's comment, and `--report`
names any component of 50 or more. The seeds — read off the `type` column, the
vector table and the BIOS modules — are the part of this layer that says what a
group is *for*.

576 EC rows are `ungrouped`: no typed seed and no component at or above the
minimum size. That is *not found by this method*, never "these functions have
no subsystem", and the vocabulary has `ungrouped` in it so saying so costs
nothing — the same argument `unresolved` makes in the `type` column.

### Three blind spots, none closed

- the graph is built from `lcall`/`ljmp` **operands**, so a computed target
  (`sjmp @a+dptr`) and a bank-select trampoline's DPTR-carried target are both
  invisible to it;
- Ghidra's function boundaries on this firmware are a **hypothesis**
  (`ec/annotations/bank-call-audit.md` §1), so an edge can be an artifact of
  where a boundary was drawn;
- the paged `ajmp`/`acall` forms stay inside the caller's own region and are
  not edges at all.

**And nothing here is a behavioural claim.** A group says which routines are
connected in the call graph, not what the EC does with them on a live machine.
No hardware is reachable from a GitHub-hosted runner, so no live test is
claimed and none is possible here. The 2,592 comments were not read by hand to
infer subsystems; anything the seeds and the graph do not support stays
`ungrouped` rather than getting a plausible label.

---

## A consequence worth recording: a plate line moved a pinned citation

`ec/annotations/xdata-0860-census-sites.csv` pins **line numbers** into the
committed `.c` files (`bank0/D091.c:43,47`) and `check_site_census.py` holds
them. Adding the `name_basis:` line to every plate comment shifted every
function body by exactly one line, and the census check failed on 5 of its 7
sites — correctly, and with a message that says exactly what happened ("the
line moved, or the reference was dropped").

The refs were recomputed from the tool's own `census_occurrences()` rather
than blanket-shifted, and **nothing but the line numbers moved**: the same 7
sites, the same per-site `census_count`, the same 17 occurrences accounted for
once each. The alternative — leaving a check red because a generated file grew
a comment line — is the "a stale pin is fine if the test is annoying" failure
this repository's rules are about.

Worth noting for the next annotation change: **a plate-comment edit is not
confined to the plate.** This is the only committed file that pins a line
number into generated output, and `check_site_census.py` is what caught it.

---

## What would move this further

- **A per-module role roll-up** for the BIOS, derived from the `type` column
  within each module. Nearly free from the committed CSVs and the one part of
  the BIOS grouping the plan named that is not in yet.
- **Making the big components smaller.** Connected components are transitive:
  one shared helper collapses two subsystems into one blob. Splitting on the
  BL51 trampoline boundary, or on strong articulation points, would give
  tighter groups — and would need its own check that it did not merge across a
  bank.
- **Reading the remaining `ungrouped` rows.** 576 of them are reachable by
  reading; they are not reachable by the method, and saying so is what the
  column is for.
