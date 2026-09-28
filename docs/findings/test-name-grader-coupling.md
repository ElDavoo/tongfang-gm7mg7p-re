# A test name that claims a coupling the test does not make

Two suites had a test whose name said its mark row was read the way the grader
reads one. Neither test touched the grader, and one of the two files did not
load it anywhere. Both are now assertions made through
`grade_0751_isolation.py`'s own `read_capture` and `parse_mark`, under names that
say which of those two things they check.

The two assertions are deliberately **not** the same assertion, and that is the
part worth carrying to the next site. Copying one of them into the other file
would have replaced a small overclaim with a larger one.

## The sweep, and what it found

`grep -rn "parses_as_the_grader_expects"` over the tree returns two live sites
and one record:

- `windows/tools/test_ec_watch.py`, `MarkCsvTests` — already loaded the grader
  for its `RefusedLabelTests` and `AppendNoticeTests`; the named test alone
  still hand-split.
- `windows/tools/test_system_id_probe.py`, `RunTests` — no grader import in the
  file at all.
- [`0751-mark-provenance-column.md`](0751-mark-provenance-column.md)'s
  reproduction of #719's run, which records what that run printed. A log is not
  a claim, so it is left as it is; editing a transcript to match today's file
  would be the defect the repository's own rules are about.

There is no third site. The pattern the fix copies is not invented here either:
`test_gpu_block_watch.py` and `test_manual_fan_ctrl_probe.py` already load the
grader by path, and `test_ec_watch.py` already had the block, so
`test_system_id_probe.py` takes the sibling file's shape rather than a third
form.

## What the four-way split could and could not catch

The old bodies were a `mark.split(',')` into five names and a handful of
assertions about the middle three. What that pins is that the writer agrees
with itself about the row it wrote: four fields, `MARK` in the second, an empty
third, and the label in the fourth.

What it cannot do is the only thing a reader is for — say whether
`parse_mark` would place the mark. A row that split cleanly and that the
grader refuses is invisible to it, and a row the grader would place but that
stopped splitting cleanly would be invisible to it too. #479 is the failure
that matters: one unreadable mark is fatal for the whole run rather than for
one block, because block attribution rests entirely on the labels
(`unplaceable_marks`), so a split that agrees with the writer is not a weaker
version of the reader's verdict, it is a different one.

The rewritten tests therefore ask the reader, and their *negative* behaviour is
what shows they do. Dropping `("write", "wrote", True)` from the grader's
`MARK_FORMS` turns `MarkCsvTests.test_the_grader_reads_this_runs_mark_as_the_write_it_names`
red; adding a form the probe's label leads turns
`RunTests.test_the_grader_places_no_role_in_this_runs_free_form_label` red.
Neither went red before, and neither is red now for any reason the grader did
not cause.

## The two labels are not the same kind of thing

This is the part that shapes both assertions, and it is the part a
copy-across-the-files fix gets wrong.

`parse_mark` walks `MARK_FORMS` — `no-op` / `restored` / `wrote` / `settled` /
`held` / `watch over` — and returns `(role, value)`, or `(None, None)`.

- `test_ec_watch.py` types `wrote 0x0751=0xA0`, a §6 form. `parse_mark` returns
  `('write', 0xA0)`, and that is the honest headline: **the grader would place
  this mark.**
- `test_system_id_probe.py` types `GPU mode -> dGPU`, which no form leads, so
  `parse_mark` returns `(None, None)`. **That is the run's design, not a
  defect.** The probe is started without `--label-vocab`, so its labels are
  free-form by construction, and `ec_watch.py`'s own `RefusedLabelTests` refuses
  an unplaceable label only while a vocabulary is held. What the test asserts is
  therefore two things: the reader opens the capture and hands back the mark it
  wrote, and the label is *deliberately* unplaceable.

Asserting a role in the probe's test would have been a fresh calibration error,
and a more confident-sounding one than the one being fixed.

## The fifth column is the carve-out, and its name says so

`read_capture` reads four fields and never the fifth, so there is nothing to
ask it. `test_ec_watch.py`'s provenance assertion is therefore split into its
own test, named
`test_the_fifth_column_is_read_off_the_row_and_not_through_the_reader`, and it
reads the raw row — the reason is in the name and in the comment rather than
implied by a green tick. This is #719's recorded measurement of why the shape
was chosen over a comment row, and the page that records it is
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md).

`test_system_id_probe.py` has no such carve-out because it never had one to
lose: the fifth field is already asserted by the sibling test
`test_a_mark_lands_in_the_csv_between_two_sample_rows`, whose comment says why
that field is the provenance column. Adding a second copy of an assertion the
suite already makes would be the "a copy is exactly what would drift" problem
`test_ec_watch.py` names about itself.

The timestamps are the one claim that does not follow the pattern above, and
the reason is `parse_ts`: it is `datetime.datetime.fromisoformat`, which reads
a 1999 stamp without complaint, so reaching `read_capture`'s return
establishes *parseable* and not 20xx. The deleted `ts.startswith('20')` held
a property the return alone does not — it caught a wrong-century stamp — so
both tests assert the century again rather than dropping it, asked of
`marks[0].ts.year`, the `datetime` the reader handed back. That is the old
prefix test asked through the reader, not a stronger one: the assertion is
`marks[0].ts.year // 100 == 20`, and it is the only part of either test that
would go red on a 1999 stamp.

## The census control

A change that edits these two test files moves every pin *into* them, and
`ec/tools/test_census_test_line_pins.py` carries the protocol. Every pin was
re-anchored, and six of the seven figures the run reports are unchanged:
records, files, both verdict counts, and the whole `0/24/22/5/45` landing-shape
split, which is the check that no re-anchoring landed on a line of a different
kind.

Two figures each take one, and it is the same event seen twice rather than two
events. A line that two write-ups cited for **two different claims** is now two
lines, because one of those claims was about a `mark.split(',')` that reading
the row through the reader deleted. In `test_system_id_probe.py` the old `:317`
carried the provenance page's movement row and the shapes page's
single-quoted-MARK example; those are now `:341` and `:320`, so one spelling is
two. In `test_ec_watch.py` the old `:148` carried the same pair; those are now
`:159` and `:452`, so one target is two. No pin was added or dropped.

This write-up cites both tests by file and test name and adds no `file:line`
pin, which is why it moves none of the figures itself.

## What this is not

No hardware and no Windows machine were involved, and no sentence above should
be read as saying otherwise. Both mark rows are written by a fake EC scripted
byte by byte, in process, and read back by the reader in the same interpreter;
the whole of the evidence is that the two assertions go red when the grader
changes. Nothing here says a register exists, that a write was read back, or
that any observed behaviour was observed on this machine.

`measure_mark_provenance.py`'s citation check was re-run after the
re-anchoring, because it reads two of the lines this change moves by line *and*
by quoted text. Both of its rows into these two files resolve. The run also
reports problems in `grade_0751_isolation.py`, `ec_timer_capture.py`,
`check_capture_encoding.py` and three other files — drift that pre-dates this
change, in files it does not touch, and left alone here rather than fixed in
passing.

## The follow-up this leaves

A standing check that no test name may claim a coupling it does not make is
**not** proposed here, and the reason is worth stating rather than leaving the
reader to assume the class is closed. A narrow string check catches this one
spelling and no other, and it is a new always-running file for a two-site fix.
The sweep above covers the sweepable class — a test name containing
`as_the_grader_expects` — and a general reading of a name against its body is
not a regex. That is a follow-up candidate, and until it exists the honest
statement is that these two names were checked by eye and the class was not.
