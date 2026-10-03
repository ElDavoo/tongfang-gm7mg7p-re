# `0x07D2` is an index in some routines and a 16-bit window's low byte in others, and choosing between them is the wrong question

Issue #226 asked whether the PD firmware's `0x07D2` is "only the high half of
the `0x07D1` word, or an index in its own right", because the 16-bit reading
predicts one and three inline stride multiplies predict the other. The site
table that answers it is `ec/annotations/ec-0x07d2-sites.md`, with
`ec-0x07d2-sites.csv` beside it. This file carries only what is worth stating
across the whole stack, and what stayed open.

**The answer.** On the PD side `0x07D2` is both: all nine of its `inc dptr`
walks put it in the low position of a 16-bit — or, at `0xF628`, 24-bit — window
with `0x07D3`, while four sites multiply it into an address on its own, so the
address is a word's low byte in some routines and a standalone index in others,
and no single reading of it holds everywhere.

Neither half of the question is the whole of the evidence, so the framing's
either/or does not have an answer. What the walk does establish is that both
readings are real and that they are *in different routines* — which is the part
a single-byte classification had hidden, and it is why
`ec/annotations/ec-0x07d1-sites.md` §4.3's refusal to choose between a 3-byte
counter, a packed field and a moved 16-bit value survives this walk rather than
being overturned by it.

## The evidence, in one paragraph each

**Word half.** `0xAD83` and its neighbour `0xAD8C` are nine bytes apart and are
the clearest pair: the first reads `0x07D1` into `R7`, `inc dptr`, reads `0x07D2`
into `R5` — the little-endian load, `0x07D2` the high byte. The second reads
`0x07D2` into `R7` and **clears `R5`**. Two accessors, one loading the pair and
one loading the high half zero-extended, is what a 16-bit unit looks like from
outside. `0x8BAD` builds `R4`/`R5` from `0x07D2` then `0x07D3`; `0xA5DD` and
`0xC755` store an `R6`/`R7` and an `R7`/`R5` pair to `0x07D2` then `0x07D3`;
`0xA61C` loads them with `0x07D2` in `A` and `0x07D3` in `B`; `0xF628` writes
three. And `0x8A4A` stores `R7` to `0x07D1` then clears `0x07D2` *and* `0x07D3`,
so the window has three lengths in it.

**The `0x9411` constant appears three times.** `ec-0x07d1-sites.md` §4.3 records
`0x3E91` storing the literal `0x07D1 ← 0x11`, `0x07D2 ← 0x94` — "so the value
`0x9411`". Two further routines, `0x7580` `set_07d2_and_return_r7_zero_or_one` and
`0xB311` `write_07d2_then_dispatch_on_07d1`, load the same 16 bits as an immediate
pair (`mov R2,#0x11 ; mov R3,#0x94`) into the call `0x775C` makes, and both open by
storing `R5` to `0x07D2` before pointing DPTR at `0x07D1`. One constant that is
only meaningful if the two bytes are read as halves of a number, appearing in
three routines, is not what a coincidentally-adjacent pair of independent
variables produces on its own. It is still not a *naming* of the field, and
nothing here claims one.

**Index in its own right.** `0x35FF` and `0x373C` multiply the byte by stride
`0x5E`, `0xC7A8` by `0x17`, each against a base add — the same geometry
`0x07D0` and `0x07D1` use, reached from a third index byte. `0x4A6D` goes one
step further than any of them: it multiplies by `4` and puts the product
straight into `DPTR` with no base at all, so it is a pointer scale rather than
a structure stride. A base-less multiply is not itself new — `0x07D0`'s
`0x98A1` has one — but there the product goes back to the caller in `R7`/`R6`,
and here it becomes the address.

**Bit operations, and the field boundary.** `0x8B70` does `orl a,#0x08` on
`0x07D2` and stores it back; `0x8B81` reads `0x07D2`, stores it back unchanged,
then does `orl a,#0x02` on **`0x07D3`** after the `inc dptr` and stores that. So
the firmware sets bit 3 of `0x07D2` and bit 1 of `0x07D3` — a field straddling
the byte boundary, written by two separate instructions rather than one.

`0x8BAD` is a third `orl a,#0x01`, also on `0x07D3` after the `inc dptr`, and it
does **not** store: the result goes into `R5`, and the `R4`/`R5` pair is handed
to `0xDC29`, which writes `R4` to `0xFFFE` and `R5` to `0xFFFF`. It is evidence
that the firmware treats the two bytes as one unit, because it builds a single
register pair out of `0x07D2` then `0x07D3`; the field-boundary claim rests on
the two sites that store.

**This is not the DSDT's unnamed bit field, and the issue's question was a trap
in that direction.** The ECMG field list reads `Offset (0x7D0), DBD1, 8, DBD2,
8, Offset (0x7D3), , 4` and `GFID, 3`
(`evidence/acpi/dsdt.dsl:52248-52252`). `DBD1` is `0x07D0` and `DBD2` is
`0x07D1`, so the two 8-bit fields end where `0x07D2` begins and the next
`Offset` is `0x7D3`: **`0x07D2` is in no DSDT field at all**, outside the list
rather than unnamed in it, while bits 3:0 of `0x07D3` *are* inside the unnamed
4-bit run. The firmware spans a field boundary the ASL draws one byte earlier.

