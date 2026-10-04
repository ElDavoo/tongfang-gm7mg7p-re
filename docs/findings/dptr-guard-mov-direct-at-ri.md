# `mov direct,@Ri` is in the store table now, and the guard stopped disagreeing with it

(2026-10-04, issue #1391. Static reading of committed files:
`ec/firmware/GMxMGxx_11.800`, the committed annotation tables, and the
committed Ghidra listings. No capture opened, no EC, no hardware, no Windows,
no `registers.yaml` row touched.)

Issue #1389 measured the hole in `is_dptr_rebuild()` and left it open on
purpose, on the argument that widening the guard is a different change with a
different census behind it. The census has since landed —
[`dptr-guard-census-vs-1027.md`](dptr-guard-census-vs-1027.md) §3 counts the
form — so this is that change, and it is one line of code.

`0x86` `mov 0xnn,@r0` and `0x87` `mov 0xnn,@r1` are in
`trace_xdata_refs.DIRECT_STORE_OPS`. They name their destination at `d[i+1]`,
the index every other two-byte store form in the table already uses, so the
existing branch of `is_dptr_rebuild()` answers for them with no change to the
function body, and `MOV_DIRECT_DIRECT`'s separate three-byte handling at
`d[i+2]` is untouched.

## The two lists, which are now one relation

The sharper half of the problem was not the guard at all: the tree held **two**
opcode sets answering the same question with different answers, and a test that
asserted the disagreement rather than resolving it. `dptr_rebuild_forms.py`'s
`STORE_FORMS` carried `0x86`/`0x87` throughout; `trace_xdata_refs.py`'s
`DIRECT_STORE_OPS` did not.

The exact relation is an equality of two sets, not "the same modulo `0x90`":

```python
set(F.STORE_FORMS) == set(T.DIRECT_STORE_OPS) | {T.MOV_DIRECT_DIRECT}
```

`0x85` `mov direct,direct` is the single exception and it is in the guard as
`MOV_DIRECT_DIRECT` because its **destination** is its second operand, which
is why it is keyed on `d[i+2]` while every other member is keyed on `d[i+1]`.
`0x90` `mov DPTR,#imm16` is in **neither** set and is deliberately in none of
the census's three tables: it replaces the pointer and names no `direct`
operand at all, so a census keyed on the operand cannot hold it.

`test_dptr_rebuild_forms.py` asserts that equality, and — beside it, in the
house pattern of `test_the_completeness_check_can_reject_a_wrong_union` —
drives a copy of each set with one member missing and with one member added
through the same comparison and asserts inequality in **both** directions, so
the check is shown able to reject a wrong answer rather than only to accept
this one.

**What the case it replaces was doing, which is the reason the negative
control was not optional.** `GUARD_GAP_OPS` used to be asserted as
`set(STORE_FORMS) == set(DIRECT_STORE_OPS) | {0x85} | GUARD_GAP_OPS`. That
union is idempotent: once the guard carried `0x86`/`0x87` themselves, the
comparison still passed while being structurally incapable of noticing that
the named gap had closed. A test that tolerates a named exception cannot
notice the exception going away. The relation is now asserted with no
exception in it, and the delta constant is gone rather than renamed.

## What it costs, measured

The guard is a published part of how every committed table's `window` and
`terminator` columns were produced, so widening it is a claim about those
tables until the check says otherwise. The check says otherwise:

```sh
python3 ec/tools/walk_budget_census.py ec/firmware/GMxMGxx_11.800 --check
```

```
ec/annotations/walk-budget-census.csv: this run reproduces it byte for byte (18 lines)
```

`walk_budget_census.TABLES` is what that `--check` is derived from, and **no
committed row in any of them moves** — not a `window` cell, not a `terminator`,
not an `access`. The six `--terminator-column` tables of
[`dptr-rebuild-walk-guard.md`](dptr-rebuild-walk-guard.md) §9 and
`xdata-086x-dispatch-sites.csv`'s own `--check` all still reproduce byte for
byte; each command is that section's, unchanged.

The whole-image sweeps that write-up commits are unchanged as well, which is
the stronger statement — the check only covers rows somebody committed, and
§9's steps 9 and 9b cover every mapped site and every offset in the file:

- Over the mapped `MOV DPTR,#imm16` sites, `0x86` and `0x87` fire **0** times.
  §9's step-9 tally prints the construction that ended each window, and the
  two rows are absent from it rather than present and zero. This is the
  figure §1's table takes, and it is why the two new rows there carry 0.
- §9b's all-262,144-offset four-row census is byte-identical under the widened
  guard: `117520 max_insns (8) exhausted` / `112959 flow opcode` /
  `31655 is_dptr_rebuild` / `10 end of buffer`.

## Why it is worth doing now rather than at the next image

The census in `dptr-guard-census-vs-1027.md` §3 finds **11** byte pairs
`87 82` over the committed image, and every one of them is mid-instruction —
each the middle and last byte of an `lcall 0x8782` — so a decoded sweep finds
none and no window the guard actually walks was affected. That is a fact
about a byte census over 262,144 bytes of **this** image, not a property of
the guard, and §3 of
[`dptr-rebuild-walk-guard.md`](dptr-rebuild-walk-guard.md) says so in the same
terms where it left the gap open. A property of the file cannot tell the next
image, or the next table, that it would have inherited the hole: with the two
rows firing 0 times here, a `mov 0x82,@r0` in a window somewhere else would
have had `walk_why()` run straight past it and charge the `movx` behind it to
the address the site's own `mov DPTR,#imm16` named — one register's access row
reading as another's, which is precisely the failure the predicate exists to
prevent. Closing a gap the committed data happens not to exercise is the whole
of what a guard is for.

## What this does not establish

- **Nothing about what the EC does.** Every input is a committed file. A guard
  widened over committed bytes is not evidence about a register's behaviour,
  and no `registers.yaml` `status:` moves on the strength of it.
- **No `static_refs` count moves.** `mov 0x82,@r0` names a **byte**, not an
  XDATA address: the operand is a direct address, not a reference to whatever
  the site accessed. A register's row is unaffected by which form wrote the
  pointer.
- **The in-place forms stay declined.** #1294's six
  (`0x42`/`0x43`/`0x52`/`0x53`/`0x62`/`0x63`), `xch a,direct` (`0xC5`),
  `inc`/`dec direct` and the rest are a different half of the map, and
  `dptr-rebuild-walk-guard.md` §3 declines them for a reason that is still
  valid: they mask or arithmetically modify the pointer already there, the
  same treatment `inc dptr` gets as a span walk. Folding them in would convert
  a documented decision into behaviour, which is a different change with its
  own census behind it. `test_dptr_rebuild_guard.py` holds them as negative
  cases, so a later widening is a deliberate edit rather than a silent one.
- **Nothing about `mov DPTR,#imm16`.** It was never in either set.
- **No live test.** Static reading only; a question needing a real observation
  on the machine is a new issue for a human with the hardware.