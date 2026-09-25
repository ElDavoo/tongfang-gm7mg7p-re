# The probe's watch set can be §3's first watcher, whole (issue #666)

The write-up for [issue
#666](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/666), which asked
whether `windows/tools/manual_fan_ctrl_probe.py` should close the §4.4
whole-page gap that `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`
§3b records, or record the narrower truth accurately instead. **End (a) is
landed**: an opt-in, no-argument `--watch-page` that puts `0x0700-0x07FF` in
the watch set in place of `WATCH`'s 14 addresses. **This is a tool-side change
and nothing more**: no EC is opened, no register is read or read back, no
capture is taken against real data, no register `status:` moves, and no line
of this change is a report about the machine.

## Why (a), and why the cost argument does not hold against §3

End (b) — the probe answers §4.1-§4.3 whole and §4.4's PWM comparison only —
is the honest floor, and the #476 correction already states it accurately. It
is still the wrong end for the reason the issue itself supplies: **the probe is
the fallback for the isolation run** (#663's human fixed-load re-run is the
runbook's §3, and §3b says a probe run is the single-tool form of it). So the
gap is not a documentation nicety; it is the fallback tool unable to do the
one part of §4.4 that §4.4 keeps for a stated reason — *"the neighbourhood is
still the least mapped part of the page and `0x0786` in it is a live naming
conflict"* — which is the least-mapped part of the page, which is where a
finding is most likely to be.

The issue frames a 256-address page "on top of the existing 206 reads" as a
real per-sweep cost. Read against §3's own arithmetic rather than the probe's
default, it is **not a new figure at all** — it is §3's three watchers in one
process:

| | §3's three watchers | probe default | probe `--watch-page` |
|---|---|---|---|
| ECRR reads / sweep | `0x100+0x60+0x60` = **448** | 206 | **448** |
| `--block` IOCTLs / sweep | `0x100/4+0x60/4+0x60/4` = **112** | 56 | **112** |

The page arm is arithmetically §3's three watchers because it *substitutes* the
page for `WATCH` and leaves FANTBL and TEMP as they already were. A reader
meeting two 448s is meeting one figure, and §3's traffic paragraph now says so
beside its own arithmetic rather than leaving the two to drift.

**That is also why the grader needed no change.**
`ec/tools/grade_0751_isolation.py:1484-1490` already prints an
`other addresses that moved (N), not graded here` line for every change row
outside its `WATCHED`/`CONTEXT` groups, so a 448-address capture lands in an
existing, already-calibrated bucket rather than a new one. The grader is not
edited: touching it would be scope creep on a tool-side issue.

## The reading taken, and the two declined

- **Not a default widening of `WATCH`.** It would silently move the footprint
  a run is taken at, from the default 206 to 448, under a human who did not
  choose to — and 448 is 2.2x that traffic on the one run §3 holds under a
  **fixed load** with **#94** still the open question of what EC traffic does
  to a fan. That default is not the committed
  `evidence/ec-watch/2026-09-23-0751-isolation.txt` run's footprint, which is
  the distinction worth being careful about: that run's own header lists
  `WATCH` plus the fan table and no temperature range, so it was taken at
  **110**, and `TEMP` only joined the set the next day, with #143. 206 is the
  default a later run would have swept, and no committed run was taken at it.
  The existing `--level-block` paragraph (probe docstring, "opt-in for
  exactly that reason") is the precedent and the model: the #99/#122
  footprint stays as committed rather than growing under a flag nobody
  reading that run knows about.
- **Not a typed `--page 0x0700`.** A typed page base is one `--page 0x0460`
  away from the fan-tach page that stalled the fans on a sibling board (#94),
  and this tool's entire safety argument — the `FAN_TACH` guard, the
  "0x0400-0x045F is the EC's own temperature reading … it stops at 0x045F"
  paragraph — is that the operator *cannot* reach that page by typing. There
  is no second page to generalise to (`0x0F00` and `0x0400` are `0x60` in §3,
  not `0x100`, so a generic selector would not even reproduce the other two),
  so the generality buys nothing and costs the guard. The flag adds exactly
  the one range §4.4 names.
- **Left out of (a) entirely**, because §3b already names them and nothing
  here changes them: §4.6's dump pairs, §3a's service-stopped pass, §4.5's
  by-hand package-power readings, and §6's seven non-CSV files. The page arm
  makes §4.4 whole; it does nothing for §4.6, and the runbook's new correction
  says so in those terms.

One structural note: CLAUDE.md's "a new tool is a new file, not another mode
bolted onto an existing one" is a rule about *tools*, and this is a new *mode
on the tool the issue names* — which has to be a mode, because the write path,
the mark set, the CSV shape and the restore guard are the same for a
206-address and a 448-address sweep. **This write-up is the new file**; the
flag is not a new tool.

## The cost figures, re-derived

Computed by the tool's own `watch_set()` / `block_ioctls()` / `block_span()`,
then pinned as literals in `--self-test` and in the offline suite — the
existing pattern, "the counts it is supposed to hold to written into the check
rather than read out of the thing being checked". The plan's figures were
re-derived from the code before any of this was written, and all four rows held
to the line:

| set | addresses | `--block` runs | `--block` IOCTLs | bytes read by `--block` |
|---|---|---|---|---|
| default (`WATCH`+`FANTBL`+`TEMP`) | 206 | 7 | 56 | 224 |
| `--level-block` | 222 | 9 | 61 | 244 |
| `--watch-page` (`PAGE`+`FANTBL`+`TEMP`) | **448** | **3** | **112** | **448** |
| `--watch-page --level-block` | **464** | **5** | **117** | 468 |

Two properties are written into the docstring rather than left implied:

- **448/4 = 112 exactly, while 206/4 gives 52, not 56.** The page arm is the
  first configuration where `block_ioctls` matches the naive division, because
  the `0x07xx` part becomes contiguous. The docstring's existing "it is **not**
  the 52 that `206/4` suggests" caveat stays true of the *default* and is
  joined by a sentence saying the page arm is the divisible case — the caveat
  does not generalise, and must not be left sounding as though it did.
- **`0x0700` and `0x0800` are both 4-aligned, so the page arm's `--block` span
  has no padding at all** — 448 bytes read for 448 addresses, against 224 for
  206. And it issues no MMRD outside the default byte path's footprint: the
  default already issues an aligned 4-byte read at `0x0740` to cover `0x0743`,
  so the access *width* is unchanged and only the count moves. That is the
  answer to the question a reader will actually have — does reading the whole
  page widen any access to a page the narrow set did not already touch? — and
  the answer is no, on the same terms `--level-block` already argues.

## The invariants near the work

- **"Calibrate, don't overclaim."** The load-bearing one. Nothing here says a
  page-arm run has happened, a register moved, or the block path is safe
  against the driver. **The page arm has never been run against the vendor
  driver, on this machine or any other**; `ecrw.py:153` says the same of
  `read_dword` before this change and the new flag does not move that. The
  §3b correction in the runbook and the docstring each say so in those terms.
  The #476 correction's text stays visible with a correction beside it — the
  `docs/findings.md` §4a-4d pattern, not a quiet edit.
- **The default's 206 stays the default.** The 2026-09-23 evidence was taken
  at **110** reads per sweep, its own header listing `WATCH` plus the fan table
  and no temperature range (`TEMP` joined the next day, with #143), so 206 is
  the default a later run would sweep rather than that run's footprint, and no
  committed run was taken at it. The default set, the default banner, the
  default IOCTL figure and the docstring's 87%-over-110 sentence are
  unchanged, and `test_the_whole_page_arm_is_opt_in` plus
  `test_block_sweeps_through_readmany` assert the default is still 206/56. The
  `--level-block` precedent.
- **The fan-tach page stays unreachable by typing and by construction** (#94).
  The flag takes no address; `FAN_TACH` is unchanged; `--self-test` and
  `test_ecrw.py` check all four sets for both membership and `block_span`.
  0x045F in, 0x0460/0x046A/0x046F out.
- **One write, and it is `0x0751`.** A page-arm run must still write exactly
  three bytes (`orig`, `target`, `orig`) and nothing else. Asserted on the
  fake's `writes` list, not on a docstring sentence — a read-only watch set is
  the whole reason a 448-address capture is safe to leave running, and that is
  a worse claim to make about a bigger sweep than about a smaller one.
- **Substitution widens, never swaps.** All 14 `WATCH` addresses are inside
  `PAGE`, so a page-arm run still watches every one of them. Pinned by the
  `--self-test` row and by `test_the_page_arm_is_section_3s_three_watchers`.
- **The sweep boundary is stable.** `watch_set(...)[-1] == 0x045F` for the
  page arm, as for the default: the list order is `PAGE + FANTBL + TEMP`, not
  ascending. Appending the page instead would move the boundary to `0x07FF`
  and land every scripted value in the suite on the wrong sweep — failing as
  wrong numbers, not as a crash, which is why it is its own case and why
  `FakeEc._last` now derives from the *requested* set rather than from
  `probe.ALL[-1]`.
- **Nothing in the page is inferred from being read.** A byte that holds still
  under `--watch-page` has been *read and did not move*, which is not the same
  as *known inert* and not the same as *not present* (CLAUDE.md). 242
  newly-watched addresses that all read `0x00` is exactly the shape of a
  confident-sounding wrong claim.
- **New work in new files.** The investigation is a new file; the shared docs
  get pointers and one-clause additions only.
- **The grader is not edited**, and no fixture is. Its `others` line already
  covers the page arm's rows.

## What changed, and the tests that hold it

`windows/tools/manual_fan_ctrl_probe.py` — `PAGE` beside `WATCH`; `watch_set`
gaining `watch_page`; the `--watch-page` flag; a banner line beside the
`--level-block` one; the `block_ioctls` / `block_span` docstrings; the usage
line; and five new `--self-test` rows.

`windows/tools/test_manual_fan_ctrl_probe.py` — `FakeEc` learning the flag and
deriving its sweep boundary from the requested set, and twelve cases:

| claim | case |
|---|---|
| the default footprint is untouched, and `0x0700`/`0x07FF` are not in it | `test_the_whole_page_arm_is_opt_in` |
| the page arm **is** §3's three watchers | `test_the_page_arm_is_section_3s_three_watchers` |
| substitution widens, never swaps (14 in, no 270) | same, plus the `--self-test` row |
| the read-safety guard moves with it, all four sets | `test_watch_set_stops_before_the_fan_tach` |
| the page arm writes only `0x0751` | `test_the_page_arm_still_writes_only_the_mode_byte` |
| the sweep boundary is `0x045F` in every configuration | `test_every_set_closes_its_sweep_on_the_address_the_fake_expects` |
| …and the run therefore sees the same values | `test_the_page_arm_reports_what_the_default_reports` |
| the banner names the page, the figure and the read-only path | `test_the_banner_states_the_whole_page_and_the_read_only_path` |
| and no default run reads as answering §4.4 | `test_no_page_banner_without_the_flag` |
| `--block` on it is 112/117 over three whole runs | `test_the_page_arm_block_sweep_is_three_whole_runs` |
| the capture still grades | `test_a_page_arm_capture_passes_the_real_grader_end_to_end` |
| ungraded rows are surfaced, not dropped | `test_a_page_arm_capture_keeps_its_ungraded_rows_visible` |

`windows/tools/test_ecrw.py` — the fan-tach enumeration becomes all four sets
(a set that grows later has to fail there too, and this one grew), and
`test_the_page_arm_costs_112_ioctls_and_reads_448_bytes` runs the page set
through the **real** `readmany` on a fake `kernel32`, so 112 is what the wire
carries and not what the address count divided by four suggests.

Each new case was checked against a mutation of the tool, because a case that
passes both ways is not a pin: substituting replaced with appending (10 probe
failures), `PAGE` widened over the fan-tach page (12), `WATCH` one address
shorter so the default stops being 206 (13), the banner gated off (1), and an
extra `ec.write` of `0x0743` in the `finally` (5). Every one turns the suite
red.

**The self-test is the row a human without the machine can run, and it was not
run on this branch's runner**: `python windows/tools/manual_fan_ctrl_probe.py
0xA0 --self-test` needs `ecrw`, which binds `kernel32` at import time
(`ecrw.py:69`) and so only loads on Windows. The same code path was run here
through the suite, which installs `windows/tools/ecrw_fake.py` first
(`test_the_self_test_checks_the_page_arms_figures` and the rest). The claim
is that it passes offline on a fake, not that a human has run it on the
Windows box.

## The one judgement check, and what it found

The plan asks for one thing be run by hand rather than asserted, because it is
a judgement and not a failure mode: a `--watch-page --csv` capture fed to
`grade_0751_isolation.py`, to see how long the `other addresses that moved`
line gets when ~240 addresses differ at once. It was run offline, against the
same fake, with the 242 unnamed page addresses each given a move under the
write arm. **The grader returns exit 0, one `intact` block, three roles, every
window printed**, and the line reads:

```
    other addresses that moved (243), not graded here -- read them against §4.4 and §4.5 by hand:
      0x0751 0x0701 0x0702 ... 0x07FF
```

**243, not 242** — `0x0751` lands in the same bucket, because it is the byte
the run itself wrote and the grader grades none of it. The count is 1706
characters on a single unwrapped line, the widest in the report. So the line
stays bounded as the plan expected (one `print`, space-joined) and is also
four times a normal terminal width, which is worth knowing before the flag is
recommended to a human at a machine. **Whether it should count and wrap
instead of joining is a grader-side call**, and this offline fixture is not the
place to take it; it belongs with the first real page-arm capture in hand.
`test_a_page_arm_capture_keeps_its_ungraded_rows_visible` pins the mechanism
(one address, the count, the address named) rather than the width.

## What this does not establish

- **No hardware, no Windows box, no EC, no driver.** The page arm has never
  issued 256 ECRRs or 64 MMRDs against the real driver. #663 is the human
  fixed-load re-run, it is `needs-hardware-test`, and it owns the run; this is
  preparation for it and changes nothing about it.
- **A 448-address sweep is not a safety claim.** The only byte written is
  `0x0751`, and that is a statement about the *tool*, not about the EC. What
  EC traffic does to a fan is #94, and 2.2x the traffic does not narrow it.
  `--watch-page --block` is the combination with the least evidence behind it:
  64 aligned MMRDs back to back inside a page the EC is actively using,
  against the default's 8. The docstring says so where a human reads the help.
- **No register `status:` moves.** `ec/annotations/registers.yaml` is not
  touched. The page arm widens what a human can *observe*; the 242 addresses
  it newly sweeps are unnamed or `present-untested` today, and naming them is
  a separate issue.
- **"Read and did not move" is not "inert".** See the invariants above. A
  quiet page-arm run says the bytes did not move in that run's window, which
  per §5 of the runbook is not even a claim about the next suspend, AC
  transition or EC reset.

## Left out on purpose

- **A typed page selector, a `--len`, and any generalisation to the `0x0F00`
  or `0x0400` pages.** Declined above, with the guard as the reason.
- **§4.6's dump pairs, §3a's service-stopped pass, §4.5's package power.** The
  probe's existing §3b gaps, already named in the procedure.
- **The grader.** No edit to `grade_0751_isolation.py` or its fixtures.
- **#598** (`gpu_block_watch.py`'s `0x09E9-0x09EB` window) — a different tool
  and a different page. Untouched, as the issue says.
- **`.github/workflows/` and `.github/actions/`, and so no gate edit.**
  `tools/run-tests.sh` discovers every `test_*.py` by glob, so the new cases
  need no registration, and its own header says calling it from
  `agent-gates.sh` is an upstream (`ElDavoo/agent-pipeline`) change anyway.
- **An upstream PR.** Nothing here is a patch for `Wer-Wolf/uniwill-laptop` or
  `tuxedo-drivers`; this is a reverse-engineering instrument. If a future
  change to this tool wants upstream standing, that is issue #10's job, and
  still a human's to submit.

## Follow-ups this opens

- **242 addresses are now sweepable and unnamed.** `0x0700-0x07FF` minus the 14
  in `WATCH` is the least-mapped part of the page by §4.4's own account, and a
  `--watch-page` run will produce change rows for addresses no doc has a name
  for. Naming them — through the existing `ec/annotations/registers.yaml`
  census route, with the page's own `present-untested` discipline — is its own
  issue, and the natural next entry in the queue after this one.
- **Whether the block path is safe over a whole page** is a sharper version of
  #94 than the 14-address case was: 64 aligned MMRDs back to back inside a
  page the EC is actively using, versus 8. The tool already says the path has
  never met the driver; this makes the gap bigger and the existing wording
  does not need to change, but a human should know which flag combination has
  the least evidence behind it.
- **The grader's `other addresses that moved` line has never been read at this
  volume.** 243 addresses is one 1706-character unwrapped line. Whether it
  should count and wrap rather than join is a grader-side call, and the right
  place to raise it is with the first real page-arm capture in hand, not
  before.
