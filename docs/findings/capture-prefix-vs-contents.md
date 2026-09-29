# The date in a capture's name, held to the dates the capture carries: 15 captures, 14 agreeing, 1 stating none, 0 disagreeing (issue #1000)

`ec/tools/check_capture_names.py` holds a name in `evidence/ec-watch/` to
`PREFIX` (`^20\d\d-\d\d-\d\d-`) and refuses one that breaks it, and it is
explicit that this is the whole of its scope: *"`20\d\d-\d\d-\d\d-` is the
shape, not a calendar"* and *"This reads a directory listing. It never opens a
file, never reads a byte."* Both hold, and
[`capture-filename-date-prefix.md`](capture-filename-date-prefix.md) is the
write-up for them. **What that scope leaves open is that the prefix is a claim
about a day, and the file knows what day it is.** Not a calendar question — a
cross-check between two committed facts, which is decidable the way
`check_capture_claims.py` finds a prose claim decidable against a capture that
does not move under a re-run.

This page is the census of that cross-check and the write-up for
`ec/tools/check_capture_dates.py`, which is **a new file and not a second mode
on either sibling**, per `CLAUDE.md`: a naming guard that opens a file stops
being a naming guard, and a prose walker holding a second question would put a
date refusal in the same `--check` as an address claim.

**Nothing here is a live test, and no capture is opened by anything but the
tool.** It reads committed bytes and looks for a shape in them. No EC, no
firmware image, no laptop, no Windows, no capture-producing tool run.

## The census, measured on this tree, 2026-09-28

The file count and the tool's own census, from the repository root:

```
$ ls evidence/ec-watch/ | wc -l
15

$ python3 ec/tools/check_capture_dates.py --check
15 capture(s) under evidence/ec-watch/:
   14  prefix agrees with a date the file carries
    0  prefix disagrees
    1  prefix cannot be checked
       evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt: carries no date to check, so the day in its name is asserted by nothing but the name
1 of those cannot be cross-checked, so the day in the name is asserted by nothing this run read; each one is named above, and `--check` does not fail on it
no capture under evidence/ec-watch/ has a date prefix its own contents contradict
```

The exit code is 0 and the run is green, and that is the point of the third
line rather than an accident of it. The per-file detail behind the four
counts, which is what says *which* capture is in which population:

```
$ for f in evidence/ec-watch/*; do printf '%-52s %s\n' "$(basename "$f")" "$(grep -oaE '20[0-9]{2}-[0-9]{2}-[0-9]{2}' "$f" | sort -u | tr '\n' ' ')"; done
2026-09-18-ac-plugin-sweep-summary.csv               2026-09-18
2026-09-18-profile-switch-0400-07ff.csv              2026-09-18
2026-09-18-profile-switch-0700-07ff.csv              2026-09-18
2026-09-23-0751-isolation.txt                        2026-09-23
2026-09-23-ctgp-live.txt                             2026-09-23
2026-09-23-power-mode-cycle-0700-07ff.csv            2026-09-23
2026-09-23-power-mode-cycle-0f00-0f5f.csv            2026-09-23
2026-09-23-power-mode-cycle-0f00-final.txt
2026-09-23-power-mode-snapshot-dc.txt                2026-09-23
2026-09-24-06c2-06db-perturb-linux.csv               2026-09-24
2026-09-24-06c2-06db-suspend-linux.csv               2026-09-24
2026-09-24-06c2-06db-sweep-linux.csv                 2026-09-24
2026-09-24-06d6-reload-linux.csv                     2026-09-24
2026-09-24-06d9-hold-linux.csv                       2026-09-24
2026-09-24-host-window-page-census.txt               2026-09-24
```

**Every one of the 14 checkable captures carries exactly one distinct date and
it is the one its own name claims.** The 15th carries none. That is the whole
of the disagreement population, and it is empty.

## The three populations, and why a two-population report cannot say this

