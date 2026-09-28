# Which of the two refusals names a file that is both (issue #784)

The write-up for [issue
#784](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/784), which asks
which of the grader's two file-level refusals names a capture that is *both*
byte-order-marked and not utf-8-decodable, and to make the two callers take
that order rather than each keeping whichever `if` was written first.

It sits beside the two write-ups that own the sentences it orders —
[`0751-capture-encoding.md`](0751-capture-encoding.md) (#748, which owns the
decode refusal) and [`0751-capture-row-shape.md`](0751-capture-row-shape.md)
(#750, which owns `bom_refusal` and the mark). Its subject is the order
*between* their two claims, and nothing here re-decides either one.

**Offline throughout.** No EC, no laptop, no Windows box was reached, and no
capture was taken. Every figure below is this tree's own Python reading bytes
this repository wrote into a `tempfile` directory. That an operator can
produce such a file is a claim about what a spreadsheet export or an editor
saves, not a case measured here.

## The defect, on a fixture

Four bytes in, and the two readers said two different things. The fixture is
the issue's, byte for byte, plus a header:

```python
b'\xef\xbb\xbf' + b'ts,addr,old,new\n' \
  + b'2026-01-01T12:00:00.000+01:00,MARK,,caf\xe9\n'
```

Before the change, on that file:

```
read_capture           -> ValueError: <path>: starts with a byte-order mark, so its
                           first field is '﻿ts' and not 'ts'. A capture is utf-8
                           with no BOM; re-save this one without one.
existing_mark_findings -> refused: (None, "the grader's reader cannot decode a byte of
                           this file in the utf-8 a capture is defined to be, and
                           raises before it reaches a row: 'utf-8' codec can't decode
                           byte 0xe9 in position 58: ...")
```

Two sentences, two remedies, and they disagree about what is wrong with the
file. The strict reader's says *remove the mark*; the notice's says *re-save it
as utf-8*, over a file the first sentence has just called valid utf-8. An
operator reading the notice is handed a remedy for a fault that sentence above
it says is not the fault.

The cause is not a bug in either branch. It is that each branch is a
single-condition test over one buffer, so **nothing forced an order on either
side**: `read_capture` has to know about the mark before it reads a row, and the
notice's reader has the whole buffer already and takes the refusals in the order
they were added. The two branches landed the same day, 2026-09-25, in
`43241736` (the mark, #761) and `c9e72c15` (the decode failure, #718), so this
is two changes each correct alone and not a history of drift.

## The decision: the mark first, on both sides

The principle, which is a property of the code rather than a preference about
remedies: **the mark is a fact about the file's first three bytes**,
decidable without the file decoding at all, and it is the check the strict
reader has to make *before it reads a row*. That is why `path_starts_with_bom`
is its own three-byte `open`, and why `normalised_rows` strips the mark such
that a reader downstream of the stream cannot see it. The decode failure is the
fact that costs the whole buffer. Cheaper and always-decidable goes first on
both sides.

So the change is one reorder: `existing_mark_findings` now tests `capture_snapshot`'s
`has_bom` before `decode_failure`. `read_capture` is untouched in behaviour and
says in its docstring that the precedence is a rule rather than a position.

## The four fixtures, before and after

Measured on this tree, on the same four hand-written fixtures, with the
containment column kept because the decode refusal is held to *containment*
and not equality by an existing case
(`test_grade_0751_isolation.py`'s
`test_a_byte_this_python_cannot_decode_reports_the_verdict_it_observed`
asserts `assertIn(str(raised), refused[0][1])` — there is no sentence of its
own for the strict reader to be equal to, because it raises a bare
`UnicodeDecodeError`).

| fixture | before | after | exactly equal, after |
|---|---|---|---|
| **A.** BOM + cp1252 `é` (the issue's case) | `bom_refusal` / wrapped decode sentence | `bom_refusal` / `bom_refusal` | **yes** |
| **B.** BOM only, decodes | `bom_refusal` / `bom_refusal` | unchanged | yes |
| **C.** cp1252 `é` only, no BOM | bare `UnicodeDecodeError` / wrapped decode sentence | unchanged | no — *by design*, and by the containment contract |
| **D.** BOM + a bad hex row (decodes) | `bom_refusal` / `bom_refusal` | unchanged | yes |

Only the both-case changes. C is untouched, and the two cases that were
already right stay right.

## The two shapes that were rejected, and the measurements that rejected them

**Option 1 — move `path_starts_with_bom` after the decode in `read_capture`,
so the codec is named first and the mark second.** Measured by applying it to
a scratch copy and replaying the same four fixtures:

| fixture | under option 1 | why that is worse |
|---|---|---|
| A | `read_capture` raises a bare `UnicodeDecodeError`; the notice still says the decode sentence | still not equal, and the issue's first Done-when asks for equality |
| B | `bom_refusal` / `bom_refusal` | no change |
| C | unchanged | no change |
| D | `read_capture` says `invalid literal for int() with base 16: '0xzz'`; the notice says `bom_refusal` | **a new disagreement on a case that was correct** |

D is the disqualifier. Under this option the mark check no longer
short-circuits ahead of the row pass, so a BOM'd file with an ordinary bad row
gets the hex complaint from the grading and the mark sentence from the notice —
the same class of defect this issue is about, introduced on an input that did
not have it. A is the second disqualifier: the decode contract is containment
on purpose, and making decode equal too would contradict the existing case
above.

**Option 3 — fold the two into one refusal naming both facts.** This makes
disagreement impossible by construction and is the shape with the smallest
question attached, but it costs more than the defect:

- `bom_refusal` takes a second argument, which breaks the
  `assertIn(grader.bom_refusal(str(out)), notice)` shape in
  `windows/tools/test_ec_watch.py` — the thing that is currently holding a
  copy of the sentence out of `ec_watch.py`, and the reason the sentence is a
  function at all.
- For `read_capture` to name the decode failure it would have to decode the
  whole buffer up front, abandoning the laziness `capture_rows` documents ("a
  generator rather than a list, so laziness still holds and an undecodable
  byte comes out of the loop at its row") and adding an `open` site to a tree
  that counts them (`check_site_census.py`).

The issue preferred the codec first. That cannot be had without the D
regression, and the table above is the measurement rather than the argument
for saying so.

## The cost, stated rather than hidden

On a file that is both, an operator reads the mark sentence first and meets
the codec second, after re-saving. **Both sentences stay true of the file the
whole time** — the mark is in it and the undecodable byte is in it, and the
lenient reader still lists every mark with U+FFFD where the byte was. What
the change buys is that the notice and the grading stop being *inconsistent*,
not that the operator is told less. The notice names the mark, the operator
re-saves without it, and the next run reaches the codec.

## The contract was unverified at exactly the input where it was false

`bom_refusal`'s docstring claimed "the warning an operator reads and the error
the grading raises are one verdict, not two that have to agree". Measured on
the tree before this change, three fixtures in the tree wrote `EF BB BF`:

- `test_a_byte_order_mark_does_not_turn_the_header_into_a_bad_row`
- `test_a_leading_bom_is_refused_by_name_and_not_as_a_bad_hex_row`
- `windows/tools/test_ec_watch.py`'s
  `test_a_bom_is_refused_by_name_and_gets_the_same_remedy`

**All three decodes cleanly.** The two latin-1 fixtures on either side of them
carry no mark. So the equality the docstring claimed was only ever *exercised*
on the one-condition input, and the case that asserts it
(`assertEqual(refused[0][1], message)`) passed because its fixture was a BOM'd
file that happened to be otherwise perfect. The contract was true on every
input the suite happened to build and false on the one an operator can
produce.

A fourth case now closes it, **beside** the existing one rather than as a second
fault folded into it — the existing case is named for the *header* not
being refused as a hex complaint, which is a claim about a file with one
fault, and giving it a second would make that name false and would drop the
coverage of "a BOM'd file that is otherwise perfect" (fixture B).
`test_a_marked_and_undecodable_file_is_refused_by_the_mark` seeds both faults,
asserts the equality, and carries a **control**: the identical bytes with the
three mark bytes removed must give the decode refusal instead. Without the
control a reader that refused every file with a reason would be green, and the
order would be a coincidence rather than the assertion it is.

Where the two new cases sit in their files is deliberate. Prose across
`docs/findings/` pins lines of both suites by number, and a first draft that
put them next to the cases they extend added about a hundred lines mid-file in
the grader suite and about sixty in the notice suite, which moved every pin
below them onto a different line. So the grader's case is the only method of
`MarkBeforeCodecTests`, a class at the end of the file that borrows
`count_opens` from `ExistingMarkLabelTests`, and the notice's case follows
`test_the_reader_is_the_graders_own`, the last pinned test of its class.

The notice suite gets the same input, and **the existing assertion holds**:
`test_a_bom_is_refused_by_name_and_gets_the_same_remedy`'s
`assertIn(grader.bom_refusal(str(out)), notice)` is true on a file carrying
both, so it is kept rather than replaced. The new sibling adds the half that
was false — the decode sentence is *absent* from the notice.

## The two-moments question is not this one

[#767](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/767) is about a
file moving *between* reads. This change is entirely within one read of one
buffer, so it neither fixes that nor worsens it: `capture_snapshot` still
opens the file once, and the new case asserts it — the mark is asked of the
buffer that read had to have anyway, and `path_starts_with_bom` remains
`read_capture`'s own three-byte open rather than a third read. The sibling
`test_the_capture_is_opened_once_on_both_paths` is unchanged and still green.

## One pre-existing condition, reported and not fixed

It is on the merged tree **before** this change, measured by reconstructing
the pre-change files and running the same tool over both. The tool is not a
gate, so it does not turn red either way, and this change is not where it is
repaired.

**`ec/tools/measure_mark_provenance.py`'s `CITATIONS` table is already
stale, and this change adds to it.** The tool exits 1 at `f173d570`, this
branch's parent, with 18 drifted line pins; at this change's own first commit,
`121791da`, it exits 1 with 20. The pin the issue
names — `("ec/tools/grade_0751_isolation.py", 886, "if path_starts_with_bom(path):")`
— is 156 lines off *before* this change (the content was at 1042) and 176 off
after. The other new one is a pin into `windows/tools/ec_watch.py` that this
change's docstring edit moved. Re-pinning is **out of scope deliberately**:
the pins are wrong by different amounts, and repairing the two this change
touches would make a table with eighteen wrong entries look maintained when it
is not. This is a finding about a stale census, not a licence to add to it.

That one is a table the census tool reports and no gate reads. Two others are
gates, and this change did touch them, so they are stated here and not as
conditions it inherited:

- **The line-pin census can turn red from a change like this one.**
  `ec/tools/test_census_test_line_pins.py` asserts the shape split of the pins
  it resolves, which is a value of the tree, and a first draft of this change
  moved four pins into the grader suite from `assertion` and `other` shapes
  onto `comment` and `other`, so the suite failed where it had passed on the
  base. Placing the new cases after the last pinned line of each file, as
  above, leaves the split where it was: the suite is green here without an
  edit to any of its counts.
- **`docs/findings/INDEX.md` is generated**, and `gen_findings_index.py --check`
  is a gate. The row for this write-up is added by regenerating the file, and
  the check exits 0 on this branch. On the base the committed count and the
  generator agreed; a hand-added row without the regenerated count is what the
  check catches.

## How to re-check this

```console
python3 ec/tools/test_grade_0751_isolation.py ExistingMarkLabelTests MarkBeforeCodecTests
python3 windows/tools/test_ec_watch.py AppendNoticeTests
python3 -m unittest ec.tools.test_census_test_line_pins
python3 ec/tools/gen_findings_index.py --check
bash tools/run-tests.sh
```

**The evidence is the four-fixture table above, not the pass count.** The
fixtures are `tempfile` files this checkout wrote. No laptop, no Windows box,
no capture and no register was involved, and nothing here should be read as a
live observation.

## What this leaves open

- The operator still has to re-read a both-case file twice. Both sentences are
  true of it, so this is a cost of *ordering* rather than an information loss,
  but a single refusal naming both would be better and is the shape rejected
  in §above for the two reasons given there.
- `ec/tools/check_capture_encoding.py` happens to agree with this order and
  says nothing about it: it is a corpus-wide census whose `classify()` returns
  both facts together and whose `report()` prints the BOM before the decode
  problem, and it refuses nothing per-file with `bom_refusal`. So there is no
  second verdict here to keep in step — a coincidence, not a contract, and
  nothing was edited to make it one.
- Whether the format should ever *accept* a BOM. Unchanged by this: #748
  decided the codec and #750 made the mark a refusal, and this orders two
  refusals that already exist.
- Whether the open count in `measure_mark_provenance.py`'s table is worth
  re-deriving at all, as a question about pinning a line number into a file
  that keeps growing rather than as a task to fix twenty lines.
