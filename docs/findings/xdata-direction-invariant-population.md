# The direction invariant's population is measured, not restated

Issue #1385 found `DIRECTION_INVARIANT["write_like"]` and
`["write_like_addrs"]` interpolated into the corpus-wide direction invariant's
pass line and compared by nothing, so the line stated a population as a
measurement that would read identically had both figures been wrong. The
predicate was `not offenders`.

The pins are gone now — `fb8be6ee` removed `DIRECTION_INVARIANT` with the rest
of the census's hand-kept totals, and `check_pin_message_names.py` with it — so
the defect as filed is no longer reachable. Two things it left behind were, and
this is about those.

## What the census was asserting, and what nothing checked

The direction invariant is the argument that the census's `write` and
`read+write` buckets mean *an assignment follows this address*: it asks of every
occurrence the census buckets that way whether a second pass over the same
committed text finds an `=` that is not `==` after it. That is the claim
`ec/annotations/xdata-register-map.md` §4.3 and the writer-bearing rows of
`ec/annotations/registers.yaml` rest on.

Removing the constant removed the figure nobody compared, and with it the last
thing that *named* the population the invariant covers. What the check printed
became "every occurrence that the census buckets `write` or `read+write`" with
no count on it at all. That is honest — a bare claim, not a false measurement —
but it left the population unpinned in the other direction too: the address
width, which nothing in the tree derived, and the reconciliation between the
two passes, which nothing stated.

Meanwhile three prose sites still carried the old figure. `fb8be6ee` deleted
the constant that held it, so `xdata-register-map.md` §4.3,
`xdata-register-map.md`'s §4.3 restatement, and `xdata-086x-dispatch.md` each
asserted a number that no check, constant, CSV cell or site row held. The
figure was also two re-pins stale (`docs/findings/xdata-export-ownership-refusal-denominators.md`
records the 5,662 → 5,677 step as issue #263's). That is the calibration
failure the issue was about, one level down: a figure a reader takes for
evidence, with nothing behind it.

## The derivation, and what it costs

`direction_invariant()` already computed `bucket` for every occurrence and used
it only to compare against `assign_after()`. It now also counts the
occurrences the census buckets `write`/`read+write`, collects the addresses they
land on, and sweeps `pair_sites()` for the by-direction pair count — all from
the walk it was already doing, so **no second walk of the tree**. The `accessors`
parameter defaults to `load_pair_accessors()` for the same reason `scan()`'s
does, so a caller holding a subset can pass one.

Measured on the committed tree, from the `--self-test` line itself:

| quantity | value | how |
|---|---:|---|
| write-like occurrences, second pass | 5,677 | `direction_invariant()` |
| write-like distinct addresses | 1,008 | `direction_invariant()` |
| pair sites, by direction | 241 read / 196 write | `pair_sites()` |
| pair *references* (2 bytes a site) | 392 write | × 2 |
| census `write` + `read+write` | 6,069 | the census's own columns |

The identity the check asserts is the last row against the first plus the
write-direction pair references: **5,677 + 392 = 6,069**. It holds because a
resolved pair site is a `write`-bucket entry that deliberately has no `=` for
the second pass to find — its direction is read out of a callee's committed
`.asm`, in another routine — so the two sides balance only once that half is
added back. `spelled_refs[PAIR_SPELLING]` cannot supply it: that column has no
direction split, which is the whole reason the by-direction sweep exists.

**It is a cross-path agreement, not corroboration.** Both sides come from the
same walk and the same classifier, so agreeing is arithmetic. What it buys is
narrower than a second opinion and worth stating plainly: a figure nobody typed
cannot drift away from the pass that measured it. Before this, the population
was a literal in a message; a change to the census or to the pass moved nothing
on that line. Now it moves the line.

## The two address counts differ, and the difference has a cause

The width is a trap for whoever re-derives it. `direction_invariant()` returns
two address sets and they are **not** the same set:

- `shaped` — every address the second pass accepts an assignment on: **1,009**
- the write-like set — every address the census buckets a store on: **1,008**

`len(shaped)` is the figure a reader reaches for and it is one too high.
`assign_after()` drops the `*` test `store_target()` applies, so it accepts
`*`-dereference stores the census excludes for cause. On this tree the
difference is exactly one address, `0x048A`, counted twice — once in each of
`bank1/EF26.c` and `bank1/EF32.c`, both the same store,
`*DAT_EXTMEM_048a = DAT_EXTMEM_048d;`, in the branch that runs when
`DAT_EXTMEM_048b == '0'`. The routine's other branch writes the same byte
through `*(byte *)CONCAT11(DAT_EXTMEM_048b, DAT_EXTMEM_048a)`, and that one is
**not** among the accepted stores: `occurrence_re` finds the address inside the
indexed expression, but `assign_after()` finds no assignment following it,
because the `=` there is the whole statement's left side rather than something
that follows the token. So the two stores of this address that the census
excluded and the second pass accepted are the plain ones, and the indexed form
is invisible to both. The check asserts the difference *is* the dereference
addresses, so the gap names its own cause rather than waiting to be divided by
hand.

## What is not claimed here

No image was opened, no register read back, no capture taken. Every figure
above is re-derivable from the committed `.c` tree by
`python3 ec/tools/xdata_register_map.py --self-test`, and nothing here says what
the EC does with a byte it is written. A `write` bucket entry is a shape the
decompiler's text has, not evidence the firmware acts on the value.

The census figures these derive from move with every seeded routine and every
named register, which is why they are derived per run and asserted as relations
rather than pinned — the same reasoning `fb8be6ee` applied to the totals it
removed, and `CLAUDE.md`'s rule that a test holds a property of the tree and
never a count of it. `ec/tools/test_xdata_direction_invariant_population.py`
perturbs each side in a scratch copy and requires the line to go red; it
asserts no figure.
