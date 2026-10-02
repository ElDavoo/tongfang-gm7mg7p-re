# The main EC image's code map: a recursive descent from the entry points

[`code-map.csv`](code-map.csv) is this file's machine-readable half. It is
written by [`../tools/code_map.py`](../tools/code_map.py) and by nothing else;
`--check` recomputes it from the committed firmware and fails on any difference.

```console
$ python3 ec/tools/code_map.py ec/firmware/GMxMGxx_11.800 --report
$ python3 ec/tools/code_map.py ec/firmware/GMxMGxx_11.800 --check
$ python3 ec/tools/code_map.py ec/firmware/GMxMGxx_11.800 --at 0x15BA
```

**What the map is.** A worklist descent over `common`, `bank0` and `bank1` of
`ec/firmware/GMxMGxx_11.800`, seeded from the image's own entry points, marking
every byte it decodes. It answers one question per byte: *did a walk from these
seeds decode this byte?* That is a much weaker question than "is this byte
code", and [the third section](#the-three-verdicts-and-why-there-are-three)
is where the difference is drawn.

Nothing here measures hardware. No register was read, no capture was opened,
no `status:` in [`registers.yaml`](registers.yaml) moves on this, and no live
test is claimed — every input is a committed file.

## The three verdicts, and why there are three

| verdict | the byte is |
|---|---|
| `code` | the first byte of an instruction a walk decoded |
| `operand` | a later byte of an instruction a walk decoded |
| `unreached` | in no decoded instruction, from no seed, in this map |

**Issue #53 asked for a two-state `code`/`unreached` map, and under that map its
own acceptance test fails in the direction that matters.** The two sites it
names — `0x015BA` and `0x01110` — are the third and second bytes of a
`mov dptr,#0xC881` at `0x015B8` and of a `clr 0x91` at `0x0110F`. A descent
decodes both of those instructions, and so does any byte scan, so both sites
come out **`code`** on a two-state map: the opposite of the verdict
[`docs/findings/paged-trampoline-hits-by-hand.md`](../../docs/findings/paged-trampoline-hits-by-hand.md)
reached for them by reading their bytes. That reading stands; what changes is
that a two-state map cannot express it, and a map that cannot express it would
have appeared to *confirm* it while inverting it.

The third state is the whole of the fix, and it is the only reason this file is
not the shape the issue sketched. The issue's own wording allows for this —
"come out `unreached` **or the discrepancy is explained**" — and what follows is
the explanation.

