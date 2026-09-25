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
says so, and the self-test pins the realised figure with the bound beside it.

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

- **It does not make the peak read into "cannot raise".** After the change, no
  `--sites` address can put a read outside the region, so the window's furthest
  possible read is bounded by the code rather than by this image's spare bytes —
  that is a different and stronger sentence than the one row 10 carried. It is
  still **not** "cannot raise": the realised peak on this image remains
  `0x3000E`, a property of these bytes, and the `0x3002C` ceiling remains
  arithmetic. What the check removed is the *unbounded* direction, and only
  that.
- **It does not make `--callers` consistent with `--sites`.** Measured above:
  `--callers 0x1FFFF` **exits 0** and prints a three-row byte-scan caller list.
  It has no traceback to replace, and its output is the over-counting the module
  preamble already documents. Recorded so that nobody reads the two arguments'
  identical argparse declarations (`:1792-1796`) as an identical contract.
- **It does not fix `walk_helper`.** `--helpers 0x1FFE9` raises, measured above,
  and is left raising. A blanket range check there would also have to cover the
  targets `chain_from()` decodes out of the image's own branch operands and
  hands it at `:546` — a different contract from a user-typed anchor — and the
  question of what invariant a count-bounded walk is meant to enforce is the
  census's own open follow-up 1, which deferred it as a design question rather
  than a bug report. Fixing it here would pre-empt that.
- **It does not cover `print_sites()`'s own `pd_bounds()` call** at `:898`, which
  discards `hi` and uses `lo` only to print. Its `hi` is not load-bearing and
  there is nothing to change; it is counted in the next section and recorded as
  display-only, not as "fixed".

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
| 344 | `walk_helper` | **named by #843** |
| 516 | `chain_from` | **named by #843** |
| 620 | `site_rows` | **the one that raised** — row 10 |
| 734 | `reaches` | no |
| 761 | `is_entry_shaped` | no |
| 782 | `caller_rows` | no |
| 850 | `print_helpers` | no |
| 898 | `print_sites` | `site_rows()`'s caller; `lo` is display-only |
| 956 | `write_helpers_csv` | no |
| 1057 | `access_frames` | no |
| 1208 | `access_rows` | no |
| 1640 | `self_test` | no |

**Twelve** under the literal grep. **Four** under the narrower test the issue
applies — *the discarded `hi` would have bounded an address that arrives from
the command line* — which are `site_rows` (reached by `--sites`),
`print_sites` (its caller), and the two #843 names. Both figures and the grep
that produces each are here, so whichever test #843 meant, the right count is on
the page and the premise is corrected rather than inherited.

A branch cannot edit another issue, so the correction is committed here under
this heading and the follow-ups pass is what files it against #843. Whoever
picks it up needs to know three things, and they are all above: the two
functions it names are not the only two; one of the others is the census's own
row 10; and `walk_helper`'s count-bounded walk — the open part — is measured in
this file rather than argued from the table.

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
  walks its 16-instruction window with the last read at `0x3000E`, and that
  `0x1FFF1` and `0x23478` are each refused with the region and both ranges named.
  It does not pin that the *message wording* is the best wording; it pins that
  the message keeps naming what a reader needs.
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
