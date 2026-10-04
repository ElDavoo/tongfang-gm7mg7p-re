# The `0x07C4` DBEN probe: §3's paths, the tool's usage example, and what the second run actually is (issue #1188)

Three places spell the capture names
[`docs/hardware-tests/ctgp-dben-07c4-bit3.md`](../hardware-tests/ctgp-dben-07c4-bit3.md)
— §3's two commands, §6's two entries, and the usage example in
[`ctgp_dben_probe.py`](../../windows/tools/ctgp_dben_probe.py)'s docstring,
which is what `--help` prints. An operator following §3 has to land each §6
entry without a rename, and the tool's own example has to name a file §6 lists.
They now agree, and
[`windows/tools/test_ctgp_dben_capture_names.py`](../../windows/tools/test_ctgp_dben_capture_names.py)
holds them to each other in both directions.

**Nothing here is behavioural and no run happened.** The change reads markdown, a
module docstring and one function. No EC was opened, no `0x0743` byte was
written, no capture exists; the procedure's status header still reads **not
run** (issue #284), `GPU_DYNAMIC_BOOST_STATUS` stays `present-untested`, and
nothing under `evidence/` comes from this document.

## The issue's premise does not reproduce against the tree

**Retracted, and left here rather than dropped: the issue's headline claim —
that §6 named two captures no command in the document produces, quoting a
single `--csv` at `<date>-ctgp-dben-07c4-bit3.csv` — was not true of the tree
this change was made on.** §3 already carried two commands, one per run, each
with its own `--csv`, and each basename is what §6 lists. That was
[`hardware-test-artifact-handoff.md`](hardware-test-artifact-handoff.md)'s
`ctgp-dben-07c4-bit3.md` bullet ("both directions failed at once"), fixed by
#1190, and it is held in both directions by
[`tools/test_hardware_test_artifacts.py`](../../tools/test_hardware_test_artifacts.py),
which has this document in `HELD` with `command_producers: True`.

The issue's two "worth considering in the same change" items were delivered by
the same change, and were not re-done here: the generalising of the door's
`CaptureHandoffTests` into `tools/test_hardware_test_artifacts.py` (decision
recorded at §"The decision: normalise the prefix, not the command"), the
`manual-fan-ctrl-0751-isolation.md` §6 snapshot's false producer, and
`level-block-0860-086e.md`'s service-stopped CSV.

What survived is below, and it is the narrow remainder rather than the issue's
framing of it.

## The directory, which was the whole of the remaining name defect

§3's two `--csv` arguments passed a **bare filename** while §6's two entries
carry the `evidence/ec-watch/` prefix. `ctgp_dben_probe.py` resolves `--csv`
against whatever directory it runs in — the `open(args.csv, "a", ...)` in
`main()`, which creates nothing above the path — so following §3 verbatim put
each capture wherever the operator was standing, and §6 named a different
place. The rename step the issue describes was real; it was just not the one
the issue attributed it to.

Both `--csv` values now carry `evidence\ec-watch\`, and §3's `rem` block says
which directory they assume. §6 is unchanged: its entries were already right.
This is the shape the door procedure already uses
([`gpu-tgp-07c4-07d7-door.md`](../hardware-tests/gpu-tgp-07c4-07d7-door.md) §3),
and it makes §3's existing "§6 names both, spelled the same way" literally
true instead of adding a sentence to qualify it.

**A stated non-merge, so a reviewer can disagree:** `tools/test_hardware_test_artifacts.py`
compares §6 against §3 on the **basename**, on grounds recorded in its findings
write-up — the sibling procedures pass bare filenames, so requiring the
directory would mean rewriting their §3 prose or a committed tool's documented
invocation. That decision is not reopened here. The new suite checks the
directory for the one document whose §3 now spells it out, and the new test is
not a per-document flag in the shared table. So the strict no-rename rule now
exists twice: once as
`CaptureHandoffTests.test_the_capture_command_writes_into_that_destination`
for the door document, and once here. Two suites cannot share it because they
bind different fakes and import different tools at module scope, and the runner
gives each file its own interpreter precisely so that importing one suite from
another cannot decide which fake a second one gets — see the per-file note in
`tools/run-tests.sh`. The duplication is roughly a dozen lines of fence reading,
which is cheaper than the coupling.

## The third name, and it was in the tool

`ctgp_dben_probe.py`'s usage example read:

```
--csv ../../evidence/ec-watch/<date>-ctgp-dben-07c4-bit3.csv ^
```

**One defect: the basename is in neither §6 list.** That example is the first
spelling of a capture an operator meets, `--help` prints `description=__doc__`,
and nothing in the tree held a tool docstring against anything. It now names
the `-ac` capture.

The directory was **not** a defect and is unchanged.
`../../evidence/ec-watch/` is what resolves from `windows/tools/`, which is the
directory the docstring tells the operator to run in ("Run elevated, next to
`ecrw.py`", above the usage block), and it is the same `evidence/ec-watch/`
§3's commands write when they are run from the repository root. The two
spellings differ because the two run directories differ, and both land in the
one directory §6 names. Changing it to `evidence\ec-watch\` would have resolved
to `windows/tools/evidence/ec-watch/`, which does not exist and which
`main()`'s `open(args.csv, "a", ...)` creates nothing above.

**Docstring only.** No flag, no default, no behaviour. A tool that named a
capture no procedure listed was worth fixing; a tool that grew an
`--overwrite` was not this issue's business, and the append below is a held,
deliberate property.

## What the second run actually is

The issue asks that `--i-mean-it` and the restore be checked against what a
second run does to the first arm's byte, before the two-arm split is documented
as safe. Checked against the source:

- `arm_bytes(orig)` returns `orig | GATE_BIT | VALUE_BIT` and
  `(orig | GATE_BIT) & ~VALUE_BIT & 0xFF`. **Both arms force bit 0 set**, from
  any starting byte — `arm_bytes(0x00)` is `(0x03, 0x01)`. There is no run of
  this tool in which the gate is held closed in a window; the gate is open for
  the whole of both arms of either run.
- The baseline banner reports "bit 0 was **clear**" about the *starting* byte,
  so §3's step-3 `rem` is accurate as written.
- The second run cannot disturb the first arm's byte. Each run reads `0x0743`
  for itself (`orig = ec.read(CTRL)`, inside `with Ec()`) and restores **that**
  value in the `finally`, so it never puts back a byte an earlier run wrote.
  Held at `test_ctgp_dben_probe.py`'s
  `test_a_byte_with_bit_zero_clear_has_it_forced_on_in_both_arms` and
  `test_ctrl_c_partway_still_restores_the_byte`.

So the *safety* half of the question is answered and already pinned. What was
left was a wording defect: §6's "the same question asked with the gate starting
open and starting closed" is right about the *starting* byte, but the filename
`-gate-closed.csv` beside it reads as a window with the gate shut, and no window
in either file is one. §6 now says plainly that "starting closed" is the byte
the second run **begins** from, and that `arm_bytes()` sets bit 0 in both arms,
so the gate is open for every sample in either file.

**Reading taken: keep the filename, fix the prose.** Renaming to something like
`-gate-start-closed.csv` would churn §3, §6, the tool's docstring and the
`hardware-test-artifact-handoff.md` quotes of both names, for a document that
is not run. The alternative is named here so a reviewer can disagree.

## The clobber, which §3 denied

`main()` opens the capture with `open(args.csv, "a", newline="", encoding=...)`,
and
`test_a_second_run_into_the_same_file_appends_without_a_second_header`
deliberately holds the append — a header only on an empty file, so a re-run
stacks rows rather than a second header. §3's "it goes in its own CSV, never
appended to the first" was therefore an instruction to the operator rather than
a property of the tool, and the two commands differ only in their filename, so
a copy-paste slip appends silently.

§3 now says the file is opened for append, and how a stacked one shows: `t_s`
restarting near 0 (`t0` is taken per run) and a second `arm A` block in the
`mark` column. §6's "do not append into an existing one" stays; this is the
same fact from the other side.

## What the two-run split can and cannot answer

**It is not a two-arm contrast.** Both arms of both runs force the gate open,
so `-gate-closed.csv` is a second *starting state*, not a second *arm*. The
question the two files can answer is *"starting from a byte whose bit 0 was
clear, does `0x07C4` bit 3 follow `0x0743` bit 1?"* The question they **cannot**
answer is *"does the gate behave differently when it is closed?"* — nothing in
this tool holds it closed for a window, so a null result from the second file
is a null result about that starting byte, not about the gate being shut. That
is a real gap and a new question about the probe rather than a revision of this
document: a third arm holding `0x0743` bit 0 clear would answer it. Stated here
as an opening, not as work this change did.

**The starting byte is not in the capture either, for as long as the host write
holds.** `sample()` re-reads `0x0743` on every sweep *after* the arm byte is
written, so a `ctrl_read` row is the EC's *answer* to the arm byte, not the arm
byte itself: the arm byte while the write holds, and the starting byte if the EC
takes the write back. Which of the two a capture shows is the open question
`ctgp-dben-07c4-bit3.md` §4.3 already asks, and §2's `0x0522` citation is why
the second is not a surprise. Driven offline against `ecrw_fake` from both
starts, the byte written and the byte read back are the same —
`arm_bytes(0x00) == arm_bytes(0x03) == (0x03, 0x01)` — so the two runs are
**indistinguishable by their `0x0743` columns** *there*. That is the fixture's
behaviour and not a claim about the EC, so the consequence is scoped the same
way: a `ctrl_read` that came back at the starting byte is §4.3's "the EC took
the byte back", which §4.3 says makes the window moot. The distinction is
narrower than saying the files are identical either way: a battery-state run
could of course differ in `0x07C4`/`0x07D4`/`0x07D5`, and that would be a real
observation. What cannot be recovered from the file is *which state the run
started from*, and that is the state the `-gate-closed.csv` filename is about.

This is worth spelling because the natural way to state the correction to §6
overclaims in the other direction — that the second capture "records what the
first does not ... the *starting* byte". An operator who went to the CSV for
the "started closed" evidence would find `0x03` and `0x01` throughout and could
reasonably read the run as something else. §6 says instead that the absence is
the expected shape while the write holds, that a `ctrl_read` showing the
starting byte is the take-back case and not a fault, and that the filename and
the banner are what carry the run's start state.

## What this does not claim

It reads documents and one function's arithmetic. It proves three sets of names
agree and that the byte half of §6's sentence is what `arm_bytes()` does. It
does **not** prove any run produced a file: nothing here opens a capture, and
whether these §6 lists match what is actually in `evidence/ec-watch/` is
`ec/tools/check_capture_claims.py`'s question, which needs the captures to
exist. That is a `needs-hardware-test` step for a human at the machine, and
issue #284 owns it.