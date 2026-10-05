# `--sites` refuses an address outside the PD region, and the arithmetic the census's row 10 declined to guard becomes a statement about the code

(2026-09-25, issue #848. Static reading and commands over one committed image.
No capture opened, no EC, no hardware, no Windows.)

[`opcode-len-bounds-census.md`](opcode-len-bounds-census.md) row 10 declines to
add a guard to `pd_index_geometry.py`'s `site_rows()` on principle, and then
records in the same paragraph a property of the CLI it declines to fix:

> **the code does not clamp it**, so a caller naming `0x1FFFF` would walk off
> the region. That is a property of the CLI, stated here so the figure above is
> not read as a bound the code enforces.

That sentence is a claim about the code resting on the reader's word, and the
code was in fact worse than the sentence: it did not clamp the address, and it
did not diagnose one either. `--sites 0x1FFFF` raised a bare `IndexError` from
the middle of the listing loop. **This change makes `site_rows()` refuse an
address outside the PD region by name**, with a message naming the region, its
legal runtime range, its file range, and the value it was given, and it
replaces the census's row-10 caveat with a pointer here.

The census's principle is not overridden, and the reason it is not is the
second section below, which is the part worth reading: a range check on a
*caller's argument* is a different kind of guard from the reachability-in-this-
image one row 10 declined, and the difference is not a matter of taste.

The write-up is a new file; the shared files it touches get a row, a section, a
bullet and a retraction, and no prose is relocated.

## What was measured

Every number below was re-run at this tree while implementing, not copied from
the issue. The firmware is `ec/firmware/GMxMGxx_11.800` throughout, and `T` is
`python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800`.

### Before the change

| command | result |
|---|---|
| `T --sites 0xFFFF` | exit 0 |
| `T --sites 0x1FFF0` | exit 0 |
| `T --sites 0x1FFF1` | `IndexError: index out of range` at the listing append |
| `T --sites 0x1FFFF` | `IndexError: index out of range`, the issue's vector |
| `T --sites 0x23478` | `IndexError: index out of range`, **at a different line** — see correction 2 |
| `T --callers 0x1FFFF` | **exit 0** — prints a three-row byte-scan caller list |
| `T --helpers 0x1FFE8` | exit 0 |
| `T --helpers 0x1FFE9` | `IndexError` |
| `T --self-test` | exit 0 |

The census's other command is unaffected by anything here and was not touched:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
    0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
    0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv --census-column --check
```

### After the change

| command | result |
|---|---|
| `T --sites 0xFFF0` | exit 0, 20 lines, **byte-identical** to before |
| `T --sites 0xFFFF` | exit 0, 20 lines, **byte-identical** to before |
| `T --sites 0xC2FA 0xDA9B` | exit 0, 40 lines, **byte-identical** to before |
| `T --sites 0x1FFF0` | **exit 2**, named range, no traceback |
| `T --sites 0x1FFF1` | **exit 2**, named range, no traceback |
| `T --sites 0x1FFFF` | **exit 2**, named range, no traceback |
| `T --sites 0x23478` | **exit 2**, plus the `file_offset` second line |
| `T --sites zzz` | **exit 2** — it was a `ValueError` traceback before |
| `T --self-test` | exit 0 |
| `--helpers`, `--bases all`, `--strides all`, `--callers 0x0860`, `--accesses` | **byte-identical** to before, every one |

The byte-identical rows are the load-bearing evidence, and they are a diff
rather than an impression: the pre-change file was extracted from `HEAD`, both
copies were run over the same image, and the outputs compared with `diff -q`.
Every mode that could have been affected by a check added to `site_rows()` is in
that list, so "no behaviour changed on the legal range" is a measurement.

The refusal itself:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0x1FFFF
pd_index_geometry.py: error: 0x1FFFF is not a pd-image runtime address: that
region is 0x0000-0xFFFF at run time, 0x20000-0x2FFFF in the file
$ echo $?
2
```

and for the plausible mistake, which is the second line:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0x23478
pd_index_geometry.py: error: 0x23478 is not a pd-image runtime address: that
region is 0x0000-0xFFFF at run time, 0x20000-0x2FFFF in the file
  0x23478 is inside the file range, which is where a site's file_offset lives;
  the runtime address there is 0x3478
