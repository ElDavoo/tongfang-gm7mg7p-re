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

All are in `ec_watch.py --mark --csv` format, `MARK` rows included.

`0751-isolation-run/` is the set §6 of
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` names, all eight
files under exactly those names, so that section's command line can be run
over it end to end offline. The three CSVs are one fixed-load `0xA0` block
whose candidate PWM drifts *more* under the no-op than under the write, with
`CPU_TEMP`/`GPU_TEMP` climbing throughout and nothing §4.1-§4.3 moving — the
ambiguous, thermally-explained shape, and **not** a prediction that a re-run
produces it. That drift is monotonic, so the two figures §4.4 chooses between
agree on it (3 under the no-op against 2 under the write) and the choice does
not change what this set says; the disagreeing shape is the
`...-multi-move-0400-045f.csv` fixture above. The four dumps are full
`ecrw.py dump` ranges, `0x0751` reading `0x10` before and `0xA0` after,
differing only where the CSVs record movement.
Every file in the directory carries a `constructed` header saying no EC was
read; `../test_grade_0751_isolation.py` asserts that the list in §6 and this
directory are the same set, so a rename on one side and not the other fails.
