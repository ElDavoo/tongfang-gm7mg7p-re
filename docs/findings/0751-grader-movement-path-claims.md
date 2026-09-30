# A run that moved said "that is the 7 window(s) that were graded" under a count saying one of the 7 is a window of nothing (issue #551)

The write-up for [issue
#551](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/551), which is
about the two sentences `ec/tools/grade_0751_isolation.py`'s `moved_groups`
branch still carries unscoped on the two paths [issue
#725](0751-grader-moved-unplaced-scope.md) did not reach: the `if withheld:`
arm, whose "That is the {graded} window(s) that were graded" names a set that
holds an unattributed graded window, and the attribution underneath both
arms, which read the movement against the static prediction over the capture.
It is a disclosure change of the same kind as [#530's](0751-grader-unplaced-window-scope.md):
**no byte is read differently, no window is graded or withheld differently, and
no exit code moves** on any committed fixture. Nothing here is a register
behaviour and nothing here is evidence about the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §6 is the command the
operator runs, one invocation per value, and §7 is where the call is made.

It is the same paragraph [#530](0751-grader-unplaced-window-scope.md) opened,
which named the `moved_groups` arm and left it "for a fixture that reaches it
rather than written blind", and #725 closed for the one of its two sub-arms
where nothing was withheld. This closes the other, plus the sentence under
both. It is the sixth change in that paragraph, after
[`0751-grader-partial-grade-claims.md`](0751-grader-partial-grade-claims.md)
(#477), [`0751-grader-block-scope-claims.md`](0751-grader-block-scope-claims.md)
(#497), [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md) (#498,
landed as #502), #530 and #725.

---

## The defect, on a committed fixture with one row added

`0751-isolation-run-unread-window/` is §6's two-value day with two `restored
0x0751=0x99` marks in no block, one of which reads `'restored it somehow'`. The
run reports **8 marks, 1 withheld, 7 graded, and 1 of those 7 in no block**,
both blocks `intact`, and exits 1 on the unreadable label.
`0751-isolation-run-unplaced-window/` is the same day with both labels whole:
**8 graded, 2 in no block**, exit 0. `0751-isolation-run-3blocks-moved/` is the
only committed set where something moved at all, and it has
`graded_unplaced == 0`. **Neither fact pair meets in any committed fixture**, so
both paths below had no test on them.

Each is one row away, and the row is not invented: the address and step are
`3blocks-moved/`'s own, and `0751-isolation-example-active.csv` records the same
pair at the same byte.

    cp -r ec/tools/testdata/0751-isolation-run-unread-window /tmp/withheld
    sed -i 's/^\(2026-01-01T12:00:40\.000+01:00,MARK,,wrote 0x0751=0xA0\)$/\1\n2026-01-01T12:00:43.000+01:00,0x0784,0x50,0x28/' \
        /tmp/withheld/2026-01-01-0751-isolation-0700-07ff.csv
    python3 ec/tools/grade_0751_isolation.py /tmp/withheld/*.csv

    cp -r ec/tools/testdata/0751-isolation-run-unplaced-window /tmp/moved
    sed -i 's/^\(2026-01-01T12:00:40\.000+01:00,MARK,,wrote 0x0751=0xA0\)$/\1\n2026-01-01T12:00:43.000+01:00,0x0784,0x50,0x28/' \
        /tmp/moved/2026-01-01-0751-isolation-0700-07ff.csv
    python3 ec/tools/grade_0751_isolation.py /tmp/moved/*.csv

The `sed` inserts the row *below* the 12:00:40 write mark rather than appending
it, which is what keeps the capture in timestamp order; the tool reads
timestamps and not file order, so the position is only what makes the file
readable. #725 measured the append instead and got the same report.

"Before" is the tool at `126a67c8`, this branch's merge base with `main`; the
lines below are `git show 126a67c8:ec/tools/grade_0751_isolation.py` on those
two commands. **Shape (b), `unread-window/` with the row** — the `if withheld:`
arm, and the issue's `:2045`:

```
=== what this does and does not settle ===
  1 of the 8 window(s) above were not graded: ...
  ...
  1 of the 7 graded window(s) above are in no block: ...
  At least one of the §4.1-§4.3 bytes moved after a mark: PL1/PL2/PL4 (§4.1).
  That is the 7 window(s) that were graded. The 1 window(s) withheld above are not part of it, and what they would have shown is not reported here.
  That contradicts the static prediction in ec/annotations/manual-fan-ctrl-0751.md §5 if it is the PLs, or §4.2 if it is the fan table -- capture it in full, it is the more interesting outcome.
```

The `...` on its own line is the one line elided whole — "A mark this cannot
read is a mark no block can be attributed to …", the unreadable-label refusal,
which is unchanged boilerplate between the two counts and nothing turns on it.
The other two `...` are the tool's own, truncating the two count lines.

The `7` on the fourth line is a window the third line has just said is a window
of no value under test. That is the shape [#530](0751-grader-unplaced-window-scope.md)
removed from the no-movement chain one branch over, left standing here.

**Shape (a), `unplaced-window/` with the row** — the attribution, and the
issue's `:2076`:

```
=== what this does and does not settle ===
  2 of the 8 graded window(s) above are in no block: ...
  At least one of the §4.1-§4.3 bytes moved after a mark: PL1/PL2/PL4 (§4.1).
  That is the 8 window(s) that were graded. The 2 in no block are part of it, and this run cannot say which arm they are a window of. The static prediction is a claim about the whole capture, and this output does not make it over a run in which 2 of its 8 graded window(s) are in no block.
  That contradicts the static prediction in ec/annotations/manual-fan-ctrl-0751.md §5 if it is the PLs, or §4.2 if it is the fan table -- capture it in full, it is the more interesting outcome.
```

**This one is a defect #725's fix created.** Its `elif graded_unplaced:` arm
put "this output does not make it over a run in which 2 of its 8 graded window(s)
are in no block" on the line above a sentence that made the call anyway — the
scope and the claim, one line apart, disagreeing.

Both are the disclosure-contradicts-the-claim shape, and neither is a wrong
figure: the counts were right before and are right after.

## The decision, and the one it could not make

The issue asks for an explicit decision at the branch. **The movement path keeps
the observation and the advice and drops the whole-capture call**, on any run
where `graded_unplaced > 0` — the option the issue names second, and the one the
no-movement chain already takes. It is not available in the other form, and
the reason is #725's, which this change re-derives rather than assumes:

> **`moved_groups` is a union of group *names* over `shown` and carries no window
> identity.** The same `0x0784` row produces a byte-identical closing section
> whether it lands in block 1's write window or in the 12:00 stray.

Measured again here rather than cited, because it is what decides both hunks.
Same recipe over `unread-window/` with `12:04:05` instead, which is inside the
12:04 stray — the one that parses, and so is graded rather than withheld:

    cp -r ec/tools/testdata/0751-isolation-run-unread-window /tmp/stray
    sed -i 's/^\(2026-01-01T12:04:00\.000+01:00,MARK,,restored 0x0751=0x99\)$/\1\n2026-01-01T12:04:05.000+01:00,0x0784,0x50,0x28/' \
        /tmp/stray/2026-01-01-0751-isolation-0700-07ff.csv
    python3 ec/tools/grade_0751_isolation.py /tmp/stray/*.csv

    same marks, same block structure, same `PL1/PL2/PL4 (§4.1)`, same
    `1 of the 8` / `1 of the 7` counts, same exit 1 -- and the closing
    sections are byte-identical.

Three consequences, in the order they bound each other:

1. **The movement line itself is not narrowed, and must not be.** "At least one
   of the §4.1-§4.3 bytes moved after a mark" is a positive fact over the
   windows printed, and `placed = graded - graded_unplaced` is not a set it can
   be stated over: if the row landed in the stray, the placed windows show
   nothing moving, so "…moved in any of the 6 windows that belong to a value
   under test" would be false on one of the two placements the tool cannot
   distinguish. Nothing in this change reaches that line.
2. **The withheld arm does not get `placed` either.** Its "That is the N
   window(s) that were graded" is the movement's denominator, and the
   unattributed windows are *in* it. What is sound is what the branch already
   does — keep the true denominator, and name the withheld windows as outside
   the set, which is true **by construction**, since a withheld window never
   reaches `report_window` and so cannot have fed `moved_groups` — plus the
   clause naming the unattributed windows as part of it, with the reason their
   arm cannot be named. The contradiction goes by disclosure rather than by
   narrowing a set the movement cannot be placed in.
3. **The attribution takes the no-movement arm's declined form.** "That
   contradicts the static prediction … §5 if it is the PLs, or §4.2 if it is the
   fan table" is kept as an observation over the windows this run read, and
   "capture it in full, it is the more interesting outcome" is kept because it
   is advice and not a claim. The whole-capture reading of "contradicts" is
   what goes.

## What the two sentences read after

Shape (b), the withheld arm — one sentence, both exclusions named, neither
subtracted:

```
  That is the 7 window(s) that were graded. The 1 window(s) withheld above are not part of it, and what they would have shown is not reported here. The 1 graded window(s) in no block are part of it, and this run cannot say which arm they are a window of.
  That contradicts the static prediction in ec/annotations/manual-fan-ctrl-0751.md §5 if it is the PLs, or §4.2 if it is the fan table -- over the 7 window(s) above, not over the capture as a whole: 1 of them are a window of an arm this run cannot name. Capture it in full, it is the more interesting outcome.
```

Shape (a), the attribution — over the 8, with the 2 named:

```
  That contradicts the static prediction in ec/annotations/manual-fan-ctrl-0751.md §5 if it is the PLs, or §4.2 if it is the fan table -- over the 8 window(s) above, not over the capture as a whole: 2 of them are a window of an arm this run cannot name. Capture it in full, it is the more interesting outcome.
```

**Scoping is not retracting.** A PL that moved is still the more interesting
outcome on either reading, and the advice to go and capture the day is the same
sentence it was. What changed is which set "contradicts" is a claim over.

## Why the new branch sits where it does

After the `moved_groups == [TRIGGER_GROUP]` split, not before it. That
sentence says *what* moved — a mailbox poke rather than a table move — and says
on static evidence why, which is a claim over the row that moved and not over
the capture; it is also the only attribution in the branch, and taking it on a
partly-unattributed run would trade it for a second copy of the scope already
printed one line above. The plain `else` below the new branch is left **byte
for byte**, and it is the one every committed set with a movement takes.

The `elif graded_unplaced:` above it is left byte for byte too. The two do not
compose into a case: a run that both withheld a window and graded an
unattributed one takes `if withheld:` and gets #530's clause, which names both
kinds of excluded window in one sentence, and this one is the attribution's
scope rather than the movement's. That is the run shape (b) above, and it is
why shape (b) prints a differently-scoped attribution from shape (a) rather
than the arm and the attribution disagreeing with each other.

The withheld arm's clause is behind `if graded_unplaced:` for the same reason
every other clause in the section is: a run with no unattributed graded window
takes the `else` and the bytes are the ones the tree already pinned.

## Why no new `testdata/` fixture

**This is the one place the issue was read against its letter, and it is worth
naming in a review rather than leaving to be discovered.** The issue asks for
two committed directories under `ec/tools/testdata/`, registered in
`ec/tools/testdata/README.md`. Both cases are *one row in one capture* from a
committed set, which is exactly what `copies_of`'s docstring reserves a
temporary copy for:

> a case that is about one row in one capture is a property of that row rather
> than a second shape of the day.

#725 argued this on this exact paragraph, was merged on it, and its write-up
has the section. Both new tests build their run with `copies_of` +
`insert_after`, and the three-command recipe above reproduces either shape from
the committed bytes, offline, with no new directory.

**What that leaves out:** the two directories and the two `testdata/README.md`
rows the issue asked for. `check_testdata_index.py` *requires* a row for a new
directory, and three sibling issues in this family may each want one. If the
human who filed it wants them on disk instead, that is mechanical and nothing
in the tool change or the assertions depends on which reading is taken: copy
the two sets, add the row, and point the two tests at the paths in place of the
helper calls.

The two rows in `testdata/README.md` that describe the `moved_groups` chain's
`elif graded_unplaced:` arm as reached "only over a copy of this set with one
`0x0784` row added, not by a committed run" are **not** edited, and stay true
— the tests still build copies in a temporary directory. No row was touched.

## What is pinned

`python3 ec/tools/test_grade_0751_isolation.py` — 144 tests on this branch's
merge base, 146 after, all green.

| test | what it holds |
|---|---|
| `test_a_movement_beside_a_withheld_window_names_the_unattributed_ones` | `unread-window/` with one `0x0784` row, three legs. **First**: rc 1; the banner's `1 of the 8` and the count's `1 of the 7`; the movement line unchanged at `PL1/PL2/PL4 (§4.1)`; the withheld window still named outside the set with the "not reported here" refusal; the new clause naming the 1 unattributed window as part of it; **both** negatives — `That is the 6 window(s)`, the figure a `placed` narrowing would print here, and `belong to a value under test`, the phrase the no-movement withheld branch narrows with — and the scoped attribution, plus `Capture it in full, it is the more interesting outcome.` still printed and `host-written reload mailbox` still absent. **Second (the load-bearing one)**: the same copy with the row at `12:04:05`, inside the 12:04 stray, and the two closing sections asserted **equal**. **Third**: `--block 0xA0` over the first copy, rc 1, the per-block sentence at its 3 windows, and both new clauses absent |
| `test_a_partly_unplaced_movement_declines_the_capture_comparison` | `unplaced-window/` with the same row, two legs. **First**: rc 0; #725's scope line unchanged and still declining; the attribution's new scope over the 8 with the 2 named; `Capture it in full, it is the more interesting outcome.` kept; `fan table -- capture it in full` absent, which is the string the un-scoped sentence had; `host-written reload mailbox` absent. **Second**: the row at `12:00:05`, inside the stray, closing sections asserted **equal** |

Both new tests **fail against the tool as merged**, on the two clauses and
nothing else — as does #725's own test, whose
`assertIn('That contradicts the static prediction', out)` asserted the
capture-level reading that no longer prints and now holds the scoped sentence.
That third failure is the point, not an accident: #725's test was passing while
asserting a sentence the line above it contradicted.

The placement equality is what makes the wording decision visible to a test
rather than to a reader. On both shapes a narrowing to `placed` is true of the
first placement and false of the second, and the two must print the same bytes.
`#725`'s test already pins that equality for the scope line on shape (a); both
new tests run it again, because a narrowing is equally available on the
withheld arm and on the attribution, and would be just as false in the second
placement.

## What must not change, and did not

Measured rather than asserted. This branch's tool and
`git show 126a67c8:ec/tools/grade_0751_isolation.py` were run over **every**
`ec/tools/testdata/0751-isolation-run*/` directory four ways — unscoped, and
`--block` at each of `0xA0`, `0x10` and `0x00` — and all **48** pairs of reports
were diffed. **All 48 are byte-identical and no exit code moved.**

```
git show HEAD:ec/tools/grade_0751_isolation.py > /tmp/before_tool.py
for d in ec/tools/testdata/0751-isolation-run*/; do
  for mode in "" "--block 0xA0" "--block 0x10" "--block 0x00"; do
    python3 /tmp/before_tool.py $d/*.csv $mode > /tmp/b.out; echo "rc=$?" >> /tmp/b.out
    python3 ec/tools/grade_0751_isolation.py $d/*.csv $mode > /tmp/a.out; echo "rc=$?" >> /tmp/a.out
    diff /tmp/b.out /tmp/a.out || echo "DIFFERS: $d $mode"
  done
done
```

(48 is 12 directories × 4: the eleven `0751-isolation-run-*` sets plus
`0751-isolation-run/` itself, which is what `0751-isolation-run*/` matches.)

That number is the whole claim. Every committed set has `graded_unplaced == 0`
on the movement path — `3blocks-moved/` is the only one that moves and it has
none — so both new clauses are unreachable over committed bytes; and
`unplaced-window/` and `unread-window/` move nothing, so the `moved_groups`
branch is not entered at all over them. **If any pair had differed, a branch
would be reaching further than intended and this change would be wrong.**

The two tests the issue asks to be shown unchanged are, and their runs are the
`unread-window/` and `unplaced-window/` unscoped pairs of the 48 above —
byte-identical before and after, which is the demonstration rather than the
assertion, since the new clauses sit behind `if graded_unplaced:` and a
committed run never takes them:

* `test_a_withheld_window_in_no_block_claims_no_block_was_refused`
  (`unread-window/`, 1 withheld, 7 graded, 1 in no block) still reads
  "None of the §4.1-§4.3 bytes moved in any of the **6** window(s) that were
  graded and belong to a value under test … neither the 1 window(s) withheld
  above nor the 1 graded window(s) in no block are part of it". That is the
  **no-movement** withheld arm, which this change does not touch, and it
  narrows to `placed` for the reason above: there is no movement to place, and
  the tool is reporting what the placed windows show rather than asserting one
  of them moved.
* `test_a_window_in_no_block_whose_marks_agree_is_not_refused`
  (`unplaced-window/`, nothing withheld, nothing moved) still exits 0, refuses
  nothing, and reads "None of the §4.1-§4.3 bytes moved in any of the **6**
  window(s) that belong to a value under test … the 2 graded window(s) in no
  block above are not part of it".

Both take the no-movement chain, where a narrowing is the whole point; the
branch this change is about is the one where a narrowing would be a sentence
about a set the movement cannot be said to have moved in.

`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` is not touched: §6's
fenced file list and `0751-isolation-run/` are held equal by the suite, no
fixture was added, and §6's command line is unchanged. A `--block` run still
gets the per-block sentence, as both new tests' third legs show.
`ec/README.md` is not touched: its entry describes `--block` scoping and the
dump groups, not the closing section's cases, so nothing there goes stale —
and leaving it alone is one fewer shared file open against the other agent PRs.

## One suite outside the gates goes red on this change, and it is not a claim

**Read this before deciding the change is cheap.** Adding tests to
`ec/tools/test_grade_0751_isolation.py` moves the lines every committed
citation *into that file* lands on, and
`ec/tools/test_census_test_line_pins.py`'s
`test_the_committed_counts_are_the_ones_the_write_up_publishes` holds the
aggregate of exactly that:

```
FAIL: AssertionError: {'def test_': 1, 'assertion': 19, 'comment': 28,
                        'blank': 5, 'other': 46}
                    != {'def test_': 1, 'assertion': 24, 'comment': 23,
                        'blank': 5, 'other': 46}
```

Measured, not guessed. Both trees censused with
`census_test_line_pins.py`'s own `census()` and compared record by record:

| axis | merge base | this branch |
|---|---|---|
| resolving pins / declined | 99 / 33 | 99 / 33 |
| `out-of-range`, `unresolved-path`, `ambiguous-path` | 0 / 0 / 0 | 0 / 0 / 0 |
| distinct `(file, line)` pairs | 74 | 74 |
| shape split `assertion` / `comment` | 24 / 23 | 19 / 28 |

Every row of that table, and the 15 below it, is what this prints — the census
reads a tree from the filesystem rather than from git, so the merge base is
unpacked rather than diffed, and both trees get the same tool and the same
exclusions (`.git/`, `vendor/`, `.claude/`, and the census's own write-up):

```
rm -rf /tmp/pin-base && mkdir -p /tmp/pin-base
git archive 126a67c8 | tar -x -C /tmp/pin-base

dump () {  # $1 = tree root, $2 = where the per-pin record map goes
  python3 -c "
import json, sys; sys.path.insert(0, '$1/ec/tools')
import census_test_line_pins as c
records, _ = c.census(c.REPO)
json.dump({f'{r[0]}:{r[1]} {r[2]}': [r[3], r[4], r[6], r[2].rsplit(':', 1)[1]]
           for r in records}, open('$2', 'w'), indent=1, sort_keys=True)"
}
dump /tmp/pin-base /tmp/pin-base.json
dump .          /tmp/pin-head.json

python3 - <<'PY'
import collections, json
base = json.load(open('/tmp/pin-base.json'))
head = json.load(open('/tmp/pin-head.json'))
for name, tree in (('merge base', base), ('this branch', head)):
    live = {k: v for k, v in tree.items() if v[0] == 'resolves'}
    print(f"{name}: {len(live)} resolving, "
          f"{sum(1 for v in tree.values() if v[0] == 'declined')} declined, "
          f"{len({(v[1], v[3]) for v in live.values()})} distinct (file, line) "
          f"pairs, {dict(collections.Counter(v[2] for v in live.values()))}")
moved = [(k, base[k][2], head[k][2]) for k in sorted(base)
         if k in head and base[k][2] != head[k][2]]
for k, b, h in moved:
    print('   moved', k, f'{b} -> {h}')
net = collections.Counter(h for _, _, h in moved)
net.subtract(b for _, b, _ in moved)
print(f"{len(moved)} moved; net", {k: v for k, v in net.items() if v})
print('every one into the grader suite:',
      all(head[k][1] == 'ec/tools/test_grade_0751_isolation.py'
          for k, _, _ in moved))
PY
```

**Only the shape split moved**, and every pin whose landing shape moved is one
into the grader suite — **15** of them, and the net is `assertion -5`,
`comment +5`, `other` and `blank` and `def test_` unmoved. Every pin still
*resolves*, to the same file and the same cited line; what moved is which line
of that file the number now lands on. `ec/tools/check_pin_table_rows.py` names
all 15 on its own, as `shape-differs` rows 1302, 1306, 1341-1344, 1358-1362 and
1365-1368 of `docs/findings/test-line-pin-census.md`; it asks a different
question — reconciling the committed per-pin table row by row, rather than
totalling the shapes — and it **loads** the census rather than restating it, by
its own docstring's design, so this is a second path to the same 15 and not a
second opinion. It prints 0 `shape-differs` on the merge base.

**The figure is not re-derived here, on purpose.** `CLAUDE.md`'s
"No hand-kept totals in prose" is explicit about this shape — *"a test that
asserts a count of the tree is a value every merge has to edit … Assert the
claim, not the census"* — and this is that test. The alternative is re-deriving
the census, and that is not a one-number edit: the 15 rows
`check_pin_table_rows.py` names above carry a `shape` cell in
`docs/findings/test-line-pin-census.md`'s per-pin table, and the write-ups that
cite those lines carry the `file:NNN` spelling, so the two move together or the
re-registration is fiction. It is its own piece of work and it belongs in its
own change, where the write-ups can be read.

The suite is not in any gate, and says so itself:
`test_the_tool_is_not_in_the_cheap_gate` asserts
`census_test_line_pins.py` is absent from `.github/scripts/agent-gates.sh`,
`tools/README.md` marks `test_check_pin_table_rows.py` "**Not in any gate**",
and `.github/scripts/agent-gates.sh` passes with this change in the tree. It is
a census, by its own docstring: "a census and not a check … it exits 0 on a
tree where every pin is wrong."

Nothing here is weakened to make it pass. Nothing was edited in that suite, in
the census, or in any write-up's citations.

## Left out on purpose

- **The module docstring's other three closing-section paragraphs.** Only the
  fourth-case paragraph was wrong — it claimed the section "declines the
  capture-level comparison over the rest", which was true of the "nothing
  moved" reading and not of the "something moved" one. It now says which is
  which. The three before it describe `withheld`, which this change does not
  move.
- **The `UNPLACED_GRADED_NOTE` count line, the no-movement chain, and the
  trigger-group split** — unchanged, and the 48-pair measurement is what would
  notice.
- **`docs/findings.md`** — frozen at §97. A new write-up is a new file and
  nothing else; `check_findings_frozen.py` holds it, and
  `gen_findings_index.py` regenerates `docs/findings/INDEX.md`.
- **`ec/annotations/registers.yaml`** — this is not a register-status change.
  `MANUAL_FAN_CTRL` stays `present-untested` and its `static_refs*` counts stay
  29/29/0. **There is no row edit to look for — none was missed.** There is no
  register behaviour anywhere in this.
- **`ec/annotations/manual-fan-ctrl-0751.md`** — §5 and §4.2 are quoted by the
  sentence this change scopes, not restated or re-derived here.
- **#724, and the overlap with it.** #530's write-up assigns the withheld half
  of the movement line to
  [#724](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/724), and
  #725's leaves it there too, "a different sentence with a different fix". This
  branch carries that hunk, so the two overlap by one clause. **If #724 lands
  first, drop the withheld-arm hunk and its first leg** — the attribution's
  branch, the comparison test, and the 48-pair measurement stand alone without
  it, and the shape (b) recipe above is still the reproduction. Flagging it here
  so it can be cut cleanly rather than found in review.
- **#515, #541, #539, #546** — the issue names them for context. Read for
  fixture convention; none is fixed, duplicated or closed here.

## **None of this is a live test.**

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the commands above against the revision each
transcript names, and with the tests named. No live run, no register readback,
no hardware observation; no line of this change may be read as a report of a
capture, and none is one. `0x0784` is a row in a file someone wrote by hand, and
the `0x50 -> 0x28` step is the step `0751-isolation-example-active.csv` records,
not a measurement of this machine's PL bytes. `confirmed-inert` is §7's call,
made by a human holding the rest of the notes, and nothing here bears on it
either way.