```

`0x23478` is not a contrived number: it is the first `file_offset` in
`../../ec/annotations/ec-0x07d0-sites.csv`, whose `runtime` column reads
`0x3478` on that same row. The diagnostic's second line reproduces the CSV's own
answer, which is a check on the hint that costs nothing to make.

**`--sites zzz` is the one behaviour change the plan did not call out**, and it
is recorded here rather than left for a reviewer to find. The `try` that turns
`check_site_addr()`'s `ValueError` into `ap.error` necessarily also covers the
`int(a, 16)` on the same line, so a non-hex argument is now a diagnostic and
exit 2 where it was an unhandled `ValueError` traceback. Same failure mode, same
place, and strictly better; noted because it is a second input whose behaviour
moved.

## Three corrections, each with the wrong version left visible

Per the `docs/findings.md` §4 pattern, none of these is a silent replacement.

### 1. The issue's threshold is wrong, and the census's peak is a bound rather than the peak

The issue puts the boundary at `0x1FFFB`. **The first address that
raised was `0x1FFF1`**; `0x1FFF0` exited 0, and both are reproduced above. The
reason is the fill, not the arithmetic the issue did: the window is
`SITE_WINDOW` = 16 instructions, and **every byte from file `0x30000` to
`0x40000` is `0xFF`**, with `OPCODE_LEN[0xFF]` = 1, so the 16th read lands at
`0x20000 + addr + 15` and the first raiser is `0x40000 - 15 - 0x20000` =
`0x1FFF1`. The issue's own worst-case figure (`+ 45`, three-byte instructions)
would have put it at `0x40000 - 45 - 0x20000` = `0x1FFD4`, so `0x1FFFB` is
neither the observed boundary nor the arithmetic one.

That same arithmetic is why the census's row-10 figure needs a word added.
`0x3002C` is `0x2FFFF + 45` — **the worst case of fifteen three-byte
instructions**, not the read this image performs. Walked from `0xFFFF`, the
sixteenth read actually starts at `0x2FFFF + 15` = **`0x3000E`**, because the
window runs into the same `0xFF` fill. The census says "peak read `0x3002C`";
the realised peak is `0x3000E` and `0x3002C` is its ceiling. The row's cell now
says so, and the self-test pins the realised figure as a floor, with the bound
beside it.

**Where the `0xFF` premise comes from, and what now holds it (issue #861).**
When this section was written, the sentence "every byte from file `0x30000` to
`0x40000` is `0xFF`" had the image as its only citation, while `0x3002C` beside
it cited a census row. That is two levels of backing for the three constants
one assertion holds up. The missing citation is the
`("erased", 0x30000, 0x40000, None, "all 0xFF")` row of
`../../ec/tools/trace_xdata_refs.py`'s `REGIONS` — the map of the image, whose
`how` column every consumer of that table discards, so it was a string in a
column nothing read. It is now read:

```sh
python3 ec/tools/check_image_map.py ec/firmware/GMxMGxx_11.800
```

which measures the band in full, prints its size, its distinct byte values and
its `0x90` count, and reports the four rows it does not check as `unchecked`
with the tool that owns each. The measurement is
[`erased-band-fill-claim.md`](erased-band-fill-claim.md).

Two changes followed from the citation, and both are in
`../../ec/tools/pd_index_geometry.py`. The comments above the `0x3000E` floor
and above the `0x1FFF1` boundary now name the row, `OPCODE_LEN[0xFF] == 1` and
the command, so all three constants cite the same thing. And the premise is
**asserted rather than described**: the self-test asks the band predicate
imported from `check_image_map.py` whether the row still holds, immediately
before trusting `0x3000E` as a floor, so a dump whose `0x30000` band is not
`0xFF` goes red on the premise instead of quietly changing what the floor
means. It reads the same predicate that tool measures the whole column with,
so the two cannot come to disagree.

That is the whole of what changed in the arithmetic, and the figures above are
unchanged on the committed image: `0x1FFF1` is still the boundary, `0x3000E` is
still the realised peak and `0x3002C` is still the ceiling.

**Correction (2026-10-05, issue #1014): the premise assertion above has been
deleted, and the peak figures are now a record rather than a description.**
`site_rows()`'s listing loop is bounded at the region end, so the floor it
rested on is gone: the last read comes from `pd_bounds()` and not from the
bytes past `0x30000`. `erased_band_holds()` went with it rather than standing as
a check whose stated claim backs nothing, and the `python3 ec/tools/
check_image_map.py <image>` named in the paragraph above is where the `all 0xFF`
claim is asserted now — it puts the band to that test and refuses one whose
bytes do not satisfy it. The doctored-image table below was measured against
the assertion as it stood and is kept as the record of what it showed; the
peak column's figures are the pre-change walk's. The `0x1FFF1` boundary does
not move, for the reason the table already gives.

**What a doctored image does, measured, because "the premise is now asserted"
is worth nothing if nothing else would have moved anyway.** One byte changed at
`0x30000` of a copy of the firmware:

| byte at `0x30000` | new assertion | `--sites 0xFFFF` peak | `0x1FFF1` refusal |
|---|---|---|---|
| `0xFF` (the committed image) | ok | `0x3000E` | unchanged |
| `0x00` `nop` | **red** | `0x3000E` | unchanged |
| `0x74` `mov a,#imm` (2 bytes) | **red** | `0x3000F` | unchanged |
| `0x90` `mov dptr,#imm` (3 bytes) | **red** | `0x30010` | unchanged |

