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

All are in `ec_watch.py --mark --csv` format, `MARK` rows included.

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
