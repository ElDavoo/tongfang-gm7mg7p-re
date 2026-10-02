# The de-duplicated census's `157`/`858` pd pair is unmoved because the pass finds one fold in the PD program and that fold names no XDATA byte (issue #1364)

`docs/findings.md` §4 records two conclusions that were confidently wrong, and
this one is not a third: it is a claim of the shape those two warn about, so it
is written with its method and its limits attached. **Nothing here is a hardware
claim.** No register was read back, no image was opened, and no laptop, EC or
Windows machine is involved. Every figure below is a count over committed text
(`ec/decompiled/**`, `ec/annotations/*.csv`, `ec/firmware/GMxMGxx_11.800`) taken
from the census tool's own flags, with the scratch outputs under `/tmp` and
nothing written into the tree. The change edits one tool's constants and one
check, and no CSV, no `registers.yaml` row and no `status:` value.

## The sentence

**The export-ownership pass reaches the PD program, finds exactly one fold in
it, and that fold carries no XDATA literal — so not one of the pass's 858 pd
references moves.** Not "there is nothing to fold in the PD image": there is a
fold, and the write-ups that called the pair "left open for a narrow reason"
framed the gap as bookkeeping, which understates a fact about the program.

## The fold

`ec/tools/export_ownership.py`'s `classes_of()` folds a file into an owner when
the smaller body's statements are contained in a larger one's, at
`export_ownership.py`'s `THRESHOLD` (0.90) and `MIN_BODY_STMTS` (3) floor — the
two constants whose values the module's own comment says change the map. Each
class takes one owner, the largest body, and the census pass then does not open
a `shared` file at all: its references are already counted through the owner,
because the owner's body is the superset. **That is the whole mechanism, and it
is why a fold only moves a reference when the non-owner's own body named an
XDATA byte.** No XDATA literal in the folded body, nothing to relocate onto the
owner.

At the committed thresholds, exactly one `pd` export folds. Read off
`ec/annotations/xdata-export-ownership.csv`, the only row with `program=pd` and
`shared=yes` out of 146 `shared=yes` rows tree-wide:

| non-owner | owner | containment | body_lines | owner name |
|---|---|---|---|---|
| `pd/3750.c` | `pd/9784.c` | 1.00 | 4 | `call_0faf_0f00_0dbc_then_r3_23` |

The other 145 `shared=yes` rows are main-EC, and `ec/decompiled/index.csv`
carries 541 `pd` rows, so the PD program's single fold is one export in 541 —
against 42 in the `bank1:0x8001` class the pass was built for.

## The two bodies

Both are the same three-call forwarder. `ec/decompiled/pd/3750.c`:

```c
void call_0faf_0f00_then_jump_0dbc(void)
{
  read4xdata_to_r4_r7();
  negate_32bit_r4r7();
  add_32bit_r0r3_to_r4r7();
  return;
}
```

and `ec/decompiled/pd/9784.c` the same three calls in the same order with one
extra statement:

```c
void call_0faf_0f00_0dbc_then_r3_23(void)
{
  read4xdata_to_r4_r7();
  negate_32bit_r4r7();
  add_32bit_r0r3_to_r4r7();
  sub_or_cmp_r0_r7(0,0,0,0x23);
  return;
}
```

**Neither names an XDATA byte**, and that is not this file's reading of them —
it is what each export's own plate comment records. `pd/3750.c`'s: *"No register
is set up and no XDATA address appears in the listing; all register and memory
effects belong to the three callees, none of which is decoded here."*
`pd/9784.c`'s: *"The entry starts mid-sequence -- its DPL is set by instructions
not in this listing"* — the DPL, not an address the listing names. So the fold
is real and it is a genuine duplicate read of one body, and it is empty of
XDATA by construction rather than by accident.

## The before/after, measured

`--export-ownership` writes only to paths the caller names and is refused with
`--check` and `--self-test`, so this is the only route to the comparison:

```
python3 ec/tools/xdata_register_map.py --export-ownership \
    --out-registers /tmp/ao-reg.csv --out-clusters /tmp/ao-cls.csv
```

which prints `main-ec: 1218 distinct addresses, 9320 references` and
`pd: 157 distinct addresses, 858 references`. Against the committed
`ec/annotations/xdata-registers.csv`:

| | committed | `/tmp` run | differ |
|---|---|---|---|
| `program=pd` rows | 108 | 108 | — |
| their `refs` sum | 603 | 603 | **0 of 108** |
| `program=both` rows | 49 | 49 | — |
| their `refs_pd` sum | 255 | 255 | **0 of 49** |
| address sets | 1326 | 1326 | equal |

**"Nothing moved" is only interesting against a pass that demonstrably moves
something, so here is what it moves.** File-wide, 296 addresses change `refs`
between the two runs, and they are exactly the `OWNERSHIP["moved"]` set: 281
`program=main-ec` rows and 15 `program=both` rows. Of those 15, **15 change on
their main-EC half and 0 change on their pd half.** So the pass moves 296
addresses' references file-wide and not one of the 858 pd references. The
"0 moved" is a real result against a live pass, not a pass that found nothing
to do.

