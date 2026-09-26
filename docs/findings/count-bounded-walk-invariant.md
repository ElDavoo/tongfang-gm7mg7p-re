# A count is a budget on work, not a bound on the buffer: the region end bounds `walk_helper` and `chain_from`

(2026-09-26, issue #843. Static reading and commands over one committed image.
No capture opened, no EC, no hardware, no Windows.)

[`opcode-len-bounds-census.md`](opcode-len-bounds-census.md) rows 15 and 16
deferred a question rather than a fix. Their verdict cell reads `census row +
verdict` for both, and follow-up 1 says why:

> Now that the `len(d)`-bounded walks are written down as a class, whether these
> two should get a real bounds check is a well-posed question. It needs its own
> issue: the answer depends on what invariant a count-bounded walk is supposed
> to enforce, which is a design question and not a bug report.

This is that answer.

**The invariant, as one sentence: a count is a budget on work, not a bound on
the buffer, so the region end bounds the walk and the count stays as the cap on
a walk that never reaches it — and whichever end stopped the walk is said out
loud, because "ran out of instructions" and "ran out of image" are different
claims about the same routine.**

`walk_helper()` and `chain_from()` now take both ends of `pd_bounds()`,
clamp the top to the buffer as well, and stop at the region end naming it. The
count is untouched, and so is every number on the committed inputs.

## What was measured

Every figure below was re-run at this tree while implementing. The firmware is
`ec/firmware/GMxMGxx_11.800` throughout and `T` is
`python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800`.

### 1. No committed walk crosses the region end

The census's six commands, all exit 0, with `walk_helper()` instrumented to
report any listing offset `>= 0x30000` and every mode that reaches it driven:

| command | exit | output lines | listing offsets `>= 0x30000` |
|---|---:|---:|---:|
| `T --helpers` | 0 | 70 | 0 |
| `T --bases all` | 0 | 7270 | 0 |
| `T --sites 0xFFF0` | 0 | 20 | 0 |
| `T --accesses` | 0 | 980 | 0 |
| `T --callers 0x0860` | 0 | 4 | 0 |
| `T --strides all` | 0 | 12 | 0 |

**Zero crossings is "did not cross over these runs", not "cannot cross"** —
`docs/findings.md` §4, and the caveat on `ec/annotations/registers.yaml`. The
change is not justified by that zero; it is justified by the next section.

### 2. A *legal* address crossed it, which is what decides the question

The issue's exposure vector is `--helpers 0x1FFE9` / `0x1FFFF`, and both are
caller errors — an address that is not a PD runtime address. That framing alone
cannot be the whole answer, because there is a second case, and it is the one
that decides it:

```console
$ T --helpers 0xFFFF          # exit 0
    0xffff  ff       mov  r7,a
    0x10000  ff       mov  r7,a    <- file 0x30000, the region's first erased byte
    ...
    0x10016  ff       mov  r7,a
```

`0xFFFF` is a **legal** PD runtime address. `check_site_addr()` accepts it, the
region is 64 KiB wide, no CLI rule is broken and the caller did nothing wrong.
The listing is 24 lines and the last offset is file `0x30016`, so **23 of those
lines are the erased fill past the region's end at `0x30000`**, printed as
instructions, with nothing in the output saying the routine ended there.
`0xFF` is a 1-byte opcode, so nothing would ever have stopped it.

So the answer to the issue's question is not "a run off the region end is a
caller error" on its own — the vector above shows a *legal* argument doing
exactly that, for 23 of its 24 lines. The region end bounds the walk. This is
not a new shape either: it is the module's own `access_walk()`, which has
always taken `hi` for its loop bound and reports `image-bound` and
`truncated-instruction` as the two things that are not its budget.

### 3. The census's deferred "second contract" is provable, not assumed

Follow-up 1 also warned that a blanket range check inside `walk_helper()` "has a
second contract to satisfy", because `chain_from()` hands it targets decoded
out of the image's own branch operands. That contract is settled by two
measurements, and it is the reason the check goes where it goes:

