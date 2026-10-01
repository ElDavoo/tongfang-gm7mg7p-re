# A denial is the only shape a retraction takes, so `check_capture_claims.py` checks it instead of skipping it (issue #328)

`ec/tools/check_capture_claims.py` used to short-circuit a unit on `DENIAL`
before either rule ran: a sentence saying an address did *not* move in a named
capture was reported as a skip, never checked. This inverts that — an address
a unit says did not move in a capture the capture watched has to have **no**
row in it — and the tree goes green without a single word of prose edited.
Every figure below is read off a command in this tree, not carried forward.

**Nothing here reads hardware.** No EC, BIOS or Windows binary is read, no
image is loaded, no register is touched, and no laptop is involved: the
captures are read as committed `.csv` files on disk. If a later capture makes
a checked denial disagree, fixing that prose is a human's edit against a real
run.

## Why the skip cost real coverage rather than hypothetical coverage

A denial is the shape both retractions in this tool's history took. Issue #265
and the `0x07D4` clause issue #270 withdrew were both written as *this did not
happen*: "`0x07D4` moved at the AC plug-in" was wrong because the capture has
no `0x07D4` row, and the correction that replaced it is "`0x07D4` did not
move". A checker that reads only attributions cannot see either version of
that sentence, so a withdrawn claim that came back in its corrected form would
have gone unnoticed. Worse, the skip took the affirmative half with it:
`docs/findings.md` §4g's "`0x0436` moving 4 times … and `0x0437` never
moving" is one sentence, so **neither half was read** — the 4 is a real count
and it is the number the #265 correction turns on.

## The measurement that settled the design

Taking `DENIAL` out of the rule entirely and re-running gives **14 problems,
every one of them a true denial being read backwards by the presence rule**.
That is the evidence the fix is an inversion of polarity rather than a
loosening of the check: the tree goes green with no prose edit because all
fourteen are true and only the direction was wrong. The count also decides
*where* the split has to happen — with `DENIAL` neutralised the affirmative
half of §4g's sentence alone yields checked claims and no problems, so
`0x0436`'s 4 binds through the nearest-address fallback and agrees with the
capture, and so does `0x0438`'s once.

## What the split is, and why it is local

The clause split is **local to this tool**, not in
`check_cluster_citations.units()`. That walker is capture-agnostic by design:
it splits on sentence terminators so a cluster citation has exactly one owner,
and the cluster checker knows nothing about captures, movement or polarity. A
boundary defined by *denial versus affirmation* is a capture-claims concept,
and putting it in the shared walker would make that tool split on a
distinction it has no use for and perturb its own output — the mis-paired-split
problem #273 is about. It also keeps this branch out of a file other open
branches are editing.

What is **not** duplicated is the line bookkeeping: `unit_lines()` already maps
an offset in the unit back to a source line, so the report still points at the
line an address is *on* rather than the unit's first line, and
`test_reported_line_is_the_address_line_not_the_unit_start` still holds.

## The rule, and the two cases it declines

Polarity is a property of an **address**, not of a clause: whether a unit
denies `0x07D0` is a fact about `0x07D0` everywhere in it. `denied_addresses()`
walks outward from each denial cue and binds the nearest address either side,
continuing across a connective so a coordinated subject stays one subject
("`0x07B9`, `0x07D0` and `0x07D1` did not change once"), stopping at a comma
and at a gap that is not a connective, and never binding an address inside
parentheses. Quoted spans are blanked before the cue search, because
`registers.yaml`'s `XDATA_0436_PAIR` note quotes `"0x0437 never moving"` in
order to characterise the claim rather than to make a new one.

Two of the seventeen denials the tree carried are **skipped**, each with its
own `--verbose` reason, `skip (denial outside the watched window)`:

- `ec/annotations/registers.yaml`'s `XDATA_09EB` note against
  `2026-09-23-power-mode-cycle-0700-07ff.csv`. The capture's name states
  `-0700-07ff` and the note says so itself — "the capture watched
  `0x0700-0x07FF` and never saw `0x09EB`". That is a statement about
  **coverage**, not about movement, and "not covered" is a different claim
  from "absent from what was watched". It is a skip, never a pass and never a
  failure.
- `docs/findings/perturb-arm-colliding-marks.md`'s `0x0751` against
  `2026-09-24-06c2-06db-perturb-linux.csv`, which is outside `0x06C2-0x06DB`.
  The quote it sits in is tool output inside a fence.

The window a denial is judged against is the capture's own name unioned with
the ranges its unit names, because neither source is enough alone: seven of the
ten committed captures carry `-0700-07ff` in the filename and three do not,
and the AC-plugin sweep summary has no name to read — there the sentence's own
`0x0000-0x07FF` is the only thing that puts `0x07B9` in scope at all. A
capture with no window in either place is not windowed, and every address is
checked.

## The surface, before and after

`--verbose` now reports a denial as a claim **checked**, and the total rises
from what it printed before — a run reaching nothing still prints `0`, and the
figure is asserted non-empty rather than held to a literal, because it is a
count over the tree and every merge moves it.

- Before: 15 capture claims checked, in six files.
- After: 64, in nine files. `docs/findings.md`,
  `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md` and
  `docs/hardware-tests/remain-capacity-0436.md` each yield claims for the
  first time.

All twelve in-window denials the tree holds — fourteen address-level claims
across eight units, the other two being the windowed skips above — are
**true**. That includes the #265 correction itself, whose own note lists that
capture's 22 distinct addresses and names no row for either `0x07D4` or
`0x07D5`. It is why `ec/annotations/registers.yaml` is not edited: no `note:`,
no `status:` and no correction moves, because there is nothing to correct.

## What is still not checked

Nothing was taken away to make room for this. The documented limits stay
limits and are restated in the docstring: a table whose capture is named above
it, `.txt` captures (outside the oracle), word numerals, the bare-date `addr`
column, and a denial whose subject is named outside its own clause — coverage
given up, rather than a claim missed. Each is "not found by this method", never
"absent", and the new skip reason is worded the same way for the same reason:
`0x09EB` is **not covered**, which is a fact about the method's reach rather
than about the firmware.

The `0x07B9`/`0x07D0`/`0x07D1` absence `docs/findings.md` §4g rests on is now
held to `2026-09-18-ac-plugin-sweep-summary.csv` by a check rather than by a
re-reading: the sentence names the sweep's `0x0000-0x07FF` window, all three
addresses are inside it, and none has a row in that file. A later capture that
gave one of them a row turns §4g red here. This **adds** a check and retracts
nothing, so §4a's wrong figures and their corrections stay exactly as they
were, and no `status:` is touched.