(Every figure in the middle column is the pre-change listing's. After issue
#1014's bound the peak is `0x2FFFF` in all four rows, because the region's end
and not the byte at `0x30000` decides where the listing stops. The premise still
goes red in every case, but from the tool that owns the claim rather than from
this one: `python3 ec/tools/check_image_map.py` on each of the three copies
refuses `0x30000` by name and exits 1, while `pd_index_geometry.py --self-test`
is green on all three.)

Three things are visible there and worth separating. The **premise** goes red in
every case, which is the change #861 was for. The **peak** moves by one or two
bytes with the replaced instruction's length and the range assertion still
passes — that is the `0x3000E <= peak <= 0x3002C` *range* doing its job rather
than a figure being re-derived, and it is why the self-test pins a floor and a
ceiling rather than `0x3000E` alone. And the **`0x1FFF1` boundary does not move
at all**, which is the correction to a natural wrong reading: since #848 that
refusal is `check_site_addr()`'s, a property of the *argument's* 16-bit width
and the region's extent, so it holds whatever the fill beyond `0x30000` is
made of. `0x1FFF1` is where the pre-change walk ran off the end, and it is
still the right arithmetic for that, but the code no longer depends on the fill
to produce it.

**One consequence of the change itself, stated here because it is not what a
reader of the issue's transcript would expect.** The check refuses anything
`>= 0x10000`, so `--sites 0x1FFF0` is now **exit 2 as well**, not exit 0. That
is not a regression and not a narrowing: `0x1FFF0` was never a PD runtime
address on any target — an 8051's DPTR is 16 bits, which is why the module
preamble already says every address wraps modulo `0x10000` — it was only
*accepted*, because nothing checked. The `0x1FFF0` / `0x1FFF1` pair is therefore
a boundary of the **pre-change** code, and the check supersedes it by refusing
both. It stays on the page because it is what the census's arithmetic is about,
and a reader checking that arithmetic needs both numbers.

### 2. The plausible-mistake vector fails one line earlier than the issue says

The issue reports `site_rows()` `:600` as the raising line. **The `file_offset`
vector fails at the other read**, the `MOV DPTR` immediate two bytes above
`i`, and it fails there whether or not the `0x1FFF1` path is taken. The census's
row-10 arithmetic only ever considered the listing loop's reads, so this one was
outside its model. The check is placed above both of them, so which line would
have raised is now a question with no answer on the legal range.

### 3. #843's "the only two" is twelve under the literal test, and four under the issue's

See its own section below.

## Why this check is not the guard row 10 declined

This is the part a reviewer should check hardest, because the obvious reading is
that the census's principle has been quietly reversed.

Row 10's reasoning is sound and is not being touched. Reachability there was a
property of **a committed input that can change**: the image is 262144 bytes
today, and that number is why the window did not walk off the end. A guard
written on that basis is a guard justified by an assumption about one file, and
`docs/findings.md` §4 is a page about exactly that mistake.

