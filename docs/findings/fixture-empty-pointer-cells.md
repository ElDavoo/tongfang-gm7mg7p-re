# The fixture's six empty cells are not a count, and the set is derivable where the six is not (issue #1006)

The write-up for [issue
#1006](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1006), which
follows #780's. That issue emptied six `evidence` cells in the two CSVs of
`ec/tools/testdata/call-graph/` rather than point them at a listing the real
tree does not have, and wrote the six down in the fixture's own `README.md` in
the same edit. Both halves of that are hand-kept. This is the half nothing
held: the six were never a count of the emptied cells, and nothing kept them
equal to one.

`ec/tools/check_fixture_pointer_cells.py` now derives the set from the two
committed CSVs and `ec/tools/test_check_fixture_pointer_cells.py` holds the
README's six addresses to it from both sides. Nothing here reads a capture, an
EC or a laptop; every figure below is a read of committed files, and each
section names the command that produces it.

---

## The measurement

```sh
$ python3 ec/tools/check_fixture_pointer_cells.py --check
```

The last three lines of that run, which are the whole of the derivation and
are quoted rather than retyped so a reader can re-run them rather than trust
them:

```
2 fixture CSV(s), 3 pointer column(s), 64 pointer cell(s): 37 resolved, 0 unresolved, 27 empty
27 empty cell(s), 23 address(es): 5 documented, 1 synthetic, 17 transfer-seeded, 0 undocumented
6 named address(es), 6 of them empty here
```

Per address the report prints the kind and every cell behind it, which is the
shape a reader wants and the reason an address with a cell in both CSVs is one
entry rather than two:

```
  0071  documented
      ec/tools/testdata/call-graph/ghidra-functions.csv  evidence  common,0071
      ec/tools/testdata/call-graph/index.csv  evidence  common,0071
      README.md: "A cell whose path the real tree does not have turns the check red, so six of this fixture's addresses have their cell **empty**: ..."
  0EA3  synthetic
      ec/tools/testdata/call-graph/ghidra-functions.csv  evidence  bank0,0EA3
  05E8  transfer-seeded
      ec/tools/testdata/call-graph/index.csv  evidence  common,05E8
```

`37 + 27 = 64`: the two CSVs' three pointer columns hold 64 cells, and 27 of
them carry no value, over 23 distinct addresses (four addresses are empty in
both CSVs, and one of the six is empty in `ghidra-functions.csv` only).

## The retraction: "so six" is not a count of them

`ec/tools/testdata/call-graph/README.md` says a cell whose path the real tree
does not have turns the check red, "**so six of this fixture's addresses have
their cell empty**", and then names six. The word carrying the count is *so*.
Twenty-three addresses have an empty cell. The six are the six the paragraph
goes on to explain — the fixture-only pair, the synthetic row, the two
fixture-invented addresses and the PD one — and that is a different claim from
being the population.

The same sentence appeared in #780's write-up, and there it was explicit about
the arithmetic, which is what makes this a retraction rather than a rewording.
`docs/findings/testdata-index-evidence-column.md` says of the sixth address:

> it is in the list because a reader counting the emptied cells should find the
> number the file explains.

**That reason does not hold.** A reader counting finds twenty-three, so the
sentence told a reader to expect a number the tree does not have — which is
`CLAUDE.md`'s *"assert the claim (`twelve suites are cited by line`), not the
census (`fifty-nine suites exist`)"* one level down, and the reason the fix
here holds the **addresses** rather than any figure. The correction is beside
the sentence in the fixture README, in the `**Correction, …**` form rather
than `*(Superseded …)*` (`check_no_append_logs.py` fails the second outside
`docs/findings/`, and this file is outside it). The six are left visible and
unedited: they are the record of a decision, and §4a-4d is about keeping the
wrong version next to the correction, not about deleting the thing that was
decided.

## Why the six is not derivable — the negative result

Recorded here so the next reader does not run the search again. Every column
of both CSVs, every distinct value, and whether any value puts the six on one
side of the other seventeen:

```sh
$ python3 - <<'PY'
import csv, os
d = "ec/tools/testdata/call-graph"
def read(n):
    rows = list(csv.reader(open(os.path.join(d, n), encoding="utf-8", newline="")))
    return rows[0], [r for r in rows[1:] if r]
def empties(h, rows):
    i = h.index("evidence")
    return {r[h.index("addr")] for r in rows if i >= len(r) or not r[i].strip()}
ih, idx = read("index.csv"); gh, ghi = read("ghidra-functions.csv")
empty = empties(ih, idx) | empties(gh, ghi)
six = {"0D20", "0D40", "0EA3", "0071", "F6A0", "10E0"}
rest = empty - six
for h, rows, label in ((ih, idx, "index"), (gh, ghi, "ghidra")):
    for c in h:
        if c in ("addr", "name", "size", "comment", "evidence", "out_file"):
            continue                      # per-address, so a tautology
        mine, theirs = set(), set()
        for r in rows:
            a = r[h.index("addr")]
            (mine if a in six else theirs if a in rest else set()).add(r[h.index(c)])
        print(f"{label}.{c:<11} {sorted(mine)} shared: {sorted(mine & theirs)}")
PY
```

| column | values on the six | shared with the seventeen |
|---|---|---|
| `index.program` | `bank1`, `common`, `pd` | `common`, `pd` |
| `index.seed_basis` | `annotation`, `call-target` | **`call-target`** |
| `index.common` | `no`, `yes` | `no`, `yes` |
| `index.annotated` | `no`, `yes` | `no` |
| `index.type` | `''`, `delay`, `unresolved` | `''` |
| `index.basis` | `''`, `hand-decoded` | `''` |
| `index.also_in` | `''`, `bank0`, `bank1` | `''`, **`bank1`** |
| `ghidra.scope` | `bank0`, `bank1`, `common`, `pd` | `pd` |
| `ghidra.type` | `unresolved` | `unresolved` |
| `ghidra.signature` | `''` | `''` |
| `ghidra.basis` | `hand-decoded` | `hand-decoded` |

Every column in that table has a value on both sides. The two the command
skips are the ones that cannot: `index.out_file`, whose five values are derived
from the address (`common/0071.c` for `0x0071`), and the per-address columns
`addr`, `name`, `size`, `comment`, `evidence` — "the row's own address separates
it from the other rows" is not a predicate.

The nearest miss is `seed_basis=annotation`, which covers three of the six
(`0x0D20`, `0x0071`, `0x10E0`) and misses the other three: `0x0D40` and
`0xF6A0` are `call-target` rows exactly like the seventeen, and `0x0EA3` is in
a CSV with no `seed_basis` column at all. `also_in=bank1` is shared with
fifteen of the seventeen. So **no value in any column of either file puts all
six on one side**, and the six are a record of #780's decision, not a class
anything derives. The tool keeps them as prose and derives only the set.

## The three classes, and each rule's edge

The set partitions, and the three rules are read off columns rather than off
prose, so nothing here depends on a sentence staying as written.

| class | rule | this tree |
|---|---|---|
| `synthetic` | the address is carried by exactly one CSV **and** that CSV has no `seed_basis` column, so nothing in the fixture records how the row was seeded | 1 — `0xEA3` |
| `documented` | the fixture README's empty-cell paragraph names the address | 5 — `0x0D20` `0x0071` `0xF6A0` `0x10E0` `0x0D40` |
| `transfer-seeded` | the row's CSV has a `seed_basis` column and this row reads `call-target` | 17 |
| `undocumented` | none of the above — **and the run is red** | 0 |

**Precedence is `synthetic` → `documented` → `transfer-seeded`,** and each
step down is a weaker input: a column set, then a sentence, then one cell's
value explaining a class. Two of the three are decided by the disagreement
between them, and both are live on this tree:

- `0x0EA3` is in the README's six *and* uncorroborated by any other file, so
  the two clauses disagree and the columns outrank the prose. It is the only
  address where they do.
- `0x0D40` and `0xF6A0` are in the README's six *and* `call-target` rows like
  the seventeen, so the prose outranks `transfer-seeded`. Without the
  precedence the six would reclassify themselves the moment a `seed_basis`
  cell was edited.

**Why `synthetic` needs the missing `seed_basis` column and not only the
missing row.** `common,0D40` is equally uncorroborated — no other file has a
row at that address — and is not synthetic. Its own row says it was seeded by
a transfer scan, which is a record of where it came from. A rule that asked
only "is any other CSV carrying this address" would call it synthetic and
would be wrong for a reason no reader of the report could see.

**The residue is the finding.** An empty cell on a row the transfer scan did
not seed, with no sentence beside it, is `undocumented` and fails: that is the
issue's own failure, one cell, and the message names the row and the
`seed_basis` it read. A CSV carrying a pointer column and no `seed_basis`
column at all lands there too and says so, rather than having a rule invented
for it.

**The reverse direction is checked too,** because a claim can be left behind
by a cell being *filled in* as well as by one being emptied. An address the
paragraph names whose pointer cells are all populated is a finding. That is
the #780 fix explicitly declined: repointing `0x0EA3` at the real
`bank0/0EA2.asm` makes a resolved cell assert that a synthetic row's
decompilation is a different function's file, and only this direction reports
it.

## The marker column, declined

The issue leaves it to this stage to decide whether each entry's reason should
be a `synthetic` marker column in the fixture CSVs or something else, and to
defend the call. **Declined**, and the reason is one property of the fixture
that is easy to break silently:

```sh
$ md5sum <(head -1 ec/tools/testdata/call-graph/index.csv) \
          <(head -1 ec/decompiled/index.csv) \
          <(head -1 ec/decompiled/listing-index.csv)
7c43e57a07df8f0c87a4dbed9cda307b  /dev/fd/63
7c43e57a07df8f0c87a4dbed9cda307b  /dev/fd/62
7c43e57a07df8f0c87a4dbed9cda307b  /dev/fd/61
```

The fixture's header **is** the real tree's header, byte for byte, and that is
what lets the fixture exercise the real column set — twelve columns, read by
name because `evidence` is column 10 of 12 here and column 7 of 8 in the other
CSV. A thirteenth column would break the one property that makes it a fixture,
and it would break it *silently*: `call_graph.py`'s `load_index()` is a
`csv.DictReader` with no `fieldnames=`, and every column lookup in
`check_testdata_index.py` is by name, so a thirteenth key would be carried and
never read rather than refused. So the reason is **derived and printed**: each
entry carries a `kind` and the rule that fired, in the report above, and the
rule is structural over column *sets* rather than a list of column names.

The same argument makes **which** columns are pointer columns structural: a
column qualifies when one of its cells names a path, which on this tree
selects `evidence` and `out_file` and nothing else — `also_in` holds program
names, and `comment` holds sentences. A fixture carrying a fourth pointer
column is read with no edit here, and the suite tests that with a directory
name and a header the tool has never seen.

One clause in the tool's `names_a_file()` is not a restatement. The reference
implementation reads backticked tokens out of a markdown table, where a token
is a path by construction; this reads whole CSV columns, and `comment` cells
are sentences that end in a period, which `splitext` reads as a file whose
extension is `.`. A path has no spaces and a sentence has many, so the test is
over the token as a whole.

## The `out_file` column, measured

The issue's fourth bullet asks that the README say which column each entry
came from, and offers to fold in the `out_file` issue's ten if it lands first.
The answer is that only one column contributes, and the reason is worth the
sibling issue inheriting a number rather than a rumour.

- `out_file` has **zero** cells carrying no value: all 27 of `index.csv`'s
  carry one. It is not in the derived set, and the ten is a different
  predicate.
- The ten is real and is about the *tree*, not the cells: **10 of the 27**
  `out_file` values name a path the real `ec/decompiled/` does not have. 17
  resolve there, `bank1/F6A0.asm` exists only in the fixture's own tree, and 9
  are in neither.
- **`out_file` is read by nothing in the fixture's neighbourhood.** `grep -c
  out_file` over `call_graph.py`, `citation_frames.py`, `citation_callers.py`
  and `check_testdata_index.py` returns `0` for all four.
  `build_ec_decompile.py` does write it when it builds the real index, and
  normalises the value it wrote, so the column is not vestigial in the pipeline —
  it is a vestigial column *in the fixture*, inherited from the real header it
  has to match, and read by nothing that looks at the fixture at all.
- Therefore this tool does not resolve a path against the disk at all. The two
  pointer columns are rooted at different places — `evidence` at the
  repository root, `out_file` at `ec/decompiled/` — so an existence check
  needs a per-column base, which is the exemption list the structural rule
  above exists to avoid, and it would be red on the day it landed. That is the
  condition `docs/findings/testdata-index-evidence-column.md` records for
  pointing a check at that column at all, and the tool repeats it rather than
  re-deciding it. `check_testdata_index.py` keeps the `evidence`-side check,
  so between them the two cover the cell from both ends and neither
  double-counts the other's base.

## What this holds, and what it does not claim

- **Held:** every address the README names is an empty pointer cell; the
  derived set is exactly those addresses plus the transfer-seeded residue,
  disjointly; and every entry carries one of the three kinds. No assertion
  anywhere of the shape "the derived set has N entries" — a count of the tree
  is a value every emptied cell moves.
- **Not claimed:** that any fixture is *correct*, that an empty cell is the
  right answer (`0x0EA3` needing one is #780's judgement, left standing), or
  that a static scan's silence means absence. An empty cell is reported as a
  cell carrying no value, which is the line `ec/annotations/registers.yaml`
  carries.
- **The declared limit, found by writing this suite.** The qualification rule
  needs one path-shaped cell per pointer column, so a CSV whose every
  `evidence` cell is empty has no pointer column at all and its empties are
  invisible. The populated cells the committed fixture carries are the only
  reason its empty ones are read at all. The suite's own scratch corpus is
  built with a populated cell for the same reason, which is the second time
  that detail has turned out to be load-bearing; the degenerate case is pinned
  as red rather than green, because the README's claim then has nothing behind
  it and the run says so.

## Left out on purpose

- **Gate wiring.** `.github/scripts/agent-gates.sh` is copied from
  `ElDavoo/agent-pipeline` and this branch's push token has no `workflow`
  scope, so a branch editing it fails at the end rather than at the start. The
  prepared patch is the established answer and
  `tools/test_agent_gates_patches.py` keeps an **ordered** `PATCHES` list that
  two branches each numbering from their own base have already collided in; an
  eighth patch for a line that cannot take effect, at the cost of editing two
  more shared files, is not worth it. The one line a human would add is a
  `check_fixture_pointer_cells.py --check` arm beside the
  `check_testdata_index.py` one. Nothing is lost meanwhile: the suite runs the
  tool over scratch fixtures and over the committed one, which is how
  `check_testdata_index.py`'s own rules are exercised today.
- **The `out_file` column and its ten.** Measured above: a different
  predicate, a sibling issue's, and red on arrival per #780's record.
- **The reverse direction over listings.** A real `ec/decompiled/**` listing
  that no `evidence` cell names — 2,711 `.asm` files, 11 tokens — is
  `check_testdata_index.py`'s declared limit and is unchanged here.
- **The real tree's own indexes.** `ec/decompiled/index.csv` and
  `ec/annotations/ghidra-functions.csv` are a different owner and a much
  larger tree, and `pd,0x10BC`'s real `evidence` names three
  `ec/annotations/*.md` documents rather than listings, so pointing a check at
  them is a piece of work in its own right.
- **`ec/tools/testdata/call-graph/README.md:15` carries a real drift**, found
  while measuring and not fixed here: the `decompiled/common/05E8.asm` row
  says the common row must report `also_in=bank0`, while `index.csv:3` carries
  `also_in=bank1` and `call_graph.py`'s self-test asserts `== "bank1"`. Two of
  the three say `bank1` and the prose is the odd one out. It is a different
  defect with a different owner, in a shared file this branch already edits
  once. **Named here so it becomes an issue.**
- **`ec/tools/test_check_testdata_index.py` carries a census** —
  `(found.cells, found.tokens) == (5, 6)` and `(5, 5)` — which is the
  anti-pattern `CLAUDE.md` names and which moves every time a cell is emptied.
  Named, not fixed: that file is #780's and a live conflict surface.
- **Live hardware, Windows, the EC, the BIOS, the vendor stack.** Nothing in
  this change needs a machine. Every artifact it reads is already committed
  and no live observation is required to close the issue.
- **Submitting anything upstream.** No issue or PR is opened against
  `Wer-Wolf/uniwill-laptop`, `tuxedo-drivers` or anywhere else. This work is
  not an upstream deliverable; that is issue #10's, for a human to submit by
  hand.
- **A judgement no check here can make.** Whether `0x0D40` *should* be in the
  six is a decision #780 recorded, and this change preserves it rather than
  re-opening it. The derivation can hold the record to the CSVs, which is what
  the issue asked for; it cannot say the record is the right record.
