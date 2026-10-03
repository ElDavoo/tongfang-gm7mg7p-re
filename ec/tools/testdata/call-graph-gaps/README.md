# call-graph-gaps fixture

A miniature `ec/decompiled/` tree for `../call_graph_gaps.py --self-test`. Its
subject is the two populations `../call_graph.py`'s census reduces to an
integer — the transfer targets `Index.resolve()` declines, and the anonymous
rows no transfer reaches — so every file here exists to put one target or one
unreached row into a named class, or to put two classes at the same address so
the precedence has something to decide.

Every case is at a `D0xx` address. That is deliberate and it is the reason the
assertions read as shapes: the committed tree's real addresses are free to move
as tranches land, so an assertion pinned to `0x5A44` would redden the day a
tranche renamed its host, and the failure would say nothing about whether the
classifier still worked.

One consequence worth naming: `D` is a hex digit and `D0xx` is not a complete
one, so `../check_testdata_index.py` reports the `index.csv` rows this file
names as *unresolved* -- it splits a `X.csv + address` cell and reads the
address as hex, and `D100` is not. That is counted and printed, never a
failure, and it is the tool's stated "not resolved by this method, never
absent" line rather than a gap in the fixture. A fixture address the checker
*could* read would have to be hex, and a hex address chosen for being unused is
the thing these cases are avoiding.

| file / row | what it pins |
|---|---|
| `index.csv` rows `bank0,D100` / `bank1,D100` | the **`multi-scope`** case: one address two scopes carry, reached from `common/D0A0` in a third. `Index.resolve()` declines it, and the artifact has to name both host rows rather than pick one — the caller's bank is not a choice this method gets to make |
| `registers.yaml` `0xD012` | the **`xdata-or-data`** case, and the only address two rules would claim: it is also strictly inside `common/D010`'s span, so `xdata-or-data` and `interior-entry` both fire and the precedence is exercised rather than described |
| `registers.yaml` `0xD0F8` | a second XDATA address that **no transfer and no index row reaches**, so the fixture's `no-index-row` case at `0xD0F1` is a real miss rather than the only address the file happened to carry |
| `index.csv` row `common,D010` (size 21) | the **`interior-entry`** host. `[0xD010, 0xD025)` is its span, so `0xD01E` and `0xD024` are interior entries with no index row of their own — and `0xD012` from the row above sits inside the same span |
| `decompiled/common/D080.asm` | a 2-byte **`ajmp`**, whose page is in the opcode and only the low byte in the operand. It reaches `0xD012`, so the `forms` column has a paged-only row to carry while `cause` still reports `xdata-or-data`: the paged signal is a column and not a fifth vocabulary value |
| `decompiled/common/D010.asm` | four `lcall`s from one row — one that resolves to a real row and three that land inside this row with no row of their own. It is what makes `sites` differ from `callers` on the artifact's own fixture |
| `decompiled/common/D090.asm` | the **`no-index-row`** case: `0xD0F1` has no index row, no `registers.yaml` entry and no row whose span contains it. This method placed it nowhere, which is not a statement about the firmware and is why the artifact says so in its own header |
| `decompiled/common/D030.asm` + `index.csv` `common,D031` | the **`fall-through`** case. A 1-byte `nop`, so `0xD031` is one past this listing's last instruction and control does continue into it. The predecessor is a *named* row, which is the `pred_named=yes` case |
| `decompiled/common/D03F.asm` + `index.csv` `common,D040` | the **`adjacent-return`** case, and the reason `entry` is three values rather than two. This listing ends in `ret`, so `0xD040` one past it is adjacent by arithmetic and **not** entered by falling through. Reading it as a fall-through would credit an entry the bytes do not make |
| `decompiled/common/D050.asm` + `index.csv` `common,D050` | the **`not-adjacent`** case: no index row's last instruction lands immediately before it, so the classifier says so rather than inventing a predecessor. It is also the row whose empty `pred_*` cells the self-test pins |

The `#` header comments on the listings are the house format
(`build_ec_decompile.py` writes them), kept so the tree looks like a
decompiled one rather than a pile of hand-written bytes. The `; bank0 @` line
names the scope the fixture uses throughout; the `D0xx` addresses are not real
firmware addresses and the byte values are not real instruction encodings
beyond being the right width.

Both CSVs keep the real tree's column set, so the tool under test reads them
with the same `csv.DictReader` path it reads `ec/decompiled/index.csv` with. The
`evidence` column is empty throughout: it is the one column that points at the
**real** tree, and `../check_testdata_index.py` resolves it against the
repository root, so a fixture address named there would be a cell asserting a
path this tree does not have.

Not a model of the real tree, and not meant to be: the real censuses are in
`ec/annotations/call-graph.md`, the real artifacts are
`ec/annotations/call-graph-unresolved.csv` and
`ec/annotations/call-graph-unreached.csv`, and the real `.asm` files are
generated. This tree is hand-written and hand-checked, which is what makes it
an oracle.