A run with a verdict per capture has to fold one of these into another, and
the fold is the defect:

| population | count | what it is | is it a verdict |
| --- | --- | --- | --- |
| prefix agrees | 14 | the prefix is among the dates the file carries | no |
| prefix disagrees | 0 | it is not | **yes — the only refusal** |
| prefix cannot be checked | 1 | the file states no day, or no reader takes it, or the name carries no prefix | no |

The third is the one a merged count hides. "15 captures, 0 problems" over a
corpus in which one capture's day is asserted by nothing but its own filename
is a green run that has said **nothing whatever** about that capture, and
`--check` is exactly the kind of thing a human wires into a workflow and stops
reading. So every member is **named on its own line on every run**, with the
reason it is uncheckable, and the line says in as many words that `--check`
does not fail on it.

The member is **`evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt`**,
a bare six-line hex page of the `0x0F00`–`0x0F5F` fan table:

```
$ cat evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt
0F00: 35 39 3b 3d 3f 41 43 4b 50 53 ff ff ff ff ff ff
0F10: 00 30 32 3a 3c 3e 40 42 45 4f 52 ff ff ff ff ff
0F20: 00 3c 3c 46 5a 60 64 6e 8c aa c8 c8 c8 c8 c8 c8
0F30: 32 32 34 36 38 3a 3c 43 46 49 ff ff ff ff ff ff
0F40: 00 30 30 33 35 37 39 3b 3e 45 48 ff ff ff ff ff
0F50: 00 3c 3c 46 5a 60 64 6e 8c aa c8 c8 c8 c8 c8 c8
```

