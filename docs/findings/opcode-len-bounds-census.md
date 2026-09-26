# The opcode-table bounds census: every `OPCODE_LEN[d[i]]` in `ec/tools/`, and what holds the index in

(2026-09-25, issue #797. Static reading and arithmetic over committed bytes.
No capture opened, no EC, no hardware, no Windows.)

Issue #679 fixed one instance of a shape and wrote down what the shape is for
the first time: *read a byte out of a buffer, then index the 8051 opcode table
with it, before checking the buffer's end*. `disasm8051.decode()` was the
instance, and `ec/tools/citation_gap_scan.py:26-46` carries the in-place
retraction for it, which stays as it is. This is the census of the rest of
`ec/tools/` for the same shape, one row per site, with a measured verdict per
row instead of an assertion. It is a **new file**; the only shared file it edits
is `docs/findings.md`, by one section.

One site had its comment restated rather than its code changed, and that
comment is the only code change in this work.

## What the shape is, and what it is not

The shape is **reading a byte out of a buffer in order to index the opcode
table**, where the *buffer read* is what can raise.

It is not "the opcode table is indexed". `OPCODE_LEN` covers all 256 byte
values — 16 rows of 16, opcode `0x00` first (`ec/tools/disasm8051.py:39-56`) —
so `OPCODE_LEN[op]` where `op` is already a byte value cannot go out of range,
and `counter_sweep_entry.py:319,384,551,565` and
`audit_call_targets.py:170,314` index the table exactly that way. The
distinction is the whole content of this census, and it is stated here because a
grep for `OPCODE_LEN[` returns both kinds and a reader has to be told which is
which.

Two more shapes are adjacent and are **excluded**, with the reason, so the
sweep's boundary is stated rather than assumed:

- `audit_call_targets.py:171,315`'s `d[i + OPCODE_LEN[op] - 1]` — a
  last-byte-of-the-instruction read. The table is indexed by a byte value and
  the *buffer* read is the displacement, at an offset derived from the table.
  A different shape with a different bound. `audit_call_targets.py` over the
  committed image exits 0 (`## Reproducing it`, command 8), so nothing here is
  a report of a live fault; whether that pair wants a check of its own is a
  question for a follow-up, not a finding. Asked as issue #847 and answered in
  [`rel8-displacement-bound.md`](rel8-displacement-bound.md): the pair wants a
  `--self-test` check of the bound, not a `len(d)` guard, because `hi` is a
  constant in another module and it is `main()`'s PD-marker check, three frames
  from the read, that holds it in range.
- `counter_sweep_entry.py`'s `OPCODE_LEN[r["owner_opcode"]]` — a table index by
  a value read out of a dict, so by the paragraph above it cannot raise.

And a third, in the same family, which is *not* the shape and is easy to
mistake for it: `pd_index_geometry.py:595,629`'s `i + OPCODE_LEN[MOV_DPTR]`
indexes the table with the `MOV_DPTR` **constant**, not with anything read out
of a buffer.

## The sweep, and its full output

One grep, from the repository root. This is the census's membership test: a
site is in the table if this command puts it there, and a reader re-running it
either gets the same list or finds a correction to make.

```console
$ grep -rn 'OPCODE_LEN\[' --include=*.py ec/tools
```
```
ec/tools/trace_xdata_refs.py:297:        n = OPCODE_LEN[d[i]]
ec/tools/disasm8051.py:109:    `disp` is the instruction's *last* byte -- `d[i + OPCODE_LEN[op] - 1]`, not
ec/tools/disasm8051.py:115:    return (addr + OPCODE_LEN[op] + (disp - 256 if disp > 127 else disp)) & 0xFFFF
ec/tools/disasm8051.py:312:        n = OPCODE_LEN[d[i]]
ec/tools/disasm8051.py:334:            i += OPCODE_LEN[d[i]]
ec/tools/second_copy_census.py:468:            i += OPCODE_LEN[fw[i]]
ec/tools/second_copy_census.py:473:        raw = fw[last:last + OPCODE_LEN[fw[last]]]
ec/tools/test_disasm8051.py:52:        # `OPCODE_LEN[d[1]]` before its own bounds check -- an IndexError from
ec/tools/pd_index_geometry.py:364:        raw = d[i:i + OPCODE_LEN[op]]
ec/tools/pd_index_geometry.py:403:        i += OPCODE_LEN[op]
ec/tools/pd_index_geometry.py:412:        n = OPCODE_LEN[d[i]]
ec/tools/pd_index_geometry.py:430:            run.append((i, d[i:i + OPCODE_LEN[d[i]]]))
ec/tools/pd_index_geometry.py:431:            i += OPCODE_LEN[d[i]]
ec/tools/pd_index_geometry.py:531:        raw = d[i:i + OPCODE_LEN[op]]
ec/tools/pd_index_geometry.py:538:            i += OPCODE_LEN[op]
ec/tools/pd_index_geometry.py:566:        i += OPCODE_LEN[op]
ec/tools/pd_index_geometry.py:595:        helpers, terms, stopped = chain_from(d, i + OPCODE_LEN[MOV_DPTR],
ec/tools/pd_index_geometry.py:629:        start = i + OPCODE_LEN[MOV_DPTR] if base is not None else i
ec/tools/pd_index_geometry.py:636:            listing.append((j, d[j:j + OPCODE_LEN[d[j]]]))
ec/tools/pd_index_geometry.py:637:            j += OPCODE_LEN[d[j]]
ec/tools/pd_index_geometry.py:716:        raw = d[i:i + OPCODE_LEN[op]]
ec/tools/pd_index_geometry.py:739:        i += OPCODE_LEN[d[i]]
ec/tools/pd_index_geometry.py:1062:            n = OPCODE_LEN[d[i]]
ec/tools/pd_index_geometry.py:1100:        op, n = d[i], OPCODE_LEN[d[i]]
ec/tools/pd_index_geometry.py:1178:        n = OPCODE_LEN[d[i]]
ec/tools/pd_index_geometry.py:1191:            n = OPCODE_LEN[d[i]]
ec/tools/pd_index_geometry.py:1507:            i += OPCODE_LEN[op]
ec/tools/counter_sweep_entry.py:319:    last = idx == OPCODE_LEN[op] - 1
ec/tools/counter_sweep_entry.py:384:            n = OPCODE_LEN[r["owner_opcode"]]
ec/tools/counter_sweep_entry.py:551:    check(all(r["owner_index"] == OPCODE_LEN[r["owner_opcode"]] - 1
ec/tools/counter_sweep_entry.py:565:          and all(r["owner_index"] == OPCODE_LEN[r["owner_opcode"]] - 1
ec/tools/walk_branch_arms.py:220:        n = OPCODE_LEN[op]
ec/tools/walk_branch_arms.py:347:            n = OPCODE_LEN[op]
ec/tools/audit_call_targets.py:170:        if op in REL_OPCODES and i + OPCODE_LEN[op] <= hi:
ec/tools/audit_call_targets.py:171:            yield i, op, relative_target(op, d[i + OPCODE_LEN[op] - 1],
ec/tools/audit_call_targets.py:314:                "length": OPCODE_LEN[op],
ec/tools/audit_call_targets.py:315:                "disp": d[off + OPCODE_LEN[op] - 1],
ec/tools/citation_gap_scan.py:28:called in a loop over these windows.** It evaluates `OPCODE_LEN[d[i]]` *before*
ec/tools/citation_gap_scan.py:234:        n = D.OPCODE_LEN[window[i]]
```

