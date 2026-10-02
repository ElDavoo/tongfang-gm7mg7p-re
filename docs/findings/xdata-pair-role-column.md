# The `pair_role` column: which half of a pair a census row is (issue #734)

**Issue #734, 2026-10-02.** `xdata_register_map.py`'s pair pass folds each
resolved accessor call into one `pair-literal` row covering `addr` and
`addr + 1` under the same spelling, so the seed/`+1` distinction existed only
inside `pair_sites()`. `ec/tools/inc_dptr_sites.py` (issue #723) took the
distinction out of the tool and into a derived population, and
[`xdata-inc-dptr-only.md`](../../ec/annotations/xdata-inc-dptr-only.md) §1 said
plainly that "`xdata-registers.csv` cannot answer the question". That sentence
was right when it was written and is wrong now: the census carries
**`pair_role`**, a column recording which half of a resolved pair an address is.

This is a label added to a census that already existed. No register `status:`
moved, no register was read back, `xdata-clusters.csv` did not change a byte,
`registers.yaml` and `ec/ghidra/xdata-symbols.csv` were not involved, and no
hardware or Windows machine was involved — every number here re-derives from the
committed decompiled tree and the committed CSV.

## What the column is, and where it sits

Column **34**, appended after `refs_main_ec`-through-`address-taken_pd`. Its
values are `seed`, `inc-dptr`, both joined with `+`, and the empty cell.

**Appended last, for the reason every column on this file after column 20 was.**
`REGISTER_COLUMNS` documents that committed `awk -F,` / `cut -d,` commands read
this file **by position** — `xdata-census-totals.md` sums `$6` and adds up
`$7`-`$11`, and `xdata-export-ownership-page-census.md` does the same over its
own scratch files. Inserting beside `spelled_as` would move every one of those
fields. Appending leaves `$6`-`$11`, `$21` and `$22`-`$33` meaning exactly what
they mean today.

**What it says.** Which spelling of a pair call site reached the address: this
byte was the `addr` argument a committed call site passes (`seed`), or it is the
byte the accessor's own `inc DPTR` walks onto (`inc-dptr`). That is all.

**Written on every row.** An empty cell is the answer "no pair call reaches this
address", and writing it everywhere is what makes the column checkable
corpus-wide. The alternative — blank on most rows — is the
`int('')`-where-`int`-is-natural failure `per_program_counts_of()` names, and
#713 already declined it once on these rows.

**Comma-free, mechanically.** `+` is the only punctuation that can appear, and
`pair_role_of()` can only join from the fixed `PAIR_ROLE_ORDER` tuple, so there
is no path by which a comma reaches the cell. That is what keeps the positional
readers exact; the self-test holds it by requiring every non-empty cell to
equal the vocabulary re-rendered in that order.

**Both roles, if both.** Two call sites can pass `a` and reach `a + 1`
themselves, so the halves are disjoint by no construction. A cell reading
`seed+inc-dptr` is then a true statement about one address rather than the
writer quietly dropping a role. On the committed tree the cell never occurs —
see the measurement below — so this is a superset of the two values, not a
different column.

## Where the numbers come from

```console
$ cd ec/tools
$ python3 xdata_register_map.py --self-test
$ python3 -m unittest test_xdata_pair_role.py
```

On the committed tree the pair pass reaches 214 addresses, and the census's
214 non-empty cells split **107 `seed` / 107 `inc-dptr`** with an intersection
of **none** — so the two halves partition the population and nothing is
counted twice. `xdata_register_map.PAIR_ROWS` is 214 and the self-test asserts
the column's closure against it, reading the figure out of the module rather
than typing it here; `test_xdata_pair_role.py` re-derives the same partition
from `inc_dptr_sites.pair_pass()` and compares it to the committed CSV cell for
cell.

Nothing about those figures is a total this repository keeps: they are a
measurement over the committed tree that no change to the prose can move.

## What this does not establish

The column records a **spelling role at a call site**, and each of the following
is a claim it does not support. §4.7's "What it does not establish" is inherited
wholesale and is not restated here; this is the part specific to a *pair*.

- **Not that the two halves are the same register, or that the EC treats them
  alike.** `write_r3r4_to_xdata_pair`'s seed is a *written* pair by
  construction and `read_xdata_pair_to_r1r2`'s seed is a *read* pair; nothing
  in the tree establishes that a pair is one logical field.
- **Not that a reader and a writer of the same pair agree about the value.**
  The two halves can be reached only through accessors of opposite direction,
  and `spelled_as` says nothing about which.
- **Not that a static read or write is the EC acting on the byte.**
  `xdata-register-map.md` §4.7 works this through and it holds unchanged.
- **Not that the halves are disjoint.** That is measured here and asserted, not
  assumed — an address that is both would read `seed+inc-dptr` and would fail
  the disjointness check by name rather than quietly shrinking both counts.

## A `program=both` row, and why its union is benign here

A `both` row's cell is the union across the two programs, exactly as
`spelled_as` is. For a spelling that is load-bearing, because the two programs
spell one address differently; for a role it is not, and the reason is already
established in the tool: **every pair-reached address is a main-EC one** — the
pd image's own `read_be16_from_dptr` is called once with no argument — so a
union can only ever be a union with an empty half, and the cell is the
main-EC half unambiguously.

`0x04A3` is the row that proves it rather than merely arguing it. It reads
`program=both`, its `spelled_as` is the union `DAT_EXTMEM+pair-literal`, and its
role is `inc-dptr`: it is the `+1` of seed `0x04A2`, and the
`PAIR_BOTH_PAIR_LITERAL` reconciliation already establishes that the
`pair-literal` in that union is the main EC's. The self-test pins the row by
value for exactly that reason — it is the one row where a reader could
reasonably wonder which program's half the cell is describing.

## The correction ledger

**`xdata-inc-dptr-only.md` §1.** That page opens its "Why a tool, when the
census CSV exists" paragraph with "`xdata-registers.csv` cannot answer the
question", and goes on to say the seed/`+1` distinction "exists only inside
`pair_sites()`". Both halves were true on the tree that page was written on and
the first is now false. Per the retraction convention the sentence is **left
exactly as written**, with a dated correction beside it: the census answers it
now, the tool remains the right place for the *derivation* and for the
`MOV DPTR` question the column says nothing about, and this column is a reading
of the derivation rather than a replacement for it. `inc_dptr_sites.py`'s module
docstring carries the mirror of the same claim and is corrected the same way.

**`xdata-register-map.md` §2.** Its column-naming clause names column 21 and
the twelve after it; it now names column 34 in the same clause.

**`ec/README.md`.** The `annotations/xdata-registers.csv` bullet's column tour
ended at "the twelve columns after it (22–33)" and gained one sentence.

**`docs/findings/xdata-per-program-counts.md`.** §"what the twelve columns are"
states the file's shape as "1,326 rows × 33 columns", which this change makes
34. Left as written with a dated note beside it, for the same reason as the
rest of this ledger.

**`docs/findings.md` is not edited at all**, for two independent reasons. A
column change moves no census total: `refs`, the five buckets, `readers`,
`writers`, `functions_touched`, `co_reading`, `sources_beyond`, `spelled_as`,
`spellings_by_program` and every previous column are byte for byte what they
were, and no row was added or lost. `xdata-clusters.csv` regenerating
byte-identical is the proof, and the `awk -F,` transcript in
`xdata-per-program-counts.md` below re-runs unchanged. The file is also frozen:
`check_findings_frozen.py` fails a change that adds a section. §39 is left
exactly as written — its closing sentence names the re-keying follow-up and
already carries the 2026-09-30 correction recording that #713 and #714 did it,
and this column is orthogonal to both.

## One recorded limitation

`scan()` skips `shared` files when `--export-ownership` is set, so under that
flag the census's pair population is a *subset* of `inc_dptr_sites`'s.
`--export-ownership` is refused with both `--check` and `--self-test` and cannot
write the committed paths, so the committed column is the default run's answer
and the self-test pins that answer against `PAIR_ROWS`. The subset is not a
disagreement about which calls resolve — the two tools take the same
`pair_sites()` walk with the same arguments — it is the same walk over fewer
files.

## Not this issue's job

- **The `program=both` re-keying (#713) and §2's `both`-row re-keying
  (#714).** This column touches neither, and #713's write-up's "not done, and
  named" list is unchanged.
- **Whether the 73 are entered in `registers.yaml`.** Settled by #723 and not
  reopened. No `status:` moves and no entry is added or removed.
- **Whether a pair is one logical field.** No evidence in the tree, and this
  page records the question as open rather than answering it.
- **Any hardware or Windows run.** None is needed and none is possible from a
  runner. Nothing here is evidence the EC acts on any of these bytes.
- **Registering the new suite in CI.** `.github/scripts/agent-gates.sh` cannot
  be written by this branch, so `test_xdata_pair_role.py` is run by hand, exactly
  as `test_inc_dptr_sites.py` is today, and both say so in the same words. The
  `--self-test` assertions *are* gated already. **A human's change.**
- **Submitting anything upstream.** There is no prepared upstream patch and none
  is planned; this is a census column in this repository.
