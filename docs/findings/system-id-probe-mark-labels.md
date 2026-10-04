# The `0x0456` probe's mark labels are free-form by design, and its blank press records nothing (issue #1329)

The write-up for [issue
#1329](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1329), which asks
two things about `windows/tools/system_id_probe.py`'s `Marker`: whether a blank
press should stop making a mark the way `ec_watch.py`'s stopped under #474, and
whether the probe should carry a `--label-vocab`. The first is done. The second
is a decision, and the decision is **no** — the labels are free-form prose by
design, and there is nothing to check them against.

Everything here is offline and static. **No EC was opened, no register was
read, no mark was typed and no capture was taken.** The one artefact this
change touches that a hardware run would produce is a row the probe no longer
writes. Issue #1309 is the `0x0456` run, it is **not run**, and nothing here
runs it: no laptop and no Windows machine is reachable from a GitHub-hosted
runner.

Re-derive the checks with:

```console
python3 windows/tools/test_system_id_probe.py       # the blank-press cases and the label cases
python3 ec/tools/measure_mark_provenance.py --page \
    docs/findings/0751-mark-provenance-column.md \
    docs/findings/0751-mark-provenance-shapes.md    # the re-anchored writer pin
```

---

## The decision, and the three reasons it goes this way

`--label-vocab` is a real flag on `ec_watch.py` and this probe has none. The
question is whether that is a gap. It is not, and the deciding reason is the
runbook's own:

- **The labels this procedure mandates are ones that check would refuse.**
  §3 and §3b tell the operator to type `block start`, `control arm end`,
  `steady window end`, `block end`, and for the bit-7 block `GPU mode ->
  discrete`, `suspend/resume`, `driver reload` and `power mode -> N`. None
  leads with a form in `MARK_FORMS` (`no-op` / `restored` / `wrote` /
  `settled` / `held` / `watch over`), so `parse_mark` returns `(None, None)`
  for every one of them. A `--label-vocab 0751` here would refuse **every label
  the procedure mandates**, at the first mark.
- **Nothing grades the capture.** The procedure's own status paragraph says
  neither the probe nor its output is graded by a script, and §6 says it
  outright. `--label-vocab` exists to catch a mistyped `=` or a dropped `0x`
  *before* a day of hardware time is spent against a grader that will read the
  file. There is no such grader here, so the day is not at risk and the check
  has nothing to be worth.
- **The marks are read by a person.** §4's reading is against the `0x0456`
  bit-7 trajectory, and prose is the medium for that. "power mode -> 3" is a
  description of what the operator did; nothing about it needs to be
  machine-parseable for the run to be worth having.

So the two tools differ for the same underlying reason and neither is a copy
that drifted: `ec_watch.py` takes marks for a procedure whose §3 fixes graded
forms, and this probe takes them for one whose labels are a person's own words.

### An alternative considered and rejected

Importing `ec_watch.Marker` rather than keeping a class of its own. It would
remove the duplication outright. It also inherits that class's `check` /
`forms` / `provenance` surface and its documented reason for defaulting those to
no check — `gpu_block_watch.py` stamps free-form labels through the same class,
which is why the flag is off by default rather than absent. Coupling the two
tools is a larger design question than this issue asks, and it is one to settle
with both procedures in hand rather than from one of them. The duplication
actually in scope was one line of behaviour, and that is what changed.

---

## What changed

`Marker._loop` dropped `label = label.strip() or f"mark {self._n}"` and gained
the same guard `ec_watch.py` has had since 2026-09-25: strip the line, and if
what is left is empty, print the notice, say no mark number was taken, and
`continue` — **before** `self._n += 1`, so the counter names the number the
press did not take and `_n` counts marks recorded rather than lines read. The
cases in `test_system_id_probe.py`'s `BlankMarkTests` mirror
`test_ec_watch.py`'s one for one, case for case and name for name. The sixth
is this tool's own and has no counterpart there: it asserts on the loop's
*shape* rather than its behaviour, so that the substitution cannot be pasted
back in a form the five behavioural cases would miss. It checks for an `or`
fallback node rather than for any spelling of the old line, and it is
required to fire — the case runs its own check against the deleted line and
its concatenation spelling, so the guard cannot pass vacuously. That detail is
recorded because the obvious version of this case cannot fire at all: an
f-string's `mark {` placeholder never reaches the literal list as a substring,
and the blank-press notice's own `no mark {self._n + 1}` would trip a text
search on correct code.

The design half is stated in the places a reader meets it rather than in a
comment somewhere: the module docstring, `Marker`'s own docstring, the
`--mark` help, and §3 of the runbook all say the labels are free-form by
design and why there is no vocabulary to check one against. The `--mark` help
is the one an operator sees at `--help`, and the §3 paragraph is the one they
read while holding a run together.

`system_id_probe.py`'s parser moved out of `main` into a `build_parser` of its
own. Nothing about the parser changed in the move: the same options, the same
help strings, and `--help` output byte-identical to the commit before it —
checked by diffing the two, since a parser is exactly the thing a reader
trusts without reading. It is there so the case below can ask the parser a
question without `main`'s side effects, which is the whole difference between
that case failing and hanging — see the correction in *What
`FreeFormLabelTests` is for`.

### Why the new tests sit at the end of the suite file

`docs/findings/test-line-pin-census.md` carries pins that cite lines *into*
`windows/tools/test_system_id_probe.py`, and a citation whose target line moves
below an edit has to be re-registered in that table. `FakeStdin` and
`RunTests.run_probe` both sit above every one of those pins, so a new class
placed next to either would put all of them below the edit and re-register them
for a shift of a few hundred lines rather than a few. The new helper and both
new classes go after `NoWriteTests`, at the very end. The reason is written in
the file next to the helper rather than only here, because that is where a reader
deciding where to add the next case will look.

**The placement does not make the pins unmoved, and a draft of this said it
did.** The modules the new cases need are imported at module level, so their
imports went to the top of the suite file and shifted every line below them by
that many lines — the targets the table registers no longer land where it
records them. The draft claimed "where nothing above them moves", and the same
claim stood in the suite file and in the pull request description; it was wrong,
and the import hunk in the same diff is what refutes it.

The census rows are left stale on purpose rather than re-registered, which is the
same outcome `origin/main` already has: `CLAUDE.md`'s "No totals of the
repository's own text" bullet says the census records the tree it was measured on
and nothing holds it to the current one, and `test-line-pin-census.md` says so
itself. So what the placement buys is that the shift is a handful of lines and
sits above nothing that a future case is extending — not that it is zero.

The new tests are cited **by name** throughout this file rather than by line,
which is the same rule applied to avoiding the census rather than to
re-deriving it.

### The pins this change had to re-anchor

`ec/tools/measure_mark_provenance.py`'s `CITATIONS` cites by quoted text and
holds the line number as a hint the tool prints, so a moved line is not a
failure by itself — `resolve()` finds the text wherever it now sits. Three of
the files this change edits are cited there, though, so their hints were
re-anchored to the lines the cited text now occupies: the mark-row writer in
`windows/tools/system_id_probe.py`, which the blank-press guard pushes down, and
six more in `windows/tools/ec_watch.py`, `windows/tools/system_id_probe.py` and
`windows/tools/test_system_id_probe.py`, which the correction comments and the
new imports push down. `--self-test` is that tool's check; the citation check
runs under `--page`, and both were run after the edit.

Lines also moved inside `ec/tools/test_grade_0751_isolation.py`, which this
change cannot help: the correction over the `mark 3` fixture is a comment
block, so it sits above every line below it and pushes them down. Rows in
`docs/findings/test-line-pin-census.md` cite into that file, so some of them no
longer land where they were registered to. The same is true of the imports this
change adds to `windows/tools/test_system_id_probe.py`, for the reason given
above. **They are left alone on purpose.** That table records the tree it was
measured on and, by the rule in `CLAUDE.md`, nothing holds it to the current one —
which is also why the new tests go at the end of their file rather than beside
the code they test, though as that section now says, the placement reduces the
shift rather than preventing it.

---

## The corrections, beside the sentences they correct

Every place in the tree that said the probe still substitutes the label, or said
it for the wrong reason, is corrected **beside** the original sentence, which
stays visible — the §4a-4d pattern `docs/findings.md` §4 records, and the one
`ec_watch-marks.md` already uses in these very files. The table is the list;
it is not counted here, because a count of the corrections in a write-up is one
more line every later correction has to edit.

| Where | What it said | What is true now |
|---|---|---|
| `windows/tools/ec_watch.py`, the `--label-vocab` paragraph | `system_id_probe.py` "has its own, still `strip() or` at `:252`" | Both line numbers were already stale; that substitution is gone **from the probe**, and is still in `ec/tools/ec_timer_capture.py` — see *Left open* below. The conclusion the sentence supported — that the flag is a flag and not a rule — stands on the labels instead. |
| `windows/tools/ec_watch-marks.md`, *The refused label* | the same claim, at `:257` | Same correction, same reason. |
| `windows/tools/ec_watch-marks.md`, *The same substitution, in two other tools* | "Neither was changed here … Both … are follow-ups" | One is changed and one is not, so the section carries an **addendum at its end** naming which is which. The bullets above it stand as written. |
| `ec/tools/test_grade_0751_isolation.py`, the comment over the `mark 3` fixture | "though `windows/tools/system_id_probe.py` still substitutes the same label, and writes the same shape of row" | Stale; corrected beside it. **The `mark 3` fixture and every assertion under it stand** — the grader's refusal is correct, this change does not touch it, and a row of that shape is still fatal however it got there. |
| `docs/findings/test-name-grader-coupling.md`, *The two labels are not the same kind of thing* | the probe "is started without `--label-vocab`" | The **premise** is false and the **conclusion** stands. There is no such flag on this tool, so no run can be started with one; the labels are free-form because the tool carries no vocabulary and is not going to. Replacing the premise while leaving the conclusion is the point: the conclusion — that `parse_mark('GPU mode -> dGPU') == (None, None)` is right for this run — is correct, and saying otherwise would be the overclaim in the other direction. |

`docs/findings/test-name-grader-coupling.md` is what makes the last row a
correction rather than a disagreement: it already held that asserting a role for
this probe's labels would be a calibration error, and the decision recorded here
is the same fact reached from the other side.

---

## Left open, named rather than overlooked

- **`ec/tools/ec_timer_capture.py`'s `mark_loop`** carries the same `strip() or`
  over a plain `for line in sys.stdin`, and `ec_watch-marks.md` names it beside
  this probe. It is **deliberately not settled here.** It is a different tool
  on a different platform against a different grader: `grade_timer_sweep.py`
  reads a label *containing* `resumed` rather than §3's forms, so the
  consequence there is a misleading row rather than a withheld run — a smaller
  cost, as `ec_watch-marks.md` itself says. It also has no suite of its own,
  so settling it means a new test file as well as the edit, three more writer
  pins in `measure_mark_provenance.py` to re-anchor, and a change in the
  directory where parallel branches collide most. Recorded here so the
  follow-up pass can open it as its own issue rather than lose it.
- **Whether #483 / #484 are duplicates of this.** `ec_watch.py` and
  `ec_watch-marks.md` both cite them as the open issues for this substitution,
  so this may overlap work already queued. The implement stage could not run
  `gh issue view` from this environment to check, so **that check is not
  done** and no stage here closes an issue to tidy a duplicate. A human decides.
- **Whether an operator's marks are good.** Nothing here can settle that.
  `parse_mark` returning `(None, None)` for a runbook label is the design, and
  `FreeFormLabelTests` pins it; it is not evidence that any run produced a
  usable capture, and must not be read as one. §4 of the procedure is read by a
  person.

## What `FreeFormLabelTests` is for

It is a **tripwire that goes red in the useful direction**, and it is worth being
precise about which case fires, because the obvious answer is the wrong one.

`test_there_is_no_vocabulary_to_hold` is the detector: it asks `main`'s parser
for `--label-vocab` and expects argparse's exit 2, so a flag added to this tool
fails it outright. The class docstring says so, so the next reader does not read
red as a bug.

**CORRECTION (#1329 fix round 1, 2026-10-04), beside the paragraph above rather
than under it.** *"Asks `main`'s parser … fails it outright"* was right about
the answer and wrong about what a reader would have seen. That case invoked
`main`, and with the flag added `main` does not fail: it parses the flag, falls
through to `with Ec() as ec:` and sweeps the six addresses under the default
`--seconds 0` until it is killed. So the one case this file points a reader at
would have hung to the suite timeout — a red that names no assertion and says
nothing about which one mattered. Verified by adding the flag and calling what
that case called: it prints the sweep banner, opens the fake EC, and is still
sweeping when a timeout kills it — exit 124, eleven sweeps in, with stdin a pipe
and with stdin `/dev/null` alike.

The fix is not a better assertion but a smaller blast radius. The parser now has
a name of its own — `build_parser` returns it, `main` takes what it returns, and
no option, help string or `--help` line changed — so the case asks the parser
to parse the flag, which has no side effect in either direction. The flag then
makes the assertion fail at once and by name rather than run on into a sweep.
Same run with the flag injected:

```
FAIL: test_there_is_no_vocabulary_to_hold
AssertionError: False is not true : this tool now takes --label-vocab,
so the free-form decision its labels rest on needs reopening
Ran 4 tests in 0.002s
```

and that check is no longer only a claim about a change nobody has made. Its own
case, `test_that_case_can_go_red`, arms the flag on a fresh copy of this tool's
real parser and fails if the detector stays green with it — the same instrument,
and for the same reason, as the AST case's liveness check above, which is what
the guard in this section should have had from the start. A claim about the
future that has never been seen to fire has not been shown to fire.

The other cases are **not** that detector, and rounding them into it would be the
same overclaim this change is correcting elsewhere. They read the runbook and
`grade_0751_isolation.parse_mark`, and none of them touches this probe's
parser — adding `--label-vocab` here would not change `parse_mark`, so they stay
green. Verified by adding the flag and running them: still passing. What they
hold is the *consequence* the decision rests on: every label the procedure
mandates is one that check would refuse, so a flag added alongside them would be
refusing the runbook's own labels at the first mark. That is an argument, not a
detector.

The extraction guards itself against a vacuous pass by naming the labels the
decision rests on and requiring each to be among what it found, so a §3 that
stops asking for one fails by name; a floor on the extraction's yield would only
have said that some number of them went. Every extracted label is then checked
one at a time, and a `wrote 0x0751=0xA0` from the *other* procedure is checked in
the same suite by the same call, so `(None, None)` cannot be a reader that is
simply agreeing with everything.