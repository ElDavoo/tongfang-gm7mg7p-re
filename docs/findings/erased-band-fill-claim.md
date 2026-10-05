# The image map's `all 0xFF` rows are measured, and the `0x90` count makes an unreachable branch a reading

(2026-09-30, issue #861. Static reading and commands over one committed image.
No capture opened, no EC, no hardware, no Windows.)

`trace_xdata_refs.REGIONS` is the image map for
`ec/firmware/GMxMGxx_11.800`, and its fifth tuple element — `how` — is the only
thing in it that says anything about the *contents* of the bands it maps. Every
consumer discards it: `region_of()` returns it, and `xdata_span_survey.py`,
`decode_index_table.py`, `pd_index_geometry.py`, `audit_call_targets.py` and
`trace_xdata_refs.py` itself all bind the fifth element to `_`. So the column
carrying the map's only checkable claim about itself is the column nothing
reads.

Two of its six rows say `"all 0xFF"`. **Both hold, and nothing in the tree had
established either.**

## What was measured

Re-run at this tree, over `ec/firmware/GMxMGxx_11.800` (0x40000 bytes exactly),
with both bands read in full — 32768 and 65536 bytes, no sampling.

| row | file span | bytes | distinct values | `0x90` count |
|---|---|---:|---|---:|
| `("erased", 0x18000, 0x20000, None, "all 0xFF")` | `0x18000`-`0x1FFFF` | 32768 | `{0xFF}` | **0** |
| `("erased", 0x30000, 0x40000, None, "all 0xFF")` | `0x30000`-`0x3FFFF` | 65536 | `{0xFF}` | **0** |

That is `python3 ec/tools/check_image_map.py ec/firmware/GMxMGxx_11.800`, which
is the deliverable; before it, the same two numbers came from a throwaway
expression and the map carried neither.

## The check, and what it is not built to say

`ec/tools/check_image_map.py` is a new file rather than a mode on
`trace_xdata_refs.py`, for the reason `CLAUDE.md` gives — a new tool is a new
file — and because the issue's own observation is that `trace_xdata_refs.py` has
no `--self-test` of its own to extend. It imports `REGIONS` and `PD_MARKER` and
never restates them, so a check holding a claim the table no longer makes is not
reachable from here.

**What decides a row's fate is the `how` string, and membership is exact.**
`CHECKED` is a small vocabulary — today one entry, `"all 0xFF"`, meaning every
byte of the band is `0xFF` — and a row is measured only if its `how` is a key.
The strictness is deliberately in the direction that cannot overclaim: editing a
row's prose moves it *out* of coverage, never into it. `"all 0xFF (pad to bank
1)"` is not `"all 0xFF"`, and it is reported `unidentified` — neither measured
nor attributed to another tool — so a claim this tool has stopped recognising
reads as unchecked rather than as verified.

**The bands are read in full, and the bytes that are not are named.** 32 KiB and
64 KiB is a cheap read of a committed file, and a sample cannot answer "is every
byte `0xFF`" in any case: it can only fail to notice. The first eight offending
offsets are named with their values and the rest counted, so a badly wrong image
gives bounded output and a real fill failure is locatable.

**Four refusals, and they are the half that makes the rest worth anything.**

- **A band running past the end of the image is refused**, not sliced short and
  compared. A truncated dump that stopped inside an erased band would otherwise
  pass the claim by running out of bytes.
- **A zero-length band is refused**, for the same reason one step in: `all()`
  over no bytes is `True`, so an empty read is a pass that measured nothing.
- **A `how` the vocabulary holds no test for is refused** by `band_faults`
  itself, not only by the row loop that consults `CHECKED` first. A second
  caller that skipped that membership test would otherwise get a silent pass
  from whichever test happened to be written below.
