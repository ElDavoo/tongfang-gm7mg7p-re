# The PD call-target census: sixteen sites get sixteen verdicts, and two of them are calls

`docs/findings/pd-common-address-spaces.md` byte-scans
`ec/firmware/GMxMGxx_11.800[0x20000:0x30000]` for the `12 11 c2` encoding,
gets sixteen hits, and says in so many words that this method "can neither
call them callers nor data". That is the right sentence about a byte scan and
not the last word. A byte triple is not an instruction, and what settles it is
decoding the bytes under an aligned walk — which
`ec/tools/pd_call_targets.py` now does, from a stated entry set, following
control flow rather than matching byte patterns.

The committed artifact is `ec/annotations/pd-call-targets.csv`: one row per
candidate offset, each with a verdict, the enclosing listing, whether that
listing contains it, the framing evidence, and the terminator of the walk that
reached it. The tool's `--check` regenerates the table and diffs it byte for
byte, so the page and the bytes cannot drift apart quietly.

**Nothing here was observed on hardware.** Every input is the committed
firmware and committed CSVs, and every verdict is a statement about framing.

## What the sixteen `12 11 c2` sites now say

The addresses are the ones `pd-common-address-spaces.md` lists and
`ec/annotations/pd-image.md` already pins in its `code_table_inline` line, so
they are cross-referenced here rather than restated as a new discovery. What is
new is the verdict each one carries:

| site | enclosing listing | `in_listing` | verdict |
|---|---|---|---|
| `0x13F6` | `0x133F` | no | `unreached-by-this-method` |
| `0x153E` | `0x133F` | no | `unreached-by-this-method` |
| `0x16A7` | `0x133F` | no | `unreached-by-this-method` |
| `0x1AB6` | `0x1820` | no | `unreached-by-this-method` |
| `0x1C88` | `0x1820` | no | `unreached-by-this-method` |
| `0x3A46` | `0x3A33` | no | `unreached-by-this-method` |
| `0x4587` | `0x4402` | no | `unreached-by-this-method` |
| `0x483A` | `0x4800` | no | `unreached-by-this-method` |
| `0x4FFA` | `0x4E84` | no | `unreached-by-this-method` |
| `0x617D` | `0x5950` | no | `unreached-by-this-method` |
| `0x776C` | `0x775C` | no | `unreached-by-this-method` |
| `0x7948` | `0x775C` | no | `unreached-by-this-method` |
| **`0x8288`** | `0x821B` | **no** | **`decoded-lcall`** |
| `0x83CF` | `0x821B` | no | `unreached-by-this-method` |
| `0x92EF` | `0x9177` | no | `unreached-by-this-method` |
| **`0xCB4A`** | `0xCB2A` | **yes** | **`decoded-lcall`** |

So the census **adds one site to the page's list of calls** — `0x8288`, which
no committed listing contains — and it **refutes nothing that was previously
called a call**. `0xCB4A` was already the one the byte scan found inside a
committed listing and it stays a call; the other fourteen the byte scan left as
candidates stay candidates, now with the reason attached: no walk from this
entry set decoded them.

**`0x8288` is a call, and it is outside every committed listing.** An aligned
decode from the nearest listing above it reads it as an `lcall 0x11C2` between
a `mov b,r6` and a `movc a,@a+pc`:

```
$ python3 ec/tools/make_bank_image.py --pd ec/firmware/GMxMGxx_11.800 pd.bin
$ r2 -a 8051 -q -e bin.baddr=0 -c 's 0x8274; pd 14' pd.bin
0x00008274  900849   mov dptr, #0x0849
0x00008277  e0       movx a, @dptr
0x00008278  fb       mov r3, a
0x00008279  900424   mov dptr, #0x0424
0x0000827c  1299c1   lcall 0x99c1
0x0000827f  12998f   lcall 0x998f
0x00008282  e0       movx a, @dptr
0x00008283  fe       mov r6, a
0x00008284  a3       inc dptr
0x00008285  e0       movx a, @dptr
0x00008286  8ef0     mov b, r6
0x00008288  1211c2   lcall 0x11c2     <- the site the census adds
0x0000828b  83       movc a, @a+pc
0x0000828c  6f       xrl a, r7
```

