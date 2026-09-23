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

All are in `ec_watch.py --mark --csv` format, `MARK` rows included.
