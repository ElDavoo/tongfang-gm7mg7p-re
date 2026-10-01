# Direction A's fallback was a search over a whole write-up, and it is now three named addresses

(2026-10-01. Static arithmetic over committed files at `2a7aad70`. No EC is
opened, no register is read back, no laptop or Windows machine is involved:
every figure below is a count of strings in a file in this repository, and each
is given with the pattern that produces it. Nothing here is hardware evidence.)

## What the fallback was, and what it admitted

`SiteCensusTests` in `windows/tools/test_gpu_block_watch.py` grades §7's
`EC-side cross-reference` column in both directions. Direction A is doc →
census: an address a cell cites must either be a bank0 site in
`ec/annotations/ec-07c4-07d5-sites.csv` or be something the walk named in
prose.

The second half is not a convenience. Three of the addresses the cells cite are
not `MOV DPTR` sites at all:

| address | what it is | why the CSV has no row |
|---|---|---|
| `bank0:0x83FF` | routine entry `sync_0788_and_07d4_from_09e9` | the routine *contains* the `0x07C4`/`0x07D4`/`0x07D5` sites; it is not one |
| `bank0:0x94C0` | routine entry `set_07c4_bit4_from_r7` | the `MOV DPTR,#0x07C4` the 8-instruction walk stops on is at `0x94C1` |
| `bank0:0x9711` | the single `lcall 0x94C0` | a caller, not an access |

That fallback was implemented as `re.search` for the address anywhere in
`ec/annotations/ec-07c4-07d5-sites.md`. The document is a write-up of the whole
walk, so it names every register address the walk reads, every operand and
every byte of every listing in it — and a cell citing `0x0743` or `0x09E9`
passed.

Counting what the pattern the test itself used admits, at `2a7aad70`, with
`0x([0-9A-Fa-f]{4})(?![0-9A-Fa-f])` and `re.I` over the whole document: **235
distinct spellings, 209 distinct values**. Restricting to the fully-uppercase
spellings gives **153**. The document is 902 lines at this commit.

**The exact figure is not the claim and nothing here rests on it** — both the
document and the counting pattern move the number. The claim is that every way
of counting gives something two orders of magnitude wider than three.

## What it is now

`NON_SITE_CITATIONS` names those three addresses, each with a note saying what
it is, and direction A admits a citation on membership in it. The census is no
weaker for it: the two directions between them still pin every address, and
this narrows only the half that could not see a citation failing to resolve.

The `.md` still backs the allowance — `test_the_fallback_is_exactly_the_
addresses_the_census_does_not_carry` asserts each of the three is named in it,
and asserts the derived fall-through set equals the constant's keys in *both*
directions. So a cell citing a fourth non-site address fails, and so does a
constant grown past what the data needs. The `.md` naming is checked once, in
the guard, rather than on every address in a 902-line document: the failure
names the allowance either way.

## Why enumeration and not section scoping

The alternative — scope the search to the sections that name the three (§3, §4,
§4.1) — does not reach the same bar. Measured the same way, that scoping still
admits **83 distinct values, 80 of which are not the three**, including
`0x0743` (`CTGP_DB_CTRL`), `0x07D4`, `0x07D5` and `0x09E9`. A register address
and a source byte are not sites, and §4's own heading names two of the four
census registers.

Enumeration is also the reading that survives an edit to the document: a scoped
regex widens silently every time somebody writes a new section, and there is no
edit to the `.md` that makes a scoped fallback report the right thing.

## The perturbations, and one correction to the issue's version

**The tightening.** On a deep copy of the parsed table with `bank0:0x0743`
substituted for `bank0:0x94C0` in the `0x07C4` cell, the tightened check
reports it — and the test also asserts the old `re.search` *would* have admitted
the same address. That second half is what makes it a demonstration rather than
a check that happens to fire: it shows the tightening is the reason. The three
real addresses are asserted to still pass against the same mutated table.

**The drop, retargeted.** The issue asks for "drop a genuinely-cited site from
a cell, and confirm the tightened direction A still fails it". That cannot hold
as written: direction A asks whether a *cited* address resolves, so removing a
citation cannot fail it — dropping `bank0:0x843D` leaves A passing by
construction. The case is kept, aimed at **direction B**, which asks the
converse and is the half that catches a census site a cell stopped crediting.

Both perturbations call the same helpers the direction tests call, rather than
recomputing the verdict. That is load-bearing: a perturbation that restates the
arithmetic stays green when the check it is meant to be demonstrating is
reverted, which is the failure this would otherwise have shipped.

## A re-registration this change forced

Adding the allowance block and the two perturbations put 152 lines above every
pin the line-pin census holds into `windows/tools/test_gpu_block_watch.py`, so
two rows there were re-registered against the same target lines at their new
numbers. `0751-mark-provenance-column.md` §3 carries the citing prose for both,
and its table row in `test-line-pin-census.md` carries the record, so the two
move together; the cited lines are byte-identical to the ones they replace and
the verdicts are the readings recorded against the old numbers. Recorded here
because the write-up is where the shape of the edit is stated, not only in the
two files' own re-registration notes.

## Follow-up this opens

The three addresses are a shape the census has no vocabulary for: a routine
entry, and a call site that is not itself a `MOV DPTR` site. Until the census
can say so, direction A has to carry an exception list — and this change makes
that list three explicit, checkable names rather than a document-wide regex.
Whether `ec-07c4-07d5-sites.csv` should grow a row kind for a named entry point,
which would retire the fallback rather than narrow it, is recorded here and not
answered.