`0x821B`'s committed listing is `fill_0849_0857_block`, spanning `0x821B` through
`0x825A`, so it does not reach `0x8288`. That is why `enclosing` and
`in_listing` are two columns: the nearest listing below a site is a fact about
where the site sits, and whether the site is inside that listing is a separate
question that here answers no. The suite asserts this disagreement on this named
site — both the `enclosing` cell and the `no` — which is the only way to hold it
without pinning a count of this repository's listings.

## The nine `12 11 9c` sites

The same treatment for `dispatch_code_table` at `0x119C`. Eight of the nine are
`decoded-lcall` and `0x6B4C` is `unreached-by-this-method`. Six of the eight sit
inside a committed listing and two do not — `0x42C5` (enclosing `0x3FEA`) and
`0x44D2` (enclosing `0x4402`). All nine score 24 of 24 on `converges_from`,
which is worth saying plainly: that is the *framing* evidence being unanimous
and it settles nothing about whether the walk reaches the byte.

## The premise this issue was filed on is refuted by grep

The issue says the `.asm` headers at `ec/decompiled/pd/10F1.asm`, `1229.asm`
and others note the function boundary "came from a call-target byte scan and is
a hypothesis".

**No `pd/*.asm` carries that note, in either spelling.** The phrase is in
these `pd/*.c` files, whose comments say "The .asm header notes that this
function boundary came from a call-target byte scan" — citing a header beside
them that does not contain it:

`0EF3.c`, `10F1.c`, `1229.c`, `9A1B.c`, `9A90.c`, `F109.c`, `F126.c`, `F4AB.c`

Most of them say "call-target byte scan"; `1229.c` alone says
"call-target-scan", so a grep for one spelling alone would have found fewer
than the list and called it complete. Every `pd` row of
`ec/decompiled/listing-index.csv` reads `seed_basis=annotation`, which is the
committed record of where those boundaries came from.

The wrong version is left standing rather than quietly fixed, per CLAUDE.md's
retraction rule. The amendment to those comments is not in this change: the
`.c` files are generated and the editable surface is
`ec/annotations/ghidra-functions.csv`, so a comment edit without the matching
Ghidra re-export would leave `build_ec_decompile.py --check` red, and the
re-export rewrites many generated files for a prose fix. That is the natural
follow-up issue.

`--seed-verdicts` measures the question the issue actually wanted rather than
planning around the stale prose: for each listing those comments name, does the
walk reach it, is it an entry in its own right, and does `converges_from()`
frame it. On this image every one of them is reached, is an entry by way of the
committed listing index, and scores 24 of 24. The seed list is derived from the
comments themselves, so it moves with the prose it is about and no figure of it
is pinned anywhere.

## What the walk is, and where its reach stops

The entry set is four sets and each row is tagged with its own: `vector` (the
table `pd_image_census.vector_table()` walks rather than looks up), `listing`
(the `pd` rows of `listing-index.csv`), `call-graph` (the `pd` rows of
`call-graph-callees.csv`, less the overlap), and `discovered` (a target a walk
itself decoded, queued as an entry in its own right, which closes the loop). An
address two of them name is one entry with two witnesses — all six vector
targets are also committed listings, so they carry the `vector` tag and are not
counted twice.

**The boundary rule is load-bearing.** A walk from entry *E* stops at the
lowest committed `pd` listing start strictly above *E* and records `next
listing boundary` in `ends`. Without it a mis-seeded entry runs for thousands of
bytes and every candidate site gets the wrong enclosing function. Ablating it
on this image yields a strict superset with a non-empty difference, which is
asserted as a *relationship* and never as a figure — a count of it is a number
this repository's own listings would move.

**Coverage is two partial methods that partly overlap, and neither contains the
other.** That is the honest shape and it is the opposite of what "the walk
reaches more" would suggest. `--report` prints the walk's reach, the listings'
coverage, and both differences; `check_coverage()` asserts on every run that
each is below the image size and that *both* differences are non-empty, so a
method that degenerated into containing the other would be a red run. No figure
of any of the four is written down here, in the tool, or in a test. An earlier
attempt at this tool pinned them as exact values, which made it red the moment a
`pd` listing landed — for a change that never touched it.