The new check is not justified by the image, and the difference is not
rhetorical — the two guards would behave differently on a **different dump**,
which is the test that separates them:

- The census's would be a statement about *this* file's spare 65492 bytes. Swap
  in a smaller image and it is false, or vacuous, and nothing in the code says
  so.
- The new one is a statement about the **shape of the argument**. `--sites` is
  documented as taking PD runtime addresses; a runtime address is 16 bits wide
  on this target, and `pd_bounds()` is the tool's own map of where the PD image
  lives in the file, so `0 <= addr < hi - lo` is a property of the interface that
  holds for **any** dump. On a different image the committed CSVs would be wrong
  and this check would still be right, which is exactly the case the image-based
  argument cannot cover.

So it tests the caller's *argument*, not the image's *bytes*, and it is the same
kind of check `parse_span()` has always made on `--bases` / `--strides` — the
one whose refusal `main()` already turns into `ap.error` for a span outside
`0x0000-0xFFFF`. The failure mode is reused rather than invented, which is why
the diagnostic arrives as `pd_index_geometry.py: error: …` and exit 2.

**The instruction-boundary precondition deliberately stays a precondition**, and
the two now sit side by side in `site_rows()`'s docstring so that neither reads
as the only one. The boundary is not decidable from the bytes: nothing in an
image says where a routine's instructions begin, a caller naming a mid-instruction
address gets a listing that is visibly wrong rather than refused, and that
listing is the mechanism the tool already relies on. Refusing there would be
guessing at a question the bytes do not answer.

## What the check does not do