- **`pd_bounds()` gives `hi - lo` = `0x10000`** — exactly the 16-bit address
  space. Every runtime address `branch_target()` can produce is therefore a
  legal PD runtime address *by construction*: the absolute forms build
  `(raw[1] << 8) | raw[2]`, and `paged_target()` masks to the same 16 bits.
- **Driven over every byte of the region**, the 9553 branch operands it finds
  produce **0** unresolvable targets (`None`) and **0** targets `>= 0x10000`.

So the check belongs **at the boundary that takes a caller's address**, which
is `print_helpers()`, beside the `site_rows()` call that is already there.
`walk_helper()` itself takes no new check, and `chain_from()`'s internal calls
pass for free — they are by construction in range. That is the concrete form of
the issue's *"say where the caller is checked"*.

### 4. The census's rows 15 and 16, measured against the code they describe

| | before | after |
|---|---|---|
| `walk_helper` `lo, _ = pd_bounds()` | `:344` | `:360`, `hi = min(hi, len(d))` |
| `walk_helper` stops | none | `:372` region end, `:378` template crossing it, `:392` instruction cut by it |
| `chain_from` `lo, _ = pd_bounds()` | `:516` | `:552`, `hi = min(hi, len(d))` |
| `chain_from` stops | none | `:557` region end, `:567` template crossing it, `:576` instruction cut by it |
| `print_helpers` caller check | none | `:909`, `check_site_addr()` per entry |

Three stops each, not two, because a template's length is known before its
first byte is read: a `mov rN,a` whose *next* instruction is cut by the end is
a different thing from a three-byte template that straddles it, and both are
one comparison off a length `_match_template()` has already returned.

`walk_helper()`'s new stops keep the `unmodelled:` prefix its third element
already uses, because that element is the row's **completeness flag** —
`write_helpers_csv()` writes `unmodelled=yes` from it, and `chain_from()` stops
a chain on a non-empty one. A walk that ran off the region is not a complete
decode, so it is flagged as one. `chain_from()`'s stops read in its own
prose style, next to the existing `f"{max_insns}-instruction window ended"`, so
a chain that left the region and a chain that hit its budget do not read alike.

The **clamp is `min(hi, len(d))`, not `hi` alone**, and it is not decoration.
On the committed image the region ends 65536 bytes before the buffer does, so
`hi` alone would be the only thing tested and the clamp would be untested. On a
truncated fixture the pre-change code raises `IndexError` from
`walk_helper(short, 0x1F8)` and from `chain_from(short, lo+0x1F8, …)`, and
`chain_from(short, lo+0x1F0, …)` reports `16-instruction window ended` for a
reason that has nothing to do with the end of anything. All three now stop at
the end and name it.

## The sibling, decided in the same pass

