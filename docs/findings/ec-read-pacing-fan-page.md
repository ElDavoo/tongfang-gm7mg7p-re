# EC reads leave the fan-tach page out and pace themselves (issue #94)

`windows/tools/ec_watch.py` and `windows/tools/ecrw.py dump` now leave
`0x0460-0x046F` out by default behind `--include-fan-tach`, and sleep
`--gap-ms` after every read (default 6). This is the write-up for issue #94,
which asked for both.

It is also the write-up for the second half of the problem, which is the half
that has taken six review rounds: a tool-behaviour change here makes a class
of committed prose stale, and the class has no natural end — each round fixed
the sites a review named and each surfaced more. §4 below is the stopping rule
that ends it, and `tools/check_ec_read_pacing_claims.py` is what runs it.

## 1. What the change is

| | before | after |
|---|---|---|
| `ec_watch.py`, default range `0x0000-0x07FF` | 2048 `ECRR` reads back to back | 2032 reads, `--gap-ms` after each |
| `ec_watch.py --block` | one `readmany` over the whole range | two `readmany`s, split either side of the page |
| `ecrw.py dump` | every byte asked for | the same, minus the page |
| a range inside the page | a baseline and a run that moved nothing | a refusal naming `--include-fan-tach` |

The banner prints the projected sweep time — one gap per address on the
per-byte path, one per `readmany` run under `--block`, which is the unit that
path's sleep loop actually uses — and, when the page was left out, how many
bytes and which. An operator is told rather than left to divide a gap by an
address count. The count follows the path for the same reason `sweep()` does:
projecting `len(addrs) * gap_ms` on `--block` overstated the sleeping by the
number of bytes a run covers, promising 12.2 s for a sweep that takes two
gaps.

**The refusal is the point.** A range entirely inside `0x0460-0x046F` used to
print a baseline, sweep zero addresses and then report "nothing moved" — which
is a result, and the wrong one. It now exits 2 with the opt-in named.

## 2. Why the exclusion is exact under `--block`

`readmany` covers a range with the aligned blocks that enclose it, so it reads
bytes on both sides of what was asked for. Dropping the page from the
*addresses* is therefore not the same as dropping it from the *reads*, and a
split that ignored the overshoot would still read the page without ever naming
an address in it. It does not, and the argument is an alignment one:

- the page starts at `0x0460`, which is 4-aligned, and is 16 bytes long, so
  `0x0470` is 4-aligned too. A run below it ends at `0x045F` at the latest, and
  `readmany` covers a run with blocks starting at `start & ~3` through
  `(end & ~3)` — so its last block ends at `(end & ~3) + 3`, which is at most
  `0x045F` and cannot reach `0x0460`. The lead-in block starts *below* `start`
  and reads downward, so it is not the half that overshoots into the page.
- a run above it starts at `0x0470` or later, which is already aligned, so
  `start & ~3 == start` and there is no lead-in overshoot at all.

Both ends of the page being block-aligned is the whole of it. That is what
`ec_watch.py`'s `block_runs` split and `ecrw.py dump --block` both rely on,
and `windows/tools/test_ecrw_pacing.py` asserts the covered byte set rather
than the call count — a tool that got the runs right and the keys wrong would
pass a call-count check and fail that one.

## 3. What this is not

**6 ms is not measured here, and neither is the hazard.** Both come from
HydroControl's DESIGN.md §4.2, recorded in `docs/related-projects.md` as a
finding about the Eluktronics HYDROC-16 G1 — a different board, a much newer
EC. The OEM software and `uniwill-laptop` sleep about that after every EC
access; that is the report, and it is the only committed source for the
figure.

What has *not* happened on this machine:

- reading the fan page has never been observed to stall these fans.
  `ec_watch.py` was stopped on 2026-09-19 as a precaution, not after an
  incident.
- no `ECRR` has ever been timed here. Nothing in this repository measures one,
  which is why `docs/findings.md` §4g's "2.5 times a second" was wrong when it
  was written and is corrected in place rather than deleted.

So the defaults are the shape the sibling-board evidence argues *against*, not
a rate anyone has validated. `--include-fan-tach` and `--gap-ms 0` are what
keep that falsifiable: a human at the machine can read the page and watch the
fans, which is the only way this stops being a judgement.

**`ec/annotations/registers.yaml` is untouched.** A tool's default is not a
register's status. No `status:` moves here, and none should be looked for.

**`ec_watch.py`'s default range is unchanged.** `--start 0x0000 --len 0x0800`
still watches the same window. What changed is that a sweep of it now takes
about twelve seconds instead of a fraction of one, so the docstring says
plainly that `--start 0x0700 --len 0x100` is the range a run actually uses.
Narrowing the default was not asked for and changes what the tool is for.

**`ecrw.py read` and `write` are left alone.** One explicitly-typed address is
a different risk profile from a 2 KiB sweep, and the operator named it
deliberately.

## 4. The stopping rule

The class is "committed prose that states the retired default as current fact".
It was enumerated once, and the two properties below are what hold it — both
derived from the tools, neither a table of files. A hand-kept list of sites is
precisely the merge-conflict trap `tools/README.md` and `docs/findings.md`
each paid for; `CLAUDE.md`'s own rule is to assert the claim and not the census.

**Property 1 — no committed place states a rate or sweep period for these tools
that disagrees with what their argparse defaults produce.** The checker reads
`--gap-ms`, `--interval`, `--start`, `--len` and `FAN_TACH` out of
`ec_watch.py` itself and computes the sweep cost from them, so it stays true
when a default moves again and it cannot go stale into a second #94.

