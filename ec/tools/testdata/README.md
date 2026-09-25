# Constructed inputs for the tools in `ec/tools/`

**Nothing in this directory is a capture.** These files were written by hand to
exercise a tool's branches; no byte here was read from an EC, and none of them
is evidence of anything. Real captures live in `../../../evidence/` and are
dated with the day they were taken — the files here carry an obviously
placeholder `2026-01-01` timestamp so the two can never be confused.

| File | Feeds | What it constructs |
| --- | --- | --- |
| `0751-isolation-example-quiet.csv` | `../grade_0751_isolation.py` | A capture in which none of the bytes §4 of the isolation procedure names moves after the mark — only two sensor-looking addresses do. |
| `0751-isolation-example-active.csv` | `../grade_0751_isolation.py` | The opposite branch: `0x0784` and `0x07C6` move within a second of the write mark. This is *not* a prediction that they will. |
| `0751-isolation-example-fixed-load-0700-07ff.csv` + `...-0400-045f.csv` | `../grade_0751_isolation.py` | One fixed-load run as §3 now takes it, split the way the procedure splits it: the candidate PWM bytes in the `0x0700-0x07FF` capture, `0x043E`/`0x044F` in the `0x0400-0x045F` one, both marking a no-op control arm, the write under test and the restore. PWM moves in all three windows and `CPU_TEMP` climbs throughout, none of §4.1-§4.3 moves at all — the shape the 2026-09-23 run actually saw, where the PWM drift was thermal. It is *not* a prediction that a re-run will produce it. |
| `0751-isolation-example-multi-move-0400-045f.csv` | `../grade_0751_isolation.py` | The temperature half of the same three marks, in a shape the pair above does not have: `CPU_TEMP` climbs two steps and then comes back down one inside the control window, so its net (`+1`) and its total movement (`3`) disagree where the write window's (`+3`, `3`) do not. It is the fixture §4.4's choice of figure is argued from — the two arms moved identically, and only the net makes the write look like it moved three times as far. It is read alongside `...-fixed-load-0700-07ff.csv` above and was written to match that file's marks; the two are fixtures, not a run. It is *not* a prediction that a die will wander like that. |
| `0751-isolation-example-mailbox-poke.csv` | `../grade_0751_isolation.py` | The `0x0F5D-0x0F5F` mailbox poke as three change rows inside the write window, which is the same shape the `...-moved-mailbox-` pair below has as a dump difference. It reaches the windowed reader's own group heading and the closing paragraph's attribution, which the dump pairs cannot. It is *not* a prediction that a host writes those three bytes, or when. |
| `0751-isolation-example-moved-pl2-before-0700.txt` + `...-after-0700.txt` | `../grade_0751_isolation.py --dump-pair` | A `0x0700-0x07FF` before/after pair in the shape §3's steps 0 and 6 take, differing at `0x0784` and at nothing else. It reaches the whole-block read's value line — the `else` that prints `0xNNNN 0xXX -> 0xXX` under a heading — which no pair in `0751-isolation-run/` reaches, because those differ only where the captures record movement. `0x50 -> 0x28` is the move `0751-isolation-example-active.csv` records at that byte, so the two agree. It is *not* a prediction that a PL moves. |
| `0751-isolation-example-moved-fan-before-0f00.txt` + `...-after-0f00.txt` | `../grade_0751_isolation.py --dump-pair` | A `0x0F00-0x0F5F` pair differing at one §4.2 duty slot and at the three mailbox bytes after it, so the two halves have to come back under different headings and §4.2's own next step is printed. The three taking one value (`0x6E`) is the shape the 2026-09-23 power-mode-cycle capture shows, where they track `0x0F58-0x0F5C` and the `0xFD`/`0xC9` magic never appears. It is *not* a prediction that a table is written this way. |
| `0751-isolation-example-moved-mailbox-before-0f00.txt` + `...-after-0f00.txt` | `../grade_0751_isolation.py --dump-pair` | The same page again, this time differing at `0x0F5D-0x0F5F` **only**, and holding the magic and a selector the `manual-fan-ctrl-0751.md` §6 handler at `0x888D` requires. This is the false-positive shape: with the vendor service up, §3's main arm, a poke there must not read as the EC reloading its own table, and §4.2's own bytes are unchanged here. It is *not* a prediction that the service poked the mailbox. |
| `capture-claims-example-power-mode-cycle-0700-07ff.csv` | `../check_capture_claims.py`, via `../test_check_capture_claims.py` | A `0x0700-0x07FF` power-mode-cycle log in the committed `2026-09-23` file's shape — the two `0x07C4` writes, a `0x07C6` run, the `0x0743`/`0x0745`/`0x0746` plug-in sweep — and **no row at all for `0x07D4` or `0x07D5`**. That absence is the point: it is the shape issue #270's correction describes, and the sentence that used to contradict it is the one the test asserts fails. The prose is inline in the test rather than stored beside this file, because a `.md` under `ec/` naming a capture and claiming a movement is exactly what the tool flags, so committing one would make the tool's own committed-tree case red by construction. It is *not* a prediction that a byte which did not move once will not move again. |
| `capture-claims-example-ac-plugin-sweep-summary.csv` | `../check_capture_claims.py`, via `../test_check_capture_claims.py` | A per-address summary in the committed sweep summary's own schema — one row per address, the change total in a `change_count` column rather than a row per change — so the reader's derived branch is exercised and not just the row tally. Its `#` comment lines are also the parse: the committed file opens with three, and a reader that does not drop them before the header takes a comment as the fieldnames and finds no `addr` column. It is *not* a prediction that a sweep changes any address this many times. |
| `gpu-door-example-acpi-first.csv` | `../grade_gpu_door.py` | The ACPI half (`0x07C4`-`0x07D7`) leading the host half in both of two mark windows, by 800 ms and 1300 ms, so the ordering figure and its ms delta can be read off a file. One address moves eight seconds *before* the first mark, so it belongs to no window but still sets the level both windows opened on. It is *not* a prediction that the ACPI half leads. |
| `gpu-door-example-host-first.csv` | `../grade_gpu_door.py` | The same question the other way round, by 650 ms and 950 ms, with `0x07D0` among the hits so the report's DSDT-name column carries a `DO-NOT-WRITE-BLIND` byte. It is *not* a prediction that the host half leads, or that `0x07D0` moves at all. |
| `gpu-door-example-one-block.csv` | `../grade_gpu_door.py` | Only the ACPI half moves, in both windows, so there is no ordering to report and a report that printed one would be inventing a comparison — and whose closing paragraph must not reach for §6's "no movement at all" reading over a capture in which it moved twice. It is *not* a prediction that the host half will hold still; §1 of the procedure notes the service writes it. |
| `gpu-door-example-quiet.csv` | `../grade_gpu_door.py` | §6's third bullet: three marks, thirty seconds apart, and not one change row. Every one of the 24 watched addresses therefore has a `???? -> ????  net +0  total 0  max 0` line in every window, which is the fixture that makes "a zero is a stated line, not a missing one" testable rather than asserted. It is *not* a prediction that a run will be quiet. |
| `gpu-door-example-moved-and-back.csv` | `../grade_gpu_door.py` | `0x07D0` steps up twice and returns to where it started inside one window, so its endpoint line reads `0x00 -> 0x00` — held — while `total 112` and `max 56` say it moved 112 and got 56 away. The block summary counts one address over three rows, and the block still counts as moved, so the ordering is unaffected. It is *not* a prediction that `0x07D0` moves and returns, or by how much. |
| `gpu-door-example-close-marks.csv` | `../grade_gpu_door.py` | Two marks 1.0 s apart, inside `grade_0751_isolation.py`'s `MARK_MERGE_SECONDS`. That grader fuses them on purpose and this one must not, so the first — a one-second window with nothing in it — survives as a window of its own and the distance is printed. It is *not* a prediction that a run will be paced like this; §3 asks for ~30 s between actions. |
| `0751-isolation-run-3blocks/*.csv` | `../grade_0751_isolation.py` | A three-value day: the three CSVs §6 names, carrying all three blocks' marks in one set the way §3 takes them, one block per value `a0`/`00`/`10`, and **block 2's restore mark absent** — what a mark typed after that watcher had exited looks like in a capture, printed by `ec_watch.py` and written to no CSV. It is the three-value day §3's per-block integrity check and the grader's `--block` are first read against; `0751-isolation-run-void-block/` below is that same void condition in a one-block set, with nothing else wrong with it. The duty byte drifts throughout and nothing §4.1-§4.3 moves, as in `0751-isolation-run/` above. It is *not* a prediction that a block will come out void, that a restore mark will be lost, or that a die warms the way the drift beside it suggests. |
| `0751-isolation-run-missing-mark/*.csv` | `../grade_0751_isolation.py` | The same `0xA0` block as `0751-isolation-run/`, byte for byte in the `0x0700` and `0x0400` captures, with **the control-arm mark missing from the `0x0F00` capture** — two marks there where the other two have three. Its `0x0F0A` row at 12:00:08.500 is the control arm's own movement and lands before the first mark of the set, so no window can claim it: an arm quiet for want of a mark rather than because nothing moved. The second `0x0F0A` row, after its own write mark, is present and inside a window, so the capture is not quiet everywhere and the quiet control window is the interesting half. It is *not* a prediction that a run will lose a mark, and `0x0F0A` is not a prediction that a fan-table byte moves. |
| `0751-isolation-run-3blocks-moved/*.csv` | `../grade_0751_isolation.py` | `0751-isolation-run-3blocks/` above with **one `0x0784` row added** (`0x50 -> 0x28`) inside block 1's `0xA0` write window, the address and the step `0751-isolation-example-active.csv` records, and every mark untouched — so the block structure and the void block 2 are that set verbatim: the same 2 withheld of 8, and now one of the 6 that were graded moved. It exists because that combination had no fixture at all: the three sets below withhold every window and the two clean ones move nothing, so the grader's "something moved" branch was only ever reached over runs with no withheld window in the chain, and a partly-graded run had nothing to scope a movement claim against. It is *not* a prediction that a PL moves, nor that a re-run of a three-value day will lose a restore mark. |
| `0751-isolation-run-disagreeing-marks/*.csv` | `../grade_0751_isolation.py` | The same `0xA0` block again, with **one console's write mark spelling `0x10` where the other two say `0xA0`** — a mistyped digit that `coalesce_marks` merges into `wrote 0x0751=0xA0 / wrote 0x0751=0x10` and that no amount of timestamp arithmetic can see. Every byte still lands in the right window, which is the point: the label is the only thing that can catch it, and §6 asks for the three captures to agree for exactly that reason. It is *not* a prediction that an operator will mistype a mark. |
| `0751-isolation-run-void-block/*.csv` | `../grade_0751_isolation.py` | The same `0xA0` block with **no restore mark in any capture** — two marks per console, ending on the write. The duty byte drifts and nothing §4.1-§4.3 moves, so what the check withholds here would otherwise have been the quietest report the tool can produce, which is what makes withholding it worth a fixture. It is *not* a prediction that a restore will be lost. |
| `0751-isolation-run-multi-block/*.csv` + `*-a0-before-0700.txt` etc. | `../grade_0751_isolation.py` | A clean **two-value day**, `0xA0` then `0x10`, in §6's three-CSV form with all six marks present in all three captures and spelled the same way in all of them. Nothing here is meant to be caught: it is the shape the mark census and the per-block grading are read against, and the one fixture with a dump of its own per block. The four dumps are a short `ecrw.py dump 0x0750 0x0010` around `0x0751` rather than the whole `0x0700` page, because §4.6 is the only question they are read for; `0x0751` reads `0x10` in the `a0` before-dump, holds `0xA0` in its after-dump, and the `10` pair is the same page in the other order, so one value's verdict cannot be read as another's. It is *not* a prediction that a day holds two values. |
| `0751-isolation-run-unplaced-window/*.csv` | `../grade_0751_isolation.py` | The same two-value day as `multi-block/`, with **two `restore` marks in no block** — one before the first block and one between the two. Nothing else is wrong: every mark is in every capture and spelled the same way in all three, and both blocks are intact, so this set is not here to be refused. It is the fixture for `--block` selecting a block's *own* windows, and unscoped for the closing section's fourth case: the only committed run that reaches the `elif graded_unplaced:` branch, and so the only one to print `UNPLACED_GRADED_NOTE` at `2 of the 8` *with* that branch's sentence under it — `unread-window/` below prints the same note and takes the withheld branch above it instead. `assign_blocks` leaves a window it could not place in the same list, so a `--block` run that took a range the length of the blocks ahead of it ran short by whichever of these came first — printing one in the block's place, dropping the block's own restore, and still calling the block `intact`. The two leftovers are one in each position so both blocks are held to the same promise the census makes of them (`--block` cannot select a window in no block); the stray at the front holds the first temperature row, so it is a window with real bytes in it and not a quiet one. The two roles are one set of bytes rather than two, and a `--block 0xA0` run over it is what shows why: the per-block sentence prints, the count line and `UNREAD_MARK_NOTE` do not, exit 0. That is structural rather than guarded — a `--block` run's `shown` is that block's own windows, and a window in no block cannot be one — which is why the branch is placed where a `--block` run cannot reach it at all. See `docs/findings/0751-grader-unplaced-window-scope.md`. It is *not* a prediction that a restore is ever typed with no block open. |
| `0751-isolation-run-unread-window/*.csv` | `../grade_0751_isolation.py` | `0751-isolation-run-unplaced-window/` **byte for byte, with one mark relabelled** — the first of its two block-less restores reads `'restored it somehow'` in all three captures, a form §6 does not fix. The label is the only variable, and the two windows in no block differ in exactly that: the 12:04 restore still parses and is graded under `block: unplaced`, the 12:00 one is refused. Both blocks are intact, so this withholds 1 window of 8 and grades 7 — the *other* reason a run is partly graded, and the one whose withheld window is in no block at all. It is here because the closing summary a withheld run prints has to hold for both reasons a window is withheld, and only the mark-set one was covered: a window refused for an unreadable label belongs to no block, which the same run's census says in as many words, so a closing sentence about a *block* this report refused to read is a §7 fact the output denies. It is also the fixture holding **both** kinds of window in no block at once, which is the property both ways of scoping an unreadable label rest on: `--block` can select neither the refused 12:00 window nor the graded 12:04 one, so a `--block 0xA0` run of this set prints that block's three windows, `intact`, and exits 1 without having printed or withheld either stray — and `unplaced-window/`, the same day byte for byte with that one label made readable, exits 0. See `docs/findings/0751-grader-block-scoping.md`. It is also the only committed run where a withheld window and a graded window in no block hold at once, and the only one whose two counts are taken over different denominators — the withheld banner's `1 of the 8` against the count line's `1 of the 7` — which is what makes it the run that can tell where the count is taken: on `unplaced-window/` above the two coincide, so a count taken over `shown` rather than at the print point would print the same `2 of the 8` there. See `docs/findings/0751-grader-unplaced-window-scope.md`. It is *not* a prediction that a mark is ever mistyped, nor that a re-run of a two-value day will hold a window in no block. |
| `0751-isolation-run-unplaced-window-failures/*.csv` | `../grade_0751_isolation.py` | `0751-isolation-run-unplaced-window/` **byte for byte, with one thing wrong with each of its two block-less restores** — the 12:00 one is spelled `restored 0x0751=0x0a` in the `0x0700` capture where the other two say `0x99`, and the 12:04 one is **absent from the `0x0F00` capture** altogether, one mark short of the eight the other two captures hold. Both labels still parse, so neither is a `restored it somehow`: they are a stray the consoles spelled two ways and a stray one console did not record — the two checks `check_block_marks` was already running over a block's own windows and was not reaching past a block. The two are the two *kinds* on purpose, so a one-sided fix has something to fail against, and it is one directory rather than two because the test discriminates on the refusal each window carries rather than on the directory's name. Both blocks are intact and their six windows are that set verbatim, so the 2 withheld of 8 are the strays and nothing else. It is *not* a prediction that a mark is ever mistyped or ever lost. |
| `0751-isolation-run-void-block-with-dumps/*.csv` + `*-a0-before-0700.txt`, `*-a0-after-0700.txt` | `../grade_0751_isolation.py` | `0751-isolation-run-void-block/` **byte for byte, plus `0751-isolation-run-multi-block/`'s two `a0` dumps under that file's own name** — so the `<value>` in the name still says `0xA0` and `DUMP_VALUE` still files them there. It is the one shape the two clean sets cannot reach: `run/` and `multi-block/` both grade every window, so neither has a `--dump` read or a `--dump-pair` bracket filed under a block whose windows the run refused, which is the case issue #499 is about. Copied rather than composed from the two directories in the test, for the reason the other derived sets here are — a failure names its own case, and an edit to `multi-block/`'s `a0` dumps cannot move this set's block under it. Deliberately **not** in §6's fenced file list: that list and `0751-isolation-run/` are held equal on both sides, and §6's command line is unchanged by this work. It is *not* a prediction that a restore will be lost, nor that a re-run with dumps handed in will produce this combination. |
| `0751-isolation-run-staged/*.csv` | `../grade_0751_isolation.py` | The two-value day as **§3's command block prints it**: six mark rounds per block rather than three, with the three stage boundaries `settled`, `held` and `watch over` beside the three actions, so `Block.roles` reads `settle, control, hold, write, watch, restore` and `--block` has six windows to select. The `0x075B` rows are placed on either side of the `watch over` mark — one at 12:02:00 inside the write window, one at 12:03:00 between the boundary and the restore — so the claim the boundary makes is a checkable fact about the fixture and not an assertion about the tool: read with the mark, the write window is `0x68 -> 0x6B` over two changes and the `watch over` window `0x6B -> 0x6D` over one; drop it and they are one window reading `0x68 -> 0x6D` over three, with the restore's own write inside the bracket §4.4 compares. Every mark is in all three captures and spelled the same way, so nothing here is meant to be caught. It is *not* a prediction that a fan duty moves on either side of a watch, that a day holds two values, or that a re-run produces this. |

