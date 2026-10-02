# Eight of the ten `0x0400`-`0x0457` census gaps are closed by two tools, and the two that are not fail for two different reasons

(2026-10-02, issue #429. Static reading of the committed decompiled tree and the
committed firmware. No capture was opened, no register was read back, no EC,
hardware or Windows machine was involved, no Ghidra export was run, no
`static_refs*` count moved, and no `status:` moved.)

#429 was opened automatically from #217 and asks for two things: a per-address
account of why ten addresses in the `0x0400`-`0x0457` page have main-EC byte
sites and no reference the decompiled tree can show, and a decision on whether
the census needs a category for the shape. Both are answerable from the tree as
it stands, and neither needs new evidence — which is the first thing worth
saying, because the issue's own first premise no longer holds.

**The premise is stale.** #429 reads "All ten are confirmed absent from
`ec/annotations/xdata-registers.csv`". Eight of the ten have a census row.
`xdata_register_map.py`'s `NOT_IN_TREE` carries the reason in its own comments:
issue #279 gave the pair pass a `movx` discriminator, eight of the entries
stopped being true, and the eight that stopped are the eight that arrived. What
"absent" would have meant here, and does not, is *not found by this method* —
`xdata_register_map.py` prints that gloss on every `--reconcile` run, and
`registers.yaml` carries it in the header. Nothing in this write-up should be
read as a claim that a byte is gone.

The second half of the issue's premise is also worth correcting once: it groups
nine addresses as "seed-to-helper", and `0x0420` is not one of them. §3 gives
the listing.

## 1. The position, measured

`--reconcile` joins the two censuses — `xdata_register_map.py`'s C-level one
against `register_ref_table.py`'s image-level one — and prints the main-EC row
for every address in `registers.yaml`:

```console
$ python3 ec/tools/xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800 2>&1 >/dev/null
217 addresses: 62 agree on the main-EC count, 12 have main-EC sites the decompiled tree does not contain, 143 differ another way. A zero in the 'this tool' column is 'not found by this method' -- a function that did not decompile carries its references nowhere -- never 'absent'.
```

The ten rows that issue is about:

| address | `registers.yaml` name | census, main EC | census, PD | image, main EC | image, PD | in the decompiled tree |
|---|---|---:|---:|---:|---:|---|
| `0x0402` | `BAT_DESIGN_CAPACITY` | 10 | 0 | 3 | 0 | differs |
| `0x0404` | `BAT_FULL_CAPACITY_1` | 13 | 0 | 11 | 3 | differs |
| `0x0408` | `BAT_DESIGN_VOLTAGE_1` | 3 | 0 | 2 | 7 | differs |
| `0x040A` | `XDATA_040A` | 3 | 0 | 3 | 0 | agrees |
| `0x040C` | `XDATA_040C` | 2 | 0 | 2 | 2 | agrees |
| `0x040E` | `XDATA_040E` | 2 | 0 | 2 | 0 | agrees |
| `0x0410` | `XDATA_0410` | 1 | 0 | 1 | 5 | agrees |
| `0x0420` | `XDATA_0420` | 0 | 0 | 1 | 11 | **not in the decompiled tree** |
| `0x043A` | `XDATA_043A` | 6 | 0 | 3 | 3 | differs |
| `0x0457` | `XDATA_0457` | 0 | 0 | 4 | 1 | **not in the decompiled tree** |

Every zero in the two `census` columns means *not found by this method*, and the
census and the image are not counting the same thing even where both are
non-zero: the census counts C-level occurrences, the image counts
`MOV DPTR,#imm16` sites, and `xdata-register-map.md` §6 is the section that
keeps the two languages apart. `0x0402`'s census figure against an image figure
of 3 is the §4.7 overlapping-export case, not a contradiction.

So the partition is **eight plus two**: the eight are the members of §7's
"other ten" that the census now carries, and the two it does not are not there
for the same reason. The rest of this write-up is that difference.

## 2. Which artifact carries which address

Two committed CSVs now hold facts about the same ten addresses from two
instruments, and nothing in the tree said which was which. That is the second
of #429's two asks, and the per-address reasons the issue was told already
existed had never been laid out as a map from address to artifact.