**39 lines, and 25 of them are sites of the shape, in 20 rows.** The other
14 are accounted for here so that the arithmetic is checkable rather than
asserted:

*(Line numbers note, added by #847: the two `audit_call_targets.py` sites at
`:307,308` are `:314,315` now, because `region_bounds()` above them grew a
docstring. Extended by #848, which moved every `pd_index_geometry.py` site in
this block — the 19 of them are the re-run, and the table below and rows 4-7,
11-12 and 15-20 cite the same new numbers. `check_site_addr()` and the address
loop above the listing add no `OPCODE_LEN[` of their own, so the count is
unchanged at 39 and the sweep still exits 0. The block above is the grep re-run,
not the old output edited by hand.)*

*(Re-run again by #844, which moved both `walk_branch_arms.py` sites: `:213` is
`:220` and `:328` is `:347`, because the new `END_IMAGE` stop reason and its
`CUTS` entry sit above `test_site()` and the pre-read guard sits between them
and `descend()`'s read. The count is unchanged at 39. **This re-run also picked
up five lines that were already stale before #844 touched anything**, and they
are recorded here so they are not credited to it: `trace_xdata_refs.py:229` is
`:297` — the #846 note further down this file records that same move, and this
block was not updated with it — and the four `disasm8051.py` lines are each one
higher, `:108,114,311,333` becoming `:109,115,312,334`. A partial hand-edit of
two lines would have left the block neither the old output nor the new one,
which is what the sentence above exists to prevent, so all seven are the re-run.
The `not a site` table's first row cites `disasm8051.py:108,114` and needs
`109,115`; it is the one row in that table this change moves.)*

*(The per-site table's rows 2 and 8 are **deliberately left at `:212-213` and
`:327-328`**, and the `three more rows` paragraph at its `:328` with them. Row 8
is the most conflict-prone cell in the file, both rows name their function
beside the number, and follow-up 2's correction clause below carries the update
— which is why the answer went there rather than here. The mapping for a reader
who follows one of those citations: row 2's `test_site()` guard is `:217` and
its read and table index are `:219` and `:220`; row 8's `descend()` read and
index are `:346` and `:347`, its new pre-read guard is `:343`, and its
`off + n > len(d)` test is `:353`. This is the same shape as the #846 note
below — a moved file, not a wrong one.)*

| not a site | lines | why |
|---|---|---|
| `disasm8051.py:109,115` | 2 | `relative_target()`'s docstring and body, indexing by the `op` **argument** — a byte value, and this function indexes no buffer at all |
| `citation_gap_scan.py:28` | 1 | the module docstring, quoting the retracted `decode()` claim |
| `test_disasm8051.py:52` | 1 | a comment in the test that already pins the #679 fix |
| `pd_index_geometry.py:595,629` | 2 | `OPCODE_LEN[MOV_DPTR]` — the constant, not a buffer read |
| `counter_sweep_entry.py:319,384,551,565` | 4 | `op` or `r["owner_opcode"]` is a byte value already in hand |
| `audit_call_targets.py:170,314` | 2 | the same: `op` is in hand from `d[i]` at `:169`, and `:314`'s `OPCODE_LEN[op]` is a length value with no buffer read at all |
| `audit_call_targets.py:171,315` | 2 | the adjacent last-byte-of-instruction read, excluded above |

The six sites the issue named are a subset of the table, not its content. Three
more rows are the sweep's finding beyond both the issue and the plan that
produced this file: `walk_branch_arms.py:328` (`descend`), which is a
*different* function from the `test_site` the issue cites and has a different
bound; `pd_index_geometry.py:716` (`branch_index`); and
`pd_index_geometry.py:1507` (`byte_address`, a `--self-test` fixture walker
whose buffer is a hand-written fixture rather than the image).