No header, no `#` comment, no timestamp. **It is not an unused file**: it is
cited as a capture in `ec/annotations/manual-fan-ctrl-0751.md:385` and
`evidence/README.md:42`, it is the `--final` argument in a worked command at
`windows/tools/fan_table_replay.py:27`, and it is read by
`ec/tools/check_capture_claims.py`'s case at `:260` and by two write-ups
(`docs/findings/capture-claims-docstring-surface.md:64`,
[`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md)
at `:64`).

> **Correction to the issue's line numbers, recorded here rather than repeated.**
> The issue cites `docs/findings/testdata-row-claims-dated-capture.md` and
> `ec/tools/test_check_capture_claims.py` at lines **54** and **174**; measured
> on this tree both files name the capture, and the lines are **64** and
> **260**. The other three citations are at the lines the issue gave. Per
> `docs/findings.md` §4a-4d the wrong pair is left visible here next to the
> measurement rather than edited out of the quotation — **and deliberately
> written so, rather than as `path:line`**, because
> `ec/tools/census_test_line_pins.py` reads that shape as a citation into a test
> file and would resolve a number this very block calls wrong.

The date is not in doubt so much as **unasserted**: four other captures from
the same `2026-09-23` run agree, and the sibling snapshot says so in its own
first line. What nothing says is that *this file* is one of them.

## The rule: set membership, and the reading that was declined

**The prefix must be *among* the dates the file carries.** The stricter
reading — every date the file carries must equal the prefix — is declined, and
the corpus is why: **a capture names its siblings.**

```
$ sed -n '1,2p' evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt
# Read-only EC reads taken 2026-09-23 between 17:52 and 17:57 (+02:00), just
# before the power-mode capture in 2026-09-23-power-mode-cycle-*.
```

A date that is not the file's own day is already a shape this corpus has, and
the all-must-match reading would refuse a capture for naming its neighbour
correctly. **The two readings give identical answers on this tree**, where
every checkable capture carries exactly one date: this is a decision about the
rule, not a measurement of a difference, and the suite pins it on a fixture
where the two readings actually part company.

## The other decisions, and what was left out

**One rule for how a date is found, not one per file type.** Dates are read out
of the whole file as text — the `ts` column for a `.csv` and a `#` header for a
`.txt` are both a date in the text — rather than through a per-extension
reader, which would be a second rule to keep in step with the corpus's file
types. Both directions are pinned by a case, so re-deriving the extraction
from the extension is red whichever way it is wrong.

**No exemption roster, and no `#` header added.**
`evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt` is a committed
evidence file and a human at the machine owns both halves of changing one: a
header carrying that run's date and conditions is a claim about conditions
only someone with the run in front of them can make, and an exemption list
keyed by filename is a second hand-kept list that has to be edited on a rename.
**Naming the file on the counted line is strictly more visible than a list
nobody reads**, and it is what a human closing the gap actually watches
shrink. Both options stay open to that human; the tool names the file on every
run until one of them is taken.

**No size cap on the read.** Reading only the first N KB and reporting "no date
found" for a file whose date is later is a silent truncation, which is the
thing this repository refuses on principle. Files are read whole; the largest
committed capture is 233 KB.

**Four ways to fail to check, one population.** A file no utf-8 reader takes, a
file with no day in it, a name with no prefix, and a file that cannot be opened
are four *reasons* in one bucket, not four buckets: what they share is that
the run cannot say anything about the capture, and a report that grew a
population per reason would be reporting the corpus's file types as its
verdicts. Each reason is named, the decode one pointing at
`check_capture_encoding.py` because a capture is defined to be utf-8 and that
is the tool that owns the refusal.

**A prefix-less file and a subdirectory are the naming guard's, not this
tool's.** The listing this walks is `check_capture_names.census().files`, so a
subdirectory is never seen and never read. A name with no prefix *is* counted
and named here, with a reason and no second refusal — two tools reporting one
mistake in two vocabularies is the blurring the sibling's own docstring
refuses at length, in a section headed "two refusals, two vocabularies".

**No gate patch.** No `docs/ci/agent-gates-*.patch` is written and no workflow
is touched: `.github/` is copied from `ElDavoo/agent-pipeline` and this
branch's push token has no `workflow` scope. Both closest siblings —
`check_capture_names.py` and `check_capture_encoding.py` — are ungated on
exactly this reasoning, and their `tools/README.md` rows say so. It also
avoids a forced edit to `tools/test_agent_gates_patches.py`, which hardcodes
the patch set in both directions.

**One walk, three views.** `partition()` reads one `population` field rather
than three lists, so a capture cannot be counted twice, and the suite asserts
the partition over a root holding one file of each kind — which is what stops
a tool that reports everything agreeing from satisfying every positive case.

## How it was checked

`ec/tools/test_check_capture_dates.py` is new, **22 cases**, collected by
`tools/run-tests.sh` by `find` with no wiring. **The committed root cannot show
a disagreement** — every capture that states a day agrees with its own prefix —
so both refusals fire on a **scratch root**, the reason
`test_check_capture_names.py` gives for its own two: a case over a conformant
tree proves the tool runs, not that it refuses.

- `--check` exits 1 on a disagreement and names the file, the prefix it has and
  the date the contents say; the **default run over the same tree exits 0 and
  still prints the bucket**, which is what makes the tool a measurement the
  write-up's own figures can be read off.
- The **third population is held as a relation, not a size**: every member is
  named in the output, and a case adds a day to an uncheckable capture and
  watches the bucket shrink with nothing turning red. That is the demonstration
  of the claim above rather than an assertion of it.
- The **set-membership** rule is pinned from both sides — a capture naming a
  sibling's day *beside its own* agrees, one stating *only* a sibling's day
  does not.
- The undecodable, prefix-less and unopenable cases each land in the third
  population **with their own reason named**: none crashes, none is counted as
  agreement.
- A **lookalike date conforms** (`2026-99-99-`): this is a cross-check, not a
  calendar, and `check_capture_names.py` already pins that half.
- A **root that cannot be listed** is a broken census and exits non-zero with
  or without `--check`, never three zero populations — the `docs/findings.md`
  §14b defect one level above the sibling's own guard.
- `prefix_of()` and `PREFIX` are asserted to **agree in two spellings** — the
  tool drops the pattern's trailing hyphen, the case takes ten characters — so
  a pattern that grew a second separator cannot quietly change what a prefix is
  read as.
- **No count of the corpus is asserted anywhere.** The committed-root cases pin
  the *emptiness* of the disagreement set and that the denominator is non-zero.
  `15`, `14` and `1` are figures of the tree this was written against; a floor
  is a claim too, and it is the one that keeps being raised to defeat the next
  capture. The tripwire is the refusal; the corpus is free to grow.

**The mutations, run.** Seven wrong implementations were applied to
`check_capture_dates.py` and the suite was run over each, so the "can fail"
claim is demonstrated rather than asserted: the third population folded into
agreement (5 cases red), a `--check` that never fails (1), the all-must-match
reading in place of set membership (1), a date anywhere satisfying every
capture (3), an undecodable file counted as agreement (1), the third population
counted with its members dropped from the output (8), and a tool listing the
root itself so a subdirectory is read as a file (1).

**The all-must-match mutation is the one worth naming, because it was green
first.** The sibling case was originally built from the corpus's own sibling
line, which names a sibling of the *same* day — where the two readings cannot
part company — so the suite passed with the rule inverted. The fixture now
dates the sibling the 21st and the file the 23rd, and a decision is only held
by a fixture on which the decision bites.

## Not claimed here, and what this does not do

- **That any capture is misdated.** All 14 checkable captures agree, and the
  15th is a dump with no day in it rather than a wrong one. The refusal
  describes what may be added, not a defect in the corpus.
- **That a date in a filename is a real day.** `20\d\d-\d\d-\d\d` is the shape,
  and the `2026-99-99-` case says so.
- **That `0f00-final.txt` *is* from the 23rd.** It is not checkable from its
  contents, which is the finding; four sibling captures and four citations
  make it likely and do not make it stated. A human closes that, not a case.
- **That this would have caught anything in the corpus's history.** It is a
  read of the tree as it stands. A misdated capture in an earlier commit is a
  claim about history nothing here walks.
- **Which of two disagreeing facts is wrong.** A name and a header are both
  claims about one run, and the refusal says so rather than guessing.
- **That a conforming file is a capture, or that its contents are right.** It
  reads bytes and looks for a shape in them. What a capture contains is
  `check_capture_claims.py`'s, what it is written in is
  `check_capture_encoding.py`'s, whether it is one of these files is
  `check_capture_names.py`'s.
- **Editing the prose to match the check.** `ec/tools/testdata/README.md:5-6`
  ("Real captures live in `../../../evidence/` and are dated with the day they
  were taken") and `evidence/README.md:65` (which spells the naming for a
  capture not yet taken) are **not touched**. They are the convention being
  held, not a defect to be rewritten so a checker goes green, and
  [`capture-filename-date-prefix.md`](capture-filename-date-prefix.md) is the
  write-up that gives the reason.
- **Renaming, re-headering or removing any capture, and the root growing or
  shrinking.**
- **`docs/findings.md`, `ec/README.md` and `ec/annotations/registers.yaml`.**
  The first is frozen; the second is a shared list of tools a row in does not
  justify (`capture-filename-date-prefix.md` gives the same reason and the same
  decision for the tool this one sits beside); the third moves only when a
  `status:` moves, and none does here.
- **`tools/README.md` beyond one table row.** No total, no correction, no
  `*(Superseded …)*` note — the trap
  [`capture-filename-date-prefix.md`](capture-filename-date-prefix.md) records
  and `tools/test_readme_suite_table.py` fails on.
- **Live hardware, Windows, and the EC/BIOS/Windows stack.** No register is
  read, no firmware image is opened, no capture-producing tool is run.
- **Anything in another repository.** No PR or issue is opened anywhere.