| address | which artifact carries it | which method cannot see it, and why |
|---|---|---|
| `0x0402` | `xdata-registers.csv` `spelled_as=pair-literal`, `pair_role=seed`; 3 EC-side rows in `site-resolution.csv` | nothing since #279, whose pass reaches these by resolving the literal first argument through the callee's own `movx`; before that the decompiled text spelled the seed as the invented function name `FUN_CODE_0402`, which matches neither half of the census's occurrence pattern |
| `0x0404` | same, 11 EC-side rows (one of them a direct `read` where the site sits) | same |
| `0x0408` | same, 2 EC-side rows, both writes | same |
| `0x040A` | same, 3 EC-side rows | same |
| `0x040C` | same, 2 EC-side rows | same |
| `0x040E` | same, 2 EC-side rows | same |
| `0x0410` | same, 1 EC-side row | same |
| `0x043A` | same, 3 EC-side rows, all reads | same |
| `0x0420` | `site-resolution.csv` only — 1 row, `resolution=unresolved-none`; no census row at all | twice, once per program: the main EC's `E769.c` drops the store entirely and so spells the address nowhere, and the PD image's `.c` spells it as a bare hex literal argument to a callee that is not a consecutive-pair accessor, which `pair_accessor()` does not select (§3) |
| `0x0457` | `site-resolution.csv` only — 4 rows, `resolution=read+write`, `function=not exported` | the census: no exported function covers the routine the four sites sit in, and the one committed `.c` that names the address does so in a comment the census strips (§4) |

All ten also carry a dated per-address reason in their `registers.yaml` note —
`*** 2026-09-25 (issue #279) ***` and `*** 2026-09-28 (issue #1105) ***` blocks
naming the sites and the callee each one resolves to. The full per-site
resolution is [`handoff-site-warrant.md`](handoff-site-warrant.md), and the
per-site table is `ec/annotations/site-resolution.csv`.

**One gap on this page is *not* accounted for here, and it is a different
one.** The census's PD column is zero for all ten while the image census finds
PD-image sites for seven of them — the "seven of the ten also have PD-image
sites" §7 records. The PD program has its own XDATA map, and a direction for
its bytes is a different question from a direction for the EC's, which is why
`check_site_resolution.py` filters those sites out rather than classifying them;
but the census counting zero there is not explained by that filter, and this
write-up does not re-derive why. Recorded as an open question, not resolved.

**The boundary between the two instruments, stated once.** A `MOV DPTR,#addr`
that is followed by an `lcall` to a two-byte pair accessor is a *seed*: the
`movx` is in the callee, the address is an argument, and the decompiler's C
carries the callee's name rather than the address. That is why the image census
sees a site and the C-level census once saw nothing, and it is why
`xdata-registers.csv` records the address as a `pair-literal` row with
`pair_role=seed` — the row exists because a *C-level* occurrence was resolved,
and the column says which half of the pair the address is. An image site count
is not a `refs` cell and does not belong in that CSV; the site counts live in
`site-resolution.csv` and in `register_ref_table.py`, which is the instrument
that produces them.

## 3. `0x0420` is a third mechanism, and the issue has no box for it

`ec/decompiled/bank1/E769.asm` is the whole routine — 24 bytes, exported,
`clamp_r2r1_to_0420_above_3c0b`. Verbatim from the listing:

```
E769     ea - -   mov      A, R2
E76A     70 06 -  jnz      0xe772
E76C     e9 - -   mov      A, R1
E76D     c3 - -   clr      CY
E76E     94 3c -  subb     A, #0x3c
E770     40 07 -  jc       0xe779
E772     ea - -   mov      A, R2
E773     c3 - -   clr      CY
E774     94 0b -  subb     A, #0x0b
E776     50 01 -  jnc      0xe779
E778     22 - -   ret
E779     90 04 20 mov      DPTR, #0x420
E77C     aa 83 -  mov      R2, DPH
E77E     a9 82 -  mov      R1, DPL
E780     22 - -   ret
```

The routine tests `R2:R1` against `0x3C0B` a byte at a time — `subb a,#0x3c`
with `R2` zero, `subb a,#0x0b` otherwise — and one of the three exits loads the
address into DPTR, copies DPTR into `R1:R2`, and returns. **There is no
`lcall` anywhere in it.** So the address is *offered* to a caller in the very
register pair `read_xdata_pair_to_r1r2` fills with the byte's *value*; nothing
at the site loads or stores through it, and the two are not interchangeable.

Two consequences, and they are the reason the issue's grouping is wrong rather
than merely incomplete:

- It is not a seed-to-helper site, so a category for seeds would not reach it
  even if the category existed. The census misses it twice over, and neither
  miss is about the site. **Main EC:** `ec/decompiled/bank1/E769.c` does not
  spell `0x0420` anywhere — its own header comment says the decompile "drops
  the store-back entirely and returns a char the listing never produces", so
  there is no token for the census's occurrence pattern to match. **PD image:**
  the address is spelled as a bare hex literal argument to
  `add_full_product_to_dptr` in `ec/decompiled/pd/34A5.c`, and that callee is a
  record helper rather than a consecutive-pair accessor, so `pair_accessor()`
  does not select it. `xdata_register_map.py`'s `NOT_IN_TREE` entry for
  `0x0420` says the second of those in its own words.