## The per-site table

Six columns: the site, the loop bound, whether that bound is `len(d)` or a
caller's number, whether the shape is reached, what the measurement is, and
what the census settles the row with. "Bound" is read at the line that drives
the loop, and `walk_helper`/`chain_from` are credited with every `OPCODE_LEN`
in the function that walks.

| # | site | bound | `len(d)`? | reached | measurement | settled by |
|---|---|---|---|---|---|---|
| 1 | `disasm8051.py:311` `decode()` | `range(count)`, `if i >= len(d): return` at `:309` | **is** | yes | #679's own fix; `test_disasm8051.py` pins it | existing guard + docstring `:303-306` |
| 2 | `walk_branch_arms.py:212-213` `test_site()` | `range(SCAN_INSNS)`, `if off < 0 or off >= len(d): return None` at `:210` | **is** | yes | the check is on the line *before* the read | existing guard |
| 3 | `citation_gap_scan.py:234` `walk()` | `while i < len(window)` | **is** | yes | — | existing docstring `:227-229` |
| 4 | `pd_index_geometry.py:1100` `access_walk()` | `while used < budget`, `if not lo <= i < hi: break` at `:1093`, `hi = min(hi, len(d))` at `:1078` | region, clamped to `len(d)` | yes | — | existing guard |
| 5 | `pd_index_geometry.py:1191` `reaches_template()` | `range(HELPER_MAX_INSNS)`, `if not lo <= i < hi: return False` at `:1189` | region | yes | — | existing guard |
| 6 | `pd_index_geometry.py:1178` `access_entries()` | `for i in range(lo, hi)`, `hi = min(hi, len(d))` at `:1175` | region, clamped | yes | — | existing guard |
| 7 | `pd_index_geometry.py:1507` `byte_address()` | `while i < len(raw)` | **is** (`len(raw)`) | yes | `--self-test` over the committed fixtures, exit 0 | existing bound; not the image |
| 8 | `walk_branch_arms.py:327-328` `descend()` | `while True`, `budget <= 0` at `:324`; `if off + n > len(d)` at `:329` | **is**, but the test runs *after* the read | yes | `--self-test` over the image, exit 0 | existing guard; see follow-up 2 |
| 9 | **`trace_xdata_refs.py:229` `walk()`** | `range(max_insns)`; `len(d)` is tested twice, `:230` and the guard's first disjunct, and only the latter bounds the index | **no** — held by `:241` | yes, 114 walks / 311 iterations over the committed sweep | the guard's first disjunct fired **0** times; the exposure is real (see below) | **restated comment at `:241-242`** |
| 10 | `pd_index_geometry.py:635-637` `site_rows()` (was `:600-601` when this census was written) | `range(max_insns)` = `SITE_WINDOW` (16), no flow break, two `d[j]` per iteration | **no** | yes, every `--sites` run | last read `0x3000E` from `--sites 0xFFFF` against a `0x40000` image, under the `0x3002C` ceiling below; command 2, exit 0 | **range check added by #848** — [`pd-sites-address-range.md`](pd-sites-address-range.md); the instruction-boundary precondition stays one |
| 11 | `pd_index_geometry.py:412` `_insns()` | `while i < start + length` | caller's | yes | `--helpers` and `--accesses`, exit 0 | census row + verdict |
| 12 | `pd_index_geometry.py:1062` `access_frames()` | `while i < off` | caller's | yes | `--accesses` over the image, 980 lines, exit 0 | census row + verdict |
| 13 | `second_copy_census.py:468` `framing()` | `while i < off` | caller's | yes | over the committed image, exit 0 | census row + verdict |
| 14 | `disasm8051.py:333` `converges_from()` | `while i < off` | caller's | yes | inside every `trace_xdata_refs --check` run | **no change** — #679's reason stands |
| 15 | `pd_index_geometry.py:362-403` `walk_helper()` | `for _ in range(HELPER_MAX_INSNS)` | **no** | yes | `--helpers` over the image, exit 0 | census row + verdict |
| 16 | `pd_index_geometry.py:530-566` `chain_from()` | `for _ in range(max_insns)` at `:519`, `max_insns: int = 12` at `:496` | **no** | yes | `--bases all`, 7270 lines, exit 0 | census row + verdict |
| 17 | `pd_index_geometry.py:430-431` `frame_of()` | `while i < off` | caller's | yes | driven by four of the modes: `--helpers`, `--bases`, `--sites`, `--callers` | census row + verdict |
| 18 | `pd_index_geometry.py:739` `reaches()` | `while i < lo + site` | caller's | yes | `--callers 0x0860`, exit 0 | census row + verdict |
| 19 | `second_copy_census.py:473` `framing()` | after the `:468` loop: `fw[last:last + OPCODE_LEN[fw[last]]]` | caller's | yes | as row 13 | census row + verdict |
| 20 | `pd_index_geometry.py:716` `branch_index()` | `for i in range(lo, hi - 2)` | region | yes | `--callers 0x0860`, exit 0 | census row + verdict |

Rows 1-8 are the contrast class: a bound that **is** `len(d)`, or clamped to
it, or a check that runs before the read. Eight rows, eight existing guards or
docstrings, and **no code changes** — the issue asks for a comment at one
address, and a comment at each of the other seven would be seven more shared
file edits for no required gain. **Row 8 is the one exception inside this
class**: its `len(d)` test is a real check, but it runs *after* `d[off]` has
already been read, which is the ordering #679 established everywhere else. It is
safe for a different reason, and follow-up 2 is about it.

