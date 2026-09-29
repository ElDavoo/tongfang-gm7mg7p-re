# §4.6's second precondition, stated when nothing names the value that was written (issue #387)

The write-up for [issue
#387](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/387), which follows
#202 from the same chain. #202 made §4.6 *a coverage statement before it is a
comparison* and added a line for the half that fails first: when the last
`--dump` does not reach `0x0751`, the section says the readback was not taken.
The other precondition of the same comparison was still met with a bare
`return`, so a run that got past the coverage half and had nothing to compare
the byte against ended the section on a bare `0x0751 = 0xNN` row with nothing
saying the comparison was not taken. This closes that, and the close is one
`print`.

**Offline throughout, and nothing here is a claim about the machine.** No EC
was read, no §3 run was performed, no laptop or Windows box was reached, and no
register was observed. The whole of the evidence is this tree's Python printing
sections over the committed fixtures in `ec/tools/testdata/` and over
hand-written dump lines in a `tempfile` directory. The fix is about which files
and which numbers were handed in.

---

## The two preconditions, and which one was checked

§4.6's readback is a comparison, and a comparison needs two sides. The tool
prints the byte from the block's last `--dump`; it needs a written value to
compare it against, and the value is not in the dump — a dump is a whole-range
read with no marks in it (`docs/findings/0751-grader-block-scoping.md` owns
that argument). It comes from one of three places, and the tool has a name for
each:

| source | where it is read | what the report says |
|---|---|---|
| the block's own value, from the `<value>` in a §6 file name | `dump_block` (`:2663`) | `block 0xA0, from the <value> in these files' §6 names` |
| `--wrote` | the command line, `:2856` | `from --block/--wrote; these files carry no <value> of their own` |
| `--block` | the command line, via the same fallback | as above |

What the branch looked like, at `report_readback` (`:2809`):

```python
    if here[-1][1].get(MANUAL_FAN_CTRL) is None:      # :2844, the coverage half
        print("  the last --dump does not cover 0x0751, so the §4.6 readback "
              "was not taken -- ...")
        for before_path, after_path, before, after in pairs:
            ...
    written = value if value is not None else wrote
    if written is None:
        return                                          # :2857, before this change
```

The first precondition is checked and stated. The second was checked and
*discarded* — a `return` that says nothing, on the one path where the section
prints bytes and no answer about them.

That is silence rather than a false claim, which is why it is the smaller half:
no reader is told anything untrue. But the section's whole purpose is the
sentence the issue quotes, and on this path it printed the inputs to a
comparison and stopped.

## The reproduction as filed no longer reproduces, and what does

The issue's command line is §6's minus `--wrote 0xA0`, over the committed
fixtures. On this tree it takes the verdict, because the `<value>` in the file
name is the first of the three sources above and §6's dumps all carry one:

```
$ D=ec/tools/testdata/0751-isolation-run
$ python3 ec/tools/grade_0751_isolation.py $D/2026-01-01-0751-isolation-0700-07ff.csv \
    --dump $D/2026-01-01-0751-isolation-a0-before-0700.txt \
    --dump $D/2026-01-01-0751-isolation-a0-after-0700.txt
=== 0x0751 across the dumps (§4.6) ===
  block 0xA0, from the <value> in these files' §6 names
  …-a0-before-0700.txt: 0x0751 = 0x10
  …-a0-after-0700.txt: 0x0751 = 0xA0
  the last dump still holds the written 0xA0. Per CLAUDE.md that is a readback,
  not evidence the EC acted on it.
```

The block grouping `dump_block` introduced reads the value out of the name, so
`--wrote` stopped being the only way a written value can be named. The defect
is still live, on a narrower path: dumps whose names carry no §6 `<value>`,
handed in with neither `--wrote` nor `--block`. On the fixtures that are
copied to a temporary directory under names that carry nothing:

```
=== 0x0751 across the dumps (§4.6) ===
  no block named: these files carry no §6 <value> and neither --block nor --wrote was given
  /tmp/unnamed/before-0700.txt: 0x0751 = 0x10
  /tmp/unnamed/after-0700.txt: 0x0751 = 0xA0
```

… and, before this change, nothing after that. The `no block named` line is
true and is about *attribution* — which block these dumps belong to. Nothing in
the section said anything about the *comparison*, which is a different fact and
the one §4.6 is for.

**So the issue's wording is corrected in one place and kept elsewhere.** Its
"Do" asks for a line saying §4.6's question "needs `--wrote`", and a line so
worded would be wrong here: a `--wrote` is one of three sources, and a §6-named
run with no `--wrote` at all takes the verdict, as the transcript above shows.
The new line names the condition rather than one flag — no §6 `<value>` in
these files' names, and neither `--wrote` nor `--block` — which is what
`written is None` actually means.

## The line, and the four things it must not do

```
  nothing here names the value that was written, so the §4.6 readback was not taken -- no §6 <value> in these files' names, and neither --wrote nor --block on the command line. Pass --wrote 0xNN to take it; --block names a value too.
```

Against the four properties it is held to, each of which a test pins:

- **It says the comparison was not taken.** "so the §4.6 readback was not
  taken" is `report_readback`'s own phrase for the comparison, and it is the
  phrase the coverage notice above already uses — so a reader meets one
  sentence meaning "no comparison was taken" in both branches rather than
  learning two vocabularies.
- **It says why**, in the line rather than by reference: the condition is the
  `no block named` one above it, restated rather than pointed at, because the
  two answer different questions and a reader who has only this line — the tail
  of a section, which is where a fold-in quotes from — has to be able to act on
  it without scrolling up. It is the same restatement the tool already makes in
  one place: the closing summary says its scope under a withheld-window banner
  "in the place the count of withheld windows would be", so a reader who reads
  only one line is not left holding half a sentence.
- **It names what takes the comparison.** `--wrote 0xNN`, with `--block` noted
  as naming a value too, because it does and an operator who has two blocks
  should not conclude the flag is the only route.
- **It says nothing about the byte.** No reading of `0x10` or `0xA0`, no
  register verdict, no `confirmed-` word. The value is printed two lines above
  and the notice is about the comparison, not the number. The test asserts the
  absence of every verdict phrasing as well as the presence of the notice.

**It is unconditional on `pairs`**, unlike the coverage notice, which names a
`--dump-pair` only when one covers the address. That is not an inconsistency
but the difference between the two conditions: a missing *file* can be
replaced by another file, and the notice says which; a missing *number* cannot
be, because no file carries one. The test runs the same command line with and
without a pair and asserts the two §4.6 sections are byte-identical, rather
than picking the notice line out of each.

## Both preconditions failing is not one case, it is two

The last dump can fail to cover `0x0751` *and* nothing can name the value.
Both notices print. They are two independent facts, and gating the second on
the first would make the section's tail depend on a condition the reader
cannot see — the same reasoning the coverage notice's own comment gives for
ending at the count rather than guessing the next line. It also fixes the
wording: the new line may not refer to "the byte printed above", which is
false on that path, and does not.

```
=== 0x0751 across the dumps (§4.6) ===
  no block named: these files carry no §6 <value> and neither --block nor --wrote was given
  /tmp/unnamed/before-0f00.txt: 0x0751 not covered by this dump
  /tmp/unnamed/after-0f00.txt: 0x0751 not covered by this dump
  the last --dump does not cover 0x0751, so the §4.6 readback was not taken -- nothing here says what the byte held after the write
  nothing here names the value that was written, so the §4.6 readback was not taken -- no §6 <value> in these files' names, and neither --wrote nor --block on the command line. Pass --wrote 0xNN to take it; --block names a value too.
```

The decision is a test, not a comment:
`test_both_readback_notices_print_when_neither_precondition_holds`.

## Placement, and why it is in `report_readback`

The notice is inside `report_readback` rather than in `report_dumps`, so it
fires only for the group the readback belongs to — a run over three blocks
gets one notice for the block that needed it, not one per group — and it
inherits `--block` scoping for free, since `report_dumps` has already skipped
the groups of other blocks (`:2788-2793`) before calling in.

**`report_dump_pairs` is left alone**, and the reason is that it has no
analogous silence: its `wrote` is a fallback for *filing* a pair under a block
(`:2994`) and it never compares a byte against a written value. A pair is a
bracket of two files. There is no comparison there to leave unstated.

## The tests

Three cases in `GradeTests`
(`ec/tools/test_grade_0751_isolation.py`), beside
`test_readback_not_taken_when_nothing_here_covers_0751` (`:1194`), which is the
same branch's coverage half.

1. **`test_a_named_value_takes_the_readback_and_the_notice_is_not_printed`**
   (`:1208`) — the two directions over the committed `a0` dumps, since a notice
   that fired on the common path would be a line on every §6 run. The
   `still holds` direction is what §6's own order gives; `not the written` is
   the same two files in the order §6's `rem` warns about, the before-dump
   holding the value the block starts in. A third run names the value with
   `--wrote` over a name that carries none, which pins the property that the
   flag the notice tells the operator to pass is the flag that silences it.
2. **`test_the_readback_is_not_taken_when_nothing_names_the_written_value`**
   (`:1242`) — the path the notice is for, with and without a `--dump-pair`,
   asserting the two sections are identical; and the absence of every verdict
   phrasing on that section.
3. **`test_both_readback_notices_print_when_neither_precondition_holds`**
   (`:1281`) — the decision above.

**The unnamed dumps are written into a `tempfile.TemporaryDirectory()`, and
this is the one place the issue's "over the committed fixtures" is not
literally satisfiable.** Every committed fixture in
`ec/tools/testdata/0751-isolation-run/` carries a §6 `<value>` in its name, so
none of them can reach the branch, and
`test_section6s_file_list_is_the_fixture_set` (`:1322`) holds that directory's
file set *equal* to §6's list — adding a fixture breaks it. The suite already
writes dump-shaped one-liners into a temp directory for exactly this reason
(`:1303-1308`), so this adds no committed input. The committed fixtures still
carry the direction the issue asks for in the other half, the two verdict lines
unchanged.

Cases 2 and 3 were run against the pre-change module with only the `print` and
its comment swapped back, and each fails there: the notice is absent from the
section. Case 1 passes against both, which is the point of it — the fix cannot
pass by breaking the verdict lines.

## What this does not do

- **§6's command line is unchanged.** It keeps `--block <value> --wrote
  <value>` (`:883`), and
  `test_section6s_command_reads_every_dump_it_lists` (`:1335`) reads it. The
  issue is
  explicit about that, and a run that takes the verdict does not need a line
  saying it did not.
- **The two already-silent paths in `report_dumps`** — `:2753` "no dump given"
  and `:2804` "no dump was given for block N" — are left as they are. Both
  already say what was not taken.
- **No register's status changes.** `ec/annotations/registers.yaml` is not
  touched: the notice is about a command line, not about `0x0751`.
- **Nothing is run on the machine.** No §3 run, no live read, no observation
  of what `0x0751` does. A human with the physical laptop is the only one who
  can do that and this change does not need it.
- **The grader's suite is still wired to no per-commit gate.** The patch that
  would do it (`docs/ci/agent-gates-0751-self-test.patch`) is prepared and not
  landed, so these tests run through `--self-test` and `tools/run-tests.sh`.
  Landing it is a human's change.

## Where the rest of it lives

- `ec/tools/grade_0751_isolation.py` — the line, in `report_readback`, plus
  the paragraph that function's docstring now carries on the two
  preconditions and the clause the module docstring's "coverage statement
  before it is a comparison" sentence gained.
- `ec/tools/test_grade_0751_isolation.py` — the three cases in `GradeTests`.
- `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` — §4.6 item 6
  (`:698`) and the sentence on a dump whose name carries no value (`:915`),
  which now carries the third case: neither the name nor a flag.
- [`0751-notice-two-moments.md`](0751-notice-two-moments.md) and
  [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md) — the
  neighbouring work on what a dump's name can and cannot say, which is what
  made the issue's own reproduction stale.
