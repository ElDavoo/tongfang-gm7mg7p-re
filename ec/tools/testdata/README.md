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
| `0751-isolation-example-multi-move-0400-045f.csv` | `../grade_0751_isolation.py` | The temperature half of the same three marks, in a shape the pair above does not have: `CPU_TEMP` climbs two steps and then comes back down one inside the control window, so its first→last (`+1`) understates the three changes behind it and a window summary's endpoints and change count say different things. It is read alongside `...-fixed-load-0700-07ff.csv` above and was written to match that file's marks; the two are fixtures, not a run. It is *not* a prediction that a die will wander like that. |
| `0751-isolation-example-mailbox-poke.csv` | `../grade_0751_isolation.py` | The `0x0F5D-0x0F5F` mailbox poke as three change rows inside the write window, which is the same shape the `...-moved-mailbox-` pair below has as a dump difference. It reaches the windowed reader's own group heading and the closing paragraph's attribution, which the dump pairs cannot. It is *not* a prediction that a host writes those three bytes, or when. |
| `0751-isolation-example-moved-pl2-before-0700.txt` + `...-after-0700.txt` | `../grade_0751_isolation.py --dump-pair` | A `0x0700-0x07FF` before/after pair in the shape §3's steps 0 and 6 take, differing at `0x0784` and at nothing else. It reaches the whole-block read's value line — the `else` that prints `0xNNNN 0xXX -> 0xXX` under a heading — which no pair in `0751-isolation-run/` reaches, because those differ only where the captures record movement. `0x50 -> 0x28` is the move `0751-isolation-example-active.csv` records at that byte, so the two agree. It is *not* a prediction that a PL moves. |
| `0751-isolation-example-moved-fan-before-0f00.txt` + `...-after-0f00.txt` | `../grade_0751_isolation.py --dump-pair` | A `0x0F00-0x0F5F` pair differing at one §4.2 duty slot and at the three mailbox bytes after it, so the two halves have to come back under different headings and §4.2's own next step is printed. The three taking one value (`0x6E`) is the shape the 2026-09-23 power-mode-cycle capture shows, where they track `0x0F58-0x0F5C` and the `0xFD`/`0xC9` magic never appears. It is *not* a prediction that a table is written this way. |
| `0751-isolation-example-moved-mailbox-before-0f00.txt` + `...-after-0f00.txt` | `../grade_0751_isolation.py --dump-pair` | The same page again, this time differing at `0x0F5D-0x0F5F` **only**, and holding the magic and a selector the `manual-fan-ctrl-0751.md` §6 handler at `0x888D` requires. This is the false-positive shape: with the vendor service up, §3's main arm, a poke there must not read as the EC reloading its own table, and §4.2's own bytes are unchanged here. It is *not* a prediction that the service poked the mailbox. |

The `.csv` files are in `ec_watch.py --mark --csv` format, `MARK` rows
included. The `.txt` files are `ecrw.py dump` output and are read through
`--dump-pair`, which compares two dumps against each other and takes its
windows from whatever capture is passed alongside — so a `.txt` file on its
own is a half of a pair, not a capture. The dump examples sit outside
`0751-isolation-run/` on purpose: that directory is the set §6 of
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` names, and
`../test_grade_0751_isolation.py` holds the two equal, so a dump no operator
of a hardware day would take has no business in that list.

`0751-isolation-run/` is the set §6 of
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` names, all ten
files under exactly those names, so that section's command line can be run
over it end to end offline. The three CSVs are one fixed-load `0xA0` block
whose candidate PWM drifts *more* under the no-op than under the write, with
`CPU_TEMP`/`GPU_TEMP` climbing throughout and nothing §4.1-§4.3 moving — the
ambiguous, thermally-explained shape, and **not** a prediction that a re-run
produces it. The six dumps are full `ecrw.py dump` ranges, one pair per
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
read; `../test_grade_0751_isolation.py` asserts that the list in §6 and this
directory are the same set, so a rename on one side and not the other fails.