**Property 2 — a place attributing the open work that would make these tools
safe to #94 must name a tool that is still unpaced.** Which tools read the EC
is read out of their own sources — each either binds `Ec` from `ecrw` at module
level or, in `ecrw`'s own case, defines it — and which of those pace themselves
is read out of the same sources (`--gap-ms` declared or not). A tool that gains
a gap drops out of every attribution on its own; nothing has to name it. This
is what bounds the sweep — the checker *prints* the stale set, so it is
enumerated by running the check rather than by a reviewer naming sites.

`ecrw.py` is in that set for the same reason `ec_watch.py` is: it is one of the
two tools this rule is written about. Deriving the subject purely from tools
that *import* `Ec` excluded the module every other tool in the directory gets
it from, so an attribution resting on `ecrw.py dump` was invisible — a hole in
the stopping rule exactly where a contributor would hit it, since that is the
tool named in half the issue's title. An attribution rests on the union of the
tools its own paragraph names and the unpaced ones its file is about, so a
runbook for a tool that has no gap is not refused for mentioning a tool that
does.

Two exemptions, and both are the review's own distinction rather than a
loophole:

- **A record of a run may state the old figure.** `evidence/README.md`'s
  "0.2 s sweeps" describes two committed captures and is exactly as true as it
  ever was. The checker keys on the block naming a *run* — an ISO date or an
  `evidence/` path — not on the tense of a verb, because tense is not something
  a source scan can read and the subject is.
- **A retired figure may stay visible where its correction is beside it.**
  `CLAUDE.md` §4a-4d is the repository's own retraction rule: the wrong number
  stays, with the correction next to it. `docs/findings.md` §4g's rate sentence
  is exactly that shape now, and a checker that demanded the number go would be
  demanding a silent edit.

`python3 tools/check_ec_read_pacing_claims.py` prints the sweep and its
disagreements, each with the file, the line, what the block said and what the
tools compute; `--check` is the exit status. It is in no gate: adding a line to
`.github/scripts/agent-gates.sh` is an upstream change and a re-copy, per
`docs/agent-pipeline.md`, and `tools/run-tests.sh` discovers a suite by `find`
so none is needed for the suite either.

### What the rule does not reach

Both properties are heuristics over prose and are written to fail legibly
rather than to be right about everything. Three things sit outside them, and
knowing which is the difference between a rule and a pretence:

- **A figure spelled in words.** "a little over twelve seconds" is invisible to
  a scan that reads digits. Both tools' docstrings therefore carry the figure
  as digits rather than as an adjective, which is what puts their own opening
  paragraphs inside the rule instead of outside it — the place where a rule
  that cannot see the subject it was written about would be a rule that is not
  checking.
- **An adequacy judgement.** `ec/annotations/xdata-06c2-06db-timers.md` said
  `ec_watch.py`'s "0.25 s default sweep is close enough to the 0.2 s below to
  use as is". The 0.25 is still the `--interval` default, so no figure in it
  is stale; what is false is the *recommendation*, and no computation can
  object to that. It is corrected in place.
- **A tool that is unpaced for a reason someone documents.** The rule reads
  `--gap-ms` as the definition of paced, which is narrow on purpose — a flag
  whose default is zero, or a sleep the sweep never reaches, would read as
  paced to a source scan and then be offered as an open question that is not
  open. The safe direction for that mistake is a stale attribution a reviewer
  reads, not a silent pass.

## 5. The rest of the class, settled by reading

Not everything in it is a figure. These are sentences whose claim about a
tool's current state was false and are restated in place — the hazard clause
kept, the `#94` clause restated to name what is still open:

- `docs/related-projects.md`, whose HydroControl row said `ec_watch.py`
  "sweeps those addresses without a delay".
- `docs/hardware-tests/fan-table-defaults-0f5d.md` and
  `docs/hardware-tests/oem4-07a6-bit0.md`, which named #94 as the open work
  for a watcher this change paces. Both keep "no interval here is validated",
  which is still true and is the load-bearing half of the sentence.
- `docs/findings/0751-grader-zero-is-of-observed-transitions.md`, which put the
  sampling period on #94 without noticing that §3's own watchers had been paced
  under it.
- the runtime banners and docstrings of `manual_fan_ctrl_probe.py`,
  `gpu_block_watch.py` and `system_id_probe.py`. Their reads stay unpaced and
  the hazard is real; only the pointer to #94 as *the* open work went stale,
  so only that clause moved.
- `ec/tools/grade_0751_isolation.py`'s comment beside `ZERO_SCOPE_NOTE`. The
  printed note itself is untouched: "the per-byte sampling period is
  `--interval` plus a sweep duration nothing in this repo measures" is still
  true, because a default borrowed from another board is not a measurement.

## 6. What a human at the machine has to decide

Nothing here can be settled from a runner, and the questions are the ones the
opt-ins exist for:

1. Does reading `0x0460-0x046F` at 6 ms actually stall these fans? A run with
   `--include-fan-tach` against a fixed load answers it; a run without is the
   control.
2. How long does one `ECRR` take on this EC? That is the figure
   `docs/findings.md` §4g has been getting wrong since it was written, and no
   rate in this repository is validated until somebody measures it.

`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` §3 is where a run
under a fixed load belongs, and the offline suites here prove the defaults and
the flag handling and nothing whatever about fan behaviour.