- **The negative control.** This check has exactly one shape of pass, so without
  a way for it to fail there is nothing here distinguishing "the bands are all
  `0xFF`" from "this function returns an empty list". Nine single-byte
  corruptions — `0x00`, `0x90` and `0x02` at the first, middle and last byte of
  a 32 KiB band — are driven through *the same* `band_faults` call the committed
  rows go through, and each is asserted to be caught and named. `0x90` is in
  that set deliberately: it is the byte whose absence the next section is about,
  and `0x02` is a real opcode, so a predicate narrowed to "not `0x00`" would go
  red on two of the nine rather than looking like it works.

At the command level, a copy of the firmware with one `0x00` spliced into
`0x18000` exits 1 and names the offset:

```console
$ python3 ec/tools/check_image_map.py doctored.bin
          REFUSED: 1 of 32768 byte(s) are not 0xFF: 0x18000 is 0x00
1 refusal(s): a band's bytes do not satisfy the claim the map makes about it.
```

## The `how` column's census: two rows measured, four not

The other four rows are reported `unchecked` with the tool that owns each, and
the run's summary line prints the split so the output cannot be read as "the
whole `how` column is verified":

| row | `how` | verdict | what would check it |
|---|---|---|---|
| `common` | `always mapped; same runtime address in every bank image` | unchecked | `make_bank_image.py` — the bank windows are what it builds |
| `bank0` | `make_bank_image.py <fw> 0 0x08000` | unchecked | `find_banks.py` — the bank→offset rows are its heuristic scoring |
| `bank1` | `make_bank_image.py <fw> 1 0x10000` | unchecked | `find_banks.py` — the same |
| `pd-image` | `separate ITE8850-PD 8051 image; dd bs=64k skip=2` | unchecked | `trace_xdata_refs.PD_MARKER` — the image's own marker |

Making those four checkable is `find_banks.py`'s and `make_bank_image.py`'s
job and a different change. The gap is named rather than closed, and a fifth
state (`unidentified`) is kept distinct from `unchecked` so that a row whose
prose has been edited is visibly *nobody's* claim rather than borrowing a
neighbour's owner.

**One of those four is partly checked already**, and the tool says so rather
than claiming the row: the `pd-image` row's identifying marker is what
`pd_index_geometry.py --self-test` and `check_register_counts.py` refuse an
image without, so what is unchecked is the rest of that row's prose — the "64k
skip=2" and the separate-address-space claim, which nothing measures.

## `check_register_counts.py`'s branch, and why it cannot fire here

The one check that would notice a wrong image map cannot fire on this one.
`check_register_counts.py` splits each register's site count by region and
reports `main + pd != total` under the comment "Sites in the erased regions
would land here; the image map would be wrong, not the YAML".

It fires only if a `MOV DPTR` byte — `0x90` — lands in an erased band. Fill
cannot contain one, and the measurement above is **0 in both bands**. So:

> **The branch is a true guard against a re-derived map and is unreachable
> against this image.** Those are different claims, and the original comment
> made the first while reading as the second. The correction is in place beside
> it in the tool, per the `docs/findings.md` §4a-4d pattern, and it is a plain
> Python comment rather than the `*(Superseded …)*` note form —
> `check_no_append_logs.py` fences that form to `docs/findings/`, and a `.py`
> comment carrying it would be imitating a rule that does not apply to it.

The `0x90` count is now **printed** rather than asserted in a comment, which is
what makes the unreachability a reading: a reader runs the named command and
reads 0 against a 64 KiB band, rather than taking a comment's word for it. It
counts `trace_xdata_refs.MOV_DPTR`, the same constant the rest of the tree uses,
so the two cannot come to disagree about which byte that is.

**This is a reading, not a proof of unreachability on every image.** It is the
count for this dump. A different dump whose `0x30000` band held a `0x90` would
make the branch fire, which is what the branch is for.

## The premise behind `0x3000E` and `0x1FFF1`, now asserted