The walk's terminators are the vocabulary `walk_branch_arms.py` already
established, imported rather than re-spelled so one stop does not acquire two
names in this tree: `ret`, `reti`, `tail jump to a callee`, `indirect jump --
target not resolvable from the bytes`, `loop`, `depth limit`, `max_insns`, and
`index past the end of the image`, plus this tool's own `next listing
boundary`. The set is closed and the suite holds it.

**Annotate, never suppress.** A site inside an `ec/annotations/data-regions.yaml`
region keeps its row and gains its label in the `region` column;
`refuse_filtering()` is a named function called from `--self-test`, so a future
`--only-in-data` flag has to delete it to exist. The committed file lists no
region inside the PD extent, so `--report`'s data-region sentence is *derived*
from the live verdict count and the live region extents rather than typed — a
region landing moves both together and the report cannot contradict itself. The
suite asserts the printed prose matches the derived figures, not merely that the
count is what it was.

## The candidate set is a union, and the `candidate` column says which half

Rows are the union of two populations: every offset whose byte is `0x02` or
`0x12` with two bytes after it (the byte-scan upper bound, the same population
`bank-call-targets.csv` reports for three bank images), and every offset a walk
decoded as a call or a jump. The `candidate` column records which population
booked each row, so the union is auditable from the CSV alone. Either half
alone is wrong in a way the other fixes: the byte scan over-counts, because
those two byte values occur as operand bytes inside other instructions and
inside tables; the walk alone under-counts, because it cannot see a call whose
site no walk reached.

The rows the walk contributes that the byte scan structurally cannot find are
the paged and PC-relative transfers — `0x01`/`0x11` and the rel8 family carry
no `0x02`/`0x12` byte at the site. Those are the `walk`-only rows, and the
suite asserts each one's opcode really is outside the absolute family, so the
union is demonstrably carrying information the byte scan did not have.

## What this does not establish

- **A `decoded-lcall` row is a call as read by an aligned walk from a stated
  seed — not a confirmed caller.** `audit_call_targets.py`'s module docstring
  records that framing is unsettled in *both* directions, that its anchored
  count is "demonstrably not phantom-free", and that a same-bank and a
  cross-bank direct call are byte-identical. Nothing here settles framing.
- **`unreached-by-this-method` is never "absent" and never "data".** A byte can
  be unreached because no seed reaches it, because its only in-edges are edges
  this walk does not follow, or because the walk stopped at the boundary rule
  or a budget. All three are "not reached by this method".
- **The sixteen and the nine are not new discoveries.** They are already
  committed in `ec/annotations/pd-image.md`'s pinned `code_table_inline` line
  and in `pd-common-address-spaces.md`. This change's contribution is the
  *verdict per site*, and it cross-references those rather than printing the
  counts as new.
- **A row scoring 24 of 24 on `converges_from` is framing evidence, not a
  call.** `audit_call_targets.py` §4 lists sites that score 24 of 24 and are
  plainly inside an address table.
- **Nothing behavioural was established.** Nothing here was observed on
  hardware, no register was read back, and no `status:` in
  `ec/annotations/registers.yaml` moves because of a row in this table.

## What is deliberately not here

- **The 2-byte paged and PC-relative censuses as tables.** The walk *follows*
  those forms and its `walk`-only rows come from them, but
  `bank-paged-call-targets.csv` and `bank-relative-branch-targets.csv` are the
  committed censuses for them on the bank images, and giving the PD its own
  would be a second tool's census in a first tool's file. `--paged-csv` is the
  obvious follow-up.
- **What the dispatch tables select.** `pd-common-address-spaces.md` leaves
  `0x11C2` and `0x119C` open about what they hand back. That is a question
  about a table's contents, not about whether a call into it exists, and it
  stays open.
- **Naming any new function.** The census produces function *entries*; it does
  not make `ghidra-functions.csv` rows. `0x8288`'s routine is ordinary
  annotation work.
- **Amending the stale `pd/*.c` comments**, for the generated-file reason above.

## Reproducing it

```
python3 ec/tools/pd_call_targets.py --self-test
python3 ec/tools/pd_call_targets.py --check
python3 ec/tools/pd_call_targets.py --for-target 0x11C2
python3 ec/tools/pd_call_targets.py --for-target 0x119C
python3 ec/tools/pd_call_targets.py --seed-verdicts
python3 ec/tools/pd_call_targets.py --report
python3 ec/tools/test_pd_call_targets.py
```

`--check` is refused alongside every other output mode, so a gate line that
appends a flag fails loudly rather than exiting 0 having run no check. It has
exactly two halves and both run, with their return codes combined, so a table
mismatch cannot skip the relationship check.