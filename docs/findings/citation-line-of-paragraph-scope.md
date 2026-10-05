# `line_of` reported a paragraph's first match, not the citation's own line (issue #1051)

**Issue #1051.** `check_citation_lines.py`'s `line_of` stated a standard its
implementation did not meet, and the recorded instance of the gap was a live one
waiting for a scope entry. This decides the question the issue left open and
makes the code meet the docstring.

**Nothing here is about the firmware.** `line_of` reads a string this repository
wrote. No EC is opened, no register read back, no capture taken, and no laptop,
EC or Windows machine is involved. No `status:` moved, no CSV or Ghidra export
was regenerated, and every figure the prose asserts about the hardware is
unchanged — this changes which line a report *names*, not what it reports.

## The defect, reproduced

`check_row_pointers` finds each citation in one **sentence** — `units()` yields
`(lineno, unit)` and `POINTER.findall` runs on the unit — but handed `line_of`
the whole **paragraph's** raw lines and the bare `name:cited` string, so the
search returned the first line of the paragraph containing that string
*anywhere*. `paragraph()` makes a folded `note: >` scalar one paragraph, so a
register entry that names the same generated-CSV row in two of its sentences is
one run of non-blank lines and both reports land on the first occurrence's line.

The recorded instance is `registers.yaml`'s `XDATA_0860` entry, measured here:
the entry opens at `:4693` and its paragraph runs unbroken from there, naming
`:662` twice — as `ec/annotations/xdata-registers.csv:662` at `:4733`, the
2026-09-24 block's live prose, and as the bare `xdata-registers.csv:662` at
`:4754`, the 2026-09-25 addendum's. `POINTER` keys on the basename, so those are
one needle found twice. Running
`check_row_pointers` over that file with a `ROW_SCOPE` entry for `0x0860`
printed the same line twice:

```
  moved ec/annotations/registers.yaml:4733: cites xdata-registers.csv:662, which is the 0x077E row ...
  moved ec/annotations/registers.yaml:4733: cites xdata-registers.csv:662, which is the 0x077E row ...
```

The second report names a line its citation is not on, which is the exact
failure `line_of`'s own docstring calls worse than pointing at none. It is
latent only because `registers.yaml` is in neither `bodies` nor `ROW_SCOPE`, so
no rule walks the file — it goes live the moment anything scopes it in, which is
the direction `docs/findings/xdata-0860-note-live-pointers.md` already decided
against on other grounds.

## Why the fix counts rather than floors

Two narrower fixes were available. Flooring the search at the unit's own line
fixes the recorded instance — the two citations there are in different
sentences — and leaves the committed tree's output byte-identical. It does not
meet the docstring's standard in the case where the same needle appears twice
inside *one* sentence across a wrap: both reports still collapse onto the
sentence's first line. Measured, on a fixture in the `registers.yaml` shape:

| the reports named | two sentences | one wrapped sentence |
|---|---|---|
| before | `[3, 3]` | `[3, 3]` |
| floor only | `[3, 5]` | `[3, 3]` — still the same line twice |
| **counting (shipped)** | `[3, 5]` | `[3, 4]` |

Shipping the floor and describing it as meeting the stated standard is the
overclaim CLAUDE.md's calibration rule is about, so the fix counts.
`line_of` takes the ordinal of the citation among those sharing its needle
within the unit, and returns the line of that occurrence at or after the unit's
own line. The per-needle counter falls out of the loop that already existed —
`check_row_pointers` iterates `POINTER.findall(unit)` — keyed on
`f"{name}:{cited}"` and reset per unit, because the unit is the scope being
counted in.

**The paragraph is still what gets searched**, and that is deliberate rather
than incidental: `supersession()` reads the whole run, because a blockquote's
`>` can open any line of it. A blockquote whose citing sentence is *not* its
first — the `>` opening one sentence and the citation landing in the next — is
skipped when the whole paragraph is passed and **checked** when only the
sentence's lines are. That is the one outcome this tool's vocabulary exists to
refuse, so `line_of` floors internally and the caller keeps passing `raw`.

**The fallback is defensive.** No committed file splits a citation across a
wrap, and one cannot reach the rule that way either: a needle `POINTER` matched
in a unit's joined text is always on a single raw line of the paragraph — the
join inserts the space a match could not straddle — and always at or after the
unit's own line. So the needle-absent branch is pinned by calling `line_of`
directly rather than through the rule, which is what it lands on when the
sentence's line is where the claim was found rather than the paragraph's first.

## Nothing on the committed tree moved

With `line_of` swapped, `main()`'s exit code, stdout and stderr are
byte-identical on this tree, because no committed paragraph names the same
generated-CSV pointer twice. That is the evidence the guard on the published
prose did not shift, and it is the property the issue's "any that moved named
and explained" is really asking about.

The `--verbose` baseline is this run's output, reproduced by
`python3 ec/tools/check_citation_lines.py --verbose`:

```
  skip (quoted material) ec/annotations/xdata-086x-dispatch.md:179 xdata-overrides.csv:4
  skip (quoted material) ec/annotations/xdata-086x-dispatch.md:290 xdata-registers.csv:662
  skip (quoted material) ec/annotations/xdata-086x-dispatch.md:292 xdata-registers.csv:817
  skip (quoted material) docs/findings/reset-vector-dptr-targets.md:484 xdata-registers.csv:583
  skip (quoted material) docs/findings/reset-vector-dptr-targets.md:486 xdata-clusters.csv:101
  skip (quoted material) docs/findings/reset-vector-dptr-targets.md:489 xdata-clusters.csv:82
```

The issue recorded eight such lines. The two that are absent are not this
change's doing: they were the `HAND_CHECKED["0x0860"]` comment skips, and
**Rule 2 and that comment were both removed** — the comment went with the
per-address count pins it justified, and the rule with it, which the tool's own
docstring records. Three of the six moved with the dispatch page's growth
(`:167`→`:179`, `:258`→`:290`, `:260`→`:292`); the three
`reset-vector-dptr-targets.md` skips are unmoved. These are positions in
committed files, recorded because they are this run's output rather than a count
of the tree; nothing holds them to the current ones.

## The stale pins this corrected in passing

The module docstring's own record of this instance named `registers.yaml:3008`,
a bare `file:NNN` that had moved twice since. Measured, it is `:4733` and
`:4754` now. Two neighbouring pins were stale the same way and were measured
rather than guessed at the same time: the `:3013` this bullet's sibling
attributed the `:359`/`:1490-1496` source-file pointers to, and the
`xdata-086x-dispatch.md:326` that Rule 3's rationale cited for a sentence
naming no address. All three now name what they point at rather than a line
number, which is the same "hold the address, not the number" principle the tool
applies to the CSVs, applied to its own prose.

## What this does not do

- **Scoping `registers.yaml` into `ROW_SCOPE`** stays out. That is the separate
  decision already measured and recorded in
  `docs/findings/xdata-0860-note-live-pointers.md`; this fixes the report so that
  work is not done against a wrong line, and does not do that work.
- **The `.py:NNN` pointer class** is a different tool with its own
  false-positive surface, and those cells stay fixed by hand.
- **Needle matching is still by substring**, unchanged, including the
  pre-existing adjacency where one citation's needle is a prefix of another's.
  Nothing here measures that further.