- **The direction is a limit of an instrument, not a fact about the byte.**
  `check_site_resolution.py`'s `resolve_handoff()` models a DPTR passed to a
  call; this one passes it across a `ret`, so the site records as
  `unresolved-none` — "no `movx` in the decoded window", which is evidence of
  nothing in either direction. `check_status_vocabulary.py` refuses rule 3 for
  `XDATA_0420` and holds it by a named exemption whose own text says the
  exemption is deleted when the direction is established. **#1103 owns the
  `R1:R2` propagation.** This change records the misfiling and closes nothing
  there; the status stays `present-untested` and the exemption is untouched.

## 4. `0x0457` is a listing gap, and `bank-call-audit.md` is the wrong home for it

Four EC-side sites, all in bank1, all read-modify-writes, at `0x8190`,
`0x81D1`, `0x8246` and `0x826A`. Reading them out of
`ec/decompiled/listing-index.csv` against the committed function boundaries:

| site | falls between |
|---|---|
| `0x8190`, `0x81D1` | `0x80EF` `dec_timers_and_set_expiry_flags` / `0x8202` `clear_0801_bit5_then_call_19a2_84` |
| `0x8246`, `0x826A` | `0x820F` `with_r7_results_into_carry` / `0x8300` `clear_and_set_xdata_flag_bits` |

No exported function covers any of the four. That is the census's reason, and it
is a stronger one than it looks: the census reads *every* `.c` in the tree, the
overlapping exports included, so an address reachable through a neighbour's
decompile would have been counted. Exactly one committed `.c` names `0x0457`,
`ec/decompiled/bank1/8418.c`, and it does so inside a block comment;
`xdata_register_map.py`'s `strip_comments()` blanks those, so the census's zero
is a measurement rather than a miss.

An exported routine reaches the same byte by a route the census cannot take,
recorded at `ec/annotations/xdata-0400-045f.md` §5: `bank1/8418.c`'s
`code_table_scatter_to_xdata` walks three-byte CODE records at `0x851C`, a
big-endian destination followed by a value per iteration, and one of those
records' destination bytes are `0x0457`. DPTR there is built from the record
rather than seeded by a literal, which is a different instrument's subject
(`computed_dptr_sites.py`), and it is why the four rows above are the only ones
in `site-resolution.csv`. The site census classifies all four as `read+write` —
it walks the bytes rather than reading a name — which is why
`site-resolution.csv` has the rows and `xdata-registers.csv` does not.

**What would cover it** is seeding the routine and running
`--mode rebuild-project`. That writes the committed Ghidra database, and
`.gitattributes` makes git refuse to merge a `.gpr`/`.rep` change rather than
text-merge it, so two branches that both rebuild cannot merge. The gap and what
would close it are recorded; the closing is a human's. `0x0457` stays
`present-untested`.

**Why not `ec/annotations/bank-call-audit.md`.** The issue points there, and the
file is the right *kind* of record — calls naming an address no program exports
— but its subject is call *targets*, and nothing calls these. The four are
read-modify-writes reached by no `lcall` at all, so a row in that table would be
a row about a shape the table does not describe. The argument belongs with the
per-address record, which is here and in the address's own note.

## 5. The category decision, and the third place this declines

#279 already made the decision, and made it in code rather than in prose:
`xdata-registers.csv`'s `spelled_as=pair-literal` and `pair_role=seed` are the
category, and `xdata_register_map.py --self-test` holds the `NOT_IN_TREE` set
to the census's own gap in both directions — nothing in the census without a
recorded reason, and nothing with a reason the census has reached. The issue
asks whether to add one; the answer is that it would be a third place, and here
is why that is worse than not adding it.

- **A DPTR-seed bucket in `xdata-registers.csv` would duplicate
  `site-resolution.csv`.** The latter already carries a row per site with its
  `depth1_class`, its `callee` and the `callee_function` that gives it a
  direction. A census-level bucket would be the same fact at a coarser
  resolution, in a file whose `refs` column is *not* an image site count.
- **It would make `refs` mean two things.** That column counts C-level
  occurrences in the decompiled text, and other tools sum it. An `.asm`-derived
  bucket filling the same row would leave the reader unable to say whether a
  cell is text or bytes. `xdata-register-map.md` §6 and
  `check_site_census.py`'s vocabulary table exist to keep the census's
  language and the image census's language apart. Merging their numbers would
  undo that arrangement rather than extend it.
