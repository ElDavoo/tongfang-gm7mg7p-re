# The `XDATA_0860` note's six live pointers, and what holds them (issue #870)

**Issue #870, 2026-09-26.** #801 corrected eight line citations across three
files and named, as its follow-up 2, six more that it deliberately did not
correct. This is that follow-up: the six are repointed in place, the addendum
that recorded them is extended with a dated entry naming each old→new pair, and
the question #801 left open — whether the supersession vocabulary should change
so a correction paragraph's *new* claims get checked — is decided and recorded.

**None of this is a live test, and none of it is evidence about the firmware.**
The whole of it is arithmetic over committed text: no EC is opened, no register
is read back, no capture is taken, and no laptop, EC or Windows machine is
involved. A line number into `ec/tools/xdata_register_map.py` is a statement
about a source file this repository reads, not an observation of a byte. No
`status:` moved — `XDATA_0860` stays `present-untested` — no count, bucket or
`refs:` figure moved, and no CSV or Ghidra export was regenerated. Every figure
the block asserts about the firmware is unchanged, because only pointers moved.

*(Correction, 2026-10-02, issue #907. **The six measured figures in the table
below have moved again**, and the table is kept as written rather than edited:
each is a `grep -n` into `ec/tools/xdata_register_map.py`, and #907's
per-program function-count columns added lines above four of the six anchors.
Re-measured on this tree, not shifted:*

| the table says | it now names | **measured now** |
|---|---|---|
| `:1730` | `def store_target` | **`:2070`** |
| `:377` | `ASSIGN = (...)` | **`:404`** |
| `:1753-1754` | the `==` rejection | **`:2093-2094`** |
| `:1750-1751` | the reason, in the function's own comment | **`:2090-2091`** |
| `:1752` | the 838 tree-wide count | **`:2092`** |
| `:757-758`, in the `ORACLE` opening at `:638` | the `131 -> 146` / `146 -> 150` record | **`:828-829`**, `ORACLE` opening at **`:708`** |

*Nothing else on this page moves: the six anchors are the same six, in the same
order, and the reasoning here and below is a reading of their surroundings
rather than of their line numbers. **This is the same shape the page describes**
— a corrected pointer a later growth of the tool makes stale again — so the note
worth recording is the shape and not the arithmetic. The nine anchors
`check_eq_guard_citations.py` does hold were re-pointed with #907 and its run is
green; the rest of the class is §"What is left" below, and is not swept by a
change that grows the tool.*

## The six, measured

The block quotes six live pointers in its own present tense, outside the
quotation marks that hold its superseded direction split. All six had drifted:
`ec/tools/xdata_register_map.py` is **5,034** lines now, and the block's own
figures were a different module. Measured on the tree this lands in, each target
re-read rather than inferred:

| the block said | it names | the issue proposed | **measured** | what is there now |
|---|---|---|---|---|
| `:505` | `def store_target` | `:1572` | **`:1730`** | `def store_target(text: str, start: int, end: int, eq_guard: bool = True) -> bool:` |
| `:165` | `ASSIGN = (...)` | `:359` | **`:377`** | `ASSIGN = ("=", "\|=", "&=", "+=", "-=", "*=", "/=", "^=", "%=", "<<=", ">>=")` |
| `:524-525` | the `==` rejection | `:1593-1595` | **`:1753-1754`** | `if eq_guard and stripped.startswith("=="):` / `return False` |
| `:515-516` | the reason, in the function's own comment | `:1593-1595` | **`:1750-1751`** | `# A separate test rather than a reordering of ASSIGN, because the two` / `# exclusions are unrelated and \`==\` is by far the commoner of them:` |
| `:523` | the 838 tree-wide count | `"eq_after"` at `:1322` | **`:1752`** | `# 838 occurrences in the committed tree against two dereference stores.` |
| `:258-259` | the `131 -> 146` / `146 -> 150` record | `:668-669` in `ORACLE` at `:549` | **`:757-758`**, in the `ORACLE` that opens at **`:638`** | `# 131 -> 146 with issue #180's 15 0x086x/0x1Cxx/0x1Fxx entries.` / `# 146 -> 150 with issue #183's 0x07C4/0x07D3/0x07D4/0x07D5.` |

**The issue's own replacement figures were stale too, and that is worth
recording rather than quietly using the right numbers anyway.** Every one of
the six is wrong in the issue, five of them by 18 to 160 lines and the sixth
— the `:523` row — by 430: `:1593-1595` is inside `store_target` but well
short of the two constructs the block is about, and `:1322` is a blank line
rather than a line number pointing at anything. On the `:523` row it also
names the wrong *shape*: the entry it means,
`DIRECTION_INVARIANT["eq_after"]`, is real and is at `:1480` — but the block's
`:523` sits between the reason and the rejection, so it is a
`store_target`-internal pointer and lands on the `# 838 occurrences` comment at
`:1752`, not on a `DIRECTION_INVARIANT` row at all. The measurements above are
the ones used; the issue's are recorded here so the next reader can see which
list was re-derived.

Two details of the old figures are worth keeping, because they are the reason
this class is hard rather than merely tedious. **`:523` was a blank line** — it
resolved to nothing, so no amount of re-reading would have caught it by
inspection, and it is the same shape `test-line-pin-census.md` §"Why no checker"
counts as its "6 a blank line" (item 1 of four). And **`:258-259` is not in a
neighbouring definition either**: it is a comment inside the `ORACLE` literal,
which spans `:638-791`, and the record the block means sits 119 lines below the
literal's opening, in the header comment run rather than anywhere near a data
row. Nothing about the old span's surroundings would have pointed a reader to
the replacement.

**`:64-75` still resolves and was not repointed.** `:64` is the module
docstring's `==` rule and `:75` its closing sentence; the issue notes it rather
than listing it among the six, and that is right. Confirmed by re-read; it is
left alone.

## Why nothing holds them — two corrections to the issue's own account

The issue explains the six's being unheld by mechanism, and **both halves of
that mechanism claim are false.** The wrong version stays visible here, per
CLAUDE.md's retraction rule.

**The issue said, in full, that** "`check_citation_lines.py`'s `supersession()`
skips a whole paragraph when any line opens with `>` or the paragraph opens with
`CORRECTION`. So the entire block … is passed over, and the merge's run reports
`26 citation(s) resolve … 8 skipped as superseded` **with these six inside the
eight**."

> **Corrected 2026-09-26, issue #870.** `supersession()` **never fires on this
> block**, and the six are **not among the eight skips**. Both are measurable,
> and the measurement is: a YAML folded scalar contains no blank lines, so the
> whole `XDATA_0860` entry (raw lines 2968–3106) is *one* paragraph whose
> opening is `name: XDATA_0860`. The `*** CORRECTION` marker sits at 2990, the
> `*** ADDENDUM` at 3025 and the 2026-09-26 one at 3082 — all three *inside*
> that paragraph. `supersession()` tests `lines[0]`, so it returns `''` for all
> three, verified by importing the tool and calling `supersession()` on the
> entry's real paragraph. The three `***` markers in the tree are the reason a
> rule that skipped corrections would have looked correct here, not a
> demonstration that it does.
>
> The eight skips are three in `xdata-086x-dispatch.md`, three in
> `reset-vector-dptr-targets.md`, and two in the `HAND_CHECKED["0x0860"]`
> comment — `--verbose` names all eight with a reason, and the six are in none
> of them.

**The two reasons that do hold** are both mechanical, and neither is the
vocabulary:

1. **`registers.yaml` is in neither `bodies` nor `ROW_SCOPE`.** The tool's
   `main()` walks `bodies` — `xdata-086x-dispatch.md`,
   `reset-vector-dptr-targets.md` and `xdata_register_map.py` — so the file is
   never read at all. This is "not done by this method", never "there is
   nothing there".
2. **`POINTER` is `([\w-]+\.csv):(\d+)`,** a generated-CSV pointer and nothing
   else. All six point into a `.py`. A `.py` pointer is outside the one pointer
   rule whatever the supersession vocabulary says, so refining that vocabulary
   would not hold a single one of the six.

This is also why the docstring's `registers.yaml` bullet, `prose-line-citations-held.md`
§"Coverage, stated plainly" and `docs/findings.md` §58 all gave a reason that
was wrong on its own terms — each said the file's cells are unheld *because*
every live sentence in the note is a `*** CORRECTION` paragraph. That reads
well and is not what is happening. All three now carry the measured reason, and
`§4a-4d` is still what it was: the quoted predecessor has to stay visible. In
`registers.yaml` that is an **inline correction beside the standing clause**, not
a rewrite of it: the `NOT CHECKED HERE` paragraph keeps its 2026-09-25 "because
every live sentence in this note is a `CORRECTION` paragraph" verbatim, and the
measured reason follows it under a dated bold correction. That file is the one
where the distinction costs most — the merge is a squash, so once this lands the
2026-09-25 wording is recoverable only from what the file itself still says.

## The vocabulary question, decided

#801 asked, and said either answer was defensible: should a correction
paragraph that makes *new*, checkable assertions be checked for the subjects it
declares, with only the quoted run skipped? **No. The paragraph-wide skip
stays, and `registers.yaml` stays out of `ROW_SCOPE`.** This is not a taste
call, and the number behind it is one run.

Scoping the file in was measured, not assumed — `check_row_pointers` over
`registers.yaml` with a `ROW_SCOPE` entry for `0x0860` — and it goes red
immediately, with seven reports, of which the one that decides this is:

```
ec/annotations/registers.yaml:3008: cites xdata-registers.csv:662, which is the 0x077E row,
  not the 0x0860 row at 817 -- a rank into a file that keeps growing, so the address is what
  a citation is held to, not the number
```

**`:3008` is the 2026-09-24 block's own live prose, not quoted material.** It
reads "The committed row at ec/annotations/xdata-registers.csv:662 is 14 read, 2
write, 0 read+write, 1 passed-to-call" — the block's own present-tense
assertion, six lines past the quotation mark that closes the quoted run at
`:3002`. The quoted run is the opposite case: at `:2994` it names
`ec/annotations/xdata-registers.csv` with **no row number**, so it holds no
pointer a check could fail on. The entry carries three `.csv:NNN` pointers in
all, at `:3008`, `:3029` and `:3035`, and both reports for the `:662` print
`:3008` — the addendum's second `:662`, at `:3029`, rides on the first because
`line_of()` returns the paragraph's *first* line holding the needle.

So the red is not §4a-4d's quoted figure, because nothing in the quotes is a
row pointer. It is one of the **four pointers the 2026-09-25 addendum corrects
by record and deliberately leaves standing** (the asymmetry, below): the same
paragraph already says `:662` is the `0x077E` row and that `0x0860` is at
`:817`. A rule scoped to the file would be red, then, on a pointer a dated
record in the same paragraph already covers — which is
`check_citation_lines.py`'s own stated reason for the skip (*"a check that
reddened on its own corrected tree would be switched off, and then nothing
would be left"*, `check_row_pointers`, the comment on the `if why:`) arriving on
a file it had only been argued about, on the right ground rather than the one
first claimed here.

**A second reason, and the more structural one:** Rule 3 does not scope a
*file*, it scopes a `(file, csv, subject, column)` tuple, so putting
`registers.yaml` in `ROW_SCOPE` is an entry per CSV that file cites rather than
one line of configuration. It cites four, and the run reports the other three —
five pointers, each "this tool declares no subject of … in this file":
`ec-callsites.csv:62`/`:63` and `ec-callsites-summary.csv:42`/`:43` at `:1684`,
`:1685` and `:1793` (all outside this entry), and
`xdata-0860-census-sites.csv:6` at `:3035`, inside it. That last one is a
*hand-maintained* correspondence file — `ec/README.md` records it as derived
from nothing in the image — whose columns (`region,file_offset,census_state,
census_bucket,census_count,census_refs`) hold no address to declare a subject
on, so `POINTER` matching any `.csv` is by itself enough to redden the file.
Even with the `:662` recorded away, the scope entry is not one row.

**Consequence, stated plainly: the six stay hand-maintained**, like the note's
other pointers. The tool that would actually hold them is follow-up 1 in
[`prose-line-citations-held.md`](prose-line-citations-held.md), and building it
is out of scope for an issue whose deliverable is six numbers.

## The asymmetry, which is the reason this is an issue at all

The same 2026-09-24 block carries **four** other pointers that have *also*
drifted — `:662`, `bank0/D281.c:18`/`D289.c:17`, `:359` and `:1490-1496` — and
those are **left exactly as they are.** The difference is not which pointer is
wrong; it is whether a record already says so:

- The **four** were corrected *by record* in #801's 2026-09-25 `*** ADDENDUM`,
  which names each stale figure, names its replacement, and quotes the old one
  verbatim. Editing them now would falsify a §4a-4d record to no gain: a reader
  who finds `:662` can follow the addendum straight to `:817`.
- The **six** had no record at all. That was the state this issue exists to
  end — "a live claim in `registers.yaml` that is wrong with no record that it
  is wrong."

So the six are repointed in place, and the 2026-09-26 `*** ADDENDUM` says which
treatment each pointer got and why, so the difference is stated rather than left
for a reader to infer from which numbers moved. It also records the two
**source-file pointers of the addendum's own** — `:1399` → `:1557` and
`:3606-3619` → `:4073-4085` — which had drifted again since 2026-09-25 and are
corrected in place for the same reason the six were: leaving known-wrong live
pointers in the sentence that records the fixing of live wrong pointers would
be incoherent. The 2026-09-25 sentence's own measurements stand as a dated
record of what was true that day, superseded rather than edited.

## What changed, and what deliberately did not

- **Changed:** six line numbers in the 2026-09-24 block's prose; two in the
  2026-09-25 addendum's own; the tense of one adjacent observation; the
  `NOT CHECKED HERE` reason, in `ec/annotations/registers.yaml`; the
  `registers.yaml` bullet and one stale sub-reference in
  `ec/tools/check_citation_lines.py` (**docstring only** — `bodies`,
  `ROW_SCOPE`, `POINTER`, `MARKERS`, `ANNOUNCES` and `supersession()` are
  untouched and the run's output is byte-identical); one new case in
  `ec/tools/test_check_citation_lines.py`; and three places in
  `prose-line-citations-held.md`, which this discharges follow-up 2 of.
- **Not changed:** `ec/tools/xdata_register_map.py` — it is what the six point
  *into*, and editing it would move them again; the four pointers corrected by
  record; the quoted direction split; `ec/README.md` (its statements are true
  and general); `tools/README.md` (its blockquote says suite and test counts
  are deliberately not updated, and `test_readme_suite_table.py` compares the
  row *set* and never the counts, so a count bump needs no edit by the
  repository's own recorded decision); `test-line-pin-census.md` §"Why no
  checker" (this issue's measurement reinforces it — see the blank line at the
  old `:523` — and changes nothing in it); and the generated CSVs and Ghidra
  projects.

## The one new test, and the case it is not

`test_a_correction_marker_inside_a_yaml_entry_is_still_checked` asserts that a
blank-line-free YAML-shaped entry whose `*** CORRECTION` marker is
**mid-paragraph** is still checked, because the announcement is not the
paragraph's opening. It pins the fact that decides the vocabulary question, and
that fact was previously implicit in `paragraph()`.

The counterpart the issue asked for — asserting a quoted run is still skipped —
**already exists**, and is not duplicated here:
`test_a_blockquoted_supersession_is_skipped` and
`test_a_correction_paragraph_is_skipped` are its two halves, and both pass.

## Verified on this tree

`python3 ec/tools/check_citation_lines.py` exits 0 with `26 citation(s) resolve
to the row they name, 8 skipped as superseded`. **The unchanged counts are
themselves the proof** that the docstring edit did not quietly widen the tool's
scope: both figures are what the tool printed before it, over the same three
files. `python3 -m unittest discover -s ec/tools -p test_check_citation_lines.py`
runs **41** cases green, 40 before this issue and one added.

The new case was shown to go red, by moving the marker to the paragraph's
opening in its own fixture — which is the only way it can be, since a YAML
entry's paragraph always opens with `name:` and never with the marker:

| fixture | checked | skipped | problems |
|---|---|---|---|
| as committed (paragraph opens `  - name:`) | 0 | **0** | 1 |
| same text, paragraph opens with `*** CORRECTION` | 0 | **1** | 0 |

The six themselves were shown to be **unheld**, which is the honest form of
this demonstration. `store_target()` was put back to its stale `:505` and every
check in the repository that could have noticed was run: `check_citation_lines.py`
still reported `26 / 8` and exited 0, and `registers.yaml` still parsed with
`XDATA_0860` at `present-untested`. The edit was reverted. That silence is the
finding, and it is why the consequence above is "hand-maintained" rather than
"now held".

`python3 -c "import yaml; yaml.safe_load(open('ec/annotations/registers.yaml'))"`
parses, `XDATA_0860` is still `present-untested`, and the block's quoted
direction split — `13 write, 3 read+write, 1 passed-to-call, 0 read` — is still
present, still inside quotation marks, exactly where §4a-4d put it.

## What is left

The tool that would hold a prose → source-line pointer is follow-up 1 in
[`prose-line-citations-held.md`](prose-line-citations-held.md), and
`test-line-pin-census.md` §"Why no checker" argues at length that it needs a
judgement no rule here can make — 74 pins, six of them blank lines, no single
anchor covering them. A new tool of that size is its own issue. A prepared gate
patch for `check_citation_lines.py` stays follow-up 3 there, for the reason
that file gives.

Submitting anything upstream is unaffected: this touches no driver, and the
mission's eventual `Wer-Wolf/uniwill-laptop` / `tuxedo-drivers` contribution
stays a prepared patch in this repository for a human to submit, per issue #10.
