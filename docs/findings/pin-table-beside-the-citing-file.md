# The beside-the-citing-file reading, in the tool that had only the tree's (issue #952)

**Nothing here is a hardware claim, and nothing here is a firmware claim.** No
image is opened, no register is read back, no capture is taken, and no laptop, EC
or Windows machine is involved anywhere below. Every figure is a count of lines
in files in this repository, and the one command that produces them is in it.
Same framing as [`pin-table-by-cited-file.md`](pin-table-by-cited-file.md) and
[`test-line-pin-census.md`](test-line-pin-census.md): a census of text about
text.

**The finding is a reading that one of the two readers had and the other did
not.** [`check_pin_table_by_cited_file.py`](../../ec/tools/check_pin_table_by_cited_file.py)
reads a *declined* record's spelling for a target itself — the fence rule
declines before resolution runs, so a declined record arrives here with no path
to charge — and until this issue it had two readings of a path spelling: the one
the tree satisfies, and the named bucket where the tree satisfies nothing. The
census it is a second axis on has three, and the middle one was missing here.

**This is not a rewrite of the census, and it is not issue #940.** The census
already does this reading; `census.resolve()` is untouched and its own suite is
green and unmodified. What was added is the same reading, in the same order, on
the other side of the fence.

## The two readings, side by side

`place()` decides a declined record's target. It has four outcomes, and before
this issue it had three:

| # | the spelling names a path… | read to | verb |
|---|---|---|---|
| 1 | …that **the tree** has, after `normpath` | that file | `by-path` |
| 2 | …that **the file beside the citing one** has | that file | `beside-the-citing-file` |
| 3 | …a **bare module name** the index answers | the index's one file, or `ambiguous-path` | `by-name` |
| — | …none of the three | a **named** `unresolved-path` / `ambiguous-path` bucket | never guessed |

Rows 1, 2 and 3 are read in that order, and the order is the point rather than an
implementation detail: **the tree wins over the beside candidate.** A page that
wrote a path the tree has meant that one, and the beside reading exists for the
page that wrote a path the tree does not have. A retried candidate that had gone
first would be a preference between two files that both exist, and the census's
own suite holds the property in its *the tree wins when both readings would
resolve* case. `place()` holds it now for the same reason, in a case of its own.

**The census's argument for row 2 is its own, and it is the argument this change
adopts rather than one invented beside it.**
[`census_test_line_pins.py`](../../ec/tools/census_test_line_pins.py)'s
`resolve()`, in the numbered second step of its own docstring, says:

> 2. a path that is not in the tree is retried **beside the citing file**,
>    because `ec/annotations/xdata-register-map.md` writes `../tools/…`
>    and `../../docs/findings/…` for its own neighbours and means them. This
>    is a second reading, not a choice between two files that both exist:
>    step 1 already took the tree's answer whenever there was one.

and the same tool's module docstring says it a second time, in *What the reader
accepts as a pin*: a path is read against the tree first and, if the tree does
not have it, **beside the citing file**, because
`ec/annotations/xdata-register-map.md` writes `../tools/…` for its own neighbour,
"and reading that against the tree reports a sound pin as a missing one". A page
that writes a neighbour's path relative to itself has written a path that means
one thing and is spelled as another, and a reader that stops at the tree has read
it as a file the repository does not have.

**So the two readings disagree on exactly one shape: a fenced `../`-relative
spelling.** The census declines it, this tool charged it to
`unresolved-path` and reported a file that is in the tree, and it did so with a
hint naming the right file — the hint was doing the work the branch should have
done. The census's `resolve()` on the identical spelling returns
`(resolves, ec/tools/test_a.py, beside-the-citing-file)`.

## The measured zero, and what it is not

Replayed on the committed tree by hand, the branch is reached by **nothing**:

| figure | measured |
|---|---|
| records / declined | 132 records, 33 declined |
| declined records reaching the by-path branch | 33 of 33 |
| records a beside retry would charge | **0** |
| named buckets | `0 unresolved-path, 0 ambiguous-path` |

**That zero is a fact about today's 33 declined records, not a measurement that
the branch is right.** It is *not found by this method* in exactly the sense
`ec/annotations/registers.yaml` uses for a static scan, and it is stated that way
because the number is genuinely flattering and genuinely weak: it says no
declined record happens to have this spelling today, which is a fact about the
corpus and not about the code. The evidence for the branch is therefore the three
cases, and **the absence of a red is not part of the argument** — a branch that
is dead and a branch that is right are the same zero here, and only the cases
tell them apart.

