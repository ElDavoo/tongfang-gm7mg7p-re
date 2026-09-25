# The shape census at the top of `subsystems.md` §2 is held to a recount (issue #630)

The write-up for [issue #630](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/630),
which is about a paragraph of prose in `ec/annotations/subsystems.md` that
states a census of its own that no gate could go red over. What this branch
adds is the gate: `build_ec_decompile.py --check` now derives that census from
`ec/annotations/ghidra-functions.csv` and fails when the document's figures
disagree, and the paragraph's inline list of prefixes has become a table whose
rows are the vocabulary the figure is derived over.

**Nothing here was observed on hardware.** No register was read, written or
read back, and no behaviour was exercised. The recount is over a committed CSV
and the proof is the two modes' output. §2's own "Nothing here was observed on
hardware" is not weakened by any of this; the new text sits under it.

`docs/findings.md` §19 carries the one-paragraph summary.

---

## The census as it stands on this tree

Recounted over the committed `ec/annotations/ghidra-functions.csv`, 1,914 rows,
counting `name.startswith(prefix)` on the whole prefix:

| prefix | rows | of which |
|---|---|---|
| `call_` | 88 | |
| `load_` | 120 | 83 `load_dptr_`, 37 register and table |
| `trampoline_` | 29 | |
| `ret_` | 27 | 19 `ret_only_`, 8 named beside them |
| `nop_` | 9 | |
| `seed_` | 6 | |
| **total** | **279** | |

`thunk_` is 0, `type: unresolved` is 160, and those are the numbers §2's live
paragraph now states. **The prose was already right when this branch started**;
what was missing was anything that would say so again tomorrow.

### Why the figure is 279 and not 271, which is not a disagreement

Both numbers are in the document and both are arithmetically right about
different readings. The 271 is the same six prefixes with the `ret_` row read as
its 19 `ret_only_` members; the 279 is the same six prefixes with `ret_` read
whole, which adds the eight `ret_stub` (two rows), `ret_immediately`,
`ret_no_op`, `ret_stub_no_request_bit`, `ret_terminating_89f4` and two
`ret_stub_table_f041_row..`. §2's blockquote already says exactly this and
explains why: the six-prefix-plus-`ret_only_` reading gives 271, reading the
half whole gives 279. **The table's `ret_` row is 27 for that reason**, and a
reader who lands on the blockquote's 271 first deserves to know the two are one
measurement taken two ways rather than one of them being stale.

The eight rows are seven names: `ret_stub` is carried by two. The blockquote's
enumeration of them at :215-216 lists the other six, so it reads as eight over
seven. The retraction is left as written — a correction is not edited into the
thing it corrects — and the derived `of which` column states the eight
correctly.

### The issue's own recount is a tranche behind the tree

Issue #630 quotes a recount of 1,872 rows, 169 unresolved and 269 names. Those
are the #602-era figures, and they are what §2's blockquote says; the tree is
one tranche ahead, at 1,914 / 160 / 279. **The live paragraph must not be
corrected back to the issue's numbers**, and a reader who diffs the two will
otherwise spend time on a discrepancy that is only a merge order.

## The vocabulary, which is the substantive half of the issue

The issue offers a choice: commit the prefix list as a vocabulary the check
derives from, or scope the number to the prefixes the prose enumerates. It is
the first, and the thing that settles it is a structural one rather than a
stylistic one.

The paragraph's real fault was that `forward_to_*` is a shape-census item — the
blockquote at :225 says so outright — while the headline number read as a
total over shape names. **The list was illustrative and the number read as
total, and prose cannot carry that distinction**, because "the seven prefixes
above" is a phrase rather than a set. A table carries it by construction: the
rows *are* the scope, the total is the sum of the rows, and a family that is
not a row is visibly outside rather than quietly uncounted. That is also what
"a stated count, a derived count, and a failure when they disagree" needs — a
committed vocabulary to derive against, or the derivation is circular.

So `SUBSYSTEM_SHAPE_PREFIXES` in `ec/tools/build_ec_decompile.py` carries the
six, and the table in §2 is a view of it rather than its source.

### What the check refuses

Five faults, all of them the kind a prose paragraph accumulates silently:

- a prefix in the vocabulary with **no row** — the dropped-row fault, which the
  total cannot see, because the remaining rows still add to it. The `seed_` row
  deleted from a correct table leaves the document's own total correct;
- a row for a prefix **not** in the vocabulary, reported rather than raised,
  on this file's rule that a broken input is a failed check and not a traceback.
  `load_dptr_` is the case the rule exists for: it is a `of which` breakdown,
  not a seventh row;
- a row whose **tally** disagrees with the recount;
- a `of which` breakdown that disagrees with the **recount** or with its **own
  parent row** — two separate faults, because they can only be made separately;
- a `**total**` that is not the recount over the six.

`thunk_` is deliberately **not** in the vocabulary, and the check does not ask
for a row for it. A prefix nothing carries is a prefix #602 renamed away, not a
row that went missing, and a gate that reported it would be reporting a
correction as damage.

## The live-line rule, and why it is not a deletion

`subsystems_stated_counts` collects **every** occurrence of a label on purpose:
the document states its four counts twice, and keying on the label alone would
leave the earlier copy unchecked. That is the right rule, and extending it to
the shape census naively would have pinned the retracted figures in §2's
blockquote and turned #602's own correction red — the one thing a correction is
not.

So all three census readers skip a line whose left-stripped form opens with `>`.
The rule is one helper, `is_blockquote_line()`, and it is applied to the two
existing readers as well as the new one: **a rule that lives in one reader is a
rule the other reader will trip over**, and §2 already states its census three
ways — four bullets, a per-program table and now the shape table — so a future
correction can put a copy of any of them beside itself.

**This is a reading rule, not a deletion.** The blockquote is left exactly as
written, in place, and a reader still sees what the document used to say. What
changes is only which lines the check compares — and the committed tree is
unaffected by the rule today, which is asserted rather than assumed: §2's eight
census bullets are all live lines, and the `--self-test` case says so by name so
a correction moving one of them into a blockquote goes red instead of quietly
halving what the four-count check compares.

A `>` that opens a block whose continuation lines carry no marker of their own
would not be caught. This document's own blockquotes prefix every line, and the
helper's docstring says what the limit is rather than implying coverage it does
not have.

## The `#629` boundary, and why the table is written not to depend on it

Issue #629 is open and owns the `forward_to_` / `forwarder_to_` spelling: 17
rows and 9 rows respectively on this tree. **Nothing here re-derives that
spelling**, and the table carries no forwarder row, so the forwarder family is
outside the six by construction. §2 says so in one clause and points at the
blockquote for the count, which stays a scoped prose statement rather than a
derived one.

The consequence is the useful part: **#629 renaming those rows cannot turn this
gate red**, because the gate never counted them. If #629 lands first and settles
the spelling, adding the family is a seventh entry in
`SUBSYSTEM_SHAPE_PREFIXES` and a row in the table — one line each, deliberately
not this change's job.

## What was checked, and what was not

- `--check` prints the derived census and exits 0 on the committed tree.
- `--self-test` covers the matching table **and** the corrected-beside-retracted
  one, with the blockquote case asserting both that the live table passes and
  that a number edited *inside* the blockquote is not read. A guard exercised
  only on known-bad input cannot distinguish "clean" from "never ran", which is
  why the matching case is first in the block as it is in the rest of the file.
- Every fault above is exercised by a fixture, each on the good document with
  exactly one thing wrong, so a failure names the guard that stopped rejecting.
- Adding a row to `ghidra-functions.csv` that moves a prefix tally turns the
  gate red. That is shown on a synthetic row set inside the fixture rather than
  by committing a row, so the CSV is unchanged: `git diff --stat` on it is empty.

**Not established here.** Whether a name over one of these six prefixes is the
*right* name is untouched by any of this — the census counts what the names
say, and §2's point is that a shape name is not a mechanism. Nothing here reads
a byte of the firmware, and nothing here bears on §4's separate 290/282/94 BL51
census, which is a different measurement in a different section and is
explicitly marked as not held to a recount.