`pd_index_geometry.py --self-test` pins `--sites 0xFFFF`'s last read as
`0x3000E <= peak <= 0x3002C`. The `0x3002C` had a citation — the census's row
10 — and `0x3000E` had only this document. It is `0x2FFFF + 15`, one byte per
instruction, and it is the right number *only* because the bytes past the region
are the `("erased", 0x30000, 0x40000, None, "all 0xFF")` row, with
`disasm8051.OPCODE_LEN[0xFF] == 1`. A string in a discarded column.

**The comments now carry the same provenance the `0x3002C` figure has** — the
row, the `OPCODE_LEN` fact, and the command by name — and the premise is
**asserted rather than described**: the self-test asks the band predicate
imported from `check_image_map.py` whether the row still holds, immediately
before trusting `0x3000E` as a floor. That import is the answer to the issue's
"the same provenance is not a longer comment": a comment is a claim, and this
one is now load-bearing.

The predicate is looked up by the row's own bounds, and is asked only when the
`how` is a claim `CHECKED` declares a test for — so a table whose row has been
reworded makes the assertion go red rather than measuring a claim that is no
longer there. A doctored image with one byte changed at `0x30000` fails exactly
that assertion and nothing else; the `0x1FFF1` boundary is `check_site_addr()`'s
and does not move with the fill, which
[`pd-sites-address-range.md`](pd-sites-address-range.md)'s correction 1 now
records as a correction to the natural reading of it.

### Correction (2026-10-05, issue #1014): nothing in `pd_index_geometry.py` rests on this premise any more

**The assertion named in the two sections above has been deleted, along with
the floor it existed to hold.** `site_rows()`'s listing loop is now bounded at
`pd_bounds()`'s region end, so `--sites 0xFFFF` stops at `0x2FFFF` and its stop
names `0x30000`. The last read comes from the region's extent and no longer
from the bytes past it, and a check whose stated claim backs nothing is the
failure the refusals in this corpus are written against. The section above is
kept as the record of what the premise was and why it was worth asserting
while something depended on it.

**Where the premise is asserted now: `python3 ec/tools/check_image_map.py
ec/firmware/GMxMGxx_11.800`**, which is the command this document has always
named for the measurement. It puts `d[0x30000:0x40000]` to the `all 0xFF` test
the row itself names, prints the band's size, distinct byte values and `0x90`
count, and exits non-zero on a band whose bytes do not satisfy the claim.
`check_image_map.py --self-test` holds the predicate and the `CHECKED`
vocabulary it selects through, so the measurement has the same negative control
it had when the assertion lived in the other tool. Nothing was lost by the move:
the band is a claim about the image map, and this is the tool that owns it.

Measured, so the deletion is a relocation and not a loss: splicing `0x00`,
`0x74` or `0x90` into `0x30000` of a copy of the committed image moves
`check_image_map.py`'s verdict from ok to a refusal naming the offset, while
`pd_index_geometry.py --self-test` stays green — the listing stops at the region
end in every case. See [`site-rows-window-bound.md`](site-rows-window-bound.md).

## The self-test, and why no suite was added

**No `test_*.py` suite, no `tools/README.md` row, and the runner's tally is
unchanged — which is the point.** `--self-test` is the established idiom for a
tool checking its own subject here (`census_ff_fill.py`,
`decode_index_table.py`, `check_status_vocabulary.py`), and
`census_ff_fill.py` exists precisely to stop two tools answering "is this fill"
separately. The alternative costs a row in `tools/README.md` — the file this
repository collected 3,522 lines and 22 supersession notes in, and the one
`CLAUDE.md` names as a conflict site — for a change whose regression surface is
a band of fill and a string. `pd-sites-address-range.md` already made this exact
trade for #848 and recorded it. It is also mechanically free:
`test_readme_suite_table.py` discovers only `test_*.py`, so a lone `check_*.py`
is invisible to it in both directions and nothing goes red.

## What this does not establish

- **No live test ran.** No EC was opened, no register read back, no capture
  taken, no hardware, no Windows, no Ghidra. Every number above is a static read
  of a committed file or the output of a command over one. "Both bands are all
  `0xFF`" is a measurement of committed bytes, **not** a claim about what the EC
  does with them.