- **A `dptr-seed` row in `check_site_census.py`'s vocabulary table** would be
  the same decision in a third file, in a tool whose subject is a different
  shape (§6). It is declined here and named, rather than left for the next
  reader to mistake for an omission.

The issue's own expectation — that a `.asm`-derived bucket "closes all nine at
once" — would in fact close eight. The ninth is not that shape, and §3 is the
argument.

## 6. Not #399, and the inversion is the whole difference

#399 asks for a `dptr-carried` category in `trace_xdata_refs.py` and
`check_site_census.py`, for a seed whose `movx` is in the **caller**. This is
the inverse: the seed and the call are in the same site, and the `movx` is in
the **callee**.

| | this shape | #399's | the rebuilt-DPTR shape |
|---|---|---|---|
| where the `movx` is | the callee, one `lcall` past the seed | the caller, past the `lcall` | the same listing, after a pointer rebuild |
| instruments | `xdata_register_map.py` (census), `register_ref_table.py` (`--callee-depth 1`), `check_site_resolution.py` (per-site) | `trace_xdata_refs.py`, `check_site_census.py` | `dptr_rebuild_forms.py`, `computed_dptr_sites.py` |
| committed record | `xdata-registers.csv`'s `pair_role`, `site-resolution.csv` | not yet implemented | `computed-dptr-sites.csv` |

The third column is there because both of the others are easy to confuse
with it:
[`dptr-rebuild-walk-guard.md`](dptr-rebuild-walk-guard.md) §7 already holds the
rebuilt-DPTR shape distinct from #399's, and neither is this one. None of the
three subsumes another. #399 is not implemented by this change.

## 7. What this does not establish

- **Every verdict here is static.** A `write` is an instruction that stores to
  an address, not evidence that the EC reads the value back or acts on it. No
  register was read back, no capture opened, no EC or HID node touched.
- **A `read` or `write` in either CSV is a claim about the machine code, not a
  behaviour.** `registers.yaml`'s gloss on `present-untested` — "static-scan
  finds real references, not yet exercised live" — is unchanged by anything here.
- **No `status:` moved, and no `static_refs*` moved.** `check_register_counts.py`
  still reproduces every one of them from the image. The census figures in §1
  are the tool's, and the two instruments' units differ; neither is a behavioural
  result.
- **A zero is "not found by this method", never "absent".** This is the
  `registers.yaml` header's own caveat and the reason the two addresses in §1's
  "not in the decompiled tree" column are described as gaps in coverage rather
  than as findings about the bytes. `docs/findings.md` §4c's `0x07B9` is the
  standing counter-example: writable, working, no direct site anywhere.
- **Two independent methods agreeing is not twice the evidence.** For the eight,
  the census and the image reach the same direction by different routes; that is
  worth saying and is still one static claim.
- **`0x0420`'s direction is unknown and stays unknown.** Nothing here settles
  it, and no static instrument in the tree can while the propagation is across a
  `ret`.

## 8. Reproducing it

All of it from the repository root, committed inputs only — no image beyond the
committed dump, no Ghidra, no network, no capture, no hardware, no Windows.

```console
$ python3 ec/tools/xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800
$ python3 ec/tools/xdata_register_map.py --check
$ python3 ec/tools/xdata_register_map.py --self-test
$ python3 ec/tools/check_site_resolution.py --check
$ python3 ec/tools/test_dptr_seed_census_gap.py
```

The per-site table behind §2 and §3 is
`ec/annotations/site-resolution.csv`; the four helpers' own bodies are
`ec/decompiled/bank1/8886.asm` and its three siblings at `888C`, `8892` and
`889E`; the `0x0420` listing is `ec/decompiled/bank1/E769.asm`, quoted whole
in §3.

The suite was checked the way this repository checks a new one: on a scratch
copy of the tree, with one artifact doctored at a time, and each group red
before it was called a check — a census row dropped, a `pair_role` flipped, a
census row *added* to `0x0420`, `0x0457`'s site rows removed, a dated marker
stripped from a note, an accessor renamed in one CSV and not the other, an
absence word put into a `NOT_IN_TREE` reason, that reason's anchor removed, the
entry itself removed, a `read+write` site rewritten as `unresolved`, a callee
added to `0x0420`, the §7 correction deleted, the finding unindexed, and the
#399 inversion taken out. A check nobody has seen reject anything looks exactly
like a check that is working.
