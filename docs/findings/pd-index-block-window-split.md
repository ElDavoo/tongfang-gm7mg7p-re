# The `0x260` block, split three ways by the host window before the run is written

Issue #1151 asked for a live run over the PD image's `0x260` record block at
`0x0400`-`0x04A8`. Writing the procedure turned up three things about that
block that the issue's wording did not have, all of them arithmetic over
committed inputs and all of them cheap to check. None of it is a hardware
observation: the run has not happened, and
`docs/hardware-tests/pd-index-geometry-live.md` carries a `Status: not run`
header and no results section.

The three are worth writing down separately from the procedure, because each
one would otherwise be a sentence in it that a reader has no way to re-derive.

## 1. The block the issue names is refused by the capture tool's own guard

`ec_timer_capture.py` refuses `0x0460`-`0x046F` before it opens `/dev/mem`
(issue #94: reading those bytes stalled the fans on a sibling board). That
range sits **inside** `0x0400`-`0x04A8`, so the block spec as filed never
produces a capture. Running the tool's own functions says which of the two
spellings is refused:

```console
$ cd ec/tools
$ python3 -c "import sys; sys.path.insert(0,'.'); import ec_timer_capture as C; \
    a=C.parse_addrs('0x0400-0x04a8'); b=C.parse_addrs('0x0400-0x045f,0x0470-0x04a8'); \
    print(len(a), C.check_addrs(a)); print(len(b), C.check_addrs(b))"
169 refusing the fan page 0x0460-0x046F (issue #94): 0x0460 0x0461 0x0462 ...
153 None
```

So the procedure specifies the **split**, and the split differs from the
requested range by exactly the fan page — which is the relation
`ec/tools/test_pd_index_block_readability.py` holds, in both directions: the
range as written is refused, and the split is the range less exactly those
addresses. Nothing else about the block changes, and no base of the `0x60`
family in that range is lost to the carve-out.

## 2. A record can start inside the window and still run out of it

The host maps `0x0000`-`0x07FF` and `0x0C00`-`0x0FFF` and nothing else
(`docs/hardware-tests/xdata-06c2-06db-sweep.md` §3, from the 2026-09-24
census committed at `evidence/ec-watch/2026-09-24-host-window-page-census.txt`).
The gap between `0x0800` and `0x0BFF` is what makes "readable" a weaker claim
than it looks: a `0x260`-byte record based at `0x0400` starts at `0x0400` and
runs to `0x065F`, which does not leave the window at all, but the same record's
next index starts at `0x0660` and runs to `0x08BF` — and everything from
`0x0800` up is `0xFF`. **Slot 1 is reachable and truncated, not reachable or
not.**

`pd_index_block_readability.py --slots` prints the reachable length beside each
family rather than a yes/no, because a procedure that said "readable" about a
truncated record would be overclaiming in the direction this repository cares
most about. For the `0x60` family, slot 0 leaves between 592 and 608 of its 608
bytes sampleable and slot 1 between 248 and 416, depending on where the base
sits.

**A third cut, and the one a window-only count misses.** 23 of the `0x60`
family's 37 bases have a slot-0 record spanning `0x0460`-`0x046F` — the fan
page from §1, which sits inside this block. So "inside the window" and
"readable by a capture" are not the same question, and a count that asked only
the first would report those 23 records as wholly covered when sixteen bytes of
each were refused before the tool read anything. `sampleable()` in
`pd_index_block_readability.py` is the one place that answers it: inside the
window *and* off the fan page, which is what `ec_timer_capture.check_addrs`
accepts. The `--self-test` entry "what a record counts reachable is exactly
what the capture guard accepts" holds the two against each other address by
address, and `--check` now holds the document's slot table as well as its
readability table, so the figure a reader copies cannot drift back to the
window-only one.

Two consequences the procedure uses. **The record-contents arm can sample two
indices rather than one** — a run that stopped at slot 0 would leave half of
what the window can reach unsampled. And **no slot-2 record starts inside the
window at all**, which is the other half of the same boundary.

## 3. The readability split is a property of the host, and the record stride is not

The per-family split is derived, not typed, and it matches the issue's:

```console
$ python3 pd_index_block_readability.py --table
```

It reproduces the issue's own division — the `0x5E`, `0x77` and `0x17` bases
are all inside `0x0800`-`0x0BFF` and none of them can be sampled — from the
committed base list and the window constant, so a re-run that moves a base
moves the table.

The scope of that table is worth stating plainly, because it is narrower than
"which of the widened base set is readable". A base is readable at slot 0 when
its **first byte** is sampleable, which needs no record stride at all. No
committed base sits on the fan page, so on this data that is the same set the
window alone gives; the difference is in the definition, not the table. The
`0x260` arithmetic is a claim about the `0x60` and `0x1F` families only, and
`pd-index-geometry.md` §7.4 is why: not one site with a `0x5E`, `0x77`, `0x17`,
`0x67` or `0x04` stride applies a `0x200 ×` page term, so for those families
`0x260` is arithmetic and not layout. `pd_index_block_readability.py` holds
that scope by deriving the paged families from the census's own
`sites_with_page_term` column rather than from a list in this paragraph, so a
future re-run that gives one of the others a page term turns the tool red
instead of quietly extending the slot table.

**What this is not.** Every figure here is over committed files — a CSV of
bases, a window constant, the fan page — and none of it says what the EC or
the PD image holds at any address. A page that reads `0xFF` is *consistent
with* the window not mapping it; the census is one read-only pass, not a proof
about the host's memory controller.

## What this opens

- **The Windows arm is not covered.** `windows/tools/ec_watch.py` over the
  same block with the Control Center started and stopped is a separate run on
  a machine this pipeline cannot reach either, and the host window it reads
  through is not this one. It is named in the procedure as an arm the
  procedure does not cover, not as work it defers.
- **The index registers are not answerable this way, and that is now written
  down before the run rather than after it.** A memory read observes state; it
  does not observe a register at the moment a site runs.
  `pd-index-geometry.md` §5 states no record count for that reason and its §4
  bounds no index range. A trace or a debugger would settle it and no tool in
  this tree drives either.
- **The separation question is one-sided**, and both directions are written
  down in the procedure's "what this cannot conclude" before anyone runs it: a
  quiet `0x04A6` is *consistent with* separate maps and proves nothing, while
  a `0x04A6` that moves across a renegotiation does prove overlap.
  `grade_pd_index_block.py` prints that asymmetry per run rather than leaving
  a table reader to supply it.
- **`0x08xx` stays a gap, not a zero.** Those bases are unreadable through
  this window on this machine, and per `docs/findings.md` §4e the vendor's
  `ECRW` path goes through the same window, so a different read path is
  unlikely to help. If one is found, the procedure says to record how it was
  obtained.