- **No `registers.yaml` `status:` is involved, and none could have been.** The
  issue says so and it is right: this is the image map's own accuracy. Nothing
  here is evidence about a register's behaviour, and the erased bands
  deliberately stay out of the tables that carry behaviour.
- **A pass over the committed image is a claim about that image.** The map is a
  claim about a *map*, and the difference is the re-derivation path, which
  `REGIONS`'s own preamble states: "Re-derive this with find_banks.py before
  trusting it against a different dump -- the bank->offset rows are that
  script's heuristic scoring, not a header field." The same command over a
  re-derived dump compares the claim against that dump's bytes, and the tool's
  footer names the tool that re-derives the table. **Which of the two was built
  is the question the issue asked to have answered: both, and they are the same
  command.**
- **The two `0x90` counts are 0 for this image, not for every image.** A
  different dump is a different reading, and the count is printed so it can be
  re-taken rather than assumed.
- **Nothing is in any CI gate.** See the next section.

## Not wired into the cheap gate, and why

A `docs/ci/agent-gates-*.patch` for the new tool was considered and **declined**
with the reason recorded here rather than left as a silent omission, which is
what `check_fixture_pointer_cells.py`'s own `tools/README.md` row did for the
same decision. Adding one also requires an edit to
`tools/test_agent_gates_patches.py`'s `PATCHES` list — the only place that says
what the set is, and where every patch must both apply alone and compose — and
the gate line itself is a human's `git apply`. `.github/` is copied from
`ElDavoo/agent-pipeline` and this branch's push token has no `workflow` scope,
so a branch touching it fails at the end of a PR rather than the start.

**The consequence, stated rather than hidden: nothing in CI runs this check.**
It runs when someone runs the named command or the `--self-test`. The issue's
bar is "a named, committed command", which this meets; a gate was never asked
for and the declining is recorded here so the next reader knows the absence is a
decision.

## Reproducing it

From the repository root. The doctored image is the command-level negative
control, and is what distinguishes a check that has only ever been green against
one input from one that cannot fail.

```sh
# the check, over the committed image: exit 0, both bands, 0x90 count 0 in each
python3 ec/tools/check_image_map.py ec/firmware/GMxMGxx_11.800

# the fixtures, including the negative control; reads no firmware
python3 ec/tools/check_image_map.py --self-test

# the premise itself, asserted and holding. Since issue #1014 this is the
# first command above rather than a check inside pd_index_geometry.py; nothing
# in that tool rests on the fill any more.
python3 ec/tools/check_image_map.py ec/firmware/GMxMGxx_11.800

# the --sites listing, bounded at the region end rather than at its window
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0xFFFF

# the comment-only edit changed no behaviour
python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800

# the command-level negative control: one spliced byte, exit 1, offset named
python3 - <<'PY'
d = bytearray(open("ec/firmware/GMxMGxx_11.800", "rb").read())
d[0x18000] = 0x00
open("/tmp/doctored.bin", "wb").write(bytes(d))
PY
python3 ec/tools/check_image_map.py /tmp/doctored.bin   # exit 1

# the index is current, and no frozen file moved
python3 ec/tools/gen_findings_index.py --check
python3 ec/tools/check_findings_frozen.py
python3 ec/tools/check_no_append_logs.py

# the tally is unchanged, which is the point
bash tools/run-tests.sh
```

## Out of scope

- **The `pd-image` region's own 2,120-byte `0xFF` tail** — absent from the map
  rather than misdescribed in it, as the issue says itself. A separate
  measurement, and the table does not claim otherwise.
- **The four non-`erased` rows' `how` prose.** Named as `unchecked` with the
  tool that would check each, so the gap is visible rather than absent.
- **Any live run, and any upstream submission.** No stage opens an issue or PR
  against `Wer-Wolf/uniwill-laptop` or `tuxedo-drivers`; had this change
  reached one, the deliverable would be a prepared patch in this repository for
  a human to submit.