The same zero is why nothing on the committed tree's figures moves. Same fifteen
rows, the same 43 of 132 and 83 of 132, the same two empty buckets, the same 132
records the census's own suite holds; and the concentration is a count of *files*
and a count of *occurrences*, and no declined record changed which file a record
is charged to, because none had a beside candidate to be charged to. Nothing here
is a denominator that a reader has to be told about.

## The two live `../tools/…` pins, and why they do not exercise it

[`ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md)
is the page the census cites as the reason the reading exists, and it is live on
this tree: it writes `../tools/test_xdata_cluster_names.py` for its own
neighbour in two places — in the *Two identities, because a rank is not one*
section (§4.4) and in *What follows* (§8). Both are the two records the census
resolves by the beside reading, and both are why the tool's
`ec/tools/test_xdata_cluster_names.py` row is 33 rather than 31: without this
reading the census would resolve 31 of them.

**They do not exercise the branch here, and the reason is worth stating rather
than leaving as a coincidence.** They are in live prose, so the census reads them
and they are not declined; the branch belongs to declined records, and no fenced
transcript of either sentence exists on the tree today. The first fenced
transcript of either — a `grep` run whose output quotes one of them, or any
write-up quoting one inside a fence — is what exercises it, and before this issue
it would have been reported as a file not in the tree.

The census write-up's per-pin table already records both rows as read by the
beside reading, which is the visible sign of the reading having been live all
along. A third tool,
[`check_pin_table_rows.py`](../../ec/tools/check_pin_table_rows.py), reconciles
that table's read-kind column against `census()`'s own run; it is a reader of
the **census** rather than of this tool, and the census is untouched, so this
change moves nothing it holds. Its committed-tree cases are red on the tree this
was written on, and were red on it before this change for reasons in files
neither this issue nor that tool's readers touch; the same is true of five other
suites, so **a red `run-tests.sh` on this tree is not evidence about this
change** and the check that is — the census's own 41 cases and the 30 here, both
green — is named rather than left to be inferred from an exit code.

## Why this is a reading and not a repair

A repair is a different act from a reading, and the difference is the whole of
what is safe here.

* **No basename fallback, and the beside branch is not one.** It is gated on the
  candidate being *in the tree*, so a spelling naming a file that is somewhere
  else still lands in `unresolved-path` with the file of that name named beside
  it. A fallback to a base name is the guess `ambiguous-path` exists to refuse,
  and `ec/annotations/registers.yaml`'s caveat is the same shape: a negative is
  a statement about a directory walk, never that a citation is missing.
* **The tree wins, and the order is what says so.** The retry sits after the
  `normalised in files` check, and a case holds the ordering rather than leaving
  it to a reader of the source.
* **A placed record stays `declined`.** The census declined it before resolution
  ran; which file it *would* have resolved to is a different fact from what it
  did with it. The same rule the bare-name branch has always followed.
* **The `unresolved-path` message now names both candidates.** A wrong directory
  prefix and a deleted file look identical from a row of this table and have
  opposite fixes, which is why the census's `resolve()` names both candidates in
  its `unresolved-path` message and why the message here was the one losing that
  distinction. Both clauses the message carried before are still
  in it — *not repaired*, and the base-name hint — and two cases hold them.

**No census of the census.** The branch reuses the census's own vocabulary
constant and its own join rather than writing a third reader, and
`census.resolve()` is untouched: two readers that agree today is already one
more agreement than the file had, and a third would be a problem to reconcile
rather than one to add.

## What is left, as follow-ups

1. **The two readers of a path spelling are two readers.** `place()` states the
   guard, the order and the message for itself where `census.resolve()` states
   them for itself, and the beside reading is now written twice. The bare-name
   branch already delegates rather than re-reading, so the asymmetry is visible
   from the file: whether the by-path branch should delegate the same way — and
   the `normpath` with it, which
   [`pin-table-by-cited-file.md`](pin-table-by-cited-file.md)'s follow-up 2
   already asks about — is a question about the *census's* behaviour, and
   [#940](../../docs/MISSION.md) is the issue that owns that file.
2. **The branch has no record exercising it, and that is a property of the
   corpus rather than of the code.** A fenced transcript of either live
   `../tools/…` sentence would be the first one, and it would land in
   `unresolved-path` under the pre-issue reading and in a table row under this
   one. Nothing needs to be written to make that happen; it is recorded so that
   the next fenced transcript of a `../`-relative pin is recognised as the
   measurement the corpus had been missing, and so that its effect on this
   tool's committed table is read as a row moving rather than as a drift.