## Two corrections to things that were already written down

**`0x07D2` has no name to borrow, and the spelling that exists is not one.** It
is absent from `windows/decompiled/v3.1.6.0/ECSpec.cs`, no row in the
service's `ec-callsites.csv` names it, and the only spelling any committed input
carries is `DAT_EXTMEM_07d2` — this repository's generic placeholder for an
unnamed XDATA byte, which is what `ec/decompiled/pd/A571.c` emits and what
`xdata-registers.csv`'s `spelled_as` column records. The `registers.yaml` entry
says so in its `name`, so a later reader does not mistake the placeholder for a
vendor symbol.

**The `no movx` classification cell is this method stopping, not the site being
inert.** `0x6757` is scored `no movx found in the decoded window` because the
instruction after its `MOV DPTR,#0x07D2` is `cjne a,#0x02` and the walk stops at
a branch. It is a **write**: both arms store a constant through that DPTR, `0x02`
when `[0x07F9]` equals 2 and `0x01` otherwise. The cell means "the walk stopped
before reaching the access", which is not "no access happens here" — a
distinction worth carrying to any future walk whose guard fires.

## What this does not move

**No EC-side status, and none was moved.** A PD-image decode cannot move an
EC-side grading. The new `registers.yaml` entry carries `unknown-not-absent`,
not `present-untested`, because rule 2 of that file's header requires
`static_refs_main_ec >= 1` and this address's count there is 0 — the same reason
`0x07CC` was re-graded. The entry deliberately carries **no**
`DO-NOT-WRITE-BLIND` suffix, unlike `0x07D0` and `0x07D1`: that suffix's declared
warrant is a byte Windows demonstrably writes with no traceable EC-side handler,
and the DSDT does not name `0x07D2` at all, so there is no committed writer to
warn a reader about. That is a statement about the committed inputs, not a
licence to write the byte.

**Nothing was observed on hardware.** No register was read back, no write was
attempted, no live test was run, and none is possible from this pipeline. The
bit-field finding in particular is a statement about two instructions in a
committed image and about nothing else.

**`0x07D3`'s EC side is not this file's.** It is issue #183's
(`ec/annotations/ec-07c4-07d5-sites.md`). The two share an address and a
firmware; they do not share a program.

**The nine walks are what the method found, not a census of the walks that
exist.** `0x8D41` `advance_07d2_counter_and_dispatch` is a tenth: it writes `R7`
to `0x07D2`, clears it, writes `0xFF` back, then calls `0x35FF` — which reloads
`0x07D2` and reads it — and `inc dptr` into `0x07D3`, where it reads that byte and
tests its top bit. The committed listing shows all of it; the site table does not
record it as a walk, because the window for `0x8D41` stops three instructions in,
on the `lcall` right after the store. A linear walk that stops at the first
branch does not reach it, which is the same limitation as §4c below and in a
specific instance rather than in the abstract.

**47 is a lower bound**, for the computed-`DPTR` reason in `docs/findings.md`
§4c: `trace_xdata_refs.py` finds direct `MOV DPTR,#imm16` sites only, so a byte
reached through a register-held address or a pointer table is not in that
number, and would have read as "not found by this method" rather than "absent"
had there been none. It is also not a count of distinct logic: five sites hand
DPTR to shared accessors and nine walk into `0x07D3`.

## Two things the walk did *not* narrow, and why no retraction follows

**`docs/findings.md` §3d is untouched, and does not need a correction.** It
claims the PD firmware holds `0x07D0`/`0x07D1` as adjacent halves of
overlapping 16-bit windows while the DSDT field list declares them two
independent 8-bit fields with `0x07D2` unnamed, and calls the DSDT's
`DBD1`/`DBD2` pair "a pair of the DSDT's own making". This walk supports all of
it and sharpens the last clause: `0x07D2` is not merely unnamed, it is outside
the list, and `0x07D2`/`0x07D3` is a second 16-bit window running the other way.
Nothing §3d asserts is falsified, and correcting it in place would be editing a
correct conclusion rather than withdrawing a wrong one.

**`ec/annotations/ec-0x07d1-sites.md` §4.3 is untouched, and does not need a
correction either.** §4.3 declined to choose between a 3-byte counter, a packed
field and a moved 16-bit value, and said the single-byte class could not
distinguish them. It was right about its own evidence, and this walk confirms
the reason rather than dissolving it: the address is a low byte in one routine
and an index in another, so the table is what separates them. What would
overturn §4.3 is the call graph, not another site enumeration.

Both files are therefore exactly as they were, and the retraction style in
`docs/findings.md` §4a-4d is not invoked anywhere in this change.

## Open

- **What the `0x07D0`-`0x07D3` field is**, and why one routine reads `0x07D2` as
  a high byte while another multiplies it alone. `#26` and `#67`.
- **Whether the field `0x8B70`/`0x8B81` sets has any DSDT counterpart
  at all.** It straddles a boundary the ASL draws one byte earlier, which
  suggests there may be nothing to collide with. Only a live observation would
  settle it, and none is reachable from here.
- **Whether the EC firmware reads `0x07D2` at all.** The EC image references it
  zero times by this method, which is the §4c signal and not a verdict.