- **It does not make the peak read into "cannot raise".** What the check bounds
  is the *start* address, not the reads: `0 <= addr < 0x10000` puts the first
  read at `0x20000-0x2FFFF`, and from there the window's furthest possible read
  is bounded at `0x3002C` by the code rather than by this image's spare bytes —
  a different and stronger sentence than the one row 10 carried. It is still
  **not** "cannot raise", and a *legal* address's reads did still leave the
  region: `--sites 0xFFFF` started in-region at `0x2FFFF` and its last read
  started at file `0x3000E`, 14 bytes past the region's last byte. The realised
  peak on this image was `0x3000E`, a property of these bytes, and the
  `0x3002C` ceiling was arithmetic. What the check removed is the *unbounded*
  direction, and only that.
  **Correction (2026-10-05, issue #1014): the listing loop is now bounded at the
  region end, so a legal address's reads no longer leave the region.**
  `site_rows()` takes both ends of `pd_bounds()` and stops at `0x30000`, naming
  the end in its own stop reason; `--sites 0xFFFF` now reads one instruction,
  at `0x2FFFF`. This change does not touch `--callers`. See
  [`site-rows-window-bound.md`](site-rows-window-bound.md).
- **It does not make `--callers` consistent with `--sites`.** Measured above:
  `--callers 0x1FFFF` **exits 0** and prints a three-row byte-scan caller list.
  It has no traceback to replace, and its output is the over-counting the module
  preamble already documents. Recorded so that nobody reads the two arguments'
  identical argparse declarations (`:1792-1796`) as an identical contract.
  *(**Correction, 2026-09-28, issue #860.** False at this tree, and left here
  because it was true when measured. `caller_rows()` reaches
  `check_site_addr()` through the `site_rows(d, [site])` it already makes to
  decode each site's index registers, so `--callers 0x1FFFF` **exits 2** with
  the diagnostic `--sites` gives — re-measured, and `--callers 0x23478` with the
  `file_offset` second line. The warning above is answered rather than
  repeated: the two arguments' declarations are now one contract, and
  [`pd-index-geometry-address-contract.md`](pd-index-geometry-address-contract.md)
  carries the re-measured table and the three `--help` strings that make it
  legible. `:1792-1796` was this tree's line numbers when this section was
  written; the declaration is at `../../ec/tools/pd_index_geometry.py:2394`
  now.)*
- **It does not fix `walk_helper`.** `--helpers 0x1FFE9` raises, measured above,
  and is left raising. A blanket range check there would also have to cover the
  targets `chain_from()` decodes out of the image's own branch operands and
  hands it at `:546` — a different contract from a user-typed anchor — and the
  question of what invariant a count-bounded walk is meant to enforce is the
  census's own open follow-up 1, which deferred it as a design question rather
  than a bug report. Fixing it here would pre-empt that.
  *(**Correction, 2026-09-28, issue #860.** False at this tree on both counts.
  `--helpers 0x1FFE9` **exits 2** now rather than raising bare, and the walker
  itself no longer discards `pd_bounds()`'s `hi` at all: `walk_helper()` takes
  both ends and clamps `hi = min(hi, len(d))`, which is
  [`count-bounded-walk-invariant.md`](count-bounded-walk-invariant.md) — the
  answer to the follow-up this bullet was still waiting on, and the module
  preamble's own count line already says so. What is left is narrower and is
  #843's: the *image-derived* targets are still unchecked, `chain_from()`
  handing a decoded `branch_target()` to `walk_helper()` at `:645`, so
  `--helpers 0xFFE9` exits 0 and lists 23 lines of the `0xFF` fill at the top
  of the region — file `0x2FFE9`-`0x2FFFF`, inside it — and stops at the region
  end, with the region-exit note saying so. `:546` was that handoff's address
  when this section was written; the distinction between a caller's anchor and
  the image's own operands is the part that still stands.)*
- **It does not cover `print_sites()`'s own `pd_bounds()` call** at `:898`, which
  discards `hi` and uses `lo` only to print. Its `hi` is not load-bearing and
  there is nothing to change; it is counted in the next section and recorded as
  display-only, not as "fixed". *(`:898` was this tree's line number when
  written; the re-measured table below has it at `:1126`. The claim is
  unchanged, and re-checked: `hi` is still not load-bearing there.)*

## #843's "the only two" is twelve, and four under the narrower test

#843's premise is that `walk_helper()` and `chain_from()` are *the only*
functions in `pd_index_geometry.py` that write `lo, _` from `pd_bounds()` and
throw `hi` away. One grep, and the line numbers are the ones in the tree this
change leaves behind — 28 to 36 higher than the ones #843 and the issue quote,
depending on where the site falls, because `check_site_addr()` is now between
`pd_bounds()` and `walk_helper()` and `site_rows()`'s docstring grew by seven
lines:

```console
$ grep -n 'lo, _ = pd_bounds()' ec/tools/pd_index_geometry.py
```

| line | function | the issue's narrower test |
|---|---|---|
| 725 | `site_rows` | **the one that raised** — row 10 |
| 768 | `reached_entries` | no — entries are the image's own, from `base_sites(d, span)` |
| 928 | `reaches` | no |
| 955 | `is_entry_shaped` | no |
| 976 | `caller_rows` | no — reaches the check through `site_rows()` |
| 1046 | `print_helpers` | no — checks each entry itself |
| 1079 | `print_reached` | no |
| 1126 | `print_sites` | `site_rows()`'s caller; `lo` is display-only |
| 1188 | `write_helpers_csv` | no |
| 1220 | `reached_csv_row` | no |
| 1322 | `access_frames` | no |
| 1473 | `access_rows` | no |
| 1801 | `access_self_test` | no |
| 2105 | `self_test` | no |

**Twelve** under the literal grep. **Four** under the narrower test the issue
applies — *the discarded `hi` would have bounded an address that arrives from
the command line* — which are `site_rows` (reached by `--sites`),
`print_sites` (its caller), and the two #843 names. Both figures and the grep
that produces each are here, so whichever test #843 meant, the right count is on
the page and the premise is corrected rather than inherited.

*(**Correction, 2026-09-28, issue #860.** Both figures above are stale, and the
table has been re-measured — the old table's line numbers (`:344`, `:516` and so
down) are not this tree's. **The literal grep is fourteen**, not twelve, and the
two functions #843 names are **no longer in it at all**: both `walk_helper()` and
`chain_from()` now take both ends of `pd_bounds()`, and `walk_helper()` further
clamps `hi = min(hi, len(d))`. That is
[`count-bounded-walk-invariant.md`](count-bounded-walk-invariant.md), which
answered the census's follow-up 1 that the old table's third paragraph was still
waiting on, and the module preamble's own count line already records it. So #843's
premise has changed shape rather than merely grown — the two functions it names
are no longer candidates — and **the narrower total is deliberately not
restated here**, because its definition is #843's and the two entries it was
counting have left it. The third column above is per-function evidence and
carries the narrower judgement for the functions still in the list, so whoever
picks #843 up can read the count off it rather than take a stale figure on
trust. What remains unchecked is not a discarded `hi` at all: it is the
*image-derived* targets `chain_from()` hands `walk_helper()` at `:645`, which
discarding `hi` would never have covered either. Re-measured command and table
in [`pd-index-geometry-address-contract.md`](pd-index-geometry-address-contract.md).)*

A branch cannot edit another issue, so the correction is committed here under
this heading and the follow-ups pass is what files it against #843. Whoever
picks it up needs to know three things, and they are all above: the two
functions it names are not the only two; one of the others is the census's own
row 10; and `walk_helper`'s count-bounded walk — the open part — is measured in
this file rather than argued from the table.
*(**Correction, 2026-09-28, issue #860.** The first and third of those are
superseded by the correction above, and this paragraph is left as it was rather
than rewritten, because what changed is #843's premise and not this section's
reason for existing. The two functions #843 names are no longer in the set at
all rather than merely outnumbered; and `walk_helper`'s count-bounded walk is
no longer the open part — it is answered in
[`count-bounded-walk-invariant.md`](count-bounded-walk-invariant.md), which is
what the third bullet under "What the check does not do" above is now waiting
on. The middle one still stands: `site_rows` is the census's row 10.)*

## What this does not establish

- **No live test ran.** No EC was opened, no register read back, no capture
  taken, no hardware and no Windows involved. Every number above is a static
  read of a committed file or the output of a command over one.
- **No `registers.yaml` status moved, and none could have.** Nothing here is
  about a register; this is Python walking a `bytes` object.
- **"Exits 0" is a statement about these commands on this image**, not a
  property of the code. The byte-identical diffs are what make it a regression
  test; on their own they would be a formality.
- **The self-test pins three facts, not a proof.** That `--sites 0xFFFF` still
  walks its full `SITE_WINDOW` with the last read at or above `0x3000E` and no
  higher than the `0x3002C` ceiling — a range, not the realised figure, so a
  window that walked further would still pass — and that
  `0x1FFF1` and `0x23478` are each refused with the region and both ranges named.
  It does not pin that the *message wording* is the best wording; it pins that
  the message keeps naming what a reader needs.
  **Correction (2026-10-05, issue #1014): the first of those three facts is
  gone and the pin says the opposite now.** The range it asserted described the
  pre-change listing. `--sites 0xFFFF` is pinned to stop at the region's last
  byte with a stop naming `0x30000` — a bound rather than a range, so a window
  that walked further would now go red — and a mid-region anchor is pinned to
  the full `SITE_WINDOW` beside it so the bound cannot pass by stopping too
  early. The `0x1FFF1` and `0x23478` refusals are unchanged and still pinned.
- **No suite was added.** The tool's own `--self-test` is the established idiom
  for this tool, and a committed `test_*.py` would need a row in
  `../../tools/README.md`'s table and a corrected suite total in two long shared
  files, for a change whose regression surface is three assertions. The runner's
  tally is therefore unchanged, which is the point.

## Reproducing it

From the repository root. The first three are the refusal, the second is the
"the CSV's own answer" second line, and the diff pair is the evidence that
nothing on the legal range moved.

```sh
# the legal range, unchanged
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0xFFF0
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0xFFFF
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0xC2FA 0xDA9B

# the refusals: 0x1FFF0 and 0x1FFF1 were the pre-change boundary pair
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0x1FFF0   # exit 2
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0x1FFF1   # exit 2
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0x1FFFF   # exit 2
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0x23478   # exit 2, + 2nd line

# the tool's own suite, and the runner's unchanged tally
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
bash tools/run-tests.sh ec/tools

# #843's count, re-derived from the committed source
grep -n 'lo, _ = pd_bounds()' ec/tools/pd_index_geometry.py

# the census's other command, untouched
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
  0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv --census-column --check
```

The two boundary commands are the ones a reader should run first, and they are
worth running in the order above on purpose: `0x1FFF0` exiting 2 is the visible
consequence of correction 1, and it is the number the census's old parenthetical
bound was about.