And it is an identity rather than a spot check, because `157 = 108 + 49` and
`858 = 603 + 255` is the arithmetic `PER_PROGRAM` already asserts over the
default census, read back here over the de-duplicated one. The de-duplicated pd
group is exactly the default census's `pd` rows plus the `both` rows' pd half,
and the `refs_pd` cell is unmoved on all 49. A figure that is the sum of two
independently-pinned halves, neither of which moved, is held by more than one
assertion.

## What is now held, and what a `pd_moved: 0` would have cost

`OWNERSHIP` now carries `"pd_distinct": 157, "pd_refs": 858` beside the
main-EC pair, and `--self-test`'s ownership block reads both in a new "and its
pd half is" check beside the main-EC one. That closes the last row of
[`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md)
§2b, whose `pin` cell previously named only the `ORACLE["extmem_pd_*"]` keys —
which measure the **default** census — while §6b prints the pair for its own
de-duplicated run.

**The pin is deliberately a width and not a "moved: 0" key.** A zero is a value
the first real `pd` fold edits, and a test holding it would have to be edited in
the same commit that makes the fold true. The width pair already goes red on
that event: a fold whose body *does* name an XDATA byte drops that body's
references onto the owner, and `pd_refs` moves. That is what this pin is for.

Note also what was **already** held before this change, so the pin's reach is
not oversold: the `lost` check in the same block spans both
`groups_own["main-ec"]` and `groups_own["pd"]` and is empty, so "the pass drops
nothing" was pinned across both programs. What is new is the width of the pd
half and the fact that it does not move — not the safety property.

## What this does not establish

- **"0 pd references move" is this method on this tree, not a proof the pass can
  never move one.** It is a static comparison of the committed decompiled tree
  against a fresh `--export-ownership` run, by the thresholds
  `export_ownership.py` currently commits. Change either and this is a
  re-derivation, not a standing fact.
- **A body not naming an XDATA byte is a fact about the export, not about the
  PD firmware.** Both bodies are forwarders into callees that are not decoded in
  these listings, so what the callees touch is not established here. The claim
  is that the *listed* body is empty of XDATA, which is what makes the fold
  move nothing.
- **A register whose only writer is a folded body is not thereby unreferenced.**
  Nothing in this file is evidence about EC behaviour, and the
  `confirmation` rule in `CLAUDE.md` applies to everything downstream of it: a
  write being counted is not evidence the EC acts on it.

## The corrections

Three write-ups carried the "left open for a narrow reason" framing. All three
keep the original text visible and carry a correction beside it, per
[`../findings.md`](../findings.md) §4a-4d:

- [`xdata-export-ownership-page-census.md`](xdata-export-ownership-page-census.md)
  — the paragraph after its correction banner, which says the `157`/`858` pair
  is "still not held".
- [`xdata-6a-direction-rows-pinned.md`](xdata-6a-direction-rows-pinned.md) —
  the §2b bullet that ends "**Still open on the merged tree.**", closed here the
  way the `1218`/`9320` bullet beside it already records its own closure.
- [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md)
  §2b — the live paragraph that calls the caveat "the wrong answer for the
  figure on the page", and the `157`/`858` row's `pin` cell, which said "**but
  for the *default* census, not this run's**". That caveat is now false: this
  run's is measured too. The blockquoted older §2b further down is already under
  a supersession banner and is left alone.

No gate, workflow or action file changed. `check_doc_figure_pins.py` runs by way
of its test in `tools/run-tests.sh` and is not in
`.github/scripts/agent-gates.sh`; adding it there is a human's change, since an
agent branch's token has no `workflow` scope.

## What else moved, and why

Adding keys to `OWNERSHIP` and a check below it moves every line under it, and
several suites in this tree hold line pins rather than a statement about a
file's content. Each went red on the addition, and each is the tooling working.
`check_eq_guard_citations.py` reported citations across four prose files as
naming a line the tool has since left, naming each one's current line beside it,
and those numbers are re-pointed to it here — a number-only change in every one,
with the sentences, the paragraphs and `docs/findings.md`'s frozen section count
untouched. Its own rule is the one this follows: hold the code, and let the
number follow. The three superseded paragraphs its `skip` rule passes over are
left exactly as written.

The same addition moved two line pins in `test_check_doc_figure_pins.py`, which
that file's own comments document as re-measured against the tool rather than
shifted by arithmetic; both were re-read from the file.

The §2b correction above moved lines in the checklist that
[`test-line-pin-census.md`](test-line-pin-census.md)'s own table cites, so its
reconciler reported eight rows whose target the correction had walked away from,
and that file's suite asserts the *property* that every record places — not a
count of the rows, which is why it went red rather than needing a number edited.
Each row was re-anchored by grepping the citation the row names and reading the
line it is now on. None of this is a new claim about anything — it is the cost of
putting a pin in the tree, paid by whatever cites the line the pin moved.