```console
$ python3 ec/tools/code_map.py ec/firmware/GMxMGxx_11.800 --at 0x15BA
0x015BA (common) is operand: byte 2 of 3 of `0x015B8 90 c8 81` `mov dptr,#0xc881`
$ python3 ec/tools/code_map.py ec/firmware/GMxMGxx_11.800 --at 0x01110
0x01110 (common) is operand: byte 1 of 2 of `0x0110F c2 91` `clr 0x91`
```

`--at` prints the instruction, because `operand` on its own is a claim about
framing and the instruction is the evidence.

**`unreached` means "not reached by this method", never "data"**
([`docs/findings.md`](../../docs/findings.md) §4c). A byte can land there
because no seed reaches it, because its only in-edges are edges this walk does
not follow, or because the walk stepped over it as the inline argument block or
case table of a call. [`docs/findings/7151-case-tables-in-the-walk.md`](../../docs/findings/7151-case-tables-in-the-walk.md)
establishes that one such block in this image is a case table; this map calls its
bytes `unreached`, which is a weaker and different statement and does not
restate it. The word is the claim; nothing here upgrades it. The PD image at
`0x20000`+ is a separate program with its own address space and is not mapped
here at all.

## The seed set, and why coverage is a property of it

`--seeds narrow` (the default, and what the committed map is built from) seeds
from the image's own entry points and nothing else:

| seed basis | what it is |
|---|---|
| `vector` | the reset/interrupt vector table, walked by `discover_vector_table()` rather than read off a hardcoded offset list — that function's docstring records what a hardcoded list does, which is seed the wrong addresses on an image whose table is laid out differently, and the failure then reads as "the firmware has no handler there" |
| `vector-target` | the common-area addresses those entries point at |
| `trampoline` | the BL51 bank-switch entries `audit_call_targets.trampolines()` finds by shape |
| `trampoline-target` | where each trampoline's DPTR immediate lands, in the bank `find_stubs()` says its stub selects |

**A coverage figure for this map is a claim about that list, not about the
firmware**, and the tool is built so the claim is easy to make honestly:
`--seeds wide` adds every target the three committed censuses name, and prints
its coverage beside the narrow one rather than instead of it.

| region | reached, all bytes | reached, live bytes |
|---|---:|---:|
| `common` | 45.8% | 33.9% |
| `bank0` | 72.2% | 44.0% |
| `bank1` | 25.0% | 21.6% |

Live bytes are the region's bytes outside an erased run, at
`audit_call_targets.MIN_ERASED_RUN` — the denominator a coverage figure about
*code* wants, since erased flash is never code and counting it makes every
figure look worse than it is. Both columns are `--report` output; neither is
written down as a property of the image.

**The wide set reaches 90.2% / 96.4% / 93.9% and that number should not be
quoted as this method's reach.** A census row's target becomes a seed, so a byte
the censuses name as a call target is `code` by construction, and the wide
figure is partly the censuses restated. It is in the tool because the gap the
narrow set leaves is the interesting part, and because the wide run's own
framing disagreements are visible — thousands of bytes the wide seeds reach as
an entry point that another arm had already decoded as an operand, which the
narrow walk never does.

## bank1 reaches a quarter of itself, and the reason is the linker

`--report`'s seed table is the whole of the explanation: 350 of the 403
trampolines select bank 0 and 53 select bank 1, so bank1 enters this map through
an eighth of the firmware's cross-bank paths. Once inside a bank the walk
follows intra-bank `lcall`/`ljmp` and relative edges normally — bank1's distinct
banked call targets are ordinary seeds-by-edge, and the count is printed by the
one-liner below — but nothing else brings a caller in. A bank the linker rarely
crosses into is a bank this method seeds thinly.

```console
$ python3 -c "
import csv, collections
rows = csv.DictReader(open('ec/annotations/bank-call-targets.csv', newline=''))
print(len({r['target'] for r in rows if r['region'] == 'bank1'
           and int(r['target'], 16) >= 0x8000}))"
608
```

25.0% is **not reached by this method**, never "mostly not code". Bank1 has
24,574 unreached bytes and bank0 has 9,110, and the difference is entirely in
how many entry points each was handed.

## Blind spots, named

Each of these is a place the walk cannot go. None of them is a claim about the
bytes.

- **Computed targets.** `jmp @a+dptr` is a real transfer this walk never
  follows. The narrow descent decodes 3 of them in `common` and 7 in `bank1`;
  every byte past one is `unreached` unless another route reaches it. The suite
  asserts the shape directly — a `jmp @a+dptr` yields no target, because a walk
  that invented one would be guessing an address and a bank out of a register.
- **The trampoline is followed, and that is a decision rather than an omission.**
  Issue #53 lists "the trampoline's DPTR-carried target" among the computed-target
  blind spots. That is right for a walk that does not know which stub it called
  and wrong for this one: `find_stubs()` recovers the selected bank from the
  stub's own `clr`/`setb` port writes, so the bank is read off the image rather
  than inferred, and the address the entry carries in DPTR is exact. Without
  this edge both banks come out at 0.0%, because the common area's own decoded
  instructions contain no direct banked call at all.
- **Bucket C.** A `>= 0x8000` target from the common area is genuinely
  unresolvable — nothing in the byte says which bank is mapped — and
  `offset_for_runtime()` returns `None`. The walk declines those edges, counts
  them under `target does not resolve from this region`, and guesses no bank.
- **The same-bank assumption, carried unchanged.** Every bucket-B edge — a
  `>= 0x8000` target from inside a bank — is resolved by
  `offset_for_runtime()`'s convention that the target is in the caller's own
  bank. [`bank-call-audit.md`](bank-call-audit.md) §3 is why that cannot be
  proved from the bytes, and this map inherits the assumption without testing
  it. A bucket-B edge that is really a cross-bank call would put this map's
  `code` bytes in the wrong bank's window.
- **Inline data.** A `lcall` to an address in `disasm8051.INLINE_ARG_CALLS` or
  `CASE_TABLE_CALLS` is followed and its inline block stepped over, because a
  walk that decoded a case table as instructions would be misframed from there
  to the end of the region. Those bytes come out `unreached`, and that is the
  honest verdict: this map does not decode them, and
  [`docs/findings/7151-case-tables-in-the-walk.md`](../../docs/findings/7151-case-tables-in-the-walk.md)
  is where the claim that they are data is established. The step-over is load-
  bearing here and not merely tidy — [the section below](#the-15-dispatch-calls-into-issue-50s-tables-and-what-two-methods-agree-on)
  is what it buys.
- **The region edge.** An instruction that would take a byte from the next
  region is not decoded. The narrow walk stops on no such edge, and `--report`
  prints the count either way.

## The three censuses, annotated

[`audit_call_targets.py`](../tools/audit_call_targets.py) `--map-column` adds
one column to each of its three CSVs: this map's verdict for the **site byte**.
It is off by default and the committed CSVs are byte-identical without it,
which is what makes "no count moves" structural rather than a promise.

| census | `code` | `operand` | `unreached` |
|---|---:|---:|---:|
| `bank-call-targets.csv` | 2,732 | 479 | 2,787 |
| `bank-paged-call-targets.csv` | 0 | 1,744 | 1,737 |
| `bank-relative-branch-targets.csv` | 2,575 | 2,270 | 4,231 |

```console
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 \
    --paged-csv --map-column | cut -d, -f2,14 | sort | uniq -c
   1737 common,unreached
   1744 common,operand