The issue asks which of the two answers applies to `site_rows()`
(`:684-686`, its `d[j:j + OPCODE_LEN[d[j]]]` listing loop, fed by
`i = lo + addr` at `:676` from the caller's `--sites` argument). **It is a caller error,
rejected at the CLI** — which is what `check_site_addr()` has already done for
`--sites` since #848 and now does for `--helpers` too. An out-of-region address
is not bytes to decode and label; it is a value with no file offset to read, and
the right response is to name the ranges and stop.

**The listing loop itself is deliberately left alone**, for a reason that is
specific rather than convenient. It is census row 10, which #848 closed with a
range check and *deliberately left the read side to the bytes*; and its
contract is a fixed `SITE_WINDOW`-long listing, which is exactly the mechanism a
misaligned anchor is caught by — `#848`'s own self-test pins
`--sites 0xFFFF` to still walk its whole window, last read at file `0x3000E`
and no higher than the `0x3002C` ceiling. Bounding that loop would move a pin
that exists to measure it. The contrast with the two walkers is the point and it
is a real one: `walk_helper` and `chain_from` walk until something *stops* them,
and a walk that stops nowhere is a listing with no end; `site_rows` walks a
window whose length is the contract, and its end is the answer.

`site_rows()` also keeps `lo, _ = pd_bounds()`; `hi` is not load-bearing in it.
That is unchanged and is not counted below as a fix.

## What this does not establish

- **Zero crossings still means "did not cross over these runs".** The bound
  rests on the `0xFFFF` measurement, which is a legal argument crossing *here*,
  on *this* image — not a claim that a count-only walk can always cross, and not
  a claim that the pre-change code would cross on another dump.
- **It is not "cannot raise".** The guards bound the two walkers' reads to
  `min(hi, len(d))`; nothing here is a statement about reachability of any
  *other* row of the census, and no site's behaviour on hardware is claimed,
  denied or discussed.
- **No live test ran.** No EC was opened, no register read back, no capture
  taken, no hardware and no Windows involved. Every number above is a static
  read of a committed file or the output of a command over one.
- **No `registers.yaml` status moved, and none could have.** Nothing here is
  about a register; this is Python walking a `bytes` object.
- **The self-test pins four facts, not a proof.** That `--helpers 0xFFFF` stops
  at the region end with the note naming it; that a `chain_from` fixture stops
  at the region end rather than at its budget; that a truncated fixture ends
  both walkers without either raising; and that `0x1FFE9` and `0x1FFFF` are
  each refused naming the region and both ranges. It does not pin that the
  wording is the best wording, and the first is pinned by count and offset
  rather than by the invariant, so a walk that stopped one instruction earlier
  would pass it.
- **A pre-existing suite failure is not this change's, and no suite was added.**
  `bash tools/run-tests.sh ec/tools` runs **29 suites, 960 tests** — the same
  totals `../../tools/README.md` already carries, because the four new cases
  went into this tool's own `--self-test` rather than into a committed
  `test_*.py`, and `tools/test_readme_suite_table.py` compares the discovered
  suite *set* against that table in both directions. That run reports
  `test_check_cluster_citations.py` FAILED on
  `docs/findings/xdata-cluster-names-guard-off-recipe.md:220` disagreeing with
  `ec/annotations/xdata-clusters.csv`. Both files are untouched by this change
  and the failing suite does not import the tool, so it fails at `HEAD` too.

## Three behaviour changes, each reported as a change

The plan's "nothing changed on the committed inputs" is true and is a `diff`,
not an impression: the pre-change file was extracted from `HEAD`, both copies
were run over the same image and the outputs compared. **Sixteen modes, all
byte-identical** — `--helpers`, `--helpers-csv`, `--bases`, `--bases all`,
`--strides all`, `--strides-csv all`, `--callers 0x0860`, `--callers-csv`,
`--accesses`, `--accesses-csv`, `--access-strides`, `--access-strides-csv`,
`--sites 0xFFF0`, `--sites 0xFFFF`, `--sites 0xC2FA 0xDA9B`, `--helpers 0x34D9
0x578E` — plus the existing byte-for-byte regeneration of all five committed
CSVs, which `--self-test` already asserts and which is what makes "no behaviour
changed on the committed inputs" a measurement rather than a claim.

The three that did move:

1. **`T --helpers 0xFFFF`**: 24 listing lines become 1, and the note changes
   from `unmodelled: 0xFFFF \`mov r7,a\` is outside the term model` to
   `unmodelled: walk left the pd-image at runtime 0x10000, its end at file
   0x30000`. **This is a correction, not a fix in the sense of a repair**: the
   other 23 lines were erased bytes presented as instructions, and printing them
   was the defect. It is still the one output that visibly changes, so it is
   named here rather than left for a reviewer to find.
2. **`T --helpers 0x1FFE9` and `T --helpers 0x1FFFF`**: a bare `IndexError`
   from inside the decode becomes the same `pd_index_geometry.py: error: …` and
   exit 2 that `--sites` has used since #848, naming the region and both ranges.
3. **`T --helpers 0x1FFE8`**: was **exit 0** with 24 listing lines of the same
   erased fill; it is now **exit 2** with the named range. Like
   `--sites 0x1FFF0` in #848, it was never a 16-bit runtime address on any
   target, only an unchecked one. It stays on the page because it is what the
   pre-change boundary pair was about.

**`T --helpers zzz` is a fourth, unremarkable side effect** and is recorded so
it is not left for a reviewer: the `try` that turns `check_site_addr()`'s
`ValueError` into `ap.error` also covers the `int(a, 16)` on the same line, so
a non-hex argument is now a diagnostic and exit 2 where it was an unhandled
traceback. Same failure mode, same place, strictly better — and the identical
trade #848 recorded for `--sites zzz`.

## What the census's table needs now

[`pd-sites-address-range.md`](pd-sites-address-range.md) measured
`grep -n 'lo, _ = pd_bounds()'` at **twelve** and called that #843's "the only
two" corrected. That count is now **eleven**, because the two this change fixes
are the two that were on it, and one function (`access_self_test`) moved the
other way when its `fixture()` closure was hoisted to module scope. The current
eleven, so a reader checking the older table knows what moved:

| line | function | the issue's narrower test |
|---|---|---|
| 669 | `site_rows` | the one that raised — row 10, `--sites` |
| 783 | `reaches` | no |
| 810 | `is_entry_shaped` | no |
| 831 | `caller_rows` | no |
| 899 | `print_helpers` | `--helpers`; `lo` is display-only, the check is at `:909` |
| 951 | `print_sites` | `site_rows()`'s caller; `lo` is display-only |
| 1009 | `write_helpers_csv` | no |
| 1110 | `access_frames` | no |
| 1261 | `access_rows` | no |
| 1446 | `access_self_test` | no |
| 1702 | `self_test` | no |

## Follow-ups this opens

- **The `site_rows()` listing loop (`:684-686`) is the remaining instance of this
  shape.** `--sites 0xFFFF` reads to file `0x3000E`, 14 bytes past the region's
  last byte, and this change deliberately left it. It is named here rather than
  left silent; the reason for not touching it is the second half of the sibling
  section above, and whoever picks it up needs to know that bounding it moves a
  self-test pin that exists to measure the read.
- **`--callers` takes caller addresses and still checks nothing.**
  `--callers 0x1FFFF` exits 0 and prints a three-row byte-scan caller list; it
  has no traceback to replace, and its output is the over-counting the module
  preamble already documents. It is the one remaining mode whose argument is a
  PD runtime address and whose contract is unstated. Recorded by
  `pd-sites-address-range.md` already; unchanged here, and repeated because a
  reader counting the argument-taking modes will land on it.
- **The rows that are not walkers.** Census rows 11, 12, 17, 18, 20 keep `hi`
  already and needed no decision; the table above is what a future sweep should
  re-derive rather than inherit.

## Reproducing it

From the repository root. The first two are the measurement that decides the
question, the third is the corrected output, and the diff pair is the evidence
that nothing on the committed inputs moved.

```sh
# the legal address that crossed, before and after. The extracted copy needs
# PYTHONPATH: outside ec/tools/ it cannot find disasm8051 and trace_xdata_refs.
git show HEAD:ec/tools/pd_index_geometry.py > /tmp/old-pd.py
PYTHONPATH=ec/tools python3 /tmp/old-pd.py ec/firmware/GMxMGxx_11.800 --helpers 0xFFFF
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --helpers 0xFFFF

# the refusals, the other mode
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --helpers 0x1FFE8   # exit 2
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --helpers 0x1FFE9   # exit 2
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --helpers 0x1FFFF   # exit 2

# the tool's own suite, and the runner
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
bash tools/run-tests.sh ec/tools

# the census's own arithmetic: hi - lo is the whole 16-bit space
python3 -c 'import sys; sys.path.insert(0, "ec/tools"); \
  import pd_index_geometry as T; print(hex(T.pd_bounds()[1] - T.pd_bounds()[0]))'

# the discard sites, eleven now and twelve in the table above
grep -n 'lo, _ = pd_bounds()' ec/tools/pd_index_geometry.py
```

`--helpers 0xFFFF` is the command to run first. The other five census commands
exit 0 and cross nothing both before and after, which is the zero this change
is *not* resting on.
