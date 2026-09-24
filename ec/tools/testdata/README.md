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
| `0751-isolation-run-3blocks/*.csv` | `../grade_0751_isolation.py` | A three-value day: the three CSVs §6 names, carrying all three blocks' marks in one set the way §3 takes them, one block per value `a0`/`00`/`10`, and **block 2's restore mark absent** — what a mark typed after that watcher had exited looks like in a capture, printed by `ec_watch.py` and written to no CSV. It is the only fixture with a void block in it, and so the one §3's per-block integrity check and the grader's `--block` are read against. The duty byte drifts throughout and nothing §4.1-§4.3 moves, as in `0751-isolation-run/` above. It is *not* a prediction that a block will come out void, that a restore mark will be lost, or that a die warms the way the drift beside it suggests. |

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