```

**The paged row is the sharp one: not one of the paged byte-scan sites is an
instruction start under this walk's framing.** 1,744 of them are the operand
byte of an instruction the descent decoded — exactly the shape #54 read by hand
— and the other 1,737 are in bytes no walk from these seeds touches. That is
consistent with the census being a byte-scan upper bound over a two-byte
opcode, and it is *not* a retraction of the census: `operand` is not `phantom`
and `unreached` is not `data`. #54's hand reading extended from 18 sites to
none of the rest, and this map extends it to none of the rest either.

The relative row is the middle case and the reason a column beats a filter: the
census's `operand` and `unreached` sites are each a substantial population, and
a reader who wants the byte-scan phantoms is the reader who needs to see which
are which. Nothing is dropped.

## The 15 dispatch calls into issue #50's tables, and what two methods agree on

The sharpest thing the walk found is not a disagreement. Every span in
[`index-table-spans.csv`](index-table-spans.csv) is reached at its **dispatch
call**: the narrow descent decodes the `lcall 0x7151` that introduces it, and
steps over exactly the block `decode_index_table.py` independently measured as
the table. Both mark the span's own bytes `unreached`.

The two routes never call each other's code — `disasm8051.case_table_len()`
scans for the `00 00` terminator a case table ends on, and
`decode_index_table.py` finds the calls by the reader's prologue and its own
table walk — so this is corroboration rather than a restatement. **Every span
extent agrees, to the byte**: the tables end where the other method says they
end, and each is reached through a call a descent follows. That is a statement
about the firmware that neither method makes on its own, and
`test_code_map.py` holds the two to each other span by span.

What the two do *not* agree on is what that means. `decode_index_table.py` says
the block is a switch table and reads its entries; this map says no walk from
these seeds decodes those bytes as instructions, which is a statement about entry
points and edge classes rather than about what the bytes are. Under the *wide*
seed set every span picks up decoded bytes, and `0x04064`'s comes out with no
`unreached` byte left in it at all — which is not evidence against #50, it is what
happens when a table's bytes are handed to the walk as seeds. That is the
circularity the wide seed set exists to expose.

**Neither verdict adjudicates the other, and this does not close #50.** The
data-side partition is a different question from the code-side one. What this
change establishes is narrower and is stated here rather than left implied: the
dispatch calls are reachable and decoded, and the tables' extents are confirmed
from a second direction.

## What does not move

No `status:` in [`registers.yaml`](registers.yaml) changes: a decode is not a
behaviour, and nothing here is a live observation. The three committed censuses
are byte-identical without the new flag. [`bank-call-audit.md`](bank-call-audit.md)
§7 is left exactly as written — its two named sites are answered here rather
than edited there, and §7's own text still stands.

Nothing here needs the laptop or Windows, so nothing is deferred to a human at
the machine.