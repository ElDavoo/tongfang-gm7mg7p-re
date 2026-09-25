# What `ec_watch.py --mark` records, and what a blank press no longer records

**A blank line is not a mark.** Since 2026-09-25 (issue #474) the prompt
records nothing for one, prints that it recorded nothing, and asks for the
next line. Before that it substituted `mark N` for the empty label, which
wrote a row no grader of a §3 capture can read — see *Why the substitution
went* below. The rule is pinned in `test_ec_watch.py`'s `BlankMarkTests`, and
this file is the reasoning that does not belong in a runbook paragraph.

Nothing here has been run at a machine. The refusal, the notice and the count
are offline behaviour of the tool, checked against a fake EC; a human running
[the §3 procedure](../../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md)
is the one who sees the new prompt, and that is their step.

## What a mark is

With `--mark`, each line read from stdin is one mark, and it lands in three
places at once:

- in the capture, as its own row `ts,MARK,,label` (`ts` to the millisecond,
  the label exactly as typed), which is what makes a `--csv` capture
  self-contained rather than a log plus a set of notes;
- on the console, as `--- ts  MARK: label ---`;
- in the end-of-run `marks:` summary, one line per mark the run took.

The label is the operator's own words, and the tool does not read it. The
grader does: `grade_0751_isolation.py`'s `parse_mark` reads the leading word
and the value after `0x0751=`, which is why §3 fixes a fixed set of forms and
why they are load-bearing rather than illustrative.

**CORRECTION (issue #531, 2026-09-25), leaving the sentence above as it was
written.** *The tool does not read it* was true when this was written, and is
still true whenever `--label-vocab` is absent — which is every caller in this
tree except §3's three commands. With `--label-vocab 0751` the prompt reads
every label against that same `parse_mark` and refuses the ones it cannot place
— see *The refused label* below. Nothing else changes, so the sentence above
still describes what `gpu_block_watch.py` and `system_id_probe.py` get through
their mark prompts, which is the reason the check is a flag and not a rule.
Only `gpu_block_watch.py` shares this class; the other keeps its own.

**CORRECTION (issue #548, 2026-09-25), beside the one above rather than under
it.** *The tool does not read it* is still true of the decision — nothing here
passes or fails a label — and is no longer true of the reading. With
`--label-vocab 0751` and a `--csv` that already holds mark rows, the tool reads
that file's mark labels at startup, to name them; see *The marks already in the
file* below. So the file has two readers now, and only one of them judges.

> **Addendum (issue #718, 2026-09-25).** Still only one of them judges, and
> still nothing here passes or fails a label. What changed is that the tool now
> *asks* the judging reader for its verdict instead of working from the lenient
> one's list, so "two readers" is three functions: the same lenient reader
> doing the naming, a partition that names the rows the strict reader refuses,
> and the strict reader itself deciding. The file is read twice where it was
> read once, and the notice's reasons come from the half that judges.

## The blank press

`ec_watch.py` strips the line. If what is left is empty — an empty line, or
one holding nothing but spaces — the tool writes no row, appends nothing to
its mark list, does not advance the mark number, and says so before reading
again:

```
--- blank line: nothing recorded, no mark 1 taken; type a label + Enter ---
```

The notice is not framed as a mark on purpose. A line that looks like the
`MARK:` frames is the confusion the refusal exists to remove, and the notice
is on the same stream the operator is already reading.

Closed stdin still ends the thread: the EOF check is ahead of the blank check,
so a redirected or closed input stops the marker rather than spinning it on a
line that will never come.

## The refused label

`--label-vocab 0751` is that same refusal one step along, and it is opt-in for
a reason that is not caution: `gpu_block_watch.py:59,166` imports this `Marker`
and stamps free-form labels through it, so a blanket check would refuse labels
that procedure is entitled to write. `system_id_probe.py:232` keeps a class of
its own of the same shape, still carrying the `strip() or` default at `:252`
(#483, #484, named there as still open). So the check is a flag, and §3's
three commands are where the operator turns it on.

With it on, a label `grade_0751_isolation.py`'s own `parse_mark` cannot place is
refused exactly as a blank press is — no row, nothing appended, the counter held
back, the same notice shape:

```
--- unplaceable label: nothing recorded, no mark 1 taken; one of: no-op wrote 0x0751=0xA0 / wrote 0x0751=0x10 / restored 0x0751=0xA0 / settled / held / watch over; type a label + Enter ---
```

Both halves of that are the grader's rather than a copy of it. The predicate is
`parse_mark(label)[0] is not None` — the test `unplaceable_marks` applies to
decide a mark is unreadable — and the forms are that module's own
`REQUIRED_LABEL_FORMS`, loaded from it by path. A copy could drift from the
grader, and a prompt that has drifted promises something the grading does not
do. The last three above are the stage boundaries §3 added for issue #472
(`settled`, `held`, `watch over`): a mark that names a stage rather than a
write, which the prompt reads and the grader files against a block. What is
left is the operator correcting the label while the run is still going, instead
of finding out at the grading that a day is withheld.

**What it does not catch is as much of the point as what it does.** `parse_mark`
reads the leading word and the value after `0x0751=`, and it knows nothing about
which values this run means to write or what its sequence of actions should be.
So:

- `wrote 0x0751=0xB0` parses, and is recorded — the prompt cannot know that §3's
  three values are `0xA0`/`0x00`/`0x10`;
- `WROTE 0x0751=0xA0` parses, because `parse_mark` is case-insensitive, and is
  written verbatim, which is as it should be;
- a dropped hex *digit* parses too: `0x0751=0xA` is a value of its own. A
  dropped `0x` from the address is caught; a dropped digit is not;
- a wrong *sequence* — two writes in a row, a restore with no block open — is
  not a per-line question at all. Those still reach `build_windows` and
  `check_block_marks` at grading time.

The promise is exactly *the grader can place this row*, and the mistyped digit
that survives is what §3's three-console comparison is for.

A grader that will not load is a refusal rather than a fallback, printed before
the CSV is opened and long before the EC is. **Correction (issue #549,
2026-09-25), leaving the message above as it was written.** It named one
hard-coded path; the lookup is a list now, and what it prints is
`error: --label-vocab 0751 needs grade_0751_isolation.py, the module this
prompt reads its vocabulary from, and none of these is it:` followed by every
place it looked, one per line, then the two ways out — a copy beside
`ec_watch.py`, or a checkout that has one. *Where the grader is looked for*
below is why the list exists.

A capture taken under a promise the tool silently did not keep is #502's
failure caught a step later rather than a step earlier, and an operator told a
label was refused by a check that was never there has been told something
false.

**CORRECTION (issue #548, 2026-09-25), leaving the two sentences above as they
were written.** *A capture taken under a promise* is true of the labels this
process types and was false of the labels already in the file it appends to: the
check runs where a label is typed, and `CsvSink` opens the path without reading
it. So a `--label-vocab 0751` run is under a promise about its own rows and
about nothing else in that file, and a mark another process wrote is not
something it kept any promise about. A run that finds any now says so and names
them, above the file — see *The marks already in the file*. The refusal above
it, a grader that will not load, is unchanged and is still fatal: there the
check is off for the whole run rather than partial for its oldest rows.

## Where the grader is looked for

The lookup is an ordered list, and the order is the whole of it:

1. **`--grader <path>`,** and nothing else. An explicit path that quietly fell
   through to a different file would be the silent fallback the refusal above
   exists to prevent, in the one form where the operator has already said which
   file they meant.
2. **`ec/tools/grade_0751_isolation.py`** in a checkout, relative to this
   tool. First among the built-ins so that a checkout grades its prompts
   against the grader its own tests pin.
3. **A copy of it in this file's own directory,** which is the case a directory
   of tools staged onto a Windows box is in.

The search advances past a candidate that is not there and **stops at one that
is there and will not load**, naming that path. A staged copy quietly standing
in for a committed grader that has been broken since the checkout was made is a
capture graded against a rule the tree does not hold, and the operator would
find that out at the grading rather than at the watcher.

**A copy that loads but is missing one of the four names is refused the same
way** (2026-09-25, issue #718). `load_label_vocab` reads `parse_mark`,
`REQUIRED_LABEL_FORMS`, `existing_mark_labels` and `existing_mark_findings` off
the grader, and the fourth is new, so a staged copy taken before it is a
working grader that is not a usable one. Read outside the guard around the
load, that is a bare `AttributeError` naming the attribute and not the file —
and the file is the thing an operator can act on, because a staged tools
directory holds a copy rather than a checkout to pull. The four reads are
inside the `try` now, so the refusal is the "there and will not load" one
above, naming the path to copy the current grader over.

**What this settles is which dependency is the real one, not that there is
none.** `load_label_vocab`'s docstring used to argue that the repository layout
is not something to depend on, over the same line that computed
`parents[2] / "ec/tools"` — which described the *lookup*, and the lookup was
one hard-coded path. The layout is one of three places now. The dependency
that survives is on the file existing somewhere: §3's three commands carry
`--label-vocab 0751` and will not start without it, and that is a real startup
dependency, stated rather than looked past. What does not happen is the
dependency spreading to `main()` itself — `gpu_block_watch.py:59,166` imports
`Marker` at module scope and stamps free-form labels through it, and it must
not inherit a grader requirement it never asked for.

**"Copy it beside the tool" is an operator action at staging time**, not a
second committed copy. A duplicate in the tree would be exactly the drift the
current design — loading the grader rather than copying its rules — exists to
prevent, and the lookup above is ordered so a checkout can never grade itself
against the staged one.

None of the lookup has been exercised at a machine. The candidate order, the
refusal and the two ways out are offline behaviour of the tool, checked against
temp directories in `test_ec_watch.py`'s `RefusedLabelTests` rather than
against a staged copy on Windows; an operator there starting §3's three
watchers is the one who finds out whether the second candidate is where they
put the file, and that is their step.

## The marks already in the file

Everything above is a per-process fact: the check runs on each label as it is
typed, and a label this process typed is one it can stand behind. A `--csv` is
not a process. `CsvSink` opens it with `open(path, "a", newline="")` and never
reads what is in it, and the runbook fixes the three CSVs as one set for the
whole run — so a run started against a file another process wrote is appending
to marks it did not type and could not have checked.

When `--label-vocab 0751` meets a `--csv` that already holds MARK rows, it says
so, names them, and goes on. A file the grader's own reader takes whole reads
exactly as it did in #548:

```
  appending to <path>, which already holds 2 mark(s) placed by a process that did not type them here:
    2026-01-01T12:00:00.000+01:00  'wrote 0x0751=0xA0'
    2026-01-01T12:00:30.000+01:00  'settled'
  this run did not check those marks and cannot: it did not write them. §3's three CSVs are one file for the whole run, so blocks 2 and 3 are expected to land here; the grader judges the whole file, though, so a mark it cannot place refuses the day however it got in. The mark numbers in this run's prompts count this run's marks only: they start at 1 whatever the file already holds.
```

printed above the file and a long way above the EC, beside the startup
refusals, so no capture is opened under a notice the operator did not see.

**The notice names two lists, not one (2026-09-25, issue #718).** The block
above is the clean case and it is unchanged. A file that also holds a row the
grader will refuse gets a second section between the marks and the closing
paragraph, one line per row, each with the reason:

```
  appending to <path>, which already holds 2 mark(s) placed by a process that did not type them here:
    2026-01-01T12:00:00.000+01:00  'wrote 0x0751=0xA0'
    2026-01-01T12:00:30.000+01:00  'settled'
  and 1 row(s) of it the grader's own reader refuses, which refuses the file whole: every mark in it, not only the ones this run adds.
    ['2026-01-01T12:01:00.000+01:00', 'MARK', '']  -- <path>: short row ['2026-01-01T12:01:00.000+01:00', 'MARK', '']
  fix or delete the row(s) above before the run: that is the one thing here worth stopping for. The run itself does not care -- it appends either way.
  the marks it could not place are not reported while the file is refused: it is refused whole, so that would add nothing.
  this run did not check those marks and cannot: it did not write them. ... [closing paragraph, unchanged]
```

Three blocks are reproduced from the tool's own output rather than written out
by hand, so a rewording that changes what an operator reads changes them here
too. The `<path>` is the operator's own file, and the reason the first line of a
refusal repeats it is that `read_capture` leads its message with it.

**The reason is the grader's own, and the first one is quoted whole.** The
`short row` sentence above is `read_capture`'s `ValueError` text verbatim, and
that is deliberate: the prompt is showing the error the grading will raise, so
an operator fixes the row from this screen or from the grading log and gets
the same sentence either way. Every bad row is named, not just the first —
`read_capture` stops at the first, so a file holding two after a half-finished
write or a hand edit would otherwise be a fix-one-re-run-meet-the-next loop.
The four reasons it can raise over are a short row (`:690`), a timestamp
`parse_ts` cannot read, hex that is not hex in a change row, and a byte this
interpreter's encoding cannot decode.

**The last of those is a refusal of the file, not of a row, and the remedy
changes with it.** Iteration is lazy, so the decode failure comes out of the
loop and there is no line to point at; the notice prints `the file itself`,
names the encoding it opened the file with, and asks for the capture to be
re-saved rather than telling the operator to fix a row that is not at fault.
The marks beside it are still named, with U+FFFD where the byte was, which is
how the operator finds it.

**The counts are per list and never one total.** Two good marks and one short
row read "2 mark(s)" and "1 row(s)": the short row is a row, not a mark, and
folding it into the mark count would tell the operator to go looking for a
third mark that is not there. The header count is the accepted count, so the
clean case above is byte-for-byte what it was.

**A file that loads can still be refused by its labels**, and that is a third
section rather than a second refusal, because the day is what it costs rather
than the file. The message is `unplaceable_marks`' own, quoted:

```
  appending to <path>, which already holds 2 mark(s) placed by a process that did not type them here:
    2026-01-01T12:00:00.000+01:00  'wrote 0x0751=0xA0'
    2026-01-01T12:00:30.000+01:00  'pressed the thing'
  and the grader's own placement pass reports 1 mark(s) in it as unplaceable, which refuses the day whole. That is its verdict over the group the consoles' marks form, not one label's:
    <path> at 2026-01-01 12:00:30+01:00: 'pressed the thing' is not one of the forms §6 fixes ('no-op wrote 0x0751=0xA0', 'wrote 0x0751=0x10', 'restored 0x0751=0xA0', 'settled', 'held', 'watch over'), and a mark this cannot read is a mark no block can be attributed to
  this run did not check those marks and cannot: ... [closing paragraph, unchanged]
```

**That third section is worded as a group verdict, and the wording is the
calibration.** `coalesce_marks` joins the consoles' labels for one action with
`' / '` and `parse_mark` reads the first part that matches, so a window whose
first label is `settled` places over a second console's unparseable one. A
notice that said "this label is unreadable" would be false about that second
console, so the notice says what `unplaceable_marks` returned — a window it
could not place, or nothing — and a `settled`/`garbage` pair in one merge
window is not reported at all. That is the difference between the issue's
phrase ("fatal only when it leads its group"), which describes the symptom,
and the mechanism: `parse_mark` returns on the first part whose leading word
matches one of §6's forms, and an action part whose value does not parse fails
the whole label there and then, without the rest of the group being tried. So
"nothing in the group parses" is one way to reach that and not the only one — a
hand-edited `wrote 0x0751` with the `=0xA0` dropped off is enough by itself,
and a second console's `settled` does not rescue it.

**A refused file reports no placement verdict, and says so in one line.** A
label verdict needs a file the grader can read, and one it cannot read is
already refused whole, so a second list would add nothing the refusal has not
already said. Leaving the section out silently would read as "the labels are
fine", which is the one thing the operator must not infer here.

**What the notice still cannot say.** It is a preflight and not a second
grader, and three things are outside it on purpose: `unplaced_window_problems`
(a window whose consoles disagree, or whose action one of them never recorded)
is not reported; the cross-console and block checks are not run; and a file
that is accepted here can still be refused at the grading, because the check
that refuses it is a comparison between blocks and this notice looks at one
file. None of those can be known before a run, which is the whole of what a
startup notice is.

**The notice is scoped to this run, and the wording is load-bearing.** A first
cut said the marks in the file "were not checked against the 0751 forms", which
is a claim about the file's *history* — and false in the very case the notice
calls expected. §3's block 1 carries `--label-vocab` like the other two, so the
marks blocks 2 and 3 find were checked against the forms, as they were typed,
by the process that typed them. The tool cannot tell that case from a console
started without the flag, which is the premise of warning over refusing, so the
strongest sentence it can support is the one about the process in front of it:
this run did not check them and cannot, having not written them. The grader's
half is unchanged and is the half that decides the day — it reads and checks
every mark in the file, so an unplaceable one refuses the day however it got in.
**That closing paragraph is printed unchanged whatever the sections above did**
(#718), because its two halves are load-bearing and a second closing to keep in
step with the first is a second thing to get wrong.

**It is a warning and not a refusal, and the runbook is the reason.** §3's
blocks 2 and 3 are *meant* to append to block 1's marks, so a tool that
refused a non-empty `--csv` would refuse the procedure it documents. What no
process can do is check a mark another one wrote, and the grader judges the
whole file rather than this run's rows — which is why an unchecked one can
still refuse the day, and why the operator is better told at the top of a run
they can still stop than a day later as a withheld run with no remedy.

**The predicate is "already holds MARK rows", not "is not empty."** A file
holding only a header, or only change rows, carries no unchecked label: a change
row is not a label, opens no block, and is not something any process could have
checked against §3's forms. §3's block-1 start legitimately appends to exactly
that. A `st_size` predicate warns on the second console of every run, which is
how an operator learns to skip the line.

**Four ways a file comes to hold marks this run did not type** (#548). A
process cannot check any of them, which is the whole of what the notice can say,
and the first three are the ones that can leave the day ungraded:

1. a run taken before `--label-vocab` existed;
2. a §3 console started without the flag — three processes, and nothing forces
   the flag onto all three;
3. a watcher restarted mid-block, appending into the file the first one left;
4. a `manual_fan_ctrl_probe.py` capture, which writes the same
   `ts,MARK,,label` row (`:433-438`) and was never a `--label-vocab` prompt at
   all. The probe is only a *source* of a mark in someone else's file, and is
   unchanged by this.

§3a's service-stopped pass is *not* one of them, and its own runbook note is
why: it is a second run with its own `<date>`, not a fourth block of §3's
(`manual-fan-ctrl-0751-isolation.md:904-907`), so a §3a pass on a fresh date
writes three new files and starts on empty ones — the one routine that
correctly *avoids* the collision, which is why the notice stays quiet for it.
The collision the warning has to allow for is §3's own blocks 2 and 3.

There is no flag to silence the notice, on purpose. Silencing it would be a way
to wave through a collision the tool provably cannot verify, and the cost is one
line at the top of a four-minute run, before a mark has been typed or a number
spent. A later reader who wants one should meet that argument rather than
re-derive it.

The reader is `grade_0751_isolation.py`'s `existing_mark_labels`, loaded by path
on the same load as `parse_mark` and `REQUIRED_LABEL_FORMS` and for the same
reason: the shape of a mark row is the grader's, and a copy in the prompt is a
copy that can drift from the thing that enforces it. It does not raise on the
file's *content* — a row `read_capture` rejects, or a byte the encoding cannot
decode, which comes back as U+FFFD inside a label rather than ending the run —
so a preflight that could not read the file would lose the one warning that
says what is in it. `CsvSink` appends to that same path and never decodes it,
so the bytes are whatever the writing process's locale wrote; `read_capture`
still raises on them, and still grades. `unplaceable_marks`,
`build_windows` and the exit code are all untouched: the grader's refusal is
correct, and forgiving marks it cannot attribute to a process would need it to
know which process wrote each one, which is not in the file.

> **Correction (2026-09-25, issue #718).** The paragraph above describes the
> notice as reading the file with one lenient reader, and it was the whole of
> the notice then. It now reads it with the grader's own
> `existing_mark_findings` instead, a fourth name on the same load: the
> lenient reader is still what does the naming and still does not raise on the
> content, and the strict reader's *verdict* is now beside it rather than
> inferred. Nothing above it is wrong — `existing_mark_labels` is unchanged and
> still returns every mark row — but "it does not raise on the file's content"
> read as though that were the only property the notice needed, and it is not:
> a reader that cannot raise is also a reader that cannot say which of a file's
> rows will be refused. That gap is what #718 closed, and the reason is
> recorded rather than quietly edited.

**The encoding is a property of the interpreter, not of the file, and the
notice reports the verdict it observed rather than one it predicted**
(2026-09-25, issue #718). `read_capture` opens with `open(path, newline="")`
and no `encoding=`, so it decodes in whatever the running locale prefers. A
lone 0xE9 — which latin-1 and cp1252 both write for `café` — is refused under
UTF-8 and read as `café` under cp1252, so the same capture can be gradeable on
the box it was taken on and refused when it is brought back to a machine whose
default differs. Measured under the gate's Python 3.12 on ubuntu (UTF-8), the
0xE9 raises and the notice says so and names the encoding; the cp1252 case is a
**prediction from the documented default and has not been observed on a Windows
box.** The design does not depend on which is right: the notice reports what
the interpreter it is running under actually did, and a mark it read is
reported as accepted with no decode failure claimed. The case stays in
`read_capture`'s contract — the strict reader still raises wherever the
encoding cannot read the byte — and out of the notice on the box where it does
not.

## Why the substitution went

It was `label = label.strip() or f"mark {self._n}"` — a default that made
three wrong things true at once.

**A missing mark read as a deliberate one.** `mark 3` is a label, so at the
console and in the capture it is indistinguishable from a label somebody
typed on purpose. The operator's actual mistake — a press of Enter instead of
a word — left no trace anywhere, which is the one thing a mark is for.

**It wrote a label no form can parse.** `grade_0751_isolation.py`'s
`parse_mark` returns `(None, None)` for it, and `unplaceable_marks` treats one
such mark as fatal for **the whole run** rather than for one block, because
block attribution rests entirely on the labels: a mark the grader cannot read
leaves every block's completeness uncertifiable, not only the one it would
have landed in. `--block` scoping narrows what is graded, not what is known.
The day's windows are withheld and the grader exits 1.

**The grader cannot recover a mark that was never described.** This is the
part that decides it. A lenient parse or a "best effort" flag would make a
mark the operator never typed grade as though they had, and the whole §3
comparison rests on the labels meaning what they say. The right place to stop
an undescribed mark is where it would have been invented.

## What a capture with one action missing looks like now

The refusal is honest rather than clever: it does not invent a mark, and it
does not know what the press was meant to be. So a capture whose operator
simply did not type a label is a capture with that action's mark absent, and
`build_windows` opens each window on a mark and closes it on the next one.
Two actions and one mark is **one window holding both actions' changes**, not
two windows — the bytes really did move between the marks that exist, and the
timestamps are perfectly happy. Nothing in the capture says a mark is
missing; the window is simply longer, and the three-console merge opens it on
the two labels joined with ` / ` where
[§3](../../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md) says it will
when a digit is mistyped in one console.

That is the honest consequence, and it is the reason to type the label rather
than press Enter.

## The counting rule

The mark counter counts **marks recorded**, not lines read. A refused press
does not advance it, which is what lets the notice name the number the press
would have taken: a blank at the start says `no mark 1 taken`, and the label
typed next is the capture's first mark. So the number in a notice is always
the number the operator's next accepted mark will carry, and a run where three
presses are refused still reads 1, 2, 3 at the console. A label `--label-vocab`
refuses is held back by the same rule and for the same reason, which is why the
two notices read alike: the counter is on marks recorded, and neither press
recorded one. Nothing else in the output numbers the marks — the grader reads
labels, not numbers — so this is about the console being readable rather than
about the capture.

**The counter is on this process, and a file can hold another process's.** From
2026-09-25 (issue #548) `--label-vocab 0751` on a `--csv` that already holds
marks says so at startup and names them, which puts two sequences on the screen
at once: the file's marks, counted there, and the numbers in this run's
prompts, which count marks *this* process recorded and start at 1 whatever the
file holds. A block 2 that opens on `no mark 1 taken` over a file already
carrying block 1's six is two correct statements about two different things,
and the startup notice is what keeps a reader from taking the first for the
second. Nothing downstream is affected either way — the grader reads labels
and not numbers — so this is entirely about the console not lying by
juxtaposition.

## Where the refusal shows up

- [manual-fan-ctrl-0751-isolation.md](../../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md)
  §3 is where the operator is told what to type, and its "those forms are
  load-bearing" paragraph carries the dated correction: a blank press is no
  longer one way to produce an unplaceable mark, and the mistyped digit that
  survives is what the three-console comparison is for. Its three commands also
  carry `--label-vocab 0751`, which is where the operator turns the second
  refusal on, and since issue #472 its console block carries a `rem` line per
  mark round naming the exact string to type — all six of them, the three
  stage boundaries included.
- `windows/tools/ec_watch.py` — `load_label_vocab` and the `check`/`forms`
  keyword parameters on `Marker`. The parameters default to no check because
  `windows/tools/gpu_block_watch.py:166` constructs `Marker(sink)` and stamps
  free-form labels, so a default that checked anything would refuse that
  procedure's own marks. `load_label_vocab` returns the grader's
  `existing_mark_labels` as a third value, and `warn_unchecked_marks` is the
  startup notice, beside the startup refusals and above `CsvSink` and `Ec`.
  **Later the same day (issue #718), leaving the sentence above as it was:**
  that is still true and now incomplete in the way a reader would notice. The
  function returns **four** values, and the fourth — `existing_mark_findings`,
  which carries the refusal reasons beside the accepted marks — is the one
  `warn_unchecked_marks` now reads. The notice does not run on the third value;
  a reader following this bullet to find out what the notice is built from
  needs the fourth.
- `windows/tools/test_ec_watch.py`'s `RefusedLabelTests`, beside
  `BlankMarkTests`. It pins the refusal, the notice, the counter, and the
  default: with the flag absent an unplaceable label is recorded unchanged,
  which is what those two other tools depend on. Its later cases pin the
  lookup itself — the grader in neither place, beside the tool, named with
  `--grader`, present and broken, and the flag without a vocabulary — so the
  candidate order and the refusal are one file's behaviour rather than a list
  in a write-up. The committed copy needs no case of its own: every other case
  in the class reaches it from a real checkout, so a lookup that stopped
  looking there would fail them. Its `AppendNoticeTests` (issue #548) pins the
  file side on the same fixture shape.
- [`windows/README.md`](../README.md)'s staging section, and
  §2 of
  [manual-fan-ctrl-0751-isolation.md](../../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md)
  — the two places an operator finds out the grader has to be there before
  §3's commands refuse to start, rather than at the refusal itself.
- `ec/tools/grade_0751_isolation.py` — `parse_mark`, `unplaceable_marks` and
  `build_windows` are the three functions above. None of them changed: the
  grader's refusal was correct and still is. `existing_mark_labels` is the one
  addition, and it is additive.
- `ec/tools/test_grade_0751_isolation.py` — its `mark 3` case is a
  hand-written fixture of the shape, and it still exits 1, because a capture
  carrying that row is still fatal however it got there.
  `ExistingMarkLabelTests` pins the new reader, and holds `read_capture`'s own
  behaviour beside it so the leniency cannot spread.
- `docs/findings.md` §16a is the one-paragraph version of this file, and
  `docs/findings/0751-append-unchecked-marks.md` is the reasoning behind the
  file side — including why there is no flag to silence the notice.

## The same substitution, in two other tools

Neither was changed here: `system_id_probe.py` has its own suite and its own
runbook, and `ec_timer_capture.py`'s marks are read by the timer-sweep grader
under a different label convention. Both write the same `ts,MARK,,mark N` row
for a blank press, and both are follow-ups.

- `windows/tools/system_id_probe.py:252` — the same
  `label = label.strip() or f"mark {self._n}"`, in a `Marker._loop` of the
  same shape. Its mark rows are the shape the 0751 grader reads, so a mark
  captured with that tool and graded with this one fails the same way.
- `ec/tools/ec_timer_capture.py:162` — `mark_loop`, the same `strip() or`
  default over a plain `for line in sys.stdin`. `grade_timer_sweep.py` reads a
  `resumed` label rather than §3's forms, so the consequence there is a
  misleading row rather than a withheld run — a smaller cost, not a smaller
  bug.