Rows 11-20 are the class `decode()`'s fix does not reach, and the class is not
as uniform as "rows 1-8" is. Seven of the ten (11-14, 17-19) are bounded by
**a caller's number**; two (15, 16) by a **count** — a module constant
(`HELPER_MAX_INSNS`) and a parameter default (`max_insns: int = 12`) — and one
(20) by a **region**, `range(lo, hi - 2)`. What they share is only that the
bound is *not* `len(d)`, so a `len(d)` guard would be checking something other
than the loop's own invariant. All ten get a verdict, not a guard.

Rows 9 and 10 are the two the issue singles out, and the decisions differ.

## Row 9: `trace_xdata_refs.py:241-242` — the comment named the wrong disjunct

The line, as it stood before this change:

```python
        if i + 2 >= len(d) or d[i] == MOV_DPTR:
            break  # DPTR reloaded: whatever follows is a different access
```

and the comment described the **second** disjunct while being silent on the
**first**, which is the one holding the index in. The `i + 2 >= len(d)` test is
what makes the loop continue only when `i <= len(d) - 3`, so the `d[i]` at the
top of the next iteration is in range; and the `or` short-circuits, so `d[i]` is
never even evaluated when the bound fails.

A reader taking the comment at face value concludes the line is about DPTR.
That reader can reasonably move it below the `i += n`, or narrow it to the
DPTR test, and reintroduce the `IndexError` — which is exactly what the vector
below does.

**And here is the part that makes the comment more dangerous than it looks,
which the issue did not have.** Over the committed fifteen-address sweep the two
disjuncts do not fire equally at all. Instrumenting the loop to record which
disjunct ended each walk:

```
over the 114 walks the 15-address --check sweep makes:
  loop iterations, each one an OPCODE_LEN[d[i]]: 311
  smallest len(d) - i at the top of a loop:       94109
        75  d[i] == MOV_DPTR -- the DPTR test
        39  flow opcode
```