The `0751-isolation-*` `.csv` files are in `ec_watch.py --mark --csv`
format, `MARK` rows included; the two `capture-claims-example-*` ones are
read by their own tool and are in whatever schema the committed capture they
stand in for uses. The `.txt` files are `ecrw.py dump` output and are read through
`--dump-pair`, which compares two dumps against each other and takes its
windows from whatever capture is passed alongside — so a `.txt` file on its
own is a half of a pair, not a capture. The dump examples sit outside
`0751-isolation-run/` on purpose: that directory is the set §6 of
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` names, and
`../test_grade_0751_isolation.py` holds the two equal, so a dump no operator
of a hardware day would take has no business in that list.

The `gpu-door-example-*.csv` files are `gpu_block_watch.py --csv --mark`
output in the same schema — the two tools read one schema on purpose — and
they sit outside any `gpu-door-run/` directory because no such directory
exists: `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md` §5 does not name a
file set, and the run those fixtures stand in for is issue #283's and nobody
has made it. `../test_grade_gpu_door.py` holds the `gpu-door-example-*.csv`
on disk and the fixtures it runs equal, so a fixture nobody grades fails
rather than sitting there looking covered.

`0751-isolation-run-3blocks/` is a three-value day and only the three CSVs —
no dumps and no snapshot, so it is not a §6 set and nothing holds it to one.
It is what the per-block integrity check and the grader's `--block` are read
against: eight marks over three blocks, the middle one's restore missing,
which is the shape a mark typed after a watcher exited leaves behind. It sits
outside `0751-isolation-run/` for the reason the dump examples sit outside it
— that directory is the set §6 names — so a second directory under the same
naming cannot be mistaken for §6's set by the equality in
`../test_grade_0751_isolation.py`, which is over the run directory alone.

The four `0751-isolation-run-{missing-mark,disagreeing-marks,void-block,multi-block}/`
directories are the mark-set checks' own fixtures, one directory per case so
that a failure names the case. Three of the four are §3 sets with one thing
wrong with them and `multi-block/` is a §3 set with nothing wrong, which is
the half the other three are compared against: the same `0xA0` block, the
same duty drift, the same climb, so what differs between a passing run and a
refused one is the mark set and nothing else. All four are outside
`0751-isolation-run/` for the same reason as `3blocks/`: that directory is the
set §6 names, and `../test_grade_0751_isolation.py` holds the two equal.

`0751-isolation-run-unplaced-window/` sits beside those four and is a fifth
kind of case rather than a fifth mark set: its marks are all in all three
captures and both its blocks are intact, and what it is for is `--block`
picking a block's own windows when a window in no block comes first, and, run
unscoped, for the closing section's `graded_unplaced` case — the only committed
run to reach it. Its `--block 0xA0` half is what shows that count is zero there
by construction rather than by a guard, which is what holds both roles to one
set of bytes. Outside `0751-isolation-run/` for the same reason as the rest.

`0751-isolation-run-unread-window/` is that set again with one label made
unreadable, so it is a sixth kind rather than a sixth mark set: still no mark
missing and no block void, but a window refused for its own label. It is the
other half of what "partly graded" can mean — the withholding that is not the
mark-set withholding, and the only one whose window is in no block — so the
two together are what a summary sentence printed over either has to hold for.
It is also the only committed run where a withheld window and a graded window
in no block hold at once, and the only one whose two counts are taken over
different denominators — so it is the run that can tell a count taken where the
window is printed from one taken over `shown`, which the cleaner
`unplaced-window/` above cannot, its two denominators both being 8.

`0751-isolation-run-unplaced-window-failures/` is `unplaced-window/` again and an
eighth kind rather than an eighth mark set: the block structure, the six block
windows and both `intact` verdicts are that set byte for byte, and the whole
defect is in the two windows in no block, one failing each of the two checks
`check_block_marks` runs over a block's own windows. It is here because those
two were exactly the checks a stray could not fail — `check_block_marks`
iterates `block.windows`, and a window the block walk could not place was
reached by `unplaceable_marks` alone — so a mistyped digit that survived into a
stray's label, or a console that never recorded one, was named by the census
and then graded in full, in the same confident format as a result. See
`docs/findings/0751-grader-unplaced-window-checks.md`. Outside
`0751-isolation-run/` for the same reason as the rest.

`0751-isolation-run-void-block-with-dumps/` is `void-block/` with dump files
added, and it is a seventh kind rather than a seventh mark set: the marks are
the void set's verbatim, and what it adds is the *file* sections — a §4.6
readback and a whole-block bracket read for a block whose windows the run
refused. Neither clean set reaches it, because both grade every window, so
before this the dump readers were never run over a refused block and a verdict
printed four sections earlier could not reach them. Outside
`0751-isolation-run/` for the same reason as the rest, and it stays out of §6's
fenced list on purpose: the test holds that list and the run directory equal
on both sides, and §6's command line is unchanged by this work.

`0751-isolation-run-staged/` is `multi-block/` with the three mark rounds §3's
command block asks for and does not name, added: it is the day as the runbook
prints it rather than as the grader could previously read it, and it is where
the stage boundaries are exercised end to end — the roles line reads
`settle, control, hold, write, watch, restore`, a per-block run selects six
windows rather than three, and a `watch over` one capture missed or that two
spelled differently withholds its block's windows on the terms a `write`
would. It is three CSVs and no dumps, so it is not a §6 set; outside
`0751-isolation-run/` for the same reason as the rest, and its
`0751-isolation-run-staged` name says staged because the run itself is
#380's, on the machine, and nobody has taken it.

`0751-isolation-run/` is the set §6 of
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` names, all ten
files under exactly those names, so that section's command line can be run
over it end to end offline. The three CSVs are one fixed-load `0xA0` block
whose candidate PWM drifts *more* under the no-op than under the write, with
`CPU_TEMP`/`GPU_TEMP` climbing throughout and nothing §4.1-§4.3 moving — the
ambiguous, thermally-explained shape, and **not** a prediction that a re-run
produces it. That drift is monotonic, so the two figures §4.4 chooses between
agree on it (3 under the no-op against 2 under the write) and the choice does
not change what this set says; the disagreeing shape is the
`...-multi-move-0400-045f.csv` fixture above. The six dumps are full `ecrw.py dump` ranges, one pair per
range; the `0x0700` pair is the one that carries `0x0751`, reading `0x10`
before and `0xA0` after. The `0x0700` and `0x0400` pairs each differ only
where the CSVs record movement, and the `0x0F00` pair is byte for byte
identical by construction. That is what makes the `0x0F00` pair worth
keeping: it is the one that exercises the whole-block read's *unchanged*
branch, which the `0x0700` pair — always carrying the four addresses the
captures record moving — cannot reach. The `0x0400` pair is what puts
§4.5's two temperatures in the whole-block read at all, and it differs at
`0x0402` and at the two confirmed bytes, so it reaches the context group the
`0x0700` and `0x0F00` pairs have to name as out of reach. All three pairs
are now given to `--dump-pair` in §6's command, so all six dumps are
consumed and every pair names both §4.4/§4.5 context groups — as value
pairs where the range covers them, as *not covered by this pair* where it
does not.
Every file in the directory carries a `constructed` header saying no EC was
read; `../test_grade_0751_isolation.py` asserts that the list in §6 and
`0751-isolation-run/` are the same set, so a rename on one side and not the
other fails. The two `capture-claims-example-*` files are outside that set
and outside §6 on purpose — they feed a different tool and are not a §6 run —
so the assertion is over the run directory rather than over everything here.