**The bounds disjunct fired zero times.** Widening the drive to *every* one of
the image's 262144 start offsets — 1330807 loop iterations — it fires 10 times,
and all 10 are from starts in the **last 10 bytes** of the image (`0x3FFF6` and
up; the walk's index reaches `0x3FFFE` and `0x40000`). The `MOV_DPTR` disjunct
fires 26257 times over the same drive.

No committed caller passes a start there. Both call sites, `trace_xdata_refs.py:330`
and `:436`, hand `walk()` an offset from `sites_for()`, which only yields
`MOV DPTR` sites, and there is no `0x90` byte anywhere in the last 64 bytes of
`ec/firmware/GMxMGxx_11.800`.

So a reader who instruments the tool finds that the comment's disjunct does
essentially all the work — 75 of 114 walks on the committed sweep, and 26257 of
every walk this image admits — while the other fires 10 times in 262144 driven
offsets. That reads as *the comment is accurate and the first disjunct is dead
code*. It is not dead code. It is the check that holds the index in range, and
the loop's other `len(d)` test does not: `:230` asks whether the *instruction*
fits (`i + n > len(d)`) rather than whether the index is readable, so it permits
`i + n == len(d)` and can leave `i` sitting at `len(d)` for the `d[i]` at the top
of the next iteration. That off-by-one is what makes the first disjunct the test
that does bound the index, and deleting it raises, as the vector below shows. The
measurement is the reason the comment has to be restated carefully rather than
casually: a comment that is merely incomplete is easy to leave alone, and this
one is contradicted by the numbers a reader is most likely to go and collect.

**What the change is.** Comment lines only, naming both disjuncts, saying
plainly which one is the bounds check and what it bounds, and saying that the
loop's own bound is `max_insns` and not `len(d)`. The trailing
`# DPTR reloaded: ...` moves off the `break` and into that block, because a
comment on the `break` can only ever read as describing the `break`. The
restatement adds five lines above the guard, so **the guard is at `:241-242`
after this change** and at `:236-237` before it; the issue and the
`walk()` call sites cite the pre-change numbers, and the sweep in the table
above is unaffected because the shape itself is at `:229`, above the edit. No
behaviour change — which is what makes command 1 a real regression test rather
than a formality.

## Row 10: `pd_index_geometry.py:635-637` — the arithmetic is a statement about this image, and the check added by #848 is not

`site_rows()` starts each window at `i = lo + addr`, where `lo` is the PD
region's `0x20000` (`trace_xdata_refs.py:77`) and `addr` is the 16-bit runtime
address `--sites` names. The loop has no flow break, so it always takes all
`SITE_WINDOW` (16) iterations, and at the table's longest instruction (3 bytes)
the arithmetic is short enough to do in the head: the highest start is
`0x20000 + 0xFFFF` = `0x2FFFF`; the 16th read is 15 increments of at most 3
later, at `0x2FFFF + 45` = **`0x3002C`**; and the image
`ec/firmware/GMxMGxx_11.800` is **262144 bytes** (`0x40000`). That leaves
**65492 bytes** between the furthest read and the end of the buffer.

`0x3002C` is that ceiling and not the read this image performs: walked from
`0xFFFF`, the sixteenth read starts at `0x2FFFF + 15` = **`0x3000E`**, because
every byte from file `0x30000` to `0x40000` is `0xFF` and `OPCODE_LEN[0xFF]` is
1. The table's cell now says *last read* rather than *peak read* and gives both
figures. The same `0xFF` fill is what fixes the first address that raised,
which is `0x1FFF1` and not the `0x1FFFB` the issue that opened #848 put it at.

Command 2 runs the tightest case the CLI offers — `--sites 0xFFF0`, whose
window really does reach the last byte of the PD region at `0x2FFFF` — and
prints its 16 listing lines with no traceback and exit 0.

**No guard is added**, per the issue and per `docs/findings.md` §4. Reachability
here is a property of a committed input that can change, and a guard justified
by "it cannot happen on this image" is a guard justified by an assumption. The
honest phrasing is the one the table uses: *did not raise over the range run*.
Note also that the arithmetic rests on `addr` being a 16-bit runtime address,
which is what the tool's own `--sites` documentation says it takes and what
`int(a, 16)` is used for — **the code does not clamp it**, so a caller naming
`0x1FFFF` would walk off the region. That is a property of the CLI, stated here
so the figure above is not read as a bound the code enforces.

**The clause "the code does not clamp it" is retracted, in place, by #848** —
and the retraction is not of the reasoning above but of its scope. The sentence
was written about the *loop*, and it was right about the loop: `SITE_WINDOW` is
still the bound, the listing reads at `:636` are still the ones the arithmetic
above describes, and nothing here is guarded against walking off **this** image.
What #848 adds is a check on the *argument*, and the two do not overlap:

- `check_site_addr()` refuses an address outside `0x0000-0xFFFF`, because
  `--sites` is documented as taking PD runtime addresses and a runtime address
  on this target is 16 bits wide on any dump. That is a statement about the
  interface, not about the 262144 bytes above, so it is not the guard
  "it cannot happen on this image" that this section declined.
- The image-dependent half is unchanged and still unenforced. A *legal* 16-bit
  address whose window happens to run past the end of a short image is still not
  caught, and the `0x3002C` arithmetic is still what decides it.

What the caveat above should now be read as is narrower than it was: the code
clamps the **range** and leaves the **boundary** to the caller, which is still
a documented precondition, and the read the table measures is still
`0x3000E` on this image rather than a bound anything enforces. The write-up,
including why the two kinds of guard are not the same kind and why the boundary
one has to stay a precondition, is
[`pd-sites-address-range.md`](pd-sites-address-range.md).

## The issue's vector does not reproduce; here is one that does

The issue reports that `b"\x01\x00\x01\x00\x01\x00"` — described as "three
2-byte non-flow instructions" — raises `IndexError: index out of range` on the
fourth iteration of a copy of `walk()` with the guard deleted.

**It does not, and the reason is in the committed tables.** `0x01` is `ajmp`:
`disasm8051.py:61` puts `range(0x01, 0x100, 0x20)` into `FLOW_OPCODES`, and
`OPCODE_LEN[0x01]` is 2. So `walk()` decodes the first instruction and breaks
at `:233` on the flow test, long before a fourth iteration exists — with the
guard present *and* with it deleted:

```
vector: issue's b"\x01\x00\x01\x00\x01\x00"
  guard as committed  -> 1 instruction(s): [(0, '0100')]
  guard deleted       -> 1 instruction(s): [(0, '0100')]
```

A vector that works against this loop as committed is `b"\x00\x00\x00\x00"`.
`0x00` is 1 byte (`OPCODE_LEN` row 0), is not a flow opcode, and is not
`MOV_DPTR` (`0x90`), so the walk runs until something else stops it:

```
vector: derived b"\x00\x00\x00\x00"
  guard as committed  -> 2 instruction(s): [(0, '00'), (1, '00')]
  guard deleted       -> IndexError: index out of range

walk of b"\x00\x00\x00\x00" with the guard PRESENT:
  iteration 1: i=0 n=1, appended, i becomes 1
  iteration 2: i=1 n=1, appended, i becomes 2
  iteration 3: i=2 n=1, appended, i becomes 3
  iteration 4: i=3, appended, i becomes 4, then the guard sees i+2=4 >= len(d)=4 and breaks

walk of b"\x00\x00\x00\x00" with the guard DELETED:
  iteration 1: i=0 n=1, appended, i becomes 1
  iteration 2: i=1 n=1, appended, i becomes 2
  iteration 3: i=2 n=1, appended, i becomes 3
  iteration 4: i=3 n=1, appended, i becomes 4
  iteration 5: OPCODE_LEN[d[4]] raises IndexError -- d is 4 bytes long
```

With the guard present the fourth iteration appends, `i` becomes 4, and the
test `i + 2 >= len(d)` is `4 >= 4` — true, and the walk stops with two
instructions. With it deleted the walk reaches a fifth iteration and reads
`d[4]` out of a 4-byte buffer. The two rows are the property, and the property
is the reason the guard is load-bearing.

**Two corrections to the issue's own recipe, so a reader does not hit either.**
The guard is **two lines** — the `if` and the `break` it owns — so deleting the
one physical line the issue names leaves an orphaned `break` and an
`IndentationError`; "delete line 236" has to mean delete the guard. And the
number itself is now stale: the restatement in row 9 adds five lines above it,
so the guard is at **`:241-242`** after this change, not `:236-237`. The two
blocks above were produced by locating the guard by its source text rather than
by a line number, which is why they read the same before and after.

**Nothing in this repository ever asserted the issue's vector**, so unlike
`docs/findings.md` §4 there is no wrong claim in a committed file to retract in
place. The correction lives here, beside the claim it corrects, and the wrong
vector is left visible above rather than quietly replaced.

## What this does not say

- **No site "cannot raise".** Every reachability cell above is a property of
  the committed inputs and of the range that was run. Row 10 in particular is
  arithmetic over a 262144-byte image, not a property of the code, and the
  `addr` it rests on is a documented convention rather than a clamp. **#848
  added a range check to row 10 and that does not make this bullet wrong**: the
  check refuses an address the arithmetic never had to survive, and the last read
  — `0x3000E` on this image, under the `0x3002C` ceiling — is still decided by
  these bytes. The instruction-boundary precondition is still unchecked, and
  still a precondition.
- **The sweep bounds the table, not reading.** Per the caveat in
  `ec/annotations/registers.yaml`, a sweep that finds nothing means "not found
  by this method". Twenty functions is what this grep finds in `ec/tools/`
  today; it is not a claim that no other tool or no other buffer-indexed table
  has the shape. The other two tools directories have been swept the same way
  since, and found nothing **by this method**:
  `grep -rn 'OPCODE_LEN\[' --include=*.py bios/tools windows/tools` returns no
  lines, and neither directory can have the shape for a stronger reason than
  the empty grep — `OPCODE_LEN` is defined once, in `ec/tools/disasm8051.py:39`,
  and nothing under `bios/` or `windows/` imports `disasm8051` at all. Both
  commands and their counts are in
  [`rel8-displacement-bound.md`](rel8-displacement-bound.md) (issue #847).
- **No live test ran.** No EC was opened, no register read back, no hardware
  and no Windows involved. Every number here is a static read of a committed
  file or the output of a command over a committed file.
- **No behaviour changed.** The one code edit is comment lines in one function.
  Command 1 diffs a full sweep against the committed CSV before and after and
  both exit 0, which is the evidence for that sentence. (That sentence is about
  *this census's* edit, and only about it. #848 later added a real range check to
  the same tool's `site_rows()`; it is diffed the same way, over `--sites` on
  the legal range, in
  [`pd-sites-address-range.md`](pd-sites-address-range.md).)
- **Nothing is claimed about what the EC does** with any of this. The shape is
  a property of Python walking a `bytes` object.

## Reproducing it

All of it, from the repository root. The six commands first, then the one
snippet behind row 9 and the vector section — which is why those two claims
carry an offset list and a disjunct tally rather than a number in prose.

Command 1 is the load-bearing one: it diffs a 114-site sweep against the
committed `ec/annotations/xdata-086x-dispatch-sites.csv`, so it fails if the
comment restatement changed any behaviour.

```sh
# 1. the sweep behind every row, and the proof the row 9 edit is comment-only
python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
  0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
  0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv --census-column --check

# 2. row 10's reachability, the tightest window the CLI offers
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0xFFF0

# 2b. the pair that bounded row 10 before #848: 0x1FFF0 exited 0 and 0x1FFF1
# raised, and both are now refused (exit 2) by the range check, because
# neither is a 16-bit runtime address. The pair is kept because the row's
# arithmetic is about it; the outputs are in
# docs/findings/pd-sites-address-range.md.
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0x1FFF0
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --sites 0x1FFF1

# 3-6. rows 11, 12, 15, 16, 17, 18, 20 over the whole image
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --helpers
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --bases all
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --accesses
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --callers 0x0860

# 7. rows 13, 19, and row 14 inside every command 1 run
python3 ec/tools/second_copy_census.py

# 8. the excluded adjacent shape, and row 8's module
python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800
python3 ec/tools/walk_branch_arms.py --self-test ec/firmware/GMxMGxx_11.800
python3 ec/tools/disasm8051.py --self-test
```

**Note on command 1's argument list.** The plan this was implemented from names
one address, `0x0860`, for this command. That does not reproduce the committed
CSV and exits 1 at baseline: the file carries 105 rows the single-address sweep
never reaches, because `ec/annotations/xdata-086x-dispatch.md` §1 names all
fifteen. The fifteen-address form above is the one that exits 0, before and
after the edit, and it is the form recorded on that page.

The two self-tests and `bash tools/run-tests.sh ec/tools` are green and pick up
nothing new, which is the point: this work adds no suite. *(Merged-tree note
(2026-09-25): the two self-tests are green on the merged tree, and the tally is
unchanged from `origin/main` — `19 suite(s) run, 600 tests` on both, thirty
suites and 882 tests for the whole runner — so "adds no suite" holds. What the
merge changes is the verdict: one suite is red, `test_check_cluster_citations.py`,
on `:220` of `docs/findings/xdata-cluster-names-guard-off-recipe.md`, a file and
line `2ed6f030` (#822) added and this work never touched. It is the same red
`docs/findings.md` §52 already names, it reproduces on a clean `origin/main`,
and it is named rather than fixed here for the reason §52 gives.)*

The snippet needs no committed file of its own. It re-reads the tool, so it is
correct both before and after the restatement — which is the only reason to
write it this way.

```sh
python3 - <<'EOF'
import collections, sys
sys.path.insert(0, "ec/tools")
import trace_xdata_refs as T

SRC = "ec/tools/trace_xdata_refs.py"
d = open("ec/firmware/GMxMGxx_11.800", "rb").read()
lines = open(SRC).read().splitlines(keepends=True)
# Locate the guard by its source text, not by a line number: the restatement in
# docs/findings/opcode-len-bounds-census.md adds five lines above it.
guard = next(i for i, l in enumerate(lines) if "i + 2 >= len(d)" in l)

def load(src, name):
    m = type(sys)(name); m.__file__ = SRC
    exec(compile(src, SRC, "exec"), m.__dict__); return m

# The guard is its `if` plus the `break` it owns; the `if` alone strands the break.
kept = load("".join(lines), "kept")
cut  = load("".join(lines[:guard] + lines[guard + 2:]), "cut")
print("guard at line %d: %r" % (guard + 1, lines[guard].rstrip()))

for label, vec in [("issue's b'\\x01\\x00\\x01\\x00\\x01\\x00'", b"\x01\x00\x01\x00\x01\x00"),
                   ("derived b'\\x00\\x00\\x00\\x00'", b"\x00\x00\x00\x00")]:
    print("\nvector: %s" % label)
    for name, mod in (("guard as committed", kept), ("guard deleted     ", cut)):
        try:
            out = mod.walk(vec, 0)
            print("  %s -> %d instruction(s): %s"
                  % (name, len(out), [(i, r.hex()) for i, r, _ in out]))
        except IndexError as e:
            print("  %s -> IndexError: %s" % (name, e))

# Which disjunct ends each walk. `committed` is the fifteen-address sweep the --check
# run does; the wide drive is every offset of the whole image.
def census(buf, starts):
    ended, hits, margin, iters = collections.Counter(), [], [], 0
    for start in starts:
        i = start
        for _ in range(8):
            iters += 1
            margin.append(len(buf) - i)
            n = T.OPCODE_LEN[buf[i]]
            if i + n > len(buf):
                ended["instruction does not fit"] += 1; break
            if buf[i] in T.FLOW_OPCODES:
                ended["flow opcode"] += 1; break
            i += n
            if i + 2 >= len(buf):
                ended["i + 2 >= len(d) -- the end-of-buffer check"] += 1
                hits.append((start, i)); break
            if buf[i] == T.MOV_DPTR:
                ended["d[i] == MOV_DPTR -- the DPTR test"] += 1; break
        else:
            ended["max_insns (8) exhausted"] += 1
    return ended, hits, margin, iters

ADDRS = "0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B " \
        "0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07".split()
sites = [o for a in ADDRS for o in T.sites_for(d, int(a, 16))]
ended, _hits, margin, iters = census(d, sites)
print("\nover the %d walks the %d-address --check sweep makes:" % (len(sites), len(ADDRS)))
print("  loop iterations, each one an OPCODE_LEN[d[i]]: %d" % iters)
print("  smallest len(d) - i at the top of a loop:       %d" % min(margin))
for why, n in ended.most_common():
    print("  %8d  %s" % (n, why))

ended, hits, margin, iters = census(d, range(len(d)))
print("\nwalk() driven from all %d offsets of the %d-byte image:" % (len(d), len(d)))
for why, n in ended.most_common():
    print("  %8d  %s" % (n, why))
print("smallest len(d) - i at the top of a loop: %d" % min(margin))
print("the %d start(s) that reached the end-of-buffer check: %s"
      % (len(hits), ", ".join("0x%05X -> 0x%05X" % h for h in hits)))
print("0x90 (MOV DPTR) in the last 64 bytes of the image: %s" % (0x90 in d[-64:]))
EOF
```

```
guard at line 241: '        if i + 2 >= len(d) or d[i] == MOV_DPTR:'

vector: issue's b'\x01\x00\x01\x00\x01\x00'
  guard as committed -> 1 instruction(s): [(0, '0100')]
  guard deleted      -> 1 instruction(s): [(0, '0100')]

vector: derived b'\x00\x00\x00\x00'
  guard as committed -> 2 instruction(s): [(0, '00'), (1, '00')]
  guard deleted      -> IndexError: index out of range

over the 114 walks the 15-address --check sweep makes:
  loop iterations, each one an OPCODE_LEN[d[i]]: 311
  smallest len(d) - i at the top of a loop:       94109
        75  d[i] == MOV_DPTR -- the DPTR test
        39  flow opcode

walk() driven from all 262144 offsets of the 262144-byte image:
    119530  max_insns (8) exhausted
    116347  flow opcode
     26257  d[i] == MOV_DPTR -- the DPTR test
        10  i + 2 >= len(d) -- the end-of-buffer check
smallest len(d) - i at the top of a loop: 1
the 10 start(s) that reached the end-of-buffer check: 0x3FFF6 -> 0x3FFFE, 0x3FFF7 -> 0x3FFFE, 0x3FFF8 -> 0x3FFFE, 0x3FFF9 -> 0x3FFFE, 0x3FFFA -> 0x3FFFE, 0x3FFFB -> 0x3FFFE, 0x3FFFC -> 0x3FFFE, 0x3FFFD -> 0x3FFFE, 0x3FFFE -> 0x3FFFF, 0x3FFFF -> 0x40000
0x90 (MOV DPTR) in the last 64 bytes of the image: False
```

## Follow-ups this opens

1. **The count-bounded walks in `pd_index_geometry.py` are the real gap.** Rows
   15 and 16 are bounded by a *count* (`HELPER_MAX_INSNS`, and `chain_from`'s
   `max_insns: int = 12` default) with no end-of-buffer check anywhere, and they
   are the **parents** of the bounded
   sites the table already covers — `walk_helper` and `chain_from` own the
   budgets the reachability arguments turn on. Now that the `len(d)`-bounded
   walks are written down as a class, whether these two should get a real
   bounds check is a well-posed question. It needs its own issue: the answer
   depends on what invariant a count-bounded walk is supposed to enforce,
   which is a design question and not a bug report. **#848 measured one end of
   it and deliberately did not fix it**: `--helpers 0x1FFE8` exits 0 and
   `--helpers 0x1FFE9` raises `IndexError`. `walk_helper` is also called with
   targets `chain_from` decodes out of the image's own branch operands, so a
   blanket range check there has a second contract to satisfy — which is the
   design question, and is why the fix waits for the issue rather than arriving
   with row 10's.
2. **`walk_branch_arms.py:328`'s `descend()` is the one contrast case whose
   check runs *after* the read.** Rows 1-7 all put the end-of-buffer test
   before the index it guards, which is the shape #679 established.
   `descend()` reads `d[off]` at `:327`, indexes at `:328`, and only then tests
   `off + n > len(d)` at `:329`. That is safe for a different reason — `off`
   comes from `offset_for_runtime()`, which is `None`-checked at `:321-322`, so
   the read is in range before the length test is reached — and the comment at
   `:337-339` explains why the operand bytes are read separately. Worth its own
   look, because it is the single place in the table where the post-#679
   ordering is not what #679 established, and a reader scanning for "index
   before bounds" will land on it.

   **(2026-09-26, #844: the reason in the paragraph above is wrong as a general
   claim, and the ordering it describes no longer exists. The paragraph stands
   as the record; this is the correction beside it.)** It says the read is in
   range "`before the length test is reached", on the strength of
   `offset_for_runtime()` being `None`-checked. **`None`-checked is not the same
   as in-range**: returning non-`None` says the *runtime address* is inside a
   mapped region, and nothing in it says the *file offset* it computes is inside
   the buffer. Those coincide only while the buffer is as long as the region
   table implies, and `descend()` never said so. The arithmetic is in
   [`descend-index-guard.md`](descend-index-guard.md); the short version is that
   the region table's ceiling is `0x2FFFF` and `main()`'s PD-marker check
   certifies only `0x2004A`, so 65461 bytes of the range are unguarded.
   **The verdict is the pre-read check** `test_site()` already has, now at
   `walk_branch_arms.py:343`, above the read at `:346`; the `off + n > len(d)`
   test stays at `:353` because it answers a different question (does the
   *instruction* fit, which `off + n == len(d)` satisfies) and was never what
   held the index. The line numbers above are the pre-#844 ones: the read is
   `:327`→`:346`, the index `:328`→`:347`, the fits test `:329`→`:353`, the
   `None`-check `:321-322`→`:328-329`, and the operand comment `:337-339`
   →`:361-363`.

---

## Note (2026-09-25, issue #846): the 119530's per-table consequence, and where row 9's line numbers went

Two records. Neither rewrites what is above: the line numbers in row 9 and in
`docs/findings.md` §53 are a record of the tree at the time this census was
written, and a reader checking them after #846 is reading a moved file, not a
wrong one. The same shape the note on `tools/README.md`'s totals uses.

**1. The per-table consequence of row 9's 119530.** That figure is over every
start offset in the image. Over the committed tables it is 45, out of 1288
rows across the nine `window` columns `walk()` produces — and that is what a
reader of a site table actually meets, because the table row is the unit the
CSV records:

| | rows | `max_insns (8) exhausted` |
|---|---:|---:|
| `ec-07c4-07d5-sites.csv` | 117 | 16 |
| `ec-07d6-07d7-sites.csv` | 213 | 13 |
| `ec-0x07d1-sites.csv` | 76 | 10 |
| `ec-0x07d0-sites.csv` | 254 | 4 |
| `manual-fan-ctrl-0751-sites.csv` | 29 | 1 |
| `xdata-0400-045f-sites.csv` | 409 | 1 |
| `ec-09e9-09eb-sites.csv` | 9 | 0 |
| `xdata-086x-dispatch-sites.csv` | 114 | 0 |
| `xdata-1c3x-consumers-sites.csv` | 67 | 0 |

The `0x086x` row's zero is this census's own 39/75 over the same 114 rows,
reached by a second route. All 45 are listed in
`ec/annotations/walk-budget-census.csv`; the write-up is
[`walk-window-terminators.md`](walk-window-terminators.md).

**2. Where row 9's line numbers moved.** `walk()`'s loop is now
`walk_why()`'s, and `walk()` is that function's first element. The mapping, for
anyone following a citation above:

| cited above | is now | what moved |
|---|---|---|
| `:224-243` (`walk()`) | `:278-319` (`walk_why()`) | the whole body |
| `:229` (`n = OPCODE_LEN[d[i]]`) | `:297` | unchanged, lifted |
| `:230` (`if i + n > len(d)`) | `:298` | unchanged, lifted |
| `:241-242` (the guard and its `break`) | `:311-318` | split: two guards, two `break`s, each naming its own token |
| `:330` (a `walk()` call site) | `:418` | now `insns, why = walk_why(d, o)` |
| `:436` (the other call site) | `:563` | likewise, in the non-CSV decode |

The symbol is named in every row as well as the line, so a later edit to a
comment moves the number without making the row unreadable: `walk_why()` at
`:278`, `walk()` at `:322`, the two guards at `:311` and `:316`. The one
number worth quoting and not relying on is the guard's new home, because
`:298` still permits `i + n == len(d)` and `:311` is what holds the index —
the same asymmetry row 9 records, now with the `or` made into two statements
so each token can name the guard it belongs to.

The 311 iterations and 114 walks of the sweep below are unchanged, and that is
the regression test: command 1 in *Reproducing it* still reproduces
`xdata-086x-dispatch-sites.csv` byte for byte, because the `0x086x` table was
deliberately not re-cut. Row 9's shape — `range(max_insns)`, `len(d)` tested
twice, only the second test bounding the index — is exactly as recorded; what
moved is the arithmetic of the citation, and `:298`'s test still permits
`i + n == len(d)` while `:312` is what holds the index.

`walk()`'s own budget is still 8, and nothing here argues for a value. What
#846 does add is the finding that raising it to 64 would rewrite 13 committed
`access` cells, 10 of them wrongly — so the parameter is now a recorded fact
with a cost attached rather than one nobody can account for.
